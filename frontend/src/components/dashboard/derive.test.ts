import { describe, it, expect } from 'vitest';
import {
  readinessTracks,
  pickNextReps,
  pickNextInterview,
  upcomingRounds,
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
