/// <reference path="../pb_data/types.d.ts" />

// Resume library references: add a `links` JSON column to resumes,
// resume_variants, and resume_versions. It holds the per-entry reference
// graph (library ref + edited flags + index-aligned bullet refs) that lets
// resume content reference the experience library while resume.data stays a
// materialized snapshot. Absent/{} = a fully manual resume (prior behavior).

migrate(
  (db) => {
    const dao = new Dao(db);
    const JSON_LIMIT = 2 * 1024 * 1024;
    for (const name of ["resumes", "resume_variants", "resume_versions"]) {
      const col = dao.findCollectionByNameOrId(name);
      col.schema.addField(new SchemaField({ name: "links", type: "json", options: { maxSize: JSON_LIMIT } }));
      dao.saveCollection(col);
    }
  },
  (db) => {
    const dao = new Dao(db);
    for (const name of ["resumes", "resume_variants", "resume_versions"]) {
      const col = dao.findCollectionByNameOrId(name);
      const f = col.schema.getFieldByName("links");
      if (f) col.schema.removeField(f.id);
      dao.saveCollection(col);
    }
  },
);
