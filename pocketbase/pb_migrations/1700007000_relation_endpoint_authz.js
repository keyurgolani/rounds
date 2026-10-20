/// <reference path="../pb_data/types.d.ts" />

// Authorize every typed relation and quarantine cross-owner links
// (ROUNDS-00B-L02).
//
// Two forward-only changes, applied in one transaction:
//
//   1. A BEFORE INSERT / BEFORE UPDATE trigger on every relation field in
//      relation_endpoints.v1.json, plus a BEFORE UPDATE OF user trigger on
//      each target, enforces target.user == row.user inside the write's own
//      SQLite transaction. This is the atomic backstop for the create-vs-delete
//      race the request-time hooks cannot see; the hooks still shape the
//      uniform client response. The owner-scoped collection rules from
//      1700006000 stay exactly as they are: this migration adds endpoint
//      authorization, it never relaxes or rewrites a rule.
//   2. Existing cross-owner (and missing-target) references are quarantined
//      before the predicate starts rejecting them: a reference on an optional
//      field is cleared and journalled; a row whose required relation points
//      at another account (or a missing record) is moved into
//      relation_quarantine and deleted, which cascades or null-repairs its own
//      dependents exactly as a normal delete would. One pseudonymized report
//      row is written to relation_quarantine_reports, reusing the
//      scan_cross_owner.py report shape.
//
// Dry run: with ROUNDS_RELATION_QUARANTINE=dry-run the migration writes the
// report to ROUNDS_RELATION_QUARANTINE_REPORT (which must be set, outside
// pb_data) and then throws, so PocketBase rolls the transaction back and exits
// without serving. Nothing in the database changes. Operators run this against
// a copy of each deployment before the real upgrade (docs/operations.md).
//
// down() keeps every trigger: account isolation is never relaxed. A predicate
// that proves too tight is repaired with a forward-fix migration. The field
// list below is checked against relation_endpoints.v1.json by the contract
// test so the two never drift.

const FIELDS = [
  { c: "ai_coding_attempts",    f: "campaign",        t: "campaigns",               required: false,  cascade: false },
  { c: "ai_coding_drafts",      f: "campaign",        t: "campaigns",               required: false,  cascade: false },
  { c: "ai_settings",           f: "text_provider",   t: "ai_providers",            required: false,  cascade: false },
  { c: "ai_settings",           f: "vision_provider", t: "ai_providers",            required: false,  cascade: false },
  { c: "applications",          f: "campaign",        t: "campaigns",               required: false,  cascade: false },
  { c: "code_drafts",           f: "campaign",        t: "campaigns",               required: true,   cascade: true },
  { c: "exp_anecdote_bullets",  f: "child",           t: "experience_bullets",      required: true,   cascade: true },
  { c: "exp_anecdote_bullets",  f: "parent",          t: "experience_anecdotes",    required: true,   cascade: true },
  { c: "exp_job_anecdotes",     f: "child",           t: "experience_anecdotes",    required: true,   cascade: true },
  { c: "exp_job_anecdotes",     f: "parent",          t: "experience_jobs",         required: true,   cascade: true },
  { c: "exp_job_bullets",       f: "child",           t: "experience_bullets",      required: true,   cascade: true },
  { c: "exp_job_bullets",       f: "parent",          t: "experience_jobs",         required: true,   cascade: true },
  { c: "exp_job_projects",      f: "child",           t: "experience_projects",     required: true,   cascade: true },
  { c: "exp_job_projects",      f: "parent",          t: "experience_jobs",         required: true,   cascade: true },
  { c: "exp_project_anecdotes", f: "child",           t: "experience_anecdotes",    required: true,   cascade: true },
  { c: "exp_project_anecdotes", f: "parent",          t: "experience_projects",     required: true,   cascade: true },
  { c: "exp_project_bullets",   f: "child",           t: "experience_bullets",      required: true,   cascade: true },
  { c: "exp_project_bullets",   f: "parent",          t: "experience_projects",     required: true,   cascade: true },
  { c: "interview_rounds",      f: "application",     t: "applications",            required: true,   cascade: true },
  { c: "interview_rounds",      f: "campaign",        t: "campaigns",               required: false,  cascade: false },
  { c: "offers",                f: "application",     t: "applications",            required: true,   cascade: true },
  { c: "offers",                f: "previous_offer",  t: "offers",                  required: false,  cascade: false },
  { c: "resume_share_links",    f: "resume",          t: "resumes",                 required: false,  cascade: true },
  { c: "resume_share_links",    f: "variant",         t: "resume_variants",         required: false,  cascade: true },
  { c: "resume_share_views",    f: "link",            t: "resume_share_links",      required: true,   cascade: true },
  { c: "resume_variants",       f: "application",     t: "applications",            required: false,  cascade: false },
  { c: "resume_variants",       f: "resume",          t: "resumes",                 required: true,   cascade: true },
  { c: "resume_versions",       f: "resume",          t: "resumes",                 required: false,  cascade: true },
  { c: "resume_versions",       f: "variant",         t: "resume_variants",         required: false,  cascade: true },
  { c: "take_home_attempts",    f: "campaign",        t: "campaigns",               required: false,  cascade: false },
  { c: "take_home_drafts",      f: "campaign",        t: "campaigns",               required: false,  cascade: false },
  { c: "todos",                 f: "campaign",        t: "campaigns",               required: true,   cascade: true },
  { c: "user_preferences",      f: "current_campaign", t: "campaigns",              required: false,  cascade: false },
  { c: "user_progress",         f: "campaign",        t: "campaigns",               required: false,  cascade: false },
];

const OWNER = "user";
const REPORT_KIND = "rounds.relation-quarantine";
const REPORT_VERSION = "v1";
const RETENTION_DAYS = 14;

migrate(
  (db) => {
    const dao = new Dao(db);
    const q = (sql) => db.newQuery(sql).execute();

    const dryRun = ($os.getenv("ROUNDS_RELATION_QUARANTINE") || "").trim().toLowerCase() === "dry-run";

    // --- 1. Atomic triggers for every relation field. -----------------------
    for (let i = 0; i < FIELDS.length; i++) {
      const r = FIELDS[i];
      const base = "rel_authz_" + r.c + "_" + r.f;
      const mismatch =
        'NEW."' + r.f + '" IS NOT NULL AND NEW."' + r.f + "\" != '' AND NOT EXISTS " +
        '(SELECT 1 FROM "' + r.t + '" tgt WHERE tgt."id" = NEW."' + r.f + '" AND tgt."' + OWNER + '" = NEW."' + OWNER + '")';
      q('DROP TRIGGER IF EXISTS "' + base + '_ins"');
      q('DROP TRIGGER IF EXISTS "' + base + '_upd"');
      q('DROP TRIGGER IF EXISTS "' + base + '_tgt"');
      q(
        'CREATE TRIGGER "' + base + '_ins" BEFORE INSERT ON "' + r.c + '" FOR EACH ROW WHEN ' +
        mismatch + " BEGIN SELECT RAISE(ABORT, 'relation endpoint denied'); END",
      );
      q(
        'CREATE TRIGGER "' + base + '_upd" BEFORE UPDATE OF "' + r.f + '", "' + OWNER + '" ON "' + r.c +
        '" FOR EACH ROW WHEN ' + mismatch + " BEGIN SELECT RAISE(ABORT, 'relation endpoint denied'); END",
      );
      q(
        'CREATE TRIGGER "' + base + '_tgt" BEFORE UPDATE OF "' + OWNER + '" ON "' + r.t +
        '" FOR EACH ROW WHEN NEW."' + OWNER + '" != OLD."' + OWNER + '" AND EXISTS ' +
        '(SELECT 1 FROM "' + r.c + '" src WHERE src."' + r.f + '" = OLD."id" AND src."' + OWNER + '" != NEW."' + OWNER + '") ' +
        "BEGIN SELECT RAISE(ABORT, 'relation endpoint denied'); END",
      );
    }

    // --- 2a. Quarantine collections (superuser-only). -----------------------
    const ensureCollection = (name, schema) => {
      try {
        return dao.findCollectionByNameOrId(name);
      } catch (_) {
        const col = new Collection({
          name: name,
          type: "base",
          listRule: null,
          viewRule: null,
          createRule: null,
          updateRule: null,
          deleteRule: null,
          schema: schema,
        });
        dao.saveCollection(col);
        return col;
      }
    };
    ensureCollection("relation_quarantine", [
      { name: "source_collection", type: "text", required: true },
      { name: "source_id", type: "text", required: true },
      { name: "owner", type: "text", required: false },
      { name: "field", type: "text", required: true },
      { name: "target_collection", type: "text", required: false },
      { name: "target_id", type: "text", required: false },
      { name: "kind", type: "text", required: true },
      { name: "payload", type: "json", required: false },
      { name: "quarantined_at", type: "text", required: false },
    ]);
    const reportsCol = ensureCollection("relation_quarantine_reports", [
      { name: "report_kind", type: "text", required: true },
      { name: "report_version", type: "text", required: true },
      { name: "generated_at", type: "text", required: true },
      { name: "expires_at", type: "text", required: false },
      { name: "checksum", type: "text", required: false },
      { name: "dry_run", type: "bool", required: false },
      { name: "summary", type: "json", required: false },
      { name: "relations", type: "json", required: false },
      { name: "findings", type: "json", required: false },
    ]);
    const quarantineCol = dao.findCollectionByNameOrId("relation_quarantine");

    // --- 2b. Find existing cross-owner / missing-target references. ----------
    const refsOf = (value) => {
      if (value === null || value === undefined) return [];
      const text = ("" + value).trim();
      if (text === "") return [];
      if (text.charAt(0) === "[") {
        try {
          const arr = JSON.parse(text);
          if (Array.isArray(arr)) return arr.filter((x) => typeof x === "string" && x !== "");
        } catch (_) {}
        return [];
      }
      return [text];
    };

    const ownerMaps = {}; // target -> { id: ownerId }
    const ownerMapOf = (target) => {
      if (!ownerMaps[target]) {
        const rows = arrayOf(new DynamicModel({ id: "", owner: "" }));
        db.newQuery('SELECT "id" AS id, "' + OWNER + '" AS owner FROM "' + target + '"').all(rows);
        const map = {};
        for (let i = 0; i < rows.length; i++) map[rows[i].id] = rows[i].owner || "";
        ownerMaps[target] = map;
      }
      return ownerMaps[target];
    };

    const findings = []; // { kind, c, f, record_id, t, target_id, owner, target_owner, required }
    const perField = [];
    for (let i = 0; i < FIELDS.length; i++) {
      const r = FIELDS[i];
      const owners = ownerMapOf(r.t);
      const rows = arrayOf(new DynamicModel({ id: "", owner: "", val: "" }));
      db.newQuery(
        'SELECT "id" AS id, "' + OWNER + '" AS owner, "' + r.f + '" AS val FROM "' + r.c + '" ORDER BY "id"',
      ).all(rows);
      let references = 0;
      let crossOwner = 0;
      let missing = 0;
      for (let j = 0; j < rows.length; j++) {
        const refs = refsOf(rows[j].val);
        for (let k = 0; k < refs.length; k++) {
          references++;
          const ref = refs[k];
          const rowOwner = rows[j].owner || "";
          let kind = null;
          let targetOwner = null;
          if (!Object.prototype.hasOwnProperty.call(owners, ref)) {
            kind = "missing_target";
            missing++;
          } else if (owners[ref] !== rowOwner) {
            kind = "cross_owner";
            targetOwner = owners[ref];
            crossOwner++;
          } else {
            continue;
          }
          findings.push({
            kind: kind,
            c: r.c,
            f: r.f,
            record_id: rows[j].id,
            t: r.t,
            target_id: ref,
            owner: rowOwner,
            target_owner: targetOwner,
            target_is_users: false,
            required: r.required,
          });
        }
      }
      perField.push({
        collection: r.c,
        field: r.f,
        target_collection: r.t,
        rows: rows.length,
        references: references,
        cross_owner: crossOwner,
        missing_target: missing,
      });
    }

    findings.sort((a, b) => {
      const ka = a.c + "|" + a.f + "|" + a.record_id + "|" + a.target_id;
      const kb = b.c + "|" + b.f + "|" + b.record_id + "|" + b.target_id;
      return ka < kb ? -1 : ka > kb ? 1 : 0;
    });

    // --- 2c. Pseudonymize accounts for the report (never store account ids). -
    const labels = {};
    const label = (account) => {
      if (account === null || account === undefined) return null;
      if (!Object.prototype.hasOwnProperty.call(labels, account)) {
        const n = Object.keys(labels).length + 1;
        labels[account] = "acct-" + (n < 10 ? "0" + n : "" + n);
      }
      return labels[account];
    };
    const publicFindings = findings.map((g) => ({
      kind: g.kind,
      collection: g.c,
      field: g.f,
      record_id: g.record_id,
      target_collection: g.t,
      target_id: g.target_id,
      owner: label(g.owner),
      target_owner: label(g.target_owner),
    }));

    const now = new Date();
    const iso = (d) => d.toISOString().replace(/\.\d{3}Z$/, "Z");
    const sourceCollections = {};
    for (let i = 0; i < FIELDS.length; i++) sourceCollections[FIELDS[i].c] = true;
    const summary = {
      owned_collections: Object.keys(sourceCollections).length,
      relations_checked: FIELDS.length,
      rows_scanned: perField.reduce((s, r) => s + r.rows, 0),
      references_checked: perField.reduce((s, r) => s + r.references, 0),
      cross_owner: publicFindings.filter((f) => f.kind === "cross_owner").length,
      missing_target: publicFindings.filter((f) => f.kind === "missing_target").length,
    };
    const canonicalBody = JSON.stringify({
      version: REPORT_VERSION,
      relations: perField,
      findings: publicFindings,
    });
    const report = {
      report_kind: REPORT_KIND,
      report_version: REPORT_VERSION,
      generated_at: iso(now),
      expires_at: iso(new Date(now.getTime() + RETENTION_DAYS * 86400000)),
      checksum: "sha256:" + $security.sha256(canonicalBody),
      dry_run: dryRun,
      summary: summary,
      relations: perField,
      findings: publicFindings,
    };

    // --- 2d. Dry run: write the report file and abort before any change. -----
    if (dryRun) {
      const out = ($os.getenv("ROUNDS_RELATION_QUARANTINE_REPORT") || "").trim();
      if (!out) {
        throw new Error(
          "relation_endpoint_authz: ROUNDS_RELATION_QUARANTINE=dry-run needs ROUNDS_RELATION_QUARANTINE_REPORT set to a path outside pb_data",
        );
      }
      if (out.indexOf("pb_data") >= 0) {
        throw new Error(
          "relation_endpoint_authz: refusing to write the dry-run report inside pb_data (" + out + ")",
        );
      }
      $os.writeFile(out, JSON.stringify(report, null, 2) + "\n", 0o600);
      console.log(
        JSON.stringify({
          v: "obs/v1",
          event: "relation_quarantine_dry_run",
          service: "pocketbase",
          report: out,
          cross_owner: summary.cross_owner,
          missing_target: summary.missing_target,
        }),
      );
      throw new Error(
        "relation_endpoint_authz: dry run complete; report written to " + out +
          "; aborting so nothing changes",
      );
    }

    // --- 2e. Apply: move required rows (cascading), clear optional refs. -----
    const moved = {}; // "collection|id" -> true
    const captureRow = (collection, id) => {
      let rec;
      try {
        rec = dao.findRecordById(collection, id);
      } catch (_) {
        return null;
      }
      return rec;
    };
    const payloadOf = (rec) => {
      const col = rec.collection();
      const schema = col.schema.fields();
      const out = { id: rec.id };
      for (let i = 0; i < schema.length; i++) {
        const name = schema[i].name;
        out[name] = rec.get(name);
      }
      return out;
    };

    // Moves first so later clears skip rows a cascade already removed.
    for (let i = 0; i < findings.length; i++) {
      const g = findings[i];
      if (!g.required) continue;
      const key = g.c + "|" + g.record_id;
      if (moved[key]) continue;
      const rec = captureRow(g.c, g.record_id);
      if (!rec) {
        moved[key] = true;
        continue;
      }
      const qrec = new Record(quarantineCol, {
        source_collection: g.c,
        source_id: g.record_id,
        owner: g.owner,
        field: g.f,
        target_collection: g.t,
        target_id: g.target_id,
        kind: g.kind,
        payload: payloadOf(rec),
        quarantined_at: iso(now),
      });
      dao.saveRecord(qrec);
      dao.deleteRecord(rec); // cascades / null-repairs dependents like a normal delete
      moved[key] = true;
    }

    for (let i = 0; i < findings.length; i++) {
      const g = findings[i];
      if (g.required) continue;
      if (moved[g.c + "|" + g.record_id]) continue;
      const rec = captureRow(g.c, g.record_id);
      if (!rec) continue;
      rec.set(g.f, "");
      dao.saveRecord(rec);
    }

    // --- 2f. One report row, only when something was quarantined. -----------
    if (summary.cross_owner > 0 || summary.missing_target > 0) {
      const rrec = new Record(reportsCol, report);
      dao.saveRecord(rrec);
      console.log(
        JSON.stringify({
          v: "obs/v1",
          event: "relation_quarantine_applied",
          service: "pocketbase",
          cross_owner: summary.cross_owner,
          missing_target: summary.missing_target,
          checksum: report.checksum,
        }),
      );
    }
  },
  (_db) => {
    // Forward-only: every relation endpoint trigger stays in place and no
    // quarantined row is reinstated. Account isolation is never rolled back;
    // repair a too-tight predicate with a new forward migration
    // (docs/operations.md).
  },
);
