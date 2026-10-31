import { useLocale } from "../i18n";

export interface ExampleChip {
  label: string;
  prompt: string;
  /** Inline SVG path (24x24, stroke) shown before the label. */
  icon: string;
}

/** Chip icons stay constant; labels/prompts come from the locale dict. */
const CHIP_ICONS = [
  "M7 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm10 0a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
  "M10.5 4.5l9 9a4.24 4.24 0 0 1-6 6l-9-9a4.24 4.24 0 0 1 6-6zM8 8l8 8",
  "M12 2l8 4.5v9L12 20l-8-4.5v-9L12 2zm0 0v9m8-4.5L12 11M4 6.5L12 11",
  "M3 8h11a3 3 0 1 0-3-3M3 12h16a3 3 0 1 1-3 3M3 16h8",
] as const;

type ChipBase = "oxygen" | "drug" | "tumor" | "less";
const CHIP_BASES: ChipBase[] = ["oxygen", "drug", "tumor", "less"];

type ChipLabelKey =
  | "chip.oxygen.label"
  | "chip.drug.label"
  | "chip.tumor.label"
  | "chip.less.label";
type ChipPromptKey =
  | "chip.oxygen.prompt"
  | "chip.drug.prompt"
  | "chip.tumor.prompt"
  | "chip.less.prompt";

function exampleChips(
  t: (key: ChipLabelKey | ChipPromptKey) => string,
): ExampleChip[] {
  return CHIP_BASES.map((base, i) => ({
    label: t(`chip.${base}.label` as ChipLabelKey),
    prompt: t(`chip.${base}.prompt` as ChipPromptKey),
    icon: CHIP_ICONS[i],
  }));
}

interface Props {
  prompt: string;
  onPromptChange: (value: string) => void;
  onPlan: () => void;
  planning: boolean;
  busy: boolean;
}

export default function PromptBar({ prompt, onPromptChange, onPlan, planning, busy }: Props) {
  const { t } = useLocale();
  const empty = prompt.trim().length === 0;
  return (
    <section className="prompt-block" aria-label={t("feed.promptBlock")}>
      <form
        className="prompt-pill"
        onSubmit={(e) => {
          e.preventDefault();
          onPlan();
        }}
      >
        <label className="visually-hidden" htmlFor="prompt-input">
          {t("feed.promptLabel")}
        </label>
        <input
          id="prompt-input"
          className="prompt-input"
          type="text"
          value={prompt}
          onChange={(e) => onPromptChange(e.target.value)}
          placeholder={t("feed.promptPlaceholder")}
          autoComplete="off"
        />
        <button
          type="submit"
          className="prompt-go"
          disabled={busy || empty}
          aria-label={t("feed.promptSend")}
          title={t("feed.promptSend")}
        >
          <span aria-hidden="true">{planning ? "…" : "→"}</span>
        </button>
      </form>
      <div className="prompt-chips" role="group" aria-label={t("feed.examples")}>
        {exampleChips(t).map((chip) => (
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
