from typing import Optional
from entity import Direction, Linear, Point, PointFace, Route, Section


# ==================== ROUTE OPERATIONS ====================
def first_element(route: Route) -> Optional[Section]:
    """Get the first element in the route path"""
    return route.path[0] if route.path else None

def last_element(route: Route) -> Optional[Section]:
    """Get the last element in the route path"""
    return route.path[-1] if route.path else None

def next_element(route: Route, element: Section) -> Optional[Section]:
    """Get the next element after the given element in the route"""
    try:
        idx = route.path.index(element)
        if idx < len(route.path) - 1:
            return route.path[idx + 1]
    except (ValueError, IndexError):
        pass
    return None

def prev_element(route: Route, element: Section) -> Optional[Section]:
    """Get the previous element before the given element in the route"""
    try:
        idx = route.path.index(element)
        if idx > 0:
            return route.path[idx - 1]
    except (ValueError, IndexError):
        pass
    return None

def get_conn_end_dir(element: Section, neighbor: Section):
    """
    Return the end identifier for element connected to neighbor.

    Linear sections returns Direction.DOWN/UP.
    Point sections returns PointAspect.STEM/NORMAL/REVERSE.
    """
    if isinstance(element, Linear):
        if element.down_neighbor is neighbor:
            return Direction.DOWN

        if element.up_neighbor is neighbor:
            return Direction.UP

        return None
    elif isinstance(element, Point):
        if element.stem_neighbor is neighbor:
            return PointFace.SNR

        if element.normal_neighbor is neighbor:
            return PointFace.NS

        if element.reverse_neighbor is neighbor:
            return PointFace.RS

        return None
    return None

def get_occ_by_end(element: Section, end):
    """Get occupancy value from element by end identifier"""
    if isinstance(element, Linear):
        if end == Direction.DOWN:
            return element.occDown

        if end == Direction.UP:
            return element.occUp
    elif isinstance(element, Point):
        if end == PointFace.SNR:
            return element.occSNR

        if end == PointFace.NS:
            return element.occNS

        if end == PointFace.RS:
            return element.occRS
    return None

def set_occ_by_end(element: Section, end, value: str) -> None:
    """Set occupancy value on element for the specified end"""
    if isinstance(element, Linear):
        if end == Direction.DOWN:
            element.occDown = value
            return

        if end == Direction.UP:
            element.occUp = value
            return
    elif isinstance(element, Point):
        if end == PointFace.SNR:
            element.occSNR = value
            return

        if end == PointFace.NS:
            element.occNS = value
            return

        if end == PointFace.RS:
            element.occRS = value
            return