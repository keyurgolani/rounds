#!/usr/bin/env python3
"""Compiles the seed sources into backend/definitions/ (ROUNDS-00A-L02).

Sources:

1. ``pocketbase/seeds/content.json`` and ``more_coding.json``: each coding
   question becomes one test-definition/v1 per language (``python`` and
   ``javascript``) and, when a case uses a validator predicate, one
   coding-validators harness revision that both languages share. The
   entry is the stored one or, as ``1700000100_seed_data.js`` infers it,
   the first ``def`` in the Python starter. A predicate that only compares
   ``out`` to a literal becomes that literal.
2. ``backend/ai_coding/rounds/<slug>/``: one ai-coding-checkpoint harness
   revision per language, with each checkpoint's visible run, its grade
   driver under ``harness/``, and the result ids it reports on fd 3.
3. ``backend/take_home/assignments/<slug>/``: the three removed
   assignments, compiled only as ``retired`` versions.
4. The five AI-coding samples whose sources are gone: payload-free
   ``retired`` entries.

Output: ``manifest.json``, with every version's identity, lifecycle, file,
and checksum, and ``store/``, one file per version holding exactly the
RFC 8785 bytes its checksum covers.

Versions only get added. When a source's compiled content differs from its
latest version, the compiler adds the next version as ``active`` and marks
the previous active one ``superseded``; an existing version's file and
checksum never change. Only an edit to the manifest retires a version.

usage: build.py [--check]
  --check   exit 1 unless the committed manifest and store are exactly
            what the sources compile to
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import shlex
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

DEFINITIONS = Path(__file__).resolve().parent
BACKEND = DEFINITIONS.parent
ROOT = BACKEND.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app import canonical, contract_schema  # noqa: E402

MANIFEST = DEFINITIONS / "manifest.json"
STORE = DEFINITIONS / "store"
SEEDS = ROOT / "pocketbase" / "seeds"
AI_CODING_ROUNDS = BACKEND / "ai_coding" / "rounds"
TAKE_HOME_ASSIGNMENTS = BACKEND / "take_home" / "assignments"
HARNESS_RUNTIME = DEFINITIONS / "harness" / "rounds_harness.py"

CODING_VARIANTS = ("python", "javascript")
# AI-coding samples removed on 2026-05-16 whose sources are gone; only a
# pre-2026-05-16 database still has rows for them (docs/dev-db-reseed.md).
SOURCELESS_AI_CODING = {
    "async-bugs-py": "python",
    "cart-bugfix-py": "python",
    "log-parser-ts": "typescript",
    "rate-limiter-ts": "typescript",
    "word-count-py": "python",
}
# Removed take-home assignments whose sources remain: retired versions only.
RETIRED_TAKE_HOME = frozenset({"csv-summarize-py", "event-bus-ts", "kv-store-py"})
VALUED_MATCHERS = frozenset({"exact", "unordered", "unordered_deep", "contains", "subset_of", "superset_of"})
INTERPRETERS = frozenset({"python3", "node", "tsx"})
VISIBLE_RUN_WALL_S = 10
TAKE_HOME_RUN_WALL_S = 60
TAKE_HOME_SUBMIT_WALL_S = 120
SCHEMAS = {
    "test-definition": "definitions/test-definition.v1.schema.json",
    "harness-revision": "definitions/harness-revision.v1.schema.json",
}
MANIFEST_SCHEMA = "definitions/manifest.v1.schema.json"
LITERAL_PREDICATE = re.compile(r"lambda inp, out: out == (.+)", re.S)
ARTIFACT_PARTS = frozenset({"__pycache__", ".pytest_cache", "node_modules", ".DS_Store"})


class CompileError(Exception):
    """The sources don't compile to valid definitions."""


@dataclass(frozen=True, order=True)
class Key:
    track: str
    slug: str
    kind: str
    variant: str | None

    def sort_key(self) -> tuple[str, str, str, str]:
        return (self.track, self.slug, self.kind, self.variant or "")


@dataclass
class Source:
    """A compiled definition before it has a version."""

    key: Key
    body: dict[str, Any] | None  # None: a payload-free retired entry
    lifecycle: str = "active"  # what a new version starts as


@dataclass
class Plan:
    entries: list[dict[str, Any]] = field(default_factory=list)
    files: dict[str, bytes] = field(default_factory=dict)  # store path -> bytes, every version with a file


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------


def slugify(text: str) -> str:
    """1700000100_seed_data.js's slugify."""
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:80]


def infer_function_entry(row: dict[str, Any]) -> dict[str, Any] | None:
    """1700000100_seed_data.js's inferFunctionEntry: the first ``def`` in
    the Python starter, every parameter typed ``any``."""
    starter = ((row.get("starter_code") or {}).get("python")) or ""
    found = re.search(r"def\s+(\w+)\s*\(([^)]*)\)", starter, re.ASCII)
    if not found:
        return None
    raw = found.group(2).strip()
    params = []
    if raw:
        for part in (p.strip() for p in raw.split(",")):
            if part and part != "self":
                params.append({"name": re.split(r"[:=]", part)[0].strip(), "type": "any"})
    return {"kind": "function", "name": found.group(1), "params": params, "returns": "any"}


def _literal_predicate(code: str) -> tuple[bool, Any]:
    """(True, value) when ``code`` only compares ``out`` to a literal."""
    found = LITERAL_PREDICATE.fullmatch(code.strip())
    if not found:
        return False, None
    try:
        value = ast.literal_eval(found.group(1).strip())
    except (ValueError, SyntaxError):
        return False, None
    try:
        canonical.canonical(value)
    except canonical.CanonicalError:
        return False, None
    return True, value


def validator_id(code: str) -> str:
    return "v-" + hashlib.sha256(code.encode("utf-8")).hexdigest()[:12]


def _expected(expected: Any, validators: dict[str, str], where: str) -> dict[str, Any]:
    if not (isinstance(expected, dict) and isinstance(expected.get("$match"), str)):
        return {"literal": expected}
    kind = expected["$match"]
    if kind == "validator":
        code = expected.get("code")
        if not isinstance(code, str):
            raise CompileError(f"{where}: validator without code")
        is_literal, value = _literal_predicate(code)
        if is_literal:
            return {"literal": value}
        vid = validator_id(code)
        validators[vid] = code
        return {"validator_id": vid}
    if kind == "any_of":
        return {"matcher": "any_of", "values": expected.get("values")}
    if kind == "approx":
        out = {"matcher": "approx", "value": expected.get("value")}
        for tol in ("abs_tol", "rel_tol"):
            if expected.get(tol) is not None:
                out[tol] = expected[tol]
        return out
    if kind in VALUED_MATCHERS:
        return {"matcher": kind, "value": expected.get("value")}
    raise CompileError(f"{where}: unknown matcher {kind!r}")


def coding_questions(seeds: Path = SEEDS) -> list[dict[str, Any]]:
    """The rows 1700000100_seed_data.js loads into coding_questions."""
    rows: list[dict[str, Any]] = []
    for name, required in (("content.json", True), ("more_coding.json", False)):
        path = seeds / name
        if not path.exists():
            if required:
                raise CompileError(f"missing {path}")
            continue
        rows.extend(json.loads(path.read_text(encoding="utf-8")).get("coding_questions") or [])
    return rows


def coding_sources(rows: Iterable[dict[str, Any]]) -> tuple[list[Source], dict[str, list[Source]]]:
    """(validator revisions, the test definitions waiting on each slug's)."""
    validators_out: list[Source] = []
    pending: dict[str, list[Source]] = {}
    seen: set[str] = set()
    for row in rows:
        slug = slugify(row.get("slug") or row.get("title") or "")
        if not slug:
            continue
        if slug in seen:
            raise CompileError(f"coding question {slug!r} appears twice")
        seen.add(slug)
        entry = row.get("entry")
        if not entry or not isinstance(entry, (dict, list)):
            entry = infer_function_entry(row)
        if entry is None:
            raise CompileError(f"coding question {slug!r} has no entry")
        validators: dict[str, str] = {}
        cases = []
        stored = [tc for tc in (row.get("test_cases") or []) if isinstance(tc, dict)]
        for i, tc in enumerate(stored):
            tags = list(tc.get("tags") or [])
            cases.append({
                "case_id": f"c{i:03d}",
                "tags": tags,
                "visibility": "visible",
                "time_class": "large" if "large" in tags else "standard",
                "description": tc.get("description") or "",
                "input": tc.get("input", {}),
                "expected": _expected(tc.get("expected"), validators, f"{slug} case {i}"),
            })
        definitions = []
        for variant in CODING_VARIANTS:
            definitions.append(Source(
                Key("coding", slug, "test-definition", variant),
                {
                    "schema": "test-definition/v1",
                    "track": "coding",
                    "slug": slug,
                    "variant": variant,
                    "entry": entry,
                    "cases": cases,
                    "validators": None,
                },
            ))
        if validators:
            validators_out.append(Source(
                Key("coding", slug, "harness-revision", None),
                {
                    "schema": "harness-revision/v1",
                    "kind": "coding-validators",
                    "track": "coding",
                    "slug": slug,
                    "variant": None,
                    "validators": [{"validator_id": vid, "predicate": validators[vid]} for vid in sorted(validators)],
                    "runtime_profile": "validator-python",
                    "network": "none",
                },
            ))
        pending[slug] = definitions
    return validators_out, pending


def _is_artifact(rel: Path) -> bool:
    return rel.suffix in {".pyc", ".pyo"} or any(part in ARTIFACT_PARTS for part in rel.parts)


def _walk(base: Path, prefix: str = "", skip: frozenset[str] = frozenset()) -> list[dict[str, str]]:
    out = []
    if not base.exists():
        return out
    for path in sorted(base.rglob("*")):
        rel = path.relative_to(base)
        if not path.is_file() or _is_artifact(rel) or rel.name in skip:
            continue
        out.append({"path": f"{prefix}{rel.as_posix()}", "contents": path.read_text(encoding="utf-8")})
    return out


def _argv(command: str, where: str) -> list[str]:
    argv = shlex.split(command)
    if argv and argv[0] == "pytest":
        argv = ["python3", "-m", "pytest"] + argv[1:]
    if not argv or argv[0] not in INTERPRETERS:
        raise CompileError(f"{where}: {command!r} doesn't start with one of {sorted(INTERPRETERS)}")
    return argv


def ai_coding_sources(rounds: Path = AI_CODING_ROUNDS, runtime: Path = HARNESS_RUNTIME) -> list[Source]:
    out: list[Source] = []
    driver_lib = {"path": "harness/rounds_harness.py", "contents": runtime.read_text(encoding="utf-8")}
    for d in sorted(p for p in rounds.iterdir() if p.is_dir()):
        manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
        slug = manifest["slug"]
        multi = "variants" in manifest and "languages" in manifest
        languages = list(manifest["languages"]) if multi else [manifest["language"]]
        shared = _walk(d / "harness", "harness/")
        for lang in languages:
            checkpoints_src = manifest["variants"][lang]["checkpoints"] if multi else manifest["checkpoints"]
            starter = d / "starter" / lang if multi else d / "starter"
            cp_base = d / "checkpoints" / lang if multi else d / "checkpoints"
            files = [driver_lib] + shared
            candidate = [f["path"] for f in _walk(starter)]
            checkpoints = []
            loopback = False
            for idx, cp in enumerate(checkpoints_src):
                where = f"{slug} {lang} checkpoint {idx}"
                harness_dir = cp_base / str(idx) / "harness"
                meta_path = harness_dir / "harness.json"
                if not meta_path.exists():
                    raise CompileError(f"{where}: no harness/harness.json")
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                files += _walk(harness_dir, f"harness/checkpoint_{idx}/", frozenset({"harness.json"}))
                candidate += [f["path"] for f in _walk(cp_base / str(idx) / "tests", f"tests/checkpoint_{idx}/")]
                loopback = loopback or meta.get("network") == "job-loopback"
                checkpoints.append({
                    "index": idx,
                    "label": cp["label"],
                    "ai_allowed": bool(cp.get("ai_allowed")),
                    "run": {"argv": _argv(cp["test_command"], where), "job_class": "interactive", "wall_s": VISIBLE_RUN_WALL_S},
                    "grade": {"argv": meta["grade"]["argv"], "job_class": "project", "wall_s": meta["grade"]["wall_s"]},
                    "results": meta["results"],
                    "min_executed": meta["min_executed"],
                })
            out.append(Source(
                Key("ai-coding", slug, "harness-revision", lang),
                {
                    "schema": "harness-revision/v1",
                    "kind": "ai-coding-checkpoint",
                    "track": "ai-coding",
                    "slug": slug,
                    "variant": lang,
                    "files": sorted(files, key=lambda f: f["path"]),
                    "candidate_paths": sorted(candidate),
                    "checkpoints": checkpoints,
                    "rubric": manifest.get("rubric") or {"items": []},
                    "ai_policy": "per-checkpoint",
                    "runtime_profile": "python-pytest" if lang == "python" else "node-tsx",
                    "network": "job-loopback" if loopback else "none",
                    "result_protocol": "fd3",
                },
            ))
    for slug, lang in sorted(SOURCELESS_AI_CODING.items()):
        if (rounds / slug).exists():
            raise CompileError(f"{slug} has sources again; drop it from SOURCELESS_AI_CODING")
        out.append(Source(Key("ai-coding", slug, "harness-revision", lang), None, "retired"))
    return out


def take_home_sources(assignments: Path = TAKE_HOME_ASSIGNMENTS) -> list[Source]:
    out: list[Source] = []
    if not assignments.exists():
        return out
    for d in sorted(p for p in assignments.iterdir() if p.is_dir()):
        manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
        slug = manifest["slug"]
        if slug not in RETIRED_TAKE_HOME:
            raise CompileError(
                f"take-home {slug!r}: only the removed assignments compile, as retired; "
                "a new one needs an fd 3 driver first"
            )
        argv = _argv(manifest["entrypoint"], slug)
        policy = manifest.get("ai_policy", "off")
        out.append(Source(
            Key("take-home", slug, "harness-revision", manifest["language"]),
            {
                "schema": "harness-revision/v1",
                "kind": "take-home",
                "track": "take-home",
                "slug": slug,
                "variant": manifest["language"],
                "files": _walk(d / "harness", "harness/"),
                "candidate_paths": sorted(f["path"] for f in _walk(d / "starter")),
                "checkpoints": [{
                    "index": 0,
                    "label": manifest["title"],
                    "ai_allowed": policy != "off",
                    "run": {"argv": argv, "job_class": "project", "wall_s": TAKE_HOME_RUN_WALL_S},
                    "grade": {"argv": argv, "job_class": "project", "wall_s": TAKE_HOME_SUBMIT_WALL_S},
                    "results": [],
                    "min_executed": 0,
                }],
                "rubric": manifest.get("rubric") or {"items": []},
                "ai_policy": "off" if policy == "off" else "allowed",
                "runtime_profile": "python-pytest" if manifest["language"] == "python" else "node-tsx",
                "network": "none",
                "result_protocol": "legacy-stdout",
            },
            "retired",
        ))
    return out


# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------


def store_path(key: Key, version: int) -> str:
    name = "validators" if key.kind == "harness-revision" and key.track == "coding" else key.variant
    return f"store/{key.track}/{key.slug}/{name}.v{version}.json"


def _key_of(entry: dict[str, Any]) -> Key:
    return Key(entry["track"], entry["slug"], entry["kind"], entry["variant"])


def _entry(key: Key, version: int, lifecycle: str, path: str | None, checksum: str | None) -> dict[str, Any]:
    return {
        "kind": key.kind,
        "track": key.track,
        "slug": key.slug,
        "variant": key.variant,
        "content_version": version,
        "lifecycle": lifecycle,
        "path": path,
        "checksum": checksum,
    }


def _document(source: Source, version: int) -> dict[str, Any]:
    assert source.body is not None
    return {**source.body, "content_version": version}


def place_group(sources: list[Source], by_key: dict[Key, list[dict[str, Any]]], plan: Plan) -> dict[Key, dict[str, Any]]:
    """Adds one (track, slug, kind)'s versions to ``plan`` and returns each
    variant's latest entry. Its variants share a version number, so one
    presentation row names one version: when any variant's content
    changes or a variant is new, every variant gets the next version."""
    olds = {s.key: sorted(by_key.get(s.key, []), key=lambda e: e["content_version"]) for s in sources}
    for s in sources:
        plan.entries.extend(dict(e) for e in olds[s.key])
    if all(s.body is None for s in sources):
        out = {}
        for s in sources:
            if olds[s.key]:
                out[s.key] = next(e for e in plan.entries if _key_of(e) == s.key and e["content_version"] == olds[s.key][-1]["content_version"])
            else:
                out[s.key] = _entry(s.key, 1, "retired", None, None)
                plan.entries.append(out[s.key])
        return out
    if any(s.body is None for s in sources):
        raise CompileError(f"{sources[0].key}: a payload-free variant can't share a version with stored ones")
    group_latest = max((e["content_version"] for es in olds.values() for e in es), default=0)
    current: dict[Key, tuple[dict[str, Any], bytes]] = {}
    for s in sources:
        latest = olds[s.key][-1] if olds[s.key] else None
        if latest is None or latest["checksum"] is None or latest["content_version"] != group_latest:
            continue
        data = canonical.canonical(_document(s, group_latest))
        if canonical.checksum_bytes(data) == latest["checksum"]:
            current[s.key] = (latest, data)
    if len(current) == len(sources):
        out = {}
        for key, (latest, data) in current.items():
            plan.files[latest["path"]] = data
            out[key] = next(e for e in plan.entries if _key_of(e) == key and e["content_version"] == group_latest)
        return out
    version = group_latest + 1
    out = {}
    for s in sources:
        for entry in plan.entries:
            if _key_of(entry) == s.key and entry["lifecycle"] == "active":
                entry["lifecycle"] = "superseded"
        data = canonical.canonical(_document(s, version))
        path = store_path(s.key, version)
        out[s.key] = _entry(s.key, version, s.lifecycle, path, canonical.checksum_bytes(data))
        plan.entries.append(out[s.key])
        plan.files[path] = data
    return out


def compile_all(old_manifest: dict[str, Any] | None, *, seeds: Path = SEEDS, rounds: Path = AI_CODING_ROUNDS,
                assignments: Path = TAKE_HOME_ASSIGNMENTS, runtime: Path = HARNESS_RUNTIME,
                definitions: Path = DEFINITIONS) -> Plan:
    old_entries = list((old_manifest or {}).get("entries") or [])
    by_key: dict[Key, list[dict[str, Any]]] = {}
    for entry in old_entries:
        by_key.setdefault(_key_of(entry), []).append(entry)
    plan = Plan()
    placed: set[Key] = set()

    def put(sources: list[Source]) -> dict[Key, dict[str, Any]]:
        for source in sources:
            if source.key in placed:
                raise CompileError(f"{source.key} compiled twice")
            placed.add(source.key)
            if source.body is not None:
                _validate(source)
        return place_group(sources, by_key, plan)

    validator_sources, pending = coding_sources(coding_questions(seeds))
    validators_entry = {source.key.slug: put([source])[source.key] for source in validator_sources}
    for slug, variants in pending.items():
        ref = validators_entry.get(slug)
        if ref is not None:
            for source in variants:
                source.body["validators"] = {"slug": slug, "content_version": ref["content_version"], "checksum": ref["checksum"]}
        put(variants)
    groups: dict[tuple[str, str, str], list[Source]] = {}
    for source in ai_coding_sources(rounds, runtime) + take_home_sources(assignments):
        groups.setdefault((source.key.track, source.key.slug, source.key.kind), []).append(source)
    for sources in groups.values():
        put(sources)
    # Versions whose sources are gone stay as they were.
    for key, entries in by_key.items():
        if key not in placed:
            plan.entries.extend(dict(e) for e in entries)
    plan.entries.sort(key=lambda e: (_key_of(e).sort_key(), e["content_version"]))
    # Earlier versions keep their committed bytes, which have to match.
    for entry in plan.entries:
        path = entry["path"]
        if path is None or path in plan.files:
            continue
        stored = definitions / path
        data = stored.read_bytes() if stored.is_file() else None
        if data is None or canonical.checksum_bytes(data) != entry["checksum"]:
            raise CompileError(f"{path} is missing or doesn't match its checksum")
        plan.files[path] = data
    _check_plan(plan)
    return plan


def _validate(source: Source) -> None:
    doc = _document(source, 1)
    errors = contract_schema.load(SCHEMAS[source.key.kind]).errors(doc)
    if errors:
        raise CompileError(f"{source.key}: " + "; ".join(errors[:5]))
    try:
        canonical.canonical(doc)
    except canonical.CanonicalError as err:
        raise CompileError(f"{source.key}: {err}") from None


def _check_plan(plan: Plan) -> None:
    manifest = manifest_of(plan)
    errors = contract_schema.load(MANIFEST_SCHEMA).errors(manifest)
    if errors:
        raise CompileError("manifest: " + "; ".join(errors[:5]))
    for key in {_key_of(e) for e in plan.entries}:
        active = [e for e in plan.entries if _key_of(e) == key and e["lifecycle"] == "active"]
        if len(active) > 1:
            raise CompileError(f"{key} has {len(active)} active versions")


def manifest_of(plan: Plan) -> dict[str, Any]:
    return {"schema": "definitions-manifest/v1", "entries": plan.entries}


def manifest_text(plan: Plan) -> str:
    return json.dumps(manifest_of(plan), indent=2, ensure_ascii=False) + "\n"


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def load_manifest(path: Path = MANIFEST) -> dict[str, Any] | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def differences(plan: Plan, definitions: Path = DEFINITIONS) -> list[str]:
    """What on disk differs from ``plan``."""
    out = []
    manifest = definitions / "manifest.json"
    if not manifest.exists() or manifest.read_text(encoding="utf-8") != manifest_text(plan):
        out.append("manifest.json")
    expected = set(plan.files)
    for rel, data in sorted(plan.files.items()):
        path = definitions / rel
        if not path.exists() or path.read_bytes() != data:
            out.append(rel)
    store = definitions / "store"
    if store.exists():
        for path in sorted(store.rglob("*.json")):
            rel = path.relative_to(definitions).as_posix()
            if rel not in expected:
                out.append(f"{rel} (not in the manifest)")
    return out


def write(plan: Plan, definitions: Path = DEFINITIONS) -> list[str]:
    written = []
    for rel, data in sorted(plan.files.items()):
        path = definitions / rel
        if path.exists() and path.read_bytes() == data:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        written.append(rel)
    text = manifest_text(plan)
    manifest = definitions / "manifest.json"
    if not manifest.exists() or manifest.read_text(encoding="utf-8") != text:
        manifest.write_text(text, encoding="utf-8")
        written.append("manifest.json")
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if the committed output differs")
    args = parser.parse_args(argv)
    try:
        plan = compile_all(load_manifest(), definitions=DEFINITIONS)
    except CompileError as err:
        print(f"build: {err}", file=sys.stderr)
        return 2
    if args.check:
        stale = differences(plan)
        for rel in stale:
            print(f"stale: backend/definitions/{rel}", file=sys.stderr)
        if stale:
            print("run python3 backend/definitions/build.py and commit the result", file=sys.stderr)
            return 1
        print(f"build: {len(plan.entries)} versions, all current")
        return 0
    for rel in write(plan):
        print(f"wrote backend/definitions/{rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
