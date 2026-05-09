/// <reference path="../pb_data/types.d.ts" />

// Public read for `/r/:token` viewers.
//
// Earlier migrations (1700000700, 1700000900) left a "Phase 7 will
// refactor these rules so anonymous reads work for /r/:token" comment.
// This is that refactor.
//
// Rule shape:
//   user = @request.auth.id || token = @request.query.token
//
// What this does:
//   * Owners (the authed creator) keep full read/list access on their
//     own links — the existing settings UI + share-list endpoints are
//     unaffected.
//   * An anonymous viewer can resolve a single link by hitting PB with
//     `?token=<the-token>` in the query string. Without that param the
//     rule yields no rows, so blanket enumeration is still impossible.
//
// Why we still keep the FastAPI admin-proxy in `backend/routers/share.py`:
//   * View tracking writes a `resume_share_views` row with an IP hash
//     and user-agent. That has to be server-side anyway.
//   * The viewer payload joins resume/variant template + design + data
//     and intentionally exposes only that subset; relaxing the rule on
//     `resumes` / `resume_variants` directly would leak more fields than
//     the current `view_resume()` response.
//
// So the new rule is defense-in-depth + documentation-of-intent: if a
// future caller bypasses FastAPI and queries PB directly with the
// token, they'll succeed (matching the public-by-token contract); the
// current architecture is unchanged.
//
// `createRule`, `updateRule`, and `deleteRule` stay owner-only — the
// only thing that loosens is read access.

migrate(
  (db) => {
    const dao = new Dao(db);
    const links = dao.findCollectionByNameOrId("resume_share_links");
    links.viewRule = "user = @request.auth.id || token = @request.query.token";
    links.listRule = "user = @request.auth.id || token = @request.query.token";
    dao.saveCollection(links);
  },
  (db) => {
    const dao = new Dao(db);
    const links = dao.findCollectionByNameOrId("resume_share_links");
    links.viewRule = "user = @request.auth.id";
    links.listRule = "user = @request.auth.id";
    dao.saveCollection(links);
  },
);
