/// <reference path="../pb_data/types.d.ts" />

// Clean cutover: the behavioral `anecdotes` collection is replaced by
// experience_anecdotes. Remove the now-orphaned resume_bullets.source_anecdote
// relation, then delete the anecdotes collection. (No data migration.)

migrate(
  (db) => {
    const dao = new Dao(db);

    // 1. Drop resume_bullets.source_anecdote (relation → anecdotes).
    try {
      const rb = dao.findCollectionByNameOrId("resume_bullets");
      const f = rb.schema.getFieldByName("source_anecdote");
      if (f) {
        rb.schema.removeField(f.id);
        dao.saveCollection(rb);
      }
    } catch (_) {
      // resume_bullets already gone (e.g. sub-project B applied first)
    }

    // 2. Delete the legacy anecdotes collection.
    try {
      const anecdotes = dao.findCollectionByNameOrId("anecdotes");
      dao.deleteCollection(anecdotes);
    } catch (_) {
      // already gone
    }
  },
  (db) => {
    // Down: recreate a minimal anecdotes collection so the migration is
    // reversible in dev. (Field-for-field parity with the original is not
    // required for rollback.)
    const dao = new Dao(db);
    const users = dao.findCollectionByNameOrId("users");
    const cats = dao.findCollectionByNameOrId("behavioral_categories");
    const questions = dao.findCollectionByNameOrId("behavioral_questions");
    const ownerRule = "user = @request.auth.id";
    const createIfAuthed = '@request.auth.id != ""';
    const col = new Collection({
      name: "anecdotes",
      type: "base",
      listRule: ownerRule, viewRule: ownerRule, createRule: createIfAuthed,
      updateRule: ownerRule, deleteRule: ownerRule,
      schema: [
        { name: "user", type: "relation", required: true,
          options: { collectionId: users.id, cascadeDelete: true, maxSelect: 1 } },
        { name: "title", type: "text", required: true },
        { name: "description", type: "text" },
        { name: "situation", type: "text" },
        { name: "task", type: "text" },
        { name: "action", type: "text" },
        { name: "result", type: "text" },
        { name: "categories", type: "relation",
          options: { collectionId: cats.id, cascadeDelete: false, maxSelect: null } },
        { name: "linked_questions", type: "relation",
          options: { collectionId: questions.id, cascadeDelete: false, maxSelect: null } },
        { name: "notes", type: "text" },
      ],
      indexes: ["CREATE INDEX idx_anecdotes_user ON anecdotes (user)"],
    });
    dao.saveCollection(col);
  },
);
