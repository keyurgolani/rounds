# AI Assisted Coding — brief catalog

20 curated briefs for the `/ai-coding` track. Each brief conforms to the
schema in `docs/superpowers/specs/2026-05-15-real-world-and-ai-coding-catalog-design.md`.

**Distribution (locked):** 6 easy / 8 medium / 6 hard. Flavor counts:
4 audit / 5 drive / 5 debug-refactor / 3 prompt-spec / 3 mini-app.

**Languages:** every brief is solvable in Python or TypeScript at the
candidate's choice unless explicitly narrowed.

---

## Easy (6 briefs)

<!-- 1 audit · 2 drive · 1 debug-refactor · 1 prompt-spec · 1 mini-app -->

### E1. Hallucinated HTTP client method

- **slug:** `hallucinated-http-client`
- **flavor:** `audit`
- **languages:** `[python, typescript]`
- **difficulty:** `easy`
- **topics:** `[ai-output-review, http-client, library-knowledge]`
- **companies:** `[Meta, Shopify]`

**Description.** An AI assistant wrote a small function that fetches a JSON payload from an internal service. The visible tests pass against a stub. Find what's wrong before it ships against the real service.

**Scenario.** This pattern is widely reported in AI-assisted interview write-ups: an LLM produces code that calls a plausible-looking method that doesn't actually exist on the chosen HTTP library (Python `requests`, TypeScript `node-fetch` / `axios`). The visible test passes because it mocks the call by name and accepts any signature. Real candidates have flagged this on the Meta E4 AI-assisted round (mid-2024 reports on Blind corroborated in late-2025 write-ups on interviewing.io) as one of the first things they were asked to catch. The candidate's job is to spot the hallucination in roughly ten minutes.

**Tasks.**
- Read the AI-generated function and identify the bogus method call.
- Cross-check against the real library's surface and replace with the correct API.
- Preserve the function's signature and behavior contract.
- Confirm the visible test still passes and that the hidden test passes too.

**Evaluation signal.**
- Did the candidate read the AI output critically rather than trusting that visible tests imply correctness?
- Did they reach for documentation or library knowledge to verify the call?
- Is the fix minimal (no rewrite-from-scratch)?
- Did they articulate why the visible test was insufficient?

**AI coding shape.**
- checkpoints: 1
- verification: "Hidden test exercises the function against a real local HTTP server, so a hallucinated method call throws at runtime."
- hidden test intent: "Catches solutions that only pass the mock-based visible test by mocking the bogus method by name."

### E2. Cursor pagination on a list endpoint

- **slug:** `cursor-pagination-list-endpoint`
- **flavor:** `drive`
- **languages:** `[python, typescript]`
- **difficulty:** `easy`
- **topics:** `[pagination, rest-api, cursor-encoding, api-design]`
- **companies:** `[Meta, Stripe, Shopify]`

**Description.** An existing `GET /messages` endpoint returns every row in one shot. Add stable cursor-based pagination with a `limit` and an opaque `cursor` parameter, without breaking existing callers.

**Scenario.** Pagination on top of a working list endpoint is one of the most-cited "feature on existing code" warm-ups in the AI-assisted coding round at Meta and at backend-heavy scaleups like Stripe and Shopify. The starter handler already loads messages from a small in-memory store sorted by `(created_at, id)`. Visible tests check that `limit` works on a fresh call. The catch lives in the cursor: candidates who let the AI hand them offset-based pagination silently break under concurrent inserts, and candidates who skip the tie-breaker drop or duplicate rows when two messages share a timestamp.

**Tasks.**
- Accept `limit` (default 20, max 100) and an optional opaque `cursor` query param.
- Encode the cursor from the last row's `(created_at, id)` so pagination is stable under inserts.
- Return `next_cursor` only when more rows exist; omit or null it on the last page.
- Reject invalid cursors with a 400 rather than silently restarting from the top.
- Keep callers that pass no `cursor` working exactly as before.

**Evaluation signal.**
- Did the candidate pick a stable sort key with a tie-breaker, or fall into the offset trap?
- Did they treat the cursor as opaque to the client (base64 or signed JSON), not a leaked offset?
- Did they handle malformed and end-of-stream cursors explicitly?
- Did they review the AI's draft for off-by-one inclusion at the cursor boundary?
- Was backwards compatibility preserved?

**AI coding shape.**
- checkpoints: 1
- verification: "Hidden test inserts rows mid-pagination and walks the cursor to end; offset-based solutions drop or duplicate rows."
- hidden test intent: "Catches solutions that paginate by integer offset and miss the tie-breaker on identical timestamps."

### E3. Email and password validator with explicit errors

- **slug:** `validator-explicit-errors`
- **flavor:** `drive`
- **languages:** `[python, typescript]`
- **difficulty:** `easy`
- **topics:** `[input-validation, error-messages, api-contracts]`
- **companies:** `[Meta, Stripe, Coinbase]`

**Description.** Add a `validate_signup(payload)` helper that returns either `{ok: true}` or a structured list of per-field errors. Each rejection must name the field and the specific rule that failed — not a generic "invalid input."

**Scenario.** Validators are a Meta favorite for AI-assisted warm-ups because they expose two failure modes at once: candidates who accept the AI's first draft of `True/False` and lose all the field-level signal, and candidates who let the AI return human-prose errors that downstream code can't switch on. The starter has a signup form with `email`, `password`, and `age`. Visible tests check happy-path acceptance. Hidden tests assert the exact shape and per-field code of the error list so an API consumer can localize and surface them.

**Tasks.**
- Validate `email` (RFC-shaped, single `@`, non-empty local and domain parts).
- Validate `password` (length 8-72, at least one digit, at least one letter).
- Validate `age` (integer, 13 or older, 120 or younger).
- Return a list of `{field, code, message}` entries in the same order as the rules above, not a single concatenated string.
- Stop at the first failure per field; do not double-report the same field.

**Evaluation signal.**
- Did the candidate define a typed error shape rather than free-form strings?
- Did they choose stable, machine-readable codes (e.g. `password_too_short`) over English-only messages?
- Did they check the AI output for catch-all regex that silently accepts edge cases like trailing dots?
- Did they think about empty / missing keys vs explicit invalid values?

**AI coding shape.**
- checkpoints: 1
- verification: "Hidden test asserts both the set of error codes and their order for adversarial payloads (empty strings, whitespace, unicode emails)."
- hidden test intent: "Catches solutions that return a boolean or a single concatenated message, and solutions whose regex accepts `a@b` or `a@b.` as valid."

### E4. Off-by-one in an inclusive date-range helper

- **slug:** `inclusive-date-range-off-by-one`
- **flavor:** `debug-refactor`
- **languages:** `[python, typescript]`
- **difficulty:** `easy`
- **topics:** `[dates, off-by-one, timezones, debugging]`
- **companies:** `[Meta, Airbnb, Datadog]`

**Description.** A `days_between(start, end)` helper is meant to return the inclusive count of days in a date range. The reporting dashboard is undercounting by one for every range. Find and fix the bug without breaking the existing call sites.

**Scenario.** Date-range off-by-ones are the canonical "AI wrote it, tests passed, reports were wrong" bug; they show up in real Meta and Airbnb AI-assisted writeups as the bug-fix half of the round. The helper uses naive `end - start` and returns the raw day delta, which is correct for a half-open range and wrong for the documented inclusive contract. A second, sneakier bug lurks if the inputs cross a DST boundary or arrive as `datetime` instead of `date`: the helper silently rounds. The candidate has to read the docstring carefully, not the implementation.

**Tasks.**
- Identify the off-by-one against the documented inclusive contract.
- Fix it without changing the signature or breaking the three call sites in the codebase.
- Handle the case where `start == end` (should return 1, not 0).
- Reject ranges where `end < start` with a clear error rather than returning a negative number.
- Leave a one-line comment explaining the inclusive convention so the next AI doesn't reintroduce it.

**Evaluation signal.**
- Did the candidate read the docstring contract before changing the implementation?
- Did they catch the `start == end` edge case, not just shift everything by one?
- Did they push back on the AI when it suggested re-deriving the bug as the spec?
- Did they consider timezone or `datetime`-vs-`date` input drift?
- Is the fix minimal and locally scoped?

**AI coding shape.**
- checkpoints: 1
- verification: "Hidden test sweeps `start == end`, single-day, month-boundary, and leap-year ranges; both the off-by-one and the negative-range path are checked."
- hidden test intent: "Catches solutions that fix the common case by adding `+ 1` but break `start == end` or fail to reject inverted ranges."

### E5. Prompt for a correct "plural-of" function

- **slug:** `prompt-plural-of-function`
- **flavor:** `prompt-spec`
- **languages:** `[python, typescript]`
- **difficulty:** `easy`
- **topics:** `[prompt-engineering, specification, english-morphology, edge-cases]`
- **companies:** `[Meta, GitHub, Notion]`

**Description.** Write the prompt that gets the AI to produce a correct `plural_of(word)` function on the first try. The prompt is graded by whether the resulting code passes a hidden suite of English pluralization edge cases.

**Scenario.** Pluralization is a deceptively rich problem: "box" -> "boxes", "city" -> "cities", "leaf" -> "leaves", "child" -> "children", "deer" -> "deer", "sheep" -> "sheep". Candidates who write "make a function that pluralizes English words" get a 4-line regex that fails half the suite. Candidates who enumerate the rules they care about (sibilant endings, consonant-y, f/fe, irregulars, invariants) and forbid web lookups get code that passes. Prompt/spec problems showed up in Meta's AI-enabled rollout (late 2025) as the question that separates candidates who can think about specs from candidates who can only react to AI output.

**Tasks.**
- The starter file shows a `pytest`-compatible `visible_cases` list of `(word, expected_plural)` tuples and a stub `def pluralize(word: str) -> str: ...`; the candidate's deliverable is a prompt string they paste to an AI.
- Read the visible test cases to infer the contract (no Latin/Greek scientific plurals; no proper nouns).
- Write a single prompt that produces a deterministic, dependency-free `plural_of` function.
- Spell out the rule families (regular, sibilant, consonant-y, f/fe, irregulars, invariants) in the prompt.
- Specify case preservation ("Box" -> "Boxes", "BOX" -> "BOXES") explicitly.
- Forbid external dependencies, network calls, and `inflect`/`pluralize`-style libraries.

**Evaluation signal.**
- Does the prompt enumerate the rule families rather than gesture at "plural in English"?
- Does it specify the contract (case preservation, no libraries, deterministic) precisely?
- Does it list at least three irregulars or call out an irregular table?
- Does it constrain the output shape (single function, type signature)?
- Was the candidate's prompt understandable in one read?

**AI coding shape.**
- checkpoints: 1
- verification: "The candidate's prompt is fed to a fixed model and the generated code is run against a hidden suite spanning sibilant, consonant-y, f/fe, irregular, and invariant nouns."
- hidden test intent: "Catches prompts that produce a regex-only solution that passes regulars but fails f/fe and irregulars."

### E6. Tip calculator with split-by-N and round-to-nearest

- **slug:** `tip-calculator-split-round`
- **flavor:** `mini-app`
- **languages:** `[python, typescript]`
- **difficulty:** `easy`
- **topics:** `[mini-app, currency, rounding, requirements-to-code]`
- **companies:** `[Meta, Square, DoorDash]`

**Description.** Build a small `TipCalculator` module from a written spec. Compute per-person totals from a bill, tip percentage, party size, and a round-to-nearest setting. No UI — just a clean, testable API.

**Scenario.** Tip-and-split calculators are one of the most common AI-built mini-apps in the wild, which is exactly why they appear as easy-tier AI-assisted coding warm-ups at Meta and at consumer-payments shops like Square and DoorDash. The interesting parts are not arithmetic: they are how the candidate handles currency (cents-as-integers vs floats), how they distribute the unavoidable remainder when a bill doesn't divide evenly across `n` people, and whether they let the AI quietly use `round()` (banker's rounding in Python) when the spec says "round up to the nearest 0.25". Visible tests check clean divisions; hidden tests probe the remainder distribution rule.

**Tasks.**
- Implement `calc(bill_cents, tip_percent, party_size, round_to_cents)` returning `{per_person_cents, total_cents, tip_cents}`.
- Compute the tip on the pre-tip bill, then round the per-person share to the nearest `round_to_cents` value.
- Distribute any rounding remainder deterministically — the spec says "earlier seats absorb the extra cent" — so totals sum back to the bill plus tip.
- Reject `party_size < 1`, negative bills, and tip percentages outside [0, 100] with explicit errors.
- Keep all money in integer cents; never return floats.

**Evaluation signal.**
- Did the candidate represent money as integer cents end-to-end?
- Did they implement the remainder-distribution rule from the spec, or let totals silently drift?
- Did they catch the AI's default `round()` behavior diverging from "round to nearest 0.25"?
- Did they validate inputs at the boundary rather than deep inside the calculation?
- Is the public API small and clearly documented?

**AI coding shape.**
- checkpoints: 1
- verification: "Hidden test checks that per-person amounts sum back to the rounded total exactly, across awkward party sizes (3, 7) and round-to values (25, 50, 100 cents)."
- hidden test intent: "Catches solutions that use floats, lose the remainder, or use banker's rounding instead of the specified round-to-nearest behavior."

---

## Medium (8 briefs)

<!-- 2 audit · 2 drive · 2 debug-refactor · 1 prompt-spec · 1 mini-app -->

### M1. Race in a cache-aside fetch

- **slug:** `cache-aside-race-condition`
- **flavor:** `audit`
- **languages:** `[python, typescript]`
- **difficulty:** `medium`
- **topics:** `[concurrency, caching, race-condition, ai-output-review, distributed-systems]`
- **companies:** `[Meta, Stripe, Datadog]`

**Description.** An AI assistant wrote a `get_user(user_id)` helper that reads from a cache, falls back to the database on a miss, and writes the result back. The visible tests pass single-threaded. Audit it for the concurrency bug before it goes behind a hot read path.

**Scenario.** Cache-aside is the most-cited example in interviewing.io and Blind write-ups of Meta's AI-enabled coding round where the AI produces code that is "obviously" correct line-by-line but quietly wrong under load. The starter looks textbook: `if cached: return cached; row = db.fetch(id); cache.set(id, row); return row`. The visible suite never runs two requests in parallel, so the dogpile is invisible. Under real traffic the database gets hammered on every cache miss as N concurrent requests all decide to refill the same key, and a second bug lurks in the write-back: the AI used a plain `set` with no TTL on a negative result, so a transient DB error poisons the cache for the lifetime of the process. The candidate has to find both issues without rewriting the module.

**Tasks.**
- Read the AI-generated cache-aside helper and name the two concurrency or correctness bugs.
- Add single-flight (per-key lock or in-flight future map) so a thundering herd collapses into one DB read.
- Decide and document the negative-cache policy: short TTL, no cache, or explicit error propagation.
- Preserve the public signature; the call sites must not change.
- Add a brief comment justifying the single-flight scope (per-process vs distributed) so the next AI doesn't widen it.

**Evaluation signal.**
- Did the candidate identify the dogpile without being prompted by a failing test?
- Did they reach for single-flight (`asyncio.Lock` keyed by id, `p-limit`, request coalescing) rather than a global mutex?
- Did they treat negative results as a distinct policy decision, not an oversight?
- Did they avoid the temptation to add a distributed lock when an in-process one is sufficient for the call site?
- Did they push back on the AI's "looks fine to me" follow-up suggestion?

**AI coding shape.**
- checkpoints: 2
- verification: "Hidden test fires N concurrent reads for the same cold key and asserts the DB was hit exactly once; a separate test forces a transient DB error and asserts the cache is not permanently poisoned."
- hidden test intent: "Catches solutions that pass the single-threaded visible suite by being correct on paper but collapse under any concurrent traffic, and solutions that swallow DB errors into the cache."

### M2. SQL injection masked by ORM string interpolation

- **slug:** `orm-string-interpolation-sqli`
- **flavor:** `audit`
- **languages:** `[python, typescript]`
- **difficulty:** `medium`
- **topics:** `[security, sql-injection, orm-misuse, ai-output-review, code-review]`
- **companies:** `[Meta, Shopify, GitLab]`

**Description.** An AI-generated reporting endpoint filters orders by a `status` query parameter and a sortable `column`. It uses SQLAlchemy (Python) or Prisma's `$queryRawUnsafe` / Knex `raw` (TypeScript), so it "feels" safe. Find the injection and fix it without changing the endpoint contract.

**Scenario.** This pattern dominates the SWE-bench and Sourcery vulnerability catalogs and is the canonical security-flavored audit in Meta's AI-assisted round: the AI reaches for the ORM's raw escape hatch the moment a parameterized API can't express the desired dynamic SQL, and it silently f-strings user input into a `text(...)` call or a `raw` template. The visible tests pass because they only exercise valid `status` values like `"shipped"` and `"refunded"`. The hidden tests submit a `status` of `'shipped' OR 1=1 --` and a `column` of `id; DROP TABLE orders --`. Candidates also need to recognize that even with bound parameters, dynamic identifier interpolation (column names, table names) needs an allowlist, not escaping.

**Tasks.**
- Identify every place user input flows into a raw SQL string, including identifier interpolation.
- Replace value interpolation with bound parameters (`:status`, `$1`, etc.) using the ORM's parameter API.
- Constrain `column` to an explicit allowlist of sortable fields; reject anything else with a 400.
- Preserve the endpoint's URL contract and JSON response shape.
- Leave a one-line note explaining why the ORM's "safe by default" reputation didn't apply here.

**Evaluation signal.**
- Did the candidate spot both the value-injection and the identifier-injection vectors?
- Did they reach for an allowlist on `column` rather than escaping or quoting it?
- Did they use the ORM's parameterization API correctly (not f-string into `text()`)?
- Did they verify the fix with an injection payload, not just by re-running the visible tests?
- Did they push back on the AI's suggestion to "sanitize" with a regex?

**AI coding shape.**
- checkpoints: 1
- verification: "Hidden test fires injection payloads against both `status` and `column`; the database state and the response must be unaffected, and the request must be rejected with 400 for invalid `column`."
- hidden test intent: "Catches solutions that fix the obvious value interpolation but leave identifier interpolation as a second injection vector, and solutions that quote-escape instead of allowlist."

### M3. Idempotency keys on a webhook handler

- **slug:** `webhook-idempotency-keys`
- **flavor:** `drive`
- **languages:** `[python, typescript]`
- **difficulty:** `medium`
- **topics:** `[idempotency, webhooks, at-least-once-delivery, distributed-systems, api-design]`
- **companies:** `[Stripe, Meta, Shopify]`

**Description.** An existing `POST /webhooks/payments` handler credits a user account on every delivery. The provider guarantees at-least-once delivery, so duplicates happen. Add idempotency-key handling so retries are safe without changing the external contract.

**Scenario.** This is the Stripe Integration round prompt in miniature and shows up in Meta's drive-flavored AI-assisted rounds as "make this existing handler safe to retry." The provider sends an `Idempotency-Key` (or `event.id`) header on every delivery and may re-send the same payload after a network blip or a 5xx response. The current handler reads the payload, debits an external account, and writes a row to `account_credits` — a duplicate delivery double-credits the user. Visible tests check the happy path on a fresh key. Hidden tests fire the same delivery twice in parallel, fire a delivery whose first attempt succeeded at the DB but failed to return 200, and fire a delivery with the same key but a different body (which must be rejected as a key reuse, not silently accepted).

**Tasks.**
- The starter uses the `Idempotency-Key` request header; the dedupe table stores `(key, sha256_of_body, response_status, response_body)`, and body-mismatch returns 409 with `{"error":"idempotency_key_reuse"}`, not the cached response.
- Persist the idempotency key with a unique constraint at the same transaction boundary as the side effect.
- On a duplicate key with the same payload, return the original response (status + body) verbatim.
- On a duplicate key with a different payload, reject with 409 — do not silently overwrite or re-credit.
- Handle the concurrent-duplicate case: two deliveries with the same key in flight must collapse to one credit.
- Document the key retention policy (how long the dedupe table holds keys) inline.

**Evaluation signal.**
- Did the candidate make the dedupe row and the side effect atomic (same transaction or insert-first)?
- Did they handle the body-mismatch case explicitly, not just "first write wins"?
- Did they think about concurrent duplicates, not only sequential retries?
- Did they cache the original response so retries see byte-identical output?
- Did they avoid the AI's suggestion to "just check before insert," which has the classic check-then-act race?

**AI coding shape.**
- checkpoints: 2
- verification: "Hidden tests fire (a) the same delivery sequentially twice, (b) the same delivery concurrently twice, and (c) the same key with a tampered body; account state and response bodies are asserted exactly."
- hidden test intent: "Catches solutions that use check-then-insert (race), solutions that accept body changes on the same key, and solutions that do not return byte-identical retry responses."

### M4. Structured logging with correlation IDs in an existing handler

- **slug:** `structured-logging-correlation-id`
- **flavor:** `drive`
- **languages:** `[python, typescript]`
- **difficulty:** `medium`
- **topics:** `[observability, structured-logging, correlation-id, request-context, refactoring]`
- **companies:** `[Meta, Datadog, Cloudflare]`

**Description.** A `POST /orders` handler logs in free-form English. Convert all logs to structured JSON, propagate a per-request `correlation_id`, and accept an inbound `X-Correlation-Id` header when one is present. No new functional behavior — just observability.

**Scenario.** This is a high-frequency drive-flavored prompt at Meta and Datadog-shaped backends because it tests three things the AI usually gets two-thirds right: the log shape, the context propagation, and the test discipline. The handler does three logical steps (validate, charge, persist), and each currently emits something like `logger.info(f"charging {amount} for user {user_id}")`. The candidate must convert these to a JSON shape with a stable field set, generate a correlation ID if none came in on the header (UUIDv4 is fine), make it accessible to all downstream calls in the request without threading it as a parameter (context var, MDC, AsyncLocalStorage), and echo it back on the response and on every log line for that request. The hidden tests parse the log output and assert the correlation ID appears on every line emitted within the request scope, including from a helper module two function calls deep.

**Tasks.**
- Convert each log call to a structured emit with a fixed schema (`timestamp`, `level`, `event`, `correlation_id`, plus event-specific fields).
- Generate a UUIDv4 correlation ID on entry; honor the inbound `X-Correlation-Id` header when present and well-formed.
- Propagate the ID via a context variable (`contextvars.ContextVar` in Python, `AsyncLocalStorage` in TS) so helpers don't need a new parameter.
- Echo the correlation ID back on the response as `X-Correlation-Id`.
- Ensure structured emits remain machine-parsable when fields contain commas, quotes, or newlines — no naive string concat.

**Evaluation signal.**
- Did the candidate pick a context propagation mechanism instead of threading the ID through every signature?
- Did they validate the inbound header (length, charset) rather than echo arbitrary input?
- Did they keep log emission O(1) and avoid building large strings on the hot path?
- Did they leave the existing functional behavior untouched (no new branches, no swallowed errors)?
- Did they handle exception paths, so a request that throws still emits a structured log with the correlation ID?

**AI coding shape.**
- checkpoints: 2
- verification: "Hidden test makes a request with a known `X-Correlation-Id`, captures the log stream, parses each line as JSON, and asserts the ID is present on every emit including from helper modules and from the exception path."
- hidden test intent: "Catches solutions that print pretty strings instead of JSON, solutions that thread the ID manually and miss helper-module emits, and solutions that lose the ID on exception."

### M5. Event listener leak under repeated mount/unmount

- **slug:** `event-listener-cleanup-leak`
- **flavor:** `debug-refactor`
- **languages:** `[typescript]`
- **difficulty:** `medium`
- **topics:** `[memory-leak, event-listeners, lifecycle, abortcontroller, debugging]`
- **companies:** `[Meta, Vercel, Notion]`

**Description.** A `Widget` class subscribes to `resize`, `visibilitychange`, and a custom event bus on mount and is meant to detach on unmount. Memory profiling shows the heap retains every previously-mounted instance. Find and fix the leak without changing the public API.

**Scenario.** Event listener leaks are the highest-signal debug-refactor in Meta's frontend AI-assisted rounds: the bug is almost always one of three patterns, and the AI almost always suggests a fix that misses one. The starter calls `window.addEventListener('resize', () => this.layout())` in `mount()` and `window.removeEventListener('resize', () => this.layout())` in `unmount()` — different function references, so `removeEventListener` is a no-op. A second listener is registered on a long-lived event bus singleton with `bus.on('refresh', this.onRefresh)` but never unsubscribed because `unmount()` was written before `onRefresh` was added. A third subtle leak comes from a closed-over `this` keeping the DOM node alive even after the widget is "torn down" — specifically, `this.handleResize = () => this.layout()` is stored in a `Map` keyed by the element's `dataset.widgetId`, preventing GC even after `unmount()`. The candidate must find all three and apply the modern `AbortController` pattern to make the next regression impossible.

**Tasks.**
- Reproduce the leak with the provided heap-snapshot harness, identifying which references retain each `Widget`.
- Replace anonymous-handler `addEventListener`/`removeEventListener` pairs with a single `AbortController` whose `signal` is passed to each listener.
- Find and unsubscribe the event-bus listener on `unmount()`; consider whether the bus needs a `WeakRef`-style escape hatch.
- Ensure `unmount()` is idempotent and safe to call after construction failure (partial init).
- Add a one-line invariant comment so a future AI rewrite doesn't reintroduce the mismatched-reference pattern.

**Evaluation signal.**
- Did the candidate use the heap snapshot rather than guessing?
- Did they reach for `AbortController` instead of patching the broken `removeEventListener` pair?
- Did they find all three listener sources, not just the obvious `window` one?
- Did they verify the fix by remounting N times and confirming flat heap growth?
- Did they keep `unmount()` idempotent for safe error-path use?

**AI coding shape.**
- checkpoints: 2
- verification: "Hidden test mounts and unmounts the widget 1000 times under a heap snapshot harness; retained-size growth must be bounded by a small constant, and listener counts on `window` and the bus must return to baseline."
- hidden test intent: "Catches solutions that fix only the `window` listener and leave the bus listener leaking, and solutions whose `unmount()` throws when called twice."

### M6. Refactor a 300-line god function without changing behavior

- **slug:** `god-function-refactor`
- **flavor:** `debug-refactor`
- **languages:** `[python, typescript]`
- **difficulty:** `medium`
- **topics:** `[refactoring, separation-of-concerns, characterization-tests, behavior-preservation]`
- **companies:** `[Meta, Stripe, Shopify]`

**Description.** A single `process_order(order)` function is 300 lines: it validates, prices, discounts, reserves inventory, charges, persists, and emits notifications. Refactor it into focused units. Every observable behavior — return value, side effects, exceptions — must be preserved exactly.

**Scenario.** The "make this readable without breaking it" refactor is Meta's most-cited debug-refactor in the AI-assisted round because it tests the candidate's discipline more than their cleverness: the AI will eagerly propose a rewrite that subtly drops a log line, reorders two side effects, or moves an exception to a different layer. The starter has no unit tests for the function itself, only one end-to-end visible test. The candidate is expected to add characterization tests against the current behavior before refactoring, then extract pure functions (pricing, discount), command-shaped side-effect handlers (inventory, charge, persist, notify), and a thin orchestrator. The hidden suite includes adversarial cases — a discount that brings the total to exactly zero, an out-of-stock item, a charge that succeeds but persistence that fails — and asserts both return values and the exact order of side effects, so any reordering during refactor is caught.

**Tasks.**
- Add characterization tests that pin the current return value, exception type, and side-effect order before changing any code.
- Extract pure logic (pricing, discount math, validation) into deterministic helpers with no I/O.
- Move each side effect (inventory reservation, charge, persist, notify) into a named function with an explicit return/error contract.
- Reduce the orchestrator to under 50 lines that reads top-to-bottom as the business flow.
- Preserve the original signature; no caller changes anywhere in the repo.

**Evaluation signal.**
- Did the candidate write characterization tests first, or refactor blind?
- Did they preserve side-effect ordering, including in the failure paths?
- Did they resist the AI's suggestion to inline-fix bugs they noticed during the refactor (separate PR concern)?
- Did they keep the public signature stable and avoid leaking new exceptions?
- Is the resulting orchestrator readable in one screen?

**AI coding shape.**
- checkpoints: 2
- verification: "Hidden test asserts identical return values and identical side-effect call order (recorded via spies on the side-effect functions) across happy-path, discount-to-zero, out-of-stock, and charge-succeeds-persist-fails scenarios."
- hidden test intent: "Catches refactors that reorder side effects, swallow or relabel exceptions, or fix latent bugs along the way and therefore change observable behavior."

### M7. Spec a fuzzy-match function with explicit edge cases

- **slug:** `prompt-fuzzy-match-spec`
- **flavor:** `prompt-spec`
- **languages:** `[python, typescript]`
- **difficulty:** `medium`
- **topics:** `[prompt-engineering, specification, edit-distance, unicode, edge-cases]`
- **companies:** `[Meta, GitHub, Notion]`

**Description.** Write a prompt that gets the AI to produce a correct `fuzzy_match(query, candidate, threshold)` function returning a boolean. The function must be based on a normalized edit distance with explicit, defensible behavior on the edge cases the hidden suite probes.

**Scenario.** Edit-distance functions are the most-cited prompt-spec problem at Meta and GitHub for AI-assisted rounds because the textbook Levenshtein recurrence is two lines but the contract around it is a swamp: case sensitivity, Unicode normalization (NFC vs NFD), whitespace collapsing, empty strings, and how to turn an integer distance into a fraction (over `max(len(a), len(b))`? over `len(query)`? Sorensen-Dice instead?). A candidate who writes "build me a fuzzy match" gets a working Levenshtein that disagrees with the hidden suite on five of ten cases. A candidate who enumerates the normalization rules, the distance metric, the threshold semantics ("`>= threshold` means accept"), and the empty-string behavior gets code that passes. The prompt-spec is judged by the generated code, not the prose.

**Tasks.**
- The candidate receives a file with 8 visible test cases and a stub function signature; their deliverable is a prompt string.
- Read the visible cases to infer the contract; do not assume Levenshtein over raw bytes is the right choice.
- Write a single prompt that specifies the distance metric, the normalization step, and the similarity-to-threshold mapping.
- Spell out Unicode normalization (NFC), case folding, and whitespace collapsing as preprocessing.
- Define empty-string and identical-string behavior explicitly (`fuzzy_match("", "", 0.5)` -> true; `fuzzy_match("", "x", 0.5)` -> false).
- Forbid external libraries (`fuzzywuzzy`, `rapidfuzz`, `string-similarity`) and require a self-contained implementation.

**Evaluation signal.**
- Does the prompt name the distance metric (Levenshtein, normalized by max length) rather than gesture at "similarity"?
- Does it enumerate the preprocessing steps in order?
- Does it nail down the threshold semantics (inclusive vs exclusive, similarity vs distance)?
- Does it specify behavior on empty and identical inputs?
- Was the candidate's prompt understandable in one read and reproducible across runs?

**AI coding shape.**
- checkpoints: 1
- verification: "The candidate's prompt is fed to a fixed model and the generated code is run against a hidden suite covering ASCII near-misses, accented characters (NFC vs NFD), mixed case, leading/trailing whitespace, empty strings, and threshold boundaries."
- hidden test intent: "Catches prompts that produce a vanilla Levenshtein with no normalization, prompts that pick the wrong denominator for the similarity ratio, and prompts that leave threshold inclusivity ambiguous."

### M8. URL shortener with collision handling

- **slug:** `url-shortener-collisions`
- **flavor:** `mini-app`
- **languages:** `[python, typescript]`
- **difficulty:** `medium`
- **topics:** `[mini-app, hashing, collision-handling, data-structures, api-design]`
- **companies:** `[Meta, Cloudflare, Bitly]`

**Description.** Build a `UrlShortener` module with `shorten(long_url)` and `resolve(code)`. Codes must be 7 characters, deterministic for the same URL, and survive concurrent inserts of distinct URLs that happen to collide.

**Scenario.** URL shorteners are the canonical AI-built mini-app in interviewing.io's Meta write-ups because they hit three real design choices in 30 minutes: how to generate codes (hash-prefix vs counter-encoded vs random), how to detect and resolve collisions when two different URLs hash to the same 7-char prefix, and how to handle the "same long URL submitted twice" case (idempotent — return the existing code, do not mint a new one). The visible tests check happy-path shorten/resolve. Hidden tests force a collision by seeding the store with a fixed prefix, fire concurrent `shorten()` calls for the same URL and assert exactly one code is minted, and fire concurrent `shorten()` calls for different URLs that hash-prefix-collide and assert both succeed with distinct codes. The candidate must also avoid the classic mistake of using `hash()` (non-deterministic across Python processes).

**Tasks.**
- Implement `shorten(long_url)` returning a 7-char code over the alphabet `[A-Za-z0-9]`.
- Make `shorten` idempotent: the same long URL always maps to the same code.
- Detect collisions on insert and resolve them deterministically (e.g., re-hash with a salt counter) without changing the code for already-stored URLs.
- Make concurrent `shorten()` of the same URL collapse to one row (single-flight or unique constraint + retry).
- Implement `resolve(code)` returning the long URL or raising/returning a clear not-found result.

**Evaluation signal.**
- Did the candidate pick a deterministic hash (SHA-256 prefix, not Python's `hash()`)?
- Did they handle the same-URL-twice case with idempotency, not by minting duplicates?
- Did they handle hash-prefix collisions with a defined strategy (salt-and-retry, linear probe in the code space) rather than overwriting?
- Did they make concurrent inserts safe with a unique constraint and a retry loop, not a pre-check?
- Is the API small and the storage interface swappable (dict today, KV tomorrow)?

**AI coding shape.**
- checkpoints: 2
- verification: "Hidden test seeds a collision, fires 50 concurrent `shorten()` calls for the same URL (asserts exactly one code minted), and fires concurrent `shorten()` calls for different URLs that share a 7-char prefix (asserts both resolve correctly)."
- hidden test intent: "Catches solutions using `hash()` (non-deterministic across processes), solutions that mint duplicate codes for the same URL under concurrency, and solutions that overwrite on prefix collision."

---

## Hard (6 briefs)

<!-- 1 audit · 1 drive · 2 debug-refactor · 1 prompt-spec · 1 mini-app -->

### H1. Banker's rounding drift in a multi-step billing calculation

- **slug:** `financial-rounding-bankers-drift`
- **flavor:** `audit`
- **languages:** `[python, typescript]`
- **difficulty:** `hard`
- **topics:** `[financial-rounding, decimal-arithmetic, ai-output-review, invariants, audit]`
- **companies:** `[Meta, Stripe, Square, Coinbase]`

**Description.** An AI assistant wrote a `compute_invoice(items, discount_pct, tax_rate, refund_lines)` routine for a billing service. It uses Python's built-in `round()` (or JavaScript's `Math.round` plus `toFixed`) and the visible tests pass on whole-dollar cases. Find the rounding bug before it ships against real customer money.

**Scenario.** Subtle rounding drift on multi-step money math is the canonical hard audit at Meta Pay, Stripe, Square, and Coinbase, and it dominates the financial-bugs slice of SWE-bench because the error compounds across operations rather than blowing up in one place. The AI-written routine computes a pre-discount subtotal, applies a percentage discount to produce a discounted subtotal, applies tax on the discounted subtotal, then subtracts a list of refund lines (each of which re-applies its share of the discount). Each step uses `round(value, 2)` — which is banker's rounding in Python (round-half-to-even, the IEEE 754 default) and floating-point `Math.round` in TS — while the customer contract requires round-half-away-from-zero on every step, implemented as `decimal.Context(rounding=decimal.ROUND_HALF_UP)` (Python's `ROUND_HALF_UP` matches half-away-from-zero for both signs), and per-line truncation on refund allocation. The result is a one-cent drift per refund line, with the sign flipping on credits, so a customer with three refunds is undercharged by three cents and the books refuse to reconcile. Visible tests use single-item invoices with no refunds, which never exercise the compounding path.

**Tasks.**
- Identify every rounding call and classify it: midpoint behavior, sign behavior, and whether it operates on `float` or `Decimal`.
- Replace `float` arithmetic with `decimal.Decimal` (Python) or a fixed-point integer-cents representation (TS) end-to-end; do not round between intermediate operations except at the documented boundaries.
- Implement the contract's rounding rule explicitly using `decimal.Context(rounding=decimal.ROUND_HALF_UP)` for all steps (Python's `ROUND_HALF_UP` rounds away from zero on both positive and negative midpoints).
- Fix the refund allocation so per-line discount shares sum back to the original discount exactly — distribute the residual cent to the largest refund line (or per the spec).
- Prove the fix with an invariant test: for any randomized invoice, `sum(line_totals) + tax - sum(refunds) == grand_total` to the cent.
- Leave a one-line comment naming the rounding mode so the next AI does not silently switch to `round()`.

**Evaluation signal.**
- Did the candidate spot that `round()` is banker's rounding, not "round half up," without being told?
- Did they switch the entire calculation to `Decimal` or integer cents rather than patching one call?
- Did they identify the refund-allocation residual-cent bug, not only the midpoint bug?
- Did they encode the reconciliation invariant as a property-based test rather than relying on hand-picked cases?
- Did they push back on the AI's first-pass fix of "use `round(x, 2)` everywhere"?
- Did they leave the rounding mode discoverable to the next reader?

**AI coding shape.**
- checkpoints: 2
- verification: "Hidden suite differential-tests against a Decimal-based reference: for 10000 random invoices (positive and negative line items, multiple refunds, awkward percentages like 33.33% off and 8.875% tax) the reconciliation invariant must hold to the cent, and known midpoint cases (e.g. 0.125, -0.125 at two decimals) must match the spec's rounding rule."
- hidden test intent: "Catches solutions that fix the obvious banker's-rounding call but leave `float` arithmetic in place and therefore drift on long invoices, and solutions that ignore the residual-cent allocation rule for refunds."

### H2. Add a feature-flag system to an existing handler stack

- **slug:** `feature-flag-system-rollout`
- **flavor:** `drive`
- **languages:** `[python, typescript]`
- **difficulty:** `hard`
- **topics:** `[feature-flags, gradual-rollout, request-context, api-design, configuration]`
- **companies:** `[Meta, LaunchDarkly, Stripe, Shopify]`

**Description.** A REST service has five handlers (`/checkout`, `/recommendations`, `/search`, `/profile`, `/admin/*`) sharing a common middleware chain. Add a feature-flag system that supports boolean kill-switches, percentage rollouts keyed by user, and targeted rules (allowlist of user IDs, country codes), without touching call sites beyond a single `flags.is_enabled(...)` call.

**Scenario.** Rolling a feature-flag layer into an existing handler stack is Meta's canonical hard drive prompt because it tests API design, request-scoped context propagation, deterministic bucketing, and backwards compatibility all at once — the same shape LaunchDarkly, Statsig, and Meta's internal Gatekeeper expose. The starter has a config file declaring flags (`new_checkout_flow`, `recs_v2`, etc.) but no runtime. The candidate must implement `flags.is_enabled(name, context)` where `context` carries `user_id`, `country`, and the current request's `correlation_id`; the function must be stable across calls within a request (same answer for the same flag+user, even if the rollout percentage changes mid-request via a hot-reload), and deterministic across processes for the same user (hash-based bucketing on `(flag_name, user_id)`, not random sampling). The flag config supports three rule types in priority order: `kill_switch: false` (forces off), `allow_user_ids: [...]` (forces on), `rollout_pct: 0-100` (hash-based). Hidden tests reload the config mid-request, fire concurrent requests for the same user across flag changes, and verify bucketing distribution holds within 1% over 100k users. The candidate must also expose `flags.all_active(context)` for logging and not break the existing five handlers.

Example config schema:

```yaml
flags:
  new_checkout_flow:
    kill_switch: false
    allow_user_ids: [101, 202]
    rollout_pct: 20
  legacy_writes_off:
    kill_switch: true
    allow_user_ids: []
    rollout_pct: 0
```

`rollout_pct` is an integer 0–100. Rule precedence: `kill_switch` (highest) → `allow_user_ids` → `rollout_pct` (lowest).

**Tasks.**
- Implement `FlagService` with `is_enabled(name, context) -> bool` and `all_active(context) -> list[str]`; both must be O(1) per flag and free of I/O on the request path.
- Pick a deterministic bucketing function (e.g., MurmurHash3 of `f"{flag_name}:{user_id}"` mod 10000, compared to `rollout_pct * 100`) so the same user-flag pair always lands the same way across processes.
- Snapshot the flag config at request entry so a hot-reload mid-request does not flip the answer for an in-flight call.
- Wire the existing middleware to attach the snapshot to request context; expose `flags` via `contextvars.ContextVar` / `AsyncLocalStorage` so handlers call `flags.is_enabled(...)` without a parameter dependency.
- Add a `POST /admin/flags/reload` endpoint that atomically swaps the config (and only that); do not allow partial reload. Admin endpoints require an `X-Admin-Token` header check; reject with 401 if missing or wrong.
- Preserve every existing handler's response shape; only `/admin/flags/reload` is new.
- Emit a single structured log line per request listing `all_active` flags, gated by a sampling rate.

**Evaluation signal.**
- Did the candidate pick a hash-based bucketing function instead of `random.random() < pct`?
- Did they snapshot the config at request entry, so concurrent reloads cannot flip an in-flight decision?
- Did they handle rule precedence explicitly (kill-switch wins, then allowlist, then rollout)?
- Did they avoid threading a `flags` parameter through every handler and use a context var?
- Did they make `/admin/flags/reload` atomic (swap-pointer or read-write lock), not field-by-field?
- Did they keep the public response shapes of the five existing handlers byte-identical?

**AI coding shape.**
- checkpoints: 3
- verification: "Hidden tests: (a) deterministic bucketing — for 100k synthetic users the active fraction matches `rollout_pct` within 1%; (b) per-user stability — the same user gets the same answer across 1000 calls and across a process restart; (c) reload atomicity — fire 200 concurrent requests while reloading and assert no request sees a mix of old and new config; (d) backwards compat — the five existing handlers return byte-identical responses with flags off."
- hidden test intent: "Catches solutions that use `random.random()` (non-deterministic across processes), solutions that read the live config dict per-call (torn reads during reload), and solutions that flip rule precedence so allowlist beats kill-switch."

### H3. Flaky integration test caused by event-loop scheduling order

- **slug:** `flaky-test-event-loop-reordering`
- **flavor:** `debug-refactor`
- **languages:** `[python, typescript]`
- **difficulty:** `hard`
- **topics:** `[flaky-tests, asyncio, event-loop, race-conditions, debugging]`
- **companies:** `[Meta, Vercel, Datadog]`

**Description.** An integration test for an async order pipeline passes locally 99% of the time and fails on CI roughly once per 50 runs. The test exercises a chain of `asyncio` (or `Promise`) callbacks across a queue, a fake HTTP client, and an in-memory DB. Diagnose the source of the flake and fix it so the test is deterministic, without weakening the assertion.

**Scenario.** Flaky-test hunts driven by event-loop scheduling order are the highest-signal hard debug-refactor in Meta's backend AI-assisted rounds because the AI's instinct is to slap a `sleep(0.1)` on the assertion and call it done. The starter has a producer that enqueues three orders, a consumer that pulls from the queue and `await`s a fake HTTP `notify()` per order, and a final `assert_processed(order_ids)` that reads from the DB. On a fast loop the consumer often interleaves a microtask between the HTTP `await` and the DB write in a different order than the producer expected; on CI under load, a different scheduling order causes the assertion to read a partially-written state. The visible test passes locally because the loop happens to dispatch tasks in insertion order; on CI it does not. A second, deeper bug is that the consumer uses `asyncio.gather(*tasks)` and relies on the gather order matching the queue order — which is true for the result list but not for side-effect ordering. The candidate has to read the actual scheduling, not the source-line order, and either serialize the side effects explicitly or change the assertion to be order-independent in the right way.

**Tasks.**
- Reproduce the flake deterministically: run the test under a fixed-seed event loop or `--forked` configuration until it fails, capturing the actual await order. Use `PYTHONASYNCIODEBUG=1` and a custom `asyncio.AbstractEventLoop` subclass (or task factory) that records the order coroutines transition from pending to running. In Node, use `--trace-warnings` and the `async_hooks` module to capture before/after callback transitions.
- Identify the specific await point where producer assumptions diverge from scheduler reality, and write a one-paragraph diagnosis in the PR.
- Choose a fix: serialize via an `asyncio.Lock` on the DB write, or replace `gather` with a serial `for await` if the workload allows, or change the assertion to a set-based check if order is genuinely not a contract.
- Justify the chosen fix against the others — explicitly rule out `sleep` and "retry the assertion" as anti-patterns.
- Add a regression test that pins the chosen invariant (ordered or set) so the next AI cannot drift the contract.
- Run the test 1000 times under the same harness and confirm zero failures.

**Evaluation signal.**
- Did the candidate reproduce the flake before proposing a fix, or guess?
- Did they read the scheduling order (e.g., `asyncio.get_event_loop().set_debug(True)`, `PYTHONASYNCIODEBUG=1`, Node `--trace-warnings`) rather than reasoning from source?
- Did they avoid the `sleep`/`retry` cargo-cult fix?
- Did they explicitly choose between "make it ordered" and "make the assertion order-independent" based on the business contract, not convenience?
- Did they pin the chosen invariant with a regression test?
- Did they confirm with a stress run, not a single passing run?

**AI coding shape.**
- checkpoints: 2
- verification: "Hidden harness runs the test 1000 times under a randomized scheduler (Python: `asyncio` with a custom task factory that shuffles ready callbacks; TS: `setImmediate` reordering shim); zero failures required. A separate test asserts the chosen invariant explicitly (e.g., side effects emitted in queue order, or DB rows present as a set)."
- hidden test intent: "Catches fixes that add a `sleep` or assertion retry — these still fail under the randomized scheduler — and fixes that change the assertion to 'works for me' rather than encoding a defensible invariant."

### H4. Refactor a recursive parser to iterative with identical AST output

- **slug:** `recursive-parser-to-iterative`
- **flavor:** `debug-refactor`
- **languages:** `[python, typescript]`
- **difficulty:** `hard`
- **topics:** `[parser, recursion-to-iteration, explicit-stack, ast-equality, behavior-preservation]`
- **companies:** `[Meta, GitHub, Anthropic]`

**Description.** A recursive-descent parser for a small expression language (`number`, `identifier`, `+ - * /`, parens, function calls with comma-separated args) blows the stack on deeply-nested inputs from a real user workload (`((((... 5000 deep ...))))`). Convert it to an iterative implementation backed by an explicit stack. The produced AST must be structurally identical, with the same spans and error positions, to the recursive version on every legal input.

**Scenario.** Recursive-to-iterative parser conversion is Meta's hardest debug-refactor in the AI-assisted round and a frequent take-home at GitHub's editor team and Anthropic's tools group because the AI can produce something that "parses the same grammar" but disagrees with the original on associativity, precedence ties, error position, or whitespace handling. The starter is roughly 250 lines, hand-written, with left-recursion-free Pratt-style precedence climbing. The AST is a tagged-tuple structure (`("binop", op, left, right, span)`) where `span` is a `(start, end)` byte range that the language server depends on. Hidden tests fuzz 10000 random inputs against a corpus of malformed inputs (unbalanced parens, trailing operators, EOF inside a call) and assert structural equality of the AST and exact equality of error positions and messages. A naive iterative rewrite typically gets right-associativity wrong on a chain like `a - b - c` (must be `((a-b)-c)`, not `(a-(b-c))`) and drops the span of the parent node when reconstructing from the operand stack.

**Tasks.**
- Add a characterization test that captures the recursive parser's AST and error output across a fixed corpus before any refactor.
- Design the explicit-stack state machine — operand stack, operator stack, and a precedence/associativity table identical to the recursive Pratt loop.
- Preserve span computation: when popping operands to build a binary node, the new node's span is the merge of the leftmost operand's start and the rightmost operand's end, not the operator's span.
- Preserve error behavior exactly: the same input must produce the same error type, message, and `(line, column)` position as the recursive version.
- Keep recursion only where the grammar's nesting depth is small and bounded (e.g., argument lists if you choose to leave them recursive, but document the bound); the test inputs reach 5000-deep parenthesization.
- Verify against the original on the characterization corpus, then on a fuzz corpus, and confirm no stack-depth regression under the 5000-deep input.

**Evaluation signal.**
- Did the candidate write the characterization tests first, against the recursive version's actual output?
- Did they preserve operator precedence and associativity exactly (especially left-associative subtraction and division)?
- Did they preserve span computation, including for error nodes?
- Did they preserve error messages byte-for-byte, not "an error with the same meaning"?
- Did they avoid letting the AI rewrite the grammar "while we're in there"?
- Did they verify by differential AST comparison, not by re-running the visible suite?

**AI coding shape.**
- checkpoints: 3
- verification: "Hidden tests do a differential AST comparison against the original recursive parser over 10000 fuzzed inputs (numbers, deep parens up to depth 5000, mixed-precedence chains, unbalanced parens, EOF mid-call); structural and span equality required. A second test asserts the iterative parser completes the 5000-deep input under a constrained recursion limit (`sys.setrecursionlimit(100)` / equivalent), which any residual recursion blows."
- hidden test intent: "Catches rewrites that flip associativity on left-associative operators, lose or recompute spans wrong, change error messages or positions, or smuggle recursion in through a helper function."

### H5. Spec an RFC 4180 CSV parser the AI can implement correctly

- **slug:** `prompt-rfc4180-csv-parser`
- **flavor:** `prompt-spec`
- **languages:** `[python, typescript]`
- **difficulty:** `hard`
- **topics:** `[prompt-engineering, csv, rfc-4180, edge-cases, specification]`
- **companies:** `[Meta, GitHub, Snowflake]`

**Description.** Write the prompt that gets the AI to produce a correct streaming CSV parser conforming to RFC 4180 with the documented extensions. The function takes an iterator of text chunks (not a file) and yields one list of fields per record. The prompt is graded by whether the generated code passes a hidden suite of edge cases that the standard library `csv` and `papaparse` modules also handle.

**Scenario.** CSV-with-quoted-strings is the canonical hard prompt-spec problem at Meta, GitHub, and data-platform shops like Snowflake because RFC 4180 is short enough that candidates think they know it and long enough that the AI's first draft fails on at least four of: quoted fields containing the delimiter, quoted fields containing newlines (record split across chunks), escaped double-quotes inside quoted fields (`""` → `"`), trailing newline (record vs no-record), CRLF vs LF vs mixed line endings, UTF-8 BOM at file start, empty fields (`a,,b` → `["a","","b"]`), and fields containing a quote character without the field being quoted (which RFC 4180 says is malformed — the prompt has to choose whether to be strict or lenient and document it). The candidate also has to decide on the chunking contract: a record can straddle multiple input chunks, including in the middle of a quoted field, and the parser must buffer rather than emit a wrong record. The prompt-spec is judged by the generated code, not the prose.

**Tasks.**
- Read RFC 4180 and the visible cases to infer which extensions to support (BOM stripping, configurable delimiter, configurable quote char, lenient vs strict mode).
- Write a single prompt that specifies the parser's contract: streaming input shape, output shape (list of fields per yielded record), quote-escape semantics (`""` → `"`), line-ending handling, BOM behavior, and what "malformed" produces (an exception with a row/column position, not silent recovery).
- Enumerate the chunk-boundary invariant explicitly: any input split into chunks must produce the same records as the same input concatenated.
- Specify the empty-input and trailing-newline behavior (`""` → no records; `"a\n"` → one record `["a"]`; `"a\n\n"` → two records, the second being `[""]`).
- Forbid `csv` / `papaparse` / `csv-parser` and require a self-contained state-machine implementation; specify the state names so the AI does not invent a recursive-descent variant. At minimum, the prompt must name the `FIELD_START`, `IN_UNQUOTED`, `IN_QUOTED`, `ESCAPE_IN_QUOTED`, and `FIELD_END` states (or equivalent unambiguous names).
- Specify the error type and message format for malformed input (e.g., `CSVError(row=12, col=34, reason="unterminated quoted field")`).

**Evaluation signal.**
- Does the prompt name RFC 4180 and call out the specific edge cases (quoted delimiter, embedded newline, escaped quote, BOM) rather than gesture at "CSV"?
- Does it pin the chunk-boundary invariant — same output for any chunking of the same bytes?
- Does it specify the state-machine shape so the AI does not produce a regex-or-split solution?
- Does it nail down strict-vs-lenient behavior on malformed input, with a typed error?
- Does it specify trailing-newline and empty-input behavior, the most common silent-disagreement source?
- Did the candidate's prompt produce code that passed on the first generation, or did they iterate?

**AI coding shape.**
- checkpoints: 1
- verification: "The candidate's prompt is fed to a fixed model and the generated code is differentially tested against Python's `csv` module (or `papaparse` in TS) over 5000 fuzzed inputs spanning all RFC 4180 features plus pathological chunkings; additional hand-picked cases assert byte-identical behavior on BOM, CRLF, escaped quotes, and unterminated-quote errors."
- hidden test intent: "Catches prompts that produce a `split(',')` or regex-based solution (fails on quoted delimiters), prompts that produce a non-streaming solution (fails on chunked input), and prompts that leave malformed-input behavior unspecified so the AI silently recovers."

### H6. Rate-limited API gateway with token bucket and admin endpoints

- **slug:** `rate-limited-gateway-token-bucket`
- **flavor:** `mini-app`
- **languages:** `[python, typescript]`
- **difficulty:** `hard`
- **topics:** `[rate-limiting, token-bucket, concurrency, api-design, mini-app]`
- **companies:** `[Meta, Stripe, Cloudflare]`

**Description.** Build a small in-process API gateway that proxies `GET /proxy/*` to an upstream service, applies per-API-key token-bucket rate limiting, and exposes admin endpoints to inspect and adjust limits at runtime. The bucket must be concurrent-safe and the gateway must keep tail latency low under contention.

**Scenario.** Token-bucket rate limiters built as mini-apps are the canonical hard mini-app at Meta, Stripe, and Cloudflare and trace directly to Stripe's "Scaling your API with rate limiters" blog post and Cloudflare's published gateway design. The starter has a stub upstream and an empty gateway. The candidate builds: (1) a `TokenBucket(capacity, refill_per_sec)` that uses the lazy-refill trick (compute available tokens on demand from `last_refill_time`, not a background thread); (2) a per-key `BucketStore` keyed by `X-API-Key` header, with default `(capacity=60, refill=1/sec)` and configurable overrides; (3) a request path that takes one token or rejects with `429` plus a `Retry-After` header computed from the deficit; (4) admin endpoints `GET /admin/limits/{key}` returning the live bucket state, `PUT /admin/limits/{key}` to update `(capacity, refill_per_sec)`, and `POST /admin/limits/{key}/reset` to refill the bucket. Hidden tests fire 1000 concurrent requests under a known key (asserts exactly `capacity` are admitted in the first window, the rest get 429 with monotonically non-decreasing `Retry-After` values), drift the clock to verify lazy refill is correct, change the bucket size mid-flight via the admin endpoint (existing tokens must not be lost), and assert the admin endpoints themselves are not rate-limited.

**Tasks.**
- Implement `TokenBucket` with `try_take(n=1) -> (allowed: bool, retry_after_ms: int)`; use lazy refill (compute current tokens from `now - last_refill`), not a background timer.
- Make the bucket concurrent-safe: a single `Lock` per bucket is acceptable, but the lock must not be held across the upstream call.
- Implement `BucketStore` with per-key buckets; a missing key creates one on demand from the configured defaults. Bound the store so an attacker spamming random keys cannot OOM the process (LRU or sharded-with-cap).
- Wire the proxy: on each `GET /proxy/*`, take one token; on rejection return `429` with `Retry-After` (seconds) and an `X-RateLimit-Remaining: 0` header; on accept, forward to the upstream and stream the response.
- Implement the three admin endpoints. `PUT` updates capacity and refill rate; if the new capacity is smaller than current tokens, clamp; if larger, leave current tokens unchanged (do not refill on a config change). `POST /reset` sets tokens to capacity. Admin endpoints are exempt from rate limiting and require a separate `X-Admin-Token` header.
- Emit a structured log per request with `key`, `allowed`, `tokens_remaining`, and `retry_after_ms`.
- Keep the data plane lock-free of I/O: holding the bucket lock during a `httpx.get(...)` is a fail.

**Evaluation signal.**
- Did the candidate use lazy refill rather than a background sweeper task?
- Did they release the bucket lock before the upstream call?
- Did they compute `Retry-After` correctly from the token deficit and the refill rate (not a fixed value)?
- Did they handle the admin `PUT` semantics (capacity clamp, tokens preserved) thoughtfully?
- Did they bound the `BucketStore` so unknown keys do not OOM the process?
- Did they avoid global locks that serialize all keys?

**AI coding shape.**
- checkpoints: 3
- verification: "Hidden tests: (a) burst of `capacity + 100` concurrent requests admits exactly `capacity` and returns 429 with monotonically non-decreasing `Retry-After` for the rest; (b) clock-skew test advances a fake clock and asserts lazy refill produces the right token count; (c) `PUT /admin/limits` mid-flight changes the rate without losing in-flight tokens; (d) random-key flood with 1M unique keys does not exceed a bounded process memory budget; (e) bucket lock is not held during the upstream call (asserted by an instrumented upstream that records request arrival timing under contention)."
- hidden test intent: "Catches solutions that use a background refill task (timer drift on lazy clocks), solutions that hold the lock across the upstream call (head-of-line blocking), solutions with an unbounded bucket store (DoS via random keys), and solutions whose `Retry-After` is a constant or zero."
