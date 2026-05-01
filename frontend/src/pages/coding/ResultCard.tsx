import type { ReactNode } from 'react';
import { formatValue } from './format';

export type ResultStatus = 'pass' | 'fail' | 'error' | 'timeout' | 'pending';

interface ResultCardProps {
  status: ResultStatus;
  input?: unknown;
  output?: unknown;
  expected?: unknown;
  reason?: string | null;
  stdout?: string;
  stderr?: string;
  durationMs?: number;
  description?: string;
  /** Optional kind-aware renderer; if absent, JSON.stringify is used. */
  renderValue?: (label: 'input' | 'output' | 'expected', value: unknown) => ReactNode;
}

const STATUS_LABELS: Record<ResultStatus, string> = {
  pass: 'PASS',
  fail: 'FAIL',
  error: 'ERROR',
  timeout: 'TIMEOUT',
  pending: '—',
};

const STATUS_COLORS: Record<ResultStatus, string> = {
  pass: 'var(--status-pass)',
  fail: 'var(--status-fail)',
  error: 'var(--status-fail)',
  timeout: 'var(--status-warn)',
  pending: 'var(--text-4)',
};

function defaultRender(value: unknown): ReactNode {
  if (value === undefined) return '(empty)';
  try {
    return formatValue(value);
  } catch {
    return String(value);
  }
}

function Block({
  label,
  children,
  tone,
}: {
  label: string;
  children: ReactNode;
  tone?: 'neutral' | 'bad' | 'accent';
}) {
  const fg =
    tone === 'bad' ? 'var(--status-fail)' : tone === 'accent' ? 'var(--accent)' : 'var(--text-2)';
  return (
    <div
      className="grid gap-3"
      style={{
        gridTemplateColumns: '72px minmax(0, 1fr)',
        padding: '10px 14px',
        borderBottom: '1px dashed var(--border)',
      }}
    >
      <span
        className="mono uppercase"
        style={{
          fontSize: 9.5,
          color: 'var(--text-4)',
          letterSpacing: '0.12em',
          paddingTop: 3,
        }}
      >
        {label}
      </span>
      <pre
        className="mono"
        style={{
          margin: 0,
          fontSize: 12,
          color: fg,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}
      >
        {children}
      </pre>
    </div>
  );
}

export function ResultCard({
  status,
  input,
  output,
  expected,
  reason,
  stdout,
  stderr,
  durationMs,
  description,
  renderValue,
}: ResultCardProps) {
  const render = (label: 'input' | 'output' | 'expected', v: unknown) =>
    renderValue ? renderValue(label, v) : defaultRender(v);

  return (
    <div className="card overflow-hidden">
      <div
        className="flex items-center justify-between"
        style={{
          padding: '10px 14px',
          background: 'var(--bg-sunken)',
          borderBottom: '1px solid var(--border)',
        }}
      >
        <div className="flex items-center gap-2">
          <span
            className="mono uppercase"
            style={{
              fontSize: 9.5,
              fontWeight: 600,
              color: STATUS_COLORS[status],
              letterSpacing: '0.12em',
            }}
          >
            {STATUS_LABELS[status]}
          </span>
          {description && (
            <span style={{ fontSize: 11.5, color: 'var(--text-3)' }}>{description}</span>
          )}
        </div>
        {durationMs !== undefined && (
          <span className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)' }}>
            {durationMs}ms
          </span>
        )}
      </div>

      {input !== undefined && <Block label="Input">{render('input', input)}</Block>}
      {output !== undefined && (
        <Block label="Output" tone="accent">
          {render('output', output)}
        </Block>
      )}
      {expected !== undefined && status !== 'pass' && (
        <Block label="Expected">{render('expected', expected)}</Block>
      )}
      {reason && (
        <Block label="Reason" tone="bad">
          {reason}
        </Block>
      )}
      {stdout && <Block label="stdout">{stdout}</Block>}
      {stderr && (
        <Block label="stderr" tone="bad">
          {stderr}
        </Block>
      )}
    </div>
  );
}
