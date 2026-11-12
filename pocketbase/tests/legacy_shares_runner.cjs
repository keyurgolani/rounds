// Runs the older share links' decisions under node (ROUNDS-00B-L06 stage 1)
// for test_legacy_share_migration.py, test_legacy_share_receipt.py, and
// test_share_links.py:
//
//   node legacy_shares_runner.cjs <hooks dir> <migrations dir> < program.json
//
// A program is {"steps": [...]}, each step a call and its arguments; the
// output is {"results": [...]}. The migration file is loaded with a
// `migrate` that only keeps its two callbacks, so nothing in it runs but
// its pure decisions. Node's own SHA-256 and #4's canonical() stand in for
// the receipt's.

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const [hooksDir, migrationsDir] = process.argv.slice(2);
const program = JSON.parse(fs.readFileSync(0, "utf8"));

let callbacks = null;
globalThis.migrate = (up, down) => {
  callbacks = { up, down };
};
globalThis.__hooks = hooksDir;

const migration = require(path.join(migrationsDir, "1700008500_legacy_share_migration.js"));
const receipts = require(path.join(hooksDir, "legacy_shares.js"));
const snapshots = require(path.join(hooksDir, "legacy_snapshots.js"));
const links = require(path.join(hooksDir, "share_links.js"));

const sha256 = (text) => crypto.createHash("sha256").update(text, "utf8").digest("hex");

const results = program.steps.map((step) => {
  switch (step.call) {
    case "constants":
      return {
        manifest: migration.MANIFEST,
        predicate_version: migration.PREDICATE_VERSION,
        batch: migration.BATCH,
        outcomes: migration.OUTCOMES,
        reasons: migration.REASONS,
        dropped: migration.DROPPED.map((f) => f.name),
        dropped_index: migration.DROPPED_INDEX,
        link_payload_drops: migration.LINK_PAYLOAD_DROPS,
        view_payload_drops: migration.VIEW_PAYLOAD_DROPS,
        fields: migration.FIELDS,
        registered: callbacks !== null && typeof callbacks.up === "function" && typeof callbacks.down === "function",
        receipt: {
          schema: receipts.SCHEMA,
          manifest: receipts.MANIFEST,
          predicate_version: receipts.PREDICATE_VERSION,
          outcomes: receipts.OUTCOMES,
          reasons: receipts.REASONS,
          dropped: receipts.DROPPED,
          link_payload_drops: receipts.LINK_PAYLOAD_DROPS,
          view_payload_drops: receipts.VIEW_PAYLOAD_DROPS,
          journal_fields: receipts.JOURNAL_FIELDS,
        },
      };
    case "classify":
      return step.rows.map((row) => migration.classify(row));
    case "classifyQuarantined":
      return step.kinds.map((kind) => migration.classifyQuarantined(kind));
    case "quarantinedLinks": {
      const live = {};
      step.live.forEach((id) => {
        live[id] = true;
      });
      return migration.quarantinedLinks(step.entries, live);
    }
    case "journalRow": {
      const views = step.views.reduce((counts, day) => migration.countView(counts, day), migration.noViews());
      return migration.journalRow(step.link, step.origin, step.entry, step.decided, views);
    }
    case "day":
      return migration.DAY(step.expr);
    case "receipt":
      return receipts.receipt(step.input, snapshots.canonical, sha256);
    case "unavailableOf":
      return receipts.unavailableOf(step.report);
    case "screenUpdate":
      return step.cases.map((c) => links.screenUpdate(c.before, c.after));
    default:
      throw new Error(`unknown call ${step.call}`);
  }
});

process.stdout.write(JSON.stringify({ results }));
