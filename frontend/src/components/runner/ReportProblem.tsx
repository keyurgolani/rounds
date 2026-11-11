// A submission report that can't show (ROUNDS-00A-L03 PR 3): a grade
// that failed with nothing to show for it, or a graded row this page
// couldn't read. It says what happened in a fixed sentence and offers to
// try again where that can help. It never shows a score, a verdict, or
// the server's own text.

import { CircleAlert, RotateCcw } from 'lucide-react';

interface ReportProblemProps {
  title: string;
  body: string;
  onRetry?: () => void;
}

export function ReportProblem({ title, body, onRetry }: ReportProblemProps) {
  return (
    <div
      role="alert"
      data-testid="report-problem"
      style={{
        display: 'flex',
        gap: 10,
        alignItems: 'flex-start',
        padding: '12px 14px',
        borderRadius: 'var(--radius)',
        background: 'var(--bg-elev)',
        boxShadow: 'inset 0 0 0 1px var(--border-strong)',
        fontSize: 13,
        lineHeight: 1.5,
        color: 'var(--text-2)',
      }}
    >
      <CircleAlert
        aria-hidden="true"
        size={16}
        strokeWidth={1.8}
        style={{ flexShrink: 0, marginTop: 2, color: 'var(--status-warn)' }}
      />
      <div style={{ minWidth: 0, flex: 1 }}>
        <strong style={{ display: 'block', color: 'var(--text)', fontWeight: 600 }}>
          {title}
          <span className="sr-only">. </span>
        </strong>
        <span>{body}</span>
        {onRetry && (
          <div style={{ marginTop: 10 }}>
            <button
              type="button"
              onClick={onRetry}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                minHeight: 32,
                padding: '6px 12px',
                borderRadius: 'var(--radius)',
                border: 0,
                background: 'transparent',
                boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                color: 'var(--text)',
                fontSize: 12,
                fontWeight: 500,
                cursor: 'pointer',
              }}
            >
              <RotateCcw aria-hidden="true" size={12} strokeWidth={1.8} />
              Try again
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
