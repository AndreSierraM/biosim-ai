import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import en from "./en.json";
import es from "./es.json";

export type Locale = "es" | "en";

const dicts = { es, en } as const;
export type Strings = typeof es;

// Compile-time parity: en.json must carry exactly the es.json keys.
export const _parityCheck: Strings = en;

export type Vars = Record<string, string | number>;

const STORAGE_KEY = "biosim-locale";

function initialLocale(): Locale {
  if (typeof window === "undefined" || typeof localStorage === "undefined") return "es";
  try {
    return localStorage.getItem(STORAGE_KEY) === "en" ? "en" : "es";
  } catch {
    return "es";
  }
}

/** Locale for non-React code (API client errors). Mirrors the provider. */
let current: Locale = initialLocale();
export function getLocale(): Locale {
  return current;
}

function render(template: string, vars?: Vars): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (_, k: string) =>
    vars[k] === undefined ? `{${k}}` : String(vars[k]),
  );
}

interface LocaleValue {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: (key: keyof Strings, vars?: Vars) => string;
}

const LocaleContext = createContext<LocaleValue>({
  locale: "es",
  setLocale: () => {},
  t: (key) => String(key),
});

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => initialLocale());
  const value = useMemo<LocaleValue>(() => {
    const dict = dicts[locale] as Record<string, string>;
    const fallback = dicts.es as Record<string, string>;
    return {
      locale,
      setLocale: (l: Locale) => {
        current = l;
        setLocaleState(l);
        try {
          localStorage.setItem(STORAGE_KEY, l);
        } catch {
          // Private mode: locale simply does not persist.
        }
      },
      t: (key: keyof Strings, vars?: Vars) => {
        const template = dict[String(key)] ?? fallback[String(key)] ?? String(key);
        return render(template, vars);
      },
    };
  }, [locale]);

  useEffect(() => {
    current = locale;
    document.documentElement.lang = locale;
    const dict = dicts[locale] as Record<string, string>;
    document.title = dict["doc.title"] ?? document.title;
    const meta = document.querySelector('meta[name="description"]');
    if (meta && locale === "en") {
      meta.setAttribute(
        "content",
        "BioSim AI: describe your hypothesis, the AI plans, the engine computes, compare tumors in 3D.",
      );
    }
  }, [locale]);

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale(): LocaleValue {
  return useContext(LocaleContext);
}

/** String lookup outside React (falls back to Spanish when a key is missing). */
export function tFor(locale: Locale, key: keyof Strings, vars?: Vars): string {
  const dict = dicts[locale] as Record<string, string>;
  const template =
    dict[String(key)] ?? (dicts.es as Record<string, string>)[String(key)] ?? String(key);
  return render(template, vars);
}
