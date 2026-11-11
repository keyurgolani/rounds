"""The rubric review's admission operation (ROUNDS-00A-L03 PR 3).

Static checks on 1700008400_grading_review.js, plus a run of its up() and
down() against a stubbed Dao through node, as
test_share_secrets_migration.py does: `review` joins the `operation` list
of admission_commands and admission_leases once, nothing else changes, and
down() takes it off again. pb_hooks/admission.js's operation table is
checked against it, so the two stay in step. The migration also runs on
real databases in #9's harness and in harness/migration_check.sh."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "pocketbase" / "pb_migrations" / "1700008400_grading_review.js"
HOOKS = ROOT / "pocketbase" / "pb_hooks"
COMMANDS_BEFORE = ["run", "evaluate", "run_project", "grade", "take_home_run", "take_home_submit", "pdf_render",
                   "snapshot_create", "share_create", "share_rotate"]
LEASES_BEFORE = ["run", "evaluate", "run_project", "grade", "take_home_run", "take_home_submit", "pdf_render"]


@pytest.fixture(scope="module")
def src() -> str:
    return MIGRATION.read_text()


def test_the_file_is_a_migration_that_sorts_after_the_stores_it_changes(src):
    assert src.lstrip().startswith("/// <reference")
    assert "migrate(" in src
    names = sorted(p.name for p in MIGRATION.parent.glob("*.js") if p.name.startswith("17000"))
    assert names.index(MIGRATION.name) > names.index("1700006100_admission.js")
    assert names.index(MIGRATION.name) > names.index("1700008300_share_secrets.js")


def test_neither_step_reads_or_writes_a_record(src):
    for call in ("saveRecord", "deleteRecord", "findRecordsByFilter", "findFirstRecordByData", "new Record(",
                 "newQuery", "deleteCollection", "removeField"):
        assert call not in src, call


def test_the_migration_lint_finds_nothing(src):
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import lint_migrations
    finally:
        sys.path.pop(0)
    assert lint_migrations.scan(src) == []


_HARNESS = r"""
const [migrationPath, hooksDir, commandsJson, leasesJson] = process.argv.slice(2);
let up, down;
globalThis.migrate = (u, d) => { up = u; down = d; };
function Schema(fields) {
  this.items = fields.map((f) => JSON.parse(JSON.stringify(f)));
  this.getFieldByName = (n) => this.items.find((f) => f.name === n) || null;
}
const db = { collections: {}, saves: [] };
const add = (name, values, missing) => {
  if (missing) return;
  db.collections[name] = {
    name,
    schema: new Schema([
      { name: "command", type: "text", options: {} },
      { name: "operation", type: "select", required: true, options: { maxSelect: 1, values } },
    ]),
  };
};
function Dao(d) {
  this.findCollectionByNameOrId = (n) => {
    const c = d.collections[n];
    if (!c) throw new Error("missing collection " + n);
    return c;
  };
  this.saveCollection = (c) => d.saves.push(c.name);
}
globalThis.Dao = Dao;
const dump = () => JSON.parse(JSON.stringify(
  Object.fromEntries(Object.entries(db.collections).map(([name, c]) => [name, c.schema.items]))));
const missing = process.env.MISSING || "";
add("admission_commands", JSON.parse(commandsJson), missing === "admission_commands");
add("admission_leases", JSON.parse(leasesJson), missing === "admission_leases");
require(migrationPath);
let upError = null;
try { up(db); } catch (err) { upError = String(err && err.message); }
const afterUp = dump();
const saves = db.saves.slice();
const twice = (() => { if (upError) return null; up(db); return dump(); })();
if (!upError) down(db);
globalThis.__hooks = hooksDir;
const admission = require(require("path").join(hooksDir, "admission.js"));
process.stdout.write(JSON.stringify({
  up: afterUp, twice, saves, upError, down: dump(),
  hook: { operations: Object.keys(admission.OPERATIONS), hookOnly: admission.HOOK_ONLY_OPERATIONS },
}));
"""


def _run(tmp_path_factory, missing: str = "") -> dict:
    node = shutil.which("node")
    assert node, "node is required for the PocketBase migration checks; CI installs it"
    harness = tmp_path_factory.mktemp("grading-review") / "harness.cjs"
    harness.write_text(_HARNESS)
    res = subprocess.run([node, str(harness), str(MIGRATION), str(HOOKS), json.dumps(COMMANDS_BEFORE),
                          json.dumps(LEASES_BEFORE)], capture_output=True, text=True, timeout=60,
                         env={"PATH": "", "MISSING": missing})
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


@pytest.fixture(scope="module")
def run(tmp_path_factory) -> dict:
    return _run(tmp_path_factory)


def _values(state: dict, collection: str) -> list[str]:
    (field,) = [f for f in state[collection] if f["name"] == "operation"]
    return field["options"]["values"]


def test_up_lists_review_once_on_both_and_changes_nothing_else(run):
    assert run["upError"] is None
    assert _values(run["up"], "admission_commands") == [*COMMANDS_BEFORE, "review"]
    assert _values(run["up"], "admission_leases") == [*LEASES_BEFORE, "review"]
    assert run["saves"] == ["admission_commands", "admission_leases"]
    for name in ("admission_commands", "admission_leases"):
        (other,) = [f for f in run["up"][name] if f["name"] == "command"]
        assert other == {"name": "command", "type": "text", "options": {}}
    # Applied again, it lists review once.
    assert _values(run["twice"], "admission_commands") == [*COMMANDS_BEFORE, "review"]


def test_down_takes_review_off_both_lists_again(run):
    assert _values(run["down"], "admission_commands") == COMMANDS_BEFORE
    assert _values(run["down"], "admission_leases") == LEASES_BEFORE


@pytest.mark.parametrize("missing", ["admission_commands", "admission_leases"])
def test_a_missing_store_fails_up_before_it_changes_either(tmp_path_factory, missing):
    out = _run(tmp_path_factory, missing=missing)
    assert out["upError"] and "missing collection" in out["upError"]
    assert out["saves"] == []


def test_the_hooks_charge_the_operation_this_lists(run):
    assert "review" in run["hook"]["operations"] and run["hook"]["hookOnly"] == ["review"]
