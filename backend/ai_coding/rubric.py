"""Build the rubric-review prompt and parse the model's JSON response."""
from __future__ import annotations

import json
import re
from typing import Any


SYSTEM_PROMPT = (
    "You are grading a candidate's submission in an AI-assisted coding "
    "practice round. Score each rubric item on a 0.0-1.0 scale. Be terse "
    "but cite specific files and lines as evidence. Output ONLY a JSON "
    "object - no prose, no markdown fences. Schema:\n"
    '{ "items": [{"id": "...", "score": 0.0-1.0, "evidence": "...", "suggestions": ["..."]}], '
    '  "total": 0.0-1.0 }\n'
    "Total is the weighted sum of item scores using the rubric weights."
)


def build_prompt(
    rubric: dict[str, Any],
    files: dict[str, str],
    test_results: dict[str, Any],
    ai_chats: list[dict[str, Any]],
) -> str:
    parts = ["## Rubric items\n"]
    for it in rubric.get("items", []):
        parts.append(
            f"- id={it['id']}  weight={it.get('weight', 0)}  label={it.get('label', '')}\n"
            f"  prompt: {it.get('prompt', '')}\n"
        )
    parts.append("\n## Test results\n```json\n" + json.dumps(test_results, indent=2)[:8000] + "\n```\n")
    parts.append("\n## Files\n```json\n" + json.dumps(files)[:60_000] + "\n```\n")
    if ai_chats:
        parts.append("\n## AI chat history\n```json\n" + json.dumps(ai_chats)[:20_000] + "\n```\n")
    return "".join(parts)


_FENCE = re.compile(r"```(?:json)?\s*({.*?})\s*```", re.DOTALL)


def parse_ai_output(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if not raw:
        return {"items": [], "total": 0.0}
    # Try direct JSON first.
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Try to extract a fenced or substring JSON block.
    m = _FENCE.search(raw)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Last resort: find the outer braces.
    first = raw.find("{")
    last = raw.rfind("}")
    if first != -1 and last != -1 and last > first:
        try:
            return json.loads(raw[first:last + 1])
        except json.JSONDecodeError:
            pass
    return {"items": [], "total": 0.0, "parse_error": raw[:500]}
