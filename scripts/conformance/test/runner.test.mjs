import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { after, describe, it } from 'node:test';
import { parseArgs, runConformance } from '../run.mjs';
import { REPO_ROOT, cleanup, codes, editJson, editText, fixture, tempDir } from './helpers.mjs';

after(cleanup);

const allFindings = (results) => results.flatMap((r) => r.findings);

describe('runner', () => {
  it('runs every rule clean on the repository with no drift', async () => {
    const results = await runConformance({ ...parseArgs([]), root: REPO_ROOT, base: 'none' });
    assert.deepEqual(results.map((r) => r.id).sort(), ['authority', 'decision-records', 'vocabulary']);
    assert.deepEqual(allFindings(results), []);
    for (const r of results) assert.deepEqual(r.written, []);
  });

  it('prints the registry revision, counts, and open ratified-here items', async () => {
    const results = await runConformance({ ...parseArgs([]), root: REPO_ROOT, base: 'none' });
    const summary = results.find((r) => r.id === 'vocabulary').summary.join('\n');
    assert.match(summary, /registry revision 1 \(vocabulary@1 = DR-0001@1\)/);
    assert.match(summary, /terms: \d+ /);
    assert.match(summary, /adapters: \d+ /);
    assert.match(summary, /open ratified-here items: decisions G6, G7, G8, G9/);
    assert.match(summary, /40 live, 3 historical/);
  });

  it('fails on drift in a generated file and --write repairs it', async () => {
    const dir = fixture((d) => editText(d, 'docs/vocabulary.md', (s) => `${s}\nhand edit\n`));
    const drift = await runConformance({ ...parseArgs([]), root: dir, base: 'none', treeRoot: REPO_ROOT });
    assert.deepEqual(codes(allFindings(drift)), ['CONFORMANCE_DRIFT']);
    fs.rmSync(path.join(dir, 'frontend/src/vocabulary/labels.ts'));
    const written = await runConformance({ ...parseArgs(['--write']), root: dir, base: 'none', treeRoot: REPO_ROOT });
    assert.deepEqual(written.find((r) => r.id === 'vocabulary').written.sort(), ['docs/vocabulary.md', 'frontend/src/vocabulary/labels.ts']);
    const clean = await runConformance({ ...parseArgs([]), root: dir, base: 'none', treeRoot: REPO_ROOT });
    assert.deepEqual(allFindings(clean), []);
  });

  it('regenerates docs/authority.md and baseline-stores.json, keeping each store\'s rows and note', async () => {
    const STORES = 'contracts/authority/baseline-stores.json';
    let key = -1;
    const dir = fixture((d) => {
      editText(d, 'docs/authority.md', (s) => `${s}\nhand edit\n`);
      editJson(d, STORES, (b) => {
        key = b.stores.findIndex((s) => s.kind === 'browser-key' && s.writes.length);
        b.stores[key].writes = [];
        b.stores[0].note = 'Kept across regeneration.';
      });
    });
    const opts = { root: dir, base: 'none', treeRoot: REPO_ROOT, rules: ['authority'] };
    const drift = await runConformance({ ...parseArgs([]), ...opts });
    assert.deepEqual(drift[0].findings.map((f) => `${f.code} ${f.path}`).sort(), [`CONFORMANCE_DRIFT ${STORES}`, 'CONFORMANCE_DRIFT docs/authority.md']);
    const written = await runConformance({ ...parseArgs(['--write']), ...opts });
    assert.deepEqual(written[0].written.sort(), [STORES, 'docs/authority.md']);
    const after = JSON.parse(fs.readFileSync(path.join(dir, STORES), 'utf8'));
    const repo = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, STORES), 'utf8'));
    assert.deepEqual(after.stores[key].writes, repo.stores[key].writes);
    assert.equal(after.stores[0].note, 'Kept across regeneration.');
    assert.deepEqual(after.stores.map((s) => s.rows), repo.stores.map((s) => s.rows));
    assert.deepEqual(allFindings(await runConformance({ ...parseArgs([]), ...opts })), []);
  });

  it('prints the matrix revision, blocked rows with their decisions, and pending counts by leaf', async () => {
    const results = await runConformance({ ...parseArgs(['--rule', 'authority']), root: REPO_ROOT, base: 'none' });
    const summary = results[0].summary.join('\n');
    assert.match(summary, /matrix revision 1 \(DR-0002@1 /);
    assert.match(summary, /blocked rows: 6 \(OD-1: ai-provider-credential, .*; OD-5: login-streak\)/);
    assert.match(summary, /pending cells by leaf \(\d+ cells, \d+ leaves\): ROUNDS-02-L01 84, /);
    assert.match(summary, /40 collections and 82 browser key families at 62d4eae/);
    assert.equal(parseArgs(['--review', 'some/dir']).review, path.resolve('some/dir'));
  });

  it('rejects a rule that breaks the interface or names an unknown owning leaf', async () => {
    const rulesDir = tempDir();
    fs.writeFileSync(path.join(rulesDir, 'a-bad.mjs'), "export const id = 'bad';\n");
    fs.writeFileSync(path.join(rulesDir, 'b-unowned.mjs'), "export const id = 'unowned';\nexport const owningLeaf = 'ROUNDS-99-L01';\nexport function check() { return []; }\n");
    fs.writeFileSync(path.join(rulesDir, 'c-ok.mjs'), "export const id = 'ok';\nexport const owningLeaf = 'ROUNDS-01-L01';\nexport function check() { return [{ code: 'X_FOUND', path: 'README.md', line: 2, message: 'example finding' }]; }\n");
    const results = await runConformance({ ...parseArgs([]), root: REPO_ROOT, base: 'none', rulesDir });
    const byId = Object.fromEntries(results.map((r) => [r.id, codes(r.findings)]));
    assert.deepEqual(byId, { bad: ['CONFORMANCE_RULE_INVALID'], unowned: ['CONFORMANCE_RULE_INVALID'], ok: ['X_FOUND'] });
  });

  it('rejects an unknown --rule instead of skipping it', async () => {
    await assert.rejects(runConformance({ ...parseArgs(['--rule', 'vocabulary', '--rule', 'no-such-rule']), root: REPO_ROOT, base: 'none' }), /unknown rule no-such-rule/);
    const script = path.join(REPO_ROOT, 'scripts/conformance/run.mjs');
    let failed = null;
    try {
      execFileSync(process.execPath, [script, '--base', 'none', '--rule', 'vocabulry'], { cwd: REPO_ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
    } catch (err) {
      failed = err;
    }
    assert.ok(failed, 'the run fails');
    assert.equal(failed.status, 2);
    assert.match(failed.stderr, /unknown rule vocabulry; rules are authority, decision-records, vocabulary/);
  });

  it('compares with the branch a pull request targets, and runs on pushes to next', () => {
    const ci = fs.readFileSync(path.join(REPO_ROOT, '.github/workflows/ci.yml'), 'utf8');
    const job = ci.slice(ci.indexOf('\n  conformance:'), ci.indexOf('\n  harness:'));
    assert.match(job, /BASE_REF: \$\{\{ github\.base_ref \|\| 'main' \}\}/);
    assert.match(job, /run\.mjs --base "origin\/\$\{BASE_REF\}"/);
    assert.match(job, /git fetch --no-tags origin "\+refs\/heads\/\$\{BASE_REF\}:refs\/remotes\/origin\/\$\{BASE_REF\}"/);
    assert.doesNotMatch(job, /--base origin\/main/);
    assert.match(job, /fetch-depth: 0/);
    assert.match(ci, /push:\n(?:\s+#.*\n)?\s+branches: \[main, next\]/);
  });

  it('exits 1 with path:line findings and 0 when clean', () => {
    const script = path.join(REPO_ROOT, 'scripts/conformance/run.mjs');
    const ok = execFileSync(process.execPath, [script, '--base', 'none'], { cwd: REPO_ROOT, encoding: 'utf8', env: { ...process.env, GITHUB_ACTIONS: '' } });
    assert.match(ok, /conformance: 3 rule\(s\), 0 finding\(s\)/);
    const dir = fixture((d) => editText(d, 'README.md', (s) => s.replace(/^Rounds is a self-hostable career command center.*$/m, 'Rounds is a tool.')));
    let failed = null;
    try {
      execFileSync(process.execPath, [script, '--base', 'none', '--root', dir, '--rule', 'vocabulary'], { encoding: 'utf8', env: { ...process.env, GITHUB_ACTIONS: 'true' } });
    } catch (err) {
      failed = err;
    }
    assert.ok(failed, 'the run fails');
    assert.equal(failed.status, 1);
    assert.match(failed.stdout, /README\.md:3 VOCAB_POSITIONING_STALE/);
    assert.match(failed.stdout, /::error file=README\.md,line=3,title=VOCAB_POSITIONING_STALE::/);
  });
});
