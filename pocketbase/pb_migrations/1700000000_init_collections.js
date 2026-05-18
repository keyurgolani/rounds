/// <reference path="../pb_data/types.d.ts" />

// Single source of truth for the schema. Creates every collection
// Rounds needs in its final shape and extends the built-in `users`
// auth collection. JSON fields ship with `maxSize` set so PB 0.22+
// accepts writes without retrofitting.

migrate(
  (db) => {
    const dao = new Dao(db);

    const JSON_LIMIT = 2 * 1024 * 1024; // 2 MB per JSON field
    const json = (name) => ({
      name,
      type: "json",
      options: { maxSize: JSON_LIMIT },
    });
    const guideJson = (name) => ({
      name,
      type: "json",
      options: { maxSize: 4 * 1024 * 1024 },
    });

    // ---- Extend built-in `users` collection -------------------------
    const users = dao.findCollectionByNameOrId("users");
    users.schema.addField(new SchemaField({ name: "bio", type: "text" }));
    users.schema.addField(new SchemaField({ name: "target", type: "text" }));
    dao.saveCollection(users);

    // ---- Shared content collections ---------------------------------
    // Public-read for any authenticated user; writes locked to admin.
    const readForAuthed = '@request.auth.id != ""';

    const systemDesign = new Collection({
      name: "system_design_questions",
      type: "base",
      listRule: readForAuthed,
      viewRule: readForAuthed,
      createRule: null,
      updateRule: null,
      deleteRule: null,
      schema: [
        { name: "title", type: "text", required: true },
        { name: "slug", type: "text", required: true, options: { pattern: "^[a-z0-9-]+$" } },
        { name: "difficulty", type: "text" },
        { name: "description", type: "editor", required: true },
        json("hints"),
        json("constraints"),
        json("requirements_functional"),
        json("requirements_nonfunctional"),
        json("estimation"),
        json("api_design"),
        json("database_schema"),
        json("high_level_design"),
        json("detailed_design"),
        json("trade_offs"),
        json("tips"),
        json("thought_process"),
        json("tags"),
        json("architecture_diagram"),
        { name: "sequence_diagram", type: "text" },
        { name: "er_diagram", type: "text" },
        { name: "thought_flow", type: "text" },
        json("tradeoff_visual"),
        json("senior_topics"),
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_sdq_slug ON system_design_questions (slug)",
      ],
    });
    dao.saveCollection(systemDesign);

    const coding = new Collection({
      name: "coding_questions",
      type: "base",
      listRule: readForAuthed,
      viewRule: readForAuthed,
      createRule: null,
      updateRule: null,
      deleteRule: null,
      schema: [
        { name: "title", type: "text", required: true },
        { name: "slug", type: "text", required: true, options: { pattern: "^[a-z0-9-]+$" } },
        { name: "difficulty", type: "text" },
        { name: "description", type: "editor", required: true },
        json("hints"),
        json("constraints"),
        json("starter_code"),
        json("boilerplate_code"),
        json("test_cases"),
        json("solutions"),
        json("thought_process"),
        json("tips"),
        json("companies"),
        json("topics"),
        {
          name: "entry",
          type: "json",
          required: true,
          options: { maxSize: 64 * 1024 },
        },
        { name: "time_complexity", type: "text" },
        { name: "space_complexity", type: "text" },
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_cq_slug ON coding_questions (slug)",
      ],
    });
    dao.saveCollection(coding);

    const behavioralCategories = new Collection({
      name: "behavioral_categories",
      type: "base",
      listRule: readForAuthed,
      viewRule: readForAuthed,
      createRule: null,
      updateRule: null,
      deleteRule: null,
      schema: [
        { name: "name", type: "text", required: true },
        { name: "description", type: "text" },
        { name: "color", type: "text" },
        { name: "icon", type: "text" },
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_bc_name ON behavioral_categories (name)",
      ],
    });
    dao.saveCollection(behavioralCategories);

    const behavioralQuestions = new Collection({
      name: "behavioral_questions",
      type: "base",
      listRule: readForAuthed,
      viewRule: readForAuthed,
      createRule: null,
      updateRule: null,
      deleteRule: null,
      schema: [
        { name: "title", type: "text", required: true },
        { name: "slug", type: "text", required: true, options: { pattern: "^[a-z0-9-]+$" } },
        { name: "question_text", type: "text", required: true },
        {
          name: "categories",
          type: "relation",
          options: {
            collectionId: behavioralCategories.id,
            cascadeDelete: false,
            maxSelect: null,
          },
        },
        json("star_guide"),
        json("sample_response"),
        json("tips"),
        json("common_pitfalls"),
        json("follow_up_questions"),
        json("what_interviewers_look_for"),
        json("tags"),
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_bq_slug ON behavioral_questions (slug)",
      ],
    });
    dao.saveCollection(behavioralQuestions);

    const guideSchema = () => [
      { name: "title", type: "text", required: true },
      { name: "slug", type: "text", required: true, options: { pattern: "^[a-z0-9-]+$" } },
      { name: "description", type: "editor", required: true },
      guideJson("sections"),
      guideJson("checklists"),
      guideJson("resources"),
    ];

    const systemDesignGuides = new Collection({
      name: "system_design_guides",
      type: "base",
      listRule: readForAuthed,
      viewRule: readForAuthed,
      createRule: null,
      updateRule: null,
      deleteRule: null,
      schema: guideSchema(),
      indexes: [
        "CREATE UNIQUE INDEX idx_system_design_guides_slug ON system_design_guides (slug)",
      ],
    });
    dao.saveCollection(systemDesignGuides);

    const codingGuides = new Collection({
      name: "coding_guides",
      type: "base",
      listRule: readForAuthed,
      viewRule: readForAuthed,
      createRule: null,
      updateRule: null,
      deleteRule: null,
      schema: guideSchema(),
      indexes: ["CREATE UNIQUE INDEX idx_coding_guides_slug ON coding_guides (slug)"],
    });
    dao.saveCollection(codingGuides);

    const behavioralGuides = new Collection({
      name: "behavioral_guides",
      type: "base",
      listRule: readForAuthed,
      viewRule: readForAuthed,
      createRule: null,
      updateRule: null,
      deleteRule: null,
      schema: guideSchema(),
      indexes: ["CREATE UNIQUE INDEX idx_behavioral_guides_slug ON behavioral_guides (slug)"],
    });
    dao.saveCollection(behavioralGuides);

    // ---- User-scoped collections -----------------------------------
    // One canonical rule: rows belong to a single user, only that user
    // can CRUD them. `@request.auth.id != ""` blocks anonymous reads.
    const ownerRule = "user = @request.auth.id";
    const createIfAuthed = '@request.auth.id != ""';

    const anecdotes = new Collection({
      name: "anecdotes",
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
        { name: "title", type: "text", required: true },
        { name: "description", type: "text" },
        { name: "situation", type: "text" },
        { name: "task", type: "text" },
        { name: "action", type: "text" },
        { name: "result", type: "text" },
        {
          name: "categories",
          type: "relation",
          options: {
            collectionId: behavioralCategories.id,
            cascadeDelete: false,
            maxSelect: null,
          },
        },
        {
          name: "linked_questions",
          type: "relation",
          options: {
            collectionId: behavioralQuestions.id,
            cascadeDelete: false,
            maxSelect: null,
          },
        },
        { name: "notes", type: "text" },
      ],
      indexes: ["CREATE INDEX idx_anecdotes_user ON anecdotes (user)"],
    });
    dao.saveCollection(anecdotes);

    // Campaigns must exist before any collection that references them.
    const campaigns = new Collection({
      name: "campaigns",
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
        { name: "description", type: "text" },
        { name: "target_role_level", type: "text" },
        json("target_companies"),
        { name: "start_date", type: "text" },
        { name: "end_date", type: "text" },
        {
          name: "status",
          type: "select",
          options: { maxSelect: 1, values: ["planning", "active", "wrapped"] },
        },
        { name: "color", type: "text" },
        { name: "is_default", type: "bool" },
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_campaigns_user_slug ON campaigns (user, slug)",
        "CREATE INDEX idx_campaigns_user_status ON campaigns (user, status)",
      ],
    });
    dao.saveCollection(campaigns);

    const applications = new Collection({
      name: "applications",
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
        { name: "company", type: "text", required: true },
        { name: "role", type: "text", required: true },
        { name: "status", type: "text" },
        { name: "applied_date", type: "text" },
        { name: "notes", type: "text" },
        { name: "resume_variant", type: "text" },
        { name: "url", type: "url", options: { exceptDomains: [], onlyDomains: [] } },
        { name: "job_description", type: "text" },
        {
          name: "campaign",
          type: "relation",
          options: { collectionId: campaigns.id, cascadeDelete: false, maxSelect: 1 },
        },
        { name: "last_activity_at", type: "text" },
      ],
      indexes: ["CREATE INDEX idx_applications_user ON applications (user)"],
    });
    dao.saveCollection(applications);

    const rounds = new Collection({
      name: "interview_rounds",
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
          name: "application",
          type: "relation",
          required: true,
          options: { collectionId: applications.id, cascadeDelete: true, maxSelect: 1 },
        },
        { name: "round_type", type: "text", required: true },
        { name: "date", type: "text" },
        { name: "interviewer", type: "text" },
        json("questions_asked"),
        { name: "notes", type: "text" },
        { name: "result", type: "text" },
        {
          name: "campaign",
          type: "relation",
          options: { collectionId: campaigns.id, cascadeDelete: false, maxSelect: 1 },
        },
        {
          name: "scheduled_status",
          type: "select",
          options: { maxSelect: 1, values: ["scheduled", "completed", "canceled"] },
        },
        { name: "preparation_notes", type: "text" },
        // Optional free-text label used to group rounds into an
        // interview "loop" (e.g. a Meta onsite of 6 rounds across 2
        // days). Empty/null means a one-off round. Kept as text (not
        // a relation) — see migration 1700001600 for rationale.
        { name: "loop_label", type: "text" },
        // Scheduled round length in minutes. Optional — empty/null
        // renders as "—" in the UI. See migration 1700001700.
        {
          name: "duration_minutes",
          type: "number",
          options: { min: 0, max: 1440 },
        },
      ],
      indexes: [
        "CREATE INDEX idx_rounds_user ON interview_rounds (user)",
        "CREATE INDEX idx_rounds_app ON interview_rounds (application)",
      ],
    });
    dao.saveCollection(rounds);

    const progress = new Collection({
      name: "user_progress",
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
          name: "question_type",
          type: "select",
          required: true,
          options: { maxSelect: 1, values: ["system", "coding", "behavioral"] },
        },
        { name: "question_slug", type: "text", required: true },
        {
          name: "status",
          type: "select",
          options: { maxSelect: 1, values: ["todo", "in-progress", "mastered"] },
        },
        { name: "notes", type: "text" },
        { name: "confidence", type: "number" },
        { name: "completed_at", type: "date" },
        {
          name: "campaign",
          type: "relation",
          options: { collectionId: campaigns.id, cascadeDelete: false, maxSelect: 1 },
        },
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_progress_user_campaign_question ON user_progress (user, campaign, question_type, question_slug)",
      ],
    });
    dao.saveCollection(progress);

    const preferences = new Collection({
      name: "user_preferences",
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
        { name: "theme", type: "text" },
        { name: "accent", type: "text" },
        { name: "type_variant", type: "text" },
        { name: "density", type: "text" },
        { name: "nav_style", type: "text" },
        { name: "card_treatment", type: "text" },
        { name: "sans_font", type: "text" },
        { name: "radius", type: "text" },
        { name: "shadow", type: "text" },
        { name: "card_accent", type: "text" },
        { name: "app_background", type: "text" },
        { name: "glass_transparency", type: "number" },
        { name: "glass_frost", type: "number" },
        { name: "glass_shadow", type: "number" },
        {
          name: "current_campaign",
          type: "relation",
          options: { collectionId: campaigns.id, cascadeDelete: false, maxSelect: 1 },
        },
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_prefs_user ON user_preferences (user)",
      ],
    });
    dao.saveCollection(preferences);

    // ---- Offers (1:1 with applications) ----------------------------
    const offers = new Collection({
      name: "offers",
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
          name: "application",
          type: "relation",
          required: true,
          options: { collectionId: applications.id, cascadeDelete: true, maxSelect: 1 },
        },
        {
          name: "status",
          type: "select",
          required: true,
          options: {
            maxSelect: 1,
            values: ["pending", "accepted", "declined", "expired"],
          },
        },
        { name: "base_salary", type: "number" },
        { name: "equity_type", type: "text" },
        { name: "equity_amount", type: "text" },
        { name: "equity_vest_schedule", type: "text" },
        { name: "sign_on", type: "number" },
        { name: "annual_bonus_target_pct", type: "number" },
        { name: "relocation", type: "text" },
        {
          name: "visa_sponsorship",
          type: "select",
          options: { maxSelect: 1, values: ["yes", "no", "n/a"] },
        },
        { name: "remote_policy", type: "text" },
        { name: "pto", type: "text" },
        { name: "decision_deadline", type: "text" },
        { name: "letter_url", type: "url", options: { exceptDomains: [], onlyDomains: [] } },
        { name: "notes", type: "text" },
        json("trail"),
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_offers_user_application ON offers (user, application)",
        "CREATE INDEX idx_offers_status ON offers (status)",
      ],
    });
    dao.saveCollection(offers);

    // ---- Code drafts ----------------------------------------------
    const codeDrafts = new Collection({
      name: "code_drafts",
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
          name: "campaign",
          type: "relation",
          required: true,
          options: { collectionId: campaigns.id, cascadeDelete: true, maxSelect: 1 },
        },
        { name: "question", type: "text", required: true },
        { name: "language", type: "text", required: true },
        { name: "code", type: "text", required: true },
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_drafts_user_campaign_q_lang ON code_drafts (user, campaign, question, language)",
      ],
    });
    dao.saveCollection(codeDrafts);

    // ---- Todos -----------------------------------------------------
    // Single-field todo: `body` holds the raw markdown with mention
    // tokens (`[[type:slug|label]]`); `mentions` is kept in sync by
    // the client so at-risk queries don't re-parse the body.
    const todos = new Collection({
      name: "todos",
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
          name: "campaign",
          type: "relation",
          required: true,
          options: { collectionId: campaigns.id, cascadeDelete: true, maxSelect: 1 },
        },
        { name: "body", type: "text" },
        json("mentions"),
        { name: "due_date", type: "text" },
        {
          name: "priority",
          type: "select",
          options: { maxSelect: 1, values: ["low", "normal", "high"] },
        },
        { name: "completed_at", type: "text" },
      ],
      indexes: [
        "CREATE INDEX idx_todos_user_campaign ON todos (user, campaign)",
        "CREATE INDEX idx_todos_user_due ON todos (user, due_date)",
      ],
    });
    dao.saveCollection(todos);
  },

  // Rollback — drop in reverse dependency order.
  (db) => {
    const dao = new Dao(db);
    for (const name of [
      "todos",
      "code_drafts",
      "offers",
      "user_preferences",
      "user_progress",
      "interview_rounds",
      "applications",
      "campaigns",
      "anecdotes",
      "behavioral_guides",
      "coding_guides",
      "system_design_guides",
      "behavioral_questions",
      "behavioral_categories",
      "coding_questions",
      "system_design_questions",
    ]) {
      try {
        const c = dao.findCollectionByNameOrId(name);
        dao.deleteCollection(c);
      } catch (_) {
        /* already dropped */
      }
    }
    try {
      const users = dao.findCollectionByNameOrId("users");
      try { users.schema.removeField("bio"); } catch (_) {}
      try { users.schema.removeField("target"); } catch (_) {}
      dao.saveCollection(users);
    } catch (_) {
      /* ignore */
    }
  },
);
