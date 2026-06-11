import { describe, it, expect } from 'vitest';
import { addBullet, removeBulletAt, moveBullet, editBulletAt, markEdits, reconcileHighlightLinks } from '../maintain';
import { emptyEntryLink, emptyLinks } from '../types';
import type { ResumeData } from '../../types';

describe('link-array maintenance', () => {
  const base = () => ({ ref: 'j1', headerEdited: false, bulletRefs: ['b1', null, 'b3'], bulletEdited: [false, false, false] });

  it('addBullet appends null ref + false edited', () => {
    expect(addBullet(base())).toEqual({ ref: 'j1', headerEdited: false, bulletRefs: ['b1', null, 'b3', null], bulletEdited: [false, false, false, false] });
  });
  it('removeBulletAt splices both arrays', () => {
    expect(removeBulletAt(base(), 1)).toEqual({ ref: 'j1', headerEdited: false, bulletRefs: ['b1', 'b3'], bulletEdited: [false, false] });
  });
  it('moveBullet reorders both arrays', () => {
    const out = moveBullet(base(), 0, 2);
    expect(out.bulletRefs).toEqual([null, 'b3', 'b1']);
  });
  it('editBulletAt flags only that index edited', () => {
    expect(editBulletAt(base(), 2).bulletEdited).toEqual([false, false, true]);
  });
});

describe('markEdits', () => {
  it('flags header + bullets that diverge from prior values', () => {
    const prev: ResumeData = { personalInfo: { fullName: '' }, education: [], skills: [], publications: [], profiles: [], projects: [],
      experience: [{ id: 'e1', company: 'Acme', position: 'Eng', location: '', startDate: '', endDate: '', current: false, description: '', highlights: ['a', 'b'] }] };
    const next: ResumeData = { ...prev, experience: [{ ...prev.experience[0], position: 'Senior Eng', highlights: ['a', 'B!'] }] };
    const links = emptyLinks();
    links.experience.e1 = { ref: 'j1', headerEdited: false, bulletRefs: ['x', 'y'], bulletEdited: [false, false] };
    const out = markEdits(prev, next, links);
    expect(out.experience.e1.headerEdited).toBe(true);
    expect(out.experience.e1.bulletEdited).toEqual([false, true]);
  });
});

it('emptyEntryLink shape', () => {
  expect(emptyEntryLink()).toEqual({ ref: null, headerEdited: false, bulletRefs: [], bulletEdited: [] });
});

describe('reconcileHighlightLinks', () => {
  const baseLink = () => ({
    ref: 'j1',
    headerEdited: false,
    bulletRefs: ['b1', 'b2', 'b3'] as (string | null)[],
    bulletEdited: [false, false, false],
  });

  it('same length: preserves refs; flips edited only for the changed index', () => {
    const prev = ['alpha', 'beta', 'gamma'];
    const next = ['alpha', 'CHANGED', 'gamma'];
    const out = reconcileHighlightLinks(prev, next, baseLink());
    expect(out.bulletRefs).toEqual(['b1', 'b2', 'b3']);
    expect(out.bulletEdited).toEqual([false, true, false]);
  });

  it('next shorter: arrays are truncated to next.length', () => {
    const prev = ['alpha', 'beta', 'gamma'];
    const next = ['alpha', 'beta'];
    const out = reconcileHighlightLinks(prev, next, baseLink());
    expect(out.bulletRefs).toHaveLength(2);
    expect(out.bulletEdited).toHaveLength(2);
    expect(out.bulletRefs).toEqual(['b1', 'b2']);
    expect(out.bulletEdited).toEqual([false, false]);
  });

  it('next longer: appended rows get null ref + false edited', () => {
    const link = { ref: 'j1', headerEdited: false, bulletRefs: ['b1'] as (string | null)[], bulletEdited: [false] };
    const prev = ['alpha'];
    const next = ['alpha', 'new row'];
    const out = reconcileHighlightLinks(prev, next, link);
    expect(out.bulletRefs).toEqual(['b1', null]);
    expect(out.bulletEdited).toEqual([false, false]);
  });
});
