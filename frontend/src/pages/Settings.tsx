import { type ReactNode } from 'react';
import AppHeader from '../components/shell/AppHeader';
import PageShell from '../components/shell/PageShell';
import { useTheme, type Tweaks } from '../theme/ThemeProvider';
import { useAuth } from '../auth/AuthProvider';
import { pocketbaseEnabled } from '../lib/pocketbase';
import DataSection from '../settings/DataSection';
import { APP_VERSION } from '../version';

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
          actions={
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
            <Row label="Theme" help="Warm paper, deep slate, ocean, sepia, rose, mono, or follow OS.">
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
                <Opt key={k} active={t.theme === k} onClick={() => t.setTweak('theme', k)}>
                  {label}
                </Opt>
              ))}
            </Row>

            <Row
              label="Accent"
              help="The brand color for buttons, pills, and active links."
            >
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
                  swatch={s}
                >
                  {k}
                </Opt>
              ))}
            </Row>

            <Row
              label="Display type"
              help="Font used for italic titles and card display type."
            >
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
                >
                  {label}
                </Opt>
              ))}
            </Row>

            <Row label="Body font" help="Sans family used for body copy and UI chrome.">
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
                >
                  {label}
                </Opt>
              ))}
            </Row>

            <Row
              label="Corners"
              help="How rounded the corners on cards, buttons, and pills should be."
            >
              {(
                [
                  ['sharp', 'Sharp'],
                  ['soft', 'Soft'],
                  ['round', 'Round'],
                  ['pill', 'Pill'],
                ] as [Tweaks['radius'], string][]
              ).map(([k, label]) => (
                <Opt key={k} active={t.radius === k} onClick={() => t.setTweak('radius', k)}>
                  {label}
                </Opt>
              ))}
            </Row>

            <Row label="Shadow depth" help="From flat to floating.">
              {(
                [
                  ['none', 'None'],
                  ['subtle', 'Subtle'],
                  ['soft', 'Soft'],
                  ['bold', 'Bold'],
                ] as [Tweaks['shadow'], string][]
              ).map(([k, label]) => (
                <Opt key={k} active={t.shadow === k} onClick={() => t.setTweak('shadow', k)}>
                  {label}
                </Opt>
              ))}
            </Row>

            <Row
              label="Cards"
              help="Choose the card structure. Glass is a separate effect that can layer over any structure."
            >
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
                >
                  {label}
                </Opt>
              ))}
            </Row>

            <Row
              label="Glass effect"
              help="0 turns glass off. Higher values add frosted translucency on top of the selected card structure."
            >
              <Slider
                value={t.glassTransparency}
                onChange={(v) => t.setTweak('glassTransparency', v)}
                ariaLabel="Glass effect"
              />
            </Row>
            <Row
              label="Glass frost"
              help="Backdrop blur and saturation strength when the glass effect is above 0."
            >
              <Slider
                value={t.glassFrost}
                onChange={(v) => t.setTweak('glassFrost', v)}
                ariaLabel="Glass frost"
              />
            </Row>
            <Row
              label="Glass shadow"
              help="Depth and edge contrast for glass surfaces."
            >
              <Slider
                value={t.glassShadow}
                onChange={(v) => t.setTweak('glassShadow', v)}
                ariaLabel="Glass shadow"
              />
            </Row>

            <Row
              label="Background"
              help="The surface behind every page. Each option retints itself to the active theme."
            >
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
                >
                  {label}
                </Opt>
              ))}
            </Row>

            <Row
              label="Card accent"
              help="Neutral stays flat; tinted adds a left accent bar; ruled adds a top accent line."
            >
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
                >
                  {label}
                </Opt>
              ))}
            </Row>

            <Row label="Density" help="Compact fits more on-screen; spacious gives type more room.">
              {(['compact', 'comfortable', 'spacious'] as const).map((v) => (
                <Opt key={v} active={t.density === v} onClick={() => t.setTweak('density', v)}>
                  {v}
                </Opt>
              ))}
            </Row>

            <Row
              label="Navigation"
              help="Sidebar keeps nav off the content column; top bar frees horizontal space."
              last
            >
              {(
                [
                  ['sidebar', 'Sidebar'],
                  ['topbar', 'Top bar'],
                ] as [Tweaks['navStyle'], string][]
              ).map(([k, label]) => (
                <Opt key={k} active={t.navStyle === k} onClick={() => t.setTweak('navStyle', k)}>
                  {label}
                </Opt>
              ))}
            </Row>
          </div>
        </Card>

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
  help,
  children,
  last,
}: {
  label: string;
  help: string;
  children: ReactNode;
  last?: boolean;
}) {
  return (
    <div
      className="grid gap-3 grid-cols-1 sm:[grid-template-columns:180px_1fr] items-start"
      style={{
        padding: '14px 0',
        borderBottom: last ? 'none' : '1px solid var(--border)',
      }}
    >
      <div>
        <div className="eyebrow mb-1.5">{label}</div>
        <p
          style={{
            margin: 0,
            fontSize: 12,
            color: 'var(--text-3)',
            lineHeight: 1.55,
          }}
        >
          {help}
        </p>
      </div>
      <div className="flex gap-1.5 flex-wrap">{children}</div>
    </div>
  );
}

function Slider({
  value,
  onChange,
  ariaLabel,
}: {
  value: number;
  onChange: (v: number) => void;
  ariaLabel: string;
}) {
  return (
    <div className="flex items-center gap-3" style={{ width: '100%', maxWidth: 360 }}>
      <input
        type="range"
        min={0}
        max={100}
        step={1}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        aria-label={ariaLabel}
        style={{
          flex: 1,
          height: 4,
          accentColor: 'var(--accent)',
          cursor: 'pointer',
        }}
      />
      <span
        className="mono"
        style={{ width: 36, fontSize: 11, color: 'var(--text-3)', textAlign: 'right' }}
      >
        {value}
      </span>
    </div>
  );
}

function Opt({
  active,
  onClick,
  children,
  swatch,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
  swatch?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        padding: swatch ? '7px 12px 7px 7px' : '7px 12px',
        border: 0,
        borderRadius: 'var(--radius)',
        background: active ? 'var(--accent)' : 'var(--bg-sunken)',
        color: active ? 'var(--bg-elev)' : 'var(--text-2)',
        fontSize: 11.5,
        fontWeight: 500,
        display: 'inline-flex',
        alignItems: 'center',
        gap: 7,
        cursor: 'pointer',
        textTransform: 'capitalize',
        boxShadow: active ? 'none' : 'inset 0 0 0 1px var(--border)',
        height: 32,
      }}
    >
      {swatch && (
        <span
          style={{
            width: 12,
            height: 12,
            borderRadius: 3,
            background: swatch,
            boxShadow: active ? '0 0 0 1px var(--bg-elev)' : '0 0 0 1px var(--border-strong)',
          }}
        />
      )}
      {children}
    </button>
  );
}
