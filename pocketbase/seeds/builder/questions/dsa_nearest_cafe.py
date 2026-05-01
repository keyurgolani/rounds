"""Nearest Café Finder — Medium. KD-tree / Spatial Indexing.

Given a list of cafés (lat, lng) and a user location, return the
nearest café. Senior bar discusses scaling: KD-tree for O(log n)
queries, geohash for distributed sharding, R-tree for moving objects."""
from builder.registry import register
from builder.registry import any_of


PAYLOAD = {
    "title": "Nearest Café Finder",
    "difficulty": "Medium",
    "description": (
        "Given a list of cafés as `(name, x, y)` tuples and a user location `(ux, uy)`, return the **name** "
        "of the café closest to the user by Euclidean distance. If multiple cafés are equidistant, return "
        "any of them.\n\n"
        "**Example:**\n"
        "- Input: `cafes = [('A', 0, 0), ('B', 3, 4), ('C', 1, 1)], user = (0, 0)`\n"
        "- Output: `'A'`\n\n"
        "**Follow-up scaling discussion:**\n"
        "- 100 cafés in one city → linear scan is fine.\n"
        "- 100K cafés → KD-tree for O(log n) queries.\n"
        "- 100M cafés globally → geohash + sharded indexes per geo cell."
    ),
    "hints": [
        "Linear scan: compute distance to each café, track the minimum. O(n) per query — fine for small n.",
        "Skip the square root: comparing squared distances gives the same ordering and avoids the floating-point cost.",
        "For repeated queries: build a KD-tree once (O(n log n)), then answer each query in O(log n) average.",
        "For massive scale: geohash by location, route each query to the relevant cell's index.",
        "For moving objects (e.g. taxi locations updating every second), the offline KD-tree no longer fits — use an R-tree, or rebuild periodically.",
    ],
    "constraints": [
        "0 <= |cafes| <= 10⁴",
        "Coordinates are floats with reasonable magnitude",
    ],
    "starter_code": {
        "python": "def nearest_cafe(cafes, user):\n    # Your code here\n    pass",
        "javascript": "function nearestCafe(cafes, user) {\n    // Your code here\n}",
        "java": "public String nearestCafe(List<Object[]> cafes, double[] user) {\n    // Your code here\n    return null;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cafes = [('A', 0, 0), ('B', 3, 4), ('C', 1, 1)]\n"
            "    print(nearest_cafe(cafes, (0, 0)))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"cafes": [["A", 0, 0], ["B", 3, 4], ["C", 1, 1]], "user": [0, 0]},
         "expected": "A",
         "description": "User exactly at café A", "tags": ["basic"]},
        {"input": {"cafes": [["A", 0, 0], ["B", 3, 4]], "user": [3, 4]},
         "expected": "B",
         "description": "User exactly at café B", "tags": ["basic"]},
        {"input": {"cafes": [["A", 1, 1], ["B", 1, -1]], "user": [0, 0]},
         "expected": any_of(["A", "B"]),
         "description": "Two cafés equidistant — either is acceptable", "tags": ["tricky"]},
        {"input": {"cafes": [["solo", 5, 5]], "user": [0, 0]},
         "expected": "solo",
         "description": "Single café", "tags": ["edge"]},
        {"input": {"cafes": [], "user": [0, 0]}, "expected": None,
         "description": "No cafés — return None", "tags": ["edge"]},
        {"input": {"cafes": [[f"c{i}", i, 0] for i in range(1000)], "user": [500, 0]},
         "expected": "c500",
         "description": "1000 cafés, exact match in middle", "tags": ["large"]},
    ],
    "solutions": [
        {
            "title": "Linear Scan (Optimal for small n)",
            "time_complexity": "O(n) per query",
            "space_complexity": "O(1)",
            "description": (
                "Compute squared Euclidean distance to each café, track the minimum. Skip the sqrt — it's "
                "monotonic, so it doesn't change the argmin and avoids float work. For small n (typical "
                "city-scale, hundreds of cafés), this beats every fancier alternative on simplicity."
            ),
            "code": {
                "python": (
                    "def nearest_cafe(cafes, user):\n"
                    "    if not cafes:\n"
                    "        return None\n"
                    "    ux, uy = user\n"
                    "    best_name = None\n"
                    "    best_d2 = float('inf')\n"
                    "    for name, x, y in cafes:\n"
                    "        d2 = (x - ux) ** 2 + (y - uy) ** 2\n"
                    "        if d2 < best_d2:\n"
                    "            best_d2 = d2\n"
                    "            best_name = name\n"
                    "    return best_name"
                ),
                "javascript": (
                    "function nearestCafe(cafes, user) {\n"
                    "    if (!cafes.length) return null;\n"
                    "    const [ux, uy] = user;\n"
                    "    let best = null, bestD2 = Infinity;\n"
                    "    for (const [name, x, y] of cafes) {\n"
                    "        const d2 = (x - ux) ** 2 + (y - uy) ** 2;\n"
                    "        if (d2 < bestD2) { bestD2 = d2; best = name; }\n"
                    "    }\n"
                    "    return best;\n"
                    "}"
                ),
            },
        },
        {
            "title": "KD-tree (Optimal for repeated queries on large n)",
            "time_complexity": "O(n log n) build, O(log n) average per query",
            "space_complexity": "O(n)",
            "description": (
                "Build a KD-tree over the cafés once. Each query descends the tree, pruning branches whose "
                "bounding box is further than the current best. Average O(log n) per query. Worth it once "
                "you cross ~1K points or have many concurrent queries."
            ),
            "code": {
                "python": (
                    "# Sketch — production code typically uses scipy.spatial.cKDTree.\n"
                    "from scipy.spatial import cKDTree  # type: ignore\n\n"
                    "def nearest_cafe(cafes, user):\n"
                    "    if not cafes:\n"
                    "        return None\n"
                    "    pts = [(x, y) for _, x, y in cafes]\n"
                    "    names = [n for n, _, _ in cafes]\n"
                    "    tree = cKDTree(pts)\n"
                    "    _, idx = tree.query(user, k=1)\n"
                    "    return names[idx]"
                ),
            },
        },
        {
            "title": "Geohash + Cell Lookup (Distributed Scale)",
            "time_complexity": "O(1) per query within a cell, plus a one-time bucketing pass",
            "space_complexity": "O(n) total across cells",
            "description": (
                "For globe-scale (100M+ points), partition the world into geohash cells. Index each cell "
                "separately. A query hashes its location to a cell and consults that cell's index (which "
                "could itself be a KD-tree). Adjacent-cell fallback handles boundary cases. This is the "
                "production architecture behind Uber/DoorDash/Yelp nearest-X queries."
            ),
            "code": {
                "python": (
                    "# Architectural sketch — full geohash code is out of scope for an interview answer.\n"
                    "def nearest_cafe(cafes, user):\n"
                    "    raise NotImplementedError(\n"
                    "        'Geohash-sharded approach. In production: 1) bucket every café by its 6-char\\n'\n"
                    "        ' geohash; 2) keep a per-cell KD-tree; 3) query hashes its location to a cell\\n'\n"
                    "        ' and falls back to neighbouring cells if the boundary is too close.'\n"
                    "    )"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Clarify scale. 100 cafés vs 100M cafés have very different right answers.",
        "2. State linear scan as the n=small baseline. Show the squared-distance trick (skip sqrt).",
        "3. If repeated queries: KD-tree. O(n log n) build, O(log n) query.",
        "4. If global scale: geohash + sharded indexes. Mention adjacent-cell fallback for points near a cell boundary.",
        "5. If moving objects (taxis, bikes): offline KD-tree decays — switch to R-tree or rebuild periodically.",
        "6. Edge cases: empty list (return None / sentinel), single café, equidistant cafés (any acceptable).",
    ],
    "tips": [
        "Always raise the squared-distance trick — it's a free win and shows numerical-thinking instinct.",
        "Don't lead with the KD-tree for n=10. The interviewer wants to see you match complexity to scale.",
        "Common follow-up: 'k nearest cafés' instead of 1. Same algorithm, maintain a k-sized max-heap.",
        "Common follow-up: 'cafés open right now.' Filter on a secondary attribute before/during the spatial query.",
        "Common follow-up: 'cafés the user hasn't visited.' Lookup a per-user visited set; filter the candidates.",
    ],
    "companies": ["Amazon", "Uber", "DoorDash", "Yelp", "Google"],
    "topics": ["Geometry", "KD-tree", "Distance", "Sorting"],
    "time_complexity": "O(n) per query (linear); O(log n) with KD-tree",
    "space_complexity": "O(1) linear; O(n) KD-tree",
}


def REFERENCE(cafes, user):
    if not cafes:
        return None
    ux, uy = user
    best_name = None
    best_d2 = float("inf")
    for name, x, y in cafes:
        d2 = (x - ux) ** 2 + (y - uy) ** 2
        if d2 < best_d2:
            best_d2 = d2
            best_name = name
    return best_name


register(PAYLOAD, REFERENCE)
