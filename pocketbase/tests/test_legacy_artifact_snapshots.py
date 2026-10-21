"""Static checks on the Legacy Artifact Snapshot store (ROUNDS-00A-L04, PR 1).

The behavioural side, with the pinned PocketBase binary, is harness phase 14
(harness/probes/snapshot_store_check.py): the migration applies, its down
step keeps a non-empty store and drops an empty one, and it reapplies. The
two-account harness probes the collection's row in the account-scope policy.
These pin the parts a reviewer reads: the rules, the field limits, the reuse
index, the down step's guard, and the policy and server-write rows.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1].parent
MIGRATION = ROOT / "pocketbase" / "pb_migrations" / "1700008000_legacy_artifact_snapshots.js"
POLICY = ROOT / "docs" / "security" / "account-scope.v1.json"
SERVER_WRITES = ROOT / "docs" / "security" / "server-writes.md"


@pytest.fixture(scope="module")
def src() -> str:
    return MIGRATION.read_text()


def _up(src: str) -> str:
    return src[src.index("migrate(") : src.index("(db) => {", src.index("dao.saveCollection(snapshots)"))]


def _down(src: str) -> str:
    return src[src.index("(db) => {", src.index("dao.saveCollection(snapshots)")) :]


def test_it_sorts_after_the_migrations_it_depends_on():
    # It must apply after the account-scope rules and the relation-endpoint
    # authorization migration so the owner rules and the server-write
    # invariants are already in place. It need not be the last migration,
    # so a later leaf may add one after it without breaking this.
    names = sorted(p.name for p in MIGRATION.parent.glob("*.js"))
    assert MIGRATION.name in names
    for prerequisite in ("1700006000_account_scope_rules.js", "1700007000_relation_endpoint_authz.js"):
        assert prerequisite in names, prerequisite
        assert names.index(prerequisite) < names.index(MIGRATION.name), prerequisite


def test_owners_read_and_no_client_writes(src):
    up = _up(src)
    assert 'listRule: "user = @request.auth.id"' in up
    assert 'viewRule: "user = @request.auth.id"' in up
    for rule in ("createRule", "updateRule", "deleteRule"):
        assert f"{rule}: null" in up, rule


def test_every_json_field_sets_max_size(src):
    # A JSON field without maxSize keeps 0 on a database that upgraded across
    # PocketBase's size default, and then rejects every value.
    fields = re.findall(r'\{ name: "(\w+)", type: "json"[^}]*options: \{ maxSize: ([^}]+) \}', src)
    assert sorted(name for name, _ in fields) == ["data", "design", "font_families"]
    assert all(size.strip() for _, size in fields)
    assert src.count('type: "json"') == 3


def test_markup_is_one_protected_html_file_of_at_most_2_mib(src):
    up = _up(src)
    block = up[up.index('name: "markup"') : up.index("content_checksum")]
    assert 'type: "file"' in block and "required: true" in block
    assert "maxSelect: 1" in block and "maxSize: MAX_MARKUP_BYTES" in block
    assert 'mimeTypes: ["text/html"]' in block and "protected: true" in block
    assert "const MAX_MARKUP_BYTES = 2 * 1024 * 1024;" in up


def test_the_owner_relation_cascades_and_sources_are_plain_text(src):
    up = _up(src)
    owner = up[up.index('name: "user"') : up.index('text("source_kind"')]
    assert 'type: "relation"' in owner and "cascadeDelete: true" in owner and "maxSelect: 1" in owner
    assert up.count('type: "relation"') == 1
    for name in ("source_kind", "source_id", "source_updated", "parent_id", "parent_updated"):
        assert f'text("{name}"' in up, name


def test_reuse_stays_inside_one_source(src):
    assert (
        '"CREATE UNIQUE INDEX idx_legacy_artifact_snapshots_reuse ON legacy_artifact_snapshots " +\n'
        '          "(user, source_kind, source_id, content_checksum, materializer_digest)"'
    ) in src


def test_down_drops_the_collection_only_while_it_is_empty(src):
    down = _down(src)
    count = down.index("SELECT COUNT(*) AS n FROM legacy_artifact_snapshots")
    refuse = down.index("throw new Error(")
    drop = down.index("dao.deleteCollection(collection)")
    assert count < refuse < drop
    assert "if (count.n > 0)" in down
    # Nothing else is dropped, and no row is deleted.
    assert down.count("deleteCollection") == 1
    assert "DELETE FROM" not in down.upper()
    assert not re.search(r"\bdelete(?!Collection\b)\w*\s*\(", down)


def test_the_policy_row_states_the_migration_rules():
    row = json.loads(POLICY.read_text())["collections"]["legacy_artifact_snapshots"]
    assert row["migration"] == row["target_rule_migration"] == MIGRATION.name
    assert row["current_rules"] == {
        "list": "user = @request.auth.id",
        "view": "user = @request.auth.id",
        "create": None,
        "update": None,
        "delete": None,
    }
    assert row["owner_field"] == "user" and row["relation_exceptions"] == [] and "relation_endpoints" not in row


def test_the_server_write_record_registers_the_writer():
    text = SERVER_WRITES.read_text()
    (row,) = [line for line in text.splitlines() if line.startswith("| #4 |")]
    assert "`legacy_artifact_snapshots`" in row and "POST /api/rounds/legacy-snapshots" in row
    assert MIGRATION.name in text
