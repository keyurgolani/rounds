import type { PracticeStatus } from '../shell/StatusDot';

export type TrackKey = 'coding' | 'system' | 'behavioral' | 'ai-coding' | 'take-home';
export type StatusItem = { id: string; title: string; difficulty?: string };
export type StatusFn = (track: TrackKey, id: string) => PracticeStatus;
export type ReadinessLists = Record<TrackKey, StatusItem[]>;

const TRACK_ORDER: TrackKey[] = ['coding', 'system', 'behavioral', 'ai-coding', 'take-home'];

/** Show rounds that started up to this many ms ago, so in-flight events stay visible. */
const ROUND_LOOKBACK_MS = 12 * 3_600_000;

const TRACK_META: Record<TrackKey, { name: string; to: string; color: string; rep: (id: string) => string }> = {
  coding: { name: 'Coding', to: '/coding/guide', color: 'var(--forest)', rep: (id) => `/coding/question/${id}` },
  system: { name: 'System Design', to: '/system-design/guide', color: 'var(--terracotta)', rep: (id) => `/system-design/question/${id}` },
  behavioral: { name: 'Behavioral', to: '/behavioral/guide', color: 'var(--plum)', rep: (id) => `/behavioral/question/${id}` },
  'ai-coding': { name: 'AI-Assisted Coding', to: '/ai-coding/guide', color: 'var(--ochre)', rep: (id) => `/ai-coding/round/${id}` },
  // No themeable CSS var for a 5th track color; sage hex is intentional.
  'take-home': { name: 'Real-World Problems', to: '/take-home/guide', color: '#6f8a86', rep: (id) => `/take-home/assignment/${id}` },
};

export type TrackReadiness = {
  key: TrackKey; name: string; to: string; color: string;
  total: number; mastered: number; inProgress: number;
};

export function readinessTracks(lists: ReadinessLists, status: StatusFn): TrackReadiness[] {
  return TRACK_ORDER.map((key) => {
    let mastered = 0;
    let inProgress = 0;
    for (const it of lists[key]) {
      const s = status(key, it.id);
      if (s === 'mastered') mastered++;
      else if (s === 'in-progress') inProgress++;
    }
    const m = TRACK_META[key];
    return { key, name: m.name, to: m.to, color: m.color, total: lists[key].length, mastered, inProgress };
  });
}

export type NextRep = { kind: string; title: string; status: PracticeStatus; difficulty?: string; to: string };

export function pickNextReps(lists: ReadinessLists, status: StatusFn, limit = 2): NextRep[] {
  const picks: NextRep[] = [];
  for (const key of TRACK_ORDER) {
    const inProgressItem = lists[key].find((it) => status(key, it.id) === 'in-progress');
    const item = inProgressItem ?? lists[key].find((it) => status(key, it.id) === 'todo');
    if (!item) continue;
    const m = TRACK_META[key];
    picks.push({ kind: m.name, title: item.title, status: inProgressItem ? 'in-progress' : 'todo', difficulty: item.difficulty, to: m.rep(item.id) });
  }
  picks.sort((a, b) => Number(b.status === 'in-progress') - Number(a.status === 'in-progress'));
  return picks.slice(0, limit);
}

export type DashRound = {
  id: string; application_id: string; round_type: string; date: string;
  interviewer?: string; scheduled_status?: string;
};

export function upcomingRounds(rounds: DashRound[], now: number): DashRound[] {
  const horizon = now - ROUND_LOOKBACK_MS;
  return rounds
    .filter((r) => r.scheduled_status !== 'completed' && r.scheduled_status !== 'canceled')
    .map((r) => ({ r, ts: Date.parse(r.date) }))
    .filter((x) => !Number.isNaN(x.ts) && x.ts >= horizon)
    .sort((a, b) => a.ts - b.ts)
    .map((x) => x.r);
}

export function pickNextInterview(rounds: DashRound[], now: number): DashRound | null {
  const up = upcomingRounds(rounds, now);
  return up.length ? up[0] : null;
}
