import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { CasesTab } from '../CasesTab';
import type { TestCase, Entry } from '../types';

const fnEntry: Entry = {
  kind: 'function',
  name: 'add',
  params: [
    { name: 'a', type: 'int' },
    { name: 'b', type: 'int' },
  ],
  returns: 'int',
};

const samples: TestCase[] = [
  { input: { a: 1, b: 2 }, expected: 3 },
  { input: { a: 10, b: 20 }, expected: 30 },
];

describe('CasesTab', () => {
  it('renders one ParamField per param for function kind', () => {
    render(
      <CasesTab entry={fnEntry} samples={samples} running={false} onRun={vi.fn()} />,
    );
    expect(screen.getByLabelText('a: int')).toBeInTheDocument();
    expect(screen.getByLabelText('b: int')).toBeInTheDocument();
  });

  it('preserves per-chip session edits', () => {
    render(
      <CasesTab entry={fnEntry} samples={samples} running={false} onRun={vi.fn()} />,
    );
    const aField = screen.getByLabelText('a: int') as HTMLInputElement;
    expect(aField.value).toBe('1');
    fireEvent.change(aField, { target: { value: '99' } });
    fireEvent.click(screen.getByRole('button', { name: /Case 02/i }));
    expect((screen.getByLabelText('a: int') as HTMLInputElement).value).toBe('10');
    fireEvent.click(screen.getByRole('button', { name: /Case 01/i }));
    expect((screen.getByLabelText('a: int') as HTMLInputElement).value).toBe('99');
  });

  it('Run sends the edited input', () => {
    const onRun = vi.fn();
    render(
      <CasesTab entry={fnEntry} samples={samples} running={false} onRun={onRun} />,
    );
    fireEvent.change(screen.getByLabelText('a: int'), { target: { value: '5' } });
    fireEvent.click(screen.getByRole('button', { name: /^Run$/ }));
    expect(onRun).toHaveBeenCalledWith({ a: 5, b: 2 });
  });
});
