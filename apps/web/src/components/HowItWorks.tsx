import { useEffect, useRef } from "react";

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function HowItWorks({ open, onClose }: Props) {
  const closeRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="how-title"
      >
        <h2 id="how-title">Cómo funciona</h2>
        <ol>
          <li>
            <strong>Describe.</strong> Escribes tu hipótesis con tus palabras.
          </li>
          <li>
            <strong>La IA planifica.</strong> El planificador propone dos condiciones
            comparables (mismo motor, misma semilla).
          </li>
          <li>
            <strong>El motor calcula.</strong> PhysiCell simula cada célula como
            agente: posiciones reales, nada inventado.
          </li>
          <li>
            <strong>Comparas.</strong> Métricas y conclusión salen de los
            resúmenes calculados, nunca del chat.
          </li>
        </ol>
        <button ref={closeRef} type="button" className="modal-close" onClick={onClose}>
          Entendido
        </button>
      </div>
    </div>
  );
}
