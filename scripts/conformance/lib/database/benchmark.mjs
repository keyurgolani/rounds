// The database benchmark's receipt (ROUNDS-02-L01, DR-0004):
// contracts/database/benchmark.json, written by harness/bench/bench.py.
// It must carry the synthetic label, the full profile, the seed at the scale
// floor for 1 and 10 accounts, all five targets of spec 2056-2067 with the
// spec's unit and limit, each value as the scales measured it, each basis as
// its extrapolations make it, a recorded consequence for every miss, and the
// rollback defaults with the basis of the target each rests on. An
// extrapolated miss is a miss.

import { finding, jsonLine } from '../context.mjs';
import { validate } from '../json-schema.mjs';

export const RECEIPT_PATH = 'contracts/database/benchmark.json';
export const RECEIPT_SCHEMA_PATH = 'contracts/database/benchmark.schema.json';
export const TARGET_IDS = ['read_your_writes', 'projection_lag_p95', 'write_freeze', 'rpo_zero', 'restore_rto'];
export const SCALES = ['1', '10'];
export const TARGETS = {
  read_your_writes: { limit: 5000, unit: 'ms' },
  projection_lag_p95: { limit: 2000, unit: 'ms' },
  write_freeze: { limit: 900, unit: 's' },
  rpo_zero: { limit: 0, unit: 'writes' },
  restore_rto: { limit: 1800, unit: 's' },
};

export const minor = (v) => String(v || '').split('.').slice(0, 2).join('.');

export function dockerfilePin(text) {
  const m = /^ARG PB_VERSION=(\d+\.\d+\.\d+)$/m.exec(text || '');
  return m ? m[1] : null;
}

// What each target's value is, recomputed from the scales the way
// harness/bench/bench.py's build_receipt computes it.
// A receipt missing a scale is DB_BENCH_INCOMPLETE, and nothing is recomputed.
export function measuredTargets(receipt) {
  const scales = receipt.scales || {};
  if (!SCALES.every((s) => scales[s])) return {};
  const big = scales['10'];
  const st = big.steady || {};
  let lost = 0;
  for (const sc of Object.values(scales)) {
    lost += (sc.crash?.ackedMissing || 0) + (sc.freeze?.rollback?.ackedMissing || 0) + (sc.freeze?.acceptedDuringFreeze || 0)
      + (sc.failpoints?.afterCommitBeforeRelay?.ackedMissing || 0);
  }
  const restore = (big.restores || []).find((r) => r.method === 'vacuum-into')?.restoreSeconds;
  const bytes = (receipt.extrapolations || []).filter((e) => e.target === 'restore_rto').reduce((a, e) => a + (e.seconds || 0), 0);
  return {
    read_your_writes: st.readYourWritesMs?.p99,
    projection_lag_p95: st.relayLagMs?.p95,
    write_freeze: big.freeze?.seconds,
    rpo_zero: lost,
    restore_rto: restore === undefined ? undefined : Math.round((restore + bytes) * 100) / 100,
  };
}

const close = (a, b) => typeof a === 'number' && typeof b === 'number' && Math.abs(a - b) <= 0.01 + 1e-9 * Math.abs(b);

// ctx-free checks of one receipt. `pocketbase` is DR-0004's pocketbase
// section (its ratified line, the pin at ratification, and the benchmark
// note), and `record` is DR-0004. The Dockerfile's pin is checked against
// the line in record.mjs.
export function checkReceipt({ receipt, text, schema, pocketbase = {}, record = null }) {
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
  const extrapolations = receipt.extrapolations || [];
  const measured = measuredTargets(receipt);
  for (const id of TARGET_IDS) {
    const hits = targets.filter((t) => t.id === id);
    if (hits.length !== 1) { f('DB_BENCH_INCOMPLETE', ['targets'], `target ${id} appears ${hits.length} times; each of the five appears once`); continue; }
    const t = hits[0];
    const i = targets.indexOf(t);
    const { limit, unit } = TARGETS[id];
    if (t.unit !== unit || t.limit !== limit) f('DB_BENCH_INVALID', ['targets', i, 'limit'], `${id} is ${t.limit} ${t.unit}; the spec's limit is ${limit} ${unit}`);
    const over = t.value === null || t.value === undefined || (id === 'rpo_zero' ? t.value !== 0 : t.value > limit);
    if (t.result === 'pass' && over) f('DB_BENCH_INVALID', ['targets', i, 'result'], `${id} reports pass with ${t.value} ${t.unit}, over its limit of ${limit}`);
    if (t.result === 'fail' && (!t.consequence || t.consequence === 'unrecorded')) f('DB_BENCH_MISS_UNRECORDED', ['targets', i], `${id} failed with no recorded consequence; name the next step (spec 2069-2071)`);
    if (measured[id] !== undefined && !close(t.value, measured[id])) {
      f('DB_BENCH_INVALID', ['targets', i, 'value'], `${id} reports ${t.value} ${t.unit}, but the receipt's own measurements give ${measured[id]}`);
    }
    // The basis is what the value rests on: a target an extrapolation feeds
    // is extrapolated, and an extrapolated one names its extrapolation.
    const feeds = extrapolations.filter((e) => e.target === id);
    if (t.basis === 'extrapolated' && !feeds.length) f('DB_BENCH_INCOMPLETE', ['extrapolations'], `${id} is extrapolated, but the receipt lists no extrapolation for it with its formula`);
    if (t.basis === 'measured' && feeds.length) f('DB_BENCH_INVALID', ['targets', i, 'basis'], `${id} is labeled measured, but ${feeds.length} extrapolation(s) feed it`);
  }
  const all = TARGET_IDS.every((id) => targets.some((t) => t.id === id && t.result === 'pass'));
  if (receipt.result === 'pass' && !all) f('DB_BENCH_INVALID', ['result'], 'the receipt says pass while a target failed');
  // DR-0003 P5's defaults carry their target's basis and verdict.
  for (const [name, d] of Object.entries(receipt.rollbackDefaults || {})) {
    // A default without its basis is DB_BENCH_INCOMPLETE through the schema.
    if (!d || typeof d !== 'object' || d.basis === undefined) continue;
    const at = ['rollbackDefaults', name];
    if (d.target) {
      const t = targets.find((x) => x.id === d.target);
      if (!t) f('DB_BENCH_INVALID', at, `the default ${name} rests on ${d.target}, which the receipt doesn't have`);
      else if (d.basis !== t.basis || d.met !== (t.result === 'pass')) {
        f('DB_BENCH_INVALID', at, `the default ${name} says ${d.met ? 'met' : 'not met'} (${d.basis}), but its target ${d.target} is a ${t.basis} ${t.result}`);
      }
    } else if (d.basis === 'not-run' && (d.met || !d.owner)) {
      f('DB_BENCH_INVALID', at, `the default ${name} wasn't run, so it is not met and names the leaf that runs it`);
    }
  }
  // The line, not the patch: the receipt ran on DR-0004's line, and a run on
  // another patch than the pin at ratification is stated, naming both.
  const ran = receipt.profile?.pocketbase?.version;
  if (pocketbase.line && ran && minor(ran) !== pocketbase.line) {
    f('DB_VERSION_MISMATCH', ['profile', 'pocketbase', 'version'], `the receipt ran PocketBase ${ran}, off DR-0004's ${pocketbase.line} line; rerun it on that line`);
  }
  const at = pocketbase.pinAtRatification;
  if (at && ran && ran !== at) {
    const note = String(pocketbase.benchmark || '');
    if (!note.includes(ran) || !note.includes(at)) {
      f('DB_VERSION_MISMATCH', ['profile', 'pocketbase', 'version'], `the receipt ran PocketBase ${ran} and DR-0004 pins ${at}; pocketbase.benchmark must state the difference, naming both versions`);
    }
  }
  const recorded = receipt.profile?.pocketbase?.dockerfilePin?.PB_VERSION;
  if (recorded && ran && recorded !== ran) f('DB_BENCH_INVALID', ['profile', 'pocketbase'], `the receipt ran ${ran} but recorded the Dockerfile pin ${recorded}; it ran something other than what it records`);
  // One revision counter: the receipt belongs to a revision the record has reached.
  if (record && Number.isInteger(receipt.revision)) {
    if (receipt.revision > record.revision) f('DB_VERSION_MISMATCH', ['revision'], `the receipt is for revision ${receipt.revision}; ${record.id} is at ${record.revision}`);
    if (record.benchmark?.revision !== undefined && record.benchmark.revision !== receipt.revision) {
      f('DB_VERSION_MISMATCH', ['revision'], `${record.id} rests on the receipt of revision ${record.benchmark.revision}; this one is revision ${receipt.revision}`);
    }
  }
  return findings;
}

export function receiptSummary(receipt) {
  if (!receipt) return 'no receipt';
  const t = (receipt.targets || []).map((x) => `${x.id} ${x.result}`).join(', ');
  return `${receipt.result} (${t}); PocketBase ${receipt.profile?.pocketbase?.version}, ${Object.keys(receipt.scales || {}).join(' and ')} accounts, fraction ${receipt.seedPlan?.fraction}, revision ${receipt.revision}`;
}
