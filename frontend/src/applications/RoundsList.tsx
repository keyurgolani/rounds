/**
 * Shared rendering primitives for an application's rounds. Used by
 * ApplicationDetail's main "Rounds & loops" card and by Applications'
 * per-row inline drawer.
 *
 * Each round renders as a `RoundCard` — a collapsed summary that
 * expands inline to the full editor (no separate /interviews/:id
 * page). Loop_label clusters rounds under a header with an N-rounds
 * counter; one-off rounds fall to the bottom.
 */
import RoundCard from './RoundCard';
import type { InterviewRound } from './api';

export type RoundsGroup = { label: string; rounds: InterviewRound[] };

export function groupRoundsByLoop(rounds: InterviewRound[]): RoundsGroup[] {
  const map = new Map<string, InterviewRound[]>();
  for (const r of rounds) {
    const key = r.loop_label ?? '';
    const bucket = map.get(key);
    if (bucket) bucket.push(r);
    else map.set(key, [r]);
  }
  const groups = Array.from(map.entries()).map(([label, rs]) => ({
    label,
    rounds: rs.slice().sort(byDateAsc),
  }));
  groups.sort((a, b) => {
    if (!a.label && b.label) return 1;
    if (a.label && !b.label) return -1;
    const aDate = a.rounds[0]?.date ?? '';
    const bDate = b.rounds[0]?.date ?? '';
    return aDate.localeCompare(bDate);
  });
  return groups;
}

function byDateAsc(a: InterviewRound, b: InterviewRound): number {
  return (a.date || '').localeCompare(b.date || '');
}

type Props = {
  rounds: InterviewRound[];
  /** Round was edited inline — caller replaces the entry in its
   *  source-of-truth list with `next`. */
  onUpdated: (next: InterviewRound) => void;
  /** Round was deleted from inside the expanded card. */
  onDeleted: (id: string) => void;
};

export default function RoundsList({ rounds, onUpdated, onDeleted }: Props) {
  const groups = groupRoundsByLoop(rounds);
  if (groups.length === 0) return null;
  return (
    <div className="flex flex-col gap-3">
      {groups.map((group) =>
        group.label ? (
          <LoopGroup
            key={`loop:${group.label}`}
            label={group.label}
            rounds={group.rounds}
            onUpdated={onUpdated}
            onDeleted={onDeleted}
          />
        ) : (
          <div key="loop:_singles" className="flex flex-col gap-2">
            {group.rounds.map((r) => (
              <RoundCard
                key={r.id}
                round={r}
                onUpdated={onUpdated}
                onDeleted={onDeleted}
              />
            ))}
          </div>
        ),
      )}
    </div>
  );
}

function LoopGroup({
  label,
  rounds,
  onUpdated,
  onDeleted,
}: {
  label: string;
  rounds: InterviewRound[];
  onUpdated: (next: InterviewRound) => void;
  onDeleted: (id: string) => void;
}) {
  return (
    <div
      style={{
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        background: 'var(--bg)',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          padding: '8px 12px',
          background: 'var(--bg-elev)',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'baseline',
          gap: 8,
        }}
      >
        <span
          className="eyebrow"
          style={{ color: 'var(--text-3)', letterSpacing: '0.1em' }}
        >
          Loop
        </span>
        <span style={{ fontSize: 13, fontWeight: 600 }}>{label}</span>
        <span
          className="mono"
          style={{
            marginLeft: 'auto',
            fontSize: 10.5,
            color: 'var(--text-4)',
          }}
        >
          {rounds.length} round{rounds.length === 1 ? '' : 's'}
        </span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {rounds.map((r, i) => (
          <RoundCard
            key={r.id}
            round={r}
            ordinal={i + 1}
            nested
            onUpdated={onUpdated}
            onDeleted={onDeleted}
          />
        ))}
      </div>
    </div>
  );
}
