import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MyAnecdotesPanel } from '../MyAnecdotesPanel';
import type { Anecdote, BehavioralCategoryLite, BehavioralQuestionLite } from '../types';
import { listAnecdotes, updateAnecdote } from '../anecdotesApi';

vi.mock('../anecdotesApi', () => ({
  listAnecdotes: vi.fn(),
  createAnecdote: vi.fn(),
  updateAnecdote: vi.fn(),
  deleteAnecdote: vi.fn(),
  getAnecdote: vi.fn(),
}));

const navigateMock = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => navigateMock };
});

const listAnecdotesMock = listAnecdotes as unknown as ReturnType<typeof vi.fn>;
const updateAnecdoteMock = updateAnecdote as unknown as ReturnType<typeof vi.fn>;

beforeEach(() => {
  navigateMock.mockClear();
  vi.clearAllMocks();
});

const cats: BehavioralCategoryLite[] = [
  { id: 'cat1', name: 'Ownership', color: '#7928ca', icon: '◆' },
  { id: 'cat2', name: 'Empathy', color: '#0072f5', icon: '○' },
];
const questions: BehavioralQuestionLite[] = [
  { id: 'q10', title: 'Tell me about a conflict' },
  { id: 'q11', title: 'Tell me about a failure' },
];
const anecdotes: Anecdote[] = [
  {
    id: 'a1',
    title: 'Linked story',
    description: '',
    situation: 'X situation',
    task: '',
    action: '',
    result: '',
    category_ids: ['cat2'],
    linked_question_ids: ['q10'],
    notes: '',
    updated_at: '2026-04-18T00:00:00',
  },
  {
    id: 'a2',
    title: 'Match candidate',
    description: '',
    situation: 'Y situation',
    task: '',
    action: '',
    result: '',
    category_ids: ['cat2'],
    linked_question_ids: [],
    notes: '',
    updated_at: '2026-04-17T00:00:00',
  },
  {
    id: 'a3',
    title: 'Other story',
    description: '',
    situation: 'Z situation',
    task: '',
    action: '',
    result: '',
    category_ids: ['cat1'],
    linked_question_ids: [],
    notes: '',
    updated_at: '2026-04-16T00:00:00',
  },
];

function renderPanel(questionId = 'q10') {
  return render(
    <MyAnecdotesPanel
      questionId={questionId}
      questionCategoryIds={['cat2']}
      categories={cats}
      questions={questions}
    />
  );
}

describe('MyAnecdotesPanel', () => {
  it('auto-selects the first linked anecdote and loads it into the STAR editor', async () => {
    listAnecdotesMock.mockResolvedValue(anecdotes);
    renderPanel();
    await waitFor(() => screen.getByDisplayValue('Linked story'));
    expect(screen.getByDisplayValue('X situation')).toBeInTheDocument();
  });

  it('opens the library panel and excludes already-linked anecdotes', async () => {
    listAnecdotesMock.mockResolvedValue(anecdotes);
    renderPanel();
    await waitFor(() => screen.getByDisplayValue('Linked story'));
    fireEvent.click(screen.getByRole('button', { name: /Link from library/i }));
    expect(screen.getByText('Match candidate')).toBeInTheDocument();
    expect(screen.getByText('Other story')).toBeInTheDocument();
    expect(screen.queryAllByText('Linked story').length).toBe(1);
  });

  it('library list orders category-matching anecdotes first', async () => {
    listAnecdotesMock.mockResolvedValue(anecdotes);
    renderPanel();
    await waitFor(() => screen.getByDisplayValue('Linked story'));
    fireEvent.click(screen.getByRole('button', { name: /Link from library/i }));
    const rows = screen
      .getAllByRole('button')
      .filter((b) => /Match candidate|Other story/.test(b.textContent ?? ''));
    const matchIdx = rows.findIndex((el) => (el.textContent ?? '').includes('Match candidate'));
    const otherIdx = rows.findIndex((el) => (el.textContent ?? '').includes('Other story'));
    expect(matchIdx).toBeLessThan(otherIdx);
  });

  it('clicking a library row updates the anecdote with the question added', async () => {
    listAnecdotesMock.mockResolvedValue(anecdotes);
    updateAnecdoteMock.mockResolvedValue({ ...anecdotes[1], linked_question_ids: ['q10'] });
    renderPanel();
    await waitFor(() => screen.getByDisplayValue('Linked story'));
    fireEvent.click(screen.getByRole('button', { name: /Link from library/i }));
    fireEvent.click(screen.getByRole('button', { name: /Match candidate/i }));
    await waitFor(() => expect(updateAnecdoteMock).toHaveBeenCalled());
    const [id, body] = updateAnecdoteMock.mock.calls[0];
    expect(id).toBe('a2');
    expect(body.linked_question_ids).toContain('q10');
  });

  it('Unlink removes the current question from the selected anecdote', async () => {
    listAnecdotesMock.mockResolvedValue(anecdotes);
    updateAnecdoteMock.mockResolvedValue({ ...anecdotes[0], linked_question_ids: [] });
    renderPanel();
    await waitFor(() => screen.getByDisplayValue('Linked story'));
    fireEvent.click(screen.getByRole('button', { name: /unlink/i }));
    await waitFor(() => expect(updateAnecdoteMock).toHaveBeenCalled());
    const body = updateAnecdoteMock.mock.calls[0][1];
    expect(body.linked_question_ids).not.toContain('q10');
  });

  it('New anecdote button navigates to new anecdote page with ?question=<slug>', async () => {
    listAnecdotesMock.mockResolvedValue(anecdotes);
    renderPanel();
    await waitFor(() => screen.getByDisplayValue('Linked story'));
    fireEvent.click(screen.getByRole('button', { name: /^\s*New anecdote\s*$/i }));
    expect(navigateMock).toHaveBeenCalledWith('/behavioral/anecdotes/new?question=tell-me-about-a-conflict');
  });

  it('defaults to description mode when the selected anecdote has only description content', async () => {
    const descOnly: Anecdote[] = [
      {
        id: 'a10',
        title: 'Desc only',
        description: 'A quick summary of what happened.',
        situation: '',
        task: '',
        action: '',
        result: '',
        category_ids: ['cat2'],
        linked_question_ids: ['q10'],
        notes: '',
        updated_at: '2026-04-18T00:00:00',
      },
    ];
    listAnecdotesMock.mockResolvedValue(descOnly);
    renderPanel();
    await waitFor(() => screen.getByDisplayValue('Desc only'));
    expect(screen.getByDisplayValue('A quick summary of what happened.')).toBeInTheDocument();
  });

  it('defaults to STAR mode when the anecdote has STAR content', async () => {
    listAnecdotesMock.mockResolvedValue(anecdotes);
    renderPanel();
    await waitFor(() => screen.getByDisplayValue('Linked story'));
    expect(screen.getByDisplayValue('X situation')).toBeInTheDocument();
  });
});
