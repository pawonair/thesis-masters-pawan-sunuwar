/* global generateSteps */
// steps-source.jsx
// ---------------------------------------------------------------------------
// Pluggable step source. The UI no longer calls generateSteps() directly – it
// asks loadSteps(...) for the progression, and THIS file decides where the
// steps come from:
//
//   "synth"  – the in-browser narrative synthesizer (progression.jsx).
//              Zero backend. This is the original behaviour / safety net.
//
//   "json"   – a static file your Python app pre-baked (Option 1, "offline
//              solve"). Looks for  steps/<layout>__<r1>__<r2>.json  (and
//              steps/<layout>__<r1>.json for a single train). Generate these
//              with python/export_steps.py.
//
//   "api"    – a live HTTP endpoint your Python app serves (Option 2). Calls
//              GET <API_BASE>/simulate?layout=..&r1=..&r2=..  and expects the
//              same step array back. Run python/server.py (FastAPI).
//
// EVERY source resolves to the SAME shape – the contract below – so the rest
// of the UI is identical no matter who computed the steps. If a remote source
// errors, we fall back to "synth" and report it via the status callback so the
// wireframe never ends up blank.
//
// ---------------------------------------------------------------------------
// THE CONTRACT  (one entry per timeline step)
// ---------------------------------------------------------------------------
//   [
//     {
//       "label": "t=3",                      // scrubber caption
//       "note":  "r0 LOCKED. signal2 = GO.", // human-readable line under it
//       "<routeId>": {                       // one key per ACTIVE route, e.g. "r0"
//         "transition": "CAN_OCCUPY",        // free text / state-machine edge
//         "mode": "LOCKED",                  // FREE|MARKED|ALLOCATING|LOCKED|OCCUPIED
//         "completion": 60,                  // integer 0..100
//         "path": [                          // ordered path elements
//           ["seg3",  "F", "A"],             // [ id, occCode, modeCode ]
//           ["point1","F", "X"],
//           ["seg5",  "H", "U"]
//         ],
//         "signals": [                       // signal states for this route
//           ["signal2", "GO"],               // [ id, "GO"|"STOP"|... ]
//           ["signal4", "STOP"]
//         ]
//       }
//       // ...more route keys if two trains are active
//     }
//     // ...more steps
//   ]
//
// occCode  : F free · H head · C train · T tail · E error   (see OCC_FILL in app.jsx)
// modeCode : A available · X exlocked · U used               (see chipBorder in app.jsx)
//
// A response may be either the bare array above, or wrapped as { "steps": [...] }
// (plus any extra metadata you like) – normalizeSteps() accepts both.
// ---------------------------------------------------------------------------

// Where the live API lives. Override at runtime from the console if needed:
//   window.SWT_API_BASE = "http://localhost:8000"
window.SWT_API_BASE = window.SWT_API_BASE || "http://localhost:8000";

// Folder holding pre-baked static step files (Option 1).
window.SWT_STEPS_DIR = window.SWT_STEPS_DIR || "steps";

function _key(layout, r1, r2) {
    return r2 ? `${layout}__${r1}__${r2}` : `${layout}__${r1}`;
}

// Accept either a bare array or { steps: [...] }.
function normalizeSteps(payload) {
    const arr = Array.isArray(payload)
        ? payload
        : (payload && Array.isArray(payload.steps))
            ? payload.steps
            : null;

    if (!arr) throw new Error("Response is not a step array or { steps: [...] }");

    return arr;
}

// Lightweight shape check so a malformed backend reply fails loudly (and we
// fall back) instead of rendering garbage.
function validateSteps(steps, r1, r2) {
    if (!steps.length) throw new Error("empty step array");

    const first = steps[0];
    const wantKeys = [r1, r2].filter(Boolean);

    for (const k of wantKeys) {
        if (!(k in first)) throw new Error(`step is missing route key "${k}"`);

        const snap = first[k];

        if (!snap || !Array.isArray(snap.path) || !Array.isArray(snap.signals)) {
            throw new Error(`route "${k}" snapshot missing path/signals`);
        }
    }

    return steps;
}

function _synth(layout, r1, r2) {
    // layout here is the LAYOUT_DATA object (same as generateSteps expects).
    return generateSteps(layout, r1, r2 || null);
}

async function _json(layoutId, r1, r2) {
    const url = `${window.SWT_STEPS_DIR}/${_key(layoutId, r1, r2)}.json`;
    const res = await fetch(url, {cache: "no-store"});

    if (!res.ok) throw new Error(`${url} -> HTTP ${res.status}`);

    return validateSteps(normalizeSteps(await res.json()), r1, r2);
}

async function _api(layoutId, r1, r2) {
    const qs = new URLSearchParams({layout: layoutId, r1});

    if (r2) qs.set("r2", r2);

    const url = `${window.SWT_API_BASE}/simulate?${qs}`;
    const res = await fetch(url, {headers: {Accept: "application/json"}});

    if (!res.ok) throw new Error(`${url} -> HTTP ${res.status}`);

    return validateSteps(normalizeSteps(await res.json()), r1, r2);
}

// Main entry point used by app.jsx.
//   source : "synth" | "json" | "api"
//   layout : LAYOUT_DATA[layoutId]   (object)
//   layoutId, r1, r2 : ids (strings)
//   onStatus(state)  : optional – { phase, source, usedFallback, error }
//
// Always resolves to a valid step array (falls back to synth on remote error).
async function loadSteps({source, layout, layoutId, r1, r2, onStatus}) {
    const report = (s) => {
        try {
            onStatus && onStatus(s);
        } catch (_) {
        }
    };

    if (source === "synth" || !source) {
        report({phase: "ready", source: "synth", usedFallback: false});
        return _synth(layout, r1, r2);
    }

    report({phase: "loading", source});

    try {
        const steps = source === "json"
            ? await _json(layoutId, r1, r2)
            : source === "api"
                ? await _api(layoutId, r1, r2)
                : _synth(layout, r1, r2);

        report({phase: "ready", source, usedFallback: false});

        return steps;
    } catch (err) {
        // Network down, file missing, malformed reply -> degrade gracefully.
        report({
            phase: "ready", source: "synth", usedFallback: true,
            error: String(err && err.message || err)
        });

        return _synth(layout, r1, r2);
    }
}

window.loadSteps = loadSteps;
window.normalizeSteps = normalizeSteps;
window.validateSteps = validateSteps;
