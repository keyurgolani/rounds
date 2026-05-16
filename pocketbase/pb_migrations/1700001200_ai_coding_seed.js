/// <reference path="../pb_data/types.d.ts" />

const ROUNDS = [
  // Intentionally empty: legacy samples removed 2026-05-16 as part of the
  // catalog-rebuild round. New rounds will be added here in later sessions
  // as briefs from docs/briefs/ai-assisted-coding.md are implemented.
];

migrate(
  (db) => {
    const dao = new Dao(db);
    const coll = dao.findCollectionByNameOrId("ai_coding_rounds");
    for (const r of ROUNDS) {
      // Upsert: drop any existing row with this slug so the seed is
      // idempotent across re-applies (the previous strategy of
      // "skip on collision" left old rows with stale checkpoints).
      try {
        const old = dao.findFirstRecordByData("ai_coding_rounds", "slug", r.slug);
        dao.deleteRecord(old);
      } catch (_) { /* not present */ }
      const rec = new Record(coll, {
        slug: r.slug,
        title: r.title,
        difficulty: r.difficulty,
        language: r.language,
        description: r.description,
        starter_files: r.starter_files,
        checkpoints: r.checkpoints,
        rubric: r.rubric,
        topics: r.topics,
        companies: r.companies,
      });
      dao.saveRecord(rec);
    }
  },
  (db) => {
    const dao = new Dao(db);
    for (const r of ROUNDS) {
      try {
        const rec = dao.findFirstRecordByData("ai_coding_rounds", "slug", r.slug);
        dao.deleteRecord(rec);
      } catch (_) { /* ignore */ }
    }
  },
);
