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

function tree123(): VerboseGraph {
  // Root id=0 (val 1) with left=id=1 (val 2), right=id=2 (val 3).
  return {
    nodes: [
      { id: 0, fields: { val: 1 }, links: { left: 1, right: 2 } },
      { id: 1, fields: { val: 2 }, links: { left: null, right: null } },
      { id: 2, fields: { val: 3 }, links: { left: null, right: null } },
    ],
    entry: 0,
  };
}

describe('NodeGraphBuilder chain mode (ChainCanvas)', () => {
  it('renders existing chain values in order', () => {
    render(
      <NodeGraphBuilder
        template={linkedListTemplate}
        layout="chain"
        value={chain([1, 2, 3])}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByTestId('chain-text-0').textContent).toBe('1');
    expect(screen.getByTestId('chain-text-1').textContent).toBe('2');
    expect(screen.getByTestId('chain-text-2').textContent).toBe('3');
  });

  it('appending a node grows the chain and re-wires the previous tail', () => {
    const onChange = vi.fn();
    render(
      <NodeGraphBuilder
        template={linkedListTemplate}
        layout="chain"
        value={chain([1, 2])}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByTestId('chain-append'));
    const next = onChange.mock.calls[0][0] as VerboseGraph;
    expect(next.nodes.length).toBe(3);
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
    // Hover reveals the remove handle.
    fireEvent.mouseEnter(screen.getByTestId('chain-text-1').parentElement!);
    fireEvent.click(screen.getByTestId('chain-remove-1'));
    const next = onChange.mock.calls[0][0] as VerboseGraph;
    expect(next.nodes.map((n) => n.fields.val).sort()).toEqual([1, 3]);
    const head = next.nodes.find((n) => n.id === 0)!;
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
    fireEvent.click(screen.getByTestId('chain-text-0'));
    fireEvent.change(screen.getByTestId('chain-input-0'), { target: { value: '7' } });
    const next = onChange.mock.calls[0][0] as VerboseGraph;
    expect(next.nodes.find((n) => n.id === 0)!.fields.val).toBe(7);
  });
});

describe('NodeGraphBuilder tree mode (TreeCanvas)', () => {
  it('shows Add root button for empty tree', () => {
    render(
      <NodeGraphBuilder
        template={treeTemplate}
        layout="tree"
        value={{ nodes: [], entry: null }}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByTestId('tree-add-root')).toBeTruthy();
  });

  it('renders existing tree node values', () => {
    render(
      <NodeGraphBuilder
        template={treeTemplate}
        layout="tree"
        value={tree123()}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByTestId('tree-text-0').textContent).toBe('1');
    expect(screen.getByTestId('tree-text-1').textContent).toBe('2');
    expect(screen.getByTestId('tree-text-2').textContent).toBe('3');
  });

  it('shows empty add-child slots under leaf nodes', () => {
    render(
      <NodeGraphBuilder
        template={treeTemplate}
        layout="tree"
        value={tree123()}
        onChange={vi.fn()}
      />,
    );
    // id=1 (leaf at val=2) should have empty left + right slots.
    expect(screen.getByTestId('tree-slot-1-left')).toBeTruthy();
    expect(screen.getByTestId('tree-slot-1-right')).toBeTruthy();
  });

  it('clicking an empty slot adds a child and links it', () => {
    const onChange = vi.fn();
    render(
      <NodeGraphBuilder
        template={treeTemplate}
        layout="tree"
        value={tree123()}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByTestId('tree-slot-1-left'));
    const next = onChange.mock.calls[0][0] as VerboseGraph;
    expect(next.nodes.length).toBe(4);
    const parent = next.nodes.find((n) => n.id === 1)!;
    expect(typeof parent.links.left).toBe('number');
  });

  it('removing a subtree drops descendants and clears the parent link', () => {
    // Build root with a 2-deep left subtree so we can verify descendants
    // get pruned, not just the targeted node.
    const value: VerboseGraph = {
      nodes: [
        { id: 0, fields: { val: 1 }, links: { left: 1, right: null } },
        { id: 1, fields: { val: 2 }, links: { left: 3, right: null } },
        { id: 3, fields: { val: 4 }, links: { left: null, right: null } },
      ],
      entry: 0,
    };
    const onChange = vi.fn();
    render(
      <NodeGraphBuilder template={treeTemplate} layout="tree" value={value} onChange={onChange} />,
    );
    fireEvent.mouseEnter(screen.getByTestId('tree-text-1').parentElement!);
    fireEvent.click(screen.getByTestId('tree-remove-1'));
    const next = onChange.mock.calls[0][0] as VerboseGraph;
    expect(next.nodes.map((n) => n.id).sort()).toEqual([0]);
    const root = next.nodes.find((n) => n.id === 0)!;
    expect(root.links.left).toBe(null);
  });

  it('editing a field updates the value', () => {
    const onChange = vi.fn();
    render(
      <NodeGraphBuilder template={treeTemplate} layout="tree" value={tree123()} onChange={onChange} />,
    );
    fireEvent.click(screen.getByTestId('tree-text-0'));
    fireEvent.change(screen.getByTestId('tree-input-0'), { target: { value: '9' } });
    const next = onChange.mock.calls[0][0] as VerboseGraph;
    expect(next.nodes.find((n) => n.id === 0)!.fields.val).toBe(9);
  });
});

describe('NodeGraphBuilder graph mode (GraphCanvas)', () => {
  function graph(values: number[][], edges: [number, number][]): VerboseGraph {
    const nodes = values.map(([id, val]) => ({
      id,
      fields: { val },
      links: { neighbors: edges.flatMap(([a, b]) => (a === id ? [b] : b === id ? [a] : [])) },
    }));
    return { nodes, entry: nodes.length > 0 ? nodes[0].id : null };
  }

  it('shows Add first node button for empty graph', () => {
    render(
      <NodeGraphBuilder
        template={graphTemplate}
        layout="general"
        value={{ nodes: [], entry: null }}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByTestId('graph-add-first')).toBeTruthy();
  });

  it('renders existing nodes with their values', () => {
    render(
      <NodeGraphBuilder
        template={graphTemplate}
        layout="general"
        value={graph(
          [
            [0, 7],
            [1, 8],
          ],
          [[0, 1]],
        )}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByTestId('graph-text-0').textContent).toBe('7');
    expect(screen.getByTestId('graph-text-1').textContent).toBe('8');
  });

  it('Add node toolbar grows the graph', () => {
    const onChange = vi.fn();
    render(
      <NodeGraphBuilder
        template={graphTemplate}
        layout="general"
        value={graph(
          [
            [0, 1],
            [1, 2],
          ],
          [],
        )}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByTitle('Add node'));
    const next = onChange.mock.calls[0][0] as VerboseGraph;
    expect(next.nodes.length).toBe(3);
  });

  it('removing a node strips it from neighbor lists too', () => {
    const onChange = vi.fn();
    render(
      <NodeGraphBuilder
        template={graphTemplate}
        layout="general"
        value={graph(
          [
            [0, 1],
            [1, 2],
            [2, 3],
          ],
          [
            [0, 1],
            [0, 2],
          ],
        )}
        onChange={onChange}
      />,
    );
    fireEvent.mouseEnter(screen.getByTestId('graph-node-2'));
    fireEvent.click(screen.getByTestId('graph-remove-2'));
    const next = onChange.mock.calls[0][0] as VerboseGraph;
    expect(next.nodes.find((n) => n.id === 2)).toBeUndefined();
    const a = next.nodes.find((n) => n.id === 0)!;
    expect(a.links.neighbors).not.toContain(2);
  });

  it('clicking two nodes toggles an edge between them', () => {
    const onChange = vi.fn();
    render(
      <NodeGraphBuilder
        template={graphTemplate}
        layout="general"
        value={graph(
          [
            [0, 1],
            [1, 2],
          ],
          [],
        )}
        onChange={onChange}
      />,
    );
    // Click the circles (not the text — text has stopPropagation).
    fireEvent.click(screen.getByTestId('graph-circle-0'));
    fireEvent.click(screen.getByTestId('graph-circle-1'));
    const next = onChange.mock.calls[0][0] as VerboseGraph;
    const a = next.nodes.find((n) => n.id === 0)!;
    const b = next.nodes.find((n) => n.id === 1)!;
    expect(a.links.neighbors).toContain(1);
    expect(b.links.neighbors).toContain(0);
  });

  it('clicking an existing edge again removes it', () => {
    const onChange = vi.fn();
    render(
      <NodeGraphBuilder
        template={graphTemplate}
        layout="general"
        value={graph(
          [
            [0, 1],
            [1, 2],
          ],
          [[0, 1]],
        )}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByTestId('graph-circle-0'));
    fireEvent.click(screen.getByTestId('graph-circle-1'));
    const next = onChange.mock.calls[0][0] as VerboseGraph;
    const a = next.nodes.find((n) => n.id === 0)!;
    expect(a.links.neighbors).not.toContain(1);
  });

  it('editing a node value updates the field', () => {
    const onChange = vi.fn();
    render(
      <NodeGraphBuilder
        template={graphTemplate}
        layout="general"
        value={graph([[0, 1]], [])}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByTestId('graph-text-0'));
    fireEvent.change(screen.getByTestId('graph-input-0'), { target: { value: '5' } });
    const next = onChange.mock.calls[0][0] as VerboseGraph;
    expect(next.nodes.find((n) => n.id === 0)!.fields.val).toBe(5);
  });
});
