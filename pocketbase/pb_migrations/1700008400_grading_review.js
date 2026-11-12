/// <reference path="../pb_data/types.d.ts" />

// The rubric review's admission operation (ROUNDS-00A-L03 PR 3).
//
// Additive. A grading job's review is charged as its own admission
// operation, `review`, which pb_hooks/execution.js reviewStart admits once
// per result. This lists it on the `operation` field of admission_commands
// and admission_leases. Hooks save those rows through the DAO, which
// doesn't check the list, so this changes no row and no write; the lists
// match what the rows hold, as 1700008300_share_secrets.js did for its
// three.
//
// down() takes `review` off both lists again and leaves every row as it is.

const OPERATION = "review";
const COLLECTIONS = ["admission_commands", "admission_leases"];

migrate(
  (db) => {
    const dao = new Dao(db);
    // Both are looked up first, so a missing one changes neither.
    const collections = COLLECTIONS.map((name) => dao.findCollectionByNameOrId(name));
    collections.forEach((collection) => {
      const operation = collection.schema.getFieldByName("operation");
      const values = operation.options.values || [];
      if (values.indexOf(OPERATION) < 0) values.push(OPERATION);
      operation.options.values = values;
      dao.saveCollection(collection);
    });
  },

  (db) => {
    const dao = new Dao(db);
    COLLECTIONS.forEach((name) => {
      const collection = dao.findCollectionByNameOrId(name);
      const operation = collection.schema.getFieldByName("operation");
      operation.options.values = (operation.options.values || []).filter((value) => value !== OPERATION);
      dao.saveCollection(collection);
    });
  },
);
