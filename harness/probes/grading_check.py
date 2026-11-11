"""Harness checks for grading jobs (ROUNDS-00A-L03 PR 3): grade and
take-home submit as durable jobs whose graded row the server writes, with
both runner replicas and nginx built from this commit on the real
PocketBase, at ``ROUNDS_GATE_EXECUTION_STORE=on``,
``ROUNDS_GATE_EXECUTION_GRADING=on``, and
``ROUNDS_GATE_EXECUTION_DEFINITIONS=enforce``. Every account is generated
for the run.

Phase ``execution-grading``, through nginx:

- each replica's saved gates line holds the three values;
- a grade of ``hallucinated-http-client`` answers 202 with its job, which
  ends with an authoritative envelope, and the graded row PocketBase wrote
  and that envelope name each other, for the account and the round, with
  no review yet;
- a duplicate answers the same job and charges nothing more;
- another account asking for that result's review gets the same 404 as an
  unknown id and is charged nothing (a receipt, the case table's evidence
  for ``runner:execution-review``);
- the owner's review with no AI provider set up says so, and charges and
  marks nothing.

Prints one PASS/FAIL line per check and exits non-zero on any failure.
"""
from __future__ import annotations

import time
from typing import Any

import verify_deployment as vd
from admission_check import Checks, call, usage, uuid7
from admission_deploy import gates_log, verifier_receipts
from pbclient import PBClient
from receipts import Receipt, ReceiptWriter
from scratch_check import ANSWER_KEYS, FRONTEND, POCKETBASE_URL, accounts, sans_id, settle, submit

GATES = {"EXECUTION_STORE": "on", "EXECUTION_GRADING": "on", "EXECUTION_DEFINITIONS": "enforce"}
GRADE = {"track": "ai-coding", "slug": "hallucinated-http-client", "variant": "python", "version": 1}
REVIEW = "/api/ai-coding/grade/{}/review"
REVIEW_KEYS = {"job_id", "rubric_state", "rubric_review", "unavailable"}
# The round's fixed client: it calls the users API the hidden harness
# serves, as the round asks.
FIXED_CLIENT = (
    "import httpx\n\nINTERNAL_BASE_URL = 'http://internal-users.local'\n\n\n"
    "def fetch_user(user_id: str) -> dict:\n"
    "    res = httpx.get(f'{INTERNAL_BASE_URL}/users/{user_id}', timeout=5.0)\n"
    "    res.raise_for_status()\n"
    "    return res.json()\n"
)
FILES = {"client.py": FIXED_CLIENT}
EARNED = ("passed", "candidate-failure")


def grade_body() -> dict[str, Any]:
    return {"definition": GRADE, "files": FILES, "ai_chats": []}


def review(token: str, job_id: str, files: dict[str, str]) -> tuple[int, Any, int]:
    started = time.monotonic()
    status, parsed, _ = call(FRONTEND, "POST", REVIEW.format(job_id), token, {"files": files},
                             {"Idempotency-Key": uuid7()}, timeout=90)
    return status, parsed, int((time.monotonic() - started) * 1000)


def charged(token: str) -> tuple[int, int]:
    used = usage(token)
    return used["requests"], used["wall_seconds"]


def first(resp: Any) -> dict:
    items = (resp.body or {}).get("items") if resp.status == 200 and isinstance(resp.body, dict) else None
    return items[0] if items else {}


def run_grading(c: Checks, writer: ReceiptWriter) -> None:
    for service in ("runner", "runner-b"):
        results = vd.check_gates_log(gates_log("execution-grading", service), dict(GATES),
                                     source=f"{service} gates line")
        verifier_receipts(writer, results, service)
        c.check(f"execution.grading.gates.{service}", all(r.passed for r in results),
                "; ".join(r.detail for r in results if not r.passed))
    pb = PBClient(POCKETBASE_URL)
    pb.wait_healthy()
    a, b = accounts(pb, writer, "grd-a", "grd-b")

    # A grade is a job that ends authoritative, with the row the server
    # wrote.
    key = uuid7()
    status, answer = submit(a.token, "/api/ai-coding/grade", key, grade_body())
    shaped = status == 202 and isinstance(answer, dict) and set(answer) == ANSWER_KEYS
    c.check("execution.grading.grade.accepted-as-a-job", shaped, f"status={status}")
    if not shaped:
        return
    job_id = answer["job_id"]
    done = settle(a.token, job_id, 150)
    env = done.get("envelope") or {}
    c.check("execution.grading.grade.ends-authoritative",
            done.get("state") == "completed" and done.get("outcome_class") in EARNED
            and env.get("authoritative") is True and env.get("output") is None,
            f"{done.get('state')}/{done.get('outcome_class')}")

    # The account reads its envelope and the graded row it names, and the
    # two name each other.
    envelope = first(pb.listing("execution_envelopes", a.token, {"filter": f"job = '{job_id}'"}))
    row_id = envelope.get("graded_row") or ""
    row_resp = pb.view("ai_coding_attempts", row_id or "x" * 15, a.token)
    row = row_resp.body if row_resp.status == 200 and isinstance(row_resp.body, dict) else {}
    graded_round = first(pb.listing("ai_coding_rounds", a.token, {"filter": f"slug = '{GRADE['slug']}'"}))
    results = row.get("test_results") or []
    c.check("execution.grading.grade.row-and-envelope-name-each-other",
            envelope.get("graded_collection") == "ai_coding_attempts" and bool(row_id)
            and row.get("envelope") == envelope.get("id") and row.get("user") == a.user_id
            and row.get("round") == graded_round.get("id") and row.get("status") == "graded"
            and row.get("rubric_review") in (None, "") and len(results) == 1
            and results[0].get("outcome_class") == done.get("outcome_class"),
            f"envelope={bool(envelope)} row={row_resp.status}")

    # The same request again: the same job, and no second charge.
    before = charged(a.token)
    status, again = submit(a.token, "/api/ai-coding/grade", key, grade_body())
    c.check("execution.grading.duplicate.same-job-uncharged",
            status == 202 and (again or {}).get("job_id") == job_id and charged(a.token) == before,
            f"status={status}")

    # Another account asking for that result's review is the unknown id's
    # 404, and pays nothing.
    unknown = "zzzzzzzzzzzzzzz"
    b_before = charged(b.token)
    foreign = review(b.token, job_id, FILES)
    missing = review(b.token, unknown, FILES)
    same = foreign[0] == 404 and sans_id(foreign[1]) == sans_id(missing[1]) \
        and (foreign[1] or {}).get("code") == "not_found" and charged(b.token) == b_before
    writer.write(Receipt("isolation.execution-review.foreign", REVIEW.format("{job_id}"), "review",
                         "authenticated-other", 404, foreign[0], same, foreign[2],
                         "" if same else f"status={foreign[0]} unknown={missing[0]}"))
    c.check("isolation.execution-review.foreign", same, f"status={foreign[0]}")

    # The owner's review with no AI provider set up says so, and charges
    # and marks nothing.
    a_before = charged(a.token)
    status, body, _ = review(a.token, job_id, FILES)
    answered = isinstance(body, dict) and set(body) == REVIEW_KEYS
    after = first(pb.listing("execution_envelopes", a.token, {"filter": f"job = '{job_id}'"}))
    c.check("execution.grading.review.no-provider-charges-nothing",
            status == 200 and answered and body.get("unavailable") == "no_provider"
            and body.get("rubric_review") is None and charged(a.token) == a_before
            and ((after.get("user_view") or {}).get("rubric")) is None,
            f"status={status} unavailable={(body or {}).get('unavailable') if answered else None}")


PHASES = {
    "execution-grading": run_grading,
}


def main(phase: str, writer: ReceiptWriter) -> int:
    c = Checks()
    try:
        PHASES[phase](c, writer)
    except Exception as err:  # noqa: BLE001 - a crash is one failed check, with its type only
        c.check(f"{phase}.ran", False, type(err).__name__)
    print(f"{phase}: {c.passed} passed, {c.failed} failed")
    return 1 if c.failed else 0
