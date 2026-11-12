// Tests for the database ADR rule (ROUNDS-02-L01, DR-0004): the committed
// record, ERD, snapshot, and receipt pass, and each finding code fails a
// fixture copy that breaks one thing.

import assert from 'node:assert/strict';
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
const RECORD_SCHEMA = 'docs/decisions/decision-record.schema.json';
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
const pinIn = (text) => /^ARG PB_VERSION=(\S+)$/m.exec(text)[1];

describe('database ADR: repository', () => {
  it('passes as committed', () => {
    assert.deepEqual(db.check(REPO_ROOT, createContext(REPO_ROOT, { base: 'none' })), []);
  });

  it('passes on an unmodified fixture copy', () => {
    assert.deepEqual(run(fixture()), []);
  });

  it('validates the record, the ERD, the snapshot, and the receipt against their schemas', () => {
    for (const [doc, schema] of [[RECORD, RECORD_SCHEMA], [ERD, ERD_SCHEMA], [SNAPSHOT, SNAPSHOT_SCHEMA], [RECEIPT, RECEIPT_SCHEMA]]) {
      assert.deepEqual(validate(repo(doc), repo(schema)), [], doc);
    }
  });

  it('regenerates the ERD and the ADR exactly as committed', () => {
    const ctx = createContext(REPO_ROOT, { base: 'none' });
    const out = db.generate(REPO_ROOT, ctx);
    assert.deepEqual(out.map((o) => o.path).sort(), [ERD, ADR]);
    for (const o of out) assert.equal(o.content, fs.readFileSync(path.join(REPO_ROOT, o.path), 'utf8'), o.path);
  });

  it('decides all ten concerns, each with one store, one owning process, and one owning leaf', () => {
    const r = repo(RECORD);
    assert.deepEqual(r.decisions.map((d) => d.concern).sort(), [...CONCERNS].sort());
    assert.deepEqual(r.decisions.map((d) => d.id), ['DB1', 'DB2', 'DB3', 'DB4', 'DB5', 'DB6', 'DB7', 'DB8', 'DB9', 'DB10']);
    const stores = new Set(repo(ERD).stores.map((s) => s.id));
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

  it('covers every collection on next, the system tables, and the planned tables with their owning leaves', () => {
    const e = repo(ERD);
    const ids = new Set(e.entities.map((x) => x.id));
    for (const c of repo(SNAPSHOT).collections) assert.ok(ids.has(c.name), c.name);
    for (const t of ['_admins', '_collections', '_externalAuths', '_migrations', '_params']) assert.ok(ids.has(t), t);
    const planned = e.entities.filter((x) => x.status !== 'live');
    for (const x of planned) assert.match(x.owningLeaf, /^ROUNDS-\d{2}[A-Z]?-L\d{2}(\/\w+)?$/, x.id);
    for (const t of ['change_sets', 'audit_entries', 'domain_outbox', 'platform_leases', 'projector_checkpoints', 'account_system_state', 'account_blobs']) {
      assert.ok(planned.some((x) => x.id === t), t);
    }
    // Containment stores on next, at class level.
    for (const t of ['execution_jobs', 'legacy_artifact_snapshots', 'relation_quarantine', 'share_capabilities', 'share_resolvers', 'share_throttle', 'legacy_share_migration']) {
      assert.equal(e.entities.find((x) => x.id === t).group, 'containment', t);
    }
  });

  it('gives every relation its cardinality, delete behavior as measured, merge behavior, and authorization', () => {
    const e = repo(ERD);
    assert.ok(e.relations.length >= 80);
    for (const r of e.relations) {
      assert.ok(['cascade', 'restrict', 'unset'].includes(r.onDelete), r.id);
      assert.ok(['none', 'repoint', 'n/a'].includes(r.merge), r.id);
      assert.ok(['many-to-one', 'many-to-many'].includes(r.cardinality), r.id);
      assert.ok(r.authorization, r.id);
    }
    assert.deepEqual(Object.keys(e.semantics.measured).sort(), Object.keys(repo(SNAPSHOT).relationDeleteSemantics).sort());
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
  });

  it('names the account, privacy, secret, and public-boundary consequences, the superuser, each service identity, and the dedupe scope', () => {
    const r = repo(RECORD);
    assert.deepEqual(Object.keys(r.securityConsequences).sort(), ['account', 'privacy', 'publicBoundary', 'secret']);
    const holders = r.credentials.map((c) => c.holder);
    for (const h of ['superuser', 'execution_service', 'share_resolvers', 'ai_gateway', 'dispatcher_service']) assert.ok(holders.includes(h), h);
    assert.match(r.credentials.find((c) => c.holder === 'superuser').disposition, /No runtime writer uses it/);
    assert.match(decision(r, 'byte-store').dedupe, /one account only/);
    assert.match(r.exposure, /existing \/api\/ pass-through/);
    assert.match(r.exposure, /no new port, hostname, or route outside/);
  });

  it('records the receipt with its synthetic label, the profile, both scales, and all five targets', () => {
    const rc = repo(RECEIPT);
    assert.equal(rc.synthetic, true);
    assert.deepEqual(Object.keys(rc.scales).sort(), ['1', '10']);
    assert.deepEqual(rc.targets.map((t) => t.id), TARGET_IDS);
    for (const k of ['hardware', 'pocketbase', 'k8sLimits', 'emulation', 'revision', 'sharedMachine']) assert.ok(rc.profile[k], k);
    assert.equal(repo(RECORD).benchmark.result, rc.result);
    assert.equal(rc.seedPlan.fraction, 1);
  });

  it('pins the Dockerfile\'s PocketBase and states a benchmarked version on its minor line', () => {
    const r = repo(RECORD);
    const pin = pinIn(fs.readFileSync(path.join(REPO_ROOT, DOCKERFILE), 'utf8'));
    assert.equal(r.pocketbase.pin, pin);
    const ran = repo(RECEIPT).profile.pocketbase.version;
    assert.equal(ran.split('.').slice(0, 2).join('.'), pin.split('.').slice(0, 2).join('.'));
    if (ran !== pin) assert.ok(r.pocketbase.benchmark, 'the version difference is stated');
    assert.equal(r.pocketbase.triggers.length, 3);
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
    only(run(record((r) => { r.pocketbase.breakSites[0].upstream = ''; })), 'DB_RECORD_INCOMPLETE');
    only(run(record((r) => { r.containment = r.containment.filter((c) => !c.entities.includes('share_throttle')); })), 'DB_RECORD_INCOMPLETE');
  });

  it('fails DB_TWO_AUTHORITIES for one concern decided twice, two stores in a decision, two chosen alternatives, or an entity listed twice', () => {
    // The second decision for one concern leaves its own concern undecided, too.
    const twice = run(record((r) => { decision(r, 'aggregate-version-model').concern = 'transaction-owner'; }));
    assert.deepEqual(codes(twice), ['DB_RECORD_INCOMPLETE', 'DB_TWO_AUTHORITIES']);
    only(run(record((r) => { decision(r, 'canonical-write-database').store = 'sqlite-data+files'; })), 'DB_TWO_AUTHORITIES');
    only(run(record((r) => { r.alternativesEvaluated.find((a) => a.id === 'C').verdict = 'chosen'; })), 'DB_TWO_AUTHORITIES');
    only(run(erd((e) => { e.entities.push({ ...e.entities.find((x) => x.id === 'offers') }); })), 'DB_TWO_AUTHORITIES');
    // An invariant belongs to its row's command owner in #16's matrix.
    only(run(record((r) => { r.invariants.find((x) => x.row === 'offer').owningLeaf = 'ROUNDS-02-L02'; })), 'DB_TWO_AUTHORITIES');
  });

  it('fails DB_UNKNOWN_REF for an unknown store, leaf, row, entity, relation end, or citation', () => {
    only(run(record((r) => { decision(r, 'canonical-write-database').store = 'postgres'; })), 'DB_UNKNOWN_REF');
    only(run(record((r) => { decision(r, 'outbox-projectors').owningLeaf = 'ROUNDS-99-L01'; })), 'DB_UNKNOWN_REF');
    only(run(record((r) => { r.invariants[0].row = 'no-such-row'; })), 'DB_UNKNOWN_REF');
    only(run(record((r) => { r.invariants[0].site = 'frontend/src/applications/api.ts@62d4eae:L9000-L9001'; })), 'DB_UNKNOWN_REF');
    only(run(record((r) => { r.baselineFacts[0].citation = 'no/such/file.ts@62d4eae:L1'; })), 'DB_UNKNOWN_REF');
    only(run(record((r) => { r.containment[0].entities.push('no_such_table'); })), 'DB_UNKNOWN_REF');
    only(run(record((r) => { r.changes[0].dependsOn.push('ROUNDS-99-L09'); })), 'DB_UNKNOWN_REF');
    only(run(erd((e) => { e.relations[0].to = 'no_such_table'; })), 'DB_UNKNOWN_REF');
    only(run(erd((e) => { e.entities.find((x) => x.id === 'account_blobs').owningLeaf = 'ROUNDS-98-L01'; })), 'DB_UNKNOWN_REF');
    only(run(edit(MATRIX, (m) => { m.rows[0].storage = 'DR-0004@1:postgres'; })), 'DB_UNKNOWN_REF');
    // A citation in the docs names a decision, store, or entity that exists.
    const cite = (text) => fixture((d) => fs.writeFileSync(path.join(d, 'docs/example-db.md'), text));
    assert.deepEqual(run(cite('Cite DR-0004@1:DB2, DR-0004@1:sqlite-data, and DR-0004@1:account_blobs.\n')), []);
    only(run(cite('Cite DR-0004@1:DB99.\n')), 'DB_UNKNOWN_REF');
  });

  it('fails DB_VERSION_MISMATCH for a pin, an ERD, a receipt, a result, or a cell at another version', () => {
    only(run(record((r) => { r.pocketbase.pin = '0.23.0'; })), 'DB_VERSION_MISMATCH');
    only(run(erd((e) => { e.revision = 2; })), 'DB_VERSION_MISMATCH');
    only(run(erd((e) => { e.snapshot.revision = '0'.repeat(40); })), 'DB_VERSION_MISMATCH');
    only(run(record((r) => { r.benchmark.result = r.benchmark.result === 'pass' ? 'fail' : 'pass'; })), 'DB_VERSION_MISMATCH');
    only(run(edit(MATRIX, (m) => { m.rows[0].storage = 'DR-0004@2:sqlite-data'; })), 'DB_VERSION_MISMATCH');
    only(run(fixture((d) => fs.writeFileSync(path.join(d, 'docs/example-db.md'), 'Cite DR-0004@2:DB2.\n'))), 'DB_VERSION_MISMATCH');
    // A receipt off the pin's minor line, and one on it without the record's note.
    const ran = repo(RECEIPT).profile.pocketbase.version;
    includes(run(receipt((rc) => { rc.profile.pocketbase.version = '0.23.1'; rc.profile.pocketbase.dockerfilePin.PB_VERSION = '0.23.1'; })), 'DB_VERSION_MISMATCH');
    const otherPatch = `0.22.${Number(ran.split('.')[2]) + 1}`;
    const moved = (note) => fixture((d) => {
      editText(d, DOCKERFILE, (s) => s.replace(/^ARG PB_VERSION=\S+$/m, `ARG PB_VERSION=${otherPatch}`));
      editJson(d, RECORD, (r) => { r.pocketbase.pin = otherPatch; if (note) r.pocketbase.benchmark = note; else delete r.pocketbase.benchmark; });
    });
    only(run(moved(null)), 'DB_VERSION_MISMATCH');
    assert.deepEqual(run(moved(`The receipt ran on ${ran}, on the pin's minor line.`)), []);
  });

  it('fails DB_CHANGE_INCOMPLETE for a changed authority without its entry, order, or rollback', () => {
    only(run(record((r) => { r.changes = r.changes.filter((c) => c.authority !== 'byte-store'); })), 'DB_CHANGE_INCOMPLETE');
    only(run(record((r) => { delete r.changes.find((c) => c.authority === 'pocketbase-version').rollback; })), 'DB_CHANGE_INCOMPLETE');
    only(run(record((r) => { r.changes.find((c) => c.authority === 'containment-stores').dependsOn = []; })), 'DB_CHANGE_INCOMPLETE');
  });

  it('fails DB_ERD_DELETE_MISSING for a relation without delete or merge behavior', () => {
    only(run(erd((e) => { delete e.relations[0].onDelete; })), 'DB_ERD_DELETE_MISSING');
    only(run(erd((e) => { delete e.relations[0].merge; })), 'DB_ERD_DELETE_MISSING');
  });

  it('fails DB_ERD_UNCOVERED and DB_ERD_UNRESOLVED for collections the ERD lacks', () => {
    only(run(erd((e) => { e.entities = e.entities.filter((x) => x.id !== 'todos'); e.relations = e.relations.filter((r) => r.from !== 'todos' && r.to !== 'todos'); })), 'DB_ERD_UNCOVERED');
    const migration = (body) => fixture((d) => fs.writeFileSync(path.join(d, MIGRATIONS, '1900000001_test_collection.js'), body));
    const create = (name) => `migrate((db) => {\n  const dao = new Dao(db);\n  dao.saveCollection(new Collection({ name: ${name}, type: "base", schema: [] }));\n}, (db) => {});\n`;
    only(run(migration(create('"rogue_table"'))), 'DB_ERD_UNCOVERED');
    only(run(migration(create('`rogue_${"table"}`'))), 'DB_ERD_UNRESOLVED');
  });

  it('fails DB_ERD_INCOMPLETE and DB_ERD_INVALID for an entity without its partition or with a bad shape', () => {
    only(run(erd((e) => { e.entities.find((x) => x.id === 'change_sets').partition = null; })), 'DB_ERD_INCOMPLETE');
    only(run(erd((e) => { delete e.entities.find((x) => x.id === 'offers').purge; })), 'DB_ERD_INCOMPLETE');
    only(run(erd((e) => { e.entities.find((x) => x.id === 'offers').scope = 'everyone'; })), 'DB_ERD_INVALID');
  });

  it('fails DB_BENCH_INCOMPLETE for a missing receipt, label, profile field, scale, target, or floor', () => {
    only(run(fixture((d) => fs.rmSync(path.join(d, RECEIPT)))), 'DB_BENCH_INCOMPLETE');
    includes(run(receipt((rc) => { rc.synthetic = false; })), 'DB_BENCH_INCOMPLETE');
    only(run(receipt((rc) => { delete rc.profile.hardware; })), 'DB_BENCH_INCOMPLETE');
    only(run(receipt((rc) => { delete rc.scales['10']; })), 'DB_BENCH_INCOMPLETE');
    includes(run(receipt((rc) => { rc.targets = rc.targets.filter((t) => t.id !== 'restore_rto'); })), 'DB_BENCH_INCOMPLETE');
    only(run(receipt((rc) => { rc.seedPlan.fraction = 0.5; })), 'DB_BENCH_INCOMPLETE');
  });

  it('fails DB_BENCH_MISS_UNRECORDED for a miss with no consequence, and DB_BENCH_INVALID for a miss reported as a pass', () => {
    const miss = (consequence) => fixture((d) => {
      editJson(d, RECEIPT, (rc) => {
        Object.assign(rc.targets.find((t) => t.id === 'projection_lag_p95'), { value: 9000, result: 'fail', consequence });
        rc.result = 'fail';
      });
      editJson(d, RECORD, (r) => { r.benchmark.result = 'fail'; });
    });
    only(run(miss('unrecorded')), 'DB_BENCH_MISS_UNRECORDED');
    assert.deepEqual(run(miss('The relay batches differently, or another authority comes before #19.')), []);
    only(run(receipt((rc) => { rc.targets.find((t) => t.id === 'write_freeze').value = 4000; })), 'DB_BENCH_INVALID');
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
// owner, its packages, its leaves, and its supersession links.
describe('database ADR: the record checks every decision record gets', () => {
  const runRecords = (dir) => records.check(dir, ctxFor(dir));
  const recordOnly = (findings, code) => assert.deepEqual(codes(findings), [code], JSON.stringify(findings, null, 2));

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
});
