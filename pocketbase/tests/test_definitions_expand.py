"""The definitions_expand migration (ROUNDS-00A-L02).

Static checks on the source (like test_account_scope_migration.py), plus a
behavioural run of the migration's up() and down() against a stubbed Dao,
driven through node so it exercises the real migration file. The node run
covers a fresh database and a pre-2026-05-16 one that still holds the eight
removed samples, checking each row's mapping and the journal, and that
down() drops only the columns and the journal. The full Compose-harness dry
run on real databases is wired in #9's harness.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "pocketbase" / "pb_migrations" / "1700006200_definitions_expand.js"
TOUCHED = ROOT / "pocketbase" / "migration-manifests" / "1700006200_definitions_expand.json"


@pytest.fixture(scope="module")
def src() -> str:
    return MIGRATION.read_text()


@pytest.fixture(scope="module")
def touched() -> dict:
    return json.loads(TOUCHED.read_text())


def _string_array(src: str, name: str) -> list[str]:
    m = re.search(rf"const {name} = \[(.*?)\];", src, re.DOTALL)
    assert m, f"could not find {name}"
    return re.findall(r'"([^"]+)"', m.group(1))


def test_the_file_is_a_migration(src):
    assert src.lstrip().startswith("/// <reference")
    assert "definitions_expand" in src


def test_down_deletes_no_rows(src):
    down = src[src.rindex("(db) =>"):]
    for destructive in ("deleteRecord", "findRecordsByFilter", "DELETE FROM"):
        assert destructive not in down, destructive
    # It drops only the added columns and the journal collection.
    assert "removeField" in down and "deleteCollection" in down


def test_up_resolves_every_collection_before_it_writes(src):
    up = src[src.index("(db) =>"):src.rindex("(db) =>")]
    first_write = min(up.index("saveCollection"), up.index("saveRecord"))
    for name in ("coding_questions", "ai_coding_rounds", "take_home_assignments"):
        assert up.index(f'findCollectionByNameOrId("{name}")') < first_write


def test_the_retired_slug_sets_match_the_touched_row_manifest(src, touched):
    assert set(_string_array(src, "RETIRED_AI_CODING")) == set(touched["ai_coding_rounds"]["retired"]["slugs"])
    assert set(_string_array(src, "RETIRED_TAKE_HOME")) == set(touched["take_home_assignments"]["retired"]["slugs"])


def test_the_active_slug_sets_match_the_touched_row_manifest(src, touched):
    # Only these slugs map to active version 1; any other row is left
    # unversioned and resolves to definition_not_found.
    assert _string_array(src, "ACTIVE_CODING") == sorted(touched["coding_questions"]["slugs"])
    assert _string_array(src, "ACTIVE_AI_CODING") == sorted(touched["ai_coding_rounds"]["active"]["slugs"])


def test_the_touched_manifest_matches_the_definitions_manifest(touched):
    man = json.loads((ROOT / "backend" / "definitions" / "manifest.json").read_text())
    active_coding = {e["slug"] for e in man["entries"]
                     if e["track"] == "coding" and e["kind"] == "test-definition" and e["lifecycle"] == "active"}
    assert set(touched["coding_questions"]["slugs"]) == active_coding
    for track, key, bucket in [("ai-coding", "active", touched["ai_coding_rounds"]["active"]),
                               ("ai-coding", "retired", touched["ai_coding_rounds"]["retired"]),
                               ("take-home", "retired", touched["take_home_assignments"]["retired"])]:
        expected = {e["slug"] for e in man["entries"] if e["track"] == track and e["lifecycle"] == key}
        assert set(bucket["slugs"]) == expected


# ---- behavioural: run up() and down() through node against a stub Dao ----

_HARNESS = r"""
const path = process.argv[2];
let up, down;
globalThis.migrate = (u, d) => { up = u; down = d; };
class Schema {
  constructor() { this.fields = []; }
  addField(f) { this.fields.push(f); }
  getFieldByName(n) { return this.fields.find((f) => f.name === n) || null; }
  removeField(id) { this.fields = this.fields.filter((f) => f.id !== id); }
}
globalThis.SchemaField = function (opts) { this.name = opts.name; this.type = opts.type; this.id = opts.name + "_id"; };
globalThis.Collection = function (opts) {
  Object.assign(this, opts);
  this.id = opts.name + "_id";
  this.schema = new Schema();
  for (const f of opts.schema || []) this.schema.addField(Object.assign({ id: f.name + "_id" }, f));
};
globalThis.Record = function (collection, data) {
  this.collection = collection.name;
  this._data = Object.assign({}, data);
  this.id = data.record ? "j_" + Math.random().toString(36).slice(2) : (data.id || null);
  this.set = (k, v) => { this._data[k] = v; };
  this.get = (k) => this._data[k];
  this.getString = (k) => (this._data[k] == null ? "" : String(this._data[k]));
};
function Dao(db) {
  this.collections = db.collections;
  this.rows = db.rows;
  this.findCollectionByNameOrId = (n) => { if (!this.collections[n]) throw new Error("missing collection " + n); return this.collections[n]; };
  this.saveCollection = (c) => { this.collections[c.name] = c; };
  this.deleteCollection = (c) => { delete this.collections[c.name]; db.deleted.push(c.name); };
  this.findRecordsByFilter = (n, _f) => this.rows[n] || [];
  this.saveRecord = (r) => {
    if (r.collection === "definition_migration_journal") { db.journal.push(Object.assign({}, r._data)); return; }
    const list = this.rows[r.collection] || (this.rows[r.collection] = []);
    if (!list.includes(r)) list.push(r);
  };
}
globalThis.Dao = Dao;

function makeRow(collection, data) {
  const r = { collection, _data: Object.assign({}, data), id: data.id };
  r.set = (k, v) => { r._data[k] = v; };
  r.get = (k) => r._data[k];
  r.getString = (k) => { const v = r._data[k]; return v == null ? "" : (typeof v === "string" ? v : JSON.stringify(v)); };
  return r;
}

function baseDb(extra) {
  const collections = {};
  for (const n of ["coding_questions", "ai_coding_rounds", "take_home_assignments"]) {
    collections[n] = new Collection({ name: n, type: "base", schema: [{ name: "slug", type: "text" }] });
  }
  const rows = {
    coding_questions: [
      makeRow("coding_questions", { id: "c1", slug: "two-sum", test_cases: [{ input: {} }, { input: {} }, "junk"] }),
      makeRow("coding_questions", { id: "c2", slug: "mystery-op", test_cases: [] }),
    ],
    ai_coding_rounds: [makeRow("ai_coding_rounds", { id: "a1", slug: "hallucinated-http-client" })],
    take_home_assignments: [],
  };
  if (extra === "legacy") {
    rows.ai_coding_rounds.push(makeRow("ai_coding_rounds", { id: "a2", slug: "word-count-py" }));
    rows.ai_coding_rounds.push(makeRow("ai_coding_rounds", { id: "a3", slug: "admin-added-round" }));
    rows.take_home_assignments.push(makeRow("take_home_assignments", { id: "t1", slug: "kv-store-py" }));
    rows.take_home_assignments.push(makeRow("take_home_assignments", { id: "t2", slug: "brand-new" }));
  }
  return { collections, rows, journal: [], deleted: [] };
}

require(path);
const out = {};
for (const variant of ["fresh", "legacy"]) {
  const db = baseDb(variant === "legacy" ? "legacy" : null);
  up(db);
  const rows = {};
  for (const [n, list] of Object.entries(db.rows)) {
    rows[n] = list.map((r) => ({ slug: r._data.slug, v: r._data.definition_version ?? null, caseIds: r._data.definition_case_ids ?? null }));
  }
  out[variant] = { rows, journal: db.journal, hasJournal: Boolean(db.collections["definition_migration_journal"]) };
}
// down() on the fresh result drops the columns and the journal collection.
const db = baseDb(null);
up(db);
const before = db.rows.coding_questions[0]._data.definition_version;
down(db);
out.down = {
  droppedJournal: db.deleted.includes("definition_migration_journal"),
  journalGone: !db.collections["definition_migration_journal"],
  codingFields: db.collections.coding_questions.schema.fields.map((f) => f.name),
  rowsUntouched: db.rows.coding_questions.length === 2 && before === 1,
};
process.stdout.write(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory) -> dict:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not on PATH")
    harness = tmp_path_factory.mktemp("def-expand") / "harness.cjs"
    harness.write_text(_HARNESS)
    res = subprocess.run([node, str(harness), str(MIGRATION)], capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def test_a_fresh_database_maps_coding_and_the_active_round(run):
    fresh = run["fresh"]
    assert fresh["hasJournal"] is True
    coding = {r["slug"]: r for r in fresh["rows"]["coding_questions"]}
    assert coding["two-sum"]["v"] == 1 and coding["two-sum"]["caseIds"] == ["c000", "c001"]
    (round_,) = fresh["rows"]["ai_coding_rounds"]
    assert round_["v"] == 1
    dispositions = {(j["collection"], j["slug"]): j["disposition"] for j in fresh["journal"]}
    assert dispositions[("ai_coding_rounds", "hallucinated-http-client")] == "active"
    assert dispositions[("coding_questions", "two-sum")] == "active"


def test_a_question_the_manifest_doesnt_compile_is_left_unversioned(run):
    # An admin-added question has no definition: no version, no case ids,
    # and a definition-not-found journal row, so step 2 answers
    # definition_not_found rather than running it.
    fresh = run["fresh"]
    coding = {r["slug"]: r for r in fresh["rows"]["coding_questions"]}
    assert coding["mystery-op"]["v"] is None and coding["mystery-op"]["caseIds"] is None
    journal = {(j["collection"], j["slug"]): (j["disposition"], j["definition_version"]) for j in fresh["journal"]}
    assert journal[("coding_questions", "mystery-op")] == ("definition-not-found", 0)
    # Every row still gets a journal row, mapped or not.
    assert len(fresh["journal"]) == sum(len(rows) for rows in fresh["rows"].values())


def test_a_pre_2026_05_16_database_retires_the_removed_samples(run):
    legacy = run["legacy"]
    dispositions = {(j["collection"], j["slug"]): (j["disposition"], j["definition_version"]) for j in legacy["journal"]}
    assert dispositions[("ai_coding_rounds", "word-count-py")] == ("retired", 1)
    # A round with no definition is left unversioned and not-found too.
    assert dispositions[("ai_coding_rounds", "admin-added-round")] == ("definition-not-found", 0)
    assert {r["slug"]: r["v"] for r in legacy["rows"]["ai_coding_rounds"]}["admin-added-round"] is None
    assert dispositions[("take_home_assignments", "kv-store-py")] == ("retired", 1)
    # A take-home with no definition is left unversioned and not-found.
    assert dispositions[("take_home_assignments", "brand-new")] == ("definition-not-found", 0)
    rows = {r["slug"]: r for r in legacy["rows"]["take_home_assignments"]}
    assert rows["kv-store-py"]["v"] == 1 and rows["brand-new"]["v"] is None
    # Every row still present: nothing deleted or recreated.
    assert len(legacy["rows"]["ai_coding_rounds"]) == 3
    assert len(legacy["rows"]["take_home_assignments"]) == 2


def test_down_drops_only_the_columns_and_the_journal(run):
    down = run["down"]
    assert down["droppedJournal"] and down["journalGone"]
    assert "definition_version" not in down["codingFields"]
    assert "definition_case_ids" not in down["codingFields"]
    assert down["rowsUntouched"] is True
