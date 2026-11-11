// Runs pb_hooks/execution.js under node for test_execution_hooks.py
// (ROUNDS-00A-L03 PR 1), on the in-memory store in execution_memory.cjs.
//
//   node execution_runner.cjs <hooks dir> < program.json
//
// A program is {"steps": [...]}; each step names a call and its
// arguments, and the output is {"results": [...], "store": {...}}.

const fs = require("fs");
const path = require("path");
const { memoryStore, installGlobals } = require("./execution_memory.cjs");

const [hooksDir] = process.argv.slice(2);
const program = JSON.parse(fs.readFileSync(0, "utf8"));

const { BadRequestError, NotFoundError } = installGlobals(hooksDir);

const execution = require(path.join(hooksDir, "execution.js"));
const admission = require(path.join(hooksDir, "admission.js"));

// The execution_service collection, as bootstrapWorker sees it.
function memoryAccounts(initial) {
  const records = initial ? [Object.assign({}, initial)] : [];
  return {
    records,
    find: (username) => records.find((r) => r.username === username) || null,
    create: (username, secret) => records.push({ username, password: secret }),
    validatePassword: (record, secret) => record.password === secret,
    setPassword: (record, secret) => {
      record.password = secret;
    },
  };
}

// $app and $os as bootstrapWorker and syncWorkerForLogin use them, over
// one execution_service collection that may not exist yet.
function fakeApp(step) {
  const records = step.existing ? [Object.assign({}, step.existing)] : [];
  const logs = [];
  class FakeRecord {
    constructor() {
      this.fields = {};
    }
    set(name, value) {
      this.fields[name] = value;
    }
    setPassword(secret) {
      this.fields.password = secret;
    }
  }
  const view = (r) => (r ? { username: r.username, password: r.password } : null);
  const dao = {
    findCollectionByNameOrId: (name) => {
      if (name !== "execution_service" || step.collection === false) throw new Error("missing collection " + name);
      return { name };
    },
    findAuthRecordByUsername: (_collection, username) => {
      if (step.collection === false) throw new Error("missing collection");
      const found = records.find((r) => r.username === username);
      if (!found) throw new Error("sql: no rows in result set");
      return {
        _row: found,
        validatePassword: (secret) => found.password === secret,
        setPassword: (secret) => {
          found.password = secret;
        },
      };
    },
    saveRecord: (record) => {
      if (record instanceof FakeRecord) records.push({ username: record.fields.username, password: record.fields.password });
    },
  };
  globalThis.$app = { dao: () => dao };
  globalThis.$os = { getenv: (key) => (key === "ROUNDS_EXECUTION_SECRET" ? step.secret : "") };
  globalThis.$security = { randomString: (n) => "r".repeat(n) };
  globalThis.Record = FakeRecord;
  const log = console.log;
  const error = console.error;
  console.log = (...a) => logs.push(a.join(" "));
  console.error = (...a) => logs.push(a.join(" "));
  return {
    records,
    view,
    done: () => {
      console.log = log;
      console.error = error;
      return logs;
    },
  };
}

function guard(step) {
  const record = (fields) => ({ getString: (name) => (fields && typeof fields[name] === "string" ? fields[name] : "") });
  const original = step.original === undefined ? null : record(step.original);
  const e = {
    httpContext: { info: { admin: step.superuser ? { id: "admin" } : null } },
    record: Object.assign(record(step.fields || {}), { originalCopy: () => original }),
  };
  try {
    execution[step.call](e);
    return { allowed: true };
  } catch (err) {
    return { allowed: false, bad_request: err instanceof BadRequestError, message: err.message };
  }
}

// handleCaller or handleService on a fake request. Their gate,
// principal, and key checks all run before the transaction, so the step
// stops there and reports whether it got that far.
function handle(step) {
  const env = Object.assign({ ROUNDS_GATE_EXECUTION_STORE: "on" }, step.env || {});
  globalThis.$os = { getenv: (key) => (key in env ? env[key] : "") };
  let reached = false;
  const reach = () => {
    reached = true;
    throw new Error("reached the store");
  };
  globalThis.$app = {
    // status reads outside a transaction, so a read counts too (PR 2).
    dao: () => ({ runInTransaction: reach, findRecordsByFilter: reach, findCollectionByNameOrId: reach }),
  };
  const who = step.principal || null;
  const authRecord = who === null ? null : {
    id: who.id || "acct00000000001",
    collection: () => ({ name: who.collection }),
    username: () => who.username || "",
  };
  const c = {
    info: { authRecord, headers: step.headers || {}, data: step.data || {}, admin: null },
    json: (status, body) => ({ status, body }),
  };
  const fn = step.call === "handleCaller" ? execution.handleCaller : execution.handleService;
  try {
    const out = fn(c, step.action);
    return { reached, status: out.status, error: out.body.error };
  } catch (err) {
    return reached ? { reached } : { reached, thrown: err.constructor.name };
  }
}

const maxBudget = (kind) => admission.OPERATIONS[execution.KINDS[kind].operation][1];
// The job's admission charge moves with the job, as in one PocketBase
// transaction (PR 2).
const store = memoryStore({ admission });
const results = program.steps.map((step) => {
  switch (step.call) {
    case "seedCommand":
      return store.seedCommand(step.row);
    // What admission's same-key retry does to the account's command: it's
    // in flight again (PR 2's jobEnded ends it with its job).
    case "rearmCommand": {
      const row = store.admission().findCommand(step.account.id, step.command_id);
      row.state = "in_flight";
      store.admission().saveCommand(row);
      return null;
    }
    // Admission's own decisions on the same rows, as handle() runs them.
    case "admit": {
      const input = admission.checkAdmit(step.input);
      return input === null ? { invalid: true } : admission.admit(store.admission(), step.account, input, step.now);
    }
    case "settle": {
      const input = admission.checkSettle(step.input);
      return input === null ? { invalid: true } : admission.settle(store.admission(), step.account, input, step.now);
    }
    case "finish": {
      const input = admission.checkFinish(step.input);
      return input === null ? { invalid: true } : admission.finish(store.admission(), step.account, input, step.now);
    }
    case "sweep":
      return admission.sweep(store.admission(), step.now);
    case "status": {
      const input = execution.checkStatus(step.input);
      if (input === null) return { status: 400, body: { error: "invalid_request" } };
      return execution.status(store, step.account, input);
    }
    case "purge":
      return execution.purge(store, step.now);
    case "checkEnqueue":
    case "checkCancel":
    case "checkStatus":
    case "checkClaim":
    case "checkHeartbeat":
    case "checkComplete":
    case "checkResult":
    case "checkReap":
      return execution[step.call](step.input);
    // As the handlers do: the input is checked before the decision runs.
    case "enqueue":
    case "cancel": {
      const check = step.call === "enqueue" ? execution.checkEnqueue : execution.checkCancel;
      const input = check(step.input);
      if (input === null) return { status: 400, body: { error: "invalid_request" } };
      return execution[step.call](store, step.account, input, step.now);
    }
    case "claim": {
      const input = execution.checkClaim(step.input);
      if (input === null) return { status: 400, body: { error: "invalid_request" } };
      // With how many whole job rows it read.
      const before = store.jobReads();
      const out = execution.claim(store, input, step.now);
      return Object.assign({ job_reads: store.jobReads() - before }, out);
    }
    case "heartbeat": {
      const input = execution.checkHeartbeat(step.input);
      if (input === null) return { status: 400, body: { error: "invalid_request" } };
      return execution.heartbeat(store, input, step.now, maxBudget);
    }
    case "complete": {
      const input = execution.checkComplete(step.input);
      if (input === null) return { status: 400, body: { error: "invalid_request" } };
      return execution.complete(store, input, step.now);
    }
    case "reap":
      return execution.reap(store, step.now);
    case "ensureWorker": {
      const accounts = memoryAccounts(step.existing);
      const did = execution.ensureWorker(accounts, step.secret, () => "r".repeat(64));
      return { did, records: accounts.records };
    }
    case "guardEnvelopeCreate":
    case "guardEnvelopeUpdate":
      return guard(step);
    case "handleCaller":
    case "handleService":
      return handle(step);
    case "bootstrapWorker": {
      const app = fakeApp(step);
      const did = execution.bootstrapWorker();
      app.done();
      return { did, records: app.records.map(app.view) };
    }
    case "syncWorkerForLogin": {
      const app = fakeApp(step);
      // The login request, under the collection segment its path named.
      const segment = step.segment === undefined ? "execution_service" : step.segment;
      const httpContext = segment === null ? null : { pathParam: (name) => (name === "collection" ? segment : "") };
      const e = { identity: step.identity, record: null, httpContext };
      try {
        execution.syncWorkerForLogin(e);
      } catch (err) {
        app.done();
        if (!(err instanceof NotFoundError)) throw err;
        return { not_found: true, records: app.records.map(app.view) };
      }
      // What it did, from its obs line; it logs every change, not a
      // login that changed nothing.
      const lines = app.done().filter((line) => line.startsWith("{")).map((line) => JSON.parse(line));
      let did = null;
      if (step.identity === execution.WORKER_USERNAME) did = lines.length ? lines[0].worker : "unchanged";
      return { did, record: e.record ? app.view(e.record._row) : null, records: app.records.map(app.view) };
    }
    default:
      throw new Error(`unknown call ${step.call}`);
  }
});

process.stdout.write(JSON.stringify({ results, store: store.dump() }));
