from typing import Optional
from entity import Linear, Point
from interlocking import InterlockingSystem


def safe_name(name: str) -> str:
    """Sanitize a string to be a valid SMV identifier."""
    import re
    s = name.strip()
    # replace non-word chars with point
    s = re.sub(r"[^0-9A-Za-z_]", ".", s)
    # collapse multiple underscores
    s = re.sub(r"_+", ".", s)
    # cannot start with digit
    if re.match(r"^[0-9]", s):
        s = "X" + s
    return s

def get_approach_check(route) -> Optional[str]:
    """
    Return an SMV expression that is TRUE when a train occupies the segment
    immediately before the first path element in the route's direction of travel.
    This prevents routes from being dispatched when no train is waiting for them.
    Returns None if the approach segment cannot be determined.
    """
    first = route.path[0] if route.path else None

    if first is None:
        return None

    entry_dir = str(route.entry_dir)

    if isinstance(first, Point):
        req_act = route.points.get(first)

        if entry_dir == 'down':
            # Train enters the point from stem side (occSNR direction going DOWN)
            approach = first.stem_neighbor
            occ_suffix = 'occDown'
        else:
            # UP direction: enters from normal or reverse branch
            if req_act is not None and req_act.name == 'REVERSE':
                approach = first.reverse_neighbor
            else:
                approach = first.normal_neighbor
            occ_suffix = 'occUp'
    elif isinstance(first, Linear):
        if entry_dir == 'down':
            approach = first.up_neighbor
            occ_suffix = 'occDown'
        else:
            approach = first.down_neighbor
            occ_suffix = 'occUp'
    else:
        return None

    if approach is None:
        return None

    # Guard: neighbor may be an unresolved string reference for some layouts
    if not isinstance(approach, (Linear, Point)):
        return None

    """
    If approach is already in the route path, the approach check would
    contradict the path-empty check (path requires approach segment to be FREE,
    but approach check requires it to be non-FREE). Skip the check.
    """
    if approach in route.path:
        return None

    approach_sn = safe_name(approach.name)

    if isinstance(approach, Linear):
        return f"track.{approach_sn}.{occ_suffix} != FREE"
    else:
        return f"(track.{approach_sn}.occSNR != FREE | track.{approach_sn}.occNS != FREE | track.{approach_sn}.occRS != FREE)"

def make_vacant_expr(elem):
    """Return an SMV expression that is true when section `elem` is vacant."""
    sn = safe_name(elem.name)

    if isinstance(elem, Linear):
        return f"track.{sn}.occDown = FREE & track.{sn}.occUp = FREE"
    else:
        return f"track.{sn}.occSNR = FREE & track.{sn}.occNS = FREE & track.{sn}.occRS = FREE"

def write_route_interlocking(system: InterlockingSystem, out):
    out.write("""-------------------------------------------------------------------------------
-- Interlocking System Moduel --
-- Represents a route state transitions for the train movement
-------------------------------------------------------------------------------
MODULE InterlockingSystem 
VAR
	track : TrackSection;
ASSIGN
""")

    # Route mode transitions
    for r in system.routes:
        rn = safe_name(r.name)

        # can_allocate: route in MARKED and all conflicts not (ALLOCATING or LOCKED)
        conf_checks = []

        for cr in r.conflicts:
            conf_checks.append(f"track.{safe_name(cr.name)}.mode != ALLOCATING & track.{safe_name(cr.name)}.mode != LOCKED")
        conf_expr = "\n\t\t& ".join(conf_checks) if conf_checks else "TRUE"

        vac_checks = [make_vacant_expr(elem) for elem in (r.path)]
        vac_expr = "\n\t\t& ".join(vac_checks) if vac_checks else "TRUE"

        path_avail_checks = [f"track.{safe_name(elem.name)}.mode = AVAILABLE" for elem in r.path]
        path_avail = "\n\t\t& ".join(path_avail_checks) if path_avail_checks else "TRUE"

        # Fix R2 (same pattern): use `idx` (Point object) not `point_obj` (PointAspect)
        point_checks = []

        for idx, point_obj in r.points.items():
            pnm = safe_name(idx.name)

            if idx not in r.path:
                point_checks.append(f"track.{pnm}.mode = AVAILABLE")
        point_expr = "\n\t\t& ".join(point_checks) if point_checks else "TRUE"

        approach_check = get_approach_check(r)
        approach_expr = f"\n        & {approach_check}" if approach_check else ""

        can_allocate = f"""{conf_expr}
        & {vac_expr}
        & {path_avail}
        & {point_expr}{approach_expr}"""

        # can_lock: ALLOCATING & all signals ACT = STOP & points ACT=req
        #           & all_sections vacant & path elems EXLOCKED
        sig_checks = "\n\t\t& ".join(
            [f"track.{safe_name(sig.name)}.ACT = STOP" for sig in r.signals]
        ) if r.signals else "TRUE"

        points_req_checks = "\n\t\t& ".join(
            [f"track.{safe_name(p.name)}.ACT = {req.name}" for p, req in r.points.items()]
        ) if r.points else "TRUE"

        """
        Fix R1: removed dead lines that built path_exlocked from EXLOCKED checks.
                use path_exlocked_checks, not path_avail_checks.
        """
        path_exlocked_checks = [f"track.{safe_name(elem.name)}.mode = EXLOCKED" for elem in r.path]
        path_exlocked = "\n\t\t& ".join(path_exlocked_checks) if path_exlocked_checks else "TRUE"

        """
        Fix R2: filter uses `idx` (the Point object) not `point_obj` (the PointAspect),
                so points that are already in r.path are correctly excluded from the extra check.
        """
        point_exlocked_checks = []

        for idx, point_obj in r.points.items():
            pnm = safe_name(idx.name)
            if idx not in r.path:
                point_exlocked_checks.append(f"track.{pnm}.mode = EXLOCKED")
        point_exlocked = "\n\t\t& ".join(point_exlocked_checks) if point_exlocked_checks else "TRUE"

        all_sections_vac = vac_expr

        """
        Conflict exclusion in `can_lock` prevents two conflicting routes from simultaneously
        reaching LOCKED via the point-switching race:
            when both are ALLOCATING, the point ACT still shows the old aspect for one step (1-step lag),
            so both can satisfy their can_lock checks in that window unless
            we explicitly exclude ALLOCATING/LOCKED conflicting routes here.
        """
        can_lock = f"""{conf_expr}
        & {sig_checks}
        & {points_req_checks}
        & {all_sections_vac}
        & {path_exlocked}
        & {point_exlocked}"""

        # can_set_in_use: LOCKED & entry signal GO & train has entered first path element
        first = r.path[0] if r.path else None

        if first is not None:
            entry_sig = r.entry_signal
            sig_in_go = f"track.{entry_sig}.ACT = GO"

            """
            Fix R3: check the specific entry-face variable, not !all_vacant.
            For Linear: entry face is occDown (DOWN route) or occUp (UP route).
            For Point: DOWN route enters from stem side (occSNR); UP route enters
                from normal branch (occNS) or reverse branch (occRS) per required ACT.
            """
            fsn = safe_name(first.name)

            if isinstance(first, Linear):
                dir_cap = str(r.entry_dir).capitalize()
                entry_occ = f"track.{fsn}.occ{dir_cap}"
            else:
                if str(r.entry_dir) == 'down':
                    entry_occ = f"track.{fsn}.occSNR"
                else:
                    req_act = r.points.get(first)
                    if req_act is not None and req_act.name == 'REVERSE':
                        entry_occ = f"track.{fsn}.occRS"
                    else:
                        entry_occ = f"track.{fsn}.occNS"
            can_setinuse = f"{sig_in_go}\n\t\t& {entry_occ} != FREE"
        else:
            can_setinuse = f"track.{rn}.mode = LOCKED & FALSE"

        # Next route transitions
        out.write(f"\tnext(track.{rn}.transition) := case\n")
        out.write(f"\t\ttrack.{rn}.transition = CAN_DISPATCH\n\t\t& {can_allocate}\n\t\t: CAN_ALLOCATE;\n\n")
        out.write(f"\t\ttrack.{rn}.transition = CAN_ALLOCATE\n\t\t& {can_lock}\n\t\t: CAN_LOCK;\n\n")
        out.write(f"\t\ttrack.{rn}.transition = CAN_LOCK\n\t\t& track.{rn}.mode = LOCKED\n\t\t& {can_setinuse}\n\t\t: CAN_OCCUPY;\n\n")
        out.write(f"\t\ttrack.{rn}.transition = CAN_OCCUPY\n\t\t& track.{rn}.mode = FREE\n\t\t: CAN_DISPATCH;\n\n")
        out.write(f"\t\tTRUE : track.{rn}.transition;\n")
        out.write(f"\tesac;\n\n")

        # Next route modes
        out.write(f"\tnext(track.{rn}.mode) := case\n")
        out.write(f"\t\ttrack.{rn}.mode = FREE\n\t\t& track.{rn}.transition = CAN_DISPATCH\n\t\t: MARKED;\n\n")
        out.write(f"\t\ttrack.{rn}.mode = MARKED\n\t\t& {can_allocate}\n\t\t: ALLOCATING;\n\n")
        out.write(f"\t\ttrack.{rn}.mode = ALLOCATING\n\t\t& {can_lock}\n\t\t: LOCKED;\n\n")
        out.write(f"\t\ttrack.{rn}.mode = LOCKED\n\t\t& {can_setinuse}\n\t\t: OCCUPIED;\n\n")

        # release last route: if do_release_last and route in OCCUPIED and last available and prev ok -> FREE
        last = r.path[-1] if r.path else None

        if last is not None:
            # Fix R4: Point terminals use occSNR (not occDown/occUp, which don't exist on Point).
            lsn = safe_name(last.name)

            if isinstance(last, Linear):
                dir_cap = str(r.entry_dir).capitalize()
                last_occ = f"track.{lsn}.occ{dir_cap} in {{HEADOCC, COMPLETETRAINOCC}}"
            else:
                last_occ = f"track.{lsn}.occSNR in {{HEADOCC, COMPLETETRAINOCC}}"

            # prev check simplified: either first == last or last.prev = RELEASED
            if last is first:
                prev_ok = "TRUE"
            else:
                prev_ok = f"track.{safe_name(last.name)}.mode = USED\n\t\t& track.{safe_name(last.name)}.prev = RELEASED"
            can_release_last = f"{last_occ}\n\t\t& {prev_ok}"
            out.write(f"\t\ttrack.{rn}.mode = OCCUPIED\n\t\t& {can_release_last}\n\t\t: FREE;\n")

        out.write(f"\n\t\tTRUE : track.{rn}.mode;\n")
        out.write(f"\tesac;\n\n")

    out.write("\n")
