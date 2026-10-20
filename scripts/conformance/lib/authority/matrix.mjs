// Authority matrix checks (ROUNDS-01-L02, DR-0002): #16's rules 1 to 12, the
// coverage of the audited revision's stores, citations, secrets, open owner
// decisions, owner labels, the owner-sentence corrections, and revisions
// against the base branch. Node built-ins only.
//
// Each check reads the loaded files defensively, so a malformed file yields
// findings rather than an exception.

import fs from 'node:fs';
import path from 'node:path';
import { canonical, finding, jsonLine, sha256 } from '../context.mjs';
import { validate } from '../json-schema.mjs';
import { leafResolver, loadLeafIds } from '../leaf-ids.mjs';
import { BASELINE_STORES_PATH, extractBaselineStores } from './stores.mjs';

export { BASELINE_STORES_PATH };
export const MATRIX_PATH = 'contracts/authority/matrix.json';
export const PACKAGES_PATH = 'contracts/authority/packages.json';
export const OWNER_LABELS_PATH = 'contracts/authority/owner-labels.json';
export const LEDGER_PATH = 'contracts/authority/disposition-ledger.json';
export const CORRECTIONS_PATH = 'contracts/authority/owner-sentence-corrections.json';
export const DR_PATH = 'docs/decisions/DR-0002-authority-matrix.json';
export const AUTHORITY_MD = 'docs/authority.md';
const TERMS_PATH = 'contracts/vocabulary/terms.json';
const ADAPTERS_PATH = 'contracts/vocabulary/adapters.json';

export const DATA_FILES = [
  { key: 'matrix', path: MATRIX_PATH },
  { key: 'packages', path: PACKAGES_PATH },
  { key: 'labels', path: OWNER_LABELS_PATH },
  { key: 'ledger', path: LEDGER_PATH },
  { key: 'stores', path: BASELINE_STORES_PATH },
  { key: 'corrections', path: CORRECTIONS_PATH },
].map((f) => ({ ...f, schema: f.path.replace(/\.json$/, '.schema.json') }));

// The spec's Authority Matrix table (spec 781-811), service list (spec
// 1919-1935), and read models (spec 1970-1980).
export const SPEC_ROWS = { from: 781, to: 811 };
export const SPEC_SERVICES = { from: 1919, to: 1935 };
export const SPEC_READ_MODELS = [
  'Today', 'Career Profile overview', 'Pipeline', 'Opportunity Workspace', 'Material-use graph',
  'Preparation plan', 'Readiness', 'Search index', 'Data Health',
];
// Issue #16's C1 to C13 are facts about the audited revision, so they stay
// flagged while the matrix audits it.
export const BASELINE_CONFLICTS = { revision: '62d4eae', ids: Array.from({ length: 13 }, (_, i) => `C${i + 1}`) };
export const OPEN_DECISIONS = ['OD-1', 'OD-2', 'OD-3', 'OD-4', 'OD-5'];
const OD_STATUS = { blocked: 'draft', settled: 'ratified', 'default-taken': 'ratified-here' };
// rounds-review files that --review checks.
export const REVIEW_SPEC = 'docs/superpowers/specs/2026-10-18-rounds-review-board-design.md';
export const REVIEW_LEDGER = 'src/data/dispositionLedger.ts';

const CONTAINED = ['test-definition', 'harness-revision']; // rule 10
const SECRET_CONSUMERS = new Set(['verifier', 'gateway']); // rule 4
const PROJECTION_CONSUMERS = new Set(['read-model', 'search-index']);
// Changing any of these on a row is breaking (#16 AC 9).
export const BREAKING_FIELDS = ['command_owner', 'target_authority', 'privacy_floor', 'visibility', 'scope', 'package'];
const NEW_CONCEPT = /^new-platform-concept:(INT-02|INT-03)$/;

const PENDING = /^pending:(ROUNDS-\d{2}[A-Z]?-L\d{2})$/;
const BLOCKED = /^blocked:(OD-\d+)$/;
const NA = /^n\/a:\S/;
const LEAF_REFS = /ROUNDS-\d{2}[A-Z]?-L\d{2}(?:\/[A-Za-z0-9.]+)?/g;
const CAPABILITY = /^ROUNDS-\d{2}[A-Z]?$/;

export const isNote = (v) => typeof v === 'string' && (PENDING.test(v) || BLOCKED.test(v) || NA.test(v));
export const isBlocked = (v) => typeof v === 'string' && BLOCKED.test(v);
export const capabilityOf = (leaf) => (typeof leaf === 'string' ? leaf.replace(/-L\d{2}(\/.*)?$/, '') : null);
const isObject = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);
const list = (v) => (Array.isArray(v) ? v : []);
const empty = (v) => v === null || (typeof v === 'string' && !v.trim());

function walk(value, at, visit) {
  visit(value, at);
  if (Array.isArray(value)) value.forEach((v, i) => walk(v, [...at, i], visit));
  else if (isObject(value)) for (const [k, v] of Object.entries(value)) walk(v, [...at, k], visit);
}

function pointerParts(pointer) {
  return pointer.split('/').slice(1).map((p) => p.replace(/~1/g, '/').replace(/~0/g, '~')).map((p) => (/^\d+$/.test(p) ? Number(p) : p));
}

function valueAt(value, parts) {
  let v = value;
  for (const p of parts) v = v === null || v === undefined ? undefined : v[p];
  return v;
}

const where = (parts) => `/${parts.join('/')}`;
const EMPTY_MESSAGE = (parts) => `${where(parts)} is empty; write a value, pending:<leaf-id>, n/a:<reason>, or blocked:OD-<n>`;

// -------------------------------------------------------------- loading

// Loads the authority files, validates each against its schema, and indexes
// rows, conflicts, packages, labels, and decisions. `A.push(code, file,
// parts|line, message)` records a finding at a JSON path's line.
export function loadAuthority(ctx, findings) {
  const A = { texts: {} };
  const seen = new Set();
  A.push = (code, file, at, message) => {
    const text = A.texts[file];
    const line = typeof at === 'number' ? at : text && Array.isArray(at) ? jsonLine(text, at) : 1;
    const key = `${code}\0${file}\0${line}\0${message}`;
    if (seen.has(key)) return;
    seen.add(key);
    findings.push(finding(code, file, line, message));
  };
  for (const f of DATA_FILES) {
    if (!ctx.exists(f.path)) { A.push('AUTH_SHAPE_INVALID', f.path, 1, `${f.path} is missing`); continue; }
    const text = ctx.read(f.path);
    A.texts[f.path] = text;
    let value;
    try {
      value = JSON.parse(text);
    } catch (err) {
      A.push('AUTH_SHAPE_INVALID', f.path, 1, `not valid JSON: ${err.message}`);
      continue;
    }
    A[f.key] = value;
    let errors;
    try {
      errors = validate(value, ctx.readJson(f.schema));
    } catch (err) {
      A.push('AUTH_SHAPE_INVALID', f.schema, 1, `${f.schema} is missing or invalid: ${err.message}`);
      continue;
    }
    for (const err of errors) {
      const parts = pointerParts(err.pointer);
      if (empty(valueAt(value, parts))) { A.push('AUTH_EMPTY_CELL', f.path, parts, EMPTY_MESSAGE(parts)); continue; }
      const code = err.keyword === 'required' && err.property === 'disposition' && f.key === 'matrix' && parts[0] === 'rows' ? 'AUTH_NO_DISPOSITION' : 'AUTH_SHAPE_INVALID';
      A.push(code, f.path, parts, `${err.pointer || '/'} ${err.message}`);
    }
  }
  if (ctx.exists(DR_PATH)) {
    A.texts[DR_PATH] = ctx.read(DR_PATH);
    try {
      A.dr = JSON.parse(A.texts[DR_PATH]);
    } catch {
      A.dr = null; // decision-records reports an unreadable record.
    }
  }
  A.leafIds = loadLeafIds(ctx);
  A.resolveLeaf = leafResolver(A.leafIds);
  try { A.terms = ctx.readJson(TERMS_PATH); } catch { A.terms = null; }
  try { A.adapters = ctx.readJson(ADAPTERS_PATH).adapters; } catch { A.adapters = null; }
  indexAuthority(A);
  return A;
}

function indexAuthority(A) {
  const m = isObject(A.matrix) ? A.matrix : {};
  A.rows = list(m.rows).filter(isObject);
  A.rowAt = new Map();
  list(m.rows).forEach((r, i) => { if (isObject(r) && typeof r.id === 'string' && !A.rowAt.has(r.id)) A.rowAt.set(r.id, i); });
  A.row = (id) => (A.rowAt.has(id) ? m.rows[A.rowAt.get(id)] : null);
  A.where = (id, ...rest) => ['rows', A.rowAt.has(id) ? A.rowAt.get(id) : 0, ...rest];
  A.conflicts = list(m.conflicts).filter(isObject);
  A.conflict = new Map(A.conflicts.map((c) => [c.id, c]));
  A.relations = list(m.relations).filter(isObject);
  A.readModels = list(m.readModels).filter(isObject);
  A.packageList = list(A.packages?.packages).filter(isObject);
  A.packageIds = new Set(A.packageList.map((p) => p.id).filter((x) => typeof x === 'string'));
  A.labelList = list(A.labels?.labels).filter(isObject);
  A.labelByCapability = new Map(A.labelList.map((l) => [l.capability, l]));
  A.ledgerIds = new Set(list(A.ledger?.rows).map((r) => r?.id).filter(Boolean));
  A.termIds = new Set(list(A.terms?.terms).map((t) => t?.id).filter(Boolean));
  A.storeList = list(A.stores?.stores).filter(isObject);
  A.decisions = new Map(list(A.dr?.decisions).filter(isObject).map((d) => [d.id, d]));
  A.leafIssue = new Map(list(A.leafIds?.leaves).map((l) => [l.id, l.issue]));
  A.capabilities = new Set(list(A.leafIds?.leaves).filter((l) => l.status !== 'rejected').map((l) => capabilityOf(l.id)));
  A.ownedBy = new Map();
  for (const r of A.rows) {
    if (isObject(r.command_owner) && typeof r.command_owner.leaf === 'string') {
      if (!A.ownedBy.has(r.command_owner.leaf)) A.ownedBy.set(r.command_owner.leaf, []);
      if (!A.ownedBy.get(r.command_owner.leaf).includes(r.id)) A.ownedBy.get(r.command_owner.leaf).push(r.id);
    }
  }
}

// ------------------------------------------------------------ identity

function duplicatesOf(items, keyOf) {
  const seen = new Map();
  const dups = [];
  items.forEach((item, i) => {
    const key = keyOf(item);
    if (key === undefined || key === null) return;
    if (seen.has(key)) dups.push({ key, i, first: seen.get(key) });
    else seen.set(key, i);
  });
  return dups;
}

export function checkIdentity(A) {
  const m = A.matrix || {};
  const groups = [
    [MATRIX_PATH, 'rows', list(m.rows), (x) => x?.id, 'row id'],
    [MATRIX_PATH, 'conflicts', list(m.conflicts), (x) => x?.id, 'conflict id'],
    [MATRIX_PATH, 'relations', list(m.relations), (x) => x?.id, 'relation id'],
    [MATRIX_PATH, 'relations', list(m.relations), (x) => (x?.from && x?.to ? [x.from, x.to].sort().join(' and ') : null), 'relation between'],
    [MATRIX_PATH, 'readModels', list(m.readModels), (x) => x?.name, 'read model'],
    [MATRIX_PATH, 'readModels', list(m.readModels), (x) => x?.row, 'read model row'],
    [PACKAGES_PATH, 'packages', A.packageList, (x) => x.id, 'package id'],
    [PACKAGES_PATH, 'packages', A.packageList, (x) => x.service, 'service'],
    [PACKAGES_PATH, 'packages', A.packageList, (x) => x.spec, 'service spec line'],
    [OWNER_LABELS_PATH, 'labels', A.labelList, (x) => x.capability, 'capability'],
    [OWNER_LABELS_PATH, 'labels', A.labelList, (x) => x.label, 'owner label'],
    [LEDGER_PATH, 'rows', list(A.ledger?.rows), (x) => x?.id, 'ledger id'],
    [BASELINE_STORES_PATH, 'stores', A.storeList, (x) => x.id, 'store id'],
    [CORRECTIONS_PATH, 'entries', list(A.corrections?.entries), (x) => x?.issue, 'correction for issue'],
  ];
  for (const [file, field, items, keyOf, what] of groups) {
    for (const d of duplicatesOf(items, keyOf)) A.push('AUTH_DUPLICATE_ID', file, [field, d.i], `${what} ${d.key} appears twice (entries ${d.first} and ${d.i})`);
  }
}

// ------------------------------------------------------------ spec rows

const SPEC_COLUMNS = ['information', 'authority', 'mutability', 'delete_merge', 'consumers'];

function specCells(line) {
  const cells = String(line || '').split('|').slice(1, -1).map((c) => c.trim());
  if (cells.length !== 5) return null;
  return Object.fromEntries(SPEC_COLUMNS.map((k, i) => [k, cells[i]]));
}

// The pinned form of spec 781-811: one line per row, its cells joined by " | ".
export function specRowsDigest(cellsByLine) {
  const lines = [];
  for (let line = SPEC_ROWS.from; line <= SPEC_ROWS.to; line++) {
    const cells = cellsByLine(line);
    lines.push(cells ? SPEC_COLUMNS.map((k) => cells[k]).join(' | ') : '');
  }
  return sha256(lines.join('\n'));
}

export function checkSpecRows(ctx, A) {
  const byLine = new Map();
  for (const r of A.rows) {
    const hasSpec = r.spec !== undefined;
    if (hasSpec === (r.summary !== undefined)) {
      A.push('AUTH_SHAPE_INVALID', MATRIX_PATH, A.where(r.id), `${r.id} has ${hasSpec ? 'both spec and summary' : 'neither spec nor summary'}; a spec row keeps the spec's five columns in spec, any other row describes itself in summary`);
    }
    if (!isObject(r.spec)) continue;
    const line = r.spec.line;
    if (!Number.isInteger(line) || line < SPEC_ROWS.from || line > SPEC_ROWS.to) {
      A.push('AUTH_SPEC_ROW_MISSING', MATRIX_PATH, A.where(r.id, 'spec'), `${r.id} names spec line ${line}, outside the Authority Matrix (spec ${SPEC_ROWS.from}-${SPEC_ROWS.to})`);
      continue;
    }
    if (!byLine.has(line)) byLine.set(line, []);
    byLine.get(line).push(r);
  }
  for (let line = SPEC_ROWS.from; line <= SPEC_ROWS.to; line++) {
    if (!byLine.has(line)) A.push('AUTH_SPEC_ROW_MISSING', MATRIX_PATH, ['rows'], `spec line ${line} has no row; the matrix keeps all 31 spec rows`);
  }
  for (const [line, rows] of byLine) {
    if (rows.length < 2) continue;
    const first = canonical(rows[0].spec);
    for (const r of rows) {
      if (!r.split) A.push('AUTH_SPEC_ROW_CHANGED', MATRIX_PATH, A.where(r.id), `${r.id} shares spec line ${line} with ${rows.filter((x) => x !== r).map((x) => x.id).join(', ')} but does not say how the row splits (split)`);
      if (canonical(r.spec) !== first) A.push('AUTH_SPEC_ROW_CHANGED', MATRIX_PATH, A.where(r.id, 'spec'), `${r.id} splits spec line ${line} but its spec columns differ from ${rows[0].id}'s; every part keeps the spec text`);
    }
  }
  // Verbatim without a rounds-review checkout: the spec columns hash to the pin.
  const pin = A.matrix?.spec?.authorityRowsSha256;
  if (typeof pin === 'string' && byLine.size && specRowsDigest((line) => byLine.get(line)?.[0]?.spec) !== pin) {
    A.push('AUTH_SPEC_ROW_CHANGED', MATRIX_PATH, ['spec', 'authorityRowsSha256'], `the rows' spec columns no longer hash to the pinned spec ${SPEC_ROWS.from}-${SPEC_ROWS.to}; keep the spec text verbatim (check with --review)`);
  }
  if (!ctx.reviewRoot) return;
  const spec = readReview(ctx, A, REVIEW_SPEC);
  if (!spec) return;
  const lines = spec.split('\n');
  if (typeof pin === 'string' && specRowsDigest((line) => specCells(lines[line - 1])) !== pin) {
    A.push('AUTH_SPEC_ROW_CHANGED', MATRIX_PATH, ['spec', 'authorityRowsSha256'], `spec ${SPEC_ROWS.from}-${SPEC_ROWS.to} in ${REVIEW_SPEC} no longer matches the pin; recheck every spec row and re-pin`);
  }
  for (const [line, rows] of byLine) {
    const cells = specCells(lines[line - 1]);
    for (const r of rows) {
      if (!cells) { A.push('AUTH_SPEC_ROW_CHANGED', MATRIX_PATH, A.where(r.id, 'spec'), `spec line ${line} is not an Authority Matrix row in ${REVIEW_SPEC}`); continue; }
      for (const [k, v] of Object.entries(cells)) {
        if (r.spec[k] !== v) A.push('AUTH_SPEC_ROW_CHANGED', MATRIX_PATH, A.where(r.id, 'spec', k), `${r.id} spec ${k} "${r.spec[k]}" is not spec line ${line}'s "${v}"; keep the spec text verbatim`);
      }
    }
  }
  for (const p of A.packageList) {
    const n = Number(String(p.spec || '').replace(/^spec /, ''));
    const text = (lines[n - 1] || '').replace(/^-\s*/, '').trim();
    if (text !== p.service) A.push('AUTH_PACKAGE_MISMATCH', PACKAGES_PATH, ['packages', A.packageList.indexOf(p), 'service'], `${p.id} names service "${p.service}", but ${p.spec} reads "${text}"`);
  }
}

function readReview(ctx, A, rel) {
  const abs = path.join(ctx.reviewRoot, rel);
  try {
    return fs.readFileSync(abs, 'utf8').replace(/\r\n/g, '\n');
  } catch (err) {
    A.push('AUTH_REVISION_UNAVAILABLE', MATRIX_PATH, 1, `cannot read ${rel} under --review ${ctx.reviewRoot}: ${err.code || err.message}`);
    return null;
  }
}

// ---------------------------------------------------------------- cells

// Rule 7: no empty cell, and every leaf ID and capability resolves.
export function checkCells(A) {
  if (A.matrix) {
    walk(A.matrix, [], (v, at) => {
      if (empty(v)) A.push('AUTH_EMPTY_CELL', MATRIX_PATH, at, EMPTY_MESSAGE(at));
    });
  }
  const skipDr = new Set(['leaf', 'consumers', 'prerequisites', 'citedBy']); // decision-records resolves these
  const sources = [...DATA_FILES.map((f) => [f.path, A[f.key]]), [DR_PATH, A.dr]];
  for (const [file, data] of sources) {
    if (!data) continue;
    walk(data, [], (v, at) => {
      if (typeof v !== 'string') return;
      if (file === DR_PATH && at.some((p) => skipDr.has(p))) return;
      for (const m of v.matchAll(LEAF_REFS)) {
        const r = A.resolveLeaf(m[0]);
        if (!r.ok) A.push('AUTH_UNRESOLVED_REF', file, at, `${where(at)}: ${r.reason}`);
      }
      if (CAPABILITY.test(v) && !A.capabilities.has(v)) A.push('AUTH_UNRESOLVED_REF', file, at, `${where(at)}: capability ${v} has no leaf in contracts/vocabulary/leaf-ids.json`);
    });
  }
}

// ----------------------------------------------------------------- rows

function consumers(r) {
  return list(r.consumers).filter(isObject);
}

const declaresNone = (c) => typeof c.name === 'string' && NA.test(c.name);

export function checkRows(A) {
  const rm = new Set(A.readModels.map((x) => x.row));
  for (const r of A.rows) {
    const at = (...rest) => A.where(r.id, ...rest);
    // Rules 1 and 6: exactly one target authority, never browser storage.
    if (Array.isArray(r.target_authority)) {
      A.push('AUTH_TWO_AUTHORITIES', MATRIX_PATH, at('target_authority'), `${r.id} lists ${r.target_authority.length} target authorities; a row has exactly one writable authority at any revision`);
    } else if (isObject(r.target_authority) && r.target_authority.location === 'browser-storage') {
      A.push('AUTH_BROWSER_AUTHORITY', MATRIX_PATH, at('target_authority', 'location'), `${r.id} names browser storage as its target authority; browser storage holds only account-namespaced preferences, drafts, and caches that yield to the server (spec 2005-2007)`);
    }
    // Scope decides privacy floor or visibility.
    if (r.scope === 'account') {
      if (r.privacy_floor === undefined || r.visibility !== undefined) A.push('AUTH_PRIVACY_MISSING', MATRIX_PATH, at(), `${r.id} is account-scoped, so it names a privacy_floor and no visibility`);
    } else if (r.scope === 'platform-global' || r.scope === 'pack-owned') {
      if (r.visibility === undefined || r.privacy_floor !== undefined) A.push('AUTH_PRIVACY_MISSING', MATRIX_PATH, at(), `${r.id} is ${r.scope}, so it names a visibility and no privacy_floor`);
    }
    // Rule 10: Test Definitions and Harness Revisions are server-only.
    if ((CONTAINED.includes(r.id) || CONTAINED.includes(r.term)) && r.visibility !== 'server-only') {
      A.push('AUTH_CONTAINMENT_VISIBILITY', MATRIX_PATH, at('visibility'), `${r.id} holds Test Definition or Harness Revision data, so its visibility is server-only (got ${r.visibility ?? 'none'})`);
    }
    const cs = consumers(r);
    const real = cs.filter((c) => !declaresNone(c));
    // Rule 4: Secret rows reach only verifiers and gateways.
    if (r.privacy_floor === 'Secret') {
      for (const c of real) if (!SECRET_CONSUMERS.has(c.type)) A.push('AUTH_SECRET_CONSUMER', MATRIX_PATH, at('consumers', list(r.consumers).indexOf(c)), `${r.id} is Secret, but "${c.name}" consumes it as ${c.type}; only verifier and gateway consumers may`);
    }
    if (r.visibility === 'server-only') {
      for (const c of real) if (!SECRET_CONSUMERS.has(c.type)) A.push('AUTH_CONTAINMENT_VISIBILITY', MATRIX_PATH, at('consumers', list(r.consumers).indexOf(c)), `${r.id} is server-only, but "${c.name}" reads it as ${c.type}; only verifier and gateway consumers may`);
    }
    for (const c of cs) {
      const i = list(r.consumers).indexOf(c);
      if (declaresNone(c) && c.type !== 'public-share') A.push('AUTH_SHAPE_INVALID', MATRIX_PATH, at('consumers', i), `${r.id} consumer ${c.type} says ${c.name}; only the public-share entry may declare n/a`);
      if (!declaresNone(c) && !c.leaf && c.type !== 'log-trace') A.push('AUTH_SHAPE_INVALID', MATRIX_PATH, at('consumers', i), `${r.id} consumer "${c.name}" (${c.type}) names no leaf`);
    }
    const shares = cs.filter((c) => c.type === 'public-share');
    if (!shares.length) A.push('AUTH_PUBLIC_SHARE_UNDECLARED', MATRIX_PATH, at('consumers'), `${r.id} lists no public-share entry; name the public consumer or write n/a:<reason>`);
    else if (shares.length > 1 && shares.some(declaresNone)) A.push('AUTH_PUBLIC_SHARE_UNDECLARED', MATRIX_PATH, at('consumers'), `${r.id} both declares no public-share consumer and lists one`);
    // Rule 5: a ledger disposition, or a new platform concept under INT-02 or INT-03.
    if (r.disposition !== undefined && !empty(r.disposition)) {
      const d = r.disposition;
      if (!(NEW_CONCEPT.test(d) || A.ledgerIds.has(d))) A.push('AUTH_NO_DISPOSITION', MATRIX_PATH, at('disposition'), `${r.id} disposition "${d}" is neither a ${LEDGER_PATH} row nor new-platform-concept:INT-02 or INT-03`);
    }
    // Rule 8: package, service, and term resolve.
    if (typeof r.package === 'string' && !isNote(r.package) && !A.packageIds.has(r.package)) A.push('AUTH_UNRESOLVED_REF', MATRIX_PATH, at('package'), `${r.id} package "${r.package}" is not in ${PACKAGES_PATH}`);
    if (isObject(r.command_owner)) {
      const s = r.command_owner.service;
      if (typeof s === 'string' && !isBlocked(s) && !A.packageIds.has(s)) A.push('AUTH_UNRESOLVED_REF', MATRIX_PATH, at('command_owner', 'service'), `${r.id} command owner service "${s}" is not a package in ${PACKAGES_PATH}`);
      if (typeof s === 'string' && typeof r.package === 'string' && s !== r.package) A.push('AUTH_PACKAGE_MISMATCH', MATRIX_PATH, at('package'), `${r.id} package "${r.package}" is not its command owner's service "${s}"`);
    }
    if (typeof r.term === 'string' && !isNote(r.term) && !A.termIds.has(r.term)) A.push('AUTH_UNRESOLVED_REF', MATRIX_PATH, at('term'), `${r.id} term "${r.term}" is not a term id in ${TERMS_PATH}`);
    // Commands need an owner.
    if (Array.isArray(r.commands) && r.commands.length && !isObject(r.command_owner)) A.push('AUTH_COMMAND_UNOWNED', MATRIX_PATH, at('commands'), `${r.id} lists commands but its command owner is ${r.command_owner}`);
    // Migration: a row with baseline writers has a full transfer block.
    if (list(r.baseline_writers).length && !isObject(r.transfer)) A.push('AUTH_TRANSFER_MISSING', MATRIX_PATH, at('baseline_writers'), `${r.id} has baseline writers but no transfer (leaf, window, retirement, rollback)`);
    if (r.projection !== undefined && !rm.has(r.id)) A.push('AUTH_PROJECTION_INCOMPLETE', MATRIX_PATH, at('projection'), `${r.id} has a projection but is not one of the matrix's read models`);
  }
}

// ------------------------------------------------- writers and conflicts

// Rule 2: a store with writers in more than one module, or a derived
// consumer writing its source, needs a conflict naming the row.
export function checkWriters(A) {
  for (const r of A.rows) {
    const byStore = new Map();
    for (const w of list(r.baseline_writers).filter(isObject)) {
      if (!byStore.has(w.store)) byStore.set(w.store, []);
      byStore.get(w.store).push(w);
    }
    const flagged = list(r.conflicts).some((id) => list(A.conflict.get(id)?.rows).includes(r.id));
    for (const [store, writers] of byStore) {
      const modules = [...new Set(writers.map((w) => w.path))];
      const derived = writers.filter((w) => w.role === 'derived-consumer');
      if ((modules.length > 1 || derived.length) && !flagged) {
        const why = derived.length ? `a derived consumer (${derived[0].path}:${derived[0].lines}) writes it` : `${modules.length} modules write it (${modules.join(', ')})`;
        A.push('AUTH_UNFLAGGED_WRITERS', MATRIX_PATH, A.where(r.id, 'baseline_writers'), `${r.id}: ${why} for store ${store}, and no conflict names the row; add a conflict with its disposition and resolving leaf`);
      }
    }
  }
}

export function checkConflicts(A) {
  const at = (c, ...rest) => ['conflicts', list(A.matrix?.conflicts).indexOf(c), ...rest];
  for (const r of A.rows) {
    list(r.conflicts).forEach((id, i) => {
      const c = A.conflict.get(id);
      if (!c) A.push('AUTH_UNRESOLVED_REF', MATRIX_PATH, A.where(r.id, 'conflicts', i), `${r.id} names conflict ${id}, which the matrix does not list`);
      else if (!list(c.rows).includes(r.id)) A.push('AUTH_CONFLICT_UNFLAGGED', MATRIX_PATH, A.where(r.id, 'conflicts', i), `${r.id} names ${id}, but ${id} does not list ${r.id} in its rows`);
    });
  }
  for (const c of A.conflicts) {
    list(c.rows).forEach((id, i) => {
      const r = A.row(id);
      if (!r) A.push('AUTH_UNRESOLVED_REF', MATRIX_PATH, at(c, 'rows', i), `${c.id} names row ${id}, which does not exist`);
      else if (!list(r.conflicts).includes(c.id)) A.push('AUTH_CONFLICT_UNFLAGGED', MATRIX_PATH, at(c, 'rows', i), `${c.id} lists ${id}, but ${id} does not name ${c.id} in its conflicts`);
    });
    if (typeof c.disposition === 'string' && !A.ledgerIds.has(c.disposition)) A.push('AUTH_UNRESOLVED_REF', MATRIX_PATH, at(c, 'disposition'), `${c.id} disposition ${c.disposition} is not a ${LEDGER_PATH} row`);
    if (!BASELINE_CONFLICTS.ids.includes(c.id) && c.foundHere !== true) A.push('AUTH_SHAPE_INVALID', MATRIX_PATH, at(c), `${c.id} is beyond #16's C1 to C13, so it is marked foundHere`);
  }
  if (A.matrix?.auditedRevision === BASELINE_CONFLICTS.revision) {
    for (const id of BASELINE_CONFLICTS.ids) {
      if (!A.conflict.has(id)) A.push('AUTH_CONFLICT_MISSING', MATRIX_PATH, ['conflicts'], `${id} (#16's baseline conflict at ${BASELINE_CONFLICTS.revision}) is not flagged with its rows, disposition, and resolving leaves`);
    }
  }
}

// Rule 3: every relation has an owning row.
export function checkRelations(A) {
  A.relations.forEach((rel) => {
    const i = list(A.matrix?.relations).indexOf(rel);
    for (const k of ['from', 'to']) if (typeof rel[k] === 'string' && !A.row(rel[k])) A.push('AUTH_UNRESOLVED_REF', MATRIX_PATH, ['relations', i, k], `relation ${rel.id} ${k} ${rel[k]} is not a row`);
    if (!A.row(rel.owner_row)) A.push('AUTH_RELATION_UNOWNED', MATRIX_PATH, ['relations', i, 'owner_row'], `relation ${rel.id} (${rel.from} to ${rel.to}) has no owning row${rel.owner_row ? `: ${rel.owner_row} is not a row` : ''}`);
  });
}

// ------------------------------------------------------- projections

export function checkReadModels(A) {
  const names = A.readModels.map((x) => x.name);
  for (const n of SPEC_READ_MODELS) if (!names.includes(n)) A.push('AUTH_READ_MODEL_MISSING', MATRIX_PATH, ['readModels'], `spec read model "${n}" (spec 1970-1980) has no row`);
  const projectorOf = new Map();
  A.readModels.forEach((x, i) => {
    if (!SPEC_READ_MODELS.includes(x.name)) A.push('AUTH_READ_MODEL_MISSING', MATRIX_PATH, ['readModels', i], `"${x.name}" is not one of the spec's nine read models`);
    const r = A.row(x.row);
    if (!r) { A.push('AUTH_UNRESOLVED_REF', MATRIX_PATH, ['readModels', i, 'row'], `read model ${x.name} names row ${x.row}, which does not exist`); return; }
    const p = r.projection;
    if (!isObject(p)) { A.push('AUTH_PROJECTION_INCOMPLETE', MATRIX_PATH, A.where(r.id), `${r.id} (read model ${x.name}) has no projection with sources, watermark, stale and degraded behavior, and one projector`); return; }
    if (r.projector !== p.projector) A.push('AUTH_PROJECTION_INCOMPLETE', MATRIX_PATH, A.where(r.id, 'projector'), `${r.id} projector column ${r.projector} is not its projection's projector ${p.projector}`);
    const other = [...projectorOf.entries()].find(([, leaf]) => leaf === p.projector);
    if (other) A.push('AUTH_PROJECTION_INCOMPLETE', MATRIX_PATH, A.where(r.id, 'projection', 'projector'), `read models ${other[0]} and ${x.name} share projector ${p.projector}; each read model has one projector of its own`);
    projectorOf.set(x.name, p.projector);
    const type = x.row === 'search-index' ? 'search-index' : 'read-model';
    list(p.sources).forEach((id, k) => {
      const s = A.row(id);
      if (!s) { A.push('AUTH_UNRESOLVED_REF', MATRIX_PATH, A.where(r.id, 'projection', 'sources', k), `${x.name} source ${id} is not a row`); return; }
      if (!consumers(s).some((c) => c.type === type && c.leaf === p.projector)) A.push('AUTH_PROJECTION_INCOMPLETE', MATRIX_PATH, A.where(id, 'consumers'), `${id} is a source of ${x.name} but lists no ${type} consumer for its projector ${p.projector}`);
    });
  });
  const rmByProjector = new Map(A.readModels.map((x) => [A.row(x.row)?.projection?.projector, x]).filter(([leaf]) => leaf));
  const searchRow = A.row('search-index');
  for (const r of A.rows) {
    const cs = consumers(r);
    for (const c of cs) {
      const x = rmByProjector.get(c.leaf);
      if (!x || !PROJECTION_CONSUMERS.has(c.type) || x.row === r.id) continue;
      if (!list(A.row(x.row)?.projection?.sources).includes(r.id)) A.push('AUTH_PROJECTION_INCOMPLETE', MATRIX_PATH, A.where(r.id, 'consumers', list(r.consumers).indexOf(c)), `${r.id} lists ${x.name}'s projector ${c.leaf} as a consumer, but ${x.row} does not list ${r.id} as a source`);
    }
    if (A.readModels.some((x) => x.row === r.id)) continue;
    const projected = cs.some((c) => PROJECTION_CONSUMERS.has(c.type));
    if (projected === NA.test(String(r.projector))) {
      A.push('AUTH_PROJECTION_INCOMPLETE', MATRIX_PATH, A.where(r.id, 'projector'), projected ? `${r.id} is read through a projection, so its projector column names the leaf that registers it (pending:ROUNDS-31-L01), not ${r.projector}` : `${r.id} has no projection consumer, so its projector column is n/a, not ${r.projector}`);
    }
    if (searchRow && r.id !== searchRow.id) {
      const indexed = list(searchRow.projection?.sources).includes(r.id);
      if (indexed === NA.test(String(r.search))) A.push('AUTH_PROJECTION_INCOMPLETE', MATRIX_PATH, A.where(r.id, 'search'), indexed ? `${r.id} is a search index source, so its search column names #153 (pending:ROUNDS-31-L08), not ${r.search}` : `${r.id} is not a search index source, so its search column is n/a, not ${r.search}`);
    }
  }
}

// ------------------------------------------------------- packages, labels

export function checkPackages(A) {
  const count = SPEC_SERVICES.to - SPEC_SERVICES.from + 1;
  if (A.packages && A.packageList.length !== count) A.push('AUTH_PACKAGE_MISMATCH', PACKAGES_PATH, ['packages'], `${PACKAGES_PATH} lists ${A.packageList.length} packages; the spec names ${count} services (spec ${SPEC_SERVICES.from}-${SPEC_SERVICES.to}), one package each`);
  A.packageList.forEach((p, i) => {
    const n = Number(String(p.spec || '').replace(/^spec /, ''));
    if (!(n >= SPEC_SERVICES.from && n <= SPEC_SERVICES.to)) A.push('AUTH_PACKAGE_MISMATCH', PACKAGES_PATH, ['packages', i, 'spec'], `${p.id} cites ${p.spec}, outside the service list (spec ${SPEC_SERVICES.from}-${SPEC_SERVICES.to})`);
  });
  for (const f of [PACKAGES_PATH, BASELINE_STORES_PATH]) {
    const data = f === PACKAGES_PATH ? A.packages : A.stores;
    if (data && A.matrix && data.auditedRevision !== A.matrix.auditedRevision) A.push('AUTH_REVISION_MISMATCH', f, ['auditedRevision'], `${f} audits ${data.auditedRevision}, but the matrix audits ${A.matrix.auditedRevision}`);
  }
}

export function checkOwnerLabels(ctx, A) {
  const services = (s) => s === 'none' || s === 'per-row' || isBlocked(s) || A.packageIds.has(s);
  A.labelList.forEach((l, i) => {
    if (typeof l.service === 'string' && !services(l.service)) A.push('AUTH_UNRESOLVED_REF', OWNER_LABELS_PATH, ['labels', i, 'service'], `${l.label} maps to "${l.service}", which is not a package, none, per-row, or blocked:OD-<n>`);
    if (l.service === 'per-row' && !isObject(l.rows)) A.push('AUTH_OWNER_LABEL_MISMATCH', OWNER_LABELS_PATH, ['labels', i], `${l.label} is per-row but lists no rows`);
    for (const [id, s] of Object.entries(isObject(l.rows) ? l.rows : {})) {
      const r = A.row(id);
      if (!r) { A.push('AUTH_UNRESOLVED_REF', OWNER_LABELS_PATH, ['labels', i, 'rows', id], `${l.label} maps row ${id}, which does not exist`); continue; }
      if (!A.packageIds.has(s)) A.push('AUTH_UNRESOLVED_REF', OWNER_LABELS_PATH, ['labels', i, 'rows', id], `${l.label} maps ${id} to "${s}", which is not a package`);
      if (capabilityOf(r.command_owner?.leaf) !== l.capability) A.push('AUTH_OWNER_LABEL_MISMATCH', OWNER_LABELS_PATH, ['labels', i, 'rows', id], `${l.label} maps ${id}, but ${id}'s command owner ${r.command_owner?.leaf ?? r.command_owner} is not a ${l.capability} leaf`);
    }
  });
  for (const cap of [...A.capabilities].sort()) {
    if (A.labels && !A.labelByCapability.has(cap)) A.push('AUTH_OWNER_LABEL_MISMATCH', OWNER_LABELS_PATH, ['labels'], `capability ${cap} has leaves but no owner label`);
  }
  // A row whose command owner is a capability's leaf takes that label's service.
  for (const r of A.rows) {
    if (!isObject(r.command_owner) || typeof r.command_owner.leaf !== 'string') continue;
    const cap = capabilityOf(r.command_owner.leaf);
    const l = A.labelByCapability.get(cap);
    if (!l) continue;
    const expected = isObject(l.rows) && l.rows[r.id] !== undefined ? l.rows[r.id] : l.service;
    if (expected === 'none' || expected === 'per-row') {
      A.push('AUTH_OWNER_LABEL_MISMATCH', MATRIX_PATH, A.where(r.id, 'command_owner'), expected === 'none' ? `${r.id}'s command owner ${r.command_owner.leaf} is a ${l.label} leaf, and ${l.label} owns no commands` : `${l.label} is per-row but does not map ${r.id}`);
    } else if (expected !== r.command_owner.service) {
      A.push('AUTH_OWNER_LABEL_MISMATCH', MATRIX_PATH, A.where(r.id, 'command_owner', 'service'), `${r.id}'s command owner ${r.command_owner.leaf} is a ${l.label} leaf, which maps to ${expected}, not ${r.command_owner.service}`);
    }
  }
  if (!ctx.catalogPath || !A.labels) return;
  let catalog;
  try {
    catalog = JSON.parse(fs.readFileSync(ctx.catalogPath, 'utf8'));
  } catch (err) {
    A.push('AUTH_LABELS_PIN', OWNER_LABELS_PATH, 1, `cannot read the catalog ${ctx.catalogPath}: ${err.message}`);
    return;
  }
  const caps = list(catalog?.capabilities);
  for (const c of caps) {
    const l = A.labelByCapability.get(c.id);
    if (!l) A.push('AUTH_LABELS_PIN', OWNER_LABELS_PATH, ['labels'], `catalog capability ${c.id} (owner "${c.owner}") has no label entry`);
    else if (l.label !== c.owner) A.push('AUTH_LABELS_PIN', OWNER_LABELS_PATH, ['labels', A.labelList.indexOf(l), 'label'], `${c.id} label "${l.label}" is not the catalog owner "${c.owner}"`);
  }
  for (const l of A.labelList) if (!caps.some((c) => c.id === l.capability)) A.push('AUTH_LABELS_PIN', OWNER_LABELS_PATH, ['labels', A.labelList.indexOf(l)], `${l.capability} is not a catalog capability`);
}

// The ledger's pin, and with --review its source in rounds-review.
export function checkLedger(ctx, A) {
  const L = A.ledger;
  if (!L) return;
  if (L.pin?.rows !== list(L.rows).length) A.push('AUTH_LEDGER_PIN', LEDGER_PATH, ['pin', 'rows'], `the pin counts ${L.pin?.rows} rows, but the ledger lists ${list(L.rows).length}`);
  if (!ctx.reviewRoot) return;
  const text = readReview(ctx, A, REVIEW_LEDGER);
  if (text === null) return;
  const actual = sha256(text);
  if (actual !== L.pin?.sha256) A.push('AUTH_LEDGER_PIN', LEDGER_PATH, ['pin', 'sha256'], `${REVIEW_LEDGER} has sha256 ${actual.slice(0, 12)}..., not the pinned ${String(L.pin?.sha256).slice(0, 12)}...; re-pin it and recheck every row`);
  const seeds = [];
  for (const line of text.split('\n')) {
    const m = /^\s*(\["(?:INT|CUR)-\d{2}".*\]),?\s*$/.exec(line);
    if (!m) continue;
    try { seeds.push(JSON.parse(m[1])); } catch { /* not a plain seed line */ }
  }
  const byId = new Map(list(L.rows).map((r) => [r.id, r]));
  for (const [id, intent, cls, , , proposals, proof] of seeds) {
    const r = byId.get(id);
    if (!r) { A.push('AUTH_LEDGER_PIN', LEDGER_PATH, ['rows'], `${REVIEW_LEDGER} has ${id}, which the ledger lacks`); continue; }
    const same = r.intent === intent && r.class === cls && canonical(r.proposals) === canonical(proposals) && r.proof === proof;
    if (!same) A.push('AUTH_LEDGER_PIN', LEDGER_PATH, ['rows', list(L.rows).indexOf(r)], `${id} differs from ${REVIEW_LEDGER} (intent, class, proposals, or proof)`);
  }
  if (seeds.length !== list(L.rows).length) A.push('AUTH_LEDGER_PIN', LEDGER_PATH, ['rows'], `${REVIEW_LEDGER} has ${seeds.length} rows; the ledger lists ${list(L.rows).length}`);
}

// ----------------------------------------------------------- commands

// Rule 12: a command type sits on one row.
// TODO(ROUNDS-02-L02): once #19's command registry lands, also fail a
// registered type that no row lists, and a row command it does not register.
export function checkCommands(A) {
  const seen = new Map();
  for (const r of A.rows) {
    list(r.commands).forEach((type, i) => {
      if (seen.has(type)) A.push('AUTH_COMMAND_DUPLICATE', MATRIX_PATH, A.where(r.id, 'commands', i), `command type ${type} is on ${seen.get(type)} and ${r.id}; a command type belongs to one row`);
      else seen.set(type, r.id);
    });
  }
}

// ------------------------------------------------------ open decisions

export function checkOpenDecisions(A) {
  if (!A.dr) {
    A.push('AUTH_OD_MISSING', DR_PATH, 1, `${DR_PATH} is missing or unreadable; it records OD-1 to OD-5`);
    return;
  }
  const at = (id) => ['decisions', list(A.dr.decisions).findIndex((d) => d?.id === id)];
  for (const id of OPEN_DECISIONS) {
    const d = A.decisions.get(id);
    if (!d) { A.push('AUTH_OD_MISSING', DR_PATH, ['decisions'], `DR-0002 has no ${id} decision`); continue; }
    const od = d.od;
    if (!isObject(od) || !OD_STATUS[od.state]) { A.push('AUTH_OD_MISSING', DR_PATH, at(id), `${id} has no od.state (blocked, settled, or default-taken)`); continue; }
    if (d.status !== OD_STATUS[od.state]) A.push('AUTH_OD_MISSING', DR_PATH, at(id), `${id} is ${od.state}, so its status is ${OD_STATUS[od.state]}, not ${d.status}`);
    if (od.state === 'settled' && !od.basis) A.push('AUTH_OD_MISSING', DR_PATH, at(id), `${id} is settled but cites no basis`);
    if (od.state === 'default-taken' && !od.default) A.push('AUTH_OD_MISSING', DR_PATH, at(id), `${id} took a default but does not say which`);
  }
  const blockedCells = [];
  const sources = [[MATRIX_PATH, A.matrix], [OWNER_LABELS_PATH, A.labels]];
  for (const [file, data] of sources) {
    if (!data) continue;
    walk(data, [], (v, parts) => { if (isBlocked(v)) blockedCells.push([file, parts, BLOCKED.exec(v)[1]]); });
  }
  A.conflicts.forEach((c, i) => { if (typeof c.blockedBy === 'string') blockedCells.push([MATRIX_PATH, ['conflicts', i, 'blockedBy'], c.blockedBy]); });
  for (const [file, parts, id] of blockedCells) {
    const d = A.decisions.get(id);
    if (!d) A.push('AUTH_OD_MISSING', file, parts, `${where(parts)} is blocked on ${id}, which DR-0002 does not record`);
    else if (d.od?.state !== 'blocked') A.push('AUTH_OD_SETTLED_BLOCKED', file, parts, `${where(parts)} is blocked on ${id}, but ${id} is ${d.od?.state ?? d.status}; fill the cell`);
  }
}

// Rows blocked on an open decision: { row, ods }.
export function blockedRows(A) {
  const out = [];
  for (const r of A.rows) {
    const ods = new Set();
    walk(r, [], (v) => { if (isBlocked(v)) ods.add(BLOCKED.exec(v)[1]); });
    if (ods.size) out.push({ row: r.id, ods: [...ods].sort() });
  }
  return out;
}

// pending:<leaf> cells by leaf: Map leaf -> { cells, rows: Set }.
export function pendingByLeaf(A) {
  const out = new Map();
  for (const r of A.rows) {
    walk(r, [], (v) => {
      const m = typeof v === 'string' ? PENDING.exec(v) : null;
      if (!m) return;
      if (!out.has(m[1])) out.set(m[1], { cells: 0, rows: new Set() });
      out.get(m[1]).cells++;
      out.get(m[1]).rows.add(r.id);
    });
  }
  return out;
}

// ------------------------------------------------- owner-sentence corrections

// The corrections cite the revision #17 re-authorizes against; a later
// additive revision keeps those citations valid, so it may trail the matrix.
export function checkCorrections(A) {
  const C = A.corrections;
  if (!C) return;
  if (A.matrix && !(C.matrixRevision >= 1 && C.matrixRevision <= A.matrix.revision)) A.push('AUTH_REVISION_MISMATCH', CORRECTIONS_PATH, ['matrixRevision'], `corrections cite matrix revision ${C.matrixRevision}, which the matrix (at ${A.matrix.revision}) has not reached`);
  list(C.entries).forEach((e, i) => {
    if (!isObject(e)) return;
    const at = (...rest) => ['entries', i, ...rest];
    const bad = (k, message) => A.push('AUTH_CORRECTION_INVALID', CORRECTIONS_PATH, at(k), `#${e.issue}: ${message}`);
    if (A.leafIssue.has(e.leaf) && A.leafIssue.get(e.leaf) !== e.issue) bad('leaf', `${e.leaf} is #${A.leafIssue.get(e.leaf)}, not #${e.issue}`);
    const label = A.labelByCapability.get(capabilityOf(e.leaf));
    if (label && e.label !== label.label) bad('label', `${e.leaf} is a ${label.label} leaf, not ${e.label}`);
    if (typeof e.original === 'string' && !e.original.startsWith(`- ${e.label} is the only command or contract owner for "`)) bad('original', 'the original sentence does not name its label');
    for (const id of list(e.rows)) if (!A.row(id)) A.push('AUTH_UNRESOLVED_REF', CORRECTIONS_PATH, at('rows'), `#${e.issue} names row ${id}, which does not exist`);
    const owned = (A.ownedBy.get(e.leaf) || []).slice().sort();
    const rows = list(e.rows).slice().sort();
    if (e.kind === 'owner' && (!rows.length || canonical(rows) !== canonical(owned))) bad('rows', `${e.leaf} is the command owner of ${owned.join(', ') || 'no row'}, but the correction lists ${rows.join(', ') || 'none'}`);
    if (e.kind === 'adds') {
      if (!rows.length) bad('rows', 'an adds correction names the rows it adds to');
      for (const id of rows) {
        const owner = A.row(id)?.command_owner?.leaf;
        if (owner === e.leaf) bad('rows', `${e.leaf} owns ${id}, so the correction is kind owner`);
        else if (owner && !String(e.corrected).includes(`(${owner})`)) bad('corrected', `the corrected sentence does not name ${id}'s command owner ${owner}`);
      }
    }
    if (e.kind === 'none') {
      if (rows.length) bad('rows', 'a none correction lists no rows');
      if (owned.length) bad('kind', `${e.leaf} is the command owner of ${owned.join(', ')}`);
    }
    if (typeof e.corrected === 'string') {
      if (!e.corrected.includes(`DR-0002@${C.matrixRevision}`)) bad('corrected', `the corrected sentence does not cite DR-0002@${C.matrixRevision}`);
      for (const id of rows) if (!e.corrected.includes(`\`${id}\``)) bad('corrected', `the corrected sentence does not name \`${id}\``);
    }
  });
}

// --------------------------------------------- stores, citations, secrets

const memo = new WeakMap();
function treeFacts(tree, adapters) {
  if (!memo.has(tree)) memo.set(tree, {});
  const facts = memo.get(tree);
  if (!facts.stores) facts.stores = extractBaselineStores(tree, adapters);
  return facts;
}

export function auditedTree(ctx, A) {
  const rev = A.matrix?.auditedRevision;
  if (typeof rev !== 'string') return null;
  const tree = ctx.tree(rev);
  if (!tree.ok) {
    A.push('AUTH_REVISION_UNAVAILABLE', MATRIX_PATH, ['auditedRevision'], `cannot read the audited revision: ${tree.reason}`);
    return null;
  }
  return tree;
}

const sitePath = (site) => String(site).slice(0, String(site).lastIndexOf(':'));
const siteLine = (site) => Number(String(site).slice(String(site).lastIndexOf(':') + 1));

// Rule 9 and coverage: every store at the audited revision has an entry,
// every entry has a row, and every writer's store is declared.
export function checkStores(A, tree) {
  const byName = new Map(A.storeList.map((s) => [s.name, s]));
  A.storeList.forEach((s, i) => {
    if (!list(s.rows).length) A.push('AUTH_STORE_NO_ROW', BASELINE_STORES_PATH, ['stores', i, 'rows'], `${s.id} has no row; name the DR-0002 rows it holds`);
    for (const id of list(s.rows)) if (!A.row(id)) A.push('AUTH_UNRESOLVED_REF', BASELINE_STORES_PATH, ['stores', i, 'rows'], `${s.id} names row ${id}, which does not exist`);
  });
  for (const r of A.rows) {
    list(r.baseline_writers).forEach((w, k) => {
      if (!isObject(w) || typeof w.store !== 'string' || w.store.startsWith('bundled:')) return;
      const at = A.where(r.id, 'baseline_writers', k, 'store');
      const entries = w.store.includes('*') && !byName.has(w.store)
        ? A.storeList.filter((s) => s.kind === 'collection' && new RegExp(`^${w.store.split('*').map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('.*')}$`).test(s.name))
        : [byName.get(w.store)].filter(Boolean);
      if (!entries.length) { A.push('AUTH_STORE_UNDECLARED', MATRIX_PATH, at, `${r.id} writes store ${w.store}, which ${BASELINE_STORES_PATH} does not declare (or name bundled:<registry> for a registry in code)`); return; }
      for (const s of entries) if (!list(s.rows).includes(r.id)) A.push('AUTH_STORE_NO_ROW', BASELINE_STORES_PATH, ['stores', A.storeList.indexOf(s), 'rows'], `${s.id} does not list ${r.id}, which writes it (${w.path}:${w.lines})`);
    });
  }
  if (!tree || !A.stores) return null;
  const extracted = treeFacts(tree, A.adapters).stores;
  const declared = new Set(A.storeList.map((s) => s.id));
  const found = new Set(extracted.stores.map((s) => s.id));
  for (const s of extracted.stores) {
    if (!declared.has(s.id)) A.push('AUTH_STORE_UNDECLARED', BASELINE_STORES_PATH, ['stores'], `${s.id} (${s.created || s.writes?.[0] || s.reads?.[0]} at ${tree.ref}) has no entry; run --write and name its rows`);
  }
  A.storeList.forEach((s, i) => { if (!found.has(s.id)) A.push('AUTH_STORE_STALE', BASELINE_STORES_PATH, ['stores', i], `${s.id} is not a store at ${tree.ref}`); });
  for (const site of extracted.unresolved) A.push('AUTH_STORE_UNDECLARED', BASELINE_STORES_PATH, ['stores'], `cannot resolve the store at ${site} (${tree.ref}); its key or collection name must be statically known`);
  return extracted;
}

// A credential assignment: a variable or key whose name ends in a secret word,
// set to a literal that looks like a value (no spaces or code punctuation, and
// not an environment variable name or a store name).
const CREDENTIAL_NAME = /(password|passwd|secret|token|api[_-]?key|private[_-]?key|credential|email)$/i;
const ASSIGNMENT = /([A-Za-z_][\w.-]*)["'`]?\s*(?:=|:)\s*(["'`])([^"'`\n\\]{8,})\2/g;
const ENV_ASSIGNMENT = /^[ \t]*(?:export[ \t]+)?([A-Za-z_][A-Za-z0-9_]*)[ \t]*=[ \t]*([^\s#"'`]{8,})[ \t]*$/gm;

export function credentialAssignments(text, isName = () => false) {
  const out = [];
  const add = (name, value, index) => {
    if (!CREDENTIAL_NAME.test(name)) return;
    if (/[\s,()[\]{}<>;]/.test(value) || /^[A-Z][A-Z0-9_]*$/.test(value) || value.includes('${') || /^(process\.env|import\.meta|os\.environ)/.test(value) || isName(value)) return;
    out.push({ name, value, index });
  };
  for (const m of String(text).matchAll(ASSIGNMENT)) add(m[1], m[3], m.index);
  for (const m of String(text).matchAll(ENV_ASSIGNMENT)) add(m[1], m[2], m.index);
  return out;
}

// Setting a stored password is a credential line even when the value is a
// constant defined elsewhere.
const CITES_CREDENTIAL = /\.setPassword\(/;
const SECRET_SOURCE = /^(pocketbase|backend|frontend\/src|scripts|deploy|docker)\/|^(docker-compose[^/]*\.ya?ml|\.env[^/]*|Dockerfile[^/]*)$/;

function credentialValues(tree, isName) {
  const facts = memo.get(tree) || {};
  memo.set(tree, facts);
  if (!facts.credentials) {
    const files = tree.files().filter((f) => SECRET_SOURCE.test(f) && /\.(js|mjs|cjs|ts|tsx|py|ya?ml|json|sh|toml|example)$|(^|\/)(\.env[^/]*|Dockerfile[^/]*)$/.test(f) && !f.includes('node_modules/') && !/package-lock\.json$/.test(f));
    tree.prefetch(files);
    const values = new Map();
    for (const f of files) {
      const text = tree.read(f);
      if (text === null || text.length > 2_000_000) continue;
      for (const a of credentialAssignments(text, isName)) {
        if (!values.has(a.value)) values.set(a.value, `${f}:${text.slice(0, a.index).split('\n').length}`);
      }
    }
    facts.credentials = values;
  }
  return facts.credentials;
}

function citationsOf(A) {
  const out = [];
  for (const r of A.rows) {
    list(r.baseline_writers).forEach((w, k) => { if (isObject(w)) out.push({ c: w, file: MATRIX_PATH, at: A.where(r.id, 'baseline_writers', k), what: `${r.id} writer` }); });
  }
  A.conflicts.forEach((c) => {
    const i = list(A.matrix?.conflicts).indexOf(c);
    list(c.evidence).forEach((e, k) => { if (isObject(e)) out.push({ c: e, file: MATRIX_PATH, at: ['conflicts', i, 'evidence', k], what: `${c.id} evidence` }); });
  });
  return out;
}

// Documentation: citations resolve at the audited revision and never point
// at a credential line.
export function checkCitations(A, tree) {
  if (!tree) return;
  const cites = citationsOf(A);
  const sites = [];
  A.storeList.forEach((s, i) => {
    if (s.created) sites.push([s.created, ['stores', i, 'created']]);
    for (const k of ['writes', 'reads']) list(s[k]).forEach((x, j) => sites.push([x, ['stores', i, k, j]]));
  });
  list(A.stores?.purgeSites).forEach((x, j) => sites.push([x, ['purgeSites', j]]));
  tree.prefetch([...new Set([...cites.map((x) => x.c.path), ...sites.map(([x]) => sitePath(x))].filter((p) => typeof p === 'string'))]);
  const lines = (p) => { const t = tree.read(p); return t === null ? null : t.split('\n'); };
  for (const { c, file, at, what } of cites) {
    const text = typeof c.path === 'string' ? lines(c.path) : null;
    if (!text) { A.push('AUTH_CITATION_STALE', file, at, `${what} cites ${c.path}, which does not exist at ${tree.ref}`); continue; }
    const [a, b = a] = String(c.lines).split('-').map(Number);
    if (!(a >= 1 && b >= a && b <= text.length)) { A.push('AUTH_CITATION_STALE', file, at, `${what} cites ${c.path}:${c.lines}, outside the file's ${text.length} lines at ${tree.ref}`); continue; }
    if (c.anchor && !text[a - 1].includes(c.anchor)) A.push('AUTH_CITATION_STALE', file, at, `${what} cites ${c.path}:${c.lines}, but line ${a} at ${tree.ref} does not contain its anchor`);
    for (let n = a; n <= b; n++) {
      if (CITES_CREDENTIAL.test(text[n - 1]) || credentialAssignments(text[n - 1]).length) {
        A.push('AUTH_CITES_SECRET', file, at, `${what} cites ${c.path}:${c.lines}, and line ${n} assigns a credential; cite the fields around it by name, never the credential lines`);
        break;
      }
    }
  }
  for (const [site, at] of sites) {
    const text = lines(sitePath(site));
    const n = siteLine(site);
    if (!text || !(n >= 1 && n <= text.length)) A.push('AUTH_CITATION_STALE', BASELINE_STORES_PATH, at, `${site} does not resolve at ${tree.ref}`);
  }
  A.packageList.forEach((p, i) => {
    list(p.baseline_locations).forEach((loc, k) => {
      const ok = loc.endsWith('/') ? tree.files().some((f) => f.startsWith(loc)) : tree.exists(loc);
      if (!ok) A.push('AUTH_CITATION_STALE', PACKAGES_PATH, ['packages', i, 'baseline_locations', k], `${p.id} baseline location ${loc} does not exist at ${tree.ref}`);
    });
  });
}

const SECRET_SHAPES = [
  [/eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}/, 'a JWT'],
  [/\bAKIA[0-9A-Z]{16}\b/, 'an AWS access key ID'],
  [/\bsk-[A-Za-z0-9_-]{16,}/, 'an API key'],
  [/-----BEGIN [A-Z ]*PRIVATE KEY-----/, 'a private key'],
  [/\/r\/[A-Za-z0-9_-]{8,}/, 'a share URL with its token'],
  [/\b(?=[A-Za-z0-9_-]*[A-Z])(?=[A-Za-z0-9_-]*[a-z])(?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]{32,}\b/, 'a bearer-shaped token'],
];
const EMAIL = /[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})/g;

export function secretShapesIn(text) {
  const out = [];
  for (const [re, what] of SECRET_SHAPES) if (re.test(text)) out.push(what);
  for (const m of String(text).matchAll(EMAIL)) {
    const domain = m[1].toLowerCase();
    if (domain !== 'example.com' && !domain.endsWith('.example.com')) out.push(`an email address at ${domain}`);
  }
  return out;
}

// Security: no authority file holds a secret value. Secrets appear by name
// and location only.
export function checkSecrets(ctx, A, tree) {
  const files = [...DATA_FILES.map((f) => f.path), DR_PATH, AUTHORITY_MD].filter((f) => ctx.exists(f));
  const storeNames = new Set(A.storeList.map((s) => s.name));
  const values = tree ? credentialValues(tree, (v) => storeNames.has(v)) : new Map();
  for (const f of files) {
    const text = A.texts[f] ?? ctx.read(f);
    text.split('\n').forEach((line, i) => {
      for (const what of secretShapesIn(line)) A.push('AUTH_SECRET_VALUE', f, i + 1, `holds ${what}; name a secret and its location, never its value`);
      for (const [value, origin] of values) {
        if (line.includes(value)) A.push('AUTH_SECRET_VALUE', f, i + 1, `holds the credential value that ${origin} assigns at ${tree.ref}; name the secret and its location instead`);
      }
    });
  }
}

// Documentation examples: DR-0002@<n>:<row> citations name a row and a
// revision the matrix has reached.
const EXAMPLE = /DR-0002@(\d+):([a-z][a-z0-9]*(?:-[a-z0-9]+)*)/g;
const EXAMPLE_FILES = /^(docs\/.*\.(md|json)|README\.md|contracts\/.*\.json|scripts\/conformance\/(rules|lib)\/.*\.mjs)$/;
export function checkExamples(ctx, A) {
  if (!A.matrix) return;
  for (const f of ctx.files().filter((x) => EXAMPLE_FILES.test(x))) {
    const text = f === DR_PATH || f === MATRIX_PATH ? A.texts[f] : ctx.read(f);
    if (!text || !text.includes('DR-0002@')) continue;
    text.split('\n').forEach((line, i) => {
      for (const m of line.matchAll(EXAMPLE)) {
        const n = Number(m[1]);
        if (!(n >= 1 && n <= A.matrix.revision)) A.push('AUTH_CITATION_UNRESOLVED', f, i + 1, `${m[0]} cites revision ${n}; the matrix is at revision ${A.matrix.revision}`);
        else if (!A.row(m[2])) A.push('AUTH_CITATION_UNRESOLVED', f, i + 1, `${m[0]} cites row ${m[2]}, which does not exist`);
      }
    });
  }
}

// --------------------------------------------------------- revisions

const rowContent = (r) => {
  const { revision, compatibility, ...rest } = r || {};
  return canonical(rest);
};

// Rule 11: a changed row carries the new matrix revision and declares its
// compatibility; a breaking change (owner, target authority, privacy floor or
// visibility, scope, package) is marked breaking; rows are never removed.
export function checkRevision(ctx, A) {
  const cur = A.matrix;
  if (!isObject(cur)) return { base: 'unavailable' };
  const dr = A.dr;
  if (dr && (dr.revision !== cur.revision || dr.compatibility !== cur.compatibility)) {
    A.push('AUTH_REVISION_MISMATCH', DR_PATH, ['revision'], `DR-0002@${dr.revision} (${dr.compatibility}) must match matrix revision ${cur.revision} (${cur.compatibility}); they share one counter`);
  }
  if (dr?.status === 'ratified' && dr.approvalRef) {
    const pinned = new Set(list(dr.approvalRef.governedFiles).map((g) => g?.path));
    for (const f of [MATRIX_PATH, PACKAGES_PATH, OWNER_LABELS_PATH]) if (!pinned.has(f)) A.push('AUTH_APPROVAL_INCOMPLETE', DR_PATH, ['approvalRef'], `ratified DR-0002 does not pin ${f}`);
  }
  for (const r of A.rows) {
    if (Number.isInteger(r.revision) && r.revision > cur.revision) A.push('AUTH_REVISION_MISMATCH', MATRIX_PATH, A.where(r.id, 'revision'), `${r.id} is at revision ${r.revision}, past the matrix's ${cur.revision}`);
  }
  const base = ctx.readBase(MATRIX_PATH);
  if (!base.ok) {
    if (ctx.baseRef === 'none') return { base: 'none' };
    A.push('AUTH_REVISION_UNAVAILABLE', MATRIX_PATH, ['revision'], `cannot read ${MATRIX_PATH} at ${ctx.baseRef} (${base.reason}); fetch it (CI checks out with fetch-depth 0) or run with --base none locally`);
    return { base: 'unavailable' };
  }
  if (base.content === null) return { base: 'absent' };
  let prev;
  try {
    prev = JSON.parse(base.content);
  } catch {
    A.push('AUTH_REVISION_UNAVAILABLE', MATRIX_PATH, ['revision'], `${MATRIX_PATH} at ${ctx.baseRef} is not valid JSON`);
    return { base: 'unavailable' };
  }
  const strip = (d) => {
    const { revision, compatibility, rows, ...rest } = d || {};
    return canonical(rest);
  };
  let changed = strip(cur) !== strip(prev);
  let breaking = false;
  const prevRows = new Map(list(prev.rows).filter(isObject).map((r) => [r.id, r]));
  const changedRows = [];
  for (const r of A.rows) {
    const p = prevRows.get(r.id);
    const at = (k) => A.where(r.id, k);
    if (!p) {
      changed = true;
      changedRows.push(r.id);
      if (r.revision !== cur.revision) A.push('AUTH_REVISION_NOT_BUMPED', MATRIX_PATH, at('revision'), `${r.id} is new, so it carries the matrix revision ${cur.revision}, not ${r.revision}`);
      continue;
    }
    if (rowContent(r) === rowContent(p)) continue;
    changed = true;
    changedRows.push(r.id);
    if (r.revision !== cur.revision || !(cur.revision > prev.revision)) A.push('AUTH_REVISION_NOT_BUMPED', MATRIX_PATH, at('revision'), `${r.id} changed since ${ctx.baseRef}; give it the new matrix revision (above ${prev.revision}) and declare its compatibility`);
    const fields = BREAKING_FIELDS.filter((k) => canonical(r[k]) !== canonical(p[k]));
    if (fields.length) {
      breaking = true;
      if (r.compatibility !== 'breaking') A.push('AUTH_COMPATIBILITY_UNDECLARED', MATRIX_PATH, at('compatibility'), `${r.id} changes ${fields.join(', ')}, which is breaking, but is marked ${r.compatibility}`);
    }
  }
  for (const id of prevRows.keys()) {
    if (A.row(id)) continue;
    changed = true;
    A.push('AUTH_ROW_REMOVED', MATRIX_PATH, ['rows'], `row ${id} is gone since ${ctx.baseRef}; rows are superseded, never deleted`);
  }
  const prevRel = new Map(list(prev.relations).filter(isObject).map((x) => [x.id, x]));
  for (const [id, x] of prevRel) {
    const now = A.relations.find((y) => y.id === id);
    if (!now || now.owner_row !== x.owner_row) breaking = true;
  }
  if (changed && !(cur.revision > prev.revision)) A.push('AUTH_REVISION_NOT_BUMPED', MATRIX_PATH, ['revision'], `the matrix changed since ${ctx.baseRef} but keeps revision ${cur.revision}; raise it above ${prev.revision} here and in DR-0002`);
  if (breaking && cur.compatibility !== 'breaking') A.push('AUTH_COMPATIBILITY_UNDECLARED', MATRIX_PATH, ['compatibility'], `revision ${cur.revision} makes a breaking change but is marked ${cur.compatibility}`);
  return { base: changed ? 'changed' : 'unchanged', baseRevision: prev.revision, changedRows };
}
