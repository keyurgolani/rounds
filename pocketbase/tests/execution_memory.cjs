// An in-memory store with the PocketBase store's contract for
// pb_hooks/execution.js (ROUNDS-00A-L03 PR 1): one job per
// (account, command_id), one attempt per (job, attempt_number) and per
// token hash, one envelope per attempt, and admission command rows as
// admission.js keeps them. execution_runner.cjs and execution_server.cjs
// run the decisions on it; the PocketBase store itself runs against a
// real PocketBase in the harness.

const crypto = require("crypto");

function unique(rows, row, fields, name) {
  if (rows.some((r) => r.id !== row.id && fields.every((f) => r[f] === row[f]))) {
    throw new Error(`UNIQUE constraint failed: ${name}.${fields.join(", ")}`);
  }
}

function memoryStore() {
  const commands = new Map();
  const jobs = new Map();
  const attempts = new Map();
  const envelopes = new Map();
  let ids = 0;
  const nextId = () => `id${String(++ids).padStart(13, "0")}`;
  const clone = (row) => (row === null || row === undefined ? null : JSON.parse(JSON.stringify(row)));
  function saver(map, uniques, name) {
    return (row) => {
      const saved = clone(row);
      if (!saved.id) saved.id = nextId();
      uniques.forEach((fields) => unique([...map.values()], saved, fields, name));
      map.set(saved.id, saved);
      return clone(saved);
    };
  }
  return {
    dump: () => ({
      commands: [...commands.values()].map(clone),
      jobs: [...jobs.values()].map(clone),
      attempts: [...attempts.values()].map(clone),
      envelopes: [...envelopes.values()].map(clone),
    }),
    seedCommand: (row) => {
      const saved = Object.assign({ id: nextId(), job: "" }, row);
      commands.set(saved.id, saved);
      return clone(saved);
    },
    hash: (token) => crypto.createHash("sha256").update(token).digest("hex"),
    findCommand: (account, commandId) =>
      clone([...commands.values()].find((c) => c.account === account && c.command_id === commandId) || null),
    saveCommand: (row) => {
      const stored = commands.get(row.id);
      stored.job = row.job;
      return clone(stored);
    },
    findJob: (account, commandId) =>
      clone([...jobs.values()].find((j) => j.account === account && j.command_id === commandId) || null),
    getJob: (id) => clone(jobs.get(id) || null),
    saveJob: saver(jobs, [["account", "command_id"]], "execution_jobs"),
    queuedJobs: (limit) =>
      [...jobs.values()].filter((j) => j.state === "queued").sort((a, b) => a.queued_at - b.queued_at).slice(0, limit).map(clone),
    activeJobCount: (account) =>
      [...jobs.values()].filter((j) => j.account === account && (j.state === "leased" || j.state === "started")).length,
    getAttempt: (id) => clone(attempts.get(id) || null),
    findAttemptByToken: (tokenHash) => clone([...attempts.values()].find((a) => a.token_hash === tokenHash) || null),
    saveAttempt: saver(attempts, [["job", "attempt_number"], ["token_hash"]], "execution_attempts"),
    expiredAttempts: (now, limit) =>
      [...attempts.values()]
        .filter((a) => (a.state === "leased" || a.state === "started") && a.lease_expires_at <= now)
        .sort((a, b) => a.lease_expires_at - b.lease_expires_at)
        .slice(0, limit)
        .map(clone),
    overBudgetAttempts: (cutoff, limit) =>
      [...attempts.values()]
        .filter((a) => a.state === "started" && a.deadline_at < cutoff)
        .sort((a, b) => a.deadline_at - b.deadline_at)
        .slice(0, limit)
        .map(clone),
    saveEnvelope: saver(envelopes, [["attempt"]], "execution_envelopes"),
  };
}

// The PocketBase globals execution.js reaches for while it loads.
function installGlobals(hooksDir) {
  class BadRequestError extends Error {}
  class UnauthorizedError extends Error {}
  class ForbiddenError extends Error {}
  globalThis.BadRequestError = BadRequestError;
  globalThis.UnauthorizedError = UnauthorizedError;
  globalThis.ForbiddenError = ForbiddenError;
  globalThis.$apis = { requestInfo: (ctx) => ctx.info };
  globalThis.__hooks = hooksDir;
  return { BadRequestError, UnauthorizedError, ForbiddenError };
}

module.exports = { memoryStore, installGlobals };
