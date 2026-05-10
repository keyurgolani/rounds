"""Read every round directory and emit a JS migration that inserts rows
into ai_coding_rounds. Run after authoring/changing a round.

Usage:  python backend/ai_coding/build_seed.py
Output: pocketbase/pb_migrations/1700001200_ai_coding_seed.js
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent / "rounds"
OUT = pathlib.Path(__file__).resolve().parents[2] / "pocketbase" / "pb_migrations" / "1700001200_ai_coding_seed.js"


def _is_artifact(path: pathlib.Path) -> bool:
    if path.suffix in {".pyc", ".pyo"}:
        return True
    return any(part in {"__pycache__", ".pytest_cache", "node_modules", ".DS_Store"} for part in path.parts)


def collect_round(d: pathlib.Path) -> dict:
    manifest = json.loads((d / "manifest.json").read_text())
    starter = []
    for f in sorted((d / "starter").rglob("*")):
        if f.is_file() and not _is_artifact(f.relative_to(d / "starter")):
            starter.append({"path": str(f.relative_to(d / "starter")), "contents": f.read_text(encoding="utf-8")})
    # Embed checkpoint tests as additional starter files in a /tests dir
    # so the candidate sees them. Per-checkpoint test commands point at
    # the appropriate subset via tests_glob.
    for idx, cp in enumerate(manifest["checkpoints"]):
        cp_tests_dir = d / "checkpoints" / str(idx) / "tests"
        cp_hidden_dir = d / "checkpoints" / str(idx) / "hidden_tests"

        if cp_tests_dir.exists():
            for f in sorted(cp_tests_dir.rglob("*")):
                rel = f.relative_to(cp_tests_dir)
                if f.is_file() and not _is_artifact(rel):
                    starter.append({
                        "path": f"tests/checkpoint_{idx}/{rel}",
                        "contents": f.read_text(encoding="utf-8"),
                    })

        hidden_files = []
        if cp_hidden_dir.exists():
            for f in sorted(cp_hidden_dir.rglob("*")):
                rel = f.relative_to(cp_hidden_dir)
                if f.is_file() and not _is_artifact(rel):
                    hidden_files.append({
                        "path": f"tests/checkpoint_{idx}/{rel}",
                        "contents": f.read_text(encoding="utf-8"),
                    })
        cp["hidden_files"] = hidden_files

        # Patch the test_command to point at the checkpoint subdir.
        cp["test_command"] = cp["test_command"].replace(
            "tests/test_checkpoint.py",
            f"tests/checkpoint_{idx}/test_checkpoint.py",
        ).replace(
            "tests/parser.test.ts",
            f"tests/checkpoint_{idx}/parser.test.ts",
        )
    manifest["starter_files"] = starter
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
