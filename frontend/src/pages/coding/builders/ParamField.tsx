import type { ParamSpec, TypeName } from '../types';
import { formatValue } from '../format';
import { ListBuilder } from './ListBuilder';
import { MatrixBuilder } from './MatrixBuilder';

interface ParamFieldProps {
  spec: ParamSpec;
  value: unknown;
  onChange: (next: unknown) => void;
  /** Optional override renderer for the 'node' type — provided by NodeGraphBuilder when a parent context wants to swap in a graph builder for node params. */
  renderNode?: (value: unknown, onChange: (n: unknown) => void) => React.ReactNode;
}

function ScalarInput({
  type,
  value,
  onChange,
  ariaLabel,
}: {
  type: TypeName;
  value: unknown;
  onChange: (n: unknown) => void;
  ariaLabel: string;
}) {
  function coerce(raw: string): unknown {
    if (type === 'int') {
      const n = parseInt(raw, 10);
      return Number.isNaN(n) ? 0 : n;
    }
    if (type === 'float') {
      const n = parseFloat(raw);
      return Number.isNaN(n) ? 0 : n;
    }
    if (type === 'bool') return raw === 'true';
    return raw;
  }
  return (
    <input
      aria-label={ariaLabel}
      value={value === undefined || value === null ? '' : String(value)}
      onChange={(e) => onChange(coerce(e.target.value))}
      className="mono"
      style={{
        padding: '5px 8px',
        fontSize: 11.5,
        background: 'var(--bg-sunken)',
        border: '1px solid var(--border)',
        borderRadius: 4,
        width: '100%',
        outline: 'none',
      }}
    />
  );
}

function JsonFallback({
  value,
  onChange,
  ariaLabel,
}: {
  value: unknown;
  onChange: (n: unknown) => void;
  ariaLabel: string;
}) {
  return (
    <textarea
      aria-label={ariaLabel}
      value={(() => {
        try {
          return formatValue(value);
        } catch {
          return '';
        }
      })()}
      onChange={(e) => {
        try {
          onChange(JSON.parse(e.target.value));
        } catch {
          // keep last good upstream value while invalid
        }
      }}
      spellCheck={false}
      className="mono"
      style={{
        width: '100%',
        minHeight: 64,
        padding: 8,
        background: 'var(--bg-sunken)',
        border: '1px solid var(--border)',
        borderRadius: 4,
        fontSize: 11.5,
        color: 'var(--text)',
        outline: 'none',
        resize: 'vertical',
      }}
    />
  );
}

export function ParamField({ spec, value, onChange, renderNode }: ParamFieldProps) {
  const ariaLabel = `${spec.name}: ${spec.type}`;
  const t = spec.type;

  let editor: React.ReactNode;
  if (t === 'int' || t === 'float' || t === 'bool' || t === 'string') {
    editor = <ScalarInput type={t} value={value} onChange={onChange} ariaLabel={ariaLabel} />;
  } else if (t === 'int[]' || t === 'string[]') {
    const itemType: TypeName = t === 'int[]' ? 'int' : 'string';
    editor = (
      <ListBuilder
        value={Array.isArray(value) ? value : []}
        onChange={onChange}
        itemType={itemType}
      />
    );
  } else if (t === 'int[][]') {
    editor = (
      <MatrixBuilder
        value={Array.isArray(value) ? (value as number[][]) : []}
        onChange={onChange as (n: number[][]) => void}
      />
    );
  } else if (t === 'node' && renderNode) {
    editor = renderNode(value, onChange);
  } else {
    editor = <JsonFallback value={value} onChange={onChange} ariaLabel={ariaLabel} />;
  }

  return (
    <div className="flex flex-col gap-1">
      <label
        className="mono uppercase"
        style={{
          fontSize: 9.5,
          color: 'var(--text-4)',
          letterSpacing: '0.12em',
        }}
      >
        {spec.name}
        <span style={{ marginLeft: 6, color: 'var(--text-4)', textTransform: 'none' }}>
          {spec.type}
        </span>
      </label>
      {editor}
    </div>
  );
}
