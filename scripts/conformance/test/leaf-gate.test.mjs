// Tests for the leaf prerequisite check (ROUNDS-01-L03 S2, DR-0003
// decision P12): scripts/program/leaf-gate.mjs against fixture titles and
// base histories, its CLI in a throwaway git repository, and the ci.yml
// step that runs it read-only in the conformance job.

import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { after, describe, it } from 'node:test';
import { evaluate, main, prerequisiteMet, render } from '../../program/leaf-gate.mjs';
import { REPO_ROOT, cleanup, tempDir, writeJson } from './helpers.mjs';

after(cleanup);

// A synthetic DAG: #15 and #16 unstaged, #17 staged with satisfiedBy S2,
// #1 staged with a complete list, #18 on all of them, #170 with stage edges.
const DAG = {
  nodes: [
    { id: 'ROUNDS-00A-L01', issue: 1, status: 'filed', stages: ['S0', 'S1'], stagesComplete: true, filedPrerequisites: [] },
    { id: 'ROUNDS-01-L01', issue: 15, status: 'filed', filedPrerequisites: [] },
    { id: 'ROUNDS-01-L02', issue: 16, status: 'filed', filedPrerequisites: [{ prerequisite: 'ROUNDS-01-L01', reason: 'record format', source: 'test' }] },
    { id: 'ROUNDS-01-L03', issue: 17, status: 'filed', stages: ['S1', 'S2', 'S3', 'S4'], stagesComplete: true, satisfiedBy: ['S2'], filedPrerequisites: [{ prerequisite: 'ROUNDS-01-L01', reason: 'record format', source: 'test' }] },
    { id: 'ROUNDS-02-L01', issue: 18, status: 'filed', filedPrerequisites: [
      { prerequisite: 'ROUNDS-01-L02', reason: 'authority rows', source: 'test' },
      { prerequisite: 'ROUNDS-01-L03', reason: 'the program', source: 'test' },
      { prerequisite: 'ROUNDS-00A-L01', reason: 'admission', source: 'test' },
    ] },
    { id: 'ROUNDS-34-L01', issue: 170, status: 'filed', stages: ['S1', 'S2'], stagesComplete: true, filedPrerequisites: [
      { prerequisite: 'ROUNDS-01-L01', forStages: ['S1'], reason: 'conformance runner', source: 'test' },
      { prerequisite: 'ROUNDS-00A-L01/S1', forStages: ['S2'], reason: 'gate registry', source: 'test' },
    ] },
  ],
  dropped: [{ id: 'ROUNDS-00A-L09', foldedInto: 'ROUNDS-00A-L01' }],
};
const REGISTRY = { leaves: DAG.nodes.map((n) => ({ id: n.id, issue: n.issue, status: n.status })) };
const squash = (subject, body = '') => `${subject}${body ? `\n\n${body}` : ''}`;
const gate = (title, messages) => evaluate({ title, dag: DAG, messages, registry: REGISTRY });
const missingOf = (r) => r.missing.map((m) => m.prerequisite);

describe('leaf gate: verdicts', () => {
  it('passes when every prerequisite is merged into the base', () => {
    const r = gate('docs(x): did a thing [ROUNDS-01-L02]', [squash('docs(vocabulary): ratified it [ROUNDS-01-L01] (#188)')]);
    assert.equal(r.verdict, 'pass');
    assert.equal(r.code, 'LEAF_GATE_PASS');
  });

  it('reports LEAF_GATE_BLOCKED with the missing prerequisites', () => {
    const r = gate('feat(db): ADR [ROUNDS-02-L01]', [squash('docs: vocabulary [ROUNDS-01-L01] (#1)')]);
    assert.equal(r.code, 'LEAF_GATE_BLOCKED');
    assert.deepEqual(missingOf(r), ['ROUNDS-01-L02', 'ROUNDS-01-L03', 'ROUNDS-00A-L01']);
    assert.ok(r.missing.every((m) => m.reason));
  });

  it('counts a whole leaf once its satisfiedBy stages, every listed stage, its [LEAF-ID] PR, or Closes #N merged', () => {
    const base = [
      squash('docs: matrix [ROUNDS-01-L02] (#2)'),
      squash('docs: program [ROUNDS-01-L03/S2] (#3)'),
      squash('fix: route auth [ROUNDS-00A-L01/S0] (#4)'),
      squash('fix: route auth [ROUNDS-00A-L01/S1] (#5)'),
    ];
    assert.equal(gate('feat: ADR [ROUNDS-02-L01]', base).verdict, 'pass');
    assert.deepEqual(missingOf(gate('feat: ADR [ROUNDS-02-L01]', base.slice(0, 3))), ['ROUNDS-00A-L01']);
    const closes = [base[0], base[1], squash('fix: last stage of the leaf (#6)', 'Closes #1')];
    assert.equal(gate('feat: ADR [ROUNDS-02-L01]', closes).verdict, 'pass');
    const whole = [base[0], base[1], squash('fix: everything [ROUNDS-00A-L01] (#7)')];
    assert.equal(gate('feat: ADR [ROUNDS-02-L01]', whole).verdict, 'pass');
  });

  it('a stage prerequisite needs that stage, and a stage PR only its own stage edges', () => {
    const nodes = new Map(DAG.nodes.map((n) => [n.id, n]));
    const state = (subjects) => ({ merged: new Set(subjects), complete: new Set(), done: new Set() });
    assert.equal(prerequisiteMet('ROUNDS-00A-L01/S1', nodes, state(['ROUNDS-00A-L01/S0'])), false);
    assert.equal(prerequisiteMet('ROUNDS-00A-L01/S1', nodes, state(['ROUNDS-00A-L01/S1'])), true);
    const s1 = gate('test: harness [ROUNDS-34-L01/S1]', []);
    assert.deepEqual(missingOf(s1), ['ROUNDS-01-L01']);
    const s2 = gate('test: harness [ROUNDS-34-L01/S2]', [squash('x [ROUNDS-00A-L01/S1] (#9)')]);
    assert.equal(s2.verdict, 'pass');
  });

  it('a prerequisite on a branch other than the base does not count', () => {
    // Only the base's messages are read; a merge elsewhere never reaches them.
    assert.deepEqual(missingOf(gate('docs: matrix [ROUNDS-01-L02]', [])), ['ROUNDS-01-L01']);
  });

  it('fails closed on a missing, empty, or malformed title, an unreadable DAG, or an unreadable history', () => {
    for (const title of [undefined, '', '   ']) assert.equal(gate(title, []).code, 'LEAF_GATE_UNREADABLE');
    assert.equal(gate('feat: x [ROUNDS-01-L3]', []).code, 'LEAF_GATE_UNREADABLE');
    assert.equal(evaluate({ title: 'x [ROUNDS-01-L02]', dag: null, messages: [], registry: REGISTRY }).code, 'LEAF_GATE_UNREADABLE');
    assert.equal(evaluate({ title: 'x [ROUNDS-01-L02]', dag: DAG, messages: null, registry: REGISTRY }).code, 'LEAF_GATE_UNREADABLE');
    for (const r of [gate('', []), gate('x [ROUNDS-01-L3]', [])]) assert.equal(r.verdict, 'blocked');
  });

  it('blocks an unlabeled title, an unknown or folded leaf, and a stage the DAG does not list', () => {
    assert.equal(gate('chore: bump a dependency', []).code, 'LEAF_GATE_UNLABELED');
    assert.equal(gate('x [ROUNDS-99-L99]', []).code, 'LEAF_GATE_UNKNOWN');
    const folded = gate('x [ROUNDS-00A-L09]', []);
    assert.equal(folded.code, 'LEAF_GATE_UNKNOWN');
    assert.match(folded.message, /folded into ROUNDS-00A-L01/);
    assert.equal(gate('x [ROUNDS-01-L03/S9]', []).code, 'LEAF_GATE_UNKNOWN');
    assert.equal(gate('x [ROUNDS-01-L02/S1]', []).code, 'LEAF_GATE_UNKNOWN');
    for (const t of ['chore: bump a dependency', 'x [ROUNDS-99-L99]']) assert.equal(gate(t, []).verdict, 'blocked');
  });

  it('reads the last label in the title, as the squash subject carries it', () => {
    assert.equal(gate('fix: follow-up to [ROUNDS-01-L01] [ROUNDS-01-L02]', [squash('x [ROUNDS-01-L01] (#1)')]).label, 'ROUNDS-01-L02');
  });

  it('renders a report-mode warning and an enforce-mode error, escaping line breaks', () => {
    const r = { ...gate('x [ROUNDS-02-L01]', []) };
    r.missing = [{ prerequisite: 'ROUNDS-01-L02', reason: 'line one\nline two' }];
    assert.match(render(r, 'report', { annotate: true }), /^::warning title=LEAF_GATE_BLOCKED::/m);
    assert.match(render(r, 'enforce', { annotate: true }), /^::error title=LEAF_GATE_BLOCKED::/m);
    assert.doesNotMatch(render(r, 'report', { annotate: true }).split('\n').filter((l) => l.startsWith('::')).join('\n'), /line two/);
  });
});

describe('leaf gate: CLI', () => {
  const git = (dir, ...args) => execFileSync('git', ['-C', dir, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', '-c', 'commit.gpgsign=false', ...args], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  const repo = (mode, subjects) => {
    const dir = tempDir('rounds-leaf-gate-');
    writeJson(dir, 'docs/program/leaf-dag.json', DAG);
    writeJson(dir, 'docs/program/leaf-gate.json', { description: 'test', mode, decision: 'DR-0003@2' });
    git(dir, 'init', '-q', '-b', 'next');
    git(dir, 'add', '-A');
    git(dir, 'commit', '-q', '-m', 'init');
    for (const s of subjects) git(dir, 'commit', '-q', '--allow-empty', '-m', s);
    return dir;
  };
  const cli = (dir, env, args = ['--base', 'next']) => {
    let out = '';
    let err = '';
    const code = main([...args, '--root', dir], { env, out: { write: (s) => { out += s; } }, err: { write: (s) => { err += s; } } });
    return { code, out, err };
  };

  it('report mode prints LEAF_GATE_BLOCKED and exits 0; enforce mode exits 1; a pass exits 0 in both', () => {
    const report = repo('report', ['docs: vocabulary [ROUNDS-01-L01] (#1)']);
    const r = cli(report, { PR_TITLE: 'feat: ADR [ROUNDS-02-L01]' });
    assert.equal(r.code, 0);
    assert.match(r.out, /LEAF_GATE_BLOCKED ROUNDS-02-L01/);
    assert.match(r.out, /missing ROUNDS-01-L02: authority rows/);
    const enforce = repo('enforce', ['docs: vocabulary [ROUNDS-01-L01] (#1)']);
    assert.equal(cli(enforce, { PR_TITLE: 'feat: ADR [ROUNDS-02-L01]' }).code, 1);
    assert.equal(cli(enforce, { PR_TITLE: 'docs: matrix [ROUNDS-01-L02]' }).code, 0);
  });

  it('reads the title only from the environment and never prints it', () => {
    const dir = repo('enforce', []);
    const marker = 'x\n::error::injected [ROUNDS-01-L01]';
    const r = cli(dir, { PR_TITLE: marker, GITHUB_ACTIONS: 'true' });
    assert.equal(r.code, 0);
    assert.doesNotMatch(r.out, /injected/);
    const missing = cli(dir, {});
    assert.equal(missing.code, 1);
    assert.match(missing.out, /LEAF_GATE_UNREADABLE/);
    assert.equal(cli(dir, { OTHER: 'x [ROUNDS-01-L01]' }, ['--base', 'next', '--title-env', 'OTHER']).code, 0);
    assert.equal(cli(dir, {}, ['--base', 'next', '--title-env', 'BAD NAME']).code, 2);
  });

  it('fails closed on an unknown base, a missing DAG, and a missing or invalid mode file', () => {
    const dir = repo('enforce', []);
    const r = cli(dir, { PR_TITLE: 'x [ROUNDS-01-L01]' }, ['--base', 'origin/no-such-branch']);
    assert.equal(r.code, 1);
    assert.match(r.out, /LEAF_GATE_UNREADABLE/);
    fs.rmSync(path.join(dir, 'docs/program/leaf-dag.json'));
    assert.match(cli(dir, { PR_TITLE: 'x [ROUNDS-01-L01]' }).out, /LEAF_GATE_UNREADABLE/);
    writeJson(dir, 'docs/program/leaf-gate.json', { mode: 'off' });
    assert.equal(cli(dir, { PR_TITLE: 'x [ROUNDS-01-L01]' }).code, 1);
    fs.rmSync(path.join(dir, 'docs/program/leaf-gate.json'));
    assert.equal(cli(dir, { PR_TITLE: 'x [ROUNDS-01-L01]' }).code, 1);
    assert.equal(cli(dir, {}, []).code, 2);
  });

  it('runs against the committed DAG and mode: report, so it passes', () => {
    const r = cli(REPO_ROOT, { PR_TITLE: 'feat: x [ROUNDS-02-L02]' }, ['--base', 'HEAD']);
    assert.equal(r.code, 0);
    assert.match(r.out, /\(report mode\)/);
  });
});

describe('leaf gate: CI wiring', () => {
  const ci = fs.readFileSync(path.join(REPO_ROOT, '.github/workflows/ci.yml'), 'utf8');
  const job = ci.slice(ci.indexOf('\n  conformance:'), ci.indexOf('\n  harness:'));

  it('runs in the read-only conformance job on pull requests, with the title passed through env', () => {
    assert.match(job, /permissions:\n\s+contents: read/);
    const step = job.slice(job.indexOf('- name: Leaf prerequisites'));
    assert.match(step, /if: \$\{\{ !cancelled\(\) && github\.event_name == 'pull_request' \}\}/);
    assert.match(step, /PR_TITLE: \$\{\{ github\.event\.pull_request\.title \}\}/);
    const run = step.slice(step.indexOf('run:'));
    assert.doesNotMatch(run, /\$\{\{/, 'the run script interpolates no expression');
    assert.match(run, /node scripts\/program\/leaf-gate\.mjs --base "origin\/\$\{BASE_REF\}"/);
  });

  it('adds no privileged trigger or permission anywhere in ci.yml', () => {
    assert.doesNotMatch(ci, /pull_request_target|workflow_dispatch|statuses:\s*write/);
  });
});
