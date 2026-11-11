// An in-memory store with the PocketBase store's contract for
// pb_hooks/admission.js (ROUNDS-00A-L01 stage 3): one command per
// (account, command_id), one counter per (bucket, account, hour), unique
// lease token hashes, and leases deleted with their command. A command
// that enqueued an execution job (ROUNDS-00A-L03 PR 2) names it in `job`;
// the sweep leaves such a command, and the lease that is its job's charge,
// to the job.
//
// admission_runner.cjs runs the decisions on it by itself.
// execution_memory.cjs builds it over the maps it shares with the
// execution store, so the two hooks' decisions run together, as they do
// in one PocketBase transaction. The PocketBase store itself runs in the
// harness.

const crypto = require("crypto");

function newMaps() {
  let ids = 0;
  return {
    commands: new Map(),
    counters: new Map(),
    leases: new Map(),
    jobs: new Map(),
    nextId: () => `id${String(++ids).padStart(13, "0")}`,
  };
}

const clone = (row) => (row === null || row === undefined ? null : JSON.parse(JSON.stringify(row)));
const counterKey = (bucket, account, hour) => `${bucket}|${account}|${hour}`;
const live = (lease, now) => lease.expires_at > now;

function admissionMemoryStore(maps) {
  const { commands, counters, leases, jobs, nextId } = maps;
  const deleteLease = (id) => leases.delete(id);
  // A command that enqueued a job, which only the job ends.
  const holdsJob = (command) => Boolean(command && command.job);

  return {
    dump: () => ({
      commands: [...commands.values()].map(clone),
      counters: [...counters.values()].map(clone),
      leases: [...leases.values()].map(clone),
    }),
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
      // As PocketBase's save of the listed fields: the job link stays.
      const stored = commands.get(saved.id);
      if (stored && stored.job && !saved.job) saved.job = stored.job;
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
    leasesForCommand: (commandId) => [...leases.values()].filter((l) => l.command === commandId).map(clone),
    jobOf: (jobId) => {
      const job = jobs.get(jobId);
      if (!job) return null;
      return {
        id: job.id,
        state: job.state,
        outcome_class: job.outcome_class,
        attempts: job.attempts,
        attempts_started: job.attempts_started,
      };
    },
    liveLeaseForCommand: (commandId, now) => [...leases.values()].some((l) => l.command === commandId && live(l, now)),
    liveLeaseExpiry: (commandId, now) => {
      const rows = [...leases.values()].filter((l) => l.command === commandId && live(l, now));
      return rows.length > 0 ? Math.max(...rows.map((l) => l.expires_at)) : null;
    },
    liveLeases: (filter, now) => {
      const rows = [...leases.values()]
        .filter((l) => live(l, now) && l.counted === true)
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
      const due = [...commands.values()].filter((c) => c.state === "in_flight" && !holdsJob(c)).slice(0, limit);
      for (const command of due) {
        if ([...leases.values()].some((l) => l.command === command.id && live(l, now))) continue;
        command.state = "failed_infrastructure";
        command.result = null;
        repaired += 1;
      }
      return repaired;
    },
    deleteExpired: (now, oldestHour, limit) => {
      [...leases.values()]
        .filter((l) => l.expires_at <= now && !holdsJob(commands.get(l.command)))
        .slice(0, limit)
        .forEach((l) => deleteLease(l.id));
      [...commands.values()]
        .filter((c) => c.expires_at <= now && !holdsJob(c))
        .slice(0, limit)
        .forEach((c) => commands.delete(c.id));
      [...counters.entries()].filter(([, c]) => c.hour < oldestHour).slice(0, limit).forEach(([k]) => counters.delete(k));
    },
  };
}

module.exports = { newMaps, admissionMemoryStore };
