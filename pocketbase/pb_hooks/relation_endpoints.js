/// <reference path="../pb_data/types.d.ts" />
//
// Relation endpoint predicate (ROUNDS-00B-L02).
//
// Every typed relation listed in relation_endpoints.v1.json must point at a
// record owned by the same account as the row that carries it
// (target.user == row.user). This module is the single predicate used by
// relation_endpoints.pb.js for both the router middleware (which runs before
// PocketBase validates relation existence) and the record-level hooks (which
// re-check the resolved record). It is also require()d by the Node unit test,
// so the decision logic (idsOf, screen) must not touch any PocketBase global.
//
// The table and this module load from /pb/pb_hooks on the running instance.
// A denial answers with the same body PocketBase emits for its own rule
// failures, so a foreign id, a nonexistent id and a malformed id are
// indistinguishable per operation: create -> 400 "Failed to create record.",
// update -> 404 "The requested resource wasn't found." No id, owner or value
// is ever logged.

const OWNER_FIELD = "user";

function table() {
  if (typeof __hooks !== "undefined") {
    return require(`${__hooks}/relation_endpoints.v1.json`);
  }
  // Node unit test: resolve the table next to this module.
  return require("./relation_endpoints.v1.json");
}

function rowsFor(name) {
  return table().fields.filter((r) => r.collection === name);
}

// The relation ids PocketBase would read from one raw request value. Returns
// an array of ids, or null when the value cannot be an id (list) at all -- a
// malformed value, which must be denied rather than treated as empty.
function idsOf(value) {
  if (value === null || value === undefined) return [];
  if (typeof value === "string") {
    if (value === "") return [];
    if (value.indexOf("[") >= 0) {
      try {
        const parsed = JSON.parse(value);
        if (Array.isArray(parsed) && parsed.every((x) => typeof x === "string")) {
          return parsed.filter((x) => x !== "");
        }
      } catch (_) {
        return null;
      }
      return null;
    }
    return [value];
  }
  if (Array.isArray(value)) {
    const out = [];
    for (const x of value) {
      if (x === null || x === undefined || x === "") continue;
      if (typeof x !== "string") return null;
      out.push(x);
    }
    return out;
  }
  return null;
}

// Pure predicate shared by every layer. rawFor(field) returns the raw request
// values to screen for that field; lookup(target, id) returns the owner id of
// target/id or null when it does not exist. Returns the first offending field,
// or null when every relation is an owner-matching id. A request with no owner
// (anonymous, or an owner that cannot be resolved) fails every relation.
function screen(rows, owner, rawFor, lookup) {
  for (let i = 0; i < rows.length; i++) {
    const r = rows[i];
    const raws = rawFor(r.field);
    for (let k = 0; k < raws.length; k++) {
      const ids = idsOf(raws[k]);
      if (ids === null) return r.field;
      for (let j = 0; j < ids.length; j++) {
        if (!owner || lookup(r.target, ids[j]) !== owner) return r.field;
      }
    }
  }
  return null;
}

function ownerLookup(dao) {
  return (target, id) => {
    try {
      return dao.findRecordById(target, id).getString(OWNER_FIELD);
    } catch (_) {
      return null;
    }
  };
}

function deny(op, collection, field, actor) {
  // Disclosure-safe: no id, owner or value.
  console.log(
    JSON.stringify({
      v: "obs/v1",
      event: "relation_denied",
      service: "pocketbase",
      collection: collection,
      field: field,
      operation: op,
      actor: actor,
    }),
  );
  if (op === "create") throw new BadRequestError("Failed to create record.");
  throw new NotFoundError();
}

// Every raw value the request carries for one field: the plain key, the
// "field+" and "+field" append/prepend modifiers, from the JSON body and from
// a multipart form (including @jsonPayload). Screening all of them means an
// offending id in any encoding is denied; over-reading a request that is being
// denied anyway is harmless.
function candidates(c, info, field) {
  const out = [];
  const keys = [field, field + "+", "+" + field];
  const data = (info && info.data) || {};
  for (let i = 0; i < keys.length; i++) {
    if (Object.prototype.hasOwnProperty.call(data, keys[i])) out.push(data[keys[i]]);
  }
  let ct = "";
  try {
    ct = (c.request().header.get("Content-Type") || "").toLowerCase();
  } catch (_) {}
  if (ct.indexOf("multipart/form-data") === 0) {
    let form = null;
    try {
      form = c.request().postForm;
    } catch (_) {}
    if (form) {
      for (let i = 0; i < keys.length; i++) {
        const vs = form[keys[i]];
        if (vs) for (let j = 0; j < vs.length; j++) out.push(vs[j]);
      }
      const payloads = form["@jsonPayload"] || [];
      for (let p = 0; p < payloads.length; p++) {
        try {
          const obj = JSON.parse(payloads[p]);
          if (obj && typeof obj === "object") {
            for (let i = 0; i < keys.length; i++) {
              if (Object.prototype.hasOwnProperty.call(obj, keys[i])) out.push(obj[keys[i]]);
            }
          }
        } catch (_) {}
      }
    }
  }
  return out;
}

// Router middleware: runs before PocketBase validates relation existence, so a
// nonexistent or malformed id is answered with the uniform body here rather
// than PocketBase's field-level validation error.
function preCheck(c) {
  const method = c.request().method;
  const path = c.path();
  let op = "";
  if (method === "POST" && path === "/api/collections/:collection/records") op = "create";
  else if (method === "PATCH" && path === "/api/collections/:collection/records/:id") op = "update";
  else return;

  let collection;
  try {
    collection = $app.dao().findCollectionByNameOrId(c.pathParam("collection"));
  } catch (_) {
    return; // unknown collection: PocketBase answers 404 itself
  }
  const rows = rowsFor(collection.name);
  if (!rows.length) return;

  const info = $apis.requestInfo(c);
  const admin = !!info.admin;
  const rule = op === "create" ? collection.createRule : collection.updateRule;
  if (!admin && (rule === null || rule === undefined)) return; // null rule: PocketBase answers 403

  const actor = admin ? "admin" : info.authRecord ? "user" : "anonymous";

  // The owner the relations must match. A signed-in account is itself (the
  // create/update rules force row.user == auth.id). A superuser's row carries
  // whatever user the request names; on an update that does not resend user,
  // the existing row's owner stands.
  let owner = info.authRecord ? info.authRecord.id : "";
  if (admin) {
    const flat = [];
    const userRaws = candidates(c, info, OWNER_FIELD);
    for (let i = 0; i < userRaws.length; i++) {
      const ids = idsOf(userRaws[i]);
      if (ids) for (let j = 0; j < ids.length; j++) flat.push(ids[j]);
    }
    if (op === "update" && !flat.length) {
      try {
        owner = $app.dao().findRecordById(collection.name, c.pathParam("id")).getString(OWNER_FIELD);
      } catch (_) {
        return; // missing record: PocketBase answers 404 itself
      }
    } else {
      owner = flat.length ? flat[flat.length - 1] : "";
    }
  }

  const lookup = ownerLookup($app.dao());
  const bad = screen(rows, owner, (field) => candidates(c, info, field), lookup);
  if (bad) deny(op, collection.name, bad, actor);
}

// Record-level hook: the authoritative check on the resolved record, after
// PocketBase has merged every body encoding. Catches anything the raw parse
// missed and, on update, skips a relation left unchanged under the same owner.
function checkRecord(e, op) {
  const rows = rowsFor(e.collection.name);
  if (!rows.length) return;

  const info = $apis.requestInfo(e.httpContext);
  const actor = info.admin ? "admin" : info.authRecord ? "user" : "anonymous";
  const owner = e.record.getString(OWNER_FIELD);
  const original = op === "update" ? e.record.originalCopy() : null;
  const lookup = ownerLookup($app.dao());

  for (let i = 0; i < rows.length; i++) {
    const r = rows[i];
    const now = e.record.getStringSlice(r.field);
    if (original) {
      const before = original.getStringSlice(r.field);
      if (
        JSON.stringify(before) === JSON.stringify(now) &&
        original.getString(OWNER_FIELD) === owner
      ) {
        continue;
      }
    }
    for (let j = 0; j < now.length; j++) {
      if (!owner || lookup(r.target, now[j]) !== owner) {
        deny(op, e.collection.name, r.field, actor);
      }
    }
  }
}

module.exports = {
  OWNER_FIELD: OWNER_FIELD,
  table: table,
  rowsFor: rowsFor,
  idsOf: idsOf,
  screen: screen,
  preCheck: preCheck,
  checkRecord: checkRecord,
};
