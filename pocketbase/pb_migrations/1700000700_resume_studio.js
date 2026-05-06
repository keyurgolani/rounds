/// <reference path="../pb_data/types.d.ts" />

// Resume Studio collections. Mirrors the conventions in
// 1700000000_init_collections.js: per-row ownership via `user`, the
// canonical `ownerRule`/`createIfAuthed` access rules, and 2 MB JSON
// fields for the larger structured payloads (the resume document
// itself, ATS breakdowns, version snapshots, etc.).
//
// New collections:
//   resumes              — master resume documents (data = canonical ResumeData)
//   resume_variants      — job-tailored copies, optionally linked to an Application
//   resume_versions      — auto + manual snapshots for restore/diff
//   resume_bullets       — reusable bullets, tagged by skill/tech, optionally
//                          sourced from an existing behavioral anecdote
//   ai_settings          — per-user AI provider config + encrypted key blob
//   resume_share_links   — public token URLs for read-only sharing
//   resume_share_views   — view tracking for share links
//
// Notes on design:
// - `resume_variants.application` is an optional 1:1 relation to applications.
//   That covers the common case (one variant per Application). A many-to-many
//   join table would be over-design for v1; the existing `applications.resume_variant`
//   text field can also be populated with the primary variant id when useful.
// - `resume_share_*` rules are owner-only here. Phase 7 will refactor them
//   so anonymous reads work for `/r/:token` viewers.

migrate(
  (db) => {
    const dao = new Dao(db);

    const JSON_LIMIT = 2 * 1024 * 1024; // 2 MB per JSON field
    const json = (name) => ({
      name,
      type: "json",
      options: { maxSize: JSON_LIMIT },
    });

    const users = dao.findCollectionByNameOrId("users");
    const applications = dao.findCollectionByNameOrId("applications");
    const anecdotes = dao.findCollectionByNameOrId("anecdotes");

    const ownerRule = "user = @request.auth.id";
    const createIfAuthed = '@request.auth.id != ""';

    // ---- resumes -----------------------------------------------------
    const resumes = new Collection({
      name: "resumes",
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
        { name: "name", type: "text", required: true },
        { name: "slug", type: "text", required: true, options: { pattern: "^[a-z0-9-]+$" } },
        { name: "template_id", type: "text" },
        json("design"),
        json("data"),
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_resumes_user_slug ON resumes (user, slug)",
        "CREATE INDEX idx_resumes_user ON resumes (user)",
      ],
    });
    dao.saveCollection(resumes);

    // ---- resume_variants --------------------------------------------
    const resumeVariants = new Collection({
      name: "resume_variants",
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
          name: "resume",
          type: "relation",
          required: true,
          options: { collectionId: resumes.id, cascadeDelete: true, maxSelect: 1 },
        },
        { name: "name", type: "text", required: true },
        { name: "target_company", type: "text" },
        { name: "job_title", type: "text" },
        { name: "job_description", type: "text" },
        { name: "tone", type: "text" },
        json("role_focus"),
        json("data"),
        { name: "ats_score", type: "number" },
        json("ats_breakdown"),
        {
          name: "application",
          type: "relation",
          options: { collectionId: applications.id, cascadeDelete: false, maxSelect: 1 },
        },
      ],
      indexes: [
        "CREATE INDEX idx_variants_user ON resume_variants (user)",
        "CREATE INDEX idx_variants_resume ON resume_variants (resume)",
        "CREATE INDEX idx_variants_application ON resume_variants (application)",
      ],
    });
    dao.saveCollection(resumeVariants);

    // ---- resume_versions --------------------------------------------
    // Snapshot rows. Either `resume` or `variant` is set (xor) — enforced
    // at the API layer rather than via PB constraints.
    const resumeVersions = new Collection({
      name: "resume_versions",
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
          name: "resume",
          type: "relation",
          options: { collectionId: resumes.id, cascadeDelete: true, maxSelect: 1 },
        },
        {
          name: "variant",
          type: "relation",
          options: { collectionId: resumeVariants.id, cascadeDelete: true, maxSelect: 1 },
        },
        json("data"),
        { name: "label", type: "text" },
        { name: "is_auto", type: "bool" },
      ],
      indexes: [
        "CREATE INDEX idx_versions_user ON resume_versions (user)",
        "CREATE INDEX idx_versions_resume ON resume_versions (resume)",
        "CREATE INDEX idx_versions_variant ON resume_versions (variant)",
      ],
    });
    dao.saveCollection(resumeVersions);

    // ---- resume_bullets ---------------------------------------------
    const resumeBullets = new Collection({
      name: "resume_bullets",
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
        { name: "text", type: "text", required: true },
        json("tags"),
        {
          name: "source_anecdote",
          type: "relation",
          options: { collectionId: anecdotes.id, cascadeDelete: false, maxSelect: 1 },
        },
        json("metrics"),
      ],
      indexes: [
        "CREATE INDEX idx_bullets_user ON resume_bullets (user)",
        "CREATE INDEX idx_bullets_anecdote ON resume_bullets (source_anecdote)",
      ],
    });
    dao.saveCollection(resumeBullets);

    // ---- ai_settings ------------------------------------------------
    // One row per user. `encrypted_key` + `key_iv` form an AES-GCM
    // ciphertext blob; the wrapping KEK is held server-side.
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
        { name: "provider", type: "text" },
        { name: "model", type: "text" },
        { name: "import_model", type: "text" },
        { name: "base_url", type: "text" },
        { name: "encrypted_key", type: "text" },
        { name: "key_iv", type: "text" },
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_ai_settings_user ON ai_settings (user)",
      ],
    });
    dao.saveCollection(aiSettings);

    // ---- resume_share_links -----------------------------------------
    // Public read for `/r/:token` is deferred to Phase 7; v1 keeps owner
    // rules. The token itself is unguessable enough to be safe to expose
    // once the rule loosens.
    const shareLinks = new Collection({
      name: "resume_share_links",
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
          name: "variant",
          type: "relation",
          required: true,
          options: { collectionId: resumeVariants.id, cascadeDelete: true, maxSelect: 1 },
        },
        { name: "token", type: "text", required: true },
        { name: "is_password", type: "bool" },
        { name: "password_hash", type: "text" },
        { name: "expires_at", type: "text" },
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_share_links_token ON resume_share_links (token)",
        "CREATE INDEX idx_share_links_user ON resume_share_links (user)",
      ],
    });
    dao.saveCollection(shareLinks);

    // ---- resume_share_views -----------------------------------------
    const shareViews = new Collection({
      name: "resume_share_views",
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
          name: "link",
          type: "relation",
          required: true,
          options: { collectionId: shareLinks.id, cascadeDelete: true, maxSelect: 1 },
        },
        { name: "viewer_ip_hash", type: "text" },
        { name: "user_agent", type: "text" },
        { name: "viewed_at", type: "text" },
      ],
      indexes: [
        "CREATE INDEX idx_share_views_link ON resume_share_views (link)",
      ],
    });
    dao.saveCollection(shareViews);
  },

  // Rollback — drop in reverse dependency order.
  (db) => {
    const dao = new Dao(db);
    for (const name of [
      "resume_share_views",
      "resume_share_links",
      "ai_settings",
      "resume_bullets",
      "resume_versions",
      "resume_variants",
      "resumes",
    ]) {
      try {
        const c = dao.findCollectionByNameOrId(name);
        dao.deleteCollection(c);
      } catch (_) {
        /* already dropped */
      }
    }
  },
);
