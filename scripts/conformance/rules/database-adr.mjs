// Conformance rule for the canonical database ADR (ROUNDS-02-L01, DR-0004).
//
// Rejects a decision without its owner, store, process, alternatives,
// failure modes, limits, or consequences; two authorities for one concern;
// unknown packages, leaves, rows, stores, or entities; a pin off DR-0004's
// PocketBase line, or an ERD or receipt at another revision; a changed
// authority without its disposition, order, and rollback; ERD relations
// without delete or merge behavior; a collection no ERD entity covers; a
// planned account table no index leads with its partition; a migration the
// schema snapshot hasn't seen (DB_ERD_STALE); a benchmark receipt without its
// label, profile, a target, the spec's unit and limit, a value its scales
// give, the basis its extrapolations give, or a consequence for a miss; a
// rollback default whose basis or verdict isn't its target's; and #16's
// storage and target_path cells still pending this leaf. generate() builds
// erd.json from the written part and the native schema snapshot, and
// renders the ADR (record, written ERD, receipt) and the generated ERD.

import { createContext, finding } from '../lib/context.mjs';
import { leafResolver, loadLeafIds } from '../lib/leaf-ids.mjs';
import { prettyJson } from '../lib/pretty-json.mjs';
import { BASELINE_STORES_PATH, DECISIONS_PATH, DECISIONS_SCHEMA_PATH, ENDPOINTS_PATH, ERD_DOC_PATH, ERD_PATH, ERD_SCHEMA_PATH, SNAPSHOT_PATH, SNAPSHOT_SCHEMA_PATH,
  buildErd, checkDecisions, checkErd } from '../lib/database/erd.mjs';
import { RECEIPT_PATH, RECEIPT_SCHEMA_PATH, checkReceipt, dockerfilePin, minor, receiptSummary } from '../lib/database/benchmark.mjs';
import { ADR_PATH, DOCKERFILE_PATH, MATRIX_PATH, PACKAGES_PATH, RECORD_PATH, checkRecord } from '../lib/database/record.mjs';
import { renderAdr, renderErdDoc } from '../lib/database/render.mjs';
import { validate } from '../lib/json-schema.mjs';

export const id = 'database-adr';
export const owningLeaf = 'ROUNDS-02-L01';
export const description = 'The canonical database ADR: ten decisions, alternatives, ERD, benchmark receipt, and #16\'s storage cells';

function load(ctx, rel) {
  if (!ctx.exists(rel)) return { missing: true };
  const text = ctx.read(rel);
  try {
    return { text, json: JSON.parse(text) };
  } catch (err) {
    return { text, error: err.message };
  }
}

function inputs(ctx) {
  const out = {};
  for (const [k, rel] of Object.entries({ record: RECORD_PATH, decisions: DECISIONS_PATH, decisionsSchema: DECISIONS_SCHEMA_PATH, erd: ERD_PATH, erdSchema: ERD_SCHEMA_PATH,
    snapshot: SNAPSHOT_PATH, snapshotSchema: SNAPSHOT_SCHEMA_PATH, receipt: RECEIPT_PATH, receiptSchema: RECEIPT_SCHEMA_PATH, endpoints: ENDPOINTS_PATH,
    baseline: BASELINE_STORES_PATH, matrix: MATRIX_PATH, packages: PACKAGES_PATH })) {
    out[k] = load(ctx, rel);
    out[k].path = rel;
  }
  out.dockerfile = ctx.exists(DOCKERFILE_PATH) ? ctx.read(DOCKERFILE_PATH) : null;
  return out;
}

export function check(repoRoot, ctx = createContext(repoRoot)) {
  const findings = [];
  const I = inputs(ctx);
  for (const k of ['record', 'decisions', 'decisionsSchema', 'erd', 'erdSchema', 'snapshot', 'snapshotSchema', 'receipt', 'receiptSchema']) {
    if (I[k].missing) findings.push(finding(k === 'receipt' ? 'DB_BENCH_INCOMPLETE' : 'DB_RECORD_MISSING', I[k].path, 1, `${I[k].path} is missing`));
    else if (I[k].error) findings.push(finding('DB_RECORD_INVALID', I[k].path, 1, `${I[k].path} is not valid JSON: ${I[k].error}`));
  }
  if (findings.length) return findings;
  const resolveLeaf = leafResolver(loadLeafIds(ctx));
  const record = I.record.json;
  for (const err of validate(I.snapshot.json, I.snapshotSchema.json)) findings.push(finding('DB_ERD_INVALID', SNAPSHOT_PATH, 1, `${err.pointer || '/'} ${err.message}`));
  const line = record.pocketbase?.line;
  if (line && minor(I.snapshot.json.pocketbaseVersion) !== line) {
    findings.push(finding('DB_VERSION_MISMATCH', SNAPSHOT_PATH, 1, `the snapshot was taken on PocketBase ${I.snapshot.json.pocketbaseVersion}, off DR-0004's ${line} line; regenerate it with harness/bench/schema_dump.py`));
  }
  findings.push(...checkDecisions({ decisions: I.decisions.json, text: I.decisions.text, schema: I.decisionsSchema.json, snapshot: I.snapshot.json, resolveLeaf, record }));
  findings.push(...checkErd(ctx, { erd: I.erd.json, erdText: I.erd.text, schema: I.erdSchema.json, snapshot: I.snapshot.json, decisions: I.decisions.json, record }));
  findings.push(...checkRecord(ctx, { record, text: I.record.text, resolveLeaf, erd: I.erd.json, matrix: I.matrix.json, matrixText: I.matrix.text,
    packages: I.packages.json, packagesText: I.packages.text, dockerfile: I.dockerfile }));
  findings.push(...checkReceipt({ receipt: I.receipt.json, text: I.receipt.text, schema: I.receiptSchema.json, pocketbase: record.pocketbase || {}, record }));
  if (record.benchmark?.result && I.receipt.json.result !== record.benchmark.result) {
    findings.push(finding('DB_VERSION_MISMATCH', RECORD_PATH, 1, `DR-0004 records the benchmark as ${record.benchmark.result}; the receipt says ${I.receipt.json.result}`));
  }
  return findings;
}

export function generate(repoRoot, ctx = createContext(repoRoot)) {
  const I = inputs(ctx);
  if (I.snapshot.missing || I.snapshot.error || I.decisions.missing || I.decisions.error) return [];
  const erd = buildErd(I.snapshot.json, I.decisions.json, I.endpoints.json || null, I.baseline.json || null);
  const out = [{ path: ERD_PATH, content: prettyJson(erd) }, { path: ERD_DOC_PATH, content: renderErdDoc(erd) }];
  if (I.record.json) out.push({ path: ADR_PATH, content: renderAdr(I.record.json, I.decisions.json, I.receipt.json || null) });
  return out;
}

export function summary(repoRoot, ctx = createContext(repoRoot)) {
  const I = inputs(ctx);
  const r = I.record.json;
  const lines = [];
  if (!r) return [`${RECORD_PATH}: missing`];
  const open = (r.decisions || []).filter((d) => d.status !== 'ratified').map((d) => d.id);
  lines.push(`${r.id}@${r.revision} ${r.status}${r.approvalRef?.pr ? ` (PR #${r.approvalRef.pr})` : ''}: ${(r.decisions || []).length} decisions${open.length ? `, open: ${open.join(', ')}` : ''}, ${(r.consumers || []).length} consuming leaves`);
  const d = I.decisions.json;
  if (d) lines.push(`${DECISIONS_PATH}: ${d.entities.filter((x) => !x.status).length} live tables annotated, ${d.entities.filter((x) => x.status).length} planned or held, ${d.relations.length} relations`);
  const e = I.erd.json;
  if (e) lines.push(`${ERD_PATH}: ${e.entities.filter((x) => x.status === 'live').length} live entities, ${e.entities.filter((x) => x.status !== 'live').length} planned or held, ${e.relations.length} relations, snapshot ${String(e.snapshot?.revision).slice(0, 7)}`);
  lines.push(`${RECEIPT_PATH}: ${receiptSummary(I.receipt.json)}`);
  lines.push(`PocketBase: pinned ${dockerfilePin(I.dockerfile)}, line ${r.pocketbase?.line}, decision ${r.pocketbase?.decision}`);
  return lines;
}
