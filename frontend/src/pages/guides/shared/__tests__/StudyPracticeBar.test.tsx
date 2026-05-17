import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import StudyPracticeBar from '../StudyPracticeBar';

// Test file lives at frontend/src/pages/guides/shared/__tests__/, so up 4
// hops lands at frontend/src/, and up 3 hops at frontend/src/pages/.
vi.mock('../../../../content/api', () => ({
  listSystemDesignQuestions: vi.fn(),
  listCodingQuestions: vi.fn(),
  listBehavioralQuestions: vi.fn(),
}));

vi.mock('../../../ai-coding/aiCodingApi', () => ({
  listMyAttempts: vi.fn(),
}));

vi.mock('../../../take-home/takeHomeApi', () => ({
  listMyTakeHomeAttempts: vi.fn(),
}));

vi.mock('../../../../hooks/usePracticeStatus', () => ({
  effectiveStatus: vi.fn(() => 'todo'),
  useStatusMapVersion: () => 0,
}));

import { listSystemDesignQuestions, listCodingQuestions, listBehavioralQuestions } from '../../../../content/api';
import { listMyAttempts } from '../../../ai-coding/aiCodingApi';
import { listMyTakeHomeAttempts } from '../../../take-home/takeHomeApi';
import { effectiveStatus } from '../../../../hooks/usePracticeStatus';

beforeEach(() => {
  vi.clearAllMocks();
});

function renderBar(track: 'system-design' | 'coding' | 'behavioral' | 'ai-coding' | 'builder') {
  return render(
    <MemoryRouter>
      <StudyPracticeBar track={track} />
    </MemoryRouter>,
  );
}

describe('StudyPracticeBar', () => {
  it('shows mastered/in-progress/todo counts for system-design', async () => {
    (listSystemDesignQuestions as any).mockResolvedValue([
      { id: 's1', title: 'Q1' },
      { id: 's2', title: 'Q2' },
      { id: 's3', title: 'Q3' },
    ]);
    (effectiveStatus as any).mockImplementation((_t: string, id: string) => {
      if (id === 's1') return 'mastered';
      if (id === 's2') return 'in-progress';
      return 'todo';
    });
    renderBar('system-design');
    await waitFor(() => expect(screen.getByText(/1\s*\/\s*3/)).toBeInTheDocument());
    expect(screen.getByText(/practicing/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /browse questions/i })).toHaveAttribute(
      'href',
      '/system-design/questions',
    );
  });

  it('uses the coding fetcher and questionsPath for the coding track', async () => {
    (listCodingQuestions as any).mockResolvedValue([
      { id: 'c1', title: 'C1' },
      { id: 'c2', title: 'C2' },
    ]);
    (effectiveStatus as any).mockImplementation((_t: string, id: string) =>
      id === 'c1' ? 'mastered' : 'todo',
    );
    renderBar('coding');
    await waitFor(() => expect(screen.getByText(/1\s*\/\s*2/)).toBeInTheDocument());
    expect(screen.getByRole('link', { name: /browse questions/i })).toHaveAttribute(
      'href',
      '/coding/questions',
    );
  });

  it('uses ai-coding attempts for the ai-coding track', async () => {
    (listMyAttempts as any).mockResolvedValue([
      { status: 'in-progress' },
      { status: 'graded' },
      { status: 'graded' },
    ]);
    renderBar('ai-coding');
    await waitFor(() => expect(screen.getByText(/3 rounds/i)).toBeInTheDocument());
    expect(screen.getByText(/2 graded/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /view rounds/i })).toHaveAttribute('href', '/ai-coding');
  });

  it('uses take-home attempts for the builder track', async () => {
    (listMyTakeHomeAttempts as any).mockResolvedValue([
      { status: 'in-progress' },
      { status: 'graded' },
    ]);
    renderBar('builder');
    await waitFor(() => expect(screen.getByText(/2 assignments/i)).toBeInTheDocument());
    expect(screen.getByText(/1 graded/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /view assignments/i })).toHaveAttribute('href', '/builder');
  });

  it('renders only the CTA when async fetch fails (no count strip)', async () => {
    (listMyAttempts as any).mockRejectedValue(new Error('boom'));
    renderBar('ai-coding');
    // CTA visible immediately
    expect(screen.getByRole('link', { name: /view rounds/i })).toBeInTheDocument();
    // Count text should not appear
    await waitFor(() => {
      expect(screen.queryByText(/rounds started/i)).toBeNull();
    });
  });
});
