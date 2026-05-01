import { type ReactNode } from 'react';
import { useTheme, type Tweaks } from '../../theme/ThemeProvider';

const themeOptions: [Tweaks['theme'], string][] = [
  ['light', 'Light'],
  ['dark', 'Dark'],
  ['sepia', 'Sepia'],
  ['ocean', 'Ocean'],
  ['slate', 'Slate'],
  ['rose', 'Rose'],
  ['mono', 'Mono'],
  ['system', 'System'],
];

const accentOptions: [Tweaks['accent'], string][] = [
  ['terracotta', '#C9633F'],
  ['forest', '#2F5D4A'],
  ['ochre', '#B68C2A'],
  ['plum', '#7C3A4E'],
  ['ink', '#181613'],
  ['indigo', '#4C5FD6'],
  ['teal', '#147A6B'],
  ['rose', '#C7305F'],
];

const displayOptions: [Tweaks['typeVariant'], string][] = [
  ['serif-display', 'Instrument Serif'],
  ['fraunces', 'Fraunces'],
  ['playfair', 'Playfair'],
  ['dm-serif', 'DM Serif'],
  ['sans-only', 'Sans only'],
];

const sansOptions: [Tweaks['sansFont'], string][] = [
  ['inter', 'Inter'],
  ['geist', 'Geist'],
  ['manrope', 'Manrope'],
  ['space-grotesk', 'Space Grotesk'],
  ['system', 'System'],
];

const radiusOptions: [Tweaks['radius'], string][] = [
  ['sharp', 'Sharp'],
  ['soft', 'Soft'],
  ['round', 'Round'],
  ['pill', 'Pill'],
];

const shadowOptions: [Tweaks['shadow'], string][] = [
  ['none', 'None'],
  ['subtle', 'Subtle'],
  ['soft', 'Soft'],
  ['bold', 'Bold'],
];

const cardOptions: [Tweaks['cardTreatment'], string][] = [
  ['layered', 'Layered'],
  ['bordered', 'Bordered'],
  ['flat', 'Flat'],
  ['filled', 'Filled'],
];

const backgroundOptions: [Tweaks['appBackground'], string][] = [
  ['grainy', 'Grainy'],
  ['mesh', 'Mesh'],
  ['gradient', 'Gradient'],
  ['paper', 'Paper'],
  ['natural', 'Natural'],
];

const cardAccentOptions: [Tweaks['cardAccent'], string][] = [
  ['neutral', 'Neutral'],
  ['tinted', 'Tinted'],
  ['ruled', 'Ruled'],
];

const densityOptions: Tweaks['density'][] = ['compact', 'comfortable', 'spacious'];

const navOptions: [Tweaks['navStyle'], string][] = [
  ['sidebar', 'Sidebar'],
  ['topbar', 'Top bar'],
];

export default function ThemeView({ onComplete }: { onComplete: () => void }) {
  const t = useTheme();

  return (
    <div className="flex flex-col gap-4">
      <Group label="Theme">
        {themeOptions.map(([k, label]) => (
          <Opt key={k} active={t.theme === k} onClick={() => t.setTweak('theme', k)}>
            {label}
          </Opt>
        ))}
      </Group>

      <Group label="Accent">
        {accentOptions.map(([k, swatch]) => (
          <Opt
            key={k}
            active={t.accent === k}
            onClick={() => t.setTweak('accent', k)}
            swatch={swatch}
          >
            {k}
          </Opt>
        ))}
      </Group>

      <Group label="Display type">
        {displayOptions.map(([k, label]) => (
          <Opt
            key={k}
            active={t.typeVariant === k}
            onClick={() => t.setTweak('typeVariant', k)}
          >
            {label}
          </Opt>
        ))}
      </Group>

      <Group label="Body font">
        {sansOptions.map(([k, label]) => (
          <Opt
            key={k}
            active={t.sansFont === k}
            onClick={() => t.setTweak('sansFont', k)}
          >
            {label}
          </Opt>
        ))}
      </Group>

      <Group label="Corners">
        {radiusOptions.map(([k, label]) => (
          <Opt key={k} active={t.radius === k} onClick={() => t.setTweak('radius', k)}>
            {label}
          </Opt>
        ))}
      </Group>

      <Group label="Shadow">
        {shadowOptions.map(([k, label]) => (
          <Opt key={k} active={t.shadow === k} onClick={() => t.setTweak('shadow', k)}>
            {label}
          </Opt>
        ))}
      </Group>

      <Group label="Cards">
        {cardOptions.map(([k, label]) => (
          <Opt
            key={k}
            active={t.cardTreatment === k}
            onClick={() => t.setTweak('cardTreatment', k)}
          >
            {label}
          </Opt>
        ))}
      </Group>

      <SliderGroup
        label="Glass effect"
        value={t.glassTransparency}
        onChange={(v) => t.setTweak('glassTransparency', v)}
      />
      <SliderGroup
        label="Glass frost"
        value={t.glassFrost}
        onChange={(v) => t.setTweak('glassFrost', v)}
      />
      <SliderGroup
        label="Glass shadow"
        value={t.glassShadow}
        onChange={(v) => t.setTweak('glassShadow', v)}
      />

      <Group label="Background">
        {backgroundOptions.map(([k, label]) => (
          <Opt
            key={k}
            active={t.appBackground === k}
            onClick={() => t.setTweak('appBackground', k)}
          >
            {label}
          </Opt>
        ))}
      </Group>

      <Group label="Card accent">
        {cardAccentOptions.map(([k, label]) => (
          <Opt
            key={k}
            active={t.cardAccent === k}
            onClick={() => t.setTweak('cardAccent', k)}
          >
            {label}
          </Opt>
        ))}
      </Group>

      <Group label="Density">
        {densityOptions.map((v) => (
          <Opt key={v} active={t.density === v} onClick={() => t.setTweak('density', v)}>
            {v}
          </Opt>
        ))}
      </Group>

      <Group label="Navigation">
        {navOptions.map(([k, label]) => (
          <Opt key={k} active={t.navStyle === k} onClick={() => t.setTweak('navStyle', k)}>
            {label}
          </Opt>
        ))}
      </Group>

      <div
        className="flex items-center justify-between gap-3 pt-3"
        style={{ borderTop: '1px solid var(--border)' }}
      >
        <button
          type="button"
          onClick={t.reset}
          className="mono uppercase"
          style={{
            padding: '7px 12px',
            borderRadius: 'var(--radius)',
            border: 0,
            background: 'transparent',
            boxShadow: 'inset 0 0 0 1px var(--border)',
            color: 'var(--text-3)',
            fontSize: 10.5,
            letterSpacing: '0.12em',
            cursor: 'pointer',
          }}
        >
          Reset to default
        </button>
        <button
          type="button"
          onClick={onComplete}
          style={{
            padding: '8px 14px',
            borderRadius: 'var(--radius)',
            border: 0,
            background: 'var(--accent)',
            color: 'var(--bg-elev)',
            fontSize: 12.5,
            fontWeight: 500,
            cursor: 'pointer',
          }}
        >
          Done
        </button>
      </div>
    </div>
  );
}

function Group({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="eyebrow" style={{ fontSize: 9.5 }}>
        {label}
      </span>
      <div className="flex gap-1.5 flex-wrap">{children}</div>
    </div>
  );
}

function SliderGroup({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="eyebrow" style={{ fontSize: 9.5 }}>
        {label}
      </span>
      <div className="flex items-center gap-3">
        <input
          type="range"
          min={0}
          max={100}
          step={1}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          aria-label={label}
          style={{
            flex: 1,
            height: 4,
            accentColor: 'var(--accent)',
            cursor: 'pointer',
          }}
        />
        <span
          className="mono"
          style={{ width: 32, fontSize: 11, color: 'var(--text-3)', textAlign: 'right' }}
        >
          {value}
        </span>
      </div>
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
        padding: swatch ? '6px 11px 6px 6px' : '6px 11px',
        border: 0,
        borderRadius: 'var(--radius)',
        background: active ? 'var(--accent)' : 'var(--bg-sunken)',
        color: active ? 'var(--bg-elev)' : 'var(--text-2)',
        fontSize: 11,
        fontWeight: 500,
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        cursor: 'pointer',
        textTransform: 'capitalize',
        boxShadow: active ? 'none' : 'inset 0 0 0 1px var(--border)',
        height: 28,
      }}
    >
      {swatch && (
        <span
          style={{
            width: 11,
            height: 11,
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
