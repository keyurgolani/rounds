#!/usr/bin/env node
// The leaf prerequisite check (ROUNDS-01-L03 S2, DR-0003 decision P12). On a
// pull request it reads the title's [LEAF-ID] or [LEAF-ID/<stage>] label,
// that leaf's prerequisites in docs/program/leaf-dag.json, and the commit
// messages on the base branch, and reports LEAF_GATE_BLOCKED for every
// prerequisite that hasn't merged there. A prerequisite counts once it is
// merged into the base. Read-only: it runs git log and reads the checkout.
//
//   PR_TITLE="..." node scripts/program/leaf-gate.mjs --base origin/next
//
// The title comes from an environment variable (PR_TITLE, or --title-env),
// never from the command line, and is never printed: it is the PR author's
// text. docs/program/leaf-gate.json sets the mode: report prints the
// verdict and exits 0; enforce exits 1 on any blocked verdict. Fail closed:
// a missing or unlabeled title, an unknown leaf or stage, an unreadable DAG,
// or an unreadable base history is a blocked verdict, never a pass, and an
// unreadable mode file exits 1. Exits 2 on bad arguments.

import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { DAG_PATH, GATE_PATH } from './dag.mjs';
import { stateFrom, titleLabel } from './lib.mjs';

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
export const MODES = ['report', 'enforce'];

export function parseArgs(argv) {
  const opts = { base: null, titleEnv: 'PR_TITLE', root: REPO_ROOT, json: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const value = () => {
      const v = argv[++i];
      if (v === undefined || v.startsWith('--')) throw new Error(`${a} needs a value`);
      return v;
    };
    if (a === '--base') opts.base = value();
    else if (a === '--title-env') opts.titleEnv = value();
    else if (a === '--root') opts.root = path.resolve(value());
    else if (a === '--json') opts.json = true;
    else if (a === '--help' || a === '-h') opts.help = true;
    else throw new Error(`unknown argument ${a}`);
  }
  if (!opts.help && !opts.base) throw new Error('--base <ref> is required');
  if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(opts.titleEnv)) throw new Error('--title-env takes an environment variable name');
  return opts;
}

// Every commit message reachable from base, newest first.
export function baseMessages(root, base) {
  const out = execFileSync('git', ['-C', root, 'log', '--format=%B%x1e', base, '--'], {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
    maxBuffer: 256 * 1024 * 1024,
  });
  return out.split('\x1e').map((m) => m.replace(/^\n+/, '').trimEnd()).filter(Boolean);
}

// What the base branch carries: { merged: Set<ref>, complete: Set<leaf> }.
// A squash subject's [LEAF-ID] or [LEAF-ID/<stage>] label is that leaf or
// stage merged; "Closes #N" in a message marks leaf #N's finishing PR.
export function baseState(messages, registry) {
  const pulls = messages.map((m) => ({ title: m.split('\n')[0], state: 'MERGED' }));
  return stateFrom({ pulls, issues: [], commits: messages }, registry);
}

// Whether a prerequisite ref is merged into the base. A stage needs its own
// PR; a whole leaf needs its [LEAF-ID] PR, its finishing PR, or every stage
// its satisfiedBy names, or, when its stage list is complete, every stage.
export function prerequisiteMet(ref, nodes, state) {
  const [id, stage] = String(ref).split('/');
  if (state.merged.has(id) || state.complete.has(id) || state.done?.has(id)) return true;
  if (stage) return state.merged.has(ref);
  const n = nodes.get(id);
  if (n?.satisfiedBy?.length) return n.satisfiedBy.every((s) => state.merged.has(`${id}/${s}`));
  if (n?.stages?.length && n.stagesComplete) return n.stages.every((s) => state.merged.has(`${id}/${s}`));
  return false;
}

const blocked = (code, message, extra = {}) => ({ verdict: 'blocked', code, message, missing: [], ...extra });

// The verdict for a title against a DAG and the base's messages. dag or
// messages null means it could not be read.
export function evaluate({ title, dag, messages, registry }) {
  if (typeof title !== 'string' || !title.trim()) return blocked('LEAF_GATE_UNREADABLE', 'the pull request title is missing or empty');
  const label = titleLabel(title);
  if (!label) {
    if (/\[ROUNDS-/i.test(title)) return blocked('LEAF_GATE_UNREADABLE', 'the title has a malformed leaf label; use [ROUNDS-XX-LYY] or [ROUNDS-XX-LYY/<stage>]');
    return blocked('LEAF_GATE_UNLABELED', 'the title carries no [ROUNDS-XX-LYY] or [ROUNDS-XX-LYY/<stage>] label');
  }
  if (!dag || !Array.isArray(dag.nodes)) return blocked('LEAF_GATE_UNREADABLE', `${DAG_PATH} is missing or unreadable`, { label: label.ref });
  if (!Array.isArray(messages)) return blocked('LEAF_GATE_UNREADABLE', 'the base branch history is unreadable; fetch it in full (actions/checkout fetch-depth: 0)', { label: label.ref });
  const nodes = new Map(dag.nodes.map((n) => [n.id, n]));
  const node = nodes.get(label.leaf);
  if (!node) {
    const folded = (dag.dropped || []).find((d) => d.id === label.leaf);
    return blocked('LEAF_GATE_UNKNOWN', folded ? `${label.leaf} was folded into ${folded.foldedInto}; label the PR with that leaf` : `${label.leaf} is not a leaf in ${DAG_PATH}`, { label: label.ref });
  }
  if (label.stage && !(node.stages || []).includes(label.stage)) {
    return blocked('LEAF_GATE_UNKNOWN', node.stages?.length ? `${label.leaf} has no stage ${label.stage}; its stages are ${node.stages.join(', ')}` : `${label.leaf} has no stages in ${DAG_PATH}; label the PR [${label.leaf}]`, { label: label.ref });
  }
  const state = baseState(messages, registry);
  const edges = (node.filedPrerequisites || []).filter((e) => !label.stage || !e.forStages || e.forStages.includes(label.stage));
  const missing = [];
  const met = [];
  for (const e of edges) (prerequisiteMet(e.prerequisite, nodes, state) ? met : missing).push({ prerequisite: e.prerequisite, reason: e.reason });
  if (missing.length) {
    return { verdict: 'blocked', code: 'LEAF_GATE_BLOCKED', label: label.ref, message: `waits on ${missing.length} of ${edges.length} prerequisites`, missing, met };
  }
  return { verdict: 'pass', code: 'LEAF_GATE_PASS', label: label.ref, message: `all ${edges.length} prerequisites are merged into the base`, missing, met };
}

// Workflow-command text: no line breaks or percent signs pass through.
const escapeCommand = (s) => String(s).replace(/%/g, '%25').replace(/\r/g, '%0D').replace(/\n/g, '%0A');

export function render(result, mode, { annotate = false } = {}) {
  const out = [];
  const head = `${result.code}${result.label ? ` ${result.label}` : ''}: ${result.message}`;
  out.push(`leaf-gate (${mode} mode): ${head}`);
  for (const m of result.missing) out.push(`  missing ${m.prerequisite}: ${m.reason}`);
  if (result.verdict === 'blocked') out.push(mode === 'enforce' ? 'leaf-gate: blocked; this check fails in enforce mode' : 'leaf-gate: blocked; report mode passes (S4 sets enforce)');
  if (annotate && result.verdict === 'blocked') {
    const detail = result.missing.length ? `${head}; missing ${result.missing.map((m) => m.prerequisite).join(', ')}` : head;
    out.push(`::${mode === 'enforce' ? 'error' : 'warning'} title=${result.code}::${escapeCommand(detail)}`);
  }
  return `${out.join('\n')}\n`;
}

export function readMode(root) {
  const gate = JSON.parse(fs.readFileSync(path.join(root, GATE_PATH), 'utf8'));
  if (!MODES.includes(gate?.mode)) throw new Error(`${GATE_PATH} mode must be ${MODES.join(' or ')}`);
  return gate.mode;
}

export function main(argv, { env = process.env, out = process.stdout, err = process.stderr } = {}) {
  let opts;
  try {
    opts = parseArgs(argv);
  } catch (e) {
    err.write(`leaf-gate.mjs: ${e.message}\n`);
    return 2;
  }
  if (opts.help) {
    out.write('usage: PR_TITLE=... node scripts/program/leaf-gate.mjs --base <ref> [--title-env <NAME>] [--root <dir>] [--json]\n');
    return 0;
  }
  let mode;
  try {
    mode = readMode(opts.root);
  } catch (e) {
    err.write(`leaf-gate.mjs: cannot read the mode from ${GATE_PATH}: ${e.message}\n`);
    return 1;
  }
  let dag = null;
  let registry = null;
  try {
    dag = JSON.parse(fs.readFileSync(path.join(opts.root, DAG_PATH), 'utf8'));
    registry = { leaves: dag.nodes.map((n) => ({ id: n.id, issue: n.issue, status: n.status })) };
  } catch {
    dag = null;
  }
  let messages = null;
  try {
    messages = baseMessages(opts.root, opts.base);
  } catch {
    messages = null;
  }
  const result = evaluate({ title: env[opts.titleEnv], dag, messages, registry });
  out.write(opts.json ? `${JSON.stringify({ mode, ...result }, null, 2)}\n` : render(result, mode, { annotate: env.GITHUB_ACTIONS === 'true' }));
  return result.verdict === 'blocked' && mode === 'enforce' ? 1 : 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = main(process.argv.slice(2));
}
