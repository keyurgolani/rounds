"""Speeding Cars in City Grid — Medium. Geometry / Math.

Given GPS pings of cars at integer time steps and a speed limit,
return the set of car ids that exceeded the limit between any pair of
consecutive pings."""
from builder.registry import register


PAYLOAD = {
    "title": "Speeding Cars in City Grid",
    "difficulty": "Medium",
    "description": (
        "Given a list of GPS pings `(car_id, t, x, y)` (timestamps in seconds, coordinates in metres) "
        "and a `speed_limit` in metres/second, return the **set of distinct car ids** that exceeded the "
        "speed limit between any consecutive pair of their pings.\n\n"
        "Speed between two pings = `distance / (t2 - t1)`. Distance is Euclidean.\n\n"
        "**Example:**\n"
        "- Input: `pings = [['c1', 0, 0, 0], ['c1', 1, 30, 40]]`, `speed_limit = 25`\n"
        "- Output: `['c1']` — the car moved 50m in 1s = 50 m/s > 25 m/s\n\n"
        "Return ids in any order. Each car appears at most once."
    ),
    "hints": [
        "Group pings by car_id. Sort each car's pings by time.",
        "For each adjacent pair, compute Euclidean distance / time delta. If > speed_limit, mark the car as speeding.",
        "Avoid sqrt: compare `distance²` against `(speed_limit · dt)²` to stay in integer arithmetic when coords are integers.",
        "Edge cases: car with one ping (no segment), zero time delta (skip; bad data), no cars exceeding.",
    ],
    "constraints": [
        "1 <= |pings| <= 10⁵",
        "0 <= speed_limit <= 10³",
    ],
    "starter_code": {
        "python": "def speeding_cars(pings, speed_limit):\n    # Your code here\n    pass",
        "javascript": "function speedingCars(pings, speedLimit) {\n    // Your code here\n}",
        "java": "public Set<String> speedingCars(List<Object[]> pings, double speedLimit) {\n    // Your code here\n    return new HashSet<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(speeding_cars([['c1', 0, 0, 0], ['c1', 1, 30, 40]], 25))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"pings": [["c1", 0, 0, 0], ["c1", 1, 30, 40]], "speed_limit": 25},
         "expected": ["c1"],
         "description": "50 m/s exceeds 25 m/s", "tags": ["basic"]},
        {"input": {"pings": [["c1", 0, 0, 0], ["c1", 10, 1, 0]], "speed_limit": 25},
         "expected": [],
         "description": "0.1 m/s — well under limit", "tags": ["basic"]},
        {"input": {"pings": [["c1", 0, 0, 0]], "speed_limit": 25}, "expected": [],
         "description": "Single ping — no segment", "tags": ["edge"]},
        {"input": {"pings": [["c1", 0, 0, 0], ["c1", 0, 100, 0]], "speed_limit": 25},
         "expected": [],
         "description": "Zero time delta — bad data, skip", "tags": ["edge"]},
        {"input": {"pings": [["c1", 0, 0, 0], ["c1", 1, 25, 0],
                              ["c2", 0, 0, 0], ["c2", 1, 50, 0]], "speed_limit": 25},
         "expected": ["c2"],
         "description": "c1 exactly at limit (not over); c2 exceeds", "tags": ["tricky"]},
        {"input": {"pings": [["c1", 0, 0, 0], ["c1", 1, 30, 0], ["c1", 2, 40, 0]],
                    "speed_limit": 25},
         "expected": ["c1"],
         "description": "First segment exceeds, second doesn't — still flagged",
         "tags": ["basic"]},
    ],
    "solutions": [
        {
            "title": "Group + Adjacent-Pair Speed Check (Optimal)",
            "time_complexity": "O(N log N) per query (group + sort)",
            "space_complexity": "O(N)",
            "description": (
                "Group pings by car. Sort each car's pings by time. For each adjacent pair, compute "
                "speed and compare. Stop checking a car as soon as it's flagged."
            ),
            "code": {
                "python": (
                    "from collections import defaultdict\n\n"
                    "def speeding_cars(pings, speed_limit):\n"
                    "    by_car = defaultdict(list)\n"
                    "    for cid, t, x, y in pings:\n"
                    "        by_car[cid].append((t, x, y))\n"
                    "    out = []\n"
                    "    limit_sq = speed_limit * speed_limit\n"
                    "    for cid, lst in by_car.items():\n"
                    "        lst.sort()\n"
                    "        for i in range(len(lst) - 1):\n"
                    "            t1, x1, y1 = lst[i]\n"
                    "            t2, x2, y2 = lst[i + 1]\n"
                    "            dt = t2 - t1\n"
                    "            if dt <= 0:\n"
                    "                continue\n"
                    "            dist_sq = (x2 - x1) ** 2 + (y2 - y1) ** 2\n"
                    "            if dist_sq > limit_sq * dt * dt:\n"
                    "                out.append(cid)\n"
                    "                break\n"
                    "    return out"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Group by car. Each car's pings form a path.",
        "2. Sort each car's pings by time. Adjacent pairs define segments.",
        "3. For each segment: speed = distance / dt. Compare against limit.",
        "4. Squared distance comparison avoids the sqrt and stays in integers when coords are integers.",
        "5. Strict inequality: 'exactly at limit' is NOT speeding.",
        "6. Edge cases: single ping, zero dt (bad data), unsorted input.",
    ],
    "tips": [
        "Compare `distance² > limit² · dt²` to skip the sqrt — exact for integer coordinates, faster than floats.",
        "Strict vs non-strict: clarify '>=' vs '>'. Default is strict (over the limit, not 'at the limit').",
        "If the input is already sorted by time globally, you can skip the per-car sort — but don't assume it.",
        "Common follow-up: 'streaming pings.' Maintain per-car last-ping; on each new ping, compute one segment.",
        "Common follow-up: 'speed limit varies by location.' Lookup a 2D speed-limit grid; compare segment max against the most-restrictive limit on its path.",
    ],
    "companies": ["Amazon", "Uber", "Tesla"],
    "topics": ["Geometry", "Hash Table", "Sorting"],
    "time_complexity": "O(N log N)",
    "space_complexity": "O(N)",
}


def REFERENCE(pings, speed_limit):
    from collections import defaultdict
    by_car = defaultdict(list)
    for cid, t, x, y in pings:
        by_car[cid].append((t, x, y))
    out = []
    limit_sq = speed_limit * speed_limit
    for cid, lst in by_car.items():
        lst.sort()
        for i in range(len(lst) - 1):
            t1, x1, y1 = lst[i]
            t2, x2, y2 = lst[i + 1]
            dt = t2 - t1
            if dt <= 0:
                continue
            dist_sq = (x2 - x1) ** 2 + (y2 - y1) ** 2
            if dist_sq > limit_sq * dt * dt:
                out.append(cid)
                break
    return out


register(PAYLOAD, REFERENCE)
