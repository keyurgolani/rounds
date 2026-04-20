import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { AnecdoteCard } from '../AnecdoteCard';
import type { Anecdote, BehavioralCategoryLite } from '../types';

const cats: BehavioralCategoryLite[] = [
  { id: 1, name: 'Ownership', color: '#7928ca', icon: '◆' },
  { id: 2, name: 'Empathy', color: '#0072f5', icon: '○' },
];

const a: Anecdote = {
  id: 10,
  title: 'Reorg conflict with marketing',
  description: '',
  situation: 'Mid-Q3 my team was asked to integrate with a marketing platform that was out of scope.',
  task: 'Resolve the disagreement without losing the relationship.',
  action: 'I scheduled a 1:1 with their lead and surfaced the constraints we both faced.',
  result: 'We landed on a phased plan; both teams shipped on time.',
  category_ids: [1, 2],
  linked_question_ids: [3, 4, 7],
  notes: '',
};

describe('AnecdoteCard', () => {
  it('renders title and situation preview', () => {
    render(<AnecdoteCard anecdote={a} categories={cats} onEdit={vi.fn()} />);
    expect(screen.getByText('Reorg conflict with marketing')).toBeInTheDocument();
    expect(screen.getByText(/Mid-Q3 my team was asked/)).toBeInTheDocument();
  });

  it('renders category pills using category names', () => {
    render(<AnecdoteCard anecdote={a} categories={cats} onEdit={vi.fn()} />);
    expect(screen.getByText('Ownership')).toBeInTheDocument();
    expect(screen.getByText('Empathy')).toBeInTheDocument();
  });

  it('renders the linked-question count', () => {
    render(<AnecdoteCard anecdote={a} categories={cats} onEdit={vi.fn()} />);
    expect(screen.getByText(/3 questions/)).toBeInTheDocument();
  });

  it('clicking the card calls onEdit with the anecdote', () => {
    const onEdit = vi.fn();
    render(<AnecdoteCard anecdote={a} categories={cats} onEdit={onEdit} />);
    fireEvent.click(screen.getByRole('button', { name: /Reorg conflict/ }));
    expect(onEdit).toHaveBeenCalledWith(a);
  });

  it('clicking delete calls onDelete with the id and stops card-click propagation', () => {
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    render(<AnecdoteCard anecdote={a} categories={cats} onEdit={onEdit} onDelete={onDelete} />);
    fireEvent.click(screen.getByRole('button', { name: /delete/i }));
    expect(onDelete).toHaveBeenCalledWith(10);
    expect(onEdit).not.toHaveBeenCalled();
  });
});
