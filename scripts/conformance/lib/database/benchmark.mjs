// The database benchmark's receipt (ROUNDS-02-L01, DR-0004):
// contracts/database/benchmark.json, written by harness/bench/bench.py.
// It must carry the synthetic label, the full profile, the seed at the scale
// floor for 1 and 10 accounts, all five targets of spec 2056-2067, and a
// recorded consequence for every miss; an extrapolated miss is a miss.

import { finding, jsonLine } from '../context.mjs';
import { validate } from '../json-schema.mjs';

export const RECEIPT_PATH = 'contracts/database/benchmark.json';
export const RECEIPT_SCHEMA_PATH = 'contracts/database/benchmark.schema.json';
export const TARGET_IDS = ['read_your_writes', 'projection_lag_p95', 'write_freeze', 'rpo_zero', 'restore_rto'];
export const SCALES = ['1', '10'];
const LIMIT = { read_your_writes: 5000, projection_lag_p95: 2000, write_freeze: 900, rpo_zero: 0, restore_rto: 1800 };

const minor = (v) => String(v || '').split('.').slice(0, 2).join('.');

export function dockerfilePin(text) {
  const m = /^ARG PB_VERSION=(\S+)$/m.exec(text || '');
  return m ? m[1] : null;
}

// ctx-free checks of one receipt. `pin` is the Dockerfile's PB_VERSION and
// `stated` is DR-0004's pocketbase.benchmark note for a version difference.
export function checkReceipt({ receipt, text, schema, pin, stated }) {
  const findings = [];
  const f = (code, parts, message) => findings.push(finding(code, RECEIPT_PATH, text ? jsonLine(text, parts) : 1, message));
  for (const err of validate(receipt, schema)) {
    const missing = err.keyword === 'required' || err.keyword === 'const' || err.keyword === 'minItems';
    f(missing ? 'DB_BENCH_INCOMPLETE' : 'DB_BENCH_INVALID', err.pointer.split('/').slice(1), `${err.pointer || '/'} ${err.message}`);
  }
  if (receipt.synthetic !== true) f('DB_BENCH_INCOMPLETE', ['synthetic'], 'the receipt is not labeled synthetic; it may only hold generated data');
  if (receipt.seedPlan?.fraction !== 1) f('DB_BENCH_INCOMPLETE', ['seedPlan', 'fraction'], `the receipt seeded ${receipt.seedPlan?.fraction} of the scale floor; a ratified receipt is at the floor (spec 2020-2028)`);
  for (const s of SCALES) if (!receipt.scales?.[s]) f('DB_BENCH_INCOMPLETE', ['scales'], `the receipt has no ${s}-account run`);
  const targets = receipt.targets || [];
  for (const id of TARGET_IDS) {
    const hits = targets.filter((t) => t.id === id);
    if (hits.length !== 1) { f('DB_BENCH_INCOMPLETE', ['targets'], `target ${id} appears ${hits.length} times; each of the five appears once`); continue; }
    const t = hits[0];
    const i = targets.indexOf(t);
    const over = t.value === null || t.value === undefined || (id === 'rpo_zero' ? t.value !== 0 : t.value > LIMIT[id]);
    if (t.result === 'pass' && over) f('DB_BENCH_INVALID', ['targets', i, 'result'], `${id} reports pass with ${t.value} ${t.unit}, over its limit of ${LIMIT[id]}`);
    if (t.result === 'fail' && (!t.consequence || t.consequence === 'unrecorded')) f('DB_BENCH_MISS_UNRECORDED', ['targets', i], `${id} failed with no recorded consequence; name the next step (spec 2069-2071)`);
    if (t.basis === 'extrapolated' && !(receipt.extrapolations || []).length) f('DB_BENCH_INCOMPLETE', ['extrapolations'], `${id} is extrapolated, but the receipt lists no extrapolation with its formula`);
  }
  const all = TARGET_IDS.every((id) => targets.some((t) => t.id === id && t.result === 'pass'));
  if (receipt.result === 'pass' && !all) f('DB_BENCH_INVALID', ['result'], 'the receipt says pass while a target failed');
  const ran = receipt.profile?.pocketbase?.version;
  if (pin && ran && ran !== pin) {
    if (minor(ran) !== minor(pin)) f('DB_VERSION_MISMATCH', ['profile', 'pocketbase', 'version'], `the receipt ran PocketBase ${ran}, off the pinned ${pin}'s line; rerun it on the pin`);
    else if (!stated) f('DB_VERSION_MISMATCH', ['profile', 'pocketbase', 'version'], `the receipt ran PocketBase ${ran} and the pin is ${pin}; DR-0004 must state the difference (pocketbase.benchmark)`);
  }
  if (pin && receipt.profile?.pocketbase?.dockerfilePin?.PB_VERSION && receipt.profile.pocketbase.dockerfilePin.PB_VERSION !== ran) {
    f('DB_BENCH_INVALID', ['profile', 'pocketbase'], 'the receipt\'s binary and the Dockerfile pin it recorded differ; it ran something other than what it records');
  }
  return findings;
}

export function receiptSummary(receipt) {
  if (!receipt) return 'no receipt';
  const t = (receipt.targets || []).map((x) => `${x.id} ${x.result}`).join(', ');
  return `${receipt.result} (${t}); PocketBase ${receipt.profile?.pocketbase?.version}, ${Object.keys(receipt.scales || {}).join(' and ')} accounts, fraction ${receipt.seedPlan?.fraction}`;
}
