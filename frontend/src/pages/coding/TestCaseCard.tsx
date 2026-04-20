import { Check, ChevronDown, ChevronRight, Circle, Play, X } from 'lucide-react';
import type { TestCase, EvaluateCaseResult } from './types';

interface TestCaseCardProps {
  index: number;
  testCase: TestCase;
  result?: EvaluateCaseResult;
  onEvaluate: (index: number) => void;
  running?: boolean;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function StatusBadge({ result }: { result?: EvaluateCaseResult }) {
  if (!result) {
    return (
      <span
        aria-label="not run"
        className="inline-flex items-center justify-center flex-shrink-0"
        style={{
          width: 20,
          height: 20,
          borderRadius: 999,
          color: 'var(--text-4)',
          boxShadow: 'inset 0 0 0 1px var(--border-strong)',
        }}
      >
        <Circle size={8} strokeWidth={2} />
      </span>
    );
  }
  if (result.passed) {
    return (
      <span
        aria-label="passed"
        className="inline-flex items-center justify-center flex-shrink-0"
        style={{
          width: 20,
          height: 20,
          borderRadius: 999,
          background: 'var(--forest-soft)',
          color: 'var(--forest)',
        }}
      >
        <Check size={12} strokeWidth={2.2} />
      </span>
    );
  }
  return (
    <span
      aria-label="failed"
      className="inline-flex items-center justify-center flex-shrink-0"
      style={{
        width: 20,
        height: 20,
        borderRadius: 999,
        background: 'var(--plum-soft)',
        color: 'var(--plum)',
      }}
    >
      <X size={12} strokeWidth={2.2} />
    </span>
  );
}

function formatValue(v: unknown): string {
  if (v === undefined) return 'undefined';
  try {
    return JSON.stringify(v);
  } catch {
    return String(v);
  }
}

export function TestCaseCard({
  index,
  testCase,
  result,
  onEvaluate,
  running = false,
  open,
  onOpenChange,
}: TestCaseCardProps) {
  const tags = testCase.tags ?? [];

  const failed = result && !result.passed;

  return (
    <div
      className="card overflow-hidden"
      style={{
        boxShadow: failed
          ? '0 0 0 1.5px var(--plum), var(--shadow-card)'
          : 'var(--shadow-card)',
      }}
    >
      <button
        type="button"
        onClick={() => onOpenChange(!open)}
        className="flex items-center gap-3 w-full text-left"
        style={{
          padding: '10px 14px',
          background: 'transparent',
          border: 0,
          cursor: 'pointer',
        }}
      >
        <StatusBadge result={result} />
        <span
          className="mono"
          style={{ fontSize: 11, color: 'var(--text-4)', letterSpacing: '0.06em' }}
        >
          #{String(index + 1).padStart(2, '0')}
        </span>
        <span
          className="min-w-0 truncate"
          style={{ fontSize: 13, color: 'var(--text)' }}
        >
          {testCase.description || 'Untitled test'}
        </span>
        <div className="flex items-center gap-1.5 ml-auto flex-shrink-0">
          {tags.slice(0, 2).map((t) => (
            <span
              key={t}
              className="pill"
              style={{
                background: 'var(--bg-sunken)',
                color: 'var(--text-3)',
                fontSize: 10,
              }}
            >
              {t}
            </span>
          ))}
          {result && (
            <span
              className="mono"
              style={{ fontSize: 10.5, color: 'var(--text-4)' }}
            >
              {result.duration_ms}ms
            </span>
          )}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onEvaluate(index);
            }}
            disabled={running}
            aria-label="Evaluate this test"
            className="inline-flex items-center justify-center"
            style={{
              width: 24,
              height: 24,
              borderRadius: 999,
              border: 0,
              background: 'var(--bg-sunken)',
              boxShadow: 'inset 0 0 0 1px var(--border)',
              color: 'var(--text-2)',
              cursor: running ? 'wait' : 'pointer',
              opacity: running ? 0.5 : 1,
            }}
          >
            <Play size={10} strokeWidth={1.8} />
          </button>
          <span
            className="inline-flex items-center justify-center"
            style={{ width: 16, color: 'var(--text-4)' }}
          >
            {open ? (
              <ChevronDown size={14} strokeWidth={1.7} />
            ) : (
              <ChevronRight size={14} strokeWidth={1.7} />
            )}
          </span>
        </div>
      </button>

      {open && (
        <div
          className="flex flex-col"
          style={{
            padding: '10px 14px 14px',
            borderTop: '1px solid var(--border)',
            background: 'var(--bg-sunken)',
          }}
        >
          <KeyValue label="Input" value={formatValue(testCase.input)} />
          <KeyValue label="Expected" value={formatValue(testCase.expected)} />
          {result && (
            <KeyValue
              label="Output"
              value={formatValue(result.output)}
              tone={result.passed ? 'neutral' : 'bad'}
            />
          )}
          {result?.error && (
            <KeyValue label="Error" value={result.error} tone="bad" />
          )}
        </div>
      )}
    </div>
  );
}

function KeyValue({
  label,
  value,
  tone = 'neutral',
}: {
  label: string;
  value: string;
  tone?: 'neutral' | 'bad';
}) {
  const fg = tone === 'bad' ? 'var(--plum)' : 'var(--text-2)';
  return (
    <div
      className="grid gap-3 py-2"
      style={{
        gridTemplateColumns: '80px minmax(0, 1fr)',
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
        {value}
      </pre>
    </div>
  );
}
