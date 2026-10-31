import type { CellPosition, TrajectoryFile } from "./types";

/** Honest label for the golden preview shown before the first run. */
export const PREVIEW_LABEL = "Preview · physicell v1.14.2 · seed 7";

interface GoldenFrame {
  t_min: number;
  cells: CellPosition[];
}

interface GoldenFixture {
  frames: GoldenFrame[];
  params: Record<string, number>;
  seed: number;
  summary: TrajectoryFile["summary"];
}

/**
 * Loads the golden preview spheroid shipped in public/. The fixture stores
 * raw frames/params/seed/summary; this adapts it into a TrajectoryFile so the
 * existing CellViewer renders real computed positions (never invented).
 */
export async function loadPreviewSpheroid(signal?: AbortSignal): Promise<TrajectoryFile> {
  const res = await fetch(`${import.meta.env.BASE_URL}preview-spheroid.json`, { signal });
  if (!res.ok) {
    throw new Error(`preview-spheroid.json: HTTP ${res.status}`);
  }
  const g = (await res.json()) as GoldenFixture;
  const lastT = g.frames.length > 0 ? g.frames[g.frames.length - 1].t_min : 0;
  const frameEvery = g.frames.length > 1 ? lastT / (g.frames.length - 1) : 1;
  return {
    meta: {
      engine_id: "physicell",
      engine_version: "1.14.2",
      seed: g.seed,
      units: { length: "um", time: "min" },
      dt_min: 0.1,
      duration_min: lastT,
      frame_every: frameEvery,
      params: { ...g.params },
      assumptions: [
        "Golden preview trajectory (physicell v1.14.2, seed 7). Run to compute yours.",
      ],
    },
    frames: g.frames.map((f) => ({ t_min: f.t_min, contact: false, cells: f.cells })),
    summary: g.summary,
  };
}
