"""
=======================================================
Description: Generic behavioral model of SWTbahn
             interlocking systems
=======================================================
Route states: FREE, MARKED, ALLOCATING, LOCKED, OCCUPIED
Signals aspect: GO, STOP
Point aspect: NORMAL, REVERSE, INTERMEDIATE
Element modes: AVAILABLE, EXLOCKED, USED
"""

from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import List, Optional, Set, Union


# ==================== CONSTANTS ====================
class RouteMode(StrEnum):
    """Route state constants"""
    FREE = auto()
    MARKED = auto()
    ALLOCATING = auto()
    LOCKED = auto()
    OCCUPIED = auto()

class SignalAspect(StrEnum):
    """Signal aspect constants"""
    GO = auto()
    STOP = auto()

class SignalCommand(StrEnum):
    """Signal command constants"""
    GO = auto()
    STOP = auto()

class PointAspect(StrEnum):
    """Point position constants"""
    STEM = auto()
    NORMAL = auto()
    REVERSE = auto()
    INTERMEDIATE = auto()

class PointCommand(StrEnum):
    """Point aspect command constants"""
    NORMAL = auto()
    REVERSE = auto()

class PointFace(StrEnum):
    """Point face identifiers for occupancy tracking (distinct from a commanded aspect)"""
    SNR = auto()   # stem face  (occSNR: SNR-direction trains)
    NS  = auto()   # normal branch face (occNS)
    RS  = auto()   # reverse branch face (occRS)

class ElementMode(StrEnum):
    """Element mode constants"""
    AVAILABLE = auto()
    EXLOCKED = auto()
    USED = auto()

class ElementOcc(StrEnum):
    """Element occupancy constants"""
    FREE = auto()
    HEADOCC = auto()
    COMPLETETRAINOCC = auto()
    TAILOCC = auto()
    ERROROCC = auto()

class PrevState(StrEnum):
    """Previous element release state"""
    PENDING = auto()
    RELEASED = auto()

class Direction(StrEnum):
    """Direction constants"""
    DOWN = auto()
    UP = auto()


# ==================== ELEMENT CLASSES ====================
@dataclass
class Linear:
    """
    Linear track section
    --------------------
    occupancy status for a direction:
        - occDown: {FREE, HEADOCC, COMPLETETRAINOCC, TAILOCC, ERROROCC}
        - occUp: {FREE, HEADOCC, COMPLETETRAINOCC, TAILOCC, ERROROCC}
    MODE: current mode of the element
    PREV: whether the previous element in the same route has been released
    """
    name: str
    occDown: ElementOcc = ElementOcc.FREE
    occUp: ElementOcc = ElementOcc.FREE
    MODE: ElementMode = ElementMode.AVAILABLE
    PREV: PrevState = PrevState.PENDING
    
    # Connections
    down_neighbor: Optional['Section'] = None
    up_neighbor: Optional['Section'] = None
    down_signal: Optional['Signal'] = None
    up_signal: Optional['Signal'] = None

    def __hash__(self):
        return hash(self.name)

@dataclass
class Point:
    """
    Point section
    --------------------
    occSNR: occupancy status for the direction from stem to normal/reverse
    occNS: occupancy status for the direction from normal to stem
    occRS: occupancy status for the direction from reverse to stem
    CMD: commanded position of the point
    ACT: actual position of the point
    MODE: current mode of the element
    PREV: whether the previous element in the same route has been released
    """
    name: str
    segName: Optional[str] = None
    occSNR: ElementOcc = ElementOcc.FREE
    occNS: ElementOcc = ElementOcc.FREE
    occRS: ElementOcc = ElementOcc.FREE
    CMD: PointAspect = PointAspect.NORMAL
    ACT: PointAspect = PointAspect.NORMAL
    MODE: ElementMode = ElementMode.AVAILABLE
    PREV: PrevState = PrevState.PENDING
    
    # Connections
    stem_neighbor: Optional['Section'] = None
    normal_neighbor: Optional['Section'] = None
    reverse_neighbor: Optional['Section'] = None

    def __hash__(self):
        return hash(self.name)

@dataclass
class Signal:
    """
    Signal element
    --------------------
    ACT: actual aspect of the signal
    CMD: commanded aspect of the signal
    """
    name: str
    ACT: SignalAspect = SignalAspect.STOP
    CMD: SignalCommand = SignalCommand.STOP

@dataclass
class Route:
    """
    Route element
    --------------------
    MODE: current mode of the route (internal)
    """
    name: str
    MODE: RouteMode = RouteMode.FREE
    
    # Route configuration
    path: List['Section'] = field(default_factory=list)
    overlap: List['Section'] = field(default_factory=list)
    points: dict = field(default_factory=dict) # Point -> required position
    signals: List[Signal] = field(default_factory=list)
    conflicts: Set['Route'] = field(default_factory=set)
    entry_signal: Optional[Signal] = None
    exit_signal: Optional[Signal] = None
    entry_dir: Direction = Direction.DOWN

    def __hash__(self):
        return hash(self.name)

# Type alias for sections
Section = Union[Linear, Point]
