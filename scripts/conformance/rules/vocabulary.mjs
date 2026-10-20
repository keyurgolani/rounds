// Conformance rule for the product vocabulary (ROUNDS-01-L01, DR-0001).
//
// check:    registry shape and references, label and alias collisions, pack
//           collisions, usage rules, term examples, leaf IDs, coverage of every
//           baseline name, positioning lines, data-preserving cutover wording,
//           and revision discipline against main.
// generate: frontend/src/vocabulary/labels.ts, docs/vocabulary.md, and
//           docs/decisions/DR-0001-owner-corrections.md.

import { createContext } from '../lib/context.mjs';
import { leafResolver } from '../lib/leaf-ids.mjs';
import {
  checkAdapters, checkCoverage, checkCutover, checkLeafIds, checkRevision, checkTerms, decisionRecordFile, loadRegistry,
} from '../lib/vocabulary/registry.mjs';
import { CORRECTIONS_MD, LABELS_TS, VOCABULARY_MD, renderCorrectionsMd, renderLabelsTs, renderVocabularyMd } from '../lib/vocabulary/render.mjs';

export const id = 'vocabulary';
export const owningLeaf = 'ROUNDS-01-L01';
export const description = 'Product vocabulary registry, adapters, leaf IDs, coverage set, positioning, and cutover wording';

const memo = new WeakMap();

function analyze(ctx) {
  if (memo.has(ctx)) return memo.get(ctx);
  const findings = [];
  const reg = loadRegistry(ctx, findings);
  const resolveLeaf = leafResolver(reg.leafIds);
  checkLeafIds(ctx, reg, findings);
  const byId = checkTerms(ctx, reg, findings, resolveLeaf) || new Map();
  checkAdapters(ctx, reg, findings, resolveLeaf, byId);
  const coverage = reg.terms && reg.adapters ? checkCoverage(ctx, reg, findings, byId) : null;
  checkCutover(ctx, reg, findings);
  const revision = checkRevision(ctx, reg, findings);
  const result = { findings, reg, byId, coverage, revision };
  memo.set(ctx, result);
  return result;
}

export function check(repoRoot, ctx = createContext(repoRoot)) {
  return analyze(ctx).findings;
}

export function generate(repoRoot, ctx = createContext(repoRoot)) {
  const { reg } = analyze(ctx);
  if (!reg.terms || !reg.adapters || !reg.leafIds) return [];
  const drFile = decisionRecordFile(ctx, reg.terms.decisionRecord);
  let dr = null;
  try {
    dr = drFile ? ctx.readJson(drFile) : null;
  } catch {
    dr = null;
  }
  const outputs = [{ path: LABELS_TS, content: renderLabelsTs(reg.terms) }];
  if (dr) {
    outputs.push({ path: VOCABULARY_MD, content: renderVocabularyMd(reg.terms, reg.adapters, reg.leafIds, dr) });
    outputs.push({ path: CORRECTIONS_MD, content: renderCorrectionsMd(reg.terms, reg.leafIds, dr) });
  }
  return outputs;
}

export function summary(repoRoot, ctx = createContext(repoRoot)) {
  const { reg, coverage, revision } = analyze(ctx);
  const lines = [];
  const t = reg.terms;
  if (!t) return ['registry unreadable'];
  const terms = t.terms || [];
  const count = (v) => terms.filter((x) => x.visibility === v).length;
  lines.push(`registry revision ${t.revision} (vocabulary@${t.revision} = ${t.decisionRecord}@${t.revision}), ${t.compatibility}`);
  lines.push(`terms: ${terms.length} (${count('user-facing')} user-facing, ${count('inspection-only')} inspection-only, ${count('internal')} internal) in ${(t.categories || []).length} categories`);
  const adapters = reg.adapters?.adapters || [];
  const kinds = [...new Set(adapters.map((a) => a.kind))];
  lines.push(`adapters: ${adapters.length} (${kinds.map((k) => `${adapters.filter((a) => a.kind === k).length} ${k}`).join(', ')})`);
  const leaves = reg.leafIds?.leaves || [];
  const by = (s) => leaves.filter((l) => l.status === s).length;
  lines.push(`leaf IDs: ${by('filed')} filed, ${by('proposed')} proposed, ${by('rejected')} rejected; catalog pin sha256 ${reg.leafIds?.catalog?.sha256?.slice(0, 12)}... ${ctx.catalogPath ? 'checked against --catalog' : 'not checked (pass --catalog <capabilities.json>)'}`);
  if (coverage) {
    const c = coverage.cov;
    const live = c.collections.filter((x) => !x.historical).length;
    const viaAdapter = coverage.results.filter((r) => r.via === 'adapter').length;
    const viaLabel = coverage.results.filter((r) => r.via === 'label').length;
    lines.push(`coverage: ${c.collections.length} collections (${live} live, ${c.collections.length - live} historical), ${c.storedValues.length} stored values, ${c.apiRoutes.length} API routes, ${c.routeSegments.length} route segments, ${c.uiStrings.length} UI strings, ${c.appHeaders.length} AppHeader props at ${c.appHeaderCallSites} call sites, ${c.positioning.length} positioning lines; ${viaAdapter} names covered by adapters, ${viaLabel} by term labels`);
  }
  const drFile = decisionRecordFile(ctx, t.decisionRecord);
  let open = [];
  try {
    const dr = drFile ? ctx.readJson(drFile) : null;
    open = (dr?.decisions || []).filter((d) => d.status === 'ratified-here').map((d) => d.id);
    const scr = (dr?.specChangeRequests || []).map((s) => s.id);
    lines.push(`open ratified-here items: decisions ${open.join(', ') || 'none'}; terms ${terms.filter((x) => x.status === 'ratified-here').map((x) => x.id).join(', ') || 'none'}; spec-change requests ${scr.join(', ') || 'none'}`);
  } catch {
    lines.push('open ratified-here items: decision record unreadable');
  }
  const base = {
    none: 'base: none (--base none)',
    unavailable: `base: ${ctx.baseRef} unavailable`,
    absent: `base: ${ctx.baseRef} has no terms.json; this is the first revision`,
    unchanged: `base: unchanged since ${ctx.baseRef} (revision ${revision.baseRevision})`,
    changed: `base: revision ${t.revision} over ${ctx.baseRef}'s ${revision.baseRevision}`,
    unparseable: `base: terms.json at ${ctx.baseRef} is not valid JSON`,
  }[revision.base];
  lines.push(base);
  return lines;
}
