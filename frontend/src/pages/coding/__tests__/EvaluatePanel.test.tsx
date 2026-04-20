import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { EvaluatePanel } from '../EvaluatePanel';
import type { TestCase, EvaluateFilter } from '../types';

const cases: TestCase[] = [
  { input: { x: 1 }, expected: 1, description: 'alpha', tags: ['basic'] },
  { input: { x: 2 }, expected: 2, description: 'beta', tags: ['edge'] },
  { input: { x: 3 }, expected: 3, description: 'gamma', tags: ['basic', 'tricky'] },
  { input: { x: 4 }, expected: 4, description: 'delta', tags: ['large'] },
];

describe('EvaluatePanel', () => {
  it('renders a filter chip per unique tag with correct counts', () => {
    render(<EvaluatePanel testCases={cases} running={false} onEvaluate={vi.fn()} />);
    expect(screen.getByText(/basic.*2/)).toBeInTheDocument();
    expect(screen.getByText(/edge.*1/)).toBeInTheDocument();
    expect(screen.getByText(/tricky.*1/)).toBeInTheDocument();
    expect(screen.getByText(/large.*1/)).toBeInTheDocument();
  });

  it('renders all test cards by default', () => {
    render(<EvaluatePanel testCases={cases} running={false} onEvaluate={vi.fn()} />);
    expect(screen.getByText('alpha')).toBeInTheDocument();
    expect(screen.getByText('beta')).toBeInTheDocument();
    expect(screen.getByText('gamma')).toBeInTheDocument();
    expect(screen.getByText('delta')).toBeInTheDocument();
  });

  it('clicking a tag chip filters the visible list', () => {
    render(<EvaluatePanel testCases={cases} running={false} onEvaluate={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /filter tag edge/i }));
    expect(screen.queryByText('alpha')).not.toBeInTheDocument();
    expect(screen.getByText('beta')).toBeInTheDocument();
    expect(screen.queryByText('gamma')).not.toBeInTheDocument();
  });

  it('"Evaluate all" triggers onEvaluate with no filter', () => {
    const onEvaluate = vi.fn();
    render(<EvaluatePanel testCases={cases} running={false} onEvaluate={onEvaluate} />);
    fireEvent.click(screen.getByRole('button', { name: /Evaluate all/i }));
    expect(onEvaluate).toHaveBeenCalledWith(undefined);
  });

  it('per-tag evaluate button triggers onEvaluate with {tags: [tag]}', () => {
    const onEvaluate = vi.fn();
    render(<EvaluatePanel testCases={cases} running={false} onEvaluate={onEvaluate} />);
    fireEvent.click(screen.getByRole('button', { name: /evaluate tag tricky/i }));
    const filter = onEvaluate.mock.calls[0][0] as EvaluateFilter;
    expect(filter).toEqual({ tags: ['tricky'] });
  });

  it('per-test play button triggers onEvaluate with {indices: [i]}', () => {
    const onEvaluate = vi.fn();
    render(<EvaluatePanel testCases={cases} running={false} onEvaluate={onEvaluate} />);
    // First expand all cards so we can find the evaluate buttons
    fireEvent.click(screen.getByRole('button', { name: /expand all/i }));
    const cards = screen.getAllByRole('button', { name: /evaluate this test/i });
    fireEvent.click(cards[1]);
    expect(onEvaluate).toHaveBeenCalledWith({ indices: [1] });
  });

  it('summary counts update from results', () => {
    render(
      <EvaluatePanel
        testCases={cases}
        running={false}
        onEvaluate={vi.fn()}
        results={[
          { index: 0, passed: true, description: 'a', tags: ['basic'], output: 1, expected: 1, error: null, duration_ms: 1 },
          { index: 1, passed: false, description: 'b', tags: ['edge'], output: 0, expected: 2, error: null, duration_ms: 1 },
        ]}
      />,
    );
    expect(screen.getByText(/1 passed/)).toBeInTheDocument();
    expect(screen.getByText(/1 failed/)).toBeInTheDocument();
  });

  it('test cases are collapsed by default', () => {
    render(<EvaluatePanel testCases={cases} running={false} onEvaluate={vi.fn()} />);
    expect(screen.queryByText(/^Input$/)).not.toBeInTheDocument();
    expect(screen.queryByText(/^Expected$/)).not.toBeInTheDocument();
  });

  it('"Expand all" button opens every test case', () => {
    render(<EvaluatePanel testCases={cases} running={false} onEvaluate={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /expand all/i }));
    // Each of 4 cards shows an Input label
    const inputLabels = screen.getAllByText(/^Input$/);
    expect(inputLabels).toHaveLength(4);
  });

  it('"Collapse all" button re-collapses all cases', () => {
    render(<EvaluatePanel testCases={cases} running={false} onEvaluate={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /expand all/i }));
    fireEvent.click(screen.getByRole('button', { name: /collapse all/i }));
    expect(screen.queryByText(/^Input$/)).not.toBeInTheDocument();
    expect(screen.queryByText(/^Expected$/)).not.toBeInTheDocument();
  });
});
