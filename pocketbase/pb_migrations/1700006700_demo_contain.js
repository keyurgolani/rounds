/// <reference path="../pb_data/types.d.ts" />

// Demo containment (ROUNDS-00B-L07 stage 1, manifest demo-contain-v1).
//
// Deletes what a demo account (users.is_demo) owns in the three
// collections a demo account may no longer hold: its resume share links,
// whose views go with them (resume_share_views cascades from its link),
// its AI settings, and then its AI providers with their stored keys.
// pb_hooks/demo.pb.js refuses new ones from now on.
//
// It writes no row a standard account owns. Every demo account's settings
// go before any provider, so no demo row still points at one. A demo
// provider that another account's AI settings point at keeps its row, with
// its stored key cleared, so deleting it doesn't rewrite that account's
// settings: 1700007000_relation_endpoint_authz.js, which runs after this on
// an upgrade, journals and clears that reference. Nothing else a demo
// account owns changes; stage 3 handles the rest.
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
    const owned = (name, account) =>
      dao.findRecordsByFilter(name, "user = {:user}", "", 0, 0, { user: account.id });
    const accounts = dao.findRecordsByFilter("users", "is_demo = true");
    // Share links and settings first, for every demo account.
    for (const name of ["resume_share_links", "ai_settings"]) {
      for (const account of accounts) {
        for (const row of owned(name, account)) dao.deleteRecord(row);
      }
    }
    for (const account of accounts) {
      for (const row of owned("ai_providers", account)) {
        const referenced = dao.findRecordsByFilter(
          "ai_settings", "text_provider = {:provider} || vision_provider = {:provider}", "", 1, 0,
          { provider: row.id },
        );
        if (referenced.length === 0) {
          dao.deleteRecord(row);
        } else {
          row.set("encrypted_key", "");
          row.set("key_iv", "");
          dao.saveRecord(row);
        }
      }
    }
  },
  (_db) => {
    // Forward-only; see above.
  },
);
