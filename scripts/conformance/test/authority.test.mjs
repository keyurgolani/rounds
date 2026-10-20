import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { after, describe, it } from 'node:test';
import { createContext } from '../lib/context.mjs';
import { validate } from '../lib/json-schema.mjs';
import { credentialAssignments, loadAuthority, REVIEW_LEDGER, REVIEW_SPEC } from '../lib/authority/matrix.mjs';
import { extractBaselineStores } from '../lib/authority/stores.mjs';
import * as authority from '../rules/authority.mjs';
import { REPO_ROOT, cleanup, codes, ctxFor, editJson, fixture, readJson, tempDir, writeJson } from './helpers.mjs';

const MATRIX = 'contracts/authority/matrix.json';
const STORES = 'contracts/authority/baseline-stores.json';
const PACKAGES = 'contracts/authority/packages.json';
const LABELS = 'contracts/authority/owner-labels.json';
const LEDGER = 'contracts/authority/disposition-ledger.json';
const CORRECTIONS = 'contracts/authority/owner-sentence-corrections.json';
const DR = 'docs/decisions/DR-0002-authority-matrix.json';
const AUDITED = '62d4eae';
// A rounds-review checkout, when one is named, for the verbatim checks.
const ROUNDS_REVIEW = process.env.ROUNDS_REVIEW_ROOT || null;

after(cleanup);

const run = (dir, options) => authority.check(dir, ctxFor(dir, options));
const only = (findings, code) => assert.deepEqual(codes(findings), [code], JSON.stringify(findings, null, 2));
const includes = (findings, code) => assert.ok(codes(findings).includes(code), JSON.stringify(findings, null, 2));
const row = (m, id) => m.rows.find((r) => r.id === id);
const editMatrix = (fn) => fixture((d) => editJson(d, MATRIX, fn));
const editRow = (id, fn) => editMatrix((m) => { fn(row(m, id), m); });
const repo = (rel) => readJson(REPO_ROOT, rel);

// #16's baseline conflicts: the row each one targets and its resolving leaves.
const ISSUE_CONFLICTS = {
  C1: { rows: ['artifact-edition', 'pursuit'], leaves: ['ROUNDS-17-L01', 'ROUNDS-19-L04'] },
  C2: { rows: ['authentication-identity', 'professional-identity'], leaves: ['ROUNDS-03-L01', 'ROUNDS-03-L02'] },
  C3: { rows: ['campaign-membership', 'current-campaign'], leaves: ['ROUNDS-25-L01', 'ROUNDS-25-L03'] },
  C4: { rows: ['practice-progress', 'practice-draft'], leaves: ['ROUNDS-28-L01', 'ROUNDS-32-L04'] },
  C5: { rows: ['appearance'], leaves: ['ROUNDS-03-L04'] },
  C6: { rows: ['employment-facts', 'project-facts', 'achievement'], leaves: ['ROUNDS-16-L04'] },
  C7: { rows: ['resume-autosave'], leaves: ['ROUNDS-16-L04'] },
  C8: { rows: ['practice-attempt'], leaves: ['ROUNDS-28-L06'] },
  C9: { rows: ['practice-guides'], leaves: ['ROUNDS-07-L05'] },
  C10: { rows: ['demo-state'], leaves: ['ROUNDS-00A-L01', 'ROUNDS-00B-L07'] },
  C11: { rows: ['login-streak'], leaves: ['ROUNDS-03-L01', 'ROUNDS-32-L04'] },
  C12: { rows: ['test-definition', 'harness-revision'], leaves: ['ROUNDS-00A-L02'] },
  C13: { rows: ['account-session'], leaves: ['ROUNDS-03-L04', 'ROUNDS-14-L01'] },
};

describe('authority: repository', () => {
  it('passes on the repository', () => {
    assert.deepEqual(authority.check(REPO_ROOT, createContext(REPO_ROOT, { base: { files: {} } })), []);
  });

  it('passes on an unmodified fixture copy', () => {
    assert.deepEqual(run(fixture()), []);
  });

  it('validates every data file against its schema', () => {
    const findings = [];
    loadAuthority(createContext(REPO_ROOT, { base: 'none' }), findings);
    assert.deepEqual(findings, []);
  });

  it('keeps every schema to the keyword subset the validator and #182 support', () => {
    const schemas = ['contracts/authority', 'contracts/vocabulary', 'docs/decisions']
      .flatMap((dir) => fs.readdirSync(path.join(REPO_ROOT, dir)).filter((f) => f.endsWith('.schema.json')).map((f) => `${dir}/${f}`));
    assert.ok(schemas.length >= 9);
    for (const rel of schemas) {
      const text = fs.readFileSync(path.join(REPO_ROOT, rel), 'utf8');
      for (const k of ['anyOf', 'oneOf', 'allOf', 'not', 'if', 'then', 'else']) assert.doesNotMatch(text, new RegExp(`"${k}"\\s*:`), `${rel} uses ${k}`);
    }
  });
});

describe('authority: matrix content', () => {
  const m = repo(MATRIX);

  it('keeps the 31 spec rows verbatim and splits only 782, 783, and 810', () => {
    const byLine = new Map();
    for (const r of m.rows.filter((x) => x.spec)) byLine.set(r.spec.line, [...(byLine.get(r.spec.line) || []), r]);
    assert.deepEqual([...byLine.keys()].sort((a, b) => a - b), Array.from({ length: 31 }, (_, i) => 781 + i));
    const splits = Object.fromEntries([...byLine].filter(([, rows]) => rows.length > 1).map(([line, rows]) => [line, rows.map((r) => r.id)]));
    assert.deepEqual(splits, {
      782: ['professional-identity', 'profile-contact-point', 'person-contact-point'],
      783: ['employment-facts', 'project-facts'],
      810: ['share-capability-metadata', 'share-bearer-digest', 'share-projection'],
    });
    assert.equal(row(m, 'profile-contact-point').privacy_floor, 'Private');
    assert.equal(row(m, 'person-contact-point').privacy_floor, 'Third-party personal');
    assert.deepEqual(['share-capability-metadata', 'share-bearer-digest', 'share-projection'].map((id) => row(m, id).privacy_floor), ['Private', 'Secret', 'Share Projection']);
  });

  it('gives every row a scope, one target, a disposition, a privacy floor or visibility, a package, and a public-share entry', () => {
    const ledger = new Set(repo(LEDGER).rows.map((r) => r.id));
    for (const r of m.rows) {
      assert.ok(['account', 'platform-global', 'pack-owned'].includes(r.scope), r.id);
      assert.ok(!Array.isArray(r.target_authority), r.id);
      assert.ok(ledger.has(r.disposition) || /^new-platform-concept:INT-0[23]$/.test(r.disposition), r.id);
      assert.ok(r.scope === 'account' ? r.privacy_floor : r.visibility, r.id);
      assert.ok(r.package, r.id);
      assert.equal(r.consumers.filter((c) => c.type === 'public-share').length, 1, r.id);
    }
  });

  for (const [id, want] of Object.entries(ISSUE_CONFLICTS)) {
    it(`flags ${id} with its target rows, disposition, and resolving leaves`, () => {
      const c = m.conflicts.find((x) => x.id === id);
      assert.ok(c, id);
      assert.deepEqual([...c.rows].sort(), [...want.rows].sort());
      assert.deepEqual(c.resolvingLeaves, want.leaves);
      assert.match(c.disposition, /^(INT|CUR)-\d{2}$/);
      assert.ok(c.evidence.length >= 1);
      for (const r of want.rows) assert.ok(row(m, r).conflicts.includes(id), `${r} names ${id}`);
      // Removing the flag fails the check.
      const dir = editMatrix((x) => {
        x.conflicts = x.conflicts.filter((y) => y.id !== id);
        for (const r of x.rows) {
          r.conflicts = r.conflicts.filter((y) => y !== id);
          for (const w of r.baseline_writers) if (w.conflicts) w.conflicts = w.conflicts.filter((y) => y !== id);
          for (const w of r.baseline_writers) if (w.conflicts && !w.conflicts.length) delete w.conflicts;
        }
      });
      const found = codes(run(dir));
      assert.ok(found.includes('AUTH_CONFLICT_MISSING'), JSON.stringify(found));
      assert.deepEqual(found.filter((x) => x !== 'AUTH_CONFLICT_MISSING' && x !== 'AUTH_UNFLAGGED_WRITERS'), []);
    });
  }

  it('requires C1 to C13 when the audited revision is written in full', () => {
    const full = '62d4eaeaecf601da836afa1981adc0b1ae2db16a';
    const audit = (d) => { for (const f of [MATRIX, STORES, PACKAGES]) editJson(d, f, (x) => { x.auditedRevision = full; }); };
    assert.deepEqual(run(fixture(audit)), []);
    const dir = fixture((d) => {
      audit(d);
      editJson(d, MATRIX, (x) => {
        x.conflicts = x.conflicts.filter((c) => c.id !== 'C9');
        for (const r of x.rows) r.conflicts = r.conflicts.filter((c) => c !== 'C9');
      });
    });
    only(run(dir), 'AUTH_CONFLICT_MISSING');
  });

  it('records the conflicts found beyond the issue as foundHere', () => {
    assert.deepEqual(m.conflicts.filter((c) => c.foundHere).map((c) => c.id), ['C14', 'C15', 'C16', 'C17']);
  });

  it('gives each of the nine spec read models one projector, with the OD-3 default for the Preparation plan', () => {
    const projector = Object.fromEntries(m.readModels.map((x) => [x.name, row(m, x.row).projection.projector]));
    assert.deepEqual(projector, {
      Today: 'ROUNDS-30-L02', 'Career Profile overview': 'ROUNDS-31-L02', Pipeline: 'ROUNDS-31-L03', 'Opportunity Workspace': 'ROUNDS-31-L04',
      'Material-use graph': 'ROUNDS-31-L05', 'Preparation plan': 'ROUNDS-31-L07', Readiness: 'ROUNDS-31-L06', 'Search index': 'ROUNDS-31-L08', 'Data Health': 'ROUNDS-31-L09',
    });
    for (const x of m.readModels) for (const k of ['watermark', 'stale', 'degraded']) assert.ok(row(m, x.row).projection[k], `${x.name} ${k}`);
  });

  it('applies the open decisions: OD-1 settled by D8, OD-2 settled, OD-3 and OD-4 defaults, OD-5 blocked', () => {
    const dr = repo(DR);
    const od = Object.fromEntries(dr.decisions.filter((d) => d.od).map((d) => [d.id, d.od.state]));
    assert.deepEqual(od, { 'OD-1': 'settled', 'OD-2': 'settled', 'OD-3': 'default-taken', 'OD-4': 'default-taken', 'OD-5': 'blocked' });
    assert.match(dr.decisions.find((d) => d.id === 'OD-1').od.basis, /D8/);
    const d8 = dr.decisions.find((d) => d.id === 'D8');
    assert.equal(d8.status, 'ratified');
    assert.match(d8.sources.join(' '), /orchestrator decision D8 under the owner's delegation/);
    assert.match(dr.decisions.find((d) => d.id === 'OD-2').od.basis, /PRODUCT\.md:67-70/);
    for (const id of ['career-activity-schedule', 'career-activity-outcome', 'career-activity-kinds']) {
      assert.deepEqual(row(m, id).command_owner, { service: 'interview-process', leaf: 'ROUNDS-22-L02' });
      assert.doesNotMatch(JSON.stringify(row(m, id)), /blocked:/);
    }
    assert.equal(row(m, 'pack-activation').scope, 'account');
    assert.equal(row(m, 'login-streak').command_owner, 'blocked:OD-5');
    assert.equal(row(m, 'login-streak').disposition, 'CUR-20');
    for (const id of ['ai-provider-credential', 'ai-role-settings', 'generation-proposal', 'staged-provider-result', 'provider-invocation-receipt']) {
      assert.equal(row(m, id).command_owner.service, 'provider-gateway', id);
      assert.equal(row(m, id).package, 'provider-gateway', id);
      assert.doesNotMatch(JSON.stringify(row(m, id)), /blocked:/, id);
    }
    assert.deepEqual(m.rows.filter((r) => JSON.stringify(r).includes('blocked:')).map((r) => r.id), ['login-streak']);
  });

  it('maps all 36 owner labels as #16 lists them', () => {
    const labels = repo(LABELS).labels;
    assert.equal(labels.length, 36);
    const svc = Object.fromEntries(labels.map((l) => [l.label, l.service]));
    for (const l of ['Product Architecture', 'Product Design System', 'Interaction Platform', 'Command Center', 'Opportunity Experience', 'Transformation Migration', 'Quality and Release Engineering']) assert.equal(svc[l], 'none', l);
    assert.equal(svc['AI Trust Platform'], 'provider-gateway');
    const expected = {
      'Pursuit Lifecycle': 'opportunity-pursuit', Campaigns: 'opportunity-pursuit', Offers: 'opportunity-pursuit',
      Capture: 'capture-ingestion', 'Source Processing': 'capture-ingestion', 'Claims and Provenance': 'capture-ingestion', 'Profile Bootstrap': 'capture-ingestion',
      Materials: 'artifact', 'Resume Studio': 'artifact', 'Opportunity Materials': 'artifact', 'Claims and Career Profile': 'career-profile',
      Today: 'read-model', 'Preparation Guidance': 'read-model', 'Execution and Rendering Platform': 'execution-control-plane', 'Relationship Platform': 'command-gateway',
    };
    for (const [l, s] of Object.entries(expected)) assert.equal(svc[l], s, l);
    const rows = Object.fromEntries(labels.filter((l) => l.rows).map((l) => [l.label, l.rows]));
    assert.deepEqual(Object.keys(rows).sort(), ['Domain Platform', 'Identity and Career Profile', 'Identity, Authorization, and Sharing', 'Portability and Sharing', 'Read Platform', 'Relationships and Networking']);
    assert.deepEqual(rows['Portability and Sharing'], { 'account-export': 'account', 'account-restore': 'account', 'share-projection': 'public-share', 'share-view': 'public-share' });
    assert.deepEqual(rows['Read Platform'], { 'search-index': 'search' });
    assert.deepEqual(rows['Identity, Authorization, and Sharing'], { 'share-capability-metadata': 'public-share', 'share-bearer-digest': 'public-share', 'demo-state': 'account' });
    assert.deepEqual(rows['Domain Platform'], { 'idempotency-record': 'command-gateway', 'audit-entry-change-set': 'revision-audit', 'domain-event': 'revision-audit' });
    assert.deepEqual(rows['Relationships and Networking'], { 'person-role': 'identity-directory', referral: 'opportunity-pursuit' });
    for (const id of ['authentication-identity', 'account-session', 'appearance', 'current-campaign']) assert.equal(rows['Identity and Career Profile'][id], 'account', id);
    for (const id of ['professional-identity', 'profile-contact-point']) assert.equal(rows['Identity and Career Profile'][id], 'career-profile', id);
  });

  it('covers all 101 owner sentences, one per body', () => {
    const c = repo(CORRECTIONS);
    assert.equal(c.entries.length, 101);
    assert.equal(new Set(c.entries.map((e) => e.issue)).size, 101);
    assert.equal(c.matrixRevision, m.revision);
  });

  it('lists one package per spec service, plus D8\'s Provider Gateway, with target paths pending #18', () => {
    const p = repo(PACKAGES).packages;
    assert.equal(p.length, 18);
    assert.deepEqual(p.filter((x) => !x.decision).map((x) => x.spec), Array.from({ length: 17 }, (_, i) => `spec ${1919 + i}`));
    assert.deepEqual(p.filter((x) => x.decision).map((x) => [x.id, x.service, x.spec, x.decision]), [['provider-gateway', 'Provider Gateway', 'spec 808', 'D8']]);
    for (const x of p) assert.equal(x.target_path, 'pending:ROUNDS-02-L01');
  });

  it('gives Recommendation dispositions one owner and keeps #144 to Today hides and reminder acknowledgments', () => {
    const text = (r) => JSON.stringify(r.spec || r.summary);
    assert.deepEqual(m.rows.filter((r) => /snooze/i.test(text(r))).map((r) => r.id), ['recommendation']);
    assert.doesNotMatch(text(row(m, 'today-item-state')), /accept|dismiss|snooze/i);
    assert.match(row(m, 'today-item-state').summary.information, /hides and reminder acknowledgments/);
    const c144 = repo(CORRECTIONS).entries.find((e) => e.issue === 144);
    assert.deepEqual(c144.rows, ['today-item-state']);
    assert.match(c144.corrected, /#140's \(ROUNDS-29-L03\) commands on `recommendation`/);
  });

  it('routes the pasted job description caches to the Opportunity and the draft journal to the Practice Draft', () => {
    const jd = row(m, 'job-description-cache');
    assert.equal(jd.yields_to, 'opportunity');
    assert.match(jd.target_authority, /^n\/a:/);
    assert.deepEqual([jd.transfer.leaf, jd.transfer.mapping], ['ROUNDS-32-L04', 'ROUNDS-19-L01']);
    assert.deepEqual(jd.consumers.filter((c) => c.leaf).map((c) => c.leaf), ['ROUNDS-17-L02', 'ROUNDS-17-L03']);
    assert.deepEqual(jd.baseline_writers.map((w) => w.store), ['rounds.resume.ats.*.jd', 'rounds.resume.tailor.*.jd']);
    const drafts = row(m, 'draft-caches');
    assert.equal(drafts.yields_to, 'practice-draft');
    assert.deepEqual(drafts.baseline_writers, []);
    const stores = repo(STORES).stores;
    for (const k of ['rounds.resume.ats.*.jd', 'rounds.resume.tailor.*.jd']) assert.deepEqual(stores.find((x) => x.name === k).rows, ['job-description-cache']);
  });

  it('names a distinct target authority on every row, each one record', () => {
    const targets = m.rows.filter((r) => typeof r.target_authority === 'object').map((r) => `${r.target_authority.record.toLowerCase()}@${r.target_authority.location}`);
    assert.equal(new Set(targets).size, targets.length);
    for (const t of targets) assert.doesNotMatch(t, /[,;]| or /);
  });

  it('lists the 40 live collections and every browser key family, including the SDK auth store', () => {
    const s = repo(STORES);
    const collections = s.stores.filter((x) => x.kind === 'collection').map((x) => x.name);
    assert.equal(collections.length, 40);
    assert.ok(collections.includes('users'));
    assert.equal(collections.filter((n) => n.startsWith('exp_')).length, 6);
    const keys = s.stores.filter((x) => x.kind === 'browser-key').map((x) => x.name);
    assert.equal(keys.length, s.counts.browserKeyFamilies);
    for (const k of ['pocketbase_auth', 'rounds.loginStreak.v1', 'rounds.loginStreak.v1:*', 'rounds.currentCampaign.v1']) assert.ok(keys.includes(k), k);
    assert.deepEqual(s.stores.find((x) => x.name === 'pocketbase_auth').rows, ['account-session']);
  });

  it('pins the 34 ledger rows', () => {
    const l = repo(LEDGER);
    assert.equal(l.rows.length, 34);
    assert.equal(l.pin.rows, 34);
    assert.deepEqual([...new Set(l.rows.map((r) => r.id.slice(0, 3)))], ['INT', 'CUR']);
  });
});

describe('authority: rules 1 to 12, one negative control each', () => {
  it('rule 1: two target authorities', () => {
    only(run(editRow('offer', (r) => { r.target_authority = [r.target_authority, { record: 'Offer copy', location: 'server' }]; })), 'AUTH_TWO_AUTHORITIES');
    only(run(editRow('offer', (r) => { r.target_authority.record = 'Offer, Offer copy'; })), 'AUTH_TWO_AUTHORITIES');
    only(run(editRow('offer', (r) => { r.target_authority.record = 'Offer or Pursuit'; })), 'AUTH_TWO_AUTHORITIES');
  });

  it('rule 1 across rows: one authority claimed by two rows', () => {
    const findings = run(editMatrix((m) => {
      const o = row(m, 'offer');
      const { spec, transfer, ...copy } = o;
      m.rows.push({
        ...copy, id: 'offer-copy', summary: { information: 'A second offer record', authority: 'Offer', mutability: 'Entity Version', delete_merge: 'Tombstone', consumers: 'None' },
        command_owner: { service: 'opportunity-pursuit', leaf: 'ROUNDS-24-L03' }, commands: 'pending:ROUNDS-24-L03', baseline_writers: [], conflicts: [],
        consumers: [{ type: 'public-share', name: 'n/a:not shared' }], projector: 'n/a:no read model consumes it', search: 'n/a:not indexed',
      });
    }));
    only(findings, 'AUTH_AUTHORITY_SHARED');
    assert.match(findings[0].message, /offer-copy and offer both claim "Offer and Offer Revision"/);
  });

  it('rule 1: a cache yields to one server row and claims no authority', () => {
    only(run(editRow('draft-caches', (r) => { r.yields_to = 'no-such-row'; })), 'AUTH_UNRESOLVED_REF');
    only(run(editRow('draft-caches', (r) => { r.yields_to = 'view-state'; })), 'AUTH_UNRESOLVED_REF');
    only(run(editRow('draft-caches', (r) => { r.target_authority = { record: 'Practice draft cache', location: 'server' }; })), 'AUTH_TWO_AUTHORITIES');
  });

  it('rule 2: a second writer module, or a derived consumer, with no conflict', () => {
    only(run(editMatrix((m) => {
      const w = row(m, 'interview-process').baseline_writers[0];
      row(m, 'artifact-revision').baseline_writers.push({ ...w, store: 'resume_versions' });
    })), 'AUTH_UNFLAGGED_WRITERS');
    only(run(editRow('artifact-revision', (r) => { r.baseline_writers[0].role = 'derived-consumer'; })), 'AUTH_UNFLAGGED_WRITERS');
    // C7's row is a derived consumer: without C7 it fails.
    includes(run(editMatrix((m) => {
      m.conflicts = m.conflicts.filter((c) => c.id !== 'C7');
      row(m, 'resume-autosave').conflicts = [];
    })), 'AUTH_UNFLAGGED_WRITERS');
  });

  it('rule 2: a conflict exempts only the writers that name it', () => {
    const extra = (m) => ({ ...row(m, 'interview-process').baseline_writers[0] });
    // appearance names C5 and C16, and offer only C16; a new module on either still fails.
    only(run(editMatrix((m) => { row(m, 'appearance').baseline_writers.push({ ...extra(m), store: 'user_preferences' }); })), 'AUTH_UNFLAGGED_WRITERS');
    only(run(editMatrix((m) => { row(m, 'offer').baseline_writers.push({ ...extra(m), store: 'offers' }); })), 'AUTH_UNFLAGGED_WRITERS');
    only(run(editRow('offer', (r) => { delete r.baseline_writers[0].conflicts; })), 'AUTH_UNFLAGGED_WRITERS');
    only(run(editRow('offer', (r) => { r.baseline_writers[0].conflicts = ['C16', 'C5']; })), 'AUTH_CONFLICT_UNFLAGGED');
    only(run(editRow('offer', (r) => { r.baseline_writers[0].conflicts = ['C16', 'C99']; })), 'AUTH_UNRESOLVED_REF');
  });

  it('rule 3: a relation with no owning row', () => {
    only(run(editMatrix((m) => { m.relations[0].owner_row = 'no-such-row'; })), 'AUTH_RELATION_UNOWNED');
  });

  it('rule 4: a Secret row with a consumer other than a verifier or gateway', () => {
    only(run(editRow('account-session', (r) => { r.consumers.push({ type: 'export', name: 'account export', leaf: 'ROUNDS-18-L03' }); })), 'AUTH_SECRET_CONSUMER');
    only(run(editRow('share-bearer-digest', (r) => { r.consumers.push({ type: 'log-trace', name: 'request log' }); })), 'AUTH_SECRET_CONSUMER');
  });

  it('rule 5: no disposition, or one outside the ledger', () => {
    only(run(editRow('offer', (r) => { delete r.disposition; })), 'AUTH_NO_DISPOSITION');
    only(run(editRow('offer', (r) => { r.disposition = 'CUR-99'; })), 'AUTH_NO_DISPOSITION');
    only(run(editRow('person', (r) => { r.disposition = 'new-platform-concept:INT-05'; })), 'AUTH_NO_DISPOSITION');
  });

  it('rule 6: browser storage as target authority', () => {
    only(run(editRow('appearance', (r) => { r.target_authority.location = 'browser-storage'; })), 'AUTH_BROWSER_AUTHORITY');
  });

  it('rule 7: an empty cell, or a leaf outside leaf-ids.json', () => {
    only(run(editRow('offer', (r) => { r.health = ''; })), 'AUTH_EMPTY_CELL');
    only(run(editRow('offer', (r) => { r.health = 'pending:ROUNDS-99-L99'; })), 'AUTH_UNRESOLVED_REF');
    const rejected = run(editRow('offer', (r) => { r.health = 'pending:ROUNDS-26-L05'; }));
    only(rejected, 'AUTH_UNRESOLVED_REF');
    assert.match(rejected[0].message, /rejected/);
  });

  it('rule 8: an unresolved package, service, or term', () => {
    only(run(editRow('draft-caches', (r) => { r.package = 'no-such-package'; })), 'AUTH_UNRESOLVED_REF');
    only(run(editRow('offer', (r) => { r.term = 'no-such-term'; })), 'AUTH_UNRESOLVED_REF');
    includes(run(editRow('offer', (r) => { r.command_owner.service = 'no-such-service'; r.package = 'no-such-service'; })), 'AUTH_UNRESOLVED_REF');
    only(run(editRow('offer', (r) => { r.package = 'account'; })), 'AUTH_PACKAGE_MISMATCH');
  });

  it('rule 9: a baseline store with no row, or a writer naming an undeclared store', () => {
    only(run(fixture((d) => editJson(d, STORES, (s) => { s.stores.find((x) => x.name === 'offers').rows = []; }))), 'AUTH_STORE_NO_ROW');
    only(run(editRow('offer', (r) => { r.baseline_writers[0].store = 'no_such_collection'; })), 'AUTH_STORE_UNDECLARED');
    only(run(fixture((d) => editJson(d, STORES, (s) => { s.stores.find((x) => x.name === 'offers').rows = ['no-such-row', 'offer']; }))), 'AUTH_UNRESOLVED_REF');
  });

  it('rule 10: a Test Definition or Harness Revision row that is not server-only', () => {
    only(run(editRow('test-definition', (r) => { r.visibility = 'authed-readable'; })), 'AUTH_CONTAINMENT_VISIBILITY');
    only(run(editRow('harness-revision', (r) => { r.visibility = 'public-ui'; })), 'AUTH_CONTAINMENT_VISIBILITY');
  });

  describe('rule 11: revisions against the base', () => {
    const base = (fn = () => {}) => {
      const m = repo(MATRIX);
      fn(m);
      return { base: { files: { [MATRIX]: JSON.stringify(m) } } };
    };
    // Raises the matrix and DR-0002 to revision 2, as one counter.
    const bump = (d, compatibility = 'additive') => {
      editJson(d, DR, (r) => { r.revision = 2; r.compatibility = compatibility; });
      editJson(d, MATRIX, (m) => { m.revision = 2; m.compatibility = compatibility; });
    };

    it('passes an unchanged matrix', () => {
      assert.deepEqual(run(fixture(), base()), []);
    });

    it('fails a changed row that keeps its revision', () => {
      only(run(editRow('offer', (r) => { r.storage = 'postgres:offers'; }), base()), 'AUTH_REVISION_NOT_BUMPED');
      const rowOnly = fixture((d) => { bump(d); editJson(d, MATRIX, (m) => { row(m, 'offer').storage = 'postgres:offers'; }); });
      only(run(rowOnly, base()), 'AUTH_REVISION_NOT_BUMPED');
    });

    it('passes an additive change that bumps the row and the matrix', () => {
      const dir = fixture((d) => { bump(d); editJson(d, MATRIX, (m) => { Object.assign(row(m, 'offer'), { revision: 2, storage: 'postgres:offers' }); }); });
      assert.deepEqual(run(dir, base()), []);
    });

    it('fails a breaking change marked additive, on the row and on the matrix', () => {
      const change = (compat, rowCompat) => fixture((d) => {
        bump(d, compat);
        editJson(d, MATRIX, (m) => { const r = row(m, 'offer');
          Object.assign(r, { revision: 2, compatibility: rowCompat, privacy_floor: r.privacy_floor === 'Sensitive' ? 'Private' : 'Sensitive' }); });
      });
      only(run(change('additive', 'additive'), base()), 'AUTH_COMPATIBILITY_UNDECLARED');
      only(run(change('additive', 'breaking'), base()), 'AUTH_COMPATIBILITY_UNDECLARED');
      assert.deepEqual(run(change('breaking', 'breaking'), base()), []);
    });

    it('fails a removed row and a new row at an old revision', () => {
      const retired = base((m) => { m.rows.push({ ...row(m, 'offer'), id: 'retired-offer' }); });
      only(run(fixture((d) => bump(d)), retired), 'AUTH_ROW_REMOVED');
      const added = base((m) => { m.rows = m.rows.filter((r) => r.id !== 'view-state'); });
      only(run(fixture((d) => bump(d)), added), 'AUTH_REVISION_NOT_BUMPED');
      assert.deepEqual(run(fixture((d) => { bump(d); editJson(d, MATRIX, (m) => { row(m, 'view-state').revision = 2; }); }), added), []);
    });

    it('checks the hand-written baseline store rows against the base', () => {
      const withStores = (fn) => {
        const st = repo(STORES);
        fn(st);
        return { base: { files: { [MATRIX]: JSON.stringify(repo(MATRIX)), [STORES]: JSON.stringify(st) } } };
      };
      const offers = (st) => st.stores.find((x) => x.name === 'offers');
      const added = fixture((d) => editJson(d, STORES, (st) => { offers(st).rows.push('pursuit'); }));
      only(run(added, withStores(() => {})), 'AUTH_REVISION_NOT_BUMPED');
      const addedBumped = fixture((d) => { bump(d); editJson(d, STORES, (st) => { offers(st).rows.push('pursuit'); }); });
      assert.deepEqual(run(addedBumped, withStores(() => {})), []);
      // Dropping a row from a store re-homes it, which is breaking.
      const dropped = withStores((st) => { offers(st).rows.push('pursuit'); });
      only(run(fixture((d) => bump(d)), dropped), 'AUTH_COMPATIBILITY_UNDECLARED');
      assert.deepEqual(run(fixture((d) => bump(d, 'breaking')), dropped), []);
    });

    it('fails a ratified DR-0002 that leaves a governed file unpinned', () => {
      const dr = repo(DR);
      assert.deepEqual(dr.approvalRef.governedFiles.map((g) => g.path), [MATRIX, PACKAGES, LABELS, STORES]);
      only(run(fixture((d) => editJson(d, DR, (r) => { r.approvalRef.governedFiles = r.approvalRef.governedFiles.filter((g) => g.path !== STORES); }))), 'AUTH_APPROVAL_INCOMPLETE');
    });

    it('fails closed when the base cannot be read, and when DR-0002 disagrees', () => {
      only(run(fixture(), { base: 'no-such-ref' }), 'AUTH_REVISION_UNAVAILABLE');
      only(run(fixture((d) => editJson(d, DR, (r) => { r.revision = 2; }))), 'AUTH_REVISION_MISMATCH');
    });
  });

  it('rule 12: a command type on two rows, or commands with no owner', () => {
    only(run(editMatrix((m) => { row(m, 'offer').commands = ['RecordOffer']; row(m, 'referral').commands = ['RecordOffer']; })), 'AUTH_COMMAND_DUPLICATE');
    only(run(editRow('draft-caches', (r) => { r.commands = ['CacheDraft']; })), 'AUTH_COMMAND_UNOWNED');
  });
});

describe('authority: projections, migration, and privacy', () => {
  it('fails a projection whose sources and consumers disagree', () => {
    only(run(editRow('action', (r) => { r.consumers = r.consumers.filter((c) => c.name !== 'Today'); })), 'AUTH_PROJECTION_INCOMPLETE');
    only(run(editRow('offer', (r) => { r.consumers.unshift({ type: 'read-model', name: 'Readiness', leaf: 'ROUNDS-31-L06' }); })), 'AUTH_PROJECTION_INCOMPLETE');
    only(run(editRow('offer', (r) => { r.projector = 'n/a:no read model consumes it'; })), 'AUTH_PROJECTION_INCOMPLETE');
    only(run(editRow('opportunity', (r) => { r.search = 'n/a:not indexed'; })), 'AUTH_PROJECTION_INCOMPLETE');
  });

  it('fails two read models on one projector, and a missing spec read model', () => {
    only(run(editRow('preparation-plan-read-model', (r) => { r.projection.projector = 'ROUNDS-30-L02'; r.projector = 'ROUNDS-30-L02'; })), 'AUTH_PROJECTION_INCOMPLETE');
    includes(run(editMatrix((m) => { m.readModels = m.readModels.filter((x) => x.name !== 'Today'); })), 'AUTH_READ_MODEL_MISSING');
  });

  it('fails a row with baseline writers and no transfer', () => {
    only(run(editRow('offer', (r) => { delete r.transfer; })), 'AUTH_TRANSFER_MISSING');
  });

  it('fails an account row without a privacy floor and a row without a public-share entry', () => {
    only(run(editRow('offer', (r) => { delete r.privacy_floor; })), 'AUTH_PRIVACY_MISSING');
    only(run(editRow('practice-guides', (r) => { r.privacy_floor = 'Private'; })), 'AUTH_PRIVACY_MISSING');
    only(run(editRow('offer', (r) => { r.consumers = r.consumers.filter((c) => c.type !== 'public-share'); })), 'AUTH_PUBLIC_SHARE_UNDECLARED');
  });

  it('keeps server-only rows to verifier and gateway consumers', () => {
    only(run(editRow('test-definition', (r) => { r.consumers.push({ type: 'ui-direct-read', name: 'practice page', leaf: 'ROUNDS-28-L01' }); })), 'AUTH_CONTAINMENT_VISIBILITY');
  });
});

describe('authority: coverage of the audited revision', () => {
  it('fails a collection at the audited revision with no entry', () => {
    only(run(fixture((d) => editJson(d, STORES, (s) => { s.stores = s.stores.filter((x) => x.id !== 'collection:question_timers'); }))), 'AUTH_STORE_UNDECLARED');
  });

  it('fails a key a frontend/src storage call writes at the audited revision with no entry, including the SDK auth store', () => {
    only(run(fixture((d) => editJson(d, STORES, (s) => { s.stores = s.stores.filter((x) => x.id !== 'browser-key:pocketbase_auth'); }))), 'AUTH_STORE_UNDECLARED');
    only(run(fixture((d) => editJson(d, STORES, (s) => { s.stores = s.stores.filter((x) => x.id !== 'browser-key:rounds.loginStreak.v1:*'); }))), 'AUTH_STORE_UNDECLARED');
  });

  it('fails an entry that is not a store at the audited revision', () => {
    only(run(fixture((d) => editJson(d, STORES, (s) => { s.stores.push({ id: 'collection:zz_gone', kind: 'collection', name: 'zz_gone', rows: ['offer'] }); }))), 'AUTH_STORE_STALE');
  });

  it('extracts collections, key families, and unresolved storage calls from a pinned tree', () => {
    const files = {
      'pocketbase/pb_migrations/1_init.js': 'migrate((db) => {\n  const c = new Collection({ name: "things" });\n}, (db) => {});\n',
      'frontend/src/a.ts': 'const id = crypto.randomUUID();\nlocalStorage.setItem(`rounds.x.${id}`, "1");\nexport const odd = (v: string) => localStorage.setItem(keyFrom(v), v);\n',
    };
    const tree = createContext(REPO_ROOT, { trees: { t: { files } } }).tree('t');
    const out = extractBaselineStores(tree, []);
    assert.deepEqual(out.stores.map((s) => s.id).sort(), ['browser-key:rounds.x.*', 'collection:things', 'collection:users']);
    assert.deepEqual(out.unresolved, ['frontend/src/a.ts:3']);
  });

  it('fails closed when the audited revision cannot be read', () => {
    only(run(fixture(), { treeRoot: tempDir() }), 'AUTH_REVISION_UNAVAILABLE');
  });

  it('recreates a missing baseline-stores.json with every store and no rows', () => {
    const dir = fixture((d) => fs.rmSync(path.join(d, STORES)));
    const missing = run(dir);
    includes(missing, 'AUTH_SHAPE_INVALID');
    assert.match(missing.find((f) => f.code === 'AUTH_SHAPE_INVALID').message, /baseline-stores\.json is missing/);
    const out = authority.generate(dir, ctxFor(dir)).find((o) => o.path === STORES);
    assert.ok(out, 'generate recreates the file');
    const doc = JSON.parse(out.content);
    assert.deepEqual(doc.counts, { collections: 40, browserKeyFamilies: 82 });
    assert.ok(doc.stores.every((x) => Array.isArray(x.rows) && !x.rows.length));
    fs.writeFileSync(path.join(dir, STORES), out.content);
    includes(run(dir), 'AUTH_STORE_NO_ROW');
  });

  it('keeps an unreadable baseline-stores.json for a person to fix', () => {
    const dir = fixture((d) => fs.writeFileSync(path.join(d, STORES), '{ not json'));
    only(run(dir), 'AUTH_SHAPE_INVALID');
    assert.equal(authority.generate(dir, ctxFor(dir)).find((o) => o.path === STORES), undefined);
  });
});

describe('authority: spec rows', () => {
  it('keeps the spec columns verbatim without a rounds-review checkout', () => {
    only(run(editRow('offer', (r) => { r.spec.authority = 'Many offers per Pursuit'; })), 'AUTH_SPEC_ROW_CHANGED');
    only(run(editRow('profile-contact-point', (r) => { r.spec.consumers = 'Materials'; })), 'AUTH_SPEC_ROW_CHANGED');
    only(run(editRow('profile-contact-point', (r) => { delete r.split; })), 'AUTH_SPEC_ROW_CHANGED');
  });

  it('fails a spec row with no row, and a row with both spec and summary', () => {
    const missing = run(editMatrix((m) => { m.rows = m.rows.filter((r) => r.spec?.line !== 791); }));
    includes(missing, 'AUTH_SPEC_ROW_MISSING');
    assert.match(missing.find((f) => f.code === 'AUTH_SPEC_ROW_MISSING').message, /spec line 791 has no row/);
    only(run(editRow('offer', (r) => { r.summary = { ...r.spec }; delete r.summary.line; })), 'AUTH_SHAPE_INVALID');
  });
});

describe('authority: documentation', () => {
  it('fails a citation that does not resolve at the audited revision', () => {
    only(run(editRow('offer', (r) => { r.baseline_writers[0].lines = '99999'; })), 'AUTH_CITATION_STALE');
    only(run(editRow('offer', (r) => { r.baseline_writers[0].anchor = 'not on that line'; })), 'AUTH_CITATION_STALE');
    only(run(editRow('offer', (r) => { r.baseline_writers[0].path = 'frontend/src/not-there.ts'; })), 'AUTH_CITATION_STALE');
    only(run(editMatrix((m) => { m.conflicts[0].evidence[0].lines = '1-99999'; })), 'AUTH_CITATION_STALE');
    only(run(fixture((d) => editJson(d, STORES, (s) => { s.stores[0].created = 'pocketbase/pb_migrations/not-there.js:1'; }))), 'AUTH_CITATION_STALE');
    only(run(fixture((d) => editJson(d, PACKAGES, (p) => { p.packages[1].baseline_locations.push('frontend/src/not-there/'); }))), 'AUTH_CITATION_STALE');
  });

  it('cites the demo row\'s quota fields, never its credential lines', () => {
    const demo = row(repo(MATRIX), 'demo-state').baseline_writers.find((w) => w.path === 'pocketbase/pb_migrations/1700000600_demo_user.js');
    assert.equal(demo.lines, '15-17');
    only(run(editRow('demo-state', (r) => {
      const w = r.baseline_writers.find((x) => x.path === 'pocketbase/pb_migrations/1700000600_demo_user.js');
      w.lines = '7-8';
      delete w.anchor;
    })), 'AUTH_CITES_SECRET');
  });

  it('fails a leaf reference that does not resolve', () => {
    only(run(editMatrix((m) => { m.conflicts[0].resolvingLeaves.push('ROUNDS-99-L01'); })), 'AUTH_UNRESOLVED_REF');
    only(run(fixture((d) => editJson(d, LEDGER, (l) => { l.rows[0].proposals.push('ROUNDS-99'); }))), 'AUTH_UNRESOLVED_REF');
    only(run(fixture((d) => editJson(d, DR, (r) => { r.decisions[0].decision += ' See ROUNDS-98-L01.'; }))), 'AUTH_UNRESOLVED_REF');
  });

  it('checks DR-0002@<n>:<row> examples against the matrix', () => {
    const write = (text) => fixture((d) => fs.writeFileSync(path.join(d, 'docs/example-citations.md'), text));
    assert.deepEqual(run(write('Cite DR-0002@1:appearance in consumes.\n')), []);
    const bad = run(write('Cite DR-0002@2:appearance or DR-0002@1:no-such-row.\n'));
    only(bad, 'AUTH_CITATION_UNRESOLVED');
    assert.equal(bad.length, 2);
  });
});

describe('authority: security', () => {
  it('holds no secret value or secret-shaped string', () => {
    const jwt = ['eyJ', 'x'.repeat(12), '.', 'y'.repeat(12)].join('');
    only(run(editRow('offer', (r) => { r.baseline_writers[0].note = `token ${jwt}`; })), 'AUTH_SECRET_VALUE');
    only(run(editRow('offer', (r) => { r.baseline_writers[0].note = `mail ${['owner', 'gmail.com'].join('@')}`; })), 'AUTH_SECRET_VALUE');
    only(run(editRow('offer', (r) => { r.baseline_writers[0].note = `see /r/${'a'.repeat(16)}`; })), 'AUTH_SECRET_VALUE');
    // A credential the audited revision assigns, injected without printing it.
    const tree = createContext(REPO_ROOT).tree(AUDITED);
    const value = credentialAssignments(tree.read('pocketbase/pb_migrations/1700000600_demo_user.js')).find((a) => /PASSWORD/.test(a.name)).value;
    const findings = run(editRow('offer', (r) => { r.baseline_writers[0].note = `demo ${value}`; }));
    only(findings, 'AUTH_SECRET_VALUE');
    assert.ok(!JSON.stringify(findings).includes(value));
  });

  it('keeps Secret rows to verifier and gateway consumers and Test Definitions and Harness Revisions server-only', () => {
    const m = repo(MATRIX);
    for (const r of m.rows.filter((x) => x.privacy_floor === 'Secret')) {
      for (const c of r.consumers.filter((x) => !x.name.startsWith('n/a:'))) assert.ok(['verifier', 'gateway'].includes(c.type), `${r.id} ${c.type}`);
    }
    assert.deepEqual(m.rows.filter((r) => r.privacy_floor === 'Secret').map((r) => r.id), ['account-session', 'ai-provider-credential', 'share-bearer-digest']);
    for (const id of ['test-definition', 'harness-revision']) assert.equal(row(m, id).visibility, 'server-only');
  });
});

describe('authority: packages beyond the spec services', () => {
  it('needs a ratified DR-0002 decision for a package beyond the 17 spec services', () => {
    only(run(fixture((d) => editJson(d, PACKAGES, (p) => { p.packages.find((x) => x.id === 'provider-gateway').decision = 'D99'; }))), 'AUTH_UNRESOLVED_REF');
    only(run(fixture((d) => editJson(d, PACKAGES, (p) => { delete p.packages.find((x) => x.id === 'provider-gateway').decision; }))), 'AUTH_PACKAGE_MISMATCH');
    only(run(fixture((d) => editJson(d, DR, (r) => { r.decisions.find((x) => x.id === 'D8').status = 'draft'; }))), 'AUTH_PACKAGE_MISMATCH');
  });
});

describe('authority: open decisions, labels, and corrections', () => {
  it('fails a missing OD entry, a cell blocked on a settled decision, and a mismatched status', () => {
    only(run(fixture((d) => editJson(d, DR, (r) => { r.decisions = r.decisions.filter((x) => x.id !== 'OD-3'); }))), 'AUTH_OD_MISSING');
    only(run(fixture((d) => editJson(d, DR, (r) => { Object.assign(r.decisions.find((x) => x.id === 'OD-5'), { status: 'ratified', od: { state: 'settled', basis: 'owner decision' } }); }))), 'AUTH_OD_SETTLED_BLOCKED');
    only(run(fixture((d) => editJson(d, DR, (r) => { r.decisions.find((x) => x.id === 'OD-1').status = 'draft'; }))), 'AUTH_OD_MISSING');
    only(run(editRow('offer', (r) => { r.impact = 'blocked:OD-9'; })), 'AUTH_OD_MISSING');
  });

  it('fails a row whose command owner disagrees with its capability\'s owner label', () => {
    only(run(fixture((d) => editJson(d, LABELS, (l) => { l.labels.find((x) => x.capability === 'ROUNDS-04').service = 'account'; }))), 'AUTH_OWNER_LABEL_MISMATCH');
    only(run(fixture((d) => editJson(d, LABELS, (l) => { delete l.labels.find((x) => x.capability === 'ROUNDS-02').rows['domain-event']; }))), 'AUTH_OWNER_LABEL_MISMATCH');
    only(run(fixture((d) => editJson(d, LABELS, (l) => { l.labels = l.labels.filter((x) => x.capability !== 'ROUNDS-27'); }))), 'AUTH_OWNER_LABEL_MISMATCH');
  });

  it('checks the labels against the catalog when one is given', () => {
    const dir = tempDir();
    const catalog = (fn = (c) => c) => {
      const file = path.join(dir, `catalog-${Math.random().toString(36).slice(2)}.json`);
      fs.writeFileSync(file, JSON.stringify({ capabilities: fn(repo(LABELS).labels.map((l) => ({ id: l.capability, owner: l.label }))) }));
      return file;
    };
    assert.deepEqual(run(fixture(), { catalogPath: catalog() }), []);
    only(run(fixture(), { catalogPath: catalog((c) => c.map((x) => (x.id === 'ROUNDS-21' ? { ...x, owner: 'Opportunity Surfaces' } : x))) }), 'AUTH_LABELS_PIN');
  });

  it('fails a correction that names the wrong rows, label, or revision', () => {
    only(run(fixture((d) => editJson(d, CORRECTIONS, (c) => { c.entries[0].rows = []; }))), 'AUTH_CORRECTION_INVALID');
    only(run(fixture((d) => editJson(d, CORRECTIONS, (c) => { c.entries.find((e) => e.kind === 'none').rows = ['offer']; }))), 'AUTH_CORRECTION_INVALID');
    only(run(fixture((d) => editJson(d, CORRECTIONS, (c) => { c.entries[0].label = 'Directory'; }))), 'AUTH_CORRECTION_INVALID');
    includes(run(fixture((d) => editJson(d, CORRECTIONS, (c) => { c.matrixRevision = 2; }))), 'AUTH_REVISION_MISMATCH');
  });
});

describe('authority: --review against rounds-review', () => {
  // A stand-in rounds-review checkout built from the committed files, so the
  // test runs without one; the real checkout is checked when present.
  function reviewDir(edit = {}) {
    const dir = tempDir('rounds-review-');
    const m = repo(MATRIX);
    const lines = Array.from({ length: 2000 }, () => '');
    for (const r of m.rows.filter((x) => x.spec)) lines[r.spec.line - 1] = `| ${r.spec.information} | ${r.spec.authority} | ${r.spec.mutability} | ${r.spec.delete_merge} | ${r.spec.consumers} |`;
    for (const p of repo(PACKAGES).packages.filter((x) => !x.decision)) lines[Number(p.spec.slice(5)) - 1] = `- ${p.service}`;
    if (edit.spec) edit.spec(lines);
    fs.mkdirSync(path.join(dir, path.dirname(REVIEW_SPEC)), { recursive: true });
    fs.writeFileSync(path.join(dir, REVIEW_SPEC), lines.join('\n'));
    const seeds = repo(LEDGER).rows.map((r) => `  ${JSON.stringify([r.id, r.intent, r.class, [], [], r.proposals, r.proof])},`);
    if (edit.ledger) edit.ledger(seeds);
    const ledger = `const seeds = [\n${seeds.join('\n')}\n];\n`;
    fs.mkdirSync(path.join(dir, path.dirname(REVIEW_LEDGER)), { recursive: true });
    fs.writeFileSync(path.join(dir, REVIEW_LEDGER), ledger);
    writeJson(dir, 'src/data/capabilities.json', { capabilities: repo(LABELS).labels.map((l) => ({ id: l.capability, owner: l.label })) });
    return { dir, sha: createHash('sha256').update(ledger).digest('hex') };
  }
  const pinned = (sha) => fixture((d) => editJson(d, LEDGER, (l) => { l.pin.sha256 = sha; }));

  it('passes when the spec rows, services, ledger, and labels match', () => {
    const { dir, sha } = reviewDir();
    assert.deepEqual(run(pinned(sha), { reviewRoot: dir }), []);
  });

  it('fails a spec column that is not verbatim and a renamed service', () => {
    const { dir, sha } = reviewDir({ spec: (lines) => { lines[780] = lines[780].replace('Sidebar, notifications', 'Sidebar'); } });
    only(run(pinned(sha), { reviewRoot: dir }), 'AUTH_SPEC_ROW_CHANGED');
    const renamed = reviewDir({ spec: (lines) => { lines[1919] = '- Accounts Service'; } });
    only(run(pinned(renamed.sha), { reviewRoot: renamed.dir }), 'AUTH_PACKAGE_MISMATCH');
  });

  it('fails a ledger that drifted from its pin', () => {
    const { dir, sha } = reviewDir();
    only(run(fixture(), { reviewRoot: dir }), 'AUTH_LEDGER_PIN');
    const edited = reviewDir({ ledger: (seeds) => { seeds[0] = seeds[0].replace('One cohesive end-user platform', 'One platform'); } });
    only(run(pinned(sha), { reviewRoot: edited.dir }), 'AUTH_LEDGER_PIN');
  });

  it('fails closed when a rounds-review file is missing', () => {
    const { dir, sha } = reviewDir();
    fs.rmSync(path.join(dir, REVIEW_LEDGER));
    only(run(pinned(sha), { reviewRoot: dir }), 'AUTH_REVISION_UNAVAILABLE');
  });

  it('matches the rounds-review checkout', { skip: !ROUNDS_REVIEW && 'set ROUNDS_REVIEW_ROOT to a rounds-review checkout' }, () => {
    assert.deepEqual(authority.check(REPO_ROOT, createContext(REPO_ROOT, { base: { files: {} }, reviewRoot: ROUNDS_REVIEW })), []);
  });
});

describe('authority: schemas', () => {
  it('rejects unknown fields and wrong shapes in each data file', () => {
    for (const rel of [MATRIX, PACKAGES, LABELS, LEDGER, STORES, CORRECTIONS]) {
      const schema = repo(rel.replace(/\.json$/, '.schema.json'));
      assert.deepEqual(validate(repo(rel), schema), [], rel);
      assert.ok(validate({ ...repo(rel), unexpected: true }, schema).length, rel);
    }
    only(run(editRow('offer', (r) => { r.scope = 'global'; })), 'AUTH_SHAPE_INVALID');
    only(run(editRow('offer', (r) => { r.consumers.find((c) => c.type === 'export').type = 'webhook'; })), 'AUTH_SHAPE_INVALID');
    only(run(fixture((d) => editJson(d, PACKAGES, (p) => { p.packages[0].target_path = ''; }))), 'AUTH_EMPTY_CELL');
    only(run(editMatrix((m) => { m.rows.push({ ...row(m, 'referral'), target_authority: { record: 'Referral copy', location: 'server' } }); })), 'AUTH_DUPLICATE_ID');
  });
});
