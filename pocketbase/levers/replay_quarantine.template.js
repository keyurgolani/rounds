/// <reference path="../pb_data/types.d.ts" />
// RELATION QUARANTINE REPLAY (operator lever) - ROUNDS-00B-L02.
//
// This is a TEMPLATE, not a migration. Nothing here runs on its own. To use it
// (docs/operations.md, "Relation endpoint authorization and quarantine"):
//   1. copy this file into an empty folder as `<unix-seconds>_replay_quarantine.js`;
//   2. replace "__ENTRY_ID__" with the relation_quarantine entry ids to replay,
//      each quoted, comma-separated: "id1", "id2";
//   3. with PocketBase stopped and a fresh pb_data backup, run
//      `pocketbase migrate up` with --migrationsDir pointing at that folder.
//
// A `moved` entry's row is written back from its payload exactly as it was:
// every column, created and updated included, read and written by SQLite
// itself so nothing is rounded or reordered. A `cleared` entry's field is set
// back to its target. Every write goes through the relation triggers, so an
// entry replays only when its targets exist and belong to the row's own
// account: fix the ownership first if that is why it was quarantined, and list
// a moved parent with its dependents (parents go first whatever the order
// here). Each replayed entry gets status `replayed`. If any listed entry is
// not `quarantined` or cannot be replayed, the whole run fails and nothing
// changes; PocketBase logs why and still exits 0, so check that the entries
// now read `replayed`.
//
// down() is a deliberate no-op, like every account-scope lever.
const ENTRY_IDS = ["__ENTRY_ID__"];

migrate(
  (db) => {
    const dao = new Dao(db);
    if (!ENTRY_IDS.length) throw new Error("replay_quarantine: list at least one entry id");
    const entries = ENTRY_IDS.map((id) => dao.findRecordById("relation_quarantine", id));
    for (let i = 0; i < entries.length; i++) {
      const status = entries[i].getString("status");
      if (status !== "quarantined") {
        throw new Error("replay_quarantine: entry " + entries[i].id + " is " + status + ", not quarantined");
      }
    }

    // The payload's columns that the table still has, in table order.
    const columnsFor = (entry) => {
      const rows = arrayOf(new DynamicModel({ name: "" }));
      db.newQuery(
        "SELECT p.name AS name FROM pragma_table_info({:t}) p WHERE p.name IN " +
          '(SELECT key FROM json_each((SELECT "payload" FROM "relation_quarantine" WHERE "id" = {:id}))) ORDER BY p.cid',
      )
        .bind({ t: entry.getString("source_collection"), id: entry.id })
        .all(rows);
      return rows.map((r) => r.name);
    };
    const restoreRow = (entry) => {
      const table = entry.getString("source_collection");
      const cols = columnsFor(entry);
      if (!cols.length) throw new Error("replay_quarantine: entry " + entry.id + " has no payload columns");
      db.newQuery(
        'INSERT INTO "' + table + '" (' + cols.map((n) => '"' + n + '"').join(", ") + ") SELECT " +
          cols.map((n) => "json_extract(\"payload\", '$.\"" + n + "\"')").join(", ") +
          ' FROM "relation_quarantine" WHERE "id" = {:id}',
      )
        .bind({ id: entry.id })
        .execute();
    };
    const restoreField = (entry) => {
      const rec = dao.findRecordById(entry.getString("source_collection"), entry.getString("source_id"));
      rec.set(entry.getString("field"), entry.getString("target_id"));
      dao.saveRecord(rec);
    };

    // Parents before dependents: keep passing over what is left until every
    // entry is written; a pass that writes nothing means the rest cannot be.
    let pending = entries.slice();
    while (pending.length) {
      const left = [];
      let lastError = "";
      for (let i = 0; i < pending.length; i++) {
        const entry = pending[i];
        try {
          if (entry.getString("action") === "moved") restoreRow(entry);
          else restoreField(entry);
        } catch (err) {
          left.push(entry);
          lastError = String(err);
          continue;
        }
        entry.set("status", "replayed");
        dao.saveRecord(entry);
      }
      if (left.length === pending.length) {
        throw new Error("replay_quarantine: " + left.length + " entries could not be replayed (" + lastError + ")");
      }
      pending = left;
    }
  },
  (_db) => {
    // Forward-only: undo a replay with a forward step, never a rollback.
  },
);
