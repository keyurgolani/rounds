/// <reference path="../pb_data/types.d.ts" />

// Multi-provider AI: one user can configure several provider entries
// (Anthropic, OpenAI, OpenAI-compatible, Anthropic-compatible) and
// then assign a model from any of them to two roles: text and vision.
//
// Schema changes:
//   * New collection ``ai_providers`` — provider entries with their
//     own key, base_url, kind, and a cached model list.
//   * ``ai_settings`` is dropped and recreated as a thin role-mapping
//     row: text_provider + text_model and vision_provider + vision_model.
//
// We don't try to migrate existing ai_settings rows. The previous
// shape stored a single key under ai_settings directly; users will
// re-add their key once after this migration. There are no production
// users on this collection yet — small dev cost for a much cleaner
// data model going forward.

migrate(
  (db) => {
    const dao = new Dao(db);
    const JSON_LIMIT = 256 * 1024;
    const json = (name) => ({
      name,
      type: "json",
      options: { maxSize: JSON_LIMIT },
    });

    const users = dao.findCollectionByNameOrId("users");
    const ownerRule = "user = @request.auth.id";
    const createIfAuthed = '@request.auth.id != ""';

    // 1) Drop the old ai_settings (single-provider shape).
    try {
      const old = dao.findCollectionByNameOrId("ai_settings");
      dao.deleteCollection(old);
    } catch (_) {
      /* not present — fine */
    }

    // 2) New ai_providers collection.
    const aiProviders = new Collection({
      name: "ai_providers",
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
          name: "kind",
          type: "select",
          required: true,
          options: {
            maxSelect: 1,
            values: [
              "anthropic",
              "openai",
              "openai-compatible",
              "anthropic-compatible",
            ],
          },
        },
        { name: "label", type: "text", required: true },
        { name: "base_url", type: "text" },
        { name: "encrypted_key", type: "text" },
        { name: "key_iv", type: "text" },
        json("models_cache"),
        { name: "models_cached_at", type: "text" },
      ],
      indexes: [
        "CREATE INDEX idx_ai_providers_user ON ai_providers (user)",
      ],
    });
    dao.saveCollection(aiProviders);

    // 3) Recreated ai_settings — role-mapping only.
    const aiSettings = new Collection({
      name: "ai_settings",
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
          name: "text_provider",
          type: "relation",
          options: {
            collectionId: aiProviders.id,
            cascadeDelete: false,
            maxSelect: 1,
          },
        },
        { name: "text_model", type: "text" },
        {
          name: "vision_provider",
          type: "relation",
          options: {
            collectionId: aiProviders.id,
            cascadeDelete: false,
            maxSelect: 1,
          },
        },
        { name: "vision_model", type: "text" },
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_ai_settings_user ON ai_settings (user)",
      ],
    });
    dao.saveCollection(aiSettings);
  },

  // Down — drop both. We don't recreate the legacy ai_settings shape;
  // running this in reverse leaves no AI configuration tables, which
  // is fine for rollback hygiene.
  (db) => {
    const dao = new Dao(db);
    for (const name of ["ai_settings", "ai_providers"]) {
      try {
        dao.deleteCollection(dao.findCollectionByNameOrId(name));
      } catch (_) {
        /* ignore */
      }
    }
  },
);
