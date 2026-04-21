import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { FlowchartDiagram } from '../FlowchartDiagram';
import { parseFlowchart } from '../internal/parseFlowchart';

vi.mock('../MermaidRenderer', () => ({
  MermaidRenderer: ({ chart }: { chart: string }) => (
    <div data-testid="stub-mermaid">{chart}</div>
  ),
}));

describe('parseFlowchart', () => {
  it('parses rect and diamond nodes with labeled edges', () => {
    const src =
      'graph TD\n' +
      '  A[Start] --> B{Branch}\n' +
      '  B -->|yes| C[Go]\n' +
      '  B -->|no| D[Stop]\n';
    const data = parseFlowchart(src);
    expect(data).not.toBeNull();
    expect(data!.nodes.map((n) => n.id).sort()).toEqual(['A', 'B', 'C', 'D']);
    const b = data!.nodes.find((n) => n.id === 'B')!;
    expect(b.shape).toBe('diamond');
    expect(b.label).toBe('Branch');

    const yesEdge = data!.edges.find((e) => e.label === 'yes');
    expect(yesEdge).toMatchObject({ source: 'B', target: 'C' });
  });

  it('strips surrounding quotes from labels', () => {
    const data = parseFlowchart('graph TD\n  A["1:1 or group?"] --> B[Next]');
    expect(data).not.toBeNull();
    expect(data!.nodes[0].label).toBe('1:1 or group?');
  });

  it('returns null when the header is missing', () => {
    expect(parseFlowchart('A --> B')).toBeNull();
  });

  it('returns null when subgraph syntax appears (force fallback)', () => {
    const src = 'graph TD\n  subgraph S\n  A --> B\n  end';
    expect(parseFlowchart(src)).toBeNull();
  });
});

describe('FlowchartDiagram', () => {
  it('renders node labels from the parsed source', () => {
    render(
      <FlowchartDiagram source={'graph TD\n  A[Read] --> B{Decide}\n  B -->|yes| C[Ship]'} />,
    );
    expect(screen.getByText('Read')).toBeInTheDocument();
    expect(screen.getByText('Decide')).toBeInTheDocument();
    expect(screen.getByText('Ship')).toBeInTheDocument();
  });

  it('renders edge labels in the second SVG layer', () => {
    const { container } = render(
      <FlowchartDiagram source={'graph TD\n  A[One] --> B[Two]\n  A -->|go| B'} />,
    );
    const canvas = container.querySelector('[data-testid="flowchart-canvas"]');
    const svgs = canvas!.querySelectorAll(':scope > svg');
    expect(svgs.length).toBe(2);
    const labelSvg = svgs[1];
    expect(labelSvg.textContent).toContain('go');
  });

  it('falls back to Mermaid when parsing fails', () => {
    render(<FlowchartDiagram source={'graph TD\n  subgraph x\n  A --> B\n  end'} />);
    expect(screen.getByTestId('stub-mermaid')).toBeInTheDocument();
  });
});
