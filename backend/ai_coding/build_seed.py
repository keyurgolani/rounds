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


def main():
    rounds = [collect_round(d) for d in sorted(ROOT.iterdir()) if d.is_dir()]
    body = "/// <reference path=\"../pb_data/types.d.ts\" />\n\n"
    body += f"const ROUNDS = {json.dumps(rounds, indent=2)};\n\n"
    body += """\
migrate(
  (db) => {
    const dao = new Dao(db);
    const coll = dao.findCollectionByNameOrId("ai_coding_rounds");
    for (const r of ROUNDS) {
      // Upsert: drop any existing row with this slug so the seed is
      // idempotent across re-applies (the previous strategy of
      // "skip on collision" left old rows with stale checkpoints).
      try {
        const old = dao.findFirstRecordByData("ai_coding_rounds", "slug", r.slug);
        dao.deleteRecord(old);
      } catch (_) { /* not present */ }
      const rec = new Record(coll, {
        slug: r.slug,
        title: r.title,
        difficulty: r.difficulty,
        // For multi-language rounds `language` is the primary (first
        // entry of manifest.languages); the full set is derivable from
        // Object.keys(checkpoints) when checkpoints is a map.
        language: r.language,
        description: r.description,
        starter_files: r.starter_files,
        checkpoints: r.checkpoints,
        rubric: r.rubric,
        topics: r.topics,
        companies: r.companies,
      });
      dao.saveRecord(rec);
    }
  },
  (db) => {
    const dao = new Dao(db);
    for (const r of ROUNDS) {
      try {
        const rec = dao.findFirstRecordByData("ai_coding_rounds", "slug", r.slug);
        dao.deleteRecord(rec);
      } catch (_) { /* ignore */ }
    }
  },
);
"""
    OUT.write_text(body)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
