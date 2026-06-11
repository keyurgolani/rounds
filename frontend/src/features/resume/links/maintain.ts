import type { ResumeData, WorkExperience, Project } from '../types';
import type { EntryLink, ResumeLinks } from './types';

export function addBullet(link: EntryLink): EntryLink {
  return { ...link, bulletRefs: [...link.bulletRefs, null], bulletEdited: [...link.bulletEdited, false] };
}
export function removeBulletAt(link: EntryLink, i: number): EntryLink {
  return { ...link, bulletRefs: link.bulletRefs.filter((_, j) => j !== i), bulletEdited: link.bulletEdited.filter((_, j) => j !== i) };
}
export function moveBullet(link: EntryLink, from: number, to: number): EntryLink {
  const move = <X,>(arr: X[]) => { const a = arr.slice(); const [x] = a.splice(from, 1); a.splice(to, 0, x); return a; };
  return { ...link, bulletRefs: move(link.bulletRefs), bulletEdited: move(link.bulletEdited) };
}
/** Mark highlight i as edited (detached). No-op flag on a null-ref row is harmless. */
export function editBulletAt(link: EntryLink, i: number): EntryLink {
  if (!link.bulletEdited[i]) {
    const bulletEdited = link.bulletEdited.slice(); bulletEdited[i] = true;
    return { ...link, bulletEdited };
  }
  return link;
}

/** Reconcile a link's bullet arrays to a wholesale-replaced highlights list
 *  (e.g. field-level AI improve). Aligns array lengths to `next`, keeps refs
 *  for surviving indices, marks any index whose text changed as edited, and
 *  treats appended rows as manual (null ref). */
export function reconcileHighlightLinks(prev: string[], next: string[], link: EntryLink): EntryLink {
  const bulletRefs: (string | null)[] = [];
  const bulletEdited: boolean[] = [];
  for (let i = 0; i < next.length; i++) {
    if (i < prev.length) {
      bulletRefs[i] = link.bulletRefs[i] ?? null;
      bulletEdited[i] = (link.bulletEdited[i] ?? false) || next[i] !== prev[i];
    } else {
      bulletRefs[i] = null;
      bulletEdited[i] = false;
    }
  }
  return { ...link, bulletRefs, bulletEdited };
}

const HEADER_KEYS_EXP: (keyof WorkExperience)[] = ['company', 'position', 'location', 'startDate', 'endDate', 'current', 'description'];
const HEADER_KEYS_PROJ: (keyof Project)[] = ['name', 'description', 'technologies', 'startDate', 'endDate'];

/** After a wholesale data replace (AI tailor / ATS), flag any linked header or
 *  bullet that changed value so library sync won't overwrite the tailored text. */
export function markEdits(prev: ResumeData, next: ResumeData, links: ResumeLinks): ResumeLinks {
  const out: ResumeLinks = { experience: { ...links.experience }, projects: { ...links.projects } };
  markSection(prev.experience, next.experience, out.experience, HEADER_KEYS_EXP as string[]);
  markSection(prev.projects, next.projects, out.projects, HEADER_KEYS_PROJ as string[]);
  return out;
}

function markSection(
  prevList: { id: string; highlights: string[] }[],
  nextList: { id: string; highlights: string[] }[],
  linkMap: Record<string, EntryLink>,
  headerKeys: string[],
) {
  const prevById = new Map(prevList.map((e) => [e.id, e as unknown as Record<string, unknown>]));
  for (const entry of nextList as unknown as Record<string, unknown>[]) {
    const id = entry.id as string;
    const link = linkMap[id];
    if (!link || link.ref === null) continue;
    const before = prevById.get(id);
    if (!before) continue;
    let l = link;
    if (!l.headerEdited && headerKeys.some((k) => JSON.stringify(before[k]) !== JSON.stringify(entry[k]))) {
      l = { ...l, headerEdited: true };
    }
    const nextHl = entry.highlights as string[];
    const prevHl = before.highlights as string[];
    const bulletEdited = l.bulletEdited.slice();
    let bChanged = false;
    for (let i = 0; i < bulletEdited.length; i++) {
      if (l.bulletRefs[i] !== null && !bulletEdited[i] && nextHl[i] !== prevHl[i]) { bulletEdited[i] = true; bChanged = true; }
    }
    if (bChanged) l = { ...l, bulletEdited };
    if (l !== link) linkMap[id] = l;
  }
}
