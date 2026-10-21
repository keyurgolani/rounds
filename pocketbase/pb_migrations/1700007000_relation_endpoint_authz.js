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
//      uniform client response. PocketBase rewrites every column on a save, so
//      the update trigger checks a relation only when that relation or the
//      row's owner changed: clearing one relation (as a delete's cascade does)
//      never re-checks the row's other, unchanged relations. The owner-scoped
//      collection rules from 1700006000 stay exactly as they are: this
//      migration adds endpoint authorization, it never relaxes or rewrites a
//      rule.
//   2. Existing cross-owner (and missing-target) references are quarantined
//      before the predicate starts rejecting them:
//        - a row whose required or cascading relation points at another
//          account (or a missing record) moves into relation_quarantine with
//          its cascade dependents (a variant brings its versions, share links,
//          and their views): every moved row is copied first, then deleted
//          leaf-first, so PocketBase's own cascade has nothing left to do;
//        - a reference on an optional, non-cascading field is cleared, all of a
//          row's offending fields in one update, and journalled; when clearing
//          it would collide with a unique index (SQLite treats an empty string
//          as a present value), the row moves instead;
//        - a non-cascading reference to a moved row (previous_offer) is cleared
//          and journalled the same way.
//      Each journal entry holds the migration, the row, the field, the original
//      row, per-report account pseudonyms, and a status (quarantined, replayed,
//      dropped). The original row is every column's raw value as text, read
//      by SQLite itself, so nothing is rounded or reordered; the replay lever
//      (pocketbase/levers/replay_quarantine.template.js) writes it back
//      exactly, created and updated included. One pseudonymized report row is
//      written to relation_quarantine_reports, reusing the scan_cross_owner.py
//      report shape. Anything unexpected fails the whole migration: the boot
//      aborts, nothing is written, and the failure is still logged (and, in a
//      dry run, reported). That covers a write failing for any reason other
//      than the unique collision above, a frozen relation that is missing or
//      no longer a single relation to its target, a changed required or
//      cascade option on a field with something to quarantine, and a relation
//      outside the frozen table that points at a row about to move.
//
// Dry run: with ROUNDS_RELATION_QUARANTINE=dry-run the migration takes exactly
// the apply's path, writes the report (outcomes and checksum included, or the
// failure the apply would hit) to ROUNDS_RELATION_QUARANTINE_REPORT (which must
// be set, outside pb_data), and then throws, so PocketBase rolls the
// transaction back. Nothing in the database changes. Operators run this
// against a copy of each deployment before the real upgrade
// (docs/operations.md).
//
// down() keeps every trigger: account isolation is never relaxed. A predicate
// that proves too tight is repaired with a forward-fix migration. The field
// list below is checked against relation_endpoints.v1.json, and the
// per-field disposition against pocketbase/migration-manifests/, by the
// contract test so they never drift.

const MIGRATION = "1700007000_relation_endpoint_authz";

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
// Every JSON field created here sets its own maxSize. PocketBase's own
// size-default migration has already run on an upgraded deployment, so a JSON
// field created without one keeps 0 and every later API write to the record
// fails validation. A moved row's payload holds its JSON columns as escaped
// text (the largest JSON field in the schema allows 4 MiB), and a large
// deployment's findings and outcomes can run to megabytes.
const JSON_MAX = 16 * 1024 * 1024;

migrate(
  (db) => {
    const dao = new Dao(db);
    const q = (sql) => db.newQuery(sql).execute();
    const has = (obj, key) => Object.prototype.hasOwnProperty.call(obj, key);
    const textOf = (err) => String(err) + " " + (err && err.message ? String(err.message) : "");
    const byKey = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

    const dryRun = ($os.getenv("ROUNDS_RELATION_QUARANTINE") || "").trim().toLowerCase() === "dry-run";
    const reportPath = ($os.getenv("ROUNDS_RELATION_QUARANTINE_REPORT") || "").trim();
    if (dryRun) {
      // Checked before anything else: without a usable path there is nowhere
      // to write the dry run's report.
      if (!reportPath) {
        throw new Error(
          "relation_endpoint_authz: ROUNDS_RELATION_QUARANTINE=dry-run needs ROUNDS_RELATION_QUARANTINE_REPORT set to a path outside pb_data",
        );
      }
      if (reportPath.indexOf("pb_data") >= 0) {
        throw new Error(
          "relation_endpoint_authz: refusing to write the dry-run report inside pb_data (" + reportPath + ")",
        );
      }
    }

    // What the failure path reports, filled in as the migration goes.
    const now = new Date();
    const iso = (d) => d.toISOString().replace(/\.\d{3}Z$/, "Z");
    const sourceCollections = {};
    for (let i = 0; i < FIELDS.length; i++) sourceCollections[FIELDS[i].c] = true;
    const perField = [];
    const findings = []; // { kind, c, f, record_id, t, target_id, owner, target_owner, required, cascade }
    let publicFindings = [];
    const summary = {
      owned_collections: Object.keys(sourceCollections).length,
      relations_checked: FIELDS.length,
      rows_scanned: 0,
      references_checked: 0,
      cross_owner: 0,
      missing_target: 0,
    };
    const labels = {};
    const label = (account) => {
      if (account === null || account === undefined || account === "") return null;
      if (!has(labels, account)) {
        const n = Object.keys(labels).length + 1;
        labels[account] = "acct-" + (n < 10 ? "0" + n : "" + n);
      }
      return labels[account];
    };

    const buildReport = (status, publicOutcomes) => {
      const body = { version: REPORT_VERSION, relations: perField, findings: publicFindings };
      if (publicOutcomes) body.outcomes = publicOutcomes;
      const out = {
        report_kind: REPORT_KIND,
        report_version: REPORT_VERSION,
        generated_at: iso(now),
        expires_at: iso(new Date(now.getTime() + RETENTION_DAYS * 86400000)),
        checksum: publicOutcomes ? "sha256:" + $security.sha256(JSON.stringify(body)) : null,
        dry_run: dryRun,
        status: status,
        summary: Object.assign({}, summary),
        relations: perField,
        findings: publicFindings,
        outcomes: publicOutcomes || [],
      };
      if (publicOutcomes) {
        out.summary.rows_moved = publicOutcomes.filter((o) => o.action === "moved").length;
        out.summary.dependents_moved = publicOutcomes.filter((o) => o.action === "moved" && o.kind === "dependent").length;
        out.summary.references_cleared = publicOutcomes.filter((o) => o.action === "cleared").length;
        out.summary.unique_fallbacks = publicOutcomes.filter((o) => o.unique_fallback).length;
      }
      return out;
    };
    const counts = (rep) => ({
      cross_owner: rep.summary.cross_owner,
      missing_target: rep.summary.missing_target,
      rows_moved: rep.summary.rows_moved || 0,
      references_cleared: rep.summary.references_cleared || 0,
      unique_fallbacks: rep.summary.unique_fallbacks || 0,
    });
    const logLine = (event, fields) => {
      console.log(JSON.stringify(Object.assign({ v: "obs/v1", event: event, service: "pocketbase" }, fields)));
    };
    const writeDryRunReport = (rep) => {
      $os.writeFile(reportPath, JSON.stringify(rep, null, 2) + "\n", 0o600);
    };

    let stage = "triggers";
    let report = null;
    try {
      // --- 1. Atomic triggers for every relation field. ---------------------
      for (let i = 0; i < FIELDS.length; i++) {
        const r = FIELDS[i];
        const base = "rel_authz_" + r.c + "_" + r.f;
        const mismatch =
          'NEW."' + r.f + '" IS NOT NULL AND NEW."' + r.f + "\" != '' AND NOT EXISTS " +
          '(SELECT 1 FROM "' + r.t + '" tgt WHERE tgt."id" = NEW."' + r.f + '" AND tgt."' + OWNER + '" = NEW."' + OWNER + '")';
        // PocketBase's save rewrites every column, so UPDATE OF fires on any
        // save; check the relation only when it, or the row's owner, changed.
        const changed =
          '(NEW."' + r.f + '" IS NOT OLD."' + r.f + '" OR NEW."' + OWNER + '" IS NOT OLD."' + OWNER + '")';
        q('DROP TRIGGER IF EXISTS "' + base + '_ins"');
        q('DROP TRIGGER IF EXISTS "' + base + '_upd"');
        q('DROP TRIGGER IF EXISTS "' + base + '_tgt"');
        q(
          'CREATE TRIGGER "' + base + '_ins" BEFORE INSERT ON "' + r.c + '" FOR EACH ROW WHEN ' +
          mismatch + " BEGIN SELECT RAISE(ABORT, 'relation endpoint denied'); END",
        );
        q(
          'CREATE TRIGGER "' + base + '_upd" BEFORE UPDATE OF "' + r.f + '", "' + OWNER + '" ON "' + r.c +
          '" FOR EACH ROW WHEN ' + changed + " AND " + mismatch +
          " BEGIN SELECT RAISE(ABORT, 'relation endpoint denied'); END",
        );
        q(
          'CREATE TRIGGER "' + base + '_tgt" BEFORE UPDATE OF "' + OWNER + '" ON "' + r.t +
          '" FOR EACH ROW WHEN NEW."' + OWNER + '" != OLD."' + OWNER + '" AND EXISTS ' +
          '(SELECT 1 FROM "' + r.c + '" src WHERE src."' + r.f + '" = OLD."id" AND src."' + OWNER + '" != NEW."' + OWNER + '") ' +
          "BEGIN SELECT RAISE(ABORT, 'relation endpoint denied'); END",
        );
      }

      // --- 2a. Quarantine collections (superuser-only). ---------------------
      stage = "collections";
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
        { name: "migration", type: "text", required: true },
        { name: "report_checksum", type: "text", required: false },
        { name: "source_collection", type: "text", required: true },
        { name: "source_id", type: "text", required: true },
        { name: "field", type: "text", required: true },
        { name: "target_collection", type: "text", required: false },
        { name: "target_id", type: "text", required: false },
        { name: "kind", type: "text", required: true },
        { name: "action", type: "text", required: true },
        { name: "unique_fallback", type: "bool", required: false },
        { name: "owner", type: "text", required: false },
        { name: "target_owner", type: "text", required: false },
        { name: "payload", type: "json", required: false, options: { maxSize: JSON_MAX } },
        { name: "status", type: "text", required: true },
        { name: "quarantined_at", type: "text", required: false },
      ]);
      const reportsCol = ensureCollection("relation_quarantine_reports", [
        { name: "report_kind", type: "text", required: true },
        { name: "report_version", type: "text", required: true },
        { name: "generated_at", type: "text", required: true },
        { name: "expires_at", type: "text", required: false },
        { name: "checksum", type: "text", required: false },
        { name: "dry_run", type: "bool", required: false },
        { name: "status", type: "text", required: false },
        { name: "summary", type: "json", required: false, options: { maxSize: JSON_MAX } },
        { name: "relations", type: "json", required: false, options: { maxSize: JSON_MAX } },
        { name: "findings", type: "json", required: false, options: { maxSize: JSON_MAX } },
        { name: "outcomes", type: "json", required: false, options: { maxSize: JSON_MAX } },
      ]);
      const quarantineCol = dao.findCollectionByNameOrId("relation_quarantine");

      // --- 2b. Find existing cross-owner / missing-target references. --------
      stage = "scan";
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
            if (!has(owners, ref)) {
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
              required: r.required,
              cascade: r.cascade,
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
      findings.sort((a, b) =>
        byKey(a.c + "|" + a.f + "|" + a.record_id + "|" + a.target_id, b.c + "|" + b.f + "|" + b.record_id + "|" + b.target_id),
      );
      // Pseudonymize accounts for the report (never store account ids).
      publicFindings = findings.map((g) => ({
        kind: g.kind,
        collection: g.c,
        field: g.f,
        record_id: g.record_id,
        target_collection: g.t,
        target_id: g.target_id,
        owner: label(g.owner),
        target_owner: label(g.target_owner),
      }));
      summary.rows_scanned = perField.reduce((s, r) => s + r.rows, 0);
      summary.references_checked = perField.reduce((s, r) => s + r.references, 0);
      summary.cross_owner = publicFindings.filter((f) => f.kind === "cross_owner").length;
      summary.missing_target = publicFindings.filter((f) => f.kind === "missing_target").length;

      // --- 2c. Plan: clear, then close over the rows that move. --------------
      stage = "plan";
      const fieldsBySource = {};
      const fieldsByTarget = {};
      for (let i = 0; i < FIELDS.length; i++) {
        const r = FIELDS[i];
        (fieldsBySource[r.c] = fieldsBySource[r.c] || []).push(r);
        (fieldsByTarget[r.t] = fieldsByTarget[r.t] || []).push(r);
      }

      // The live schema of the base and auth collections (views hold no rows
      // a delete can reach), read from _collections in this transaction.
      const colRows = arrayOf(new DynamicModel({ id: "", name: "", type: "", schema: "" }));
      db.newQuery('SELECT "id" AS id, "name" AS name, "type" AS type, "schema" AS schema FROM "_collections"').all(colRows);
      const nameById = {};
      for (let i = 0; i < colRows.length; i++) nameById[colRows[i].id] = colRows[i].name;
      const liveRelations = []; // { c, f, t, required, cascade, max }
      for (let i = 0; i < colRows.length; i++) {
        if (colRows[i].type === "view") continue;
        let fields = [];
        try {
          fields = JSON.parse(colRows[i].schema || "[]");
        } catch (_) {}
        if (!Array.isArray(fields)) continue;
        for (let j = 0; j < fields.length; j++) {
          const fd = fields[j];
          if (!fd || fd.type !== "relation") continue;
          const o = fd.options || {};
          liveRelations.push({
            c: colRows[i].name,
            f: fd.name,
            t: nameById[o.collectionId] || "",
            required: !!fd.required,
            cascade: !!o.cascadeDelete,
            max: o.maxSelect,
          });
        }
      }

      // Guard. The trigger above can only enforce a frozen field that is
      // still a single relation to its frozen target, so anything else stops
      // the migration whatever it holds. The disposition reads the frozen
      // required and cascade flags, so a changed flag stops it only on a field
      // with something to quarantine. A relation outside the table stops it
      // only when it points at a row about to move (checked in the closure).
      const listed = {};
      for (let i = 0; i < FIELDS.length; i++) listed[FIELDS[i].c + "." + FIELDS[i].f] = FIELDS[i];
      const liveByKey = {};
      const unlistedByTarget = {}; // target -> [{ c, f }]
      for (let i = 0; i < liveRelations.length; i++) {
        const rel = liveRelations[i];
        const key = rel.c + "." + rel.f;
        if (has(listed, key)) liveByKey[key] = rel;
        else (unlistedByTarget[rel.t] = unlistedByTarget[rel.t] || []).push(rel);
      }
      const withFindings = {};
      for (let i = 0; i < findings.length; i++) withFindings[findings[i].c + "." + findings[i].f] = true;
      for (let i = 0; i < FIELDS.length; i++) {
        const want = FIELDS[i];
        const key = want.c + "." + want.f;
        const live = liveByKey[key];
        if (!live) {
          throw new Error("relation_endpoint_authz: schema: " + key + " is missing or no longer a relation");
        }
        if (live.t !== want.t || live.max !== 1) {
          throw new Error("relation_endpoint_authz: schema: " + key + " is no longer a single relation to " + want.t);
        }
        if (withFindings[key] && (live.required !== want.required || live.cascade !== want.cascade)) {
          throw new Error(
            "relation_endpoint_authz: schema: " + key + " has something to quarantine but its required or cascade option changed",
          );
        }
      }

      // The original row: every column's raw value as text (a real with all
      // 17 significant digits), or null, as SQLite reads it, so a big integer,
      // a real, and a JSON column's key order all survive.
      const columnsOf = (table) => {
        const rows = arrayOf(new DynamicModel({ name: "" }));
        db.newQuery("SELECT name FROM pragma_table_info({:t}) ORDER BY cid").bind({ t: table }).all(rows);
        return rows.map((r) => r.name);
      };
      const rawValue = (n) =>
        "CASE typeof(\"" + n + "\") WHEN 'null' THEN NULL WHEN 'real' THEN printf('%!.17g', \"" + n +
        "\") ELSE CAST(\"" + n + "\" AS TEXT) END";
      const rawExpr = {};
      const rawRowSql = (table) => {
        if (!rawExpr[table]) {
          // json_object takes at most 63 pairs (127 arguments), so wider
          // tables add the rest with json_set, which keeps the key order and
          // stores a null as null.
          const cols = columnsOf(table);
          const CHUNK = 50;
          let expr = "json_object(" + cols.slice(0, CHUNK).map((n) => "'" + n + "', " + rawValue(n)).join(", ") + ")";
          for (let i = CHUNK; i < cols.length; i += CHUNK) {
            expr = "json_set(" + expr + ", " +
              cols.slice(i, i + CHUNK).map((n) => "'$.\"" + n + "\"', " + rawValue(n)).join(", ") + ")";
          }
          rawExpr[table] = expr;
        }
        return "SELECT " + rawExpr[table] + ' AS payload, "' + OWNER + '" AS owner FROM "' + table + '" WHERE "id" = {:id}';
      };
      const keyOf = (c, id) => c + "|" + id;
      const snapshots = {}; // key -> { owner, payload (JSON text), refs (parsed) }
      const capture = (c, id) => {
        const k = keyOf(c, id);
        if (has(snapshots, k)) return snapshots[k];
        const rows = arrayOf(new DynamicModel({ payload: "", owner: "" }));
        db.newQuery(rawRowSql(c)).bind({ id: id }).all(rows);
        if (rows.length !== 1) throw new Error("relation_endpoint_authz: " + c + " row vanished while being quarantined");
        // Every value is text or null, so parsing it in JS loses nothing; it
        // is only read for relation ids, never written back.
        snapshots[k] = { owner: rows[0].owner || "", payload: rows[0].payload, refs: JSON.parse(rows[0].payload) };
        return snapshots[k];
      };

      // Findings grouped per row, in scan order; every scanned row captured.
      const rowFindings = {};
      const rowOrder = [];
      for (let i = 0; i < findings.length; i++) {
        const g = findings[i];
        const k = keyOf(g.c, g.record_id);
        if (!rowFindings[k]) {
          rowFindings[k] = [];
          rowOrder.push(k);
        }
        rowFindings[k].push(g);
      }
      rowOrder.sort(byKey);
      for (let i = 0; i < rowOrder.length; i++) {
        const g = rowFindings[rowOrder[i]][0];
        capture(g.c, g.record_id);
      }

      const moved = {}; // key -> entry
      const movedOrder = [];
      const cleared = [];
      const addMove = (entry) => {
        const k = keyOf(entry.c, entry.id);
        if (moved[k]) return;
        moved[k] = entry;
        movedOrder.push(k);
      };
      const fromFinding = (g, extra) => ({
        c: g.c,
        id: g.record_id,
        kind: g.kind,
        field: g.f,
        t: g.t,
        target_id: g.target_id,
        owner: g.owner,
        target_owner: g.target_owner,
        unique_fallback: !!(extra && extra.unique_fallback),
      });

      // Only a unique-index collision falls back to moving the row; any other
      // failure to clear is unexpected and fails the migration whole.
      const isUniqueCollision = (err) => textOf(err).indexOf("UNIQUE constraint failed") >= 0;
      const clearFields = (c, id, fields) => {
        const rec = dao.findRecordById(c, id);
        for (let i = 0; i < fields.length; i++) rec.set(fields[i], "");
        try {
          dao.saveRecord(rec);
          return true;
        } catch (err) {
          if (isUniqueCollision(err)) return false;
          throw err;
        }
      };

      // A required or cascading reference moves the row.
      for (let i = 0; i < rowOrder.length; i++) {
        const gs = rowFindings[rowOrder[i]];
        for (let j = 0; j < gs.length; j++) {
          if (gs[j].required || gs[j].cascade) {
            addMove(fromFinding(gs[j]));
            break;
          }
        }
      }

      // The rest are optional, non-cascading: clear all of a row's offending
      // fields in one update, or move the row on a unique collision.
      for (let i = 0; i < rowOrder.length; i++) {
        const k = rowOrder[i];
        if (moved[k]) continue;
        const gs = rowFindings[k];
        const fields = gs.map((g) => g.f);
        if (clearFields(gs[0].c, gs[0].record_id, fields)) {
          for (let j = 0; j < gs.length; j++) {
            cleared.push({
              c: gs[j].c,
              id: gs[j].record_id,
              kind: gs[j].kind,
              field: gs[j].f,
              t: gs[j].t,
              target_id: gs[j].target_id,
              owner: gs[j].owner,
              target_owner: gs[j].target_owner,
            });
          }
        } else {
          addMove(fromFinding(gs[0], { unique_fallback: true }));
        }
      }

      // Close over the moved rows: a cascading (or required) dependent moves
      // with its parent; a non-cascading reference to a moved row is cleared,
      // or its row moves on a unique collision. A relation outside the frozen
      // table that points at a moved row stops the migration.
      const pointsAt = (f) =>
        '("' + f + '" = {:ref} OR (json_valid("' + f + '") AND EXISTS (SELECT 1 FROM json_each("' + f + '") WHERE value = {:ref})))';
      const dependentsOf = (c, id) => {
        const out = [];
        const rels = fieldsByTarget[c] || [];
        for (let i = 0; i < rels.length; i++) {
          const r = rels[i];
          const rows = arrayOf(new DynamicModel({ id: "", owner: "" }));
          db.newQuery(
            'SELECT "id" AS id, "' + OWNER + '" AS owner FROM "' + r.c + '" WHERE "' + r.f + '" = {:ref} ORDER BY "id"',
          )
            .bind({ ref: id })
            .all(rows);
          for (let j = 0; j < rows.length; j++) out.push({ r: r, id: rows[j].id, owner: rows[j].owner || "" });
        }
        const others = unlistedByTarget[c] || [];
        for (let i = 0; i < others.length; i++) {
          const rows = arrayOf(new DynamicModel({ n: 0 }));
          db.newQuery('SELECT COUNT(*) AS n FROM "' + others[i].c + '" WHERE ' + pointsAt(others[i].f))
            .bind({ ref: id })
            .all(rows);
          if (rows.length && rows[0].n > 0) {
            throw new Error(
              "relation_endpoint_authz: schema: " + others[i].c + "." + others[i].f + " points at a " + c +
                " row about to move but is not in the frozen relation table",
            );
          }
        }
        return out;
      };
      const referenceCleared = {};
      for (let n = 0; n < movedOrder.length; n++) {
        const parent = moved[movedOrder[n]];
        const parentOwner = capture(parent.c, parent.id).owner;
        const deps = dependentsOf(parent.c, parent.id);
        for (let i = 0; i < deps.length; i++) {
          const d = deps[i];
          const dk = keyOf(d.r.c, d.id);
          if (moved[dk]) continue;
          capture(d.r.c, d.id);
          const entry = {
            c: d.r.c,
            id: d.id,
            kind: d.r.required || d.r.cascade ? "dependent" : "reference",
            field: d.r.f,
            t: parent.c,
            target_id: parent.id,
            owner: d.owner,
            target_owner: parentOwner,
            unique_fallback: false,
          };
          if (d.r.required || d.r.cascade) {
            addMove(entry);
            continue;
          }
          const rk = dk + "|" + d.r.f;
          if (referenceCleared[rk]) continue;
          if (clearFields(d.r.c, d.id, [d.r.f])) {
            referenceCleared[rk] = true;
            cleared.push(entry);
          } else {
            entry.unique_fallback = true;
            addMove(entry);
          }
        }
      }

      // Outcomes in a fixed order, pseudonymized after the findings.
      const outcomes = [];
      for (let i = 0; i < movedOrder.length; i++) outcomes.push({ action: "moved", e: moved[movedOrder[i]] });
      for (let i = 0; i < cleared.length; i++) outcomes.push({ action: "cleared", e: cleared[i] });
      outcomes.sort((a, b) =>
        byKey(a.e.c + "|" + a.e.id + "|" + a.e.field + "|" + a.action, b.e.c + "|" + b.e.id + "|" + b.e.field + "|" + b.action),
      );
      const publicOutcomes = outcomes.map((o) => ({
        action: o.action,
        kind: o.e.kind,
        collection: o.e.c,
        record_id: o.e.id,
        field: o.e.field,
        target_collection: o.e.t,
        target_id: o.e.target_id,
        owner: label(o.e.owner),
        target_owner: label(o.e.target_owner),
        unique_fallback: !!o.e.unique_fallback,
      }));
      report = buildReport("ok", publicOutcomes);

      // --- 2d. Copy every quarantined row first: one journal entry per ------
      //         outcome, with the original row.
      stage = "journal";
      for (let i = 0; i < outcomes.length; i++) {
        const o = outcomes[i];
        const pub = publicOutcomes[i];
        dao.saveRecord(
          new Record(quarantineCol, {
            migration: MIGRATION,
            report_checksum: report.checksum,
            source_collection: o.e.c,
            source_id: o.e.id,
            field: o.e.field,
            target_collection: o.e.t,
            target_id: o.e.target_id,
            kind: o.e.kind,
            action: o.action,
            unique_fallback: !!o.e.unique_fallback,
            owner: pub.owner || "",
            target_owner: pub.target_owner || "",
            payload: snapshots[keyOf(o.e.c, o.e.id)].payload,
            status: "quarantined",
            quarantined_at: iso(now),
          }),
        );
      }

      // --- 2e. Then delete the moved rows leaf-first: a row that points at ---
      //         another moved row goes before it, so no delete cascades into a
      //         row that has not been copied, and PocketBase's own cascade
      //         finds nothing left.
      stage = "delete";
      const depth = {};
      const visiting = {};
      const depthOf = (k) => {
        if (has(depth, k)) return depth[k];
        if (visiting[k]) return 0; // a reference cycle: the delete clears the remaining link
        visiting[k] = true;
        const m = moved[k];
        const refs = snapshots[k].refs;
        const rels = fieldsBySource[m.c] || [];
        let d = 0;
        for (let i = 0; i < rels.length; i++) {
          const ref = refs[rels[i].f];
          if (typeof ref !== "string" || ref === "") continue;
          const pk = keyOf(rels[i].t, ref);
          if (pk !== k && moved[pk]) d = Math.max(d, depthOf(pk) + 1);
        }
        visiting[k] = false;
        depth[k] = d;
        return d;
      };
      const order = movedOrder.slice().sort((a, b) => depthOf(b) - depthOf(a) || byKey(a, b));
      for (let i = 0; i < order.length; i++) {
        const m = moved[order[i]];
        let rec = null;
        try {
          rec = dao.findRecordById(m.c, m.id);
        } catch (_) {
          rec = null; // already gone with a moved parent; it was copied above
        }
        if (rec) dao.deleteRecord(rec);
      }

      // --- 2f. One report row, only when something was quarantined. ---------
      stage = "report";
      if (summary.cross_owner > 0 || summary.missing_target > 0) {
        dao.saveRecord(new Record(reportsCol, report));
      }
    } catch (err) {
      const schema = textOf(err).indexOf("relation_endpoint_authz: schema:") >= 0;
      const reason = schema ? "schema_mismatch" : "apply_failed";
      if (dryRun) {
        const failed = buildReport("failed", null);
        failed.stage = stage;
        failed.error = textOf(err).trim();
        writeDryRunReport(failed);
        logLine(
          "relation_quarantine_dry_run",
          Object.assign({ status: "failed", stage: stage, reason: reason, report: reportPath }, counts(failed)),
        );
        throw new Error(
          "relation_endpoint_authz: dry run found the apply would fail; report written to " + reportPath +
            "; aborting so nothing changes",
        );
      }
      logLine("relation_quarantine_failed", { stage: stage, reason: reason });
      throw new Error(
        "relation_endpoint_authz: the quarantine could not be applied (" + reason + " at " + stage +
          "), so nothing was changed; run the dry run on a copy for the details",
      );
    }

    // --- 3. Dry run: the apply ran above; write the report and roll back. ---
    if (dryRun) {
      writeDryRunReport(report);
      logLine(
        "relation_quarantine_dry_run",
        Object.assign({ status: "ok", report: reportPath, checksum: report.checksum }, counts(report)),
      );
      throw new Error(
        "relation_endpoint_authz: dry run complete; report written to " + reportPath + "; aborting so nothing changes",
      );
    }

    if (summary.cross_owner > 0 || summary.missing_target > 0) {
      logLine("relation_quarantine_applied", Object.assign({ checksum: report.checksum }, counts(report)));
    }
  },
  (_db) => {
    // Forward-only: every relation endpoint trigger stays in place and no
    // quarantined row is reinstated. Account isolation is never rolled back;
    // repair a too-tight predicate with a new forward migration
    // (docs/operations.md).
  },
);
