#!/usr/bin/env python3
"""
It reuses the existing machinery rather than re-implementing it:
    - runner.load_system / _apply_signal_corrections / _apply_neighbor_corrections
      do the parsing + corrections, exactly as the tests do.
    - The verified TestScenario objects already defined in your test_*.py files
      are the source of truth for train positions, route selection, and the
      parser corrections each layout needs. This file discovers them and replays
      them through the real InterlockingSystem, snapshotting state after every
      step into the JSON shape the frontend reads.

So there is NO second copy of the engine and NO second copy of the scenario
setup. If you add a test_*.py with a TestScenario, the UI can drive it for free.

Two ways to use it (pick one — both are stdlib only)
----------------------------------------------------
    # 1. Live server: serves the UI and the API on one port (no CORS, no build)
    python tests/sim_bridge.py serve            # then open http://localhost:8000

    # 2. Offline bake: write static step files the UI fetches with no server
    python tests/sim_bridge.py export           # writes web/steps/*.json

Faithfulness
------------
A request whose {layout, routes} set matches a TestScenario reproduces the
verified run step-for-step. A request that matches no scenario is reported as
"unsupported" — the frontend then transparently falls back to its in-browser
synthesizer, so nothing breaks and you never see a fabricated engine timeline.
"""
from __future__ import annotations

import argparse
import importlib
import io
import json
import os
import pkgutil
import sys
from contextlib import redirect_stdout
from urllib.parse import urlparse, parse_qs

# --- make 'runner', the test modules, and the engine importable --------------
# This mirrors exactly what every test_*.py does, so imports resolve the same
# way whether you run pytest or this file.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))  # .../tests
_REPO_DIR = os.path.dirname(_THIS_DIR)  # repo root
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from runner import (  # noqa: E402  (your file, untouched)
    TestScenario,
    load_system,
    _resolve_layout_dir,
    _apply_signal_corrections,
    _apply_neighbor_corrections,
)
from entity import (  # noqa: E402  (your file, untouched)
    Direction, ElementMode, ElementOcc, Linear, Point, RouteMode,
    Signal, SignalAspect,
)

# Where the static UI lives (so 'serve' can hand it out). Override with --web.
_DEFAULT_WEB_DIR = os.path.join(_REPO_DIR, "web")

# ---------------------------------------------------------------------------
# Contract code maps (see the frontend's steps-source.jsx for the schema)
# ---------------------------------------------------------------------------
_OCC = {
    ElementOcc.FREE: "F",
    ElementOcc.HEADOCC: "H",
    ElementOcc.COMPLETETRAINOCC: "C",
    ElementOcc.TAILOCC: "T",
    ElementOcc.ERROROCC: "E",
}
_SEG_MODE = {
    ElementMode.AVAILABLE: "A",
    ElementMode.EXLOCKED: "X",
    ElementMode.USED: "U",
}
_ROUTE_MODE = {
    RouteMode.FREE: "FREE",
    RouteMode.MARKED: "MARKED",
    RouteMode.ALLOCATING: "ALLOCATING",
    RouteMode.LOCKED: "LOCKED",
    RouteMode.OCCUPIED: "OCCUPIED",
}
_TRANSITION = {
    RouteMode.FREE: "\u2014",
    RouteMode.MARKED: "CAN_ALLOCATE",
    RouteMode.ALLOCATING: "CAN_LOCK",
    RouteMode.LOCKED: "CAN_OCCUPY",
    RouteMode.OCCUPIED: "\u2014",
}
_PRESENT = (ElementOcc.HEADOCC, ElementOcc.COMPLETETRAINOCC, ElementOcc.TAILOCC)


# ===========================================================================
# 1. Discover the verified scenarios already defined in your test_*.py files
# ===========================================================================
def discover_scenarios() -> list[TestScenario]:
    """Import every tests/test_*.py and collect its module-level TestScenarios.

    Importing is side-effect-free: the tests only run under `if __name__ ==
    '__main__'`, so importing just builds the scenario objects we want.
    """
    scenarios: list[TestScenario] = []
    for mod in pkgutil.iter_modules([_THIS_DIR]):
        if not mod.name.startswith("test_"):
            continue
        try:
            module = importlib.import_module(mod.name)
        except Exception as exc:  # noqa: BLE001
            print(f"[sim_bridge] skipped {mod.name}: {exc}", file=sys.stderr)
            continue
        for value in vars(module).values():
            if isinstance(value, TestScenario):
                scenarios.append(value)
    return scenarios


def match_scenario(scenarios, layout, r1, r2) -> TestScenario | None:
    want = {r for r in (r1, r2) if r}
    for s in scenarios:
        if s.layout == layout and set(s.routes) == want:
            return s
    return None


# ===========================================================================
# 2. Read engine state into the contract
# ===========================================================================
def _occ_letter(elem, direction: str) -> str:
    if isinstance(elem, Point):
        for occ in (elem.occSNR, elem.occNS, elem.occRS):
            if occ != ElementOcc.FREE:
                return _OCC.get(occ, "F")
        return "F"
    occ = elem.occUp if direction == "UP" else elem.occDown
    return _OCC.get(occ, "F")


def _is_present(elem, direction: str) -> bool:
    if isinstance(elem, Point):
        return any(o in _PRESENT for o in (elem.occSNR, elem.occNS, elem.occRS))
    occ = elem.occUp if direction == "UP" else elem.occDown
    return occ in _PRESENT


def _sig_name(sig):
    if isinstance(sig, Signal):
        return sig.name
    return sig if isinstance(sig, str) else None


class _RouteView:
    """Resolved, reusable metadata for one active route."""

    def __init__(self, route, scenario, sec_map, pt_map):
        self.route = route
        self.direction = "UP" if route.entry_dir == Direction.UP else "DOWN"
        self.entry_sig = _sig_name(route.entry_signal)
        self.exit_sig = _sig_name(route.exit_signal)

        # The approach is the train-start segment (from the scenario) that sits
        # in this route's direction and is adjacent to the first path element.
        self.approach = self._find_approach(scenario, route, sec_map)

        engine_path = [e.name for e in route.path]
        self.path_names = ([self.approach] if self.approach else []) + engine_path
        self.terminal = engine_path[-1] if engine_path else self.approach

    def _find_approach(self, scenario, route, sec_map):
        want_face = "occUp" if self.direction == "UP" else "occDown"
        candidates = [seg for seg, faces in scenario.trains.items()
                      if want_face in faces]
        if len(candidates) <= 1:
            return candidates[0] if candidates else None
        first = route.path[0] if route.path else None
        for seg in candidates:
            el = sec_map.get(seg)
            if el is not None and (el.up_neighbor is first or el.down_neighbor is first):
                return seg
        return candidates[0]


def _route_snapshot(view, sec_map, pt_map, sig_map) -> dict:
    path, head_idx = [], 0
    for i, name in enumerate(view.path_names):
        elem = sec_map.get(name) or pt_map.get(name)
        if elem is None:
            continue
        is_approach = (i == 0 and name == view.approach)
        mode = "A" if is_approach else _SEG_MODE.get(elem.MODE, "A")
        path.append([name, _occ_letter(elem, view.direction), mode])
        if _is_present(elem, view.direction):
            head_idx = max(head_idx, len(path) - 1)

    completion = round(head_idx / max(1, len(path) - 1) * 100)

    signals = []
    for sname in (view.entry_sig, view.exit_sig):
        if not sname:
            continue
        sig = sig_map.get(sname)
        state = "GO" if (sig and sig.ACT == SignalAspect.GO) else "STOP"
        signals.append([sname, state])

    mode = view.route.MODE
    return {
        "transition": _TRANSITION.get(mode, "\u2014"),
        "mode": _ROUTE_MODE.get(mode, "FREE"),
        "completion": int(completion),
        "path": path or [[view.approach or view.route.name, "F", "A"]],
        "signals": signals,
    }


def _note(views, sig_map) -> str:
    parts = []
    for v in views:
        line = f"{v.route.name} {_ROUTE_MODE.get(v.route.MODE, 'FREE')}"
        sig = sig_map.get(v.entry_sig) if v.entry_sig else None
        if sig and sig.ACT == SignalAspect.GO:
            line += f" \u00b7 {v.entry_sig}=GO"
        parts.append(line)
    return "  \u2502  ".join(parts)


# ===========================================================================
# 3. Run a scenario through the real engine, snapshotting every step
# ===========================================================================
def run_scenario_steps(scenario: TestScenario,
                       order: list[str] | None = None) -> list[dict]:
    """Replay a TestScenario through InterlockingSystem and return contract steps.

    `order` optionally fixes the route-key order (so the file/route the UI asked
    for as train #1 stays train #1); defaults to scenario.routes order.
    """
    layout_dir = _resolve_layout_dir(scenario.layout)
    system = load_system(layout_dir)  # your loader
    if scenario.neighbor_corrections:
        _apply_neighbor_corrections(system, scenario.neighbor_corrections)
    if scenario.signal_corrections:
        _apply_signal_corrections(system, scenario.signal_corrections)

    sec_map = {s.name: s for s in system.sections if isinstance(s, Linear)}
    pt_map = {p.name: p for p in system.points}
    sig_map = {s.name: s for s in system.signals}
    route_map = {r.name: r for r in system.routes}

    # Initial occupancy + marked routes — exactly as runner.run_scenario does.
    for seg_name, faces in scenario.trains.items():
        elem = sec_map.get(seg_name) or pt_map.get(seg_name)
        for face, occ in faces.items():
            setattr(elem, face, occ)
    for rname in scenario.routes:
        route_map[rname].MODE = RouteMode.MARKED

    route_order = order or list(scenario.routes)
    views = [_RouteView(route_map[r], scenario, sec_map, pt_map)
             for r in route_order]

    def frame(idx: int) -> dict:
        step = {"label": f"t={idx}", "note": _note(views, sig_map)}
        for v in views:
            step[v.route.name] = _route_snapshot(v, sec_map, pt_map, sig_map)
        return step

    def goals_met() -> bool:
        for g in scenario.goals:
            elem = sec_map.get(g.segment) or pt_map.get(g.segment)
            if elem is None or getattr(elem, g.face, ElementOcc.FREE) != g.state:
                return False
        return bool(scenario.goals)

    steps = [frame(0)]
    for i in range(1, scenario.max_steps + 1):
        with redirect_stdout(io.StringIO()):
            changed = system.step()
        steps.append(frame(i))
        if goals_met() or not changed:
            break
    return steps


def simulate(scenarios, layout, r1, r2):
    """Return contract steps for (layout, r1, r2), or None if unsupported."""
    scenario = match_scenario(scenarios, layout, r1, r2)
    if scenario is None:
        return None
    return run_scenario_steps(scenario, order=[x for x in (r1, r2) if x])


# ===========================================================================
# 4a. Offline bake — write static files the UI fetches with no server running
# ===========================================================================
def cmd_export(args):
    scenarios = discover_scenarios()
    out_dir = os.path.join(args.web, "steps")
    os.makedirs(out_dir, exist_ok=True)
    written = 0
    for s in scenarios:
        routes = list(s.routes)
        # Write every selection order the UI might request, same content.
        orders = [routes] if len(routes) == 1 else [routes, list(reversed(routes))]
        for order in orders:
            key = "__".join([s.layout] + order)
            steps = run_scenario_steps(s, order=order)
            with open(os.path.join(out_dir, f"{key}.json"), "w") as f:
                json.dump(steps, f, indent=2)
            written += 1
            print(f"  wrote steps/{key}.json  ({len(steps)} steps)")
    print(f"[sim_bridge] baked {written} file(s) into {out_dir}")
    print("Open the UI and set Tweaks \u2192 data source \u2192 json.")


# ===========================================================================
# 4b. Live server — one stdlib http.server for BOTH the API and the static UI
# ===========================================================================
def cmd_serve(args):
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    scenarios = discover_scenarios()
    web_dir = args.web
    print(f"[sim_bridge] {len(scenarios)} scenario(s) discovered; "
          f"serving UI from {web_dir}")

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=web_dir, **k)

        def log_message(self, *a):  # keep the console quiet
            pass

        def _send_json(self, status, payload):
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path.rstrip("/") in ("/simulate", "/api/simulate"):
                q = parse_qs(parsed.query)
                layout = (q.get("layout") or [None])[0]
                r1 = (q.get("r1") or [None])[0]
                r2 = (q.get("r2") or [None])[0]
                if not layout or not r1:
                    return self._send_json(400, {"error": "need layout & r1"})
                try:
                    steps = simulate(scenarios, layout, r1, r2)
                except Exception as exc:  # noqa: BLE001
                    return self._send_json(500, {"error": str(exc)})
                if steps is None:
                    # Unsupported combo → 404 makes the UI fall back to synth.
                    return self._send_json(
                        404, {"error": f"no verified scenario for "
                                       f"{layout} {r1}{'+' + r2 if r2 else ''}"})
                return self._send_json(200, {"steps": steps})
            return super().do_GET()  # otherwise serve a static file

    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}"
    print(f"[sim_bridge] open {url}  (API at {url}/simulate?layout=..&r1=..&r2=..)")
    print("[sim_bridge] in the UI set Tweaks \u2192 data source \u2192 api  ·  Ctrl-C to stop")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[sim_bridge] bye")


# ===========================================================================
# CLI
# ===========================================================================
def main():
    p = argparse.ArgumentParser(description="SWTbahn sim frontend bridge")
    p.add_argument("--web", default=_DEFAULT_WEB_DIR,
                   help="static UI directory (default: <repo>/web)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("serve", help="serve UI + live /simulate API")
    sp.add_argument("--host", default="localhost")
    sp.add_argument("--port", type=int, default=8000)
    sp.set_defaults(func=cmd_serve)

    se = sub.add_parser("export", help="bake static web/steps/*.json")
    se.set_defaults(func=cmd_export)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
