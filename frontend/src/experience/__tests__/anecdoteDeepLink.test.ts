import { describe, it, expect } from 'vitest';
import { resolveAnecdoteParam } from '../anecdoteDeepLink';
import type { TimelineEntity } from '../experienceApi';

const ent = (id: string, title: string): TimelineEntity =>
  ({ kind: 'anecdote', id, title, date: '2026-01-01', situation: '', task: '', action: '',
     result: '', impact: '', company: '', project: '', tags: [], description: '',
     category_ids: [], linked_question_ids: [], notes: '' } as TimelineEntity);

describe('resolveAnecdoteParam', () => {
  const entities = [ent('abc123', 'Scaled the Pipeline'), ent('def456', 'Mentored Interns')];

  it('matches by id', () => {
    expect(resolveAnecdoteParam('abc123', entities)?.id).toBe('abc123');
  });
  it('matches by slugified title', () => {
    expect(resolveAnecdoteParam('scaled-the-pipeline', entities)?.id).toBe('abc123');
  });
  it('returns null for "new" and for unknown', () => {
    expect(resolveAnecdoteParam('new', entities)).toBeNull();
    expect(resolveAnecdoteParam('nope', entities)).toBeNull();
  });
  it('ignores non-anecdote entities', () => {
    const job = { kind: 'job', id: 'abc123', company: 'X' } as unknown as TimelineEntity;
    expect(resolveAnecdoteParam('abc123', [job])).toBeNull();
  });
});
