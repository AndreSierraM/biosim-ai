import { Suspense, lazy, useEffect, useRef, useState } from "react";
const CellViewer = lazy(() => import("./viewer/CellViewer"));
import DoseChart from "./viewer/DoseChart";
import Sidebar, { type View } from "./components/Sidebar";
import PromptBar from "./components/PromptBar";
import CopilotPanel, { type ArmRun } from "./components/CopilotPanel";
import ParamSliders, { type SliderValues } from "./components/ParamSliders";
import HowItWorks from "./components/HowItWorks";
import { api, pollRun } from "./api";
import { PREVIEW_LABEL, loadPreviewSpheroid } from "./preview";
import { buildConclusion } from "./conclusion";
import type { EngineInfo, Job, Plan, TrajectoryFile } from "./types";
import "./App.css";

const DEFAULT_PROMPT = "Compara oxygen availability normal vs baja en el esferoide tumoral";
const API_BASE = import.meta.env.VITE_API_URL ?? "";

interface SweepRun {
  dose: number;
  job: Job;
  traj: TrajectoryFile | null;
}

interface HistoryRow {
  id: string;
  label: string;
  job: Job;
}

const HISTORY_KEY = "biosim-history-v1";
const HISTORY_MAX = 20;

function loadHistoryIds(): { id: string; label: string }[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter(
        (r): r is { id: string; label: string } =>
          typeof r === "object" && r !== null &&
          typeof (r as { id: string }).id === "string" &&
          typeof (r as { label: string }).label === "string",
      )
      .slice(0, HISTORY_MAX);
  } catch {
    return [];
  }
}

/** Stable idempotency key: same generation+inputs dedupe accidental double
 *  submits; any new action bumps the generation so replicas run for real. */
function idemKey(gen: number, engine: string, values: Record<string, number>, seed: number): string {
  const params = Object.keys(values).sort().map((k) => `${k}=${values[k]}`).join(",");
  return `g${gen}:${engine}:${seed}:${params}`.slice(0, 120);
}

const SWEEP_OXYGEN = 38;
const SWEEP_SEED = 7;
const SWEEP_CONCURRENCY = 2;

/** Slider keys map 1:1 to PhysiCell adapter params; other engines keep plan values. */
const PHYSICELL_SLIDER_KEYS = ["oxygen", "drug_dose", "initial_cells"] as const;

function err(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

/** Peak total cells across frames; shared y-scale so arms stay comparable. */
function trajMaxCells(traj: TrajectoryFile): number {
  let m = 1;
  for (const f of traj.frames) m = Math.max(m, f.cells.length);
  return m;
}

/** Old phones get fewer frames over the wire (stride 2 ≈ half the JSON). */
function trajStride(): number {
  if (typeof window === "undefined") return 1;
  if (window.innerWidth < 700) return 2;
  if (typeof window.matchMedia === "function" && window.matchMedia("(pointer: coarse)").matches) return 2;
  return 1;
}

function isLightPreview(): boolean {
  if (typeof window === "undefined") return false;
  return window.innerWidth < 700;
}

function isAbort(e: unknown): boolean {
  return e instanceof DOMException && e.name === "AbortError";
}

export default function App() {
  const [view, setView] = useState<View>("experiment");
  const [engines, setEngines] = useState<EngineInfo[] | null>(null);
  const [plannerBackend, setPlannerBackend] = useState<"fixture" | "live" | null>(null);
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [runs, setRuns] = useState<Record<string, ArmRun>>({});
  const [sliders, setSliders] = useState<SliderValues>({ oxygen: 38, drug: 0, cells: 12 });
  const [selectedArm, setSelectedArm] = useState<string | null>(null);
  const [ladder, setLadder] = useState("0, 0.3, 1, 3, 10");
  const [history, setHistory] = useState<HistoryRow[]>([]);
  const [sweep, setSweep] = useState<SweepRun[]>([]);
  const [selDose, setSelDose] = useState<number | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sweepError, setSweepError] = useState<string | null>(null);
  const [preview, setPreview] = useState<TrajectoryFile | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [howOpen, setHowOpen] = useState(false);
  const pollControllers = useRef<Set<AbortController>>(new Set());
  /** Experiment generation: stale async results never touch current state. */
  const genRef = useRef(0);

  // Cancela polls activos al desmontar.
  useEffect(() => {
    const tracked = pollControllers.current;
    return () => {
      for (const c of tracked) c.abort();
      tracked.clear();
    };
  }, []);

  // Cancela polls activos al reintentar (nuevo run/sweep reemplaza al anterior).
  const abortPolls = () => {
    for (const c of pollControllers.current) c.abort();
    pollControllers.current.clear();
  };

  const trackPoll = (): { signal: AbortSignal; done: () => void } => {
    const c = new AbortController();
    pollControllers.current.add(c);
    return { signal: c.signal, done: () => void pollControllers.current.delete(c) };
  };

  const enginesOk = engines !== null && engines.some((e) => e.available);
  // Honesto: "live" solo con Meta real; fixture es demo sin llamada a Meta.
  const badgeState =
    error || (engines !== null && !enginesOk)
      ? "offline"
      : engines === null
        ? "connecting"
        : plannerBackend === "live"
          ? "live"
          : plannerBackend === "fixture"
            ? "demo"
            : "ready";
  const badgeText =
    badgeState === "live"
      ? `live Meta · ${plan?.model_version ?? "planner"} + engines`
      : badgeState === "demo"
        ? `demo IA · fixture ${plan?.model_version ?? ""} (sin llamada Meta)`
        : badgeState === "ready"
          ? "engines ok · plan to verify AI"
          : badgeState === "offline"
            ? "offline"
            : "connecting…";

  useEffect(() => {
    api
      .engines()
      .then((r) => setEngines(r.engines))
      .catch((e: unknown) => {
        setError(
          `API unreachable (${API_BASE || "same-origin /v1 via dev proxy"}) — start it: cd services/api && .venv/bin/python -m uvicorn app.main:app --port 8123 (${err(e)})`,
        );
      });
  }, []);

  // Golden preview spheroid: real computed positions, shown until the first run lands.
  useEffect(() => {
    const c = new AbortController();
    loadPreviewSpheroid(c.signal, isLightPreview())
      .then(setPreview)
      .catch((e: unknown) => {
        if (!isAbort(e)) setPreviewError(err(e));
      });
    return () => c.abort();
  }, []);

  const doPlan = async () => {
    const gen = ++genRef.current;
    abortPolls();
    setError(null);
    setSweepError(null);
    setPlan(null);
    setRuns({});
    setSweep([]);
    setSelDose(null);
    setSelectedArm(null);
    setPlannerBackend(null);
    setBusy("Planning…");
    try {
      const p = await api.plan(prompt);
      if (genRef.current !== gen) return;
      setPlan(p);
      if (p.planner_backend) setPlannerBackend(p.planner_backend);
      else if (p.model_version === "planner-fixture") setPlannerBackend("fixture");
      else if (p.model_version) setPlannerBackend("live");
      if (p.validated && p.arms.length > 0) setSelectedArm(p.arms[0].name);
    } catch (e) {
      if (genRef.current !== gen) return;
      if (err(e).toLowerCase().includes("planner")) setPlannerBackend(null);
      setError(err(e));
    } finally {
      if (genRef.current === gen) setBusy("");
    }
  };

  const logHistory = (row: HistoryRow) => {
    setHistory((prev) => {
      const rest = prev.filter((r) => r.id !== row.id);
      return [...rest, row].slice(-HISTORY_MAX);
    });
  };

  // Persist only own ids+labels (never other users' jobs); states revalidate on load.
  useEffect(() => {
    try {
      localStorage.setItem(
        HISTORY_KEY,
        JSON.stringify(history.map((r) => ({ id: r.id, label: r.label }))),
      );
    } catch {
      // Private mode / quota: history simply stays in memory.
    }
  }, [history]);

  // Revalidate stored history after reload: drop missing, refresh states.
  useEffect(() => {
    let cancelled = false;
    const stored = loadHistoryIds();
    if (stored.length === 0) return;
    (async () => {
      const rows: HistoryRow[] = [];
      for (const s of stored) {
        try {
          const job = await api.getRun(s.id);
          rows.push({ id: s.id, label: s.label, job });
        } catch {
          // Deleted/unknown run: stays out of the list, no crash.
        }
        if (cancelled) return;
      }
      if (!cancelled && rows.length > 0) setHistory(rows);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const runArm = async (
    armName: string,
    engine: string,
    values: Record<string, number>,
    seed: number,
    gen: number,
  ) => {
    const { signal, done } = trackPoll();
    try {
      const job = await api.submit(engine, values, seed, idemKey(gen, engine, values, seed));
      if (genRef.current !== gen) return;
      setRuns((prev) => ({ ...prev, [armName]: { job, traj: prev[armName]?.traj ?? null } }));
      logHistory({ id: job.id, label: `brazo ${armName}`, job });
      const final = await pollRun(job.id, { signal });
      if (genRef.current !== gen) return;
      logHistory({ id: final.id, label: `brazo ${armName}`, job: final });
      if (final.state !== "completed") {
        throw new Error(`run ${final.id} ${final.state}: ${final.error ?? ""}`);
      }
      const traj = await api.trajectory(final.id, trajStride());
      if (genRef.current !== gen) return;
      setRuns((prev) => ({ ...prev, [armName]: { job: final, traj } }));
    } catch (e) {
      if (genRef.current !== gen || isAbort(e)) return;
      setError(err(e));
    } finally {
      done();
    }
  };

    /** Plan keys whose values differ across arms: the experiment's variables. */
  const variedKeys = (() => {
    if (!plan?.validated) return new Set<string>();
    const keys = new Set(plan.arms.flatMap((a) => Object.keys(a.spec.parameters)));
    const varied = new Set<string>();
    for (const k of keys) {
      const vals = new Set(plan.arms.map((a) => a.spec.parameters[k]?.value));
      if (vals.size > 1) varied.add(k);
    }
    return varied;
  })();
  const allPhysicell =
    !plan?.validated || plan.arms.every((a) => a.spec.engine === "physicell");

  /**
   * Effective run params: plan values, overridden by sliders ONLY for shared
   * assay conditions. Keys the plan varies across arms (the experimental
   * variables) are never clobbered, and non-PhysiCell arms keep plan values.
   */
  const armValues = (armName: string): { engine: string; values: Record<string, number>; seed: number } | null => {
    const arm = plan?.arms.find((a) => a.name === armName);
    if (!arm) return null;
    const values: Record<string, number> = Object.fromEntries(
      Object.entries(arm.spec.parameters).map(([k, q]) => [k, q.value]),
    );
    if (arm.spec.engine === "physicell" && allPhysicell) {
      const overrides: Record<(typeof PHYSICELL_SLIDER_KEYS)[number], number> = {
        oxygen: sliders.oxygen,
        drug_dose: sliders.drug,
        initial_cells: Math.round(sliders.cells),
      };
      for (const [k, v] of Object.entries(overrides)) {
        if (!variedKeys.has(k)) values[k] = v;
      }
    }
    return { engine: arm.spec.engine, values, seed: arm.spec.seed };
  };

  const UNIT_OF: Record<string, string> = {
    oxygen: "mmHg",
    drug_dose: "µM",
    initial_cells: "células",
  };

  /** Honest per-arm subtitle: actual run params when available, else effective plan+sliders. */
  const subtitleFor = (armName: string): string => {
    const actual = runs[armName]?.job.params;
    const src =
      actual && Object.keys(actual).length > 0 ? actual : armValues(armName)?.values;
    if (!src || Object.keys(src).length === 0) return armName;
    return Object.entries(src)
      .map(([k, v]) => {
        const unit = UNIT_OF[k];
        return `${k.replace(/_/g, " ")} ${v}${unit ? ` ${unit}` : ""}`;
      })
      .join(" · ");
  };

  const sliderLocks: Record<"oxygen" | "drug" | "cells", string | null> = (() => {
    const none = { oxygen: null, drug: null, cells: null };
    if (!plan?.validated) return none;
    if (!allPhysicell) {
      const msg = "Este motor usa los valores del plan";
      return { oxygen: msg, drug: msg, cells: msg };
    }
    const lockFor = (key: string): string | null => {
      if (!variedKeys.has(key)) return null;
      const vals = plan.arms.map((a) => String(a.spec.parameters[key]?.value)).join(" vs ");
      return `Lo define el plan (${vals})`;
    };
    return {
      oxygen: lockFor("oxygen"),
      drug: lockFor("drug_dose"),
      cells: lockFor("initial_cells"),
    };
  })();

  const doRunAll = async () => {
    if (!plan?.validated) return;
    const gen = ++genRef.current;
    abortPolls();
    setError(null);
    setSweepError(null);
    setBusy("Running both arms…");
    try {
      await Promise.all(
        plan.arms.map((arm) => {
          const spec = armValues(arm.name);
          if (!spec) throw new Error(`arm ${arm.name} missing from plan`);
          return runArm(arm.name, spec.engine, spec.values, spec.seed, gen);
        }),
      );
    } catch (e) {
      if (genRef.current !== gen || isAbort(e)) return;
      setError(err(e));
    } finally {
      if (genRef.current === gen) setBusy("");
    }
  };

  const doRerun = async (armName: string) => {
    const spec = armValues(armName);
    if (!spec) return;
    // New generation: a rerun always computes fresh (replicas stay honest).
    const gen = ++genRef.current;
    abortPolls();
    setError(null);
    setSweepError(null);
    setBusy(`Rerunning ${armName}…`);
    try {
      await runArm(armName, spec.engine, spec.values, spec.seed, gen);
    } catch (e) {
      if (genRef.current !== gen || isAbort(e)) return;
      setError(err(e));
    } finally {
      if (genRef.current === gen) setBusy("");
    }
  };

  const runSweepDose = async (dose: number, gen: number) => {
    const { signal, done } = trackPoll();
    try {
      const values = { oxygen: SWEEP_OXYGEN, drug_dose: dose };
      const job = await api.submit(
        "physicell",
        values,
        SWEEP_SEED,
        idemKey(gen, "physicell", values, SWEEP_SEED),
      );
      if (genRef.current !== gen) return;
      setSweep((prev) => [...prev, { dose, job, traj: null }]);
      logHistory({ id: job.id, label: `dosis ${dose} µM`, job });
      const final = await pollRun(job.id, { signal });
      if (genRef.current !== gen) return;
      logHistory({ id: final.id, label: `dosis ${dose} µM`, job: final });
      if (final.state !== "completed") {
        setSweep((prev) => prev.map((s) => (s.job.id === final.id ? { dose, job: final, traj: null } : s)));
        throw new Error(`dose ${dose}: run ${final.id} ${final.state}: ${final.error ?? ""}`);
      }
      const traj = await api.trajectory(final.id, trajStride());
      if (genRef.current !== gen) return;
      setSweep((prev) => prev.map((s) => (s.job.id === final.id ? { dose, job: final, traj } : s)));
    } catch (e) {
      if (genRef.current !== gen || isAbort(e)) {
        if (genRef.current === gen) {
          setSweep((prev) => prev.filter((s) => s.traj !== null || s.dose !== dose));
        }
        return;
      }
      throw e;
    } finally {
      done();
    }
  };

  const doSweep = async () => {
    const doses = [...new Set(
      ladder
        .split(/[,\s]+/)
        .filter((t) => t.length > 0)
        .map(Number),
    )].sort((a, b) => a - b);
    if (doses.length === 0 || doses.some((d) => !Number.isFinite(d) || d < 0 || d > 100)) {
      const msg = "dose ladder must be numbers between 0 and 100 µM, e.g. 0, 0.3, 1, 3, 10";
      setError(msg);
      setSweepError(msg);
      return;
    }
    if (doses.length > 8) {
      const msg = "at most 8 doses per sweep";
      setError(msg);
      setSweepError(msg);
      return;
    }
    abortPolls();
    const gen = genRef.current;
    setError(null);
    setSweepError(null);
    setSweep([]);
    setSelDose(doses[0]);
    setBusy(`Running dose sweep (${doses.length} runs)…`);
    const queue = [...doses];
    const failures: string[] = [];
    const worker = async () => {
      while (queue.length > 0) {
        const dose = queue.shift() as number;
        try {
          await runSweepDose(dose, gen);
        } catch (e) {
          if (genRef.current !== gen || isAbort(e)) return;
          failures.push(err(e));
        }
      }
    };
    await Promise.all(
      Array.from({ length: Math.min(SWEEP_CONCURRENCY, doses.length) }, () => worker()),
    );
    if (genRef.current !== gen) return;
    if (failures.length > 0) {
      const msg = `${failures.length} of ${doses.length} doses failed: ${failures.join("; ")}`;
      setError(msg);
      setSweepError(msg);
    }
    setBusy("");
  };

  const doExport = async (id: string) => {
    try {
      const bundle = await api.bundle(id);
      const blob = new Blob([JSON.stringify(bundle, null, 1)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `${id}-bundle.json`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) {
      setError(err(e));
    }
  };

  const exportArm = (armName: string) => {
    const run = runs[armName];
    if (run) void doExport(run.job.id);
  };

  const trajs = plan?.validated
    ? plan.arms.map((a) => runs[a.name]?.traj).filter((t): t is TrajectoryFile => !!t)
    : [];
  // Hero rule: golden preview until the first real trajectory lands; no empty boxes ever.
  const hasCompletedRun =
    trajs.length > 0 || sweep.some((s) => s.traj !== null);
  const showPreview = !hasCompletedRun;
  const planning = busy.startsWith("Planning");
  const running = busy.startsWith("Running") || busy.startsWith("Rerunning");
  /** The copilot panel only earns its space once there is a plan to show. */
  const showCopilot = planning || plan !== null;
  const physicell = engines?.find((e) => e.engine_id === "physicell");
  const firstTraj =
    Object.values(runs).map((r) => r.traj).find((t) => !!t) ??
    sweep.map((s) => s.traj).find((t) => !!t) ??
    null;

  const armNames = plan?.validated ? plan.arms.map((a) => a.name) : [];
  const activeArm = selectedArm && armNames.includes(selectedArm) ? selectedArm : armNames[0] ?? null;
  const activeTraj = activeArm ? (runs[activeArm]?.traj ?? null) : null;
  const viewerData = activeTraj ?? preview;
  const viewerIsLive = activeTraj !== null;
  const sharedYMax = trajs.length > 0 ? Math.max(...trajs.map(trajMaxCells)) : undefined;
  const conclusion =
    plan?.validated && trajs.length > 0
      ? buildConclusion(
          plan.arms
            .filter((a) => runs[a.name]?.traj)
            .map((a) => ({
              label: `Condición ${plan.arms.indexOf(a) + 1} (${a.name})`,
              summary: (runs[a.name].traj as TrajectoryFile).summary,
            })),
        )
      : null;

  const historyRows = [...history].reverse();

  return (
    <div className="shell">
      <Sidebar view={view} onNav={setView}>
        {view === "experiment" && (
          <ParamSliders values={sliders} onChange={setSliders} disabled={!!busy} locks={sliderLocks} />
        )}
      </Sidebar>
      <div className={view === "experiment" ? "main is-feed" : "main"}>
        <header className="topbar">
          <span className={`status is-${badgeState}`}>
            <span className="dot" aria-hidden="true" />
            {badgeText}
          </span>
          <button type="button" className="how-btn" onClick={() => setHowOpen(true)}>
            <span aria-hidden="true">?</span> Cómo funciona
          </button>
        </header>

        {view === "experiment" && (
          <>
            <div className="feed">
            <div className="feed-head">
              <h2 className="prompt-title">¿Qué quieres descubrir?</h2>
            </div>

            {error && <p className="error-banner" role="alert">{error}</p>}
            {busy && (
              <p className="loading" role="status" aria-live="polite">
                <span className="spinner" aria-hidden="true" />
                {busy}
              </p>
            )}

            {plan && !plan.validated && (
              <section className="refusal-card" aria-label="plan rechazado">
                <h2>No se pudo planificar</h2>
                <p>{plan.refusal?.reason ?? "unknown reason"}</p>
                <p className="hint">
                  Prueba con oxígeno (p. ej. “compara oxygen availability normal vs baja”) o dosis de
                  fármaco (p. ej. “qué drug dose frena el crecimiento”).
                </p>
              </section>
            )}

            <div className={showCopilot ? "stage-grid" : "stage-grid is-solo"}>
              <div className="stage-main">
                <section className="viewer-card" aria-label="simulación 3D">
                  {armNames.length > 1 && (
                    <div className="arm-tabs" role="tablist" aria-label="brazos">
                      {armNames.map((name, i) => (
                        <button
                          key={name}
                          type="button"
                          role="tab"
                          aria-selected={activeArm === name}
                          className={activeArm === name ? "arm-tab is-on" : "arm-tab"}
                          onClick={() => setSelectedArm(name)}
                        >
                          Condición {i + 1} · {name}
                        </button>
                      ))}
                    </div>
                  )}
                  {viewerData ? (
                    <Suspense
                      fallback={
                        <div className="viewer-skeleton" role="status" aria-label="cargando visor 3D…">
                          <span className="visually-hidden">cargando visor 3D…</span>
                        </div>
                      }
                    >
                      <CellViewer
                        key={viewerIsLive ? runs[activeArm as string].job.id : "preview"}
                        data={viewerData}
                        yMax={sharedYMax}
                        autoRotate={!viewerIsLive}
                        badge={
                          viewerIsLive ? (
                            <span className="live-badge">
                              <span className="dot" aria-hidden="true" />
                              Simulación en vivo
                            </span>
                          ) : (
                            <span className="preview-badge">{PREVIEW_LABEL}</span>
                          )
                        }
                      />
                    </Suspense>
                  ) : previewError ? (
                    <p className="inline-error" role="alert">
                      Preview unavailable ({previewError}). Genera un plan para correr el motor.
                    </p>
                  ) : (
                    <div className="viewer-skeleton" role="status" aria-label="cargando preview…">
                      <span className="visually-hidden">cargando preview…</span>
                    </div>
                  )}
                </section>

                {conclusion && (
                  <section className="conclusion-card" aria-label="conclusión de BioSim AI">
                    <span className="conclusion-icon" aria-hidden="true">✦</span>
                    <div>
                      <h2>Conclusión de BioSim AI</h2>
                      <p>{conclusion}</p>
                      <p className="conclusion-src">
                        Generada por reglas desde los resúmenes calculados · sin LLM para números
                      </p>
                    </div>
                  </section>
                )}

                {physicell?.available && !showPreview && (
                  <section className="sweep-card" aria-label="barrido de dosis">
                    <h2>
                      Barrido de dosis{" "}
                      <span className="model">oxígeno {SWEEP_OXYGEN} mmHg · semilla {SWEEP_SEED}</span>
                    </h2>
                    <div className="sweep-row">
                      <div className="sweep-field">
                        <input
                          className="field"
                          value={ladder}
                          onChange={(e) => {
                            setLadder(e.target.value);
                            setSweepError(null);
                          }}
                          aria-label="dosis en µM separadas por comas"
                          aria-invalid={sweepError ? true : undefined}
                          placeholder="0, 0.3, 1, 3, 10"
                        />
                        {sweepError && (
                          <p className="inline-error" role="alert">
                            {sweepError}
                          </p>
                        )}
                      </div>
                      <button type="button" className="primary-btn" onClick={doSweep} disabled={!!busy}>
                        Run sweep
                      </button>
                    </div>
                    {sweep.length === 0 && (
                      <p className="hint">
                        Escribe dosis separadas por comas (µM, máx. 8) y pulsa{" "}
                        <strong>Run sweep</strong> para ver la curva dosis-respuesta e IC50.
                      </p>
                    )}
                    {sweep.length > 0 && (
                      <>
                        {sweep.some((s) => s.traj !== null) && (
                          <DoseChart
                            points={sweep
                              .filter((s) => s.traj !== null)
                              .map((s) => ({ dose: s.dose, live: s.traj!.summary.final_live }))}
                            selected={selDose}
                            onSelect={setSelDose}
                          />
                        )}
                        {(() => {
                          const sel = sweep.find((s) => s.dose === selDose);
                          if (!sel) return null;
                          const sweepMax = Math.max(
                            ...sweep
                              .filter((s) => s.traj !== null)
                              .map((s) => trajMaxCells(s.traj!)),
                          );
                          return sel.traj ? (
                            <Suspense
                              fallback={
                                <div className="viewer-skeleton" role="status" aria-label="cargando visor 3D…">
                                  <span className="visually-hidden">cargando visor 3D…</span>
                                </div>
                              }
                            >
                              <CellViewer key={sel.job.id} data={sel.traj} yMax={sweepMax} />
                            </Suspense>
                          ) : (
                            <div className="viewer-skeleton" role="status" aria-label={`calculando dosis ${sel.dose}…`}>
                              <span className="visually-hidden">calculando dosis {sel.dose}…</span>
                            </div>
                          );
                        })()}
                      </>
                    )}
                  </section>
                )}
              </div>

              {showCopilot && (
              <CopilotPanel
                plan={plan}
                runs={runs}
                planning={planning}
                running={running}
                busy={!!busy}
                subtitleFor={subtitleFor}
                onRunAll={doRunAll}
                onRerun={doRerun}
                onExport={exportArm}
              />
            )}
            </div>
            </div>

            <div className="composer">
              <PromptBar
                prompt={prompt}
                onPromptChange={setPrompt}
                onPlan={doPlan}
                planning={planning}
                busy={!!busy}
              />
            </div>
          </>
        )}

        {view === "history" && (
          <section className="page-card" aria-label="mis experimentos">
            <h2>Mis experimentos</h2>
            <p className="page-sub">Tus runs de este navegador (se conservan al recargar).</p>
            {historyRows.length === 0 ? (
              <p className="hint">
                Aún no hay runs. <button type="button" className="link-btn" onClick={() => setView("experiment")}>Experimenta</button> para crear el primero.
              </p>
            ) : (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>run</th>
                      <th>brazo</th>
                      <th>estado</th>
                      <th>vivas</th>
                      <th>muertas</th>
                      <th>radio</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {historyRows.map((r) => (
                      <tr key={r.id}>
                        <td title={r.id}>{r.id.slice(0, 8)}</td>
                        <td>{r.label}</td>
                        <td>{r.job.state}</td>
                        <td>{r.job.summary ? r.job.summary.final_live : "—"}</td>
                        <td>{r.job.summary ? r.job.summary.final_dead : "—"}</td>
                        <td>{r.job.summary ? `${r.job.summary.final_radius_um.toFixed(0)} µm` : "—"}</td>
                        <td>
                          <button type="button" onClick={() => void doExport(r.id)}>
                            Exportar
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}

        {view === "learn" && (
          <section className="page-card" aria-label="aprender">
            <h2>Aprender</h2>
            <p className="page-sub">Qué calcula BioSim AI y qué supone cada run.</p>
            <div className="learn-grid">
              <article className="learn-card">
                <h3>El modelo</h3>
                <p>
                  PhysiCell simula cada célula como un agente en 3D: crece, se divide y puede morir
                  por falta de oxígeno (necrosis bajo 8 mmHg) o por fármaco (apoptosis Hill sobre
                  todas las vivas). Las posiciones del visor son las calculadas por el motor.
                </p>
              </article>
              <article className="learn-card">
                <h3>Supuestos del último run</h3>
                {firstTraj ? (
                  <ul>
                    {firstTraj.meta.assumptions.map((a) => (
                      <li key={a}>{a}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="hint">Corre tu primera simulación para ver sus supuestos.</p>
                )}
              </article>
              <article className="learn-card">
                <h3>Motores</h3>
                {engines ? (
                  <ul>
                    {engines.map((e) => (
                      <li key={e.engine_id}>
                        {e.engine_id} v{e.engine_version ?? "?"} —{" "}
                        {e.available ? "disponible" : `no disponible (${e.reason})`}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="hint">Conectando con la API…</p>
                )}
              </article>
            </div>
          </section>
        )}

      </div>
      <HowItWorks open={howOpen} onClose={() => setHowOpen(false)} />
    </div>
  );
}
