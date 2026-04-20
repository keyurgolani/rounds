import type { ReactNode } from 'react';

type Props = {
  illustration?: ReactNode;
  title: string;
  body?: string;
  primary?: { label: string; onClick: () => void };
  secondary?: { label: string; onClick: () => void };
  tip?: string;
};

export default function EmptyState({
  illustration,
  title,
  body,
  primary,
  secondary,
  tip,
}: Props) {
  return (
    <div className="flex flex-col items-center text-center py-16 px-6">
      {illustration && <div className="mb-6">{illustration}</div>}
      <h2
        className="display-italic"
        style={{ fontSize: 32, margin: 0, fontWeight: 400, letterSpacing: '-0.02em' }}
      >
        {title}
      </h2>
      {body && (
        <p
          style={{
            marginTop: 10,
            fontSize: 13.5,
            color: 'var(--text-2)',
            maxWidth: 480,
            lineHeight: 1.6,
          }}
        >
          {body}
        </p>
      )}
      {(primary || secondary) && (
        <div className="flex gap-2 mt-6">
          {primary && (
            <button
              type="button"
              onClick={primary.onClick}
              style={{
                padding: '9px 16px',
                border: 0,
                borderRadius: 'var(--radius)',
                background: 'var(--accent)',
                color: 'var(--bg-elev)',
                fontSize: 13,
                fontWeight: 500,
              }}
            >
              {primary.label}
            </button>
          )}
          {secondary && (
            <button
              type="button"
              onClick={secondary.onClick}
              style={{
                padding: '9px 16px',
                borderRadius: 'var(--radius)',
                background: 'transparent',
                color: 'var(--text-2)',
                border: 0,
                boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                fontSize: 13,
                fontWeight: 500,
              }}
            >
              {secondary.label}
            </button>
          )}
        </div>
      )}
      {tip && (
        <div
          className="mono mt-5"
          style={{ fontSize: 10.5, color: 'var(--text-4)', letterSpacing: '0.08em' }}
        >
          TIP · {tip.toUpperCase()}
        </div>
      )}
    </div>
  );
}
