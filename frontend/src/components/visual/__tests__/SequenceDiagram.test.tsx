import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SequenceDiagram } from '../SequenceDiagram';
import { parseSequence } from '../internal/parseSequence';

vi.mock('../MermaidRenderer', () => ({
  MermaidRenderer: ({ chart }: { chart: string }) => (
    <div data-testid="stub-mermaid">{chart}</div>
  ),
}));

const SRC =
  'sequenceDiagram\n' +
  '  participant C as Client\n' +
  '  participant API as API Server\n' +
  '  participant R as Redis\n' +
  '  C->>API: GET /v1/users\n' +
  '  API->>R: INCR rl:user:1\n' +
  '  R-->>API: 6\n' +
  '  alt under limit\n' +
  '    API-->>C: 200 OK\n' +
  '  else over\n' +
  '    API-->>C: 429\n' +
  '  end';

describe('parseSequence', () => {
  it('parses participants, messages, and block markers', () => {
    const data = parseSequence(SRC);
    expect(data).not.toBeNull();
    expect(data!.participants.map((p) => p.id)).toEqual(['C', 'API', 'R']);
    const msgs = data!.steps.filter((s) => s.type === 'msg');
    expect(msgs.length).toBe(5);
    const dashed = msgs.filter((m) => m.type === 'msg' && m.dashed);
    expect(dashed.length).toBe(3); // R-->>API, API-->>C ×2

    const blockOpens = data!.steps.filter((s) => s.type === 'block-open');
    const blockElses = data!.steps.filter((s) => s.type === 'block-else');
    const blockCloses = data!.steps.filter((s) => s.type === 'block-close');
    expect(blockOpens.length).toBe(1);
    expect(blockElses.length).toBe(1);
    expect(blockCloses.length).toBe(1);
  });

  it('returns null on a missing header', () => {
    expect(parseSequence('C->>API: hi')).toBeNull();
  });
});

describe('SequenceDiagram', () => {
  it('renders participant ids and labels', () => {
    render(<SequenceDiagram source={SRC} />);
    expect(screen.getByText('Client')).toBeInTheDocument();
    expect(screen.getByText('API Server')).toBeInTheDocument();
    expect(screen.getByText('Redis')).toBeInTheDocument();
    // The ids show up as monospace eyebrows next to the labels.
    expect(screen.getAllByText('API').length).toBeGreaterThan(0);
  });

  it('renders a lifeline per participant', () => {
    const { container } = render(<SequenceDiagram source={SRC} />);
    const canvas = container.querySelector('[data-testid="sequence-canvas"]');
    expect(canvas).not.toBeNull();
    const lifelines = canvas!.querySelectorAll('line');
    expect(lifelines.length).toBeGreaterThanOrEqual(3);
  });

  it('falls back to Mermaid when parsing fails', () => {
    render(<SequenceDiagram source={'sequenceDiagram\n  !!nonsense syntax!!'} />);
    expect(screen.getByTestId('stub-mermaid')).toBeInTheDocument();
  });
});
