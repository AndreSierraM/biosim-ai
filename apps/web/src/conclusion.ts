import type { TrajectorySummary } from "./types";

export interface ConclusionArm {
  /** Short display name, e.g. "Condición 1 · Oxígeno 38 mmHg". */
  label: string;
  summary: TrajectorySummary;
}

function fmtInt(n: number): string {
  return n.toLocaleString("es-ES");
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
 * single arm it describes; with two it compares.
 */
export function buildConclusion(arms: ConclusionArm[]): string | null {
  const done = arms.filter((a) => a.summary.n_frames > 0);
  if (done.length === 0) return null;
  if (done.length === 1) {
    const [a] = done;
    const s = a.summary;
    const t50 = fmtT50(s.t50_min);
    return (
      `${a.label} terminó con ${fmtInt(s.final_live)} células vivas y ` +
      `${fmtInt(s.final_dead)} muertas (radio ${s.final_radius_um.toFixed(0)} µm).` +
      (t50
        ? ` La población cayó a la mitad de su pico a los ${t50} (t50).`
        : ` La población nunca cayó a la mitad de su pico: el esferoide siguió creciendo.`)
    );
  }
  const [a, b] = done;
  const sa = a.summary;
  const sb = b.summary;
  const parts: string[] = [];
  const dLive = sb.final_live - sa.final_live;
  if (dLive === 0) {
    parts.push(
      `ambas condiciones terminaron con ${fmtInt(sa.final_live)} células vivas`,
    );
  } else {
    const high = dLive > 0 ? b : a;
    const low = dLive > 0 ? a : b;
    const hi = dLive > 0 ? sb.final_live : sa.final_live;
    const lo = dLive > 0 ? sa.final_live : sb.final_live;
    if (lo === 0) {
      parts.push(
        `${low.label} terminó sin células vivas frente a ` +
          `${fmtInt(hi)} de ${high.label} en esta simulación`,
      );
    } else {
      const pctLess = Math.round((((hi - lo) / hi) * 100) * 10) / 10;
      const pctText = Number.isInteger(pctLess) ? String(pctLess) : pctLess.toFixed(1);
      parts.push(
        `${low.label} terminó con un ${pctText} % menos de células vivas que ` +
          `${high.label} (${fmtInt(lo)} frente a ${fmtInt(hi)}, en esta simulación)`,
      );
    }
  }
  const fa = deadFraction(sa);
  const fb = deadFraction(sb);
  if (Math.abs(fa - fb) >= 0.01) {
    const higher = fb > fa ? b : a;
    const [hi, lo] = fb > fa ? [fb, fa] : [fa, fb];
    parts.push(
      `la fracción muerta fue mayor en ${higher.label} ` +
        `(${(hi * 100).toFixed(0)} % frente a ${(lo * 100).toFixed(0)} %)`,
    );
  } else {
    parts.push(
      `la fracción muerta fue similar en ambas (≈${(fa * 100).toFixed(0)} %)`,
    );
  }
  const dr = sb.final_radius_um - sa.final_radius_um;
  if (Math.abs(dr) >= 1) {
    const bigger = dr > 0 ? b : a;
    const [hi, lo] = dr > 0 ? [sb.final_radius_um, sa.final_radius_um] : [sa.final_radius_um, sb.final_radius_um];
    parts.push(
      `y el radio final fue mayor en ${bigger.label} ` +
        `(${hi.toFixed(0)} µm frente a ${lo.toFixed(0)} µm)`,
    );
  } else {
    parts.push(`y el radio final fue parecido (≈${sa.final_radius_um.toFixed(0)} µm)`);
  }
  const ta = fmtT50(sa.t50_min);
  const tb = fmtT50(sb.t50_min);
  let t50bit = "";
  if (ta && tb) {
    t50bit = ` T50: ${ta} en ${a.label} y ${tb} en ${b.label}.`;
  } else if (ta || tb) {
    const which = ta ? a : b;
    t50bit = ` Solo ${which.label} cayó a la mitad de su pico (${ta ?? tb}); la otra siguió creciendo.`;
  } else {
    t50bit = ` Ninguna cayó a la mitad de su pico: ambas siguieron creciendo.`;
  }
  const first = parts[0].charAt(0).toUpperCase() + parts[0].slice(1);
  return `${first}; ${parts.slice(1).join("; ")}.${t50bit}`;
}
