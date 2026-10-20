"""scripts/definitions_manifest_check.py (ROUNDS-00A-L02): the CI guard
that backend/definitions/ only grows, never restates a shipped version."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from app import canonical

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "definitions_manifest_check.py"


def _load():
    spec = importlib.util.spec_from_file_location("definitions_manifest_check", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check = _load()


def entry(slug="two-sum", variant="python", version=1, lifecycle="active", path="auto", checksum="c1"):
    if path == "auto":
        path = f"store/coding/{slug}/{variant}.v{version}.json"
    return {"kind": "test-definition", "track": "coding", "slug": slug, "variant": variant,
            "content_version": version, "lifecycle": lifecycle, "path": path, "checksum": checksum}


def manifest(*entries):
    return {"schema": "definitions-manifest/v1", "entries": list(entries)}


def files(*entries):
    return {e["path"]: e["checksum"] for e in entries if e["path"] is not None}


def test_adding_a_new_version_is_fine():
    base = manifest(entry(version=1, lifecycle="superseded"))
    head = manifest(entry(version=1, lifecycle="superseded"), entry(version=2, checksum="c2"))
    assert check.compare(base, head, files(*head["entries"])) == []


def test_a_first_introduction_with_no_base_only_checks_the_files():
    head = manifest(entry(), entry(slug="3sum", checksum="c9"))
    assert check.compare(None, head, files(*head["entries"])) == []
    broken = check.compare(None, head, {"store/coding/two-sum/python.v1.json": "c1"})
    assert any("3sum" in p and "missing" in p for p in broken)


def test_moving_a_lifecycle_forward_is_fine():
    base = manifest(entry(lifecycle="active"))
    head = manifest(entry(lifecycle="retired"))
    assert check.compare(base, head, files(*head["entries"])) == []


def test_a_lifecycle_cant_move_back():
    base = manifest(entry(lifecycle="retired"))
    head = manifest(entry(lifecycle="active"))
    assert any("moved back" in p for p in check.compare(base, head, files(*head["entries"])))


def test_a_shipped_checksum_cant_change():
    base = manifest(entry(checksum="c1"))
    head = manifest(entry(checksum="c2"))
    problems = check.compare(base, head, files(*head["entries"]))
    assert any("shipped bytes changed" in p for p in problems)


def test_a_shipped_path_cant_change():
    base = manifest(entry(path="store/coding/two-sum/python.v1.json"))
    head = manifest(entry(path="store/coding/two-sum/moved.json"))
    assert any("path changed" in p for p in check.compare(base, head, files(*head["entries"])))


def test_a_shipped_version_cant_be_removed():
    base = manifest(entry(version=1), entry(version=2, checksum="c2"))
    head = manifest(entry(version=1))
    assert any("removed from the manifest" in p for p in check.compare(base, head, files(*head["entries"])))


def test_a_referenced_file_must_be_present_with_its_checksum():
    head = manifest(entry(checksum="c1"))
    assert any("missing at the head" in p for p in check.compare(None, head, {}))
    assert any("doesn't match" in p for p in check.compare(None, head, {"store/coding/two-sum/python.v1.json": "c2"}))


def test_a_store_file_with_no_entry_is_flagged():
    head = manifest(entry())
    extra = {**files(*head["entries"]), "store/coding/orphan/python.v1.json": "c3"}
    assert any("no manifest entry names it" in p for p in check.compare(None, head, extra))


def test_a_payload_free_retired_entry_needs_no_file():
    head = manifest({"kind": "harness-revision", "track": "ai-coding", "slug": "word-count-py",
                     "variant": "python", "content_version": 1, "lifecycle": "retired",
                     "path": None, "checksum": None})
    assert check.compare(None, head, {}) == []


def test_the_committed_manifest_passes_against_itself():
    # The real manifest and store: nothing changed, so no finding.
    head = json.loads((ROOT / "backend" / "definitions" / "manifest.json").read_text())
    store = ROOT / "backend" / "definitions"
    head_files = {
        e["path"]: canonical.checksum_bytes((store / e["path"]).read_bytes())
        for e in head["entries"] if e["path"] is not None
    }
    assert check.compare(head, head, head_files) == []


def test_the_script_runs_over_git_and_passes_for_this_branch():
    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--base", "HEAD", "--head", "HEAD", "--repo", str(ROOT)],
        capture_output=True, text=True, timeout=120,
    )
    assert res.returncode == 0, res.stderr
    assert "versions, 0 added" in res.stdout


# ---- reading the base ------------------------------------------------------------


def _repo(tmp_path: Path, stored: bytes = b'{"a":1}') -> Path:
    """A repository whose first commit predates the manifest and whose
    second adds it with one stored version."""
    repo = tmp_path / "repo"
    repo.mkdir()

    def vcs(*args: str) -> None:
        subprocess.run(["git", "-C", str(repo), "-c", "user.email=check@example.invalid", "-c", "user.name=check",
                        "-c", "commit.gpgsign=false", *args], check=True, capture_output=True)

    vcs("init", "-q")
    (repo / "README").write_text("x\n")
    vcs("add", "README")
    vcs("commit", "-q", "-m", "first")
    store = repo / "backend" / "definitions" / "store" / "coding" / "two-sum"
    store.mkdir(parents=True)
    (store / "python.v1.json").write_bytes(stored)
    shipped = manifest(entry(checksum=canonical.checksum_bytes(stored)))
    (repo / "backend" / "definitions" / "manifest.json").write_text(json.dumps(shipped))
    vcs("add", "-A")
    vcs("commit", "-q", "-m", "second")
    return repo


def _run(repo: Path, base: str, head: str = "HEAD") -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), "--base", base, "--head", head, "--repo", str(repo)],
                          capture_output=True, text=True, timeout=60)


def test_a_base_that_predates_the_manifest_only_checks_the_head(tmp_path):
    res = _run(_repo(tmp_path), "HEAD~1")
    assert res.returncode == 0, res.stderr
    assert "1 versions, 1 added" in res.stdout


@pytest.mark.parametrize("base", ["no-such-rev", "HEAD~5"], ids=["unknown", "past-the-root"])
def test_a_base_that_cant_be_read_stops_the_check(tmp_path, base):
    # Never taken for a base without a manifest, which would skip every
    # immutability check.
    res = _run(_repo(tmp_path), base)
    assert res.returncode == 2
    assert "can't read revision" in res.stderr


def test_a_head_that_cant_be_read_stops_the_check(tmp_path):
    res = _run(_repo(tmp_path), "HEAD~1", head="no-such-rev")
    assert res.returncode == 2


def test_stored_checksums_are_over_the_exact_bytes(tmp_path):
    # A line ending that a text read would rewrite still matches its checksum.
    res = _run(_repo(tmp_path, stored=b'{"a":\r\n1}'), "HEAD~1")
    assert res.returncode == 0, res.stderr
