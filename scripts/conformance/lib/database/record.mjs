// DR-0004's own checks (ROUNDS-02-L01), beyond decision-record.schema.json
// and the decision-records rule: the ten decisions each with one concern,
// one store, one owning process and leaf, alternatives, failure modes,
// limits, and consequences; alternatives A to D and the three rejections;
// invariants, containment dispositions, identifiers, the storage plan, the
// PocketBase analysis with its ratified line and the commit it counted,
// credentials, the export gate, and every changed authority with its order
// and rollback. Citations at the audited revision resolve there, and #16's
// storage and target_path cells cite DR-0004.

import { finding, jsonLine } from '../context.mjs';
import { dockerfilePin, minor } from './benchmark.mjs';
import { ERD_DOC_PATH } from './erd.mjs';

export const RECORD_PATH = 'docs/decisions/DR-0004-canonical-database.json';
export const ADR_PATH = 'docs/decisions/DR-0004-canonical-database.md';
export const MATRIX_PATH = 'contracts/authority/matrix.json';
export const PACKAGES_PATH = 'contracts/authority/packages.json';
export const DOCKERFILE_PATH = 'pocketbase/Dockerfile';
export const AUDITED = '62d4eae';
export const CONCERNS = [
  'canonical-write-database', 'transaction-owner', 'gateway-placement', 'account-authorization', 'idempotency-store',
  'aggregate-version-model', 'outbox-projectors', 'backup-restore', 'pocketbase-version', 'byte-store',
];
export const ALTERNATIVES = ['A', 'B', 'C', 'D'];
export const REJECTED = ['fastapi-rest', 'fastapi-sqlite', 'postgres-pocketbase'];
export const MECHANISMS = ['transaction', 'unique-index', 'composed-sub-command'];
export const REQUIRED_CHANGES = ['containment-stores', 'pocketbase-version', 'byte-store'];
const DECISION_FIELDS = ['concern', 'store', 'process', 'owningLeaf', 'failureModes', 'limits'];
const CITATION = /^([A-Za-z0-9_./-]+)@([0-9a-f]{7,40}):L(\d+)(?:-L(\d+))?$/;
const STORAGE_CELL = /^DR-0004@(\d+):([a-z][a-z0-9-]*(?:\+[a-z][a-z0-9-]*)*)$/;
const PENDING_HERE = 'pending:ROUNDS-02-L01';

const nonEmpty = (v) => (typeof v === 'string' ? v.trim().length > 0 : Array.isArray(v) ? v.length > 0 && v.every(nonEmpty) : v !== undefined && v !== null);

export function checkRecord(ctx, { record, text, resolveLeaf, erd, matrix, matrixText, packages, packagesText, dockerfile }) {
  const findings = [];
  const f = (code, parts, message) => findings.push(finding(code, RECORD_PATH, jsonLine(text, parts), message));
  const leaf = (ref, parts, what) => {
    const r = resolveLeaf(ref);
    if (!r.ok) f('DB_UNKNOWN_REF', parts, `${what}: ${r.reason}`);
  };
  const stores = new Set((erd?.stores || []).map((s) => s.id));
  const entities = new Set((erd?.entities || []).map((e) => e.id));
  const rows = new Set((matrix?.rows || []).map((r) => r.id));

  // The ten decisions.
  const decisions = record.decisions || [];
  const byConcern = new Map();
  decisions.forEach((d, i) => {
    for (const k of DECISION_FIELDS) if (!nonEmpty(d[k])) f('DB_RECORD_INCOMPLETE', ['decisions', i], `decision ${d.id} has no ${k}`);
    if (!nonEmpty(d.alternatives)) f('DB_RECORD_INCOMPLETE', ['decisions', i, 'alternatives'], `decision ${d.id} has no alternatives`);
    if (d.concern) {
      if (byConcern.has(d.concern)) f('DB_TWO_AUTHORITIES', ['decisions', i, 'concern'], `${d.concern} is decided by both ${byConcern.get(d.concern)} and ${d.id}; one concern has one authority`);
      byConcern.set(d.concern, d.id);
      if (!CONCERNS.includes(d.concern)) f('DB_UNKNOWN_REF', ['decisions', i, 'concern'], `${d.id} decides ${d.concern}, which is not one of DR-0004's ten concerns`);
    }
    if (typeof d.store === 'string' && /[,;+]|\band\b/.test(d.store) && !d.store.startsWith('n/a:')) {
      f('DB_TWO_AUTHORITIES', ['decisions', i, 'store'], `${d.id} names more than one store (${d.store}); a decision names one store`);
    } else if (typeof d.store === 'string' && !d.store.startsWith('n/a:') && !stores.has(d.store)) {
      f('DB_UNKNOWN_REF', ['decisions', i, 'store'], `${d.id} names store ${d.store}, which the ERD doesn't list`);
    }
    if (d.owningLeaf) leaf(d.owningLeaf, ['decisions', i, 'owningLeaf'], `${d.id} owning leaf`);
  });
  for (const c of CONCERNS) if (!byConcern.has(c)) f('DB_RECORD_INCOMPLETE', ['decisions'], `no decision decides ${c}; DR-0004 decides all ten`);

  // Alternatives A to D, and the three rejections.
  const alts = record.alternativesEvaluated || [];
  for (const id of ALTERNATIVES) {
    const a = alts.find((x) => x.id === id);
    if (!a) { f('DB_RECORD_INCOMPLETE', ['alternativesEvaluated'], `alternative ${id} is not evaluated`); continue; }
    for (const k of ['name', 'runnerWritePath', 'imageBuild', 'bindings', 'nginxChange', 'verdict', 'reason']) {
      if (!nonEmpty(a[k])) f('DB_RECORD_INCOMPLETE', ['alternativesEvaluated', alts.indexOf(a)], `alternative ${id} has no ${k}`);
    }
  }
  if (alts.filter((a) => a.verdict === 'chosen').length !== 1) f('DB_TWO_AUTHORITIES', ['alternativesEvaluated'], 'exactly one of alternatives A to D is chosen');
  for (const id of REJECTED) {
    const r = (record.rejected || []).find((x) => x.id === id);
    if (!r || !nonEmpty(r.reason) || !nonEmpty(r.source)) f('DB_RECORD_INCOMPLETE', ['rejected'], `the rejected option ${id} has no reason and source`);
  }

  // Invariants: a #16 row and a mechanism each, owned by the row's command owner.
  const commandOwner = new Map((matrix?.rows || []).map((r) => [r.id, r.command_owner?.leaf]));
  (record.invariants || []).forEach((inv, i) => {
    if (!rows.has(inv.row)) f('DB_UNKNOWN_REF', ['invariants', i, 'row'], `invariant ${inv.id} names row ${inv.row}, which ${MATRIX_PATH} doesn't have`);
    else if (inv.owningLeaf && commandOwner.get(inv.row) && inv.owningLeaf !== commandOwner.get(inv.row)) {
      f('DB_TWO_AUTHORITIES', ['invariants', i, 'owningLeaf'], `invariant ${inv.id} names ${inv.owningLeaf}, but ${inv.row}'s commands belong to ${commandOwner.get(inv.row)}; the row's command owner owns its invariant`);
    }
    const mech = Array.isArray(inv.mechanism) ? inv.mechanism : [inv.mechanism];
    if (!mech.length || mech.some((m) => !MECHANISMS.includes(m))) f('DB_RECORD_INCOMPLETE', ['invariants', i, 'mechanism'], `invariant ${inv.id} needs a mechanism from ${MECHANISMS.join(', ')}`);
    if (inv.owningLeaf) leaf(inv.owningLeaf, ['invariants', i, 'owningLeaf'], `invariant ${inv.id} owner`);
    if (inv.site) checkCitation(ctx, inv.site, (m) => f('DB_UNKNOWN_REF', ['invariants', i, 'site'], `invariant ${inv.id}: ${m}`));
  });
  if ((record.invariants || []).length < 4) f('DB_RECORD_INCOMPLETE', ['invariants'], 'the four browser-side invariants each need a row and a mechanism');

  // Containment stores: ratified, or a path and its leaf.
  (record.containment || []).forEach((c, i) => {
    if (!['ratified', 'path'].includes(c.disposition)) f('DB_RECORD_INCOMPLETE', ['containment', i], `${c.store} has no disposition (ratified or path)`);
    if (c.leaf) leaf(c.leaf, ['containment', i, 'leaf'], `${c.store} leaf`);
    if (c.disposition === 'path' && !c.owningLeaf) f('DB_RECORD_INCOMPLETE', ['containment', i], `${c.store} has a path but no owning leaf`);
    if (c.owningLeaf) leaf(c.owningLeaf, ['containment', i, 'owningLeaf'], `${c.store} owner`);
    for (const e of c.entities || []) if (erd && !entities.has(e)) f('DB_UNKNOWN_REF', ['containment', i, 'entities'], `${c.store} names ${e}, which the ERD doesn't have`);
  });
  for (const e of erd?.entities || []) {
    if (e.group !== 'containment' || e.status !== 'live') continue;
    if (!(record.containment || []).some((c) => (c.entities || []).includes(e.id))) f('DB_RECORD_INCOMPLETE', ['containment'], `the containment store ${e.id} has no disposition`);
  }

  // Changed authorities: disposition, ordered dependency, rollback.
  const changes = record.changes || [];
  for (const id of REQUIRED_CHANGES) if (!changes.some((c) => c.authority === id)) f('DB_CHANGE_INCOMPLETE', ['changes'], `the changed authority ${id} has no entry`);
  changes.forEach((c, i) => {
    for (const k of ['disposition', 'dependsOn', 'rollback']) if (!nonEmpty(c[k])) f('DB_CHANGE_INCOMPLETE', ['changes', i], `${c.authority} has no ${k}`);
    for (const ref of c.dependsOn || []) leaf(ref, ['changes', i, 'dependsOn'], `${c.authority} depends on`);
  });
  // Ratifying the containment stores in place comes after each leaf that built one.
  const contain = changes.find((c) => c.authority === 'containment-stores');
  if (contain && Array.isArray(contain.dependsOn) && contain.dependsOn.length) {
    const after = new Set(contain.dependsOn.map((ref) => String(ref).split('/')[0]));
    for (const c of record.containment || []) {
      if (c.disposition === 'ratified' && c.leaf && !after.has(c.leaf)) {
        f('DB_CHANGE_INCOMPLETE', ['changes', changes.indexOf(contain), 'dependsOn'], `containment-stores ratifies ${c.store} in place but doesn't come after ${c.leaf}, which built it`);
      }
    }
  }

  // Credentials: the superuser and every service identity, each with a
  // disposition and the leaf that retires or owns it.
  const creds = record.credentials || [];
  const services = (erd?.entities || []).filter((e) => e.type === 'auth' && e.id !== 'users' && e.scope === 'service').map((e) => e.id);
  for (const need of ['superuser', ...services]) {
    const c = creds.find((x) => x.holder === need);
    if (!c || !nonEmpty(c.disposition) || !c.leaf) f('DB_SECURITY_INCOMPLETE', ['credentials'], `the ${need} credential needs a disposition and its leaf`);
  }
  creds.forEach((c, i) => c.leaf && leaf(c.leaf, ['credentials', i, 'leaf'], `${c.holder} credential leaf`));
  const bytes = decisions.find((d) => d.concern === 'byte-store');
  if (bytes && !nonEmpty(bytes.dedupe)) f('DB_SECURITY_INCOMPLETE', ['decisions', decisions.indexOf(bytes)], 'the byte store must state its dedupe scope (no cross-account oracle)');

  // The export gate and the foundation exemption.
  if ((record.exportGate || []).length < 4 || (record.exportGate || []).some((g) => !nonEmpty(g.producer))) f('DB_RECORD_INCOMPLETE', ['exportGate'], 'each of the four export-gate items names its producer');
  for (const g of record.exportGate || []) for (const p of [].concat(g.producer || [])) leaf(p, ['exportGate'], `export gate producer for ${g.item}`);
  if (!nonEmpty(record.foundationExemption)) f('DB_RECORD_INCOMPLETE', ['foundationExemption'], 'state the foundation exemption (spec 3232-3236)');

  // Identifiers and the storage plan.
  for (const k of ['identifiers', 'storagePlan']) if (!nonEmpty(record[k])) f('DB_RECORD_INCOMPLETE', [k], `${k} is empty`);
  (record.storagePlan || []).forEach((s, i) => {
    for (const k of ['location', 'growthAtFloor', 'writeAmplification', 'compaction', 'lockBudget', 'sizing']) if (!nonEmpty(s[k])) f('DB_RECORD_INCOMPLETE', ['storagePlan', i], `${s.store} has no ${k}`);
  });

  // PocketBase: DR-0004 ratifies a line, so a patch on it is a pin change and
  // a port to another line supersedes the record first. The pin at
  // ratification is history, and the counts name the commit they counted.
  const pb = record.pocketbase || {};
  for (const k of ['line', 'pinAtRatification', 'decision', 'countedAt', 'breakSites', 'strategy', 'freezeWindow', 'rollbackBoundary', 'triggers']) {
    if (!nonEmpty(pb[k])) f('DB_RECORD_INCOMPLETE', ['pocketbase'], `pocketbase.${k} is missing`);
  }
  const pinned = dockerfilePin(dockerfile);
  if (!pinned) f('DB_VERSION_MISMATCH', ['pocketbase', 'line'], `${DOCKERFILE_PATH} has no readable ARG PB_VERSION=<x.y.z>, so the pin can't be checked against DR-0004's line`);
  else if (pb.line && minor(pinned) !== pb.line) f('DB_VERSION_MISMATCH', ['pocketbase', 'line'], `${DOCKERFILE_PATH} pins ${pinned}, off DR-0004's ${pb.line} line; a port to another line supersedes DR-0004 first`);
  if (pb.line && pb.pinAtRatification && minor(pb.pinAtRatification) !== pb.line) f('DB_VERSION_MISMATCH', ['pocketbase', 'pinAtRatification'], `the pin at ratification ${pb.pinAtRatification} is off the ${pb.line} line`);
  if (pb.line && typeof pb.decision === 'string' && !pb.decision.includes(pb.line)) f('DB_VERSION_MISMATCH', ['pocketbase', 'decision'], `decision 9 "${pb.decision}" doesn't name the ${pb.line} line it ratifies`);
  if (pb.countedAt) {
    const t = ctx.tree(pb.countedAt);
    if (!t.ok) f('DB_UNKNOWN_REF', ['pocketbase', 'countedAt'], `the version analysis counted ${pb.countedAt}, which can't be read: ${t.reason}`);
  }
  (pb.breakSites || []).forEach((b, i) => {
    if (!nonEmpty(b.upstream)) f('DB_RECORD_INCOMPLETE', ['pocketbase', 'breakSites', i], `break site ${b.id} cites no upstream release note`);
  });

  // Baseline facts cited at the audited revision resolve there.
  (record.baselineFacts || []).forEach((b, i) => checkCitation(ctx, b.citation, (m) => f('DB_UNKNOWN_REF', ['baselineFacts', i, 'citation'], `${b.id}: ${m}`)));

  // #16's cells this leaf fills: storage cites DR-0004's stores; no package
  // keeps a pending target_path.
  (matrix?.rows || []).forEach((r, i) => {
    const cell = r.storage;
    const at = (code, message) => findings.push(finding(code, MATRIX_PATH, jsonLine(matrixText, ['rows', i, 'storage']), message));
    if (cell === PENDING_HERE) return at('DB_STORAGE_PENDING', `${r.id} storage is still ${PENDING_HERE}; name its DR-0004 store`);
    if (typeof cell !== 'string' || /^(n\/a:|blocked:OD-|pending:)/.test(cell)) return undefined;
    const m = STORAGE_CELL.exec(cell);
    if (!m) return at('DB_UNKNOWN_REF', `${r.id} storage "${cell}" is not DR-0004@<revision>:<store>[+<store>]`);
    if (Number(m[1]) > record.revision) at('DB_VERSION_MISMATCH', `${r.id} storage cites DR-0004@${m[1]}; DR-0004 is at revision ${record.revision}`);
    for (const s of m[2].split('+')) if (!stores.has(s)) at('DB_UNKNOWN_REF', `${r.id} storage names store ${s}, which the ERD doesn't list`);
    return undefined;
  });
  (packages?.packages || []).forEach((p, i) => {
    if (p.target_path === PENDING_HERE) findings.push(finding('DB_STORAGE_PENDING', PACKAGES_PATH, jsonLine(packagesText, ['packages', i, 'target_path']), `${p.id} target_path is still ${PENDING_HERE}; DR-0004 places the package`));
  });

  // Every other DR-0004@<n>[:<id>] in docs/ and contracts/ cites a revision
  // that exists and a decision, store, or entity this record and its ERD name.
  const known = new Set([...decisions.map((d) => d.id), ...stores, ...entities]);
  for (const file of ctx.files()) {
    if (!/^(docs|contracts)\/.+\.(md|json)$/.test(file) || [ADR_PATH, MATRIX_PATH, ERD_DOC_PATH].includes(file)) continue;
    const body = ctx.read(file);
    if (!body.includes('DR-0004@')) continue;
    body.split('\n').forEach((line, i) => {
      for (const m of line.matchAll(/DR-0004@(\d+)(?::([A-Za-z_][A-Za-z0-9_-]*))?/g)) {
        if (Number(m[1]) < 1 || Number(m[1]) > record.revision) findings.push(finding('DB_VERSION_MISMATCH', file, i + 1, `${m[0]} cites a revision DR-0004 hasn't reached (it is at ${record.revision})`));
        else if (m[2] && !known.has(m[2])) findings.push(finding('DB_UNKNOWN_REF', file, i + 1, `${m[0]} names ${m[2]}, which is no DR-0004 decision, store, or entity`));
      }
    });
  }
  return findings;
}

function checkCitation(ctx, citation, report) {
  const m = CITATION.exec(String(citation || ''));
  if (!m) { report(`"${citation}" is not path@revision:L<a>[-L<b>]`); return; }
  const [, file, rev, a, b] = m;
  const tree = ctx.tree(rev);
  if (!tree.ok) { report(`cannot read ${rev}: ${tree.reason}`); return; }
  const body = tree.read(file);
  if (body === null) { report(`${file} does not exist at ${rev}`); return; }
  const lines = body.split('\n').length;
  const end = Number(b || a);
  if (Number(a) < 1 || end < Number(a) || end > lines) report(`${file}@${rev} has ${lines} lines; L${a}${b ? `-L${b}` : ''} is out of range`);
}
