// Native sequence diagram renderer — replaces Mermaid for `sequenceDiagram`.
// Participants become column headers with dashed lifelines descending below;
// each message is a labeled arrow between lifelines at its vertical step.
// Self-loops and alt/else/end blocks are supported as boxed regions.

import { useId, useMemo, useState } from 'react';
import type { SeqData, SeqParticipant, SeqStepKind } from './parseSequence';

const COL_W = 160;
const HEADER_H = 56;
const STEP_H = 58;
const PAD_X = 28;
const PAD_TOP = 24;
const PAD_BOTTOM = 40;

// A palette cycled across participants so each lane reads as distinct.
const LANE_COLORS = [
  'var(--accent)',
  'var(--forest)',
  'var(--ochre)',
  'var(--plum)',
  'var(--ink)',
];

interface Layout {
  width: number;
  height: number;
  lifelineTop: number;
  lifelineBottom: number;
  colOfParticipant: Map<string, number>;
  stepYs: number[]; // y-center for each step index (-1 for non-message steps)
  blocks: { open: number; close: number; label: string; kind: string; depth: number }[];
}

function computeLayout(data: SeqData): Layout {
  const colOfParticipant = new Map<string, number>();
  data.participants.forEach((p, i) => colOfParticipant.set(p.id, i));

  const stepYs: number[] = [];
  let y = PAD_TOP + HEADER_H + 16;
  for (const step of data.steps) {
    if (step.type === 'msg' || step.type === 'note') {
      stepYs.push(y + STEP_H / 2);
      y += STEP_H;
    } else {
      // block markers get their own thin row for visual separation
      stepYs.push(y);
      y += 26;
    }
  }

  // Walk blocks to determine open/close pairs and nesting depth.
  const blocks: Layout['blocks'] = [];
  const stack: { open: number; label: string; kind: string; depth: number }[] = [];
  for (let i = 0; i < data.steps.length; i++) {
    const s = data.steps[i];
    if (s.type === 'block-open') {
      stack.push({ open: i, label: s.label, kind: s.kind, depth: stack.length });
    } else if (s.type === 'block-close') {
      const open = stack.pop();
      if (open) blocks.push({ ...open, close: i });
    } else if (s.type === 'block-else') {
      // treat else as a visual continuation — no change to block nesting.
    }
  }

  const width = data.participants.length * COL_W + PAD_X * 2;
  const height = y + PAD_BOTTOM;
  return {
    width,
    height,
    lifelineTop: PAD_TOP + HEADER_H,
    lifelineBottom: height - PAD_BOTTOM + 8,
    colOfParticipant,
    stepYs,
    blocks,
  };
}

function colorFor(idx: number): string {
  return LANE_COLORS[idx % LANE_COLORS.length];
}

function colX(col: number): number {
  return PAD_X + col * COL_W + COL_W / 2;
}

function ParticipantHeader({
  p,
  idx,
}: {
  p: SeqParticipant;
  idx: number;
}) {
  const [hover, setHover] = useState(false);
  const accent = colorFor(idx);
  return (
    <div
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        position: 'absolute',
        left: colX(idx) - 66,
        top: PAD_TOP,
        width: 132,
        height: HEADER_H - 8,
        background: 'var(--bg-elev)',
        border: `1px solid var(--border-strong)`,
        borderRadius: 'var(--radius)',
        boxShadow: hover ? 'var(--shadow-card-hover)' : 'var(--shadow-card)',
        padding: '8px 10px',
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
        justifyContent: 'center',
        textAlign: 'center',
        transition: 'box-shadow 0.15s ease, transform 0.15s ease',
        transform: hover ? 'translateY(-1px)' : undefined,
      }}
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
          justifyContent: 'center',
        }}
      >
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: 999,
            background: accent,
            display: 'inline-block',
          }}
        />
        {p.id}
      </span>
      <span
        style={{
          fontFamily: 'var(--font-sans)',
          fontSize: 12,
          fontWeight: 500,
          color: 'var(--text)',
          lineHeight: 1.2,
        }}
      >
        {p.label}
      </span>
    </div>
  );
}

interface MsgRenderProps {
  step: Extract<SeqStepKind, { type: 'msg' }>;
  y: number;
  colFrom: number;
  colTo: number;
}

function MessageLine({ step, y, colFrom, colTo }: MsgRenderProps) {
  const selfLoop = colFrom === colTo;
  const x1 = colX(colFrom);
  const x2 = colX(colTo);
  const stroke = step.dashed ? 'var(--text-3)' : 'var(--ink)';
  const strokeW = step.dashed ? 1.3 : 1.5;
  const dash = step.dashed ? '5 4' : undefined;

  if (selfLoop) {
    const loopW = 44;
    const top = y - 18;
    const bot = y + 18;
    const d = `M ${x1},${top} h ${loopW} v ${bot - top} h -${loopW}`;
    return (
      <g>
        <path
          d={d}
          fill="none"
          stroke={stroke}
          strokeWidth={strokeW}
          strokeDasharray={dash}
        />
        <polygon
          points={`${x1},${bot} ${x1 + 6},${bot - 5} ${x1 + 6},${bot + 5}`}
          fill={stroke}
        />
        <foreignObject x={x1 + 8} y={top - 6} width={loopW + 60} height={22}>
          <div
            style={{
              fontFamily: 'var(--font-sans)',
              fontSize: 11.5,
              color: 'var(--text-2)',
              lineHeight: 1.4,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {step.label}
          </div>
        </foreignObject>
      </g>
    );
  }

  const dir = x2 > x1 ? 1 : -1;
  const arrowX = x2 - dir * 3;
  const head = `${x2},${y} ${arrowX - dir * 6},${y - 5} ${arrowX - dir * 6},${y + 5}`;
  const midX = (x1 + x2) / 2;

  return (
    <g>
      <line
        x1={x1 + dir * 3}
        y1={y}
        x2={x2 - dir * 3}
        y2={y}
        stroke={stroke}
        strokeWidth={strokeW}
        strokeDasharray={dash}
      />
      <polygon points={head} fill={stroke} />
      <foreignObject x={midX - 90} y={y - 24} width={180} height={22}>
        <div
          style={{
            fontFamily: 'var(--font-sans)',
            fontSize: 11.5,
            color: 'var(--text-2)',
            textAlign: 'center',
            lineHeight: 1.4,
            background: 'var(--bg-elev)',
            borderRadius: 4,
            padding: '1px 6px',
            display: 'inline-block',
            maxWidth: '100%',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          {step.label}
        </div>
      </foreignObject>
    </g>
  );
}

function NoteBox({
  step,
  y,
  layout,
}: {
  step: Extract<SeqStepKind, { type: 'note' }>;
  y: number;
  layout: Layout;
}) {
  const cols = step.over
    .map((id) => layout.colOfParticipant.get(id))
    .filter((v): v is number => v !== undefined);
  if (cols.length === 0) return null;
  const minCol = Math.min(...cols);
  const maxCol = Math.max(...cols);
  const x1 = colX(minCol) - 56;
  const x2 = colX(maxCol) + 56;
  const w = x2 - x1;
  return (
    <g>
      <rect
        x={x1}
        y={y - 14}
        width={w}
        height={28}
        rx={4}
        fill="var(--ochre-soft)"
        stroke="var(--ochre)"
        strokeWidth={1}
        opacity={0.9}
      />
      <text
        x={(x1 + x2) / 2}
        y={y + 1}
        textAnchor="middle"
        dominantBaseline="middle"
        fontFamily="var(--font-sans)"
        fontSize={11.5}
        fill="var(--text)"
      >
        {step.text}
      </text>
    </g>
  );
}

export default function SequenceChart({ data }: { data: SeqData }) {
  const uid = useId().replace(/:/g, '');
  const layout = useMemo(() => computeLayout(data), [data]);

  // Group messages per step that share a block — we color the block region.
  const blockShades = useMemo(() => {
    return layout.blocks.map((b, i) => {
      const yTop = layout.stepYs[b.open] + 10;
      const yBot = (layout.stepYs[b.close] ?? yTop + 40) - 2;
      const tone =
        b.kind === 'alt'
          ? 'var(--plum-soft)'
          : b.kind === 'opt'
          ? 'var(--ochre-soft)'
          : b.kind === 'loop'
          ? 'var(--forest-soft)'
          : 'var(--accent-soft)';
      const stroke =
        b.kind === 'alt'
          ? 'var(--plum)'
          : b.kind === 'opt'
          ? 'var(--ochre)'
          : b.kind === 'loop'
          ? 'var(--forest)'
          : 'var(--accent)';
      return {
        key: `block-${i}`,
        yTop,
        yBot,
        label: `${b.kind.toUpperCase()} ${b.label}`.trim(),
        tone,
        stroke,
        depth: b.depth,
      };
    });
  }, [layout]);

  return (
    <div style={{ overflowX: 'auto', width: '100%', display: 'flex', justifyContent: 'center' }}>
      <div
        style={{
          position: 'relative',
          width: layout.width,
          height: layout.height,
          flexShrink: 0,
        }}
        data-testid="sequence-canvas"
      >
        <svg
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: layout.width,
            height: layout.height,
            pointerEvents: 'none',
            overflow: 'visible',
          }}
        >
          <defs>
            <style>{`
              @keyframes seq-pulse-${uid} {
                0%, 100% { opacity: 0.25; }
                50%      { opacity: 0.65; }
              }
            `}</style>
          </defs>

          {blockShades.map((b) => (
            <g key={b.key}>
              <rect
                x={PAD_X - 12 + b.depth * 8}
                y={b.yTop}
                width={layout.width - PAD_X * 2 + 24 - b.depth * 16}
                height={Math.max(b.yBot - b.yTop, 20)}
                rx={6}
                fill={b.tone}
                opacity={0.35}
                stroke={b.stroke}
                strokeWidth={1}
                strokeDasharray="4 3"
              />
              <text
                x={PAD_X - 4 + b.depth * 8}
                y={b.yTop + 12}
                fontFamily="var(--font-mono)"
                fontSize={9.5}
                letterSpacing="0.14em"
                fill={b.stroke}
                style={{ textTransform: 'uppercase' }}
              >
                {b.label}
              </text>
            </g>
          ))}

          {data.participants.map((p, i) => (
            <line
              key={`ll-${p.id}`}
              x1={colX(i)}
              y1={layout.lifelineTop}
              x2={colX(i)}
              y2={layout.lifelineBottom}
              stroke={colorFor(i)}
              strokeOpacity={0.4}
              strokeWidth={1.2}
              strokeDasharray="3 4"
              style={{ animation: `seq-pulse-${uid} 3s ease-in-out infinite` }}
            />
          ))}

          {data.steps.map((step, i) => {
            const y = layout.stepYs[i];
            if (step.type === 'msg') {
              const cFrom = layout.colOfParticipant.get(step.from);
              const cTo = layout.colOfParticipant.get(step.to);
              if (cFrom === undefined || cTo === undefined) return null;
              return (
                <MessageLine
                  key={`s-${i}`}
                  step={step}
                  y={y}
                  colFrom={cFrom}
                  colTo={cTo}
                />
              );
            }
            if (step.type === 'note') {
              return <NoteBox key={`s-${i}`} step={step} y={y} layout={layout} />;
            }
            return null;
          })}
        </svg>

        {data.participants.map((p, i) => (
          <ParticipantHeader key={p.id} p={p} idx={i} />
        ))}
      </div>
    </div>
  );
}
