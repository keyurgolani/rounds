import { useState } from 'react';
import { Play } from 'lucide-react';
import type { TestCase, CodeRunResult } from './types';

interface RunPanelProps {
  samples: TestCase[];
  running: boolean;
  onRun: (input: Record<string, unknown>) => void;
  result?: CodeRunResult;
}

function stringify(v: unknown): string {
  try {
    return JSON.stringify(v, null, 2);
  } catch {
    return String(v);
  }
}

export function RunPanel({ samples, running, onRun, result }: RunPanelProps) {
  const initial = samples[0]?.input ?? {};
  const [text, setText] = useState(JSON.stringify(initial, null, 2));
  const [parseError, setParseError] = useState<string | null>(null);
  const [selected, setSelected] = useState(0);

  function handleSample(i: number) {
    setSelected(i);
    setText(JSON.stringify(samples[i]?.input ?? {}, null, 2));
    setParseError(null);
  }

  function handleRun() {
    let parsed: unknown;
    try {
      parsed = JSON.parse(text);
    } catch {
      setParseError('Input must be valid JSON.');
      return;
    }
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      setParseError('Input must be a JSON object.');
      return;
    }
    setParseError(null);
    onRun(parsed as Record<string, unknown>);
  }

  return (
    <div className="flex flex-col h-full gap-3">
      <div className="flex flex-col flex-1 min-h-0">
        <div className="eyebrow mb-2">Custom input</div>
        {samples.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2 flex-shrink-0">
            {samples.map((s, i) => (
              <button
                key={i}
                type="button"
                onClick={() => handleSample(i)}
                style={{
                  padding: '5px 10px',
                  border: 0,
                  borderRadius: 999,
                  background: selected === i ? 'var(--ink)' : 'transparent',
                  color: selected === i ? 'var(--paper)' : 'var(--text-3)',
                  boxShadow:
                    selected === i
                      ? 'none'
                      : 'inset 0 0 0 1px var(--border-strong)',
                  fontSize: 10.5,
                  fontWeight: 500,
                  cursor: 'pointer',
                }}
              >
                Sample {String(i + 1).padStart(2, '0')}
              </button>
            ))}
          </div>
        )}
        <textarea
          id="run-input"
          aria-label="Input (JSON)"
          value={text}
          onChange={(e) => setText(e.target.value)}
          spellCheck={false}
          className="mono"
          style={{
            width: '100%',
            flex: 1,
            minHeight: 96,
            padding: 10,
            background: 'var(--bg-sunken)',
            boxShadow: parseError
              ? 'inset 0 0 0 1px var(--plum)'
              : 'inset 0 0 0 1px var(--border)',
            borderRadius: 'var(--radius)',
            border: 0,
            fontSize: 12,
            color: 'var(--text)',
            outline: 'none',
            resize: 'none',
          }}
        />
        {parseError && (
          <div
            className="mono"
            style={{ fontSize: 11, color: 'var(--plum)', marginTop: 4 }}
          >
            {parseError}
          </div>
        )}
      </div>

      <button
        type="button"
        onClick={handleRun}
        disabled={running}
        className="inline-flex items-center gap-1.5"
        style={{
          padding: '7px 14px',
          borderRadius: 'var(--radius)',
          border: 0,
          background: 'var(--ink)',
          color: 'var(--paper)',
          fontSize: 12,
          fontWeight: 500,
          cursor: running ? 'wait' : 'pointer',
          opacity: running ? 0.6 : 1,
        }}
      >
        <Play size={11} strokeWidth={1.8} />
        {running ? 'Running…' : 'Run with this input'}
      </button>

      {result && (
        <div
          className="card overflow-hidden"
          style={{ marginTop: 4 }}
        >
          <div
            className="flex items-center justify-between"
            style={{
              padding: '10px 14px',
              background: 'var(--bg-sunken)',
              borderBottom: '1px solid var(--border)',
            }}
          >
            <div className="eyebrow">Output</div>
            <span
              className="mono"
              style={{ fontSize: 10.5, color: 'var(--text-4)' }}
            >
              {result.duration_ms}ms
              {result.truncated ? ' · truncated' : ''}
            </span>
          </div>

          {result.error ? (
            <ResultSection
              label="Error"
              tone="bad"
              value={result.error}
            />
          ) : null}

          <ResultSection
            label="Return"
            tone="accent"
            value={stringify(result.return_value)}
          />

          {result.stdout && (
            <ResultSection label="stdout" value={result.stdout} />
          )}

          {result.stderr && (
            <ResultSection label="stderr" tone="bad" value={result.stderr} />
          )}
        </div>
      )}
    </div>
  );
}

function ResultSection({
  label,
  value,
  tone = 'neutral',
}: {
  label: string;
  value: string;
  tone?: 'neutral' | 'bad' | 'accent';
}) {
  const fg =
    tone === 'bad'
      ? 'var(--plum)'
      : tone === 'accent'
        ? 'var(--accent)'
        : 'var(--text-2)';
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
        {value || '(empty)'}
      </pre>
    </div>
  );
}
