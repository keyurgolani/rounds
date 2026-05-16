# Real World Problems — brief catalog

20 curated briefs for the `/take-home` track (formerly "Builder Problems").
Each brief conforms to the schema in
`docs/superpowers/specs/2026-05-15-real-world-and-ai-coding-catalog-design.md`.

**Distribution (locked):** 6 easy / 8 medium / 6 hard. Flavor counts:
6 services-apis / 5 data-etl / 5 concurrency-systems / 4 domain-modeled.
AI policy mix: 2 `off` (both at easy tier on domain-modeled problems),
6 `candidate-choice` (spread across medium/hard), 12 `on` (weighted toward
medium/hard).

**Languages:** every brief is solvable in Python or TypeScript at the
candidate's choice unless explicitly narrowed.

---

## Easy (6 briefs)

<!-- 1 services-apis · 2 data-etl · 1 concurrency-systems · 2 domain-modeled -->
<!-- AI policy: 2 off (on the 2 domain-modeled), 0 candidate-choice, 4 on -->

### E1. Library reservation conflict checker

- **slug:** `library-reservation-conflicts`
- **flavor:** `domain-modeled`
- **languages:** `[python, typescript]`
- **difficulty:** `easy`
- **time_budget_min:** 30
- **ai_policy:** `off`
- **topics:** `[scheduling, conflicts, domain-modeling, intervals]`
- **companies:** `[Meta, Airbnb]`

**Description.** Given a stream of reservation requests, accept the ones that don't overlap and reject the ones that do. Reflects the kind of small-scope domain-modeling problem Meta uses to probe "can you turn fuzzy product rules into clean code."

**Scenario.** A small library lets members reserve study rooms in 30-minute slots. Reservations arrive as `{room_id, member_id, start, end}` with ISO-8601 timestamps. Two reservations conflict when they share a room and their time intervals overlap — but touching at the boundary does NOT conflict, so `[10:00, 10:30)` and `[10:30, 11:00)` are both fine. Implement the accept-or-reject decision for an incoming reservation against an existing list. Use no AI assist: this problem is here for the pure-judgment signal of how you turn a fuzzy product rule into a precise function. Treat reservations as half-open intervals `[start, end)`; the overlap test is `incoming.start < existing.end && incoming.end > existing.start`.

**Tasks.**
- Implement `check_reservation(existing, incoming) -> {accepted: bool, reason: str}`.
- Handle the boundary case explicitly so touching intervals don't conflict.
- Surface a clear, specific `reason` on rejection (which existing reservation blocked it).
- Treat `start >= end` as invalid input with its own rejection reason.
- Stay under 50 lines of implementation code.

**Evaluation signal.**
- Boundary-case handling: did the candidate notice and document the touching-interval case?
- Error message quality: does "rejected" actually explain which reservation conflicted?
- Style: short, named helpers vs. one big nested conditional.
- Input-validation discipline: did they reject `start >= end` instead of silently accepting it?
- Test thinking: did the candidate add any of their own test cases beyond the visible ones?

### E2. Expense splitter for a small group

- **slug:** `expense-splitter-small-group`
- **flavor:** `domain-modeled`
- **languages:** `[python, typescript]`
- **difficulty:** `easy`
- **time_budget_min:** 30
- **ai_policy:** `off`
- **topics:** `[money, rounding, domain-modeling, fairness]`
- **companies:** `[Meta, Splitwise, Airbnb]`

**Description.** Given a list of expenses where one person pays and a set of people share the cost, compute how much each person owes whom. The trick is integer-cent arithmetic and remainder distribution, not graph algorithms.

**Scenario.** A group of housemates tracks shared expenses in the form `{payer, participants, amount_cents}` — for example, `{payer: "ada", participants: ["ada", "ben", "cleo"], amount_cents: 1000}` means Ada paid $10 and three people share it. The result should be a list of `{from, to, amount_cents}` debts owed back to each payer. Real money is integer cents, and naive division leaves a stray cent on uneven splits like `1000 / 3`. Use no AI assist: the point is to see how you handle remainder distribution and the "payer is also a participant" case without hand-waving.

**Tasks.**
- Implement `split_expenses(expenses) -> list[Debt]` where each `Debt` is `{from, to, amount_cents}`.
- Apportion in integer cents — distribute leftover cents deterministically (e.g., by sorted participant id).
- Exclude self-debts when the payer is also in `participants`.
- Aggregate debts into a single net `{from, to, amount_cents}` entry per ordered `(from, to)` pair across ALL expenses (not per-expense). If ada owes ben 300¢ from one expense and 200¢ from another, the result is one ada→ben entry of 500¢.
- Reject expenses where `participants` is empty or `amount_cents <= 0`.

**Evaluation signal.**
- Rounding discipline: did the candidate keep everything in integer cents, or float their way to a cent-off bug?
- Remainder distribution: is the leftover-cent rule explicit and deterministic, not "whoever's first in the dict"?
- Self-debt handling: did they remember the payer is usually also a participant?
- Style: did they model `Debt` cleanly or return loose tuples?
- Test thinking: did they add a `1000 / 3` style remainder test of their own?

### E3. Health-check endpoint with version and dependency status

- **slug:** `health-check-with-dependencies`
- **flavor:** `services-apis`
- **languages:** `[python, typescript]`
- **difficulty:** `easy`
- **time_budget_min:** 45
- **ai_policy:** `on`
- **topics:** `[http-api, health-check, observability, status-codes]`
- **companies:** `[Meta, Stripe, Datadog]`

**Description.** Implement `GET /healthz` that returns the service version and the status of each declared dependency, with the HTTP status code reflecting whether the service is actually serving traffic.

**Scenario.** Health endpoints look trivial and are repeatedly cited on Blind and interviewing.io as a 30-45 minute warm-up at Meta, Stripe, and observability shops like Datadog — because the obvious one-line "return 200 OK" answer is wrong. The starter has a service with two declared dependencies (a primary database and a cache) exposed as `check_db()` and `check_cache()` callables that may raise or return a latency-ms number. The endpoint must aggregate their states, surface them per-dependency, return 200 only when all hard dependencies are healthy, and return 503 otherwise. AI assist is allowed: the signal is whether you keep the AI from cargo-culting a generic boilerplate and miss the soft-vs-hard dependency distinction.

**Tasks.**
- Return JSON `{status, version, dependencies: [{name, status, latency_ms?, error?}]}`.
- Mark dependencies as `healthy`, `degraded`, or `unhealthy` based on call outcome.
- Return HTTP 200 when all hard dependencies are healthy; 503 if any hard dependency is unhealthy.
- Treat the cache as a soft dependency — its failure degrades but does not unheal the service. For dependencies returning a latency reading: `latency_ms > 200` → `degraded`; an exception or timeout → `unhealthy`. Successful and under 200ms → `healthy`. Soft dependencies (cache) downgrade the overall service to `degraded`; hard dependencies (database) `unhealthy` returns 503.
- Apply a per-dependency timeout (e.g., 500 ms) so a slow dep doesn't hang the health probe.
- Pull `version` from a build-time constant or env var, not a hard-coded string.

**Evaluation signal.**
- Status-code discipline: did the candidate avoid the "always 200" trap that breaks load-balancer health checks?
- Soft vs hard dependency: did they model the cache differently from the database?
- Timeout handling: does a hung dependency yield a 503 instead of hanging the request?
- AI-output review: did the candidate keep the AI from inventing fields like `uptime_seconds` that aren't actually measured?
- Versioning: is `version` sourced from build metadata, not a literal in the handler?

### E4. Normalize a CSV with inconsistent date formats

- **slug:** `csv-date-format-normalizer`
- **flavor:** `data-etl`
- **languages:** `[python, typescript]`
- **difficulty:** `easy`
- **time_budget_min:** 45
- **ai_policy:** `on`
- **topics:** `[csv, date-parsing, etl, data-quality]`
- **companies:** `[Meta, Stripe, Plaid]`

**Description.** A vendor CSV mixes `MM/DD/YYYY`, `DD-MM-YYYY`, `YYYY.MM.DD`, and a few free-form strings in the same `date` column. Emit a clean CSV with every date in ISO-8601 (`YYYY-MM-DD`) and a sidecar report of every row that couldn't be parsed.

**Scenario.** Date-format normalization is a staple of the Meta data-engineering and Stripe data-pipeline take-home rounds because it forces candidates to draw a line between "guess the format" and "fail loud." The starter reads a 500-row CSV from a vendor whose upstream system was a multi-team spreadsheet, so the same column has US-style and EU-style dates mixed in, plus the occasional `"unknown"` or `"03/15/24 (approx)"`. Visible tests check that unambiguous ISO dates pass through unchanged. The interesting territory is the ambiguous and the un-parseable rows. AI assist is allowed: this is a "use AI to write the parser, but you own the policy decisions" round.

**Tasks.**
- Read the input CSV and write a normalized CSV with the same columns plus dates rewritten as `YYYY-MM-DD`.
- Support `YYYY-MM-DD`, `MM/DD/YYYY`, `DD-MM-YYYY`, and `YYYY.MM.DD` formats explicitly.
- Resolve ambiguous strings like `03/04/2024` by picking ONE ambiguity policy and documenting it (a `README.md` note OR a CLI flag like `--date-order ymd|dmy|mdy`). The brief deliberately leaves the choice to you. Do not silently guess.
- Emit a sidecar `rejects.csv` with the original row plus a reason for every unparseable date.
- Never invent a date — unparseable rows go to rejects, not to the output.

**Evaluation signal.**
- Ambiguity policy: did the candidate explicitly pick a rule for `03/04/2024` and document it, or silently default?
- Failure mode: are rejects captured with a reason, or silently dropped?
- AI-output review: did the candidate audit the AI's regex for date formats like `2024.02.30` (invalid day)?
- Streaming vs in-memory: did they handle the file row-by-row, or eagerly load and hope it's small?
- Test thinking: did the candidate test a leap-year edge case (`02/29/2024` vs `02/29/2023`)?

### E5. Aggregate JSON-Lines logs by error code

- **slug:** `jsonl-log-aggregator-by-error-code`
- **flavor:** `data-etl`
- **languages:** `[python, typescript]`
- **difficulty:** `easy`
- **time_budget_min:** 45
- **ai_policy:** `on`
- **topics:** `[jsonl, log-aggregation, streaming, error-grouping]`
- **companies:** `[Meta, Datadog, Cloudflare]`

**Description.** A service emits structured JSON-Lines logs. Read the file (which won't fit in a comfortable amount of memory if you're not careful), group entries by `error_code`, and emit a sorted summary of count + first/last seen timestamp per code.

**Scenario.** Log aggregation by error code is a near-universal warm-up in the data and reliability tracks at Meta, Datadog, and Cloudflare — public Meta engineering blog posts on the move from `printf` debugging to structured logging cite "group by error code" as the first thing they wanted every newsfeed-team backend engineer to be able to do in an afternoon. The starter is a 100 MB-ish JSONL file where each line is `{ts, level, error_code?, message, ...}`. Logs without an `error_code` are skipped, malformed JSON lines are counted but not fatal. AI assist is allowed: the signal is whether the candidate streams the file and audits the AI's draft for the "load everything into a dict" trap.

**Tasks.**
- Stream the JSONL file line-by-line and aggregate by `error_code` without loading the whole file.
- Track `count`, `first_seen_ts`, `last_seen_ts` per code.
- Skip entries that have no `error_code` field; count malformed JSON lines into a separate `_malformed` bucket.
- Output a summary sorted by `count` descending, then `error_code` ascending as a stable tie-breaker.
- Print or write the summary as JSON so it's machine-readable downstream.

**Evaluation signal.**
- Streaming discipline: does the solution handle the file row-by-row, or did the candidate let the AI hand them `json.load(f)`?
- Robustness: do malformed lines fail the whole job or get counted?
- Tie-breaker: is the sort stable and deterministic across reruns?
- Schema thinking: did the candidate handle entries with no `error_code` field gracefully (skip without crashing, or count into `_malformed`)?
- AI-output review: did the candidate catch any silent type confusion (string vs int `error_code`) in the AI's grouping key?

### E6. Debounce function with trailing-edge semantics

- **slug:** `debounce-trailing-edge`
- **flavor:** `concurrency-systems`
- **languages:** `[python, typescript]`
- **difficulty:** `easy`
- **time_budget_min:** 60
- **ai_policy:** `on`
- **topics:** `[debounce, timers, concurrency, async]`
- **companies:** `[Meta, Figma, Notion]`

**Description.** Implement a `debounce(fn, wait_ms, options)` that delays calling `fn` until `wait_ms` have passed since the last invocation. Support a `trailing` option (default true) and a `max_wait_ms` cap so a busy stream still flushes on schedule.

**Scenario.** Debounce shows up in the warm-up round at Meta (newsfeed search-as-you-type), Figma (autosave), and Notion (collab cursor) because it sits in the sweet spot of "everyone has used lodash and thinks they understand it." The hidden complexity is the trailing-edge call and the `max_wait_ms` cap that prevents starvation on a busy event stream. Candidates who let the AI hand them the textbook 5-line debounce miss both. AI assist is allowed: the signal is whether the candidate adversarially tests the AI's draft against rapid back-to-back calls.

**Tasks.**
- Implement `debounce(fn, wait_ms, options)` returning a wrapped callable with the same call signature as `fn`.
- Cancel the prior pending invocation when called again within `wait_ms`.
- Honor `options.trailing` (default true) — fire `fn` with the most recent arguments after `wait_ms` of quiet.
- Honor `options.max_wait_ms` — guarantee `fn` fires at least once within that window even under sustained call pressure.
- Expose `cancel()` to drop any pending invocation and `flush()` to fire it immediately.
- Pass the most recent arguments to `fn`, not the first ones from the burst.

**Evaluation signal.**
- Trailing-edge correctness: does the wrapped function fire with the LAST arguments after a burst, not the first?
- Starvation prevention: does `max_wait_ms` actually fire mid-burst under sustained pressure?
- Cancel/flush semantics: are `cancel()` and `flush()` correct, idempotent, and don't double-fire? Both MUST be no-ops when no invocation is pending — never raise, never double-fire.
- Timer hygiene: are timers cleaned up so a long-lived debounced function doesn't leak handles?
- AI-output review: did the candidate test their debounce against rapid back-to-back calls and not just `setTimeout(...).then()` style happy-path checks?

---

## Medium (8 briefs)

<!-- 3 services-apis · 2 data-etl · 2 concurrency-systems · 1 domain-modeled -->
<!-- AI policy: 0 off, 3 candidate-choice, 5 on -->

### M1. Idempotency-key layer for a payment-like POST endpoint

- **slug:** `idempotency-key-payment-endpoint`
- **flavor:** `services-apis`
- **languages:** `[python, typescript]`
- **difficulty:** `medium`
- **time_budget_min:** 60
- **ai_policy:** `on`
- **topics:** `[http-api, idempotency, retries, payments, request-replay]`
- **companies:** `[Meta, Stripe, Shopify]`

**Description.** Wrap `POST /charges` with an idempotency-key layer so retries of the same request return the original response instead of double-charging, and replays with the same key but a different body are rejected as conflicts. Stripe's public idempotency docs are the canonical reference for the semantics.

**Scenario.** Your service exposes `POST /charges` with body `{amount_cents: int, currency: str, customer_id: str}` returning `201 {charge_id, status, amount_cents, currency, customer_id, created_at}`. Clients (mobile apps, cron jobs, partner integrations) retry aggressively on timeouts, and without an idempotency layer a single network blip becomes a duplicate charge. Callers pass an `Idempotency-Key` header on every retry of the same logical operation. The layer must store the first successful response keyed by `(customer_id, idempotency_key)`, replay it on subsequent retries with the same body, and reject mismatched bodies as conflicts — this is the exact contract Stripe documents. AI assist is allowed: the signal is whether you keep the AI from collapsing the "same key, different body" case into "just return the cached response."

**Tasks.**
- Implement middleware/decorator that accepts an optional `Idempotency-Key` header and short-circuits the handler when a stored response exists.
- On first call with a key: execute the handler, persist `{key, customer_id, request_body_hash, response_status, response_body, created_at}` atomically with the side effect, return 201.
- On retry with the same key AND matching `request_body_hash`: return the stored response with the same status code (do not re-run the handler, do not re-charge). Store the response regardless of status code (including 4xx from the charge handler); a stored 4xx replays on retry without re-attempting the charge.
- On retry with the same key AND a DIFFERENT body: return `409 {error: "idempotency_key_conflict", original_request_hash: str, conflict_at: iso8601_str}` without executing the handler.
- Treat keys as scoped to `customer_id` — same key from different customers is independent. Reject keys longer than 255 chars or containing whitespace with `400`.
- Apply a 24-hour TTL on stored idempotency records; expired records behave as if the key was never seen.

**Evaluation signal.**
- Replay correctness: does the second call with the same key+body actually skip the charge side effect, not just return a cached body while still charging?
- Conflict handling: does the candidate detect body mismatch and return 409, or silently replay the wrong response?
- Atomicity: is the response stored in the same transaction as the side effect, or is there a window where the charge happened but the response wasn't recorded?
- Scoping: did they scope keys per-customer instead of globally, where one tenant could collide with another?
- AI-output review: did the candidate notice if the AI used a non-cryptographic hash that collides, or stored the raw body in a way that leaks PII in logs?

### M2. Webhook receiver with retries and dead-letter queue

- **slug:** `webhook-receiver-retries-dlq`
- **flavor:** `services-apis`
- **languages:** `[python, typescript]`
- **difficulty:** `medium`
- **time_budget_min:** 60
- **ai_policy:** `on`
- **topics:** `[http-api, webhooks, retries, dlq, exponential-backoff]`
- **companies:** `[Meta, Stripe, GitHub]`

**Description.** Build the inbound side of a webhook system: verify signature, enqueue for async processing, retry failed deliveries with exponential backoff, and route permanently-failed events to a dead-letter queue. Mirrors the GitHub and Stripe webhook delivery contracts.

**Scenario.** Your service receives `POST /webhooks/inbound` events from a partner with body `{event_id: str, event_type: str, payload: object, sent_at: iso8601}` and headers `X-Signature: sha256=...` and `X-Timestamp: ...`. The HTTP handler must verify the HMAC signature, reject replays older than 5 minutes, persist the event, and return `202 Accepted` within 200ms — actual processing happens out-of-band. A worker pulls pending events and invokes a downstream `process(event)` function that may fail transiently (timeout, 5xx) or permanently (validation error, business-rule violation). Failed deliveries retry up to 5 times with exponential backoff and jitter, and events that exhaust retries land in a `dead_letter` table with the failure reason. AI assist is allowed: the signal is whether you keep the AI from conflating transient and permanent failures into one retry loop.

**Tasks.**
- Implement `POST /webhooks/inbound`: verify `X-Signature` (HMAC-SHA256 over `X-Timestamp + "." + raw_body` with a shared secret), reject as `401` on mismatch.
- Reject events whose `X-Timestamp` is more than 300 seconds from server time as `401 {error: "stale_signature"}`.
- Persist `{event_id, payload, received_at, status: "pending", attempts: 0}` and return `202` synchronously. Dedupe on `event_id` (a second delivery of the same event_id must not enqueue twice).
- Implement `process_pending()` worker step: pick the next pending event, call `process(event)`, on `TransientError` increment `attempts` and schedule retry with backoff `2^attempts seconds + random(0, 1) seconds` jitter, max 5 attempts, on `PermanentError` move directly to `dead_letter`.
- After 5 transient failures, move to `dead_letter` with `failure_reason` and the final exception.
- Expose `GET /webhooks/dead-letter` returning the list for operator inspection and `POST /webhooks/dead-letter/{id}/replay` that re-enqueues a single event with `attempts=0`.

**Evaluation signal.**
- Signature verification: constant-time comparison, not `==` on the digest, and timestamp included in the signed payload to prevent replay.
- Transient vs permanent distinction: does the worker actually retry on `TransientError` and skip retries on `PermanentError`, or does it retry everything?
- Backoff math: is the schedule `2^n + jitter` (or similar) and bounded, not unbounded or zero-jitter?
- Dedup on `event_id`: does a duplicate delivery from the partner result in one row, or N rows?
- AI-output review: did the candidate catch the AI handing them a fixed-interval retry loop, or a signature check that doesn't include the timestamp?

### M3. Feature-flag service with percentage rollout

- **slug:** `feature-flag-percentage-rollout`
- **flavor:** `services-apis`
- **languages:** `[python, typescript]`
- **difficulty:** `medium`
- **time_budget_min:** 60
- **ai_policy:** `candidate-choice`
- **topics:** `[feature-flags, hashing, rollout, http-api, determinism]`
- **companies:** `[Meta, LaunchDarkly, GitHub]`

**Description.** Implement an `is_enabled(flag, user_id, attributes)` evaluator backed by an HTTP API that supports boolean flags, percentage rollouts with stable bucketing, and rule-based targeting on user attributes. Meta's internal Gatekeeper and LaunchDarkly's public docs are the reference shape.

**Scenario.** Your service stores flag definitions like `{key, enabled, rollout_percentage, rules: [{attribute, op, value, variant}]}` and exposes `GET /flags/{key}/evaluate?user_id=...&attrs=...` returning `{enabled: bool, reason: str, variant?: str}`. Rules are evaluated in order; the first matching rule wins. If no rule matches, a deterministic hash of `(flag_key, user_id)` decides whether the user falls inside the rollout percentage. The same user must get the same answer on every call until the flag is changed, and shifting the percentage from 10% to 20% must keep the original 10% inside the new 20% (no churn). This is candidate-choice on AI because the design space — hash function, attribute schema, rule grammar — is exactly what we want to see the candidate own.

**Tasks.**
- Implement `GET /flags/{key}/evaluate` returning `{enabled, reason, variant?}` where `reason` is one of `disabled`, `rule_matched`, `in_rollout`, `out_of_rollout`, `flag_not_found`.
- Implement deterministic bucketing: `bucket(flag_key, user_id) -> int in [0, 99]`. The same `(flag, user)` MUST always return the same bucket; bumping rollout from 10 → 20 MUST keep every user from the 10% cohort inside the 20% cohort (i.e., the bucket is independent of the threshold).
- Support rules with operators (at minimum: `eq`, `in`, `gt`, `lt`). The first rule whose condition matches wins; its `variant` is returned regardless of `rollout_percentage`.
- Implement `PUT /flags/{key}` to upsert a flag and `GET /flags` to list them. Persist to whatever store you choose (in-memory is fine for the take-home; document the choice).
- Pick a hash function and document why: it must be fast, well-distributed, and stable across process restarts (so not Python's `hash()` of strings with `PYTHONHASHSEED=random`). Capture all design choices (hash function, attribute schema, flag-missing behavior, store choice) in a `DECISIONS.md`.
- Add a `/healthz` and basic structured logging on every evaluation for debuggability.

**Evaluation signal.**
- Bucket stability: does a 10→20% rollout keep the original 10% inside the new cohort, or does the candidate's hash scheme churn the assignment?
- Hash choice: did they pick something stable and documented (e.g., MurmurHash3, SHA-256 truncated, FNV) and explain it, or use a language built-in that breaks across runs?
- Rule precedence: is the "first matching rule wins" order explicit, with a test that flips two rules and shows the answer changes?
- Decision documentation: does `DECISIONS.md` actually capture the hash choice, attribute schema, and what happens when a flag is missing?
- AI-output review: if they used AI, did they catch the cargo-culted "shuffle users into 100 buckets at creation time" approach that doesn't survive process restarts?

### M4. Multi-format ingest into a canonical schema

- **slug:** `multi-format-ingest-canonical-schema`
- **flavor:** `data-etl`
- **languages:** `[python, typescript]`
- **difficulty:** `medium`
- **time_budget_min:** 60
- **ai_policy:** `candidate-choice`
- **topics:** `[etl, csv, jsonl, parquet, schema-normalization]`
- **companies:** `[Meta, Stripe, Snowflake]`

**Description.** Ingest order data arriving as CSV, JSONL, and Parquet from three different upstream vendors and emit a single canonical JSONL stream conforming to one shared schema. Field names, types, and unit conventions vary across vendors — pick a normalization policy and own it.

**Scenario.** Your data team is consolidating order events from three vendors: Vendor A drops daily CSVs with columns `order_id, cust, total_usd, ts`; Vendor B publishes JSONL with `{orderId, customerId, totalCents, createdAt}`; Vendor C writes Parquet with `id, customer, amount (decimal), event_time`. The canonical schema is `{order_id: str, customer_id: str, amount_cents: int, occurred_at: iso8601_utc}`. Currencies, decimal places, ID casing, and timestamp timezones are all inconsistent across vendors. The job runs nightly over per-vendor directories and emits a single `orders.canonical.jsonl` plus a `rejects.jsonl` sidecar. This is candidate-choice on AI because the heart of the problem is policy decisions — how to coerce floats to integer cents, what to do with naive timestamps, how to handle missing fields — and those decisions must be the candidate's, documented in a `DECISIONS.md`.

**Tasks.**
- Implement a CLI: `ingest --vendor {a,b,c} --input PATH --output orders.canonical.jsonl --rejects rejects.jsonl`.
- Per-vendor adapter that maps source fields to the canonical schema. Adapters are pluggable — a new vendor is one new file, not a fork of the main loop.
- Currency/precision policy: amounts MUST land as integer cents. Vendor A's float dollars and Vendor C's decimal must be converted without floating-point drift (use `Decimal` in Python, or a string-based path in TS). Document the rounding rule (banker's rounding vs half-up) in `DECISIONS.md`.
- Timestamp policy: emit `occurred_at` as ISO-8601 UTC with `Z` suffix. Decide explicitly what to do with naive (no-timezone) timestamps from Vendor A — reject? assume vendor-local TZ? — and document it.
- Reject (don't crash, don't invent) rows with missing required fields, unparseable amounts, invalid timestamps, or unknown/unsupported currency. Write them to `rejects.jsonl` with `{vendor, source_row, reason}`.
- Stream input where the format allows (CSV, JSONL); Parquet may be read in row-group chunks but MUST NOT require loading the whole file into memory for files larger than a row group.

**Evaluation signal.**
- Precision discipline: did the candidate keep amounts in integer cents end-to-end, or are there `float` ops that introduce a cent-off bug?
- Adapter shape: is there a clean Vendor → canonical boundary, or did they hand-roll three nearly-identical pipelines with copy-paste?
- Ambiguity policies: are the rounding rule and naive-timestamp policy explicit in `DECISIONS.md`, or implicit in the code where a reviewer has to reverse-engineer them?
- Reject pipeline: are rejects captured with vendor + reason + source row, or silently dropped to make the happy path look clean?
- AI-output review: if they used AI, did they catch the AI's `float(amount) * 100` round-trip that breaks on values like `19.99`?

### M5. Streaming aggregation of click events with windowed counts

- **slug:** `streaming-clicks-windowed-counts`
- **flavor:** `data-etl`
- **languages:** `[python, typescript]`
- **difficulty:** `medium`
- **time_budget_min:** 90
- **ai_policy:** `on`
- **topics:** `[streaming, windowing, event-time, watermarks, aggregation]`
- **companies:** `[Meta, Cloudflare, Datadog]`

**Description.** Consume a stream of click events and emit per-minute counts grouped by `campaign_id`, using event-time tumbling windows with a watermark that tolerates late-arriving events. Cloudflare's analytics pipeline and Meta's ads delivery telemetry are the public reference.

**Scenario.** Click events arrive as an iterator of `{click_id, campaign_id, user_id, event_time: iso8601_utc, received_at: iso8601_utc}` with `received_at >= event_time` but no upper bound on lateness — a mobile client offline for 20 minutes will batch-replay its clicks when it reconnects. The job must emit tumbling 1-minute windows keyed by `campaign_id` with `(window_start, window_end, campaign_id, count)`. Windows close when the watermark — the max `event_time` seen, minus a 2-minute slack — passes their end. Events arriving after their window has closed go to a `late_events.jsonl` sidecar, not into the closed window. AI assist is allowed: the signal is whether you keep the AI from using wall-clock time instead of event-time, which is the single most common bug in windowed aggregations.

**Tasks.**
- Implement `aggregate(events: Iterable[Event]) -> Iterable[WindowResult]` emitting `{window_start, window_end, campaign_id, count}` per closed window.
- Use EVENT-TIME tumbling 1-minute windows (`window_start = floor(event_time, 60s)`, `window_end = window_start + 60s`). Not wall-clock.
- Maintain a watermark = `max(event_time_seen) - 2 minutes`. A window closes when `watermark >= window_end`.
- On window close, emit results sorted by `(window_start, campaign_id)` for deterministic output.
- Route events whose window is already closed — i.e., the event's `window_end <= watermark` — to `late_events.jsonl` with `{event, reason: "after_watermark"}`. They MUST NOT mutate already-emitted window counts.
- Memory bound: at any time, only currently-open windows are in state. After a window closes, its per-campaign counters are evicted.

**Evaluation signal.**
- Event-time vs wall-clock: did the candidate window on `event_time` or did they let the AI use `datetime.now()`?
- Watermark semantics: do windows actually close on watermark progress, or do they linger forever because the candidate forgot to track the max?
- Late-event handling: are late events sidecarred with a reason, or do they silently mutate closed windows / get dropped without record?
- Memory profile: does state stay proportional to open windows, or does the candidate accumulate every event in a list "just in case"?
- AI-output review: did the candidate test with an out-of-order input stream and catch the off-by-one on `window_end` exclusivity?

### M6. Bounded worker pool with graceful shutdown

- **slug:** `bounded-worker-pool-graceful-shutdown`
- **flavor:** `concurrency-systems`
- **languages:** `[python, typescript]`
- **difficulty:** `medium`
- **time_budget_min:** 90
- **ai_policy:** `on`
- **topics:** `[concurrency, worker-pool, backpressure, graceful-shutdown, thread-safety]`
- **companies:** `[Meta, Cloudflare, Uber]`

**Description.** Implement a `WorkerPool(num_workers, max_queue)` that accepts tasks via `submit(task) -> Future`, applies backpressure when the queue is full, and supports a `shutdown(graceful: bool, timeout: float)` that drains in-flight work without losing results. This is the standard worker-pool interview at infra-heavy shops.

**Scenario.** Many services need a bounded in-process worker pool — log shippers, image processors, request fan-outs — that cap concurrency, refuse work when overloaded, and shut down cleanly without dropping in-flight tasks. The pool starts `num_workers` workers (threads in Python, worker contexts in TS); each pulls tasks from a bounded queue of size `max_queue`. `submit(task)` returns a Future-like handle that resolves with the task's return value or rejects with its exception. When the queue is full, `submit` blocks (or, with `submit_nowait`, raises `QueueFull`). AI assist is allowed: the signal is whether you keep the AI from inventing a "shutdown" that just calls `pool.join()` and leaks the queue.

**Tasks.**
- Implement `WorkerPool(num_workers: int, max_queue: int)` with methods `submit(fn, *args, **kwargs) -> Future`, `submit_nowait(...)` that raises `QueueFull`, and `shutdown(graceful: bool = True, timeout: float | None = None) -> bool`.
- The pool MUST be thread-safe: concurrent `submit` from multiple producer threads is safe, and `shutdown` from one thread while others are submitting is safe (post-shutdown `submit` raises `PoolClosed`).
- `submit` blocks when the queue is at `max_queue` until space frees up or the pool is shutdown. Document this backpressure behavior.
- `shutdown(graceful=True, timeout=T)`: stop accepting new submits, wait up to `T` seconds for queued + in-flight tasks to complete, return `True` if drained, `False` if timeout elapsed with work remaining. `timeout=None` means wait indefinitely; on `timeout` expiration with `graceful=True`, return False and leave in-flight tasks to complete in the background.
- `shutdown(graceful=False)`: stop accepting new submits, drain the queue (failing pending futures with `Cancelled`), set a `cancel_event` that long-running tasks can poll, and join workers with a hard timeout.
- Futures returned by `submit` MUST be resolvable from the caller: `.result(timeout)`, `.exception()`, `.cancelled()`. Test that exception in `fn` propagates to `.result()` raising it.

**Evaluation signal.**
- Thread-safety: did the candidate guard internal state with a lock or use a thread-safe queue, or is there a race between `submit` and `shutdown`?
- Graceful semantics: does `shutdown(graceful=True)` actually wait for in-flight work to finish, or does it `join` workers immediately and silently lose results?
- Backpressure: does `submit` block when the queue is full, or does it grow unboundedly because the candidate used an unbounded queue under the hood?
- Cancellation cooperation: is there a way for long-running tasks to notice `graceful=False` shutdown (a `cancel_event` they poll), or are they doomed to run to completion regardless?
- AI-output review: did the candidate notice the AI handing them `daemon=True` threads that get killed mid-task on interpreter shutdown, leaking partial state?

### M7. TTL cache with lazy expiry and size eviction

- **slug:** `ttl-cache-lazy-expiry-size-eviction`
- **flavor:** `concurrency-systems`
- **languages:** `[python, typescript]`
- **difficulty:** `medium`
- **time_budget_min:** 60
- **ai_policy:** `candidate-choice`
- **topics:** `[cache, ttl, eviction, lru, concurrency]`
- **companies:** `[Meta, Cloudflare, Redis]`

**Description.** Implement a `TTLCache(max_size)` with `get`, `put(key, value, ttl_seconds)`, and `delete`, where entries expire lazily on access and the cache evicts a chosen item when it grows past `max_size`. Candidate picks the eviction policy and the laziness vs. background-sweep tradeoff and documents both.

**Scenario.** Your team needs an in-process cache where some entries carry per-entry TTLs (auth tokens that expire in 5 minutes) and the total entry count is capped. Reads must be fast and must NOT return expired entries even if no background sweep has run. Writes may evict an existing entry when at capacity. Concurrent `get`/`put`/`delete` from multiple threads MUST not corrupt internal state. This is candidate-choice on AI because the policy decisions (which eviction strategy — LRU, LFU, FIFO; lazy-only vs hybrid background sweep; per-key locks vs single lock) are exactly the things we want the candidate to own and defend in `DECISIONS.md`.

**Tasks.**
- Implement `TTLCache(max_size: int)` with `get(key) -> value | None`, `put(key, value, ttl_seconds: float)`, `delete(key) -> bool`, `__len__()`, and `clear()`.
- Entries expire `ttl_seconds` after their `put`. `get` of an expired entry MUST return `None` AND remove the entry (lazy expiry), even if no background task has swept it.
- When `put` would push size past `max_size`, evict ONE entry per your chosen policy. Document the policy (LRU vs LFU vs FIFO vs random) and why in `DECISIONS.md`. Re-putting an existing key updates its value and TTL without consuming an additional slot.
- Choose and document whether you ALSO run a background sweep. If yes, the sweep cadence and how it interacts with the lock are part of the design. If no, justify that the lazy-only path is enough for the workload.
- Thread-safety: all operations are safe to call from multiple threads concurrently. State your locking strategy (single mutex, per-shard, per-key) in `DECISIONS.md`.
- Expose a `stats()` method returning `{size, hits, misses, expirations, evictions}` so a reviewer can verify behavior under load.

**Evaluation signal.**
- Lazy expiry correctness: does `get` of an expired key really return `None` AND drop the entry, even with no sweep configured?
- Eviction policy explicit and tested: is there a test that distinguishes the chosen policy from at least one other (e.g., for LRU, an entry promoted by `get` survives an eviction that would have caught it under FIFO)?
- Concurrency: does the candidate's lock actually cover the read-modify-write of `(check_expiry → evict → insert)`, or is there a window where two threads each evict a different entry?
- Decision documentation: does `DECISIONS.md` actually defend the eviction-policy choice and the sweep-vs-lazy-only tradeoff, or is it a one-liner?
- AI-output review: if they used AI, did they catch the typical `dict` + `time.time()` draft that has races between expiry check and read, or evicts mid-iteration over the keys?

### M8. Shopping cart with discounts, coupons, and tax precedence

- **slug:** `cart-discounts-coupons-tax-precedence`
- **flavor:** `domain-modeled`
- **languages:** `[python, typescript]`
- **difficulty:** `medium`
- **time_budget_min:** 90
- **ai_policy:** `on`
- **topics:** `[domain-modeling, pricing, money, rounding, precedence]`
- **companies:** `[Meta, Shopify, Stripe]`

**Description.** Compute a final cart total from line items, line-level percentage discounts, a cart-level coupon, and jurisdiction tax — with an explicit, defensible order of operations and integer-cent arithmetic throughout. Shopify's pricing engine and Stripe's tax calculation docs are the public reference for the precedence questions this surfaces.

**Scenario.** Your platform's pricing engine takes a cart `{items: [{sku, qty, unit_price_cents, line_discount_pct?}], coupon?: {type: "percent"|"fixed_cents", value, applies_to: "subtotal"|"taxable"}, tax_rate_bps: int}` and must emit a fully-itemized total: `{lines: [{sku, qty, gross_cents, line_discount_cents, net_cents}], subtotal_cents, coupon_cents, taxable_cents, tax_cents, total_cents}`. The precedence is fixed and must match every other engine in the industry: per-line discount → cart-level coupon → tax on the discounted base. Coupons that target `"taxable"` reduce the base on which tax is computed; coupons that target `"subtotal"` are applied AFTER tax. All math is integer cents; rounding happens once per stage, with the rule documented. AI assist is allowed: the signal is whether the candidate keeps the AI from helpfully reordering the precedence and double-discounting or under-taxing the cart.

**Tasks.**
- Implement `price_cart(cart) -> PricedCart` returning the fully-itemized breakdown above.
- Per-line: `gross_cents = qty * unit_price_cents`; `line_discount_cents = round(gross_cents * line_discount_pct / 100)`; `net_cents = gross_cents - line_discount_cents`. Round per line using your chosen rule (half-up vs banker's) and document it.
- Subtotal = sum of `net_cents`. Apply coupon to subtotal: if `type=percent`, `coupon_cents = round(subtotal * value / 10000)` (value in basis points to keep integer math); if `type=fixed_cents`, `coupon_cents = min(value, subtotal)` (coupon never makes the total negative).
- Compute `taxable_cents` per the coupon's `applies_to`: if `"taxable"`, `taxable_cents = subtotal - coupon_cents`; if `"subtotal"`, `taxable_cents = subtotal` (coupon does not reduce the tax base).
- `tax_cents = round(taxable_cents * tax_rate_bps / 10000)`. `total_cents = subtotal - coupon_cents + tax_cents` (the coupon shows up exactly once regardless of `applies_to`).
- Reject invalid carts (negative qty, unit_price_cents < 0, tax_rate_bps < 0, line_discount_pct outside [0,100]) with a clear domain error per field.

**Evaluation signal.**
- Precedence correctness: does `applies_to: "taxable"` actually reduce the tax base, and does `applies_to: "subtotal"` not? An off-by-one here understates or overstates tax and is the bug Shopify built whole test suites around.
- Money discipline: integer cents end-to-end with no `float` arithmetic in the hot path, rounding rule explicit and applied once per stage rather than ad hoc?
- Domain validation: are negative quantities, negative prices, and out-of-range discount percentages caught with field-level errors, or do they silently produce a nonsense total?
- Coupon clamp: does a fixed-cents coupon larger than the subtotal stop at the subtotal, or drive the total negative?
- AI-output review: did the candidate catch the AI rearranging the order (e.g., applying tax before the coupon) or distributing the coupon proportionally across lines in a way that double-rounds and breaks reconciliation?

---

## Hard (6 briefs)

<!-- 2 services-apis · 1 data-etl · 2 concurrency-systems · 1 domain-modeled -->
<!-- AI policy: 0 off, 3 candidate-choice, 3 on -->

### H1. URL shortener with custom slugs, expiry, and abuse limits

- **slug:** `url-shortener-custom-slugs-expiry`
- **flavor:** `services-apis`
- **languages:** `[python, typescript]`
- **difficulty:** `hard`
- **time_budget_min:** 180
- **ai_policy:** `on`
- **topics:** `[http-api, url-shortener, rate-limiting, analytics, collisions]`
- **companies:** `[Meta, Bitly, Cloudflare]`

**Description.** Build a URL shortener service with custom slug reservations, per-link expiry, click analytics, and per-creator abuse limits. The hard part isn't the redirect — it's the slug-collision race, the per-link counter under high read fan-out, and keeping the abuse limiter honest without making the create path slow.

**Scenario.** Your service exposes `POST /links` to create short links with body `{long_url: str, custom_slug?: str, expires_at?: iso8601_utc}` returning `201 {slug, short_url, long_url, expires_at?, created_at, creator_id}`, and `GET /{slug}` that 301-redirects to the long URL when the link exists and is unexpired. A `GET /links/{slug}/stats` endpoint returns `{slug, total_clicks, last_24h_clicks, last_click_at, top_referrers}`. Custom slugs must be globally unique and reserved atomically — two concurrent `POST /links` with the same `custom_slug` must result in exactly one success and one `409`. When `custom_slug` is omitted, the service generates a 7-char base62 slug; collisions on the auto-generated path retry up to 5 times with fresh slugs before returning `500`. Each `creator_id` is limited to 100 link creations per hour and 10 per minute (token-bucket); breaches return `429 {error: "rate_limited", retry_after_seconds: int}`. AI assist is allowed: the signal is whether you keep the AI from collapsing the slug-uniqueness guarantee into "check then insert" without a unique constraint backing it.

**Tasks.**
- Implement `POST /links`, `GET /{slug}` (301 redirect), `DELETE /links/{slug}` (creator-only), and `GET /links/{slug}/stats`.
- Enforce slug uniqueness via a database unique constraint on `slug` (not application-level "check then insert"). On constraint violation for a custom slug return `409 {error: "slug_taken"}`; for auto-generated slugs, retry up to 5 times then `500 {error: "slug_generation_exhausted"}`.
- Validate `long_url` with a strict allowlist of schemes (`http`, `https` only — reject `javascript:`, `data:`, `file:`). Validate `custom_slug` against `^[a-zA-Z0-9_-]{3,32}$` and reject reserved words (`api`, `links`, `healthz`, `admin`). Reject `expires_at` in the past with `400`.
- Implement per-`creator_id` token-bucket rate limiting: 10 creates/minute and 100 creates/hour. Use two buckets and require BOTH to have a token. Return `429` with `retry_after_seconds` reflecting the tighter bucket.
- Record clicks asynchronously: on `GET /{slug}` enqueue `{slug, ts, referrer, user_agent_hash}` to a buffered writer (in-process queue is fine for the take-home; document the durability tradeoff). The redirect MUST NOT block on the analytics write. Stats are read from the aggregated store.
- Expired links return `410 Gone` (not `404`) on `GET /{slug}` and on stats. Document why a deleted link returns `404` but an expired link returns `410`.
- (Stretch) Add a `/links/{slug}/qr` endpoint that returns a PNG QR code, cached by slug+size.

**Evaluation signal.**
- Slug-uniqueness guarantee: is uniqueness enforced by a unique constraint at the storage layer, or by an application-level read-then-write that has a TOCTOU race under concurrent customs?
- Rate limiter correctness: do BOTH the per-minute and per-hour buckets apply, and does `retry_after_seconds` reflect the tighter of the two? A burst of 11 creates in 10 seconds from the same creator should yield exactly 10 `201`s and 1 `429`.
- URL validation: does the candidate reject `javascript:` and `data:` schemes, or did the AI hand them a permissive parser that opens a stored-XSS via redirect?
- Async analytics: does the redirect path stay fast (sub-10ms median) by enqueueing, or does the candidate write to the analytics store synchronously and tank P99?
- Status-code discipline: `410` for expired vs `404` for deleted, `301` (not `302`) for the redirect so browsers cache it, `409` (not `400`) for slug conflict?
- AI-output review: did the candidate notice if the AI's slug generator used `random.choice` without a CSPRNG, letting an attacker enumerate someone else's about-to-be-created slug?

### H2. Pagination cursor service with stable ordering under inserts

- **slug:** `pagination-cursor-stable-ordering`
- **flavor:** `services-apis`
- **languages:** `[python, typescript]`
- **difficulty:** `hard`
- **time_budget_min:** 120
- **ai_policy:** `candidate-choice`
- **topics:** `[http-api, pagination, cursors, ordering, consistency]`
- **companies:** `[Meta, Stripe, Shopify]`

**Description.** Build a cursor-based pagination service over a feed-style resource where inserts happen continuously. Stable ordering, no duplicates, no skipped items across page boundaries — even when new rows land mid-traversal. Stripe's API pagination docs and Meta's Graph API cursor design are the canonical references.

**Scenario.** Your service exposes `GET /feed?cursor=<opaque>&limit=N&direction=forward|backward` returning `{items: [...], next_cursor?: str, prev_cursor?: str, has_more: bool}`. Rows have `(id: uuid, created_at: timestamptz, payload: jsonb)`, sorted primarily by `created_at DESC` then `id DESC` as a tiebreaker. Limit is between 1 and 100; default 25. A client walking the feed from cursor=null to the end must observe each row exactly once even though new rows are being inserted at the head between page fetches, and the order seen across pages must be totally consistent (no row appears on page 3 that should have appeared on page 1). Cursors are opaque to clients but must survive a server restart (no in-memory cursor table). This is candidate-choice on AI because the design decisions — cursor encoding, what "stable" means under inserts, how to handle deleted rows mid-walk — are exactly what we want the candidate to own and defend in `DECISIONS.md`.

**Tasks.**
- Implement `GET /feed` accepting `cursor` (optional, opaque), `limit` (1-100, default 25), `direction` (`forward` for older, `backward` for newer; default `forward`). Return `items`, `next_cursor`, `prev_cursor`, `has_more`.
- Encode cursors as a signed/encoded representation of the sort-key tuple `(created_at, id)` of the last row on the page — base64url of `{"c": "2026-05-15T10:00:00Z", "i": "uuid", "d": "forward"}` is fine. Cursors MUST be parseable after a process restart (no server-side cursor state).
- Query semantics: forward page uses `WHERE (created_at, id) < (cursor.c, cursor.i) ORDER BY created_at DESC, id DESC LIMIT N+1`. The `+1` row is used to populate `has_more` without re-querying. Backward direction is symmetric. Deleted-row cursors still work because the inequality is on `(created_at, id)`, not row existence; test this explicitly.
- Guarantee no duplicates across consecutive pages and no skipped rows when new inserts arrive between page fetches. A row inserted between page 1 and page 2 with a `created_at` newer than page 1's last row MUST NOT appear on page 2 (it's "before" the cursor in DESC order). Validate this with an explicit test.
- Reject malformed/tampered cursors with `400 {error: "invalid_cursor"}`. Cursors should be signed (HMAC over the payload with a server-side secret) or, alternatively, validated on parse. Document the choice.
- Document all design decisions in `DECISIONS.md`: cursor encoding format, signing vs validation-only, tiebreaker column choice, what happens on `limit > 100`, behavior of `cursor` with `direction=backward` from the very first page, and how the API surfaces a deleted-row scenario to the client.
- (Stretch) Add a `total_count` field guarded by a `?include_count=true` flag and explain in `DECISIONS.md` why you would NOT enable it by default on a high-traffic feed.

**Evaluation signal.**
- Tiebreaker discipline: does the sort use `(created_at, id)` and the cursor encode BOTH, or did the candidate use only `created_at` and accept duplicate rows on millisecond ties?
- Insertion stability: under continuous inserts, do consecutive pages contain disjoint rows, or does an insert between pages shift the boundary and cause a row to appear on two pages?
- Cursor opacity & forgery: is the cursor opaque to clients and tamper-resistant (signed or validated), or can a client craft a cursor that exposes future/private rows?
- Restart resilience: does the cursor survive a server restart, or did the candidate store cursor state in process memory?
- `DECISIONS.md` quality: does it actually justify the chosen tiebreaker, signing approach, and `limit` cap with reasoning, or is it a list of headers with no defense?
- AI-output review: if they used AI, did they catch the OFFSET-based pagination draft that breaks under inserts (rows shift by N as new ones land at the head)?

### H3. Backfill pipeline with idempotent re-runs and dedup keys

- **slug:** `backfill-pipeline-idempotent-dedup`
- **flavor:** `data-etl`
- **languages:** `[python, typescript]`
- **difficulty:** `hard`
- **time_budget_min:** 180
- **ai_policy:** `on`
- **topics:** `[etl, backfill, idempotency, dedup, checkpointing]`
- **companies:** `[Meta, Stripe, Airbnb]`

**Description.** Build a backfill pipeline that walks a historical date range, fetches per-day source records, transforms them, and upserts into a target store such that re-running any subset of dates produces the same target state. Stripe's public engineering posts on backfills and Airbnb's data-platform writeups on Airflow idempotency are the public reference for the pattern this brief targets.

**Scenario.** Your team needs to backfill the last 90 days of `orders` from a source API into an analytics warehouse table. The CLI is `backfill --start 2026-02-15 --end 2026-05-15 --concurrency 8 [--dry-run] [--days 2026-04-01,2026-04-02]`. The pipeline divides the range into per-day shards, fetches `GET /source/orders?date=YYYY-MM-DD&page=...` (paginated, may return up to ~50k records per day), transforms each record to the target schema, and upserts into `target.orders` keyed by `(source_id)`. Re-running the same date range MUST produce byte-identical target state — no duplicate rows, no churned `updated_at` on rows whose payloads didn't change. The job must checkpoint progress so a crash mid-backfill resumes where it left off without re-fetching completed days. AI assist is allowed: the signal is whether you keep the AI from giving you an `INSERT` that double-counts on every re-run instead of an idempotent upsert keyed on the right column.

**Tasks.**
- Implement the CLI with the flags above. `--dry-run` reports per-day record counts and intended target writes without committing. `--days A,B,C` runs only those specific dates, ignoring `--start/--end`. Source pagination tokens are NOT stable across re-runs; resuming a failed day means re-fetching all pages for that date from the beginning.
- Per-day shard: fetch all pages from source, transform, write a per-shard `staging.orders_YYYYMMDD` table (or equivalent intermediate), then in a single transaction MERGE/UPSERT into `target.orders` keyed on `source_id`. Document the choice of staging-then-merge vs streaming-merge in `README.md`.
- Idempotency contract: re-running a date that completed successfully produces no changed rows in `target.orders` (verify with a content hash per row: `updated_at` only bumps when `content_hash` changes). The dedup key is `source_id`; the change-detection key is `sha256(canonical_json(record))`.
- Checkpointing: maintain a `backfill_runs(run_id, date, status, rows_in, rows_out, started_at, finished_at, last_error?)` table. A day is in one of `pending|in_progress|completed|failed`. Completed days are skipped on re-run unless `--force` is passed. In-progress days that crashed must be detectable and retried (e.g., `in_progress` with a stale `started_at` > 30 min). On completion, emit a structured run summary `{run_id, started_at, finished_at, days_total, days_completed, days_failed, rows_processed, rows_inserted, rows_updated, rows_rejected}` to stdout and to `backfill_runs`.
- Concurrency: process up to `--concurrency` days in parallel (worker pool). Each worker owns its date shard end-to-end. The MERGE into `target.orders` must be safe under concurrent shards because shards never overlap on `source_id` (assert this invariant with a `(date, source_id)` constraint on staging).
- Failure handling: a per-day transient failure (network, 5xx) retries with exponential backoff up to 5 times. A per-record validation failure routes to `rejects.YYYYMMDD.jsonl` with `{source_record, reason}` and does NOT fail the whole day. A schema-incompatible response from the source (e.g., a new required field) fails the day and marks it `failed`.
- (Stretch) Add a `--verify` mode that re-fetches a sample of completed days and asserts target hashes match, surfacing silent upstream changes that didn't trigger an `updated_at` correctly.

**Evaluation signal.**
- Idempotency proof: does re-running a completed day touch zero rows (per `updated_at`), or does the candidate's "upsert" bump `updated_at` on every row even when nothing changed?
- Dedup key correctness: is the unique key on `source_id` (the real source identity) or on a derived field like `(date, row_index)` that breaks if pagination order shifts?
- Checkpoint recovery: does a kill -9 mid-backfill leave the system in a recoverable state, or does it leave a day stuck in `in_progress` with no detection?
- Shard isolation: can two parallel shards corrupt each other (e.g., both trying to merge into a shared staging table)? Are shards content-isolated by date?
- Reject vs fail discipline: is a single bad record a rejected row (continue the day) or a failed day (abort), and is that line drawn explicitly?
- AI-output review: did the candidate catch the AI handing them `INSERT INTO target ...` instead of `INSERT ... ON CONFLICT (source_id) DO UPDATE SET ... WHERE content_hash IS DISTINCT FROM EXCLUDED.content_hash`? The latter is what makes re-runs free of churn.

### H4. Distributed rate limiter with Redis-flavored interface

- **slug:** `distributed-rate-limiter-redis-interface`
- **flavor:** `concurrency-systems`
- **languages:** `[python, typescript]`
- **difficulty:** `hard`
- **time_budget_min:** 120
- **ai_policy:** `on`
- **topics:** `[rate-limiting, token-bucket, distributed-systems, redis, atomicity]`
- **companies:** `[Meta, Cloudflare, Stripe]`

**Description.** Implement a distributed token-bucket rate limiter that runs against an in-memory backend AND a Redis-flavored interface (Lua scripting or `MULTI`/`EXEC`-style atomic ops). Allow exactly N tokens per second per key with burst capacity B, atomic decrements across many limiter clients, and correct behavior when system clocks drift. Cloudflare's public rate-limiter posts and Stripe's published Redis-Lua bucket algorithm are the reference shape.

**Scenario.** Your platform's API edge needs a rate limiter that survives across multiple stateless app servers — so the bucket state cannot live in any single process. Implement `RateLimiter(backend, rate_per_sec, burst)` with `allow(key) -> {allowed: bool, tokens_remaining: float, retry_after_ms: int}`. The limiter must be backed by EITHER an in-memory store (for unit tests / single-process mode) OR a Redis-flavored client exposing `eval(script, keys, args) -> Any` and `pipeline()` for atomic multi-op. Token-bucket semantics: each `key` has a bucket of capacity `burst`; tokens refill at `rate_per_sec`; `allow` consumes one token if available, else rejects with `retry_after_ms` = time to next token. The fetch-modify-write of `(last_refill_ts, tokens)` MUST be atomic across all limiter clients — no double-spend. AI assist is allowed: the signal is whether you keep the AI from giving you a `GET key; DECR key; SET key` shape that has a TOCTOU race between two clients hitting the same bucket.

**Tasks.**
- Implement `RateLimiter(backend: Backend, rate_per_sec: float, burst: int)` and `allow(key: str) -> AllowResult`. Define a `Backend` protocol that both the in-memory and Redis-flavored impls satisfy: `eval(script, keys, args) -> Any`, `time() -> (sec, microsec)`, `pipeline()`.
- The token-bucket update MUST be atomic at the backend. For the Redis-flavored backend: implement as a single Lua script that calls `TIME` for the current timestamp, reads `{last_refill_ts, tokens}`, computes refill, decides allow/deny, writes the new state, and returns the decision — all in one server-side evaluation (document why client wall-clock is wrong: skew, NTP jumps). For the in-memory backend: a single lock around the read-modify-write using a monotonic clock seeded by the backend.
- Refill formula: `tokens = min(burst, tokens + (now - last_refill_ts) * rate_per_sec)`. If `tokens >= 1`, deduct one and return `{allowed: true, tokens_remaining: tokens-1, retry_after_ms: 0}`. Else `{allowed: false, tokens_remaining: tokens, retry_after_ms: ceil((1 - tokens) / rate_per_sec * 1000)}`.
- TTL: each bucket key MUST have a TTL of at least `burst / rate_per_sec * 2` seconds. Idle keys expire so the keyspace doesn't grow unboundedly under one-shot user IDs.
- Concurrency proof: write a test that spawns N concurrent `allow(key)` calls against the same key with `rate=10/s, burst=10` and asserts EXACTLY 10 are allowed (not 9, not 11). This must pass under both backends.
- Failure mode: on backend unavailability (Redis down), the limiter must either fail-open (allow, log a warning, return `tokens_remaining: -1` as a sentinel) OR fail-closed (deny, return `503`). Pick one and document why; the choice is a tradeoff between availability and abuse exposure.
- (Stretch) Add a `cost: int = 1` parameter to `allow` to support weighted limits (a "heavy" request costs 5 tokens). The atomic update generalizes trivially; show this in a test.

**Evaluation signal.**
- Atomicity proof: under 100 concurrent `allow(key)` calls with `burst=10`, are exactly 10 allowed across both backends? Or does the Redis path leak extra allows because the candidate used `GET`/`SET` instead of a Lua script?
- Clock-source correctness: does the refill use the backend's clock (Redis `TIME`, in-memory monotonic) or the client's wall clock that can jump under NTP correction?
- TTL hygiene: do idle keys eventually expire from the backend, or did the candidate omit the TTL and leak entries on per-user keys?
- Failure-mode choice: did the candidate make an explicit fail-open vs fail-closed decision and defend it, or does Redis timeout silently turn into "allow forever"?
- Token-debt vs strict-positive: does the algorithm allow negative balances ("over-spend") or strictly require `tokens >= 1` before consuming? Either is defensible; the candidate must be explicit.
- AI-output review: did the candidate catch the AI's `if get(key) > 0: decr(key)` draft that has a TOCTOU race, or the formula that uses `rate_per_sec * (now - last)` without bounding to `burst`?

### H5. Leader-election simulator with bounded-staleness reads

- **slug:** `leader-election-simulator-bounded-staleness`
- **flavor:** `concurrency-systems`
- **languages:** `[python, typescript]`
- **difficulty:** `hard`
- **time_budget_min:** 120
- **ai_policy:** `candidate-choice`
- **topics:** `[distributed-systems, leader-election, raft, consensus, bounded-staleness]`
- **companies:** `[Meta, etcd, MongoDB]`

**Description.** Build a single-process simulator of a Raft-style leader-election cluster that exposes `read(key, consistency)` and `write(key, value)` operations and offers `linearizable` or `bounded_staleness(max_lag_ms)` reads from followers. The hard part is correctly modeling election terms, vote splitting, and the staleness guarantee under simulated network delay. References: Raft paper §3, etcd's `Linearizable` vs `Serializable` read modes, MongoDB's `readConcern: "majority"` / `maxStalenessSeconds`.

**Scenario.** Your simulator instantiates `Cluster(n_nodes, election_timeout_ms_range, heartbeat_interval_ms, network_delay_ms_range)` with `n_nodes` in {3, 5, 7}. Each node has a state machine `dict[str, str]` and a Raft-ish log of `{term, index, op}` entries. Nodes communicate via in-process channels with simulated jitter drawn from `network_delay_ms_range`. The cluster exposes `client.write(key, value)` (always goes to the leader; non-leader nodes reply with `NotLeader{hint}`), `client.read(key, consistency)` where `consistency ∈ {linearizable, bounded_staleness}` — `linearizable` reads guarantee the value returned reflects all writes acknowledged before the read started. `bounded_staleness(max_lag_ms)` may serve from any follower whose `last_applied_ts` is within `max_lag_ms` of the leader's commit timestamp; if no follower qualifies, the call falls back to the leader. The simulator must support fault injection: `cluster.partition([{a,b}, {c,d,e}])` splits the network; `cluster.kill(node_id)` stops a node; `cluster.heal()` restores connectivity.

**Tasks.**
- Implement `Cluster(n_nodes, election_timeout_ms_range=(150, 300), heartbeat_interval_ms=50, network_delay_ms_range=(5, 30))` with `client.write`, `client.read`, `partition`, `kill`, `heal`, and `step()` (advance simulator one tick). The simulator must be deterministic given a seed: `Cluster(..., seed=42)` reproduces the same election sequence.
- Implement leader election and log replication: nodes start as followers; on election timeout a follower becomes candidate, increments term, votes for self, and requests votes — a majority wins; a node that observes a higher term immediately reverts to follower. Implement randomized election timeouts to avoid split-vote livelock (split votes must resolve within a bounded number of rounds in tests). Leader receives writes, appends to its log, replicates to followers via `AppendEntries`, commits when a majority acks, then applies to state machine; followers reject `AppendEntries` from a lower term or mismatched `prevLogIndex/prevLogTerm`.
- Implement `bounded_staleness(max_lag_ms)` reads: each follower tracks `last_applied_commit_ts` (the leader's commit timestamp of the last entry the follower applied). On a follower-served read, if `now - last_applied_commit_ts <= max_lag_ms`, serve from the follower's state machine; else, forward to the leader. Define `now` and `last_applied_commit_ts` against the simulator's logical clock, not wall clock — document this in `DECISIONS.md`.
- Partition behavior: under `partition([{minority}, {majority}])`, the majority side must elect (or retain) a leader within a bounded number of ticks; the minority side must NOT have a committed leader (its leader, if any, cannot achieve majority and can't commit new writes). Writes to the minority side return `NotLeader{hint}` or `NoQuorum`. Heal restores convergence.
- `DECISIONS.md` must explicitly document: choice of linearizable read strategy (leader-only vs ReadIndex vs lease-based) and why; how staleness is measured (clock source, leader-commit-ts propagation); what happens on a network partition for a `bounded_staleness` read that hits the minority side; the tradeoff between `network_delay_ms_range` and `heartbeat_interval_ms` for liveness.
- Test suite must include: split-vote convergence, leader failover under `kill`, partition + heal correctness (no diverged committed state), `bounded_staleness` actually returning slightly stale data under simulated lag, and `linearizable` reads never returning a value that hadn't been committed before the read started.
- (Stretch) Add log compaction (snapshot at commit index N, truncate prefix, ship snapshot to a lagging follower on `AppendEntries` failure with `prevLogIndex < snapshot.index`).

**Evaluation signal.**
- Election correctness: do split votes resolve, and does a higher-term observation correctly demote a stale leader? Or does the candidate's election livelock or have two leaders in the same term?
- Bounded-staleness honesty: does `bounded_staleness(max_lag_ms=50)` actually serve from followers within the threshold AND fall back to the leader otherwise, or does it always go to the leader (making the guarantee vacuous) or always go to followers (violating the bound)?
- Partition safety: under a partition, can the minority side accept and commit a write? It must not. Is there a test that asserts this explicitly?
- Determinism: does the simulator reproduce the same election sequence under the same seed, or are there non-deterministic ordering bugs that make the tests flaky?
- `DECISIONS.md` rigor: does it actually defend the linearizable-read strategy with reference to a published design (Raft §6.4 ReadIndex, leader-lease), or is it hand-waved?
- AI-output review: if they used AI, did they catch the omission of the term-increment + persistence rule (a node must increment its term and persist before voting, else split brain on restart), or the "always serve linearizable from leader's local state without confirming leadership" bug?

### H6. Subscription billing engine with proration and plan changes

- **slug:** `subscription-billing-proration-plan-changes`
- **flavor:** `domain-modeled`
- **languages:** `[python, typescript]`
- **difficulty:** `hard`
- **time_budget_min:** 180
- **ai_policy:** `candidate-choice`
- **topics:** `[domain-modeling, billing, proration, subscriptions, money]`
- **companies:** `[Meta, Stripe, Zuora]`

**Description.** Build a subscription billing engine that computes the next invoice for a customer who may upgrade, downgrade, cancel, or pause mid-cycle. The engine must handle proration (credit unused time on the old plan, charge for used time on the new plan), trial periods, and plan-change effective-date policies. Stripe's billing API docs (proration_behavior, billing_cycle_anchor, schedule) and Zuora's public ratings engine are the reference shape.

**Scenario.** Your engine processes `SubscriptionEvent` records like `{customer_id, type: "create"|"upgrade"|"downgrade"|"cancel"|"pause"|"resume"|"renew", plan_id, effective_at: iso8601_utc, ...}` against a customer's subscription history. Plans are `{plan_id, price_cents_per_period, period_unit: "month"|"year", trial_days?}`. A customer on plan A ($30/mo, billed 2026-05-01 → 2026-06-01) who upgrades to plan B ($90/mo) effective 2026-05-15 owes: credit for 17 unused days on A (17/31 × $30 = $16.45) and charge for 17 days on B (17/31 × $90 = $49.35), netted into the next invoice or invoiced immediately depending on the chosen policy. Downgrades may apply at end-of-cycle (default) or immediately (with credit). Output is `compute_invoice(customer_id, as_of: iso8601_utc) -> Invoice` with fully-itemized lines `{description, period_start, period_end, plan_id, amount_cents}`. All math is integer cents; rounding is per-line and the rule is documented.

**Tasks.**
- Implement `compute_invoice(customer_id, as_of) -> Invoice` with `Invoice = {customer_id, period_start, period_end, lines: [...], subtotal_cents, total_cents, currency}`. `lines` MUST itemize every proration credit and charge separately so a customer-facing receipt can render them.
- Implement proration math in integer cents using `Decimal` (Python) or a fixed-point integer pipeline (TS). For a partial period spanning `p` days out of `n` in the billing period, charge `round(price * p / n)`. Document the rounding rule (banker's vs half-up) in `DECISIONS.md`; rounding happens exactly once per line.
- Handle plan-change effective dates: upgrades are effective `immediately` by default (immediate credit + immediate charge on next invoice). Downgrades are effective at `end_of_cycle` by default (no proration, switch on renewal). Both can be overridden per-event; document the override surface in `DECISIONS.md`.
- Handle cancellations: `type=cancel` with `effective_at=immediately` produces a credit for unused time on the current invoice; `effective_at=end_of_cycle` produces no proration but stops auto-renewal. Distinguish these in the invoice and in `DECISIONS.md`.
- Handle trials and billing-cycle alignment: a customer in `trial_days` charges $0 until trial end, then a full first invoice; plan changes during trial extend (not reset) the trial unless the new plan has no trial. On mid-cycle upgrade, the cycle anchor stays on the original day by default (Stripe's behavior); document the override path and test both aligned and misaligned cycles (including a Feb cycle that exercises calendar-month math).
- `DECISIONS.md` MUST cover: proration formula and rounding rule, plan-change effective-date defaults and override surface, trial-during-plan-change policy, billing-cycle anchor policy, what "a month" means (30 days vs calendar-month vs actual days in source month) and the Feb consequence, currency handling (single-currency assumption ok; state it), pause/resume semantics. Test suite must include: same-day upgrade (no proration since p=0), exact mid-cycle upgrade (verify cent arithmetic), downgrade with `end_of_cycle` (no immediate invoice change), cancel mid-cycle with credit, and trial-to-paid transition.
- (Stretch) Add support for usage-based add-ons (a metered `{metered_unit, unit_price_cents}` line item summed from a usage feed) integrated into the same invoice.

**Evaluation signal.**
- Money discipline: integer cents end-to-end (`Decimal` or fixed-point), one rounding event per line, no `float * price / days` arithmetic that introduces a sub-cent drift?
- Proration correctness: for a known upgrade scenario (30→90 mid-month), do the credit and charge lines net to the expected amount within ±1 cent due to documented rounding, or do they reconcile to nonsense?
- Plan-change policy explicitness: are upgrade-immediate vs downgrade-end-of-cycle defaults stated, with the override path documented, or buried in code?
- `DECISIONS.md` rigor: does it actually defend the calendar-month definition, the rounding rule, the trial-during-change behavior, and the cycle-anchor choice, or is it a list of headers?
- Trial handling: does the engine charge $0 during trial AND correctly resume on trial end, including when a plan change happened during the trial?
- AI-output review: if they used AI, did they catch the AI's `price * (now - period_start) / (period_end - period_start)` formula that uses `datetime` deltas without aligning to UTC and breaks on DST-affected cycles? Or the "credit the old plan AND keep charging it" bug where the new charge isn't fully proration-aware?
