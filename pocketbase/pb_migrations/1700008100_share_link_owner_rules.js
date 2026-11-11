/// <reference path="../pb_data/types.d.ts" />

// A share link answers only its owner (ROUNDS-00B-L03 stage 1).
//
// resume_share_links:
//   * list and view rules become `user = @request.auth.id`, so a link row
//     reads for its owner and nobody else, signed in or not;
//   * the update rule becomes null, so no client can change a link's token or
//     its target once it exists (the owner deletes and creates instead).
// Create and delete rules are unchanged (1700006000_account_scope_rules.js),
// and so is every other collection. No data changes.
//
// Public reads go through the runner (backend/routers/share.py), which
// answers only the resume's projection.
//
// down() deliberately keeps these rules: account isolation is never rolled
// back, and no down step loosens them. A rule that turns out
// too tight is repaired with a forward-fix migration (docs/operations.md,
// "Account-scope rules"). The rule table these values come from is
// docs/security/account-scope.v1.json.

const OWNER_READ = "user = @request.auth.id";

migrate(
  (db) => {
    const dao = new Dao(db);
    let links;
    try {
      links = dao.findCollectionByNameOrId("resume_share_links");
    } catch (_) {
      throw new Error("share_link_owner_rules: collection resume_share_links is missing; no rule was changed");
    }
    links.listRule = OWNER_READ;
    links.viewRule = OWNER_READ;
    links.updateRule = null;
    dao.saveCollection(links);
  },
  (_db) => {
    // Intentionally keeps the owner-only rules; see the header comment.
  },
);
