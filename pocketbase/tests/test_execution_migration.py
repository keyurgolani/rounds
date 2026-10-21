"""The execution_jobs migration (ROUNDS-00A-L03 PR 1).

Static checks on the source, plus a run of its up() and down() against a
stubbed Dao through node, like test_definitions_expand.py: the four
collections and their rules, fields, and indexes, the links it adds to
the attempt collections and admission_commands, take_home_attempts.files
at 8 MiB, and a down() that drops only what up() added. The values that
pb_hooks/execution.js also holds are checked against it, so the two stay
in step. The migration also runs on real databases in #9's harness and
in harness/migration_check.sh.
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
MIGRATION = ROOT / "pocketbase" / "pb_migrations" / "1700007100_execution_jobs.js"
HOOKS = ROOT / "pocketbase" / "pb_hooks"
MIB = 1024 * 1024
# What take_home_attempts.files holds before the migration: PocketBase's
# JSON default, which its own migration sets after 1700001300_take_home.js.
BASE_FILES_MAX = 2000000
SERVICE_ONLY = '@request.auth.collectionName = "execution_service"'
JOB_COLLECTIONS = ("execution_jobs", "execution_attempts", "execution_envelopes")


@pytest.fixture(scope="module")
def src() -> str:
    return MIGRATION.read_text()


def test_the_file_is_a_migration(src):
    assert src.lstrip().startswith("/// <reference")
    assert "migrate(" in src


def test_neither_step_reads_or_writes_a_record(src):
    for call in ("saveRecord", "deleteRecord", "findRecordsByFilter", "findFirstRecordByData", "newQuery",
                 "new Record("):
        assert call not in src, call


def test_up_resolves_every_collection_it_changes_before_it_writes(src):
    up = src[src.index("(db) =>"):src.rindex("(db) =>")]
    first_write = up.index("saveCollection")
    for name in ("users", "admission_commands", "ai_coding_attempts", "take_home_attempts"):
        assert up.index(f'findCollectionByNameOrId("{name}")') < first_write, name


def test_the_migration_lint_finds_nothing(src):
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import lint_migrations
    finally:
        sys.path.pop(0)
    assert lint_migrations.scan(src) == []


# ---- behavioural: up() and down() through node against a stub Dao ---------

_HARNESS = r"""
const [migrationPath, hooksDir] = process.argv.slice(2);
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

function baseDb() {
  const collections = {};
  const add = (name, type, fields) => {
    const c = new Collection({ name, type, schema: fields });
    c.id = "c_" + name;
    collections[name] = c;
  };
  add("users", "auth", []);
  add("admission_commands", "base", [{ name: "command_id", type: "text" }]);
  add("ai_coding_attempts", "base", [{ name: "status", type: "select" }]);
  add("take_home_attempts", "base", [{ name: "files", type: "json", options: { maxSize: 2000000 } }]);
  return { collections, saves: [], deleted: [] };
}

function dump(db) {
  const out = {};
  for (const [name, c] of Object.entries(db.collections)) {
    out[name] = {
      id: c.id, type: c.type, listRule: c.listRule, viewRule: c.viewRule, createRule: c.createRule,
      updateRule: c.updateRule, deleteRule: c.deleteRule, options: c.options || null, indexes: c.indexes || [],
      fields: c.schema.fields().map((f) => ({ name: f.name, type: f.type, required: Boolean(f.required), options: f.options })),
    };
  }
  // A copy, so down() can't change what up() left.
  return JSON.parse(JSON.stringify(out));
}

require(migrationPath);
const db = baseDb();
up(db);
const afterUp = dump(db);
const saves = db.saves.slice();
down(db);
const execution = require(require("path").join(hooksDir, "execution.js"));
process.stdout.write(JSON.stringify({
  up: afterUp,
  saves,
  down: dump(db),
  deleted: db.deleted,
  hooks: {
    kinds: Object.keys(execution.KINDS),
    terminal: execution.TERMINAL,
    cleanup: execution.CLEANUP,
    maxAttempts: execution.MAX_ATTEMPTS,
    secretMin: execution.SECRET_MIN_CHARS,
  },
}));
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory) -> dict:
    node = shutil.which("node")
    assert node, "node is required for the PocketBase migration checks; CI installs it"
    harness = tmp_path_factory.mktemp("execution-jobs") / "harness.cjs"
    harness.write_text(_HARNESS)
    # The hooks need these globals to load.
    prelude = "globalThis.__hooks = process.argv[3];"
    harness.write_text(prelude + _HARNESS)
    res = subprocess.run([node, str(harness), str(MIGRATION), str(HOOKS)], capture_output=True, text=True,
                         timeout=60)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def _field(collection: dict, name: str) -> dict:
    (field,) = [f for f in collection["fields"] if f["name"] == name]
    return field


def test_up_adds_the_four_collections_and_changes_three(run):
    assert set(run["up"]) - {"users", "admission_commands", "ai_coding_attempts", "take_home_attempts"} == {
        "execution_service", *JOB_COLLECTIONS,
    }
    assert run["saves"] == ["execution_service", *JOB_COLLECTIONS, "ai_coding_attempts", "take_home_attempts",
                            "admission_commands"]


def test_the_service_writer_is_an_auth_collection_no_client_reaches(run):
    service = run["up"]["execution_service"]
    assert service["type"] == "auth" and service["fields"] == []
    for rule in ("listRule", "viewRule", "createRule", "updateRule", "deleteRule"):
        assert service[rule] is None, rule
    options = service["options"]
    assert options["allowUsernameAuth"] is True
    assert options["allowEmailAuth"] is False and options["allowOAuth2Auth"] is False
    assert options["requireEmail"] is False and options["manageRule"] is None
    assert options["minPasswordLength"] == run["hooks"]["secretMin"]


@pytest.mark.parametrize("name, owner, reader", [
    ("execution_jobs", "account", SERVICE_ONLY),
    ("execution_attempts", "account", SERVICE_ONLY),
    # D9: the account reads its own envelopes, and only the store writes them.
    ("execution_envelopes", "user", "user = @request.auth.id"),
])
def test_only_the_store_writes_a_job_collection_and_each_has_its_one_reader(run, name, owner, reader):
    collection = run["up"][name]
    assert collection["type"] == "base"
    assert collection["listRule"] == collection["viewRule"] == reader
    assert collection["createRule"] is None and collection["updateRule"] is None
    assert collection["deleteRule"] is None
    field = _field(collection, owner)
    assert field["type"] == "relation" and field["required"] is True
    assert field["options"] == {"collectionId": "c_users", "cascadeDelete": True, "maxSelect": 1}


def test_the_envelope_an_account_reads_holds_no_operator_view(run):
    envelopes, attempts = run["up"]["execution_envelopes"], run["up"]["execution_attempts"]
    assert [f["name"] for f in envelopes["fields"]] == [
        "user", "job", "attempt", "version", "state", "outcome_class", "authoritative", "user_view",
        "graded_collection", "graded_row",
    ]
    operator = _field(attempts, "operator_view")
    assert operator["type"] == "json" and not operator.get("required")
    assert "CREATE INDEX idx_execution_envelopes_user ON execution_envelopes (user)" in envelopes["indexes"]


def test_jobs_attempts_and_envelopes_point_at_each_other_and_cascade(run):
    attempts, envelopes = run["up"]["execution_attempts"], run["up"]["execution_envelopes"]
    jobs_id, attempts_id = run["up"]["execution_jobs"]["id"], attempts["id"]
    assert _field(attempts, "job")["options"] == {"collectionId": jobs_id, "cascadeDelete": True, "maxSelect": 1}
    assert _field(envelopes, "job")["options"]["collectionId"] == jobs_id
    assert _field(envelopes, "attempt")["options"] == {"collectionId": attempts_id, "cascadeDelete": True,
                                                       "maxSelect": 1}


@pytest.mark.parametrize(
    "name, index",
    [
        ("execution_jobs", "CREATE UNIQUE INDEX idx_execution_jobs_command ON execution_jobs (account, command_id)"),
        ("execution_attempts",
         "CREATE UNIQUE INDEX idx_execution_attempts_number ON execution_attempts (job, attempt_number)"),
        ("execution_attempts", "CREATE UNIQUE INDEX idx_execution_attempts_token ON execution_attempts (token_hash)"),
        ("execution_envelopes", "CREATE UNIQUE INDEX idx_execution_envelopes_attempt ON execution_envelopes (attempt)"),
    ],
)
def test_the_uniques_the_protocol_relies_on_are_indexes(run, name, index):
    assert index in run["up"][name]["indexes"]


def test_the_values_match_the_hooks(run):
    jobs, attempts, envelopes = (run["up"][n] for n in JOB_COLLECTIONS)
    terminal = run["hooks"]["terminal"]
    classes = sorted({c for entry in terminal.values() for c in entry["classes"]})
    assert _field(jobs, "kind")["options"]["values"] == run["hooks"]["kinds"]
    assert _field(jobs, "state")["options"]["values"] == ["queued", "leased", "started", *terminal]
    assert _field(attempts, "state")["options"]["values"] == ["leased", "started", *terminal]
    assert _field(envelopes, "state")["options"]["values"] == list(terminal)
    for collection in (jobs, attempts, envelopes):
        assert sorted(_field(collection, "outcome_class")["options"]["values"]) == classes
    for collection in (jobs, attempts):
        assert _field(collection, "cleanup")["options"]["values"] == run["hooks"]["cleanup"]
    number = _field(attempts, "attempt_number")["options"]
    assert (number["min"], number["max"]) == (1, run["hooks"]["maxAttempts"])


def test_the_json_fields_hold_what_the_hooks_allow(run):
    jobs, attempts, envelopes = (run["up"][n] for n in JOB_COLLECTIONS)
    hooks = (HOOKS / "execution.js").read_text()
    limits = {name: eval(value, {}) for name, value in  # noqa: S307 - integer arithmetic from our own file
              re.findall(r"^const (\w+_MAX_CHARS) = ([0-9 *]+);$", hooks, re.M)}
    assert _field(jobs, "input")["options"]["maxSize"] == limits["INPUT_MAX_CHARS"] == 8 * MIB
    assert _field(envelopes, "user_view")["options"]["maxSize"] == limits["USER_VIEW_MAX_CHARS"]
    assert _field(attempts, "operator_view")["options"]["maxSize"] == limits["OPERATOR_VIEW_MAX_CHARS"]


@pytest.mark.parametrize("name", ["ai_coding_attempts", "take_home_attempts"])
def test_each_attempt_collection_gets_a_nullable_envelope_link(run, name):
    envelope = _field(run["up"][name], "envelope")
    assert envelope["type"] == "relation" and envelope["required"] is False
    assert envelope["options"] == {"collectionId": run["up"]["execution_envelopes"]["id"], "cascadeDelete": False,
                                   "maxSelect": 1}


def test_take_home_files_hold_8_mib_and_admission_rows_link_their_job(run):
    assert _field(run["up"]["take_home_attempts"], "files")["options"]["maxSize"] == 8 * MIB
    job = _field(run["up"]["admission_commands"], "job")
    assert job["type"] == "relation" and job["required"] is False
    assert job["options"] == {"collectionId": run["up"]["execution_jobs"]["id"], "cascadeDelete": False,
                              "maxSelect": 1}


def test_down_drops_only_what_up_added(run):
    down = run["down"]
    assert set(down) == {"users", "admission_commands", "ai_coding_attempts", "take_home_attempts"}
    assert run["deleted"] == ["execution_envelopes", "execution_attempts", "execution_jobs", "execution_service"]
    assert [f["name"] for f in down["admission_commands"]["fields"]] == ["command_id"]
    assert [f["name"] for f in down["ai_coding_attempts"]["fields"]] == ["status"]
    assert [f["name"] for f in down["take_home_attempts"]["fields"]] == ["files"]
    assert _field(down["take_home_attempts"], "files")["options"]["maxSize"] == BASE_FILES_MAX
