"""Static and contract checks on the relation-endpoint migration (ROUNDS-00B-L02).

These assert, without a running PocketBase, that the three sources of truth for
typed-relation authorization never drift:

  * the canonical table ``pocketbase/pb_hooks/relation_endpoints.v1.json``;
  * the ``FIELDS`` array in
    ``pocketbase/pb_migrations/1700007000_relation_endpoint_authz.js`` that the
    triggers and the quarantine scan iterate; and
  * the per-collection ``relation_endpoints`` in
    ``docs/security/account-scope.v1.json`` that the harness points its probes
    at.

They also pin the migration's forward-only ``down`` (every trigger stays, no
quarantined row is reinstated) and the dry-run guards, and check that every
collection whose policy row lists a relation family declares a non-empty
``relation_endpoints`` so no probe passes vacuously.

The behavioural side (triggers actually aborting a cross-owner write, the dry
run leaving the database untouched, apply moving and clearing rows) lives in
``harness/migration_check.sh`` and ``harness/probes/scan_check.py``.
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
        assert rex - rep == shared, (name, sorted(rex - rep), sorted(shared))


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


def test_optional_clear_falls_back_to_quarantine_on_a_unique_collision(src):
    # Clearing an optional cross-owner reference to "" can violate a unique
    # index (SQLite treats "" as present, unlike NULL). The apply must catch
    # that and quarantine the whole row instead of letting the write throw and
    # roll back the boot transaction. Keep the clear inside a try/catch whose
    # recovery path moves the row.
    m = re.search(
        r'rec\.set\(g\.f, ""\);\s*try \{.*?catch.*?quarantineRow\(g, fresh\);',
        src,
        re.DOTALL,
    )
    assert m, "optional clear must fall back to quarantineRow on a failed save"
