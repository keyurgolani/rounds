// Native flowchart renderer — replaces Mermaid for the Approach map.
// Lays nodes out in top-down layers using longest-path rank assignment,
// then draws type-accented cards (rectangle or diamond) with SVG bezier
// edges between them.

import { useId, useMemo, useState } from 'react';
import type { FlowchartData, FlowNode } from './parseFlowchart';

const NODE_W = 180;
const NODE_H = 58;
const NODE_H_DIAMOND = 76;
const H_GAP = 36;
const V_GAP = 58;
const PADDING = 36;

interface Positioned {
  id: string;
  x: number;
  y: number;
  w: number;
  h: number;
  rank: number;
  col: number;
  node: FlowNode;
}

function rankAssign(data: FlowchartData): Map<string, number> {
  // Topological longest-path — each node's rank = max(parent rank) + 1.
  const inbound = new Map<string, string[]>();
  const outbound = new Map<string, string[]>();
  for (const n of data.nodes) {
    inbound.set(n.id, []);
    outbound.set(n.id, []);
  }
  for (const e of data.edges) {
    inbound.get(e.target)?.push(e.source);
    outbound.get(e.source)?.push(e.target);
  }

  const rank = new Map<string, number>();
  const queue: string[] = [];
  for (const n of data.nodes) {
    if ((inbound.get(n.id) ?? []).length === 0) {
      rank.set(n.id, 0);
      queue.push(n.id);
    }
  }

  // If the graph has a cycle, some nodes never enter the queue — assign
  // them a rank via a second pass based on DFS depth.
  const visited = new Set<string>(queue);
  while (queue.length > 0) {
    const id = queue.shift()!;
    const myRank = rank.get(id) ?? 0;
    for (const next of outbound.get(id) ?? []) {
      const prev = rank.get(next);
      const candidate = myRank + 1;
      if (prev === undefined || candidate > prev) rank.set(next, candidate);
      if (!visited.has(next)) {
        visited.add(next);
        queue.push(next);
      }
    }
  }

  // Any orphaned nodes get rank 0.
  for (const n of data.nodes) {
    if (!rank.has(n.id)) rank.set(n.id, 0);
  }
  return rank;
}

function layout(data: FlowchartData): {
  positions: Positioned[];
  width: number;
  height: number;
} {
  const rank = rankAssign(data);
  const byRank = new Map<number, FlowNode[]>();
  for (const n of data.nodes) {
    const r = rank.get(n.id) ?? 0;
    if (!byRank.has(r)) byRank.set(r, []);
    byRank.get(r)!.push(n);
  }

  // Sort columns using barycenter of parent columns to reduce crossings.
  const col = new Map<string, number>();
  const sortedRanks = [...byRank.keys()].sort((a, b) => a - b);
  for (const r of sortedRanks) {
    const bucket = byRank.get(r)!;
    bucket.forEach((n, i) => col.set(n.id, i));
  }
  for (const r of sortedRanks) {
    const bucket = byRank.get(r)!;
    bucket.sort((a, b) => {
      const parA = data.edges
        .filter((e) => e.target === a.id)
        .map((e) => col.get(e.source) ?? 0);
      const parB = data.edges
        .filter((e) => e.target === b.id)
        .map((e) => col.get(e.source) ?? 0);
      const avg = (arr: number[]) =>
        arr.length ? arr.reduce((x, y) => x + y, 0) / arr.length : col.get(a.id) ?? 0;
      return avg(parA) - avg(parB);
    });
    bucket.forEach((n, i) => col.set(n.id, i));
  }

  const maxCols = Math.max(...[...byRank.values()].map((b) => b.length), 1);
  const width = maxCols * (NODE_W + H_GAP) - H_GAP + PADDING * 2;

  const positions: Positioned[] = [];
  sortedRanks.forEach((r, visualRank) => {
    const bucket = byRank.get(r)!;
    const rowW = bucket.length * NODE_W + (bucket.length - 1) * H_GAP;
    const startX = (width - rowW) / 2;
    bucket.forEach((node, colIdx) => {
      const h = node.shape === 'diamond' ? NODE_H_DIAMOND : NODE_H;
      positions.push({
        id: node.id,
        x: startX + colIdx * (NODE_W + H_GAP),
        y: PADDING + visualRank * (NODE_H_DIAMOND + V_GAP),
        w: NODE_W,
        h,
        rank: visualRank,
        col: colIdx,
        node,
      });
    });
  });

  const height = sortedRanks.length * (NODE_H_DIAMOND + V_GAP) - V_GAP + PADDING * 2;
  return { positions, width, height };
}

function edgePath(src: Positioned, tgt: Positioned): {
  d: string;
  mx: number;
  my: number;
  arrow: string;
} {
  const sx = src.x + src.w / 2;
  const sy = src.y + src.h;
  const tx = tgt.x + tgt.w / 2;
  const ty = tgt.y;

  if (src.rank === tgt.rank) {
    // Same rank — arc above.
    const midY = Math.min(src.y, tgt.y) - V_GAP * 0.6;
    const sxSide = src.x < tgt.x ? src.x + src.w : src.x;
    const txSide = src.x < tgt.x ? tgt.x : tgt.x + tgt.w;
    const sxY = src.y + src.h / 2;
    const txY = tgt.y + tgt.h / 2;
    const d = `M ${sxSide},${sxY} C ${sxSide},${midY} ${txSide},${midY} ${txSide},${txY}`;
    const arrow = arrowPolyPoint(txSide, txY, src.x < tgt.x ? 'left' : 'right');
    return { d, mx: (sxSide + txSide) / 2, my: midY, arrow };
  }

  if (src.rank > tgt.rank) {
    // Upward — rare, mirror.
    const sxUp = src.x + src.w / 2;
    const syUp = src.y;
    const txUp = tgt.x + tgt.w / 2;
    const tyUp = tgt.y + tgt.h;
    const midY = syUp + (tyUp - syUp) / 2;
    const d = `M ${sxUp},${syUp} C ${sxUp},${midY} ${txUp},${midY} ${txUp},${tyUp}`;
    const arrow = arrowPolyPoint(txUp, tyUp, 'up');
    return { d, mx: (sxUp + txUp) / 2, my: midY, arrow };
  }

  // Downward — standard case.
  const midY = sy + (ty - sy) / 2;
  const d = `M ${sx},${sy} C ${sx},${midY} ${tx},${midY} ${tx},${ty}`;
  const arrow = arrowPolyPoint(tx, ty, 'down');
  return { d, mx: (sx + tx) / 2, my: midY, arrow };
}

function arrowPolyPoint(cx: number, cy: number, dir: 'up' | 'down' | 'left' | 'right'): string {
  const s = 5;
  switch (dir) {
    case 'down':
      return `${cx},${cy} ${cx - s},${cy - s * 1.6} ${cx + s},${cy - s * 1.6}`;
    case 'up':
      return `${cx},${cy} ${cx - s},${cy + s * 1.6} ${cx + s},${cy + s * 1.6}`;
    case 'left':
      return `${cx},${cy} ${cx + s * 1.6},${cy - s} ${cx + s * 1.6},${cy + s}`;
    case 'right':
      return `${cx},${cy} ${cx - s * 1.6},${cy - s} ${cx - s * 1.6},${cy + s}`;
  }
}

function NodeCard({ pos }: { pos: Positioned }) {
  const [hover, setHover] = useState(false);
  const { node } = pos;
  const isDiamond = node.shape === 'diamond';
  const accent = isDiamond ? 'var(--ochre)' : 'var(--accent)';

  // Diamond rendered as a rotated square with an upright inner label.
  const common: React.CSSProperties = {
    position: 'absolute',
    left: pos.x,
    top: pos.y,
    width: pos.w,
    height: pos.h,
    boxSizing: 'border-box',
    cursor: 'default',
    transition: 'box-shadow 0.15s ease, transform 0.15s ease',
    transform: hover ? 'translateY(-1px)' : undefined,
  };

  if (isDiamond) {
    const pad = 12;
    return (
      <div
        style={common}
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
      >
        <svg
          width={pos.w}
          height={pos.h}
          viewBox={`0 0 ${pos.w} ${pos.h}`}
          style={{ position: 'absolute', top: 0, left: 0, overflow: 'visible' }}
        >
          <polygon
            points={`${pos.w / 2},2 ${pos.w - 2},${pos.h / 2} ${pos.w / 2},${pos.h - 2} 2,${pos.h / 2}`}
            fill="var(--bg-elev)"
            stroke={accent}
            strokeWidth={1.5}
            filter={hover ? 'drop-shadow(0 8px 18px rgba(24, 22, 19, 0.12))' : undefined}
          />
        </svg>
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: `${pad}px ${pad + 8}px`,
            textAlign: 'center',
          }}
        >
          <span
            style={{
              fontFamily: 'var(--font-sans)',
              fontSize: 12.5,
              fontWeight: 500,
              color: 'var(--text)',
              lineHeight: 1.25,
              maxWidth: '100%',
            }}
          >
            {node.label}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        ...common,
        padding: '12px 14px',
        background: 'var(--bg-elev)',
        boxShadow: hover ? 'var(--shadow-card-hover)' : 'var(--shadow-card)',
        borderRadius: 'var(--radius)',
        border: '1px solid var(--border-strong)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        gap: 4,
      }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <span
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 9.5,
          letterSpacing: '0.14em',
          textTransform: 'uppercase',
          color: accent,
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
            background: accent,
            display: 'inline-block',
            flexShrink: 0,
          }}
        />
        Step
      </span>
      <span
        style={{
          fontFamily: 'var(--font-sans)',
          fontSize: 13,
          fontWeight: 500,
          color: 'var(--text)',
          lineHeight: 1.3,
        }}
      >
        {node.label}
      </span>
    </div>
  );
}

export default function FlowchartChart({ data }: { data: FlowchartData }) {
  const uid = useId().replace(/:/g, '');
  const { positions, width, height } = useMemo(() => layout(data), [data]);
  const posMap = useMemo(() => {
    const m = new Map<string, Positioned>();
    for (const p of positions) m.set(p.id, p);
    return m;
  }, [positions]);

  const geom = useMemo(
    () =>
      data.edges
        .map((e, i) => {
          const s = posMap.get(e.source);
          const t = posMap.get(e.target);
          if (!s || !t) return null;
          return { e, i, ...edgePath(s, t) };
        })
        .filter(Boolean) as {
        e: FlowchartData['edges'][number];
        i: number;
        d: string;
        mx: number;
        my: number;
        arrow: string;
      }[],
    [data.edges, posMap],
  );

  return (
    <div style={{ overflowX: 'auto', width: '100%', display: 'flex', justifyContent: 'center' }}>
      <div
        style={{ position: 'relative', width, height, flexShrink: 0 }}
        data-testid="flowchart-canvas"
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
              @keyframes flow-path-${uid} {
                from { stroke-dashoffset: 18; }
                to   { stroke-dashoffset: 0; }
              }
            `}</style>
          </defs>
          {geom.map(({ e, i, d, arrow }) => (
            <g key={`e-${i}`}>
              <path
                d={d}
                fill="none"
                stroke="var(--border-strong)"
                strokeWidth={1.5}
                opacity={0.75}
                strokeDasharray={e.dashed ? '5 4' : undefined}
                style={
                  e.dashed
                    ? { animation: `flow-path-${uid} 0.7s linear infinite` }
                    : undefined
                }
              />
              <polygon points={arrow} fill="var(--border-strong)" opacity={0.85} />
            </g>
          ))}
        </svg>

        {positions.map((pos) => (
          <NodeCard key={pos.id} pos={pos} />
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
          {geom.map(({ e, i, mx, my }) => {
            if (!e.label) return null;
            const labelW = e.label.length * 6.6 + 10;
            const labelH = 18;
            return (
              <g key={`l-${i}`}>
                <rect
                  x={mx - labelW / 2}
                  y={my - labelH / 2}
                  width={labelW}
                  height={labelH}
                  rx={4}
                  fill="var(--bg-elev)"
                  stroke="var(--border)"
                />
                <text
                  x={mx}
                  y={my + 1}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill="var(--text-2)"
                  fontFamily="var(--font-mono)"
                  fontSize={10.5}
                >
                  {e.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}

