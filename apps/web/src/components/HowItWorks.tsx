import { useEffect, useRef } from "react";
import { useLocale } from "../i18n";

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function HowItWorks({ open, onClose }: Props) {
  const { t } = useLocale();
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
        <h2 id="how-title">{t("how.title")}</h2>
        <ol>
          <li>{t("how.step1")}</li>
          <li>{t("how.step2")}</li>
          <li>{t("how.step3")}</li>
          <li>{t("how.step4")}</li>
        </ol>
        <button ref={closeRef} type="button" className="modal-close" onClick={onClose}>
          {t("how.close")}
        </button>
      </div>
    </div>
  );
}
