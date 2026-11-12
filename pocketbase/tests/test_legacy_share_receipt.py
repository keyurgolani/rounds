"""The older share links' receipt (ROUNDS-00B-L06 stage 1).

pocketbase legacy-share-receipt reports the migration's journal and what
the share collections and relation_quarantine hold now. receipt() runs here
under node (legacy_shares_runner.cjs) over plain inputs: it counts by
outcome and reason, counts incidents and links given a new link, counts
anything left of an old link's secret or its viewers' details, checksums
the journal without its dates, and reconciles. It holds no id. The runner
signs it (backend/tests/test_legacy_receipt.py); harness phase 15 runs the
command on real databases.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / "pocketbase" / "pb_hooks"
MIGRATIONS = ROOT / "pocketbase" / "pb_migrations"
RUNNER = ROOT / "pocketbase" / "tests" / "legacy_shares_runner.cjs"

LINKS = [f"link{n:011d}" for n in range(6)]
SECRET = "AbCdEfGhIjKlMnOpQrSt_-"


def run(*steps: dict) -> list:
    node = shutil.which("node")
    assert node, "node is required for the PocketBase hook checks; CI installs it"
    res = subprocess.run([node, str(RUNNER), str(HOOKS), str(MIGRATIONS)], input=json.dumps({"steps": list(steps)}),
                         capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)["results"]


def journal_row(n: int, outcome: str, reason: str, origin: str = "live", views: int = 0, incident: bool = False):
    return {"id": LINKS[n], "manifest": "legacy-shares-v1", "predicate_version": 1, "link": LINKS[n],
            "origin": origin, "quarantine_entry": "" if origin == "live" else f"q{n:014d}", "outcome": outcome,
            "reason": reason, "views": views, "first_view_day": "2024-01-02" if views else "",
            "last_view_day": "2024-02-03" if views else "", "incident": incident}


def migrated_input(**over) -> dict:
    """What the store reads right after a clean migration: four live links
    and one quarantined one."""
    data = {
        "journal": [
            journal_row(0, "migrated", "eligible", views=3),
            journal_row(1, "migrated", "eligible"),
            journal_row(2, "revoked_unverified", "token_format"),
            journal_row(3, "revoked_demo", "demo_account"),
            journal_row(4, "revoked_ownership", "quarantined_cross_owner", origin="quarantine", views=2, incident=True),
        ],
        "links": [
            {"id": LINKS[0], "status": "migrated", "replaced": True},
            {"id": LINKS[1], "status": "migrated", "replaced": False},
            {"id": LINKS[2], "status": "revoked_unverified", "replaced": False},
            {"id": LINKS[3], "status": "revoked_demo", "replaced": False},
        ],
        "linkColumns": ["user", "resume", "variant", "legacy_status", "legacy_reason", "turned_off_at", "manifest_id",
                        "replaced_by"],
        "linkEntries": [{"link": LINKS[4], "secret_keys": 0}],
        "viewRows": {"rows": 3, "detailed": 0},
        "viewEntries": {"entries": 2, "detailed": 0},
        "commit": "v0.1.3",
        "unavailable": None,
    }
    data.update(over)
    return data


def receipt(data: dict) -> dict:
    (out,) = run({"call": "receipt", "input": data})
    return out


def canonical(value) -> str:
    """Sorted keys, no spaces: #4's canonical() for these values."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def test_a_clean_migration_reconciles_and_counts_each_outcome_reason_and_incident():
    out = receipt(migrated_input())
    assert out["schema"] == "legacy-share-receipt/v1" and out["manifest"] == "legacy-shares-v1"
    assert out["reconciled"] is True
    assert out["outcomes"] == {"migrated": 2, "revoked_ownership": 1, "revoked_demo": 1, "revoked_unverified": 1}
    assert out["reasons"]["eligible"] == 2 and out["reasons"]["quarantined_cross_owner"] == 1
    assert sum(out["reasons"].values()) == 5
    assert out["links"] == {"journaled": 5, "live": 4, "quarantined": 1, "now": 4}
    assert (out["incidents"], out["reissued"]) == (1, 1)
    assert out["views"] == {"counted": 5, "rows_now": 3, "quarantined_entries": 2}
    assert out["left"] == {"link_fields": 0, "quarantined_link_secrets": 0, "view_details": 0,
                           "quarantined_view_details": 0}
    assert out["commit"] == "v0.1.3" and out["unavailable"] is None


def test_every_reason_code_is_counted_even_at_zero():
    out = receipt(migrated_input())
    assert sorted(out["reasons"]) == sorted(
        ["eligible", "target_owner", "parent_owner", "quarantined_cross_owner", "quarantined_missing_target",
         "quarantined_dependent", "quarantined_other", "demo_account", "owner_missing", "no_target",
         "target_missing", "token_format", "password_set", "expiry_set"])


def test_the_checksums_cover_the_receipt_and_the_journal_without_its_dates():
    data = migrated_input()
    out = receipt(data)
    body = {k: v for k, v in out.items() if k != "checksum"}
    assert out["checksum"] == "sha256:" + hashlib.sha256(canonical(body).encode()).hexdigest()
    rows = sorted(data["journal"], key=lambda r: r["id"])
    assert out["journal"] == {"rows": 5, "checksum": "sha256:" + hashlib.sha256(canonical(rows).encode()).hexdigest()}
    dated = migrated_input(journal=[dict(r, created="2026-11-11 12:00:00.000Z") for r in data["journal"]])
    assert receipt(dated)["journal"] == out["journal"]


def test_the_same_journal_in_any_order_gives_the_same_receipt():
    data = migrated_input()
    flipped = migrated_input(journal=list(reversed(data["journal"])))
    assert receipt(flipped) == receipt(data)


def test_a_new_link_after_the_dry_run_changes_only_the_reissued_count():
    before = receipt(migrated_input(links=[dict(link, replaced=False) for link in migrated_input()["links"]]))
    after = receipt(migrated_input())
    assert before["journal"] == after["journal"] and before["outcomes"] == after["outcomes"]
    assert (before["reissued"], after["reissued"]) == (0, 1)


@pytest.mark.parametrize("over, why", [
    ({"linkColumns": ["user", "resume", "token"]}, "link_fields"),
    ({"linkEntries": [{"link": LINKS[4], "secret_keys": 2}]}, "quarantined_link_secrets"),
    ({"viewRows": {"rows": 3, "detailed": 1}}, "view_details"),
    ({"viewEntries": {"entries": 2, "detailed": 1}}, "quarantined_view_details"),
])
def test_anything_left_of_an_old_links_secret_or_its_viewers_fails_reconciliation(over, why):
    out = receipt(migrated_input(**over))
    assert out["reconciled"] is False and out["left"][why] > 0


@pytest.mark.parametrize("change", [
    {"links": migrated_input()["links"] + [{"id": LINKS[5], "status": "migrated", "replaced": False}]},
    {"links": [dict(migrated_input()["links"][0], status="revoked_unverified")] + migrated_input()["links"][1:]},
    {"linkEntries": [{"link": LINKS[5], "secret_keys": 0}]},
    {"journal": migrated_input()["journal"] + [journal_row(5, "turned_on", "eligible")]},
    {"journal": migrated_input()["journal"] + [journal_row(5, "migrated", "made_up")]},
    {"journal": migrated_input()["journal"][:4] + [dict(journal_row(4, "revoked_ownership", "quarantined_cross_owner",
                                                                    origin="quarantine", views=2, incident=True),
                                                         id="j00000000000004")]},
], ids=["a-link-not-journaled", "a-status-unlike-its-journal", "a-quarantined-link-not-journaled",
        "an-unknown-outcome", "an-unknown-reason", "a-row-not-under-its-links-id"])
def test_a_link_the_journal_doesnt_account_for_fails_reconciliation(change):
    assert receipt(migrated_input(**change))["reconciled"] is False


def test_the_receipt_holds_no_id_secret_or_address():
    data = migrated_input()
    text = json.dumps(receipt(data))
    for value in LINKS + [r["id"] for r in data["journal"]] + [r["quarantine_entry"] for r in data["journal"] if
                                                               r["quarantine_entry"]]:
        assert value not in text
    assert SECRET not in text and not re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", text)


def test_the_scan_counts_come_from_4s_report():
    report = {"totals": {"sources": 4, "resumes": 3, "variants": 1, "eligible": 2, "ineligible": 1, "unavailable": 1},
              "by_reason": {"data_too_large": 1}, "materializer_digest": "sha256:" + "a" * 64, "complete": False,
              "accounts": {"acct-01": {}}, "checksum": "sha256:" + "b" * 64}
    (out,) = run({"call": "unavailableOf", "report": report})
    assert out == {"checked": 4, "ineligible": 1, "unreachable": 1, "by_reason": {"data_too_large": 1},
                   "materializer_digest": "sha256:" + "a" * 64, "complete": False}
    with_scan = receipt(migrated_input(unavailable=out))
    assert with_scan["unavailable"] == out
    assert with_scan["journal"] == receipt(migrated_input())["journal"]


def test_the_command_is_registered_and_its_module_is_not_a_hook_file():
    wiring = (HOOKS / "legacy_shares.pb.js").read_text()
    assert 'use: "legacy-share-receipt"' in wiring and "disableFlagParsing: true" in wiring
    assert "require(`${__hooks}/legacy_shares.js`).receiptCommand(args)" in wiring
    assert not (HOOKS / "legacy_shares.js").name.endswith(".pb.js")


def test_the_command_writes_only_a_new_file_outside_pb_data_with_mode_0600():
    src = (HOOKS / "legacy_shares.js").read_text()
    assert "snapshots.reportPathError(out, $app.dataDir(), cwd)" in src
    assert '"legacy-share-receipt: --out names a file that exists; give a new path"' in src
    assert "$os.writeFile(out, text, 0o600)" in src
