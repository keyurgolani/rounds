// Visual SVG linked-list editor — replaces the horizontal chip-row
// ChainLayout. Same visual language as TreeCanvas/GraphCanvas: SVG nodes
// with click-to-edit values, hover-X to delete, toolbar with Paste/Copy
// shorthand + Clear.

import { useState } from 'react';
import { Plus, Clipboard, Copy as CopyIcon, Trash2 } from 'lucide-react';
import type { NodeTemplate } from '../types';
import {
  type VerboseGraph,
  type VerboseNode,
  type NodeRef,
  fromChainShorthand,
  toChainShorthand,
} from './shorthand';
import { PanZoomSvg } from './PanZoomSvg';

interface ChainCanvasProps {
  template: NodeTemplate;
  value: VerboseGraph;
  onChange: (next: VerboseGraph) => void;
}

const NODE_R = 18;
const H_GAP = 36;
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

function chainOrder(value: VerboseGraph, linkName: string): number[] {
  if (value.entry === null) return [];
  const byId = new Map<number, VerboseNode>(value.nodes.map((n) => [n.id, n]));
  const seen = new Set<number>();
  const out: number[] = [];
  let cur: NodeRef = value.entry;
  while (typeof cur === 'number' && !seen.has(cur)) {
    seen.add(cur);
    out.push(cur);
    cur = byId.get(cur)?.links[linkName] ?? null;
  }
  return out;
}

export function ChainCanvas({ template, value, onChange }: ChainCanvasProps) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [hoverId, setHoverId] = useState<number | null>(null);
  const [pasteOpen, setPasteOpen] = useState(false);
  const [pasteText, setPasteText] = useState('');
  const [pasteError, setPasteError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const linkName = template.links[0]?.name ?? 'next';
  const fieldDef = template.fields[0];
  const fieldName = fieldDef?.name ?? 'val';
  const fieldType = fieldDef?.type ?? 'int';

  const order = chainOrder(value, linkName);
  const byId = new Map<number, VerboseNode>(value.nodes.map((n) => [n.id, n]));
  const SLOT = 2 * NODE_R + H_GAP;
  const width = Math.max(240, order.length * SLOT + PAD * 2);
  const height = NODE_R * 2 + PAD * 2;

  function setField(nodeId: number, raw: string) {
    onChange({
      ...value,
      nodes: value.nodes.map((n) =>
        n.id === nodeId ? { ...n, fields: { ...n.fields, [fieldName]: coerce(fieldType, raw) } } : n,
      ),
    });
  }

  function append() {
    const newId = nextId(value);
    const newNode = emptyNode(template, newId);
    let nodes = [...value.nodes, newNode];
    let entry = value.entry;
    if (entry === null) {
      entry = newId;
    } else if (order.length > 0) {
      const tailId = order[order.length - 1];
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

  function clearAll() {
    onChange({ nodes: [], entry: null });
  }

  function applyPaste() {
    setPasteError(null);
    try {
      const next = fromChainShorthand(pasteText, template);
      onChange(next);
      setPasteOpen(false);
      setPasteText('');
    } catch (e) {
      setPasteError(e instanceof Error ? e.message : 'invalid input');
    }
  }

  async function copyShorthand() {
    const flat = toChainShorthand(value, linkName, fieldName);
    const text = JSON.stringify(flat);
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
      <div className="flex items-center gap-1.5 flex-wrap" data-testid="chain-toolbar">
        <ToolbarButton icon={Plus} label="Append" onClick={append} testid="chain-append" />
        <ToolbarButton
          icon={Clipboard}
          label={pasteOpen ? 'Close paste' : 'Paste shorthand'}
          onClick={() => setPasteOpen((o) => !o)}
          active={pasteOpen}
        />
        <ToolbarButton
          icon={CopyIcon}
          label={copied ? 'Copied' : 'Copy as shorthand'}
          onClick={copyShorthand}
          disabled={value.nodes.length === 0}
          accent={copied}
        />
        <span style={{ flex: 1 }} />
        <ToolbarButton
          icon={Trash2}
          label="Clear"
          onClick={clearAll}
          disabled={value.nodes.length === 0}
          danger
        />
      </div>

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
            placeholder="[2, 4, 3]"
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
              Flat array of values, head first. Press Enter to apply.
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

      {order.length === 0 ? (
        <button
          type="button"
          onClick={append}
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
          Add head
        </button>
      ) : (
        <PanZoomSvg
          contentWidth={width}
          contentHeight={height}
          displayHeight={Math.max(110, height)}
          maxDisplayHeight={Math.max(110, height)}
        >
          <>
            {order.map((id, i) => {
              if (i === order.length - 1) return null;
              const x1 = PAD + i * SLOT + NODE_R * 2;
              const x2 = PAD + (i + 1) * SLOT;
              const y = PAD + NODE_R;
              return (
                <g key={`e${i}`}>
                  <line
                    x1={x1}
                    y1={y}
                    x2={x2 - 5}
                    y2={y}
                    stroke="var(--border-strong)"
                    strokeWidth={1.5}
                  />
                  <polyline
                    points={`${x2 - 8},${y - 4} ${x2 - 2},${y} ${x2 - 8},${y + 4}`}
                    fill="none"
                    stroke="var(--border-strong)"
                    strokeWidth={1.5}
                  />
                </g>
              );
            })}
            {order.map((id, i) => {
              const node = byId.get(id);
              const cx = PAD + i * SLOT + NODE_R;
              const cy = PAD + NODE_R;
              const isHead = i === 0;
              const isHover = hoverId === id;
              const isEditing = editingId === id;
              return (
                <g
                  key={`n${id}`}
                  onMouseEnter={() => setHoverId(id)}
                  onMouseLeave={() => setHoverId((h) => (h === id ? null : h))}
                >
                  <circle
                    cx={cx}
                    cy={cy}
                    r={NODE_R}
                    fill="var(--paper)"
                    stroke={isHead ? 'var(--accent)' : 'var(--text-3)'}
                    strokeWidth={isHead ? 2 : 1.4}
                  />
                  {!isEditing && (
                    <text
                      x={cx}
                      y={cy + 4}
                      textAnchor="middle"
                      fontSize={12}
                      fontFamily="JetBrains Mono, monospace"
                      fill="var(--text)"
                      style={{ cursor: 'text', userSelect: 'none' }}
                      onClick={() => setEditingId(id)}
                      data-testid={`chain-text-${id}`}
                    >
                      {String(node?.fields[fieldName] ?? '')}
                    </text>
                  )}
                  {isEditing && (
                    <foreignObject x={cx - NODE_R + 2} y={cy - 11} width={NODE_R * 2 - 4} height={22}>
                      <input
                        autoFocus
                        type="text"
                        value={String(node?.fields[fieldName] ?? '')}
                        onChange={(e) => setField(id, e.target.value)}
                        onBlur={() => setEditingId(null)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === 'Escape') setEditingId(null);
                        }}
                        className="mono"
                        data-testid={`chain-input-${id}`}
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
                      onClick={() => removeAt(i)}
                      style={{ cursor: 'pointer' }}
                      data-testid={`chain-remove-${id}`}
                    >
                      <circle
                        cx={cx + NODE_R - 2}
                        cy={cy - NODE_R + 2}
                        r={7}
                        fill="var(--paper)"
                        stroke="var(--plum)"
                        strokeWidth={1.2}
                      />
                      <text
                        x={cx + NODE_R - 2}
                        y={cy - NODE_R + 5}
                        textAnchor="middle"
                        fontSize={9}
                        fill="var(--plum)"
                        pointerEvents="none"
                      >
                        ×
                      </text>
                      <title>Remove node</title>
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

function ToolbarButton({
  icon: Icon,
  label,
  onClick,
  active,
  disabled,
  danger,
  accent,
  testid,
}: {
  icon: typeof Plus;
  label: string;
  onClick: () => void;
  active?: boolean;
  disabled?: boolean;
  danger?: boolean;
  accent?: boolean;
  testid?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={label}
      data-testid={testid}
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
