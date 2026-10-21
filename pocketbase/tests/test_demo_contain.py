"""The demo containment migration (ROUNDS-00B-L07 stage 1).

1700006700_demo_contain.js deletes what accounts with users.is_demo own in
resume_share_links (their views cascade), ai_settings, and ai_providers,
and nothing else. Its up() and down() run through node against a stub Dao;
its lint entry is pinned to the file and waits on the owner's review; and
manifest demo-contain-v1 names the same deletes. #9's harness runs the
migration on real databases with the rest.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
NAME = "1700006700_demo_contain"
MIGRATION = ROOT / "pocketbase" / "pb_migrations" / f"{NAME}.js"
MANIFEST = ROOT / "pocketbase" / "migration-manifests" / "demo-contain-v1.json"
ALLOWLIST = ROOT / "scripts" / "migration-lint-allowlist.json"
CONTAINED = ["resume_share_links", "ai_settings", "ai_providers"]

sys.path.insert(0, str(ROOT / "scripts"))
try:
    import lint_migrations as lm
finally:
    sys.path.pop(0)


@pytest.fixture(scope="module")
def src() -> str:
    return MIGRATION.read_text()


def test_the_file_is_a_migration(src):
    assert src.lstrip().startswith("/// <reference")
    assert "migrate(" in src


def test_the_lint_finds_only_the_reviewed_deletes(src):
    assert [rule for rule, _line in lm.scan(src)] == ["rewrites-rows"]
    change = lm.Change("A", f"pocketbase/pb_migrations/{NAME}.js", content=src)
    blocking, allowed = lm.lint([change], lm.load_allowlist(ALLOWLIST))
    assert blocking == [] and [f.rule for f in allowed] == ["rewrites-rows"]


def test_the_lint_entry_is_pinned_to_this_file_and_waits_on_the_owner(src):
    (entry,) = [e for e in json.loads(ALLOWLIST.read_text())["entries"] if e["path"].endswith(f"{NAME}.js")]
    assert entry["sha256"] == lm.sha256(src)
    assert entry["rules"] == ["rewrites-rows"] and entry["issue"] == "#177"
    assert entry["reviewed_by"] == "pending owner review"
    assert (ROOT / entry["manifest"]) == MANIFEST


def test_the_manifest_names_the_migrations_deletes_and_nothing_else():
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["manifest"] == "demo-contain-v1" and manifest["issue"] == "#177"
    assert manifest["owner_approval"] == "pending owner review"
    (stage,) = [m for m in manifest["migrations"] if m["migration"] == NAME]
    assert [d["collection"] for d in stage["deletes"]] == ["resume_share_links", "ai_settings", "ai_providers"]
    assert all(d["disposition"] == "drop" and d["owner_field"] == "user" for d in stage["deletes"])
    (views,) = stage["deletes"][0]["with"]
    assert views["collection"] == "resume_share_views" and views["via"] == "link"
    assert stage["user_row_writes"] == []


def test_the_views_cascade_from_their_link():
    studio = (ROOT / "pocketbase" / "pb_migrations" / "1700000700_resume_studio.js").read_text()
    views = studio[studio.index('name: "resume_share_views"'):]
    link = views[views.index('name: "link"'):]
    assert "collectionId: shareLinks.id, cascadeDelete: true" in link[:200]


# ---- behavioural: up() and down() through node against a stub Dao ---------

_HARNESS = r"""
const [migrationPath, raw] = process.argv.slice(2);
let up, down;
globalThis.migrate = (u, d) => { up = u; down = d; };
const plan = JSON.parse(raw);
function record(collection, row) {
  return { id: row.id, collection, getBool: (n) => row[n] === true, getString: (n) => row[n] || "" };
}
const db = { deleted: [], queries: [] };
globalThis.Dao = function () {
  this.findRecordsByFilter = (name, filter, sort, limit, offset, params) => {
    db.queries.push({ name, filter, params: params || null });
    const rows = (plan[name] || []).map((row) => record(name, row));
    if (filter === "is_demo = true") return rows.filter((r) => r.getBool("is_demo"));
    if (filter === "user = {:user}") return rows.filter((r) => r.getString("user") === params.user);
    throw new Error("unexpected filter " + filter);
  };
  this.deleteRecord = (r) => { db.deleted.push(r.collection + ":" + r.id); };
  this.saveRecord = () => { throw new Error("no saves"); };
  this.saveCollection = () => { throw new Error("no schema changes"); };
  this.deleteCollection = () => { throw new Error("no schema changes"); };
};
require(migrationPath);
up({});
const afterUp = { deleted: db.deleted.slice(), queries: db.queries.slice() };
db.deleted = []; db.queries = [];
down({});
process.stdout.write(JSON.stringify({ up: afterUp, down: { deleted: db.deleted, queries: db.queries } }));
"""

PLAN = {
    "users": [
        {"id": "demo00000000001", "is_demo": True},
        {"id": "demo00000000002", "is_demo": True},
        {"id": "user00000000001", "is_demo": False},
    ],
    "resume_share_links": [
        {"id": "link0000000000a", "user": "demo00000000001"},
        {"id": "link0000000000b", "user": "user00000000001"},
    ],
    "ai_settings": [
        {"id": "sets0000000000a", "user": "demo00000000001"},
        {"id": "sets0000000000b", "user": "demo00000000002"},
        {"id": "sets0000000000c", "user": "user00000000001"},
    ],
    "ai_providers": [
        {"id": "prov0000000000a", "user": "demo00000000001"},
        {"id": "prov0000000000b", "user": "user00000000001"},
    ],
    "todos": [{"id": "todo0000000000a", "user": "demo00000000001"}],
}


@pytest.fixture(scope="module")
def run(tmp_path_factory) -> dict:
    node = shutil.which("node")
    assert node, "node is required for the PocketBase migration checks; CI installs it"
    harness = tmp_path_factory.mktemp("demo-contain") / "harness.cjs"
    harness.write_text(_HARNESS)
    res = subprocess.run([node, str(harness), str(MIGRATION), json.dumps(PLAN)], capture_output=True, text=True,
                         timeout=60)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def test_up_deletes_what_demo_accounts_own_there_settings_before_providers(run):
    assert run["up"]["deleted"] == [
        "resume_share_links:link0000000000a",
        "ai_settings:sets0000000000a",
        "ai_providers:prov0000000000a",
        "ai_settings:sets0000000000b",
    ]


def test_up_reads_only_demo_accounts_rows_in_the_three_collections(run):
    # The exact list above already leaves every standard row and the todo.
    assert {q["name"] for q in run["up"]["queries"]} == {"users", *CONTAINED}
    for query in run["up"]["queries"]:
        if query["name"] != "users":
            assert query["params"]["user"].startswith("demo"), query


def test_down_changes_nothing(run):
    assert run["down"] == {"deleted": [], "queries": []}
