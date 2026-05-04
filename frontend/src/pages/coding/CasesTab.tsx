import { useState, useMemo, useEffect } from 'react';
import { Play } from 'lucide-react';
import type { TestCase, Entry, ParamSpec, NodeTemplate } from './types';
import { RawModeToggle } from './builders/RawModeToggle';
import { ParamField } from './builders/ParamField';
import { OpsBuilder } from './builders/OpsBuilder';
import { NodeGraphBuilder, type Layout } from './builders/NodeGraphBuilder';
import { toVerbose } from './builders/shorthand';

interface CasesTabProps {
  entry: Entry;
  samples: TestCase[];
  running: boolean;
  onRun: (input: unknown) => void;
}

function defaultNodeTemplate(kind: 'linked_list' | 'tree' | 'graph'): NodeTemplate {
  if (kind === 'linked_list') {
    return {
      name: 'ListNode',
      fields: [{ name: 'val', type: 'int' }],
      links: [{ name: 'next', arity: 'single' }],
    };
  }
  if (kind === 'tree') {
    return {
      name: 'TreeNode',
      fields: [{ name: 'val', type: 'int' }],
      links: [
        { name: 'left', arity: 'single' },
        { name: 'right', arity: 'single' },
      ],
    };
  }
  return {
    name: 'Node',
    fields: [{ name: 'val', type: 'int' }],
    links: [{ name: 'neighbors', arity: 'list' }],
  };
}

function layoutFor(kind: 'linked_list' | 'tree' | 'graph'): Layout {
  if (kind === 'linked_list') return 'chain';
  if (kind === 'tree') return 'tree';
  return 'general';
}

function defaultShape(kind: 'linked_list' | 'tree' | 'graph'): string {
  if (kind === 'linked_list') return 'linked_list_array';
  if (kind === 'tree') return 'tree_level_order';
  return 'graph_adjacency';
}

export function CasesTab({ entry, samples, running, onRun }: CasesTabProps) {
  const [selected, setSelected] = useState(0);
  const [edits, setEdits] = useState<Record<number, unknown>>({});

  const seedInput = useMemo(() => samples[selected]?.input ?? {}, [samples, selected]);
  const value = edits[selected] !== undefined ? edits[selected] : seedInput;

  useEffect(() => {
    setEdits({});
    setSelected(0);
  }, [samples, entry]);

  function handleSelectChip(i: number) {
    setSelected(i);
  }

  function handleChange(next: unknown) {
    setEdits((prev) => ({ ...prev, [selected]: next }));
  }

  function handleResetToSample() {
    setEdits((prev) => {
      const next = { ...prev };
      delete next[selected];
      return next;
    });
  }

  function handleRun() {
    onRun(value);
  }

  const isEdited = edits[selected] !== undefined;

  return (
    <div className="flex flex-col gap-3">
      {samples.length > 0 && (
        <div className="flex flex-wrap gap-1.5 flex-shrink-0">
          {samples.map((_, i) => (
            <button
              key={i}
              type="button"
              onClick={() => handleSelectChip(i)}
              style={{
                padding: '5px 10px',
                border: 0,
                borderRadius: 999,
                background: selected === i ? 'var(--ink)' : 'transparent',
                color: selected === i ? 'var(--paper)' : 'var(--text-3)',
                boxShadow:
                  selected === i ? 'none' : 'inset 0 0 0 1px var(--border-strong)',
                fontSize: 10.5,
                fontWeight: 500,
                cursor: 'pointer',
              }}
              aria-pressed={selected === i}
            >
              Case {String(i + 1).padStart(2, '0')}
              {edits[i] !== undefined ? ' •' : ''}
            </button>
          ))}
        </div>
      )}

      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between flex-shrink-0">
          <div className="eyebrow">Input</div>
          {isEdited && (
            <button
              type="button"
              onClick={handleResetToSample}
              className="mono"
              style={{
                fontSize: 10.5,
                color: 'var(--text-4)',
                background: 'transparent',
                border: 0,
                cursor: 'pointer',
                textDecoration: 'underline',
              }}
            >
              Reset to sample
            </button>
          )}
        </div>

        <RawModeToggle value={value} onChange={handleChange}>
          {(formValue, formOnChange) => (
            <KindForm
              entry={entry}
              value={formValue}
              onChange={formOnChange}
            />
          )}
        </RawModeToggle>
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
          alignSelf: 'flex-start',
        }}
      >
        <Play size={11} strokeWidth={1.8} />
        {running ? 'Running…' : 'Run'}
      </button>
    </div>
  );
}

function KindForm({
  entry,
  value,
  onChange,
}: {
  entry: Entry;
  value: unknown;
  onChange: (next: unknown) => void;
}) {
  if (entry.kind === 'function' || entry.kind === 'in_place_mutation') {
    const params: ParamSpec[] =
      entry.kind === 'function' ? entry.params : entry.params;
    const obj =
      typeof value === 'object' && value !== null && !Array.isArray(value)
        ? (value as Record<string, unknown>)
        : {};
    return (
      <div className="flex flex-col gap-2">
        {params.map((p) => (
          <ParamField
            key={p.name}
            spec={p}
            value={obj[p.name]}
            onChange={(v) => onChange({ ...obj, [p.name]: v })}
          />
        ))}
      </div>
    );
  }
  if (entry.kind === 'class_ops') {
    const v =
      value &&
      typeof value === 'object' &&
      Array.isArray((value as { ops?: unknown }).ops) &&
      Array.isArray((value as { args?: unknown }).args)
        ? (value as { ops: string[]; args: unknown[][] })
        : { ops: [entry.class], args: [[]] };
    return <OpsBuilder entry={entry} value={v} onChange={onChange} />;
  }
  if (entry.kind === 'linked_list' || entry.kind === 'tree' || entry.kind === 'graph') {
    const tmpl = entry.node_template ?? defaultNodeTemplate(entry.kind);
    const layout = layoutFor(entry.kind);
    const shape = entry.input_shape ?? defaultShape(entry.kind);
    const nodeParams = entry.params.filter((p) => p.type === 'node');
    const otherParams = entry.params.filter((p) => p.type !== 'node');
    const obj =
      typeof value === 'object' && value !== null && !Array.isArray(value)
        ? (value as Record<string, unknown>)
        : {};
    return (
      <div className="flex flex-col gap-2">
        {nodeParams.map((p) => {
          const raw = obj[p.name];
          let verbose;
          try {
            verbose =
              raw && typeof raw === 'object' && 'nodes' in (raw as object)
                ? (raw as Parameters<typeof toVerbose>[0])
                : toVerbose(raw, shape as Parameters<typeof toVerbose>[1], tmpl);
          } catch {
            verbose = { nodes: [], entry: null };
          }
          return (
            <div key={p.name} className="flex flex-col gap-1">
              <label
                className="mono uppercase"
                style={{
                  fontSize: 9.5,
                  color: 'var(--text-4)',
                  letterSpacing: '0.12em',
                }}
              >
                {p.name}
                <span style={{ marginLeft: 6, color: 'var(--text-4)', textTransform: 'none' }}>
                  {p.type}
                </span>
              </label>
              <NodeGraphBuilder
                template={tmpl}
                layout={layout}
                value={verbose as { nodes: []; entry: number | null }}
                onChange={(next) => onChange({ ...obj, [p.name]: next })}
              />
            </div>
          );
        })}
        {otherParams.map((p) => (
          <ParamField
            key={p.name}
            spec={p}
            value={obj[p.name]}
            onChange={(v) => onChange({ ...obj, [p.name]: v })}
          />
        ))}
      </div>
    );
  }
  // custom — fall back to raw JSON via the Raw toggle (which the wrapper already provides).
  return (
    <pre className="mono" style={{ fontSize: 11, color: 'var(--text-4)', margin: 0 }}>
      Switch to Raw mode to edit custom input.
    </pre>
  );
}
