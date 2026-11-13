/// <reference path="../pb_data/types.d.ts" />

// Saved AI provider keys and model lists, kept server-side (ROUNDS-14-L02
// stage A).
//
// Two collections, both with every client rule null: only the hook routes
// in pocketbase/pb_hooks/ai_custody.pb.js write or read them
// (docs/security/server-writes.md), with the caller's bearer and the
// runner key, and the runner is the only process that opens a key.
//
// ai_credentials holds one provider's saved key, wrapped by the runner's
// keyring (backend/app/provider_gateway/keyring.py):
//
//   user               the owner; deleting the account deletes its keys
//   provider           the provider the key belongs to; one key a provider,
//                      deleted with it
//   wrap               aad-v1, or legacy-v0 for a key saved before this
//                      release, until its first good use rewraps it
//   key_version        the keyring's root version, 1
//   ciphertext,
//   nonce              the wrapped key, base64
//   registered_host,
//   registered_port    the address the key was entered for; empty on a
//                      legacy-v0 key, whose provider keeps the address it
//                      had until the key is entered again or rewrapped
//   status             active, or suspect-planted for a key that also sits
//                      under another account, which never opens
//   legacy_ciphertext,
//   legacy_nonce       the pair the provider row held before the move, kept
//                      for the move's down step (1700008820) until the key
//                      is entered again
//
// ai_provider_models is a provider's model list: one row a model, from the
// provider's own list (registry) or named by its owner for a compatible
// endpoint (user-declared).
//
// It also adds the owner-equality triggers for both `provider` relations
// that every typed relation in pocketbase/pb_hooks/relation_endpoints.v1.json
// gets (1700007000_relation_endpoint_authz.js), so no writer, a superuser or
// a hook included, can attach a key or a model to another account's
// provider, or move a provider that has them to another account. Neither
// collection has a JSON field, so this adds nothing to the JSON limit
// registry.
//
// down() drops both collections and their triggers only while they hold no
// row, and otherwise fails and changes nothing; 1700008820's down step
// empties them first.

const OWNER = "user";
const COLLECTIONS = ["ai_credentials", "ai_provider_models"];

// The typed relations this migration adds to relation_endpoints.v1.json,
// in 1700007000's shape (test_relation_endpoint_authz.py reads both).
const FIELDS = [
  { c: "ai_credentials", f: "provider", t: "ai_providers", required: true, cascade: true },
  { c: "ai_provider_models", f: "provider", t: "ai_providers", required: true, cascade: true },
];

const BASE64 = "^[A-Za-z0-9+/]+={0,2}$";
// A 96-bit nonce, base64.
const NONCE = "^[A-Za-z0-9+/]{16}$";
// A wrapped key of up to 4096 bytes and its tag, base64, with room.
const CIPHERTEXT_MAX = 8192;

migrate(
  (db) => {
    const dao = new Dao(db);
    const users = dao.findCollectionByNameOrId("users");
    const providers = dao.findCollectionByNameOrId("ai_providers");

    const text = (name, pattern, required, max) => ({
      name,
      type: "text",
      required,
      options: { min: null, max: max || null, pattern },
    });
    const number = (name, min, max, required) => ({
      name,
      type: "number",
      required,
      options: { min, max, noDecimal: true },
    });

    dao.saveCollection(
      new Collection({
        name: "ai_credentials",
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
          {
            name: "provider",
            type: "relation",
            required: true,
            options: { collectionId: providers.id, cascadeDelete: true, minSelect: null, maxSelect: 1, displayFields: null },
          },
          text("wrap", "^(legacy-v0|aad-v1)$", true),
          number("key_version", 1, 999, true),
          text("ciphertext", BASE64, true, CIPHERTEXT_MAX),
          text("nonce", NONCE, true),
          text("registered_host", "^[a-z0-9._:-]{1,253}$", false, 253),
          number("registered_port", 1, 65535, false),
          text("status", "^(active|suspect-planted)$", true),
          text("legacy_ciphertext", BASE64, false, CIPHERTEXT_MAX),
          text("legacy_nonce", NONCE, false),
        ],
        indexes: [
          "CREATE UNIQUE INDEX idx_ai_credentials_provider ON ai_credentials (provider)",
          "CREATE INDEX idx_ai_credentials_user ON ai_credentials (user)",
        ],
      }),
    );

    dao.saveCollection(
      new Collection({
        name: "ai_provider_models",
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
          {
            name: "provider",
            type: "relation",
            required: true,
            options: { collectionId: providers.id, cascadeDelete: true, minSelect: null, maxSelect: 1, displayFields: null },
          },
          // A model id as its provider names it: no control characters.
          text("model", "^[^\\x00-\\x1f\\x7f]+$", true, 256),
          text("verification", "^(registry|user-declared)$", true),
        ],
        indexes: [
          "CREATE UNIQUE INDEX idx_ai_provider_models_model ON ai_provider_models (provider, model)",
          "CREATE INDEX idx_ai_provider_models_user ON ai_provider_models (user)",
        ],
      }),
    );

    // Owner equality for each relation in FIELDS, as 1700007000 writes it:
    // a row may name only a provider its own account owns, and a provider
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
    const found = [];
    for (let i = 0; i < COLLECTIONS.length; i++) {
      try {
        found.push(dao.findCollectionByNameOrId(COLLECTIONS[i]));
      } catch (_) {
        // already gone
      }
    }
    for (let i = 0; i < found.length; i++) {
      const count = new DynamicModel({ n: 0 });
      db.newQuery('SELECT COUNT(*) AS n FROM "' + found[i].name + '"').one(count);
      if (count.n > 0) {
        throw new Error(
          found[i].name + " still holds rows, so this down step keeps it; " +
            "run 1700008820's down step first (docs/operations.md)",
        );
      }
    }
    // Dropping a table drops the triggers on it; the one on ai_providers
    // names these tables, so it goes too.
    for (let i = 0; i < FIELDS.length; i++) {
      db.newQuery('DROP TRIGGER IF EXISTS "rel_authz_' + FIELDS[i].c + "_" + FIELDS[i].f + '_tgt"').execute();
    }
    for (let i = 0; i < found.length; i++) dao.deleteCollection(found[i]);
  },
);
