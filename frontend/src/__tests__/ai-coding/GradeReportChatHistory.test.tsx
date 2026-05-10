import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

// AIPatchView pulls in Monaco's DiffEditor + ThemeProvider + AuthProvider
// for its own deps. The chat-history test only cares that the diff card
// is rendered (instead of raw JSON), so stub it to a marker element.
vi.mock('../../components/ai/AIPatchView', () => ({
  default: ({ patches, applied }: { patches: unknown[]; applied?: boolean }) => (
    <div data-testid="patch-view" data-applied={applied ? 'true' : 'false'}>
      {applied ? 'Applied' : 'Proposed'} ({patches.length})
    </div>
  ),
}));

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

  it('renders an AI patch as an Applied diff card, not raw JSON', () => {
    // Patch contents include a `[` character — the regression we're
    // guarding against was using lastIndexOf('[') which would land
    // INSIDE the contents string and fail to parse, causing the raw
    // JSON to render as plain text.
    const json = JSON.stringify([
      {
        file: 'cart.py',
        patch_kind: 'replace',
        contents: 'def total(cart):\n    return sum(item[1] for item in cart)\n',
      },
    ]);
    const aiChats = [
      { checkpoint: 0, role: 'user', content: 'fix it', ts: 1 },
      { checkpoint: 0, role: 'assistant', content: json, ts: 2 },
    ];
    render(<GradeReport {...baseProps} aiChats={aiChats} files={{}} />);
    // The "Applied" badge from AIPatchView should be visible.
    expect(screen.getByText(/Applied/i)).toBeInTheDocument();
    // The raw JSON text shouldn't appear anywhere as a rendered string.
    expect(screen.queryByText(/"patch_kind"/)).toBeNull();
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
