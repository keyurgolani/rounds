import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { useState } from 'react';
import ExperienceEditor from '../ExperienceEditor';
import type { ResumeData } from '../../../types';
import { emptyLinks, type ResumeLinks } from '../../../links/types';
import type { LibraryData } from '../../../links/library';
import { updateJob, updateBullet } from '../../../../../experience/experienceApi';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock('../../../links/LibraryPicker', () => ({
  default: ({
    open,
    onPick,
    onClose,
  }: {
    open: boolean;
    onPick: (sel: { ref: string; bulletIds: string[]; bulletTitles: string[] }) => void;
    onClose: () => void;
  }) => {
    if (!open) return null;
    return (
      <div data-testid="library-picker">
        <button
          type="button"
          data-testid="picker-pick"
          onClick={() => {
            onPick({ ref: 'j1', bulletIds: ['b1'], bulletTitles: ['Cut p99 40%'] });
            onClose();
          }}
        >
          Pick j1
        </button>
        <button type="button" data-testid="picker-close" onClick={onClose}>
          Close
        </button>
      </div>
    );
  },
}));

vi.mock('../../../../../experience/experienceApi', () => ({
  updateJob: vi.fn().mockResolvedValue({}),
  updateBullet: vi.fn().mockResolvedValue({}),
}));

vi.mock('../../../links/library', () => ({
  loadLibrarySnapshot: vi.fn().mockResolvedValue({}),
}));

// ---------------------------------------------------------------------------
// Shared fixture data
// ---------------------------------------------------------------------------

const mockLib: LibraryData = {
  jobs: {
    j1: {
      id: 'j1',
      company: 'Acme',
      role: 'Staff Eng',
      location: 'Remote',
      employment_type: '',
      start_date: '2021-01-01',
      end_date: null,
      description: 'Built things',
      tags: [],
    },
  },
  projects: {},
  bullets: {
    b1: { id: 'b1', title: 'Cut p99 40%', impact: '', category: '', date: '2021-06-01', tags: [] },
  },
  connMap: { j1: { bullet: ['b1'] } as Record<string, string[]> },
};

function emptyResumeData(): ResumeData {
  return {
    personalInfo: { fullName: '' },
    experience: [],
    education: [],
    skills: [],
    projects: [],
    publications: [],
    profiles: [],
  };
}

// ---------------------------------------------------------------------------
// Controlled harness — holds data + links in state so tests can read them
// ---------------------------------------------------------------------------

function Harness({
  initialData,
  initialLinks,
  lib,
}: {
  initialData?: ResumeData;
  initialLinks?: ResumeLinks;
  lib?: LibraryData | null;
}) {
  const [data, setData] = useState<ResumeData>(initialData ?? emptyResumeData());
  const [links, setLinks] = useState<ResumeLinks>(initialLinks ?? emptyLinks());

  return (
    <>
      {/* Expose state to assertions via data attributes on a hidden node */}
      <div
        data-testid="state-snapshot"
        data-links={JSON.stringify(links)}
        data-experience={JSON.stringify(data.experience)}
      />
      <ExperienceEditor
        data={data}
        setData={setData}
        links={links}
        setLinks={setLinks}
        lib={lib ?? null}
      />
    </>
  );
}

function getLinks(): ResumeLinks {
  return JSON.parse(screen.getByTestId('state-snapshot').getAttribute('data-links')!);
}
function getExperience(): ResumeData['experience'] {
  return JSON.parse(screen.getByTestId('state-snapshot').getAttribute('data-experience')!);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
});

describe('ExperienceEditor — library-link integration', () => {
  // (a) Add from library → correct entry + links created
  it('(a) clicking "Add from library" → picks j1 → entry + links are created', async () => {
    render(<Harness lib={mockLib} />);

    // Click the "Add from library" button
    fireEvent.click(screen.getByRole('button', { name: /add from library/i }));

    // The picker stub should appear
    expect(screen.getByTestId('library-picker')).toBeInTheDocument();

    // Simulate picking j1
    await act(async () => {
      fireEvent.click(screen.getByTestId('picker-pick'));
    });

    // Picker should close
    expect(screen.queryByTestId('library-picker')).not.toBeInTheDocument();

    // Check the new experience entry
    const exp = getExperience();
    expect(exp).toHaveLength(1);
    expect(exp[0].company).toBe('Acme');
    expect(exp[0].position).toBe('Staff Eng');
    expect(exp[0].highlights).toEqual(['Cut p99 40%']);

    // Check that links were created
    const links = getLinks();
    const newId = exp[0].id;
    expect(links.experience[newId]).toBeDefined();
    expect(links.experience[newId].ref).toBe('j1');
    expect(links.experience[newId].bulletRefs).toEqual(['b1']);
    expect(links.experience[newId].bulletEdited).toEqual([false]);
    expect(links.experience[newId].headerEdited).toBe(false);
  });

  // (b) Editing a linked highlight flips bulletEdited[i] = true
  it('(b) editing a linked highlight sets bulletEdited[i] = true', async () => {
    const baseData = emptyResumeData();
    baseData.experience = [
      {
        id: 'e1',
        company: 'Acme',
        position: 'Staff Eng',
        highlights: ['Cut p99 40%'],
        location: '',
        startDate: '',
        endDate: '',
        current: false,
        description: '',
      },
    ];
    const baseLinks = emptyLinks();
    baseLinks.experience.e1 = {
      ref: 'j1',
      headerEdited: false,
      bulletRefs: ['b1'],
      bulletEdited: [false],
    };

    render(<Harness initialData={baseData} initialLinks={baseLinks} lib={mockLib} />);

    // Find the highlights textarea (the first row in StringList) and change it
    const textarea = screen.getByDisplayValue('Cut p99 40%');
    fireEvent.change(textarea, { target: { value: 'Changed highlight text' } });

    // bulletEdited[0] should now be true
    await waitFor(() => {
      const links = getLinks();
      expect(links.experience.e1.bulletEdited[0]).toBe(true);
    });
  });

  // (c) Edited bullet shows Relink; clicking it restores from lib + sets bulletEdited[i]=false
  it('(c) edited bullet shows Relink; clicking restores title and clears bulletEdited', async () => {
    const baseData = emptyResumeData();
    baseData.experience = [
      {
        id: 'e1',
        company: 'Acme',
        position: 'Staff Eng',
        highlights: ['my custom text'],
        location: '',
        startDate: '',
        endDate: '',
        current: false,
        description: '',
      },
    ];
    const baseLinks = emptyLinks();
    baseLinks.experience.e1 = {
      ref: 'j1',
      headerEdited: false,
      bulletRefs: ['b1'],
      bulletEdited: [true], // already edited
    };

    render(<Harness initialData={baseData} initialLinks={baseLinks} lib={mockLib} />);

    // Should see a Relink button for the edited bullet
    const relinkBtns = await screen.findAllByRole('button', { name: /relink/i });
    expect(relinkBtns.length).toBeGreaterThan(0);
    const relinkBtn = relinkBtns[0];

    // Click Relink
    await act(async () => {
      fireEvent.click(relinkBtn);
    });

    // Highlight should be restored to library value
    await waitFor(() => {
      const exp = getExperience();
      expect(exp[0].highlights[0]).toBe('Cut p99 40%');
    });

    // bulletEdited[0] should be false again
    await waitFor(() => {
      const links = getLinks();
      expect(links.experience.e1.bulletEdited[0]).toBe(false);
    });
  });

  // (d) Push on an edited bullet calls updateBullet and clears bulletEdited
  it('(d) Push on edited bullet calls updateBullet and clears bulletEdited[i]', async () => {
    const baseData = emptyResumeData();
    baseData.experience = [
      {
        id: 'e1',
        company: 'Acme',
        position: 'Staff Eng',
        highlights: ['my edited bullet'],
        location: '',
        startDate: '',
        endDate: '',
        current: false,
        description: '',
      },
    ];
    const baseLinks = emptyLinks();
    baseLinks.experience.e1 = {
      ref: 'j1',
      headerEdited: false,
      bulletRefs: ['b1'],
      bulletEdited: [true],
    };

    render(<Harness initialData={baseData} initialLinks={baseLinks} lib={mockLib} />);

    // Should see a Push button for the edited bullet
    const pushBtns = await screen.findAllByRole('button', { name: /^push$/i });
    expect(pushBtns.length).toBeGreaterThan(0);

    await act(async () => {
      fireEvent.click(pushBtns[0]);
    });

    // updateBullet should have been called with the edited text
    await waitFor(() => {
      expect(updateBullet).toHaveBeenCalledWith('b1', { title: 'my edited bullet' });
    });

    // bulletEdited[0] should now be false
    await waitFor(() => {
      const links = getLinks();
      expect(links.experience.e1.bulletEdited[0]).toBe(false);
    });
  });

  // (e) Editing a header field sets headerEdited = true
  it('(e) editing a linked header field sets headerEdited = true', async () => {
    const baseData = emptyResumeData();
    baseData.experience = [
      {
        id: 'e1',
        company: 'Acme',
        position: 'Staff Eng',
        highlights: [],
        location: '',
        startDate: '',
        endDate: '',
        current: false,
        description: '',
      },
    ];
    const baseLinks = emptyLinks();
    baseLinks.experience.e1 = {
      ref: 'j1',
      headerEdited: false,
      bulletRefs: [],
      bulletEdited: [],
    };

    render(<Harness initialData={baseData} initialLinks={baseLinks} lib={mockLib} />);

    // Find the Position input and change it
    const positionInput = screen.getByDisplayValue('Staff Eng');
    fireEvent.change(positionInput, { target: { value: 'Principal Eng' } });

    // headerEdited should flip to true
    await waitFor(() => {
      const links = getLinks();
      expect(links.experience.e1.headerEdited).toBe(true);
    });
  });
});
