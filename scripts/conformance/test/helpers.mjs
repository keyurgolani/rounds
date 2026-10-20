// Shared fixtures for the conformance tests. A fixture is a temporary copy of
// the repository files the rules read, so negative controls can mutate it.

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createContext } from '../lib/context.mjs';

export const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
export const FIXTURES = path.join(path.dirname(fileURLToPath(import.meta.url)), 'fixtures');

const COPY_DIRS = ['contracts/vocabulary', 'docs/decisions', 'pocketbase/pb_migrations', 'backend/routers'];
const COPY_FILES = [
  'backend/main.py', 'frontend/src/App.tsx', 'frontend/src/components/Layout.tsx', 'frontend/src/command-center/registry.tsx',
  'frontend/src/applications/interviewTypes.ts', 'frontend/src/auth/AuthProvider.tsx', 'frontend/index.html',
  'frontend/src/pages/Login.tsx', 'README.md', 'docs/architecture.md', 'SHOWCASE.md',
  // Generated outputs, for drift checks.
  'docs/vocabulary.md', 'frontend/src/vocabulary/labels.ts',
];

function appHeaderFiles() {
  const out = [];
  const walk = (dir) => {
    for (const e of fs.readdirSync(path.join(REPO_ROOT, dir), { withFileTypes: true })) {
      const rel = `${dir}/${e.name}`;
      if (e.isDirectory()) { if (e.name !== '__tests__' && e.name !== 'node_modules') walk(rel); continue; }
      if (rel.endsWith('.tsx') && !rel.endsWith('.test.tsx') && fs.readFileSync(path.join(REPO_ROOT, rel), 'utf8').includes('<AppHeader')) out.push(rel);
    }
  };
  walk('frontend/src');
  return out;
}

let baseFixture = null;
const created = [];

export function tempDir(prefix = 'rounds-conformance-') {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), prefix));
  created.push(dir);
  return dir;
}

export function cleanup() {
  for (const dir of created.splice(0)) fs.rmSync(dir, { recursive: true, force: true });
  baseFixture = null;
}

function copyInto(target, rel) {
  const from = path.join(REPO_ROOT, rel);
  const to = path.join(target, rel);
  fs.mkdirSync(path.dirname(to), { recursive: true });
  fs.cpSync(from, to, { recursive: true });
}

export function baseFixtureDir() {
  if (baseFixture) return baseFixture;
  const dir = tempDir('rounds-conformance-base-');
  for (const rel of [...COPY_DIRS, ...COPY_FILES, ...appHeaderFiles()]) copyInto(dir, rel);
  baseFixture = dir;
  return dir;
}

// Copies the base fixture, applies mutate(dir), and returns the directory.
export function fixture(mutate = () => {}) {
  const dir = tempDir();
  fs.cpSync(baseFixtureDir(), dir, { recursive: true });
  mutate(dir);
  return dir;
}

export function readJson(dir, rel) {
  return JSON.parse(fs.readFileSync(path.join(dir, rel), 'utf8'));
}

export function writeJson(dir, rel, data) {
  fs.mkdirSync(path.dirname(path.join(dir, rel)), { recursive: true });
  fs.writeFileSync(path.join(dir, rel), `${JSON.stringify(data, null, 2)}\n`);
}

export function editJson(dir, rel, fn) {
  const data = readJson(dir, rel);
  const result = fn(data);
  writeJson(dir, rel, result === undefined ? data : result);
}

export function editText(dir, rel, fn) {
  const file = path.join(dir, rel);
  fs.writeFileSync(file, fn(fs.readFileSync(file, 'utf8')));
}

// No base ref unless a test passes one: { files: { 'contracts/vocabulary/terms.json': '...' } }.
export function ctxFor(dir, options = {}) {
  return createContext(dir, { base: { files: {} }, ...options });
}

export const codes = (findings) => [...new Set(findings.map((f) => f.code))].sort();
