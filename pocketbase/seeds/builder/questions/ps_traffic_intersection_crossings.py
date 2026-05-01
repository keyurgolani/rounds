"""Traffic Intersection Crossings — Medium. Sweep / Spatial Index.

Given GPS pings (vehicle, time, x, y), count how many times each vehicle
crossed a query intersection (px, py) within [start, end]. Sort by
vehicle+time, sweep adjacent pings, intersect-segment-with-point."""
from builder.registry import register


PAYLOAD = {
    "title": "Traffic Intersection Crossings",
    "difficulty": "Medium",
    "description": (
        "Self-driving cars report `(vehicle_id, time, x, y)` GPS pings. Given a list of pings sorted by "
        "no particular order, plus a query `(start_time, end_time, px, py)`, return the number of TIMES "
        "any vehicle CROSSED the intersection `(px, py)`.\n\n"
        "A 'crossing' is defined as: between two consecutive pings of the same vehicle within "
        "`[start_time, end_time]`, the straight-line segment connecting them passes through `(px, py)`.\n\n"
        "**Simplification:** treat segments as exact straight-line interpolations, and 'pass through' means "
        "the integer point `(px, py)` lies on the segment (inclusive of endpoints). Each segment "
        "contributes at most 1 to the count.\n\n"
        "Pings outside `[start_time, end_time]` are ignored."
    ),
    "hints": [
        "Group pings by vehicle. Sort each vehicle's pings by time.",
        "For each vehicle, sweep adjacent ping pairs whose times both fall in [start, end]. For each pair, check whether (px, py) lies on the segment.",
        "Point-on-segment check: `(p - a) × (b - a) == 0` (collinearity) AND `(p - a) · (b - a)` between `0` and `|b - a|²` (between-ness).",
        "Don't precompute every segment — generate them lazily per vehicle.",
        "Edge cases: vehicle with one ping (no segments), all pings outside the time window, intersection exactly on a ping (counts as crossing in any segment containing that ping).",
    ],
    "constraints": [
        "1 <= |pings| <= 10⁵",
    ],
    "starter_code": {
        "python": "def count_crossings(pings, start_time, end_time, px, py):\n    # Your code here\n    pass",
        "javascript": "function countCrossings(pings, startTime, endTime, px, py) {\n    // Your code here\n}",
        "java": "public int countCrossings(List<Object[]> pings, int startTime, int endTime, int px, int py) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    pings = [['v1', 0, 0, 0], ['v1', 2, 4, 4]]\n"
            "    print(count_crossings(pings, 0, 10, 2, 2))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"pings": [["v1", 0, 0, 0], ["v1", 2, 4, 4]],
                    "start_time": 0, "end_time": 10, "px": 2, "py": 2},
         "expected": 1,
         "description": "Single vehicle crosses (2,2) on the diagonal", "tags": ["basic"]},
        {"input": {"pings": [["v1", 0, 0, 0], ["v1", 5, 10, 0]],
                    "start_time": 0, "end_time": 10, "px": 5, "py": 0},
         "expected": 1,
         "description": "Crossing on horizontal segment", "tags": ["basic"]},
        {"input": {"pings": [["v1", 0, 0, 0], ["v1", 5, 0, 0]],
                    "start_time": 0, "end_time": 10, "px": 1, "py": 1},
         "expected": 0,
         "description": "Vehicle stationary — no crossing", "tags": ["edge"]},
        {"input": {"pings": [["v1", 0, 0, 0], ["v1", 5, 4, 4],
                              ["v2", 0, 4, 0], ["v2", 5, 0, 4]],
                    "start_time": 0, "end_time": 10, "px": 2, "py": 2},
         "expected": 2,
         "description": "Two vehicles cross (2,2) on intersecting paths",
         "tags": ["basic"]},
        {"input": {"pings": [["v1", 0, 0, 0], ["v1", 100, 4, 4]],
                    "start_time": 0, "end_time": 50, "px": 2, "py": 2},
         "expected": 0,
         "description": "Pings span outside the query window — segment ignored",
         "tags": ["edge"]},
        {"input": {"pings": [["v1", 0, 0, 0]],
                    "start_time": 0, "end_time": 10, "px": 0, "py": 0},
         "expected": 0,
         "description": "Single ping — no segment to check", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Group + Sweep + Point-on-Segment (Optimal)",
            "time_complexity": "O(N log N) per query — group + sort + scan",
            "space_complexity": "O(N)",
            "description": (
                "Group pings by vehicle, sort each vehicle's pings by time. For each adjacent pair where "
                "both pings are inside [start, end], test whether (px, py) lies on the segment using "
                "cross-product collinearity and dot-product between-ness."
            ),
            "code": {
                "python": (
                    "from collections import defaultdict\n\n"
                    "def count_crossings(pings, start_time, end_time, px, py):\n"
                    "    by_v = defaultdict(list)\n"
                    "    for v, t, x, y in pings:\n"
                    "        by_v[v].append((t, x, y))\n"
                    "    total = 0\n"
                    "    for v, lst in by_v.items():\n"
                    "        lst.sort()\n"
                    "        for i in range(len(lst) - 1):\n"
                    "            t1, x1, y1 = lst[i]\n"
                    "            t2, x2, y2 = lst[i + 1]\n"
                    "            if t1 < start_time or t2 > end_time:\n"
                    "                continue\n"
                    "            # collinearity: (p - a) x (b - a) == 0\n"
                    "            cross = (px - x1) * (y2 - y1) - (py - y1) * (x2 - x1)\n"
                    "            if cross != 0:\n"
                    "                continue\n"
                    "            # between-ness: dot >= 0 and dot <= |b - a|^2\n"
                    "            dot = (px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)\n"
                    "            seg_len_sq = (x2 - x1) ** 2 + (y2 - y1) ** 2\n"
                    "            if 0 <= dot <= seg_len_sq:\n"
                    "                total += 1\n"
                    "    return total"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Group pings by vehicle. Each vehicle's pings form a path.",
        "2. Sort each vehicle's pings by time. Adjacent pings define segments.",
        "3. For each segment, check if it overlaps the query time window AND passes through (px, py).",
        "4. Point-on-segment: cross product = 0 (collinear) and dot product within [0, |segment|²] (between endpoints).",
        "5. Edge cases: single ping (no segment), stationary vehicle, segment outside window, multiple vehicles.",
        "6. Discuss spatial indexing as the offline-precompute follow-up: bucket segments into a 2D grid.",
    ],
    "tips": [
        "Don't try to detect crossings via 'time of arrival = time at intersection' — interpolation has float issues. Use integer cross/dot and lattice points.",
        "Cross product zero is the necessary condition. Many candidates miss the between-ness check and double-count.",
        "Common follow-up: 'spatial precomputation.' Bucket each segment by its bounding box; intersect query point with buckets.",
        "Common follow-up: 'streaming pings.' Maintain per-vehicle 'last ping' state; on each new ping, emit a segment and check against any active queries.",
        "Common follow-up: 'fuzzy crossings (within ε).' Replace exact equality with magnitude comparisons against ε² to avoid sqrt.",
    ],
    "companies": ["Amazon", "Uber", "Tesla"],
    "topics": ["Geometry", "Sweep", "Hash Table"],
    "time_complexity": "O(N log N)",
    "space_complexity": "O(N)",
}


def REFERENCE(pings, start_time, end_time, px, py):
    from collections import defaultdict
    by_v = defaultdict(list)
    for v, t, x, y in pings:
        by_v[v].append((t, x, y))
    total = 0
    for v, lst in by_v.items():
        lst.sort()
        for i in range(len(lst) - 1):
            t1, x1, y1 = lst[i]
            t2, x2, y2 = lst[i + 1]
            if t1 < start_time or t2 > end_time:
                continue
            # Degenerate segment (vehicle stationary): only matches if query equals that point
            if x1 == x2 and y1 == y2:
                if px == x1 and py == y1:
                    total += 1
                continue
            cross = (px - x1) * (y2 - y1) - (py - y1) * (x2 - x1)
            if cross != 0:
                continue
            dot = (px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)
            seg_len_sq = (x2 - x1) ** 2 + (y2 - y1) ** 2
            if 0 <= dot <= seg_len_sq:
                total += 1
    return total


register(PAYLOAD, REFERENCE)
