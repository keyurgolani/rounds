import { Plus, X } from 'lucide-react';
import type { NodeTemplate } from '../types';
import { formatValue } from '../format';
import {
  type VerboseGraph,
  type VerboseNode,
  type NodeRef,
  fromVerboseChain,
  fromVerboseLevelOrder,
} from './shorthand';

export type Layout = 'chain' | 'tree' | 'general';

interface NodeGraphBuilderProps {
  template: NodeTemplate;
  layout: Layout;
  value: VerboseGraph;
  onChange: (next: VerboseGraph) => void;
}

function coerce(type: 'int' | 'float' | 'bool' | 'string' | string, raw: string): unknown {
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

function emptyNode(template: NodeTemplate, id: number): VerboseNode {
  const fields: Record<string, unknown> = {};
  for (const f of template.fields) {
    fields[f.name] = f.type === 'string' ? '' : 0;
  }
  const links: VerboseNode['links'] = {};
  for (const l of template.links) {
    links[l.name] = l.arity === 'list' ? [] : null;
  }
  return { id, fields, links };
}

function ChainLayout({ template, value, onChange }: Omit<NodeGraphBuilderProps, 'layout'>) {
  const linkName = template.links[0]?.name ?? 'next';
  const fieldName = template.fields[0]?.name ?? 'val';

  // Walk the chain via the entry, returning the IDs in order.
  const order: number[] = [];
  if (value.entry !== null) {
    const byId = new Map<number, VerboseNode>(value.nodes.map((n) => [n.id, n]));
    let cur: number | null = value.entry;
    const seen = new Set<number>();
    while (cur !== null && !seen.has(cur)) {
      seen.add(cur);
      order.push(cur);
      const nextRef: NodeRef | undefined = byId.get(cur)?.links[linkName];
      cur = typeof nextRef === 'number' ? nextRef : null;
    }
  }

  function setField(id: number, name: string, raw: string, type: string) {
    const next: VerboseGraph = {
      ...value,
      nodes: value.nodes.map((n) =>
        n.id === id ? { ...n, fields: { ...n.fields, [name]: coerce(type, raw) } } : n,
      ),
    };
    onChange(next);
  }

  function append() {
    const newId = (value.nodes.reduce((m, n) => Math.max(m, n.id), -1) + 1) || 0;
    const newNode = emptyNode(template, newId);
    let nodes = [...value.nodes, newNode];
    let entry = value.entry;
    if (entry === null) {
      entry = newId;
    } else {
      // wire previous tail's link to newId
      const tailId = order[order.length - 1] ?? entry;
      nodes = nodes.map((n) =>
        n.id === tailId ? { ...n, links: { ...n.links, [linkName]: newId } } : n,
      );
    }
    onChange({ nodes, entry });
  }

  function removeAt(idx: number) {
    if (idx < 0 || idx >= order.length) return;
    const removeId = order[idx];
    const newOrder = order.filter((_, i) => i !== idx);
    let nodes = value.nodes.filter((n) => n.id !== removeId);
    // Re-wire neighbors
    for (let i = 0; i < newOrder.length - 1; i++) {
      const a = newOrder[i];
      const b = newOrder[i + 1];
      nodes = nodes.map((n) =>
        n.id === a ? { ...n, links: { ...n.links, [linkName]: b } } : n,
      );
    }
    if (newOrder.length > 0) {
      const tail = newOrder[newOrder.length - 1];
      nodes = nodes.map((n) =>
        n.id === tail ? { ...n, links: { ...n.links, [linkName]: null } } : n,
      );
    }
    const entry = newOrder.length > 0 ? newOrder[0] : null;
    onChange({ nodes, entry });
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {order.map((id, idx) => {
        const node = value.nodes.find((n) => n.id === id)!;
        return (
          <div key={id} className="flex items-center gap-1.5">
            <div
              className="flex items-center gap-1"
              style={{
                padding: '4px 8px',
                background: 'var(--bg-sunken)',
                border: '1px solid var(--border)',
                borderRadius: 6,
              }}
            >
              {template.fields.map((f) => (
                <input
                  key={f.name}
                  aria-label={`Node ${idx + 1} ${f.name}`}
                  value={String(node.fields[f.name] ?? '')}
                  onChange={(e) => setField(id, f.name, e.target.value, f.type)}
                  className="mono"
                  style={{
                    width: 36,
                    fontSize: 11.5,
                    padding: '2px 4px',
                    background: 'var(--paper)',
                    border: '1px solid var(--border)',
                    borderRadius: 4,
                    textAlign: 'center',
                    outline: 'none',
                  }}
                />
              ))}
              <button
                type="button"
                onClick={() => removeAt(idx)}
                aria-label={`Remove node ${idx + 1}`}
                style={{
                  background: 'transparent',
                  border: 0,
                  cursor: 'pointer',
                  color: 'var(--text-4)',
                  padding: 0,
                  display: 'inline-flex',
                }}
              >
                <X size={11} strokeWidth={1.8} />
              </button>
            </div>
            {idx < order.length - 1 && (
              <span style={{ color: 'var(--text-4)', fontSize: 13 }}>→</span>
            )}
          </div>
        );
      })}
      <button
        type="button"
        onClick={append}
        aria-label="Append node"
        className="inline-flex items-center mono"
        style={{
          fontSize: 10.5,
          padding: '4px 10px',
          background: 'transparent',
          color: 'var(--text-3)',
          border: '1px dashed var(--border)',
          borderRadius: 6,
          cursor: 'pointer',
        }}
      >
        <Plus size={11} strokeWidth={1.8} />
      </button>
      <PreviewChain value={value} linkName={linkName} fieldName={fieldName} />
    </div>
  );
}

function PreviewChain({
  value,
  linkName,
  fieldName,
}: {
  value: VerboseGraph;
  linkName: string;
  fieldName: string;
}) {
  const flat = fromVerboseChain(value, linkName, fieldName);
  if (flat.length === 0) return null;
  return (
    <span
      className="mono"
      style={{
        fontSize: 11,
        color: 'var(--text-4)',
        marginLeft: 6,
      }}
    >
      [{flat.join(', ')}]
    </span>
  );
}

function TreeLayout({ template, value, onChange }: Omit<NodeGraphBuilderProps, 'layout'>) {
  const linkNames = template.links.map((l) => l.name);
  const fieldName = template.fields[0]?.name ?? 'val';
  if (linkNames.length !== 2) {
    return (
      <div className="mono" style={{ fontSize: 11, color: 'var(--plum)' }}>
        Tree layout requires exactly 2 links (e.g. left, right). Got {linkNames.length}.
      </div>
    );
  }
  // Render as a level-order array of editable slots. We round-trip
  // through the level-order serializer so users can edit the array
  // representation directly; the verbose form is rebuilt on change.
  const flat = fromVerboseLevelOrder(value, linkNames[0], linkNames[1], fieldName);

  function setSlot(i: number, raw: string) {
    const next = [...flat];
    if (raw === '' || raw === 'null') {
      next[i] = null;
    } else {
      const n = parseInt(raw, 10);
      next[i] = Number.isNaN(n) ? raw : n;
    }
    onChange(rebuildTree(next, template));
  }

  function addSlot() {
    const next = [...flat, 0];
    onChange(rebuildTree(next, template));
  }

  function removeSlot(i: number) {
    const next = flat.filter((_, j) => j !== i);
    onChange(rebuildTree(next, template));
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-1.5">
        {flat.map((slot, i) => (
          <span
            key={i}
            className="inline-flex items-center gap-1"
            style={{
              padding: '3px 6px 3px 8px',
              background: slot === null ? 'transparent' : 'var(--bg-sunken)',
              border: slot === null ? '1px dashed var(--border)' : '1px solid var(--border)',
              borderRadius: 999,
              fontSize: 11.5,
            }}
          >
            <input
              aria-label={`Slot ${i + 1}`}
              value={slot === null ? 'null' : String(slot)}
              onChange={(e) => setSlot(i, e.target.value)}
              className="mono"
              style={{
                width: Math.max(1, String(slot ?? 'null').length) * 8 + 4,
                fontSize: 11.5,
                background: 'transparent',
                border: 0,
                outline: 'none',
                color: slot === null ? 'var(--text-4)' : 'var(--text)',
              }}
            />
            <button
              type="button"
              onClick={() => removeSlot(i)}
              aria-label={`Remove slot ${i + 1}`}
              style={{
                background: 'transparent',
                border: 0,
                cursor: 'pointer',
                color: 'var(--text-4)',
                padding: 0,
                display: 'inline-flex',
              }}
            >
              <X size={11} strokeWidth={1.8} />
            </button>
          </span>
        ))}
        <button
          type="button"
          onClick={addSlot}
          aria-label="Append slot"
          className="inline-flex items-center mono"
          style={{
            fontSize: 10.5,
            padding: '4px 10px',
            background: 'transparent',
            color: 'var(--text-3)',
            border: '1px dashed var(--border)',
            borderRadius: 999,
            cursor: 'pointer',
          }}
        >
          <Plus size={11} strokeWidth={1.8} />
        </button>
      </div>
      <span
        className="mono"
        style={{ fontSize: 11, color: 'var(--text-4)' }}
      >
        level-order: [{flat.map((v) => (v === null ? 'null' : v)).join(', ')}]
      </span>
    </div>
  );
}

function rebuildTree(values: (unknown | null)[], t: NodeTemplate): VerboseGraph {
  const fieldName = t.fields[0]?.name ?? 'val';
  const linkNames = t.links.map((l) => l.name);
  if (!values || values.length === 0 || values[0] === null) return { nodes: [], entry: null };
  const nodes: VerboseNode[] = [];
  const idForPos: Record<number, number> = {};
  for (let pos = 0; pos < values.length; pos++) {
    if (values[pos] === null) continue;
    idForPos[pos] = nodes.length;
    const linkInit: Record<string, NodeRef> = {};
    for (const ln of linkNames) linkInit[ln] = null;
    nodes.push({
      id: nodes.length,
      fields: { [fieldName]: values[pos] },
      links: linkInit,
    });
  }
  const queue: [number, number][] = [[0, idForPos[0]]];
  let cursor = 1;
  while (queue.length > 0 && cursor < values.length) {
    const next = queue.shift()!;
    const parentId = next[1];
    for (const ln of linkNames) {
      if (cursor >= values.length) break;
      const childPos = cursor++;
      if (values[childPos] === null) continue;
      const childId = idForPos[childPos];
      nodes[parentId].links[ln] = childId;
      queue.push([childPos, childId]);
    }
  }
  return { nodes, entry: 0 };
}

export function NodeGraphBuilder(props: NodeGraphBuilderProps) {
  if (props.layout === 'chain') return <ChainLayout {...props} />;
  if (props.layout === 'tree') return <TreeLayout {...props} />;
  return (
    <pre
      className="mono"
      style={{ fontSize: 11, color: 'var(--text-4)', margin: 0 }}
    >
      {formatValue(props.value)}
    </pre>
  );
}

// Re-export verbose helpers for callers that build NodeGraphBuilder values from shorthand.
export { fromVerboseChain, fromVerboseLevelOrder };
