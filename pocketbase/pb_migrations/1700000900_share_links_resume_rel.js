/// <reference path="../pb_data/types.d.ts" />

// Schema update: public share links can target either a master resume
// or a tailored variant. The original schema made `variant` required,
// which forced users to tailor before they could share. We add a
// parallel `resume` relation and relax `variant` so the app can choose.
// Both are optional at the schema level; the share router requires
// exactly one to be set.

migrate(
  (db) => {
    const dao = new Dao(db);
    const links = dao.findCollectionByNameOrId("resume_share_links");
    const resumes = dao.findCollectionByNameOrId("resumes");

    // Relax `variant` to optional.
    const variantField = links.schema.getFieldByName("variant");
    if (variantField) {
      variantField.required = false;
    }

    // Add a new `resume` relation if it isn't there yet.
    if (!links.schema.getFieldByName("resume")) {
      links.schema.addField(
        new SchemaField({
          name: "resume",
          type: "relation",
          options: {
            collectionId: resumes.id,
            cascadeDelete: true,
            maxSelect: 1,
          },
        }),
      );
    }

    dao.saveCollection(links);
  },
  (db) => {
    const dao = new Dao(db);
    try {
      const links = dao.findCollectionByNameOrId("resume_share_links");
      try {
        links.schema.removeField("resume");
      } catch (_) {
        /* already gone */
      }
      const variantField = links.schema.getFieldByName("variant");
      if (variantField) variantField.required = true;
      dao.saveCollection(links);
    } catch (_) {
      /* collection already dropped */
    }
  },
);
