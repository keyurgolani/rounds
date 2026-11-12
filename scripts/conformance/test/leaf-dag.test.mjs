// Tests for the leaf DAG (ROUNDS-01-L03 S2): the committed export and DAG,
// the section parser in scripts/program/dag.mjs, the export trimmer, and
// scripts/conformance/rules/program.mjs against fixture copies that break
// one rule each.

import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { after, describe, it } from 'node:test';
import { canonical, createContext, sha256 } from '../lib/context.mjs';
import { runConformance, parseArgs } from '../run.mjs';
import * as program from '../rules/program.mjs';
import {
  DAG_PATH, EXPORT_PATH, GATE_PATH, INPUTS_PATH, buildDag, clauseRefs, exportDigest, findCycles, parseSection,
  prerequisiteSection, renderDag, stageGraph, trimExport,
} from '../../program/dag.mjs';
import { main as exportMain } from '../../program/export.mjs';
import { REPO_ROOT, cleanup, codes, ctxFor, editJson, editText, fixture, readJson, tempDir, writeJson } from './helpers.mjs';

after(cleanup);

const dag = () => readJson(REPO_ROOT, DAG_PATH);
const node = (d, issue) => d.nodes.find((n) => n.issue === issue);
const prereqs = (d, issue) => node(d, issue).filedPrerequisites.map((e) => e.prerequisite);
const run = (dir) => program.check(dir, ctxFor(dir));
const only = (findings, code) => assert.deepEqual(codes(findings), [code], JSON.stringify(findings.slice(0, 5), null, 2));
const issueLeaf = new Map(readJson(REPO_ROOT, 'contracts/vocabulary/leaf-ids.json').leaves.filter((l) => l.issue).map((l) => [l.issue, l.id]));

describe('leaf DAG: repository', () => {
  it('is exactly what the export and leaf-program.json produce, and the program rule is clean', () => {
    const ctx = createContext(REPO_ROOT, { base: 'none' });
    assert.deepEqual(program.check(REPO_ROOT, ctx), []);
    const [out] = program.generate(REPO_ROOT, ctx);
    assert.equal(out.path, DAG_PATH);
    assert.equal(out.content, fs.readFileSync(path.join(REPO_ROOT, DAG_PATH), 'utf8'));
  });

  it('has one node per filed and proposed leaf, the five folded ids dropped, and no cycle', () => {
    const d = dag();
    assert.equal(d.nodes.length, 182);
    assert.deepEqual(d.nodes.map((n) => n.issue), Array.from({ length: 182 }, (_, i) => i + 1));
    assert.deepEqual(d.dropped.map((x) => x.id).sort(), ['ROUNDS-00A-L09', 'ROUNDS-04-L05', 'ROUNDS-14-L08', 'ROUNDS-24-L05', 'ROUNDS-26-L05']);
    assert.deepEqual(findCycles(stageGraph(d)), []);
    assert.equal(d.edgeSet, 'filed');
    for (const n of d.nodes) for (const e of n.filedPrerequisites) assert.ok(e.reason.trim(), `${n.id} on ${e.prerequisite}`);
  });

  it('pins the export it was built from, and the export pins its own issues', () => {
    const exp = readJson(REPO_ROOT, EXPORT_PATH);
    assert.equal(exp.sha256, exportDigest(exp.issues));
    assert.equal(dag().source.exportSha256, exp.sha256);
    assert.equal(dag().source.inputsSha256, sha256(canonical(readJson(REPO_ROOT, INPUTS_PATH))));
    assert.equal(exp.issues.length, 182);
    for (const i of exp.issues) assert.deepEqual(Object.keys(i).sort(), ['number', 'prerequisites', 'title']);
  });

  it('lists the stages of the staged leaves the brief names, and #17 dependents wait on S2', () => {
    const d = dag();
    const want = { 1: ['S0', 'S1', 'S2', 'S3', 'S4', 'S5'], 2: ['1', '2', '3'], 3: ['1', '2', '3', '4'], 4: ['1', '2', '3'], 8: ['S1', 'S2'], 9: ['S1', 'S2', 'S3', 'S4'], 11: ['S1', 'S2'], 17: ['S1', 'S2', 'S3', 'S4'], 177: ['S1', 'S2', 'S3', 'S4'] };
    for (const [issue, stages] of Object.entries(want)) {
      assert.deepEqual(node(d, Number(issue)).stages, stages, `#${issue}`);
      assert.equal(node(d, Number(issue)).stagesComplete, true, `#${issue}`);
    }
    assert.deepEqual(node(d, 17).satisfiedBy, ['S2']);
    assert.ok(prereqs(d, 25).includes('ROUNDS-01-L03'));
  });

  it('reads stage-scoped edges and stage prerequisites from the bodies', () => {
    const d = dag();
    const e = (issue, ref) => node(d, issue).filedPrerequisites.find((x) => x.prerequisite === ref);
    assert.deepEqual(e(1, 'ROUNDS-00B-L01').forStages, ['S4']);
    assert.deepEqual(e(9, 'ROUNDS-00A-L01/S5').forStages, ['S3']);
    assert.ok(e(18, 'ROUNDS-00A-L01/S3'));
    assert.ok(e(19, 'ROUNDS-01-L03/S2'));
    assert.deepEqual(e(8, 'ROUNDS-00A-L07').forStages, ['S2']);
    assert.ok(!prereqs(d, 2).includes('ROUNDS-00A-L03'), '#2 lists #3 only as downstream');
    assert.ok(!prereqs(d, 18).includes('ROUNDS-01-L03'), '#18 drops its filed edge on #17');
  });

  it('resolves both #N and leaf-id references in the refinement-created leaves #177 to #182', () => {
    const d = dag();
    assert.ok(prereqs(d, 177).includes('ROUNDS-00B-L01'), '#177 names #9 by number');
    assert.ok(prereqs(d, 177).includes('ROUNDS-00A-L01/S3'), '#177 names #1 stage 3');
    assert.ok(prereqs(d, 178).includes('ROUNDS-02-L06'), '#178 names a leaf-id range');
    assert.ok(prereqs(d, 179).includes('ROUNDS-14-L02/SC'), '#179 names #73 stage C');
    assert.ok(prereqs(d, 180).includes('ROUNDS-06-L02'));
    assert.ok(prereqs(d, 181).includes('ROUNDS-19-L02'), '#181 names leaf ids beside issue numbers');
    assert.ok(!prereqs(d, 181).includes('ROUNDS-27-L04'), '#181 blocks #129, not the other way');
    assert.ok(prereqs(d, 182).includes('ROUNDS-34-L01/S1'));
  });

  it('assigns each leaf a program phase and milestone, pulling prerequisites earlier', () => {
    const d = dag();
    for (const n of d.nodes) {
      assert.ok(n.phase >= 1 && n.phase <= 9, n.id);
      assert.ok(n.milestone >= 0 && n.milestone <= 7, n.id);
      for (const e of n.filedPrerequisites.filter((x) => !x.forStages)) {
        const p = d.nodes.find((x) => x.id === e.prerequisite.split('/')[0]);
        assert.ok(p.phase <= n.phase, `${p.id} (phase ${p.phase}) lands after ${n.id} (phase ${n.phase})`);
      }
    }
    assert.equal(node(d, 1).phase, 1);
    assert.equal(node(d, 17).phase, 2);
    assert.equal(node(d, 19).phase, 3);
    assert.equal(node(d, 164).phase, 9);
    assert.equal(node(d, 9).milestone, 0);
  });
});

describe('leaf DAG: section parser', () => {
  it('expands issue and leaf-id ranges and the -Lnn shorthand', () => {
    const refs = clauseRefs('#19 to #22 (`ROUNDS-02-L02` to `L05`), `ROUNDS-15-L02`, `-L03`', issueLeaf).flatMap((r) => r.ids);
    assert.deepEqual([...new Set(refs)], ['ROUNDS-02-L02', 'ROUNDS-02-L03', 'ROUNDS-02-L04', 'ROUNDS-02-L05', 'ROUNDS-15-L02', 'ROUNDS-15-L03']);
  });

  it('reads a stage qualifier after a reference', () => {
    const [r] = clauseRefs("#1's stage 3", issueLeaf);
    assert.deepEqual(r.qualifier, [{ kind: 'S', value: '3' }]);
    const [p] = clauseRefs('#91 (`ROUNDS-18-L03`, export, Stage 1 only)', issueLeaf);
    assert.deepEqual(p.qualifier, [{ kind: 'S', value: '1' }]);
  });

  it('skips downstream, dropped, transitive, and other-leaf statements', () => {
    const text = [
      '- #1 (`ROUNDS-00A-L01`, route auth): the account dependency.',
      '',
      'Downstream: #3 to #6; for rendering #78.',
      '#17 (`ROUNDS-01-L03`) consumes this ADR, so its filed edge is dropped.',
      'Transitive: #9.',
      '#29 isn\'t a prerequisite; its events are stubbed.',
    ].join('\n');
    const { edges } = parseSection(text, 'ROUNDS-02-L01', issueLeaf);
    assert.deepEqual(edges.map((e) => e.prerequisite.id), ['ROUNDS-00A-L01']);
  });

  it('scopes edges to the stages a line names, and keeps "only" stages to their own list', () => {
    const text = ['- Stage 1: #1 (`ROUNDS-00A-L01`, route auth).', '- Stage 2 adds #2 (`ROUNDS-00A-L02`, definitions).', '- #9 (`ROUNDS-00B-L01`, harness)', '', 'PR 1 needs only #15.'].join('\n');
    const { edges, exclusive } = parseSection(text, 'ROUNDS-34-L01', issueLeaf);
    const scope = (id) => edges.find((e) => e.prerequisite.id === id).forStages;
    assert.deepEqual(scope('ROUNDS-00A-L01').tokens, [{ kind: 'S', value: '1' }]);
    assert.deepEqual(scope('ROUNDS-00A-L02').tokens, [{ kind: 'S', value: '2' }]);
    assert.equal(scope('ROUNDS-00B-L01'), null);
    assert.deepEqual(exclusive, [[{ kind: 'P', value: '1' }]]);
  });

  it('finds the section in a body, and trims an export to number, title, and that section', () => {
    const body = '# T\n\n## Dependencies and sequencing\n\n### Exact prerequisite leaf issues\n\n- #1\n\n### Parent capability dependencies\n\n- None.\n';
    assert.equal(prerequisiteSection(body), '- #1');
    assert.equal(prerequisiteSection('# no section'), null);
    const exp = trimExport([{ number: 2, title: '[ROUNDS-00A-L02] B', body }, { number: 1, title: '[ROUNDS-00A-L01] A', body: 'secret body text' }], { repo: 'owner/repo', exportedOn: '2026-11-11' });
    assert.deepEqual(exp.issues, [{ number: 1, title: '[ROUNDS-00A-L01] A', prerequisites: null }, { number: 2, title: '[ROUNDS-00A-L02] B', prerequisites: '- #1' }]);
    assert.equal(exp.sha256, exportDigest(exp.issues));
    assert.doesNotMatch(JSON.stringify(exp), /secret body text|Parent capability/);
  });

  it('export.mjs writes the export from a saved gh file and refuses bad input', () => {
    const dir = tempDir();
    fs.mkdirSync(path.join(dir, 'docs/program'), { recursive: true });
    const from = path.join(dir, 'issues.json');
    fs.writeFileSync(from, JSON.stringify([{ number: 1, title: '[ROUNDS-00A-L01] A', body: '### Exact prerequisite leaf issues\n\n- None.\n' }]));
    const sink = { out: { write() {} }, err: { write() {} } };
    assert.equal(exportMain(['--from', from, '--root', dir, '--exported-on', '2026-11-11', '--write'], sink), 0);
    assert.equal(readJson(dir, EXPORT_PATH).issues[0].prerequisites, '- None.');
    fs.writeFileSync(from, '{"not":"an array"}');
    assert.equal(exportMain(['--from', from, '--root', dir, '--write'], sink), 2);
    assert.equal(exportMain([], sink), 2);
  });

  it('reports an export reference that names no leaf, and a stale edge override', () => {
    const exportFile = readJson(REPO_ROOT, EXPORT_PATH);
    const inputs = readJson(REPO_ROOT, INPUTS_PATH);
    const registry = readJson(REPO_ROOT, 'contracts/vocabulary/leaf-ids.json');
    exportFile.issues[14].prerequisites = '- #999 (unknown).';
    inputs.edges.drop.push({ dependent: 'ROUNDS-01-L01', prerequisite: 'ROUNDS-02-L01', reason: 'no such edge' });
    assert.deepEqual(codes(buildDag({ exportFile, inputs, registry }).findings), ['PROGRAM_OVERRIDE_STALE', 'PROGRAM_UNRESOLVED_REF']);
  });
});

describe('leaf DAG: failing fixtures', () => {
  const editDag = (fn) => fixture((d) => editJson(d, DAG_PATH, fn));
  const nodeIn = (x, issue) => x.nodes.find((n) => n.issue === issue);

  it('passes on an unmodified fixture copy', () => {
    assert.deepEqual(run(fixture()), []);
  });

  it('fails PROGRAM_DAG_CYCLE for a cycle across leaves and for a self edge', () => {
    only(run(editDag((x) => { nodeIn(x, 15).filedPrerequisites.push({ prerequisite: 'ROUNDS-01-L03', reason: 'a test cycle', source: 'test' }); })), 'PROGRAM_DAG_CYCLE');
    only(run(editDag((x) => { nodeIn(x, 16).filedPrerequisites.push({ prerequisite: 'ROUNDS-01-L02', reason: 'itself', source: 'test' }); })), 'PROGRAM_DAG_CYCLE');
  });

  it('fails PROGRAM_DAG_UNKNOWN for an unknown leaf, an unknown stage, or a stage the dependent lacks', () => {
    only(run(editDag((x) => { nodeIn(x, 16).filedPrerequisites.push({ prerequisite: 'ROUNDS-99-L99', reason: 'unknown', source: 'test' }); })), 'PROGRAM_DAG_UNKNOWN');
    only(run(editDag((x) => { nodeIn(x, 16).filedPrerequisites.push({ prerequisite: 'ROUNDS-01-L03/S9', reason: 'no such stage', source: 'test' }); })), 'PROGRAM_DAG_UNKNOWN');
    only(run(editDag((x) => { nodeIn(x, 16).filedPrerequisites[0].forStages = ['S1']; })), 'PROGRAM_DAG_UNKNOWN');
  });

  it('fails PROGRAM_DAG_DUPLICATE for a node or an edge listed twice', () => {
    only(run(editDag((x) => { x.nodes.push(structuredClone(nodeIn(x, 15))); })), 'PROGRAM_DAG_DUPLICATE');
    only(run(editDag((x) => { const n = nodeIn(x, 16); n.filedPrerequisites.push(structuredClone(n.filedPrerequisites[0])); })), 'PROGRAM_DAG_DUPLICATE');
  });

  it('fails PROGRAM_DAG_DROPPED for a folded id as a node or a prerequisite, or missing from dropped', () => {
    only(run(editDag((x) => { x.nodes.push({ ...structuredClone(nodeIn(x, 1)), id: 'ROUNDS-00A-L09', issue: 999 }); })), 'PROGRAM_DAG_DROPPED');
    only(run(editDag((x) => { nodeIn(x, 16).filedPrerequisites.push({ prerequisite: 'ROUNDS-14-L08', reason: 'folded', source: 'test' }); })), 'PROGRAM_DAG_DROPPED');
    only(run(editDag((x) => { x.dropped.pop(); })), 'PROGRAM_DAG_DROPPED');
  });

  it('fails PROGRAM_DAG_MISSING when a leaf has no node', () => {
    only(run(editDag((x) => { x.nodes = x.nodes.filter((n) => n.issue !== 176); })), 'PROGRAM_DAG_MISSING');
  });

  it('fails PROGRAM_EDGE_REASON for an edge without a reason', () => {
    only(run(editDag((x) => { nodeIn(x, 16).filedPrerequisites[0].reason = '  '; })), 'PROGRAM_EDGE_REASON');
  });

  it('fails PROGRAM_EXPORT_STALE when the export is edited by hand or the DAG names another export', () => {
    only(run(fixture((d) => editJson(d, EXPORT_PATH, (x) => { x.issues[0].prerequisites += ' '; }))), 'PROGRAM_EXPORT_STALE');
    only(run(editDag((x) => { x.source.exportSha256 = '0'.repeat(64); })), 'PROGRAM_EXPORT_STALE');
    only(run(fixture((d) => editJson(d, INPUTS_PATH, (x) => { x.description += ' Edited.'; }))), 'PROGRAM_EXPORT_STALE');
  });

  it('fails PROGRAM_DR_UNRESOLVED for a decision reference that does not resolve or is not current', () => {
    only(run(editDag((x) => { x.decision = 'DR-0003@1'; })), 'PROGRAM_DR_UNRESOLVED');
    only(run(fixture((d) => editJson(d, GATE_PATH, (x) => { x.decision = 'DR-0003@9'; }))), 'PROGRAM_DR_UNRESOLVED');
    only(run(fixture((d) => editText(d, 'docs/program/cutover-policy.md', (t) => `${t}\nSee DR-0009@1.\n`))), 'PROGRAM_DR_UNRESOLVED');
    only(run(fixture((d) => editText(d, 'docs/program/cutover-policy.md', (t) => `${t}\nSee DR-0003@2:U99.nothing.\n`))), 'PROGRAM_DR_UNRESOLVED');
  });

  it('fails PROGRAM_FILE_INVALID for a DAG off its schema, an unknown leaf-gate mode, or a missing input', () => {
    only(run(editDag((x) => { nodeIn(x, 16).phase = 12; })), 'PROGRAM_FILE_INVALID');
    only(run(fixture((d) => editJson(d, GATE_PATH, (x) => { x.mode = 'off'; }))), 'PROGRAM_FILE_INVALID');
    only(run(fixture((d) => fs.rmSync(path.join(d, EXPORT_PATH)))), 'PROGRAM_FILE_INVALID');
  });

  it('fails CONFORMANCE_DRIFT on a hand-edited DAG, and --write regenerates it', async () => {
    const dir = editDag((x) => { nodeIn(x, 16).filedPrerequisites[0].reason = 'hand edit'; });
    const opts = { root: dir, base: 'none', treeRoot: REPO_ROOT, rules: ['program'] };
    assert.deepEqual(codes((await runConformance({ ...parseArgs([]), ...opts }))[0].findings), ['CONFORMANCE_DRIFT']);
    assert.deepEqual((await runConformance({ ...parseArgs(['--write']), ...opts }))[0].written, [DAG_PATH]);
    assert.deepEqual((await runConformance({ ...parseArgs([]), ...opts }))[0].findings, []);
  });

  it('renders the DAG it builds deterministically', () => {
    const f = { exportFile: readJson(REPO_ROOT, EXPORT_PATH), inputs: readJson(REPO_ROOT, INPUTS_PATH), registry: readJson(REPO_ROOT, 'contracts/vocabulary/leaf-ids.json') };
    assert.equal(renderDag(buildDag(f).dag), renderDag(buildDag(f).dag));
    void writeJson;
  });
});
