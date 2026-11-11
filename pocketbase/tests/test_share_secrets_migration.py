"""The share secrets migration (ROUNDS-00B-L04).

Static checks on the source, plus a run of its up() and down() against a
stubbed Dao through node, as test_execution_migration.py does: the
share_resolvers auth collection and the share_throttle store, both closed
to every client, the throttle's unique key, the three operations it lists
on admission_commands, and a down() that drops only what up() added. The
values pb_hooks/share_secrets.js holds are checked against it, so the two
stay in step. The migration also runs on real databases in #9's harness and
in harness/migration_check.sh."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "pocketbase" / "pb_migrations" / "1700008300_share_secrets.js"
HOOKS = ROOT / "pocketbase" / "pb_hooks"
BEFORE = ["run", "evaluate", "run_project", "grade", "take_home_run", "take_home_submit", "pdf_render"]
ADDED = ["snapshot_create", "share_create", "share_rotate"]


@pytest.fixture(scope="module")
def src() -> str:
    return MIGRATION.read_text()


def test_the_file_is_a_migration_that_sorts_after_the_stores_it_names(src):
    assert src.lstrip().startswith("/// <reference")
    assert "migrate(" in src
    names = sorted(p.name for p in MIGRATION.parent.glob("*.js") if p.name.startswith("17000"))
    assert names.index(MIGRATION.name) > names.index("1700006100_admission.js")


def test_neither_step_reads_or_writes_a_record(src):
    for call in ("saveRecord", "deleteRecord", "findRecordsByFilter", "findFirstRecordByData", "new Record(",
                 "newQuery"):
        assert call not in src, call


def test_the_migration_lint_finds_nothing(src):
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import lint_migrations
    finally:
        sys.path.pop(0)
    assert lint_migrations.scan(src) == []


# ---- behavioural: up() and down() through node against a stub Dao ---------

_HARNESS = r"""
const [migrationPath, hooksDir, beforeJson] = process.argv.slice(2);
let up, down;
globalThis.migrate = (u, d) => { up = u; down = d; };
let ids = 0;
class Schema {
  constructor(fields) { this.items = []; (fields || []).forEach((f) => this.addField(new SchemaField(f))); }
  addField(f) { if (!f.id) f.id = "f" + String(++ids).padStart(7, "0"); this.items.push(f); }
  getFieldByName(n) { return this.items.find((f) => f.name === n) || null; }
  removeField(id) { this.items = this.items.filter((f) => f.id !== id); }
  fields() { return this.items; }
}
globalThis.SchemaField = function (opts) {
  Object.assign(this, JSON.parse(JSON.stringify(opts)));
  if (this.options === undefined) this.options = {};
};
globalThis.Collection = function (opts) {
  const copy = JSON.parse(JSON.stringify(Object.assign({}, opts, { schema: [] })));
  Object.assign(this, copy);
  this.id = "";
  this.schema = new Schema(opts.schema);
};
function Dao(db) {
  this.findCollectionByNameOrId = (n) => {
    const c = db.collections[n];
    if (!c) throw new Error("missing collection " + n);
    return c;
  };
  this.saveCollection = (c) => {
    if (!c.id) c.id = "c_" + c.name;
    db.collections[c.name] = c;
    db.saves.push(c.name);
  };
  this.deleteCollection = (c) => {
    delete db.collections[c.name];
    db.deleted.push(c.name);
  };
}
globalThis.Dao = Dao;

const db = { collections: {}, saves: [], deleted: [] };
const add = (name, type, fields) => {
  const c = new Collection({ name, type, schema: fields });
  c.id = "c_" + name;
  db.collections[name] = c;
};
add("users", "auth", []);
add("admission_commands", "base", [
  { name: "command_id", type: "text" },
  { name: "operation", type: "select", required: true, options: { maxSelect: 1, values: JSON.parse(beforeJson) } },
]);

function dump() {
  const out = {};
  for (const [name, c] of Object.entries(db.collections)) {
    out[name] = {
      type: c.type, listRule: c.listRule, viewRule: c.viewRule, createRule: c.createRule,
      updateRule: c.updateRule, deleteRule: c.deleteRule, options: c.options || null, indexes: c.indexes || [],
      fields: c.schema.fields().map((f) => ({ name: f.name, type: f.type, required: Boolean(f.required), options: f.options })),
    };
  }
  return JSON.parse(JSON.stringify(out));
}

require(migrationPath);
up(db);
const afterUp = dump();
const saves = db.saves.slice();
down(db);
const afterDown = dump();
// A second down, on a database that already lost both collections.
let secondDown = null;
try { down(db); } catch (err) { secondDown = String(err && err.message); }
globalThis.__hooks = hooksDir;
const secrets = require(require("path").join(hooksDir, "share_secrets.js"));
process.stdout.write(JSON.stringify({
  up: afterUp, saves, down: afterDown, deleted: db.deleted, secondDown,
  hooks: { order: secrets.ORDER, minChars: secrets.SECRET_MIN_CHARS, collection: secrets.COLLECTION, throttle: secrets.THROTTLE },
}));
"""


def _run(tmp_path_factory, before: list[str]) -> dict:
    node = shutil.which("node")
    assert node, "node is required for the PocketBase migration checks; CI installs it"
    harness = tmp_path_factory.mktemp("share-secrets") / "harness.cjs"
    harness.write_text(_HARNESS)
    res = subprocess.run([node, str(harness), str(MIGRATION), str(HOOKS), json.dumps(before)],
                         capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


@pytest.fixture(scope="module")
def run(tmp_path_factory) -> dict:
    return _run(tmp_path_factory, BEFORE)


def _field(collection: dict, name: str) -> dict:
    (field,) = [f for f in collection["fields"] if f["name"] == name]
    return field


RULES = ("listRule", "viewRule", "createRule", "updateRule", "deleteRule")


def test_up_adds_the_two_collections_and_changes_admission_commands(run):
    assert set(run["up"]) == {"users", "admission_commands", "share_resolvers", "share_throttle"}
    assert run["saves"] == ["share_resolvers", "share_throttle", "admission_commands"]


def test_the_resolver_login_is_an_auth_collection_no_client_reaches(run):
    c = run["up"]["share_resolvers"]
    assert c["type"] == "auth" and c["fields"] == []
    assert all(c[rule] is None for rule in RULES)
    assert c["options"]["manageRule"] is None
    # A username login only, with a password at least as long as the secret.
    assert c["options"]["allowUsernameAuth"] is True
    assert c["options"]["allowEmailAuth"] is False and c["options"]["allowOAuth2Auth"] is False
    assert c["options"]["requireEmail"] is False
    assert c["options"]["minPasswordLength"] == run["hooks"]["minChars"] == 32
    assert run["hooks"]["collection"] == "share_resolvers"


def test_the_throttle_store_is_closed_to_every_client_and_holds_only_keyed_counters(run):
    c = run["up"]["share_throttle"]
    assert c["type"] == "base" and run["hooks"]["throttle"] == "share_throttle"
    assert all(c[rule] is None for rule in RULES)
    assert [f["name"] for f in c["fields"]] == ["key", "scope", "window_start", "count"]
    assert _field(c, "key")["options"]["pattern"] == "^[0-9a-f]{64}$" and _field(c, "key")["required"]
    scopes = re.fullmatch(r"\^\((.*)\)\$", _field(c, "scope")["options"]["pattern"]).group(1).split("|")
    assert scopes == run["hooks"]["order"]
    for name in ("window_start", "count"):
        assert _field(c, name)["type"] == "number" and _field(c, name)["options"]["noDecimal"] is True
        assert _field(c, name)["options"]["min"] == 0
    # No JSON field, so nothing joins the JSON limit registry.
    assert all(f["type"] != "json" for f in c["fields"])
    assert "CREATE UNIQUE INDEX idx_share_throttle_key ON share_throttle (key)" in c["indexes"]
    assert "CREATE INDEX idx_share_throttle_window ON share_throttle (window_start)" in c["indexes"]


def test_up_lists_the_three_operations_once(run, tmp_path_factory):
    assert _field(run["up"]["admission_commands"], "operation")["options"]["values"] == BEFORE + ADDED
    # A database that already lists one of them gets each once.
    again = _run(tmp_path_factory, BEFORE + ["snapshot_create"])
    assert _field(again["up"]["admission_commands"], "operation")["options"]["values"] == BEFORE + ADDED


def test_down_drops_only_what_up_added(run):
    assert set(run["down"]) == {"users", "admission_commands"}
    assert run["deleted"] == ["share_throttle", "share_resolvers"]
    assert _field(run["down"]["admission_commands"], "operation")["options"]["values"] == BEFORE
    # admission_commands keeps every other field.
    assert [f["name"] for f in run["down"]["admission_commands"]["fields"]] == ["command_id", "operation"]
    # Run again, it finds nothing left to drop and changes nothing.
    assert run["secondDown"] is None
