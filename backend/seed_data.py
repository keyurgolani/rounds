from database import SessionLocal
from models import (
    SystemDesignQuestion, CodingQuestion,
    BehavioralQuestion, BehavioralCategory,
)


def seed_all():
    db = SessionLocal()
    try:
        if db.query(SystemDesignQuestion).first():
            return
        _seed_system_design(db)
        _seed_coding(db)
        _seed_behavioral_categories(db)
        db.flush()
        _seed_behavioral(db)
        db.commit()
    finally:
        db.close()


def _seed_system_design(db):
    questions = [
        SystemDesignQuestion(
            title="Design a URL Shortener (like bit.ly)",
            difficulty="Medium",
            description="Design a scalable URL shortening service that takes a long URL and returns a short alias. When users visit the alias, they should be redirected to the original URL.",
            hints=[
                "Start with the write/read ratio — URL shorteners are read-heavy (99:1 read:write).",
                "Think about the encoding scheme: base62 gives you 62^7 = 3.5 trillion unique IDs with just 7 characters.",
                "Consider caching hot URLs at the redirect layer to avoid DB hits.",
                "Don't forget analytics — tracking clicks, geolocation, referrers is a core feature.",
            ],
            constraints=[
                "Short URLs should be at most 7 characters",
                "Redirects must happen in <100ms at the 99th percentile",
                "Support 100M+ URLs",
                "Handle 10K new URLs/second, 1M redirects/second",
                "URLs should never expire (unless explicitly set)",
            ],
            requirements_functional=[
                "Given a long URL, generate a unique short alias",
                "When users access the short alias, redirect to the original URL",
                "Custom aliases (users can pick their own short code)",
                "Analytics dashboard: click count, geographic data, referrers",
                "User accounts to manage URLs",
                "API for programmatic access",
                "URL expiration (optional TTL)",
            ],
            requirements_nonfunctional=[
                "High availability — redirects must work even during partial failures",
                "Low latency — redirect should feel instant",
                "Durability — shortened URLs must not be lost",
                "Scalability — handle billions of URLs",
                "Security — prevent malicious URL creation, rate limiting",
            ],
            estimation={
                "total_urls": "1 billion URLs",
                "url_length_avg": "100 bytes (long) + 7 bytes (short)",
                "storage": "~100GB for URLs + metadata",
                "qps_write": "10K writes/sec",
                "qps_read": "1M reads/sec",
                "bandwidth": "~100GB/day for redirects",
            },
            api_design={
                "endpoints": [
                    {"method": "POST", "path": "/api/urls", "description": "Create short URL", "body": '{"long_url": "...", "custom_alias": "...", "ttl": 3600}'},
                    {"method": "GET", "path": "/{short_code}", "description": "Redirect to long URL"},
                    {"method": "GET", "path": "/api/urls/{short_code}/stats", "description": "Get click analytics"},
                    {"method": "DELETE", "path": "/api/urls/{short_code}", "description": "Delete URL"},
                ],
            },
            database_schema={
                "tables": [
                    {"name": "urls", "columns": ["id BIGINT PK", "short_code VARCHAR(7) UNIQUE", "long_url TEXT", "user_id BIGINT FK", "created_at TIMESTAMP", "expires_at TIMESTAMP", "click_count BIGINT"]},
                    {"name": "click_analytics", "columns": ["id BIGINT PK", "short_code VARCHAR(7)", "ip_address INET", "country VARCHAR(2)", "referrer TEXT", "user_agent TEXT", "clicked_at TIMESTAMP"]},
                    {"name": "users", "columns": ["id BIGINT PK", "email VARCHAR(255)", "created_at TIMESTAMP"]},
                ],
                "indexes": ["short_code (unique, B-tree)", "user_id", "click_analytics(short_code, clicked_at)"],
            },
            high_level_design={
                "description": "Client → Load Balancer → API Servers (write path) / Redirect Servers (read path) → Cache (Redis) → Database (sharded PostgreSQL/NoSQL). Use a key-generation service (KGS) to pre-generate unique IDs.",
                "components": [
                    {"name": "API Gateway / Load Balancer", "role": "Route traffic, SSL termination, rate limiting"},
                    {"name": "Write Servers", "role": "Handle URL creation requests, generate short codes, write to DB"},
                    {"name": "Redirect Servers", "role": "Handle short URL lookups, serve 301/302 redirects"},
                    {"name": "Cache Layer (Redis)", "role": "Cache hot URLs for sub-ms redirect lookups"},
                    {"name": "Key Generation Service", "role": "Pre-generate unique IDs to avoid collisions and DB coordination"},
                    {"name": "Database", "role": "Persistent storage for URL mappings and analytics"},
                ],
            },
            detailed_design={
                "encoding": "Use base62 encoding (a-z, A-Z, 0-9). Pre-generate IDs with KGS. Two tables: used_keys and unused_keys. KGS picks from unused, moves to used.",
                "caching": "Redis cache with LRU eviction. Cache miss → DB lookup → cache the result. TTL matches URL expiration.",
                "sharding": "Shard by short_code hash or range-based. Consistent hashing for even distribution.",
                "reliability": "Multi-AZ deployment, read replicas for redirect servers, eventual consistency for analytics.",
                "slo_contract": "Redirect SLO: 99.99% availability, p99 <50ms (error budget 4.3 min/month). Analytics SLO: eventual within 60s, loss ≤0.1% acceptable (freshness, not latency). The two paths fail independently — an analytics outage never degrades redirects.",
            },
            trade_offs=[
                {"option": "Pre-generated keys vs computed keys", "for_pre_generated": "No collision risk, no distributed locking, fast writes", "for_computed": "Simpler, no extra KGS service", "recommendation": "Pre-generated for scale"},
                {"option": "301 (Permanent) vs 302 (Found) redirect", "for_301": "Browser/CDN caches indefinitely — fewer origin hits, preserves SEO equity, lower latency for repeat visitors. Cost: clicks invisible after first visit; destination un-editable without user cache eviction.", "for_302": "Every click reaches origin — accurate per-click analytics, editable destinations post-creation, protection against link hijacking via rewrite.", "recommendation": "302 is the default for marketing/attribution/editable links. 301 only for vanity or permanent URLs where per-click analytics aren't product-critical. Use 307/308 to preserve non-GET methods. Prefer 410 Gone over 404 for expired links (faster SEO de-indexing). See Senior Topics → 301 vs 302 Defended for the full analysis."},
                {"option": "SQL vs NoSQL", "for_sql": "ACID guarantees, familiar querying", "for_nosql": "Better horizontal scaling for billions of rows", "recommendation": "Start with SQL, migrate hot path to NoSQL"},
            ],
            tips=[
                "Mention that URL shorteners are essentially a distributed hash table.",
                "Always discuss the trade-off between 301 (permanent) and 302 (temporary) redirects — this is a classic interview gotcha.",
                "Bring up the Key Generation Service early — it shows systems thinking.",
                "Don't forget to discuss how you'd prevent abuse (rate limiting, content scanning).",
            ],
            thought_process=[
                "1. Clarify requirements — what features beyond basic shorten/redirect?",
                "2. Estimate scale — how many URLs? What QPS? Storage?",
                "3. Define the API surface",
                "4. Sketch the high-level architecture (load balancer, app servers, cache, DB)",
                "5. Dive into the key generation strategy (this is the core algorithmic question)",
                "6. Discuss caching strategy for the read-heavy workload",
                "7. Talk about sharding if scale warrants it",
                "8. Wrap up with reliability, monitoring, and security considerations",
            ],
            architecture_diagram={
                "nodes": [
                    {"id": "client", "label": "Client", "type": "client"},
                    {"id": "lb", "label": "Load Balancer", "type": "lb"},
                    {"id": "api", "label": "API Server", "type": "server"},
                    {"id": "kgs", "label": "Key Gen Service", "type": "service"},
                    {"id": "redirect", "label": "Redirect Server", "type": "server"},
                    {"id": "cache", "label": "Redis Cache", "type": "cache"},
                    {"id": "db", "label": "URL Database", "type": "database"},
                    {"id": "analytics", "label": "Analytics DB", "type": "database"},
                ],
                "edges": [
                    {"source": "client", "target": "lb", "label": "HTTPS", "animated": True},
                    {"source": "lb", "target": "api", "animated": True},
                    {"source": "lb", "target": "redirect", "animated": True},
                    {"source": "api", "target": "kgs", "label": "get key"},
                    {"source": "api", "target": "db", "label": "INSERT"},
                    {"source": "redirect", "target": "cache", "label": "GET"},
                    {"source": "cache", "target": "db", "label": "miss"},
                    {"source": "redirect", "target": "analytics", "label": "log click"},
                ],
            },
            sequence_diagram=(
                "sequenceDiagram\n"
                "  participant C as Client\n"
                "  participant API as API Server\n"
                "  participant KGS as Key Gen Service\n"
                "  participant DB as Database\n"
                "  C->>API: POST /api/urls {long_url}\n"
                "  API->>KGS: getNextKey()\n"
                "  KGS-->>API: short_code\n"
                "  API->>DB: INSERT urls\n"
                "  DB-->>API: ok\n"
                "  API-->>C: 201 {short_url}"
            ),
            er_diagram=(
                "erDiagram\n"
                "  USERS ||--o{ URLS : owns\n"
                "  URLS ||--o{ CLICK_ANALYTICS : has\n"
                "  USERS {\n"
                "    bigint id PK\n"
                "    varchar email\n"
                "    timestamp created_at\n"
                "  }\n"
                "  URLS {\n"
                "    bigint id PK\n"
                "    varchar short_code\n"
                "    text long_url\n"
                "    bigint user_id FK\n"
                "    timestamp created_at\n"
                "  }\n"
                "  CLICK_ANALYTICS {\n"
                "    bigint id PK\n"
                "    varchar short_code\n"
                "    inet ip_address\n"
                "    timestamp clicked_at\n"
                "  }"
            ),
            thought_flow=(
                "graph TD\n"
                "  A[Read problem] --> B{Read or write heavy?}\n"
                "  B -->|Read 99:1| C[Cache hot URLs]\n"
                "  B --> D[Estimate scale]\n"
                "  D --> E[Choose encoding: base62]\n"
                "  E --> F{Generate keys how?}\n"
                "  F -->|Pre-gen| G[Add KGS]\n"
                "  F -->|Hash| H[Risk collisions]\n"
                "  G --> I[Design API + DB]\n"
                "  I --> J[Discuss sharding]\n"
                "  J --> K[Reliability + analytics]"
            ),
            tradeoff_visual={
                "title": "Pre-generated keys vs Computed keys",
                "options": [
                    {
                        "label": "Pre-generated (KGS)",
                        "description": "A separate service hands out unique base62 codes from a pool.",
                        "pros": [
                            "No collisions, no distributed locking",
                            "Fast writes — single key lookup",
                            "Easy to rate-limit at the KGS",
                        ],
                        "cons": [
                            "Extra service to operate",
                            "KGS becomes single point of contention",
                        ],
                    },
                    {
                        "label": "Computed (hash)",
                        "description": "Hash long_url with MD5/SHA, base62-encode, take first N chars.",
                        "pros": [
                            "Stateless — no extra service",
                            "Same long URL maps to same short code (idempotent)",
                        ],
                        "cons": [
                            "Collision handling required (probe, salt)",
                            "Slower under write contention",
                        ],
                    },
                ],
                "recommendation": "Pre-generated for high-scale; computed is fine for read-heavy small services.",
            },
            senior_topics=[
                {
                    "id": "cqrs-split",
                    "title": "CQRS: Redirect Path vs Analytics Path",
                    "summary": "Treat redirects and analytics as separate subsystems with independent SLOs. A failing analytics pipeline must never degrade redirect availability.",
                    "sections": [
                        {
                            "heading": "Why senior candidates separate these",
                            "body": "Mid-level answers write click events inline with the redirect (`INSERT INTO clicks ...`) or to the same DB as the URL mapping. This couples their availability: every analytics DB hiccup becomes a redirect outage, and heavy dashboard queries contend with the 1M-QPS hot path. The senior framing is: the redirect is a single read from a hot cache; analytics is an eventually-consistent stream processor. Two pipelines, two SLOs, failing independently.",
                        },
                        {
                            "heading": "The architecture",
                            "body": "Redirect path: Client → CDN → Redirect Server → Redis (hot) → DB (cold miss). Analytics path: Redirect Server → async emit (Kafka / NSQ topic) → clicks consumer → ClickHouse (or Druid / columnar OLAP). The emit is fire-and-forget with a bounded local buffer — if Kafka is unreachable, drop events past the buffer rather than block the response. Snowflake-ID-style event IDs provide deduplication and monotonic ordering downstream.",
                        },
                        {
                            "heading": "SLOs & failure semantics",
                            "body": "Redirect: availability 99.99%, p99 latency <50ms, error budget 4.3 min/month. Analytics: eventual within 60s, loss ≤0.1% acceptable, freshness-SLO (not latency-SLO). When analytics is down, redirects must still succeed and dashboards show 'delayed' rather than 'down'.",
                        },
                        {
                            "heading": "Why Kafka/NSQ and not direct writes",
                            "body": "Topic-channel fan-out lets multiple independent consumers see the same event stream without coupling: real-time dashboard consumer, billing consumer, fraud/ML consumer, long-term archive consumer. Bitly's NSQ post describes exactly this pattern running at ~35K msg/s on commodity hardware.",
                        },
                        {
                            "heading": "What 'done' looks like on a whiteboard",
                            "body": "Two lanes drawn horizontally: top lane ends at '301 response in <50ms'; bottom lane forks off the redirect server and ends at 'ClickHouse table partitioned by hour'. The fork point is explicitly labeled 'fire-and-forget + bounded buffer'. Interviewers love this diagram.",
                        },
                    ],
                    "diagram": (
                        "sequenceDiagram\n"
                        "  participant C as Client\n"
                        "  participant R as Redirect Server\n"
                        "  participant K as Kafka\n"
                        "  participant W as Click Worker\n"
                        "  participant OLAP as ClickHouse\n"
                        "  C->>R: GET /abc123\n"
                        "  R->>R: lookup (Redis hit)\n"
                        "  R-->>C: 302 → long URL (p99 <50ms)\n"
                        "  R->>K: emit click event (fire-and-forget)\n"
                        "  K->>W: deliver\n"
                        "  W->>OLAP: INSERT INTO clicks_by_hour"
                    ),
                    "sources": [
                        {"label": "Bitly Engineering — NSQ origin post", "url": "https://word.bitly.com/post/33232969144/nsq"},
                        {"label": "DevelopersVoice — URL Shorteners at Scale", "url": "https://developersvoice.com/blog/practical-design/url-shorteners-at-scale-practical-guide/"},
                    ],
                },
                {
                    "id": "abuse-safety-subsystem",
                    "title": "Abuse & Safety as an Architected Subsystem",
                    "summary": "Safety is a pipeline, not a blocklist lookup — check at submission, re-check over time, and mediate at click time. NDSS 2025 found 22 of 88 dedicated shorteners exploitable because domain-level trust decays.",
                    "sections": [
                        {
                            "heading": "Three checkpoints, not one",
                            "body": "Submission-time: reputation lookup against Google Safe Browsing + VirusTotal + internal deny-list + ML model on creation pattern (account age, IP, destination domain rarity). Periodic: re-scan every stored destination on a priority queue weighted by click volume. Click-time: check a 'recently flagged' bloom filter; on hit, serve an interstitial warning instead of a 302.",
                        },
                        {
                            "heading": "Why domain allowlists alone fail",
                            "body": "NDSS 2025's 'Misdirection of Trust' tested 88 dedicated shorteners and found 22 abusable via three attacks: (a) domain ownership transfer after submission, (b) post-injection on trusted pages, (c) open redirects on the destination. Static domain-level trust is rebuttable.",
                        },
                        {
                            "heading": "Click-time interstitial pattern",
                            "body": "When a stored destination is freshly flagged but existing short codes point to it, you can't retroactively break the link without breaking the internet. Instead serve /go?u=<code> with a 2-second warning page + 'continue anyway' + 'report this link'. Bitly does this.",
                        },
                        {
                            "heading": "Abuse signals for ML",
                            "body": "Velocity (N links/minute/account), geo-skew (single IP, global destination fanout), domain-age (newly-registered targets), keyword filter (phishing lure terms in custom aliases), co-creation patterns (shared fingerprints across 'different' accounts).",
                        },
                        {
                            "heading": "Operational hand-off",
                            "body": "Flagged links route to a human review queue with SLA (15 min for trending, 24h for baseline). Dashboard surfaces 'links created in last hour flagged post-hoc' as a leading abuse-rate indicator.",
                        },
                    ],
                    "diagram": (
                        "graph TD\n"
                        "  A[Submit URL] --> B{Reputation check}\n"
                        "  B -->|clean| C[Store + index]\n"
                        "  B -->|flagged| R[Reject with reason]\n"
                        "  C --> D[Periodic re-scan queue]\n"
                        "  D --> E{Still clean?}\n"
                        "  E -->|yes| C\n"
                        "  E -->|no| F[Mark flagged]\n"
                        "  G[Click] --> H{In flagged bloom?}\n"
                        "  H -->|no| I[302 redirect]\n"
                        "  H -->|yes| J[Interstitial warning]"
                    ),
                    "sources": [
                        {"label": "NDSS 2025 — Misdirection of Trust", "url": "https://www.ndss-symposium.org/ndss-paper/misdirection-of-trust-demystifying-the-abuse-of-dedicated-url-shortening-service/"},
                        {"label": "Bitly Blog — Scalable secure short links", "url": "https://bitly.com/blog/scalable-secure-short-links/"},
                    ],
                },
                {
                    "id": "301-vs-302-defended",
                    "title": "301 vs 302 — Defended, Not Defaulted",
                    "summary": "The choice is product-driven, not cacheability-driven. 302 preserves analytics fidelity and destination editability; 301 surrenders both to the browser/CDN permanently.",
                    "sections": [
                        {
                            "heading": "What 301 actually costs you",
                            "body": "Browsers and CDNs cache 301s indefinitely (spec says 'permanent'). After the first click on a device, subsequent clicks never reach your origin — zero analytics, zero ability to change the destination. Changing a 301 target requires user cache eviction, which you can't force. Bots and Safari are the harshest about this.",
                        },
                        {
                            "heading": "Why 302 is the default",
                            "body": "Every click reaches origin → accurate per-click analytics → A/B testing, attribution, editable destinations. Cost: your hot cache absorbs the load (see Cache Hierarchy + Stampede Defenses).",
                        },
                        {
                            "heading": "When 301 wins",
                            "body": "Vanity domains (yourname.co/hi) where clicks aren't product-critical; SEO canonicalization for content migrations; link-in-bio tools that also want edge-cacheability. Pair with explicit Cache-Control: max-age=... so you can bound the permanence.",
                        },
                        {
                            "heading": "410 Gone vs 404 Not Found",
                            "body": "Expired link → 410 Gone (SEO de-indexes faster, crawler stops re-checking). Never existed → 404. Mid-level answers use 404 for everything; crawler behavior diverges materially.",
                        },
                        {
                            "heading": "307 / 308 — the 'preserve method' variants",
                            "body": "If a short code ever shortens a POST request (rare but real for webhook vanity URLs), 301/302 change POST → GET. 308 (permanent) and 307 (temporary) preserve method. Mention these if interviewer probes into RESTful nuance.",
                        },
                    ],
                    "sources": [
                        {"label": "systemdesign.one — URL Shortening System Design", "url": "https://systemdesign.one/url-shortening-system-design/"},
                        {"label": "Hello Interview — Bitly breakdown", "url": "https://www.hellointerview.com/learn/system-design/problem-breakdowns/bitly"},
                        {"label": "AlgoMaster — Design a URL Shortener", "url": "https://blog.algomaster.io/p/design-a-url-shortener"},
                    ],
                },
                {
                    "id": "multi-region-writes",
                    "title": "Multi-Region Write Topology — Disjoint Counter Ranges",
                    "summary": "Partition the 64-bit ID space by region using high-order bits. Writes stay local, collisions are impossible by construction, zero global coordination on the write path.",
                    "sections": [
                        {
                            "heading": "Why global sequences don't scale",
                            "body": "A single global counter (SELECT nextval('seq')) forces cross-region coordination on every write. At 10K writes/sec globally with 3 regions, that's 3 RTTs/write — unusable. Spanner hides this with TrueTime at a price tier most startups skip.",
                        },
                        {
                            "heading": "Snowflake-style layout",
                            "body": "64-bit ID = 41 bits millisecond-timestamp + 10 bits region/datacenter ID + 12 bits sequence. Timestamp gives monotonicity across the global set, region bits guarantee disjointness, sequence handles within-millisecond concurrency. Each region generates locally, never coordinates.",
                        },
                        {
                            "heading": "Cross-region reads via replication",
                            "body": "URL mapping is immutable-after-create, so active-active with last-write-wins is trivially safe. Cassandra multi-DC, CockroachDB regions, or DynamoDB Global Tables all work. Read traffic hits the nearest region; write traffic pins to the user's home region.",
                        },
                        {
                            "heading": "Region failure and recovery",
                            "body": "If us-east is down, writes there fail fast (no retry loop to a dead region). When it returns, its locally-generated IDs are by construction non-conflicting with what other regions emitted while it was down. No merge step, no conflict resolution.",
                        },
                        {
                            "heading": "Alternative: per-region KGS range allocation",
                            "body": "If you already have a key-generation service, have it hand each region a range (e.g., region us-east gets [1B, 2B), eu-west gets [2B, 3B)). Simpler than Snowflake bit-packing, same disjointness property, loses the monotonic-timestamp analytics benefit.",
                        },
                    ],
                    "sources": [
                        {"label": "Hello Interview — Bitly breakdown", "url": "https://www.hellointerview.com/learn/system-design/problem-breakdowns/bitly"},
                        {"label": "DevelopersVoice — URL Shorteners at Scale", "url": "https://developersvoice.com/blog/practical-design/url-shorteners-at-scale-practical-guide/"},
                    ],
                },
                {
                    "id": "cache-hierarchy-stampede",
                    "title": "Cache Hierarchy + Stampede Defenses for Viral Links",
                    "summary": "A viral tweet sends 100K+ QPS at one short code. Single-tier Redis isn't enough — L1 in-process + L2 Redis + L3 CDN, plus single-flight coalescing to survive cold-cache bursts.",
                    "sections": [
                        {
                            "heading": "Three layers, three TTLs",
                            "body": "L1: per-server in-process LRU (LruCache, 5–15s TTL, sub-ms latency, 10K entries). L2: Redis cluster (minutes–hours TTL, 1–2ms latency, warm set of millions). L3: CDN caching the 302 response directly with Cache-Control: max-age=60. At L3 cache hit, origin sees nothing — viral wave absorbed at the edge.",
                        },
                        {
                            "heading": "Thundering-herd math",
                            "body": "A hot key expires; 10K concurrent clients all miss. Without coalescing, 10K DB queries hit simultaneously. With single-flight (one lookup, N waiters), 1 DB query. The coalescing logic belongs in the L1 layer — a sync.Once (Go) or asyncio.Event per key.",
                        },
                        {
                            "heading": "Jittered TTLs",
                            "body": "Caches expiring synchronously causes correlated stampedes ('TTL storm'). Randomize by ±20% (ttl * (1 + rand(-0.2, 0.2))). Zero complexity, meaningful real-world impact on correlated-load events.",
                        },
                        {
                            "heading": "Soft-TTL with background refresh",
                            "body": "Serve stale for up to 2× TTL while one background worker fetches fresh. Latency stays p99-clean even during refresh; correctness stays within staleness budget.",
                        },
                        {
                            "heading": "CDN as the ultimate cache (the 302-friendly version)",
                            "body": "Cache-Control: private, max-age=60 on the 302 response lets CDNs serve the redirect for 60s. Viral wave absorbed at edge; origin load bounded. Cost: 60s of stale analytics, which is acceptable for marketing-attribution use cases but not for rug-pull abuse where you need to break a link now (see Abuse & Safety).",
                        },
                    ],
                    "diagram": (
                        "graph LR\n"
                        "  C[Client] --> CDN[L3: CDN 302 cache]\n"
                        "  CDN -->|miss| LB[Load Balancer]\n"
                        "  LB --> S[Redirect Server]\n"
                        "  S --> L1[L1: in-process LRU]\n"
                        "  L1 -->|miss| L2[L2: Redis]\n"
                        "  L2 -->|miss| DB[DB shard]"
                    ),
                    "sources": [
                        {"label": "DevelopersVoice — URL Shorteners at Scale", "url": "https://developersvoice.com/blog/practical-design/url-shorteners-at-scale-practical-guide/"},
                        {"label": "Bitly Engineering — NSQ origin post", "url": "https://word.bitly.com/post/33232969144/nsq"},
                    ],
                },
                {
                    "id": "deep-linking-contract",
                    "title": "Deep-Linking & Multi-Platform Redirect Contract",
                    "summary": "Post-Firebase-Dynamic-Links shutdown (Aug 25, 2025), short-link servers must serve different responses to iOS, Android, desktop, and unfurl bots. The contract is content-negotiation on steroids.",
                    "sections": [
                        {
                            "heading": ".well-known/ manifests",
                            "body": "iOS Universal Links require https://yourdomain.com/.well-known/apple-app-site-association (JSON, no extension, served as application/json). Android App Links require https://yourdomain.com/.well-known/assetlinks.json with SHA-256 cert fingerprints of your APK signing key. Both are checked by OS on app install; misconfigured → links open in browser instead of app.",
                        },
                        {
                            "heading": "User-Agent routing",
                            "body": "On GET, inspect UA: iOS Safari → HTML with Universal Link meta + fallback JS; Android Chrome → HTTP 302 to intent:// URL; desktop → direct 302; known bots (Slackbot, Twitterbot, Discordbot, iMessage-link-preview) → HTML with OG tags from DB, no redirect. Keep a bot allowlist, not a denylist — denylists miss new bots and inflate click counts.",
                        },
                        {
                            "heading": "OG-tag preview HTML",
                            "body": "Render <meta property='og:title'>, og:description, og:image, og:url from the stored destination's pre-scraped preview data. Bots consume tags, bail; no 302 means your click counter stays honest.",
                        },
                        {
                            "heading": "Deferred deep linking",
                            "body": "If app isn't installed → redirect to App Store / Play Store → after install, replay intent via: copy-to-clipboard + app-first-launch-read on iOS, or Google Play Install Referrer on Android. Not perfect (pasteboard permissions tightening on iOS 14+) but standard.",
                        },
                        {
                            "heading": "Firebase Dynamic Links context",
                            "body": "Google EOL'd FDL on Aug 25, 2025 citing 'low-quality crawler traffic' as a primary motivation — every app that used FDL for deep-linking + preview is now rebuilding this in-house, and interviewers at mobile-first companies ask about it. Bot-inflated click counts were Google's stated reason for shutting it down; mention you've solved it with UA allowlisting.",
                        },
                    ],
                    "sources": [
                        {"label": "Andrew Zaikin (Medium) — Replacing Firebase Dynamic Links", "url": "https://medium.com/@azaikin/firebase-dynamic-links-is-shutting-down-heres-how-i-replaced-it-with-a-custom-deep-link-server-e8dfeb7ec6b3"},
                        {"label": "Firebase Dynamic Links Deprecation FAQ", "url": "https://firebase.google.com/support/dynamic-links-faq"},
                    ],
                },
                {
                    "id": "link-rot-product",
                    "title": "Link Rot as a Product Feature",
                    "summary": "Pew 2024: 38% of 2013 web pages are dead by 2023, 23% of news-article links are broken. If your shortener ages, destination liveness is a UX problem you must architect for.",
                    "sections": [
                        {
                            "heading": "The Pew numbers",
                            "body": "38% of web pages from 2013 inaccessible in 2023. 23% of news sites have at least one broken reference. Government sites: 21%. Social media is worse — 50% of cited-to tweets from 2015 are gone (deleted, account-banned, or private). Shorteners outlive their destinations; this is the UX problem you inherit.",
                        },
                        {
                            "heading": "Passive vs active liveness checking",
                            "body": "Passive: log 4xx/5xx responses when users click — cheap, biases toward popular links. Active: crawl a priority queue (weighted by log(click_count)) on a schedule — expensive, catches cold links before users hit them. Run both; cross-reference results.",
                        },
                        {
                            "heading": "Wayback Machine fallback",
                            "body": "On destination 404/410, offer 'View archived version' via the Internet Archive CDX API (https://web.archive.org/cdx/search/cdx?url=...). Graceful degradation: your shortener still delivers value even when the destination is dead.",
                        },
                        {
                            "heading": "'Destination unreachable' UX",
                            "body": "Don't return a blank error. Render a branded page: 'The original destination is no longer available. Here's what we know: last seen [date], last working snapshot [Wayback link], report a better destination [form].' Product-grade link rot handling.",
                        },
                        {
                            "heading": "Destination change detection",
                            "body": "Hash the destination's HTTP response body (or just the <title> + <h1>) at submission and re-scan. If the hash drifts materially, flag the link for re-moderation — the domain was sold, the page was injected, or the content was replaced. Catches a class of abuse that reputation-scoring misses.",
                        },
                    ],
                    "sources": [
                        {"label": "Pew Research 2024 — When Online Content Disappears", "url": "https://www.pewresearch.org/wp-content/uploads/sites/20/2024/05/pl_2024.05.17_link-rot_report.pdf"},
                        {"label": "NDSS 2025 — Misdirection of Trust", "url": "https://www.ndss-symposium.org/ndss-paper/misdirection-of-trust-demystifying-the-abuse-of-dedicated-url-shortening-service/"},
                    ],
                },
            ],
            tags=["url-shortener", "hashing", "caching", "distributed-systems", "database-design"],
        ),
        SystemDesignQuestion(
            title="Design a Chat Application (like WhatsApp/Slack)",
            difficulty="Hard",
            description="Design a real-time messaging application supporting one-on-one chats, group chats, read receipts, online presence, and message history.",
            hints=[
                "The core challenge is the real-time communication layer — WebSocket vs long-polling vs SSE.",
                "Think about message ordering — in distributed systems, global ordering is expensive.",
                "Consider the read/write pattern: users write messages sequentially but read from many conversations.",
                "Group chats are fundamentally different from 1:1 — fan-out on write vs fan-out on read.",
            ],
            constraints=[
                "Support 50M DAU",
                "Message delivery in <500ms",
                "Support groups up to 500 members",
                "Messages must be durable and ordered within a conversation",
                "Support text, images, files up to 100MB",
            ],
            requirements_functional=[
                "One-on-one messaging",
                "Group messaging (up to 500 members)",
                "Online/presence status",
                "Read receipts (per-message)",
                "Typing indicators",
                "Message history and search",
                "File/image sharing",
                "Push notifications for offline users",
                "Message deletion",
            ],
            requirements_nonfunctional=[
                "Low latency message delivery (<500ms end-to-end)",
                "High availability (99.99%)",
                "Eventual consistency for read receipts and presence",
                "Durability — messages must not be lost",
                "Scalability to 50M+ concurrent connections",
            ],
            estimation={
                "dau": "50M",
                "messages_per_user_per_day": "50",
                "total_messages_per_day": "2.5B",
                "message_size_avg": "200 bytes",
                "storage_per_day": "~500GB",
                "concurrent_connections": "10M",
                "qps": "~30K messages/sec peak",
            },
            api_design={
                "endpoints": [
                    {"method": "WS", "path": "/ws", "description": "WebSocket connection for real-time messaging"},
                    {"method": "POST", "path": "/api/messages", "description": "Send message (fallback HTTP)"},
                    {"method": "GET", "path": "/api/conversations/{id}/messages", "description": "Get message history"},
                    {"method": "GET", "path": "/api/conversations", "description": "List conversations"},
                    {"method": "PUT", "path": "/api/messages/{id}/read", "description": "Mark as read"},
                    {"method": "GET", "path": "/api/users/{id}/presence", "description": "Get online status"},
                ],
            },
            database_schema={
                "tables": [
                    {"name": "messages", "columns": ["id BIGINT PK", "conversation_id BIGINT FK", "sender_id BIGINT FK", "content TEXT", "message_type ENUM", "created_at TIMESTAMP"]},
                    {"name": "conversations", "columns": ["id BIGINT PK", "type ENUM('direct','group')", "name VARCHAR(255)", "created_at TIMESTAMP"]},
                    {"name": "conversation_members", "columns": ["conversation_id BIGINT FK", "user_id BIGINT FK", "last_read_message_id BIGINT", "joined_at TIMESTAMP"]},
                    {"name": "users", "columns": ["id BIGINT PK", "username VARCHAR(100)", "status ENUM('online','offline','away')", "last_seen TIMESTAMP"]},
                ],
                "indexes": ["messages(conversation_id, created_at)", "conversation_members(user_id)", "users(status)"],
            },
            high_level_design={
                "description": "Clients connect via WebSocket to Connection Servers (stateless, behind load balancer). Connection Servers publish messages to a Message Queue. Worker servers consume from queue, persist to DB, and fan-out to recipients via their Connection Server. Presence service tracks online status via heartbeat.",
                "components": [
                    {"name": "Connection Servers", "role": "Maintain WebSocket connections, handle incoming/outgoing messages"},
                    {"name": "Message Queue (Kafka)", "role": "Buffer messages, enable fan-out to group members, ensure delivery"},
                    {"name": "Message Workers", "role": "Persist messages to DB, trigger push notifications for offline users"},
                    {"name": "Presence Service", "role": "Track online/offline status via heartbeats, publish status changes"},
                    {"name": "Notification Service", "role": "Send push notifications (APNs/FCM) for offline recipients"},
                    {"name": "Database Cluster", "role": "Store messages (Cassandra for write-heavy) and metadata (PostgreSQL)"},
                ],
            },
            detailed_design={
                "connection_management": "Use WebSocket with heartbeat every 30s. Load balancer (L7) routes connections. Session mapping: user_id → connection_server stored in Redis.",
                "message_flow": "Sender → Connection Server → Kafka topic (per conversation) → Message Worker → DB write → lookup recipient connections → push to recipient Connection Servers → deliver via WebSocket",
                "group_chat": "Fan-out on write: message worker writes once, then pushes to all group members' connection servers. Use Kafka consumer groups for parallel fan-out.",
                "presence": "Clients send heartbeat every 30s. Presence service updates Redis (user_id → status). Subscribers get presence updates via pub/sub.",
                "message_ordering": "Sequence numbers per conversation (not global). Use DB-sequence or logical timestamp within conversation.",
            },
            trade_offs=[
                {"option": "WebSocket vs Server-Sent Events vs Long Polling", "for_ws": "Full duplex, lowest latency, standard protocol", "for_sse": "Simpler, HTTP-based, one-way", "for_lp": "No special protocol needed", "recommendation": "WebSocket for real-time messaging"},
                {"option": "Fan-out on write vs fan-out on read", "for_write": "Read is fast (pre-computed), good for active groups", "for_read": "Less write amplification, good for inactive groups", "recommendation": "Fan-out on write for groups ≤500 members"},
                {"option": "Cassandra vs ScyllaDB vs PostgreSQL for messages", "for_cassandra": "Write-optimized, linear scalability, no single point of failure. JVM GC pauses become a p99 problem at very high write rates.", "for_postgres": "ACID, rich queries, simpler ops — but doesn't scale to billions of messages/day.", "recommendation": "Cassandra for message storage at modest scale; Postgres for metadata. ScyllaDB (C++ rewrite, shard-per-core, no GC) is the modern replacement when JVM-induced p99 spikes matter — Discord migrated 177 Cassandra nodes to 72 Scylla nodes in 2023 specifically to eliminate GC pauses. See Senior Topics → Hot-Partition Absorption for the full pattern."},
            ],
            tips=[
                "Start by establishing the real-time communication mechanism — this sets the architecture.",
                "Message ordering is always a follow-up question. Have a clear answer: per-conversation sequence numbers.",
                "Don't underestimate presence — it's a surprisingly complex distributed systems problem.",
                "Mention idempotency: if a message is sent twice (network retry), the recipient should see it once.",
            ],
            thought_process=[
                "1. Clarify: 1:1 vs group chat? How big are groups? Any special features (threads, reactions)?",
                "2. Estimate: DAU, messages/day, concurrent connections",
                "3. Choose real-time protocol (WebSocket) and explain why",
                "4. Design the message flow: send → persist → deliver",
                "5. Tackle group chat fan-out strategy",
                "6. Design presence/online status system",
                "7. Discuss push notifications for offline users",
                "8. Address message ordering, idempotency, and reliability",
            ],
            architecture_diagram={
                "nodes": [
                    {"id": "client", "label": "Client (mobile/web)", "type": "client"},
                    {"id": "lb", "label": "L7 Load Balancer", "type": "lb"},
                    {"id": "conn", "label": "Connection Server (WS)", "type": "server"},
                    {"id": "kafka", "label": "Kafka", "type": "queue"},
                    {"id": "worker", "label": "Message Worker", "type": "service"},
                    {"id": "presence", "label": "Presence Service", "type": "service"},
                    {"id": "redis", "label": "Redis (presence/session)", "type": "cache"},
                    {"id": "msgdb", "label": "Cassandra (messages)", "type": "database"},
                    {"id": "metadb", "label": "Postgres (metadata)", "type": "database"},
                    {"id": "push", "label": "Push (APNs/FCM)", "type": "service"},
                ],
                "edges": [
                    {"source": "client", "target": "lb", "label": "WS", "animated": True},
                    {"source": "lb", "target": "conn", "animated": True},
                    {"source": "conn", "target": "kafka", "label": "publish"},
                    {"source": "kafka", "target": "worker", "label": "consume"},
                    {"source": "worker", "target": "msgdb"},
                    {"source": "worker", "target": "metadb"},
                    {"source": "worker", "target": "conn", "label": "fan-out"},
                    {"source": "worker", "target": "push", "label": "if offline"},
                    {"source": "conn", "target": "presence", "label": "heartbeat"},
                    {"source": "presence", "target": "redis"},
                ],
            },
            sequence_diagram=(
                "sequenceDiagram\n"
                "  participant A as User A (sender)\n"
                "  participant CA as Conn Server A\n"
                "  participant K as Kafka\n"
                "  participant W as Worker\n"
                "  participant CB as Conn Server B\n"
                "  participant B as User B (recipient)\n"
                "  A->>CA: WebSocket: send msg\n"
                "  CA->>K: publish(conv_id, msg)\n"
                "  K->>W: deliver\n"
                "  W->>W: persist to Cassandra\n"
                "  W->>CB: push to recipient's conn server\n"
                "  CB-->>B: WebSocket: deliver msg\n"
                "  B-->>CB: ack (read receipt)"
            ),
            er_diagram=(
                "erDiagram\n"
                "  USERS ||--o{ CONVERSATION_MEMBERS : in\n"
                "  CONVERSATIONS ||--o{ CONVERSATION_MEMBERS : has\n"
                "  CONVERSATIONS ||--o{ MESSAGES : contains\n"
                "  USERS ||--o{ MESSAGES : sent\n"
                "  USERS {\n"
                "    bigint id PK\n"
                "    varchar username\n"
                "    enum status\n"
                "    timestamp last_seen\n"
                "  }\n"
                "  CONVERSATIONS {\n"
                "    bigint id PK\n"
                "    enum type\n"
                "    varchar name\n"
                "  }\n"
                "  MESSAGES {\n"
                "    bigint id PK\n"
                "    bigint conversation_id FK\n"
                "    bigint sender_id FK\n"
                "    text content\n"
                "    timestamp created_at\n"
                "  }"
            ),
            thought_flow=(
                "graph TD\n"
                "  A[\"1:1 or group?\"] --> B{Real-time protocol}\n"
                "  B -->|WebSocket| C[Connection servers]\n"
                "  C --> D[Message queue]\n"
                "  D --> E{Group fan-out}\n"
                "  E -->|on write| F[Persist + push]\n"
                "  E -->|on read| G[Compute on fetch]\n"
                "  F --> H[Presence + push]\n"
                "  H --> I[Ordering + idempotency]"
            ),
            tradeoff_visual={
                "title": "Fan-out on write vs Fan-out on read",
                "options": [
                    {
                        "label": "Fan-out on write",
                        "description": "Worker writes one message, then pushes a copy to every group member's mailbox.",
                        "pros": [
                            "Reads are O(1) — message already in inbox",
                            "Great for active groups (chat, live channels)",
                        ],
                        "cons": [
                            "Write amplification = N (group size)",
                            "Wasted writes for inactive members",
                        ],
                    },
                    {
                        "label": "Fan-out on read",
                        "description": "Worker writes once. Each reader pulls the conversation timeline on demand.",
                        "pros": [
                            "Cheap writes",
                            "Good for huge inactive groups",
                        ],
                        "cons": [
                            "Reads are O(N conversations)",
                            "Harder to push notify",
                        ],
                    },
                ],
                "recommendation": "On write for groups ≤ 500. On read for very large channels.",
            },
            senior_topics=[
                {
                    "id": "mls-group-e2ee",
                    "title": "MLS (RFC 9420) — Group E2EE That Actually Scales",
                    "summary": "Pairwise Signal needs O(N²) channels for an N-member group; MLS via TreeKEM does it in O(log N), making 50,000-member E2EE groups practical. Discord's DAVE (Sept 2024) is the first major production deployment.",
                    "sections": [
                        {
                            "heading": "Why pairwise Signal breaks for groups",
                            "body": "The Signal protocol (X3DH + Double Ratchet) is genuinely E2EE for 1:1, but a group of N members requires O(N²) pairwise channels. Adding/removing one member requires re-keying with each other member individually. Beyond ~100 members, the cryptographic and bandwidth overhead is prohibitive — and a single membership change becomes a fan-out storm.",
                        },
                        {
                            "heading": "Sender Keys (WhatsApp's compromise)",
                            "body": "WhatsApp uses Sender Keys: each member encrypts their messages with a single per-sender key shared with the group. O(N) fan-out instead of O(N²). Cost: forward secrecy is weaker (a compromised member's key exposes their history for as long as it was current), and key rotation on membership change is O(N) — every other member must receive the new key.",
                        },
                        {
                            "heading": "MLS / TreeKEM — the logarithmic answer",
                            "body": "IETF RFC 9420 (July 2023). Members form a left-balanced binary tree; each leaf is a member, each internal node holds a derived key. Re-keying after add/remove only updates one path (root → affected leaf): O(log N) operations per change. A 50,000-member group rekeys in ~16 messages instead of 50,000.",
                        },
                        {
                            "heading": "Epoch + commit state machine",
                            "body": "MLS state advances in discrete epochs. Membership changes are batched into Commit messages; all clients advance to the new epoch atomically once they see the same Commit. Asynchronous (no roundtrip required), tolerant of out-of-order delivery, and audit-friendly because every state transition is a signed Commit.",
                        },
                        {
                            "heading": "DAVE: the first production MLS at scale",
                            "body": "Discord shipped MLS for audio/video calls in September 2024 — the first major consumer rollout. Sender keys rotate on every join/leave event within ~10 seconds. Audited by Trail of Bits. Pairs with PQXDH (Signal's post-quantum hybrid handshake) for forward-secret + post-quantum-secure group bootstrap.",
                        },
                    ],
                    "diagram": (
                        "graph TD\n"
                        "  R[Root key]\n"
                        "  R --> L[Left subtree key]\n"
                        "  R --> RR[Right subtree key]\n"
                        "  L --> A[Alice]\n"
                        "  L --> B[Bob]\n"
                        "  RR --> C[Carol]\n"
                        "  RR --> D[Dave]"
                    ),
                    "sources": [
                        {"label": "IETF RFC 9420 — MLS", "url": "https://datatracker.ietf.org/doc/rfc9420/"},
                        {"label": "Discord — DAVE: E2EE for Audio & Video", "url": "https://discord.com/blog/meet-dave-e2ee-for-audio-video"},
                        {"label": "Signal — PQXDH spec", "url": "https://signal.org/docs/specifications/pqxdh/"},
                    ],
                },
                {
                    "id": "hot-partition-coalescing",
                    "title": "Hot-Partition Absorption via Request Coalescing",
                    "summary": "Sharding by channel_id alone doesn't save you when one channel goes viral. Discord's answer is a Rust data-service tier in front of the database that coalesces concurrent reads of the same row into a single DB hit.",
                    "sections": [
                        {
                            "heading": "The hot-partition problem",
                            "body": "Even with consistent-hash sharding by channel_id, one viral channel sends all its traffic to a single Cassandra/Scylla partition. At 100K reads/sec on one row, that partition becomes a hotspot — the rest of the cluster is fine, but that one node dies. Resharding doesn't help because virality is unpredictable.",
                        },
                        {
                            "heading": "Why caching alone isn't enough",
                            "body": "A Redis cache helps for repeat reads of the same message, but viral conversations have constantly arriving new messages. The N-th reader misses the cache, and 10K simultaneous misses thunder the DB. Cache TTLs jittered to ±20% don't save you when every key expires under load.",
                        },
                        {
                            "heading": "The coalescing tier",
                            "body": "Discord built a Rust data service in front of Scylla that detects identical concurrent queries within a short window and merges them into one DB hit, then fans the result back to all waiters. The data service holds the 'in-flight read' state explicitly — single-flight semantics at the storage tier, not just the cache tier.",
                        },
                        {
                            "heading": "Consistent-hash routing to the data service, not just the DB",
                            "body": "Routes for a given channel_id always land on the same data-service node, ensuring the coalescing pool can detect duplicates. If routing were random, each node would see one request and the coalescing wouldn't help. The principle: coalescing requires affinity, not just sharding.",
                        },
                        {
                            "heading": "Cassandra → ScyllaDB as a forcing function",
                            "body": "Discord migrated 177 Cassandra nodes to 72 Scylla nodes in 2023. The motivation wasn't TPS — it was JVM GC pauses causing latency spikes that, combined with hot-partition pressure, made p99 unmanageable. Scylla's C++ shard-per-core architecture eliminated GC pauses entirely. The lesson: at very high write rates, runtime choice (BEAM/JVM/Rust) is a p99 architecture concern.",
                        },
                    ],
                    "diagram": (
                        "graph LR\n"
                        "  C[10K Clients] --> H[Consistent hash by channel_id]\n"
                        "  H --> DS[Data Service node X]\n"
                        "  DS --> CO[Coalescing pool: 1 in-flight read]\n"
                        "  CO --> DB[(Scylla partition)]\n"
                        "  CO -.->|fan-out result| DS\n"
                        "  DS -.->|fan-out result| C"
                    ),
                    "sources": [
                        {"label": "Discord — How Discord Stores Trillions of Messages", "url": "https://discord.com/blog/how-discord-stores-trillions-of-messages"},
                    ],
                },
                {
                    "id": "connection-fleet-edge-cache",
                    "title": "Connection-Fleet Failover + Edge-Cache Subscribed to the Event Stream",
                    "summary": "16M channels held in memory on stateful Channel Servers. CHARM-style consistent hashing fails over in <20s; Slack's Flannel edge cache subscribes to the same WebSocket event stream to pre-warm session boot — payload cut 44× and P99 from 2000ms to 200ms.",
                    "sections": [
                        {
                            "heading": "Why 'use consistent hashing' is junior",
                            "body": "The interview cliché is 'consistent hashing solves it.' A senior candidate explains what happens when a stateful Channel Server holding 16 million channels dies. State-loss is unacceptable, connection thrash is unacceptable, and the replacement node has to take over without re-fetching everything from disk.",
                        },
                        {
                            "heading": "CHARM ring with <20s replacement",
                            "body": "Slack's CHARM is a consistent-hash ring designed for stateful workloads with bounded recovery time. New owner of a slot streams the relevant in-memory state from the previous owner (or a replica), warming up in under 20 seconds. Documented production numbers — not theoretical.",
                        },
                        {
                            "heading": "Session boot is the silent killer",
                            "body": "When a user opens Slack, the client downloads its current view: every channel they're in, recent messages, member lists, presence, etc. For a 32K-user team, this naive payload is huge. Pre-Flannel, P99 session-boot latency at Slack was around 2 seconds — and getting worse linearly with team size.",
                        },
                        {
                            "heading": "Flannel: an edge cache that subscribes to the event stream",
                            "body": "Slack runs a per-region edge service called Flannel. It subscribes to the same WebSocket event topics that real-time users receive, and uses those events to maintain a pre-warmed snapshot of every team's state. When a user reconnects, Flannel serves the boot payload from local memory — no DB roundtrip.",
                        },
                        {
                            "heading": "The architectural insight + real numbers",
                            "body": "Flannel cut the boot payload 44× for 32K-user teams. P99 channel-membership read dropped from 2000ms → 200ms. The deeper insight: the same event stream that drives real-time messaging also drives cache freshness — no separate invalidation pipeline needed. Saying 'we'll piggyback the cache on the event stream' is an instant senior-tell.",
                        },
                    ],
                    "sources": [
                        {"label": "Slack Engineering — Real-time Messaging", "url": "https://slack.engineering/real-time-messaging/"},
                        {"label": "Slack Engineering — Flannel Edge Cache", "url": "https://slack.engineering/flannel-an-application-level-edge-cache-to-make-slack-scale/"},
                    ],
                },
                {
                    "id": "e2ee-media-pipeline",
                    "title": "E2EE Media Pipeline — Encoded-Transform over SFU + MLS Sender Keys",
                    "summary": "Voice and video E2EE inside an SFU sounds impossible — the SFU needs to packetize and forward media. Encoded-transform (Chrome 86+) lets you encrypt at the codec output and decrypt at the codec input, leaving the SFU to handle opaque ciphertext.",
                    "sections": [
                        {
                            "heading": "Why naive WebRTC isn't E2EE",
                            "body": "Standard WebRTC encrypts in transit (DTLS-SRTP), but the SFU (Selective Forwarding Unit) terminates that encryption. The SFU sees plaintext media to do its job: forwarding to N participants, codec tuning, simulcast layer selection. 'WebRTC encrypted' is hop-by-hop, not end-to-end.",
                        },
                        {
                            "heading": "The encoded-transform unlock",
                            "body": "Chrome 86+ exposed RTCRtpScriptTransform, letting JavaScript intercept media frames after the encoder and before the packetizer. You can encrypt the encoded frames; the packetizer/SFU sees opaque bytes; the receiver decrypts before its decoder. SFU keeps doing its job; E2EE survives.",
                        },
                        {
                            "heading": "Sender keys via MLS commits",
                            "body": "Each call participant has a sender key derived from the call's MLS group state. When a participant joins or leaves, the gateway issues an MLS Commit, all clients advance epoch, and sender keys rotate within ~10 seconds. The SFU (which never holds the sender key) keeps forwarding ciphertext throughout — no media disruption during membership change.",
                        },
                        {
                            "heading": "Voice gateway as MLS external sender",
                            "body": "DAVE's clever piece: the call's signaling gateway acts as the MLS 'external sender' — it commits add/remove operations into the group state without ever holding any decryption key. Solves the bootstrap problem (who initiates the group when nobody has talked yet) without weakening end-to-end guarantees.",
                        },
                        {
                            "heading": "Stateless SFU recovery",
                            "body": "Discord's SFU stores no per-call state durably. On node failure, clients re-signal to a new SFU which reconstructs forwarding state from the signaling channel. Combined with MLS sender keys (rotated on every connectivity event anyway), failover is invisible to participants — no key re-establishment needed because the keys were never tied to the SFU instance.",
                        },
                    ],
                    "sources": [
                        {"label": "Discord — DAVE: E2EE for Audio & Video", "url": "https://discord.com/blog/meet-dave-e2ee-for-audio-video"},
                        {"label": "DAVE Protocol Whitepaper", "url": "https://daveprotocol.com/"},
                        {"label": "Discord — 2.5M Concurrent Voice Users with WebRTC", "url": "https://discord.com/blog/how-discord-handles-two-and-half-million-concurrent-voice-users-using-webrtc"},
                    ],
                },
                {
                    "id": "runtime-choice-design",
                    "title": "Runtime Choice as a First-Class Design Decision",
                    "summary": "Most candidates pick Go or Node and move on. Senior candidates know that the actor-model runtime — BEAM (WhatsApp, Discord), JVM/Akka (LinkedIn, Slack), or Rust/C++ — is load-bearing for chat at scale, and that escaping into Rust NIFs/services is now standard.",
                    "sections": [
                        {
                            "heading": "WhatsApp on FreeBSD + BEAM",
                            "body": "2 to 2.8 million TCP connections per box, in production, on commodity hardware. Hot code reload as a deploy primitive (no fleet drain). Achieved by deep BEAM scheduler tuning + FreeBSD kernel tuning, not by framework magic. Erlang's process-per-connection model is the table stakes for connection density at this scale.",
                        },
                        {
                            "heading": "Discord — BEAM with Rust escape hatches",
                            "body": "Discord scaled Elixir to 5 million concurrent users with a per-session GenServer + per-guild GenServer topology. They hit Registry stampede issues on large guilds and rescued the BEAM hot path with Rust NIFs (Zlib, sort). Pattern: stay on BEAM for the actor model and IO orchestration; escape to Rust for CPU-bound paths.",
                        },
                        {
                            "heading": "LinkedIn on JVM + Akka + SSE",
                            "body": "Akka's actor-per-connection runs hundreds of thousands of actors on a few JVM threads. LinkedIn chose SSE over WebSocket because corporate firewalls and HTTP/2 multiplexing favor SSE; topic→frontend subscription routing goes through Couchbase, not Kafka, accepting rare event loss for sub-100ms p99. A different load profile leads to different decisions.",
                        },
                        {
                            "heading": "The Rust infiltration trend",
                            "body": "Discord's data services (in front of Scylla) are Rust. Cloudflare's edge is a mix of Rust and C. Scylla itself is C++. The trend across 2023–2026: BEAM/JVM for orchestration and IO, Rust/C++ for hot paths. Pure-runtime answers ('we'll write it all in Go') are increasingly rare at the senior tier.",
                        },
                        {
                            "heading": "Why this matters in interviews",
                            "body": "When asked 'what runtime?' the senior answer ties choice to load profile: 'BEAM if connection-bound (hundreds of thousands per node); JVM if you have an existing Akka shop; Rust for the data plane below; never Node for stateful long-lived connections at this scale.' Picking a runtime for a reason — naming the load characteristics that drive the choice — signals depth.",
                        },
                    ],
                    "sources": [
                        {"label": "High Scalability — WhatsApp Architecture", "url": "https://highscalability.com/the-whatsapp-architecture-facebook-bought-for-19-billion/"},
                        {"label": "Discord — Scaled Elixir to 5M Concurrent Users", "url": "https://discord.com/blog/how-discord-scaled-elixir-to-5-000-000-concurrent-users"},
                        {"label": "LinkedIn Real-Time Messaging (InfoQ)", "url": "https://www.infoq.com/podcasts/linkedin-realtime-messaging-architecture/"},
                    ],
                },
                {
                    "id": "push-notification-constraints",
                    "title": "Push Notifications as a Constrained-Resource Architecture",
                    "summary": "APNs caps silent pushes at ~2-3/hour per device. PushKit is its own credential lane for VoIP. Token rotation, provider fallback, and server-side coalescing turn push from a checkbox into a real architecture concern.",
                    "sections": [
                        {
                            "heading": "Provider rate caps drive architecture",
                            "body": "Apple's APNs limits silent (background) pushes to ~2-3 per hour per device, with throttling beyond that. FCM has its own quotas. A naive 'one push per message' architecture cannot ship at WhatsApp scale — you must coalesce server-side: batch unread counts, aggregate notifications per app launch, not per message.",
                        },
                        {
                            "heading": "Token database design",
                            "body": "Each device has multiple tokens: APNs production, APNs sandbox, FCM, PushKit. Tokens rotate (app reinstall, OS reset, key rollover). Token table is keyed by (user_id, device_id) with current token + provider + last-validated-at. Stale-token cleanup runs on every 410-Gone or invalid-registration response from a provider.",
                        },
                        {
                            "heading": "PushKit for VoIP — separate credential lane",
                            "body": "Incoming-call notifications cannot use regular APNs (latency, no app-wake guarantee). iOS provides PushKit: a 5KB-payload, bypasses-throttle, app-launches-before-user-decides credential channel. Different cert, different token, different code path from regular APNs. Required if you want incoming-call rings to work when the app is backgrounded.",
                        },
                        {
                            "heading": "Silent vs user-visible prioritization",
                            "body": "User-visible pushes ('New message from Bob') trigger banners and consume the budget aggressively. Silent pushes (sync triggers, badge updates) have their own (smaller) budget. Architectural decision: which messages deserve a user-visible push, which are silent-sync-only, which are dropped entirely? Mismatch this and Apple throttles you.",
                        },
                        {
                            "heading": "Provider fallback semantics",
                            "body": "When APNs is degraded (real outages happen), fall back to opportunistic local sync on next app open. When FCM is degraded, fall back to long-polling on next foregrounded session. Don't try to multi-route a single notification through both providers — duplicates are worse than misses. The right answer is degraded-mode behaviors per provider, not provider failover.",
                        },
                    ],
                    "sources": [
                        {"label": "Apple — APNs Documentation", "url": "https://developer.apple.com/documentation/usernotifications"},
                        {"label": "Apple — PushKit", "url": "https://developer.apple.com/documentation/pushkit"},
                    ],
                },
                {
                    "id": "regulatory-design-pressure",
                    "title": "Regulatory Pressure as a Design Constraint",
                    "summary": "E2EE is no longer just a crypto choice — it's a jurisdictional and product choice. EU Chat Control, the UK Online Safety Act, and proposed client-side scanning have forced explicit 'we will leave' commitments from Signal and WhatsApp. A staff candidate names these.",
                    "sections": [
                        {
                            "heading": "Why this is an architecture topic",
                            "body": "Government-mandated client-side scanning (CSAM detection, terrorist-content filters) breaks E2EE in a specific way: the content remains encrypted in transit, but the client must hash + check + report before encrypting. From the user's perspective, the system is no longer end-to-end private. Refusing to implement client-side scanning is now an architectural decision, not just a policy one.",
                        },
                        {
                            "heading": "EU Chat Control (CSAR proposal)",
                            "body": "Repeatedly proposed, repeatedly stalled — currently active legislation in 2025–2026 that would require messaging services to scan all media at the client. Signal's CEO publicly stated they would withdraw from the EU rather than implement. WhatsApp echoed similar sentiments. The architectural ask is not 'add a scanner' but 'redesign so we can comply with mandate and still call ourselves E2EE' — which has no satisfying answer.",
                        },
                        {
                            "heading": "UK Online Safety Act (in force 2023)",
                            "body": "Includes a 'spy clause' giving Ofcom power to require messaging providers to deploy 'accredited technology' for content scanning. Signal stated they would leave the UK if compelled. Ofcom has so far declined to invoke the power, but the legal framework remains. Senior candidates know the framework exists and what services have committed to do.",
                        },
                        {
                            "heading": "Apple NeuralHash retraction",
                            "body": "In 2021, Apple announced on-device hash-based CSAM scanning before iCloud upload. After backlash from cryptographers (collisions, scope-creep concerns) the project was withdrawn. The episode is the canonical case study for why client-side scanning is architecturally fragile — collision attacks, scope creep, and chilling effects all materialize quickly once the mechanism exists.",
                        },
                        {
                            "heading": "What seniors say about it",
                            "body": "When asked 'how do you handle CSAM/terrorism reports in an E2EE messenger,' the answer separates concerns: (a) encrypted content is unreachable by design; (b) abuse signals come from metadata + user reports + sender-rate-limiting + spam-pattern ML — not from content scanning; (c) honoring legitimate subpoenas is possible for metadata (timestamps, identities, group memberships) without breaking encryption. Sealed sender + sealed groups deliberately push more of even that into the unreachable column.",
                        },
                    ],
                    "sources": [
                        {"label": "EFF — UK Online Safety Bill is Extreme", "url": "https://www.eff.org/deeplinks/2023/09/uk-government-knows-how-extreme-online-safety-bill"},
                        {"label": "Computer Weekly — Signal on EU Chat Control", "url": "https://www.computerweekly.com/news/366631949/EU-Chat-Control-plans-pose-existential-catastrophic-risk-to-encryption-says-Signal"},
                    ],
                },
            ],
            tags=["real-time", "websocket", "messaging", "distributed-systems", "fan-out"],
        ),
        SystemDesignQuestion(
            title="Design a Rate Limiter",
            difficulty="Medium",
            description="Design a distributed rate limiting service that can throttle API requests per user, per IP, or per endpoint. Should support multiple algorithms and work across a distributed fleet of servers.",
            hints=[
                "Start by choosing the algorithm — each has different trade-offs (token bucket, sliding window, fixed window, leaky bucket).",
                "The hard part is distributed rate limiting — a single Redis instance becomes a bottleneck.",
                "Think about where the rate limiter sits: client-side, server-side, or as middleware/API gateway.",
                "Don't forget to handle the edge case of clock skew in distributed systems.",
            ],
            constraints=[
                "Rate limit per user: 100 requests/minute for free tier, 1000/minute for paid",
                "Rate limit per IP: 1000 requests/hour",
                "Must work across multiple server instances",
                "Rate limiting decision must be made in <10ms",
                "Support burst traffic (allow short bursts above limit)",
            ],
            requirements_functional=[
                "Limit requests per user, per IP, per API endpoint",
                "Support configurable rate limits (requests per second/minute/hour)",
                "Return proper HTTP 429 with Retry-After header",
                "Support different tiers (free, paid, enterprise)",
                "Allow burst traffic within reason",
                "Dashboard to view rate limit usage",
            ],
            requirements_nonfunctional=[
                "Low latency — rate limit check must not add significant overhead",
                "Distributed — consistent limits across multiple server instances",
                "Accurate — no significant over-counting or under-counting",
                "Fault-tolerant — if rate limiter fails, prefer allowing traffic over blocking (fail-open)",
            ],
            estimation={
                "total_users": "10M",
                "peak_qps": "100K requests/sec",
                "rate_limit_entries": "~10M active counters at any time",
                "memory_per_entry": "~100 bytes (key + counter + timestamp)",
                "total_memory": "~1GB in Redis",
            },
            api_design={
                "endpoints": [
                    {"method": "MIDDLEWARE", "path": "/*", "description": "Check rate limit before forwarding request"},
                    {"method": "GET", "path": "/api/rate-limits/{user_id}", "description": "Get current rate limit status"},
                    {"method": "PUT", "path": "/api/rate-limits/config", "description": "Update rate limit configuration"},
                ],
                "headers": [
                    "X-RateLimit-Limit: 100",
                    "X-RateLimit-Remaining: 95",
                    "X-RateLimit-Reset: 1620000000",
                    "Retry-After: 30 (on 429)",
                ],
            },
            database_schema={
                "description": "Use Redis for counters (in-memory). Configuration stored in PostgreSQL.",
                "redis_keys": [
                    "rate_limit:{user_id}:{endpoint} → counter value (with TTL)",
                    "rate_limit_config:{tier}:{endpoint} → JSON config",
                ],
            },
            high_level_design={
                "description": "API Gateway / Middleware intercepts every request → checks rate limiter (Redis-backed) → if under limit, forward to service; if over limit, return 429. The rate limiter is implemented as a library (client-side) and/or as a service (server-side).",
                "components": [
                    {"name": "API Gateway / Middleware", "role": "Intercept requests, extract rate limit key (user_id, IP, endpoint)"},
                    {"name": "Rate Limiter Service", "role": "Evaluate rate limit using chosen algorithm, return allow/deny"},
                    {"name": "Redis Cluster", "role": "Store distributed counters with atomic operations (INCR + EXPIRE)"},
                    {"name": "Config Service", "role": "Manage rate limit rules per tier/endpoint"},
                ],
            },
            detailed_design={
                "algorithms": {
                    "fixed_window": "Simple: INCR key, set TTL on first request. Problem: allows 2x traffic at window boundaries.",
                    "sliding_window_log": "Store timestamps of each request in a sorted set. Count entries in window. Accurate but memory-heavy.",
                    "sliding_window_counter": "Hybrid: weighted average of current and previous fixed windows. Good balance of accuracy and performance.",
                    "token_bucket": "Refill tokens at fixed rate. Each request consumes one. Allows bursts. Most common in industry.",
                    "leaky_bucket": "Process requests at fixed rate (FIFO queue). Smooths traffic. Good for downstream protection.",
                },
                "recommended": "Token bucket for most use cases. Sliding window counter if you need strict limits.",
                "distributed_consistency": "Use Redis Lua scripts for atomic check-and-increment. For very high scale, use local rate limiting with periodic Redis sync (approximate but fast).",
            },
            trade_offs=[
                {"option": "Token bucket vs Fixed window", "for_token": "Allows bursts, smoother traffic shape", "for_fixed": "Simpler to implement, easier to reason about", "recommendation": "Token bucket for API rate limiting"},
                {"option": "Centralized (Redis) vs Distributed (local)", "for_centralized": "Exact limits, consistent across servers", "for_local": "No network hop, ultra-low latency", "recommendation": "Centralized for strict limits, local + sync for ultra-high QPS"},
                {"option": "Fail-open vs Fail-closed", "for_open": "Service stays available if rate limiter is down", "for_closed": "Prevents abuse even during failures", "recommendation": "Fail-open for user-facing APIs, fail-closed for security-critical"},
            ],
            tips=[
                "Always discuss the boundary condition problem with fixed window (the '2x burst at window edge' issue).",
                "Lua scripts in Redis are your friend for atomic operations — mention this specifically.",
                "In practice, most companies use a hybrid: strict centralized limiting + loose local limiting as first line of defense.",
                "Don't forget to return proper HTTP headers (X-RateLimit-*) so clients can self-regulate.",
            ],
            thought_process=[
                "1. Clarify what's being rate-limited (per user? per IP? per endpoint?)",
                "2. Understand scale: QPS, number of distinct limit keys",
                "3. Choose algorithm: explain each briefly, pick one and justify",
                "4. Design the data flow: request → rate limiter → allow/deny",
                "5. Discuss distributed consistency (Redis atomic operations)",
                "6. Handle edge cases: clock skew, fail-open vs fail-closed",
                "7. Discuss monitoring: how to detect when users are near their limits",
            ],
            architecture_diagram={
                "nodes": [
                    {"id": "client", "label": "Client", "type": "client"},
                    {"id": "lb", "label": "Load Balancer", "type": "lb"},
                    {"id": "api1", "label": "API Server 1", "type": "server"},
                    {"id": "api2", "label": "API Server 2", "type": "server"},
                    {"id": "rl", "label": "Rate Limit Middleware", "type": "service"},
                    {"id": "redis", "label": "Redis (atomic INCR)", "type": "cache"},
                    {"id": "config", "label": "Config Store", "type": "database"},
                ],
                "edges": [
                    {"source": "client", "target": "lb", "animated": True},
                    {"source": "lb", "target": "api1", "animated": True},
                    {"source": "lb", "target": "api2", "animated": True},
                    {"source": "api1", "target": "rl", "label": "check"},
                    {"source": "api2", "target": "rl", "label": "check"},
                    {"source": "rl", "target": "redis", "label": "INCR"},
                    {"source": "rl", "target": "config", "label": "load rules"},
                ],
            },
            sequence_diagram=(
                "sequenceDiagram\n"
                "  participant C as Client\n"
                "  participant API as API Server\n"
                "  participant R as Redis\n"
                "  C->>API: GET /v1/users/42\n"
                "  API->>R: INCR rl:user:42:1m\n"
                "  R-->>API: 6\n"
                "  alt count <= limit\n"
                "    API-->>C: 200 OK\n"
                "  else over limit\n"
                "    API-->>C: 429 Too Many Requests\n"
                "  end"
            ),
            er_diagram=(
                "erDiagram\n"
                "  RULES ||--o{ COUNTERS : tracks\n"
                "  RULES {\n"
                "    bigint id PK\n"
                "    varchar key_template\n"
                "    int limit_per_window\n"
                "    int window_seconds\n"
                "    enum algorithm\n"
                "  }\n"
                "  COUNTERS {\n"
                "    varchar key PK\n"
                "    int count\n"
                "    timestamp window_start\n"
                "    timestamp ttl\n"
                "  }"
            ),
            thought_flow=(
                "graph TD\n"
                "  A[What identity? user/IP/key] --> B[Pick algorithm]\n"
                "  B --> C{Algorithm}\n"
                "  C -->|Token bucket| D[Burst friendly]\n"
                "  C -->|Leaky bucket| E[Smooths traffic]\n"
                "  C -->|Sliding window| F[Most accurate]\n"
                "  C -->|Fixed window| G[Simplest]\n"
                "  D --> H[Where to store?]\n"
                "  E --> H\n"
                "  F --> H\n"
                "  G --> H\n"
                "  H --> I[Local vs centralized]\n"
                "  I --> J[Distributed: Redis INCR]"
            ),
            tradeoff_visual={
                "title": "Token bucket vs Fixed window",
                "options": [
                    {
                        "label": "Token bucket",
                        "description": "Tokens drip in at a steady rate; each request consumes one. Allows bursts up to capacity.",
                        "pros": [
                            "Allows controlled bursts",
                            "Smooth average rate",
                            "Easy to reason about",
                        ],
                        "cons": [
                            "Two parameters to tune (rate + capacity)",
                            "Needs precise timestamp math under contention",
                        ],
                    },
                    {
                        "label": "Fixed window",
                        "description": "Count requests within each calendar minute (or N seconds). Reset at boundary.",
                        "pros": [
                            "Trivially simple — single counter",
                            "Cheapest to implement",
                        ],
                        "cons": [
                            "2× burst at window boundary",
                            "No burst control",
                        ],
                    },
                ],
                "recommendation": "Token bucket for user-facing APIs. Fixed window only for very rough quotas.",
            },
            senior_topics=[
                {
                    "id": "gcra-algorithm",
                    "title": "GCRA: The O(1)-memory token bucket",
                    "summary": "Generic Cell Rate Algorithm stores a single timestamp per key (the Theoretical Arrival Time) instead of a token count, giving identical burst semantics to token bucket at O(1) memory and O(1) compute. Stripe uses it in production; the redis-cell Redis module exposes it as a single CL.THROTTLE command.",
                    "sections": [
                        {
                            "heading": "What TAT is and why it's sufficient",
                            "body": "Token bucket needs two numbers: the current token count and the last-refill timestamp. GCRA replaces both with a single value: the Theoretical Arrival Time (TAT) — the moment the virtual queue would be empty if the limiter were fully saturated. On each request, you compute new_TAT = max(now, TAT) + emission_interval, where emission_interval = 1/rate. If new_TAT - now > burst_tolerance (the bucket depth), reject; otherwise accept and write new_TAT back. One atomic read-modify-write of a single integer — no floating-point token math, no refill loop.",
                        },
                        {
                            "heading": "Sliding window log vs token bucket vs GCRA",
                            "body": "Sliding window log stores every request timestamp in a sorted set; accurate but O(N) memory and O(log N) lookup per request — catastrophic at 1M RPM per key. Token bucket stores a float count + timestamp — two fields, but refill math requires a floating-point multiply. GCRA stores one integer (TAT in microseconds), does one integer compare, and rejects or advances. At Stripe's scale (millions of keys, 100K+ QPS), the memory savings per key compound into measurable RAM reduction in Redis.",
                        },
                        {
                            "heading": "redis-cell: CL.THROTTLE",
                            "body": "Brandur Leach's redis-cell module (written in Rust, loaded as a Redis module) exposes `CL.THROTTLE key max_burst count_per_period period [quantity]`. It returns six values: allowed/denied flag, total limit, remaining, reset epoch, and retry-after seconds — all the information a client needs to populate X-RateLimit-* headers. Because it executes inside the Redis event loop as a native command, it avoids the round-trip overhead of a Lua script and is fully atomic without MULTI/EXEC.",
                        },
                        {
                            "heading": "Pseudocode for manual implementation",
                            "body": "In any Redis Lua script: `local tat = tonumber(redis.call('GET', key) or now); local new_tat = math.max(tat, now) + emission_interval; if new_tat - now > burst_tolerance then return 0 end; redis.call('SET', key, new_tat, 'PX', ttl_ms); return 1`. The TTL is set to burst_tolerance + emission_interval so the key self-expires when the bucket is full and the client is idle. No background cleanup worker needed.",
                        },
                        {
                            "heading": "Production context and failure modes",
                            "body": "Stripe published their rate limiting architecture in 2017 and explicitly called out GCRA as their algorithm of choice after benchmarking sliding window and token bucket variants. The main failure mode is TAT drift under clock skew: if two Redis replicas have clocks skewed by >emission_interval, you can double-admit or double-reject. The fix is to always use Redis as the authoritative clock (`TIME` command) rather than application-server time.",
                        },
                    ],
                    "diagram": (
                        "graph LR\n"
                        "  subgraph TAT_timeline[\"TAT timeline\"]\n"
                        "    T0[\"now=0\"] --> T1[\"TAT=0: req1 allowed, TAT→10ms\"]\n"
                        "    T1 --> T2[\"now=5ms: req2, new_TAT=15ms, 15-5=10 ≤ burst OK\"]\n"
                        "    T2 --> T3[\"now=6ms: req3, new_TAT=25ms, 25-6=19 > burst=15 → REJECT\"]\n"
                        "    T3 --> T4[\"now=20ms: req4, max(25,20)=25, 25-20=5 ≤ burst OK\"]\n"
                        "  end"
                    ),
                    "sources": [
                        {"label": "Stripe Engineering — Scaling your API with rate limiters", "url": "https://stripe.com/blog/rate-limiters"},
                        {"label": "redis-cell — GCRA Redis module (Brandur Leach)", "url": "https://github.com/brandur/redis-cell"},
                        {"label": "Wikipedia — Generic cell rate algorithm", "url": "https://en.wikipedia.org/wiki/Generic_cell_rate_algorithm"},
                    ],
                },
                {
                    "id": "local-plus-central-hybrid",
                    "title": "Local + central: dodging the Redis hot-key",
                    "summary": "At 1M QPS, every request hitting a single Redis INCR collapses onto one CPU core of one shard — a classic hot-key. The production answer is a local-approximate + central-exact hybrid: nodes enforce locally for the common case and reconcile globally only at boundaries.",
                    "sections": [
                        {
                            "heading": "Why naive central Redis breaks at scale",
                            "body": "A single `INCR rl:POST:/search:user_42` routes via Redis Cluster hash slot to one shard. One Redis shard can sustain ~100K commands/sec on a single CPU core. At 1M QPS on one key, you've saturated 10× the capacity of one shard. Horizontal scaling doesn't help because hash-slot assignment pins a key to one node. The hot-key problem isn't hypothetical — teams at Twitter, Pinterest, and Discord have all published post-mortems where a single Redis key caused cascading failures.",
                        },
                        {
                            "heading": "Gubernator: owned-slice gossip architecture",
                            "body": "Mailgun open-sourced Gubernator, a distributed rate limiter where each node in the cluster 'owns' a slice of the key space via consistent hashing. A request arriving at any node for key K is forwarded to K's owner, which holds the authoritative counter. Owners gossip usage deltas to peers every ~100ms. The result: no hot-key (ownership is spread), no single-shard contention, and N-millisecond-eventual consistency rather than per-request round trips. Gubernator is deployed in Mailgun's production email pipeline handling tens of millions of requests per day.",
                        },
                        {
                            "heading": "Envoy RLS sidecar model",
                            "body": "Envoy's Rate Limit Service (RLS) filter architecture separates the local enforcement path from the global adjudication path. The Envoy sidecar enforces a local token bucket in-process (zero network hops, sub-microsecond). Periodically it calls the global RLS gRPC service to sync the actual count and adjust the local budget. Only borderline cases — requests near the limit — block on the global call. The vast majority of requests are handled entirely locally, and the global service only needs to sustain the borderline-case QPS, which is a fraction of total traffic.",
                        },
                        {
                            "heading": "Google Doorman concept",
                            "body": "Google's internal 'Doorman' system (described in the Doorman OSDI paper and referenced in the SRE book) frames the problem as capacity sharing: each client is allocated a lease on a fraction of the global resource budget. The central server hands out leases with TTLs; clients spend from their lease locally without contacting the server. Lease renewal batches the accounting and amortizes the RTT across many requests. If the server is unreachable, clients continue spending from their existing lease until TTL expiry — inherently fail-open with bounded over-admission.",
                        },
                        {
                            "heading": "Acceptable over-allowance in flight",
                            "body": "The hybrid model's tradeoff is bounded approximate over-allowance: at the moment of a local sync, up to N × local_window requests may be in flight globally above the limit, where N is the number of nodes and local_window is the sync interval. For most APIs this is acceptable — a 5% over-allowance at boundary is far better than a 1000ms latency spike from a hot-key. Publish the tolerance in your rate-limit policy: 'limits are enforced globally within 200ms; short-term bursts of up to 10% above limit are possible during high-concurrency events.'",
                        },
                    ],
                    "sources": [
                        {"label": "Gubernator — distributed rate limiting by Mailgun", "url": "https://github.com/mailgun/gubernator"},
                        {"label": "Envoy — Global rate limiting configuration", "url": "https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/rate_limit_filter"},
                        {"label": "Stripe Engineering — Scaling your API with rate limiters", "url": "https://stripe.com/blog/rate-limiters"},
                    ],
                },
                {
                    "id": "cost-based-limiting",
                    "title": "Not every request costs the same",
                    "summary": "A flat-rate limiter treats a 1-ms health-check GET identically to a 500-ms cross-table aggregation query. Attackers exploit this arbitrage; the fix is cost-unit weighted rate limiting where expensive operations consume proportionally more quota.",
                    "sections": [
                        {
                            "heading": "The list-users × 10,000 problem",
                            "body": "A mid-level rate limiter counts requests: 1000 requests/minute/user. A determined attacker calls `GET /users?limit=10000` 1000 times — each request triggers a full-table scan, saturating your DB at 1000× the intended load. The attacker stays under the request-count limit while causing 1000× the compute cost. This is not hypothetical: GraphQL APIs are especially vulnerable because a single query can traverse arbitrarily deep relationship graphs, each level multiplying DB calls.",
                        },
                        {
                            "heading": "GitHub GraphQL cost model",
                            "body": "GitHub's GraphQL API explicitly computes a point cost for each query before execution using a static analysis pass over the query AST. A query that fetches 100 repositories (each with 10 issues, each issue with 5 comments) costs 100 × 10 × 5 = 5000 points. The user's rate limit is expressed in points per hour (5000 for authenticated, 60 for unauthenticated), and the cost is charged before the query executes. GitHub returns `X-RateLimit-Cost` and `X-RateLimit-Used` headers so clients can track their budget. This prevents the 'query that returns 500KB of JSON in one call' from being counted the same as a single-field lookup.",
                        },
                        {
                            "heading": "Per-endpoint cost tables",
                            "body": "For REST APIs without a query language, assign cost weights per endpoint and method: `GET /health` = 0, `GET /users/{id}` = 1, `GET /users` = 5, `POST /reports/generate` = 50, `POST /bulk-import` = 100. Expose costs via an OpenAPI extension `x-rate-limit-cost: 50` on each operation. Clients can pre-calculate their expected spend before making calls. The cost table becomes part of the API contract and must be versioned with the API.",
                        },
                        {
                            "heading": "Charging and overage handling",
                            "body": "Deduct the cost before the request executes (optimistic) or after (conservative). Optimistic deduction prevents runaway queries but requires refunding on error — if a `POST /reports/generate` times out and you already charged 50 points, you must refund them or users lose quota for work that never completed. Conservative deduction is simpler but allows a fully-depleted client to submit one more expensive request. In practice, Stripe uses optimistic with partial-refund on timeout; most REST APIs use conservative.",
                        },
                        {
                            "heading": "Surfacing cost to clients",
                            "body": "Response headers: `X-RateLimit-Cost: 10`, `X-RateLimit-Limit: 1000`, `X-RateLimit-Remaining: 740`, `X-RateLimit-Reset: 1720000000`. The IETF draft `draft-ietf-httpapi-ratelimit-headers` is working toward standardizing a `RateLimit-Policy` header that can express cost semantics. Until the standard lands, document your cost model in your API reference and emit `X-RateLimit-Cost` consistently — clients that don't read it still benefit from seeing remaining quota drop faster than expected.",
                        },
                    ],
                    "sources": [
                        {"label": "GitHub GraphQL API — Resource Limitations", "url": "https://docs.github.com/en/graphql/overview/resource-limitations"},
                        {"label": "Stripe Engineering — Scaling your API with rate limiters", "url": "https://stripe.com/blog/rate-limiters"},
                        {"label": "IETF draft-ietf-httpapi-ratelimit-headers", "url": "https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/"},
                    ],
                },
                {
                    "id": "redis-hot-key-sharding",
                    "title": "When the counter itself becomes the bottleneck",
                    "summary": "A heavily-hit rate-limit key — `rl:POST:/search` at 500K QPS — pins to one Redis shard and one CPU core, causing cascading failures unrelated to the resource you're protecting. The fix is sharding the counter, not the cluster.",
                    "sections": [
                        {
                            "heading": "Hot-key anatomy",
                            "body": "Redis Cluster routes keys by CRC16(key) % 16384 hash slot. Every slot is owned by exactly one node. A single key like `rl:POST:/search` with 500K INCR/sec hits one node, one core, one event loop. Redis is single-threaded per slot by design — I/O threads can parallelize reads, but INCR is a write that serializes. At ~100K atomic writes/sec per core, you saturate the node and introduce queuing latency across all keys on that slot — not just the hot one. This was the root cause of a Redis-related outage at GitHub in 2015.",
                        },
                        {
                            "heading": "Counter sharding across N keys",
                            "body": "Instead of one key, maintain N shards: `rl:POST:/search:0`, `rl:POST:/search:1`, ... `rl:POST:/search:N-1`. Each request picks a shard by `rand() % N` (or `hash(server_id) % N` for per-server affinity). On each write, INCR one shard. To check the limit, sum all N shards. The summing query is N GETs; batch them as a pipeline or Lua script. With N=10, you've distributed the write load 10× and reduced per-shard QPS to 50K — within single-node budget. The tradeoff: reads now cost N GETs instead of 1.",
                        },
                        {
                            "heading": "Redis Cluster hash tags for per-user colocating",
                            "body": "Redis Cluster scatters keys across nodes by hash slot. If you shard `rl:{user_42}:endpoint_1`, `rl:{user_42}:endpoint_2` — using curly-brace hash tags — all keys for user_42 land on the same slot, enabling atomic multi-key Lua scripts for that user's combined quota. Endpoint-level keys (no hash tag) scatter across the cluster for hot-endpoint protection. This two-tier key design lets you enforce per-user aggregate limits atomically while scattering endpoint-level hot keys.",
                        },
                        {
                            "heading": "Lua script vs MULTI/EXEC vs WATCH/CAS",
                            "body": "WATCH/CAS (optimistic locking) retries the whole transaction on conflict — under high contention, retry rates compound and latency blows up. MULTI/EXEC batches commands but doesn't provide conditional execution — you can't check-then-increment atomically without a preceding WATCH. Lua scripts execute atomically in the Redis event loop: single round trip, no network interleave, conditionals and loops supported. A typical rate-limit Lua script (get TAT, compare, set) runs in 5–10µs. Redis 7 introduced Functions (`FUNCTION LOAD`, `FCALL`) as a first-class replacement for EVAL — named, versioned, persistent across restarts, no re-upload on reconnect.",
                        },
                        {
                            "heading": "Measuring and detecting hot keys",
                            "body": "Redis 4+ has `redis-cli --hotkeys` (requires `maxmemory-policy allkeys-lfu`). Redis 7.4+ adds `OBJECT FREQ key` for individual key frequency. In production, instrument your client to emit a metric when a single key's INCR latency exceeds 2ms — that's your early-warning signal before the shard saturates. CloudWatch / Datadog Redis integration surfaces `CacheHits` and `CacheMisses` per shard; a shard at 90%+ CPU with normal cluster-level utilization is the telltale sign of a hot key.",
                        },
                    ],
                    "sources": [
                        {"label": "Redis — Patterns: Rate limiting", "url": "https://redis.io/docs/latest/develop/use/patterns/rate-limiting/"},
                        {"label": "Redis — Cluster hash tags", "url": "https://redis.io/docs/latest/operate/oss_and_stack/reference/cluster-spec/#hash-tags"},
                        {"label": "Stripe Engineering — Scaling your API with rate limiters", "url": "https://stripe.com/blog/rate-limiters"},
                    ],
                },
                {
                    "id": "fail-open-vs-fail-closed",
                    "title": "Blast radius and graceful degradation",
                    "summary": "When the rate limiter itself is unavailable, you must choose between fail-open (forward all requests, accept DoS risk) and fail-closed (reject all requests, accept availability loss). The choice is endpoint-specific, not system-wide.",
                    "sections": [
                        {
                            "heading": "Fail-open: the availability-first choice",
                            "body": "If Redis is unreachable, forward the request as if it passed the rate check. This preserves availability — your primary service keeps working — at the cost of potentially allowing unbounded traffic during the outage window. For most user-facing APIs (search, read endpoints, dashboard fetches), the blast radius of an unprotected burst is bounded: DB connections saturate, cache miss rate spikes, but no persistent data corruption occurs. Stripe defaults to fail-open for their payment API rate limiter, reasoning that a brief over-admission is better than 100% rejection of legitimate payments.",
                        },
                        {
                            "heading": "Fail-closed: the security-first choice",
                            "body": "For authentication endpoints (login, password reset, OAuth token exchange), fail-closed is the correct default. If the limiter is down and you forward login attempts, a credential-stuffing attack can proceed without the 5-failed-login-per-minute guardrail. The blast radius of failing open on /auth/login is a full account takeover campaign, not a temporary latency spike. Return 503 or 429 with a Retry-After indicating when to retry; clients will wait, attackers will keep trying but without rate-limit bypass.",
                        },
                        {
                            "heading": "Circuit breaker on the limiter itself",
                            "body": "Wrap all calls to the rate-limit backend (Redis, Gubernator, etc.) in a circuit breaker. After N consecutive timeouts or errors within a rolling window, open the circuit and switch to a local approximate mode: an in-process token bucket with no global sync. The local bucket is initialized with the last-known quota state before the circuit opened. This bounds the degradation window: you're rate-limiting approximately for the duration of the outage, then exact limits resume when the circuit closes. Netflix's Hystrix and Resilience4j both implement this pattern; go-resty and gRPC interceptors have first-class circuit-breaker support.",
                        },
                        {
                            "heading": "Regional failover and state replication",
                            "body": "A rate-limit Redis cluster tied to one region fails the whole rate-limit tier when that region has a network partition. The fix: replicate limit state asynchronously to a secondary region. Use Redis Sentinel or Redis Cluster cross-region replication, accept up to 200ms of stale state in the secondary. On primary failure, promote the secondary — the worst outcome is a brief over-admission by whatever requests arrived in the 200ms replication lag window. Binding your rate limiter's availability to a single region is the #1 operational mistake in rate-limit deployments.",
                        },
                        {
                            "heading": "Noisy-neighbor blast radius",
                            "body": "A single abusive customer sending 100K RPS saturates your rate-limit backend not just for themselves but for all customers who share the same Redis shard. Partition rate-limit state by customer tier: enterprise customers' keys route to dedicated Redis nodes; free-tier keys share commodity nodes. When a free-tier customer causes a hot-key event, it degrades other free-tier customers but never bleeds into enterprise SLAs. This is the 'noisy neighbor' isolation pattern applied to the rate-limit layer itself, not just the application layer.",
                        },
                    ],
                    "sources": [
                        {"label": "Stripe Engineering — Scaling your API with rate limiters", "url": "https://stripe.com/blog/rate-limiters"},
                        {"label": "AWS Architecture Blog — Exponential Backoff and Jitter", "url": "https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/"},
                        {"label": "Cloudflare Blog — Cloudflare Rate Limiting", "url": "https://blog.cloudflare.com/introducing-rate-limiting/"},
                    ],
                },
                {
                    "id": "429-retry-after-contract",
                    "title": "The client-cooperation handshake",
                    "summary": "Returning 429 Too Many Requests is necessary but not sufficient. Without a well-formed Retry-After and the full X-RateLimit-* header suite, clients retry immediately, turning a graceful rate limit into a thundering-herd self-DDoS.",
                    "sections": [
                        {
                            "heading": "The full header contract",
                            "body": "A complete 429 response must include: `Retry-After: 30` (seconds until the client may retry — HTTP/1.1 also accepts an HTTP-date), `X-RateLimit-Limit: 1000` (the policy ceiling), `X-RateLimit-Remaining: 0` (current quota left), `X-RateLimit-Reset: 1720000060` (Unix epoch of next window reset), and optionally `X-RateLimit-Policy: 1000;w=60;burst=200` (machine-readable policy per the IETF draft). Without `Retry-After`, naive HTTP clients — including curl, Axios, and many AWS SDK retry loops — retry immediately on 429, generating another 429 in a tight loop that saturates your rate-limit backend.",
                        },
                        {
                            "heading": "IETF draft-ietf-httpapi-ratelimit-headers",
                            "body": "The IETF HTTP API working group has been standardizing these headers since 2020. The draft (currently at version 7+) defines `RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset`, and `RateLimit-Policy` as the canonical names (without X- prefix). In practice, every major API — GitHub, Stripe, Twilio, Shopify, Twitter/X — has shipped X-RateLimit-* variants before the standard landed and will maintain them indefinitely for backward compatibility. New APIs should emit both forms during the transition period.",
                        },
                        {
                            "heading": "Client backoff: decorrelated jitter beats exponential",
                            "body": "Pure exponential backoff (`sleep = min(cap, base * 2^attempt)`) causes synchronized retry storms: every client that hit the limit at t=0 wakes at t=1, t=2, t=4 simultaneously, causing correlated bursts. AWS's 2015 architecture blog post 'Exponential Backoff and Jitter' demonstrates that decorrelated jitter (`sleep = rand(base, min(cap, prev_sleep * 3))`) breaks synchronization effectively. The key insight: each retry's sleep is bounded by 3× the *previous* sleep (not the base), so retries spread out over time proportional to the backoff scale. Full jitter (random between 0 and the cap) is even more spread but can cause very short retries that don't respect Retry-After.",
                        },
                        {
                            "heading": "429 vs 503: clients treat them differently",
                            "body": "429 means 'you specifically are over-limit; try later per Retry-After.' 503 means 'the whole service is unavailable; try later per Retry-After or per circuit breaker.' Load balancers, CDNs, and API gateways automatically retry 503s with exponential backoff on your behalf — they do not automatically retry 429s, because 429 implies retrying will also fail. Monitoring systems classify 429 as 'client error' and 503 as 'server error'; returning 503 for rate-limit events inflates your error rate SLI and triggers false-positive oncall alerts.",
                        },
                        {
                            "heading": "Crawler behavior and SEO implications",
                            "body": "Googlebot and Bingbot specifically honor `Retry-After` on 429 and 503 responses — they will pause crawling of the affected URL and resume after the specified delay. If you return 429 without Retry-After, Googlebot backs off with its default crawl delay but may interpret the repeated 429s as 'content unavailable' and reduce crawl frequency for the entire domain. For high-SEO-value pages, return a short Retry-After (30–300 seconds) rather than no header at all. Google's Search Central documentation explicitly lists 429 as a supported status for crawl-rate signaling.",
                        },
                    ],
                    "sources": [
                        {"label": "AWS Architecture Blog — Exponential Backoff and Jitter", "url": "https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/"},
                        {"label": "IETF draft-ietf-httpapi-ratelimit-headers", "url": "https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/"},
                        {"label": "MDN Web Docs — 429 Too Many Requests", "url": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429"},
                    ],
                },
                {
                    "id": "rate-limit-vs-abuse-prevention",
                    "title": "Where rate limiting ends and abuse prevention begins",
                    "summary": "Rate limiting stops accidental overload and naive one-IP abuse. It does not stop a residential-proxy botnet (every request from a unique IP, every target a different account). Senior candidates draw the full defense-in-depth stack, with rate limiting as layer one of five.",
                    "sections": [
                        {
                            "heading": "What rate limiting cannot stop",
                            "body": "Credential stuffing via residential proxy networks (e.g., sold by IPRoyal, Brightdata): each request arrives from a unique residential IP with a valid HTTP fingerprint, fresh session cookie, and human-mimicking timing. Your 100-requests/IP/hour limiter sees each IP once and passes it. A 10,000-IP botnet can attempt 10,000 logins per hour — entirely inside per-IP limits — and achieve a 0.1% success rate on credential databases, yielding 10 account takeovers per hour. Rate limiting is not designed to stop this class of attack.",
                        },
                        {
                            "heading": "Layer 2: velocity rules",
                            "body": "Velocity rules operate on behavioral signals that span multiple requests: 5 failed logins per minute from any IP to the same account → temporary block (10 minutes). 20 distinct accounts attempted from the same IP in 5 minutes → IP block. 50 account lockouts per hour across the whole service → trigger CAPTCHA ramp for all login attempts. These rules are closer to fraud detection than rate limiting — they act on derived signals, not raw request counts. Tools like Datadog's Watchdog, Elastic SIEM, or custom Kafka Streams topologies can compute these in near-real-time.",
                        },
                        {
                            "heading": "Layer 3: challenge ramping",
                            "body": "Cloudflare Turnstile (invisible CAPTCHA replacement), hCaptcha, and Google reCAPTCHA Enterprise operate as challenge layers that can be activated progressively: no challenge for clean traffic, invisible Turnstile for borderline traffic (solved by client-side JS silently), interactive challenge for suspicious traffic, full block for known-bad traffic. Cloudflare Durable Objects enable a serverless edge rate limiter that integrates Turnstile challenges directly at the CDN edge — the request never reaches your origin for blocked traffic, and challenges are solved at the nearest POP with <50ms overhead.",
                        },
                        {
                            "heading": "Honeypot endpoints",
                            "body": "Add routes that no legitimate client ever calls: `/api/v1/internal/debug`, a hidden form field named `email_confirm` (a classic honeypot field that browsers autofill but users don't), or a robots.txt-disallowed path. Any request hitting these endpoints is automated by definition. Block the IP or fingerprint immediately, no challenge needed, no false-positive risk. Honeypots are zero-latency, zero-false-positive detectors — pair them with WAF rules that auto-block the originating ASN if more than N honeypot hits arrive from it per hour.",
                        },
                        {
                            "heading": "The defense-in-depth framing",
                            "body": "The senior answer is a stack, not a single control: (1) rate limiting — stops naive abuse and accidental overload; (2) velocity/behavioral rules — stops credential-stuffing campaigns; (3) challenge ramping (Turnstile/CAPTCHA) — forces human interaction cost on bots; (4) WAF with ML scoring (Cloudflare, Fastly Signal Sciences, AWS WAF) — stops known attack patterns and anomalous request structures; (5) device fingerprinting + behavioral biometrics (PerimeterX/HUMAN, DataDome) — stops sophisticated humanlike bots. Rate limiting as the only layer is insufficient; rate limiting as the first layer in a five-layer stack is the production architecture.",
                        },
                    ],
                    "diagram": (
                        "graph TD\n"
                        "  A[Incoming Request] --> B[Layer 1: Rate Limiter]\n"
                        "  B -->|over limit| Z1[429 Reject]\n"
                        "  B -->|under limit| C[Layer 2: Velocity Rules]\n"
                        "  C -->|suspicious pattern| Z2[Block + alert]\n"
                        "  C -->|ok| D[Layer 3: Challenge Ramp]\n"
                        "  D -->|high risk score| E[Turnstile / CAPTCHA]\n"
                        "  D -->|low risk| F[Layer 4: WAF + ML]\n"
                        "  E -->|solved| F\n"
                        "  E -->|failed| Z3[Block]\n"
                        "  F -->|known attack sig| Z4[Block]\n"
                        "  F -->|ok| G[Layer 5: Behavioral biometrics]\n"
                        "  G -->|bot-like| Z5[Block]\n"
                        "  G -->|human| H[Forward to Origin]"
                    ),
                    "sources": [
                        {"label": "Cloudflare Blog — Introducing Rate Limiting", "url": "https://blog.cloudflare.com/introducing-rate-limiting/"},
                        {"label": "Cloudflare Turnstile docs", "url": "https://developers.cloudflare.com/turnstile/"},
                        {"label": "OWASP ASVS — Credential Stuffing and Brute Force", "url": "https://owasp.org/www-project-application-security-verification-standard/"},
                    ],
                },
            ],
            tags=["rate-limiting", "api-gateway", "redis", "distributed-systems", "algorithms"],
        ),
    ]
    for q in questions:
        db.add(q)


def _seed_coding(db):
    questions = [
        CodingQuestion(
            title="Two Sum",
            difficulty="Easy",
            description="Given an array of integers `nums` and an integer `target`, return indices of the two numbers such that they add up to `target`.\n\nYou may assume that each input would have exactly one solution, and you may not use the same element twice.\n\nYou can return the answer in any order.",
            hints=[
                "A brute force approach would check every pair — O(n²) time. Can we do better?",
                "If you know the target and one number, you know what the other number must be.",
                "Use a hash map to store numbers you've seen and their indices. For each number, check if (target - number) is in the map.",
                "The key insight: transform the problem from 'find two numbers that sum to target' to 'for each number, check if its complement exists'.",
            ],
            constraints=[
                "2 <= nums.length <= 10⁴",
                "-10⁹ <= nums[i] <= 10⁹",
                "-10⁹ <= target <= 10⁹",
                "Only one valid answer exists",
                "You may not use the same element twice",
            ],
            starter_code={
                "python": "def two_sum(nums, target):\n    # Your code here\n    pass",
                "javascript": "function twoSum(nums, target) {\n    // Your code here\n}",
                "java": "public int[] twoSum(int[] nums, int target) {\n    // Your code here\n    return new int[]{};\n}",
            },
            boilerplate_code={
                "python": "# Test runner (read-only)\nif __name__ == \"__main__\":\n    test_cases = [\n        ([2, 7, 11, 15], 9),\n        ([3, 2, 4], 6),\n        ([3, 3], 6),\n    ]\n    for nums, target in test_cases:\n        result = two_sum(nums, target)\n        print(f\"two_sum({nums}, {target}) = {result}\")",
                "javascript": "// Test runner (read-only)\nconst testCases = [\n    [[2, 7, 11, 15], 9],\n    [[3, 2, 4], 6],\n    [[3, 3], 6],\n];\ntestCases.forEach(([nums, target]) => {\n    console.log(`twoSum(${JSON.stringify(nums)}, ${target}) =`, twoSum(nums, target));\n});",
                "java": "// Test runner (read-only)\npublic class Main {\n    public static void main(String[] args) {\n        Solution s = new Solution();\n        int[][][] tests = {{{2,7,11,15}, {9}}, {{3,2,4}, {6}}, {{3,3}, {6}}};\n        // results printed\n    }\n}",
            },
            test_cases=[
                {"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1], "description": "Pair at the start", "tags": ["basic"]},
                {"input": {"nums": [3, 2, 4], "target": 6}, "expected": [1, 2], "description": "Pair not at the start", "tags": ["basic"]},
                {"input": {"nums": [3, 3], "target": 6}, "expected": [0, 1], "description": "Duplicate values used as the pair", "tags": ["basic", "tricky"]},
                {"input": {"nums": [1, 5, 6, 9, 14], "target": 15}, "expected": [0, 4], "description": "Pair spans first and last", "tags": ["tricky"]},
                {"input": {"nums": [-3, 4, 3, 90], "target": 0}, "expected": [0, 2], "description": "Includes negative numbers", "tags": ["edge"]},
                {"input": {"nums": [0, 4, 3, 0], "target": 0}, "expected": [0, 3], "description": "Zero target with two zeros", "tags": ["edge"]},
                {"input": {"nums": [-1, -2, -3, -4], "target": -7}, "expected": [2, 3], "description": "Negative target", "tags": ["tricky"]},
                {"input": {"nums": [5, 5], "target": 10}, "expected": [0, 1], "description": "Minimum-size array", "tags": ["edge"]},
                {"input": {"nums": list(range(1, 101)), "target": 199}, "expected": [98, 99], "description": "Sorted ascending — answer at the end (100 elements)", "tags": ["large"]},
                {"input": {"nums": [1] * 4999 + [2, 3], "target": 5}, "expected": [4999, 5000], "description": "Mostly duplicates — answer after many dupes (5001 elements)", "tags": ["large", "tricky"]},
                {"input": {"nums": list(range(0, 10000)), "target": 19997}, "expected": [9998, 9999], "description": "10K ascending — answer at the very end", "tags": ["large"]},
                {"input": {"nums": [10**9, -10**9, 0], "target": 0}, "expected": [0, 1], "description": "Values at the constraint boundary", "tags": ["edge"]},
            ],
            solutions=[
                {
                    "title": "Hash Map (Optimal)",
                    "time_complexity": "O(n)",
                    "space_complexity": "O(n)",
                    "description": "Iterate through the array once. For each element, check if its complement (target - num) exists in a hash map. If not, add the current number and its index to the map.",
                    "code": {
                        "python": "def two_sum(nums, target):\n    seen = {}\n    for i, num in enumerate(nums):\n        complement = target - num\n        if complement in seen:\n            return [seen[complement], i]\n        seen[num] = i",
                        "javascript": "function twoSum(nums, target) {\n    const seen = new Map();\n    for (let i = 0; i < nums.length; i++) {\n        const complement = target - nums[i];\n        if (seen.has(complement)) {\n            return [seen.get(complement), i];\n        }\n        seen.set(nums[i], i);\n    }\n}",
                        "java": "public int[] twoSum(int[] nums, int target) {\n    Map<Integer, Integer> seen = new HashMap<>();\n    for (int i = 0; i < nums.length; i++) {\n        int complement = target - nums[i];\n        if (seen.containsKey(complement)) {\n            return new int[]{seen.get(complement), i};\n        }\n        seen.put(nums[i], i);\n    }\n    return new int[]{};\n}",
                    },
                },
                {
                    "title": "Brute Force",
                    "time_complexity": "O(n²)",
                    "space_complexity": "O(1)",
                    "description": "Check every pair of numbers. Simple but slow for large arrays.",
                    "code": {
                        "python": "def two_sum(nums, target):\n    for i in range(len(nums)):\n        for j in range(i + 1, len(nums)):\n            if nums[i] + nums[j] == target:\n                return [i, j]",
                    },
                },
            ],
            thought_process=[
                "1. Start with brute force: check every pair — O(n²). Mention this first to show you think about simple solutions.",
                "2. Ask: what are we looking up? For each number, we need to find its complement. Lookups → hash map.",
                "3. Build the hash map as we go (one pass): for each number, check if complement exists, if not store current number.",
                "4. Why one-pass works: we only need each pair once. When we reach the second element of the pair, the first is already in the map.",
                "5. Edge cases: duplicate values (like [3,3]), negative numbers, zeros.",
            ],
            tips=[
                "Always start with brute force, then optimize. Interviewers want to see your thought process.",
                "Hash map lookup is O(1) average case — mention this explicitly.",
                "Ask about follow-up: 'What if the array is sorted?' → Two pointers, O(n) time, O(1) space.",
                "Another follow-up: 'What if there are multiple valid pairs?' → Return all of them.",
            ],
            companies=["Google", "Amazon", "Apple", "Microsoft", "Meta"],
            topics=["Array", "Hash Table"],
            time_complexity="O(n)",
            space_complexity="O(n)",
        ),
        CodingQuestion(
            title="LRU Cache",
            difficulty="Medium",
            description="Design a data structure that follows the constraints of a Least Recently Used (LRU) cache.\n\nImplement the `LRUCache` class:\n- `LRUCache(capacity)` Initialize the LRU cache with positive size capacity.\n- `get(key)` Return the value of the key if it exists, otherwise return -1.\n- `put(key, value)` Update the value of the key if it exists. Otherwise, add the key-value pair. If the number of keys exceeds the capacity, evict the least recently used key.\n\nThe functions `get` and `put` must each run in O(1) average time complexity.",
            hints=[
                "You need O(1) lookups → hash map. But a hash map alone doesn't track usage order.",
                "To track recency in O(1), you need a doubly linked list — move accessed items to head, evict from tail.",
                "Combine them: hash map maps keys to linked list nodes. This gives O(1) lookup AND O(1) reorder.",
                "Use dummy head and tail nodes to simplify edge cases (insertions/deletions at boundaries).",
            ],
            constraints=[
                "1 <= capacity <= 3000",
                "0 <= key <= 10⁴",
                "0 <= value <= 10⁵",
                "At most 2 * 10⁵ calls to get and put",
            ],
            starter_code={
                "python": "class LRUCache:\n    def __init__(self, capacity):\n        pass\n\n    def get(self, key):\n        pass\n\n    def put(self, key, value):\n        pass",
                "javascript": "class LRUCache {\n    constructor(capacity) {}\n    get(key) {}\n    put(key, value) {}\n}",
                "java": "class LRUCache {\n    public LRUCache(int capacity) {}\n    public int get(int key) {}\n    public void put(int key, int value) {}\n}",
            },
            boilerplate_code={
                "python": "# Test runner (read-only)\ncache = LRUCache(2)\nprint(cache.put(1, 1))  # None\nprint(cache.put(2, 2))  # None\nprint(cache.get(1))     # 1\nprint(cache.put(3, 3))  # evicts key 2\nprint(cache.get(2))     # -1\nprint(cache.put(4, 4))  # evicts key 1\nprint(cache.get(1))     # -1\nprint(cache.get(3))     # 3\nprint(cache.get(4))     # 4",
                "javascript": "// Test runner (read-only)\nconst cache = new LRUCache(2);\nconsole.log(cache.put(1, 1));\nconsole.log(cache.put(2, 2));\nconsole.log(cache.get(1));  // 1\nconsole.log(cache.put(3, 3));  // evicts 2\nconsole.log(cache.get(2));  // -1",
                "java": "// Test runner (read-only)",
            },
            test_cases=[
                {
                    "input": {
                        "ops": ["LRUCache", "put", "put", "get", "put", "get", "put", "get", "get", "get"],
                        "args": [[2], [1, 1], [2, 2], [1], [3, 3], [2], [4, 4], [1], [3], [4]],
                    },
                    "expected": [None, None, None, 1, None, -1, None, -1, 3, 4],
                    "description": "Standard sequence from the problem",
                    "tags": ["basic"],
                },
                {
                    "input": {
                        "ops": ["LRUCache", "put", "get"],
                        "args": [[2], [1, 10], [1]],
                    },
                    "expected": [None, None, 10],
                    "description": "Put then get",
                    "tags": ["basic"],
                },
                {
                    "input": {
                        "ops": ["LRUCache", "put", "put", "get"],
                        "args": [[2], [1, 1], [1, 2], [1]],
                    },
                    "expected": [None, None, None, 2],
                    "description": "Put with existing key overwrites the value",
                    "tags": ["basic", "eviction-order"],
                },
                {
                    "input": {
                        "ops": ["LRUCache", "put", "put", "put", "get", "get"],
                        "args": [[2], [1, 1], [2, 2], [3, 3], [1], [2]],
                    },
                    "expected": [None, None, None, None, -1, -1],
                    "description": "Evict LRU entry when exceeding capacity — first two keys gone",
                    "tags": ["basic", "eviction-order"],
                },
                {
                    "input": {
                        "ops": ["LRUCache", "put", "put", "get", "put", "get", "get"],
                        "args": [[1], [1, 1], [2, 2], [1], [3, 3], [2], [3]],
                    },
                    "expected": [None, None, None, -1, None, -1, 3],
                    "description": "Capacity 1 — every new put evicts the previous",
                    "tags": ["edge", "capacity-1"],
                },
                {
                    "input": {
                        "ops": ["LRUCache", "get", "get", "get"],
                        "args": [[3], [1], [2], [3]],
                    },
                    "expected": [None, -1, -1, -1],
                    "description": "Get on missing keys returns -1",
                    "tags": ["edge"],
                },
                {
                    "input": {
                        "ops": ["LRUCache", "put", "put", "get", "put", "get", "get"],
                        "args": [[2], [1, 1], [2, 2], [1], [3, 3], [2], [1]],
                    },
                    "expected": [None, None, None, 1, None, -1, 1],
                    "description": "get() moves key to most-recently-used; new put evicts the OTHER key",
                    "tags": ["tricky", "eviction-order"],
                },
                {
                    "input": {
                        "ops": ["LRUCache", "put", "put", "put", "get", "get"],
                        "args": [[2], [1, 1], [2, 2], [1, 100], [1], [2]],
                    },
                    "expected": [None, None, None, None, 100, 2],
                    "description": "put() on existing key updates value but must not evict anything",
                    "tags": ["tricky", "eviction-order"],
                },
                {
                    "input": {
                        "ops": ["LRUCache", "put", "put", "get", "get", "put", "get", "get"],
                        "args": [[2], [1, 1], [2, 2], [2], [1], [3, 3], [2], [1]],
                    },
                    "expected": [None, None, None, 2, 1, None, -1, 1],
                    "description": "Alternating gets reorder LRU before eviction",
                    "tags": ["tricky", "eviction-order"],
                },
                {
                    "input": {
                        "ops": ["LRUCache"] + ["put"] * 10,
                        "args": [[3]] + [[i, i * 10] for i in range(1, 11)],
                    },
                    "expected": [None] + [None] * 10,
                    "description": "10 sequential puts at capacity 3 — only last 3 survive",
                    "tags": ["eviction-order"],
                },
                {
                    "input": {
                        "ops": ["LRUCache"] + [op for i in range(1, 101) for op in ("put", "get")],
                        "args": [[100]] + [arg for i in range(1, 101) for arg in ([i, i], [i])],
                    },
                    "expected": [None] + [val for i in range(1, 101) for val in (None, i)],
                    "description": "200 alternating put/get inside capacity — all hits",
                    "tags": ["large"],
                },
                {
                    "input": {
                        "ops": ["LRUCache"] + ["put"] * 1000 + ["get"] * 100,
                        "args": [[100]]
                                 + [[i, i] for i in range(1000)]
                                 + [[i] for i in range(100)],
                    },
                    "expected": [None] + [None] * 1000 + [-1] * 100,
                    "description": "1000 unique puts at capacity 100 — first 900 evicted; early keys all miss",
                    "tags": ["large"],
                },
            ],
            solutions=[
                {
                    "title": "Hash Map + Doubly Linked List (Optimal)",
                    "time_complexity": "O(1) for both get and put",
                    "space_complexity": "O(capacity)",
                    "description": "Use a hash map for O(1) key lookup and a doubly linked list for O(1) reordering. Dummy head/tail nodes eliminate edge cases.",
                    "code": {
                        "python": "class Node:\n    def __init__(self, key=0, val=0):\n        self.key = key\n        self.val = val\n        self.prev = None\n        self.next = None\n\nclass LRUCache:\n    def __init__(self, capacity):\n        self.cap = capacity\n        self.cache = {}\n        self.head = Node()\n        self.tail = Node()\n        self.head.next = self.tail\n        self.tail.prev = self.head\n\n    def _remove(self, node):\n        node.prev.next = node.next\n        node.next.prev = node.prev\n\n    def _add_to_front(self, node):\n        node.next = self.head.next\n        node.prev = self.head\n        self.head.next.prev = node\n        self.head.next = node\n\n    def get(self, key):\n        if key in self.cache:\n            node = self.cache[key]\n            self._remove(node)\n            self._add_to_front(node)\n            return node.val\n        return -1\n\n    def put(self, key, value):\n        if key in self.cache:\n            self._remove(self.cache[key])\n        node = Node(key, value)\n        self._add_to_front(node)\n        self.cache[key] = node\n        if len(self.cache) > self.cap:\n            lru = self.tail.prev\n            self._remove(lru)\n            del self.cache[lru.key]",
                    },
                },
                {
                    "title": "OrderedDict (Python shortcut)",
                    "time_complexity": "O(1)",
                    "space_complexity": "O(capacity)",
                    "description": "Python's collections.OrderedDict maintains insertion order with move_to_end() and popitem(last=False). Not acceptable in interviews as the sole solution, but good to mention.",
                    "code": {
                        "python": "from collections import OrderedDict\n\nclass LRUCache:\n    def __init__(self, capacity):\n        self.cap = capacity\n        self.cache = OrderedDict()\n\n    def get(self, key):\n        if key not in self.cache:\n            return -1\n        self.cache.move_to_end(key)\n        return self.cache[key]\n\n    def put(self, key, value):\n        if key in self.cache:\n            self.cache.move_to_end(key)\n        self.cache[key] = value\n        if len(self.cache) > self.cap:\n            self.cache.popitem(last=False)",
                    },
                },
            ],
            thought_process=[
                "1. Understand the requirements: O(1) get and put. This constraints your data structure choices heavily.",
                "2. O(1) lookup → hash map. But hash maps don't have order.",
                "3. O(1) ordered access → doubly linked list. But linked lists have O(n) lookup.",
                "4. Combine them: hash map points to linked list nodes directly, so no traversal needed.",
                "5. Design the node: key, value, prev, next. Key is needed for eviction (to remove from hash map).",
                "6. Use dummy head/tail to avoid null checks on edge operations.",
                "7. get(): look up in map → remove node from list → add to front → return value.",
                "8. put(): if exists, remove old. Add new node to front + map. If over capacity, evict tail.",
            ],
            tips=[
                "This is one of the most common interview questions. Practice it until you can write it from memory.",
                "The dummy head/tail trick eliminates ALL edge cases — always use it.",
                "In Python interviews, mention OrderedDict but implement the manual version.",
                "Follow-up: 'How would you make this thread-safe?' → Add a lock, or use concurrent data structures.",
            ],
            companies=["Google", "Amazon", "Microsoft", "Bloomberg", "Apple"],
            topics=["Hash Table", "Linked List", "Design"],
            time_complexity="O(1)",
            space_complexity="O(capacity)",
        ),
        CodingQuestion(
            title="Merge Intervals",
            difficulty="Medium",
            description="Given an array of `intervals` where `intervals[i] = [start_i, end_i]`, merge all overlapping intervals, and return an array of the non-overlapping intervals that cover all the intervals in the input.",
            hints=[
                "First sort the intervals by start time. This guarantees you only need to look at the last merged interval.",
                "If the current interval's start <= last merged interval's end, they overlap — merge by extending the end.",
                "If no overlap, add the current interval to the result as a new entry.",
                "The key insight: after sorting, overlapping intervals form contiguous groups.",
            ],
            constraints=[
                "1 <= intervals.length <= 10⁴",
                "intervals[i].length == 2",
                "0 <= start_i <= end_i <= 10⁴",
            ],
            starter_code={
                "python": "def merge_intervals(intervals):\n    # Your code here\n    pass",
                "javascript": "function mergeIntervals(intervals) {\n    // Your code here\n}",
                "java": "public int[][] merge(int[][] intervals) {\n    // Your code here\n    return new int[][]{};\n}",
            },
            boilerplate_code={
                "python": "# Test runner (read-only)\ntests = [\n    [[1,3],[2,6],[8,10],[15,18]],\n    [[1,4],[4,5]],\n    [[1,4],[0,4]],\n]\nfor intervals in tests:\n    print(f\"merge_intervals({intervals}) = {merge_intervals(intervals)}\")",
                "javascript": "// Test runner (read-only)\nconst tests = [[[1,3],[2,6],[8,10],[15,18]], [[1,4],[4,5]]];\ntests.forEach(intervals => {\n    console.log(`merge(${JSON.stringify(intervals)}) =`, mergeIntervals(intervals));\n});",
                "java": "// Test runner (read-only)",
            },
            test_cases=[
                {"input": {"intervals": [[1, 3], [2, 6], [8, 10], [15, 18]]}, "expected": [[1, 6], [8, 10], [15, 18]], "description": "Sample from the problem", "tags": ["basic"]},
                {"input": {"intervals": [[1, 4], [4, 5]]}, "expected": [[1, 5]], "description": "Two intervals touching at the boundary", "tags": ["basic", "adjacency"]},
                {"input": {"intervals": [[1, 2], [3, 4], [5, 6]]}, "expected": [[1, 2], [3, 4], [5, 6]], "description": "No overlaps at all", "tags": ["edge"]},
                {"input": {"intervals": [[1, 5]]}, "expected": [[1, 5]], "description": "Single interval", "tags": ["edge"]},
                {"input": {"intervals": []}, "expected": [], "description": "Empty input", "tags": ["edge"]},
                {"input": {"intervals": [[1, 4], [1, 4], [1, 4]]}, "expected": [[1, 4]], "description": "Three identical intervals", "tags": ["edge"]},
                {"input": {"intervals": [[1, 10], [2, 3], [4, 5]]}, "expected": [[1, 10]], "description": "One big interval contains the others", "tags": ["tricky", "full-overlap"]},
                {"input": {"intervals": [[1, 2], [2, 3]]}, "expected": [[1, 3]], "description": "Touching at the boundary (closed intervals merge)", "tags": ["tricky", "adjacency"]},
                {"input": {"intervals": [[10, 12], [5, 8], [1, 3]]}, "expected": [[1, 3], [5, 8], [10, 12]], "description": "Input is reverse-sorted — solution must sort first", "tags": ["tricky", "reverse-sorted"]},
                {"input": {"intervals": [[1, 3], [3, 5], [5, 7], [7, 9], [9, 11]]}, "expected": [[1, 11]], "description": "Chain of 5 adjacent intervals collapses to one", "tags": ["tricky", "adjacency"]},
                {"input": {"intervals": [[1, 100], [5, 10], [20, 30], [50, 60]]}, "expected": [[1, 100]], "description": "One outer interval swallows many inner", "tags": ["full-overlap"]},
                {"input": {"intervals": [[-5, -1], [-3, 0], [1, 2]]}, "expected": [[-5, 0], [1, 2]], "description": "Negative values", "tags": ["edge"]},
                {"input": {"intervals": [[1, 1], [2, 2], [1, 2]]}, "expected": [[1, 2]], "description": "Zero-width intervals merge via the spanning one", "tags": ["tricky"]},
                {"input": {"intervals": [[i * 3, i * 3 + 1] for i in range(1000)]}, "expected": [[i * 3, i * 3 + 1] for i in range(1000)], "description": "1000 disjoint intervals — none merge", "tags": ["large"]},
                {"input": {"intervals": [[i, i + 10] for i in range(0, 1000, 2)]}, "expected": [[0, 1008]], "description": "1000 heavily-overlapping intervals — all merge into one", "tags": ["large", "full-overlap"]},
            ],
            solutions=[
                {
                    "title": "Sort + Linear Scan (Optimal)",
                    "time_complexity": "O(n log n)",
                    "space_complexity": "O(n)",
                    "description": "Sort intervals by start time, then linearly scan merging overlapping intervals into the result.",
                    "code": {
                        "python": "def merge_intervals(intervals):\n    if not intervals:\n        return []\n    intervals.sort(key=lambda x: x[0])\n    merged = [intervals[0]]\n    for curr in intervals[1:]:\n        last = merged[-1]\n        if curr[0] <= last[1]:\n            last[1] = max(last[1], curr[1])\n        else:\n            merged.append(curr)\n    return merged",
                        "javascript": "function mergeIntervals(intervals) {\n    if (!intervals.length) return [];\n    intervals.sort((a, b) => a[0] - b[0]);\n    const merged = [intervals[0]];\n    for (const curr of intervals.slice(1)) {\n        const last = merged[merged.length - 1];\n        if (curr[0] <= last[1]) {\n            last[1] = Math.max(last[1], curr[1]);\n        } else {\n            merged.push(curr);\n        }\n    }\n    return merged;\n}",
                    },
                },
            ],
            thought_process=[
                "1. Understand what 'overlapping' means: two intervals [a,b] and [c,d] overlap if c <= b.",
                "2. If unsorted, checking all pairs is O(n²). But sorting makes overlapping intervals adjacent.",
                "3. Sort by start time O(n log n).",
                "4. Scan once: compare each interval with the last merged. Merge or append.",
                "5. The max(last[1], curr[1]) handles partial overlaps where one interval extends beyond the other.",
            ],
            tips=[
                "Sort first — always. Unsorted merge intervals is a much harder problem.",
                "Use max() when extending the end — the overlapping interval might end later.",
                "Follow-up: 'Insert a new interval into already merged intervals' → Binary search for position, then merge.",
                "Follow-up: 'Meeting rooms' — same pattern, count maximum concurrent intervals.",
            ],
            companies=["Google", "Amazon", "Meta", "Microsoft", "LinkedIn"],
            topics=["Array", "Sorting"],
            time_complexity="O(n log n)",
            space_complexity="O(n)",
        ),
    ]
    for q in questions:
        db.add(q)


def _seed_behavioral_categories(db):
    categories = [
        BehavioralCategory(name="Customer Obsession", description="Leaders start with the customer and work backwards. They work vigorously to earn and keep customer trust.", color="#0070f3", icon="🎯"),
        BehavioralCategory(name="Ownership", description="Leaders are owners. They think long term and don't sacrifice long-term value for short-term results.", color="#ff5b4f", icon="🔑"),
        BehavioralCategory(name="Bias for Action", description="Speed matters. Many decisions are reversible and don't need extensive study. Leaders value calculated risk-taking.", color="#0a72ef", icon="⚡"),
        BehavioralCategory(name="Deliver Results", description="Leaders focus on the key inputs and deliver them with the right quality in a timely fashion.", color="#7928ca", icon="🏆"),
        BehavioralCategory(name="Learn and Be Curious", description="Leaders are never done learning and always seek to improve themselves.", color="#50e3c2", icon="📚"),
        BehavioralCategory(name="Disagree and Commit", description="Leaders respectfully challenge decisions when they disagree, but once committed, they wholly support the decision.", color="#de1d8d", icon="🤝"),
        BehavioralCategory(name="Insist on Highest Standards", description="Leaders have relentlessly high standards. They raise the bar continuously and drive their teams to deliver high-quality products.", color="#f5a623", icon="⭐"),
        BehavioralCategory(name="Think Big", description="Thinking small is a self-fulfilling prophecy. Leaders create bold directions that deliver results.", color="#0072f5", icon="🌍"),
    ]
    for c in categories:
        db.add(c)


def _seed_behavioral(db):
    categories = {c.name: c.id for c in db.query(BehavioralCategory).all()}
    questions = [
        BehavioralQuestion(
            title="Conflict with a Teammate",
            question_text="Tell me about a time you had a conflict with a teammate. How did you resolve it?",
            category_ids=[categories.get("Disagree and Commit", 0), categories.get("Ownership", 0)],
            star_guide={
                "situation": "Set the scene: who was the teammate, what was the project, what was the context of the disagreement?",
                "task": "What was your responsibility? What needed to be resolved?",
                "action": "Focus on YOUR actions: how did you initiate the conversation? What did you do to understand their perspective? How did you find common ground?",
                "result": "What was the outcome? How did the relationship improve? What did you learn about handling conflicts?",
                "framework_tips": [
                    "Avoid blaming — frame the conflict as a difference in approach, not a personal issue",
                    "Show that you listened first before advocating your position",
                    "Demonstrate data-driven decision making when possible",
                    "End with what you learned and how it changed your approach going forward",
                ],
            },
            sample_response={
                "situation": "On a payment processing migration project, my teammate Sarah advocated for a big-bang cutover while I preferred a gradual canary deployment. Both approaches had merit — hers was faster, mine was safer.",
                "task": "We needed to decide on a migration strategy that balanced speed with safety for a critical revenue system.",
                "action": "I organized a meeting where both of us presented our approaches with data. Sarah showed that the big-bang approach would save 3 weeks. I presented a risk analysis showing the canary approach would let us catch issues affecting 1% of traffic before full rollout. Instead of debating, I proposed a hybrid: canary for the first 5%, then accelerated rollout with automated rollback. I specifically said 'I think the canary approach is safer, but if you have data showing the risk is manageable, I'm happy to go with your approach.' Sarah agreed to the hybrid since it incorporated both our concerns.",
                "result": "The hybrid approach worked perfectly. We caught a currency rounding bug at 2% rollout that would have affected all customers. We still completed the migration in 2 weeks (vs 3 for pure canary). Sarah and I developed a strong working relationship and later co-authored our team's deployment playbook. I learned that the best solutions often combine elements from both sides of a disagreement.",
                "key_strengths_shown": ["Active listening", "Data-driven approach", "Compromise", "Building relationships"],
            },
            tips=[
                "Never say you've never had a conflict — everyone has. Pick a real, mild-to-moderate conflict.",
                "Show empathy: acknowledge the other person had valid reasons for their position.",
                "Demonstrate 'disagree and commit' — even if your approach wasn't chosen, you executed it fully.",
                "Avoid stories where you 'won' the argument — focus on resolution, not victory.",
                "Have 2-3 conflict stories ready: one with a peer, one with a manager, one with a stakeholder.",
            ],
            common_pitfalls=[
                "Blaming the other person or painting them as unreasonable",
                "Choosing a conflict where the stakes were too low (arguing about code style) or too high (ethical violations)",
                "Not showing YOUR specific actions — saying 'we resolved it' without detailing what you did",
                "Ending the story at the resolution without reflecting on what you learned",
            ],
            follow_up_questions=[
                "What would you have done if you couldn't reach an agreement?",
                "How did this experience change how you handle disagreements?",
                "Have you used this approach again since then?",
            ],
            what_interviewers_look_for=[
                "Emotional intelligence and self-awareness",
                "Ability to separate the person from the problem",
                "Data-driven conflict resolution",
                "Growth mindset — learning from the experience",
                "Collaboration skills — seeking win-win outcomes",
            ],
            tags=["conflict-resolution", "collaboration", "communication", "disagree-and-commit"],
        ),
        BehavioralQuestion(
            title="Decision Without Full Information",
            question_text="Describe a situation where you had to make a decision without having all the information you needed. What was the outcome?",
            category_ids=[categories.get("Bias for Action", 0), categories.get("Deliver Results", 0)],
            star_guide={
                "situation": "What was the decision? Why was it time-sensitive? What information was missing and why?",
                "task": "What were the stakes? What were the possible consequences of waiting vs acting?",
                "action": "How did you assess the available information? What mental model or framework did you use? How did you mitigate risk?",
                "result": "What happened? If the decision was correct, what enabled that? If not, how did you recover?",
                "framework_tips": [
                    "Show that you didn't act recklessly — you gathered what you could within the time constraint",
                    "Demonstrate awareness of what you didn't know and how you planned for it",
                    "Discuss reversibility — was this a one-way door or two-way door decision?",
                    "Show the follow-through: monitoring the outcome and being ready to adjust",
                ],
            },
            sample_response={
                "situation": "During a major product launch, our primary database started showing elevated latency 2 hours before the scheduled release. The on-call DBA was unreachable, and we had partial monitoring data suggesting it might be a query plan regression from a recent schema change.",
                "task": "I had to decide within 30 minutes whether to proceed with the launch, delay it, or roll back the schema change — without being able to definitively identify the root cause.",
                "action": "I quickly gathered what data I could: the latency spike correlated with the schema change deployment, but CPU and memory metrics were normal. I applied the 'reversibility' framework: rolling back the schema change was easily reversible (we had the migration scripts), but launching with degraded DB performance would be hard to undo once users were on it. I decided to roll back the schema change while simultaneously setting up a parallel staging test. I communicated the decision and reasoning to the team lead within 15 minutes.",
                "result": "The rollback resolved the latency immediately. The staging test confirmed the schema change was the cause — a missing index on a newly added column. We added the index, redeployed the change, and launched 90 minutes late with zero user impact. The post-incident review led to a new pre-launch checklist item for schema change validation. I learned that in ambiguous situations, optimize for reversibility and communicate your reasoning transparently.",
                "key_strengths_shown": ["Decision-making under pressure", "Risk assessment", "Communication", "Incident management"],
            },
            tips=[
                "Pick a decision with real stakes — not 'which restaurant to pick for lunch'.",
                "Show your decision-making framework, not just the outcome.",
                "It's okay if the decision turned out to be wrong — focus on how you handled it.",
                "Demonstrate that you communicated the decision and its rationale to stakeholders.",
                "Amazon's 'one-way vs two-way door' framework is excellent to reference here.",
            ],
            common_pitfalls=[
                "Choosing a trivial decision that doesn't show real judgment",
                "Not explaining WHY you couldn't get more information",
                "Acting without any analysis — the interviewer wants to see a structured approach",
                "Only sharing stories where everything worked out — show resilience with mixed outcomes too",
            ],
            follow_up_questions=[
                "How would you handle that situation differently today?",
                "What was the most important piece of information you wished you had?",
                "How did stakeholders react to your decision?",
            ],
            what_interviewers_look_for=[
                "Structured thinking under ambiguity",
                "Risk awareness and mitigation",
                "Bias for action — not paralyzed by imperfect information",
                "Communication skills — keeping stakeholders informed",
                "Self-reflection and learning from outcomes",
            ],
            tags=["decision-making", "ambiguity", "bias-for-action", "leadership"],
        ),
        BehavioralQuestion(
            title="Failure and Learning",
            question_text="Tell me about a time you failed. What did you learn from it?",
            category_ids=[categories.get("Learn and Be Curious", 0), categories.get("Ownership", 0), categories.get("Insist on Highest Standards", 0)],
            star_guide={
                "situation": "What was the project or task? What was your role? Set the context clearly.",
                "task": "What were you trying to achieve? What were the expectations?",
                "action": "Focus on what went wrong and YOUR role in the failure. Be honest. Then detail what you did to address the immediate situation.",
                "result": "What was the impact? Most importantly: what did you learn and how did you change your behavior/process going forward?",
                "framework_tips": [
                    "Choose a real failure — not a weakness disguised as a strength ('I worked too hard')",
                    "Take genuine ownership — don't deflect blame",
                    "Spend 30% on the failure and 70% on the learning and changes",
                    "Show that the failure made you better, not bitter",
                    "Have a specific, concrete change in behavior/process to point to",
                ],
            },
            sample_response={
                "situation": "I was leading the migration of our authentication service from a monolith to microservices. It was my first time owning a cross-team migration that affected 15 downstream services.",
                "task": "Migrate all services to the new auth service within 6 weeks with zero downtime, while maintaining backward compatibility.",
                "action": "I created a detailed migration plan and started with the highest-traffic services. But I skipped a proper load test for one service because we were behind schedule. When we cut over that service, the new auth library had a connection pooling issue that caused cascading timeouts. It took down the checkout flow for 45 minutes. I immediately coordinated the rollback, communicated transparently to leadership, and stayed until the root cause was fully diagnosed.",
                "result": "The immediate fix took 2 hours. The deeper fix (connection pooling configuration) took 2 days. But the real outcome was process change: I created a mandatory pre-migration checklist that included load testing with 3x expected traffic, circuit breaker verification, and a graduated rollout plan. Every migration since then has used this checklist with zero incidents. I also learned to push back on aggressive timelines when they compromise quality. The experience made me a more thorough engineer and a better communicator under pressure.",
                "key_strengths_shown": ["Accountability", "Process improvement", "Resilience", "Growth mindset"],
            },
            tips=[
                "This question is about self-awareness, not perfection. A genuine failure builds trust.",
                "Don't say 'I haven't really failed' — it signals lack of self-reflection.",
                "The failure should be professional, not personal.",
                "Show the before/after: what changed in your approach because of this failure?",
                "Avoid failures involving ethical lapses, interpersonal harm, or negligence.",
            ],
            common_pitfalls=[
                "Fake failures: 'I cared too much' or 'I worked too hard'",
                "Blaming others: 'The team didn't support me'",
                "Choosing a failure with no meaningful learning",
                "Spending too much time on what went wrong and not enough on what you changed",
                "Choosing a failure that raises concerns about your competence",
            ],
            follow_up_questions=[
                "How did this experience change your approach to similar projects?",
                "What would you do differently if you could go back?",
                "How did your team respond to the failure?",
                "Have you applied these lessons since then?",
            ],
            what_interviewers_look_for=[
                "Genuine self-awareness and humility",
                "Ability to take ownership without being asked",
                "Growth mindset — converting failure into improvement",
                "Process thinking — not just 'I'll try harder' but 'I'll change the system'",
                "Resilience — bouncing back from setbacks",
            ],
            tags=["failure", "growth-mindset", "self-awareness", "learning", "ownership"],
        ),
    ]
    for q in questions:
        db.add(q)
