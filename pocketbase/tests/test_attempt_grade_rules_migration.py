"""Graded attempt rows are the server's (ROUNDS-00A-L03 PR 4).

Static checks on 1700008700_attempt_grade_rules.js, plus runs of its up()
and down() against a stubbed Dao through node, as
test_grading_review_migration.py does: up sets the two rules on both
attempt collections and records the ones it replaced once, a missing
collection fails it before it changes either, and down() changes nothing.
The rules agree with docs/security/account-scope.v1.json and with the
manifest, whose record of the rules replaced is checked against
1700006000_account_scope_rules.js. The migration runs on a real pb_data in
the harness's dry run (phase 16), and the two-account harness proves the
live rules refuse each client write to a graded row."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "pocketbase" / "pb_migrations"
MIGRATION = MIGRATIONS / "1700008700_attempt_grade_rules.js"
OWNERSHIP = MIGRATIONS / "1700006000_account_scope_rules.js"
MANIFEST = ROOT / "pocketbase" / "migration-manifests" / "attempt-grade-rules-v1.json"
POLICY = ROOT / "docs" / "security" / "account-scope.v1.json"
COLLECTIONS = ["ai_coding_attempts", "take_home_attempts"]


@pytest.fixture(scope="module")
def src() -> str:
    return MIGRATION.read_text()


def _ownership_rule(name: str) -> str:
    found = re.search(rf"const {name} =\s*'([^']*)'", OWNERSHIP.read_text(), re.DOTALL)
    assert found, name
    return found.group(1)


_HARNESS = r"""
const [migrationPath, before] = process.argv.slice(2);
let up, down;
globalThis.migrate = (u, d) => { up = u; down = d; };
const db = { collections: {}, saves: [], params: {} };
for (const [name, rules] of Object.entries(JSON.parse(before))) {
  if (process.env.MISSING === name) continue;
  db.collections[name] = { name, listRule: "list", viewRule: "view", deleteRule: "delete", ...rules };
}
function Dao(d) {
  this.findCollectionByNameOrId = (n) => {
    const c = d.collections[n];
    if (!c) throw new Error("missing collection " + n);
    return c;
  };
  this.saveCollection = (c) => d.saves.push(c.name);
  this.saveParam = (key, value) => { d.params[key] = JSON.parse(JSON.stringify(value)); };
}
globalThis.Dao = Dao;
const dump = () => JSON.parse(JSON.stringify(db.collections));
require(migrationPath);
let upError = null;
try { up(db); } catch (err) { upError = String(err && err.message); }
const afterUp = dump();
const saves = db.saves.slice();
const params = JSON.parse(JSON.stringify(db.params));
let twice = null;
let afterDown = null;
if (!upError) {
  down(db);
  afterDown = dump();
  up(db);
  twice = { collections: dump(), saves: db.saves.slice(saves.length), params: db.params };
}
process.stdout.write(JSON.stringify({ upError, up: afterUp, saves, params, down: afterDown, twice }));
"""


def _run(tmp_path_factory, missing: str = "") -> dict:
    node = shutil.which("node")
    assert node, "node is required for the PocketBase migration checks; CI installs it"
    harness = tmp_path_factory.mktemp("grade-rules") / "harness.cjs"
    harness.write_text(_HARNESS)
    before = {name: {"createRule": _ownership_rule("CREATE_RULE"), "updateRule": _ownership_rule("UPDATE_RULE")}
              for name in COLLECTIONS}
    res = subprocess.run([node, str(harness), str(MIGRATION), json.dumps(before)], capture_output=True, text=True,
                         timeout=60, env={"PATH": "", "MISSING": missing})
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


@pytest.fixture(scope="module")
def run(tmp_path_factory) -> dict:
    return _run(tmp_path_factory)


def test_the_file_is_a_migration_that_sorts_after_the_rules_and_the_link_it_builds_on(src):
    assert src.lstrip().startswith("/// <reference") and "migrate(" in src
    names = sorted(p.name for p in MIGRATIONS.glob("*.js") if p.name.startswith("17000"))
    assert names.index(MIGRATION.name) > names.index(OWNERSHIP.name)
    # The envelope link comes with the job store (ROUNDS-00A-L03 PR 1).
    assert names.index(MIGRATION.name) > names.index("1700007100_execution_jobs.js")


def test_neither_step_reads_or_writes_a_record(src):
    for call in ("saveRecord", "deleteRecord", "findRecordsByFilter", "findFirstRecordByData", "new Record(",
                 "newQuery", "deleteCollection", "removeField", "findParamByKey"):
        assert call not in src, call


def test_the_migration_lint_finds_nothing(src):
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import lint_migrations
    finally:
        sys.path.pop(0)
    assert lint_migrations.scan(src) == []


def test_up_sets_both_rules_on_both_collections_and_nothing_else(run):
    assert run["upError"] is None and run["saves"] == COLLECTIONS
    rules = {(c["createRule"], c["updateRule"]) for c in run["up"].values()}
    assert len(rules) == 1
    for collection in run["up"].values():
        assert (collection["listRule"], collection["viewRule"], collection["deleteRule"]) == ("list", "view", "delete")


def test_up_records_the_rules_it_replaced_once(run):
    record = run["params"][MIGRATION.name]
    assert record == [{"collection": name, "create": _ownership_rule("CREATE_RULE"),
                       "update": _ownership_rule("UPDATE_RULE")} for name in COLLECTIONS]
    # down() keeps the rules and the record; up again changes and records
    # nothing, so the first record stands.
    assert run["down"] == run["up"]
    assert run["twice"]["saves"] == [] and run["twice"]["collections"] == run["up"]
    assert run["twice"]["params"][MIGRATION.name] == record


@pytest.mark.parametrize("missing", COLLECTIONS)
def test_a_missing_collection_fails_up_before_it_changes_either(tmp_path_factory, missing):
    out = _run(tmp_path_factory, missing=missing)
    assert out["upError"] and "missing collection" in out["upError"]
    assert out["saves"] == [] and out["params"] == {}


def test_the_rules_keep_the_ownership_clauses_and_name_the_open_statuses(run):
    collection = run["up"]["ai_coding_attempts"]
    create, update = collection["createRule"], collection["updateRule"]
    # Signed in, and the row is the caller's, as 1700006000 has it.
    assert create.startswith('@request.auth.id != "" && ') and create.endswith("@request.auth.id = @request.data.user")
    assert "user = @request.auth.id" in update and "@request.data.user:isset = false" in update
    # A stored graded row takes no update at all.
    assert update.startswith('status != "graded" && ')
    for rule in (create, update):
        assert "@request.data.envelope:isset = false" in rule
        # The statuses a client may send, never only the one it may not.
        assert '@request.data.status = "in-progress" || @request.data.status = "submitted"' in rule
        assert "@request.data.status !=" not in rule
    assert "@request.data.status:isset = false" in update


def test_the_policy_and_the_manifest_hold_the_same_rules(run):
    policy = json.loads(POLICY.read_text())
    manifest = json.loads(MANIFEST.read_text())
    assert sorted(manifest["collections"]) == COLLECTIONS and manifest["rows_touched"] == 0
    assert manifest["journal"]["param"] == MIGRATION.name
    for name in COLLECTIONS:
        live = run["up"][name]
        row = policy["collections"][name]
        for key, field in (("create", "createRule"), ("update", "updateRule")):
            assert row["current_rules"][key] == row["target_rules"][key] == live[field], (name, key)
            assert manifest["collections"][name]["after"][key] == live[field], (name, key)
            want = hashlib.sha256(_ownership_rule(f"{key.upper()}_RULE").encode()).hexdigest()
            assert manifest["collections"][name]["before"][f"{key}_sha256"] == want, (name, key)
        assert {"migration": MIGRATION.name, "rules": ["create", "update"]} in row["rule_overrides"]
        # The client-graded exception is closed by this.
        assert all(e["id"] != "client-graded-status" for e in row["exceptions"])
        for family in ("account-scope.create.graded.denied", "account-scope.update.graded.denied"):
            assert family in row["probes"] and policy["probe_families"][family]["status"] == "enforced"
