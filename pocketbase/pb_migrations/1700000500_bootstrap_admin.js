/// <reference path="../pb_data/types.d.ts" />

// Bootstrap a PocketBase admin account from environment variables on
// fresh setup. Reads PB_ADMIN_EMAIL and PB_ADMIN_PASSWORD; if both are
// set and no admin with that email exists yet, creates one.
//
// Designed for compose deploys: `.env` carries the credentials, the
// container picks them up, and the first `docker compose up` creates
// the admin without anyone running CLI commands. Subsequent boots are
// no-ops (the migration is one-shot, AND the admin-exists check makes
// it safe even if someone re-applies migrations).
//
// Other admins (created manually via the UI or CLI) are left alone.

migrate(
  (db) => {
    const dao = new Dao(db);
    const email = $os.getenv("PB_ADMIN_EMAIL");
    const password = $os.getenv("PB_ADMIN_PASSWORD");
    if (!email || !password) {
      console.log(
        "bootstrap_admin: PB_ADMIN_EMAIL and PB_ADMIN_PASSWORD not both set; skipping",
      );
      return;
    }
    if (password.length < 8) {
      throw new Error(
        "bootstrap_admin: PB_ADMIN_PASSWORD must be at least 8 characters",
      );
    }
    let existing = null;
    try {
      existing = dao.findAdminByEmail(email);
    } catch (_) {
      // not found — fall through to create
    }
    if (existing) {
      console.log("bootstrap_admin: admin already exists for " + email);
      return;
    }
    const admin = new Admin();
    admin.email = email;
    admin.setPassword(password);
    dao.saveAdmin(admin);
    console.log("bootstrap_admin: created admin " + email);
  },
  (_db) => {
    // No rollback — admin accounts are persisted intentionally.
  },
);
