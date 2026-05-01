// Native DOM/SVG architecture diagram renderer — replaces ReactFlow.
// Lays nodes out in vertical rows grouped by type (top-to-bottom flow),
// connects them with SVG cubic-bezier paths.

import { useMemo, useState, useId } from 'react';
import type { ArchitectureDiagramData, ArchitectureNode } from '../types';

type NodeType = 'client' | 'server' | 'cache' | 'database' | 'queue' | 'lb' | 'service';

const TYPE_ACCENT: Record<NodeType, { stroke: string; dot: string; label: string }> = {
  client:   { stroke: 'var(--accent)',  dot: 'var(--accent)',  label: 'Client' },
  server:   { stroke: 'var(--ink)',     dot: 'var(--ink)',     label: 'Server' },
  cache:    { stroke: 'var(--ochre)',   dot: 'var(--ochre)',   label: 'Cache' },
  database: { stroke: 'var(--plum)',    dot: 'var(--plum)',    label: 'Database' },
  queue:    { stroke: 'var(--plum)',    dot: 'var(--plum)',    label: 'Queue' },
  lb:       { stroke: 'var(--accent)', dot: 'var(--accent)',  label: 'Load balancer' },
  service:  { stroke: 'var(--forest)', dot: 'var(--forest)',  label: 'Service' },
};

// Row ordering — index within this array is the visual row index (0 = top).
const ROW_ORDER: NodeType[][] = [
  ['client'],
  ['lb'],
  ['server', 'service'],
  ['cache'],
  ['database', 'queue'],
];

const NODE_W = 170;
const NODE_H = 70;
const H_GAP = 32;
const V_GAP = 56;
const PADDING = 40;

interface NodePosition {
  id: string;
  x: number;
  y: number;
  row: number;
  node: ArchitectureNode;
}

type EdgeDef = { source: string; target: string; id?: string; label?: string; animated?: boolean };

function computeLayout(
  nodes: ArchitectureNode[],
  edges: EdgeDef[],
): {
  positions: NodePosition[];
  containerW: number;
  containerH: number;
} {
  // Bucket nodes by row.
  const buckets: ArchitectureNode[][] = ROW_ORDER.map(() => []);
  const unassigned: ArchitectureNode[] = [];

  for (const node of nodes) {
    const type = (node.type ?? 'service') as NodeType;
    const rowIdx = ROW_ORDER.findIndex((types) => types.includes(type));
    if (rowIdx === -1) {
      unassigned.push(node);
    } else {
      buckets[rowIdx].push(node);
    }
  }

  // Unassigned nodes go into the 'server/service' row.
  buckets[2].push(...unassigned);

  // Collapse empty rows.
  const activeRows = buckets
    .map((bucket, rowIdx) => ({ bucket, rowIdx }))
    .filter(({ bucket }) => bucket.length > 0);

  // Column ordering: sort each row by pull score to reduce same-row crossings.
  // First pass: provisional columns (index in its bucket).
  const colOf = new Map<string, number>();
  activeRows.forEach(({ bucket }) => {
    bucket.forEach((n, i) => colOf.set(n.id, i));
  });

  // Second pass: for each node, score = average column of its edge partners.
  activeRows.forEach(({ bucket }) => {
    const score = new Map<string, number>();
    for (const node of bucket) {
      const partners: number[] = [];
      for (const e of edges) {
        if (e.source === node.id && colOf.has(e.target)) partners.push(colOf.get(e.target)!);
        if (e.target === node.id && colOf.has(e.source)) partners.push(colOf.get(e.source)!);
      }
      score.set(
        node.id,
        partners.length > 0
          ? partners.reduce((a, b) => a + b, 0) / partners.length
          : colOf.get(node.id)!,
      );
    }
    bucket.sort((a, b) => score.get(a.id)! - score.get(b.id)!);
  });

  const maxCols = Math.max(...activeRows.map(({ bucket }) => bucket.length), 1);
  const containerW = maxCols * (NODE_W + H_GAP) - H_GAP + PADDING * 2;
  const containerH = activeRows.length * (NODE_H + V_GAP) - V_GAP + PADDING * 2;

  const positions: NodePosition[] = [];

  activeRows.forEach(({ bucket, rowIdx }, visualRow) => {
    const rowWidth = bucket.length * NODE_W + (bucket.length - 1) * H_GAP;
    const startX = (containerW - rowWidth) / 2;
    bucket.forEach((node, colIdx) => {
      positions.push({
        id: node.id,
        x: startX + colIdx * (NODE_W + H_GAP),
        y: PADDING + visualRow * (NODE_H + V_GAP),
        row: rowIdx,
        node,
      });
    });
  });

  return { positions, containerW, containerH };
}

// Derive a bezier path between two node positions.
// Connects bottom-center of source → top-center of target (top-to-bottom flow).
// For same-row: side routing when adjacent; arc above row when non-adjacent.
// For reverse flow (source below target): top-of-source → bottom-of-target.
function edgePath(
  src: NodePosition,
  tgt: NodePosition,
  posMap: Map<string, NodePosition>,
): { d: string; mx: number; my: number; sameRowAbove: boolean } {
  const srcCx = src.x + NODE_W / 2;
  const tgtCx = tgt.x + NODE_W / 2;

  if (src.row === tgt.row) {
    // Determine if any node sits between src and tgt in the same row.
    const srcLeft = Math.min(src.x, tgt.x);
    const srcRight = Math.max(src.x + NODE_W, tgt.x + NODE_W);
    let hasMidNode = false;
    for (const pos of posMap.values()) {
      if (pos.id === src.id || pos.id === tgt.id) continue;
      if (pos.row !== src.row) continue;
      const posCx = pos.x + NODE_W / 2;
      if (posCx > srcLeft + NODE_W / 2 && posCx < srcRight - NODE_W / 2) {
        hasMidNode = true;
        break;
      }
    }

    if (hasMidNode) {
      // Arc above the row.
      const sx = srcCx;
      const sy = src.y;
      const tx = tgtCx;
      const ty = tgt.y;
      const midY = sy - V_GAP * 0.8;
      const d = `M ${sx},${sy} C ${sx},${midY} ${tx},${midY} ${tx},${ty}`;
      return { d, mx: (sx + tx) / 2, my: midY, sameRowAbove: true };
    }

    // Adjacent same-row — route left/right sides.
    const srcRight2 = src.x > tgt.x;
    const sx = srcRight2 ? src.x : src.x + NODE_W;
    const sy = src.y + NODE_H / 2;
    const tx = srcRight2 ? tgt.x + NODE_W : tgt.x;
    const ty = tgt.y + NODE_H / 2;
    const midX = (sx + tx) / 2;
    const d = `M ${sx},${sy} C ${midX},${sy} ${midX},${ty} ${tx},${ty}`;
    return { d, mx: midX, my: (sy + ty) / 2, sameRowAbove: false };
  }

  if (src.row <= tgt.row) {
    // Downward: bottom of source → top of target.
    const sx = srcCx;
    const sy = src.y + NODE_H;
    const tx = tgtCx;
    const ty = tgt.y;
    const midY = sy + (ty - sy) / 2;
    const d = `M ${sx},${sy} C ${sx},${midY} ${tx},${midY} ${tx},${ty}`;
    return { d, mx: (sx + tx) / 2, my: midY, sameRowAbove: false };
  }

  // Upward / reverse: top of source → bottom of target.
  const sx = srcCx;
  const sy = src.y;
  const tx = tgtCx;
  const ty = tgt.y + NODE_H;
  const midY = sy - (sy - ty) / 2;
  const d = `M ${sx},${sy} C ${sx},${midY} ${tx},${midY} ${tx},${ty}`;
  return { d, mx: (sx + tx) / 2, my: midY, sameRowAbove: false };
}

// Arrow polygon pointing down (for downward edges) or up (for upward).
function arrowPolygon(tgt: NodePosition, isDownward: boolean): string {
  const cx = tgt.x + NODE_W / 2;
  const tipY = isDownward ? tgt.y : tgt.y + NODE_H;
  const dir = isDownward ? 1 : -1;
  const size = 5;
  const p1 = `${cx},${tipY}`;
  const p2 = `${cx - size},${tipY - dir * size * 1.6}`;
  const p3 = `${cx + size},${tipY - dir * size * 1.6}`;
  return `${p1} ${p2} ${p3}`;
}

// For same-row edges, arrow points right or left.
function arrowPolygonHorizontal(tgt: NodePosition, pointRight: boolean): string {
  const cy = tgt.y + NODE_H / 2;
  const tipX = pointRight ? tgt.x : tgt.x + NODE_W;
  const dir = pointRight ? 1 : -1;
  const size = 5;
  const p1 = `${tipX},${cy}`;
  const p2 = `${tipX - dir * size * 1.6},${cy - size}`;
  const p3 = `${tipX - dir * size * 1.6},${cy + size}`;
  return `${p1} ${p2} ${p3}`;
}

interface NodeCardProps {
  pos: NodePosition;
  orphan?: boolean;
}

function NodeCard({ pos, orphan }: NodeCardProps) {
  const [hovered, setHovered] = useState(false);
  const { node } = pos;
  const type = (node.type ?? 'service') as NodeType;
  const accent = TYPE_ACCENT[type] ?? TYPE_ACCENT.service;

  return (
    <div
      style={{
        position: 'absolute',
        left: pos.x,
        top: pos.y,
        width: NODE_W,
        minHeight: NODE_H,
        padding: '10px 12px',
        background: 'var(--bg-elev)',
        boxShadow: hovered ? 'var(--shadow-card-hover)' : 'var(--shadow-card)',
        borderRadius: 'var(--radius)',
        border: orphan ? '1px dashed var(--border-strong)' : '1px solid var(--border-strong)',
        opacity: orphan ? 0.75 : undefined,
        boxSizing: 'border-box',
        cursor: 'default',
        transition: 'box-shadow 0.15s ease',
        display: 'flex',
        flexDirection: 'column',
        gap: 5,
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <span
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 9.5,
          letterSpacing: '0.14em',
          textTransform: 'uppercase',
          color: accent.stroke,
          display: 'inline-flex',
          alignItems: 'center',
          gap: 5,
        }}
      >
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: 999,
            background: accent.dot,
            display: 'inline-block',
            flexShrink: 0,
          }}
        />
        {accent.label}
      </span>
      <span
        style={{
          fontFamily: 'var(--font-sans)',
          fontSize: 13,
          fontWeight: 500,
          color: 'var(--text)',
          lineHeight: 1.25,
        }}
      >
        {node.label}
      </span>
      {node.description && (
        <span
          style={{
            fontFamily: 'var(--font-sans)',
            fontSize: 11,
            color: 'var(--text-3)',
            lineHeight: 1.4,
          }}
        >
          {node.description}
        </span>
      )}
    </div>
  );
}

export default function ArchitectureChart({
  data,
}: {
  data: ArchitectureDiagramData;
}) {
  const uid = useId().replace(/:/g, '');
  const { positions, containerW, containerH } = useMemo(
    () => computeLayout(data.nodes, data.edges),
    [data.nodes, data.edges],
  );

  const posMap = useMemo(() => {
    const m = new Map<string, NodePosition>();
    for (const p of positions) m.set(p.id, p);
    return m;
  }, [positions]);

  // Compute which node ids appear in at least one edge.
  const connectedIds = useMemo(() => {
    const s = new Set<string>();
    for (const e of data.edges) {
      s.add(e.source);
      s.add(e.target);
    }
    return s;
  }, [data.edges]);

  // Pre-compute edge geometry once so both SVG layers stay aligned.
  const edgeGeometry = useMemo(() => {
    return data.edges.map((edge, i) => {
      const src = posMap.get(edge.source);
      const tgt = posMap.get(edge.target);
      if (!src || !tgt) return null;

      const { d, mx, my, sameRowAbove } = edgePath(src, tgt, posMap);
      const isDownward = src.row < tgt.row;
      const isSameRow = src.row === tgt.row;
      const isReverse = src.row > tgt.row;
      const edgeKey = edge.id ?? `e-${i}`;

      const arrowPts = sameRowAbove
        ? arrowPolygon(tgt, true)
        : isSameRow
        ? arrowPolygonHorizontal(tgt, src.x < tgt.x)
        : arrowPolygon(tgt, isDownward || (!isReverse && !isSameRow));

      return { edge, edgeKey, src, tgt, d, mx, my, arrowPts };
    });
  }, [data.edges, posMap]);

  return (
    <div
      style={{
        overflowX: 'auto',
        width: '100%',
        display: 'flex',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          position: 'relative',
          width: containerW,
          height: containerH,
          background: 'transparent',
          flexShrink: 0,
        }}
      >
        {/* Layer 1: SVG for edge paths + arrowheads only — sits below node cards */}
        <svg
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: containerW,
            height: containerH,
            pointerEvents: 'none',
            overflow: 'visible',
          }}
        >
          <defs>
            <style>{`
              @keyframes arch-flow-${uid} {
                from { stroke-dashoffset: 20; }
                to   { stroke-dashoffset: 0; }
              }
            `}</style>
          </defs>
          {edgeGeometry.map((geo) => {
            if (!geo) return null;
            const { edge, edgeKey, arrowPts, d } = geo;
            return (
              <g key={edgeKey}>
                <path
                  d={d}
                  fill="none"
                  stroke="var(--border-strong)"
                  strokeWidth={1.5}
                  opacity={0.7}
                  strokeDasharray={edge.animated ? '6 4' : undefined}
                  style={
                    edge.animated
                      ? {
                          animation: `arch-flow-${uid} 0.6s linear infinite`,
                        }
                      : undefined
                  }
                />
                <polygon
                  points={arrowPts}
                  fill="var(--border-strong)"
                  opacity={0.8}
                />
              </g>
            );
          })}
        </svg>

        {/* Node cards — middle layer */}
        {positions.map((pos) => (
          <NodeCard key={pos.id} pos={pos} orphan={!connectedIds.has(pos.id)} />
        ))}

        {/* Layer 2: SVG for edge labels only — sits above node cards */}
        <svg
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: containerW,
            height: containerH,
            pointerEvents: 'none',
            overflow: 'visible',
          }}
        >
          {edgeGeometry.map((geo) => {
            if (!geo) return null;
            const { edge, edgeKey, mx, my } = geo;
            if (!edge.label) return null;
            const labelW = edge.label.length * 6.5 + 6;
            const labelH = 16;
            return (
              <g key={`${edgeKey}-label`}>
                <rect
                  x={mx - labelW / 2}
                  y={my - labelH / 2}
                  width={labelW}
                  height={labelH}
                  rx={3}
                  fill="var(--bg-elev)"
                />
                <text
                  x={mx}
                  y={my + 1}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill="var(--text-3)"
                  fontFamily="var(--font-mono)"
                  fontSize={10}
                >
                  {edge.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
