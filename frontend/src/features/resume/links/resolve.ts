import type { ResumeData, WorkExperience, Project } from '../types';
import type { ResumeLinks, EntryLink } from './types';
import type { ExperienceJob, ExperienceProject, ExperienceBullet } from '../../../experience/experienceApi';

export interface LibrarySnapshot {
  jobs: Record<string, ExperienceJob>;
  projects: Record<string, ExperienceProject>;
  bullets: Record<string, ExperienceBullet>;
}

/** 'YYYY-MM-DD' -> 'YYYY-MM'; null/'' -> ''. */
export function toYM(date: string | null | undefined): string {
  if (!date) return '';
  return date.slice(0, 7);
}

interface Resolved { data: ResumeData; links: ResumeLinks; changed: boolean; }

export function resolveAndSync(data: ResumeData, links: ResumeLinks, lib: LibrarySnapshot): Resolved {
  let changed = false;
  const nextLinks: ResumeLinks = { experience: { ...links.experience }, projects: { ...links.projects } };

  const experience = data.experience.map((entry) => {
    const link = links.experience[entry.id];
    if (!link) return entry;
    const [e2, l2, c] = resolveEntry(entry, link, lib, 'job');
    if (c) { changed = true; nextLinks.experience[entry.id] = l2; }
    return e2 as WorkExperience;
  });

  const projects = data.projects.map((entry) => {
    const link = links.projects[entry.id];
    if (!link) return entry;
    const [p2, l2, c] = resolveEntry(entry, link, lib, 'project');
    if (c) { changed = true; nextLinks.projects[entry.id] = l2; }
    return p2 as Project;
  });

  return { data: { ...data, experience, projects }, links: nextLinks, changed };
}

function resolveEntry<T extends WorkExperience | Project>(
  entry: T, link: EntryLink, lib: LibrarySnapshot, kind: 'job' | 'project',
): [T, EntryLink, boolean] {
  let changed = false;
  let nextEntry: T = entry;
  let nextLink: EntryLink = link;

  if (link.ref !== null) {
    const item = kind === 'job' ? lib.jobs[link.ref] : lib.projects[link.ref];
    if (!item) {
      nextLink = { ...nextLink, ref: null }; changed = true;
    } else if (!link.headerEdited) {
      const header = kind === 'job'
        ? jobHeader(item as ExperienceJob)
        : projectHeader(item as ExperienceProject);
      if (differs(entry as Record<string, unknown>, header as Record<string, unknown>)) {
        nextEntry = { ...nextEntry, ...header }; changed = true;
      }
    }
  }

  const bulletRefs = nextLink.bulletRefs.slice();
  const highlights = nextEntry.highlights.slice();
  let bulletsChanged = false;
  // Clamp to highlights.length so the resolver can never grow `highlights`
  // even when bulletRefs is longer (e.g. after a field-level AI-improve desync).
  for (let i = 0; i < Math.min(bulletRefs.length, highlights.length); i++) {
    const ref = bulletRefs[i];
    if (ref === null) continue;
    const bullet = lib.bullets[ref];
    if (!bullet) { bulletRefs[i] = null; bulletsChanged = true; continue; }
    if (nextLink.bulletEdited[i]) continue;
    if (highlights[i] !== bullet.title) { highlights[i] = bullet.title; bulletsChanged = true; }
  }
  if (bulletsChanged) {
    changed = true;
    nextEntry = { ...nextEntry, highlights };
    nextLink = { ...nextLink, bulletRefs };
  }

  return [nextEntry, nextLink, changed];
}

export function jobHeader(j: ExperienceJob): Partial<WorkExperience> {
  return {
    company: j.company, position: j.role, location: j.location,
    startDate: toYM(j.start_date), endDate: toYM(j.end_date), current: j.end_date == null,
    description: j.description,
  };
}
export function projectHeader(p: ExperienceProject): Partial<Project> {
  return {
    name: p.title, description: p.description, technologies: p.tech_stack,
    startDate: toYM(p.start_date), endDate: toYM(p.end_date),
  };
}

// --- inverse mappers (push-to-library): resume header -> library fields ---
// These intentionally cover only the library-backed subset; PocketBase .update()
// uses partial semantics so omitted columns are left unchanged — but extending
// the mapper to cover all columns is the safe way to add new fields.
/** 'YYYY-MM' -> 'YYYY-MM-01'; '' -> ''. Inverse of toYM (day precision is lost). */
export function toMD(ym: string | null | undefined): string {
  if (!ym) return '';
  return ym.length === 7 ? `${ym}-01` : ym;
}
export function jobHeaderBack(e: WorkExperience): Partial<ExperienceJob> {
  return {
    company: e.company, role: e.position, location: e.location ?? '',
    start_date: toMD(e.startDate), end_date: e.current ? null : (toMD(e.endDate) || null),
    description: e.description ?? '',
  };
}
export function projectHeaderBack(p: Project): Partial<ExperienceProject> {
  return {
    title: p.name, description: p.description ?? '', tech_stack: p.technologies ?? [],
    start_date: toMD(p.startDate), end_date: toMD(p.endDate) || null,
  };
}

function differs(entry: Record<string, unknown>, header: Record<string, unknown>): boolean {
  return Object.keys(header).some((k) => JSON.stringify(entry[k]) !== JSON.stringify(header[k]));
}
