// Runs pb_hooks/legacy_snapshots.js under node for
// test_legacy_snapshot_hooks.py (ROUNDS-00A-L04, PR 2).
//
// The decisions run on an in-memory store with the PocketBase store's
// contract: resumes and variants by id, snapshots unique by (user,
// source_kind, source_id, content_checksum, materializer_digest), and
// admission commands by (account, command_id) through admission.js. A
// transaction runs on a copy and keeps it only when it returns, so a throw
// leaves the store as it was. The PocketBase store itself runs in the
// harness.
//
//   node legacy_snapshots_runner.cjs <hooks dir> < program.json
//
// A program is {"state": {...}, "steps": [...]}. Each step is one call
// ("create", "scan", "utf8Length", "canonical") with its arguments and the
// materializer's canned answers; the output is {"results": [...], "state":
// {...}}.

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const [hooksDir] = process.argv.slice(2);
const program = JSON.parse(fs.readFileSync(0, "utf8"));

globalThis.BadRequestError = class BadRequestError extends Error {};
globalThis.UnauthorizedError = class UnauthorizedError extends Error {};

const admission = require(path.join(hooksDir, "admission.js"));
const snapshots = require(path.join(hooksDir, "legacy_snapshots.js"));

const sha256 = (text) => crypto.createHash("sha256").update(text, "utf8").digest("hex");
const clone = (value) => JSON.parse(JSON.stringify(value));

function emptyState() {
  return { resumes: {}, variants: {}, users: {}, snapshots: [], commands: [], files: [] };
}

function storeOver(state, options) {
  let ids = state.commands.length;
  const commands = {
    findCommand: (account, commandId) =>
      clone(state.commands.find((c) => c.account === account && c.command_id === commandId) || null),
    saveCommand: (row) => {
      const saved = clone(row);
      if (!saved.id) {
        ids += 1;
        saved.id = "cmd" + String(ids).padStart(12, "0");
        state.commands.push(saved);
      } else {
        const i = state.commands.findIndex((c) => c.id === saved.id);
        state.commands[i] = saved;
      }
      return clone(saved);
    },
  };
  return {
    commands,
    findSource: (kind, id) => {
      const row = (kind === "resume" ? state.resumes : state.variants)[id];
      return row ? clone({ kind, id, ...row }) : null;
    },
    findResume: (id) => (state.resumes[id] ? clone({ id, ...state.resumes[id] }) : null),
    findSnapshot: (user, kind, id, sum, digest) => {
      const row = state.snapshots.find((s) => s.user === user && s.source_kind === kind && s.source_id === id &&
        s.content_checksum === sum && s.materializer_digest === digest);
      return row ? { id: row.id, content_checksum: row.content_checksum } : null;
    },
    quota: (user) => {
      const rows = state.snapshots.filter((s) => s.user === user);
      return { count: rows.length, bytes: rows.reduce((n, s) => n + s.size_bytes, 0) };
    },
    saveSnapshot: (fields, markup) => {
      // The file is stored first, then the row, as PocketBase's form does.
      state.files.push(fields.id);
      if (options.failSave) throw new Error("save failed");
      if (state.snapshots.some((s) => s.user === fields.user && s.source_kind === fields.source_kind &&
          s.source_id === fields.source_id && s.content_checksum === fields.content_checksum &&
          s.materializer_digest === fields.materializer_digest)) {
        throw new Error("UNIQUE constraint failed");
      }
      state.snapshots.push({ ...clone(fields), markup_sha256: sha256(markup) });
    },
    isDemo: (user) => Boolean(state.users[user] && state.users[user].is_demo),
    eachSource: (fn) => {
      Object.keys(state.resumes).sort().forEach((id) => fn(clone({ kind: "resume", id, ...state.resumes[id] })));
      Object.keys(state.variants).sort().forEach((id) => fn(clone({ kind: "variant", id, ...state.variants[id] })));
    },
  };
}

// The materializer's answers, in call order. "throw" is a transport error;
// {"ok": {...}} builds a contract-shaped snapshot for that markup.
function materializerFrom(answers, calls) {
  let i = 0;
  return (input) => {
    calls.push(clone(input));
    const answer = answers[Math.min(i, answers.length - 1)];
    i += 1;
    if (answer === "throw") throw new Error("connect: refused");
    if (answer && answer.ok) {
      const markup = answer.ok.markup;
      const body = {
        status: "ok",
        template_id: answer.ok.template_id || "modern",
        template_fallback: Boolean(answer.ok.template_fallback),
        design: answer.ok.design || {},
        data: answer.ok.data || { personalInfo: {} },
        markup,
        content_checksum: "sha256:" + sha256(markup),
        size_bytes: Buffer.byteLength(markup, "utf8"),
        font_families: answer.ok.font_families || [],
        sanitizer_version: "1.0.0",
        materializer_digest: answer.ok.digest || "sha256:" + "d".repeat(64),
      };
      Object.assign(body, answer.ok.override || {});
      return { status: 200, body };
    }
    return answer;
  };
}

let state = program.state ? Object.assign(emptyState(), clone(program.state)) : emptyState();
let nextId = 0;
const results = [];
for (const step of program.steps) {
  if (step.op === "utf8Length") {
    results.push({ ours: snapshots.utf8Length(step.text), node: Buffer.byteLength(step.text, "utf8") });
    continue;
  }
  if (step.op === "canonical") {
    results.push(snapshots.canonical(step.value));
    continue;
  }
  const calls = [];
  const logs = [];
  const discarded = [];
  const options = { failSave: Boolean(step.failSave) };
  const materialize = materializerFrom(step.materializer || [], calls);
  if (step.op === "create") {
    const deps = {
      gateOn: step.gateOn !== false,
      store: storeOver(state, options),
      transaction: (fn) => {
        const copy = clone(state);
        try {
          fn(storeOver(copy, options));
        } catch (err) {
          throw err;
        }
        state = copy;
      },
      materialize,
      sha256,
      newId: () => {
        nextId += 1;
        return "snap" + String(nextId).padStart(11, "0");
      },
      discard: (id) => discarded.push(id),
      admission,
      now: step.now || 1_800_000_000,
      log: (fields) => logs.push(fields),
    };
    // A step can change the store between the materializer call and the
    // transaction, as another tab's save would.
    if (step.changeDuringMaterialize) {
      const inner = deps.materialize;
      deps.materialize = (input) => {
        const out = inner(input);
        const change = step.changeDuringMaterialize;
        Object.assign(state[change.table][change.id], change.set);
        return out;
      };
    }
    const out = snapshots.create(deps, step.account, step.data);
    results.push({ out, calls, logs, discarded });
  } else if (step.op === "scan") {
    const report = snapshots.scan({ store: storeOver(state, options), materialize, sha256, commit: step.commit });
    results.push({ report, calls });
  } else if (step.op === "admit") {
    // What the runner's admit leaves for this command: one in-flight row.
    state.commands.push({
      id: "cmd" + String(state.commands.length + 1).padStart(12, "0"),
      account: step.account.id,
      command_id: step.command_id,
      operation: step.operation || "snapshot_create",
      fingerprint: "f".repeat(64),
      state: "in_flight",
      wall_seconds: 10,
      result: null,
      expires_at: (step.now || 1_800_000_000) + 24 * 3600,
    });
    results.push({ ok: true });
  } else {
    throw new Error("unknown op " + step.op);
  }
}
process.stdout.write(JSON.stringify({ results, state }));
