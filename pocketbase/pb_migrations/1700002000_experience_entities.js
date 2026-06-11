/// <reference path="../pb_data/types.d.ts" />

// Drops the legacy unified experience_items collection and creates four
// dedicated collections: jobs, projects, anecdotes, bullets.

migrate(
  (db) => {
    const dao = new Dao(db);
    const users = dao.findCollectionByNameOrId("users");
    const ownerRule = "user = @request.auth.id";
    const createIfAuthed = '@request.auth.id != ""';
    const JSON_LIMIT = 2 * 1024 * 1024;

    // ---- Drop legacy unified collection ---------------------------
    try {
      const legacy = dao.findCollectionByNameOrId("experience_items");
      dao.deleteCollection(legacy);
    } catch (_) {
      // already gone
    }

    // ---- experience_jobs ------------------------------------------
    const jobs = new Collection({
      name: "experience_jobs",
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
        { name: "company", type: "text", required: true },
        { name: "role", type: "text", required: true },
        { name: "location", type: "text" },
        {
          name: "employment_type",
          type: "select",
          options: {
            maxSelect: 1,
            values: ["full-time", "contract", "part-time", "internship", "freelance"],
          },
        },
        { name: "start_date", type: "date", required: true },
        { name: "end_date", type: "date" },
        { name: "description", type: "text" },
        {
          name: "tags",
          type: "json",
          options: { maxSize: JSON_LIMIT },
        },
      ],
      indexes: [
        "CREATE INDEX idx_exp_jobs_user ON experience_jobs (user)",
      ],
    });
    dao.saveCollection(jobs);

    // ---- experience_projects --------------------------------------
    const projects = new Collection({
      name: "experience_projects",
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
        { name: "title", type: "text", required: true },
        { name: "company", type: "text" },
        { name: "role", type: "text" },
        { name: "team_size", type: "number" },
        {
          name: "tech_stack",
          type: "json",
          options: { maxSize: JSON_LIMIT },
        },
        { name: "start_date", type: "date", required: true },
        { name: "end_date", type: "date" },
        { name: "description", type: "text" },
        {
          name: "tags",
          type: "json",
          options: { maxSize: JSON_LIMIT },
        },
      ],
      indexes: [
        "CREATE INDEX idx_exp_projects_user ON experience_projects (user)",
      ],
    });
    dao.saveCollection(projects);

    // ---- experience_anecdotes -------------------------------------
    const anecdotes = new Collection({
      name: "experience_anecdotes",
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
        { name: "title", type: "text", required: true },
        { name: "situation", type: "text" },
        { name: "task", type: "text" },
        { name: "action", type: "text" },
        { name: "result", type: "text" },
        { name: "impact", type: "text" },
        { name: "company", type: "text" },
        { name: "project", type: "text" },
        { name: "date", type: "date", required: true },
        {
          name: "tags",
          type: "json",
          options: { maxSize: JSON_LIMIT },
        },
      ],
      indexes: [
        "CREATE INDEX idx_exp_anecdotes_user ON experience_anecdotes (user)",
      ],
    });
    dao.saveCollection(anecdotes);

    // ---- experience_bullets ---------------------------------------
    const bullets = new Collection({
      name: "experience_bullets",
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
        { name: "title", type: "text", required: true },
        { name: "impact", type: "text" },
        {
          name: "category",
          type: "select",
          options: {
            maxSelect: 1,
            values: ["leadership", "technical", "process", "business", "other"],
          },
        },
        { name: "date", type: "date", required: true },
        {
          name: "tags",
          type: "json",
          options: { maxSize: JSON_LIMIT },
        },
      ],
      indexes: [
        "CREATE INDEX idx_exp_bullets_user ON experience_bullets (user)",
      ],
    });
    dao.saveCollection(bullets);
  },
  (db) => {
    const dao = new Dao(db);
    const collections = [
      "experience_jobs",
      "experience_projects",
      "experience_anecdotes",
      "experience_bullets",
    ];
    for (const name of collections) {
      try {
        const col = dao.findCollectionByNameOrId(name);
        dao.deleteCollection(col);
      } catch (_) {
        // already gone
      }
    }
  },
);
