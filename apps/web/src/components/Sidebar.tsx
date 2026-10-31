import type { ReactNode } from "react";
import { useLocale } from "../i18n";

export type View = "experiment" | "history" | "learn";

interface Props {
  view: View;
  onNav: (view: View) => void;
  /** Extra block between nav and help (e.g. assay params on experiment view). */
  children?: ReactNode;
}

function items(t: (key: "nav.experiment" | "nav.history" | "nav.learn") => string) {
  return [
    { id: "experiment", label: t("nav.experiment"), icon: "▶" },
    { id: "history", label: t("nav.history"), icon: "▤" },
    { id: "learn", label: t("nav.learn"), icon: "✎" },
  ] as const;
}

export default function Sidebar({ view, onNav, children }: Props) {
  const { t } = useLocale();
  return (
    <aside className="sidebar" aria-label={t("nav.main")}>
      <div className="side-brand">
        <span className="side-logo" aria-hidden="true">
          <i className="b1" />
          <i className="b2" />
          <i className="b3" />
          <i className="b4" />
        </span>
        <span className="side-brand-text">
          <strong>BioSim</strong>
          <small>{t("brand.sub")}</small>
        </span>
      </div>
      <nav aria-label={t("nav.main")}>
        <ul className="side-nav">
          {items(t).map((item) => (
            <li key={item.id}>
              <button
                type="button"
                className={view === item.id ? "side-link is-active" : "side-link"}
                aria-current={view === item.id ? "page" : undefined}
                onClick={() => onNav(item.id)}
              >
                <span className="side-icon" aria-hidden="true">
                  {item.icon}
                </span>
                {item.label}
              </button>
            </li>
          ))}
        </ul>
      </nav>
      {children}
      <div className="side-help">
        <span className="side-help-face" aria-hidden="true">
          ?
        </span>
        <p>
          <strong>{t("help.title")}</strong>
          <span>{t("help.text")}</span>
        </p>
      </div>
    </aside>
  );
}
