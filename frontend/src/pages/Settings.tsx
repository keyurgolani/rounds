import { type ReactNode } from 'react';
import PageHeader from '../components/shell/PageHeader';
import { useTheme, type Tweaks } from '../theme/ThemeProvider';
import { useAuth } from '../auth/AuthProvider';
import { supabaseEnabled } from '../lib/supabase';

export default function Settings() {
  const t = useTheme();
  const { user } = useAuth();
  const synced = supabaseEnabled && Boolean(user);

  return (
    <div className="h-full overflow-y-auto">
      <PageHeader
        eyebrow="Account · Preferences"
        title="Settings"
        subtitle="Tune the look and feel of Rounds — theme, accent, density, and more."
      >
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
      </PageHeader>

      <div className="mx-auto px-8 py-6" style={{ maxWidth: 920 }}>
        <div className="flex flex-col gap-5">
          <Section label="Theme" help="Warm ink paper (default), a deep forest dark, a sepia mid-tone, or follow the OS setting.">
            {(['light', 'dark', 'sepia', 'system'] as const).map((v) => (
              <Opt
                key={v}
                active={t.theme === v}
                onClick={() => t.setTweak('theme', v)}
              >
                {v}
              </Opt>
            ))}
          </Section>

          <Section
            label="Accent"
            help="Terracotta is the default brand accent. Other accents map onto the same UI — difficulty pills and category colors don't change."
          >
            {(
              [
                ['terracotta', '#C9633F'],
                ['forest', '#2F5D4A'],
                ['ochre', '#B68C2A'],
                ['plum', '#7C3A4E'],
                ['ink', '#181613'],
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
          </Section>

          <Section
            label="Display type"
            help="The font used for italic titles and card display type. Sans-only hides the serif."
          >
            {(
              [
                ['serif-display', 'Instrument Serif'],
                ['fraunces', 'Fraunces'],
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
          </Section>

          <Section label="Density" help="Compact fits more on-screen; spacious gives the type more room to breathe.">
            {(['compact', 'comfortable', 'spacious'] as const).map((v) => (
              <Opt key={v} active={t.density === v} onClick={() => t.setTweak('density', v)}>
                {v}
              </Opt>
            ))}
          </Section>

          <Section label="Navigation" help="Sidebar keeps nav out of the content column; top bar frees horizontal space for wide pages like Coding.">
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
          </Section>

          <Section
            label="Cards"
            help="Layered is the default — a hairline border plus a soft elevation shadow. Bordered drops the shadow; flat drops both."
          >
            {(['layered', 'bordered', 'flat'] as const).map((v) => (
              <Opt
                key={v}
                active={t.cardTreatment === v}
                onClick={() => t.setTweak('cardTreatment', v)}
              >
                {v}
              </Opt>
            ))}
          </Section>
        </div>

        {synced && (
          <div
            className="mono mt-10"
            style={{ fontSize: 10.5, color: 'var(--text-4)', letterSpacing: '0.12em' }}
          >
            SETTINGS SYNC TO YOUR ACCOUNT
          </div>
        )}
      </div>
    </div>
  );
}

function Section({
  label,
  help,
  children,
}: {
  label: string;
  help: string;
  children: ReactNode;
}) {
  return (
    <div className="card p-5 grid gap-4" style={{ gridTemplateColumns: '220px 1fr' }}>
      <div>
        <div className="eyebrow mb-1.5">{label}</div>
        <p style={{ margin: 0, fontSize: 12.5, color: 'var(--text-3)', lineHeight: 1.55 }}>{help}</p>
      </div>
      <div className="flex gap-2 flex-wrap">{children}</div>
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
        padding: swatch ? '8px 14px 8px 8px' : '8px 14px',
        border: 0,
        borderRadius: 'var(--radius)',
        background: active ? 'var(--accent)' : 'var(--bg-sunken)',
        color: active ? 'var(--bg-elev)' : 'var(--text-2)',
        fontSize: 12,
        fontWeight: 500,
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
        cursor: 'pointer',
        textTransform: 'capitalize',
        boxShadow: active ? 'none' : 'inset 0 0 0 1px var(--border)',
        height: 34,
      }}
    >
      {swatch && (
        <span
          style={{
            width: 14,
            height: 14,
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
