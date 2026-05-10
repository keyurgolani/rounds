import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import TakeHomeList from '../../pages/take-home/TakeHomeList';
import { CommandCenterProvider } from '../../command-center/CommandCenterProvider';

vi.mock('../../pages/take-home/takeHomeApi', () => ({
  listAssignments: vi.fn(),
}));

import { listAssignments } from '../../pages/take-home/takeHomeApi';

describe('TakeHomeList', () => {
  beforeEach(() => {
    (listAssignments as unknown as { mockReset: () => void }).mockReset();
  });

  it('renders the seeded assignments fetched from listAssignments', async () => {
    (listAssignments as unknown as { mockResolvedValue: (v: unknown) => void }).mockResolvedValue([
      { id: '1', slug: 'kv-store-py', title: 'Tiny KV Store', difficulty: 'easy', language: 'python', time_budget_min: 60, ai_policy: 'off', prompt_md: '', starter_files: [], rubric: { items: [] } },
      { id: '2', slug: 'event-bus-ts', title: 'Event Bus', difficulty: 'easy', language: 'typescript', time_budget_min: 60, ai_policy: 'off', prompt_md: '', starter_files: [], rubric: { items: [] } },
    ]);
    render(
      <MemoryRouter>
        <CommandCenterProvider>
          <TakeHomeList />
        </CommandCenterProvider>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Tiny KV Store')).toBeInTheDocument();
      expect(screen.getByText('Event Bus')).toBeInTheDocument();
    });
  });

  it('renders the empty state when there are no assignments', async () => {
    (listAssignments as unknown as { mockResolvedValue: (v: unknown) => void }).mockResolvedValue([]);
    render(
      <MemoryRouter>
        <CommandCenterProvider>
          <TakeHomeList />
        </CommandCenterProvider>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText(/No assignments available yet/i)).toBeInTheDocument();
    });
  });
});
