import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AnecdoteLibrary } from '../AnecdoteLibrary';
import type { Anecdote, BehavioralCategoryLite, BehavioralQuestionLite } from '../types';
import { api } from '../../../api/client';

vi.mock('../../../api/client', () => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), del: vi.fn() },
}));

const navigateMock = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => navigateMock };
});

beforeEach(() => {
  navigateMock.mockClear();
  vi.clearAllMocks();
});

const cats: BehavioralCategoryLite[] = [
  { id: 1, name: 'Ownership', color: '#7928ca', icon: '◆' },
  { id: 2, name: 'Empathy', color: '#0072f5', icon: '○' },
];
const questions: BehavioralQuestionLite[] = [
  { id: 10, title: 'Tell me about a conflict' },
];
const anecdotes: Anecdote[] = [
  { id: 1, title: 'Reorg story', description: '', situation: 'A',  task: '', action: '', result: '', category_ids: [1, 2], linked_question_ids: [10], notes: '' },
  { id: 2, title: 'Failure story', description: '', situation: 'B', task: '', action: '', result: '', category_ids: [2], linked_question_ids: [], notes: '' },
];

describe('AnecdoteLibrary', () => {
  it('fetches anecdotes on mount and renders cards', async () => {
    (api.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(anecdotes);
    render(<AnecdoteLibrary categories={cats} questions={questions} />);
    await waitFor(() => {
      expect(screen.getByText('Reorg story')).toBeInTheDocument();
      expect(screen.getByText('Failure story')).toBeInTheDocument();
    });
  });

  it('filters by category chip', async () => {
    (api.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(anecdotes);
    render(<AnecdoteLibrary categories={cats} questions={questions} />);
    await waitFor(() => screen.getByText('Reorg story'));
    fireEvent.click(screen.getByRole('button', { name: /^Ownership/ }));
    expect(screen.getByText('Reorg story')).toBeInTheDocument();
    expect(screen.queryByText('Failure story')).not.toBeInTheDocument();
  });

  it('clicking + New anecdote navigates to /behavioral/anecdotes/new', async () => {
    (api.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    render(<AnecdoteLibrary categories={cats} questions={questions} />);
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    fireEvent.click(screen.getByRole('button', { name: /\+ New anecdote/i }));
    expect(navigateMock).toHaveBeenCalledWith('/behavioral/anecdotes/new');
  });

  it('clicking edit on an AnecdoteCard navigates to /:id/edit', async () => {
    (api.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(anecdotes);
    render(<AnecdoteLibrary categories={cats} questions={questions} />);
    await waitFor(() => screen.getByText('Reorg story'));
    fireEvent.click(screen.getByRole('button', { name: /Reorg story/ }));
    expect(navigateMock).toHaveBeenCalledWith('/behavioral/anecdotes/1/edit');
  });
});
