/// <reference path="../pb_data/types.d.ts" />

migrate(
  (db) => {
    const dao = new Dao(db);

    // Idempotent: skip if collection already exists (e.g. created via admin UI
    // or a prior migration run that was partially rolled back).
    try {
      dao.findCollectionByNameOrId("experience_items");
      return; // already exists
    } catch (_) {
      // proceed with creation
    }

    const users = dao.findCollectionByNameOrId("users");
    const ownerRule = "user = @request.auth.id";
    const createIfAuthed = '@request.auth.id != ""';
    const JSON_LIMIT = 2 * 1024 * 1024;

    const experienceItems = new Collection({
      name: "experience_items",
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
          name: "type",
          type: "select",
          required: true,
          options: {
            maxSelect: 1,
            values: ["anecdote", "bullet", "history", "job"],
          },
        },
        { name: "title", type: "text", required: true },
        { name: "description", type: "text" },
        { name: "start_date", type: "date", required: true },
        { name: "end_date", type: "date" },
        {
          name: "tags",
          type: "json",
          options: { maxSize: JSON_LIMIT },
        },
        {
          name: "meta",
          type: "json",
          options: { maxSize: JSON_LIMIT },
        },
        { name: "sort_order", type: "number" },
      ],
      indexes: [
        "CREATE INDEX idx_exp_items_user ON experience_items (user)",
        "CREATE INDEX idx_exp_items_type ON experience_items (type)",
      ],
    });
    dao.saveCollection(experienceItems);
  },
  (db) => {
    const dao = new Dao(db);
    try {
      const col = dao.findCollectionByNameOrId("experience_items");
      dao.deleteCollection(col);
    } catch (_) {
      // collection may not exist
    }
  },
);
