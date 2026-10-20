"""Read every assignment directory and emit a JS migration that inserts
rows into take_home_assignments. Run after authoring/changing an
assignment.

Usage:  python3 backend/take_home/build_seed.py
Output: pocketbase/pb_migrations/1700001400_take_home_seed.js
"""
import hashlib
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
# at its own version, never a delete. What runs and how it scores live
# only in the compiled revision, so the row carries no entrypoint or
# harness files.
DEFINITIONS_MANIFEST = pathlib.Path(__file__).resolve().parents[2] / "backend" / "definitions" / "manifest.json"
MIGRATIONS = pathlib.Path(__file__).resolve().parents[2] / "pocketbase" / "pb_migrations"
PRESENTATION_NAME = "take_home_presentation"
PRESENTATION_FIELDS = ("title", "difficulty", "language", "time_budget_min", "ai_policy", "prompt_md",
                       "starter_files", "rubric", "topics", "companies")


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


def presentation_row(row: dict) -> dict:
    """The display fields of a collected assignment, at its own version."""
    return {"definition_version": row["definition_version"],
            **{k: row[k] for k in PRESENTATION_FIELDS if k in row}, "slug": row["slug"]}


def presentation_path(rows: list[dict], migrations: pathlib.Path = MIGRATIONS) -> pathlib.Path | None:
    """Where the migration for these assignments' versions goes, or None
    when one for exactly these versions is already there. Each version
    bump gets a new file, numbered after every migration in the
    directory, so a migration that may have been applied is never written
    again."""
    versions = sorted((r["slug"], r["definition_version"]) for r in rows)
    stamp = hashlib.sha256(json.dumps(versions).encode("utf-8")).hexdigest()[:12]
    name = f"{PRESENTATION_NAME}_{stamp}.js"
    if any(migrations.glob(f"*_{name}")):
        return None
    numbers = [int(p.name.split("_", 1)[0]) for p in migrations.glob("*.js") if p.name.split("_", 1)[0].isdigit()]
    return migrations / f"{max(numbers, default=0) + 1}_{name}"


def presentation_migration(rows: list[dict]) -> str:
    """A presentation-only upsert migration for ``rows``. It updates a row
    by slug or creates it, never deletes; down() leaves every row."""
    display = [presentation_row(r) for r in rows]
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
    path = presentation_path(rows, MIGRATIONS)
    if path is None:
        print("take_home presentation: a migration for these versions is already there; nothing to emit.")
        return
    with open(path, "x", encoding="utf-8") as out:
        out.write(presentation_migration(rows))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
