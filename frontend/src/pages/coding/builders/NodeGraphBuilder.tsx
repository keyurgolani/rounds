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

function nextId(g: VerboseGraph): number {
  return g.nodes.reduce((m, n) => Math.max(m, n.id), -1) + 1;
}

function mapNodes(g: VerboseGraph, fn: (n: VerboseNode) => VerboseNode): VerboseGraph {
  return { ...g, nodes: g.nodes.map(fn) };
}

/* ------------------------------------------------------------------ */
/*  Chain (linked list)                                               */
/* ------------------------------------------------------------------ */

function ChainLayout({ template, value, onChange }: Omit<NodeGraphBuilderProps, 'layout'>) {
  const linkName = template.links[0]?.name ?? 'next';
  const fieldName = template.fields[0]?.name ?? 'val';

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
    onChange(mapNodes(value, (n) =>
      n.id === id ? { ...n, fields: { ...n.fields, [name]: coerce(type, raw) } } : n,
    ));
  }

  function append() {
    const newId = nextId(value) || 0;
    const newNode = emptyNode(template, newId);
    let nodes = [...value.nodes, newNode];
    let entry = value.entry;
    if (entry === null) {
      entry = newId;
    } else {
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
    onChange({ nodes, entry: newOrder.length > 0 ? newOrder[0] : null });
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
                style={{ background: 'transparent', border: 0, cursor: 'pointer', color: 'var(--text-4)', padding: 0, display: 'inline-flex' }}
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

function PreviewChain({ value, linkName, fieldName }: { value: VerboseGraph; linkName: string; fieldName: string }) {
  const flat = fromVerboseChain(value, linkName, fieldName);
  if (flat.length === 0) return null;
  return (
    <span className="mono" style={{ fontSize: 11, color: 'var(--text-4)', marginLeft: 6 }}>
      [{flat.join(', ')}]
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  Tree                                                              */
/* ------------------------------------------------------------------ */

const TREE_BRANCH: React.CSSProperties = {
  display: 'inline-block',
  width: 20,
  color: 'var(--border-strong)',
  fontFamily: 'monospace',
  fontSize: 11,
  userSelect: 'none',
  flexShrink: 0,
};

const ADD_BTN: React.CSSProperties = {
  fontSize: 10.5,
  padding: '3px 8px',
  background: 'transparent',
  color: 'var(--text-3)',
  border: '1px dashed var(--border)',
  borderRadius: 4,
  cursor: 'pointer',
  display: 'inline-flex',
  alignItems: 'center',
  gap: 3,
};

function TreeLayout({ template, value, onChange }: Omit<NodeGraphBuilderProps, 'layout'>) {
  const linkNames = template.links.map((l) => l.name);
  const fieldDef = template.fields[0];
  const fieldName = fieldDef?.name ?? 'val';
  const fieldType = fieldDef?.type ?? 'int';

  if (linkNames.length !== 2) {
    return (
      <div className="mono" style={{ fontSize: 11, color: 'var(--plum)' }}>
        Tree layout requires exactly 2 links (e.g. left, right). Got {linkNames.length}.
      </div>
    );
  }

  const byId = new Map<number, VerboseNode>(value.nodes.map((n) => [n.id, n]));

  function setField(nodeId: number, raw: string) {
    onChange(mapNodes(value, (n) =>
      n.id === nodeId ? { ...n, fields: { ...n.fields, [fieldName]: coerce(fieldType, raw) } } : n,
    ));
  }

  function addRoot() {
    const newId = nextId(value) || 0;
    onChange({ nodes: [...value.nodes, emptyNode(template, newId)], entry: newId });
  }

  function addChild(parentId: number, linkName: string) {
    const newId = nextId(value);
    onChange({
      nodes: [
        ...value.nodes.map((n) =>
          n.id === parentId ? { ...n, links: { ...n.links, [linkName]: newId } } : n,
        ),
        emptyNode(template, newId),
      ],
      entry: value.entry,
    });
  }

  function removeSubtree(nodeId: number) {
    const toRemove = new Set<number>();
    const q = [nodeId];
    while (q.length > 0) {
      const id = q.shift()!;
      if (toRemove.has(id)) continue;
      toRemove.add(id);
      const nd = byId.get(id);
      if (!nd) continue;
      for (const ln of linkNames) {
        const c = nd.links[ln];
        if (typeof c === 'number') q.push(c);
      }
    }
    const remaining = value.nodes
      .filter((n) => !toRemove.has(n.id))
      .map((n) => {
        const newLinks = { ...n.links };
        for (const ln of linkNames) {
          if (toRemove.has(n.links[ln] as number)) newLinks[ln] = null;
        }
        return { ...n, links: newLinks };
      });
    onChange({ nodes: remaining, entry: toRemove.has(value.entry!) ? null : value.entry });
  }

  if (value.entry === null) {
    return (
      <button type="button" onClick={addRoot} style={ADD_BTN} aria-label="Add root node">
        <Plus size={11} strokeWidth={1.8} /> Add root
      </button>
    );
  }

  return (
    <div className="flex flex-col gap-0.5">
      <TreeNodeRow
        nodeId={value.entry}
        byId={byId}
        template={template}
        linkNames={linkNames}
        fieldName={fieldName}
        fieldType={fieldType}
        onSetField={setField}
        onAddChild={addChild}
        onRemove={removeSubtree}
        prefix={[]}
      />
    </div>
  );
}

function TreeNodeRow({
  nodeId,
  byId,
  template,
  linkNames,
  fieldName,
  fieldType,
  onSetField,
  onAddChild,
  onRemove,
  prefix,
}: {
  nodeId: number;
  byId: Map<number, VerboseNode>;
  template: NodeTemplate;
  linkNames: string[];
  fieldName: string;
  fieldType: string;
  onSetField: (id: number, raw: string) => void;
  onAddChild: (parentId: number, linkName: string) => void;
  onRemove: (id: number) => void;
  prefix: string[];
}) {
  const node = byId.get(nodeId);
  if (!node) return null;

  const childRows: React.ReactNode[] = [];
  for (let li = 0; li < linkNames.length; li++) {
    const ln = linkNames[li];
    const childId = node.links[ln];
    const label = ln === 'left' ? 'L' : ln === 'right' ? 'R' : ln[0];
    if (typeof childId === 'number' && byId.has(childId)) {
      childRows.push(
        <TreeNodeRow
          key={childId}
          nodeId={childId}
          byId={byId}
          template={template}
          linkNames={linkNames}
          fieldName={fieldName}
          fieldType={fieldType}
          onSetField={onSetField}
          onAddChild={onAddChild}
          onRemove={onRemove}
          prefix={[...prefix, label]}
        />,
      );
    } else {
      childRows.push(
        <div key={`empty-${ln}`} className="flex items-center" style={{ paddingLeft: prefix.length * 20 }}>
          <span style={TREE_BRANCH}>  {prefix.length === 0 ? '' : '├─'}{label}:</span>
          <button type="button" onClick={() => onAddChild(nodeId, ln)} style={ADD_BTN} aria-label={`Add ${ln} child`}>
            <Plus size={10} strokeWidth={1.8} /> {label}
          </button>
        </div>,
      );
    }
  }

  return (
    <>
      <div className="flex items-center gap-1" style={{ paddingLeft: prefix.length * 20 }}>
        {prefix.length === 0 && <span style={{ ...TREE_BRANCH, color: 'var(--text-4)' }}>root</span>}
        {prefix.length > 0 && (
          <span style={TREE_BRANCH}>  ├─{prefix[prefix.length - 1]}:</span>
        )}
        <div
          className="flex items-center gap-1"
          style={{
            padding: '3px 6px 3px 8px',
            background: 'var(--bg-sunken)',
            border: '1px solid var(--border)',
            borderRadius: 6,
          }}
        >
          <input
            aria-label={`Node ${nodeId} ${fieldName}`}
            value={String(node.fields[fieldName] ?? '')}
            onChange={(e) => onSetField(nodeId, e.target.value)}
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
          <button
            type="button"
            onClick={() => onRemove(nodeId)}
            aria-label={`Remove node ${nodeId}`}
            style={{ background: 'transparent', border: 0, cursor: 'pointer', color: 'var(--text-4)', padding: 0, display: 'inline-flex' }}
          >
            <X size={11} strokeWidth={1.8} />
          </button>
        </div>
      </div>
      {childRows}
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  Graph                                                             */
/* ------------------------------------------------------------------ */

function GraphLayout({ template, value, onChange }: Omit<NodeGraphBuilderProps, 'layout'>) {
  const linkName = template.links[0]?.name ?? 'neighbors';
  const fieldDef = template.fields[0];
  const fieldName = fieldDef?.name ?? 'val';
  const fieldType = fieldDef?.type ?? 'int';
  const byId = new Map<number, VerboseNode>(value.nodes.map((n) => [n.id, n]));

  function setField(nodeId: number, raw: string) {
    onChange(mapNodes(value, (n) =>
      n.id === nodeId ? { ...n, fields: { ...n.fields, [fieldName]: coerce(fieldType, raw) } } : n,
    ));
  }

  function addNode() {
    const newId = nextId(value);
    onChange({ ...value, nodes: [...value.nodes, emptyNode(template, newId)] });
  }

  function removeNode(nodeId: number) {
    const remaining = value.nodes.filter((n) => n.id !== nodeId);
    const fixed = remaining.map((n) => ({
      ...n,
      links: {
        ...n.links,
        [linkName]: (Array.isArray(n.links[linkName]) ? n.links[linkName] : []).filter(
          (id: NodeRef) => id !== nodeId,
        ),
      },
    }));
    const entry = value.entry === nodeId ? (fixed.length > 0 ? fixed[0].id : null) : value.entry;
    onChange({ nodes: fixed, entry });
  }

  function addNeighbor(nodeId: number, targetId: number) {
    onChange(mapNodes(value, (n) => {
      if (n.id !== nodeId) return n;
      const neighbors: NodeRef[] = Array.isArray(n.links[linkName])
        ? [...n.links[linkName]]
        : [];
      if (!neighbors.includes(targetId)) neighbors.push(targetId);
      return { ...n, links: { ...n.links, [linkName]: neighbors } };
    }));
  }

  function removeNeighbor(nodeId: number, targetId: number) {
    onChange(mapNodes(value, (n) => {
      if (n.id !== nodeId) return n;
      const neighbors: NodeRef[] = Array.isArray(n.links[linkName])
        ? n.links[linkName]
        : [];
      return { ...n, links: { ...n.links, [linkName]: neighbors.filter((id) => id !== targetId) } };
    }));
  }

  if (value.nodes.length === 0) {
    return (
      <button type="button" onClick={addNode} style={ADD_BTN} aria-label="Add node">
        <Plus size={11} strokeWidth={1.8} /> Add node
      </button>
    );
  }

  return (
    <div className="flex flex-col gap-1.5">
      {value.nodes.map((node) => {
        const neighbors: NodeRef[] = Array.isArray(node.links[linkName])
          ? node.links[linkName]
          : [];
        const others = value.nodes.filter((n) => n.id !== node.id);
        return (
          <div
            key={node.id}
            className="flex flex-wrap items-center gap-1.5"
            style={{
              padding: '5px 8px',
              background: 'var(--bg-sunken)',
              border: '1px solid var(--border)',
              borderRadius: 6,
            }}
          >
            <span className="mono" style={{ fontSize: 10, color: 'var(--text-4)', width: 18 }}>
              {node.id}
            </span>
            <input
              aria-label={`Node ${node.id} ${fieldName}`}
              value={String(node.fields[fieldName] ?? '')}
              onChange={(e) => setField(node.id, e.target.value)}
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
            <span style={{ color: 'var(--border-strong)', fontSize: 11 }}>→</span>
            {neighbors.map((nid) => {
              const target = byId.get(nid as number);
              return (
                <span
                  key={String(nid)}
                  className="inline-flex items-center gap-0.5 mono"
                  style={{
                    padding: '2px 6px',
                    background: 'var(--bg-elev)',
                    border: '1px solid var(--border)',
                    borderRadius: 4,
                    fontSize: 11,
                  }}
                >
                  {target ? String(target.fields[fieldName]) : String(nid)}
                  <button
                    type="button"
                    onClick={() => removeNeighbor(node.id, nid as number)}
                    aria-label={`Remove neighbor ${String(nid)}`}
                    style={{ background: 'transparent', border: 0, cursor: 'pointer', color: 'var(--text-4)', padding: 0, display: 'inline-flex' }}
                  >
                    <X size={10} strokeWidth={1.8} />
                  </button>
                </span>
              );
            })}
            {others.length > 0 && (
              <select
                aria-label={`Add neighbor to node ${node.id}`}
                onChange={(e) => {
                  const v = parseInt(e.target.value, 10);
                  if (!Number.isNaN(v)) addNeighbor(node.id, v);
                  e.target.value = '';
                }}
                defaultValue=""
                className="mono"
                style={{
                  fontSize: 10.5,
                  padding: '2px 4px',
                  background: 'transparent',
                  border: '1px dashed var(--border)',
                  borderRadius: 4,
                  color: 'var(--text-3)',
                  cursor: 'pointer',
                }}
              >
                <option value="" disabled>
                  + neighbor
                </option>
                {others.map((o) => (
                  <option key={o.id} value={o.id}>
                    {String(o.fields[fieldName])}
                  </option>
                ))}
              </select>
            )}
            <button
              type="button"
              onClick={() => removeNode(node.id)}
              aria-label={`Remove node ${node.id}`}
              style={{ marginLeft: 'auto', background: 'transparent', border: 0, cursor: 'pointer', color: 'var(--text-4)', padding: 0, display: 'inline-flex' }}
            >
              <X size={11} strokeWidth={1.8} />
            </button>
          </div>
        );
      })}
      <button
        type="button"
        onClick={addNode}
        aria-label="Add node"
        className="inline-flex items-center mono"
        style={{
          ...ADD_BTN,
          alignSelf: 'flex-start',
        }}
      >
        <Plus size={11} strokeWidth={1.8} /> node
      </button>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Dispatch                                                          */
/* ------------------------------------------------------------------ */

export function NodeGraphBuilder(props: NodeGraphBuilderProps) {
  if (props.layout === 'chain') return <ChainLayout {...props} />;
  if (props.layout === 'tree') return <TreeLayout {...props} />;
  if (props.layout === 'general') return <GraphLayout {...props} />;
  return (
    <pre className="mono" style={{ fontSize: 11, color: 'var(--text-4)', margin: 0 }}>
      {formatValue(props.value)}
    </pre>
  );
}

// Re-export verbose helpers for callers that build NodeGraphBuilder values from shorthand.
export { fromVerboseChain, fromVerboseLevelOrder };
