// Visual SVG tree editor — replaces the indented-list TreeLayout. Top-down
// layout uses a tidy-tree algorithm (left-leaf count to position siblings)
// which is enough for the 0-30 node trees our test cases live in. Edges are
// straight lines; an empty child slot is a dashed circle with `+`. Hover a
// node to reveal its delete-subtree X.
//
// State model: same VerboseGraph the rest of the app uses, so this is a
// drop-in for TreeLayout.

import { useState } from 'react';
import { Plus, X, Clipboard, Copy as CopyIcon, Trash2 } from 'lucide-react';
import type { NodeTemplate } from '../types';
import {
  type VerboseGraph,
  type VerboseNode,
  fromLevelOrderShorthand,
  toLevelOrderShorthand,
} from './shorthand';
import { PanZoomSvg } from './PanZoomSvg';

interface TreeCanvasProps {
  template: NodeTemplate;
  value: VerboseGraph;
  onChange: (next: VerboseGraph) => void;
}

interface LayoutNode {
  id: number;
  cx: number;
  cy: number;
  width: number;
  depth: number;
}

interface LayoutSlot {
  parentId: number;
  link: string;
  cx: number;
  cy: number;
}

interface LayoutEdge {
  from: { x: number; y: number };
  to: { x: number; y: number };
}

const NODE_R = 18;
const H_GAP = 36;
const V_GAP = 56;
const PAD = 20;

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

// Leaf-count layout: each subtree's horizontal extent is the sum of its
// leaves * (2*NODE_R + H_GAP). Empty slots count as 1 leaf so siblings
// stay symmetrical even when a node has only one child.
function layout(
  value: VerboseGraph,
  linkNames: string[],
): { nodes: LayoutNode[]; slots: LayoutSlot[]; edges: LayoutEdge[]; width: number; height: number } {
  if (value.entry === null || linkNames.length !== 2) {
    return { nodes: [], slots: [], edges: [], width: 240, height: 120 };
  }
  const byId = new Map<number, VerboseNode>(value.nodes.map((n) => [n.id, n]));
  const SLOT = 2 * NODE_R + H_GAP;
  let maxDepth = 0;

  function leafCount(id: number | null): number {
    if (id === null) return 1;
    const node = byId.get(id);
    if (!node) return 1;
    let total = 0;
    for (const ln of linkNames) {
      const child = node.links[ln];
      total += leafCount(typeof child === 'number' ? child : null);
    }
    return Math.max(1, total);
  }

  const out: LayoutNode[] = [];
  const slots: LayoutSlot[] = [];
  const edges: LayoutEdge[] = [];

  function place(id: number | null, leftX: number, depth: number, parentXY?: { x: number; y: number; link?: string; parentId?: number }): void {
    const cy = PAD + NODE_R + depth * V_GAP;
    if (depth > maxDepth) maxDepth = depth;
    if (id === null) {
      const cx = leftX + (SLOT * 0.5);
      if (parentXY && parentXY.parentId !== undefined && parentXY.link) {
        slots.push({ parentId: parentXY.parentId, link: parentXY.link, cx, cy });
        edges.push({
          from: { x: parentXY.x, y: parentXY.y + NODE_R },
          to: { x: cx, y: cy - NODE_R },
        });
      }
      return;
    }
    const node = byId.get(id);
    if (!node) return;
    const lc = leafCount(id);
    const cx = leftX + (lc * SLOT) / 2;
    out.push({ id, cx, cy, width: lc * SLOT, depth });
    if (parentXY) {
      edges.push({
        from: { x: parentXY.x, y: parentXY.y + NODE_R },
        to: { x: cx, y: cy - NODE_R },
      });
    }
    let cursor = leftX;
    for (const ln of linkNames) {
      const child = node.links[ln];
      const childId = typeof child === 'number' ? child : null;
      const childLeaves = leafCount(childId);
      place(childId, cursor, depth + 1, { x: cx, y: cy, link: ln, parentId: id });
      cursor += childLeaves * SLOT;
    }
  }

  const totalLeaves = leafCount(value.entry);
  place(value.entry, PAD, 0);
  const width = totalLeaves * SLOT + PAD * 2 - H_GAP;
  const height = (maxDepth + 1) * V_GAP + PAD * 2;
  return { nodes: out, slots, edges, width: Math.max(240, width), height };
}

export function TreeCanvas({ template, value, onChange }: TreeCanvasProps) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [hoverId, setHoverId] = useState<number | null>(null);
  const [pasteOpen, setPasteOpen] = useState(false);
  const [pasteText, setPasteText] = useState('');
  const [pasteError, setPasteError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const linkNames = template.links.map((l) => l.name);
  const fieldDef = template.fields[0];
  const fieldName = fieldDef?.name ?? 'val';
  const fieldType = fieldDef?.type ?? 'int';

  if (linkNames.length !== 2) {
    return (
      <div className="mono" style={{ fontSize: 11, color: 'var(--plum)' }}>
        Tree canvas requires exactly 2 links (e.g. left, right). Got {linkNames.length}.
      </div>
    );
  }

  const { nodes, slots, edges, width, height } = layout(value, linkNames);
  const byId = new Map<number, VerboseNode>(value.nodes.map((n) => [n.id, n]));

  function setField(nodeId: number, raw: string) {
    onChange({
      ...value,
      nodes: value.nodes.map((n) =>
        n.id === nodeId ? { ...n, fields: { ...n.fields, [fieldName]: coerce(fieldType, raw) } } : n,
      ),
    });
  }

  function addRoot() {
    const newId = nextId(value);
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

  function removeSubtree(rootId: number) {
    const toRemove = new Set<number>();
    const queue = [rootId];
    while (queue.length > 0) {
      const id = queue.shift()!;
      if (toRemove.has(id)) continue;
      toRemove.add(id);
      const nd = byId.get(id);
      if (!nd) continue;
      for (const ln of linkNames) {
        const child = nd.links[ln];
        if (typeof child === 'number') queue.push(child);
      }
    }
    const remaining = value.nodes
      .filter((n) => !toRemove.has(n.id))
      .map((n) => {
        const newLinks = { ...n.links };
        for (const ln of linkNames) {
          if (typeof n.links[ln] === 'number' && toRemove.has(n.links[ln] as number)) {
            newLinks[ln] = null;
          }
        }
        return { ...n, links: newLinks };
      });
    onChange({
      nodes: remaining,
      entry: toRemove.has(value.entry as number) ? null : value.entry,
    });
  }

  function clearAll() {
    onChange({ nodes: [], entry: null });
  }

  function applyPaste() {
    setPasteError(null);
    try {
      const next = fromLevelOrderShorthand(pasteText, template);
      onChange(next);
      setPasteOpen(false);
      setPasteText('');
    } catch (e) {
      setPasteError(e instanceof Error ? e.message : 'invalid input');
    }
  }

  async function copyShorthand() {
    const shorthand = toLevelOrderShorthand(value, linkNames[0], linkNames[1], fieldName);
    const text = JSON.stringify(shorthand);
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {
      /* clipboard blocked — silent */
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <CanvasToolbar
        empty={value.entry === null}
        onClear={clearAll}
        onPaste={() => setPasteOpen((o) => !o)}
        onCopy={copyShorthand}
        copied={copied}
        pasteOpen={pasteOpen}
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
            placeholder="[1, null, 2, 3]"
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
              LeetCode level-order array. Press Enter to apply.
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

      {value.entry === null ? (
        <button
          type="button"
          onClick={addRoot}
          data-testid="tree-add-root"
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
          Add root
        </button>
      ) : (
        <PanZoomSvg
          contentWidth={width}
          contentHeight={height}
          displayHeight={360}
          maxDisplayHeight={360}
        >
          <>
            {edges.map((e, i) => (
              <line
                key={`e${i}`}
                x1={e.from.x}
                y1={e.from.y}
                x2={e.to.x}
                y2={e.to.y}
                stroke="var(--border-strong)"
                strokeWidth={1.5}
              />
            ))}
            {slots.map((s, i) => (
              <g
                key={`s${i}`}
                onClick={() => addChild(s.parentId, s.link)}
                style={{ cursor: 'pointer' }}
                data-testid={`tree-slot-${s.parentId}-${s.link}`}
              >
                <circle
                  cx={s.cx}
                  cy={s.cy}
                  r={NODE_R - 4}
                  fill="transparent"
                  stroke="var(--border-strong)"
                  strokeDasharray="3 3"
                  strokeWidth={1.2}
                />
                <text
                  x={s.cx}
                  y={s.cy + 4}
                  textAnchor="middle"
                  fontSize={12}
                  fill="var(--text-4)"
                  pointerEvents="none"
                >
                  +
                </text>
                <title>{`Add ${s.link} child`}</title>
              </g>
            ))}
            {nodes.map((n) => {
              const node = byId.get(n.id);
              const isEntry = n.id === value.entry;
              const isHover = hoverId === n.id;
              const isEditing = editingId === n.id;
              return (
                <g
                  key={`n${n.id}`}
                  onMouseEnter={() => setHoverId(n.id)}
                  onMouseLeave={() => setHoverId((h) => (h === n.id ? null : h))}
                >
                  <circle
                    cx={n.cx}
                    cy={n.cy}
                    r={NODE_R}
                    fill="var(--paper)"
                    stroke={isEntry ? 'var(--accent)' : 'var(--text-3)'}
                    strokeWidth={isEntry ? 2 : 1.4}
                  />
                  {!isEditing && (
                    <text
                      x={n.cx}
                      y={n.cy + 4}
                      textAnchor="middle"
                      fontSize={12}
                      fontFamily="JetBrains Mono, monospace"
                      fill="var(--text)"
                      style={{ cursor: 'text', userSelect: 'none' }}
                      onClick={() => setEditingId(n.id)}
                      data-testid={`tree-text-${n.id}`}
                    >
                      {String(node?.fields[fieldName] ?? '')}
                    </text>
                  )}
                  {isEditing && (
                    <foreignObject
                      x={n.cx - NODE_R + 2}
                      y={n.cy - 11}
                      width={NODE_R * 2 - 4}
                      height={22}
                    >
                      <input
                        autoFocus
                        type="text"
                        value={String(node?.fields[fieldName] ?? '')}
                        onChange={(e) => setField(n.id, e.target.value)}
                        onBlur={() => setEditingId(null)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === 'Escape') setEditingId(null);
                        }}
                        className="mono"
                        data-testid={`tree-input-${n.id}`}
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
                    <g
                      onClick={() => removeSubtree(n.id)}
                      style={{ cursor: 'pointer' }}
                      data-testid={`tree-remove-${n.id}`}
                    >
                      <circle
                        cx={n.cx + NODE_R - 2}
                        cy={n.cy - NODE_R + 2}
                        r={7}
                        fill="var(--paper)"
                        stroke="var(--plum)"
                        strokeWidth={1.2}
                      />
                      <text
                        x={n.cx + NODE_R - 2}
                        y={n.cy - NODE_R + 5}
                        textAnchor="middle"
                        fontSize={9}
                        fill="var(--plum)"
                        pointerEvents="none"
                      >
                        ×
                      </text>
                      <title>Remove subtree</title>
                    </g>
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
  onClear,
  onPaste,
  onCopy,
  copied,
  pasteOpen,
}: {
  empty: boolean;
  onClear: () => void;
  onPaste: () => void;
  onCopy: () => void;
  copied: boolean;
  pasteOpen: boolean;
}) {
  return (
    <div className="flex items-center gap-1.5 flex-wrap">
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

// Use the icons explicitly so the bundler keeps them; X is referenced in JSX too.
export const _icons = { X };
