import { describe, it, expect } from 'vitest';
import { linkMetaByEntity, isUnfiled } from '../arrangeMetadata';

describe('linkMetaByEntity', () => {
  it('counts parents and children per entity', () => {
    const conns = [
      { parentId: 'j1', childId: 'p1' },
      { parentId: 'j1', childId: 'b1' },
      { parentId: 'p1', childId: 'b1' },
    ];
    const meta = linkMetaByEntity(conns);
    expect(meta['j1']).toEqual({ parents: 0, children: 2, total: 2 });
    expect(meta['p1']).toEqual({ parents: 1, children: 1, total: 2 });
    expect(meta['b1']).toEqual({ parents: 2, children: 0, total: 2 });
  });

  it('returns an empty map for no connections', () => {
    expect(linkMetaByEntity([])).toEqual({});
  });
});

describe('isUnfiled', () => {
  it('flags non-job entities that have no parent', () => {
    expect(isUnfiled('bullet', undefined)).toBe(true);
    expect(isUnfiled('bullet', { parents: 0, children: 1, total: 1 })).toBe(true);
    expect(isUnfiled('anecdote', { parents: 1, children: 0, total: 1 })).toBe(false);
    expect(isUnfiled('project', undefined)).toBe(true);
  });

  it('flags a job only when it has no children (jobs are roots)', () => {
    expect(isUnfiled('job', undefined)).toBe(true);
    expect(isUnfiled('job', { parents: 0, children: 2, total: 2 })).toBe(false);
  });
});
