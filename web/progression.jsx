/* global LAYOUT_DATA */
// progression.jsx – synthesizes a step-by-step progression for the selected
// route pair, using the layout-data parsed from the .bahn / .yml configs.
//
// SECTIONAL INTERLOCKING (element-wise release)
// --------------------------------------------------------------------------
// As the train head advances along its path, each path element passes through
// three mode states in order:
//
//     EXLOCKED  (ahead of head, locked for this route)
//     USED      (head is here, OR head just left it – element used)
//     AVAILABLE (head has moved further on; element released, can be re-locked)
//
// Occupancy is independent:
//     HEAD      = current segment under the train head
//     FREE      = no train present (either ahead, or already released)
//
// The critical sectional-release transition is when the head moves OFF an
// element: that element becomes mode=USED, occ=FREE – at this exact moment
// any conflicting route that needs this element can begin its transition,
// because no train is physically on it and the interlocking can re-allocate
// it (USED → AVAILABLE → EXLOCKED for the new route).
//
// In our snapshot for each route phase p (where p >= 4 means OCCUPIED):
//     head index H = p - 3      (1 .. L-1)
//     i == H              → mode=U  occ=H   (train head)
//     i == H - 1          → mode=U  occ=F   (just released – sectional gap)
//     i <  H - 1          → mode=A  occ=F   (fully available)
//     i >  H              → mode=X  occ=F   (still exlocked, ahead)
//     i == 0 (approach)   → mode=A  always  (approach is not locked)
//
// Phases per route:
//   0  FREE       train at approach, signals STOP
//   1  MARKED     train at approach, MARKED
//   2  ALLOCATING path elements EXLOCKED, mode ALLOCATING
//   3  LOCKED     mode LOCKED, entry signal GO
//   4..(4+L-2)    OCCUPIED, head advances one path-element per step
//   last          FREE, train parked at terminal
//
// Combined timeline:
//   * non-conflicting → parallel. both timelines advance in lockstep.
//   * conflicting     → sequential AT THE CONFLICT BOUNDARY ONLY. r1 starts.
//     r2 stays FREE-waiting until r1's head has cleared the *last common*
//     path element. At that step the common element is USED+FREE, r2's phase
//     0 begins, and from then on both routes advance together until parked.

function _occMap(route, phase) {
    // For the given phase index, compute occ + mode per path element.
    // path[0] is the approach segment, path[1..end] are locked elements
    // (point + block segments).
    const L = route.path.length;
    const headPhaseStart = 4;
    const lastPhase = headPhaseStart + (L - 1) - 1; // train at terminal (parked)
    const result = [];

    // Head index in path for OCCUPIED phases (-1 = not entered, -2 sentinel)
    let head = -1;

    if (phase >= headPhaseStart && phase <= lastPhase) {
        head = phase - headPhaseStart + 1;
    } else if (phase > lastPhase) {
        head = L - 1;
    }

    for (let i = 0; i < L; i++) {
        const seg = route.path[i];
        let occ = "F", mode = "A";

        // -------- Pre-OCCUPIED phases (0..3) --------
        if (phase < headPhaseStart) {
            // mode: approach stays A; rest of path is EXLOCKED once ALLOCATING (p>=2)
            if (i === 0) mode = "A";
            else if (phase >= 2) mode = "X";
            else mode = "A";
            // occupancy: train sits on approach
            occ = i === 0 ? "C" : "F";
        } else if (phase <= lastPhase) {
            // -------- OCCUPIED phases (4..lastPhase) --------
            if (i === 0) {
                // approach: emptied as soon as train left it (phase 4 onward)
                mode = "A";
                occ = "F";
            } else if (i > head) {
                mode = "X";   // still EXLOCKED ahead
                occ = "F";
            } else if (i === head) {
                mode = "U";   // train head currently here
                occ = "H";
            } else if (i === head - 1) {
                mode = "U";   // just released – USED state, FREE occupancy
                occ = "F";   // ← the sectional-release moment
            } else {
                mode = "A";   // fully released, AVAILABLE again
                occ = "F";
            }
        } else {
            // -------- Parked phase (> lastPhase) --------
            if (i === L - 1) {
                mode = "U";
                occ = "C";
            }   // terminal: train parked
            else {
                mode = "A";
                occ = "F";
            }   // rest released
        }

        result.push([seg, occ, mode]);
    }

    return result;
}

function _routeSnapshot(route, phase) {
    const L = route.path.length;
    const lastPhase = 4 + (L - 1) - 1;

    let mode, transition;

    if (phase < 0) {
        mode = "FREE";
        transition = "\u2014";
    } else if (phase === 0) {
        mode = "FREE";
        transition = "CAN_DISPATCH";
    } else if (phase === 1) {
        mode = "MARKED";
        transition = "CAN_ALLOCATE";
    } else if (phase === 2) {
        mode = "ALLOCATING";
        transition = "CAN_LOCK";
    } else if (phase === 3) {
        mode = "LOCKED";
        transition = "CAN_OCCUPY";
    } else if (phase <= lastPhase) {
        mode = "OCCUPIED";
        transition = "\u2014";
    } else {
        mode = "FREE";
        transition = "\u2014";
    }

    // Signals: entry GO from LOCKED through OCCUPIED-middle; STOP otherwise.
    const [sigEntry, sigExit] = route.signals;
    let entryState = "STOP", exitState = "STOP";

    if (phase >= 3 && phase <= lastPhase - 1) entryState = "GO";

    const completion = phase < 0
        ? 0
        : phase < 4
            ? 0
            : phase > lastPhase
                ? 100
                : Math.round(((phase - 3) / (lastPhase - 3 + 1)) * 100);

    return {
        transition, mode, completion,
        path: _occMap(route, phase),
        signals: [[sigEntry, entryState], [sigExit, exitState]],
    };
}

function _waitingSnapshot(route, commonEl) {
    // train sits at approach, mode FREE, signals STOP – used while the OTHER
    // train still holds a conflicting common element.
    const path = route.path.map((seg, i) => [seg, i === 0 ? "C" : "F", "A"]);

    return {
        transition: commonEl ? `Blocked; waits on ${commonEl}` : "Blocked",
        mode: "FREE",
        completion: 0,
        path,
        signals: [[route.signals[0], "STOP"], [route.signals[1], "STOP"]],
    };
}

function _parkedSnapshot(route) {
    const L = route.path.length;
    const path = route.path.map((seg, i) => [seg, i === L - 1 ? "C" : "F", i === L - 1 ? "U" : "A"]);

    return {
        transition: "\u2014",
        mode: "FREE",
        completion: 100,
        path,
        signals: [[route.signals[0], "STOP"], [route.signals[1], "STOP"]],
    };
}

// Find the last index in r1.path that is also present in r2.path.
// This is the bottleneck for sectional release: r2 cannot acquire any of its
// common elements until r1's head has cleared the deepest one.
function _lastCommonIdx(r1, r2) {
    const r2set = new Set(r2.path);

    for (let i = r1.path.length - 1; i >= 0; i--) {
        if (r2set.has(r1.path[i])) return i;
    }

    return -1;
}

// Collect every shared path element (for note text).
function _commonElements(r1, r2) {
    const r2set = new Set(r2.path);
    return r1.path.filter(e => r2set.has(e));
}

function generateSteps(layout, r1id, r2id) {
    const r1 = layout.routes[r1id];
    const r2 = r2id ? layout.routes[r2id] : null;
    const conflict = r2 ? r1.conflicts.includes(r2id) : false;

    const L1 = r1.path.length;
    const T1 = 4 + (L1 - 1) + 1;   // phases 0..lastPhase+1

    const steps = [];

    if (!r2) {
        for (let p = 0; p < T1; p++) {
            steps.push({
                label: `t=${p}`,
                note: _soloNote(r1, p),
                [r1id]: _routeSnapshot(r1, p),
            });
        }

        return steps;
    }

    const L2 = r2.path.length;
    const T2 = 4 + (L2 - 1) + 1;

    if (!conflict) {
        // Parallel – both progress in lockstep, run until both parked.
        const T = Math.max(T1, T2);

        for (let p = 0; p < T; p++) {
            const snap = {};

            snap[r1id] = p < T1 ? _routeSnapshot(r1, p) : _parkedSnapshot(r1);
            snap[r2id] = p < T2 ? _routeSnapshot(r2, p) : _parkedSnapshot(r2);

            steps.push({
                label: `t=${p}`,
                note: _parallelNote(r1, r2, p),
                ...snap,
            });
        }

        return steps;
    }

    // ----------------------------------------------------------------------
    // CONFLICTING ROUTES – element-wise sectional release.
    //
    // Find the LAST common element in r1's path. r2 is held in waiting until
    // r1's head moves OFF that element – at that step the element is
    // mode=USED, occ=FREE, and r2 starts phase 0 (CAN_DISPATCH).
    //
    // r1 phase p → head index H = p - 3 (for p >= 4).
    // Common element at r1.path[K] is USED+FREE when H = K + 1, i.e. p = K + 4.
    // So r2's phase 0 begins at timeline step (K + 4).
    // ----------------------------------------------------------------------
    const lastCommonIdx = _lastCommonIdx(r1, r2);
    const commonEls = _commonElements(r1, r2);
    const commonEl = lastCommonIdx >= 0 ? r1.path[lastCommonIdx] : null;

    // If somehow conflict is declared but no shared path element exists, fall
    // back to fully-sequential so we don't deadlock the visualisation.
    const r2StartStep = lastCommonIdx >= 0 ? (4 + lastCommonIdx) : T1;
    const total = Math.max(T1, r2StartStep + T2);

    for (let t = 0; t < total; t++) {
        const r1p = t;
        const r2p = t - r2StartStep;
        const snap = {};

        snap[r1id] = r1p < T1 ? _routeSnapshot(r1, r1p) : _parkedSnapshot(r1);

        if (r2p < 0) {
            snap[r2id] = _waitingSnapshot(r2, commonEl);
        } else if (r2p < T2) {
            snap[r2id] = _routeSnapshot(r2, r2p);
        } else {
            snap[r2id] = _parkedSnapshot(r2);
        }

        steps.push({
            label: `t=${t}`,
            note: _sectionalNote(r1, r2, r1p, r2p, lastCommonIdx, commonEl, commonEls, r2StartStep),
            ...snap,
        });
    }

    return steps;
}

// ---------------------------------------------------------------------------
// Note generators
// ---------------------------------------------------------------------------

function _soloNote(r, p) {
    const L = r.path.length;
    const lastPhase = 4 + (L - 1) - 1;

    if (p === 0) return `Train at ${r.approach}. CAN_DISPATCH.`;
    if (p === 1) return `MARKED – interlocking acknowledges route ${r.id}.`;
    if (p === 2) return `ALLOCATING – exlocking ${r.path.slice(1).join(", ")}.`;
    if (p === 3) return `LOCKED. ${r.signals[0]} = GO.`;
    if (p <= lastPhase) {
        const h = p - 3;
        const at = r.path[h];
        const released = r.path.slice(1, Math.max(1, h - 1)).join(", ") || "\u2014";

        return `OCCUPIED – head at ${at} (step ${h}/${L - 1}). Released: ${released}.`;
    }

    return `Parked at ${r.terminal}.`;
}

function _parallelNote(r1, r2, p) {
    const L = Math.max(r1.path.length, r2.path.length);
    const lastPhase = 4 + (L - 1) - 1;

    if (p === 0) return `Both trains at approach. routes do not conflict – running in parallel.`;
    if (p === 1) return `Both MARKED.`;
    if (p === 2) return `Both ALLOCATING – disjoint path elements EXLOCKED.`;
    if (p === 3) return `Both LOCKED. entry signals GO.`;
    if (p <= lastPhase) return `Both OCCUPIED – independent traversal (head step ${p - 3}).`;

    return `Both trains parked.`;
}

function _sectionalNote(r1, r2, r1p, r2p, kIdx, commonEl, commonEls, r2StartStep) {
    const L1 = r1.path.length;
    const lastP1 = 4 + (L1 - 1) - 1;
    const commonList = commonEls.length > 1
        ? `Common: {${commonEls.join(", ")}}, deepest = ${commonEl}`
        : `Common element: ${commonEl}`;

    // Phase 0..3: r1 setting up, r2 still blocked
    if (r2p < 0) {
        if (r1p === 0) return `${r1.id}: CAN_DISPATCH. ${r2.id} blocked – ${commonList}.`;
        if (r1p === 1) return `${r1.id}: MARKED. ${r2.id} still blocked on ${commonEl}.`;
        if (r1p === 2) return `${r1.id}: ALLOCATING – exlocks ${r1.path.slice(1).join(", ")} (incl. ${commonEl}).`;
        if (r1p === 3) return `${r1.id}: LOCKED. ${r1.signals[0]} = GO. ${r2.id} still blocked.`;

        // r1 OCCUPIED, approaching the common element
        const h = r1p - 3;
        const at = r1.path[h];

        if (h < kIdx) return `${r1.id}: OCCUPIED – head at ${at}, advancing toward ${commonEl}.`;
        if (h === kIdx) return `${r1.id}: head on ${commonEl} (mode=USED, occ=HEAD). ${r2.id} still blocked.`;

        return `${r1.id}: OCCUPIED – head at ${at}.`;
    }

    // The unlock step – r2p === 0
    if (r2p === 0) {
        return `Sectional release: ${commonEl} now mode=USED; occ=FREE. ${r2.id} CAN_DISPATCH while ${r1.id} keeps traversing.`;
    }

    // r2 is running concurrently with r1
    const r1HeadAt = r1p <= lastP1 ? r1.path[Math.max(1, r1p - 3)] : `parked@${r1.terminal}`;

    if (r2p === 1) return `${r2.id}: MARKED. ${r1.id} still traversing (head at ${r1HeadAt}).`;
    if (r2p === 2) return `${r2.id}: ALLOCATING – re-exlocks ${commonEl} (now AVAILABLE) + ${r2.path.slice(1).filter(e => !commonEls.includes(e)).join(", ") || "\u2014"}.`;
    if (r2p === 3) return `${r2.id}: LOCKED. ${r2.signals[0]} = GO. both routes locked, traversing concurrently.`;

    const L2 = r2.path.length;
    const lastP2 = 4 + (L2 - 1) - 1;

    if (r2p <= lastP2) {
        const h2 = r2p - 3;
        return `Concurrent – ${r1.id} head ${r1HeadAt}; ${r2.id} head ${r2.path[h2]} (step ${h2}/${L2 - 1}).`;
    }

    if (r1p < L1 + 4 - 1) return `${r2.id} parked. ${r1.id} still traversing (head at ${r1HeadAt}).`;

    return `Both trains parked.`;
}

window.generateSteps = generateSteps;
