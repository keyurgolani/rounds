/// <reference path="../pb_data/types.d.ts" />

// The older share links' receipt (ROUNDS-00B-L06 stage 1).
//
//   pocketbase legacy-share-receipt [--out PATH] [--scan] [--commit SHA]
//
// Reports what 1700008400_legacy_share_migration.js wrote: the journal of
// manifest legacy-shares-v1 and what the share collections and
// relation_quarantine hold now. It prints the receipt and its checksum, and
// with --out writes it to a new file, mode 0600, outside pb_data (the path
// rule of #4's scan). The runner signs it:
//
//   python -m app.legacy_receipt sign RECEIPT
//
// under HKDF-SHA256(AI_KEY_SECRET, "rounds/legacy-share-receipt/v1"), the key
// ROUNDS-00B-L04 reserved for it (backend/app/share_secrets.py).
//
// The receipt holds counts and checksums only: links by origin, outcomes and
// reasons, incidents, links given a new link, view counts, what is left of an
// old link's secret or its viewers' details (all zero after the migration),
// the journal's row count and checksum, and whether it all reconciles. No
// id, secret, address, or content. It has no clock, so the same journal gives
// the same receipt: the dry run's on a stopped copy and the deployment's after
// the upgrade compare by their journal checksum and counts.
//
// --scan adds how many older links can't get a new link yet: #4's scan core
// (legacy_snapshots.js scan()) over each migrated link that has no new link,
// one decision per link. Like #4's scan, it needs the materializer.
//
// receipt() is pure, so test_legacy_share_receipt.py runs it under node.

const SCHEMA = "legacy-share-receipt/v1";
const MANIFEST = "legacy-shares-v1";
const PREDICATE_VERSION = 1;
const LINKS = "resume_share_links";
const VIEWS = "resume_share_views";
const JOURNAL = "legacy_share_migration";
const QUARANTINE = "relation_quarantine";
const OUTCOMES = ["migrated", "revoked_ownership", "revoked_demo", "revoked_unverified"];
// The migration's reason codes, by outcome (the tests check they match it
// and the manifest).
const REASONS = {
  migrated: ["eligible"],
  revoked_ownership: ["target_owner", "parent_owner", "quarantined_cross_owner", "quarantined_missing_target",
    "quarantined_dependent", "quarantined_other"],
  revoked_demo: ["demo_account"],
  revoked_unverified: ["owner_missing", "no_target", "target_missing", "token_format", "password_set", "expiry_set"],
};
// What the migration removes, which the receipt counts as left over.
const DROPPED = ["expires_at", "is_password", "password_hash", "token"];
const LINK_PAYLOAD_DROPS = ["token", "password_hash", "expires_at"];
const VIEW_PAYLOAD_DROPS = ["viewer_ip_hash", "user_agent"];
// The journal's fields its checksum covers, in this order; never its dates.
const JOURNAL_FIELDS = ["id", "manifest", "predicate_version", "link", "origin", "quarantine_entry", "outcome", "reason",
  "views", "first_view_day", "last_view_day", "incident"];

function zero(names) {
  const out = {};
  names.forEach((name) => {
    out[name] = 0;
  });
  return out;
}

function allReasons() {
  return OUTCOMES.reduce((list, outcome) => list.concat(REASONS[outcome]), []).sort();
}

// The receipt from what the store read. input:
//   journal       the journal's rows for MANIFEST, JOURNAL_FIELDS each
//   links         the links now in resume_share_links: { id, status, replaced }
//   linkColumns   resume_share_links's field names now
//   linkEntries   relation_quarantine's link entries: { link, secret_keys }
//   viewRows      { rows, detailed }: view rows, and those holding more than a day
//   viewEntries   { entries, detailed }: the same for quarantined view entries
//   commit        the commit the operator names, or ""
//   unavailable   --scan's counts, or null
// canonical and sha256 are #4's (legacy_snapshots.js), so Python verifies the
// checksum the way it verifies #4's report.
function receipt(input, canonical, sha256) {
  const journal = input.journal.slice().sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  const outcomes = zero(OUTCOMES);
  const reasons = zero(allReasons());
  const origins = { live: 0, quarantine: 0 };
  let incidents = 0;
  let views = 0;
  let unknown = 0;
  const byLink = {};
  journal.forEach((row) => {
    if (Object.prototype.hasOwnProperty.call(outcomes, row.outcome)) outcomes[row.outcome] += 1;
    else unknown += 1;
    if (Object.prototype.hasOwnProperty.call(reasons, row.reason)) reasons[row.reason] += 1;
    else unknown += 1;
    if (Object.prototype.hasOwnProperty.call(origins, row.origin)) origins[row.origin] += 1;
    else unknown += 1;
    if (row.incident) incidents += 1;
    views += row.views;
    byLink[row.link] = row;
  });
  const rows = journal.map((row) => {
    const out = {};
    JOURNAL_FIELDS.forEach((key) => {
      out[key] = row[key];
    });
    return out;
  });

  // Every link now in the table is in the journal with the same status, and
  // every quarantined link is too.
  let unjournaled = 0;
  let mismatched = 0;
  let reissued = 0;
  input.links.forEach((link) => {
    const row = byLink[link.id];
    if (!row) unjournaled += 1;
    else if (row.outcome !== link.status) mismatched += 1;
    if (link.replaced) reissued += 1;
  });
  input.linkEntries.forEach((entry) => {
    if (!byLink[entry.link]) unjournaled += 1;
  });

  const left = {
    link_fields: input.linkColumns.filter((name) => DROPPED.indexOf(name) >= 0).length,
    quarantined_link_secrets: input.linkEntries.reduce((n, e) => n + e.secret_keys, 0),
    view_details: input.viewRows.detailed,
    quarantined_view_details: input.viewEntries.detailed,
  };
  const leftover = Object.keys(left).reduce((n, key) => n + left[key], 0);
  const sum = OUTCOMES.reduce((n, outcome) => n + outcomes[outcome], 0);

  const out = {
    schema: SCHEMA,
    manifest: MANIFEST,
    predicate_version: PREDICATE_VERSION,
    commit: typeof input.commit === "string" && input.commit !== "" ? input.commit : "unknown",
    links: { journaled: journal.length, live: origins.live, quarantined: origins.quarantine, now: input.links.length },
    outcomes,
    reasons,
    incidents,
    reissued,
    views: { counted: views, rows_now: input.viewRows.rows, quarantined_entries: input.viewEntries.entries },
    left,
    journal: { rows: journal.length, checksum: "sha256:" + sha256(canonical(rows)) },
    reconciled: unknown === 0 && sum === journal.length && unjournaled === 0 && mismatched === 0 && leftover === 0,
    unavailable: input.unavailable,
  };
  out.checksum = "sha256:" + sha256(canonical(out));
  return out;
}

// --scan's counts from #4's scan report over one source per link.
function unavailableOf(report) {
  return {
    checked: report.totals.sources,
    ineligible: report.totals.ineligible,
    unreachable: report.totals.unavailable,
    by_reason: report.by_reason,
    materializer_digest: report.materializer_digest,
    complete: report.complete,
  };
}

// ---------------------------------------------------------------------------
// PocketBase
// ---------------------------------------------------------------------------

function read(dao) {
  const db = dao.db();
  const q = (sql) => db.newQuery(sql);
  const journal = arrayOf(new DynamicModel({
    id: "", manifest: "", predicate_version: 0, link: "", origin: "", quarantine_entry: "", outcome: "", reason: "",
    views: 0, first_view_day: "", last_view_day: "", incident: false,
  }));
  q("SELECT " + JOURNAL_FIELDS.join(", ") + " FROM " + JOURNAL + " WHERE manifest = {:m} ORDER BY id")
    .bind({ m: MANIFEST }).all(journal);
  const links = arrayOf(new DynamicModel({ id: "", status: "", replaced: 0 }));
  q("SELECT id, legacy_status AS status, (CASE WHEN replaced_by != '' THEN 1 ELSE 0 END) AS replaced FROM " + LINKS)
    .all(links);
  const columns = dao.findCollectionByNameOrId(LINKS).schema.fields().map((f) => f.name);
  const path = (key) => "'$.\"" + key + "\"'";
  const entries = arrayOf(new DynamicModel({ link: "", secret_keys: 0 }));
  q(
    "SELECT source_id AS link, (" + LINK_PAYLOAD_DROPS.map((k) => "(json_type(payload, " + path(k) + ") IS NOT NULL)")
      .join(" + ") + ") AS secret_keys FROM " + QUARANTINE + " WHERE source_collection = {:links}",
  ).bind({ links: LINKS }).all(entries);
  const day = (expr) => {
    const head = "substr(COALESCE(" + expr + ", ''), 1, 10)";
    return "(CASE WHEN date(" + head + ") IS " + head + " THEN " + head + " ELSE '' END)";
  };
  const viewRows = new DynamicModel({ rows: 0, detailed: 0 });
  q(
    "SELECT COUNT(*) AS rows, COALESCE(SUM(CASE WHEN viewer_ip_hash != '' OR user_agent != '' OR viewed_at IS NOT " +
      day("viewed_at") + " THEN 1 ELSE 0 END), 0) AS detailed FROM " + VIEWS,
  ).one(viewRows);
  const viewedAt = "json_extract(payload, " + path("viewed_at") + ")";
  const viewEntries = new DynamicModel({ entries: 0, detailed: 0 });
  q(
    "SELECT COUNT(*) AS entries, COALESCE(SUM(CASE WHEN " +
      VIEW_PAYLOAD_DROPS.map((k) => "json_type(payload, " + path(k) + ") IS NOT NULL").join(" OR ") +
      " OR COALESCE(" + viewedAt + ", '') IS NOT " + day(viewedAt) + " THEN 1 ELSE 0 END), 0) AS detailed FROM " +
      QUARANTINE + " WHERE source_collection = {:views}",
  ).bind({ views: VIEWS }).one(viewEntries);
  return {
    journal: journal.map((r) => ({
      id: r.id, manifest: r.manifest, predicate_version: r.predicate_version, link: r.link, origin: r.origin,
      quarantine_entry: r.quarantine_entry, outcome: r.outcome, reason: r.reason, views: r.views,
      first_view_day: r.first_view_day, last_view_day: r.last_view_day, incident: !!r.incident,
    })),
    links: links.map((r) => ({ id: r.id, status: r.status, replaced: r.replaced === 1 })),
    linkColumns: columns,
    linkEntries: entries.map((r) => ({ link: r.link, secret_keys: r.secret_keys })),
    viewRows: { rows: viewRows.rows, detailed: viewRows.detailed },
    viewEntries: { entries: viewEntries.entries, detailed: viewEntries.detailed },
  };
}

// The sources --scan checks: each migrated link with no new link, by its
// own target (its variant if it names one, else its resume), once per link.
function scanTargets(dao) {
  const rows = arrayOf(new DynamicModel({ resume: "", variant: "" }));
  dao.db().newQuery(
    "SELECT resume, variant FROM " + LINKS + " WHERE legacy_status = 'migrated' AND replaced_by = '' ORDER BY id",
  ).all(rows);
  const wanted = {};
  rows.forEach((r) => {
    const key = r.variant !== "" ? "variant:" + r.variant : "resume:" + r.resume;
    wanted[key] = (wanted[key] || 0) + 1;
  });
  return wanted;
}

function scanUnavailable(dao, commit) {
  const snapshots = require(`${__hooks}/legacy_snapshots.js`);
  const base = snapshots.pbStore(dao);
  const wanted = scanTargets(dao);
  const store = {
    eachSource: (fn) => base.eachSource((source) => {
      const times = wanted[source.kind + ":" + source.id] || 0;
      for (let i = 0; i < times; i += 1) fn(source);
    }),
    findResume: base.findResume,
    isDemo: base.isDemo,
  };
  const report = snapshots.scan({
    store,
    materialize: snapshots.materializeOver(snapshots.materializerUrl()),
    sha256: (text) => $security.sha256(text),
    commit,
  });
  return unavailableOf(report);
}

// pocketbase legacy-share-receipt [--out PATH] [--scan] [--commit SHA]
function receiptCommand(args) {
  const snapshots = require(`${__hooks}/legacy_snapshots.js`);
  let out = "";
  let scan = false;
  let commit = $os.getenv("ROUNDS_COMMIT") || "";
  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === "--out" && i + 1 < args.length) out = args[++i];
    else if (arg.indexOf("--out=") === 0) out = arg.slice(6);
    else if (arg === "--scan") scan = true;
    else if (arg === "--commit" && i + 1 < args.length) commit = args[++i];
    else if (arg.indexOf("--commit=") === 0) commit = arg.slice(9);
    // PocketBase's own flags (--dir and the rest) are read before this runs.
  }
  if (commit !== "" && !/^[0-9A-Za-z._-]{1,64}$/.test(commit)) {
    throw new Error("legacy-share-receipt: --commit takes a commit or tag name");
  }
  if (out !== "") {
    let cwd = "/";
    try {
      cwd = $os.getwd();
    } catch (err) {
      cwd = "/";
    }
    const refused = snapshots.reportPathError(out, $app.dataDir(), cwd);
    if (refused !== null) throw new Error("legacy-share-receipt: " + refused.replace("the report", "the receipt"));
    let exists = true;
    try {
      $os.readFile(out);
    } catch (err) {
      exists = false;
    }
    if (exists) throw new Error("legacy-share-receipt: --out names a file that exists; give a new path");
  }
  const dao = $app.dao();
  try {
    dao.findCollectionByNameOrId(JOURNAL);
  } catch (err) {
    throw new Error("legacy-share-receipt: there is no journal; start PocketBase on this release first");
  }
  const input = read(dao);
  input.commit = commit;
  input.unavailable = scan ? scanUnavailable(dao, commit) : null;
  const made = receipt(input, snapshots.canonical, (text) => $security.sha256(text));
  const text = JSON.stringify(made, null, 2) + "\n";
  if (out !== "") $os.writeFile(out, text, 0o600);
  else console.log(text);
  console.log(JSON.stringify({
    v: "obs/v1",
    event: "legacy_share_receipt",
    service: "pocketbase",
    reconciled: made.reconciled,
    outcomes: made.outcomes,
    incidents: made.incidents,
    reissued: made.reissued,
    journal: made.journal,
    checksum: made.checksum,
  }));
}

module.exports = {
  SCHEMA,
  MANIFEST,
  PREDICATE_VERSION,
  OUTCOMES,
  REASONS,
  DROPPED,
  LINK_PAYLOAD_DROPS,
  VIEW_PAYLOAD_DROPS,
  JOURNAL_FIELDS,
  receipt,
  unavailableOf,
  receiptCommand,
};
