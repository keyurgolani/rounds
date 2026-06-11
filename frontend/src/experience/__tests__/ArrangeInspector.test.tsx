import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ArrangeInspector from '../ArrangeInspector';
import type { TimelineEntity } from '../experienceApi';

const entity = { kind: 'job', id: 'j1', company: 'Acme', role: 'Engineer', start_date: '2020-01-01' } as unknown as TimelineEntity;
const bundle = {
  connections: [],
  connMap: {},
  reverseMap: {},
  allEntities: [],
  onConnectionChanged: vi.fn(),
  onNavigate: vi.fn(),
};

describe('ArrangeInspector', () => {
  it('renders the entity title and tier tag', () => {
    render(
      <ArrangeInspector
        entity={entity} title="Acme" subtitle="Engineer" connection={bundle}
        onNavigate={vi.fn()} onEdit={vi.fn()} onDelete={vi.fn()} onClose={vi.fn()}
      />,
    );
    expect(screen.getByText('Acme')).toBeInTheDocument();
    expect(screen.getByText('JOB')).toBeInTheDocument();
  });

  it('fires onEdit and onDelete', async () => {
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    render(
      <ArrangeInspector
        entity={entity} title="Acme" connection={bundle}
        onNavigate={vi.fn()} onEdit={onEdit} onDelete={onDelete} onClose={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByText('Edit details'));
    expect(onEdit).toHaveBeenCalled();
    await userEvent.click(screen.getByLabelText('Delete'));
    expect(onDelete).toHaveBeenCalled();
  });
});
