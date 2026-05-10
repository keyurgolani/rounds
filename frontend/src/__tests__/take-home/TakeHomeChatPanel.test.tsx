import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import TakeHomeChatPanel from '../../components/take-home/TakeHomeChatPanel';

vi.mock('../../pages/ai-coding/aiCodingApi', () => ({
  listAICodingModels: vi.fn().mockResolvedValue([]),
}));

vi.mock('../../lib/runnerFetch', () => ({
  runnerSSE: vi.fn(),
}));

describe('TakeHomeChatPanel', () => {
  it('shows the empty-state hint', () => {
    render(
      <TakeHomeChatPanel
        assignmentSlug="kv-store-py"
        files={{}}
      />,
    );
    expect(
      screen.getByText(/Ask about the prompt or your code/i),
    ).toBeInTheDocument();
  });

  it('disables the send button when draft is empty', () => {
    render(
      <TakeHomeChatPanel
        assignmentSlug="kv-store-py"
        files={{}}
      />,
    );
    expect(screen.getByRole('button', { name: /send message/i })).toBeDisabled();
  });
});
