import { Plus, X } from 'lucide-react';
import type { Entry, ParamSpec } from '../types';

interface OpsValue {
  ops: string[];
  args: unknown[][];
}

interface OpsBuilderProps {
  entry: Extract<Entry, { kind: 'class_ops' }>;
  value: OpsValue;
  onChange: (next: OpsValue) => void;
}

function coerce(type: ParamSpec['type'], raw: string): unknown {
  if (type === 'int') {
    const n = parseInt(raw, 10);
    return Number.isNaN(n) ? 0 : n;
  }
  if (type === 'float') {
    const n = parseFloat(raw);
    return Number.isNaN(n) ? 0 : n;
  }
  if (type === 'bool') return raw === 'true';
  if (type === 'string') return raw;
  // arrays/nodes: parse JSON; fall back to raw on parse failure
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

function display(v: unknown): string {
  if (v === undefined || v === null) return '';
  if (typeof v === 'object') {
    try {
      return JSON.stringify(v);
    } catch {
      return '';
    }
  }
  return String(v);
}

export function OpsBuilder({ entry, value, onChange }: OpsBuilderProps) {
  const className = entry.class;
  const ctorParams = entry.constructor?.params ?? [];
  const methods = entry.methods ?? [];
  const methodByName = new Map(methods.map((m) => [m.name, m]));

  function setOp(i: number, op: string) {
    const m = methodByName.get(op);
    const newArgs = (m?.params ?? []).map(() => '');
    onChange({
      ops: value.ops.map((o, j) => (j === i ? op : o)),
      args: value.args.map((a, j) => (j === i ? newArgs : a)),
    });
  }

  function setArg(rowI: number, argI: number, raw: string, type: ParamSpec['type']) {
    onChange({
      ops: value.ops,
      args: value.args.map((a, ri) => {
        if (ri !== rowI) return a;
        const next = [...a];
        next[argI] = coerce(type, raw);
        return next;
      }),
    });
  }

  function addRow() {
    const first = methods[0];
    const params = first?.params ?? [];
    onChange({
      ops: [...value.ops, first ? first.name : ''],
      args: [...value.args, params.map(() => '')],
    });
  }

  function removeRow(i: number) {
    if (i === 0) return; // can't remove constructor
    onChange({
      ops: value.ops.filter((_, j) => j !== i),
      args: value.args.filter((_, j) => j !== i),
    });
  }

  return (
    <div className="flex flex-col gap-1.5">
      {value.ops.map((op, rowI) => {
        const isCtor = rowI === 0;
        const params: ParamSpec[] = isCtor
          ? ctorParams
          : methodByName.get(op)?.params ?? [];
        return (
          <div
            key={rowI}
            className="flex items-center gap-2"
            style={{
              padding: '6px 8px',
              background: 'var(--bg-sunken)',
              borderRadius: 'var(--radius)',
            }}
          >
            <span className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)', width: 24 }}>
              {String(rowI + 1).padStart(2, '0')}
            </span>
            {isCtor ? (
              <span
                className="mono"
                style={{
                  fontSize: 11.5,
                  fontWeight: 500,
                  color: 'var(--ink)',
                  whiteSpace: 'nowrap',
                }}
              >
                new {className}
              </span>
            ) : (
              <select
                value={op}
                aria-label={`Method for op ${rowI + 1}`}
                onChange={(e) => setOp(rowI, e.target.value)}
                className="mono"
                style={{
                  fontSize: 11.5,
                  padding: '3px 6px',
                  background: 'var(--paper)',
                  border: '1px solid var(--border)',
                  borderRadius: 4,
                }}
              >
                {methods.map((m) => (
                  <option key={m.name} value={m.name}>
                    {m.name}
                  </option>
                ))}
              </select>
            )}
            <span style={{ color: 'var(--text-4)' }}>(</span>
            <div className="flex flex-wrap items-center gap-1">
              {params.map((p, argI) => {
                const v = value.args[rowI]?.[argI];
                return (
                  <input
                    key={argI}
                    aria-label={`${op || 'constructor'} arg ${p.name}`}
                    value={display(v)}
                    onChange={(e) => setArg(rowI, argI, e.target.value, p.type)}
                    placeholder={`${p.name}: ${p.type}`}
                    className="mono"
                    style={{
                      fontSize: 11.5,
                      padding: '2px 6px',
                      background: 'var(--paper)',
                      border: '1px solid var(--border)',
                      borderRadius: 4,
                      width: 100,
                      outline: 'none',
                    }}
                  />
                );
              })}
            </div>
            <span style={{ color: 'var(--text-4)' }}>)</span>
            {!isCtor && (
              <button
                type="button"
                onClick={() => removeRow(rowI)}
                aria-label={`Remove op ${rowI + 1}`}
                style={{
                  marginLeft: 'auto',
                  background: 'transparent',
                  border: 0,
                  cursor: 'pointer',
                  color: 'var(--text-4)',
                  display: 'inline-flex',
                  padding: 2,
                }}
              >
                <X size={12} strokeWidth={1.8} />
              </button>
            )}
          </div>
        );
      })}
      <button
        type="button"
        onClick={addRow}
        disabled={methods.length === 0}
        aria-label="Append op"
        className="inline-flex items-center gap-1 mono"
        style={{
          fontSize: 10.5,
          padding: '3px 10px',
          background: 'transparent',
          color: 'var(--text-3)',
          border: 0,
          boxShadow: 'inset 0 0 0 1px var(--border-strong)',
          borderRadius: 999,
          cursor: 'pointer',
          alignSelf: 'flex-start',
        }}
      >
        <Plus size={11} strokeWidth={1.8} /> op
      </button>
    </div>
  );
}
