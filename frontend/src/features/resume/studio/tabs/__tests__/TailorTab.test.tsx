// TailorTab — integration tests for markEdits being applied on apply/save actions.
//
// Strategy: drive the component with a pre-set `proposed` state by mocking
// `tailorResume` to return the proposed rewrite synchronously, then click
// Generate to populate `proposed`, and then click the action buttons.
// This tests the real integration without depending on actual AI infrastructure.

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { useState } from 'react';
import { MemoryRouter } from 'react-router-dom';
import TailorTab from '../TailorTab';
import type { ResumeData } from '../../../types';
import { emptyLinks, type ResumeLinks } from '../../../links/types';
import { markEdits } from '../../../links/maintain';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock('../../../ai/client', () => ({
  tailorResume: vi.fn(),
}));

vi.mock('../../../api', () => ({
  createVariant: vi.fn(),
}));

vi.mock('../../../../applications/api', () => ({
  listApplications: vi.fn().mockResolvedValue([]),
}));

// Import the mocked modules so we can configure return values in tests
import { tailorResume } from '../../../ai/client';
import { createVariant } from '../../../api';

// ---------------------------------------------------------------------------
// Fixture data
// ---------------------------------------------------------------------------

function makeData(): ResumeData {
  return {
    personalInfo: { fullName: 'Jane Doe' },
    experience: [
      {
        id: 'e1',
        company: 'Acme',
        position: 'Engineer',
        location: 'Remote',
        startDate: '2020-01-01',
        endDate: '',
        current: true,
        description: '',
        highlights: ['Built distributed systems', 'Reduced latency by 30%'],
      },
    ],
    education: [],
    skills: [],
    projects: [],
    publications: [],
    profiles: [],
  };
}

// A proposed rewrite where the second bullet of e1 changed
function makeProposed(base: ResumeData): ResumeData {
  return {
    ...base,
    experience: [
      {
        ...base.experience[0],
        highlights: [
          base.experience[0].highlights[0], // unchanged
          'Slashed p99 latency by 40% via cache-aside pattern', // CHANGED
        ],
      },
    ],
  };
}

function makeLinks(): ResumeLinks {
  const links = emptyLinks();
  links.experience.e1 = {
    ref: 'lib-job-1',
    headerEdited: false,
    bulletRefs: ['b1', 'b2'],
    bulletEdited: [false, false],
  };
  return links;
}

// ---------------------------------------------------------------------------
// Controlled harness
// ---------------------------------------------------------------------------

function Harness({
  initialData,
  initialLinks,
}: {
  initialData?: ResumeData;
  initialLinks?: ResumeLinks;
}) {
  const [data, setData] = useState<ResumeData>(initialData ?? makeData());
  const [links, setLinks] = useState<ResumeLinks>(initialLinks ?? emptyLinks());

  return (
    <MemoryRouter>
      {/* Expose state for assertions */}
      <div
        data-testid="state-snapshot"
        data-links={JSON.stringify(links)}
        data-data={JSON.stringify(data)}
      />
      <TailorTab
        data={data}
        resume={{ id: 'r1', name: 'My Resume', user_id: 'u1', created_at: '', updated_at: '' } as never}
        setData={setData}
        links={links}
        setLinks={setLinks}
      />
    </MemoryRouter>
  );
}

function getLinks(): ResumeLinks {
  return JSON.parse(screen.getByTestId('state-snapshot').getAttribute('data-links')!);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
  // createVariant should return something realistic so the component doesn't blow up
  (createVariant as ReturnType<typeof vi.fn>).mockResolvedValue({
    id: 'v1',
    name: 'Acme — Engineer variant',
    resume_id: 'r1',
    data: makeData(),
    links: emptyLinks(),
    target_company: '',
    job_title: '',
    job_description: '',
    tone: '',
    role_focus: [],
    application_id: null,
    created_at: '',
    updated_at: '',
  });
});

describe('TailorTab — markEdits integration', () => {
  it('(a) "Apply to master" calls setLinks with markEdits applied (changed bullet flagged)', async () => {
    const data = makeData();
    const proposed = makeProposed(data);
    const links = makeLinks();

    // tailorResume resolves with the proposed rewrite
    (tailorResume as ReturnType<typeof vi.fn>).mockResolvedValue({ data: proposed });

    render(<Harness initialData={data} initialLinks={links} />);

    // Type a JD and click Generate to get proposed into state
    const jdTextarea = screen.getByPlaceholderText(/paste the job description/i);
    fireEvent.change(jdTextarea, { target: { value: 'Looking for a senior engineer with distributed systems expertise.' } });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /generate tailored draft/i }));
    });

    // Wait for proposed section to appear
    await waitFor(() => {
      expect(screen.getByText(/proposed rewrite/i)).toBeInTheDocument();
    });

    // Click "Apply to master"
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /apply to master/i }));
    });

    // The links state should reflect markEdits(data, proposed, links)
    const expectedLinks = markEdits(data, proposed, links);
    await waitFor(() => {
      const resultLinks = getLinks();
      // bulletEdited[1] should now be true (that bullet changed)
      expect(resultLinks.experience.e1.bulletEdited[1]).toBe(true);
      // bulletEdited[0] should stay false (that bullet didn't change)
      expect(resultLinks.experience.e1.bulletEdited[0]).toBe(false);
      // Deep-equal check against the real markEdits output
      expect(resultLinks).toEqual(expectedLinks);
    });
  });

  it('(b) "Save as variant" passes links=markEdits(data, proposed, links) to createVariant', async () => {
    const data = makeData();
    const proposed = makeProposed(data);
    const links = makeLinks();

    (tailorResume as ReturnType<typeof vi.fn>).mockResolvedValue({ data: proposed });

    render(<Harness initialData={data} initialLinks={links} />);

    const jdTextarea = screen.getByPlaceholderText(/paste the job description/i);
    fireEvent.change(jdTextarea, { target: { value: 'Seeking a backend engineer to own latency improvements.' } });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /generate tailored draft/i }));
    });

    await waitFor(() => {
      expect(screen.getByText(/proposed rewrite/i)).toBeInTheDocument();
    });

    // Click "Save as variant"
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /save as variant/i }));
    });

    // Wait for createVariant to be called
    await waitFor(() => {
      expect(createVariant).toHaveBeenCalledTimes(1);
    });

    // The links argument passed to createVariant must equal markEdits(data, proposed, links)
    const expectedLinks = markEdits(data, proposed, links);
    const callArg = (createVariant as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(callArg.links).toEqual(expectedLinks);

    // Sanity: the changed bullet must be flagged
    expect(callArg.links.experience.e1.bulletEdited[1]).toBe(true);
    expect(callArg.links.experience.e1.bulletEdited[0]).toBe(false);
  });
});
