/// <reference path="../pb_data/types.d.ts" />

// ai_providers' creates and updates are the server's (ROUNDS-14-L02
// stage A).
//
// From this release the runner creates and updates a provider through the
// AI hook routes (pb_hooks/ai_custody.js), which save through the DAO,
// where API rules don't apply. So this sets the collection's create and
// update rules to null, superuser only, and a client can no longer write a
// provider row itself. List, view, and delete stay the owner's, as
// 1700006000_account_scope_rules.js set them, and no row is read or
// written.
//
// The up step records the two rules it found, the reverse journal, in the
// _params row PRIOR_KEY names, and down() puts them back and removes the
// record, so the release before can write its providers again after a
// rollback (docs/operations.md, "AI provider keys"). A rule an operator's
// lock left null stays null both ways, and a run that would change
// nothing writes nothing, so a second run keeps the first record. The rule
// table is docs/security/account-scope.v1.json, and the manifest
// pocketbase/migration-manifests/ai-provider-writes-v1.json.

const COLLECTION = "ai_providers";
// The _params row where the up step records the rules it found.
const PRIOR_KEY = "1700008810_ai_provider_writes.js";

// A collection's rule as a plain string, or null. PocketBase's JS VM hands a
// rule out as a reference to the collection's own value, which an assignment
// writes through, so a rule is copied before the collection changes.
const rule = (value) => (value === null || value === undefined ? null : String(value));

migrate(
  (db) => {
    const dao = new Dao(db);
    const collection = dao.findCollectionByNameOrId(COLLECTION);
    const found = { collection: COLLECTION, create: rule(collection.createRule), update: rule(collection.updateRule) };
    if (found.create === null && found.update === null) return;
    collection.createRule = null;
    collection.updateRule = null;
    dao.saveCollection(collection);
    dao.saveParam(PRIOR_KEY, found);
  },
  (db) => {
    const dao = new Dao(db);
    const row = new DynamicModel({ value: "" });
    try {
      db.newQuery("SELECT CAST(value AS TEXT) AS value FROM _params WHERE key = {:key}").bind({ key: PRIOR_KEY }).one(row);
    } catch (_) {
      return; // the up step changed nothing
    }
    const found = JSON.parse(row.value);
    if (!found || found.collection !== COLLECTION) {
      throw new Error(PRIOR_KEY + " in _params isn't this migration's record; nothing changed");
    }
    const collection = dao.findCollectionByNameOrId(COLLECTION);
    collection.createRule = found.create;
    collection.updateRule = found.update;
    dao.saveCollection(collection);
    db.newQuery("DELETE FROM _params WHERE key = {:key}").bind({ key: PRIOR_KEY }).execute();
  },
);
