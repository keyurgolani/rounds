// Conformance rule for decision records (ROUNDS-01-L01): every
// docs/decisions/DR-<nnnn>-<slug>.json passes decision-record.schema.json and
// these semantic checks: leaf references resolve in leaf-ids.json, a ratified
// record names its approver and pins each governed file's SHA-256, supersedes
// points at a prior revision with a reason, DR-0002 and DR-0003 belong to
// ROUNDS-01-L02 and ROUNDS-01-L03, and affected packages exist in #16's
// contracts/authority/packages.json once that file lands.

import path from 'node:path';
import { createContext, finding, jsonLine, sha256 } from '../lib/context.mjs';
import { validate } from '../lib/json-schema.mjs';
import { leafResolver, loadLeafIds } from '../lib/leaf-ids.mjs';

export const id = 'decision-records';
export const owningLeaf = 'ROUNDS-01-L01';
export const description = 'Decision records: schema, approval, supersession, leaf references, and packages';

export const DECISIONS_DIR = 'docs/decisions';
export const SCHEMA_PATH = 'docs/decisions/decision-record.schema.json';
export const PACKAGES_PATH = 'contracts/authority/packages.json';
export const RESERVED_NUMBERS = { 'DR-0002': 'ROUNDS-01-L02', 'DR-0003': 'ROUNDS-01-L03' };
const FILE_PATTERN = /^DR-(\d{4})-[a-z0-9]+(-[a-z0-9]+)*\.json$/;

function pointerParts(pointer) {
  return pointer.split('/').slice(1).map((p) => (/^\d+$/.test(p) ? Number(p) : p));
}

export function recordFiles(ctx) {
  return ctx.files().filter((f) => path.posix.dirname(f) === DECISIONS_DIR && /^DR-.*\.json$/.test(path.posix.basename(f))).sort();
}

function packageIds(ctx) {
  if (!ctx.exists(PACKAGES_PATH)) return null;
  try {
    const data = ctx.readJson(PACKAGES_PATH);
    const list = Array.isArray(data) ? data : data.packages || [];
    const ids = new Set();
    for (const p of list) for (const k of ['id', 'name', 'service']) if (typeof p?.[k] === 'string') ids.add(p[k]);
    return ids;
  } catch {
    return new Set();
  }
}

export function check(repoRoot, ctx = createContext(repoRoot)) {
  const findings = [];
  let schema;
  try {
    schema = ctx.readJson(SCHEMA_PATH);
  } catch (err) {
    return [finding('DR_RECORD_INVALID', SCHEMA_PATH, 1, `${SCHEMA_PATH} is missing or invalid: ${err.message}`)];
  }
  const resolveLeaf = leafResolver(loadLeafIds(ctx));
  const packages = packageIds(ctx);
  const records = new Map();
  const parsed = [];

  for (const file of recordFiles(ctx)) {
    const text = ctx.read(file);
    let record;
    try {
      record = JSON.parse(text);
    } catch (err) {
      findings.push(finding('DR_RECORD_INVALID', file, 1, `not valid JSON: ${err.message}`));
      continue;
    }
    const push = (code, parts, message) => findings.push(finding(code, file, jsonLine(text, parts), message));
    for (const err of validate(record, schema)) {
      const code = err.keyword === 'required' || (err.keyword === 'minItems' && /\/alternatives$/.test(err.pointer)) ? 'DR_RECORD_INCOMPLETE' : 'DR_RECORD_INVALID';
      push(code, pointerParts(err.pointer), `${err.pointer || '/'} ${err.message}`);
    }
    const base = path.posix.basename(file);
    const m = FILE_PATTERN.exec(base);
    if (!m) push('DR_RECORD_INVALID', [], `${base} is not named DR-<nnnn>-<slug>.json`);
    else if (record.id && record.id !== `DR-${m[1]}`) push('DR_RECORD_INVALID', ['id'], `id ${record.id} does not match the file name ${base}`);
    if (record.id) {
      if (records.has(record.id)) push('DR_DUPLICATE_ID', ['id'], `${record.id} is also used by ${records.get(record.id)}`);
      else records.set(record.id, file);
    }
    parsed.push({ file, text, record, push });
  }

  for (const { record, push } of parsed) {
    const leafRef = (ref, parts, what) => {
      const r = resolveLeaf(ref);
      if (!r.ok) push('VOCAB_UNRESOLVED_REF', parts, `${record.id} ${what}: ${r.reason}`);
    };
    if (typeof record.leaf === 'string') leafRef(record.leaf, ['leaf'], 'leaf');
    for (const ref of record.consumers || []) leafRef(ref, ['consumers'], 'consumer');
    for (const ref of record.prerequisites || []) leafRef(ref, ['prerequisites'], 'prerequisite');
    for (const group of ['corrections', 'specChangeRequests', 'departures']) {
      for (const item of record[group] || []) for (const ref of item.citedBy || []) leafRef(ref, [group], `${group} ${item.id} citedBy`);
    }
    const reserved = RESERVED_NUMBERS[record.id];
    if (reserved && record.leaf !== reserved) push('DR_NUMBER_RESERVED', ['leaf'], `${record.id} belongs to ${reserved}; take the next free number at merge`);

    if (record.status === 'ratified') {
      if (!record.approver || !String(record.approver).trim()) push('DR_RECORD_INCOMPLETE', ['approver'], `${record.id} is ratified but names no approver; review is blocked`);
      if (!record.approvalRef) push('DR_RECORD_INCOMPLETE', ['approvalRef'], `${record.id} is ratified but has no approvalRef (PR number and governed-file SHA-256)`);
    }
    if (record.approvalRef?.governedFiles) {
      if (record.authorityBoundary && !record.approvalRef.governedFiles.some((g) => g.path === record.authorityBoundary)) {
        push('DR_RECORD_INCOMPLETE', ['approvalRef'], `${record.id} approvalRef does not pin its authority boundary ${record.authorityBoundary}`);
      }
      for (const g of record.approvalRef.governedFiles) {
        if (!ctx.exists(g.path)) { push('DR_APPROVAL_STALE', ['approvalRef'], `${record.id} governs ${g.path}, which does not exist`); continue; }
        const actual = sha256(ctx.read(g.path));
        if (actual !== g.sha256) {
          push('DR_APPROVAL_STALE', ['approvalRef'], `${g.path} changed after ${record.id}@${record.revision} was approved (sha256 ${actual.slice(0, 12)}..., approved ${String(g.sha256).slice(0, 12)}...); raise the revision and get it re-approved`);
        }
      }
    }
    if (record.authorityBoundary && !ctx.exists(record.authorityBoundary)) {
      push('DR_RECORD_INVALID', ['authorityBoundary'], `${record.id} authority boundary ${record.authorityBoundary} does not exist`);
    }
    if (record.supersedes) {
      const [sid, srev] = String(record.supersedes).split('@');
      const prior = sid === record.id ? { revision: record.revision } : parsed.find((p) => p.record.id === sid)?.record;
      if (!prior) push('DR_SUPERSEDES_INVALID', ['supersedes'], `${record.id} supersedes ${record.supersedes}, which is not a decision record here`);
      else if (sid === record.id && !(Number(srev) < record.revision)) push('DR_SUPERSEDES_INVALID', ['supersedes'], `${record.id}@${record.revision} must supersede an earlier revision, not ${record.supersedes}`);
      if (!record.supersessionReason) push('DR_SUPERSEDES_INVALID', ['supersessionReason'], `${record.id} supersedes ${record.supersedes} without a supersessionReason`);
    } else if (record.revision > 1) {
      push('DR_SUPERSEDES_INVALID', ['supersedes'], `${record.id}@${record.revision} must name the revision it supersedes`);
    }
    const ids = new Set();
    (record.decisions || []).forEach((d, i) => {
      if (ids.has(d.id)) push('DR_RECORD_INVALID', ['decisions', i], `${record.id} decision ${d.id} is listed twice`);
      ids.add(d.id);
    });
    if (packages) {
      for (const pkg of record.affectedPackages || []) {
        if (!packages.has(pkg)) push('DR_UNKNOWN_PACKAGE', ['affectedPackages'], `${record.id} affected package "${pkg}" is not in ${PACKAGES_PATH}`);
      }
    }
  }
  return findings;
}

export function summary(repoRoot, ctx = createContext(repoRoot)) {
  const lines = [];
  for (const file of recordFiles(ctx)) {
    try {
      const r = ctx.readJson(file);
      const open = (r.decisions || []).filter((d) => d.status === 'ratified-here').length;
      lines.push(`${r.id}@${r.revision} ${r.status}${r.approvalRef?.pr ? ` (PR #${r.approvalRef.pr})` : ''}: ${r.decisions?.length || 0} decisions${open ? `, ${open} ratified-here` : ''}, ${r.consumers?.length || 0} consumers, boundary ${r.authorityBoundary}`);
    } catch {
      lines.push(`${file}: unreadable`);
    }
  }
  lines.push(ctx.exists(PACKAGES_PATH) ? `affected packages checked against ${PACKAGES_PATH}` : `affected packages not checked: ${PACKAGES_PATH} does not exist yet (#16)`);
  return lines;
}
