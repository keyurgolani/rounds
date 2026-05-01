"""SDQ — Design Pastebin.

Text-snippet sharing service with TTL, visibility controls (public / unlisted /
private), and syntax highlighting at render time. Mirrors `sd_questions.SD_01`
shape via the `_q` / `_topic` helpers.
"""
from __future__ import annotations

from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design Pastebin",
    "Medium",
    "Design a service where any user (anonymous or signed-in) submits a text snippet — code, log, "
    "config, prose — receives a short shareable URL, and anyone with the URL renders the snippet "
    "with optional syntax highlighting. Snippets carry a TTL (1 day, 1 week, never), a visibility "
    "(public listed, unlisted, private with auth), and may be large (up to ~10 MB). The system is "
    "read-heavy (one write, many reads), abuse-prone (spam, malware C2), and must rate-limit per IP "
    "and account while keeping the create→render path under a few hundred milliseconds globally.",
    hints=[
        "It's TinyURL-like at the front door but a blob store at the back — keep the metadata DB tiny.",
        "Body lives in object storage; the DB row is just a pointer + ACL + TTL marker.",
        "TTL has two layers: Redis EX for hot expiry, DB tombstone + GC for durable cleanup.",
        "Visibility (public / unlisted / private) must be enforced at the read API, not just hidden in UI.",
        "Syntax highlighting is a render-time concern — never store coloured HTML, store source + language.",
        "Compress long pastes server-side (zstd/gzip); the API contract speaks plaintext.",
    ],
    constraints=[
        "Paste size up to ~10 MB; p50 is a few KB; long tail of multi-MB logs.",
        "Read:write ratio ~100:1 — most pastes are viewed many times in a short window.",
        "TTL options: 10 minutes, 1 hour, 1 day, 1 week, 1 month, never.",
        "Anonymous submissions allowed but heavily rate-limited; abuse vectors are real (malware, spam).",
        "Render latency p95 < 300 ms globally; create p95 < 500 ms.",
    ],
    req_func=[
        "Create a paste with body, language hint, TTL, and visibility.",
        "Return a short shareable URL (e.g. /p/aB3xY9).",
        "Read a paste by short ID; render with syntax highlighting if a language is set.",
        "Visibility: public (listed in /recent), unlisted (URL-only), private (auth required).",
        "Edit (signed-in only) and delete (owner or admin).",
        "Optional: full-text search across the user's own pastes.",
    ],
    req_nonfunc=[
        "Read latency p95 < 300 ms global; create p95 < 500 ms.",
        "Durability: never lose an unexpired paste; expired pastes purged within 24 h of TTL.",
        "Abuse-resistant: rate-limit anonymous IPs; CAPTCHA on suspicious traffic.",
        "Scale: 5M creates/day, 500M reads/day, ~50 TB hot blob storage.",
        "Cheap: blob is the cost driver; metadata DB stays small enough to fit in cache.",
    ],
    estimation={
        "creates_per_day": "5M",
        "reads_per_day": "500M",
        "qps_steady": "60 writes/sec, 6K reads/sec",
        "qps_peak": "5× steady at viral-paste moments",
        "avg_paste_size": "~10 KB; p99 ~1 MB; max 10 MB",
        "blob_storage": "~50 TB hot + ~200 TB warm/cold (un-expired but cold)",
        "metadata_db": "~50 GB for 5 years of metadata at 5M/day",
    },
    endpoints=[
        {"method": "POST", "path": "/v1/pastes",
         "description": "Create a paste; returns short_id and URL.",
         "body": "{body, language?, ttl_seconds?, visibility, title?}"},
        {"method": "GET", "path": "/v1/pastes/{short_id}",
         "description": "Fetch raw paste body + metadata (auth required if private)."},
        {"method": "GET", "path": "/v1/pastes/{short_id}/rendered",
         "description": "Fetch HTML-rendered (highlighted) version."},
        {"method": "PATCH", "path": "/v1/pastes/{short_id}",
         "description": "Update body/visibility/TTL — owner only.",
         "body": "{body?, visibility?, ttl_seconds?}"},
        {"method": "DELETE", "path": "/v1/pastes/{short_id}",
         "description": "Delete paste — owner or admin."},
        {"method": "GET", "path": "/v1/pastes/recent",
         "description": "List most recent public pastes (paginated)."},
        {"method": "GET", "path": "/v1/me/pastes",
         "description": "List authenticated user's own pastes (any visibility)."},
        {"method": "GET", "path": "/v1/search",
         "description": "Search within own pastes (signed-in only).",
         "body": "{q, lang?, after?, before?}"},
    ],
    tables=[
        {"name": "pastes",
         "columns": ["short_id CHAR(10) PK", "owner_user_id BIGINT NULL",
                     "blob_key VARCHAR(128)", "language VARCHAR(32) NULL",
                     "title VARCHAR(255) NULL",
                     "visibility ENUM('public','unlisted','private')",
                     "size_bytes INT", "compressed BOOLEAN",
                     "created_at BIGINT", "expires_at BIGINT NULL",
                     "deleted_at BIGINT NULL"]},
        {"name": "users",
         "columns": ["user_id BIGINT PK", "email VARCHAR(255)",
                     "password_hash VARCHAR(64)", "plan ENUM('free','pro')",
                     "created_at BIGINT"]},
        {"name": "rate_limits",
         "columns": ["bucket_key VARCHAR(64) PK", "tokens INT",
                     "refill_at BIGINT"]},
        {"name": "abuse_reports",
         "columns": ["report_id BIGINT PK", "short_id CHAR(10)",
                     "reporter VARCHAR(64)", "reason VARCHAR(64)",
                     "created_at BIGINT", "resolved_at BIGINT NULL"]},
    ],
    indexes=[
        "(short_id) on pastes — primary lookup",
        "(owner_user_id, created_at DESC) on pastes — user paste list",
        "(visibility, created_at DESC) on pastes — recent public feed (partial index where visibility='public')",
        "(expires_at) on pastes — TTL sweeper scan",
        "(short_id) on abuse_reports — moderation lookup",
    ],
    hld_desc=(
        "Stateless API tier behind a CDN-fronted load balancer. Writes generate a short ID via a "
        "base62-encoded counter (or random+collision-check), persist body to an object store keyed by "
        "blob_key, and write a thin metadata row to the DB. Reads hit Redis first (hot pastes), fall "
        "through to the metadata DB to resolve blob_key + ACL, then stream the body from the object "
        "store (or from CDN if previously cached). A render service does syntax highlighting on demand "
        "and caches the HTML. A TTL sweeper periodically reaps expired rows; Redis enforces hot expiry. "
        "Rate limiting is a token-bucket layer at the gateway, keyed by IP (anonymous) or user_id."
    ),
    hld_components=[
        {"name": "API Gateway", "role": "TLS terminate, auth, rate-limit, route"},
        {"name": "Paste Service", "role": "CRUD on pastes; ID minting; visibility checks"},
        {"name": "Render Service", "role": "Syntax-highlight to HTML on demand; cache results"},
        {"name": "Metadata DB", "role": "pastes / users / rate_limits — sharded by short_id"},
        {"name": "Object Store", "role": "Paste body blobs (compressed); cheap, durable"},
        {"name": "Hot Cache (Redis)", "role": "Hot paste body + ACL cache + TTL EX timers"},
        {"name": "TTL Sweeper", "role": "Periodic scan of expires_at; tombstones + blob delete"},
        {"name": "Abuse Pipeline", "role": "Spam/malware classifier; report-driven takedown"},
        {"name": "Search Index", "role": "Per-user inverted index over own pastes (optional)"},
        {"name": "Edge CDN", "role": "Cache rendered HTML and raw body for unlisted/public"},
    ],
    detailed_design={
        "id_generation": (
            "Short IDs are 8-character base62 (~218 trillion space). Two strategies: (1) random + "
            "INSERT ... ON CONFLICT retry — simple, collision rate negligible at our scale; or "
            "(2) per-shard counters base62-encoded — denser but leaks creation order. We pick "
            "random for unguessability of unlisted URLs; the scheme also doubles as the URL slug."
        ),
        "storage_split": (
            "Body lives in object storage (S3 / GCS) at key `pastes/{shard}/{short_id}`. The metadata "
            "row holds blob_key, ACL, TTL, language, size, compressed flag — typically ~200 bytes. "
            "This keeps the metadata DB tiny enough to run from RAM-resident indexes; the blob store "
            "handles the actual byte-volume problem. Hot bodies are cached in Redis up to 256 KB; "
            "larger pastes stream from object store via CDN."
        ),
        "ttl_strategy": (
            "Two-layer TTL. Layer 1: Redis SET ... EX {ttl} on the body cache so hot pastes silently "
            "stop serving from cache the moment they expire. Layer 2: DB column `expires_at` plus a "
            "sweeper that runs every 15 min, scans `expires_at < now()`, marks `deleted_at`, deletes "
            "the blob, and removes the metadata row. Reads always check `expires_at` even on cache hit "
            "— Redis EX is an optimisation, not the source of truth. 'Never' = NULL `expires_at`, "
            "skipped by sweeper."
        ),
        "visibility": (
            "Three levels. `public` is listed in the recent feed and indexable. `unlisted` is "
            "URL-only — never appears in feeds, never indexable, but anyone with the short_id can "
            "read. `private` requires authenticated owner (or shared-with list, future). The read API "
            "checks visibility before returning the body; the URL alone never grants access for "
            "private pastes. Visibility changes are immediate at the API; CDN cached entries get "
            "purged by tag (visibility-change → tag-based invalidation)."
        ),
        "syntax_highlighting": (
            "Stored body is always plaintext + a `language` hint (e.g. 'python', 'json'). Highlighting "
            "happens at /rendered using a server-side highlighter (Pygments / Tree-sitter / Shiki) "
            "and produces HTML. We cache the rendered HTML in CDN keyed by (short_id, body_hash, "
            "lang). Re-render only when the body or language changes (cache key changes). For "
            "huge pastes (>1 MB) we skip server render and ship raw text to the client; the browser "
            "highlights via highlight.js to keep API payloads small."
        ),
        "compression": (
            "Bodies > 4 KB are zstd-compressed before write (about 3-4× ratio on text/code/logs). "
            "The `compressed` flag drives decompression on read. Compression is a server-side "
            "concern; the API always speaks plaintext. We pick zstd over gzip for the speed/ratio "
            "trade-off at our hot-read path."
        ),
        "rate_limiting": (
            "Token-bucket at the gateway with two keys per request: anonymous → IP "
            "(e.g. 10 creates/hour, 60 reads/min), authenticated → user_id (free: 100 creates/day, "
            "pro: 10K). Counters in Redis with INCR + TTL. On bucket exhaustion: 429 + Retry-After. "
            "Suspicious traffic (datacenter ASN, fast burst) is escalated to CAPTCHA before the "
            "create endpoint."
        ),
        "search": (
            "Optional and only over the user's own pastes — public global search is intentionally "
            "not offered (privacy, abuse, cost). Per-user inverted index in Elasticsearch / OpenSearch "
            "indexed asynchronously after create. We don't index unlisted/private bodies for any "
            "global view; only the owner ever queries them."
        ),
        "abuse": (
            "Pipeline runs on every create: heuristic classifier (URL density, known-malware "
            "signatures, base64 payloads), DMCA / report queue with admin takedown, IP and account "
            "blocklists. Takedown is a soft-delete + blob purge, with the short_id grave-stoned so "
            "the URL returns 410 Gone forever rather than 404 (cleaner forensics)."
        ),
        "slo_contract": (
            "Read p95 < 300 ms (CDN hit < 50 ms, miss < 300 ms). Create p95 < 500 ms. TTL purge ≤ 24 h "
            "after expiry. Durability 11 nines on un-expired blobs. Rate-limit decisions < 5 ms p99."
        ),
    },
    trade_offs=[
        {"option": "Random vs sequential short_id",
         "for_random": "Unguessable URLs (real value for unlisted), no shard-counter coordination",
         "for_sequential": "Denser packing, sortable, easier monitoring",
         "recommendation": "Random — unguessability is the user-visible feature for unlisted pastes."},
        {"option": "Body in DB vs body in object store",
         "for_db": "One round-trip; transactional with metadata; simpler",
         "for_object_store": "Metadata DB stays tiny + cache-friendly; blob is 1000× cheaper per byte",
         "recommendation": "Object store — body bytes dominate cost and cache-poison the metadata DB."},
        {"option": "Server-side vs client-side syntax highlighting",
         "for_server": "Works on any client, fast first paint, SEO-friendly",
         "for_client": "Zero render compute on server, smaller API payload, supports huge pastes",
         "recommendation": "Hybrid — server for ≤1 MB (cache HTML), client for the long tail."},
        {"option": "Redis EX only vs DB sweeper for TTL",
         "for_redis_only": "Single layer, instant expiry on hot reads",
         "for_sweeper": "Durable purge survives Redis flush, drives blob GC and audit",
         "recommendation": "Both layers — Redis EX for hot fast-path, sweeper as the source of truth."},
    ],
    tips=[
        "Lead with the metadata-vs-blob split — same lesson as Dropbox at 1/10000 the scale.",
        "Random base62 short_id earns unguessability for unlisted URLs in one design choice.",
        "Two-layer TTL (Redis EX + sweeper) is the senior answer; pure-Redis loses pastes.",
        "Visibility lives at the read API, never just at the listing UI.",
        "Compress bodies, store plaintext + language; never store rendered HTML in the blob.",
        "Anonymous rate-limit per IP + CAPTCHA escalation is required, not a follow-up.",
    ],
    thought_process=[
        "1. Clarify: anonymous create, short URL, TTL, visibility, syntax highlight, abuse-prone.",
        "2. Estimate: 5M creates × ~10 KB → ~50 TB hot, 100:1 read:write → 6K read QPS.",
        "3. Split planes: tiny metadata DB + big blob in object store.",
        "4. APIs: POST create, GET raw, GET rendered, PATCH, DELETE, recent, search.",
        "5. Schema: pastes (short_id, blob_key, visibility, expires_at) + users + rate_limits.",
        "6. Short ID: random 8-char base62 with INSERT-ON-CONFLICT retry.",
        "7. TTL: two-layer — Redis EX for hot, DB sweeper for durable purge + blob GC.",
        "8. Visibility checked at read API; private requires auth; CDN tagged-invalidate on change.",
        "9. Render service highlights on demand and caches HTML; client-side for huge pastes.",
        "10. Compression (zstd) above 4 KB; metadata stays plaintext + language hint.",
        "11. Token-bucket rate limit at gateway; CAPTCHA escalation; abuse pipeline + takedown.",
        "12. Search only within own pastes; never global.",
    ],
    tags=["text", "sharing", "ttl", "blob", "key-value"],
    arch_nodes=[
        {"id": "client", "label": "Client / Browser", "type": "client"},
        {"id": "cdn", "label": "Edge CDN", "type": "cache"},
        {"id": "lb", "label": "API Gateway", "type": "lb"},
        {"id": "paste", "label": "Paste Service", "type": "server"},
        {"id": "render", "label": "Render Service", "type": "server"},
        {"id": "redis", "label": "Hot Cache (Redis)", "type": "cache"},
        {"id": "meta", "label": "Metadata DB", "type": "database"},
        {"id": "blob", "label": "Object Store", "type": "database"},
        {"id": "ttl", "label": "TTL Sweeper", "type": "service"},
        {"id": "abuse", "label": "Abuse Pipeline", "type": "service"},
        {"id": "search", "label": "Search Index", "type": "database"},
    ],
    arch_edges=[
        {"source": "client", "target": "cdn"},
        {"source": "cdn", "target": "lb", "label": "miss"},
        {"source": "lb", "target": "paste"},
        {"source": "lb", "target": "render"},
        {"source": "paste", "target": "redis", "label": "hot read/write"},
        {"source": "paste", "target": "meta", "label": "metadata"},
        {"source": "paste", "target": "blob", "label": "body"},
        {"source": "render", "target": "redis"},
        {"source": "render", "target": "blob"},
        {"source": "ttl", "target": "meta", "label": "scan expires_at"},
        {"source": "ttl", "target": "blob", "label": "purge"},
        {"source": "paste", "target": "abuse", "label": "classify on create"},
        {"source": "paste", "target": "search", "label": "async index (own)"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant U as Browser\n"
        "  participant CDN\n"
        "  participant API\n"
        "  participant R as Redis\n"
        "  participant DB as Metadata DB\n"
        "  participant OS as Object Store\n"
        "  Note over U,API: --- CREATE ---\n"
        "  U->>API: POST /v1/pastes (body, ttl, visibility)\n"
        "  API->>API: rate-limit check\n"
        "  API->>API: mint short_id (random base62)\n"
        "  API->>OS: PUT pastes/{shard}/{short_id} (zstd)\n"
        "  API->>DB: INSERT pastes (short_id, blob_key, expires_at, visibility)\n"
        "  API->>R: SET body EX ttl (if size<256KB)\n"
        "  API-->>U: 201 {url: /p/{short_id}}\n"
        "  Note over U,OS: --- READ ---\n"
        "  U->>CDN: GET /p/{short_id}/rendered\n"
        "  CDN-->>U: HTML (cache hit)\n"
        "  U->>CDN: GET /v1/pastes/{short_id} (raw)\n"
        "  CDN->>API: miss\n"
        "  API->>R: GET body\n"
        "  R-->>API: hit\n"
        "  API->>DB: visibility + expires_at check\n"
        "  API-->>CDN: 200 + Cache-Control\n"
        "  CDN-->>U: body"
    ),
    er_diagram=(
        "erDiagram\n"
        "  USER ||--o{ PASTE : owns\n"
        "  PASTE ||--o{ ABUSE_REPORT : flagged-by\n"
        "  PASTE { string short_id\n bigint owner_user_id\n string blob_key\n string visibility\n bigint expires_at }\n"
        "  USER { bigint user_id\n string email\n string plan }\n"
        "  ABUSE_REPORT { bigint report_id\n string short_id\n string reason }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B[Split metadata vs blob]\n"
        "  B --> C[Random base62 short_id]\n"
        "  C --> D{TTL?}\n"
        "  D -->|hot| E[Redis EX]\n"
        "  D -->|durable| F[DB sweeper + blob GC]\n"
        "  C --> G{Visibility?}\n"
        "  G -->|public| H[Listed in /recent]\n"
        "  G -->|unlisted| I[URL-only]\n"
        "  G -->|private| J[Auth required]\n"
        "  C --> K[Compress > 4KB]\n"
        "  K --> L[Render-time highlight + CDN cache]\n"
        "  C --> M[Token-bucket rate limit + CAPTCHA escalation]"
    ),
    tradeoff_title="TTL Enforcement Strategy",
    tradeoff_options=[
        {"label": "Redis EX only",
         "description": "Trust Redis to silently expire the body cache; metadata stays forever or "
                        "is reaped lazily on read.",
         "pros": ["Single layer", "Instant expiry on hot reads", "Zero sweeper infra"],
         "cons": ["Redis flush / failover loses TTL", "Blob storage grows unbounded",
                 "No durable audit of when something expired"]},
        {"label": "DB sweeper only",
         "description": "Periodic scan of `expires_at`; on hit, soft-delete + blob purge. Reads check "
                        "`expires_at` on every fetch.",
         "pros": ["Source of truth", "Drives blob GC", "Auditable"],
         "cons": ["Sweep latency means expired pastes can leak via reads briefly",
                 "Scan cost grows with table size"]},
        {"label": "Two-layer (Redis EX + DB sweeper)",
         "description": "Redis EX for hot fast-path (silent stop-serving on expiry), DB sweeper for "
                        "durable purge + blob GC. Reads always re-check `expires_at`.",
         "pros": ["Hot path has no leak window", "Durable purge survives cache loss",
                 "Drives blob cleanup"],
         "cons": ["Two systems to keep in sync", "Slightly more complex"]},
    ],
    tradeoff_rec=(
        "Two-layer. Redis EX gives instant hot-path expiry; the DB sweeper is the source of truth "
        "and the only thing that drives blob GC. Reads always check `expires_at` so a stale Redis "
        "entry can never serve an expired paste."
    ),
    senior_topics=[
        _topic("short-id-collisions",
               "Short ID Generation: Random vs Counter, Collision Rates",
               "Why random base62 wins for a paste service even though counter-based IDs are denser, "
               "and how INSERT-ON-CONFLICT retries make randomness safe at scale.",
               [
                   ("Random 8-char base62 space",
                    "62^8 ≈ 2.18 × 10^14. At 5M creates/day for 10 years → 1.8 × 10^10 IDs used → "
                    "0.008% of the space. Birthday-bound collision probability stays vanishingly small."),
                   ("INSERT-ON-CONFLICT loop",
                    "Generate candidate → INSERT ... ON CONFLICT DO NOTHING. If 0 rows inserted, retry "
                    "with a new random. Retry rate at 0.008% fill is < 1 in a billion creates."),
                   ("Why not sequential",
                    "Counter IDs leak creation order, expose request volume, and make unlisted URLs "
                    "guessable. The whole point of unlisted is unguessability."),
                   ("Why not UUIDs",
                    "UUID-128 in URL is 22 base64 chars — too long for a paste short URL. 8 base62 chars "
                    "is the sweet spot of unguessable + memorable + fits in a tweet."),
               ],
               diagram=(
                   "graph TD\n"
                   "  A[generate 8-char base62] --> B[INSERT pastes ON CONFLICT DO NOTHING]\n"
                   "  B --> C{rows=1?}\n"
                   "  C -->|yes| D[return short_id]\n"
                   "  C -->|no| A"
               )),
        _topic("ttl-two-layer",
               "Two-Layer TTL: Redis EX + DB Sweeper + Blob GC",
               "How to expire pastes durably without leaking blob storage, and why a single layer is "
               "always wrong at scale.",
               [
                   ("Hot path with Redis EX",
                    "On create, SET body EX ttl in Redis. Subsequent reads either hit the body or, "
                    "after expiry, fall through to the DB. The DB read still re-checks `expires_at` to "
                    "catch a stale Redis or a sweeper that hasn't run yet — Redis is an optimisation, "
                    "never authority."),
                   ("Sweeper as source of truth",
                    "Every 15 min, scan `WHERE expires_at < now() AND deleted_at IS NULL` ordered by "
                    "expires_at. Mark `deleted_at`, enqueue blob delete. The sweeper holds a Redis "
                    "lease so only one instance runs per shard."),
                   ("Blob GC",
                    "A separate worker drains the blob-delete queue, issuing object-store DELETE calls. "
                    "Lag this by hours so a fast 'undelete' (admin) can still recover the body. After "
                    "the GC runs, the row's blob_key is null and the short_id returns 410 Gone."),
                   ("Why both layers matter",
                    "Redis-only: a flush or failover makes expired pastes serve again until manually "
                    "purged. Sweeper-only: hot reads can leak an expired paste for up to one sweep "
                    "interval. Both layers eliminate both failure modes."),
                   ("'Never' TTL",
                    "Stored as `expires_at = NULL`. Sweeper skips them. Redis still applies a "
                    "long EX (e.g. 7 days) for cache hygiene; on miss the read re-populates."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant API\n  participant R as Redis\n  participant DB\n"
                   "  participant SW as Sweeper\n  participant OS as Object Store\n"
                   "  API->>R: SET body EX ttl\n"
                   "  API->>DB: INSERT expires_at=now+ttl\n"
                   "  Note over SW,OS: every 15 min\n"
                   "  SW->>DB: SELECT WHERE expires_at < now\n"
                   "  SW->>DB: UPDATE deleted_at = now\n"
                   "  SW->>OS: DELETE blob (lagged)\n"
                   "  Note over API,R: read path\n"
                   "  API->>R: GET body\n"
                   "  R-->>API: miss (EX fired)\n"
                   "  API->>DB: re-check expires_at\n"
                   "  DB-->>API: 410 Gone"
               )),
        _topic("visibility-and-acl",
               "Visibility Levels: Public / Unlisted / Private",
               "How three levels are enforced end-to-end, and the difference between hiding from a "
               "feed and actually denying access.",
               [
                   ("Public",
                    "Listed in /v1/pastes/recent (paginated by created_at DESC). Indexable by "
                    "external search engines (no robots restriction). Cacheable by CDN with a long TTL "
                    "since the body is by definition shareable."),
                   ("Unlisted",
                    "Never appears in feeds, never indexable (X-Robots-Tag: noindex). Anyone with the "
                    "short_id can read — security-by-unguessability of the random ID. Cacheable by CDN "
                    "but with a lower TTL so revocation propagates."),
                   ("Private",
                    "Read API returns 404 unless the requester is the owner (or, future, on the "
                    "shared-with list). Cache-Control: private, no-store. CDN never caches the body."),
                   ("Visibility change",
                    "A patch that flips visibility purges the CDN cache by tag (paste:{short_id}) and "
                    "invalidates Redis. Public→private transitions are the dangerous case: between the "
                    "DB write and the cache purge, a stale CDN edge could still serve the body. "
                    "We accept a few-second window and document it; for hard secrets the answer is "
                    "'create a new private paste'."),
                   ("Enforcement layer",
                    "Visibility is enforced in the Paste Service read handler, NOT in the listing UI. "
                    "Direct GET /v1/pastes/{short_id} runs the same ACL check as the rendered route — "
                    "skipping that is the textbook IDOR vulnerability."),
               ]),
        _topic("anonymous-rate-limiting",
               "Rate Limiting Anonymous IPs Without Punishing Real Users",
               "Token-bucket sizing, IP-vs-account keys, CAPTCHA escalation, and the NAT/CGNAT "
               "problem.",
               [
                   ("Token-bucket basics",
                    "Per (key, route) bucket: capacity C, refill R tokens/sec. Each request takes 1 "
                    "token; empty bucket → 429 + Retry-After. Counters in Redis with INCR and TTL on "
                    "the bucket key. p99 < 5 ms is achievable."),
                   ("Anonymous: IP key",
                    "Anonymous create: 10/hour, read: 60/min. Aggressive enough to slow malware "
                    "uploaders, loose enough that a school's NAT can still legitimately use the site. "
                    "Cellular CGNAT is the worst case — we soften limits for known mobile-carrier ASNs."),
                   ("Authenticated: user_id key",
                    "Free: 100 creates/day, Pro: 10K. Independent of IP, so a paying user travelling "
                    "through bad CGNAT isn't penalised."),
                   ("CAPTCHA escalation",
                    "Anomaly signals: datacenter ASN, fast burst (>5 creates in 10 s), classifier "
                    "high score on body. Escalate to CAPTCHA before the create endpoint; on pass, "
                    "lift the bucket for 1 hour."),
                   ("IP reputation",
                    "Tor exits, known abuse netblocks, and DigitalOcean / AWS / GCP egress get "
                    "tighter buckets by default. Maintain a daily-refreshed allow-list for legitimate "
                    "research crawlers."),
               ],
               diagram=(
                   "graph LR\n"
                   "  REQ[request] --> KEY{auth?}\n"
                   "  KEY -->|yes| U[bucket: user_id]\n"
                   "  KEY -->|no| IP[bucket: ip]\n"
                   "  U --> CHK{tokens > 0?}\n"
                   "  IP --> CHK\n"
                   "  CHK -->|yes| ALLOW[serve]\n"
                   "  CHK -->|no| DENY[429 + Retry-After]\n"
                   "  IP --> ANO[anomaly score]\n"
                   "  ANO -->|high| CAP[CAPTCHA challenge]"
               )),
    ],
)
