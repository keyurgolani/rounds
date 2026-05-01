import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ListBuilder } from '../builders/ListBuilder';

describe('ListBuilder', () => {
  it('renders existing items as chips', () => {
    render(<ListBuilder value={[1, 2, 3]} onChange={vi.fn()} itemType="int" />);
    expect((screen.getByLabelText('Item 1') as HTMLInputElement).value).toBe('1');
    expect((screen.getByLabelText('Item 3') as HTMLInputElement).value).toBe('3');
  });

  it('appends an int item via Enter key', () => {
    const onChange = vi.fn();
    render(<ListBuilder value={[1, 2]} onChange={onChange} itemType="int" />);
    const newField = screen.getByLabelText('New item') as HTMLInputElement;
    fireEvent.change(newField, { target: { value: '7' } });
    fireEvent.keyDown(newField, { key: 'Enter' });
    expect(onChange).toHaveBeenCalledWith([1, 2, 7]);
  });

  it('appends a string item', () => {
    const onChange = vi.fn();
    render(<ListBuilder value={['a']} onChange={onChange} itemType="string" />);
    const newField = screen.getByLabelText('New item') as HTMLInputElement;
    fireEvent.change(newField, { target: { value: 'b' } });
    fireEvent.click(screen.getByLabelText('Append item'));
    expect(onChange).toHaveBeenCalledWith(['a', 'b']);
  });

  it('removes an item', () => {
    const onChange = vi.fn();
    render(<ListBuilder value={[1, 2, 3]} onChange={onChange} itemType="int" />);
    fireEvent.click(screen.getByLabelText('Remove item 2'));
    expect(onChange).toHaveBeenCalledWith([1, 3]);
  });

  it('edits an item in place (with int coercion)', () => {
    const onChange = vi.fn();
    render(<ListBuilder value={[1, 2]} onChange={onChange} itemType="int" />);
    fireEvent.change(screen.getByLabelText('Item 1'), { target: { value: '42' } });
    expect(onChange).toHaveBeenCalledWith([42, 2]);
  });
});
