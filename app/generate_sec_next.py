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

def make_vacant_expr(elem):
    """Return an SMV expression that is true when section `elem` is vacant."""
    sn = safe_name(elem.name)
    if isinstance(elem, Linear):
        return f"{sn}.occDown = FREE & {sn}.occUp = FREE"
    else:
        return f"{sn}.occSNR = FREE & {sn}.occNS = FREE & {sn}.occRS = FREE"

"""
Completed occupancy 'next' generator:
    This new implementation follows the conditional steps in `process_train_movement()`
    from `interlocking.py` and produces explicit SMV cases for HEADOCC / COMPLETETRAINOCC / TAILOCC
    based on route conditions assembled above.
"""

def write_occupancy_transition(system: 'InterlockingSystem', out):
    """
    The pattern implements:
    1. Boundary handling (sections with no incoming neighbor)
    2. Signal-guarded transitions (for sections with entry signals)
    3. Standard train movement states: FREE -> HEADOCC -> COMPLETETRAINOCC -> TAILOCC -> FREE
    4. ERROROCC detection for invalid transitions
    5. Mode-based gating (segment must be in USED mode)
    """
    def get_prev_segment_var(s, direction):
        """Get the previous segment's occupancy variable name for the given direction.

        Returns either a string (single predecessor variable) or a list of
        (act_condition, var) tuples when the predecessor is a point and the
        traversal direction requires splitting by point ACT position.

        Traversal-direction semantics:
            - point.occSNR: train going Stem -> Normal/Reverse (enters from stem_neighbor)
            - point.occNS: train going Normal -> Stem (enters from normal_neighbor)
            - point.occRS: train going Reverse -> Stem (enters from reverse_neighbor)

        For Linear.Down (train moving down, entering from up_neighbor):
            - up_neighbor is Linear -> Linear.occDown
            - up_neighbor is Point and point.normal_neighbor==s or
                point.reverse_neighbor==s -> point.occSNR
                (train traversed SNR direction to reach this branch)
            - up_neighbor is Point and point.stem_neighbor==s
                -> ACT-split: NORMAL->point.occNS, REVERSE->point.occRS
                (train traversed NS or RS direction to reach the stem)

        For Linear.Up (train moving up, entering from down_neighbor):
            - down_neighbor is Linear -> Linear.occUp
            - down_neighbor is Point and point.normal_neighbor==s or
                point.reverse_neighbor==s -> point.occSNR
                (train traversed SNR direction to reach this branch)
            - down_neighbor is Point and point.stem_neighbor==s
                -> ACT-split: NORMAL->point.occNS, REVERSE->point.occRS
                (train traversed NS or RS direction to reach the stem)
        """
        if isinstance(s, Linear):
            if direction == 'Down':
                prev_seg = s.up_neighbor

                if prev_seg:
                    if isinstance(prev_seg, Linear):
                        return f"{safe_name(prev_seg.name)}.occDown"
                    elif isinstance(prev_seg, Point):
                        pn = safe_name(prev_seg.name)
                        if prev_seg.normal_neighbor == s or prev_seg.reverse_neighbor == s:
                            # Train going DOWN entered from point's branch -> was in SNR direction
                            return f"{pn}.occSNR"
                        elif prev_seg.stem_neighbor == s:
                            # Train going DOWN entered from point's stem -> was in NS or RS direction
                            return [(f"{pn}.ACT = NORMAL", f"{pn}.occNS"),
                                    (f"{pn}.ACT = REVERSE", f"{pn}.occRS")]
            elif direction == 'Up':
                prev_seg = s.down_neighbor

                if prev_seg:
                    if isinstance(prev_seg, Linear):
                        return f"{safe_name(prev_seg.name)}.occUp"
                    elif isinstance(prev_seg, Point):
                        pn = safe_name(prev_seg.name)
                        if prev_seg.normal_neighbor == s or prev_seg.reverse_neighbor == s:
                            # Train going UP entered from point's branch -> was in SNR direction
                            return f"{pn}.occSNR"
                        elif prev_seg.stem_neighbor == s:
                            # Train going UP entered from point's stem -> was in NS or RS direction
                            return [(f"{pn}.ACT = NORMAL", f"{pn}.occNS"),
                                    (f"{pn}.ACT = REVERSE", f"{pn}.occRS")]
        elif isinstance(s, Point):
            if direction == 'SNR':
                prev_seg = s.stem_neighbor
            elif direction == 'NS':
                prev_seg = s.normal_neighbor
            elif direction == 'RS':
                prev_seg = s.reverse_neighbor
            else:
                return None

            if prev_seg:
                if isinstance(prev_seg, Linear):
                    # Determine which linear end connects to this point
                    if prev_seg.down_neighbor == s:
                        return f"{safe_name(prev_seg.name)}.occDown"
                    elif prev_seg.up_neighbor == s:
                        return f"{safe_name(prev_seg.name)}.occUp"
                elif isinstance(prev_seg, Point):
                    if prev_seg.stem_neighbor == s:
                        return f"{safe_name(prev_seg.name)}.occSNR"
                    elif prev_seg.normal_neighbor == s:
                        return f"{safe_name(prev_seg.name)}.occNS"
                    elif prev_seg.reverse_neighbor == s:
                        return f"{safe_name(prev_seg.name)}.occRS"
        return None

    def get_entry_signal(s, direction):
        """Get the entry signal for a section/direction if it exists."""
        if isinstance(s, Linear):
            if direction == 'Down':
                return s.up_signal  # Signal guards entry from up direction
            elif direction == 'Up':
                return s.down_signal  # Signal guards entry from down direction
        elif isinstance(s, Point):
            # For points, derive the entry signal from the predecessor segment's boundary signal facing this point.
            if direction == 'SNR':
                prev_seg = s.stem_neighbor
            elif direction == 'NS':
                prev_seg = s.normal_neighbor
            elif direction == 'RS':
                prev_seg = s.reverse_neighbor
            else:
                return None
            if prev_seg and isinstance(prev_seg, Linear):
                if prev_seg.down_neighbor == s:
                    return prev_seg.down_signal
                elif prev_seg.up_neighbor == s:
                    return prev_seg.up_signal
        return None

    def is_last_segment(s, direction):
        if isinstance(s, Linear):
            if direction == 'Down':
                exit_signal = s.down_signal  # Signal at down end
                next_seg = s.down_neighbor
            elif direction == 'Up':
                exit_signal = s.up_signal  # Signal at up end
                next_seg = s.up_neighbor

            return exit_signal is not None and not next_seg
        return False

    def write_occ_next_complete(s, occ_directions):
        """Generate occupancy next transitions for a section.

        Args:
            s: Section (Linear or Point)
            occ_directions: List of direction strings
                            'Down', 'Up' for Linear
                            'SNR', 'NS', 'RS' for Point
        """
        sn = safe_name(s.name)

        for direction in occ_directions:
            var = f"{sn}.occ{direction}"
            out.write(f"\tnext({var}) := case\n")

            prev_var = get_prev_segment_var(s, direction)
            entry_signal = get_entry_signal(s, direction)
            is_destination = is_last_segment(s, direction)

            # Detect ACT-split predecessor (point with stem connecting to this segment)
            is_split = isinstance(prev_var, list)

            # Check if this is a boundary section (no incoming neighbor)
            is_boundary = prev_var is None

            if is_boundary:
                # Boundary sections: trains cannot enter from outside
                out.write(f"\t\t-- stays FREE as no train can enter from out of bounds\n")
                out.write(f"\t\t{var} = FREE : FREE;\n\n")

                out.write(f"\t\t-- ERROROCC if head of a train is here, as the tail has no previous segment\n")
                out.write(f"\t\t{var} = HEADOCC : ERROROCC;\n\n")

                out.write(f"\t\t-- stays COMPLETETRAINOCC if the segment is not in USED mode\n")
                out.write(f"\t\t{var} = COMPLETETRAINOCC & {sn}.mode != USED : COMPLETETRAINOCC;\n\n")

                out.write(f"\t\t-- train moves on with head if train is present\n")
                out.write(f"\t\t{var} = COMPLETETRAINOCC & {sn}.mode = USED : TAILOCC;\n\n")

                out.write(f"\t\t-- train tail leaves if tail is present\n")
                out.write(f"\t\t{var} = TAILOCC : FREE;\n\n")

            if not is_boundary and is_destination:
                # Case 1: Stay FREE if previous segment is FREE or ERROROCC
                out.write(f"\t\t-- stays FREE if previous segment doesnt have a train or has ERROR\n")
                out.write(f"\t\t{var} = FREE & {prev_var} in {{FREE, ERROROCC}} : FREE;\n\n")

                # Case 2: Stay FREE if not allocated (AVAILABLE = not allocated to any route)
                out.write(f"\t\t-- stays FREE if not allocated to a route\n")
                out.write(f"\t\t{var} = FREE & {sn}.mode = AVAILABLE : FREE;\n\n")

                # For points with specific ACT requirements
                point_act_check = ""

                if isinstance(s, Point):
                    if direction == 'NS':
                        point_act_check = f" & {sn}.ACT = NORMAL"
                    elif direction == 'RS':
                        point_act_check = f" & {sn}.ACT = REVERSE"
                    elif direction == 'SNR':
                        point_act_check = f" & {sn}.ACT != INTERMEDIATE"

                # Case 3: Train head may enter (nondeterministic with FREE)
                out.write(f"\t\t-- train head may enter if previous segment has head of a train\n")
                out.write(f"\t\t{var} = FREE & {sn}.mode != AVAILABLE{point_act_check}\n")
                out.write(f"\t\t& {prev_var} = HEADOCC\n")
                out.write(f"\t\t: {{HEADOCC, FREE}};\n\n")

                # Case 4: Train head enters if prev has COMPLETETRAINOCC
                out.write(f"\t\t-- train head enters if previous segment has complete train\n")
                out.write(f"\t\t{var} = FREE & {sn}.mode != AVAILABLE{point_act_check}\n")
                out.write(f"\t\t& {prev_var} = COMPLETETRAINOCC\n")
                out.write(f"\t\t: HEADOCC;\n\n")

                # Case 5: ERROROCC if prev has TAILOCC but this is FREE
                out.write(f"\t\t-- ERROROCC if previous segment has tail but this segment has no head\n")
                out.write(f"\t\t{var} = FREE & {sn}.mode != AVAILABLE{point_act_check}\n")
                out.write(f"\t\t& {prev_var} = TAILOCC\n")
                out.write(f"\t\t: ERROROCC;\n\n")

                # destination segment should have exit signal
                exit_signal = s.down_signal if direction == 'Down' else s.up_signal
                signal_name = safe_name(exit_signal.name)

                # Case 6: Train collects if head present and signal is STOP
                out.write(f"\t\t-- train collects here if head present and signal is STOP\n")
                out.write(f"\t\t{var} = HEADOCC & {signal_name}.ACT = STOP : COMPLETETRAINOCC;\n\n")

                # Case 7: ERROROCC if train head present and signal is GO
                out.write(f"\t\t-- ERROROCC if train head present and signal is GO\n")
                out.write(f"\t\t{var} = HEADOCC & {signal_name}.ACT = GO : ERROROCC;\n\n")

                # Case 8: Train stays COMPLETETRAINOCC and signal is STOP
                out.write(f"\t\t-- train stays here and signal is STOP\n")
                out.write(f"\t\t{var} = COMPLETETRAINOCC & {signal_name}.ACT = STOP : COMPLETETRAINOCC;\n\n")

                # Case 9: ERROROCC if train in COMPLETETRAINOCC and signal is GO
                out.write(f"\t\t-- ERROROCC if train in COMPLETETRAINOCC and signal is GO\n")
                out.write(f"\t\t{var} = COMPLETETRAINOCC & {signal_name}.ACT = GO : ERROROCC;\n\n")

                # Case 10: ERROROCC if train tail is present
                out.write(f"\t\t-- ERROROCC if train tail is present\n")
                out.write(f"\t\t{var} = TAILOCC : ERROROCC;\n\n")

            if not is_boundary and not is_destination: # Standard section with incoming neighbor
                # For points with specific ACT requirements
                point_act_check = ""
                if isinstance(s, Point):
                    if direction == 'NS':
                        point_act_check = f" & {sn}.ACT = NORMAL"
                    elif direction == 'RS':
                        point_act_check = f" & {sn}.ACT = REVERSE"
                    elif direction == 'SNR':
                        point_act_check = f" & {sn}.ACT != INTERMEDIATE"

                if is_split:
                    """
                    ACT-split predecessor: point.stem_neighbor == s
                    prev_var is [(act_cond0, var0), (act_cond1, var1)]

                    For trains exiting a point's stem into this linear segment, the
                    entry signal from get_entry_signal() is the opposite-direction exit
                    signal (e.g. signal3 for DOWN trains), not a gate for trains coming
                    out of the point.  Force no signal gate here.
                    """
                    split_entry_signal = None

                    # Case 1: Stay FREE if all ACT-conditional predecessors are FREE or ERROROCC
                    cond_parts = " | ".join(
                        f"({act_cond} & {act_var} in {{FREE, ERROROCC}})"
                        for act_cond, act_var in prev_var
                    )
                    out.write(f"\t\t-- stays FREE if predecessor point has no train (per ACT position)\n")
                    out.write(f"\t\t{var} = FREE & ({cond_parts}) : FREE;\n\n")

                    # Case 2: Stay FREE if not allocated
                    out.write(f"\t\t-- stays FREE if not allocated\n")
                    out.write(f"\t\t{var} = FREE & {sn}.mode = AVAILABLE : FREE;\n\n")

                    # Entry cases split by ACT (no signal gate for stem exits)
                    if split_entry_signal:
                        signal_name = safe_name(entry_signal.name)

                        for act_cond, act_var in prev_var:
                            out.write(f"\t\t-- train blocked at signal with {act_cond}\n")
                            out.write(f"\t\t{var} = FREE & {sn}.mode = USED\n")
                            out.write(f"\t\t& {act_cond} & {act_var} in {{HEADOCC, COMPLETETRAINOCC}} & {signal_name}.ACT = STOP\n")
                            out.write(f"\t\t: FREE;\n\n")

                            out.write(f"\t\t-- non-deterministic head entry with {act_cond} and signal GO\n")
                            out.write(f"\t\t{var} = FREE & {sn}.mode = USED\n")
                            out.write(f"\t\t& {act_cond} & {act_var} = HEADOCC & {signal_name}.ACT = GO\n")
                            out.write(f"\t\t: {{HEADOCC, FREE}};\n\n")

                            out.write(f"\t\t-- deterministic head entry with {act_cond} and signal GO\n")
                            out.write(f"\t\t{var} = FREE & {sn}.mode = USED\n")
                            out.write(f"\t\t& {act_cond} & {act_var} = COMPLETETRAINOCC & {signal_name}.ACT = GO\n")
                            out.write(f"\t\t: HEADOCC;\n\n")

                            out.write(f"\t\t-- ERROROCC: tail without head with {act_cond} and signal GO\n")
                            out.write(f"\t\t{var} = FREE & {sn}.mode = USED\n")
                            out.write(f"\t\t& {act_cond} & {act_var} = TAILOCC & {signal_name}.ACT = GO\n")
                            out.write(f"\t\t: ERROROCC;\n\n")
                    else:
                        for act_cond, act_var in prev_var:
                            out.write(f"\t\t-- non-deterministic head entry with {act_cond}\n")
                            out.write(f"\t\t{var} = FREE & {sn}.mode != AVAILABLE\n")
                            out.write(f"\t\t& {act_cond} & {act_var} = HEADOCC\n")
                            out.write(f"\t\t: {{HEADOCC, FREE}};\n\n")

                            out.write(f"\t\t-- deterministic head entry with {act_cond}\n")
                            out.write(f"\t\t{var} = FREE & {sn}.mode != AVAILABLE\n")
                            out.write(f"\t\t& {act_cond} & {act_var} = COMPLETETRAINOCC\n")
                            out.write(f"\t\t: HEADOCC;\n\n")

                            out.write(f"\t\t-- ERROROCC: tail without head with {act_cond}\n")
                            out.write(f"\t\t{var} = FREE & {sn}.mode != AVAILABLE\n")
                            out.write(f"\t\t& {act_cond} & {act_var} = TAILOCC\n")
                            out.write(f"\t\t: ERROROCC;\n\n")

                else: # Single predecessor variable (string)
                    # Case 1: Stay FREE if previous segment is FREE or ERROROCC
                    out.write(f"\t\t-- stays FREE if previous segment doesnt have a train or has ERROR\n")
                    out.write(f"\t\t{var} = FREE & {prev_var} in {{FREE, ERROROCC}} : FREE;\n\n")

                    # Case 2: Stay FREE if not allocated to a route
                    out.write(f"\t\t-- stays FREE if not allocated to a route\n")
                    out.write(f"\t\t{var} = FREE & {sn}.mode = AVAILABLE : FREE;\n\n")

                    # Check if there's a signal guard
                    if entry_signal:
                        signal_name = safe_name(entry_signal.name)

                        # Case 3a: Stay FREE if signal STOP (train waits regardless of predecessor)
                        out.write(f"\t\t-- train blocked at signal STOP regardless of predecessor state\n")
                        out.write(f"\t\t{var} = FREE & {sn}.mode != AVAILABLE{point_act_check}\n")
                        out.write(f"\t\t& {prev_var} in {{HEADOCC, COMPLETETRAINOCC}} & {signal_name}.ACT = STOP\n")
                        out.write(f"\t\t: FREE;\n\n")

                        # Case 3b: Non-deterministic head entry from HEADOCC predecessor when signal GO
                        out.write(f"\t\t-- non-deterministic head entry if previous segment has head and signal is GO\n")
                        out.write(f"\t\t{var} = FREE & {sn}.mode != AVAILABLE{point_act_check}\n")
                        out.write(f"\t\t& {prev_var} = HEADOCC & {signal_name}.ACT = GO\n")
                        out.write(f"\t\t: {{HEADOCC, FREE}};\n\n")

                        # Case 3c: Deterministic head entry from COMPLETETRAINOCC predecessor when signal GO
                        out.write(f"\t\t-- train head enters if previous segment has complete train and signal is GO\n")
                        out.write(f"\t\t{var} = FREE & {sn}.mode != AVAILABLE{point_act_check}\n")
                        out.write(f"\t\t& {prev_var} = COMPLETETRAINOCC & {signal_name}.ACT = GO\n")
                        out.write(f"\t\t: HEADOCC;\n\n")

                        # Case 3d: ERROROCC if prev has TAILOCC and signal is GO (invalid)
                        out.write(f"\t\t-- ERROROCC if previous segment has tail but this segment has no head\n")
                        out.write(f"\t\t-- and signal is GO\n")
                        out.write(f"\t\t{var} = FREE & {sn}.mode != AVAILABLE{point_act_check}\n")
                        out.write(f"\t\t& {prev_var} = TAILOCC & {signal_name}.ACT = GO\n")
                        out.write(f"\t\t: ERROROCC;\n\n")
                    else: # No signal guard - standard transitions
                        # Case 3: Train head may enter (nondeterministic with FREE)
                        out.write(f"\t\t-- train head may enter if previous segment has head of a train\n")
                        out.write(f"\t\t{var} = FREE & {sn}.mode != AVAILABLE{point_act_check}\n")
                        out.write(f"\t\t& {prev_var} = HEADOCC\n")
                        out.write(f"\t\t: {{HEADOCC, FREE}};\n\n")

                        # Case 4: Train head enters if prev has COMPLETETRAINOCC
                        out.write(f"\t\t-- train head enters if previous segment has complete train\n")
                        out.write(f"\t\t{var} = FREE & {sn}.mode != AVAILABLE{point_act_check}\n")
                        out.write(f"\t\t& {prev_var} = COMPLETETRAINOCC\n")
                        out.write(f"\t\t: HEADOCC;\n\n")

                        # Case 5: ERROROCC if prev has TAILOCC but this is FREE
                        out.write(f"\t\t-- ERROROCC if previous segment has tail but this segment has no head\n")
                        out.write(f"\t\t{var} = FREE & {sn}.mode != AVAILABLE{point_act_check}\n")
                        out.write(f"\t\t& {prev_var} = TAILOCC\n")
                        out.write(f"\t\t: ERROROCC;\n\n")

                # ERROROCC case for points with wrong ACT position
                if isinstance(s, Point):
                    out.write(f"\t\t-- ERROROCC if train present and aspect is INTERMEDIATE\n")
                    out.write(f"\t\t{var} != FREE & {sn}.ACT = INTERMEDIATE : ERROROCC;\n\n")

                # Check if this section has an exit signal
                exit_signal = None

                if isinstance(s, Linear):
                    if direction == 'Down':
                        exit_signal = s.down_signal  # Signal at down end
                    elif direction == 'Up':
                        exit_signal = s.up_signal  # Signal at up end

                if exit_signal:
                    signal_name = safe_name(exit_signal.name)

                    # Case 6a: Train head leaves or collects if head present and signal is GO
                    out.write(f"\t\t-- train head leaves or train collects here if head present and signal is GO\n")
                    out.write(f"\t\t{var} = HEADOCC & {signal_name}.ACT = GO : {{COMPLETETRAINOCC, TAILOCC}};\n\n")

                    # Case 6b: Train collects if head present and signal is STOP
                    out.write(f"\t\t-- train collects here if head present and signal is STOP\n")
                    out.write(f"\t\t{var} = HEADOCC & {signal_name}.ACT = STOP : COMPLETETRAINOCC;\n\n")

                    # Case 7a: Train stays if COMPLETETRAINOCC and signal is STOP
                    out.write(f"\t\t-- train stays here if train is present and signal is STOP\n")
                    out.write(f"\t\t{var} = COMPLETETRAINOCC & {signal_name}.ACT = STOP : COMPLETETRAINOCC;\n\n")

                    # Case 7b: Train moves on if COMPLETETRAINOCC and signal is GO
                    out.write(f"\t\t-- train moves on with head if train is present and signal is GO\n")
                    out.write(f"\t\t{var} = COMPLETETRAINOCC & {signal_name}.ACT = GO : TAILOCC;\n\n")
                else: # No exit signal - standard transitions
                    # Case 6: Train head leaves or train collects
                    out.write(f"\t\t-- train head leaves or train collects here if head present\n")
                    out.write(f"\t\t{var} = HEADOCC : {{COMPLETETRAINOCC, TAILOCC}};\n\n")

                    # Case 7: Train moves on with head
                    out.write(f"\t\t-- train moves on with head if train is present\n")
                    out.write(f"\t\t{var} = COMPLETETRAINOCC : TAILOCC;\n\n")

                # Case 8: Train tail leaves
                out.write(f"\t\t-- train tail leaves if tail is present\n")
                out.write(f"\t\t{var} = TAILOCC : FREE;\n\n")

            # Default case: maintain current state
            out.write(f"\t\tTRUE : {var};\n")
            out.write(f"\tesac;\n")

            # Add blank line between directions
            if direction != occ_directions[-1]:
                out.write(f"\n")

        out.write(f"\n")

    out.write("\t-- SEGMENTS OCCUPANCY NEXT --\n")

    for s in system.sections:
        if isinstance(s, Linear):
            out.write(f"\t-- {s.name}\n")
            write_occ_next_complete(s, ['Down', 'Up'])

    out.write("\t-- POINTS OCCUPANCY NEXT --\n")

    for p in system.points:
        out.write(f"\t-- {p.name}\n")
        write_occ_next_complete(p, ['SNR', 'NS', 'RS'])

    out.write("\n")
