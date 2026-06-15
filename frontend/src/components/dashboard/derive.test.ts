import { describe, it, expect } from 'vitest';
import {
  readinessTracks,
  pickNextReps,
  pickNextInterview,
  upcomingRounds,
  behavioralDepth,
  resumeCoverage,
  experienceOverview,
  computeAtRisk,
  type ReadinessLists,
  type StatusFn,
} from './derive';

const lists: ReadinessLists = {
  coding: [{ id: 'c1', title: 'LRU Cache', difficulty: 'Medium' }, { id: 'c2', title: 'Two Sum' }],
  system: [{ id: 's1', title: 'Rate Limiter' }],
  behavioral: [{ id: 'b1', title: 'Conflict' }],
  'ai-coding': [],
  'take-home': [{ id: 't1', title: 'CSV Summarize' }],
};

const statusFor = (map: Record<string, 'todo' | 'in-progress' | 'mastered'>): StatusFn =>
  (track, id) => map[`${track}:${id}`] ?? 'todo';

describe('readinessTracks', () => {
  it('returns all five tracks in order with mastered/in-progress counts', () => {
    const status = statusFor({ 'coding:c1': 'mastered', 'coding:c2': 'in-progress' });
    const tracks = readinessTracks(lists, status);
    expect(tracks.map((t) => t.key)).toEqual(['coding', 'system', 'behavioral', 'ai-coding', 'take-home']);
    const coding = tracks[0];
    expect(coding).toMatchObject({ total: 2, mastered: 1, inProgress: 1, name: 'Coding' });
    expect(tracks[3]).toMatchObject({ key: 'ai-coding', total: 0, mastered: 0, inProgress: 0 });
    expect(coding.to).toBe('/coding/guide');
    expect(coding.color).toBe('var(--forest)');
  });
});

describe('pickNextReps', () => {
  it('prefers in-progress over todo and caps at the limit', () => {
    const status = statusFor({ 'system:s1': 'in-progress', 'coding:c1': 'todo' });
    const reps = pickNextReps(lists, status, 2);
    expect(reps).toHaveLength(2);
    expect(reps[0]).toMatchObject({ kind: 'System Design', status: 'in-progress', to: '/system-design/question/s1' });
    expect(reps[1].status).toBe('todo');
  });
  it('skips tracks with no todo/in-progress item', () => {
    const status = statusFor({ 'coding:c1': 'mastered', 'coding:c2': 'mastered' });
    const reps = pickNextReps(lists, status, 5);
    expect(reps.some((r) => r.kind === 'Coding')).toBe(false);
  });
});

describe('upcomingRounds', () => {
  const NOW = Date.parse('2026-06-14T00:00:00Z');
  it('excludes completed/canceled rounds and returns the rest chronologically', () => {
    const result = upcomingRounds([
      { id: 'r1', application_id: 'a1', round_type: 'Onsite', date: '2026-06-20T00:00:00Z' },
      { id: 'r2', application_id: 'a2', round_type: 'Phone', date: '2026-06-16T00:00:00Z' },
      { id: 'r3', application_id: 'a3', round_type: 'Canceled', date: '2026-06-17T00:00:00Z', scheduled_status: 'canceled' },
    ], NOW);
    expect(result.map((r) => r.id)).toEqual(['r2', 'r1']);
  });
});

describe('pickNextInterview', () => {
  const NOW = Date.parse('2026-06-14T00:00:00Z');
  it('returns the soonest non-completed future round', () => {
    const next = pickNextInterview([
      { id: 'r1', application_id: 'a1', round_type: 'Onsite', date: '2026-06-20T00:00:00Z' },
      { id: 'r2', application_id: 'a2', round_type: 'Phone', date: '2026-06-16T00:00:00Z' },
      { id: 'r3', application_id: 'a3', round_type: 'Done', date: '2026-06-15T00:00:00Z', scheduled_status: 'completed' },
    ], NOW);
    expect(next?.id).toBe('r2');
  });
  it('returns null when nothing is upcoming', () => {
    expect(pickNextInterview([{ id: 'r1', application_id: 'a1', round_type: 'X', date: '2020-01-01T00:00:00Z' }], NOW)).toBeNull();
  });
});

describe('behavioralDepth', () => {
  it('counts questions with a linked story and the thinnest categories', () => {
    const res = behavioralDepth(
      [{ id: 'q1' }, { id: 'q2' }, { id: 'q3' }],
      [{ id: 'cat1', name: 'Conflict' }, { id: 'cat2', name: 'Leadership', color: 'red' }],
      [
        { linked_question_ids: ['q1'], category_ids: ['cat2'] },
        { linked_question_ids: ['q1', 'q2'], category_ids: ['cat2'] },
      ],
    );
    expect(res).toMatchObject({ covered: 2, total: 3, storyCount: 2, categoryCount: 2 });
    expect(res.thinCategories[0]).toMatchObject({ id: 'cat1', name: 'Conflict', count: 0 });
    expect(res.thinCategories).toHaveLength(2);
  });
});

describe('resumeCoverage', () => {
  it('flags Applied/Interviewing apps that have no tailored variant', () => {
    const res = resumeCoverage(
      [{ updated_at: '2026-06-10T00:00:00Z' }, { updated_at: '2026-06-12T00:00:00Z' }],
      [{ application_id: 'a1' }, { application_id: undefined }],
      [
        { id: 'a1', company: 'Stripe', role: 'SWE', status: 'Applied' },
        { id: 'a2', company: 'Figma', role: 'SWE', status: 'Interviewing' },
        { id: 'a3', company: 'Idea', role: 'SWE', status: 'Wishlist' },
      ],
    );
    expect(res).toMatchObject({ resumeCount: 2, relevant: 2, covered: 1, lastEditedAt: '2026-06-12T00:00:00Z' });
    expect(res.missing).toEqual([{ id: 'a2', company: 'Figma' }]);
  });
});

describe('experienceOverview', () => {
  const NOW = Date.parse('2026-06-14T00:00:00Z');
  it('counts entities, recent adds, and bullets with no parent connection', () => {
    const res = experienceOverview(
      [{ created_at: '2026-06-13T00:00:00Z' }],
      [],
      [{ created_at: '2020-01-01T00:00:00Z' }],
      [{ id: 'bl1' }, { id: 'bl2' }],
      { bl1: { job: ['j1'], project: [], anecdote: [], bullet: [] } } as never,
      NOW,
    );
    expect(res).toMatchObject({ jobs: 1, anecdotes: 1, bullets: 2, addedThisWeek: 1, unusedBullets: 1 });
  });
});

describe('computeAtRisk', () => {
  it('surfaces overdue todos', () => {
    const { overdueTodos } = computeAtRisk(
      [{ id: 't1', body: 'x', due_date: '2000-01-01', completed_at: '' }],
      [], [], [],
    );
    expect(overdueTodos).toHaveLength(1);
  });
});

describe('computeAtRisk — stale apps & pending offers', () => {
  const NOW = Date.parse('2026-06-14T00:00:00Z');
  it('flags stale Applied/Interviewing apps with no upcoming round, most-neglected first', () => {
    const apps = [
      { id: 'a1', company: 'Old', role: 'SWE', status: 'Applied', last_activity_at: '2026-05-01T00:00:00Z' },
      { id: 'a2', company: 'Older', role: 'SWE', status: 'Interviewing', last_activity_at: '2026-04-01T00:00:00Z' },
      { id: 'a3', company: 'Fresh', role: 'SWE', status: 'Applied', last_activity_at: '2026-06-13T00:00:00Z' },
    ];
    const { staleApps } = computeAtRisk([], apps, [], [], NOW);
    expect(staleApps.map((s) => s.app.id)).toEqual(['a2', 'a1']);
  });
  it('includes pending offers with no deadline and excludes far-future deadlines', () => {
    const apps = [{ id: 'a1', company: 'X', role: 'r', status: 'Offer' }, { id: 'a2', company: 'Y', role: 'r', status: 'Offer' }];
    const offers = [
      { id: 'o1', application_id: 'a1', status: 'pending' },
      { id: 'o2', application_id: 'a2', status: 'pending', decision_deadline: '2099-01-01T00:00:00Z' },
    ];
    const { pendingOffers } = computeAtRisk([], apps, [], offers, NOW);
    expect(pendingOffers.map((p) => p.offer.id)).toEqual(['o1']);
    expect(pendingOffers[0].reason).toBe('No decision deadline set');
  });
});
