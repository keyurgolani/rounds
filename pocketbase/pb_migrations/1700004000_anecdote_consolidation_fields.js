/// <reference path="../pb_data/types.d.ts" />

// Anecdote consolidation: extend experience_anecdotes with the fields the
// legacy behavioral `anecdotes` collection had — description, categories
// (competencies), linked_questions, notes — so it becomes the single store.

migrate(
  (db) => {
    const dao = new Dao(db);
    const col = dao.findCollectionByNameOrId("experience_anecdotes");
    const cats = dao.findCollectionByNameOrId("behavioral_categories");
    const questions = dao.findCollectionByNameOrId("behavioral_questions");

    col.schema.addField(new SchemaField({ name: "description", type: "text" }));
    col.schema.addField(new SchemaField({ name: "notes", type: "text" }));
    col.schema.addField(
      new SchemaField({
        name: "categories",
        type: "relation",
        options: { collectionId: cats.id, cascadeDelete: false, maxSelect: null },
      }),
    );
    col.schema.addField(
      new SchemaField({
        name: "linked_questions",
        type: "relation",
        options: { collectionId: questions.id, cascadeDelete: false, maxSelect: null },
      }),
    );

    dao.saveCollection(col);
  },
  (db) => {
    const dao = new Dao(db);
    const col = dao.findCollectionByNameOrId("experience_anecdotes");
    for (const name of ["description", "notes", "categories", "linked_questions"]) {
      const f = col.schema.getFieldByName(name);
      if (f) col.schema.removeField(f.id);
    }
    dao.saveCollection(col);
  },
);
