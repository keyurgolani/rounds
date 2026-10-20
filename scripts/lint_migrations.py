#!/usr/bin/env python3
"""Lints PocketBase migration changes (ROUNDS-00A-L01 stage 5).

PocketBase applies each ``.js`` and ``.ts`` file at the top of
``pocketbase/pb_migrations/`` once, records it by filename, and never runs
it again. So a change may only add migrations:

- an edit to an existing migration never reaches a database that already
  applied it, and deleting or renaming one breaks its own down step;
- a new migration's up step may not drop a collection or a field, or
  rewrite or delete existing rows, or load code the lint can't read;
- any other file in that directory fails too, so nothing slips in under a
  name the lint doesn't read.

The scan covers the whole file except the down step, so a helper defined
outside ``migrate(...)`` counts. It matches destructive and row-writing
calls by method name, whatever the receiver is called, plus SQL in a file
that runs newQuery(), so it catches mistakes; review still catches intent.
A finding passes only with an entry in
``scripts/migration-lint-allowlist.json`` that names the file, the rules it
may break, the issue that needs it, who reviewed it, and the SHA-256 of the
reviewed content, so any later edit needs a fresh review. The entry and
this lint come from the change under review, so they don't prove review on
their own. CODEOWNERS routes these files to the owner, and that review and
this check block a merge only once a ruleset on main and next requires
them; until then both are advisory. See docs/development.md#migrations.

TODO(ROUNDS-32-L02): #156's migration framework and #157's restore
rehearsal replace this lint.

usage: lint_migrations.py --base REV --head REV [--repo DIR] [--allowlist PATH]
exit status: 0 nothing blocking, 1 findings, 2 the lint couldn't run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

MIGRATIONS_DIR = "pocketbase/pb_migrations/"
# PocketBase 0.22's jsvm loads both from the top of the directory.
MIGRATION_SUFFIXES = (".js", ".ts")
DEFAULT_ALLOWLIST = "scripts/migration-lint-allowlist.json"

RULES: dict[str, str] = {
    "modified-migration": "edits a migration that already exists",
    "deleted-migration": "deletes a migration",
    "renamed-migration": "renames a migration",
    "drops-collection": "drops a collection outside its down step",
    "drops-field": "drops a field outside its down step",
    "rewrites-rows": "rewrites or deletes existing rows outside its down step",
    "loads-code": "loads code with require() that the lint can't read",
    "unparsed-migration": "has no migrate(up, down) call the lint can read",
    "unknown-file": f"is in {MIGRATIONS_DIR} but isn't a top-level .js or .ts migration",
}

# Checked against the scanned code, outside strings and comments, by method
# name whatever the receiver is called: db, dao, txDao, app, or anything else.
CODE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("drops-collection", re.compile(r"\b(?:deleteCollection|deleteTable|deleteView|dropTable|dropView)\s*\(")),
    # An import deletes the collections and fields it leaves out.
    ("drops-collection", re.compile(r"\bimportCollections\s*\(")),
    ("drops-field", re.compile(r"\b(?:removeField|removeById|removeByName|dropColumn)\s*\(")),
    # deleteRecord, deleteAdmin, app.delete, db.delete, and the like.
    ("rewrites-rows", re.compile(r"\bdelete(?!Collection\b|Table\b|View\b)\w*\s*\(")),
    ("rewrites-rows", re.compile(r"\btruncate\w*\s*\(")),
    # dbx's update and upsert, on the callback's db or anything else.
    ("rewrites-rows", re.compile(r"\.\s*(?:update|upsert)\s*\(")),
    ("loads-code", re.compile(r"\brequire\s*\(")),
)
# Raw SQL, checked in the strings of a file that calls newQuery().
SQL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("drops-collection", re.compile(r"\bDROP\s+(?:TABLE|VIEW)\b", re.I)),
    ("drops-field", re.compile(r"\bALTER\s+TABLE\b.*?\bDROP\b", re.I | re.S)),
    ("rewrites-rows", re.compile(r"\bDELETE\s+FROM\b", re.I)),
    ("rewrites-rows", re.compile(r"\bUPDATE\b.*?\bSET\b", re.I | re.S)),
    ("rewrites-rows", re.compile(r"\b(?:INSERT\s+OR\s+REPLACE|REPLACE\s+INTO|TRUNCATE)\b", re.I)),
)
# Looking up existing records or admins and saving in the same migration
# rewrites them: findRecordById, findAdminByEmail, findAuthRecordByEmail,
# and so on, with saveRecord, saveAdmin, or save. Collections don't count.
FIND_EXISTING = re.compile(r"\bfind(?!Collection)\w*\s*\(")
SAVE = re.compile(r"\bsave(?!Collection\b)\w*\s*\(")
NEW_QUERY = re.compile(r"\bnewQuery\s*\(")
MIGRATE_CALL = re.compile(r"\bmigrate\s*\(")

ENTRY_KEYS = {"path", "rules", "sha256", "issue", "reason", "reviewed_by"}
OPTIONAL_ENTRY_KEYS = {"manifest", "$comment"}
CONTROL = re.compile(r"[\x00-\x1f\x7f]")


class LintError(Exception):
    """The lint couldn't run; exit status 2."""


@dataclass(frozen=True)
class Change:
    status: str  # "A", "M", "D", or "R"
    path: str
    content: str | None = None  # the head content; None for a deletion
    base_content: str | None = None  # the base content for M, D, and R
    old_path: str | None = None  # for a rename


@dataclass(frozen=True)
class Finding:
    path: str
    rule: str
    line: int | None
    sha256: str

    def message(self) -> str:
        where = f"{self.path}:{self.line}" if self.line else self.path
        return f"{where}: {self.rule}: {RULES[self.rule]}"


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def in_migrations_dir(path: str) -> bool:
    return path.startswith(MIGRATIONS_DIR)


def is_migration(path: str) -> bool:
    """A file PocketBase loads as a migration: .js or .ts, at the top of
    the directory."""
    name = path[len(MIGRATIONS_DIR):] if in_migrations_dir(path) else ""
    return bool(name) and "/" not in name and name.endswith(MIGRATION_SUFFIXES)


# ---- reading JavaScript ----------------------------------------------------------


def blank_comments(source: str) -> str:
    """``source`` with comments replaced by spaces, strings and newlines
    kept, so offsets and line numbers still match the file."""
    out = list(source)
    i, n = 0, len(source)
    template_depth: list[int] = []  # brace depth at each open template ${
    brace_depth = 0
    while i < n:
        ch = source[i]
        nxt = source[i + 1] if i + 1 < n else ""
        if ch == "/" and nxt == "/":
            j = source.find("\n", i)
            j = n if j == -1 else j
            for k in range(i, j):
                out[k] = " "
            i = j
            continue
        if ch == "/" and nxt == "*":
            j = source.find("*/", i + 2)
            j = n if j == -1 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
            continue
        if ch in ("'", '"'):
            i = _skip_string(source, i, ch)
            continue
        if ch == "`":
            i = _skip_template(source, i, template_depth, brace_depth)
            continue
        if ch == "{":
            brace_depth += 1
        elif ch == "}":
            if template_depth and template_depth[-1] == brace_depth:
                template_depth.pop()
                i = _skip_template(source, i, template_depth, brace_depth)
                continue
            brace_depth -= 1
        i += 1
    return "".join(out)


def _skip_string(source: str, i: int, quote: str) -> int:
    j = i + 1
    while j < len(source):
        if source[j] == "\\":
            j += 2
            continue
        if source[j] == quote or source[j] == "\n":
            return j + 1
        j += 1
    return j


def _skip_template(source: str, i: int, template_depth: list[int], brace_depth: int) -> int:
    """Skip template text from its opening backtick, or from the brace that
    closes a ``${`` expression, to the closing backtick or the next ``${``."""
    j = i + 1
    while j < len(source):
        ch = source[j]
        if ch == "\\":
            j += 2
            continue
        if ch == "`":
            return j + 1
        if ch == "$" and j + 1 < len(source) and source[j + 1] == "{":
            template_depth.append(brace_depth)
            return j + 2
        j += 1
    return j


def _code_mask(source: str) -> list[bool]:
    """True at each offset that is code, not inside a string."""
    mask = [True] * len(source)
    i, n = 0, len(source)
    template_depth: list[int] = []
    brace_depth = 0
    while i < n:
        ch = source[i]
        if ch in ("'", '"'):
            j = _skip_string(source, i, ch)
            for k in range(i, min(j, n)):
                mask[k] = False
            i = j
            continue
        if ch == "`":
            j = _skip_template(source, i, template_depth, brace_depth)
            for k in range(i, min(j, n)):
                mask[k] = False
            i = j
            continue
        if ch == "{":
            brace_depth += 1
        elif ch == "}":
            if template_depth and template_depth[-1] == brace_depth:
                template_depth.pop()
                j = _skip_template(source, i, template_depth, brace_depth)
                for k in range(i, min(j, n)):
                    mask[k] = False
                i = j
                continue
            brace_depth -= 1
        i += 1
    return mask


def _string_runs(mask: list[bool]) -> list[tuple[int, int]]:
    """The (start, end) offsets of each stretch of string text."""
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for i, is_code in enumerate(mask):
        if not is_code and start is None:
            start = i
        elif is_code and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, len(mask)))
    return runs


def call_arguments(code: str, mask: list[bool], open_paren: int) -> list[tuple[int, int]] | None:
    """The (start, end) offsets of each top-level argument of the call
    whose ``(`` is at ``open_paren``, or None when it never closes."""
    depth = 0
    args: list[tuple[int, int]] = []
    start = open_paren + 1
    for i in range(open_paren, len(code)):
        if not mask[i]:
            continue
        ch = code[i]
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth == 0:
                if code[start:i].strip():
                    args.append((start, i))
                return args
        elif ch == "," and depth == 1:
            args.append((start, i))
            start = i + 1
    return None


def scanned_region(source: str) -> tuple[str, list[bool]] | None:
    """The file's code with comments removed and the down step blanked,
    plus its code mask, or None when there's no readable migrate() call."""
    code = blank_comments(source)
    mask = _code_mask(code)
    for match in MIGRATE_CALL.finditer(code):
        if not mask[match.start()]:
            continue
        args = call_arguments(code, mask, match.end() - 1)
        if not args:
            return None
        chars = list(code)
        if len(args) > 1:
            start, end = args[1]
            for k in range(start, end):
                if chars[k] != "\n":
                    chars[k] = " "
        return "".join(chars), mask
    return None


def _line(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def scan(source: str) -> list[tuple[str, int | None]]:
    """(rule, line) for every destructive operation outside the down step."""
    region = scanned_region(source)
    if region is None:
        return [("unparsed-migration", None)]
    code, mask = region
    hits: set[tuple[str, int | None]] = set()
    for rule, pattern in CODE_PATTERNS:
        for match in pattern.finditer(code):
            if mask[match.start()]:
                hits.add((rule, _line(code, match.start())))
    if any(mask[m.start()] for m in FIND_EXISTING.finditer(code)):
        for match in SAVE.finditer(code):
            if mask[match.start()]:
                hits.add(("rewrites-rows", _line(code, match.start())))
    queries = [m for m in NEW_QUERY.finditer(code) if mask[m.start()]]
    if queries:
        # Every string, so SQL built in a variable counts, plus each call's
        # whole argument list, so SQL split around a ${} expression counts.
        texts = [(start, code[start:end]) for start, end in _string_runs(mask)]
        for match in queries:
            args = call_arguments(code, mask, match.end() - 1)
            if args:
                texts.append((args[0][0], code[args[0][0]:args[-1][1]]))
        for offset, text in texts:
            for rule, pattern in SQL_PATTERNS:
                found = pattern.search(text)
                if found:
                    hits.add((rule, _line(code, offset + found.start())))
    return sorted(hits, key=lambda h: (h[1] or 0, h[0]))


# ---- the lint ----------------------------------------------------------------------


def load_allowlist(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise LintError(f"{path} is missing") from None
    except (OSError, ValueError) as err:
        raise LintError(f"{path} isn't valid JSON: {err}") from None
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("entries"), list):
        raise LintError(f'{path} needs {{"version": 1, "entries": [...]}}')
    entries = data["entries"]
    for index, entry in enumerate(entries):
        where = f"{path} entry {index}"
        if not isinstance(entry, dict):
            raise LintError(f"{where} isn't an object")
        missing = ENTRY_KEYS - set(entry)
        if missing:
            raise LintError(f"{where} is missing {', '.join(sorted(missing))}")
        unknown = set(entry) - ENTRY_KEYS - OPTIONAL_ENTRY_KEYS
        if unknown:
            raise LintError(f"{where} has unknown keys {', '.join(sorted(unknown))}")
        if not isinstance(entry["path"], str) or not in_migrations_dir(entry["path"]) or entry["path"] == MIGRATIONS_DIR:
            raise LintError(f"{where}: path must be a file under {MIGRATIONS_DIR}")
        rules = entry["rules"]
        if not isinstance(rules, list) or not rules or any(r not in RULES for r in rules):
            raise LintError(f"{where}: rules must be a non-empty list from {', '.join(RULES)}")
        if not isinstance(entry["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
            raise LintError(f"{where}: sha256 must be 64 lowercase hex characters")
        if not isinstance(entry["issue"], str) or not re.fullmatch(r"#[1-9]\d*", entry["issue"]):
            raise LintError(f'{where}: issue must look like "#14"')
        for key in ("reason", "reviewed_by", "manifest", "$comment"):
            if key not in entry:
                continue
            value = entry[key]
            if not isinstance(value, str) or not value.strip() or CONTROL.search(value):
                raise LintError(f"{where}: {key} must be non-empty text on one line")
        if CONTROL.search(entry["path"]):
            raise LintError(f"{where}: path must be text on one line")
    return entries


def _entry_for(finding: Finding, entries: list[dict]) -> dict | None:
    for entry in entries:
        if entry["path"] == finding.path and finding.rule in entry["rules"] and entry["sha256"] == finding.sha256:
            return entry
    return None


def _normalize(change: Change) -> list[Change]:
    """The change as it touches the migrations directory, one change per
    path: a rename between two migrations stays a rename, and any other
    rename that crosses the directory splits into a deletion of the old path
    and an addition of the new one. Paths outside the directory drop out."""
    if change.status == "R":
        old, new = change.old_path or "", change.path
        if is_migration(old) and is_migration(new):
            return [change]
        split = []
        if in_migrations_dir(old):
            split.append(Change("D", old, base_content=change.base_content))
        if in_migrations_dir(new):
            split.append(Change("A", new, content=change.content))
        return split
    return [change] if in_migrations_dir(change.path) else []


def lint(changes: list[Change], allowlist: list[dict]) -> tuple[list[Finding], list[Finding]]:
    """(blocking, allowed): the findings for ``changes``, split by whether
    an allowlist entry covers them."""
    findings: list[Finding] = []
    for change in (part for c in changes for part in _normalize(c)):
        if not is_migration(change.path):
            # Something PocketBase wouldn't load, or that the lint doesn't read.
            content = change.base_content if change.status == "D" else change.content
            findings.append(Finding(change.path, "unknown-file", None, sha256(content or "")))
            continue
        if change.status == "D":
            findings.append(Finding(change.path, "deleted-migration", None, sha256(change.base_content or "")))
            continue
        content = change.content or ""
        digest = sha256(content)
        if change.status == "M":
            findings.append(Finding(change.path, "modified-migration", None, digest))
            continue
        if change.status == "R":
            findings.append(Finding(change.path, "renamed-migration", None, digest))
        findings.extend(Finding(change.path, rule, line, digest) for rule, line in scan(content))
    blocking = [f for f in findings if _entry_for(f, allowlist) is None]
    allowed = [f for f in findings if _entry_for(f, allowlist) is not None]
    return blocking, allowed


def _git(repo: Path, *args: str) -> str:
    try:
        done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError) as err:
        stderr = getattr(err, "stderr", "") or ""
        raise LintError(f"git {' '.join(args)} failed: {stderr.strip() or err}") from None
    return done.stdout


def changes_from_git(repo: Path, base: str, head: str) -> list[Change]:
    """The migration changes ``head`` makes since its merge base with ``base``."""
    merge_base = _git(repo, "merge-base", base, head).strip()
    listing = _git(repo, "diff", "--name-status", "-M", "-z", merge_base, head, "--", MIGRATIONS_DIR)
    fields = [f for f in listing.split("\0") if f]

    def show(rev: str, path: str) -> str:
        if CONTROL.search(path):
            # Nothing PocketBase should load is named like this; refuse
            # rather than print it.
            raise LintError(f"a changed path under {MIGRATIONS_DIR} contains a control character")
        return _git(repo, "show", f"{rev}:{path}")

    changes: list[Change] = []
    i = 0
    while i < len(fields):
        status = fields[i][0]
        if status in ("R", "C"):
            old, new = fields[i + 1], fields[i + 2]
            i += 3
            if status == "R":
                changes.append(Change("R", new, content=show(head, new), base_content=show(merge_base, old), old_path=old))
            else:
                changes.append(Change("A", new, content=show(head, new)))
            continue
        path = fields[i + 1]
        i += 2
        if status == "A":
            changes.append(Change("A", path, content=show(head, path)))
        elif status == "D":
            changes.append(Change("D", path, base_content=show(merge_base, path)))
        else:  # M, T, and anything else count as an edit in place
            changes.append(Change("M", path, content=show(head, path), base_content=show(merge_base, path)))
    return changes


def _property(value: str) -> str:
    return value.replace("%", "%25").replace(":", "%3A").replace(",", "%2C")


def _report(blocking: list[Finding], allowed: list[Finding], allowlist: list[dict], allowlist_path: str) -> None:
    annotate = os.environ.get("GITHUB_ACTIONS") == "true"

    def annotation(kind: str, f: Finding, text: str) -> None:
        if annotate:
            line = f",line={f.line}" if f.line else ""
            print(f"::{kind} file={_property(f.path)}{line}::{text.replace('%', '%25')}")

    for f in allowed:
        entry = _entry_for(f, allowlist) or {}
        print(f"{f.message()} (allowed for {entry.get('issue')}: {entry.get('reason')})")
        annotation("notice", f, f"{f.rule} allowed for {entry.get('issue')}")
    for f in blocking:
        print(f.message())
        annotation("error", f, f"{f.rule}: {RULES[f.rule]}")
        stale = [e["issue"] for e in allowlist if e["path"] == f.path and f.rule in e["rules"]]
        if stale:
            print(f"  the entry for {', '.join(stale)} was reviewed against other content of this file")
    if not blocking:
        return
    print()
    print("Add a new migration instead of editing, deleting, or renaming one, and keep")
    print("drops and row rewrites out of a new migration's up step. If the change is")
    print(f"intended, get it reviewed and add this to the entries in {allowlist_path}:")
    grouped: dict[tuple[str, str], list[str]] = {}
    for f in blocking:
        rules = grouped.setdefault((f.path, f.sha256), [])
        if f.rule not in rules:
            rules.append(f.rule)
    for (path, digest), rules in grouped.items():
        entry = {"path": path, "rules": rules, "sha256": digest, "issue": "#NNN", "reason": "...", "reviewed_by": "..."}
        print("  " + json.dumps(entry))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint PocketBase migration changes.")
    parser.add_argument("--base", required=True, help="the target branch revision")
    parser.add_argument("--head", required=True, help="the revision under review")
    parser.add_argument("--repo", default=".", help="the repository root")
    parser.add_argument("--allowlist", default=DEFAULT_ALLOWLIST, help="the allowlist, relative to --repo")
    args = parser.parse_args(argv)
    repo = Path(args.repo)
    try:
        allowlist = load_allowlist(repo / args.allowlist)
        changes = changes_from_git(repo, args.base, args.head)
    except LintError as err:
        print(f"lint_migrations: {err}", file=sys.stderr)
        return 2
    blocking, allowed = lint(changes, allowlist)
    _report(blocking, allowed, allowlist, args.allowlist)
    if blocking:
        return 1
    print(f"lint_migrations: {len(changes)} migration change(s), nothing blocking.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
