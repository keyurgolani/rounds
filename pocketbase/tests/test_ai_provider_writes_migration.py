"""ai_providers' creates and updates are the server's (ROUNDS-14-L02 stage A).

Runs of 1700008810_ai_provider_writes.js's up() and down() against a
stubbed Dao through node: up sets the create and update rules to null and
records the ones it found once, a rule an operator's lock left null stays
null, and down() puts the recorded rules back and removes the record. The
rules agree with docs/security/account-scope.v1.json and with the
manifest, whose record of the rules replaced is checked against
1700006000_account_scope_rules.js. The two-account harness proves the live
rules refuse each client write."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "pocketbase" / "pb_migrations"
MIGRATION = MIGRATIONS / "1700008810_ai_provider_writes.js"
OWNERSHIP = MIGRATIONS / "1700006000_account_scope_rules.js"
MANIFEST = ROOT / "pocketbase" / "migration-manifests" / "ai-provider-writes-v1.json"
POLICY = ROOT / "docs" / "security" / "account-scope.v1.json"
KEY = "1700008810_ai_provider_writes.js"


def _ownership_rule(name: str) -> str:
    found = re.search(rf"const {name} =\s*'([^']*)'", OWNERSHIP.read_text(), re.DOTALL)
    assert found, name
    return found.group(1)


CREATE = _ownership_rule("CREATE_RULE")
UPDATE = _ownership_rule("UPDATE_RULE")

# The rules hand out as PocketBase 0.22's JS VM hands them out: an object
# that reads the collection's own value, which an assignment writes
# through. _params is a table the two queries down() makes read and write.
_HARNESS = r"""
const [migrationPath, programJson] = process.argv.slice(2);
const program = JSON.parse(programJson);
let up, down;
globalThis.migrate = (u, d) => { up = u; down = d; };
const values = Object.assign({ listRule: "list", viewRule: "view", deleteRule: "delete" }, program.rules);
const collection = { id: "pbc_providers", name: "ai_providers" };
for (const key of ["listRule", "viewRule", "createRule", "updateRule", "deleteRule"]) {
  Object.defineProperty(collection, key, {
    enumerable: true,
    get: () => (values[key] === null ? null
      : { toString: () => values[key], valueOf: () => values[key], toJSON: () => values[key] }),
    set: (v) => { values[key] = v === null ? null : String(v); },
  });
}
const db = { saves: 0, params: Object.assign({}, program.params || {}) };
db.newQuery = (sql) => {
  let bound = {};
  const q = {
    bind: (b) => { bound = b; return q; },
    one: (model) => {
      if (!/^SELECT CAST\(value AS TEXT\) AS value FROM _params WHERE key = \{:key\}$/.test(sql)) throw new Error("unexpected " + sql);
      if (!(bound.key in db.params)) throw new Error("sql: no rows in result set");
      model.value = db.params[bound.key];
    },
    execute: () => {
      if (!/^DELETE FROM _params WHERE key = \{:key\}$/.test(sql)) throw new Error("unexpected " + sql);
      delete db.params[bound.key];
    },
  };
  return q;
};
globalThis.DynamicModel = function (shape) { Object.assign(this, shape); };
globalThis.Dao = function () {
  this.findCollectionByNameOrId = (n) => {
    if (n !== "ai_providers" || program.missing) throw new Error("missing collection " + n);
    return collection;
  };
  this.saveCollection = () => { db.saves += 1; };
  this.saveParam = (key, value) => { db.params[key] = JSON.stringify(value); };
};
require(migrationPath);
const out = [];
for (const step of program.steps) {
  let error = null;
  try { (step === "up" ? up : down)(db); } catch (err) { error = String(err && err.message); }
  out.push({ step, error, rules: Object.assign({}, values), saves: db.saves, params: Object.assign({}, db.params) });
}
process.stdout.write(JSON.stringify(out));
"""


def run(tmp_path_factory, steps, rules=None, params=None, missing=False) -> list[dict]:
    node = shutil.which("node")
    assert node, "node is required for the migration checks; CI installs it"
    harness = tmp_path_factory.mktemp("ai_provider_writes") / "harness.cjs"
    harness.write_text(_HARNESS)
    program = {"steps": steps, "rules": rules or {"createRule": CREATE, "updateRule": UPDATE},
               "params": params or {}, "missing": missing}
    res = subprocess.run([node, str(harness), str(MIGRATION), json.dumps(program)], capture_output=True, text=True,
                         timeout=60)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def test_up_makes_creates_and_updates_server_only_and_records_what_it_found(tmp_path_factory):
    (up,) = run(tmp_path_factory, ["up"])
    assert up["error"] is None
    assert up["rules"] == {"listRule": "list", "viewRule": "view", "createRule": None, "updateRule": None,
                           "deleteRule": "delete"}
    assert json.loads(up["params"][KEY]) == {"collection": "ai_providers", "create": CREATE, "update": UPDATE}
    assert up["saves"] == 1


def test_a_second_run_changes_nothing_and_keeps_the_first_record(tmp_path_factory):
    first, second = run(tmp_path_factory, ["up", "up"])
    assert second["saves"] == first["saves"] == 1
    assert second["params"] == first["params"]


def test_a_locked_rule_stays_null_both_ways(tmp_path_factory):
    up, down = run(tmp_path_factory, ["up", "down"], rules={"createRule": None, "updateRule": UPDATE})
    assert json.loads(up["params"][KEY]) == {"collection": "ai_providers", "create": None, "update": UPDATE}
    assert (down["rules"]["createRule"], down["rules"]["updateRule"]) == (None, UPDATE)
    (only,) = run(tmp_path_factory, ["up"], rules={"createRule": None, "updateRule": None})
    assert only["saves"] == 0 and only["params"] == {}


def test_down_puts_the_recorded_rules_back_and_removes_the_record(tmp_path_factory):
    _up, down = run(tmp_path_factory, ["up", "down"])
    assert down["error"] is None
    assert (down["rules"]["createRule"], down["rules"]["updateRule"]) == (CREATE, UPDATE)
    assert down["params"] == {}


def test_down_without_a_record_changes_nothing(tmp_path_factory):
    (down,) = run(tmp_path_factory, ["down"], rules={"createRule": None, "updateRule": None})
    assert down["error"] is None and down["saves"] == 0
    assert (down["rules"]["createRule"], down["rules"]["updateRule"]) == (None, None)


def test_down_refuses_a_record_that_isnt_its_own(tmp_path_factory):
    (down,) = run(tmp_path_factory, ["down"], rules={"createRule": None, "updateRule": None},
                  params={KEY: json.dumps({"collection": "other", "create": "x", "update": "y"})})
    assert "isn't this migration's record" in down["error"]
    assert down["saves"] == 0


def test_a_missing_collection_fails_up(tmp_path_factory):
    (up,) = run(tmp_path_factory, ["up"], missing=True)
    assert "missing collection ai_providers" in up["error"] and up["params"] == {}


def test_the_policy_and_the_manifest_agree_with_the_migration():
    policy = json.loads(POLICY.read_text())["collections"]["ai_providers"]
    assert policy["current_rules"]["create"] is None and policy["current_rules"]["update"] is None
    assert policy["current_rules"]["list"] == policy["current_rules"]["view"] == policy["current_rules"]["delete"]
    assert {"migration": MIGRATION.name, "rules": ["create", "update"]} in policy["rule_overrides"]
    assert policy["hook"] == "pocketbase/pb_hooks/ai_custody.pb.js"
    assert {"account-scope.create.server-only.denied", "account-scope.update.server-only.denied"} <= set(policy["probes"])
    assert not {p for p in policy["probes"] if p.startswith(("account-scope.create.", "account-scope.update."))
                and "server-only" not in p}
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["migration"] == MIGRATION.stem and manifest["journal"]["param"] == KEY
    entry = manifest["collections"]["ai_providers"]
    assert entry["before"]["create_sha256"] == hashlib.sha256(CREATE.encode()).hexdigest()
    assert entry["before"]["update_sha256"] == hashlib.sha256(UPDATE.encode()).hexdigest()
    assert entry["after"] == {"create": None, "update": None}


@pytest.mark.parametrize("name", ["ai_providers"])
def test_the_rules_it_replaces_are_the_ownership_rules(name):
    policy = json.loads(POLICY.read_text())["collections"][name]
    assert policy["target_rule_migration"] == OWNERSHIP.name
    assert name in re.search(r"const OWNED = \[(.*?)\];", OWNERSHIP.read_text(), re.DOTALL).group(1)
