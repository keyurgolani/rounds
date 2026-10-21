"""Static and contract checks on the relation-endpoint migration (ROUNDS-00B-L02).

These assert, without a running PocketBase, that the four places that list the
typed relations never drift:

  * the canonical table ``pocketbase/pb_hooks/relation_endpoints.v1.json``;
  * the ``FIELDS`` array in
    ``pocketbase/pb_migrations/1700007000_relation_endpoint_authz.js`` that the
    triggers and the quarantine scan iterate;
  * the per-collection ``relation_endpoints`` in
    ``docs/security/account-scope.v1.json`` that the harness points its probes
    at; and
  * the touched-row manifest
    ``pocketbase/migration-manifests/1700007000_relation_endpoint_authz.json``
    that gives each field's quarantine disposition.

They also pin the migration's forward-only ``down`` (every trigger stays, no
quarantined row is reinstated) and the dry-run guards, and check that every
collection whose policy row lists a relation family declares a non-empty
``relation_endpoints`` so no probe passes vacuously.

The behavioural side runs the pinned PocketBase in the harness: the dry run
leaving the database untouched and predicting the apply, the apply moving,
clearing, and journalling rows on a legacy fixture, and deletes that clear one
relation of a row lives in ``harness/probes/relation_quarantine_check.py``
(harness phase 13); a trigger aborting a direct cross-owner write lives in
``harness/probes/scan_check.py``.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1].parent
MIGRATION = ROOT / "pocketbase" / "pb_migrations" / "1700007000_relation_endpoint_authz.js"
TABLE = ROOT / "pocketbase" / "pb_hooks" / "relation_endpoints.v1.json"
POLICY = ROOT / "docs" / "security" / "account-scope.v1.json"
TOUCHED = ROOT / "pocketbase" / "migration-manifests" / "1700007000_relation_endpoint_authz.json"

RELATION_FAMILIES = {
    "account-scope.create.relation-foreign.denied",
    "account-scope.create.relation-foreign-or-missing.indistinguishable",
    "account-scope.create.relation-superuser.denied",
    "account-scope.update.relation-foreign.denied",
    "account-scope.update.relation-foreign-or-missing.indistinguishable",
}

# Relation fields that point at shared, cross-account content (a shared round or
# take-home assignment), not at an owned target, so they are deliberately out of
# the owner-equality endpoint table even though they are relation_exceptions.
SHARED_CONTENT_FIELDS = {
    ("ai_coding_drafts", "round"),
    ("ai_coding_attempts", "round"),
    ("take_home_drafts", "assignment"),
    ("take_home_attempts", "assignment"),
}


# Relations no client sets at all: pb_hooks/execution.pb.js refuses any client
# create or update that sets or changes one, and only the server writes them,
# for the row's own account (ROUNDS-00A-L03). They need no owner-equality
# endpoint, and the cross-owner scan still checks them.
SERVER_SET_FIELDS = {
    ("ai_coding_attempts", "envelope"),
    ("take_home_attempts", "envelope"),
}


@pytest.fixture(scope="module")
def src() -> str:
    return MIGRATION.read_text()


@pytest.fixture(scope="module")
def table() -> dict:
    return json.loads(TABLE.read_text())


@pytest.fixture(scope="module")
def policy() -> dict:
    return json.loads(POLICY.read_text())


def _migration_fields(src: str) -> list[tuple[str, str, str]]:
    m = re.search(r"const FIELDS = \[(.*?)\];", src, re.DOTALL)
    assert m, "could not find the FIELDS array in the migration"
    rows = []
    for line in re.finditer(
        r'\{\s*c:\s*"([^"]+)",\s*f:\s*"([^"]+)",\s*t:\s*"([^"]+)"', m.group(1)
    ):
        rows.append((line.group(1), line.group(2), line.group(3)))
    return rows


def _table_triples(table: dict) -> list[tuple[str, str, str]]:
    return [(r["collection"], r["field"], r["target"]) for r in table["fields"]]


def test_migration_file_is_present(src):
    assert "relation_endpoint_authz" in src
    assert src.lstrip().startswith("/// <reference")


def test_migration_fields_match_the_canonical_table(src, table):
    assert sorted(_migration_fields(src)) == sorted(_table_triples(table))
    # 34 typed relations across the source collections, no duplicate row.
    triples = _migration_fields(src)
    assert len(triples) == 34 and len(set(triples)) == 34


def test_policy_relation_endpoints_match_the_table(policy, table):
    want: dict[str, set[tuple[str, str]]] = {}
    for c, f, t in _table_triples(table):
        want.setdefault(c, set()).add((f, t))
    got: dict[str, set[tuple[str, str]]] = {}
    for name, row in policy["collections"].items():
        if "relation_endpoints" in row:
            got[name] = {(e["field"], e["target"]) for e in row["relation_endpoints"]}
    assert got == want


def test_endpoints_are_relation_exceptions_minus_shared_content(policy):
    # Every endpoint field is a relation_exception; the only exceptions that are
    # not endpoints are the shared-content relations, which are owner-agnostic.
    for name, row in policy["collections"].items():
        rex = set(row.get("relation_exceptions", []))
        rep = {e["field"] for e in row.get("relation_endpoints", [])}
        assert rep <= rex, (name, sorted(rep - rex))
        shared = {f for (c, f) in SHARED_CONTENT_FIELDS if c == name}
        server_set = {f for (c, f) in SERVER_SET_FIELDS if c == name}
        assert rex - rep == shared | server_set, (name, sorted(rex - rep), sorted(shared | server_set))


def test_server_set_relations_are_refused_from_every_client():
    hooks = (ROOT / "pocketbase" / "pb_hooks" / "execution.pb.js").read_text()
    collections = sorted({c for c, _f in SERVER_SET_FIELDS})
    listed = '"' + '", "'.join(collections) + '"'
    for guard in ("guardEnvelopeCreate", "guardEnvelopeUpdate"):
        assert re.search(r"\.%s\(e\);\s*\},\s*%s\);" % (guard, re.escape(listed)), hooks), guard
    assert {f for _c, f in SERVER_SET_FIELDS} == {"envelope"}


def test_every_relation_family_collection_has_endpoints(policy):
    for name, row in policy["collections"].items():
        if RELATION_FAMILIES & set(row["probes"]):
            eps = row.get("relation_endpoints")
            assert eps, f"{name} lists a relation family but declares no relation_endpoints"


def test_resume_share_views_only_lists_the_superuser_relation_family(policy):
    # Its client create and update are null-rule (server-only), so only the
    # superuser relation create is exercised there.
    probes = set(policy["collections"]["resume_share_views"]["probes"])
    assert RELATION_FAMILIES & probes == {"account-scope.create.relation-superuser.denied"}


def test_deny_contract_has_the_relation_keys(policy):
    dc = policy["deny_contract"]
    assert dc["relation_create"]["status"] == 400
    assert dc["relation_update"]["status"] == 404


def test_relation_families_are_enforced_with_the_right_deny_keys(policy):
    fam = policy["probe_families"]
    for pid in RELATION_FAMILIES:
        assert fam[pid]["status"] == "enforced", pid
        key = "relation_update" if ".update." in pid else "relation_create"
        assert fam[pid]["deny_key"] == key, pid


def test_down_keeps_every_trigger_and_reinstates_nothing(src):
    m = re.search(r"\(_db\)\s*=>\s*\{(.*?)\},\s*\);", src, re.DOTALL)
    assert m, "could not find the down() callback"
    down_body = m.group(1)
    # Forward-only: down drops no trigger and restores no quarantined row.
    assert "DROP TRIGGER" not in down_body
    assert "CREATE TRIGGER" not in down_body
    assert "saveRecord" not in down_body
    assert "deleteRecord" not in down_body


def test_triggers_enforce_owner_equality_on_insert_update_and_target(src):
    # Each relation field gets insert, update, and target-owner triggers, all
    # aborting on an owner mismatch.
    assert '_ins" BEFORE INSERT' in src
    assert '_upd" BEFORE UPDATE OF' in src
    assert '_tgt" BEFORE UPDATE OF' in src
    assert "RAISE(ABORT, 'relation endpoint denied')" in src


def test_dry_run_guards_are_present(src):
    # Dry run requires the report path, refuses to write inside pb_data, and
    # aborts so nothing changes.
    assert '"ROUNDS_RELATION_QUARANTINE"' in src or "ROUNDS_RELATION_QUARANTINE" in src
    assert "ROUNDS_RELATION_QUARANTINE_REPORT" in src
    assert 'indexOf("pb_data")' in src
    assert "dry run complete" in src


def test_only_a_unique_collision_turns_a_clear_into_a_move(src):
    # Clearing an optional cross-owner reference to "" can violate a unique
    # index (SQLite treats "" as present, unlike NULL); then the row moves.
    # Any other failed clear (a trigger abort, say) is unexpected and must fail
    # the migration whole rather than be mistaken for a collision.
    assert 'indexOf("UNIQUE constraint failed")' in src
    m = re.search(
        r"dao\.saveRecord\(rec\);\s*return true;\s*\}\s*catch \(err\) \{\s*"
        r"if \(isUniqueCollision\(err\)\) return false;\s*throw err;",
        src,
    )
    assert m, "a failed clear must fall back to a move only on a unique collision, and rethrow otherwise"


def test_all_offending_fields_of_a_row_clear_in_one_update(src):
    # Clearing one foreign provider at a time saved a row that still held the
    # other foreign provider; the whole row's offending fields go in one save.
    assert re.search(r"const fields = gs\.map\(\(g\) => g\.f\);\s*if \(clearFields\(", src)
    assert re.search(r"for \(let i = 0; i < fields\.length; i\+\+\) rec\.set\(fields\[i\], \"\"\);", src)


def test_update_trigger_checks_only_a_changed_relation(src):
    # PocketBase rewrites every column on a save, so UPDATE OF fires on every
    # save; re-checking an unchanged relation blocked deletes whose cascade
    # clears one relation of a row while another still names a deleted record.
    assert re.search(r"IS NOT OLD\.\"' \+ r\.f \+ '\" OR NEW\.\"' \+ OWNER \+ '\" IS NOT OLD\.\"' \+ OWNER", src)
    assert re.search(r"'_upd\" BEFORE UPDATE OF .*?FOR EACH ROW WHEN ' \+ changed \+ \" AND \" \+ mismatch", src, re.DOTALL)


def test_dry_run_takes_the_apply_path(src):
    # The dry run must run the same moves, clears, and journal writes as the
    # apply and only then write its report and roll back, so it predicts the
    # apply's outcome (a failure included) and its checksum.
    plan = src.index('stage = "plan";')
    journal = src.index('stage = "journal";')
    deletes = src.index("if (rec) dao.deleteRecord(rec);")
    dry_report = src.index("writeDryRunReport(report);")
    assert plan < journal < deletes < dry_report
    assert re.search(r"catch \(err\) \{.*?if \(dryRun\) \{.*?writeDryRunReport\(failed\);", src, re.DOTALL)


def test_every_step_reports_its_failure(src):
    # A failure creating the triggers or collections, or during the scan, must
    # still write the dry run's report and the apply's failure log line, so
    # every step runs inside the one reporting try.
    head = src[: src.index("migrate(")]
    body = src[src.index("migrate("):]
    tried = body.index("    try {")
    for step in ("CREATE TRIGGER", 'ensureCollection("relation_quarantine"', 'stage = "scan";', 'stage = "plan";'):
        assert body.index(step) > tried, step
    assert "CREATE TRIGGER" not in head
    assert re.search(r'logLine\("relation_quarantine_failed", \{ stage: stage, reason: reason \}\);', src)


def test_every_json_field_sets_its_own_max_size(src):
    # PocketBase's size-default migration has already run on an upgraded
    # deployment, so a JSON field created without maxSize keeps 0 and every
    # later API write to the record fails validation (marking an entry
    # replayed or dropped included).
    json_fields = re.findall(r'\{ name: "([a-z_]+)", type: "json"([^}]*\})?[^}]*\}', src)
    assert {name for name, _ in json_fields} == {"payload", "summary", "relations", "findings", "outcomes"}
    for line in re.findall(r'\{ name: "[a-z_]+", type: "json".*', src):
        assert "maxSize: JSON_MAX" in line, line
    assert re.search(r"const JSON_MAX = \d+ \* 1024 \* 1024;", src)


def test_the_guard_skips_views_and_only_refuses_what_matters(src):
    # A view, an added relation, or a toggled option with nothing to
    # quarantine must not stop the migration.
    assert 'if (colRows[i].type === "view") continue;' in src
    assert re.search(r"if \(withFindings\[key\] && \(live\.required !== want\.required \|\| live\.cascade !== want\.cascade\)\)", src)
    # A relation outside the frozen table stops it only when a row about to
    # move is referenced, inside the closure.
    deps = src[src.index("const dependentsOf = "):src.index("const referenceCleared = {};")]
    assert "unlistedByTarget[c]" in deps and "about to move" in deps


def test_the_original_row_is_raw_text_read_by_sqlite(src):
    # JSON.parse rounds integers above 2^53 and reorders keys, so the payload
    # is every column's raw value as text, built by SQLite itself.
    assert "json_object(" in src and "printf('%!.17g'" in src and 'AS TEXT) END' in src
    assert "getFloat" not in src and "getBool" not in src
    assert "payload: snapshots[keyOf(o.e.c, o.e.id)].payload" in src


LEVER = ROOT / "pocketbase" / "levers" / "replay_quarantine.template.js"


def test_the_replay_lever_restores_rows_exactly_through_the_triggers():
    lever = LEVER.read_text()
    assert 'const ENTRY_IDS = ["__ENTRY_ID__"];' in lever
    # Only a quarantined entry replays, and it becomes replayed.
    assert 'status !== "quarantined"' in lever and 'entry.set("status", "replayed");' in lever
    # A moved row comes back column by column from the stored payload, so
    # created, updated, numbers, and JSON text come back exactly.
    assert re.search(r"INSERT INTO .*json_extract\(\\\"payload\\\"", lever) or "json_extract(\\\"payload\\\"" in lever
    assert "pragma_table_info" in lever
    # down() writes nothing.
    m = re.search(r"\(_db\)\s*=>\s*\{(.*?)\},\s*\);", lever, re.DOTALL)
    assert m and "db." not in m.group(1) and "dao" not in m.group(1)


def test_cascading_fields_move_the_row(src):
    # A cross-owner required OR cascading reference moves the row; only an
    # optional, non-cascading one is cleared.
    assert re.search(r"if \(gs\[j\]\.required \|\| gs\[j\]\.cascade\) \{\s*addMove\(fromFinding\(gs\[j\]\)\);", src)


def test_journal_entries_carry_the_issue_schema(src):
    # Migration version, row, field, original row JSON, per-report pseudonyms,
    # and a status, for clears as well as moves.
    m = re.search(r'ensureCollection\("relation_quarantine", \[(.*?)\]\);', src, re.DOTALL)
    assert m
    names = set(re.findall(r'name: "([a-z_]+)"', m.group(1)))
    assert {"migration", "source_collection", "source_id", "field", "payload", "owner", "target_owner",
            "status", "action", "kind"} <= names
    assert 'status: "quarantined"' in src
    assert "owner: pub.owner" in src and "target_owner: pub.target_owner" in src


def test_touched_row_manifest_matches_the_fields_table(src):
    # The committed manifest (docs/development.md#migrations) gives the
    # disposition per relation field: a required or cascading reference moves
    # the row, an optional, non-cascading one is cleared and falls back to
    # moving the row. It must name exactly the migration's FIELDS, with the
    # same required and cascade flags.
    block = re.search(r"const FIELDS = \[(.*?)\];", src, re.DOTALL)
    assert block, "could not find the FIELDS array in the migration"
    flags = {
        (m.group(1), m.group(2), m.group(3)): (m.group(4) == "true", m.group(5) == "true")
        for m in re.finditer(
            r'\{\s*c:\s*"([^"]+)",\s*f:\s*"([^"]+)",\s*t:\s*"([^"]+)",\s*required:\s*(true|false),\s*cascade:\s*(true|false)',
            block.group(1),
        )
    }
    assert len(flags) == 34
    manifest = json.loads(TOUCHED.read_text())
    assert manifest["migration"] == "1700007000_relation_endpoint_authz"
    assert sorted(manifest["writes"]) == ["relation_quarantine", "relation_quarantine_reports"]
    got = {(e["collection"], e["field"], e["target"]): e for e in manifest["fields"]}
    assert len(got) == len(manifest["fields"]), "a field is listed twice"
    assert set(got) == set(flags)
    for key, (required, cascade) in flags.items():
        entry = got[key]
        assert entry["required"] is required and entry["cascade"] is cascade, key
        if required or cascade:
            assert entry["disposition"] == "moved" and "fallback" not in entry, key
        else:
            assert entry["disposition"] == "cleared" and entry["fallback"] == "moved", key
