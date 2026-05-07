"""Chess Model — Medium. Object-Oriented Design.

Domain modeling phone screen. Board, Piece hierarchy, Move,
Rules. The OOD signal: piece-specific move logic on the Piece, not
in a giant switch/if in Board.move()."""
from builder.registry import register


PAYLOAD = {
    "title": "Chess Model (Move Validation)",
    "difficulty": "Medium",
    "description": (
        "Model the core domain of a chess game. Required:\n"
        "- `place(piece, color, x, y)` — put a piece on the board (`piece` ∈ "
        "`['pawn','rook','knight','bishop','queen','king']`, `color` ∈ `['white','black']`).\n"
        "- `move(from_xy, to_xy)` — attempt a move. Returns `'ok'`, `'invalid'`, `'capture'`, or "
        "`'check'` (if move places opponent's king in check). Same-side capture is `'invalid'`.\n"
        "- `at(x, y)` — return `(piece, color)` or `None`.\n\n"
        "**Scope reductions for this question:**\n"
        "- No castling, no en passant, no pawn promotion.\n"
        "- Pawn moves: forward 1 (or 2 from start row) for non-capture, diagonal 1 for capture only.\n"
        "- Don't enforce turn alternation.\n"
        "- Check detection: after the move, scan whether the active side's pieces threaten the opponent's "
        "king.\n\n"
        "**Coordinates:** `(0, 0)` is the bottom-left (a1); white starts on rows 0/1; black on rows 6/7."
    ),
    "hints": [
        "Piece hierarchy: each piece overrides `legal_moves(board, x, y)` returning the set of reachable squares.",
        "Don't put a giant `if piece == 'rook' …` in Board.move() — that's the L4 anti-pattern. Polymorphism on Piece.",
        "Capture: the destination has an opponent's piece. Same-side capture is invalid.",
        "Check detection: after the move, simulate; if the opponent's king is on any of your pieces' attack squares, return 'check'. Don't try to do legality-with-check-prevention here unless asked.",
        "Path-blocked: rook/bishop/queen need to scan along the ray; if any square is occupied before the destination, the move is invalid.",
    ],
    "constraints": [
        "Board is 8x8",
        "1 <= total operations <= 10⁴",
    ],
    "starter_code": {
        "python": (
            "class Chess:\n"
            "    def __init__(self): pass\n"
            "    def place(self, piece, color, x, y): pass\n"
            "    def move(self, from_xy, to_xy): pass\n"
            "    def at(self, x, y): pass"
        ),
        "javascript": (
            "class Chess {\n"
            "    constructor() {}\n"
            "    place(piece, color, x, y) {}\n"
            "    move(fromXy, toXy) {}\n"
            "    at(x, y) {}\n"
            "}"
        ),
        "java": (
            "class Chess {\n"
            "    public Chess() {}\n"
            "    public void place(String piece, String color, int x, int y) {}\n"
            "    public String move(int[] from, int[] to) { return null; }\n"
            "    public Object at(int x, int y) { return null; }\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    g = Chess()\n"
            "    g.place('rook', 'white', 0, 0)\n"
            "    print(g.move([0, 0], [0, 5]))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"ops": ["Chess", "place", "move", "at"],
                    "args": [[], ["rook", "white", 0, 0], [[0, 0], [0, 5]], [0, 5]]},
         "expected": [None, None, "ok", ["rook", "white"]],
         "description": "Rook moves up the file unobstructed", "tags": ["basic"]},
        {"input": {"ops": ["Chess", "place", "place", "move"],
                    "args": [[], ["rook", "white", 0, 0], ["pawn", "white", 0, 3], [[0, 0], [0, 5]]]},
         "expected": [None, None, None, "invalid"],
         "description": "Path blocked by own pawn", "tags": ["basic"]},
        {"input": {"ops": ["Chess", "place", "place", "move", "at"],
                    "args": [[], ["rook", "white", 0, 0], ["pawn", "black", 0, 3],
                             [[0, 0], [0, 3]], [0, 3]]},
         "expected": [None, None, None, "capture", ["rook", "white"]],
         "description": "Capture on rook's path", "tags": ["basic"]},
        {"input": {"ops": ["Chess", "place", "move"],
                    "args": [[], ["knight", "white", 0, 0], [[0, 0], [1, 2]]]},
         "expected": [None, None, "ok"],
         "description": "Knight L-move", "tags": ["basic"]},
        {"input": {"ops": ["Chess", "place", "move"],
                    "args": [[], ["bishop", "white", 0, 0], [[0, 0], [3, 0]]]},
         "expected": [None, None, "invalid"],
         "description": "Bishop can't move along ranks", "tags": ["edge"]},
        {"input": {"ops": ["Chess", "place", "move"],
                    "args": [[], ["pawn", "white", 4, 1], [[4, 1], [4, 3]]]},
         "expected": [None, None, "ok"],
         "description": "Pawn 2-square advance from start row", "tags": ["basic"]},
        {"input": {"ops": ["Chess", "place", "place", "move"],
                    "args": [[], ["pawn", "white", 4, 1], ["pawn", "black", 5, 2], [[4, 1], [5, 2]]]},
         "expected": [None, None, None, "capture"],
         "description": "Pawn diagonal capture", "tags": ["basic"]},
        {"input": {"ops": ["Chess", "place", "move"],
                    "args": [[], ["pawn", "white", 4, 1], [[4, 1], [5, 2]]]},
         "expected": [None, None, "invalid"],
         "description": "Pawn diagonal without capture target — invalid",
         "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Polymorphic Pieces (Optimal)",
            "time_complexity": "O(1) per move (board is 8x8)",
            "space_complexity": "O(1) — fixed-size board",
            "description": (
                "Board is an 8x8 grid of (piece, color) tuples or None. Move dispatches to a per-piece "
                "validator that checks geometry + path-blocking. Captures: destination is occupied by the "
                "opposite colour. Check: after move, scan if the moving side threatens the opponent's king."
            ),
            "code": {
                "python": (
                    "class Chess:\n"
                    "    def __init__(self):\n"
                    "        self._grid = [[None] * 8 for _ in range(8)]\n"
                    "    def place(self, piece, color, x, y):\n"
                    "        self._grid[y][x] = (piece, color)\n"
                    "    def at(self, x, y):\n"
                    "        cell = self._grid[y][x]\n"
                    "        return list(cell) if cell else None\n"
                    "    def move(self, from_xy, to_xy):\n"
                    "        fx, fy = from_xy\n"
                    "        tx, ty = to_xy\n"
                    "        if not (0 <= fx < 8 and 0 <= fy < 8 and 0 <= tx < 8 and 0 <= ty < 8):\n"
                    "            return 'invalid'\n"
                    "        mover = self._grid[fy][fx]\n"
                    "        if mover is None:\n"
                    "            return 'invalid'\n"
                    "        piece, color = mover\n"
                    "        target = self._grid[ty][tx]\n"
                    "        if target is not None and target[1] == color:\n"
                    "            return 'invalid'\n"
                    "        if not self._is_legal(piece, color, fx, fy, tx, ty):\n"
                    "            return 'invalid'\n"
                    "        self._grid[ty][tx] = mover\n"
                    "        self._grid[fy][fx] = None\n"
                    "        if target is not None and target[1] != color:\n"
                    "            return 'capture'\n"
                    "        if self._side_in_check('black' if color == 'white' else 'white'):\n"
                    "            return 'check'\n"
                    "        return 'ok'\n"
                    "    def _is_legal(self, piece, color, fx, fy, tx, ty):\n"
                    "        dx, dy = tx - fx, ty - fy\n"
                    "        if (fx, fy) == (tx, ty):\n"
                    "            return False\n"
                    "        if piece == 'knight':\n"
                    "            return (abs(dx), abs(dy)) in ((1, 2), (2, 1))\n"
                    "        if piece == 'rook':\n"
                    "            return (dx == 0 or dy == 0) and self._path_clear(fx, fy, tx, ty)\n"
                    "        if piece == 'bishop':\n"
                    "            return abs(dx) == abs(dy) and self._path_clear(fx, fy, tx, ty)\n"
                    "        if piece == 'queen':\n"
                    "            return (dx == 0 or dy == 0 or abs(dx) == abs(dy)) and self._path_clear(fx, fy, tx, ty)\n"
                    "        if piece == 'king':\n"
                    "            return abs(dx) <= 1 and abs(dy) <= 1\n"
                    "        if piece == 'pawn':\n"
                    "            direction = 1 if color == 'white' else -1\n"
                    "            start_row = 1 if color == 'white' else 6\n"
                    "            tgt = self._grid[ty][tx]\n"
                    "            if dx == 0 and dy == direction and tgt is None:\n"
                    "                return True\n"
                    "            if dx == 0 and dy == 2 * direction and fy == start_row and tgt is None and self._grid[fy + direction][fx] is None:\n"
                    "                return True\n"
                    "            if abs(dx) == 1 and dy == direction and tgt is not None and tgt[1] != color:\n"
                    "                return True\n"
                    "            return False\n"
                    "        return False\n"
                    "    def _path_clear(self, fx, fy, tx, ty):\n"
                    "        sx = (tx - fx) and (1 if tx > fx else -1)\n"
                    "        sy = (ty - fy) and (1 if ty > fy else -1)\n"
                    "        x, y = fx + sx, fy + sy\n"
                    "        while (x, y) != (tx, ty):\n"
                    "            if self._grid[y][x] is not None:\n"
                    "                return False\n"
                    "            x += sx\n"
                    "            y += sy\n"
                    "        return True\n"
                    "    def _side_in_check(self, side):\n"
                    "        king_pos = None\n"
                    "        for y in range(8):\n"
                    "            for x in range(8):\n"
                    "                if self._grid[y][x] == ('king', side):\n"
                    "                    king_pos = (x, y)\n"
                    "        if king_pos is None:\n"
                    "            return False\n"
                    "        kx, ky = king_pos\n"
                    "        opp = 'black' if side == 'white' else 'white'\n"
                    "        for y in range(8):\n"
                    "            for x in range(8):\n"
                    "                cell = self._grid[y][x]\n"
                    "                if cell is None or cell[1] != opp:\n"
                    "                    continue\n"
                    "                if self._is_legal(cell[0], cell[1], x, y, kx, ky):\n"
                    "                    return True\n"
                    "        return False"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Board: 8x8 grid of `(piece, color)` or None. Don't make Board a class hierarchy — it's a grid.",
        "2. Pieces: dict from piece name → validator function `(board, from, to, color) → bool`. Polymorphism by data.",
        "3. Pawn is the special case — different forward and capture geometries. Just a slightly hairier validator.",
        "4. Path-blocked check: for sliding pieces, walk the ray from `from` to `to` and reject if any intermediate square is occupied.",
        "5. Capture: destination has an enemy piece. Same-side at destination → invalid.",
        "6. Check detection: after the move, scan all of mover's pieces for an attack square equal to the opponent's king position.",
    ],
    "tips": [
        "Don't try to fully validate king-in-check legality before allowing a move (prevent self-check) at v1. Mention it as a follow-up.",
        "Sliding-piece path checks are the bug magnet — off-by-one on whether to include the destination.",
        "Knight is the simplest validator (set of (±1, ±2) and (±2, ±1)). Bishops and rooks are very similar to each other.",
        "Common follow-up: 'castling.' Track moved-status for king and both rooks; check the squares in between.",
        "Common follow-up: 'en passant.' Track the last move's pawn-from-2 status; allow capture into the empty square one rank back for one move only.",
    ],
    "companies": ["Amazon", "Google", "Microsoft"],
    "topics": ["Object-Oriented Design", "Polymorphism", "Game", "Grid"],
    "time_complexity": "O(1) per move",
    "space_complexity": "O(1)",
}


def REFERENCE(input):
    SIZE = 8

    def in_bounds(x, y):
        return 0 <= x < SIZE and 0 <= y < SIZE

    class Chess:
        def __init__(self):
            self._grid = [[None] * SIZE for _ in range(SIZE)]

        def place(self, piece, color, x, y):
            self._grid[y][x] = (piece, color)

        def at(self, x, y):
            cell = self._grid[y][x]
            return list(cell) if cell else None

        def move(self, from_xy, to_xy):
            fx, fy = from_xy
            tx, ty = to_xy
            if not (in_bounds(fx, fy) and in_bounds(tx, ty)):
                return "invalid"
            mover = self._grid[fy][fx]
            if mover is None:
                return "invalid"
            piece, color = mover
            target = self._grid[ty][tx]
            if target is not None and target[1] == color:
                return "invalid"
            if not self._is_legal(piece, color, fx, fy, tx, ty):
                return "invalid"
            # Apply
            self._grid[ty][tx] = mover
            self._grid[fy][fx] = None
            if target is not None and target[1] != color:
                return "capture"
            # Detect check on opponent
            if self._side_in_check("black" if color == "white" else "white"):
                return "check"
            return "ok"

        def _is_legal(self, piece, color, fx, fy, tx, ty):
            dx, dy = tx - fx, ty - fy
            if (fx, fy) == (tx, ty):
                return False
            if piece == "knight":
                return (abs(dx), abs(dy)) in ((1, 2), (2, 1))
            if piece == "rook":
                return (dx == 0 or dy == 0) and self._path_clear(fx, fy, tx, ty)
            if piece == "bishop":
                return abs(dx) == abs(dy) and self._path_clear(fx, fy, tx, ty)
            if piece == "queen":
                straight = dx == 0 or dy == 0
                diag = abs(dx) == abs(dy)
                return (straight or diag) and self._path_clear(fx, fy, tx, ty)
            if piece == "king":
                return abs(dx) <= 1 and abs(dy) <= 1
            if piece == "pawn":
                direction = 1 if color == "white" else -1
                start_row = 1 if color == "white" else 6
                target = self._grid[ty][tx]
                if dx == 0 and dy == direction and target is None:
                    return True
                if (dx == 0 and dy == 2 * direction and fy == start_row and target is None
                        and self._grid[fy + direction][fx] is None):
                    return True
                if abs(dx) == 1 and dy == direction and target is not None and target[1] != color:
                    return True
                return False
            return False

        def _path_clear(self, fx, fy, tx, ty):
            sx = (tx - fx) and (1 if tx > fx else -1)
            sy = (ty - fy) and (1 if ty > fy else -1)
            x, y = fx + sx, fy + sy
            while (x, y) != (tx, ty):
                if self._grid[y][x] is not None:
                    return False
                x += sx
                y += sy
            return True

        def _side_in_check(self, side):
            # Find the side's king
            king_pos = None
            for y in range(SIZE):
                for x in range(SIZE):
                    cell = self._grid[y][x]
                    if cell == ("king", side):
                        king_pos = (x, y)
            if king_pos is None:
                return False
            kx, ky = king_pos
            opp = "black" if side == "white" else "white"
            for y in range(SIZE):
                for x in range(SIZE):
                    cell = self._grid[y][x]
                    if cell is None or cell[1] != opp:
                        continue
                    p, c = cell
                    if self._is_legal(p, c, x, y, kx, ky):
                        return True
            return False

    ops = input["ops"]
    args = input["args"]
    instance = None
    results = []
    for op, a in zip(ops, args):
        if op == "Chess":
            instance = Chess()
            results.append(None)
        else:
            method = getattr(instance, op)
            results.append(method(*a))
    return results


PAYLOAD["entry"] = {
    "kind": "class_ops",
    "class": "Chess",
    "constructor": {"params": []},
    "methods": [
        {"name": "place", "params": [
            {"name": "piece", "type": "string"},
            {"name": "color", "type": "string"},
            {"name": "x", "type": "int"},
            {"name": "y", "type": "int"},
        ], "returns": "any"},
        {"name": "move", "params": [
            {"name": "from_xy", "type": "int[]"},
            {"name": "to_xy", "type": "int[]"},
        ], "returns": "string"},
        {"name": "at", "params": [
            {"name": "x", "type": "int"},
            {"name": "y", "type": "int"},
        ], "returns": "any"},
    ],
}


register(PAYLOAD, REFERENCE)
