/// <reference path="../pb_data/types.d.ts" />

// Per-question timer state. One row per (user, question_type,
// question_slug). The frontend's useQuestionTimer hook reads this row
// on mount, ticks a local 1s display while running, and writes back
// on toggle/reset. Persists across sessions, devices, and logout —
// resuming the round shows the timer where the user left off.
//
// `started_at` is text (not date) because PB's date type can't cleanly
// distinguish "unset" from epoch 0; we use empty string for "paused".

migrate(
  (db) => {
    const dao = new Dao(db);

    const users = dao.findCollectionByNameOrId("users");
    const ownerRule = "user = @request.auth.id";
    const createIfAuthed = '@request.auth.id != ""';

    const timers = new Collection({
      name: "question_timers",
      type: "base",
      listRule: ownerRule,
      viewRule: ownerRule,
      createRule: createIfAuthed,
      updateRule: ownerRule,
      deleteRule: ownerRule,
      schema: [
        {
          name: "user",
          type: "relation",
          required: true,
          options: { collectionId: users.id, cascadeDelete: true, maxSelect: 1 },
        },
        { name: "question_type", type: "text", required: true },
        { name: "question_slug", type: "text", required: true },
        { name: "accumulated_ms", type: "number" },
        { name: "started_at", type: "text" },
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_question_timers_unique ON question_timers (user, question_type, question_slug)",
        "CREATE INDEX idx_question_timers_user ON question_timers (user)",
      ],
    });
    dao.saveCollection(timers);
  },

  (db) => {
    const dao = new Dao(db);
    try {
      dao.deleteCollection(dao.findCollectionByNameOrId("question_timers"));
    } catch (_) { /* already dropped */ }
  },
);
