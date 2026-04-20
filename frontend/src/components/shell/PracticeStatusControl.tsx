import type { PracticeStatus } from './StatusDot';

type Props = {
  status: PracticeStatus;
  onChange: (s: PracticeStatus) => void;
  size?: 'sm' | 'md';
};

const opts: { key: PracticeStatus; label: string; color: string; fill: string }[] = [
  { key: 'todo', label: 'Todo', color: 'var(--text-4)', fill: 'transparent' },
  { key: 'in-progress', label: 'Practicing', color: 'var(--ochre)', fill: 'var(--ochre)' },
  { key: 'mastered', label: 'Mastered', color: 'var(--forest)', fill: 'var(--forest)' },
];

export default function PracticeStatusControl({ status, onChange, size = 'md' }: Props) {
  const pad = size === 'sm' ? '5px 9px' : '6px 11px';
  const fs = size === 'sm' ? 11 : 12;
  return (
    <div
      className="inline-flex gap-0.5"
      style={{
        padding: 3,
        borderRadius: 999,
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
              padding: pad,
              border: 0,
              borderRadius: 999,
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
