import type { ReactNode } from "react";

export type View = "experiment" | "history" | "learn";

interface Props {
  view: View;
  onNav: (view: View) => void;
  /** Extra block between nav and help (e.g. assay params on experiment view). */
  children?: ReactNode;
}

const ITEMS: { id: View; label: string; icon: string }[] = [
  { id: "experiment", label: "Experimentar", icon: "▶" },
  { id: "history", label: "Mis experimentos", icon: "▤" },
  { id: "learn", label: "Aprender", icon: "✎" },
];

export default function Sidebar({ view, onNav, children }: Props) {
  return (
    <aside className="sidebar" aria-label="navegación principal">
      <div className="side-brand">
        <span className="side-logo" aria-hidden="true">
          <i className="b1" />
          <i className="b2" />
          <i className="b3" />
          <i className="b4" />
        </span>
        <span className="side-brand-text">
          <strong>BioSim</strong>
          <small>AI · Biological Simulator</small>
        </span>
      </div>
      <nav aria-label="secciones">
        <ul className="side-nav">
          {ITEMS.map((item) => (
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
          <strong>¿Necesitas ayuda?</strong>
          <span>Solo escribe lo que quieres ver.</span>
        </p>
      </div>
    </aside>
  );
}
