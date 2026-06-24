from typing import List

from entity import (Direction, ElementOcc, Linear, Point, PointAspect, PointFace,
                    Route, RouteMode, Section, Signal, SignalAspect)
from route_op import get_conn_end_dir, get_occ_by_end, set_occ_by_end
from trans import (allocate_route, dispatch_route, lock_route,
                   release_last_element_and_route, sequential_release_element,
                   set_element_in_use, set_route_in_use, update_route_prev_states)
from utils import head_can_advance, is_boundary_sec


# ==================== POINT SWITCHING ====================
def start_point_switching(point: Point) -> bool:
    """Start switching a point (move to INTERMEDIATE position)"""
    if point.ACT != point.CMD and point.ACT != PointAspect.INTERMEDIATE:
        point.ACT = PointAspect.INTERMEDIATE
        return True

    return False


def complete_point_switching(point: Point) -> bool:
    """Complete switching a point (move to commanded position)"""
    if point.ACT == PointAspect.INTERMEDIATE:
        point.ACT = point.CMD
        return True

    return False


# ==================== SIGNAL COMMUNICATION ====================
def communicate_signal_aspect(signal: Signal) -> bool:
    """Update signal actual aspect to match commanded aspect"""
    if signal.ACT != signal.CMD:
        signal.ACT = signal.CMD
        return True

    return False


# ==================== INTERLOCKING SYSTEM ====================
class InterlockingSystem:
    """Main interlocking system class"""

    def __init__(self):
        self.routes: List[Route] = []
        self.sections: List[Section] = []
        self.signals: List[Signal] = []
        self.points: List[Point] = []

    def add_route(self, route: Route) -> None:
        """Add a route to the system"""
        self.routes.append(route)

    def add_section(self, section: Section) -> None:
        """Add a section to the system"""
        if isinstance(section, Linear):
            self.sections.append(section)

        if isinstance(section, Point):
            self.points.append(section)

    def add_signal(self, signal: Signal) -> None:
        """Add a signal to the system"""
        self.signals.append(signal)

    def safety_violations(self) -> List[str]:
        """Collect all safety violations as per-element diagnostic strings.

        Single source of truth for safety checking. Returns one string per
        violation; an empty list means safe.
        """
        errors: List[str] = []
        _TRAIN_HEAD = (ElementOcc.HEADOCC, ElementOcc.COMPLETETRAINOCC)
        _TRAIN_TAIL = (ElementOcc.TAILOCC, ElementOcc.COMPLETETRAINOCC)
        _TRAIN_ON_FACE = (ElementOcc.HEADOCC, ElementOcc.COMPLETETRAINOCC, ElementOcc.TAILOCC)
        _ACTIVE_ROUTE = (RouteMode.ALLOCATING, RouteMode.LOCKED)

        for l in self.sections:
            if not isinstance(l, Linear):
                continue
            if l.occDown == ElementOcc.ERROROCC:
                errors.append(f"ERROROCC on {l.name}.occDown")
            if l.occUp == ElementOcc.ERROROCC:
                errors.append(f"ERROROCC on {l.name}.occUp")

            if not is_boundary_sec(l):
                if l.occDown in _TRAIN_ON_FACE and l.occUp in _TRAIN_ON_FACE:
                    errors.append(f"Head-to-head collision on {l.name}")

            # Head-to-tail: a tail in `l` means a follower (in the same direction)
            # would be approaching from the segment BEHIND `l` in the travel direction.
            # For UP: behind = l.down_neighbor; for DOWN: behind = l.up_neighbor.
            # Linear->Point limitation: get_conn_end_dir only inspects the face of the
            # point that physically touches l, not the branch-to-stem faces that a
            # follower would actually occupy. Follower detection across points is
            # therefore approximate.
            if l.occUp in _TRAIN_TAIL and l.down_neighbor is not None:
                nx = l.down_neighbor
                nx_end = get_conn_end_dir(nx, l)
                nx_occ = get_occ_by_end(nx, nx_end) if nx_end is not None else None
                if nx_occ in _TRAIN_HEAD:
                    errors.append(
                        f"Head-to-tail collision (UP): follower head in {nx.name}"
                        f" approaching {l.name}.occUp"
                    )

            if l.occDown in _TRAIN_TAIL and l.up_neighbor is not None:
                nx = l.up_neighbor
                nx_end = get_conn_end_dir(nx, l)
                nx_occ = get_occ_by_end(nx, nx_end) if nx_end is not None else None
                if nx_occ in _TRAIN_HEAD:
                    errors.append(
                        f"Head-to-tail collision (DOWN): follower head in {nx.name}"
                        f" approaching {l.name}.occDown"
                    )

        for p in self.points:
            for face_name, occ in [('SNR', p.occSNR), ('NS', p.occNS), ('RS', p.occRS)]:
                if occ == ElementOcc.ERROROCC:
                    errors.append(f"ERROROCC on {p.name}.occ{face_name}")

            occupied_faces = sum(
                1 for occ in (p.occSNR, p.occNS, p.occRS)
                if occ in _TRAIN_ON_FACE
            )
            if occupied_faces > 1:
                errors.append(f"Multi-face collision on {p.name}")

            if p.occNS in _TRAIN_ON_FACE and p.ACT != PointAspect.NORMAL:
                errors.append(f"Derailment {p.name}: train on NS face but ACT={p.ACT}")
            if p.occRS in _TRAIN_ON_FACE and p.ACT != PointAspect.REVERSE:
                errors.append(f"Derailment {p.name}: train on RS face but ACT={p.ACT}")
            if p.occSNR in _TRAIN_ON_FACE and p.ACT == PointAspect.INTERMEDIATE:
                errors.append(f"Derailment {p.name}: train on SNR face but ACT=INTERMEDIATE")

        reported_pairs: set = set()
        for r in self.routes:
            if r.MODE not in _ACTIVE_ROUTE:
                continue
            for cr in r.conflicts:
                if cr.MODE not in _ACTIVE_ROUTE:
                    continue
                pair = frozenset({r.name, cr.name})
                if pair in reported_pairs:
                    continue
                reported_pairs.add(pair)
                errors.append(
                    f"Conflicting routes both active: {r.name} ({r.MODE})"
                    f" vs {cr.name} ({cr.MODE})"
                )

        return errors

    def verify_safety_properties(self) -> dict:
        """Verify high-level safety properties (derived from safety_violations)."""
        violations = self.safety_violations()
        return {
            'no_head_to_head_collisions_linear':
                not any(v.startswith('Head-to-head') for v in violations),
            'no_head_to_tail_collisions_linear':
                not any(v.startswith('Head-to-tail') for v in violations),
            'no_derailments':
                not any(v.startswith('Derailment') for v in violations),
            'conflicting_routes_not_set':
                not any(v.startswith('Conflicting routes') for v in violations),
        }

    def step(self) -> bool:
        """Execute one step of the interlocking system"""
        changed = False

        # Process route state transitions
        for route in self.routes:
            if dispatch_route(route):
                changed = True
                print(f"# {route.name}: {route.MODE}")
            elif allocate_route(route):
                changed = True
                print(f"# {route.name}: {route.MODE}")
            elif lock_route(route):
                changed = True
                print(f"# {route.name}: {route.MODE}")
            elif set_route_in_use(route):
                changed = True
                print(f"# {route.name}: {route.MODE}")

        # Set intermediate elements in use
        for route in self.routes:
            print(f"Setting route {route.name} elements in use:")
            for elem in route.path:
                if set_element_in_use(route, elem):
                    changed = True
                    print(f"  - {elem.name}: MODE: {elem.MODE}, PREV: {elem.PREV}")
            print(f"------------------------")

        # Train movement
        if self.process_train_movement():
            changed = True
            print(f"Starting train traversal.")
            print(f"------------------------")

        # Sequential release for all elements (except last)
        for route in self.routes:
            print(f"Releasing route {route.name} elements:")
            for elem in route.path:
                if sequential_release_element(route, elem):
                    changed = True
                    print(f"  - {elem.name}: MODE: {elem.MODE}, PREV: {elem.PREV}")
            print(f"------------------------")

        # Release the last element and free the route
        for route in self.routes:
            if release_last_element_and_route(route):
                print(f"Releasing route {route.name}: {route.MODE}")
                changed = True

        """
        # H4: Point CMD is set during ALLOCATING (in allocate_route).
            Do NOT re-set CMD during OCCUPIED: mid-transit switching causes ERROROCC.
            Propagate `CMD -> ACT` (1-step lag)
        """
        for point in self.points:
            if start_point_switching(point):
                changed = True
            elif complete_point_switching(point):
                changed = True

        print(f"Starting signal communication:")
        # Process signal communication
        for signal in self.signals:
            if communicate_signal_aspect(signal):
                changed = True
            print(f"  - {signal.name}: {signal.ACT}")

        return changed

    def process_train_movement(self) -> bool:
        # Snapshot all occupancy at the start of the step (`prev_occ`)
        prev_occ = {}

        for seg in self.sections:  # Linear only
            prev_occ[(seg, Direction.DOWN)] = seg.occDown
            prev_occ[(seg, Direction.UP)] = seg.occUp

        for pt in self.points:  # Points
            prev_occ[(pt, PointFace.SNR)] = pt.occSNR
            prev_occ[(pt, PointFace.NS)] = pt.occNS
            prev_occ[(pt, PointFace.RS)] = pt.occRS

        # Start `next_occ` as a copy of the current state
        next_occ = dict(prev_occ)

        def p(elem, end):
            """Read from the `prev_occ` snapshot (never from the live element)."""
            return prev_occ.get((elem, end), ElementOcc.FREE)

        def head_move(src_key, dst_key):
            """Record: head leaves src (-> TAILOCC), head enters dst (-> HEADOCC)."""
            next_occ[src_key] = ElementOcc.TAILOCC
            next_occ[dst_key] = ElementOcc.HEADOCC

        def tail_arrive(src_key, dst_key):
            """
            Record: tail leaves src (-> FREE), tail arrives at dst.
                If dst head stayed (still HEADOCC in next_occ) -> COMPLETETRAINOCC.
                If dst head moved (TAILOCC already written) -> TAILOCC.
            """
            next_occ[src_key] = ElementOcc.FREE
            dst_next = next_occ.get(dst_key, p(*dst_key))

            if dst_next == ElementOcc.TAILOCC:
                next_occ[dst_key] = ElementOcc.TAILOCC  # head moved on, tail follows
            elif dst_next == ElementOcc.HEADOCC:
                next_occ[dst_key] = ElementOcc.COMPLETETRAINOCC  # head waited, tail caught up
            else:
                next_occ[dst_key] = ElementOcc.ERROROCC  # no head is present -> derailment

        # ----------------------------------------------------------------- #
        # PASS 1: HEAD movements (HEADOCC/COMPLETETRAINOCC -> next segment) #
        #         All reads from `prev_occ` only.                           #
        # ----------------------------------------------------------------- #

        # --- Linear head movements ---
        for seg in self.sections:
            l = seg

            # Head UP -> up_neighbor
            if l.up_neighbor is not None:
                occ = p(l, Direction.UP)

                if head_can_advance(occ) and (l.up_signal is None or l.up_signal.ACT == SignalAspect.GO):
                    nx = l.up_neighbor
                    nx_end = Direction.UP if isinstance(nx, Linear) else get_conn_end_dir(nx, l)

                    if nx_end is not None and p(nx, nx_end) == ElementOcc.FREE:
                        head_move((l, Direction.UP), (nx, nx_end))

            # Head DOWN -> down_neighbor
            if l.down_neighbor is not None:
                occ = p(l, Direction.DOWN)

                if head_can_advance(occ) and (l.down_signal is None or l.down_signal.ACT == SignalAspect.GO):
                    nx = l.down_neighbor
                    nx_end = Direction.DOWN if isinstance(nx, Linear) else get_conn_end_dir(nx, l)

                    if nx_end is not None and p(nx, nx_end) == ElementOcc.FREE:
                        head_move((l, Direction.DOWN), (nx, nx_end))

        # --- Point head movements (all reads from prev_occ) ---
        for pt in self.points:
            # SNR face (stem, DOWN-direction) -> normal/reverse branch
            if head_can_advance(p(pt, PointFace.SNR)):
                if pt.ACT == PointAspect.NORMAL and pt.normal_neighbor is not None:
                    nx = pt.normal_neighbor
                    nx_end = Direction.DOWN if isinstance(nx, Linear) else get_conn_end_dir(nx, pt)

                    if nx_end is not None and p(nx, nx_end) == ElementOcc.FREE:
                        head_move((pt, PointFace.SNR), (nx, nx_end))

                elif pt.ACT == PointAspect.REVERSE and pt.reverse_neighbor is not None:
                    nx = pt.reverse_neighbor
                    nx_end = Direction.DOWN if isinstance(nx, Linear) else get_conn_end_dir(nx, pt)

                    if nx_end is not None and p(nx, nx_end) == ElementOcc.FREE:
                        head_move((pt, PointFace.SNR), (nx, nx_end))

            # NS face (normal branch, UP-direction) -> stem
            if head_can_advance(p(pt, PointFace.NS)) and pt.ACT == PointAspect.NORMAL and pt.stem_neighbor is not None:
                nx = pt.stem_neighbor
                nx_end = Direction.UP if isinstance(nx, Linear) else get_conn_end_dir(nx, pt)

                if nx_end is not None and p(nx, nx_end) == ElementOcc.FREE:
                    head_move((pt, PointFace.NS), (nx, nx_end))

            # RS face (reverse branch, UP-direction) -> stem
            if head_can_advance(p(pt, PointFace.RS)) and pt.ACT == PointAspect.REVERSE and pt.stem_neighbor is not None:
                nx = pt.stem_neighbor
                nx_end = Direction.UP if isinstance(nx, Linear) else get_conn_end_dir(nx, pt)

                if nx_end is not None and p(nx, nx_end) == ElementOcc.FREE:
                    head_move((pt, PointFace.RS), (nx, nx_end))

        # ------------------------------------------------------------------ #
        # PASS 2: TAIL movements (TAILOCC -> next segment)                   #
        #         Uses `prev_occ` for presence checks;                       #
        #              `next_occ` for "did head move?"                       #
        # ------------------------------------------------------------------ #

        # --- Linear tail movements ---
        for seg in self.sections:
            l = seg

            # Tail UP -> up_neighbor
            if l.up_neighbor is not None and p(l, Direction.UP) == ElementOcc.TAILOCC:
                nx = l.up_neighbor
                nx_end = Direction.UP if isinstance(nx, Linear) else get_conn_end_dir(nx, l)

                if nx_end is not None:
                    tail_arrive((l, Direction.UP), (nx, nx_end))

            # Tail DOWN -> down_neighbor
            if l.down_neighbor is not None and p(l, Direction.DOWN) == ElementOcc.TAILOCC:
                nx = l.down_neighbor
                nx_end = Direction.DOWN if isinstance(nx, Linear) else get_conn_end_dir(nx, l)

                if nx_end is not None:
                    tail_arrive((l, Direction.DOWN), (nx, nx_end))

        # --- Point tail movements ---
        for pt in self.points:
            # SNR face tail -> normal/reverse branch
            if p(pt, PointFace.SNR) == ElementOcc.TAILOCC:
                if pt.ACT == PointAspect.NORMAL and pt.normal_neighbor is not None:
                    nx = pt.normal_neighbor
                    nx_end = Direction.DOWN if isinstance(nx, Linear) else get_conn_end_dir(nx, pt)

                    if nx_end is not None:
                        tail_arrive((pt, PointFace.SNR), (nx, nx_end))

                elif pt.ACT == PointAspect.REVERSE and pt.reverse_neighbor is not None:
                    nx = pt.reverse_neighbor
                    nx_end = Direction.DOWN if isinstance(nx, Linear) else get_conn_end_dir(nx, pt)

                    if nx_end is not None:
                        tail_arrive((pt, PointFace.SNR), (nx, nx_end))

            # NS face tail -> stem
            if p(pt,
                 PointFace.NS) == ElementOcc.TAILOCC and pt.ACT == PointAspect.NORMAL and pt.stem_neighbor is not None:
                nx = pt.stem_neighbor
                nx_end = Direction.UP if isinstance(nx, Linear) else get_conn_end_dir(nx, pt)

                if nx_end is not None:
                    tail_arrive((pt, PointFace.NS), (nx, nx_end))

            # RS face tail -> stem
            if p(pt,
                 PointFace.RS) == ElementOcc.TAILOCC and pt.ACT == PointAspect.REVERSE and pt.stem_neighbor is not None:
                nx = pt.stem_neighbor
                nx_end = Direction.UP if isinstance(nx, Linear) else get_conn_end_dir(nx, pt)

                if nx_end is not None:
                    tail_arrive((pt, PointFace.RS), (nx, nx_end))

        # ------------------------------------------------------------------ #
        # Apply all transitions atomically                                   #
        # ------------------------------------------------------------------ #
        changed = False

        for key, new_occ in next_occ.items():
            old_occ = prev_occ[key]

            if new_occ != old_occ:
                set_occ_by_end(key[0], key[1], new_occ)
                changed = True

        # C6: PREV state propagation
        for route in self.routes:
            if route.MODE == RouteMode.OCCUPIED:
                if update_route_prev_states(route):
                    changed = True

        return changed
