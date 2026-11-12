/// <reference path="../pb_data/types.d.ts" />

// The database benchmark's fixture (ROUNDS-02-L01). Bench only: pbnative.py
// copies this file into a scratch migrations directory beside the
// repository's own migrations; the image never carries it.
//
// One fixture aggregate table plus prototypes of the platform tables
// DR-0004 places: change sets and audit (#21), the outbox, relay lease and
// cursor (#22), the projection and its checkpoint (#23), an idempotency
// table keyed like admission_commands (#1, #20), the account byte store
// (decision 10), and rows for modeled background writers. Every rule is
// null, so only the bench's hook routes write or read them.
//
// The partial unique index on bench_records is the offer chain's invariant
// mechanism: at most one active offer per opportunity, whatever the writer.

migrate(
  (db) => {
    const dao = new Dao(db);
    const text = (name, required) => ({ name, type: "text", required: !!required, options: {} });
    const num = (name, required) => ({ name, type: "number", required: !!required, options: {} });
    const json = (name, maxSize) => ({ name, type: "json", options: { maxSize: maxSize || 65536 } });
    const closed = { listRule: null, viewRule: null, createRule: null, updateRule: null, deleteRule: null };

    const collections = [
      {
        name: "bench_records",
        schema: [text("account_id", true), text("kind", true), num("version", true), text("status"), text("parent"),
          { name: "deleted", type: "bool", options: {} }, json("payload")],
        indexes: [
          "CREATE INDEX idx_bench_records_account_kind ON bench_records (account_id, kind)",
          "CREATE INDEX idx_bench_records_parent ON bench_records (parent)",
          "CREATE UNIQUE INDEX idx_bench_records_one_active_offer ON bench_records (parent) WHERE kind = 'offer' AND status = 'active'",
        ],
      },
      {
        name: "bench_change_sets",
        schema: [text("account_id", true), num("commit_position", true), num("seq", true), text("command_id", true),
          text("actor"), json("vector"), json("ops")],
        indexes: [
          "CREATE UNIQUE INDEX idx_bench_change_sets_seq ON bench_change_sets (seq)",
          "CREATE UNIQUE INDEX idx_bench_change_sets_position ON bench_change_sets (account_id, commit_position)",
          // #21: command_id, like commit_position, is unique per account.
          "CREATE UNIQUE INDEX idx_bench_change_sets_command ON bench_change_sets (account_id, command_id)",
        ],
      },
      {
        name: "bench_audit",
        schema: [text("account_id", true), text("change_set"), num("commit_position"), text("actor"), text("action"),
          text("target"), json("meta", 16384)],
        indexes: ["CREATE INDEX idx_bench_audit_position ON bench_audit (account_id, commit_position)"],
      },
      {
        name: "bench_idempotency",
        schema: [text("account_id", true), text("command_id", true), text("fingerprint"), text("state"),
          json("result", 16384), num("expires_at")],
        indexes: [
          "CREATE UNIQUE INDEX idx_bench_idempotency_key ON bench_idempotency (account_id, command_id)",
          "CREATE INDEX idx_bench_idempotency_expires ON bench_idempotency (expires_at)",
        ],
      },
      {
        name: "bench_outbox",
        schema: [text("account_id", true), num("commit_position", true), num("ordinal", true), num("relay_seq", true),
          text("event_id", true), text("aggregate_id", true), num("aggregate_seq", true), text("type"),
          json("payload", 16384), num("occurred_at")],
        indexes: [
          "CREATE UNIQUE INDEX idx_bench_outbox_relay_seq ON bench_outbox (relay_seq)",
          "CREATE UNIQUE INDEX idx_bench_outbox_event ON bench_outbox (event_id)",
          "CREATE UNIQUE INDEX idx_bench_outbox_position ON bench_outbox (account_id, commit_position, ordinal)",
        ],
      },
      {
        name: "bench_leases",
        schema: [text("name", true), text("holder"), num("fencing_token"), num("expires_at")],
        indexes: ["CREATE UNIQUE INDEX idx_bench_leases_name ON bench_leases (name)"],
      },
      {
        name: "bench_checkpoints",
        schema: [text("name", true), num("last_seq"), num("updated_at")],
        indexes: ["CREATE UNIQUE INDEX idx_bench_checkpoints_name ON bench_checkpoints (name)"],
      },
      {
        name: "bench_projection",
        schema: [text("account_id", true), text("aggregate_id", true), text("kind"), num("version"), num("aggregate_seq"),
          num("position"), num("applied_at"), json("summary", 8192)],
        indexes: [
          "CREATE UNIQUE INDEX idx_bench_projection_aggregate ON bench_projection (aggregate_id)",
          "CREATE INDEX idx_bench_projection_account ON bench_projection (account_id)",
        ],
      },
      {
        name: "bench_blobs",
        schema: [text("account_id", true), text("sha256", true), num("size"), text("privacy_class"), num("retain_until"),
          { name: "file", type: "file", options: { maxSelect: 1, maxSize: 52428800, protected: true } }],
        indexes: ["CREATE UNIQUE INDEX idx_bench_blobs_hash ON bench_blobs (account_id, sha256)"],
      },
      {
        name: "bench_bg",
        schema: [text("kind", true), text("key", true), num("count"), num("at")],
        indexes: [
          "CREATE UNIQUE INDEX idx_bench_bg_key ON bench_bg (kind, key)",
          "CREATE INDEX idx_bench_bg_at ON bench_bg (kind, at)",
        ],
      },
    ];

    for (const c of collections) {
      dao.saveCollection(new Collection(Object.assign({ name: c.name, type: "base", schema: c.schema, indexes: c.indexes }, closed)));
    }
  },
  (db) => {
    const dao = new Dao(db);
    for (const name of ["bench_bg", "bench_blobs", "bench_projection", "bench_checkpoints", "bench_leases", "bench_outbox",
      "bench_idempotency", "bench_audit", "bench_change_sets", "bench_records"]) {
      try {
        dao.deleteCollection(dao.findCollectionByNameOrId(name));
      } catch (_) {
        /* not there */
      }
    }
  },
);
