/// <reference path="../pb_data/types.d.ts" />

// Expand step for server-owned definitions (ROUNDS-00A-L02).
//
// The compiled definitions in backend/definitions/ are the source of
// truth for what executes and how it scores. This migration records, on
// each presentation row, which definition version it corresponds to, so
// step 2 can resolve a request's (track, slug, variant, version) against
// the manifest. At this step the runner still reads the legacy PocketBase
// path (ROUNDS_GATE_EXECUTION_DEFINITIONS=legacy), so the new columns are
// written and not yet read; the resolver, never a column, is the
// authority on whether a version exists.
//
// It is additive and non-destructive:
//   * a new server-only collection, definition_migration_journal, with a
//     row per touched presentation row recording its mapping;
//   * definition_version (number) on coding_questions, ai_coding_rounds,
//     and take_home_assignments, plus definition_case_ids (json) on
//     coding_questions (the case ids its compiled test definition holds);
//   * every presentation row stays, so drafts and attempts survive.
//
// Mapping by slug (backend/definitions/manifest.json; the committed
// touched-row manifest pocketbase/migration-manifests/
// 1700006200_definitions_expand.json records the expected disposition):
//   * coding questions and hallucinated-http-client -> active, version 1;
//   * the 5 removed AI-coding samples and the 3 removed take-home
//     assignments, present only on a pre-2026-05-16 database, -> retired,
//     version 1 (their definitions are retired, payload-free for the
//     AI-coding ones), so a request gets definition_retired, not a run;
//   * any other slug has no definition, so its row is left unversioned and
//     the resolver answers definition_not_found at step 2.
//
// down() removes only the columns and the journal collection it added. It
// deletes no presentation, draft, or attempt row, so it is a safe revert;
// account isolation and user content are untouched.

// The removed samples whose sources are gone (build.py SOURCELESS_AI_CODING)
// and the removed take-home assignments (build.py RETIRED_TAKE_HOME). Only
// a pre-2026-05-16 database still has rows for these.
const RETIRED_AI_CODING = ["async-bugs-py", "cart-bugfix-py", "log-parser-ts", "rate-limiter-ts", "word-count-py"];
const RETIRED_TAKE_HOME = ["csv-summarize-py", "event-bus-ts", "kv-store-py"];
const JOURNAL = "definition_migration_journal";
const MIGRATION = "1700006200_definitions_expand";

migrate(
  (db) => {
    const dao = new Dao(db);

    // Resolve every presentation collection before writing anything, so a
    // missing one fails the whole migration and changes nothing.
    const coding = dao.findCollectionByNameOrId("coding_questions");
    const aiRounds = dao.findCollectionByNameOrId("ai_coding_rounds");
    const takeHome = dao.findCollectionByNameOrId("take_home_assignments");

    // 1) The server-only journal. Every client rule is null, so only a
    //    superuser (this migration) ever reads or writes it.
    const journal = new Collection({
      name: "definition_migration_journal",
      type: "base",
      listRule: null,
      viewRule: null,
      createRule: null,
      updateRule: null,
      deleteRule: null,
      schema: [
        { name: "migration", type: "text", required: true },
        { name: "collection", type: "text", required: true },
        { name: "record", type: "text", required: true },
        { name: "slug", type: "text" },
        { name: "definition_track", type: "text" },
        { name: "definition_version", type: "number" },
        { name: "disposition", type: "text", required: true },
      ],
      indexes: [
        `CREATE INDEX idx_def_journal_migration ON ${JOURNAL} (migration)`,
      ],
    });
    dao.saveCollection(journal);

    // 2) The new presentation columns.
    const numberField = (name) => new SchemaField({ name, type: "number" });
    coding.schema.addField(numberField("definition_version"));
    coding.schema.addField(new SchemaField({ name: "definition_case_ids", type: "json", options: { maxSize: 64 * 1024 } }));
    dao.saveCollection(coding);
    aiRounds.schema.addField(numberField("definition_version"));
    dao.saveCollection(aiRounds);
    takeHome.schema.addField(numberField("definition_version"));
    dao.saveCollection(takeHome);

    const record = (collection, row, track, version, disposition, caseIds) => {
      if (version !== null) row.set("definition_version", version);
      if (caseIds !== null) row.set("definition_case_ids", caseIds);
      dao.saveRecord(row);
      const entry = new Record(journal, {
        migration: MIGRATION,
        collection: collection,
        record: row.id,
        slug: row.getString("slug"),
        definition_track: track,
        definition_version: version === null ? 0 : version,
        disposition: disposition,
      });
      dao.saveRecord(entry);
    };

    // 3) Map each presentation row. find*ByFilter with an always-true
    //    filter lists every row; nothing is deleted or recreated.
    for (const row of dao.findRecordsByFilter("coding_questions", "id != ''")) {
      const cases = row.get("test_cases");
      const ids = [];
      if (Array.isArray(cases)) {
        for (let i = 0; i < cases.length; i += 1) {
          if (cases[i] && typeof cases[i] === "object") ids.push("c" + String(ids.length).padStart(3, "0"));
        }
      }
      record("coding_questions", row, "coding", 1, "active", ids);
    }
    for (const row of dao.findRecordsByFilter("ai_coding_rounds", "id != ''")) {
      const slug = row.getString("slug");
      const retired = RETIRED_AI_CODING.indexOf(slug) !== -1;
      record("ai_coding_rounds", row, "ai-coding", 1, retired ? "retired" : "active", null);
    }
    for (const row of dao.findRecordsByFilter("take_home_assignments", "id != ''")) {
      const slug = row.getString("slug");
      const retired = RETIRED_TAKE_HOME.indexOf(slug) !== -1;
      // No active take-home definition exists at step 1; a non-retired
      // assignment is left unversioned and resolves to not-found.
      record("take_home_assignments", row, "take-home", retired ? 1 : null, retired ? "retired" : "definition-not-found", null);
    }
  },
  (db) => {
    const dao = new Dao(db);
    // Forward-safe revert: drop only the added columns and the journal
    // collection. No presentation, draft, or attempt row is touched.
    for (const [name, fields] of [
      ["coding_questions", ["definition_version", "definition_case_ids"]],
      ["ai_coding_rounds", ["definition_version"]],
      ["take_home_assignments", ["definition_version"]],
    ]) {
      const collection = dao.findCollectionByNameOrId(name);
      for (const field of fields) {
        if (collection.schema.getFieldByName(field)) collection.schema.removeField(collection.schema.getFieldByName(field).id);
      }
      dao.saveCollection(collection);
    }
    dao.deleteCollection(dao.findCollectionByNameOrId(JOURNAL));
  }
);
