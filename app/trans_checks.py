from entity import (Direction, ElementMode, ElementOcc, Linear, Point,
                    PointAspect, Route, RouteMode, Signal, SignalAspect)
from route_op import first_element, next_element
from utils import vacant


# ==================== TRANSITION CHECKS ====================
def _get_approach_occ(route: Route):
    """Return occupancy of the first route element in the entry direction.

    The approach segment is the first element of the route path. A train must
    be present there (HEADOCC or COMPLETETRAINOCC) before the route is dispatched.
    Returns None if the approach cannot be determined.
    """
    first = first_element(route)

    if first is None:
        return None

    if isinstance(first, Linear):
        return first.occDown if route.entry_dir == Direction.DOWN else first.occUp

    # Points as first elements: check stem face for DOWN, normal/reverse branch otherwise
    if isinstance(first, Point):
        return first.occSNR if route.entry_dir == Direction.DOWN else first.occNS

    return None

def can_dispatch_route(route: Route) -> bool:
    """Check if the route can be dispatched (FREE -> MARKED).

    Requires a train present in the approach segment (first route element).
    Without this check every FREE route would dispatch immediately on every step.
    """
    if route.MODE != RouteMode.FREE:
        return False

    approach_occ = _get_approach_occ(route)

    if approach_occ is not None and approach_occ == ElementOcc.FREE:
        return False

    return True

def can_allocate_route(route: Route) -> bool:
    """Check if route can be allocated (MARKED -> ALLOCATING)"""
    if route.MODE != RouteMode.MARKED:
        return False

    """
    # Check no conflicting routes are being set up (ALLOCATING or LOCKED).
    
    OCCUPIED is not excluded here: the element vacancy check below already prevents allocation
                                   while a conflict route's train occupies shared elements.
    """
    for cr in route.conflicts:
        if cr.MODE in [RouteMode.ALLOCATING, RouteMode.LOCKED]:
            return False

    """
    # C3: HAS TRAIN variant - first element may be occupied by the waiting train.
    Only check elements AFTER the first for vacancy.
    """
    first = route.path[0] if route.path else None

    for elem in route.path:
        if elem is first:
            continue   # train starts here; skip vacancy check

        if not vacant(elem):
            return False

    for elem in route.overlap:
        if not vacant(elem):
            return False

    # All path elements must be AVAILABLE (train's starting element included)
    for elem in route.path:
        if elem.MODE != ElementMode.AVAILABLE:
            return False

    # Overlap elements must not be USED
    for elem in route.overlap:
        if elem.MODE == ElementMode.USED:
            return False

    # Protecting points outside path must be AVAILABLE or already correct
    for point, req_pos in route.points.items():
        if point not in route.path:
            if point.MODE != ElementMode.AVAILABLE and point.ACT != req_pos:
                return False

    return True

def can_lock_route(route: Route) -> bool:
    """Check if route can be locked (ALLOCATING -> LOCKED)"""
    if route.MODE != RouteMode.ALLOCATING:
        return False

    """
    # Conflict exclusion: mirrors SMV fix #6
        - prevents two conflicting routes from both reaching LOCKED in the same step
          during the point actuator lag window.
    """
    for cr in route.conflicts:
        if cr.MODE in [RouteMode.ALLOCATING, RouteMode.LOCKED]:
            return False

    # Flank protecting signals must show STOP
    for signal in route.signals:
        if signal.ACT != SignalAspect.STOP:
            return False

    # Points must be in the required position
    for point, req_pos in route.points.items():
        if point.ACT != req_pos:
            return False

    """
    # C4: HAS TRAIN variant - first element may be occupied by the waiting train.
    Only check elements AFTER the first for vacancy.
    """
    first = route.path[0] if route.path else None
    for elem in route.path:
        if elem is first:
            continue   # train occupies entry element; skip vacancy check

        if not vacant(elem):
            return False

    for elem in route.overlap:
        if not vacant(elem):
            return False

    # All path elements must be EXLOCKED
    for elem in route.path:
        if elem.MODE != ElementMode.EXLOCKED:
            return False

    return True

def can_set_route_in_use(route: Route) -> bool:
    """Check if route can be set in use (LOCKED -> OCCUPIED)"""
    if route.MODE != RouteMode.LOCKED:
        return False

    # H5: Entry signal must be GO before the train may enter
    entry_sig = route.entry_signal

    if isinstance(entry_sig, Signal) and entry_sig.ACT != SignalAspect.GO:
        return False

    # Train must be present at the entry element in the correct direction
    first = first_element(route)

    if first is None:
        return False

    dir = route.entry_dir

    if isinstance(first, Linear):
        # HAS TRAIN variant: train waits at the first Linear element, signal gates exit
        occ = first.occDown if dir == Direction.DOWN else first.occUp

        return occ in [ElementOcc.COMPLETETRAINOCC, ElementOcc.HEADOCC]
    elif isinstance(first, Point):
        req_pos = route.points.get(first)
        nxt = next_element(route, first)

        """
        If the next path element is the stem neighbor, the train exits via stem.
            - meaning it entered from a branch face (NS or RS).
        Otherwise it entered from the stem face (SNR): the "fork" topology case.
        """
        next_is_via_stem = (nxt is not None and nxt is first.stem_neighbor)

        if next_is_via_stem:
            occ = first.occNS if (req_pos is None or req_pos == PointAspect.NORMAL) else first.occRS
        else:
            occ = first.occSNR
        return occ != ElementOcc.FREE

    return False