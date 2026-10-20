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
//      row JSON, per-report account pseudonyms, and a status (quarantined,
//      replayed, dropped). One pseudonymized report row is written to
//      relation_quarantine_reports, reusing the scan_cross_owner.py report
//      shape. Anything unexpected (a schema that no longer matches the frozen
//      table below, or a write that fails for any reason other than the unique
//      collision above) fails the whole migration: the boot aborts and nothing
//      is written.
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

migrate(
  (db) => {
    const dao = new Dao(db);
    const q = (sql) => db.newQuery(sql).execute();
    const has = (obj, key) => Object.prototype.hasOwnProperty.call(obj, key);
    const textOf = (err) => String(err) + " " + (err && err.message ? String(err.message) : "");

    const dryRun = ($os.getenv("ROUNDS_RELATION_QUARANTINE") || "").trim().toLowerCase() === "dry-run";
    const reportPath = ($os.getenv("ROUNDS_RELATION_QUARANTINE_REPORT") || "").trim();
    if (dryRun) {
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

    // --- 1. Atomic triggers for every relation field. -----------------------
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
      { name: "payload", type: "json", required: false },
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
      { name: "summary", type: "json", required: false },
      { name: "relations", type: "json", required: false },
      { name: "findings", type: "json", required: false },
      { name: "outcomes", type: "json", required: false },
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

    const findings = []; // { kind, c, f, record_id, t, target_id, owner, target_owner, required, cascade }
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

    const byKey = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
    findings.sort((a, b) =>
      byKey(a.c + "|" + a.f + "|" + a.record_id + "|" + a.target_id, b.c + "|" + b.f + "|" + b.record_id + "|" + b.target_id),
    );

    // --- 2c. Pseudonymize accounts for the report (never store account ids). -
    const labels = {};
    const label = (account) => {
      if (account === null || account === undefined || account === "") return null;
      if (!has(labels, account)) {
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

    // --- 2d. Quarantine. The dry run takes this same path, then throws. -------
    const quarantine = () => {
      const fieldsBySource = {};
      const fieldsByTarget = {};
      for (let i = 0; i < FIELDS.length; i++) {
        const r = FIELDS[i];
        (fieldsBySource[r.c] = fieldsBySource[r.c] || []).push(r);
        (fieldsByTarget[r.t] = fieldsByTarget[r.t] || []).push(r);
      }

      // The live schema, read from _collections in this transaction.
      const colRows = arrayOf(new DynamicModel({ id: "", name: "", schema: "" }));
      db.newQuery('SELECT "id" AS id, "name" AS name, "schema" AS schema FROM "_collections"').all(colRows);
      const nameById = {};
      const schemaByName = {};
      for (let i = 0; i < colRows.length; i++) nameById[colRows[i].id] = colRows[i].name;
      for (let i = 0; i < colRows.length; i++) {
        let fields = [];
        try {
          fields = JSON.parse(colRows[i].schema || "[]");
        } catch (_) {}
        schemaByName[colRows[i].name] = Array.isArray(fields) ? fields : [];
      }

      // Guard: the closure below follows the frozen table, so the live schema
      // must still match it, and no other relation may point into a collection
      // that can lose a row. Otherwise fail whole, before writing anything.
      const listed = {};
      for (let i = 0; i < FIELDS.length; i++) listed[FIELDS[i].c + "." + FIELDS[i].f] = FIELDS[i];
      const seen = {};
      const names = Object.keys(schemaByName);
      for (let i = 0; i < names.length; i++) {
        const fields = schemaByName[names[i]];
        for (let j = 0; j < fields.length; j++) {
          const fd = fields[j];
          if (!fd || fd.type !== "relation") continue;
          const o = fd.options || {};
          const key = names[i] + "." + fd.name;
          const target = nameById[o.collectionId] || "";
          const want = listed[key];
          if (want) {
            seen[key] = true;
            if (target !== want.t || !!fd.required !== want.required || !!o.cascadeDelete !== want.cascade || o.maxSelect !== 1) {
              throw new Error("relation_endpoint_authz: schema: " + key + " no longer matches the frozen relation table");
            }
          } else if (has(fieldsBySource, target)) {
            throw new Error("relation_endpoint_authz: schema: " + key + " points into " + target + " but is not in the frozen relation table");
          }
        }
      }
      for (let i = 0; i < FIELDS.length; i++) {
        if (!seen[FIELDS[i].c + "." + FIELDS[i].f]) {
          throw new Error("relation_endpoint_authz: schema: " + FIELDS[i].c + "." + FIELDS[i].f + " is missing");
        }
      }

      // The original row, as JSON, captured before anything is written.
      const valueOf = (rec, fd) => {
        const n = fd.name;
        const o = fd.options || {};
        if (fd.type === "number") return rec.getFloat(n);
        if (fd.type === "bool") return rec.getBool(n);
        if (fd.type === "json") {
          const raw = rec.getString(n);
          if (raw === "") return null;
          try {
            return JSON.parse(raw);
          } catch (_) {
            return raw;
          }
        }
        if ((fd.type === "select" || fd.type === "file" || fd.type === "relation") && o.maxSelect !== 1) {
          return rec.getStringSlice(n);
        }
        return rec.getString(n);
      };
      const keyOf = (c, id) => c + "|" + id;
      const snapshots = {}; // key -> { owner, payload }
      const capture = (c, id) => {
        const k = keyOf(c, id);
        if (has(snapshots, k)) return snapshots[k];
        const rec = dao.findRecordById(c, id);
        const payload = { id: rec.id, created: rec.getString("created"), updated: rec.getString("updated") };
        const fields = schemaByName[c] || [];
        for (let i = 0; i < fields.length; i++) payload[fields[i].name] = valueOf(rec, fields[i]);
        snapshots[k] = { owner: rec.getString(OWNER), payload: payload };
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
      // or its row moves on a unique collision.
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
      return { outcomes: outcomes, publicOutcomes: publicOutcomes, moved: moved, movedOrder: movedOrder, snapshots: snapshots, keyOf: keyOf, fieldsBySource: fieldsBySource };
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

    let report;
    try {
      const plan = quarantine();
      report = buildReport("ok", plan.publicOutcomes);

      // Copy every quarantined row first: one journal entry per outcome, with
      // the original row JSON.
      for (let i = 0; i < plan.outcomes.length; i++) {
        const o = plan.outcomes[i];
        const pub = plan.publicOutcomes[i];
        const snap = plan.snapshots[plan.keyOf(o.e.c, o.e.id)];
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
            payload: snap.payload,
            status: "quarantined",
            quarantined_at: iso(now),
          }),
        );
      }

      // Then delete the moved rows leaf-first: a row that points at another
      // moved row goes before it, so no delete cascades into a row that has
      // not been copied, and PocketBase's own cascade finds nothing left.
      const depth = {};
      const visiting = {};
      const depthOf = (k) => {
        if (has(depth, k)) return depth[k];
        if (visiting[k]) return 0; // a reference cycle: the delete clears the remaining link
        visiting[k] = true;
        const m = plan.moved[k];
        const payload = plan.snapshots[k].payload;
        const rels = plan.fieldsBySource[m.c] || [];
        let d = 0;
        for (let i = 0; i < rels.length; i++) {
          const ref = payload[rels[i].f];
          if (typeof ref !== "string" || ref === "") continue;
          const pk = plan.keyOf(rels[i].t, ref);
          if (pk !== k && plan.moved[pk]) d = Math.max(d, depthOf(pk) + 1);
        }
        visiting[k] = false;
        depth[k] = d;
        return d;
      };
      const order = plan.movedOrder.slice().sort((a, b) => depthOf(b) - depthOf(a) || byKey(a, b));
      for (let i = 0; i < order.length; i++) {
        const m = plan.moved[order[i]];
        let rec = null;
        try {
          rec = dao.findRecordById(m.c, m.id);
        } catch (_) {
          rec = null; // already gone with a moved parent; it was copied above
        }
        if (rec) dao.deleteRecord(rec);
      }

      // One report row, only when something was quarantined.
      if (summary.cross_owner > 0 || summary.missing_target > 0) {
        dao.saveRecord(new Record(reportsCol, report));
      }
    } catch (err) {
      const schema = textOf(err).indexOf("relation_endpoint_authz: schema:") >= 0;
      if (dryRun) {
        const failed = buildReport("failed", null);
        failed.error = textOf(err).trim();
        writeDryRunReport(failed);
        logLine("relation_quarantine_dry_run", Object.assign({ status: "failed", report: reportPath }, counts(failed)));
        throw new Error(
          "relation_endpoint_authz: dry run found the apply would fail; report written to " + reportPath +
            "; aborting so nothing changes",
        );
      }
      logLine("relation_quarantine_failed", { reason: schema ? "schema_mismatch" : "apply_failed" });
      throw new Error(
        "relation_endpoint_authz: the quarantine could not be applied (" + (schema ? "schema mismatch" : "apply failed") +
          "), so nothing was changed; run the dry run on a copy for the details",
      );
    }

    // --- 2e. Dry run: the apply ran above; write the report and roll back. ---
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
