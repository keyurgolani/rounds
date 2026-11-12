// Pure evaluators for the privacy policy (ROUNDS-14-L01, DR-0005). They read
// the policy files beside this module, which
// `node scripts/conformance/run.mjs --write` copies from contracts/privacy/
// (TODO(ROUNDS-34-L08): the shared contracts package takes the copy over).
// backend/app/privacy/evaluator.py answers the same shared vectors the same
// way: these are the same functions, named in camelCase.
//
// Every answer is { decision: 'deny', code, rule } or
// { decision: 'allow', obligations, versions }. Nothing here reads the
// network, the clock, or storage, and nothing enforces: ROUNDS-14-L04 renders
// consent from these answers, and each sink owner calls them at its sink.

import policyJson from './policy.json';
import purposesJson from './purposes.json';
import fieldMapJson from './field-map.json';
import secretPatternsJson from './secret-patterns.json';

export type Json = string | number | boolean | null | Json[] | { [key: string]: Json };
type Ctx = Record<string, unknown>;
export interface Deny { decision: 'deny'; code: string; rule: string }
export interface Allow { decision: 'allow'; obligations: string[]; versions: Record<string, string> }
export type Decision = Deny | Allow;

export interface Case { when: Record<string, Json>; obligations: string[] }
export interface Rule {
  decision: 'deny' | 'allow' | 'allow-if' | 'allow-with-consent';
  code?: string; obligations?: string[]; cases?: Case[]; otherwise?: string; consent?: string;
}
export interface Entry { id: string; class?: string; visibility?: string; kind: string; row?: string; pathsFrom?: string }
export interface Input { field: string; omit?: boolean }
export interface Purpose {
  id: string; status: string; consent?: string; inputs: Input[];
  toolAuthority?: Json; streaming?: boolean; batchMax?: number;
}
export interface Registry { purposes: Purpose[] }
interface Override { source?: string; sink?: string; class?: string; visibility?: string; rule: Rule }
interface Retention { default: Json; choices?: Json[]; range?: [number, number] }
interface LifecycleRow {
  id: string; retention?: Retention; sameAs?: string; purgeWithinHours?: number; warningDays?: number;
  tombstoneDays?: number; digestDays?: number; renewDays?: Record<string, number>; neverClasses?: string[];
  neverFor?: string[]; maxDaysByClass?: Record<string, number>;
}
interface Locations {
  classes: { id: string }[];
  never: { loopback: string[]; linkLocal: string[]; unspecified: string[]; metadata: string[]; serviceNames: string[]; serviceSuffixes: string[] };
  nonPublic: string[];
  privateNetworks: string[];
}
interface Policy {
  versions: { id: string; current: number }[];
  sinks: { id: string; families: string[] }[];
  matrix: { cells: { id: string; class: string; sink: string; rule: Rule }[] };
  visibilityRules: { id: string; visibility: string; sink: string; rule: Rule }[];
  lifecycle: { rows: LifecycleRow[]; decided: LifecycleRow[] };
  locations: Locations;
}
interface Sample { pattern: string; before: string; parts: string[]; after: string }

export const POLICY = policyJson as unknown as Policy;
export const PURPOSES = purposesJson as unknown as Registry;
export const FIELD_MAP = fieldMapJson as unknown as { entries: Entry[] };
export const SECRET_PATTERNS = secretPatternsJson as unknown as {
  patterns: { id: string; regex: string }[]; fixtures: Sample[]; nearMisses: Sample[];
};

export const VERSIONS: Record<string, string> = Object.fromEntries(POLICY.versions.map((v) => [v.id, `${v.id}@${v.current}`]));
const SINKS = new Map(POLICY.sinks.map((s) => [s.id, s]));
const CELLS = new Map(POLICY.matrix.cells.map((c) => [`${c.class}|${c.sink}`, c]));
const VIS_RULES = new Map(POLICY.visibilityRules.map((r) => [`${r.visibility}|${r.sink}`, r]));
const ENTRIES = new Map(FIELD_MAP.entries.map((e) => [e.id, e]));
const LIFECYCLE = new Map([...POLICY.lifecycle.rows, ...POLICY.lifecycle.decided].map((r) => [r.id, r]));
const LOC = POLICY.locations;
const SYSTEM_FIELDS = ['id', 'created', 'updated'];
const PATTERNS = SECRET_PATTERNS.patterns.map((p) => ({ id: p.id, re: new RegExp(p.regex, 'g') }));

export function deny(code: string, rule: string): Deny {
  return { decision: 'deny', code, rule };
}

export function allow(obligations: Iterable<string>, versions: string[] = ['privacy', 'consent', 'redaction', 'retention']): Allow {
  return {
    decision: 'allow',
    obligations: [...new Set(obligations)].sort(),
    versions: Object.fromEntries(versions.map((k) => [k, VERSIONS[k]])),
  };
}

// ---------------------------------------------------------------- field ids

function split(id: string): [string, string | null] {
  const i = id.indexOf('#');
  return i === -1 ? [id, null] : [id.slice(0, i), id.slice(i + 1)];
}

function segments(pointer: string | null): string[] {
  if (!pointer) return [];
  return pointer.split('/').slice(1).map((s) => s.replace(/~1/g, '/').replace(/~0/g, '~'));
}

/** A pattern covers `segs` when it is a prefix of them, `*` taking any one segment. */
function pointerMatch(pattern: string[], segs: string[]): boolean {
  return pattern.length <= segs.length && pattern.every((p, i) => p === '*' || p === segs[i]);
}

const familyRegexes = new Map<string, RegExp>();

function familyCovers(wide: string, narrow: string): boolean {
  let re = familyRegexes.get(wide);
  if (!re) {
    re = new RegExp(`^${wide.split('*').map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('[\\s\\S]*')}$`);
    familyRegexes.set(wide, re);
  }
  return re.test(narrow);
}

function columns(base: string): string[] {
  const alias = ENTRIES.get(base)?.pathsFrom;
  return alias ? [base, alias] : [base];
}

/** The field-map entry that classifies `fieldId`, or null. A JSON pointer
 * takes its deepest covering entry (fewer wildcards first on a tie), then
 * the column's own entry; `pathsFrom` reads another column's paths; a
 * store's id, created, and updated take the store entry; a storage key
 * takes the family that covers it. */
export function resolveField(fieldId: string): Entry | null {
  if (typeof fieldId !== 'string' || !fieldId) return null;
  const exact = ENTRIES.get(fieldId);
  if (exact) return exact;
  if (fieldId.startsWith('storage:')) {
    const key = fieldId.slice('storage:'.length);
    const hits = FIELD_MAP.entries.filter((e) => e.id.startsWith('storage:') && familyCovers(e.id.slice('storage:'.length), key));
    hits.sort((a, b) => (a.id.split('*').length - b.id.split('*').length) || (b.id.length - a.id.length));
    return hits[0] ?? null;
  }
  const [base, pointer] = split(fieldId);
  if (pointer === null) {
    if (base.startsWith('pb:') && base.includes('.')) {
      const dot = base.indexOf('.');
      if (SYSTEM_FIELDS.includes(base.slice(dot + 1))) return ENTRIES.get(base.slice(0, dot)) ?? null;
    }
    return null;
  }
  const segs = segments(pointer);
  for (const column of columns(base)) {
    let best: { rank: [number, number]; entry: Entry } | null = null;
    for (const e of FIELD_MAP.entries) {
      const [b, p] = split(e.id);
      if (b !== column || p === null) continue;
      const pattern = segments(p);
      if (!pointerMatch(pattern, segs)) continue;
      const rank: [number, number] = [pattern.length, -pattern.filter((x) => x === '*').length];
      if (!best || rank[0] > best.rank[0] || (rank[0] === best.rank[0] && rank[1] > best.rank[1])) best = { rank, entry: e };
    }
    if (best) return best.entry;
  }
  return ENTRIES.get(base) ?? null;
}

function family(entry: Entry): ['class' | 'visibility', string] {
  return entry.class !== undefined ? ['class', entry.class] : ['visibility', entry.visibility as string];
}

// ---------------------------------------------------------------- sink rules

function baseRule(entry: Entry, sink: string): [Rule, string] | null {
  const [fam, value] = family(entry);
  if (!SINKS.get(sink)?.families.includes(fam)) return null;
  const cell = fam === 'class' ? CELLS.get(`${value}|${sink}`) : VIS_RULES.get(`${value}|${sink}`);
  if (!cell) return null;
  return [cell.rule, `${fam === 'class' ? 'matrix.' : 'visibility.'}${cell.id}`];
}

const covers = (wide: string[] = [], narrow: string[] = []) => narrow.every((x) => wide.includes(x));
const caseTighter = (c: Case, base: Case) =>
  Object.entries(base.when).every(([k, v]) => c.when[k] === v) && covers(c.obligations, base.obligations);

/** True when `override` allows no more than `base`: a deny always is; an
 * allow keeps every obligation; a conditional allow keeps every condition
 * and obligation of some base case; a consent allow keeps the same unit
 * and obligations. */
export function tighterOrEqual(override: Rule, base: Rule): boolean {
  const o = override.decision;
  const b = base.decision;
  if (o === 'deny') return true;
  if (b === 'deny') return false;
  if (o === 'allow') return b === 'allow' && covers(override.obligations, base.obligations);
  if (o === 'allow-if') {
    if (b === 'allow') return (override.cases ?? []).every((c) => covers(c.obligations, base.obligations));
    if (b === 'allow-if') return (override.cases ?? []).every((c) => (base.cases ?? []).some((bc) => caseTighter(c, bc)));
    return false;
  }
  if (o === 'allow-with-consent') {
    return b === 'allow-with-consent' && override.consent === base.consent && covers(override.obligations, base.obligations);
  }
  return false;
}

function withOverrides(entry: Entry, sink: string, rule: Rule, ruleId: string, overrides: Override[]): [Rule, string, Deny | null] {
  const [fam, value] = family(entry);
  for (const o of overrides) {
    if (o.sink !== sink || o[fam] !== value) continue;
    const id = `override.${o.source ?? 'unknown'}`;
    if (!tighterOrEqual(o.rule, rule)) return [rule, ruleId, deny('OVERRIDE_RELAXES', id)];
    rule = o.rule;
    ruleId = id;
  }
  return [rule, ruleId, null];
}

export interface Consent { unit?: string; preview?: boolean; fields?: string[]; purpose?: string; batch?: number; added?: string[] }

function consentOk(unit: string | undefined, consent: Consent, fieldId: string, purpose: unknown): boolean {
  if (consent.unit !== 'per-request' || consent.preview !== true) return false;
  if (unit === 'field-level') return (consent.fields ?? []).includes(fieldId);
  if (unit === 'purpose-specific') return purpose !== undefined && purpose !== null && consent.purpose === purpose;
  return unit === 'per-request';
}

function apply(rule: Rule, ruleId: string, entry: Entry, fieldId: string, context: Ctx): Decision {
  if (rule.decision === 'deny') return deny(rule.code as string, ruleId);
  if (rule.decision === 'allow') return allow(rule.obligations ?? []);
  if (rule.decision === 'allow-if') {
    for (const c of rule.cases ?? []) {
      if (Object.entries(c.when).every(([k, v]) => (k === 'kind' ? entry.kind : context[k]) === v)) return allow(c.obligations);
    }
    return deny(rule.otherwise as string, ruleId);
  }
  if (rule.decision === 'allow-with-consent') {
    const consent = (context.consent || {}) as Consent;
    if (consent.unit === 'legacy-implicit') {
      if (context.purposeStatus !== 'legacy') return deny('CONSENT_LEGACY_ONLY', 'consent.legacy-implicit');
      const kept = (rule.obligations ?? []).filter((o) => !o.startsWith('consent:') && !o.startsWith('preview:'));
      return allow([...kept, 'consent:legacy-implicit']);
    }
    if (consentOk(rule.consent, consent, fieldId, context.purpose)) return allow(rule.obligations ?? []);
    return deny(rule.otherwise as string, ruleId);
  }
  return deny('SINK_WITHOUT_RULE', ruleId);
}

/** Whether `fieldId` may reach `sink`, and on what terms. */
export function evaluateSink(fieldId: string, sink: string, context?: Ctx | null): Decision {
  const ctx = context || {};
  if (!SINKS.has(sink)) return deny('SINK_WITHOUT_RULE', 'sinks');
  const entry = resolveField(fieldId);
  if (!entry) return deny('FIELD_UNCLASSIFIED', 'field-map');
  const base = baseRule(entry, sink);
  if (!base) return deny('SINK_WITHOUT_RULE', `sinks.${sink}`);
  const [rule, ruleId, refused] = withOverrides(entry, sink, base[0], base[1], (ctx.overrides || []) as Override[]);
  if (refused) return refused;
  return apply(rule, ruleId, entry, fieldId, ctx);
}

// ---------------------------------------------------------------- locations

interface Addr { v: 4 | 6; addr: bigint }
export interface Net extends Addr { prefix: number }
const BITS = { 4: 32, 6: 128 } as const;

function parseV4(text: string): bigint | null {
  const parts = text.split('.');
  if (parts.length !== 4) return null;
  let out = 0n;
  for (const p of parts) {
    if (!/^(0|[1-9][0-9]{0,2})$/.test(p) || Number(p) > 255) return null;
    out = (out << 8n) | BigInt(p);
  }
  return out;
}

function parseV6(text: string): bigint | null {
  let s = text;
  const tail: number[] = [];
  const v4 = /^(.*:)([0-9.]+)$/.exec(s);
  if (v4 && v4[2].includes('.')) {
    const x = parseV4(v4[2]);
    if (x === null) return null;
    tail.push(Number((x >> 16n) & 0xffffn), Number(x & 0xffffn));
    s = v4[1].endsWith('::') ? v4[1] : v4[1].slice(0, -1);
  }
  const halves = s.split('::');
  if (halves.length > 2) return null;
  const read = (h: string) => (h === '' ? [] : h.split(':'));
  const head = read(halves[0]);
  const rest = halves.length === 2 ? read(halves[1]) : [];
  if (![...head, ...rest].every((g) => /^[0-9a-fA-F]{1,4}$/.test(g))) return null;
  const known = head.length + rest.length + tail.length;
  if (halves.length === 1 ? known !== 8 : known > 7) return null;
  const zeros: number[] = Array(halves.length === 2 ? 8 - known : 0).fill(0);
  const groups = [...head.map((g) => parseInt(g, 16)), ...zeros, ...rest.map((g) => parseInt(g, 16)), ...tail];
  return groups.reduce((acc, g) => (acc << 16n) | BigInt(g), 0n);
}

/** An address as Python's ip_address reads it, with no zone index. */
function parsePlain(text: string): Addr | null {
  if (text.includes(':')) {
    const a = parseV6(text);
    return a === null ? null : { v: 6, addr: a };
  }
  const a = parseV4(text);
  return a === null ? null : { v: 4, addr: a };
}

const parseAddress = (text: string) => parsePlain(text.split('%')[0]);

/** A network as Python's ip_network reads it, prefix lengths only. */
function parseNetwork(text: string, strict: boolean): Net | null {
  const parts = text.split('/');
  if (parts.length > 2) return null;
  const a = parsePlain(parts[0]);
  if (!a) return null;
  let prefix: number = BITS[a.v];
  if (parts.length === 2) {
    if (!/^[0-9]{1,3}$/.test(parts[1]) || Number(parts[1]) > BITS[a.v]) return null;
    prefix = Number(parts[1]);
  }
  const shift = BigInt(BITS[a.v] - prefix);
  const masked = (a.addr >> shift) << shift;
  if (strict && masked !== a.addr) return null;
  return { v: a.v, addr: masked, prefix };
}

function contains(n: Net, a: Addr): boolean {
  if (n.v !== a.v) return false;
  const shift = BigInt(BITS[n.v] - n.prefix);
  return (a.addr >> shift) === (n.addr >> shift);
}

const net = (text: string) => parseNetwork(text, false) as Net;
const overlaps = (a: Net, b: Net) => a.v === b.v && (contains(a, b) || contains(b, a));
const within = (a: Net, b: Net) => a.v === b.v && a.prefix >= b.prefix && contains(b, a);
const inNets = (a: Addr, nets: string[]) => nets.some((n) => contains(net(n), a));

function unwrap(a: Addr): Addr {
  if (a.v !== 6) return a;
  if (contains(net('::ffff:0:0/96'), a) || contains(net('64:ff9b::/96'), a)) return { v: 4, addr: a.addr & 0xffffffffn };
  if (contains(net('2002::/16'), a)) return { v: 4, addr: (a.addr >> 80n) & 0xffffffffn };
  return a;
}

/** A network in Python's notation, so both evaluators print an entry the same way. */
export function formatNetwork(n: Net): string {
  if (n.v === 4) return `${[24n, 16n, 8n, 0n].map((s) => String((n.addr >> s) & 0xffn)).join('.')}/${n.prefix}`;
  const groups = Array.from({ length: 8 }, (_, i) => Number((n.addr >> BigInt(112 - 16 * i)) & 0xffffn));
  let best = { start: -1, len: 0 };
  for (let i = 0; i < 8;) {
    if (groups[i] !== 0) { i++; continue; }
    let j = i;
    while (j < 8 && groups[j] === 0) j++;
    if (j - i > 1 && j - i > best.len) best = { start: i, len: j - i };
    i = j;
  }
  const hex = groups.map((g) => g.toString(16));
  const text = best.start === -1
    ? hex.join(':')
    : `${hex.slice(0, best.start).join(':')}::${hex.slice(best.start + best.len).join(':')}`;
  return `${text}/${n.prefix}`;
}

const NEVER_NETS = [...LOC.never.loopback, ...LOC.never.linkLocal, ...LOC.never.unspecified, ...LOC.never.metadata];

function serviceName(host: string): boolean {
  const h = host.replace(/\.+$/, '').toLowerCase();
  if (parseAddress(h)) return false;
  return !h.includes('.') || LOC.never.serviceNames.includes(h) || LOC.never.serviceSuffixes.some((s) => h.endsWith(s));
}

export type Destination = Deny | { decision: 'allow'; location: string };

/** The location class of a destination, from its resolved addresses.
 * `settings` carries `gate` (R0's private-network gate value) and
 * `allowlist` (ROUNDS_AI_PRIVATE_ENDPOINTS as written). */
export function classifyDestination(host: string, port: number | string, addresses: string[], settings?: Ctx | null): Destination {
  const s = settings || {};
  const h = String(host || '').replace(/^[[\]]+|[[\]]+$/g, '');
  if (serviceName(h)) return deny('DESTINATION_NEVER', 'locations.never');
  const found = (addresses || []).map(parseAddress);
  if (!found.length || found.some((a) => a === null)) return deny('DESTINATION_UNCLASSED', 'locations');
  const resolved = (found as Addr[]).map(unwrap);
  const kinds = new Set<string>();
  for (const a of resolved) {
    if (inNets(a, NEVER_NETS)) return deny('DESTINATION_NEVER', 'locations.never');
    if (inNets(a, LOC.privateNetworks)) kinds.add('private');
    else if (inNets(a, LOC.nonPublic)) return deny('DESTINATION_UNCLASSED', 'locations');
    else kinds.add('public');
  }
  if (kinds.size === 2) return deny('DESTINATION_MIXED', 'locations');
  if (kinds.has('public')) return { decision: 'allow', location: 'third-party-hosted' };
  if (s.gate !== 'enabled') return deny('DESTINATION_NOT_ALLOWLISTED', 'locations.combination');
  const entries = parsePrivateEndpoints(String(s.allowlist || ''));
  for (const a of resolved) {
    if (!entries.some((e) => contains(e.network, a) && Number(port) === e.port)) return deny('DESTINATION_NOT_ALLOWLISTED', 'locations.combination');
  }
  return { decision: 'allow', location: 'operator-network' };
}

const ENTRY = /^(?:\[([^\]]+)\]|([^:[\]]+)):([0-9]{1,5})$/;

/** A string quoted the way Python's repr quotes it, so both evaluators name a refused entry alike. */
function quoted(s: string): string {
  const q = s.includes("'") && !s.includes('"') ? '"' : "'";
  const hex = (cp: number, width: number) => cp.toString(16).padStart(width, '0');
  let out = q;
  for (const ch of s) {
    const cp = ch.codePointAt(0) as number;
    if (ch === '\\' || ch === q) out += `\\${ch}`;
    else if (ch === '\t') out += '\\t';
    else if (ch === '\n') out += '\\n';
    else if (ch === '\r') out += '\\r';
    else if (ch !== ' ' && /[\p{C}\p{Z}]/u.test(ch)) out += cp < 0x100 ? `\\x${hex(cp, 2)}` : cp < 0x10000 ? `\\u${hex(cp, 4)}` : `\\U${hex(cp, 8)}`;
    else out += ch;
  }
  return out + q;
}

/** ROUNDS_AI_PRIVATE_ENDPOINTS as entries { network, port }. Throws an Error
 * naming the first entry it refuses. */
export function parsePrivateEndpoints(value: string): { network: Net; port: number }[] {
  const name = 'ROUNDS_AI_PRIVATE_ENDPOINTS';
  const text = (value || '').trim();
  if (!text) return [];
  const out: { network: Net; port: number }[] = [];
  for (const raw of text.split(',')) {
    const item = raw.trim();
    if (!item) throw new Error(`${name} has an empty entry; separate entries with single commas`);
    const entry = `${name} entry ${quoted(item)}`;
    const m = ENTRY.exec(item);
    if (!m) throw new Error(`${entry} isn't ip:port, [ipv6]:port, cidr:port, or [ipv6-cidr]:port`);
    const host = m[1] ?? m[2];
    const port = Number(m[3]);
    if (port < 1 || port > 65535) throw new Error(`${entry} has port ${port}; ports run from 1 to 65535`);
    const slash = host.indexOf('/');
    const plain = !host.includes('%') && (slash === -1 || /^[0-9]{1,3}$/.test(host.slice(slash + 1)));
    let network = plain ? parseNetwork(host, true) : null;
    if (!network) {
      if (serviceName(host) || !/^[0-9a-fA-F.:/]+$/.test(host.split('%')[0])) {
        throw new Error(`${entry} names a host; entries are addresses or CIDR ranges, and service names are never destinations`);
      }
      throw new Error(`${entry} isn't a valid address or CIDR range`);
    }
    if (network.prefix === BITS[network.v]) {
      const a = unwrap(network);
      network = { ...a, prefix: BITS[a.v] };
    } else if (network.v === 6 && within(network, net('::ffff:0:0/96'))) {
      throw new Error(`${entry} is an IPv4-mapped range; write the IPv4 range`);
    }
    const n = network;
    const refused = NEVER_NETS.find((x) => overlaps(n, net(x)));
    if (refused) throw new Error(`${entry} covers ${refused}, which is never a destination`);
    if (!LOC.privateNetworks.some((x) => within(n, net(x)))) {
      throw new Error(`${entry} isn't inside a private network (${LOC.privateNetworks.join(', ')})`);
    }
    out.push({ network: n, port });
  }
  return out;
}

// ---------------------------------------------------------------- egress

/** The deepest input entry that covers `fieldId`. An omitted path also holds
 * for a column that reads its paths from that column. */
function inputFor(purpose: Purpose, fieldId: string): Input | null {
  const [base, pointer] = split(fieldId);
  const segs = segments(pointer);
  const aliases = columns(base).slice(1);
  let best: { rank: [number, number]; item: Input } | null = null;
  for (const item of purpose.inputs) {
    const [ib, ip] = split(item.field);
    let hit: boolean;
    if (item.field === fieldId) hit = true;
    else if (base.startsWith('storage:')) hit = ib.startsWith('storage:') && familyCovers(ib.slice('storage:'.length), base.slice('storage:'.length));
    else if (ib === base || (item.omit && aliases.includes(ib))) hit = ip !== null ? pointer !== null && pointerMatch(segments(ip), segs) : ib === base;
    else hit = false;
    if (!hit) continue;
    const rank: [number, number] = [segments(ip).length, item.omit ? 1 : 0];
    if (!best || rank[0] > best.rank[0] || (rank[0] === best.rank[0] && rank[1] > best.rank[1])) best = { rank, item };
  }
  return best ? best.item : null;
}

export interface Endpoint {
  host?: string | null; port?: number | string; addresses?: string[]; settings?: Ctx;
  credential?: { field?: string; registeredFor?: { host?: string; port?: number | string } };
}

/** Whether one provider request may go: `purpose` names a registered
 * purpose, `fieldIds` every classed value the payload carries as content,
 * `endpoint` its host, port, resolved addresses, and credential, `location`
 * the class the caller resolved, and `consent` what the user agreed to for
 * this request. Flags such as ai_policy never stand in for consent.
 * `registry` defaults to the purpose registry beside this module. */
export function evaluateEgress(purpose: string, fieldIds: string[], endpoint?: Endpoint | null, location?: string | null,
  consent?: Consent | null, context?: Ctx | null, registry?: Registry | null): Decision {
  const c = consent || {};
  const ctx = context || {};
  const ep = endpoint || {};
  const p = (registry || PURPOSES).purposes.find((x) => x.id === purpose);
  if (!p) return deny('PURPOSE_UNREGISTERED', 'purposes');
  const rule = `purposes.${purpose}`;
  if (p.status === 'retired') return deny('PURPOSE_RETIRED', rule);
  if (Math.trunc(Number(c.batch || 1)) > (p.batchMax ?? 1)) return deny('BATCH_OVER_CAP', `${rule}.batchMax`);
  const entries: [string, Entry][] = [];
  for (const fid of fieldIds) {
    const entry = resolveField(fid);
    if (!entry) return deny('FIELD_UNCLASSIFIED', 'field-map');
    if (entry.class === 'Secret') return deny('SECRET_AS_CONTENT', 'credentialChannel');
    const item = inputFor(p, fid);
    if (!item) return deny('FIELD_NOT_ALLOWED', `${rule}.inputs`);
    if (item.omit && !(c.added || []).includes(fid)) return deny('FIELD_NOT_ADDED', `${rule}.inputs`);
    entries.push([fid, entry]);
  }
  const credential = ep.credential && Object.keys(ep.credential).length ? ep.credential : null;
  if (credential) {
    const cred = resolveField(credential.field ?? '');
    if (!cred || cred.class !== 'Secret') return deny('CREDENTIAL_NOT_SECRET', 'credentialChannel');
    const reg = credential.registeredFor || {};
    const same = String(reg.host ?? '').toLowerCase() === String(ep.host ?? '').toLowerCase()
      && Math.trunc(Number(reg.port || 0)) === Math.trunc(Number(ep.port || 0));
    if (!same) return deny('CREDENTIAL_ENDPOINT_MISMATCH', 'credentialChannel');
  }
  if (!LOC.classes.some((x) => x.id === location)) return deny('DESTINATION_UNCLASSED', 'locations');
  if (ep.host !== undefined && ep.host !== null) {
    const resolved = classifyDestination(ep.host, ep.port || 0, ep.addresses || [], ep.settings);
    if (resolved.decision === 'deny') return resolved;
    if (resolved.location !== location) return deny('LOCATION_MISMATCH', 'locations');
  }
  const classed = entries.filter(([, e]) => e.class !== undefined);
  const unit = c.unit;
  if (unit === 'legacy-implicit' && p.status !== 'legacy') return deny('CONSENT_LEGACY_ONLY', 'consent.legacy-implicit');
  if (classed.length && unit !== 'per-request' && unit !== 'legacy-implicit') return deny('CONSENT_REQUIRED', 'consent');
  const obligations = [`location:${location}`];
  const sinkContext: Ctx = { consent: c, purpose, purposeStatus: p.status, purposeDeclares: true, overrides: ctx.overrides || [] };
  for (const [fid] of entries) {
    const answer = evaluateSink(fid, 'remote-ai', sinkContext);
    if (answer.decision === 'deny') return answer;
    obligations.push(...answer.obligations);
  }
  if (p.toolAuthority !== undefined && p.toolAuthority !== null && p.toolAuthority !== 'none') obligations.push('tools:buffer-staged');
  if (p.streaming) obligations.push('stream:provisional-preview');
  if (credential) obligations.push('credential:auth-header-only');
  if (unit === 'legacy-implicit') obligations.push('consent:legacy-implicit');
  return allow(obligations);
}

// ---------------------------------------------------------------- retention

const DAY = 86_400_000;
const HOUR = 3_600_000;

/** An instant; a timestamp without a zone reads as UTC. */
function instant(value: string): number {
  const text = String(value).replace(/^(\d{4}-\d{2}-\d{2}) /, '$1T');
  const zoned = /(?:[zZ]|[+-]\d{2}(?::?\d{2})?)$/.test(text) || !text.includes('T');
  const ms = Date.parse(zoned ? text : `${text}Z`);
  if (Number.isNaN(ms)) throw new RangeError(`not an ISO instant: ${text}`);
  return ms;
}

const iso = (ms: number) => new Date(ms).toISOString().replace(/\.\d{3}Z$/, 'Z');

export type RetentionAnswer = Deny | ({ decision: 'allow' } & Record<string, Json>);

/** When a `rowId` item expires and must be purged by, for the chosen `value`
 * (null takes the row's default) from `anchor`. `context` may name the
 * data's `class` and whether the account is a `demo`. */
export function evaluateRetention(rowId: string, value: Json | undefined, anchor: string, context?: Ctx | null): RetentionAnswer {
  const ctx = context || {};
  let row = LIFECYCLE.get(rowId);
  if (!row) return deny('RETENTION_UNKNOWN_ROW', 'lifecycle');
  const rule = `lifecycle.${rowId}`;
  while (row.sameAs !== undefined) row = LIFECYCLE.get(row.sameAs) as LifecycleRow;
  const spec = row.retention as Retention;
  const chosen = value === null || value === undefined ? spec.default : value;
  if (typeof chosen === 'boolean') return deny('OUT_OF_BOUNDS', rule);
  if (spec.choices && !spec.choices.includes(chosen)) return deny('OUT_OF_BOUNDS', rule);
  if (spec.range && (typeof chosen !== 'number' || !Number.isInteger(chosen) || chosen < spec.range[0] || chosen > spec.range[1])) {
    return deny('OUT_OF_BOUNDS', rule);
  }
  const cls = ctx.class;
  if (typeof cls === 'string' && (row.neverClasses ?? []).includes(cls)) return deny('NEVER_STORED', rule);
  if (ctx.demo && (row.neverFor ?? []).includes('demo')) return deny('NEVER_STORED', rule);
  const cap = typeof cls === 'string' ? row.maxDaysByClass?.[cls] : undefined;
  if (cap !== undefined && typeof chosen === 'number' && Number.isInteger(chosen) && chosen > cap) return deny('OUT_OF_BOUNDS', rule);
  const start = instant(anchor);
  const out: { decision: 'allow' } & Record<string, Json> = { decision: 'allow', value: chosen, versions: { retention: VERSIONS.retention } };
  if (chosen === 'off') return { ...out, stored: false, expires_at: null, purge_by: null };
  let expires: number | null;
  if (chosen === 'until-delete' || chosen === 'pinned') expires = null;
  else if (chosen === 'delete') expires = start;
  else expires = start + Math.trunc(Number(chosen)) * DAY;
  const hours = row.purgeWithinHours ?? 24;
  out.expires_at = expires === null ? null : iso(expires);
  out.purge_by = expires === null ? null : iso(expires + hours * HOUR);
  if (expires !== null && row.warningDays !== undefined) out.warn_at = iso(expires - row.warningDays * DAY);
  if (expires !== null && row.tombstoneDays !== undefined) out.tombstone_until = iso(expires + row.tombstoneDays * DAY);
  if (row.digestDays !== undefined) out.digest_until = iso(start + row.digestDays * DAY);
  const renew = typeof cls === 'string' ? row.renewDays?.[cls] : undefined;
  if (chosen === 'pinned' && renew) out.renew_by = iso(start + renew * DAY);
  return out;
}

// ---------------------------------------------------------------- secrets

export interface SecretFinding { pattern: string; start: number; end: number }

/** { code: 'secret-detected', findings: [{ pattern, start, end }] } with
 * offsets in code points, or null. Never returns the match. */
export function detectSecret(text: string): { code: 'secret-detected'; findings: SecretFinding[] } | null {
  const source = text || '';
  const findings: SecretFinding[] = [];
  const points = (i: number) => Array.from(source.slice(0, i)).length;
  for (const { id, re } of PATTERNS) {
    for (const m of source.matchAll(re)) {
      const at = m.index ?? 0;
      findings.push({ pattern: id, start: points(at), end: points(at + m[0].length) });
    }
  }
  if (!findings.length) return null;
  findings.sort((a, b) => a.start - b.start || a.end - b.end || (a.pattern < b.pattern ? -1 : a.pattern > b.pattern ? 1 : 0));
  return { code: 'secret-detected', findings };
}
