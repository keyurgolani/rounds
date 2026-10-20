#!/usr/bin/env python3
"""Checks that a change to backend/definitions/ only adds (ROUNDS-00A-L02).

The compiled definitions are immutable once shipped: a worker that ran one
version has to see the same bytes forever, and a result's receipt names a
version that never changes under it. So between the base and the head of a
pull request, the manifest may only:

- add new versions (new identity keys), and
- move a version's lifecycle forward: active to superseded or retired,
  superseded to retired. Never back.

A version that exists at the base keeps its path and checksum, and the
file at that path keeps its exact bytes; no shipped store file is modified
or deleted. The checksum is ``sha256:`` over the file's bytes
(app.canonical), so an unchanged checksum is unchanged bytes, and the
check also makes sure every referenced file is present at the head with
that checksum, and that no store file is left behind without an entry.

``build.py --check`` (in the backend suite) already proves the committed
output is what the sources compile to; this guards the invariant that
compiling can't restate, only extend.

usage: definitions_manifest_check.py --base REV --head REV [--repo DIR]
exit status: 0 nothing blocking, 1 findings, 2 the check couldn't run
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

MANIFEST_PATH = "backend/definitions/manifest.json"
STORE_PREFIX = "backend/definitions/store/"
LIFECYCLE_ORDER = {"active": 0, "superseded": 1, "retired": 2}


class CheckError(Exception):
    """The check itself couldn't run."""


def _key(entry: dict) -> tuple:
    return (entry["kind"], entry["track"], entry["slug"], entry["variant"], entry["content_version"])


def _label(key: tuple) -> str:
    kind, track, slug, variant, version = key
    return f"{kind} {track}/{slug}/{variant or 'shared'}@{version}"


def compare(base: dict | None, head: dict, head_files: dict[str, str | None]) -> list[str]:
    """What the head changes that it may not. ``head_files`` maps each
    store path the head manifest references to its checksum at the head,
    or None when the file is missing there."""
    problems: list[str] = []
    head_by_key = {_key(e): e for e in head.get("entries", [])}

    for key, entry in head_by_key.items():
        if entry["path"] is None:
            continue
        if not entry["path"].startswith("store/"):
            problems.append(f"{_label(key)}: path {entry['path']!r} is outside store/")
            continue
        actual = head_files.get(entry["path"])
        if actual is None:
            problems.append(f"{_label(key)}: its file {entry['path']} is missing at the head")
        elif actual != entry["checksum"]:
            problems.append(f"{_label(key)}: its file {entry['path']} doesn't match the manifest checksum")

    referenced = {e["path"] for e in head_by_key.values() if e["path"] is not None}
    for path in head_files:
        if path not in referenced:
            problems.append(f"{path} is in the store but no manifest entry names it")

    if base is None:
        return problems

    for key, was in {_key(e): e for e in base.get("entries", [])}.items():
        now = head_by_key.get(key)
        if now is None:
            problems.append(f"{_label(key)}: a shipped version was removed from the manifest")
            continue
        if now["path"] != was["path"]:
            problems.append(f"{_label(key)}: its path changed from {was['path']!r} to {now['path']!r}")
        if now["checksum"] != was["checksum"]:
            problems.append(f"{_label(key)}: its checksum changed, so its shipped bytes changed")
        if LIFECYCLE_ORDER[now["lifecycle"]] < LIFECYCLE_ORDER[was["lifecycle"]]:
            problems.append(
                f"{_label(key)}: its lifecycle moved back from {was['lifecycle']} to {now['lifecycle']}"
            )
    return problems


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    """A git command's result, its output as bytes so a blob's checksum is
    over exactly what's stored."""
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True)


def _commit(repo: Path, rev: str) -> str:
    """``rev`` as a commit id, or CheckError when it doesn't name one, so a
    base that can't be read is never taken for one without a manifest."""
    done = _git(repo, "rev-parse", "--verify", "--quiet", "--end-of-options", f"{rev}^{{commit}}")
    if done.returncode != 0:
        raise CheckError(f"can't read revision {rev!r}")
    return done.stdout.decode("ascii").strip()


def _manifest_at(repo: Path, rev: str) -> dict | None:
    """The manifest at ``rev``, or None when that commit has no manifest
    file. A revision that can't be read, or a manifest that can't be,
    is a CheckError."""
    commit = _commit(repo, rev)
    listed = _git(repo, "ls-tree", "-z", "--name-only", commit, "--", MANIFEST_PATH)
    if listed.returncode != 0:
        raise CheckError(f"can't list {MANIFEST_PATH} at {rev}")
    if not listed.stdout:
        return None  # a base that predates the manifest
    done = _git(repo, "show", f"{commit}:{MANIFEST_PATH}")
    if done.returncode != 0:
        raise CheckError(f"can't read {MANIFEST_PATH} at {rev}")
    try:
        return json.loads(done.stdout)
    except ValueError as err:
        raise CheckError(f"{MANIFEST_PATH} at {rev} isn't JSON: {err}") from None


def _store_checksums_at(repo: Path, rev: str) -> dict[str, str]:
    """Each store/*.json path the revision carries, with ``sha256:`` of its
    bytes, so an entry can be checked against the file actually shipped."""
    import hashlib

    commit = _commit(repo, rev)
    listing = _git(repo, "ls-tree", "-r", "-z", "--name-only", commit, "--", STORE_PREFIX)
    if listing.returncode != 0:
        raise CheckError(f"can't list {STORE_PREFIX} at {rev}")
    out: dict[str, str] = {}
    for path in (p for p in listing.stdout.decode("utf-8").split("\0") if p.endswith(".json")):
        blob = _git(repo, "show", f"{commit}:{path}")
        if blob.returncode != 0:
            raise CheckError(f"can't read {path} at {rev}")
        out[path[len(STORE_PREFIX) - len("store/"):]] = "sha256:" + hashlib.sha256(blob.stdout).hexdigest()
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check that backend/definitions/ only grows.")
    parser.add_argument("--base", required=True, help="the target branch revision")
    parser.add_argument("--head", required=True, help="the revision under review")
    parser.add_argument("--repo", default=".", help="the repository root")
    args = parser.parse_args(argv)
    repo = Path(args.repo)
    try:
        head = _manifest_at(repo, args.head)
        if head is None:
            raise CheckError(f"no {MANIFEST_PATH} at {args.head}")
        base = _manifest_at(repo, args.base)
        head_files = _store_checksums_at(repo, args.head)
    except CheckError as err:
        print(f"definitions-manifest-check: {err}", file=sys.stderr)
        return 2
    problems = compare(base, head, head_files)
    for problem in problems:
        print(f"definitions: {problem}", file=sys.stderr)
    if problems:
        print(
            "\nShipped definitions are immutable. Add a new version instead of changing one, "
            "and move a lifecycle only forward.",
            file=sys.stderr,
        )
        return 1
    added = len(head.get("entries", [])) - (len(base.get("entries", [])) if base else 0)
    print(f"definitions-manifest-check: ok ({len(head.get('entries', []))} versions, {added} added)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
