// A stand-in for PocketBase's execution hook routes, for the runner's
// worker tests (backend/tests/test_execution_worker.py, ROUNDS-00A-L03
// PR 1). It serves pb_hooks/execution.js's own checks and decisions over
// HTTP on 127.0.0.1, on the in-memory store in execution_memory.cjs, with
// a clock the test moves. What only PocketBase does, the record auth and
// the one write connection, runs on a real PocketBase in the harness.
//
//   node execution_server.cjs <hooks dir> <worker secret> <runner key>
//
// It prints {"port": N} once it listens. Beside the hook routes and the
// execution_service login, /__test/ routes seed admission commands and
// user tokens, move the clock, switch the store off, and dump the store.

const http = require("http");
const path = require("path");
const crypto = require("crypto");
const { memoryStore, installGlobals } = require("./execution_memory.cjs");

const [hooksDir, workerSecret, runnerKey] = process.argv.slice(2);
installGlobals(hooksDir);
const execution = require(path.join(hooksDir, "execution.js"));
const admission = require(path.join(hooksDir, "admission.js"));

const store = memoryStore();
const serviceTokens = new Set();
const userTokens = new Map();
let offset = 0;
let storeOn = true;
let logins = 0;
const base = Math.floor(Date.now() / 1000);
const now = () => base + Math.floor((Date.now() / 1000 - base)) + offset;
const maxBudget = (kind) => admission.OPERATIONS[execution.KINDS[kind].operation][1];

function send(res, status, body) {
  const text = JSON.stringify(body);
  res.writeHead(status, { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(text) });
  res.end(text);
}

function bearer(req) {
  const raw = req.headers.authorization || "";
  return raw.startsWith("Bearer ") ? raw.slice(7) : raw;
}

const SERVICE = {
  claim: [execution.checkClaim, (input) => execution.claim(store, input, now())],
  heartbeat: [execution.checkHeartbeat, (input) => execution.heartbeat(store, input, now(), maxBudget)],
  complete: [execution.checkComplete, (input) => execution.complete(store, input, now())],
  reap: [execution.checkReap, () => ({ status: 200, body: Object.assign({ v: execution.VERSION }, execution.reap(store, now())) })],
};
const CALLER = {
  enqueue: [execution.checkEnqueue, (account, input) => execution.enqueue(store, account, input, now())],
  cancel: [execution.checkCancel, (account, input) => execution.cancel(store, account, input, now())],
};

function route(req, data, res) {
  const url = req.url.split("?")[0];
  if (url === "/api/collections/execution_service/auth-with-password") {
    logins += 1;
    if (data && data.identity === execution.WORKER_USERNAME && data.password === workerSecret) {
      const token = "svc" + crypto.randomBytes(16).toString("hex");
      serviceTokens.add(token);
      return send(res, 200, { token, record: { id: "worker000000001", username: execution.WORKER_USERNAME } });
    }
    return send(res, 400, { code: 400, message: "Failed to authenticate.", data: {} });
  }
  const hook = url.match(/^\/api\/rounds\/execution\/(\w+)$/);
  if (hook) {
    const action = hook[1];
    const token = bearer(req);
    if (SERVICE[action]) {
      if (!serviceTokens.has(token) && !userTokens.has(token)) return send(res, 401, { code: 401, message: "", data: {} });
      if (!serviceTokens.has(token)) return send(res, 403, { code: 403, message: "", data: {} });
      if (!storeOn) return send(res, 503, { v: execution.VERSION, error: "store_off" });
      const [check, decide] = SERVICE[action];
      const input = check(data);
      if (input === null) return send(res, 400, { v: execution.VERSION, error: "invalid_request" });
      const out = decide(input);
      return send(res, out.status, out.body);
    }
    if (CALLER[action]) {
      if (!userTokens.has(token)) return send(res, 401, { code: 401, message: "", data: {} });
      if (!storeOn) return send(res, 503, { v: execution.VERSION, error: "store_off" });
      const refused = admission.runnerKeyError({ x_rounds_admission_key: req.headers["x-rounds-admission-key"] }, runnerKey);
      if (refused !== null) return send(res, refused.status, { v: execution.VERSION, error: refused.body.error });
      const [check, decide] = CALLER[action];
      const input = check(data);
      if (input === null) return send(res, 400, { v: execution.VERSION, error: "invalid_request" });
      const out = decide({ id: userTokens.get(token) }, input);
      return send(res, out.status, out.body);
    }
    return send(res, 404, { code: 404, message: "", data: {} });
  }
  if (url === "/__test/user") {
    const token = "usr" + crypto.randomBytes(16).toString("hex");
    userTokens.set(token, data.account);
    return send(res, 200, { token });
  }
  if (url === "/__test/command") return send(res, 200, store.seedCommand(Object.assign({ expires_at: now() + 86400 }, data)));
  if (url === "/__test/advance") {
    offset += data.seconds;
    return send(res, 200, { now: now() });
  }
  if (url === "/__test/store") {
    storeOn = Boolean(data.on);
    return send(res, 200, { on: storeOn });
  }
  if (url === "/__test/revoke") {
    serviceTokens.clear();
    return send(res, 200, {});
  }
  if (url === "/__test/dump") return send(res, 200, Object.assign({ now: now(), logins }, store.dump()));
  return send(res, 404, { code: 404, message: "", data: {} });
}

const server = http.createServer((req, res) => {
  const chunks = [];
  req.on("data", (chunk) => chunks.push(chunk));
  req.on("end", () => {
    let data = null;
    const text = Buffer.concat(chunks).toString("utf8");
    if (text) {
      try {
        data = JSON.parse(text);
      } catch (_) {
        return send(res, 400, { code: 400, message: "", data: {} });
      }
    }
    try {
      route(req, data, res);
    } catch (err) {
      send(res, 500, { code: 500, message: String(err && err.message), data: {} });
    }
  });
});

server.listen(0, "127.0.0.1", () => {
  process.stdout.write(JSON.stringify({ port: server.address().port }) + "\n");
});
