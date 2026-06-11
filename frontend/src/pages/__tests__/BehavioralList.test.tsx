import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import BehavioralList from '../BehavioralList';
import { CommandCenterProvider } from '../../command-center/CommandCenterProvider';

// Mock the experience API (new source)
vi.mock('../../experience/experienceApi', () => ({
  listAnecdotes: vi.fn(),
  updateAnecdote: vi.fn(),
}));

// Mock the content API
vi.mock('../../content/api', () => ({
  listBehavioralQuestions: vi.fn(),
  listBehavioralCategories: vi.fn(),
}));

// Mock hooks that depend on localStorage / external state
vi.mock('../../hooks/usePracticeStatus', () => ({
  effectiveStatus: vi.fn(() => 'todo'),
  useStatusMapVersion: vi.fn(() => 0),
}));

const navigateMock = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => navigateMock };
});

import { listAnecdotes, updateAnecdote } from '../../experience/experienceApi';
import { listBehavioralQuestions, listBehavioralCategories } from '../../content/api';

const mockAnecdote = {
  id: 'anec1',
  title: 'Led a major reorg',
  situation: 'Our team was growing fast and the structure was unclear.',
  task: 'Define clear ownership areas.',
  action: 'I proposed and drove a restructuring.',
  result: 'Team velocity improved 30%.',
  impact: 'High',
  company: 'Acme',
  project: 'Reorg2023',
  date: '2023-06-01',
  tags: [],
  description: '',
  category_ids: [],
  linked_question_ids: [],
  notes: '',
  updated_at: '2023-06-02T00:00:00Z',
};

beforeEach(() => {
  navigateMock.mockClear();
  vi.clearAllMocks();
  (listAnecdotes as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([mockAnecdote]);
  (updateAnecdote as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockAnecdote);
  (listBehavioralQuestions as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);
  (listBehavioralCategories as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);
});

function renderList() {
  return render(
    <MemoryRouter>
      <CommandCenterProvider>
        <BehavioralList />
      </CommandCenterProvider>
    </MemoryRouter>,
  );
}

describe('BehavioralList — experience anecdote integration', () => {
  it('renders experience anecdote titles in the notebook column after load', async () => {
    renderList();
    await waitFor(() => {
      expect(screen.getByText('Led a major reorg')).toBeInTheDocument();
    });
  });

  it('calls listAnecdotes from the experience API (not the legacy behavioral API)', async () => {
    renderList();
    await waitFor(() => expect(listAnecdotes).toHaveBeenCalled());
  });

  it('desktop "+ new" button navigates to /experience/list?anecdote=new', async () => {
    renderList();
    await waitFor(() => screen.getByText('Led a major reorg'));
    // The desktop header "+ new" button
    const newButtons = screen.getAllByRole('button', { name: '+ new' });
    newButtons[0].click();
    expect(navigateMock).toHaveBeenCalledWith('/experience/list?anecdote=new');
  });

  it('"Write a new anecdote" dashed button navigates to /experience/list?anecdote=new', async () => {
    renderList();
    await waitFor(() => screen.getByText('Led a major reorg'));
    const writeButton = screen.getByRole('button', { name: /Write a new anecdote/i });
    writeButton.click();
    expect(navigateMock).toHaveBeenCalledWith('/experience/list?anecdote=new');
  });

  it('clicking an anecdote card navigates to /experience/list?anecdote=<id>', async () => {
    renderList();
    await waitFor(() => screen.getByText('Led a major reorg'));
    // The anecdote card open button is the title itself (LinkableCard's onOpen callback).
    // LinkableCard renders a button with the card content — find by the anecdote title text.
    const titleEl = screen.getByText('Led a major reorg');
    // LinkableCard is a div.card whose onClick fires onOpen (unless the click
    // lands on the drag handle). Click the card itself.
    const card = titleEl.closest('.card');
    expect(card).toBeTruthy();
    (card as HTMLElement).click();
    expect(navigateMock).toHaveBeenCalledWith('/experience/list?anecdote=anec1');
  });
});
