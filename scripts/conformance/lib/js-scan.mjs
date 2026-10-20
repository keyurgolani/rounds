// Small source scanners for the conformance rules. Node built-ins only.
//
// tokenize() is a JavaScript lexer: comments, string and template literals,
// regular expression literals (by the usual previous-token heuristic),
// identifiers, numbers, and punctuation. It is enough to read literal values
// out of PocketBase migrations and plain modules. It does not parse JSX text,
// so TSX files go through readJsxOpeningElement() instead.

const REGEX_PREFIX_KEYWORDS = new Set([
  'return', 'typeof', 'case', 'do', 'else', 'in', 'instanceof', 'new', 'void',
  'delete', 'throw', 'yield', 'await', 'of',
]);
const REGEX_PREFIX_PUNCT = new Set('(,=:[!&|?{};+-*%<>~^'.split(''));
const IDENT_START = /[A-Za-z_$]/;
const IDENT_PART = /[A-Za-z0-9_$]/;

export function lineStarts(src) {
  const starts = [0];
  for (let i = 0; i < src.length; i++) if (src.charCodeAt(i) === 10) starts.push(i + 1);
  return starts;
}

export function lineAt(starts, index) {
  let lo = 0;
  let hi = starts.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (starts[mid] <= index) lo = mid;
    else hi = mid - 1;
  }
  return lo + 1;
}

function readQuoted(src, i) {
  // src[i] is the opening quote. Returns { value, end } with end after the closing quote.
  const quote = src[i];
  let j = i + 1;
  let value = '';
  while (j < src.length && src[j] !== quote) {
    if (src[j] === '\\' && j + 1 < src.length) {
      const next = src[j + 1];
      const map = { n: '\n', t: '\t', r: '\r', '\\': '\\', "'": "'", '"': '"', '`': '`' };
      value += Object.prototype.hasOwnProperty.call(map, next) ? map[next] : next;
      j += 2;
      continue;
    }
    if (src[j] === '\n' && quote !== '`') break; // unterminated string literal
    value += src[j];
    j++;
  }
  return { value, end: Math.min(j + 1, src.length) };
}

function readTemplate(src, i) {
  // src[i] is the opening backtick. Returns { value, end, hasExpressions }.
  let j = i + 1;
  let value = '';
  let hasExpressions = false;
  while (j < src.length && src[j] !== '`') {
    if (src[j] === '\\' && j + 1 < src.length) {
      value += src[j + 1];
      j += 2;
      continue;
    }
    if (src[j] === '$' && src[j + 1] === '{') {
      hasExpressions = true;
      j = skipBalancedCode(src, j + 1);
      continue;
    }
    value += src[j];
    j++;
  }
  return { value, end: Math.min(j + 1, src.length), hasExpressions };
}

function readRegex(src, i) {
  let j = i + 1;
  let inClass = false;
  while (j < src.length) {
    const ch = src[j];
    if (ch === '\\') { j += 2; continue; }
    if (ch === '\n') break;
    if (inClass) { if (ch === ']') inClass = false; }
    else if (ch === '[') inClass = true;
    else if (ch === '/') { j++; break; }
    j++;
  }
  while (j < src.length && /[a-z]/.test(src[j])) j++;
  return j;
}

function regexAllowed(prev) {
  if (!prev) return true;
  if (prev.type === 'punct') return REGEX_PREFIX_PUNCT.has(prev.value) || prev.value === '=>';
  if (prev.type === 'ident') return REGEX_PREFIX_KEYWORDS.has(prev.value);
  return false;
}

// Skips JavaScript code from src[i] === '{' (or '(' / '[') to just after its
// matching closer, honoring strings, templates, comments, and regex literals.
export function skipBalancedCode(src, i) {
  const open = src[i];
  const close = { '{': '}', '(': ')', '[': ']' }[open];
  let depth = 0;
  let j = i;
  let prev = null;
  while (j < src.length) {
    const ch = src[j];
    if (ch === '/' && src[j + 1] === '/') { const e = src.indexOf('\n', j); j = e === -1 ? src.length : e; continue; }
    if (ch === '/' && src[j + 1] === '*') { const e = src.indexOf('*/', j + 2); j = e === -1 ? src.length : e + 2; continue; }
    if (ch === '"' || ch === "'") { j = readQuoted(src, j).end; prev = { type: 'string' }; continue; }
    if (ch === '`') { j = readTemplate(src, j).end; prev = { type: 'string' }; continue; }
    if (ch === '/' && regexAllowed(prev)) { j = readRegex(src, j); prev = { type: 'regex' }; continue; }
    if (ch === open) depth++;
    else if (ch === close) { depth--; if (depth === 0) return j + 1; }
    if (IDENT_START.test(ch)) {
      let k = j + 1;
      while (k < src.length && IDENT_PART.test(src[k])) k++;
      prev = { type: 'ident', value: src.slice(j, k) };
      j = k;
      continue;
    }
    if (!/\s/.test(ch)) prev = { type: 'punct', value: ch };
    j++;
  }
  return src.length;
}

export function tokenize(src) {
  const starts = lineStarts(src);
  const tokens = [];
  let prev = null;
  let i = 0;
  const n = src.length;
  const push = (token) => {
    token.line = lineAt(starts, token.start);
    tokens.push(token);
    if (token.type !== 'comment') prev = token;
  };
  while (i < n) {
    const ch = src[i];
    if (/\s/.test(ch)) { i++; continue; }
    if (ch === '/' && src[i + 1] === '/') {
      const e = src.indexOf('\n', i);
      const end = e === -1 ? n : e;
      push({ type: 'comment', value: src.slice(i, end), start: i, end });
      i = end;
      continue;
    }
    if (ch === '/' && src[i + 1] === '*') {
      const e = src.indexOf('*/', i + 2);
      const end = e === -1 ? n : e + 2;
      push({ type: 'comment', value: src.slice(i, end), start: i, end });
      i = end;
      continue;
    }
    if (ch === '"' || ch === "'") {
      const { value, end } = readQuoted(src, i);
      push({ type: 'string', value, start: i, end });
      i = end;
      continue;
    }
    if (ch === '`') {
      const { value, end, hasExpressions } = readTemplate(src, i);
      push({ type: 'template', value, hasExpressions, start: i, end });
      i = end;
      continue;
    }
    if (ch === '/' && regexAllowed(prev)) {
      const end = readRegex(src, i);
      push({ type: 'regex', value: src.slice(i, end), start: i, end });
      i = end;
      continue;
    }
    if (IDENT_START.test(ch)) {
      let j = i + 1;
      while (j < n && IDENT_PART.test(src[j])) j++;
      push({ type: 'ident', value: src.slice(i, j), start: i, end: j });
      i = j;
      continue;
    }
    if (/[0-9]/.test(ch)) {
      let j = i + 1;
      while (j < n && /[0-9A-Za-z_.]/.test(src[j])) j++;
      push({ type: 'number', value: src.slice(i, j), start: i, end: j });
      i = j;
      continue;
    }
    if (ch === '=' && src[i + 1] === '>') { push({ type: 'punct', value: '=>', start: i, end: i + 2 }); i += 2; continue; }
    if (ch === '.' && src[i + 1] === '.' && src[i + 2] === '.') { push({ type: 'punct', value: '...', start: i, end: i + 3 }); i += 3; continue; }
    push({ type: 'punct', value: ch, start: i, end: i + 1 });
    i++;
  }
  return tokens.filter((t) => t.type !== 'comment');
}

const OPENERS = { '(': ')', '[': ']', '{': '}' };

// Index of the token that closes the bracket opened at tokens[i].
export function matchClose(tokens, i) {
  const open = tokens[i].value;
  const close = OPENERS[open];
  let depth = 0;
  for (let j = i; j < tokens.length; j++) {
    const t = tokens[j];
    if (t.type !== 'punct') continue;
    if (t.value === open) depth++;
    else if (t.value === close) { depth--; if (depth === 0) return j; }
  }
  return tokens.length - 1;
}

// Top-level comma-separated items inside the bracket at tokens[open].
export function splitItems(tokens, open) {
  const close = matchClose(tokens, open);
  const items = [];
  let start = open + 1;
  let depth = 0;
  for (let j = open + 1; j < close; j++) {
    const t = tokens[j];
    if (t.type === 'punct') {
      if (OPENERS[t.value]) depth++;
      else if (t.value === ')' || t.value === ']' || t.value === '}') depth--;
      else if (t.value === ',' && depth === 0) { if (j > start) items.push([start, j]); start = j + 1; }
    }
  }
  if (close > start) items.push([start, close]);
  return items;
}

// Top-level properties of the object literal opened by tokens[open] ('{').
// Returns Map name -> { keyIndex, valueStart, valueEnd, shorthand }.
export function objectProperties(tokens, open) {
  const props = new Map();
  for (const [start, end] of splitItems(tokens, open)) {
    const key = tokens[start];
    if (!key || (key.type !== 'ident' && key.type !== 'string')) continue;
    if (end - start === 1) {
      props.set(key.value, { keyIndex: start, valueStart: start, valueEnd: end, shorthand: true });
      continue;
    }
    if (tokens[start + 1] && tokens[start + 1].value === ':') {
      props.set(key.value, { keyIndex: start, valueStart: start + 2, valueEnd: end, shorthand: false });
    }
  }
  return props;
}

// String literals that are direct elements of the array opened by tokens[open].
export function arrayStrings(tokens, open) {
  const out = [];
  for (const [start, end] of splitItems(tokens, open)) {
    if (end - start === 1 && tokens[start].type === 'string') out.push(tokens[start]);
  }
  return out;
}

// Splits `migrate(up, down)` into the token ranges of its two function bodies.
export function migrateBodies(tokens) {
  for (let i = 0; i < tokens.length - 1; i++) {
    if (tokens[i].type === 'ident' && tokens[i].value === 'migrate' && tokens[i + 1].value === '(') {
      const args = splitItems(tokens, i + 1);
      const bodies = args.map(([start, end]) => {
        for (let j = start; j < end; j++) {
          if (tokens[j].value === '{' && tokens[j].type === 'punct') return [j, matchClose(tokens, j)];
        }
        return [start, end];
      });
      return { up: bodies[0] || null, down: bodies[1] || null };
    }
  }
  return { up: null, down: null };
}

// ---------------------------------------------------------------------------
// JSX: just enough structure to read the attributes of one opening element.

function skipWsAndComments(src, i) {
  let j = i;
  for (;;) {
    while (j < src.length && /\s/.test(src[j])) j++;
    if (src[j] === '/' && src[j + 1] === '/') { const e = src.indexOf('\n', j); j = e === -1 ? src.length : e; continue; }
    if (src[j] === '/' && src[j + 1] === '*') { const e = src.indexOf('*/', j + 2); j = e === -1 ? src.length : e + 2; continue; }
    return j;
  }
}

function jsxStartsAt(src, i, prevChar, prevWord) {
  if (src[i] !== '<') return false;
  const next = src[i + 1];
  if (!(next === '>' || IDENT_START.test(next || ''))) return false;
  if (prevWord === 'return') return true;
  return prevChar === '' || '(,{[:?=&|!;>'.includes(prevChar);
}

// Skips a JSX expression container from src[i] === '{' to after its '}'.
export function skipJsxExpression(src, i) {
  let depth = 0;
  let j = i;
  let prevChar = '';
  let prevWord = '';
  while (j < src.length) {
    const ch = src[j];
    if (ch === '/' && src[j + 1] === '/') { const e = src.indexOf('\n', j); j = e === -1 ? src.length : e; continue; }
    if (ch === '/' && src[j + 1] === '*') { const e = src.indexOf('*/', j + 2); j = e === -1 ? src.length : e + 2; continue; }
    if (ch === '"' || ch === "'") { j = readQuoted(src, j).end; prevChar = 'x'; prevWord = ''; continue; }
    if (ch === '`') { j = readTemplate(src, j).end; prevChar = 'x'; prevWord = ''; continue; }
    if (ch === '<' && jsxStartsAt(src, j, prevChar, prevWord)) { j = skipJsxElement(src, j); prevChar = 'x'; prevWord = ''; continue; }
    if (ch === '{') depth++;
    else if (ch === '}') { depth--; if (depth === 0) return j + 1; }
    if (IDENT_START.test(ch)) {
      let k = j + 1;
      while (k < src.length && IDENT_PART.test(src[k])) k++;
      prevWord = src.slice(j, k);
      prevChar = 'x';
      j = k;
      continue;
    }
    if (!/\s/.test(ch)) { prevChar = ch; prevWord = ''; }
    j++;
  }
  return src.length;
}

function readJsxName(src, i) {
  let j = i;
  while (j < src.length && /[A-Za-z0-9_$.:-]/.test(src[j])) j++;
  return { name: src.slice(i, j), end: j };
}

// Reads the opening element starting at src[i] === '<'. Returns
// { name, attributes, end, selfClosing } where end is just after '>' or '/>'.
// Each attribute is { name, start, kind, literal } with kind 'string' for
// "x" / 'x' / {"x"} / {`x`} (no ${}), 'expression' for any other {...}, and
// 'none' for a bare attribute.
export function readJsxOpeningElement(src, i) {
  const { name, end: nameEnd } = readJsxName(src, i + 1);
  const attributes = [];
  let j = nameEnd;
  for (;;) {
    j = skipWsAndComments(src, j);
    if (j >= src.length) return { name, attributes, end: j, selfClosing: false };
    if (src[j] === '/' && src[j + 1] === '>') return { name, attributes, end: j + 2, selfClosing: true };
    if (src[j] === '>') return { name, attributes, end: j + 1, selfClosing: false };
    if (src[j] === '{') { j = skipJsxExpression(src, j); continue; } // spread attribute
    const attr = readJsxName(src, j);
    if (!attr.name) { j++; continue; }
    const start = j;
    j = skipWsAndComments(src, attr.end);
    if (src[j] !== '=') { attributes.push({ name: attr.name, start, kind: 'none', literal: null }); continue; }
    j = skipWsAndComments(src, j + 1);
    if (src[j] === '"' || src[j] === "'") {
      const q = src[j];
      const close = src.indexOf(q, j + 1);
      const end = close === -1 ? src.length : close;
      attributes.push({ name: attr.name, start, kind: 'string', literal: src.slice(j + 1, end) });
      j = end + 1;
      continue;
    }
    if (src[j] === '{') {
      const exprEnd = skipJsxExpression(src, j);
      const inner = src.slice(j + 1, exprEnd - 1).trim();
      let literal = null;
      const quoted = /^(["'])((?:\\.|(?!\1)[^\\])*)\1$/s.exec(inner);
      if (quoted) literal = readQuoted(inner, 0).value;
      else if (/^`[^`]*`$/s.test(inner) && !inner.includes('${')) literal = inner.slice(1, -1);
      attributes.push({ name: attr.name, start, kind: literal === null ? 'expression' : 'string', literal });
      j = exprEnd;
      continue;
    }
    j++;
  }
}

// Skips a whole JSX element (with children) from src[i] === '<'.
export function skipJsxElement(src, i) {
  if (src[i + 1] === '>') return skipJsxChildren(src, i + 2, '');
  const open = readJsxOpeningElement(src, i);
  if (open.selfClosing) return open.end;
  return skipJsxChildren(src, open.end, open.name);
}

function skipJsxChildren(src, i, name) {
  let j = i;
  while (j < src.length) {
    if (src[j] === '<' && src[j + 1] === '/') {
      const close = src.indexOf('>', j);
      const closing = src.slice(j + 2, close).trim();
      if (closing === name) return close + 1;
      j = close + 1;
      continue;
    }
    if (src[j] === '<') { j = skipJsxElement(src, j); continue; }
    if (src[j] === '{') { j = skipJsxExpression(src, j); continue; }
    j++;
  }
  return src.length;
}
