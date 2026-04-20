import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { RunPanel } from '../RunPanel';
import type { TestCase, CodeRunResult } from '../types';

const samples: TestCase[] = [
  { input: { nums: [2, 7], target: 9 }, expected: [0, 1], description: 'Basic', tags: ['basic'] },
  { input: { nums: [3, 2, 4], target: 6 }, expected: [1, 2], description: 'Mid', tags: ['edge'] },
];

describe('RunPanel', () => {
  it('pre-fills textarea with the first sample input (JSON)', () => {
    render(<RunPanel samples={samples} running={false} onRun={vi.fn()} />);
    const ta = screen.getByLabelText('Input (JSON)') as HTMLTextAreaElement;
    expect(ta.value).toContain('"nums"');
    // Input is pretty-printed — the values are present on their own lines.
    expect(ta.value).toMatch(/2/);
    expect(ta.value).toMatch(/7/);
  });

  it('shows parse error for invalid JSON and does not call onRun', () => {
    const onRun = vi.fn();
    render(<RunPanel samples={samples} running={false} onRun={onRun} />);
    const ta = screen.getByLabelText('Input (JSON)') as HTMLTextAreaElement;
    fireEvent.change(ta, { target: { value: '{not json' } });
    fireEvent.click(screen.getByRole('button', { name: /Run with this input/i }));
    expect(screen.getByText(/must be valid JSON/i)).toBeInTheDocument();
    expect(onRun).not.toHaveBeenCalled();
  });

  it('calls onRun with parsed JSON when valid', () => {
    const onRun = vi.fn();
    render(<RunPanel samples={samples} running={false} onRun={onRun} />);
    fireEvent.click(screen.getByRole('button', { name: /Run with this input/i }));
    expect(onRun).toHaveBeenCalledWith({ nums: [2, 7], target: 9 });
  });

  it('renders stdout / stderr / return value sections from the result', () => {
    const result: CodeRunResult = {
      stdout: 'hello\n',
      stderr: 'oops\n',
      return_value: [0, 1],
      error: null,
      duration_ms: 3,
      truncated: false,
    };
    render(<RunPanel samples={samples} running={false} onRun={vi.fn()} result={result} />);
    expect(screen.getByText(/hello/)).toBeInTheDocument();
    expect(screen.getByText(/oops/)).toBeInTheDocument();
    // Return value is pretty-printed — look for the array contents.
    expect(screen.getByText(/0,\s*1/)).toBeInTheDocument();
  });

  it('switches to the selected sample when a sample chip is clicked', () => {
    render(<RunPanel samples={samples} running={false} onRun={vi.fn()} />);
    const ta = screen.getByLabelText('Input (JSON)') as HTMLTextAreaElement;
    fireEvent.click(screen.getByRole('button', { name: /Sample 02/i }));
    expect(ta.value).toMatch(/3/);
    expect(ta.value).toMatch(/"target":\s*6/);
  });
});
