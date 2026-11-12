/// <reference path="../pb_data/types.d.ts" />

// What PocketBase does to a reference when its target is deleted
// (ROUNDS-02-L01). Bench only: schema_dump.py runs it with `migrate up` in a
// throwaway directory of its own, never beside the repository's migrations,
// and records the outcomes in the schema snapshot. The ERD's delete
// behavior per relation comes from these outcomes and each field's flags.

migrate(
  (db) => {
    const dao = new Dao(db);
    const closed = { listRule: null, viewRule: null, createRule: null, updateRule: null, deleteRule: null };
    const make = (name, schema) => {
      dao.saveCollection(new Collection(Object.assign({ name, type: "base", schema }, closed)));
      return dao.findCollectionByNameOrId(name);
    };
    const target = make("probe_target", [{ name: "label", type: "text", options: {} }]);
    const ref = (name, required, cascade, maxSelect) =>
      make(name, [{ name: "ref", type: "relation", required, options: { collectionId: target.id, cascadeDelete: cascade, maxSelect } }]);
    const cases = [
      ["single-required-cascade", ref("probe_a", true, true, 1)],
      ["single-required-no-cascade", ref("probe_b", true, false, 1)],
      ["single-optional-no-cascade", ref("probe_c", false, false, 1)],
      ["single-optional-cascade", ref("probe_d", false, true, 1)],
      ["multi-optional-no-cascade", ref("probe_e", false, false, null)],
    ];
    const results = make("probe_results", [{ name: "case", type: "text", options: {} }, { name: "outcome", type: "text", options: {} }]);
    const save = (col, data) => {
      const r = new Record(col);
      Object.keys(data).forEach((k) => r.set(k, data[k]));
      dao.saveRecord(r);
      return r;
    };
    cases.forEach((c) => {
      const t = save(target, { label: c[0] });
      const other = save(target, { label: c[0] + "-other" });
      const value = c[0].indexOf("multi") === 0 ? [t.id, other.id] : t.id;
      const row = save(c[1], { ref: value });
      let outcome;
      try {
        dao.deleteRecord(t);
        let kept;
        try {
          kept = dao.findRecordById(c[1].name, row.id);
        } catch (_) {
          kept = null;
        }
        if (!kept) outcome = "cascade";
        else {
          // getStringSlice reads a single or a multiple relation alike.
          const ids = kept.getStringSlice("ref");
          let found = false;
          for (let i = 0; i < ids.length; i += 1) if (ids[i] === t.id) found = true;
          outcome = found ? "dangling" : "unset";
        }
      } catch (_) {
        outcome = "restrict";
      }
      save(results, { case: c[0], outcome });
    });
  },
  () => {},
);
