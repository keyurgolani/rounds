"""Read every assignment directory and emit a JS migration that inserts
rows into take_home_assignments. Run after authoring/changing an
assignment.

Usage:  python3 backend/take_home/build_seed.py
Output: pocketbase/pb_migrations/1700001400_take_home_seed.js
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent / "assignments"
OUT = pathlib.Path(__file__).resolve().parents[2] / "pocketbase" / "pb_migrations" / "1700001400_take_home_seed.js"


def _is_artifact(path: pathlib.Path) -> bool:
    if path.suffix in {".pyc", ".pyo"}:
        return True
    return any(part in {"__pycache__", ".pytest_cache", "node_modules", ".DS_Store"} for part in path.parts)


def _walk(root: pathlib.Path) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if not root.exists():
        return out
    for f in sorted(root.rglob("*")):
        rel = f.relative_to(root)
        if f.is_file() and not _is_artifact(rel):
            out.append({"path": str(rel), "contents": f.read_text(encoding="utf-8")})
    return out


def collect_assignment(d: pathlib.Path) -> dict:
    manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    prompt_md = (d / "prompt.md").read_text(encoding="utf-8")
    starter_files = _walk(d / "starter")
    # Harness files: paths keep their `harness/` prefix (relative to
    # the assignment root, not the harness/ subdir) so entrypoints
    # like `python3 harness/run.py` work at runtime.
    harness_files: list[dict[str, str]] = []
    hd = d / "harness"
    if hd.exists():
        for f in sorted(hd.rglob("*")):
            rel = f.relative_to(d)
            if f.is_file() and not _is_artifact(rel):
                harness_files.append({"path": str(rel), "contents": f.read_text(encoding="utf-8")})
    return {
        "slug": manifest["slug"],
        "title": manifest["title"],
        "difficulty": manifest.get("difficulty", "medium"),
        "language": manifest["language"],
        "time_budget_min": int(manifest.get("time_budget_min", 60)),
        "ai_policy": manifest.get("ai_policy", "off"),
        "entrypoint": manifest["entrypoint"],
        "prompt_md": prompt_md,
        "starter_files": starter_files,
        "harness_files": harness_files,
        "rubric": manifest.get("rubric", {"items": []}),
        "topics": manifest.get("topics", []),
        "companies": manifest.get("companies", []),
    }


def main() -> None:
    if not ROOT.exists():
        # No assignments authored yet — emit an empty seed so the
        # migration applies cleanly.
        rows: list[dict] = []
    else:
        rows = [collect_assignment(d) for d in sorted(ROOT.iterdir()) if d.is_dir()]
    body = "/// <reference path=\"../pb_data/types.d.ts\" />\n\n"
    body += f"const ASSIGNMENTS = {json.dumps(rows, indent=2)};\n\n"
    body += """\
migrate(
  (db) => {
    const dao = new Dao(db);
    const coll = dao.findCollectionByNameOrId("take_home_assignments");
    for (const a of ASSIGNMENTS) {
      try {
        const old = dao.findFirstRecordByData("take_home_assignments", "slug", a.slug);
        dao.deleteRecord(old);
      } catch (_) { /* not present */ }
      const rec = new Record(coll, {
        slug: a.slug,
        title: a.title,
        difficulty: a.difficulty,
        language: a.language,
        entrypoint: a.entrypoint,
        time_budget_min: a.time_budget_min,
        ai_policy: a.ai_policy,
        prompt_md: a.prompt_md,
        starter_files: a.starter_files,
        harness_files: a.harness_files,
        rubric: a.rubric,
        topics: a.topics,
        companies: a.companies,
      });
      dao.saveRecord(rec);
    }
  },
  (db) => {
    const dao = new Dao(db);
    for (const a of ASSIGNMENTS) {
      try {
        const rec = dao.findFirstRecordByData("take_home_assignments", "slug", a.slug);
        dao.deleteRecord(rec);
      } catch (_) { /* ignore */ }
    }
  },
);
"""
    OUT.write_text(body, encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
