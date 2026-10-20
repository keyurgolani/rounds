// Checks for the product vocabulary registry (ROUNDS-01-L01, DR-0001).

import fs from 'node:fs';
import { canonical, finding, isTextPath, jsonLine, sha256 } from '../context.mjs';
import { validate } from '../json-schema.mjs';
import { LEAF_IDS_PATH, LEAF_REF_PATTERN, leafResolver } from '../leaf-ids.mjs';
import { extractCoverage, renderPositioning } from './coverage.mjs';

export const TERMS_PATH = 'contracts/vocabulary/terms.json';
export const TERMS_SCHEMA = 'contracts/vocabulary/terms.schema.json';
export const ADAPTERS_PATH = 'contracts/vocabulary/adapters.json';
export const ADAPTERS_SCHEMA = 'contracts/vocabulary/adapters.schema.json';
export const LEAF_IDS_SCHEMA = 'contracts/vocabulary/leaf-ids.schema.json';
export const DECISIONS_DIR = 'docs/decisions';

// Terms these checks require by ID: the five containment terms (G12) and the
// five privacy classes (spec 2142-2148).
export const REQUIRED_TERMS = [
  'legacy-artifact-snapshot', 'test-definition', 'harness-revision', 'artifact-renderer-contract', 'share-capability',
  'privacy-private', 'privacy-sensitive', 'privacy-third-party-personal', 'privacy-secret', 'privacy-share-projection',
];

// Paths the data-preserving cutover wording scan skips: fixtures that hold
// deliberate violations for the rule's own tests.
export const CUTOVER_SCAN_SKIP = ['scripts/conformance/test/fixtures/'];

const MATCH_KEYS = {
  collection: ['legacyName'],
  'stored-value': ['legacyName', 'field'],
  'api-route': ['legacyName'],
  'route-segment': ['legacyName', 'path'],
  'ui-string': ['legacyName', 'path'],
  'app-header': ['legacyName', 'path', 'prop'],
  positioning: ['legacyName', 'path'],
};
const IMPLICIT_KINDS = new Set(['ui-string', 'app-header']);

const norm = (s) => String(s).trim().replace(/\s+/g, ' ').toLowerCase();

function parseLines(spec) {
  const out = [];
  for (const part of String(spec || '').split(',')) {
    const [a, b] = part.split('-').map(Number);
    if (Number.isInteger(a)) out.push([a, Number.isInteger(b) ? b : a]);
  }
  return out;
}
const inLines = (spec, line) => parseLines(spec).some(([a, b]) => line >= a && line <= b);

function readJsonFile(ctx, rel, code, findings) {
  if (!ctx.exists(rel)) {
    findings.push(finding(code, rel, 1, `${rel} is missing`));
    return null;
  }
  try {
    return { text: ctx.read(rel), data: JSON.parse(ctx.read(rel)) };
  } catch (err) {
    findings.push(finding(code, rel, 1, `${rel} is not valid JSON: ${err.message}`));
    return null;
  }
}

function pointerParts(pointer) {
  return pointer.split('/').slice(1).map((p) => (/^\d+$/.test(p) ? Number(p) : p.replace(/~1/g, '/').replace(/~0/g, '~')));
}

function schemaFindings(ctx, file, text, data, schemaRel, mapCode) {
  const out = [];
  let schema;
  try {
    schema = JSON.parse(ctx.read(schemaRel));
  } catch (err) {
    return [finding('VOCAB_SHAPE_INVALID', schemaRel, 1, `${schemaRel} is missing or invalid: ${err.message}`)];
  }
  for (const err of validate(data, schema)) {
    const parts = pointerParts(err.pointer);
    out.push(finding(mapCode(err), file, jsonLine(text, parts), `${err.pointer || '/'} ${err.message}`));
  }
  return out;
}

function termsCode(err) {
  if (/^\/terms\/\d+\/id$/.test(err.pointer) && err.keyword === 'pattern') return 'VOCAB_TERM_ID_INVALID';
  if (/^\/terms\/\d+$/.test(err.pointer) && err.keyword === 'required' && err.property === 'owningLeaf') return 'VOCAB_NO_OWNING_LEAF';
  if (/^\/terms\/\d+\/label/.test(err.pointer)) return 'VOCAB_LABEL_INVALID';
  return 'VOCAB_SHAPE_INVALID';
}

// Loads and shape-checks the three registry files. Returns null data for a
// file that can't be parsed.
export function loadRegistry(ctx, findings) {
  const termsFile = readJsonFile(ctx, TERMS_PATH, 'VOCAB_SHAPE_INVALID', findings);
  const adaptersFile = readJsonFile(ctx, ADAPTERS_PATH, 'VOCAB_ADAPTER_INVALID', findings);
  const leafFile = readJsonFile(ctx, LEAF_IDS_PATH, 'VOCAB_LEAF_IDS_INVALID', findings);
  if (termsFile) findings.push(...schemaFindings(ctx, TERMS_PATH, termsFile.text, termsFile.data, TERMS_SCHEMA, termsCode));
  if (adaptersFile) findings.push(...schemaFindings(ctx, ADAPTERS_PATH, adaptersFile.text, adaptersFile.data, ADAPTERS_SCHEMA, () => 'VOCAB_ADAPTER_INVALID'));
  if (leafFile) findings.push(...schemaFindings(ctx, LEAF_IDS_PATH, leafFile.text, leafFile.data, LEAF_IDS_SCHEMA, () => 'VOCAB_LEAF_IDS_INVALID'));
  return {
    termsText: termsFile?.text || '',
    terms: termsFile?.data || null,
    adaptersText: adaptersFile?.text || '',
    adapters: adaptersFile?.data || null,
    leafIdsText: leafFile?.text || '',
    leafIds: leafFile?.data || null,
  };
}

// ------------------------------------------------------------------ leaf IDs

export function checkLeafIds(ctx, reg, findings) {
  const data = reg.leafIds;
  if (!data || !Array.isArray(data.leaves)) return;
  const at = (i) => jsonLine(reg.leafIdsText, ['leaves', i]);
  const seen = new Map();
  const issues = new Map();
  const filed = [];
  data.leaves.forEach((leaf, i) => {
    if (seen.has(leaf.id)) findings.push(finding('VOCAB_LEAF_IDS_INVALID', LEAF_IDS_PATH, at(i), `${leaf.id} is listed twice`));
    seen.set(leaf.id, leaf);
    if (leaf.issue !== null && leaf.issue !== undefined) {
      if (issues.has(leaf.issue)) findings.push(finding('VOCAB_LEAF_IDS_INVALID', LEAF_IDS_PATH, at(i), `issue #${leaf.issue} is listed twice`));
      issues.set(leaf.issue, leaf.id);
    }
    if (leaf.status === 'filed') filed.push({ leaf, i });
  });
  const count = data.catalog?.leafCount;
  if (filed.length !== count) {
    findings.push(finding('VOCAB_LEAF_IDS_INVALID', LEAF_IDS_PATH, 1, `${filed.length} filed leaves, but the catalog pin records ${count}`));
  }
  filed.forEach(({ leaf, i }, n) => {
    if (leaf.issue !== n + 1) findings.push(finding('VOCAB_LEAF_IDS_INVALID', LEAF_IDS_PATH, at(i), `filed leaf ${leaf.id} is issue #${leaf.issue}, expected #${n + 1} in catalog order`));
  });
  data.leaves.forEach((leaf, i) => {
    if (leaf.status === 'rejected' ? leaf.issue !== null || !leaf.foldedInto : !Number.isInteger(leaf.issue) || leaf.foldedInto !== undefined) {
      findings.push(finding('VOCAB_LEAF_IDS_INVALID', LEAF_IDS_PATH, at(i), `${leaf.id}: a rejected leaf has foldedInto and issue null; a filed or proposed one has an issue and no foldedInto`));
    }
    if (leaf.status === 'proposed' && !(leaf.issue > count)) {
      findings.push(finding('VOCAB_LEAF_IDS_INVALID', LEAF_IDS_PATH, at(i), `proposed leaf ${leaf.id} must have an issue number above the ${count} filed ones`));
    }
    if (leaf.status === 'rejected' && leaf.foldedInto) {
      const target = seen.get(leaf.foldedInto);
      if (!target || target.status === 'rejected') {
        findings.push(finding('VOCAB_LEAF_IDS_INVALID', LEAF_IDS_PATH, at(i), `${leaf.id} folds into ${leaf.foldedInto}, which is not a filed or proposed leaf`));
      }
    }
  });
  if (ctx.catalogPath) {
    let raw;
    try {
      raw = fs.readFileSync(ctx.catalogPath);
    } catch (err) {
      findings.push(finding('VOCAB_LEAF_IDS_PIN', LEAF_IDS_PATH, 1, `cannot read the catalog at ${ctx.catalogPath}: ${err.message}`));
      return;
    }
    const digest = sha256(raw);
    if (digest !== data.catalog.sha256) {
      findings.push(finding('VOCAB_LEAF_IDS_PIN', LEAF_IDS_PATH, jsonLine(reg.leafIdsText, ['catalog', 'sha256']), `catalog sha256 is ${digest}, the pin records ${data.catalog.sha256}; regenerate leaf-ids.json from the catalog`));
    }
    try {
      const catalog = JSON.parse(raw.toString('utf8'));
      const ids = [];
      for (const cap of catalog.capabilities || []) for (const l of cap.leaves || []) ids.push(Array.isArray(l) ? l[0] : l.id);
      const filedIds = filed.map(({ leaf }) => leaf.id);
      const first = ids.findIndex((id, n) => id !== filedIds[n]);
      if (ids.length !== filedIds.length || first !== -1) {
        findings.push(finding('VOCAB_LEAF_IDS_PIN', LEAF_IDS_PATH, 1, `filed leaves differ from the catalog${first === -1 ? '' : ` at #${first + 1} (${ids[first]} in the catalog, ${filedIds[first]} here)`}`));
      }
    } catch (err) {
      findings.push(finding('VOCAB_LEAF_IDS_PIN', LEAF_IDS_PATH, 1, `the catalog at ${ctx.catalogPath} is not valid JSON: ${err.message}`));
    }
  }
}

// --------------------------------------------------------------------- terms

const TOKEN = /[A-Za-z0-9_-]{20,}/g;
const SHARE_URL = /\/r\/[A-Za-z0-9_-]+/;
const EMAIL = /[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})/g;

export function secretShapes(text, knownIds) {
  const problems = [];
  for (const m of String(text).matchAll(TOKEN)) {
    const token = m[0];
    if (/[A-Za-z]/.test(token) && /\d/.test(token) && !knownIds.has(token)) problems.push(`bearer-shaped token "${token.slice(0, 6)}..."`);
  }
  if (SHARE_URL.test(text)) problems.push('a /r/<token> share URL');
  for (const m of String(text).matchAll(EMAIL)) {
    const domain = m[1].toLowerCase();
    if (domain !== 'example.com' && !domain.endsWith('.example.com')) problems.push(`an email address at ${domain}`);
  }
  return problems;
}

export function labelForms(term) {
  const forms = [];
  for (const o of term.label?.options || []) {
    forms.push(o.singular);
    if (o.plural !== o.singular) forms.push(o.plural);
  }
  return forms;
}

function termNames(term) {
  return [term.term, ...(term.aliases || []), ...labelForms(term)];
}

export function checkTerms(ctx, reg, findings, resolveLeaf) {
  const data = reg.terms;
  if (!data || !Array.isArray(data.terms)) return;
  const text = reg.termsText;
  const terms = data.terms;
  const at = (i, ...rest) => jsonLine(text, ['terms', i, ...rest]);
  const push = (code, line, message) => findings.push(finding(code, TERMS_PATH, line, message));
  const byId = new Map();
  terms.forEach((t, i) => {
    if (byId.has(t.id)) push('VOCAB_DUPLICATE_ID', at(i, 'id'), `term ID "${t.id}" is defined twice`);
    else byId.set(t.id, t);
  });

  const categories = new Set((data.categories || []).map((c) => c.id));
  const namespaces = new Set((data.namespaces || []).map((n) => n.id));
  const perCategory = new Map([...categories].map((c) => [c, 0]));
  const knownIds = new Set([...byId.keys(), ...(reg.leafIds?.leaves || []).map((l) => l.id)]);
  const leafRef = (ref, line, what) => {
    const r = resolveLeaf(ref);
    if (!r.ok) push('VOCAB_UNRESOLVED_REF', line, `${what}: ${r.reason}`);
  };

  terms.forEach((t, i) => {
    if (!categories.has(t.category)) push('VOCAB_SHAPE_INVALID', at(i, 'category'), `${t.id}: category "${t.category}" is not one of the 15 scope categories`);
    else perCategory.set(t.category, perCategory.get(t.category) + 1);
    if (!namespaces.has(t.namespace)) push('VOCAB_SHAPE_INVALID', at(i, 'namespace'), `${t.id}: namespace "${t.namespace}" is not declared`);
    if (typeof t.owningLeaf === 'string') leafRef(t.owningLeaf, at(i, 'owningLeaf'), `${t.id} owningLeaf`);
    for (const ref of t.definedBy || []) {
      if (LEAF_REF_PATTERN.test(ref)) leafRef(ref, at(i, 'definedBy'), `${t.id} definedBy`);
      else if (ref.includes('/')) {
        if (!ctx.exists(ref)) push('VOCAB_UNRESOLVED_REF', at(i, 'definedBy'), `${t.id} definedBy: ${ref} does not exist`);
      } else if (!/^spec \d/.test(ref)) push('VOCAB_UNRESOLVED_REF', at(i, 'definedBy'), `${t.id} definedBy: "${ref}" is not a leaf ID, repository path, or spec range`);
    }
    if (!t.definition && !(Array.isArray(t.definedBy) && t.definedBy.length)) push('VOCAB_TERM_UNDEFINED', at(i), `${t.id}: needs a definition or definedBy`);
    const label = t.label;
    if (t.visibility === 'user-facing' && !label) push('VOCAB_LABEL_INVALID', at(i, 'label'), `${t.id}: a user-facing term needs a label`);
    if (t.visibility && t.visibility !== 'user-facing' && label) push('VOCAB_LABEL_INVALID', at(i, 'label'), `${t.id}: ${t.visibility} terms have no label`);
    if (label && (label.axis === 'stage' || label.axis === 'submission-state') && !Array.isArray(label.mappingOwner)) {
      push('VOCAB_LABEL_INVALID', at(i, 'label', 'mappingOwner'), `${t.id}: a ${label.axis} label needs a mapping owner`);
    }
    if (label && Array.isArray(label.options)) {
      const keys = label.options.map((o) => o.key);
      if (new Set(keys).size !== keys.length) push('VOCAB_LABEL_INVALID', at(i, 'label'), `${t.id}: label option keys repeat`);
      if (!keys.includes(label.default)) push('VOCAB_LABEL_INVALID', at(i, 'label', 'default'), `${t.id}: default "${label.default}" is not a label option`);
      if (label.axis === 'none' && label.mappingOwner !== null) push('VOCAB_LABEL_INVALID', at(i, 'label', 'mappingOwner'), `${t.id}: axis none takes no mapping owner`);
      if (label.axis !== 'none' && label.mappingOwner === null && label.default !== keys[0] && label.default !== keys[keys.length - 1]) {
        push('VOCAB_LABEL_INVALID', at(i, 'label', 'default'), `${t.id}: without a mapping owner the default is the first option or the catch-all`);
      }
      for (const ref of label.mappingOwner || []) leafRef(ref, at(i, 'label', 'mappingOwner'), `${t.id} label mappingOwner`);
    }
    for (const example of t.examples || []) {
      const problems = secretShapes(example, knownIds);
      if (problems.length) push('VOCAB_SECRET_EXAMPLE', at(i, 'examples'), `${t.id}: example holds ${problems.join(', ')}; examples must be synthetic`);
    }
  });
  for (const [cat, n] of perCategory) {
    if (n === 0) push('VOCAB_CATEGORY_EMPTY', jsonLine(text, ['categories']), `scope category "${cat}" has no term`);
  }
  for (const id of REQUIRED_TERMS) {
    if (!byId.has(id)) push('VOCAB_REQUIRED_TERM_MISSING', 1, `required term "${id}" is missing`);
  }
  for (const id of data.coreConcepts?.terms || []) {
    const t = byId.get(id);
    if (!t || t.namespace !== 'platform') push('VOCAB_REQUIRED_TERM_MISSING', jsonLine(text, ['coreConcepts']), `core concept "${id}" (${data.coreConcepts.source}) is not a platform term`);
  }
  for (const entry of data.platformCore?.names || []) {
    for (const id of entry.terms) if (!byId.has(id)) push('VOCAB_REQUIRED_TERM_MISSING', jsonLine(text, ['platformCore']), `platform core name "${entry.name}" points at unknown term "${id}"`);
  }
  for (const ns of data.namespaces || []) if (ns.owningLeaf) leafRef(ns.owningLeaf, jsonLine(text, ['namespaces']), `namespace ${ns.id} owningLeaf`);

  // Duplicate label and option pairs outside sharedLabels.
  const shared = [];
  for (const entry of data.sharedLabels || []) {
    const texts = new Set();
    for (const id of entry.terms) {
      const t = byId.get(id);
      const opt = t?.label?.options?.find((o) => o.singular === entry.label);
      if (!opt) push('VOCAB_SHARED_LABEL_INVALID', jsonLine(text, ['sharedLabels']), `sharedLabels "${entry.label}": term "${id}" has no option with that label`);
      else { texts.add(norm(opt.singular)); texts.add(norm(opt.plural)); }
    }
    shared.push({ entry, texts, terms: new Set(entry.terms) });
  }
  const labelOwners = new Map();
  terms.forEach((t, i) => {
    for (const form of new Set(labelForms(t).map(norm))) {
      if (!labelOwners.has(form)) labelOwners.set(form, []);
      labelOwners.get(form).push({ id: t.id, i });
    }
  });
  for (const [form, owners] of labelOwners) {
    const ids = [...new Set(owners.map((o) => o.id))];
    if (ids.length < 2) continue;
    const covered = shared.some((s) => s.texts.has(form) && ids.every((id) => s.terms.has(id)));
    if (!covered) push('VOCAB_DUPLICATE_LABEL', at(owners[1].i, 'label'), `label "${form}" is used by ${ids.join(' and ')} and is not in sharedLabels`);
  }

  // Aliases: one term per alias, and never a canonical term name.
  const canonicalNames = new Map(terms.map((t) => [norm(t.term), t.id]));
  const aliasOwners = new Map();
  terms.forEach((t, i) => {
    for (const alias of t.aliases || []) {
      const key = norm(alias);
      if (canonicalNames.has(key)) push('VOCAB_ALIAS_SHADOWS_TERM', at(i, 'aliases'), `${t.id}: alias "${alias}" equals the canonical term of ${canonicalNames.get(key)}`);
      if (!aliasOwners.has(key)) aliasOwners.set(key, []);
      aliasOwners.get(key).push({ id: t.id, i, alias });
    }
  });
  for (const [, owners] of aliasOwners) {
    const ids = [...new Set(owners.map((o) => o.id))];
    if (ids.length > 1) push('VOCAB_ALIAS_AMBIGUOUS', at(owners[1].i, 'aliases'), `alias "${owners[0].alias}" resolves to ${ids.join(' and ')}`);
  }

  // Packs cannot redefine platform terms (spec 815-840).
  const platformNames = new Map();
  for (const t of terms) if (t.namespace === 'platform') for (const n of termNames(t)) platformNames.set(norm(n), t.id);
  for (const entry of data.platformCore?.names || []) platformNames.set(norm(entry.name), `platform core "${entry.name}"`);
  terms.forEach((t, i) => {
    if (t.namespace === 'platform') return;
    for (const n of new Set(termNames(t))) {
      const hit = platformNames.get(norm(n));
      if (hit) push('VOCAB_PACK_REDEFINES_PLATFORM', at(i), `${t.namespace} term ${t.id} uses "${n}", which is the platform name of ${hit}`);
    }
  });

  // Usage rules (G3, G4, G6, G7) on label options.
  for (const rule of data.usageRules || []) {
    let re;
    try {
      re = new RegExp(rule.pattern, 'i');
    } catch (err) {
      push('VOCAB_SHAPE_INVALID', jsonLine(text, ['usageRules']), `usage rule ${rule.id}: bad pattern (${err.message})`);
      continue;
    }
    for (const id of rule.allowedTerms) if (!byId.has(id)) push('VOCAB_SHAPE_INVALID', jsonLine(text, ['usageRules']), `usage rule ${rule.id}: unknown term "${id}"`);
    terms.forEach((t, i) => {
      if (rule.allowedTerms.includes(t.id)) return;
      for (const form of labelForms(t)) {
        if (re.test(form)) push('VOCAB_RESERVED_LABEL', at(i, 'label'), `${t.id}: label "${form}" breaks ${rule.decision}: ${rule.rule}`);
      }
    });
  }

  // Disposition catalog words map to item values (G10).
  const itemValues = new Set((data.dispositions?.item?.values || []).map((v) => v.value));
  for (const w of data.dispositions?.item?.catalogWords || []) {
    if (!itemValues.has(w.value)) push('VOCAB_SHAPE_INVALID', jsonLine(text, ['dispositions']), `catalog word "${w.word}" maps to unknown item disposition "${w.value}"`);
  }
  return byId;
}

// ------------------------------------------------------------------ adapters

export function adapterKey(a) {
  return [a.kind, a.source?.path, a.legacyName, a.field || '', a.prop || ''].join('\u0000');
}

export function checkAdapters(ctx, reg, findings, resolveLeaf, byId) {
  const list = reg.adapters?.adapters;
  if (!Array.isArray(list)) return;
  const at = (i, ...rest) => jsonLine(reg.adaptersText, ['adapters', i, ...rest]);
  const push = (code, line, message) => findings.push(finding(code, ADAPTERS_PATH, line, message));
  const seen = new Set();
  list.forEach((a, i) => {
    const key = adapterKey(a);
    if (seen.has(key)) push('VOCAB_DUPLICATE_ADAPTER', at(i), `adapter for ${a.kind} "${a.legacyName}" at ${a.source?.path} is listed twice`);
    seen.add(key);
    if ((typeof a.termId === 'string') === (typeof a.decidedBy === 'string')) push('VOCAB_ADAPTER_INVALID', at(i), `adapter "${a.legacyName}" needs exactly one of termId and decidedBy`);
    if (a.kind === 'stored-value' && !a.field) push('VOCAB_ADAPTER_INVALID', at(i), `stored-value adapter "${a.legacyName}" needs field`);
    if (a.kind === 'app-header' && !a.prop) push('VOCAB_ADAPTER_INVALID', at(i), `app-header adapter "${a.legacyName}" needs prop`);
    if (a.kind === 'term' ? !a.source?.revision : !a.source?.lines) {
      push('VOCAB_ADAPTER_INVALID', at(i, 'source'), `adapter "${a.legacyName}" source needs ${a.kind === 'term' ? 'the revision that removed it' : 'lines'}`);
    }
    if (a.termId && byId && !byId.has(a.termId)) push('VOCAB_UNRESOLVED_REF', at(i, 'termId'), `adapter "${a.legacyName}": unknown term "${a.termId}"`);
    for (const field of ['decidedBy', 'retiringLeaf']) {
      if (typeof a[field] !== 'string') continue;
      const r = resolveLeaf(a[field]);
      if (!r.ok) push('VOCAB_UNRESOLVED_REF', at(i, field), `adapter "${a.legacyName}" ${field}: ${r.reason}`);
    }
    if (a.kind !== 'term' && a.source?.path && !ctx.exists(a.source.path)) {
      push('VOCAB_ADAPTER_STALE', at(i, 'source'), `adapter "${a.legacyName}": ${a.source.path} no longer exists; remove the entry or fix its source`);
    }
    if ((a.kind === 'field' || a.kind === 'doc') && a.source?.path && ctx.exists(a.source.path)) {
      const needle = a.kind === 'field' ? a.legacyName.split('.').pop() : a.legacyName;
      if (!ctx.read(a.source.path).includes(needle)) push('VOCAB_ADAPTER_STALE', at(i), `adapter "${a.legacyName}": ${a.source.path} no longer mentions it; remove the entry`);
    }
  });
}

// ------------------------------------------------------------------ coverage

function adapterMatches(a, item) {
  if (a.kind !== item.kind) return false;
  return MATCH_KEYS[item.kind].every((k) => {
    if (k === 'legacyName') return a.legacyName === item.name;
    if (k === 'path') return a.source?.path === item.path;
    return a[k] === item[k];
  });
}

export function analyzeCoverage(ctx, reg, byId) {
  const adapters = reg.adapters?.adapters || [];
  const resolveNonLiteral = (ev) => {
    const names = adapters.filter((a) => a.kind === 'collection' && a.source?.path === ev.path && inLines(a.source.lines, ev.line)).map((a) => a.legacyName);
    return names.length ? names : null;
  };
  const cov = extractCoverage(ctx, resolveNonLiteral);
  const labelTexts = new Set();
  for (const t of byId?.values() || []) if (t.visibility === 'user-facing') for (const f of labelForms(t)) labelTexts.add(f);
  const items = [...cov.collections, ...cov.storedValues, ...cov.apiRoutes, ...cov.routeSegments, ...cov.uiStrings, ...cov.appHeaders];
  const matched = new Set();
  const results = [];
  for (const it of items) {
    const a = adapters.find((x) => adapterMatches(x, it));
    if (a) {
      matched.add(a);
      results.push({ item: it, via: 'adapter', adapter: a });
    } else if (IMPLICIT_KINDS.has(it.kind) && labelTexts.has(it.name)) {
      results.push({ item: it, via: 'label' });
    } else {
      results.push({ item: it, via: null });
    }
  }
  const positioning = cov.positioning.map((it) => {
    const expected = renderPositioning(it.template, reg.terms?.positioning || { statement: '', title: '' });
    const a = adapters.find((x) => adapterMatches(x, it));
    if (a) matched.add(a);
    return { item: it, expected, adapter: a || null, current: it.name === expected.trim() };
  });
  return { cov, results, positioning, matched };
}

export function checkCoverage(ctx, reg, findings, byId) {
  const analysis = analyzeCoverage(ctx, reg, byId);
  const { cov, results, positioning, matched } = analysis;
  for (const ev of cov.unresolvedCollections) {
    findings.push(finding('VOCAB_NONLITERAL_COLLECTION', ev.path, ev.line, `${ev.type === 'create-nonliteral' ? 'new Collection' : 'deleteCollection'} with a non-literal name has no adapter entry; add one collection entry per name with source.lines covering line ${ev.line}`));
  }
  for (const r of results) {
    if (r.via) continue;
    const it = r.item;
    const what = it.kind === 'stored-value' ? `${it.field} value "${it.name}"` : it.kind === 'app-header' ? `AppHeader ${it.prop} "${it.name}"` : `${it.kind} "${it.name}"`;
    findings.push(finding('VOCAB_UNCOVERED_NAME', it.path, it.line, `${what} maps to no term label or adapter entry. Add an adapter entry (termId or decidedBy, targetLabel, retiringLeaf) to ${ADAPTERS_PATH}; never loosen the rule.`));
  }
  for (const p of positioning) {
    if (p.current) continue;
    if (p.adapter) continue;
    findings.push(finding('VOCAB_POSITIONING_STALE', p.item.path, p.item.line, `positioning line differs from terms.json positioning ("${p.expected.slice(0, 60)}...") and from its adapter entry`));
  }
  const list = reg.adapters?.adapters || [];
  list.forEach((a, i) => {
    if (!MATCH_KEYS[a.kind] || matched.has(a)) return;
    findings.push(finding('VOCAB_ADAPTER_STALE', ADAPTERS_PATH, jsonLine(reg.adaptersText, ['adapters', i]), `adapter for ${a.kind} "${a.legacyName}" matches nothing in ${a.source?.path}; its name is gone, so remove the entry (retiring leaf ${a.retiringLeaf})`));
  });
  return analysis;
}

// ------------------------------------------------- data-preserving cutover

const CUTOVER = /\bclean(?:[\s*#/]|-)+cut-?over\b/gi;
const QUALIFIER = /data[\s-]*preserving[\s,"'`*_]*$/i;

export function cutoverMatches(text) {
  const out = [];
  for (const m of text.matchAll(CUTOVER)) {
    const before = text.slice(Math.max(0, m.index - 40), m.index);
    if (QUALIFIER.test(before)) continue;
    let line = 1;
    for (let k = 0; k < m.index; k++) if (text.charCodeAt(k) === 10) line++;
    out.push({ line, text: m[0] });
  }
  return out;
}

export function checkCutover(ctx, reg, findings) {
  const allow = reg.terms?.cutover?.allowlist || [];
  const allowed = new Set(allow.map((a) => `${a.path}:${a.line}`));
  const used = new Set();
  for (const file of ctx.files()) {
    if (!isTextPath(file) || CUTOVER_SCAN_SKIP.some((p) => file.startsWith(p))) continue;
    let text;
    try {
      text = ctx.read(file);
    } catch {
      continue;
    }
    for (const m of cutoverMatches(text)) {
      const key = `${file}:${m.line}`;
      if (allowed.has(key)) { used.add(key); continue; }
      findings.push(finding('VOCAB_CUTOVER_UNQUALIFIED', file, m.line, `"${m.text}" without "data-preserving": the approved term is data-preserving clean cutover (spec 2637-2647, DR-0001 G11)`));
    }
  }
  allow.forEach((a, i) => {
    if (!used.has(`${a.path}:${a.line}`)) {
      findings.push(finding('VOCAB_CUTOVER_ALLOWLIST_STALE', TERMS_PATH, jsonLine(reg.termsText, ['cutover', 'allowlist', i]), `allowlisted ${a.path}:${a.line} no longer holds the unqualified phrase; remove the entry`));
    }
  });
}

// ------------------------------------------------------------------ revisions

export function decisionRecordFile(ctx, id) {
  return ctx.files().find((f) => f.startsWith(`${DECISIONS_DIR}/${id}-`) && f.endsWith('.json')) || null;
}

function registryNames(data) {
  const names = new Map();
  for (const t of data.terms || []) {
    names.set(`term:${norm(t.term)}`, { id: t.id, name: t.term });
    for (const a of t.aliases || []) names.set(`alias:${norm(a)}`, { id: t.id, name: a });
    for (const o of t.label?.options || []) names.set(`label:${t.id}:${o.key}:${norm(o.singular)}`, { id: t.id, name: o.singular });
  }
  return names;
}

export function compareWithBase(current, base) {
  const strip = (d) => {
    const { revision, compatibility, ...rest } = d;
    return canonical(rest);
  };
  const changed = strip(current) !== strip(base);
  const baseNames = registryNames(base);
  const curNames = registryNames(current);
  const removed = [...baseNames.entries()].filter(([k]) => !curNames.has(k)).map(([, v]) => v);
  const curById = new Map((current.terms || []).map((t) => [t.id, t]));
  for (const t of base.terms || []) {
    if (!curById.has(t.id)) removed.push({ id: t.id, name: t.term, idRemoved: true });
  }
  const visibility = (base.terms || []).filter((t) => curById.has(t.id) && curById.get(t.id).visibility !== t.visibility).map((t) => t.id);
  return { changed, removed, visibility };
}

export function checkRevision(ctx, reg, findings) {
  const data = reg.terms;
  if (!data) return { base: 'unavailable' };
  const drFile = decisionRecordFile(ctx, data.decisionRecord);
  if (!drFile) {
    findings.push(finding('VOCAB_REVISION_MISMATCH', TERMS_PATH, jsonLine(reg.termsText, ['decisionRecord']), `no ${DECISIONS_DIR}/${data.decisionRecord}-*.json for this registry`));
  } else {
    try {
      const dr = ctx.readJson(drFile);
      if (dr.revision !== data.revision || dr.compatibility !== data.compatibility) {
        findings.push(finding('VOCAB_REVISION_MISMATCH', drFile, jsonLine(ctx.read(drFile), ['revision']), `${dr.id}@${dr.revision} (${dr.compatibility}) must match terms.json revision ${data.revision} (${data.compatibility}); they share one counter`));
      }
    } catch {
      // decision-records reports an unreadable record.
    }
  }
  const base = ctx.readBase(TERMS_PATH);
  if (!base.ok) {
    if (ctx.baseRef === 'none') return { base: 'none' };
    findings.push(finding('VOCAB_BASE_UNAVAILABLE', TERMS_PATH, 1, `cannot read terms.json at ${ctx.baseRef} (${base.reason}); fetch it (CI checks out with fetch-depth 0) or run with --base none locally`));
    return { base: 'unavailable' };
  }
  if (base.content === null) return { base: 'absent' };
  let prev;
  try {
    prev = JSON.parse(base.content);
  } catch {
    return { base: 'unparseable' };
  }
  const diff = compareWithBase(data, prev);
  if (!diff.changed) return { base: 'unchanged', baseRevision: prev.revision };
  const line = jsonLine(reg.termsText, ['revision']);
  if (!(data.revision > prev.revision)) {
    findings.push(finding('VOCAB_REVISION_NOT_BUMPED', TERMS_PATH, line, `terms.json changed since ${ctx.baseRef} but keeps revision ${data.revision} (${data.compatibility}); raise revision above ${prev.revision} in terms.json and ${data.decisionRecord}`));
  }
  if ((diff.removed.length || diff.visibility.length) && data.compatibility !== 'breaking') {
    findings.push(finding('VOCAB_COMPATIBILITY_UNDECLARED', TERMS_PATH, jsonLine(reg.termsText, ['compatibility']), `revision removes or changes ${[...diff.removed.map((r) => `"${r.name}"`), ...diff.visibility.map((v) => `${v} visibility`)].join(', ')} but is marked ${data.compatibility}; mark it breaking`));
  }
  const termAdapters = new Set((reg.adapters?.adapters || []).filter((a) => a.kind === 'term').map((a) => norm(a.legacyName)));
  const currentNames = new Set([...registryNames(data).values()].map((v) => norm(v.name)));
  for (const r of diff.removed) {
    if (currentNames.has(norm(r.name))) continue; // still a name, e.g. moved to another term
    if (!termAdapters.has(norm(r.name))) {
      findings.push(finding('VOCAB_REMOVED_TERM_UNADAPTED', ADAPTERS_PATH, 1, `"${r.name}" (was ${r.id}) is removed at revision ${data.revision}; keep a term adapter entry for it`));
    }
  }
  return { base: 'changed', baseRevision: prev.revision, diff };
}

export { leafResolver };
