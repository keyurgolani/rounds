/// <reference path="../pb_data/types.d.ts" />

// Share capabilities (ROUNDS-00B-L03 stage 2).
//
// A share capability is a read grant over one Legacy Artifact Snapshot
// (ROUNDS-00A-L04) of the same account. Every client rule is null: only
// pocketbase/pb_hooks/share_capabilities.js writes these rows
// (docs/security/server-writes.md), and an owner sees its own through the
// hook route the runner calls. Nothing creates a row until #12's create
// route calls create_capability.
//
//   user                  the owner; deleting the account deletes its
//                         capabilities first (share_capabilities.pb.js)
//   target_kind           legacy_artifact_snapshot, the only kind until #80
//   snapshot              the snapshot it grants: required, and not
//                         cascading, so a snapshot a capability names can't
//                         be deleted while the capability exists
//   target_checksum       the snapshot's content_checksum when it was made
//   purpose               the owner's label, 1 to 80 characters, never public
//   expires_at            set when it's made; it only ever moves earlier
//   password_policy_ref   empty, or the verifier #12 stores
//   view_policy           disabled: nothing counts views
//   capability_version    from 1; every rotate and every revoke raises it
//   status                active or revoked; revoked is final
//   revoked_at,
//   revoked_reason        when, and why: owner or source_deleted
//   projection_version    1, the snapshot's markup and nothing else
//   bearer_digest         the keyed digest of the bearer #12 issues; unique
//   digest_key_version    the key version that digest was made under
//
// It also adds the owner-equality triggers for `snapshot` that every typed
// relation in pocketbase/pb_hooks/relation_endpoints.v1.json gets
// (1700007000_relation_endpoint_authz.js), so no writer, a superuser or a
// hook included, can point a capability at another account's snapshot or
// move a named snapshot to another account. The collection has no JSON
// field, so it adds nothing to the JSON limit registry.
//
// down() drops the collection and its triggers only while it holds no
// capability, and otherwise fails and changes nothing.

const COLLECTION = "share_capabilities";
const OWNER = "user";

// The typed relations this migration adds to relation_endpoints.v1.json,
// in that migration's shape (test_relation_endpoint_authz.py reads both).
const FIELDS = [
  { c: "share_capabilities", f: "snapshot", t: "legacy_artifact_snapshots", required: true, cascade: false },
];

migrate(
  (db) => {
    const dao = new Dao(db);
    const users = dao.findCollectionByNameOrId("users");
    const snapshots = dao.findCollectionByNameOrId("legacy_artifact_snapshots");

    const text = (name, pattern, required, max) => ({
      name,
      type: "text",
      required,
      options: { min: null, max: max || null, pattern },
    });
    const number = (name, min, max) => ({
      name,
      type: "number",
      required: true,
      options: { min, max, noDecimal: true },
    });
    const date = (name, required) => ({ name, type: "date", required, options: { min: "", max: "" } });

    const collection = new Collection({
      name: "share_capabilities",
      type: "base",
      listRule: null,
      viewRule: null,
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
        text("target_kind", "^legacy_artifact_snapshot$", true),
        {
          name: "snapshot",
          type: "relation",
          required: true,
          options: { collectionId: snapshots.id, cascadeDelete: false, minSelect: null, maxSelect: 1, displayFields: null },
        },
        text("target_checksum", "^sha256:[0-9a-f]{64}$", true),
        // No control characters; the hook trims it and counts characters.
        text("purpose", "^[^\\x00-\\x1f\\x7f]+$", true, 80),
        date("expires_at", true),
        text("password_policy_ref", "^[!-~]+$", false, 512),
        text("view_policy", "^disabled$", true),
        number("capability_version", 1, null),
        text("status", "^(active|revoked)$", true),
        date("revoked_at", false),
        text("revoked_reason", "^(owner|source_deleted)$", false),
        number("projection_version", 1, 1),
        text("bearer_digest", "^[0-9a-f]{64}$", true),
        number("digest_key_version", 1, 999),
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_share_capabilities_digest ON share_capabilities (bearer_digest)",
        "CREATE INDEX idx_share_capabilities_user ON share_capabilities (user, created)",
        "CREATE INDEX idx_share_capabilities_snapshot ON share_capabilities (snapshot, status)",
      ],
    });
    dao.saveCollection(collection);

    // Owner equality for each relation in FIELDS, as 1700007000 writes it:
    // a row may name only a target its own account owns, and a target
    // can't move to another account while a row names it.
    const q = (sql) => db.newQuery(sql).execute();
    for (let i = 0; i < FIELDS.length; i++) {
      const r = FIELDS[i];
      const base = "rel_authz_" + r.c + "_" + r.f;
      const mismatch =
        'NEW."' + r.f + '" IS NOT NULL AND NEW."' + r.f + "\" != '' AND NOT EXISTS " +
        '(SELECT 1 FROM "' + r.t + '" tgt WHERE tgt."id" = NEW."' + r.f + '" AND tgt."' + OWNER + '" = NEW."' + OWNER + '")';
      // PocketBase's save rewrites every column, so UPDATE OF fires on any
      // save; check the relation only when it, or the row's owner, changed.
      const changed =
        '(NEW."' + r.f + '" IS NOT OLD."' + r.f + '" OR NEW."' + OWNER + '" IS NOT OLD."' + OWNER + '")';
      q('DROP TRIGGER IF EXISTS "' + base + '_ins"');
      q('DROP TRIGGER IF EXISTS "' + base + '_upd"');
      q('DROP TRIGGER IF EXISTS "' + base + '_tgt"');
      q(
        'CREATE TRIGGER "' + base + '_ins" BEFORE INSERT ON "' + r.c + '" FOR EACH ROW WHEN ' +
        mismatch + " BEGIN SELECT RAISE(ABORT, 'relation endpoint denied'); END",
      );
      q(
        'CREATE TRIGGER "' + base + '_upd" BEFORE UPDATE OF "' + r.f + '", "' + OWNER + '" ON "' + r.c +
        '" FOR EACH ROW WHEN ' + changed + " AND " + mismatch +
        " BEGIN SELECT RAISE(ABORT, 'relation endpoint denied'); END",
      );
      q(
        'CREATE TRIGGER "' + base + '_tgt" BEFORE UPDATE OF "' + OWNER + '" ON "' + r.t +
        '" FOR EACH ROW WHEN NEW."' + OWNER + '" != OLD."' + OWNER + '" AND EXISTS ' +
        '(SELECT 1 FROM "' + r.c + '" src WHERE src."' + r.f + '" = OLD."id" AND src."' + OWNER + '" != NEW."' + OWNER + '") ' +
        "BEGIN SELECT RAISE(ABORT, 'relation endpoint denied'); END",
      );
    }
  },

  (db) => {
    const dao = new Dao(db);
    let collection;
    try {
      collection = dao.findCollectionByNameOrId(COLLECTION);
    } catch (_) {
      return; // already gone
    }
    const count = new DynamicModel({ n: 0 });
    db.newQuery("SELECT COUNT(*) AS n FROM " + COLLECTION).one(count);
    if (count.n > 0) {
      throw new Error(
        COLLECTION + " still holds capabilities, so this down step keeps it; " +
          "reverting #11 stage 2 never deletes one (docs/operations.md)",
      );
    }
    // Dropping the table drops the triggers on it; the one on the target
    // table names this table, so it goes too.
    for (let i = 0; i < FIELDS.length; i++) {
      db.newQuery('DROP TRIGGER IF EXISTS "rel_authz_' + FIELDS[i].c + "_" + FIELDS[i].f + '_tgt"').execute();
    }
    dao.deleteCollection(collection);
  },
);
