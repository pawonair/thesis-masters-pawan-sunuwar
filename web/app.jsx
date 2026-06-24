/* global React, ReactDOM, TweaksPanel, useTweaks, TweakSection, TweakRadio, TweakToggle, TweakSlider,
          LAYOUT_DATA, generateSteps, loadSteps */

const {useState, useMemo, useEffect} = React;

// Occupancy fill (kept muted; not full saturation).
const OCC_FILL = {
    F: "transparent",          // FREE
    H: "#f6c177",              // HEADOCC
    C: "#e26d5c",              // COMPLETETRAINOCC
    T: "#cdb4db",              // TAILOCC
    E: "#ff2e63",              // ERROROCC
};

const OCC_LABEL = {
    F: "free", H: "head", C: "train", T: "tail", E: "ERR",
};

const MODE_LABEL = {A: "available", X: "exlocked", U: "used"};

// Border style per mode.
function chipBorder(modeCode) {
    if (modeCode === "U") return "3px solid #1a1a1a";
    if (modeCode === "X") return "2px solid #1a1a1a";
    return "1px dashed #888";
}

function SegmentChip({id, occ, mode, dense}) {
    const fill = OCC_FILL[occ] || "transparent";
    const isPoint = id.startsWith("point");

    return (
        <div className="seg-chip" title={`${id}\nocc=${OCC_LABEL[occ]} · mode=${MODE_LABEL[mode]}`}
             style={{
                 border: chipBorder(mode),
                 background: fill,
                 padding: dense ? "2px 8px" : "4px 10px",
                 borderRadius: isPoint ? "999px" : "6px",
                 fontSize: dense ? 11 : 12,
                 transform: `rotate(${(id.charCodeAt(id.length - 1) % 3 - 1) * 0.4}deg)`,
             }}>
            {isPoint && <span style={{fontSize: 10}}>♢</span>}
            <span>{id}</span>
        </div>
    );
}

function Arrow() {
    return <span style={{color: "#888", margin: "0 -2px"}}>→</span>;
}

function SignalDot({id, state}) {
    const color = state === "GO" ? "#3ea66a" : state === "STOP" ? "#d24a3d" : "#bbb";
    const ring = state === "GO" ? "#235e3b" : state === "STOP" ? "#7a2820" : "#888";

    return (
        <div className="sig" title={`${id} = ${state}`}>
            <span style={{
                background: color, border: `1.5px solid ${ring}`,
                boxShadow: state === "GO" ? "0 0 4px #3ea66a55" : "none",
            }}/>
            <span>{id}</span>
        </div>
    );
}

function ProgressBar({pct}) {
    return (
        <div className="progress-bar">
            <div className="sketch-box">
                <div className="sketch-trans" style={{width: `${pct}%`}}/>
            </div>

            <span>{pct}%</span>
        </div>
    );
}

function ModeBadge({mode}) {
    const colors = {
        FREE: {background: "transparent", color: "#666", border: "1px dashed #888"},
        MARKED: {background: "#fff4d6", color: "#7a5a00", border: "1.5px solid #7a5a00"},
        ALLOCATING: {background: "#e0f0ff", color: "#2358a3", border: "1.5px solid #2358a3"},
        LOCKED: {background: "#dfeede", color: "#235e3b", border: "1.5px solid #235e3b"},
        OCCUPIED: {background: "#1a1a1a", color: "#fbf8f1", border: "1.5px solid #1a1a1a"},
    };
    const c = colors[mode] || colors.FREE;

    return (
        <span className="mode-badge" style={{...c}}>{mode}</span>
    );
}

function TransitionPill({label}) {
    const muted = label === "\u2014" || label.startsWith("Blocked");

    return (
        <span className="transition-pill" style={{
            color: muted ? "#999" : "#1a1a1a",
            border: muted ? "none" : "1.5px dashed #1a1a1a",
            padding: muted ? "0" : "2px 8px",
        }}>{label}</span>
    );
}

// ---------------------------------------------------------------------------
// Source badge – shows where the steps came from + fallback warnings.
// ---------------------------------------------------------------------------
function SourceBadge({status, requested}) {
    if (!status) return null;
    const loading = status.phase === "loading";
    const fallBack = status.usedFallback;
    const bg = loading ? "#e0f0ff" : fallBack ? "#fbe4dc" : "#dfeede";
    const fg = loading ? "#2358a3" : fallBack ? "#7a2820" : "#235e3b";
    const border = loading ? "#2358a3" : fallBack ? "#d24a3d" : "#3ea66a";
    const dot = loading ? "⌛︎" : fallBack ? "⚠" : "●";
    const text = loading
        ? `loading · ${requested}`
        : fallBack
            ? `${requested} unreachable → synth`
            : `source · ${status.source}`;

    return (
        <span className="source-badge"
              title={fallBack && status.error ? status.error : (SOURCE_LABEL[status.source] || status.source)}
              style={{color: fg, background: bg, border: `1.5px solid ${border}`}}>
            <span>{dot}</span>{text}
        </span>
    );
}

// ---------------------------------------------------------------------------
// Legend
// ---------------------------------------------------------------------------
function Legend() {
    const borders = {
        A: {border: "1px dashed #888"},
        X: {border: "2px solid #1a1a1a"},
        U: {border: "3px solid #1a1a1a"},
    };
    const sigColors = {
        GO: {background: "#3ea66a", border: "1.5px solid #235e3b"},
        STOP: {background: "#d24a3d", border: "1.5px solid #7a2820"},
    }

    return (
        <div className="legend">
            <div className="legend-title">Legend</div>

            <div className="legend-content">
                <span className="label">Occupancy:</span>

                {["F", "H", "C", "T", "E"].map(k => (
                    <span className="legend-occ" key={k}>
                        <span style={{background: OCC_FILL[k] || "transparent"}}/>
                        <span>{OCC_LABEL[k]}</span>
                    </span>
                ))}
            </div>

            <div className="legend-content">
                <span className="label">Mode (bordered):</span>

                {["A", "X", "U"].map(k => (
                    <span className="legend-mode" key={k}>
                        <span style={{...borders[k]}}/>
                        <span>{MODE_LABEL[k]}</span>
                    </span>
                ))}
            </div>

            <div className="legend-content">
                <span className="label">Signal:</span>

                {["GO", "STOP"].map(k => (
                    <span className="legend-sig" key={k}>
                        <span style={{
                            width: 10,
                            height: 10,
                            borderRadius: "50%",
                            ...sigColors[k]
                        }}/>
                        <span>{k}</span>
                    </span>
                ))}
            </div>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Route row
// ---------------------------------------------------------------------------
function RouteRow({id, dir, snapshot, dense, dim}) {
    if (!snapshot) return null;

    return (
        <tr style={{opacity: dim ? 0.45 : 1, transition: "opacity 200ms"}}>
            <td className="cell">
                <div style={{fontSize: 22, fontWeight: 700}}>{id}</div>
                <div style={{fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#888"}}>
                    {dir}
                </div>
            </td>

            <td className="cell"><TransitionPill label={snapshot.transition}/></td>

            <td className="cell"><ModeBadge mode={snapshot.mode}/></td>

            <td className="cell">
                <div style={{display: "flex", flexWrap: "wrap", alignItems: "center", gap: 6}}>
                    {snapshot.path.map(([sid, occ, mode], i) => (
                        <React.Fragment key={i}>
                            <SegmentChip id={sid} occ={occ} mode={mode} dense={dense}/>
                            {i < snapshot.path.length - 1 && <Arrow/>}
                        </React.Fragment>
                    ))}
                </div>
            </td>

            <td className="cell">
                <div style={{display: "flex", flexWrap: "wrap"}}>
                    {snapshot.signals.map(([sid, state], i) => (
                        <SignalDot key={i} id={sid} state={state}/>
                    ))}
                </div>
            </td>

            <td className="cell" style={{minWidth: 140}}>
                <ProgressBar pct={snapshot.completion}/>
            </td>
        </tr>
    );
}

// ---------------------------------------------------------------------------
// Main app
// ---------------------------------------------------------------------------
const DEFAULTS = /*EDITMODE-BEGIN*/{
    "density": "comfy",
    "showLegend": true,
    "stepSource": "synth"
}/*EDITMODE-END*/;

// Pretty labels for the active step source.
const SOURCE_LABEL = {
    synth: "in-browser synth",
    json: "static JSON (python export)",
    api: "live API (python server)",
};

function App() {
    const [tw, setTweak] = useTweaks(DEFAULTS);

    const layoutIds = Object.keys(LAYOUT_DATA);
    const [layoutId, setLayoutId] = useState("2_Point");
    const [start1, setStart1] = useState("");
    const [start2, setStart2] = useState("");
    const [simulated, setSimulated] = useState(false);
    const [step, setStep] = useState(0);

    const layout = LAYOUT_DATA[layoutId];
    const isWired = !!layout;

    // start option = route id directly. label includes approach segment + dir.
    const startOpts1 = isWired ? layout.startOptions : [];

    const route1 = start1 ? layout.routes[start1] : null;
    const destBlock1 = route1 ? new Set(route1.destBlockSegs) : new Set();
    const terminal1 = route1 ? route1.terminal : null;

    // Train#2 filter:
    //   (a) different route
    //   (b) starting segment outside #1's destination block
    //   (c) terminal segment ≠ #1's terminal
    const startOpts2 = startOpts1.filter(o => {
        if (!route1) return false;
        if (o.value === start1) return false;

        const r = layout.routes[o.value];

        if (!r) return false;
        if (destBlock1.has(r.approach)) return false;
        if (r.terminal === terminal1) return false;

        return true;
    });

    // -------------------------------------------------------------------------
    // Steps now come from a pluggable source (steps-source.jsx): the in-browser
    // synth, a static JSON file your Python app pre-baked, or a live Python API.
    // Loading is async, so steps live in state and are filled by an effect.
    // -------------------------------------------------------------------------
    const [steps, setSteps] = useState([]);
    const [srcStatus, setSrcStatus] = useState(null); // { phase, source, usedFallback, error }
    const totalSteps = steps.length;

    useEffect(() => {
        if (!simulated || !route1) {
            setSteps([]);
            setSrcStatus(null);
            return;
        }

        let cancelled = false;

        setSrcStatus({phase: "loading", source: tw.stepSource});

        loadSteps({
            source: tw.stepSource,
            layout,
            layoutId,
            r1: start1,
            r2: start2 || null,
            onStatus: (s) => {
                if (!cancelled) setSrcStatus(s);
            },
        }).then((result) => {
            if (cancelled) return;

            setSteps(result);
            setStep((prev) => Math.min(prev, Math.max(0, result.length - 1)));
        });

        return () => {
            cancelled = true;
        };
    }, [simulated, layoutId, start1, start2, tw.stepSource]);

    const snapshot = simulated && steps.length ? steps[Math.min(step, steps.length - 1)] : null;

    const activeRoutes = useMemo(() => {
        const ids = new Set();

        if (start1) ids.add(start1);
        if (start2) ids.add(start2);

        return ids;
    }, [start1, start2]);

    const simulate = () => {
        setSimulated(true);
        setStep(0);
    };

    const reset = () => {
        setSimulated(false);
        setStep(0);
    };

    const dense = tw.density === "compact";

    return (
        <div className="page">
            <header className="paper-header">
                <div>
                    <h1 className="hand-title">SWTLite-Bahn Sim</h1>
                    <p className="hand-sub">Sectional Interlocking System</p>
                </div>

                <div className="legend-slot">
                    {tw.showLegend && <Legend/>}
                </div>
            </header>

            {/* ----------------- Controls ----------------- */}
            <section className="controls sketch-card">
                <div className="ctrl">
                    <label className="hand-label">Layout</label>

                    <select className="hand-select" value={layoutId}
                            onChange={e => {
                                setLayoutId(e.target.value);
                                setStart1("");
                                setStart2("");
                                reset();
                            }}>
                        {layoutIds.map(id => (
                            <option key={id} value={id}>{id.replace("_", " - ")}</option>
                        ))}
                    </select>
                </div>

                <div className="ctrl">
                    <label className="hand-label">
                        <span className="step-num">1</span> Train #1
                    </label>

                    <select className="hand-select" value={start1}
                            onChange={e => {
                                setStart1(e.target.value);
                                setStart2("");
                                reset();
                            }}
                            disabled={!isWired}>
                        <option value="" disabled>Choose a starting segment</option>
                        {startOpts1.map(o => (
                            <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                    </select>
                </div>

                <div className="ctrl">
                    <label className="hand-label">
                        <span className="step-num">2</span> Train #2
                        {start1 && (
                            <span className="hand-hint">( Distinct terminal – outside #1's block )</span>
                        )}
                    </label>

                    <select className="hand-select" value={start2}
                            onChange={e => {
                                setStart2(e.target.value);
                                reset();
                            }}
                            disabled={!isWired || !start1 || startOpts2.length === 0}>
                        {!start1 ? (
                            <option value="">Pick Train #1 first</option>
                        ) : startOpts2.length === 0 ? (
                            <option value="">No valid starting segments</option>
                        ) : (
                            <>
                                <option value="" disabled>Choose a starting segment</option>
                                {startOpts2.map(o => (
                                    <option key={o.value} value={o.value}>{o.label}</option>
                                ))}
                            </>
                        )}
                    </select>
                </div>

                {start1 && isWired && startOpts2.length === 0 && (
                    <div className="controls-warn-row hand-warn">
                        No remaining option satisfies both rules – starting segment must sit outside train #1's
                        destination block (<span className="mono">{[...destBlock1].join(", ")}</span>),
                        and the terminal must differ from <span className="mono">{terminal1}</span>.
                    </div>
                )}

                {start1 && start2 && isWired && (() => {
                    const r2 = layout.routes[start2];
                    return (
                        <div className="controls-info-row hand-info">
                            Train #1 (<span className="mono">{route1.id}</span>) parks at
                            <span className="mono"> {terminal1}</span>.
                            Train #2 (<span className="mono">{r2.id}</span>) parks at
                            <span className="mono"> {r2.terminal}</span>.
                            {route1.conflicts.includes(start2)
                                ? " Routes conflict – the interlocking sequences them."
                                : " Routes don't conflict – will run in parallel."}
                            {" "}✓
                        </div>
                    );
                })()}

                <div className="ctrl ctrl-actions">
                    <button className="sim-btn" onClick={simulate}
                            disabled={!isWired || !start1 || !start2}>
                        Simulate <span style={{marginLeft: 6}}>→</span>
                    </button>
                    {simulated && (
                        <button className="reset-btn" onClick={reset}>
                            Reset <span style={{marginLeft: 6, fontSize: "1.5em"}}>↺</span>
                        </button>
                    )}
                </div>
            </section>

            {/* ----------------- Scrubber ----------------- */}
            {simulated && isWired && (
                <section className="scrubber sketch-card">
                    <div className="scrubber-ctrl">
                        <button className="step-btn"
                                onClick={() => setStep(Math.max(0, step - 1))}
                                disabled={totalSteps === 0}>
                            ◀ prev
                        </button>

                        <input type="range" min={0} max={Math.max(0, totalSteps - 1)} value={step}
                               onChange={e => setStep(parseInt(e.target.value))}
                               disabled={totalSteps === 0}
                        />

                        <button className="step-btn"
                                onClick={() => setStep(Math.min(totalSteps - 1, step + 1))}
                                disabled={totalSteps === 0}>
                            next ▶
                        </button>

                        <div className="step-count">
                            {totalSteps === 0 ? "..." : `step ${step} / ${totalSteps - 1}`}
                        </div>

                        <SourceBadge status={srcStatus} requested={tw.stepSource}/>
                    </div>

                    <div className="step-meta">
                        <div className="step-label">
                            {snapshot?.label || (srcStatus?.phase === "loading" ? "loading steps..." : "")}
                        </div>

                        <div className="step-note">{snapshot?.note}</div>
                    </div>
                </section>
            )}

            {/* ----------------- Table ----------------- */}
            <section className="table-wrap sketch-card">
                {!isWired ? (
                    <div className="stub">
                        <div className="hand-stub-title">{layoutId}</div>
                        <div className="hand-stub-body">layout not available.</div>
                    </div>
                ) : !simulated ? (
                    <div className="stub">
                        <div className="hand-stub-title">Press <span
                            style={{borderBottom: "1.5px dashed #1a1a1a"}}>Simulate</span> to begin
                        </div>
                        <div className="hand-stub-body">
                            The route progression table will appear here; scrub through the steps with the slider.
                        </div>
                    </div>
                ) : !snapshot ? (
                    <div className="stub">
                        <div
                            className="hand-stub-title">{srcStatus?.phase === "loading" ? "loading steps…" : "no steps"}</div>
                        <div className="hand-stub-body">
                            {srcStatus?.phase === "loading"
                                ? <>fetching from <span
                                    className="mono">{SOURCE_LABEL[srcStatus.source] || srcStatus.source}</span>…</>
                                : "the step source returned nothing."}
                        </div>
                    </div>
                ) : (
                    <table className="route-table">
                        <thead>
                        <tr>
                            <th>Route</th>
                            <th>Transition</th>
                            <th>Mode</th>
                            <th>Path</th>
                            <th>Signals</th>
                            <th>Completion</th>
                        </tr>
                        </thead>
                        <tbody>
                        {[...activeRoutes].map(rid => {
                            const r = layout.routes[rid];
                            return (
                                <RouteRow
                                    key={rid}
                                    id={rid}
                                    dir={r.dir}
                                    snapshot={snapshot[rid]}
                                    dense={dense}
                                    dim={false}
                                />
                            );
                        })}
                        </tbody>
                    </table>
                )}
            </section>

            {/* ----------------- Footnote ----------------- */}
            <footer className="hand-foot">
                Derived from <span className="mono">SECTIONAL_INTERLOCKING.md</span> + parsed
                <span className="mono"> *.bahn</span>/<span className="mono">*.yml</span> configs.
                Steps come from the <span className="mono">{SOURCE_LABEL[tw.stepSource] || tw.stepSource}</span> source
                (switch in Tweaks). <span className="mono">json</span>/<span className="mono">api</span> run the real
                <span className="mono">InterlockingSystem</span> via <span className="mono">tests/sim_bridge.py</span>.
            </footer>

            {/* ----------------- Tweaks ----------------- */}
            <TweaksPanel title="Tweaks">
                <TweakSection label="data source"/>
                <TweakRadio
                    label="steps from"
                    value={tw.stepSource}
                    options={["synth", "json", "api"]}
                    onChange={v => setTweak("stepSource", v)}
                />
                <div style={{
                    fontFamily: "'JetBrains Mono', monospace", fontSize: 10.5,
                    color: "#777", lineHeight: 1.5, margin: "2px 2px 4px",
                }}>
                    {tw.stepSource === "synth" && "in-browser narrative – no backend."}
                    {tw.stepSource === "json" && <>static files in <span style={{color: "#1a1a1a"}}>steps/</span> from
                        python/export_steps.py</>}
                    {tw.stepSource === "api" && <>live GET <span style={{color: "#1a1a1a"}}>/simulate</span> – run
                        python/server.py</>}
                </div>
                <TweakSection label="layout"/>
                <TweakRadio
                    label="density"
                    value={tw.density}
                    options={["comfy", "compact"]}
                    onChange={v => setTweak("density", v)}
                />
                <TweakToggle
                    label="show legend"
                    value={tw.showLegend}
                    onChange={v => setTweak("showLegend", v)}
                />
            </TweaksPanel>
        </div>
    );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App/>);
