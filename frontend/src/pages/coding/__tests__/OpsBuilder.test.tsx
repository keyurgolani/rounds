import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { OpsBuilder } from '../builders/OpsBuilder';
import type { Entry } from '../types';

const lru: Extract<Entry, { kind: 'class_ops' }> = {
  kind: 'class_ops',
  class: 'LRUCache',
  constructor: { params: [{ name: 'capacity', type: 'int' }] },
  methods: [
    { name: 'get', params: [{ name: 'key', type: 'int' }], returns: 'int' },
    {
      name: 'put',
      params: [
        { name: 'key', type: 'int' },
        { name: 'value', type: 'int' },
      ],
      returns: 'any',
    },
  ],
};

describe('OpsBuilder', () => {
  it('renders constructor row first with class name', () => {
    render(
      <OpsBuilder
        entry={lru}
        value={{ ops: ['LRUCache'], args: [[2]] }}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByText('new LRUCache')).toBeInTheDocument();
  });

  it('appends an op with the first method as default', () => {
    const onChange = vi.fn();
    render(
      <OpsBuilder
        entry={lru}
        value={{ ops: ['LRUCache'], args: [[2]] }}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByLabelText('Append op'));
    expect(onChange).toHaveBeenCalledWith({
      ops: ['LRUCache', 'get'],
      args: [[2], ['']],
    });
  });

  it('changes op via dropdown and resets args', () => {
    const onChange = vi.fn();
    render(
      <OpsBuilder
        entry={lru}
        value={{ ops: ['LRUCache', 'get'], args: [[2], [42]] }}
        onChange={onChange}
      />,
    );
    fireEvent.change(screen.getByLabelText('Method for op 2'), {
      target: { value: 'put' },
    });
    expect(onChange).toHaveBeenCalledWith({
      ops: ['LRUCache', 'put'],
      args: [[2], ['', '']],
    });
  });

  it('updates an arg with int coercion', () => {
    const onChange = vi.fn();
    render(
      <OpsBuilder
        entry={lru}
        value={{ ops: ['LRUCache', 'get'], args: [[2], ['']] }}
        onChange={onChange}
      />,
    );
    fireEvent.change(screen.getByLabelText('get arg key'), { target: { value: '7' } });
    expect(onChange).toHaveBeenCalledWith({
      ops: ['LRUCache', 'get'],
      args: [[2], [7]],
    });
  });

  it('removes a non-constructor op', () => {
    const onChange = vi.fn();
    render(
      <OpsBuilder
        entry={lru}
        value={{ ops: ['LRUCache', 'get', 'put'], args: [[2], [1], [1, 1]] }}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByLabelText('Remove op 2'));
    expect(onChange).toHaveBeenCalledWith({
      ops: ['LRUCache', 'put'],
      args: [[2], [1, 1]],
    });
  });
});
