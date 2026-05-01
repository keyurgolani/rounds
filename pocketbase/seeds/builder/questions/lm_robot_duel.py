"""Robot Duel Board Game — Medium. Logical & Maintainable / OOD.

Model a 2-player turn-based game with robots that have different
abilities. Strategy/Behaviour pattern for each robot kind."""
from builder.registry import register


PAYLOAD = {
    "title": "Robot Duel Board Game",
    "difficulty": "Medium",
    "description": (
        "Two-player turn-based duel on a 10x10 grid. Each player picks a robot. First to destroy the "
        "other's robot wins. Each turn, the active player either moves their robot or attacks an adjacent "
        "(or in-range) cell.\n\n"
        "Three robot kinds:\n"
        "1. **Alpha** — can attack any of 8 surrounding squares (orthogonal + diagonal); moves 1 ortho.\n"
        "2. **Beta** — once per game, can take 2 actions in one turn; otherwise standard 1-square ortho move/attack.\n"
        "3. **Gamma** — moves or attacks up to 2 squares (still ortho).\n\n"
        "Required operations:\n"
        "- `__init__(p1_robot, p1_pos, p2_robot, p2_pos)` — set up two robots at given positions.\n"
        "- `move(player, dx, dy)` — move player's robot by (dx, dy). Validate range per robot kind. "
        "Returns True if successful.\n"
        "- `attack(player, x, y)` — attack the cell at (x, y). If it's the other robot, that player loses. "
        "Returns 'win' if it ends the game, 'hit' if it lands on the opponent (Alpha attack range), or "
        "'miss' otherwise.\n"
        "- `beta_double(player)` — Beta-only: enable 'this turn allows two actions'. Returns True if the "
        "player's robot is Beta and the ability hasn't been used.\n"
        "- `winner()` — `1`, `2`, or `0` if game is ongoing.\n\n"
        "Players alternate turns; player 1 goes first. The game enforces alternation."
    ),
    "hints": [
        "Robot is an interface with `can_move(dx, dy)` and `can_attack(target_x, target_y)` predicates. Three concrete classes: Alpha, Beta, Gamma.",
        "Don't put 'beta_used' or 'gamma_distance' on the base Robot — that pollutes every kind. Each subclass owns its own state.",
        "Game enforces turn alternation by tracking `current_player`. Each successful action advances the turn — except when Beta has activated `beta_double`.",
        "Attack range varies per robot; encapsulate in `can_attack` per kind. Don't put `if instance of Alpha` checks in the game loop.",
        "Edge cases: move out of bounds, attack out of range, attack own robot, action while game already over, Beta double used twice.",
    ],
    "constraints": [
        "Board is 10x10",
        "1 <= total operations <= 10⁴",
    ],
    "starter_code": {
        "python": (
            "class RobotDuel:\n"
            "    def __init__(self, p1_robot, p1_pos, p2_robot, p2_pos): pass\n"
            "    def move(self, player, dx, dy): pass\n"
            "    def attack(self, player, x, y): pass\n"
            "    def beta_double(self, player): pass\n"
            "    def winner(self): pass"
        ),
        "javascript": (
            "class RobotDuel {\n"
            "    constructor(p1Robot, p1Pos, p2Robot, p2Pos) {}\n"
            "    move(p, dx, dy) {}\n"
            "    attack(p, x, y) {}\n"
            "    betaDouble(p) {}\n"
            "    winner() {}\n"
            "}"
        ),
        "java": (
            "class RobotDuel {\n"
            "    public RobotDuel(String p1Robot, int[] p1Pos, String p2Robot, int[] p2Pos) {}\n"
            "    public boolean move(int p, int dx, int dy) { return false; }\n"
            "    public String attack(int p, int x, int y) { return \"miss\"; }\n"
            "    public boolean betaDouble(int p) { return false; }\n"
            "    public int winner() { return 0; }\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    g = RobotDuel('alpha', [0,0], 'gamma', [2,2])\n"
            "    print(g.attack(1, 1, 1))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"ops": ["RobotDuel", "attack", "winner"],
                    "args": [["alpha", [0, 0], "gamma", [1, 1]], [1, 1, 1], []]},
         "expected": [None, "win", 1],
         "description": "Alpha attacks diagonally and wins immediately", "tags": ["basic"]},
        {"input": {"ops": ["RobotDuel", "attack", "winner"],
                    "args": [["alpha", [0, 0], "gamma", [5, 5]], [1, 5, 5], []]},
         "expected": [None, "miss", 0],
         "description": "Alpha cannot reach far cell — miss; game continues",
         "tags": ["basic"]},
        {"input": {"ops": ["RobotDuel", "move", "move"],
                    "args": [["gamma", [0, 0], "alpha", [9, 9]], [1, 2, 0], [1, 1, 0]]},
         "expected": [None, True, False],
         "description": "Gamma can move 2; second move is out of turn (still p1's)",
         "tags": ["edge"]},
        {"input": {"ops": ["RobotDuel", "beta_double", "attack", "attack", "winner"],
                    "args": [["beta", [0, 0], "gamma", [1, 0]],
                             [1], [1, 1, 0], [1, 1, 0], []]},
         "expected": [None, True, "win", "miss", 1],
         "description": "Beta uses double to attack twice in same turn (second is a no-op since target dead)",
         "tags": ["tricky"]},
        {"input": {"ops": ["RobotDuel", "beta_double", "beta_double"],
                    "args": [["beta", [0, 0], "gamma", [5, 5]], [1], [1]]},
         "expected": [None, True, False],
         "description": "Beta-double once only", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Strategy Pattern per Robot",
            "time_complexity": "O(1) per op",
            "space_complexity": "O(1)",
            "description": (
                "Each Robot subclass encapsulates its movement and attack rules. The game loop never "
                "type-checks; it asks the Robot 'can you do X?'. Adding a new robot is one new class — no "
                "game-loop changes."
            ),
            "code": {
                "python": (
                    "class _Robot:\n"
                    "    def __init__(self, x, y):\n"
                    "        self.x, self.y = x, y; self.alive = True\n"
                    "    def can_move(self, dx, dy): raise NotImplementedError\n"
                    "    def can_attack(self, tx, ty): raise NotImplementedError\n\n"
                    "class _Alpha(_Robot):\n"
                    "    def can_move(self, dx, dy):\n"
                    "        return abs(dx) + abs(dy) == 1\n"
                    "    def can_attack(self, tx, ty):\n"
                    "        return max(abs(tx - self.x), abs(ty - self.y)) == 1\n\n"
                    "class _Beta(_Robot):\n"
                    "    def __init__(self, x, y):\n"
                    "        super().__init__(x, y); self.double_left = True\n"
                    "    def can_move(self, dx, dy):\n"
                    "        return abs(dx) + abs(dy) == 1\n"
                    "    def can_attack(self, tx, ty):\n"
                    "        return abs(tx - self.x) + abs(ty - self.y) == 1\n\n"
                    "class _Gamma(_Robot):\n"
                    "    def can_move(self, dx, dy):\n"
                    "        return (abs(dx) + abs(dy)) in (1, 2) and (dx == 0 or dy == 0)\n"
                    "    def can_attack(self, tx, ty):\n"
                    "        d = abs(tx - self.x) + abs(ty - self.y)\n"
                    "        return d in (1, 2) and (tx == self.x or ty == self.y)"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Robots vary in attack/move range — that's polymorphism, not branching. Robot interface, three subclasses.",
        "2. The game loop calls `robot.can_move(dx, dy)` / `robot.can_attack(x, y)` and never knows which kind it is.",
        "3. Beta's 'double action this turn' is its OWN state — Beta tracks `double_left` and `double_active`. Game asks `robot.is_double_pending()` to decide whether to advance the turn.",
        "4. Adding Delta (or Epsilon, etc.) is one new class plus one entry in the constructor map. No game-loop changes.",
        "5. Edge cases: out-of-bounds attack, attack while game over, Beta-double twice, action-out-of-turn.",
    ],
    "tips": [
        "If you find yourself writing `if isinstance(r, Alpha)` in the game loop, you've leaked behaviour. Push it down to the robot subclass.",
        "Beta's special ability ALMOST belongs on the base class — but it doesn't. Resist the temptation to add `double_left` to base Robot.",
        "Game-state validity: after every action, recheck winner; subsequent ops on a finished game should be no-ops or rejected.",
        "Common follow-up: 'add a 4th robot type Delta with a teleport ability.' One new subclass, one new method, zero game-loop changes — that's the L&M pass.",
        "Common follow-up: 'AI player.' Strategy pattern again — Player interface with `pick_move(state)`. Game loop doesn't care which one is human.",
    ],
    "companies": ["Amazon", "Microsoft"],
    "topics": ["Object-Oriented Design", "Strategy Pattern", "Polymorphism"],
    "time_complexity": "O(1) per op",
    "space_complexity": "O(1)",
}


def REFERENCE(input):
    class _Robot:
        def __init__(self, x, y):
            self.x, self.y = x, y
            self.alive = True

    class _Alpha(_Robot):
        kind = "alpha"

        def can_move(self, dx, dy):
            return (abs(dx) + abs(dy)) == 1

        def can_attack(self, tx, ty):
            return max(abs(tx - self.x), abs(ty - self.y)) == 1

    class _Beta(_Robot):
        kind = "beta"

        def __init__(self, x, y):
            super().__init__(x, y)
            self.double_left = True

        def can_move(self, dx, dy):
            return (abs(dx) + abs(dy)) == 1

        def can_attack(self, tx, ty):
            return (abs(tx - self.x) + abs(ty - self.y)) == 1

    class _Gamma(_Robot):
        kind = "gamma"

        def can_move(self, dx, dy):
            return (abs(dx) + abs(dy)) in (1, 2) and (dx == 0 or dy == 0)

        def can_attack(self, tx, ty):
            d = abs(tx - self.x) + abs(ty - self.y)
            return d in (1, 2) and (tx == self.x or ty == self.y)

    BUILDERS = {"alpha": _Alpha, "beta": _Beta, "gamma": _Gamma}
    SIZE = 10

    class RobotDuel:
        def __init__(self, p1_robot, p1_pos, p2_robot, p2_pos):
            self.p1 = BUILDERS[p1_robot](*p1_pos)
            self.p2 = BUILDERS[p2_robot](*p2_pos)
            self.current = 1
            self.actions_left = 1
            self._winner = 0

        def _own(self, p):
            return self.p1 if p == 1 else self.p2

        def _opp(self, p):
            return self.p2 if p == 1 else self.p1

        def move(self, player, dx, dy):
            if self._winner:
                return False
            if player != self.current:
                return False
            r = self._own(player)
            if not r.alive:
                return False
            if not r.can_move(dx, dy):
                return False
            nx, ny = r.x + dx, r.y + dy
            if not (0 <= nx < SIZE and 0 <= ny < SIZE):
                return False
            r.x, r.y = nx, ny
            self._end_action()
            return True

        def attack(self, player, x, y):
            if self._winner:
                return "miss"
            if player != self.current:
                return "miss"
            r = self._own(player)
            opp = self._opp(player)
            if not r.alive:
                return "miss"
            in_range = r.can_attack(x, y)
            if not in_range:
                self._end_action()
                return "miss"
            if opp.alive and opp.x == x and opp.y == y:
                opp.alive = False
                self._winner = player
                return "win"
            self._end_action()
            return "miss"

        def beta_double(self, player):
            if self._winner:
                return False
            r = self._own(player)
            if not isinstance(r, _Beta):
                return False
            if not r.double_left:
                return False
            r.double_left = False
            self.actions_left = 2
            return True

        def _end_action(self):
            self.actions_left -= 1
            if self.actions_left <= 0:
                self.current = 2 if self.current == 1 else 1
                self.actions_left = 1

        def winner(self):
            return self._winner

    ops = input["ops"]
    args = input["args"]
    instance = None
    results = []
    for op, a in zip(ops, args):
        if op == "RobotDuel":
            instance = RobotDuel(*a)
            results.append(None)
        else:
            method = getattr(instance, op)
            results.append(method(*a))
    return results


PAYLOAD["entry"] = {
    "kind": "class_ops",
    "class": "RobotDuel",
    "constructor": {"params": [
        {"name": "p1_robot", "type": "string"},
        {"name": "p1_pos", "type": "int[]"},
        {"name": "p2_robot", "type": "string"},
        {"name": "p2_pos", "type": "int[]"},
    ]},
    "methods": [
        {"name": "move", "params": [
            {"name": "player", "type": "int"},
            {"name": "dx", "type": "int"},
            {"name": "dy", "type": "int"},
        ], "returns": "bool"},
        {"name": "attack", "params": [
            {"name": "player", "type": "int"},
            {"name": "x", "type": "int"},
            {"name": "y", "type": "int"},
        ], "returns": "string"},
        {"name": "beta_double", "params": [
            {"name": "player", "type": "int"},
        ], "returns": "bool"},
        {"name": "winner", "params": [], "returns": "int"},
    ],
}


register(PAYLOAD, REFERENCE)
