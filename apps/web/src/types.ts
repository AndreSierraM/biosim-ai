export interface CellPosition {
  id: string;
  x_um: number;
  y_um: number;
  z_um: number;
  dead?: boolean;
}

export interface TrajectoryFrame {
  t_min: number;
  contact?: boolean;
  cells: CellPosition[];
}

export interface TrajectoryMeta {
  engine_id: string;
  engine_version: string;
  seed: number;
  units: { length: string; time: string };
  dt_min: number;
  duration_min: number;
  frame_every: number;
  /** PhysiCell spheroid params (oxygen, drug_dose, ...); shape follows the engine manifest. */
  params: Record<string, number>;
  assumptions: string[];
}

export interface TrajectorySummary {
  n_frames: number;
  initial_cells: number;
  final_live: number;
  final_dead: number;
  final_radius_um: number;
  /** Extra metrics merged by worker.metrics.summarize_frames (absent in older runs). */
  final_live_fraction?: number;
  final_dead_fraction?: number;
  /** First t_min past the live peak where live <= half max; null when never. */
  t50_min?: number | null;
  peak_live?: number;
  peak_live_t_min?: number | null;
}

export interface TrajectoryFile {
  meta: TrajectoryMeta;
  frames: TrajectoryFrame[];
  summary: TrajectorySummary;
}

export interface Quantity {
  value: number;
  unit: string;
}

export interface PlanSpec {
  intent: string;
  engine: string;
  seed: number;
  parameters: Record<string, Quantity>;
}

export interface PlanArm {
  name: string;
  spec: PlanSpec;
}

export interface PlanProvenance {
  model_version: string | null;
  request_id: string | null;
  tokens_in: number | null;
  tokens_out: number | null;
  latency_s: number;
  prompt_template: string;
  schema_version: string;
}

export interface Plan {
  validated: boolean;
  arms: PlanArm[];
  model_version: string | null;
  warnings: string[];
  refusal: { reason: string } | null;
  runs_created: string[];
  planner_backend?: "fixture" | "live";
  provenance?: PlanProvenance;
}

export interface Job {
  id: string;
  state: string;
  engine: string;
  params: Record<string, number>;
  seed: number;
  error: string | null;
  summary: TrajectorySummary | null;
}

export interface EngineInfo {
  engine_id: string;
  engine_version: string | null;
  available: boolean;
  reason: string;
}
