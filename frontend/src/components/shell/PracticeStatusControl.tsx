import type { PracticeStatus } from './StatusDot';

type Props = {
  status: PracticeStatus;
  onChange: (s: PracticeStatus) => void;
  size?: 'sm' | 'md';
  compact?: boolean;
};

const opts: { key: PracticeStatus; label: string; color: string; fill: string }[] = [
  { key: 'todo', label: 'Not started', color: 'var(--text-4)', fill: 'transparent' },
  { key: 'in-progress', label: 'Practicing', color: 'var(--ochre)', fill: 'var(--ochre)' },
  { key: 'mastered', label: 'Mastered', color: 'var(--forest)', fill: 'var(--forest)' },
];

const ORDER: PracticeStatus[] = ['todo', 'in-progress', 'mastered'];

function nextStatus(s: PracticeStatus): PracticeStatus {
  const i = ORDER.indexOf(s);
  return ORDER[(i + 1) % ORDER.length];
}

export default function PracticeStatusControl({
  status,
  onChange,
  size = 'md',
  compact = false,
}: Props) {
  if (compact) {
    const cur = opts.find((o) => o.key === status) ?? opts[0];
    // For the empty `todo` state, use a darker ring so the dot reads at
    // a glance against the sunken button background.
    const ringColor = cur.key === 'todo' ? 'var(--text-3)' : cur.color;
    return (
      <button
        type="button"
        onClick={() => onChange(nextStatus(status))}
        title={cur.label}
        aria-label={`Practice status: ${cur.label}. Press to cycle to next.`}
        className="inline-flex items-center justify-center"
        style={{
          width: 28,
          height: 28,
          padding: 0,
          borderRadius: 999,
          background: 'var(--bg-sunken)',
          boxShadow: 'inset 0 0 0 1px var(--border)',
          border: 0,
          cursor: 'pointer',
        }}
      >
        <span
          style={{
            width: 9,
            height: 9,
            borderRadius: 999,
            background: cur.fill === 'transparent' ? 'transparent' : cur.fill,
            boxShadow:
              cur.fill === 'transparent'
                ? `inset 0 0 0 1px ${ringColor}`
                : 'none',
          }}
        />
      </button>
    );
  }

  // Existing 3-pill behavior preserved as-is below this point.
  const pad = size === 'sm' ? '0 9px' : '0 11px';
  const h = size === 'sm' ? 22 : 24;
  const fs = size === 'sm' ? 11 : 12;
  return (
    <div
      className="inline-flex gap-0.5"
      style={{
        padding: 3,
        borderRadius: 8,
        background: 'var(--bg-sunken)',
        boxShadow: 'inset 0 0 0 1px var(--border)',
      }}
    >
      {opts.map((o) => {
        const on = status === o.key;
        return (
          <button
            key={o.key}
            type="button"
            onClick={() => onChange(o.key)}
            className="inline-flex items-center gap-1.5"
            style={{
              height: h,
              padding: pad,
              border: 0,
              borderRadius: 5,
              background: on ? 'var(--bg-elev)' : 'transparent',
              boxShadow: on ? '0 1px 2px rgba(24,22,19,0.08)' : 'none',
              color: on ? o.color : 'var(--text-3)',
              fontSize: fs,
              fontWeight: 500,
              transition: 'all 120ms',
            }}
          >
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: 999,
                background: on ? o.fill : 'transparent',
                boxShadow:
                  o.key === 'todo' && on
                    ? `inset 0 0 0 1px ${o.color}`
                    : !on
                      ? 'inset 0 0 0 1px var(--text-4)'
                      : 'none',
              }}
            />
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
