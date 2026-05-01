import { useState, type CSSProperties, type ReactNode } from 'react';
import { useTheme, type Tweaks } from './ThemeProvider';

export default function TweaksPanel() {
  const [open, setOpen] = useState(false);
  const t = useTheme();

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Open theme tweaks"
        style={{
          position: 'fixed',
          bottom: 18,
          right: 18,
          width: 40,
          height: 40,
          borderRadius: 999,
          border: 0,
          background: 'var(--bg-elev)',
          boxShadow: 'var(--shadow-elev)',
          color: 'var(--text-2)',
          cursor: 'pointer',
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <svg viewBox="0 0 20 20" width="18" height="18" fill="none" aria-hidden="true">
          <circle cx="10" cy="10" r="3" stroke="currentColor" strokeWidth="1.4" />
          <path
            d="M10 2v2M10 16v2M2 10h2M16 10h2M4.2 4.2l1.4 1.4M14.4 14.4l1.4 1.4M4.2 15.8l1.4-1.4M14.4 5.6l1.4-1.4"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
          />
        </svg>
      </button>
    );
  }

  return (
    <div
      className="fade-up"
      style={{
        position: 'fixed',
        bottom: 20,
        right: 20,
        width: 284,
        maxHeight: 'calc(100vh - 40px)',
        overflowY: 'auto',
        zIndex: 1000,
        background: 'var(--bg-elev)',
        borderRadius: 10,
        boxShadow: 'var(--shadow-elev)',
        overflowX: 'hidden',
      }}
    >
      <div
        className="flex items-center justify-between"
        style={{
          padding: '12px 14px',
          background: 'var(--ink)',
          color: '#F7F2E7',
        }}
      >
        <span className="display-italic" style={{ fontSize: 17 }}>
          Tweaks
        </span>
        <div className="flex items-center gap-3">
          <span
            className="mono uppercase"
            style={{ fontSize: 9.5, opacity: 0.55, letterSpacing: '0.12em' }}
          >
            Live
          </span>
          <button
            type="button"
            onClick={() => setOpen(false)}
            aria-label="Close"
            style={{
              border: 0,
              background: 'transparent',
              color: '#F7F2E7',
              fontSize: 14,
              cursor: 'pointer',
              opacity: 0.7,
            }}
          >
            ✕
          </button>
        </div>
      </div>

      <Row label="Theme">
        {(['light', 'dark', 'sepia'] as const).map((v) => (
          <Opt key={v} active={t.theme === v} onClick={() => t.setTweak('theme', v)}>
            {v}
          </Opt>
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

      <Row label="Display type">
        {(
          [
            ['serif-display', 'Instrument'],
            ['fraunces', 'Fraunces'],
            ['sans-only', 'Sans only'],
          ] as [Tweaks['typeVariant'], string][]
        ).map(([k, label]) => (
          <Opt key={k} active={t.typeVariant === k} onClick={() => t.setTweak('typeVariant', k)}>
            {label}
          </Opt>
        ))}
      </Row>

      <Row label="Density">
        {(['compact', 'comfortable', 'spacious'] as const).map((d) => (
          <Opt key={d} active={t.density === d} onClick={() => t.setTweak('density', d)}>
            {d}
          </Opt>
        ))}
      </Row>

      <Row label="Navigation">
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

      <Row label="Cards" last>
        {(['layered', 'bordered', 'flat'] as const).map((c) => (
          <Opt key={c} active={t.cardTreatment === c} onClick={() => t.setTweak('cardTreatment', c)}>
            {c}
          </Opt>
        ))}
      </Row>

      <div style={{ padding: '10px 14px 14px' }}>
        <button
          type="button"
          onClick={t.reset}
          className="mono uppercase"
          style={{
            background: 'transparent',
            border: 0,
            color: 'var(--text-3)',
            fontSize: 10.5,
            letterSpacing: '0.12em',
            cursor: 'pointer',
            padding: 0,
          }}
        >
          Reset to default
        </button>
      </div>
    </div>
  );
}

function Row({ label, children, last }: { label: string; children: ReactNode; last?: boolean }) {
  return (
    <div
      style={{
        padding: '10px 14px',
        borderBottom: last ? 'none' : '1px solid var(--border)',
      }}
    >
      <div className="eyebrow mb-2" style={{ fontSize: 9.5 }}>
        {label}
      </div>
      <div className="flex gap-1.5 flex-wrap">{children}</div>
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
  const style: CSSProperties = {
    padding: swatch ? '6px 10px 6px 6px' : '6px 10px',
    border: 0,
    borderRadius: 4,
    background: active ? 'var(--accent)' : 'var(--bg-sunken)',
    color: active ? 'var(--bg-elev)' : 'var(--text-2)',
    fontSize: 11,
    fontWeight: 500,
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    cursor: 'pointer',
    textTransform: 'capitalize',
  };
  return (
    <button type="button" onClick={onClick} style={style}>
      {swatch && (
        <span
          style={{
            width: 12,
            height: 12,
            borderRadius: 2,
            background: swatch,
            display: 'inline-block',
            boxShadow: active ? '0 0 0 1px var(--bg-elev)' : '0 0 0 1px var(--border)',
          }}
        />
      )}
      {children}
    </button>
  );
}
