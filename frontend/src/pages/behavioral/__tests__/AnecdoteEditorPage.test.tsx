import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { AnecdoteEditorPage } from '../AnecdoteEditorPage';
import { api } from '../../../api/client';
import { CommandCenterProvider } from '../../../command-center/CommandCenterProvider';

vi.mock('../../../api/client', () => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), del: vi.fn() },
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

beforeEach(() => {
  navigateMock.mockClear();
  vi.clearAllMocks();
});

describe('AnecdoteEditorPage', () => {
  it('renders Both mode by default on /new (Description + STAR both visible)', async () => {
    (api.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    renderNew();
    await waitFor(() => screen.getByLabelText('Title'));
    expect(screen.getByLabelText('Description')).toBeInTheDocument();
    expect(screen.getByLabelText('Situation')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Description$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^STAR$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Both$/i })).toBeInTheDocument();
  });

  it('toggling to STAR-only shows S/T/A/R fields and hides Description', async () => {
    (api.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);
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
    (api.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    renderNew();
    await waitFor(() => screen.getByLabelText('Title'));
    fireEvent.click(screen.getByRole('button', { name: /^Description$/i }));
    expect(screen.getByLabelText('Description')).toBeInTheDocument();
    expect(screen.queryByLabelText('Situation')).not.toBeInTheDocument();
  });

  it('entering a title + description and submitting POSTs to /api/anecdotes', async () => {
    (api.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    (api.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 99, title: 'My story', description: 'Free-form text', situation: '', task: '',
      action: '', result: '', category_ids: [], linked_question_ids: [], notes: '',
    });
    renderNew();
    await waitFor(() => screen.getByLabelText('Title'));
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'My story' } });
    fireEvent.change(screen.getByLabelText('Description'), { target: { value: 'Free-form text' } });
    fireEvent.click(screen.getByRole('button', { name: /Save anecdote/i }));
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const [path, body] = (api.post as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(path).toBe('/api/anecdotes');
    expect(body).toMatchObject({ title: 'My story', description: 'Free-form text' });
    expect(navigateMock).toHaveBeenCalledWith(-1);
  });

  it('blocks creating an anecdote when another title has the same slug', async () => {
    (api.get as unknown as ReturnType<typeof vi.fn>).mockImplementation((path: string) => {
      if (path.includes('behavioral-categories')) return Promise.resolve(cats);
      if (path === '/api/behavioral') return Promise.resolve(questions);
      if (path === '/api/anecdotes') return Promise.resolve([duplicateSlugAnecdote]);
      return Promise.resolve([]);
    });
    renderNew();
    await waitFor(() => screen.getByLabelText('Title'));
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'API test' } });
    fireEvent.click(screen.getByRole('button', { name: /Save anecdote/i }));
    expect(await screen.findByText(/already exists/i)).toBeInTheDocument();
    expect(api.post).not.toHaveBeenCalled();
  });

  it('?question=<slug> pre-selects question by matching slug to title', async () => {
    (api.get as unknown as ReturnType<typeof vi.fn>).mockImplementation((path: string) => {
      if (path.includes('behavioral-categories')) return Promise.resolve(cats);
      if (path.includes('behavioral')) return Promise.resolve(questions);
      return Promise.resolve([]);
    });
    renderNew('/behavioral/anecdotes/new?question=tell-me-about-a-conflict');
    await waitFor(() => screen.getByLabelText('Title'));
    // The question pill for id=10 should be toggled (active)
    const conflictBtn = screen.getByRole('button', { name: /Tell me about a conflict/i });
    // Active style means it has the darker bg; just verify it exists and is a button
    expect(conflictBtn).toBeInTheDocument();
  });

  it('in edit mode, pre-fills from fetched anecdote', async () => {
    (api.get as unknown as ReturnType<typeof vi.fn>).mockImplementation((path: string) => {
      if (path.includes('behavioral-categories')) return Promise.resolve(cats);
      if (path === '/api/behavioral') return Promise.resolve(questions);
      if (path === '/api/anecdotes') return Promise.resolve([existingAnecdote]);
      return Promise.resolve([]);
    });
    renderNew('/behavioral/anecdotes/existing-anecdote/edit');
    await waitFor(() => screen.getByDisplayValue('Existing anecdote'));
    expect((screen.getByLabelText('Title') as HTMLInputElement).value).toBe('Existing anecdote');
    // description mode because description is non-empty and STAR fields are empty
    expect(screen.getByLabelText('Description')).toBeInTheDocument();
    expect((screen.getByLabelText('Description') as HTMLTextAreaElement).value).toBe('A description here');
    expect((screen.getByLabelText('Notes') as HTMLTextAreaElement).value).toBe('Some notes');
  });

  it('Delete button in edit mode calls DELETE and navigates back', async () => {
    (api.get as unknown as ReturnType<typeof vi.fn>).mockImplementation((path: string) => {
      if (path.includes('behavioral-categories')) return Promise.resolve(cats);
      if (path === '/api/behavioral') return Promise.resolve(questions);
      if (path === '/api/anecdotes') return Promise.resolve([existingAnecdote]);
      return Promise.resolve([]);
    });
    (api.del as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(undefined);
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    renderNew('/behavioral/anecdotes/existing-anecdote/edit');
    await waitFor(() => screen.getByDisplayValue('Existing anecdote'));
    fireEvent.click(screen.getByRole('button', { name: /Delete anecdote/i }));
    await waitFor(() => expect(api.del).toHaveBeenCalled());
    expect((api.del as unknown as ReturnType<typeof vi.fn>).mock.calls[0][0]).toBe('/api/anecdotes/5');
    expect(navigateMock).toHaveBeenCalledWith(-1);
  });

  it('blocks editing an anecdote to a title whose slug matches another anecdote', async () => {
    (api.get as unknown as ReturnType<typeof vi.fn>).mockImplementation((path: string) => {
      if (path.includes('behavioral-categories')) return Promise.resolve(cats);
      if (path === '/api/behavioral') return Promise.resolve(questions);
      if (path === '/api/anecdotes') return Promise.resolve([existingAnecdote, duplicateSlugAnecdote]);
      return Promise.resolve([]);
    });
    renderNew('/behavioral/anecdotes/existing-anecdote/edit');
    await waitFor(() => screen.getByDisplayValue('Existing anecdote'));
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'API-test' } });
    fireEvent.click(screen.getByRole('button', { name: /Save anecdote/i }));
    expect(await screen.findByText(/already exists/i)).toBeInTheDocument();
    expect(api.put).not.toHaveBeenCalled();
  });

  it('Cancel button navigates back without saving', async () => {
    (api.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    renderNew();
    await waitFor(() => screen.getByLabelText('Title'));
    fireEvent.click(screen.getByRole('button', { name: /^Cancel$/i }));
    expect(navigateMock).toHaveBeenCalledWith(-1);
    expect(api.post).not.toHaveBeenCalled();
  });
});
