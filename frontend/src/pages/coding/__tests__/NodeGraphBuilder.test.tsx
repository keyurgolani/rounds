import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { NodeGraphBuilder } from '../builders/NodeGraphBuilder';
import type { NodeTemplate } from '../types';
import type { VerboseGraph } from '../builders/shorthand';

const linkedListTemplate: NodeTemplate = {
  name: 'Node',
  fields: [{ name: 'val', type: 'int' }],
  links: [{ name: 'next', arity: 'single' }],
};

function chain(values: number[]): VerboseGraph {
  if (values.length === 0) return { nodes: [], entry: null };
  return {
    nodes: values.map((v, i) => ({
      id: i,
      fields: { val: v },
      links: { next: i + 1 < values.length ? i + 1 : null },
    })),
    entry: 0,
  };
}

describe('NodeGraphBuilder chain mode', () => {
  it('renders existing chain in order with arrows', () => {
    render(
      <NodeGraphBuilder
        template={linkedListTemplate}
        layout="chain"
        value={chain([1, 2, 3])}
        onChange={vi.fn()}
      />,
    );
    expect((screen.getByLabelText('Node 1 val') as HTMLInputElement).value).toBe('1');
    expect((screen.getByLabelText('Node 3 val') as HTMLInputElement).value).toBe('3');
  });

  it('appending a node grows the chain and re-wires the tail link', () => {
    const onChange = vi.fn();
    render(
      <NodeGraphBuilder
        template={linkedListTemplate}
        layout="chain"
        value={chain([1, 2])}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByLabelText('Append node'));
    const next = onChange.mock.calls[0][0] as VerboseGraph;
    expect(next.nodes.length).toBe(3);
    // The previous tail (id=1) now points at the new node.
    const tail = next.nodes.find((n) => n.id === 1)!;
    expect(typeof tail.links.next).toBe('number');
  });

  it('removing a middle node re-wires the neighbors', () => {
    const onChange = vi.fn();
    render(
      <NodeGraphBuilder
        template={linkedListTemplate}
        layout="chain"
        value={chain([1, 2, 3])}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByLabelText('Remove node 2'));
    const next = onChange.mock.calls[0][0] as VerboseGraph;
    expect(next.nodes.map((n) => n.fields.val).sort()).toEqual([1, 3]);
    const head = next.nodes.find((n) => n.id === 0)!;
    // Head now points at id=2 (which holds val=3).
    expect(head.links.next).toBe(2);
  });

  it('editing a field updates the value', () => {
    const onChange = vi.fn();
    render(
      <NodeGraphBuilder
        template={linkedListTemplate}
        layout="chain"
        value={chain([1, 2])}
        onChange={onChange}
      />,
    );
    fireEvent.change(screen.getByLabelText('Node 1 val'), { target: { value: '42' } });
    const next = onChange.mock.calls[0][0] as VerboseGraph;
    const updated = next.nodes.find((n) => n.id === 0)!;
    expect(updated.fields.val).toBe(42);
  });
});

const treeTemplate: NodeTemplate = {
  name: 'TreeNode',
  fields: [{ name: 'val', type: 'int' }],
  links: [
    { name: 'left', arity: 'single' },
    { name: 'right', arity: 'single' },
  ],
};

function tree(level: (number | null)[]): VerboseGraph {
  const nodes: VerboseGraph['nodes'] = [];
  const idForPos: Record<number, number> = {};
  for (let pos = 0; pos < level.length; pos++) {
    if (level[pos] === null) continue;
    idForPos[pos] = nodes.length;
    nodes.push({
      id: nodes.length,
      fields: { val: level[pos] as number },
      links: { left: null, right: null },
    });
  }
  if (idForPos[0] === undefined) return { nodes: [], entry: null };
  const queue: [number, number][] = [[0, idForPos[0]]];
  let cursor = 1;
  while (queue.length > 0 && cursor < level.length) {
    const next = queue.shift()!;
    const parentId = next[1];
    for (const ln of ['left', 'right']) {
      if (cursor >= level.length) break;
      const childPos = cursor++;
      if (level[childPos] === null) continue;
      const childId = idForPos[childPos];
      nodes[parentId].links[ln] = childId;
      queue.push([childPos, childId]);
    }
  }
  return { nodes, entry: 0 };
}

describe('NodeGraphBuilder tree mode', () => {
  it('renders existing tree with node value inputs', () => {
    render(
      <NodeGraphBuilder
        template={treeTemplate}
        layout="tree"
        value={tree([1, 2, 3, null, 5])}
        onChange={vi.fn()}
      />,
    );
    expect((screen.getByLabelText('Node 0 val') as HTMLInputElement).value).toBe('1');
    expect((screen.getByLabelText('Node 1 val') as HTMLInputElement).value).toBe('2');
    expect((screen.getByLabelText('Node 2 val') as HTMLInputElement).value).toBe('3');
    expect((screen.getByLabelText('Node 3 val') as HTMLInputElement).value).toBe('5');
  });

  it('shows Add root button for empty tree', () => {
    const onChange = vi.fn();
    render(
      <NodeGraphBuilder
        template={treeTemplate}
        layout="tree"
        value={{ nodes: [], entry: null }}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByLabelText('Add root node'));
    const next = onChange.mock.calls[0][0] as VerboseGraph;
    expect(next.nodes.length).toBe(1);
    expect(next.entry).toBe(0);
  });

  it('shows Add left/right child buttons for leaf nodes', () => {
    render(
      <NodeGraphBuilder
        template={treeTemplate}
        layout="tree"
        value={tree([1])}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByLabelText('Add left child')).toBeTruthy();
    expect(screen.getByLabelText('Add right child')).toBeTruthy();
  });

  it('adding a left child creates a new node and links it', () => {
    const onChange = vi.fn();
    render(
      <NodeGraphBuilder
        template={treeTemplate}
        layout="tree"
        value={tree([1])}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByLabelText('Add left child'));
    const next = onChange.mock.calls[0][0] as VerboseGraph;
    expect(next.nodes.length).toBe(2);
    const root = next.nodes.find((n) => n.id === 0)!;
    expect(root.links.left).toBe(1);
  });

  it('removing a node removes its entire subtree', () => {
    const onChange = vi.fn();
    render(
      <NodeGraphBuilder
        template={treeTemplate}
        layout="tree"
        value={tree([1, 2, 3])}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByLabelText('Remove node 1'));
    const next = onChange.mock.calls[0][0] as VerboseGraph;
    const vals = next.nodes.map((n) => n.fields.val).sort();
    expect(vals).toEqual([1, 3]);
  });

  it('editing a field updates the value', () => {
    const onChange = vi.fn();
    render(
      <NodeGraphBuilder
        template={treeTemplate}
        layout="tree"
        value={tree([1, 2, 3])}
        onChange={onChange}
      />,
    );
    fireEvent.change(screen.getByLabelText('Node 0 val'), { target: { value: '42' } });
    const next = onChange.mock.calls[0][0] as VerboseGraph;
    const root = next.nodes.find((n) => n.id === 0)!;
    expect(root.fields.val).toBe(42);
  });
});

const graphTemplate: NodeTemplate = {
  name: 'Node',
  fields: [{ name: 'val', type: 'int' }],
  links: [{ name: 'neighbors', arity: 'list' }],
};

function graph(adj: Record<number, number[]>): VerboseGraph {
  const keys = Object.keys(adj).map(Number);
  if (keys.length === 0) return { nodes: [], entry: null };
  const nodes = keys.map((k, i) => ({
    id: i,
    fields: { val: k },
    links: {
      neighbors: adj[k]
        .map((n) => keys.indexOf(n))
        .filter((id) => id !== -1),
    },
  }));
  return { nodes, entry: 0 };
}

describe('NodeGraphBuilder graph mode', () => {
  it('renders existing nodes with neighbor pills', () => {
    render(
      <NodeGraphBuilder
        template={graphTemplate}
        layout="general"
        value={graph({ 1: [2, 3], 2: [1], 3: [1] })}
        onChange={vi.fn()}
      />,
    );
    expect((screen.getByLabelText('Node 0 val') as HTMLInputElement).value).toBe('1');
    expect((screen.getByLabelText('Node 1 val') as HTMLInputElement).value).toBe('2');
    expect(screen.getByLabelText('Remove neighbor 1')).toBeTruthy();
    expect(screen.getByLabelText('Remove neighbor 2')).toBeTruthy();
  });

  it('shows Add node button for empty graph', () => {
    const onChange = vi.fn();
    render(
      <NodeGraphBuilder
        template={graphTemplate}
        layout="general"
        value={{ nodes: [], entry: null }}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByLabelText('Add node'));
    const next = onChange.mock.calls[0][0] as VerboseGraph;
    expect(next.nodes.length).toBe(1);
  });

  it('adds a node to a non-empty graph', () => {
    const onChange = vi.fn();
    render(
      <NodeGraphBuilder
        template={graphTemplate}
        layout="general"
        value={graph({ 1: [] })}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByLabelText('Add node'));
    const next = onChange.mock.calls[0][0] as VerboseGraph;
    expect(next.nodes.length).toBe(2);
  });

  it('removing a node cleans up neighbor references', () => {
    const onChange = vi.fn();
    render(
      <NodeGraphBuilder
        template={graphTemplate}
        layout="general"
        value={graph({ 1: [2], 2: [1] })}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByLabelText('Remove node 1'));
    const next = onChange.mock.calls[0][0] as VerboseGraph;
    expect(next.nodes.length).toBe(1);
    const remaining = next.nodes[0];
    expect(remaining.links.neighbors).toEqual([]);
  });

  it('removing a neighbor severs the edge', () => {
    const onChange = vi.fn();
    render(
      <NodeGraphBuilder
        template={graphTemplate}
        layout="general"
        value={graph({ 1: [2], 2: [1] })}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByLabelText('Remove neighbor 1'));
    const next = onChange.mock.calls[0][0] as VerboseGraph;
    const node0 = next.nodes.find((n) => n.id === 0)!;
    expect(node0.links.neighbors).toEqual([]);
  });

  it('editing a field updates the value', () => {
    const onChange = vi.fn();
    render(
      <NodeGraphBuilder
        template={graphTemplate}
        layout="general"
        value={graph({ 1: [], 2: [] })}
        onChange={onChange}
      />,
    );
    fireEvent.change(screen.getByLabelText('Node 0 val'), { target: { value: '99' } });
    const next = onChange.mock.calls[0][0] as VerboseGraph;
    const node = next.nodes.find((n) => n.id === 0)!;
    expect(node.fields.val).toBe(99);
  });
});
