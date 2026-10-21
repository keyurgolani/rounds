/// <reference path="../pb_data/types.d.ts" />

// The execution job store (ROUNDS-00A-L03 PR 1).
//
// Additive. It creates:
//
//   execution_service     the Service writer: an auth collection whose one
//                         record, execution-worker, pb_hooks/execution.pb.js
//                         creates at start from ROUNDS_EXECUTION_SECRET.
//                         This migration leaves it empty.
//   execution_jobs        one row per (account, command_id): the kind, the
//                         definition reference, the input digests, the
//                         candidate's input, and the job's state.
//   execution_attempts    one row per (job, attempt_number), at most three:
//                         the lease, the fencing token's hash, the times, and
//                         the operator view of its result.
//   execution_envelopes   one per attempt: the rounds.execution-envelope/v1
//                         result the account sees, and the graded row it was
//                         written for.
//
// Client create, update, and delete rules are null, so only the functions
// in pb_hooks/execution.js write these at runtime
// (docs/security/server-writes.md). Jobs and attempts are read by the
// execution_service record only. An envelope is read by its own account
// (D9): it has a `user` field like every collection an account reads
// (docs/security/account-scope.v1.json), and it carries the user view only,
// outcome classes and the server's totals for a run with hidden material.
// The operator view stays on the attempt.
//
// It also adds a nullable `envelope` relation to ai_coding_attempts and
// take_home_attempts, raises take_home_attempts.files to 8 MiB for #1's
// 5 MiB file ceiling, and adds a nullable `job` relation to
// admission_commands, which enqueue sets. An envelope names its graded row
// back (graded_collection, graded_row), so a row's `envelope` counts only
// when the envelope points at that row for the same account, and
// pb_hooks/execution.pb.js refuses a client write that sets `envelope`.
//
// Times are whole epoch seconds on PocketBase's clock. No existing row is
// rewritten. The down step drops only what this adds.

migrate(
  (db) => {
    const dao = new Dao(db);
    const users = dao.findCollectionByNameOrId("users");
    const admissionCommands = dao.findCollectionByNameOrId("admission_commands");
    const aiAttempts = dao.findCollectionByNameOrId("ai_coding_attempts");
    const takeHomeAttempts = dao.findCollectionByNameOrId("take_home_attempts");

    const SERVICE_ONLY = '@request.auth.collectionName = "execution_service"';
    const OWNER_ONLY = "user = @request.auth.id";
    const KINDS = ["run", "evaluate", "run_project", "take_home_run", "grade", "take_home_submit"];
    const STATES = ["queued", "leased", "started", "completed", "timed-out", "denied", "canceled", "failed"];
    const ATTEMPT_STATES = ["leased", "started", "completed", "timed-out", "denied", "canceled", "failed"];
    const TERMINAL_STATES = ["completed", "timed-out", "denied", "canceled", "failed"];
    const OUTCOME_CLASSES = [
      "passed", "candidate-failure", "resource-limit", "definition-invalid", "policy-violation", "canceled",
      "worker-lost", "infrastructure-degraded",
    ];
    const CLEANUP = ["pending", "confirmed", "unconfirmed"];
    const COMMAND_ID = "^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$";
    const SHA256_HEX = "^[0-9a-f]{64}$";
    const WORKER_ID = "^[a-z0-9][a-z0-9-]{0,62}$";
    const MIB = 1024 * 1024;

    const account = {
      name: "account",
      type: "relation",
      required: true,
      options: { collectionId: users.id, cascadeDelete: true, maxSelect: 1 },
    };
    const select = (name, values, required) => ({ name, type: "select", required, options: { maxSelect: 1, values } });
    const seconds = (name, required) => ({ name, type: "number", required, options: { min: 0, noDecimal: true } });
    const sha256 = (name, required) => ({ name, type: "text", required, options: { pattern: SHA256_HEX } });

    const service = new Collection({
      name: "execution_service",
      type: "auth",
      listRule: null,
      viewRule: null,
      createRule: null,
      updateRule: null,
      deleteRule: null,
      schema: [],
      options: {
        allowEmailAuth: false,
        allowOAuth2Auth: false,
        allowUsernameAuth: true,
        exceptEmailDomains: null,
        manageRule: null,
        minPasswordLength: 32,
        onlyEmailDomains: null,
        onlyVerified: false,
        requireEmail: false,
      },
    });
    dao.saveCollection(service);

    const jobs = new Collection({
      name: "execution_jobs",
      type: "base",
      listRule: SERVICE_ONLY,
      viewRule: SERVICE_ONLY,
      createRule: null,
      updateRule: null,
      deleteRule: null,
      schema: [
        account,
        { name: "command_id", type: "text", required: true, options: { max: 36, pattern: COMMAND_ID } },
        select("kind", KINDS, true),
        select("purpose", ["scratch", "grading"], true),
        // {track, slug, variant, version}, as #2's request names it.
        { name: "definition", type: "json", required: true, options: { maxSize: 1024 } },
        // The admission fingerprint the job was enqueued under.
        sha256("fingerprint", true),
        sha256("source_checksum", true),
        sha256("input_digest", true),
        // The candidate's code or files and typed inputs; it goes with the job.
        { name: "input", type: "json", required: true, options: { maxSize: 8 * MIB } },
        select("state", STATES, true),
        select("outcome_class", OUTCOME_CLASSES, false),
        // Attempts whose candidate tree started; a retry needs fewer than 3.
        seconds("attempts_started", false),
        seconds("attempts", false),
        { name: "cancel_requested", type: "bool" },
        select("cleanup", CLEANUP, false),
        seconds("queued_at", true),
        seconds("finished_at", false),
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_execution_jobs_command ON execution_jobs (account, command_id)",
        "CREATE INDEX idx_execution_jobs_queue ON execution_jobs (state, queued_at)",
        "CREATE INDEX idx_execution_jobs_active ON execution_jobs (account, state)",
      ],
    });
    dao.saveCollection(jobs);

    const attempts = new Collection({
      name: "execution_attempts",
      type: "base",
      listRule: SERVICE_ONLY,
      viewRule: SERVICE_ONLY,
      createRule: null,
      updateRule: null,
      deleteRule: null,
      schema: [
        {
          name: "job",
          type: "relation",
          required: true,
          options: { collectionId: jobs.id, cascadeDelete: true, maxSelect: 1 },
        },
        account,
        { name: "attempt_number", type: "number", required: true, options: { min: 1, max: 3, noDecimal: true } },
        // SHA-256 of the fencing token the claiming replica made and holds.
        sha256("token_hash", true),
        { name: "worker", type: "text", required: true, options: { max: 63, pattern: WORKER_ID } },
        select("state", ATTEMPT_STATES, true),
        select("outcome_class", OUTCOME_CLASSES, false),
        // The wall budget the started run declared, and when it runs out;
        // reap ends the attempt 30 s past that.
        seconds("budget_s", false),
        seconds("deadline_at", false),
        seconds("leased_at", true),
        seconds("lease_expires_at", true),
        seconds("started_at", false),
        seconds("heartbeat_at", false),
        seconds("finished_at", false),
        // Writes refused because this attempt's token was superseded.
        seconds("rejected_writes", false),
        select("cleanup", CLEANUP, false),
        // What only operators see of the result: digests, measurements,
        // the executor, the build. Set when the attempt ends.
        { name: "operator_view", type: "json", options: { maxSize: 64 * 1024 } },
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_execution_attempts_number ON execution_attempts (job, attempt_number)",
        "CREATE UNIQUE INDEX idx_execution_attempts_token ON execution_attempts (token_hash)",
        "CREATE INDEX idx_execution_attempts_lease ON execution_attempts (state, lease_expires_at)",
        "CREATE INDEX idx_execution_attempts_deadline ON execution_attempts (state, deadline_at)",
      ],
    });
    dao.saveCollection(attempts);

    const envelopes = new Collection({
      name: "execution_envelopes",
      type: "base",
      listRule: OWNER_ONLY,
      viewRule: OWNER_ONLY,
      createRule: null,
      updateRule: null,
      deleteRule: null,
      schema: [
        {
          name: "user",
          type: "relation",
          required: true,
          options: { collectionId: users.id, cascadeDelete: true, maxSelect: 1 },
        },
        {
          name: "job",
          type: "relation",
          required: true,
          options: { collectionId: jobs.id, cascadeDelete: true, maxSelect: 1 },
        },
        {
          name: "attempt",
          type: "relation",
          required: true,
          options: { collectionId: attempts.id, cascadeDelete: true, maxSelect: 1 },
        },
        { name: "version", type: "text", required: true, options: { max: 64 } },
        select("state", TERMINAL_STATES, true),
        select("outcome_class", OUTCOME_CLASSES, true),
        { name: "authoritative", type: "bool" },
        // What the account sees: no output for a run with hidden material.
        { name: "user_view", type: "json", required: true, options: { maxSize: MIB } },
        // The graded row this envelope was written for: the back-pointer
        // a row's `envelope` has to match.
        select("graded_collection", ["ai_coding_attempts", "take_home_attempts"], false),
        { name: "graded_row", type: "text", options: { max: 15 } },
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_execution_envelopes_attempt ON execution_envelopes (attempt)",
        "CREATE INDEX idx_execution_envelopes_job ON execution_envelopes (job)",
        "CREATE INDEX idx_execution_envelopes_user ON execution_envelopes (user)",
      ],
    });
    dao.saveCollection(envelopes);

    const envelopeLink = () =>
      new SchemaField({
        name: "envelope",
        type: "relation",
        options: { collectionId: envelopes.id, cascadeDelete: false, maxSelect: 1 },
      });
    aiAttempts.schema.addField(envelopeLink());
    dao.saveCollection(aiAttempts);
    takeHomeAttempts.schema.addField(envelopeLink());
    // On a database built from scratch PocketBase's own JSON reset sorts
    // after this migration, and 1702134273_json_limits.js sets this limit
    // and the ones above back after it (D10).
    takeHomeAttempts.schema.getFieldByName("files").options.maxSize = 8 * MIB;
    dao.saveCollection(takeHomeAttempts);

    admissionCommands.schema.addField(
      new SchemaField({
        name: "job",
        type: "relation",
        options: { collectionId: jobs.id, cascadeDelete: false, maxSelect: 1 },
      }),
    );
    dao.saveCollection(admissionCommands);
  },

  (db) => {
    const dao = new Dao(db);
    // The links into the job store go first, then the collections, which
    // point at each other in this order.
    for (const [name, field] of [
      ["admission_commands", "job"],
      ["ai_coding_attempts", "envelope"],
      ["take_home_attempts", "envelope"],
    ]) {
      const collection = dao.findCollectionByNameOrId(name);
      const existing = collection.schema.getFieldByName(field);
      if (existing) collection.schema.removeField(existing.id);
      dao.saveCollection(collection);
    }
    // Back to 2,000,000 bytes, PocketBase's JSON default. The field holds
    // that before this migration rather than the 2 MiB that
    // 1700001300_take_home.js declares, because PocketBase's own JSON-size
    // migration runs after that one and overwrites it.
    const takeHome = dao.findCollectionByNameOrId("take_home_attempts");
    takeHome.schema.getFieldByName("files").options.maxSize = 2000000;
    dao.saveCollection(takeHome);
    for (const name of ["execution_envelopes", "execution_attempts", "execution_jobs", "execution_service"]) {
      try {
        dao.deleteCollection(dao.findCollectionByNameOrId(name));
      } catch (_) {
        /* already dropped */
      }
    }
  },
);
