import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SeniorTopicsPanel } from '../SeniorTopicsPanel';
import type { SeniorTopic } from '../types';

// Stub MermaidRenderer so we don't spin up real mermaid in jsdom.
vi.mock('../MermaidRenderer', () => ({
  MermaidRenderer: ({ chart }: { chart: string }) => (
    <div data-testid="stub-mermaid">{chart}</div>
  ),
}));

const topics: SeniorTopic[] = [
  {
    id: 't1',
    title: 'First Topic',
    summary: 'first summary',
    sections: [
      { heading: 'Intro', body: 'Intro body text' },
      { heading: 'Details', body: 'Details body text' },
    ],
    diagram: 'graph TD\n  A-->B',
    sources: [{ label: 'Source One', url: 'https://example.com/one' }],
  },
  {
    id: 't2',
    title: 'Second Topic',
    summary: 'second summary',
    sections: [{ heading: 'Only', body: 'Only body' }],
    sources: [{ label: 'Source Two', url: 'https://example.com/two' }],
  },
];

describe('SeniorTopicsPanel', () => {
  it('renders all topic titles and summaries', () => {
    render(<SeniorTopicsPanel topics={topics} />);
    expect(screen.getByText('First Topic')).toBeInTheDocument();
    expect(screen.getByText('Second Topic')).toBeInTheDocument();
    expect(screen.getByText('first summary')).toBeInTheDocument();
    expect(screen.getByText('second summary')).toBeInTheDocument();
  });

  it('shows the first topic body by default, and its sections', () => {
    render(<SeniorTopicsPanel topics={topics} />);
    expect(screen.getByText('Intro')).toBeInTheDocument();
    expect(screen.getByText('Intro body text')).toBeInTheDocument();
    expect(screen.getByText('Details')).toBeInTheDocument();
  });

  it('renders the Mermaid diagram for topics that have one', () => {
    render(<SeniorTopicsPanel topics={topics} />);
    expect(screen.getByTestId('stub-mermaid')).toHaveTextContent('graph TD');
  });

  it('renders sources with external links', () => {
    render(<SeniorTopicsPanel topics={topics} />);
    const link = screen.getByRole('link', { name: /Source One/ });
    expect(link).toHaveAttribute('href', 'https://example.com/one');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', expect.stringContaining('noopener'));
  });

  it('clicking the second topic expands it', () => {
    render(<SeniorTopicsPanel topics={topics} />);
    fireEvent.click(screen.getByRole('button', { name: /Second Topic/ }));
    expect(screen.getByText('Only body')).toBeInTheDocument();
  });
});
