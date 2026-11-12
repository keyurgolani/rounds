// The privacy rule (ROUNDS-14-L01, DR-0005). Each negative control runs the
// rule over the repository with a few files replaced, added, or removed in
// memory, so a test names exactly what it changes.

import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { after, describe, it } from 'node:test';
import { createContext } from '../lib/context.mjs';
import { definitionUse } from '../lib/privacy/checks.mjs';
import { COPY_DIRS, CONFIG_DOC_PATH, DOC_PATH, PRIVACY_DIR, sourceFiles } from '../lib/privacy/files.mjs';
import { MIGRATIONS_DIR, extractSchema, migrationFiles } from '../lib/privacy/schema-vm.mjs';
import * as privacy from '../rules/privacy.mjs';
import { FIXTURES, REPO_ROOT, cleanup, codes, tempDir } from './helpers.mjs';

after(cleanup);

const POLICY = 'contracts/privacy/policy.json';
const SCHEMA = 'contracts/privacy/policy.schema.json';
const PURPOSES = 'contracts/privacy/purposes.json';
const FIELD_MAP = 'contracts/privacy/field-map.json';
const VIOLATIONS = 'contracts/privacy/violations.json';
const RECORD = 'docs/decisions/DR-0005-privacy-policy.json';
const MATRIX = 'contracts/authority/matrix.json';
const PIN = 'privacy/schema-6c4a5a3.json';
const SPEC_FIXTURE = 'privacy/spec-2126-2169.md';

const real = createContext(REPO_ROOT, { base: 'none' });
const json = (rel) => JSON.parse(real.read(rel));
const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);

// The repository with `files` replaced or added and `remove` gone, all in
// memory. `base` stands in for the base branch ({ [rel]: content }); a file
// it doesn't name is absent there.
function overlay({ files = {}, remove = [], base = {}, reviewRoot = null } = {}) {
  const gone = new Set(remove);
  const list = [...new Set([...real.files().filter((f) => !gone.has(f)), ...Object.keys(files)])].sort();
  const ctx = {
    ...real,
    reviewRoot,
    files: () => list,
    exists: (rel) => own(files, rel) || (!gone.has(rel) && real.exists(rel)),
    read: (rel) => {
      if (own(files, rel)) return files[rel];
      if (gone.has(rel)) throw new Error(`ENOENT: ${rel}`);
      return real.read(rel);
    },
    readJson: (rel) => JSON.parse(ctx.read(rel)),
    readBase: (rel) => ({ ok: true, content: own(base, rel) ? base[rel] : null }),
  };
  return ctx;
}

// { [rel]: text } for `rel` after fn edits its parsed JSON in place.
const edit = (rel, fn) => {
  const data = json(rel);
  const out = fn(data);
  return { [rel]: `${JSON.stringify(out === undefined ? data : out, null, 2)}\n` };
};
const check = (options) => privacy.check(REPO_ROOT, overlay(options));
const only = (findings, code) => assert.deepEqual(codes(findings), [code], JSON.stringify(findings, null, 2));
const includes = (findings, code) => assert.ok(codes(findings).includes(code), JSON.stringify(findings, null, 2));
const clean = (findings) => assert.deepEqual(findings, [], JSON.stringify(findings, null, 2));

const entry = (m, id) => m.entries.find((e) => e.id === id);
const purpose = (r, id) => r.purposes.find((p) => p.id === id);
const violation = (r, id) => r.entries.find((v) => v.id === id);
const python = (lines) => `${lines.join('\n')}\n`;
const EXAMPLE_PY = 'backend/app/overlay_example.py';

describe('privacy: repository', () => {
  it('passes on the repository, and on an overlay that changes nothing', () => {
    clean(privacy.check(REPO_ROOT, createContext(REPO_ROOT, { base: { files: {} } })));
    clean(check());
  });

  it('keeps every generated file in step with the policy', () => {
    const out = privacy.generate(REPO_ROOT, overlay());
    const paths = out.map((o) => o.path);
    assert.ok(paths.includes(DOC_PATH) && paths.includes(CONFIG_DOC_PATH));
    const settings = out.find((o) => o.path === CONFIG_DOC_PATH).content;
    for (const name of ['ROUNDS_LOG_RETENTION_DAYS', 'ROUNDS_BACKUP_RETENTION_DAYS', 'ROUNDS_AI_PRIVATE_ENDPOINTS']) assert.match(settings, new RegExp(`\\| \`${name}\` \\|`));
    for (const o of out) assert.equal(o.content, fs.readFileSync(path.join(REPO_ROOT, o.path), 'utf8'), `${o.path} differs; run node scripts/conformance/run.mjs --write`);
  });

  it('copies every contract file byte for byte into both evaluators\' directories', () => {
    const out = privacy.generate(REPO_ROOT, overlay());
    for (const file of sourceFiles(real)) {
      for (const dir of COPY_DIRS) {
        const copy = out.find((o) => o.path === `${dir}/${file.slice(PRIVACY_DIR.length + 1)}`);
        assert.ok(copy, `${dir} has no copy of ${file}`);
        assert.equal(copy.content, real.read(file));
      }
    }
  });

  it('regenerates the policy doc from the policy, and fails when the settings markers are gone', () => {
    const changed = edit(POLICY, (p) => { p.accountDeletion.text += ' Example.'; });
    const doc = privacy.generate(REPO_ROOT, overlay({ files: changed })).find((o) => o.path === DOC_PATH);
    assert.notEqual(doc.content, real.read(DOC_PATH));
    const config = real.read(CONFIG_DOC_PATH).replace('<!-- privacy-settings:end -->', '');
    only(check({ files: { [CONFIG_DOC_PATH]: config } }), 'PRIVACY_DOC_MARKERS');
  });

  it('fails a copy whose contract file is gone', () => {
    only(check({ files: { 'backend/app/privacy/retired.json': '{}\n' } }), 'PRIVACY_COPY_STALE');
  });
});

describe('privacy: the live schema', () => {
  const pin = JSON.parse(fs.readFileSync(path.join(FIXTURES, PIN), 'utf8'));

  it('reads exactly the schema PocketBase left at 6c4a5a3, over exactly the pinned migrations', () => {
    const tree = real.tree(pin.revision);
    assert.ok(tree.ok, tree.reason);
    assert.deepEqual(migrationFiles(tree).map((f) => f.slice(MIGRATIONS_DIR.length + 1)), pin.migrations);
    const got = extractSchema(tree, { only: pin.migrations });
    assert.deepEqual(got.errors, []);
    assert.equal(got.files.length, 38);
    // The pin holds each field's name and type; the reader also keeps a
    // text field's pattern, for the free-text kind check.
    const byName = (cs) => [...cs].sort((a, b) => (a.name < b.name ? -1 : 1)).map((c) => ({
      name: c.name, type: c.type, listRule: c.listRule, viewRule: c.viewRule, fields: c.fields.map((f) => ({ name: f.name, type: f.type })),
    }));
    assert.deepEqual(byName(got.collections), byName(pin.collections));
    assert.equal(pin.collections.length, 55);
    assert.equal(pin.collections.reduce((n, c) => n + c.fields.length, 0), 495);
  });

  it('fails closed on a migration it can\'t interpret', () => {
    const file = `${MIGRATIONS_DIR}/1799999999_overlay_example.js`;
    const text = 'migrate((db) => { const dao = new Dao(db); dao.runSomethingNew("applications"); }, (db) => {});\n';
    includes(check({ files: { [file]: text } }), 'PRIVACY_SCHEMA_UNREADABLE');
  });
});

describe('privacy: coverage', () => {
  it('fails a new collection field until the field map classes it', () => {
    const file = `${MIGRATIONS_DIR}/1799999999_overlay_example.js`;
    const text = [
      'migrate((db) => {',
      '  const dao = new Dao(db);',
      '  const collection = dao.findCollectionByNameOrId("applications");',
      '  collection.schema.addField(new SchemaField({ name: "overlay_note", type: "text" }));',
      '  dao.saveCollection(collection);',
      '}, (db) => {});',
      '',
    ].join('\n');
    const findings = check({ files: { [file]: text } });
    only(findings, 'FIELD_UNCLASSIFIED');
    assert.match(findings[0].message, /pb:applications\.overlay_note/);
    const classed = edit(FIELD_MAP, (m) => { m.entries.push({ id: 'pb:applications.overlay_note', class: 'Private', kind: 'content', row: 'opportunity' }); });
    clean(check({ files: { [file]: text, ...classed } }));
  });

  it('fails a new browser storage key family', () => {
    const file = 'frontend/src/lib/overlayExample.ts';
    const findings = check({ files: { [file]: "export const remember = () => localStorage.setItem('rounds:overlay-example', '1');\n" } });
    only(findings, 'FIELD_UNCLASSIFIED');
    assert.match(findings[0].message, /storage:rounds:overlay-example/);
  });

  it('fails a new property on a stored definition\'s schema', () => {
    const used = definitionUse(real).used.find((d) => d.name === 'manifest');
    const findings = check({ files: edit(used.path, (s) => { s.properties = { ...s.properties, overlay_note: { type: 'string' } }; }) });
    only(findings, 'FIELD_UNCLASSIFIED');
    assert.match(findings[0].message, /def:manifest#\/overlay_note/);
  });

  it('fails an entry no migration, key, or definition still has', () => {
    only(check({ files: edit(FIELD_MAP, (m) => { m.entries.push({ id: 'pb:applications.retired_field', class: 'Private', kind: 'content', row: 'opportunity' }); }) }), 'PRIVACY_FIELD_STALE');
    only(check({ files: edit(FIELD_MAP, (m) => { m.entries.push({ id: 'storage:rounds:retired-key', class: 'Private', kind: 'metadata', row: 'view-state' }); }) }), 'PRIVACY_FIELD_STALE');
  });

  it('needs each named JSON column\'s declared paths, and pointer entries inside them', () => {
    only(check({ files: edit(FIELD_MAP, (m) => { delete m.shapes['pb:resumes.data']; }) }), 'PRIVACY_SHAPE_MISSING');
    only(check({ files: edit(FIELD_MAP, (m) => { m.entries.push({ id: 'pb:resumes.data#/undeclared', class: 'Private', kind: 'content', row: 'artifact-edition' }); }) }), 'PRIVACY_FIELD_STALE');
  });
});

describe('privacy: the field map', () => {
  it('fails an id outside the four forms, and the entity form until its entities exist', () => {
    includes(check({ files: edit(FIELD_MAP, (m) => { m.entries.push({ id: 'Not An Id', class: 'Private', kind: 'content' }); }) }), 'PRIVACY_FIELD_ID_INVALID');
    only(check({ files: edit(FIELD_MAP, (m) => { m.entries.push({ id: 'pursuit.company', class: 'Private', kind: 'content' }); }) }), 'PRIVACY_FIELD_ID_INVALID');
  });

  it('gives each field one class: a second entry fails', () => {
    only(check({ files: edit(FIELD_MAP, (m) => { m.entries.push({ ...entry(m, 'pb:applications.company'), class: 'Sensitive' }); }) }), 'PRIVACY_FIELD_TWO_CLASSES');
  });

  it('fails a row the authority matrix doesn\'t have, and a row its store doesn\'t map to', () => {
    only(check({ files: edit(FIELD_MAP, (m) => { entry(m, 'pb:applications.company').row = 'no-such-row'; }) }), 'PRIVACY_UNKNOWN_REF');
    includes(check({ files: edit(FIELD_MAP, (m) => { entry(m, 'pb:applications.company').row = 'offer'; }) }), 'PRIVACY_ROW_MISMATCH');
  });

  it('fails a class looser than its row\'s floor', () => {
    includes(check({ files: edit(FIELD_MAP, (m) => { entry(m, 'pb:offers.annual_bonus_target_pct').class = 'Private'; }) }), 'PRIVACY_FLOOR_LOOSER');
    // A visibility too: grading material may not move below its row's server-only.
    includes(check({ files: edit(FIELD_MAP, (m) => { entry(m, 'pb:ai_coding_rounds.checkpoints#/*/hidden_files').visibility = 'authed-readable'; }) }), 'PRIVACY_FLOOR_LOOSER');
  });

  it('lets a deeper entry only tighten its column', () => {
    // The resume purposes list Private only, so they fail too; the point is the paths.
    const findings = check({ files: edit(FIELD_MAP, (m) => { entry(m, 'pb:resumes.data').class = 'Sensitive'; }) });
    includes(findings, 'PRIVACY_DESCENDANT_LOOSER');
    assert.ok(findings.filter((f) => f.code === 'PRIVACY_DESCENDANT_LOOSER').every((f) => /^pb:resumes\.data#\//.test(f.message)));
  });

  it('fails an entry that names no row when its store maps to rows', () => {
    only(check({ files: edit(FIELD_MAP, (m) => { delete entry(m, 'pb:applications.company').row; }) }), 'PRIVACY_ROW_MISSING');
  });

  it('kinds free text as content: metadata needs a text column its migration constrains', () => {
    only(check({ files: edit(FIELD_MAP, (m) => { entry(m, 'pb:experience_anecdotes.action').kind = 'metadata'; }) }), 'PRIVACY_KIND_UNCONSTRAINED');
    only(check({ files: edit(FIELD_MAP, (m) => { entry(m, 'pb:applications.status').kind = 'opaque-id'; }) }), 'PRIVACY_KIND_UNCONSTRAINED');
    // A pattern that only bars some characters still leaves free text.
    only(check({ files: edit(FIELD_MAP, (m) => { entry(m, 'pb:share_capabilities.purpose').kind = 'metadata'; }) }), 'PRIVACY_KIND_UNCONSTRAINED');
    clean(check({ files: edit(FIELD_MAP, (m) => { entry(m, 'pb:experience_anecdotes.action').kind = 'content'; }) }));
  });

  it('fails a field_map cell still pending on this leaf', () => {
    only(check({ files: edit(MATRIX, (m) => { m.rows.find((r) => r.field_map === 'contracts/privacy/field-map.json').field_map = 'pending:ROUNDS-14-L01'; }) }), 'PRIVACY_FIELD_MAP_CELL');
  });
});

describe('privacy: the policy', () => {
  it('validates every file against its schema', () => {
    only(check({ files: edit(POLICY, (p) => { p.overlay = true; }) }), 'PRIVACY_SCHEMA_INVALID');
    only(check({ files: edit(VIOLATIONS, (r) => { violation(r, 3).status = 'paused'; }) }), 'PRIVACY_SCHEMA_INVALID');
    includes(check({ files: { [PURPOSES]: '{ not json' } }), 'PRIVACY_SCHEMA_INVALID');
  });

  it('needs a rule for every class and sink, in the spec\'s words', () => {
    includes(check({ files: edit(POLICY, (p) => { p.matrix.cells = p.matrix.cells.filter((c) => c.id !== 'sensitive.export'); }) }), 'PRIVACY_MATRIX_INCOMPLETE');
    only(check({ files: edit(POLICY, (p) => { p.matrix.cells.find((c) => c.id === 'private.index').text = 'Indexed freely'; }) }), 'PRIVACY_MATRIX_TEXT');
    only(check({ files: edit(POLICY, (p) => { p.matrix.rows.reverse(); }) }), 'PRIVACY_MATRIX_TEXT');
    includes(check({ files: edit(POLICY, (p) => { p.sinks.push({ ...p.sinks[0] }); }) }), 'PRIVACY_DUPLICATE');
  });

  it('keeps each lifecycle default inside its own bounds, and each enforcing leaf real', () => {
    only(check({ files: edit(POLICY, (p) => { p.lifecycle.rows.find((r) => r.id === 'logs-traces').retention.default = 45; }) }), 'PRIVACY_SCHEMA_INVALID');
    includes(check({ files: edit(POLICY, (p) => { p.sinks[0].enforcingLeaf = 'ROUNDS-99-L99'; }) }), 'PRIVACY_UNKNOWN_REF');
  });

  it('fails a pin no revision has, and a superseded pin its successor isn\'t compatible with', () => {
    only(check({ files: { 'docs/overlay-example.md': 'This reads privacy@7.\n' } }), 'PRIVACY_UNKNOWN_PIN');
    const next = edit(POLICY, (p) => {
      const v = p.versions.find((x) => x.id === 'redaction');
      v.current = 2;
      v.revisions.push({ revision: 2, status: 'draft', compatibleWith: [], changedConstraint: 'An example change.' });
    });
    includes(check({ files: { ...next, 'docs/overlay-example.md': 'This reads redaction@1.\n' } }), 'PRIVACY_PIN_INCOMPATIBLE');
    const compatible = edit(POLICY, (p) => {
      const v = p.versions.find((x) => x.id === 'redaction');
      v.current = 2;
      v.revisions.push({ revision: 2, status: 'draft', compatibleWith: [1], changedConstraint: 'An example change.' });
    });
    const findings = check({ files: { ...compatible, 'docs/overlay-example.md': 'This reads redaction@1.\n' } });
    assert.ok(!codes(findings).includes('PRIVACY_PIN_INCOMPATIBLE'), JSON.stringify(findings, null, 2));
  });

  it('fails a revision that names no changed constraint', () => {
    includes(check({ files: edit(POLICY, (p) => {
      const v = p.versions.find((x) => x.id === 'consent');
      v.current = 2;
      v.revisions.push({ revision: 2, status: 'draft', compatibleWith: [1], changedConstraint: null });
    }) }), 'PRIVACY_SUPERSESSION_INCOMPLETE');
  });

  it('holds no secret-shaped value; fixtures are stored as parts', () => {
    const key = ['sk-ant-', 'api03-', 'Q'.repeat(24)].join('');
    only(check({ files: edit(PURPOSES, (r) => { purpose(r, 'resume.improve').note = `example ${key}`; }) }), 'PRIVACY_SECRET_VALUE');
    // The docs the rule writes are scanned too.
    const doc = `${real.read(DOC_PATH)}\nexample ${key}\n`;
    includes(check({ files: { [DOC_PATH]: doc } }), 'PRIVACY_SECRET_VALUE');
  });
});

describe('privacy: the vectors', () => {
  const VECTORS = 'contracts/privacy/vectors';
  const drop = (suite, id) => edit(`${VECTORS}/${suite}.json`, (v) => { v.cases = v.cases.filter((c) => c.id !== id); });

  it('needs a never-destination case for every range, service name, and suffix', () => {
    only(check({ files: drop('destinations', 'never.wire-server') }), 'PRIVACY_VECTORS_INCOMPLETE');
    only(check({ files: drop('destinations', 'never.materializer') }), 'PRIVACY_VECTORS_INCOMPLETE');
    only(check({ files: drop('destinations', 'never.cluster-suffix') }), 'PRIVACY_VECTORS_INCOMPLETE');
  });

  it('needs each lifecycle row\'s default, an allowed value, an out-of-bound value, and purge_by', () => {
    const findings = check({ files: drop('retention', 'secrets.out-of-bounds') });
    only(findings, 'PRIVACY_VECTORS_INCOMPLETE');
    assert.match(findings[0].message, /secrets has no out-of-bound case/);
    only(check({ files: drop('retention', 'browser-ai-caches.seven') }), 'PRIVACY_VECTORS_INCOMPLETE');
  });

  it('needs a fixture and a near miss for every secret pattern', () => {
    only(check({ files: edit('contracts/privacy/secret-patterns.json', (s) => { s.nearMisses = s.nearMisses.filter((x) => x.pattern !== 'jwt'); }) }), 'PRIVACY_VECTORS_INCOMPLETE');
  });
});

describe('privacy: the decision record', () => {
  it('passes the committed record', () => {
    const r = json(RECORD);
    assert.equal(r.leaf, 'ROUNDS-14-L01');
    assert.equal(r.authorityBoundary, POLICY);
    assert.ok(r.decisions.length >= 1 && r.decisions.every((d) => d.alternatives.length));
  });

  it('fails a record without an owner, its enforcing leaves, alternatives, versions, or supersession', () => {
    only(check({ files: edit(RECORD, (r) => { r.owner = ''; }) }), 'PRIVACY_RECORD_INCOMPLETE');
    only(check({ files: edit(RECORD, (r) => { r.consumers = r.consumers.filter((c) => c !== 'ROUNDS-14-L02'); }) }), 'PRIVACY_RECORD_INCOMPLETE');
    only(check({ files: edit(RECORD, (r) => { r.decisions[0].alternatives = []; }) }), 'PRIVACY_RECORD_INCOMPLETE');
    only(check({ files: edit(RECORD, (r) => { r.versioning = r.versioning.replaceAll('consent@1', 'consent'); }) }), 'PRIVACY_RECORD_INCOMPLETE');
    only(check({ files: edit(RECORD, (r) => { delete r.supersession; }) }), 'PRIVACY_RECORD_INCOMPLETE');
    only(check({ files: edit(RECORD, (r) => { r.authorityBoundary = 'contracts/privacy/purposes.json'; }) }), 'PRIVACY_RECORD_INCOMPLETE');
  });

  // The policy with every current revision marked `status`.
  const policyMarked = (status) => edit(POLICY, (p) => { for (const v of p.versions) v.revisions.find((r) => r.revision === v.current).status = status; });

  it('pins the policy and its schema once ratified', () => {
    const policy = policyMarked('ratified');
    const sha = (rel) => createHash('sha256').update(own(policy, rel) ? policy[rel] : real.read(rel)).digest('hex');
    const ratify = (pins) => ({ ...policy, ...edit(RECORD, (r) => {
      Object.assign(r, { status: 'ratified', approver: 'a reviewer', approvalRef: { pr: 1, governedFiles: pins.map((p) => ({ path: p, sha256: sha(p) })) } });
    }) });
    clean(check({ files: ratify([POLICY, SCHEMA]) }));
    only(check({ files: ratify([POLICY]) }), 'PRIVACY_RECORD_INCOMPLETE');
  });

  it('ratifies the record and the policy\'s current revisions together', () => {
    only(check({ files: policyMarked('ratified') }), 'PRIVACY_STATUS_MISMATCH');
    const sha = (rel) => createHash('sha256').update(real.read(rel)).digest('hex');
    const record = edit(RECORD, (r) => {
      Object.assign(r, { status: 'ratified', approver: 'a reviewer', approvalRef: { pr: 1, governedFiles: [POLICY, SCHEMA].map((p) => ({ path: p, sha256: sha(p) })) } });
    });
    only(check({ files: record }), 'PRIVACY_STATUS_MISMATCH');
  });

  it('fails when no record names the leaf', () => {
    only(check({ remove: [RECORD] }), 'PRIVACY_RECORD_MISSING');
  });
});

describe('privacy: purposes and the provider-call scan', () => {
  const caller = (body) => ({ [EXAMPLE_PY]: python(body) });

  it('fails a provider helper reference no purpose registers, called, passed, or aliased', () => {
    for (const body of [
      ['from routers.ai import _call_complete', '', '', 'async def overlay_summary(text):', '    return await _call_complete(text)'],
      ['from routers.ai import _call_stream', '', '', 'def overlay_stream():', '    handler = _call_stream', '    return handler'],
      ['from routers.ai import _fetch_models', '', '', 'async def overlay_models(row):', '    return await _fetch_models(row)'],
      ['from routers.sd_practice import _anthropic_stream_with_tools', '', '', 'async def overlay_tools(x):', '    return _anthropic_stream_with_tools(x)'],
      ['from routers.ai import _call_complete as complete', '', '', 'async def overlay_alias(text):', '    return await complete(text)'],
    ]) {
      const findings = check({ files: caller(body) });
      only(findings, 'PURPOSE_UNREGISTERED_CALL');
      assert.equal(findings[0].path, EXAMPLE_PY);
    }
  });

  it('fails a vendor SDK call or API marker outside the provider helpers', () => {
    for (const body of [
      ['from openai import AsyncOpenAI', '', '', 'def overlay_client(key):', '    return AsyncOpenAI(api_key=key)'],
      ['from openai import OpenAI', '', '', 'def overlay_client(key):', '    return OpenAI(api_key=key)'],
      ['def overlay_url(base):', '    return f"{base}/chat/completions"'],
      ['def overlay_headers(key):', '    return {"x-api-key": key}'],
    ]) only(check({ files: caller(body) }), 'PURPOSE_UNREGISTERED_CALL');
  });

  it('fails a new caller of a registered call site, in its module or through an import', () => {
    for (const body of [
      ['from execution.review import review', '', '', 'async def overlay_grade(attempt):', '    return await review(attempt)'],
      ['from execution import review as reviews', '', '', 'async def overlay_grade(attempt):', '    return await reviews.review(attempt)'],
      ['import execution.review as rv', '', '', 'async def overlay_grade(attempt):', '    return await rv._call(attempt)'],
      ['from routers.ai import _summarize_doc', '', '', 'async def overlay_doc(doc):', '    return await _summarize_doc(doc)'],
    ]) {
      const findings = check({ files: caller(body) });
      only(findings, 'PURPOSE_UNREGISTERED_CALL');
      assert.match(findings[0].message, /a registered call site that reaches a provider/);
    }
    const review = 'backend/execution/review.py';
    const extended = `${real.read(review)}\n\nasync def overlay_again(prompt):\n    return await _call(prompt)\n`;
    only(check({ files: { [review]: extended } }), 'PURPOSE_UNREGISTERED_CALL');
  });

  it('reads a wrapper\'s name as a call only in code, not in a string or as another object\'s attribute', () => {
    clean(check({ files: caller([
      'from execution.review import review', '', '', 'def overlay_text(attempt):', '    label = "review(attempt)"', '    return label, attempt.review',
    ]) }));
  });

  it('reads past a comment or triple-quote mark inside an ordinary string', () => {
    for (const body of [
      ['from routers.ai import _call_complete', '', '', 'async def overlay_hash(text):', '    tag = "#"; return await _call_complete(text)'],
      ['from routers.ai import _call_complete', '', '', 'async def overlay_quote(text):', '    mark = \'"""\'', '    return await _call_complete(text)'],
    ]) only(check({ files: caller(body) }), 'PURPOSE_UNREGISTERED_CALL');
  });

  it('passes a helper call its purpose registers, and fails a call site that is gone', () => {
    const body = ['from routers.ai import _call_complete', '', '', 'async def overlay_summary(text):', '    return await _call_complete(text)'];
    const registered = edit(PURPOSES, (r) => { purpose(r, 'resume.improve').callSites.push({ path: EXAMPLE_PY, function: 'overlay_summary' }); });
    clean(check({ files: { ...caller(body), ...registered } }));
    only(check({ files: registered }), 'PURPOSE_STALE_SITE');
  });

  it('keeps legacy to the sixteen baseline purposes, and a current purpose from going back', () => {
    const added = edit(PURPOSES, (r) => { r.purposes.push({ ...purpose(r, 'resume.improve'), id: 'resume.overlay' }); });
    includes(check({ files: added }), 'PRIVACY_LEGACY_OUTSIDE_BASELINE');
    const base = edit(PURPOSES, (r) => { Object.assign(purpose(r, 'resume.improve'), { status: 'current', consent: 'per-request' }); });
    only(check({ base }), 'PRIVACY_LEGACY_OUTSIDE_BASELINE');
    includes(check({ files: edit(PURPOSES, (r) => { r.purposes = r.purposes.filter((p) => p.id !== 'resume.tailor'); }) }), 'PRIVACY_UNKNOWN_REF');
  });

  it('fails a purpose without a real owner', () => {
    only(check({ files: edit(PURPOSES, (r) => { purpose(r, 'resume.improve').owner = 'ROUNDS-99-L99'; }) }), 'PRIVACY_OWNERLESS');
  });

  it('fails a Secret, server-only, or rubric input where the policy forbids it', () => {
    const secret = json(FIELD_MAP).entries.find((e) => e.class === 'Secret' && e.id.startsWith('pb:ai_providers.'));
    const add = (field) => edit(PURPOSES, (r) => { purpose(r, 'resume.improve').inputs.push({ field }); });
    includes(check({ files: add(secret.id) }), 'PRIVACY_SECRET_INPUT');
    only(check({ files: add('def:harness-revision#/checkpoints') }), 'PRIVACY_SERVER_ONLY_INPUT');
    only(check({ files: add('def:harness-revision#/rubric') }), 'PRIVACY_RUBRIC_OUTSIDE_GRADE');
    only(check({ files: add('pb:offers.annual_bonus_target_pct') }), 'PRIVACY_PURPOSE_CLASSES');
  });

  it('reads an input\'s whole subtree: a parent holding a Secret or server-only entry fails', () => {
    const add = (field) => edit(PURPOSES, (r) => { purpose(r, 'resume.improve').inputs.push({ field }); });
    const secret = check({ files: add('pb:share_capabilities') });
    includes(secret, 'PRIVACY_SECRET_INPUT');
    assert.ok(secret.some((f) => /bearer_digest, a Secret/.test(f.message)), JSON.stringify(secret, null, 2));
    const serverOnly = check({ files: add('pb:ai_coding_rounds.checkpoints') });
    includes(serverOnly, 'PRIVACY_SERVER_ONLY_INPUT');
    assert.ok(serverOnly.every((f) => f.code === 'PRIVACY_SERVER_ONLY_INPUT'), JSON.stringify(serverOnly, null, 2));
  });
});

describe('privacy: the violation register', () => {
  it('fails a detected breach the register doesn\'t list, however the entry was closed', () => {
    only(check({ files: edit(VIOLATIONS, (r) => { r.entries = r.entries.filter((v) => v.id !== 5); }) }), 'PRIVACY_VIOLATION_UNREGISTERED');
    // Closing entry 5 while its fields stay client-readable doesn't make the breach go away.
    includes(check({ files: edit(VIOLATIONS, (r) => { Object.assign(violation(r, 5), { status: 'closed', history: [{ pr: 1, closed: 'example' }] }); }) }), 'PRIVACY_VIOLATION_UNREGISTERED');
  });

  it('fails an open entry whose location is gone', () => {
    only(check({ files: edit(VIOLATIONS, (r) => { violation(r, 3).location.anchors[0].text = 'no longer in the file'; }) }), 'PRIVACY_VIOLATION_STALE');
    only(check({ files: edit(VIOLATIONS, (r) => { violation(r, 1).location.fields.push('storage:rounds:retired-key'); }) }), 'PRIVACY_VIOLATION_STALE');
  });

  it('needs each entry\'s location and exit', () => {
    only(check({ files: edit(VIOLATIONS, (r) => { violation(r, 3).location = {}; }) }), 'PRIVACY_SCHEMA_INVALID');
    only(check({ files: edit(VIOLATIONS, (r) => { delete violation(r, 3).exit; }) }), 'PRIVACY_SCHEMA_INVALID');
  });

  it('fails a closed entry that names no fixing PR, and an entry without a real owner', () => {
    only(check({ files: edit(VIOLATIONS, (r) => { Object.assign(violation(r, 3), { status: 'closed', history: [] }); }) }), 'PRIVACY_CLOSED_WITHOUT_PR');
    only(check({ files: edit(VIOLATIONS, (r) => { violation(r, 3).owner = 'ROUNDS-99-L99'; }) }), 'PRIVACY_OWNERLESS');
    only(check({ files: edit(VIOLATIONS, (r) => { violation(r, 3).rule = 'no-such-rule'; }) }), 'PRIVACY_UNKNOWN_REF');
  });
});

describe('privacy: loosening against the base branch', () => {
  const baseMap = (fn) => edit(FIELD_MAP, fn);

  it('fails a field moved to a looser class, unless a relaxation names a spec change and an approval', () => {
    const base = baseMap((m) => { entry(m, 'pb:applications.company').class = 'Sensitive'; });
    only(check({ base }), 'PRIVACY_RELAXED');
    const approved = edit(POLICY, (p) => { p.relaxations.push({ target: 'pb:applications.company', specChange: 'An example spec change.', approvalRef: { pr: 1 } }); });
    clean(check({ base, files: approved }));
  });

  it('passes tightening', () => {
    clean(check({ base: baseMap((m) => { entry(m, 'pb:offers.annual_bonus_target_pct').class = 'Private'; }) }));
  });

  it('fails a sink rule that allows more, a row that keeps data longer, and a purpose that sends more', () => {
    only(check({ base: edit(POLICY, (p) => { p.matrix.cells.find((c) => c.id === 'private.remote-ai').rule = { decision: 'deny', code: 'EXAMPLE' }; }) }), 'PRIVACY_RELAXED');
    only(check({ base: edit(POLICY, (p) => { p.lifecycle.rows.find((r) => r.id === 'logs-traces').retention.range = [1, 14]; }) }), 'PRIVACY_RELAXED');
    only(check({ base: edit(PURPOSES, (r) => { const p = purpose(r, 'resume.improve'); p.inputs = p.inputs.filter((i) => i.field !== 'pb:resume_variants.data'); }) }), 'PRIVACY_RELAXED');
  });

  it('passes a new input that an input already on the base covers', () => {
    clean(check({
      base: { [PURPOSES]: real.read(PURPOSES) },
      files: edit(PURPOSES, (r) => { purpose(r, 'resume.improve').inputs.push({ field: 'pb:resumes.data#/experience' }); }),
    }));
  });

  it('fails a deleted entry whose id resolves looser on head', () => {
    const findings = check({
      base: { [FIELD_MAP]: real.read(FIELD_MAP) },
      files: edit(FIELD_MAP, (m) => { m.entries = m.entries.filter((e) => !e.id.startsWith('pb:ai_coding_rounds.checkpoints#')); }),
    });
    includes(findings, 'PRIVACY_RELAXED');
    assert.ok(findings.some((f) => f.code === 'PRIVACY_RELAXED' && /hidden_files/.test(f.message)), JSON.stringify(findings, null, 2));
  });

  it('fails a kind change that opens a log case', () => {
    only(check({ base: baseMap((m) => { entry(m, 'pb:offers.user').kind = 'metadata'; }) }), 'PRIVACY_RELAXED');
    only(check({ base: baseMap((m) => { entry(m, 'pb:offers.user').kind = 'content'; }) }), 'PRIVACY_RELAXED');
  });

  it('fails a register entry removed, given a new owner, or moved off its location while open', () => {
    const base = { [VIOLATIONS]: real.read(VIOLATIONS) };
    only(check({ base, files: edit(VIOLATIONS, (r) => { r.entries = r.entries.filter((v) => v.id !== 3); }) }), 'PRIVACY_RELAXED');
    only(check({ base, files: edit(VIOLATIONS, (r) => { violation(r, 3).owner = 'ROUNDS-08-L02'; }) }), 'PRIVACY_RELAXED');
    only(check({ base, files: edit(VIOLATIONS, (r) => { violation(r, 4).location.fields = violation(r, 4).location.fields.slice(1); }) }), 'PRIVACY_RELAXED');
  });

  it('fails a secret pattern removed or changed', () => {
    const PATTERNS = 'contracts/privacy/secret-patterns.json';
    const base = { [PATTERNS]: real.read(PATTERNS) };
    includes(check({ base, files: edit(PATTERNS, (s) => { s.patterns.find((p) => p.id === 'groq-key').regex = 'gsk_[A-Za-z0-9]{40,}'; }) }), 'PRIVACY_RELAXED');
    includes(check({ base, files: edit(PATTERNS, (s) => {
      s.patterns = s.patterns.filter((p) => p.id !== 'groq-key');
      s.fixtures = s.fixtures.filter((x) => x.pattern !== 'groq-key');
      s.nearMisses = s.nearMisses.filter((x) => x.pattern !== 'groq-key');
    }) }), 'PRIVACY_RELAXED');
  });
});

describe('privacy: --review against the spec', () => {
  // A stand-in rounds-review checkout: the committed copy of spec lines
  // 2126 to 2169 at their line numbers.
  function reviewRoot() {
    const dir = tempDir('rounds-review-privacy-');
    const spec = json(POLICY).spec.path;
    fs.mkdirSync(path.join(dir, path.dirname(spec)), { recursive: true });
    fs.writeFileSync(path.join(dir, spec), '\n'.repeat(2125) + fs.readFileSync(path.join(FIXTURES, SPEC_FIXTURE), 'utf8'));
    return dir;
  }

  it('keeps the matrix, the lifecycle table, and the deletion text word for word', () => {
    const root = reviewRoot();
    clean(check({ reviewRoot: root }));
    // The row and its cell change together, so only the spec comparison sees it.
    only(check({ reviewRoot: root, files: edit(POLICY, (p) => {
      p.matrix.rows[0].cells[2] = 'Consent after preview';
      p.matrix.cells.find((c) => c.id === 'private.remote-ai').text = 'Consent after preview';
    }) }), 'PRIVACY_SPEC_MISMATCH');
    only(check({ reviewRoot: root, files: edit(POLICY, (p) => { p.lifecycle.rows[0].cells[1] = 'Forever'; }) }), 'PRIVACY_SPEC_MISMATCH');
    only(check({ reviewRoot: root, files: edit(POLICY, (p) => { p.accountDeletion.text += ' Example.'; }) }), 'PRIVACY_SPEC_MISMATCH');
  });
});
