"""Parking Lot System — Medium. Logical & Maintainable / OOD.

Classic OOD question. Park, leave, charge — but the real bar is
extensibility: vehicle types, multiple lots, multiple pricing models.
Strategy pattern for rates, mediator for park-responsibility."""
from builder.registry import register


PAYLOAD = {
    "title": "Parking Lot Management System",
    "difficulty": "Medium",
    "description": (
        "Design a parking-lot management system. Required behaviours:\n"
        "1. `park(vehicle_type, plate, time_in)` — assign a spot. Compact spots fit Sedans and Bikes; "
        "Standard spots fit Trucks too. Returns the assigned spot id, or `None` if full.\n"
        "2. `leave(plate, time_out)` — free the spot and return the fee.\n"
        "3. `available()` — number of free spots.\n\n"
        "**Test framing:** the lot is initialised with `compact_count` and `standard_count`. Pricing is "
        "`$2/hour` (rounded up). All times are integer hours.\n\n"
        "**Example:**\n"
        "```\n"
        "lot = ParkingLot(compact=2, standard=1)\n"
        "lot.park('sedan', 'A', 0)   → 'C0'\n"
        "lot.park('truck', 'B', 0)   → 'S0'\n"
        "lot.park('truck', 'C', 0)   → None  (no compact accepts trucks)\n"
        "lot.leave('A', 3)            → 6     ($2 × 3 hours)\n"
        "lot.available()              → 2\n"
        "```"
    ),
    "hints": [
        "Vehicle hierarchy: `Vehicle` base, `Sedan/Bike/Truck` subclasses. Each has a `fits(spot_type)` predicate.",
        "Spot hierarchy: `Spot` base, `CompactSpot/StandardSpot`. Each tracks occupant + spot id.",
        "Strategy pattern for pricing: `RateStrategy` interface, with `HourlyRate`, `EarlyBirdRate`, etc. Lots compose a rate strategy.",
        "Mediator: `ParkingLot.park(vehicle)` rather than `Vehicle.park(lot)` — single owner of allocation logic.",
        "For multiple lots / locations, factor pricing per lot; lots share a `Vehicle/Spot` model but each has its own rate.",
        "Concurrency follow-up: lock per spot pool, or use atomic 'compare-and-claim' on a free queue.",
    ],
    "constraints": [
        "0 <= total operations <= 10⁴",
    ],
    "starter_code": {
        "python": (
            "class ParkingLot:\n"
            "    def __init__(self, compact, standard): pass\n"
            "    def park(self, vehicle_type, plate, time_in): pass\n"
            "    def leave(self, plate, time_out): pass\n"
            "    def available(self): pass"
        ),
        "javascript": (
            "class ParkingLot {\n"
            "    constructor(compact, standard) {}\n"
            "    park(type, plate, timeIn) {}\n"
            "    leave(plate, timeOut) {}\n"
            "    available() {}\n"
            "}"
        ),
        "java": (
            "class ParkingLot {\n"
            "    public ParkingLot(int compact, int standard) {}\n"
            "    public String park(String type, String plate, int timeIn) { return null; }\n"
            "    public int leave(String plate, int timeOut) { return 0; }\n"
            "    public int available() { return 0; }\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    lot = ParkingLot(2, 1)\n"
            "    print(lot.park('sedan', 'A', 0))\n"
            "    print(lot.leave('A', 3))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"ops": ["ParkingLot", "park", "park", "park", "leave", "available"],
                    "args": [[2, 1], ["sedan", "A", 0], ["truck", "B", 0], ["truck", "C", 0],
                             ["A", 3], []]},
         "expected": [None, "C0", "S0", None, 6, 2],
         "description": "Park 3 vehicles, third truck rejected, leave one", "tags": ["basic"]},
        {"input": {"ops": ["ParkingLot", "park", "park", "park", "park"],
                    "args": [[1, 1], ["sedan", "A", 0], ["sedan", "B", 0],
                             ["truck", "T", 0], ["truck", "T2", 0]]},
         "expected": [None, "C0", "S0", None, None],
         "description": "Compact + standard fill (sedans fall back to standard); trucks then rejected",
         "tags": ["edge"]},
        {"input": {"ops": ["ParkingLot", "park", "leave", "leave"],
                    "args": [[1, 0], ["bike", "B", 0], ["B", 1], ["B", 2]]},
         "expected": [None, "C0", 2, None],
         "description": "Leave with no record returns None", "tags": ["edge"]},
        {"input": {"ops": ["ParkingLot", "available"], "args": [[3, 2], []]},
         "expected": [None, 5],
         "description": "Brand-new lot — all spots free", "tags": ["edge"]},
        {"input": {"ops": ["ParkingLot", "park", "leave"],
                    "args": [[1, 1], ["sedan", "A", 5], ["A", 5]]},
         "expected": [None, "C0", 0],
         "description": "Same-second leave — 0-hour stay", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Strategy + Mediator (Optimal)",
            "time_complexity": "O(1) park / leave with per-pool free queue",
            "space_complexity": "O(N) where N = total spots",
            "description": (
                "Two free queues: one per spot type. `park` picks the smallest type that accepts the "
                "vehicle. `leave` looks up plate → assigned spot, computes fee via the rate strategy, frees "
                "the spot. Mediator pattern keeps allocation logic out of `Vehicle` and `Spot`."
            ),
            "code": {
                "python": (
                    "from collections import deque\n"
                    "import math\n\n"
                    "class ParkingLot:\n"
                    "    def __init__(self, compact, standard):\n"
                    "        self._compact = deque(f'C{i}' for i in range(compact))\n"
                    "        self._standard = deque(f'S{i}' for i in range(standard))\n"
                    "        self._occupied = {}  # plate -> (spot_id, time_in)\n"
                    "    def park(self, vehicle_type, plate, time_in):\n"
                    "        if vehicle_type in ('sedan', 'bike') and self._compact:\n"
                    "            spot = self._compact.popleft()\n"
                    "        elif vehicle_type in ('sedan', 'bike') and self._standard:\n"
                    "            spot = self._standard.popleft()\n"
                    "        elif vehicle_type == 'truck' and self._standard:\n"
                    "            spot = self._standard.popleft()\n"
                    "        else:\n"
                    "            return None\n"
                    "        self._occupied[plate] = (spot, time_in)\n"
                    "        return spot\n"
                    "    def leave(self, plate, time_out):\n"
                    "        if plate not in self._occupied:\n"
                    "            return None\n"
                    "        spot, time_in = self._occupied.pop(plate)\n"
                    "        if spot.startswith('C'):\n"
                    "            self._compact.appendleft(spot)\n"
                    "        else:\n"
                    "            self._standard.appendleft(spot)\n"
                    "        hours = max(0, math.ceil(time_out - time_in))\n"
                    "        return hours * 2\n"
                    "    def available(self):\n"
                    "        return len(self._compact) + len(self._standard)"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Domain objects: Vehicle (sedan/bike/truck), Spot (compact/standard), ParkingLot (mediator).",
        "2. Compact accepts sedans + bikes; standard accepts everything. Encode the fits-in relation explicitly.",
        "3. Park policy: prefer the smallest spot that fits — leave bigger spots for vehicles that need them.",
        "4. Free queues per spot type → O(1) allocation.",
        "5. Plate → (spot, time_in) map for `leave`.",
        "6. Pricing as a strategy — `HourlyRate` here, but one swap-in away from EarlyBird, weekly, surge.",
        "7. Edge cases: full of one type but not the other, leave on unknown plate, zero-hour stay, exactly-fits constraint.",
    ],
    "tips": [
        "Don't let `Vehicle` know about `Spot` or `ParkingLot`. Push everything that needs to know both into a mediator.",
        "If you find yourself writing `if vehicle.type == 'truck'` in 5 places, you've missed the polymorphism — `vehicle.fits(spot)` instead.",
        "Pricing as a strategy is the bar-raising signal. One concrete strategy now, two more in the follow-up.",
        "Common follow-up: 'multiple lots.' Lot is a top-level entity; pricing strategy and spot pools per lot.",
        "Common follow-up: 'lot full sign with internet connection.' Read-mostly endpoint that returns `available()` — easy if your design didn't bury that count.",
        "Common follow-up: 'reports.' Log every park/leave; aggregate offline. Keep logging out of the hot path.",
    ],
    "companies": ["Amazon", "Microsoft", "Apple"],
    "topics": ["Object-Oriented Design", "Strategy Pattern", "Mediator Pattern"],
    "time_complexity": "O(1) per op",
    "space_complexity": "O(N)",
}


def REFERENCE(input):
    from collections import deque
    import math

    class ParkingLot:
        def __init__(self, compact, standard):
            self._compact = deque(f"C{i}" for i in range(compact))
            self._standard = deque(f"S{i}" for i in range(standard))
            self._occupied = {}

        def park(self, vehicle_type, plate, time_in):
            spot = None
            if vehicle_type in ("sedan", "bike"):
                if self._compact:
                    spot = self._compact.popleft()
                elif self._standard:
                    spot = self._standard.popleft()
            elif vehicle_type == "truck":
                if self._standard:
                    spot = self._standard.popleft()
            if spot is None:
                return None
            self._occupied[plate] = (spot, time_in)
            return spot

        def leave(self, plate, time_out):
            if plate not in self._occupied:
                return None
            spot, time_in = self._occupied.pop(plate)
            if spot.startswith("C"):
                self._compact.appendleft(spot)
            else:
                self._standard.appendleft(spot)
            hours = max(0, math.ceil(time_out - time_in))
            return hours * 2

        def available(self):
            return len(self._compact) + len(self._standard)

    ops = input["ops"]
    args = input["args"]
    instance = None
    results = []
    for op, a in zip(ops, args):
        if op == "ParkingLot":
            instance = ParkingLot(*a)
            results.append(None)
        else:
            method = getattr(instance, op)
            results.append(method(*a))
    return results


PAYLOAD["entry"] = {
    "kind": "class_ops",
    "class": "ParkingLot",
    "constructor": {"params": [{"name": "compact", "type": "int"},
                                {"name": "standard", "type": "int"}]},
    "methods": [
        {"name": "park", "params": [{"name": "vehicle_type", "type": "string"},
                                     {"name": "plate", "type": "string"},
                                     {"name": "time_in", "type": "int"}],
         "returns": "any"},
        {"name": "leave", "params": [{"name": "plate", "type": "string"},
                                      {"name": "time_out", "type": "int"}],
         "returns": "any"},
        {"name": "available", "params": [], "returns": "int"},
    ],
}


register(PAYLOAD, REFERENCE)
