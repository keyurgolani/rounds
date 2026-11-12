/// <reference path="../pb_data/types.d.ts" />
// FORWARD FIX for the account-scope write lock - ROUNDS-00B-L01.
//
// This is a TEMPLATE, not a migration. To use it:
//   1. copy this file into pocketbase/pb_migrations/ with a fresh timestamp
//      AFTER the lock migration's;
//   2. replace __COLLECTION__ with the frozen collection;
//   3. deploy.
// It restores the server-derived ownership rules, identical to
// 1700006000_account_scope_rules.js, once the fix is ready.
//
// Do NOT use this to re-open resume_share_views: that collection is
// superuser-only by design (only the share viewer's admin-token insert writes
// it), so leave it locked.
//
// The two attempt collections are refused, whether __COLLECTION__ names
// one or holds its id: their rules are 1700008700_attempt_grade_rules.js's,
// which keep graded rows the server's (ROUNDS-00A-L03 PR 4), and the rules
// below would let clients write those again. A forward fix for either sets
// that migration's rules.
const KEEPS_ITS_OWN_RULES = ["ai_coding_attempts", "take_home_attempts"];

migrate(
  (db) => {
    const dao = new Dao(db);
    const collection = dao.findCollectionByNameOrId("__COLLECTION__");
    if (KEEPS_ITS_OWN_RULES.indexOf(collection.name) >= 0) {
      throw new Error(
        "restore_collection: " + collection.name + " takes 1700008700_attempt_grade_rules.js's rules, not these",
      );
    }
    collection.createRule = '@request.auth.id != "" && @request.data.user = @request.auth.id';
    collection.updateRule =
      'user = @request.auth.id && (@request.data.user:isset = false || @request.data.user = @request.auth.id)';
    dao.saveCollection(collection);
  },
  (_db) => {
    // Forward-only.
  },
);
