// Design controls — typography, color, spacing.
//
// Template selection has its own tool now (`TemplatesTab`); Design is
// the look-and-feel layer that applies *on top of* whichever template
// is active. Each knob maps directly to a `TemplateConfig` field that
// every built-in template honors; nothing in here is dead code.

import type { TemplateConfig } from '../types';

type Props = {
  design: TemplateConfig;
  setDesign: (next: TemplateConfig | ((prev: TemplateConfig) => TemplateConfig)) => void;
};

const ACCENT_PRESETS: { key: string; hex: string }[] = [
  { key: 'steel', hex: '#1f3b56' },
  { key: 'forest', hex: '#2F5D4A' },
  { key: 'plum', hex: '#7C3A4E' },
  { key: 'ochre', hex: '#B68C2A' },
  { key: 'terracotta', hex: '#C9633F' },
  { key: 'ink', hex: '#0f172a' },
];

// Human label + a sample glyph that previews the marker exactly as the
// resume CSS will render it. Kept in sync with the rules in
// templates/parts.tsx → RESUME_PAGE_CSS.
type BulletStyle = NonNullable<TemplateConfig['bulletStyle']>;
const BULLET_PRESETS: { key: BulletStyle; label: string; glyph: string }[] = [
  { key: 'disc', label: 'Disc', glyph: '•' },
  { key: 'circle', label: 'Circle', glyph: '◦' },
  { key: 'square', label: 'Square', glyph: '▪' },
  { key: 'dot', label: 'Dot', glyph: '·' },
  { key: 'dash', label: 'Dash', glyph: '–' },
  { key: 'arrow', label: 'Arrow', glyph: '›' },
  { key: 'arrow-long', label: 'Arrow long', glyph: '→' },
  { key: 'chevron', label: 'Chevron', glyph: '»' },
  { key: 'triangle', label: 'Triangle', glyph: '▸' },
  { key: 'check', label: 'Check', glyph: '✓' },
  { key: 'star', label: 'Star', glyph: '★' },
  { key: 'star-outline', label: 'Star outline', glyph: '☆' },
  { key: 'diamond', label: 'Diamond', glyph: '◆' },
  { key: 'plus', label: 'Plus', glyph: '+' },
  { key: 'asterisk', label: 'Asterisk', glyph: '∗' },
  { key: 'none', label: 'None', glyph: '—' },
];

export default function DesignSidebar({ design, setDesign }: Props) {
  const margin = design.spacing?.margin ?? 14;
  const fontSize = design.typography?.body?.size ?? 10.5;
  const accent = design.colors?.primary;
  const bullet = design.bulletStyle ?? 'disc';

  const setMargin = (mm: number) =>
    setDesign((prev) => ({ ...prev, spacing: { ...prev.spacing, margin: mm } }));
  const setFontSize = (px: number) =>
    setDesign((prev) => ({
      ...prev,
      typography: { ...prev.typography, body: { ...prev.typography?.body, size: px } },
    }));
  const setAccent = (hex: string | undefined) =>
    setDesign((prev) => ({ ...prev, colors: { ...prev.colors, primary: hex } }));
  const setBullet = (next: BulletStyle) =>
    setDesign((prev) => ({ ...prev, bulletStyle: next }));

  return (
    <div className="flex flex-col gap-4">
      <Section title="Accent color" hint="Drives section heads and the name bar in templates that color them.">
        <div className="flex flex-wrap gap-2">
          <ResetSwatch active={!accent} onClick={() => setAccent(undefined)} />
          {ACCENT_PRESETS.map((p) => (
            <Swatch
              key={p.key}
              hex={p.hex}
              label={p.key}
              active={accent?.toLowerCase() === p.hex.toLowerCase()}
              onClick={() => setAccent(p.hex)}
            />
          ))}
          <input
            type="color"
            aria-label="Custom accent"
            value={accent ?? '#1f3b56'}
            onChange={(e) => setAccent(e.target.value)}
            style={{
              width: 32,
              height: 32,
              padding: 0,
              border: 0,
              background: 'transparent',
              cursor: 'pointer',
            }}
          />
        </div>
      </Section>

      <Section title="Body size" hint={`${fontSize.toFixed(1)} pt — affects density on the page.`}>
        <input
          type="range"
          min={9}
          max={12}
          step={0.5}
          value={fontSize}
          onChange={(e) => setFontSize(Number(e.target.value))}
          style={{ width: '100%', accentColor: 'var(--accent)' }}
          aria-label="Body font size"
        />
      </Section>

      <Section title="Page margin" hint={`${margin} mm — smaller margins fit more content per page.`}>
        <input
          type="range"
          min={8}
          max={22}
          step={1}
          value={margin}
          onChange={(e) => setMargin(Number(e.target.value))}
          style={{ width: '100%', accentColor: 'var(--accent)' }}
          aria-label="Page margin"
        />
      </Section>

      <Section title="Bullet style" hint="Marker for highlight lists in experience and projects.">
        <div className="flex flex-wrap gap-1.5">
          {BULLET_PRESETS.map((b) => (
            <BulletChip
              key={b.key}
              label={b.label}
              glyph={b.glyph}
              active={bullet === b.key}
              onClick={() => setBullet(b.key)}
            />
          ))}
        </div>
      </Section>
    </div>
  );
}

function BulletChip({
  label,
  glyph,
  active,
  onClick,
}: {
  label: string;
  glyph: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={`Bullet ${label}`}
      aria-pressed={active}
      title={label}
      className="inline-flex items-center gap-1.5"
      style={{
        padding: '6px 10px',
        borderRadius: 8,
        background: active ? 'var(--ink)' : 'transparent',
        color: active ? 'var(--paper)' : 'var(--text-2)',
        boxShadow: active
          ? '0 0 0 2px var(--accent)'
          : 'inset 0 0 0 1px var(--border-strong)',
        border: 0,
        fontSize: 11.5,
        fontWeight: 500,
        cursor: 'pointer',
      }}
    >
      <span
        style={{
          display: 'inline-block',
          width: 12,
          textAlign: 'center',
          fontSize: 13,
          lineHeight: 1,
        }}
      >
        {glyph}
      </span>
      {label}
    </button>
  );
}

function Section({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2">
      <div>
        <div className="eyebrow" style={{ fontSize: 9.5 }}>
          {title}
        </div>
        {hint && (
          <p style={{ margin: '2px 0 0 0', fontSize: 11, color: 'var(--text-4)', lineHeight: 1.4 }}>
            {hint}
          </p>
        )}
      </div>
      {children}
    </div>
  );
}

function Swatch({
  hex,
  label,
  active,
  onClick,
}: {
  hex: string;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={label}
      aria-label={`Accent ${label}`}
      style={{
        width: 32,
        height: 32,
        borderRadius: 8,
        background: hex,
        border: 0,
        boxShadow: active ? '0 0 0 2px var(--accent)' : 'inset 0 0 0 1px var(--border-strong)',
        cursor: 'pointer',
      }}
    />
  );
}

function ResetSwatch({ active, onClick }: { active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title="Reset to template default"
      aria-label="Reset accent"
      style={{
        width: 32,
        height: 32,
        borderRadius: 8,
        background: 'var(--bg-elev)',
        border: 0,
        boxShadow: active ? '0 0 0 2px var(--accent)' : 'inset 0 0 0 1px var(--border-strong)',
        cursor: 'pointer',
        fontSize: 10,
        color: 'var(--text-3)',
      }}
    >
      ✕
    </button>
  );
}
