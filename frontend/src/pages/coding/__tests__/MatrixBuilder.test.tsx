import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MatrixBuilder } from '../builders/MatrixBuilder';

describe('MatrixBuilder', () => {
  it('renders cells in a grid', () => {
    render(<MatrixBuilder value={[[1, 2], [3, 4]]} onChange={vi.fn()} />);
    expect((screen.getByLabelText('Cell 1,1') as HTMLInputElement).value).toBe('1');
    expect((screen.getByLabelText('Cell 2,2') as HTMLInputElement).value).toBe('4');
  });

  it('updates a cell with int coercion', () => {
    const onChange = vi.fn();
    render(<MatrixBuilder value={[[1, 2], [3, 4]]} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText('Cell 1,2'), { target: { value: '99' } });
    expect(onChange).toHaveBeenCalledWith([[1, 99], [3, 4]]);
  });

  it('appends a row of correct width', () => {
    const onChange = vi.fn();
    render(<MatrixBuilder value={[[1, 2, 3]]} onChange={onChange} />);
    fireEvent.click(screen.getByLabelText('Add row'));
    expect(onChange).toHaveBeenCalledWith([[1, 2, 3], [0, 0, 0]]);
  });

  it('appends a column to every row', () => {
    const onChange = vi.fn();
    render(<MatrixBuilder value={[[1], [2]]} onChange={onChange} />);
    fireEvent.click(screen.getByLabelText('Add column'));
    expect(onChange).toHaveBeenCalledWith([[1, 0], [2, 0]]);
  });
});
