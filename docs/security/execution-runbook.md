# Execution and Render Runbook

Owner: [#1](https://github.com/keyurgolani/rounds/issues/1) (`ROUNDS-00A-L01`). Stage 2 added the gates, codes, limits, and checks below. Stage 3 added idempotency, quotas, the demo tier, and the repair steps for their records.

## Admitted Routes and Their Gates

Every admitted route runs the `admission/v1` chain in `backend/app/admission.py` before it starts any subprocess, sidecar call, or provider call. Its gate is its off switch.

| Route | Gate | Off, the app shows |
| --- | --- | --- |
| `POST /api/run` | `ROUNDS_GATE_RUN` | Coding: running code is turned off; the code stays in the editor |
| `POST /api/evaluate` | `ROUNDS_GATE_EVALUATE` | Coding: running tests is turned off |
| `POST /api/ai-coding/run-project` | `ROUNDS_GATE_AI_CODING_RUN_PROJECT` | AI-assisted coding: Run is turned off |
| `POST /api/ai-coding/grade` | `ROUNDS_GATE_AI_CODING_GRADE` | AI-assisted coding: Submit is turned off; no report opens and no attempt is saved |
| `POST /api/take-home/run` | `ROUNDS_GATE_TAKE_HOME_RUN` | Take-home: Run is turned off |
| `POST /api/take-home/submit` | `ROUNDS_GATE_TAKE_HOME_SUBMIT` | Take-home: Submit is turned off |
| `POST /api/pdf/render` | `ROUNDS_GATE_PDF_RENDER` | PDF export is turned off and offers Print |
| `GET /api/pdf/health` | `ROUNDS_GATE_PDF_HEALTH` | nothing in the app; the health check answers 503 |
| `POST /api/ai/ats-rule` | `ROUNDS_GATE_ATS_RULE` | the ATS tab shows an error in place of the rule score |

Two more gates switch outbound reach, and both start off: `ROUNDS_GATE_PAPER_FETCH` for the `paper_url` fetch in `/api/ai/improve`, and `ROUNDS_GATE_PROVIDER_PRIVATE_NETWORK` for AI provider base URLs on private addresses. See [configuration](../configuration.md#gates) before enabling either.

## Turning a Gate Off

1. Set the gate to `disabled`: in the root `.env` for compose, or in the `rounds-gates` ConfigMap (`k8s/gates.yaml`) for k8s.
2. Restart the runner. It reads its gates once, at startup. On k8s, restart every runner replica.
3. Confirm. The runner's startup log has one JSON line with `"event":"gates"`; the gate shows `"value":"disabled","source":"env"`. A request to the route answers 503 with code `route_disabled`, for every caller, because the gate is checked before the account. Each of those requests writes a `decision` line with `"code":"route_disabled"`.

A value outside the gate's list resolves to `disabled`, logs an error that names the gate, and shows `"source":"invalid"`. Fix the value and restart.

In-flight runs finish or time out. Runner logs stay as receipts.

## Turning a Gate Back On

1. Set the gate empty or to `enabled`, and restart the runner.
2. Confirm the startup line shows the gate `enabled`.
3. Run the route once from the app as a signed-in account: a coding run, a test run, an AI-coding run and submit, a take-home run and submit, a PDF export, or an ATS score. Each should answer 200 and write a `decision` line with status 200 and no code.

## Error Codes

Typed errors answer `{"detail", "code", "correlation_id"}`. `detail` is a fixed sentence that never repeats request content. The same `correlation_id` is in the `X-Correlation-Id` header and in the request's `decision` line, so a support id from the app finds the log line. The steps are admission's order.

| Code | Status | Step | Means | Next step |
| --- | --- | --- | --- | --- |
| `payload_too_large` | 413 | 1 | The body is over the route's cap, at nginx, the Ingress, or the runner | The app shows too large; trim the input |
| `route_disabled` | 503 | 2 | The route's gate is off | Turn it back on when it's safe |
| `unauthenticated` | 401 | 3 | No usable bearer, or PocketBase refused it | The app asks the person to sign in again |
| `auth_unavailable` | 503 | 3, 8 | PocketBase is down or answered 5xx while checking the account or reading a record | Check PocketBase from the runner (Dependency Checks) |
| `not_permitted` | 403 | 4 | The account's tier can't use this operation | Every tier and operation is permitted; the demo tier's limits are its quota |
| `limit_exceeded` | 413 | 5 | A field is over its limit (Limits) | The app shows too large |
| `invalid_request` | 422 | 5, 8 | An unknown or malformed field, the request shape an older tab sends, or a stored definition this runner can't run, such as a `custom` entry | Reload the page; for a stored definition, fix the record |
| `idempotency_key_required` | 400 | 6 | No `Idempotency-Key`, or one that isn't a UUIDv7, while `ENFORCE_IDEMPOTENCY` enforces | Reload the page; the app sends one key per action |
| `already_completed` | 409 | 6 | The command already completed and no response was kept: a PDF render, or a result over 256 KiB | Start the action again; it gets a new key |
| `idempotency_mismatch` | 409 | 6 | The key was used for a different request or route | Start the action again; it gets a new key |
| `already_in_flight` | 409 | 6 | The same command is still running | Wait for it; a retry once it completes gets its result |
| `quota_exceeded` | 429 | 7 | An account or deployment limit is reached for this hour, or the account's in-flight limit | The app shows limit reached and the wait from `Retry-After` |
| `demo_limit_reached` | 429 | 7 | The shared demo limit is reached | The app shows limit reached and the wait from `Retry-After` |
| `quota_unavailable` | 503 | 7 | The admission store didn't answer while a gate enforces | Check PocketBase and the admission routes (Dependency Checks) |
| `not_found` | 404 | 8 | The question, round, checkpoint, assignment, or campaign is missing or belongs to another account | None; the caller named something it can't use |
| `worker_unavailable` | 503 | 9, or after admission | Every in-flight slot on this replica is busy, or the PDF renderer couldn't finish | The app retries with the same key, keeps the draft, and shows unavailable if it persists; check the renderer |
| `destination_denied` | 403 | provider calls | An AI provider base URL points at a refused address | Use a public provider URL, or the LAN address with `ROUNDS_GATE_PROVIDER_PRIVATE_NETWORK` |

The app retries `auth_unavailable`, `quota_unavailable`, and `worker_unavailable` twice with the same key, after 1 and 3 seconds or a `Retry-After` of up to 10 seconds, before it shows unavailable.

## Idempotency and Quotas

Steps 6 and 7 run in one call to the admission store, `pocketbase/pb_hooks/admission.js`, once a route has parsed its body and before any lookup. The runner calls `POST /api/rounds/admission/admit` with the caller's bearer, and PocketBase writes the command row, the charge, and the lease in one transaction, or nothing. PocketBase runs every write transaction on its one write connection, so all runner replicas share one count. nginx answers `/api/rounds/admission/` with 404, so browsers never reach the store.

1. **Commands.** The `Idempotency-Key` is the command id. A command is keyed on the account and its id, with a SHA-256 fingerprint of the route and the parsed body. A completed command's retry gets the stored response with `Idempotent-Replayed: true` and runs nothing: no execution, no provider call, and no attempt row. A command denied at step 8 or 9 is left retryable, and one that failed after admission is left `failed_infrastructure`; a retry of either runs admission again. A command and its stored response are kept for 24 hours from its last admission. Responses over 256 KiB and rendered PDFs aren't kept, so their retries get `already_completed`.
2. **Charges.** Admission charges one request plus the most the execution can run: run 3 s, evaluate 3 s per case and 10 s per `large` case, run-project 10 s, grade 45 s per checkpoint, take-home run 60 s, take-home submit 120 s, and render 25 s. Evaluate and grade are admitted on one case or checkpoint and settle the exact charge once their definitions load, so the last request of an hour can go over by its own charge.
3. **Leases.** A lease counts the request as in flight until it ends, or until 30 seconds after its charged wall time if the runner never says it ended.
4. **Refunds.** A step 8 or 9 denial and a typed failure after admission, such as the renderer failing, refund the request's wall seconds, never the request itself. Nothing else refunds.

Proposed hourly limits, counted per UTC hour; the owner ratifies them:

| Bucket | Requests | Wall seconds | In flight |
| --- | --- | --- | --- |
| Each account | 120 | 1,800 | 2 |
| The deployment | 2,000 | no limit | 8 |
| The demo tier, shared by every demo account | 30 | 300 | 1 |
| Each runner replica | none | none | 4 (step 9) |

A request has to fit every bucket it counts in, and a demo account counts in all three. The tier is `is_demo` on the account's PocketBase record; a PocketBase hook refuses any client write to it or to the old demo flags. There's no `verified` requirement, so the deployment bucket bounds what new signups can spend. An over-limit request writes nothing, and its 429 carries `Retry-After`: the rest of the hour for requests and wall seconds, or up to 10 seconds for a full in-flight bucket.

`ROUNDS_GATE_ENFORCE_IDEMPOTENCY` and `ROUNDS_GATE_ENFORCE_QUOTA` start at `observe`: admission checks every request and denies nothing. Each `decision` line then carries `idempotency` (`new`, `retry`, `replay`, `mismatch`, `in_flight`, `missing`, `unavailable`, or `skipped`), `quota` (`charged`, `exceeded`, `demo_limit`, `refunded`, `unavailable`, or `skipped`), and `would_deny`, the code enforcing would have answered. In observe mode an over-limit request runs without a charge or a command row, and a replay runs again.

To enforce:

1. Read a few days of `decision` lines. `would_deny` should be rare and explainable, and `idempotency` should be `new` for nearly every request from a current tab.
2. Set both gates to `enforce` and restart every runner replica.
3. Confirm the startup line shows both `"value":"enforce","source":"env"`, then run a coding run twice from the app: both answer 200, and the second `decision` line shows `"idempotency":"new"` again, since each click mints a new key.

To back out, set a gate to `observe` (keep checking, deny nothing) or `off` (skip the check) and restart. Command rows, counters, and leases stay as receipts until the sweep expires them.

## Limits

Proposed values; the owner ratifies them. The 256 KiB snippet and the 200-file or 5 MiB project ceilings come from the spec.

| Route | Body cap | Field limits | Wall time |
| --- | --- | --- | --- |
| `/api/run` | 512 KiB | code 256 KiB, input 64 KiB | 3 s |
| `/api/evaluate` | 512 KiB | code 256 KiB, at most 32 selected cases | 3 s per case, 10 s for a `large` case |
| `/api/ai-coding/run-project` | 6 MiB | 200 files or 5 MiB | 10 s |
| `/api/ai-coding/grade` | 6 MiB | 200 files or 5 MiB, `ai_chats` 512 KiB | 45 s per checkpoint |
| `/api/take-home/run` | 6 MiB | 200 files or 5 MiB | 60 s |
| `/api/take-home/submit` | 6 MiB | 200 files or 5 MiB, `notes` 64 KiB, `ai_chats` 512 KiB | 120 s |
| `/api/pdf/render` | 2 MiB | none | 25 s |
| `/api/ai/ats-rule` | 1 MiB | job description 64 KiB | none |
| `/api/ai/enhance-projects` | 6 MiB | at most 25 projects | none |

nginx caps every other path at 1 MiB and the Ingress at 6 MiB. Each runner replica runs at most 4 admitted executions or renders at once.

## Candidate Processes Until #5

Each run gets a minimal environment with none of the runner's settings or secrets, a private scratch directory that is its working directory, `HOME`, and `TMPDIR`, and its input in a file. In the image the runner is root and each in-flight slot runs as its own user (uids 10001 to 10004, group 10000). `/app` stays root-owned, so candidate code can't write it. When a run ends, anything still running as that slot's user is killed and what it left in `/tmp`, `/var/tmp`, and `/dev/shm` is removed; that cleanup runs off the event loop, before the slot is free again. The runner keeps the first 4 MiB of each output stream. A `/api/run` or `/api/evaluate` result comes back in its own file in the scratch directory, read only if it's a regular file the slot's user owns and no larger than 4 MiB, so output size can't break a result. On k8s no pod mounts a service-account token. [#5](https://github.com/keyurgolani/rounds/issues/5) replaces this with ephemeral workers that have no secrets and no network; until then candidate code shares the runner's network.

## Alerts

Proposed thresholds, from the `decision` lines:

1. `auth_unavailable`, `quota_unavailable`, or `worker_unavailable` on more than 5% of a route's requests for 5 minutes. In observe mode, count `"would_deny":"quota_unavailable"` and `"quota":"unavailable"` too.
2. Any 5xx after admission: a `decision` line with status 500 or higher and no code.

## Dependency Checks

1. PocketBase's auth-refresh answers from each runner replica at `POCKETBASE_URL`. A failure shows as `auth_unavailable` on every admitted route.
2. The renderer's health: a signed-in `GET /api/pdf/health` answers `{"status": "ok"}`, or 503 `{"status": "unavailable"}` when the runner can't reach the sidecar.
3. The admission store reads its counters for each replica: from inside each runner container, `GET http://pocketbase:8090/api/rounds/admission/usage` (or the replica's `POCKETBASE_URL`) with a signed-in test account's bearer answers that account's requests, wall seconds, and in-flight count for this hour. A failure shows as `quota_unavailable`, or as `"quota":"unavailable"` in observe mode.

## Repair

A PocketBase cron job, `rounds_admission_sweep`, runs every 5 minutes. It marks each `in_flight` command without a live lease `failed_infrastructure`, so its key can run again, and deletes expired leases, commands past their 24 hours, and counters older than a day. It refunds nothing and logs one `admission_sweep` line with the number it repaired.

If the sweep isn't running, repair by hand as a superuser in the PocketBase admin UI, where `now` is the current epoch second:

1. In `admission_leases`, delete every row with `expires_at <= now`.
2. In `admission_commands`, find rows with `state = 'in_flight'` that no remaining lease points at, and set each one's `state` to `failed_infrastructure`.
3. Optionally, delete `admission_commands` rows with `expires_at <= now` and `admission_counters` rows with `hour` more than 24 below `now / 3600`.

Then find out why the sweep stopped: PocketBase's log has one `admission_sweep` line every 5 minutes while it runs.
