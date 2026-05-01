// Native ER diagram renderer — replaces Mermaid for `erDiagram` blocks.
// Entities are rendered as branded "table" cards (matching the DB schema
// cards used elsewhere in the page) arranged in a grid, with SVG bezier
// connectors between related entities and cardinality pills at each end.

import { useId, useMemo, useState } from 'react';
import type { ERCardinality, ERData, EREntity, ERRelation } from './parseER';

const CARD_W = 252;
const HEADER_H = 46;
const ROW_H = 26;
const PAD_V = 14;
const H_GAP = 68;
const V_GAP = 72;
const PADDING = 28;

interface EntityBox {
  name: string;
  x: number;
  y: number;
  w: number;
  h: number;
  entity: EREntity;
}

type Side = 'top' | 'bottom' | 'left' | 'right';

function heightOf(entity: EREntity): number {
  return HEADER_H + entity.columns.length * ROW_H + PAD_V * 2;
}

function perRow(count: number): number {
  if (count <= 2) return count;
  if (count <= 4) return 2;
  if (count <= 6) return 3;
  return 3;
}

function layout(data: ERData): { boxes: EntityBox[]; width: number; height: number } {
  // Order entities by relation degree so dense hubs sit near the center.
  const degree = new Map<string, number>();
  for (const e of data.entities) degree.set(e.name, 0);
  for (const r of data.relations) {
    degree.set(r.source, (degree.get(r.source) ?? 0) + 1);
    degree.set(r.target, (degree.get(r.target) ?? 0) + 1);
  }
  const sorted = [...data.entities].sort(
    (a, b) => (degree.get(b.name) ?? 0) - (degree.get(a.name) ?? 0),
  );

  const cols = perRow(sorted.length);
  const rows: EREntity[][] = [];
  for (let i = 0; i < sorted.length; i += cols) {
    rows.push(sorted.slice(i, i + cols));
  }

  const rowHeights = rows.map((row) => Math.max(...row.map(heightOf)));
  const maxRowW = cols * CARD_W + (cols - 1) * H_GAP;
  const width = maxRowW + PADDING * 2;

  const boxes: EntityBox[] = [];
  let y = PADDING;
  for (let r = 0; r < rows.length; r++) {
    const row = rows[r];
    const rowW = row.length * CARD_W + (row.length - 1) * H_GAP;
    const startX = (width - rowW) / 2;
    row.forEach((entity, i) => {
      boxes.push({
        name: entity.name,
        x: startX + i * (CARD_W + H_GAP),
        y,
        w: CARD_W,
        h: heightOf(entity),
        entity,
      });
    });
    y += rowHeights[r] + V_GAP;
  }
  const height = y - V_GAP + PADDING;
  return { boxes, width, height };
}

function sideAnchor(box: EntityBox, side: Side): { x: number; y: number } {
  switch (side) {
    case 'top':
      return { x: box.x + box.w / 2, y: box.y };
    case 'bottom':
      return { x: box.x + box.w / 2, y: box.y + box.h };
    case 'left':
      return { x: box.x, y: box.y + box.h / 2 };
    case 'right':
      return { x: box.x + box.w, y: box.y + box.h / 2 };
  }
}

function pickSides(a: EntityBox, b: EntityBox): { aSide: Side; bSide: Side } {
  const dx = b.x + b.w / 2 - (a.x + a.w / 2);
  const dy = b.y + b.h / 2 - (a.y + a.h / 2);
  if (Math.abs(dx) > Math.abs(dy)) {
    return dx > 0 ? { aSide: 'right', bSide: 'left' } : { aSide: 'left', bSide: 'right' };
  }
  return dy > 0 ? { aSide: 'bottom', bSide: 'top' } : { aSide: 'top', bSide: 'bottom' };
}

function bezierBetween(
  p1: { x: number; y: number },
  p2: { x: number; y: number },
  aSide: Side,
  bSide: Side,
): string {
  const horizA = aSide === 'left' || aSide === 'right';
  const horizB = bSide === 'left' || bSide === 'right';
  const dx = (p2.x - p1.x) * 0.5;
  const dy = (p2.y - p1.y) * 0.5;
  const c1 = horizA ? { x: p1.x + dx, y: p1.y } : { x: p1.x, y: p1.y + dy };
  const c2 = horizB ? { x: p2.x - dx, y: p2.y } : { x: p2.x, y: p2.y - dy };
  return `M ${p1.x},${p1.y} C ${c1.x},${c1.y} ${c2.x},${c2.y} ${p2.x},${p2.y}`;
}

function cardinalityLabel(c: ERCardinality): string {
  switch (c) {
    case 'one':
      return '1';
    case 'many':
      return 'N';
    case 'zero-or-one':
      return '0..1';
    case 'zero-or-many':
      return '0..N';
  }
}

function EntityCard({ box }: { box: EntityBox }) {
  const [hover, setHover] = useState(false);
  const { entity } = box;

  return (
    <div
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        position: 'absolute',
        left: box.x,
        top: box.y,
        width: box.w,
        minHeight: box.h,
        background: 'var(--bg-elev)',
        border: '1px solid var(--border-strong)',
        borderRadius: 'var(--radius)',
        boxShadow: hover ? 'var(--shadow-card-hover)' : 'var(--shadow-card)',
        transition: 'box-shadow 0.15s ease, transform 0.15s ease',
        transform: hover ? 'translateY(-1px)' : undefined,
        overflow: 'hidden',
        boxSizing: 'border-box',
      }}
    >
      <div
        style={{
          padding: '10px 14px',
          background: 'var(--bg-sunken)',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 10,
        }}
      >
        <span
          className="eyebrow"
          style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 9.5 }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: 999,
              background: 'var(--accent)',
              display: 'inline-block',
            }}
          />
          Entity
        </span>
        <span
          className="mono"
          style={{ fontSize: 10, color: 'var(--text-4)' }}
        >
          {entity.columns.length} col{entity.columns.length === 1 ? '' : 's'}
        </span>
      </div>
      <div style={{ padding: '10px 14px' }}>
        <h4
          className="display-italic"
          style={{
            fontSize: 18,
            fontWeight: 400,
            lineHeight: 1.1,
            marginBottom: 8,
            color: 'var(--text)',
          }}
        >
          {entity.name}
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          {entity.columns.map((col, i) => (
            <div
              key={`${col.name}-${i}`}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 8,
                padding: '5px 0',
                borderBottom:
                  i < entity.columns.length - 1
                    ? '1px dashed var(--border)'
                    : 'none',
                fontSize: 11.5,
              }}
            >
              <span
                className="mono"
                style={{
                  color: 'var(--text-2)',
                  fontWeight: col.keys.includes('PK') ? 600 : 400,
                }}
              >
                {col.name}
              </span>
              <span style={{ display: 'inline-flex', gap: 4, alignItems: 'center' }}>
                {col.keys.map((k) => (
                  <span
                    key={k}
                    className="mono"
                    style={{
                      fontSize: 8.5,
                      letterSpacing: '0.1em',
                      padding: '1px 5px',
                      borderRadius: 3,
                      color:
                        k === 'PK'
                          ? 'var(--paper)'
                          : k === 'FK'
                          ? 'var(--plum)'
                          : 'var(--forest)',
                      background:
                        k === 'PK'
                          ? 'var(--ink)'
                          : k === 'FK'
                          ? 'var(--plum-soft)'
                          : 'var(--forest-soft)',
                      fontWeight: 600,
                    }}
                  >
                    {k}
                  </span>
                ))}
                <span
                  className="mono uppercase"
                  style={{
                    fontSize: 9.5,
                    color: 'var(--text-4)',
                    letterSpacing: '0.08em',
                  }}
                >
                  {col.type}
                </span>
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function CardinalityMarker({
  x,
  y,
  label,
}: {
  x: number;
  y: number;
  label: string;
}) {
  const w = label.length * 6.5 + 10;
  const h = 15;
  return (
    <g>
      <rect
        x={x - w / 2}
        y={y - h / 2}
        width={w}
        height={h}
        rx={999}
        fill="var(--bg-elev)"
        stroke="var(--border-strong)"
      />
      <text
        x={x}
        y={y + 1}
        textAnchor="middle"
        dominantBaseline="middle"
        fontFamily="var(--font-mono)"
        fontSize={9.5}
        fill="var(--text-2)"
        style={{ letterSpacing: '0.04em' }}
      >
        {label}
      </text>
    </g>
  );
}

export default function ERChart({ data }: { data: ERData }) {
  const uid = useId().replace(/:/g, '');
  const { boxes, width, height } = useMemo(() => layout(data), [data]);
  const boxMap = useMemo(() => {
    const m = new Map<string, EntityBox>();
    for (const b of boxes) m.set(b.name, b);
    return m;
  }, [boxes]);

  const connectors = useMemo(() => {
    return data.relations
      .map((rel, i) => {
        const a = boxMap.get(rel.source);
        const b = boxMap.get(rel.target);
        if (!a || !b) return null;
        const { aSide, bSide } = pickSides(a, b);
        const p1 = sideAnchor(a, aSide);
        const p2 = sideAnchor(b, bSide);
        const d = bezierBetween(p1, p2, aSide, bSide);
        // Place cardinality labels just inside each end.
        const offset = 22;
        const nudge = (
          p: { x: number; y: number },
          side: Side,
        ): { x: number; y: number } => {
          switch (side) {
            case 'top':
              return { x: p.x, y: p.y - offset };
            case 'bottom':
              return { x: p.x, y: p.y + offset };
            case 'left':
              return { x: p.x - offset, y: p.y };
            case 'right':
              return { x: p.x + offset, y: p.y };
          }
        };
        return {
          rel,
          i,
          d,
          aPill: { ...nudge(p1, aSide), label: cardinalityLabel(rel.sourceCard) },
          bPill: { ...nudge(p2, bSide), label: cardinalityLabel(rel.targetCard) },
          midX: (p1.x + p2.x) / 2,
          midY: (p1.y + p2.y) / 2,
        };
      })
      .filter(Boolean) as {
      rel: ERRelation;
      i: number;
      d: string;
      aPill: { x: number; y: number; label: string };
      bPill: { x: number; y: number; label: string };
      midX: number;
      midY: number;
    }[];
  }, [data.relations, boxMap]);

  return (
    <div style={{ overflowX: 'auto', width: '100%', display: 'flex', justifyContent: 'center' }}>
      <div
        style={{ position: 'relative', width, height, flexShrink: 0 }}
        data-testid="er-canvas"
      >
        <svg
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width,
            height,
            pointerEvents: 'none',
            overflow: 'visible',
          }}
        >
          <defs>
            <style>{`
              @keyframes er-flow-${uid} {
                from { stroke-dashoffset: 18; }
                to   { stroke-dashoffset: 0; }
              }
            `}</style>
          </defs>
          {connectors.map(({ rel, i, d }) => (
            <path
              key={`path-${i}`}
              d={d}
              fill="none"
              stroke={rel.identifying ? 'var(--plum)' : 'var(--border-strong)'}
              strokeWidth={rel.identifying ? 1.7 : 1.5}
              opacity={0.75}
              strokeDasharray={rel.identifying ? undefined : '5 4'}
              style={
                rel.identifying
                  ? undefined
                  : { animation: `er-flow-${uid} 0.9s linear infinite` }
              }
            />
          ))}
        </svg>

        {boxes.map((box) => (
          <EntityCard key={box.name} box={box} />
        ))}

        <svg
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width,
            height,
            pointerEvents: 'none',
            overflow: 'visible',
          }}
        >
          {connectors.map(({ rel, i, aPill, bPill, midX, midY }) => (
            <g key={`lbl-${i}`}>
              <CardinalityMarker x={aPill.x} y={aPill.y} label={aPill.label} />
              <CardinalityMarker x={bPill.x} y={bPill.y} label={bPill.label} />
              {rel.label && (
                <g>
                  <rect
                    x={midX - (rel.label.length * 6.5 + 12) / 2}
                    y={midY - 9}
                    width={rel.label.length * 6.5 + 12}
                    height={18}
                    rx={4}
                    fill="var(--bg-elev)"
                    stroke="var(--border)"
                  />
                  <text
                    x={midX}
                    y={midY + 1}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontFamily="var(--font-mono)"
                    fontSize={10.5}
                    fill="var(--text-2)"
                  >
                    {rel.label}
                  </text>
                </g>
              )}
            </g>
          ))}
        </svg>
      </div>
    </div>
  );
}
