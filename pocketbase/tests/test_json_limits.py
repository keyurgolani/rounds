"""JSON field limits on every database (ROUNDS-00A-L03, decision D10).

PocketBase's own 1702134272_set_default_json_max_size migration sets every
JSON field to 2,000,000 bytes, and it sorts after the repository's
1700xxxxxx migrations, so on a fresh database it overwrites the limits they
declare. 1702134273_json_limits.js sorts right after it and sets them back
from its LIMITS registry.

These tests hold the registry to the migrations: every JSON field they
define is registered at the size they end on, the registry's up and down
steps behave on a stubbed Dao through node (down puts back the size each
field held before up, from up's record), the migration lint refuses a new
migration whose JSON limit isn't registered, and the account-scope policy's
oversized probes use the declared limits. Harness phase 12c checks the same
on fresh and upgraded databases with the pinned PocketBase binary.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
try:
    import lint_migrations as lm
finally:
    sys.path.pop(0)

MIG_DIR = ROOT / "pocketbase" / "pb_migrations"
MIG = "pocketbase/pb_migrations/"
REGISTRY = MIG_DIR / "1702134273_json_limits.js"
POLICY = ROOT / "docs" / "security" / "account-scope.v1.json"
MIB = 1024 * 1024


def _migrations() -> dict[str, str]:
    return {MIG + p.name: p.read_text() for p in sorted(MIG_DIR.iterdir()) if lm.is_migration(MIG + p.name)}


# ---- the registry against the migrations -------------------------------------------------------


def test_every_json_field_the_migrations_define_is_registered_at_the_size_they_end_on():
    migrations = _migrations()
    declared, unreadable = lm.declared_limits(migrations)
    assert unreadable == []
    registry = lm.registry_limits(migrations)
    assert len(declared) >= 90
    assert {k: v for k, v in declared.items() if registry.get(k) != v} == {}
    # An entry may outlive its field only when a migration dropped the field
    # after declaring it; a registry file is never edited to take it out.
    ever = {(e.collection, e.field) for src in migrations.values() for e in lm.read_json_limits(src)[0]
            if e.kind == "set"}
    assert sorted(set(registry) - set(declared) - ever) == []


def test_the_limits_d10_names_hold_their_sizes():
    registry = lm.registry_limits(_migrations())
    assert registry[("take_home_attempts", "files")] == 8 * MIB
    for field in ("summary", "relations", "findings", "outcomes"):
        assert registry[("relation_quarantine_reports", field)] == 16 * MIB
    assert registry[("relation_quarantine", "payload")] == 16 * MIB
    assert registry[("execution_jobs", "input")] == 8 * MIB
    assert registry[("execution_attempts", "operator_view")] == 64 * 1024
    assert registry[("execution_envelopes", "user_view")] == MIB
    # The snapshot store's (1700008000_legacy_artifact_snapshots.js).
    assert registry[("legacy_artifact_snapshots", "design")] == 64 * 1024
    assert registry[("legacy_artifact_snapshots", "data")] == 2 * MIB
    assert registry[("legacy_artifact_snapshots", "font_families")] == 4 * 1024


def test_each_registry_file_sorts_after_the_reset_and_holds_a_sorted_literal_list():
    names = sorted(p.name for p in MIG_DIR.iterdir() if lm.REGISTRY_FILE.match(p.name))
    assert names[0] == REGISTRY.name
    for name in names:
        source = (MIG_DIR / name).read_text()
        entries = lm.registry_entries(source)
        assert entries and entries == sorted(entries), name
        assert name > lm.JSON_RESET, name
        assert lm.scan(source) == [], name
        assert lm.json_limit_findings(MIG + name, source, {}, {}) == [], name


def test_each_registry_file_records_under_its_own_name():
    for path in sorted(q for q in MIG_DIR.iterdir() if lm.REGISTRY_FILE.match(q.name)):
        assert f'const PRIOR_KEY = "{path.name}";' in path.read_text(), path.name


def test_the_registry_sorts_right_after_pocketbases_reset():
    reset_stamp = int(lm.JSON_RESET.split("_", 1)[0])
    assert int(REGISTRY.name.split("_", 1)[0]) == reset_stamp + 1
    assert all(p.name < REGISTRY.name for p in MIG_DIR.iterdir() if not lm.REGISTRY_FILE.match(p.name))


def test_the_oversized_probes_use_the_declared_limits():
    policy = json.loads(POLICY.read_text())
    registry = lm.registry_limits(_migrations())
    probes = {name: row["oversized_probe"] for name, row in policy["collections"].items() if "oversized_probe" in row}
    assert len(probes) >= 14
    for name, probe in probes.items():
        assert probe["max_bytes"] == registry[(name, probe["field"])], name


# ---- the registry's up and down steps through node, against a stub Dao --------------------------

_HARNESS = r"""
const [migrationPath, plansJson] = process.argv.slice(2);
let up, down;
globalThis.migrate = (u, d) => { up = u; down = d; };
globalThis.Dao = function (db) {
  this.findCollectionByNameOrId = (name) => {
    const c = db.collections[name];
    if (!c) throw new Error("missing collection " + name);
    return c;
  };
  this.saveCollection = (c) => { db.saves.push(c.name); };
  this.saveParam = (key, value) => { db.params[key] = JSON.stringify(value); };
  this.findParamByKey = (key) => {
    if (!(key in db.params)) throw new Error("sql: no rows in result set");
    return { key, value: { string: () => db.params[key] } };
  };
  this.deleteParam = (param) => { delete db.params[param.key]; };
};
require(migrationPath);
function build(plan) {
  const collections = {};
  for (const [name, fields] of Object.entries(plan)) {
    const items = fields.map(([field, type, size]) => ({ name: field, type, options: size === null ? {} : { maxSize: size } }));
    collections[name] = { name, items, schema: { getFieldByName: (f) => items.find((x) => x.name === f) || null } };
  }
  return { collections, saves: [], params: {} };
}
function dump(db) {
  const out = {};
  for (const [name, c] of Object.entries(db.collections)) {
    out[name] = c.items.map((f) => [f.name, f.type, f.options.maxSize === undefined ? null : f.options.maxSize]);
  }
  return out;
}
const results = JSON.parse(plansJson).map((plan) => {
  const db = build(plan);
  up(db);
  const afterUp = dump(db);
  const upSaves = db.saves.splice(0);
  const paramsAfterUp = Object.assign({}, db.params);
  up(db);
  const againSaves = db.saves.splice(0);
  const paramsAfterAgain = Object.assign({}, db.params);
  down(db);
  return {
    afterUp, upSaves, againSaves, afterDown: dump(db), downSaves: db.saves.splice(0),
    params: { afterUp: paramsAfterUp, afterAgain: paramsAfterAgain, afterDown: db.params },
  };
});
process.stdout.write(JSON.stringify(results));
"""


@pytest.fixture(scope="module")
def registry() -> dict[tuple[str, str], int]:
    entries = lm.registry_entries(REGISTRY.read_text())
    assert entries
    return {(c, f): size for c, f, size in entries}


def _plan(registry: dict, at_size: set[str] = frozenset()) -> dict[str, list]:
    """A database holding every registered field at PocketBase's default,
    or at its size for the collections in ``at_size``; without ``todos``;
    with ``offers.trail`` as text; and with an unregistered JSON field."""
    plan: dict[str, list] = {}
    for (collection, field), size in sorted(registry.items()):
        plan.setdefault(collection, []).append([field, "json", size if collection in at_size else lm.JSON_DEFAULT_BYTES])
    del plan["todos"]
    plan["offers"] = [["trail", "text", None]]
    plan["resumes"].append(["unregistered", "json", 1234])
    return plan


@pytest.fixture(scope="module")
def runs(registry, tmp_path_factory) -> list[dict]:
    node = shutil.which("node")
    assert node, "node is required for the PocketBase migration checks; CI installs it"
    harness = tmp_path_factory.mktemp("json-limits") / "harness.cjs"
    harness.write_text(_HARNESS)
    plans = [_plan(registry), _plan(registry, {"coding_questions", "resumes"})]
    res = subprocess.run([node, str(harness), str(REGISTRY), json.dumps(plans)], capture_output=True, text=True,
                         timeout=60)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def _sizes(dump: dict) -> dict[tuple[str, str], int | None]:
    return {(c, f): size for c, fields in dump.items() for f, _type, size in fields}


def test_up_sets_every_registered_field_to_its_size_and_saves_each_collection_once(runs, registry):
    run = runs[0]
    sizes = _sizes(run["afterUp"])
    for key, size in registry.items():
        if key[0] not in ("todos", "offers"):
            assert sizes[key] == size, key
    expected = sorted({c for c, _f in registry} - {"todos", "offers"})
    assert run["upSaves"] == expected


def test_up_skips_a_missing_collection_another_type_and_an_unregistered_field(runs):
    run = runs[0]
    assert "todos" not in run["afterUp"]
    assert run["afterUp"]["offers"] == [["trail", "text", None]]
    assert ["unregistered", "json", 1234] in run["afterUp"]["resumes"]


def test_up_again_changes_nothing(runs):
    assert [run["againSaves"] for run in runs] == [[], []]


def test_up_on_an_upgraded_database_saves_only_the_collections_whose_limits_change(runs, registry):
    run = runs[1]
    assert "coding_questions" not in run["upSaves"] and "resumes" not in run["upSaves"]
    assert run["upSaves"] == sorted({c for c, _f in registry} - {"todos", "offers", "coding_questions", "resumes"})
    assert _sizes(run["afterUp"]) == _sizes(runs[0]["afterUp"])


def test_down_puts_pocketbases_default_back(runs, registry):
    # Every registered field held the default here before up.
    run = runs[0]
    sizes = _sizes(run["afterDown"])
    for key in registry:
        if key[0] not in ("todos", "offers"):
            assert sizes[key] == lm.JSON_DEFAULT_BYTES, key
    assert ["unregistered", "json", 1234] in run["afterDown"]["resumes"]
    assert run["afterDown"]["offers"] == [["trail", "text", None]]
    assert run["downSaves"] == run["upSaves"]


def _record(params: dict) -> dict[tuple[str, str], int] | None:
    raw = params.get(REGISTRY.name)
    return None if raw is None else {(c, f): size for c, f, size in json.loads(raw)}


def test_up_records_the_size_each_field_it_changed_held(runs, registry):
    skipped = ("todos", "offers")
    held = [{key: lm.JSON_DEFAULT_BYTES for key in registry if key[0] not in skipped},
            {key: lm.JSON_DEFAULT_BYTES for key in registry
             if key[0] not in skipped + ("coding_questions", "resumes")}]
    for run, want in zip(runs, held):
        assert set(run["params"]["afterUp"]) == {REGISTRY.name}
        assert _record(run["params"]["afterUp"]) == want


def test_up_again_keeps_the_record(runs):
    for run in runs:
        assert run["params"]["afterAgain"] == run["params"]["afterUp"]


def test_down_leaves_a_field_that_already_held_its_size_and_removes_the_record(runs, registry):
    run = runs[1]
    sizes = _sizes(run["afterDown"])
    for key, size in registry.items():
        if key[0] in ("coding_questions", "resumes"):
            assert sizes[key] == size, key
        elif key[0] not in ("todos", "offers"):
            assert sizes[key] == lm.JSON_DEFAULT_BYTES, key
    assert run["downSaves"] == run["upSaves"]
    assert [r["params"]["afterDown"] for r in runs] == [{}, {}]


@pytest.fixture(scope="module")
def steady(registry, tmp_path_factory) -> dict:
    """A run on a database whose every registered field holds its size."""
    harness = tmp_path_factory.mktemp("json-limits-steady") / "harness.cjs"
    harness.write_text(_HARNESS)
    plan = {}
    for (collection, field), size in sorted(registry.items()):
        plan.setdefault(collection, []).append([field, "json", size])
    res = subprocess.run([shutil.which("node"), str(harness), str(REGISTRY), json.dumps([plan])],
                         capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)[0]


def test_up_with_nothing_to_change_saves_and_records_nothing(steady):
    assert steady["upSaves"] == [] and steady["downSaves"] == []
    assert steady["params"] == {"afterUp": {}, "afterAgain": {}, "afterDown": {}}


# ---- the lint: what a new migration's JSON limits need ----------------------------------------------


def _up(body: str) -> str:
    return f"migrate((db) => {{\n  const dao = new Dao(db);\n{body}\n}}, (db) => {{\n}});\n"


def _registry(entries: list[tuple[str, str, int | str]]) -> str:
    lines = "".join(f'  ["{c}", "{f}", {size}],\n' for c, f, size in entries)
    return (f"const LIMITS = [\n{lines}];\nfunction apply(dao, size) {{}}\n"
            "migrate((db) => apply(new Dao(db), (b) => b), (db) => apply(new Dao(db), () => 2000000));\n")


def _lint(added: dict[str, str], existing: dict[str, str] | None = None) -> list[tuple[str, str, int | None]]:
    head = {MIG + name: source for name, source in {**(existing or {}), **added}.items()}
    changes = [lm.Change("A", MIG + name, content=source) for name, source in added.items()]
    blocking, _allowed = lm.lint(changes, [], head)
    return sorted((f.path[len(MIG):], f.rule, f.line) for f in blocking)


NOTES = _up('  const notes = new Collection({\n    name: "notes",\n'
            '    schema: [{ name: "body", type: "json", options: { maxSize: 4096 } }],\n  });\n'
            "  dao.saveCollection(notes);")


def test_a_new_json_field_without_a_registry_entry_fails():
    assert _lint({"1700009000_notes.js": NOTES}) == [("1700009000_notes.js", "unregistered-json-limit", 5)]


def test_a_new_json_field_registered_at_its_size_passes():
    registry = _registry([("notes", "body", 4096)])
    assert _lint({"1700009000_notes.js": NOTES, "1702134274_json_limits_notes.js": registry}) == []
    # Or registered by a json_limits migration that's already there.
    assert _lint({"1700009000_notes.js": NOTES}, {"1702134274_json_limits_notes.js": registry}) == []


def test_a_registry_entry_at_another_size_fails():
    registry = _registry([("notes", "body", 8192)])
    assert _lint({"1700009000_notes.js": NOTES, "1702134274_json_limits_notes.js": registry}) == [
        ("1700009000_notes.js", "unregistered-json-limit", 5)]


def test_a_later_registry_entry_wins():
    old = _registry([("notes", "body", 8192)])
    new = _registry([("notes", "body", 4096)])
    assert _lint({"1700009000_notes.js": NOTES, "1702134275_json_limits_fix.js": new},
                 {"1702134274_json_limits_notes.js": old}) == []


def test_the_registry_holds_the_size_the_migrations_end_on():
    grow = _up('  const notes = dao.findCollectionByNameOrId("notes");\n'
               '  notes.schema.getFieldByName("body").options.maxSize = 8192;\n  dao.saveCollection(notes);')
    added = {"1700009000_notes.js": NOTES, "1700009100_grow.js": grow}
    assert _lint({**added, "1702134274_json_limits_notes.js": _registry([("notes", "body", 8192)])}) == []
    assert _lint({**added, "1702134274_json_limits_notes.js": _registry([("notes", "body", 4096)])}) == [
        ("1700009000_notes.js", "unregistered-json-limit", 5), ("1700009100_grow.js", "unregistered-json-limit", 4)]


@pytest.mark.parametrize("name, source", [
    ("1700009000_json_limits.js", _registry([("notes", "body", 4096)])),
    ("1702134272_json_limits_early.js", _registry([("notes", "body", 4096)])),
    ("1702134274_json_limits_notes.js", _registry([("notes", "body", "4 * 1024")])),
    ("1702134274_json_limits_notes.js", _registry([("notes", "body", 4096), ("notes", "body", 4096)])),
    ("1702134274_json_limits_notes.js", _up("  const n = 1;")),
])
def test_a_json_limits_migration_must_sort_after_the_reset_and_hold_a_literal_list(name, source):
    assert _lint({name: source}) == [(name, "json-limits-registry", None)]


# ---- the lint: the shapes it reads -----------------------------------------------------------------

READABLE = [
    # A field helper with a constant, in a new collection's schema.
    ('  const J = 1024;\n  const json = (name) => ({ name, type: "json", options: { maxSize: 2 * J } });\n'
     '  dao.saveCollection(new Collection({ name: "a", schema: [json("x"), json("y")] }));',
     {("a", "x", 2048), ("a", "y", 2048)}),
    # A helper that returns a schema, used by two collections.
    ('  const json = (name) => ({ name, type: "json", options: { maxSize: 10 } });\n'
     '  const fields = () => [json("x")];\n'
     '  dao.saveCollection(new Collection({ name: "a", schema: fields() }));\n'
     '  dao.saveCollection(new Collection({ name: "b", schema: fields() }));',
     {("a", "x", 10), ("b", "x", 10)}),
    # addField on a binding, and on a lookup.
    ('  const c = dao.findCollectionByNameOrId("a");\n'
     '  c.schema.addField(new SchemaField({ name: "x", type: "json", options: { maxSize: 5 } }));\n'
     '  dao.findCollectionByNameOrId("b").schema.addField(new SchemaField({ name: "y", type: "json", options: { maxSize: 6 } }));',
     {("a", "x", 5), ("b", "y", 6)}),
    # A loop over a literal array.
    ('  for (const n of ["a", "b"]) {\n    const c = dao.findCollectionByNameOrId(n);\n'
     '    c.schema.addField(new SchemaField({ name: "x", type: "json", options: { maxSize: 5 } }));\n  }',
     {("a", "x", 5), ("b", "x", 5)}),
    # A local helper called with the collection's name and its schema.
    ('  const ensure = (name, schema) => null;\n  ensure("a", [{ name: "x", type: "json", options: { maxSize: 5 } }]);',
     {("a", "x", 5)}),
    # An assignment, on the lookup and through a field binding.
    ('  const MIB = 1024 * 1024;\n  const c = dao.findCollectionByNameOrId("a");\n'
     '  c.schema.getFieldByName("x").options.maxSize = 8 * MIB;\n'
     '  const f = c.schema.getFieldByName("y");\n  f.options.maxSize = 7;',
     {("a", "x", 8 * MIB), ("a", "y", 7)}),
    # A SchemaField helper whose size is a parameter.
    ('  const jf = (n, size) => new SchemaField({ name: n, type: "json", options: { maxSize: size } });\n'
     '  const c = dao.findCollectionByNameOrId("a");\n  c.schema.addField(jf("x", 9));',
     {("a", "x", 9)}),
    # A file field's maxSize isn't a JSON limit; comments don't count.
    ('  // c.schema.getFieldByName("x").options.maxSize = 1;\n'
     '  dao.saveCollection(new Collection({ name: "a", schema: [{ name: "f", type: "file", options: { maxSize: 5242880 } }] }));',
     set()),
]


@pytest.mark.parametrize("body, expected", READABLE)
def test_the_lint_reads_these_json_limits(body, expected):
    events, unreadable = lm.read_json_limits(_up(body))
    assert unreadable == []
    assert {(e.collection, e.field, e.size) for e in events if e.kind == "set"} == expected


UNREADABLE = [
    '  dao.saveCollection(new Collection({ name: "a", schema: [{ name: "x", type: "json" }] }));',
    '  const c = dao.findCollectionByNameOrId("a");\n  c.schema.getFieldByName("x").options.maxSize = Math.max(1, 2);',
    '  const c = dao.findCollectionByNameOrId("a");\n  c.schema.getFieldByName("x").options.maxSize *= 2;',
    '  const c = dao.findCollectionByNameOrId("a");\n  Object.assign(c.schema.getFieldByName("x").options, { maxSize: 5 });',
    '  const c = dao.findCollectionByNameOrId("a");\n  const o = c.schema.getFieldByName("x").options;\n  o.maxSize = 5;',
    '  dao.saveCollection(new Collection({ name: "a", schema: ["x"].map((n) => ({ name: n, type: "json", options: { maxSize: 5 } })) }));',
    '  someCollection.schema.addField(new SchemaField({ name: "x", type: "json", options: { maxSize: 5 } }));',
    '  const c = dao.findCollectionByNameOrId("a");\n  c.schema.addField(new SchemaField({ name: pick(), type: "json", options: { maxSize: 5 } }));',
]


@pytest.mark.parametrize("body", UNREADABLE)
def test_a_json_limit_the_lint_cant_read_fails(body):
    assert [rule for _name, rule, _line in _lint({"1700009000_x.js": _up(body)})] == ["unreadable-json-limit"]


def test_a_drop_or_a_removed_field_takes_its_limit_out():
    create = _up('  dao.saveCollection(new Collection({ name: "a", schema: ['
                 '{ name: "x", type: "json", options: { maxSize: 5 } }, { name: "y", type: "json", options: { maxSize: 6 } }] }));')
    remove = _up('  const c = dao.findCollectionByNameOrId("a");\n  const f = c.schema.getFieldByName("x");\n'
                 "  c.schema.removeField(f.id);\n  dao.saveCollection(c);")
    drop = _up('  dao.deleteCollection(dao.findCollectionByNameOrId("a"));')
    again = _up('  dao.saveCollection(new Collection({ name: "a", schema: [{ name: "z", type: "json", options: { maxSize: 7 } }] }));')
    declared, unreadable = lm.declared_limits({MIG + "1_a.js": create, MIG + "2_a.js": remove})
    assert declared == {("a", "y"): 6} and unreadable == []
    declared, _unreadable = lm.declared_limits({MIG + "1_a.js": create, MIG + "2_a.js": drop, MIG + "3_a.js": again})
    assert declared == {("a", "z"): 7}


def test_a_down_step_and_an_existing_migration_dont_count():
    down_only = "migrate((db) => {\n}, (db) => {\n  const c = dao.findCollectionByNameOrId(\"a\");\n" \
                "  c.schema.getFieldByName(\"x\").options.maxSize = 1;\n});\n"
    assert _lint({"1700009000_x.js": down_only}) == []
    # Only a new migration is checked; the existing ones are held by the test above.
    assert _lint({}, {"1700009000_notes.js": NOTES}) == []


# ---- the lint end to end, through git -------------------------------------------------------------


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for key in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{key}_NAME", "Lint Test")
        monkeypatch.setenv(f"GIT_{key}_EMAIL", "lint@example.test")
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / MIG).mkdir(parents=True)
    (root / lm.DEFAULT_ALLOWLIST).write_text(json.dumps({"version": 1, "entries": []}))
    (root / MIG / "1700000000_init.js").write_text(_up("  const n = 1;"))
    _git(root, "init", "-q", "-b", "main")
    _commit(root)
    _git(root, "switch", "-q", "-c", "change")
    return root


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def _commit(root: Path) -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "change")


def test_an_unregistered_json_limit_fails_the_lint_until_it_is_registered(repo, capsys):
    (repo / MIG / "1700009000_notes.js").write_text(NOTES)
    _commit(repo)
    assert lm.main(["--repo", str(repo), "--base", "main", "--head", "HEAD"]) == 1
    out = capsys.readouterr().out
    assert "1700009000_notes.js:5: unregistered-json-limit" in out and "json_limits" in out
    (repo / MIG / "1702134274_json_limits_notes.js").write_text(_registry([("notes", "body", 4096)]))
    _commit(repo)
    assert lm.main(["--repo", str(repo), "--base", "main", "--head", "HEAD"]) == 0
