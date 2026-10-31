import { useLocale } from "../i18n";

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

/**
 * Assay parameters. They override the matching PhysiCell keys
 * (oxygen, drug_dose, initial_cells) on the next run of each arm.
 */
export default function ParamSliders({ values, onChange, disabled, locks }: Props) {
  const { t } = useLocale();
  const unitCells = t("params.unitCells");
  const sliders = [
    { key: "oxygen" as const, name: t("params.oxygen"), min: 0, max: 100, step: 1,
      fmt: (v: number) => `${v.toFixed(0)} mmHg` },
    { key: "drug" as const, name: t("params.drug"), min: 0, max: 10, step: 0.1,
      fmt: (v: number) => `${v.toFixed(1)} µM` },
    { key: "cells" as const, name: t("params.cells"), min: 4, max: 40, step: 1,
      fmt: (v: number) => `${v.toFixed(0)} ${unitCells}` },
  ];
  return (
    <section className="params-card" aria-label={t("params.title")}>
      <div className="params-head">
        <h2>{t("params.title")}</h2>
        <p>{t("params.desc")}</p>
      </div>
      <div className="params-grid">
        {sliders.map((s) => {
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
