/// <reference path="../pb_data/types.d.ts" />

// Legacy Artifact Snapshot creation (ROUNDS-00A-L04, PR 2): the
// CreateLegacyArtifactSnapshot command and its dry-run scan.
//
// The only writer of legacy_artifact_snapshots
// (docs/security/server-writes.md). The runner's POST /api/pdf/snapshots
// forwards the caller's bearer, the runner key, and the request to
// POST /api/rounds/legacy-snapshots (legacy_snapshots.pb.js); nginx and the
// Vite proxy answer that path with 404, so a browser never reaches it.
// Every read is of records the caller owns, read through the DAO and
// checked here against the record's user (and a variant's parent's user),
// never with a superuser token. A snapshot is built only from those server
// reads: the request carries ids and the `updated` the caller saw, never
// markup, a template, or a design.
//
// Order (#4, Data and API contracts):
//   gate off                            503 route_disabled
//   no runner key                       503 unconfigured or 403 forbidden
//   malformed request                   400 invalid_request
//   completed (account, command_id)     its stored result, before any lookup
//   source missing or another's         404 not_found, one answer for both
//   updated differs from expected       409 conflict, nothing written
//   demo account                        ineligible demo_account
//   variant parent missing or foreign   ineligible parent_invalid
//   materializer error or timeout       503 materializer_unavailable
//   materializer says ineligible        ineligible with its reason
// then one transaction: read the source again, check the markup against
// its SHA-256, reuse a matching snapshot, check the account's quota (429
// snapshot_quota_exceeded), complete the admission_commands row, and save
// the record and its markup file last. Only created, reused, and
// ineligible complete the command; anything else leaves it for the
// runner's finish, so a same-key retry runs again.
//
// A handler requires this file itself, as with admission.js:
//
//   const snapshots = require(`${__hooks}/legacy_snapshots.js`);
//
// The decisions take their store and the materializer as arguments, so
// tests run them under node on plain objects
// (pocketbase/tests/test_legacy_snapshot_hooks.py); pbStore() is the store
// over a PocketBase DAO, which the harness exercises.

const VERSION = "legacy-snapshot/v1";
const SCAN_SCHEMA = "legacy-snapshot-scan/v1";
const OPERATION = "snapshot_create";
const SNAPSHOTS = "legacy_artifact_snapshots";
const GATE = "LEGACY_SNAPSHOT_CREATE";
const MATERIALIZER_URL_ENV = "MATERIALIZER_URL";
const MATERIALIZER_URL_DEFAULT = "http://materializer:4100";
const MATERIALIZE_TIMEOUT_S = 10;

// Proposed per-account caps, a lifetime count since rows leave only
// through #76's purge; the owner ratifies them (#4, owner input 3).
const QUOTA = { snapshots: 500, bytes: 200 * 1024 * 1024 };
const MAX_MARKUP_BYTES = 2 * 1024 * 1024;

const KINDS = ["resume", "variant"];
const RECORD_ID = /^[a-z0-9]{15}$/;
// PocketBase 0.22's `updated`: "2006-01-02 15:04:05.000Z".
const PB_DATETIME = /^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,9})?Z$/;
const CHECKSUM = /^sha256:[0-9a-f]{64}$/;
const SEMVER = /^[0-9]+\.[0-9]+\.[0-9]+$/;
const TEMPLATE_ID = /^[a-z0-9-]{1,64}$/;
const FONT_ID = /^[a-z0-9-]{1,64}$/;

// What the materializer can answer as ineligible, then the two this hook
// decides itself. The scan's report counts each of them.
const MATERIALIZER_REASONS = ["design_out_of_domain", "data_malformed", "data_too_large", "markup_unsafe"];
const REASONS = MATERIALIZER_REASONS.concat(["parent_invalid", "demo_account"]).sort();

// ---------------------------------------------------------------------------
// Answers
// ---------------------------------------------------------------------------

function error(status, code) {
  return { status, body: { v: VERSION, error: code } };
}

// The body the runner answers, which the command keeps for replay as it is.
function outcome(status, kind, fields) {
  const body = { status: kind, snapshot_id: null, content_checksum: null };
  Object.keys(fields || {}).forEach((key) => {
    body[key] = fields[key];
  });
  return { status, body };
}

// ---------------------------------------------------------------------------
// Checks
// ---------------------------------------------------------------------------

function only(data, allowed) {
  if (!data || typeof data !== "object" || Array.isArray(data)) return false;
  return Object.keys(data).every((key) => allowed.indexOf(key) >= 0);
}

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

// The checked request, or null when it is malformed.
function checkCreate(data, commandPattern) {
  if (!only(data, ["source_kind", "source_id", "expected_updated", "command_id"])) return null;
  if (KINDS.indexOf(data.source_kind) < 0) return null;
  if (typeof data.source_id !== "string" || !RECORD_ID.test(data.source_id)) return null;
  if (typeof data.expected_updated !== "string" || data.expected_updated.length > 40 ||
      !PB_DATETIME.test(data.expected_updated)) return null;
  const commandId = data.command_id === undefined || data.command_id === null ? null : data.command_id;
  if (commandId !== null && (typeof commandId !== "string" || !commandPattern.test(commandId))) return null;
  return {
    source_kind: data.source_kind,
    source_id: data.source_id,
    expected_updated: data.expected_updated,
    command_id: commandId,
  };
}

// UTF-8 byte length, a lone surrogate counting as U+FFFD (3 bytes), as the
// materializer's well-formed string encodes.
function utf8Length(text) {
  let n = 0;
  for (let i = 0; i < text.length; i += 1) {
    const c = text.charCodeAt(i);
    if (c < 0x80) n += 1;
    else if (c < 0x800) n += 2;
    else if (c >= 0xd800 && c <= 0xdbff && i + 1 < text.length &&
             text.charCodeAt(i + 1) >= 0xdc00 && text.charCodeAt(i + 1) <= 0xdfff) {
      n += 4;
      i += 1;
    } else n += 3;
  }
  return n;
}

// What the materializer answered, as one of
//   { kind: "ok", snapshot }       a snapshot that passed every check here
//   { kind: "ineligible", reason }
//   { kind: "unavailable", why }   an error, a timeout, or an answer that
//                                  isn't the contract's (logged, never shown)
function readMaterialized(answer, sha256) {
  if (!answer || typeof answer.status !== "number") return { kind: "unavailable", why: "no_answer" };
  const body = answer.body;
  // The materializer refuses a body over its cap; that source is too large.
  if (answer.status === 413) return { kind: "ineligible", reason: "data_too_large" };
  if (answer.status !== 200 || !isObject(body)) return { kind: "unavailable", why: "status" };
  if (body.status === "ineligible") {
    return MATERIALIZER_REASONS.indexOf(body.reason) >= 0
      ? { kind: "ineligible", reason: body.reason }
      : { kind: "unavailable", why: "reason" };
  }
  if (body.status !== "ok") return { kind: "unavailable", why: "status" };
  const markup = body.markup;
  if (typeof markup !== "string" || markup.length === 0) return { kind: "unavailable", why: "shape" };
  if (typeof body.content_checksum !== "string" || !CHECKSUM.test(body.content_checksum)) {
    return { kind: "unavailable", why: "shape" };
  }
  // The markup is checked against its checksum here, so a stored snapshot
  // always hashes to its content_checksum.
  if ("sha256:" + sha256(markup) !== body.content_checksum) return { kind: "unavailable", why: "integrity" };
  const size = utf8Length(markup);
  if (body.size_bytes !== size || size < 1) return { kind: "unavailable", why: "integrity" };
  if (size > MAX_MARKUP_BYTES) return { kind: "ineligible", reason: "data_too_large" };
  if (typeof body.materializer_digest !== "string" || !CHECKSUM.test(body.materializer_digest) ||
      typeof body.sanitizer_version !== "string" || !SEMVER.test(body.sanitizer_version) ||
      typeof body.template_id !== "string" || !TEMPLATE_ID.test(body.template_id) ||
      typeof body.template_fallback !== "boolean" ||
      !isObject(body.design) || !isObject(body.data) ||
      !Array.isArray(body.font_families) ||
      !body.font_families.every((f) => typeof f === "string" && FONT_ID.test(f))) {
    return { kind: "unavailable", why: "shape" };
  }
  return {
    kind: "ok",
    snapshot: {
      template_id: body.template_id,
      template_fallback: body.template_fallback,
      design: body.design,
      data: body.data,
      markup,
      content_checksum: body.content_checksum,
      materializer_digest: body.materializer_digest,
      sanitizer_version: body.sanitizer_version,
      font_families: body.font_families.slice(),
      size_bytes: size,
    },
  };
}

// The materializer's input for a source: a resume renders with its own
// template and design, a variant with its parent's.
function materializerInput(source, parent) {
  const owner = parent || source;
  return {
    template_id: typeof owner.template_id === "string" && owner.template_id !== "" ? owner.template_id : null,
    design: owner.design === undefined ? null : owner.design,
    data: source.data === undefined ? null : source.data,
  };
}

// ---------------------------------------------------------------------------
// CreateLegacyArtifactSnapshot
// ---------------------------------------------------------------------------

// deps:
//   gateOn        whether LEGACY_SNAPSHOT_CREATE is enabled
//   store         reads outside a transaction (findSource, findResume)
//   transaction   (fn) => runs fn(txStore) in one transaction; throws to roll back
//   materialize   (input) => { status, body }, throws on a transport error
//   sha256        (text) => hex over the text's UTF-8 bytes
//   newId         () => a fresh 15-character record id
//   discard       (id) => removes any file stored for a record id that was
//                 never committed
//   admission     admission.js (completedResult, completeCommand, COMMAND_ID)
//   now           seconds
//   log           (fields) => one content-free metric line
// account: { id, demo }
function create(deps, account, data) {
  const log = deps.log || (() => {});
  if (!deps.gateOn) {
    log({ outcome: "disabled" });
    return error(503, "route_disabled");
  }
  const input = checkCreate(data, deps.admission.COMMAND_ID);
  if (input === null) {
    log({ outcome: "invalid" });
    return error(400, "invalid_request");
  }

  if (input.command_id !== null) {
    const kept = deps.admission.completedResult(deps.store.commands, account, input.command_id, deps.now);
    if (kept !== null) {
      log({ outcome: "replayed" });
      return kept;
    }
  }

  const source = deps.store.findSource(input.source_kind, input.source_id);
  if (source === null || source.user !== account.id) {
    log({ outcome: "not_found" });
    return error(404, "not_found");
  }
  if (source.updated !== input.expected_updated) {
    log({ outcome: "conflict" });
    return outcome(409, "conflict");
  }

  // An ineligible source writes no snapshot; its command completes, so a
  // retry with the same key gets the same answer.
  const finishIneligible = (reason) => {
    const result = outcome(200, "ineligible", { reason });
    if (input.command_id !== null) {
      try {
        deps.transaction((tx) => {
          deps.admission.completeCommand(tx.commands, account, input.command_id, OPERATION, result);
        });
      } catch (err) {
        log({ outcome: "unavailable", why: "transaction" });
        return error(503, "unavailable");
      }
    }
    log({ outcome: "ineligible", reason });
    return result;
  };

  if (account.demo) return finishIneligible("demo_account");

  let parent = null;
  if (input.source_kind === "variant") {
    parent = typeof source.resume === "string" && RECORD_ID.test(source.resume)
      ? deps.store.findResume(source.resume)
      : null;
    if (parent === null || parent.user !== account.id) return finishIneligible("parent_invalid");
  }

  let answer = null;
  const started = Date.now();
  try {
    answer = deps.materialize(materializerInput(source, parent));
  } catch (err) {
    answer = null;
  }
  const materializeMs = Date.now() - started;
  const read = readMaterialized(answer, deps.sha256);
  if (read.kind === "unavailable") {
    log({ outcome: "materializer_unavailable", why: read.why, materialize_ms: materializeMs });
    return error(503, "materializer_unavailable");
  }
  if (read.kind === "ineligible") return finishIneligible(read.reason);

  const snapshot = read.snapshot;
  let out = null;
  let pendingId = null;
  try {
    deps.transaction((tx) => {
      // The source may have changed while the materializer ran.
      const again = tx.findSource(input.source_kind, input.source_id);
      if (again === null || again.user !== account.id) {
        out = error(404, "not_found");
        return;
      }
      if (again.updated !== input.expected_updated) {
        out = outcome(409, "conflict");
        return;
      }
      if (parent !== null) {
        const parentAgain = tx.findResume(parent.id);
        if (parentAgain === null || parentAgain.user !== account.id || parentAgain.updated !== parent.updated) {
          out = outcome(409, "conflict");
          return;
        }
      }

      const existing = tx.findSnapshot(account.id, input.source_kind, input.source_id, snapshot.content_checksum,
        snapshot.materializer_digest);
      if (existing !== null) {
        out = outcome(200, "reused", { snapshot_id: existing.id, content_checksum: existing.content_checksum });
        deps.admission.completeCommand(tx.commands, account, input.command_id, OPERATION, out);
        return;
      }

      const used = tx.quota(account.id);
      if (used.count + 1 > QUOTA.snapshots || used.bytes + snapshot.size_bytes > QUOTA.bytes) {
        out = error(429, "snapshot_quota_exceeded");
        return;
      }

      const id = deps.newId();
      const result = outcome(201, "created", { snapshot_id: id, content_checksum: snapshot.content_checksum });
      deps.admission.completeCommand(tx.commands, account, input.command_id, OPERATION, result);
      // The record and its file are saved last, so nothing after them can
      // fail the transaction once the file is stored.
      pendingId = id;
      tx.saveSnapshot({
        id,
        user: account.id,
        source_kind: input.source_kind,
        source_id: input.source_id,
        source_updated: again.updated,
        parent_id: parent === null ? "" : parent.id,
        parent_updated: parent === null ? "" : parent.updated,
        template_id: snapshot.template_id,
        template_fallback: snapshot.template_fallback,
        design: snapshot.design,
        data: snapshot.data,
        content_checksum: snapshot.content_checksum,
        materializer_digest: snapshot.materializer_digest,
        sanitizer_version: snapshot.sanitizer_version,
        font_families: snapshot.font_families,
        size_bytes: snapshot.size_bytes,
      }, snapshot.markup);
      out = result;
    });
  } catch (err) {
    // Nothing committed; a file stored for the record that never was goes too.
    if (pendingId !== null && deps.discard) deps.discard(pendingId);
    log({ outcome: "unavailable", why: "transaction" });
    return error(503, "unavailable");
  }

  if (out.status === 201) log({ outcome: "created", bytes: snapshot.size_bytes, materialize_ms: materializeMs });
  else if (out.status === 200) log({ outcome: "reused", materialize_ms: materializeMs });
  else if (out.status === 409) log({ outcome: "conflict" });
  else if (out.status === 429) log({ outcome: "quota_exceeded" });
  else log({ outcome: "not_found" });
  return out;
}

// ---------------------------------------------------------------------------
// The dry-run scan
// ---------------------------------------------------------------------------

// Canonical JSON: keys sorted at every level, no whitespace, so the report's
// checksum can be recomputed (python -m app.legacy_receipt).
function canonical(value) {
  if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
  if (isObject(value)) {
    return "{" + Object.keys(value).sort().map((key) => JSON.stringify(key) + ":" + canonical(value[key])).join(",") + "}";
  }
  return JSON.stringify(value);
}

function zeroReasons() {
  const out = {};
  REASONS.forEach((reason) => {
    out[reason] = 0;
  });
  return out;
}

// Runs the command's decisions over every resume and variant and writes
// nothing. deps:
//   store         eachSource((source) => void) over resumes then variants,
//                 each { kind, id, user, ...fields } in id order;
//                 findResume(id); isDemo(userId)
//   materialize   as in create()
//   sha256        as in create()
//   commit        the commit the operator names
// The report holds counts by reason, by kind, and by account pseudonym
// (acct-01, ... in scan order), the materializer digest, the commit, and
// its own SHA-256 over its canonical JSON. No id, name, or content.
function scan(deps) {
  const totals = { sources: 0, resumes: 0, variants: 0, eligible: 0, ineligible: 0, unavailable: 0 };
  const byReason = zeroReasons();
  const accounts = {};
  const labels = {};
  let digest = null;
  let sanitizer = null;
  let mixed = false;

  function account(user) {
    if (!Object.prototype.hasOwnProperty.call(labels, user)) {
      const n = Object.keys(labels).length + 1;
      labels[user] = "acct-" + (n < 10 ? "0" + n : String(n));
      accounts[labels[user]] = { sources: 0, eligible: 0, ineligible: 0, unavailable: 0, by_reason: zeroReasons() };
    }
    return accounts[labels[user]];
  }

  function count(row, result, reason) {
    totals[result] += 1;
    row[result] += 1;
    if (reason) {
      byReason[reason] += 1;
      row.by_reason[reason] += 1;
    }
  }

  deps.store.eachSource((source) => {
    totals.sources += 1;
    totals[source.kind === "resume" ? "resumes" : "variants"] += 1;
    const row = account(source.user);
    row.sources += 1;
    if (deps.store.isDemo(source.user)) {
      count(row, "ineligible", "demo_account");
      return;
    }
    let parent = null;
    if (source.kind === "variant") {
      parent = typeof source.resume === "string" && RECORD_ID.test(source.resume)
        ? deps.store.findResume(source.resume)
        : null;
      if (parent === null || parent.user !== source.user) {
        count(row, "ineligible", "parent_invalid");
        return;
      }
    }
    let answer = null;
    try {
      answer = deps.materialize(materializerInput(source, parent));
    } catch (err) {
      answer = null;
    }
    const read = readMaterialized(answer, deps.sha256);
    if (answer && isObject(answer.body) && typeof answer.body.materializer_digest === "string") {
      if (digest === null) digest = answer.body.materializer_digest;
      else if (digest !== answer.body.materializer_digest) mixed = true;
      if (typeof answer.body.sanitizer_version === "string" && sanitizer === null) {
        sanitizer = answer.body.sanitizer_version;
      }
    }
    if (read.kind === "ok") count(row, "eligible");
    else if (read.kind === "ineligible") count(row, "ineligible", read.reason);
    else count(row, "unavailable");
  });

  const report = {
    schema: SCAN_SCHEMA,
    commit: typeof deps.commit === "string" && deps.commit !== "" ? deps.commit : "unknown",
    // Every source rendered by one materializer build, or the report says
    // it can't be trusted as one inventory.
    materializer_digest: digest === null ? "absent" : (mixed ? "mixed" : digest),
    sanitizer_version: sanitizer === null ? "absent" : sanitizer,
    complete: totals.unavailable === 0 && !mixed,
    quota: { snapshots: QUOTA.snapshots, bytes: QUOTA.bytes },
    totals,
    by_reason: byReason,
    accounts,
  };
  report.checksum = "sha256:" + deps.sha256(canonical(report));
  return report;
}

// ---------------------------------------------------------------------------
// PocketBase
// ---------------------------------------------------------------------------

function json(record, field) {
  const raw = record.getString(field);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch (err) {
    return null;
  }
}

function sourceOf(record, kind) {
  const out = {
    kind,
    id: record.id,
    user: record.getString("user"),
    updated: record.getString("updated"),
    data: json(record, "data"),
  };
  if (kind === "resume") {
    out.template_id = record.getString("template_id");
    out.design = json(record, "design");
  } else {
    out.resume = record.getString("resume");
  }
  return out;
}

function pbStore(dao) {
  const admission = require(`${__hooks}/admission.js`);
  function byId(collection, id) {
    try {
      return dao.findRecordById(collection, id);
    } catch (err) {
      return null;
    }
  }
  function resume(id) {
    const record = byId("resumes", id);
    if (record === null) return null;
    return {
      id: record.id,
      user: record.getString("user"),
      updated: record.getString("updated"),
      template_id: record.getString("template_id"),
      design: json(record, "design"),
    };
  }
  return {
    commands: admission.pbStore(dao),
    findSource: (kind, id) => {
      const record = byId(kind === "resume" ? "resumes" : "resume_variants", id);
      return record === null ? null : sourceOf(record, kind);
    },
    findResume: resume,
    findSnapshot: (user, kind, id, checksum, digest) => {
      try {
        const record = dao.findFirstRecordByFilter(
          SNAPSHOTS,
          "user = {:user} && source_kind = {:kind} && source_id = {:id} && content_checksum = {:sum} && " +
            "materializer_digest = {:digest}",
          { user, kind, id, sum: checksum, digest },
        );
        return { id: record.id, content_checksum: record.getString("content_checksum") };
      } catch (err) {
        return null;
      }
    },
    quota: (user) => {
      const row = new DynamicModel({ n: 0, b: 0 });
      dao.db()
        .newQuery("SELECT COUNT(*) AS n, COALESCE(SUM(size_bytes), 0) AS b FROM " + SNAPSHOTS + " WHERE user = {:user}")
        .bind({ user })
        .one(row);
      return { count: row.n, bytes: row.b };
    },
    saveSnapshot: (fields, markup) => {
      const collection = dao.findCollectionByNameOrId(SNAPSHOTS);
      const record = new Record(collection);
      record.setId(fields.id);
      record.markAsNew();
      const form = new RecordUpsertForm($app, record);
      form.setDao(dao);
      const data = {};
      Object.keys(fields).forEach((key) => {
        if (key !== "id") data[key] = fields[key];
      });
      form.loadData(data);
      form.addFiles("markup", $filesystem.fileFromBytes(markup, "snapshot.html"));
      form.submit();
    },
    isDemo: (() => {
      const seen = {};
      return (userId) => {
        if (!Object.prototype.hasOwnProperty.call(seen, userId)) {
          const record = byId("users", userId);
          seen[userId] = record !== null && admission.tierOf(record) === "demo";
        }
        return seen[userId];
      };
    })(),
    eachSource: (fn) => {
      const BATCH = 200;
      [["resumes", "resume"], ["resume_variants", "variant"]].forEach((pair) => {
        for (let offset = 0; ; offset += BATCH) {
          const rows = dao.findRecordsByFilter(pair[0], "id != ''", "id", BATCH, offset);
          rows.forEach((record) => fn(sourceOf(record, pair[1])));
          if (rows.length < BATCH) break;
        }
      });
    },
  };
}

function materializerUrl() {
  const raw = ($os.getenv(MATERIALIZER_URL_ENV) || "").trim();
  const url = raw === "" ? MATERIALIZER_URL_DEFAULT : raw;
  if (!/^https?:\/\/[A-Za-z0-9.-]+(:[0-9]{1,5})?$/.test(url)) {
    throw new Error(MATERIALIZER_URL_ENV + " must be an http(s) origin with no path");
  }
  return url;
}

function materializeOver(url) {
  return (input) => {
    const res = $http.send({
      url: url + "/v1/materialize",
      method: "POST",
      body: JSON.stringify(input),
      headers: { "content-type": "application/json" },
      timeout: MATERIALIZE_TIMEOUT_S,
    });
    let body = null;
    try {
      body = res.json;
    } catch (err) {
      body = null;
    }
    return { status: res.statusCode, body };
  };
}

function discardFiles(id) {
  let fs = null;
  try {
    const collection = $app.dao().findCollectionByNameOrId(SNAPSHOTS);
    fs = $app.newFilesystem();
    fs.deletePrefix(collection.baseFilesPath() + "/" + id + "/");
  } catch (err) {
    console.error(JSON.stringify({ v: "obs/v1", event: "legacy_snapshot", service: "pocketbase", outcome: "discard_failed" }));
  } finally {
    if (fs !== null) fs.close();
  }
}

function emit(fields) {
  const line = { v: "obs/v1", event: "legacy_snapshot", service: "pocketbase" };
  Object.keys(fields).forEach((key) => {
    line[key] = fields[key];
  });
  console.log(JSON.stringify(line));
}

function gateOn() {
  const gates = require(`${__hooks}/gates.js`);
  const env = {};
  gates.envKeys().forEach((key) => {
    env[key] = $os.getenv(key);
  });
  return gates.resolve(GATE, env).value === "enabled";
}

// POST /api/rounds/legacy-snapshots. The account and its tier come from the
// bearer, never from the body, and the call needs the runner's key.
function handle(c) {
  const admission = require(`${__hooks}/admission.js`);
  const info = $apis.requestInfo(c);
  const record = info.authRecord;
  if (!record) throw new UnauthorizedError("Sign in to continue.");
  const on = gateOn();
  if (on) {
    const refused = admission.runnerKeyError(info.headers, $os.getenv(admission.RUNNER_KEY_ENV));
    if (refused !== null) return c.json(refused.status, { v: VERSION, error: refused.body.error });
  }
  let url = null;
  if (on) {
    try {
      url = materializerUrl();
    } catch (err) {
      emit({ outcome: "materializer_unavailable", why: "config" });
      return c.json(503, { v: VERSION, error: "materializer_unavailable" });
    }
  }
  const out = create(
    {
      gateOn: on,
      store: pbStore($app.dao()),
      transaction: (fn) => $app.dao().runInTransaction((txDao) => fn(pbStore(txDao))),
      materialize: url === null ? () => null : materializeOver(url),
      sha256: (text) => $security.sha256(text),
      newId: () => $security.randomStringWithAlphabet(15, "abcdefghijklmnopqrstuvwxyz0123456789"),
      discard: discardFiles,
      admission,
      now: admission.nowSeconds(),
      log: emit,
    },
    { id: record.id, demo: admission.tierOf(record) === "demo" },
    info.data,
  );
  return c.json(out.status, out.body);
}

// pocketbase legacy-snapshot-scan --out PATH [--commit SHA]
//
// The operator's dry run before turning LEGACY_SNAPSHOT_CREATE on: writes
// the report (mode 0600) outside pb_data and prints its counts and
// checksum. It writes nothing to the database and needs only the
// materializer, whatever the gate says.
function scanCommand(args) {
  let out = "";
  let commit = $os.getenv("ROUNDS_COMMIT") || "";
  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === "--out" && i + 1 < args.length) out = args[++i];
    else if (arg.indexOf("--out=") === 0) out = arg.slice(6);
    else if (arg === "--commit" && i + 1 < args.length) commit = args[++i];
    else if (arg.indexOf("--commit=") === 0) commit = arg.slice(9);
    // PocketBase's own flags (--dir and the rest) are read before this runs.
  }
  if (out === "") throw new Error("legacy-snapshot-scan: give --out PATH for the report");
  if (!/^\/[^\0]*$/.test(out)) throw new Error("legacy-snapshot-scan: --out must be an absolute path");
  const dataDir = $app.dataDir().replace(/\/+$/, "") + "/";
  if (out.indexOf(dataDir) === 0) {
    throw new Error("legacy-snapshot-scan: write the report outside pb_data, so backups never carry it");
  }
  if (commit !== "" && !/^[0-9A-Za-z._-]{1,64}$/.test(commit)) {
    throw new Error("legacy-snapshot-scan: --commit takes a commit or tag name");
  }
  const report = scan({
    store: pbStore($app.dao()),
    materialize: materializeOver(materializerUrl()),
    sha256: (text) => $security.sha256(text),
    commit,
  });
  $os.writeFile(out, JSON.stringify(report, null, 2) + "\n", 0o600);
  console.log(JSON.stringify({
    v: "obs/v1",
    event: "legacy_snapshot_scan",
    service: "pocketbase",
    complete: report.complete,
    totals: report.totals,
    by_reason: report.by_reason,
    checksum: report.checksum,
  }));
}

module.exports = {
  VERSION,
  SCAN_SCHEMA,
  OPERATION,
  QUOTA,
  MAX_MARKUP_BYTES,
  REASONS,
  MATERIALIZER_REASONS,
  MATERIALIZE_TIMEOUT_S,
  checkCreate,
  utf8Length,
  readMaterialized,
  materializerInput,
  create,
  canonical,
  scan,
  pbStore,
  handle,
  scanCommand,
};
