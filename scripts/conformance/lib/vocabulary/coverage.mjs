// Extracts the vocabulary coverage set (ROUNDS-01-L01) from the repository:
//
//   collection     PocketBase collections created or dropped by migrations, plus built-in `users`
//   stored-value   user_progress.question_type and .status select values, and the
//                  INTERVIEW_TYPES keys stored in interview_rounds.round_type
//   api-route      runner router prefixes mounted in backend/main.py, and /health
//   route-segment  literal path segments in frontend/src/App.tsx
//   ui-string      navigation labels in Layout.tsx and Command Center entry labels and descriptions
//   app-header     literal eyebrow and title props at every <AppHeader> call site
//   positioning    the six product positioning lines
//
// Every extracted name must map to a term label or an adapter entry. #155
// (ROUNDS-32-L01) takes over the collection extraction once its store registry lands.

import path from 'node:path';
import {
  arrayStrings, lineAt, lineStarts, matchClose, migrateBodies, objectProperties,
  readJsxOpeningElement, tokenize,
} from '../js-scan.mjs';

export const MIGRATIONS_DIR = 'pocketbase/pb_migrations';
export const BUILTIN_COLLECTIONS = [
  // PocketBase creates the auth collection itself; migrations only extend it.
  { name: 'users', path: 'pocketbase/pb_migrations/1700000000_init_collections.js', marker: 'findCollectionByNameOrId("users")' },
];
export const STORED_SELECTS = [
  { collection: 'user_progress', field: 'question_type' },
  { collection: 'user_progress', field: 'status' },
];
export const INTERVIEW_TYPES_PATH = 'frontend/src/applications/interviewTypes.ts';
export const BACKEND_MAIN = 'backend/main.py';
export const APP_ROUTES = 'frontend/src/App.tsx';
export const LAYOUT = 'frontend/src/components/Layout.tsx';
export const COMMAND_REGISTRY = 'frontend/src/command-center/registry.tsx';
// The six positioning lines. Each is found by content, never by line number:
// the line that equals the rendered template, or else the legacy line its
// adapter entry records.
export const POSITIONING_SITES = [
  { path: 'README.md', template: '# Rounds: {title}' },
  { path: 'README.md', template: '{statement}' },
  { path: 'docs/architecture.md', template: '{statement}' },
  { path: 'frontend/index.html', template: '<title>Rounds: {title}</title>' },
  { path: 'frontend/src/pages/Login.tsx', template: '<div className="eyebrow mb-2">Rounds · {title}</div>' },
  { path: 'SHOWCASE.md', template: '{statement}' },
];

const item = (kind, name, file, line, extra = {}) => ({ kind, name, path: file, line, ...extra });

// ------------------------------------------------------------ collections

function stringArg(tokens, open) {
  // tokens[open] is '(' of a call; returns the string token if the call's only
  // argument is a string literal.
  const close = matchClose(tokens, open);
  if (close === open + 2 && tokens[open + 1].type === 'string') return tokens[open + 1];
  return null;
}

// Map identifier -> collection name for `const x = <dao>.findCollectionByNameOrId("name")`.
function collectionBindings(tokens, from, to) {
  const bindings = [];
  for (let i = from; i < to - 2; i++) {
    const t = tokens[i];
    if (t.type !== 'ident' || t.value !== 'findCollectionByNameOrId' || tokens[i + 1].value !== '(') continue;
    const arg = stringArg(tokens, i + 1);
    if (!arg) continue;
    // Walk back over `<expr>.` to the `name =` assignment.
    let j = i - 1;
    while (j > from && (tokens[j].value === '.' || tokens[j].type === 'ident') && tokens[j].value !== '=') j--;
    if (tokens[j] && tokens[j].value === '=' && tokens[j - 1] && tokens[j - 1].type === 'ident') {
      bindings.push({ name: tokens[j - 1].value, collection: arg.value, index: j - 1 });
    }
  }
  return bindings;
}

function resolveBinding(bindings, name, index) {
  let best = null;
  for (const b of bindings) if (b.name === name && b.index < index) best = b;
  return best;
}

export function migrationFiles(ctx) {
  return ctx.files().filter((f) => f.startsWith(`${MIGRATIONS_DIR}/`) && f.endsWith('.js') && path.posix.dirname(f) === MIGRATIONS_DIR).sort();
}

// Collection lifecycle events in migration order, from `up` bodies only.
// TODO(ROUNDS-32-L01): collection extraction moves to #155's store registry
// once it lands (DR-0001 C5); the rule then reads collections from there.
export function collectionEvents(ctx) {
  const events = [];
  for (const file of migrationFiles(ctx)) {
    const tokens = tokenize(ctx.read(file));
    const { up } = migrateBodies(tokens);
    if (!up) continue;
    const [from, to] = up;
    const bindings = collectionBindings(tokens, from, to);
    for (let i = from; i < to; i++) {
      const t = tokens[i];
      if (t.type === 'ident' && t.value === 'new' && tokens[i + 1]?.value === 'Collection' && tokens[i + 2]?.value === '(') {
        const open = tokens[i + 3]?.value === '{' ? i + 3 : -1;
        const props = open === -1 ? new Map() : objectProperties(tokens, open);
        const nameProp = props.get('name');
        const literal = nameProp && !nameProp.shorthand && nameProp.valueEnd - nameProp.valueStart === 1 && tokens[nameProp.valueStart].type === 'string';
        if (literal) events.push({ type: 'create', name: tokens[nameProp.valueStart].value, path: file, line: tokens[nameProp.valueStart].line });
        else events.push({ type: 'create-nonliteral', path: file, line: t.line });
      }
      if (t.type === 'ident' && t.value === 'deleteCollection' && tokens[i + 1]?.value === '(') {
        const open = i + 1;
        const close = matchClose(tokens, open);
        let name = null;
        if (tokens[open + 1]?.type === 'ident' && close === open + 2) {
          name = resolveBinding(bindings, tokens[open + 1].value, i)?.collection || null;
        } else {
          for (let j = open + 1; j < close; j++) {
            if (tokens[j].value === 'findCollectionByNameOrId' && tokens[j + 1]?.value === '(') {
              name = stringArg(tokens, j + 1)?.value || null;
            }
          }
        }
        if (name) events.push({ type: 'delete', name, path: file, line: t.line });
        else events.push({ type: 'delete-nonliteral', path: file, line: t.line });
      }
    }
  }
  return events;
}

// Applies collection events. `resolveNonLiteral(event)` returns the names an
// adapter entry declares for a non-literal create or delete site (or null).
export function extractCollections(ctx, resolveNonLiteral = () => null) {
  const state = new Map(); // name -> { live, createdAt: {path,line}, droppedAt }
  const unresolved = [];
  for (const b of BUILTIN_COLLECTIONS) {
    const text = ctx.exists(b.path) ? ctx.read(b.path) : '';
    const idx = text.indexOf(b.marker);
    const line = idx === -1 ? 1 : lineAt(lineStarts(text), idx);
    state.set(b.name, { live: true, createdAt: { path: b.path, line }, builtin: true });
  }
  for (const ev of collectionEvents(ctx)) {
    let names = ev.name ? [ev.name] : null;
    if (!names) {
      names = resolveNonLiteral(ev);
      if (!names) { unresolved.push(ev); continue; }
    }
    for (const name of names) {
      if (ev.type.startsWith('create')) {
        const prev = state.get(name);
        state.set(name, { live: true, createdAt: prev?.createdAt || { path: ev.path, line: ev.line }, nonLiteral: ev.type === 'create-nonliteral' });
      } else {
        const prev = state.get(name) || { createdAt: { path: ev.path, line: ev.line } };
        state.set(name, { ...prev, live: false, droppedAt: { path: ev.path, line: ev.line } });
      }
    }
  }
  const items = [];
  for (const [name, s] of [...state.entries()].sort(([a], [b]) => a.localeCompare(b))) {
    items.push(item('collection', name, s.createdAt.path, s.createdAt.line, { historical: !s.live, ...(s.droppedAt ? { droppedAt: s.droppedAt } : {}) }));
  }
  return { items, unresolved };
}

// ---------------------------------------------------------- stored values

function selectValuesFromInit(tokens, from, to, collection, field) {
  const out = [];
  for (let i = from; i < to; i++) {
    if (!(tokens[i].value === 'new' && tokens[i + 1]?.value === 'Collection' && tokens[i + 3]?.value === '{')) continue;
    const props = objectProperties(tokens, i + 3);
    const nameProp = props.get('name');
    if (!nameProp || tokens[nameProp.valueStart].value !== collection) continue;
    const schemaProp = props.get('schema');
    if (!schemaProp || tokens[schemaProp.valueStart].value !== '[') continue;
    const schemaOpen = schemaProp.valueStart;
    for (let j = schemaOpen + 1; j < matchClose(tokens, schemaOpen); j++) {
      if (tokens[j].value !== '{') continue;
      const fieldProps = objectProperties(tokens, j);
      const fname = fieldProps.get('name');
      if (fname && tokens[fname.valueStart].value === field) {
        const options = fieldProps.get('options');
        if (options && tokens[options.valueStart].value === '{') {
          const values = objectProperties(tokens, options.valueStart).get('values');
          if (values && tokens[values.valueStart].value === '[') out.push(...arrayStrings(tokens, values.valueStart));
        }
      }
      j = matchClose(tokens, j);
    }
  }
  return out;
}

function selectValueAdditions(tokens, from, to, collection, field) {
  // `const f = <coll>.schema.getFieldByName("field")` where <coll> is bound to
  // findCollectionByNameOrId("collection"), then `f.options.values = [..., "x"]`.
  const out = [];
  const colls = collectionBindings(tokens, from, to);
  const fieldVars = new Set();
  for (let i = from; i < to; i++) {
    if (tokens[i].value !== 'getFieldByName' || tokens[i + 1]?.value !== '(') continue;
    const arg = stringArg(tokens, i + 1);
    if (!arg || arg.value !== field) continue;
    // ... = <collVar> . schema . getFieldByName
    const collVar = tokens[i - 4]?.type === 'ident' && tokens[i - 3]?.value === '.' && tokens[i - 2]?.value === 'schema' ? tokens[i - 4].value : null;
    const bound = collVar ? resolveBinding(colls, collVar, i) : null;
    if (!bound || bound.collection !== collection) continue;
    if (tokens[i - 5]?.value === '=' && tokens[i - 6]?.type === 'ident') fieldVars.add(tokens[i - 6].value);
  }
  for (let i = from; i < to; i++) {
    const t = tokens[i];
    if (t.type === 'ident' && fieldVars.has(t.value) && tokens[i + 1]?.value === '.' && tokens[i + 2]?.value === 'options'
      && tokens[i + 3]?.value === '.' && tokens[i + 4]?.value === 'values' && tokens[i + 5]?.value === '=' && tokens[i + 6]?.value === '[') {
      out.push(...arrayStrings(tokens, i + 6));
    }
  }
  return out;
}

export function extractStoredValues(ctx) {
  const items = [];
  for (const { collection, field } of STORED_SELECTS) {
    const seen = new Set();
    for (const file of migrationFiles(ctx)) {
      const tokens = tokenize(ctx.read(file));
      const { up } = migrateBodies(tokens);
      if (!up) continue;
      const found = [...selectValuesFromInit(tokens, up[0], up[1], collection, field), ...selectValueAdditions(tokens, up[0], up[1], collection, field)];
      for (const tok of found) {
        if (seen.has(tok.value)) continue;
        seen.add(tok.value);
        items.push(item('stored-value', tok.value, file, tok.line, { field: `${collection}.${field}` }));
      }
    }
  }
  if (ctx.exists(INTERVIEW_TYPES_PATH)) {
    const tokens = tokenize(ctx.read(INTERVIEW_TYPES_PATH));
    const field = 'interview_rounds.round_type';
    // export const INTERVIEW_TYPES: InterviewTypeEntry[] = [ ... ]
    const types = declarationValue(tokens, 'INTERVIEW_TYPES', '[');
    if (types !== -1) {
      for (let j = types + 1; j < matchClose(tokens, types); j++) {
        if (tokens[j].value !== '{') continue;
        const key = objectProperties(tokens, j).get('key');
        if (key && tokens[key.valueStart].type === 'string') items.push(item('stored-value', tokens[key.valueStart].value, INTERVIEW_TYPES_PATH, tokens[key.valueStart].line, { field }));
        j = matchClose(tokens, j);
      }
    }
    // const INTERVIEW_TYPE_ALIASES: Record<string, string> = { ... }
    const aliases = declarationValue(tokens, 'INTERVIEW_TYPE_ALIASES', '{');
    if (aliases !== -1) {
      for (const [name, prop] of objectProperties(tokens, aliases)) items.push(item('stored-value', name, INTERVIEW_TYPES_PATH, tokens[prop.keyIndex].line, { field, alias: true }));
    }
  }
  return items;
}

// Index of the opening bracket of `const <name>[: Type] = <opener>`, or -1.
// Uses of the name elsewhere in the file never match.
function declarationValue(tokens, name, opener) {
  for (let i = 1; i < tokens.length - 1; i++) {
    const t = tokens[i];
    if (t.type !== 'ident' || t.value !== name) continue;
    if (!['const', 'let', 'var'].includes(tokens[i - 1].value)) continue;
    let j = i + 1;
    if (tokens[j].value === ':') {
      // Skip the type annotation: angle brackets and [] nest.
      let depth = 0;
      for (j = j + 1; j < tokens.length; j++) {
        const v = tokens[j].value;
        if (v === '<' || v === '[' || v === '(' || (v === '{' && depth > 0)) depth++;
        else if (v === '>' || v === ']' || v === ')' || (v === '}' && depth > 0)) depth--;
        else if (depth === 0 && v === '=') break;
        else if (depth === 0 && v === ';') return -1;
      }
    }
    if (tokens[j]?.value !== '=') return -1;
    return tokens[j + 1]?.value === opener ? j + 1 : -1;
  }
  return -1;
}

// ------------------------------------------------------------- api routes

export function extractApiRoutes(ctx) {
  const items = [];
  if (!ctx.exists(BACKEND_MAIN)) return items;
  const main = ctx.read(BACKEND_MAIN);
  const lines = main.split('\n');
  lines.forEach((text, idx) => {
    const inc = /^\s*app\.include_router\(\s*([A-Za-z_][A-Za-z0-9_]*)\.router\s*\)/.exec(text);
    if (inc) {
      const modPath = `backend/routers/${inc[1]}.py`;
      if (!ctx.exists(modPath)) return;
      const mod = ctx.read(modPath);
      const m = /APIRouter\(\s*prefix\s*=\s*["']([^"']+)["']/.exec(mod);
      if (m) {
        const line = mod.slice(0, m.index).split('\n').length;
        items.push(item('api-route', m[1], modPath, line, { mountedAt: { path: BACKEND_MAIN, line: idx + 1 } }));
      }
    }
    const direct = /^\s*@app\.(?:get|post|put|patch|delete|head|options)\(\s*["']([^"']+)["']/.exec(text);
    if (direct) items.push(item('api-route', direct[1], BACKEND_MAIN, idx + 1));
  });
  return items;
}

// --------------------------------------------------------- route segments

export function extractRouteSegments(ctx) {
  if (!ctx.exists(APP_ROUTES)) return [];
  const src = ctx.read(APP_ROUTES);
  const starts = lineStarts(src);
  const bySegment = new Map();
  const re = /<(Route|Navigate)\b/g;
  let m;
  while ((m = re.exec(src))) {
    const el = readJsxOpeningElement(src, m.index);
    const attr = el.attributes.find((a) => a.name === (m[1] === 'Route' ? 'path' : 'to') && a.kind === 'string');
    if (!attr) continue;
    const line = lineAt(starts, attr.start);
    for (const seg of attr.literal.split('/')) {
      if (!seg || seg.startsWith(':') || seg === '*') continue;
      if (!bySegment.has(seg)) bySegment.set(seg, []);
      if (!bySegment.get(seg).includes(line)) bySegment.get(seg).push(line);
    }
  }
  return [...bySegment.entries()].map(([seg, lines]) => item('route-segment', seg, APP_ROUTES, lines[0], { lines }));
}

// ------------------------------------------------------------- UI strings

function pushString(map, name, file, line) {
  const key = `${file}\u0000${name}`;
  if (!map.has(key)) map.set(key, item('ui-string', name, file, line, { lines: [] }));
  const entry = map.get(key);
  if (!entry.lines.includes(line)) entry.lines.push(line);
}

// String value of an object property when it is one string literal (either
// quote style) or a template literal without substitutions.
function literalValue(tokens, prop) {
  if (!prop || prop.shorthand || prop.valueEnd - prop.valueStart !== 1) return null;
  const t = tokens[prop.valueStart];
  if (t.type === 'string') return t;
  if (t.type === 'template' && !t.hasExpressions) return t;
  return null;
}

// Object literals in src that carry every property in `keys` as a literal,
// in any order: yields { tokens, props, values }.
function* literalObjects(src, keys) {
  const tokens = tokenize(src);
  for (let i = 0; i < tokens.length; i++) {
    if (tokens[i].type !== 'punct' || tokens[i].value !== '{') continue;
    const props = objectProperties(tokens, i);
    const values = {};
    let ok = true;
    for (const k of keys) {
      const v = literalValue(tokens, props.get(k));
      if (!v) { ok = false; break; }
      values[k] = v;
    }
    if (ok) yield { tokens, props, values };
  }
}

export function extractUiStrings(ctx) {
  const found = new Map();
  if (ctx.exists(LAYOUT)) {
    const src = ctx.read(LAYOUT);
    const starts = lineStarts(src);
    // Navigation definitions: objects with a literal path and label, in any
    // key order and quote style.
    for (const { values } of literalObjects(src, ['path', 'label'])) pushString(found, values.label.value, LAYOUT, values.label.line);
    // User-menu destinations: <MenuItem label="..." onClick={() => onNavigate('/x')} />,
    // attributes in any order.
    for (const m of src.matchAll(/<MenuItem\b/g)) {
      const el = readJsxOpeningElement(src, m.index);
      const label = el.attributes.find((a) => a.name === 'label' && a.kind === 'string');
      const click = el.attributes.find((a) => a.name === 'onClick' && a.kind === 'expression');
      if (!label || !click || !/^\(\)\s*=>\s*(?:onNavigate|go)\(\s*(["'`])[^"'`]*\1\s*\)$/.test(click.expression)) continue;
      pushString(found, label.literal, LAYOUT, lineAt(starts, label.start));
    }
    // Sidebar section headings: <div className="eyebrow ...">Text</div>.
    for (const m of src.matchAll(/<div className=(?:"|'|\{["'`])eyebrow[^"'`]*(?:"|'|["'`]\})[^>]*>\s*([^<{}]+?)\s*<\/div>/g)) pushString(found, m[1], LAYOUT, lineAt(starts, m.index + m[0].indexOf(m[1])));
  }
  if (ctx.exists(COMMAND_REGISTRY)) {
    const src = ctx.read(COMMAND_REGISTRY);
    // Command Center entries: objects with a literal id and label, and the
    // description when it is a literal, in any key order and quote style.
    for (const { tokens, props, values } of literalObjects(src, ['id', 'label'])) {
      pushString(found, values.label.value, COMMAND_REGISTRY, values.label.line);
      const description = literalValue(tokens, props.get('description'));
      if (description) pushString(found, description.value, COMMAND_REGISTRY, description.line);
    }
  }
  return [...found.values()];
}

// ---------------------------------------------------- <AppHeader> props

export function appHeaderFiles(ctx) {
  return ctx.files().filter((f) => f.startsWith('frontend/src/') && f.endsWith('.tsx') && !f.includes('/__tests__/') && !f.endsWith('.test.tsx'));
}

export function extractAppHeaders(ctx) {
  const items = [];
  let callSites = 0;
  for (const file of appHeaderFiles(ctx)) {
    const src = ctx.read(file);
    if (!src.includes('<AppHeader')) continue;
    const starts = lineStarts(src);
    const re = /<AppHeader\b/g;
    let m;
    while ((m = re.exec(src))) {
      callSites++;
      const el = readJsxOpeningElement(src, m.index);
      for (const attr of el.attributes) {
        if ((attr.name === 'eyebrow' || attr.name === 'title') && attr.kind === 'string' && attr.literal.trim()) {
          items.push(item('app-header', attr.literal, file, lineAt(starts, attr.start), { prop: attr.name }));
        }
      }
    }
  }
  return { items, callSites };
}

// ------------------------------------------------------------- positioning

export function renderPositioning(template, positioning) {
  return template.replace('{statement}', positioning.statement).replace('{title}', positioning.title);
}

// Locates each positioning site by content. `candidates(site)` lists the
// texts that may stand there ({ text, adapter? }), in order of preference;
// the item's name is the matching text and its line where it was found, or
// name null when no line in the file matches.
export function extractPositioning(ctx, candidates = () => []) {
  return POSITIONING_SITES.map((site) => {
    const lines = ctx.exists(site.path) ? ctx.read(site.path).split('\n').map((l) => l.trim()) : [];
    const options = candidates(site);
    for (const candidate of options) {
      const idx = lines.indexOf(candidate.text.trim());
      if (idx !== -1) return item('positioning', candidate.text.trim(), site.path, idx + 1, { template: site.template, found: candidate });
    }
    return item('positioning', null, site.path, nearestLine(lines, options.map((c) => c.text.trim())), { template: site.template, found: null });
  });
}

// For a finding's line only: the line sharing the longest prefix (at least
// eight characters) with any candidate text, else 1.
function nearestLine(lines, texts) {
  let best = { line: 1, length: 7 };
  lines.forEach((l, i) => {
    for (const t of texts) {
      let n = 0;
      while (n < l.length && n < t.length && l[n] === t[n]) n++;
      if (n > best.length) best = { line: i + 1, length: n };
    }
  });
  return best.line;
}

export function extractCoverage(ctx, resolveNonLiteral, positioningCandidates) {
  const collections = extractCollections(ctx, resolveNonLiteral);
  const headers = extractAppHeaders(ctx);
  return {
    collections: collections.items,
    unresolvedCollections: collections.unresolved,
    storedValues: extractStoredValues(ctx),
    apiRoutes: extractApiRoutes(ctx),
    routeSegments: extractRouteSegments(ctx),
    uiStrings: extractUiStrings(ctx),
    appHeaders: headers.items,
    appHeaderCallSites: headers.callSites,
    positioning: extractPositioning(ctx, positioningCandidates),
  };
}
