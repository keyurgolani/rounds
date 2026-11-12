/// <reference path="../pb_data/types.d.ts" />

// The benchmark's startup schema change (ROUNDS-02-L01). Bench only: bench.py
// adds it to a stopped scratch copy and times PocketBase's next start, which
// applies it before serving. A field with a backfill and an index over the
// largest table at the floor stand in for a typical additive migration.

migrate(
  (db) => {
    const dao = new Dao(db);
    const col = dao.findCollectionByNameOrId("bench_records");
    col.schema.addField(new SchemaField({ name: "archived", type: "bool", options: {} }));
    dao.saveCollection(col);
    // Raw SQL for the index: the repository's migrations set indexes only
    // when they create a collection, so this doesn't edit a saved list.
    db.newQuery("CREATE INDEX idx_bench_records_account_status ON bench_records (account_id, status)").execute();
    db.newQuery("UPDATE bench_records SET archived = (kind = 'activity' AND status = 'done')").execute();
  },
  (db) => {
    const dao = new Dao(db);
    const col = dao.findCollectionByNameOrId("bench_records");
    db.newQuery("DROP INDEX IF EXISTS idx_bench_records_account_status").execute();
    const f = col.schema.getFieldByName("archived");
    if (f) col.schema.removeField(f.id);
    dao.saveCollection(col);
  },
);
