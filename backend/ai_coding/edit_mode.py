"""Edit-mode prompt + parser. The model is asked to return ONLY a JSON
array of patches (no prose, no fences). The parser tolerates minor
deviations (a fenced block, extra prose) but never silently applies a
malformed response — callers should surface `error` to the user."""
from __future__ import annotations

import json
import re
from typing import Any


EDIT_SYSTEM_PROMPT = (
    "You are a senior pair-programmer in an interview practice round. The "
    "candidate has asked you to propose CODE CHANGES. Output ONLY a JSON "
    "array of patches — no prose, no markdown fences. Schema:\n"
    "[\n"
    '  {"file": "<path>", "patch_kind": "replace", "contents": "<full new file contents>"}\n'
    "]\n"
    "Rules:\n"
    "  - Use patch_kind=\"replace\" only — the candidate's UI does not yet support diff format.\n"
    "  - Provide minimal changes. Don't rewrite files that don't need it.\n"
    "  - Don't touch test files unless the candidate explicitly asks.\n"
    "  - If you'd rather discuss before coding, output an empty array [] and the candidate will switch to Ask mode.\n"
    "The candidate's project is given as a JSON object of {path: contents}."
)

_FENCE = re.compile(r"```(?:json)?\s*(\[.*?\])\s*```", re.DOTALL)
_VALID_KINDS = {"replace"}


def parse_patches(raw: str) -> tuple[list[dict[str, Any]], str | None]:
    """Returns (patches, error). Patches is always a list (possibly empty);
    error is None on success or a short human-readable string on failure."""
    raw = (raw or "").strip()
    if not raw:
        return [], None

    arr = _try_load_array(raw)
    if arr is None:
        m = _FENCE.search(raw)
        if m:
            arr = _try_load_array(m.group(1))
    if arr is None:
        first = raw.find("[")
        last = raw.rfind("]")
        if first != -1 and last != -1 and last > first:
            arr = _try_load_array(raw[first:last + 1])
    if arr is None:
        return [], "Couldn't parse model output as a JSON patch array."

    cleaned: list[dict[str, Any]] = []
    for it in arr:
        if not isinstance(it, dict):
            continue
        kind = it.get("patch_kind")
        if kind not in _VALID_KINDS:
            continue
        f = it.get("file")
        c = it.get("contents")
        if not isinstance(f, str) or not isinstance(c, str):
            continue
        cleaned.append({"file": f, "patch_kind": kind, "contents": c})

    if not cleaned and arr:
        # The model emitted SOMETHING that parsed as an array, but every
        # entry failed validation (wrong patch_kind, non-string fields,
        # or non-dict). That's distinct from a deliberate empty array
        # (the prompt's "switch to Ask mode" signal) — surface it so
        # callers can show a "model returned an unsupported format"
        # hint instead of silently rendering "no changes."
        return [], (
            "Model output parsed as a JSON array but no entries were valid "
            'patches (each entry needs patch_kind="replace", string file, string contents).'
        )
    return cleaned, None


def _try_load_array(text: str) -> list | None:
    try:
        v = json.loads(text)
        return v if isinstance(v, list) else None
    except json.JSONDecodeError:
        return None
