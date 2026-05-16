/// <reference path="../pb_data/types.d.ts" />

const ASSIGNMENTS = [
  // Intentionally empty: legacy samples removed 2026-05-16 as part of the
  // catalog-rebuild round. New assignments will be added here in later
  // sessions as briefs from docs/briefs/real-world-problems.md are implemented.
];

migrate(
  (db) => {
    const dao = new Dao(db);
    const coll = dao.findCollectionByNameOrId("take_home_assignments");
    for (const a of ASSIGNMENTS) {
      try {
        const old = dao.findFirstRecordByData("take_home_assignments", "slug", a.slug);
        dao.deleteRecord(old);
      } catch (_) { /* not present */ }
      const rec = new Record(coll, {
        slug: a.slug,
        title: a.title,
        difficulty: a.difficulty,
        language: a.language,
        entrypoint: a.entrypoint,
        time_budget_min: a.time_budget_min,
        ai_policy: a.ai_policy,
        prompt_md: a.prompt_md,
        starter_files: a.starter_files,
        harness_files: a.harness_files,
        rubric: a.rubric,
        topics: a.topics,
        companies: a.companies,
      });
      dao.saveRecord(rec);
    }
  },
  (db) => {
    const dao = new Dao(db);
    for (const a of ASSIGNMENTS) {
      try {
        const rec = dao.findFirstRecordByData("take_home_assignments", "slug", a.slug);
        dao.deleteRecord(rec);
      } catch (_) { /* ignore */ }
    }
  },
);
