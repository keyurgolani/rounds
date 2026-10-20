// Shared context for conformance rules: repository file access, the base ref
// used for revision checks, and small helpers. Node built-ins only.

import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

// Directories never scanned when the file list comes from a filesystem walk.
const SKIP_DIRS = new Set([
  '.git', 'node_modules', 'dist', 'build', 'coverage', '__pycache__', '.pytest_cache',
  '.venv', 'venv', 'pb_data', '.receipts', '.claude', '.vite', '.mypy_cache', '.ruff_cache',
]);

const TEXT_EXTENSIONS = new Set([
  '.js', '.mjs', '.cjs', '.jsx', '.ts', '.tsx', '.py', '.md', '.json', '.yml', '.yaml',
  '.html', '.css', '.sh', '.toml', '.txt', '.conf', '.cfg', '.ini', '.sql', '.example',
]);

export function isTextPath(rel) {
  const base = path.basename(rel);
  if (base === 'Dockerfile' || base.startsWith('Dockerfile.') || base.startsWith('.env')) return true;
  return TEXT_EXTENSIONS.has(path.extname(rel));
}

function walk(root) {
  const out = [];
  const visit = (dir) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      if (entry.isDirectory()) {
        if (SKIP_DIRS.has(entry.name)) continue;
        visit(path.join(dir, entry.name));
      } else if (entry.isFile()) {
        out.push(path.relative(root, path.join(dir, entry.name)).split(path.sep).join('/'));
      }
    }
  };
  visit(root);
  return out.sort();
}

function gitFiles(root) {
  try {
    const out = execFileSync('git', ['-C', root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
      maxBuffer: 64 * 1024 * 1024,
    });
    // ls-files from a subdirectory of a work tree lists paths relative to it,
    // which is what we want; an empty list means "not a work tree" here.
    const files = out.split('\0').filter(Boolean).filter((f) => fs.existsSync(path.join(root, f)));
    return files.length ? files.sort() : null;
  } catch {
    return null;
  }
}

function isGitTopLevel(root) {
  try {
    const top = execFileSync('git', ['-C', root, 'rev-parse', '--show-toplevel'], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim();
    return fs.realpathSync(top) === fs.realpathSync(root);
  } catch {
    return false;
  }
}

function gitShow(root, ref, rel) {
  // Returns the file at ref, null when the ref exists but the file does not,
  // and throws when the ref itself cannot be resolved.
  execFileSync('git', ['-C', root, 'rev-parse', '--verify', '--quiet', `${ref}^{commit}`], {
    stdio: ['ignore', 'ignore', 'ignore'],
  });
  try {
    return execFileSync('git', ['-C', root, 'show', `${ref}:${rel}`], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
      maxBuffer: 64 * 1024 * 1024,
    });
  } catch {
    return null;
  }
}

// A read-only view of the repository at a git revision: files() lists its
// paths and read(rel) returns content (null when absent). One `git ls-tree`
// and one `git cat-file --batch` per prefetch keep it to a few processes.
// A commit never changes, so its view is shared by every context in the
// process, and a ref that is a commit hash resolves once.
const GIT_TREES = new Map();
const COMMIT_HASH = /^[0-9a-f]{7,40}$/;
function gitTree(root, ref) {
  const hashKey = COMMIT_HASH.test(ref) ? `${root}\0${ref}` : null;
  if (hashKey && GIT_TREES.has(hashKey)) return GIT_TREES.get(hashKey);
  let commit;
  try {
    commit = execFileSync('git', ['-C', root, 'rev-parse', '--verify', '--quiet', `${ref}^{commit}`], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim();
  } catch {
    return { ok: false, ref, reason: `cannot resolve ${ref}; fetch full history (actions/checkout fetch-depth: 0)` };
  }
  const key = `${root}\0${commit}`;
  if (!GIT_TREES.has(key)) GIT_TREES.set(key, buildGitTree(root, ref, commit));
  if (hashKey) GIT_TREES.set(hashKey, GIT_TREES.get(key));
  return GIT_TREES.get(key);
}

function buildGitTree(root, ref, commit) {
  const list = execFileSync('git', ['-C', root, 'ls-tree', '-r', '-z', '--name-only', commit], {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'ignore'],
    maxBuffer: 64 * 1024 * 1024,
  }).split('\0').filter(Boolean).sort();
  const present = new Set(list);
  const cache = new Map();
  const prefetch = (rels) => {
    const wanted = rels.filter((rel) => present.has(rel) && !cache.has(rel));
    if (!wanted.length) return;
    const out = execFileSync('git', ['-C', root, 'cat-file', '--batch'], {
      input: wanted.map((rel) => `${commit}:${rel}`).join('\n') + '\n',
      stdio: ['pipe', 'pipe', 'ignore'],
      maxBuffer: 256 * 1024 * 1024,
    });
    let pos = 0;
    for (const rel of wanted) {
      const nl = out.indexOf(10, pos);
      const header = out.subarray(pos, nl).toString('utf8');
      const size = Number(header.split(' ')[2]);
      if (!Number.isFinite(size) || header.endsWith('missing')) { cache.set(rel, null); pos = nl + 1; continue; }
      cache.set(rel, out.subarray(nl + 1, nl + 1 + size).toString('utf8').replace(/\r\n/g, '\n'));
      pos = nl + 1 + size + 1;
    }
  };
  return {
    ok: true,
    ref,
    commit,
    files: () => list,
    exists: (rel) => present.has(rel),
    prefetch,
    read(rel) {
      if (!present.has(rel)) return null;
      if (!cache.has(rel)) prefetch([rel]);
      return cache.get(rel);
    },
  };
}

// A tree from an in-memory map or a directory on disk, for fixtures.
function fixtureTree(ref, source) {
  if (source && typeof source === 'object' && source.files) {
    const files = source.files;
    const list = Object.keys(files).sort();
    return {
      ok: true, ref, commit: ref, files: () => list, prefetch: () => {},
      exists: (rel) => Object.prototype.hasOwnProperty.call(files, rel),
      read: (rel) => (Object.prototype.hasOwnProperty.call(files, rel) ? files[rel] : null),
    };
  }
  const dir = path.resolve(source.dir);
  const list = walk(dir);
  const present = new Set(list);
  return {
    ok: true, ref, commit: ref, files: () => list, prefetch: () => {},
    exists: (rel) => present.has(rel),
    read: (rel) => (present.has(rel) ? fs.readFileSync(path.join(dir, rel), 'utf8').replace(/\r\n/g, '\n') : null),
  };
}

// options.base: a git ref (default 'origin/main'), 'none' for no base, or an
// object { files: { [rel]: content } } that tests use instead of git.
// options.catalogPath: optional path to the rounds-review capabilities.json.
// options.reviewRoot: optional rounds-review checkout (catalog, ledger, spec).
// options.trees: { [ref]: { files } | { dir } } replaces git for tree(ref).
// options.treeRoot: the work tree that tree(ref) reads revisions from
// (default repoRoot), so a fixture directory can still read pinned revisions
// of the real repository.
export function createContext(repoRoot, options = {}) {
  const root = path.resolve(repoRoot);
  const cache = new Map();
  const trees = new Map();
  let fileList = null;
  const baseOption = options.base === undefined ? 'origin/main' : options.base;
  const reviewRoot = options.reviewRoot ? path.resolve(options.reviewRoot) : null;
  const ctx = {
    root,
    baseRef: typeof baseOption === 'string' ? baseOption : 'fixture',
    reviewRoot,
    catalogPath: options.catalogPath || (reviewRoot ? path.join(reviewRoot, 'src/data/capabilities.json') : null),
    // The repository at a pinned revision (the audited baseline).
    tree(ref) {
      if (!trees.has(ref)) {
        const override = options.trees && options.trees[ref];
        trees.set(ref, override ? fixtureTree(ref, override) : gitTree(options.treeRoot ? path.resolve(options.treeRoot) : root, ref));
      }
      return trees.get(ref);
    },
    abs: (rel) => path.join(root, rel),
    exists: (rel) => fs.existsSync(path.join(root, rel)),
    read(rel) {
      if (!cache.has(rel)) cache.set(rel, fs.readFileSync(path.join(root, rel), 'utf8').replace(/\r\n/g, '\n'));
      return cache.get(rel);
    },
    readJson(rel) {
      return JSON.parse(ctx.read(rel));
    },
    files() {
      if (!fileList) {
        const listed = isGitTopLevel(root) ? gitFiles(root) : null;
        fileList = listed || walk(root);
      }
      return fileList;
    },
    // Returns { ok: true, content } (content null when absent at base) or
    // { ok: false, reason } when no base is configured or it can't be read.
    readBase(rel) {
      if (baseOption === 'none' || baseOption === null) return { ok: false, reason: 'no base configured' };
      if (typeof baseOption === 'object') {
        const files = baseOption.files || {};
        return { ok: true, content: Object.prototype.hasOwnProperty.call(files, rel) ? files[rel] : null };
      }
      try {
        return { ok: true, content: gitShow(root, baseOption, rel) };
      } catch {
        return { ok: false, reason: `cannot resolve ${baseOption}` };
      }
    },
  };
  return ctx;
}

export function sha256(text) {
  return createHash('sha256').update(text).digest('hex');
}

export function finding(code, file, line, message) {
  return { code, path: file, line: line || 1, message };
}

// Canonical JSON (sorted keys) for content comparisons.
export function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((k) => `${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

// 1-based line of the first occurrence of needle in text (1 when absent).
export function lineOf(text, needle, from = 0) {
  const idx = text.indexOf(needle, from);
  if (idx === -1) return 1;
  let line = 1;
  for (let i = 0; i < idx; i++) if (text.charCodeAt(i) === 10) line++;
  return line;
}

// Line of a JSON path like ['terms', 3, 'owningLeaf']: walks the document
// structurally, so a key is found only in the object the path names. Stops
// at the deepest part it can reach (1 when the text isn't JSON there).
export function jsonLine(text, pathParts) {
  let i = skipJsonWs(text, 0);
  let reached = i;
  for (const part of pathParts) {
    const next = typeof part === 'number' ? jsonElement(text, i, part) : jsonMember(text, i, part);
    if (!next) break;
    reached = next.at;
    i = next.value;
  }
  let line = 1;
  for (let k = 0; k < reached && k < text.length; k++) if (text.charCodeAt(k) === 10) line++;
  return line;
}

function skipJsonWs(text, i) {
  while (i < text.length && /\s/.test(text[i])) i++;
  return i;
}

function skipJsonString(text, i) {
  // text[i] is the opening quote; returns the index just past the closing one.
  let j = i + 1;
  while (j < text.length && text[j] !== '"') j += text[j] === '\\' ? 2 : 1;
  return j + 1;
}

function skipJsonValue(text, i) {
  const ch = text[i];
  if (ch === '"') return skipJsonString(text, i);
  if (ch === '{' || ch === '[') {
    let depth = 0;
    let j = i;
    while (j < text.length) {
      const c = text[j];
      if (c === '"') { j = skipJsonString(text, j); continue; }
      if (c === '{' || c === '[') depth++;
      else if (c === '}' || c === ']') { depth--; if (depth === 0) return j + 1; }
      j++;
    }
    return text.length;
  }
  let j = i;
  while (j < text.length && !/[\s,}\]]/.test(text[j])) j++;
  return j;
}

// Member `key` of the object at text[i]: { at: key offset, value: value offset }.
function jsonMember(text, i, key) {
  if (text[i] !== '{') return null;
  let j = skipJsonWs(text, i + 1);
  while (j < text.length && text[j] !== '}') {
    if (text[j] !== '"') return null;
    const keyEnd = skipJsonString(text, j);
    let name;
    try { name = JSON.parse(text.slice(j, keyEnd)); } catch { return null; }
    let k = skipJsonWs(text, keyEnd);
    if (text[k] !== ':') return null;
    k = skipJsonWs(text, k + 1);
    if (name === key) return { at: j, value: k };
    j = skipJsonWs(text, skipJsonValue(text, k));
    if (text[j] === ',') j = skipJsonWs(text, j + 1);
  }
  return null;
}

// Element n of the array at text[i]: { at, value } (both the element offset).
function jsonElement(text, i, n) {
  if (text[i] !== '[') return null;
  let j = skipJsonWs(text, i + 1);
  for (let count = 0; j < text.length && text[j] !== ']'; count++) {
    if (count === n) return { at: j, value: j };
    j = skipJsonWs(text, skipJsonValue(text, j));
    if (text[j] === ',') j = skipJsonWs(text, j + 1);
  }
  return null;
}
