/// <reference path="../pb_data/types.d.ts" />

// AI provider custody (ROUNDS-14-L02 stage A): the only writer of
// ai_credentials and ai_provider_models, and of ai_providers' creates and
// updates (docs/security/server-writes.md).
//
// The runner calls the routes in ai_custody.pb.js with the caller's bearer
// and the runner key, ROUNDS_ADMISSION_SECRET; nginx and the Vite proxy
// answer /api/rounds/ai/ with 404, so a browser never reaches them. The
// account comes from the bearer, never from the body, and every read and
// write is of the caller's own rows, in one transaction a route.
//
// PocketBase never sees a provider key in the clear. The runner's keyring
// (backend/app/provider_gateway/keyring.py) wraps a key for its account,
// its provider, and the address it was entered for before it gets here,
// and only the runner opens one. So a create carries the provider id the
// runner bound the key to, and the runner computes each address.
//
// A saved key works only with the address it was entered for: an update
// that changes a provider's address asks for the key again
// (credential_required) unless it brings one. A key saved before this
// release (legacy-v0) names no address yet, so any change of its
// provider's kind or base URL asks for the key again until its first use
// rewraps it (convert).
//
// Answers, each {v, ...}:
//   no runner key               503 unconfigured, or 403 forbidden
//   a demo account's write      403 demo_not_permitted
//   malformed request           400 invalid_request
//   provider missing or another's  404 not_found, one answer for both
//   address changed, key kept   400 credential_required
//   provider id taken, or a
//   rewrap that lost a race     409 conflict
//
// The decisions take their store as an argument, so tests run them under
// node on plain objects (pocketbase/tests/test_ai_custody_hooks.py);
// pbStore() is the store over a PocketBase DAO.

const VERSION = "ai-custody/v1";
const PROVIDERS = "ai_providers";
const CREDENTIALS = "ai_credentials";
const MODELS = "ai_provider_models";

const RECORD_ID = /^[a-z0-9]{15}$/;
const KINDS = ["anthropic", "openai", "openai-compatible", "anthropic-compatible"];
const FIRST_PARTY = ["anthropic", "openai"];
const WRAP = "aad-v1";
const LEGACY_WRAP = "legacy-v0";
const KEY_VERSION = 1;
const BASE64 = /^[A-Za-z0-9+/]+={0,2}$/;
const NONCE = /^[A-Za-z0-9+/]{16}$/;
const CIPHERTEXT_MAX = 8192;
const HOST = /^[a-z0-9._:-]{1,253}$/;
const DIGEST = /^[0-9a-f]{64}$/;
// No control characters; lengths in characters.
const PLAIN = /^[^\x00-\x1f\x7f]+$/;
const LABEL_MAX = 200;
const BASE_URL_MAX = 2048;
const MODEL_MAX = 256;
// A provider's model list, and the providers an account lists.
const MODELS_MAX = 1000;
const PROVIDERS_MAX = 50;
const VERIFICATIONS = ["registry", "user-declared"];

// ---------------------------------------------------------------------------
// Answers
// ---------------------------------------------------------------------------

function error(status, code) {
  return { status, body: { v: VERSION, error: code } };
}

function ok(fields) {
  const body = { v: VERSION };
  Object.keys(fields).forEach((key) => {
    body[key] = fields[key];
  });
  return { status: 200, body };
}

const INVALID = error(400, "invalid_request");
const NOT_FOUND = error(404, "not_found");

// ---------------------------------------------------------------------------
// Checks
// ---------------------------------------------------------------------------

function only(data, allowed) {
  if (!data || typeof data !== "object" || Array.isArray(data)) return false;
  return Object.keys(data).every((key) => allowed.indexOf(key) >= 0);
}

function text(value, max) {
  return typeof value === "string" && value.length > 0 && value.length <= max && PLAIN.test(value);
}

function port(value) {
  return typeof value === "number" && Math.floor(value) === value && value >= 1 && value <= 65535;
}

function endpointOf(value) {
  if (!only(value, ["host", "port"])) return null;
  if (typeof value.host !== "string" || !HOST.test(value.host) || !port(value.port)) return null;
  return { host: value.host, port: value.port };
}

// A wrapped key as the runner sends it: an aad-v1 wrap, and the address
// it was entered for.
function credentialOf(value) {
  if (!only(value, ["wrap", "key_version", "ciphertext", "nonce", "host", "port"])) return null;
  if (value.wrap !== WRAP || value.key_version !== KEY_VERSION) return null;
  if (typeof value.ciphertext !== "string" || value.ciphertext.length > CIPHERTEXT_MAX || !BASE64.test(value.ciphertext)) {
    return null;
  }
  if (typeof value.nonce !== "string" || !NONCE.test(value.nonce)) return null;
  const at = endpointOf({ host: value.host, port: value.port });
  if (at === null) return null;
  return {
    wrap: WRAP,
    key_version: KEY_VERSION,
    ciphertext: value.ciphertext,
    nonce: value.nonce,
    host: at.host,
    port: at.port,
  };
}

// The provider fields a create or an update sets. A first-party kind
// keeps no base URL; its address is the provider's own.
function providerFields(data) {
  if (KINDS.indexOf(data.kind) < 0) return null;
  if (typeof data.label !== "string") return null;
  const label = data.label.trim();
  if (!text(label, LABEL_MAX)) return null;
  if (typeof data.base_url !== "string") return null;
  const baseUrl = data.base_url.trim();
  if (baseUrl !== "" && !text(baseUrl, BASE_URL_MAX)) return null;
  if (FIRST_PARTY.indexOf(data.kind) >= 0 && baseUrl !== "") return null;
  return { kind: data.kind, label, base_url: baseUrl };
}

function checkList(data) {
  return only(data || {}, []) ? {} : null;
}

function checkCreate(data) {
  if (!only(data, ["id", "kind", "label", "base_url", "credential"])) return null;
  if (typeof data.id !== "string" || !RECORD_ID.test(data.id)) return null;
  const fields = providerFields(data);
  if (fields === null) return null;
  let credential = null;
  if (data.credential !== undefined && data.credential !== null) {
    credential = credentialOf(data.credential);
    if (credential === null) return null;
  }
  return { id: data.id, fields, credential };
}

// key: "keep" the saved key, "clear" it, or a new one. endpoint is the
// address the runner computed for the new kind and base URL, or null when
// they name none (a compatible kind without a base URL).
function checkUpdate(data) {
  if (!only(data, ["provider", "kind", "label", "base_url", "endpoint", "key"])) return null;
  if (typeof data.provider !== "string" || !RECORD_ID.test(data.provider)) return null;
  const fields = providerFields(data);
  if (fields === null) return null;
  let endpoint = null;
  if (data.endpoint !== null) {
    endpoint = endpointOf(data.endpoint);
    if (endpoint === null) return null;
  }
  let key;
  if (data.key === "keep" || data.key === "clear") key = data.key;
  else {
    key = credentialOf(data.key);
    if (key === null) return null;
    // A new key is wrapped for the address the update sets.
    if (endpoint === null || key.host !== endpoint.host || key.port !== endpoint.port) return null;
  }
  return { provider: data.provider, fields, endpoint, key };
}

function checkModels(data) {
  if (!only(data, ["provider", "models", "verification", "replace"])) return null;
  if (typeof data.provider !== "string" || !RECORD_ID.test(data.provider)) return null;
  if (VERIFICATIONS.indexOf(data.verification) < 0 || typeof data.replace !== "boolean") return null;
  if (!Array.isArray(data.models) || data.models.length > MODELS_MAX) return null;
  const seen = {};
  const models = [];
  for (let i = 0; i < data.models.length; i += 1) {
    const m = data.models[i];
    if (!text(m, MODEL_MAX)) return null;
    if (!Object.prototype.hasOwnProperty.call(seen, m)) {
      seen[m] = true;
      models.push(m);
    }
  }
  models.sort();
  return { provider: data.provider, models, verification: data.verification, replace: data.replace };
}

function checkRead(data) {
  if (!only(data, ["provider"])) return null;
  if (typeof data.provider !== "string" || !RECORD_ID.test(data.provider)) return null;
  return { provider: data.provider };
}

// from: the SHA-256 of the legacy-v0 ciphertext and nonce the runner
// opened, joined by a colon, so a key changed since then wins.
function checkConvert(data) {
  if (!only(data, ["provider", "from", "credential"])) return null;
  if (typeof data.provider !== "string" || !RECORD_ID.test(data.provider)) return null;
  if (typeof data.from !== "string" || !DIGEST.test(data.from)) return null;
  const credential = credentialOf(data.credential);
  if (credential === null) return null;
  return { provider: data.provider, from: data.from, credential };
}

const CHECKS = {
  list: checkList,
  create: checkCreate,
  update: checkUpdate,
  models: checkModels,
  read: checkRead,
  convert: checkConvert,
};
const WRITES = ["create", "update", "models", "convert"];

// ---------------------------------------------------------------------------
// Decisions
// ---------------------------------------------------------------------------

// What the runner sees of a saved key: never its ciphertext, except to the
// read it opens it with.
function keyView(credential) {
  if (credential === null) return null;
  return {
    wrap: credential.wrap,
    status: credential.status,
    registered_host: credential.registered_host,
    registered_port: credential.registered_port,
  };
}

function providerView(row, credential, models) {
  return {
    id: row.id,
    kind: row.kind,
    label: row.label,
    base_url: row.base_url,
    created: row.created,
    has_key: credential !== null && credential.status === "active",
    key: keyView(credential),
    models: models.map((m) => ({ model: m.model, verification: m.verification })),
    models_cached_at: row.models_cached_at,
  };
}

// The caller's provider, or null for one that is missing or another's.
function owned(store, account, id) {
  const row = store.provider(id);
  return row !== null && row.user === account.id ? row : null;
}

function view(store, row) {
  return providerView(row, store.credential(row.id), store.models(row.id));
}

function list(store, account) {
  const rows = store.providers(account.id, PROVIDERS_MAX);
  return ok({ providers: rows.map((row) => view(store, row)) });
}

function newCredential(account, providerId, credential) {
  return {
    user: account.id,
    provider: providerId,
    wrap: credential.wrap,
    key_version: credential.key_version,
    ciphertext: credential.ciphertext,
    nonce: credential.nonce,
    registered_host: credential.host,
    registered_port: credential.port,
    status: "active",
    legacy_ciphertext: "",
    legacy_nonce: "",
  };
}

function create(store, account, input) {
  if (store.provider(input.id) !== null) return error(409, "conflict");
  if (input.credential !== null && input.fields.base_url === "" && FIRST_PARTY.indexOf(input.fields.kind) < 0) {
    // A compatible kind without a base URL has no address to bind a key to.
    return INVALID;
  }
  store.createProvider({
    id: input.id,
    user: account.id,
    kind: input.fields.kind,
    label: input.fields.label,
    base_url: input.fields.base_url,
  });
  if (input.credential !== null) store.saveCredential(input.id, newCredential(account, input.id, input.credential));
  return ok({ provider: view(store, store.provider(input.id)) });
}

// Whether a saved key may stay through this update: its address must be
// the one the update sets. A legacy-v0 key names none, so its provider's
// kind and base URL must stay as they are.
function keyMayStay(row, credential, input) {
  if (credential.registered_host) {
    return (
      input.endpoint !== null &&
      input.endpoint.host === credential.registered_host &&
      input.endpoint.port === credential.registered_port
    );
  }
  return input.fields.kind === row.kind && input.fields.base_url === row.base_url;
}

function update(store, account, input) {
  const row = owned(store, account, input.provider);
  if (row === null) return NOT_FOUND;
  const credential = store.credential(row.id);
  if (input.key === "keep" && credential !== null && !keyMayStay(row, credential, input)) {
    return error(400, "credential_required");
  }
  const moved = input.fields.kind !== row.kind || input.fields.base_url !== row.base_url;
  store.updateProvider(row.id, {
    kind: input.fields.kind,
    label: input.fields.label,
    base_url: input.fields.base_url,
    models_cached_at: moved ? "" : row.models_cached_at,
  });
  if (input.key === "clear") store.saveCredential(row.id, null);
  else if (input.key !== "keep") store.saveCredential(row.id, newCredential(account, row.id, input.key));
  // A model list belongs to the kind and address it came from.
  if (moved) store.replaceModels(row.id, account.id, [], null);
  return ok({ provider: view(store, store.provider(row.id)) });
}

function models(store, account, input) {
  const row = owned(store, account, input.provider);
  if (row === null) return NOT_FOUND;
  const current = store.models(row.id);
  const keep = current.filter((m) =>
    input.replace ? m.verification !== input.verification : true,
  );
  const have = {};
  keep.forEach((m) => {
    have[m.model] = true;
  });
  const next = keep.map((m) => ({ model: m.model, verification: m.verification }));
  input.models.forEach((m) => {
    if (!have[m]) {
      have[m] = true;
      next.push({ model: m, verification: input.verification });
    }
  });
  if (next.length > MODELS_MAX) return INVALID;
  store.replaceModels(row.id, account.id, next, input.replace && input.verification === "registry" ? store.now() : undefined);
  return ok({ provider: view(store, store.provider(row.id)) });
}

// The one answer that carries a saved key's ciphertext, for the runner to
// open it with.
function read(store, account, input) {
  const row = owned(store, account, input.provider);
  if (row === null) return NOT_FOUND;
  const credential = store.credential(row.id);
  return ok({
    provider: { id: row.id, kind: row.kind, label: row.label, base_url: row.base_url },
    credential: credential === null ? null : {
      wrap: credential.wrap,
      key_version: credential.key_version,
      ciphertext: credential.ciphertext,
      nonce: credential.nonce,
      registered_host: credential.registered_host,
      registered_port: credential.registered_port,
      status: credential.status,
    },
    models: store.models(row.id).map((m) => ({ model: m.model, verification: m.verification })),
  });
}

function convert(store, account, input) {
  const row = owned(store, account, input.provider);
  if (row === null) return NOT_FOUND;
  const credential = store.credential(row.id);
  if (
    credential === null ||
    credential.wrap !== LEGACY_WRAP ||
    credential.status !== "active" ||
    store.sha256(credential.ciphertext + ":" + credential.nonce) !== input.from
  ) {
    return error(409, "conflict");
  }
  const next = newCredential(account, row.id, input.credential);
  // The pair the move copied stays for its down step.
  next.legacy_ciphertext = credential.legacy_ciphertext;
  next.legacy_nonce = credential.legacy_nonce;
  store.saveCredential(row.id, next);
  return ok({ converted: true });
}

const DECISIONS = { list, create, update, models, read, convert };

// One route's decision, on a store that runs inside one transaction.
function run(store, account, action, data) {
  const check = CHECKS[action];
  if (!check) return INVALID;
  if (account.demo && WRITES.indexOf(action) >= 0) return error(403, "demo_not_permitted");
  const input = check(data);
  if (input === null) return INVALID;
  return DECISIONS[action](store, account, input);
}

// ---------------------------------------------------------------------------
// PocketBase
// ---------------------------------------------------------------------------

function pbStore(dao) {
  const collections = {};
  function collection(name) {
    if (!collections[name]) collections[name] = dao.findCollectionByNameOrId(name);
    return collections[name];
  }
  function first(name, filter, params) {
    const rows = dao.findRecordsByFilter(name, filter, "", 1, 0, params);
    return rows.length > 0 ? rows[0] : null;
  }
  function providerRow(record) {
    return {
      id: record.id,
      user: record.getString("user"),
      kind: record.getString("kind"),
      label: record.getString("label"),
      base_url: record.getString("base_url"),
      models_cached_at: record.getString("models_cached_at"),
      created: record.getString("created"),
    };
  }
  function credentialRecord(providerId) {
    return first(CREDENTIALS, "provider = {:provider}", { provider: providerId });
  }
  return {
    providers: (user, limit) =>
      dao.findRecordsByFilter(PROVIDERS, "user = {:user}", "created", limit, 0, { user }).map(providerRow),
    provider: (id) => {
      const record = first(PROVIDERS, "id = {:id}", { id });
      return record === null ? null : providerRow(record);
    },
    credential: (providerId) => {
      const record = credentialRecord(providerId);
      if (record === null) return null;
      return {
        wrap: record.getString("wrap"),
        key_version: record.getInt("key_version"),
        ciphertext: record.getString("ciphertext"),
        nonce: record.getString("nonce"),
        registered_host: record.getString("registered_host"),
        registered_port: record.getInt("registered_port"),
        status: record.getString("status"),
        legacy_ciphertext: record.getString("legacy_ciphertext"),
        legacy_nonce: record.getString("legacy_nonce"),
      };
    },
    models: (providerId) =>
      dao
        .findRecordsByFilter(MODELS, "provider = {:provider}", "model", MODELS_MAX, 0, { provider: providerId })
        .map((r) => ({ model: r.getString("model"), verification: r.getString("verification") })),
    createProvider: (fields) => {
      const record = new Record(collection(PROVIDERS));
      record.setId(fields.id);
      record.markAsNew();
      record.set("user", fields.user);
      record.set("kind", fields.kind);
      record.set("label", fields.label);
      record.set("base_url", fields.base_url);
      dao.saveRecord(record);
    },
    updateProvider: (id, fields) => {
      const record = dao.findRecordById(PROVIDERS, id);
      Object.keys(fields).forEach((key) => record.set(key, fields[key]));
      dao.saveRecord(record);
    },
    saveCredential: (providerId, fields) => {
      const record = credentialRecord(providerId);
      if (fields === null) {
        if (record !== null) dao.deleteRecord(record);
        return;
      }
      const target = record === null ? new Record(collection(CREDENTIALS)) : record;
      Object.keys(fields).forEach((key) => target.set(key, fields[key]));
      dao.saveRecord(target);
    },
    replaceModels: (providerId, user, rows, cachedAt) => {
      dao.findRecordsByFilter(MODELS, "provider = {:provider}", "", 0, 0, { provider: providerId })
        .forEach((r) => dao.deleteRecord(r));
      rows.forEach((m) => {
        const record = new Record(collection(MODELS));
        record.set("user", user);
        record.set("provider", providerId);
        record.set("model", m.model);
        record.set("verification", m.verification);
        dao.saveRecord(record);
      });
      if (cachedAt !== undefined && cachedAt !== null) {
        const provider = dao.findRecordById(PROVIDERS, providerId);
        provider.set("models_cached_at", cachedAt);
        dao.saveRecord(provider);
      }
    },
    sha256: (value) => $security.sha256(value),
    now: () => new Date().toISOString(),
  };
}

// One route. The account and its tier come from the bearer, never from the
// body, and every route needs the runner's key as well.
function handle(c, action) {
  const admission = require(`${__hooks}/admission.js`);
  const info = $apis.requestInfo(c);
  const record = info.authRecord;
  if (!record) throw new UnauthorizedError("Sign in to continue.");
  const refused = admission.runnerKeyError(info.headers, $os.getenv(admission.RUNNER_KEY_ENV));
  if (refused !== null) return c.json(refused.status, { v: VERSION, error: refused.body.error });
  const account = { id: record.id, demo: admission.tierOf(record) === "demo" };
  let out = null;
  try {
    $app.dao().runInTransaction((txDao) => {
      out = run(pbStore(txDao), account, action, info.data);
      // A refusal writes nothing.
      if (out.status !== 200) throw new Error("ai custody: refused");
    });
  } catch (err) {
    if (out === null || out.status === 200) throw err;
  }
  return c.json(out.status, out.body);
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    VERSION,
    KINDS,
    FIRST_PARTY,
    MODELS_MAX,
    PROVIDERS_MAX,
    checkCreate,
    checkUpdate,
    checkModels,
    checkRead,
    checkConvert,
    providerView,
    keyMayStay,
    run,
    pbStore,
    handle,
  };
}
