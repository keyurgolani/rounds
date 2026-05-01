"""SD-Typeahead — Design Search Autocomplete (Typeahead). Mirrors the
schema/shape of SD_01 in sd_questions.py. Auto-discovered by
`sd_questions._load_more` because this module exposes `PAYLOAD`."""
from __future__ import annotations

from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design Search Autocomplete (Typeahead)",
    "Medium",
    "Design a search autocomplete (typeahead) service that suggests the top-K relevant completions "
    "as the user types each character into a search box. Suggestions must be ranked by frequency, "
    "personalization, and recency, and arrive within tens of milliseconds end-to-end. Cover the trie "
    "data structure with precomputed top-K at each node, offline rank-build pipeline from query logs, "
    "personalization via user history and location, fuzzy/typo-tolerant matching, sharding by prefix, "
    "edge caching of common prefixes, incremental updates vs periodic rebuilds, evergreen ranking "
    "with time decay and surge detection, and privacy/sanitization of query logs.",
    hints=[
        "Read-heavy by 100:1 — every keystroke is a query. Optimize the read path first.",
        "Latency target is the design constraint: p99 < 100ms end-to-end, ideally sub-50ms.",
        "Don't recompute top-K per request — precompute and cache top-K at every trie node.",
        "Building the trie is offline; serving the trie is online. Decouple the two.",
        "Personalization is a re-rank on top of a global top-K, not a separate index per user.",
        "Fuzzy match is the fallback when the prefix has no high-quality completions, not the default.",
        "Trending/surge detection requires fast incremental update path; full rebuilds happen daily.",
    ],
    constraints=[
        "Suggestions returned per keystroke — every character typed",
        "Latency budget: p99 < 100ms end-to-end (sub-50ms ideal)",
        "100M+ DAU; 10+ keystrokes per search session × billions of searches/day",
        "Top-K per query usually 5–10 suggestions",
        "Index size: ~10–100M unique queries; trie fits per-shard in RAM",
        "Privacy: query logs cannot retain raw PII; sanitize before ranking pipeline",
        "Multi-locale: separate ranking per language/region",
    ],
    req_func=[
        "Return top-K completions for a given prefix",
        "Rank by frequency, recency, and personalization (user history, location)",
        "Tolerate typos via approximate / fuzzy matching when exact prefix is sparse",
        "Surface trending/recently surging queries",
        "Update suggestions as new queries are issued (incremental + periodic rebuilds)",
        "Suppress disallowed/abusive completions (banlist, low-quality, NSFW where required)",
    ],
    req_nonfunc=[
        "p99 end-to-end latency < 100ms; p50 < 30ms; sub-50ms p99 ideal in-region",
        "Read:write ratio ~100:1 — optimize read path; write path can be batch",
        "High availability — typeahead failure should degrade gracefully (return empty, never block)",
        "Eventual consistency for new queries is acceptable (minutes for incremental, hours for full rebuild)",
        "Index hot in RAM per shard; cold tail acceptable to fall back to slower path",
        "Cost-sensitive: edge cache + browser cache absorb most traffic",
        "Privacy: query logs sanitized; per-user data scoped and TTL-bounded",
    ],
    estimation={
        "dau": "100M",
        "searches_per_user_per_day": "5",
        "keystrokes_per_search": "~10",
        "qps_steady": "100M × 5 × 10 / 86400 ≈ 60K typeahead QPS avg; ~200K peak",
        "unique_queries_indexed": "~50M (head+torso); long tail truncated",
        "storage_trie_per_locale": "~1–4 GB compressed per locale (top-K embedded at nodes)",
        "log_volume_for_ranking": "~5B query events/day → ~500 GB/day raw",
        "edge_cache_hit_ratio": "~70–80% of keystrokes hit common prefixes",
    },
    endpoints=[
        {"method": "GET", "path": "/autocomplete",
         "description": "Return top-K suggestions for a prefix",
         "body": "query params: q (prefix), locale, k (default 10), user_token (optional)"},
        {"method": "POST", "path": "/events/query",
         "description": "Record an issued search query (fire-and-forget) for ranking pipeline",
         "body": "{user_id?, query, ts, locale, geo, session_id}"},
        {"method": "POST", "path": "/admin/banlist",
         "description": "Add/remove a phrase from the suppression list (admin)"},
        {"method": "POST", "path": "/admin/rebuild",
         "description": "Trigger an offline trie rebuild (admin)"},
    ],
    tables=[
        {"name": "query_events",
         "columns": ["event_id BIGINT PK", "user_id BIGINT NULL", "query VARCHAR(256)",
                     "locale VARCHAR(8)", "geo VARCHAR(8)", "ts BIGINT", "session_id VARCHAR(64)"]},
        {"name": "query_freq",
         "columns": ["query VARCHAR(256)", "locale VARCHAR(8)", "freq BIGINT",
                     "freq_decayed DOUBLE", "last_seen BIGINT",
                     "PRIMARY KEY (query, locale)"]},
        {"name": "user_history",
         "columns": ["user_id BIGINT", "query VARCHAR(256)", "ts BIGINT",
                     "PRIMARY KEY (user_id, query)"]},
        {"name": "banlist",
         "columns": ["phrase VARCHAR(256) PK", "locale VARCHAR(8)", "reason VARCHAR(64)",
                     "added_at BIGINT"]},
        {"name": "trie_snapshots",
         "columns": ["snapshot_id VARCHAR(32) PK", "locale VARCHAR(8)",
                     "built_at BIGINT", "s3_key VARCHAR(255)", "active BOOLEAN"]},
    ],
    indexes=[
        "(query, locale) on query_freq — rank lookups",
        "(user_id, ts DESC) on user_history — personalization",
        "(locale, freq_decayed DESC) on query_freq — top-K extraction during build",
        "(ts) on query_events — windowed aggregation for ranking",
    ],
    hld_desc=(
        "Two decoupled planes. Serving plane: client → edge cache → typeahead service → in-memory "
        "trie shard (sharded by prefix). Each trie node carries a precomputed top-K so a request is "
        "an O(prefix_len) descent + cached read. Personalization is a cheap re-rank merging the "
        "global top-K with the user's recent queries. Build plane: query events → Kafka → batch "
        "ranking pipeline (Spark/Flink) computes time-decayed frequencies, applies banlist, builds "
        "a fresh trie snapshot, and ships it to serving shards. Incremental update path streams "
        "high-velocity queries into a delta layer that the serving node merges on top of the base "
        "trie for trending/surge detection."
    ),
    hld_components=[
        {"name": "Edge Cache / CDN", "role": "Caches popular prefixes; serves most keystrokes"},
        {"name": "Typeahead API", "role": "Stateless front-end; routes to correct shard"},
        {"name": "Trie Shard", "role": "In-memory trie with precomputed top-K per node"},
        {"name": "Personalization Re-ranker", "role": "Merges user history + location into global top-K"},
        {"name": "Fuzzy Matcher", "role": "Edit-distance / n-gram fallback for sparse prefixes"},
        {"name": "Query Event Ingestor", "role": "Kafka producer for issued searches"},
        {"name": "Ranking Pipeline", "role": "Batch (daily) + stream (minute) frequency aggregation"},
        {"name": "Trie Builder", "role": "Builds top-K-embedded trie snapshots, ships to shards"},
        {"name": "Surge Detector", "role": "Flink job spotting recent surging queries"},
        {"name": "Banlist / Moderation", "role": "Suppresses disallowed completions"},
        {"name": "Sanitizer", "role": "Strips PII from query logs before ranking"},
    ],
    detailed_design={
        "trie_with_topk": (
            "Each trie node stores: edge label (character or compressed substring for radix-trie), "
            "children pointers, and a precomputed top-K list of {query, score} for the subtree rooted "
            "at this node. A request walks down the prefix in O(prefix_len) and returns the cached "
            "top-K directly — no on-the-fly aggregation. Top-K is small (10–20) so memory overhead "
            "is bounded; storing top-K at every node ~5–10× the raw trie but still single-digit GB "
            "per locale shard."
        ),
        "build_pipeline": (
            "Query events land in Kafka (sanitized: PII fields stripped, IP truncated, raw query "
            "tokenized and validated against banlist). Hourly stream job aggregates per-(query, locale) "
            "counts. Nightly batch job applies time decay (e.g., score = freq × exp(-age/τ) with τ ~ 7 "
            "days), prunes long-tail (< threshold), and emits ranked (query, score) pairs per locale. "
            "Trie builder reads the ranked set, constructs a radix trie, and at each node computes "
            "top-K for the subtree (bottom-up merge of children's top-Ks plus self). Snapshot "
            "serialised, written to object store, atomically swapped on shards via blue-green load."
        ),
        "sharding_strategy": (
            "Shard by prefix range (first 1–2 characters) or by hash of the first character / "
            "consistent hash on prefix. Prefix-range gives natural locality (one shard owns 'app*') "
            "but creates hot shards on common letters; hash spreads load but each request still hits "
            "exactly one shard since the prefix determines the route. We use a 2-char prefix range "
            "with split-on-load for hot ranges (e.g., 's*' splits into 'sa-sm', 'sn-sz'). Each shard "
            "loads only its slice of the trie into RAM."
        ),
        "personalization": (
            "After the global top-K is fetched, a fast re-ranker blends signals: user_history (last "
            "N queries with recency boost), location (geo-relevant queries from query_freq filtered "
            "by geo), and session context (queries from same session get downweighted to avoid "
            "showing what they just searched). Personalization signals live in a feature store keyed "
            "by user_id and read with the global call. Score: w1·global + w2·history + w3·geo + "
            "w4·session. Weights tuned offline. If user is anonymous, fall back to geo + session only."
        ),
        "fuzzy_matching": (
            "When the exact-prefix top-K is sparse (e.g., < K results or all low score), trigger a "
            "fuzzy fallback. Two techniques: (1) Edit-distance trie traversal — descend with a "
            "Levenshtein automaton allowing up to 1–2 edits, scoring matches by (edit_distance, freq). "
            "(2) N-gram inverted index for typo recovery on longer prefixes — bigrams of the prefix "
            "lookup candidate queries containing those n-grams, then re-rank. Fuzzy is more expensive; "
            "gate by prefix length ≥ 3 and fall back only when exact is sparse."
        ),
        "caching": (
            "Three cache layers. (1) Browser cache: client caches recent typeahead responses keyed "
            "by prefix for the session — instant for back-tracking. (2) Edge / CDN cache: short TTL "
            "(10–60s) keyed by (prefix, locale); absorbs ~70–80% of all keystrokes since common "
            "prefixes ('a', 'th', 'how to') dominate. Anonymous (non-personalized) responses only — "
            "personalized requests bypass edge. (3) In-memory result cache on the API node for hot "
            "prefixes inside the trie shard. Cache invalidated by snapshot version bump."
        ),
        "incremental_updates": (
            "Full rebuild happens nightly (and per-locale on schedule). Between rebuilds, a delta "
            "layer captures recent high-velocity queries from the surge detector and is merged on "
            "top of the static trie at request time (read-time merge, not write-time, since the "
            "delta is small). Delta layer is recomputed every minute from the Flink stream job. "
            "Surge detector flags a query as 'trending' when its recent-window rate exceeds its "
            "decayed long-term rate by N× (e.g., breaking-news queries)."
        ),
        "evergreen_ranking": (
            "Score = base_freq × time_decay + recency_boost − staleness_penalty. Time decay uses an "
            "exponential with τ tuned per locale (faster decay on news-heavy locales). Recency boost "
            "added for queries with rising velocity in the last hour. Staleness penalty applied to "
            "queries that haven't been seen in N days to keep the head fresh. Banned/disallowed "
            "queries scored to −∞ so they never surface."
        ),
        "privacy_sanitization": (
            "At ingest, strip identifying fields (precise IP, exact device id) and bucket geo to "
            "city level. Query strings scrubbed against a PII regex (emails, phones, SSN-shaped "
            "tokens) before persistence. user_history rows are TTL'd (e.g., 90–180 days) and gated "
            "by user consent. Aggregation pipeline operates only on sanitized events; raw logs in "
            "cold storage are encrypted-at-rest with restricted access. Per-region data residency "
            "honored — EU events ranked in EU pipelines."
        ),
        "slo_contract": (
            "Typeahead p99 < 100ms end-to-end (in-region p99 < 50ms). Availability 99.95% — failure "
            "returns empty list, never blocks the search box. Snapshot freshness: head queries < 24h, "
            "trending queries < 1min via delta layer. Personalization added latency budget < 10ms."
        ),
    },
    trade_offs=[
        {"option": "Trie with cached top-K vs on-the-fly aggregation",
         "for_cached": "O(prefix_len) read; constant work regardless of subtree size",
         "for_onthefly": "No precompute; index smaller; can incorporate fresh signals exactly",
         "recommendation": "Cached top-K — the 5–10× memory cost buys orders-of-magnitude latency savings."},
        {"option": "Sharding by prefix range vs hash of prefix",
         "for_range": "Locality; natural ordering; easy range scans for analytics",
         "for_hash": "Even load distribution; no hot shards on common letters",
         "recommendation": "Prefix range with split-on-load — locality + hot-range mitigation."},
        {"option": "Incremental updates vs periodic full rebuilds",
         "for_incremental": "Trending queries surface in minutes; no nightly compute spike",
         "for_full": "Simpler; deterministic snapshots; easier rollback",
         "recommendation": "Hybrid — full nightly rebuild + minute-level delta layer for surges."},
        {"option": "Personalize at index-build time vs at request time",
         "for_buildtime": "No request-time work; simple API",
         "for_requesttime": "Single global index; personalization is a cheap re-rank",
         "recommendation": "Request-time re-rank — building per-user indexes is intractable at 100M users."},
        {"option": "Fuzzy match always vs only on sparse prefixes",
         "for_always": "Resilient to any typo regardless of head/tail",
         "for_sparse_only": "Fuzzy is expensive; head prefixes always have rich exact results",
         "recommendation": "Fuzzy fallback only — exact-prefix top-K covers the common case."},
    ],
    tips=[
        "Lead with the latency budget (p99 < 100ms). It drives every decision.",
        "Naming 'precomputed top-K at each trie node' is a senior signal — most candidates aggregate at request time.",
        "Distinguish offline build from online serve. Don't propose live trie mutations on each query event.",
        "Edge cache on anonymous prefixes absorbs ~70% of traffic — call it out explicitly.",
        "Personalization = re-rank on top of global top-K, not a per-user index.",
        "Fuzzy matching is a fallback path, not the primary. Gate by prefix length and exact sparsity.",
        "Surge detection (delta layer) is what makes typeahead feel 'alive' for breaking-news queries.",
        "Mention privacy: PII scrubbing at ingest, TTL on user history, locale data residency.",
    ],
    thought_process=[
        "1. Clarify: every keystroke triggers a request; top-K=10; latency target sub-100ms p99.",
        "2. Estimate: 100M DAU × 5 searches × 10 keystrokes ≈ 60K avg / 200K peak QPS.",
        "3. Read:write ratio ~100:1 → optimize read path; build is offline.",
        "4. Data structure: radix trie with precomputed top-K at every node.",
        "5. Build pipeline: query events → Kafka → batch (decayed freq) → trie builder → ship snapshot.",
        "6. Sharding: by prefix range with split-on-load for hot ranges.",
        "7. Caching: browser → edge (anonymous) → API result cache → trie shard.",
        "8. Personalization: cheap request-time re-rank merging global top-K with user/geo signals.",
        "9. Fuzzy matching: edit-distance traversal as fallback for sparse prefixes.",
        "10. Trending: minute-level delta layer + surge detector merged at read time.",
        "11. Privacy: sanitize at ingest; TTL user history; locale-scoped pipelines.",
    ],
    tags=["search", "autocomplete", "trie", "ranking", "low-latency"],
    arch_nodes=[
        {"id": "client", "label": "Client (browser/app)", "type": "client"},
        {"id": "edge", "label": "Edge / CDN Cache", "type": "cache"},
        {"id": "api", "label": "Typeahead API", "type": "lb"},
        {"id": "trie", "label": "Trie Shard (in-mem)", "type": "server"},
        {"id": "personalize", "label": "Personalization Re-ranker", "type": "service"},
        {"id": "fuzzy", "label": "Fuzzy Matcher", "type": "service"},
        {"id": "feature", "label": "Feature Store", "type": "database"},
        {"id": "kafka", "label": "Kafka (query events)", "type": "service"},
        {"id": "stream", "label": "Stream Aggregator (Flink)", "type": "server"},
        {"id": "batch", "label": "Batch Ranker (Spark)", "type": "server"},
        {"id": "builder", "label": "Trie Builder", "type": "server"},
        {"id": "snapshot", "label": "Trie Snapshot Store", "type": "database"},
        {"id": "delta", "label": "Delta Layer (trending)", "type": "cache"},
        {"id": "surge", "label": "Surge Detector", "type": "service"},
        {"id": "banlist", "label": "Banlist / Moderation", "type": "service"},
        {"id": "sanitize", "label": "Sanitizer", "type": "service"},
    ],
    arch_edges=[
        {"source": "client", "target": "edge", "label": "GET /autocomplete?q="},
        {"source": "edge", "target": "api", "label": "miss"},
        {"source": "api", "target": "trie", "label": "prefix descent"},
        {"source": "trie", "target": "delta", "label": "merge trending"},
        {"source": "api", "target": "personalize", "label": "re-rank"},
        {"source": "personalize", "target": "feature", "label": "user/geo signals"},
        {"source": "api", "target": "fuzzy", "label": "fallback if sparse"},
        {"source": "client", "target": "kafka", "label": "issued query"},
        {"source": "kafka", "target": "sanitize"},
        {"source": "sanitize", "target": "stream"},
        {"source": "sanitize", "target": "batch"},
        {"source": "stream", "target": "surge"},
        {"source": "surge", "target": "delta", "label": "minute updates"},
        {"source": "batch", "target": "builder", "label": "ranked queries"},
        {"source": "banlist", "target": "builder", "label": "suppress"},
        {"source": "builder", "target": "snapshot"},
        {"source": "snapshot", "target": "trie", "label": "load + swap"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant U as User\n"
        "  participant C as Client\n"
        "  participant E as Edge Cache\n"
        "  participant API\n"
        "  participant T as Trie Shard\n"
        "  participant P as Personalizer\n"
        "  participant F as Feature Store\n"
        "  U->>C: types 'how t'\n"
        "  C->>E: GET /autocomplete?q=how t\n"
        "  alt cache hit (anonymous)\n"
        "    E-->>C: top-K\n"
        "  else miss\n"
        "    E->>API: forward\n"
        "    API->>T: descend('how t')\n"
        "    T-->>API: cached top-K + delta merge\n"
        "    API->>P: re-rank\n"
        "    P->>F: user history, geo\n"
        "    F-->>P: signals\n"
        "    P-->>API: blended top-K\n"
        "    API-->>E: 200 (short TTL)\n"
        "    E-->>C: top-K\n"
        "  end\n"
        "  C-->>U: render suggestions\n"
        "  U->>C: presses Enter on 'how to tie a tie'\n"
        "  C->>API: POST /events/query (fire-and-forget)\n"
    ),
    er_diagram=(
        "erDiagram\n"
        "  USER ||--o{ USER_HISTORY : has\n"
        "  QUERY_EVENT }o--|| QUERY_FREQ : aggregates_into\n"
        "  TRIE_SNAPSHOT ||--o{ QUERY_FREQ : built_from\n"
        "  BANLIST ||--o{ TRIE_SNAPSHOT : suppresses_in\n"
        "  QUERY_EVENT { bigint event_id\n bigint user_id\n string query\n string locale\n bigint ts }\n"
        "  QUERY_FREQ { string query\n string locale\n bigint freq\n double freq_decayed }\n"
        "  USER_HISTORY { bigint user_id\n string query\n bigint ts }\n"
        "  TRIE_SNAPSHOT { string snapshot_id\n string locale\n bigint built_at\n bool active }\n"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B{Latency target}\n"
        "  B -->|p99 < 100ms| C[Precompute top-K at trie nodes]\n"
        "  C --> D[Decouple offline build from online serve]\n"
        "  D --> E[Shard by prefix range with split-on-load]\n"
        "  E --> F[Edge cache anonymous prefixes]\n"
        "  F --> G[Personalization = request-time re-rank]\n"
        "  G --> H[Fuzzy = fallback when sparse]\n"
        "  H --> I[Delta layer for trending surges]\n"
        "  I --> J[Sanitize logs; TTL user history]\n"
    ),
    tradeoff_title="Periodic Full Rebuild vs Continuous Incremental Updates",
    tradeoff_options=[
        {"label": "Periodic full rebuild only (e.g., nightly)",
         "description": "All ranking aggregation done in a daily batch; trie snapshot rebuilt and "
                        "shipped wholesale; serving shards atomically swap to the new snapshot.",
         "pros": ["Simple — one pipeline, one snapshot artifact",
                  "Deterministic and easy to reason about / roll back",
                  "Cheap aggregation (one pass over the day's events)"],
         "cons": ["Trending/breaking-news queries take up to 24h to surface",
                  "Stale during news/event spikes",
                  "Nightly compute spike — capacity planning required"]},
        {"label": "Continuous incremental updates only",
         "description": "Stream pipeline updates per-query frequency in near-real-time; serving shards "
                        "mutate the trie online on each update.",
         "pros": ["Trending queries appear in seconds",
                  "Smooth load profile — no nightly spike"],
         "cons": ["Live mutation of an in-memory trie shared across requests is hard to do safely",
                  "Top-K cache at each node must be re-derived on every update along the path",
                  "Hard to roll back a bad update; no clean snapshot",
                  "Decay/dedup is harder than a daily batch can do"]},
        {"label": "Hybrid (recommended): full nightly rebuild + minute-level delta layer",
         "description": "Nightly batch produces an authoritative trie snapshot. A small read-only "
                        "delta layer, recomputed every minute from a Flink surge detector, is "
                        "merged on top of the static trie at request time for trending queries.",
         "pros": ["Trending freshness within ~1 min via delta",
                  "Authoritative head/torso ranking via nightly batch",
                  "Static base trie is immutable per-snapshot — easy to roll back",
                  "Read-time merge avoids unsafe live trie mutation"],
         "cons": ["Two pipelines to operate (batch + stream)",
                  "Read-time merge adds a few ms of latency",
                  "Dedup between base and delta needed when the same query exists in both"]},
    ],
    tradeoff_rec=(
        "Hybrid. Nightly full rebuild ships an immutable, top-K-embedded trie snapshot that serves "
        "the head and torso authoritatively. A minute-level delta layer driven by a surge detector "
        "captures trending queries and is merged at read time. This gives the freshness of "
        "incremental with the safety, ranking quality, and rollback story of periodic full rebuilds."
    ),
    senior_topics=[
        _topic("trie-with-topk",
               "Radix Trie with Precomputed Top-K at Each Node",
               "The senior pattern: every trie node carries the top-K best completions for its "
               "subtree, computed offline. A request becomes O(prefix_len) descent + cached read.",
               [
                   ("Why precompute top-K",
                    "Aggregating top-K from a subtree at request time is O(subtree_size · log K). "
                    "For prefixes near the root the subtree is huge — sub-100ms is impossible. "
                    "Precomputation moves that cost to the offline build."),
                   ("Storage cost",
                    "Top-K at every node is K × node_count entries. For K=10–20 and ~10M nodes per "
                    "locale, that's ~100–200M entries × ~32B each ≈ 3–6 GB per locale — fits in "
                    "RAM on a single shard."),
                   ("Bottom-up build",
                    "After the radix trie skeleton is built from ranked (query, score) pairs, do "
                    "a post-order traversal: for each node, merge its children's top-K lists with "
                    "any query that terminates at the node, keeping the K highest scores."),
                   ("Compression",
                    "Radix-trie compression (collapse single-child chains into substrings) cuts "
                    "node count 5–10× on natural language. Top-K dominates memory; compress trie "
                    "structure aggressively."),
                   ("Snapshot & swap",
                    "Each build produces an immutable serialized snapshot in object store. Serving "
                    "shards download and load into RAM, then atomically swap from old to new — "
                    "in-flight requests finish on the old snapshot, new requests use the new one."),
               ],
               diagram=(
                   "graph TD\n"
                   "  R[root] --> A[a]\n"
                   "  A --> AP[ap]\n"
                   "  AP --> APP[apple]\n"
                   "  AP --> APN[apnea]\n"
                   "  R -.topK=apple,amazon,...-.->R\n"
                   "  A -.topK=apple,amazon,airbnb-.->A\n"
                   "  AP -.topK=apple,apnea-.->AP\n"
               )),
        _topic("ranking-time-decay",
               "Evergreen Ranking with Time Decay and Surge Detection",
               "Raw frequency promotes evergreen queries forever and never surfaces breaking news. "
               "Combine exponential decay with a surge bonus to get a fresh, balanced head.",
               [
                   ("Exponential time decay",
                    "score = Σ_events exp(-(now - ts)/τ). τ tuned per locale (faster on news-heavy). "
                    "Implemented incrementally: maintain decayed_freq, on update "
                    "decayed_freq = decayed_freq · exp(-Δt/τ) + 1."),
                   ("Surge detection",
                    "Compare recent-window rate (last 10 min) to long-term decayed rate. If "
                    "recent_rate > N × long_term_rate (and absolute count exceeds a floor), tag the "
                    "query as 'surging' and inject into the delta layer with a recency bonus."),
                   ("Staleness pruning",
                    "Queries unseen for > N days are pruned from the trie at build time; tail-only "
                    "completions hurt latency and quality."),
                   ("Banlist & quality filters",
                    "Hardcoded banlist + low-quality classifier (NSFW, hate, spam). Applied at "
                    "build time so banned phrases never make the trie at all — defense in depth "
                    "vs request-time filtering alone."),
                   ("Localization",
                    "Separate ranking per (language, region). Same prefix has different top-K in "
                    "en-US vs en-IN. Locale routing happens at the API layer pre-shard."),
               ],
               diagram=(
                   "graph LR\n"
                   "  E[Query Events] --> S[Stream Aggregator]\n"
                   "  S --> R1[recent rate 10min]\n"
                   "  S --> L1[long-term decayed]\n"
                   "  R1 & L1 --> SU[surge detector]\n"
                   "  SU --> D[Delta Layer]\n"
                   "  E --> B[Batch Ranker]\n"
                   "  B --> TB[Trie Builder]\n"
                   "  TB --> SN[Snapshot]\n"
                   "  SN & D --> SH[Serving Shard]\n"
               )),
        _topic("personalization-rerank",
               "Personalization as Request-Time Re-rank",
               "Building a per-user index for 100M users is intractable. Instead, fetch a global "
               "top-K from the shared trie and blend with cheap per-user signals at request time.",
               [
                   ("Why not per-user index",
                    "A per-user trie at 100M scale is prohibitive in storage and build cost. "
                    "Personalization is a small re-rank on a global top-K, not a separate index."),
                   ("Signals blended in",
                    "user_history (last N issued queries with recency boost), location (geo-relevant "
                    "completions), session context (downweight items already seen this session), "
                    "device/locale, time-of-day."),
                   ("Linear scoring model",
                    "score = w1·global_score + w2·history_match + w3·geo_match + w4·session_signal. "
                    "Weights tuned offline against held-out clicks; periodic A/B re-tuning."),
                   ("Feature store",
                    "Per-user features cached in low-latency KV (Redis-class) keyed by user_id; "
                    "TTL-bounded for privacy. Read concurrent with the global trie read."),
                   ("Anonymous fallback",
                    "Anonymous users get geo + session re-rank only — and crucially, anonymous "
                    "responses are eligible for edge caching, dramatically improving hit rate."),
               ]),
        _topic("fuzzy-typo-tolerance",
               "Fuzzy Matching: Edit-Distance Trie + N-gram Fallback",
               "Exact-prefix top-K covers most cases; fuzzy is the safety net for typos and "
               "transposition. Two complementary techniques.",
               [
                   ("When to trigger fuzzy",
                    "Only when exact-prefix top-K is sparse (size < K or all scores low) AND "
                    "prefix length ≥ 3. Fuzzy is expensive — gate it tightly."),
                   ("Edit-distance trie traversal",
                    "Descend the trie with a Levenshtein automaton allowing up to 1–2 edits "
                    "(insertion, deletion, substitution, transposition). Score = α/(1+edits) × freq. "
                    "Bound traversal by max edits to keep cost predictable."),
                   ("N-gram inverted index",
                    "Build an inverted index from character n-grams (e.g., trigrams) to candidate "
                    "queries. For typo recovery on longer prefixes, lookup candidates by overlapping "
                    "n-grams of the prefix and re-rank."),
                   ("Hybrid",
                    "Edit-distance for short prefixes (≤ 8 chars), n-gram for longer where edit "
                    "automaton blows up. Both feed into the same re-ranker as the exact path."),
                   ("Caching fuzzy",
                    "Fuzzy results are deterministic per prefix → cache them in the API-node result "
                    "cache to amortize cost across repeated typos."),
               ]),
        _topic("sharding-and-cache-tiers",
               "Sharding by Prefix and Multi-Tier Caching",
               "Latency budget is met by absorbing most traffic before it ever hits the trie shard. "
               "Layered caches plus prefix sharding make the read path cheap.",
               [
                   ("Why prefix-range sharding",
                    "Each request maps to exactly one shard determined by the first 1–2 prefix "
                    "chars. Locality means each shard loads only its slice of the global trie into "
                    "RAM — keeps per-shard memory bounded."),
                   ("Hot range mitigation",
                    "Common letters ('s', 't') get split-on-load: 's*' becomes 'sa-sm' and "
                    "'sn-sz'. Routing layer holds the current split table; rebalancing happens at "
                    "snapshot deploy time."),
                   ("Browser cache",
                    "Client memoizes responses keyed by prefix for the session. Backspacing or "
                    "retyping the same prefix is instant and offloads the network entirely."),
                   ("Edge / CDN cache",
                    "Anonymous (non-personalized) responses cached at edge with short TTL "
                    "(10–60s). Common prefixes ('a', 'the', 'how to') dominate keystrokes — edge "
                    "hit ratio reaches 70–80%. Personalized requests bypass edge."),
                   ("In-process result cache",
                    "API node holds a small LRU of {(prefix, locale) → top-K} for recently asked "
                    "non-personalized prefixes — cuts trie shard fan-out further. Invalidated on "
                    "snapshot version bump."),
               ],
               diagram=(
                   "graph LR\n"
                   "  C[Client] --> BC[Browser Cache]\n"
                   "  BC -->|miss| EC[Edge / CDN]\n"
                   "  EC -->|miss anonymous| API\n"
                   "  API --> RC[API Result Cache]\n"
                   "  RC -->|miss| TS[Trie Shard]\n"
                   "  TS --> DL[Delta Layer merge]\n"
                   "  API --> P[Personalizer]\n"
                   "  P --> FS[Feature Store]\n"
               )),
        _topic("privacy-log-sanitization",
               "Privacy: Sanitizing Query Logs",
               "Query logs are PII-rich (people search for medical, legal, personal queries). "
               "Sanitize at ingest, scope user data, and respect data-residency boundaries.",
               [
                   ("Sanitize at ingest",
                    "Strip precise IP (truncate to /24), exact device id, and any URL-bearing query "
                    "params. Run a PII regex over the query string to mask emails, phones, and "
                    "SSN-shaped tokens before persistence."),
                   ("Scope user data",
                    "user_history is gated by user consent and TTL'd (e.g., 90–180 days). "
                    "Aggregation pipelines operate on the sanitized event stream, never raw."),
                   ("Data residency",
                    "Per-region pipelines for regulated locales. EU events are aggregated in EU "
                    "infra; resulting trie snapshot is region-scoped. No cross-border raw event "
                    "movement."),
                   ("Encrypted cold storage",
                    "Raw logs (pre-sanitization) retained briefly in encrypted cold storage with "
                    "narrow access for incident response, then deleted on a fixed schedule."),
                   ("Rate of disclosure",
                    "Public typeahead must not leak identifying queries (e.g., a phone number "
                    "completing into a name). Banlist + low-frequency suppression — queries below "
                    "k-anonymity threshold are excluded from the trie entirely."),
               ]),
    ],
)
