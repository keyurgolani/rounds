import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { TestCaseCard } from '../TestCaseCard';

describe('TestCaseCard', () => {
  const baseProps = {
    index: 2,
    testCase: {
      input: { nums: [2, 7], target: 9 },
      expected: [0, 1],
      description: 'Pair at the start',
      tags: ['basic', 'edge'],
    },
    onEvaluate: vi.fn(),
    open: true,
    onOpenChange: vi.fn(),
  };

  it('renders description, tag pills, and input/expected preview', () => {
    render(<TestCaseCard {...baseProps} />);
    expect(screen.getByText('Pair at the start')).toBeInTheDocument();
    expect(screen.getByText('basic')).toBeInTheDocument();
    expect(screen.getByText('edge')).toBeInTheDocument();
    expect(screen.getByText(/Input/)).toBeInTheDocument();
    expect(screen.getByText(/Expected/)).toBeInTheDocument();
  });

  it('shows not-run status by default', () => {
    render(<TestCaseCard {...baseProps} />);
    expect(screen.getByLabelText('not run')).toBeInTheDocument();
  });

  it('shows passed status when given a passing result', () => {
    render(
      <TestCaseCard
        {...baseProps}
        result={{
          index: 2, passed: true, description: 'Pair at the start', tags: ['basic'],
          output: [0, 1], expected: [0, 1], error: null, duration_ms: 2,
        }}
      />,
    );
    expect(screen.getByLabelText('passed')).toBeInTheDocument();
    expect(screen.getByText(/2ms/)).toBeInTheDocument();
  });

  it('shows failed status and output when given a failing result', () => {
    render(
      <TestCaseCard
        {...baseProps}
        result={{
          index: 2, passed: false, description: 'Pair at the start', tags: ['basic'],
          output: [1, 2], expected: [0, 1], error: null, duration_ms: 4,
        }}
      />,
    );
    expect(screen.getByLabelText('failed')).toBeInTheDocument();
    expect(screen.getByText(/Output/)).toBeInTheDocument();
  });

  it('invokes onEvaluate with the card index when play is clicked', () => {
    const onEvaluate = vi.fn();
    render(<TestCaseCard {...baseProps} onEvaluate={onEvaluate} />);
    fireEvent.click(screen.getByRole('button', { name: /evaluate this test/i }));
    expect(onEvaluate).toHaveBeenCalledWith(2);
  });

  it('respects controlled open=false by hiding input/expected body', () => {
    render(<TestCaseCard {...baseProps} open={false} />);
    expect(screen.queryByText(/Input/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Expected/)).not.toBeInTheDocument();
  });

  it('calls onOpenChange when the header is clicked', () => {
    const onOpenChange = vi.fn();
    render(<TestCaseCard {...baseProps} open={true} onOpenChange={onOpenChange} />);
    // Click the header button (the outer toggle button)
    const headerBtn = screen.getAllByRole('button')[0];
    fireEvent.click(headerBtn);
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
