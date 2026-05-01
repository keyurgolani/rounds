import type { ReactNode } from 'react';

type Props = {
  eyebrow: string;
  value: ReactNode;
  hint?: string;
  onClick?: () => void;
};

export default function StatCard({ eyebrow, value, hint, onClick }: Props) {
  const clickable = Boolean(onClick);
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!clickable}
      className={`card text-left p-5 fade-up ${clickable ? 'card-hover' : ''}`}
      style={{
        border: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
        cursor: clickable ? 'pointer' : 'default',
        width: '100%',
      }}
    >
      <span className="eyebrow">{eyebrow}</span>
      <span
        className="display-italic"
        style={{ fontSize: 48, lineHeight: 1, fontWeight: 400, color: 'var(--text)' }}
      >
        {value}
      </span>
      {hint && (
        <span style={{ fontSize: 12, color: 'var(--text-3)', lineHeight: 1.5 }}>{hint}</span>
      )}
    </button>
  );
}
