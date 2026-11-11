// Runs pb_hooks/admission.js under node for test_admission_hooks.py
// (ROUNDS-00A-L01 stage 3).
//
// The decisions run on an in-memory store with the PocketBase store's
// contract: one command per (account, command_id), one counter per
// (bucket, account, hour), unique lease token hashes, and leases deleted
// with their command. The PocketBase store itself runs in the harness.
//
//   node admission_runner.cjs <hooks dir> < program.json
//
// A program is {"steps": [...]}, read from stdin since a large result
// is over Linux's limit for one argument; each step names a call and its
// arguments, and the output is {"results": [...], "store": {...}}.

const fs = require("fs");
const path = require("path");
const { newMaps, admissionMemoryStore } = require("./admission_memory.cjs");

const [hooksDir] = process.argv.slice(2);
const program = JSON.parse(fs.readFileSync(0, "utf8"));

class BadRequestError extends Error {}
class UnauthorizedError extends Error {}
globalThis.BadRequestError = BadRequestError;
globalThis.UnauthorizedError = UnauthorizedError;
globalThis.$apis = { requestInfo: (ctx) => ctx.info };
// admission.js reads execution.js's job rules for a command that enqueued
// a job (ROUNDS-00A-L03 PR 2).
globalThis.__hooks = hooksDir;

const admission = require(path.join(hooksDir, "admission.js"));

function record(fields) {
  return { getBool: (name) => fields[name] === true };
}

function guard(step) {
  const original = step.original === undefined ? null : record(step.original);
  const e = {
    httpContext: { info: { admin: step.superuser ? { id: "admin" } : null, data: step.data || {} } },
    record: Object.assign(record(step.fields || {}), { originalCopy: () => original }),
    isNewRecord: step.isNewRecord !== false,
  };
  try {
    admission[step.call](e);
    return { allowed: true };
  } catch (err) {
    return { allowed: false, bad_request: err instanceof BadRequestError, message: err.message };
  }
}

const maps = newMaps();
const store = admissionMemoryStore(maps);
const results = program.steps.map((step) => {
  switch (step.call) {
    case "checkAdmit":
    case "checkSettle":
    case "checkFinish":
      return admission[step.call](step.input);
    // As handle() does: the input is checked before the decision runs.
    case "admit": {
      const input = admission.checkAdmit(step.input);
      return input === null ? { invalid: true } : admission.admit(store, step.account, input, step.now);
    }
    case "settle": {
      const input = admission.checkSettle(step.input);
      return input === null ? { invalid: true } : admission.settle(store, step.account, input, step.now);
    }
    case "finish": {
      const input = admission.checkFinish(step.input);
      return input === null ? { invalid: true } : admission.finish(store, step.account, input, step.now);
    }
    case "usage":
      return admission.usage(store, step.account, step.now);
    // A leaf hook that completes its own command (ROUNDS-00A-L04).
    case "completedResult":
      return admission.completedResult(store, step.account, step.command_id, step.now, step.operation,
        step.fingerprint);
    case "completeCommand":
      return admission.completeCommand(store, step.account, step.command_id, step.operation, step.result);
    // Earlier use in this hour, without a request for each unit.
    case "seedCounter":
      store.addToCounter(step.bucket, step.account, step.hour, step.requests, step.wall_seconds);
      return null;
    case "dump":
      return store.dump();
    case "sweep":
      return admission.sweep(store, step.now);
    // An execution job as execution.js keeps it, and enqueue's link to it
    // on the account's command (ROUNDS-00A-L03 PR 2).
    case "seedJob":
      maps.jobs.set(step.job.id, Object.assign({ outcome_class: "", attempts: 0, attempts_started: 0 }, step.job));
      return null;
    case "linkJob": {
      const linked = [...maps.commands.values()].find(
        (c) => c.account === step.account.id && c.command_id === step.command_id,
      );
      linked.job = step.job;
      return null;
    }
    case "jobStarted":
      admission.jobStarted(store, step.account.id, step.command_id, step.job);
      return null;
    case "jobEnded":
      return admission.jobEnded(store, step.account.id, step.command_id, step.job, step.outcome_class);
    case "tierOf":
      return admission.tierOf(step.fields === null ? null : record(step.fields));
    case "constants":
      return {
        VERSION: admission.VERSION,
        LIMITS: admission.LIMITS,
        OPERATIONS: admission.OPERATIONS,
        HOUR_S: admission.HOUR_S,
        COMMAND_TTL_S: admission.COMMAND_TTL_S,
        LEASE_GRACE_S: admission.LEASE_GRACE_S,
        HOLD_S: admission.HOLD_S,
        RESULT_MAX_CHARS: admission.RESULT_MAX_CHARS,
        DEMO_FIELDS: admission.DEMO_FIELDS,
        RUNNER_KEY_ENV: admission.RUNNER_KEY_ENV,
        RUNNER_KEY_HEADER: admission.RUNNER_KEY_HEADER,
        RUNNER_KEY_MIN_CHARS: admission.RUNNER_KEY_MIN_CHARS,
      };
    case "runnerKeyError":
      return admission.runnerKeyError(step.headers, step.secret);
    case "guardDemoCreate":
    case "guardDemoUpdate":
    case "guardDemoOAuth2":
      return guard(step);
    default:
      throw new Error("unknown call " + step.call);
  }
});

process.stdout.write(JSON.stringify({ results, store: store.dump() }));
