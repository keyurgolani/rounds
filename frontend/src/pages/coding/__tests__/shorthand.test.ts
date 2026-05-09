import { describe, it, expect } from 'vitest';
import {
  asVerbose,
  fromVerboseChain,
  fromVerboseLevelOrder,
  type VerboseGraph,
} from '../builders/shorthand';
import type { NodeTemplate } from '../types';

const linkedListTemplate: NodeTemplate = {
  name: 'Node',
  fields: [{ name: 'val', type: 'int' }],
  links: [{ name: 'next', arity: 'single' }],
};

describe('asVerbose', () => {
  it('passes through a verbose graph unchanged', () => {
    const v: VerboseGraph = {
      nodes: [{ id: 0, fields: { val: 9 }, links: { next: null } }],
      entry: 0,
    };
    expect(asVerbose(v, linkedListTemplate)).toBe(v);
  });

  it('returns an empty graph for a legacy array shorthand (must not silently convert)', () => {
    expect(asVerbose([1, 2, 3], linkedListTemplate)).toEqual({ nodes: [], entry: null });
  });

  it('returns an empty graph for undefined / null inputs', () => {
    expect(asVerbose(undefined, linkedListTemplate)).toEqual({ nodes: [], entry: null });
    expect(asVerbose(null, linkedListTemplate)).toEqual({ nodes: [], entry: null });
  });
});

describe('fromVerboseChain', () => {
  it('flattens a singly-linked verbose graph', () => {
    const v: VerboseGraph = {
      nodes: [
        { id: 0, fields: { val: 1 }, links: { next: 1 } },
        { id: 1, fields: { val: 2 }, links: { next: 2 } },
        { id: 2, fields: { val: 3 }, links: { next: null } },
      ],
      entry: 0,
    };
    expect(fromVerboseChain(v, 'next', 'val')).toEqual([1, 2, 3]);
  });

  it('returns [] for empty', () => {
    expect(fromVerboseChain({ nodes: [], entry: null }, 'next', 'val')).toEqual([]);
  });
});

describe('fromVerboseLevelOrder', () => {
  it('walks BFS, emitting nulls for missing children, trimming trailing nulls', () => {
    const v: VerboseGraph = {
      nodes: [
        { id: 0, fields: { val: 1 }, links: { left: 1, right: 2 } },
        { id: 1, fields: { val: 2 }, links: { left: null, right: 3 } },
        { id: 2, fields: { val: 3 }, links: { left: null, right: null } },
        { id: 3, fields: { val: 5 }, links: { left: null, right: null } },
      ],
      entry: 0,
    };
    expect(fromVerboseLevelOrder(v, 'left', 'right', 'val')).toEqual([1, 2, 3, null, 5]);
  });
});
