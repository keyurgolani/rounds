import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import {
  CommandCenterProvider,
  useCommandCenter,
} from '../CommandCenterProvider';
import { CommandCenter } from '../CommandCenter';

vi.mock('../../todos/api', () => ({
  listTodos: vi.fn().mockResolvedValue([]),
  createTodo: vi.fn().mockResolvedValue({ id: 'tod123' }),
  updateTodo: vi.fn().mockResolvedValue({ id: 'tod123' }),
  deleteTodo: vi.fn().mockResolvedValue(undefined),
}));

vi.mock('../../campaign/CampaignContext', () => ({
  useCampaign: () => ({
    currentId: 'camp1',
    currentCampaign: { id: 'camp1', name: 'Acme' },
  }),
}));

function Trigger() {
  const cc = useCommandCenter();
  return <button onClick={() => cc.openView('add-todo')}>open</button>;
}

describe('AddTodoView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders TodoForm body field when opened from Command Center', async () => {
    render(
      <MemoryRouter>
        <CommandCenterProvider>
          <Trigger />
          <CommandCenter />
        </CommandCenterProvider>
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByText('open'));
    // TodoForm placeholder: "What's next? Type @ to mention a question, ..."
    await waitFor(() =>
      expect(screen.getByPlaceholderText(/what'?s next/i)).toBeInTheDocument(),
    );
  });
});
