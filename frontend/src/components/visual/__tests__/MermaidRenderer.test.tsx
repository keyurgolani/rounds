import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MermaidRenderer } from '../MermaidRenderer';

vi.mock('mermaid', () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn(async (id: string, _src: string) => ({
      svg: `<svg data-id="${id}"><g/></svg>`,
    })),
  },
}));

describe('MermaidRenderer', () => {
  it('renders the SVG produced by mermaid', async () => {
    render(<MermaidRenderer chart="graph TD\n  A --> B" />);
    await waitFor(() => {
      const container = screen.getByTestId('mermaid');
      expect(container.innerHTML).toMatch(/<svg/);
    });
  });

  it('shows a fallback while loading', () => {
    render(<MermaidRenderer chart="graph TD\n  A --> B" />);
    expect(screen.getByTestId('mermaid-loading')).toBeInTheDocument();
  });
});
