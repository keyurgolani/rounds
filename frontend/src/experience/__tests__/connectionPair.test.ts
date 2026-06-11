import { describe, it, expect } from 'vitest';
import { orderedValidPair, canParent } from '../connectionPair';

describe('orderedValidPair', () => {
  it('orders job + project as parent job, child project', () => {
    expect(orderedValidPair('job', 'j1', 'project', 'p1')).toEqual({
      parentKind: 'job', parentId: 'j1', childKind: 'project', childId: 'p1',
    });
  });

  it('orders the same pair regardless of argument order', () => {
    expect(orderedValidPair('project', 'p1', 'job', 'j1')).toEqual({
      parentKind: 'job', parentId: 'j1', childKind: 'project', childId: 'p1',
    });
  });

  it('orders anecdote + bullet as parent anecdote, child bullet', () => {
    expect(orderedValidPair('bullet', 'b1', 'anecdote', 'a1')).toEqual({
      parentKind: 'anecdote', parentId: 'a1', childKind: 'bullet', childId: 'b1',
    });
  });

  it('orders job + bullet as parent job, child bullet', () => {
    expect(orderedValidPair('job', 'j1', 'bullet', 'b1')).toEqual({
      parentKind: 'job', parentId: 'j1', childKind: 'bullet', childId: 'b1',
    });
  });

  it('returns null when both entities are the same kind', () => {
    expect(orderedValidPair('job', 'j1', 'job', 'j2')).toBeNull();
    expect(orderedValidPair('bullet', 'b1', 'bullet', 'b2')).toBeNull();
  });
});

describe('canParent (directional)', () => {
  it('is true when the parent kind ranks above the child kind', () => {
    expect(canParent('job', 'project')).toBe(true);
    expect(canParent('job', 'anecdote')).toBe(true);
    expect(canParent('job', 'bullet')).toBe(true);
    expect(canParent('project', 'anecdote')).toBe(true);
    expect(canParent('project', 'bullet')).toBe(true);
    expect(canParent('anecdote', 'bullet')).toBe(true);
  });

  it('is false in the reverse direction', () => {
    expect(canParent('project', 'job')).toBe(false);
    expect(canParent('bullet', 'job')).toBe(false);
    expect(canParent('bullet', 'anecdote')).toBe(false);
    expect(canParent('anecdote', 'project')).toBe(false);
  });

  it('is false for same-kind pairs', () => {
    expect(canParent('job', 'job')).toBe(false);
    expect(canParent('bullet', 'bullet')).toBe(false);
  });
});
