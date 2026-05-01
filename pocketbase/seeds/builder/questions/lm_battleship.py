"""Battleship Game — Medium. Logical & Maintainable / OOD.

Model and simulate a Battleship board. Place ships, shoot, detect hits
and sinks. The L&M signal is the abstraction: Ship as first-class
object with cells and a hit count, Board as a grid that knows nothing
about Ship internals beyond the lookup."""
from builder.registry import register


PAYLOAD = {
    "title": "Battleship Game Model",
    "difficulty": "Medium",
    "description": (
        "Model a single-player Battleship game. The board is a 10x10 grid. Ships occupy contiguous cells "
        "either horizontally or vertically. Required operations:\n"
        "- `place_ship(ship_id, length, x, y, direction)` — place a ship of `length` starting at `(x, y)` "
        "going `'H'` (horizontal +x) or `'V'` (vertical +y). Returns True if placed, False on conflict or "
        "out of bounds.\n"
        "- `shoot(x, y)` — returns one of `'miss'`, `'hit'`, `'sink'` (when this shot was the final one "
        "for some ship), or `'win'` (when this shot sank the last remaining ship).\n"
        "- `remaining_ships()` — count of ships not yet sunk.\n\n"
        "**Test framing:** the harness drives a sequence of operations against a 10x10 board and inspects "
        "every return value."
    ),
    "hints": [
        "Don't store 'has a ship' as a plain bool grid — store the ship reference (or id) at each cell. Then a hit can update the relevant ship's hit count.",
        "Ship has: id, length, hits (count), cells (list of coordinates). Sunk iff hits == length.",
        "Placement: validate bounds first, then check no overlap with existing occupancy.",
        "shoot: lookup ship at (x, y); if none, miss. If any, increment hits, mark cell as hit (so repeated shots don't double-count). If hits == length, sink. If all ships sunk, win.",
        "Edge cases: ship out of bounds, overlap, double-shoot same cell, shoot empty cell, win on the last shot.",
    ],
    "constraints": [
        "Board is 10x10",
        "1 <= total operations <= 10⁴",
    ],
    "starter_code": {
        "python": (
            "class Battleship:\n"
            "    def __init__(self): pass\n"
            "    def place_ship(self, ship_id, length, x, y, direction): pass\n"
            "    def shoot(self, x, y): pass\n"
            "    def remaining_ships(self): pass"
        ),
        "javascript": (
            "class Battleship {\n"
            "    constructor() {}\n"
            "    placeShip(id, length, x, y, dir) {}\n"
            "    shoot(x, y) {}\n"
            "    remainingShips() {}\n"
            "}"
        ),
        "java": (
            "class Battleship {\n"
            "    public Battleship() {}\n"
            "    public boolean placeShip(int id, int length, int x, int y, String dir) { return false; }\n"
            "    public String shoot(int x, int y) { return \"miss\"; }\n"
            "    public int remainingShips() { return 0; }\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    g = Battleship()\n"
            "    g.place_ship(1, 3, 0, 0, 'H')\n"
            "    print(g.shoot(0, 0))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"ops": ["Battleship", "place_ship", "shoot", "shoot", "shoot"],
                    "args": [[], [1, 3, 0, 0, "H"], [0, 0], [1, 0], [2, 0]]},
         "expected": [None, True, "hit", "hit", "win"],
         "description": "Place a 3-cell ship and sink it (only ship → win)", "tags": ["basic"]},
        {"input": {"ops": ["Battleship", "place_ship", "shoot"],
                    "args": [[], [1, 2, 0, 0, "H"], [5, 5]]},
         "expected": [None, True, "miss"],
         "description": "Miss", "tags": ["basic"]},
        {"input": {"ops": ["Battleship", "place_ship", "place_ship", "shoot", "shoot", "shoot", "shoot"],
                    "args": [[], [1, 1, 0, 0, "H"], [2, 2, 5, 5, "H"],
                             [0, 0], [5, 5], [6, 5], [9, 9]]},
         "expected": [None, True, True, "sink", "hit", "win", "miss"],
         "description": "Sink 1-cell ship; hit then win on 2-cell ship; then miss",
         "tags": ["basic"]},
        {"input": {"ops": ["Battleship", "place_ship", "place_ship"],
                    "args": [[], [1, 3, 0, 0, "H"], [2, 2, 1, 0, "H"]]},
         "expected": [None, True, False],
         "description": "Overlap — second placement rejected", "tags": ["edge"]},
        {"input": {"ops": ["Battleship", "place_ship", "place_ship"],
                    "args": [[], [1, 3, 8, 0, "H"], [2, 1, 0, 0, "V"]]},
         "expected": [None, False, True],
         "description": "Out of bounds — first rejected; second valid",
         "tags": ["edge"]},
        {"input": {"ops": ["Battleship", "place_ship", "shoot", "shoot"],
                    "args": [[], [1, 1, 3, 3, "H"], [3, 3], [3, 3]]},
         "expected": [None, True, "win", "miss"],
         "description": "Re-shoot same sunk cell registers as miss", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Cell → Ship Reference (Optimal)",
            "time_complexity": "O(L) place / O(1) shoot",
            "space_complexity": "O(B²) board + O(N) ships",
            "description": (
                "10x10 grid stores `None` or a Ship reference. Ship knows its length, hits, and cells. "
                "Shoot: dereference the cell, increment the ship's hit count, mark the cell as hit (None) "
                "to prevent double-count. Sink/win is derivable from per-ship hits and the ships-remaining "
                "count."
            ),
            "code": {
                "python": (
                    "class _Ship:\n"
                    "    def __init__(self, sid, length):\n"
                    "        self.id = sid; self.length = length; self.hits = 0\n"
                    "    def is_sunk(self):\n"
                    "        return self.hits >= self.length\n\n"
                    "class Battleship:\n"
                    "    SIZE = 10\n"
                    "    def __init__(self):\n"
                    "        self._grid = [[None] * self.SIZE for _ in range(self.SIZE)]\n"
                    "        self._ships = {}\n"
                    "        self._afloat = 0\n"
                    "    def place_ship(self, ship_id, length, x, y, direction):\n"
                    "        cells = []\n"
                    "        for i in range(length):\n"
                    "            cx = x + (i if direction == 'H' else 0)\n"
                    "            cy = y + (i if direction == 'V' else 0)\n"
                    "            if not (0 <= cx < self.SIZE and 0 <= cy < self.SIZE):\n"
                    "                return False\n"
                    "            if self._grid[cy][cx] is not None:\n"
                    "                return False\n"
                    "            cells.append((cx, cy))\n"
                    "        ship = _Ship(ship_id, length)\n"
                    "        self._ships[ship_id] = ship\n"
                    "        for cx, cy in cells:\n"
                    "            self._grid[cy][cx] = ship\n"
                    "        self._afloat += 1\n"
                    "        return True\n"
                    "    def shoot(self, x, y):\n"
                    "        if not (0 <= x < self.SIZE and 0 <= y < self.SIZE):\n"
                    "            return 'miss'\n"
                    "        ship = self._grid[y][x]\n"
                    "        if ship is None:\n"
                    "            return 'miss'\n"
                    "        self._grid[y][x] = None\n"
                    "        ship.hits += 1\n"
                    "        if ship.is_sunk():\n"
                    "            self._afloat -= 1\n"
                    "            if self._afloat == 0:\n"
                    "                return 'win'\n"
                    "            return 'sink'\n"
                    "        return 'hit'\n"
                    "    def remaining_ships(self):\n"
                    "        return self._afloat"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Domain objects: Ship (id, length, hits) and Board (cell → ship-or-null).",
        "2. Place: validate bounds and overlap; install Ship references in cells.",
        "3. Shoot: lookup, increment hits, clear the cell so re-shoots register as miss.",
        "4. Sink detection: hits == length. Win: afloat counter hits zero.",
        "5. Edge cases: out-of-bounds placement / shot, overlap, re-shoot same cell, win on the final ship.",
        "6. Bar-raise: refactor 'is sunk' into Ship; refactor 'is winning' into Board. Don't entangle.",
    ],
    "tips": [
        "Storing the ship reference (not just a bool) at each cell is what makes hit attribution O(1).",
        "Don't recompute 'all sunk?' by scanning all ships every shot — maintain a counter.",
        "Common follow-up: 'two players.' Two boards, alternate shoot. Hide each player's board from the other.",
        "Common follow-up: 'add diagonal ships.' Generalise the placement direction; cells loop is unchanged.",
        "Common follow-up: 'random placement.' Pick a random ship-fitting (x, y, direction) and retry on conflict; cap retries to avoid livelock.",
    ],
    "companies": ["Amazon", "Microsoft", "Apple"],
    "topics": ["Object-Oriented Design", "Grid", "Simulation"],
    "time_complexity": "O(1) per shot",
    "space_complexity": "O(B²)",
}


def REFERENCE(input):
    class _Ship:
        def __init__(self, sid, length):
            self.id = sid
            self.length = length
            self.hits = 0

        def is_sunk(self):
            return self.hits >= self.length

    class Battleship:
        SIZE = 10

        def __init__(self):
            self._grid = [[None] * self.SIZE for _ in range(self.SIZE)]
            self._ships = {}
            self._afloat = 0

        def place_ship(self, ship_id, length, x, y, direction):
            cells = []
            for i in range(length):
                cx = x + (i if direction == "H" else 0)
                cy = y + (i if direction == "V" else 0)
                if not (0 <= cx < self.SIZE and 0 <= cy < self.SIZE):
                    return False
                if self._grid[cy][cx] is not None:
                    return False
                cells.append((cx, cy))
            ship = _Ship(ship_id, length)
            self._ships[ship_id] = ship
            for cx, cy in cells:
                self._grid[cy][cx] = ship
            self._afloat += 1
            return True

        def shoot(self, x, y):
            if not (0 <= x < self.SIZE and 0 <= y < self.SIZE):
                return "miss"
            ship = self._grid[y][x]
            if ship is None:
                return "miss"
            self._grid[y][x] = None
            ship.hits += 1
            if ship.is_sunk():
                self._afloat -= 1
                if self._afloat == 0:
                    return "win"
                return "sink"
            return "hit"

        def remaining_ships(self):
            return self._afloat

    ops = input["ops"]
    args = input["args"]
    instance = None
    results = []
    for op, a in zip(ops, args):
        if op == "Battleship":
            instance = Battleship()
            results.append(None)
        else:
            method = getattr(instance, op)
            results.append(method(*a))
    return results


PAYLOAD["entry"] = {
    "kind": "class_ops",
    "class": "Battleship",
    "constructor": {"params": []},
    "methods": [
        {"name": "place_ship", "params": [
            {"name": "ship_id", "type": "int"},
            {"name": "length", "type": "int"},
            {"name": "x", "type": "int"},
            {"name": "y", "type": "int"},
            {"name": "direction", "type": "string"},
        ], "returns": "bool"},
        {"name": "shoot", "params": [
            {"name": "x", "type": "int"},
            {"name": "y", "type": "int"},
        ], "returns": "string"},
        {"name": "remaining_ships", "params": [], "returns": "int"},
    ],
}


register(PAYLOAD, REFERENCE)
