// Tests for the database ADR rule (ROUNDS-02-L01, DR-0004): the committed
// record, ERD, snapshot, and receipt pass, and each finding code fails a
// fixture copy that breaks one thing.

import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { after, describe, it } from 'node:test';
import { createContext } from '../lib/context.mjs';
import { validate } from '../lib/json-schema.mjs';
import { leafResolver, loadLeafIds } from '../lib/leaf-ids.mjs';
import { CONCERNS, REJECTED } from '../lib/database/record.mjs';
import { TARGET_IDS } from '../lib/database/benchmark.mjs';
import * as db from '../rules/database-adr.mjs';
import * as records from '../rules/decision-records.mjs';
import { REPO_ROOT, cleanup, codes, ctxFor, editJson, editText, fixture, readJson } from './helpers.mjs';

const RECORD = 'docs/decisions/DR-0004-canonical-database.json';
const ADR = 'docs/decisions/DR-0004-canonical-database.md';
const ERD_DOC = 'docs/decisions/DR-0004-erd.md';
const RECORD_SCHEMA = 'docs/decisions/decision-record.schema.json';
const DECISIONS = 'contracts/database/erd-decisions.json';
const DECISIONS_SCHEMA = 'contracts/database/erd-decisions.schema.json';
const ERD = 'contracts/database/erd.json';
const ERD_SCHEMA = 'contracts/database/erd.schema.json';
const SNAPSHOT = 'contracts/database/schema-snapshot.json';
const SNAPSHOT_SCHEMA = 'contracts/database/schema-snapshot.schema.json';
const RECEIPT = 'contracts/database/benchmark.json';
const RECEIPT_SCHEMA = 'contracts/database/benchmark.schema.json';
const MATRIX = 'contracts/authority/matrix.json';
const PACKAGES = 'contracts/authority/packages.json';
const DOCKERFILE = 'pocketbase/Dockerfile';
const MIGRATIONS = 'pocketbase/pb_migrations';

// DR-0004 is a draft until #222's r2 review passes; harness/bench/ratify.py
// sets this to 'ratified' in the ratification commit.
const STATUS = 'draft';
// What a ratified DR-0004 pins (M4): the ERD's written part, the receipt,
// their schemas, and the ADR. The snapshot and the generated ERD are not
// governed; a migration change regenerates them.
const GOVERNED = [DECISIONS, DECISIONS_SCHEMA, RECEIPT, RECEIPT_SCHEMA, ADR];

after(cleanup);

const run = (dir) => db.check(dir, ctxFor(dir));
const only = (findings, code) => assert.deepEqual(codes(findings), [code], JSON.stringify(findings, null, 2));
const includes = (findings, code) => assert.ok(codes(findings).includes(code), JSON.stringify(findings, null, 2));
const edit = (rel, fn) => fixture((d) => editJson(d, rel, fn));
const record = (fn) => edit(RECORD, fn);
const erd = (fn) => edit(ERD, fn);
const receipt = (fn) => edit(RECEIPT, fn);
const decision = (r, concern) => r.decisions.find((d) => d.concern === concern);
const repo = (rel) => readJson(REPO_ROOT, rel);
const sha = (dir, rel) => createHash('sha256').update(fs.readFileSync(path.join(dir, rel))).digest('hex');
const pinIn = (text) => /^ARG PB_VERSION=(\S+)$/m.exec(text)[1];
const entity = (d, id) => d.entities.find((x) => x.id === id);
const target = (rc, id) => rc.targets.find((t) => t.id === id);

// Writes generate()'s outputs into a fixture, as a PR does with --write.
function regen(dir) {
  for (const o of db.generate(dir, ctxFor(dir))) fs.writeFileSync(path.join(dir, o.path), o.content);
}
// Edits the ERD's written part and regenerates, as a PR that changes it does.
const written = (fn) => fixture((d) => { editJson(d, DECISIONS, fn); regen(d); });

describe('database ADR: repository', () => {
  it('passes as committed', () => {
    assert.deepEqual(db.check(REPO_ROOT, createContext(REPO_ROOT, { base: 'none' })), []);
  });

  it('passes on an unmodified fixture copy', () => {
    assert.deepEqual(run(fixture()), []);
  });

  it('validates the record, both parts of the ERD, the snapshot, and the receipt against their schemas', () => {
    for (const [doc, schema] of [[RECORD, RECORD_SCHEMA], [DECISIONS, DECISIONS_SCHEMA], [ERD, ERD_SCHEMA], [SNAPSHOT, SNAPSHOT_SCHEMA], [RECEIPT, RECEIPT_SCHEMA]]) {
      assert.deepEqual(validate(repo(doc), repo(schema)), [], doc);
    }
  });

  it('regenerates the ERD, its document, and the ADR exactly as committed', () => {
    const ctx = createContext(REPO_ROOT, { base: 'none' });
    const out = db.generate(REPO_ROOT, ctx);
    assert.deepEqual(out.map((o) => o.path).sort(), [ERD, ERD_DOC, ADR].sort());
    for (const o of out) assert.equal(o.content, fs.readFileSync(path.join(REPO_ROOT, o.path), 'utf8'), o.path);
  });

  it(`is ${STATUS} as committed, and pins only the ERD's written part, the receipt, their schemas, and the ADR once ratified`, () => {
    const r = repo(RECORD);
    assert.equal(r.status, STATUS);
    assert.equal(r.authorityBoundary, DECISIONS);
    if (STATUS === 'ratified') {
      assert.match(r.approver, /^rounds lane review \(PR #222, r\d+\), \d{4}-\d{2}-\d{2}$/);
      assert.deepEqual(r.approvalRef.governedFiles.map((g) => g.path), GOVERNED);
      for (const g of r.approvalRef.governedFiles) assert.equal(g.sha256, sha(REPO_ROOT, g.path), g.path);
      assert.ok(r.decisions.every((d) => d.status === 'ratified'));
    } else {
      assert.equal(r.approvalRef, null);
      assert.ok(r.decisions.every((d) => d.status === 'draft'));
    }
  });

  it('keeps the ADR free of the generated part, so a migration change leaves its SHA-256 alone', () => {
    const adr = fs.readFileSync(path.join(REPO_ROOT, ADR), 'utf8');
    const snap = repo(SNAPSHOT);
    assert.ok(!adr.includes(snap.revision.commit.slice(0, 7)), 'the ADR names the snapshot revision');
    assert.ok(!adr.includes('erDiagram'), 'the ADR draws the generated ERD');
    assert.match(fs.readFileSync(path.join(REPO_ROOT, ERD_DOC), 'utf8'), new RegExp(snap.revision.commit.slice(0, 7)));
  });

  it('decides all ten concerns, each with one store, one owning process, and one owning leaf', () => {
    const r = repo(RECORD);
    assert.deepEqual(r.decisions.map((d) => d.concern).sort(), [...CONCERNS].sort());
    assert.deepEqual(r.decisions.map((d) => d.id), ['DB1', 'DB2', 'DB3', 'DB4', 'DB5', 'DB6', 'DB7', 'DB8', 'DB9', 'DB10']);
    const stores = new Set(repo(DECISIONS).stores.map((s) => s.id));
    for (const d of r.decisions) {
      assert.ok(stores.has(d.store) || d.store.startsWith('n/a:'), `${d.id} store ${d.store}`);
      for (const k of ['process', 'owningLeaf', 'decision', 'consequences', 'migrationImpact', 'rollbackImpact']) assert.ok(d[k]?.length, `${d.id} ${k}`);
      for (const k of ['alternatives', 'failureModes', 'limits', 'sources']) assert.ok(d[k]?.length, `${d.id} ${k}`);
    }
    assert.equal(decision(r, 'canonical-write-database').store, 'sqlite-data');
    assert.equal(decision(r, 'byte-store').store, 'files');
    assert.equal(decision(r, 'transaction-owner').owningLeaf, 'ROUNDS-02-L02');
  });

  it('evaluates alternatives A to D, chooses one, and records the three rejections with their sources', () => {
    const r = repo(RECORD);
    assert.deepEqual(r.alternativesEvaluated.map((a) => a.id), ['A', 'B', 'C', 'D']);
    assert.deepEqual(r.alternativesEvaluated.filter((a) => a.verdict === 'chosen').map((a) => a.id), ['A']);
    for (const a of r.alternativesEvaluated) for (const k of ['runnerWritePath', 'imageBuild', 'bindings', 'nginxChange', 'reason']) assert.ok(a[k]?.length, `${a.id} ${k}`);
    assert.deepEqual(r.rejected.map((x) => x.id), REJECTED);
    assert.match(r.rejected.find((x) => x.id === 'postgres-pocketbase').source, /^https:\/\/pocketbase\.io\//);
  });

  it('covers every collection on next, the system tables, and the planned tables with their owning leaves and indexes', () => {
    const e = repo(ERD);
    const ids = new Set(e.entities.map((x) => x.id));
    for (const c of repo(SNAPSHOT).collections) assert.ok(ids.has(c.name), c.name);
    for (const t of ['_admins', '_collections', '_externalAuths', '_migrations', '_params']) assert.ok(ids.has(t), t);
    const planned = e.entities.filter((x) => x.status !== 'live');
    for (const x of planned) assert.match(x.owningLeaf, /^ROUNDS-\d{2}[A-Z]?-L\d{2}(\/\w+)?$/, x.id);
    // M2: the keys #19 to #23 build on, and an index that leads with each
    // planned account table's partition.
    const keys = (id) => entity(e, id).indexes.map((i) => `${i.unique ? 'unique ' : ''}${i.columns.join(',')}`);
    assert.deepEqual(keys('change_sets'), ['unique account_id,commit_position', 'unique account_id,command_id']);
    assert.deepEqual(keys('audit_entries'), ['account_id,commit_position']);
    assert.deepEqual(keys('domain_outbox'), ['unique relay_seq', 'unique event_id', 'unique account_id,commit_position,ordinal']);
    assert.deepEqual(keys('account_blobs'), ['unique account_id,sha256']);
    assert.deepEqual(keys('platform_leases'), ['unique name']);
    assert.deepEqual(keys('projector_checkpoints'), ['unique account_id,projector']);
    assert.deepEqual(keys('outbox_cursors'), ['unique consumer']);
    assert.deepEqual(keys('outbox_parked'), ['account_id,consumer']);
    for (const x of planned.filter((p) => p.scope === 'account')) assert.equal(x.partitionIndexed, true, x.id);
    // Containment stores on next, at class level.
    for (const t of ['execution_jobs', 'legacy_artifact_snapshots', 'relation_quarantine', 'share_capabilities', 'share_resolvers', 'share_throttle', 'legacy_share_migration']) {
      assert.equal(entity(e, t).group, 'containment', t);
    }
    // M3: the byte store's file field is protected and read through the gateway.
    assert.match(entity(repo(DECISIONS), 'account_blobs').note, /protected.*gateway route that checks the account/);
  });

  it('gives every relation its cardinality, delete behavior as measured, merge behavior, and authorization, and defines each value', () => {
    const e = repo(ERD);
    assert.ok(e.relations.length >= 80);
    for (const r of e.relations) {
      assert.ok(['cascade', 'restrict', 'unset'].includes(r.onDelete), r.id);
      assert.ok(['none', 'repoint', 'n/a'].includes(r.merge), r.id);
      assert.ok(['many-to-one', 'many-to-many'].includes(r.cardinality), r.id);
      assert.ok(r.authorization, r.id);
    }
    assert.deepEqual(Object.keys(e.semantics.measured).sort(), Object.keys(repo(SNAPSHOT).relationDeleteSemantics).sort());
    assert.deepEqual(Object.keys(repo(DECISIONS).semantics.merge).sort(), ['n/a', 'none', 'repoint']);
  });

  it('cites the audited revision for baseline facts and invariants, and resolves every leaf it names', () => {
    const r = repo(RECORD);
    const resolve = leafResolver(loadLeafIds(createContext(REPO_ROOT, { base: 'none' })));
    for (const b of r.baselineFacts) assert.match(b.citation, /@62d4eae:L\d+(-L\d+)?$/, b.id);
    assert.equal(r.invariants.length, 4);
    for (const i of r.invariants) assert.match(i.site, /@62d4eae:L\d+(-L\d+)?$/, i.id);
    const refs = [r.leaf, ...r.consumers, ...r.prerequisites, ...r.decisions.map((d) => d.owningLeaf), ...r.changes.flatMap((c) => c.dependsOn),
      ...r.credentials.map((c) => c.leaf), ...r.exportGate.flatMap((g) => g.producer)];
    for (const ref of refs) assert.ok(resolve(ref).ok, ref);
    assert.ok(r.prerequisites.includes('ROUNDS-01-L03/S2'));
  });

  it('names the account, privacy, secret, and public-boundary consequences, the superuser, each service identity, and the dedupe scope', () => {
    const r = repo(RECORD);
    assert.deepEqual(Object.keys(r.securityConsequences).sort(), ['account', 'privacy', 'publicBoundary', 'secret']);
    const holders = r.credentials.map((c) => c.holder);
    for (const h of ['superuser', 'execution_service', 'share_resolvers', 'ai_gateway', 'dispatcher_service']) assert.ok(holders.includes(h), h);
    assert.match(r.credentials.find((c) => c.holder === 'superuser').disposition, /No runtime writer uses it/);
    assert.equal(r.credentials.find((c) => c.credential === 'ROUNDS_ADMISSION_SECRET').holder, 'PocketBase and the runner');
    assert.ok(r.credentials.some((c) => c.credential === 'AI_KEY_SECRET'));
    assert.match(decision(r, 'byte-store').dedupe, /one account only/);
    assert.match(r.exposure, /existing \/api\/ pass-through/);
    assert.match(r.exposure, /no new port, hostname, or route outside/);
  });

  it('records the receipt with its synthetic label, the profile, both scales, all five targets, and the defaults with their basis', () => {
    const rc = repo(RECEIPT);
    assert.equal(rc.synthetic, true);
    assert.deepEqual(Object.keys(rc.scales).sort(), ['1', '10']);
    assert.deepEqual(rc.targets.map((t) => t.id), TARGET_IDS);
    for (const k of ['hardware', 'pocketbase', 'k8sLimits', 'emulation', 'revision', 'sharedMachine', 'loadAverageAtStart', 'loadAverageAtEnd']) assert.ok(rc.profile[k], k);
    assert.equal(repo(RECORD).benchmark.result, rc.result);
    assert.equal(repo(RECORD).benchmark.revision, rc.revision);
    assert.equal(rc.seedPlan.fraction, 1);
    // M1: the steady phase measured its own events, after the sweep drained.
    for (const s of Object.values(rc.scales)) assert.ok(s.steady.sweepDrainSeconds >= 0 && s.steady.lagWindow && s.steady.checkpoint.ms >= 0);
    // M7: each default names its target's basis; the bench's restores aren't the floor rehearsal.
    const d = rc.rollbackDefaults;
    assert.deepEqual(d.restoreWithin30Minutes, { met: true, basis: target(rc, 'restore_rto').basis, target: 'restore_rto' });
    assert.equal(d.floorRestoreRehearsed.met, false);
    assert.equal(d.floorRestoreRehearsed.owner, 'ROUNDS-32-L03');
  });

  it('ratifies the PocketBase line, keeps the pin at ratification as history, and states a benchmarked patch on that line', () => {
    const r = repo(RECORD);
    const pin = pinIn(fs.readFileSync(path.join(REPO_ROOT, DOCKERFILE), 'utf8'));
    const line = (v) => v.split('.').slice(0, 2).join('.');
    assert.equal(r.pocketbase.line, '0.22');
    assert.equal(line(pin), r.pocketbase.line);
    assert.equal(r.pocketbase.pinAtRatification, pin);
    const ran = repo(RECEIPT).profile.pocketbase.version;
    assert.equal(line(ran), r.pocketbase.line);
    if (ran !== r.pocketbase.pinAtRatification) {
      assert.ok(r.pocketbase.benchmark.includes(ran) && r.pocketbase.benchmark.includes(r.pocketbase.pinAtRatification), 'the version difference names both');
    }
    assert.equal(r.pocketbase.triggers.length, 3);
    assert.match(r.pocketbase.countedAt, /^[0-9a-f]{40}$/);
    for (const b of r.pocketbase.breakSites) assert.ok(b.upstream, b.id);
  });

  it('fills #16\'s storage and target_path cells from DR-0004', () => {
    const rows = repo(MATRIX).rows;
    assert.ok(!rows.some((r) => r.storage === 'pending:ROUNDS-02-L01'));
    assert.ok(!repo(PACKAGES).packages.some((p) => p.target_path === 'pending:ROUNDS-02-L01'));
    for (const r of rows) assert.match(r.storage, /^(DR-0004@1:[a-z-]+(\+[a-z-]+)*|n\/a:.+|blocked:OD-\d+)$/, r.id);
  });
});

describe('database ADR: negative controls', () => {
  it('fails DB_RECORD_MISSING and DB_RECORD_INVALID', () => {
    only(run(fixture((d) => fs.rmSync(path.join(d, RECORD)))), 'DB_RECORD_MISSING');
    only(run(fixture((d) => fs.rmSync(path.join(d, ERD)))), 'DB_RECORD_MISSING');
    only(run(fixture((d) => fs.rmSync(path.join(d, DECISIONS)))), 'DB_RECORD_MISSING');
    only(run(fixture((d) => fs.writeFileSync(path.join(d, RECORD), '{ not json'))), 'DB_RECORD_INVALID');
  });

  it('fails DB_RECORD_INCOMPLETE for a missing decision, field, alternative, invariant, or exemption', () => {
    only(run(record((r) => { r.decisions = r.decisions.filter((d) => d.concern !== 'outbox-projectors'); })), 'DB_RECORD_INCOMPLETE');
    for (const k of ['store', 'process', 'owningLeaf', 'failureModes', 'limits']) {
      only(run(record((r) => { delete decision(r, 'transaction-owner')[k]; })), 'DB_RECORD_INCOMPLETE');
    }
    only(run(record((r) => { r.alternativesEvaluated = r.alternativesEvaluated.filter((a) => a.id !== 'B'); })), 'DB_RECORD_INCOMPLETE');
    only(run(record((r) => { r.rejected = r.rejected.filter((x) => x.id !== 'fastapi-sqlite'); })), 'DB_RECORD_INCOMPLETE');
    only(run(record((r) => { r.invariants.pop(); })), 'DB_RECORD_INCOMPLETE');
    only(run(record((r) => { r.invariants[0].mechanism = 'hope'; })), 'DB_RECORD_INCOMPLETE');
    only(run(record((r) => { delete r.foundationExemption; })), 'DB_RECORD_INCOMPLETE');
    only(run(record((r) => { r.exportGate[1].producer = []; })), 'DB_RECORD_INCOMPLETE');
    only(run(record((r) => { r.storagePlan[0].sizing = ''; })), 'DB_RECORD_INCOMPLETE');
    only(run(record((r) => { delete r.pocketbase.rollbackBoundary; })), 'DB_RECORD_INCOMPLETE');
    only(run(record((r) => { delete r.pocketbase.countedAt; })), 'DB_RECORD_INCOMPLETE');
    only(run(record((r) => { r.pocketbase.breakSites[0].upstream = ''; })), 'DB_RECORD_INCOMPLETE');
    only(run(record((r) => { r.containment = r.containment.filter((c) => !c.entities.includes('share_throttle')); })), 'DB_RECORD_INCOMPLETE');
  });

  it('fails DB_TWO_AUTHORITIES for one concern decided twice, two stores in a decision, two chosen alternatives, or an entity written twice', () => {
    // The second decision for one concern leaves its own concern undecided, too.
    const twice = run(record((r) => { decision(r, 'aggregate-version-model').concern = 'transaction-owner'; }));
    assert.deepEqual(codes(twice), ['DB_RECORD_INCOMPLETE', 'DB_TWO_AUTHORITIES']);
    only(run(record((r) => { decision(r, 'canonical-write-database').store = 'sqlite-data+files'; })), 'DB_TWO_AUTHORITIES');
    only(run(record((r) => { r.alternativesEvaluated.find((a) => a.id === 'C').verdict = 'chosen'; })), 'DB_TWO_AUTHORITIES');
    only(run(written((d) => { d.entities.push({ ...entity(d, 'offers') }); })), 'DB_TWO_AUTHORITIES');
    only(run(written((d) => { d.relations.push({ ...d.relations[0] }); })), 'DB_TWO_AUTHORITIES');
    // An invariant belongs to its row's command owner in #16's matrix.
    only(run(record((r) => { r.invariants.find((x) => x.row === 'offer').owningLeaf = 'ROUNDS-02-L02'; })), 'DB_TWO_AUTHORITIES');
  });

  it('fails DB_UNKNOWN_REF for an unknown store, leaf, row, entity, relation end, citation, or counted commit', () => {
    only(run(record((r) => { decision(r, 'canonical-write-database').store = 'postgres'; })), 'DB_UNKNOWN_REF');
    only(run(record((r) => { decision(r, 'outbox-projectors').owningLeaf = 'ROUNDS-99-L01'; })), 'DB_UNKNOWN_REF');
    only(run(record((r) => { r.invariants[0].row = 'no-such-row'; })), 'DB_UNKNOWN_REF');
    only(run(record((r) => { r.invariants[0].site = 'frontend/src/applications/api.ts@62d4eae:L9000-L9001'; })), 'DB_UNKNOWN_REF');
    only(run(record((r) => { r.baselineFacts[0].citation = 'no/such/file.ts@62d4eae:L1'; })), 'DB_UNKNOWN_REF');
    only(run(record((r) => { r.containment[0].entities.push('no_such_table'); })), 'DB_UNKNOWN_REF');
    only(run(record((r) => { r.changes[0].dependsOn.push('ROUNDS-99-L09'); })), 'DB_UNKNOWN_REF');
    only(run(record((r) => { r.pocketbase.countedAt = 'f'.repeat(40); })), 'DB_UNKNOWN_REF');
    only(run(erd((e) => { e.relations[0].to = 'no_such_table'; })), 'DB_UNKNOWN_REF');
    only(run(written((d) => { entity(d, 'account_blobs').owningLeaf = 'ROUNDS-98-L01'; })), 'DB_UNKNOWN_REF');
    // Written fields for a table or a relation the snapshot doesn't have.
    only(run(written((d) => { d.entities.push({ ...entity(d, 'offers'), id: 'no_such_table' }); })), 'DB_UNKNOWN_REF');
    only(run(written((d) => { d.relations.push({ id: 'offers.no_such_field', merge: 'none' }); })), 'DB_UNKNOWN_REF');
    only(run(edit(MATRIX, (m) => { m.rows[0].storage = 'DR-0004@1:postgres'; })), 'DB_UNKNOWN_REF');
    // A citation in the docs names a decision, store, or entity that exists.
    const cite = (text) => fixture((d) => fs.writeFileSync(path.join(d, 'docs/example-db.md'), text));
    assert.deepEqual(run(cite('Cite DR-0004@1:DB2, DR-0004@1:sqlite-data, and DR-0004@1:account_blobs.\n')), []);
    only(run(cite('Cite DR-0004@1:DB99.\n')), 'DB_UNKNOWN_REF');
  });

  it('fails DB_VERSION_MISMATCH for an ERD, a receipt, a result, or a cell at another revision', () => {
    only(run(erd((e) => { e.revision = 2; })), 'DB_VERSION_MISMATCH');
    only(run(written((d) => { d.revision = 2; })), 'DB_VERSION_MISMATCH');
    only(run(erd((e) => { e.snapshot.revision = '0'.repeat(40); })), 'DB_VERSION_MISMATCH');
    only(run(record((r) => { r.benchmark.result = r.benchmark.result === 'pass' ? 'fail' : 'pass'; })), 'DB_VERSION_MISMATCH');
    only(run(edit(MATRIX, (m) => { m.rows[0].storage = 'DR-0004@2:sqlite-data'; })), 'DB_VERSION_MISMATCH');
    only(run(fixture((d) => fs.writeFileSync(path.join(d, 'docs/example-db.md'), 'Cite DR-0004@2:DB2.\n'))), 'DB_VERSION_MISMATCH');
    // L5 (f): the receipt shares the record's revision counter.
    only(run(receipt((rc) => { rc.revision = 2; })), 'DB_VERSION_MISMATCH');
  });

  describe('the PocketBase line (M6)', () => {
    const ran = repo(RECEIPT).profile.pocketbase.version;
    const at = repo(RECORD).pocketbase.pinAtRatification;
    const pinTo = (d, v) => editText(d, DOCKERFILE, (s) => s.replace(/^ARG PB_VERSION=\S+$/m, `ARG PB_VERSION=${v}`));
    const nextPatch = (v) => `0.22.${Number(v.split('.')[2]) + 1}`;

    it('passes a patch on the line with no record change: a pin change, not a revision', () => {
      assert.deepEqual(run(fixture((d) => pinTo(d, nextPatch(at)))), []);
    });

    it('fails a pin or a receipt on another line, and a line decision 9 doesn\'t name', () => {
      only(run(fixture((d) => pinTo(d, '0.23.0'))), 'DB_VERSION_MISMATCH');
      only(run(receipt((rc) => { rc.profile.pocketbase.version = '0.23.0'; rc.profile.pocketbase.dockerfilePin.PB_VERSION = '0.23.0'; })), 'DB_VERSION_MISMATCH');
      // The review's case: the pin, the record, and the receipt all moved to
      // 0.23, while decision 9 still retains the 0.22 line.
      only(run(fixture((d) => {
        pinTo(d, '0.23.0');
        editJson(d, RECORD, (r) => { Object.assign(r.pocketbase, { line: '0.23', pinAtRatification: '0.23.0' }); });
        editJson(d, RECEIPT, (rc) => { rc.profile.pocketbase.version = '0.23.0'; rc.profile.pocketbase.dockerfilePin.PB_VERSION = '0.23.0'; });
      })), 'DB_VERSION_MISMATCH');
      only(run(record((r) => { r.pocketbase.line = '0.23'; })), 'DB_VERSION_MISMATCH');
      only(run(fixture((d) => editJson(d, SNAPSHOT, (s) => { s.pocketbaseVersion = '0.23.0'; }))), 'DB_VERSION_MISMATCH');
    });

    it('fails closed when the Dockerfile\'s pin can\'t be read (L5 a)', () => {
      only(run(fixture((d) => editText(d, DOCKERFILE, (s) => s.replace(/^ARG PB_VERSION=/m, 'ARG POCKETBASE_VERSION=')))), 'DB_VERSION_MISMATCH');
    });

    it('requires a note naming both versions when the receipt ran another patch than the pin at ratification (L5 e)', () => {
      const other = nextPatch(ran);
      const moved = (note) => fixture((d) => {
        pinTo(d, other);
        editJson(d, RECORD, (r) => { r.pocketbase.pinAtRatification = other; if (note) r.pocketbase.benchmark = note; else delete r.pocketbase.benchmark; });
      });
      only(run(moved(null)), 'DB_VERSION_MISMATCH');
      only(run(moved('x')), 'DB_VERSION_MISMATCH');
      assert.deepEqual(run(moved(`The receipt ran on ${ran}, before the pin moved to ${other}; the numbers are ${ran}'s.`)), []);
    });
  });

  it('fails DB_CHANGE_INCOMPLETE for a changed authority without its entry, order, or rollback', () => {
    only(run(record((r) => { r.changes = r.changes.filter((c) => c.authority !== 'byte-store'); })), 'DB_CHANGE_INCOMPLETE');
    only(run(record((r) => { delete r.changes.find((c) => c.authority === 'pocketbase-version').rollback; })), 'DB_CHANGE_INCOMPLETE');
    only(run(record((r) => { r.changes.find((c) => c.authority === 'containment-stores').dependsOn = []; })), 'DB_CHANGE_INCOMPLETE');
    // N7: ratifying a containment store in place comes after the leaf that built it.
    only(run(record((r) => { const c = r.changes.find((x) => x.authority === 'containment-stores'); c.dependsOn = c.dependsOn.filter((x) => x !== 'ROUNDS-00B-L02'); })),
      'DB_CHANGE_INCOMPLETE');
  });

  it('fails DB_ERD_DELETE_MISSING for a relation without delete or merge behavior', () => {
    only(run(written((d) => { delete d.relations[0].merge; })), 'DB_ERD_DELETE_MISSING');
    only(run(written((d) => { d.relations = d.relations.filter((r) => r.id !== 'offers.application'); })), 'DB_ERD_DELETE_MISSING');
    const plannedRelation = { id: 'change_sets.aggregate', status: 'planned', from: 'change_sets', field: 'aggregate', to: 'domain_outbox',
      cardinality: 'many-to-one', required: true, merge: 'none', authorization: 'server' };
    only(run(written((d) => { d.relations.push(plannedRelation); })), 'DB_ERD_DELETE_MISSING');
    assert.deepEqual(run(written((d) => { d.relations.push({ ...plannedRelation, onDelete: 'purge' }); })), []);
    only(run(erd((e) => { delete e.relations[0].onDelete; })), 'DB_ERD_DELETE_MISSING');
  });

  it('fails DB_ERD_UNCOVERED and DB_ERD_UNRESOLVED for collections the ERD has no written fields for', () => {
    only(run(written((d) => { d.entities = d.entities.filter((x) => x.id !== 'todos'); })), 'DB_ERD_UNCOVERED');
    const migration = (body) => fixture((d) => fs.writeFileSync(path.join(d, MIGRATIONS, '1900000001_test_collection.js'), body));
    const create = (name) => `migrate((db) => {\n  const dao = new Dao(db);\n  dao.saveCollection(new Collection({ name: ${name}, type: "base", schema: [] }));\n}, (db) => {});\n`;
    // A migration the snapshot hasn't seen is stale as well (M4).
    assert.deepEqual(codes(run(migration(create('"rogue_table"')))), ['DB_ERD_STALE', 'DB_ERD_UNCOVERED']);
    assert.deepEqual(codes(run(migration(create('`rogue_${"table"}`')))), ['DB_ERD_STALE', 'DB_ERD_UNRESOLVED']);
    // A planned table needs no new written fields when its migration lands.
    assert.deepEqual(codes(run(migration(create('"change_sets"')))), ['DB_ERD_STALE']);
  });

  it('fails DB_ERD_STALE for a migration the snapshot hasn\'t seen, changed, or lost (M4)', () => {
    const latest = fs.readdirSync(path.join(REPO_ROOT, MIGRATIONS)).filter((f) => f.endsWith('.js')).sort().at(-1);
    // The review's case: a new migration that adds a relation field and an
    // index to an existing collection.
    const addField = 'migrate((db) => {\n  const dao = new Dao(db);\n  const c = dao.findCollectionByNameOrId("offers");\n  c.schema.addField(new SchemaField({ name: "next_offer", type: "relation", options: { collectionId: "offers", maxSelect: 1 } }));\n  c.indexes.push("CREATE INDEX idx_offers_next ON offers (next_offer)");\n  dao.saveCollection(c);\n}, (db) => {});\n';
    only(run(fixture((d) => fs.writeFileSync(path.join(d, MIGRATIONS, '1900000002_offers_next.js'), addField))), 'DB_ERD_STALE');
    const changed = fixture((d) => editText(d, `${MIGRATIONS}/${latest}`, (s) => `${s}// changed\n`));
    only(run(changed), 'DB_ERD_STALE');
    only(run(fixture((d) => fs.rmSync(path.join(d, MIGRATIONS, latest)))), 'DB_ERD_STALE');
    // Regenerating the snapshot clears it, with no revision of the record.
    const regenerated = fixture((d) => {
      editText(d, `${MIGRATIONS}/${latest}`, (s) => `${s}// changed\n`);
      editJson(d, SNAPSHOT, (s) => { s.migrations.find((m) => m.file === latest).sha256 = sha(d, `${MIGRATIONS}/${latest}`); });
    });
    assert.deepEqual(run(regenerated), []);
  });

  it('fails DB_ERD_INCOMPLETE and DB_ERD_INVALID for an entity without its partition, its partition index, or with a bad shape', () => {
    only(run(written((d) => { entity(d, 'change_sets').partition = null; })), 'DB_ERD_INCOMPLETE');
    // M2: a planned account table needs an index that leads with its partition.
    only(run(written((d) => { entity(d, 'change_sets').indexes = [{ name: 'idx_change_sets_seq', unique: true, columns: ['commit_position'] }]; })), 'DB_ERD_INCOMPLETE');
    only(run(written((d) => { delete entity(d, 'offers').purge; })), 'DB_ERD_INCOMPLETE');
    only(run(erd((e) => { delete entity(e, 'offers').purge; })), 'DB_ERD_INCOMPLETE');
    only(run(written((d) => { entity(d, 'offers').scope = 'everyone'; })), 'DB_ERD_INVALID');
    // A live table's mechanical fields come from the snapshot, never the written part.
    only(run(written((d) => { entity(d, 'offers').indexes = []; })), 'DB_ERD_INVALID');
    // N6: an entity live in the snapshot but planned in the ERD.
    only(run(erd((e) => { Object.assign(entity(e, 'todos'), { status: 'planned', owningLeaf: 'ROUNDS-02-L04' }); })), 'DB_ERD_INVALID');
  });

  it('passes a planned table that goes live with no change to its written fields', () => {
    // The snapshot gains the table; the written part keeps it as planned.
    const live = fixture((d) => {
      editJson(d, SNAPSHOT, (s) => {
        const todos = s.collections.find((c) => c.name === 'todos');
        s.collections.push({ ...todos, name: 'platform_leases', fields: todos.fields.filter((f) => f.type !== 'relation'), indexes: [] });
      });
      regen(d);
    });
    assert.deepEqual(run(live), []);
    assert.equal(entity(readJson(live, ERD), 'platform_leases').status, 'live');
  });

  it('fails DB_BENCH_INCOMPLETE for a missing receipt, label, profile field, scale, target, floor, or extrapolation', () => {
    only(run(fixture((d) => fs.rmSync(path.join(d, RECEIPT)))), 'DB_BENCH_INCOMPLETE');
    includes(run(receipt((rc) => { rc.synthetic = false; })), 'DB_BENCH_INCOMPLETE');
    only(run(receipt((rc) => { delete rc.profile.hardware; })), 'DB_BENCH_INCOMPLETE');
    only(run(receipt((rc) => { delete rc.scales['10']; })), 'DB_BENCH_INCOMPLETE');
    includes(run(receipt((rc) => { rc.targets = rc.targets.filter((t) => t.id !== 'restore_rto'); })), 'DB_BENCH_INCOMPLETE');
    only(run(receipt((rc) => { rc.seedPlan.fraction = 0.5; })), 'DB_BENCH_INCOMPLETE');
    // M7: the schema requires each default's basis.
    only(run(receipt((rc) => { delete rc.rollbackDefaults.restoreWithin30Minutes.basis; })), 'DB_BENCH_INCOMPLETE');
  });

  it('fails DB_BENCH_MISS_UNRECORDED for a miss with no consequence, and DB_BENCH_INVALID for a miss reported as a pass', () => {
    const miss = (consequence) => fixture((d) => {
      editJson(d, RECEIPT, (rc) => {
        rc.scales['10'].steady.relayLagMs.p95 = 9000;
        Object.assign(target(rc, 'projection_lag_p95'), { value: 9000, result: 'fail', consequence });
        rc.result = 'fail';
      });
      editJson(d, RECORD, (r) => { r.benchmark.result = 'fail'; });
    });
    only(run(miss('unrecorded')), 'DB_BENCH_MISS_UNRECORDED');
    assert.deepEqual(run(miss('The relay batches differently, or another authority comes before #19.')), []);
    only(run(receipt((rc) => { rc.scales['10'].freeze.seconds = 4000; target(rc, 'write_freeze').value = 4000; })), 'DB_BENCH_INVALID');
    // N6: a passing receipt with a failed target.
    only(run(receipt((rc) => { Object.assign(target(rc, 'projection_lag_p95'), { result: 'fail', consequence: 'The relay batches differently.' }); })), 'DB_BENCH_INVALID');
  });

  it('fails DB_BENCH_INVALID for a target off its unit, limit, measurement, or basis, a default off its target, or a recorded pin off the binary', () => {
    // L5 (c): the unit and limit are the spec's.
    only(run(receipt((rc) => { Object.assign(target(rc, 'read_your_writes'), { unit: 's', limit: 5 }); })), 'DB_BENCH_INVALID');
    // L5 (d): the value is what the scales measured.
    only(run(receipt((rc) => { target(rc, 'projection_lag_p95').value = 500; })), 'DB_BENCH_INVALID');
    // L5 (b): an extrapolation feeds the restore target, so it isn't measured.
    only(run(receipt((rc) => { target(rc, 'restore_rto').basis = 'measured'; rc.rollbackDefaults.restoreWithin30Minutes.basis = 'measured'; })), 'DB_BENCH_INVALID');
    includes(run(receipt((rc) => { rc.extrapolations[0].target = 'write_freeze'; })), 'DB_BENCH_INCOMPLETE');
    // M7: a default carries its target's basis and verdict.
    only(run(receipt((rc) => { rc.rollbackDefaults.restoreWithin30Minutes.basis = 'measured'; })), 'DB_BENCH_INVALID');
    only(run(receipt((rc) => { rc.rollbackDefaults.freezeUnder15Minutes.met = false; })), 'DB_BENCH_INVALID');
    only(run(receipt((rc) => { rc.rollbackDefaults.floorRestoreRehearsed.met = true; })), 'DB_BENCH_INVALID');
    // N6: the Dockerfile pin the run recorded differs from the binary it ran.
    only(run(receipt((rc) => { rc.profile.pocketbase.dockerfilePin.PB_VERSION = '0.22.99'; })), 'DB_BENCH_INVALID');
  });

  it('fails DB_SECURITY_INCOMPLETE for a credential or service identity without its disposition, or the byte store without its dedupe scope', () => {
    only(run(record((r) => { r.credentials = r.credentials.filter((c) => c.holder !== 'execution_service'); })), 'DB_SECURITY_INCOMPLETE');
    only(run(record((r) => { r.credentials.find((c) => c.holder === 'superuser').disposition = ''; })), 'DB_SECURITY_INCOMPLETE');
    only(run(record((r) => { delete decision(r, 'byte-store').dedupe; })), 'DB_SECURITY_INCOMPLETE');
  });

  it('fails DB_STORAGE_PENDING for a storage cell or a target path still pending this leaf', () => {
    only(run(edit(MATRIX, (m) => { m.rows[3].storage = 'pending:ROUNDS-02-L01'; })), 'DB_STORAGE_PENDING');
    only(run(edit(PACKAGES, (p) => { p.packages[0].target_path = 'pending:ROUNDS-02-L01'; })), 'DB_STORAGE_PENDING');
  });
});

// #15's decision-records rule checks every record, DR-0004 included: its
// owner, its packages, its leaves, its supersession links, and, once
// ratified, the pins of its governed files.
describe('database ADR: the record checks every decision record gets', () => {
  const runRecords = (dir) => records.check(dir, ctxFor(dir));
  const recordOnly = (findings, code) => assert.deepEqual(codes(findings), [code], JSON.stringify(findings, null, 2));
  const ratify = (paths) => (d) => editJson(d, RECORD, (r) => {
    Object.assign(r, { status: 'ratified', approver: 'a reviewer', approvalRef: { pr: 1, governedFiles: paths.map((p) => ({ path: p, sha256: sha(d, p) })) } });
  });

  it('passes DR-0004 as committed', () => {
    assert.deepEqual(runRecords(fixture()), []);
  });

  it('fails a missing owner, an unknown package or leaf, and a revision without its supersession link', () => {
    recordOnly(runRecords(record((r) => { delete r.owner; })), 'DR_RECORD_INCOMPLETE');
    recordOnly(runRecords(record((r) => { r.affectedPackages.push('no-such-package'); })), 'DR_UNKNOWN_PACKAGE');
    recordOnly(runRecords(record((r) => { r.consumers.push('ROUNDS-99-L01'); })), 'VOCAB_UNRESOLVED_REF');
    recordOnly(runRecords(record((r) => { r.revision = 2; })), 'DR_SUPERSEDES_INVALID');
    recordOnly(runRecords(record((r) => { r.decisions[0].alternatives = []; })), 'DR_RECORD_INCOMPLETE');
  });

  it('ratified, pins its five governed files, and a migration change that regenerates leaves the pins alone (M4)', () => {
    assert.deepEqual(runRecords(fixture(ratify(GOVERNED))), []);
    recordOnly(runRecords(fixture(ratify(GOVERNED.filter((p) => p !== DECISIONS)))), 'DR_RECORD_INCOMPLETE');
    // A written field changes: the pinned written part goes stale.
    recordOnly(runRecords(fixture((d) => { ratify(GOVERNED)(d); editJson(d, DECISIONS, (x) => { entity(x, 'offers').writers = 'someone else'; }); })), 'DR_APPROVAL_STALE');
    // The generated part and the snapshot change: nothing pinned moves. The
    // ADR renders its ratified header first, as the ratification commit does.
    const migrated = fixture((d) => {
      editJson(d, RECORD, (r) => Object.assign(r, { status: 'ratified', approver: 'a reviewer', approvalRef: { pr: 1, governedFiles: [] } }));
      regen(d);
      ratify(GOVERNED)(d);
      editJson(d, SNAPSHOT, (s) => { s.collections.find((c) => c.name === 'offers').indexes.push({ name: 'idx_offers_next', unique: false, columns: ['offers.application'] }); });
      regen(d);
    });
    assert.deepEqual(runRecords(migrated), []);
    assert.deepEqual(run(migrated), []);
  });
});
