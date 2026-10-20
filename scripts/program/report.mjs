#!/usr/bin/env node
// Prints ROUNDS-01 closure, the pending re-authorization edges, and drift in
// the program files (ROUNDS-01-L03, DR-0003 decisions P7 and P11). Read-only:
// it reads merged PR titles, closed issue states, and the integration
// branch's commit messages from GitHub with `gh`, or from a saved file, and
// writes nothing.
//
//   node scripts/program/report.mjs                      # asks gh (read-only)
//   node scripts/program/report.mjs --state state.json   # offline
//   node scripts/program/report.mjs --json
//
// state.json: { "pulls": <gh pr list --state merged --json number,title,state>,
//               "issues": <gh issue list --state closed --json number,state,stateReason>,
//               "commits": [<commit message>, ...] (optional) }
// Exits 0 with a report, 2 on bad arguments or unreadable input.
//
// TODO(ROUNDS-01-L03): from S2, read leaf stages and pending edges from
// docs/program/leaf-dag.json, so a staged leaf counts as merged once every
// stage PR merges, without the squash-message signal.

import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createContext } from '../conformance/lib/context.mjs';
import { loadLeafIds } from '../conformance/lib/leaf-ids.mjs';
import { checkProgram, computeClosure, loadProgram, pendingEdges, refResolver, stateFrom } from './lib.mjs';

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const DEFAULT_REPO = 'keyurgolani/rounds';

export function parseArgs(argv) {
  const opts = { state: null, repo: DEFAULT_REPO, branch: 'next', json: false, root: REPO_ROOT };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const value = () => {
      const v = argv[++i];
      if (v === undefined || v.startsWith('--')) throw new Error(`${a} needs a value`);
      return v;
    };
    if (a === '--state') opts.state = value();
    else if (a === '--repo') opts.repo = value();
    else if (a === '--branch') opts.branch = value();
    else if (a === '--root') opts.root = path.resolve(value());
    else if (a === '--json') opts.json = true;
    else if (a === '--help' || a === '-h') opts.help = true;
    else throw new Error(`unknown argument ${a}`);
  }
  return opts;
}

function ghJson(args) {
  return JSON.parse(execFileSync('gh', args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], maxBuffer: 64 * 1024 * 1024 }));
}

export function readState(opts) {
  if (opts.state) {
    const data = JSON.parse(fs.readFileSync(opts.state, 'utf8'));
    if (!Array.isArray(data?.pulls) || !Array.isArray(data?.issues)) throw new Error(`${opts.state} needs "pulls" and "issues" arrays`);
    if (data.commits !== undefined && !Array.isArray(data.commits)) throw new Error(`${opts.state} "commits" must be an array`);
    return data;
  }
  const pages = ghJson(['api', '--paginate', '--slurp', `repos/${opts.repo}/commits?sha=${encodeURIComponent(opts.branch)}&per_page=100`]);
  return {
    pulls: ghJson(['pr', 'list', '--repo', opts.repo, '--state', 'merged', '--limit', '2000', '--json', 'number,title,state']),
    issues: ghJson(['issue', 'list', '--repo', opts.repo, '--state', 'closed', '--limit', '2000', '--json', 'number,state,stateReason']),
    commits: pages.flat().map((c) => c?.commit?.message || ''),
  };
}

export function buildReport(root, data) {
  const ctx = createContext(root, { base: 'none' });
  const program = loadProgram(ctx, []);
  const resolve = refResolver(ctx);
  const state = stateFrom(data, loadLeafIds(ctx));
  return {
    closure: computeClosure(program, state, resolve),
    pendingEdges: pendingEdges(program, state, resolve),
    drift: checkProgram(ctx),
  };
}

const mark = (met) => (met ? 'merged' : 'open');

export function renderReport(report) {
  const { closure, pendingEdges: edges, drift } = report;
  const out = [];
  out.push(`${closure.capability} closure: ${closure.closed ? 'closed' : 'open'} (${closure.met} of ${closure.total} conditions met; closure gates no leaf)`);
  out.push(`  leaves: ${closure.leaves.map((l) => `${l.ref} ${mark(l.met)}`).join(', ')}`);
  const byGate = new Map();
  for (const a of closure.artifacts) byGate.set(a.gate, [...(byGate.get(a.gate) || []), a]);
  for (const [gate, rows] of byGate) {
    out.push(`  ${gate}: ${rows.filter((r) => r.met).length} of ${rows.length} artifacts met`);
    for (const r of rows) out.push(`    ${r.id}: ${describe(r)}`);
  }
  const c = closure.containment;
  out.push(`Containment gates (C0 to C7, not part of closure): ${c.filter((r) => r.met).length} of ${c.length} artifacts met`);
  for (const r of c) out.push(`  ${r.id}: ${describe(r)}`);
  out.push(`Pending edges: ${edges.length}, until the re-authorization receipt (docs/program/reauthorization.md)`);
  for (const e of edges) out.push(`  ${e.id} ${e.change} ${e.dependent} on ${e.prerequisite} (${e.kind}): prerequisite ${e.prerequisiteMerged ? 'merged' : 'open'}`);
  out.push(drift.length ? `Drift: ${drift.length}` : 'Drift: none');
  for (const f of drift) out.push(`  ${f.code} ${f.path}:${f.line} ${f.message}`);
  return `${out.join('\n')}\n`;
}

function describe(r) {
  if (!r.producers.length) return 'no producer';
  const open = r.producers.filter((p) => !p.met).map((p) => p.ref);
  const designation = r.designation ? ` (designation ${r.designation})` : '';
  if (r.perRow) return `${r.producers.length} per-row producers, ${r.producers.length - open.length} merged${open.length ? `; open: ${open.join(', ')}` : ''}`;
  return `${r.producers[0].ref} ${mark(r.producers[0].met)}${designation}`;
}

export function main(argv, io = { out: process.stdout, err: process.stderr }) {
  let opts;
  try {
    opts = parseArgs(argv);
  } catch (err) {
    io.err.write(`report.mjs: ${err.message}\n`);
    return 2;
  }
  if (opts.help) {
    io.out.write('usage: node scripts/program/report.mjs [--state <file>] [--repo <owner/name>] [--branch <name>] [--root <dir>] [--json]\n');
    return 0;
  }
  let data;
  try {
    data = readState(opts);
  } catch (err) {
    io.err.write(`report.mjs: cannot read PR and issue state: ${err.message}${opts.state ? '' : '; pass --state <file> to run offline'}\n`);
    return 2;
  }
  const report = buildReport(opts.root, data);
  io.out.write(opts.json ? `${JSON.stringify(report, null, 2)}\n` : renderReport(report));
  return 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = main(process.argv.slice(2));
}
