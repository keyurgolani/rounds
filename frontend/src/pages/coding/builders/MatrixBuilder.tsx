import { Plus, Minus } from 'lucide-react';

interface MatrixBuilderProps {
  value: number[][];
  onChange: (next: number[][]) => void;
}

function coerce(raw: string): number {
  const n = parseInt(raw, 10);
  return Number.isNaN(n) ? 0 : n;
}

export function MatrixBuilder({ value, onChange }: MatrixBuilderProps) {
  const rows = value.length;
  const cols = rows > 0 ? Math.max(...value.map((r) => r.length)) : 0;

  function setCell(r: number, c: number, raw: string) {
    const next = value.map((row, ri) => {
      if (ri !== r) return row;
      const padded = [...row];
      while (padded.length <= c) padded.push(0);
      padded[c] = coerce(raw);
      return padded;
    });
    onChange(next);
  }

  function addRow() {
    onChange([...value, new Array(cols || 1).fill(0)]);
  }
  function removeRow() {
    onChange(value.slice(0, -1));
  }
  function addCol() {
    onChange(value.map((r) => [...r, 0]));
  }
  function removeCol() {
    onChange(value.map((r) => r.slice(0, -1)));
  }

  return (
    <div className="flex flex-col gap-2">
      {value.length === 0 && (
        <div className="mono" style={{ fontSize: 11, color: 'var(--text-4)' }}>
          (empty matrix — click + to add a row)
        </div>
      )}
      <div
        className="grid gap-1"
        style={{
          gridTemplateColumns: cols > 0 ? `repeat(${cols}, minmax(40px, 60px))` : undefined,
        }}
      >
        {value.flatMap((row, r) =>
          new Array(cols).fill(0).map((_, c) => {
            const cell = row[c] ?? 0;
            return (
              <input
                key={`${r}-${c}`}
                value={String(cell)}
                onChange={(e) => setCell(r, c, e.target.value)}
                className="mono"
                aria-label={`Cell ${r + 1},${c + 1}`}
                style={{
                  padding: '4px 6px',
                  fontSize: 11.5,
                  textAlign: 'center',
                  background: 'var(--bg-sunken)',
                  border: '1px solid var(--border)',
                  borderRadius: 4,
                  color: 'var(--text)',
                  outline: 'none',
                  width: '100%',
                  minWidth: 0,
                }}
              />
            );
          }),
        )}
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={addRow}
          aria-label="Add row"
          className="inline-flex items-center gap-1 mono"
          style={iconBtn}
        >
          <Plus size={11} strokeWidth={1.8} /> row
        </button>
        <button
          type="button"
          onClick={removeRow}
          disabled={rows === 0}
          aria-label="Remove row"
          className="inline-flex items-center gap-1 mono"
          style={iconBtn}
        >
          <Minus size={11} strokeWidth={1.8} /> row
        </button>
        <button
          type="button"
          onClick={addCol}
          disabled={rows === 0}
          aria-label="Add column"
          className="inline-flex items-center gap-1 mono"
          style={iconBtn}
        >
          <Plus size={11} strokeWidth={1.8} /> col
        </button>
        <button
          type="button"
          onClick={removeCol}
          disabled={cols === 0}
          aria-label="Remove column"
          className="inline-flex items-center gap-1 mono"
          style={iconBtn}
        >
          <Minus size={11} strokeWidth={1.8} /> col
        </button>
      </div>
    </div>
  );
}

const iconBtn: React.CSSProperties = {
  fontSize: 10.5,
  padding: '3px 8px',
  background: 'transparent',
  color: 'var(--text-3)',
  border: 0,
  boxShadow: 'inset 0 0 0 1px var(--border-strong)',
  borderRadius: 999,
  cursor: 'pointer',
};
