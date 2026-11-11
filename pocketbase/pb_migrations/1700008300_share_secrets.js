/// <reference path="../pb_data/types.d.ts" />

// Share link secrets (ROUNDS-00B-L04).
//
// Additive. It creates:
//
//   share_resolvers   the share resolver's service login: an auth
//                     collection whose one record, share-resolver,
//                     pb_hooks/share_secrets.pb.js creates at start from
//                     ROUNDS_SHARE_RESOLVER_PASSWORD. This migration leaves
//                     it empty.
//   share_throttle    the resolver's counters: one row per counter, named
//                     by a key only the runner can make (a hash, never a
//                     client address or a bearer digest), with its scope,
//                     the start of its window, and its count.
//
// Every rule on both is null, so only pb_hooks/share_secrets.js writes them
// at runtime (docs/security/server-writes.md). Neither has a JSON field, so
// nothing joins the JSON limit registry.
//
// On admission_commands it lists three operations that hooks already record
// or will: snapshot_create (ROUNDS-00A-L04's snapshot command), and
// share_create and share_rotate (this leaf's commands). Hooks save those
// rows through the DAO, which doesn't check the list, so this changes no row
// and no write; the list matches what the rows hold. It also adds a nullable
// share_snapshot_command: the key a share_create row's snapshot call runs
// under, made on its first attempt so a retry reuses it.
//
// down() drops both collections: a counter only lasts a day, and the
// share-resolver record comes back from the secret at the next start. It
// takes the three operations off the list again, drops
// share_snapshot_command, and leaves every row as it is otherwise.

const OPERATIONS = ["snapshot_create", "share_create", "share_rotate"];
const SNAPSHOT_COMMAND = "share_snapshot_command";
const COMMAND_ID = "^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$";

migrate(
  (db) => {
    const dao = new Dao(db);
    const commands = dao.findCollectionByNameOrId("admission_commands");

    const resolvers = new Collection({
      name: "share_resolvers",
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
    dao.saveCollection(resolvers);

    const throttle = new Collection({
      name: "share_throttle",
      type: "base",
      listRule: null,
      viewRule: null,
      createRule: null,
      updateRule: null,
      deleteRule: null,
      schema: [
        { name: "key", type: "text", required: true, options: { min: null, max: null, pattern: "^[0-9a-f]{64}$" } },
        {
          name: "scope",
          type: "text",
          required: true,
          options: { min: null, max: null, pattern: "^(ip_minute|pw_15m|digest_day)$" },
        },
        { name: "window_start", type: "number", required: false, options: { min: 0, max: null, noDecimal: true } },
        { name: "count", type: "number", required: false, options: { min: 0, max: null, noDecimal: true } },
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_share_throttle_key ON share_throttle (key)",
        "CREATE INDEX idx_share_throttle_window ON share_throttle (window_start)",
      ],
    });
    dao.saveCollection(throttle);

    const operation = commands.schema.getFieldByName("operation");
    const values = operation.options.values || [];
    OPERATIONS.forEach((name) => {
      if (values.indexOf(name) < 0) values.push(name);
    });
    operation.options.values = values;
    if (!commands.schema.getFieldByName(SNAPSHOT_COMMAND)) {
      commands.schema.addField(
        new SchemaField({
          name: SNAPSHOT_COMMAND,
          type: "text",
          required: false,
          options: { min: null, max: 36, pattern: COMMAND_ID },
        }),
      );
    }
    dao.saveCollection(commands);
  },

  (db) => {
    const dao = new Dao(db);
    for (const name of ["share_throttle", "share_resolvers"]) {
      try {
        dao.deleteCollection(dao.findCollectionByNameOrId(name));
      } catch (_) {
        /* already gone */
      }
    }
    const commands = dao.findCollectionByNameOrId("admission_commands");
    const operation = commands.schema.getFieldByName("operation");
    operation.options.values = (operation.options.values || []).filter((name) => OPERATIONS.indexOf(name) < 0);
    const link = commands.schema.getFieldByName(SNAPSHOT_COMMAND);
    if (link) commands.schema.removeField(link.id);
    dao.saveCollection(commands);
  },
);
