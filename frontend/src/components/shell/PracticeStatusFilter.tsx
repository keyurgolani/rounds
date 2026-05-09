import type { PracticeStatus } from './StatusDot';

// Filter equivalent of PracticeStatusControl. Same visual language as
// the detail-page status pill (so users recognize it as the filter
// counterpart), but with a fourth "All" option that disables filtering.
//
// Mirrors PracticeStatusControl's color scheme:
//   - All        → neutral (no dot)
//   - Not started→ outlined gray dot
//   - Practicing → ochre filled dot
//   - Mastered   → forest filled dot
//
// `compact` mode swaps text labels for icons-only so the filter still
// fits the 44px minimal/mobile header alongside the chrome buttons.

export type PracticeStatusFilterValue = 'all' | PracticeStatus;

type Props = {
  value: PracticeStatusFilterValue;
  onChange: (next: PracticeStatusFilterValue) => void;
  compact?: boolean;
};

const OPTS: {
  key: PracticeStatusFilterValue;
  label: string;
  short: string;
  color: string;
  fill: string;
}[] = [
  { key: 'all', label: 'All', short: 'All', color: 'var(--text-3)', fill: 'transparent' },
  {
    key: 'todo',
    label: 'Not started',
    short: 'Not started',
    color: 'var(--text-4)',
    fill: 'transparent',
  },
  {
    key: 'in-progress',
    label: 'Practicing',
    short: 'Practicing',
    color: 'var(--ochre)',
    fill: 'var(--ochre)',
  },
  {
    key: 'mastered',
    label: 'Mastered',
    short: 'Mastered',
    color: 'var(--forest)',
    fill: 'var(--forest)',
  },
];

export default function PracticeStatusFilter({ value, onChange, compact = false }: Props) {
  const pad = compact ? '0 7px' : '0 11px';
  const h = compact ? 22 : 24;
  const fs = compact ? 11 : 12;
  return (
    <div
      role="radiogroup"
      aria-label="Filter questions by practice status"
      className="inline-flex gap-0.5"
      style={{
        padding: 3,
        borderRadius: 8,
        background: 'var(--bg-sunken)',
        boxShadow: 'inset 0 0 0 1px var(--border)',
      }}
    >
      {OPTS.map((o) => {
        const on = value === o.key;
        const isAll = o.key === 'all';
        return (
          <button
            key={o.key}
            type="button"
            role="radio"
            aria-checked={on}
            onClick={() => onChange(o.key)}
            title={o.label}
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
              cursor: 'pointer',
              transition: 'all 120ms',
            }}
          >
            {!isAll && (
              <span
                aria-hidden="true"
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
            )}
            {compact ? (
              isAll ? (
                <span>All</span>
              ) : null
            ) : (
              o.label
            )}
          </button>
        );
      })}
    </div>
  );
}
