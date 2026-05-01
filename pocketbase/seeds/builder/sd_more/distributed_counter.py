"""SDQ — Design a Distributed Counter Service.

A horizontally-scaled service that increments and reads counts (likes, views,
reactions, rate-limits, follower counts) at internet scale, where a single hot
counter (a viral tweet, a celebrity Like button) can attract 1M+ writes/sec and
the long tail spans billions of low-traffic counters. Mirrors `sd_questions.SD_01`
shape via the `_q` / `_topic` helpers.
"""
from __future__ import annotations

from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design a Distributed Counter Service",
    "Medium",
    "Design a service that maintains numeric counters at massive scale: like/view counters on tweets and "
    "videos, reaction counts on posts, follower counts, rate-limit counters, and unique-visitor counts. "
    "The system must absorb single-counter write hotspots in the millions of QPS (one viral tweet), serve "
    "reads with low latency from any region, store billions of low-traffic counters cheaply, support "
    "exact and approximate (HyperLogLog-style) modes, and remain idempotent under client retries. "
    "Display values are eventually consistent — readers tolerate seconds of staleness — but no increment "
    "may be lost or double-counted.",
    hints=[
        "The whole problem is the hot key: one viral counter at 1M writes/sec collapses naive INCR.",
        "Sharded counters (random sub-counter per increment, sum on read) are THE pattern — name it early.",
        "Approximate vs exact is a per-counter choice: views can be HLL, payments cannot.",
        "Idempotence belongs at the edge with a dedup key — don't trust 'INCR is idempotent' (it isn't).",
        "Kafka windowed aggregation flattens write storms into per-second batched DB updates.",
        "Read path = cached aggregate. Write path = append + async fold. Don't conflate them.",
    ],
    constraints=[
        "Hot counters: a single counter sustains 1M+ increments/sec for hours (viral content).",
        "Long tail: billions of counters, most at <1 QPS — storage cost dominates for the cold majority.",
        "Reads tolerate eventual consistency (seconds of staleness fine for view counts, likes).",
        "No lost increments and no double-counts — clients retry aggressively on network errors.",
        "Per-region reads ≤ 50 ms p99; cross-region replication lag ≤ 5 s acceptable.",
        "Some counters have TTL (rate-limit windows: 1-min, 1-hour) and must auto-expire.",
        "Some counters are unique-cardinality (unique viewers per video) — exact storage is prohibitive.",
    ],
    req_func=[
        "INCR(counter_id, delta=1, dedup_key) — idempotent additive increment.",
        "DECR(counter_id, delta=1, dedup_key) — for unlikes / undo.",
        "GET(counter_id) — current aggregated value (eventually consistent).",
        "GET_BATCH(ids[]) — one round trip for fan-out reads (timeline view counts).",
        "ADD_UNIQUE(counter_id, member_id) — HyperLogLog-style unique-cardinality counter.",
        "TTL counters: SET_WITH_TTL(counter_id, window_sec) for rate limits and rolling windows.",
        "RESET(counter_id) — admin/debug; rare.",
    ],
    req_nonfunc=[
        "Write throughput: 10M increments/sec aggregate; 1M+ on a single hot counter.",
        "Read latency: p50 < 5 ms, p99 < 50 ms intra-region.",
        "Eventual consistency: reads converge within ~5 s of the last write under steady load.",
        "Durability: at-least-once + dedup → effectively exactly-once; no lost increments on broker failure.",
        "Cardinality: 10B+ counters total; per-counter storage ≤ 100 B for the cold tail.",
        "Cost: HLL-mode unique counters ≤ 12 KB per counter regardless of cardinality.",
        "TTL accuracy: rate-limit windows expire within ±1 s of nominal.",
    ],
    estimation={
        "total_counters": "10B (tweets, posts, videos, follower counts, rate-limit windows)",
        "hot_counter_qps": "1M+ writes/sec on a viral tweet sustained for hours",
        "aggregate_writes": "10M increments/sec across the fleet at peak",
        "aggregate_reads": "50M reads/sec (timeline rendering fans out reads massively)",
        "shards_per_hot_counter": "100–1000 sub-counters → caps a single Redis shard at ≤10k writes/sec",
        "kafka_partitions": "1024 partitions for the increment topic; counter_id hashed in",
        "hll_register_count": "16384 registers × 6 bits ≈ 12 KB → ±0.81% relative error",
        "dedup_window": "5 min sliding window per (counter, dedup_key); 1B keys × 32 B ≈ 32 GB cluster-wide",
    },
    endpoints=[
        {"method": "POST", "path": "/v1/counters/{id}/incr",
         "description": "Increment with optional delta and dedup key",
         "body": "{delta: 1, dedup_key: 'uuid', client_ts: 1714312345}"},
        {"method": "POST", "path": "/v1/counters/{id}/decr",
         "description": "Decrement (unlike / undo)",
         "body": "{delta: 1, dedup_key: 'uuid'}"},
        {"method": "GET", "path": "/v1/counters/{id}",
         "description": "Read current aggregated value (cached, eventually consistent)"},
        {"method": "POST", "path": "/v1/counters:batchGet",
         "description": "Read N counters in one round trip; used by timeline/feed renderers",
         "body": "{ids: ['c1','c2',...]}"},
        {"method": "POST", "path": "/v1/counters/{id}/unique",
         "description": "Add a member to a unique-cardinality (HLL) counter",
         "body": "{member_id: 'user_42'}"},
        {"method": "GET", "path": "/v1/counters/{id}/unique",
         "description": "Read approximate unique cardinality (HLL estimate)"},
        {"method": "POST", "path": "/v1/counters/{id}/ttl",
         "description": "Configure auto-expiry for a rate-limit / rolling window counter",
         "body": "{window_sec: 60}"},
        {"method": "GET", "path": "/admin/hot-counters",
         "description": "List counters currently sharded with their shard counts"},
    ],
    tables=[
        {"name": "counter_meta",
         "columns": ["counter_id VARCHAR(64) PK", "kind ENUM(exact,hll,ttl)",
                     "shard_count INT DEFAULT 1", "ttl_sec INT NULL",
                     "created_at_ms BIGINT", "owner_namespace VARCHAR(64)"]},
        {"name": "counter_value (system of record, partitioned by counter_id hash)",
         "columns": ["counter_id VARCHAR(64)", "shard_idx INT", "value BIGINT",
                     "updated_at_ms BIGINT", "PRIMARY KEY (counter_id, shard_idx)"]},
        {"name": "counter_hll (HyperLogLog sketches)",
         "columns": ["counter_id VARCHAR(64) PK", "registers BYTES (12 KB)",
                     "estimated_card BIGINT", "updated_at_ms BIGINT"]},
        {"name": "dedup_keys (sliding window, Redis or RocksDB)",
         "columns": ["dedup_key VARCHAR(64)", "counter_id VARCHAR(64)",
                     "applied_at_ms BIGINT", "PRIMARY KEY (counter_id, dedup_key)",
                     "TTL 300 sec"]},
        {"name": "rate_limit_windows (TTL counters)",
         "columns": ["counter_id VARCHAR(64) PK", "value INT", "window_start_ms BIGINT",
                     "expire_at_ms BIGINT"]},
        {"name": "kafka_increments (topic, not a table)",
         "columns": ["partition INT (counter_id % 1024)", "offset BIGINT",
                     "counter_id VARCHAR(64)", "delta INT", "dedup_key VARCHAR(64)",
                     "ts_ms BIGINT"]},
    ],
    indexes=[
        "counter_value: PRIMARY KEY (counter_id, shard_idx) — read-side SUM scans the small shard set per id.",
        "dedup_keys: TTL index drops entries after 5 min; per-(counter_id, dedup_key) hashed lookup.",
        "counter_meta: secondary on shard_count > 1 → admin view of currently hot counters.",
        "Kafka: producer hashes by counter_id so all increments for one counter land on one partition (in-order).",
        "HLL sketches: keyed by counter_id; registers stored inline (12 KB) — no external index.",
    ],
    hld_desc=(
        "Two-stage write path and a cache-fronted read path. Clients POST to a stateless ingest tier behind "
        "a regional load balancer; ingest validates the dedup_key, writes the increment to a Redis "
        "sub-counter (HINCRBY on a random shard_idx for hot counters), and asynchronously publishes the "
        "increment to Kafka. A flink/kstreams aggregator consumes the topic, batches per-counter deltas in "
        "1-second tumbling windows, and applies them to the durable system of record (Cassandra or Spanner) "
        "via UPDATE ... SET value = value + delta. The read path serves from Redis (write-through aggregate) "
        "with the SoR as the back-stop on cold misses. For hot counters the value is the SUM over "
        "shard_count sub-counters; the system promotes a counter from 1 shard to 100–1000 shards "
        "automatically when sampled QPS exceeds threshold. HLL counters live entirely in Redis with "
        "periodic snapshots to the SoR. TTL counters are pure Redis with EXPIRE."
    ),
    hld_components=[
        {"name": "API Gateway", "role": "Auth, rate-limit, routing; terminates TLS"},
        {"name": "Ingest Service", "role": "Stateless; dedup check, choose sub-counter shard, write Redis + Kafka"},
        {"name": "Dedup Store", "role": "Redis SETNX with 5-min TTL on dedup_key; rejects retries"},
        {"name": "Counter Cache", "role": "Redis cluster; HINCRBY on (counter_id, shard_idx); per-counter SUM aggregate"},
        {"name": "Kafka Increment Topic", "role": "Durable log of every applied increment; partitioned by counter_id"},
        {"name": "Aggregator (Flink/KStreams)", "role": "1-sec tumbling windows; folds deltas; writes to SoR"},
        {"name": "System of Record", "role": "Cassandra or Spanner; counter_value table; durable truth"},
        {"name": "Hot-Counter Detector", "role": "Sampled QPS sketch; promotes to N sub-counters; broadcasts shard_count"},
        {"name": "HLL Service", "role": "Unique-cardinality sketches; ADD register update; ESTIMATE on read"},
        {"name": "Read Cache", "role": "CDN/edge for ultra-hot public counters (likes on viral tweet)"},
        {"name": "Admin/Metrics", "role": "Per-counter QPS, shard_count, dedup hit rate, replication lag"},
    ],
    detailed_design={
        "hot_key_problem": (
            "A naive design picks one row in one shard for each counter. A viral tweet at 1M writes/sec "
            "drives 1M INCR/sec at one Redis instance, which caps at ~100k ops/sec; the shard saturates, "
            "every other counter hosted on it suffers tail-latency, and the SoR partition behind it "
            "deadlocks on row-level locks for the UPDATE ... SET value = value + 1. This is THE problem "
            "the design exists to solve. Every other concern — durability, replication, persistence — is "
            "secondary to correctly absorbing the single-counter spike."
        ),
        "sharded_counter_pattern": (
            "Replace the single row with N sub-counters: counter_value(counter_id, shard_idx, value). "
            "On increment, the client (or ingest) picks shard_idx = random(0, N-1) and HINCRBY's that "
            "specific cell. Aggregate read = SUM(value) WHERE counter_id = X. With N=1000 sub-counters, "
            "1M writes/sec spreads to 1k writes/sec/shard — every Redis instance stays in its happy zone. "
            "Trade-off: read cost grows from 1 GET to N gets (mitigated by caching the SUM behind a "
            "second key updated on each window aggregation). N is tuned per counter: cold counters keep "
            "N=1; the hot-counter detector promotes them to N=100 → N=1000 as QPS climbs. Demotion is "
            "lazy with hysteresis to prevent flapping."
        ),
        "kafka_aggregation_pipeline": (
            "Every applied increment (after Redis HINCRBY) is published to a Kafka topic partitioned by "
            "counter_id (so in-order per counter). A Flink job consumes with 1-second tumbling windows "
            "per counter, sums deltas, and applies a single UPDATE counter_value SET value = value + Δ "
            "to the SoR. This collapses 1M Redis writes/sec into 1 SoR write/sec/counter — the SoR sees "
            "human-scale load even when the cache sees machine-scale load. Late events go to a side "
            "stream and are merged at the next window. The pipeline is replayable: restart from a "
            "checkpoint to rebuild the cache after a region failure."
        ),
        "exact_vs_approximate": (
            "Counters split into two regimes. EXACT (likes, retweets, follower counts, payments): "
            "every increment must be reflected; sharded counter pattern + Kafka pipeline + Cassandra "
            "counter columns or Spanner row-add. APPROXIMATE unique-cardinality (unique viewers per "
            "video, distinct IPs hitting an endpoint): naive exact storage = O(unique_users) per counter, "
            "which is prohibitive. Use HyperLogLog: a 12 KB sketch (16384 6-bit registers) estimates "
            "cardinality up to 10^9 with ±0.81% standard error. ADD = hash(member) → register update; "
            "ESTIMATE = harmonic mean of register values. HLL is mergeable: union of two sketches is "
            "register-wise max — perfect for cross-region rollups."
        ),
        "idempotence_dedup": (
            "Clients retry on any network error. INCR is NOT naturally idempotent — two retries = two "
            "increments. The fix is a client-supplied dedup_key (UUID) per logical increment. Ingest "
            "checks Redis with SET NX dedup:counter_id:key EX 300; if it loses the race, the increment "
            "is silently dropped as a duplicate. Window: 5 min (covers any plausible retry; longer "
            "windows cost RAM proportionally). On dedup-store failure, fail OPEN (allow the increment) "
            "for likes/views — undercounting is worse than rare double-counts. For counters where "
            "double-count is unacceptable (payments masquerading as counters: shouldn't, but happens), "
            "fail CLOSED — return error and let the client retry."
        ),
        "redis_hincrby_vs_db_update": (
            "Two paths exist for every increment. (A) Redis HINCRBY on (counter:id, shard_idx): "
            "in-memory, ≤200 µs, 100k ops/sec/instance, but loss-on-crash. (B) DB UPDATE counter_value "
            "SET value = value + 1: durable, but 1–5 ms, ≤5k ops/sec/partition, row-locked. The right "
            "answer is BOTH, layered: Redis is the live aggregate (read path), Kafka is the durable "
            "audit log (write path), DB is the periodic reconciliation (recovery path). Redis HINCRBY "
            "happens first (fast ack to the client), Kafka publish happens immediately after (durability "
            "guarantee), DB UPDATE happens via the windowed aggregator (cost-efficient consolidation). "
            "Crash of any one layer is recoverable from the others."
        ),
        "write_through_cache": (
            "The Redis 'aggregate' key (no shard suffix) is the read-fast path. It is updated by the "
            "Kafka aggregator's 1-second window: aggregate += Δ_window. Direct reads of GET "
            "counter:id:total are O(1). On cold cache miss, fall back to SUM(shard values) from Redis "
            "directly; if Redis is down, the SoR has the last-window value. The aggregate key has no "
            "TTL for hot counters and a 1-day TTL for cold counters — the cold tail evicts and is "
            "recomputed from the SoR on next read. Write-through (rather than write-behind) keeps the "
            "read path within ~1 s of true value."
        ),
        "read_patterns_and_tail_latency": (
            "Reads vastly outnumber writes (50M:10M). Three classes: (1) Single-counter read (tweet "
            "detail page) — Redis GET, ~200 µs. (2) Batch read (timeline of 200 tweets) — pipelined "
            "MGET, ~2 ms total. (3) Real-time counter widget (auto-refresh on a viral tweet) — push via "
            "websocket every 1 s; one read per second per viewer regardless of UI poll rate. Edge-cache "
            "the public ultra-hot counters at the CDN with 1-second TTL; 99% of reads of a viral "
            "tweet's like count never touch the origin. Tail latency is bounded by the slowest of "
            "(N shard reads || cached aggregate); cap N at 1000 and make the aggregate key authoritative."
        ),
        "cardinality_and_storage": (
            "10B counters × ~50 B/counter (id + value + meta + shard_count) ≈ 500 GB cold storage — "
            "trivial in Cassandra. The hot subset (≤0.001%) lives in Redis at ~1 KB/counter (sharded "
            "values + aggregate + dedup); 100 GB cluster easily covers the full hot working set. HLL "
            "counters: 10M unique-cardinality counters × 12 KB ≈ 120 GB Redis — sized as a separate "
            "cluster. Rate-limit counters: short-lived, billions of windows per day but with TTL ≤ 1 hr; "
            "Redis EXPIRE keeps the working set bounded to the active window count (~100M, ~10 GB)."
        ),
        "ttl_for_transient_counters": (
            "Rate limiters and rolling-window analytics use counters with explicit TTL. Pattern: "
            "counter_id = 'rate:user42:1714312345' where the suffix is the 1-second bucket; on "
            "increment, INCR + EXPIRE 60. The bucket auto-expires; reads sum the last N buckets "
            "(sliding window). Approximate sliding window: weighted blend of current bucket and "
            "previous bucket (count_now × elapsed_in_now/window + count_prev × (1 - elapsed_in_now/window)) "
            "— one-bucket storage, ≤1% error. Fixed-window (e.g. hourly login attempts) uses a single "
            "bucket with TTL = window. TTL accuracy depends on Redis's lazy + active expiration; for "
            "tight bounds use volatile-lru maxmemory + active expiration with high frequency."
        ),
        "examples": (
            "Tweet view count: exact additive, sharded across N=100 sub-counters when viral; Kafka → "
            "Cassandra UPDATE; CDN-cached aggregate for read fan-out. Like button: same as views but "
            "supports DECR (unlike); dedup_key = (user_id, tweet_id) so the like is idempotent across "
            "client retries and cannot double-count. Unique viewers per video: HLL counter, ADD "
            "viewer_id on every play, ESTIMATE for the public number. Rate limiter (login attempts/min/IP): "
            "TTL counter, INCR + EXPIRE 60, reject when value > threshold. Follower count: exact, "
            "sharded only for celebrity accounts (>1M followers gain/sec during a viral moment); also "
            "a 'feed fan-out' problem if delivery matters, but the counter itself is just a number."
        ),
        "slo_contract": (
            "INCR p99 < 20 ms ack (Redis HINCRBY + Kafka produce ack). GET p99 < 50 ms intra-region. "
            "Eventual consistency: aggregate matches the actual sum within 5 s under steady load, 60 s "
            "under window-aggregator backpressure. Lost-increment rate < 1e-9 (Kafka durability + dedup). "
            "HLL relative error ≤ 1.5%. TTL counter expiry within ±1 s of nominal."
        ),
    },
    trade_offs=[
        {"option": "Single counter row vs sharded sub-counters",
         "for_single": "Reads are O(1) GET; trivial implementation; right for cold counters",
         "for_sharded": "Absorbs 1M+ writes/sec on a hot key; reads scale to N parallel gets",
         "recommendation": "Adaptive: N=1 for cold, auto-promote to N=100–1000 on QPS threshold."},
        {"option": "Exact counts vs HyperLogLog for unique-cardinality",
         "for_exact": "True count, supports membership queries, simple semantics",
         "for_hll": "12 KB regardless of cardinality, mergeable across regions, ±0.81% error",
         "recommendation": "Exact for likes/views/payments; HLL for unique-visitor / distinct-cardinality."},
        {"option": "Synchronous DB UPDATE vs Kafka windowed aggregation",
         "for_sync_db": "Single source of truth; immediate persistence; row-level row contention is the price",
         "for_kafka": "10M writes/sec → 10k DB writes/sec; replayable; survives DB outage",
         "recommendation": "Kafka windowed for hot counters; sync DB acceptable for low-QPS tail."},
        {"option": "Fail-open vs fail-closed on dedup-store failure",
         "for_fail_open": "Counters keep moving; rare double-count",
         "for_fail_closed": "No double-count; counters stall under dedup outage",
         "recommendation": "Fail-open for likes/views/follower counts; fail-closed only if double-count is catastrophic."},
        {"option": "Redis-only state vs Kafka + DB durability",
         "for_redis_only": "Cheapest, fastest; rebuild from upstream signal on loss",
         "for_durable": "Survives full Redis cluster loss without rebuilding from app traffic",
         "recommendation": "Durable for counters that drive UX (visible numbers); Redis-only for ephemeral rate-limits."},
    ],
    tips=[
        "Lead with the hot-key problem. Every other detail follows from 'one viral counter at 1M QPS.'",
        "Name 'sharded counter pattern' explicitly — it's the canonical answer and senior interviewers listen for it.",
        "Distinguish exact (likes) from approximate (unique viewers). Conflating them is the most common junior mistake.",
        "Idempotence ≠ INCR. Spell out the dedup_key + SETNX flow; 'INCR is idempotent' is wrong and disqualifying.",
        "Show the two-layer write: Redis HINCRBY for speed + Kafka for durability + DB UPDATE for consolidation.",
        "Quote concrete numbers: 1024 Kafka partitions, 16384 HLL registers, 12 KB per HLL, 100–1000 sub-counters.",
        "Mention TTL counters as a separate regime (rate limiters); junior candidates lump them with normal counters.",
    ],
    thought_process=[
        "1. Clarify: counters at scale; hot keys are the dominant constraint; eventual consistency on reads is fine.",
        "2. Estimate: 10B counters, 10M increments/sec, 1M+ on a single hot counter, 50M reads/sec.",
        "3. APIs: INCR, DECR, GET, GET_BATCH, ADD_UNIQUE (HLL), TTL counters.",
        "4. Hot-key problem first: explain why naive INCR on one row collapses at 1M QPS.",
        "5. Sharded counter pattern: random sub-counter on write, SUM on read; N adaptive 1 → 1000.",
        "6. Idempotence: client dedup_key + Redis SETNX with 5-min TTL.",
        "7. Two-layer write: Redis HINCRBY (live aggregate) + Kafka publish (durability).",
        "8. Aggregation pipeline: Flink 1-sec tumbling windows → DB UPDATE counter_value SET value += Δ.",
        "9. Approximate counters: HyperLogLog for unique-cardinality; 12 KB sketch, ±0.81% error.",
        "10. Read path: cached aggregate (write-through) + edge CDN for ultra-hot public counters.",
        "11. TTL counters: rate limiters with EXPIRE; sliding-window approximation by weighted blend.",
        "12. Failure: Redis loss → rebuild from Kafka replay; Kafka loss → DB is the floor; DB loss → Redis carries reads.",
    ],
    tags=["counter", "distributed", "hot-key", "sharding", "kafka", "hyperloglog", "rate-limit"],
    arch_nodes=[
        {"id": "client", "label": "Client / App", "type": "client"},
        {"id": "lb", "label": "API Gateway", "type": "lb"},
        {"id": "ingest", "label": "Ingest Service", "type": "server"},
        {"id": "dedup", "label": "Dedup Store (Redis)", "type": "cache"},
        {"id": "redis", "label": "Counter Cache (Redis)", "type": "cache"},
        {"id": "kafka", "label": "Kafka Increment Topic", "type": "queue"},
        {"id": "agg", "label": "Aggregator (Flink)", "type": "service"},
        {"id": "db", "label": "Counter SoR (Cassandra)", "type": "database"},
        {"id": "hll", "label": "HLL Service", "type": "service"},
        {"id": "hot", "label": "Hot-Counter Detector", "type": "service"},
        {"id": "cdn", "label": "Edge CDN", "type": "cache"},
    ],
    arch_edges=[
        {"source": "client", "target": "lb", "label": "INCR / GET"},
        {"source": "lb", "target": "ingest"},
        {"source": "ingest", "target": "dedup", "label": "SETNX dedup_key"},
        {"source": "ingest", "target": "redis", "label": "HINCRBY shard_idx"},
        {"source": "ingest", "target": "kafka", "label": "publish increment"},
        {"source": "kafka", "target": "agg", "label": "consume"},
        {"source": "agg", "target": "db", "label": "UPDATE value += Δ (1s window)"},
        {"source": "agg", "target": "redis", "label": "write-through aggregate"},
        {"source": "client", "target": "cdn", "label": "GET (public counters)"},
        {"source": "cdn", "target": "redis", "label": "origin miss"},
        {"source": "ingest", "target": "hll", "label": "ADD member"},
        {"source": "hot", "target": "redis", "label": "promote shard_count"},
        {"source": "redis", "target": "hot", "label": "sample QPS"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant App\n"
        "  participant API as API Gateway\n"
        "  participant I as Ingest\n"
        "  participant D as Dedup\n"
        "  participant R as Redis (sub-counters)\n"
        "  participant K as Kafka\n"
        "  participant A as Aggregator\n"
        "  participant DB as Cassandra\n"
        "  App->>API: POST /counters/{id}/incr (dedup_key)\n"
        "  API->>I: forward\n"
        "  I->>D: SETNX dedup:{id}:{key} EX 300\n"
        "  alt duplicate\n"
        "    D-->>I: 0 (exists)\n"
        "    I-->>App: 200 (no-op)\n"
        "  else fresh\n"
        "    D-->>I: 1 (set)\n"
        "    I->>I: shard_idx = rand(0, shard_count)\n"
        "    I->>R: HINCRBY counter:{id} {shard_idx} 1\n"
        "    I->>K: produce(counter_id, +1)\n"
        "    I-->>App: 200 OK\n"
        "  end\n"
        "  K->>A: stream\n"
        "  A->>A: 1-sec window: sum Δ per counter_id\n"
        "  A->>DB: UPDATE counter_value SET value=value+Δ\n"
        "  A->>R: SET counter:{id}:total value\n"
        "  Note over R: GET counter:{id}:total → cached aggregate"
    ),
    er_diagram=(
        "erDiagram\n"
        "  COUNTER_META ||--o{ COUNTER_VALUE : has\n"
        "  COUNTER_META ||--o| COUNTER_HLL : optional\n"
        "  COUNTER_META ||--o{ DEDUP_KEY : guards\n"
        "  COUNTER_META ||--o| RATE_LIMIT : optional\n"
        "  COUNTER_VALUE { string counter_id\n int shard_idx\n bigint value }\n"
        "  COUNTER_HLL { string counter_id\n bytes registers\n bigint estimate }\n"
        "  DEDUP_KEY { string counter_id\n string dedup_key\n bigint applied_at }\n"
        "  RATE_LIMIT { string counter_id\n int value\n bigint expire_at }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B[Hot key is THE problem]\n"
        "  B --> C{Counter kind?}\n"
        "  C -->|Exact additive| D[Sharded sub-counters]\n"
        "  C -->|Unique cardinality| E[HyperLogLog 12 KB]\n"
        "  C -->|TTL/rate-limit| F[Redis EXPIRE]\n"
        "  D --> G[Random shard_idx on INCR]\n"
        "  G --> H[Dedup_key SETNX 5 min]\n"
        "  H --> I[Redis HINCRBY → fast ack]\n"
        "  I --> J[Kafka publish → durability]\n"
        "  J --> K[1-sec window aggregator]\n"
        "  K --> L[DB UPDATE value += Δ]\n"
        "  K --> M[Write-through aggregate to cache]\n"
        "  M --> N[Reads: GET cached aggregate]\n"
        "  N --> O{Hot counter?}\n"
        "  O -->|yes| P[CDN edge cache 1s TTL]\n"
        "  O -->|no| Q[Direct Redis read]"
    ),
    tradeoff_title="Sharding strategy and consistency model",
    tradeoff_options=[
        {"label": "Single row, synchronous DB UPDATE",
         "description": "One counter_value row per counter; every INCR is a SET value=value+1 in the SoR.",
         "pros": ["Strong consistency (read sees own write)",
                 "Simplest data model",
                 "Right for low-QPS, audit-critical counters"],
         "cons": ["Row contention collapses at >5k writes/sec/counter",
                 "Hot-key tweet → DB partition meltdown",
                 "Latency 1–5 ms per INCR — eats the user's budget"]},
        {"label": "Sharded sub-counters in Redis + Kafka + DB rollup (recommended)",
         "description": "Random shard_idx per INCR; HINCRBY in Redis; Kafka durably logs; aggregator folds into DB.",
         "pros": ["Absorbs 1M+ writes/sec/counter via N=1000 sub-counters",
                 "≤1 ms write ack from Redis",
                 "DB sees ~1 update/counter/sec post-aggregation",
                 "Replayable from Kafka after Redis loss"],
         "cons": ["Eventual consistency: reads lag writes by ~1 s",
                 "Reads cost N gets unless aggregate is cached",
                 "Operational complexity: 4 components on the write path"]},
        {"label": "Pure Redis, no DB durability",
         "description": "Sharded sub-counters in Redis; AOF for crash recovery; no Kafka, no DB.",
         "pros": ["Simplest hot-path (1 component)",
                 "Sub-ms latency end-to-end",
                 "Right for ephemeral rate-limit counters with TTL"],
         "cons": ["AOF loss bound (≤1 s) is not 'no lost increments'",
                 "No cross-region durable replication story",
                 "Cluster loss = full counter wipe"]},
    ],
    tradeoff_rec=(
        "Sharded sub-counters + Kafka + DB rollup as the default for counters whose values appear in UX "
        "(likes, views, followers). Pure Redis acceptable only for ephemeral counters that can be rebuilt "
        "from upstream signal (rate-limit windows, transient analytics). Single-row synchronous DB only "
        "for low-QPS counters where strict read-your-write matters more than throughput; auto-promote to "
        "sharded when the QPS detector flags the counter as hot."
    ),
    senior_topics=[
        _topic("hot-key-sharded-counter",
               "The Hot-Key Problem and the Sharded Counter Pattern",
               "Why one viral tweet breaks every naive counter design, and how partitioning a single "
               "logical counter across N sub-counters trades a constant-factor read cost for unbounded "
               "write scalability.",
               [
                   ("Failure mode of the naive design",
                    "counter_value(counter_id PK, value BIGINT). INCR = UPDATE SET value=value+1 WHERE id=X. "
                    "Row-level lock on a single row serialises all increments cluster-wide; throughput is "
                    "capped at the slowest of (network RTT, lock acquire, log write) — typically 5–10k "
                    "ops/sec/row. A viral tweet at 1M ops/sec backs up; clients time out; retries amplify "
                    "the storm; the partition holding the row goes red."),
                   ("Sharded counter pattern",
                    "Replace one row with N rows: counter_value(counter_id, shard_idx, value) PK "
                    "(counter_id, shard_idx). On INCR, shard_idx = random(0, N-1). On READ, "
                    "SUM(value) GROUP BY counter_id. With N=1000, contention is divided by 1000; one "
                    "Redis instance holding 1000 sub-counters of one viral tweet sees 1k ops/sec/cell — "
                    "well within budget."),
                   ("Choosing N adaptively",
                    "Cold counters (99.99% of them) keep N=1; the read cost is one GET. The hot-counter "
                    "detector samples per-counter QPS via count-min sketch; when QPS exceeds a threshold "
                    "(e.g. 10× per-shard mean), it broadcasts shard_count = 100 to clients. If QPS keeps "
                    "climbing, promote to 1000. Demotion is hysteretic — wait until QPS stays below a "
                    "lower threshold for minutes to avoid flapping. shard_count change is a metadata-only "
                    "operation: existing sub-counters keep their values; new writes simply pick from a "
                    "wider range."),
                   ("Read amplification and the cached aggregate",
                    "Naive sharded read = N gets (1000 round trips for a hot counter). The Kafka "
                    "aggregator mitigates this by maintaining a single 'aggregate' key updated each "
                    "1-second window; reads hit the aggregate (1 GET) and fall back to SUM only on cache "
                    "miss. The aggregate lags by ~1 s, which is exactly the eventual-consistency budget "
                    "the spec allows."),
                   ("Why it generalises",
                    "Any monotonically-aggregable operation (SUM, COUNT, MIN, MAX) works under the same "
                    "pattern. Average is SUM/COUNT — store both. Median doesn't (use t-digest instead). "
                    "Distinct-count needs HLL. The pattern's domain is exactly: 'commutative, associative, "
                    "scalar reduction over a stream of small updates with one logical aggregation key.'"),
               ],
               diagram=(
                   "graph LR\n"
                   "  W1[writer] --> P[pick shard_idx = rand]\n"
                   "  W2[writer] --> P\n"
                   "  W3[writer] --> P\n"
                   "  P --> S0[shard_0]\n"
                   "  P --> S1[shard_1]\n"
                   "  P --> SN[shard_N-1]\n"
                   "  S0 --> SUM[SUM on read]\n"
                   "  S1 --> SUM\n"
                   "  SN --> SUM\n"
                   "  SUM --> AGG[cached aggregate key]\n"
                   "  R[reader] --> AGG"
               )),
        _topic("hyperloglog",
               "HyperLogLog for Unique-Cardinality Counters",
               "A 12 KB probabilistic sketch that estimates the number of distinct elements in a stream "
               "with ±0.81% error, regardless of whether the true cardinality is 100 or 10 billion. "
               "Mergeable across regions and shards.",
               [
                   ("The problem with exact unique-counts",
                    "Counting distinct viewers of a video exactly requires storing every viewer_id (or a "
                    "Bloom filter of them) — O(unique_users) memory per counter. For 10B videos × millions "
                    "of viewers each, that's exabytes. Set-membership stores (Redis SETs, Postgres bitmap "
                    "indexes) all share this scaling wall."),
                   ("HLL intuition",
                    "Hash each member to a 64-bit value. The first p=14 bits choose one of 2^14 = 16384 "
                    "registers. The remaining bits are scanned for the position of the leading 1; if a "
                    "stream has hashes with leading-zero runs of length k, the cardinality is roughly 2^k. "
                    "Each register tracks the max leading-zero-run seen for hashes routed to it. The "
                    "harmonic mean across registers, with a bias-correction constant, estimates "
                    "cardinality. 6 bits per register × 16384 registers = 12 KB."),
                   ("Operations",
                    "ADD(member): h = hash(member); idx = h[0..14]; lz = leading_zeros(h[14..]); "
                    "registers[idx] = max(registers[idx], lz+1). ESTIMATE: harmonic_mean(registers) × "
                    "α_m × m^2 with small/large-cardinality bias correction. MERGE(a, b): "
                    "out[i] = max(a[i], b[i]) — register-wise. Merge enables cross-region rollup: each "
                    "region maintains its own sketch; periodic union gives a global estimate."),
                   ("Accuracy and limits",
                    "Standard relative error = 1.04 / sqrt(m) ≈ 0.81% for m=16384. ±0.81% on 1M = ±8100, "
                    "which is acceptable for view counters but wrong for billing. HLL CANNOT answer "
                    "membership ('did user X view this?'); use a Bloom filter alongside for that. "
                    "Cannot decrement; if removal matters, use HLL+ or move to exact set storage."),
                   ("Operational notes",
                    "Redis ships PFADD / PFCOUNT / PFMERGE natively; underlying registers are 12 KB. "
                    "For very small cardinalities (<1000) pure HLL is biased; production implementations "
                    "transparently use a sparse representation (raw hash list) until promotion to dense "
                    "registers. Snapshot HLL state to durable storage periodically — same pattern as the "
                    "exact counter aggregator."),
               ],
               diagram=(
                   "graph LR\n"
                   "  M[member] --> H[hash 64-bit]\n"
                   "  H --> P[idx = h[0..14]]\n"
                   "  H --> Z[lz = leading_zeros(h[14..])]\n"
                   "  P --> R[registers[idx]]\n"
                   "  Z --> R\n"
                   "  R --> E[ESTIMATE = harmonic_mean × α × m²]\n"
                   "  R1[region A sketch] --> MG[MERGE = register-wise max]\n"
                   "  R2[region B sketch] --> MG\n"
                   "  MG --> EG[global estimate]"
               )),
        _topic("idempotence-dedup",
               "Idempotence: Why INCR Is Not Enough and How dedup_keys Work",
               "Every counter increment crosses an unreliable network. Clients retry. Without explicit "
               "deduplication the counter overcounts. The fix is a client-supplied key checked against a "
               "sliding-window store before the increment is applied.",
               [
                   ("The retry problem",
                    "Client POSTs INCR. Server applies it. Network drops the response. Client retries. "
                    "Server applies it again. The user clicked Like once; the counter went up twice. At "
                    "1% retry rate × 1M likes/sec, that's 10k spurious increments/sec on a single tweet."),
                   ("Why 'INCR is idempotent' is wrong",
                    "INCR is COMMUTATIVE (order doesn't matter) but not IDEMPOTENT (multiplicity does). "
                    "f(f(x)) ≠ f(x); applying INCR twice is different from applying it once. The mistake "
                    "is conflating Redis's atomic INCR (no torn writes within one command) with "
                    "end-to-end exactly-once semantics across retries. Atomic ≠ idempotent."),
                   ("Dedup key flow",
                    "Client generates a UUID per logical action (user clicks Like → one UUID for all "
                    "retries of that click). Server first runs SET NX dedup:{counter_id}:{uuid} EX 300 "
                    "against Redis; if the SETNX returns 0 (key exists), the increment is silently "
                    "dropped — this retry has been seen. If 1, proceed with the actual INCR. The "
                    "SETNX-then-INCR sequence is logically a CAS: 'if not seen, apply.'"),
                   ("Window sizing",
                    "Window must exceed the retry horizon. Aggressive client retries (5–30 s) and "
                    "occasional very-late retries (TCP RTO + DNS flap, ~1 min) → 5 minutes is the safe "
                    "default. 10B daily increments × 5-min window × ~5% concurrent → 100M dedup keys "
                    "× 32 B ≈ 3 GB; cluster-sized comfortably."),
                   ("Failure modes and fail-open vs fail-closed",
                    "Dedup store down → choose. FAIL-OPEN: skip the dedup check, apply the increment, "
                    "accept rare double-counts. Right for likes/views (undercounting > rare double-count). "
                    "FAIL-CLOSED: reject the increment, force client retry. Right when double-count is "
                    "catastrophic (rare in counters; if you have one, you probably want a real "
                    "transactional system not a counter service)."),
                   ("Composability with at-least-once Kafka",
                    "Kafka producers retry on network errors and may publish the same increment twice. "
                    "The aggregator MUST de-duplicate against (counter_id, dedup_key) within its window — "
                    "Kafka's Idempotent Producer handles per-partition session-level dedup but NOT cross-"
                    "session. Carry the dedup_key into the Kafka message and have the aggregator filter "
                    "duplicates from its windowed state."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant C as Client\n"
                   "  participant I as Ingest\n"
                   "  participant D as Dedup\n"
                   "  participant R as Redis\n"
                   "  C->>I: INCR (dedup=u1)\n"
                   "  I->>D: SETNX dedup:t:u1\n"
                   "  D-->>I: 1 (fresh)\n"
                   "  I->>R: HINCRBY counter:t shard\n"
                   "  I-->>C: 200\n"
                   "  Note over C: response lost\n"
                   "  C->>I: INCR (dedup=u1) [retry]\n"
                   "  I->>D: SETNX dedup:t:u1\n"
                   "  D-->>I: 0 (exists)\n"
                   "  I-->>C: 200 (no-op)"
               )),
        _topic("kafka-aggregation-pipeline",
               "Kafka + Stream Aggregation: From 10M Writes/Sec to 10k DB Writes/Sec",
               "How a tumbling-window stream processor flattens internet-scale write storms into "
               "human-scale durable updates, while remaining replayable for disaster recovery.",
               [
                   ("Why aggregate at all",
                    "Cassandra counter columns (or Spanner row-update with monotonic +1) cap at "
                    "~5k writes/sec/partition. 10M raw increments/sec would require 2000 partitions just "
                    "for the hot keys, and Cassandra partition splits during a viral spike are operationally "
                    "painful. Aggregation in front of the SoR collapses N updates into 1: write the SUM "
                    "every second, not every increment."),
                   ("Topic design",
                    "One topic 'counter.increments' with 1024 partitions. Producer key = counter_id, so "
                    "all increments for one counter land on the same partition (in-order). Retention "
                    "≥ 24 h to support replay after aggregator outage. Compression (zstd) and batching "
                    "(linger.ms=5, batch.size=1MB) cut bandwidth ~10×."),
                   ("Aggregator: 1-second tumbling windows",
                    "Flink job keyed by counter_id, tumbling window of 1 second, fold(delta) → window "
                    "sum. On window close, emit (counter_id, Σ delta). Sink: UPSERT counter_value "
                    "(counter_id, shard_idx, value) SET value = value + Σ — Cassandra counter column "
                    "or Spanner DML. With 10M ops/sec → 10M increments → 1M unique counters in the "
                    "window → 1M DB updates/sec, aggregated from 10M raw events. For sub-counter sharding, "
                    "key by (counter_id, shard_idx); same logic."),
                   ("Late events and watermarks",
                    "Consumer lag and clock skew mean some events arrive after the window closes. Flink's "
                    "watermark mechanism allows a small lateness tolerance (e.g. 30 s) — late events "
                    "belong to a side output and are merged into the next window's update. Beyond 30 s, "
                    "events are dropped and surfaced to monitoring; the aggregator's checkpoint preserves "
                    "exactly-once semantics within the watermark."),
                   ("Replay for recovery",
                    "Kafka retention is the disaster-recovery story. If the cache or even the SoR is "
                    "lost, reset the consumer offset to N hours ago and replay; the aggregator rebuilds "
                    "every counter's last-N-hour delta. For counters whose absolute value also lives in "
                    "the SoR, the rebuild is O(replay_window) — typically minutes to hours, not days. "
                    "This is why Kafka durability is the load-bearing piece, not the SoR alone."),
                   ("Backpressure and SLOs",
                    "Aggregator falls behind → window closures lag → cache aggregate is stale → reads "
                    "see older values. The SLO 'eventual consistency within 5 s' implicitly bounds "
                    "consumer lag. Alarm at lag > 30 s; auto-scale aggregator workers; rebalance Kafka "
                    "partitions if a single hot partition is overloading one worker. The hot-key "
                    "detector also informs aggregator partition assignment."),
               ],
               diagram=(
                   "graph LR\n"
                   "  I[Ingest] --> K[Kafka topic 1024p]\n"
                   "  K --> F[Flink keyed by counter_id]\n"
                   "  F --> W[1-sec tumbling window]\n"
                   "  W --> S[Σ delta per window]\n"
                   "  S --> DB[Cassandra UPDATE value+=Σ]\n"
                   "  S --> R[Redis SET aggregate]\n"
                   "  W -. late >30s .-> SO[side output]\n"
                   "  SO --> ALERT[monitoring]\n"
                   "  K -. replay .-> F"
               )),
        _topic("rate-limit-counters-ttl",
               "TTL Counters and Rate-Limiting: Sliding Windows on a Budget",
               "Rate limiters are counters with a deadline. The data structure is the same; the "
               "operational profile is very different — high churn, small values, strict expiry, and a "
               "decision is made on every increment.",
               [
                   ("Fixed-window counter",
                    "counter_id = 'rate:user42:hour:2026042814'; bucket suffix is the window. INCR + "
                    "EXPIRE 3600. Rejection check: if INCR returns > threshold, return 429. Simple, "
                    "cheap, but suffers boundary effects: 100 requests in the last second of one window "
                    "and 100 in the first second of the next allows 200 in 2 s on a nominally "
                    "100/hour limit."),
                   ("Sliding-window log",
                    "Store every request timestamp in a sorted set (ZADD with score=ts). Trim entries "
                    "older than now-window. Count = ZCARD. Exact, fair, but O(window × QPS) memory per "
                    "user — prohibitive for fine-grained limits like 10000 ops/min."),
                   ("Sliding-window approximation (recommended)",
                    "Two adjacent fixed-window buckets. Estimate = count[curr] + count[prev] × "
                    "(1 - elapsed_in_curr/window). Updates one bucket; reads two. Memory: 2 keys/user "
                    "instead of N. Error bounded by ≤1% under uniform traffic; up to ~9% under "
                    "adversarial bursts. Right answer for ~99% of rate-limit use cases."),
                   ("Token bucket for burst-tolerant limits",
                    "Pair (tokens, last_refill_ms) per user. On each request, refill tokens by "
                    "(now - last_refill) × rate, cap at burst_size, decrement, reject if < 0. Lua script "
                    "in Redis makes this atomic. Allows controlled bursts (queue-depth) on top of "
                    "average-rate limits — the right semantics for API gateways."),
                   ("Distributed coordination",
                    "Per-region Redis is fine for per-region limits. Global limits ('1M API calls/sec "
                    "across the world for free tier') are harder: cross-region replication lag means "
                    "counts are stale; the practical answer is per-region quota allocation with "
                    "occasional rebalancing — not real-time global consensus. Hierarchical limits "
                    "(per-user-per-region + global rollup with HLL-style merge) are the senior signal."),
                   ("TTL and storage hygiene",
                    "Rate-limit keys churn fast: billions of unique window keys per day, all with "
                    "≤1 hour TTL. Redis volatile-LRU + active expiration keeps the working set bounded "
                    "to the active window count (~100M keys at any moment, ~10 GB cluster). Don't "
                    "forget: TTL keys touched by INCR get their TTL reset only with explicit EXPIRE — "
                    "INCR alone preserves the existing TTL, which is the desired behaviour."),
               ],
               diagram=(
                   "graph TD\n"
                   "  Q[request] --> B{which window?}\n"
                   "  B -->|fixed| F[INCR rate:user:hour]\n"
                   "  F --> CK{> limit?}\n"
                   "  CK -->|yes| R[429]\n"
                   "  CK -->|no| OK[allow]\n"
                   "  B -->|sliding| S[curr+prev × 1-elapsed/window]\n"
                   "  B -->|burst| T[token bucket Lua]\n"
                   "  T --> CK\n"
                   "  S --> CK\n"
                   "  F -. EXPIRE 3600 .-> EXP[auto-cleanup]"
               )),
    ],
)
