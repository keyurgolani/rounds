"""Grading harness for csv-summarize-py.

Creates fixture CSVs in a tempdir, calls the candidate's summarize(),
reads the output, asserts shape + values. Emits one JSON line on
stdout matching the take-home runner contract."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import traceback
from typing import Any


def _safe_call_summarize(csv_path: str, out_path: str) -> str:
    """Returns "" on success, or the error trace string on failure."""
    try:
        from summarize import summarize
    except Exception:
        return f"couldn't import summarize: {traceback.format_exc()[:500]}"
    try:
        summarize(csv_path, out_path)
        return ""
    except Exception:
        return f"summarize raised: {traceback.format_exc()[:500]}"


def _read_json(path: str) -> dict[str, Any] | None:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _write_csv(path: str, rows: list[tuple[str, int]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("name,score\n")
        for name, score in rows:
            f.write(f"{name},{score}\n")


def _populated_run() -> dict[str, Any] | None:
    """Run summarize against a 3-row fixture and return the parsed
    output (or None on failure). Memoized in module-level state so
    multiple criteria don't re-run the candidate's code."""
    if hasattr(_populated_run, "_cache"):
        return _populated_run._cache  # type: ignore[attr-defined]
    tmp = tempfile.mkdtemp(prefix="csv-harness-")
    csv_path = os.path.join(tmp, "in.csv")
    out_path = os.path.join(tmp, "out.json")
    _write_csv(csv_path, [("Alice", 87), ("Bob", 92), ("Carol", 71)])
    err = _safe_call_summarize(csv_path, out_path)
    if err:
        _populated_run._cache = {"_error": err}  # type: ignore[attr-defined]
        return _populated_run._cache  # type: ignore[attr-defined]
    out = _read_json(out_path)
    if out is None:
        _populated_run._cache = {"_error": f"output file not valid JSON at {out_path}"}  # type: ignore[attr-defined]
    else:
        _populated_run._cache = out  # type: ignore[attr-defined]
    return _populated_run._cache  # type: ignore[attr-defined]


def _empty_run() -> dict[str, Any] | None:
    if hasattr(_empty_run, "_cache"):
        return _empty_run._cache  # type: ignore[attr-defined]
    tmp = tempfile.mkdtemp(prefix="csv-harness-empty-")
    csv_path = os.path.join(tmp, "empty.csv")
    out_path = os.path.join(tmp, "out.json")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("name,score\n")
    err = _safe_call_summarize(csv_path, out_path)
    if err:
        _empty_run._cache = {"_error": err}  # type: ignore[attr-defined]
        return _empty_run._cache  # type: ignore[attr-defined]
    out = _read_json(out_path)
    if out is None:
        _empty_run._cache = {"_error": f"output file not valid JSON at {out_path}"}  # type: ignore[attr-defined]
    else:
        _empty_run._cache = out  # type: ignore[attr-defined]
    return _empty_run._cache  # type: ignore[attr-defined]


def _check_count() -> tuple[bool, str]:
    out = _populated_run() or {}
    if "_error" in out:
        return False, out["_error"]
    if out.get("count") == 3:
        return True, "count=3"
    return False, f"expected count=3, got {out.get('count')!r}"


def _check_mean() -> tuple[bool, str]:
    out = _populated_run() or {}
    if "_error" in out:
        return False, out["_error"]
    expected = (87 + 92 + 71) / 3.0
    actual = out.get("mean_score")
    if isinstance(actual, (int, float)) and abs(actual - expected) <= 0.001:
        return True, f"mean_score={actual}"
    return False, f"expected ~{expected:.3f}, got {actual!r}"


def _check_max() -> tuple[bool, str]:
    out = _populated_run() or {}
    if "_error" in out:
        return False, out["_error"]
    mx = out.get("max")
    if isinstance(mx, dict) and mx.get("name") == "Bob" and mx.get("score") == 92:
        return True, "max=Bob/92"
    return False, f"expected max={{name:'Bob',score:92}}, got {mx!r}"


def _check_min() -> tuple[bool, str]:
    out = _populated_run() or {}
    if "_error" in out:
        return False, out["_error"]
    mn = out.get("min")
    if isinstance(mn, dict) and mn.get("name") == "Carol" and mn.get("score") == 71:
        return True, "min=Carol/71"
    return False, f"expected min={{name:'Carol',score:71}}, got {mn!r}"


def _check_empty() -> tuple[bool, str]:
    out = _empty_run() or {}
    if "_error" in out:
        return False, out["_error"]
    if out == {"count": 0}:
        return True, "empty handled"
    return False, f"expected exactly {{count:0}}, got {out!r}"


def _check_code_quality() -> tuple[bool, str]:
    """Heuristic: source imports csv (the stdlib module) and json. We
    pass if BOTH imports are present — a candidate using a manual CSV
    parser is doing extra work."""
    try:
        with open("summarize.py", encoding="utf-8") as f:
            src = f.read()
    except Exception as e:
        return False, f"couldn't read summarize.py: {e}"
    if "import csv" in src and "import json" in src:
        return True, "uses stdlib csv + json"
    missing = []
    if "import csv" not in src:
        missing.append("csv")
    if "import json" not in src:
        missing.append("json")
    return False, f"missing stdlib imports: {missing}"


CRITERIA = [
    ("count_correct", 0.15, _check_count),
    ("mean_score_correct", 0.2, _check_mean),
    ("max_correct", 0.2, _check_max),
    ("min_correct", 0.2, _check_min),
    ("empty_csv_returns_count_zero", 0.15, _check_empty),
    ("code_quality", 0.1, _check_code_quality),
]


def main() -> None:
    sys.path.insert(0, ".")  # so `from summarize import summarize` resolves
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
