#!/usr/bin/env node
// Trims a `gh issue list` export to docs/program/issue-export.json
// (ROUNDS-01-L03 S2): each issue's number, title, and "Exact prerequisite
// leaf issues" section, and nothing else from the body, with a SHA-256 over
// the result. The owner or an agent runs gh once; CI only reads the file.
//
//   gh issue list --repo keyurgolani/rounds --state all --limit 300 --json number,title,body > issues.json
//   node scripts/program/export.mjs --from issues.json --write
//   node scripts/conformance/run.mjs --write     # regenerates leaf-dag.json
//
// Without --write it prints the export. Exits 2 on bad arguments or input.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { prettyJson } from '../conformance/lib/pretty-json.mjs';
import { EXPORT_PATH, trimExport } from './dag.mjs';

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');

export function parseArgs(argv) {
  const opts = { from: null, write: false, repo: 'keyurgolani/rounds', exportedOn: new Date().toISOString().slice(0, 10), root: REPO_ROOT };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const value = () => {
      const v = argv[++i];
      if (v === undefined || v.startsWith('--')) throw new Error(`${a} needs a value`);
      return v;
    };
    if (a === '--from') opts.from = value();
    else if (a === '--write') opts.write = true;
    else if (a === '--repo') opts.repo = value();
    else if (a === '--exported-on') opts.exportedOn = value();
    else if (a === '--root') opts.root = path.resolve(value());
    else if (a === '--help' || a === '-h') opts.help = true;
    else throw new Error(`unknown argument ${a}`);
  }
  if (!opts.help && !opts.from) throw new Error('--from <gh issue list output> is required');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(opts.exportedOn)) throw new Error('--exported-on takes YYYY-MM-DD');
  return opts;
}

export function main(argv, io = { out: process.stdout, err: process.stderr }) {
  let opts;
  try {
    opts = parseArgs(argv);
  } catch (err) {
    io.err.write(`export.mjs: ${err.message}\n`);
    return 2;
  }
  if (opts.help) {
    io.out.write('usage: node scripts/program/export.mjs --from <issues.json> [--write] [--repo <owner/name>] [--exported-on YYYY-MM-DD]\n');
    return 0;
  }
  let text;
  try {
    const raw = JSON.parse(fs.readFileSync(opts.from, 'utf8'));
    text = prettyJson(trimExport(raw, { repo: opts.repo, exportedOn: opts.exportedOn }));
  } catch (err) {
    io.err.write(`export.mjs: cannot read ${opts.from}: ${err.message}\n`);
    return 2;
  }
  if (!opts.write) {
    io.out.write(text);
    return 0;
  }
  fs.writeFileSync(path.join(opts.root, EXPORT_PATH), text);
  io.out.write(`wrote ${EXPORT_PATH}\n`);
  return 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = main(process.argv.slice(2));
}
