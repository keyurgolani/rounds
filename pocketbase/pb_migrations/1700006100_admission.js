/// <reference path="../pb_data/types.d.ts" />

// Admission state (ROUNDS-00A-L01 stage 3, admission/v1 steps 6 and 7).
//
// Three server-only collections: every client rule is null, so only
// superusers can reach them through the API, and at runtime only the
// functions in pb_hooks/admission.js write them
// (docs/security/server-writes.md).
//
//   admission_commands  one row per (account, command_id): the request's
//                       fingerprint, state, charge, and stored result,
//                       kept for 24 hours.
//   admission_counters  hourly request and wall-second counts per bucket:
//                       each account, the whole deployment, and the shared
//                       demo tier.
//   admission_leases    one row per admitted request while it runs; live
//                       leases are the in-flight counts.
//
// Times are whole epoch seconds, and an `hour` is a UTC hour, the epoch
// seconds divided by 3600. The down step drops only these three
// collections.

migrate(
  (db) => {
    const dao = new Dao(db);
    const users = dao.findCollectionByNameOrId("users");

    const OPERATIONS = ["run", "evaluate", "run_project", "grade", "take_home_run", "take_home_submit", "pdf_render"];
    const COMMAND_ID = "^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$";
    const SHA256_HEX = "^[0-9a-f]{64}$";
    const account = (required) => ({
      name: "account",
      type: "relation",
      required,
      options: { collectionId: users.id, cascadeDelete: true, maxSelect: 1 },
    });
    const operation = {
      name: "operation",
      type: "select",
      required: true,
      options: { maxSelect: 1, values: OPERATIONS },
    };
    const seconds = (name, required) => ({
      name,
      type: "number",
      required,
      options: { min: 0, noDecimal: true },
    });

    const commands = new Collection({
      name: "admission_commands",
      type: "base",
      listRule: null,
      viewRule: null,
      createRule: null,
      updateRule: null,
      deleteRule: null,
      schema: [
        account(true),
        { name: "command_id", type: "text", required: true, options: { max: 36, pattern: COMMAND_ID } },
        operation,
        { name: "fingerprint", type: "text", required: true, options: { pattern: SHA256_HEX } },
        {
          name: "state",
          type: "select",
          required: true,
          options: { maxSelect: 1, values: ["in_flight", "completed", "retryable", "failed_infrastructure"] },
        },
        seconds("wall_seconds", false),
        // The completed response a replay returns. Larger results and
        // rendered PDFs aren't kept.
        { name: "result", type: "json", options: { maxSize: 1024 * 1024 } },
        seconds("expires_at", true),
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_admission_commands_key ON admission_commands (account, command_id)",
        "CREATE INDEX idx_admission_commands_expires ON admission_commands (expires_at)",
        "CREATE INDEX idx_admission_commands_state ON admission_commands (state)",
      ],
    });
    dao.saveCollection(commands);

    const counters = new Collection({
      name: "admission_counters",
      type: "base",
      listRule: null,
      viewRule: null,
      createRule: null,
      updateRule: null,
      deleteRule: null,
      schema: [
        {
          name: "bucket",
          type: "select",
          required: true,
          options: { maxSelect: 1, values: ["account", "deployment", "demo"] },
        },
        // Set for an account bucket, empty for the deployment and demo ones.
        account(false),
        seconds("hour", true),
        seconds("requests", false),
        seconds("wall_seconds", false),
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_admission_counters_bucket ON admission_counters (bucket, account, hour)",
        "CREATE INDEX idx_admission_counters_hour ON admission_counters (hour)",
      ],
    });
    dao.saveCollection(counters);

    const leases = new Collection({
      name: "admission_leases",
      type: "base",
      listRule: null,
      viewRule: null,
      createRule: null,
      updateRule: null,
      deleteRule: null,
      schema: [
        account(true),
        // Empty when the request has no command row of its own.
        {
          name: "command",
          type: "relation",
          options: { collectionId: commands.id, cascadeDelete: true, maxSelect: 1 },
        },
        operation,
        { name: "demo", type: "bool" },
        seconds("hour", true),
        seconds("wall_seconds", false),
        // SHA-256 of the lease token only the admitting runner holds.
        { name: "token_hash", type: "text", required: true, options: { pattern: SHA256_HEX } },
        seconds("expires_at", true),
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_admission_leases_token ON admission_leases (token_hash)",
        "CREATE INDEX idx_admission_leases_expires ON admission_leases (expires_at)",
        "CREATE INDEX idx_admission_leases_account ON admission_leases (account, expires_at)",
        "CREATE INDEX idx_admission_leases_command ON admission_leases (command)",
      ],
    });
    dao.saveCollection(leases);
  },

  (db) => {
    const dao = new Dao(db);
    // Leases point at commands, so they go first.
    for (const name of ["admission_leases", "admission_counters", "admission_commands"]) {
      try {
        dao.deleteCollection(dao.findCollectionByNameOrId(name));
      } catch (_) {
        /* already dropped */
      }
    }
  },
);
