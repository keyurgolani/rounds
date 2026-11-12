/// <reference path="../pb_data/types.d.ts" />
//
// Older share links (ROUNDS-00B-L06 stage 1).
//
// 1700008500_legacy_share_migration.js turned off every share link made
// before it, and no client creates, changes, or deletes one: every write rule
// on resume_share_links is null. This holds every writer the app's Dao runs to
// the same, the admin UI and the hooks included: an older link's row changes
// only when "Get a new link" sets its replaced_by, from empty to a share
// capability, once (pb_hooks/share_secrets.js, in the same transaction as the
// capability). Rows leave only with their resume, variant, account, or the
// capability that replaced them. A migration writes with its own Dao and runs
// no model hooks.
//
// screenUpdate() is pure, so the Node unit test require()s it without
// PocketBase. Nothing is logged but a refusal's reason.

const RECORD_ID = /^[a-z0-9]{15}$/;
const REPLACED_BY = "replaced_by";
// Never compared: PocketBase sets it on every save.
const UPDATED = "updated";

// Why an update to an older link may not happen, or null. before and after
// map every field name to its value as text.
function screenUpdate(before, after) {
  const names = Object.keys(before).concat(Object.keys(after));
  for (let i = 0; i < names.length; i += 1) {
    const name = names[i];
    if (name === REPLACED_BY || name === UPDATED) continue;
    if ((before[name] || "") !== (after[name] || "")) return "field";
  }
  const was = before[REPLACED_BY] || "";
  const now = after[REPLACED_BY] || "";
  if (was === now) return null;
  if (was !== "" || !RECORD_ID.test(now)) return "replaced_by";
  return null;
}

function valuesOf(record) {
  const out = { created: record.getString("created") };
  record.collection().schema.fields().forEach((field) => {
    out[field.name] = record.getString(field.name);
  });
  return out;
}

function checkUpdate(e) {
  const after = e.model;
  const reason = screenUpdate(valuesOf(after.originalCopy()), valuesOf(after));
  if (reason === null) return;
  console.log(JSON.stringify({ v: "obs/v1", event: "share_link_refused", service: "pocketbase", reason }));
  throw new BadRequestError("Older share links can't be changed.");
}

module.exports = { screenUpdate: screenUpdate, checkUpdate: checkUpdate };
