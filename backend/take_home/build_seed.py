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


# ROUNDS-00A-L02: the three assignments under assignments/ are retired, so
# they compile only as retired definitions (build.py RETIRED_TAKE_HOME) and
# this builder emits nothing for them. The committed 1700001400 seed stays
# as it is. A future, non-retired assignment with a compiled take-home
# definition past version 1 gets a presentation-only upsert migration here,
# never a delete.
DEFINITIONS_MANIFEST =pathlib.Path(__file__).resolve().parents[2] / "backend" / "definitions" / "manifest.json"
PRESENTATION_OUT = (
    pathlib.Path(__file__).resolve().parents[2] / "pocketbase" / "pb_migrations" / "1700006400_take_home_presentation.js"
)
PRESENTATION_FIELDS = ("title", "difficulty", "language", "entrypoint", "time_budget_min", "ai_policy", "prompt_md",
                       "starter_files", "harness_files", "rubric", "topics", "companies")


def _manifest_entries() -> list[dict]:
    if not DEFINITIONS_MANIFEST.exists():
        return []
    return json.loads(DEFINITIONS_MANIFEST.read_text(encoding="utf-8")).get("entries", [])


def live_assignments() -> list[dict]:
    """The assignments whose take-home definition is active (not retired).
    Every current assignment is retired, so this is empty."""
    retired = {e["slug"] for e in _manifest_entries() if e.get("track") == "take-home" and e.get("lifecycle") == "retired"}
    active = {e["slug"]: e["content_version"] for e in _manifest_entries()
              if e.get("track") == "take-home" and e.get("lifecycle") == "active"}
    if not ROOT.exists():
        return []
    out = []
    for d in sorted(ROOT.iterdir()):
        if not d.is_dir():
            continue
        slug = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["slug"]
        if slug in retired or slug not in active:
            continue
        row = collect_assignment(d)
        row["definition_version"] = active[slug]
        out.append(row)
    return out


def presentation_migration(rows: list[dict]) -> str:
    """A presentation-only upsert migration for ``rows``. It updates a row
    by slug or creates it, never deletes; down() leaves every row."""
    display = [{"definition_version": r["definition_version"],
                **{k: r.get(k) for k in PRESENTATION_FIELDS}, "slug": r["slug"]} for r in rows]
    body = "/// <reference path=\"../pb_data/types.d.ts\" />\n\n"
    body += f"const ASSIGNMENTS = {json.dumps(display, indent=2)};\n\n"
    body += """\
migrate(
  (db) => {
    const dao = new Dao(db);
    const coll = dao.findCollectionByNameOrId("take_home_assignments");
    for (const a of ASSIGNMENTS) {
      // Upsert in place: update the existing row or create it. Never
      // delete, so drafts and attempts survive.
      let rec;
      try {
        rec = dao.findFirstRecordByData("take_home_assignments", "slug", a.slug);
      } catch (_) {
        rec = new Record(coll, { slug: a.slug });
      }
      for (const [key, value] of Object.entries(a)) rec.set(key, value);
      dao.saveRecord(rec);
    }
  },
  (_db) => {
    // Presentation-only and forward-safe: nothing to undo.
  },
);
"""
    return body


def main() -> None:
    rows = live_assignments()
    if not rows:
        print("take_home presentation: every assignment is retired; nothing to emit.")
        return
    PRESENTATION_OUT.write_text(presentation_migration(rows), encoding="utf-8")
    print(f"Wrote {PRESENTATION_OUT}")


if __name__ == "__main__":
    main()
