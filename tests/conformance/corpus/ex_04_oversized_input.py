"""EX-04: an oversized request is refused before it is read.

Guarantee (closed by ROUNDS-00A-L01, with ROUNDS-00A-L02): a body larger
than the route's byte cap answers 413 ``payload_too_large`` at the byte
step, before authentication, so an outsized payload never reaches a
parser, a lookup, or a subprocess. The contained answer is the typed 413;
a 2xx, a parser error, or a 401 (the cap not applied before auth) is a
finding.

The fixture sends a body of filler bytes just over the ``/api/run`` cap
(512 KiB). The bytes are inert filler, not an exploit.
"""
from __future__ import annotations

import json

from corpus._base import Result, contained, detected

# Just over the /api/run and /api/evaluate 512 KiB admission cap.
_CAP_BYTES = 512 * 1024
_OVERSIZE = _CAP_BYTES + 4096


def run(ctx) -> Result:
    filler = "A" * _OVERSIZE
    body = json.dumps({"question_slug": "x", "language": "python", "code": "", "input": {"pad": filler}}).encode()
    with ctx.budget.spend():
        resp = ctx.runner.request("POST", "/api/run", raw_body=body, headers={"Content-Type": "application/json"})
    evidence = {"status": str(resp.status), "sent_bytes": str(len(body))}
    code = (resp.body or {}).get("code") if isinstance(resp.body, dict) else None
    if resp.status == 413 and code == "payload_too_large":
        return contained(
            f"a {len(body)}-byte body was refused 413 payload_too_large before the body was read",
            evidence=evidence,
        )
    return detected(
        f"an oversized body was not refused at the byte cap (status {resp.status}, code {code})",
        evidence=evidence,
        canary_text=resp.text,
    )
