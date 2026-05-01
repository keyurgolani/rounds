"""SD-Yelp — Design Yelp / Nearby Friends (Geospatial Search). Mirrors the
schema/shape of SD_01 in sd_questions.py. Auto-discovered by
`sd_questions._load_more` because this module exposes `PAYLOAD`."""
from __future__ import annotations

from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design Yelp / Nearby Friends",
    "Hard",
    "Design a geospatial search service that lets users find nearby businesses (Yelp) and friends "
    "within a configurable radius (e.g., 500m, 5km, 50km). The system stores tens of millions of "
    "business records with category, ratings, hours, photos, and reviews; tens of millions of users "
    "post live location updates every few seconds. Cover the geospatial index choice (geohash vs "
    "quadtree vs R-tree vs S2), why naive Haversine over a SQL table fails at scale, the radius "
    "query path (geohash prefix → candidate set → exact distance filter → ranking), business "
    "metadata + review aggregates, real-time location ingest with sharding by geohash region, "
    "category and keyword search, and review write/aggregate pipeline.",
    hints=[
        "Naive 'SELECT * WHERE Haversine(lat,lng,?,?) < r' is O(N) full-scan — dies at ~10M rows.",
        "The job of a geospatial index is to prune the candidate set BEFORE the exact distance check.",
        "Geohash = base32 prefix encoding of (lat,lng); shared prefix ≈ spatial proximity (with edge cases).",
        "Quadtree adapts to density (Manhattan vs desert); geohash is fixed-grid and simpler to shard.",
        "S2 (Google) and H3 (Uber) are production-grade hierarchical cell systems — mention by name.",
        "Read-heavy for businesses (mostly static); write-heavy for friends (location pings every few sec).",
        "Reviews aggregate (avg rating, count) is updated async — never on the hot read path.",
        "Search radius queries always need a 'neighbor cells' fan-out — boundary objects span cells.",
    ],
    constraints=[
        "100M+ businesses globally; 500M+ users; 50M DAU",
        "Read p99 < 200ms for nearby business search",
        "Friend location ping every 3-10s while app is foreground",
        "Search radius typically 500m-50km, capped at 100km",
        "Hot regions (Manhattan, Tokyo) 100× denser than rural — index must adapt",
    ],
    req_func=[
        "Find businesses near (lat,lng) within radius R, optionally filtered by category/keyword",
        "Find friends near (lat,lng) within radius R who have opted-in to sharing",
        "Update user location (high write QPS)",
        "Read business details, photos, hours, reviews",
        "Post review and rating; aggregate updates near-real-time",
        "Rank results by distance, rating, popularity, personalization",
    ],
    req_nonfunc=[
        "Search latency p99 < 200ms",
        "Location update accepted within p99 < 100ms",
        "Eventual consistency for friend location (~5s acceptable)",
        "Business metadata strongly consistent on owner-edits",
        "Horizontally scalable: shard by geohash region",
        "Privacy: friends visibility opt-in, location TTL",
    ],
    estimation={
        "businesses": "100M",
        "users_dau": "50M",
        "location_writes_qps": "~5M users foreground × 1 ping / 5s = ~1M writes/sec peak",
        "search_qps": "~200K reads/sec steady, 1M peak",
        "reviews_per_day": "~10M",
        "avg_candidates_per_radius_query": "~200-2000 before distance filter",
        "storage_business_metadata": "~5KB/biz × 100M ≈ 500GB",
        "storage_location_hot": "50M users × ~100B = 5GB hot tier (in-memory)",
    },
    endpoints=[
        {"method": "GET", "path": "/search/nearby",
         "description": "Search businesses near (lat,lng) within radius",
         "body": "?lat=&lng=&radius_m=&category=&keyword=&page_size=20"},
        {"method": "GET", "path": "/friends/nearby",
         "description": "Find opted-in friends near (lat,lng)",
         "body": "?lat=&lng=&radius_m="},
        {"method": "POST", "path": "/location/update",
         "description": "User pushes current location",
         "body": "{user_id, lat, lng, accuracy_m, ts}"},
        {"method": "GET", "path": "/business/{id}",
         "description": "Read business detail + review aggregates"},
        {"method": "POST", "path": "/business/{id}/review",
         "description": "Post review",
         "body": "{user_id, stars, text}"},
    ],
    tables=[
        {"name": "businesses",
         "columns": ["id BIGINT PK", "name VARCHAR(256)", "lat DOUBLE", "lng DOUBLE",
                     "geohash VARCHAR(12)", "category VARCHAR(64)", "subcats TEXT",
                     "address TEXT", "hours JSON", "photos_url TEXT",
                     "avg_rating FLOAT", "review_count INT", "updated_at BIGINT"]},
        {"name": "reviews",
         "columns": ["id BIGINT PK", "business_id BIGINT", "user_id BIGINT",
                     "stars TINYINT", "text TEXT", "created_at BIGINT"]},
        {"name": "review_aggregates",
         "columns": ["business_id BIGINT PK", "avg_rating FLOAT",
                     "rating_histogram JSON", "review_count INT", "last_updated BIGINT"]},
        {"name": "user_location",
         "columns": ["user_id BIGINT PK", "lat DOUBLE", "lng DOUBLE",
                     "geohash VARCHAR(12)", "accuracy_m INT", "ts BIGINT",
                     "ttl_seconds INT", "share_with_friends BOOL"]},
        {"name": "friendships",
         "columns": ["user_id BIGINT", "friend_id BIGINT", "share_location BOOL",
                     "PRIMARY KEY (user_id, friend_id)"]},
    ],
    indexes=[
        "(geohash) on businesses — primary spatial pruning",
        "(geohash, category) on businesses — common 2-tuple query",
        "(business_id, created_at DESC) on reviews — paginate review feed",
        "(geohash, ts) on user_location — find recently-pinging users in cell",
        "(user_id) on friendships",
    ],
    hld_desc=(
        "Read path goes through CDN/cache-fronted Search Service which talks to a Geo Index "
        "(geohash-sharded, in-memory grid + spillover to KV). Business metadata lives in a "
        "sharded relational store; review aggregates are a read-replica updated async by a stream "
        "processor. Location ingest is a separate high-QPS write path: clients ping a Location "
        "Service that writes to a sharded in-memory store keyed by geohash, with TTL. Friends-nearby "
        "queries hit the same geo index but with a per-user friend filter."
    ),
    hld_components=[
        {"name": "API Gateway", "role": "Auth, rate-limit, route"},
        {"name": "Search Service", "role": "Radius queries, ranking, candidate pruning"},
        {"name": "Geo Index", "role": "Geohash-sharded in-memory grid; primary pruning"},
        {"name": "Business Store", "role": "Sharded RDB for business metadata + reviews"},
        {"name": "Review Aggregator", "role": "Stream consumer; updates avg_rating async"},
        {"name": "Location Service", "role": "High-QPS location ingest, TTL store"},
        {"name": "Location Hot Store", "role": "In-memory KV (Redis-style), sharded by geohash"},
        {"name": "Friend Service", "role": "Maintains opt-in graph; filters geo results"},
        {"name": "Edge Cache / CDN", "role": "Cache popular query/category responses"},
    ],
    detailed_design={
        "geo_index_choice": (
            "Geohash chosen as the primary index: base32 prefix of interleaved lat/lng bits → "
            "shared prefix ≈ proximity. Length 6 ≈ ~1.2km cells; length 7 ≈ ~150m. Service "
            "computes the target cell + 8 neighbours (border objects), unions candidates, then "
            "applies exact Haversine. For dense regions (Manhattan), fall back to a quadtree-style "
            "hybrid: regions with >N businesses are subdivided to longer geohash prefixes. "
            "S2/H3 are equivalent production choices — call out hexagonal cells (H3) avoid "
            "longitude convergence issues at poles. R-tree is rejected for cluster-wide "
            "horizontal sharding because it doesn't shard cleanly."
        ),
        "radius_query_path": (
            "1) Compute geohash(lat,lng,precision) where precision is chosen from radius "
            "(radius 500m → precision 7; 5km → precision 6; 50km → precision 5). "
            "2) Fan-out target cell + 8 neighbours; for radii > cell, walk a wider grid. "
            "3) Pull candidate business ids per cell (in-memory set or KV lookup). "
            "4) For each candidate compute exact Haversine distance, drop > radius. "
            "5) Apply category/keyword filter. "
            "6) Rank by weighted score (distance, rating, review_count, personalization). "
            "Candidate set is typically 200-2000 — fast in-memory."
        ),
        "naive_haversine_failure": (
            "A SQL 'WHERE haversine(lat,lng,?,?) < r' forces a full scan because Haversine is "
            "not index-eligible. Even with a B-tree on (lat,lng), the predicate spans both "
            "axes non-contiguously. At 100M rows the per-query cost is seconds, not milliseconds. "
            "The geo index reduces the candidate set from 100M to ~hundreds before any "
            "distance math runs."
        ),
        "real_time_location": (
            "Location pings hit a stateless Location Service that derives geohash and writes "
            "{user_id → (lat,lng,geohash,ts)} to an in-memory sharded store with a 5-minute TTL. "
            "Sharding is BY GEOHASH PREFIX, not user_id, so 'who's near me' is a single-shard "
            "lookup for most queries. Friend filter is a join against a small per-user friend "
            "set (cached) on the result. Location writes are fire-and-forget at p99 < 100ms; "
            "occasional drops are acceptable because the next ping arrives in seconds."
        ),
        "review_pipeline": (
            "POST /review writes synchronously to reviews table and emits a Kafka event. A "
            "stream processor consumes the event, recomputes (avg_rating, rating_histogram, "
            "review_count) for that business, and writes review_aggregates. Search reads "
            "review_aggregates only — never aggregates on the hot path. Lag is bounded "
            "to a few seconds in normal operation."
        ),
        "category_keyword_search": (
            "Categories are a low-cardinality enum filter applied during candidate scan. "
            "Free-text keyword search uses a separate inverted index (Elasticsearch) "
            "queried in parallel; results are intersected with the geo candidate set. For "
            "keyword-heavy queries (e.g., 'sushi near me'), the keyword path is primary and "
            "the geo cell becomes a post-filter."
        ),
        "sharding_strategy": (
            "Geo Index sharded by geohash prefix (e.g., first 4 chars → ~32^4 = ~1M shards "
            "rolled up to ~256 physical nodes). Hot regions assigned more replicas. Business "
            "metadata sharded by business_id (stable, no rebalance on geo updates). User "
            "location sharded by current geohash — re-keyed on every ping if cell changes."
        ),
        "slo_contract": (
            "Search p99<200ms, location-update p99<100ms, review-aggregate lag p99<10s, "
            "friend-nearby p99<300ms (extra hop for friend filter)."
        ),
    },
    trade_offs=[
        {"option": "Geohash vs Quadtree",
         "for_geohash": "Fixed-grid, trivial to shard, simple prefix matching",
         "for_quadtree": "Adapts to density (Manhattan vs desert), better candidate count",
         "recommendation": "Geohash primary + quadtree-style adaptive subdivision in dense regions."},
        {"option": "S2 (Google) vs H3 (Uber)",
         "for_s2": "Hierarchical spherical cells, mature at Google",
         "for_h3": "Hexagonal cells, uniform neighbour distance, no pole convergence",
         "recommendation": "H3 for ride-hailing-like uniform-distance queries; S2 fine for Yelp."},
        {"option": "Push location to server vs query on demand",
         "for_push": "Real-time friend-nearby without per-friend pull",
         "for_pull": "Lower write QPS, only query when needed",
         "recommendation": "Push for friends-nearby; otherwise pull is fine."},
        {"option": "Sync vs async review aggregate update",
         "for_sync": "Read-after-write consistency",
         "for_async": "Decouples write latency, scales reads",
         "recommendation": "Async — UI optimistically shows new review immediately."},
    ],
    tips=[
        "Lead with 'naive Haversine over a SQL table is O(N) — geospatial index pruning is the whole point.'",
        "Name geohash, quadtree, R-tree, S2, H3 — interviewer wants to know you know the landscape.",
        "Always do candidate prune → exact distance — never one or the other.",
        "Border-cell fan-out (target + 8 neighbours) is the bug candidates miss.",
        "Friends-nearby and businesses-nearby share the geo index but have different write profiles.",
        "Review aggregates are async — never compute avg on hot read path.",
        "Sharding by geohash makes 'who's near me' single-shard; sharding by user_id does NOT.",
    ],
    thought_process=[
        "1. Clarify: businesses (read-heavy, mostly static) vs friends (write-heavy, real-time).",
        "2. Estimate: 100M businesses, 1M location writes/sec peak, 200K search reads/sec.",
        "3. Reject naive Haversine: O(N) full-scan dies past 10M rows.",
        "4. Pick geo index: geohash for sharding simplicity, quadtree for adaptive density.",
        "5. Radius query path: target cell + 8 neighbours → candidate pull → exact distance → rank.",
        "6. Location ingest: shard by geohash (not user_id), TTL hot store.",
        "7. Reviews: sync write, async aggregate via stream processor.",
        "8. Category/keyword: low-card enum on candidate scan; full-text via parallel ES path.",
        "9. Hot-region adaptation: subdivide dense geohash prefixes.",
    ],
    tags=["geospatial", "search", "quadtree", "geohash", "location"],
    arch_nodes=[
        {"id": "client", "label": "Mobile App", "type": "client"},
        {"id": "lb", "label": "API Gateway", "type": "lb"},
        {"id": "search", "label": "Search Service", "type": "server"},
        {"id": "loc", "label": "Location Service", "type": "server"},
        {"id": "geo", "label": "Geo Index (geohash-sharded)", "type": "service"},
        {"id": "biz", "label": "Business Store (RDB)", "type": "database"},
        {"id": "rev", "label": "Review Aggregator", "type": "service"},
        {"id": "agg", "label": "Review Aggregates", "type": "database"},
        {"id": "hot", "label": "Location Hot Store", "type": "cache"},
        {"id": "es", "label": "Keyword Index (ES)", "type": "service"},
        {"id": "friend", "label": "Friend Service", "type": "server"},
        {"id": "cdn", "label": "Edge Cache", "type": "cache"},
    ],
    arch_edges=[
        {"source": "client", "target": "lb"},
        {"source": "lb", "target": "search", "label": "/search/nearby"},
        {"source": "lb", "target": "loc", "label": "/location/update"},
        {"source": "search", "target": "geo", "label": "candidate pull"},
        {"source": "search", "target": "biz", "label": "metadata"},
        {"source": "search", "target": "agg", "label": "ratings"},
        {"source": "search", "target": "es", "label": "keyword"},
        {"source": "search", "target": "friend", "label": "friend filter"},
        {"source": "loc", "target": "hot", "label": "geohash write"},
        {"source": "loc", "target": "geo", "label": "update cell"},
        {"source": "biz", "target": "rev", "label": "review event"},
        {"source": "rev", "target": "agg", "label": "recompute"},
        {"source": "client", "target": "cdn", "label": "popular cells"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant U as User App\n"
        "  participant API\n"
        "  participant S as Search Svc\n"
        "  participant G as Geo Index\n"
        "  participant B as Business Store\n"
        "  participant A as Review Aggregates\n"
        "  U->>API: GET /search/nearby?lat=..&lng=..&r=2km\n"
        "  API->>S: route\n"
        "  S->>S: geohash(lat,lng,6) + 8 neighbours\n"
        "  S->>G: pull candidates in 9 cells\n"
        "  G-->>S: ~500 business ids\n"
        "  S->>S: Haversine filter to radius\n"
        "  S->>B: fetch metadata for top-N\n"
        "  S->>A: fetch review aggregates\n"
        "  S->>S: rank (distance, rating, popularity)\n"
        "  S-->>U: 20 results"
    ),
    er_diagram=(
        "erDiagram\n"
        "  BUSINESS ||--o{ REVIEW : has\n"
        "  BUSINESS ||--|| REVIEW_AGGREGATE : summarises\n"
        "  USER ||--o{ REVIEW : writes\n"
        "  USER ||--|| LOCATION : pings\n"
        "  USER ||--o{ FRIENDSHIP : owns\n"
        "  BUSINESS { bigint id\n string name\n double lat\n double lng\n string geohash\n string category }\n"
        "  REVIEW { bigint id\n bigint business_id\n bigint user_id\n int stars\n text body }\n"
        "  LOCATION { bigint user_id\n double lat\n double lng\n string geohash\n bigint ts }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B{Naive Haversine?}\n"
        "  B -->|Reject: O N| C[Geo index]\n"
        "  C --> D[Geohash vs quadtree vs S2]\n"
        "  D --> E[Geohash + adaptive subdivision]\n"
        "  E --> F[Radius query: cell + 8 neighbours]\n"
        "  F --> G[Exact Haversine on candidates]\n"
        "  G --> H[Rank: dist + rating + pop]\n"
        "  C --> I[Friends: shard by geohash]\n"
        "  I --> J[TTL hot store]"
    ),
    tradeoff_title="Geohash vs Quadtree vs S2/H3 for primary geo index",
    tradeoff_options=[
        {"label": "Geohash (fixed grid)",
         "description": "Base32 prefix of interleaved lat/lng bits.",
         "pros": ["Trivial to shard by prefix", "Simple to reason about", "Cheap encode/decode"],
         "cons": ["Fixed grid wastes space in deserts and overflows in Manhattan",
                 "Boundary cells require 8-neighbour fan-out",
                 "Longitude shrinks at poles"]},
        {"label": "Quadtree (adaptive)",
         "description": "Recursive subdivision of regions when density exceeds threshold.",
         "pros": ["Density-adaptive: dense regions get finer cells", "Bounded candidate count per cell"],
         "cons": ["Harder to shard cluster-wide", "Tree mutation under writes is non-trivial"]},
        {"label": "S2 / H3 (hierarchical cells)",
         "description": "Production-grade hierarchical cell systems (Google / Uber).",
         "pros": ["Built-in hierarchy", "H3 hexagons give uniform neighbour distance",
                 "Battle-tested libraries"],
         "cons": ["More complex than geohash", "Library dependency"]},
    ],
    tradeoff_rec=(
        "Geohash for primary sharding + adaptive quadtree-style subdivision in dense prefixes. "
        "Mention S2/H3 as production alternatives. R-tree rejected for cluster-wide sharding."
    ),
    senior_topics=[
        _topic("geo-index-choice",
               "Geospatial Index Selection: Geohash, Quadtree, R-tree, S2, H3",
               "The choice of geo index dictates shard layout, query latency, and "
               "density-handling. No single index dominates — most production systems hybridise.",
               [
                   ("Geohash",
                    "Interleave lat/lng bits, base32 encode. Length L → cell ~⁠proportional to 2^-L "
                    "in each axis. Great for prefix sharding; poor at dense areas; longitude "
                    "convergence at poles."),
                   ("Quadtree",
                    "Recursive 2D subdivision. Each node has 4 children; subdivides only when "
                    "density exceeds threshold. Adapts to skew. Harder to shard horizontally."),
                   ("R-tree",
                    "Bounding-rectangle tree for arbitrary shapes. Excellent in-process index "
                    "(PostGIS uses it) but cluster-sharding is awkward — overlapping rectangles "
                    "force replication or routing layer."),
                   ("S2 (Google)",
                    "Spherical hierarchical cell IDs; 30 levels deep. Used by Google Maps. "
                    "Strong library support, well-defined neighbour math."),
                   ("H3 (Uber)",
                    "Hexagonal hierarchical cells. Uniform neighbour distance — preferred for "
                    "ride-hailing dispatch. 16 resolution levels."),
                   ("Hybrid in practice",
                    "Yelp-class system: geohash for cluster-wide sharding + quadtree-style "
                    "subdivision in dense prefixes. Search service is the only place that "
                    "knows the hybrid."),
               ],
               diagram=(
                   "graph TD\n"
                   "  A[lat,lng] --> B[geohash prefix]\n"
                   "  B --> C{Cell density}\n"
                   "  C -->|low| D[Use cell directly]\n"
                   "  C -->|high| E[Subdivide quadtree-style]\n"
                   "  D --> F[Candidate set]\n"
                   "  E --> F\n"
                   "  F --> G[Exact Haversine filter]"
               )),
        _topic("border-cell-fanout",
               "Border-Cell Fan-Out for Radius Queries",
               "A query at the edge of a geohash cell will miss businesses sitting just across "
               "the boundary in neighbouring cells. The fix is to always fan out target + 8 "
               "neighbours; for radii larger than cell-size, walk a wider grid.",
               [
                   ("Why one cell isn't enough",
                    "A point near the cell edge has neighbours in adjacent cells within the "
                    "radius — single-cell pull silently drops them."),
                   ("8-neighbour fan-out",
                    "Compute target cell c, then c.N, c.S, c.E, c.W, and 4 diagonals. Union "
                    "candidate ids, dedupe, then exact distance filter."),
                   ("Radius-driven precision",
                    "Pick geohash precision from radius: each precision-step is ~⁠4× cell area. "
                    "If radius > cell, escalate to lower precision OR walk a larger grid."),
                   ("Sharding implications",
                    "Cross-shard scatter on every query — bound by 9. Mitigate via co-located "
                    "neighbour cells on same physical node where possible."),
               ]),
        _topic("location-write-shard",
               "Sharding the Location Hot Store by Geohash, Not User ID",
               "Friends-nearby is a 'who's in my cell' query, not a 'where is user X' query. "
               "Sharding by geohash makes the common query single-shard.",
               [
                   ("User-id sharding fails the common query",
                    "If sharded by user_id, 'who's near me' fans out to every shard. At 1M "
                    "writes/sec and 50M users, that's catastrophic."),
                   ("Geohash sharding makes it single-shard",
                    "Most queries hit one shard (target cell); 8 neighbours add bounded fan-out."),
                   ("Re-key on cell change",
                    "When a user's geohash changes, write moves to a new shard. Old entry "
                    "expires via TTL or explicit delete."),
                   ("TTL discipline",
                    "Stale locations are worse than missing ones. 5-minute TTL keeps the hot "
                    "store small and fresh."),
               ]),
        _topic("review-async-aggregate",
               "Async Review Aggregate Pipeline",
               "Computing avg_rating on the read path is forbidden — for a popular business "
               "with 100K reviews, this is an O(N) scan per query.",
               [
                   ("Write path",
                    "POST /review → reviews table insert → emit Kafka event {business_id, "
                    "stars}."),
                   ("Aggregate consumer",
                    "Stream processor (Flink/Kafka Streams) maintains running (sum, count, "
                    "histogram) keyed by business_id. Writes review_aggregates on each event."),
                   ("Read path",
                    "Search reads review_aggregates only — single row lookup, never scans "
                    "reviews table."),
                   ("UI consistency illusion",
                    "Client optimistically shows the user's own review immediately; aggregate "
                    "lag of a few seconds is invisible."),
                   ("Rebuild safety",
                    "Aggregator can be rebuilt from scratch by replaying the review event log — "
                    "no separate backup needed."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant U as User\n"
                   "  participant API\n"
                   "  participant DB as Reviews DB\n"
                   "  participant K as Kafka\n"
                   "  participant F as Flink\n"
                   "  participant A as Aggregates\n"
                   "  U->>API: POST /review\n"
                   "  API->>DB: insert\n"
                   "  API->>K: event {biz, stars}\n"
                   "  API-->>U: 200 (optimistic)\n"
                   "  K->>F: consume\n"
                   "  F->>A: update avg, count, histogram"
               )),
    ],
)
