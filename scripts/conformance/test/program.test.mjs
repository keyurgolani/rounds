// Tests for the transformation program files (ROUNDS-01-L03 S1, DR-0003):
// scripts/program/lib.mjs's checks against the committed files and against
// fixture copies that break one rule each, the rollback template, and
// scripts/program/report.mjs's closure computation and CLI.

import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { after, describe, it } from 'node:test';
import { createContext } from '../lib/context.mjs';
import { validate } from '../lib/json-schema.mjs';
import { leafResolver, loadLeafIds } from '../lib/leaf-ids.mjs';
import { cutoverMatches } from '../lib/vocabulary/registry.mjs';
import * as records from '../rules/decision-records.mjs';
import {
  DR_PATH, GATE_IDS, POLICY_PATH, REAUTH_PATH, ROLLBACK_FIXTURE, ROLLBACK_SCHEMA, STAGE_LINES,
  checkProgram, computeClosure, isMerged, loadProgram, pendingEdges, producersOf, readContexts, readEdges, readStages,
  refResolver, rollbackDefaultFindings, stateFrom, titleLabel,
} from '../../program/lib.mjs';
import { main } from '../../program/report.mjs';
import { REPO_ROOT, cleanup, codes, ctxFor, editJson, editText, fixture, readJson, tempDir, writeJson } from './helpers.mjs';

const ROUNDS_REVIEW = process.env.ROUNDS_REVIEW_ROOT || null;
const NON_GOALS = 'docs/program/non-goals.json';
const DOD = 'docs/program/definition-of-done.json';
const JOURNEYS = 'docs/program/journeys.json';

after(cleanup);

const real = () => createContext(REPO_ROOT, { base: 'none' });
const dr = () => readJson(REPO_ROOT, DR_PATH);
const issueLeaf = new Map(readJson(REPO_ROOT, 'contracts/vocabulary/leaf-ids.json').leaves.filter((l) => l.issue).map((l) => [l.issue, l.id]));
const L = (n) => issueLeaf.get(n);

// A fixture copy plus every file a gate artifact row says it lives at.
function programFixture(mutate = () => {}) {
  return fixture((dir) => {
    for (const a of dr().gateArtifacts) {
      for (const rel of a.paths) {
        if (fs.existsSync(path.join(dir, rel))) continue;
        fs.mkdirSync(path.dirname(path.join(dir, rel)), { recursive: true });
        fs.copyFileSync(path.join(REPO_ROOT, rel), path.join(dir, rel));
      }
    }
    mutate(dir);
  });
}
const run = (dir) => checkProgram(ctxFor(dir));
const only = (findings, code) => assert.deepEqual(codes(findings), [code], JSON.stringify(findings, null, 2));
const editDr = (fn) => programFixture((d) => editJson(d, DR_PATH, fn));
const artifact = (record, id) => record.gateArtifacts.find((a) => a.id === id);

describe('program: repository', () => {
  it('passes every program check as committed', () => {
    assert.deepEqual(checkProgram(real()), []);
  });

  it('passes the decision-records rule and records what criterion 3 asks', () => {
    assert.deepEqual(records.check(REPO_ROOT, real()), []);
    const r = dr();
    assert.equal(r.leaf, 'ROUNDS-01-L03');
    assert.equal(r.owner, 'Product Architecture');
    assert.equal(r.authorityBoundary, POLICY_PATH);
    assert.deepEqual(r.prerequisites, ['ROUNDS-01-L01', 'ROUNDS-01-L02']);
    assert.equal(r.affectedPackages.length, 18);
    assert.ok(r.versioning.includes('DR-0003@<revision>:<artifact-id>'));
    assert.ok(r.supersession.length > 0);
    assert.deepEqual(Object.keys(r.securityConsequences).sort(), ['account', 'privacy', 'publicBoundary', 'secret']);
    for (const d of r.decisions) {
      assert.ok(d.alternatives.length >= 1, d.id);
      for (const k of ['consequences', 'migrationImpact', 'rollbackImpact']) assert.ok(d[k].length > 0, `${d.id} ${k}`);
    }
  });

  it('records the delivery order and the disabled leaf-gate rollout', () => {
    const byId = Object.fromEntries(dr().decisions.map((d) => [d.id, d]));
    assert.ok(byId.P1.sources.includes('spec 3070-3097'));
    assert.match(byId.P1.decision, /nine phases of spec 3072-3092/);
    assert.ok(byId.P12.decision.includes("vars.LEAF_GATE_ENABLED == 'true'"));
    assert.equal(byId.P3.status, 'draft');
    assert.equal(byId.P5.status, 'draft');
  });

  it('binds all 20 gate strings, each artifact to exactly one producer', () => {
    const r = dr();
    assert.deepEqual(r.gates.map((g) => g.id), GATE_IDS);
    for (const gate of GATE_IDS) assert.ok(r.gateArtifacts.some((a) => a.gate === gate), gate);
    for (const a of r.gateArtifacts) assert.equal(Number(Boolean(a.producer)) + Number(Boolean(a.producerFrom)), 1, a.id);
    const producers = (gate) => r.gateArtifacts.filter((a) => a.gate === gate).map((a) => a.producer);
    assert.deepEqual(producers('C7'), ['ROUNDS-00A-L01/S4', 'ROUNDS-00B-L01/S4', L(8), L(13)]);
    assert.deepEqual(producers('U8'), ['ROUNDS-00A-L02/1', L(5), L(6)]);
    assert.deepEqual(producers('U9'), [L(11), L(12)]);
  });

  it('resolves per-row producers through DR-0002 instead of copying them', () => {
    const { dr: record, matrix } = loadProgram(real());
    const rows = record.gateArtifacts.filter((a) => a.producerFrom);
    assert.deepEqual(rows.map((a) => a.id), ['U0.erd-rows', 'U1.aggregates', 'U10.mappings']);
    const owners = producersOf(artifact(record, 'U1.aggregates'), matrix);
    assert.ok(owners.includes('ROUNDS-19-L01') && owners.includes('ROUNDS-02-L04'));
    const withOwner = matrix.rows.filter((row) => typeof row.command_owner === 'object');
    assert.equal(new Set(withOwner.map((row) => row.command_owner.leaf)).size, owners.length);
  });

  it('forces U4 on #43 and #130 to #137, U8 on #133 to #135, and U9 on #93, #94, and #161', () => {
    const r = dr();
    const want = { U4: [43, 130, 131, 132, 133, 134, 135, 136, 137], U8: [133, 134, 135], U9: [93, 94, 161] };
    for (const [gate, issues] of Object.entries(want)) {
      for (const a of r.gateArtifacts.filter((x) => x.gate === gate)) assert.deepEqual(a.requiredFor, issues.map(L), a.id);
    }
  });

  it('cites the producers already merged on next and where their artifacts live', () => {
    const r = dr();
    assert.deepEqual(artifact(r, 'C0.inventory').paths, ['docs/security/inventory.md']);
    assert.equal(artifact(r, 'C0.inventory').producer, 'ROUNDS-00A-L01/S0');
    assert.equal(artifact(r, 'C7.admission-deployment').producer, 'ROUNDS-00A-L01/S4');
    assert.equal(artifact(r, 'U11.non-goals').producer, 'ROUNDS-01-L03/S1');
    for (const a of r.gateArtifacts) for (const rel of a.paths) assert.ok(fs.existsSync(path.join(REPO_ROOT, rel)), `${a.id}: ${rel}`);
    assert.equal(artifact(r, 'U11.reference-leaf').producer, L(18));
    assert.equal(artifact(r, 'U11.reference-leaf').designation, 'default');
  });

  it('owns all 16 migration stages with one leaf each', () => {
    const stages = readStages(real());
    assert.deepEqual(stages.map((s) => s.stage), STAGE_LINES.map((_, i) => i + 1));
    assert.deepEqual(stages.map((s) => s.spec), STAGE_LINES);
    for (const s of stages) assert.equal(s.owners.length, 1, `stage ${s.stage}`);
    assert.equal(stages[0].owners[0], L(8));
    assert.equal(stages[15].owners[0], L(164));
    assert.equal(stages[14].owners[0], 'ROUNDS-01-L03');
  });

  it('lists the draft context order, one transfer node per context', () => {
    const contexts = readContexts(real());
    assert.deepEqual(contexts.map((c) => c.context), [
      'share', 'account', 'directory', 'career-profile', 'pipeline', 'campaign', 'people-pursuit-notes', 'actions', 'materials',
      'interview', 'people-round-notes', 'offer', 'practice-0', 'practice-1', 'practice-2', 'practice-3', 'practice-4', 'practice-5', 'practice-6',
    ]);
    assert.deepEqual([...new Set(contexts.map((c) => c.milestone))], [0, 1, 2, 3, 4, 5]);
    assert.deepEqual([...new Set(contexts.map((c) => c.node))], [
      'ROUNDS-00B-L06/S1', 'ROUNDS-32-L05', 'ROUNDS-32-L06/S1', 'ROUNDS-32-L06/S2', 'ROUNDS-32-L06/S3', 'ROUNDS-32-L08/S1', 'ROUNDS-32-L07',
      'ROUNDS-32-L06/S4', 'ROUNDS-32-L06/S5', 'ROUNDS-32-L06/S6', 'ROUNDS-32-L09/P1',
    ]);
  });

  it('maps every journey step to one leaf, milestone, and gate, and traces the first run', () => {
    const j = readJson(REPO_ROOT, JOURNEYS);
    assert.deepEqual(j.journeys.map((x) => x.steps.length), [7, 6, 6, 7, 5]);
    for (const step of j.journeys.flatMap((x) => x.steps)) {
      assert.ok(step.leaf && Number.isInteger(step.milestone) && GATE_IDS.includes(step.gate), step.id);
    }
    assert.deepEqual(j.firstRun.steps.map((s) => s.leaf), [L(145), L(26), L(49), L(65)]);
    assert.equal(j.firstRun.chooser, L(49));
    const completeness = j.journeys[0].steps.find((s) => s.lines === '1030');
    assert.equal(completeness.leaf, L(26));
  });

  it('holds the product non-goals, 38 tradeoffs verbatim, and the reference leaf', () => {
    const ng = readJson(REPO_ROOT, NON_GOALS);
    assert.equal(ng.product.length, 7);
    assert.equal(ng.product.filter((g) => g.product).length, 6);
    assert.equal(ng.tradeoffs.length, 38);
    assert.equal(new Set(ng.tradeoffs.map((t) => t.capability)).size, 36);
    assert.deepEqual(ng.referenceLeaf, { ...ng.referenceLeaf, leaf: L(18), issue: 18, designation: 'default' });
  });

  it('quotes the ROUNDS-32 tradeoff verbatim without an unqualified cutover phrase in the file', () => {
    const raw = fs.readFileSync(path.join(REPO_ROOT, NON_GOALS), 'utf8');
    const quote = JSON.parse(raw).tradeoffs.find((t) => t.capability === 'ROUNDS-32').text;
    // \x20 keeps this test's own source free of the unqualified phrase.
    assert.match(quote, /^A clean\x20cutover requires deliberate gates/);
    assert.equal(cutoverMatches(quote).length, 1);
    assert.deepEqual(cutoverMatches(raw), []);
  });

  it('defines DOD-1 to DOD-7', () => {
    const d = readJson(REPO_ROOT, DOD);
    assert.deepEqual(d.items.map((x) => x.id), ['DOD-1', 'DOD-2', 'DOD-3', 'DOD-4', 'DOD-5', 'DOD-6', 'DOD-7']);
    assert.ok(d.revision >= 1);
  });

  it('orders re-authorization items 1 to 8 and records the edges on #10', () => {
    const text = fs.readFileSync(path.join(REPO_ROOT, REAUTH_PATH), 'utf8');
    assert.deepEqual([...text.matchAll(/^(\d)\. \*\*/gm)].map((m) => Number(m[1])), [1, 2, 3, 4, 5, 6, 7, 8]);
    const edges = readEdges(real());
    const onTen = edges.filter((e) => e.prerequisite === L(10) && e.change === 'add').map((e) => e.dependent);
    assert.deepEqual(onTen, [13, 19, 29, 37, 47].map(L));
    assert.ok(edges.some((e) => e.change === 'drop' && e.dependent === L(18) && e.prerequisite === 'ROUNDS-01-L03'));
  });

  it('keeps every program schema to the keyword subset the validator and #182 support', () => {
    const dir = path.join(REPO_ROOT, 'docs/program');
    const schemas = fs.readdirSync(dir).filter((f) => f.endsWith('.schema.json'));
    assert.equal(schemas.length, 5);
    for (const f of schemas) {
      const text = fs.readFileSync(path.join(dir, f), 'utf8');
      for (const k of ['anyOf', 'oneOf', 'allOf', 'not', 'if', 'then', 'else']) assert.doesNotMatch(text, new RegExp(`"${k}"\\s*:`), `${f} uses ${k}`);
    }
  });
});

describe('program: failing fixtures', () => {
  it('passes on an unmodified fixture copy', () => {
    assert.deepEqual(run(programFixture()), []);
  });

  it('fails PROGRAM_PRODUCER for an artifact without a producer or with two', () => {
    only(run(editDr((r) => { artifact(r, 'U0.adr').producer = null; })), 'PROGRAM_PRODUCER');
    only(run(editDr((r) => { artifact(r, 'U0.adr').producerFrom = 'contracts/authority/matrix.json#command_owner.leaf'; })), 'PROGRAM_PRODUCER');
  });

  it('fails PROGRAM_PRODUCER when a per-row producer field names no leaf', () => {
    const dir = programFixture((d) => editJson(d, 'contracts/authority/matrix.json', (m) => { for (const row of m.rows) delete row.transfer; }));
    const findings = run(dir);
    only(findings, 'PROGRAM_PRODUCER');
    assert.match(findings[0].message, /U10\.mappings/);
  });

  it('fails PROGRAM_UNRESOLVED_REF on an unknown or rejected producer', () => {
    only(run(editDr((r) => { artifact(r, 'U0.adr').producer = 'ROUNDS-99-L99'; })), 'PROGRAM_UNRESOLVED_REF');
    const rejected = run(editDr((r) => { artifact(r, 'U5.source-anchor').producer = 'ROUNDS-26-L05'; }));
    only(rejected, 'PROGRAM_UNRESOLVED_REF');
    assert.match(rejected[0].message, /rejected/);
  });

  it('fails PROGRAM_GATE_UNBOUND when a gate has no artifact', () => {
    const findings = run(editDr((r) => { r.gateArtifacts = r.gateArtifacts.filter((a) => a.gate !== 'U8'); }));
    only(findings, 'PROGRAM_GATE_UNBOUND');
    assert.match(findings[0].message, /gate U8 has no artifact/);
    assert.ok(codes(run(editDr((r) => { r.gates = r.gates.filter((g) => g.id !== 'U5'); }))).includes('PROGRAM_GATE_UNBOUND'));
  });

  it('fails PROGRAM_REQUIRED_FOR when a forced binding is dropped', () => {
    only(run(editDr((r) => { artifact(r, 'U4.pack-contract').requiredFor = artifact(r, 'U4.pack-contract').requiredFor.filter((l) => l !== L(43)); })), 'PROGRAM_REQUIRED_FOR');
  });

  it('fails PROGRAM_PATH_MISSING for an artifact path that does not exist', () => {
    only(run(editDr((r) => { artifact(r, 'C0.inventory').paths.push('docs/security/not-there.md'); })), 'PROGRAM_PATH_MISSING');
  });

  it('fails PROGRAM_STAGE_UNOWNED for a stage without one owner, or a missing stage', () => {
    const swap = (fn) => programFixture((d) => editText(d, POLICY_PATH, fn));
    only(run(swap((t) => t.replace(/(\| 7 \| 2683-2684 \|[^|]*\| )`ROUNDS-32-L02`/, '$1none'))), 'PROGRAM_STAGE_UNOWNED');
    only(run(swap((t) => t.replace(/(\| 13 \| 2691 \|[^|]*\| )`ROUNDS-34-L05`/, '$1`ROUNDS-34-L05`, `ROUNDS-31-L09`'))), 'PROGRAM_STAGE_UNOWNED');
    only(run(swap((t) => t.replace(/^\| 16 \| 2694-2695 .*\n/m, ''))), 'PROGRAM_STAGE_UNOWNED');
  });

  it('fails PROGRAM_CONTEXT_ORDER for a context listed twice, out of milestone order, or a split node', () => {
    const swap = (fn) => programFixture((d) => editText(d, POLICY_PATH, fn));
    const twice = run(swap((t) => t.replace(/^(\| 19 \| 5 \| `practice-6` .*)$/m, '$1\n| 20 | 5 | `account` | `ROUNDS-32-L09/P1` | test |')));
    only(twice, 'PROGRAM_CONTEXT_ORDER');
    assert.match(twice[0].message, /account is listed twice/);
    const backwards = run(swap((t) => t.replace('| 9 | 3 | `materials`', '| 9 | 1 | `materials`')));
    only(backwards, 'PROGRAM_CONTEXT_ORDER');
    const split = run(swap((t) => t.replace('| 4 | 1 | `career-profile` | `ROUNDS-32-L05`', '| 4 | 1 | `career-profile` | `ROUNDS-00B-L06/S1`')));
    only(split, 'PROGRAM_CONTEXT_ORDER');
  });

  it('fails when a journey step loses its leaf, gate, or completing leaf, or the first run gains a second chooser', () => {
    const edit = (fn) => programFixture((d) => editJson(d, JOURNEYS, fn));
    only(run(edit((j) => { delete j.journeys[1].steps[2].leaf; })), 'PROGRAM_FILE_INVALID');
    only(run(edit((j) => { j.journeys[1].steps[2].gate = 'U12'; })), 'PROGRAM_FILE_INVALID');
    only(run(edit((j) => { j.journeys[0].completingLeaf = L(26); j.journeys[0].steps[0].milestone = 0; j.journeys[0].steps[6].milestone = 0; })), 'PROGRAM_JOURNEY_UNMAPPED');
    only(run(edit((j) => { j.firstRun.steps.push({ id: 'FR.5', surface: 'A second chooser', leaf: L(49), milestone: 1, gate: 'U1' }); })), 'PROGRAM_JOURNEY_UNMAPPED');
  });

  it('fails PROGRAM_REGISTER when a DOD item is dropped or the reference leaf disagrees', () => {
    only(run(programFixture((d) => editJson(d, DOD, (x) => { x.items.splice(2, 1); }))), 'PROGRAM_REGISTER');
    only(run(programFixture((d) => editJson(d, NON_GOALS, (x) => { x.referenceLeaf.leaf = L(19); x.referenceLeaf.issue = 19; }))), 'PROGRAM_REGISTER');
  });

  it('fails PROGRAM_EDGE_INVALID or PROGRAM_UNRESOLVED_REF for a bad edge row', () => {
    const swap = (fn) => programFixture((d) => editText(d, REAUTH_PATH, fn));
    only(run(swap((t) => t.replace('| E7 | add | `ROUNDS-34-L07` | `ROUNDS-32-L10` | done |', '| E7 | add | `ROUNDS-34-L07` | `ROUNDS-32-L10` | soon |'))), 'PROGRAM_EDGE_INVALID');
    only(run(swap((t) => t.replace('| E7 | add | `ROUNDS-34-L07` | `ROUNDS-32-L10` |', '| E7 | add | `ROUNDS-34-L07` | `ROUNDS-32-L99` |'))), 'PROGRAM_UNRESOLVED_REF');
    only(run(swap((t) => t.replace('| E5 | add | `ROUNDS-27-L02` | `ROUNDS-09` |', '| E5 | add | `ROUNDS-27-L02` | `ROUNDS-99` |'))), 'PROGRAM_UNRESOLVED_REF');
  });

  it('fails DR_APPROVAL_STALE when a governed program file changes after ratification', () => {
    const r = dr();
    assert.equal(r.status, 'ratified');
    assert.ok(r.approvalRef.governedFiles.some((g) => g.path === POLICY_PATH));
    const recordRun = (dir) => records.check(dir, ctxFor(dir));
    only(recordRun(programFixture((d) => editText(d, POLICY_PATH, (t) => `${t}\nAn unapproved edit.\n`))), 'DR_APPROVAL_STALE');
    only(recordRun(programFixture((d) => editJson(d, DOD, (x) => { x.items.pop(); }))), 'DR_APPROVAL_STALE');
  });

  it('fails DR_RECORD_INCOMPLETE when DR-0003 loses a field criterion 3 or the security section asks for', () => {
    const recordRun = (dir) => records.check(dir, ctxFor(dir));
    for (const field of ['owner', 'authorityBoundary', 'affectedPackages', 'versioning', 'supersession', 'securityConsequences']) {
      const findings = recordRun(editDr((r) => { delete r[field]; }));
      assert.ok(codes(findings).includes('DR_RECORD_INCOMPLETE'), `${field}: ${JSON.stringify(codes(findings))}`);
    }
    for (const field of ['alternatives', 'consequences', 'migrationImpact', 'rollbackImpact']) {
      assert.ok(codes(recordRun(editDr((r) => { delete r.decisions[1][field]; }))).includes('DR_RECORD_INCOMPLETE'), field);
    }
    for (const key of ['account', 'privacy', 'secret', 'publicBoundary']) {
      assert.ok(codes(recordRun(editDr((r) => { delete r.securityConsequences[key]; }))).includes('DR_RECORD_INCOMPLETE'), key);
    }
  });
});

describe('program: rollback template', () => {
  const schema = readJson(REPO_ROOT, ROLLBACK_SCHEMA);
  const synthetic = readJson(REPO_ROOT, ROLLBACK_FIXTURE);

  it('accepts the synthetic fixture', () => {
    assert.deepEqual(validate(synthetic, schema), []);
    assert.deepEqual(rollbackDefaultFindings(synthetic), []);
  });

  it('rejects a copy missing any field', () => {
    for (const field of schema.required) {
      const copy = structuredClone(synthetic);
      delete copy[field];
      assert.ok(validate(copy, schema).some((e) => e.keyword === 'required' && e.property === field), field);
    }
    assert.ok(schema.required.length >= 13 + 4);
  });

  it('needs an owner-approved deviation to loosen a default', () => {
    const loose = { ...structuredClone(synthetic), allowedDowntime: { freezeMinutes: 20, readsDuringFreeze: 'available' } };
    assert.match(rollbackDefaultFindings(loose)[0].message, /freezeMinutes is 20/);
    loose.deviations = [{ field: 'allowedDowntime.freezeMinutes', value: 20, default: 15, approvedBy: 'owner (test)', reason: 'test' }];
    assert.deepEqual(rollbackDefaultFindings(loose), []);
    assert.deepEqual(validate(loose, schema), []);
    assert.equal(rollbackDefaultFindings({ ...synthetic, backupConsistency: { ...synthetic.backupConsistency, restoreRehearsed: false } }).length, 1);
  });

  it('holds placeholder digests only', () => {
    for (const image of synthetic.upgradeSource.images) assert.equal(image.digest, `sha256:${'0'.repeat(64)}`);
    assert.equal(synthetic.upgradeSource.commit, '0000000');
  });

  it('fails PROGRAM_ROLLBACK_INVALID and PROGRAM_ROLLBACK_DEFAULT in the fixture file', () => {
    only(run(programFixture((d) => editJson(d, ROLLBACK_FIXTURE, (x) => { delete x.journal; }))), 'PROGRAM_ROLLBACK_INVALID');
    only(run(programFixture((d) => editJson(d, ROLLBACK_FIXTURE, (x) => { x.recoveryTimeObjective.minutes = 45; }))), 'PROGRAM_ROLLBACK_DEFAULT');
  });
});

describe('program: report', () => {
  const registry = readJson(REPO_ROOT, 'contracts/vocabulary/leaf-ids.json');
  const pull = (title, state = 'MERGED') => ({ number: 1, title, state });

  it('parses leaf, stage, and multi-PR stage labels from titles', () => {
    assert.deepEqual(titleLabel('docs(program): x [ROUNDS-01-L03/S1]'), { leaf: 'ROUNDS-01-L03', stage: 'S1', ref: 'ROUNDS-01-L03/S1' });
    assert.equal(titleLabel('chore: y [ROUNDS-32-L10/SB.3]').ref, 'ROUNDS-32-L10/SB.3');
    assert.equal(titleLabel('feat(runner): z [ROUNDS-00A-L02/1]').ref, 'ROUNDS-00A-L02/1');
    assert.equal(titleLabel('docs(x): w [ROUNDS-01-L02]').ref, 'ROUNDS-01-L02');
    assert.equal(titleLabel('fix(guides): no label'), null);
  });

  it('counts merged PRs, finishing squash messages, and completed issues, and nothing else', () => {
    const state = stateFrom({
      pulls: [pull('a [ROUNDS-02-L01]'), pull('b [ROUNDS-02-L02]', 'OPEN'), pull('c [ROUNDS-00A-L01/S2]')],
      issues: [{ number: 20, state: 'CLOSED', stateReason: 'COMPLETED' }, { number: 21, state: 'CLOSED', stateReason: 'NOT_PLANNED' }],
      commits: ['test(runner): finished [ROUNDS-00B-L01/S4] (#193)\n\nCloses #9', { message: 'Fixes #22' }],
    }, registry);
    assert.ok(isMerged(L(18), state));
    assert.ok(!isMerged(L(19), state));
    assert.ok(isMerged('ROUNDS-00A-L01/S2', state));
    assert.ok(!isMerged(L(1), state));
    assert.ok(isMerged(L(20), state) && isMerged(`${L(20)}/S1`, state));
    assert.ok(!isMerged(L(21), state));
    assert.ok(isMerged(L(9), state) && isMerged(`${L(9)}/S2`, state));
    assert.ok(isMerged(L(22), state));
  });

  // Every producer and closure leaf merged, through titles alone.
  function allMerged(except = []) {
    const program = loadProgram(real());
    const refs = new Set(program.dr.closure.leaves);
    for (const a of program.dr.gateArtifacts) for (const ref of producersOf(a, program.matrix)) refs.add(ref);
    return { program, data: { pulls: [...refs].filter((r) => !except.includes(r)).map((r) => pull(`x [${r}]`)), issues: [] } };
  }

  it('reports ROUNDS-01 open until every closure leaf and U0 to U11 producer has merged', () => {
    const resolve = refResolver(real());
    const { program, data } = allMerged();
    const closed = computeClosure(program, stateFrom(data, registry), resolve);
    assert.equal(closed.closed, true);
    assert.equal(closed.met, closed.total);
    const empty = computeClosure(program, stateFrom({}, registry), resolve);
    assert.equal(empty.closed, false);
    assert.equal(empty.met, 0);
    assert.equal(empty.total, 3 + program.dr.gateArtifacts.filter((a) => a.gate.startsWith('U')).length);
    const missing = allMerged(['ROUNDS-31-L09']);
    const open = computeClosure(missing.program, stateFrom(missing.data, registry), resolve);
    assert.equal(open.closed, false);
    assert.deepEqual(open.artifacts.filter((a) => !a.met).map((a) => a.id), ['U0.erd-rows', 'U1.aggregates']);
    const s4 = allMerged(['ROUNDS-01-L03/S4']);
    assert.equal(computeClosure(s4.program, stateFrom(s4.data, registry), resolve).closed, false);
  });

  it('keeps containment gates out of closure', () => {
    const { program, data } = allMerged();
    const containmentOnly = new Set(program.dr.gateArtifacts.filter((a) => a.gate.startsWith('C')).flatMap((a) => producersOf(a, program.matrix)));
    const universal = new Set(program.dr.gateArtifacts.filter((a) => a.gate.startsWith('U')).flatMap((a) => producersOf(a, program.matrix)));
    const ref = [...containmentOnly].find((r) => !universal.has(r) && !program.dr.closure.leaves.includes(r));
    assert.ok(ref, 'a producer only containment gates name');
    const state = stateFrom({ pulls: data.pulls.filter((p) => !p.title.includes(`[${ref}]`)), issues: [] }, registry);
    const result = computeClosure(program, state, refResolver(real()));
    assert.equal(result.closed, true);
    assert.ok(result.containment.some((a) => !a.met));
  });

  it('lists the edge table as pending with each prerequisite state', () => {
    const program = loadProgram(real());
    const edges = pendingEdges(program, stateFrom({ pulls: [pull('x [ROUNDS-00A-L01/S5]')], issues: [] }, registry), refResolver(real()));
    assert.equal(edges.length, program.edges.length);
    assert.equal(edges.find((e) => e.id === 'E10').prerequisiteMerged, true);
    assert.equal(edges.find((e) => e.id === 'E5').prerequisiteMerged, false);
  });

  const capture = () => {
    const io = { text: '', errText: '' };
    io.out = { write: (s) => { io.text += s; } };
    io.err = { write: (s) => { io.errText += s; } };
    return io;
  };

  it('prints closure, pending edges, and drift from a saved state file', () => {
    const file = path.join(tempDir(), 'state.json');
    writeJson(path.dirname(file), path.basename(file), { pulls: [pull('x [ROUNDS-01-L01]'), pull('y [ROUNDS-01-L02]')], issues: [], commits: [] });
    const io = capture();
    assert.equal(main(['--state', file, '--root', REPO_ROOT], io), 0, io.errText);
    assert.match(io.text, /^ROUNDS-01 closure: open \(2 of \d+ conditions met; closure gates no leaf\)/);
    assert.match(io.text, /leaves: ROUNDS-01-L01 merged, ROUNDS-01-L02 merged, ROUNDS-01-L03\/S4 open/);
    assert.match(io.text, /Pending edges: 26,/);
    assert.match(io.text, /\nDrift: none\n$/);
    const json = capture();
    assert.equal(main(['--state', file, '--root', REPO_ROOT, '--json'], json), 0);
    const parsed = JSON.parse(json.text);
    assert.equal(parsed.closure.closed, false);
    assert.deepEqual(parsed.drift, []);
  });

  it('reports drift from a broken fixture', () => {
    const dir = programFixture((d) => editJson(d, DR_PATH, (r) => { artifact(r, 'U0.adr').producer = 'ROUNDS-99-L99'; }));
    const file = path.join(tempDir(), 'state.json');
    fs.writeFileSync(file, JSON.stringify({ pulls: [], issues: [] }));
    const io = capture();
    assert.equal(main(['--state', file, '--root', dir], io), 0);
    assert.match(io.text, /Drift: 1\n {2}PROGRAM_UNRESOLVED_REF docs\/decisions\/DR-0003-transformation-program\.json:\d+ /);
  });

  it('exits 2 on bad arguments or an unreadable state file', () => {
    const missing = capture();
    assert.equal(main(['--state', path.join(tempDir(), 'none.json')], missing), 2);
    assert.match(missing.errText, /cannot read PR and issue state/);
    const bad = capture();
    assert.equal(main(['--bogus'], bad), 2);
    assert.match(bad.errText, /unknown argument --bogus/);
    const shape = capture();
    const file = path.join(tempDir(), 'state.json');
    fs.writeFileSync(file, JSON.stringify({ pulls: [] }));
    assert.equal(main(['--state', file], shape), 2);
    assert.match(shape.errText, /needs "pulls" and "issues" arrays/);
    assert.equal(main(['--state'], capture()), 2);
  });
});

// Verbatim text against the approved rounds-review checkout.
describe('program: approved sources', { skip: !ROUNDS_REVIEW && 'set ROUNDS_REVIEW_ROOT to a rounds-review checkout' }, () => {
  const lines = (rel) => fs.readFileSync(path.join(ROUNDS_REVIEW, rel), 'utf8').split('\n');
  const spec = () => lines('docs/superpowers/specs/2026-10-18-rounds-review-board-design.md');
  // List items from..to: "- x" or "N. x" with indented continuation lines.
  const items = (src, from, to, marker) => {
    const out = [];
    for (let i = from; i <= to; i++) {
      const l = src[i - 1];
      const m = marker.exec(l);
      if (m) out.push({ start: i, end: i, text: m[1].trim() });
      else if (/^\s+\S/.test(l) && out.length) { out[out.length - 1].text += ` ${l.trim()}`; out[out.length - 1].end = i; }
    }
    return out;
  };
  const span = (x) => (x.start === x.end ? `${x.start}` : `${x.start}-${x.end}`);

  it('quotes the 20 gate strings of capabilities.ts:185-209', () => {
    const ts = lines('src/data/capabilities.ts');
    for (const g of dr().gates) {
      const line = Number(g.source.split(':').pop());
      assert.equal(ts[line - 1].trim(), `"${g.text}",`, g.id);
    }
    assert.match(ts[184], /^export const containmentGateRequirements = \[/);
    assert.match(ts[195], /^export const universalGateRequirements = \[/);
  });

  it('quotes the product non-goals and every catalog tradeoff verbatim', () => {
    const strip = (x) => ({ lines: span(x), text: x.text.replace(/(; or|;|\.)$/, '') });
    const fromSpec = items(spec(), 177, 184, /^- (.+)$/).map(strip);
    const fromProduct = items(lines('PRODUCT.md'), 211, 217, /^- (.+)$/).map(strip);
    const ng = readJson(REPO_ROOT, NON_GOALS);
    assert.deepEqual(ng.product.map((g) => g.spec), fromSpec);
    assert.deepEqual(ng.product.filter((g) => g.product).map((g) => g.product), fromProduct);
    const catalog = JSON.parse(fs.readFileSync(path.join(ROUNDS_REVIEW, 'src/data/capabilities.json'), 'utf8'));
    assert.deepEqual(ng.tradeoffs, catalog.capabilities.flatMap((c) => c.tradeoffs.map((text) => ({ capability: c.id, text }))));
  });

  it('quotes every journey step and migration stage verbatim', () => {
    const src = spec();
    const steps = items(src, 1019, 1071, /^\d+\. (.+)$/);
    assert.deepEqual(readJson(REPO_ROOT, JOURNEYS).journeys.flatMap((j) => j.steps).map((s) => ({ lines: s.lines, text: s.text })), steps.map((s) => ({ lines: span(s), text: s.text })));
    const stages = items(src, 2677, 2695, /^\d+\. (.+)$/);
    assert.deepEqual(readStages(real()).map((s) => ({ spec: s.spec, step: s.step })), stages.map((s) => ({ spec: span(s), step: s.text })));
  });

  it('resolves every leaf the program names in the catalog leaf list', () => {
    const resolve = leafResolver(loadLeafIds(real()));
    const program = loadProgram(real());
    const refs = [
      ...program.dr.gateArtifacts.flatMap((a) => [...producersOf(a, program.matrix), ...a.requiredFor]),
      ...program.stages.flatMap((s) => [...s.owners, ...s.with]),
      ...program.contexts.map((c) => c.node),
    ];
    for (const ref of refs) assert.ok(resolve(ref).ok, ref);
  });
});
