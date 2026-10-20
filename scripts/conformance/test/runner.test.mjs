import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { after, describe, it } from 'node:test';
import { parseArgs, runConformance } from '../run.mjs';
import { REPO_ROOT, cleanup, codes, editText, fixture, tempDir } from './helpers.mjs';

after(cleanup);

const allFindings = (results) => results.flatMap((r) => r.findings);

describe('runner', () => {
  it('runs every rule clean on the repository with no drift', async () => {
    const results = await runConformance({ ...parseArgs([]), root: REPO_ROOT, base: 'none' });
    assert.deepEqual(results.map((r) => r.id).sort(), ['decision-records', 'vocabulary']);
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
    const drift = await runConformance({ ...parseArgs([]), root: dir, base: 'none' });
    assert.deepEqual(codes(allFindings(drift)), ['CONFORMANCE_DRIFT']);
    fs.rmSync(path.join(dir, 'frontend/src/vocabulary/labels.ts'));
    const written = await runConformance({ ...parseArgs(['--write']), root: dir, base: 'none' });
    assert.deepEqual(written.find((r) => r.id === 'vocabulary').written.sort(), ['docs/vocabulary.md', 'frontend/src/vocabulary/labels.ts']);
    const clean = await runConformance({ ...parseArgs([]), root: dir, base: 'none' });
    assert.deepEqual(allFindings(clean), []);
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

  it('exits 1 with path:line findings and 0 when clean', () => {
    const script = path.join(REPO_ROOT, 'scripts/conformance/run.mjs');
    const ok = execFileSync(process.execPath, [script, '--base', 'none'], { cwd: REPO_ROOT, encoding: 'utf8', env: { ...process.env, GITHUB_ACTIONS: '' } });
    assert.match(ok, /conformance: 2 rule\(s\), 0 finding\(s\)/);
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
