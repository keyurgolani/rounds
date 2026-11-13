// Runs pb_hooks/ai_custody.js under node for test_ai_custody_hooks.py
// (ROUNDS-14-L02 stage A).
//
// The decisions run on an in-memory store with the PocketBase store's
// contract: providers by id, at most one saved key a provider, and a
// provider's models unique by name. Each step runs on a copy of the state
// and keeps it only when it answers 200, as the route's transaction does,
// so a refusal leaves the store as it was. The PocketBase store itself
// runs in the harness.
//
//   node ai_custody_runner.cjs <hooks dir> < program.json
//
// A program is {"state": {...}, "steps": [{"op", "account", "data"}]};
// the output is {"results": [...], "state": {...}}.

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const [hooksDir] = process.argv.slice(2);
const program = JSON.parse(fs.readFileSync(0, "utf8"));

globalThis.UnauthorizedError = class UnauthorizedError extends Error {};

const custody = require(path.join(hooksDir, "ai_custody.js"));

const sha256 = (text) => crypto.createHash("sha256").update(text, "utf8").digest("hex");
const clone = (value) => JSON.parse(JSON.stringify(value));

function storeOver(state) {
  state.providers = state.providers || {};
  state.credentials = state.credentials || {};
  state.models = state.models || {};
  let clock = Object.keys(state.providers).length;
  return {
    providers: (user, limit) =>
      Object.keys(state.providers)
        .map((id) => Object.assign({ id }, state.providers[id]))
        .filter((row) => row.user === user)
        .sort((a, b) => (a.created < b.created ? -1 : a.created > b.created ? 1 : 0))
        .slice(0, limit)
        .map(clone),
    provider: (id) => (state.providers[id] ? clone(Object.assign({ id }, state.providers[id])) : null),
    credential: (providerId) => (state.credentials[providerId] ? clone(state.credentials[providerId]) : null),
    models: (providerId) =>
      clone((state.models[providerId] || []).slice().sort((a, b) => (a.model < b.model ? -1 : a.model > b.model ? 1 : 0))),
    createProvider: (fields) => {
      if (state.providers[fields.id]) throw new Error("UNIQUE constraint failed: ai_providers.id");
      clock += 1;
      state.providers[fields.id] = {
        user: fields.user,
        kind: fields.kind,
        label: fields.label,
        base_url: fields.base_url,
        models_cached_at: "",
        created: "2026-11-13 00:00:" + String(clock).padStart(2, "0") + ".000Z",
      };
    },
    updateProvider: (id, fields) => {
      Object.keys(fields).forEach((key) => {
        state.providers[id][key] = fields[key];
      });
    },
    saveCredential: (providerId, fields) => {
      if (fields === null) delete state.credentials[providerId];
      else state.credentials[providerId] = clone(fields);
    },
    replaceModels: (providerId, user, rows, cachedAt) => {
      const names = rows.map((m) => m.model);
      if (new Set(names).size !== names.length) throw new Error("UNIQUE constraint failed: ai_provider_models");
      state.models[providerId] = rows.map((m) => ({ user, model: m.model, verification: m.verification }));
      if (cachedAt !== undefined && cachedAt !== null) state.providers[providerId].models_cached_at = cachedAt;
    },
    sha256,
    now: () => "2026-11-13T00:00:00.000Z",
  };
}

let state = clone(program.state || {});
const results = [];
for (const step of program.steps) {
  if (step.op === "sha256") {
    results.push(sha256(step.text));
    continue;
  }
  const draft = clone(state);
  const out = custody.run(storeOver(draft), step.account, step.op, step.data);
  if (out.status === 200) state = draft;
  results.push(out);
}
process.stdout.write(JSON.stringify({ results, state }));
