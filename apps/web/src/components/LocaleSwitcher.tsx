import { useLocale } from "../i18n";
import type { Locale } from "../i18n";

export default function LocaleSwitcher() {
  const { locale, setLocale, t } = useLocale();
  const pick = (l: Locale) => (e: React.MouseEvent) => {
    e.preventDefault();
    if (l !== locale) setLocale(l);
  };
  return (
    <div className="locale-switch" role="group" aria-label={t("locale.label")}>
      {(["es", "en"] as const).map((l) => (
        <button
          key={l}
          type="button"
          className={l === locale ? "on" : ""}
          aria-pressed={l === locale}
          onClick={pick(l)}
        >
          {l === "es" ? "ES" : "EN"}
        </button>
      ))}
    </div>
  );
}
