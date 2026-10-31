import { useMemo } from "react";
import { useLocale } from "../i18n";
import { niceCeil } from "./SeriesChart";

const W = 640;
const H = 190;
const PAD = 44;

export interface DosePoint {
  dose: number;
  live: number;
}

interface Props {
  points: DosePoint[];
  selected: number | null;
  onSelect: (dose: number) => void;
}

/**
 * Quantitative dose position: log1p scale so dose 0 (control) stays
 * visible while 0.3 vs 10 keep their real numeric distances.
 * Linear scales crowd low doses; categorical indexes lie about spacing.
 */
export function doseX(dose: number, maxDose: number): number {
  const span = W - PAD - 16;
  if (!(maxDose > 0)) return PAD;
  const t = Math.log1p(Math.max(0, dose)) / Math.log1p(maxDose);
  return PAD + t * span;
}

/** Log-linear IC50: dose where live cells cross 50% of the lowest-dose arm. */
export function ic50(points: DosePoint[]): number | null {
  if (points.length < 2) return null;
  const sorted = [...points].sort((p, q) => p.dose - q.dose);
  const target = sorted[0].live / 2;
  for (let i = 1; i < sorted.length; i++) {
    const a = sorted[i - 1];
    const b = sorted[i];
    if (a.live !== b.live && (a.live - target) * (b.live - target) <= 0) {
      const f = (target - a.live) / (b.live - a.live);
      if (a.dose <= 0) return a.dose + f * (b.dose - a.dose);
      return Math.pow(10, Math.log10(a.dose) + f * (Math.log10(b.dose) - Math.log10(a.dose)));
    }
  }
  return null;
}

export default function DoseChart({ points, selected, onSelect }: Props) {
  const { t } = useLocale();
  const sorted = useMemo(() => [...points].sort((p, q) => p.dose - q.dose), [points]);
  const maxDose = useMemo(() => Math.max(0, ...sorted.map((s) => s.dose)), [sorted]);
  if (sorted.length === 0) return null;
  const maxY = niceCeil(Math.max(1, ...sorted.map((s) => s.live)));
  const x = (dose: number) => doseX(dose, maxDose);
  const y = (v: number) => H - PAD - (v / (maxY * 1.1)) * (H - PAD - 14);
  const line = sorted.map((s) => `${x(s.dose).toFixed(1)},${y(s.live).toFixed(1)}`).join(" ");
  const half = sorted[0].live / 2;
  const ic = ic50(sorted);
  const xIc = ic === null ? 0 : x(ic);
  const xIcLabel = Math.min(Math.max(xIc, PAD + 40), W - 48);
  const fmtTick = (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(1));

  return (
    <div>
      <svg
        className="chart"
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={t("dose.imgAria") + (ic === null ? "" : t("dose.imgAriaIc50", { v: ic.toFixed(2) }))}
      >
        <line x1={PAD} x2={W - 16} y1={y(0)} y2={y(0)} className="grid" />
        <line x1={PAD} x2={W - 16} y1={y(maxY)} y2={y(maxY)} className="grid" />
        <line x1={PAD} x2={W - 16} y1={y(half)} y2={y(half)} className="cursor" strokeDasharray="5 4" />
        <text x={W - 20} y={y(half) - 6} textAnchor="end" className="axis">
          {t("dose.axisHalf")}
        </text>
        <text x={PAD - 6} y={y(maxY) + 4} textAnchor="end" className="axis">
          {maxY}
        </text>
        <text x={PAD - 6} y={y(half) + 4} textAnchor="end" className="axis">
          {fmtTick(half)}
        </text>
        <text x={PAD - 6} y={y(0) + 4} textAnchor="end" className="axis">
          0
        </text>
        <polyline points={line} className="series-live" />
        {ic !== null && (
          <g aria-hidden="true">
            <line x1={xIc} x2={xIc} y1={30} y2={H - PAD} className="ic50-marker" />
            <text x={xIcLabel} y={22} textAnchor="middle" className="ic50-label">
              {t("dose.ic50", { v: ic.toFixed(2) })}
            </text>
          </g>
        )}
        {sorted.map((s) => (
          <g
            key={s.dose}
            role="button"
            tabIndex={0}
            aria-label={t("dose.point", { d: s.dose, live: s.live })}
            aria-pressed={s.dose === selected}
            onClick={() => onSelect(s.dose)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelect(s.dose);
              }
            }}
            style={{ cursor: "pointer" }}
          >
            <circle
              cx={x(s.dose)}
              cy={y(s.live)}
              r={s.dose === selected ? 7 : 5}
              className="cursor-dot-live"
              stroke={s.dose === selected ? "#fff" : "none"}
              strokeWidth={2}
            />
            <text
              x={x(s.dose)}
              y={y(s.live) < 36 ? y(s.live) + 20 : y(s.live) - 12}
              textAnchor="middle"
              className="axis"
            >
              {s.live}
            </text>
            <line x1={x(s.dose)} x2={x(s.dose)} y1={H - 30} y2={H - 24} className="grid" />
            <text x={Math.min(Math.max(x(s.dose), PAD - 10), W - 30)} y={H - 22} textAnchor="middle" className="axis">
              {s.dose} µM
            </text>
          </g>
        ))}
        <text x={W - 20} y={H - 6} textAnchor="end" className="axis">
          {t("dose.axis")}
        </text>
      </svg>
      <p className="ic50">
        {ic === null ? (
          <>
            {t("dose.captionWithout")} <span className="ic50-hint">{t("dose.captionHint")}</span>
          </>
        ) : (
          t("dose.captionWith", { v: ic.toFixed(2) })
        )}
      </p>
      <table className="dose-table" aria-label={t("dose.table")}>
        <thead>
          <tr>
            <th scope="col">dosis (µM)</th>
            <th scope="col">vivas</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((s) => (
            <tr key={s.dose} aria-current={s.dose === selected ? true : undefined}>
              <td>{s.dose}</td>
              <td>{s.live}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
