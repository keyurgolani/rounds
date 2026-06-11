import { describe, it, expect } from 'vitest';
import { toYM, toMD, jobHeaderBack, resolveAndSync, type LibrarySnapshot } from '../resolve';
import type { ResumeData } from '../../types';
import { emptyLinks } from '../types';

const lib: LibrarySnapshot = {
  jobs: { j1: { id: 'j1', company: 'Acme', role: 'Staff Eng', location: 'Remote', employment_type: '', start_date: '2021-03-15', end_date: null, description: 'Built things', tags: [] } },
  projects: {},
  bullets: { b1: { id: 'b1', title: 'Cut p99 40%', impact: '', category: '', date: '2021-06-01', tags: [] } },
};

function baseData(): ResumeData {
  return {
    personalInfo: { fullName: 'X' }, education: [], skills: [], publications: [], profiles: [], projects: [],
    experience: [{ id: 'e1', company: 'stale', position: 'stale', location: 'stale', startDate: '2000-01', endDate: '', current: false, description: 'stale', highlights: ['stale bullet'] }],
  };
}

describe('toYM', () => {
  it('truncates YYYY-MM-DD to YYYY-MM and passes empty through', () => {
    expect(toYM('2021-03-15')).toBe('2021-03');
    expect(toYM(null)).toBe('');
    expect(toYM('')).toBe('');
  });
});

describe('toMD / jobHeaderBack (push-to-library)', () => {
  it('toMD appends -01 to a YYYY-MM and passes empty through', () => {
    expect(toMD('2021-03')).toBe('2021-03-01');
    expect(toMD('')).toBe('');
  });
  it('jobHeaderBack maps a resume header to library job fields', () => {
    const e = { id: 'e1', company: 'Acme', position: 'Staff', location: 'Remote', startDate: '2021-03', endDate: '', current: true, description: 'd', highlights: [] };
    expect(jobHeaderBack(e)).toEqual({ company: 'Acme', role: 'Staff', location: 'Remote', start_date: '2021-03-01', end_date: null, description: 'd' });
  });
});

describe('resolveAndSync', () => {
  it('refreshes a linked, unedited header + bullet from the library', () => {
    const data = baseData();
    const links = emptyLinks();
    links.experience.e1 = { ref: 'j1', headerEdited: false, bulletRefs: ['b1'], bulletEdited: [false] };
    const out = resolveAndSync(data, links, lib);
    expect(out.changed).toBe(true);
    expect(out.data.experience[0].company).toBe('Acme');
    expect(out.data.experience[0].position).toBe('Staff Eng');
    expect(out.data.experience[0].startDate).toBe('2021-03');
    expect(out.data.experience[0].current).toBe(true);
    expect(out.data.experience[0].highlights[0]).toBe('Cut p99 40%');
  });

  it('skips edited pieces', () => {
    const data = baseData();
    const links = emptyLinks();
    links.experience.e1 = { ref: 'j1', headerEdited: true, bulletRefs: ['b1'], bulletEdited: [true] };
    const out = resolveAndSync(data, links, lib);
    expect(out.changed).toBe(false);
    expect(out.data.experience[0].company).toBe('stale');
    expect(out.data.experience[0].highlights[0]).toBe('stale bullet');
  });

  it('orphans a missing ref: keeps the value, clears the ref', () => {
    const data = baseData();
    const links = emptyLinks();
    links.experience.e1 = { ref: 'GONE', headerEdited: false, bulletRefs: ['ALSO_GONE'], bulletEdited: [false] };
    const out = resolveAndSync(data, links, lib);
    expect(out.data.experience[0].company).toBe('stale');
    expect(out.links.experience.e1.ref).toBeNull();
    expect(out.links.experience.e1.bulletRefs[0]).toBeNull();
    expect(out.changed).toBe(true);
  });

  it('leaves manual entries (no ref) untouched', () => {
    const data = baseData();
    const links = emptyLinks();
    links.experience.e1 = { ref: null, headerEdited: false, bulletRefs: [null], bulletEdited: [false] };
    const out = resolveAndSync(data, links, lib);
    expect(out.changed).toBe(false);
    expect(out.data.experience[0].company).toBe('stale');
  });

  it('does NOT extend highlights when bulletRefs is longer than highlights (desync guard)', () => {
    // bulletRefs has 3 entries but the entry only has 2 highlights — simulates
    // the field-level AI-improve desync. Resolver must clamp to highlights.length.
    const data: ResumeData = {
      personalInfo: { fullName: 'X' }, education: [], skills: [], publications: [], profiles: [], projects: [],
      experience: [{ id: 'e1', company: 'Acme', position: 'Staff Eng', location: 'Remote', startDate: '2021-03', endDate: '', current: true, description: 'Built things', highlights: ['first', 'second'] }],
    };
    const libWithBullets: LibrarySnapshot = {
      ...lib,
      bullets: {
        b1: { id: 'b1', title: 'From lib 1', impact: '', category: '', date: '2021-06-01', tags: [] },
        b2: { id: 'b2', title: 'From lib 2', impact: '', category: '', date: '2021-06-01', tags: [] },
        b3: { id: 'b3', title: 'From lib 3', impact: '', category: '', date: '2021-06-01', tags: [] },
      },
    };
    const links = emptyLinks();
    links.experience.e1 = { ref: null, headerEdited: false, bulletRefs: ['b1', 'b2', 'b3'], bulletEdited: [false, false, false] };
    const out = resolveAndSync(data, links, libWithBullets);
    // highlights must stay at length 2 — the third ref is out-of-bounds
    expect(out.data.experience[0].highlights).toHaveLength(2);
    // The first two highlights should be refreshed from library
    expect(out.data.experience[0].highlights[0]).toBe('From lib 1');
    expect(out.data.experience[0].highlights[1]).toBe('From lib 2');
  });
});
