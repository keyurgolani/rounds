"""Static checks on the stage-3 rule migration (ROUNDS-00B-L01/S3).

These assert the three properties the issue calls out without needing a running
PocketBase:

  * forward-only: ``migrate down`` keeps the rules, because ``down`` reverts
    nothing;
  * a missing collection fails the migration whole, because ``up`` resolves
    every collection before it writes the first rule;
  * the migration and ``docs/security/account-scope.v1.json`` agree on the rule
    forms and the exact set of collections, so the two cannot drift.

The behavioural side (``migrate up`` actually producing these rules, a missing
collection aborting, and the emergency lever) lives in
``harness/migration_check.sh``; the two-account harness reads the live rules
back against the same policy file.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1].parent
MIGRATION = ROOT / "pocketbase" / "pb_migrations" / "1700006000_account_scope_rules.js"
POLICY = ROOT / "docs" / "security" / "account-scope.v1.json"


@pytest.fixture(scope="module")
def src() -> str:
    return MIGRATION.read_text()


@pytest.fixture(scope="module")
def policy() -> dict:
    return json.loads(POLICY.read_text())


def _string_array(src: str, name: str) -> list[str]:
    m = re.search(rf"const {name} = \[(.*?)\];", src, re.DOTALL)
    assert m, f"could not find the {name} array in the migration"
    return re.findall(r'"([^"]+)"', m.group(1))


def _const(src: str, name: str) -> str:
    # Single quoted-string constant (the rule forms are single literals).
    m = re.search(rf"const {name} =\s*'([^']*)'", src, re.DOTALL)
    assert m, f"could not find the {name} constant as a single string literal"
    return m.group(1)


def test_migration_file_is_present(src):
    assert "account_scope_rules" in src
    assert src.lstrip().startswith("/// <reference")


def test_down_reverts_nothing(src):
    # The down callback takes an unused `_db` and must not restore or change a
    # rule: account isolation is never rolled back (forward-only).
    m = re.search(r"\(_db\)\s*=>\s*\{([^}]*)\}", src)
    assert m, "could not find the down() callback"
    down_body = m.group(1)
    assert "saveCollection" not in down_body
    assert "Rule" not in down_body


def test_up_resolves_every_collection_before_writing(src):
    # A missing collection must fail the migration whole, so every lookup
    # happens (and may throw) before the first saveCollection.
    first_save = src.index("saveCollection")
    owned_lookup = src.index("OWNED.map(lookup)")
    server_lookup = src.index("SERVER_ONLY.map(lookup)")
    assert owned_lookup < first_save
    assert server_lookup < first_save
    assert "throw new Error" in src  # lookup throws on a missing collection


def test_owned_and_server_only_match_the_policy(src, policy):
    owned = _string_array(src, "OWNED")
    server_only = _string_array(src, "SERVER_ONLY")
    assert server_only == ["resume_share_views"]
    assert len(owned) == 29 and len(set(owned)) == 29

    # The rows this migration rules are exactly its two arrays.
    ruled_here = {
        name for name, row in policy["collections"].items() if row["target_rule_migration"] == MIGRATION.name
    }
    assert set(owned) | set(server_only) == ruled_here
    # Every other row is users or a collection a later migration creates
    # with its rules already in place, such as #4's snapshot store.
    for name in set(policy["collections"]) - ruled_here - {"users"}:
        row = policy["collections"][name]
        assert row["migration"] == row["target_rule_migration"] > MIGRATION.name, name
        assert (MIGRATION.parent / row["migration"]).is_file(), name
    # users keeps its 0.22.22 defaults; the migration must not touch it.
    assert "users" not in owned and "users" not in server_only


def test_rule_constants_match_the_policy(src, policy):
    create_rule = _const(src, "CREATE_RULE")
    update_rule = _const(src, "UPDATE_RULE")
    # Every owned collection gets these exact create/update rules.
    for name in _string_array(src, "OWNED"):
        cur = policy["collections"][name]["current_rules"]
        assert cur["create"] == create_rule, name
        assert cur["update"] == update_rule, name
    # resume_share_views is superuser-only: create and update are null.
    rsv = policy["collections"]["resume_share_views"]["current_rules"]
    assert rsv["create"] is None and rsv["update"] is None
    # The create clause derives ownership from the caller, never the client.
    assert "@request.data.user = @request.auth.id" in create_rule
    assert "@request.data.user:isset = false" in update_rule
