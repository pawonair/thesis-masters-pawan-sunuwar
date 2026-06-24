# 🖥️ SWT-Lite Bahn Interface

## Sectional Interlocking System Simulation

**In-browser React Application with Standalone Bable** for simulating SWT-Lite Bahn sectional interlocking system.

The `tests/runner.py` already loads layouts, applies corrections, seeds occupancy, and steps the system, and each
`test_*.py` already encodes a verified scenario as a `TestScenario`. The bridge just **replays those through the engine
and snapshots each step** into the JSON the UI reads.

---

## Structure

```
bahn-smv/
|-- tests/
|   |-- sim_bridge.py
|-- web/
    |-- index.html
    |-- app.jsx
    |-- tweaks-panel.jsx
    |-- layouts-data.jsx
    |-- progression.jsx
    |-- steps-source.jsx
```

> `web/` is static: React + Babel load from a CDN, so there is **no build step, no npm, no bundler**. (An internet
> connection is needed for those CDN scripts; everything else is local.)

---

## Run

### Option A: Live Server (recommended)

One stdlib server hands out the UI **and** answers the API on the same port, so there's no CORS and nothing else to
start:

```bash
python tests/sim_bridge.py serve          # http://localhost:8000
```

Open `http://localhost:8000`, then in the UI: **Tweaks -> data source -> `api`**. Pick a layout and route(s); the
timeline you scrub is the real engine running.

### Option B: Offline Bake (no server)

Pre-compute the step files once; the UI then just fetches static JSON:

```bash
python tests/sim_bridge.py export         # writes web/steps/*.json
cd web && python -m http.server 8000      # or open index.html directly
```

In the UI: **Tweaks -> data source -> `json`**.

---

## Process

- A selection whose **{layout, routes}** matches a `TestScenario` (e.g. `2_Point` with r0 + r2) reproduces that verified
  run **step-for-step**: same corrections, same train positions, same outcome.
- A selection that matches **no** scenario returns `404` (live) / no file (offline). The frontend then transparently
  uses its built-in in-browser synthesizer, so the UI never breaks and never shows a *fabricated* engine timeline. The
  footnote / Tweaks status shows which source actually answered.

### Support more route pairs

Add another `TestScenario` in a `tests/test_*.py` (trains, routes, goals, corrections). `sim_bridge.py` discovers it
automatically on the next run. The tests stay the single source of truth for every simulatable scenario.

---

## Operation

```
sim_bridge.py
  |-- discover_scenarios()    # imports tests/test_*.py, collects TestScenario objects
  |-- run_scenario_steps()    # reuses runner.load_system + the correction helpers,
  |                             marks routes, steps InterlockingSystem, and after
  |                             every step records each route's path occupancy /
  |                             element mode / signal aspect
  |-- serve  (subcommand)     # http.server: GET /simulate?layout&r1&r2  + static UI
  |-- export (subcommand)     # writes web/steps/<layout>__<r1>__<r2>.json
```

The JSON shape (one entry per timeline step) is documented at the top of `web/steps-source.jsx` which is the contract
both sides agree on.

```
{ "label": "t=3", "note": "...",
  "r0": { "mode": "LOCKED", "completion": 60,
          "path": [["seg3","C","U"], ["point1","F","X"], ...],
          "signals": [["signal2","GO"], ["signal4","STOP"]] } }
```
