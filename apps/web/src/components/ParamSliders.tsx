export interface SliderValues {
  oxygen: number;
  drug: number;
  cells: number;
}

interface Props {
  values: SliderValues;
  onChange: (values: SliderValues) => void;
  disabled: boolean;
  /** Per-slider lock reason (plan-owned experimental variable), or null. */
  locks: Record<keyof SliderValues, string | null>;
}

const SLIDERS = [
  {
    key: "oxygen" as const,
    name: "Oxígeno",
    unit: "mmHg",
    min: 0,
    max: 100,
    step: 1,
    fmt: (v: number) => `${v.toFixed(0)} mmHg`,
  },
  {
    key: "drug" as const,
    name: "Medicamento",
    unit: "µM",
    min: 0,
    max: 10,
    step: 0.1,
    fmt: (v: number) => `${v.toFixed(1)} µM`,
  },
  {
    key: "cells" as const,
    name: "Tamaño inicial",
    unit: "células",
    min: 4,
    max: 40,
    step: 1,
    fmt: (v: number) => `${v.toFixed(0)} células`,
  },
];

/**
 * Assay parameters. They override the matching PhysiCell keys
 * (oxygen, drug_dose, initial_cells) on the next run of each arm.
 */
export default function ParamSliders({ values, onChange, disabled, locks }: Props) {
  return (
    <section className="params-card" aria-label="parámetros del ensayo">
      <div className="params-head">
        <h2>Parámetros</h2>
        <p>Se aplican a ambas condiciones en la próxima simulación. La variable del experimento la define el plan.</p>
      </div>
      <div className="params-grid">
        {SLIDERS.map((s) => {
          const lock = locks[s.key];
          return (
            <div key={s.key} className={lock ? "param is-locked" : "param"}>
              <div className="param-top">
                <label htmlFor={`param-${s.key}`}>{s.name}</label>
                <output htmlFor={`param-${s.key}`} aria-live="off">
                  {s.fmt(values[s.key])}
                </output>
              </div>
              <input
                id={`param-${s.key}`}
                type="range"
                min={s.min}
                max={s.max}
                step={s.step}
                value={values[s.key]}
                disabled={disabled || lock !== null}
                title={lock ?? undefined}
                onChange={(e) =>
                  onChange({ ...values, [s.key]: Number(e.target.value) })
                }
                aria-valuetext={s.fmt(values[s.key])}
                aria-describedby={lock ? `param-${s.key}-lock` : undefined}
              />
              {lock && (
                <p className="param-lock" id={`param-${s.key}-lock`}>
                  {lock}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
