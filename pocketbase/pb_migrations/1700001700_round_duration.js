/// <reference path="../pb_data/types.d.ts" />

// Adds `duration_minutes` (number) to interview_rounds so each round
// can record its scheduled length. Existing rows default to null —
// the UI renders "—" for unset durations.

migrate(
  (db) => {
    const dao = new Dao(db);
    const rounds = dao.findCollectionByNameOrId("interview_rounds");
    if (!rounds.schema.getFieldByName("duration_minutes")) {
      rounds.schema.addField(
        new SchemaField({
          name: "duration_minutes",
          type: "number",
          options: { min: 0, max: 1440 },
        }),
      );
    }
    dao.saveCollection(rounds);
  },
  (db) => {
    const dao = new Dao(db);
    try {
      const rounds = dao.findCollectionByNameOrId("interview_rounds");
      try {
        rounds.schema.removeField("duration_minutes");
      } catch (_) {
        /* already gone */
      }
      dao.saveCollection(rounds);
    } catch (_) {
      /* collection dropped */
    }
  },
);
