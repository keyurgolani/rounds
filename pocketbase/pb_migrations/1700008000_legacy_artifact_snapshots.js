/// <reference path="../pb_data/types.d.ts" />

// Legacy Artifact Snapshots (ROUNDS-00A-L04, PR 1).
//
// One immutable, account-scoped snapshot of a resume or variant, built by
// the materializer (backend/materializer/) from records PocketBase reads
// itself, never from markup a caller sends. Its owner can list and view
// it; create, update, and delete are null, so only a PocketBase hook writes
// it, and only #4's PR 2 adds that hook (docs/security/server-writes.md).
// This migration adds the store and nothing writes it yet.
//
//   user                  the owner; deleting the account deletes its
//                         snapshots and their files
//   source_kind           resume or variant
//   source_id             the resume's or variant's id, as plain text, so
//                         deleting the source leaves its snapshots for #76
//   source_updated        the source's `updated` the snapshot was built from
//   parent_id,
//   parent_updated        a variant's parent resume, which its template and
//                         design come from; empty for a resume
//   template_id           the template rendered, after any fallback
//   template_fallback     true when the source named no known template
//   design                the design normalized to #2's Artifact Renderer
//                         Contract overrides
//   data                  the normalized ResumeData that was rendered
//   markup                the rendered HTML document, a protected file
//   content_checksum      sha256: and the hex SHA-256 of markup's bytes
//   materializer_digest   the materializer bundle's SHA-256, which is the
//                         template version
//   sanitizer_version     the output-check rules the markup passed
//   font_families         the font ids the markup names
//   size_bytes            markup's size
//
// The unique index keeps reuse inside one source: the same source, bytes,
// and materializer digest are one snapshot, and a variant whose markup
// matches its parent's still gets its own.
//
// Every JSON field sets maxSize, so a database that upgraded across
// PocketBase's size default still validates them (1700007000's JSON_MAX).
//
// down() drops the collection only while it holds no snapshot, and
// otherwise fails and changes nothing, so reverting never deletes one.

migrate(
  (db) => {
    const dao = new Dao(db);
    const users = dao.findCollectionByNameOrId("users");

    const ID = "^[a-z0-9]{15}$";
    const OPTIONAL_ID = "^([a-z0-9]{15})?$";
    // PocketBase's own datetime text, as `updated` reads.
    const UPDATED = "^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$";
    const OPTIONAL_UPDATED = "^([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z)?$";
    const SHA256 = "^sha256:[0-9a-f]{64}$";
    const MAX_MARKUP_BYTES = 2 * 1024 * 1024;
    const text = (name, pattern, required = true) => ({
      name,
      type: "text",
      required,
      options: { min: null, max: null, pattern },
    });

    const snapshots = new Collection({
      name: "legacy_artifact_snapshots",
      type: "base",
      listRule: "user = @request.auth.id",
      viewRule: "user = @request.auth.id",
      createRule: null,
      updateRule: null,
      deleteRule: null,
      schema: [
        {
          name: "user",
          type: "relation",
          required: true,
          options: { collectionId: users.id, cascadeDelete: true, minSelect: null, maxSelect: 1, displayFields: null },
        },
        text("source_kind", "^(resume|variant)$"),
        text("source_id", ID),
        text("source_updated", UPDATED),
        text("parent_id", OPTIONAL_ID, false),
        text("parent_updated", OPTIONAL_UPDATED, false),
        text("template_id", "^[a-z0-9-]{1,64}$"),
        { name: "template_fallback", type: "bool", required: false, options: {} },
        // Not required: a design with no overrides normalizes to {}, which
        // PocketBase counts as blank.
        { name: "design", type: "json", required: false, options: { maxSize: 64 * 1024 } },
        { name: "data", type: "json", required: true, options: { maxSize: 2 * 1024 * 1024 } },
        {
          name: "markup",
          type: "file",
          required: true,
          options: {
            maxSelect: 1,
            maxSize: MAX_MARKUP_BYTES,
            mimeTypes: ["text/html"],
            thumbs: [],
            protected: true,
          },
        },
        text("content_checksum", SHA256),
        text("materializer_digest", SHA256),
        text("sanitizer_version", "^[0-9]+\\.[0-9]+\\.[0-9]+$"),
        { name: "font_families", type: "json", required: false, options: { maxSize: 4 * 1024 } },
        {
          name: "size_bytes",
          type: "number",
          required: true,
          options: { min: 1, max: MAX_MARKUP_BYTES, noDecimal: true },
        },
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_legacy_artifact_snapshots_reuse ON legacy_artifact_snapshots " +
          "(user, source_kind, source_id, content_checksum, materializer_digest)",
      ],
    });
    dao.saveCollection(snapshots);
  },

  (db) => {
    const dao = new Dao(db);
    let collection;
    try {
      collection = dao.findCollectionByNameOrId("legacy_artifact_snapshots");
    } catch (_) {
      return; // already gone
    }
    const count = new DynamicModel({ n: 0 });
    db.newQuery("SELECT COUNT(*) AS n FROM legacy_artifact_snapshots").one(count);
    if (count.n > 0) {
      throw new Error(
        "legacy_artifact_snapshots still holds snapshots, so this down step keeps it; " +
          "reverting #4 never deletes a snapshot (docs/operations.md)",
      );
    }
    dao.deleteCollection(collection);
  },
);
