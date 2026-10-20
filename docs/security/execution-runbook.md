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
3. Confirm. The runner's startup log has one JSON line with `"event":"gates"`; the gate shows `"value":"disabled","source":"env"`. A request to the route answers 503 with code `route_disabled`, for every caller, because the gate is checked before the account. Each of those requests writes a `decision` line with `"code":"route_disabled"`. The deployment verifier checks both without sending anything a route would run. For `/api/run`:

   ```sh
   docker compose -f docker-compose.prod.yml logs --no-color runner > runner.log
   python3 harness/verify_deployment.py --url https://your-domain \
     --expect-disabled /api/run \
     --gates-log runner.log --expect-gate RUN=disabled
   ```

   On k8s, save one log per runner pod (`kubectl -n rounds get pods -l app=runner`, then `kubectl -n rounds logs <pod> > <pod>.log`) and run `--gates-log` on each.

A value outside the gate's list resolves to `disabled`, logs an error that names the gate, and shows `"source":"invalid"`. Fix the value and restart.

In-flight runs finish or time out. Runner logs stay as receipts.

## Turning a Gate Back On

1. Set the gate empty or to `enabled`, and restart the runner.
2. Confirm the startup line shows the gate `enabled`: save the log again and run the verifier with `--gates-log runner.log --expect-gate RUN=enabled` (for `/api/run`), and with `--url https://your-domain --admission`, which fails while any admitted route still answers 503 instead of refusing an anonymous caller with 401.
3. Run the route once from the app as a signed-in account: a coding run, a test run, an AI-coding run and submit, a take-home run and submit, a PDF export, or an ATS score. Each should answer 200 and write a `decision` line with status 200 and no code.

The harness (`harness/run.sh`) does this whole cycle on every CI run: it restarts both runner replicas with `ROUNDS_GATE_RUN=disabled`, checks the route is refused for every caller on each and charges nothing while the other routes still admit, then clears the gate, restarts both, and checks every route refuses an anonymous caller 401 again and runs are admitted on each.

## Compiled Definitions

`ROUNDS_GATE_EXECUTION_DEFINITIONS` selects where the six execution routes (run, evaluate, grade, run-project, take-home run and submit) get what they run. It is `legacy` by default. The runner and the frontend both read it, the frontend through `runtime-config.js`, so the app's requests change shape with the runner's. Set it once, in `.env` or the `rounds-gates` ConfigMap, and restart both.

- `legacy`: each route loads its question, round, or assignment from PocketBase with the caller's token, as before #2. The compiled definitions in the image are verified at startup and served only at `enforce`.
- `enforce`: the six routes take only definition requests. `definition` names one compiled version, `{track, slug, variant, version}`, which the runner resolves to an active, checksum-verified file before anything runs, and the rest of the request is the candidate's code, files, and inputs. The entry, cases, harness, time limits, and scoring all come from that file. A field from an older request shape answers 422 `legacy_request_rejected`, naming the field, and the app asks for a reload that saves the draft first. A version that was replaced answers 409 `definition_superseded`; the app rereads the item and retries once. A submission's files can't use the harness's paths, test or package configuration, Python startup files, or a library module's name (422 `path_not_allowed`). Grades and take-home runs answer each result's outcome and the server's score, never what the harness printed. Every seeded take-home assignment is retired, so take-home answers 410 `definition_retired`, and coding compiles Python and JavaScript only, so a Java run answers 404 `definition_not_found`.
- `disabled`: the six routes answer 503 `definitions_disabled` before any lookup, and every draft is kept. Use it to stop all execution in one place without touching the per-route gates. To confirm it, name each of the six with that code:

  ```sh
  python3 harness/verify_deployment.py --url https://your-domain --admission \
    --expect-disabled /api/run=definitions_disabled \
    --expect-disabled /api/evaluate=definitions_disabled \
    --expect-disabled /api/ai-coding/run-project=definitions_disabled \
    --expect-disabled /api/ai-coding/grade=definitions_disabled \
    --expect-disabled /api/take-home/run=definitions_disabled \
    --expect-disabled /api/take-home/submit=definitions_disabled \
    --gates-log runner.log --expect-gate EXECUTION_DEFINITIONS=disabled
  ```

  After you set it back, `--admission` without those names passes again.
- An unknown value closes to `disabled` and logs an error, so a typo never opens execution.

To turn on `enforce`, set it and restart the runner and the frontend. The runner's gates line shows `"EXECUTION_DEFINITIONS":{"source":"env","value":"enforce"}`, which the verifier checks with `--gates-log runner.log --expect-gate EXECUTION_DEFINITIONS=enforce`, and the frontend's start log shows `runtime-config: ROUNDS_GATE_EXECUTION_DEFINITIONS=enforce`. `--admission` passes as before, since every route still refuses an anonymous caller before it reads the body. A tab opened before the switch gets `legacy_request_rejected` and a Reload button. To go back, set `legacy`, or leave it empty, and restart both; nothing in PocketBase changes, and drafts and attempts stay. A tab opened while it was `enforce` gets `invalid_request` until it reloads.

At startup the runner reads `backend/definitions/manifest.json` (mode 0400 in the image) and checks every shipped version's bytes against its checksum. It logs one `definitions.loaded` line with `entries` and `mismatched`; `mismatched` should be 0. A version whose file is missing or altered is the only one that fails, with `definition_integrity_mismatch`, and the rest keep serving. A manifest that's missing, isn't JSON, or isn't the manifest's shape leaves no definitions at all: the runner logs one `definition.rejected` line with `definition_integrity_mismatch` and no `definitions.loaded` line, keeps starting, and the legacy routes keep serving.

## Error Codes

Typed errors answer `{"detail", "code", "correlation_id"}`. `detail` is a fixed sentence that never repeats request content. The same `correlation_id` is in the `X-Correlation-Id` header and in the request's `decision` line, so a support id from the app finds the log line. The steps are admission's order.

| Code | Status | Step | Means | Next step |
| --- | --- | --- | --- | --- |
| `payload_too_large` | 413 | 1 | The body is over the route's cap, at nginx, the Ingress, or the runner | The app shows too large; trim the input |
| `route_disabled` | 503 | 2 | The route's gate is off | Turn it back on when it's safe |
| `definitions_disabled` | 503 | 2 | `ROUNDS_GATE_EXECUTION_DEFINITIONS` is `disabled`, so the six execution routes are off | Set it to `legacy` (or leave it unset) and restart; drafts are kept |
| `unauthenticated` | 401 | 3 | No usable bearer, or PocketBase refused it | The app asks the person to sign in again |
| `auth_unavailable` | 503 | 3, 8 | PocketBase is down or answered 5xx while checking the account or reading a record | Check PocketBase from the runner (Dependency Checks) |
| `not_permitted` | 403 | 4 | The account's tier can't use this operation | Every tier and operation is permitted; the demo tier's limits are its quota |
| `limit_exceeded` | 413 | 5 | A field is over its limit (Limits) | The app shows too large |
| `invalid_request` | 422 | 5, 8 | An unknown or malformed field, a definition request at `legacy` (a tab from an `enforce` deployment), or a stored definition this runner can't run, such as a `custom` entry | Reload the page; for a stored definition, fix the record |
| `legacy_request_rejected` | 422 | 5 | At `EXECUTION_DEFINITIONS=enforce`, a field from an older request shape or one that would choose what runs; `detail` names the field | The app asks for a reload and saves the draft first |
| `idempotency_key_required` | 400 | 6 | No `Idempotency-Key`, or one that isn't a UUIDv7, while `ENFORCE_IDEMPOTENCY` enforces | The app shows unavailable; reload the page, since the app sends one key per action |
| `already_completed` | 409 | 6 | The command already completed and no response was kept: a PDF render, or a result over 256 KiB | The app shows unavailable; the next try gets a new key |
| `idempotency_mismatch` | 409 | 6 | The key was used for a different request or route | The app shows unavailable; the next try gets a new key |
| `already_in_flight` | 409 | 6 | The same command is still running, or its end isn't recorded yet | `Retry-After`, up to 10 seconds, says when to look again; the app shows unavailable, and the next try gets a new key |
| `quota_exceeded` | 429 | 7 | An account or deployment limit is reached for this hour, or the account's in-flight limit, at admission or when evaluate or grade settle | The app shows limit reached and the wait from `Retry-After` |
| `demo_limit_reached` | 429 | 7 | The shared demo limit is reached | The app shows limit reached and the wait from `Retry-After` |
| `quota_unavailable` | 503 | 7 | The admission store didn't answer while a gate enforces, or the runner has no usable `ROUNDS_ADMISSION_SECRET` | Check PocketBase, the admission routes, and the runner key (Dependency Checks) |
| `not_found` | 404 | 8 | The question, round, checkpoint, assignment, or campaign is missing or belongs to another account | None; the caller named something it can't use |
| `definition_not_found` | 404 | definition lookup | No active definition for the request's `(track, slug, variant, version)`; the same for an unknown slug, variant, or version, a Java coding run included | None; the caller named a definition that isn't shipped (only at `EXECUTION_DEFINITIONS=enforce`) |
| `definition_superseded` | 409 | definition lookup | The named version was replaced; the error names the active version | The app rereads the item and retries once with its current version; a second refusal asks for a reload |
| `definition_retired` | 410 | definition lookup | The named definition was retired; nothing runs | None; the item is gone. Drafts stay |
| `runtime_unsupported` | 422 | definition lookup | This runner has no runtime for the named variant; the error names the variants it does have | Use a supported variant, or deploy a runner with that runtime |
| `case_unknown` | 422 | definition lookup | An evaluate named a case id, or a run-project a checkpoint, that the resolved version doesn't have | The app asks for a reload |
| `path_not_allowed` | 422 | after definition lookup | A submitted file uses a harness path, test or package configuration, a Python startup file, or a library module's name; `detail` is a fixed sentence for the kind, never the path | Rename or remove the file; drafts stay |
| `definition_integrity_mismatch` | 503 | startup and definition lookup | A shipped definition file is missing or its bytes don't match the manifest checksum | Redeploy a clean image; the alert names the version. See Alerts |
| `worker_unavailable` | 503 | 9, or after admission | Every in-flight slot on this replica is busy, or the PDF renderer was unreachable, failed, opened no page within 2 s, or didn't answer within 25 s | The app retries with the same key, keeps the draft, and shows unavailable if it persists; check the renderer |
| `render_timeout` | 422 | after admission | The renderer reported that the document didn't load or print within its budget (13 s to load, 8 s to print) | The app shows the error; simplify the document. The content decides this, so it keeps its charge and the app doesn't retry it |
| `destination_denied` | 403 | provider calls | An AI provider base URL points at a refused address | Use a public provider URL, or the LAN address with `ROUNDS_GATE_PROVIDER_PRIVATE_NETWORK` |

The app retries `auth_unavailable`, `quota_unavailable`, and `worker_unavailable` twice with the same key, after 1 and 3 seconds or a `Retry-After` of up to 10 seconds, before it shows unavailable. A retry that finds its command still running gets `already_in_flight`, which the app shows as unavailable without trying again.

## Idempotency and Quotas

Steps 6 and 7 run in one call to the admission store, `pocketbase/pb_hooks/admission.js`, once a route has parsed its body and before any lookup. The runner calls `POST /api/rounds/admission/admit` with the caller's bearer, for the account, and the runner key, `ROUNDS_ADMISSION_SECRET` in `X-Rounds-Admission-Key`, which only PocketBase and the runner hold. PocketBase writes the command row, the charge, and the lease in one transaction, or nothing. PocketBase runs every write transaction on its one write connection, so all runner replicas share one count. The write routes (`admit`, `settle`, and `finish`) need the key as well as a bearer: without it they answer 403, and 503 while PocketBase has no key set. nginx answers `/api/rounds/admission/` with 404, so browsers never reach the store.

1. **Commands.** The `Idempotency-Key` is the command id. A command is keyed on the account and its id, with a SHA-256 fingerprint of the route and the parsed body. A completed command's retry gets the stored response with `Idempotent-Replayed: true` and runs nothing: no execution, no provider call, and no attempt row. A command denied before it ran is left retryable, and one that failed after it ran is left `failed_infrastructure`; a retry of either runs admission again. A command and its stored response are kept for 24 hours from its last admission. Responses over 256 KiB and rendered PDFs aren't kept, so their retries get `already_completed`.
2. **Charges.** Admission charges one request plus the most the execution can run: run 3 s, evaluate 3 s per case and 10 s per `large` case, run-project 10 s, grade 45 s per checkpoint, take-home run 60 s, take-home submit 120 s, and render 25 s. Evaluate and grade are admitted on one case or checkpoint, for at most 32 cases of 10 s or 8 checkpoints of 45 s, and settle the exact charge once their definitions load. A lease settles once, never above what it was admitted for, and a raise has to fit the hour or the request is denied with `quota_exceeded` or `demo_limit_reached` before it runs.
3. **Leases.** The runner makes each lease's token and the store keeps only its hash, so the runner can end a lease whose admit answer it lost. A lease counts the request as in flight until the runner ends it, or until its window closes: the most the request was admitted for, plus 90 seconds for grade's and take-home submit's rubric review and attempt write, plus 30 seconds. Nothing moves the window later; a settle can only bring it closer. The rubric review stops after 60 seconds and the attempt write after 10, so both end inside it. The runner tries to record each request's end up to 3 times within 6 seconds, 1.5 seconds a try. If the store never hears, the lease stops counting when its window closes and the sweep marks the command `failed_infrastructure`. An admit that gets no answer, or one in the wrong shape, ends its lease the same way, since the store may have written it. A refusal (any 4xx, such as a runner key the store doesn't accept, or 503 while PocketBase has no key) wrote nothing: the runner ends no lease for it and doesn't try a refused finish again.
4. **Refunds.** A denial before the request ran, and an infrastructure failure after it ran (`auth_unavailable`, `quota_unavailable`, or `worker_unavailable`), refund the request's wall seconds, never the request itself. A render that ran out of time on its content (`render_timeout`) and every other failure keep their charge.

Proposed hourly limits, counted per UTC hour; the owner ratifies them:

| Bucket | Requests | Wall seconds | In flight |
| --- | --- | --- | --- |
| Each account | 120 | 1,800 | 2 |
| The deployment | 2,000 | no limit | 8 |
| The demo tier, shared by every demo account | 30 | 300 | 1 |
| Each runner replica | none | none | 4 (step 9) |

A request has to fit every bucket it counts in, and a demo account counts in all three. The tier is `is_demo` on the account's PocketBase record; a PocketBase hook refuses any client write to it or to the old demo flags. There's no `verified` requirement, so the deployment bucket bounds what new signups can spend. While quota enforces, an over-limit request writes nothing, and its 429 carries `Retry-After`: the rest of the hour for requests and wall seconds, or up to 10 seconds for a full in-flight bucket.

`ROUNDS_GATE_ENFORCE_IDEMPOTENCY` and `ROUNDS_GATE_ENFORCE_QUOTA` start at `observe`: admission checks every request and denies nothing. Each `decision` line then carries `idempotency` (`new`, `retry`, `replay`, `mismatch`, `in_flight`, `missing`, `unavailable`, or `skipped`), `quota` (`charged`, `exceeded`, `demo_limit`, `refunded`, `unavailable`, or `skipped`), and `would_deny`, the code enforcing would have answered. In observe mode an over-limit request runs uncounted and uncharged, and a replay runs again. With `ENFORCE_QUOTA` at `off` nothing is counted, charged, or limited. Idempotency doesn't depend on the quota gate: while `ENFORCE_IDEMPOTENCY` is on, every request that runs with a new key records its command.

To enforce:

1. Set `ROUNDS_ADMISSION_SECRET` to one value of at least 32 printable characters, such as the output of `openssl rand -hex 32`, on PocketBase and on every runner replica, and restart them. Without it the runner can't reach the store: in observe mode every `decision` line shows `"would_deny":"quota_unavailable"`, and enforcing answers `quota_unavailable`.
2. Read a few days of `decision` lines. `would_deny` should be rare and explainable, and `idempotency` should be `new` for nearly every request from a current tab.
3. Set both gates to `enforce` and restart every runner replica.
4. Confirm the startup line shows both `"value":"enforce","source":"env"`, then run a coding run twice from the app: both answer 200, and the second `decision` line shows `"idempotency":"new"` again, since each click mints a new key.

To back out, set a gate to `observe` (keep checking, deny nothing) or `off` (skip the check) and restart. Command rows, counters, and leases stay as receipts until the sweep expires them. To rotate the runner key, set the new value everywhere and restart PocketBase and the runners together; requests in between answer `quota_unavailable`, or run with `would_deny` in observe mode.

## Limits

Proposed values; the owner ratifies them. The 256 KiB snippet and the 200-file or 5 MiB project ceilings come from the spec.

| Route | Body cap | Field limits | Wall time |
| --- | --- | --- | --- |
| `/api/run` | 512 KiB | code 256 KiB, input 64 KiB | 3 s |
| `/api/evaluate` | 512 KiB | code 256 KiB, at most 32 selected cases | 3 s per case, 10 s for a `large` case |
| `/api/ai-coding/run-project` | 6 MiB | 200 files or 5 MiB | 10 s |
| `/api/ai-coding/grade` | 6 MiB | 200 files or 5 MiB, `ai_chats` 512 KiB | 45 s per checkpoint, at most 8 checkpoints |
| `/api/take-home/run` | 6 MiB | 200 files or 5 MiB | 60 s |
| `/api/take-home/submit` | 6 MiB | 200 files or 5 MiB, `notes` 64 KiB, `ai_chats` 512 KiB | 120 s |
| `/api/pdf/render` | 2 MiB | none | 25 s |
| `/api/ai/ats-rule` | 1 MiB | job description 64 KiB | none |
| `/api/ai/enhance-projects` | 6 MiB | at most 25 projects | none |

nginx caps every other path at 1 MiB and the Ingress at 6 MiB. nginx waits up to 60 seconds for `/api/run`, 420 seconds for `/api/evaluate`, and an hour for the other runner routes, each longer than the longest request admitted there. Each runner replica runs at most 4 admitted executions or renders at once.

## Candidate Processes Until #5

Each run gets a minimal environment with none of the runner's settings or secrets, a private scratch directory that is its working directory, `HOME`, and `TMPDIR`, and its input in a file. In the image the runner is root and each in-flight slot runs as its own user (uids 10001 to 10004, group 10000). `/app` stays root-owned, so candidate code can't write it. When a run ends, anything still running as that slot's user is killed and what it left in `/tmp`, `/var/tmp`, and `/dev/shm` is removed; that cleanup runs off the event loop, before the slot is free again. The runner keeps the first 4 MiB of each output stream. A `/api/run` or `/api/evaluate` result comes back in its own file in the scratch directory, read only if it's a regular file the slot's user owns and no larger than 4 MiB, so output size can't break a result. On k8s no pod mounts a service-account token. [#5](https://github.com/keyurgolani/rounds/issues/5) replaces this with ephemeral workers that have no secrets and no network; until then candidate code shares the runner's network.

## Alerts

Proposed thresholds, from the `decision` lines:

1. `auth_unavailable`, `quota_unavailable`, or `worker_unavailable` on more than 5% of a route's requests for 5 minutes. In observe mode, count `"would_deny":"quota_unavailable"` and `"quota":"unavailable"` too.
2. Any 5xx after admission: a `decision` line with status 500 or higher and no code.
3. A `definitions.loaded` line with `mismatched` above 0, or any `definition.rejected` line with `code":"definition_integrity_mismatch"`: a shipped definition in that image is missing or altered. Redeploy a clean image built from a tagged release; the line's `definition` names the version.

## Dependency Checks

1. PocketBase's auth-refresh answers from each runner replica at `POCKETBASE_URL`. A failure shows as `auth_unavailable` on every admitted route.
2. The renderer's health: a signed-in `GET /api/pdf/health` answers `{"status": "ok"}`, or 503 `{"status": "unavailable"}` when the runner can't reach the sidecar.
3. The admission store reads its counters for each replica: from inside each runner container, `GET http://pocketbase:8090/api/rounds/admission/usage` (or the replica's `POCKETBASE_URL`) with a signed-in test account's bearer answers that account's requests, wall seconds, and in-flight count for this hour. A failure shows as `quota_unavailable`, or as `"quota":"unavailable"` in observe mode.
4. The runner key: when `usage` answers but every `decision` line shows `"quota":"unavailable"`, `ROUNDS_ADMISSION_SECRET` is missing, shorter than 32 characters, or different on PocketBase and the runners.

## Repair

A PocketBase cron job, `rounds_admission_sweep`, runs every 5 minutes. It marks each `in_flight` command without a live lease `failed_infrastructure`, so its key can run again, and deletes expired leases, commands past their 24 hours, and counters older than a day. It refunds nothing and logs one `admission_sweep` line with the number it repaired.

If the sweep isn't running, repair by hand as a superuser in the PocketBase admin UI, where `now` is the current epoch second:

1. In `admission_leases`, delete every row with `expires_at <= now`.
2. In `admission_commands`, find rows with `state = 'in_flight'` that no remaining lease points at, and set each one's `state` to `failed_infrastructure`.
3. Optionally, delete `admission_commands` rows with `expires_at <= now` and `admission_counters` rows with `hour` more than 24 below `now / 3600`.

Then find out why the sweep stopped: PocketBase's log has one `admission_sweep` line every 5 minutes while it runs.
