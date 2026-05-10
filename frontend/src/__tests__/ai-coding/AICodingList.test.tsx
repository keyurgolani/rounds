import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import AICodingList from '../../pages/ai-coding/AICodingList';
import { CommandCenterProvider } from '../../command-center/CommandCenterProvider';

vi.mock('../../pages/ai-coding/aiCodingApi', () => ({
  listRounds: vi.fn().mockResolvedValue([
    {
      id: '1',
      slug: 'cart-bugfix-py',
      title: 'Shopping Cart',
      difficulty: 'medium',
      language: 'python',
      checkpoints: [],
      starter_files: [],
      rubric: { items: [] },
      description: '',
      topics: [],
      companies: [],
    },
  ]),
}));

describe('AICodingList', () => {
  it('renders a row per round', async () => {
    render(
      <MemoryRouter>
        <CommandCenterProvider>
          <AICodingList />
        </CommandCenterProvider>
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByText('Shopping Cart')).toBeTruthy());
    expect(screen.getByText('python')).toBeTruthy();
  });
});
