import { useMemo } from "react";
import type { TrajectoryFile } from "../types";

const W = 640;
const H = 150;
const PAD = 34;

/** Round a y-axis ceiling to 1/2/2.5/5·10ⁿ so ticks read clean (data untouched). */
export function niceCeil(v: number): number {
  if (v <= 0) return 1;
  const p = 10 ** Math.floor(Math.log10(v));
  for (const m of [1, 2, 2.5, 5, 10]) if (m * p >= v) return m * p;
  return 10 * p;
}

interface Props {
  data: TrajectoryFile;
  frame: number;
  onSeek: (frame: number) => void;
  /** Shared y ceiling so arms can use one scale; defaults to this arm's max. */
  yMax?: number;
}

export default function SeriesChart({ data, frame, onSeek, yMax }: Props) {
  const n = data.frames.length;
  const maxT = data.meta.duration_min;
  const safeMaxT = Number.isFinite(maxT) && maxT > 0 ? maxT : 1;
  const useDays = maxT >= 1440;
  const series = useMemo(
    () =>
      data.frames.map((f) => {
        const live = f.cells.filter((c) => !c.dead).length;
        return { t: f.t_min, live, dead: f.cells.length - live };
      }),
    [data],
  );
  const dataMax = Math.max(1, ...series.map((s) => s.live + s.dead));
  const maxY = niceCeil(Math.max(1, yMax ?? dataMax));
  const x = (t: number) => PAD + (t / safeMaxT) * (W - PAD - 12);
  const y = (v: number) => H - PAD - (v / (maxY * 1.05)) * (H - PAD - 10);
  const line = (pick: (s: (typeof series)[number]) => number) =>
    series.map((s) => `${x(s.t).toFixed(1)},${y(pick(s)).toFixed(1)}`).join(" ");
  const fmtT = (t: number) => (useDays ? `${(t / 1440).toFixed(1)}d` : `${t.toFixed(0)}`);
  const fmtY = (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(1));
  const safeFrame = n > 0 ? Math.min(Math.max(0, frame), n - 1) : 0;
  const cur = series[safeFrame] ?? { t: 0, live: 0, dead: 0 };
  const valueText =
    n === 0
      ? "no frames"
      : `frame ${safeFrame + 1} of ${n}, t ${fmtT(cur.t)}${useDays ? "" : " min"}, ${cur.live} live, ${cur.dead} dead`;

  return (
    <svg
      className="chart"
      viewBox={`0 0 ${W} ${H}`}
      role="slider"
      tabIndex={0}
      aria-label="living and dead cell counts over time (click or press arrows, Enter, Space to seek)"
      aria-valuemin={0}
      aria-valuemax={Math.max(0, n - 1)}
      aria-valuenow={safeFrame}
      aria-valuetext={valueText}
      onClick={(e) => {
        if (n <= 0) return;
        const rect = e.currentTarget.getBoundingClientRect();
        const px = ((e.clientX - rect.left) / rect.width) * W;
        const t = ((px - PAD) / (W - PAD - 12)) * safeMaxT;
        onSeek(Math.min(n - 1, Math.max(0, Math.round((t / safeMaxT) * (n - 1)))));
      }}
      onKeyDown={(e) => {
        if (n <= 0) return;
        const stepKeys = ["ArrowRight", "ArrowUp", "Enter", " ", "Spacebar"];
        if (stepKeys.includes(e.key)) {
          e.preventDefault();
          onSeek(Math.min(n - 1, safeFrame + 1));
        } else if (e.key === "ArrowLeft" || e.key === "ArrowDown") {
          e.preventDefault();
          onSeek(Math.max(0, safeFrame - 1));
        } else if (e.key === "Home") {
          e.preventDefault();
          onSeek(0);
        } else if (e.key === "End") {
          e.preventDefault();
          onSeek(n - 1);
        } else if (e.key === "PageUp") {
          e.preventDefault();
          onSeek(Math.min(n - 1, safeFrame + 10));
        } else if (e.key === "PageDown") {
          e.preventDefault();
          onSeek(Math.max(0, safeFrame - 10));
        }
      }}
    >
      {[0, maxY / 2, maxY].map((v) => (
        <line key={v} x1={PAD} x2={W - 12} y1={y(v)} y2={y(v)} className="grid" />
      ))}
      <polyline points={line((s) => s.live)} className="series-live" />
      <polyline points={line((s) => s.dead)} className="series-dead" />
      <line x1={x(cur.t)} y1={8} x2={x(cur.t)} y2={H - PAD} className="cursor" />
      <circle cx={x(cur.t)} cy={y(cur.live)} r={4} className="cursor-dot-live" />
      <circle cx={x(cur.t)} cy={y(cur.dead)} r={4} className="cursor-dot-dead" />
      <text x={PAD} y={H - 8} className="axis">
        0
      </text>
      <text x={x(maxT / 2)} y={H - 8} textAnchor="middle" className="axis">
        {fmtT(maxT / 2)}
      </text>
      <text x={W - 12} y={H - 8} className="axis end">
        {fmtT(maxT)} {useDays ? "" : "min"}
      </text>
      <text x={PAD} y={y(maxY) + 4} className="axis">
        {fmtY(maxY)}
      </text>
      <text x={PAD} y={y(maxY / 2) + 4} className="axis">
        {fmtY(maxY / 2)}
      </text>
    </svg>
  );
}
