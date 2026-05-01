import type { CodeRunResult } from './types';

interface ConsoleTabProps {
  result?: CodeRunResult;
}

export function ConsoleTab({ result }: ConsoleTabProps) {
  if (!result) {
    return (
      <div className="mono" style={{ fontSize: 12, color: 'var(--text-4)' }}>
        stdout/stderr will appear here after a Run.
      </div>
    );
  }
  const hasOut = result.stdout && result.stdout.length > 0;
  const hasErr = result.stderr && result.stderr.length > 0;
  if (!hasOut && !hasErr) {
    return (
      <div className="mono" style={{ fontSize: 12, color: 'var(--text-4)' }}>
        (no console output)
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      {hasOut && (
        <div>
          <div className="eyebrow" style={{ marginBottom: 4 }}>
            stdout
          </div>
          <pre
            className="mono"
            style={{
              fontSize: 12,
              color: 'var(--text-2)',
              background: 'var(--bg-sunken)',
              padding: 10,
              borderRadius: 'var(--radius)',
              margin: 0,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {result.stdout}
          </pre>
        </div>
      )}
      {hasErr && (
        <div>
          <div className="eyebrow" style={{ marginBottom: 4 }}>
            stderr
          </div>
          <pre
            className="mono"
            style={{
              fontSize: 12,
              color: 'var(--plum)',
              background: 'var(--bg-sunken)',
              padding: 10,
              borderRadius: 'var(--radius)',
              margin: 0,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {result.stderr}
          </pre>
        </div>
      )}
      {result.truncated && (
        <div className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)' }}>
          (output truncated)
        </div>
      )}
    </div>
  );
}
