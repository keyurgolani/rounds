/// <reference path="../pb_data/types.d.ts" />
// EMERGENCY WRITE LOCK (account-scope lever) - ROUNDS-00B-L01.
//
// This is a TEMPLATE, not a migration. Nothing here runs on its own. To use it:
//   1. copy this file into pocketbase/pb_migrations/ with a fresh timestamp,
//      e.g. `<unix-seconds>_lock_<collection>.js`;
//   2. replace __COLLECTION__ with the one collection to freeze;
//   3. deploy.
// It sets that collection's create and update rules to null (superuser only),
// so no client can write it until the forward fix ships. List, view, and delete
// are left alone.
//
// Use only when a probe or the cross-owner scan shows a collection's rules are
// too loose and a forward fix is not ready yet (docs/operations.md,
// "Account-scope rules"). Never run against a live deployment without a pb_data
// backup taken with PocketBase stopped.
//
// down() is a deliberate no-op: a lever is forward-only like every account-scope
// migration, so `migrate down` does not lift the lock. Lift it with the
// restore_collection template once the fix is ready.
migrate(
  (db) => {
    const dao = new Dao(db);
    const collection = dao.findCollectionByNameOrId("__COLLECTION__");
    collection.createRule = null;
    collection.updateRule = null;
    dao.saveCollection(collection);
  },
  (_db) => {
    // Forward-only: the lock stays until the forward fix restores the rules.
  },
);
