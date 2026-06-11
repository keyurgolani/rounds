// frontend/src/experience/arrangeMetadata.ts
//
// Pure helpers for the Arrange board: per-entity link counts (for the count
// badge) and the "unfiled" rule (for the orphan flag). Kept separate from the
// React components so the logic is unit-testable.
import type { EntityKind } from './experienceApi';

export interface LinkMeta {
  /** Incoming links (this entity is the child). */
  parents: number;
  /** Outgoing links (this entity is the parent). */
  children: number;
  /** parents + children. */
  total: number;
}

type Edge = { parentId: string; childId: string };

/** Builds a per-entity-id link tally from the flat connection list. */
export function linkMetaByEntity(connections: Edge[]): Record<string, LinkMeta> {
  const meta: Record<string, LinkMeta> = {};
  const slot = (id: string): LinkMeta => (meta[id] ??= { parents: 0, children: 0, total: 0 });
  for (const c of connections) {
    const p = slot(c.parentId);
    p.children += 1;
    p.total += 1;
    const child = slot(c.childId);
    child.parents += 1;
    child.total += 1;
  }
  return meta;
}

/**
 * "Unfiled" = a gap in the source-of-truth library.
 * Jobs are roots, so a job is unfiled only when it has no children; every
 * other kind is unfiled when it has no parent.
 */
export function isUnfiled(kind: EntityKind, meta: LinkMeta | undefined): boolean {
  const m = meta ?? { parents: 0, children: 0, total: 0 };
  return kind === 'job' ? m.children === 0 : m.parents === 0;
}
