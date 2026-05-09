// Visual SVG graph editor — replaces the row-list GraphLayout. Nodes are
// laid out on a circle (or 2-row grid for large graphs); edges are
// straight lines between node centers. Interaction model:
//   - Click empty space → add a node at that position (snaps to circle).
//   - Click a node → select it (orange ring).
//   - Click a second node → toggle an edge between selected and clicked.
//   - Click selected node again → deselect (so you can do "set as entry").
//   - Hover a node → reveals an X for delete + a star to mark entry.
//
// State model: same VerboseGraph as the rest of the app, drop-in for
// GraphLayout.

import { useState } from 'react';
import { Plus, Clipboard, Copy as CopyIcon, Trash2, X, Star } from 'lucide-react';
import type { NodeTemplate } from '../types';
import {
  type VerboseGraph,
  type VerboseNode,
  type NodeRef,
  fromAdjacencyShorthand,
  toAdjacencyShorthand,
} from './shorthand';
import { PanZoomSvg } from './PanZoomSvg';

interface GraphCanvasProps {
  template: NodeTemplate;
  value: VerboseGraph;
  onChange: (next: VerboseGraph) => void;
}

const NODE_R = 20;
const PAD = 24;

function coerce(type: string, raw: string): unknown {
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

function circularLayout(count: number): { width: number; height: number; positions: { x: number; y: number }[] } {
  if (count === 0) return { width: 360, height: 220, positions: [] };
  const minRadius = 60;
  const radius = Math.max(minRadius, count * 14);
  const cx = radius + PAD + NODE_R;
  const cy = radius + PAD + NODE_R;
  const positions: { x: number; y: number }[] = [];
  for (let i = 0; i < count; i++) {
    const angle = (i / count) * Math.PI * 2 - Math.PI / 2;
    positions.push({
      x: cx + Math.cos(angle) * radius,
      y: cy + Math.sin(angle) * radius,
    });
  }
  const dim = (radius + PAD + NODE_R) * 2;
  return { width: Math.max(360, dim), height: Math.max(220, dim), positions };
}

export function GraphCanvas({ template, value, onChange }: GraphCanvasProps) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [hoverId, setHoverId] = useState<number | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [pasteOpen, setPasteOpen] = useState(false);
  const [pasteText, setPasteText] = useState('');
  const [pasteError, setPasteError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const linkName = template.links[0]?.name ?? 'neighbors';
  const fieldDef = template.fields[0];
  const fieldName = fieldDef?.name ?? 'val';
  const fieldType = fieldDef?.type ?? 'int';

  const { width, height, positions } = circularLayout(value.nodes.length);
  const posById = new Map<number, { x: number; y: number }>();
  value.nodes.forEach((n, i) => posById.set(n.id, positions[i]));

  // Undirected edges as deduplicated unordered pairs (so we draw one line
  // per pair even if both endpoints list each other in their neighbors).
  const edgeSet = new Set<string>();
  const edges: { a: number; b: number }[] = [];
  for (const n of value.nodes) {
    const links = n.links[linkName];
    const arr: NodeRef[] = Array.isArray(links) ? links : [];
    for (const ref of arr) {
      if (typeof ref !== 'number') continue;
      if (!posById.has(ref)) continue;
      const key = n.id < ref ? `${n.id}-${ref}` : `${ref}-${n.id}`;
      if (edgeSet.has(key)) continue;
      edgeSet.add(key);
      edges.push({ a: n.id, b: ref });
    }
  }

  function setField(nodeId: number, raw: string) {
    onChange({
      ...value,
      nodes: value.nodes.map((n) =>
        n.id === nodeId ? { ...n, fields: { ...n.fields, [fieldName]: coerce(fieldType, raw) } } : n,
      ),
    });
  }

  function addNode() {
    const newId = nextId(value);
    const next = emptyNode(template, newId);
    onChange({
      nodes: [...value.nodes, next],
      entry: value.entry === null ? newId : value.entry,
    });
  }

  function removeNode(nodeId: number) {
    const remaining = value.nodes
      .filter((n) => n.id !== nodeId)
      .map((n) => {
        const links = n.links[linkName];
        const arr: NodeRef[] = Array.isArray(links) ? links : [];
        return {
          ...n,
          links: { ...n.links, [linkName]: arr.filter((r) => r !== nodeId) },
        };
      });
    let entry = value.entry;
    if (entry === nodeId) entry = remaining.length > 0 ? remaining[0].id : null;
    onChange({ nodes: remaining, entry });
    if (selectedId === nodeId) setSelectedId(null);
  }

  function toggleEdge(a: number, b: number) {
    if (a === b) return;
    onChange({
      ...value,
      nodes: value.nodes.map((n) => {
        if (n.id !== a && n.id !== b) return n;
        const other = n.id === a ? b : a;
        const links = n.links[linkName];
        const arr: NodeRef[] = Array.isArray(links) ? links : [];
        const has = arr.includes(other);
        return {
          ...n,
          links: {
            ...n.links,
            [linkName]: has ? arr.filter((r) => r !== other) : [...arr, other],
          },
        };
      }),
    });
  }

  function setEntry(nodeId: number) {
    onChange({ ...value, entry: nodeId });
  }

  function clickNode(nodeId: number) {
    if (selectedId === null) {
      setSelectedId(nodeId);
      return;
    }
    if (selectedId === nodeId) {
      setSelectedId(null);
      return;
    }
    toggleEdge(selectedId, nodeId);
    setSelectedId(null);
  }

  function clearAll() {
    onChange({ nodes: [], entry: null });
    setSelectedId(null);
  }

  function applyPaste() {
    setPasteError(null);
    try {
      const next = fromAdjacencyShorthand(pasteText, template);
      onChange(next);
      setPasteOpen(false);
      setPasteText('');
    } catch (e) {
      setPasteError(e instanceof Error ? e.message : 'invalid input');
    }
  }

  async function copyShorthand() {
    const adj = toAdjacencyShorthand(value, linkName, fieldName);
    const text = JSON.stringify(adj);
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {
      /* clipboard blocked */
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <CanvasToolbar
        empty={value.nodes.length === 0}
        onAdd={addNode}
        onClear={clearAll}
        onPaste={() => setPasteOpen((o) => !o)}
        onCopy={copyShorthand}
        copied={copied}
        pasteOpen={pasteOpen}
        selectedHint={
          selectedId !== null
            ? `selected #${selectedId} — click another to toggle edge`
            : value.nodes.length > 0
              ? 'click a node to select, then click another to toggle edge'
              : null
        }
      />

      {pasteOpen && (
        <div
          className="flex flex-col gap-1.5"
          style={{
            padding: 8,
            background: 'var(--bg-elev)',
            border: '1px solid var(--border)',
            borderRadius: 6,
          }}
        >
          <input
            type="text"
            value={pasteText}
            onChange={(e) => {
              setPasteText(e.target.value);
              setPasteError(null);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') applyPaste();
              if (e.key === 'Escape') setPasteOpen(false);
            }}
            placeholder='{"1": [2, 3], "2": [1], "3": [1]}'
            autoFocus
            className="mono"
            style={{
              width: '100%',
              padding: '6px 8px',
              fontSize: 11.5,
              background: 'var(--paper)',
              border: '1px solid var(--border)',
              borderRadius: 4,
              outline: 'none',
            }}
          />
          {pasteError ? (
            <span className="mono" style={{ fontSize: 10.5, color: 'var(--plum)' }}>
              {pasteError}
            </span>
          ) : (
            <span className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)' }}>
              Adjacency dict keyed by node value. Press Enter to apply.
            </span>
          )}
          <div className="flex gap-1.5">
            <button
              type="button"
              onClick={applyPaste}
              style={{
                padding: '4px 10px',
                fontSize: 11,
                background: 'var(--ink)',
                color: 'var(--paper)',
                border: 0,
                borderRadius: 4,
                cursor: 'pointer',
              }}
            >
              Apply
            </button>
            <button
              type="button"
              onClick={() => setPasteOpen(false)}
              style={{
                padding: '4px 10px',
                fontSize: 11,
                background: 'transparent',
                color: 'var(--text-3)',
                border: '1px solid var(--border)',
                borderRadius: 4,
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {value.nodes.length === 0 ? (
        <button
          type="button"
          onClick={addNode}
          data-testid="graph-add-first"
          className="inline-flex items-center gap-1.5 mono"
          style={{
            alignSelf: 'flex-start',
            padding: '8px 14px',
            fontSize: 11.5,
            background: 'transparent',
            color: 'var(--text-3)',
            border: '1px dashed var(--border-strong)',
            borderRadius: 999,
            cursor: 'pointer',
          }}
        >
          <Plus size={12} strokeWidth={1.8} />
          Add first node
        </button>
      ) : (
        <PanZoomSvg
          contentWidth={width}
          contentHeight={height}
          displayHeight={420}
          maxDisplayHeight={420}
        >
          <>
            {edges.map((e, i) => {
              const a = posById.get(e.a)!;
              const b = posById.get(e.b)!;
              return (
                <line
                  key={`e${i}`}
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  stroke="var(--border-strong)"
                  strokeWidth={1.5}
                />
              );
            })}
            {value.nodes.map((n) => {
              const pos = posById.get(n.id)!;
              const isEntry = n.id === value.entry;
              const isSelected = selectedId === n.id;
              const isHover = hoverId === n.id;
              const isEditing = editingId === n.id;
              return (
                <g
                  key={`n${n.id}`}
                  data-testid={`graph-node-${n.id}`}
                  onMouseEnter={() => setHoverId(n.id)}
                  onMouseLeave={() => setHoverId((h) => (h === n.id ? null : h))}
                >
                  <circle
                    cx={pos.x}
                    cy={pos.y}
                    r={NODE_R}
                    fill={isEntry ? 'var(--accent-soft)' : 'var(--paper)'}
                    stroke={
                      isSelected
                        ? 'var(--ochre)'
                        : isEntry
                          ? 'var(--accent)'
                          : 'var(--text-3)'
                    }
                    strokeWidth={isSelected ? 2.5 : isEntry ? 2 : 1.4}
                    style={{ cursor: isEditing ? 'text' : 'pointer' }}
                    onClick={() => !isEditing && clickNode(n.id)}
                    data-testid={`graph-circle-${n.id}`}
                  />
                  {!isEditing && (
                    <text
                      x={pos.x}
                      y={pos.y + 4}
                      textAnchor="middle"
                      fontSize={12}
                      fontFamily="JetBrains Mono, monospace"
                      fill="var(--text)"
                      style={{ cursor: 'text', userSelect: 'none' }}
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingId(n.id);
                      }}
                      data-testid={`graph-text-${n.id}`}
                    >
                      {String(n.fields[fieldName] ?? '')}
                    </text>
                  )}
                  {isEditing && (
                    <foreignObject
                      x={pos.x - NODE_R + 2}
                      y={pos.y - 11}
                      width={NODE_R * 2 - 4}
                      height={22}
                    >
                      <input
                        autoFocus
                        type="text"
                        value={String(n.fields[fieldName] ?? '')}
                        onChange={(e) => setField(n.id, e.target.value)}
                        onBlur={() => setEditingId(null)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === 'Escape') setEditingId(null);
                        }}
                        className="mono"
                        data-testid={`graph-input-${n.id}`}
                        style={{
                          width: '100%',
                          height: '100%',
                          padding: 0,
                          textAlign: 'center',
                          fontSize: 12,
                          background: 'transparent',
                          border: 0,
                          outline: 'none',
                          color: 'var(--text)',
                        }}
                      />
                    </foreignObject>
                  )}
                  {isHover && !isEditing && (
                    <>
                      {!isEntry && (
                        <g
                          onClick={(e) => {
                            e.stopPropagation();
                            setEntry(n.id);
                          }}
                          style={{ cursor: 'pointer' }}
                          data-testid={`graph-set-entry-${n.id}`}
                        >
                          <circle
                            cx={pos.x - NODE_R + 2}
                            cy={pos.y - NODE_R + 2}
                            r={7}
                            fill="var(--paper)"
                            stroke="var(--accent)"
                            strokeWidth={1.2}
                          />
                          <Star
                            x={pos.x - NODE_R + 2 - 4}
                            y={pos.y - NODE_R + 2 - 4}
                            size={8}
                            color="var(--accent)"
                            strokeWidth={1.5}
                          />
                          <title>Set as entry</title>
                        </g>
                      )}
                      <g
                        onClick={(e) => {
                          e.stopPropagation();
                          removeNode(n.id);
                        }}
                        style={{ cursor: 'pointer' }}
                        data-testid={`graph-remove-${n.id}`}
                      >
                        <circle
                          cx={pos.x + NODE_R - 2}
                          cy={pos.y - NODE_R + 2}
                          r={7}
                          fill="var(--paper)"
                          stroke="var(--plum)"
                          strokeWidth={1.2}
                        />
                        <text
                          x={pos.x + NODE_R - 2}
                          y={pos.y - NODE_R + 5}
                          textAnchor="middle"
                          fontSize={9}
                          fill="var(--plum)"
                          pointerEvents="none"
                        >
                          ×
                        </text>
                        <title>Remove node</title>
                      </g>
                    </>
                  )}
                </g>
              );
            })}
          </>
        </PanZoomSvg>
      )}
    </div>
  );
}

function CanvasToolbar({
  empty,
  onAdd,
  onClear,
  onPaste,
  onCopy,
  copied,
  pasteOpen,
  selectedHint,
}: {
  empty: boolean;
  onAdd: () => void;
  onClear: () => void;
  onPaste: () => void;
  onCopy: () => void;
  copied: boolean;
  pasteOpen: boolean;
  selectedHint: string | null;
}) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1.5 flex-wrap">
        <ToolbarButton icon={Plus} label="Add node" onClick={onAdd} />
        <ToolbarButton
          icon={Clipboard}
          label={pasteOpen ? 'Close paste' : 'Paste shorthand'}
          onClick={onPaste}
          active={pasteOpen}
        />
        <ToolbarButton
          icon={CopyIcon}
          label={copied ? 'Copied' : 'Copy as shorthand'}
          onClick={onCopy}
          disabled={empty}
          accent={copied}
        />
        <span style={{ flex: 1 }} />
        <ToolbarButton
          icon={Trash2}
          label="Clear"
          onClick={onClear}
          disabled={empty}
          danger
        />
      </div>
      {selectedHint && (
        <span className="mono" style={{ fontSize: 10, color: 'var(--text-4)' }}>
          {selectedHint}
        </span>
      )}
    </div>
  );
}

function ToolbarButton({
  icon: Icon,
  label,
  onClick,
  active,
  disabled,
  danger,
  accent,
}: {
  icon: typeof Plus;
  label: string;
  onClick: () => void;
  active?: boolean;
  disabled?: boolean;
  danger?: boolean;
  accent?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={label}
      className="inline-flex items-center gap-1 mono"
      style={{
        padding: '4px 8px',
        fontSize: 10.5,
        background: active ? 'var(--accent-soft)' : 'transparent',
        color: disabled
          ? 'var(--text-4)'
          : danger
            ? 'var(--plum)'
            : accent
              ? 'var(--forest)'
              : active
                ? 'var(--accent)'
                : 'var(--text-3)',
        border: '1px solid var(--border)',
        borderRadius: 4,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
      }}
    >
      <Icon size={11} strokeWidth={1.8} />
      {label}
    </button>
  );
}

// Re-export icons for tests/typing — also keeps tree-shaking honest.
export const _icons = { X };
