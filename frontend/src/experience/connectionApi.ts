import type { RecordModel } from 'pocketbase';
import { pb } from '../lib/pocketbase';
import type { EntityKind } from './experienceApi';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** The 6 junction tables that store parent-child relationships. */
export type JunctionTable =
  | 'exp_job_projects'
  | 'exp_job_anecdotes'
  | 'exp_job_bullets'
  | 'exp_project_anecdotes'
  | 'exp_project_bullets'
  | 'exp_anecdote_bullets';

/** A single connection row between a parent entity and a child entity. */
export interface Connection {
  id: string;
  junctionTable: JunctionTable;
  parentId: string;
  childId: string;
}

/**
 * Maps parent ID -> { childKind -> childIds[] }.
 * Useful for answering "what children does this entity have?"
 */
export type ConnectionMap = Record<string, Record<EntityKind, string[]>>;

/**
 * Maps child ID -> { parentKind -> parentIds[] }.
 * Useful for answering "what parents does this entity belong to?"
 */
export type ReverseConnectionMap = Record<string, Record<EntityKind, string[]>>;

// ---------------------------------------------------------------------------
// Hierarchy rules
// ---------------------------------------------------------------------------

/**
 * Defines which child kinds each parent kind may have.
 *
 * Job -> project, anecdote, bullet
 * Project -> anecdote, bullet
 * Anecdote -> bullet
 * Bullet -> (leaf, no children)
 */
const VALID_CHILDREN: Record<EntityKind, EntityKind[]> = {
  job: ['project', 'anecdote', 'bullet'],
  project: ['anecdote', 'bullet'],
  anecdote: ['bullet'],
  bullet: [],
};

/**
 * Maps (parentKind, childKind) to the junction table name.
 * Constructed from VALID_CHILDREN to ensure consistency.
 */
const JUNCTION_MAP: Record<string, JunctionTable> = {};

const PARENT_PREFIX: Record<EntityKind, string> = {
  job: 'exp_job',
  project: 'exp_project',
  anecdote: 'exp_anecdote',
  bullet: 'exp_bullet',
};

const CHILD_SUFFIX: Record<EntityKind, string> = {
  project: 'projects',
  anecdote: 'anecdotes',
  bullet: 'bullets',
  job: '', // unreachable — job is never a child
};

// Build the junction table map from VALID_CHILDREN.
for (const [parentKind, childKinds] of Object.entries(VALID_CHILDREN)) {
  for (const childKind of childKinds) {
    const key = `${parentKind}->${childKind}`;
    JUNCTION_MAP[key] = `${PARENT_PREFIX[parentKind as EntityKind]}_${CHILD_SUFFIX[childKind]}` as JunctionTable;
  }
}

// ---------------------------------------------------------------------------
// Helper functions
// ---------------------------------------------------------------------------

/**
 * Returns the junction table name for a valid (parentKind, childKind) pair,
 * or null if the pair is not allowed by the hierarchy rules.
 */
export function getJunctionTable(parentKind: EntityKind, childKind: EntityKind): JunctionTable | null {
  return JUNCTION_MAP[`${parentKind}->${childKind}`] ?? null;
}

/** Returns the child entity kinds that a given parent kind may have. */
export function validChildKinds(parentKind: EntityKind): EntityKind[] {
  return VALID_CHILDREN[parentKind];
}

/** Returns the parent entity kinds that a given child kind may belong to. */
export function validParentKinds(childKind: EntityKind): EntityKind[] {
  const parents: EntityKind[] = [];
  for (const [parent, children] of Object.entries(VALID_CHILDREN)) {
    if (children.includes(childKind)) {
      parents.push(parent as EntityKind);
    }
  }
  return parents;
}

// ---------------------------------------------------------------------------
// Internals
// ---------------------------------------------------------------------------

interface JunctionRow extends RecordModel {
  user: string;
  parent: string;
  child: string;
}

function userId(): string {
  const id = pb.authStore.record?.id;
  if (!id) throw new Error('Not authenticated');
  return id;
}

function ownerFilter() {
  return `user = "${userId()}"`;
}

function adaptConnection(junctionTable: JunctionTable, r: JunctionRow): Connection {
  return {
    id: r.id,
    junctionTable,
    parentId: r.parent,
    childId: r.child,
  };
}

// ---------------------------------------------------------------------------
// Read functions
// ---------------------------------------------------------------------------

/**
 * Loads all connections across all 6 junction tables for the current user.
 */
export async function listAllConnections(): Promise<Connection[]> {
  const tables = Object.values(JUNCTION_MAP) as JunctionTable[];
  const results = await Promise.all(
    tables.map(async (table) => {
      const rows = await pb.collection<JunctionRow>(table).getFullList({
        filter: ownerFilter(),
      });
      return rows.map((r) => adaptConnection(table, r));
    }),
  );
  return results.flat();
}

/**
 * Builds a forward map: parentId -> { childKind -> childIds[] }.
 */
export function buildConnectionMap(connections: Connection[]): ConnectionMap {
  const map: ConnectionMap = {};
  for (const conn of connections) {
    // Derive the child kind from the junction table name.
    const childKind = childKindFromTable(conn.junctionTable);
    if (!map[conn.parentId]) {
      map[conn.parentId] = {} as Record<EntityKind, string[]>;
    }
    if (!map[conn.parentId][childKind]) {
      map[conn.parentId][childKind] = [];
    }
    map[conn.parentId][childKind].push(conn.childId);
  }
  return map;
}

/**
 * Builds a reverse map: childId -> { parentKind -> parentIds[] }.
 */
export function buildReverseMap(connections: Connection[]): ReverseConnectionMap {
  const map: ReverseConnectionMap = {};
  for (const conn of connections) {
    const parentKind = parentKindFromTable(conn.junctionTable);
    if (!map[conn.childId]) {
      map[conn.childId] = {} as Record<EntityKind, string[]>;
    }
    if (!map[conn.childId][parentKind]) {
      map[conn.childId][parentKind] = [];
    }
    map[conn.childId][parentKind].push(conn.parentId);
  }
  return map;
}

// ---------------------------------------------------------------------------
// Write functions
// ---------------------------------------------------------------------------

/**
 * Creates a junction row linking parent to child.
 * Throws if the (parentKind, childKind) pair is not in the hierarchy.
 */
export async function createConnection(
  parentKind: EntityKind,
  parentId: string,
  childKind: EntityKind,
  childId: string,
): Promise<Connection> {
  const table = getJunctionTable(parentKind, childKind);
  if (!table) {
    throw new Error(`Invalid connection: ${parentKind} cannot have ${childKind} as a child`);
  }
  const row = await pb.collection<JunctionRow>(table).create({
    user: userId(),
    parent: parentId,
    child: childId,
  });
  return adaptConnection(table, row);
}

/**
 * Deletes a junction row identified by its Connection object.
 */
export async function deleteConnection(connection: Connection): Promise<void> {
  await pb.collection<JunctionRow>(connection.junctionTable).delete(connection.id);
}

/**
 * Creates multiple connections in parallel (used during import).
 */
export async function batchCreateConnections(
  pairs: Array<{ parentKind: EntityKind; parentId: string; childKind: EntityKind; childId: string }>,
): Promise<Connection[]> {
  return Promise.all(
    pairs.map((p) => createConnection(p.parentKind, p.parentId, p.childKind, p.childId)),
  );
}

// ---------------------------------------------------------------------------
// Internal utilities
// ---------------------------------------------------------------------------

/** Derives the child entity kind from a junction table name. */
function childKindFromTable(table: JunctionTable): EntityKind {
  if (table.endsWith('_projects')) return 'project';
  if (table.endsWith('_anecdotes')) return 'anecdote';
  if (table.endsWith('_bullets')) return 'bullet';
  throw new Error(`Unknown junction table: ${table}`);
}

/** Derives the parent entity kind from a junction table name. */
function parentKindFromTable(table: JunctionTable): EntityKind {
  if (table.startsWith('exp_job_')) return 'job';
  if (table.startsWith('exp_project_')) return 'project';
  if (table.startsWith('exp_anecdote_')) return 'anecdote';
  throw new Error(`Unknown junction table: ${table}`);
}
