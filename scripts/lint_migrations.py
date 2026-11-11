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
  name the lint doesn't read;
- a JSON field maxSize that a new migration sets must be registered, at the
  size the migrations end on, in a ``NNNN_json_limits*.js`` migration. Those
  sort after PocketBase's own migration that resets every JSON limit to
  2,000,000 bytes, and set the declared limits back (decision D10, see
  docs/development.md#json-field-limits).

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
    "unregistered-json-limit": "sets a JSON field's maxSize that no json_limits migration registers at that size",
    "unreadable-json-limit": "declares a JSON field or sets a maxSize the lint can't tie to one collection, field, "
                             "and size",
    "json-limits-registry": "is a json_limits migration that doesn't sort after PocketBase's JSON reset, or whose "
                            "LIMITS isn't a literal list of [collection, field, bytes]",
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


# ---- JSON field limits (D10) ---------------------------------------------------------

# PocketBase 0.22's own migration that sets every JSON field's maxSize to its
# 2,000,000-byte default. It sorts after every 1700xxxxxx migration, so on a
# fresh database it overwrites what they declare. Each json_limits migration
# sorts after it and sets the declared limits back from its LIMITS registry,
# a later file's entry winning over an earlier one's.
JSON_RESET = "1702134272_set_default_json_max_size.go"
JSON_DEFAULT_BYTES = 2_000_000
REGISTRY_FILE = re.compile(r"\A\d+_json_limits(?:_[a-z0-9]+)*\.js\Z")
JSON_RULES = ("unregistered-json-limit", "unreadable-json-limit", "json-limits-registry")

_IDENT = r"[A-Za-z_$][\w$]*"
_DECL = re.compile(rf"\b(?:const|let|var)\s+({_IDENT})\s*=(?![=>])\s*")
_FOR_OF = re.compile(rf"\bfor\s*\(\s*(?:const|let|var)\s+({_IDENT})\s+of\b\s*")
_JSON_TYPE = re.compile(r"\btype\s*:\s*([\"'])json\1")
_MAX_SIZE = re.compile(r"\bmaxSize\b")
_SET_MAX_SIZE = re.compile(r"\.\s*options\s*\.\s*maxSize\s*=(?!=)\s*")
_CHANGE_MAX_SIZE = re.compile(r"\bmaxSize\s*(?:[-+*/%&|^]|\*\*|<<|>>>?|\?\?|&&|\|\|)=")
_LIMITS = re.compile(r"\bconst\s+LIMITS\s*=\s*(?=\[)")
_REGISTRY_ENTRY = re.compile(r'\A\[\s*"([a-z][a-z0-9_]*)"\s*,\s*"([A-Za-z_][A-Za-z0-9_]*)"\s*,\s*([1-9][0-9]*)\s*\]\Z')
_NUMBER_TOKEN = re.compile(rf"\s*(\d[\d_]*|{_IDENT}|[*+\-()]|\S)")
# Past this many look-ups a name is unreadable, so a loop can't hang the lint.
_MAX_DEPTH = 12


@dataclass(frozen=True)
class JsonEvent:
    """One change a migration's up step makes to the JSON field limits: it
    sets a field's maxSize (``set``), drops a collection (``drop``), or
    removes a field (``remove``)."""

    kind: str
    collection: str
    field: str | None
    size: int | None
    line: int


@dataclass(frozen=True)
class _Decl:
    name: str
    offset: int
    scope: tuple[int, int]
    init: tuple[int, int] | None  # None for a for-of loop variable
    values: tuple[str, ...] | None = None  # a loop variable's strings


# A call argument the name of a helper's parameter stands for: its span and
# the offset its own names resolve from.
_Env = dict[str, tuple[int, int, int]]


class _Reader:
    """Finds the JSON limits in one migration's code, comments removed and
    the down step blanked. It reads the shapes the repository's migrations
    use: field objects in a ``new Collection`` schema, in
    ``X.schema.addField(new SchemaField(...))``, or in a local helper's
    schema array (``ensureCollection("name", [...])``); arrow-function field
    helpers such as ``json("tags")``; ``X.schema.getFieldByName("f")
    .options.maxSize = ...``; constants and for-of loops over literal
    arrays. Anything else that sets a maxSize, or a JSON field without
    one, is unreadable."""

    def __init__(self, code: str, mask: list[bool]) -> None:
        self.code, self.mask, self.n = code, mask, len(code)
        self.close: dict[int, int] = {}
        self.open_of: dict[int, int] = {}
        self.opens: list[int] = []
        stack: list[int] = []
        for i, ch in enumerate(code):
            if not mask[i]:
                continue
            if ch in "([{":
                stack.append(i)
                self.opens.append(i)
            elif ch in ")]}" and stack:
                opened = stack.pop()
                self.close[opened] = i
                self.open_of[i] = opened
        for opened in stack:
            self.close[opened] = self.n
        self.decls: list[_Decl] = []
        for m in _DECL.finditer(code):
            if mask[m.start()]:
                self.decls.append(_Decl(m.group(1), m.start(1), self._scope(m.start()),
                                        (m.end(), self._expression_end(m.end()))))
        for m in _FOR_OF.finditer(code):
            if mask[m.start()]:
                paren = code.index("(", m.start())
                values = self._string_list(m.end(), self.close.get(paren, self.n), m.start())
                self.decls.append(_Decl(m.group(1), m.start(1), self._loop_scope(paren), None, values))
        self.found: list[tuple[int, JsonEvent]] = []
        self.unreadable: list[tuple[int, str]] = []
        self.options_read: set[int] = set()  # the options objects of JSON fields read
        self.sizes_set: set[int] = set()  # the maxSize of each assignment read

    # ---- positions

    def line(self, offset: int) -> int:
        return _line(self.code, offset)

    def enclosing(self, offset: int) -> int | None:
        """The innermost bracket that opens before ``offset`` and closes
        after it."""
        best = None
        for opened in self.opens:
            if opened >= offset:
                break
            if self.close[opened] > offset:
                best = opened
        return best

    def before(self, offset: int, pattern: str) -> re.Match[str] | None:
        """``pattern`` matched right before ``offset``."""
        start = max(0, offset - 400)
        return re.search(f"(?:{pattern})\\s*\\Z", self.code[start:offset])

    def _next_code(self, offset: int) -> int:
        while offset < self.n and self.code[offset].isspace():
            offset += 1
        return offset

    def _last_code(self, offset: int) -> int:
        """The offset of the last non-space character before ``offset``."""
        offset -= 1
        while offset >= 0 and self.code[offset].isspace():
            offset -= 1
        return offset

    def _scope(self, offset: int) -> tuple[int, int]:
        opened = self.enclosing(offset)
        return (0, self.n) if opened is None else (opened, self.close[opened])

    def _loop_scope(self, paren: int) -> tuple[int, int]:
        body = self._next_code(self.close.get(paren, self.n) + 1)
        if body < self.n and self.code[body] == "{" and self.mask[body]:
            return (paren, self.close.get(body, self.n))
        return (paren, self._expression_end(body))

    def _expression_end(self, start: int) -> int:
        depth = 0
        for i in range(start, self.n):
            if not self.mask[i]:
                continue
            ch = self.code[i]
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                if depth == 0:
                    return i
                depth -= 1
            elif depth == 0 and ch in ";,\n":
                return i
        return self.n

    def _trim(self, start: int, end: int) -> tuple[int, int]:
        start = self._next_code(start)
        while end > start and self.code[end - 1].isspace():
            end -= 1
        return start, end

    def lookup(self, name: str, at: int) -> _Decl | None:
        """The declaration of ``name`` in scope at ``at``: the last one
        before it whose block holds it."""
        best = None
        for decl in self.decls:
            if decl.name == name and decl.offset < at and decl.scope[0] <= at <= decl.scope[1]:
                if best is None or decl.offset > best.offset:
                    best = decl
        return best

    # ---- values

    def string_at(self, start: int, end: int) -> str | None:
        start, end = self._trim(start, end)
        text = self.code[start:end]
        if len(text) >= 2 and text[0] in "'\"" and text[-1] == text[0] and text[0] not in text[1:-1] \
                and "\\" not in text and not self.mask[start]:
            return text[1:-1]
        return None

    def strings(self, start: int, end: int, at: int, env: _Env | None = None,
                depth: int = 0) -> tuple[str, ...] | None:
        """The strings an expression can be: a literal, a constant, a
        helper's parameter, or each value of a for-of loop variable."""
        if depth > _MAX_DEPTH:
            return None
        literal = self.string_at(start, end)
        if literal is not None:
            return (literal,)
        start, end = self._trim(start, end)
        name = self.code[start:end]
        if not re.fullmatch(_IDENT, name):
            return None
        if env and name in env:
            arg_start, arg_end, arg_at = env[name]
            return self.strings(arg_start, arg_end, arg_at, None, depth + 1)
        decl = self.lookup(name, at)
        if decl is None:
            return None
        if decl.init is None:
            return decl.values
        return self.strings(decl.init[0], decl.init[1], decl.offset, None, depth + 1)

    def _string_list(self, start: int, end: int, at: int, depth: int = 0) -> tuple[str, ...] | None:
        """The strings of a literal array, or of a constant holding one."""
        if depth > _MAX_DEPTH:
            return None
        start, end = self._trim(start, end)
        if start < end and self.code[start] == "[" and self.close.get(start) == end - 1:
            out: list[str] = []
            for arg_start, arg_end in call_arguments(self.code, self.mask, start) or []:
                literal = self.string_at(arg_start, arg_end)
                if literal is None:
                    return None
                out.append(literal)
            return tuple(out)
        name = self.code[start:end]
        if re.fullmatch(_IDENT, name):
            decl = self.lookup(name, at)
            if decl is not None and decl.init is not None:
                return self._string_list(decl.init[0], decl.init[1], decl.offset, depth + 1)
        return None

    def number(self, start: int, end: int, at: int, env: _Env | None = None, depth: int = 0) -> int | None:
        """An integer expression of literals, constants, and a helper's
        parameters with ``+``, ``-``, ``*``, and parentheses."""
        if depth > _MAX_DEPTH:
            return None
        tokens = [m.group(1) for m in _NUMBER_TOKEN.finditer(self.code[start:end])]
        pos = 0

        def factor() -> int | None:
            nonlocal pos
            if pos >= len(tokens):
                return None
            token = tokens[pos]
            pos += 1
            if token == "(":
                value = expression()
                if value is None or pos >= len(tokens) or tokens[pos] != ")":
                    return None
                pos += 1
                return value
            if token[0].isdigit():
                return int(token.replace("_", ""))
            if re.fullmatch(_IDENT, token):
                if env and token in env:
                    arg_start, arg_end, arg_at = env[token]
                    return self.number(arg_start, arg_end, arg_at, None, depth + 1)
                decl = self.lookup(token, at)
                if decl is None or decl.init is None:
                    return None
                return self.number(decl.init[0], decl.init[1], decl.offset, None, depth + 1)
            return None

        def term() -> int | None:
            nonlocal pos
            value = factor()
            while value is not None and pos < len(tokens) and tokens[pos] == "*":
                pos += 1
                right = factor()
                value = None if right is None else value * right
            return value

        def expression() -> int | None:
            nonlocal pos
            value = term()
            while value is not None and pos < len(tokens) and tokens[pos] in ("+", "-"):
                op = tokens[pos]
                pos += 1
                right = term()
                value = None if right is None else (value + right if op == "+" else value - right)
            return value

        value = expression()
        return value if value is not None and pos == len(tokens) else None

    def properties(self, brace: int) -> dict[str, tuple[int, int]] | None:
        """An object literal's properties and their value spans, or None
        when one is a spread, a method, or a computed or quoted key."""
        args = call_arguments(self.code, self.mask, brace)
        if args is None:
            return None
        props: dict[str, tuple[int, int]] = {}
        for start, end in args:
            text = self.code[start:end]
            keyed = re.match(rf"\s*({_IDENT})\s*:(?!:)\s*", text)
            if keyed:
                props[keyed.group(1)] = (start + keyed.end(), end)
                continue
            short = re.fullmatch(rf"\s*({_IDENT})\s*", text)
            if short:
                props[short.group(1)] = (start + short.start(1), start + short.end(1))
                continue
            return None
        return props

    def _object(self, start: int, end: int) -> int | None:
        """The opening brace when the span is exactly one object literal."""
        start, end = self._trim(start, end)
        if start < end and self.code[start] == "{" and self.mask[start] and self.close.get(start) == end - 1:
            return start
        return None

    def _call(self, start: int, end: int) -> tuple[str, int] | None:
        """(callee text, opening parenthesis) when the span is exactly one
        call."""
        start, end = self._trim(start, end)
        if start >= end or self.code[end - 1] != ")" or not self.mask[end - 1]:
            return None
        paren = self.open_of.get(end - 1)
        if paren is None or paren <= start:
            return None
        return self.code[start:paren].strip(), paren

    # ---- collections

    def collections(self, start: int, end: int, at: int, depth: int = 0) -> tuple[str, ...] | None:
        """The collections an expression names: a binding, a lookup by
        name, a ``new Collection``, or a local helper called with the
        collection's name first."""
        if depth > _MAX_DEPTH:
            return None
        start, end = self._trim(start, end)
        name = self.code[start:end]
        if re.fullmatch(_IDENT, name):
            decl = self.lookup(name, at)
            if decl is None:
                return None
            if decl.init is None:
                return decl.values
            return self.collections(decl.init[0], decl.init[1], decl.offset, depth + 1)
        call = self._call(start, end)
        if call is None:
            return None
        callee, paren = call
        args = call_arguments(self.code, self.mask, paren) or []
        if not args:
            return None
        if re.search(r"\.\s*findCollectionByNameOrId\Z", callee):
            return self.strings(*args[0], at)
        if re.fullmatch(r"new\s+Collection", callee):
            brace = self._object(*args[0])
            props = self.properties(brace) if brace is not None else None
            return self.strings(*props["name"], brace) if props and "name" in props else None
        if re.fullmatch(_IDENT, callee) and self.lookup(callee, start) is not None:
            return self.strings(*args[0], at)
        return None

    def _receiver(self, dot: int, at: int) -> tuple[str, ...] | None:
        """The collections the expression ending just before ``dot`` names."""
        last = self._last_code(dot)
        if last < 0:
            return None
        if self.code[last] == ")" and self.mask[last]:
            paren = self.open_of.get(last)
            if paren is None:
                return None
            head = re.search(rf"({_IDENT}(?:\s*\.\s*{_IDENT})*)\s*\Z", self.code[max(0, paren - 400):paren])
            if head is None:
                return None
            return self.collections(paren - len(head.group(0)), last + 1, at)
        name = re.search(rf"({_IDENT})\Z", self.code[max(0, last - 200):last + 1])
        if name is None:
            return None
        return self.collections(last + 1 - len(name.group(1)), last + 1, at)

    def _schema_collections(self, start: int, end: int) -> tuple[str, ...] | None:
        """The collection whose ``new Collection`` schema is the value at
        [start, end)."""
        obj = self.enclosing(start)
        if obj is None or self.code[obj] != "{":
            return None
        paren = self.enclosing(obj)
        if paren is None or self.code[paren] != "(" or not self.before(paren, r"\bnew\s+Collection"):
            return None
        props = self.properties(obj)
        if not props or "name" not in props or "schema" not in props or self._trim(*props["schema"]) != (start, end):
            return None
        return self.strings(*props["name"], obj)

    def _calls(self, decl: _Decl):
        """(start, opening parenthesis, end) of each call of a helper."""
        for call in re.finditer(rf"(?<![\w$.]){re.escape(decl.name)}\s*\(", self.code):
            if self.mask[call.start()] and call.start() != decl.offset and self.lookup(decl.name, call.start()) is decl:
                paren = call.end() - 1
                yield call.start(), paren, self.close[paren] + 1

    def _site_collections(self, start: int, end: int) -> tuple[str, ...] | None:
        """The collections a field written at [start, end) lands in."""
        opened = self.enclosing(start)
        if opened is None:
            return None
        if self.code[opened] == "[":
            array_end = self.close[opened] + 1
            if self.before(opened, r"\bschema\s*:"):
                return self._schema_collections(opened, array_end)
            helper = self._helper(opened, array_end)
            if helper:
                # A helper that returns a schema, such as guideSchema().
                out: list[str] = []
                for call_start, _paren, call_end in self._calls(helper[0]):
                    found = self._schema_collections(call_start, call_end)
                    if not found:
                        return None
                    out.extend(found)
                return tuple(out) or None
            paren = self.enclosing(opened)
            if paren is None or self.code[paren] != "(" or not self.before(paren, rf"(?<![\w$.]){_IDENT}"):
                return None
            args = call_arguments(self.code, self.mask, paren) or []
            if len(args) >= 2 and self._trim(*args[1]) == (opened, self.close[opened] + 1):
                return self.strings(*args[0], paren)
            return None
        if self.code[opened] == "(":
            args = call_arguments(self.code, self.mask, opened) or []
            if len(args) != 1 or self._trim(*args[0]) != (start, end):
                return None
            add = self.before(opened, r"\.\s*schema\s*\.\s*addField")
            if add is None:
                return None
            return self._receiver(opened - len(add.group(0)), start)
        return None

    def _field_target(self, dot: int) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
        """(collections, fields) for ``<field>.options.maxSize = ...`` with
        the ``.`` before ``options`` at ``dot``."""
        last = self._last_code(dot)
        if last < 0:
            return None
        start, end = None, last + 1
        if self.code[last] == ")" and self.mask[last]:
            paren = self.open_of.get(last)
            if paren is not None:
                head = re.search(rf"({_IDENT}(?:\s*\.\s*{_IDENT})*)\s*\Z", self.code[max(0, paren - 400):paren])
                start = paren - len(head.group(0)) if head else None
        else:
            name = re.search(rf"({_IDENT})\Z", self.code[max(0, last - 200):last + 1])
            if name:
                decl = self.lookup(name.group(1), dot)
                if decl is not None and decl.init is not None:
                    start, end = decl.init
        if start is None:
            return None
        call = self._call(start, end)
        if call is None:
            return None
        callee, paren = call
        lookup = re.search(r"\.\s*schema\s*\.\s*getFieldByName\Z", callee)
        args = call_arguments(self.code, self.mask, paren) or []
        if lookup is None or len(args) != 1:
            return None
        receiver_end = self._trim(start, end)[0] + lookup.start()
        found = self._receiver(receiver_end, start)
        fields = self.strings(*args[0], start)
        return (found, fields) if found and fields else None

    # ---- reading

    def _add(self, offset: int, kind: str, collections: tuple[str, ...], fields: tuple[str | None, ...],
             size: int | None) -> None:
        for collection in collections:
            for field in fields:
                self.found.append((offset, JsonEvent(kind, collection, field, size, self.line(offset))))

    def _helper(self, node: int, node_end: int) -> tuple[_Decl, list[str]] | None | bool:
        """The arrow-function helper whose body is the expression at
        [node, node_end), and its parameters; None when it isn't one, False
        when it's an arrow function the lint can't name."""
        start = node
        opened = self.enclosing(node)
        if opened is not None and self.code[opened] == "(" and self._trim(opened + 1, self.close[opened]) == (node, node_end):
            start = opened
        arrow = self.before(start, rf"(\(([^()]*)\)|({_IDENT}))\s*=>")
        if arrow is None:
            return None
        params_text = arrow.group(2) if arrow.group(2) is not None else arrow.group(3)
        params = [p.strip() for p in params_text.split(",")] if params_text.strip() else []
        params_start = start - len(arrow.group(0))
        decl = next((d for d in self.decls if d.init is not None and d.init[0] == params_start), None)
        if decl is None or any(not re.fullmatch(_IDENT, p) for p in params):
            return False
        return decl, params

    def _json_field(self, match: re.Match[str]) -> None:
        offset = match.start()
        brace = self.enclosing(offset)
        props = self.properties(brace) if brace is not None and self.code[brace] == "{" else None
        if props is None or "type" not in props:
            self.unreadable.append((self.line(offset), "a JSON field the lint can't read"))
            return
        size_span = None
        options = self._object(*props["options"]) if "options" in props else None
        if options is not None:
            option_props = self.properties(options)
            if option_props and "maxSize" in option_props:
                size_span = option_props["maxSize"]
                self.options_read.add(options)
        if size_span is None:
            self.unreadable.append((self.line(brace), "a JSON field without a maxSize"))
            return
        node, node_end = brace, self.close[brace] + 1
        wrapper = self.enclosing(brace)
        if wrapper is not None and self.code[wrapper] == "(" and self.before(wrapper, r"\bnew\s+SchemaField") \
                and self._trim(wrapper + 1, self.close[wrapper]) == (brace, node_end):
            node = wrapper - len(self.before(wrapper, r"\bnew\s+SchemaField").group(0))
            node_end = self.close[wrapper] + 1
        helper = self._helper(node, node_end)
        if helper is False:
            self.unreadable.append((self.line(brace), "a JSON field in a helper the lint can't name"))
            return
        sites: list[tuple[int, int, _Env | None]] = []
        if helper is None:
            sites.append((node, node_end, None))
        else:
            decl, params = helper
            for call_start, paren, call_end in self._calls(decl):
                args = call_arguments(self.code, self.mask, paren) or []
                env = {p: (args[i][0], args[i][1], call_start) for i, p in enumerate(params) if i < len(args)}
                sites.append((call_start, call_end, env))
        for start, end, env in sites:
            fields = self.strings(*props["name"], brace, env) if "name" in props else None
            size = self.number(*size_span, brace, env)
            collections = self._site_collections(start, end)
            if not fields or size is None or not collections:
                self.unreadable.append((self.line(start), "a JSON field the lint can't tie to a collection, a name, "
                                                          "and a size"))
                continue
            self._add(start, "set", collections, fields, size)

    def read(self) -> None:
        for match in _JSON_TYPE.finditer(self.code):
            if self.mask[match.start()]:
                self._json_field(match)
        for match in _SET_MAX_SIZE.finditer(self.code):
            if not self.mask[match.start()]:
                continue
            self.sizes_set.add(match.start() + match.group(0).index("maxSize"))
            size = self.number(match.end(), self._expression_end(match.end()), match.start())
            target = self._field_target(match.start())
            if size is None or target is None:
                self.unreadable.append((self.line(match.start()), "a maxSize assignment the lint can't read"))
                continue
            self._add(match.start(), "set", target[0], target[1], size)
        for match in _MAX_SIZE.finditer(self.code):
            offset = match.start()
            if not self.mask[offset] or offset in self.sizes_set:
                continue
            after = self.code[match.end():match.end() + 40]
            if _CHANGE_MAX_SIZE.match(self.code, offset) or re.match(r"\s*=(?!=)", after):
                self.unreadable.append((self.line(offset), "a maxSize assignment the lint can't read"))
                continue
            if not re.match(r"\s*:(?!:)", after):
                continue  # reads a limit
            options = self.enclosing(offset)
            if options in self.options_read:
                continue
            field = self.enclosing(options) if options is not None else None
            props = self.properties(field) if field is not None and self.code[field] == "{" else None
            kind = self.strings(*props["type"], field) if props and "type" in props else None
            if kind and kind[0] != "json":
                continue  # a file field's or another type's limit
            self.unreadable.append((self.line(offset), "a maxSize the lint can't tie to a JSON field"))
        for match in re.finditer(r"\bdeleteCollection\s*\(", self.code):
            if not self.mask[match.start()]:
                continue
            args = call_arguments(self.code, self.mask, match.end() - 1) or []
            dropped = self.collections(*args[0], match.start()) if args else None
            if dropped:
                self._add(match.start(), "drop", dropped, (None,), None)
        for match in re.finditer(r"\bremoveField\s*\(", self.code):
            if not self.mask[match.start()]:
                continue
            removed = self._removal(match)
            if removed:
                self._add(match.start(), "remove", removed[0], removed[1], None)

    def _removal(self, match: re.Match[str]) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
        """(collections, fields) for ``X.schema.removeField(F.id)``."""
        call = self.before(match.start(), r"\.\s*schema\s*\.\s*")
        if call is None:
            return None
        found = self._receiver(match.start() - len(call.group(0)), match.start())
        args = call_arguments(self.code, self.mask, match.end() - 1) or []
        if not found or len(args) != 1:
            return None
        start, end = self._trim(*args[0])
        literal = self.string_at(start, end)
        if literal is not None:
            return found, (literal,)
        text = self.code[start:end]
        by_id = re.fullmatch(rf"(.+?)\s*\.\s*id", text, re.S)
        if by_id is None:
            return None
        target_end = start + len(by_id.group(1))
        target = self._field_target_of(start, target_end)
        return (found, target) if target else None

    def _field_target_of(self, start: int, end: int) -> tuple[str, ...] | None:
        """The field names an expression for a field object holds: a
        ``getFieldByName`` call, or a binding of one."""
        text = self.code[start:end]
        if re.fullmatch(_IDENT, text):
            decl = self.lookup(text, start)
            if decl is None or decl.init is None:
                return None
            start, end = decl.init
        call = self._call(start, end)
        if call is None or not re.search(r"\.\s*getFieldByName\Z", call[0]):
            return None
        args = call_arguments(self.code, self.mask, call[1]) or []
        return self.strings(*args[0], start) if len(args) == 1 else None

    def events(self) -> list[JsonEvent]:
        return [event for _offset, event in sorted(self.found, key=lambda pair: pair[0])]


def read_json_limits(source: str) -> tuple[list[JsonEvent], list[tuple[int | None, str]]]:
    """What a migration's up step does to JSON field limits, in source
    order, and the places the lint can't read."""
    region = scanned_region(source)
    if region is None:
        return [], [(None, "no migrate(up, down) call the lint can read")]
    reader = _Reader(*region)
    reader.read()
    return reader.events(), sorted(set(reader.unreadable), key=lambda u: (u[0] or 0, u[1]))


def registry_entries(source: str) -> list[tuple[str, str, int]] | None:
    """A json_limits migration's LIMITS as (collection, field, bytes), or
    None unless it's one literal list of unique [collection, field, bytes]
    entries."""
    code = blank_comments(source)
    mask = _code_mask(code)
    found = [m for m in _LIMITS.finditer(code) if mask[m.start()]]
    if len(found) != 1:
        return None
    args = call_arguments(code, mask, found[0].end())
    if args is None:
        return None
    entries: list[tuple[str, str, int]] = []
    for start, end in args:
        entry = _REGISTRY_ENTRY.match(code[start:end].strip())
        if entry is None:
            return None
        entries.append((entry.group(1), entry.group(2), int(entry.group(3))))
    if len({(c, f) for c, f, _size in entries}) != len(entries):
        return None
    return entries


def _file_name(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def registry_limits(migrations: dict[str, str]) -> dict[tuple[str, str], int]:
    """Every json_limits migration's entries, in the order PocketBase
    applies them, a later file's entry for a field winning."""
    out: dict[tuple[str, str], int] = {}
    for path in sorted(migrations, key=_file_name):
        if REGISTRY_FILE.match(_file_name(path)):
            for collection, field, size in registry_entries(migrations[path]) or []:
                out[(collection, field)] = size
    return out


def declared_limits(migrations: dict[str, str]) -> tuple[dict[tuple[str, str], int], list[tuple[str, int | None, str]]]:
    """The maxSize each JSON field ends on after every migration but the
    json_limits ones, applied in PocketBase's order, which is what a
    database whose own reset ran first holds; and each place the lint
    can't read."""
    state: dict[tuple[str, str], int] = {}
    unreadable: list[tuple[str, int | None, str]] = []
    for path in sorted(migrations, key=_file_name):
        if REGISTRY_FILE.match(_file_name(path)):
            continue
        events, problems = read_json_limits(migrations[path])
        for event in events:
            if event.kind == "set" and event.field is not None and event.size is not None:
                state[(event.collection, event.field)] = event.size
            elif event.kind == "drop":
                for key in [k for k in state if k[0] == event.collection]:
                    del state[key]
            elif event.field is not None:
                state.pop((event.collection, event.field), None)
        unreadable.extend((path, line, why) for line, why in problems)
    return state, unreadable


def json_limit_findings(path: str, content: str, declared: dict[tuple[str, str], int],
                        registry: dict[tuple[str, str], int]) -> list[tuple[str, int | None]]:
    """(rule, line) for a new migration's JSON limits: each must be
    registered at the size the migrations end on; a json_limits migration
    must sort after PocketBase's reset and hold a literal LIMITS."""
    name = _file_name(path)
    if REGISTRY_FILE.match(name):
        if name <= JSON_RESET or registry_entries(content) is None:
            return [("json-limits-registry", None)]
        return []
    if scanned_region(content) is None:
        return []  # unparsed-migration already covers it
    events, unreadable = read_json_limits(content)
    hits = {("unreadable-json-limit", line) for line, _why in unreadable}
    for event in events:
        key = (event.collection, event.field or "")
        if event.kind == "set" and key in declared and registry.get(key) != declared[key]:
            hits.add(("unregistered-json-limit", event.line))
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


def lint(changes: list[Change], allowlist: list[dict],
         head: dict[str, str] | None = None) -> tuple[list[Finding], list[Finding]]:
    """(blocking, allowed): the findings for ``changes``, split by whether
    an allowlist entry covers them. With ``head``, every migration at the
    revision under review by path, a new migration's JSON limits are also
    checked against the json_limits registry."""
    findings: list[Finding] = []
    declared: dict[tuple[str, str], int] = {}
    registry: dict[tuple[str, str], int] = {}
    if head is not None:
        declared, _unreadable = declared_limits(head)
        registry = registry_limits(head)
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
        if head is not None:
            findings.extend(Finding(change.path, rule, line, digest)
                            for rule, line in json_limit_findings(change.path, content, declared, registry))
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


def migrations_at(repo: Path, rev: str) -> dict[str, str]:
    """Every migration at ``rev``, by path."""
    listing = _git(repo, "ls-tree", "-r", "-z", "--name-only", rev, "--", MIGRATIONS_DIR)
    out: dict[str, str] = {}
    for path in (p for p in listing.split("\0") if p):
        if CONTROL.search(path):
            raise LintError(f"a path under {MIGRATIONS_DIR} contains a control character")
        if is_migration(path):
            out[path] = _git(repo, "show", f"{rev}:{path}")
    return out


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
    if any(f.rule in JSON_RULES for f in blocking):
        print("Register each JSON field's maxSize, at the size the migrations end on, in a new")
        print("NNNN_json_limits_<name>.js copied from 1702134273_json_limits.js, and keep its")
        print("LIMITS a literal list (docs/development.md#json-field-limits).")
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
        head = migrations_at(repo, args.head)
    except LintError as err:
        print(f"lint_migrations: {err}", file=sys.stderr)
        return 2
    blocking, allowed = lint(changes, allowlist, head)
    _report(blocking, allowed, allowlist, args.allowlist)
    if blocking:
        return 1
    print(f"lint_migrations: {len(changes)} migration change(s), nothing blocking.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
