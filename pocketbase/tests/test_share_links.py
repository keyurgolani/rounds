"""Share link rows (ROUNDS-00B-L03 stage 1, ROUNDS-00B-L06 stage 1).

Two halves, both static or pure so they run without a PocketBase:

  * the older links' guard in pb_hooks/share_links.js: screenUpdate() is
    pure, so legacy_shares_runner.cjs require()s it into Node. Once
    1700008500_legacy_share_migration.js has turned every link off, a row
    changes only when "Get a new link" sets its replaced_by, from empty to a
    capability, once; any other change by any writer the app's Dao runs is
    refused;
  * 1700008100_share_link_owner_rules.js: list and view read only the owner,
    no client updates a link, and its down step restores nothing.
    1700008500 sets every rule again, and docs/security/account-scope.v1.json
    names both.

The live rules and the guard on PocketBase 0.22.57 are the two-account
harness's (account-scope.share.owner-only.isolated and the server-only
families on resume_share_links, the rule read-back) and phase 15's.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / "pocketbase" / "pb_hooks"
MIGRATIONS = ROOT / "pocketbase" / "pb_migrations"
MIGRATION = MIGRATIONS / "1700008100_share_link_owner_rules.js"
RUNNER = ROOT / "pocketbase" / "tests" / "legacy_shares_runner.cjs"
POLICY = ROOT / "docs" / "security" / "account-scope.v1.json"

CAPABILITY = "capaaaaaaaaaaa1"


def _screen(cases: list[dict]) -> list:
    node = shutil.which("node")
    assert node, "node is required for the share link hook checks; CI installs it"
    program = {"steps": [{"call": "screenUpdate", "cases": cases}]}
    res = subprocess.run([node, str(RUNNER), str(HOOKS), str(MIGRATIONS)], input=json.dumps(program),
                         capture_output=True, text=True, timeout=60, check=True)
    return json.loads(res.stdout)["results"][0]


def _row(**over) -> dict:
    row = {"user": "owner000000000a", "resume": "res000000000001", "variant": "", "legacy_status": "migrated",
           "legacy_reason": "eligible", "turned_off_at": "2026-11-11 12:00:00.000Z", "manifest_id": "legacy-shares-v1",
           "replaced_by": "", "created": "2026-01-02 03:04:05.000Z", "updated": "2026-11-11 12:00:00.000Z"}
    row.update(over)
    return row


ACCEPTED = {
    "the-first-replacement": (_row(), _row(replaced_by=CAPABILITY)),
    "a-save-that-changes-nothing": (_row(), _row()),
    "a-save-that-changes-only-updated": (_row(), _row(updated="2026-11-12 00:00:00.000Z")),
    "a-replaced-row-saved-again": (_row(replaced_by=CAPABILITY), _row(replaced_by=CAPABILITY)),
}
REFUSED = {
    "a-second-replacement": (_row(replaced_by=CAPABILITY), _row(replaced_by="capbbbbbbbbbbb2"), "replaced_by"),
    "a-replacement-cleared": (_row(replaced_by=CAPABILITY), _row(), "replaced_by"),
    "a-replacement-that-isnt-an-id": (_row(), _row(replaced_by="x"), "replaced_by"),
    "the-status-turned-back-on": (_row(legacy_status="revoked_unverified"), _row(legacy_status="migrated"), "field"),
    "the-status-cleared": (_row(), _row(legacy_status=""), "field"),
    "the-reason-changed": (_row(), _row(legacy_reason="token_format"), "field"),
    "the-owner-changed": (_row(), _row(user="other00000000b"), "field"),
    "the-target-changed": (_row(), _row(resume="res000000000002"), "field"),
    "a-variant-added": (_row(), _row(variant="var000000000001"), "field"),
    "the-date-changed": (_row(), _row(turned_off_at=""), "field"),
    "created-changed": (_row(), _row(created="2020-01-01 00:00:00.000Z"), "field"),
    "a-field-added-back": (_row(), _row(token="AbCdEfGhIjKlMnOpQrSt_-"), "field"),
    "a-replacement-and-another-change": (_row(), _row(replaced_by=CAPABILITY, legacy_status="revoked_demo"), "field"),
}


def test_a_link_takes_only_its_first_replacement():
    assert _screen([{"before": b, "after": a} for b, a in ACCEPTED.values()]) == [None] * len(ACCEPTED)


@pytest.mark.parametrize("name", sorted(REFUSED))
def test_every_other_change_to_an_older_link_is_refused(name):
    before, after, reason = REFUSED[name]
    assert _screen([{"before": before, "after": after}]) == [reason]


def test_the_guard_is_wired_to_every_save_of_a_link_and_logs_only_a_reason():
    wiring = (HOOKS / "share_links.pb.js").read_text()
    assert re.search(r'onModelBeforeUpdate\(\(e\) => \{\s*require\(`\$\{__hooks\}/share_links\.js`\)'
                     r'\.checkUpdate\(e\);\s*\}, "resume_share_links"\);', wiring)
    assert "onRecordBeforeCreateRequest" not in wiring
    hook = (HOOKS / "share_links.js").read_text()
    (log,) = re.findall(r"console\.log\((.*?)\);\n", hook, re.S)
    assert re.sub(r"\s+", " ", log) == ('JSON.stringify({ v: "obs/v1", event: "share_link_refused", service: '
                                        '"pocketbase", reason })')
    assert hook.count("throw new ") == 1


def test_re_issue_is_the_one_writer_of_replaced_by():
    # pb_hooks/share_secrets.js sets it inside the capability's transaction;
    # nothing else in the hooks writes it.
    writers = [p.name for p in HOOKS.glob("*.js") if '"replaced_by"' in p.read_text()]
    assert sorted(writers) == ["share_links.js", "share_secrets.js"]
    secrets = (HOOKS / "share_secrets.js").read_text()
    assert secrets.count('link.set("replaced_by", capabilityId);') == 1


# ---- the rule migration ------------------------------------------------------


@pytest.fixture(scope="module")
def src() -> str:
    return MIGRATION.read_text()


@pytest.fixture(scope="module")
def policy() -> dict:
    return json.loads(POLICY.read_text())


def test_the_migration_sorts_after_every_earlier_rule_migration():
    names = sorted(p.name for p in MIGRATIONS.glob("*.js") if p.name.startswith("17000"))
    assert names.index(MIGRATION.name) > names.index("1700006000_account_scope_rules.js")
    assert names.index(MIGRATION.name) > names.index("1700007000_relation_endpoint_authz.js")


def test_up_sets_owner_only_reads_and_no_updates(src):
    up = src[src.index("migrate("): src.index("(_db) =>")]
    assert 'const OWNER_READ = "user = @request.auth.id";' in src
    assert "links.listRule = OWNER_READ;" in up
    assert "links.viewRule = OWNER_READ;" in up
    assert "links.updateRule = null;" in up
    # Only resume_share_links changes, and only those three rules.
    assert up.count("findCollectionByNameOrId(") == 1
    assert re.findall(r"\.(\w+Rule) =", up) == ["listRule", "viewRule", "updateRule"]


def test_down_restores_nothing(src):
    m = re.search(r"\(_db\)\s*=>\s*\{([^}]*)\}", src)
    assert m, "could not find the down() callback"
    body = m.group(1)
    assert "saveCollection" not in body and "Rule" not in body and "token" not in body


def test_the_policy_row_names_both_rule_migrations_and_only_server_only_writes(policy):
    row = policy["collections"]["resume_share_links"]
    rules = row["current_rules"]
    assert rules["list"] == rules["view"] == 'legacy_status != "revoked_ownership" && user = @request.auth.id'
    assert rules["create"] is rules["update"] is rules["delete"] is None
    assert row["target_rules"] == {"create": None, "update": None}
    assert row["rule_overrides"] == [
        {"migration": MIGRATION.name, "rules": ["list", "view", "update"]},
        {"migration": "1700008500_legacy_share_migration.js", "rules": ["list", "view", "create", "update", "delete"]},
    ]
    assert row["hook"] == "pocketbase/pb_hooks/share_links.pb.js"
    assert not row.get("exceptions")
    # No client writes at all: only the server-only families apply to writes,
    # and the superuser seeds the fixture.
    probes = set(row["probes"])
    for kept in ("account-scope.create.server-only.denied", "account-scope.update.server-only.denied",
                 "account-scope.delete.server-only.denied", "account-scope.create.superuser.accepted",
                 "account-scope.create.relation-superuser.denied", "account-scope.share.owner-only.isolated"):
        assert kept in probes, kept
    for gone in ("account-scope.update.own.accepted", "account-scope.update.reassign-owner.denied",
                 "account-scope.create.foreign-owner.denied", "account-scope.create.anonymous.denied",
                 "account-scope.delete.cross-account.denied", "account-scope.share.create-shape.denied",
                 "account-scope.create.relation-foreign.denied"):
        assert gone not in probes, gone
