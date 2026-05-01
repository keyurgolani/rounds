"""SD-extra — Design a Web Crawler.

Politeness, dedup, freshness, scaling to billions of URLs.
"""
from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design a Web Crawler",
    "Hard",
    "Design a distributed web crawler that discovers, fetches, and indexes pages across the public web. "
    "It must be polite (honor robots.txt + per-host rate limits), deduplicate URLs and content at "
    "billion-scale, schedule recrawls based on importance and change rate, and survive spider traps and "
    "JS-heavy pages. Optimize for crawl throughput per dollar without getting banned by hosts.",
    hints=[
        "Politeness is non-negotiable — robots.txt + per-host token bucket gates every fetch.",
        "Two dedup layers: URL canonicalization (pre-fetch) and content hash (post-fetch).",
        "Bloom filter for 'have we seen this URL?' set-membership at billion-scale.",
        "Frontier is a priority queue, not FIFO — importance × freshness × change-rate ranks recrawl.",
        "Shard by URL host hash so each host has one owner — politeness rate-limit lives in one place.",
        "JS-heavy pages need a render farm (headless Chromium) on a separate, expensive lane.",
    ],
    constraints=[
        "Scale to 10B+ URLs in the frontier and 1B+ pages crawled per day",
        "Respect robots.txt and crawl-delay directives — never get a host's IP banned",
        "Per-host concurrency cap (default 1-2 requests in flight, tunable)",
        "Storage budget: ~50KB avg HTML × 1B pages/day → 50TB/day raw; compressed WARC",
        "Recrawl SLA: high-importance pages within hours, long tail within weeks",
    ],
    req_func=[
        "Seed with URL list; discover new URLs via link extraction",
        "Fetch HTML, follow redirects, store raw response (WARC) + parsed text",
        "Honor robots.txt per host with TTL cache",
        "Deduplicate URLs (canonicalization) and content (hash)",
        "Render JS-heavy pages via headless browser when needed",
        "Schedule recrawl based on importance × freshness × change rate",
        "Detect and skip spider traps (infinite calendars, session-id loops)",
    ],
    req_nonfunc=[
        "Throughput: 10K+ pages/sec sustained across the fleet",
        "Politeness: zero host bans; per-host QPS bounded",
        "Durability: crawled pages survive worker crashes (WARC + manifest in S3)",
        "Cost-efficient: only render JS pages on the expensive lane when needed",
        "Recoverable: frontier checkpointed; crash does not lose pending URLs",
    ],
    estimation={
        "frontier_size": "10B URLs (pending + seen)",
        "pages_per_day": "1B (~12K pages/sec)",
        "avg_page_bytes": "~50KB compressed → ~50TB/day raw, ~15TB compressed",
        "render_lane_share": "~5% of pages need JS render",
        "robots_cache": "~200M unique hosts × 5KB = ~1TB",
        "bloom_filter": "10B URLs × 10 bits/URL ≈ 12GB per shard pair",
    },
    endpoints=[
        {"method": "POST", "path": "/seeds",
         "description": "Inject seed URLs into the frontier",
         "body": "{urls:[...], priority?: int}"},
        {"method": "POST", "path": "/frontier/enqueue",
         "description": "Internal — enqueue discovered URLs after canonicalization",
         "body": "{url, parent_url, depth, importance_hint}"},
        {"method": "GET", "path": "/frontier/lease",
         "description": "Internal — fetcher leases the next URL for a host it owns",
         "body": "{worker_id, host_shard}"},
        {"method": "POST", "path": "/pages",
         "description": "Internal — fetcher records a fetched page (WARC offset + metadata)",
         "body": "{url, status, content_hash, warc_ref, fetched_at}"},
        {"method": "GET", "path": "/robots/{host}",
         "description": "Get cached robots.txt rules for a host",
         "body": "{}"},
    ],
    tables=[
        {"name": "frontier",
         "columns": ["url_hash BIGINT PK", "url TEXT", "host VARCHAR(253)", "priority INT",
                     "scheduled_at BIGINT", "importance FLOAT", "depth INT", "host_shard INT"]},
        {"name": "pages",
         "columns": ["url_hash BIGINT PK", "url TEXT", "content_hash BIGINT", "status INT",
                     "fetched_at BIGINT", "warc_ref VARCHAR(128)", "etag VARCHAR(128)",
                     "last_modified BIGINT", "change_rate FLOAT"]},
        {"name": "links",
         "columns": ["src_hash BIGINT", "dst_hash BIGINT", "anchor TEXT",
                     "PRIMARY KEY (src_hash, dst_hash)"]},
        {"name": "robots",
         "columns": ["host VARCHAR(253) PK", "rules TEXT", "crawl_delay_ms INT",
                     "fetched_at BIGINT", "ttl_at BIGINT"]},
        {"name": "hosts",
         "columns": ["host VARCHAR(253) PK", "shard INT", "qps_cap FLOAT",
                     "last_fetch_at BIGINT", "consecutive_5xx INT"]},
    ],
    indexes=[
        "(host_shard, priority DESC, scheduled_at) on frontier",
        "(host, scheduled_at) on frontier for politeness pacing",
        "(content_hash) on pages for content dedup",
        "(host) on pages for per-host stats",
    ],
    hld_desc=(
        "URL frontier (priority queue, sharded by host hash) feeds a fetcher pool. Each fetcher owns a "
        "set of host shards and enforces per-host rate limit via token bucket. Robots.txt cached per "
        "host. Fetched HTML written to WARC on S3; parsed for links → canonicalized → Bloom-filter "
        "checked → enqueued back into frontier. Content hash dedups near-duplicates. JS-heavy pages "
        "diverted to a render farm (headless Chromium) on a separate lane. Scheduler periodically "
        "re-enqueues pages for recrawl based on importance × age × change-rate. ZooKeeper coordinates "
        "host-shard ownership and leader election."
    ),
    hld_components=[
        {"name": "Seed Loader", "role": "Bulk-inject initial URL list"},
        {"name": "URL Frontier", "role": "Priority queue sharded by host hash"},
        {"name": "Host Coordinator (ZK)", "role": "Assign host shards to fetchers; leader-elect"},
        {"name": "Fetcher Pool", "role": "Owns host shards; per-host token bucket; HTTP fetch"},
        {"name": "Robots Cache", "role": "Per-host robots.txt with TTL"},
        {"name": "DNS Resolver", "role": "Async batched resolution + cache"},
        {"name": "Render Farm", "role": "Headless Chromium for JS-heavy pages"},
        {"name": "Parser + Extractor", "role": "Parse HTML, extract links, canonicalize"},
        {"name": "URL Dedup (Bloom)", "role": "Set-membership for 'seen' URLs"},
        {"name": "Content Dedup", "role": "SimHash / MinHash for near-duplicate detection"},
        {"name": "WARC Writer", "role": "Append-only blobs on S3"},
        {"name": "Link Graph Store", "role": "Edges for PageRank + recrawl signals"},
        {"name": "Scheduler", "role": "Recrawl ranker by importance × freshness × change rate"},
        {"name": "Trap Detector", "role": "Per-host depth caps + URL-pattern entropy checks"},
    ],
    detailed_design={
        "url_frontier": (
            "Priority queue keyed by (host_shard, priority, scheduled_at). Each host has a sub-queue; "
            "the fetcher dequeues round-robin across hosts it owns to balance hosts. Priority blends "
            "importance (PageRank-ish), freshness (age since last fetch), and change-rate. Backed by a "
            "log-structured store (RocksDB or Kafka per shard) so enqueue is O(1) and lease is pop+ack."
        ),
        "politeness_and_robots": (
            "Before fetching any URL on host H: (1) ensure robots.txt is cached (refresh if expired) and "
            "the URL is allowed; (2) check token bucket for H — refilled at 1/crawl_delay rate (default "
            "1 req/sec, lower if Crawl-delay set); (3) on 5xx or 429, halve the rate and back off "
            "exponentially. Single fetcher owns each host shard so rate limit is enforced in one place."
        ),
        "dns_resolution": (
            "Async resolver with shared cache (e.g., 200M hosts × 100B = ~20GB). Batches lookups, "
            "caches negative results, refreshes near-TTL entries. Avoids per-fetch latency spike — DNS "
            "is otherwise ~50% of cold-fetch wall time."
        ),
        "url_dedup": (
            "Two stages. (1) Canonicalization: lowercase host, strip default ports, sort query params, "
            "remove tracking params, resolve relative paths. (2) Bloom filter (10B × 10 bits ≈ 12GB) "
            "per host shard for fast 'have we seen?' check. False positives ~1% accepted — re-fetch "
            "would be wasted, but a backing exact-set (RocksDB) confirms before persisting."
        ),
        "content_dedup": (
            "After fetch, compute a content hash (SHA-256) and a SimHash over the textual content for "
            "near-dup detection. If exact hash matches an existing page, drop it; if SimHash is within "
            "Hamming distance ≤3, mark as near-dup and downweight in the link graph."
        ),
        "render_lane": (
            "Quick heuristic on raw HTML: little text, lots of <script>, or known SPA frameworks → "
            "send to render farm. Headless Chromium with a JS-execution timeout (5s) and resource cap. "
            "Render lane is ~10× costlier per page; gate it carefully — only ~5% of URLs."
        ),
        "trap_detection": (
            "Per-host depth cap (e.g., 20). URL-pattern entropy: if many URLs differ only by an "
            "increasing query param (calendar trap, session id), penalize that pattern's priority and "
            "cap its enqueue rate. Detect cycles via the link graph."
        ),
        "recrawl_scheduling": (
            "Score = importance × age_factor × change_rate. importance from inbound link count or "
            "PageRank. age_factor = (now − last_fetch) / target_interval. change_rate learned from "
            "diff history (fraction of fetches where content_hash changed). High-importance frequently-"
            "changing news pages re-enter the frontier in hours; static pages, weeks."
        ),
        "distributed_coordination": (
            "ZooKeeper holds the host-shard → fetcher map and a fetcher lease (ephemeral node). On "
            "fetcher death, ZK fires a watch and the leader reassigns shards. Frontier writes are "
            "idempotent (keyed by url_hash) so reassignment is safe. Bloom filters per shard rebuild "
            "from RocksDB on takeover (cold for ~minutes)."
        ),
        "storage_layout": (
            "Raw HTML appended to WARC files on S3 (10GB rolls). pages table holds metadata + WARC "
            "offset. links table is the directed graph (src_hash → dst_hash) for recrawl ranking and "
            "downstream PageRank. All hashed by url_hash for partitioning."
        ),
    },
    trade_offs=[
        {"option": "Frontier: shard by URL hash vs by host hash",
         "for_url_hash": "Even load distribution",
         "for_host_hash": "Politeness rate-limit lives in one place; co-located robots.txt cache",
         "recommendation": "Host hash — politeness correctness > load evenness; rebalance hot hosts."},
        {"option": "Bloom filter vs exact set for URL dedup",
         "for_bloom": "12GB/shard for 10B URLs; O(1) check; ~1% false-positive cost",
         "for_exact": "Zero false positives but ~10× the memory or disk seeks",
         "recommendation": "Bloom in front, RocksDB as source of truth before persisting."},
        {"option": "Render every page vs render-when-needed",
         "for_render_all": "Uniform pipeline; no heuristic mistakes",
         "for_selective": "10× cheaper; render farm reserved for SPA-heavy pages",
         "recommendation": "Selective — JS render is the most expensive op in the pipeline."},
        {"option": "FIFO frontier vs priority frontier",
         "for_fifo": "Simple, fair BFS",
         "for_priority": "Recrawl high-importance pages first; freshness SLA",
         "recommendation": "Priority — BFS alone wastes budget on low-value pages."},
    ],
    tips=[
        "Lead with politeness — interviewers expect robots.txt + per-host rate limit on the first slide.",
        "Shard by host hash, not URL hash — politeness must live in one place.",
        "Two dedup layers: URL canonicalization (pre-fetch) AND content hash (post-fetch). Don't conflate.",
        "Bloom filter is the right answer for set-membership at 10B URLs. Quote the 10 bits/URL number.",
        "Mention spider traps unprompted — depth cap + URL entropy check shows seniority.",
        "Render farm as a separate lane is the senior move — it's 10× cost; don't bury it.",
        "Recrawl scheduling = importance × freshness × change rate. Memorize this triplet.",
    ],
    thought_process=[
        "1. Clarify scope: public-web crawler, billions of URLs, freshness matters.",
        "2. Estimate: 1B pages/day → ~12K pages/sec → fleet sized at ~5K fetchers.",
        "3. APIs: seed inject, frontier enqueue/lease (internal), pages record.",
        "4. Frontier: priority queue, sharded by host hash for politeness ownership.",
        "5. Politeness: robots.txt cache + per-host token bucket, single owner per host.",
        "6. Dedup: canonicalize URL → Bloom filter → exact set; SHA + SimHash on content.",
        "7. JS-heavy pages: diverted to render farm (headless Chromium, separate budget).",
        "8. Recrawl: scheduler scores pages by importance × age × change-rate.",
        "9. Trap detection: depth cap, URL entropy, cycle detection on link graph.",
        "10. Coordination: ZK for shard ownership + leader election; idempotent enqueue.",
    ],
    tags=["crawler", "distributed", "queue", "scaling", "backend"],
    arch_nodes=[
        {"id": "seed", "label": "Seed Loader", "type": "client"},
        {"id": "front", "label": "URL Frontier", "type": "queue"},
        {"id": "zk", "label": "ZooKeeper", "type": "service"},
        {"id": "fetch", "label": "Fetcher Pool", "type": "server"},
        {"id": "robots", "label": "Robots Cache", "type": "cache"},
        {"id": "dns", "label": "DNS Resolver", "type": "cache"},
        {"id": "render", "label": "Render Farm", "type": "server"},
        {"id": "parse", "label": "Parser + Extractor", "type": "server"},
        {"id": "bloom", "label": "URL Dedup (Bloom)", "type": "cache"},
        {"id": "warc", "label": "WARC on S3", "type": "database"},
        {"id": "pages", "label": "Pages + Links DB", "type": "database"},
        {"id": "sched", "label": "Recrawl Scheduler", "type": "server"},
    ],
    arch_edges=[
        {"source": "seed", "target": "front"},
        {"source": "zk", "target": "fetch", "label": "host shards"},
        {"source": "front", "target": "fetch", "label": "lease"},
        {"source": "fetch", "target": "dns"},
        {"source": "fetch", "target": "robots"},
        {"source": "fetch", "target": "render", "label": "JS-heavy"},
        {"source": "fetch", "target": "parse"},
        {"source": "render", "target": "parse"},
        {"source": "parse", "target": "bloom", "label": "seen?"},
        {"source": "parse", "target": "front", "label": "enqueue new"},
        {"source": "fetch", "target": "warc"},
        {"source": "parse", "target": "pages"},
        {"source": "sched", "target": "front", "label": "recrawl"},
        {"source": "pages", "target": "sched"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant F as Frontier\n"
        "  participant W as Fetcher\n"
        "  participant R as Robots\n"
        "  participant H as Host\n"
        "  participant P as Parser\n"
        "  participant B as Bloom\n"
        "  participant S as WARC/S3\n"
        "  W->>F: lease (host_shard)\n"
        "  F-->>W: url\n"
        "  W->>R: rules for host\n"
        "  R-->>W: allow + crawl-delay\n"
        "  W->>W: token-bucket wait\n"
        "  W->>H: GET url\n"
        "  H-->>W: 200 HTML\n"
        "  W->>S: append WARC\n"
        "  W->>P: parse + extract links\n"
        "  P->>B: seen(url)?\n"
        "  B-->>P: no\n"
        "  P->>F: enqueue new urls"
    ),
    er_diagram=(
        "erDiagram\n"
        "  HOST ||--o{ FRONTIER : queues\n"
        "  HOST ||--|| ROBOTS : has\n"
        "  PAGE ||--o{ LINK : outbound\n"
        "  PAGE { bigint url_hash PK\n bigint content_hash\n int status\n string warc_ref }\n"
        "  FRONTIER { bigint url_hash PK\n int priority\n bigint scheduled_at }\n"
        "  ROBOTS { string host PK\n int crawl_delay_ms\n bigint ttl_at }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Seed URLs] --> B[Frontier]\n"
        "  B --> C{Robots.txt allows?}\n"
        "  C -->|No| X[Drop]\n"
        "  C -->|Yes| D[Token-bucket wait]\n"
        "  D --> E[HTTP fetch]\n"
        "  E --> F{JS-heavy?}\n"
        "  F -->|Yes| G[Render farm]\n"
        "  F -->|No| H[Parse]\n"
        "  G --> H\n"
        "  H --> I[Extract + canonicalize links]\n"
        "  I --> J{Bloom: seen?}\n"
        "  J -->|No| B\n"
        "  J -->|Yes| K[Skip]\n"
        "  H --> L[Content hash dedup]\n"
        "  L --> M[Persist WARC + pages]"
    ),
    tradeoff_title="Shard frontier by URL hash vs by host hash",
    tradeoff_options=[
        {"label": "Shard by URL hash",
         "description": "URLs distributed evenly across shards, regardless of host.",
         "pros": ["Even load distribution", "No hot-shard problem", "Trivial sharding key"],
         "cons": ["Per-host rate limit must be coordinated across shards (hard)",
                 "robots.txt cache duplicated across shards",
                 "Politeness becomes a distributed-counter problem"]},
        {"label": "Shard by host hash",
         "description": "All URLs for a host land on the same shard / fetcher.",
         "pros": ["Politeness rate-limit lives in one place — correct by construction",
                 "Co-located robots.txt cache, DNS cache",
                 "Single fetcher owns host = simple token bucket"],
         "cons": ["Hot hosts (e.g., wikipedia.org) overload one shard",
                 "Need rebalance / split-large-host logic"]},
    ],
    tradeoff_rec="Host hash — politeness correctness wins; mitigate hot hosts by splitting them across "
                 "sub-shards keyed by url_hash within the host.",
    senior_topics=[
        _topic("politeness-rate-limits",
               "Politeness: robots.txt + Per-Host Token Bucket",
               "Politeness is the single most important crawler property. Get it wrong and the host "
               "blackholes your IP range, often permanently.",
               [
                   ("robots.txt protocol",
                    "Fetched once per host with TTL (~24h). Parse User-agent, Disallow, Allow, and "
                    "Crawl-delay. Cache in shared store keyed by host. Refresh on expiry, on first "
                    "fetch after long gap, and on 5xx burst (host may have changed rules)."),
                   ("Per-host token bucket",
                    "Bucket capacity 1-2, refill rate = 1/Crawl-delay (default 1/sec). Fetcher waits "
                    "for a token before issuing the request. Refill rate halves on 429/5xx and "
                    "geometrically backs off on consecutive errors."),
                   ("Why single owner per host",
                    "If two fetchers crawl the same host independently, each enforcing 1 QPS, the "
                    "host sees 2 QPS — politeness violated. Sharding by host hash gives one owner; "
                    "ZK lease prevents concurrent ownership during failover."),
                   ("Dealing with shared-IP hosts",
                    "Many small sites share a single CDN/IP. Apply a secondary token bucket keyed by "
                    "resolved IP, not just host, to avoid hammering the underlying server."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant Q as URL queue\n"
                   "  participant W as Fetcher\n"
                   "  participant TB as Token Bucket\n"
                   "  participant H as Host\n"
                   "  Q->>W: url for host=example.com\n"
                   "  W->>TB: take token\n"
                   "  alt token available\n"
                   "    TB-->>W: ok\n"
                   "    W->>H: GET /page\n"
                   "  else empty\n"
                   "    TB-->>W: wait Δt\n"
                   "    W->>W: sleep\n"
                   "  end"
               )),
        _topic("url-and-content-dedup",
               "Two-Layer Dedup: URL Canonicalization + Content Hash",
               "URL dedup prevents wasted fetches; content dedup prevents wasted indexing. Both are "
               "needed and they answer different questions.",
               [
                   ("URL canonicalization",
                    "Lowercase host, strip default ports, sort query params, remove tracking params "
                    "(utm_*, fbclid), resolve relative paths, normalize trailing slash. ?a=1&b=2 and "
                    "?b=2&a=1 collapse to one URL. Keeps the frontier from re-discovering the same "
                    "page via different surface forms."),
                   ("Bloom filter for set membership",
                    "10B URLs × 10 bits/URL ≈ 12GB per shard. False-positive rate ~1% — meaning ~1% "
                    "of NEW URLs falsely reported 'seen' and skipped. Acceptable: a backing exact "
                    "set (RocksDB) confirms before persisting. False negatives are impossible."),
                   ("Content hash (exact dedup)",
                    "SHA-256 of normalized text. If two URLs return identical content, mark one as "
                    "an alias of the other and downweight the duplicate in the link graph."),
                   ("SimHash for near-duplicates",
                    "64-bit SimHash on shingled tokens. Hamming distance ≤3 → near-duplicate. Catches "
                    "boilerplate-only variants, mirror sites, and printer-friendly versions of the "
                    "same article."),
                   ("Why both layers",
                    "URL dedup avoids the fetch entirely (cheap). Content dedup catches mirrors and "
                    "session-id-suffixed URLs that canonicalization missed (expensive but rare)."),
               ],
               diagram=(
                   "graph LR\n"
                   "  A[Raw URL] --> B[Canonicalize]\n"
                   "  B --> C{Bloom seen?}\n"
                   "  C -->|Maybe| D[Exact set check]\n"
                   "  C -->|No| E[Enqueue]\n"
                   "  D -->|Hit| F[Drop]\n"
                   "  D -->|Miss| E\n"
                   "  E --> G[Fetch]\n"
                   "  G --> H[SHA + SimHash]\n"
                   "  H --> I{Dup?}\n"
                   "  I -->|Yes| J[Mark alias]\n"
                   "  I -->|No| K[Persist]"
               )),
        _topic("recrawl-scheduling",
               "Recrawl Scheduling: Importance × Freshness × Change Rate",
               "A finite crawl budget must prioritize what's worth re-fetching. The right score "
               "balances how valuable a page is, how stale it might be, and how often it actually "
               "changes when re-fetched.",
               [
                   ("Importance signal",
                    "Inbound link count (cheap proxy) or full PageRank computed offline weekly on the "
                    "link graph. High-importance pages get priority budget; long-tail pages crawl "
                    "less often."),
                   ("Freshness factor",
                    "age_factor = (now − last_fetch) / target_interval, where target_interval is "
                    "tuned per topic (news: 1h; reference: 1 week). Pages past their target "
                    "fly to the top of the priority queue."),
                   ("Change-rate learning",
                    "Track per-page fraction of recrawls where content_hash changed. Pages that "
                    "rarely change get longer target_interval; pages that always change get shorter. "
                    "This is the long-term steady-state optimization."),
                   ("The full score",
                    "priority = w1 × importance + w2 × age_factor + w3 × change_rate. Weights tuned "
                    "by offline experiment against observed ranking-quality metrics."),
                   ("Budget partitioning",
                    "~80% of crawl budget on recrawl, ~20% on discovery. Discovery starvation is the "
                    "common pitfall — corpus growth stalls if it's all recrawl."),
               ],
               diagram=(
                   "graph TD\n"
                   "  A[Page] --> B[Importance]\n"
                   "  A --> C[Age factor]\n"
                   "  A --> D[Change rate]\n"
                   "  B --> E[Score]\n"
                   "  C --> E\n"
                   "  D --> E\n"
                   "  E --> F[Frontier priority]"
               )),
        _topic("trap-detection",
               "Spider Trap and Infinite-Loop Detection",
               "Naive crawlers get stuck in calendars, search-result pagination, or session-id loops, "
               "burning crawl budget on near-empty pages.",
               [
                   ("Per-host depth cap",
                    "Hard cap on link depth from any seed (e.g., 20). Beyond it, only enqueue if "
                    "importance score is very high. Prevents runaway recursion."),
                   ("URL-pattern entropy",
                    "Group URLs on a host by template (path with numeric segments masked). If a "
                    "template generates >10K children with low content variance, throttle that "
                    "template's enqueue rate aggressively."),
                   ("Calendar / pagination traps",
                    "Detect URLs differing only by an increasing date or page number. If new pages "
                    "in the sequence consistently SimHash-collide with prior pages, abandon the "
                    "sequence."),
                   ("Session-ID stripping",
                    "Recognize common session-id query params (sid, jsessionid, PHPSESSID) during "
                    "canonicalization and strip them. Prevents the same logical URL from re-entering "
                    "the frontier under a fresh ID."),
                   ("Cycle detection on link graph",
                    "Periodic offline pass on the link graph flags strongly-connected components "
                    "with low external entry — likely traps. Manually review and blacklist."),
               ]),
        _topic("distributed-coordination",
               "ZooKeeper for Host-Shard Ownership and Leader Election",
               "The crawler is a stateful distributed system; static config doesn't survive fetcher "
               "churn. ZK (or etcd) provides the consensus layer for ownership and failover.",
               [
                   ("Host-shard map",
                    "ZK znode /crawler/shards/{shard_id} → fetcher_id. Fetcher writes its ID with an "
                    "ephemeral lease; on death, the znode disappears and the leader reassigns."),
                   ("Leader election",
                    "Standard ZK recipe: candidates create sequential ephemeral znodes under "
                    "/crawler/leader; lowest sequence wins. Leader runs the rebalancer and the "
                    "scheduler. Loss of leader triggers re-election in <1s."),
                   ("Idempotent enqueue",
                    "Frontier writes keyed by url_hash. Replay during failover is safe — duplicate "
                    "enqueue is a no-op. Bloom filter ensures we don't re-fetch already-crawled URLs."),
                   ("Bloom filter recovery",
                    "On shard takeover, the new fetcher rebuilds its Bloom filter from RocksDB — "
                    "warmup takes minutes. During warmup, dedup is conservative (consult exact set) "
                    "to avoid duplicate fetches."),
                   ("Why not just hash-mod",
                    "Static hash-mod doesn't handle fetcher churn or hot-host splits. Consistent "
                    "hashing helps with rebalancing minimization but still needs a coordination "
                    "store to publish the ring."),
               ],
               diagram=(
                   "graph TD\n"
                   "  L[Leader Fetcher] -->|publishes| ZK[ZooKeeper]\n"
                   "  ZK -->|shard map| F1[Fetcher 1]\n"
                   "  ZK -->|shard map| F2[Fetcher 2]\n"
                   "  ZK -->|shard map| F3[Fetcher 3]\n"
                   "  F2 -.x ZK\n"
                   "  ZK -->|reassign| L\n"
                   "  L -->|new map| F1\n"
                   "  L -->|new map| F3"
               )),
        _topic("render-farm",
               "Render Farm for JS-Heavy Pages",
               "Modern SPAs return near-empty HTML; the real content materializes only after JS "
               "executes. A separate render lane is required, but it's 10× the cost of a plain fetch.",
               [
                   ("Routing heuristic",
                    "Quick test on raw HTML: text-to-script ratio low, common SPA framework markers "
                    "(<div id='root'>, Next.js __NEXT_DATA__, React/Vue mount points), or known "
                    "SPA hosts → divert to render lane. Otherwise plain fetch is fine."),
                   ("Headless Chromium pool",
                    "Pool of headless browser instances; each isolated by container or microVM for "
                    "security. Hard timeouts: 5s navigation, 2s post-load idle, 30MB memory cap, "
                    "block tracking pixels and analytics resources."),
                   ("Cost discipline",
                    "Render lane is ~10× the cost of plain fetch. Cap to ~5% of pages. Cache render "
                    "results aggressively keyed by URL — many pages re-render to the same DOM."),
                   ("Security",
                    "Run renders in a sandbox (gVisor, Firecracker microVMs). Malicious JS can "
                    "exhaust CPU, exfiltrate data, or attempt SSRF. Block private IP ranges and "
                    "internal DNS at the network level."),
                   ("Fallback behavior",
                    "If render times out or fails, fall back to the static HTML and mark the page "
                    "as 'render-incomplete'. Re-enqueue with lower priority to avoid burning budget "
                    "on a problematic URL."),
               ]),
    ],
)
