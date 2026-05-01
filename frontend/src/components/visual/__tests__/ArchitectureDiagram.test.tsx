import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ArchitectureDiagram } from '../ArchitectureDiagram';
import type { ArchitectureDiagramData } from '../types';

const data: ArchitectureDiagramData = {
  nodes: [
    { id: 'a', label: 'Alpha', type: 'client' },
    { id: 'b', label: 'Beta', type: 'server' },
  ],
  edges: [{ source: 'a', target: 'b', animated: true }],
};

describe('ArchitectureDiagram', () => {
  it('renders nodes from data', () => {
    render(<ArchitectureDiagram data={data} />);
    expect(screen.getByText('Alpha')).toBeInTheDocument();
    expect(screen.getByText('Beta')).toBeInTheDocument();
  });

  it('renders nothing visible when data is empty', () => {
    render(<ArchitectureDiagram data={{ nodes: [], edges: [] }} />);
    expect(screen.queryByText('Alpha')).not.toBeInTheDocument();
  });

  it('edges are rendered as SVG paths between nodes', () => {
    const { container } = render(<ArchitectureDiagram data={data} />);
    const svg = container.querySelector('svg');
    expect(svg).not.toBeNull();
    const paths = svg!.querySelectorAll('path');
    expect(paths.length).toBeGreaterThanOrEqual(1);
  });

  it('renders two SVG layers and edge labels appear in the top layer', () => {
    const labelData: ArchitectureDiagramData = {
      nodes: [
        { id: 'a', label: 'Alpha', type: 'client' },
        { id: 'b', label: 'Beta', type: 'server' },
      ],
      edges: [{ source: 'a', target: 'b', label: 'HTTP' }],
    };
    const { container } = render(<ArchitectureDiagram data={labelData} />);
    // The relative container should contain exactly two SVG elements.
    const relativeDiv = container.querySelector('div[style*="position: relative"]');
    expect(relativeDiv).not.toBeNull();
    const svgs = relativeDiv!.querySelectorAll(':scope > svg');
    expect(svgs.length).toBe(2);
    // Edge label text must live in the second (top) SVG, not the first.
    const topSvg = svgs[1];
    const textEls = topSvg.querySelectorAll('text');
    expect(textEls.length).toBeGreaterThanOrEqual(1);
    expect(textEls[0].textContent).toBe('HTTP');
  });

  it('nodes are grouped into rows by type — client above server above database', () => {
    const multiData: ArchitectureDiagramData = {
      nodes: [
        { id: 'c', label: 'MyClient', type: 'client' },
        { id: 's', label: 'MyServer', type: 'server' },
        { id: 'd', label: 'MyDatabase', type: 'database' },
      ],
      edges: [],
    };
    const { container } = render(<ArchitectureDiagram data={multiData} />);

    // Node cards are absolutely positioned divs inside the relative container.
    // We identify them by finding divs that contain the label text and reading
    // their inline `top` style value.
    function topOf(label: string): number {
      const el = screen.getByText(label);
      // Walk up to the absolutely positioned card container.
      let node: HTMLElement | null = el;
      while (node && node.style?.position !== 'absolute') {
        node = node.parentElement;
      }
      return node ? parseInt(node.style.top, 10) : NaN;
    }

    const clientTop = topOf('MyClient');
    const serverTop = topOf('MyServer');
    const dbTop = topOf('MyDatabase');

    expect(clientTop).toBeLessThan(serverTop);
    expect(serverTop).toBeLessThan(dbTop);
  });
});
