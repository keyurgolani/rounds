import type { EntityKind } from './experienceApi';
import { getJunctionTable } from './connectionApi';

/** Hierarchy depth — a lower number may parent a higher one. */
const HIERARCHY: Record<EntityKind, number> = { job: 0, project: 1, anecdote: 2, bullet: 3 };

export interface OrderedPair {
  parentKind: EntityKind;
  parentId: string;
  childKind: EntityKind;
  childId: string;
}

/**
 * True when `parentKind` may directly parent `childKind` in the hierarchy
 * (and so a junction table exists for that ordered pair).
 */
export function canParent(parentKind: EntityKind, childKind: EntityKind): boolean {
  return getJunctionTable(parentKind, childKind) !== null;
}

/**
 * Orders two entities into a (parent, child) pair by hierarchy and validates that
 * the pair maps to a real junction table. Returns null for invalid pairs
 * (same kind, or a combination with no junction such as bullet→job).
 */
export function orderedValidPair(
  aKind: EntityKind,
  aId: string,
  bKind: EntityKind,
  bId: string,
): OrderedPair | null {
  if (aKind === bKind) return null;
  const [parentKind, parentId, childKind, childId] =
    HIERARCHY[aKind] < HIERARCHY[bKind]
      ? [aKind, aId, bKind, bId]
      : [bKind, bId, aKind, aId];
  if (!getJunctionTable(parentKind, childKind)) return null;
  return { parentKind, parentId, childKind, childId };
}
