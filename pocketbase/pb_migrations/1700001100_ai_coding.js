/// <reference path="../pb_data/types.d.ts" />

// AI-Assisted Coding — three new collections plus a select-value
// extension to user_progress so the existing list filter and progress
// hook can plug into the new track without code changes.
//
// Collections:
//   ai_coding_rounds      — round content (language, starter files,
//                           checkpoints, rubric)
//   ai_coding_drafts      — per-file working copies (one row per file,
//                           keyed by user + campaign + round + file_path)
//   ai_coding_attempts    — one row per session: chats, test results,
//                           rubric review, status

migrate(
  (db) => {
    const dao = new Dao(db);
    const JSON_LIMIT = 2 * 1024 * 1024;
    const json = (name) => ({ name, type: "json", options: { maxSize: JSON_LIMIT } });

    const users = dao.findCollectionByNameOrId("users");
    const campaigns = dao.findCollectionByNameOrId("campaigns");
    const ownerRule = "user = @request.auth.id";
    const createIfAuthed = '@request.auth.id != ""';

    // 1) Extend user_progress.question_type to include "ai-coding".
    const progress = dao.findCollectionByNameOrId("user_progress");
    const qtField = progress.schema.getFieldByName("question_type");
    const values = qtField.options.values || [];
    if (!values.includes("ai-coding")) {
      qtField.options.values = [...values, "ai-coding"];
      dao.saveCollection(progress);
    }

    // 2) ai_coding_rounds — author-owned content; readable by any authed user.
    const rounds = new Collection({
      name: "ai_coding_rounds",
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
        { name: "description", type: "editor" },
        json("starter_files"),     // [{path, contents, readonly?}]
        json("checkpoints"),       // [{label, prompt, ai_allowed, test_command, tests_hidden?}]
        json("rubric"),            // {items: [{id, label, weight, prompt}]}
        json("topics"),
        json("companies"),
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_ai_coding_rounds_slug ON ai_coding_rounds (slug)",
      ],
    });
    dao.saveCollection(rounds);

    // 3) ai_coding_drafts — one row per file in a (user, campaign, round) session.
    const drafts = new Collection({
      name: "ai_coding_drafts",
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
          name: "round",
          type: "relation",
          required: true,
          options: { collectionId: rounds.id, cascadeDelete: true, maxSelect: 1 },
        },
        { name: "file_path", type: "text", required: true },
        { name: "contents", type: "text" },
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_ai_drafts_unique ON ai_coding_drafts (user, campaign, round, file_path)",
        "CREATE INDEX idx_ai_drafts_user_round ON ai_coding_drafts (user, round)",
      ],
    });
    dao.saveCollection(drafts);

    // 4) ai_coding_attempts — one row per session.
    const attempts = new Collection({
      name: "ai_coding_attempts",
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
          name: "round",
          type: "relation",
          required: true,
          options: { collectionId: rounds.id, cascadeDelete: true, maxSelect: 1 },
        },
        { name: "current_checkpoint", type: "number" },
        json("ai_chats"),          // [{checkpoint, role, content, model, ts}]
        json("test_results"),      // {[checkpoint_index]: {passed, failed, results}}
        json("rubric_review"),     // {items: [{id, score, evidence, suggestions}], total}
        {
          name: "status",
          type: "select",
          required: true,
          options: { maxSelect: 1, values: ["in-progress", "submitted", "graded"] },
        },
        { name: "duration_ms", type: "number" },
      ],
      indexes: [
        "CREATE INDEX idx_ai_attempts_user_round ON ai_coding_attempts (user, round)",
      ],
    });
    dao.saveCollection(attempts);
  },

  (db) => {
    const dao = new Dao(db);
    for (const name of ["ai_coding_attempts", "ai_coding_drafts", "ai_coding_rounds"]) {
      try {
        dao.deleteCollection(dao.findCollectionByNameOrId(name));
      } catch (_) { /* ignore */ }
    }
    // Revert user_progress enum
    try {
      const progress = dao.findCollectionByNameOrId("user_progress");
      const qt = progress.schema.getFieldByName("question_type");
      qt.options.values = (qt.options.values || []).filter((v) => v !== "ai-coding");
      dao.saveCollection(progress);
    } catch (_) { /* ignore */ }
  },
);
