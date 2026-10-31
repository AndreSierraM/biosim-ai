import type { Job, Plan, TrajectoryFile } from "../types";
import { fmtT50 } from "../conclusion";

export interface ArmRun {
  job: Job;
  traj: TrajectoryFile | null;
}

interface Props {
  plan: Plan | null;
  runs: Record<string, ArmRun>;
  planning: boolean;
  running: boolean;
  busy: boolean;
  /** Effective/actual subtitle per arm (real run params, not just plan). */
  subtitleFor: (armName: string) => string;
  onRunAll: () => void;
  onRerun: (arm: string) => void;
  onExport: (arm: string) => void;
}

function fmtUnit(unit: string): string {
  return unit === "uM" ? "µM" : unit;
}

/** Short honest subtitle from the arm's planned parameters. */
export function armSubtitle(plan: Plan | null, armName: string): string {
  const arm = plan?.arms.find((a) => a.name === armName);
  if (!arm) return armName;
  const bits = Object.entries(arm.spec.parameters).map(
    ([k, q]) => `${k.replace(/_/g, " ")} ${q.value} ${fmtUnit(q.unit)}`,
  );
  return bits.length > 0 ? bits.join(" · ") : armName;
}

function Metric({
  label,
  value,
  frac,
}: {
  label: string;
  value: string;
  frac: number;
}) {
  const pct = Math.max(0, Math.min(1, Number.isFinite(frac) ? frac : 0)) * 100;
  return (
    <div className="metric">
      <div className="metric-top">
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <span className="metric-bar" aria-hidden="true">
        <i style={{ width: `${pct.toFixed(0)}%` }} />
      </span>
    </div>
  );
}

export default function CopilotPanel({
  plan,
  runs,
  planning,
  running,
  busy,
  subtitleFor,
  onRunAll,
  onRerun,
  onExport,
}: Props) {
  const arms = plan?.validated ? plan.arms : [];
  const trajs = arms
    .map((a) => runs[a.name]?.traj)
    .filter((t): t is TrajectoryFile => !!t);
  const anyRunning = running || arms.some((a) => {
    const st = runs[a.name]?.job.state;
    return st === "queued" || st === "running";
  });
  const allDone = arms.length > 0 && trajs.length === arms.length;

  const step1 = plan?.validated === true ? "done" : planning ? "active" : "todo";
  const step2 = plan?.validated === true ? "done" : planning ? "todo" : "todo";
  const step3 = allDone ? "done" : anyRunning ? "active" : "todo";

  const maxLive = Math.max(1, ...trajs.map((t) => t.summary.final_live));
  const maxDead = Math.max(1, ...trajs.map((t) => t.summary.final_dead));
  const maxR = Math.max(1, ...trajs.map((t) => t.summary.final_radius_um));
  const t50vals = trajs.map((t) => t.summary.t50_min ?? null);
  const maxT50 = Math.max(1, ...t50vals.filter((v): v is number => v !== null));

  const steps = [
    { state: step1, label: "Entendí tu pregunta" },
    { state: step2, label: "Diseñé el experimento" },
    {
      state: step3,
      label: allDone ? "Simulación completa" : "Ejecutando simulación…",
    },
  ];

  return (
    <aside className="copilot" aria-label="BioSim AI">
      <h2 className="copilot-title">
        <span className="copilot-spark" aria-hidden="true">
          ✦
        </span>
        BioSim AI
      </h2>

      <ol className="checklist" aria-label="progreso">
        {steps.map((s) => (
          <li key={s.label} className={`check is-${s.state}`}>
            <span className="check-dot" aria-hidden="true">
              {s.state === "done" ? "✓" : s.state === "active" ? "…" : "○"}
            </span>
            {s.label}
          </li>
        ))}
      </ol>

      <h3 className="results-title">
        <span className={trajs.length > 0 ? "results-dot is-on" : "results-dot"} aria-hidden="true" />
        Resultados listos
      </h3>
      {plan !== null || trajs.length > 0 ? (
        <p className="results-sub">
          {trajs.length > 0
            ? "Aquí puedes ver lo que pasó y comparar las condiciones."
            : "Cuando termine el run verás aquí la comparativa."}
        </p>
      ) : null}

      {plan?.validated && (
        <button
          type="button"
          className="run-all"
          onClick={onRunAll}
          disabled={busy}
        >
          {anyRunning ? "Ejecutando…" : trajs.length > 0 ? "Volver a ejecutar" : "Ejecutar simulación"}
        </button>
      )}

      <div className="conditions">
        {arms.map((arm, i) => {
          const run = runs[arm.name];
          const traj = run?.traj ?? null;
          const s = traj?.summary ?? null;
          const t50 = s ? fmtT50(s.t50_min) : null;
          return (
            <article
              key={arm.name}
              className={i === 0 ? "condition is-a" : "condition is-b"}
              aria-label={`Condición ${i + 1}: ${arm.name}`}
            >
              <h4>Condición {i + 1}</h4>
              <p className="condition-sub">{subtitleFor(arm.name)}</p>
              {s ? (
                <div className="metrics">
                  <Metric label="Vivas" value={s.final_live.toLocaleString("es-ES")} frac={s.final_live / maxLive} />
                  <Metric label="Muertas" value={s.final_dead.toLocaleString("es-ES")} frac={s.final_dead / maxDead} />
                  <Metric
                    label="Radio"
                    value={`${s.final_radius_um.toFixed(0)} µm`}
                    frac={s.final_radius_um / maxR}
                  />
                  <Metric
                    label="T50"
                    value={t50 ?? "—"}
                    frac={s.t50_min == null ? 0 : s.t50_min / maxT50}
                  />
                </div>
              ) : (
                <p className="condition-pending" role="status">
                  {run ? `run ${run.job.state}…` : "pendiente de run"}
                </p>
              )}
              <div className="condition-actions">
                <button type="button" onClick={() => onRerun(arm.name)} disabled={busy}>
                  Re-ejecutar
                </button>
                <button type="button" onClick={() => onExport(arm.name)} disabled={!run}>
                  Exportar
                </button>
              </div>
            </article>
          );
        })}
      </div>

      {plan && !plan.validated && (
        <p className="copilot-note" role="alert">
          No se pudo planificar: {plan.refusal?.reason ?? "motivo desconocido"}
        </p>
      )}
      {!plan && !planning && (
        <p className="copilot-note">
          Describe tu hipótesis abajo y pulsa → para generar el plan.
        </p>
      )}
    </aside>
  );
}
