// Custom-input editor for the Run tab. Each parameter renders as its
// own ParamCard with a type-appropriate visual editor; a sticky param
// tab strip appears when there are 4+ params so the user can jump
// between them instead of scrolling. The Run button at the bottom
// surfaces aggregated validation issues with a "jump to" affordance.

import { useEffect, useMemo, useRef, useState } from 'react';
import { Play } from 'lucide-react';
import type { TestCase, Entry, ParamSpec, NodeTemplate, TypeName } from './types';
import { formatValue } from './format';
import { ParamCard } from './builders/ParamCard';
import { ParamField } from './builders/ParamField';
import { OpsBuilder } from './builders/OpsBuilder';
import { NodeGraphBuilder, type Layout } from './builders/NodeGraphBuilder';
import { asVerbose, type VerboseGraph } from './builders/shorthand';

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

function entryParams(entry: Entry): ParamSpec[] {
  if (entry.kind === 'function') return entry.params;
  if (entry.kind === 'in_place_mutation') return entry.params;
  if (entry.kind === 'linked_list' || entry.kind === 'tree' || entry.kind === 'graph') {
    return entry.params;
  }
  return [];
}

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return v !== null && typeof v === 'object' && !Array.isArray(v);
}

function defaultForParam(spec: ParamSpec): unknown {
  switch (spec.type) {
    case 'int':
    case 'float':
      return 0;
    case 'bool':
      return false;
    case 'string':
      return '';
    case 'int[]':
    case 'string[]':
      return [];
    case 'int[][]':
      return [];
    case 'node':
      return { nodes: [], entry: null };
    default:
      return null;
  }
}

function structuralPreview(spec: ParamSpec, value: unknown): string | null {
  if (spec.type === 'int[]' || spec.type === 'string[]') {
    if (Array.isArray(value)) return `${value.length} items`;
  }
  if (spec.type === 'int[][]') {
    if (Array.isArray(value)) {
      const rows = value.length;
      const cols = rows > 0 && Array.isArray(value[0]) ? (value[0] as unknown[]).length : 0;
      return `${rows} × ${cols}`;
    }
  }
  if (spec.type === 'node') {
    if (isPlainObject(value) && Array.isArray(value.nodes)) {
      const nodeCount = value.nodes.length;
      return nodeCount === 0 ? 'empty' : `${nodeCount} node${nodeCount === 1 ? '' : 's'}`;
    }
  }
  return null;
}

function validateValue(
  spec: ParamSpec,
  value: unknown,
): { tone: 'muted' | 'warn' | 'error'; message: string } | null {
  if (spec.type === 'int' || spec.type === 'float') {
    if (value === undefined || value === null || (typeof value === 'string' && value === '')) {
      return { tone: 'warn', message: 'value is empty' };
    }
  }
  if (spec.type === 'string') {
    if (value === undefined || value === null) {
      return { tone: 'warn', message: 'value is empty' };
    }
  }
  if (spec.type === 'node') {
    if (!isPlainObject(value) || !Array.isArray(value.nodes)) {
      return { tone: 'error', message: 'expected verbose {nodes, entry}' };
    }
    const nodes = value.nodes as unknown[];
    if (nodes.length > 0 && (value.entry === null || value.entry === undefined)) {
      return { tone: 'warn', message: 'no entry node selected' };
    }
  }
  return null;
}

export function CasesTab({ entry, samples, running, onRun }: CasesTabProps) {
  const [selected, setSelected] = useState(0);
  const [edits, setEdits] = useState<Record<number, unknown>>({});
  const [rawByParam, setRawByParam] = useState<Record<string, boolean>>({});
  const [highlightParam, setHighlightParam] = useState<string | null>(null);
  const cardRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  const seedInput = useMemo(() => samples[selected]?.input ?? {}, [samples, selected]);
  const value = edits[selected] !== undefined ? edits[selected] : seedInput;

  useEffect(() => {
    setEdits({});
    setSelected(0);
    setRawByParam({});
  }, [samples, entry]);

  const params = entryParams(entry);
  const showParamTabs = params.length >= 4;

  const valueObj: Record<string, unknown> = isPlainObject(value) ? value : {};
  const seedObj: Record<string, unknown> = isPlainObject(seedInput) ? seedInput : {};

  function handleChange(next: unknown) {
    setEdits((prev) => ({ ...prev, [selected]: next }));
  }

  function setParam(name: string, v: unknown) {
    handleChange({ ...valueObj, [name]: v });
  }

  function resetParam(name: string) {
    const next = { ...valueObj };
    if (name in seedObj) {
      next[name] = seedObj[name];
    } else {
      delete next[name];
    }
    handleChange(next);
  }

  function resetAll() {
    setEdits((prev) => {
      const next = { ...prev };
      delete next[selected];
      return next;
    });
  }

  function toggleRaw(name: string) {
    setRawByParam((prev) => ({ ...prev, [name]: !prev[name] }));
  }

  function jumpTo(name: string) {
    setHighlightParam(name);
    const el = cardRefs.current.get(name);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    window.setTimeout(() => setHighlightParam((cur) => (cur === name ? null : cur)), 1400);
  }

  const issues = params
    .map((p) => ({ p, issue: validateValue(p, valueObj[p.name]) }))
    .filter((x) => x.issue !== null) as { p: ParamSpec; issue: { tone: 'warn' | 'error'; message: string } }[];

  const isAnyEdited = edits[selected] !== undefined;

  function handleRun() {
    onRun(value);
  }

  // For class_ops the entire input is one OpsBuilder, no per-param cards.
  if (entry.kind === 'class_ops') {
    return (
      <div className="flex flex-col gap-3">
        <SampleChips
          samples={samples}
          selected={selected}
          edits={edits}
          onSelect={setSelected}
        />
        <div className="flex items-center justify-between">
          <div className="eyebrow">Input</div>
          {isAnyEdited && (
            <button
              type="button"
              onClick={resetAll}
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
        <OpsBuilder
          entry={entry}
          value={
            value &&
            typeof value === 'object' &&
            Array.isArray((value as { ops?: unknown }).ops) &&
            Array.isArray((value as { args?: unknown }).args)
              ? (value as { ops: string[]; args: unknown[][] })
              : { ops: [entry.class], args: [[]] }
          }
          onChange={handleChange}
        />
        <RunButton running={running} onRun={handleRun} issues={issues} onJumpTo={jumpTo} />
      </div>
    );
  }

  // Custom kind — no params known, fall back to a single raw JSON card.
  if (entry.kind === 'custom' || params.length === 0) {
    return (
      <div className="flex flex-col gap-3">
        <SampleChips
          samples={samples}
          selected={selected}
          edits={edits}
          onSelect={setSelected}
        />
        <ParamCard
          name="input"
          type="any"
          edited={isAnyEdited}
          rawMode
          onToggleRaw={() => {}}
          onReset={resetAll}
        >
          <RawEditor value={value} onChange={handleChange} ariaLabel="Raw input JSON" />
        </ParamCard>
        <RunButton running={running} onRun={handleRun} issues={issues} onJumpTo={jumpTo} />
      </div>
    );
  }

  // Function / in_place_mutation / linked_list / tree / graph: per-param cards.
  const isNodeEntry =
    entry.kind === 'linked_list' || entry.kind === 'tree' || entry.kind === 'graph';
  const tmpl: NodeTemplate | null = isNodeEntry
    ? entry.node_template ?? defaultNodeTemplate(entry.kind)
    : null;
  const layout: Layout | null = isNodeEntry ? layoutFor(entry.kind) : null;

  return (
    <div className="flex flex-col gap-3">
      <SampleChips
        samples={samples}
        selected={selected}
        edits={edits}
        onSelect={setSelected}
      />

      {showParamTabs && (
        <ParamJumpStrip params={params} highlight={highlightParam} onJump={jumpTo} />
      )}

      <div className="flex flex-col gap-3">
        {params.map((p) => {
          const v = valueObj[p.name] !== undefined ? valueObj[p.name] : defaultForParam(p);
          const edited = !shallowEqual(v, seedObj[p.name]);
          const raw = rawByParam[p.name] === true;
          const issue = validateValue(p, v);
          const preview = !issue ? structuralPreview(p, v) : null;
          const footerNode = issue
            ? issue.message
            : preview
              ? preview
              : null;
          return (
            <div
              key={p.name}
              ref={(el) => {
                if (el) cardRefs.current.set(p.name, el);
                else cardRefs.current.delete(p.name);
              }}
            >
              <ParamCard
                name={p.name}
                type={p.type}
                edited={edited}
                rawMode={raw}
                onToggleRaw={() => toggleRaw(p.name)}
                onReset={() => resetParam(p.name)}
                footer={footerNode}
                footerTone={issue ? issue.tone : 'muted'}
                highlight={highlightParam === p.name}
                cardId={`param-card-${p.name}`}
              >
                {raw ? (
                  <RawEditor
                    value={v}
                    onChange={(nv) => setParam(p.name, nv)}
                    ariaLabel={`${p.name} raw JSON`}
                  />
                ) : (
                  <ParamBody
                    spec={p}
                    value={v}
                    onChange={(nv) => setParam(p.name, nv)}
                    nodeTemplate={tmpl}
                    nodeLayout={layout}
                  />
                )}
              </ParamCard>
            </div>
          );
        })}
      </div>

      {isAnyEdited && (
        <button
          type="button"
          onClick={resetAll}
          className="mono"
          style={{
            alignSelf: 'flex-start',
            fontSize: 10.5,
            color: 'var(--text-4)',
            background: 'transparent',
            border: 0,
            cursor: 'pointer',
            textDecoration: 'underline',
          }}
        >
          Reset all params to sample
        </button>
      )}

      <RunButton running={running} onRun={handleRun} issues={issues} onJumpTo={jumpTo} />
    </div>
  );
}

function shallowEqual(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (a === undefined || b === undefined) return false;
  try {
    return JSON.stringify(a) === JSON.stringify(b);
  } catch {
    return false;
  }
}

function SampleChips({
  samples,
  selected,
  edits,
  onSelect,
}: {
  samples: TestCase[];
  selected: number;
  edits: Record<number, unknown>;
  onSelect: (i: number) => void;
}) {
  if (samples.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1.5 flex-shrink-0">
      {samples.map((_, i) => {
        const active = selected === i;
        return (
          <button
            key={i}
            type="button"
            onClick={() => onSelect(i)}
            style={{
              padding: '5px 10px',
              border: 0,
              borderRadius: 999,
              background: active ? 'var(--ink)' : 'transparent',
              color: active ? 'var(--paper)' : 'var(--text-3)',
              boxShadow: active ? 'none' : 'inset 0 0 0 1px var(--border-strong)',
              fontSize: 10.5,
              fontWeight: 500,
              cursor: 'pointer',
            }}
            aria-pressed={active}
          >
            Case {String(i + 1).padStart(2, '0')}
            {edits[i] !== undefined ? ' •' : ''}
          </button>
        );
      })}
    </div>
  );
}

function ParamJumpStrip({
  params,
  highlight,
  onJump,
}: {
  params: ParamSpec[];
  highlight: string | null;
  onJump: (name: string) => void;
}) {
  return (
    <div
      className="flex gap-1 flex-wrap"
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 1,
        padding: '6px 0',
        background: 'var(--bg)',
        borderBottom: '1px solid var(--border)',
      }}
    >
      <span
        className="mono uppercase"
        style={{
          fontSize: 9.5,
          color: 'var(--text-4)',
          letterSpacing: '0.12em',
          alignSelf: 'center',
          marginRight: 6,
        }}
      >
        Jump to
      </span>
      {params.map((p) => {
        const active = highlight === p.name;
        return (
          <button
            key={p.name}
            type="button"
            onClick={() => onJump(p.name)}
            className="mono"
            style={{
              padding: '3px 8px',
              fontSize: 10.5,
              border: '1px solid var(--border)',
              borderRadius: 999,
              background: active ? 'var(--accent-soft)' : 'transparent',
              color: active ? 'var(--accent)' : 'var(--text-3)',
              cursor: 'pointer',
            }}
          >
            {p.name}
          </button>
        );
      })}
    </div>
  );
}

function RunButton({
  running,
  onRun,
  issues,
  onJumpTo,
}: {
  running: boolean;
  onRun: () => void;
  issues: { p: ParamSpec; issue: { tone: 'warn' | 'error'; message: string } }[];
  onJumpTo: (name: string) => void;
}) {
  const errorCount = issues.filter((i) => i.issue.tone === 'error').length;
  const warnCount = issues.filter((i) => i.issue.tone === 'warn').length;
  const total = issues.length;
  return (
    <div className="flex flex-col gap-1.5">
      <button
        type="button"
        onClick={onRun}
        disabled={running || errorCount > 0}
        className="inline-flex items-center gap-1.5"
        style={{
          padding: '7px 14px',
          borderRadius: 'var(--radius)',
          border: 0,
          background: errorCount > 0 ? 'var(--bg-sunken)' : 'var(--ink)',
          color: errorCount > 0 ? 'var(--text-4)' : 'var(--paper)',
          fontSize: 12,
          fontWeight: 500,
          cursor: running ? 'wait' : errorCount > 0 ? 'not-allowed' : 'pointer',
          opacity: running ? 0.6 : 1,
          alignSelf: 'flex-start',
        }}
      >
        <Play size={11} strokeWidth={1.8} />
        {running
          ? 'Running…'
          : errorCount > 0
            ? `Run · ${errorCount} error${errorCount === 1 ? '' : 's'}`
            : warnCount > 0
              ? `Run · ${warnCount} warning${warnCount === 1 ? '' : 's'}`
              : 'Run'}
      </button>
      {total > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {issues.map((it) => (
            <button
              key={it.p.name}
              type="button"
              onClick={() => onJumpTo(it.p.name)}
              className="mono"
              style={{
                padding: '3px 8px',
                fontSize: 10.5,
                background: 'transparent',
                color: it.issue.tone === 'error' ? 'var(--plum)' : 'var(--ochre)',
                border: `1px solid ${it.issue.tone === 'error' ? 'var(--plum)' : 'var(--ochre)'}`,
                borderRadius: 999,
                cursor: 'pointer',
              }}
              title={it.issue.message}
            >
              {it.p.name}: {it.issue.message}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function ParamBody({
  spec,
  value,
  onChange,
  nodeTemplate,
  nodeLayout,
}: {
  spec: ParamSpec;
  value: unknown;
  onChange: (next: unknown) => void;
  nodeTemplate: NodeTemplate | null;
  nodeLayout: Layout | null;
}) {
  if (spec.type === 'node' && nodeTemplate && nodeLayout) {
    const verbose = asVerbose(value, nodeTemplate);
    return (
      <NodeGraphBuilder
        template={nodeTemplate}
        layout={nodeLayout}
        value={verbose as VerboseGraph}
        onChange={onChange}
      />
    );
  }
  // For all non-node param types, ParamField already provides the right
  // editor (scalar / list / matrix / JSON fallback). We only render the
  // editor part — the label/header is provided by ParamCard so we hide
  // ParamField's own label by passing a wrapper.
  return <ParamFieldNoLabel spec={spec} value={value} onChange={onChange} />;
}

function ParamFieldNoLabel({
  spec,
  value,
  onChange,
}: {
  spec: ParamSpec;
  value: unknown;
  onChange: (next: unknown) => void;
}) {
  // Reuse ParamField's editor logic but strip its own label by wrapping
  // it in a div whose child label is hidden via CSS. Cheap and avoids a
  // copy-paste of all the type dispatch.
  return (
    <div className="param-field-no-label">
      <style>{`.param-field-no-label > div > label { display: none; }`}</style>
      <ParamField spec={spec} value={value} onChange={onChange} />
    </div>
  );
}

function RawEditor({
  value,
  onChange,
  ariaLabel,
}: {
  value: unknown;
  onChange: (next: unknown) => void;
  ariaLabel: string;
}) {
  const text = useMemo(() => {
    try {
      return formatValue(value);
    } catch {
      return '';
    }
  }, [value]);

  return (
    <textarea
      aria-label={ariaLabel}
      value={text}
      onChange={(e) => {
        try {
          onChange(JSON.parse(e.target.value));
        } catch {
          /* keep last good upstream value while invalid */
        }
      }}
      spellCheck={false}
      className="mono"
      style={{
        width: '100%',
        minHeight: 80,
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

// Re-export TypeName so a few internal narrowings type-resolve cleanly.
export type { TypeName };
