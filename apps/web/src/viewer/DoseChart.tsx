import { useMemo } from "react";
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

/** Log-linear IC50: dose where live cells cross 50% of the lowest-dose arm. */
export function ic50Position(points: DosePoint[]): { value: number; pos: number } | null {
  if (points.length < 2) return null;
  const target = points[0].live / 2;
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1];
    const b = points[i];
    if (a.live !== b.live && (a.live - target) * (b.live - target) <= 0) {
      const f = (target - a.live) / (b.live - a.live);
      const value =
        a.dose <= 0
          ? a.dose + f * (b.dose - a.dose)
          : Math.pow(10, Math.log10(a.dose) + f * (Math.log10(b.dose) - Math.log10(a.dose)));
      return { value, pos: i - 1 + f };
    }
  }
  return null;
}

/** Log-linear IC50: dose where live cells cross 50% of the lowest-dose arm. */
export function ic50(points: DosePoint[]): number | null {
  return ic50Position(points)?.value ?? null;
}

export default function DoseChart({ points, selected, onSelect }: Props) {
  const sorted = useMemo(() => [...points].sort((p, q) => p.dose - q.dose), [points]);
  if (sorted.length === 0) return null;
  const maxY = niceCeil(Math.max(1, ...sorted.map((s) => s.live)));
  const n = sorted.length;
  const x = (i: number) => (n === 1 ? W / 2 : PAD + (i / (n - 1)) * (W - PAD - 16));
  const y = (v: number) => H - PAD - (v / (maxY * 1.1)) * (H - PAD - 14);
  const line = sorted.map((s, i) => `${x(i).toFixed(1)},${y(s.live).toFixed(1)}`).join(" ");
  const half = sorted[0].live / 2;
  const icPos = ic50Position(sorted);
  const ic = icPos?.value ?? null;
  const fmtTick = (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(1));
  const xIc = icPos === null ? 0 : x(icPos.pos);
  const xIcLabel = Math.min(Math.max(xIc, PAD + 40), W - 48);

  return (
    <div>
      <svg
        className="chart"
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`final live cells versus drug dose in µM (click a point to view)${
          ic === null ? "" : `, IC50 aprox ${ic.toFixed(2)} µM`
        }`}
      >
        <line x1={PAD} x2={W - 16} y1={y(0)} y2={y(0)} className="grid" />
        <line x1={PAD} x2={W - 16} y1={y(maxY)} y2={y(maxY)} className="grid" />
        <line x1={PAD} x2={W - 16} y1={y(half)} y2={y(half)} className="cursor" strokeDasharray="5 4" />
        <text x={W - 20} y={y(half) - 6} textAnchor="end" className="axis">
          50% of control
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
        {icPos !== null && (
          <g aria-hidden="true">
            <line x1={xIc} x2={xIc} y1={30} y2={H - PAD} className="ic50-marker" />
            <text x={xIcLabel} y={22} textAnchor="middle" className="ic50-label">
              IC50 ≈ {icPos.value.toFixed(2)} µM
            </text>
          </g>
        )}
        {sorted.map((s, i) => (
          <g
            key={s.dose}
            role="button"
            tabIndex={0}
            aria-label={`show dose ${s.dose} µM, ${s.live} live cells`}
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
              cx={x(i)}
              cy={y(s.live)}
              r={s.dose === selected ? 7 : 5}
              className="cursor-dot-live"
              stroke={s.dose === selected ? "#fff" : "none"}
              strokeWidth={2}
            />
            <text
              x={x(i)}
              y={y(s.live) < 36 ? y(s.live) + 20 : y(s.live) - 12}
              textAnchor="middle"
              className="axis"
            >
              {s.live}
            </text>
            <line x1={x(i)} x2={x(i)} y1={H - 30} y2={H - 24} className="grid" />
            <text x={x(i)} y={H - 22} textAnchor="middle" className="axis">
              {s.dose} µM
            </text>
          </g>
        ))}
        <text x={W - 20} y={H - 6} textAnchor="end" className="axis">
          drug dose (µM)
        </text>
      </svg>
      <p className="ic50">
        {ic === null ? (
          <>
            IC50 <span className="ic50-hint">not bracketed — widen the ladder</span>
          </>
        ) : (
          `IC50 aprox ${ic.toFixed(2)} µM · assay-scale, not clinical`
        )}
      </p>
    </div>
  );
}
