from entity import (Direction, ElementMode, ElementOcc, Linear, Point,
                    PrevState, Route, RouteMode, Section, Signal, SignalAspect)
from route_op import first_element, last_element, next_element, prev_element
from trans_checks import (can_allocate_route, can_dispatch_route,
                          can_lock_route, can_set_route_in_use)
from utils import vacant, occupied  # REFACTOR: Added occupied() helper for PREV state transitions


# ==================== STATE TRANSITIONS ====================
def dispatch_route(route: Route) -> bool:
    """Dispatch a route: FREE -> MARKED"""
    if can_dispatch_route(route):
        route.MODE = RouteMode.MARKED
        return True

    return False

def allocate_route(route: Route) -> bool:
    """Allocate a route: MARKED -> ALLOCATING"""
    if not can_allocate_route(route):
        return False
    
    route.MODE = RouteMode.ALLOCATING
    
    # Command points
    for point, req_pos in route.points.items():
        point.CMD = req_pos
    
    # Command signals
    for signal in route.signals:
        signal.CMD = SignalAspect.STOP
    
    # Exclusively lock all elements in the route's path
    for elem in route.path:
        elem.MODE = ElementMode.EXLOCKED
    
    return True

def lock_route(route: Route) -> bool:
    """Lock a route: ALLOCATING -> LOCKED"""
    if not can_lock_route(route):
        return False

    route.MODE = RouteMode.LOCKED

    # M3: guard against `entry_signal` being a raw string ID rather than a Signal object
    if isinstance(route.entry_signal, Signal):
        route.entry_signal.CMD = SignalAspect.GO

    return True

def set_route_in_use(route: Route) -> bool:
    """Set the route in use: LOCKED -> OCCUPIED"""
    if not can_set_route_in_use(route):
        return False

    route.MODE = RouteMode.OCCUPIED

    # M3: guard against entry_signal being a raw string ID
    if isinstance(route.entry_signal, Signal):
        route.entry_signal.CMD = SignalAspect.STOP

    # Set the first element to USED
    first = first_element(route)

    if first:
        first.MODE = ElementMode.USED
        """
        # REFACTOR: Initialize PREV state for first element (Issue #3)
            When train is already in first element, immediately set PREV to RELEASED.
            This starts the sequential release wave for the rest of the route.
        """
        if occupied(first):
            first.PREV = PrevState.RELEASED
        
        """
        Note: If train is not yet in the first element, PREV stays PENDING
              and will transition to RELEASED via `update_element_prev_state()`
              when train physically enters.
        """

    return True

def set_element_in_use(route: Route, element: Section) -> bool:
    """Set an element in the route to USED (excluding the first element)"""
    if route.MODE != RouteMode.OCCUPIED:
        return False
    
    if element not in route.path:
        return False
    
    first = first_element(route)
    last = last_element(route)
    
    if element == first:
        return False
    
    prev = prev_element(route, element)
    
    if prev is None or prev.MODE != ElementMode.USED:
        return False
    
    if element.MODE != ElementMode.EXLOCKED:
        return False
    
    if not vacant(element):
        return False
    
    # For points, check position
    if isinstance(element, Point):
        req_pos = route.points.get(element)
        
        if req_pos is not None and element.ACT != req_pos:
            return False
    
    # Check the next element is locked (if not last)
    if element != last:
        nxt = next_element(route, element)
        
        if nxt is None or nxt.MODE != ElementMode.EXLOCKED:
            return False
    
    element.MODE = ElementMode.USED
    
    return True

def sequential_release_element(route: Route, element: Section) -> bool:
    """Sequential release of an element (except the last)"""
    if route.MODE != RouteMode.OCCUPIED:
        return False
    
    if element not in route.path:
        return False
    
    first = first_element(route)
    last = last_element(route)
    
    if element == last:
        return False
    
    if element.MODE != ElementMode.USED:
        return False
    
    if not vacant(element):
        return False
    
    # Check PREV state if not first
    if element != first and element.PREV != PrevState.RELEASED:
        return False
    
    nxt = next_element(route, element)
    
    if nxt is None:
        return False

    """
    # REFACTOR: Fix sequential release condition (Issue #2)
        ORIGINAL (INCORRECT): Required BOTH conditions with AND logic.
                              ```
                              if nxt.PREV != PrevState.PENDING or
                              nxt.MODE != ElementMode.USED:
                                  return False
                              ```
        This is De Morgan's Law inverted - effectively requires:
            `nxt.PREV == PENDING AND nxt.MODE == USED` (too restrictive!)
    """

    """
    # FIXED: Allow release when EITHER condition is true (verified SMV model)
        Per SMV logic (lines 360-368): (seg3.mode = USED | seg3.prev = PENDING)
        
        Element can release when:
            - Next element is USED (train has moved forward), OR
            - Next element's PREV is PENDING (preparing to release)
    """
    if not (nxt.MODE == ElementMode.USED or nxt.PREV == PrevState.PENDING):
        return False
    
    # For points, check position
    if isinstance(element, Point):
        req_pos = route.points.get(element)
        
        if req_pos is not None and element.ACT != req_pos:
            return False
    
    if isinstance(nxt, Point):
        req_pos = route.points.get(nxt)
        
        if req_pos is not None and nxt.ACT != req_pos:
            return False

    """
    # REFACTOR: Fix PREV reset timing (Issue #4)
        - Validate that element.PREV was already RELEASED before this transition.
        - Per verified SMV model: element should have PREV=RELEASED before releasing.
    """
    if element.PREV != PrevState.RELEASED and element != first:
        # VALIDATION WARNING: This should not happen if PREV transitions are working
        print(f"WARNING: Element {element.name} releasing but PREV != RELEASED (PREV={element.PREV})")
        # Continue anyway for robustness, but log the issue

    # Release element
    element.MODE = ElementMode.AVAILABLE
    """
    ORIGINAL: element.PREV = PrevState.PENDING
    FIXED:    Reset PREV to PENDING for next route usage
    
    This is correct timing: after MODE transition to AVAILABLE
    """
    element.PREV = PrevState.PENDING

    """
    # Signal the next element that train has entered it
    This allows the next element to eventually release its previous (current element)
    """
    nxt.PREV = PrevState.RELEASED

    return True

def release_last_element_and_route(route: Route) -> bool:
    """Release the last element and free the route"""
    if route.MODE != RouteMode.OCCUPIED:
        return False

    last = last_element(route)
    first = first_element(route)

    if last is None:
        return False

    if last.MODE != ElementMode.USED:
        return False

    """
    # C5: Terminal segments keep the train permanently (COMPLETETRAINOCC stays).
        - Route goes FREE when the train HAS ARRIVED, not when the terminal is vacant.
        - Match SMV model: r0 `OCCUPIED -> FREE` when seg7.occUp is in {HEADOCC, COMPLETETRAINOCC}.
    """
    dir = route.entry_dir
    
    if isinstance(last, Linear):
        last_occ = last.occDown if dir == Direction.DOWN else last.occUp
    elif isinstance(last, Point):
        last_occ = last.occSNR   # terminal point entered via stem
    else:
        last_occ = ElementOcc.FREE

    if last_occ not in [ElementOcc.HEADOCC, ElementOcc.COMPLETETRAINOCC]:
        return False   # train has not yet arrived at the terminal

    # Check PREV state if not first
    if last != first and last.PREV != PrevState.RELEASED:
        return False

    # For points, check position
    if isinstance(last, Point):
        req_pos = route.points.get(last)
        
        if req_pos is not None and last.ACT != req_pos:
            return False

    # Release the last element and free the route (train stays in the terminal segment)
    last.MODE = ElementMode.AVAILABLE
    last.PREV = PrevState.PENDING
    route.MODE = RouteMode.FREE

    return True

# ==================== PREV STATE MANAGEMENT ====================
# REFACTOR: NEW FUNCTION - Critical for sectional release coordination
def update_element_prev_state(route: Route, element: Section) -> bool:
    """Update element PREV state based on train occupancy (PENDING -> RELEASED)

    This function implements the verified SMV model logic for PREV state transitions.
    PREV state coordinates sequential release by tracking when a train physically
    enters an element, enabling the previous element to be released.

    Transition: PREV: PENDING -> RELEASED

    Conditions (from verified SMV model):
        1. Route is OCCUPIED
        2. Element is in USED mode (logically reserved for train)
        3. Element is physically OCCUPIED by train (train has entered)
        4. Previous element is AVAILABLE AND empty (train has left previous)

    This is the critical missing piece that enables the sequential release wave.
    Without this, elements never get PREV = RELEASED, blocking all releases.

    Args:
        route: The route containing the element
        element: The element to update PREV state for

    Returns:
        True if PREV state was transitioned to RELEASED,
        False otherwise
    """
    if route.MODE != RouteMode.OCCUPIED:
        return False

    if element.PREV != PrevState.PENDING:
        return False  # Already released

    if element.MODE != ElementMode.USED:
        return False

    """
    # CRITICAL: Element must be physically occupied by train
    This is opposite of vacant() check: we need train PRESENT
    """
    if not occupied(element):
        return False  # Train is not present yet

    """
    # Check the previous element is AVAILABLE and empty (for non-first elements)
    This ensures the train has completely left the previous element.
    """
    prev = prev_element(route, element)
    if prev is not None:
        """
        Allow EXLOCKED: prev may have been re-allocated by the next route cycle
                        while the current element is still being processed (SMV fix #4).
        """
        if prev.MODE not in (ElementMode.AVAILABLE, ElementMode.EXLOCKED):
            return False
        if not vacant(prev):
            return False  # Train still in the previous element

    """
    # Transition PREV to RELEASED
    This signals that the train has entered this element and
    the previous element can now be released.
    """
    element.PREV = PrevState.RELEASED

    return True

def update_route_prev_states(route: Route) -> bool:
    """
    Update all element PREV states for an occupied route;
    return True if any changed.
    """
    if route.MODE != RouteMode.OCCUPIED:
        return False

    changed = False

    for element in route.path:
        if element.MODE == ElementMode.USED:
            if update_element_prev_state(route, element):
                changed = True

    return changed
