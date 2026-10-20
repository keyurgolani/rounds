"""Migration lint (ROUNDS-00A-L01 stage 5, scripts/lint_migrations.py).

A change may add migrations. Editing, deleting, or renaming one fails, and
so does a new one whose up step drops a collection or a field or rewrites
rows, unless a reviewed allowlist entry pins that exact file."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("lint_migrations", ROOT / "scripts" / "lint_migrations.py")
lm = importlib.util.module_from_spec(_spec)
sys.modules["lint_migrations"] = lm
_spec.loader.exec_module(lm)

MIG = "pocketbase/pb_migrations/"

ADDITIVE = """/// <reference path="../pb_data/types.d.ts" />
migrate((db) => {
  const dao = new Dao(db);
  const users = dao.findCollectionByNameOrId("users");
  const notes = new Collection({
    name: "notes",
    type: "base",
    listRule: "user = @request.auth.id",
    schema: [{ name: "user", type: "relation", options: { collectionId: users.id, cascadeDelete: true } }],
  });
  dao.saveCollection(notes);
  const tips = dao.findCollectionByNameOrId("tips");
  tips.schema.addField(new SchemaField({ name: "rank", type: "number" }));
  dao.saveCollection(tips);
}, (db) => {
  const dao = new Dao(db);
  dao.deleteCollection(dao.findCollectionByNameOrId("notes"));
  const tips = dao.findCollectionByNameOrId("tips");
  tips.schema.removeField("rank");
  dao.saveCollection(tips);
  dao.db().newQuery("DELETE FROM tips WHERE rank IS NULL").execute();
});
"""


def _up(body: str, down: str = "") -> str:
    return f"migrate((db) => {{\n  const dao = new Dao(db);\n{body}\n}}, (db) => {{\n{down}\n}});\n"


def _rules(source: str) -> list[str]:
    return [rule for rule, _line in lm.scan(source)]


# ---- what a new migration's up step may do ---------------------------------------------------


def test_an_additive_migration_is_clean_even_with_a_destructive_down_step():
    assert lm.scan(ADDITIVE) == []


@pytest.mark.parametrize(
    "body, rule",
    [
        ('  dao.deleteCollection(dao.findCollectionByNameOrId("old"));', "drops-collection"),
        ("  dao.importCollections(snapshot, true, null);", "drops-collection"),
        ('  dao.db().dropTable("old").execute();', "drops-collection"),
        ('  const c = dao.findCollectionByNameOrId("x");\n  c.schema.removeField("y");\n  dao.saveCollection(c);', "drops-field"),
        ('  const c = app.findCollectionByNameOrId("x");\n  c.fields.removeByName("y");\n  app.save(c);', "drops-field"),
        ('  dao.db().dropColumn("x", "y").execute();', "drops-field"),
        ('  dao.deleteRecord(dao.findRecordById("x", "abc"));', "rewrites-rows"),
        ('  app.truncateCollection(app.findCollectionByNameOrId("x"));', "rewrites-rows"),
        ('  app.delete(record);', "rewrites-rows"),
        ('  dao.db().update("users", { verified: false }, null).execute();', "rewrites-rows"),
    ],
)
def test_a_destructive_up_step_is_flagged(body, rule):
    assert rule in _rules(_up(body))


def test_reading_existing_records_and_saving_rewrites_rows():
    body = '  const r = dao.findFirstRecordByData("users", "email", "a@example.test");\n  r.set("name", "x");\n  dao.saveRecord(r);'
    assert lm.scan(_up(body)) == [("rewrites-rows", 5)]


def test_seeding_new_records_is_clean():
    body = '  const c = dao.findCollectionByNameOrId("tips");\n  dao.saveRecord(new Record(c, { text: "hello" }));'
    assert lm.scan(_up(body)) == []


@pytest.mark.parametrize(
    "body",
    [
        '  dao.db().newQuery("DELETE FROM sessions WHERE 1 = 1").execute();',
        "  const sql = \"UPDATE users SET name = ''\";\n  dao.db().newQuery(sql).execute();",
        "  const t = \"users\";\n  dao.db().newQuery(`UPDATE ${t} SET verified = false`).execute();",
        '  dao.db().newQuery("ALTER TABLE users DROP COLUMN legacy").execute();',
        '  dao.db().newQuery("DROP TABLE legacy").execute();',
    ],
)
def test_raw_sql_that_drops_or_rewrites_is_flagged(body):
    assert _rules(_up(body))


def test_sql_words_in_a_file_that_runs_no_sql_are_clean():
    body = '  const c = new Collection({ name: "tips" });\n  c.description = "Delete from your list, then update the set you keep.";\n  dao.saveCollection(c);'
    assert lm.scan(_up(body)) == []


def test_comments_and_strings_dont_count():
    body = (
        "  // dao.deleteCollection(old) ran in an earlier migration\n"
        "  /* c.schema.removeField(\"y\") */\n"
        '  const note = "never call deleteRecord( here";\n'
        "  const t = `deleteCollection(${note})`;"
    )
    assert lm.scan(_up(body)) == []


def test_a_helper_outside_migrate_counts():
    source = 'function wipe(dao) {\n  dao.deleteRecord(dao.findRecordById("x", "a"));\n}\n' + _up("  wipe(dao);")
    assert lm.scan(source) == [("rewrites-rows", 2)]


def test_the_line_points_at_the_call():
    source = _up('  const x = 1;\n  dao.deleteCollection(dao.findCollectionByNameOrId("old"));')
    assert lm.scan(source) == [("drops-collection", 4)]


@pytest.mark.parametrize("source", ["// nothing to migrate\n", "migrate(\n", "const migrate = 1;\n"])
def test_a_file_without_a_readable_migrate_call_is_flagged(source):
    assert lm.scan(source) == [("unparsed-migration", None)]


def test_every_existing_migration_parses():
    for path in sorted((ROOT / MIG).glob("*.js")):
        assert ("unparsed-migration", None) not in lm.scan(path.read_text()), path.name


# ---- what a change may do to existing migrations ---------------------------------------------


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _entry(path: str, rules: list[str], content: str, **extra) -> dict:
    return {"path": path, "rules": rules, "sha256": _sha(content), "issue": "#14", "reason": "Reviewed cutover.", "reviewed_by": "keyurgolani", **extra}


@pytest.mark.parametrize(
    "change, rule",
    [
        (lm.Change("M", MIG + "1_a.js", content="edited", base_content="original"), "modified-migration"),
        (lm.Change("D", MIG + "1_a.js", base_content="original"), "deleted-migration"),
        (lm.Change("R", MIG + "2_a.js", content=ADDITIVE, base_content=ADDITIVE, old_path=MIG + "1_a.js"), "renamed-migration"),
        (lm.Change("R", "attic/1_a.js", content="x", base_content="x", old_path=MIG + "1_a.js"), "deleted-migration"),
    ],
)
def test_editing_deleting_or_renaming_a_migration_is_flagged(change, rule):
    blocking, allowed = lm.lint([change], [])
    assert [f.rule for f in blocking] == [rule] and allowed == []


def test_moving_a_file_into_the_migrations_scans_it_as_new():
    change = lm.Change("R", MIG + "3_a.js", content=_up("  app.delete(r);"), base_content="", old_path="drafts/3_a.js")
    blocking, _allowed = lm.lint([change], [])
    assert [f.rule for f in blocking] == ["rewrites-rows"]


def test_files_that_arent_migrations_are_ignored():
    changes = [
        lm.Change("M", "pocketbase/pb_hooks/main.pb.js", content="x", base_content="y"),
        lm.Change("D", MIG + "README.md", base_content="notes"),
        lm.Change("A", "backend/app/x.js", content=_up("  app.delete(r);")),
    ]
    assert lm.lint(changes, []) == ([], [])


def test_a_new_additive_migration_passes():
    assert lm.lint([lm.Change("A", MIG + "9_notes.js", content=ADDITIVE)], []) == ([], [])


def test_an_allowlist_entry_passes_that_exact_file_and_rule():
    content = _up('  dao.deleteCollection(dao.findCollectionByNameOrId("old"));')
    change = lm.Change("A", MIG + "9_drop.js", content=content)
    blocking, allowed = lm.lint([change], [_entry(MIG + "9_drop.js", ["drops-collection"], content)])
    assert blocking == [] and [f.rule for f in allowed] == ["drops-collection"]


def test_an_allowlist_entry_for_other_content_or_another_rule_doesnt_pass():
    content = _up('  dao.deleteCollection(dao.findCollectionByNameOrId("old"));')
    change = lm.Change("A", MIG + "9_drop.js", content=content)
    stale = _entry(MIG + "9_drop.js", ["drops-collection"], content + "// edited after review\n")
    other_rule = _entry(MIG + "9_drop.js", ["rewrites-rows"], content)
    other_file = _entry(MIG + "8_drop.js", ["drops-collection"], content)
    for entry in (stale, other_rule, other_file):
        blocking, allowed = lm.lint([change], [entry])
        assert [f.rule for f in blocking] == ["drops-collection"] and allowed == []


def test_an_edit_needs_its_own_entry_pinned_to_the_new_content():
    change = lm.Change("M", MIG + "1_seed.js", content="edited", base_content="original")
    assert lm.lint([change], [_entry(MIG + "1_seed.js", ["modified-migration"], "edited")])[0] == []
    assert lm.lint([change], [_entry(MIG + "1_seed.js", ["modified-migration"], "original")])[0] != []


def test_a_deletion_is_pinned_to_the_deleted_content():
    change = lm.Change("D", MIG + "1_seed.js", base_content="original")
    assert lm.lint([change], [_entry(MIG + "1_seed.js", ["deleted-migration"], "original")])[0] == []


# ---- the allowlist file ----------------------------------------------------------------------


def _allowlist(tmp_path, entries) -> Path:
    path = tmp_path / "allowlist.json"
    path.write_text(json.dumps({"version": 1, "entries": entries}))
    return path


def test_the_repository_allowlist_loads():
    assert isinstance(lm.load_allowlist(ROOT / lm.DEFAULT_ALLOWLIST), list)


def test_an_entry_can_name_its_manifest(tmp_path):
    entry = _entry(MIG + "1_a.js", ["rewrites-rows"], "x", manifest="demo-contain-v1")
    assert lm.load_allowlist(_allowlist(tmp_path, [entry])) == [entry]


@pytest.mark.parametrize(
    "change",
    [
        {"sha256": "abc"},
        {"sha256": "A" * 64},
        {"issue": "14"},
        {"issue": "#0"},
        {"rules": []},
        {"rules": ["drops-everything"]},
        {"path": "pocketbase/pb_hooks/main.pb.js"},
        {"path": MIG + "README.md"},
        {"reason": " "},
        {"reviewed_by": ""},
        {"reason": "line one\nline two"},
        {"manifest": ""},
        {"approved": True},
    ],
)
def test_a_malformed_entry_stops_the_lint(tmp_path, change):
    entry = {**_entry(MIG + "1_a.js", ["rewrites-rows"], "x"), **change}
    with pytest.raises(lm.LintError):
        lm.load_allowlist(_allowlist(tmp_path, [entry]))


@pytest.mark.parametrize("missing", sorted(lm.ENTRY_KEYS))
def test_an_entry_missing_a_field_stops_the_lint(tmp_path, missing):
    entry = _entry(MIG + "1_a.js", ["rewrites-rows"], "x")
    del entry[missing]
    with pytest.raises(lm.LintError):
        lm.load_allowlist(_allowlist(tmp_path, [entry]))


@pytest.mark.parametrize("text", ["", "{", "[]", '{"version": 2, "entries": []}', '{"version": 1}'])
def test_an_unreadable_allowlist_stops_the_lint(tmp_path, text):
    path = tmp_path / "allowlist.json"
    path.write_text(text)
    with pytest.raises(lm.LintError):
        lm.load_allowlist(path)


# ---- end to end, through git -------------------------------------------------------------------


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A repository with one migration and an empty allowlist on main. Git
    reads no global or system config."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for key in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{key}_NAME", "Lint Test")
        monkeypatch.setenv(f"GIT_{key}_EMAIL", "lint@example.test")
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / MIG).mkdir(parents=True)
    (root / lm.DEFAULT_ALLOWLIST).write_text(json.dumps({"version": 1, "entries": []}))
    (root / MIG / "1700000000_init.js").write_text(ADDITIVE)
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    git(root, "switch", "-q", "-c", "change")
    return root


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def commit(root: Path, message: str = "change") -> None:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)


def run_lint(root: Path, base: str = "main", head: str = "HEAD") -> int:
    return lm.main(["--repo", str(root), "--base", base, "--head", head])


def test_an_edit_to_an_existing_migration_fails(repo, capsys):
    (repo / MIG / "1700000000_init.js").write_text(ADDITIVE + "// one more line\n")
    commit(repo)
    assert run_lint(repo) == 1
    assert "1700000000_init.js: modified-migration" in capsys.readouterr().out


def test_deleting_an_existing_migration_fails(repo, capsys):
    (repo / MIG / "1700000000_init.js").unlink()
    commit(repo)
    assert run_lint(repo) == 1
    assert "deleted-migration" in capsys.readouterr().out


def test_a_new_migration_that_drops_a_collection_fails_with_a_suggested_entry(repo, capsys):
    content = _up('  dao.deleteCollection(dao.findCollectionByNameOrId("old"));')
    (repo / MIG / "1700009000_drop.js").write_text(content)
    commit(repo)
    assert run_lint(repo) == 1
    out = capsys.readouterr().out
    assert "1700009000_drop.js:3: drops-collection" in out
    suggestion = json.loads(out.strip().splitlines()[-1])
    assert suggestion["sha256"] == _sha(content) and suggestion["rules"] == ["drops-collection"]


def test_an_allowlisted_drop_passes_and_is_reported(repo, capsys, monkeypatch):
    content = _up('  dao.deleteCollection(dao.findCollectionByNameOrId("old"));')
    (repo / MIG / "1700009000_drop.js").write_text(content)
    entry = _entry(MIG + "1700009000_drop.js", ["drops-collection"], content)
    (repo / lm.DEFAULT_ALLOWLIST).write_text(json.dumps({"version": 1, "entries": [entry]}))
    commit(repo)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    assert run_lint(repo) == 0
    out = capsys.readouterr().out
    assert "::notice file=pocketbase/pb_migrations/1700009000_drop.js,line=3::drops-collection allowed for #14" in out


def test_a_finding_is_annotated_in_actions(repo, capsys, monkeypatch):
    (repo / MIG / "1700000000_init.js").unlink()
    commit(repo)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    assert run_lint(repo) == 1
    assert "::error file=pocketbase/pb_migrations/1700000000_init.js::deleted-migration" in capsys.readouterr().out


def test_a_new_additive_migration_passes_end_to_end(repo):
    (repo / MIG / "1700009000_notes.js").write_text(ADDITIVE)
    (repo / "README.md").write_text("unrelated\n")
    commit(repo)
    assert run_lint(repo) == 0


def test_against_a_merge_commit_only_what_the_merge_adds_counts(repo):
    # CI lints the pull request merged into its base: HEAD^1 against HEAD.
    (repo / MIG / "1700009000_notes.js").write_text(ADDITIVE)
    commit(repo, "feature")
    git(repo, "switch", "-q", "main")
    (repo / "README.md").write_text("main moved on\n")
    commit(repo, "main")
    git(repo, "merge", "-q", "--no-ff", "--no-edit", "change")
    assert run_lint(repo, base="HEAD^1", head="HEAD") == 0
    (repo / MIG / "1700009100_drop.js").write_text(_up("  app.delete(r);"))
    commit(repo, "after the merge")
    assert run_lint(repo, base="HEAD^1", head="HEAD") == 1


def test_a_bad_revision_or_allowlist_exits_2(repo, capsys):
    assert run_lint(repo, base="no-such-branch") == 2
    (repo / lm.DEFAULT_ALLOWLIST).write_text("{")
    assert run_lint(repo) == 2
    assert "lint_migrations:" in capsys.readouterr().err
