/// <reference path="../pb_data/types.d.ts" />

// Creates six junction collections for experience entity connections:
// jobs<->projects, jobs<->anecdotes, jobs<->bullets,
// projects<->anecdotes, projects<->bullets, anecdotes<->bullets.

migrate(
  (db) => {
    const dao = new Dao(db);
    const users = dao.findCollectionByNameOrId("users");
    const jobs = dao.findCollectionByNameOrId("experience_jobs");
    const projects = dao.findCollectionByNameOrId("experience_projects");
    const anecdotes = dao.findCollectionByNameOrId("experience_anecdotes");
    const bullets = dao.findCollectionByNameOrId("experience_bullets");

    const ownerRule = "user = @request.auth.id";
    const createIfAuthed = '@request.auth.id != ""';

    const junctions = [
      { name: "exp_job_projects", parent: jobs, child: projects },
      { name: "exp_job_anecdotes", parent: jobs, child: anecdotes },
      { name: "exp_job_bullets", parent: jobs, child: bullets },
      { name: "exp_project_anecdotes", parent: projects, child: anecdotes },
      { name: "exp_project_bullets", parent: projects, child: bullets },
      { name: "exp_anecdote_bullets", parent: anecdotes, child: bullets },
    ];

    for (const { name, parent, child } of junctions) {
      const col = new Collection({
        name,
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
            name: "parent",
            type: "relation",
            required: true,
            options: { collectionId: parent.id, cascadeDelete: true, maxSelect: 1 },
          },
          {
            name: "child",
            type: "relation",
            required: true,
            options: { collectionId: child.id, cascadeDelete: true, maxSelect: 1 },
          },
        ],
        indexes: [
          `CREATE INDEX idx_${name}_user ON ${name} (user)`,
          `CREATE UNIQUE INDEX idx_${name}_pair ON ${name} (parent, child)`,
        ],
      });
      dao.saveCollection(col);
    }
  },
  (db) => {
    const dao = new Dao(db);
    const names = [
      "exp_job_projects",
      "exp_job_anecdotes",
      "exp_job_bullets",
      "exp_project_anecdotes",
      "exp_project_bullets",
      "exp_anecdote_bullets",
    ];
    for (const name of names) {
      try {
        const col = dao.findCollectionByNameOrId(name);
        dao.deleteCollection(col);
      } catch (_) {
        // already gone
      }
    }
  },
);
