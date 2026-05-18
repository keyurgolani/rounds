/// <reference path="../pb_data/types.d.ts" />

// Adds optional `loop_label` to interview_rounds. Rounds that share a
// loop_label group visually as a single "interview loop" (e.g. a Meta
// onsite with 6 rounds across 2 days). Empty / null means a one-off
// round with no parent loop.
//
// We deliberately keep this as a free-text label rather than a new
// `interview_loops` collection — loops have no metadata of their own
// today (no recruiter, no aggregate stats), so the join would be
// over-engineering. If loop metadata is ever needed, a follow-up
// migration can promote loop_label into a relation.

migrate(
  (db) => {
    const dao = new Dao(db);
    const rounds = dao.findCollectionByNameOrId("interview_rounds");
    if (!rounds.schema.getFieldByName("loop_label")) {
      rounds.schema.addField(
        new SchemaField({
          name: "loop_label",
          type: "text",
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
        rounds.schema.removeField("loop_label");
      } catch (_) {
        /* already gone */
      }
      dao.saveCollection(rounds);
    } catch (_) {
      /* collection dropped */
    }
  },
);
