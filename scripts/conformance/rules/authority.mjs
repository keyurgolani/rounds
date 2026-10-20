// Conformance rule for the source-of-truth and package-boundary matrix
// (ROUNDS-01-L02, DR-0002).
//
// check:    #16's rules 1 to 12 over contracts/authority/, coverage of every
//           store at the audited revision, citations, secrets, open owner
//           decisions, owner labels, owner-sentence corrections, and
//           revisions against the base branch. With --review <rounds-review>
//           it also checks the spec rows verbatim, the services, the ledger
//           pin, and the owner labels against the catalog.
// generate: contracts/authority/baseline-stores.json (keeping each store's
//           rows and note) and docs/authority.md.

import { createContext } from '../lib/context.mjs';
import { prettyJson } from '../lib/pretty-json.mjs';
import {
  AUTHORITY_MD, BASELINE_STORES_PATH, OPEN_DECISIONS, auditedTree, blockedRows, checkAuthorities, checkCells, checkCitations, checkCommands,
  checkConflicts, checkCorrections, checkExamples, checkIdentity, checkLedger, checkOpenDecisions, checkOwnerLabels, checkPackages,
  checkReadModels, checkRelations, checkRevision, checkRows, checkSecrets, checkSpecRows, checkStores, checkWriters, loadAuthority, pendingByLeaf,
} from '../lib/authority/matrix.mjs';
import { renderAuthorityMd } from '../lib/authority/render.mjs';
import { baselineStoresDocument } from '../lib/authority/stores.mjs';

export const id = 'authority';
export const owningLeaf = 'ROUNDS-01-L02';
export const description = 'Source-of-truth and package-boundary matrix: rules 1 to 12, store coverage, citations, secrets, open decisions, owner labels, and revisions';

const memo = new WeakMap();

function analyze(ctx) {
  if (memo.has(ctx)) return memo.get(ctx);
  const findings = [];
  const A = loadAuthority(ctx, findings);
  checkIdentity(A);
  checkSpecRows(ctx, A);
  checkCells(A);
  checkRows(A);
  checkAuthorities(A);
  checkWriters(A);
  checkConflicts(A);
  checkRelations(A);
  checkReadModels(A);
  checkPackages(A);
  checkOwnerLabels(ctx, A);
  checkLedger(ctx, A);
  checkCommands(A);
  checkOpenDecisions(A);
  checkCorrections(A);
  const tree = auditedTree(ctx, A);
  const extracted = checkStores(A, tree);
  checkCitations(A, tree);
  checkSecrets(ctx, A, tree);
  checkExamples(ctx, A);
  const revision = checkRevision(ctx, A);
  const result = { findings, A, tree, extracted, revision };
  memo.set(ctx, result);
  return result;
}

export function check(repoRoot, ctx = createContext(repoRoot)) {
  return analyze(ctx).findings;
}

export function generate(repoRoot, ctx = createContext(repoRoot)) {
  const { A, extracted } = analyze(ctx);
  const outputs = [];
  // An unreadable baseline-stores.json is left for a person to fix, so its
  // hand-written rows are never lost.
  if (extracted && A.matrix && (A.stores || !ctx.exists(BASELINE_STORES_PATH))) {
    outputs.push({ path: BASELINE_STORES_PATH, content: prettyJson(baselineStoresDocument(extracted, A.stores, A.matrix.auditedRevision)) });
  }
  if (A.matrix && A.packages && A.labels && A.dr) outputs.push({ path: AUTHORITY_MD, content: renderAuthorityMd(A) });
  return outputs;
}

export function summary(repoRoot, ctx = createContext(repoRoot)) {
  const { A, revision } = analyze(ctx);
  const m = A.matrix;
  if (!m) return ['matrix unreadable'];
  const lines = [];
  const scopes = ['account', 'platform-global', 'pack-owned'].map((s) => `${A.rows.filter((r) => r.scope === s).length} ${s}`);
  const specRows = A.rows.filter((r) => r.spec).length;
  const dr = A.dr ? `DR-0002@${A.dr.revision} ${A.dr.status}${A.dr.approvalRef?.pr ? ` (PR #${A.dr.approvalRef.pr})` : ''}` : 'DR-0002 missing';
  lines.push(`matrix revision ${m.revision} (${dr}), ${m.compatibility}; audited revision ${m.auditedRevision}`);
  lines.push(`rows: ${A.rows.length} (${scopes.join(', ')}); ${specRows} carry the 31 spec rows (spec 781-811), the rest are added or split`);
  const found = A.conflicts.filter((c) => c.foundHere).map((c) => c.id);
  lines.push(`conflicts: ${A.conflicts.length} (${found.length ? `${found.join(', ')} found here` : 'none found here'}); relations: ${A.relations.length}; read models: ${A.readModels.length}, one projector each`);
  const blocked = blockedRows(A);
  const byOd = OPEN_DECISIONS.map((id) => [id, blocked.filter((b) => b.ods.includes(id)).map((b) => b.row)]).filter(([, rows]) => rows.length);
  lines.push(`blocked rows: ${blocked.length}${byOd.length ? ` (${byOd.map(([id, rows]) => `${id}: ${rows.join(', ')}`).join('; ')})` : ''}`);
  const pending = [...pendingByLeaf(A).entries()].sort(([a, x], [b, y]) => y.cells - x.cells || a.localeCompare(b));
  lines.push(`pending cells by leaf (${pending.reduce((n, [, v]) => n + v.cells, 0)} cells, ${pending.length} leaves): ${pending.map(([leaf, v]) => `${leaf} ${v.cells}`).join(', ')}`);
  const stores = A.storeList;
  lines.push(`baseline stores: ${stores.filter((s) => s.kind === 'collection').length} collections and ${stores.filter((s) => s.kind === 'browser-key').length} browser key families at ${m.auditedRevision}`);
  lines.push(`owner labels: ${A.labelList.length}; owner-sentence corrections: ${A.corrections?.entries?.length ?? 0}; packages: ${A.packageList.length}`);
  lines.push(ctx.reviewRoot ? `spec rows, services, ledger pin, and owner labels checked against ${ctx.reviewRoot}` : 'spec rows, services, and ledger pin not checked against rounds-review (pass --review <rounds-review>)');
  lines.push(`revision check: ${revision.base}${revision.baseRevision ? ` (base revision ${revision.baseRevision}${revision.changedRows?.length ? `, ${revision.changedRows.length} rows changed` : ''})` : ''}`);
  return lines;
}
