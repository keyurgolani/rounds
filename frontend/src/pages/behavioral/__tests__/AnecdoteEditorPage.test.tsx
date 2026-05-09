import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { AnecdoteEditorPage } from '../AnecdoteEditorPage';
import {
  listBehavioralCategories,
  listBehavioralQuestions,
} from '../../../content/api';
import {
  createAnecdote,
  deleteAnecdote,
  listAnecdotes,
  updateAnecdote,
} from '../anecdotesApi';
import { CommandCenterProvider } from '../../../command-center/CommandCenterProvider';

vi.mock('../../../content/api', () => ({
  listBehavioralCategories: vi.fn(),
  listBehavioralQuestions: vi.fn(),
  getBehavioralQuestion: vi.fn(),
  listSystemDesignQuestions: vi.fn(),
  getSystemDesignQuestion: vi.fn(),
  listCodingQuestions: vi.fn(),
  getCodingQuestion: vi.fn(),
  getSystemDesignGuide: vi.fn(),
  getCodingGuide: vi.fn(),
  getBehavioralGuide: vi.fn(),
}));

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

const cats = [
  { id: 'cat1', name: 'Ownership', color: '#7928ca', icon: '◆' },
  { id: 'cat2', name: 'Empathy', color: '#0072f5', icon: '○' },
];
const questions = [
  { id: 'q10', title: 'Tell me about a conflict' },
  { id: 'q11', title: 'Tell me about a failure' },
];
const existingAnecdote = {
  id: '5',
  title: 'Existing anecdote',
  description: 'A description here',
  situation: '',
  task: '',
  action: '',
  result: '',
  category_ids: ['cat1'],
  linked_question_ids: ['q10'],
  notes: 'Some notes',
};

const duplicateSlugAnecdote = {
  ...existingAnecdote,
  id: '6',
  title: 'API Test',
};

function renderNew(path = '/behavioral/anecdotes/new') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <CommandCenterProvider>
        <Routes>
          <Route path="/behavioral/anecdotes/new" element={<AnecdoteEditorPage />} />
          <Route path="/behavioral/anecdotes/:slug/edit" element={<AnecdoteEditorPage />} />
        </Routes>
      </CommandCenterProvider>
    </MemoryRouter>
  );
}

const listCategoriesMock = listBehavioralCategories as unknown as ReturnType<typeof vi.fn>;
const listQuestionsMock = listBehavioralQuestions as unknown as ReturnType<typeof vi.fn>;
const listAnecdotesMock = listAnecdotes as unknown as ReturnType<typeof vi.fn>;
const createAnecdoteMock = createAnecdote as unknown as ReturnType<typeof vi.fn>;
const updateAnecdoteMock = updateAnecdote as unknown as ReturnType<typeof vi.fn>;
const deleteAnecdoteMock = deleteAnecdote as unknown as ReturnType<typeof vi.fn>;

beforeEach(() => {
  navigateMock.mockClear();
  vi.clearAllMocks();
});

function mockContent(anecdotes: typeof cats[number][] | unknown[] = []) {
  listCategoriesMock.mockResolvedValue(cats);
  listQuestionsMock.mockResolvedValue(questions);
  listAnecdotesMock.mockResolvedValue(anecdotes);
}

describe('AnecdoteEditorPage', () => {
  it('renders Both mode by default on /new (Description + STAR both visible)', async () => {
    mockContent([]);
    renderNew();
    await waitFor(() => screen.getByLabelText('Title'));
    expect(screen.getByLabelText('Description')).toBeInTheDocument();
    expect(screen.getByLabelText('Situation')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Description$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^STAR$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Both$/i })).toBeInTheDocument();
  });

  it('toggling to STAR-only shows S/T/A/R fields and hides Description', async () => {
    mockContent([]);
    renderNew();
    await waitFor(() => screen.getByLabelText('Title'));
    fireEvent.click(screen.getByRole('button', { name: /^STAR$/i }));
    expect(screen.queryByLabelText('Description')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Situation')).toBeInTheDocument();
    expect(screen.getByLabelText('Task')).toBeInTheDocument();
    expect(screen.getByLabelText('Action')).toBeInTheDocument();
    expect(screen.getByLabelText('Result')).toBeInTheDocument();
  });

  it('toggling to Description-only hides STAR fields', async () => {
    mockContent([]);
    renderNew();
    await waitFor(() => screen.getByLabelText('Title'));
    fireEvent.click(screen.getByRole('button', { name: /^Description$/i }));
    expect(screen.getByLabelText('Description')).toBeInTheDocument();
    expect(screen.queryByLabelText('Situation')).not.toBeInTheDocument();
  });

  it('entering a title + description and submitting calls createAnecdote', async () => {
    mockContent([]);
    createAnecdoteMock.mockResolvedValue({
      id: '99', title: 'My story', description: 'Free-form text', situation: '', task: '',
      action: '', result: '', category_ids: [], linked_question_ids: [], notes: '',
    });
    renderNew();
    await waitFor(() => screen.getByLabelText('Title'));
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'My story' } });
    fireEvent.change(screen.getByLabelText('Description'), { target: { value: 'Free-form text' } });
    fireEvent.click(screen.getByRole('button', { name: /Save anecdote/i }));
    await waitFor(() => expect(createAnecdoteMock).toHaveBeenCalled());
    const [body] = createAnecdoteMock.mock.calls[0];
    expect(body).toMatchObject({ title: 'My story', description: 'Free-form text' });
    expect(navigateMock).toHaveBeenCalledWith(-1);
  });

  it('blocks creating an anecdote when another title has the same slug', async () => {
    mockContent([duplicateSlugAnecdote]);
    renderNew();
    await waitFor(() => screen.getByLabelText('Title'));
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'API test' } });
    fireEvent.click(screen.getByRole('button', { name: /Save anecdote/i }));
    expect(await screen.findByText(/already exists/i)).toBeInTheDocument();
    expect(createAnecdoteMock).not.toHaveBeenCalled();
  });

  it('?question=<slug> pre-selects question by matching slug to title', async () => {
    mockContent([]);
    renderNew('/behavioral/anecdotes/new?question=tell-me-about-a-conflict');
    await waitFor(() => screen.getByLabelText('Title'));
    const conflictBtn = screen.getByRole('button', { name: /Tell me about a conflict/i });
    expect(conflictBtn).toBeInTheDocument();
  });

  it('in edit mode, pre-fills from fetched anecdote', async () => {
    mockContent([existingAnecdote]);
    renderNew('/behavioral/anecdotes/existing-anecdote/edit');
    await waitFor(() => screen.getByDisplayValue('Existing anecdote'));
    expect((screen.getByLabelText('Title') as HTMLInputElement).value).toBe('Existing anecdote');
    expect(screen.getByLabelText('Description')).toBeInTheDocument();
    expect((screen.getByLabelText('Description') as HTMLTextAreaElement).value).toBe('A description here');
    expect((screen.getByLabelText('Notes') as HTMLTextAreaElement).value).toBe('Some notes');
  });

  it('Delete button in edit mode calls deleteAnecdote and navigates back', async () => {
    mockContent([existingAnecdote]);
    deleteAnecdoteMock.mockResolvedValue(undefined);
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    renderNew('/behavioral/anecdotes/existing-anecdote/edit');
    await waitFor(() => screen.getByDisplayValue('Existing anecdote'));
    fireEvent.click(screen.getByRole('button', { name: /Delete anecdote/i }));
    await waitFor(() => expect(deleteAnecdoteMock).toHaveBeenCalled());
    expect(deleteAnecdoteMock.mock.calls[0][0]).toBe('5');
    expect(navigateMock).toHaveBeenCalledWith(-1);
  });

  it('blocks editing an anecdote to a title whose slug matches another anecdote', async () => {
    mockContent([existingAnecdote, duplicateSlugAnecdote]);
    renderNew('/behavioral/anecdotes/existing-anecdote/edit');
    await waitFor(() => screen.getByDisplayValue('Existing anecdote'));
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'API-test' } });
    fireEvent.click(screen.getByRole('button', { name: /Save anecdote/i }));
    expect(await screen.findByText(/already exists/i)).toBeInTheDocument();
    expect(updateAnecdoteMock).not.toHaveBeenCalled();
  });

  it('Cancel button navigates back without saving', async () => {
    mockContent([]);
    renderNew();
    await waitFor(() => screen.getByLabelText('Title'));
    fireEvent.click(screen.getByRole('button', { name: /^Cancel$/i }));
    expect(navigateMock).toHaveBeenCalledWith(-1);
    expect(createAnecdoteMock).not.toHaveBeenCalled();
  });
});
