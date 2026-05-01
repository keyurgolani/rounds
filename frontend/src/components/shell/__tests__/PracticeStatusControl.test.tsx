import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import PracticeStatusControl from '../PracticeStatusControl';

describe('PracticeStatusControl (compact)', () => {
  it('renders one cycle button reflecting current status', () => {
    render(<PracticeStatusControl status="todo" onChange={vi.fn()} compact />);
    const btn = screen.getByRole('button');
    expect(btn).toHaveAttribute('title', expect.stringMatching(/not started/i));
  });

  it('cycles todo → in-progress → mastered → todo on click', () => {
    const onChange = vi.fn();
    const { rerender } = render(
      <PracticeStatusControl status="todo" onChange={onChange} compact />,
    );
    fireEvent.click(screen.getByRole('button'));
    expect(onChange).toHaveBeenLastCalledWith('in-progress');

    rerender(
      <PracticeStatusControl status="in-progress" onChange={onChange} compact />,
    );
    fireEvent.click(screen.getByRole('button'));
    expect(onChange).toHaveBeenLastCalledWith('mastered');

    rerender(
      <PracticeStatusControl status="mastered" onChange={onChange} compact />,
    );
    fireEvent.click(screen.getByRole('button'));
    expect(onChange).toHaveBeenLastCalledWith('todo');
  });

  it('non-compact still renders the three-pill row', () => {
    render(<PracticeStatusControl status="todo" onChange={vi.fn()} />);
    expect(screen.getByText(/not started/i)).toBeInTheDocument();
    expect(screen.getByText(/practicing/i)).toBeInTheDocument();
    expect(screen.getByText(/mastered/i)).toBeInTheDocument();
  });
});
