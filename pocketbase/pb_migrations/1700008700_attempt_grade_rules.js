/// <reference path="../pb_data/types.d.ts" />

// Graded attempt rows are the server's to write (ROUNDS-00A-L03 PR 4).
//
// The server writes a graded ai_coding_attempts or take_home_attempts row,
// with the envelope of the job that earned it, through the DAO, which API
// rules don't check (pb_hooks/execution.js). This changes the two rules a
// client writes through, on both collections, on top of the ownership
// clauses 1700006000_account_scope_rules.js set:
//   * create: a signed-in account's own row whose status is in-progress or
//     submitted, with no envelope;
//   * update: the account's own row while it isn't graded, with `user` left
//     out or resent as the caller, any status sent in-progress or
//     submitted, and no envelope.
// So a client can't create a graded row, move a row to graded, change a
// graded row at all, or give any row an envelope, and an in-progress row
// saves as before. The status clause names the values a client may send
// rather than the one it may not. List, view, and delete rules stay as they
// are, and no row is read or written.
//
// Both collections are looked up before either changes, and PocketBase
// applies a migration in one transaction, so a missing one changes nothing.
// The up step records the rules it replaces, the reverse journal, in the
// _params row PRIOR_KEY names, unless both collections already hold these,
// so a second run keeps the first record.
//
// down() keeps these rules and the record, as 1700006000 keeps its own, so
// reverting never reopens client writes to a graded row. A rule that turns
// out too tight is repaired by a forward fix (docs/operations.md,
// "Account-scope rules"). The rule table is docs/security/account-scope.v1.json,
// and the manifest pocketbase/migration-manifests/attempt-grade-rules-v1.json.

const COLLECTIONS = ["ai_coding_attempts", "take_home_attempts"];
// The _params row where the up step records the rules it replaced.
const PRIOR_KEY = "1700008700_attempt_grade_rules.js";

const SIGNED_IN = '@request.auth.id != ""';
const NO_ENVELOPE = "@request.data.envelope:isset = false";
const OPEN_STATUS = '@request.data.status = "in-progress" || @request.data.status = "submitted"';
const CALLER_OWNS = "@request.auth.id = @request.data.user";

const CREATE_RULE = [SIGNED_IN, NO_ENVELOPE, "(" + OPEN_STATUS + ")", CALLER_OWNS].join(" && ");
const UPDATE_RULE = [
  'status != "graded"',
  "user = @request.auth.id",
  NO_ENVELOPE,
  "(@request.data.status:isset = false || " + OPEN_STATUS + ")",
  "(@request.data.user:isset = false || " + CALLER_OWNS + ")",
].join(" && ");

migrate(
  (db) => {
    const dao = new Dao(db);
    // Both first, so a missing one changes neither.
    const collections = COLLECTIONS.map((name) => dao.findCollectionByNameOrId(name));
    const current = (c) => c.createRule === CREATE_RULE && c.updateRule === UPDATE_RULE;
    if (collections.every(current)) return;
    const replaced = collections.map((c) => ({ collection: c.name, create: c.createRule, update: c.updateRule }));
    collections.forEach((collection) => {
      collection.createRule = CREATE_RULE;
      collection.updateRule = UPDATE_RULE;
      dao.saveCollection(collection);
    });
    dao.saveParam(PRIOR_KEY, replaced);
  },
  (_db) => {
    // Keeps the rules and the record; see the header comment.
  },
);
