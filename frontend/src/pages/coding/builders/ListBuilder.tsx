import { useState } from 'react';
import { Plus, X } from 'lucide-react';
import type { TypeName } from '../types';

interface ListBuilderProps {
  value: unknown[];
  onChange: (next: unknown[]) => void;
  itemType: TypeName;
}

function coerce(itemType: TypeName, raw: string): unknown {
  if (itemType === 'int') {
    const n = parseInt(raw, 10);
    return Number.isNaN(n) ? 0 : n;
  }
  if (itemType === 'float') {
    const n = parseFloat(raw);
    return Number.isNaN(n) ? 0 : n;
  }
  if (itemType === 'bool') {
    return raw === 'true';
  }
  return raw;
}

function display(v: unknown): string {
  if (v === null || v === undefined) return '';
  return String(v);
}

export function ListBuilder({ value, onChange, itemType }: ListBuilderProps) {
  const [draft, setDraft] = useState('');

  function append() {
    if (draft === '' && itemType !== 'string') return;
    onChange([...value, coerce(itemType, draft)]);
    setDraft('');
  }
  function removeAt(i: number) {
    onChange(value.filter((_, j) => j !== i));
  }
  function updateAt(i: number, raw: string) {
    onChange(value.map((v, j) => (j === i ? coerce(itemType, raw) : v)));
  }

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {value.map((v, i) => (
        <span
          key={i}
          className="inline-flex items-center gap-1"
          style={{
            padding: '3px 6px 3px 8px',
            background: 'var(--bg-sunken)',
            border: '1px solid var(--border)',
            borderRadius: 999,
            fontSize: 11.5,
          }}
        >
          <input
            value={display(v)}
            onChange={(e) => updateAt(i, e.target.value)}
            className="mono"
            aria-label={`Item ${i + 1}`}
            style={{
              border: 0,
              background: 'transparent',
              width: Math.max(1, display(v).length) * 8 + 8,
              fontSize: 11.5,
              outline: 'none',
              color: 'var(--text)',
            }}
          />
          <button
            type="button"
            onClick={() => removeAt(i)}
            aria-label={`Remove item ${i + 1}`}
            style={{
              border: 0,
              background: 'transparent',
              cursor: 'pointer',
              color: 'var(--text-4)',
              padding: 0,
              display: 'inline-flex',
            }}
          >
            <X size={12} strokeWidth={1.8} />
          </button>
        </span>
      ))}
      <span
        className="inline-flex items-center gap-1"
        style={{
          padding: '3px 6px 3px 8px',
          background: 'transparent',
          border: '1px dashed var(--border)',
          borderRadius: 999,
          fontSize: 11.5,
        }}
      >
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              append();
            }
          }}
          aria-label="New item"
          placeholder={itemType === 'string' ? 'text' : itemType}
          className="mono"
          style={{
            border: 0,
            background: 'transparent',
            width: 60,
            fontSize: 11.5,
            outline: 'none',
            color: 'var(--text)',
          }}
        />
        <button
          type="button"
          onClick={append}
          aria-label="Append item"
          style={{
            border: 0,
            background: 'transparent',
            cursor: 'pointer',
            color: 'var(--text-4)',
            padding: 0,
            display: 'inline-flex',
          }}
        >
          <Plus size={12} strokeWidth={1.8} />
        </button>
      </span>
    </div>
  );
}
