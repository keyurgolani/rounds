"""The older share links' migration (ROUNDS-00B-L06 stage 1).

1700008500_legacy_share_migration.js turns off every share link made before
the release that carries it. Its decisions run here under node
(legacy_shares_runner.cjs): each link's outcome and reason, and the journal's
rows, each under its own link's id. Static checks hold its order, its lint entry (pinned to
the file and waiting on the owner's review), its manifest, and its down
step to what the header says. Harness phase 15 runs it on real databases
with PocketBase 0.22.22: a copy, a forward run, a run stopped part way and
run again, the down step, and a second forward run.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
NAME = "1700008500_legacy_share_migration"
MIGRATIONS = ROOT / "pocketbase" / "pb_migrations"
MIGRATION = MIGRATIONS / f"{NAME}.js"
HOOKS = ROOT / "pocketbase" / "pb_hooks"
RUNNER = ROOT / "pocketbase" / "tests" / "legacy_shares_runner.cjs"
MANIFEST = ROOT / "pocketbase" / "migration-manifests" / "legacy-shares-v1.json"
ALLOWLIST = ROOT / "scripts" / "migration-lint-allowlist.json"
POLICY = ROOT / "docs" / "security" / "account-scope.v1.json"

sys.path.insert(0, str(ROOT / "scripts"))
try:
    import lint_migrations as lm
finally:
    sys.path.pop(0)

OWNER, OTHER = "acct00000000001", "acct00000000002"
RESUME, OTHER_RESUME, VARIANT = "resumeaaaaaaaa1", "resumebbbbbbbb1", "variantaaaaaaa1"
GOOD = "AbCdEfGhIjKlMnOpQrSt_-"
LINK_RULE = 'legacy_status != "revoked_ownership" && user = @request.auth.id'
VIEW_RULE = 'link.legacy_status != "revoked_ownership" && user = @request.auth.id'


def run(*steps: dict) -> list:
    node = shutil.which("node")
    assert node, "node is required for the PocketBase hook checks; CI installs it"
    res = subprocess.run([node, str(RUNNER), str(HOOKS), str(MIGRATIONS)], input=json.dumps({"steps": list(steps)}),
                         capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)["results"]


@pytest.fixture(scope="module")
def src() -> str:
    return MIGRATION.read_text()


@pytest.fixture(scope="module")
def constants() -> dict:
    (out,) = run({"call": "constants"})
    return out


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def link(**over) -> dict:
    """A link as the classifying query reads it: a well-formed one of the
    owner's own resume, unless `over` says otherwise."""
    row = {"user": OWNER, "resume": RESUME, "variant": "", "token": GOOD, "is_password": 0, "password_hash": "",
           "expires_at": "", "owner_found": 1, "owner_demo": 0, "resume_found": 1, "resume_owner": OWNER,
           "variant_found": 0, "variant_owner": "", "parent_found": 0, "parent_owner": ""}
    row.update(over)
    return row


def variant_link(**over) -> dict:
    row = link(resume="", resume_found=0, resume_owner="", variant=VARIANT, variant_found=1, variant_owner=OWNER,
               parent_found=1, parent_owner=OWNER)
    row.update(over)
    return row


# Every clause of the predicate, and what failing it gives.
CASES = {
    "own-resume": (link(), ("migrated", "eligible")),
    "own-variant": (variant_link(), ("migrated", "eligible")),
    "both-targets-own": (variant_link(resume=RESUME, resume_found=1, resume_owner=OWNER), ("migrated", "eligible")),
    "resume-of-another-account": (link(resume=OTHER_RESUME, resume_owner=OTHER), ("revoked_ownership", "target_owner")),
    "variant-of-another-account": (variant_link(variant_owner=OTHER), ("revoked_ownership", "target_owner")),
    "variant-whose-parent-is-another-accounts": (variant_link(parent_owner=OTHER), ("revoked_ownership", "parent_owner")),
    "second-target-of-another-account": (variant_link(resume=OTHER_RESUME, resume_found=1, resume_owner=OTHER),
                                         ("revoked_ownership", "target_owner")),
    "demo-owner": (link(owner_demo=1), ("revoked_demo", "demo_account")),
    "owner-gone": (link(owner_found=0), ("revoked_unverified", "owner_missing")),
    "no-owner": (link(user="", owner_found=0, resume_owner=""), ("revoked_unverified", "owner_missing")),
    "no-target": (link(resume="", resume_found=0, resume_owner=""), ("revoked_unverified", "no_target")),
    "resume-gone": (link(resume_found=0, resume_owner=""), ("revoked_unverified", "target_missing")),
    "variant-gone": (variant_link(variant_found=0, variant_owner="", parent_found=0, parent_owner=""),
                     ("revoked_unverified", "target_missing")),
    "variant-parent-gone": (variant_link(parent_found=0, parent_owner=""), ("revoked_unverified", "target_missing")),
    "short-token": (link(token=GOOD[:-1]), ("revoked_unverified", "token_format")),
    "long-token": (link(token=GOOD + "x"), ("revoked_unverified", "token_format")),
    "token-with-a-quote": (link(token='AbCdEfGhIjKlMnOpQrS"ab'), ("revoked_unverified", "token_format")),
    "empty-token": (link(token=""), ("revoked_unverified", "token_format")),
    "password-flag": (link(is_password=1), ("revoked_unverified", "password_set")),
    "password-verifier": (link(password_hash="x"), ("revoked_unverified", "password_set")),
    "expiry": (link(expires_at="2030-01-01"), ("revoked_unverified", "expiry_set")),
}


def test_the_file_is_a_migration_that_sorts_after_every_share_migration_and_before_the_json_limits(src):
    assert src.lstrip().startswith("/// <reference") and "migrate(" in src
    names = sorted(p.name for p in MIGRATIONS.glob("*.js"))
    at = names.index(MIGRATION.name)
    for earlier in ("1700006700_demo_contain.js", "1700007000_relation_endpoint_authz.js",
                    "1700008100_share_link_owner_rules.js", "1700008200_share_capabilities.js",
                    "1700008300_share_secrets.js"):
        assert names.index(earlier) < at, earlier
    assert at < names.index("1702134273_json_limits.js")


def test_it_registers_both_steps_and_loads_no_code(src, constants):
    assert constants["registered"]
    assert "require(" not in src


@pytest.mark.parametrize("name", sorted(CASES))
def test_each_predicate_clause_gives_its_outcome_and_reason(name):
    row, (outcome, reason) = CASES[name]
    assert run({"call": "classify", "rows": [row]})[0] == [{"outcome": outcome, "reason": reason}]


def journal_rows(ids: list[str], decided: list[dict], origin: str = "live") -> list[dict]:
    return run(*({"call": "journalRow", "link": i, "origin": origin, "entry": "" if origin == "live" else
                  f"q{n:014d}", "decided": d, "views": []} for n, (i, d) in enumerate(zip(ids, decided))))


def test_classifying_twice_gives_the_same_outcomes_and_rows():
    rows = [row for row, _want in CASES.values()]
    ids = [f"link{n:011d}" for n in range(len(rows))]
    (first,) = run({"call": "classify", "rows": rows})
    (again,) = run({"call": "classify", "rows": rows})
    assert first == again
    assert [tuple(r.values()) for r in first] == [want for _row, want in CASES.values()]
    assert journal_rows(ids, first) == journal_rows(ids, again)


def test_ownership_comes_before_the_demo_account_and_the_demo_account_before_the_rest():
    both = link(resume=OTHER_RESUME, resume_owner=OTHER, owner_demo=1, token="short")
    demo_and_bad = link(owner_demo=1, token="short", is_password=1)
    assert run({"call": "classify", "rows": [both, demo_and_bad]})[0] == [
        {"outcome": "revoked_ownership", "reason": "target_owner"},
        {"outcome": "revoked_demo", "reason": "demo_account"},
    ]


def test_a_quarantined_link_is_revoked_for_ownership_with_its_kind_as_the_reason():
    kinds = ["cross_owner", "missing_target", "dependent", "something_else", ""]
    assert run({"call": "classifyQuarantined", "kinds": kinds})[0] == [
        {"outcome": "revoked_ownership", "reason": r} for r in
        ("quarantined_cross_owner", "quarantined_missing_target", "quarantined_dependent", "quarantined_other",
         "quarantined_other")
    ]


# Ids a client could pick for its own links: near neighbours, ones that
# differ only in letter case, and PocketBase's other id characters.
CHOSEN = ["aaaaaaaaaaaaaaa", "aaaaaaaaaaaaaab", "AAAAAAAAAAAAAAA", "aAaAaAaAaAaAaAa", "a_a_a_a_a_a_a_a",
          "zzzzzzzzzzzzzzz", "000000000000000", "00000000000000O", "link00000000001", "LINK00000000001"]
ELIGIBLE = {"outcome": "migrated", "reason": "eligible"}


def test_a_journal_rows_id_is_its_links_own_id():
    rows = journal_rows(CHOSEN, [ELIGIBLE] * len(CHOSEN))
    assert [r["id"] for r in rows] == CHOSEN
    assert all(r["link"] == r["id"] for r in rows)
    quarantined = journal_rows(CHOSEN[:2], [{"outcome": "revoked_ownership", "reason": "quarantined_cross_owner"}] * 2,
                               origin="quarantine")
    assert [r["id"] for r in quarantined] == CHOSEN[:2]


def test_the_journal_row_ids_are_unique_by_construction(src):
    # Every row is journalRow's, whose id is its link's, and only two paths
    # insert one: step 3's live links, which are unique ids in id order, and
    # the quarantined links quarantinedLinks() picks.
    assert src.count("insertJournal(entry)") == 2 and src.count("journalRow(") == 3
    assert "id: linkId," in src and "journalId" not in src
    live = CHOSEN[:4]
    entries = [{"id": f"q{n:014d}", "source_id": s, "kind": "cross_owner"} for n, s in
               enumerate([CHOSEN[0], CHOSEN[4], CHOSEN[4], CHOSEN[5], CHOSEN[2], CHOSEN[6], CHOSEN[6], CHOSEN[6]])]
    (held,) = run({"call": "quarantinedLinks", "entries": entries, "live": live})
    # One per link, its first entry, and none for a link that's live again.
    assert [(e["source_id"], e["id"]) for e in held] == [(CHOSEN[4], entries[1]["id"]), (CHOSEN[5], entries[3]["id"]),
                                                          (CHOSEN[6], entries[5]["id"])]
    rows = journal_rows(live, [ELIGIBLE] * len(live)) + journal_rows(
        [e["source_id"] for e in held], [{"outcome": "revoked_ownership", "reason": "quarantined_cross_owner"}] * len(held),
        origin="quarantine")
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)) == len(live) + len(held)


def test_a_rerun_reproduces_the_journal_checksum():
    rows = [row for row, _want in CASES.values()]
    ids = [f"link{n:011d}" for n in range(len(rows))]
    (decided,) = run({"call": "classify", "rows": rows})
    first = journal_rows(ids, decided)
    # A second run keeps each link's row, whatever order it meets them in;
    # a fresh one in another order writes the same rows.
    kept = {r["link"]: r for r in first}
    rerun = [kept[i] for i in reversed(ids)]
    fresh = journal_rows(list(reversed(ids)), list(reversed(decided)))

    def checksum(journal: list[dict]) -> str:
        data = {"journal": journal, "links": [{"id": r["link"], "status": r["outcome"], "replaced": False}
                                              for r in journal],
                "linkColumns": ["user", "resume", "variant"], "linkEntries": [], "viewRows": {"rows": 0, "detailed": 0},
                "viewEntries": {"entries": 0, "detailed": 0}, "commit": "", "unavailable": None}
        (out,) = run({"call": "receipt", "input": data})
        assert out["reconciled"] is True
        return out["journal"]["checksum"]

    assert checksum(first) == checksum(rerun) == checksum(fresh)


def test_a_journal_row_counts_views_and_flags_a_viewed_link_of_another_account_as_an_incident():
    days = ["2024-03-02", "", "2024-01-05", "2024-03-01"]
    viewed = run({"call": "journalRow", "link": "link00000000001", "origin": "quarantine", "entry": "entry0000000001",
                  "decided": {"outcome": "revoked_ownership", "reason": "quarantined_cross_owner"}, "views": days})[0]
    assert (viewed["views"], viewed["first_view_day"], viewed["last_view_day"]) == (4, "2024-01-05", "2024-03-02")
    assert viewed["incident"] is True and viewed["quarantine_entry"] == "entry0000000001"
    assert set(viewed) == {"id", "manifest", "predicate_version", "link", "origin", "quarantine_entry", "outcome",
                           "reason", "views", "first_view_day", "last_view_day", "incident"}
    unviewed = run({"call": "journalRow", "link": "link00000000002", "origin": "quarantine", "entry": "",
                    "decided": {"outcome": "revoked_ownership", "reason": "quarantined_cross_owner"}, "views": []})[0]
    assert unviewed["incident"] is False and (unviewed["first_view_day"], unviewed["last_view_day"]) == ("", "")
    own = run({"call": "journalRow", "link": "link00000000003", "origin": "live", "entry": "",
               "decided": {"outcome": "migrated", "reason": "eligible"}, "views": days})[0]
    assert own["incident"] is False and own["views"] == 4


def test_the_day_rule_keeps_a_real_calendar_day_only(src):
    expr = run({"call": "day", "expr": "viewed_at"})[0]
    assert "date(substr(COALESCE(viewed_at, ''), 1, 10)) IS substr(COALESCE(viewed_at, ''), 1, 10)" in expr
    assert src.count("DAY(") >= 4


def test_the_migration_and_the_receipt_agree_on_every_code_and_field(constants):
    receipt = constants["receipt"]
    assert receipt["manifest"] == constants["manifest"] == "legacy-shares-v1"
    assert receipt["predicate_version"] == constants["predicate_version"] == 1
    assert receipt["outcomes"] == constants["outcomes"]
    assert receipt["reasons"] == constants["reasons"]
    assert receipt["dropped"] == constants["dropped"] == ["expires_at", "is_password", "password_hash", "token"]
    assert receipt["link_payload_drops"] == constants["link_payload_drops"] == ["token", "password_hash", "expires_at"]
    assert receipt["view_payload_drops"] == constants["view_payload_drops"] == ["viewer_ip_hash", "user_agent"]


def test_the_manifest_names_the_same_codes_batch_rules_and_drops(constants, manifest, src):
    assert manifest["manifest"] == constants["manifest"]
    assert manifest["predicate_version"] == constants["predicate_version"]
    assert manifest["batch_size"] == constants["batch"] == 500
    assert manifest["outcomes"] == constants["reasons"]
    assert manifest["owner_approval"] == "pending owner review"
    (stage,) = manifest["migrations"]
    assert stage["migration"] == NAME
    (drop,) = stage["schema"]["drops"]
    assert drop["fields"] == constants["dropped"] and drop["index"] == constants["dropped_index"]
    assert stage["schema"]["rules"] == {
        "resume_share_links": {"list": LINK_RULE, "view": LINK_RULE, "create": None, "update": None, "delete": None},
        "resume_share_views": {"list": VIEW_RULE, "view": VIEW_RULE, "create": None, "update": None, "delete": None},
    }
    keys = {w["collection"] + ":" + ",".join(w.get("payload_keys", w.get("fields", []))) for w in
            stage["server_row_writes"] + stage["user_row_writes"]}
    assert "relation_quarantine:token,password_hash,expires_at" in keys
    assert "relation_quarantine:viewer_ip_hash,user_agent,viewed_at" in keys
    assert "resume_share_views:viewer_ip_hash,user_agent,viewed_at" in keys


def test_the_header_and_the_code_state_the_same_rules(src):
    header = src[: src.index("const MANIFEST")]
    up = src[src.index("migrate(") : src.index("  (db) => {\n    const dao = new Dao(db);\n    const links = dao.findCollectionByNameOrId(LINKS);")]
    for rule in (LINK_RULE, VIEW_RULE):
        assert rule in header
    assert up.count(f"Rule = '{LINK_RULE}';") == 2 and up.count(f"Rule = '{VIEW_RULE}';") == 2
    for collection in ("links", "views"):
        for rule in ("createRule", "updateRule", "deleteRule"):
            assert f"{collection}.{rule} = null;" in up


def test_the_lint_finds_only_the_reviewed_rules_and_the_entry_waits_on_the_owner(src):
    assert {rule for rule, _line in lm.scan(src)} == {"drops-field", "rewrites-rows"}
    change = lm.Change("A", f"pocketbase/pb_migrations/{NAME}.js", content=src)
    blocking, allowed = lm.lint([change], lm.load_allowlist(ALLOWLIST))
    assert blocking == [] and {f.rule for f in allowed} == {"drops-field", "rewrites-rows"}
    (entry,) = [e for e in json.loads(ALLOWLIST.read_text())["entries"] if e["path"].endswith(f"{NAME}.js")]
    assert entry["sha256"] == lm.sha256(src)
    assert entry["rules"] == ["drops-field", "rewrites-rows"] and entry["issue"] == "#14"
    assert entry["reviewed_by"] == "pending owner review"
    assert (ROOT / entry["manifest"]) == MANIFEST


def test_down_keeps_the_journal_rules_status_and_replacement_and_adds_the_fields_back_empty(src):
    down = src[src.index("  (db) => {\n    const dao = new Dao(db);\n    const links = dao.findCollectionByNameOrId(LINKS);"):]
    down = down[: down.index("\n);\n")]
    # No rule, no journal, no trigger, and no row is touched: only fields.
    assert "Rule" not in down and "deleteCollection" not in down and "newQuery" not in down
    assert "ADDED_ONLY_FORWARD" in down and "DROPPED" in down and "required: false" in down
    assert "idx_share_links_token" not in down and "indexes" not in down
    added_only = re.search(r"const ADDED_ONLY_FORWARD = \[(.*?)\];", src, re.S).group(1)
    assert re.findall(r'"([a-z_]+)"', added_only) == ["legacy_reason", "turned_off_at", "manifest_id"]


def test_the_journal_and_the_new_relation_are_server_only(src, constants):
    assert constants["fields"] == [{"c": "resume_share_links", "f": "replaced_by", "t": "share_capabilities",
                                    "required": False, "cascade": True}]
    journal = src[src.index("new Collection({"): src.index("indexes: [\"CREATE UNIQUE INDEX idx_legacy_share_migration_link")]
    for rule in ("listRule", "viewRule", "createRule", "updateRule", "deleteRule"):
        assert f"{rule}: null," in journal
    assert 'type: "json"' not in src


def test_the_policy_rows_carry_the_migrations_rules():
    rows = json.loads(POLICY.read_text())["collections"]
    links, views = rows["resume_share_links"], rows["resume_share_views"]
    assert links["current_rules"] == {"list": LINK_RULE, "view": LINK_RULE, "create": None, "update": None,
                                      "delete": None}
    assert views["current_rules"] == {"list": VIEW_RULE, "view": VIEW_RULE, "create": None, "update": None,
                                      "delete": None}
    for row in (links, views):
        assert {"migration": f"{NAME}.js", "rules": ["list", "view", "create", "update", "delete"]} in row["rule_overrides"]
