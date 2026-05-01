import { describe, it, expect } from 'vitest';
import { toVerbose, fromVerboseChain, type VerboseGraph } from '../builders/shorthand';
import type { NodeTemplate } from '../types';

const linkedListTemplate: NodeTemplate = {
  name: 'Node',
  fields: [{ name: 'val', type: 'int' }],
  links: [{ name: 'next', arity: 'single' }],
};
const treeTemplate: NodeTemplate = {
  name: 'TreeNode',
  fields: [{ name: 'val', type: 'int' }],
  links: [
    { name: 'left', arity: 'single' },
    { name: 'right', arity: 'single' },
  ],
};
const graphTemplate: NodeTemplate = {
  name: 'Node',
  fields: [{ name: 'val', type: 'int' }],
  links: [{ name: 'neighbors', arity: 'list' }],
};

describe('shorthand toVerbose', () => {
  it('linked_list_array singly', () => {
    expect(toVerbose([1, 2, 3], 'linked_list_array', linkedListTemplate)).toEqual({
      nodes: [
        { id: 0, fields: { val: 1 }, links: { next: 1 } },
        { id: 1, fields: { val: 2 }, links: { next: 2 } },
        { id: 2, fields: { val: 3 }, links: { next: null } },
      ],
      entry: 0,
    });
  });

  it('tree_level_order with nulls', () => {
    const r = toVerbose([1, 2, 3, null, 5], 'tree_level_order', treeTemplate);
    expect(r.entry).toBe(0);
    expect(r.nodes.length).toBe(4);
    expect(r.nodes[1].links).toEqual({ left: null, right: 3 });
  });

  it('graph_adjacency', () => {
    const r = toVerbose({ '1': [2], '2': [1] }, 'graph_adjacency', graphTemplate);
    expect(r.nodes.length).toBe(2);
    expect(r.nodes[0].fields).toEqual({ val: 1 });
    expect(r.nodes[0].links.neighbors).toEqual([1]);
  });

  it('verbose passthrough', () => {
    const v: VerboseGraph = {
      nodes: [{ id: 0, fields: { val: 9 }, links: { next: null } }],
      entry: 0,
    };
    expect(toVerbose(v, 'verbose', linkedListTemplate)).toBe(v);
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
