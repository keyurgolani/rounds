import type { PracticeStatus } from '../shell/StatusDot';
import type { ReverseConnectionMap } from '../../experience/connectionApi';

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

export type ThinCategory = { id: string; name: string; color?: string; count: number };
export type BehavioralDepthResult = {
  covered: number; total: number; storyCount: number; categoryCount: number; thinCategories: ThinCategory[];
};

export function behavioralDepth(
  questions: { id: string }[],
  categories: { id: string; name: string; color?: string }[],
  anecdotes: { linked_question_ids: string[]; category_ids: string[] }[],
): BehavioralDepthResult {
  const linked = new Set<string>();
  for (const a of anecdotes) for (const qid of a.linked_question_ids ?? []) linked.add(qid);
  const perCat = new Map<string, number>();
  for (const a of anecdotes) for (const cid of a.category_ids ?? []) perCat.set(cid, (perCat.get(cid) ?? 0) + 1);
  const thinCategories = categories
    .map((c) => ({ id: c.id, name: c.name, color: c.color, count: perCat.get(c.id) ?? 0 }))
    .sort((a, b) => a.count - b.count)
    .slice(0, THIN_CATEGORY_LIMIT);
  return {
    covered: questions.filter((q) => linked.has(q.id)).length,
    total: questions.length,
    storyCount: anecdotes.length,
    categoryCount: categories.length,
    thinCategories,
  };
}

export type MissingResumeApp = { id: string; company: string };
export type ResumeCoverageResult = {
  resumeCount: number; lastEditedAt: string | null; relevant: number; covered: number; missing: MissingResumeApp[];
};

const RESUME_RELEVANT_STATUSES = ['Applied', 'Interviewing'];

export type DashApp = {
  id: string; company: string; role: string; status: string;
  applied_date?: string; updated_at?: string; last_activity_at?: string;
};

export function resumeCoverage(
  resumes: { updated_at?: string }[],
  variants: { application_id?: string }[],
  apps: DashApp[],
): ResumeCoverageResult {
  const coveredAppIds = new Set(
    variants.map((v) => v.application_id).filter((x): x is string => !!x),
  );
  const relevant = apps.filter((a) => RESUME_RELEVANT_STATUSES.includes(a.status));
  const missing = relevant.filter((a) => !coveredAppIds.has(a.id)).map((a) => ({ id: a.id, company: a.company }));
  const lastEditedAt = resumes
    .map((r) => r.updated_at)
    .filter((x): x is string => !!x)
    .sort()
    .slice(-1)[0] ?? null;
  return { resumeCount: resumes.length, lastEditedAt, relevant: relevant.length, covered: relevant.length - missing.length, missing };
}

export type ExperienceOverviewResult = {
  jobs: number; projects: number; anecdotes: number; bullets: number; addedThisWeek: number; unusedBullets: number;
};

export function experienceOverview(
  jobs: { created_at?: string }[],
  projects: { created_at?: string }[],
  anecdotes: { created_at?: string }[],
  bullets: { id: string; created_at?: string }[],
  reverseMap: ReverseConnectionMap,
  now: number,
): ExperienceOverviewResult {
  const weekAgo = now - 7 * 86_400_000;
  const recent = (arr: { created_at?: string }[]) =>
    arr.filter((e) => {
      const t = Date.parse(e.created_at ?? '');
      return !Number.isNaN(t) && t >= weekAgo;
    }).length;
  const unusedBullets = bullets.filter((b) => {
    const parents = reverseMap[b.id];
    return !parents || Object.values(parents).every((ids) => ids.length === 0);
  }).length;
  return {
    jobs: jobs.length,
    projects: projects.length,
    anecdotes: anecdotes.length,
    bullets: bullets.length,
    addedThisWeek: recent(jobs) + recent(projects) + recent(anecdotes) + recent(bullets),
    unusedBullets,
  };
}

// --- At-risk (relocated from AtRiskSection.tsx; that file is deleted in the
//     final task and its rendering folds into TodayZone) ----------------------
export type DashOffer = { id: string; application_id: string; status: string; decision_deadline?: string };
export type DashTodo = { id: string; body: string; due_date?: string; priority?: 'low' | 'normal' | 'high'; completed_at?: string };

const STALE_APP_DAYS = 10;
const STALE_ROUND_HORIZON_DAYS = 14;
const OFFER_DEADLINE_HORIZON_DAYS = 3;
const THIN_CATEGORY_LIMIT = 3;

export function computeAtRisk(
  todos: DashTodo[],
  apps: DashApp[],
  rounds: DashRound[],
  offers: DashOffer[],
  now = Date.now(),
) {
  const staleCutoff = now - STALE_APP_DAYS * 86_400_000;
  const roundHorizon = now + STALE_ROUND_HORIZON_DAYS * 86_400_000;
  const offerCutoff = now + OFFER_DEADLINE_HORIZON_DAYS * 86_400_000;

  const overdueTodos = todos
    .filter((t) => {
      if (t.completed_at) return false;
      if (!t.due_date) return false;
      const d = Date.parse(t.due_date);
      return !Number.isNaN(d) && d < now;
    })
    .sort((a, b) => (a.due_date || '').localeCompare(b.due_date || ''));

  const staleApps: { app: DashApp; reason: string }[] = [];
  for (const app of apps) {
    if (app.status !== 'Applied' && app.status !== 'Interviewing') continue;
    const lastTs = Date.parse(app.last_activity_at ?? app.updated_at ?? '');
    const effectiveTs = Number.isNaN(lastTs) ? 0 : lastTs;
    if (effectiveTs > staleCutoff) continue;
    const hasUpcomingRound = rounds.some((r) => {
      if (r.application_id !== app.id) return false;
      if (r.scheduled_status === 'completed' || r.scheduled_status === 'canceled') return false;
      const ts = Date.parse(r.date);
      return !Number.isNaN(ts) && ts >= now && ts <= roundHorizon;
    });
    if (hasUpcomingRound) continue;
    // Static reason: TodayZone renders "— stale" and never shows this string (no need to port the old day-count).
    staleApps.push({ app, reason: 'No recent activity and no upcoming round' });
  }

  const pendingOffers: { offer: DashOffer; appLabel: string; reason: string }[] = [];
  for (const offer of offers) {
    if (offer.status !== 'pending') continue;
    const deadlineTs = Date.parse(offer.decision_deadline ?? '');
    const hasDeadline = !Number.isNaN(deadlineTs);
    if (hasDeadline && deadlineTs > offerCutoff) continue;
    const app = apps.find((a) => a.id === offer.application_id);
    pendingOffers.push({
      offer,
      appLabel: app ? `${app.company} · ${app.role}` : offer.application_id,
      reason: !hasDeadline ? 'No decision deadline set' : deadlineTs < now ? 'Deadline has passed' : 'Deadline within 3 days',
    });
  }

  staleApps.sort(
    (a, b) =>
      (Date.parse(a.app.last_activity_at ?? a.app.updated_at ?? '0') || 0) -
      (Date.parse(b.app.last_activity_at ?? b.app.updated_at ?? '0') || 0),
  );
  pendingOffers.sort(
    (a, b) =>
      (Date.parse(a.offer.decision_deadline ?? '9999') || 0) -
      (Date.parse(b.offer.decision_deadline ?? '9999') || 0),
  );

  return { overdueTodos, staleApps, pendingOffers };
}
