from entity import Direction, Linear, Point
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

def make_vacant_expr(elem):
    """Return an SMV expression that is true when section `elem` is vacant."""
    sn = safe_name(elem.name)
    if isinstance(elem, Linear):
        return f"{sn}.occDown = FREE & {sn}.occUp = FREE"
    else:
        return f"{sn}.occSNR = FREE & {sn}.occNS = FREE & {sn}.occRS = FREE"

def write_assign_section(system: InterlockingSystem, out, seg_up=None, seg_down=None):
    seg_up_name = f"seg{seg_up}" if seg_up is not None else None
    seg_down_name = f"seg{seg_down}" if seg_down is not None else None

    out.write("ASSIGN\n")
    out.write("\t-- SEGMENTS OCCUPANCY INITIAL --\n")
    for s in system.sections:
        sn = safe_name(s.name)
        if isinstance(s, Linear):
            occ_down = "COMPLETETRAINOCC" if s.name == seg_down_name else "FREE"
            occ_up = "COMPLETETRAINOCC" if s.name == seg_up_name else "FREE"
            out.write(f"\tinit({sn}.occDown) := {occ_down};\n")
            out.write(f"\tinit({sn}.occUp) := {occ_up};\n")
    out.write("\n")

    out.write("\t-- SEGMENTS OCCUPANCY INITIAL --\n")

    # Initialize points
    for p in system.points:
        sn = safe_name(p.name)
        if isinstance(p, Point):
            out.write(f"\tinit({sn}.occSNR) := FREE;\n")
            out.write(f"\tinit({sn}.occNS) := FREE;\n")
            out.write(f"\tinit({sn}.occRS) := FREE;\n")
            out.write(f"\tinit({sn}CMD) := NORMAL;\n")
    out.write("\n")
    
    out.write("\t-- SIGNALS CMD INITIAL --\n")

    # Initialize signals
    for sig in system.signals:
        sn = safe_name(sig.name)
        out.write(f"\tinit({sn}CMD) := STOP;\n")
    out.write("\n")

    out.write("\t-- NEXTS --\n")

    out.write("\t-- SIGNALS CMD NEXT --\n")

    """
    Signals are driven purely by route state (not occupancy), so that the
    `can-lock` condition (signals ACT = STOP) is achievable before the route locks.
    """
    for sig in system.signals:
        sn = safe_name(sig.name)
        out.write(f"\tnext({sn}CMD) := case\n")
        r_locked = []
        r_occupied = []

        for r in system.routes:
            rn = safe_name(r.name)

            # Primary: entry signal of this route
            if sn == r.entry_signal:
                r_locked.append(f"{rn}.mode = LOCKED")
                r_occupied.append(f"{rn}.mode = OCCUPIED")
            else:
                """
                Intermediate: signal gates entry to a segment on this route's path
                DOWN route -> up_signal of each Linear segment is the entry gate
                UP  route -> down_signal of each Linear segment is the entry gate
                """
                for elem in r.path:
                    if isinstance(elem, Linear):
                        if r.entry_dir == Direction.DOWN:
                            intermediate = getattr(elem.up_signal, 'name', elem.up_signal)
                        else:
                            intermediate = getattr(elem.down_signal, 'name', elem.down_signal)
                        if intermediate == sn:
                            r_locked.append(f"{rn}.mode = LOCKED")
                            r_occupied.append(f"{rn}.mode = OCCUPIED")
                            break

        if r_locked and len(r_locked) > 1:
            r_locked_sig = "\n\t\t\t| ".join(r_locked)
            out.write(f"\t\t(\n\t\t\t{r_locked_sig}\n\t\t)\n\t\t: GO;\n\n")
        elif r_locked:
            out.write(f"\t\t{r_locked[0]}: GO;\n")

        if r_occupied and len(r_locked) > 1:
            r_occupied_sig = "\n\t\t\t| ".join(r_occupied)
            out.write(f"\t\t(\n\t\t\t{r_occupied_sig}\n\t\t)\n\t\t: STOP;\n\n")
        elif r_occupied:
            out.write(f"\t\t{r_occupied[0]}: STOP;\n")

        out.write(f"\t\tTRUE : {sn}CMD;\n")
        out.write(f"\tesac;\n\n")
    out.write("\n")

    # Next points command (route-based: CMD tracks which routes require REVERSE aspect)
    out.write("\t-- POINTS CMD NEXT --\n")
    for p in system.points:
        sn = safe_name(p.name)

        if isinstance(p, Point):
            reverse_routes = [r for r in system.routes if p in r.points and r.points[p].name == 'REVERSE']

            if reverse_routes:
                rev_conds = " | ".join(
                    f"{safe_name(r.name)}.mode in {{ALLOCATING, LOCKED, OCCUPIED}}"
                    for r in reverse_routes
                )
                out.write(f"\tnext({sn}CMD) := case\n")
                out.write(f"\t\t{rev_conds} : REVERSE;\n")
                out.write(f"\t\tTRUE : NORMAL;\n")
                out.write(f"\tesac;\n\n")
            else:
                out.write(f"\tnext({sn}CMD) := NORMAL;\n\n")
    out.write("\n")
