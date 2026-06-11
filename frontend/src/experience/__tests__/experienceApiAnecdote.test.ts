import { describe, it, expect } from 'vitest';
import { adaptAnecdoteRow, anecdotePayload } from '../experienceApi';

describe('anecdotePayload', () => {
  it('maps renamed fields and omits undefined keys', () => {
    expect(anecdotePayload({ title: 'T', category_ids: ['c1'], linked_question_ids: ['q1'] }))
      .toEqual({ title: 'T', categories: ['c1'], linked_questions: ['q1'] });
  });

  it('passes through description and notes', () => {
    expect(anecdotePayload({ description: 'd', notes: 'n' }))
      .toEqual({ description: 'd', notes: 'n' });
  });

  it('returns empty object for empty patch', () => {
    expect(anecdotePayload({})).toEqual({});
  });
});

describe('adaptAnecdoteRow', () => {
  it('maps PB columns to the domain shape with defaults', () => {
    const a = adaptAnecdoteRow({
      id: 'a1', user: 'u1', title: 'T', date: '2026-01-01',
      categories: ['c1'], linked_questions: ['q1'], description: 'd', notes: 'n',
      created: 'C', updated: 'U',
    } as never);
    expect(a.category_ids).toEqual(['c1']);
    expect(a.linked_question_ids).toEqual(['q1']);
    expect(a.description).toBe('d');
    expect(a.notes).toBe('n');
    expect(a.situation).toBe('');
    expect(a.created_at).toBe('C');
  });
});
