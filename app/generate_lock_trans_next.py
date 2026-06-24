from typing import Dict, List, Optional, Tuple

from entity import Linear, Point, Route, Section
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

def make_occupied_expr(elem) -> str:
    """Return an SMV expression that is true when section `elem` is occupied."""
    sn = safe_name(elem.name)

    if isinstance(elem, Linear):
        return f"({sn}.occDown != FREE | {sn}.occUp != FREE)"
    else:
        return f"({sn}.occSNR != FREE | {sn}.occNS != FREE | {sn}.occRS != FREE)"

def make_arrival_expr(elem, route: 'Route') -> str:
    """Return an SMV expression that is true when a train has arrived at terminal `elem`."""
    sn = safe_name(elem.name)
    # entry_dir is a StrEnum whose value is "down" or "up"
    dir_cap = str(route.entry_dir).capitalize()

    if isinstance(elem, Linear):
        return f"{sn}.occ{dir_cap} in {{HEADOCC, COMPLETETRAINOCC}}"
    else:
        # Point as terminal: train enters via stem direction
        return f"{sn}.occSNR in {{HEADOCC, COMPLETETRAINOCC}}"

def get_element_route_info(system: 'InterlockingSystem') -> Dict[Section, List[Tuple[Route, int]]]:
    """
    Build a mapping from each element to the list of (route, index) pairs
    where the element appears in route.path at the given index.
    """
    elem_to_routes: Dict[Section, List[Tuple[Route, int]]] = {}

    for route in system.routes:
        for idx, elem in enumerate(route.path):
            if elem not in elem_to_routes:
                elem_to_routes[elem] = []
            elem_to_routes[elem].append((route, idx))

    return elem_to_routes

def get_point_act_for_route(route: Route, point: Point) -> Optional[str]:
    """Get the required ACT position for a point in a given route."""
    if point in route.points:
        pos = route.points[point]
        # pos is PointAspect enum
        return str(pos).upper()
    return None

# -----------------------------------------------------------------------------
# MODE transitions generator:
# Implements: AVAILABLE -> EXLOCKED -> USED -> AVAILABLE
# -----------------------------------------------------------------------------

def write_mode_transitions(system: 'InterlockingSystem', out):
    """
    Generate next(elem.mode) transitions for all lockable elements.

    Life-cycle:
    1. AVAILABLE -> EXLOCKED: when route.mode = ALLOCATING
    2. EXLOCKED -> USED: when route.mode = OCCUPIED, prev element USED,
                         next element EXLOCKED, element vacant (non-terminal)
                         or element occupied with arrived train (terminal)
    3. USED -> AVAILABLE: when element vacant, elem.prev = RELEASED,
                          next element (USED or prev=PENDING)
    """
    elem_to_routes = get_element_route_info(system)

    out.write("\t-- SEGMENTS/SECTIONS MODE NEXT --\n")

    # Process all elements (sections + points)
    all_elements = list(system.sections) + list(system.points)

    for elem in all_elements:
        if elem not in elem_to_routes:
            continue  # Element not used in any route

        sn = safe_name(elem.name)
        route_infos = elem_to_routes[elem]

        out.write(f"\tnext({sn}.mode) := case\n")

        # --- AVAILABLE -> EXLOCKED ---
        # Triggered when any route using this element enters ALLOCATING
        route_allocating_conds = []

        for route, idx in route_infos:
            rn = safe_name(route.name)
            route_allocating_conds.append(f"{rn}.mode = ALLOCATING")

        allocating_cond = " | ".join(route_allocating_conds)
        out.write(f"\t\t{sn}.mode = AVAILABLE\n")
        out.write(f"\t\t& ({allocating_cond})\n")
        out.write(f"\t\t: EXLOCKED;\n\n")

        """
        # --- EXLOCKED -> USED ---
        Vacancy/arrival check is per-route:
          - Non-terminal elements: vacancy check (train has passed through)
          - Terminal elements: arrival check (train has arrived and stays)
        """
        exlocked_to_used_conds = []

        for route, idx in route_infos:
            rn = safe_name(route.name)
            path = route.path
            cond_parts = [f"{rn}.mode = OCCUPIED"]

            """
            Previous element must be USED (train has physically passed through it).
            Using USED (not != AVAILABLE) prevents premature EXLOCKED->USED transitions
            for elements the train hasn't reached yet. The prev-chain release handles
            the re-allocation race via the relaxed upstream condition below.
            """
            if idx > 0:
                prev_elem = path[idx - 1]
                prev_sn = safe_name(prev_elem.name)
                cond_parts.append(f"{prev_sn}.mode = USED")

            # Next element must be EXLOCKED (last element has no next)
            if idx < len(path) - 1:
                next_elem = path[idx + 1]
                next_sn = safe_name(next_elem.name)
                cond_parts.append(f"{next_sn}.mode = EXLOCKED")

            # Point ACT check if this is a point
            if isinstance(elem, Point):
                act_pos = get_point_act_for_route(route, elem)
                if act_pos:
                    cond_parts.append(f"{sn}.ACT = {act_pos}")

            # Bug M1 fix: terminal elements use arrival check; non-terminals use vacancy check
            if idx == len(path) - 1:
                cond_parts.append(make_arrival_expr(elem, route))
            else:
                if isinstance(elem, Linear):
                    cond_parts.append(f"{sn}.occDown = FREE & {sn}.occUp = FREE")
                else:
                    cond_parts.append(f"{sn}.occSNR = FREE & {sn}.occNS = FREE & {sn}.occRS = FREE")

            route_cond = "\n\t\t\t& ".join(cond_parts)
            exlocked_to_used_conds.append(f"(\n\t\t\t{route_cond}\n\t\t)")

        if len(exlocked_to_used_conds) == 1:
            out.write(f"\t\t{sn}.mode = EXLOCKED\n")
            out.write(f"\t\t-- previous element in USED and next element in EXLOCKED\n")
            out.write(f"\t\t& {exlocked_to_used_conds[0]}\n")
            out.write(f"\t\t: USED;\n\n")
        else:
            combined_cond = "\n\t\t| ".join(exlocked_to_used_conds)
            out.write(f"\t\t{sn}.mode = EXLOCKED\n")
            out.write(f"\t\t-- previous element in USED and next element in EXLOCKED\n")
            out.write(f"\t\t& (\n\t\t{combined_cond}\n\t\t)\n")
            out.write(f"\t\t: USED;\n\n")

        """
        # --- USED -> AVAILABLE ---
        For each route, check: route OCCUPIED, element vacant, elem.prev = RELEASED,
            next element (USED or prev=PENDING), (point ACT if applicable)
        Vacancy check is shared: terminal elements stay occupied (train arrives and stays),
            so this transition correctly never fires for terminals.
        """
        vacant_expr = make_vacant_expr(elem)
        used_to_available_conds = []

        for route, idx in route_infos:
            rn = safe_name(route.name)
            path = route.path
            cond_parts = [f"{rn}.mode = OCCUPIED"]

            # Next element check (last element has special handling)
            if idx < len(path) - 1:
                next_elem = path[idx + 1]
                next_sn = safe_name(next_elem.name)
                next_cond = f"({next_sn}.mode = USED | {next_sn}.prev = PENDING)"

                # For points as next element, add ACT check
                if isinstance(next_elem, Point):
                    next_act_pos = get_point_act_for_route(route, next_elem)

                    if next_act_pos:
                        next_cond = f"(({next_sn}.mode = USED | {next_sn}.prev = PENDING) & {next_sn}.ACT = {next_act_pos})"

                cond_parts.append(next_cond)

            # Point ACT check if this is a point
            if isinstance(elem, Point):
                act_pos = get_point_act_for_route(route, elem)

                if act_pos:
                    cond_parts.append(f"{sn}.ACT = {act_pos}")

            route_cond = "\n\t\t\t& ".join(cond_parts)
            used_to_available_conds.append(f"(\n\t\t\t{route_cond}\n\t\t)")

        if len(used_to_available_conds) == 1:
            out.write(f"\t\t{sn}.mode = USED\n")
            out.write(f"\t\t-- next element mode in USED or next element prev in PENDING\n")
            out.write(f"\t\t& {used_to_available_conds[0]}\n")
            out.write(f"\t\t& ({vacant_expr})\n")
            out.write(f"\t\t& {sn}.prev = RELEASED\n")
            out.write(f"\t\t: AVAILABLE;\n\n")
        else:
            combined_cond = "\n\t\t| ".join(used_to_available_conds)
            out.write(f"\t\t{sn}.mode = USED\n")
            out.write(f"\t\t-- next element mode in USED or next element prev in PENDING\n")
            out.write(f"\t\t& (\n\t\t{combined_cond}\n\t\t)\n")
            out.write(f"\t\t& ({vacant_expr})\n")
            out.write(f"\t\t& {sn}.prev = RELEASED\n")
            out.write(f"\t\t: AVAILABLE;\n\n")

        # Default: maintain current mode
        out.write(f"\t\tTRUE : {sn}.mode;\n")
        out.write(f"\tesac;\n\n")


# -----------------------------------------------------------------------------
# PREV transitions generator:
# Implements: PENDING -> RELEASED -> PENDING (reset)
# -----------------------------------------------------------------------------

def write_prev_transitions(system: 'InterlockingSystem', out):
    """
    Generate next(elem.prev) transitions for all lockable elements.

    Life-cycle:
    PENDING -> RELEASED: when element.mode = USED, route.mode = OCCUPIED,
                         and occupancy/upstream conditions are met:
        - Non-terminal elements: element is vacant (train has moved on) +
                                 prev_elem.mode = AVAILABLE & prev_elem.prev = PENDING & prev_elem vacant
        - Terminal elements: train has arrived (occ{dir} in {HEADOCC, COMPLETETRAINOCC}) +
                             prev_elem.mode = AVAILABLE & prev_elem.prev = PENDING & prev_elem vacant
        - First element (no prev): no upstream check; just route OCCUPIED & element vacant/arrived

    RELEASED -> PENDING: reset when element returns to AVAILABLE.
                         Required so downstream prev releases can fire in the next cycle.
    """
    elem_to_routes = get_element_route_info(system)

    out.write("\t-- SEGMENTS/SECTIONS PREV NEXT --\n")

    # Process all elements (sections + points)
    all_elements = list(system.sections) + list(system.points)

    for elem in all_elements:
        if elem not in elem_to_routes:
            continue  # Element not used in any route

        sn = safe_name(elem.name)
        route_infos = elem_to_routes[elem]

        # Check if this element is always the first element
        is_always_first = all(idx == 0 for route, idx in route_infos)

        # Check if this element is always the last element
        is_always_last = all(idx == len(r.path) - 1 for r, idx in route_infos)

        out.write(f"\tnext({sn}.prev) := case\n")

        # Build PENDING -> RELEASED conditions (per-route)
        prev_release_conds = []

        for route, idx in route_infos:
            rn = safe_name(route.name)
            path = route.path
            cond_parts = [f"{rn}.mode = OCCUPIED"]

            """
            Bug P2/P3/P4 fix: occupancy check is per-route based on element's role
                - Non-terminal: element is vacant (USED implies train has passed through)
                - Terminal: train has arrived and stays (arrival check)
            """
            if idx == len(path) - 1:
                # Terminal element: check train arrival direction
                cond_parts.append(make_arrival_expr(elem, route))
            else:
                # Non-terminal: element is vacant when in USED mode
                if isinstance(elem, Linear):
                    cond_parts.append(f"({sn}.occDown = FREE & {sn}.occUp = FREE)")
                else:
                    cond_parts.append(f"({sn}.occSNR = FREE & {sn}.occNS = FREE & {sn}.occRS = FREE)")

            """
            Previous element upstream check (first element has no upstream).
            
            Accept AVAILABLE or EXLOCKED (re-allocated by new route) with prev=PENDING.
            
            When a new route grabs the prev element (AVAILABLE->EXLOCKED) before this
            element's prev fires, prev.prev has already reset to PENDING, so the combined
            condition (AVAILABLE|EXLOCKED) & prev=PENDING correctly signals "released".
            """
            if idx > 0:
                prev_elem = path[idx - 1]
                prev_sn = safe_name(prev_elem.name)
                prev_vacant = make_vacant_expr(prev_elem)
                cond_parts += [
                    f"({prev_sn}.mode = AVAILABLE | {prev_sn}.mode = EXLOCKED)",
                    f"{prev_sn}.prev = PENDING",
                    f"({prev_vacant})"
                ]

            # Point ACT check if this is a point
            if isinstance(elem, Point):
                act_pos = get_point_act_for_route(route, elem)

                if act_pos:
                    cond_parts.append(f"{sn}.ACT = {act_pos}")

            route_cond = "\n\t\t\t& ".join(cond_parts)
            prev_release_conds.append(f"(\n\t\t\t{route_cond}\n\t\t)")

        if prev_release_conds:
            if len(prev_release_conds) == 1:
                out.write(f"\t\t{sn}.prev = PENDING\n")
                out.write(f"\t\t& {sn}.mode = USED\n")
                out.write(f"\t\t-- previous element released with mode in AVAILABLE and prev in PENDING\n")
                out.write(f"\t\t& {prev_release_conds[0]}\n")
                out.write(f"\t\t: RELEASED;\n\n")
            else:
                combined_cond = "\n\t\t| ".join(prev_release_conds)
                out.write(f"\t\t{sn}.prev = PENDING\n")
                out.write(f"\t\t& {sn}.mode = USED\n")
                out.write(f"\t\t-- previous element released with mode in AVAILABLE and prev in PENDING\n")
                out.write(f"\t\t& (\n\t\t{combined_cond}\n\t\t)\n")
                out.write(f"\t\t: RELEASED;\n\n")

        # Bug P1 fix: RELEASED -> PENDING reset so downstream chain can fire in next cycle
        out.write(f"\t\t{sn}.prev = RELEASED & {sn}.mode = AVAILABLE : PENDING;\n\n")

        # Default: maintain current prev state
        out.write(f"\t\tTRUE : {sn}.prev;\n")
        out.write(f"\tesac;")

        # Add comment for special elements
        if is_always_first or is_always_last:
            out.write(" -- End segment")

        out.write(f"\n\n")
