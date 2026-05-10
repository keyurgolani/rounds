"""Build the rubric-review prompt and parse the model's JSON response."""
from __future__ import annotations

import json
import re
from typing import Any


SYSTEM_PROMPT = (
    "You are grading a candidate's submission in an AI-assisted coding "
    "practice round. Score each rubric item on a 0.0-1.0 scale. Be terse. "
    "Cite specific lines from the candidate's submitted files as evidence "
    "via the `evidence_quotes` array — each entry has the file path, the "
    "1-indexed line number, and a short quote (≤ 200 chars) showing what "
    "you're referring to. The `evidence` field is a freeform summary "
    "(2-3 sentences). Output ONLY a JSON object - no prose, no markdown "
    "fences. Schema:\n"
    "{ \"items\": [{\n"
    "    \"id\": \"...\",\n"
    "    \"score\": 0.0-1.0,\n"
    "    \"evidence\": \"...\",\n"
    "    \"evidence_quotes\": [{\"file\": \"path/to/file\", \"line\": 42, \"quote\": \"...\"}],\n"
    "    \"suggestions\": [\"...\"]\n"
    "  }],\n"
    "  \"total\": 0.0-1.0 }\n"
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


def _normalize_evidence_quotes(items: list) -> None:
    """Mutate `items` so each has an `evidence_quotes: list` of dicts
    with str `file`, int `line`, str `quote`. Tolerates missing field
    or malformed entries; never raises."""
    for it in items:
        if not isinstance(it, dict):
            continue
        raw = it.get("evidence_quotes")
        cleaned: list[dict[str, Any]] = []
        if isinstance(raw, list):
            for q in raw:
                if not isinstance(q, dict):
                    continue
                f = q.get("file")
                ln = q.get("line")
                quote = q.get("quote")
                if not isinstance(f, str) or not isinstance(quote, str):
                    continue
                try:
                    line_i = int(ln)
                except (TypeError, ValueError):
                    continue
                cleaned.append({"file": f, "line": line_i, "quote": quote[:300]})
        it["evidence_quotes"] = cleaned


def _maybe_normalize(parsed: Any) -> Any:
    """If `parsed` is the expected shape, normalize evidence_quotes in-place."""
    if isinstance(parsed, dict) and isinstance(parsed.get("items"), list):
        _normalize_evidence_quotes(parsed["items"])
    return parsed


def parse_ai_output(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if not raw:
        return {"items": [], "total": 0.0}
    # Try direct JSON first.
    try:
        return _maybe_normalize(json.loads(raw))
    except json.JSONDecodeError:
        pass
    # Try to extract a fenced or substring JSON block.
    m = _FENCE.search(raw)
    if m:
        try:
            return _maybe_normalize(json.loads(m.group(1)))
        except json.JSONDecodeError:
            pass
    # Last resort: find the outer braces.
    first = raw.find("{")
    last = raw.rfind("}")
    if first != -1 and last != -1 and last > first:
        try:
            return _maybe_normalize(json.loads(raw[first:last + 1]))
        except json.JSONDecodeError:
            pass
    return {"items": [], "total": 0.0, "parse_error": raw[:500]}
