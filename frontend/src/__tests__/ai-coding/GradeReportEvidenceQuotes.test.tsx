import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import GradeReport from '../../pages/ai-coding/GradeReport';

describe('GradeReport evidence_quotes rendering', () => {
  const baseProps = {
    testResults: [{ passed: true, passed_count: 1, failed_count: 0, stdout: '', error: null }],
    rubric: { items: [{ id: 'q1', label: 'Q1', weight: 1, prompt: 'p' }] },
  };

  it('renders nothing when evidence_quotes is missing or empty', () => {
    render(
      <GradeReport
        {...baseProps}
        rubricReview={{
          items: [{ id: 'q1', score: 0.8, evidence: 'ok', suggestions: [], evidence_quotes: [] }],
          total: 0.8,
        }}
      />,
    );
    expect(screen.queryByText(/app\.py:/i)).toBeNull();
  });

  it('renders file:line refs and quote blockquotes', () => {
    render(
      <GradeReport
        {...baseProps}
        rubricReview={{
          items: [
            {
              id: 'q1',
              score: 0.8,
              evidence: 'ok',
              suggestions: [],
              evidence_quotes: [
                { file: 'app.py', line: 12, quote: 'return result' },
                { file: 'tests/test_app.py', line: 5, quote: 'assert handle(...)' },
              ],
            },
          ],
          total: 0.8,
        }}
      />,
    );
    expect(screen.getByText('app.py:12')).toBeInTheDocument();
    expect(screen.getByText('return result')).toBeInTheDocument();
    expect(screen.getByText('tests/test_app.py:5')).toBeInTheDocument();
    expect(screen.getByText('assert handle(...)')).toBeInTheDocument();
  });
});
