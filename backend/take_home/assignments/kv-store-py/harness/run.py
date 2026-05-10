"""Grading harness for kv-store-py.

Imports the candidate's `app.handle` and exercises every route. Emits
a single line of JSON on stdout matching the take-home runner's
contract:  {"criteria": [...], "score": float, "duration_ms": int}.

The harness must NOT import anything that fails on a stub starter — a
candidate who hasn't implemented anything yet should still see a
clean 0.0 score with informative `logs` per criterion."""
from __future__ import annotations

import json
import sys
import time
import traceback
from typing import Any


def _safe_call(method: str, path: str, body: dict | None = None) -> tuple[Any, str]:
    """Returns (result_or_None, error_text). Catches all exceptions."""
    try:
        from app import handle
    except Exception:
        return None, f"couldn't import app.handle: {traceback.format_exc()[:500]}"
    try:
        return handle(method, path, body), ""
    except Exception:
        return None, f"handle() raised: {traceback.format_exc()[:500]}"


def _check_set_returns_ok() -> tuple[bool, str]:
    res, err = _safe_call("POST", "/set/alpha", {"value": 1})
    if err:
        return False, err
    if not (isinstance(res, tuple) and len(res) == 2):
        return False, f"expected (status, body) tuple, got {res!r}"
    status, body = res
    if status != 200:
        return False, f"expected status 200, got {status}"
    if body != {"ok": True}:
        return False, f"expected body {{ok: True}}, got {body!r}"
    return True, "ok"


def _check_get_returns_stored_value() -> tuple[bool, str]:
    _safe_call("POST", "/set/beta", {"value": "hello"})
    res, err = _safe_call("GET", "/get/beta")
    if err:
        return False, err
    if not (isinstance(res, tuple) and len(res) == 2):
        return False, f"expected (status, body) tuple, got {res!r}"
    status, body = res
    if status != 200 or body != {"value": "hello"}:
        return False, f"expected (200, {{value: 'hello'}}), got ({status}, {body!r})"
    return True, "ok"


def _check_get_missing_404() -> tuple[bool, str]:
    res, err = _safe_call("GET", "/get/never-set")
    if err:
        return False, err
    if not (isinstance(res, tuple) and len(res) == 2):
        return False, f"expected (status, body) tuple, got {res!r}"
    status, body = res
    if status != 404:
        return False, f"expected status 404, got {status}"
    if not isinstance(body, dict) or "error" not in body:
        return False, f"expected body with 'error' key, got {body!r}"
    return True, "ok"


def _check_delete_removes() -> tuple[bool, str]:
    _safe_call("POST", "/set/gamma", {"value": 42})
    res, err = _safe_call("DELETE", "/del/gamma")
    if err:
        return False, err
    if not (isinstance(res, tuple) and len(res) == 2 and res[0] == 200):
        return False, f"DELETE expected (200, {{ok: True}}), got {res!r}"
    # Verify it's gone.
    res2, err2 = _safe_call("GET", "/get/gamma")
    if err2 or not (isinstance(res2, tuple) and res2[0] == 404):
        return False, f"after DELETE, GET should 404; got {res2!r}"
    # Idempotent — DELETE again shouldn't raise.
    res3, err3 = _safe_call("DELETE", "/del/gamma")
    if err3:
        return False, f"DELETE on missing key raised: {err3}"
    if not (isinstance(res3, tuple) and res3[0] == 200):
        return False, f"DELETE on missing key should still 200; got {res3!r}"
    return True, "ok"


def _check_list_returns_sorted_keys() -> tuple[bool, str]:
    _safe_call("POST", "/set/banana", {"value": 1})
    _safe_call("POST", "/set/apple", {"value": 2})
    _safe_call("POST", "/set/cherry", {"value": 3})
    res, err = _safe_call("GET", "/list")
    if err:
        return False, err
    if not (isinstance(res, tuple) and len(res) == 2):
        return False, f"expected (status, body) tuple, got {res!r}"
    status, body = res
    if status != 200 or not isinstance(body, dict) or "keys" not in body:
        return False, f"expected (200, {{keys: [...]}}), got ({status}, {body!r})"
    keys = body["keys"]
    # apple, banana, cherry should appear (plus alpha, beta, possibly gamma was deleted).
    expected = {"alpha", "beta", "apple", "banana", "cherry"}
    found = set(keys)
    if not expected.issubset(found):
        return False, f"missing expected keys: {expected - found}"
    if list(keys) != sorted(keys):
        return False, f"expected sorted, got {keys!r}"
    return True, "ok"


def _check_code_quality() -> tuple[bool, str]:
    """Crude objective check: source uses some form of dispatch other
    than a flat if/elif chain across all routes. We pass if EITHER:
      - a `dict` is used as a route table, OR
      - a `re` import + match is used, OR
      - the source has fewer than 8 'if ' / 'elif ' tokens combined,
        suggesting compact dispatch.
    Subjective judgment is left to the AI rubric layer."""
    try:
        with open("app.py", encoding="utf-8") as f:
            src = f.read()
    except Exception as e:
        return False, f"couldn't read app.py: {e}"
    if "import re" in src and "match" in src:
        return True, "uses regex routing"
    if "{" in src and "}" in src and ("lambda" in src or "def " in src):
        # Very loose heuristic — a dict + functions probably means a route table.
        if_count = src.count("if ") + src.count("elif ")
        if if_count < 6:
            return True, "compact dispatch (few branches)"
        return False, f"dispatch looks long ({if_count} if/elif tokens)"
    if_count = src.count("if ") + src.count("elif ")
    if if_count < 8:
        return True, "compact dispatch"
    return False, f"flat if/elif chain detected ({if_count} branches)"


CRITERIA = [
    ("set_returns_ok", 0.2, _check_set_returns_ok),
    ("get_returns_stored_value", 0.2, _check_get_returns_stored_value),
    ("get_missing_404", 0.15, _check_get_missing_404),
    ("delete_removes", 0.2, _check_delete_removes),
    ("list_returns_sorted_keys", 0.15, _check_list_returns_sorted_keys),
    ("code_quality", 0.1, _check_code_quality),
]


def main() -> None:
    sys.path.insert(0, ".")  # so `from app import handle` resolves
    started = time.monotonic()
    out_criteria: list[dict[str, Any]] = []
    score = 0.0
    for cid, weight, fn in CRITERIA:
        try:
            ok, logs = fn()
        except Exception:
            ok, logs = False, f"check raised: {traceback.format_exc()[:500]}"
        out_criteria.append({"id": cid, "passed": bool(ok), "weight": weight, "logs": logs})
        if ok:
            score += weight
    duration_ms = int((time.monotonic() - started) * 1000)
    print(json.dumps({"criteria": out_criteria, "score": round(score, 3), "duration_ms": duration_ms}))


if __name__ == "__main__":
    main()
