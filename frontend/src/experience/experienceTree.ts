// frontend/src/experience/experienceTree.ts
//
// Pure, presentational helpers shared by the Experience Timeline tree and the
// List tab's nested cards. No React, no side effects — just shape the data and
// the per-kind / per-depth styling tokens.
import type { ConnectionMap } from './connectionApi';
import type { TimelineEntity, EntityKind } from './experienceApi';

export const TYPE_COLORS: Record<TimelineEntity['kind'], { bg: string; text: string; dot: string }> = {
  anecdote: { bg: 'var(--accent-soft)', text: 'var(--accent)', dot: 'var(--accent)' },
  bullet: { bg: 'var(--forest-soft)', text: 'var(--forest)', dot: 'var(--forest)' },
  project: { bg: 'var(--ochre-soft)', text: 'var(--ochre)', dot: 'var(--ochre)' },
  job: { bg: 'var(--ink-soft)', text: 'var(--ink)', dot: 'var(--ink)' },
};

export const TYPE_LABELS: Record<TimelineEntity['kind'], string> = {
  anecdote: 'Anecdote',
  bullet: 'Bullet',
  project: 'Project',
  job: 'Job',
};

// Child kinds in render order — the more granular, the more minimal the card.
export const CHILD_KINDS: EntityKind[] = ['project', 'anecdote', 'bullet'];

// Per-depth card sizing. `pt` is the top padding; the Timeline also uses it to
// align connectors to the badge/title row.
export const DEPTH = [
  { padding: '15px 18px', pt: 15, title: 16 },
  { padding: '11px 15px', pt: 11, title: 14 },
  { padding: '9px 13px', pt: 9, title: 13 },
  { padding: '8px 12px', pt: 8, title: 12.5 },
] as const;
export const depthCfg = (d: number) => DEPTH[Math.min(d, DEPTH.length - 1)];

export function entityDate(e: TimelineEntity): string {
  return e.kind === 'job' || e.kind === 'project' ? e.start_date : e.date;
}

export function childIdsOf(map: ConnectionMap, parentId: string): { kind: EntityKind; id: string }[] {
  const entry = map[parentId];
  if (!entry) return [];
  return CHILD_KINDS.flatMap((kind) => (entry[kind] ?? []).map((id) => ({ kind, id })));
}

export function hasChildren(map: ConnectionMap, parentId: string): boolean {
  const entry = map[parentId];
  if (!entry) return false;
  return CHILD_KINDS.some((kind) => (entry[kind] ?? []).length > 0);
}

/**
 * Newest date (epoch ms) anywhere in an entity's subtree. Children can be newer
 * than their (often older) parent, so a subtree sorts by its newest descendant.
 */
export function subtreeMaxDate(
  id: string,
  connMap: ConnectionMap,
  entityById: Record<string, TimelineEntity>,
  ancestry: Set<string> = new Set(),
): number {
  const e = entityById[id];
  if (!e) return 0;
  let max = +new Date(entityDate(e));
  for (const { id: childId } of childIdsOf(connMap, id)) {
    if (ancestry.has(childId)) continue;
    const d = subtreeMaxDate(childId, connMap, entityById, new Set(ancestry).add(id));
    if (d > max) max = d;
  }
  return max;
}

export function formatDate(entity: TimelineEntity): string {
  if (entity.kind === 'job' || entity.kind === 'project') {
    const s = new Date(entity.start_date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    if (!entity.end_date) return `${s} – Present`;
    const e = new Date(entity.end_date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    return `${s} – ${e}`;
  }
  return new Date(entity.date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
}

export function rowTitle(entity: TimelineEntity): string {
  return entity.kind === 'job' ? (entity.company || 'Untitled') : (entity.title || 'Untitled');
}

export function rowSubtitle(entity: TimelineEntity): string | undefined {
  switch (entity.kind) {
    case 'job': return entity.role || undefined;
    case 'project': return [entity.company, entity.role].filter(Boolean).join(' · ') || undefined;
    case 'anecdote': return (entity.result || entity.situation || '').slice(0, 90) || undefined;
    case 'bullet': return entity.impact || undefined;
    default: return undefined;
  }
}
