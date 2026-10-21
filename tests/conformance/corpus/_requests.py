"""Well-formed request bodies in the current shapes, one per admitted route.

The stack the corpus runs against enforces server-owned definitions
(ROUNDS_GATE_EXECUTION_DEFINITIONS=enforce), so each body names a
compiled definition and carries ordinary candidate input. A fixture that
checks a denial sends one of these, so the only thing that can refuse it
is the guarantee under test, never a malformed body.
"""
from __future__ import annotations

CODING = {"track": "coding", "slug": "3sum", "variant": "python", "version": 1}
AI_CODING = {"track": "ai-coding", "slug": "hallucinated-http-client", "variant": "python", "version": 1}
TAKE_HOME = {"track": "take-home", "slug": "csv-summarize-py", "variant": "python", "version": 1}

THREE_SUM = "def three_sum(nums):\n    return []\n"
CLIENT = "def fetch_user(user_id):\n    return None\n"
SUMMARIZE = "def summarize(path):\n    return {}\n"


def bodies() -> dict[tuple[str, str], dict]:
    """A fresh copy of every admitted route's well-formed body."""
    return {
        ("POST", "/api/run"): {"definition": dict(CODING), "code": THREE_SUM, "input": {"nums": []}},
        ("POST", "/api/evaluate"): {"definition": dict(CODING), "code": THREE_SUM},
        ("POST", "/api/ai-coding/run-project"): {
            "definition": dict(AI_CODING), "checkpoint": 0, "files": {"client.py": CLIENT},
        },
        ("POST", "/api/ai-coding/grade"): {
            "definition": dict(AI_CODING), "files": {"client.py": CLIENT}, "ai_chats": [],
        },
        ("POST", "/api/take-home/run"): {"definition": dict(TAKE_HOME), "files": {"summarize.py": SUMMARIZE}},
        ("POST", "/api/take-home/submit"): {
            "definition": dict(TAKE_HOME), "files": {"summarize.py": SUMMARIZE},
            "notes": "", "ai_chats": [], "duration_ms": 0,
        },
        ("POST", "/api/pdf/render"): {"html": "<p>conformance</p>", "margin_mm": 0},
    }
