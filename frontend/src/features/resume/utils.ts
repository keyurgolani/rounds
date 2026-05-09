// Small shared utilities used by Studio components.

import type {
  Education,
  Profile,
  Project,
  Publication,
  ResumeData,
  SectionKey,
  SkillGroup,
  WorkExperience,
} from './types';

// crypto.randomUUID is available everywhere we ship. Strip the dashes
// to make the ids slightly more compact when they appear in the DOM.
export function uid(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID().replace(/-/g, '').slice(0, 16);
  }
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

// Default ordering when the user hasn't customized it.
export const DEFAULT_SECTION_ORDER: SectionKey[] = [
  'personal',
  'experience',
  'education',
  'skills',
  'projects',
  'publications',
  'profiles',
];

export const SECTION_LABELS: Record<SectionKey, string> = {
  personal: 'Personal',
  experience: 'Experience',
  education: 'Education',
  skills: 'Skills',
  projects: 'Projects',
  publications: 'Publications',
  profiles: 'Profiles',
};

export function sectionOrder(data: ResumeData): SectionKey[] {
  if (data.sectionOrder && data.sectionOrder.length === DEFAULT_SECTION_ORDER.length) {
    return data.sectionOrder;
  }
  return DEFAULT_SECTION_ORDER;
}

export function isSectionHidden(data: ResumeData, key: SectionKey): boolean {
  return Boolean(data.hiddenSections?.includes(key));
}

// Constructors for empty section items — used by editors when "Add" is clicked.
export function newExperience(): WorkExperience {
  return { id: uid(), company: '', position: '', highlights: [] };
}

export function newEducation(): Education {
  return { id: uid(), institution: '' };
}

export function newSkillGroup(category = ''): SkillGroup {
  return { id: uid(), category, items: [] };
}

export function newProject(): Project {
  return { id: uid(), name: '', technologies: [], highlights: [] };
}

export function newPublication(): Publication {
  return { id: uid(), title: '' };
}

export function newProfile(): Profile {
  return { id: uid(), network: '' };
}

// Replace an item in an array by id (immutable).
export function patchById<T extends { id: string }>(
  arr: T[],
  id: string,
  patch: Partial<T>,
): T[] {
  return arr.map((it) => (it.id === id ? { ...it, ...patch } : it));
}

export function removeById<T extends { id: string }>(arr: T[], id: string): T[] {
  return arr.filter((it) => it.id !== id);
}

export function moveItem<T>(arr: T[], from: number, to: number): T[] {
  if (from === to || from < 0 || to < 0 || from >= arr.length || to >= arr.length) {
    return arr;
  }
  const next = arr.slice();
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item);
  return next;
}
