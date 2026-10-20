/// <reference path="../pb_data/types.d.ts" />

// Server-derived ownership on create and update (ROUNDS-00B-L01 stage 3).
//
// On every user-owned collection:
//   * a create must name the caller as `user`;
//   * an update may leave `user` out or resend the caller's own id, and
//     can't change it.
// resume_share_views takes no client writes at all: its create and update
// rules become superuser-only, which the public share viewer's
// view-tracking insert already uses. List, view, and delete rules are
// unchanged, and so are the `users` defaults. No data changes.
//
// Every collection is looked up before any rule changes, and PocketBase
// applies a migration in one transaction, so a missing collection fails
// the whole migration and leaves every rule as it was.
//
// down() deliberately keeps the tightened rules: account isolation is
// never rolled back. A rule that turns out too tight is repaired with a
// forward-fix migration (docs/operations.md, "Account-scope rules").
// The rule table these values come from is docs/security/account-scope.v1.json.

const OWNED = [
  "campaigns",
  "applications",
  "interview_rounds",
  "user_progress",
  "user_preferences",
  "offers",
  "code_drafts",
  "todos",
  "resumes",
  "resume_variants",
  "resume_versions",
  "resume_share_links",
  "ai_providers",
  "ai_settings",
  "ai_coding_drafts",
  "ai_coding_attempts",
  "take_home_drafts",
  "take_home_attempts",
  "question_timers",
  "experience_jobs",
  "experience_projects",
  "experience_anecdotes",
  "experience_bullets",
  "exp_job_projects",
  "exp_job_anecdotes",
  "exp_job_bullets",
  "exp_project_anecdotes",
  "exp_project_bullets",
  "exp_anecdote_bullets",
];

// Only the superuser path writes these rows.
const SERVER_ONLY = ["resume_share_views"];

const CREATE_RULE = '@request.auth.id != "" && @request.data.user = @request.auth.id';
const UPDATE_RULE =
  'user = @request.auth.id && (@request.data.user:isset = false || @request.data.user = @request.auth.id)';

migrate(
  (db) => {
    const dao = new Dao(db);

    const lookup = (name) => {
      try {
        return dao.findCollectionByNameOrId(name);
      } catch (_) {
        throw new Error(
          "account_scope_rules: collection " + name + " is missing; no rule was changed",
        );
      }
    };

    // Resolve all of them first so a missing collection changes nothing.
    const owned = OWNED.map(lookup);
    const serverOnly = SERVER_ONLY.map(lookup);

    for (const collection of owned) {
      collection.createRule = CREATE_RULE;
      collection.updateRule = UPDATE_RULE;
      dao.saveCollection(collection);
    }
    for (const collection of serverOnly) {
      collection.createRule = null;
      collection.updateRule = null;
      dao.saveCollection(collection);
    }
  },
  (_db) => {
    // Intentionally keeps the tightened rules; see the header comment.
  },
);
