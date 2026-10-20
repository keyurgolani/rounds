# Execution and Render Entry-Point Inventory

Stage 0 of #1 (`ROUNDS-00A-L01`). It lists every HTTP entry point that the runner, the PDF sidecar, the proxies, and the container stacks expose at commit [`62d4eae`](https://github.com/keyurgolani/rounds/tree/62d4eaeaecf601da836afa1981adc0b1ae2db16a) (`62d4eaeaecf601da836afa1981adc0b1ae2db16a`): what each one accepts, what it starts, where its data goes, and which leaf and stage closes each gap. That commit has no asynchronous entry points.

Code links point at that commit, so their line numbers hold as the code moves. `next` at `7209ed9` adds only the guide-file rename from [pull request #183](https://github.com/keyurgolani/rounds/pull/183), which touches no file cited here, so the inventory holds there too. Each threat is a category with the control that closes it.

## Counts

| Surface | At `62d4eae` | Issue body | Counted from |
| --- | --- | --- | --- |
| Runner application routes | 34 | 34 | `APIRoute` entries in `main.app.routes` |
| Runner framework routes | 4 | not counted | FastAPI defaults: `/openapi.json`, `/docs`, `/docs/oauth2-redirect`, `/redoc` |
| PDF sidecar routes | 2 | 2 | `backend/pdf_renderer/server.js` |
| nginx locations | 9 | no count | `frontend/nginx.conf` |
| Ingress rules | 1 | no count | `k8s/ingress.yaml` |
| Vite dev proxy entries | 11 | no count | `frontend/vite.config.ts` |
| Asynchronous entry points | 0 | 0 | [Asynchronous Entry Points](#asynchronous-entry-points) |
| PocketBase collections and hook routes | rows come from #9 | no count | `docs/security/account-scope.v1.json` |

The runner count comes from `main.app.routes` under the pinned `backend/requirements.txt` (FastAPI 0.115.0), which lists 38 entries, the 34 application routes and 4 framework routes. #172's surface table counts the same 38.

## Leaves Cited

| Issue | Leaf | Title |
| --- | --- | --- |
| [#1](https://github.com/keyurgolani/rounds/issues/1) | `ROUNDS-00A-L01` | Authenticate, authorize, and quota every execution and render route |
| [#2](https://github.com/keyurgolani/rounds/issues/2) | `ROUNDS-00A-L02` | Define server-owned Test Definitions, Harness Revisions, and Artifact Renderer Contracts |
| [#3](https://github.com/keyurgolani/rounds/issues/3) | `ROUNDS-00A-L03` | Introduce the execution-control protocol and durable result envelope |
| [#4](https://github.com/keyurgolani/rounds/issues/4) | `ROUNDS-00A-L04` | Create the Legacy Artifact Snapshot bridge and safe render disable |
| [#5](https://github.com/keyurgolani/rounds/issues/5) | `ROUNDS-00A-L05` | Isolate candidate code in ephemeral no-secret workers |
| [#6](https://github.com/keyurgolani/rounds/issues/6) | `ROUNDS-00A-L06` | Isolate document rendering in ephemeral no-script workers |
| [#7](https://github.com/keyurgolani/rounds/issues/7) | `ROUNDS-00A-L07` | Prove secret, network, and pooled-state containment |
| [#9](https://github.com/keyurgolani/rounds/issues/9) | `ROUNDS-00B-L01` | Establish the server-derived account-scope invariant |
| [#10](https://github.com/keyurgolani/rounds/issues/10) | `ROUNDS-00B-L02` | Authorize every typed relation and merge |
| [#11](https://github.com/keyurgolani/rounds/issues/11) | `ROUNDS-00B-L03` | Create immutable artifact share capabilities |
| [#12](https://github.com/keyurgolani/rounds/issues/12) | `ROUNDS-00B-L04` | Implement one-time share secret delivery, password protection, and rotation |
| [#14](https://github.com/keyurgolani/rounds/issues/14) | `ROUNDS-00B-L06` | Migrate legacy shares and prove immediate revocation |
| [#19](https://github.com/keyurgolani/rounds/issues/19) | `ROUNDS-02-L02` | Build the account-authorized domain command gateway |
| [#22](https://github.com/keyurgolani/rounds/issues/22) | `ROUNDS-02-L05` | Publish domain events through a transactional outbox |
| [#54](https://github.com/keyurgolani/rounds/issues/54) | `ROUNDS-10-L02` | Define durable Processing Jobs and adapter versioning |
| [#55](https://github.com/keyurgolani/rounds/issues/55) | `ROUNDS-10-L03` | Contain URL retrieval and file parsing |
| [#72](https://github.com/keyurgolani/rounds/issues/72) | `ROUNDS-14-L01` | Ratify privacy classes, sink policy, and numeric retention |
| [#73](https://github.com/keyurgolani/rounds/issues/73) | `ROUNDS-14-L02` | Define Provider Invocation Intent and authorization |
| [#76](https://github.com/keyurgolani/rounds/issues/76) | `ROUNDS-14-L05` | Enforce deletion, purge, backup expiry, and restore suppression |
| [#91](https://github.com/keyurgolani/rounds/issues/91) | `ROUNDS-18-L03` | Create complete versioned account export |
| [#93](https://github.com/keyurgolani/rounds/issues/93) | `ROUNDS-18-L05` | Build revocable public artifact sharing |
| [#172](https://github.com/keyurgolani/rounds/issues/172) | `ROUNDS-34-L03` | Maintain the authorization and privacy verification matrix |
| [#177](https://github.com/keyurgolani/rounds/issues/177) | `ROUNDS-00B-L07` | Contain and own the hosted demo account lifecycle |
| [#179](https://github.com/keyurgolani/rounds/issues/179) | `ROUNDS-14-L06` | Inventory, classify, and route legacy AI call sites through the invocation gateway |

#1's stages as this file uses them: S1 plumbing (a bearer on every runner call, typed errors, one `Idempotency-Key` per user action), S2 closures (admission middleware, server-loaded definitions, minimal child environment, nginx denials, body caps, AI limits), S3 admission state (idempotency, quotas, demo tier), S4 deployment verification in #9's harness, and S5 release guard.

## Shared Runtime Facts

### Processes

| Process | Runs as | Replicas | Secrets in its environment | Reaches |
| --- | --- | --- | --- | --- |
| `runner` (uvicorn, FastAPI) | root; [`backend/Dockerfile`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/Dockerfile) sets no `USER` | 1 in compose, 2 in [`k8s/runner.yaml:30`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/k8s/runner.yaml#L30) | `AI_KEY_SECRET`, `PB_ADMIN_EMAIL`, `PB_ADMIN_PASSWORD` ([`docker-compose.prod.yml:57-71`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/docker-compose.prod.yml#L57-L71), [`k8s/runner.yaml:61-66`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/k8s/runner.yaml#L61-L66); placeholders in [`docker-compose.yml:25-33`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/docker-compose.yml#L25-L33)) | `pocketbase:8090`, `pdf-renderer:4000`, AI provider hosts, GitHub, and any other URL; nothing limits egress |
| Candidate code | the runner's uid | one per run | all of the runner's: [`backend/runner.py:113-116`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/runner.py#L113-L116) passes no `env`, and [`backend/ai_coding/project_runner.py:116-127`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/ai_coding/project_runner.py#L116-L127) and [`backend/take_home/runner.py:107-118`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/take_home/runner.py#L107-L118) copy `os.environ` | everything the runner reaches, including the runner's own port |
| `pdf-renderer` (Express, Chromium) | root; [`backend/pdf_renderer/Dockerfile`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/pdf_renderer/Dockerfile) sets no `USER` | 1 in compose, none in `k8s/` | none | what the runner reaches. Compose declares no networks, so every service shares the default network and its outbound access ([`docker-compose.prod.yml:35-91`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/docker-compose.prod.yml#L35-L91)). #6 confines renders, and #7 proves it |

PocketBase holds `PB_ADMIN_EMAIL` and `PB_ADMIN_PASSWORD` for its first-admin migration ([`docker-compose.prod.yml:40-45`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/docker-compose.prod.yml#L40-L45)). The frontend nginx holds no secrets. `k8s/` defines no `NetworkPolicy`, and its Services are cluster-internal ([`k8s/runner.yaml:87-98`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/k8s/runner.yaml#L87-L98), [`k8s/pocketbase.yaml:74-85`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/k8s/pocketbase.yaml#L74-L85), [`k8s/frontend.yaml:43-54`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/k8s/frontend.yaml#L43-L54)).

### How the Runner Handles a Request

1. FastAPI reads and decodes the whole JSON body before any dependency runs. Routes that authenticate with `Depends(_auth_user)` ([`backend/routers/ai_coding.py:36-45`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai_coding.py#L36-L45), [`backend/routers/take_home.py:29-32`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/take_home.py#L29-L32), [`backend/routers/sd_practice.py:51-52`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/sd_practice.py#L51-L52)) check the bearer after the read and before validation. Routes that call `current_user(request)` inside the handler validate first, so a malformed anonymous request gets 422 before 401.
2. [`current_user`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/app/pb_auth.py#L45-L59) posts the bearer to PocketBase's `users` auth-refresh. Any answer other than 200 becomes 401. A connection failure isn't caught and becomes 500.
3. Byte limits come only from proxy defaults: nginx's 1 MiB, since [`frontend/nginx.conf`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/nginx.conf) sets no `client_max_body_size`, and the Ingress controller's default, since [`k8s/ingress.yaml:15-18`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/k8s/ingress.yaml#L15-L18) sets no `proxy-body-size`. The Vite proxy and uvicorn set none. The sidecar parses JSON up to 5 MB ([`backend/pdf_renderer/server.js:45`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/pdf_renderer/server.js#L45)).
4. No route has an idempotency key, replay check, quota, in-flight cap, or gate. The only gate is the signup pair: `ROUNDS_DISABLE_SIGNUPS` in [`pocketbase/pb_hooks/main.pb.js:3-9`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/pocketbase/pb_hooks/main.pb.js#L3-L9) and `VITE_DISABLE_SIGNUPS` in the SPA.
5. Plain `def` handlers run in the threadpool. Three `async def` handlers run a subprocess inline (grade, take-home run, take-home submit), which blocks the event loop until it exits.
6. CORS comes from `CORS_ALLOW_ORIGINS` ([`backend/main.py:13-23`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/main.py#L13-L23)): `*` without credentials when unset. Prod compose and k8s set it empty, which allows no cross-origin caller. Runner auth is a bearer header, never a cookie.
7. Errors are FastAPI's `{"detail": ...}`, and several routes put internal text in `detail` (threat `X1`). Only AI paths carry a correlation id, the 8-hex `_request_id` ([`backend/routers/ai.py:51-58`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L51-L58)).
8. Logs go to the container's stdout and stderr. Provider paths log exception text and some request fields, which #179 inventories.

## Threat Categories

Each route row cites these IDs. "Interim" is the #1 stage that contains the gap until the closing leaf lands.

| ID | Category | Control | Interim | Closed by |
| --- | --- | --- | --- | --- |
| `A1` | Work starts on an anonymous request: a subprocess, a browser render, or CPU-bound scoring | Admission steps 1 to 4 (byte cap, gate, account, tier) before the body is read | none | #1 S2 |
| `A2` | Nothing limits repeats or volume: no idempotency, quota, or in-flight cap | Admission steps 6, 7, and 9, with one `Idempotency-Key` per user action | S1 sends the keys | #1 S3 on admitted routes; #73's budgets on provider routes; on `by-token`, #11 S1 stops the view writes and #14 S1 removes the route |
| `A3` | Size limits come only from proxy defaults | Byte caps at nginx, the Ingress, and the middleware (413 `payload_too_large`); field limits (413 `limit_exceeded`, 422 `invalid_request`) | none | #1 S2 |
| `A4` | Demo limits live in the browser and in `users` fields the browser writes | Server tier from `is_demo` behind an accessor; a `users` hook blocks client writes to it and to the demo flags | none | #1 S3; #177 owns the demo lifecycle |
| `E1` | The caller supplies what the server runs or trusts: tests, expected values, entry and driver code, shell command, timeout | Requests carry ids and code only; definitions load on the server | S2 loads them with the caller's token | #2 |
| `E2` | Validators are evaluated inside the API process ([`backend/matchers.py:133-145`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/matchers.py#L133-L145)) | Validators run in the worker's harness | S2 evaluates only server-loaded validators | #2, its step 1 |
| `E3` | Candidate code inherits the runner's environment, which holds `AI_KEY_SECRET` and `PB_ADMIN_*` | Minimal child environment | S2 | #5; #7 proves it |
| `E4` | Candidate code runs as root beside the runner with shared `/tmp` scratch, and `bash -c` grandchildren outlive their timeouts | Separate candidate uid and private scratch, then ephemeral workers | S2 gives candidates their own uid and scratch | #5; #7 proves it |
| `E5` | Candidate code shares the runner's network | Workers with no network | none | #5; #7 proves it |
| `E6` | Input travels in argv, so a large input fails before the code runs | Input by file | none | #1 S2 |
| `E7` | A subprocess inside an `async def` handler blocks the event loop for the whole replica | `run_in_threadpool` | none | #1 S2 |
| `I1` | Results aren't server-authoritative: the SPA stores AI-coding grades itself, take-home submit saves its `status: "graded"` row with the caller's token, and a failed run can show as a score of 0 | Only the server writes graded rows, from an authoritative envelope; attempt rules refuse client `graded` writes; a failure stays typed and never becomes a score | none | #3 |
| `R1` | Caller-authored HTML renders with scripts enabled in a Chromium launched with `--no-sandbox` | Server-built Legacy Artifact Snapshots, then a fresh no-script render worker per request | S2 adds auth and a 2 MiB cap | #4, then #6; #7 proves it |
| `R2` | One pooled browser serves every account's renders, and the sidecar answers anything on its network | One sandbox per render, reachable only from the control plane | none | #6; #7 proves it |
| `N1` | `improve` fetches a caller-supplied `paper_url` from the runner and follows redirects | No fetch while `ROUNDS_GATE_PAPER_FETCH` is off | S2 | #55; #179 removes the call |
| `N2` | The account's provider `base_url` decides where the runner sends the decrypted key and the prompt | 403 `destination_denied` for loopback, link-local, metadata, and service-name hosts | S2 | #73 stage B |
| `N3` | `enhance-projects` makes up to 11 provider calls and 12 GitHub requests per project, for any number of projects, all at once | At most 25 projects (proposed), 413 `limit_exceeded` | S2 | #73's 25-call lineage budget, through #179 PR 8 |
| `O1` | The runner forwards record ids that PocketBase accepts across accounts | Lookups with the caller's token before allocation (admission step 8); account-scope rules; relation checks | S2 denies a foreign `campaign_id` | #9, #10, #11 S1, #73 stage C |
| `O2` | A route reads or writes with the cached PocketBase superuser token, minted from `PB_ADMIN_*` or development defaults when those are absent ([`backend/app/pb_auth.py:121-152`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/app/pb_auth.py#L121-L152)) | Capability-scoped share resolution | none | #11 S1, then #14 S3; #9 S4 checks that the defaults fail |
| `X1` | Internal error text reaches the caller: sidecar bodies, exception text, PocketBase error bodies ([`backend/app/pb_auth.py:62-106`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/app/pb_auth.py#L62-L106)), and provider messages | `{"detail", "code", "correlation_id"}` with fixed text | S2 on admitted routes | #179 PR 1 for provider text, #73 for PocketBase text on provider routes, #11 S1 for `public_read`, #14 S1 for `delete_link` |
| `P1` | The public proxy forwards PocketBase's admin UI and admin API | nginx 404s ahead of `/api/` | none | #1 S2; #9 S4 verifies |

## Runner Routes

"Bearer (dependency)" means `Depends(_auth_user)`, which runs after the body is read and before it's validated. "Bearer (handler)" means the handler calls `current_user` after validation. "S2 admission" is the chain #1 adds in `backend/app/admission.py`, per #1's Admission order.

| Method | Path | Handler | Auth today | Allocation | S2 admission | Owner | Threats |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `POST` | `/api/run` | [`backend/routers/runner.py:21-37`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/runner.py#L21-L37) | none | 1 subprocess, 3 s | admitted | #1 | `A1` `A2` `A3` `A4` `E1` `E3` `E4` `E5` `E6` |
| `POST` | `/api/evaluate` | [`backend/routers/runner.py:58-94`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/runner.py#L58-L94) | none | 1 subprocess per case, in order, 3 s or 10 s each | admitted | #1 | `A1` `A2` `A3` `A4` `E1` `E2` `E3` `E4` `E5` `E6` |
| `POST` | `/api/ai-coding/run-project` | [`backend/routers/ai_coding.py:66-83`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai_coding.py#L66-L83) | none | 1 `bash -c`, caller's timeout | admitted | #1 | `A1` `A2` `A3` `A4` `E1` `E3` `E4` `E5` |
| `POST` | `/api/ai-coding/grade` | [`backend/routers/ai_coding.py:262-336`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai_coding.py#L262-L336) | bearer (dependency) | 1 `bash -c` per checkpoint, 45 s each; 1 provider call | admitted | #1 | `A2` `A3` `A4` `E3` `E4` `E5` `E7` `I1` `N2` `X1` |
| `POST` | `/api/take-home/run` | [`backend/routers/take_home.py:75-94`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/take_home.py#L75-L94) | bearer (dependency) | 1 `bash -c`, 60 s | admitted | #1 | `A2` `A3` `A4` `E3` `E4` `E5` `E7` `I1` |
| `POST` | `/api/take-home/submit` | [`backend/routers/take_home.py:106-174`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/take_home.py#L106-L174) | bearer (dependency) | 1 `bash -c`, 120 s; 1 provider call; 1 PocketBase create | admitted | #1 | `A2` `A3` `A4` `E3` `E4` `E5` `E7` `I1` `N2` `O1` `X1` |
| `POST` | `/api/pdf/render` | [`backend/routers/pdf.py:42-63`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/pdf.py#L42-L63) | none | 1 sidecar render, 25 s | admitted | #1 | `A1` `A2` `A3` `A4` `R1` `R2` `X1` |
| `GET` | `/api/pdf/health` | [`backend/routers/pdf.py:32-39`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/pdf.py#L32-L39) | none | 1 sidecar request, 2 s | admitted, skips 6, 7, 9 | #1 | `A1` `X1` |
| `POST` | `/api/ai/ats-rule` | [`backend/routers/ai.py:1521-1534`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L1521-L1534) | none | CPU only | admitted, skips 6, 7, 9 | #1 | `A1` `A3` |
| `GET` | `/api/ai/providers` | [`backend/routers/ai.py:347-351`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L347-L351) | bearer (handler) | PocketBase read | not admitted | #73 | `X1` |
| `POST` | `/api/ai/providers` | [`backend/routers/ai.py:354-370`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L354-L370) | bearer (handler) | PocketBase create | not admitted | #73 | `X1` |
| `PATCH` | `/api/ai/providers/{provider_id}` | [`backend/routers/ai.py:373-399`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L373-L399) | bearer (handler) | PocketBase read and update | not admitted | #73 | `X1` |
| `DELETE` | `/api/ai/providers/{provider_id}` | [`backend/routers/ai.py:402-411`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L402-L411) | bearer (handler) | PocketBase read and delete | not admitted | #73 | `X1` |
| `POST` | `/api/ai/providers/{provider_id}/test` | [`backend/routers/ai.py:414-470`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L414-L470) | bearer (handler) | 1 provider call | not admitted | #73 | `A2` `N2` `X1` |
| `POST` | `/api/ai/providers/{provider_id}/refresh-models` | [`backend/routers/ai.py:473-502`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L473-L502) | bearer (handler) | 1 provider model list; PocketBase update | not admitted | #73 | `A2` `N2` `X1` |
| `GET` | `/api/ai/settings` | [`backend/routers/ai.py:510-521`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L510-L521) | bearer (handler) | PocketBase read | not admitted | #73 | `X1` |
| `PUT` | `/api/ai/settings` | [`backend/routers/ai.py:524-550`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L524-L550) | bearer (handler) | PocketBase create or update | not admitted | #73 | `O1` `X1` |
| `POST` | `/api/ai/improve` | [`backend/routers/ai.py:1041-1117`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L1041-L1117) | bearer (handler) | 1 provider stream; optional `paper_url` fetch | not admitted | #179 | `A2` `N1` `N2` `X1` |
| `POST` | `/api/ai/tailor` | [`backend/routers/ai.py:1192-1234`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L1192-L1234) | bearer (handler) | 1 provider call | not admitted | #179 | `A2` `N2` `X1` |
| `POST` | `/api/ai/cover-letter` | [`backend/routers/ai.py:1251-1289`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L1251-L1289) | bearer (handler) | 1 provider stream | not admitted | #179 | `A2` `N2` `X1` |
| `POST` | `/api/ai/import` | [`backend/routers/ai.py:1292-1325`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L1292-L1325) | bearer (handler) | 1 provider call | not admitted | #179 | `A2` `N2` `X1` |
| `POST` | `/api/ai/experience-import` | [`backend/routers/ai.py:1328-1367`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L1328-L1367) | bearer (handler) | 1 provider call | not admitted | #179 | `A2` `N2` `X1` |
| `POST` | `/api/ai/ats-ai` | [`backend/routers/ai.py:1537-1626`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L1537-L1626) | bearer (handler), skipped when `use_ai` is false | 1 provider call | not admitted | #179 | `A2` `N2` `X1` |
| `POST` | `/api/ai/enhance-projects` | [`backend/routers/ai.py:1882-1913`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L1882-L1913) | bearer (handler), skipped for an empty list | up to 11 provider calls and 12 GitHub requests per project | not admitted | #179 | `A2` `N2` `N3` `X1` |
| `POST` | `/api/ai-coding/chat` | [`backend/routers/ai_coding.py:167-201`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai_coding.py#L167-L201) | bearer (dependency) | 1 provider stream | not admitted | #179 | `A2` `N2` `X1` |
| `POST` | `/api/ai-coding/edit` | [`backend/routers/ai_coding.py:204-253`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai_coding.py#L204-L253) | bearer (dependency) | 1 provider stream | not admitted | #179 | `A2` `N2` `X1` |
| `GET` | `/api/ai-coding/models` | [`backend/routers/ai_coding.py:339-356`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai_coding.py#L339-L356) | bearer (dependency) | PocketBase read | not admitted | #73 | `X1` |
| `POST` | `/api/sd-practice/chat` | [`backend/routers/sd_practice.py:699-755`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/sd_practice.py#L699-L755) | bearer (dependency) | 1 provider stream with tool calls | not admitted | #179 | `A2` `N2` `X1` |
| `POST` | `/api/take-home/chat` | [`backend/routers/take_home.py:208-246`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/take_home.py#L208-L246) | bearer (dependency) | 1 provider stream | not admitted | #179 | `A2` `N2` `X1` |
| `POST` | `/api/share` | [`backend/routers/share.py:66-95`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/share.py#L66-L95) | bearer (handler) | PocketBase create | not admitted | #11 | `O1` `X1` |
| `GET` | `/api/share` | [`backend/routers/share.py:98-126`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/share.py#L98-L126) | bearer (handler) | PocketBase list; a superuser count per link | not admitted | #11 | `O2` `X1` |
| `DELETE` | `/api/share/{link_id}` | [`backend/routers/share.py:129-139`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/share.py#L129-L139) | bearer (handler) | PocketBase delete | not admitted | #11 | `X1` |
| `GET` | `/api/share/by-token/{token}` | [`backend/routers/share.py:147-218`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/share.py#L147-L218) | none, by design | superuser reads; 1 superuser create | not admitted | #11 | `A2` `O2` `X1` |
| `GET` | `/health` | [`backend/main.py:37-39`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/main.py#L37-L39) | none | none | not admitted | #1 | none |
| `GET`, `HEAD` | `/openapi.json` | FastAPI default ([`backend/main.py:8`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/main.py#L8)) | none | none | not admitted; no proxy forwards it | #1 | none |
| `GET`, `HEAD` | `/docs` | FastAPI default ([`backend/main.py:8`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/main.py#L8)) | none | none | not admitted; no proxy forwards it | #1 | none |
| `GET`, `HEAD` | `/docs/oauth2-redirect` | FastAPI default ([`backend/main.py:8`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/main.py#L8)) | none | none | not admitted; no proxy forwards it | #1 | none |
| `GET`, `HEAD` | `/redoc` | FastAPI default ([`backend/main.py:8`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/main.py#L8)) | none | none | not admitted; no proxy forwards it | #1 | none |

### Execution Routes

All six write candidate code into a temp file or a fresh `mkdtemp` directory under `/tmp` and remove it afterwards. Output is capped at 64 KiB for snippets ([`backend/runner.py:20`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/runner.py#L20)) and 256 KiB for projects ([`backend/ai_coding/project_runner.py:20`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/ai_coding/project_runner.py#L20), [`backend/take_home/runner.py:23`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/take_home/runner.py#L23)). The child gets the runner's environment (`E3`) and can reach everything the runner can (`E5`), though none of these routes needs any host.

`POST /api/run`

- Caller sends `code`, `language` (`python` or `javascript`, default `python`), `entry`, and `input` ([`backend/schemas.py:24-28`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/schemas.py#L24-L28)). `entry` accepts any extra field ([`backend/schemas.py:8-21`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/schemas.py#L8-L21)), and a `custom` entry carries its own driver source ([`backend/drivers/python/custom.py:19-20`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/drivers/python/custom.py#L19-L20), [`backend/drivers/javascript/custom.py:15-16`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/drivers/javascript/custom.py#L15-L16)).
- Server sets the 3 s timeout ([`backend/routers/runner.py:17-18`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/runner.py#L17-L18)) and the output cap.
- Starts one `python` or `node` process with `input` in argv ([`backend/runner.py:107-116`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/runner.py#L107-L116)).
- Returns stdout, stderr, the return value, the error text, and the duration.
- Called by [`frontend/src/pages/coding/runnerApi.ts:57-64`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/src/pages/coding/runnerApi.ts#L57-L64) with `auth: 'optional'`. A demo account first sets `demo_run_used` on its own `users` record from the browser ([`frontend/src/pages/coding/runnerApi.ts:39-55`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/src/pages/coding/runnerApi.ts#L39-L55)).
- S2 shape: `question_slug`, `language`, `code`, and `input` (64 KiB) in a 512 KiB body. The server loads `entry`.

`POST /api/evaluate`

- Caller sends `code`, `language`, `entry`, `test_cases`, and an optional `filter` of `tags` or `indices` ([`backend/schemas.py:40-50`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/schemas.py#L40-L50)). Each case carries `input`, `expected`, `tags`, and `description`.
- Server gives each case 3 s, or 10 s when the caller tags it `large` ([`backend/routers/runner.py:53-55`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/runner.py#L53-L55)). Nothing limits the case count.
- Starts one process per selected case, in order, then matches each result in the API process (`E2`).
- Returns each case's output, expected value, pass flag, and error.
- Called by [`frontend/src/pages/coding/runnerApi.ts:66-75`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/src/pages/coding/runnerApi.ts#L66-L75) with `auth: 'optional'` and the `demo_evaluate_used` check. The SPA sends the `test_cases` it read from `coding_questions` ([`frontend/src/pages/CodingDetail.tsx:328-334`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/src/pages/CodingDetail.tsx#L328-L334)), which clients can't write ([`pocketbase/pb_migrations/1700000000_init_collections.js:73-80`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/pocketbase/pb_migrations/1700000000_init_collections.js#L73-L80)).
- S2 shape: `question_slug`, `language`, `code`, and `filter` in 512 KiB. The server loads `entry` and `test_cases`, at most 32 cases.

`POST /api/ai-coding/run-project`

- Caller sends `files` (path to contents), `language`, `test_command`, and `timeout_s` (default 30, no upper bound) ([`backend/routers/ai_coding.py:48-52`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai_coding.py#L48-L52)).
- Server rejects absolute and `..` paths ([`backend/ai_coding/project_runner.py:88-96`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/ai_coding/project_runner.py#L88-L96)) and puts the scratch directory on `PYTHONPATH`.
- Starts `bash -c` with the caller's `test_command` in a fresh `mkdtemp` directory, with a copy of `os.environ` ([`backend/ai_coding/project_runner.py:99-127`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/ai_coding/project_runner.py#L99-L127)).
- Returns pass and fail counts parsed from the output, stdout, stderr, and the error.
- Called by [`frontend/src/pages/ai-coding/aiCodingApi.ts:176-188`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/src/pages/ai-coding/aiCodingApi.ts#L176-L188) with `auth: 'optional'`. The SPA sends the checkpoint's `test_command` from the round it loaded ([`frontend/src/pages/ai-coding/AICodingDetail.tsx:236-241`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/src/pages/ai-coding/AICodingDetail.tsx#L236-L241)).
- S2 shape: `round_slug`, `checkpoint_index`, and `files` in 6 MiB. The server uses the checkpoint's `test_command` with a 10 s limit.

`POST /api/ai-coding/grade`

- Caller sends `round_slug` (`^[a-z0-9-]+$`), `files`, and `ai_chats` ([`backend/routers/ai_coding.py:256-259`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai_coding.py#L256-L259)).
- Server reads the round from `ai_coding_rounds` with the caller's token: each checkpoint's `test_command` and `hidden_files`, the `rubric`, and `language` ([`backend/routers/ai_coding.py:267-278`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai_coding.py#L267-L278)). Clients can't write that collection ([`pocketbase/pb_migrations/1700001100_ai_coding.js:37-43`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/pocketbase/pb_migrations/1700001100_ai_coding.js#L37-L43)).
- Starts one `bash -c` per checkpoint, in order, 45 s each ([`backend/routers/ai_coding.py:307`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai_coding.py#L307)), inside `async def`. Then one provider call for the rubric review with the account's active text model ([`backend/routers/ai_coding.py:316-334`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai_coding.py#L316-L334)), decrypting its key with `AI_KEY_SECRET`.
- Returns each checkpoint's result with up to 8,000 characters of output, plus the rubric review. A provider failure's text lands in `rubric_review.reason`. Nothing is written to PocketBase; the SPA stores the graded attempt (`I1`).
- Reaches `pocketbase:8090` and the account's provider host.
- Called by [`frontend/src/pages/ai-coding/aiCodingApi.ts:219-226`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/src/pages/ai-coding/aiCodingApi.ts#L219-L226) with `auth: 'required'`.
- S2 shape: unchanged, 6 MiB, with `ai_chats` up to 512 KiB.

`POST /api/take-home/run`

- Caller sends `assignment_slug` and `files` ([`backend/routers/take_home.py:60-62`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/take_home.py#L60-L62)).
- Server reads `entrypoint` and `harness_files` from `take_home_assignments` with the caller's token ([`backend/routers/take_home.py:35-44`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/take_home.py#L35-L44)). Clients can't write that collection ([`pocketbase/pb_migrations/1700001300_take_home.js:37-43`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/pocketbase/pb_migrations/1700001300_take_home.js#L37-L43)). Harness files replace caller files at the same path.
- Starts `bash -c` with the `entrypoint`, 60 s, inside `async def` ([`backend/take_home/runner.py:92-118`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/take_home/runner.py#L92-L118)).
- Returns the harness score and criteria, with up to 8,000 characters each of stdout and stderr. The SPA shows a failed request as a score of 0 (`I1`, [`frontend/src/pages/take-home/TakeHomeDetail.tsx:203-213`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/src/pages/take-home/TakeHomeDetail.tsx#L203-L213)).
- Called by [`frontend/src/pages/take-home/takeHomeApi.ts:87-97`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/src/pages/take-home/takeHomeApi.ts#L87-L97) with `auth: 'required'`.
- S2 shape: unchanged, 6 MiB.

`POST /api/take-home/submit`

- Caller sends `assignment_slug`, `files`, `notes`, `ai_chats`, `campaign_id`, and `duration_ms` ([`backend/routers/take_home.py:97-103`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/take_home.py#L97-L103)). `campaign_id` goes into the attempt unchecked ([`backend/routers/take_home.py:162-163`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/take_home.py#L162-L163)), and `duration_ms` is the client's own number.
- Server reads `entrypoint`, `harness_files`, and `rubric`, and allows 120 s ([`backend/routers/take_home.py:116`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/take_home.py#L116)).
- Starts one `bash -c`, then one provider call for the rubric review, then one PocketBase create in `take_home_attempts` with the caller's token (`I1`): `user` from the bearer, `status: "graded"`, the files, chats, notes, harness output, and review ([`backend/routers/take_home.py:148-172`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/take_home.py#L148-L172)). A provider failure's text lands in `rubric_review.reason`.
- Reaches `pocketbase:8090` and the account's provider host, and uses `AI_KEY_SECRET`.
- Called by [`frontend/src/pages/take-home/takeHomeApi.ts:99-106`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/src/pages/take-home/takeHomeApi.ts#L99-L106) with `auth: 'required'`.
- S2 shape: unchanged, 6 MiB. A foreign `campaign_id` gets 404 before anything runs.

### Render Routes

`POST /api/pdf/render`

- Caller sends `html` (at least 1 character, no maximum) and `margin_mm` (0 to 30) ([`backend/routers/pdf.py:24-29`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/pdf.py#L24-L29)).
- Server forwards both to `PDF_RENDERER_URL` with a 25 s timeout ([`backend/routers/pdf.py:20-21`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/pdf.py#L20-L21)).
- Starts one page in the sidecar's pooled browser.
- Returns the PDF, or a 502 whose `detail` is the sidecar's error body ([`backend/routers/pdf.py:57-61`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/pdf.py#L57-L61)).
- Called by [`frontend/src/features/resume/export/pdf.ts:18-34`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/src/features/resume/export/pdf.ts#L18-L34) with a plain `fetch` and no bearer.
- S2 shape: unchanged, 2 MiB. Render stops echoing sidecar text.

`GET /api/pdf/health`

- No input. One request to the sidecar's `/health` with a 2 s timeout.
- Returns `{status, code}`, or a 502 with the exception text.
- S2: admitted without idempotency, quota, or the replica cap, and returns only `{status}`.

### ATS Rule Route

`POST /api/ai/ats-rule`

- Caller sends `data` (the resume), `job_description`, and `use_ai`, which this route ignores ([`backend/routers/ai.py:265-268`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L265-L268)).
- Server scores it by rules in the API process: contact fields, sections, keywords against the job description, dates, bullets, and action verbs ([`backend/app/ats.py`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/app/ats.py)). No provider call, no PocketBase access, nothing stored.
- Called on every ATS score in the resume studio ([`frontend/src/features/resume/ai/client.ts:166-177`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/src/features/resume/ai/client.ts#L166-L177)).
- S2: admitted without idempotency, quota, or the replica cap. 1 MiB.

### AI Provider and Settings Routes

All eight check the bearer in the handler after validation, read and write with the caller's token, and stamp `user` from the bearer on create. PocketBase error text passes through as `detail` (`X1`). #73 owns them. Its stage A moves their writes to its `ai_gateway` service writer (see [server-writes.md](server-writes.md)), and its stage C moves them to #19's command gateway.

| Route | Caller sends | What runs |
| --- | --- | --- |
| `GET /api/ai/providers` | nothing | lists the caller's `ai_providers` |
| `POST /api/ai/providers` | `kind`, `label`, `base_url`, `key` | creates the row; the key is encrypted with `AI_KEY_SECRET` ([`backend/app/crypto.py:57-67`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/app/crypto.py#L57-L67)) |
| `PATCH /api/ai/providers/{provider_id}` | path id; `kind`, `label`, `base_url`, `key` (`null` clears it, empty keeps it) | reads the row to check ownership, then updates it |
| `DELETE /api/ai/providers/{provider_id}` | path id | reads the row to check ownership, then deletes it |
| `POST /api/ai/providers/{provider_id}/test` | path id | decrypts the key and sends a 12-token request to the row's `base_url` or the first-party host; the model's reply comes back, and a failure's message goes into `detail` ([`backend/routers/ai.py:459-468`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L459-L468)) |
| `POST /api/ai/providers/{provider_id}/refresh-models` | path id | decrypts the key, lists the provider's models ([`backend/routers/ai.py:807-831`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L807-L831)), and saves them; provider text goes into `detail` ([`backend/routers/ai.py:489-495`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L489-L495)) |
| `GET /api/ai/settings` | nothing | reads the caller's `ai_settings` |
| `PUT /api/ai/settings` | `text_provider_id`, `text_model`, `vision_provider_id`, `vision_model` | creates or updates the row without checking that the provider ids are the caller's (`O1`, #73 stage C) |

### AI Generation Routes

These load the account's active text model with the caller's token and decrypt its key with `AI_KEY_SECRET` ([`backend/routers/ai.py:558-577`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L558-L577)), or use the `provider_id` and `model` pair the caller names where the route allows one. They reach `pocketbase:8090` and the provider host: `api.anthropic.com`, `api.openai.com`, or the row's `base_url` ([`backend/routers/ai.py:777-778`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L777-L778)). Streaming routes report a failure as an SSE `error` event, and its message falls back to the exception's first line ([`backend/routers/ai.py:145-150`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L145-L150)). #179's `legacy-inventory/v1` records each call's fields, persistence, and log sinks; this table covers the entry point.

| Route | Auth | Caller sends | What runs |
| --- | --- | --- | --- |
| `POST /api/ai/improve` | handler | `text`, `style`, `context`, `resume`, `ats`, `field` | rule-based ATS scoring of `resume`; an HTTP GET of `context.paper_url` that follows redirects and parses HTML or PDF ([`backend/routers/ai.py:981-1038`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L981-L1038), [`backend/routers/ai.py:1074-1080`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L1074-L1080)); one provider stream |
| `POST /api/ai/tailor` | handler | `data`, `job_description`, `tone`, `role_focus`, `target_company`, `job_title` | one provider call, up to 6,000 tokens |
| `POST /api/ai/cover-letter` | handler | `data`, `job_description`, `tone`, `target_company`, `job_title` | one provider stream |
| `POST /api/ai/import` | handler | `text` | one provider call on the first 30,000 characters |
| `POST /api/ai/experience-import` | handler | `text`, `existing`, `existing_connections` | one provider call with up to 120 elements and 300 connections |
| `POST /api/ai/ats-ai` | handler, after `use_ai` | `data`, `job_description`, `use_ai` | with `use_ai` false it returns before auth and runs nothing ([`backend/routers/ai.py:1545-1551`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L1545-L1551)); otherwise one provider call, with errors as `ai_error` in a 200 |
| `POST /api/ai/enhance-projects` | handler, after a non-empty list | `projects` | an empty list returns before auth ([`backend/routers/ai.py:1898-1899`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L1898-L1899)); each project with a `full_name` gets up to 12 requests to `api.github.com` and `raw.githubusercontent.com` and up to 11 provider calls ([`backend/routers/ai.py:1660-1665`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L1660-L1665), [`backend/routers/ai.py:1850-1879`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L1850-L1879)); all projects run at once ([`backend/routers/ai.py:1908-1912`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai.py#L1908-L1912)) |
| `POST /api/ai-coding/chat` | dependency | `round_slug`, `checkpoint_index`, `provider_id` and `model` (both or neither), `messages`, `files`, `checkpoint_prompt` | an `ai_allowed` check on the round ([`backend/routers/ai_coding.py:148-164`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/ai_coding.py#L148-L164)); one provider stream with up to 60,000 characters of files |
| `POST /api/ai-coding/edit` | dependency | same as chat | the same, with up to 8,000 tokens and a parsed `patches` event |
| `GET /api/ai-coding/models` | dependency | nothing | the caller's providers and cached models; no provider call |
| `POST /api/sd-practice/chat` | dependency | `question_slug`, `question_prompt`, `canvas_elements`, `messages`, `provider_id` and `model` | one provider stream with canvas tools |
| `POST /api/take-home/chat` | dependency | `assignment_slug`, `provider_id` and `model`, `messages`, `files` | 403 when the assignment's `ai_policy` is `off`; otherwise one provider stream with the assignment's `prompt_md` and the files |

### Share Routes

#11 owns these, then #12 and #14.

- `POST /api/share`: caller sends `resume_id` or `variant_id`. The server stamps `user` from the bearer, mints a 22-character token ([`backend/routers/share.py:55-58`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/share.py#L55-L58)), creates the `resume_share_links` row with the caller's token, and returns the token. Nothing checks who owns the target (`O1`).
- `GET /api/share`: lists the caller's links with the caller's token, then counts each link's views with the superuser token ([`backend/routers/share.py:240-258`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/share.py#L240-L258)). Returns every token again, which #12 stops.
- `DELETE /api/share/{link_id}`: deletes with the caller's token and answers `{"ok": true}` for a missing id. Other PocketBase errors pass through. #14 S1 removes the route.
- `GET /api/share/by-token/{token}`: anonymous by design. With the superuser token it finds the link and reads its resume, or its variant and the parent resume ([`backend/routers/share.py:155-196`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/share.py#L155-L196)), then creates a `resume_share_views` row holding a truncated IP hash and the user agent ([`backend/routers/share.py:198-216`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/share.py#L198-L216)). Returns the record's `data`, `template_id`, `design`, `name`, and `kind`. #11 S1 adds the kill switch, the token-format check, the uniform 404, and no view writes; #14 S1 removes the route.

### Health and Framework Routes

`GET /health` returns `{"status": "ok"}` for the k8s probes ([`k8s/runner.yaml:67-78`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/k8s/runner.yaml#L67-L78)). FastAPI also serves the OpenAPI schema and two docs pages, because `FastAPI()` doesn't turn them off. None of these touch account data or start work. nginx and Vite send all five paths to the SPA, so they answer only on the runner's port: on the host in dev compose ([`docker-compose.yml:21-22`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/docker-compose.yml#L21-L22)), and on the compose network or inside the cluster otherwise. They stay outside admission.

## PDF Sidecar Routes

| Method | Path | Handler | Auth | Input | Starts |
| --- | --- | --- | --- | --- | --- |
| `GET` | `/health` | [`backend/pdf_renderer/server.js:47-49`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/pdf_renderer/server.js#L47-L49) | none | none | nothing |
| `POST` | `/render` | [`backend/pdf_renderer/server.js:51-102`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/pdf_renderer/server.js#L51-L102) | none | `html` (string), `marginMm` (not validated here) | one page in the pooled browser |

- It listens on `0.0.0.0:4000` ([`backend/pdf_renderer/server.js:104-106`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/pdf_renderer/server.js#L104-L106)) with a 5 MB JSON limit. Neither compose file publishes it to the host ([`docker-compose.yml:39-45`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/docker-compose.yml#L39-L45), [`docker-compose.prod.yml:48-52`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/docker-compose.prod.yml#L48-L52)), and `k8s/` doesn't deploy it.
- It launches one Chromium per process with `--no-sandbox` and `--disable-setuid-sandbox` and reuses it for every request ([`backend/pdf_renderer/server.js:17-40`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/pdf_renderer/server.js#L17-L40)). Pages keep JavaScript on.
- It aborts every request the page makes unless it's a `data:` URL, waits for `load` up to 15 s ([`backend/pdf_renderer/server.js:77`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/pdf_renderer/server.js#L77)), and prints A4 with the caller's margin.
- On failure it returns 500 with the error message and logs the error to stderr ([`backend/pdf_renderer/server.js:94-96`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/pdf_renderer/server.js#L94-L96)).
- Its environment holds no secrets ([`backend/pdf_renderer/Dockerfile:16-18`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/pdf_renderer/Dockerfile#L16-L18)).
- The runner is its only intended client, but anything on its network can call it, including candidate code in the runner.
- Owner: #6, which replaces it with per-request render workers. #4 changes what it renders first. Threats: `R1`, `R2`, `X1`.

## Proxies and Published Ports

### nginx

[`frontend/nginx.conf`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/nginx.conf) ships in the frontend image ([`frontend/Dockerfile:19-26`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/Dockerfile#L19-L26)), which prod compose and k8s both run. It sets no `client_max_body_size`, so the 1 MiB default applies to every location.

| Location | Lines | Goes to | Notes | Threats |
| --- | --- | --- | --- | --- |
| `= /api/run` | [`frontend/nginx.conf:8`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/nginx.conf#L8) | runner | no forwarding headers, default read timeout | the route's, plus `A3` |
| `= /api/evaluate` | [`frontend/nginx.conf:9`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/nginx.conf#L9) | runner | same | the route's, plus `A3` |
| `= /api/execute` | [`frontend/nginx.conf:10`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/nginx.conf#L10) | runner | no runner route serves it, so FastAPI answers 404; #1 S2 removes it | none |
| `~ ^/api/(share\|pdf\|ai\|ai-coding\|sd-practice\|take-home)(/\|$)` | [`frontend/nginx.conf:17-26`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/nginx.conf#L17-L26) | runner | forwarding headers, buffering off, 3600 s read timeout | each route's, plus `A3` |
| `/api/` | [`frontend/nginx.conf:31-41`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/nginx.conf#L31-L41) | pocketbase | records, auth, realtime, files, health, and the admin API | `P1`; collection rows from #9 |
| `/_/` | [`frontend/nginx.conf:43-50`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/nginx.conf#L43-L50) | pocketbase | admin UI | `P1` |
| `/assets/` | [`frontend/nginx.conf:53-57`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/nginx.conf#L53-L57) | static files | | none |
| `~ \.mjs$` | [`frontend/nginx.conf:63-69`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/nginx.conf#L63-L69) | static files | | none |
| `/` | [`frontend/nginx.conf:72-74`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/nginx.conf#L72-L74) | the SPA's `index.html` | also answers the runner's `/health` and docs paths | none |

### Ingress

[`k8s/ingress.yaml`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/k8s/ingress.yaml) sends everything for its host to the `frontend` Service on port 80 ([`k8s/ingress.yaml:25-35`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/k8s/ingress.yaml#L25-L35)), so k8s traffic goes through the same nginx. Read and send timeouts are 3600 s, and TLS comes from cert-manager ([`k8s/ingress.yaml:15-24`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/k8s/ingress.yaml#L15-L24)). Without a `proxy-body-size` annotation the controller's default applies, 1 MiB on ingress-nginx unless the cluster changes it (`A3`). #1 S2 adds the annotation.

### Vite Dev Proxy

[`frontend/vite.config.ts:24-36`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/vite.config.ts#L24-L36), dev only. Vite 5 picks the first key the path starts with, in this order:

| Prefix | Goes to |
| --- | --- |
| `/api/run` | runner |
| `/api/evaluate` | runner |
| `/api/execute` | runner |
| `/api/pdf` | runner |
| `/api/ai-coding` | runner |
| `/api/sd-practice` | runner |
| `/api/ai` | runner |
| `/api/share` | runner |
| `/api/take-home` | runner |
| `/api` | pocketbase, with `ws: true` |
| `/_` | pocketbase |

The runner target is `VITE_API_PROXY_TARGET` (default `http://runner:8000`) and the PocketBase target is `VITE_POCKETBASE_PROXY_TARGET` (default `http://pocketbase:8090`) ([`frontend/vite.config.ts:7-10`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/vite.config.ts#L7-L10)). Prefix matching is looser than nginx's exact and segment matches, so any path that starts with a runner prefix goes to the runner in dev. The dev server listens on `0.0.0.0:3000`, accepts the hosts in `VITE_DEV_ALLOWED_HOSTS`, and caps no body ([`frontend/vite.config.ts:38-49`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/frontend/vite.config.ts#L38-L49)). #1 S2 removes `/api/execute` here too. Its `/api` and `/_` entries forward PocketBase's admin surfaces in dev (`P1`); #1's nginx denials don't apply to Vite, which serves development only.

### Published Ports

| Stack | Service | Host port | Source |
| --- | --- | --- | --- |
| dev compose | pocketbase | `POCKETBASE_PORT`, default 8090 | [`docker-compose.yml:4-5`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/docker-compose.yml#L4-L5) |
| dev compose | runner | `RUNNER_PORT`, default 3099, to 8000 | [`docker-compose.yml:21-22`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/docker-compose.yml#L21-L22) |
| dev compose | frontend (Vite) | `FRONTEND_PORT`, default 3001, to 3000 | [`docker-compose.yml:51-52`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/docker-compose.yml#L51-L52) |
| dev compose | pdf-renderer | none (`expose: 4000`) | [`docker-compose.yml:43-44`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/docker-compose.yml#L43-L44) |
| prod compose | frontend (nginx) | `HTTP_PORT`, default 80 | [`docker-compose.prod.yml:83-84`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/docker-compose.prod.yml#L83-L84) |
| prod compose | pocketbase, pdf-renderer, runner | none | [`docker-compose.prod.yml:35-75`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/docker-compose.prod.yml#L35-L75) |
| k8s | frontend | the Ingress host | [`k8s/ingress.yaml:25-35`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/k8s/ingress.yaml#L25-L35) |
| k8s | pocketbase, runner | none; cluster-internal Services | [`k8s/runner.yaml:87-98`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/k8s/runner.yaml#L87-L98), [`k8s/pocketbase.yaml:74-85`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/k8s/pocketbase.yaml#L74-L85) |

Dev compose binds every host interface, so in dev the runner and PocketBase answer directly with no proxy in front.

### Planned Proxy Changes

What each leaf's current body adds. The leaf updates this table when it lands.

| Leaf | Change |
| --- | --- |
| #1 S2 | Removes `/api/execute` from nginx and Vite. Replaces `location /_/`, and adds 404s for `/api/rounds/admission/`, the admin API, and collection metadata ahead of `/api/`, as listed in #1's nginx section. Adds byte caps at nginx and the Ingress. |
| #3 | A 404 for `/api/rounds/execution/`, and `execution` in the nginx and Vite runner groups |
| #4 | A 404 for `/api/rounds/legacy-snapshots` |
| #11 S1 | `/r` and `/r/` locations that add the share response headers |
| #11 S2 | A 404 for `/api/rounds/share/`, which also covers #12's lookup route |
| #12 | `limit_req` on `/api/share/resolve`, and real client IP settings for k8s |
| #22 | A 404 for `/api/outbox/` |
| #54 | `processing` in the nginx runner group |
| #91 | An nginx entry for `/api/account-export/prepare` |
| #93 | `limit_req` on `/api/share/resolve/pdf` |
| #177 | None. `/api/rounds/demo/` stays public through `/api/`. |

#9 S4 checks #1's S2 denials in its harness.

## PocketBase

PocketBase 0.22.22 ([`pocketbase/Dockerfile:3`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/pocketbase/Dockerfile#L3)) serves the SPA's data straight through nginx's `/api/` and `/_/` locations. Per-collection rows (rules, hooks, exception owners, probe ids) live in `docs/security/account-scope.v1.json`, which #9 adds in its stage 1; this file doesn't copy them. The proxies forward these groups, inferred from PocketBase 0.22 and checked by #9 S4.

| Group | Auth today | After #1 S2 |
| --- | --- | --- |
| Records, auth (password, OAuth2, refresh, verification, reset), realtime, files, health | collection rules | open |
| Admin API (`/api/admins`, `/api/settings`, `/api/backups`, `/api/logs`) and collection metadata (`/api/collections`) | superuser | 404 at nginx |
| Admin UI (`/_/`) | superuser | 404 at nginx |

`62d4eae` has no hook routes. Its one hook is the signup check on `users` create ([`pocketbase/pb_hooks/main.pb.js:3-9`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/pocketbase/pb_hooks/main.pb.js#L3-L9)). #1 S3 adds `/api/rounds/admission/`, and #3, #4, #11, #12, #22, #54, #91, #93, and #177 add theirs. #91's export pages sit under #3's `/api/rounds/execution/` and #93's `POST /api/rounds/share/view` under #11's `/api/rounds/share/`, so those denials cover them. [server-writes.md](server-writes.md) lists each one's writer kind. The runner talks to `pocketbase:8090` directly ([`backend/app/pb_auth.py:29-33`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/app/pb_auth.py#L29-L33)), so the nginx 404s don't affect it.

## Asynchronous Entry Points

None at `62d4eae`. Nothing in `backend/` uses `BackgroundTasks`, startup or lifespan hooks, threads, executor pools, schedulers, queues, or websocket routes; [`backend/main.py:17-23`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/main.py#L17-L23) adds only `CORSMiddleware`. The sidecar has no timers or queues and launches its browser on the first render. `pocketbase/pb_hooks/` has no `routerAdd`, `cronAdd`, or `onBeforeServe`. Streaming responses run inside their request.

Two things run without a request, and neither takes caller input:

1. PocketBase applies every migration in `pocketbase/pb_migrations/` when it starts ([`pocketbase/Dockerfile:13-24`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/pocketbase/Dockerfile#L13-L24)). The first-admin migration reads `PB_ADMIN_*` ([`pocketbase/pb_migrations/1700000500_bootstrap_admin.js`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/pocketbase/pb_migrations/1700000500_bootstrap_admin.js)), and the demo migration seeds the demo account ([`pocketbase/pb_migrations/1700000600_demo_user.js`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/pocketbase/pb_migrations/1700000600_demo_user.js)).
2. The workflows in `.github/workflows/` build, test, and publish images on pushes, pull requests, and manual dispatch. They don't serve requests.

A leaf that adds one adds a row here: #3's worker claim loop, #22's dispatcher, #54's processing pool, #76's journal sweep, #91's export pool, and #177's `cronAdd` sweep.

## Differences From the Issue Body

1. The body's 34 counts application routes. FastAPI also serves the 4 framework routes above. No proxy forwards them and they start no work, so they stay outside admission like `/health`.
2. `k8s/` ships no `pdf-renderer` Deployment or Service ([`k8s/kustomization.yaml:6-11`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/k8s/kustomization.yaml#L6-L11)), but [`k8s/runner.yaml:57-58`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/k8s/runner.yaml#L57-L58) points `PDF_RENDERER_URL` at one, so both PDF routes return 502 on k8s as shipped. #6 and #7 already note this.
3. Two of the 23 routes on `current_user` return before calling it: `ats-ai` with `use_ai` false, and `enhance-projects` with an empty list. Neither starts work.
4. Besides nginx's 1 MiB default, the sidecar caps JSON at 5 MB. The Vite proxy and uvicorn cap nothing, and the Ingress has only its controller's default.
5. nginx and Vite both proxy `/api/execute`, which no runner route serves.
6. The body ties the 25-project `enhance-projects` cap to #72's and #73's caps, but those count provider calls and a project can make up to 11. This file treats the cap as #1's proposal and #73's 25-call lineage budget as its replacement, per #179's PR 8.

## Keeping This Current

This file is the `62d4eae` baseline. A PR that adds, removes, or changes an entry point, a proxy location, or a published port edits its row here and adds a line under Changes. #9 adds the PocketBase rows by reference, #172 S1 adds a `surface` column to the runner table and checks this file against a booted stack, and #177 adds its three demo routes.

### Changes

1. #1 S1 adds plumbing and enforces nothing new. The SPA sends the caller's bearer on every runner call, including `/api/run`, `/api/evaluate`, `/api/ai-coding/run-project`, the two chat streams, and `/api/pdf/render`, which now goes through `runnerFetch`. POST, PUT, PATCH, and DELETE calls carry one `Idempotency-Key` per user action. Every runner response carries `X-Correlation-Id`, the 32-hex id that `_request_id` now returns. The typed envelope `{"detail", "code", "correlation_id"}` is installed, but no route raises it until S2. The gate registry adds `ROUNDS_GATE_<NAME>` keys with defaults that keep this baseline, and `ROUNDS_GATE_SIGNUPS` joins the signup pair, which become its aliases. Two things now run without a request, and neither takes caller input: the runner reads its gates in a FastAPI lifespan hook, and PocketBase logs its gates in an `onAfterBootstrap` hook.
