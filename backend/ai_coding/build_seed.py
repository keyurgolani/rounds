"""Read every round directory and emit a JS migration that inserts rows
into ai_coding_rounds. Run after authoring/changing a round.

Usage:  python backend/ai_coding/build_seed.py
Output: pocketbase/pb_migrations/1700001200_ai_coding_seed.js

Round layout
============

A round directory looks like one of two shapes:

  Single-language (legacy):
    manifest.json              # contains "language": "..." and "checkpoints": [...]
    starter/...                # files at the project root
    checkpoints/<idx>/tests/...        # visible tests for checkpoint idx
    checkpoints/<idx>/hidden_tests/... # hidden tests for checkpoint idx

  Multi-language:
    manifest.json              # contains "languages": ["python", "typescript"]
                               #          "variants": {<lang>: {checkpoints: [...]}}
    starter/<lang>/...                          # per-language starter files
    checkpoints/<lang>/<idx>/tests/...          # per-language visible tests
    checkpoints/<lang>/<idx>/hidden_tests/...   # per-language hidden tests

For multi-language rounds the emitted row carries:
  - language: the primary language (first entry of languages[])
  - languages: the full array
  - starter_files: an object keyed by language, each value an array of {path, contents}
  - checkpoints: an object keyed by language, each value the array of checkpoint dicts

For single-language rounds the legacy flat-array shape is preserved.
"""
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent / "rounds"
OUT = pathlib.Path(__file__).resolve().parents[2] / "pocketbase" / "pb_migrations" / "1700001200_ai_coding_seed.js"


def _is_artifact(path: pathlib.Path) -> bool:
    if path.suffix in {".pyc", ".pyo"}:
        return True
    return any(part in {"__pycache__", ".pytest_cache", "node_modules", ".DS_Store"} for part in path.parts)


def _collect_files(base: pathlib.Path, path_prefix: str = "") -> list[dict]:
    """Walk `base` recursively and return [{path, contents}] entries.
    `path_prefix` is prepended to every emitted path."""
    out: list[dict] = []
    if not base.exists():
        return out
    for f in sorted(base.rglob("*")):
        rel = f.relative_to(base)
        if not f.is_file() or _is_artifact(rel):
            continue
        emit_path = f"{path_prefix}{rel}" if path_prefix else str(rel)
        out.append({"path": emit_path, "contents": f.read_text(encoding="utf-8")})
    return out


def _attach_checkpoint_tests(
    checkpoints: list[dict],
    cp_base: pathlib.Path,
) -> tuple[list[dict], list[dict]]:
    """Build the starter-files additions for visible tests and the
    hidden_files attachments per checkpoint. Returns (starter_additions,
    cps_with_hidden_files_set)."""
    starter_additions: list[dict] = []
    annotated: list[dict] = []
    for idx, cp in enumerate(checkpoints):
        cp = dict(cp)  # shallow copy so we don't mutate the manifest
        cp_tests_dir = cp_base / str(idx) / "tests"
        cp_hidden_dir = cp_base / str(idx) / "hidden_tests"

        for f in _collect_files(cp_tests_dir, path_prefix=f"tests/checkpoint_{idx}/"):
            starter_additions.append(f)

        cp["hidden_files"] = _collect_files(
            cp_hidden_dir, path_prefix=f"tests/checkpoint_{idx}/"
        )

        # Patch the test_command to point at the checkpoint subdir.
        cp["test_command"] = (
            cp["test_command"]
            .replace("tests/test_checkpoint.py", f"tests/checkpoint_{idx}/test_checkpoint.py")
            .replace("tests/test_visible.py", f"tests/checkpoint_{idx}/test_visible.py")
            .replace("tests/parser.test.ts", f"tests/checkpoint_{idx}/parser.test.ts")
            .replace("tests/client.test.ts", f"tests/checkpoint_{idx}/client.test.ts")
        )
        annotated.append(cp)
    return starter_additions, annotated


def collect_round(d: pathlib.Path) -> dict:
    manifest = json.loads((d / "manifest.json").read_text())

    is_multi = "variants" in manifest and "languages" in manifest

    if is_multi:
        languages = list(manifest["languages"])
        starter_by_lang: dict[str, list[dict]] = {}
        checkpoints_by_lang: dict[str, list[dict]] = {}
        for lang in languages:
            variant = manifest["variants"].get(lang) or {}
            starter = _collect_files(d / "starter" / lang)
            cp_base = d / "checkpoints" / lang
            additions, cps = _attach_checkpoint_tests(
                variant.get("checkpoints", []), cp_base
            )
            starter.extend(additions)
            starter_by_lang[lang] = starter
            checkpoints_by_lang[lang] = cps

        manifest["language"] = languages[0]  # primary language for legacy consumers
        manifest["starter_files"] = starter_by_lang
        manifest["checkpoints"] = checkpoints_by_lang
        # Strip the verbose `variants` block from the emitted row — the
        # information now lives in starter_files + checkpoints maps and
        # the languages array. Keeping `variants` in the row would
        # double the JSON column size for no consumer benefit.
        manifest.pop("variants", None)
        return manifest

    # Single-language legacy path.
    starter = _collect_files(d / "starter")
    additions, cps = _attach_checkpoint_tests(
        manifest.get("checkpoints", []), d / "checkpoints"
    )
    starter.extend(additions)
    manifest["starter_files"] = starter
    manifest["checkpoints"] = cps
    return manifest


# ROUNDS-00A-L02: the committed 1700001200_ai_coding_seed.js stays the v1
# seed (the legacy runtime still reads it); build.py compiles the same
# sources into the server-owned harness revisions. When a round's compiled
# definition advances past version 1, this builder emits a NEW,
# presentation-only migration that upserts the round's display fields and
# sets that round's own definition_version, never deleting a row. What
# runs and how it scores live only in the compiled revision, so the row
# carries no test command, hidden files, or test globs. At version 1 there
# is nothing to add, so it writes nothing.
DEFINITIONS_MANIFEST = pathlib.Path(__file__).resolve().parents[2] / "backend" / "definitions" / "manifest.json"
MIGRATIONS = pathlib.Path(__file__).resolve().parents[2] / "pocketbase" / "pb_migrations"
PRESENTATION_NAME = "ai_coding_presentation"
PRESENTATION_FIELDS = ("title", "difficulty", "language", "languages", "description", "starter_files", "checkpoints",
                       "rubric", "topics", "companies")
# What a checkpoint shows; its test command, globs, and hidden files don't
# belong on a presentation row.
CHECKPOINT_FIELDS = ("label", "prompt", "ai_allowed")


def active_versions(manifest_path: pathlib.Path, track: str) -> dict[str, int]:
    """Each slug's active content version for ``track`` in the compiled
    manifest. Every variant of a slug shares its version."""
    if not manifest_path.exists():
        return {}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    out: dict[str, int] = {}
    for e in manifest.get("entries", []):
        if e.get("track") == track and e.get("lifecycle") == "active":
            out[e["slug"]] = max(out.get(e["slug"], 0), e["content_version"])
    return out


def _display_checkpoints(checkpoints):
    def one(cp):
        return {k: cp[k] for k in CHECKPOINT_FIELDS if k in cp} if isinstance(cp, dict) else cp

    if isinstance(checkpoints, dict):
        return {lang: [one(cp) for cp in cps] for lang, cps in checkpoints.items()}
    return [one(cp) for cp in checkpoints or []]


def presentation_row(round_row: dict, version: int) -> dict:
    """The display fields of a collected round, at its own version."""
    row = {k: round_row[k] for k in PRESENTATION_FIELDS if k in round_row}
    if "checkpoints" in row:
        row["checkpoints"] = _display_checkpoints(row["checkpoints"])
    return {"definition_version": version, **row, "slug": round_row["slug"]}


def presentation_path(rows: list[dict], migrations: pathlib.Path = MIGRATIONS) -> pathlib.Path | None:
    """Where the migration for these rounds' versions goes, or None when
    one for exactly these versions is already there. Each version bump
    gets a new file, numbered after every migration in the directory, so
    a migration that may have been applied is never written again."""
    versions = sorted((r["slug"], r["definition_version"]) for r in rows)
    stamp = hashlib.sha256(json.dumps(versions).encode("utf-8")).hexdigest()[:12]
    name = f"{PRESENTATION_NAME}_{stamp}.js"
    if any(migrations.glob(f"*_{name}")):
        return None
    numbers = [int(p.name.split("_", 1)[0]) for p in migrations.glob("*.js") if p.name.split("_", 1)[0].isdigit()]
    return migrations / f"{max(numbers, default=0) + 1}_{name}"


def presentation_migration(rows: list[dict]) -> str:
    """A presentation-only upsert migration for ``rows``, each already at
    its own definition_version. It updates an existing row by slug or
    creates one, and never deletes; down() leaves every row in place."""
    body = "/// <reference path=\"../pb_data/types.d.ts\" />\n\n"
    body += f"const ROUNDS = {json.dumps(rows, indent=2)};\n\n"
    body += """\
migrate(
  (db) => {
    const dao = new Dao(db);
    const coll = dao.findCollectionByNameOrId("ai_coding_rounds");
    for (const r of ROUNDS) {
      // Upsert in place: update the existing row or create it. Never
      // delete, so drafts and attempts that relate to it survive.
      let rec;
      try {
        rec = dao.findFirstRecordByData("ai_coding_rounds", "slug", r.slug);
      } catch (_) {
        rec = new Record(coll, { slug: r.slug });
      }
      for (const [key, value] of Object.entries(r)) rec.set(key, value);
      dao.saveRecord(rec);
    }
  },
  (_db) => {
    // Presentation-only and forward-safe: a version bump never deletes a
    // row, so there is nothing to undo.
  },
);
"""
    return body


def main():
    versions = active_versions(DEFINITIONS_MANIFEST, "ai-coding")
    rows = []
    for d in sorted(ROOT.iterdir()):
        if not d.is_dir():
            continue
        round_row = collect_round(d)
        version = versions.get(round_row["slug"], 1)
        if version > 1:
            rows.append(presentation_row(round_row, version))
    if not rows:
        print("ai_coding presentation: every round is at version 1, the committed seed (1700001200); nothing to emit.")
        return
    path = presentation_path(rows, MIGRATIONS)
    if path is None:
        print("ai_coding presentation: a migration for these versions is already there; nothing to emit.")
        return
    with open(path, "x", encoding="utf-8") as out:
        out.write(presentation_migration(rows))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
