import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { useState } from 'react';
import ProjectsEditor from '../ProjectsEditor';
import type { ResumeData } from '../../../types';
import { emptyLinks, type ResumeLinks } from '../../../links/types';
import type { LibraryData } from '../../../links/library';
import { updateProject, updateBullet } from '../../../../../experience/experienceApi';

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
            onPick({ ref: 'p1', bulletIds: ['b1'], bulletTitles: ['Adopted by 2k+ users'] });
            onClose();
          }}
        >
          Pick p1
        </button>
        <button type="button" data-testid="picker-close" onClick={onClose}>
          Close
        </button>
      </div>
    );
  },
}));

vi.mock('../../../../../experience/experienceApi', () => ({
  updateProject: vi.fn().mockResolvedValue({}),
  updateBullet: vi.fn().mockResolvedValue({}),
}));

vi.mock('../../../links/library', () => ({
  loadLibrarySnapshot: vi.fn().mockResolvedValue({}),
}));

// ---------------------------------------------------------------------------
// Shared fixture data
// ---------------------------------------------------------------------------

const mockLib: LibraryData = {
  jobs: {},
  projects: {
    p1: {
      id: 'p1',
      title: 'OSS CLI',
      company: '',
      role: '',
      team_size: null,
      tech_stack: ['Rust', 'WASM'],
      start_date: '2022-03-01',
      end_date: '2023-01-01',
      description: 'A blazing-fast CLI',
      tags: [],
    },
  },
  bullets: {
    b1: { id: 'b1', title: 'Adopted by 2k+ users', impact: '', category: '', date: '2022-06-01', tags: [] },
  },
  connMap: { p1: { bullet: ['b1'] } as Record<string, string[]> },
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
        data-projects={JSON.stringify(data.projects)}
      />
      <ProjectsEditor
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
function getProjects(): ResumeData['projects'] {
  return JSON.parse(screen.getByTestId('state-snapshot').getAttribute('data-projects')!);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
});

describe('ProjectsEditor — library-link integration', () => {
  // (a) Add from library → correct entry + links created
  it('(a) clicking "Add from library" → picks p1 → entry + links are created', async () => {
    render(<Harness lib={mockLib} />);

    // Click the "Add from library" button
    fireEvent.click(screen.getByRole('button', { name: /add from library/i }));

    // The picker stub should appear
    expect(screen.getByTestId('library-picker')).toBeInTheDocument();

    // Simulate picking p1
    await act(async () => {
      fireEvent.click(screen.getByTestId('picker-pick'));
    });

    // Picker should close
    expect(screen.queryByTestId('library-picker')).not.toBeInTheDocument();

    // Check the new project entry
    const projects = getProjects();
    expect(projects).toHaveLength(1);
    expect(projects[0].name).toBe('OSS CLI');
    expect(projects[0].highlights).toEqual(['Adopted by 2k+ users']);

    // Check that links were created
    const links = getLinks();
    const newId = projects[0].id;
    expect(links.projects[newId]).toBeDefined();
    expect(links.projects[newId].ref).toBe('p1');
    expect(links.projects[newId].bulletRefs).toEqual(['b1']);
    expect(links.projects[newId].bulletEdited).toEqual([false]);
    expect(links.projects[newId].headerEdited).toBe(false);
  });

  // (b) Editing a linked highlight flips bulletEdited[i] = true
  it('(b) editing a linked highlight sets bulletEdited[i] = true', async () => {
    const baseData = emptyResumeData();
    baseData.projects = [
      {
        id: 'pr1',
        name: 'OSS CLI',
        description: 'A blazing-fast CLI',
        technologies: ['Rust'],
        highlights: ['Adopted by 2k+ users'],
        startDate: '',
        endDate: '',
      },
    ];
    const baseLinks = emptyLinks();
    baseLinks.projects.pr1 = {
      ref: 'p1',
      headerEdited: false,
      bulletRefs: ['b1'],
      bulletEdited: [false],
    };

    render(<Harness initialData={baseData} initialLinks={baseLinks} lib={mockLib} />);

    // Find the highlights textarea and change it
    const textarea = screen.getByDisplayValue('Adopted by 2k+ users');
    fireEvent.change(textarea, { target: { value: 'Changed highlight text' } });

    // bulletEdited[0] should now be true
    await waitFor(() => {
      const links = getLinks();
      expect(links.projects.pr1.bulletEdited[0]).toBe(true);
    });
  });

  // (c) Edited bullet shows Relink; clicking it restores from lib + sets bulletEdited[i]=false
  it('(c) edited bullet shows Relink; clicking restores title and clears bulletEdited', async () => {
    const baseData = emptyResumeData();
    baseData.projects = [
      {
        id: 'pr1',
        name: 'OSS CLI',
        description: 'A blazing-fast CLI',
        technologies: ['Rust'],
        highlights: ['my custom text'],
        startDate: '',
        endDate: '',
      },
    ];
    const baseLinks = emptyLinks();
    baseLinks.projects.pr1 = {
      ref: 'p1',
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
      const projects = getProjects();
      expect(projects[0].highlights[0]).toBe('Adopted by 2k+ users');
    });

    // bulletEdited[0] should be false again
    await waitFor(() => {
      const links = getLinks();
      expect(links.projects.pr1.bulletEdited[0]).toBe(false);
    });
  });

  // (d) Push on an edited bullet calls updateBullet and clears bulletEdited
  it('(d) Push on edited bullet calls updateBullet and clears bulletEdited[i]', async () => {
    const baseData = emptyResumeData();
    baseData.projects = [
      {
        id: 'pr1',
        name: 'OSS CLI',
        description: 'A blazing-fast CLI',
        technologies: ['Rust'],
        highlights: ['my edited bullet'],
        startDate: '',
        endDate: '',
      },
    ];
    const baseLinks = emptyLinks();
    baseLinks.projects.pr1 = {
      ref: 'p1',
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
      expect(links.projects.pr1.bulletEdited[0]).toBe(false);
    });
  });

  // (e) Editing a header field sets headerEdited = true
  it('(e) editing a linked header field (Name) sets headerEdited = true', async () => {
    const baseData = emptyResumeData();
    baseData.projects = [
      {
        id: 'pr1',
        name: 'OSS CLI',
        description: 'A blazing-fast CLI',
        technologies: ['Rust'],
        highlights: [],
        startDate: '',
        endDate: '',
      },
    ];
    const baseLinks = emptyLinks();
    baseLinks.projects.pr1 = {
      ref: 'p1',
      headerEdited: false,
      bulletRefs: [],
      bulletEdited: [],
    };

    render(<Harness initialData={baseData} initialLinks={baseLinks} lib={mockLib} />);

    // Find the Name input and change it
    const nameInput = screen.getByDisplayValue('OSS CLI');
    fireEvent.change(nameInput, { target: { value: 'My Renamed Project' } });

    // headerEdited should flip to true
    await waitFor(() => {
      const links = getLinks();
      expect(links.projects.pr1.headerEdited).toBe(true);
    });
  });
});
