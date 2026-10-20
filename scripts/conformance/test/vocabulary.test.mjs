import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { after, describe, it } from 'node:test';
import { createContext } from '../lib/context.mjs';
import { leafResolver } from '../lib/leaf-ids.mjs';
import { extractCoverage } from '../lib/vocabulary/coverage.mjs';
import { analyzeCoverage, cutoverMatches, loadRegistry, secretShapes } from '../lib/vocabulary/registry.mjs';
import * as vocabulary from '../rules/vocabulary.mjs';
import { FIXTURES, REPO_ROOT, cleanup, codes, ctxFor, editJson, editText, fixture, readJson, tempDir, writeJson } from './helpers.mjs';

const TERMS = 'contracts/vocabulary/terms.json';
const ADAPTERS = 'contracts/vocabulary/adapters.json';
const LEAF_IDS = 'contracts/vocabulary/leaf-ids.json';
const DR = 'docs/decisions/DR-0001-product-vocabulary.json';

after(cleanup);

const run = (dir, options) => vocabulary.check(dir, ctxFor(dir, options));
const editTerm = (dir, id, fn) => editJson(dir, TERMS, (d) => { fn(d.terms.find((t) => t.id === id), d); });
const only = (findings, code) => assert.deepEqual(codes(findings), [code], JSON.stringify(findings, null, 2));

describe('vocabulary: repository', () => {
  it('passes on the repository', () => {
    const findings = vocabulary.check(REPO_ROOT, createContext(REPO_ROOT, { base: { files: {} } }));
    assert.deepEqual(findings, []);
  });

  it('passes on an unmodified fixture copy', () => {
    assert.deepEqual(run(fixture()), []);
  });
});

describe('vocabulary: contract shape and collisions', () => {
  it('terms.json, adapters.json, and leaf-ids.json pass their schemas', () => {
    const findings = [];
    loadRegistry(createContext(REPO_ROOT, { base: 'none' }), findings);
    assert.deepEqual(findings, []);
  });

  it('rejects a duplicate term ID', () => {
    only(run(fixture((dir) => editJson(dir, TERMS, (d) => { d.terms.push({ ...d.terms.find((t) => t.id === 'offer') }); }))), 'VOCAB_DUPLICATE_ID');
  });

  it('rejects a duplicate label and option pair outside sharedLabels', () => {
    only(run(fixture((dir) => editTerm(dir, 'skill', (t) => { t.label.options[1].singular = 'Story'; }))), 'VOCAB_DUPLICATE_LABEL');
  });

  it('allows the two labels sharedLabels lists and rejects one it no longer lists', () => {
    only(run(fixture((dir) => editJson(dir, TERMS, (d) => { d.sharedLabels = d.sharedLabels.filter((s) => s.label !== 'Role'); }))), 'VOCAB_DUPLICATE_LABEL');
  });

  it('rejects an alias that resolves to two terms', () => {
    only(run(fixture((dir) => editTerm(dir, 'recommendation', (t) => { t.aliases.push('Task'); }))), 'VOCAB_ALIAS_AMBIGUOUS');
  });

  it('rejects an alias that equals a canonical term', () => {
    only(run(fixture((dir) => editTerm(dir, 'pursuit', (t) => { t.aliases.push('Offer'); }))), 'VOCAB_ALIAS_SHADOWS_TERM');
  });

  it('rejects a pack term that equals a platform one', () => {
    only(run(fixture((dir) => editTerm(dir, 'track-coding', (t) => { t.aliases.push('Proposed change'); }))), 'VOCAB_PACK_REDEFINES_PLATFORM');
    only(run(fixture((dir) => editTerm(dir, 'track-behavioral', (t) => { t.term = 'Revision'; }))), 'VOCAB_PACK_REDEFINES_PLATFORM');
  });

  it('rejects a term without owningLeaf', () => {
    only(run(fixture((dir) => editTerm(dir, 'calendar-provider', (t) => { delete t.owningLeaf; }))), 'VOCAB_NO_OWNING_LEAF');
  });

  it('rejects a term with neither definition nor definedBy', () => {
    only(run(fixture((dir) => editTerm(dir, 'calendar-provider', (t) => { delete t.definition; }))), 'VOCAB_TERM_UNDEFINED');
  });

  it('rejects a non-kebab term ID and accepts kebab ones', () => {
    only(run(fixture((dir) => editTerm(dir, 'calendar-provider', (t) => { t.id = 'Calendar_Provider'; }))), 'VOCAB_TERM_ID_INVALID');
    const terms = readJson(REPO_ROOT, TERMS).terms;
    for (const t of terms) assert.match(t.id, /^[a-z][a-z0-9]*(-[a-z0-9]+)*$/);
  });

  it('rejects a reserved label', () => {
    only(run(fixture((dir) => editTerm(dir, 'calendar-provider', (t) => { t.label.options[0].singular = 'Provider'; }))), 'VOCAB_RESERVED_LABEL');
    only(run(fixture((dir) => editTerm(dir, 'account', (t) => { t.label.options[0].singular = 'Profile'; }))), 'VOCAB_RESERVED_LABEL');
    const attempt = run(fixture((dir) => editTerm(dir, 'execution-attempt', (t) => {
      t.visibility = 'user-facing';
      t.label = { axis: 'none', options: [{ key: 'attempt', singular: 'Attempt', plural: 'Attempts' }], default: 'attempt', mappingOwner: null, basis: 'test' };
    })));
    assert.deepEqual(codes(attempt), ['VOCAB_DUPLICATE_LABEL', 'VOCAB_RESERVED_LABEL']);
  });

  it('rejects a label on a non-user-facing term and a user-facing term without one', () => {
    only(run(fixture((dir) => editTerm(dir, 'domain-event', (t) => { t.label = { axis: 'none', options: [{ key: 'event', singular: 'Event', plural: 'Events' }], default: 'event', mappingOwner: null, basis: 'test' }; }))), 'VOCAB_LABEL_INVALID');
    only(run(fixture((dir) => editTerm(dir, 'calendar-provider', (t) => { t.label = null; }))), 'VOCAB_LABEL_INVALID');
    only(run(fixture((dir) => editTerm(dir, 'pursuit', (t) => { t.label.mappingOwner = null; t.label.default = 'opportunity'; }))), 'VOCAB_LABEL_INVALID');
  });
});

describe('vocabulary: leaf references', () => {
  it('rejects an unknown leaf ID', () => {
    const findings = run(fixture((dir) => editTerm(dir, 'calendar-provider', (t) => { t.owningLeaf = 'ROUNDS-99-L01'; })));
    only(findings, 'VOCAB_UNRESOLVED_REF');
  });

  it('rejects a rejected leaf ID and names its fold target', () => {
    const findings = run(fixture((dir) => editTerm(dir, 'calendar-provider', (t) => { t.owningLeaf = 'ROUNDS-24-L05'; })));
    only(findings, 'VOCAB_UNRESOLVED_REF');
    assert.match(findings[0].message, /folded into ROUNDS-21-L02/);
  });

  it('resolves a stage reference on its leaf part', () => {
    const resolve = leafResolver(readJson(REPO_ROOT, LEAF_IDS));
    assert.equal(resolve('ROUNDS-00A-L01/S3').ok, true);
    assert.equal(resolve('ROUNDS-32-L10/SB.3').ok, true);
    assert.equal(resolve('ROUNDS-24-L05/S1').ok, false);
    assert.equal(resolve('ROUNDS-99-L01/S1').ok, false);
    assert.deepEqual(run(fixture((dir) => editTerm(dir, 'calendar-provider', (t) => { t.owningLeaf = 'ROUNDS-22-L02/S1'; }))), []);
  });

  it('rejects an unknown or rejected leaf in an adapter', () => {
    only(run(fixture((dir) => editJson(dir, ADAPTERS, (d) => { d.adapters[0].retiringLeaf = 'ROUNDS-26-L05'; }))), 'VOCAB_UNRESOLVED_REF');
  });

  it('rejects an adapter with both termId and decidedBy, or missing its kind-specific field', () => {
    only(run(fixture((dir) => editJson(dir, ADAPTERS, (d) => { d.adapters[0].decidedBy = 'ROUNDS-28-L01'; }))), 'VOCAB_ADAPTER_INVALID');
    only(run(fixture((dir) => editJson(dir, ADAPTERS, (d) => { delete d.adapters.find((a) => a.kind === 'collection').source.lines; }))), 'VOCAB_ADAPTER_INVALID');
  });
});

describe('vocabulary: leaf-ids.json', () => {
  const leafIds = readJson(REPO_ROOT, LEAF_IDS);

  it('holds the 176 filed leaves in catalog order, six proposals, and five rejected ones with fold targets', () => {
    const filed = leafIds.leaves.filter((l) => l.status === 'filed');
    assert.equal(filed.length, 176);
    filed.forEach((l, i) => assert.equal(l.issue, i + 1));
    assert.equal(filed[0].id, 'ROUNDS-00A-L01');
    assert.equal(filed[175].id, 'ROUNDS-34-L07');
    assert.deepEqual(leafIds.leaves.filter((l) => l.status === 'proposed').map((l) => [l.issue, l.id]), [
      [177, 'ROUNDS-00B-L07'], [178, 'ROUNDS-03-L04'], [179, 'ROUNDS-14-L06'], [180, 'ROUNDS-14-L07'], [181, 'ROUNDS-19-L05'], [182, 'ROUNDS-34-L08'],
    ]);
    assert.deepEqual(leafIds.leaves.filter((l) => l.status === 'rejected').map((l) => [l.id, l.foldedInto]), [
      ['ROUNDS-00A-L09', 'ROUNDS-00A-L01'], ['ROUNDS-04-L05', 'ROUNDS-33-L04'], ['ROUNDS-14-L08', 'ROUNDS-14-L02'], ['ROUNDS-24-L05', 'ROUNDS-21-L02'], ['ROUNDS-26-L05', 'ROUNDS-33-L04'],
    ]);
  });

  it('rejects a missing filed leaf and a bad fold target', () => {
    only(run(fixture((dir) => editJson(dir, LEAF_IDS, (d) => { d.leaves = d.leaves.filter((l) => l.id !== 'ROUNDS-34-L07'); }))), 'VOCAB_LEAF_IDS_INVALID');
    only(run(fixture((dir) => editJson(dir, LEAF_IDS, (d) => { d.leaves.find((l) => l.id === 'ROUNDS-24-L05').foldedInto = 'ROUNDS-99-L09'; }))), 'VOCAB_LEAF_IDS_INVALID');
    only(run(fixture((dir) => editJson(dir, LEAF_IDS, (d) => { d.leaves.find((l) => l.id === 'ROUNDS-24-L05').issue = 190; }))), 'VOCAB_LEAF_IDS_INVALID');
  });

  it('checks the catalog pin when a catalog is given', () => {
    const dir = fixture();
    const ids = leafIds.leaves.filter((l) => l.status === 'filed').map((l) => [l.id, 'title']);
    const same = path.join(tempDir(), 'capabilities.json');
    fs.writeFileSync(same, JSON.stringify({ capabilities: [{ id: 'X', leaves: ids }] }));
    const sameFindings = run(dir, { catalogPath: same });
    only(sameFindings, 'VOCAB_LEAF_IDS_PIN');
    assert.equal(sameFindings.length, 1, 'only the digest differs');
    const swapped = path.join(tempDir(), 'capabilities.json');
    const reordered = [...ids];
    [reordered[0], reordered[1]] = [reordered[1], reordered[0]];
    fs.writeFileSync(swapped, JSON.stringify({ capabilities: [{ id: 'X', leaves: reordered }] }));
    const swappedFindings = run(dir, { catalogPath: swapped });
    assert.equal(swappedFindings.length, 2);
    assert.match(swappedFindings[1].message, /differ from the catalog at #1/);
  });
});

describe('vocabulary: coverage set (schema)', () => {
  const ctx = createContext(REPO_ROOT, { base: 'none' });
  const reg = loadRegistry(ctx, []);
  const byId = new Map(reg.terms.terms.map((t) => [t.id, t]));
  const analysis = analyzeCoverage(ctx, reg, byId);
  const cov = analysis.cov;

  it('extracts exactly 40 live and 3 historical collections at baseline', () => {
    const live = cov.collections.filter((c) => !c.historical).map((c) => c.name);
    const historical = cov.collections.filter((c) => c.historical).map((c) => c.name).sort();
    assert.equal(live.length, 40);
    assert.deepEqual(historical, ['anecdotes', 'experience_items', 'resume_bullets']);
    assert.ok(live.includes('users'));
    for (const j of ['exp_job_projects', 'exp_job_anecdotes', 'exp_job_bullets', 'exp_project_anecdotes', 'exp_project_bullets', 'exp_anecdote_bullets']) assert.ok(live.includes(j), j);
    assert.ok(live.includes('ai_settings'), 'ai_settings is dropped and recreated, so it is live');
  });

  it('covers every router prefix and /health', () => {
    assert.deepEqual(cov.apiRoutes.map((r) => r.name).sort(), ['/api', '/api/ai', '/api/ai-coding', '/api/pdf', '/api/sd-practice', '/api/share', '/api/take-home', '/health']);
    const main = fs.readFileSync(path.join(REPO_ROOT, 'backend/main.py'), 'utf8');
    assert.equal(cov.apiRoutes.filter((r) => r.mountedAt).length, (main.match(/app\.include_router\(/g) || []).length);
  });

  it('covers every literal App.tsx segment', () => {
    const app = fs.readFileSync(path.join(REPO_ROOT, 'frontend/src/App.tsx'), 'utf8');
    const expected = new Set();
    for (const m of app.matchAll(/(?:path|to)="([^"]+)"/g)) for (const seg of m[1].split('/')) if (seg && !seg.startsWith(':')) expected.add(seg);
    assert.deepEqual(cov.routeSegments.map((s) => s.name).sort(), [...expected].sort());
  });

  it('finds the 24 AppHeader call sites and the Layout and Command Center strings', () => {
    assert.equal(cov.appHeaderCallSites, 24);
    const layout = cov.uiStrings.filter((s) => s.path.endsWith('Layout.tsx')).map((s) => s.name);
    for (const name of ['AI Assisted Coding', 'Real World Problems', 'Todos', 'Todo', 'Profile', 'Practice', 'Track']) assert.ok(layout.includes(name), name);
    assert.ok(cov.uiStrings.some((s) => s.name === 'Add round' && s.path.endsWith('registry.tsx')));
  });

  it('maps every coverage-set name to a term label or an adapter entry', () => {
    const uncovered = analysis.results.filter((r) => !r.via).map((r) => `${r.item.kind}:${r.item.name}`);
    assert.deepEqual(uncovered, []);
    assert.deepEqual(analysis.positioning.filter((p) => !p.current && !p.adapter).map((p) => p.item.path), []);
  });

  it('fails an uncovered name', () => {
    const findings = run(fixture((dir) => editText(dir, 'frontend/src/components/Layout.tsx', (s) => s.replace("{ path: '/dashboard', label: 'Today', glyph: DashGlyph },", "{ path: '/dashboard', label: 'Today', glyph: DashGlyph },\n  { path: '/inbox', label: 'Inbox', glyph: DashGlyph },"))));
    only(findings, 'VOCAB_UNCOVERED_NAME');
    assert.match(findings[0].message, /never loosen the rule/);
    const migration = run(fixture((dir) => fs.writeFileSync(path.join(dir, 'pocketbase/pb_migrations/1700009000_capture_inbox.js'), 'migrate((db) => {\n  const dao = new Dao(db);\n  dao.saveCollection(new Collection({ name: "capture_inbox", type: "base", schema: [] }));\n}, (db) => {});\n')));
    only(migration, 'VOCAB_UNCOVERED_NAME');
  });

  it('fails a non-literal new Collection name without adapter entries', () => {
    const findings = run(fixture((dir) => editJson(dir, ADAPTERS, (d) => { d.adapters = d.adapters.filter((a) => !a.legacyName.startsWith('exp_')); })));
    only(findings, 'VOCAB_NONLITERAL_COLLECTION');
    assert.equal(findings[0].path, 'pocketbase/pb_migrations/1700003000_experience_connections.js');
  });

  it('fails an adapter entry whose name is gone', () => {
    only(run(fixture((dir) => editJson(dir, ADAPTERS, (d) => {
      d.adapters.push({ kind: 'ui-string', source: { path: 'frontend/src/components/Layout.tsx', lines: '1' }, legacyName: 'Nonexistent', termId: 'action', targetLabel: 'Actions', retiringLeaf: 'ROUNDS-33-L02' });
    }))), 'VOCAB_ADAPTER_STALE');
    only(run(fixture((dir) => editText(dir, 'frontend/src/pages/Profile.tsx', (s) => s.replace('title="Your profile"', 'title={label}')))), 'VOCAB_ADAPTER_STALE');
  });
});

describe('vocabulary: stored legacy terms (migration)', () => {
  const adapters = readJson(REPO_ROOT, ADAPTERS).adapters;
  const resolve = leafResolver(readJson(REPO_ROOT, LEAF_IDS));

  it('gives system, todo, ai-coding, real-world, take-home, and every collection a term or decider and a retiring leaf', () => {
    const stored = adapters.filter((a) => a.kind === 'stored-value');
    for (const name of ['system', 'todo', 'ai-coding', 'real-world', 'take-home']) {
      const entries = stored.filter((a) => a.legacyName === name);
      assert.ok(entries.length > 0, name);
      for (const a of entries) {
        assert.ok(a.termId || (a.decidedBy && resolve(a.decidedBy).ok), `${name} has termId or decidedBy`);
        assert.ok(resolve(a.retiringLeaf).ok, `${name} retiring leaf resolves`);
      }
    }
    const collections = adapters.filter((a) => a.kind === 'collection');
    assert.equal(collections.length, 43);
    for (const a of collections) {
      assert.ok(a.termId || a.decidedBy, a.legacyName);
      assert.ok(resolve(a.retiringLeaf).ok, a.legacyName);
    }
    assert.equal(collections.find((a) => a.legacyName === 'interview_rounds').retiringLeaf, 'ROUNDS-22-L05');
    assert.equal(adapters.find((a) => a.kind === 'field' && a.legacyName === 'users.target').decidedBy, 'ROUNDS-03-L02');
  });

  it('names #178 for the Profile page copy', () => {
    for (const a of adapters.filter((x) => x.source.path === 'frontend/src/pages/Profile.tsx')) assert.equal(a.retiringLeaf, 'ROUNDS-03-L04');
  });
});

describe('vocabulary: documentation', () => {
  it('fails a positioning line that matches neither positioning nor its adapter', () => {
    only(run(fixture((dir) => editText(dir, 'README.md', (s) => s.replace(/^Rounds is a self-hostable career command center.*$/m, 'Rounds is an interview prep tool.')))), 'VOCAB_POSITIONING_STALE');
    const showcase = run(fixture((dir) => editText(dir, 'SHOWCASE.md', (s) => s.replace('A tour of Rounds', 'A short tour of Rounds'))));
    assert.deepEqual(codes(showcase), ['VOCAB_ADAPTER_STALE', 'VOCAB_POSITIONING_STALE']);
  });

  it('accepts a kept positioning line once it is rewritten, if its adapter goes too', () => {
    const terms = readJson(REPO_ROOT, TERMS);
    const dir = fixture((d) => {
      editText(d, 'SHOWCASE.md', (s) => s.split('\n').map((l, i) => (i === 2 ? terms.positioning.statement : l)).join('\n'));
      editJson(d, ADAPTERS, (data) => { data.adapters = data.adapters.filter((a) => !(a.kind === 'positioning' && a.source.path === 'SHOWCASE.md')); });
    });
    assert.deepEqual(run(dir), []);
  });

  it('regenerates the generated files with no diff', () => {
    const ctx = createContext(REPO_ROOT, { base: 'none' });
    const outputs = vocabulary.generate(REPO_ROOT, ctx);
    assert.deepEqual(outputs.map((o) => o.path).sort(), ['docs/decisions/DR-0001-owner-corrections.md', 'docs/vocabulary.md', 'frontend/src/vocabulary/labels.ts']);
    for (const o of outputs) assert.equal(fs.readFileSync(path.join(REPO_ROOT, o.path), 'utf8'), o.content, `${o.path} is up to date`);
  });

  it('carries the spec 1000-1014 labels as written', () => {
    const spec = readJson(FIXTURES, 'spec-labels.json').rows;
    const terms = readJson(REPO_ROOT, TERMS).terms;
    const labels = fs.readFileSync(path.join(REPO_ROOT, 'frontend/src/vocabulary/labels.ts'), 'utf8');
    for (const row of spec) {
      const t = terms.find((x) => x.term === row.term);
      assert.ok(t, row.term);
      assert.equal(t.label.specLabel, row.label, row.term);
      assert.ok(labels.includes(`'${t.id}': '${row.label.replace(/'/g, "\\'")}',`), `labels.ts specLabels has ${row.term}`);
    }
    for (const word of ['Proposed change', 'Writing suggestion', 'Saved changes', 'Version or Submitted version']) assert.ok(labels.includes(`'${word}'`), word);
  });

  it('lists every owner correction in the corrections file', () => {
    const dr = readJson(REPO_ROOT, DR);
    const md = fs.readFileSync(path.join(REPO_ROOT, 'docs/decisions/DR-0001-owner-corrections.md'), 'utf8');
    assert.deepEqual(dr.corrections.map((c) => c.id), ['C1', 'C2', 'C3', 'C4', 'C5', 'C6']);
    for (const item of [...dr.corrections, ...dr.specChangeRequests, ...dr.departures]) assert.ok(md.includes(`**${item.id}. ${item.title}.**`), item.id);
    for (const d of dr.decisions.filter((x) => x.status === 'ratified-here')) assert.ok(md.includes(`**${d.id}. ${d.title}.**`), d.id);
    assert.deepEqual(dr.decisions.filter((x) => x.status === 'ratified-here').map((x) => x.id), ['G6', 'G7', 'G8', 'G9']);
  });
});

describe('vocabulary: security', () => {
  const terms = readJson(REPO_ROOT, TERMS).terms;

  it('defines the Secret privacy class and Share Capability', () => {
    for (const id of ['privacy-secret', 'share-capability']) {
      const t = terms.find((x) => x.id === id);
      assert.ok(t && t.definition && t.definition.length > 40, id);
    }
    assert.equal(terms.find((x) => x.id === 'privacy-secret').definedBy[0], 'ROUNDS-14-L01');
  });

  it('rejects token-shaped examples and passes synthetic ones', () => {
    const token = 'x1'.repeat(12);
    only(run(fixture((dir) => editTerm(dir, 'calendar-provider', (t) => { t.examples = [`a calendar link with ${token}`]; }))), 'VOCAB_SECRET_EXAMPLE');
    only(run(fixture((dir) => editTerm(dir, 'calendar-provider', (t) => { t.examples = ['shared at /r/placeholder']; }))), 'VOCAB_SECRET_EXAMPLE');
    only(run(fixture((dir) => editTerm(dir, 'calendar-provider', (t) => { t.examples = [`owner@${'mail'}.test.org`]; }))), 'VOCAB_SECRET_EXAMPLE');
    assert.deepEqual(run(fixture((dir) => editTerm(dir, 'calendar-provider', (t) => {
      t.examples = ['see provider-invocation-receipt and ROUNDS-00A-L01/S3', 'owner@example.com', 'a third-party-personal field'];
    }))), []);
    assert.deepEqual(secretShapes('provider-invocation-receipt', new Set()), []);
  });
});

describe('vocabulary: data-preserving cutover wording', () => {
  const phrase = ['Clean', 'cutover'].join(' ');

  it('passes the two shipped migration comments', () => {
    const findings = run(fixture());
    assert.equal(findings.filter((f) => f.code.startsWith('VOCAB_CUTOVER')).length, 0);
    for (const rel of ['pocketbase/pb_migrations/1700004100_drop_legacy_anecdotes.js', 'pocketbase/pb_migrations/1700005100_drop_resume_bullets.js']) {
      assert.equal(cutoverMatches(fs.readFileSync(path.join(REPO_ROOT, rel), 'utf8')).length, 1, rel);
    }
  });

  it('fails a new unqualified comment and passes a qualified one', () => {
    const bad = run(fixture((dir) => fs.writeFileSync(path.join(dir, 'pocketbase/pb_migrations/1700009100_drop_legacy_thing.js'), `// ${phrase}: drop the legacy thing. (No data migration.)\nmigrate((db) => {}, (db) => {});\n`)));
    only(bad, 'VOCAB_CUTOVER_UNQUALIFIED');
    assert.equal(bad[0].line, 1);
    const good = run(fixture((dir) => fs.writeFileSync(path.join(dir, 'docs/notes.md'), `The program is a data-preserving ${phrase.toLowerCase()}, and so is the Data-Preserving ${phrase}.\n`)));
    assert.deepEqual(good, []);
    assert.equal(cutoverMatches(`a ${phrase.toLowerCase().replace(' ', '-')} program`).length, 1);
  });

  it('fails an allowlist entry whose line no longer holds the phrase', () => {
    const findings = run(fixture((dir) => editJson(dir, TERMS, (d) => { d.cutover.allowlist[0].line = 4; })));
    assert.deepEqual(codes(findings), ['VOCAB_CUTOVER_ALLOWLIST_STALE', 'VOCAB_CUTOVER_UNQUALIFIED']);
  });
});

describe('vocabulary: revisions', () => {
  const baseText = fs.readFileSync(path.join(REPO_ROOT, TERMS), 'utf8');
  const base = { files: { [TERMS]: baseText } };
  const removeCalendar = (d, revision, compatibility) => {
    d.terms = d.terms.filter((t) => t.id !== 'calendar-provider');
    d.revision = revision;
    d.compatibility = compatibility;
  };
  const setDr = (dir, revision, compatibility) => editJson(dir, DR, (r) => { r.revision = revision; r.compatibility = compatibility; });
  const termAdapter = (revision) => (d) => {
    d.adapters.push({ kind: 'term', source: { path: TERMS, revision }, legacyName: 'Calendar provider', decidedBy: 'ROUNDS-22-L02', targetLabel: null, retiringLeaf: 'ROUNDS-32-L10' });
  };

  it('passes when terms.json is unchanged from main', () => {
    assert.deepEqual(run(fixture(), { base }), []);
  });

  it('rejects a breaking change whose revision matches main', () => {
    const dir = fixture((d) => { editJson(d, TERMS, (x) => removeCalendar(x, 1, 'breaking')); setDr(d, 1, 'breaking'); editJson(d, ADAPTERS, termAdapter(1)); });
    only(run(dir, { base }), 'VOCAB_REVISION_NOT_BUMPED');
  });

  it('rejects a removal that is not marked breaking', () => {
    const dir = fixture((d) => { editJson(d, TERMS, (x) => removeCalendar(x, 2, 'additive')); setDr(d, 2, 'additive'); editJson(d, ADAPTERS, termAdapter(2)); });
    only(run(dir, { base }), 'VOCAB_COMPATIBILITY_UNDECLARED');
  });

  it('keeps adapter entries for names a breaking revision removes', () => {
    const dir = fixture((d) => { editJson(d, TERMS, (x) => removeCalendar(x, 2, 'breaking')); setDr(d, 2, 'breaking'); });
    only(run(dir, { base }), 'VOCAB_REMOVED_TERM_UNADAPTED');
    const withAdapter = fixture((d) => { editJson(d, TERMS, (x) => removeCalendar(x, 2, 'breaking')); setDr(d, 2, 'breaking'); editJson(d, ADAPTERS, termAdapter(2)); });
    assert.deepEqual(run(withAdapter, { base }), []);
  });

  it('requires terms.json and DR-0001 to share one revision', () => {
    only(run(fixture((d) => setDr(d, 2, 'additive'))), 'VOCAB_REVISION_MISMATCH');
  });

  it('fails closed when the base ref cannot be read', () => {
    const findings = vocabulary.check(REPO_ROOT, createContext(REPO_ROOT, { base: 'refs/heads/no-such-branch-for-conformance' }));
    only(findings, 'VOCAB_BASE_UNAVAILABLE');
  });
});

describe('vocabulary: journey', () => {
  it('lets #61 cite DR-0001@1 for the "Proposed change" label', () => {
    const terms = readJson(REPO_ROOT, TERMS);
    const claim = terms.terms.find((t) => t.id === 'extracted-claim');
    assert.equal(claim.label.options.find((o) => o.key === claim.label.default).singular, 'Proposed change');
    assert.equal(`${terms.decisionRecord}@${terms.revision}`, 'DR-0001@1');
    assert.ok(readJson(REPO_ROOT, DR).consumers.includes('ROUNDS-12-L01'));
  });
});

describe('vocabulary: extraction without adapters', () => {
  it('reports the non-literal junction site as unresolved', () => {
    const dir = fixture();
    writeJson(dir, ADAPTERS, { registry: 'rounds-vocabulary-adapters', adapters: [] });
    const cov = extractCoverage(ctxFor(dir));
    assert.equal(cov.unresolvedCollections.length, 1);
    assert.equal(cov.collections.filter((c) => !c.historical).length, 34);
  });
});
