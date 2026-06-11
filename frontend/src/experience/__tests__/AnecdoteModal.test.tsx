import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import AnecdoteModal from '../AnecdoteModal';
import type { ExperienceAnecdote } from '../experienceApi';

vi.mock('../experienceApi', () => ({
  updateAnecdote: vi.fn(async (_id, p) => p),
  deleteAnecdote: vi.fn(async () => {}),
  createBullet: vi.fn(async () => ({ id: 'blt1', title: 'b', impact: '', category: '', date: '2026-01-01', tags: [] })),
}));
vi.mock('../connectionApi', () => ({ createConnection: vi.fn(async () => ({})) }));
vi.mock('../../content/api', () => ({
  listBehavioralCategories: vi.fn(async () => [{ id: 'c1', name: 'Ownership', color: '#7928ca', icon: '◆' }]),
  listBehavioralQuestions: vi.fn(async () => [{ id: 'q1', title: 'Tell me about a conflict' }]),
}));

const anecdote: ExperienceAnecdote = {
  id: 'a1', title: 'Scaled the Pipeline', situation: 's', task: 't', action: 'a', result: 'r',
  impact: 'i', company: 'Acme', project: 'P', date: '2026-01-01', tags: [],
  description: '', category_ids: [], linked_question_ids: [], notes: '',
};

describe('AnecdoteModal ported fields', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders the category options and toggles one (commits category_ids)', async () => {
    const { updateAnecdote } = await import('../experienceApi');
    render(<AnecdoteModal item={anecdote} open onClose={() => {}} onSaved={() => {}} />);
    const cat = await screen.findByRole('button', { name: 'Ownership' });
    fireEvent.click(cat);
    await waitFor(() =>
      expect(updateAnecdote).toHaveBeenCalledWith('a1', expect.objectContaining({ category_ids: ['c1'] })),
    );
  });

  it('save-as-bullet creates an experience bullet linked to the anecdote', async () => {
    const { createBullet } = await import('../experienceApi');
    const { createConnection } = await import('../connectionApi');
    render(<AnecdoteModal item={anecdote} open onClose={() => {}} onSaved={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /save as bullet/i }));
    fireEvent.click(await screen.findByRole('button', { name: /^save bullet$/i }));
    await waitFor(() => expect(createBullet).toHaveBeenCalled());
    await waitFor(() =>
      expect(createConnection).toHaveBeenCalledWith('anecdote', 'a1', 'bullet', 'blt1'),
    );
  });
});
