import { ReactNode, useState, useEffect } from 'react';
import { formatValue } from '../format';

export type Mode = 'form' | 'raw';

interface RawModeToggleProps {
  value: unknown;
  onChange: (next: unknown) => void;
  children: (value: unknown, onChange: (next: unknown) => void) => ReactNode;
  /** Custom label shown when the form can't visualize the current value. */
  unrenderableMessage?: string;
}

export function RawModeToggle({
  value,
  onChange,
  children,
}: RawModeToggleProps) {
  const [mode, setMode] = useState<Mode>('form');
  const [rawText, setRawText] = useState(() => safeStringify(value));
  const [parseError, setParseError] = useState<string | null>(null);

  // When the upstream value changes (e.g. chip switch), sync raw text.
  useEffect(() => {
    if (mode === 'raw') return;
    setRawText(safeStringify(value));
  }, [value, mode]);

  function switchMode(target: Mode) {
    if (target === 'form') {
      try {
        const parsed = JSON.parse(rawText);
        setParseError(null);
        onChange(parsed);
        setMode('form');
      } catch (e) {
        setParseError((e as Error).message);
      }
    } else {
      setRawText(safeStringify(value));
      setMode('raw');
    }
  }

  function handleRawChange(v: string) {
    setRawText(v);
    setParseError(null);
    try {
      const parsed = JSON.parse(v);
      onChange(parsed);
    } catch {
      // Don't propagate while invalid; keep last good value upstream.
    }
  }

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-end">
        <div
          role="tablist"
          aria-label="Editor mode"
          className="flex items-center gap-1"
          style={{
            padding: 2,
            background: 'var(--bg-sunken)',
            borderRadius: 999,
          }}
        >
          {(['form', 'raw'] as const).map((m) => (
            <button
              key={m}
              type="button"
              role="tab"
              aria-selected={mode === m}
              onClick={() => switchMode(m)}
              style={{
                padding: '3px 9px',
                fontSize: 10.5,
                fontWeight: 500,
                background: mode === m ? 'var(--paper)' : 'transparent',
                color: mode === m ? 'var(--ink)' : 'var(--text-4)',
                border: 0,
                borderRadius: 999,
                cursor: 'pointer',
                textTransform: 'capitalize',
              }}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {mode === 'form' ? (
        children(value, onChange)
      ) : (
        <textarea
          aria-label="Raw JSON"
          value={rawText}
          onChange={(e) => handleRawChange(e.target.value)}
          spellCheck={false}
          className="mono"
          style={{
            width: '100%',
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
            resize: 'vertical',
          }}
        />
      )}

      {parseError && (
        <div className="mono" style={{ fontSize: 11, color: 'var(--plum)' }}>
          {parseError}
        </div>
      )}
    </div>
  );
}

function safeStringify(v: unknown): string {
  try {
    return formatValue(v);
  } catch {
    return '';
  }
}
