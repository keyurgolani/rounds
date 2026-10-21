// Reads and checks the transformation program files (ROUNDS-01-L03, DR-0003):
// DR-0003's gates, gate artifacts, and closure; the stage and context tables
// in docs/program/cutover-policy.md; the edge table in reauthorization.md;
// the registers and the rollback template. report.mjs and the conformance
// tests use it. Node built-ins only.
//
// TODO(ROUNDS-01-L03): S2's scripts/conformance/rules/program.mjs runs
// checkProgram in the conformance job and adds the leaf-dag.json checks.

import { createContext, finding, jsonLine, sha256 } from '../conformance/lib/context.mjs';
import { validate } from '../conformance/lib/json-schema.mjs';
import { leafResolver, loadLeafIds } from '../conformance/lib/leaf-ids.mjs';

export const DR_PATH = 'docs/decisions/DR-0003-transformation-program.json';
export const PROGRAM_SCHEMA = 'docs/program/program-record.schema.json';
export const POLICY_PATH = 'docs/program/cutover-policy.md';
export const REAUTH_PATH = 'docs/program/reauthorization.md';
export const ROLLBACK_SCHEMA = 'docs/program/rollback-template.schema.json';
export const ROLLBACK_FIXTURE = 'docs/program/fixtures/rollback-synthetic.json';
export const MATRIX_PATH = 'contracts/authority/matrix.json';
export const REGISTERS = {
  nonGoals: { path: 'docs/program/non-goals.json', schema: 'docs/program/non-goals.schema.json' },
  dod: { path: 'docs/program/definition-of-done.json', schema: 'docs/program/definition-of-done.schema.json' },
  journeys: { path: 'docs/program/journeys.json', schema: 'docs/program/journeys.schema.json' },
};

export const GATE_IDS = [...Array.from({ length: 8 }, (_, i) => `C${i}`), ...Array.from({ length: 12 }, (_, i) => `U${i}`)];
export const UNIVERSAL = GATE_IDS.filter((g) => g.startsWith('U'));
// The 16 migration stages and their spec lines (spec 2677-2695).
export const STAGE_LINES = ['2677', '2678', '2679', '2680', '2681', '2682', '2683-2684', '2685', '2686', '2687-2688', '2689', '2690', '2691', '2692', '2693', '2694-2695'];
export const STAGE_RUNS = ['once', 'per transfer', 'between transfers'];
export const EDGE_CHANGES = ['add', 'drop'];
export const EDGE_KINDS = ['done', 'merged', 'closure'];
// Forced bindings (decision P6), by issue number: gate -> consumers.
export const FORCED_BINDINGS = {
  U4: [43, 130, 131, 132, 133, 134, 135, 136, 137],
  U8: [133, 134, 135],
  U9: [93, 94, 161],
};
export const CAPABILITY_PATTERN = /^ROUNDS-\d{2}[A-Z]?$/;

// What the registers hold, as their sources give it, so a dropped or edited
// entry fails here and not only through DR-0003's pins. The digests are
// SHA-256 over the canonical forms below; the approved-sources tests rebuild
// them from rounds-review (the catalog at leaf-ids.json's pin and the spec).
// A catalog or spec change updates the register and these together.
export const SOURCE_SETS = {
  dod: ['DOD-1', 'DOD-2', 'DOD-3', 'DOD-4', 'DOD-5', 'DOD-6', 'DOD-7'],
  nonGoals: { count: 7, withProduct: 6, sha256: 'a2f57c7d4cec956ea2fb862bfca28e8b6038d1d7b22b40d146ab203ed56acc15' },
  tradeoffs: { count: 38, capabilities: 36, sha256: 'cae1b64cf0f2ed7077743eee81518fe4e74fe58fd9ad7e9c7a71c64e8b39ec97' },
  journeys: { steps: [7, 6, 6, 7, 5], sha256: '5546316eb9cd9fffd8892f986d38f3e59c1300949ac1ec11427ba63268a10819' },
};
export const canonicalNonGoals = (list) => JSON.stringify((list || []).map((g) => [g.spec?.lines, g.spec?.text, g.product ? [g.product.lines, g.product.text] : null]));
export const canonicalTradeoffs = (list) => JSON.stringify((list || []).map((t) => [t.capability, t.text]));
export const canonicalJourneys = (list) => JSON.stringify((list || []).map((j) => [j.title, j.lines, (j.steps || []).map((s) => [s.lines, s.text])]));
// A PR title's leaf or stage label: [ROUNDS-00A-L01], [ROUNDS-00A-L01/S3], [ROUNDS-32-L10/SB.3].
export const TITLE_LABEL = /\[(ROUNDS-\d{2}[A-Z]?-L\d{2})(?:\/([A-Za-z0-9.]+))?\]/g;

// ------------------------------------------------------------ markdown tables

// The first pipe table after the heading whose text is `heading`. Returns
// { line, header, rows: [{ line, cells }] } or null. Cells keep backticks.
export function parseTable(text, heading) {
  const lines = text.split('\n');
  const start = lines.findIndex((l) => /^#{2,4} /.test(l) && l.replace(/^#+ /, '').trim() === heading);
  if (start < 0) return null;
  let i = start + 1;
  while (i < lines.length && !lines[i].startsWith('|')) {
    if (/^#{1,4} /.test(lines[i])) return null;
    i++;
  }
  if (i >= lines.length) return null;
  const split = (l) => l.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());
  const header = split(lines[i]);
  const rows = [];
  for (let j = i + 2; j < lines.length && lines[j].startsWith('|'); j++) rows.push({ line: j + 1, cells: split(lines[j]) });
  return { line: i + 1, header, rows };
}

// Backticked tokens in a cell.
export function cellRefs(cell) {
  return [...String(cell).matchAll(/`([^`]+)`/g)].map((m) => m[1]);
}

const unquote = (cell) => String(cell).replace(/`/g, '').trim();

export function readStages(ctx) {
  const table = parseTable(ctx.read(POLICY_PATH), 'Migration stages');
  if (!table) return null;
  return table.rows.map(({ line, cells }) => ({
    line,
    stage: Number(cells[0]),
    spec: cells[1],
    step: cells[2],
    owners: cellRefs(cells[3]),
    runs: cells[4],
    with: cellRefs(cells[5]),
    columns: cells.length,
  }));
}

export function readContexts(ctx) {
  const table = parseTable(ctx.read(POLICY_PATH), 'Context order (draft)');
  if (!table) return null;
  return table.rows.map(({ line, cells }) => ({
    line,
    order: Number(cells[0]),
    milestone: Number(cells[1]),
    context: unquote(cells[2]),
    node: unquote(cells[3]),
    runs: cells[4],
    columns: cells.length,
  }));
}

export function readEdges(ctx) {
  const table = parseTable(ctx.read(REAUTH_PATH), 'Edges');
  if (!table) return null;
  return table.rows.map(({ line, cells }) => ({
    line,
    id: cells[0],
    change: cells[1],
    dependent: unquote(cells[2]),
    prerequisite: unquote(cells[3]),
    kind: cells[4],
    reason: cells[5],
    source: cells[6],
    columns: cells.length,
  }));
}

// ------------------------------------------------------------ references

// Resolves a leaf, stage, or capability reference against leaf-ids.json.
export function refResolver(ctx) {
  const registry = loadLeafIds(ctx);
  const leaf = leafResolver(registry);
  const live = (registry?.leaves || []).filter((l) => l.status !== 'rejected');
  return (ref, { capability = false } = {}) => {
    if (capability && CAPABILITY_PATTERN.test(String(ref))) {
      const members = live.filter((l) => l.id.startsWith(`${ref}-L`)).map((l) => l.id);
      return members.length ? { ok: true, capability: true, members } : { ok: false, reason: `${ref} has no leaf in leaf-ids.json` };
    }
    return leaf(ref);
  };
}

// The leaf a matrix field names for each row: { rowId -> leaf } for rows that
// name one (n/a and blocked cells name none; pending:<leaf> names the leaf).
export function matrixProducers(matrix, from) {
  const field = String(from).split('#')[1] || '';
  const out = new Map();
  for (const row of matrix?.rows || []) {
    let value = row;
    for (const key of field.split('.')) value = value && typeof value === 'object' ? value[key] : undefined;
    if (typeof value !== 'string') continue;
    const m = /^(?:pending:)?(ROUNDS-\d{2}[A-Z]?-L\d{2})$/.exec(value);
    if (m) out.set(row.id, m[1]);
  }
  return out;
}

// Every producer ref an artifact row names, deduplicated, in first-seen order.
export function producersOf(artifact, matrix) {
  if (artifact.producer) return [artifact.producer];
  if (artifact.producerFrom) return [...new Set(matrixProducers(matrix, artifact.producerFrom).values())];
  return [];
}

// ------------------------------------------------------------ loading

// Loads every program file. Returns { dr, schema, registers, rollback,
// stages, contexts, edges, matrix } with null for anything unreadable, and
// pushes a PROGRAM_FILE_INVALID finding for each.
export function loadProgram(ctx, findings = []) {
  const json = (rel) => {
    if (!ctx.exists(rel)) { findings.push(finding('PROGRAM_FILE_INVALID', rel, 1, `${rel} is missing`)); return null; }
    try {
      return ctx.readJson(rel);
    } catch (err) {
      findings.push(finding('PROGRAM_FILE_INVALID', rel, 1, `${rel} is not valid JSON: ${err.message}`));
      return null;
    }
  };
  const text = (rel) => {
    if (!ctx.exists(rel)) { findings.push(finding('PROGRAM_FILE_INVALID', rel, 1, `${rel} is missing`)); return false; }
    return true;
  };
  const out = { dr: json(DR_PATH), schema: json(PROGRAM_SCHEMA), registers: {}, schemas: {}, matrix: json(MATRIX_PATH) };
  for (const [key, r] of Object.entries(REGISTERS)) {
    out.registers[key] = json(r.path);
    out.schemas[key] = json(r.schema);
  }
  out.rollbackSchema = json(ROLLBACK_SCHEMA);
  out.rollback = json(ROLLBACK_FIXTURE);
  const table = (rel, read, name) => {
    if (!text(rel)) return null;
    const rows = read(ctx);
    if (!rows) findings.push(finding('PROGRAM_FILE_INVALID', rel, 1, `${rel} has no "${name}" table`));
    return rows;
  };
  out.stages = table(POLICY_PATH, readStages, 'Migration stages');
  out.contexts = table(POLICY_PATH, readContexts, 'Context order (draft)');
  out.edges = table(REAUTH_PATH, readEdges, 'Edges');
  return out;
}

// ------------------------------------------------------------ checks

const pointerLine = (ctx, rel, pointer) => {
  try {
    return jsonLine(ctx.read(rel), pointer.split('/').slice(1).map((p) => (/^\d+$/.test(p) ? Number(p) : p)));
  } catch {
    return 1;
  }
};

function schemaFindings(ctx, value, schema, rel, code, findings) {
  if (!value || !schema) return;
  for (const err of validate(value, schema)) findings.push(finding(code, rel, pointerLine(ctx, rel, err.pointer), `${err.pointer || '/'} ${err.message}`));
}

// The rollback defaults (decision P5): each template field, the bound a
// deviations entry records as its default, and the test a value must pass.
export const ROLLBACK_DEFAULTS = [
  { field: 'allowedDowntime.freezeMinutes', bound: 15, ok: (v) => v < 15, want: 'under 15 minutes (spec 2062)' },
  { field: 'recoveryPointObjective.acceptedWritesLost', bound: 0, ok: (v) => v === 0, want: 'zero accepted writes lost (spec 2063)' },
  { field: 'recoveryTimeObjective.minutes', bound: 30, ok: (v) => v <= 30, want: 'at most 30 minutes (spec 2064-2065)' },
  { field: 'backupConsistency.restoreRehearsed', bound: true, ok: (v) => v === true, want: 'a rehearsed restore (spec 2066-2067)' },
];

const fieldValue = (record, dotted) => dotted.split('.').reduce((v, k) => (v && typeof v === 'object' ? v[k] : undefined), record);

// Loosened rollback defaults that no deviations entry approves. An entry
// covers a field only for the exact value it approves.
export function rollbackDefaultFindings(record) {
  const out = [];
  if (!record || typeof record !== 'object') return out;
  const deviations = new Map((Array.isArray(record.deviations) ? record.deviations : []).map((d) => [d.field, d]));
  for (const { field, bound, ok, want } of ROLLBACK_DEFAULTS) {
    const value = fieldValue(record, field);
    if (value === undefined || ok(value)) continue;
    const dev = deviations.get(field);
    if (!dev) {
      out.push({ field, message: `${field} is ${JSON.stringify(value)}; the default is ${want}, so loosening it needs a deviations entry with the owner's approval` });
    } else if (dev.value !== value) {
      out.push({ field, message: `the ${field} deviation approves ${JSON.stringify(dev.value)}, but the template says ${JSON.stringify(value)}` });
    } else if (dev.default !== bound) {
      out.push({ field, message: `the ${field} deviation records the default as ${JSON.stringify(dev.default)}; it is ${JSON.stringify(bound)}` });
    }
  }
  return out;
}

// A transfer template's node, context, and decision owner (decision P4):
// the context must sit in the node's list in the context order.
export function transferTemplateFindings(record, contexts, resolve) {
  const out = [];
  if (!record || typeof record !== 'object') return out;
  for (const [what, value] of [['transfer', record.transfer], ['decisionOwner.leaf', record.decisionOwner?.leaf]]) {
    if (value === undefined) continue;
    const r = resolve(value);
    if (!r.ok) out.push({ code: 'PROGRAM_UNRESOLVED_REF', field: what.split('.')[0], message: `${what}: ${r.reason}` });
  }
  if (contexts && record.context !== undefined) {
    const row = contexts.find((c) => c.context === record.context);
    if (!row) out.push({ code: 'PROGRAM_ROLLBACK_CONTEXT', field: 'context', message: `context ${record.context} is not in the context order of ${POLICY_PATH}` });
    else if (row.node !== record.transfer) out.push({ code: 'PROGRAM_ROLLBACK_CONTEXT', field: 'context', message: `context ${record.context} belongs to ${row.node}, not ${record.transfer}` });
  }
  return out;
}

export function checkProgram(ctx = createContext(process.cwd(), { base: 'none' })) {
  const findings = [];
  const p = loadProgram(ctx, findings);
  const resolve = refResolver(ctx);
  const ref = (value, rel, line, what, opts) => {
    const r = resolve(value, opts);
    if (!r.ok) findings.push(finding('PROGRAM_UNRESOLVED_REF', rel, line, `${what}: ${r.reason}`));
    return r.ok;
  };
  const issueLeaf = new Map((loadLeafIds(ctx)?.leaves || []).filter((l) => l.issue).map((l) => [l.issue, l.id]));

  // DR-0003's program fields.
  if (p.dr && p.schema) {
    schemaFindings(ctx, p.dr, p.schema, DR_PATH, 'PROGRAM_FILE_INVALID', findings);
    const at = (parts) => jsonLine(ctx.read(DR_PATH), parts);
    const gates = Array.isArray(p.dr.gates) ? p.dr.gates : [];
    const ids = gates.map((g) => g.id);
    if (JSON.stringify(ids) !== JSON.stringify(GATE_IDS)) {
      findings.push(finding('PROGRAM_GATE_UNBOUND', DR_PATH, at(['gates']), `gates must list ${GATE_IDS.join(', ')} once each, in order; found ${ids.join(', ') || 'none'}`));
    }
    const artifacts = Array.isArray(p.dr.gateArtifacts) ? p.dr.gateArtifacts : [];
    const seen = new Set();
    artifacts.forEach((a, i) => {
      const line = at(['gateArtifacts', i]);
      if (seen.has(a.id)) findings.push(finding('PROGRAM_DUPLICATE', DR_PATH, line, `artifact ${a.id} is listed twice`));
      seen.add(a.id);
      if (typeof a.id === 'string' && a.id.split('.')[0] !== a.gate) findings.push(finding('PROGRAM_FILE_INVALID', DR_PATH, line, `artifact ${a.id} sits under gate ${a.gate}; its id must start with ${a.gate}.`));
      const named = (a.producer ? 1 : 0) + (a.producerFrom ? 1 : 0);
      if (named !== 1) {
        findings.push(finding('PROGRAM_PRODUCER', DR_PATH, line, `artifact ${a.id} must name exactly one producer (producer or producerFrom); it names ${named}`));
        return;
      }
      if (a.producer) ref(a.producer, DR_PATH, line, `artifact ${a.id} producer`);
      else {
        const producers = producersOf(a, p.matrix);
        if (!producers.length) findings.push(finding('PROGRAM_PRODUCER', DR_PATH, line, `artifact ${a.id} producerFrom ${a.producerFrom} names no leaf in ${MATRIX_PATH}`));
        for (const leaf of producers) ref(leaf, DR_PATH, line, `artifact ${a.id} producer from ${a.producerFrom}`);
      }
      if (a.designation !== undefined && a.id !== 'U11.reference-leaf') findings.push(finding('PROGRAM_FILE_INVALID', DR_PATH, line, `only U11.reference-leaf takes a designation, not ${a.id}`));
      for (const leaf of a.requiredFor || []) ref(leaf, DR_PATH, line, `artifact ${a.id} requiredFor`);
      for (const rel of a.paths || []) {
        if (!ctx.exists(rel)) findings.push(finding('PROGRAM_PATH_MISSING', DR_PATH, line, `artifact ${a.id} lives at ${rel}, which does not exist`));
      }
    });
    for (const gate of GATE_IDS) {
      if (!artifacts.some((a) => a.gate === gate)) findings.push(finding('PROGRAM_GATE_UNBOUND', DR_PATH, at(['gateArtifacts']), `gate ${gate} has no artifact`));
    }
    for (const [gate, issues] of Object.entries(FORCED_BINDINGS)) {
      const want = issues.map((n) => issueLeaf.get(n)).filter(Boolean);
      for (const a of artifacts.filter((x) => x.gate === gate)) {
        const missing = want.filter((l) => !(a.requiredFor || []).includes(l));
        if (missing.length) findings.push(finding('PROGRAM_REQUIRED_FOR', DR_PATH, at(['gateArtifacts', artifacts.indexOf(a)]), `artifact ${a.id} must be requiredFor ${missing.join(', ')} (decision P6)`));
      }
    }
    const reference = artifacts.find((a) => a.id === 'U11.reference-leaf');
    if (!reference) findings.push(finding('PROGRAM_GATE_UNBOUND', DR_PATH, at(['gateArtifacts']), 'U11 needs a U11.reference-leaf row for the reference leaf issue'));
    else if (!reference.designation) findings.push(finding('PROGRAM_FILE_INVALID', DR_PATH, at(['gateArtifacts', artifacts.indexOf(reference)]), 'U11.reference-leaf needs a designation (default or owner-designated)'));
    for (const leaf of p.dr.closure?.leaves || []) ref(leaf, DR_PATH, at(['closure']), 'closure leaf');
    const ng = p.registers.nonGoals?.referenceLeaf;
    if (reference && ng && (ng.leaf !== reference.producer || ng.designation !== reference.designation)) {
      findings.push(finding('PROGRAM_REGISTER', REGISTERS.nonGoals.path, pointerLine(ctx, REGISTERS.nonGoals.path, '/referenceLeaf'), `referenceLeaf (${ng.leaf}, ${ng.designation}) disagrees with DR-0003's U11.reference-leaf row (${reference.producer}, ${reference.designation})`));
    }
  }

  // Registers.
  for (const [key, r] of Object.entries(REGISTERS)) schemaFindings(ctx, p.registers[key], p.schemas[key], r.path, 'PROGRAM_FILE_INVALID', findings);
  const ng = p.registers.nonGoals;
  if (ng) {
    const rel = REGISTERS.nonGoals.path;
    (ng.product || []).forEach((g, i) => {
      if (g.id !== `NG-${i + 1}`) findings.push(finding('PROGRAM_REGISTER', rel, pointerLine(ctx, rel, `/product/${i}`), `product non-goal ${i + 1} is ${g.id}; ids run NG-1 upward`));
    });
    const product = ng.product || [];
    const want = SOURCE_SETS.nonGoals;
    const withProduct = product.filter((g) => g.product).length;
    if (product.length !== want.count || withProduct !== want.withProduct || sha256(canonicalNonGoals(product)) !== want.sha256) {
      findings.push(finding('PROGRAM_REGISTER', rel, pointerLine(ctx, rel, '/product'), `product non-goals (${product.length}, ${withProduct} with a PRODUCT.md line) differ from spec 177-184 and PRODUCT.md 211-217 (${want.count} and ${want.withProduct}, sha256 ${want.sha256.slice(0, 12)}...); quote each one verbatim`));
    }
    const tradeoffs = ng.tradeoffs || [];
    const capabilities = new Set(tradeoffs.map((t) => t.capability)).size;
    const wantTradeoffs = SOURCE_SETS.tradeoffs;
    if (tradeoffs.length !== wantTradeoffs.count || capabilities !== wantTradeoffs.capabilities || sha256(canonicalTradeoffs(tradeoffs)) !== wantTradeoffs.sha256) {
      findings.push(finding('PROGRAM_REGISTER', rel, pointerLine(ctx, rel, '/tradeoffs'), `tradeoffs (${tradeoffs.length} across ${capabilities} capabilities) differ from the catalog's (${wantTradeoffs.count} across ${wantTradeoffs.capabilities}, sha256 ${wantTradeoffs.sha256.slice(0, 12)}...); copy each catalog tradeoff verbatim`));
    }
    tradeoffs.forEach((t, i) => ref(t.capability, rel, pointerLine(ctx, rel, `/tradeoffs/${i}`), 'tradeoff capability', { capability: true }));
    if (ng.referenceLeaf) {
      const r = resolve(ng.referenceLeaf.leaf);
      if (!r.ok) findings.push(finding('PROGRAM_UNRESOLVED_REF', rel, pointerLine(ctx, rel, '/referenceLeaf'), `referenceLeaf: ${r.reason}`));
      else if (r.issue !== ng.referenceLeaf.issue) findings.push(finding('PROGRAM_REGISTER', rel, pointerLine(ctx, rel, '/referenceLeaf'), `referenceLeaf ${ng.referenceLeaf.leaf} is issue #${r.issue}, not #${ng.referenceLeaf.issue}`));
    }
  }
  const dod = p.registers.dod;
  if (dod) {
    const rel = REGISTERS.dod.path;
    (dod.items || []).forEach((d, i) => {
      if (d.id !== `DOD-${i + 1}`) findings.push(finding('PROGRAM_REGISTER', rel, pointerLine(ctx, rel, `/items/${i}`), `definition-of-done item ${i + 1} is ${d.id}; ids run DOD-1 upward with none dropped`));
      for (const c of d.checkedBy || []) ref(c.leaf, rel, pointerLine(ctx, rel, `/items/${i}`), `${d.id} checkedBy`);
    });
    const ids = new Set((dod.items || []).map((d) => d.id));
    const missing = SOURCE_SETS.dod.filter((id) => !ids.has(id));
    if (missing.length) {
      findings.push(finding('PROGRAM_REGISTER', rel, pointerLine(ctx, rel, '/items'), `${missing.join(', ')} ${missing.length === 1 ? 'is' : 'are'} missing; dropping a definition-of-done item needs the owner's approval in a superseding DR-0003 revision`));
    }
  }
  const jr = p.registers.journeys;
  if (jr) {
    const rel = REGISTERS.journeys.path;
    const counts = (jr.journeys || []).map((j) => (j.steps || []).length);
    const want = SOURCE_SETS.journeys;
    if (JSON.stringify(counts) !== JSON.stringify(want.steps) || sha256(canonicalJourneys(jr.journeys)) !== want.sha256) {
      findings.push(finding('PROGRAM_REGISTER', rel, pointerLine(ctx, rel, '/journeys'), `journey steps (${counts.join(', ')}) differ from spec 1019-1071 (${want.steps.join(', ')}, sha256 ${want.sha256.slice(0, 12)}...); map every step, quoted verbatim`));
    }
    (jr.journeys || []).forEach((j, ji) => {
      const line = pointerLine(ctx, rel, `/journeys/${ji}`);
      const steps = j.steps || [];
      steps.forEach((s, si) => {
        const sline = pointerLine(ctx, rel, `/journeys/${ji}/steps/${si}`);
        if (s.id !== `${j.id}.${si + 1}`) findings.push(finding('PROGRAM_JOURNEY_UNMAPPED', rel, sline, `step ${si + 1} of ${j.id} is ${s.id}; steps run ${j.id}.1 upward`));
        if (s.leaf) ref(s.leaf, rel, sline, `${s.id} leaf`);
        for (const w of s.with || []) ref(w, rel, sline, `${s.id} with`);
        if (s.leaf && (s.with || []).includes(s.leaf)) findings.push(finding('PROGRAM_JOURNEY_UNMAPPED', rel, sline, `${s.id} lists its own leaf ${s.leaf} under with`));
      });
      const top = steps.length ? Math.max(...steps.map((s) => s.milestone)) : null;
      if (top !== null && j.milestone !== top) findings.push(finding('PROGRAM_JOURNEY_UNMAPPED', rel, line, `${j.id} milestone is ${j.milestone}; its latest step is in ${top}`));
      if (j.completingLeaf && !steps.some((s) => s.leaf === j.completingLeaf && s.milestone === top)) {
        findings.push(finding('PROGRAM_JOURNEY_UNMAPPED', rel, line, `${j.id} completing leaf ${j.completingLeaf} is not a step leaf in its latest milestone`));
      }
    });
    const fr = jr.firstRun;
    if (fr) {
      const line = pointerLine(ctx, rel, '/firstRun');
      (fr.steps || []).forEach((s, i) => {
        if (s.id !== `FR.${i + 1}`) findings.push(finding('PROGRAM_JOURNEY_UNMAPPED', rel, line, `first-run step ${i + 1} is ${s.id}`));
        ref(s.leaf, rel, line, `${s.id} leaf`);
      });
      const choosers = (fr.steps || []).filter((s) => s.leaf === fr.chooser);
      if (choosers.length !== 1) findings.push(finding('PROGRAM_JOURNEY_UNMAPPED', rel, line, `the first run must reach the one chooser ${fr.chooser} exactly once; it does ${choosers.length} times`));
    }
  }

  // Rollback template and fixture.
  if (p.rollback && p.rollbackSchema) {
    schemaFindings(ctx, p.rollback, p.rollbackSchema, ROLLBACK_FIXTURE, 'PROGRAM_ROLLBACK_INVALID', findings);
    for (const d of rollbackDefaultFindings(p.rollback)) findings.push(finding('PROGRAM_ROLLBACK_DEFAULT', ROLLBACK_FIXTURE, pointerLine(ctx, ROLLBACK_FIXTURE, `/${d.field.split('.')[0]}`), d.message));
    for (const d of transferTemplateFindings(p.rollback, p.contexts, resolve)) findings.push(finding(d.code, ROLLBACK_FIXTURE, pointerLine(ctx, ROLLBACK_FIXTURE, `/${d.field}`), `fixture ${d.message}`));
  }

  // Migration stages.
  if (p.stages) {
    const numbers = p.stages.map((s) => s.stage);
    if (JSON.stringify(numbers) !== JSON.stringify(STAGE_LINES.map((_, i) => i + 1))) {
      findings.push(finding('PROGRAM_STAGE_UNOWNED', POLICY_PATH, p.stages[0]?.line || 1, `the stage table must list stages 1 to 16 in order; found ${numbers.join(', ') || 'none'}`));
    }
    for (const s of p.stages) {
      if (s.columns !== 6) findings.push(finding('PROGRAM_FILE_INVALID', POLICY_PATH, s.line, `stage row has ${s.columns} columns, not 6`));
      if (STAGE_LINES[s.stage - 1] && s.spec !== STAGE_LINES[s.stage - 1]) findings.push(finding('PROGRAM_STAGE_UNOWNED', POLICY_PATH, s.line, `stage ${s.stage} is spec ${STAGE_LINES[s.stage - 1]}, not ${s.spec}`));
      if (s.owners.length !== 1) findings.push(finding('PROGRAM_STAGE_UNOWNED', POLICY_PATH, s.line, `stage ${s.stage} must name exactly one owner leaf; it names ${s.owners.length}`));
      for (const o of s.owners) ref(o, POLICY_PATH, s.line, `stage ${s.stage} owner`);
      for (const w of s.with) ref(w, POLICY_PATH, s.line, `stage ${s.stage} with`);
      if (!STAGE_RUNS.includes(s.runs)) findings.push(finding('PROGRAM_FILE_INVALID', POLICY_PATH, s.line, `stage ${s.stage} runs "${s.runs}"; use ${STAGE_RUNS.join(', ')}`));
    }
  }

  // Context order.
  if (p.contexts) {
    const contexts = new Set();
    const closedNodes = new Set();
    let prev = null;
    p.contexts.forEach((c, i) => {
      if (c.columns !== 5) findings.push(finding('PROGRAM_FILE_INVALID', POLICY_PATH, c.line, `context row has ${c.columns} columns, not 5`));
      if (c.order !== i + 1) findings.push(finding('PROGRAM_CONTEXT_ORDER', POLICY_PATH, c.line, `context ${c.context} is order ${c.order}; orders run 1 upward`));
      if (!/^[a-z][a-z0-9]*(-[a-z0-9]+)*$/.test(c.context)) findings.push(finding('PROGRAM_FILE_INVALID', POLICY_PATH, c.line, `context "${c.context}" is not a lowercase id`));
      if (contexts.has(c.context)) findings.push(finding('PROGRAM_CONTEXT_ORDER', POLICY_PATH, c.line, `context ${c.context} is listed twice; a context sits in one transfer node`));
      contexts.add(c.context);
      if (!(Number.isInteger(c.milestone) && c.milestone >= 0 && c.milestone <= 7)) findings.push(finding('PROGRAM_CONTEXT_ORDER', POLICY_PATH, c.line, `context ${c.context} milestone ${c.milestone} is not 0 to 7`));
      if (prev && c.milestone < prev.milestone) findings.push(finding('PROGRAM_CONTEXT_ORDER', POLICY_PATH, c.line, `context ${c.context} (milestone ${c.milestone}) follows ${prev.context} (milestone ${prev.milestone})`));
      ref(c.node, POLICY_PATH, c.line, `context ${c.context} transfer node`);
      if (prev && prev.node !== c.node) closedNodes.add(prev.node);
      if (closedNodes.has(c.node)) findings.push(finding('PROGRAM_CONTEXT_ORDER', POLICY_PATH, c.line, `${c.node}'s contexts must be listed together`));
      prev = c;
    });
  }

  // Re-authorization edges.
  if (p.edges) {
    const ids = new Set();
    p.edges.forEach((e, i) => {
      if (e.columns !== 7) findings.push(finding('PROGRAM_FILE_INVALID', REAUTH_PATH, e.line, `edge row has ${e.columns} columns, not 7`));
      if (e.id !== `E${i + 1}`) findings.push(finding('PROGRAM_EDGE_INVALID', REAUTH_PATH, e.line, `edge ${i + 1} is ${e.id}; edges run E1 upward`));
      if (ids.has(`${e.change} ${e.dependent} ${e.prerequisite}`)) findings.push(finding('PROGRAM_EDGE_INVALID', REAUTH_PATH, e.line, `${e.id} repeats an earlier edge`));
      ids.add(`${e.change} ${e.dependent} ${e.prerequisite}`);
      if (!EDGE_CHANGES.includes(e.change)) findings.push(finding('PROGRAM_EDGE_INVALID', REAUTH_PATH, e.line, `${e.id} change "${e.change}" is not ${EDGE_CHANGES.join(' or ')}`));
      if (!EDGE_KINDS.includes(e.kind)) findings.push(finding('PROGRAM_EDGE_INVALID', REAUTH_PATH, e.line, `${e.id} kind "${e.kind}" is not ${EDGE_KINDS.join(', ')}`));
      if (!e.reason || !e.source) findings.push(finding('PROGRAM_EDGE_INVALID', REAUTH_PATH, e.line, `${e.id} needs a reason and a source`));
      ref(e.dependent, REAUTH_PATH, e.line, `${e.id} dependent`);
      ref(e.prerequisite, REAUTH_PATH, e.line, `${e.id} prerequisite`, { capability: true });
      if (e.dependent === e.prerequisite) findings.push(finding('PROGRAM_EDGE_INVALID', REAUTH_PATH, e.line, `${e.id} depends on itself`));
    });
  }
  return findings;
}

// ------------------------------------------------------------ PR state

// The leaf or stage label of a PR title (the last bracketed label), or null.
export function titleLabel(title) {
  const matches = [...String(title || '').matchAll(TITLE_LABEL)];
  if (!matches.length) return null;
  const m = matches[matches.length - 1];
  return { leaf: m[1], stage: m[2] || null, ref: m[2] ? `${m[1]}/${m[2]}` : m[1] };
}

// GitHub's closing keywords, as an integration-branch squash message uses them.
const CLOSES = /\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)\b/gi;

// Builds { merged, complete, done } from GitHub data shaped like `gh pr list
// --json number,title,state`, `gh issue list --json number,state,stateReason`,
// and the integration branch's commit messages (strings or { message }).
// merged holds the leaf and stage refs of merged PRs. complete holds leaves
// whose finishing PR merged: the orchestrator writes "Closes #N" only in the
// squash message of the PR that finishes leaf #N, and the issue closes when
// that commit reaches main. done holds leaves whose issue closed as completed.
// An open PR and a not_planned close count for nothing. With options.base, a
// PR whose baseRefName names another branch counts for nothing either.
export function stateFrom({ pulls = [], issues = [], commits = [] } = {}, registry, { base = null } = {}) {
  const byIssue = new Map((registry?.leaves || []).filter((l) => l.issue).map((l) => [l.issue, l.id]));
  const merged = new Set();
  for (const pr of pulls) {
    if (String(pr.state || '').toUpperCase() !== 'MERGED') continue;
    if (base && pr.baseRefName && pr.baseRefName !== base) continue;
    const label = titleLabel(pr.title);
    if (label) merged.add(label.ref);
  }
  const complete = new Set();
  for (const c of commits) {
    const message = typeof c === 'string' ? c : c?.message || c?.commit?.message || '';
    for (const m of message.matchAll(CLOSES)) {
      const leaf = byIssue.get(Number(m[1]));
      if (leaf) complete.add(leaf);
    }
  }
  const done = new Set();
  for (const issue of issues) {
    if (String(issue.state || '').toUpperCase() !== 'CLOSED' || String(issue.stateReason || '').toUpperCase() !== 'COMPLETED') continue;
    const leaf = byIssue.get(issue.number);
    if (leaf) done.add(leaf);
  }
  return { merged, complete, done };
}

// A stage ref is merged when its PR merged; a leaf ref when its [LEAF-ID] PR
// merged. A complete or done leaf counts as merged, stages included. Until
// S2's DAG lists each leaf's stages, a staged leaf named whole counts only
// once its finishing PR merged.
export function isMerged(ref, state, resolve) {
  const [leaf] = String(ref).split('/');
  if (state.done.has(leaf) || state.complete?.has(leaf) || state.merged.has(ref)) return true;
  if (resolve && CAPABILITY_PATTERN.test(String(ref))) {
    const r = resolve(ref, { capability: true });
    return r.ok && r.members.every((m) => isMerged(m, state));
  }
  return false;
}

// ROUNDS-01 closure (decision P7) and the containment gates, from DR-0003.
export function computeClosure(program, state, resolve) {
  const { dr, matrix } = program;
  const leaves = (dr?.closure?.leaves || []).map((ref) => ({ ref, met: isMerged(ref, state, resolve) }));
  const closureGates = new Set(dr?.closure?.gates || UNIVERSAL);
  const rows = (dr?.gateArtifacts || []).map((a) => {
    const producers = producersOf(a, matrix).map((ref) => ({ ref, met: isMerged(ref, state, resolve) }));
    const designated = a.id !== 'U11.reference-leaf' || ['default', 'owner-designated'].includes(a.designation);
    return { id: a.id, gate: a.gate, perRow: Boolean(a.producerFrom), designation: a.designation || null, producers, met: producers.length > 0 && designated && producers.every((x) => x.met) };
  });
  const artifacts = rows.filter((r) => closureGates.has(r.gate));
  const containment = rows.filter((r) => !closureGates.has(r.gate));
  const met = leaves.filter((l) => l.met).length + artifacts.filter((a) => a.met).length;
  const total = leaves.length + artifacts.length;
  return { capability: dr?.closure?.capability || 'ROUNDS-01', closed: total > 0 && met === total, met, total, leaves, artifacts, containment };
}

// A leaf is done once its issue closed as completed; a stage is done when its
// PR merges (decision P13); a capability once every leaf in it is done.
export function isDone(ref, state, resolve) {
  const value = String(ref);
  if (resolve && CAPABILITY_PATTERN.test(value)) {
    const r = resolve(value, { capability: true });
    return r.ok && r.members.every((m) => isDone(m, state));
  }
  const [leaf, stage] = value.split('/');
  return state.done.has(leaf) || (Boolean(stage) && state.merged.has(value));
}

// An edge's prerequisite state (done, merged, or open) and whether it meets
// the edge's kind: done needs done; merged and closure need merged (closure
// gates only the dependent's closing PR, decision P13).
export function edgeStatus(edge, state, resolve) {
  const done = isDone(edge.prerequisite, state, resolve);
  const merged = done || isMerged(edge.prerequisite, state, resolve);
  return { state: done ? 'done' : merged ? 'merged' : 'open', met: edge.kind === 'done' ? done : merged };
}

// The edge table with each prerequisite's state.
export function pendingEdges(program, state, resolve) {
  return (program.edges || []).map((e) => {
    const s = edgeStatus(e, state, resolve);
    return { ...e, prerequisiteState: s.state, prerequisiteMet: s.met };
  });
}
