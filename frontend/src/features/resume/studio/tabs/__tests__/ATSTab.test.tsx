// ATS AI Scoring (ROUNDS-00A-L01): the switch starts off, a `true`
// stored under the old key no longer turns it on, and no AI score is
// asked for until the person turns it on.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../../../../applications/api', () => ({ listApplications: vi.fn().mockResolvedValue([]) }));
vi.mock('../../../ai/client', () => ({ getATSRuleScore: vi.fn(), getATSAIScore: vi.fn() }));
vi.mock('../../EnhancementContext', () => ({ useEnhancementContext: () => ({ setATS: vi.fn() }) }));

import ATSTab from '../ATSTab';
import { getATSAIScore, getATSRuleScore } from '../../../ai/client';
import { emptyResumeData, type Resume } from '../../../types';

const RESUME = { id: 'r1' } as unknown as Resume;

function renderTab() {
  return render(
    <MemoryRouter>
      <ATSTab data={emptyResumeData()} resume={RESUME} />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  window.localStorage.clear();
  vi.mocked(getATSRuleScore).mockReset().mockResolvedValue({
    rule_score: 50,
    breakdown: {},
    suggestions: [],
    missing_keywords: [],
  });
  vi.mocked(getATSAIScore).mockReset().mockResolvedValue({
    ai_score: null,
    ai: null,
    ai_status: 'unconfigured',
    ai_suggestions: [],
  });
});

afterEach(() => {
  vi.useRealTimers();
});

describe('ATSTab AI Scoring', () => {
  it('starts off, even when the old key stored an opt-in', () => {
    window.localStorage.setItem('rounds.resume.ats.r1.useAI', 'true');
    renderTab();
    expect(screen.getByRole('switch')).toHaveAttribute('aria-checked', 'false');
  });

  it('keeps a new opt-in under the v2 key', async () => {
    const user = userEvent.setup();
    renderTab();
    await user.click(screen.getByRole('switch'));
    expect(screen.getByRole('switch')).toHaveAttribute('aria-checked', 'true');
    expect(window.localStorage.getItem('rounds.resume.ats.r1.useAI.v2')).toBe('true');
  });

  it('asks for an AI score only after the person turns it on', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    renderTab();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(getATSRuleScore).toHaveBeenCalled();
    expect(getATSAIScore).not.toHaveBeenCalled();

    await user.click(screen.getByRole('switch'));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(getATSAIScore).toHaveBeenCalledTimes(1);
    expect(vi.mocked(getATSAIScore).mock.calls[0][2]).toBe(true);
  });
});
