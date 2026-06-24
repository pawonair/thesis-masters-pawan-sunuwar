from entity import Direction, ElementOcc, Linear, Point, PointFace, Section


# ==================== UTILITY FUNCTIONS ====================
def occupied_with_head(elem_occ: ElementOcc) -> bool:
    """Check if section is occupied with a head"""
    return elem_occ == ElementOcc.HEADOCC

def occupied_without_head(elem_occ: ElementOcc) -> bool:
    """Check if section is occupied without a head"""
    return elem_occ in [ElementOcc.COMPLETETRAINOCC, ElementOcc.TAILOCC]

def occupied_with_only_tail(elem_occ: ElementOcc) -> bool:
    """Check if section is occupied with only the tail"""
    return elem_occ == ElementOcc.TAILOCC

def occupied_without_tail(elem_occ: ElementOcc) -> bool:
    """Check if section is occupied without a tail"""
    return elem_occ in [ElementOcc.HEADOCC, ElementOcc.COMPLETETRAINOCC]

def head_can_advance(elem_occ: ElementOcc) -> bool:
    """Check if train head can advance (present as HEADOCC or COMPLETETRAINOCC)"""
    return elem_occ in [ElementOcc.HEADOCC, ElementOcc.COMPLETETRAINOCC]

def head_enters(element: Section, elem_occ: ElementOcc, elem_dir) -> ElementOcc:
    """Set head occupancy on the given end if free and return new occ"""
    if elem_occ == ElementOcc.FREE:
        if isinstance(element, Linear):
            if elem_dir == Direction.DOWN:
                element.occDown = ElementOcc.HEADOCC
            else: # UP
                element.occUp = ElementOcc.HEADOCC
        elif isinstance(element, Point):
            if elem_dir == PointFace.SNR:
                element.occSNR = ElementOcc.HEADOCC
            elif elem_dir == PointFace.NS:
                element.occNS = ElementOcc.HEADOCC
            else:  # RS
                element.occRS = ElementOcc.HEADOCC
        return ElementOcc.HEADOCC

    return ElementOcc.ERROROCC

def head_leaves(element: Section, elem_dir) -> ElementOcc:
    """Head has the left segment; tail remains -> TAILOCC (C1: was COMPLETETRAINOCC)"""
    if isinstance(element, Linear):
        if elem_dir == Direction.DOWN:
            element.occDown = ElementOcc.TAILOCC
        else: # UP
            element.occUp = ElementOcc.TAILOCC
    elif isinstance(element, Point):
        if elem_dir == PointFace.SNR:
            element.occSNR = ElementOcc.TAILOCC
        elif elem_dir == PointFace.NS:
            element.occNS = ElementOcc.TAILOCC
        else:  # RS
            element.occRS = ElementOcc.TAILOCC

    return ElementOcc.TAILOCC

def tail_enters(element: Section, elem_occ: ElementOcc, elem_dir) -> ElementOcc:
    """Tail arrives at the segment; valid only when head is present (HEADOCC) -> TAILOCC"""
    if elem_occ == ElementOcc.HEADOCC:
        # Head moved forward in the same step; tail occupies vacated end -> TAILOCC
        if isinstance(element, Linear):
            if elem_dir == Direction.DOWN:
                element.occDown = ElementOcc.TAILOCC
            else: # UP
                element.occUp = ElementOcc.TAILOCC
        elif isinstance(element, Point):
            if elem_dir == PointFace.SNR:
                element.occSNR = ElementOcc.TAILOCC
            elif elem_dir == PointFace.NS:
                element.occNS = ElementOcc.TAILOCC
            else:  # RS
                element.occRS = ElementOcc.TAILOCC
        return ElementOcc.TAILOCC

    return ElementOcc.ERROROCC

def tail_leaves(element: Section, elem_dir) -> ElementOcc:
    """Set tail occupancy free on the given end and return new occ"""
    if isinstance(element, Linear):
        if elem_dir == Direction.DOWN:
            element.occDown = ElementOcc.FREE
        else: # UP
            element.occUp = ElementOcc.FREE
    elif isinstance(element, Point):
        if elem_dir == PointFace.SNR:
            element.occSNR = ElementOcc.FREE
        elif elem_dir == PointFace.NS:
            element.occNS = ElementOcc.FREE
        else:  # RS
            element.occRS = ElementOcc.FREE

    return ElementOcc.FREE

def vacant_linear(section: Linear) -> bool:
    """Check if a linear section is vacant"""
    return section.occDown == ElementOcc.FREE and section.occUp == ElementOcc.FREE

def vacant_point(section: Point) -> bool:
    """Check if a point section is vacant"""
    return (section.occSNR == ElementOcc.FREE and
            section.occNS == ElementOcc.FREE and
            section.occRS == ElementOcc.FREE)

def vacant(section: Section) -> bool:
    """Check if a section is vacant"""
    if isinstance(section, Linear):
        return vacant_linear(section)
    elif isinstance(section, Point):
        return vacant_point(section)

    return True

def occupied(section: Section) -> bool:
    """Check if a section has a train head present (HEADOCC or COMPLETETRAINOCC).

    Used for PREV state transitions:
        - PREV is RELEASED when the train head has physically entered the element.
        - TAILOCC alone does not count.
    """
    _present = (ElementOcc.HEADOCC, ElementOcc.COMPLETETRAINOCC)

    if isinstance(section, Linear):
        return section.occDown in _present or section.occUp in _present
    elif isinstance(section, Point):
        return (section.occSNR in _present or
                section.occNS in _present or
                section.occRS in _present)

    return False

def swap_up_down_vars(section: Linear) -> None:
    """Swap values of occupancy status variables in a linear section"""
    section.occDown, section.occUp = section.occUp, section.occDown

def can_turn_around_at(element: Section) -> bool:
    """Check if trains can change direction at a section"""
    return (isinstance(element, Linear) and 
            element.down_signal is not None and 
            element.up_signal is not None)

def is_boundary_sec_down(element: Section) -> bool:
    """Check if element is a boundary section in the downward direction"""
    if not isinstance(element, Linear):
        return False

    return (element.down_neighbor is None and
            element.up_signal is None and 
            element.down_signal is not None and
            element.up_neighbor is not None and
            isinstance(element.up_neighbor, Linear))

def is_boundary_sec_up(element: Section) -> bool:
    """Check if element is a boundary section in the upward direction"""
    if not isinstance(element, Linear):
        return False

    return (element.up_neighbor is None and
            element.down_signal is None and 
            element.up_signal is not None and
            element.down_neighbor is not None and
            isinstance(element.down_neighbor, Linear))

def is_boundary_sec(element: Section) -> bool:
    """Check if element is a boundary section"""
    return is_boundary_sec_down(element) or is_boundary_sec_up(element)