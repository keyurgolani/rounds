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
export const POSITIONING_SITES = [
  { path: 'README.md', line: 1, template: '# Rounds: {title}' },
  { path: 'README.md', line: 3, template: '{statement}' },
  { path: 'docs/architecture.md', line: 3, template: '{statement}' },
  { path: 'frontend/index.html', line: 17, template: '<title>Rounds: {title}</title>' },
  { path: 'frontend/src/pages/Login.tsx', line: 239, template: '<div className="eyebrow mb-2">Rounds · {title}</div>' },
  { path: 'SHOWCASE.md', line: 3, template: '{statement}' },
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
    const src = ctx.read(INTERVIEW_TYPES_PATH);
    const tokens = tokenize(src);
    const field = 'interview_rounds.round_type';
    for (let i = 0; i < tokens.length; i++) {
      const t = tokens[i];
      if (t.type === 'ident' && t.value === 'INTERVIEW_TYPES' && tokens[i + 1]?.value === ':') {
        // export const INTERVIEW_TYPES: InterviewTypeEntry[] = [ ... ]
        let open = i + 2;
        while (open < tokens.length && tokens[open].value !== '=') open++;
        open++;
        if (tokens[open]?.value !== '[') continue;
        for (let j = open + 1; j < matchClose(tokens, open); j++) {
          if (tokens[j].value !== '{') continue;
          const key = objectProperties(tokens, j).get('key');
          if (key && tokens[key.valueStart].type === 'string') items.push(item('stored-value', tokens[key.valueStart].value, INTERVIEW_TYPES_PATH, tokens[key.valueStart].line, { field }));
          j = matchClose(tokens, j);
        }
      }
      if (t.type === 'ident' && t.value === 'INTERVIEW_TYPE_ALIASES') {
        let open = i + 1;
        while (open < tokens.length && tokens[open].value !== '=') open++;
        open++;
        if (tokens[open]?.value !== '{') continue;
        for (const [name, prop] of objectProperties(tokens, open)) items.push(item('stored-value', name, INTERVIEW_TYPES_PATH, tokens[prop.keyIndex].line, { field, alias: true }));
      }
    }
  }
  return items;
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

export function extractUiStrings(ctx) {
  const found = new Map();
  if (ctx.exists(LAYOUT)) {
    const src = ctx.read(LAYOUT);
    const starts = lineStarts(src);
    // Navigation definitions: objects with a path and a label.
    for (const m of src.matchAll(/\{\s*path:\s*'([^']*)',\s*label:\s*'([^']*)'/g)) pushString(found, m[2], LAYOUT, lineAt(starts, m.index));
    // User-menu destinations: <MenuItem label="..." onClick={() => onNavigate('/x')} />.
    for (const m of src.matchAll(/<MenuItem\s+label="([^"]*)"\s+onClick=\{\(\)\s*=>\s*(?:onNavigate|go)\('([^']*)'\)\}/g)) pushString(found, m[1], LAYOUT, lineAt(starts, m.index));
    // Sidebar section headings: <div className="eyebrow ...">Text</div>.
    for (const m of src.matchAll(/<div className="eyebrow[^"]*"[^>]*>\s*([^<{}]+?)\s*<\/div>/g)) pushString(found, m[1], LAYOUT, lineAt(starts, m.index + m[0].indexOf(m[1])));
  }
  if (ctx.exists(COMMAND_REGISTRY)) {
    const src = ctx.read(COMMAND_REGISTRY);
    const starts = lineStarts(src);
    for (const m of src.matchAll(/\bid:\s*'([^']+)',\s*label:\s*'([^']+)',(?:\s*description:\s*'([^']+)',)?/g)) {
      pushString(found, m[2], COMMAND_REGISTRY, lineAt(starts, m.index + m[0].indexOf(`'${m[2]}'`)));
      if (m[3]) pushString(found, m[3], COMMAND_REGISTRY, lineAt(starts, m.index + m[0].indexOf(`'${m[3]}'`)));
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

export function extractPositioning(ctx) {
  return POSITIONING_SITES.map((site) => {
    const text = ctx.exists(site.path) ? (ctx.read(site.path).split('\n')[site.line - 1] ?? '') : '';
    return item('positioning', text.trim(), site.path, site.line, { template: site.template });
  });
}

export function extractCoverage(ctx, resolveNonLiteral) {
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
    positioning: extractPositioning(ctx),
  };
}
