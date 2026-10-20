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

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const [hooksDir] = process.argv.slice(2);
const program = JSON.parse(fs.readFileSync(0, "utf8"));

class BadRequestError extends Error {}
class UnauthorizedError extends Error {}
globalThis.BadRequestError = BadRequestError;
globalThis.UnauthorizedError = UnauthorizedError;
globalThis.$apis = { requestInfo: (ctx) => ctx.info };

const admission = require(path.join(hooksDir, "admission.js"));

function memoryStore() {
  const commands = new Map();
  const counters = new Map();
  const leases = new Map();
  let ids = 0;
  let tokens = 0;
  const nextId = () => `id${String(++ids).padStart(13, "0")}`;
  const clone = (row) => (row === null || row === undefined ? null : JSON.parse(JSON.stringify(row)));
  const counterKey = (bucket, account, hour) => `${bucket}|${account}|${hour}`;
  const live = (lease, now) => lease.expires_at > now;
  const deleteLease = (id) => leases.delete(id);

  return {
    dump: () => ({
      commands: [...commands.values()].map(clone),
      counters: [...counters.values()].map(clone),
      leases: [...leases.values()].map(clone),
    }),
    newToken: () => `tok${String(++tokens).padStart(40, "0")}`,
    hash: (token) => crypto.createHash("sha256").update(token).digest("hex"),
    findCommand: (account, commandId) =>
      clone([...commands.values()].find((c) => c.account === account && c.command_id === commandId) || null),
    getCommand: (id) => clone(commands.get(id) || null),
    saveCommand: (row) => {
      const saved = clone(row);
      if (!saved.id) {
        if ([...commands.values()].some((c) => c.account === saved.account && c.command_id === saved.command_id)) {
          throw new Error("UNIQUE constraint failed: admission_commands.account, admission_commands.command_id");
        }
        saved.id = nextId();
      }
      commands.set(saved.id, saved);
      return clone(saved);
    },
    deleteCommand: (row) => {
      commands.delete(row.id);
      for (const [id, lease] of leases) if (lease.command === row.id) deleteLease(id);
    },
    findLease: (tokenHash) => clone([...leases.values()].find((l) => l.token_hash === tokenHash) || null),
    saveLease: (row) => {
      const saved = clone(row);
      if (!saved.id) {
        if ([...leases.values()].some((l) => l.token_hash === saved.token_hash)) {
          throw new Error("UNIQUE constraint failed: admission_leases.token_hash");
        }
        saved.id = nextId();
      }
      leases.set(saved.id, saved);
      return clone(saved);
    },
    deleteLease: (row) => deleteLease(row.id),
    deleteLeasesForCommand: (commandId) => {
      for (const [id, lease] of leases) if (lease.command === commandId) deleteLease(id);
    },
    liveLeaseForCommand: (commandId, now) => [...leases.values()].some((l) => l.command === commandId && live(l, now)),
    liveLeases: (filter, now) => {
      const rows = [...leases.values()]
        .filter((l) => live(l, now))
        .filter((l) => filter.account === undefined || l.account === filter.account)
        .filter((l) => filter.demo === undefined || l.demo === true)
        .sort((a, b) => a.expires_at - b.expires_at);
      return { count: rows.length, soonest: rows.length > 0 ? rows[0].expires_at : null };
    },
    counter: (bucket, account, hour) => {
      const row = counters.get(counterKey(bucket, account, hour));
      return row ? { requests: row.requests, wall_seconds: row.wall_seconds } : null;
    },
    addToCounter: (bucket, account, hour, requests, wall) => {
      const key = counterKey(bucket, account, hour);
      const row = counters.get(key) || { bucket, account, hour, requests: 0, wall_seconds: 0 };
      row.requests = Math.max(0, row.requests + requests);
      row.wall_seconds = Math.max(0, row.wall_seconds + wall);
      counters.set(key, row);
    },
    repairInFlight: (now, limit) => {
      let repaired = 0;
      for (const command of [...commands.values()].filter((c) => c.state === "in_flight").slice(0, limit)) {
        if ([...leases.values()].some((l) => l.command === command.id && live(l, now))) continue;
        command.state = "failed_infrastructure";
        command.result = null;
        repaired += 1;
      }
      return repaired;
    },
    deleteExpired: (now, oldestHour, limit) => {
      [...leases.values()].filter((l) => l.expires_at <= now).slice(0, limit).forEach((l) => deleteLease(l.id));
      [...commands.values()].filter((c) => c.expires_at <= now).slice(0, limit).forEach((c) => commands.delete(c.id));
      [...counters.entries()].filter(([, c]) => c.hour < oldestHour).slice(0, limit).forEach(([k]) => counters.delete(k));
    },
  };
}

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

const store = memoryStore();
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
    // Earlier use in this hour, without a request for each unit.
    case "seedCounter":
      store.addToCounter(step.bucket, step.account, step.hour, step.requests, step.wall_seconds);
      return null;
    case "dump":
      return store.dump();
    case "sweep":
      return admission.sweep(store, step.now);
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
        RESULT_MAX_CHARS: admission.RESULT_MAX_CHARS,
        DEMO_FIELDS: admission.DEMO_FIELDS,
      };
    case "guardDemoCreate":
    case "guardDemoUpdate":
    case "guardDemoOAuth2":
      return guard(step);
    default:
      throw new Error("unknown call " + step.call);
  }
});

process.stdout.write(JSON.stringify({ results, store: store.dump() }));
