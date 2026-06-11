import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import AICodingList from '../../pages/ai-coding/AICodingList';
import { CommandCenterProvider } from '../../command-center/CommandCenterProvider';

vi.mock('../../pages/ai-coding/aiCodingApi', async (importOriginal) => {
  // Keep the real `effectiveLanguages` + `resolveRound` helpers — the
  // list page derives its language chip and filter from them.
  const actual = (await importOriginal()) as Record<string, unknown>;
  return {
    ...actual,
    listRounds: vi.fn().mockResolvedValue([
      {
        id: '1',
        slug: 'hallucinated-http-client',
        title: 'Hallucinated HTTP client',
        difficulty: 'easy',
        language: 'python',
        checkpoints: [],
        starter_files: [],
        rubric: { items: [] },
        description: '',
        topics: [],
        companies: [],
      },
    ]),
  };
});

describe('AICodingList', () => {
  it('renders a row per round', async () => {
    render(
      <MemoryRouter>
        <CommandCenterProvider>
          <AICodingList />
        </CommandCenterProvider>
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.getByText('Hallucinated HTTP client')).toBeTruthy(),
    );
    expect(screen.getByText('python')).toBeTruthy();
  });
});
