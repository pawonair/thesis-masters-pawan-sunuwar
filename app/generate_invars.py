from entity import Linear, Point, PointAspect
from interlocking import InterlockingSystem
from route_op import get_conn_end_dir


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
        return f"({sn}.occDown = FREE & {sn}.occUp = FREE)"
    else:
        return f"({sn}.occSNR = FREE & {sn}.occNS = FREE & {sn}.occRS = FREE)"

def write_invariants(system: InterlockingSystem, out):
    out.write("-- Train Movement --\n")

    # Helper function to get neighbor occupancy variable
    def get_neighbor_occ_var(section, neighbor, direction):
        """Get occupancy variable of neighbor in the same direction.

        For train movement integrity, we check the same direction variable
        in neighboring sections. For example, if current section is seg2.occUp,
        we check seg1.occUp (previous) and seg3.occUp (next).

        Args:
            section: Current section
            neighbor: The neighboring section
            direction: Direction ('UP' or 'DOWN' for Linear sections)

        Returns:
            SMV occupancy variable string or None
        """
        if neighbor is None:
            return None

        if isinstance(neighbor, Linear):
            nn = safe_name(neighbor.name)

            # For linear sections, use the same direction variable
            if direction == 'up':
                return f"{nn}.occUp"
            else:  # down
                return f"{nn}.occDown"
        elif isinstance(neighbor, Point):  # Point
            nn = safe_name(neighbor.name)
            # Determine which end of point connects to this section
            end = get_conn_end_dir(neighbor, section)

            """
            # Map (end, direction) to the correct point occupancy variable:
                occSNR = train going DOWN through STEM (from STEM to NORMAL/REVERSE)
                occNS  = train going UP through NORMAL branch (from NORMAL to STEM)
                occRS  = train going UP through REVERSE branch (from REVERSE to STEM)
            """
            if end == PointAspect.STEM:
                if direction == 'down':
                    # Train going DOWN exits via SNR (STEM to branches)
                    return f"{nn}.occSNR"
                else:  # 'up'
                    # Train going UP could be from occNS or occRS; no single variable
                    return None
            elif end == PointAspect.NORMAL:
                if direction == 'up':
                    # Train going UP enters point via NORMAL branch (occNS)
                    return f"{nn}.occNS"
                else:  # 'down'
                    # Train going DOWN came from SNR direction in point
                    return f"{nn}.occSNR"
            elif end == PointAspect.REVERSE:
                if direction == 'up':
                    # Train going UP enters point via REVERSE branch (occRS)
                    return f"{nn}.occRS"
                else:  # 'down'
                    # Train going DOWN came from SNR direction in point
                    return f"{nn}.occSNR"
        return None

    train_movement_clauses = []

    """Generate invariants for linear sections
    
    For whole interlocking track elements:
        UP: HEADOCC -> previous segment(s) shall be TAILOCC or ERROROCC,
					   and next segment shall not be HEADOCC
        DOWN: HEADOCC -> previous segment(s) shall be TAILOCC or ERROROCC,
		                 and next segment shall not be HEADOCC
        POINTS: HEADOCC -> previous segment shall be TAILOCC or ERROROCC,
		                   and next segment(s) shall not be HEADOCC

        UP: COMPLETETRAINOCC -> previous segment(s) shall be TAILOCC,
	                            and next segment shall not be HEADOCC
        DOWN: COMPLETETRAINOCC -> previous segment(s) shall be TAILOCC,
	                              and next segment shall not be HEADOCC
        POINTS: COMPLETETRAINOCC -> previous segment shall be TAILOCC,
	                                and next segment(s) shall not be HEADOCC
    
        UP: TAILOCC -> previous segment(s) shall not be TAILOCC,
	                   and next segment has HEADOCC or ERROROCC
        DOWN: TAILOCC -> previous segment(s) shall not be TAILOCC,
	                     and next segment has HEADOCC or ERROROCC
        POINTS: TAILOCC -> previous segment shall not be TAILOCC,
	                       and next segment(S) has HEADOCC or ERROROCC
	"""

    for s in system.sections:
        if isinstance(s, Linear):
            sn = safe_name(s.name)

            # UP direction (from down_neighbor to up_neighbor)
            prev_up_var = get_neighbor_occ_var(s, s.down_neighbor, 'up')
            next_up_var = get_neighbor_occ_var(s, s.up_neighbor, 'up')

            # HEADOCC UP
            if prev_up_var and next_up_var:
                train_movement_clauses.append(
                    f"({sn}.occUp = HEADOCC -> ({prev_up_var} in {{TAILOCC, ERROROCC}} & {next_up_var} != HEADOCC))"
                )
            elif prev_up_var:
                train_movement_clauses.append(
                    f"({sn}.occUp = HEADOCC -> ({prev_up_var} in {{TAILOCC, ERROROCC}}))"
                )
            elif next_up_var:
                train_movement_clauses.append(
                    f"({sn}.occUp = HEADOCC -> ({next_up_var} != HEADOCC))"
                )

            # COMPLETETRAINOCC UP
            if prev_up_var and next_up_var:
                train_movement_clauses.append(
                    f"({sn}.occUp = COMPLETETRAINOCC -> ({prev_up_var} != TAILOCC & {next_up_var} != HEADOCC))"
                )
            elif prev_up_var:
                train_movement_clauses.append(
                    f"({sn}.occUp = COMPLETETRAINOCC -> ({prev_up_var} != TAILOCC))"
                )
            elif next_up_var:
                train_movement_clauses.append(
                    f"({sn}.occUp = COMPLETETRAINOCC -> ({next_up_var} != HEADOCC))"
                )

            # TAILOCC UP
            if prev_up_var and next_up_var:
                train_movement_clauses.append(
                    f"({sn}.occUp = TAILOCC -> ({prev_up_var} != TAILOCC & {next_up_var} in {{HEADOCC, COMPLETETRAINOCC, ERROROCC}}))"
                )
            elif next_up_var:
                train_movement_clauses.append(
                    f"({sn}.occUp = TAILOCC -> ({next_up_var} in {{HEADOCC, COMPLETETRAINOCC, ERROROCC}}))"
                )
            elif prev_up_var:
                train_movement_clauses.append(
                    f"({sn}.occUp = TAILOCC -> ({prev_up_var} != TAILOCC))"
                )

            # DOWN direction (from up_neighbor to down_neighbor)
            prev_down_var = get_neighbor_occ_var(s, s.up_neighbor, 'down')
            next_down_var = get_neighbor_occ_var(s, s.down_neighbor, 'down')

            # HEADOCC DOWN
            if prev_down_var and next_down_var:
                train_movement_clauses.append(
                    f"({sn}.occDown = HEADOCC -> ({prev_down_var} in {{TAILOCC, ERROROCC}} & {next_down_var} != HEADOCC))"
                )
            elif prev_down_var:
                train_movement_clauses.append(
                    f"({sn}.occDown = HEADOCC -> ({prev_down_var} in {{TAILOCC, ERROROCC}}))"
                )
            elif next_down_var:
                train_movement_clauses.append(
                    f"({sn}.occDown = HEADOCC -> ({next_down_var} != HEADOCC))"
                )

            # COMPLETETRAINOCC DOWN
            if prev_down_var and next_down_var:
                train_movement_clauses.append(
                    f"({sn}.occDown = COMPLETETRAINOCC -> ({prev_down_var} != TAILOCC & {next_down_var} != HEADOCC))"
                )
            elif prev_down_var:
                train_movement_clauses.append(
                    f"({sn}.occDown = COMPLETETRAINOCC -> ({prev_down_var} != TAILOCC))"
                )
            elif next_down_var:
                train_movement_clauses.append(
                    f"({sn}.occDown = COMPLETETRAINOCC -> ({next_down_var} != HEADOCC))"
                )

            # TAILOCC DOWN
            if prev_down_var and next_down_var:
                train_movement_clauses.append(
                    f"({sn}.occDown = TAILOCC -> ({prev_down_var} != TAILOCC & {next_down_var} in {{HEADOCC, COMPLETETRAINOCC, ERROROCC}}))"
                )
            elif next_down_var:
                train_movement_clauses.append(
                    f"({sn}.occDown = TAILOCC -> ({next_down_var} in {{HEADOCC, COMPLETETRAINOCC, ERROROCC}}))"
                )
            elif prev_down_var:
                train_movement_clauses.append(
                    f"({sn}.occDown = TAILOCC -> ({prev_down_var} != TAILOCC))"
                )

    # Generate invariants for points
    for p in system.points:
        if isinstance(p, Point):
            pn = safe_name(p.name)

            # occSNR: from STEM to NORMAL/REVERSE (corresponds to DOWN direction in track)
            # Previous: stem_neighbor moving down
            # Next: normal_neighbor and reverse_neighbor moving down
            prev_snr = get_neighbor_occ_var(p, p.stem_neighbor, 'down')
            next_normal = get_neighbor_occ_var(p, p.normal_neighbor, 'down')
            next_reverse = get_neighbor_occ_var(p, p.reverse_neighbor, 'down')

            if prev_snr and (next_normal or next_reverse):
                if next_normal and next_reverse:
                    # HEADOCC
                    train_movement_clauses.append(
                        f"({pn}.occSNR = HEADOCC -> ({prev_snr} in {{TAILOCC, ERROROCC}} & {next_normal} != HEADOCC & {next_reverse} != HEADOCC))"
                    )
                    # COMPLETETRAINOCC
                    train_movement_clauses.append(
                        f"({pn}.occSNR = COMPLETETRAINOCC -> ({prev_snr} != TAILOCC & {next_normal} != HEADOCC & {next_reverse} != HEADOCC))"
                    )
                    # TAILOCC
                    train_movement_clauses.append(
                        f"({pn}.occSNR = TAILOCC -> ({prev_snr} != TAILOCC & ({next_normal} in {{HEADOCC, COMPLETETRAINOCC, ERROROCC}} | {next_reverse} in {{HEADOCC, COMPLETETRAINOCC, ERROROCC}})))"
                    )

            # occNS: from NORMAL to STEM (corresponds to UP direction in track)
            # Previous: normal_neighbor moving up
            # Next: stem_neighbor moving up
            prev_ns = get_neighbor_occ_var(p, p.normal_neighbor, 'up')
            next_ns = get_neighbor_occ_var(p, p.stem_neighbor, 'up')

            if prev_ns and next_ns:
                # HEADOCC
                train_movement_clauses.append(
                    f"({pn}.occNS = HEADOCC -> ({prev_ns} in {{TAILOCC, ERROROCC}} & {next_ns} != HEADOCC))"
                )
                # COMPLETETRAINOCC
                train_movement_clauses.append(
                    f"({pn}.occNS = COMPLETETRAINOCC -> ({prev_ns} != TAILOCC & {next_ns} != HEADOCC))"
                )
                # TAILOCC
                train_movement_clauses.append(
                    f"({pn}.occNS = TAILOCC -> ({prev_ns} != TAILOCC & {next_ns} in {{HEADOCC, COMPLETETRAINOCC, ERROROCC}}))"
                )

            # occRS: from REVERSE to STEM (corresponds to UP direction in track)
            # Previous: reverse_neighbor moving up
            # Next: stem_neighbor moving up
            prev_rs = get_neighbor_occ_var(p, p.reverse_neighbor, 'up')
            next_rs = get_neighbor_occ_var(p, p.stem_neighbor, 'up')

            if prev_rs and next_rs:
                # HEADOCC
                train_movement_clauses.append(
                    f"({pn}.occRS = HEADOCC -> ({prev_rs} in {{TAILOCC, ERROROCC}} & {next_rs} != HEADOCC))"
                )
                # COMPLETETRAINOCC
                train_movement_clauses.append(
                    f"({pn}.occRS = COMPLETETRAINOCC -> ({prev_rs} != TAILOCC & {next_rs} != HEADOCC))"
                )
                # TAILOCC
                train_movement_clauses.append(
                    f"({pn}.occRS = TAILOCC -> ({prev_rs} != TAILOCC & {next_rs} in {{HEADOCC, COMPLETETRAINOCC, ERROROCC}}))"
                )

    # Write the train movement integrity invariant
    if train_movement_clauses:
        out.write(f"INVAR\n")
        out.write(f"\t{('\n\t& ').join(train_movement_clauses)}\n")

    out.write("\n")

    out.write("-- Train Occupancy Error --\n")

    # no segment occupany error
    no_occ_up_error = []
    no_occ_down_error = []

    for s in system.sections:
        if isinstance(s, Linear):
            sn = safe_name(s.name)
            no_occ_up_error.append(f"{sn}.occUp = ERROROCC\n")
            no_occ_down_error.append(f"{sn}.occDown = ERROROCC\n")
    
    if no_occ_up_error:
        out.write(f"INVARSPEC\n\tNAME NoOccUpErrors := !(\n\t\t{'\t\t| '.join(no_occ_up_error)}\t);\n\n")
    
    if no_occ_down_error:
        out.write(f"INVARSPEC\n\tNAME NoOccDownErrors := !(\n\t\t{'\t\t| '.join(no_occ_down_error)}\t);\n\n")
    
    no_occ_point_error = []

    for p in system.points:
        if isinstance(p, Point):
            pn = safe_name(p.name)
            no_occ_point_error.append(f"{pn}.occSNR = ERROROCC\n\t\t| {pn}.occRS = ERROROCC\n\t\t| {pn}.occNS = ERROROCC\n")
    
    if no_occ_point_error:
        out.write(f"INVARSPEC\n\tNAME NoOccPointErrors := !(\n\t\t{'\t\t| '.join(no_occ_point_error)}\t);\n\n")
    
    out.write("\n")

    out.write("-- Safety Invariants --\n")

    # no head-to-head collisions on segments (except boundaries)
    h2h_s_clauses = []
    for s in system.sections:
        if isinstance(s, Linear):
            sn = safe_name(s.name)
            # boundary detection not translated; include unconditional check
            h2h_s_clauses.append(f"({sn}.occDown != FREE -> {sn}.occUp = FREE) & ({sn}.occUp != FREE -> {sn}.occDown = FREE)\n")
            # h2h_s_clauses.append(f"!({sn}.occDown = HEADOCC & {sn}.occUp = HEADOCC)")
    
    if h2h_s_clauses:
        out.write(f"INVARSPEC\n\tNAME NoHeadToHeadSegmentCollisions := (\n\t\t{'\t\t& '.join(h2h_s_clauses)}\t);\n")
    
    out.write("\n")
    
    # no head-to-head collisions on points (except boundaries)
    h2h_p_clauses = []

    for p in system.points:
        if isinstance(p, Point):
            sn = safe_name(p.name)
            p_occ = f"""({sn}.occSNR != FREE -> ({sn}.occNS = FREE & {sn}.occRS = FREE))
        & ({sn}.occNS != FREE -> ({sn}.occSNR = FREE & {sn}.occRS = FREE))
        & ({sn}.occRS != FREE -> ({sn}.occSNR = FREE & {sn}.occNS = FREE))"""
            h2h_p_clauses.append(f"{p_occ}\n")

    if h2h_p_clauses:
        out.write(f"INVARSPEC\n\tNAME NoHeadToHeadPointCollisions := (\n\t\t{'\t\t& '.join(h2h_p_clauses)}\t);\n")
    
    out.write("\n")

    """
    # No head-to-tail collisions on linear sections:
    if a section has a train in TAILOCC or COMPLETETRAINOCC
        then the previous section shall not have a train in HEADOCC or COMPLETETRAINOCC, 
    UNLESS there's a signal in aspect STOP between them, or a point aspect means they would not be able to collide.
    """
    h2tc_down_clauses = []
    h2tc_up_clauses = []

    for s in system.sections:
        if isinstance(s, Linear):
            sn = safe_name(s.name)
            # If up-end has tail/complete, ensure the up neighbor
            # doesn't present a head/complete towards this section.
            nx = s.up_neighbor # for occDown previous seg
            pnx = s.down_neighbor # for occUp previos seg
            nx_s = ''
            pnx_s = ''

            if nx is not None:
                # print(sn, nx)
                not_Linear = not isinstance(nx, Linear)
                not_Point = not isinstance(nx, Point)
                nx_sn = safe_name(nx) if not_Linear and not_Point and len(nx) > 0 else safe_name(nx.name)
                nx_end = get_conn_end_dir(nx, s)
                # nx_occ = get_occ_by_end(nx, nx_end) if nx_end is not None else None
                # print("Down: ", s.name, nx_sn, nx_end)
                
                if nx_end:
                    if isinstance(nx, Point):
                        # Map point end to occupancy variable
                        if nx_end == 'stem':
                            occDir = 'occSNR'

                            # For STEM: determine which branch current segment is on
                            # Check if current segment is on normal or reverse branch
                            if nx.normal_neighbor == s:
                                act_check = f"{nx_sn}.ACT != NORMAL"
                            elif nx.reverse_neighbor == s:
                                act_check = f"{nx_sn}.ACT != REVERSE"
                            else:
                                # Shouldn't happen, but fallback
                                act_check = f"{nx_sn}.ACT = INTERMEDIATE"
                        elif nx_end == 'normal':
                            occDir = 'occNS'
                            act_check = f"{nx_sn}.ACT != NORMAL"
                        else:  # reverse
                            occDir = 'occRS'
                            act_check = f"{nx_sn}.ACT != REVERSE"

                        p_occ = f"!({nx_sn}.{occDir} in {{COMPLETETRAINOCC, HEADOCC}})"
                        nx_s = f"(\n\t\t\t{p_occ}\n\t\t\t| {act_check}\n\t\t)"
                    elif nx_end == 'down':
                        nx_s = f"!({nx_sn}.occDown in {{HEADOCC, COMPLETETRAINOCC}})"
                    elif nx_end == 'up':
                        nx_s = f"!({nx_sn}.occUp in {{HEADOCC, COMPLETETRAINOCC}})"
            
            if pnx is not None:
                pnx_sn = safe_name(pnx.name)
                pnx_end = get_conn_end_dir(pnx, s)
                # pnx_occ = get_occ_by_end(pnx, pnx_end) if pnx_end is not None else None
                # print("Up: ", s.name, pnx_sn, pnx_end)
                
                if pnx_end:
                    if isinstance(pnx, Point):
                        # Map point end to occupancy variable
                        if pnx_end == 'stem':
                            occDir = 'occSNR'

                            # For STEM: determine which branch current segment is on
                            # Check if current segment is on normal or reverse branch
                            if pnx.normal_neighbor == s:
                                act_check = f"{pnx_sn}.ACT != NORMAL"
                            elif pnx.reverse_neighbor == s:
                                act_check = f"{pnx_sn}.ACT != REVERSE"
                            else:
                                # Shouldn't happen, but fallback
                                act_check = f"{pnx_sn}.ACT = INTERMEDIATE"
                        elif pnx_end == 'normal':
                            occDir = 'occNS'
                            act_check = f"{pnx_sn}.ACT != NORMAL"
                        else:  # reverse
                            occDir = 'occRS'
                            act_check = f"{pnx_sn}.ACT != REVERSE"

                        p_occ = f"!({pnx_sn}.{occDir} in {{COMPLETETRAINOCC, HEADOCC}})"
                        pnx_s = f"(\n\t\t\t{p_occ}\n\t\t\t| {act_check}\n\t\t)"
                    elif pnx_end == 'up':
                        pnx_s = f"!({pnx_sn}.occUp in {{HEADOCC, COMPLETETRAINOCC}})"
                    elif pnx_end == 'down':
                        pnx_s = f"!({pnx_sn}.occDown in {{HEADOCC, COMPLETETRAINOCC}})"

            if nx_s:
                h2tc_down_clauses.append(f"({sn}.occDown in {{TAILOCC, COMPLETETRAINOCC}}) -> {nx_s}\n")

            if pnx_s:
                h2tc_up_clauses.append(f"({sn}.occUp in {{TAILOCC, COMPLETETRAINOCC}}) -> {pnx_s}\n")
    
    if h2tc_down_clauses:
        out.write(f"INVARSPEC\n\tNAME NoHeadToTailCollisionsDown := (\n\t\t{'\t\t& '.join(h2tc_down_clauses)}\t);\n")
    
    if h2tc_up_clauses:
        out.write(f"INVARSPEC\n\tNAME NoHeadToTailCollisionsUp := (\n\t\t{'\t\t& '.join(h2tc_up_clauses)}\t);\n")
    
    out.write("\n")

    # no derailments for points
    point_clauses = []

    for s in system.points:
        if isinstance(s, Point):
            sn = safe_name(s.name)
            point_c = f"""({sn}.occNS != FREE -> {sn}.ACT = NORMAL)
            & ({sn}.occRS != FREE -> {sn}.ACT = REVERSE)
            & ({sn}.occSNR != FREE -> {sn}.ACT != INTERMEDIATE)"""
            point_clauses.append(f"(\n\t\t\t{point_c}\n\t\t)")

    if point_clauses:
        out.write(f"INVARSPEC\n\tNAME NoPointDerailments := (\n\t\t{'\n\t\t& '.join(point_clauses)}\n\t);\n")

    out.write("\n")

    # no head-to-tail collisions for points
    h2tp_clauses = []

    for p in system.points:
        if isinstance(p, Point):
            pn = safe_name(p.name)
            prev_snr = get_neighbor_occ_var(p, p.stem_neighbor, 'down')
            prev_ns = get_neighbor_occ_var(p, p.normal_neighbor, 'up')
            prev_rs = get_neighbor_occ_var(p, p.reverse_neighbor, 'up')

            if prev_snr:
                h2tp_clauses.append(f"({pn}.occSNR in {{TAILOCC, COMPLETETRAINOCC}}) -> !({prev_snr} in {{HEADOCC, COMPLETETRAINOCC}})\n")
            if prev_ns:
                h2tp_clauses.append(f"({pn}.occNS in {{TAILOCC, COMPLETETRAINOCC}}) -> !({prev_ns} in {{HEADOCC, COMPLETETRAINOCC}})\n")
            if prev_rs:
                h2tp_clauses.append(f"({pn}.occRS in {{TAILOCC, COMPLETETRAINOCC}}) -> !({prev_rs} in {{HEADOCC, COMPLETETRAINOCC}})\n")

    if h2tp_clauses:
        out.write(f"INVARSPEC\n\tNAME NoPointHeadToTailCollisions := (\n\t\t{'\t\t& '.join(h2tp_clauses)}\t);\n\n")

    # build element-to-routes mapping for lock mode transition properties
    elem_routes: dict = {}

    for route in system.routes:
        rn = safe_name(route.name)
        for elem in route.path:
            if elem not in elem_routes:
                elem_routes[elem] = []
            elem_routes[elem].append(rn)

    """
    # Terminal elements: last element of each route's path.
        These remain USED after the route completes (parked train), so the
        USED -> route OCCUPIED invariant must not apply to them.
    """
    terminal_elements = set()

    for route in system.routes:
        if route.path:
            terminal_elements.add(route.path[-1])

    # no invalid segment lock mode transitions
    seg_lock_clauses = []

    for s in system.sections:
        if isinstance(s, Linear) and s in elem_routes:
            sn = safe_name(s.name)
            route_names = elem_routes[s]
            exlocked_cond = " | ".join(
                f"{rn}.mode in {{ALLOCATING, LOCKED, OCCUPIED}}" for rn in route_names
            )
            used_cond = " | ".join(f"{rn}.mode = OCCUPIED" for rn in route_names)

            seg_lock_clauses.append(f"({sn}.mode = EXLOCKED -> ({exlocked_cond}))\n")

            if s not in terminal_elements:
                seg_lock_clauses.append(f"({sn}.mode = USED -> ({used_cond}))\n")

    if seg_lock_clauses:
        out.write(f"INVARSPEC\n\tNAME NoSegmentLockModeTransitionError := (\n\t\t{'\t\t& '.join(seg_lock_clauses)}\t);\n\n")

    # no invalid point lock mode transitions
    pt_lock_clauses = []

    for p in system.points:
        if isinstance(p, Point) and p in elem_routes:
            pn = safe_name(p.name)
            route_names = elem_routes[p]
            exlocked_cond = " | ".join(
                f"{rn}.mode in {{ALLOCATING, LOCKED, OCCUPIED}}" for rn in route_names
            )
            used_cond = " | ".join(f"{rn}.mode = OCCUPIED" for rn in route_names)

            pt_lock_clauses.append(f"({pn}.mode = EXLOCKED -> ({exlocked_cond}))\n")

            if p not in terminal_elements:
                pt_lock_clauses.append(f"({pn}.mode = USED -> ({used_cond}))\n")

    if pt_lock_clauses:
        out.write(f"INVARSPEC\n\tNAME NoPointLockModeTransitionError := (\n\t\t{'\t\t& '.join(pt_lock_clauses)}\t);\n\n")
