# 🛤️ Sectional Release Procedure
- A sectional interlocking release procedure that is pseudo-aligned to the variables.
- Represents the sectional/sequential release of an interlocking system during a train traversal through a granted route.

### 🏷️ Entity Definition
1. **Route**
   - A route is defined by a **source** and a **destination** signal.
   - State-dependent decisions are over-approximated by non-deterministic ones.
     - The proposition representing the transition relation is effectively simplified.
    > <u>ASSUMPTION</u>: Every route requests are non-deterministic. So, the transition `FREE -> MARKED` is always enabled.

    ```json
    Route: {
      id: Int // Route identifier.,
      mode: Enum {
        FREE, // Initially the route is in FREE state. Route is ready for next request.
        MARKED, // Request for the route grant (dispatch) is made (non-deterministic).
        ALLOCATING, // Route resources are being allocated. Elements transition to EXLOCKED.
        LOCKED, // Track-side elements are locked and configured. Source signal set to GO.
        OCCUPIED, // Route is occupied by train. Sectional release in progress as train traverses.
      },
      transition: Enum { // Route transition precondition checks
        CAN_DISPATCH, // Checks whether a FREE route can be MARKED for dispatch.
        CAN_ALLOCATE, // Checks whether a MARKED route can be allocated (elements vacant, no conflicts).
        CAN_LOCK, // Checks whether an ALLOCATING route can be locked (elements EXLOCKED, points positioned).
        CAN_OCCUPY // Checks whether a LOCKED route can be set to OCCUPIED (signal GO, ready to enter).
      }
    }
    ```

2. **Linear Section**
   - Represents a linear section of track, for the SWTbahn this is equivalent to a segment.
   - Have two neighbours:
     - `UP`: End at the anti-clockwise direction.
     - `DOWN`: End at the clockwise direction.
   - Train has head and tail, and can occupy either:
     - exactly 1 section (`COMPLETETRAINOCC`), or
     - exactly 2 sections, one has the **head**, the other has the **tail**.
  
    > With sequential release, an element in a locked route can be released as soon as the train has passed it. Consequently, the capacity increases. Hence, a route may be allocated while some of its conflicting routes are still occupied by trains.

    ```json
    Linear: {
      id: Int, // Segment identifier in a linear section.
      occDown: Enum {
        FREE, // Segment is free/available.
        HEADOCC, // Segment is occupied by the head of a train.
        COMPLETETRAINOCC, // Segment is occupied by a whole train.
        TAILOCC, // Segment is occupied by the train of a train.
        ERROROCC // Error/conflict on the segment occupany update.
      },
      occUp: Enum {FREE, HEADOCC, COMPLETETRAINOCC, TAILOCC, ERROROCC},
      mode: Enum { // Track element lock mode
        AVAILABLE, // Segment is in free state - is available for use by a route.
        EXLOCKED, // Segment is exclusively locked for the use of a allocated route.
        USED // Segment of the route is finised beign used.
      },
      prev: Enum { // Identifier for previous elements' used status
        PENDING, // previous element is vacant/being used
        RELEASED // train has leaved the previous element
      },
    }
    ```

3. **Point**
   - Section with three neighbours:
     - Stem, straight(normal) and branching(reverse) path ends.
   - Switches between two positions:
     - `NORMAL`: stem is connected to the straight end.
     - `REVERSE`: stem is connected to the branching end.
    ```json
    Point: {
      id: Int, // Point identifier.
      segID: Int, // Identifier of a segment that is a point in a linear section.
      ACT: Enum { // Points' actual position aspect
        NORMAL, // Denotes that points' actual position is set from stem to straight end.
        REVERSE, // Denotes that points' actual position is set from stem to branching end.
        INTERMEDIATE // Denotes that a points' actual position is different from the position commanded.
      },
      occSNR: Enum { // Point element occupany with entry from Stem to either Normal or Reverse end
        FREE, HEADOCC, COMPLETETRAINOCC, TAILOCC, ERROROCC
      },
      occNS: Enum { // Point element occupany with entry from Normal to Stem end
        FREE, HEADOCC, COMPLETETRAINOCC, TAILOCC, ERROROCC
      },
      occSNR: Enum { // Point element occupany with entry from Reverse to Stem end
        FREE, HEADOCC, COMPLETETRAINOCC, TAILOCC, ERROROCC
      },
      mode: Enum {AVAILABLE, EXLOCKED, USED},
      prev: Enum {PENDING, RELEASED}
    }
    ```
4. **Signal**
   - Two signals installed along each linear section for each direction.
   - Only signal in the same direction of trains' movement is used as a reference location (for the start and the end of the train traversal).
    ```json
    Signal: {
      id: Int, // Signal identifier
      ACT: Enum { // Signals' actual status
        GO, // Entry to the next segment is allowed.
        STOP // Entry to the next segment is not allowed.
      }
    }
    ```

## 🧮 Sectional Interlocker, Version 1.2

#### ⚙️ Workflow:
1. Initially the route is FREE with transition state CAN_DISPATCH.
2. Route is MARKED as requested when transition CAN_DISPATCH is satisfied.
   - Complete train occupied at starting position.
3. Check the status of different track-side elements (transition CAN_ALLOCATE):
   - Track segments must be vacant (FREE).
   - The conflicting routes must not be ALLOCATING or LOCKED.
   - All points must be in required positions (ACT matches route configuration).
4. Route enters ALLOCATING state and track elements are locked:
   - All route elements' mode transitions from AVAILABLE to EXLOCKED.
   - Protecting signals remain at STOP.
   - Points are commanded to switch to their required positions.
5. Route enters LOCKED state when transition CAN_LOCK is satisfied:
   - All protecting signals are at STOP.
   - All points are in correct positions (ACT matches requirements).
   - All route elements are EXLOCKED and vacant.
   - Source signal is commanded to GO, allowing train to enter.
6. Route enters OCCUPIED state when transition CAN_OCCUPY is satisfied:
   - Source signal is at GO.
   - First element in route path is FREE (train ready to enter).
7. Train traverses the route:
   - **Sectional release** is performed on track elements as train progresses.
   - Elements transition: EXLOCKED → USED → AVAILABLE in a wave pattern.
   - Element becomes USED when previous element is USED and next element is EXLOCKED.
   - Element becomes AVAILABLE when it is vacant, next element is USED (or PENDING), and its PREV flag is RELEASED.
8. Route is released (returns to FREE) when:
   - Last element in route is USED.
   - Train has reached destination (occupies last element).
   - Transition returns to CAN_DISPATCH for next request.

### 🐍 Pseudo-Code
1. Interlocking System:
   - Add routes and required track elements (segments, points, signals) with configuration data to the interlocking system.
   - The step function executes transitions in parallel (declarative model).
   - Route transitions and element mode changes happen simultaneously based on current state.

```py
class InterlockingSystem:
    def add_route(self, route: Route) -> None:
        """Add a route to the system"""
        routes.append(route)

    def add_section(self, section: Section) -> None:
        """Add a section to the system"""
        sections.append(section)
        if isinstance(section, Point):
            points.append(section)

    def add_signal(self, signal: Signal) -> None:
        """Add a signal to the system"""
        signals.append(signal)

    def step(self) -> bool:
        """Execute one step of the interlocking system (all transitions in parallel)"""
        changed = False

        # 1. Update route transitions (CAN_DISPATCH -> CAN_ALLOCATE -> CAN_LOCK -> CAN_OCCUPY)
        for route in routes:
            if update_route_transition(route):
                changed = True

        # 2. Update route modes (FREE -> MARKED -> ALLOCATING -> LOCKED -> OCCUPIED -> FREE)
        for route in routes:
            if update_route_mode(route):
                changed = True

        # 3. Update element modes (AVAILABLE -> EXLOCKED -> USED -> AVAILABLE)
        for route in routes:
            for elem in route.path:
                if update_element_mode(route, elem):
                    changed = True

        # 4. Update element PREV flags (PENDING -> RELEASED)
        for route in routes:
            for elem in route.path:
                if update_element_prev(route, elem):
                    changed = True

        # 5. Process train movement (occupancy updates)
        if process_train_movement():
            changed = True

        # 6. Process point switching (CMD -> INTERMEDIATE -> ACT)
        for point in points:
            if update_point_position(point):
                changed = True

        # 7. Process signal communication (CMD -> ACT)
        for signal in signals:
            if update_signal_aspect(signal):
                changed = True

        return changed
```

2. Route State Management:
   - Routes have two state machines: `mode` and `transition`.
   - `transition` checks preconditions for mode changes.
   - `mode` represents the actual route state.

```py
    def update_route_transition(self, route: Route) -> bool:
        """Update route transition state based on current conditions"""
        old_transition = route.transition

        # CAN_DISPATCH -> CAN_ALLOCATE: Check if route can be allocated
        if (route.transition == RouteTransition.CAN_DISPATCH
            and route.mode == RouteMode.MARKED
            and not any(conflicting.mode in {RouteMode.ALLOCATING, RouteMode.LOCKED}
                       for conflicting in route.conflicting_routes)
            and all(elem.mode == ElementMode.AVAILABLE for elem in route.path)
            and all(elem.is_vacant() for elem in route.path)
            and all(point.ACT == route.point_positions[point]
                   for point in route.points if point in route.point_positions)):
            route.transition = RouteTransition.CAN_ALLOCATE

        # CAN_ALLOCATE -> CAN_LOCK: Check if route can be locked
        elif (route.transition == RouteTransition.CAN_ALLOCATE
              and route.mode == RouteMode.ALLOCATING
              and all(signal.ACT == SignalAspect.STOP for signal in route.protecting_signals)
              and all(point.ACT == route.point_positions[point]
                     for point in route.points)
              and all(elem.mode == ElementMode.EXLOCKED for elem in route.path)
              and all(elem.is_vacant() for elem in route.path)):
            route.transition = RouteTransition.CAN_LOCK

        # CAN_LOCK -> CAN_OCCUPY: Check if train can enter route
        elif (route.transition == RouteTransition.CAN_LOCK
              and route.mode == RouteMode.LOCKED
              and route.source_signal.ACT == SignalAspect.GO
              and route.path[0].is_vacant()):  # First element is free
            route.transition = RouteTransition.CAN_OCCUPY

        # CAN_OCCUPY -> CAN_DISPATCH: Route released, ready for next request
        elif (route.transition == RouteTransition.CAN_OCCUPY
              and route.mode == RouteMode.FREE):
            route.transition = RouteTransition.CAN_DISPATCH

        return route.transition != old_transition

    def update_route_mode(self, route: Route) -> bool:
        """Update route mode based on transition state"""
        old_mode = route.mode

        # FREE -> MARKED: Non-deterministic route request
        if (route.mode == RouteMode.FREE
            and route.transition == RouteTransition.CAN_DISPATCH):
            route.mode = RouteMode.MARKED

        # MARKED -> ALLOCATING: Allocate route resources
        elif (route.mode == RouteMode.MARKED
              and route.transition == RouteTransition.CAN_ALLOCATE
              and not any(conflicting.mode in {RouteMode.ALLOCATING, RouteMode.LOCKED}
                         for conflicting in route.conflicting_routes)
              and all(elem.is_vacant() for elem in route.path)):
            route.mode = RouteMode.ALLOCATING

        # ALLOCATING -> LOCKED: Lock route for train entry
        elif (route.mode == RouteMode.ALLOCATING
              and route.transition == RouteTransition.CAN_LOCK
              and all(elem.mode == ElementMode.EXLOCKED for elem in route.path)
              and all(elem.is_vacant() for elem in route.path)):
            route.mode = RouteMode.LOCKED

        # LOCKED -> OCCUPIED: Train enters route
        elif (route.mode == RouteMode.LOCKED
              and route.transition == RouteTransition.CAN_OCCUPY
              and route.source_signal.ACT == SignalAspect.GO
              and route.path[0].is_vacant()):
            route.mode = RouteMode.OCCUPIED

        # OCCUPIED -> FREE: Train completes route, release
        elif (route.mode == RouteMode.OCCUPIED
              and route.path[-1].mode == ElementMode.USED
              and route.path[-1].has_train_at_destination()):
            route.mode = RouteMode.FREE

        return route.mode != old_mode
```

3. Element Mode Management (Sectional Release):
   - Elements transition through: AVAILABLE → EXLOCKED → USED → AVAILABLE.
   - The wave pattern ensures sequential release as train progresses.

```py
    def update_element_mode(self, route: Route, elem: Element) -> bool:
        """Update element lock mode for sectional release"""
        old_mode = elem.mode
        elem_idx = route.path.index(elem)

        # AVAILABLE -> EXLOCKED: Lock element when route is allocating
        if (elem.mode == ElementMode.AVAILABLE
            and route.mode == RouteMode.ALLOCATING):
            elem.mode = ElementMode.EXLOCKED

        # EXLOCKED -> USED: Set element in use when wave reaches it
        elif (elem.mode == ElementMode.EXLOCKED
              and route.mode == RouteMode.OCCUPIED
              and elem.is_vacant()):
            # Previous element must be USED, next element must be EXLOCKED
            if elem_idx > 0 and elem_idx < len(route.path) - 1:
                prev_elem = route.path[elem_idx - 1]
                next_elem = route.path[elem_idx + 1]
                if prev_elem.mode == ElementMode.USED and next_elem.mode == ElementMode.EXLOCKED:
                    elem.mode = ElementMode.USED
            # First element: no previous, just check next is EXLOCKED
            elif elem_idx == 0 and len(route.path) > 1:
                next_elem = route.path[1]
                if next_elem.mode == ElementMode.EXLOCKED:
                    elem.mode = ElementMode.USED
            # Last element: check previous is USED
            elif elem_idx == len(route.path) - 1 and elem_idx > 0:
                prev_elem = route.path[elem_idx - 1]
                if prev_elem.mode == ElementMode.USED:
                    elem.mode = ElementMode.USED

        # USED -> AVAILABLE: Release element when train has passed
        elif (elem.mode == ElementMode.USED
              and route.mode == RouteMode.OCCUPIED
              and elem.is_vacant()
              and elem.prev == PrevState.RELEASED):
            # Next element must be USED or have PENDING prev
            if elem_idx < len(route.path) - 1:
                next_elem = route.path[elem_idx + 1]
                if next_elem.mode == ElementMode.USED or next_elem.prev == PrevState.PENDING:
                    elem.mode = ElementMode.AVAILABLE
            # Last element can release directly
            else:
                elem.mode = ElementMode.AVAILABLE

        return elem.mode != old_mode

    def update_element_prev(self, route: Route, elem: Element) -> bool:
        """Update element PREV flag to track train passage"""
        old_prev = elem.prev
        elem_idx = route.path.index(elem)

        # PENDING -> RELEASED: Mark released when previous element is vacant
        if (elem.prev == PrevState.PENDING
            and elem.mode == ElementMode.USED
            and route.mode == RouteMode.OCCUPIED
            and elem_idx > 0):
            prev_elem = route.path[elem_idx - 1]
            if (prev_elem.mode == ElementMode.AVAILABLE
                and prev_elem.prev == PrevState.PENDING
                and prev_elem.is_vacant()):
                elem.prev = PrevState.RELEASED

        return elem.prev != old_prev
```

4. Train Movement and Occupancy Updates:
   - Train movement is non-deterministic in the SMV model.
   - Occupancy transitions follow head/tail propagation rules.
   - Movement respects signal aspects and point positions.

```py
    def process_train_movement(self) -> bool:
        """
        Process train movement through track elements.
        Implements non-deterministic movement based on:
        - Signal aspects (GO/STOP)
        - Point positions (NORMAL/REVERSE)
        - Current occupancy states
        """
        changed = False
        next_occupancy = {}

        # Linear sections: bidirectional movement (UP/DOWN)
        for linear in self.sections:
            # UP direction: head/tail movement
            if linear.up_neighbor and linear.up_signal:
                if linear.up_signal.ACT == SignalAspect.GO:
                    # Head enters next element
                    if linear.occUp in {ElementOcc.HEADOCC, ElementOcc.COMPLETETRAINOCC}:
                        next_occupancy[(linear.up_neighbor, 'entry')] = move_head_enters(linear.occUp)
                        next_occupancy[(linear, 'up')] = move_head_leaves(linear.occUp)
                    # Tail follows
                    elif linear.occUp == ElementOcc.TAILOCC:
                        next_occupancy[(linear.up_neighbor, 'entry')] = move_tail_enters()
                        next_occupancy[(linear, 'up')] = ElementOcc.FREE

            # DOWN direction: symmetric to UP
            if linear.down_neighbor and linear.down_signal:
                if linear.down_signal.ACT == SignalAspect.GO:
                    if linear.occDown in {ElementOcc.HEADOCC, ElementOcc.COMPLETETRAINOCC}:
                        next_occupancy[(linear.down_neighbor, 'entry')] = move_head_enters(linear.occDown)
                        next_occupancy[(linear, 'down')] = move_head_leaves(linear.occDown)
                    elif linear.occDown == ElementOcc.TAILOCC:
                        next_occupancy[(linear.down_neighbor, 'entry')] = move_tail_enters()
                        next_occupancy[(linear, 'down')] = ElementOcc.FREE

        # Points: three-way movement (STEM-NORMAL-REVERSE)
        for point in self.points:
            # Movement from STEM based on point position
            if point.ACT == PointAspect.NORMAL and point.normal_neighbor:
                if point.occSNR in {ElementOcc.HEADOCC, ElementOcc.COMPLETETRAINOCC}:
                    next_occupancy[(point.normal_neighbor, 'entry')] = move_head_enters(point.occSNR)
                    next_occupancy[(point, 'snr')] = move_head_leaves(point.occSNR)
                elif point.occSNR == ElementOcc.TAILOCC:
                    next_occupancy[(point.normal_neighbor, 'entry')] = move_tail_enters()
                    next_occupancy[(point, 'snr')] = ElementOcc.FREE

            elif point.ACT == PointAspect.REVERSE and point.reverse_neighbor:
                if point.occSNR in {ElementOcc.HEADOCC, ElementOcc.COMPLETETRAINOCC}:
                    next_occupancy[(point.reverse_neighbor, 'entry')] = move_head_enters(point.occSNR)
                    next_occupancy[(point, 'snr')] = move_head_leaves(point.occSNR)
                elif point.occSNR == ElementOcc.TAILOCC:
                    next_occupancy[(point.reverse_neighbor, 'entry')] = move_tail_enters()
                    next_occupancy[(point, 'snr')] = ElementOcc.FREE

            # Movement from NORMAL/REVERSE to STEM (trailing movements)
            # ... (similar logic for occNS and occRS)

        # Apply all occupancy updates atomically
        for (elem, direction), new_occ in next_occupancy.items():
            if apply_occupancy_update(elem, direction, new_occ):
                changed = True

        return changed

# Helper functions for occupancy state transitions
def move_head_enters(current_occ):
    """When head enters element"""
    if current_occ == ElementOcc.COMPLETETRAINOCC:
        return ElementOcc.HEADOCC
    return ElementOcc.HEADOCC

def move_head_leaves(current_occ):
    """When head leaves element"""
    if current_occ == ElementOcc.COMPLETETRAINOCC:
        return ElementOcc.TAILOCC
    elif current_occ == ElementOcc.HEADOCC:
        return ElementOcc.FREE
    return current_occ

def move_tail_enters():
    """When tail enters element"""
    return ElementOcc.TAILOCC

def move_tail_leaves():
    """When tail leaves element"""
    return ElementOcc.FREE
```

5. Signal and Point Updates:
   - Signals and points communicate commanded aspects to actual state.

```py
    def update_signal_aspect(self, signal: Signal) -> bool:
        """Update signal actual aspect based on command"""
        if signal.ACT != signal.CMD:
            signal.ACT = signal.CMD
            return True
        return False

    def update_point_position(self, point: Point) -> bool:
        """Update point actual position based on command"""
        # Transition through INTERMEDIATE state
        if point.ACT != point.CMD and point.ACT != PointAspect.INTERMEDIATE:
            point.ACT = PointAspect.INTERMEDIATE
            return True
        elif point.ACT == PointAspect.INTERMEDIATE:
            point.ACT = point.CMD
            return True
        return False
```