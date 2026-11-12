// The canonical database's ERD (ROUNDS-02-L01, DR-0004).
//
// contracts/database/erd.json has two kinds of fields. The mechanical ones
// (each live collection's fields count, indexes, rule classes, partition,
// and each relation's cardinality, flags, and delete behavior) are rebuilt
// from contracts/database/schema-snapshot.json, PocketBase's own schema from
// a native `migrate up` (harness/bench/schema_dump.py). The written ones
// (group, scope, rows, writers, purge, owningLeaf, createdBy, note, and each
// relation's merge) are kept across regeneration, as #16's baseline stores
// keep their rows. Planned and held entities are written by hand.

import { finding, jsonLine } from '../context.mjs';
import { validate } from '../json-schema.mjs';
import { extractCollections } from '../vocabulary/coverage.mjs';
import { sha256 } from '../context.mjs';

export const ERD_PATH = 'contracts/database/erd.json';
export const ERD_SCHEMA_PATH = 'contracts/database/erd.schema.json';
export const SNAPSHOT_PATH = 'contracts/database/schema-snapshot.json';
export const SNAPSHOT_SCHEMA_PATH = 'contracts/database/schema-snapshot.schema.json';
export const ENDPOINTS_PATH = 'pocketbase/pb_hooks/relation_endpoints.v1.json';
export const BASELINE_STORES_PATH = 'contracts/authority/baseline-stores.json';
const MIGRATIONS_DIR = 'pocketbase/pb_migrations/';

const KEEP_ENTITY = ['group', 'scope', 'rows', 'writers', 'purge', 'owningLeaf', 'createdBy', 'note'];
const KEEP_RELATION = ['merge', 'note'];
const OWNER_FIELDS = ['user', 'account'];

export const DEFAULT_STORES = [
  { id: 'sqlite-data', kind: 'sqlite', location: 'pb_data/data.db', process: 'pocketbase', canonical: true,
    backup: 'an online SQLite-consistent copy (decision 8)', description: 'The one canonical write database: every collection below, written on PocketBase\'s single write connection.' },
  { id: 'files', kind: 'files', location: 'pb_data/storage', process: 'pocketbase', canonical: true,
    backup: 'copied after the database copy; deletes wait for the backup (decision 8)', description: 'File fields\' bytes, under one directory per collection and record.' },
  { id: 'sqlite-logs', kind: 'sqlite', location: 'pb_data/logs.db', process: 'pocketbase', canonical: false,
    backup: 'not needed for a restore', description: 'PocketBase\'s request log. Not canonical data, and never a source for a read model.' },
];

export const DEFAULT_GROUPS = [
  { id: 'account', title: 'Account, preferences, and AI settings' },
  { id: 'pipeline', title: 'Campaigns, applications, rounds, offers, and todos' },
  { id: 'experience', title: 'Experience records and their junctions' },
  { id: 'materials', title: 'Resumes, versions, snapshots, and shares' },
  { id: 'practice', title: 'Practice drafts, attempts, progress, and content' },
  { id: 'containment', title: 'Admission, execution, quarantine, and share secrets' },
  { id: 'platform', title: 'Platform tables DR-0004 places' },
  { id: 'system', title: 'PocketBase system tables' },
];

export function deleteBehavior(rel, measured) {
  if (rel.cascadeDelete) return measured?.['single-required-cascade'] || 'cascade';
  if (rel.required) return measured?.['single-required-no-cascade'] || 'restrict';
  return (rel.maxSelect === 1 ? measured?.['single-optional-no-cascade'] : measured?.['multi-optional-no-cascade']) || 'unset';
}

function partitionOf(collection) {
  if (collection.name === 'users') return { field: 'id', kind: 'self', onAccountDelete: 'pocketbase' };
  const owner = collection.fields.find((f) => f.type === 'relation' && f.relation.collection === 'users' && OWNER_FIELDS.includes(f.name));
  if (!owner) return null;
  return { field: owner.name, kind: 'relation', onAccountDelete: deleteBehavior({ ...owner.relation, required: owner.required }, null) };
}

function leading(indexes, field) {
  return indexes.some((i) => (i.columns[0] || '').split('.').pop() === field);
}

function keep(previous, next, keys) {
  if (!previous) return next;
  const out = { ...next };
  for (const k of keys) if (previous[k] !== undefined && out[k] === undefined) out[k] = previous[k];
  return out;
}

// Builds erd.json from the snapshot, keeping written fields and every
// planned or held entry of the previous file.
export function buildErd(snapshot, previous, endpoints, baselineStores, record) {
  const prevEntities = new Map((previous?.entities || []).map((e) => [e.id, e]));
  const prevRelations = new Map((previous?.relations || []).map((r) => [r.id, r]));
  const authorized = new Set((endpoints?.fields || []).map((f) => `${f.collection}.${f.field}`));
  const content = new Set((snapshot.collections || []).filter((c) => !partitionOf(c) && c.rules.list === 'expression' && c.rules.create === 'null').map((c) => c.name));
  const baselineRows = new Map((baselineStores?.stores || []).filter((s) => s.kind === 'collection').map((s) => [s.name, s.rows || []]));
  const measured = snapshot.relationDeleteSemantics || {};
  const entities = [];
  const relations = [];
  for (const c of snapshot.collections) {
    const partition = partitionOf(c);
    const bytes = c.fields.some((f) => f.type === 'file');
    const prev = prevEntities.get(c.name);
    const base = {
      id: c.name,
      status: 'live',
      kind: 'collection',
      type: c.type,
      store: 'sqlite-data',
      bytes,
      group: prev?.group,
      scope: prev?.scope,
      partition: prev?.partition && prev.partition.kind === 'text' ? prev.partition : partition,
      partitionIndexed: partition ? (partition.kind === 'self' ? true : leading(c.indexes, partition.field)) : false,
      fields: c.fields.length,
      indexes: c.indexes.map((i) => ({ name: i.name, unique: i.unique, columns: i.columns, ...(i.partial ? { partial: true } : {}) })),
      rules: c.rules,
    };
    if (prev?.partition?.kind === 'text') base.partitionIndexed = leading(c.indexes, prev.partition.field);
    const rows = prev?.rows || baselineRows.get(c.name);
    const entity = keep(prev, base, KEEP_ENTITY);
    if (rows && rows.length && !entity.rows) entity.rows = rows;
    entities.push(entity);
    for (const f of c.fields.filter((x) => x.type === 'relation')) {
      const id = `${c.name}.${f.name}`;
      const target = f.relation.collection;
      const authorization = target === 'users' ? 'owner' : authorized.has(id) ? 'relation-endpoint' : content.has(target) ? 'content' : 'server';
      relations.push(keep(prevRelations.get(id), {
        id, status: 'live', from: c.name, field: f.name, to: target,
        cardinality: f.relation.maxSelect === 1 ? 'many-to-one' : 'many-to-many',
        required: f.required, cascadeDelete: f.relation.cascadeDelete,
        onDelete: deleteBehavior({ ...f.relation, required: f.required }, measured),
        merge: undefined, authorization,
      }, KEEP_RELATION));
    }
  }
  for (const t of snapshot.systemTables || []) {
    const prev = prevEntities.get(t);
    entities.push(keep(prev, { id: t, status: 'live', kind: 'system-table', store: 'sqlite-data', group: 'system', scope: prev?.scope,
      partition: prev?.partition ?? null }, KEEP_ENTITY));
  }
  const live = new Set(entities.map((e) => e.id));
  for (const e of previous?.entities || []) if (e.status !== 'live' && !live.has(e.id)) entities.push(e);
  for (const r of previous?.relations || []) if (r.status !== 'live' && !relations.some((x) => x.id === r.id)) relations.push(r);
  for (const e of entities) for (const k of Object.keys(e)) if (e[k] === undefined) delete e[k];
  for (const r of relations) for (const k of Object.keys(r)) if (r[k] === undefined) delete r[k];
  const order = (a, b) => (a.status === b.status ? 0 : a.status === 'live' ? -1 : 1) || a.id.localeCompare(b.id);
  return {
    $schema: './erd.schema.json',
    registry: 'rounds-erd',
    decisionRecord: record?.id || previous?.decisionRecord || 'DR-0004',
    revision: record?.revision || previous?.revision || 1,
    description: 'DR-0004\'s ERD: every PocketBase collection and system table at the snapshot\'s revision, the platform tables and stores DR-0004 places, and every relation with its cardinality, account partition, delete behavior, merge behavior, and indexes. The mechanical fields come from schema-snapshot.json through node scripts/conformance/run.mjs --write; the written fields are kept.',
    snapshot: { path: SNAPSHOT_PATH, revision: snapshot.revision.commit, pocketbaseVersion: snapshot.pocketbaseVersion },
    semantics: {
      cascade: 'Deleting the target deletes this row in the same transaction.',
      restrict: 'Deleting the target is refused while this row points at it.',
      unset: 'Deleting the target removes its id from this field and keeps the row.',
      measured,
    },
    stores: previous?.stores || DEFAULT_STORES,
    groups: previous?.groups || DEFAULT_GROUPS,
    entities: entities.sort(order),
    relations: relations.sort(order),
  };
}

const push = (findings, code, file, text, parts, message) => findings.push(finding(code, file, text ? jsonLine(text, parts) : 1, message));

// Checks the ERD on its own and against the snapshot, the migrations on the
// tree, and the leaf registry.
export function checkErd(ctx, { erd, erdText, schema, snapshot, resolveLeaf, record }) {
  const findings = [];
  const f = (code, parts, message) => push(findings, code, ERD_PATH, erdText, parts, message);
  for (const err of validate(erd, schema)) {
    // A relation without delete or merge behavior is DB_ERD_DELETE_MISSING, reported below.
    if (err.keyword === 'required' && /^\/relations\/\d+$/.test(err.pointer) && ['onDelete', 'merge'].includes(err.property)) continue;
    f(err.keyword === 'required' ? 'DB_ERD_INCOMPLETE' : 'DB_ERD_INVALID', err.pointer.split('/').slice(1), `${err.pointer || '/'} ${err.message}`);
  }
  const stores = new Set((erd.stores || []).map((s) => s.id));
  const groups = new Set((erd.groups || []).map((g) => g.id));
  const ids = new Map();
  (erd.entities || []).forEach((e, i) => {
    if (ids.has(e.id)) f('DB_TWO_AUTHORITIES', ['entities', i, 'id'], `${e.id} is listed twice; one entity has one store and one owner`);
    ids.set(e.id, e);
    if (e.store && !stores.has(e.store)) f('DB_UNKNOWN_REF', ['entities', i, 'store'], `${e.id} names store ${e.store}, which the ERD doesn't list`);
    if (e.group && !groups.has(e.group)) f('DB_UNKNOWN_REF', ['entities', i, 'group'], `${e.id} names group ${e.group}, which the ERD doesn't list`);
    if (e.owningLeaf) {
      const r = resolveLeaf(e.owningLeaf);
      if (!r.ok) f('DB_UNKNOWN_REF', ['entities', i, 'owningLeaf'], `${e.id} owning leaf: ${r.reason}`);
    }
    if (e.scope === 'account' && !e.partition) f('DB_ERD_INCOMPLETE', ['entities', i, 'partition'], `${e.id} holds account data but names no partition column`);
    if (e.bytes && !stores.has('files')) f('DB_ERD_INCOMPLETE', ['entities', i, 'bytes'], `${e.id} holds bytes, but the ERD lists no file store`);
  });
  (erd.relations || []).forEach((r, i) => {
    if (!r.onDelete) f('DB_ERD_DELETE_MISSING', ['relations', i], `${r.id} has no delete behavior`);
    if (!r.merge) f('DB_ERD_DELETE_MISSING', ['relations', i], `${r.id} has no merge behavior`);
    for (const end of ['from', 'to']) if (r[end] && !ids.has(r[end])) f('DB_UNKNOWN_REF', ['relations', i, end], `${r.id} ${end} ${r[end]} is not an entity in the ERD`);
  });
  if (snapshot) {
    for (const c of snapshot.collections || []) {
      const e = ids.get(c.name);
      if (!e) { f('DB_ERD_UNCOVERED', ['entities'], `${c.name} is a collection in ${SNAPSHOT_PATH} with no ERD entity`); continue; }
      if (e.status !== 'live') f('DB_ERD_INVALID', ['entities'], `${c.name} is live in the snapshot but ${e.status} in the ERD`);
    }
    if (erd.snapshot?.revision && erd.snapshot.revision !== snapshot.revision?.commit) {
      f('DB_VERSION_MISMATCH', ['snapshot', 'revision'], `the ERD was built from snapshot ${erd.snapshot.revision.slice(0, 7)}, but ${SNAPSHOT_PATH} is ${String(snapshot.revision?.commit).slice(0, 7)}; run node scripts/conformance/run.mjs --write`);
    }
    // Migrations the snapshot didn't see: what they create must be in the ERD.
    const seen = new Map((snapshot.migrations || []).map((m) => [m.file, m.sha256]));
    const changed = ctx.files().filter((p) => p.startsWith(MIGRATIONS_DIR) && p.endsWith('.js'))
      .filter((p) => seen.get(p.slice(MIGRATIONS_DIR.length)) !== sha256(ctx.read(p)));
    if (changed.length) {
      const extracted = extractCollections(ctx);
      for (const item of extracted.items) {
        if (item.historical || !changed.includes(item.path)) continue;
        if (!ids.has(item.name)) push(findings, 'DB_ERD_UNCOVERED', item.path, null, [], `${item.path}:${item.line} creates ${item.name}, which has no ERD entity; add it, or regenerate the snapshot with harness/bench/schema_dump.py`);
      }
      for (const ev of extracted.unresolved) {
        if (changed.includes(ev.path)) push(findings, 'DB_ERD_UNRESOLVED', ev.path, null, [], `${ev.path}:${ev.line} creates a collection whose name isn't a literal; name it, or regenerate the snapshot with harness/bench/schema_dump.py`);
      }
    }
  }
  if (record && erd.decisionRecord !== record.id) f('DB_VERSION_MISMATCH', ['decisionRecord'], `the ERD names ${erd.decisionRecord}, not ${record.id}`);
  if (record && erd.revision !== record.revision) f('DB_VERSION_MISMATCH', ['revision'], `the ERD is at revision ${erd.revision}; ${record.id} is at ${record.revision}, and they share one counter`);
  return findings;
}

const MERMAID_CARD = {
  'many-to-one': (r) => `${r.required ? '||' : '|o'}--o{`,
  'many-to-many': () => '}o--o{',
};

export function renderMermaid(erd, group) {
  const members = new Set(erd.entities.filter((e) => e.group === group).map((e) => e.id));
  const lines = ['```mermaid', 'erDiagram'];
  const rels = erd.relations.filter((r) => members.has(r.from));
  for (const r of rels) lines.push(`  ${r.to} ${MERMAID_CARD[r.cardinality](r)} ${r.from} : "${r.field} (${r.onDelete}${r.status === 'live' ? '' : `, ${r.status}`})"`);
  const drawn = new Set(rels.flatMap((r) => [r.from, r.to]));
  for (const id of members) if (!drawn.has(id)) lines.push(`  ${id}`);
  lines.push('```');
  return lines.join('\n');
}
