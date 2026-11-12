// An in-memory store with the PocketBase store's contract for
// pb_hooks/execution.js (ROUNDS-00A-L03): one job per
// (account, command_id), one attempt per (job, attempt_number) and per
// token hash, one envelope per attempt, and admission command rows as
// admission.js keeps them. execution_runner.cjs and execution_server.cjs
// run the decisions on it; the PocketBase store itself runs against a
// real PocketBase in the harness.
//
// It shares its maps with admission_memory.cjs's store (`admission()`), so
// the job's admission charge (admission.js jobStarted and jobEnded, PR 2)
// moves with the job, as one PocketBase transaction moves both. Given
// `admission`, the loaded admission.js, it runs those two decisions;
// either way it records each call in `admission_calls`.

const crypto = require("crypto");
const { newMaps, admissionMemoryStore } = require("./admission_memory.cjs");

function unique(rows, row, fields, name) {
  if (rows.some((r) => r.id !== row.id && fields.every((f) => r[f] === row[f]))) {
    throw new Error(`UNIQUE constraint failed: ${name}.${fields.join(", ")}`);
  }
}

const ACTIVE = ["leased", "started"];
const TERMINAL = ["completed", "timed-out", "denied", "canceled", "failed"];

// Oldest first; jobs queued in the same second, in the order they came.
function byQueue(a, b) {
  return a.queued_at - b.queued_at || (a.id < b.id ? -1 : 1);
}

function memoryStore(options) {
  const admissionRules = options && options.admission ? options.admission : null;
  const reads = { jobs: 0 };
  const maps = newMaps();
  const { commands, jobs, leases, nextId } = maps;
  const admissionView = admissionMemoryStore(maps);
  const attempts = new Map();
  const envelopes = new Map();
  const admissionCalls = [];
  // PR 3: the practice items' own rows (slug to id), the campaigns (id to
  // owner), and the graded rows complete writes, by collection.
  const items = { ai_coding_rounds: new Map(), take_home_assignments: new Map() };
  const campaigns = new Map();
  const graded = { ai_coding_attempts: new Map(), take_home_attempts: new Map() };
  const currentEnvelope = (job) => {
    const last = [...attempts.values()].find((a) => a.job === job.id && a.attempt_number === job.attempts);
    if (!last) return null;
    return [...envelopes.values()].find((e) => e.attempt === last.id) || null;
  };
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
      leases: [...leases.values()].map(clone),
      counters: admissionView.dump().counters,
      admission_calls: admissionCalls.map(clone),
      graded: {
        ai_coding_attempts: [...graded.ai_coding_attempts.values()].map(clone),
        take_home_attempts: [...graded.take_home_attempts.values()].map(clone),
      },
    }),
    // PR 3's seeds: a practice item's row, a campaign and its owner.
    seedItem: (collection, slug) => {
      const id = nextId();
      items[collection].set(slug, id);
      return id;
    },
    dropItem: (collection, slug) => items[collection].delete(slug),
    seedCampaign: (id, user) => campaigns.set(id, user),
    // The admission side, over the same rows.
    admission: () => admissionView,
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
    findJob: (account, commandId) => {
      reads.jobs += 1;
      return clone([...jobs.values()].find((j) => j.account === account && j.command_id === commandId) || null);
    },
    getJob: (id) => {
      reads.jobs += 1;
      return clone(jobs.get(id) || null);
    },
    saveJob: saver(jobs, [["account", "command_id"]], "execution_jobs"),
    // As the PocketBase store's query: each account's oldest queued job,
    // for the accounts with fewer than cap leased or started, oldest
    // first, ids and attempt counts only.
    claimable: (cap, limit) => {
      const all = Array.from(jobs.values());
      const busy = (account) => all.filter((j) => j.account === account && ACTIVE.includes(j.state)).length;
      const queued = all.filter((j) => j.state === "queued").sort(byQueue);
      const seen = new Set();
      const heads = [];
      queued.forEach((j) => {
        if (seen.has(j.account)) return;
        seen.add(j.account);
        if (busy(j.account) < cap) heads.push({ id: j.id, account: j.account, attempts: j.attempts });
      });
      return heads.slice(0, limit);
    },
    // Whole job rows read so far.
    jobReads: () => reads.jobs,
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
    currentAttempt: (job) =>
      clone([...attempts.values()].find((a) => a.job === job.id && a.attempt_number === job.attempts) || null),
    currentEnvelope: (job) => {
      const last = [...attempts.values()].find((a) => a.job === job.id && a.attempt_number === job.attempts);
      if (!last) return null;
      const found = [...envelopes.values()].find((e) => e.attempt === last.id);
      return found ? clone({ state: found.state, outcome_class: found.outcome_class, user_view: found.user_view }) : null;
    },
    // The same contract as the PocketBase store's PR 3 functions.
    currentEnvelopeRecord: (job) => clone(currentEnvelope(job)),
    saveEnvelopeView: (row) => {
      envelopes.get(row.id).user_view = clone(row.user_view);
      return clone(row);
    },
    linkGradedRow: (envelope, collection, rowId) => {
      const stored = envelopes.get(envelope.id);
      stored.graded_collection = collection;
      stored.graded_row = rowId;
    },
    itemRow: (collection, slug) => (items[collection] && items[collection].get(slug)) || null,
    ownsCampaign: (account, campaignId) => campaigns.get(campaignId) === account,
    // For the test server's record reads.
    campaignOwner: (campaignId) => campaigns.get(campaignId) || null,
    saveGradedRow: (collection, row) => {
      const saved = Object.assign(clone(row), { id: nextId() });
      graded[collection].set(saved.id, saved);
      return { id: saved.id };
    },
    getGradedRow: (collection, id) => (graded[collection] ? clone(graded[collection].get(id) || null) : null),
    saveRubricReview: (collection, row, review) => {
      graded[collection].get(row.id).rubric_review = clone(review);
    },
    reviewCommand: (account, fingerprint) => {
      const found = [...commands.values()].find((c) => c.account === account && c.operation === "review" &&
        c.fingerprint === fingerprint);
      return found ? { id: found.id } : null;
    },
    liveLeaseForCommand: (commandId, now) => admissionView.liveLeaseForCommand(commandId, now),
    jobStarted: (row) => {
      admissionCalls.push({ call: "jobStarted", job: row.id });
      if (admissionRules) admissionRules.jobStarted(admissionView, row.account, row.command_id, row.id);
    },
    jobEnded: (row, outcomeClass) => {
      admissionCalls.push({ call: "jobEnded", job: row.id, outcome_class: outcomeClass });
      if (admissionRules) admissionRules.jobEnded(admissionView, row.account, row.command_id, row.id, outcomeClass);
    },
    // The same filter and order as execution.js's.
    purgeable: (cutoff, limit) =>
      [...jobs.values()]
        .filter((j) => j.purpose === "scratch" && (
          (j.finished_at > 0 && j.finished_at <= cutoff && TERMINAL.includes(j.state)) ||
          ((j.state === "queued" || ACTIVE.includes(j.state)) && j.queued_at <= cutoff)))
        .sort((a, b) => a.finished_at - b.finished_at || a.queued_at - b.queued_at)
        .slice(0, limit)
        .map(clone),
    deleteEnvelopes: (jobId) => {
      for (const [id, e] of envelopes) if (e.job === jobId) envelopes.delete(id);
    },
    deleteCommandOf: (row) => {
      const found = [...commands.values()].find((c) => c.account === row.account && c.command_id === row.command_id);
      if (!found || found.job !== row.id) return;
      commands.delete(found.id);
      for (const [id, lease] of leases) if (lease.command === found.id) leases.delete(id);
    },
    // Its attempts cascade, as the relation's cascadeDelete does.
    deleteJob: (row) => {
      jobs.delete(row.id);
      for (const [id, a] of attempts) if (a.job === row.id) attempts.delete(id);
    },
  };
}

// The PocketBase globals execution.js reaches for while it loads.
function installGlobals(hooksDir) {
  class BadRequestError extends Error {}
  class UnauthorizedError extends Error {}
  class ForbiddenError extends Error {}
  class NotFoundError extends Error {}
  globalThis.BadRequestError = BadRequestError;
  globalThis.UnauthorizedError = UnauthorizedError;
  globalThis.ForbiddenError = ForbiddenError;
  globalThis.NotFoundError = NotFoundError;
  globalThis.$apis = { requestInfo: (ctx) => ctx.info };
  globalThis.__hooks = hooksDir;
  return { BadRequestError, UnauthorizedError, ForbiddenError, NotFoundError };
}

module.exports = { memoryStore, installGlobals };
