#!/usr/bin/env node
// Repository conformance runner (ROUNDS-01-L01). Node 22 built-ins only; no
// install step.
//
//   node scripts/conformance/run.mjs [--write] [--rule <id>] [--base <ref>|none] [--catalog <path>] [--root <dir>]
//
// Loads every scripts/conformance/rules/*.mjs. A rule exports:
//   id, owningLeaf, check(repoRoot) -> [{ code, path, line, message }]
//   and optionally generate(repoRoot) -> [{ path, content }] and summary(repoRoot) -> [string]
// (each also takes the shared context as a second argument). Without --write the
// runner regenerates in memory and fails on drift; --write writes the files.
// --base is the ref revision checks compare with (default origin/main);
// --catalog verifies the leaf-ID pin against rounds-review's capabilities.json.
// Exits 1 when any rule reports a finding.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createContext, finding } from './lib/context.mjs';
import { leafResolver, loadLeafIds } from './lib/leaf-ids.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, '..', '..');
const RULES_DIR = path.join(HERE, 'rules');

export function parseArgs(argv) {
  const opts = { write: false, rules: [], base: undefined, catalog: undefined, root: REPO_ROOT };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--write') opts.write = true;
    else if (a === '--rule') opts.rules.push(argv[++i]);
    else if (a === '--base') opts.base = argv[++i];
    else if (a === '--catalog') opts.catalog = argv[++i];
    else if (a === '--root') opts.root = path.resolve(argv[++i]);
    else if (a === '--help' || a === '-h') opts.help = true;
    else throw new Error(`unknown argument ${a}`);
  }
  return opts;
}

export async function loadRules(dir = RULES_DIR) {
  const files = fs.readdirSync(dir).filter((f) => f.endsWith('.mjs')).sort();
  const rules = [];
  for (const f of files) rules.push({ file: path.join('scripts/conformance/rules', f), mod: await import(pathToFileURL(path.join(dir, f)).href) });
  return rules;
}

export async function runConformance(opts) {
  const ctx = createContext(opts.root, {
    base: opts.base === undefined ? process.env.CONFORMANCE_BASE || 'origin/main' : opts.base,
    catalogPath: opts.catalog || process.env.ROUNDS_REVIEW_CATALOG || null,
  });
  const resolveLeaf = leafResolver(loadLeafIds(ctx));
  const results = [];
  const all = await loadRules(opts.rulesDir);
  const unknown = opts.rules.filter((id) => !all.some(({ mod }) => mod.id === id));
  if (unknown.length) {
    throw new Error(`unknown rule ${unknown.join(', ')}; rules are ${all.map(({ mod }) => mod.id).join(', ')}`);
  }
  for (const { file, mod } of all) {
    if (opts.rules.length && !opts.rules.includes(mod.id)) continue;
    const findings = [];
    const written = [];
    const summary = [];
    if (typeof mod.id !== 'string' || typeof mod.owningLeaf !== 'string' || typeof mod.check !== 'function') {
      findings.push(finding('CONFORMANCE_RULE_INVALID', file, 1, 'a rule exports id, owningLeaf, and check(repoRoot)'));
      results.push({ id: mod.id || file, owningLeaf: mod.owningLeaf || '?', findings, written, summary });
      continue;
    }
    const owner = resolveLeaf(mod.owningLeaf);
    if (!owner.ok) findings.push(finding('CONFORMANCE_RULE_INVALID', file, 1, `owningLeaf ${mod.owningLeaf}: ${owner.reason}`));
    try {
      findings.push(...(await mod.check(opts.root, ctx)));
      if (typeof mod.generate === 'function') {
        for (const out of await mod.generate(opts.root, ctx)) {
          const abs = path.join(opts.root, out.path);
          const current = fs.existsSync(abs) ? fs.readFileSync(abs, 'utf8') : null;
          if (current === out.content) continue;
          if (opts.write) {
            fs.mkdirSync(path.dirname(abs), { recursive: true });
            fs.writeFileSync(abs, out.content);
            written.push(out.path);
          } else {
            findings.push(finding('CONFORMANCE_DRIFT', out.path, 1, `${current === null ? 'missing' : 'out of date'}; run node scripts/conformance/run.mjs --write and commit the result`));
          }
        }
      }
      if (typeof mod.summary === 'function') summary.push(...(await mod.summary(opts.root, ctx)));
    } catch (err) {
      findings.push(finding('CONFORMANCE_RULE_INVALID', file, 1, `rule threw: ${err.stack || err.message}`));
    }
    results.push({ id: mod.id, owningLeaf: mod.owningLeaf, findings, written, summary });
  }
  return results;
}

function report(results, { annotate }) {
  let total = 0;
  for (const r of results) {
    console.log(`\n${r.id} (${r.owningLeaf}): ${r.findings.length ? `${r.findings.length} finding(s)` : 'ok'}`);
    for (const line of r.summary) console.log(`  ${line}`);
    for (const p of r.written) console.log(`  wrote ${p}`);
    for (const f of r.findings) {
      console.log(`  ${f.path}:${f.line} ${f.code} ${f.message}`);
      if (annotate) {
        const msg = `${f.code} ${f.message}`.replace(/%/g, '%25').replace(/\r/g, '%0D').replace(/\n/g, '%0A');
        console.log(`::error file=${f.path},line=${f.line},title=${f.code}::${msg}`);
      }
    }
    total += r.findings.length;
  }
  console.log(`\nconformance: ${results.length} rule(s), ${total} finding(s)`);
  return total;
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  let opts;
  try {
    opts = parseArgs(process.argv.slice(2));
  } catch (err) {
    console.error(err.message);
    process.exit(2);
  }
  if (opts.help) {
    console.log('usage: node scripts/conformance/run.mjs [--write] [--rule <id>] [--base <ref>|none] [--catalog <capabilities.json>] [--root <dir>]');
    process.exit(0);
  }
  let results;
  try {
    results = await runConformance(opts);
  } catch (err) {
    console.error(err.message);
    process.exit(2);
  }
  const total = report(results, { annotate: process.env.GITHUB_ACTIONS === 'true' });
  process.exit(total ? 1 : 0);
}
