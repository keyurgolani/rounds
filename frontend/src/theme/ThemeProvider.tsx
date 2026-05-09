import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { pb } from '../lib/pocketbase';
import { useAuth } from '../auth/AuthProvider';

export type Theme =
  | 'light'
  | 'dark'
  | 'sepia'
  | 'ocean'
  | 'slate'
  | 'rose'
  | 'mono'
  | 'system';
export type Accent =
  | 'terracotta'
  | 'forest'
  | 'ochre'
  | 'plum'
  | 'ink'
  | 'indigo'
  | 'teal'
  | 'rose';
export type DisplayType =
  | 'serif-display'
  | 'fraunces'
  | 'playfair'
  | 'dm-serif'
  | 'sans-only';
export type SansFont = 'inter' | 'geist' | 'manrope' | 'space-grotesk' | 'system';
export type Density = 'compact' | 'comfortable' | 'spacious';
export type NavStyle = 'sidebar' | 'topbar';
export type CardTreatment = 'layered' | 'bordered' | 'flat' | 'filled';
export type CornerRadius = 'sharp' | 'soft' | 'round' | 'pill';
export type Shadow = 'none' | 'subtle' | 'soft' | 'bold';
export type CardAccent = 'neutral' | 'tinted' | 'ruled';
export type AppBackground = 'grainy' | 'mesh' | 'gradient' | 'paper' | 'natural';

export type Tweaks = {
  theme: Theme;
  accent: Accent;
  typeVariant: DisplayType;
  sansFont: SansFont;
  density: Density;
  navStyle: NavStyle;
  cardTreatment: CardTreatment;
  radius: CornerRadius;
  shadow: Shadow;
  cardAccent: CardAccent;
  appBackground: AppBackground;
  // Glass slider values are stored as 0-100 ints; CSS conversion lives
  // in applyTweaks so any UI control can speak in percentages.
  glassTransparency: number;
  glassFrost: number;
  glassShadow: number;
};

const STORAGE_KEY = 'rounds.tweaks.v1';

const defaults: Tweaks = {
  theme: 'light',
  accent: 'terracotta',
  typeVariant: 'fraunces',
  sansFont: 'inter',
  density: 'comfortable',
  navStyle: 'sidebar',
  cardTreatment: 'layered',
  radius: 'soft',
  shadow: 'soft',
  cardAccent: 'neutral',
  appBackground: 'grainy',
  glassTransparency: 0,
  glassFrost: 50,
  glassShadow: 50,
};

function load(): Tweaks {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaults;
    return { ...defaults, ...(JSON.parse(raw) as Partial<Tweaks>) };
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
  // Newer prefs may not be present on older rows — everything below is
  // read-if-exists with a fallback to defaults.
  sans_font?: string;
  radius?: string;
  shadow?: string;
  card_accent?: string;
  app_background?: string;
  glass_transparency?: number;
  glass_frost?: number;
  glass_shadow?: number;
};

function tweaksToDb(t: Tweaks): DbPrefs {
  return {
    theme: t.theme,
    accent: t.accent,
    type_variant: t.typeVariant,
    density: t.density,
    nav_style: t.navStyle,
    card_treatment: t.cardTreatment,
    sans_font: t.sansFont,
    radius: t.radius,
    shadow: t.shadow,
    card_accent: t.cardAccent,
    app_background: t.appBackground,
    glass_transparency: t.glassTransparency,
    glass_frost: t.glassFrost,
    glass_shadow: t.glassShadow,
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
  if (row.sans_font) out.sansFont = row.sans_font as SansFont;
  if (row.radius) out.radius = row.radius as CornerRadius;
  if (row.shadow) out.shadow = row.shadow as Shadow;
  if (row.card_accent) out.cardAccent = row.card_accent as CardAccent;
  if (row.app_background) out.appBackground = row.app_background as AppBackground;
  if (typeof row.glass_transparency === 'number')
    out.glassTransparency = row.glass_transparency;
  if (typeof row.glass_frost === 'number') out.glassFrost = row.glass_frost;
  if (typeof row.glass_shadow === 'number') out.glassShadow = row.glass_shadow;
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

  setOrClear(html, 'data-accent', t.accent, 'terracotta');
  setOrClear(html, 'data-type', t.typeVariant, 'serif-display');
  setOrClear(html, 'data-sans', t.sansFont, 'inter');
  setOrClear(html, 'data-density', t.density, 'comfortable');
  setOrClear(html, 'data-cards', t.cardTreatment, 'layered');
  setOrClear(html, 'data-radius', t.radius, 'soft');
  setOrClear(html, 'data-shadow', t.shadow, 'soft');
  setOrClear(html, 'data-card-accent', t.cardAccent, 'neutral');
  setOrClear(html, 'data-app-bg', t.appBackground, 'grainy');
  html.setAttribute('data-nav', t.navStyle);

  // Glass effect is independent from card treatment. At 0, glass styles
  // are disabled; above 0, CSS composes the frosted layer with the active
  // card structure (layered, bordered, flat, or filled).
  const glassEffect = clamp01(t.glassTransparency / 100);
  const frost = clamp01(t.glassFrost / 100);
  const shadow = clamp01(t.glassShadow / 100);
  if (glassEffect > 0) html.setAttribute('data-glass', 'on');
  else html.removeAttribute('data-glass');
  const glassAlpha = 0.94 - glassEffect * 0.54;
  html.style.setProperty('--glass-alpha', String(glassAlpha));
  html.style.setProperty('--glass-blur', `${(frost * glassEffect * 28).toFixed(1)}px`);
  html.style.setProperty('--glass-saturate', `${(1 + frost * glassEffect * 0.6).toFixed(2)}`);
  html.style.setProperty('--glass-shadow-strength', String(shadow * glassEffect));
  // Inner highlight strengthens with frost (more diffusion → brighter
  // edge), then scales down with the overall glass effect.
  html.style.setProperty(
    '--glass-highlight',
    String(clamp01((0.05 + frost * 0.35 + glassEffect * 0.1) * glassEffect)),
  );
}

function clamp01(n: number): number {
  if (Number.isNaN(n)) return 0;
  if (n < 0) return 0;
  if (n > 1) return 1;
  return n;
}

function setOrClear(el: HTMLElement, attr: string, value: string, defaultValue: string) {
  if (value === defaultValue) el.removeAttribute(attr);
  else el.setAttribute(attr, value);
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

  // Debounced PocketBase upsert — created once, stable ref.
  // We find-or-create the user's preference row each call because
  // PocketBase doesn't have a native upsert; the unique index on
  // `user` makes the lookup cheap.
  const debouncedUpsertRef = useRef<((userId: string, t: Tweaks) => void) | null>(null);
  if (!debouncedUpsertRef.current) {
    debouncedUpsertRef.current = debounce(async (userId: string, t: Tweaks) => {
      try {
        const payload = { user: userId, ...tweaksToDb(t) };
        const existing = await pb
          .collection('user_preferences')
          .getFirstListItem(`user = "${userId}"`)
          .catch(() => null);
        if (existing) {
          await pb.collection('user_preferences').update(existing.id, payload);
        } else {
          await pb.collection('user_preferences').create(payload);
        }
      } catch (err) {
        console.error('[ThemeProvider] PocketBase upsert failed:', err);
      }
    }, 300);
  }

  // On auth: load server preferences and overlay onto local state
  useEffect(() => {
    if (!authReady || !user) return;

    let cancelled = false;
    (async () => {
      try {
        const row = await pb
          .collection('user_preferences')
          .getFirstListItem(`user = "${user.id}"`)
          .catch(() => null);
        if (!cancelled && row) {
          setTweaks((prev) => ({ ...prev, ...dbToTweaks(row as unknown as Partial<DbPrefs>) }));
        }
      } catch (err) {
        console.error('[ThemeProvider] PocketBase load failed, using localStorage:', err);
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
      if (user) {
        debouncedUpsertRef.current?.(user.id, next);
      }
    },
    reset: () => {
      setTweaks(defaults);
      if (user) {
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
