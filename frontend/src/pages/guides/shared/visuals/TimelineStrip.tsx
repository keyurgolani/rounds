import type { ReactNode } from 'react';

export type TimelinePhase = {
  id: string;
  label: string;
  caption?: string;     // optional sub-label (e.g. minutes range)
  body?: ReactNode;     // optional under-card body
};

export default function TimelineStrip({
  phases,
  caption,
  activeIndex = 0,
}: {
  phases: TimelinePhase[];
  caption?: string;
  /** Which phase shows the filled accent badge. Defaults to the first. */
  activeIndex?: number;
}) {
  return (
    <div className="grid" style={{ gap: 'var(--gap-sm)' }}>
      {caption && <div className="eyebrow">{caption}</div>}
      <ol
        className="flex"
        style={{
          gap: 'var(--gap-sm)',
          overflowX: 'auto',
          paddingBottom: 6,
          margin: 0,
          listStyle: 'none',
        }}
      >
        {phases.map((phase, index) => (
          <li
            key={phase.id}
            className="grid"
            style={{
              gap: 6,
              minWidth: 168,
              padding: 'var(--pad-sm)',
              borderRadius: 'var(--radius)',
              background: 'var(--bg-elev)',
              boxShadow: 'inset 0 0 0 1px var(--border)',
            }}
          >
            <div className="flex items-center" style={{ gap: 6 }}>
              <span
                className="mono"
                style={{
                  width: 22,
                  height: 22,
                  display: 'inline-grid',
                  placeItems: 'center',
                  borderRadius: 999,
                  background: index === activeIndex ? 'var(--accent)' : 'var(--accent-soft)',
                  color: index === activeIndex ? 'var(--bg-elev)' : 'var(--accent)',
                  fontSize: 10,
                }}
              >
                {String(index + 1).padStart(2, '0')}
              </span>
              {phase.caption && (
                <span className="mono" style={{ color: 'var(--text-4)', fontSize: 10.5, letterSpacing: '0.1em' }}>
                  {phase.caption.toUpperCase()}
                </span>
              )}
            </div>
            <strong style={{ fontSize: 14, lineHeight: 1.25, fontWeight: 600, color: 'var(--text)' }}>
              {phase.label}
            </strong>
            {phase.body && (
              <div style={{ color: 'var(--text-3)', fontSize: 12.5, lineHeight: 1.45 }}>
                {phase.body}
              </div>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
