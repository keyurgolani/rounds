/// <reference path="../pb_data/types.d.ts" />

// Older share links (ROUNDS-00B-L06 stage 1, manifest legacy-shares-v1).
//
// Every share link made before this release stops working here, for good.
// Each one keeps its row, so its owner still sees it under "Older links" in
// the share dialog and can make a new link in its place: "Get a new link" is
// CreateShare with the old link's id (pb_hooks/share_secrets.js), which sets
// that row's `replaced_by`. No secret an old link was made with survives this
// migration, and nothing here can bring one back.
//
// PocketBase applies it at start, before it serves a request, in one
// transaction:
//
//   1. resume_share_links gains legacy_status, legacy_reason, turned_off_at,
//      manifest_id, and replaced_by: a share capability of the link's own
//      account, held there by the owner triggers every typed relation gets
//      (FIELDS, as 1700008200_share_capabilities.js adds them). The
//      legacy_share_migration journal is created, every rule null.
//   2. The rules on the two share collections become:
//        resume_share_links  list, view
//            legacy_status != "revoked_ownership" && user = @request.auth.id
//        resume_share_views  list, view
//            link.legacy_status != "revoked_ownership" && user = @request.auth.id
//        both                create, update, delete: null, so no client
//                            writes either one again
//   3. Every link, in id order and BATCH at a time, gets one outcome
//      (classify() below):
//        migrated            its owner owns what it points at, a variant's
//                            parent resume included; it was made the way the
//                            runner makes links, with no password or expiry;
//                            and its owner isn't a demo account. Its owner
//                            can get a new link for it.
//        revoked_ownership   it points at another account's resume or
//                            variant. Its owner never sees it again; only the
//                            receipt counts it.
//        revoked_demo        its owner is a demo account.
//        revoked_unverified  anything else, with a reason code.
//      Its views are counted (how many, and the first and last day) into
//      one journal row per link, whose id is the link's own id, so no two
//      links can ever share a row. A link that already has a journal row
//      keeps that row's outcome, reason, counts, and date, so running this
//      again writes the same journal.
//   4. Every view row keeps only the day it was viewed (DAY below).
//   5. relation_quarantine's entries for both collections
//      (ROUNDS-00B-L02) keep nothing of an old link's secret or of who
//      viewed it either, and each quarantined link gets its own journal
//      row: revoked_ownership, with the entry's kind as its reason, and an
//      incident when it was ever viewed.
//   6. The link fields only links made before this release used are
//      dropped, with their index.
//
// Anything unexpected (a collection or field that isn't there, an entry
// whose payload isn't a JSON object) fails the whole migration: nothing
// commits, and it logs legacy_share_failed with the step it reached. It logs
// one legacy_share_batch line per batch and one legacy_share_migrated line
// with its counts, never an id, a secret, or a value. `pocketbase
// legacy-share-receipt` (pb_hooks/legacy_shares.js) reports the journal.
//
// down() leaves the journal, the rules, legacy_status, and replaced_by as
// they are. It takes off the other fields step 1 added and puts step 6's
// fields back empty, with no index. It brings no link back: nothing here kept a copy of any secret,
// and the rules and statuses it keeps still turn every old link off.
//
// The lint entry in scripts/migration-lint-allowlist.json is pinned to this
// file and waits on the owner's review;
// pocketbase/migration-manifests/legacy-shares-v1.json gives each change its
// disposition.

const MANIFEST = "legacy-shares-v1";
const PREDICATE_VERSION = 1;
const BATCH = 500;
const LINKS = "resume_share_links";
const VIEWS = "resume_share_views";
const JOURNAL = "legacy_share_migration";
const QUARANTINE = "relation_quarantine";
const OWNER = "user";

const OUTCOMES = ["migrated", "revoked_ownership", "revoked_demo", "revoked_unverified"];
// Every reason a journal row can carry, by outcome. The manifest and the
// receipt list the same codes (test_legacy_share_migration.py checks them).
const REASONS = {
  migrated: ["eligible"],
  revoked_ownership: ["target_owner", "parent_owner", "quarantined_cross_owner", "quarantined_missing_target",
    "quarantined_dependent", "quarantined_other"],
  revoked_demo: ["demo_account"],
  revoked_unverified: ["owner_missing", "no_target", "target_missing", "token_format", "password_set", "expiry_set"],
};
// The one shape the runner ever made a link's secret in.
const TOKEN_FORMAT = /^[A-Za-z0-9_-]{22}$/;
const QUARANTINE_KINDS = ["cross_owner", "missing_target", "dependent"];
// Step 6's fields, as 1700000700_resume_studio.js made them; down() adds
// them back empty, none of them required.
const DROPPED = [
  { name: "expires_at", type: "text" },
  { name: "is_password", type: "bool" },
  { name: "password_hash", type: "text" },
  { name: "token", type: "text" },
];
const DROPPED_INDEX = "idx_share_links_token";
// What a quarantined entry's payload loses, by collection.
const LINK_PAYLOAD_DROPS = ["token", "password_hash", "expires_at"];
const VIEW_PAYLOAD_DROPS = ["viewer_ip_hash", "user_agent"];
// Step 1's fields that down() removes again.
const ADDED_ONLY_FORWARD = ["legacy_reason", "turned_off_at", "manifest_id"];

// The typed relation this migration adds, in 1700007000's shape
// (test_relation_endpoint_authz.py reads it and relation_endpoints.v1.json).
const FIELDS = [
  { c: "resume_share_links", f: "replaced_by", t: "share_capabilities", required: false, cascade: true },
];

// The day a view keeps, as SQL over `expr`: its first ten characters when
// they are a real calendar day, else nothing.
function DAY(expr) {
  const head = "substr(COALESCE(" + expr + ", ''), 1, 10)";
  return "(CASE WHEN date(" + head + ") IS " + head + " THEN " + head + " ELSE '' END)";
}

// ---------------------------------------------------------------------------
// Decisions, with no PocketBase in them (test_legacy_share_migration.py runs
// them under node)
// ---------------------------------------------------------------------------

function outcome(name, reason) {
  return { outcome: name, reason };
}

// A link's outcome. `row` holds the link's own values and what the
// classifying query found: whether each target, a variant's parent, and the
// owner exist, who owns them, and whether the owner is a demo account.
// Ownership comes first, then the demo account, then everything else.
function classify(row) {
  const named = [];
  if (row.resume !== "") named.push({ found: !!row.resume_found, owner: row.resume_owner });
  if (row.variant !== "") named.push({ found: !!row.variant_found, owner: row.variant_owner });
  for (let i = 0; i < named.length; i += 1) {
    if (named[i].found && named[i].owner !== row.user) return outcome("revoked_ownership", "target_owner");
  }
  if (row.variant !== "" && row.variant_found && row.parent_found && row.parent_owner !== row.user) {
    return outcome("revoked_ownership", "parent_owner");
  }
  if (row.user !== "" && row.owner_found && row.owner_demo) return outcome("revoked_demo", "demo_account");
  if (row.user === "" || !row.owner_found) return outcome("revoked_unverified", "owner_missing");
  if (named.length === 0) return outcome("revoked_unverified", "no_target");
  if (named.some((n) => !n.found) || (row.variant !== "" && !row.parent_found)) {
    return outcome("revoked_unverified", "target_missing");
  }
  if (typeof row.token !== "string" || !TOKEN_FORMAT.test(row.token)) return outcome("revoked_unverified", "token_format");
  if (row.is_password || row.password_hash !== "") return outcome("revoked_unverified", "password_set");
  if (row.expires_at !== "") return outcome("revoked_unverified", "expiry_set");
  return outcome("migrated", "eligible");
}

// A quarantined link's outcome, from its entry's kind.
function classifyQuarantined(kind) {
  return outcome("revoked_ownership", QUARANTINE_KINDS.indexOf(kind) >= 0 ? "quarantined_" + kind : "quarantined_other");
}

// The quarantined links that get a journal row of their own, from
// relation_quarantine's link entries in (source_id, id) order: one per link,
// its first entry, and none for a link back in the live table, whose row
// step 3 wrote. With the live links' own rows, that's one row per link id.
function quarantinedLinks(entries, live) {
  const seen = {};
  const out = [];
  for (let i = 0; i < entries.length; i += 1) {
    const e = entries[i];
    if (seen[e.source_id] || live[e.source_id]) continue;
    seen[e.source_id] = true;
    out.push(e);
  }
  return out;
}

// Folds one view's day into a link's counts.
function countView(counts, day) {
  counts.count += 1;
  if (day !== "") {
    if (counts.first === "" || day < counts.first) counts.first = day;
    if (counts.last === "" || day > counts.last) counts.last = day;
  }
  return counts;
}

function noViews() {
  return { count: 0, first: "", last: "" };
}

// A link's new journal row, from its outcome and its view counts. Its id is
// the link's own: link ids are unique, so the journal's are too, however
// they were chosen.
function journalRow(linkId, origin, entryId, decided, views) {
  return {
    id: linkId,
    manifest: MANIFEST,
    predicate_version: PREDICATE_VERSION,
    link: linkId,
    origin,
    quarantine_entry: entryId || "",
    outcome: decided.outcome,
    reason: decided.reason,
    views: views.count,
    first_view_day: views.first,
    last_view_day: views.last,
    incident: decided.outcome === "revoked_ownership" && views.count > 0,
  };
}

// ---------------------------------------------------------------------------
// The migration
// ---------------------------------------------------------------------------

function logLine(event, fields) {
  console.log(JSON.stringify(Object.assign({ v: "obs/v1", event, service: "pocketbase" }, fields || {})));
}

migrate(
  (db) => {
    let step = "lookup";
    try {
      const dao = new Dao(db);
      const find = (name) => {
        try {
          return dao.findCollectionByNameOrId(name);
        } catch (_) {
          throw new Error("legacy_share_migration: collection " + name + " is missing");
        }
      };
      const links = find(LINKS);
      const views = find(VIEWS);
      const capabilities = find("share_capabilities");
      find(QUARANTINE);
      // PocketBase's datetime text: the journal's rows and the date a link
      // was turned off.
      const now = new Date().toISOString().replace("T", " ");

      // --- 1. Fields, the journal, and the replaced_by triggers -----------
      step = "schema";
      const has = (collection, name) => !!collection.schema.getFieldByName(name);
      const text = (name, pattern) => ({ name, type: "text", required: false, options: { min: null, max: null, pattern } });
      const count = (name) => ({ name, type: "number", required: false, options: { min: 0, max: null, noDecimal: true } });
      const addMissing = (collection, spec) => {
        if (!has(collection, spec.name)) collection.schema.addField(new SchemaField(spec));
      };
      for (let i = 0; i < DROPPED.length; i += 1) {
        if (!has(links, DROPPED[i].name)) {
          throw new Error("legacy_share_migration: " + LINKS + "." + DROPPED[i].name + " is missing");
        }
      }
      addMissing(links, text("legacy_status", "^(" + OUTCOMES.join("|") + ")$"));
      addMissing(links, text("legacy_reason", "^[a-z_]{1,40}$"));
      addMissing(links, { name: "turned_off_at", type: "date", required: false, options: { min: "", max: "" } });
      addMissing(links, text("manifest_id", "^" + MANIFEST + "$"));
      addMissing(links, {
        name: "replaced_by",
        type: "relation",
        required: false,
        options: { collectionId: capabilities.id, cascadeDelete: true, minSelect: null, maxSelect: 1, displayFields: null },
      });

      // --- 2. Rules -----------------------------------------------------------
      step = "rules";
      links.listRule = 'legacy_status != "revoked_ownership" && user = @request.auth.id';
      links.viewRule = 'legacy_status != "revoked_ownership" && user = @request.auth.id';
      links.createRule = null;
      links.updateRule = null;
      links.deleteRule = null;
      dao.saveCollection(links);
      views.listRule = 'link.legacy_status != "revoked_ownership" && user = @request.auth.id';
      views.viewRule = 'link.legacy_status != "revoked_ownership" && user = @request.auth.id';
      views.createRule = null;
      views.updateRule = null;
      views.deleteRule = null;
      dao.saveCollection(views);

      step = "journal";
      let journal = null;
      try {
        journal = dao.findCollectionByNameOrId(JOURNAL);
      } catch (_) {
        journal = null;
      }
      if (journal === null) {
        dao.saveCollection(new Collection({
          name: JOURNAL,
          type: "base",
          listRule: null,
          viewRule: null,
          createRule: null,
          updateRule: null,
          deleteRule: null,
          schema: [
            text("manifest", "^" + MANIFEST + "$"),
            count("predicate_version"),
            text("link", "^[a-z0-9]{15}$"),
            text("origin", "^(live|quarantine)$"),
            text("quarantine_entry", "^[a-z0-9]{15}$"),
            text("outcome", "^(" + OUTCOMES.join("|") + ")$"),
            text("reason", "^[a-z_]{1,40}$"),
            count("views"),
            text("first_view_day", "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"),
            text("last_view_day", "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"),
            { name: "incident", type: "bool", required: false },
          ],
          indexes: ["CREATE UNIQUE INDEX idx_legacy_share_migration_link ON " + JOURNAL + " (manifest, link)"],
        }));
      }

      // Owner equality for each relation in FIELDS, as 1700007000 writes it:
      // a link may name only a capability of its own account.
      step = "triggers";
      for (let i = 0; i < FIELDS.length; i += 1) {
        const r = FIELDS[i];
        const base = "rel_authz_" + r.c + "_" + r.f;
        const mismatch =
          'NEW."' + r.f + '" IS NOT NULL AND NEW."' + r.f + "\" != '' AND NOT EXISTS " +
          '(SELECT 1 FROM "' + r.t + '" tgt WHERE tgt."id" = NEW."' + r.f + '" AND tgt."' + OWNER + '" = NEW."' + OWNER + '")';
        // PocketBase's save rewrites every column, so UPDATE OF fires on any
        // save; check the relation only when it, or the row's owner, changed.
        const changed =
          '(NEW."' + r.f + '" IS NOT OLD."' + r.f + '" OR NEW."' + OWNER + '" IS NOT OLD."' + OWNER + '")';
        db.newQuery('DROP TRIGGER IF EXISTS "' + base + '_ins"').execute();
        db.newQuery('DROP TRIGGER IF EXISTS "' + base + '_upd"').execute();
        db.newQuery('DROP TRIGGER IF EXISTS "' + base + '_tgt"').execute();
        db.newQuery(
          'CREATE TRIGGER "' + base + '_ins" BEFORE INSERT ON "' + r.c + '" FOR EACH ROW WHEN ' +
          mismatch + " BEGIN SELECT RAISE(ABORT, 'relation endpoint denied'); END",
        ).execute();
        db.newQuery(
          'CREATE TRIGGER "' + base + '_upd" BEFORE UPDATE OF "' + r.f + '", "' + OWNER + '" ON "' + r.c +
          '" FOR EACH ROW WHEN ' + changed + " AND " + mismatch +
          " BEGIN SELECT RAISE(ABORT, 'relation endpoint denied'); END",
        ).execute();
        db.newQuery(
          'CREATE TRIGGER "' + base + '_tgt" BEFORE UPDATE OF "' + OWNER + '" ON "' + r.t +
          '" FOR EACH ROW WHEN NEW."' + OWNER + '" != OLD."' + OWNER + '" AND EXISTS ' +
          '(SELECT 1 FROM "' + r.c + '" src WHERE src."' + r.f + '" = OLD."id" AND src."' + OWNER + '" != NEW."' + OWNER + '") ' +
          "BEGIN SELECT RAISE(ABORT, 'relation endpoint denied'); END",
        ).execute();
      }

      const JOURNAL_COLUMNS = "id, manifest, predicate_version, link, origin, quarantine_entry, outcome, reason, views, " +
        "first_view_day, last_view_day, incident, created";
      const journalModel = () => new DynamicModel({
        id: "", manifest: "", predicate_version: 0, link: "", origin: "", quarantine_entry: "", outcome: "",
        reason: "", views: 0, first_view_day: "", last_view_day: "", incident: false, created: "",
      });
      const insertJournal = (row) => {
        db.newQuery(
          "INSERT INTO " + JOURNAL + " (id, created, updated, manifest, predicate_version, link, origin, " +
          "quarantine_entry, outcome, reason, views, first_view_day, last_view_day, incident) VALUES " +
          "({:id}, {:now}, {:now}, {:manifest}, {:pv}, {:link}, {:origin}, {:entry}, {:outcome}, {:reason}, " +
          "{:views}, {:first}, {:last}, {:incident})",
        ).bind({
          id: row.id, now, manifest: row.manifest, pv: row.predicate_version, link: row.link, origin: row.origin,
          entry: row.quarantine_entry, outcome: row.outcome, reason: row.reason, views: row.views,
          first: row.first_view_day, last: row.last_view_day, incident: row.incident,
        }).execute();
      };
      const counts = { links: 0, quarantined: 0, journaled: 0, reused: 0, incidents: 0, view_rows_stripped: 0,
        entries_stripped: 0 };
      OUTCOMES.forEach((name) => {
        counts[name] = 0;
      });
      const tally = (row, reused) => {
        counts[row.outcome] += 1;
        if (row.incident) counts.incidents += 1;
        if (reused) counts.reused += 1;
        else counts.journaled += 1;
      };

      // --- 3. Live links, BATCH at a time in id order ---------------------
      step = "classify";
      const live = {};
      let after = "";
      let batch = 0;
      for (;;) {
        const rows = arrayOf(new DynamicModel({
          id: "", user: "", resume: "", variant: "", token: "", is_password: 0, password_hash: "", expires_at: "",
          owner_found: 0, owner_demo: 0, resume_found: 0, resume_owner: "", variant_found: 0, variant_owner: "",
          parent_found: 0, parent_owner: "",
        }));
        db.newQuery(
          "SELECT l.id AS id, l.user AS user, l.resume AS resume, l.variant AS variant, l.token AS token, " +
          "(CASE WHEN l.is_password THEN 1 ELSE 0 END) AS is_password, l.password_hash AS password_hash, " +
          "l.expires_at AS expires_at, " +
          "(CASE WHEN u.id IS NULL THEN 0 ELSE 1 END) AS owner_found, " +
          "(CASE WHEN u.is_demo THEN 1 ELSE 0 END) AS owner_demo, " +
          "(CASE WHEN r.id IS NULL THEN 0 ELSE 1 END) AS resume_found, COALESCE(r.user, '') AS resume_owner, " +
          "(CASE WHEN v.id IS NULL THEN 0 ELSE 1 END) AS variant_found, COALESCE(v.user, '') AS variant_owner, " +
          "(CASE WHEN p.id IS NULL THEN 0 ELSE 1 END) AS parent_found, COALESCE(p.user, '') AS parent_owner " +
          "FROM " + LINKS + " l " +
          "LEFT JOIN users u ON u.id = l.user " +
          "LEFT JOIN resumes r ON l.resume != '' AND r.id = l.resume " +
          "LEFT JOIN resume_variants v ON l.variant != '' AND v.id = l.variant " +
          "LEFT JOIN resumes p ON v.id IS NOT NULL AND p.id = v.resume " +
          "WHERE l.id > {:after} ORDER BY l.id LIMIT " + BATCH,
        ).bind({ after }).all(rows);
        if (rows.length === 0) break;
        batch += 1;
        const last = rows[rows.length - 1].id;

        const kept = {};
        const keptRows = arrayOf(journalModel());
        db.newQuery(
          "SELECT " + JOURNAL_COLUMNS + " FROM " + JOURNAL + " WHERE manifest = {:m} AND link > {:after} AND link <= {:last}",
        ).bind({ m: MANIFEST, after, last }).all(keptRows);
        keptRows.forEach((r) => {
          kept[r.link] = r;
        });

        const viewed = {};
        const viewRows = arrayOf(new DynamicModel({ link: "", day: "" }));
        db.newQuery("SELECT link AS link, " + DAY("viewed_at") + " AS day FROM " + VIEWS + " WHERE link > {:after} AND link <= {:last}")
          .bind({ after, last }).all(viewRows);
        viewRows.forEach((v) => {
          viewed[v.link] = countView(viewed[v.link] || noViews(), v.day);
        });

        // The batch's journal rows first, then its links.
        let journaled = 0;
        const decided = rows.map((row) => {
          live[row.id] = true;
          counts.links += 1;
          const reuse = kept[row.id];
          if (reuse) {
            tally(reuse, true);
            return { outcome: reuse.outcome, reason: reuse.reason, at: reuse.created, link: row.id };
          }
          const entry = journalRow(row.id, "live", "", classify(row), viewed[row.id] || noViews());
          insertJournal(entry);
          tally(entry, false);
          journaled += 1;
          return { outcome: entry.outcome, reason: entry.reason, at: now, link: row.id };
        });
        logLine("legacy_share_batch", { batch, links: rows.length, journaled });

        for (let i = 0; i < decided.length; i += 1) {
          const d = decided[i];
          db.newQuery(
            "UPDATE " + LINKS + " SET legacy_status = {:status}, legacy_reason = {:reason}, turned_off_at = {:at}, " +
            "manifest_id = {:m} WHERE id = {:id}",
          ).bind({ status: d.outcome, reason: d.reason, at: d.at, m: MANIFEST, id: d.link }).execute();
        }
        after = last;
      }

      // --- 4. Every view row keeps only its day ---------------------------
      step = "views";
      const viewChange = "viewer_ip_hash != '' OR user_agent != '' OR viewed_at IS NOT " + DAY("viewed_at");
      const changedViews = new DynamicModel({ n: 0 });
      db.newQuery("SELECT COUNT(*) AS n FROM " + VIEWS + " WHERE " + viewChange).one(changedViews);
      counts.view_rows_stripped = changedViews.n;
      db.newQuery("UPDATE " + VIEWS + " SET viewer_ip_hash = '', user_agent = '', viewed_at = " + DAY("viewed_at") +
        " WHERE " + viewChange).execute();

      // --- 5. relation_quarantine's share entries -------------------------
      step = "quarantine";
      const notObjects = new DynamicModel({ n: 0 });
      db.newQuery(
        "SELECT COUNT(*) AS n FROM " + QUARANTINE + " WHERE source_collection IN ({:links}, {:views}) AND " +
        "(payload IS NULL OR json_valid(payload) = 0 OR json_type(payload) != 'object')",
      ).bind({ links: LINKS, views: VIEWS }).one(notObjects);
      if (notObjects.n > 0) {
        throw new Error("legacy_share_migration: a quarantined share entry's payload isn't a JSON object");
      }

      const path = (key) => "'$.\"" + key + "\"'";
      const viewedAt = "json_extract(payload, " + path("viewed_at") + ")";
      const quarantinedViews = {};
      const entryViews = arrayOf(new DynamicModel({ link: "", day: "" }));
      db.newQuery(
        "SELECT COALESCE(json_extract(payload, " + path("link") + "), '') AS link, " + DAY(viewedAt) + " AS day FROM " +
        QUARANTINE + " WHERE source_collection = {:views}",
      ).bind({ views: VIEWS }).all(entryViews);
      entryViews.forEach((v) => {
        quarantinedViews[v.link] = countView(quarantinedViews[v.link] || noViews(), v.day);
      });

      const holds = (keys) => keys.map((k) => "json_type(payload, " + path(k) + ") IS NOT NULL").join(" OR ");
      const entryChange = "(source_collection = {:links} AND (" + holds(LINK_PAYLOAD_DROPS) + ")) OR " +
        "(source_collection = {:views} AND (" + holds(VIEW_PAYLOAD_DROPS) + " OR COALESCE(" + viewedAt + ", '') IS NOT " +
        DAY(viewedAt) + "))";
      const changedEntries = new DynamicModel({ n: 0 });
      db.newQuery("SELECT COUNT(*) AS n FROM " + QUARANTINE + " WHERE " + entryChange)
        .bind({ links: LINKS, views: VIEWS }).one(changedEntries);
      counts.entries_stripped = changedEntries.n;
      db.newQuery(
        "UPDATE " + QUARANTINE + " SET payload = json_remove(payload, " + LINK_PAYLOAD_DROPS.map(path).join(", ") + ") " +
        "WHERE source_collection = {:links}",
      ).bind({ links: LINKS }).execute();
      db.newQuery(
        "UPDATE " + QUARANTINE + " SET payload = json_set(json_remove(payload, " + VIEW_PAYLOAD_DROPS.map(path).join(", ") +
        "), " + path("viewed_at") + ", " + DAY(viewedAt) + ") WHERE source_collection = {:views}",
      ).bind({ views: VIEWS }).execute();

      // One journal row per quarantined link, unless it's back in the live
      // table (journaled above) or a run before this one journaled it.
      const entries = arrayOf(new DynamicModel({ id: "", source_id: "", kind: "" }));
      db.newQuery("SELECT id, source_id, kind FROM " + QUARANTINE + " WHERE source_collection = {:links} ORDER BY source_id, id")
        .bind({ links: LINKS }).all(entries);
      const held = quarantinedLinks(entries, live);
      for (let i = 0; i < held.length; i += 1) {
        const e = held[i];
        counts.quarantined += 1;
        const prior = arrayOf(journalModel());
        db.newQuery("SELECT " + JOURNAL_COLUMNS + " FROM " + JOURNAL + " WHERE manifest = {:m} AND link = {:link}")
          .bind({ m: MANIFEST, link: e.source_id }).all(prior);
        if (prior.length > 0) {
          tally(prior[0], true);
          continue;
        }
        const entry = journalRow(e.source_id, "quarantine", e.id, classifyQuarantined(e.kind),
          quarantinedViews[e.source_id] || noViews());
        insertJournal(entry);
        tally(entry, false);
      }

      // --- 6. The fields only earlier links used --------------------------
      step = "drop";
      const fresh = find(LINKS);
      fresh.indexes = fresh.indexes.filter((idx) => idx.indexOf(DROPPED_INDEX) < 0);
      for (let i = 0; i < DROPPED.length; i += 1) {
        fresh.schema.removeField(fresh.schema.getFieldByName(DROPPED[i].name).id);
      }
      dao.saveCollection(fresh);

      logLine("legacy_share_migrated", Object.assign({ batches: batch }, counts));
    } catch (err) {
      logLine("legacy_share_failed", { step });
      throw err;
    }
  },
  (db) => {
    const dao = new Dao(db);
    const links = dao.findCollectionByNameOrId(LINKS);
    for (let i = 0; i < ADDED_ONLY_FORWARD.length; i += 1) {
      const field = links.schema.getFieldByName(ADDED_ONLY_FORWARD[i]);
      if (field) links.schema.removeField(field.id);
    }
    for (let i = 0; i < DROPPED.length; i += 1) {
      if (!links.schema.getFieldByName(DROPPED[i].name)) {
        links.schema.addField(new SchemaField({ name: DROPPED[i].name, type: DROPPED[i].type, required: false }));
      }
    }
    dao.saveCollection(links);
    logLine("legacy_share_reversed", {});
  },
);

// For the node tests; PocketBase never defines `module` in a migration.
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    MANIFEST,
    PREDICATE_VERSION,
    BATCH,
    OUTCOMES,
    REASONS,
    DROPPED,
    DROPPED_INDEX,
    LINK_PAYLOAD_DROPS,
    VIEW_PAYLOAD_DROPS,
    FIELDS,
    DAY,
    classify,
    classifyQuarantined,
    quarantinedLinks,
    journalRow,
    countView,
    noViews,
  };
}
