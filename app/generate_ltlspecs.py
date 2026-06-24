from entity import Linear, Point
from interlocking import InterlockingSystem
from route_op import last_element


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

def write_ltl_properties(system: InterlockingSystem, out):
    out.write("-- LTL Properties --\n")

    for r in system.routes:
        rn = safe_name(r.name)
        r_dir = r.entry_dir.capitalize()

        last = last_element(r)
        lsn = safe_name(last.name)

        # Point terminals use occSNR; Linear terminals use occ{entry_dir}
        if isinstance(last, Linear):
            last_occ_var = f"{lsn}.occ{r_dir}"
            occ_dir_label = r_dir
        else:
            last_occ_var = f"{lsn}.occSNR"
            occ_dir_label = "Snr"

        # Route is eventually released: G(OCCUPIED -> F(FREE))
        route_released = f"G({rn}.mode = OCCUPIED -> F({rn}.mode = FREE))"
        out.write(f"LTLSPEC\n\tNAME {rn}IsReleasedEventually :=\n\t\t{route_released};\n\n")

        """
        Train stably reaches destination: F(G(terminal = COMPLETETRAINOCC))
        
        Guarded by route OCCUPIED: if the route is never occupied (no dispatched train),
        the implication is vacuously TRUE. Routes with a train that goes OCCUPIED
        must deliver the train to the terminal permanently.
        """
        train_reached = f"F({rn}.mode = OCCUPIED) -> F(G({last_occ_var} = COMPLETETRAINOCC))"
        out.write(f"LTLSPEC\n\tNAME {rn}TrainReaches{lsn.capitalize()}{occ_dir_label}EventuallyForever :=\n\t\t{train_reached};\n\n")

        """
        Element release wave - all consecutive pairs along path.
        
        Skip the last pair (curr=path[-2], nxt=terminal) because the terminal
        element stays USED with the parked train; it never goes AVAILABLE.
        """
        path = r.path

        if len(path) >= 3:
            for i in range(len(path) - 2):
                curr = path[i]
                nxt = path[i + 1]
                csn = safe_name(curr.name)
                nsn = safe_name(nxt.name)
                elem_released = f"G(({nsn}.mode = USED & {csn}.mode = AVAILABLE) -> F({nsn}.mode = AVAILABLE))"
                out.write(f"LTLSPEC\n\tNAME {rn}ElementReleaseWave{csn.capitalize()}To{nsn.capitalize()} :=\n\t\t{elem_released};\n\n")

    # mutual exclusion per conflict pair (de-duplicated across all routes)
    out.write("-- Route mutual exclusion --\n")
    seen_mutex_pairs: set = set()

    for r in system.routes:
        rn = safe_name(r.name)

        for cr in r.conflicts:
            crn = safe_name(cr.name)
            pair = tuple(sorted([rn, crn]))

            if pair in seen_mutex_pairs:
                continue

            seen_mutex_pairs.add(pair)
            mutex_clause = f"G(!({pair[0]}.mode = OCCUPIED & {pair[1]}.mode = OCCUPIED))"
            out.write(f"LTLSPEC\n\tNAME {pair[0]}And{pair[1].capitalize()}MutuallyExclusive :=\n\t\t{mutex_clause};\n\n")

    """    
    Sanity checks: initial occupancy comes from extras_config.yml, not queryable here.
    Add manually after generation, e.g.:
        LTLSPEC NAME SanityCheckPos := F(G(<start_seg>.occ<Dir> = FREE & ...));
        LTLSPEC NAME SanityCheckNeg := !(F(G(<start_seg>.occ<Dir> = FREE & ...)));
    """
    out.write("-- Sanity checks: add manually based on extras_config.yml initial train positions\n")
    out.write("-- LTLSPEC NAME SanityCheckPos := F(G(<start_seg>.occ<Dir> = FREE & ...));\n")
    out.write("-- LTLSPEC NAME SanityCheckNeg := !(F(G(<start_seg>.occ<Dir> = FREE & ...)));\n")
    out.write("\n")
