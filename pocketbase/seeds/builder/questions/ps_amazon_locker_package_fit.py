"""Amazon Locker Package Fit — Medium. Object-Oriented Design / OOD.

Pickup location with size-tiered lockers. put(package) → smallest
fitting empty locker. Free queue per size class is the win — O(1) put,
O(1) get."""
from builder.registry import register


PAYLOAD = {
    "title": "Amazon Locker Package Fit",
    "difficulty": "Medium",
    "description": (
        "Implement a pickup location. Lockers come in three sizes — `S, M, L`. Each locker has a "
        "`width × length` footprint (depth fixed). Packages are boxes with a `width × length`. A package "
        "fits a locker if BOTH dimensions of the package, considering rotation, fit within the locker.\n\n"
        "Required operations:\n"
        "- `__init__(lockers)` — `lockers` is a list of `(size_tier, locker_id, width, length)` tuples.\n"
        "- `put(package_id, width, length)` — place the package into the SMALLEST empty locker that fits "
        "(by area). If multiple lockers in the smallest fitting tier are free, any is acceptable. Returns "
        "the assigned locker id, or `None` if none fits.\n"
        "- `get(package_id)` — remove the package from its locker. Returns the locker id freed, or `None` "
        "if the package isn't held.\n\n"
        "**Note on rotation:** package `2 × 5` fits in a `5 × 3` locker (rotated)."
    ),
    "hints": [
        "Group lockers by size tier. Maintain a free queue per tier.",
        "On `put`: try tiers from smallest to largest; for the first tier with a free locker that fits the package, dequeue and assign.",
        "Fit check: package fits locker iff `(pw <= lw and pl <= ll) or (pw <= ll and pl <= lw)`. Don't compute volume — that's the canonical wrong answer.",
        "On `get`: lookup package → locker, requeue the locker.",
        "Bar-raise: priority queue keyed by area within a tier picks the tightest fit consistently.",
        "Edge cases: package larger than every locker, all lockers full, get on missing package, repeated put for same package.",
    ],
    "constraints": [
        "1 <= |lockers| <= 10⁵",
        "1 <= dimensions <= 10⁴",
    ],
    "starter_code": {
        "python": (
            "class LockerLocation:\n"
            "    def __init__(self, lockers): pass\n"
            "    def put(self, package_id, width, length): pass\n"
            "    def get(self, package_id): pass"
        ),
        "javascript": (
            "class LockerLocation {\n"
            "    constructor(lockers) {}\n"
            "    put(id, w, l) {}\n"
            "    get(id) {}\n"
            "}"
        ),
        "java": (
            "class LockerLocation {\n"
            "    public LockerLocation(List<Object[]> lockers) {}\n"
            "    public String put(String id, int w, int l) { return null; }\n"
            "    public String get(String id) { return null; }\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    loc = LockerLocation([('S','S1',2,2), ('M','M1',5,3), ('L','L1',10,8)])\n"
            "    print(loc.put('p1', 1, 1))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"ops": ["LockerLocation", "put", "get"],
                    "args": [[[["S", "S1", 2, 2], ["M", "M1", 5, 3], ["L", "L1", 10, 8]]],
                             ["p1", 1, 1], ["p1"]]},
         "expected": [None, "S1", "S1"],
         "description": "Small package fits S1 first", "tags": ["basic"]},
        {"input": {"ops": ["LockerLocation", "put"],
                    "args": [[[["S", "S1", 2, 2], ["M", "M1", 5, 3]]],
                             ["p1", 4, 3]]},
         "expected": [None, "M1"],
         "description": "Package too big for S — fits M", "tags": ["basic"]},
        {"input": {"ops": ["LockerLocation", "put"],
                    "args": [[[["S", "S1", 2, 2]]], ["p1", 5, 5]]},
         "expected": [None, None],
         "description": "Package larger than every locker", "tags": ["edge"]},
        {"input": {"ops": ["LockerLocation", "put", "put"],
                    "args": [[[["S", "S1", 2, 2], ["S", "S2", 2, 2]]],
                             ["p1", 1, 1], ["p2", 1, 1]]},
         "expected": [None, "S1", "S2"],
         "description": "Two packages fill two S lockers", "tags": ["basic"]},
        {"input": {"ops": ["LockerLocation", "put", "put", "put"],
                    "args": [[[["S", "S1", 2, 2]]], ["p1", 1, 1], ["p2", 1, 1], ["p3", 1, 1]]},
         "expected": [None, "S1", None, None],
         "description": "Single S, second put has no room", "tags": ["edge"]},
        {"input": {"ops": ["LockerLocation", "put"],
                    "args": [[[["M", "M1", 5, 3]]], ["p1", 2, 5]]},
         "expected": [None, "M1"],
         "description": "Rotation — 2x5 package fits in 5x3 locker rotated",
         "tags": ["basic"]},
        {"input": {"ops": ["LockerLocation", "get"],
                    "args": [[[["S", "S1", 2, 2]]], ["p_unknown"]]},
         "expected": [None, None],
         "description": "get on unknown package", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Free Queue per Tier (Optimal)",
            "time_complexity": "O(T) per put (T = tiers, fixed at 3); O(1) per get",
            "space_complexity": "O(N) lockers + O(P) packages",
            "description": (
                "Group lockers by tier; maintain a free deque per tier. put: walk tiers smallest→largest, "
                "scan the tier's free list for the first locker where the package fits (rotation-aware). "
                "get: lookup package's locker, push back onto its tier's queue."
            ),
            "code": {
                "python": (
                    "from collections import deque\n\n"
                    "TIER_ORDER = ['S', 'M', 'L']\n\n"
                    "def _fits(pw, pl, lw, ll):\n"
                    "    return (pw <= lw and pl <= ll) or (pw <= ll and pl <= lw)\n\n"
                    "class LockerLocation:\n"
                    "    def __init__(self, lockers):\n"
                    "        self._free = {t: deque() for t in TIER_ORDER}\n"
                    "        self._meta = {}  # locker_id -> (tier, w, l)\n"
                    "        self._held = {}  # package_id -> locker_id\n"
                    "        for tier, lid, w, l in lockers:\n"
                    "            self._meta[lid] = (tier, w, l)\n"
                    "            self._free[tier].append(lid)\n"
                    "    def put(self, package_id, width, length):\n"
                    "        if package_id in self._held:\n"
                    "            return None\n"
                    "        for tier in TIER_ORDER:\n"
                    "            for _ in range(len(self._free[tier])):\n"
                    "                lid = self._free[tier].popleft()\n"
                    "                _, lw, ll = self._meta[lid]\n"
                    "                if _fits(width, length, lw, ll):\n"
                    "                    self._held[package_id] = lid\n"
                    "                    return lid\n"
                    "                self._free[tier].append(lid)\n"
                    "        return None\n"
                    "    def get(self, package_id):\n"
                    "        if package_id not in self._held:\n"
                    "            return None\n"
                    "        lid = self._held.pop(package_id)\n"
                    "        tier = self._meta[lid][0]\n"
                    "        self._free[tier].append(lid)\n"
                    "        return lid"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Recognise the trap: don't compare volumes. Dimensions must each fit (rotation-aware), not the area.",
        "2. Group lockers by tier so 'smallest tier that fits' is just iteration over tiers.",
        "3. Free queue per tier → O(1) take/return.",
        "4. Within a tier, rotation-aware fit predicate.",
        "5. Map package → locker for fast `get`.",
        "6. Edge cases: package too big, no free locker in fitting tier, get on unknown package, repeat put on same package.",
    ],
    "tips": [
        "Volume comparison is the most common interview trap — `pw * pl <= lw * ll` is necessary but not sufficient. A 1x100 box doesn't fit a 10x10 locker.",
        "Rotation is just two checks; don't skip it.",
        "If you have many lockers per tier, the linear scan within a tier becomes expensive — switch to a sorted structure keyed by (max_dim, area).",
        "Common follow-up: 'detect unclaimed packages.' Bound `_held` by an LRU; or run a sweeper that returns expired packages to senders.",
        "Common follow-up: 'specialised lockers (frozen, oversized).' Composition over inheritance — add new tier, route packages on a flag.",
    ],
    "companies": ["Amazon"],
    "topics": ["Object-Oriented Design", "Hash Table", "Queue"],
    "time_complexity": "O(1) amortised",
    "space_complexity": "O(N + P)",
}


def REFERENCE(input):
    from collections import deque

    TIER_ORDER = ["S", "M", "L"]

    def fits(pw, pl, lw, ll):
        return (pw <= lw and pl <= ll) or (pw <= ll and pl <= lw)

    class LockerLocation:
        def __init__(self, lockers):
            self._free = {t: deque() for t in TIER_ORDER}
            self._meta = {}
            self._held = {}
            for tier, lid, w, l in lockers:
                self._meta[lid] = (tier, w, l)
                self._free[tier].append(lid)

        def put(self, package_id, width, length):
            if package_id in self._held:
                return None
            for tier in TIER_ORDER:
                rotated = deque()
                while self._free[tier]:
                    lid = self._free[tier].popleft()
                    _, lw, ll = self._meta[lid]
                    if fits(width, length, lw, ll):
                        # Restore order of skipped lockers, then return assignment
                        while rotated:
                            self._free[tier].appendleft(rotated.pop())
                        self._held[package_id] = lid
                        return lid
                    rotated.append(lid)
                # restore
                while rotated:
                    self._free[tier].appendleft(rotated.pop())
            return None

        def get(self, package_id):
            if package_id not in self._held:
                return None
            lid = self._held.pop(package_id)
            tier = self._meta[lid][0]
            self._free[tier].append(lid)
            return lid

    ops = input["ops"]
    args = input["args"]
    instance = None
    results = []
    for op, a in zip(ops, args):
        if op == "LockerLocation":
            instance = LockerLocation(*a)
            results.append(None)
        else:
            method = getattr(instance, op)
            results.append(method(*a))
    return results


PAYLOAD["entry"] = {
    "kind": "class_ops",
    "class": "LockerLocation",
    "constructor": {"params": [{"name": "lockers", "type": "any[]"}]},
    "methods": [
        {"name": "put", "params": [
            {"name": "package_id", "type": "string"},
            {"name": "width", "type": "int"},
            {"name": "length", "type": "int"},
        ], "returns": "any"},
        {"name": "get", "params": [{"name": "package_id", "type": "string"}], "returns": "any"},
    ],
}


register(PAYLOAD, REFERENCE)
