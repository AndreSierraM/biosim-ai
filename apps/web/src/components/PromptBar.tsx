export interface ExampleChip {
  label: string;
  prompt: string;
  /** Inline SVG path (24x24, stroke) shown before the label. */
  icon: string;
}

/** Chips fill the prompt; prompts carry the fixture keywords so planning works. */
export const EXAMPLE_CHIPS: ExampleChip[] = [
  {
    label: "Dos condiciones de oxígeno",
    prompt: "Compara oxygen availability normal vs baja en el esferoide tumoral",
    icon: "M7 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm10 0a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
  },
  {
    label: "Efecto de un medicamento",
    prompt: "¿Qué drug dose frena el crecimiento del tumor?",
    icon: "M10.5 4.5l9 9a4.24 4.24 0 0 1-6 6l-9-9a4.24 4.24 0 0 1 6-6zM8 8l8 8",
  },
  {
    label: "Un tumor en 3D",
    prompt: "Muestra el esferoide en 3D con oxygen availability normal vs baja",
    icon: "M12 2l8 4.5v9L12 20l-8-4.5v-9L12 2zm0 0v9m8-4.5L12 11M4 6.5L12 11",
  },
  {
    label: "Menos oxígeno",
    prompt: "¿Crece menos el tumor con menos oxígeno? oxygen availability baja vs normal",
    icon: "M3 8h11a3 3 0 1 0-3-3M3 12h16a3 3 0 1 1-3 3M3 16h8",
  },
];

interface Props {
  prompt: string;
  onPromptChange: (value: string) => void;
  onPlan: () => void;
  planning: boolean;
  busy: boolean;
}

export default function PromptBar({ prompt, onPromptChange, onPlan, planning, busy }: Props) {
  const empty = prompt.trim().length === 0;
  return (
    <section className="prompt-block" aria-label="describe tu experimento">
      <form
        className="prompt-pill"
        onSubmit={(e) => {
          e.preventDefault();
          onPlan();
        }}
      >
        <label className="visually-hidden" htmlFor="prompt-input">
          Describe tu hipótesis
        </label>
        <input
          id="prompt-input"
          className="prompt-input"
          type="text"
          value={prompt}
          onChange={(e) => onPromptChange(e.target.value)}
          placeholder="¿Qué pasa si hay menos oxígeno?"
          autoComplete="off"
        />
        <button
          type="submit"
          className="prompt-go"
          disabled={busy || empty}
          aria-label={planning ? "Planificando…" : "Generar plan"}
          title="Generar plan"
        >
          <span aria-hidden="true">{planning ? "…" : "→"}</span>
        </button>
      </form>
      <div className="prompt-chips" role="group" aria-label="ejemplos">
        {EXAMPLE_CHIPS.map((chip) => (
          <button
            key={chip.label}
            type="button"
            className="chip"
            onClick={() => onPromptChange(chip.prompt)}
            disabled={busy}
          >
            <svg
              className="chip-icon"
              viewBox="0 0 24 24"
              width="15"
              height="15"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d={chip.icon} />
            </svg>
            {chip.label}
          </button>
        ))}
      </div>
    </section>
  );
}
