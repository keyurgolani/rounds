"""Deck of Cards — Easy. Object-Oriented Design.

Card, Deck, Hand. Shuffle (deterministic via seed for tests),
deal. Bar-raise: support multiple game variants without modifying
the deck."""
from builder.registry import register


PAYLOAD = {
    "title": "Deck of Cards",
    "difficulty": "Easy",
    "description": (
        "Model a standard 52-card deck. Operations:\n"
        "- `__init__(seed)` — start with a fresh deck in a canonical order, then shuffle deterministically "
        "with the given seed.\n"
        "- `deal(n)` — return the next `n` cards from the top, removing them from the deck. If fewer than "
        "`n` cards remain, return what's available.\n"
        "- `peek()` — return the card on top without removing.\n"
        "- `remaining()` — number of cards still in the deck.\n"
        "- `reset_and_shuffle(seed)` — restore to 52 cards and re-shuffle with the new seed.\n\n"
        "Cards are pairs `[rank, suit]` where rank ∈ {`'2'..'10','J','Q','K','A'`} and suit ∈ "
        "{`'C','D','H','S'`}. Pick any canonical pre-shuffle ordering you like (the spec doesn't pin one).\n\n"
        "**Test framing:** the harness validates the 52-card invariant after each operation — every "
        "dealt card is a valid `[rank, suit]` pair, deals never duplicate cards, and `remaining()` "
        "tracks the deck size. Any seed-deterministic shuffle passes."
    ),
    "hints": [
        "Use `random.Random(seed)` and `random.shuffle` (Python) — deterministic, language-built-in.",
        "Don't reach for a fancy structure for `deal` — slicing or popping from a list is fine.",
        "`peek()` shouldn't mutate; use the index-into-list operation.",
        "Bar-raise: card-game variants extend Card / Deck without modifying. e.g. War: deck is shared, hands are subsets.",
        "Edge cases: deal more than remaining, deal 0, peek on empty, reset.",
    ],
    "constraints": [
        "1 <= total operations <= 10⁴",
    ],
    "starter_code": {
        "python": (
            "class Deck:\n"
            "    def __init__(self, seed): pass\n"
            "    def deal(self, n): pass\n"
            "    def peek(self): pass\n"
            "    def remaining(self): pass\n"
            "    def reset_and_shuffle(self, seed): pass"
        ),
        "javascript": (
            "class Deck {\n"
            "    constructor(seed) {}\n"
            "    deal(n) {}\n"
            "    peek() {}\n"
            "    remaining() {}\n"
            "    resetAndShuffle(seed) {}\n"
            "}"
        ),
        "java": (
            "class Deck {\n"
            "    public Deck(long seed) {}\n"
            "    public List<int[]> deal(int n) { return new ArrayList<>(); }\n"
            "    public int[] peek() { return null; }\n"
            "    public int remaining() { return 0; }\n"
            "    public void resetAndShuffle(long seed) {}\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    d = Deck(0)\n"
            "    print(d.deal(5))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"ops": ["Deck", "remaining", "deal", "remaining", "deal", "remaining"],
                    "args": [[0], [], [3], [], [60], []]},
         "expected": [None, 52, "first_3@seed_0", 49, "rest_at_seed_0", 0],
         "description": "Sentinel — overridden below", "tags": ["edge"]},
        {"input": {"ops": ["Deck", "remaining"], "args": [[42], []]},
         "expected": [None, 52],
         "description": "Fresh deck has 52 cards", "tags": ["edge"]},
        {"input": {"ops": ["Deck", "deal", "remaining"], "args": [[42], [0], []]},
         "expected": [None, [], 52],
         "description": "Deal 0 — no-op", "tags": ["edge"]},
        {"input": {"ops": ["Deck", "deal", "deal", "remaining"],
                    "args": [[42], [40], [20], []]},
         "expected": [None, "first_40", "remaining_12", 0],
         "description": "Sentinel — overridden below", "tags": ["edge"]},
        {"input": {"ops": ["Deck", "deal", "peek", "remaining"],
                    "args": [[7], [52], [], []]},
         "expected": [None, "all_52", None, 0],
         "description": "Sentinel", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "List Backing + Seeded Shuffle (Optimal)",
            "time_complexity": "O(n) shuffle, O(1) deal/peek/remaining (amortised)",
            "space_complexity": "O(n) deck",
            "description": (
                "Build the canonical 52-card list once. `random.Random(seed).shuffle(deck)` for "
                "reproducible randomness. `deal(n)` slices from the front (or pops repeatedly from the "
                "top). `peek` is the head. `reset_and_shuffle` rebuilds and re-shuffles."
            ),
            "code": {
                "python": (
                    "import random\n\n"
                    "class Deck:\n"
                    "    RANKS = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']\n"
                    "    SUITS = ['C','D','H','S']\n"
                    "    @classmethod\n"
                    "    def _canonical(cls):\n"
                    "        return [(r, s) for s in cls.SUITS for r in cls.RANKS]\n"
                    "    def __init__(self, seed):\n"
                    "        self._cards = self._canonical()\n"
                    "        random.Random(seed).shuffle(self._cards)\n"
                    "    def deal(self, n):\n"
                    "        out = self._cards[:n]\n"
                    "        self._cards = self._cards[n:]\n"
                    "        return out\n"
                    "    def peek(self):\n"
                    "        return self._cards[0] if self._cards else None\n"
                    "    def remaining(self):\n"
                    "        return len(self._cards)\n"
                    "    def reset_and_shuffle(self, seed):\n"
                    "        self._cards = self._canonical()\n"
                    "        random.Random(seed).shuffle(self._cards)"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Card representation: a (rank, suit) tuple. Don't over-engineer Card into a class for v1.",
        "2. Canonical order: define explicitly. Tests need it deterministic.",
        "3. Shuffle with a seed-bound RNG. Don't touch the global RNG state.",
        "4. Deal: slice the front. The deck shrinks.",
        "5. Peek: head element, no mutation.",
        "6. Reset is a fresh canonical deck + re-shuffle.",
        "7. Edge cases: deal 0, deal > remaining, peek on empty, reset.",
    ],
    "tips": [
        "Don't use the global `random` — it's process-shared state that other tests can perturb. `random.Random(seed)` is the isolated form.",
        "Shuffling the canonical list with a seed gives reproducible deals — that's the property tests need.",
        "If the question asks for a Card class with methods, write it. If not, tuples are fine.",
        "Common follow-up: 'multiple decks (casino).' List of decks, deal from one, reshuffle when low.",
        "Common follow-up: 'support War / Poker / Blackjack.' Each is a Game class that consumes a Deck — Deck doesn't know about games.",
    ],
    "companies": ["Amazon", "Microsoft", "Bloomberg"],
    "topics": ["Object-Oriented Design", "Randomness", "Simulation"],
    "time_complexity": "O(n) shuffle",
    "space_complexity": "O(n)",
}


import random as _random


# Validators run inside the matcher's eval sandbox (see backend/matchers.py).
# Tests assert the 52-card invariant — never a specific shuffle permutation —
# so any canonical pre-shuffle ordering plus a seeded shuffle passes.
_RANKS_LIT = "['2','3','4','5','6','7','8','9','10','J','Q','K','A']"
_SUITS_LIT = "['C','D','H','S']"
_VALID_CARD = (
    f"(lambda c: isinstance(c, list) and len(c) == 2 "
    f"and c[0] in {_RANKS_LIT} and c[1] in {_SUITS_LIT})"
)
_VALID_DISTINCT_CARDS = (
    f"(lambda lst: isinstance(lst, list) "
    f"and all({_VALID_CARD}(c) for c in lst) "
    f"and len(set((c[0], c[1]) for c in lst)) == len(lst))"
)


def REFERENCE(input):
    class Deck:
        RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        SUITS = ["C", "D", "H", "S"]

        @classmethod
        def _canonical(cls):
            return [[r, s] for s in cls.SUITS for r in cls.RANKS]

        def __init__(self, seed):
            self._cards = self._canonical()
            _random.Random(seed).shuffle(self._cards)

        def deal(self, n):
            out = self._cards[:n]
            self._cards = self._cards[n:]
            return out

        def peek(self):
            return self._cards[0] if self._cards else None

        def remaining(self):
            return len(self._cards)

        def reset_and_shuffle(self, seed):
            self._cards = self._canonical()
            _random.Random(seed).shuffle(self._cards)

    ops = input["ops"]
    args = input["args"]
    instance = None
    results = []
    for op, a in zip(ops, args):
        if op == "Deck":
            instance = Deck(*a)
            results.append(None)
        else:
            method = getattr(instance, op)
            results.append(method(*a))
    return results


# Tests assert the 52-card invariant — that dealt cards are valid, distinct,
# and that `remaining()` tracks the deck size — not a specific shuffle order.
PAYLOAD["test_cases"] = [
    {
        "input": {"ops": ["Deck", "remaining", "deal", "remaining", "deal", "remaining"],
                  "args": [[0], [], [3], [], [60], []]},
        "expected": {
            "$match": "validator",
            "description": (
                "Deal 3, then deal more than remaining — combined deals form 52 valid distinct cards; "
                "remaining() drops correctly; over-deal returns what's left."
            ),
            "code": (
                "lambda inp, out: ("
                "isinstance(out, list) and len(out) == 6 "
                "and out[0] is None "
                "and out[1] == 52 "
                "and out[3] == 49 "
                "and out[5] == 0 "
                f"and {_VALID_DISTINCT_CARDS}(out[2]) and len(out[2]) == 3 "
                f"and {_VALID_DISTINCT_CARDS}(out[4]) and len(out[4]) == 49 "
                "and len(set((c[0], c[1]) for c in out[2] + out[4])) == 52"
                ")"
            ),
        },
        "description": "Deal 3, then deal more than remaining — preserves 52-card invariant",
        "tags": ["basic"],
    },
    {"input": {"ops": ["Deck", "remaining"], "args": [[42], []]},
     "expected": [None, 52],
     "description": "Fresh deck has 52 cards", "tags": ["edge"]},
    {"input": {"ops": ["Deck", "deal", "remaining"], "args": [[42], [0], []]},
     "expected": [None, [], 52],
     "description": "Deal 0 — no-op", "tags": ["edge"]},
    {
        "input": {"ops": ["Deck", "deal", "deal", "remaining"],
                  "args": [[42], [40], [20], []]},
        "expected": {
            "$match": "validator",
            "description": (
                "Two deals consume the deck — first 40 valid distinct cards, then the remaining 12; "
                "together they form the canonical 52."
            ),
            "code": (
                "lambda inp, out: ("
                "isinstance(out, list) and len(out) == 4 "
                "and out[0] is None "
                "and out[3] == 0 "
                f"and {_VALID_DISTINCT_CARDS}(out[1]) and len(out[1]) == 40 "
                f"and {_VALID_DISTINCT_CARDS}(out[2]) and len(out[2]) == 12 "
                "and len(set((c[0], c[1]) for c in out[1] + out[2])) == 52"
                ")"
            ),
        },
        "description": "Two deals consuming the deck", "tags": ["edge"],
    },
    {
        "input": {"ops": ["Deck", "deal", "peek", "remaining"],
                  "args": [[7], [52], [], []]},
        "expected": {
            "$match": "validator",
            "description": (
                "Deal everything — yields the full 52 valid distinct cards; peek on empty returns None; "
                "remaining is 0."
            ),
            "code": (
                "lambda inp, out: ("
                "isinstance(out, list) and len(out) == 4 "
                "and out[0] is None "
                f"and {_VALID_DISTINCT_CARDS}(out[1]) and len(out[1]) == 52 "
                "and out[2] is None "
                "and out[3] == 0"
                ")"
            ),
        },
        "description": "Deal everything; peek empty returns None", "tags": ["edge"],
    },
]


PAYLOAD["entry"] = {
    "kind": "class_ops",
    "class": "Deck",
    "constructor": {"params": [{"name": "seed", "type": "int"}]},
    "methods": [
        {"name": "deal", "params": [{"name": "n", "type": "int"}], "returns": "any"},
        {"name": "peek", "params": [], "returns": "any"},
        {"name": "remaining", "params": [], "returns": "int"},
        {"name": "reset_and_shuffle", "params": [{"name": "seed", "type": "int"}], "returns": "any"},
    ],
}


register(PAYLOAD, REFERENCE)
