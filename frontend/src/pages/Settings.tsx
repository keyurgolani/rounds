import { type CSSProperties, type ReactNode } from 'react';
import AppHeader from '../components/shell/AppHeader';
import PageShell from '../components/shell/PageShell';
import { useTheme, type Tweaks } from '../theme/ThemeProvider';
import { useAuth } from '../auth/AuthProvider';
import { pocketbaseEnabled } from '../lib/pocketbase';
import AISection from '../settings/AISection';
import DataSection from '../settings/DataSection';
import { APP_VERSION } from '../version';

const GLASS_STEPS = [0, 25, 50, 75, 100] as const;
const GLASS_LABELS: Record<(typeof GLASS_STEPS)[number], string> = {
  0: 'Off',
  25: 'Low',
  50: 'Med',
  75: 'High',
  100: 'Max',
};

export default function Settings() {
  const t = useTheme();
  const { user } = useAuth();
  const synced = pocketbaseEnabled && Boolean(user);

  return (
    <PageShell
      header={
        <AppHeader
          eyebrow="Account · Preferences"
          title="Settings"
          description="Tune the look and feel of Rounds — theme, accent, fonts, corners, density, and more."
          chromeActions={
            <button
              type="button"
              onClick={t.reset}
              className="mono uppercase"
              style={{
                padding: '8px 14px',
                borderRadius: 'var(--radius)',
                border: 0,
                background: 'var(--bg-sunken)',
                boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                color: 'var(--text-2)',
                fontSize: 10.5,
                letterSpacing: '0.12em',
                cursor: 'pointer',
              }}
            >
              Reset to default
            </button>
          }
        />
      }
    >
      <div className="px-5 sm:px-8 py-6 flex flex-col gap-5">
        <Card title="Look & feel" subtitle="Every surface reads from these toggles.">
          <div className="grid gap-x-8 gap-y-0 grid-cols-1 xl:grid-cols-2">
            <Row label="Theme">
              {(
                [
                  ['light', 'Light'],
                  ['dark', 'Dark'],
                  ['sepia', 'Sepia'],
                  ['ocean', 'Ocean'],
                  ['slate', 'Slate'],
                  ['rose', 'Rose'],
                  ['mono', 'Mono'],
                  ['system', 'System'],
                ] as [Tweaks['theme'], string][]
              ).map(([k, label]) => (
                <Opt
                  key={k}
                  active={t.theme === k}
                  onClick={() => t.setTweak('theme', k)}
                  label={label}
                  preview={<ThemeSwatch theme={k} />}
                />
              ))}
            </Row>

            <Row label="Accent">
              {(
                [
                  ['terracotta', '#C9633F'],
                  ['forest', '#2F5D4A'],
                  ['ochre', '#B68C2A'],
                  ['plum', '#7C3A4E'],
                  ['ink', '#181613'],
                  ['indigo', '#4C5FD6'],
                  ['teal', '#147A6B'],
                  ['rose', '#C7305F'],
                ] as [Tweaks['accent'], string][]
              ).map(([k, s]) => (
                <Opt
                  key={k}
                  active={t.accent === k}
                  onClick={() => t.setTweak('accent', k)}
                  label={k}
                  preview={<AccentSwatch color={s} />}
                />
              ))}
            </Row>

            <Row label="Display type">
              {(
                [
                  ['serif-display', 'Instrument Serif'],
                  ['fraunces', 'Fraunces'],
                  ['playfair', 'Playfair Display'],
                  ['dm-serif', 'DM Serif'],
                  ['sans-only', 'Sans only'],
                ] as [Tweaks['typeVariant'], string][]
              ).map(([k, label]) => (
                <Opt
                  key={k}
                  active={t.typeVariant === k}
                  onClick={() => t.setTweak('typeVariant', k)}
                  label={label}
                  width={110}
                  preview={<DisplayTypePreview variant={k} />}
                />
              ))}
            </Row>

            <Row label="Body font">
              {(
                [
                  ['inter', 'Inter'],
                  ['geist', 'Geist'],
                  ['manrope', 'Manrope'],
                  ['space-grotesk', 'Space Grotesk'],
                  ['system', 'System'],
                ] as [Tweaks['sansFont'], string][]
              ).map(([k, label]) => (
                <Opt
                  key={k}
                  active={t.sansFont === k}
                  onClick={() => t.setTweak('sansFont', k)}
                  label={label}
                  preview={<SansFontPreview font={k} />}
                />
              ))}
            </Row>

            <Row label="Glass effect">
              {GLASS_STEPS.map((v) => (
                <Opt
                  key={v}
                  active={t.glassTransparency === v}
                  onClick={() => t.setTweak('glassTransparency', v)}
                  label={GLASS_LABELS[v]}
                  preview={
                    <GlassPreview
                      transparency={v}
                      frost={t.glassFrost}
                      shadow={t.glassShadow}
                    />
                  }
                />
              ))}
            </Row>
            <Row label="Glass frost">
              {GLASS_STEPS.map((v) => (
                <Opt
                  key={v}
                  active={t.glassFrost === v}
                  onClick={() => t.setTweak('glassFrost', v)}
                  label={GLASS_LABELS[v]}
                  preview={
                    <GlassPreview
                      transparency={Math.max(t.glassTransparency, 50)}
                      frost={v}
                      shadow={t.glassShadow}
                    />
                  }
                />
              ))}
            </Row>
            <Row label="Glass shadow" last>
              {GLASS_STEPS.map((v) => (
                <Opt
                  key={v}
                  active={t.glassShadow === v}
                  onClick={() => t.setTweak('glassShadow', v)}
                  label={GLASS_LABELS[v]}
                  preview={
                    <GlassPreview
                      transparency={Math.max(t.glassTransparency, 50)}
                      frost={t.glassFrost}
                      shadow={v}
                    />
                  }
                />
              ))}
            </Row>

            <Row label="Background" last>
              {(
                [
                  ['grainy', 'Grainy'],
                  ['mesh', 'Mesh'],
                  ['gradient', 'Gradient'],
                  ['paper', 'Paper'],
                  ['natural', 'Natural'],
                ] as [Tweaks['appBackground'], string][]
              ).map(([k, label]) => (
                <Opt
                  key={k}
                  active={t.appBackground === k}
                  onClick={() => t.setTweak('appBackground', k)}
                  label={label}
                  preview={<BackgroundPreview kind={k} />}
                />
              ))}
            </Row>

          </div>

          <div className="grid gap-x-8 gap-y-0 grid-cols-1 sm:grid-cols-2 xl:grid-cols-3" style={{ marginTop: 4 }}>
            <Row label="Corners">
              {(
                [
                  ['sharp', 'Sharp'],
                  ['soft', 'Soft'],
                  ['round', 'Round'],
                ] as [Tweaks['radius'], string][]
              ).map(([k, label]) => (
                <Opt
                  key={k}
                  active={t.radius === k}
                  onClick={() => t.setTweak('radius', k)}
                  label={label}
                  preview={<RadiusPreview radius={k} />}
                />
              ))}
            </Row>

            <Row label="Shadow depth">
              {(
                [
                  ['none', 'None'],
                  ['subtle', 'Subtle'],
                  ['soft', 'Soft'],
                  ['bold', 'Bold'],
                ] as [Tweaks['shadow'], string][]
              ).map(([k, label]) => (
                <Opt
                  key={k}
                  active={t.shadow === k}
                  onClick={() => t.setTweak('shadow', k)}
                  label={label}
                  preview={<ShadowPreview shadow={k} />}
                />
              ))}
            </Row>

            <Row label="Cards">
              {(
                [
                  ['layered', 'Layered'],
                  ['bordered', 'Bordered'],
                  ['flat', 'Flat'],
                  ['filled', 'Filled'],
                ] as [Tweaks['cardTreatment'], string][]
              ).map(([k, label]) => (
                <Opt
                  key={k}
                  active={t.cardTreatment === k}
                  onClick={() => t.setTweak('cardTreatment', k)}
                  label={label}
                  preview={<CardTreatmentPreview treatment={k} />}
                />
              ))}
            </Row>

            <Row label="Card accent" last>
              {(
                [
                  ['neutral', 'Neutral'],
                  ['tinted', 'Tinted'],
                  ['ruled', 'Ruled'],
                ] as [Tweaks['cardAccent'], string][]
              ).map(([k, label]) => (
                <Opt
                  key={k}
                  active={t.cardAccent === k}
                  onClick={() => t.setTweak('cardAccent', k)}
                  label={label}
                  preview={<CardAccentPreview accent={k} />}
                />
              ))}
            </Row>

            <Row label="Density" last>
              {(['compact', 'comfortable', 'spacious'] as const).map((v) => (
                <Opt
                  key={v}
                  active={t.density === v}
                  onClick={() => t.setTweak('density', v)}
                  label={v}
                  preview={<DensityPreview density={v} />}
                />
              ))}
            </Row>

            <Row label="Navigation" last>
              {(
                [
                  ['sidebar', 'Sidebar'],
                  ['topbar', 'Top bar'],
                ] as [Tweaks['navStyle'], string][]
              ).map(([k, label]) => (
                <Opt
                  key={k}
                  active={t.navStyle === k}
                  onClick={() => t.setTweak('navStyle', k)}
                  label={label}
                  preview={<NavPreview kind={k} />}
                />
              ))}
            </Row>
          </div>
        </Card>

        <AISection />

        <DataSection />
      </div>

      <div
        className="mono px-5 sm:px-8 pb-8"
        style={{ fontSize: 10.5, color: 'var(--text-4)', letterSpacing: '0.12em' }}
      >
        ROUNDS v{APP_VERSION}{synced ? ' · SETTINGS SYNC TO YOUR ACCOUNT' : ''}
      </div>
    </PageShell>
  );
}

function Card({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <div className="card p-5 flex flex-col">
      <div className="mb-4">
        <div className="eyebrow" style={{ marginBottom: 4 }}>
          {title}
        </div>
        {subtitle && (
          <p style={{ margin: 0, fontSize: 12.5, color: 'var(--text-3)', lineHeight: 1.55 }}>
            {subtitle}
          </p>
        )}
      </div>
      <div className="flex flex-col">{children}</div>
    </div>
  );
}

function Row({
  label,
  children,
  last,
}: {
  label: string;
  children: ReactNode;
  last?: boolean;
}) {
  return (
    <div
      className="grid gap-3 grid-cols-1 sm:[grid-template-columns:108px_1fr] items-center"
      style={{
        padding: '8px 0',
        borderBottom: last ? 'none' : '1px solid var(--border)',
      }}
    >
      <div className="eyebrow">{label}</div>
      <div className="flex gap-1.5 flex-wrap">{children}</div>
    </div>
  );
}

/**
 * Preview-bearing option button. Renders a small preview tile above
 * a label so the user sees what the choice does, not just its name.
 * The preview slot is intentionally fixed-height so a row of options
 * lines up cleanly even when each tile shows different content.
 */
function Opt({
  active,
  onClick,
  label,
  preview,
  width = 64,
}: {
  active: boolean;
  onClick: () => void;
  label: ReactNode;
  preview: ReactNode;
  width?: number;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      style={{
        width,
        padding: 6,
        border: 0,
        borderRadius: 'var(--radius)',
        background: active ? 'var(--accent-soft)' : 'var(--bg-sunken)',
        boxShadow: active
          ? 'inset 0 0 0 1.5px var(--accent)'
          : 'inset 0 0 0 1px var(--border)',
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
      }}
    >
      <div
        style={{
          height: 36,
          borderRadius: 6,
          background: 'var(--bg-elev)',
          boxShadow: 'inset 0 0 0 1px var(--border)',
          display: 'grid',
          placeItems: 'center',
          overflow: 'hidden',
        }}
      >
        {preview}
      </div>
      <span
        style={{
          fontSize: 10.5,
          color: active ? 'var(--accent)' : 'var(--text-3)',
          textAlign: 'center',
          textTransform: 'capitalize',
          lineHeight: 1.2,
          fontWeight: active ? 600 : 500,
          letterSpacing: '0.02em',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {label}
      </span>
    </button>
  );
}

// ---------- preview helpers ----------

/**
 * Reuses the global theme CSS by setting data-theme on a local wrapper.
 * The CSS variables (--bg, --text, --accent…) re-resolve inside the
 * wrapper, so the swatch reads with that theme's actual colors.
 */
function ThemeSwatch({ theme }: { theme: Tweaks['theme'] }) {
  const dataAttr = theme === 'system' ? undefined : theme;
  return (
    <div
      data-theme={dataAttr}
      style={{
        width: '100%',
        height: '100%',
        background: 'var(--bg)',
        color: 'var(--text)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 5,
      }}
    >
      <span
        style={{
          fontFamily: 'var(--font-display)',
          fontStyle: 'italic',
          fontSize: 17,
          lineHeight: 1,
        }}
      >
        Aa
      </span>
      <span
        aria-hidden="true"
        style={{
          width: 7,
          height: 7,
          borderRadius: 999,
          background: 'var(--accent)',
        }}
      />
    </div>
  );
}

function AccentSwatch({ color }: { color: string }) {
  return (
    <div
      aria-hidden="true"
      style={{
        width: 26,
        height: 26,
        borderRadius: 999,
        background: color,
        boxShadow: 'inset 0 0 0 1px rgba(0,0,0,0.15), 0 1px 2px rgba(0,0,0,0.1)',
      }}
    />
  );
}

function DisplayTypePreview({ variant }: { variant: Tweaks['typeVariant'] }) {
  return (
    <div
      data-type={variant}
      style={{
        fontFamily: 'var(--font-display)',
        fontStyle: 'italic',
        fontSize: 22,
        color: 'var(--text)',
        lineHeight: 1,
      }}
    >
      Aa
    </div>
  );
}

function SansFontPreview({ font }: { font: Tweaks['sansFont'] }) {
  return (
    <div
      data-sans={font}
      style={{
        fontFamily: 'var(--font-sans)',
        fontSize: 16,
        fontWeight: 500,
        color: 'var(--text)',
        lineHeight: 1,
        letterSpacing: '0.01em',
      }}
    >
      Ag
    </div>
  );
}

function RadiusPreview({ radius }: { radius: Tweaks['radius'] }) {
  return (
    <div
      data-radius={radius}
      style={{
        width: 32,
        height: 24,
        background: 'var(--bg-sunken)',
        borderRadius: 'var(--radius)',
        boxShadow: 'inset 0 0 0 1.5px var(--text-3)',
      }}
    />
  );
}

function ShadowPreview({ shadow }: { shadow: Tweaks['shadow'] }) {
  // Inline shadow definitions so each tile shows its OWN level
  // regardless of the page-level data-shadow. Values are picked to be
  // perceptibly distinct at preview size — flatter than the live CSS
  // for "subtle", and the "bold" tier carries a heavier drop than the
  // production token so the four steps step up clearly.
  const shadowValue =
    shadow === 'none'
      ? 'inset 0 0 0 1px var(--text-4)'
      : shadow === 'subtle'
      ? '0 1px 2px rgba(24, 22, 19, 0.12), 0 0 0 1px rgba(24, 22, 19, 0.08)'
      : shadow === 'soft'
      ? '0 3px 8px -2px rgba(24, 22, 19, 0.2), 0 0 0 1px rgba(24, 22, 19, 0.08)'
      : '0 8px 18px -4px rgba(24, 22, 19, 0.35), 0 0 0 1px rgba(24, 22, 19, 0.12)';
  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        // Tinted backdrop so the drop shadow falls onto a different
        // tone and registers visually.
        background: 'var(--bg-sunken)',
        padding: 8,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          width: '100%',
          height: '100%',
          background: 'var(--bg-elev)',
          borderRadius: 4,
          boxShadow: shadowValue,
        }}
      />
    </div>
  );
}

function CardTreatmentPreview({ treatment }: { treatment: Tweaks['cardTreatment'] }) {
  // Inline-styled so each tile renders its OWN treatment regardless of
  // the page-level data-cards on <html>. Differences are amplified
  // versus the live CSS (thicker border on bordered, deeper tonal
  // contrast on filled) so the four options read as distinctly
  // different at preview size.
  const isFilled = treatment === 'filled';
  const isBordered = treatment === 'bordered';
  const isFlat = treatment === 'flat';
  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        // Contrasting backdrop so shadows / borders / fills register.
        background: 'var(--bg-sunken)',
        padding: 6,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          width: '100%',
          height: '100%',
          borderRadius: 4,
          background: isFilled ? 'var(--paper-3)' : 'var(--bg-elev)',
          boxShadow: isBordered
            ? 'inset 0 0 0 1.5px var(--text-3)'
            : isFlat || isFilled
            ? 'none'
            : '0 2px 6px -2px rgba(24, 22, 19, 0.22), 0 0 0 1px rgba(24, 22, 19, 0.1)',
        }}
      />
    </div>
  );
}

/**
 * Renders a small frosted card on top of a tinted backdrop so the
 * glass effect is visible even at low transparency levels.
 *
 * We bypass the runtime CSS vars set by ThemeProvider by writing
 * inline `--glass-*` overrides on the wrapper — the per-step preview
 * has to show its OWN level, not the level currently applied to the
 * whole page.
 */
function GlassPreview({
  transparency,
  frost,
  shadow,
}: {
  transparency: number;
  frost: number;
  shadow: number;
}) {
  const tRatio = transparency / 100;
  const fRatio = frost / 100;
  const sRatio = shadow / 100;
  // Same math as applyTweaks() in ThemeProvider, condensed here so the
  // preview reflects the production output.
  const glassAlpha = 0.94 - tRatio * 0.54;
  const glassBlur = (fRatio * tRatio * 28).toFixed(1) + 'px';
  const glassSaturate = (1 + fRatio * tRatio * 0.6).toFixed(2);
  const shadowStrength = sRatio * tRatio;
  const highlight = Math.min(1, (0.05 + fRatio * 0.35 + tRatio * 0.1) * tRatio);
  const style: CSSProperties & Record<string, string | number> = {
    width: '100%',
    height: '100%',
    background:
      'radial-gradient(circle at 25% 30%, var(--accent-soft), transparent 55%), linear-gradient(135deg, var(--bg-sunken), var(--bg-elev))',
    padding: 6,
    display: 'grid',
    placeItems: 'center',
    '--glass-alpha': String(glassAlpha),
    '--glass-blur': glassBlur,
    '--glass-saturate': glassSaturate,
    '--glass-shadow-strength': String(shadowStrength),
    '--glass-highlight': String(highlight),
  };
  return (
    <div data-glass={transparency > 0 ? 'on' : undefined} style={style}>
      <div
        className="card"
        style={{
          width: 30,
          height: 22,
          borderRadius: 4,
        }}
      />
    </div>
  );
}

function BackgroundPreview({ kind }: { kind: Tweaks['appBackground'] }) {
  // [data-app-bg] selectors target body::before, so we approximate each
  // pattern inline. The previews are hints, not pixel-perfect mirrors —
  // good enough to tell the options apart at a glance.
  const styles: Record<Tweaks['appBackground'], CSSProperties> = {
    grainy: {
      background:
        'radial-gradient(circle at 20% 30%, rgba(0,0,0,0.05) 0 1px, transparent 1px), radial-gradient(circle at 70% 60%, rgba(0,0,0,0.04) 0 1px, transparent 1px), var(--bg)',
      backgroundSize: '5px 5px, 7px 7px',
    },
    mesh: {
      background:
        'radial-gradient(circle at 20% 30%, var(--accent-soft), transparent 50%), radial-gradient(circle at 80% 70%, var(--accent-soft), transparent 55%), var(--bg)',
    },
    gradient: {
      background: 'linear-gradient(135deg, var(--bg) 0%, var(--bg-sunken) 100%)',
    },
    paper: {
      background:
        'repeating-linear-gradient(0deg, rgba(0,0,0,0.02) 0 1px, transparent 1px 6px), var(--bg)',
    },
    natural: {
      background:
        'linear-gradient(180deg, var(--bg-elev), var(--bg) 60%, var(--bg-sunken))',
    },
  };
  return <div style={{ width: '100%', height: '100%', ...styles[kind] }} />;
}

function CardAccentPreview({ accent }: { accent: Tweaks['cardAccent'] }) {
  // The page-level [data-card-accent='tinted'] / 'ruled' rules in
  // globals.css define `.card` overrides but there's no `'neutral'`
  // reset — which means a "neutral" preview tile inherits the page's
  // active stripe/border-top whenever the user happens to be on a
  // tinted/ruled accent. Inline-styled previews dodge that entirely
  // and each tile shows exactly its own accent.
  const isTinted = accent === 'tinted';
  const isRuled = accent === 'ruled';
  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        background: 'var(--bg-sunken)',
        padding: 6,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          width: '100%',
          height: '100%',
          background: 'var(--bg-elev)',
          borderRadius: 4,
          boxShadow: isTinted
            ? '0 1px 2px rgba(24, 22, 19, 0.1), 0 0 0 1px var(--border), inset 4px 0 0 var(--accent)'
            : '0 1px 2px rgba(24, 22, 19, 0.1), 0 0 0 1px var(--border)',
          borderTop: isRuled ? '2px solid var(--accent)' : undefined,
        }}
      />
    </div>
  );
}

function DensityPreview({ density }: { density: Tweaks['density'] }) {
  const gap = density === 'compact' ? 3 : density === 'comfortable' ? 6 : 10;
  return (
    <div
      style={{
        width: 32,
        height: 32,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        gap,
      }}
    >
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          style={{
            height: 2,
            borderRadius: 999,
            background: 'var(--text-3)',
            opacity: 1 - i * 0.15,
          }}
        />
      ))}
    </div>
  );
}

function NavPreview({ kind }: { kind: Tweaks['navStyle'] }) {
  if (kind === 'sidebar') {
    return (
      <div
        style={{
          width: 40,
          height: 28,
          borderRadius: 3,
          display: 'flex',
          background: 'var(--bg-sunken)',
          boxShadow: 'inset 0 0 0 1px var(--border)',
          overflow: 'hidden',
        }}
      >
        <div style={{ width: 10, background: 'var(--accent-soft)' }} />
        <div style={{ flex: 1, background: 'var(--bg-elev)' }} />
      </div>
    );
  }
  return (
    <div
      style={{
        width: 40,
        height: 28,
        borderRadius: 3,
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--bg-sunken)',
        boxShadow: 'inset 0 0 0 1px var(--border)',
        overflow: 'hidden',
      }}
    >
      <div style={{ height: 7, background: 'var(--accent-soft)' }} />
      <div style={{ flex: 1, background: 'var(--bg-elev)' }} />
    </div>
  );
}
