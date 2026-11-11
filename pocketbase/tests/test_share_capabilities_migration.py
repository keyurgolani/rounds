"""Static checks on the share capability store (ROUNDS-00B-L03 stage 2).

The behavioural side runs on the pinned PocketBase natively and in #9's
harness: the hooks, the owner's routes, deletes of a shared source and of an
account, and a named snapshot that can't be deleted. These pin what a
reviewer reads in 1700008200_share_capabilities.js: every client rule null,
the fields and their limits, the unique digest, the owner-equality triggers,
the down step's guard, and the shape that keeps a source delete from ever
reaching a snapshot.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1].parent
MIGRATIONS = ROOT / "pocketbase" / "pb_migrations"
MIGRATION = MIGRATIONS / "1700008200_share_capabilities.js"
SNAPSHOTS = MIGRATIONS / "1700008000_legacy_artifact_snapshots.js"
POLICY = ROOT / "docs" / "security" / "account-scope.v1.json"
SERVER_WRITES = ROOT / "docs" / "security" / "server-writes.md"


@pytest.fixture(scope="module")
def src() -> str:
    return MIGRATION.read_text()


def _up(src: str) -> str:
    return src[src.index("migrate(") : src.index("(db) => {", src.index("dao.saveCollection(collection)"))]


def _down(src: str) -> str:
    return src[src.index("(db) => {", src.index("dao.saveCollection(collection)")) :]


def _schema_entries(text: str) -> list[str]:
    """Each top-level `{ name: ... }` entry or helper call of the schema array."""
    block = text[text.index("schema: [") : text.index("indexes: [")]
    return re.findall(r'(\{\s*name: "\w+",[\s\S]*?\n\s{8}\}|\w+\("\w+"[^\n]*\))', block)


def test_it_sorts_after_the_store_it_names_and_the_rules_before_it():
    names = sorted(p.name for p in MIGRATIONS.glob("*.js"))
    for prerequisite in ("1700007000_relation_endpoint_authz.js", "1700008000_legacy_artifact_snapshots.js",
                         "1700008100_share_link_owner_rules.js"):
        assert names.index(prerequisite) < names.index(MIGRATION.name), prerequisite


def test_no_client_rule_reads_or_writes_it(src):
    up = _up(src)
    for rule in ("listRule", "viewRule", "createRule", "updateRule", "deleteRule"):
        assert f"{rule}: null" in up, rule
    assert "@request" not in up


def test_the_fields_and_their_limits(src):
    up = _up(src)
    assert re.search(r'name: "user",\s*type: "relation",\s*required: true,\s*'
                     r'options: \{ collectionId: users\.id, cascadeDelete: true, minSelect: null, maxSelect: 1', up)
    assert re.search(r'name: "snapshot",\s*type: "relation",\s*required: true,\s*'
                     r'options: \{ collectionId: snapshots\.id, cascadeDelete: false, minSelect: null, maxSelect: 1',
                     up)
    assert 'findCollectionByNameOrId("legacy_artifact_snapshots")' in up
    for helper in (
        'text("target_kind", "^legacy_artifact_snapshot$", true)',
        'text("target_checksum", "^sha256:[0-9a-f]{64}$", true)',
        'text("purpose", "^[^\\\\x00-\\\\x1f\\\\x7f]+$", true, 80)',
        'date("expires_at", true)',
        'text("password_policy_ref", "^[!-~]+$", false, 512)',
        'text("view_policy", "^disabled$", true)',
        'number("capability_version", 1, null)',
        'text("status", "^(active|revoked)$", true)',
        'date("revoked_at", false)',
        'text("revoked_reason", "^(owner|source_deleted)$", false)',
        'number("projection_version", 1, 1)',
        'text("bearer_digest", "^[0-9a-f]{64}$", true)',
        'number("digest_key_version", 1, 999)',
    ):
        assert helper in up, helper
    # Fifteen fields, none of them JSON, so nothing joins the JSON limit
    # registry (D10).
    assert len(_schema_entries(up)) == 15
    assert 'type: "json"' not in up


def test_a_digest_names_one_capability(src):
    assert "CREATE UNIQUE INDEX idx_share_capabilities_digest ON share_capabilities (bearer_digest)" in _up(src)


def test_the_only_relation_it_adds_is_the_snapshot_and_it_gets_the_owner_triggers(src):
    fields = re.findall(r'\{ c: "(\w+)", f: "(\w+)", t: "(\w+)", required: (true|false), cascade: (true|false) \}', src)
    assert fields == [("share_capabilities", "snapshot", "legacy_artifact_snapshots", "true", "false")]
    up = _up(src)
    for suffix in ("_ins", "_upd", "_tgt"):
        assert f"q('DROP TRIGGER IF EXISTS \"' + base + '{suffix}\"')" in up, suffix
    assert up.count("RAISE(ABORT, 'relation endpoint denied')") == 3


def test_down_keeps_a_store_that_holds_a_capability(src):
    down = _down(src)
    count = down.index("SELECT COUNT(*) AS n FROM ")
    refuse = down.index("throw new Error(")
    drop = down.index("dao.deleteCollection(collection)")
    assert count < refuse < drop
    # The trigger on the snapshot table names this one, so it goes with it.
    assert down.index('_tgt"') < drop


def test_a_snapshot_names_its_source_as_plain_text_so_a_source_delete_never_reaches_it():
    # Deleting a shared resume or variant has to finish: a relation from a
    # snapshot to its source would cascade into the snapshot and meet the
    # capability's required, non-cascading reference.
    snapshots = SNAPSHOTS.read_text()
    relations = re.findall(r'name: "(\w+)",\s*type: "relation"', snapshots)
    assert relations == ["user"]
    for name in ("source_id", "parent_id"):
        assert re.search(rf'text\("{name}"', snapshots), name
    # And no later migration adds a relation to the snapshot store.
    for path in MIGRATIONS.glob("*.js"):
        if path.name <= SNAPSHOTS.name:
            continue
        text = path.read_text()
        assert not re.search(r'findCollectionByNameOrId\("legacy_artifact_snapshots"\)[\s\S]*addField', text), path.name


def test_the_policy_row_and_the_server_write_rows_name_it():
    policy = json.loads(POLICY.read_text())
    row = policy["collections"]["share_capabilities"]
    assert row["migration"] == MIGRATION.name
    assert row["current_rules"] == {op: None for op in ("list", "view", "create", "update", "delete")}
    assert row["hook"] == "pocketbase/pb_hooks/share_capabilities.pb.js"
    assert row["relation_endpoints"] == [{"field": "snapshot", "target": "legacy_artifact_snapshots"}]
    writes = SERVER_WRITES.read_text()
    assert "`create_capability`" in writes
    assert "`POST /api/rounds/share/capabilities/:id/revoke`" in writes
