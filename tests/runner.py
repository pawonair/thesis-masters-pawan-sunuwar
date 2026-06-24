"""
Generalized simulation runner for sectional interlocking tests.

Usage
-----
1. Define a TestScenario with layout name, initial train positions, routes
   to activate, liveness goals, and any signal corrections needed to fix
   parser output.
2. Call run_scenario(scenario) — returns a result dict.
3. Call print_result(name, result) to display a summary.

The runner loads the YAML configs from configs/<layout>/, calls the existing
parser, resolves route entry/exit signals from string names to Signal objects,
applies scenario-level signal corrections, sets initial occupancy, marks the
requested routes, then steps the InterlockingSystem until all goals are met,
a deadlock is detected, or the step limit is reached.

Step output from interlocking.py is suppressed by default (verbose=False).
"""

import io
import os
import sys
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from typing import Dict, List, Optional

_APP_DIR = os.path.join(os.path.dirname(__file__), '..', 'app')
_CONFIGS_DIR = os.path.join(os.path.dirname(__file__), '..', 'configs')

if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

import yaml  # requires pyyaml; install with: pip install pyyaml

from entity import ElementOcc, RouteMode, Signal
from interlocking import InterlockingSystem
from parser import parse_route as _parse_route


# ---------------------------------------------------------------------------
# Scenario dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TrainGoal:
    """Liveness goal: segment `segment` must have occupancy `state` on `face`."""
    segment: str
    face: str  # occDown | occUp | occSNR | occNS | occRS
    state: ElementOcc = ElementOcc.COMPLETETRAINOCC


@dataclass
class TestScenario:
    """
    Full specification for one simulation test.

    layout
        Short layout name (e.g. '2_Point') resolved to configs/<layout>/,
        or an absolute/relative path to the layout directory.

    trains
        Initial occupancy overrides: {segment_name: {face: ElementOcc}}.
        Example: {'seg3': {'occUp': ElementOcc.COMPLETETRAINOCC}}

    routes
        Route names to set to MARKED at the start (e.g. ['r0', 'r2']).

    goals
        Liveness goals that must all be satisfied for the test to pass.

    signal_corrections
        Per-segment signal overrides applied after parsing.
        {segment_name: {'up': signal_name_or_None, 'down': signal_name_or_None}}
        Use this to fix parser signal mis-assignments without touching parser.py.

    neighbor_corrections
        Per-segment neighbor overrides applied after parsing.
        {segment_name: {'up': neighbor_name_or_None, 'down': neighbor_name_or_None}}
        Neighbor names may be Linear segment names or Point names.
        Use this to fix parser neighbor mis-assignments (e.g. overwritten connections).

    max_steps
        Step limit before the run is declared a timeout.
    """
    layout: str
    name: str
    trains: Dict[str, Dict[str, ElementOcc]] = field(default_factory=dict)
    routes: List[str] = field(default_factory=list)
    goals: List[TrainGoal] = field(default_factory=list)
    signal_corrections: Dict[str, Dict[str, Optional[str]]] = field(default_factory=dict)
    neighbor_corrections: Dict[str, Dict[str, Optional[str]]] = field(default_factory=dict)
    max_steps: int = 60


# ---------------------------------------------------------------------------
# System loading
# ---------------------------------------------------------------------------

def _resolve_layout_dir(layout: str) -> str:
    if os.path.isdir(layout):
        return layout
    candidate = os.path.join(_CONFIGS_DIR, layout)
    if os.path.isdir(candidate):
        return candidate
    raise FileNotFoundError(f"Layout directory not found: {layout!r}")


def load_system(layout_dir: str) -> InterlockingSystem:
    """Parse config files and return a fully wired InterlockingSystem."""
    table_path = os.path.join(layout_dir, 'interlocking_table.yml')
    extras_path = os.path.join(layout_dir, 'extras_config.yml')
    point_path = os.path.join(layout_dir, '..', 'point_config.yml')

    with open(table_path) as f: table = yaml.safe_load(f)
    with open(extras_path) as f: extras = yaml.safe_load(f)
    with open(point_path) as f: pts = yaml.safe_load(f)

    system = InterlockingSystem()
    _parse_route(system, table, extras, pts)
    _resolve_route_signals(system)
    return system


def _resolve_route_signals(system: InterlockingSystem) -> None:
    """Promote entry_signal / exit_signal from string names to Signal objects."""
    sig_map = {s.name: s for s in system.signals}
    for route in system.routes:
        if isinstance(route.entry_signal, str):
            route.entry_signal = sig_map.get(route.entry_signal, route.entry_signal)
        if isinstance(route.exit_signal, str):
            route.exit_signal = sig_map.get(route.exit_signal, route.exit_signal)


def _apply_neighbor_corrections(system: InterlockingSystem,
                                corrections: Dict[str, Dict[str, Optional[str]]]) -> None:
    """Overwrite segment neighbor assignments to fix parser output."""
    sec_map = {s.name: s for s in system.sections}
    pt_map = {p.name: p for p in system.points}

    def _resolve(name):
        if name is None:
            return None
        if name in sec_map:
            return sec_map[name]
        if name in pt_map:
            return pt_map[name]
        raise ValueError(f"Neighbor correction references unknown element: {name!r}")

    for seg_name, dirs in corrections.items():
        sec = sec_map.get(seg_name)
        if sec is None:
            raise ValueError(f"Neighbor correction references unknown segment: {seg_name!r}")
        if 'up' in dirs:
            sec.up_neighbor = _resolve(dirs['up'])
        if 'down' in dirs:
            sec.down_neighbor = _resolve(dirs['down'])


def _apply_signal_corrections(system: InterlockingSystem,
                              corrections: Dict[str, Dict[str, Optional[str]]]) -> None:
    """Overwrite segment signal assignments to fix parser output."""
    sig_map = {s.name: s for s in system.signals}
    sec_map = {s.name: s for s in system.sections}

    for seg_name, dirs in corrections.items():
        sec = sec_map.get(seg_name)
        if sec is None:
            raise ValueError(f"Signal correction references unknown segment: {seg_name!r}")
        if 'up' in dirs:
            sec.up_signal = sig_map[dirs['up']] if dirs['up'] else None
        if 'down' in dirs:
            sec.down_signal = sig_map[dirs['down']] if dirs['down'] else None


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------

def run_scenario(scenario: TestScenario, verbose: bool = False) -> dict:
    """
    Run a test scenario and return a result dict:
        passed      — True if all goals met and no safety violations
        completed   — True if all liveness goals were reached
        steps       — number of steps executed
        violations  — list of (step, message) safety violation tuples
        reason      — 'deadlock' or 'timeout' when not completed (omitted otherwise)
    """
    layout_dir = _resolve_layout_dir(scenario.layout)
    system = load_system(layout_dir)

    if scenario.neighbor_corrections:
        _apply_neighbor_corrections(system, scenario.neighbor_corrections)

    if scenario.signal_corrections:
        _apply_signal_corrections(system, scenario.signal_corrections)

    sec_map = {s.name: s for s in system.sections}
    pt_map = {p.name: p for p in system.points}
    route_map = {r.name: r for r in system.routes}

    # Apply initial train occupancy
    for seg_name, faces in scenario.trains.items():
        elem = sec_map.get(seg_name) or pt_map.get(seg_name)
        if elem is None:
            raise ValueError(f"Segment {seg_name!r} not found in layout {scenario.layout!r}")
        for face, occ in faces.items():
            setattr(elem, face, occ)

    # Mark active routes
    for rname in scenario.routes:
        r = route_map.get(rname)
        if r is None:
            raise ValueError(f"Route {rname!r} not found in layout {scenario.layout!r}")
        r.MODE = RouteMode.MARKED

    def goals_met() -> bool:
        for g in scenario.goals:
            elem = sec_map.get(g.segment) or pt_map.get(g.segment)
            if elem is None or getattr(elem, g.face, ElementOcc.FREE) != g.state:
                return False
        return True

    violations: List[tuple] = []

    for step in range(1, scenario.max_steps + 1):
        if verbose:
            changed = system.step()
        else:
            with redirect_stdout(io.StringIO()):
                changed = system.step()

        for err in system.safety_violations():
            violations.append((step, err))

        if goals_met():
            return {
                'passed': not violations,
                'completed': True,
                'steps': step,
                'violations': violations,
            }

        if not changed:
            return {
                'passed': False,
                'completed': False,
                'steps': step,
                'violations': violations,
                'reason': 'deadlock',
            }

    return {
        'passed': False,
        'completed': False,
        'steps': scenario.max_steps,
        'violations': violations,
        'reason': 'timeout',
    }


# ---------------------------------------------------------------------------
# Result display
# ---------------------------------------------------------------------------

def print_result(scenario: TestScenario, result: dict) -> None:
    width = 62
    status = 'PASSED' if result['passed'] else 'FAILED'
    print(f"\n{'=' * width}")
    print(f"Layout   : {scenario.layout}")
    print(f"Scenario : {scenario.name}")
    print(f"Result   : {status}")
    print(f"Steps    : {result['steps']}")

    if result['violations']:
        print(f"Safety violations ({len(result['violations'])}):")
        for step, msg in result['violations']:
            print(f"  [step {step:3d}] {msg}")

    if not result['completed']:
        print(f"Reason   : {result.get('reason', 'unknown')}")
    else:
        print("Goals:")
        for g in scenario.goals:
            print(f"  {g.segment}.{g.face} = {g.state}  ✓")

    print(f"{'=' * width}")
