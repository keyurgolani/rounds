"""The demo containment migration (ROUNDS-00B-L07 stage 1).

1700006700_demo_contain.js deletes what accounts with users.is_demo own in
resume_share_links (their views cascade), ai_settings, and ai_providers,
keeps a demo provider another account's settings point at with its key
cleared, and writes no row a standard account owns. Its up() and down() run
through node against a stub Dao;
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
    # Two deletes and the provider key clear.
    assert [rule for rule, _line in lm.scan(src)] == ["rewrites-rows"] * 3
    change = lm.Change("A", f"pocketbase/pb_migrations/{NAME}.js", content=src)
    blocking, allowed = lm.lint([change], lm.load_allowlist(ALLOWLIST))
    assert blocking == [] and {f.rule for f in allowed} == {"rewrites-rows"}


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
    (write,) = stage["user_row_writes"]
    assert write["collection"] == "ai_providers" and write["disposition"] == "clear"
    assert write["fields"] == ["encrypted_key", "key_iv"]


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
// One live table per collection, so a delete is seen by later queries.
const tables = {};
Object.entries(plan).forEach(([name, rows]) => { tables[name] = rows.map((row) => Object.assign({}, row)); });
function record(collection, row) {
  return {
    id: row.id, collection, row,
    getBool: (n) => row[n] === true,
    getString: (n) => row[n] || "",
    set: (n, v) => { row["set:" + n] = v; },
  };
}
const db = { deleted: [], saved: [], queries: [] };
globalThis.Dao = function () {
  this.findRecordsByFilter = (name, filter, sort, limit, offset, params) => {
    db.queries.push({ name, filter, params: params || null });
    const rows = (tables[name] || []).map((row) => record(name, row));
    let out;
    if (filter === "is_demo = true") out = rows.filter((r) => r.getBool("is_demo"));
    else if (filter === "user = {:user}") out = rows.filter((r) => r.getString("user") === params.user);
    else if (filter === "text_provider = {:provider} || vision_provider = {:provider}") {
      out = rows.filter((r) => r.getString("text_provider") === params.provider
        || r.getString("vision_provider") === params.provider);
    } else throw new Error("unexpected filter " + filter);
    return limit ? out.slice(0, limit) : out;
  };
  this.deleteRecord = (r) => {
    // PocketBase refuses to delete a row a non-cascading reference still names.
    const named = (tables.ai_settings || []).some((s) => s.text_provider === r.id || s.vision_provider === r.id);
    if (r.collection === "ai_providers" && named) throw new Error("would rewrite a referencing row");
    tables[r.collection] = tables[r.collection].filter((row) => row.id !== r.id);
    db.deleted.push(r.collection + ":" + r.id);
  };
  this.saveRecord = (r) => {
    const sets = Object.keys(r.row).filter((k) => k.startsWith("set:")).sort();
    db.saved.push({ id: r.collection + ":" + r.id, sets: sets.map((k) => k.slice(4) + "=" + JSON.stringify(r.row[k])) });
  };
  this.saveCollection = () => { throw new Error("no schema changes"); };
  this.deleteCollection = () => { throw new Error("no schema changes"); };
};
require(migrationPath);
up({});
const afterUp = { deleted: db.deleted.slice(), saved: db.saved.slice(), queries: db.queries.slice() };
db.deleted = []; db.saved = []; db.queries = [];
down({});
process.stdout.write(JSON.stringify({ up: afterUp, down: db }));
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
        # A demo account's settings may name another demo account's provider.
        {"id": "sets0000000000a", "user": "demo00000000001", "text_provider": "prov0000000000a"},
        {"id": "sets0000000000b", "user": "demo00000000002", "vision_provider": "prov0000000000a"},
        # A standard account's settings that name a demo provider.
        {"id": "sets0000000000c", "user": "user00000000001", "text_provider": "prov0000000000c",
         "vision_provider": "prov0000000000d"},
    ],
    "ai_providers": [
        {"id": "prov0000000000a", "user": "demo00000000001"},
        {"id": "prov0000000000b", "user": "user00000000001"},
        {"id": "prov0000000000c", "user": "demo00000000002", "encrypted_key": "ciphertext", "key_iv": "iv"},
        # One a run before this already cleared: not written again.
        {"id": "prov0000000000d", "user": "demo00000000002"},
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


def test_up_deletes_what_demo_accounts_own_there_every_settings_row_before_any_provider(run):
    assert run["up"]["deleted"] == [
        "resume_share_links:link0000000000a",
        "ai_settings:sets0000000000a",
        "ai_settings:sets0000000000b",
        "ai_providers:prov0000000000a",
    ]


def test_a_demo_provider_another_account_points_at_keeps_its_row_without_its_key(run):
    # Its row stays so the standard account's settings aren't rewritten
    # here, and one already without a key isn't saved again.
    assert "ai_providers:prov0000000000d" not in run["up"]["deleted"]
    assert run["up"]["saved"] == [
        {"id": "ai_providers:prov0000000000c", "sets": ['encrypted_key=""', 'key_iv=""']},
    ]


def test_up_writes_no_standard_row(run):
    standard = {f"{name}:{row['id']}" for name, rows in PLAN.items() if name != "users"
                for row in rows if row.get("user") == "user00000000001"}
    touched = set(run["up"]["deleted"]) | {s["id"] for s in run["up"]["saved"]}
    assert standard == {"resume_share_links:link0000000000b", "ai_settings:sets0000000000c",
                        "ai_providers:prov0000000000b"}
    assert not standard & touched


def test_up_reads_only_demo_accounts_rows_in_the_three_collections(run):
    # The exact list above already leaves every standard row and the todo.
    assert {q["name"] for q in run["up"]["queries"]} == {"users", *CONTAINED}
    for query in run["up"]["queries"]:
        if query["name"] == "users":
            continue
        if "user" in query["params"]:
            assert query["params"]["user"].startswith("demo"), query
        else:
            assert query["name"] == "ai_settings" and query["params"]["provider"].startswith("prov"), query


def test_down_changes_nothing(run):
    assert run["down"] == {"deleted": [], "saved": [], "queries": []}
