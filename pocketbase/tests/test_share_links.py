"""A share link answers only its owner (ROUNDS-00B-L03 stage 1).

Two halves, both static or pure so they run without a PocketBase:

  * the create check in pb_hooks/share_links.js: screen() is pure, so it is
    require()d into Node and driven the same way test_relation_endpoints_hooks.py
    drives the relation predicate. A new link needs exactly one target, the
    caller as owner, and a 22-character URL-safe token, and every denial
    answers with the relation predicate's own create denial;
  * 1700008100_share_link_owner_rules.js: list and view read only the owner,
    no client updates a link, its down step restores nothing, and the
    migration and docs/security/account-scope.v1.json agree.

The live rules and the hook on PocketBase 0.22.22 are the two-account
harness's (account-scope.share.token-query.isolated,
account-scope.share.create-shape.denied, account-scope.update.server-only.denied
on resume_share_links, and the rule read-back).
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
POLICY = ROOT / "docs" / "security" / "account-scope.v1.json"

HARNESS = r"""
const path = require("path");
const [hooksDir, argJson] = process.argv.slice(1);
const mod = require(path.join(hooksDir, "share_links.js"));
const out = JSON.parse(argJson).map((c) => mod.screen(c.fields, c.caller, c.admin));
process.stdout.write(JSON.stringify(out));
"""

OWNER = "owner000000000a"
GOOD = "AbCdEfGhIjKlMnOpQrSt_-"


def _screen(cases: list[dict]) -> list:
    node = shutil.which("node")
    assert node, "node is required for the share link hook checks; CI installs it"
    res = subprocess.run(
        [node, "-e", HARNESS, str(HOOKS), json.dumps(cases)],
        capture_output=True, text=True, timeout=60, check=True,
    )
    return json.loads(res.stdout)


def _case(caller=OWNER, admin=False, **fields):
    base = {"user": OWNER, "resume": "res000000000001", "variant": "", "token": GOOD}
    base.update(fields)
    return {"fields": base, "caller": caller, "admin": admin}


ACCEPTED = {
    "resume": _case(),
    "variant": _case(resume="", variant="var000000000001"),
    "superuser": _case(caller="", admin=True),
}
DENIED = {
    "no-target": (_case(resume=""), "target"),
    "both-targets": (_case(variant="var000000000001"), "target"),
    "other-owner": (_case(user="other00000000b"), "owner"),
    "anonymous": (_case(caller=""), "owner"),
    "no-owner": (_case(user="", caller=""), "owner"),
    "short-token": (_case(token=GOOD[:-1]), "token"),
    "long-token": (_case(token=GOOD + "x"), "token"),
    "token-quote": (_case(token='AbCdEfGhIjKlMnOpQrS"||'), "token"),
    "token-space": (_case(token="AbCdEfGhIjKl MnOpQrStU"), "token"),
    "token-newline": (_case(token=GOOD[:21] + "\n"), "token"),
    "empty-token": (_case(token=""), "token"),
    "superuser-two-targets": (_case(caller="", admin=True, variant="var000000000001"), "target"),
    "superuser-bad-token": (_case(caller="", admin=True, token="x"), "token"),
}


def test_a_well_formed_link_passes():
    assert _screen(list(ACCEPTED.values())) == [None] * len(ACCEPTED)


@pytest.mark.parametrize("name", sorted(DENIED))
def test_a_link_without_one_target_its_owner_and_a_well_formed_token_is_denied(name):
    case, reason = DENIED[name]
    assert _screen([case]) == [reason]


def test_the_hook_token_format_matches_the_runner_minted_token():
    src = (HOOKS / "share_links.js").read_text()
    assert "/^[A-Za-z0-9_-]{22}$/" in src
    runner = (ROOT / "backend" / "routers" / "share.py").read_text()
    assert "secrets.token_urlsafe(16)" in runner  # 16 bytes -> 22 characters


def test_every_denial_is_the_relation_predicates_create_denial():
    hook = (HOOKS / "share_links.js").read_text()
    relation = (HOOKS / "relation_endpoints.js").read_text()
    denial = 'throw new BadRequestError("Failed to create record.");'
    assert denial in relation
    assert hook.count("throw new ") == 1 and denial in hook


def test_the_hook_is_wired_to_link_creates_and_logs_no_values():
    wiring = (HOOKS / "share_links.pb.js").read_text()
    assert re.search(r'onRecordBeforeCreateRequest\(\(e\) => \{\s*require\(`\$\{__hooks\}/share_links\.js`\)'
                     r'\.checkCreate\(e\);\s*\}, "resume_share_links"\);', wiring)
    hook = (HOOKS / "share_links.js").read_text()
    log = re.search(r"console\.log\((.*?)\);\n", hook, re.S).group(1)
    for value in ("token", "user:", "resume:", "variant:", "caller,", "caller:"):
        assert value not in log.replace("actor:", ""), value


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
    assert "@request.query" not in src.split("migrate(", 1)[1]


def test_down_restores_nothing(src):
    m = re.search(r"\(_db\)\s*=>\s*\{([^}]*)\}", src)
    assert m, "could not find the down() callback"
    body = m.group(1)
    assert "saveCollection" not in body and "Rule" not in body and "token" not in body


def test_the_policy_row_matches_the_migration(policy):
    row = policy["collections"]["resume_share_links"]
    rules = row["current_rules"]
    assert rules["list"] == rules["view"] == "user = @request.auth.id"
    assert rules["update"] is None
    assert row["target_rules"]["update"] is None
    assert row["rule_overrides"] == [{"migration": MIGRATION.name, "rules": ["list", "view", "update"]}]
    assert row["hook"] == "pocketbase/pb_hooks/share_links.pb.js"
    assert not [e for e in row.get("exceptions", []) if e["id"] == "share-token-read"]
    # A null update rule: no client update family that expects an accepted or
    # not-found update applies; the server-only update family does.
    probes = set(row["probes"])
    assert "account-scope.update.server-only.denied" in probes
    assert "account-scope.share.token-query.isolated" in probes
    assert "account-scope.share.create-shape.denied" in probes
    for gone in ("account-scope.update.own.accepted", "account-scope.update.reassign-owner.denied",
                 "account-scope.update.cross-account.denied", "account-scope.update.anonymous.denied",
                 "account-scope.update.foreign-or-missing.indistinguishable",
                 "account-scope.update.relation-foreign.denied",
                 "account-scope.update.relation-foreign-or-missing.indistinguishable"):
        assert gone not in probes, gone
