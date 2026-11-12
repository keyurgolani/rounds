// While the demo account is signed in, the ATS and Tailor tabs keep what a
// visitor types under the demo-only prefix (ROUNDS-00B-L07), untitled
// resumes included, which the SPA clears at every demo sign-out and at a
// start with no demo session. Every other account keeps its own keys.

import { act, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const session = vi.hoisted(() => ({ demo: true }));

vi.mock('../../../../../auth/AuthProvider', () => ({ useIsDemo: () => session.demo }));
vi.mock('../../../../../applications/api', () => ({ listApplications: vi.fn().mockResolvedValue([]) }));
vi.mock('../../../ai/client', () => ({
  getATSRuleScore: vi.fn().mockResolvedValue({ rule_score: 50, breakdown: {}, suggestions: [], missing_keywords: [] }),
  getATSAIScore: vi.fn(),
  tailorResume: vi.fn(),
}));
vi.mock('../../EnhancementContext', () => ({ useEnhancementContext: () => ({ setATS: vi.fn() }) }));
vi.mock('../../../api', () => ({ createVariant: vi.fn() }));

import ATSTab from '../ATSTab';
import TailorTab from '../TailorTab';
import { emptyResumeData, type Resume } from '../../../types';
import { emptyLinks } from '../../../links/types';

const RESUME = { id: 'r1' } as unknown as Resume;

function keys(): string[] {
  return Object.keys(window.localStorage).sort();
}

async function optInOnATS(resume: Resume | null) {
  const user = userEvent.setup();
  render(
    <MemoryRouter>
      <ATSTab data={emptyResumeData()} resume={resume} />
    </MemoryRouter>,
  );
  await user.click(screen.getByRole('switch'));
}

async function typeJobOnTailor() {
  render(
    <MemoryRouter>
      <TailorTab
        data={emptyResumeData()}
        resume={RESUME}
        setData={() => undefined}
        links={emptyLinks()}
        setLinks={() => undefined}
      />
    </MemoryRouter>,
  );
  await act(async () => {
    fireEvent.change(screen.getByPlaceholderText(/paste the job description/i), {
      target: { value: 'A job description a visitor pasted.' },
    });
  });
}

beforeEach(() => {
  window.localStorage.clear();
  session.demo = true;
});

describe('the demo account in the resume studio', () => {
  it('keeps its ATS settings under the demo-only prefix', async () => {
    await optInOnATS(RESUME);
    expect(window.localStorage.getItem('rounds.demo.resume.ats.r1.useAI.v2')).toBe('true');
    expect(keys().filter((key) => key.startsWith('rounds.resume.'))).toEqual([]);
  });

  it('keeps the keys of an untitled resume under it too', async () => {
    await optInOnATS(null);
    expect(window.localStorage.getItem('rounds.demo.resume.ats.untitled.useAI.v2')).toBe('true');
  });

  it('keeps the job description Tailor holds under it', async () => {
    await typeJobOnTailor();
    expect(JSON.parse(window.localStorage.getItem('rounds.demo.resume.tailor.r1.jd') ?? 'null')).toBe(
      'A job description a visitor pasted.',
    );
    expect(keys().filter((key) => key.startsWith('rounds.resume.'))).toEqual([]);
  });
});

describe('any other account in the resume studio', () => {
  it('keeps its keys where they were', async () => {
    session.demo = false;
    await optInOnATS(RESUME);
    await typeJobOnTailor();
    expect(window.localStorage.getItem('rounds.resume.ats.r1.useAI.v2')).toBe('true');
    expect(window.localStorage.getItem('rounds.resume.tailor.r1.jd')).not.toBeNull();
    expect(keys().filter((key) => key.startsWith('rounds.demo.'))).toEqual([]);
  });
});
