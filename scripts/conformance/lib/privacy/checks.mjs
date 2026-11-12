// The privacy rule's checks (ROUNDS-14-L01). Each pushes findings with a
// code a reader can act on; analyze() runs them all once per context.

import { BlockList, isIP } from 'node:net';
import path from 'node:path';
import { finding, jsonLine } from '../context.mjs';
import { validate } from '../json-schema.mjs';
import { leafResolver, loadLeafIds } from '../leaf-ids.mjs';
import { extractBrowserKeys } from '../authority/browser-keys.mjs';
import { AUTH_SYSTEM_FIELDS, extractSchema } from './schema-vm.mjs';
import { ancestorOf, callerIdError, descendantsOf, fieldResolver, familyCovers, idForm, pointerMatch, segments, split, within } from './fields.mjs';
import { definedFunctions, scanProviderCalls } from './scan.mjs';
import {
  BASELINE_STORES_PATH, CONFIG_DOC_PATH, COPY_DIRS, DOC_PATH, DR_LEAF, FIELD_MAP_PATH, MATRIX_PATH, POLICY_PATH, PRIVACY_DIR,
  PURPOSES_PATH, REGISTRIES, SCHEMA_PATH, SECRET_PATTERNS_PATH, VIOLATIONS_PATH, sourceFiles, staleCopies,
} from './files.mjs';

// The sixteen purposes that may be legacy (register entry 9). Pinned here,
// so a new legacy purpose fails however the registry is edited.
export const LEGACY_BASELINE = [
  'provider.test', 'provider.refresh_models', 'resume.improve', 'resume.guided_summary', 'resume.tailor', 'resume.cover_letter',
  'resume.import', 'experience.import', 'resume.ats_score', 'github.enhance', 'ai_coding.chat', 'ai_coding.edit', 'ai_coding.grade',
  'take_home.grade', 'take_home.chat', 'sd_practice.chat',
];
export const GRADE_PURPOSES = ['ai_coding.grade', 'take_home.grade'];
export const CLASS_SINKS = ['remote-ai', 'index', 'logs', 'share', 'export', 'local-draft', 'backup', 'analytics'];
export const VISIBILITY_SINKS = [...CLASS_SINKS, 'client-read'];
export const CLASS_ORDER = ['Private', 'Third-party personal', 'Sensitive', 'Secret'];
export const SPEC_ROW_ORDER = ['Private', 'Sensitive', 'Third-party personal', 'Secret', 'Share Projection'];
export const VISIBILITY_ORDER = ['public-ui', 'authed-readable', 'server-only'];
export const VERSION_IDS = ['privacy', 'retention', 'redaction', 'consent'];
export const JSON_COLUMNS = ['pb:resumes.data', 'pb:ai_coding_attempts.ai_chats', 'pb:take_home_attempts.ai_chats',
  'pb:ai_coding_attempts.rubric_review', 'pb:take_home_attempts.rubric_review', 'pb:take_home_attempts.harness_output'];
export const DEFINITIONS_DIR = 'backend/definitions';
export const DEFINITION_SCHEMAS_DIR = 'contracts/definitions';
export const LEGACY_PURPOSES_MIRROR = 'contracts/ai/legacy-purposes.json';
// Column types whose values are free text, and a pattern that only bars
// some characters (`^[^...]+$`), which leaves the column free text.
const FREE_TEXT = new Set(['text', 'editor', 'json', 'email', 'url']);
const NEGATED_ONLY = /^\^?\[\^[^\]]*\][+*]\$?$/;
const PIN = /\b(privacy|retention|redaction|consent)@(\d+)\b/g;
const PIN_FILES = /^(contracts|backend|frontend\/src|scripts|docs)\/.*\.(json|md|mjs|js|ts|tsx|py)$/;
const SPLIT_SINK = { export: 0, 'local-draft': 1, backup: 2 };

// ------------------------------------------------------------ loading

function parseFile(ctx, file, F) {
  let text;
  try {
    text = ctx.read(file);
  } catch (err) {
    F.push(finding('PRIVACY_SCHEMA_INVALID', file, 1, `can't be read: ${err.message}`));
    return null;
  }
  try {
    return { text, data: JSON.parse(text) };
  } catch (err) {
    F.push(finding('PRIVACY_SCHEMA_INVALID', file, 1, `is not valid JSON: ${err.message}`));
    return null;
  }
}

export function loadPrivacy(ctx, F) {
  const P = { texts: {}, vectors: [] };
  const schemaFile = ctx.exists(SCHEMA_PATH) ? parseFile(ctx, SCHEMA_PATH, F) : null;
  if (!schemaFile) {
    F.push(finding('PRIVACY_SCHEMA_INVALID', SCHEMA_PATH, 1, 'the privacy schema is missing'));
    return P;
  }
  P.schema = schemaFile.data;
  for (const file of sourceFiles(ctx)) {
    if (file === SCHEMA_PATH) continue;
    const parsed = parseFile(ctx, file, F);
    if (!parsed) continue;
    P.texts[file] = parsed.text;
    const def = REGISTRIES[parsed.data?.registry];
    if (!def) {
      F.push(finding('PRIVACY_SCHEMA_INVALID', file, 1, `registry "${parsed.data?.registry}" is not one of ${Object.keys(REGISTRIES).join(', ')}`));
      continue;
    }
    for (const err of validate(parsed.data, P.schema.$defs[def], P.schema)) {
      const parts = err.pointer.split('/').slice(1).map((p) => (/^\d+$/.test(p) ? Number(p) : p));
      F.push(finding('PRIVACY_SCHEMA_INVALID', file, jsonLine(parsed.text, parts), `${err.pointer || '/'} ${err.message}`));
    }
    if (def === 'vectors') P.vectors.push({ file, data: parsed.data });
    else P[def] = parsed.data;
    if (def !== 'vectors') P[`${def}Path`] = file;
  }
  for (const [def, rel] of [['policy', POLICY_PATH], ['purposes', PURPOSES_PATH], ['fieldMap', FIELD_MAP_PATH], ['violations', VIOLATIONS_PATH], ['secretPatterns', SECRET_PATTERNS_PATH]]) {
    if (!P[def]) F.push(finding('PRIVACY_SCHEMA_INVALID', rel, 1, `${rel} is missing or unreadable`));
  }
  return P;
}

const at = (P, file, parts) => jsonLine(P.texts[file] || '', parts);

// ------------------------------------------------------------ policy

export function policyIndex(policy) {
  const cells = new Map((policy?.matrix?.cells || []).map((c) => [`${c.class}|${c.sink}`, c]));
  const visibility = new Map((policy?.visibilityRules || []).map((r) => [`${r.visibility}|${r.sink}`, r]));
  const rows = new Map([...(policy?.lifecycle?.rows || []), ...(policy?.lifecycle?.decided || [])].map((r) => [r.id, r]));
  const ruleIds = new Set([
    ...[...cells.values()].map((c) => c.id), ...[...visibility.values()].map((r) => r.id), ...rows.keys(),
    ...(policy?.consent?.units || []).map((u) => `consent.${u.id}`), 'locations.never', 'locations.combination', 'credentialChannel',
  ]);
  return { cells, visibility, rows, ruleIds };
}

function checkPolicy(ctx, P, F, resolveLeaf) {
  const policy = P.policy;
  if (!policy) return;
  const file = P.policyPath;
  const push = (code, parts, message) => F.push(finding(code, file, at(P, file, parts), message));
  const versionIds = policy.versions.map((v) => v.id).sort();
  if (versionIds.join() !== [...VERSION_IDS].sort().join()) push('PRIVACY_SCHEMA_INVALID', ['versions'], `versions must be exactly ${VERSION_IDS.join(', ')}`);
  policy.versions.forEach((v, i) => {
    if (!v.revisions.some((r) => r.revision === v.current)) push('PRIVACY_UNKNOWN_PIN', ['versions', i, 'current'], `${v.id}@${v.current} has no revision entry`);
    v.revisions.forEach((r, j) => {
      if (r.revision > 1 && !r.changedConstraint) push('PRIVACY_SUPERSESSION_INCOMPLETE', ['versions', i, 'revisions', j], `${v.id}@${r.revision} supersedes an earlier revision without naming the changed constraint`);
    });
  });
  const classes = policy.classes.map((c) => c.name);
  if (classes.join() !== ['Private', 'Third-party personal', 'Sensitive', 'Secret', 'Share Projection'].join()) push('PRIVACY_SCHEMA_INVALID', ['classes'], 'classes must be the five spec classes in strictness order, Share Projection last');
  if (policy.visibilities.map((v) => v.name).join() !== VISIBILITY_ORDER.join()) push('PRIVACY_SCHEMA_INVALID', ['visibilities'], `visibilities must be ${VISIBILITY_ORDER.join(', ')}`);
  const sinkIds = new Set();
  policy.sinks.forEach((s, i) => {
    if (sinkIds.has(s.id)) push('PRIVACY_DUPLICATE', ['sinks', i, 'id'], `sink ${s.id} is listed twice`);
    sinkIds.add(s.id);
    const r = resolveLeaf(s.enforcingLeaf);
    if (!r.ok) push('PRIVACY_UNKNOWN_REF', ['sinks', i, 'enforcingLeaf'], `sink ${s.id} enforcing leaf: ${r.reason}`);
  });
  for (const s of VISIBILITY_SINKS) if (!sinkIds.has(s)) push('PRIVACY_MATRIX_INCOMPLETE', ['sinks'], `sink ${s} has no entry`);
  // The matrix: one cell per class and sink, each cell's text taken from the spec row.
  const seen = new Set();
  const rowText = new Map(policy.matrix.rows.map((r) => [r.class, r.cells]));
  policy.matrix.cells.forEach((c, i) => {
    const key = `${c.class}|${c.sink}`;
    if (seen.has(key)) push('PRIVACY_DUPLICATE', ['matrix', 'cells', i], `${c.class} has two rules for ${c.sink}`);
    seen.add(key);
    if (!CLASS_SINKS.includes(c.sink)) push('PRIVACY_SCHEMA_INVALID', ['matrix', 'cells', i, 'sink'], `${c.sink} is not a matrix sink`);
    const cells = rowText.get(c.class);
    if (!cells) return;
    let expected;
    if (c.sink === 'analytics') expected = 'fail closed';
    else if (c.sink in SPLIT_SINK) expected = null;
    else expected = cells[['remote-ai', 'index', 'logs', 'share'].indexOf(c.sink) + 2];
    if (expected !== null && c.text !== expected) push('PRIVACY_MATRIX_TEXT', ['matrix', 'cells', i, 'text'], `${c.id} text must be the spec cell "${expected}"`);
    if (expected === null && !cells[6].includes(c.text)) push('PRIVACY_MATRIX_TEXT', ['matrix', 'cells', i, 'text'], `${c.id} text must be the part of "${cells[6]}" that rules ${c.sink}`);
  });
  for (const cls of classes) for (const sink of CLASS_SINKS) if (!seen.has(`${cls}|${sink}`)) push('PRIVACY_MATRIX_INCOMPLETE', ['matrix', 'cells'], `${cls} has no rule for ${sink}; a sink without a rule is denied, so the matrix must say so`);
  if (policy.matrix.rows.map((r) => r.class).join() !== SPEC_ROW_ORDER.join()) push('PRIVACY_MATRIX_TEXT', ['matrix', 'rows'], `matrix rows must follow the spec order: ${SPEC_ROW_ORDER.join(', ')}`);
  const vseen = new Set();
  policy.visibilityRules.forEach((r, i) => {
    const key = `${r.visibility}|${r.sink}`;
    if (vseen.has(key)) push('PRIVACY_DUPLICATE', ['visibilityRules', i], `${r.visibility} has two rules for ${r.sink}`);
    vseen.add(key);
  });
  for (const v of VISIBILITY_ORDER) for (const sink of VISIBILITY_SINKS) if (!vseen.has(`${v}|${sink}`)) push('PRIVACY_MATRIX_INCOMPLETE', ['visibilityRules'], `${v} has no rule for ${sink}`);
  // Lifecycle numbers: a default inside its own choices or range.
  const rows = [...policy.lifecycle.rows, ...policy.lifecycle.decided];
  const rowIds = new Set();
  rows.forEach((row) => {
    const parts = ['lifecycle', policy.lifecycle.rows.includes(row) ? 'rows' : 'decided', (policy.lifecycle.rows.includes(row) ? policy.lifecycle.rows : policy.lifecycle.decided).indexOf(row)];
    if (rowIds.has(row.id)) push('PRIVACY_DUPLICATE', parts, `lifecycle row ${row.id} is listed twice`);
    rowIds.add(row.id);
    for (const e of row.enforcement || []) {
      const r = resolveLeaf(e.leaf);
      if (!r.ok) push('PRIVACY_UNKNOWN_REF', [...parts, 'enforcement'], `${row.id} enforcing leaf: ${r.reason}`);
      if (e.test && !ctx.exists(e.test)) push('PRIVACY_UNKNOWN_REF', [...parts, 'enforcement'], `${row.id} names test ${e.test}, which does not exist`);
      else if (e.test && !ctx.read(e.test).includes(row.id)) push('PRIVACY_UNKNOWN_REF', [...parts, 'enforcement'], `${e.test} doesn't cite row ${row.id}, so it can't read the policy value`);
    }
    const spec = row.retention;
    if (spec) {
      const ok = spec.choices ? spec.choices.includes(spec.default) : spec.range ? Number.isInteger(spec.default) && spec.default >= spec.range[0] && spec.default <= spec.range[1] : true;
      if (!ok) push('PRIVACY_SCHEMA_INVALID', [...parts, 'retention'], `${row.id} default ${spec.default} is outside its own allowed values`);
    }
    if (row.sameAs && !rows.some((r) => r.id === row.sameAs)) push('PRIVACY_UNKNOWN_REF', [...parts, 'sameAs'], `${row.id} follows ${row.sameAs}, which is not a row`);
  });
  for (const block of ['accountDeletion', 'locations', 'credentialChannel', 'consent', 'redaction']) {
    for (const e of policy[block].enforcement || []) {
      const r = resolveLeaf(e.leaf);
      if (!r.ok) push('PRIVACY_UNKNOWN_REF', [block, 'enforcement'], `${block} enforcing leaf: ${r.reason}`);
    }
  }
  const names = new Set();
  policy.operatorSettings.forEach((s, i) => {
    if (names.has(s.name)) push('PRIVACY_DUPLICATE', ['operatorSettings', i], `${s.name} is listed twice`);
    names.add(s.name);
    if (s.kind === 'days') {
      const row = rows.find((r) => r.id === s.row);
      if (!row?.retention?.range || row.retention.setting !== s.name) push('PRIVACY_UNKNOWN_REF', ['operatorSettings', i, 'row'], `${s.name} must name the lifecycle row whose range it sets`);
    }
  });
}

// ------------------------------------------------------------ field map

function authorityRows(ctx) {
  const rows = new Map();
  const stores = new Map();
  try {
    for (const r of ctx.readJson(MATRIX_PATH).rows || []) rows.set(r.id, r);
  } catch { /* the authority rule reports it */ }
  try {
    for (const s of ctx.readJson(BASELINE_STORES_PATH).stores || []) stores.set(`${s.kind}:${s.name}`, s.rows || []);
  } catch { /* the authority rule reports it */ }
  return { rows, stores };
}

function looser(entry, floorRow) {
  // A class may not sit below its row's floor; Share Projection only copies
  // Private rows; a class never stands in for a visibility or the reverse.
  if (floorRow.privacy_floor !== undefined && floorRow.privacy_floor !== null) {
    if (!entry.class) return `takes a visibility, but row ${floorRow.id} is account data with floor ${floorRow.privacy_floor}`;
    const floor = floorRow.privacy_floor;
    if (entry.class === 'Share Projection') return ['Private', 'Share Projection'].includes(floor) ? null : `is Share Projection, which can't copy a ${floor} row`;
    if (floor === 'Share Projection') return entry.class === 'Secret' ? null : `is ${entry.class}, looser than row ${floorRow.id}'s floor ${floor}`;
    return CLASS_ORDER.indexOf(entry.class) < CLASS_ORDER.indexOf(floor) ? `is ${entry.class}, looser than row ${floorRow.id}'s floor ${floor}` : null;
  }
  if (floorRow.visibility) {
    if (!entry.visibility) return `takes a class, but row ${floorRow.id} is platform content with visibility ${floorRow.visibility}`;
    return VISIBILITY_ORDER.indexOf(entry.visibility) < VISIBILITY_ORDER.indexOf(floorRow.visibility) ? `is ${entry.visibility}, looser than row ${floorRow.id}'s ${floorRow.visibility}` : null;
  }
  return null;
}

function tighterThan(child, parent) {
  if (!parent) return true;
  if (child.class && parent.class) {
    if (child.class === 'Share Projection' || parent.class === 'Share Projection') return child.class === parent.class || child.class === 'Secret';
    return CLASS_ORDER.indexOf(child.class) >= CLASS_ORDER.indexOf(parent.class);
  }
  if (child.visibility && parent.visibility) return VISIBILITY_ORDER.indexOf(child.visibility) >= VISIBILITY_ORDER.indexOf(parent.visibility);
  // Grading material inside a visibility column may only move to server-only.
  return false;
}

// The top-level properties of a definition schema, across its oneOf branches.
export function schemaProperties(schema) {
  const out = new Set(Object.keys(schema.properties || {}));
  for (const key of ['oneOf', 'anyOf', 'allOf']) {
    for (let b of schema[key] || []) {
      if (b.$ref) b = schema.$defs?.[b.$ref.split('/').pop()] || {};
      for (const p of Object.keys(b.properties || {})) out.add(p);
    }
  }
  return [...out].sort();
}

// { name, schemaConst, properties } for each definition schema.
export function definitionSchemas(ctx) {
  const out = [];
  for (const f of ctx.files().filter((x) => x.startsWith(`${DEFINITION_SCHEMAS_DIR}/`) && x.endsWith('.schema.json'))) {
    let s;
    try { s = ctx.readJson(f); } catch { continue; }
    const name = /:definitions:([a-z0-9-]+):v\d+$/.exec(s.$id || '')?.[1];
    const consts = new Set();
    const collect = (node) => {
      if (node?.properties?.schema?.const) consts.add(node.properties.schema.const);
      for (const key of ['oneOf', 'anyOf', 'allOf']) for (let b of node?.[key] || []) {
        if (b.$ref) b = s.$defs?.[b.$ref.split('/').pop()] || {};
        collect(b);
      }
    };
    collect(s);
    if (name) out.push({ name, path: f, consts: [...consts], properties: schemaProperties(s) });
  }
  return out;
}

// The definition schemas the files under backend/definitions/ use.
export function definitionUse(ctx) {
  const schemas = definitionSchemas(ctx);
  const used = new Map();
  const unknown = [];
  for (const f of ctx.files().filter((x) => x.startsWith(`${DEFINITIONS_DIR}/`) && x.endsWith('.json'))) {
    let doc;
    try { doc = ctx.readJson(f); } catch { unknown.push({ path: f, reason: 'not valid JSON' }); continue; }
    const s = schemas.find((x) => x.consts.includes(doc?.schema));
    if (!s) { unknown.push({ path: f, reason: `schema "${doc?.schema}" matches no contract in ${DEFINITION_SCHEMAS_DIR}` }); continue; }
    if (!used.has(s.name)) used.set(s.name, { ...s, files: 0 });
    used.get(s.name).files++;
  }
  return { used: [...used.values()], unknown };
}

function checkFieldMap(ctx, P, F, A) {
  const map = P.fieldMap;
  if (!map) return;
  const file = P.fieldMapPath;
  const entries = map.entries;
  const push = (code, i, message, key) => F.push(finding(code, file, at(P, file, i === null ? ['entries'] : ['entries', i, ...(key ? [key] : [])]), message));
  const { rows, stores } = authorityRows(ctx);
  const first = new Map();
  entries.forEach((e, i) => {
    if (first.has(e.id)) push('PRIVACY_FIELD_TWO_CLASSES', i, `${e.id} is listed twice; a field takes one class or visibility`, 'id');
    else first.set(e.id, i);
    if (!idForm(e.id)) push('PRIVACY_FIELD_ID_INVALID', i, `${e.id} is not a pb:, storage:, def:, request:, or <entity>.<field> id`, 'id');
    if (idForm(e.id) === 'entity') push('PRIVACY_FIELD_ID_INVALID', i, `${e.id} uses the <entity>.<field> form, which waits for ROUNDS-08-L01's entities`, 'id');
  });
  const R = fieldResolver(entries);
  A.resolver = R;
  // Rows and floors. An entry in a store the authority matrix maps keeps
  // one of its rows, so the row's floor binds it.
  const storeOf = (id) => {
    const [base] = split(id);
    if (base.startsWith('pb:')) return `collection:${base.slice(3).split('.')[0]}`;
    return base.startsWith('storage:') ? `browser-key:${base.slice(8)}` : null;
  };
  entries.forEach((e, i) => {
    const storeRows = e.row ? null : stores.get(storeOf(e.id));
    if (storeRows && storeRows.length) push('PRIVACY_ROW_MISSING', i, `${e.id} names no row, but its store maps to ${storeRows.join(', ')}; name the row whose floor it keeps`, 'id');
  });
  entries.forEach((e, i) => {
    if (!e.row) return;
    const row = rows.get(e.row);
    if (!row) { push('PRIVACY_UNKNOWN_REF', i, `${e.id} names row ${e.row}, which is not in ${MATRIX_PATH}`, 'row'); return; }
    const storeRows = stores.get(storeOf(e.id));
    if (storeRows && storeRows.length && !storeRows.includes(e.row) && !e.id.includes('#')) {
      push('PRIVACY_ROW_MISMATCH', i, `${e.id} names row ${e.row}, but ${BASELINE_STORES_PATH} maps its store to ${storeRows.join(', ')}`, 'row');
    }
    const why = looser(e, row);
    if (why) push('PRIVACY_FLOOR_LOOSER', i, `${e.id} ${why}`, e.class ? 'class' : 'visibility');
  });
  entries.forEach((e, i) => {
    if (e.pathsFrom && !R.byId.has(e.pathsFrom)) push('PRIVACY_UNKNOWN_REF', i, `${e.id} reads its paths from ${e.pathsFrom}, which is not in the map`, 'pathsFrom');
    const parent = ancestorOf(e.id, R.byId);
    if (parent && !tighterThan(e, parent)) push('PRIVACY_DESCENDANT_LOOSER', i, `${e.id} is looser than ${parent.id}; a deeper entry may only tighten`, e.class ? 'class' : 'visibility');
  });
  // Collections, fields, and auth system fields on this tree.
  const schema = extractSchema(ctx);
  A.schema = schema;
  for (const err of schema.errors) F.push(finding('PRIVACY_SCHEMA_UNREADABLE', err.path, 1, `the field map can't read the schema past this migration: ${err.message}`));
  const live = new Set();
  for (const c of schema.collections) {
    live.add(`pb:${c.name}`);
    if (c.type === 'auth') for (const f of AUTH_SYSTEM_FIELDS) live.add(`pb:${c.name}.${f}`);
    for (const f of c.fields) live.add(`pb:${c.name}.${f.name}`);
  }
  A.unclassified = [];
  if (schema.ok) {
    for (const id of live) if (!R.byId.has(id)) { A.unclassified.push(id); push('FIELD_UNCLASSIFIED', null, `${id} is a live field with no class; add it to ${FIELD_MAP_PATH}`); }
    entries.forEach((e, i) => {
      if (!e.id.startsWith('pb:')) return;
      const [base] = split(e.id);
      if (!live.has(base)) push('PRIVACY_FIELD_STALE', i, `${e.id} names a field no migration leaves live`, 'id');
    });
    // A column that takes free text can hold anything, so it is content,
    // never metadata or an opaque id, unless its migration constrains it.
    // A pattern that only bars a few characters doesn't.
    const columns = new Map();
    for (const c of schema.collections) for (const f of c.fields) columns.set(`pb:${c.name}.${f.name}`, f);
    const constrained = (f) => f.type === 'text' && Boolean(f.pattern) && !NEGATED_ONLY.test(f.pattern);
    entries.forEach((e, i) => {
      const f = e.kind !== 'content' ? columns.get(e.id) : null;
      if (f && FREE_TEXT.has(f.type) && !constrained(f)) {
        push('PRIVACY_KIND_UNCONSTRAINED', i, `${e.id} is kinded ${e.kind}, but its ${f.type} column takes free text; class it content, or constrain it in a migration`, 'kind');
      }
    });
  }
  // JSON columns: the four named columns declare their paths, and every
  // pointer entry names a declared path.
  const shapes = map.shapes || {};
  for (const col of JSON_COLUMNS) if (!shapes[col]) F.push(finding('PRIVACY_SHAPE_MISSING', file, at(P, file, ['shapes']), `${col} declares no JSON paths`));
  for (const [col, paths] of Object.entries(shapes)) {
    if (!R.byId.has(col)) F.push(finding('PRIVACY_UNKNOWN_REF', file, at(P, file, ['shapes', col]), `shape ${col} has no column entry`));
    for (const p of paths) if (!R.resolve(`${col}#${p}`)) F.push(finding('FIELD_UNCLASSIFIED', file, at(P, file, ['shapes', col]), `${col}#${p} has no class`));
  }
  entries.forEach((e, i) => {
    const [base, pointer] = split(e.id);
    if (pointer === null || !base.startsWith('pb:')) return;
    const declared = shapes[base] || shapes[R.byId.get(base)?.pathsFrom];
    if (!declared) return;
    const pattern = segments(pointer);
    if (!declared.some((p) => pointerMatch(pattern, segments(p)))) push('PRIVACY_FIELD_STALE', i, `${e.id} names a path ${base}'s declared shape doesn't have`, 'id');
  });
  // Browser storage on this tree, through ROUNDS-01-L02's extractor.
  const keys = extractBrowserKeys(ctx);
  A.storage = keys;
  for (const site of keys.unresolved) F.push(finding('PRIVACY_STORAGE_UNRESOLVED', site.split(':')[0], Number(site.split(':')[1]) || 1, 'a browser storage key the field map can\'t resolve'));
  for (const [family] of keys.families) {
    const id = `storage:${family}`;
    if (!R.byId.has(id)) { A.unclassified.push(id); push('FIELD_UNCLASSIFIED', null, `${id} is a browser storage key family with no class; add it to ${FIELD_MAP_PATH}`); }
  }
  entries.forEach((e, i) => {
    if (e.id.startsWith('storage:') && !keys.families.has(e.id.slice('storage:'.length))) push('PRIVACY_FIELD_STALE', i, `${e.id} is a key family frontend/src no longer reads or writes`, 'id');
  });
  // Definitions under backend/definitions/.
  const defs = definitionUse(ctx);
  A.definitions = defs;
  for (const u of defs.unknown) F.push(finding('PRIVACY_SCHEMA_UNREADABLE', u.path, 1, u.reason));
  const defProps = new Set(defs.used.flatMap((d) => d.properties.map((p) => `def:${d.name}#/${p}`)));
  for (const id of defProps) if (!R.byId.has(id)) { A.unclassified.push(id); push('FIELD_UNCLASSIFIED', null, `${id} is a definition property with no class; add it to ${FIELD_MAP_PATH}`); }
  entries.forEach((e, i) => {
    if (!e.id.startsWith('def:')) return;
    const [base, pointer] = split(e.id);
    const top = `${base}#/${segments(pointer)[0]}`;
    if (!defProps.has(top)) push('PRIVACY_FIELD_STALE', i, `${e.id} names a property no stored definition's schema has`, 'id');
  });
  // Request-only inputs belong to a registered purpose.
  const purposeIds = new Set((P.purposes?.purposes || []).map((p) => p.id));
  entries.forEach((e, i) => {
    const m = /^request:([^#]+)#/.exec(e.id);
    if (m && !purposeIds.has(m[1])) push('PRIVACY_UNKNOWN_REF', i, `${e.id} belongs to ${m[1]}, which is not a registered purpose`, 'id');
  });
}

// ------------------------------------------------------------ purposes

function checkPurposes(ctx, P, F, A, resolveLeaf) {
  const reg = P.purposes;
  if (!reg) return;
  const file = P.purposesPath;
  const push = (code, parts, message) => F.push(finding(code, file, at(P, file, parts), message));
  const R = A.resolver;
  const policy = P.policy;
  const ids = new Set();
  const base = readBaseJson(ctx, PURPOSES_PATH);
  const baseStatus = new Map((base?.purposes || []).map((p) => [p.id, p.status]));
  const defined = new Map();
  const functionsOf = (p) => {
    if (!defined.has(p)) defined.set(p, ctx.exists(p) ? definedFunctions(ctx.read(p)) : null);
    return defined.get(p);
  };
  const siteExists = (s) => functionsOf(s.path)?.has(s.function);
  reg.providerHelpers.forEach((s, i) => { if (!siteExists(s)) push('PURPOSE_STALE_SITE', ['providerHelpers', i], `provider helper ${s.path}::${s.function} doesn't exist`); });
  reg.providerSupport.forEach((s, i) => { if (!siteExists(s)) push('PURPOSE_STALE_SITE', ['providerSupport', i], `${s.path}::${s.function} doesn't exist`); });
  reg.purposes.forEach((p, i) => {
    const parts = ['purposes', i];
    if (ids.has(p.id)) push('PRIVACY_DUPLICATE', [...parts, 'id'], `${p.id} is registered twice`);
    ids.add(p.id);
    const owner = resolveLeaf(p.owner);
    if (!owner.ok) push('PRIVACY_OWNERLESS', [...parts, 'owner'], `${p.id} owner: ${owner.reason}`);
    if (p.status === 'legacy' && !LEGACY_BASELINE.includes(p.id)) push('PRIVACY_LEGACY_OUTSIDE_BASELINE', [...parts, 'status'], `${p.id} is legacy, but only the sixteen baseline purposes may be`);
    if (p.status === 'legacy' && ['current', 'retired'].includes(baseStatus.get(p.id))) push('PRIVACY_LEGACY_OUTSIDE_BASELINE', [...parts, 'status'], `${p.id} was ${baseStatus.get(p.id)} on the base branch and can't go back to legacy`);
    if ((p.status === 'legacy') !== (p.consent === 'legacy-implicit')) push('PRIVACY_SCHEMA_INVALID', [...parts, 'consent'], `${p.id}: legacy purposes and only they take legacy-implicit consent`);
    if (p.batchMax && policy && p.batchMax > policy.consent.batchMax) push('PRIVACY_SCHEMA_INVALID', [...parts, 'batchMax'], `${p.id} batch ${p.batchMax} exceeds the policy's ${policy.consent.batchMax}`);
    if (p.credential && R && R.resolve(p.credential)?.class !== 'Secret') push('PRIVACY_UNKNOWN_REF', [...parts, 'credential'], `${p.id} credential ${p.credential} is not a Secret field`);
    const classes = new Set();
    p.inputs.forEach((input, j) => {
      const malformed = callerIdError(input.field);
      if (malformed) { push('PRIVACY_FIELD_ID_INVALID', [...parts, 'inputs', j], `${p.id} input ${input.field} ${malformed}`); return; }
      const e = R?.resolve(input.field);
      if (R && !e) { push('PRIVACY_UNKNOWN_REF', [...parts, 'inputs', j], `${p.id} input ${input.field} has no class in the field map`); return; }
      if (!e) return;
      if (e.class) classes.add(e.class);
      if (e.class === 'Secret') push('PRIVACY_SECRET_INPUT', [...parts, 'inputs', j], `${p.id} sends ${input.field}, a Secret, as content`);
      if (e.visibility === 'server-only') push('PRIVACY_SERVER_ONLY_INPUT', [...parts, 'inputs', j], `${p.id} sends ${input.field}, which is server-only`);
      // An input sends everything below it too.
      const below = descendantsOf(input.field, P.fieldMap.entries, R.byId);
      for (const d of below) if (d.entry.class) classes.add(d.entry.class);
      const secret = below.find((d) => d.entry.class === 'Secret');
      if (secret) push('PRIVACY_SECRET_INPUT', [...parts, 'inputs', j], `${p.id} sends ${input.field}, which holds ${secret.id}, a Secret`);
      const serverOnly = below.find((d) => d.entry.visibility === 'server-only');
      if (serverOnly) push('PRIVACY_SERVER_ONLY_INPUT', [...parts, 'inputs', j], `${p.id} sends ${input.field}, which holds ${serverOnly.id}, a server-only field`);
      const rubric = /(^def:harness-revision#\/rubric$)|(^pb:[a-z_]+\.rubric$)/.test(input.field);
      if (rubric && !GRADE_PURPOSES.includes(p.id)) push('PRIVACY_RUBRIC_OUTSIDE_GRADE', [...parts, 'inputs', j], `${p.id} sends a rubric; only ${GRADE_PURPOSES.join(' and ')} may`);
    });
    for (const c of classes) if (!p.classes.includes(c)) push('PRIVACY_PURPOSE_CLASSES', [...parts, 'classes'], `${p.id} sends ${c} fields but doesn't list the class`);
    p.callSites.forEach((s, j) => { if (!siteExists(s)) push('PURPOSE_STALE_SITE', [...parts, 'callSites', j], `${p.id} call site ${s.path}::${s.function} doesn't exist`); });
  });
  for (const id of LEGACY_BASELINE) if (!ids.has(id)) push('PRIVACY_UNKNOWN_REF', ['purposes'], `baseline purpose ${id} is not registered; retire it instead of removing it`);
  if (ctx.exists(LEGACY_PURPOSES_MIRROR)) {
    try {
      const mirror = ctx.readJson(LEGACY_PURPOSES_MIRROR);
      const list = (Array.isArray(mirror) ? mirror : mirror.purposes || []).map((x) => (typeof x === 'string' ? x : x.id)).sort();
      const legacy = reg.purposes.filter((p) => p.status === 'legacy').map((p) => p.id).sort();
      if (list.join() !== legacy.join()) F.push(finding('PRIVACY_LEGACY_MIRROR', LEGACY_PURPOSES_MIRROR, 1, `must list exactly the legacy purposes in ${PURPOSES_PATH}`));
    } catch (err) {
      F.push(finding('PRIVACY_LEGACY_MIRROR', LEGACY_PURPOSES_MIRROR, 1, `is unreadable: ${err.message}`));
    }
  }
  // The scan: every provider helper reference sits in a registered function.
  const allowed = new Set([...reg.purposes.flatMap((p) => p.callSites), ...reg.providerHelpers, ...reg.providerSupport].map((s) => `${s.path}::${s.function}`));
  const inside = new Set([...reg.providerHelpers, ...reg.providerSupport].map((s) => `${s.path}::${s.function}`));
  const refs = scanProviderCalls(ctx, reg);
  A.callRefs = refs;
  for (const r of refs) {
    const key = `${r.path}::${r.function}`;
    if (r.kind === 'helper' && !allowed.has(key)) F.push(finding('PURPOSE_UNREGISTERED_CALL', r.path, r.line, `${r.name} is called from ${r.function || 'module level'}, which no purpose in ${PURPOSES_PATH} registers`));
    if (r.kind === 'wrapper' && !allowed.has(key)) F.push(finding('PURPOSE_UNREGISTERED_CALL', r.path, r.line, `${r.function || 'module level'} calls ${r.name}, a registered call site that reaches a provider; register this caller in ${PURPOSES_PATH} too`));
    if (r.kind === 'vendor' && !inside.has(key)) F.push(finding('PURPOSE_UNREGISTERED_CALL', r.path, r.line, `a provider API is used in ${r.function || 'module level'}, outside the provider helpers ${PURPOSES_PATH} names`));
  }
  const reached = new Set(refs.filter((r) => r.kind === 'helper' || r.kind === 'wrapper').map((r) => `${r.path}::${r.function}`));
  reg.purposes.forEach((p, i) => p.callSites.forEach((s, j) => {
    if (siteExists(s) && !reached.has(`${s.path}::${s.function}`)) push('PURPOSE_STALE_SITE', ['purposes', i, 'callSites', j], `${p.id} call site ${s.path}::${s.function} calls no provider helper`);
  }));
}

// ------------------------------------------------------------ register

function detections(ctx, P, A) {
  const out = [];
  const R = A.resolver;
  if (!R) return out;
  if (A.storage) {
    for (const [family, f] of A.storage.families) {
      const e = R.byId.get(`storage:${family}`);
      if (e && (e.class === 'Secret' || e.visibility === 'server-only') && f.writes.length) out.push({ detector: 'secret-storage', target: `storage:${family}`, message: `browser storage key family ${family} holds ${e.class || e.visibility} data` });
    }
  }
  if (A.schema?.ok) {
    // A rule that admits only a platform service identity isn't a client read.
    const serviceOnly = (rule) => {
      const m = /^@request\.auth\.collectionName\s*=\s*["']([a-z_][a-z0-9_]*)["']$/.exec(String(rule).trim());
      return Boolean(m && R.byId.get(`pb:${m[1]}`)?.visibility === 'server-only');
    };
    const clientRule = (rule) => rule !== null && !serviceOnly(rule);
    const readable = new Map(A.schema.collections.map((c) => [c.name, clientRule(c.listRule) || clientRule(c.viewRule)]));
    for (const e of P.fieldMap.entries) {
      if (e.visibility !== 'server-only' || !e.id.startsWith('pb:')) continue;
      const coll = e.id.slice(3).split(/[.#]/)[0];
      if (readable.get(coll)) out.push({ detector: 'server-only-readable', target: e.id, message: `${e.id} is server-only, but ${coll} has a client read rule` });
    }
  }
  for (const p of P.purposes?.purposes || []) if (p.consent === 'legacy-implicit') out.push({ detector: 'legacy-consent', target: p.id, message: `${p.id} sends without per-request consent` });
  return out;
}

function covers(entry, target) {
  const loc = entry.location || {};
  if ((loc.purposes || []).includes(target)) return true;
  return (loc.fields || []).some((f) => {
    if (f === target) return true;
    const [base] = split(target);
    if (f === base) return true;
    if (f.startsWith('storage:') && target.startsWith('storage:')) return familyCovers(f.slice(8), target.slice(8));
    return false;
  });
}

function checkViolations(ctx, P, F, A, resolveLeaf) {
  const reg = P.violations;
  if (!reg) return;
  const file = P.violationsPath;
  const push = (code, parts, message) => F.push(finding(code, file, at(P, file, parts), message));
  const { ruleIds } = policyIndex(P.policy);
  const ids = new Set();
  const live = new Set();
  if (A.schema?.ok) for (const c of A.schema.collections) { live.add(`pb:${c.name}`); for (const f of c.fields) live.add(`pb:${c.name}.${f.name}`); }
  const purposeIds = new Set((P.purposes?.purposes || []).map((p) => p.id));
  reg.entries.forEach((v, i) => {
    const parts = ['entries', i];
    if (ids.has(v.id)) push('PRIVACY_DUPLICATE', [...parts, 'id'], `register entry ${v.id} is listed twice`);
    ids.add(v.id);
    if (!ruleIds.has(v.rule)) push('PRIVACY_UNKNOWN_REF', [...parts, 'rule'], `entry ${v.id} breaks rule ${v.rule}, which the policy doesn't define`);
    const owner = resolveLeaf(v.owner);
    if (!owner.ok) push('PRIVACY_OWNERLESS', [...parts, 'owner'], `entry ${v.id} owner: ${owner.reason}`);
    if (!Object.keys(v.location || {}).length) push('PRIVACY_SCHEMA_INVALID', [...parts, 'location'], `entry ${v.id} names no location`);
    if (v.status === 'closed') {
      if (!v.history.length) push('PRIVACY_CLOSED_WITHOUT_PR', [...parts, 'history'], `entry ${v.id} is closed but names no fixing PR`);
      for (const m of v.location.migrations || []) if (!ctx.exists(m)) push('PRIVACY_UNKNOWN_REF', [...parts, 'location'], `entry ${v.id} names ${m}, which does not exist`);
      return;
    }
    // An open entry's location must still exist, or the entry is stale.
    for (const f of v.location.fields || []) {
      const [base] = split(f);
      const known = A.resolver?.resolve(f) && (!base.startsWith('pb:') || !A.schema?.ok || live.has(base));
      const storageLive = !f.startsWith('storage:') || !A.storage || A.storage.families.has(f.slice(8));
      if (!known || !storageLive) push('PRIVACY_VIOLATION_STALE', [...parts, 'location'], `entry ${v.id} names ${f}, which no longer exists; close the entry with its fixing PR`);
    }
    for (const a of v.location.anchors || []) {
      if (!ctx.exists(a.path) || !ctx.read(a.path).includes(a.text)) push('PRIVACY_VIOLATION_STALE', [...parts, 'location'], `entry ${v.id}'s anchor is gone from ${a.path}; close the entry with its fixing PR`);
    }
    for (const p of v.location.purposes || []) if (!purposeIds.has(p)) push('PRIVACY_VIOLATION_STALE', [...parts, 'location'], `entry ${v.id} names purpose ${p}, which is not registered`);
    for (const m of v.location.migrations || []) if (!ctx.exists(m)) push('PRIVACY_UNKNOWN_REF', [...parts, 'location'], `entry ${v.id} names ${m}, which does not exist`);
  });
  const found = detections(ctx, P, A);
  A.detections = found;
  for (const d of found) {
    const hit = reg.entries.some((v) => v.status === 'open' && v.detector === d.detector && covers(v, d.target));
    if (!hit) F.push(finding('PRIVACY_VIOLATION_UNREGISTERED', file, at(P, file, ['entries']), `${d.message}; register it with its owner and exit, or fix it`));
  }
  reg.entries.forEach((v, i) => {
    if (v.status !== 'open' || !v.detector) return;
    if (!found.some((d) => d.detector === v.detector && covers(v, d.target))) push('PRIVACY_VIOLATION_STALE', ['entries', i], `entry ${v.id}'s breach is no longer found; close it with its fixing PR`);
  });
}

// ------------------------------------------------------------ versions, record, base

function readBaseJson(ctx, rel) {
  const b = ctx.readBase(rel);
  if (!b.ok || b.content === null) return null;
  try { return JSON.parse(b.content); } catch { return null; }
}

function checkPins(ctx, P, F) {
  const policy = P.policy;
  if (!policy) return;
  const versions = new Map(policy.versions.map((v) => [v.id, v]));
  const testPath = /(^|\/)(tests?|__tests__|fixtures)\//;
  for (const file of ctx.files().filter((f) => PIN_FILES.test(f) && !COPY_DIRS.some((d) => f.startsWith(`${d}/`)) && !testPath.test(f))) {
    const text = ctx.read(file);
    if (!PIN.test(text)) continue;
    PIN.lastIndex = 0;
    text.split('\n').forEach((line, i) => {
      for (const m of line.matchAll(PIN)) {
        const v = versions.get(m[1]);
        const n = Number(m[2]);
        const rev = v?.revisions.find((r) => r.revision === n);
        if (!rev) F.push(finding('PRIVACY_UNKNOWN_PIN', file, i + 1, `${m[0]} is not a ${m[1]} revision; the policy has ${v ? v.revisions.map((r) => `${m[1]}@${r.revision}`).join(', ') : 'none'}`));
        else if (n !== v.current) {
          const current = v.revisions.find((r) => r.revision === v.current);
          if (!current?.compatibleWith.includes(n)) F.push(finding('PRIVACY_PIN_INCOMPATIBLE', file, i + 1, `${m[0]} was superseded by ${m[1]}@${v.current}, which isn't compatible with it; move to ${m[1]}@${v.current}`));
        }
      }
    });
  }
}

function checkRecord(ctx, P, F, resolveLeaf) {
  const records = ctx.files().filter((f) => path.posix.dirname(f) === 'docs/decisions' && /^DR-\d{4}-.*\.json$/.test(path.posix.basename(f)));
  let record = null;
  let file = null;
  for (const f of records) {
    try {
      const r = ctx.readJson(f);
      if (r.leaf === DR_LEAF) { record = r; file = f; }
    } catch { /* the decision-records rule reports it */ }
  }
  if (!record) { F.push(finding('PRIVACY_RECORD_MISSING', 'docs/decisions', 1, `no decision record names ${DR_LEAF}`)); return null; }
  const text = ctx.read(file);
  const push = (code, parts, message) => F.push(finding(code, file, jsonLine(text, parts), message));
  if (P.policy && record.id !== P.policy.decisionRecord) push('PRIVACY_UNKNOWN_REF', ['id'], `${POLICY_PATH} names ${P.policy.decisionRecord}, but the record is ${record.id}`);
  if (record.authorityBoundary !== POLICY_PATH) push('PRIVACY_RECORD_INCOMPLETE', ['authorityBoundary'], `the record's authority boundary must be ${POLICY_PATH}`);
  if (!record.owner || !String(record.owner).trim()) push('PRIVACY_RECORD_INCOMPLETE', ['owner'], 'the record names no owner');
  if (P.policy) for (const v of P.policy.versions) if (!String(record.versioning || '').includes(`${v.id}@${v.current}`)) push('PRIVACY_RECORD_INCOMPLETE', ['versioning'], `the record's versioning doesn't name ${v.id}@${v.current}`);
  if (!record.supersession) push('PRIVACY_RECORD_INCOMPLETE', ['supersession'], 'the record names no supersession rule');
  (record.decisions || []).forEach((d, i) => { if (!(d.alternatives || []).length) push('PRIVACY_RECORD_INCOMPLETE', ['decisions', i, 'alternatives'], `${d.id} lists no alternatives`); });
  if (P.policy) {
    const leaves = new Set([...P.policy.sinks.map((s) => s.enforcingLeaf), ...[...P.policy.lifecycle.rows, ...P.policy.lifecycle.decided].flatMap((r) => r.enforcement.map((e) => e.leaf))]);
    for (const leaf of leaves) if (!(record.consumers || []).includes(leaf)) push('PRIVACY_RECORD_INCOMPLETE', ['consumers'], `enforcing leaf ${leaf} is not among the record's consumers`);
  }
  if (record.status === 'ratified') {
    const governed = new Set((record.approvalRef?.governedFiles || []).map((g) => g.path));
    for (const f of [POLICY_PATH, SCHEMA_PATH]) if (!governed.has(f)) push('PRIVACY_RECORD_INCOMPLETE', ['approvalRef'], `a ratified record pins ${f}`);
  }
  // The policy's current revisions and the record are ratified together.
  if (P.policy && record.status !== 'superseded') {
    const want = record.status === 'ratified' ? 'ratified' : 'draft';
    for (const v of P.policy.versions) {
      const cur = v.revisions.find((r) => r.revision === v.current);
      if (cur && cur.status !== want) push('PRIVACY_STATUS_MISMATCH', ['status'], `${POLICY_PATH} marks ${v.id}@${v.current} ${cur.status}, but the record is ${record.status}; they're ratified together`);
    }
  }
  return { record, file };
}

// Relaxing changes against the base branch need a relaxations entry with
// a spec change and an approval reference (Decision 6).
// Why head entry `h` is looser than base entry `b`, or null. Beyond the
// class and visibility order, a kind change that a sink's rule lets through
// where it stopped the old kind (logs take metadata or ids, never content)
// is looser too.
function looserEntry(h, b, policy) {
  // A tighter class or visibility can still come with a kind that opens a
  // sink, so only a looser one returns here.
  let tightened = false;
  if (b.class && h.class && b.class !== h.class) {
    const loosened = (b.class === 'Share Projection' || h.class === 'Share Projection') ? !(h.class === 'Secret') : CLASS_ORDER.indexOf(h.class) < CLASS_ORDER.indexOf(b.class);
    if (loosened) return `is ${h.class}, looser than ${b.class}`;
    tightened = true;
  }
  if (b.visibility && h.visibility && b.visibility !== h.visibility) {
    if (VISIBILITY_ORDER.indexOf(h.visibility) < VISIBILITY_ORDER.indexOf(b.visibility)) return `is ${h.visibility}, looser than ${b.visibility}`;
    tightened = true;
  }
  if (Boolean(b.class) !== Boolean(h.class)) return 'changed family';
  if (b.kind === h.kind) return null;
  if (!tightened && b.kind === 'content') return `is ${h.kind}, where it was content`;
  // Each side's rule comes from its own class or visibility.
  const { cells, visibility } = policyIndex(policy);
  const sinks = h.class ? CLASS_SINKS : VISIBILITY_SINKS;
  const ruleOf = (e, s) => (e.class ? cells.get(`${e.class}|${s}`) : visibility.get(`${e.visibility}|${s}`))?.rule;
  const takes = (rule, kind) => rule?.decision === 'allow-if' && rule.cases.some((c) => c.when.kind === kind);
  const opened = sinks.filter((s) => takes(ruleOf(h, s), h.kind) && !takes(ruleOf(b, s), b.kind));
  const as = tightened ? ` as ${h.class || h.visibility}` : '';
  return opened.length ? `is ${h.kind}${as}, which ${opened.join(' and ')} take${opened.length === 1 ? 's' : ''} where ${b.kind} was stopped` : null;
}

const locationItems = (v) => [
  ...(v.location?.fields || []), ...(v.location?.purposes || []), ...(v.location?.migrations || []),
  ...(v.location?.anchors || []).map((a) => `${a.path}: ${a.text}`),
];

function relaxations(ctx, P) {
  const out = [];
  const baseMap = readBaseJson(ctx, FIELD_MAP_PATH);
  if (baseMap && P.fieldMap && P.policy) {
    const head = new Map(P.fieldMap.entries.map((e) => [e.id, e]));
    const R = fieldResolver(P.fieldMap.entries);
    for (const b of baseMap.entries || []) {
      const h = head.get(b.id);
      if (h) {
        const why = looserEntry(h, b, P.policy);
        if (why) out.push({ target: b.id, what: `${b.id} ${why}` });
        continue;
      }
      // A removed entry's id now takes whatever entry is left above it.
      const r = R.resolve(b.id);
      const why = r ? looserEntry(r, b, P.policy) : null;
      if (why) out.push({ target: b.id, what: `${b.id} was removed, so it now resolves to ${r.id}, which ${why}` });
    }
  }
  const baseRegister = readBaseJson(ctx, VIOLATIONS_PATH);
  if (baseRegister && P.violations) {
    const head = new Map(P.violations.entries.map((v) => [v.id, v]));
    for (const b of baseRegister.entries || []) {
      const h = head.get(b.id);
      const target = `violation:${b.id}`;
      if (!h) { out.push({ target, what: `register entry ${b.id} was removed; an entry is closed with its fixing PR, never deleted` }); continue; }
      if (b.status !== 'open' || h.status !== 'open') continue;
      if (h.owner !== b.owner) out.push({ target, what: `open register entry ${b.id} moved from ${b.owner} to ${h.owner}` });
      if (b.detector && h.detector !== b.detector) out.push({ target, what: `open register entry ${b.id} dropped its ${b.detector} detector` });
      const kept = new Set(locationItems(h));
      const lost = locationItems(b).filter((x) => !kept.has(x));
      if (lost.length) out.push({ target, what: `open register entry ${b.id} no longer names ${lost.join('; ')}` });
    }
  }
  const basePatterns = readBaseJson(ctx, SECRET_PATTERNS_PATH);
  if (basePatterns && P.secretPatterns) {
    const head = new Map(P.secretPatterns.patterns.map((p) => [p.id, p]));
    for (const b of basePatterns.patterns || []) {
      const h = head.get(b.id);
      if (!h) out.push({ target: `pattern:${b.id}`, what: `secret pattern ${b.id} was removed` });
      else if (h.regex !== b.regex) out.push({ target: `pattern:${b.id}`, what: `secret pattern ${b.id} changed, so it may match less` });
    }
  }
  const basePolicy = readBaseJson(ctx, POLICY_PATH);
  if (basePolicy && P.policy) {
    const bi = policyIndex(basePolicy);
    const hi = policyIndex(P.policy);
    for (const [key, b] of [...bi.cells, ...bi.visibility]) {
      const h = hi.cells.get(key) || hi.visibility.get(key);
      if (h && !ruleTighterOrEqual(h.rule, b.rule)) out.push({ target: b.id, what: `${b.id} allows more than it did` });
    }
    for (const [id, b] of bi.rows) {
      const h = hi.rows.get(id);
      if (!h || !b.retention || !h.retention) continue;
      if (longer(h.retention, b.retention) || (h.purgeWithinHours ?? 0) > (b.purgeWithinHours ?? 0)) out.push({ target: id, what: `lifecycle row ${id} keeps data longer than it did` });
      for (const [cls, days] of Object.entries(b.maxDaysByClass || {})) if ((h.maxDaysByClass || {})[cls] === undefined || h.maxDaysByClass[cls] > days) out.push({ target: id, what: `lifecycle row ${id} raised the ${cls} maximum` });
    }
  }
  const basePurposes = readBaseJson(ctx, PURPOSES_PATH);
  if (basePurposes && P.purposes) {
    const head = new Map(P.purposes.purposes.map((p) => [p.id, p]));
    for (const b of basePurposes.purposes || []) {
      const h = head.get(b.id);
      if (!h) continue;
      const bin = new Map(b.inputs.map((x) => [x.field, x]));
      // An input under one the purpose already sent narrows it; that's no loosening.
      for (const x of h.inputs) {
        if (bin.has(x.field) || b.inputs.some((y) => !y.omit && within(x.field, y.field))) continue;
        out.push({ target: b.id, what: `${b.id} sends ${x.field}, which it didn't` });
      }
      for (const x of b.inputs) if (x.omit && !h.inputs.some((y) => y.field === x.field && y.omit)) out.push({ target: b.id, what: `${b.id} no longer omits ${x.field}` });
      if ((h.batchMax || 1) > (b.batchMax || 1)) out.push({ target: b.id, what: `${b.id} raised its batch cap` });
      if (b.consent === 'per-request' && h.consent === 'none') out.push({ target: b.id, what: `${b.id} dropped per-request consent` });
    }
  }
  return out;
}

function longer(h, b) {
  const max = (s) => (s.range ? s.range[1] : Math.max(...(s.choices || [s.default]).filter((x) => Number.isInteger(x)), 0));
  const unbounded = (s) => (s.choices || []).some((x) => x === 'pinned' || x === 'until-delete');
  if (unbounded(h) && !unbounded(b)) return true;
  if (max(h) > max(b)) return true;
  return Number.isInteger(h.default) && Number.isInteger(b.default) && h.default > b.default;
}

export function ruleTighterOrEqual(o, b) {
  if (o.decision === 'deny') return true;
  if (b.decision === 'deny') return false;
  const sup = (x, y) => y.every((v) => x.includes(v));
  const caseTighter = (c, bc) => Object.entries(bc.when).every(([k, v]) => c.when[k] === v) && sup(c.obligations, bc.obligations);
  if (o.decision === 'allow') return b.decision === 'allow' && sup(o.obligations, b.obligations);
  if (o.decision === 'allow-if') {
    if (b.decision === 'allow') return o.cases.every((c) => sup(c.obligations, b.obligations));
    if (b.decision === 'allow-if') return o.cases.every((c) => b.cases.some((bc) => caseTighter(c, bc)));
    return false;
  }
  if (o.decision === 'allow-with-consent') return b.decision === 'allow-with-consent' && o.consent === b.consent && sup(o.obligations, b.obligations);
  return false;
}

function checkRelaxations(ctx, P, F) {
  if (!P.policy) return;
  const approved = new Set(P.policy.relaxations.map((r) => r.target));
  for (const r of relaxations(ctx, P)) {
    if (!approved.has(r.target)) F.push(finding('PRIVACY_RELAXED', POLICY_PATH, at(P, POLICY_PATH, ['relaxations']), `${r.what}; loosening needs a spec change and an approval reference in relaxations`));
  }
}

// ------------------------------------------------------------ authority cells and secrets

function checkAuthorityCells(ctx, F) {
  let matrix;
  try { matrix = ctx.readJson(MATRIX_PATH); } catch { return; }
  const text = ctx.read(MATRIX_PATH);
  // This leaf owns the cells ROUNDS-01-L02 left pending on it.
  (matrix.rows || []).forEach((r, i) => {
    if (r.field_map === `pending:${DR_LEAF}`) F.push(finding('PRIVACY_FIELD_MAP_CELL', MATRIX_PATH, jsonLine(text, ['rows', i, 'field_map']), `${r.id}'s field_map cell is still pending on ${DR_LEAF}; point it at ${FIELD_MAP_PATH}`));
  });
}

function checkSecrets(ctx, P, F, record) {
  if (!P.secretPatterns) return;
  let patterns;
  try {
    patterns = P.secretPatterns.patterns.map((p) => ({ id: p.id, re: new RegExp(p.regex, 'g') }));
  } catch (err) {
    F.push(finding('PRIVACY_SCHEMA_INVALID', SECRET_PATTERNS_PATH, 1, `a pattern doesn't compile: ${err.message}`));
    return;
  }
  const docs = [DOC_PATH, CONFIG_DOC_PATH].filter((f) => ctx.exists(f));
  const files = [...Object.keys(P.texts), ...(record ? [record.file] : []), ...docs].filter((f, i, a) => a.indexOf(f) === i);
  for (const f of files) {
    const text = P.texts[f] ?? ctx.read(f);
    text.split('\n').forEach((line, i) => {
      for (const p of patterns) {
        p.re.lastIndex = 0;
        if (p.re.test(line)) F.push(finding('PRIVACY_SECRET_VALUE', f, i + 1, `holds something shaped like a ${p.id}; fixtures are synthetic and stored as parts`));
      }
    });
  }
}

// ------------------------------------------------------------ vectors

const rangeList = (ranges) => {
  const list = new BlockList();
  for (const r of ranges) {
    const [a, prefix] = r.split('/');
    const type = isIP(a) === 6 ? 'ipv6' : 'ipv4';
    if (prefix) list.addSubnet(a, Number(prefix), type);
    else list.addAddress(a, type);
  }
  return list;
};
const listed = (list, address) => {
  const a = String(address).split('%')[0];
  const v = isIP(a);
  return v ? list.check(a, v === 6 ? 'ipv6' : 'ipv4') : false;
};

// The shared vectors cover every never destination, every lifecycle row
// (its default, an allowed value, a value out of bounds, and a purge
// deadline), and every secret pattern.
function checkVectors(P, F) {
  const policy = P.policy;
  if (!policy || !P.vectors.length) return;
  const cases = P.vectors.flatMap((v) => (v.data.cases || []).map((c) => ({ ...c, file: v.file })));
  const where = (suite) => P.vectors.find((v) => v.data.suite === suite)?.file || `${PRIVACY_DIR}/vectors`;
  const push = (suite, message) => F.push(finding('PRIVACY_VECTORS_INCOMPLETE', where(suite), 1, message));
  const never = cases.filter((c) => c.expect?.code === 'DESTINATION_NEVER');
  const hosts = (c) => [c.args?.host, c.args?.endpoint?.host].filter((h) => typeof h === 'string').map((h) => h.toLowerCase().replace(/^\[|\]$/g, ''));
  const addresses = (c) => [...(c.args?.addresses || []), ...(c.args?.endpoint?.addresses || [])];
  const n = policy.locations.never;
  for (const range of [...n.loopback, ...n.linkLocal, ...n.unspecified, ...n.metadata]) {
    const list = rangeList([range]);
    if (!never.some((c) => addresses(c).some((a) => listed(list, a)))) push('destinations', `no vector answers DESTINATION_NEVER for an address in ${range}`);
  }
  for (const name of n.serviceNames) if (!never.some((c) => hosts(c).includes(name))) push('destinations', `no vector answers DESTINATION_NEVER for the service name ${name}`);
  for (const suffix of n.serviceSuffixes) if (!never.some((c) => hosts(c).some((h) => h.endsWith(suffix)))) push('destinations', `no vector answers DESTINATION_NEVER for a name ending ${suffix}`);
  const retention = cases.filter((c) => c.call === 'evaluate_retention');
  for (const row of [...policy.lifecycle.rows, ...policy.lifecycle.decided]) {
    const mine = retention.filter((c) => c.args?.row_id === row.id);
    const unset = (c) => c.args.value === null || c.args.value === undefined;
    if (!mine.some(unset)) push('retention', `lifecycle row ${row.id} has no default case`);
    if (!mine.some((c) => !unset(c) && c.expect?.decision === 'allow')) push('retention', `lifecycle row ${row.id} has no allowed-value case`);
    if (!mine.some((c) => c.expect?.code === 'OUT_OF_BOUNDS')) push('retention', `lifecycle row ${row.id} has no out-of-bound case`);
    if (!mine.some((c) => c.expect && 'purge_by' in c.expect)) push('retention', `lifecycle row ${row.id} has no case that checks purge_by`);
  }
  const s = P.secretPatterns;
  if (s) {
    for (const p of s.patterns) {
      if (!s.fixtures.some((x) => x.pattern === p.id)) push('secrets', `secret pattern ${p.id} has no fixture`);
      if (!s.nearMisses.some((x) => x.pattern === p.id)) push('secrets', `secret pattern ${p.id} has no near miss`);
    }
  }
}

// ------------------------------------------------------------ all

export function analyze(ctx) {
  const F = [];
  const A = {};
  const resolveLeaf = leafResolver(loadLeafIds(ctx));
  const P = loadPrivacy(ctx, F);
  A.P = P;
  checkPolicy(ctx, P, F, resolveLeaf);
  checkFieldMap(ctx, P, F, A);
  checkPurposes(ctx, P, F, A, resolveLeaf);
  checkViolations(ctx, P, F, A, resolveLeaf);
  checkPins(ctx, P, F);
  A.record = checkRecord(ctx, P, F, resolveLeaf);
  checkRelaxations(ctx, P, F);
  checkAuthorityCells(ctx, F);
  checkSecrets(ctx, P, F, A.record);
  checkVectors(P, F);
  for (const f of staleCopies(ctx)) F.push(finding('PRIVACY_COPY_STALE', f, 1, `copies a file ${PRIVACY_DIR} no longer has; delete the copy`));
  return { findings: F, A };
}
