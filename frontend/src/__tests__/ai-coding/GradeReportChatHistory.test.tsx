import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import GradeReport from '../../pages/ai-coding/GradeReport';

describe('GradeReport chat history', () => {
  const baseProps = {
    testResults: [
      {
        passed: true,
        passed_count: 1,
        failed_count: 0,
        stdout: '',
        error: null,
      },
    ],
    rubric: { items: [] },
    rubricReview: { items: [], total: 0, skipped: false as const },
  };

  it('does not render the chat history section when aiChats is empty', () => {
    render(<GradeReport {...baseProps} aiChats={[]} />);
    expect(screen.queryByText(/AI chat history/i)).toBeNull();
  });

  it('groups messages by checkpoint and renders content', () => {
    const aiChats = [
      { checkpoint: 0, role: 'user', content: 'Question A', ts: 1 },
      { checkpoint: 0, role: 'assistant', content: 'Answer A', ts: 2 },
      { checkpoint: 1, role: 'user', content: 'Question B', ts: 3 },
    ];
    render(<GradeReport {...baseProps} aiChats={aiChats} />);
    expect(screen.getByText(/AI chat history/i)).toBeInTheDocument();
    expect(screen.getByText(/Checkpoint 1 — 2 messages/)).toBeInTheDocument();
    expect(screen.getByText(/Checkpoint 2 — 1 message/)).toBeInTheDocument();
    expect(screen.getByText('Question A')).toBeInTheDocument();
    expect(screen.getByText('Answer A')).toBeInTheDocument();
    expect(screen.getByText('Question B')).toBeInTheDocument();
  });

  it('preserves message newlines via whitespace pre-wrap', () => {
    const aiChats = [
      { checkpoint: 0, role: 'user', content: 'Line one\nLine two', ts: 1 },
    ];
    render(<GradeReport {...baseProps} aiChats={aiChats} />);
    // Match the multi-line content; testing-library normalizes whitespace
    // for getByText, so we use a function matcher to find the literal.
    expect(
      screen.getByText((_, node) => (node?.textContent ?? '') === 'Line one\nLine two')
    ).toBeInTheDocument();
  });
});
