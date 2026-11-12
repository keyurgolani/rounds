// The canonical database's ERD (ROUNDS-02-L01, DR-0004).
//
// The ERD has two parts. The written part, contracts/database/erd-decisions.json,
// is DR-0004's own and ratified with it: the delete and merge values, the
// stores, the groups, each entity's written fields (group, scope, rows,
// writers, purge, a partition the schema can't show, note), every planned or
// held table in full with its indexes, and each relation's merge behavior.
// The generated part, contracts/database/erd.json, joins those to PocketBase's
// own schema in contracts/database/schema-snapshot.json (a native `migrate up`,
// harness/bench/schema_dump.py): each live collection's fields count,
// indexes, rule classes, relation partition, and each relation's
// cardinality, flags, and delete behavior. A PR that adds or changes a
// migration regenerates the snapshot and the generated part (DB_ERD_STALE
// otherwise), and needs a DR-0004 revision only when it changes a written field.

import { finding, jsonLine, sha256 } from '../context.mjs';
import { validate } from '../json-schema.mjs';
import { extractCollections } from '../vocabulary/coverage.mjs';

export const ERD_PATH = 'contracts/database/erd.json';
export const ERD_SCHEMA_PATH = 'contracts/database/erd.schema.json';
export const DECISIONS_PATH = 'contracts/database/erd-decisions.json';
export const DECISIONS_SCHEMA_PATH = 'contracts/database/erd-decisions.schema.json';
export const ERD_DOC_PATH = 'docs/decisions/DR-0004-erd.md';
export const SNAPSHOT_PATH = 'contracts/database/schema-snapshot.json';
export const SNAPSHOT_SCHEMA_PATH = 'contracts/database/schema-snapshot.schema.json';
export const ENDPOINTS_PATH = 'pocketbase/pb_hooks/relation_endpoints.v1.json';
export const BASELINE_STORES_PATH = 'contracts/authority/baseline-stores.json';
export const MIGRATIONS_DIR = 'pocketbase/pb_migrations/';

const WRITTEN = ['rows', 'writers', 'purge', 'owningLeaf', 'createdBy', 'note'];
const PLANNED_ORDER = ['id', 'status', 'kind', 'type', 'store', 'bytes', 'group', 'scope', 'partition', 'partitionIndexed', 'indexes',
  'owningLeaf', 'createdBy', 'rows', 'writers', 'purge', 'note'];
const OWNER_FIELDS = ['user', 'account'];

export const isPlanned = (e) => e.status === 'planned' || e.status === 'held';

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

// Whether an index leads with the field, so a lookup or purge by it is a
// search instead of a scan.
export function leadsWith(indexes, field) {
  return (indexes || []).some((i) => (i.columns[0] || '').split('.').pop() === field);
}

// The relation fields of every collection in the snapshot, as <collection>.<field>.
export function snapshotRelations(snapshot) {
  return (snapshot?.collections || []).flatMap((c) => c.fields.filter((f) => f.type === 'relation').map((f) => ({ id: `${c.name}.${f.name}`, from: c.name, f })));
}

const pick = (o, keys) => Object.fromEntries(keys.filter((k) => o?.[k] !== undefined).map((k) => [k, o[k]]));
const order = (a, b) => (a.status === b.status ? 0 : a.status === 'live' ? -1 : 1) || a.id.localeCompare(b.id);

// Builds erd.json from the snapshot and the written decisions. A planned
// table that has gone live keeps its written fields; its live schema replaces
// the planned indexes.
export function buildErd(snapshot, decisions, endpoints, baselineStores) {
  const notes = new Map();
  const planned = new Map();
  for (const e of decisions?.entities || []) (isPlanned(e) ? planned : notes).set(e.id, e);
  const written = (id) => notes.get(id) || planned.get(id);
  const merges = new Map((decisions?.relations || []).map((r) => [r.id, r]));
  const authorized = new Set((endpoints?.fields || []).map((f) => `${f.collection}.${f.field}`));
  const content = new Set((snapshot.collections || []).filter((c) => !partitionOf(c) && c.rules.list === 'expression' && c.rules.create === 'null').map((c) => c.name));
  const baselineRows = new Map((baselineStores?.stores || []).filter((s) => s.kind === 'collection').map((s) => [s.name, s.rows || []]));
  const measured = snapshot.relationDeleteSemantics || {};
  const entities = [];
  const relations = [];
  for (const c of snapshot.collections) {
    const w = written(c.name);
    const partition = w?.partition?.kind === 'text' ? w.partition : partitionOf(c);
    const entity = {
      id: c.name,
      status: 'live',
      kind: 'collection',
      type: c.type,
      store: 'sqlite-data',
      bytes: c.fields.some((f) => f.type === 'file'),
      group: w?.group,
      scope: w?.scope,
      partition,
      partitionIndexed: partition ? (partition.kind === 'self' ? true : leadsWith(c.indexes, partition.field)) : false,
      fields: c.fields.length,
      indexes: c.indexes.map((i) => ({ name: i.name, unique: i.unique, columns: i.columns, ...(i.partial ? { partial: true } : {}) })),
      rules: c.rules,
      ...pick(w, WRITTEN),
    };
    const rows = baselineRows.get(c.name);
    if (!entity.rows && rows?.length) entity.rows = rows;
    entities.push(entity);
  }
  for (const r of snapshotRelations(snapshot)) {
    const target = r.f.relation.collection;
    const w = merges.get(r.id);
    relations.push({
      id: r.id, status: 'live', from: r.from, field: r.f.name, to: target,
      cardinality: r.f.relation.maxSelect === 1 ? 'many-to-one' : 'many-to-many',
      required: r.f.required, cascadeDelete: r.f.relation.cascadeDelete,
      onDelete: deleteBehavior({ ...r.f.relation, required: r.f.required }, measured),
      merge: w?.merge,
      authorization: target === 'users' ? 'owner' : authorized.has(r.id) ? 'relation-endpoint' : content.has(target) ? 'content' : 'server',
      note: w?.note,
    });
  }
  for (const t of snapshot.systemTables || []) {
    const w = written(t);
    entities.push({ id: t, status: 'live', kind: 'system-table', store: 'sqlite-data', group: w?.group, scope: w?.scope, partition: w?.partition ?? null, ...pick(w, WRITTEN) });
  }
  const live = new Set(entities.map((e) => e.id));
  for (const e of planned.values()) {
    if (live.has(e.id)) continue;
    const out = { ...e, partitionIndexed: e.partition ? leadsWith(e.indexes, e.partition.field) : false };
    entities.push(pick(out, PLANNED_ORDER));
  }
  const liveRelations = new Set(relations.map((r) => r.id));
  for (const r of decisions?.relations || []) if (isPlanned(r) && !liveRelations.has(r.id)) relations.push({ ...r });
  for (const x of [...entities, ...relations]) for (const k of Object.keys(x)) if (x[k] === undefined) delete x[k];
  return {
    $schema: './erd.schema.json',
    registry: 'rounds-erd',
    decisionRecord: decisions?.decisionRecord || 'DR-0004',
    revision: decisions?.revision || 1,
    description: 'DR-0004\'s ERD, generated: every PocketBase collection and system table at the snapshot\'s revision, the platform tables and stores DR-0004 places, and every relation with its cardinality, account partition, delete behavior, merge behavior, and indexes. The written fields come from erd-decisions.json, which DR-0004 ratifies; the rest comes from schema-snapshot.json through node scripts/conformance/run.mjs --write.',
    decisions: DECISIONS_PATH,
    snapshot: { path: SNAPSHOT_PATH, revision: snapshot.revision.commit, pocketbaseVersion: snapshot.pocketbaseVersion },
    semantics: { ...(decisions?.semantics || {}), measured },
    stores: decisions?.stores || [],
    groups: decisions?.groups || [],
    entities: entities.sort(order),
    relations: relations.sort(order),
  };
}

const push = (findings, code, file, text, parts, message) => findings.push(finding(code, file, text ? jsonLine(text, parts) : 1, message));

// Skips schema errors another finding reports better: a relation's missing
// merge or delete behavior is DB_ERD_DELETE_MISSING.
const reported = (err) => err.keyword === 'required' && /^\/relations\/\d+$/.test(err.pointer) && ['onDelete', 'merge'].includes(err.property);

// Checks the written part on its own and against the snapshot.
export function checkDecisions({ decisions, text, schema, snapshot, resolveLeaf, record }) {
  const findings = [];
  const f = (code, parts, message) => push(findings, code, DECISIONS_PATH, text, parts, message);
  for (const err of validate(decisions, schema)) {
    if (reported(err)) continue;
    f(err.keyword === 'required' ? 'DB_ERD_INCOMPLETE' : 'DB_ERD_INVALID', err.pointer.split('/').slice(1), `${err.pointer || '/'} ${err.message}`);
  }
  const stores = new Set((decisions.stores || []).map((s) => s.id));
  const groups = new Set((decisions.groups || []).map((g) => g.id));
  const live = new Set([...(snapshot?.collections || []).map((c) => c.name), ...(snapshot?.systemTables || [])]);
  const ids = new Map();
  (decisions.entities || []).forEach((e, i) => {
    if (ids.has(e.id)) f('DB_TWO_AUTHORITIES', ['entities', i, 'id'], `${e.id} is written twice; one entity has one store and one owner`);
    ids.set(e.id, e);
    if (e.store && !stores.has(e.store)) f('DB_UNKNOWN_REF', ['entities', i, 'store'], `${e.id} names store ${e.store}, which the ERD doesn't list`);
    if (e.group && !groups.has(e.group)) f('DB_UNKNOWN_REF', ['entities', i, 'group'], `${e.id} names group ${e.group}, which the ERD doesn't list`);
    if (e.owningLeaf) {
      const r = resolveLeaf(e.owningLeaf);
      if (!r.ok) f('DB_UNKNOWN_REF', ['entities', i, 'owningLeaf'], `${e.id} owning leaf: ${r.reason}`);
    }
    if (e.bytes && !stores.has('files')) f('DB_ERD_INCOMPLETE', ['entities', i, 'bytes'], `${e.id} holds bytes, but the ERD lists no file store`);
    if (isPlanned(e)) {
      // A planned account table states its partition and an index that
      // leads with it, so its lookups and #76's purge search one account.
      if (e.scope === 'account' && !e.partition) f('DB_ERD_INCOMPLETE', ['entities', i, 'partition'], `${e.id} holds account data but names no partition column`);
      else if (e.scope === 'account' && !leadsWith(e.indexes, e.partition.field)) {
        f('DB_ERD_INCOMPLETE', ['entities', i, 'indexes'], `${e.id} holds account data, but no index leads with its partition ${e.partition.field}; a lookup or purge would scan every account`);
      }
    } else if (snapshot && !live.has(e.id)) {
      f('DB_UNKNOWN_REF', ['entities', i, 'id'], `${e.id} annotates no collection or system table in ${SNAPSHOT_PATH}; plan it with a status, or drop it`);
    }
  });
  if (snapshot) {
    for (const name of live) {
      if (!ids.has(name)) f('DB_ERD_UNCOVERED', ['entities'], `${name} is in ${SNAPSHOT_PATH} with no entity in ${DECISIONS_PATH}; write its group, scope, writers, and purge`);
    }
  }
  const liveRelations = new Set(snapshotRelations(snapshot).map((r) => r.id));
  const relIds = new Set();
  (decisions.relations || []).forEach((r, i) => {
    if (relIds.has(r.id)) f('DB_TWO_AUTHORITIES', ['relations', i, 'id'], `${r.id} is written twice`);
    relIds.add(r.id);
    if (!r.merge) f('DB_ERD_DELETE_MISSING', ['relations', i], `${r.id} has no merge behavior`);
    if (isPlanned(r)) {
      if (!r.onDelete) f('DB_ERD_DELETE_MISSING', ['relations', i], `${r.id} has no delete behavior`);
      for (const end of ['from', 'to']) if (r[end] && !ids.has(r[end])) f('DB_UNKNOWN_REF', ['relations', i, end], `${r.id} ${end} ${r[end]} is not an entity in the ERD`);
    } else if (snapshot && !liveRelations.has(r.id)) {
      f('DB_UNKNOWN_REF', ['relations', i, 'id'], `${r.id} is no relation field in ${SNAPSHOT_PATH}; plan it with a status, or drop it`);
    }
  });
  for (const id of liveRelations) if (!relIds.has(id)) f('DB_ERD_DELETE_MISSING', ['relations'], `${id} is a relation in ${SNAPSHOT_PATH} with no merge behavior in ${DECISIONS_PATH}`);
  if (record && decisions.decisionRecord !== record.id) f('DB_VERSION_MISMATCH', ['decisionRecord'], `the ERD names ${decisions.decisionRecord}, not ${record.id}`);
  if (record && decisions.revision !== record.revision) {
    f('DB_VERSION_MISMATCH', ['revision'], `the ERD's written part is at revision ${decisions.revision}; ${record.id} is at ${record.revision}, and they share one counter`);
  }
  return findings;
}

// Migrations the snapshot didn't see, or saw with other contents.
export function staleMigrations(ctx, snapshot) {
  const listed = new Map((snapshot?.migrations || []).map((m) => [m.file, m.sha256]));
  const onTree = ctx.files().filter((p) => p.startsWith(MIGRATIONS_DIR) && p.endsWith('.js'));
  const changed = onTree.filter((p) => listed.get(p.slice(MIGRATIONS_DIR.length)) !== sha256(ctx.read(p)));
  const names = new Set(onTree.map((p) => p.slice(MIGRATIONS_DIR.length)));
  const gone = [...listed.keys()].filter((file) => !names.has(file));
  return { listed, changed, gone };
}

// Checks the generated part against the snapshot, the migrations on the
// tree, and the written part.
export function checkErd(ctx, { erd, erdText, schema, snapshot, decisions, record }) {
  const findings = [];
  const f = (code, parts, message) => push(findings, code, ERD_PATH, erdText, parts, message);
  const written = new Set((decisions?.entities || []).map((e) => e.id));
  const writtenRelations = new Set((decisions?.relations || []).map((r) => r.id));
  // An entity with no written fields is DB_ERD_UNCOVERED in the written part.
  const unwritten = new Set((erd.entities || []).map((e, i) => (written.has(e.id) ? null : i)).filter((i) => i !== null));
  for (const err of validate(erd, schema)) {
    if (reported(err)) continue;
    const at = /^\/entities\/(\d+)$/.exec(err.pointer);
    if (at && err.keyword === 'required' && unwritten.has(Number(at[1]))) continue;
    f(err.keyword === 'required' ? 'DB_ERD_INCOMPLETE' : 'DB_ERD_INVALID', err.pointer.split('/').slice(1), `${err.pointer || '/'} ${err.message}`);
  }
  const ids = new Map();
  (erd.entities || []).forEach((e, i) => {
    if (ids.has(e.id)) f('DB_TWO_AUTHORITIES', ['entities', i, 'id'], `${e.id} is listed twice; one entity has one store and one owner`);
    ids.set(e.id, e);
    if (e.status === 'live' && e.scope === 'account' && !e.partition) f('DB_ERD_INCOMPLETE', ['entities', i, 'partition'], `${e.id} holds account data but names no partition column`);
  });
  (erd.relations || []).forEach((r, i) => {
    if (!r.onDelete) f('DB_ERD_DELETE_MISSING', ['relations', i], `${r.id} has no delete behavior`);
    if (!r.merge && writtenRelations.has(r.id)) f('DB_ERD_DELETE_MISSING', ['relations', i], `${r.id} has no merge behavior`);
    for (const end of ['from', 'to']) if (r[end] && !ids.has(r[end])) f('DB_UNKNOWN_REF', ['relations', i, end], `${r.id} ${end} ${r[end]} is not an entity in the ERD`);
  });
  if (snapshot) {
    for (const c of snapshot.collections || []) {
      const e = ids.get(c.name);
      if (e && e.status !== 'live') f('DB_ERD_INVALID', ['entities', erd.entities.indexOf(e), 'status'], `${c.name} is live in the snapshot but ${e.status} in the ERD`);
    }
    if (erd.snapshot?.revision && erd.snapshot.revision !== snapshot.revision?.commit) {
      f('DB_VERSION_MISMATCH', ['snapshot', 'revision'], `the ERD was built from snapshot ${erd.snapshot.revision.slice(0, 7)}, but ${SNAPSHOT_PATH} is ${String(snapshot.revision?.commit).slice(0, 7)}; run node scripts/conformance/run.mjs --write`);
    }
    // A PR that adds or changes a migration regenerates the snapshot, then
    // the ERD; until it does, the generated part is stale.
    const { changed, gone, listed } = staleMigrations(ctx, snapshot);
    const regen = 'regenerate the snapshot with harness/bench/schema_dump.py, then run node scripts/conformance/run.mjs --write';
    for (const p of changed) {
      const file = p.slice(MIGRATIONS_DIR.length);
      push(findings, 'DB_ERD_STALE', p, null, [], listed.has(file) ? `${p} changed after ${SNAPSHOT_PATH} was taken; ${regen}` : `${p} is not in ${SNAPSHOT_PATH}'s migrations; ${regen}`);
    }
    for (const file of gone) push(findings, 'DB_ERD_STALE', SNAPSHOT_PATH, null, [], `${SNAPSHOT_PATH} lists ${file}, which is no longer in ${MIGRATIONS_DIR}; ${regen}`);
    // What those migrations create must have its written fields.
    if (changed.length) {
      const extracted = extractCollections(ctx);
      for (const item of extracted.items) {
        if (item.historical || !changed.includes(item.path)) continue;
        if (!written.has(item.name)) push(findings, 'DB_ERD_UNCOVERED', item.path, null, [], `${item.path}:${item.line} creates ${item.name}, which has no entity in ${DECISIONS_PATH}`);
      }
      for (const ev of extracted.unresolved) {
        if (changed.includes(ev.path)) push(findings, 'DB_ERD_UNRESOLVED', ev.path, null, [], `${ev.path}:${ev.line} creates a collection whose name isn't a literal; name it, so the ERD can cover it`);
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
