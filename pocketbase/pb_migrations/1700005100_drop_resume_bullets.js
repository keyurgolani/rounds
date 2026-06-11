/// <reference path="../pb_data/types.d.ts" />

// Clean cutover: resume bullets are replaced by experience_bullets referenced
// from resume links. Drop the legacy resume_bullets collection. (No data
// migration.) Sub-project A already removed its source_anecdote field.

migrate(
  (db) => {
    const dao = new Dao(db);
    try { dao.deleteCollection(dao.findCollectionByNameOrId("resume_bullets")); } catch (_) { /* gone */ }
  },
  (db) => {
    const dao = new Dao(db);
    const users = dao.findCollectionByNameOrId("users");
    const ownerRule = "user = @request.auth.id";
    const createIfAuthed = '@request.auth.id != ""';
    const JSON_LIMIT = 2 * 1024 * 1024;
    const col = new Collection({
      name: "resume_bullets", type: "base",
      listRule: ownerRule, viewRule: ownerRule, createRule: createIfAuthed, updateRule: ownerRule, deleteRule: ownerRule,
      schema: [
        { name: "user", type: "relation", required: true, options: { collectionId: users.id, cascadeDelete: true, maxSelect: 1 } },
        { name: "text", type: "text", required: true },
        { name: "tags", type: "json", options: { maxSize: JSON_LIMIT } },
        { name: "metrics", type: "json", options: { maxSize: JSON_LIMIT } },
      ],
      indexes: ["CREATE INDEX idx_bullets_user ON resume_bullets (user)"],
    });
    dao.saveCollection(col);
  },
);
