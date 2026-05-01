import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ERDiagram } from '../ERDiagram';
import { parseER } from '../internal/parseER';

vi.mock('../MermaidRenderer', () => ({
  MermaidRenderer: ({ chart }: { chart: string }) => (
    <div data-testid="stub-mermaid">{chart}</div>
  ),
}));

const SRC =
  'erDiagram\n' +
  '  USERS ||--o{ URLS : owns\n' +
  '  URLS ||--o{ CLICKS : has\n' +
  '  USERS {\n' +
  '    bigint id PK\n' +
  '    varchar email\n' +
  '  }\n' +
  '  URLS {\n' +
  '    bigint id PK\n' +
  '    bigint user_id FK\n' +
  '    text long_url\n' +
  '  }\n' +
  '  CLICKS {\n' +
  '    bigint id PK\n' +
  '    varchar short_code\n' +
  '  }';

describe('parseER', () => {
  it('parses entities, columns, and relation cardinalities', () => {
    const data = parseER(SRC);
    expect(data).not.toBeNull();
    expect(data!.entities.map((e) => e.name).sort()).toEqual(['CLICKS', 'URLS', 'USERS']);
    const users = data!.entities.find((e) => e.name === 'USERS')!;
    expect(users.columns.map((c) => c.name)).toEqual(['id', 'email']);
    expect(users.columns[0].keys).toEqual(['PK']);

    const rel = data!.relations.find((r) => r.target === 'URLS')!;
    expect(rel.sourceCard).toBe('one');
    expect(rel.targetCard).toBe('zero-or-many');
    expect(rel.label).toBe('owns');
  });

  it('returns null when header is missing', () => {
    expect(parseER('USERS ||--o{ URLS : owns')).toBeNull();
  });
});

describe('ERDiagram', () => {
  it('renders entity names and columns', () => {
    render(<ERDiagram source={SRC} />);
    expect(screen.getByText('USERS')).toBeInTheDocument();
    expect(screen.getByText('URLS')).toBeInTheDocument();
    expect(screen.getByText('CLICKS')).toBeInTheDocument();
    expect(screen.getAllByText('id').length).toBeGreaterThan(0);
  });

  it('renders at least one relation path', () => {
    const { container } = render(<ERDiagram source={SRC} />);
    const canvas = container.querySelector('[data-testid="er-canvas"]');
    expect(canvas).not.toBeNull();
    const paths = canvas!.querySelectorAll('path');
    expect(paths.length).toBeGreaterThanOrEqual(2); // 2 relations
  });

  it('falls back to Mermaid when parsing fails', () => {
    render(<ERDiagram source={'erDiagram\n  unknown_statement_here'} />);
    expect(screen.getByTestId('stub-mermaid')).toBeInTheDocument();
  });
});
