# Execution and Render Runbook

Owner: [#1](https://github.com/keyurgolani/rounds/issues/1) (`ROUNDS-00A-L01`). Stage 2 adds the gates, codes, limits, and checks below. Stage 3 adds idempotency, quotas, and the repair steps for their records.

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
| `not_permitted` | 403 | 4 | The account's tier can't use this operation | Everything is permitted until stage 3 adds the demo tier's limits |
| `limit_exceeded` | 413 | 5 | A field is over its limit (Limits) | The app shows too large |
| `invalid_request` | 422 | 5, 8 | An unknown or malformed field, the request shape an older tab sends, or a stored definition this runner can't run, such as a `custom` entry | Reload the page; for a stored definition, fix the record |
| `not_found` | 404 | 8 | The question, round, checkpoint, assignment, or campaign is missing or belongs to another account | None; the caller named something it can't use |
| `worker_unavailable` | 503 | 9, or after admission | Every in-flight slot on this replica is busy, or the PDF renderer couldn't finish | The app keeps the draft; retry shortly, and check the renderer if it persists |
| `destination_denied` | 403 | provider calls | An AI provider base URL points at a refused address | Use a public provider URL, or the LAN address with `ROUNDS_GATE_PROVIDER_PRIVATE_NETWORK` |

Stage 3 raises `idempotency_key_required`, `already_completed`, `quota_exceeded`, `demo_limit_reached`, and `quota_unavailable`.

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

Each run gets a minimal environment with none of the runner's settings or secrets, a private scratch directory that is its working directory, `HOME`, and `TMPDIR`, and its input in a file. In the image the runner is root and each in-flight slot runs as its own user (uids 10001 to 10004, group 10000). `/app` stays root-owned, so candidate code can't write it. When a run ends, anything still running as that slot's user is killed and what it left in `/tmp`, `/var/tmp`, and `/dev/shm` is removed. [#5](https://github.com/keyurgolani/rounds/issues/5) replaces this with ephemeral workers that have no secrets and no network; until then candidate code shares the runner's network.

## Alerts

Proposed thresholds, from the `decision` lines:

1. `auth_unavailable` or `worker_unavailable` on more than 5% of a route's requests for 5 minutes. Stage 3 adds `quota_unavailable`.
2. Any 5xx after admission: a `decision` line with status 500 or higher and no code.

## Dependency Checks

1. PocketBase's auth-refresh answers from each runner replica at `POCKETBASE_URL`. A failure shows as `auth_unavailable` on every admitted route.
2. The renderer's health: a signed-in `GET /api/pdf/health` answers `{"status": "ok"}`, or 503 `{"status": "unavailable"}` when the runner can't reach the sidecar.
3. Stage 3 adds a read of the admission counters per replica.

## Repair

Nothing to repair in stage 2: admission keeps no records yet. Stage 3 adds the steps for expired leases and stuck command rows.
