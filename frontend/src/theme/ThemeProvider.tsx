import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { supabase, supabaseEnabled } from '../lib/supabase';
import { useAuth } from '../auth/AuthProvider';

export type Theme = 'light' | 'dark' | 'sepia' | 'system';
export type Accent = 'terracotta' | 'forest' | 'ochre' | 'plum' | 'ink';
export type DisplayType = 'serif-display' | 'fraunces' | 'sans-only';
export type Density = 'compact' | 'comfortable' | 'spacious';
export type NavStyle = 'sidebar' | 'topbar';
export type CardTreatment = 'layered' | 'bordered' | 'flat';

export type Tweaks = {
  theme: Theme;
  accent: Accent;
  typeVariant: DisplayType;
  density: Density;
  navStyle: NavStyle;
  cardTreatment: CardTreatment;
};

const STORAGE_KEY = 'rounds.tweaks.v1';

const defaults: Tweaks = {
  theme: 'light',
  accent: 'terracotta',
  typeVariant: 'fraunces',
  density: 'comfortable',
  navStyle: 'sidebar',
  cardTreatment: 'layered',
};

function load(): Tweaks {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaults;
    return { ...defaults, ...JSON.parse(raw) } as Tweaks;
  } catch {
    return defaults;
  }
}

function save(t: Tweaks) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(t));
  } catch {
    /* noop */
  }
}

// ---------- snake_case <-> camelCase conversion ----------

type DbPrefs = {
  theme: string;
  accent: string;
  type_variant: string;
  density: string;
  nav_style: string;
  card_treatment: string;
};

function tweaksToDb(t: Tweaks): Omit<DbPrefs, never> {
  return {
    theme: t.theme,
    accent: t.accent,
    type_variant: t.typeVariant,
    density: t.density,
    nav_style: t.navStyle,
    card_treatment: t.cardTreatment,
  };
}

function dbToTweaks(row: Partial<DbPrefs>): Partial<Tweaks> {
  const out: Partial<Tweaks> = {};
  if (row.theme) out.theme = row.theme as Theme;
  if (row.accent) out.accent = row.accent as Accent;
  if (row.type_variant) out.typeVariant = row.type_variant as DisplayType;
  if (row.density) out.density = row.density as Density;
  if (row.nav_style) out.navStyle = row.nav_style as NavStyle;
  if (row.card_treatment) out.cardTreatment = row.card_treatment as CardTreatment;
  return out;
}

// ---------- tiny debounce helper ----------

function debounce<T extends (...args: Parameters<T>) => void>(fn: T, ms: number) {
  let timer: ReturnType<typeof setTimeout> | null = null;
  return (...args: Parameters<T>) => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      timer = null;
      fn(...args);
    }, ms);
  };
}

type ThemeContextValue = Tweaks & {
  setTweak: <K extends keyof Tweaks>(key: K, value: Tweaks[K]) => void;
  reset: () => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

function applyTweaks(t: Tweaks) {
  const html = document.documentElement;
  let effectiveTheme: Exclude<Theme, 'system'> = 'light';
  if (t.theme === 'system') {
    effectiveTheme =
      typeof window !== 'undefined' &&
      window.matchMedia?.('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light';
  } else {
    effectiveTheme = t.theme;
  }
  html.setAttribute('data-theme', effectiveTheme);
  html.setAttribute('data-accent', t.accent === 'terracotta' ? '' : t.accent);
  if (t.accent === 'terracotta') html.removeAttribute('data-accent');
  html.setAttribute(
    'data-type',
    t.typeVariant === 'serif-display' ? '' : t.typeVariant
  );
  if (t.typeVariant === 'serif-display') html.removeAttribute('data-type');
  html.setAttribute('data-density', t.density === 'comfortable' ? '' : t.density);
  if (t.density === 'comfortable') html.removeAttribute('data-density');
  html.setAttribute('data-cards', t.cardTreatment === 'layered' ? '' : t.cardTreatment);
  if (t.cardTreatment === 'layered') html.removeAttribute('data-cards');
  html.setAttribute('data-nav', t.navStyle);
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const { user, ready: authReady } = useAuth();
  const [tweaks, setTweaks] = useState<Tweaks>(() => load());

  // Apply tweaks + keep localStorage in sync on every change
  useEffect(() => {
    applyTweaks(tweaks);
    save(tweaks);
  }, [tweaks]);

  // Watch system theme changes when theme === 'system'
  useEffect(() => {
    if (tweaks.theme !== 'system' || typeof window === 'undefined') return;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => applyTweaks(tweaks);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, [tweaks]);

  // Debounced Supabase upsert — created once, stable ref
  const debouncedUpsertRef = useRef<((userId: string, t: Tweaks) => void) | null>(null);
  if (!debouncedUpsertRef.current) {
    debouncedUpsertRef.current = debounce(async (userId: string, t: Tweaks) => {
      if (!supabase) return;
      try {
        await supabase
          .from('user_preferences')
          .upsert({ user_id: userId, ...tweaksToDb(t) });
      } catch (err) {
        console.error('[ThemeProvider] Supabase upsert failed:', err);
      }
    }, 300);
  }

  // On auth: load server preferences and overlay onto local state
  useEffect(() => {
    if (!authReady || !supabaseEnabled || !supabase || !user) return;

    let cancelled = false;
    (async () => {
      try {
        const { data } = await supabase
          .from('user_preferences')
          .select('theme, accent, type_variant, density, nav_style, card_treatment')
          .eq('user_id', user.id)
          .maybeSingle();
        if (!cancelled && data) {
          setTweaks((prev) => ({ ...prev, ...dbToTweaks(data as Partial<DbPrefs>) }));
        }
      } catch (err) {
        console.error('[ThemeProvider] Supabase load failed, using localStorage:', err);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [authReady, user]);

  const value: ThemeContextValue = {
    ...tweaks,
    setTweak: (key, val) => {
      const next = { ...tweaks, [key]: val };
      setTweaks(next);
      // Persist to Supabase when authenticated
      if (supabaseEnabled && user) {
        debouncedUpsertRef.current?.(user.id, next);
      }
    },
    reset: () => {
      setTweaks(defaults);
      if (supabaseEnabled && user) {
        debouncedUpsertRef.current?.(user.id, defaults);
      }
    },
  };

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
}
