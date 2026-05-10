/// <reference path="../pb_data/types.d.ts" />

// Take-Home Coding Assignments — three new collections plus a select-value
// extension to user_progress so the existing list filter and progress
// hook can plug into the new track without code changes.
//
// Collections:
//   take_home_assignments — assignment content (language, prompt, starter
//                           files, harness files, rubric, ai policy)
//   take_home_drafts      — per-file working copies (one row per file,
//                           keyed by user + campaign + assignment + file_path)
//   take_home_attempts    — one row per submission: files, ai chats, harness
//                           output, rubric review, status

migrate(
  (db) => {
    const dao = new Dao(db);
    const JSON_LIMIT = 2 * 1024 * 1024;
    const json = (name) => ({ name, type: "json", options: { maxSize: JSON_LIMIT } });

    const users = dao.findCollectionByNameOrId("users");
    const campaigns = dao.findCollectionByNameOrId("campaigns");
    const ownerRule = "user = @request.auth.id";
    const createIfAuthed = '@request.auth.id != ""';

    // 1) Extend user_progress.question_type to include "take-home".
    const progress = dao.findCollectionByNameOrId("user_progress");
    const qtField = progress.schema.getFieldByName("question_type");
    const values = qtField.options.values || [];
    if (!values.includes("take-home")) {
      qtField.options.values = [...values, "take-home"];
      dao.saveCollection(progress);
    }

    // 2) take_home_assignments — author-owned content; readable by any authed user.
    const assignments = new Collection({
      name: "take_home_assignments",
      type: "base",
      listRule: '@request.auth.id != ""',
      viewRule: '@request.auth.id != ""',
      createRule: null,    // seed migration only
      updateRule: null,
      deleteRule: null,
      schema: [
        { name: "slug", type: "text", required: true, options: { pattern: "^[a-z0-9-]+$" } },
        { name: "title", type: "text", required: true },
        { name: "difficulty", type: "text" },
        { name: "language", type: "text", required: true },
        { name: "entrypoint", type: "text", required: true },
        { name: "time_budget_min", type: "number" },
        {
          name: "ai_policy",
          type: "select",
          required: true,
          options: { maxSelect: 1, values: ["off", "on", "candidate-choice"] },
        },
        { name: "prompt_md", type: "editor" },
        json("starter_files"),     // [{path, contents}]
        json("harness_files"),     // [{path, contents}] — sandbox/harness.py etc., not shown to candidate
        json("rubric"),            // {items: [{id, label, weight, prompt}]}
        json("topics"),
        json("companies"),
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_take_home_assignments_slug ON take_home_assignments (slug)",
      ],
    });
    dao.saveCollection(assignments);

    // 3) take_home_drafts — one row per file in a (user, campaign, assignment) session.
    const drafts = new Collection({
      name: "take_home_drafts",
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
        {
          name: "campaign",
          type: "relation",
          options: { collectionId: campaigns.id, cascadeDelete: false, maxSelect: 1 },
        },
        {
          name: "assignment",
          type: "relation",
          required: true,
          options: { collectionId: assignments.id, cascadeDelete: true, maxSelect: 1 },
        },
        { name: "file_path", type: "text", required: true },
        { name: "contents", type: "text" },
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_take_home_drafts_unique ON take_home_drafts (user, campaign, assignment, file_path)",
        "CREATE INDEX idx_take_home_drafts_user_assignment ON take_home_drafts (user, assignment)",
      ],
    });
    dao.saveCollection(drafts);

    // 4) take_home_attempts — one row per submission.
    const attempts = new Collection({
      name: "take_home_attempts",
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
        {
          name: "campaign",
          type: "relation",
          options: { collectionId: campaigns.id, cascadeDelete: false, maxSelect: 1 },
        },
        {
          name: "assignment",
          type: "relation",
          required: true,
          options: { collectionId: assignments.id, cascadeDelete: true, maxSelect: 1 },
        },
        json("files"),             // final submitted file tree
        { name: "ai_assist_used", type: "bool" },
        json("ai_chats"),          // optional, only when ai_policy != "off"
        { name: "notes", type: "text" },
        json("harness_output"),    // {criteria, score, duration_ms}
        json("rubric_review"),     // AI rubric output
        {
          name: "status",
          type: "select",
          required: true,
          options: { maxSelect: 1, values: ["in-progress", "submitted", "graded"] },
        },
        { name: "started_at", type: "text" },
        { name: "submitted_at", type: "text" },
        { name: "duration_ms", type: "number" },
      ],
      indexes: [
        "CREATE INDEX idx_take_home_attempts_user_assignment ON take_home_attempts (user, assignment)",
      ],
    });
    dao.saveCollection(attempts);
  },

  (db) => {
    const dao = new Dao(db);
    for (const name of ["take_home_attempts", "take_home_drafts", "take_home_assignments"]) {
      try {
        dao.deleteCollection(dao.findCollectionByNameOrId(name));
      } catch (_) { /* ignore */ }
    }
    // Revert user_progress enum
    try {
      const progress = dao.findCollectionByNameOrId("user_progress");
      const qt = progress.schema.getFieldByName("question_type");
      qt.options.values = (qt.options.values || []).filter((v) => v !== "take-home");
      dao.saveCollection(progress);
    } catch (_) { /* ignore */ }
  },
);
