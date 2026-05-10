/**
 * Grading harness for event-bus-ts.
 *
 * Imports the candidate's EventBus, runs scenarios, emits one JSON
 * line on stdout matching the take-home runner contract:
 *   {"criteria": [{"id":..., "passed":..., "weight":..., "logs":...}, ...],
 *    "score": <weighted sum>, "duration_ms": <int>}
 *
 * Path: this file is at <workdir>/harness/run.ts; the candidate's
 * source is at <workdir>/eventBus.ts. Hence the import below.
 */
import { EventBus } from "../eventBus.ts";

type Check = () => Promise<{ passed: boolean; logs: string }> | { passed: boolean; logs: string };

async function safeRun(fn: Check): Promise<{ passed: boolean; logs: string }> {
  try {
    const r = fn();
    return r instanceof Promise ? await r : r;
  } catch (e) {
    return { passed: false, logs: `check threw: ${(e as Error).stack ?? String(e)}`.slice(0, 500) };
  }
}

const checkSingleSubscriber: Check = () => {
  const bus = new EventBus();
  let received: unknown = null;
  bus.on<number>("ping", (n) => { received = n; });
  bus.emit("ping", 42);
  if (received === 42) return { passed: true, logs: "ok" };
  return { passed: false, logs: `expected 42, got ${String(received)}` };
};

const checkMultipleSubscribers: Check = () => {
  const bus = new EventBus();
  const calls: number[] = [];
  bus.on<number>("data", (n) => calls.push(n + 1));
  bus.on<number>("data", (n) => calls.push(n * 2));
  bus.emit("data", 5);
  if (calls.length === 2 && calls.includes(6) && calls.includes(10)) {
    return { passed: true, logs: `calls=${JSON.stringify(calls)}` };
  }
  return { passed: false, logs: `expected calls to contain 6 and 10, got ${JSON.stringify(calls)}` };
};

const checkUnsubscribe: Check = () => {
  const bus = new EventBus();
  let count = 0;
  const off = bus.on("evt", () => { count++; });
  bus.emit("evt", null);
  off();
  bus.emit("evt", null);
  if (count === 1) return { passed: true, logs: "ok" };
  return { passed: false, logs: `expected count=1 after unsubscribe, got ${count}` };
};

const checkNoCrossEventLeakage: Check = () => {
  const bus = new EventBus();
  let aHits = 0;
  let bHits = 0;
  bus.on("a", () => { aHits++; });
  bus.on("b", () => { bHits++; });
  bus.emit("a", null);
  bus.emit("a", null);
  if (aHits === 2 && bHits === 0) return { passed: true, logs: "ok" };
  return { passed: false, logs: `expected aHits=2,bHits=0; got aHits=${aHits},bHits=${bHits}` };
};

const checkThrowingSubscriberDoesNotBlock: Check = () => {
  const bus = new EventBus();
  let secondCalled = false;
  bus.on("evt", () => { throw new Error("boom"); });
  bus.on("evt", () => { secondCalled = true; });
  try {
    bus.emit("evt", null);
  } catch {
    return { passed: false, logs: "emit() must not propagate listener exceptions" };
  }
  if (secondCalled) return { passed: true, logs: "ok" };
  return { passed: false, logs: "second subscriber not called after first threw" };
};

const checkCodeQuality: Check = async () => {
  // Heuristic: look at the source file. Pass if EITHER:
  //   - imports/uses Map<...> / Map.prototype as the storage, OR
  //   - uses a Record/object keyed by event name (less ideal but acceptable),
  // AND the on() method returns a function (object literal storage with
  // `[event, fn]` tuples is what we don't want).
  const fs = await import("node:fs/promises");
  const src = await fs.readFile("eventBus.ts", "utf-8").catch(() => "");
  if (src.includes("Map") && src.includes("get") && src.includes("set")) {
    return { passed: true, logs: "uses Map storage" };
  }
  if (/Record<\s*string\s*,/.test(src) || /:\s*\{\s*\[/.test(src)) {
    return { passed: true, logs: "uses object/Record storage" };
  }
  return { passed: false, logs: "no Map or Record-keyed storage found in eventBus.ts" };
};

const CRITERIA: Array<{ id: string; weight: number; check: Check }> = [
  { id: "single_subscriber_receives_emit", weight: 0.2, check: checkSingleSubscriber },
  { id: "multiple_subscribers_all_called", weight: 0.2, check: checkMultipleSubscribers },
  { id: "unsubscribe_returned_function", weight: 0.2, check: checkUnsubscribe },
  { id: "no_cross_event_leakage", weight: 0.15, check: checkNoCrossEventLeakage },
  { id: "throwing_subscriber_does_not_block_others", weight: 0.15, check: checkThrowingSubscriberDoesNotBlock },
  { id: "code_quality", weight: 0.1, check: checkCodeQuality },
];

async function main(): Promise<void> {
  const started = performance.now();
  const out: Array<{ id: string; passed: boolean; weight: number; logs: string }> = [];
  let score = 0;
  for (const { id, weight, check } of CRITERIA) {
    const { passed, logs } = await safeRun(check);
    out.push({ id, passed, weight, logs });
    if (passed) score += weight;
  }
  const durationMs = Math.round(performance.now() - started);
  process.stdout.write(JSON.stringify({ criteria: out, score: Math.round(score * 1000) / 1000, duration_ms: durationMs }) + "\n");
}

main().catch((e) => {
  process.stderr.write(`harness fatal: ${(e as Error).stack ?? String(e)}\n`);
  process.stdout.write(JSON.stringify({
    criteria: CRITERIA.map(({ id, weight }) => ({ id, passed: false, weight, logs: "harness fatal" })),
    score: 0,
    duration_ms: 0,
  }) + "\n");
});
