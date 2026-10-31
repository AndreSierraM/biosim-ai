import { useLocale } from "../i18n";
import type { Locale } from "../i18n";
import { tFor } from "../i18n";
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

function nameOf(locale: Locale, key: string): string {
  const namespaced = `sub.${key}`;
  const hit = tFor(locale, namespaced as never);
  return hit === namespaced ? key.replace(/_/g, " ") : hit;
}

/** Short honest subtitle from the arm's planned parameters. */
export function armSubtitle(
  plan: Plan | null,
  armName: string,
  locale: Locale = "es",
): string {
  const arm = plan?.arms.find((a) => a.name === armName);
  if (!arm) return armName;
  const bits = Object.entries(arm.spec.parameters).map(
    ([k, q]) => `${nameOf(locale, k)} ${q.value} ${fmtUnit(q.unit)}`,
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
  const { t, locale } = useLocale();
  const num = (v: number) => v.toLocaleString(locale === "es" ? "es-ES" : "en-US");
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
    { state: step1, label: t("co.step1") },
    { state: step2, label: t("co.step2") },
    { state: step3, label: allDone ? t("co.step3") : t("co.step3run") },
  ];

  return (
    <aside className="copilot" aria-label="BioSim AI">
      <h2 className="copilot-title">
        <span className="copilot-spark" aria-hidden="true">
          ✦
        </span>
        {t("co.title")}
      </h2>

      <ol className="checklist" aria-label={t("co.progress")}>
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
        {t("co.results")}
      </h3>
      {plan !== null || trajs.length > 0 ? (
        <p className="results-sub">
          {trajs.length > 0
            ? t("co.wait")
            : t("co.planCta")}
        </p>
      ) : null}

      {plan?.validated && (
        <button
          type="button"
          className="run-all"
          onClick={onRunAll}
          disabled={busy}
        >
          {anyRunning ? t("co.step3run") : trajs.length > 0 ? t("plan.rerunAll") : t("plan.runAll")}
        </button>
      )}

      <div className="conditions">
        {arms.map((arm, i) => {
          const run = runs[arm.name];
          const traj = run?.traj ?? null;
          const s = traj?.summary ?? null;
          const t50 = s ? fmtT50(s.t50_min) : null;
          const job = run?.job ?? null;
          return (
            <article
              key={arm.name}
              className={i === 0 ? "condition is-a" : "condition is-b"}
              aria-label={t("co.condition", { i: i + 1 })}
            >
              <h4>{t("co.condition", { i: i + 1 })}</h4>
              <p className="condition-sub">{subtitleFor(arm.name)}</p>
              {s ? (
                <div className="metrics">
                  <Metric label={t("co.vivas")} value={num(s.final_live)} frac={s.final_live / maxLive} />
                  <Metric label={t("co.muertas")} value={num(s.final_dead)} frac={s.final_dead / maxDead} />
                  <Metric
                    label={t("co.radio")}
                    value={`${s.final_radius_um.toFixed(0)} µm`}
                    frac={s.final_radius_um / maxR}
                  />
                  <Metric
                    label={t("co.t50")}
                    value={t50 ?? "—"}
                    frac={s.t50_min == null ? 0 : s.t50_min / maxT50}
                  />
                </div>
              ) : (
                <p className="condition-pending" role="status">
                  {run ? t("co.running", { state: run.job.state }) : t("co.pending")}
                </p>
              )}
              <div className="condition-actions">
                <button type="button" onClick={() => onRerun(arm.name)} disabled={busy}>
                  {t("co.rerun")}
                </button>
                <button type="button" onClick={() => onExport(arm.name)} disabled={!run}>
                  {t("co.export")}
                </button>
              </div>
              {job && (
                <details className="provenance">
                  <summary>{t("co.evidence")}</summary>
                  <dl>
                    <dt>{t("co.evRun")}</dt>
                    <dd title={job.id}>{job.id.slice(0, 8)}</dd>
                    <dt>{t("co.evEngine")}</dt>
                    <dd>{job.engine} v{job.engine_version ?? "?"}</dd>
                    <dt>{t("co.evSeed")}</dt>
                    <dd>{job.seed}</dd>
                    {job.artifact_digest && (
                      <>
                        <dt>{t("co.evDigest")}</dt>
                        <dd title={job.artifact_digest}>{job.artifact_digest.slice(0, 19)}…</dd>
                      </>
                    )}
                  </dl>
                  <p className="provenance-note">
                    {t("co.evNote")}
                  </p>
                </details>
              )}
            </article>
          );
        })}
      </div>

      {plan && !plan.validated && (
        <p className="copilot-note" role="alert">
          {t("plan.refusedTitle")}: {plan.refusal?.reason ?? "?"}
        </p>
      )}
      {!plan && !planning && (
        <p className="copilot-note">
          {t("co.wait")}
        </p>
      )}
    </aside>
  );
}
