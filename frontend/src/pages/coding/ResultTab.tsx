import type { CodeRunResult } from './types';
import { ResultCard, type ResultStatus } from './ResultCard';

interface ResultTabProps {
  /** Last single-run output. */
  runResult?: CodeRunResult;
  /** Input that produced runResult, for display. */
  runInput?: unknown;
}

function statusFor(r: CodeRunResult): ResultStatus {
  if (r.error?.startsWith('Time limit')) return 'timeout';
  if (r.error) return 'error';
  return 'pass';
}

// Bottom-half of the Run tab: shows the result of the most recent
// custom-input run (no console — that lives in the bottom dock).
export function ResultTab({ runResult, runInput }: ResultTabProps) {
  if (!runResult) {
    return (
      <div className="mono" style={{ fontSize: 12, color: 'var(--text-4)' }}>
        Run a case to see the result.
      </div>
    );
  }
  return (
    <ResultCard
      status={statusFor(runResult)}
      input={runInput}
      output={runResult.error ? undefined : runResult.return_value}
      reason={runResult.error}
      durationMs={runResult.duration_ms}
    />
  );
}
