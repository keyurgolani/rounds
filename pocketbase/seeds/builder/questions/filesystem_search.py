"""search_files — Medium. API Design / Filtering.

A multi-criteria filter over a flat file inventory: name substring,
file vs directory, size range, age range, extension whitelist, plus
an explicit sort criterion and direction. The senior signal is in
how cleanly you separate the filter predicates from the sort and how
you handle 'absent criterion = match anything' without a tower of
nested if-statements. Realistic interview prompts ask you to design
the API surface (criteria object, return shape) before writing the
code — exercising taste and not just typing speed."""
from builder.registry import register


PAYLOAD = {
    "title": "Filesystem Search API",
    "difficulty": "Medium",
    "description": (
        "You're designing the search backend for a filesystem-style application. Implement a "
        "function `search_files(files, criteria)` that returns the entries in `files` matching "
        "every populated criterion, sorted as requested.\n\n"
        "**Input — `files`:** a list of dicts, each describing one entry:\n"
        "```\n"
        "{\n"
        "  \"name\": str,           # base name, e.g. \"report.pdf\"\n"
        "  \"path\": str,           # full path, e.g. \"/home/me/report.pdf\"\n"
        "  \"size\": int,           # bytes; directories may pass 0\n"
        "  \"created_ts\": int,     # unix-second timestamp\n"
        "  \"is_directory\": bool,  # true for dirs, false for files\n"
        "}\n"
        "```\n\n"
        "**Input — `criteria`:** a dict with any subset of these keys (every key is optional; if "
        "absent, the filter is not applied):\n"
        "- `name_substring` (str, case-insensitive substring match against `name`)\n"
        "- `kind` (one of `\"file\"`, `\"directory\"`, `\"both\"`; default `\"both\"`)\n"
        "- `min_size`, `max_size` (int; bytes; only enforced on FILES, not directories)\n"
        "- `start_ts`, `end_ts` (int; unix seconds; matches when `start_ts <= created_ts <= end_ts`)\n"
        "- `extensions` (list of strings, leading dot or no dot, case-insensitive; matches the "
        "lowercased extension of `name`; only enforced on FILES)\n"
        "- `sort_by` (one of `\"name\"`, `\"size\"`, `\"created_ts\"`, `\"extension\"`; default `\"name\"`)\n"
        "- `sort_direction` (one of `\"asc\"`, `\"desc\"`; default `\"asc\"`)\n\n"
        "Return a list of the matching `file` dicts in sorted order. **Don't** mutate the input. "
        "An entry passes when EVERY populated criterion accepts it — absent criteria are no-ops, "
        "which means a `criteria = {}` returns the full input sorted by name ascending.\n\n"
        "**Example:**\n"
        "```\n"
        "files = [\n"
        "  {\"name\": \"a.txt\", \"path\": \"/x/a.txt\", \"size\": 100, \"created_ts\": 10, \"is_directory\": False},\n"
        "  {\"name\": \"b.txt\", \"path\": \"/x/b.txt\", \"size\": 500, \"created_ts\": 20, \"is_directory\": False},\n"
        "  {\"name\": \"docs\",  \"path\": \"/x/docs\",  \"size\":   0, \"created_ts\":  5, \"is_directory\": True},\n"
        "]\n"
        "criteria = {\"kind\": \"file\", \"min_size\": 200}\n"
        "→ [{\"name\": \"b.txt\", ...}]\n"
        "```"
    ),
    "hints": [
        "Treat each criterion as an independent predicate `(file) → bool`. The match is the AND of all populated predicates. This decomposition keeps the matcher flat and easy to extend.",
        "Absent criterion ↔ identity predicate. Express this in code: if the key isn't in `criteria`, skip the predicate construction — don't use `criteria.get(key)` and a None-check inline at the predicate; that path branches inside the hot loop.",
        "Size and extension filters apply only to files. Directories should pass them unconditionally. Encode this as 'predicate is `is_directory or matches`'.",
        "Extension normalisation: lowercase, strip leading dot. The user can pass `[\".PDF\", \"txt\"]` and you should match both `.pdf` and `.txt` files. Compute the file's extension once per file (last `.` segment) — don't re-split inside the loop.",
        "Case-insensitive name substring: lowercase both sides and use `in`. Don't reach for regex unless the prompt specifies wildcards.",
        "Sort with a deterministic tiebreak. When `sort_by=\"size\"` produces ties, secondary-sort by name ascending so the output is stable and reviewable. Use `key=lambda f: (primary, f[\"name\"])`.",
        "Don't mutate the input list (`sorted` returns a new list; `sort` mutates). The criterion dict is also input — don't write to it.",
        "Empty `criteria` is the all-pass case; default sort is name ascending. Test this; it's the easiest miss.",
    ],
    "constraints": [
        "0 <= len(files) <= 10⁴",
        "Every file dict contains all five required fields with the documented types.",
        "0 <= size <= 10¹²",
        "0 <= created_ts <= 10¹⁰",
        "Names contain printable characters; extension is everything after the LAST `.` in the name (so `archive.tar.gz` has extension `gz`).",
        "Extensions in criteria are matched case-insensitively after stripping a leading dot.",
        "Criteria dict may contain none, some, or all of the documented keys; unrecognised keys must be ignored.",
    ],
    "starter_code": {
        "python": (
            "def search_files(files, criteria):\n"
            "    # Your code here\n"
            "    pass"
        ),
        "javascript": (
            "function searchFiles(files, criteria) {\n"
            "    // Your code here\n"
            "}"
        ),
        "java": (
            "public java.util.List<java.util.Map<String, Object>> searchFiles(\n"
            "        java.util.List<java.util.Map<String, Object>> files,\n"
            "        java.util.Map<String, Object> criteria) {\n"
            "    // Your code here\n"
            "    return java.util.Collections.emptyList();\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    files = [\n"
            "        {\"name\": \"a.txt\", \"path\": \"/x/a.txt\", \"size\": 100,\n"
            "         \"created_ts\": 10, \"is_directory\": False},\n"
            "        {\"name\": \"b.txt\", \"path\": \"/x/b.txt\", \"size\": 500,\n"
            "         \"created_ts\": 20, \"is_directory\": False},\n"
            "    ]\n"
            "    print(search_files(files, {\"min_size\": 200}))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {
            "files": [
                {"name": "a.txt", "path": "/x/a.txt", "size": 100, "created_ts": 10, "is_directory": False},
                {"name": "b.txt", "path": "/x/b.txt", "size": 500, "created_ts": 20, "is_directory": False},
                {"name": "docs", "path": "/x/docs", "size": 0, "created_ts": 5, "is_directory": True},
            ],
            "criteria": {},
         },
         "expected": [
            {"name": "a.txt", "path": "/x/a.txt", "size": 100, "created_ts": 10, "is_directory": False},
            {"name": "b.txt", "path": "/x/b.txt", "size": 500, "created_ts": 20, "is_directory": False},
            {"name": "docs", "path": "/x/docs", "size": 0, "created_ts": 5, "is_directory": True},
         ],
         "description": "Empty criteria returns all entries sorted by name ascending",
         "tags": ["basic"]},
        {"input": {
            "files": [
                {"name": "a.txt", "path": "/x/a.txt", "size": 100, "created_ts": 10, "is_directory": False},
                {"name": "b.txt", "path": "/x/b.txt", "size": 500, "created_ts": 20, "is_directory": False},
                {"name": "docs", "path": "/x/docs", "size": 0, "created_ts": 5, "is_directory": True},
            ],
            "criteria": {"kind": "file", "min_size": 200},
         },
         "expected": [
            {"name": "b.txt", "path": "/x/b.txt", "size": 500, "created_ts": 20, "is_directory": False},
         ],
         "description": "kind=file + min_size filter excludes the smaller file and the directory",
         "tags": ["basic"]},
        {"input": {
            "files": [
                {"name": "report.pdf", "path": "/d/report.pdf", "size": 100, "created_ts": 1, "is_directory": False},
                {"name": "ReportFinal.PDF", "path": "/d/ReportFinal.PDF", "size": 200, "created_ts": 2, "is_directory": False},
                {"name": "image.png", "path": "/d/image.png", "size": 300, "created_ts": 3, "is_directory": False},
            ],
            "criteria": {"name_substring": "REPORT"},
         },
         "expected": [
            {"name": "ReportFinal.PDF", "path": "/d/ReportFinal.PDF", "size": 200, "created_ts": 2, "is_directory": False},
            {"name": "report.pdf", "path": "/d/report.pdf", "size": 100, "created_ts": 1, "is_directory": False},
         ],
         "description": "Case-insensitive name substring match (sort is case-sensitive: 'R' < 'r')",
         "tags": ["basic"]},
        {"input": {
            "files": [
                {"name": "a.txt", "path": "/p/a.txt", "size": 100, "created_ts": 10, "is_directory": False},
                {"name": "b.PDF", "path": "/p/b.PDF", "size": 200, "created_ts": 20, "is_directory": False},
                {"name": "c.tar.gz", "path": "/p/c.tar.gz", "size": 300, "created_ts": 30, "is_directory": False},
            ],
            "criteria": {"extensions": [".pdf", "GZ"]},
         },
         "expected": [
            {"name": "b.PDF", "path": "/p/b.PDF", "size": 200, "created_ts": 20, "is_directory": False},
            {"name": "c.tar.gz", "path": "/p/c.tar.gz", "size": 300, "created_ts": 30, "is_directory": False},
         ],
         "description": "Extension list matches case-insensitively, with or without leading dot",
         "tags": ["tricky"]},
        {"input": {
            "files": [
                {"name": "old.txt", "path": "/o/old.txt", "size": 100, "created_ts": 100, "is_directory": False},
                {"name": "mid.txt", "path": "/o/mid.txt", "size": 200, "created_ts": 200, "is_directory": False},
                {"name": "new.txt", "path": "/o/new.txt", "size": 300, "created_ts": 300, "is_directory": False},
            ],
            "criteria": {"start_ts": 150, "end_ts": 250},
         },
         "expected": [
            {"name": "mid.txt", "path": "/o/mid.txt", "size": 200, "created_ts": 200, "is_directory": False},
         ],
         "description": "Inclusive timestamp range filter",
         "tags": ["basic"]},
        {"input": {
            "files": [
                {"name": "a.txt", "path": "/s/a.txt", "size": 100, "created_ts": 1, "is_directory": False},
                {"name": "b.txt", "path": "/s/b.txt", "size": 200, "created_ts": 2, "is_directory": False},
                {"name": "c.txt", "path": "/s/c.txt", "size": 300, "created_ts": 3, "is_directory": False},
            ],
            "criteria": {"sort_by": "size", "sort_direction": "desc"},
         },
         "expected": [
            {"name": "c.txt", "path": "/s/c.txt", "size": 300, "created_ts": 3, "is_directory": False},
            {"name": "b.txt", "path": "/s/b.txt", "size": 200, "created_ts": 2, "is_directory": False},
            {"name": "a.txt", "path": "/s/a.txt", "size": 100, "created_ts": 1, "is_directory": False},
         ],
         "description": "Sort by size descending",
         "tags": ["basic"]},
        {"input": {
            "files": [
                {"name": "data.json", "path": "/e/data.json", "size": 100, "created_ts": 1, "is_directory": False},
                {"name": "image.png", "path": "/e/image.png", "size": 200, "created_ts": 2, "is_directory": False},
                {"name": "code.py", "path": "/e/code.py", "size": 300, "created_ts": 3, "is_directory": False},
            ],
            "criteria": {"sort_by": "extension", "sort_direction": "asc"},
         },
         "expected": [
            {"name": "data.json", "path": "/e/data.json", "size": 100, "created_ts": 1, "is_directory": False},
            {"name": "image.png", "path": "/e/image.png", "size": 200, "created_ts": 2, "is_directory": False},
            {"name": "code.py", "path": "/e/code.py", "size": 300, "created_ts": 3, "is_directory": False},
         ],
         "description": "Sort by extension ascending — json, png, py",
         "tags": ["basic"]},
        {"input": {
            "files": [
                {"name": "logs", "path": "/dirs/logs", "size": 0, "created_ts": 1, "is_directory": True},
                {"name": "tmp", "path": "/dirs/tmp", "size": 0, "created_ts": 2, "is_directory": True},
                {"name": "a.txt", "path": "/dirs/a.txt", "size": 100, "created_ts": 3, "is_directory": False},
            ],
            "criteria": {"kind": "directory"},
         },
         "expected": [
            {"name": "logs", "path": "/dirs/logs", "size": 0, "created_ts": 1, "is_directory": True},
            {"name": "tmp", "path": "/dirs/tmp", "size": 0, "created_ts": 2, "is_directory": True},
         ],
         "description": "kind=directory excludes files",
         "tags": ["basic"]},
        {"input": {
            "files": [
                {"name": "small.bin", "path": "/m/small.bin", "size": 10, "created_ts": 1, "is_directory": False},
                {"name": "medium.bin", "path": "/m/medium.bin", "size": 1000, "created_ts": 2, "is_directory": False},
                {"name": "large.bin", "path": "/m/large.bin", "size": 100000, "created_ts": 3, "is_directory": False},
                {"name": "myfolder", "path": "/m/myfolder", "size": 0, "created_ts": 0, "is_directory": True},
            ],
            "criteria": {"min_size": 100, "max_size": 10000},
         },
         "expected": [
            {"name": "medium.bin", "path": "/m/medium.bin", "size": 1000, "created_ts": 2, "is_directory": False},
            {"name": "myfolder", "path": "/m/myfolder", "size": 0, "created_ts": 0, "is_directory": True},
         ],
         "description": "min_size + max_size — directories pass through size filters; output sorted by name asc",
         "tags": ["tricky"]},
        {"input": {
            "files": [],
            "criteria": {"min_size": 100},
         },
         "expected": [],
         "description": "Empty file list returns empty",
         "tags": ["edge"]},
        {"input": {
            "files": [
                {"name": "a.TXT", "path": "/c/a.TXT", "size": 100, "created_ts": 5, "is_directory": False},
                {"name": "b.txt", "path": "/c/b.txt", "size": 200, "created_ts": 3, "is_directory": False},
                {"name": "c.txt", "path": "/c/c.txt", "size": 100, "created_ts": 1, "is_directory": False},
            ],
            "criteria": {"sort_by": "size", "sort_direction": "asc"},
         },
         "expected": [
            {"name": "a.TXT", "path": "/c/a.TXT", "size": 100, "created_ts": 5, "is_directory": False},
            {"name": "c.txt", "path": "/c/c.txt", "size": 100, "created_ts": 1, "is_directory": False},
            {"name": "b.txt", "path": "/c/b.txt", "size": 200, "created_ts": 3, "is_directory": False},
         ],
         "description": "Tied size — secondary sort by name ascending (case-sensitive on the raw name)",
         "tags": ["tricky"]},
        {"input": {
            "files": [
                {"name": "a.txt", "path": "/u/a.txt", "size": 100, "created_ts": 1, "is_directory": False},
            ],
            "criteria": {"unknown_key": "ignore me"},
         },
         "expected": [
            {"name": "a.txt", "path": "/u/a.txt", "size": 100, "created_ts": 1, "is_directory": False},
         ],
         "description": "Unrecognised criteria keys are silently ignored",
         "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Predicate-Per-Criterion + Sort (Optimal)",
            "time_complexity": "O(N log N) sort dominates; O(N) for the filter pass",
            "space_complexity": "O(N) for the output list",
            "description": (
                "Build the predicate list once from the populated criteria, walk the files, keep "
                "those that pass every predicate, then sort. The shape is intentional: one place "
                "per criterion that hardcodes its semantics, and a single AND-fold over the "
                "predicates per file. New criteria add a new predicate constructor; nothing else "
                "changes. Extension normalisation (lowercase, strip leading dot) happens once per "
                "criterion, not per file. Sort uses a stable key with name-ascending tiebreak."
            ),
            "code": {
                "python": (
                    "def search_files(files, criteria):\n"
                    "    criteria = criteria or {}\n"
                    "    \n"
                    "    def get_ext(name):\n"
                    "        i = name.rfind('.')\n"
                    "        return name[i + 1:].lower() if i >= 0 else ''\n"
                    "    \n"
                    "    predicates = []\n"
                    "    \n"
                    "    if 'name_substring' in criteria:\n"
                    "        needle = criteria['name_substring'].lower()\n"
                    "        predicates.append(lambda f, _n=needle: _n in f['name'].lower())\n"
                    "    \n"
                    "    if 'kind' in criteria:\n"
                    "        kind = criteria['kind']\n"
                    "        if kind == 'file':\n"
                    "            predicates.append(lambda f: not f['is_directory'])\n"
                    "        elif kind == 'directory':\n"
                    "            predicates.append(lambda f: f['is_directory'])\n"
                    "        # 'both' or unknown → no predicate\n"
                    "    \n"
                    "    # Default-arg capture pins the value at definition time. Without it,\n"
                    "    # the lambda closes over the loop-mutated `m`/`t` and every predicate\n"
                    "    # ends up using the LAST assigned value. Classic late-binding trap.\n"
                    "    if 'min_size' in criteria:\n"
                    "        predicates.append(\n"
                    "            lambda f, _m=criteria['min_size']: f['is_directory'] or f['size'] >= _m\n"
                    "        )\n"
                    "    \n"
                    "    if 'max_size' in criteria:\n"
                    "        predicates.append(\n"
                    "            lambda f, _m=criteria['max_size']: f['is_directory'] or f['size'] <= _m\n"
                    "        )\n"
                    "    \n"
                    "    if 'start_ts' in criteria:\n"
                    "        predicates.append(\n"
                    "            lambda f, _t=criteria['start_ts']: f['created_ts'] >= _t\n"
                    "        )\n"
                    "    \n"
                    "    if 'end_ts' in criteria:\n"
                    "        predicates.append(\n"
                    "            lambda f, _t=criteria['end_ts']: f['created_ts'] <= _t\n"
                    "        )\n"
                    "    \n"
                    "    if 'extensions' in criteria:\n"
                    "        normalised = {ext.lower().lstrip('.') for ext in criteria['extensions']}\n"
                    "        predicates.append(\n"
                    "            lambda f, _n=normalised: f['is_directory'] or get_ext(f['name']) in _n\n"
                    "        )\n"
                    "    \n"
                    "    matches = [f for f in files if all(p(f) for p in predicates)]\n"
                    "    \n"
                    "    sort_by = criteria.get('sort_by', 'name')\n"
                    "    direction = criteria.get('sort_direction', 'asc')\n"
                    "    reverse = direction == 'desc'\n"
                    "    \n"
                    "    if sort_by == 'name':\n"
                    "        key = lambda f: (f['name'], f['name'])\n"
                    "    elif sort_by == 'size':\n"
                    "        key = lambda f: (f['size'], f['name'])\n"
                    "    elif sort_by == 'created_ts':\n"
                    "        key = lambda f: (f['created_ts'], f['name'])\n"
                    "    elif sort_by == 'extension':\n"
                    "        key = lambda f: (get_ext(f['name']), f['name'])\n"
                    "    else:\n"
                    "        key = lambda f: (f['name'], f['name'])\n"
                    "    \n"
                    "    return sorted(matches, key=key, reverse=reverse)"
                ),
                "javascript": (
                    "function searchFiles(files, criteria) {\n"
                    "    criteria = criteria || {};\n"
                    "    const getExt = (name) => {\n"
                    "        const i = name.lastIndexOf('.');\n"
                    "        return i >= 0 ? name.slice(i + 1).toLowerCase() : '';\n"
                    "    };\n"
                    "    const preds = [];\n"
                    "    if ('name_substring' in criteria) {\n"
                    "        const needle = criteria.name_substring.toLowerCase();\n"
                    "        preds.push(f => f.name.toLowerCase().includes(needle));\n"
                    "    }\n"
                    "    if ('kind' in criteria) {\n"
                    "        if (criteria.kind === 'file') preds.push(f => !f.is_directory);\n"
                    "        else if (criteria.kind === 'directory') preds.push(f => f.is_directory);\n"
                    "    }\n"
                    "    if ('min_size' in criteria) {\n"
                    "        const m = criteria.min_size;\n"
                    "        preds.push(f => f.is_directory || f.size >= m);\n"
                    "    }\n"
                    "    if ('max_size' in criteria) {\n"
                    "        const m = criteria.max_size;\n"
                    "        preds.push(f => f.is_directory || f.size <= m);\n"
                    "    }\n"
                    "    if ('start_ts' in criteria) {\n"
                    "        const t = criteria.start_ts;\n"
                    "        preds.push(f => f.created_ts >= t);\n"
                    "    }\n"
                    "    if ('end_ts' in criteria) {\n"
                    "        const t = criteria.end_ts;\n"
                    "        preds.push(f => f.created_ts <= t);\n"
                    "    }\n"
                    "    if ('extensions' in criteria) {\n"
                    "        const set = new Set(criteria.extensions.map(e => e.toLowerCase().replace(/^\\./, '')));\n"
                    "        preds.push(f => f.is_directory || set.has(getExt(f.name)));\n"
                    "    }\n"
                    "    const matches = files.filter(f => preds.every(p => p(f)));\n"
                    "    const sortBy = criteria.sort_by || 'name';\n"
                    "    const dir = criteria.sort_direction || 'asc';\n"
                    "    const cmp = (a, b) => {\n"
                    "        const get = (f) => sortBy === 'size' ? [f.size, f.name]\n"
                    "                          : sortBy === 'created_ts' ? [f.created_ts, f.name]\n"
                    "                          : sortBy === 'extension' ? [getExt(f.name), f.name]\n"
                    "                          : [f.name, f.name];\n"
                    "        const ka = get(a), kb = get(b);\n"
                    "        if (ka[0] < kb[0]) return -1;\n"
                    "        if (ka[0] > kb[0]) return 1;\n"
                    "        if (ka[1] < kb[1]) return -1;\n"
                    "        if (ka[1] > kb[1]) return 1;\n"
                    "        return 0;\n"
                    "    };\n"
                    "    const sorted = [...matches].sort(cmp);\n"
                    "    return dir === 'desc' ? sorted.reverse() : sorted;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Inline Single-Pass Loop (Beginner Shape)",
            "time_complexity": "O(N log N)",
            "space_complexity": "O(N)",
            "description": (
                "All criteria checked inline in one big `if` per file. Easy to write fast under "
                "pressure but hard to extend cleanly — every new criterion adds another branch in the "
                "hot loop and the criterion-list is implicit. Show this version only as the "
                "'first cut', then refactor to predicate-per-criterion in the same interview."
            ),
            "code": {
                "python": (
                    "def search_files(files, criteria):\n"
                    "    criteria = criteria or {}\n"
                    "    name_sub = criteria.get('name_substring', '').lower()\n"
                    "    kind = criteria.get('kind', 'both')\n"
                    "    mn = criteria.get('min_size'); mx = criteria.get('max_size')\n"
                    "    sts = criteria.get('start_ts'); ets = criteria.get('end_ts')\n"
                    "    exts = criteria.get('extensions')\n"
                    "    if exts is not None:\n"
                    "        exts = {e.lower().lstrip('.') for e in exts}\n"
                    "    \n"
                    "    matches = []\n"
                    "    for f in files:\n"
                    "        nm = f['name']; isd = f['is_directory']\n"
                    "        if name_sub and name_sub not in nm.lower(): continue\n"
                    "        if kind == 'file' and isd: continue\n"
                    "        if kind == 'directory' and not isd: continue\n"
                    "        if not isd:\n"
                    "            if mn is not None and f['size'] < mn: continue\n"
                    "            if mx is not None and f['size'] > mx: continue\n"
                    "        if sts is not None and f['created_ts'] < sts: continue\n"
                    "        if ets is not None and f['created_ts'] > ets: continue\n"
                    "        if exts is not None and not isd:\n"
                    "            i = nm.rfind('.')\n"
                    "            ext = nm[i + 1:].lower() if i >= 0 else ''\n"
                    "            if ext not in exts: continue\n"
                    "        matches.append(f)\n"
                    "    \n"
                    "    sort_by = criteria.get('sort_by', 'name')\n"
                    "    reverse = criteria.get('sort_direction', 'asc') == 'desc'\n"
                    "    def get_ext(name):\n"
                    "        i = name.rfind('.')\n"
                    "        return name[i + 1:].lower() if i >= 0 else ''\n"
                    "    keymap = {\n"
                    "        'name': lambda f: (f['name'], f['name']),\n"
                    "        'size': lambda f: (f['size'], f['name']),\n"
                    "        'created_ts': lambda f: (f['created_ts'], f['name']),\n"
                    "        'extension': lambda f: (get_ext(f['name']), f['name']),\n"
                    "    }\n"
                    "    return sorted(matches, key=keymap.get(sort_by, keymap['name']), reverse=reverse)"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate the API. Inputs: a flat file inventory + a criteria dict. Output: filtered, sorted list. Absent criterion = no-op.",
        "2. Choose the data shape. Flat list of dicts is what the prompt gives us. (Tree-of-directories is a different problem; if asked to extend, walk the tree externally and feed the leaf list into this function.)",
        "3. Decompose: filter (predicates) + sort. Fight the urge to put the sort key inside the filter loop.",
        "4. Predicate per criterion. Each is independent: 'this criterion is satisfied'. The match is AND-fold over the predicates. Adding a new criterion is one new predicate-builder; the loop and sort don't change.",
        "5. Directories vs files. Size and extension filters are file-only. Encode this as 'predicate is `is_directory or matches`'. Don't have the caller filter directories out before invoking.",
        "6. Normalise inputs once, not per file. Lowercase the name substring, lowercase the extensions, strip leading dots. The hot loop is integer / string comparisons after that.",
        "7. Sort with a tiebreak. `key=(primary, name)` keeps the output deterministic when two files share the primary sort field. `sorted` is stable in Python, but the explicit tiebreak makes the contract clear without relying on stability.",
        "8. Edge cases: empty files, empty criteria, unrecognised criteria keys (silently ignored), case-insensitive matches, ties in sort.",
        "9. Senior reach: stream this for large inventories. Replace the eager sort with a top-K heap if the caller passes a `limit` parameter; replace the in-memory list with a generator if memory matters.",
    ],
    "tips": [
        "Predicate-per-criterion is the design choice that signals 'I've thought about extension'. Walk the criteria once, build a list of predicates, walk files once, AND the predicates.",
        "Extension matching is the trap. Users pass `.PDF`, `pdf`, `PDF` — all should match `.pdf` files. Normalise (lower + lstrip dot) once when building the predicate.",
        "Don't apply size or extension filters to directories. The reference behaviour is 'directories pass through these filters unchanged' — otherwise a `min_size=100` filter hides every directory.",
        "Sort tiebreak by name ascending. Otherwise `sort_by=size` gives non-reproducible output across runs (because Python dict iteration order, while now stable, isn't a contract callers should depend on).",
        "An empty criteria dict matches every file. The default sort is name ascending. Test this first.",
        "Common follow-up: 'now make it tree-walking + recursive'. Same predicates; the input is now a tree-walking generator that yields files; the result is the same flat list. The filtering function shouldn't change.",
        "Common follow-up: 'now allow regex name matching'. Replace the `in` substring with `re.search`; isolate the pattern compile to once-per-call.",
        "Common follow-up: 'pagination'. Add `offset`, `limit` to criteria; slice the sorted list. For large N, consider a top-K heap to avoid the full sort.",
        "Pure functional shape. Don't mutate the input list or the criteria dict. `sorted(...)` returns a new list; `.sort()` mutates.",
    ],
    "companies": ["Amazon", "Microsoft", "Apple", "Bloomberg", "Dropbox", "Google"],
    "topics": ["Hash Table", "Sorting", "Filter", "Design"],
    "time_complexity": "O(N log N)",
    "space_complexity": "O(N)",
    "entry": {
        "kind": "function",
        "name": "search_files",
        "params": [
            {"name": "files", "type": "list"},
            {"name": "criteria", "type": "dict"},
        ],
    },
}


def REFERENCE(files, criteria):
    criteria = criteria or {}

    def get_ext(name):
        i = name.rfind('.')
        return name[i + 1:].lower() if i >= 0 else ''

    predicates = []

    if 'name_substring' in criteria:
        needle = criteria['name_substring'].lower()
        predicates.append(lambda f, _n=needle: _n in f['name'].lower())

    if 'kind' in criteria:
        kind = criteria['kind']
        if kind == 'file':
            predicates.append(lambda f: not f['is_directory'])
        elif kind == 'directory':
            predicates.append(lambda f: f['is_directory'])

    if 'min_size' in criteria:
        m = criteria['min_size']
        predicates.append(lambda f, _m=m: f['is_directory'] or f['size'] >= _m)

    if 'max_size' in criteria:
        m = criteria['max_size']
        predicates.append(lambda f, _m=m: f['is_directory'] or f['size'] <= _m)

    if 'start_ts' in criteria:
        t = criteria['start_ts']
        predicates.append(lambda f, _t=t: f['created_ts'] >= _t)

    if 'end_ts' in criteria:
        t = criteria['end_ts']
        predicates.append(lambda f, _t=t: f['created_ts'] <= _t)

    if 'extensions' in criteria:
        normalised = {ext.lower().lstrip('.') for ext in criteria['extensions']}
        predicates.append(
            lambda f, _n=normalised: f['is_directory'] or get_ext(f['name']) in _n
        )

    matches = [f for f in files if all(p(f) for p in predicates)]

    sort_by = criteria.get('sort_by', 'name')
    direction = criteria.get('sort_direction', 'asc')
    reverse = direction == 'desc'

    if sort_by == 'size':
        key = lambda f: (f['size'], f['name'])
    elif sort_by == 'created_ts':
        key = lambda f: (f['created_ts'], f['name'])
    elif sort_by == 'extension':
        key = lambda f: (get_ext(f['name']), f['name'])
    else:
        key = lambda f: (f['name'], f['name'])

    return sorted(matches, key=key, reverse=reverse)


register(PAYLOAD, REFERENCE)
