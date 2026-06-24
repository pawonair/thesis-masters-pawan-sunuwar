import sys
from pathlib import Path

from entity import Linear
from generate_assigns import write_assign_section
from generate_invars import write_invariants
from generate_lock_trans_next import (write_mode_transitions,
                                      write_prev_transitions)
from generate_ltlspecs import write_ltl_properties
from generate_route_next import write_route_interlocking
from generate_sec_next import write_occupancy_transition
from interlocking import InterlockingSystem


def make_vacant_expr(elem):
    """Return an SMV expression that is true when section `elem` is vacant."""
    sn = safe_name(elem.name)
    if isinstance(elem, Linear):
        return f"({sn}.occDown = FREE & {sn}.occUp = FREE)"
    else:
        return f"({sn}.occSNR = FREE & {sn}.occNS = FREE & {sn}.occRS = FREE)"

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

def write_header(out):
    BASE_DIR = Path(__file__).resolve().parent
    smv_template_dir = BASE_DIR.parent/'smv_model/templates'
    signal_module_path = smv_template_dir/'signal_module.smv'
    point_module_path = smv_template_dir/'point_module.smv'
    linear_module_path = smv_template_dir/'linear_module.smv'
    route_module_path = smv_template_dir/'route_module.smv'

    # Header
    out.write(f"""-------------------------------------------------------------------------------
-- ############### SWTbhan Lite ############### --

-- Auto-generated SMV model for SWTbahn
-- DO NOT EDIT - Regenerate with 'tools/generate_smv.sh'
-------------------------------------------------------------------------------\n\n""")
    
    # Signal module
    if Path.exists(signal_module_path):
        SIGNAL_MODULE = signal_module_path.read_text()
        out.write(SIGNAL_MODULE)

    # Point module
    if Path.exists(point_module_path):
        POINT_MODULE = point_module_path.read_text()
        out.write(POINT_MODULE)

    # Linear module
    if Path.exists(linear_module_path):
        LINEAR_MODULE = linear_module_path.read_text()
        out.write(LINEAR_MODULE)

    # Route module
    if Path.exists(route_module_path):
        ROUTE_MODULE = route_module_path.read_text()
        out.write(ROUTE_MODULE)

def write_var_section(system: InterlockingSystem, out):
    out.write("""\n\n-------------------------------------------------------------------------------
-- Track Section Module --
-- This bundles all segments/sections, points, train movement etc.
-------------------------------------------------------------------------------
""")
    out.write("MODULE TrackSection -- Segments/sections + point switching + signal comm\n")
    out.write("VAR\n")

    def get_id_int(name: str):
        if name.isalnum():
            res = [int(x) for x in [*name] if x.isnumeric()]
            id_int = int("".join(str(n) for n in res))
            return id_int
        else:
            return 0

    # Route vars + action booleans
    for r in system.routes:
        rn = safe_name(r.name)
        r_id = get_id_int(rn)
        out.write(f"\t{rn} : Route({r_id});\n")
    out.write("\n")

    # Segment vars
    for s in system.sections:
        sn = safe_name(s.name)
        sn_id = get_id_int(sn)
        out.write(f"\t{sn} : Linear({sn_id});\n")
    out.write("\n")
    
    # Point vars
    for p in system.points:
        pn = safe_name(p.name)
        pn_seg = safe_name(p.segName)
        pn_id = get_id_int(pn)
        pn_seg_id = get_id_int(pn_seg)
        out.write(f"\t{pn}CMD : {{NORMAL, REVERSE}};\n")
        out.write(f"\t{pn} : Point({pn_id}, {pn_seg_id}, {pn}CMD);\n\n")
    out.write("\n")

    # Signals
    for sig in system.signals:
        sn = safe_name(sig.name)
        sn_id = get_id_int(sn)
        out.write(f"\t{sn}CMD : {{GO, STOP}};\n")
        out.write(f"\t{sn} : Signal({sn_id}, {sn}CMD);\n\n")
    out.write("\n")

def generate_from_system(system: InterlockingSystem, out=sys.stdout, seg_up=None, seg_down=None):
    write_header(out)
    write_var_section(system, out)
    write_assign_section(system, out, seg_up=seg_up, seg_down=seg_down)
    write_mode_transitions(system, out)
    write_prev_transitions(system, out)
    write_occupancy_transition(system, out)
    write_invariants(system, out)
    write_ltl_properties(system, out)
    write_route_interlocking(system, out)
    
    # Main module
    out.write("""-------------------------------------------------------------------------------
-- Main Module --
-- Routes grant states in an interlocked layout
-------------------------------------------------------------------------------
MODULE main
VAR
	iSys : InterlockingSystem;

-- Fairness: all infinite executions are fair (required for non-vacuous LTL)
FAIRNESS TRUE
-------------------------------------------------------------------------------
""")
