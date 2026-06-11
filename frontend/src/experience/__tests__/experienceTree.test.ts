import { describe, it, expect } from 'vitest';
import { childIdsOf, hasChildren, subtreeMaxDate, rowTitle, formatDate, rowSubtitle } from '../experienceTree';
import { buildConnectionMap, type Connection } from '../connectionApi';
import type { TimelineEntity, EntityKind } from '../experienceApi';

const conns: Connection[] = [
  { id: 'c1', junctionTable: 'exp_job_projects', parentId: 'j1', childId: 'p1' },
  { id: 'c2', junctionTable: 'exp_job_bullets', parentId: 'j1', childId: 'b1' },
  { id: 'c3', junctionTable: 'exp_project_anecdotes', parentId: 'p1', childId: 'a1' },
];
const connMap = buildConnectionMap(conns);

// A superset object cast to TimelineEntity — the helpers only read a few fields.
const ent = (id: string, kind: EntityKind, date: string): TimelineEntity =>
  ({
    id, kind,
    title: id, company: id, role: '',
    start_date: date, end_date: null, date,
    description: '', tags: [],
    situation: '', task: '', action: '', result: '', impact: '',
  } as unknown as TimelineEntity);

const entityById: Record<string, TimelineEntity> = {
  j1: ent('j1', 'job', '2020-01-01'),
  p1: ent('p1', 'project', '2021-01-01'),
  a1: ent('a1', 'anecdote', '2022-06-01'),
  b1: ent('b1', 'bullet', '2019-01-01'),
};

describe('experienceTree helpers', () => {
  it('childIdsOf returns children in kind order (project, anecdote, bullet)', () => {
    expect(childIdsOf(connMap, 'j1')).toEqual([
      { kind: 'project', id: 'p1' },
      { kind: 'bullet', id: 'b1' },
    ]);
  });

  it('hasChildren reflects whether a node has any children', () => {
    expect(hasChildren(connMap, 'j1')).toBe(true);
    expect(hasChildren(connMap, 'b1')).toBe(false);
  });

  it('subtreeMaxDate returns the newest date anywhere in the subtree', () => {
    // j1's newest descendant is a1 (2022-06), reached via p1.
    expect(subtreeMaxDate('j1', connMap, entityById)).toBe(+new Date('2022-06-01'));
  });

  it('rowTitle uses company for jobs and title for everything else', () => {
    // Use inline objects with DISTINCT company vs title so both branches are validated.
    const job = { kind: 'job', company: 'ACME Corp', title: 'Senior Engineer' } as unknown as TimelineEntity;
    const project = { kind: 'project', title: 'My Project', company: 'Side Co' } as unknown as TimelineEntity;
    expect(rowTitle(job)).toBe('ACME Corp');
    expect(rowTitle(project)).toBe('My Project');
  });

  describe('formatDate', () => {
    it('produces "Present" for job/project with null end_date', () => {
      const job = { kind: 'job', start_date: '2020-01-01', end_date: null } as unknown as TimelineEntity;
      const project = { kind: 'project', start_date: '2021-03-01', end_date: null } as unknown as TimelineEntity;
      expect(formatDate(job)).toContain('Present');
      expect(formatDate(project)).toContain('Present');
    });

    it('produces an en-dash range for job/project with non-null end_date', () => {
      const job = { kind: 'job', start_date: '2019-06-15', end_date: '2021-06-15' } as unknown as TimelineEntity;
      expect(formatDate(job)).toContain('–');
      expect(formatDate(job)).toContain('2019');
      expect(formatDate(job)).toContain('2021');
    });

    it('produces a single month-year label for anecdote/bullet (uses date field)', () => {
      const anecdote = { kind: 'anecdote', date: '2022-06-01' } as unknown as TimelineEntity;
      const bullet = { kind: 'bullet', date: '2019-03-01' } as unknown as TimelineEntity;
      expect(formatDate(anecdote)).toContain('2022');
      expect(formatDate(anecdote)).not.toContain('–');
      expect(formatDate(bullet)).toContain('2019');
      expect(formatDate(bullet)).not.toContain('–');
    });
  });

  describe('rowSubtitle', () => {
    it('returns role for a job', () => {
      const job = { kind: 'job', role: 'Staff Engineer', company: 'Corp' } as unknown as TimelineEntity;
      expect(rowSubtitle(job)).toBe('Staff Engineer');
    });

    it('returns company · role for a project', () => {
      const project = { kind: 'project', company: 'Side Co', role: 'Lead', title: 'Proj' } as unknown as TimelineEntity;
      expect(rowSubtitle(project)).toBe('Side Co · Lead');
    });

    it('returns result (falling back to situation) for an anecdote', () => {
      const withResult = { kind: 'anecdote', result: 'Shipped it', situation: 'We needed it', date: '2022-01-01' } as unknown as TimelineEntity;
      const withoutResult = { kind: 'anecdote', result: '', situation: 'Background', date: '2022-01-01' } as unknown as TimelineEntity;
      expect(rowSubtitle(withResult)).toContain('Shipped it');
      expect(rowSubtitle(withoutResult)).toContain('Background');
    });

    it('returns impact for a bullet', () => {
      const bullet = { kind: 'bullet', impact: 'Cut latency 40%', date: '2021-01-01' } as unknown as TimelineEntity;
      expect(rowSubtitle(bullet)).toBe('Cut latency 40%');
    });
  });
});
