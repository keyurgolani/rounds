"""A take-home definition only the corpus stack has (ROUNDS-00A-L08).

No take-home definition is active on this branch: every take-home version
in backend/definitions is retired, so a take-home request stops at the
definition step (410 ``definition_retired``) and a fixture's take-home
body would never run past it. The corpus runner gets one active take-home
definition beside the real ones: the active AI-coding HTTP-client harness
revision, keyed as a take-home, which grades a candidate's ``client.py``
against a local server. Nothing in it is secret, and every real entry
stays as it is.

The launcher (run.sh) writes it before the stack starts:

    python3 tests/conformance/conformance/overlay.py --out DIR

``DIR/manifest.json`` is the real manifest with one more entry and
``DIR/store/take-home/<slug>/python.v1.json`` the definition;
tests/conformance/compose.yml mounts both read-only into the runner's
definitions directory, whose root-only permissions still keep them from
candidate code. The runner checks the new version like any stored one:
its bytes must match the manifest's checksum.

Standard library only, so the launcher runs it with the host's Python.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

SLUG = "corpus-http-client"
VARIANT = "python"
VERSION = 1
# The active revision the corpus definition is keyed from.
SOURCE = "store/ai-coding/hallucinated-http-client/python.v1.json"
PATH = f"store/take-home/{SLUG}/{VARIANT}.v{VERSION}.json"
# What the corpus changes in the source document.
REKEYED = {"track": "take-home", "kind": "take-home", "slug": SLUG}

DEFINITIONS = Path("backend") / "definitions"


def repo_root() -> Path:
    """The checkout this file is in. The corpus driver's image carries only
    tests/conformance, so it has none; only the launcher and the self-tests
    build the overlay."""
    here = Path(__file__).resolve()
    if len(here.parents) < 4:
        raise RuntimeError("the corpus definitions are built from a checkout")
    return here.parents[3]


def take_home_document(root: Path | None = None) -> bytes:
    """The corpus take-home definition: the source revision, re-keyed."""
    root = root or repo_root()
    doc = json.loads((root / DEFINITIONS / SOURCE).read_bytes())
    doc.update(REKEYED)
    return (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8")


def entry(document: bytes) -> dict[str, Any]:
    return {
        "kind": "harness-revision",
        "track": "take-home",
        "slug": SLUG,
        "variant": VARIANT,
        "content_version": VERSION,
        "lifecycle": "active",
        "path": PATH,
        "checksum": "sha256:" + hashlib.sha256(document).hexdigest(),
    }


def overlay(root: Path | None = None) -> tuple[dict[str, Any], bytes]:
    """The corpus manifest (the real one plus the corpus entry) and the
    definition it names."""
    root = root or repo_root()
    manifest = json.loads((root / DEFINITIONS / "manifest.json").read_bytes())
    entries = manifest.get("entries")
    if manifest.get("schema") != "definitions-manifest/v1" or not isinstance(entries, list):
        raise ValueError("backend/definitions/manifest.json isn't a definitions-manifest/v1")
    if any(e.get("track") == "take-home" and e.get("slug") == SLUG for e in entries):
        raise ValueError(f"take-home/{SLUG} is already a real definition")
    document = take_home_document(root)
    return {**manifest, "entries": [*entries, entry(document)]}, document


def write(out: Path, root: Path | None = None) -> None:
    manifest, document = overlay(root)
    target = out / PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(document)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", required=True, help="the directory to write the corpus definitions into")
    args = parser.parse_args(argv)
    write(Path(args.out))
    os.write(1, f"corpus definitions: take-home/{SLUG}/{VARIANT}@{VERSION} in {args.out}\n".encode())
    return 0


if __name__ == "__main__":
    sys.exit(main())
