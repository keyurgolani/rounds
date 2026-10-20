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

// options.base: a git ref (default 'origin/main'), 'none' for no base, or an
// object { files: { [rel]: content } } that tests use instead of git.
// options.catalogPath: optional path to the rounds-review capabilities.json.
export function createContext(repoRoot, options = {}) {
  const root = path.resolve(repoRoot);
  const cache = new Map();
  let fileList = null;
  const baseOption = options.base === undefined ? 'origin/main' : options.base;
  const ctx = {
    root,
    baseRef: typeof baseOption === 'string' ? baseOption : 'fixture',
    catalogPath: options.catalogPath || null,
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

// Line of a JSON key path like ['terms', 3, 'owningLeaf'] in pretty-printed
// JSON. Best effort: finds the nth element's opening and then the key.
export function jsonLine(text, pathParts) {
  let from = 0;
  for (const part of pathParts) {
    if (typeof part === 'number') {
      // Advance to the start of the part-th object in the current array.
      let count = -1;
      let depth = 0;
      let i = from;
      for (; i < text.length; i++) {
        const ch = text[i];
        if (ch === '"') { i = skipJsonString(text, i); continue; }
        if (ch === '{' || ch === '[') {
          if (depth === 1 && ch === '{') { count++; if (count === part) break; }
          depth++;
        } else if (ch === '}' || ch === ']') {
          depth--;
          if (depth === 0) break;
        }
      }
      from = i;
    } else {
      const idx = text.indexOf(`"${part}"`, from);
      if (idx === -1) break;
      from = idx;
    }
  }
  let line = 1;
  for (let i = 0; i < from && i < text.length; i++) if (text.charCodeAt(i) === 10) line++;
  return line;
}

function skipJsonString(text, i) {
  let j = i + 1;
  while (j < text.length && text[j] !== '"') j += text[j] === '\\' ? 2 : 1;
  return j;
}
