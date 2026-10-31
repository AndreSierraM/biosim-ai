import { tFor } from "./i18n";
import type { Locale } from "./i18n";
import type { TrajectorySummary } from "./types";

export interface ConclusionArm {
  /** Short display name, e.g. "Condición 1 · Oxígeno 38 mmHg". */
  label: string;
  summary: TrajectorySummary;
}

function fmtInt(n: number, locale: Locale): string {
  return n.toLocaleString(locale === "es" ? "es-ES" : "en-US");
}

/** Honest duration label from minutes; null stays null (never invented). */
export function fmtT50(t50min: number | null | undefined): string | null {
  if (t50min === null || t50min === undefined || !Number.isFinite(t50min)) return null;
  if (t50min >= 1440) return `${(t50min / 1440).toFixed(2)} d`;
  if (t50min >= 120) return `${(t50min / 60).toFixed(1)} h`;
  return `${t50min.toFixed(0)} min`;
}

function deadFraction(s: TrajectorySummary): number {
  if (typeof s.final_dead_fraction === "number") return s.final_dead_fraction;
  const total = s.final_live + s.final_dead;
  return total > 0 ? s.final_dead / total : 0;
}

/**
 * Rule-based conclusion from REAL run summaries. Pure function of numbers the
 * engines computed — it never calls the LLM and never invents values. With a
 * single arm it describes; with two it compares. Language follows locale.
 */
export function buildConclusion(arms: ConclusionArm[], locale: Locale = "es"): string | null {
  const t = (key: Parameters<typeof tFor>[1], vars?: Record<string, string | number>) =>
    tFor(locale, key, vars);
  const done = arms.filter((a) => a.summary.n_frames > 0);
  if (done.length === 0) return null;
  if (done.length === 1) {
    const [a] = done;
    const s = a.summary;
    const t50 = fmtT50(s.t50_min);
    return (
      t("concl.single", {
        label: a.label,
        live: fmtInt(s.final_live, locale),
        dead: fmtInt(s.final_dead, locale),
        r: s.final_radius_um.toFixed(0),
      }) + (t50 ? t("concl.singleT50", { t: t50 }) : t("concl.singleNoT50"))
    );
  }
  const [a, b] = done;
  const sa = a.summary;
  const sb = b.summary;
  const parts: string[] = [];
  const dLive = sb.final_live - sa.final_live;
  if (dLive === 0) {
    parts.push(t("concl.equal", { n: fmtInt(sa.final_live, locale) }));
  } else {
    const high = dLive > 0 ? b : a;
    const low = dLive > 0 ? a : b;
    const hi = dLive > 0 ? sb.final_live : sa.final_live;
    const lo = dLive > 0 ? sa.final_live : sb.final_live;
    if (lo === 0) {
      parts.push(
        t("concl.zero", { low: low.label, hi: fmtInt(hi, locale), high: high.label }),
      );
    } else {
      const pctLess = Math.round((((hi - lo) / hi) * 100) * 10) / 10;
      const pctText = Number.isInteger(pctLess) ? String(pctLess) : pctLess.toFixed(1);
      parts.push(
        t("concl.less", {
          low: low.label,
          pct: pctText,
          high: high.label,
          lo: fmtInt(lo, locale),
          hi: fmtInt(hi, locale),
        }),
      );
    }
  }
  const fa = deadFraction(sa);
  const fb = deadFraction(sb);
  if (Math.abs(fa - fb) >= 0.01) {
    const higher = fb > fa ? b : a;
    const [hi, lo] = fb > fa ? [fb, fa] : [fa, fb];
    parts.push(
      t("concl.deadFrac", {
        label: higher.label,
        a: (hi * 100).toFixed(0),
        b: (lo * 100).toFixed(0),
      }),
    );
  } else {
    parts.push(t("concl.deadSimilar", { p: (fa * 100).toFixed(0) }));
  }
  const dr = sb.final_radius_um - sa.final_radius_um;
  if (Math.abs(dr) >= 1) {
    const bigger = dr > 0 ? b : a;
    const [hi, lo] = dr > 0 ? [sb.final_radius_um, sa.final_radius_um] : [sa.final_radius_um, sb.final_radius_um];
    parts.push(
      t("concl.radius", { label: bigger.label, a: hi.toFixed(0), b: lo.toFixed(0) }),
    );
  } else {
    parts.push(t("concl.radiusSimilar", { r: sa.final_radius_um.toFixed(0) }));
  }
  const ta = fmtT50(sa.t50_min);
  const tb = fmtT50(sb.t50_min);
  let t50bit = "";
  if (ta && tb) {
    t50bit = t("concl.t50both", { ta, la: a.label, tb, lb: b.label });
  } else if (ta || tb) {
    const which = ta ? a : b;
    t50bit = t("concl.prolif", { label: which.label, t: ta ?? tb ?? "" });
  } else {
    t50bit = t("concl.prolifNone");
  }
  const first = parts[0].charAt(0).toUpperCase() + parts[0].slice(1);
  return `${first}; ${parts.slice(1).join("; ")}.${t50bit}`;
}
