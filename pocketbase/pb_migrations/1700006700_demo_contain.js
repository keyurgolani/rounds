/// <reference path="../pb_data/types.d.ts" />

// Demo containment (ROUNDS-00B-L07 stage 1, manifest demo-contain-v1).
//
// Deletes what a demo account (users.is_demo) owns in the three
// collections a demo account may no longer hold: its resume share links,
// whose views go with them (resume_share_views cascades from its link),
// its AI settings, and then its AI providers with their stored keys.
// pb_hooks/demo.pb.js refuses new ones from now on. It touches nothing a
// standard account owns, and nothing else a demo account owns; stage 3
// handles the rest.
//
// The spec allows these drops only with the owner's approval, so the
// lint entry in scripts/migration-lint-allowlist.json is pinned to this
// file's hash and waits on that review, and
// pocketbase/migration-manifests/demo-contain-v1.json records each
// disposition. Forward-only: what it deletes can't come back, so the down
// step changes nothing.

migrate(
  (db) => {
    const dao = new Dao(db);
    // Settings point at providers, so they go first.
    const CONTAINED = ["resume_share_links", "ai_settings", "ai_providers"];
    for (const account of dao.findRecordsByFilter("users", "is_demo = true")) {
      for (const name of CONTAINED) {
        for (const row of dao.findRecordsByFilter(name, "user = {:user}", "", 0, 0, { user: account.id })) {
          dao.deleteRecord(row);
        }
      }
    }
  },
  (_db) => {
    // Forward-only; see above.
  },
);
