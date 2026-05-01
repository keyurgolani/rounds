"""System Design Questions content. 17 entries matching the schema of
the existing `content.json` system_design_questions list. Helpers keep
each entry compact while preserving every required field."""
from __future__ import annotations


def _q(title, difficulty, description, *, hints, constraints,
       req_func, req_nonfunc, estimation, endpoints, tables, indexes,
       hld_desc, hld_components, detailed_design, trade_offs, tips,
       thought_process, tags, arch_nodes, arch_edges,
       sequence_diagram, er_diagram, thought_flow,
       tradeoff_title, tradeoff_options, tradeoff_rec, senior_topics):
    return {
        "title": title,
        "difficulty": difficulty,
        "description": description,
        "hints": hints,
        "constraints": constraints,
        "requirements_functional": req_func,
        "requirements_nonfunctional": req_nonfunc,
        "estimation": estimation,
        "api_design": {"endpoints": endpoints},
        "database_schema": {"tables": tables, "indexes": indexes},
        "high_level_design": {"description": hld_desc, "components": hld_components},
        "detailed_design": detailed_design,
        "trade_offs": trade_offs,
        "tips": tips,
        "thought_process": thought_process,
        "tags": tags,
        "architecture_diagram": {"nodes": arch_nodes, "edges": arch_edges},
        "sequence_diagram": sequence_diagram,
        "er_diagram": er_diagram,
        "thought_flow": thought_flow,
        "tradeoff_visual": {"title": tradeoff_title, "options": tradeoff_options,
                              "recommendation": tradeoff_rec},
        "senior_topics": senior_topics,
    }


def _topic(tid, title, summary, sections, diagram="", sources=None):
    return {
        "id": tid,
        "title": title,
        "summary": summary,
        "sections": [{"heading": h, "body": b} for h, b in sections],
        "diagram": diagram,
        "sources": sources or [],
    }


# Common diagrams shorthand
def _client_lb_app_db_arch():
    return (
        [
            {"id": "client", "label": "Client", "type": "client"},
            {"id": "lb", "label": "Load Balancer", "type": "lb"},
            {"id": "app", "label": "App Servers", "type": "server"},
            {"id": "cache", "label": "Cache", "type": "cache"},
            {"id": "db", "label": "Database", "type": "database"},
        ],
        [
            {"source": "client", "target": "lb"},
            {"source": "lb", "target": "app"},
            {"source": "app", "target": "cache"},
            {"source": "cache", "target": "db", "label": "miss"},
        ],
    )


# ============================================================================
# SD-01 — Kindle Offline Sync
# ============================================================================
SD_01 = _q(
    "Design Kindle Offline Sync",
    "Medium",
    "Design synchronisation that lets a user with multiple Kindle devices (plus phone, tablet, web) "
    "seamlessly resume reading. Sync includes Last Page Read (LPR), Furthest Page Read (FPR), bookmarks, "
    "highlights, and notes. Devices may be offline for hours-to-weeks; the design is offline-first with "
    "eventual consistency.",
    hints=[
        "Devices intermittently online — eventual consistency, not strong.",
        "FPR is monotonic (always grows) — easy. LPR can move backwards — hard conflict story.",
        "Christmas Day is a known 10× spike. Plan for it in v1.",
        "Conflict resolution server-side — old Kindle generations can't all evolve client logic together.",
        "Delta sync via opaque sync tokens, not full state.",
    ],
    constraints=[
        "Devices may be offline for hours-to-weeks",
        "5+ devices per active user",
        "Cellular bandwidth precious — delta sync only",
        "Sync within minutes of going online",
    ],
    req_func=[
        "Sync FPR and LPR per (user, book)",
        "Sync bookmarks, highlights, notes",
        "Reconcile conflicts when multiple devices were offline",
        "Push update to other devices on progress change",
        "First-time device pulls full state efficiently",
    ],
    req_nonfunc=[
        "Eventual consistency within minutes online",
        "Bandwidth efficient — delta sync",
        "Reliable — never lose annotations",
        "Scale: 100M+ readers, 1B+ books",
        "Christmas-spike-tolerant: 10× normal QPS",
    ],
    estimation={
        "active_users": "100M", "books_per_user": "30",
        "events_per_day": "~1B page-turns + annotations",
        "qps_steady": "10-20K writes/sec, 50K reads/sec",
        "qps_peak": "Christmas: 10× steady",
        "storage_per_user": "~1MB metadata + variable annotation blob",
    },
    endpoints=[
        {"method": "POST", "path": "/sync/{user}/{book}",
         "description": "Push deltas, receive server changes since sync_token",
         "body": "{since_token, fpr, lpr, lpr_ts, highlights:[], notes:[]}"},
        {"method": "GET", "path": "/sync/{user}/{book}",
         "description": "Pull server-side changes since sync_token"},
        {"method": "POST", "path": "/devices/register",
         "description": "Register a device for push notifications"},
    ],
    tables=[
        {"name": "books_progress",
         "columns": ["user_id BIGINT", "book_id VARCHAR(64)", "fpr INT", "lpr INT",
                     "lpr_device_id VARCHAR(64)", "lpr_updated_at BIGINT",
                     "PRIMARY KEY (user_id, book_id)"]},
        {"name": "annotations",
         "columns": ["id BIGINT PK", "user_id BIGINT", "book_id VARCHAR(64)",
                     "kind VARCHAR(16)", "location_start INT", "payload TEXT", "version BIGINT"]},
        {"name": "sync_tokens",
         "columns": ["user_id BIGINT", "device_id VARCHAR(64)", "last_token VARCHAR(128)",
                     "PRIMARY KEY (user_id, device_id)"]},
    ],
    indexes=["(user_id, book_id) on books_progress",
             "(user_id, book_id, version) on annotations"],
    hld_desc=(
        "Sharded sync service fronted by API gateway. Per-(user,book) progress in DynamoDB. "
        "Annotations as versioned log → S3 + materialised view. Push fan-out via APNs/FCM."
    ),
    hld_components=[
        {"name": "API Gateway", "role": "Auth, rate-limit, route"},
        {"name": "Sync Service", "role": "RMW progress; merge annotations"},
        {"name": "Conflict Resolver", "role": "LPR & annotation merge"},
        {"name": "Annotation Store", "role": "Versioned log"},
        {"name": "Push Service", "role": "Fan-out updates to user's devices"},
        {"name": "Edge CDN", "role": "Cache static book metadata"},
    ],
    detailed_design={
        "conflict_resolution": (
            "FPR monotonic — server stores max. LPR per-device but user-level 'most recent' is the "
            "LPR with highest device timestamp. Annotations with vector clocks; concurrent edits surface "
            "to user."
        ),
        "delta_sync": (
            "Client tracks opaque sync_token. POST returns new token + deltas since old token. "
            "Server-side change log is monotonic per-user."
        ),
        "christmas_spike": (
            "Pre-warm regional caches with last-90-days top-1000 books. New devices smear initial sync; "
            "server returns 429 to abusive clients."
        ),
        "slo_contract": (
            "Sync p99<2s online, p99<60s after extended offline. Annotation loss: zero. Push: best-effort 90% within 60s."
        ),
    },
    trade_offs=[
        {"option": "Client vs server conflict resolution",
         "for_client": "Lower latency, simpler server",
         "for_server": "Single source of truth, evolvable rules",
         "recommendation": "Server — old Kindle generations can't evolve."},
        {"option": "Push vs pull notifications",
         "for_push": "Real-time fan-out",
         "for_pull": "No push infrastructure",
         "recommendation": "Hybrid — push on foreground, pull as fallback."},
    ],
    tips=[
        "Lead with 'offline-first, eventual consistency.' Strong consistency = wrong prompt.",
        "Distinguish FPR (monotonic) from LPR (conflict-prone). Most candidates conflate.",
        "Vector clocks for annotations is the senior signal.",
        "Christmas spike is a v1 concern, not a follow-up.",
    ],
    thought_process=[
        "1. Clarify: offline-first, eventual consistency, multiple devices.",
        "2. Estimate: 100M users × 30 books × 10 events/day → ~1B events/day.",
        "3. APIs: POST /sync, GET /sync.",
        "4. FPR (monotonic, easy) vs LPR (per-device, conflict-prone).",
        "5. Server-side resolution: LPR by latest timestamp; annotations via vector clock.",
        "6. Christmas: smear initial sync + pre-warm.",
        "7. Push (real-time) + pull (fallback).",
    ],
    tags=["sync", "offline-first", "eventual-consistency"],
    arch_nodes=[
        {"id": "device", "label": "Kindle / App", "type": "client"},
        {"id": "lb", "label": "API Gateway", "type": "lb"},
        {"id": "sync", "label": "Sync Service", "type": "server"},
        {"id": "kv", "label": "Progress KV", "type": "database"},
        {"id": "ann", "label": "Annotation Log", "type": "database"},
        {"id": "push", "label": "Push", "type": "service"},
        {"id": "cdn", "label": "Edge CDN", "type": "cache"},
    ],
    arch_edges=[
        {"source": "device", "target": "lb"},
        {"source": "lb", "target": "sync"},
        {"source": "sync", "target": "kv", "label": "FPR/LPR"},
        {"source": "sync", "target": "ann", "label": "annotations"},
        {"source": "sync", "target": "push", "label": "fan-out"},
        {"source": "push", "target": "device"},
        {"source": "device", "target": "cdn", "label": "metadata"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant D1 as Kindle 1\n"
        "  participant API\n"
        "  participant DB\n"
        "  participant Push\n"
        "  participant D2 as Kindle 2\n"
        "  D1->>API: POST /sync (LPR=120)\n"
        "  API->>DB: read prev LPR=100\n"
        "  API->>DB: write LPR=120\n"
        "  API->>Push: notify D2\n"
        "  API-->>D1: 200 (sync_token)\n"
        "  Push-->>D2: book changed\n"
        "  D2->>API: GET /sync\n"
        "  API-->>D2: LPR=120"
    ),
    er_diagram=(
        "erDiagram\n"
        "  USER ||--o{ BOOK_PROGRESS : has\n"
        "  USER ||--o{ ANNOTATION : owns\n"
        "  BOOK_PROGRESS { bigint user_id\n string book_id\n int fpr\n int lpr }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B{Online?}\n"
        "  B -->|Offline-first| C[Eventual consistency]\n"
        "  C --> D[Delta sync]\n"
        "  D --> E[Server-side resolution]\n"
        "  E --> F[Christmas spike: smear]"
    ),
    tradeoff_title="Per-device vs Per-user LPR",
    tradeoff_options=[
        {"label": "Per-device LPR",
         "description": "Each device tracks its own.",
         "pros": ["Simple", "Each device knows where IT left off"],
         "cons": ["UI must pick", "No direct 'where did I leave off'"]},
        {"label": "Per-user (unified) LPR",
         "description": "Single canonical position.",
         "pros": ["Direct UX answer", "One source"],
         "cons": ["Conflict resolution required"]},
    ],
    tradeoff_rec="Both — per-device storage; expose unified 'most recent' to UX.",
    senior_topics=[
        _topic("vector-clocks",
               "Vector Clocks for Annotation Conflicts",
               "Concurrent offline edits need partial-order reconciliation. Vector clocks tag each "
               "annotation with per-device counters; concurrent edits surface to user.",
               [
                   ("Why timestamps fail",
                    "Two devices offline simultaneously edit same highlight; clock skew makes "
                    "last-write-wins drop a real edit silently."),
                   ("Vector-clock semantics",
                    "Tag {device_a:5, device_b:3}. vc_x dominates iff every component ≥ vc_y; "
                    "otherwise concurrent → surface."),
                   ("Storage cost",
                    "Bounded by device count (~10 per user). Trim entries for inactive devices."),
                   ("UX for concurrent edits",
                    "Server stores both versions; client renders 'pick which to keep'."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant D1\n  participant D2\n  participant S\n"
                   "  D1->>D1: edit (vc={D1:5})\n"
                   "  D2->>D2: edit (vc={D2:3})\n"
                   "  D1->>S: sync\n  D2->>S: sync\n"
                   "  S->>S: detect concurrent\n"
                   "  S-->>D1: conflict"
               )),
        _topic("christmas-spike",
               "Christmas-Day Sync Spike Mitigations",
               "10× steady-state sustained for hours. Throttle + pre-warm + lazy.",
               [
                   ("What it looks like", "Christmas morning: 10× steady-state for hours; mostly read-heavy first-time book pulls."),
                   ("Smear initial sync", "Client queue: 1 book/sec ramp; server 429 on abuse."),
                   ("Pre-warm caches", "Top-1000 books loaded into edge before peak."),
                   ("Lazy annotation load", "Don't sync all annotations on registration; load on first book-open."),
               ]),
    ],
)


# ============================================================================
# SD-02 — Ride-Sharing Platform
# ============================================================================
SD_02 = _q(
    "Design a Ride-Sharing Platform (like Uber/Lyft)",
    "Hard",
    "Design a scalable platform connecting riders with drivers in real time. Must support live location "
    "tracking, fast matching, surge pricing, payments, and 100M+ active users globally. Focus on the "
    "matching path latency, not the entire app surface.",
    hints=[
        "Geospatial indexing — geohash or H3 — is the matching core.",
        "Driver location updates dominate write traffic; rider matching is read-spike on demand.",
        "Surge pricing decoupled from matching — pricing module reads supply/demand grids.",
        "Payment is asynchronous from ride completion — never block the ride flow on payment.",
        "Rider/driver match must complete in <5s p99; that's the SLO that drives the design.",
    ],
    constraints=[
        "100M+ active users globally",
        "10M+ active drivers",
        "Driver location updates every 4-5s",
        "Match must complete p99 < 5s",
        "Payment processed within seconds of completion",
    ],
    req_func=[
        "Real-time location tracking for drivers",
        "Match rider request to nearest qualified driver",
        "Show real-time driver position to rider during ride",
        "Process payment + driver payout",
        "Surge pricing during high demand",
        "Trip history, ratings, support cases",
    ],
    req_nonfunc=[
        "Match latency p99 < 5s",
        "99.99% availability for matching path",
        "Geographic data partitioning — request from NY hits NY shard",
        "Battery-friendly client updates",
        "Eventually consistent payment + analytics",
    ],
    estimation={
        "active_users": "100M",
        "active_drivers": "10M (concurrent online: ~3M)",
        "ride_requests_per_day": "~30M",
        "location_updates": "3M drivers × 12 updates/min = 36M/min",
        "payment_volume": "~$1B/day GMV",
        "qps_match": "~5K matching requests/sec global",
    },
    endpoints=[
        {"method": "POST", "path": "/drivers/location",
         "description": "Driver pushes location update",
         "body": "{driver_id, lat, lng, speed, heading}"},
        {"method": "POST", "path": "/rides/request",
         "description": "Rider requests a trip",
         "body": "{rider_id, pickup, dropoff, vehicle_class}"},
        {"method": "GET", "path": "/rides/{ride_id}/track",
         "description": "WebSocket for live position updates"},
        {"method": "POST", "path": "/rides/{ride_id}/complete",
         "description": "Driver marks completion"},
    ],
    tables=[
        {"name": "drivers",
         "columns": ["id BIGINT PK", "name VARCHAR", "vehicle_class VARCHAR", "rating FLOAT", "active BOOL"]},
        {"name": "driver_locations",
         "columns": ["driver_id BIGINT PK", "lat DOUBLE", "lng DOUBLE", "geohash VARCHAR(8)", "updated_at BIGINT"]},
        {"name": "rides",
         "columns": ["id BIGINT PK", "rider_id BIGINT", "driver_id BIGINT", "pickup_lat DOUBLE", "pickup_lng DOUBLE",
                     "status VARCHAR", "fare_cents INT", "started_at BIGINT", "completed_at BIGINT"]},
    ],
    indexes=["(geohash, updated_at) on driver_locations",
             "(rider_id, started_at) on rides"],
    hld_desc=(
        "Geo-sharded match service. Driver location stream → in-memory geohash index per region. "
        "Match service queries the index by pickup geohash. Pricing service reads supply/demand grid "
        "and applies surge multiplier. Payment async via Kafka."
    ),
    hld_components=[
        {"name": "Mobile Apps", "role": "Driver + rider clients with WebSocket"},
        {"name": "API Gateway", "role": "Auth, region-route, rate-limit"},
        {"name": "Location Service", "role": "Ingest driver pings, update geohash index"},
        {"name": "Match Service", "role": "Find candidate drivers near pickup, dispatch"},
        {"name": "Pricing Service", "role": "Surge multiplier from supply/demand"},
        {"name": "Trip Service", "role": "Ride lifecycle state machine"},
        {"name": "Payment Service", "role": "Async charge + driver payout"},
        {"name": "Geohash Index", "role": "In-memory per-region driver positions"},
    ],
    detailed_design={
        "geohash_index": (
            "H3 (Uber's hex grid) at resolution 9 (~150m hexes). Each hex maps to a list of driver IDs. "
            "Update is hash → cell → upsert. Match queries hexes within radius around pickup."
        ),
        "matching_algorithm": (
            "Get drivers within geohash neighborhood of pickup. Filter by vehicle class, rating. Score "
            "by distance + driver acceptance rate. Dispatch top candidate; if reject, fall back to next. "
            "Cap latency by capping candidates considered."
        ),
        "surge_pricing": (
            "Periodic batch (every 30s) computes supply/demand per cell. Multiplier = demand / "
            "available_supply. Bounded [1.0, 3.0]. Per-cell, smoothed over time to prevent flapping."
        ),
        "payment_pipeline": (
            "Ride complete → emit event to Kafka → payment worker charges + records. Failures retried "
            "with exponential backoff. Driver payout aggregated daily."
        ),
    },
    trade_offs=[
        {"option": "Geohash vs H3 (hex grid)",
         "for_geohash": "Simple, library support, rectangular cells",
         "for_h3": "Equal-area cells, better neighbor distance",
         "recommendation": "H3 — Uber's choice for a reason, neighbour math is cleaner."},
        {"option": "WebSocket vs polling for location",
         "for_websocket": "Real-time push, low latency",
         "for_polling": "Simpler infrastructure",
         "recommendation": "WebSocket — required for sub-5s p99 visible-driver-position UX."},
    ],
    tips=[
        "H3 (hex grid) over square geohash — Uber chose hex for a reason.",
        "Don't synchronously charge payment on ride complete. Async via Kafka.",
        "Bound candidate set in matching to cap latency; never scan all drivers.",
        "Surge pricing decoupled from matching — different read/write rates.",
    ],
    thought_process=[
        "1. Identify the hot path: rider request → match → assign → arrival.",
        "2. Geo-shard everything — no cross-region traffic on the hot path.",
        "3. Driver location updates dominate writes; geohash index for reads.",
        "4. Match: candidate set from geohash query, score, dispatch.",
        "5. Surge pricing decoupled — periodic batch on supply/demand grid.",
        "6. Payment async — never block ride flow.",
        "7. WebSocket for live tracking; polling fallback for poor connectivity.",
    ],
    tags=["geo-sharding", "real-time", "matching", "geospatial"],
    arch_nodes=[
        {"id": "rider", "label": "Rider App", "type": "client"},
        {"id": "driver", "label": "Driver App", "type": "client"},
        {"id": "lb", "label": "API Gateway", "type": "lb"},
        {"id": "match", "label": "Match Service", "type": "server"},
        {"id": "loc", "label": "Location Service", "type": "server"},
        {"id": "geo", "label": "H3 Index", "type": "cache"},
        {"id": "trip", "label": "Trip Service", "type": "server"},
        {"id": "pay", "label": "Payment", "type": "service"},
        {"id": "kafka", "label": "Kafka", "type": "queue"},
    ],
    arch_edges=[
        {"source": "driver", "target": "lb"},
        {"source": "lb", "target": "loc"},
        {"source": "loc", "target": "geo", "label": "upsert"},
        {"source": "rider", "target": "lb"},
        {"source": "lb", "target": "match"},
        {"source": "match", "target": "geo", "label": "neighbor query"},
        {"source": "match", "target": "trip"},
        {"source": "trip", "target": "kafka"},
        {"source": "kafka", "target": "pay"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant R as Rider\n"
        "  participant API\n"
        "  participant M as Match\n"
        "  participant G as H3\n"
        "  participant D as Driver\n"
        "  R->>API: request ride\n"
        "  API->>M: match\n"
        "  M->>G: drivers near pickup\n"
        "  G-->>M: [d1, d2, d3]\n"
        "  M->>D: dispatch d1\n"
        "  D-->>M: accept\n"
        "  M-->>R: matched"
    ),
    er_diagram=(
        "erDiagram\n"
        "  RIDER ||--o{ RIDE : requests\n"
        "  DRIVER ||--o{ RIDE : fulfills\n"
        "  RIDE { bigint id PK\n string status\n int fare_cents }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Request ride] --> B[H3 query]\n"
        "  B --> C[Score candidates]\n"
        "  C --> D[Dispatch top]\n"
        "  D --> E{Accept?}\n"
        "  E -->|Yes| F[Trip starts]\n"
        "  E -->|No| C"
    ),
    tradeoff_title="Geohash vs H3 hex grid",
    tradeoff_options=[
        {"label": "Geohash",
         "description": "Lat/lng → fixed-precision string.",
         "pros": ["Simple", "Library support", "Easy prefix queries"],
         "cons": ["Rectangular cells", "Variable cell area by latitude"]},
        {"label": "H3 (hex grid)",
         "description": "Globe tiled with hexagons at resolution.",
         "pros": ["Equal-area cells", "Uniform neighbor distance", "Better for radius queries"],
         "cons": ["Steeper learning curve", "Library dependency"]},
    ],
    tradeoff_rec="H3 — Uber-validated, cleaner math.",
    senior_topics=[
        _topic("h3-hex-grid",
               "Why Uber Chose H3 Over Geohash",
               "Equal-area hexagons make radius queries and neighbor expansion correct without "
               "lat-dependent corrections. The 16 resolutions trade resolution for cell count.",
               [
                   ("Hex math vs square math",
                    "Hexagons have 6 equidistant neighbors; squares have 4 equidistant + 4 diagonal at √2 "
                    "distance. Radius search in hex is a simple ring expansion."),
                   ("Resolution tradeoff",
                    "Res 9 (~150m hex) for dispatch; res 7 (~5km) for surge pricing aggregation. "
                    "Cells per resolution scale 7×."),
                   ("Cell encoding",
                    "64-bit cell ID encodes resolution + parent path. Comparable, sortable, and the parent "
                    "of any cell is a 1-bit-shift operation."),
               ]),
        _topic("surge-pricing-decoupling",
               "Surge Pricing Decoupled from Matching",
               "Pricing reads supply/demand grids; matching reads driver positions. Decoupling lets "
               "pricing batch every 30s without slowing the dispatch path.",
               [
                   ("Why coupling fails",
                    "If matching computes surge at request-time, every match needs supply/demand aggregation — slow."),
                   ("Decoupled pipeline",
                    "Periodic batch (every 30s) over location stream computes per-cell multipliers. "
                    "Match path reads multiplier from a fast key-value store."),
                   ("Multiplier smoothing",
                    "Apply EMA over recent windows to prevent flapping. Bound to [1.0, 3.0] for UX."),
               ]),
    ],
)


# ============================================================================
# SD-03 — Chat Application
# ============================================================================
SD_03 = _q(
    "Design a Chat Application (1:1 + Group + Online Status)",
    "Hard",
    "Design a scalable chat platform supporting one-on-one DMs, group chats, message history, online "
    "presence, and push notifications for offline users. Must scale to millions of concurrent connections "
    "with sub-100ms message delivery latency.",
    hints=[
        "WebSocket for live; HTTP for history fetch.",
        "Connection state lives on a specific WS server; need a routing layer for fan-out.",
        "Message store is write-heavy, reverse-time-ordered reads. Cassandra/DynamoDB beats SQL for this.",
        "Presence is best-effort, eventually consistent — don't try to make it strong.",
        "End-to-end encryption is a key follow-up; mention but only design if asked.",
    ],
    constraints=[
        "100M+ DAU, ~10M concurrent online",
        "Sub-100ms message delivery p99",
        "Group size up to 500 members",
        "Message history infinite (cold storage tier)",
    ],
    req_func=[
        "1:1 messaging with delivery + read receipts",
        "Group chats up to 500 members",
        "Online/offline/last-seen presence",
        "Message history paginated by time",
        "Push notifications for offline users",
        "Message reactions, edits, deletes",
    ],
    req_nonfunc=[
        "Sub-100ms message delivery online",
        "Eventual consistency for presence (5-10s OK)",
        "Durable message storage (no loss)",
        "Horizontally scalable WS layer",
    ],
    estimation={
        "dau": "100M", "concurrent": "10M",
        "messages_per_day": "30B (300/user/day avg)",
        "qps_msg_send": "350K/sec global",
        "storage_per_msg": "~500 bytes",
        "annual_storage": "~5PB raw, compressed ~2PB",
    },
    endpoints=[
        {"method": "WS", "path": "/ws", "description": "Persistent WebSocket; subscribe to user/group channels"},
        {"method": "POST", "path": "/messages", "description": "Send message", "body": "{thread_id, body, attachments}"},
        {"method": "GET", "path": "/threads/{id}/messages", "description": "Paginated history"},
        {"method": "POST", "path": "/threads", "description": "Create 1:1 or group thread"},
    ],
    tables=[
        {"name": "threads",
         "columns": ["id BIGINT PK", "kind VARCHAR(8)", "created_at BIGINT"]},
        {"name": "thread_members",
         "columns": ["thread_id BIGINT", "user_id BIGINT", "joined_at BIGINT", "PRIMARY KEY (thread_id, user_id)"]},
        {"name": "messages",
         "columns": ["thread_id BIGINT", "ts BIGINT", "msg_id UUID", "user_id BIGINT", "body TEXT",
                     "PRIMARY KEY (thread_id, ts, msg_id)"]},
    ],
    indexes=["(thread_id, ts DESC) on messages — Cassandra clustering",
             "(user_id) on thread_members"],
    hld_desc=(
        "WebSocket gateway handles persistent connections (sticky to WS server). Pub/sub layer (Redis "
        "Pub/Sub or Kafka) routes between WS servers. Messages persisted to Cassandra (write-heavy, "
        "thread_id partition key, ts clustering). Push for offline via APNs/FCM."
    ),
    hld_components=[
        {"name": "WS Gateway", "role": "Sticky WebSocket termination per user"},
        {"name": "Pub/Sub Router", "role": "Route messages between WS servers"},
        {"name": "Message Service", "role": "Validate, persist, fan-out"},
        {"name": "Presence Service", "role": "Maintain online/offline + last-seen"},
        {"name": "Push Service", "role": "Mobile push for offline recipients"},
        {"name": "Message Store (Cassandra)", "role": "Append-only message log"},
    ],
    detailed_design={
        "fanout_strategy": (
            "Per-message: insert to Cassandra (thread, ts, msg_id) → publish to thread channel via Redis "
            "Pub/Sub. Each WS server subscribes to channels for its connected users. Offline users get "
            "push notifications through APNs/FCM."
        ),
        "presence": (
            "On WS connect → mark user online + last-seen=now. Periodic heartbeat (every 30s). On "
            "disconnect → mark last-seen, after 60s mark offline. Best-effort — short presence flips "
            "during reconnect are OK."
        ),
        "message_ordering": (
            "Per-thread ordering via Cassandra clustering (ts DESC). Server-assigned ts on receive. "
            "Client retries with idempotency_key to dedupe."
        ),
        "read_receipts": (
            "Per-(user, thread) last_read_ts. Updated on UI scroll. Receipt fan-out is best-effort — "
            "delays of seconds are fine."
        ),
    },
    trade_offs=[
        {"option": "WebSocket vs SSE vs long-polling",
         "for_websocket": "Bidirectional, low overhead",
         "for_sse_long_polling": "Simpler, friendlier to corporate proxies",
         "recommendation": "WebSocket — required for 100ms p99."},
        {"option": "Cassandra vs Postgres for message store",
         "for_cassandra": "Linear write scaling, time-series-friendly",
         "for_postgres": "ACID, simpler ops",
         "recommendation": "Cassandra — write-heavy chat workloads kill Postgres at scale."},
    ],
    tips=[
        "Sticky WebSocket connections — once connected, that user is on a specific server.",
        "Pub/Sub is the routing layer — don't broadcast to all WS servers.",
        "Presence is hard to make strong; embrace eventual consistency.",
        "Group fan-out at write-time is the standard pattern; very large groups (10K+) need a different model.",
    ],
    thought_process=[
        "1. Hot path: live message delivery in <100ms.",
        "2. WebSocket + Pub/Sub for routing.",
        "3. Cassandra for write-heavy message store (thread partition, ts clustering).",
        "4. Presence: eventually consistent, heartbeat-based.",
        "5. Offline → push notifications.",
        "6. Group fan-out at write — small enough for typical groups.",
        "7. Read receipts as best-effort; not on the critical path.",
    ],
    tags=["chat", "websocket", "pubsub", "real-time"],
    arch_nodes=[
        {"id": "client", "label": "Client", "type": "client"},
        {"id": "lb", "label": "Load Balancer", "type": "lb"},
        {"id": "ws", "label": "WS Gateway", "type": "server"},
        {"id": "msg", "label": "Message Service", "type": "server"},
        {"id": "pubsub", "label": "Pub/Sub", "type": "queue"},
        {"id": "cass", "label": "Cassandra", "type": "database"},
        {"id": "push", "label": "Push", "type": "service"},
        {"id": "presence", "label": "Presence", "type": "server"},
    ],
    arch_edges=[
        {"source": "client", "target": "lb"},
        {"source": "lb", "target": "ws", "label": "WS"},
        {"source": "ws", "target": "msg"},
        {"source": "msg", "target": "cass", "label": "persist"},
        {"source": "msg", "target": "pubsub", "label": "fan-out"},
        {"source": "pubsub", "target": "ws"},
        {"source": "msg", "target": "push", "label": "offline"},
        {"source": "ws", "target": "presence", "label": "heartbeat"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant A as User A\n"
        "  participant WS\n"
        "  participant M as Message Svc\n"
        "  participant PS as Pub/Sub\n"
        "  participant B as User B\n"
        "  A->>WS: send message\n"
        "  WS->>M: validate + persist\n"
        "  M->>PS: publish to thread channel\n"
        "  PS-->>WS: deliver to B's WS server\n"
        "  WS-->>B: real-time message"
    ),
    er_diagram=(
        "erDiagram\n"
        "  USER ||--o{ THREAD_MEMBER : in\n"
        "  THREAD ||--o{ THREAD_MEMBER : has\n"
        "  THREAD ||--o{ MESSAGE : contains\n"
        "  MESSAGE { bigint thread_id\n bigint ts\n uuid msg_id\n text body }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Client connects] --> B[WS sticky]\n"
        "  B --> C[Subscribe to thread channels]\n"
        "  D[Send msg] --> E[Persist Cassandra]\n"
        "  E --> F[Pub/Sub fan-out]\n"
        "  F --> G[Recipients via WS]\n"
        "  F --> H[Offline push]"
    ),
    tradeoff_title="Push (fan-out at write) vs Pull (fan-out at read)",
    tradeoff_options=[
        {"label": "Push (write fan-out)",
         "description": "On send, deliver to every recipient's inbox.",
         "pros": ["Fast reads", "Real-time delivery"],
         "cons": ["Write amplification for large groups", "Storage duplication"]},
        {"label": "Pull (read fan-out)",
         "description": "Recipients query thread on read.",
         "pros": ["Cheap writes", "No duplication"],
         "cons": ["Slow reads", "Read amplification at scale"]},
    ],
    tradeoff_rec="Push for typical groups; pull for very large channels (1K+ members).",
    senior_topics=[
        _topic("e2e-encryption",
               "End-to-End Encryption (Signal Protocol)",
               "Encrypted messages where servers can't read content. Double Ratchet for forward secrecy.",
               [
                   ("Why server-side encryption isn't enough",
                    "TLS protects in transit; at-rest server-side encryption means the operator CAN read."),
                   ("Signal protocol overview",
                    "Asymmetric prekey exchange establishes an initial session; double-ratchet evolves keys per message for forward + future secrecy."),
                   ("Server's reduced role",
                    "Server stores ciphertext blobs and per-user prekey bundles. Routes blobs without seeing content."),
                   ("Operational tradeoffs",
                    "No server-side search; no link previews on encrypted messages; key rotation complexity."),
               ],
               sources=[{"label": "Signal Protocol Spec", "url": "https://signal.org/docs/"}]),
        _topic("pubsub-routing",
               "WebSocket Routing via Pub/Sub",
               "Sticky WS means a user's connection lives on one specific server. Pub/Sub bridges servers without broadcast.",
               [
                   ("The routing problem",
                    "User A on WS-1, User B on WS-2. Sending A→B requires WS-1 to reach WS-2 without knowing where B lives."),
                   ("Pub/Sub solution",
                    "Each thread has a channel. WS servers subscribe to channels for their connected users. Send → publish → consumed by relevant WS servers."),
                   ("Backpressure",
                    "Slow consumers can back up Pub/Sub. Drop-oldest policy or per-user buffer caps avoid memory blowup."),
               ]),
    ],
)


# ============================================================================
# SD-04 — TinyURL (compact since canonical example exists in content.json)
# ============================================================================
SD_04 = _q(
    "Design a URL Shortener (TinyURL/bit.ly)",
    "Medium",
    "Design a scalable URL-shortening service. Long URL in, short alias out; clicks redirect. Must "
    "support billions of URLs, millions of redirects per second, custom aliases, analytics, and "
    "expiration.",
    hints=[
        "99:1 read:write ratio. Cache the redirect path aggressively.",
        "Base62 encoding gives 62^7 ≈ 3.5T unique 7-char IDs.",
        "Pre-generated keys via a Key Generation Service avoids collision logic at write time.",
        "302 (or 307) for editable destinations + analytics; 301 only for vanity / SEO permanence.",
        "Treat analytics as a separate subsystem with its own SLO — never let it degrade redirects.",
    ],
    constraints=[
        "Short URLs ≤ 7 chars",
        "Redirect p99 < 50ms",
        "100M+ URLs, 10K writes/sec, 1M reads/sec",
        "URLs durable (no loss)",
    ],
    req_func=[
        "POST long URL → short alias",
        "GET short alias → 30x redirect to long URL",
        "Custom aliases (user-chosen short codes)",
        "Click analytics dashboard",
        "Optional URL expiration",
    ],
    req_nonfunc=[
        "High availability — redirects work even during partial failures",
        "Sub-50ms p99 redirect latency",
        "Durable URL store",
        "Abuse-resistant — rate limiting + content scanning",
    ],
    estimation={
        "urls": "1B", "writes_per_sec": "10K", "reads_per_sec": "1M",
        "storage": "~100GB metadata", "bandwidth": "~100GB/day for redirects",
    },
    endpoints=[
        {"method": "POST", "path": "/api/urls", "description": "Create short URL",
         "body": "{long_url, custom_alias?, ttl?}"},
        {"method": "GET", "path": "/{short_code}", "description": "302 redirect"},
        {"method": "GET", "path": "/api/urls/{code}/stats", "description": "Click analytics"},
    ],
    tables=[
        {"name": "urls",
         "columns": ["id BIGINT PK", "short_code VARCHAR(7) UNIQUE", "long_url TEXT",
                     "user_id BIGINT", "created_at BIGINT", "expires_at BIGINT"]},
        {"name": "click_events",
         "columns": ["short_code VARCHAR(7)", "ip INET", "country CHAR(2)", "ua TEXT",
                     "ts BIGINT"]},
    ],
    indexes=["UNIQUE (short_code) on urls", "(short_code, ts) on click_events"],
    hld_desc=(
        "Read path: client → CDN → redirect server → Redis (hot) → DB miss. Write path: API server → "
        "KGS → DB. Analytics decoupled: redirect server emits async to Kafka → ClickHouse."
    ),
    hld_components=[
        {"name": "API Gateway / LB", "role": "Route, SSL, rate-limit"},
        {"name": "Redirect Server", "role": "Hot path: cache hit → 302"},
        {"name": "Write Server", "role": "Validate + KGS + DB"},
        {"name": "Key Generation Service", "role": "Pre-generated unique base62 codes"},
        {"name": "Redis Cache", "role": "Hot URL → long_url map"},
        {"name": "URL DB", "role": "Persistent KV store"},
        {"name": "Analytics Pipeline", "role": "Kafka → ClickHouse"},
    ],
    detailed_design={
        "encoding": "Base62 (a-z, A-Z, 0-9). 7 chars → 3.5T unique IDs.",
        "kgs": "Pre-generate IDs in batches; allocate from unused pool. Move to used on assignment.",
        "caching": "Redis LRU. TTL matches URL expiration. Hit ratio target: 99%.",
        "sharding": "Range-based or hash-based by short_code. Consistent hashing for elasticity.",
        "slo_contract": "Redirect: 99.99% avail, p99 <50ms. Analytics: eventual within 60s, loss ≤0.1%. Decoupled.",
    },
    trade_offs=[
        {"option": "Pre-generated keys vs hash-computed",
         "for_pre_generated": "No collisions, fast writes",
         "for_hash_computed": "Stateless, idempotent",
         "recommendation": "Pre-generated for scale; KGS is the lock."},
        {"option": "301 vs 302 redirect",
         "for_301": "Browser/CDN caches indefinitely; SEO equity",
         "for_302": "Per-click analytics, editable destinations",
         "recommendation": "302 default; 301 only for vanity/permanent."},
    ],
    tips=[
        "URL shortener is a distributed hash table — name the pattern.",
        "Pre-generated keys avoids the collision conversation entirely.",
        "Decouple analytics from redirect path — different SLOs, fail independently.",
        "Don't forget abuse: rate limit + content scanning at submission, periodic re-scan.",
    ],
    thought_process=[
        "1. Read-heavy (99:1) — cache the redirect path aggressively.",
        "2. Base62 encoding — 7 chars enough for 3.5T IDs.",
        "3. Pre-generate keys via KGS to avoid collision logic.",
        "4. Sharded DB; Redis LRU in front.",
        "5. Decouple analytics — Kafka → ClickHouse, never block redirects.",
        "6. Abuse: rate limit + URL scanning at write + periodic re-scan.",
    ],
    tags=["url-shortener", "base62", "caching", "kgs"],
    arch_nodes=[
        {"id": "client", "label": "Client", "type": "client"},
        {"id": "lb", "label": "Load Balancer", "type": "lb"},
        {"id": "redirect", "label": "Redirect Server", "type": "server"},
        {"id": "write", "label": "Write Server", "type": "server"},
        {"id": "kgs", "label": "KGS", "type": "service"},
        {"id": "cache", "label": "Redis", "type": "cache"},
        {"id": "db", "label": "URL DB", "type": "database"},
        {"id": "analytics", "label": "ClickHouse", "type": "database"},
    ],
    arch_edges=[
        {"source": "client", "target": "lb"},
        {"source": "lb", "target": "redirect"},
        {"source": "lb", "target": "write"},
        {"source": "redirect", "target": "cache"},
        {"source": "cache", "target": "db", "label": "miss"},
        {"source": "write", "target": "kgs"},
        {"source": "write", "target": "db"},
        {"source": "redirect", "target": "analytics", "label": "log"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant C as Client\n"
        "  participant API\n"
        "  participant KGS\n"
        "  participant DB\n"
        "  C->>API: POST /api/urls\n"
        "  API->>KGS: getNextKey()\n"
        "  KGS-->>API: 'xY3aB4z'\n"
        "  API->>DB: INSERT\n"
        "  API-->>C: 201 short_url"
    ),
    er_diagram=(
        "erDiagram\n"
        "  USER ||--o{ URL : owns\n"
        "  URL ||--o{ CLICK : has\n"
        "  URL { bigint id PK\n string short_code\n text long_url }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B[99:1 read:write]\n"
        "  B --> C[Cache hot URLs]\n"
        "  C --> D[Base62 encoding]\n"
        "  D --> E[Pre-gen via KGS]\n"
        "  E --> F[Decouple analytics]"
    ),
    tradeoff_title="301 vs 302 redirect",
    tradeoff_options=[
        {"label": "301 (Permanent)",
         "description": "Browser/CDN caches indefinitely.",
         "pros": ["Fewer origin hits", "SEO equity"],
         "cons": ["Lost analytics", "Can't change destination"]},
        {"label": "302 (Found)",
         "description": "Every click reaches origin.",
         "pros": ["Per-click analytics", "Editable destinations"],
         "cons": ["More origin load", "Cache hierarchy critical"]},
    ],
    tradeoff_rec="302 default for marketing/attribution; 301 for vanity URLs only.",
    senior_topics=[
        _topic("kgs-design",
               "Key Generation Service Design",
               "Pre-generated base62 IDs from a managed pool avoid collision logic at write time. "
               "The KGS becomes a critical-path service; design for HA.",
               [
                   ("Pool model",
                    "Two tables: used_keys, unused_keys. Worker pre-generates batches into unused; "
                    "API requests allocate (move to used) atomically."),
                   ("HA",
                    "Multiple KGS instances per region. Each holds a non-overlapping range of IDs. "
                    "Lose one → others still serve."),
                   ("Replenishment",
                    "Background worker monitors unused pool size. When < threshold, generate next batch."),
               ]),
        _topic("abuse-pipeline",
               "Three-Stage Abuse Pipeline",
               "Submission, periodic re-scan, click-time interstitial. Static domain trust decays.",
               [
                   ("Submission-time scan",
                    "Reputation lookup (Google Safe Browsing, VirusTotal) + ML on creation pattern."),
                   ("Periodic re-scan",
                    "Background queue prioritised by click volume. Catch newly-flagged destinations."),
                   ("Click-time interstitial",
                    "Bloom filter of recently-flagged. On hit, serve a 'this link may be unsafe' page."),
               ]),
    ],
)


# ============================================================================
# SD-05 — Payment Processing System
# ============================================================================
SD_05 = _q(
    "Design a Payment Processing System",
    "Hard",
    "Design Amazon's payment processing pipeline supporting hundreds of millions of customers. Must "
    "handle multi-currency charges + refunds, idempotency, fraud detection, retries, and reconciliation. "
    "PCI DSS compliant. Reliability over throughput.",
    hints=[
        "Idempotency-key on every charge — retries must not double-charge.",
        "Tokenisation: never store raw card data. PCI scope reduction is a primary architectural goal.",
        "Outbox pattern: emit events transactionally with state changes.",
        "Reconciliation runs offline against payment processor batch files.",
        "Saga pattern for multi-step transactions (charge → fulfill → ship).",
    ],
    constraints=[
        "Hundreds of millions of customers",
        "Millions of concurrent transactions",
        "<1% transaction failure rate",
        "Multi-currency (200+)",
        "Strict idempotency",
    ],
    req_func=[
        "Charge with idempotency_key",
        "Refund (full or partial) referencing original charge",
        "Multi-currency, multi-payment-method",
        "Fraud check inline",
        "Retry on transient failure",
        "Async webhooks for eventual outcomes",
    ],
    req_nonfunc=[
        "PCI DSS compliant — no raw card data outside vault",
        "Eventual consistency for non-critical events",
        "Strict consistency for charge/refund records",
        "Auditable — every state change logged",
        "Reconciliation match >99.99%",
    ],
    estimation={
        "tps_steady": "10K transactions/sec global",
        "tps_peak": "Black Friday: 100K/sec",
        "annual_volume": "$1T+",
        "fraud_rate": "<0.1%",
    },
    endpoints=[
        {"method": "POST", "path": "/charges",
         "description": "Create charge", "body": "{idempotency_key, amount_cents, currency, source_token, customer_id}"},
        {"method": "POST", "path": "/refunds", "description": "Refund a charge",
         "body": "{idempotency_key, charge_id, amount_cents}"},
        {"method": "GET", "path": "/charges/{id}", "description": "Charge state lookup"},
    ],
    tables=[
        {"name": "charges",
         "columns": ["id UUID PK", "idempotency_key VARCHAR(64) UNIQUE", "customer_id BIGINT",
                     "amount_cents BIGINT", "currency CHAR(3)", "status VARCHAR(16)",
                     "processor_ref VARCHAR(64)", "created_at BIGINT"]},
        {"name": "refunds",
         "columns": ["id UUID PK", "idempotency_key VARCHAR(64) UNIQUE", "charge_id UUID",
                     "amount_cents BIGINT", "status VARCHAR(16)"]},
        {"name": "ledger_entries",
         "columns": ["id BIGINT PK", "charge_id UUID", "kind VARCHAR(16)", "amount_cents BIGINT",
                     "balance_after BIGINT", "ts BIGINT"]},
    ],
    indexes=["UNIQUE (idempotency_key) on charges and refunds",
             "(customer_id, created_at) on charges",
             "(charge_id, ts) on ledger_entries"],
    hld_desc=(
        "API Gateway → Idempotency Layer (Redis) → Charge Service → Tokenisation Vault → Processor "
        "(Stripe/Adyen). Outbox emits events to Kafka → Fraud Service, Notification Service, "
        "Reconciliation."
    ),
    hld_components=[
        {"name": "API Gateway", "role": "Auth, mTLS to vault, rate-limit"},
        {"name": "Idempotency Layer", "role": "Reject duplicate idempotency_keys"},
        {"name": "Charge Service", "role": "Orchestrate the charge lifecycle"},
        {"name": "Tokenisation Vault", "role": "Card-data isolation, PCI boundary"},
        {"name": "Processor Adapter", "role": "Stripe/Adyen integration"},
        {"name": "Fraud Service", "role": "Real-time scoring; inline reject"},
        {"name": "Outbox + Kafka", "role": "Transactional event emission"},
        {"name": "Reconciliation", "role": "Daily batch match against processor files"},
    ],
    detailed_design={
        "idempotency": (
            "Idempotency key + customer_id + endpoint hashed → Redis lookup. First request acquires the "
            "lock + processes; subsequent return the cached response. TTL 24h."
        ),
        "tokenisation": (
            "Card data sent only to vault (PCI DSS Level 1). Vault returns token; charge service "
            "operates on tokens. Drastically shrinks PCI scope."
        ),
        "outbox_pattern": (
            "Inside the charge transaction, write to charges table AND outbox table. Background relay "
            "tails outbox → publishes to Kafka. Guarantees event emission iff state change committed."
        ),
        "saga_for_orders": (
            "Place order: charge → reserve inventory → ship. If any step fails, compensating actions "
            "(refund, release inventory). State machine per order."
        ),
        "reconciliation": (
            "Daily processor settlement file → batch reconciler diffs against ledger. Any mismatch "
            "raises ops alert; no auto-correction without human review."
        ),
    },
    trade_offs=[
        {"option": "Synchronous vs async fraud check",
         "for_synchronous": "Inline reject of fraudulent transactions",
         "for_async": "No fraud-related latency on the happy path",
         "recommendation": "Hybrid — fast model inline, deep model async with capture+reverse if needed."},
        {"option": "Single processor vs multi-processor",
         "for_single": "Simpler, one integration",
         "for_multi": "Failover, better rates per region, vendor leverage",
         "recommendation": "Multi for scale; abstract behind a Processor interface."},
    ],
    tips=[
        "Idempotency-key is non-negotiable; design it in from request 1.",
        "Tokenisation reduces PCI scope by 10×; do it.",
        "Outbox pattern is the only reliable way to emit events with state changes.",
        "Reconciliation is the safety net; design for it from day one.",
        "Don't try to make distributed transactions ACID — use sagas.",
    ],
    thought_process=[
        "1. Idempotency first — every charge needs a key.",
        "2. Tokenise card data — shrink PCI scope.",
        "3. Outbox for transactional event emission.",
        "4. Fraud: hybrid inline + async.",
        "5. Sagas for multi-step (charge → fulfil → ship).",
        "6. Reconciliation: daily batch vs processor settlement.",
        "7. Multi-processor for failover + regional rates.",
    ],
    tags=["payments", "pci", "idempotency", "saga", "outbox"],
    arch_nodes=[
        {"id": "client", "label": "Client", "type": "client"},
        {"id": "api", "label": "API Gateway", "type": "lb"},
        {"id": "idemp", "label": "Idempotency", "type": "cache"},
        {"id": "charge", "label": "Charge Svc", "type": "server"},
        {"id": "vault", "label": "Token Vault", "type": "service"},
        {"id": "proc", "label": "Processor", "type": "service"},
        {"id": "fraud", "label": "Fraud Svc", "type": "service"},
        {"id": "kafka", "label": "Kafka", "type": "queue"},
        {"id": "db", "label": "Charges DB", "type": "database"},
    ],
    arch_edges=[
        {"source": "client", "target": "api"},
        {"source": "api", "target": "idemp", "label": "dedupe"},
        {"source": "api", "target": "charge"},
        {"source": "charge", "target": "vault", "label": "tokenize"},
        {"source": "charge", "target": "fraud"},
        {"source": "charge", "target": "proc"},
        {"source": "charge", "target": "db"},
        {"source": "charge", "target": "kafka", "label": "outbox"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant C as Client\n"
        "  participant API\n"
        "  participant Ch as Charge Svc\n"
        "  participant V as Vault\n"
        "  participant P as Processor\n"
        "  C->>API: POST /charges (idempotency_key)\n"
        "  API->>Ch: forward\n"
        "  Ch->>V: tokenize card\n"
        "  V-->>Ch: token\n"
        "  Ch->>P: charge\n"
        "  P-->>Ch: success\n"
        "  Ch->>Ch: persist + outbox\n"
        "  Ch-->>C: 201"
    ),
    er_diagram=(
        "erDiagram\n"
        "  CHARGE ||--o{ LEDGER_ENTRY : produces\n"
        "  CHARGE ||--o{ REFUND : has\n"
        "  CHARGE { uuid id PK\n string idem_key\n bigint amount_cents }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Charge request] --> B{Idem key seen?}\n"
        "  B -->|Yes| C[Return cached]\n"
        "  B -->|No| D[Tokenise]\n"
        "  D --> E[Fraud check]\n"
        "  E --> F[Processor]\n"
        "  F --> G[Persist + outbox]"
    ),
    tradeoff_title="Synchronous vs Async fraud check",
    tradeoff_options=[
        {"label": "Synchronous",
         "description": "Inline fraud scoring before processor call.",
         "pros": ["Reject before charging", "Simple flow"],
         "cons": ["Adds latency", "Fraud service is critical-path"]},
        {"label": "Async (post-charge)",
         "description": "Charge first; reverse if fraud flagged after.",
         "pros": ["No latency penalty", "Fraud isn't blocking"],
         "cons": ["Reversal flow needed", "Brief fraud window"]},
    ],
    tradeoff_rec="Hybrid — fast inline model + deep async model with capture+reverse.",
    senior_topics=[
        _topic("idempotency-design",
               "Idempotency-Key Design",
               "Right idempotency-key implementation handles retries WITHOUT double-charging across "
               "client, network, and server failures.",
               [
                   ("Why it's hard",
                    "Client-side retries are inevitable. Without idempotency, network blip = double-charge."),
                   ("Implementation",
                    "Key + customer_id + endpoint hashed. First request acquires lock + processes. Subsequent return cached response."),
                   ("Replay protection",
                    "Hash request body too — same key + DIFFERENT body should fail with 422 (conflict)."),
                   ("TTL",
                    "24h is industry norm. Long enough for client retries; short enough to limit storage."),
               ],
               sources=[{"label": "Stripe — Idempotent Requests",
                         "url": "https://stripe.com/docs/api/idempotent_requests"}]),
        _topic("outbox-pattern",
               "The Outbox Pattern",
               "Atomic event emission with state change. Without it, you lose events or send duplicates.",
               [
                   ("The problem",
                    "After committing a charge, must publish 'charge.created'. If publish fails, downstream is wrong."),
                   ("Solution",
                    "Outbox table inside the same DB. Inside the transaction: insert charge AND outbox row. Background relay tails outbox + publishes."),
                   ("Tradeoff",
                    "Adds DB write per event. Worth it for guaranteed at-least-once delivery."),
                   ("Compaction",
                    "After successful publish, mark outbox row processed. Periodic GC."),
               ]),
    ],
)


# ============================================================================
# SD-06 — Email Notification System
# ============================================================================
SD_06 = _q(
    "Design Amazon Email Notification System",
    "Medium",
    "Design the system that sends transactional emails (order placed, shipped, delivered) for Amazon. "
    "Must handle billions per day, multi-language, rate-limited per recipient, with delivery tracking, "
    "bounce handling, and unsubscribe management.",
    hints=[
        "Decouple submission from delivery — Kafka in front, workers behind.",
        "Template + locale handled separately from delivery. Rendering is a different service.",
        "Bounce + complaint feedback loops are mandatory; suppression list grows from there.",
        "Rate-limit per recipient to avoid mailbox saturation (welcome + 5 alerts in 1 minute → unsub).",
        "ESP integration (SES/SendGrid) is the actual sender — design as a backend, not Postfix.",
    ],
    constraints=[
        "1B+ emails/day",
        "Multi-language (50+)",
        "GDPR/CAN-SPAM compliant",
        "<1% bounce rate target",
        "Per-recipient rate limits",
    ],
    req_func=[
        "Send templated transactional email",
        "Multi-language rendering",
        "Bounce / complaint tracking",
        "Unsubscribe management",
        "Delivery analytics",
        "Per-recipient and per-template rate limiting",
    ],
    req_nonfunc=[
        "At-least-once delivery (with idempotency)",
        "<1% bounce rate",
        "Eventually consistent delivery analytics",
        "GDPR compliant — recipient can opt out",
        "Spam-score safe templates",
    ],
    estimation={
        "emails_per_day": "1B",
        "qps_send": "~12K/sec steady, ~50K/sec peak",
        "templates": "500+ across product lines",
        "suppression_list": "~10M (bounced + unsubscribed)",
    },
    endpoints=[
        {"method": "POST", "path": "/notify",
         "description": "Send templated email",
         "body": "{recipient, template_id, locale, params, idempotency_key}"},
        {"method": "POST", "path": "/templates", "description": "Manage templates"},
        {"method": "POST", "path": "/unsubscribe", "description": "Recipient opt-out"},
        {"method": "POST", "path": "/webhooks/bounces", "description": "ESP bounce callback"},
    ],
    tables=[
        {"name": "templates",
         "columns": ["id VARCHAR PK", "name VARCHAR", "locale CHAR(5)", "subject TEXT", "body TEXT"]},
        {"name": "messages",
         "columns": ["id UUID PK", "template_id VARCHAR", "recipient VARCHAR", "status VARCHAR",
                     "sent_at BIGINT", "delivered_at BIGINT"]},
        {"name": "suppression_list",
         "columns": ["recipient VARCHAR PK", "reason VARCHAR", "added_at BIGINT"]},
    ],
    indexes=["(template_id, sent_at) on messages",
             "(recipient, sent_at) for rate-limit lookup"],
    hld_desc=(
        "API enqueues to Kafka. Renderer worker picks up, fetches template + params, renders. "
        "Suppression check, rate-limit check. ESP adapter dispatches to SES/SendGrid. "
        "Bounce/complaint webhooks update suppression list."
    ),
    hld_components=[
        {"name": "API Server", "role": "Validate + enqueue"},
        {"name": "Kafka", "role": "Durable buffering"},
        {"name": "Renderer Worker", "role": "Template + locale rendering"},
        {"name": "Suppression Check", "role": "Drop messages to opted-out recipients"},
        {"name": "Rate Limiter", "role": "Per-recipient + per-template caps"},
        {"name": "ESP Adapter", "role": "SES/SendGrid integration"},
        {"name": "Webhook Handler", "role": "Bounce/complaint feedback"},
    ],
    detailed_design={
        "templating": "Mustache-like; per-locale variants. Validated for spam-trigger keywords on save.",
        "rate_limiting": "Per-recipient (5/hour) + per-template (limit storms). Token bucket in Redis.",
        "suppression": "Hard bounces → permanent. Complaints → permanent. Soft bounces → temporary, retry.",
        "feedback_loops": "Subscribe to ESP feedback streams; webhook handler updates suppression in real time.",
    },
    trade_offs=[
        {"option": "ESP (SES/SendGrid) vs self-hosted MTA",
         "for_esp": "IP reputation managed, deliverability guaranteed",
         "for_self_hosted": "No vendor cost, full control",
         "recommendation": "ESP — deliverability is the moat, not the message bus."},
        {"option": "Render-then-queue vs queue-then-render",
         "for_render_then_queue": "Smaller queue items, faster send",
         "for_queue_then_render": "Re-render with updated template if needed",
         "recommendation": "Queue-then-render — flexibility for late template changes."},
    ],
    tips=[
        "Don't build your own MTA. ESP handles deliverability.",
        "Idempotency-key on /notify — handles retries without duplicate sends.",
        "Suppression list growth is a slow drag — design for 10M+ entries.",
        "Per-recipient rate limit prevents mailbox flooding (welcome + 5 alerts in a minute = unsub).",
    ],
    thought_process=[
        "1. Decouple via Kafka — submission and delivery are separate.",
        "2. ESP for actual sending; we focus on the orchestration above it.",
        "3. Rate limit per recipient AND per template.",
        "4. Suppression list grows from bounce/complaint feedback.",
        "5. Templating + locales as a separate service — change templates without redeploying senders.",
        "6. Idempotency-key for caller retries.",
    ],
    tags=["email", "notifications", "kafka", "esp"],
    arch_nodes=[
        {"id": "caller", "label": "Service", "type": "client"},
        {"id": "api", "label": "Notify API", "type": "server"},
        {"id": "kafka", "label": "Kafka", "type": "queue"},
        {"id": "render", "label": "Renderer", "type": "server"},
        {"id": "supp", "label": "Suppression", "type": "cache"},
        {"id": "esp", "label": "ESP (SES)", "type": "service"},
        {"id": "wh", "label": "Webhook Handler", "type": "server"},
    ],
    arch_edges=[
        {"source": "caller", "target": "api"},
        {"source": "api", "target": "kafka"},
        {"source": "kafka", "target": "render"},
        {"source": "render", "target": "supp", "label": "check"},
        {"source": "render", "target": "esp", "label": "send"},
        {"source": "esp", "target": "wh", "label": "bounce"},
        {"source": "wh", "target": "supp", "label": "update"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant S as Service\n"
        "  participant API\n"
        "  participant K as Kafka\n"
        "  participant R as Renderer\n"
        "  participant ESP\n"
        "  S->>API: notify\n"
        "  API->>K: enqueue\n"
        "  K-->>R: consume\n"
        "  R->>R: check suppression\n"
        "  R->>ESP: send\n"
        "  ESP-->>R: 250 OK"
    ),
    er_diagram=(
        "erDiagram\n"
        "  TEMPLATE ||--o{ MESSAGE : sent\n"
        "  RECIPIENT ||--o{ MESSAGE : receives\n"
        "  MESSAGE { uuid id\n string status }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Send request] --> B[Kafka]\n"
        "  B --> C[Renderer]\n"
        "  C --> D{Suppressed?}\n"
        "  D -->|Yes| E[Drop]\n"
        "  D -->|No| F[ESP send]"
    ),
    tradeoff_title="ESP vs self-hosted MTA",
    tradeoff_options=[
        {"label": "ESP (SES/SendGrid)",
         "description": "Managed sender service.",
         "pros": ["IP reputation managed", "Deliverability guarantees", "Bounce feedback loops"],
         "cons": ["Vendor cost per email", "Vendor lock-in"]},
        {"label": "Self-hosted MTA",
         "description": "Postfix / Exim on owned IPs.",
         "pros": ["No per-email cost", "Full control"],
         "cons": ["IP warming takes months", "Reputation management is full-time work"]},
    ],
    tradeoff_rec="ESP — deliverability is the moat.",
    senior_topics=[
        _topic("ip-reputation",
               "IP Reputation & Warming",
               "Email deliverability hinges on sending IP reputation. Cold IPs are blackholed by default.",
               [
                   ("Why it matters",
                    "Gmail/Outlook score senders. New IPs are zero-trust; ramp by sending small volumes that increase daily."),
                   ("Warming schedule",
                    "Day 1: 50 emails. Day 2: 100. Doubling for 2-3 weeks until reaching steady-state volume."),
                   ("Recovery from blacklist",
                    "Once blacklisted, warming again can take months. Avoid spammy templates."),
                   ("Why ESPs win",
                    "They've already done the warming and maintain reputation across thousands of customers."),
               ]),
        _topic("suppression-list-design",
               "Suppression List as a First-Class Concern",
               "Bounce and unsubscribe management is a regulatory + deliverability cornerstone.",
               [
                   ("Hard vs soft bounces",
                    "Hard (mailbox doesn't exist) → permanent suppression. Soft (mailbox full) → temporary, retry."),
                   ("Compliance",
                    "GDPR + CAN-SPAM mandate one-click unsubscribe and prompt suppression on request."),
                   ("Storage",
                    "Bloom filter for fast 'definitely allowed' check + DB lookup for borderline. Saves DB hits."),
               ]),
    ],
)


# ============================================================================
# SD-07 — Top Selling Inventory
# ============================================================================
SD_07 = _q(
    "Design Top-Selling Inventory System (Warehouse OMs)",
    "Medium",
    "Warehouses (millions of products each) need a near-real-time view of the top X% fastest-selling "
    "inventory. Must support sliding-window queries, multiple warehouses, and a dashboard with "
    "drill-down. Reads dominate but data is dynamic.",
    hints=[
        "Top-K queries → priority queue / count-min sketch + heavy-hitters.",
        "Sliding window via tumbling buckets (per-minute), aggregate last N for the window.",
        "Per-warehouse partition; cross-warehouse rollup is a separate flow.",
        "Materialise top-K periodically; serve from cache.",
    ],
    constraints=[
        "Millions of products per warehouse",
        "1000s sales/min/warehouse",
        "Multiple warehouses (100s)",
        "Dashboard latency p95 < 1s",
    ],
    req_func=[
        "Show top X% selling products per warehouse",
        "Sliding window (1h, 24h, 7d)",
        "Drill-down by category/brand",
        "Cross-warehouse aggregation",
    ],
    req_nonfunc=[
        "Eventual consistency (60s lag OK)",
        "Dashboard read p95 < 1s",
        "Bounded memory per warehouse stream",
    ],
    estimation={
        "warehouses": "100s",
        "products_per_warehouse": "1M-10M",
        "sales_events_per_sec": "10K global",
        "top_k": "Top 1-5% per warehouse (50K-500K products)",
    },
    endpoints=[
        {"method": "GET", "path": "/warehouses/{id}/top-selling",
         "description": "Top X% over given window", "body": "?window=24h&pct=5"},
        {"method": "GET", "path": "/products/{id}/velocity", "description": "Per-product sales rate"},
    ],
    tables=[
        {"name": "sales_events",
         "columns": ["id BIGINT PK", "warehouse_id INT", "product_id BIGINT", "qty INT", "ts BIGINT"]},
        {"name": "top_k_cache",
         "columns": ["warehouse_id INT", "window_seconds INT", "rank INT", "product_id BIGINT",
                     "count BIGINT", "PRIMARY KEY (warehouse_id, window_seconds, rank)"]},
    ],
    indexes=["(warehouse_id, ts) on sales_events"],
    hld_desc=(
        "Sales events → Kafka → per-warehouse stream processor (Flink) → tumbling-window aggregation → "
        "Top-K cache. Dashboard queries cache; cache pre-computed every 30s per (warehouse, window)."
    ),
    hld_components=[
        {"name": "Sales Ingest", "role": "Receive sales events from POS/order systems"},
        {"name": "Kafka", "role": "Per-warehouse partition"},
        {"name": "Flink Aggregator", "role": "Tumbling-window count per product"},
        {"name": "Top-K Cache (Redis)", "role": "Pre-computed top-K per (warehouse, window)"},
        {"name": "Dashboard API", "role": "Read cache + drill-down queries"},
    ],
    detailed_design={
        "tumbling_windows": "1-minute buckets. 24h window = sum of last 1440 buckets. Sliding via roll-off.",
        "top_k_compute": "Heap of size K per warehouse. Updated on each bucket close.",
        "cross_warehouse": "Periodic batch joins across all warehouses → global top-K.",
        "drill_down": "Pre-aggregate by (warehouse, category) and (warehouse, brand) — extra Flink jobs.",
    },
    trade_offs=[
        {"option": "Exact top-K vs approximate (count-min sketch)",
         "for_exact": "Correct numbers",
         "for_approximate": "Bounded memory, faster updates",
         "recommendation": "Exact — millions of products fits in heap; cardinality isn't the issue."},
    ],
    tips=[
        "Tumbling windows + roll-off = sliding window with bounded state.",
        "Cache pre-computed top-K — read path doesn't recompute.",
        "Drill-down dimensions are extra aggregator jobs, not on-demand queries.",
    ],
    thought_process=[
        "1. Real-time vs near-real-time — 60s lag is acceptable, simplifies a lot.",
        "2. Per-warehouse Kafka partition for scaling.",
        "3. Flink for stream aggregation (windowed counts).",
        "4. Pre-compute top-K every 30s; serve from cache.",
        "5. Drill-down via additional aggregator jobs.",
    ],
    tags=["streaming", "top-k", "windowing", "flink"],
    arch_nodes=[
        {"id": "pos", "label": "POS / Orders", "type": "client"},
        {"id": "kafka", "label": "Kafka", "type": "queue"},
        {"id": "flink", "label": "Flink", "type": "server"},
        {"id": "cache", "label": "Top-K Cache", "type": "cache"},
        {"id": "api", "label": "Dashboard API", "type": "server"},
        {"id": "ui", "label": "OM Dashboard", "type": "client"},
    ],
    arch_edges=[
        {"source": "pos", "target": "kafka"},
        {"source": "kafka", "target": "flink"},
        {"source": "flink", "target": "cache"},
        {"source": "ui", "target": "api"},
        {"source": "api", "target": "cache"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant POS\n  participant K as Kafka\n  participant F as Flink\n"
        "  participant C as Cache\n  participant UI\n"
        "  POS->>K: sale event\n  K-->>F: consume\n"
        "  F->>F: window aggregate\n  F->>C: write top-K\n"
        "  UI->>C: read top-K"
    ),
    er_diagram=(
        "erDiagram\n  WAREHOUSE ||--o{ SALES_EVENT : has\n  SALES_EVENT { bigint warehouse_id\n bigint product_id\n int qty\n bigint ts }"
    ),
    thought_flow="graph TD\n  A[Sale event] --> B[Kafka]\n  B --> C[Flink window]\n  C --> D[Top-K cache]\n  D --> E[Dashboard]",
    tradeoff_title="Exact vs Approximate Top-K",
    tradeoff_options=[
        {"label": "Exact (heap of size K)",
         "description": "Per-warehouse min-heap.",
         "pros": ["Accurate", "Simple"],
         "cons": ["Memory = O(K) per warehouse"]},
        {"label": "Approximate (count-min sketch)",
         "description": "Probabilistic counters with heavy-hitters.",
         "pros": ["Bounded memory", "Constant per-event cost"],
         "cons": ["Approximate", "Tuning required"]},
    ],
    tradeoff_rec="Exact — K is small (50K), heap fits in memory.",
    senior_topics=[
        _topic("sliding-windows",
               "Sliding-Window Aggregation in Flink",
               "Tumbling buckets + roll-off gives sliding-window semantics with bounded state.",
               [
                   ("Tumbling vs sliding",
                    "Tumbling: discrete fixed buckets. Sliding: window slides every event. Tumbling + roll-off approximates sliding with much less state."),
                   ("State management",
                    "Per-warehouse Flink state holds the last N tumbling bucket counts. Roll-off drops the oldest bucket each tick."),
                   ("Watermarks",
                    "Late events past the window are dropped or sent to a late-arrival sink for backfill."),
               ]),
    ],
)


# ============================================================================
# SD-08 — Internal Social Network (Photos)
# ============================================================================
SD_08 = _q(
    "Design Internal Social Network (Photo Feed)",
    "Medium",
    "An internal social network where employees upload photos. Home page shows recent photos from "
    "friends. ~500K users, 1 photo/day each. Friends counts are mostly 20-300 but tail goes to 10K+ "
    "(executive accounts).",
    hints=[
        "Pull (compute on read) vs push (fan-out on write) vs hybrid — the central trade-off.",
        "Pull breaks for users with many friends; push breaks for users with many followers.",
        "Hybrid: push for normal users, pull for celebrity accounts.",
        "Storage: photo blobs in S3, metadata in SQL.",
    ],
    constraints=[
        "500K users", "1 photo/day/user → 500K photos/day",
        "Friend counts: avg ~50, p99 ~3K, max ~10K",
        "1 minute feed delay acceptable",
    ],
    req_func=[
        "Upload photo (with thumbnail, EXIF strip)",
        "Home feed: recent photos from friends, reverse chronological",
        "Friend graph: add/remove friends",
    ],
    req_nonfunc=[
        "Eventually consistent feed (60s lag OK)",
        "Feed read p95 < 500ms",
        "Photo upload non-blocking (upload to S3 in background)",
    ],
    estimation={
        "users": "500K", "photos_per_day": "500K",
        "feed_reads_per_user_per_day": "10",
        "feed_qps": "~60/sec steady, peak 500/sec",
        "storage_per_year": "~180M photos × 1MiB = 180TB",
    },
    endpoints=[
        {"method": "POST", "path": "/photos", "description": "Upload (multipart)"},
        {"method": "GET", "path": "/feed", "description": "Home feed paginated"},
        {"method": "POST", "path": "/friends/{user_id}", "description": "Add friend"},
    ],
    tables=[
        {"name": "users",
         "columns": ["id BIGINT PK", "name VARCHAR", "is_celebrity BOOL"]},
        {"name": "friendships",
         "columns": ["user_a BIGINT", "user_b BIGINT", "created_at BIGINT", "PRIMARY KEY (user_a, user_b)"]},
        {"name": "photos",
         "columns": ["id BIGINT PK", "user_id BIGINT", "url TEXT", "uploaded_at BIGINT"]},
        {"name": "feed_entries",
         "columns": ["user_id BIGINT", "photo_id BIGINT", "ts BIGINT", "PRIMARY KEY (user_id, ts)"]},
    ],
    indexes=["(user_id, ts DESC) on feed_entries", "(user_id, uploaded_at DESC) on photos"],
    hld_desc=(
        "Hybrid push/pull. Photo upload → fan-out worker writes feed_entries to friends' inboxes "
        "(push) for non-celebrities. For celebrities (>1K friends), recipients pull from celebrity "
        "timeline at read time. Feed merge: union of pushed + pulled."
    ),
    hld_components=[
        {"name": "Photo Upload Service", "role": "S3 upload, thumbnail gen"},
        {"name": "Fan-out Worker", "role": "Push to friends' inboxes"},
        {"name": "Feed Service", "role": "Read merged feed"},
        {"name": "Inbox Store", "role": "Per-user feed entries (Cassandra)"},
        {"name": "Photo Metadata DB", "role": "Photo records (Postgres)"},
        {"name": "Blob Store (S3)", "role": "Original + thumbnails"},
    ],
    detailed_design={
        "fanout_strategy": (
            "Non-celebrity (≤1K friends): push to all friends' inboxes. Celebrity (>1K friends): no "
            "push; readers pull on demand. Threshold tuned empirically."
        ),
        "feed_merge": (
            "Read inbox (last N entries) + pull each celebrity friend's last N photos → merge by ts → "
            "paginate. Cache result for 60s."
        ),
        "photo_pipeline": "Upload → S3 → emit event → fan-out worker → write inbox entries.",
    },
    trade_offs=[
        {"option": "Push vs Pull vs Hybrid",
         "for_push": "Fast reads",
         "for_pull": "Cheap writes",
         "recommendation": "Hybrid — push for normals, pull for celebs."},
    ],
    tips=[
        "Hybrid push/pull is the canonical answer; identify the celebrity threshold.",
        "Don't try to make reads strongly consistent — eventual is fine here.",
        "Strip EXIF on upload — privacy default.",
    ],
    thought_process=[
        "1. Estimate scale: 500K × 1 photo/day = 500K photos/day.",
        "2. Friend distribution: most ≤300, a few >10K. Two regimes.",
        "3. Pull breaks for users with 10K friends (10K queries per feed read).",
        "4. Push breaks for users with 10K followers (10K writes per upload).",
        "5. Hybrid: push for normals, pull for celebs.",
        "6. Threshold tunable; instrument to find sweet spot.",
    ],
    tags=["social-feed", "fan-out", "hybrid"],
    arch_nodes=[
        {"id": "client", "label": "Client", "type": "client"},
        {"id": "lb", "label": "LB", "type": "lb"},
        {"id": "upload", "label": "Upload Svc", "type": "server"},
        {"id": "feed", "label": "Feed Svc", "type": "server"},
        {"id": "fan", "label": "Fan-out Worker", "type": "server"},
        {"id": "inbox", "label": "Inbox (Cassandra)", "type": "database"},
        {"id": "meta", "label": "Photo Meta", "type": "database"},
        {"id": "s3", "label": "S3", "type": "service"},
    ],
    arch_edges=[
        {"source": "client", "target": "lb"},
        {"source": "lb", "target": "upload"},
        {"source": "upload", "target": "s3"},
        {"source": "upload", "target": "fan"},
        {"source": "fan", "target": "inbox"},
        {"source": "lb", "target": "feed"},
        {"source": "feed", "target": "inbox"},
        {"source": "feed", "target": "meta"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant U as Uploader\n  participant Up as Upload\n"
        "  participant Fan as Fan-out\n  participant I as Inbox\n  participant V as Viewer\n"
        "  U->>Up: photo\n  Up->>Fan: emit event\n"
        "  Fan->>I: write to friends' inboxes\n"
        "  V->>Up: feed read → inbox + celeb pull"
    ),
    er_diagram=(
        "erDiagram\n  USER ||--o{ FRIENDSHIP : has\n  USER ||--o{ PHOTO : posts\n"
        "  USER ||--o{ FEED_ENTRY : sees\n  PHOTO { bigint id PK\n bigint user_id\n text url }"
    ),
    thought_flow=(
        "graph TD\n  A[Upload] --> B{Celebrity?}\n  B -->|No| C[Push to friends]\n"
        "  B -->|Yes| D[Skip push]\n  E[Feed read] --> F[Inbox + celebrity pull merge]"
    ),
    tradeoff_title="Push vs Pull vs Hybrid",
    tradeoff_options=[
        {"label": "Push (write fan-out)",
         "description": "On upload, write to every friend's inbox.",
         "pros": ["Fast reads", "Simple read path"],
         "cons": ["Write amplification for celebs (10K writes/upload)"]},
        {"label": "Pull (read fan-out)",
         "description": "On read, query each friend's photos.",
         "pros": ["Cheap writes"],
         "cons": ["Read amplification for users with many friends"]},
    ],
    tradeoff_rec="Hybrid — push for normals, pull for celebs.",
    senior_topics=[
        _topic("hybrid-fanout",
               "Hybrid Fan-out at Scale",
               "Twitter and Instagram both use hybrid push/pull to handle the long-tail follower distribution.",
               [
                   ("The threshold question",
                    "Above what follower count do you switch to pull? Empirical: ~1K is the rough crossover where push cost > pull cost on read."),
                   ("Migration",
                    "When a user crosses the threshold, stop pushing AND clean up old inbox entries from their followers (or leave; they'll age out)."),
                   ("Read path simplicity",
                    "Reader merges inbox + pulled-from-celebs at read time. Cache the merge for 60s to amortise."),
               ]),
    ],
)


# ============================================================================
# SD-09 — Video Recommendations
# ============================================================================
SD_09 = _q(
    "Design Video Recommendations (Prime Video)",
    "Hard",
    "Add a recommendation system to a video catalog. Use watch history → recommended videos. The "
    "central decision is real-time recommendations vs pre-computed; both have legitimate trade-offs.",
    hints=[
        "Pre-computed: simpler, latency stable. Stale recommendations.",
        "Real-time: fresh, requires fast model serving.",
        "Hybrid: pre-compute + adjust at request time based on session signals.",
        "Watch events as the source of truth; multiple downstream consumers.",
    ],
    constraints=[
        "100M customers", "Latency for recommendation serving p95 < 50ms",
        "Watch history may have 50K+ events for power users",
        "Multiple recommendation rows (per genre, mood, …)",
    ],
    req_func=[
        "Recommendations on home page",
        "Per-row recommendations (Continue Watching, Trending, etc)",
        "React to new watches within minutes",
        "Survive missing user history (cold start)",
    ],
    req_nonfunc=[
        "p95 < 50ms recommendation read",
        "Eventual consistency (~5 min lag) acceptable",
        "Bounded compute per user (don't scan all watches at request time)",
    ],
    estimation={
        "users": "100M",
        "watches_per_day": "~1B",
        "recommendation_serves_per_day": "~500M",
        "feature_vector_size": "256 dims per video",
    },
    endpoints=[
        {"method": "POST", "path": "/events/watch", "description": "Record watch event",
         "body": "{user_id, video_id, watched_seconds, completed}"},
        {"method": "GET", "path": "/recommendations/{user_id}",
         "description": "Get recommendation rows", "body": "?row=continue_watching"},
    ],
    tables=[
        {"name": "watch_events",
         "columns": ["user_id BIGINT", "video_id BIGINT", "ts BIGINT", "watched_seconds INT", "completed BOOL"]},
        {"name": "user_features",
         "columns": ["user_id BIGINT PK", "feature_vector BLOB", "last_updated_at BIGINT"]},
        {"name": "video_features",
         "columns": ["video_id BIGINT PK", "feature_vector BLOB", "genre VARCHAR"]},
    ],
    indexes=["(user_id, ts DESC) on watch_events"],
    hld_desc=(
        "Watch events → Kafka. Async aggregator updates user feature vector. Recommendation service "
        "reads user vector + retrieves top-K closest video vectors via ANN index (FAISS / vector DB). "
        "Per-row business rules layer applies."
    ),
    hld_components=[
        {"name": "Event Ingest", "role": "Watch event API"},
        {"name": "Kafka", "role": "Durable event log"},
        {"name": "Feature Aggregator", "role": "Update per-user feature vectors"},
        {"name": "Recommendation Service", "role": "Serve recs at request time"},
        {"name": "ANN Index (FAISS)", "role": "Approximate nearest-neighbor lookup"},
        {"name": "Business Rules Layer", "role": "Apply row-specific filtering"},
        {"name": "Catalog Service", "role": "Hydrate video metadata for the response"},
    ],
    detailed_design={
        "user_vector": "Aggregated from watch events: weighted average of watched-video vectors.",
        "ann_lookup": "Top-K nearest video vectors to user vector using HNSW index.",
        "row_specific_rules": "Continue Watching: filter to in-progress. Trending: filter to last-7-day high view count. Per-genre: filter by genre tag.",
        "freshness": "User vector recomputed every 5 minutes if new watches; serves cached otherwise.",
    },
    trade_offs=[
        {"option": "Pre-computed vs real-time",
         "for_pre_computed": "Stable latency, simple",
         "for_real_time": "Fresh signals, can react to current session",
         "recommendation": "Hybrid — pre-compute base, real-time adjust per session."},
    ],
    tips=[
        "Don't scan all watches at request time — pre-aggregate user features.",
        "ANN beats brute-force vector search at >1M items.",
        "Per-row business rules are layered ON TOP of base recommendations, not part of the model.",
    ],
    thought_process=[
        "1. Decision: pre-computed or real-time? Hybrid best of both.",
        "2. Watch events as the substrate — Kafka for durability + multi-consumer.",
        "3. User feature vector aggregated periodically; ANN for retrieval.",
        "4. Row-specific business rules layered after base ranking.",
        "5. Cold start: fall back to popularity / editorial.",
        "6. 50K watches user: feature vector still bounded (256 dims).",
    ],
    tags=["recommendations", "ml", "ann", "vector-search"],
    arch_nodes=[
        {"id": "client", "label": "Client", "type": "client"},
        {"id": "ingest", "label": "Event Ingest", "type": "server"},
        {"id": "kafka", "label": "Kafka", "type": "queue"},
        {"id": "agg", "label": "Aggregator", "type": "server"},
        {"id": "vec", "label": "User Vectors", "type": "cache"},
        {"id": "rec", "label": "Rec Svc", "type": "server"},
        {"id": "ann", "label": "ANN Index", "type": "service"},
        {"id": "rules", "label": "Rules Layer", "type": "server"},
    ],
    arch_edges=[
        {"source": "client", "target": "ingest"},
        {"source": "ingest", "target": "kafka"},
        {"source": "kafka", "target": "agg"},
        {"source": "agg", "target": "vec"},
        {"source": "client", "target": "rec"},
        {"source": "rec", "target": "vec"},
        {"source": "rec", "target": "ann"},
        {"source": "rec", "target": "rules"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant C as Client\n  participant R as Rec Svc\n"
        "  participant V as User Vec\n  participant A as ANN\n"
        "  C->>R: GET /recommendations\n"
        "  R->>V: get user vector\n"
        "  R->>A: top-K nearest\n"
        "  A-->>R: video IDs\n"
        "  R-->>C: hydrated rec rows"
    ),
    er_diagram=(
        "erDiagram\n  USER ||--o{ WATCH_EVENT : watches\n  WATCH_EVENT { bigint user_id\n bigint video_id\n int watched_seconds }"
    ),
    thought_flow=(
        "graph TD\n  A[Watch event] --> B[Kafka]\n  B --> C[Aggregator]\n"
        "  C --> D[User vector]\n  E[Rec request] --> F[ANN lookup]\n  F --> G[Rules]"
    ),
    tradeoff_title="Pre-computed vs Real-time Recommendations",
    tradeoff_options=[
        {"label": "Pre-computed",
         "description": "Batch job nightly produces per-user recommendations.",
         "pros": ["Stable latency", "Simple infrastructure"],
         "cons": ["Stale: no reaction to current session"]},
        {"label": "Real-time",
         "description": "Compute at request time using current state.",
         "pros": ["Fresh signals", "Reacts to in-session behavior"],
         "cons": ["Higher infrastructure cost", "Latency sensitivity"]},
    ],
    tradeoff_rec="Hybrid — pre-compute base, real-time adjust per session.",
    senior_topics=[
        _topic("ann-vs-knn",
               "ANN vs Exact KNN at Scale",
               "Approximate nearest neighbor (HNSW, IVF) trades a tiny accuracy loss for orders-of-magnitude latency wins.",
               [
                   ("Why exact KNN doesn't scale",
                    "Exact KNN over 10M videos is O(N) per query. Even with batching, that's milliseconds per query."),
                   ("HNSW",
                    "Hierarchical navigable small world graphs. O(log N) average query time. Recall@10 ~98% with right tuning."),
                   ("Index management",
                    "Rebuild on new content additions. Hot-swap atomically; old index serves until new is ready."),
               ]),
    ],
)


# ============================================================================
# SD-10 — Online Scrabble (Turn-Based Game)
# ============================================================================
SD_10 = _q(
    "Design Online Scrabble (Turn-Based Game)",
    "Medium",
    "Two-player Scrabble (or any turn-based game) on mobile, asynchronous (a player may take their "
    "turn hours later). Persist game state, validate moves, scale to many concurrent pairs, optionally "
    "support spectators.",
    hints=[
        "Server-authoritative — never trust the client to validate moves.",
        "Game state per game_id; use optimistic locking to prevent double-submits.",
        "Push notifications on opponent's turn.",
        "Spectator mode = read-only fan-out; consider WebSocket or just polling.",
    ],
    constraints=[
        "Async play (turns may be hours/days apart)",
        "100K concurrent active games",
        "Move validation is canonical (dictionary, board adjacency, score)",
    ],
    req_func=[
        "Create game between two players",
        "Submit move (validate + score + persist)",
        "Notify opponent on their turn",
        "Replay game history",
    ],
    req_nonfunc=[
        "Strong consistency on game state",
        "Move latency p95 < 500ms",
        "Push within 5s of opponent's move",
    ],
    estimation={
        "concurrent_games": "100K",
        "moves_per_day": "~1M",
        "qps_steady": "~10/sec writes, ~100/sec reads",
    },
    endpoints=[
        {"method": "POST", "path": "/games", "description": "Create new game"},
        {"method": "POST", "path": "/games/{id}/moves", "description": "Submit move",
         "body": "{tiles, position, direction, version}"},
        {"method": "GET", "path": "/games/{id}", "description": "Game state"},
    ],
    tables=[
        {"name": "games",
         "columns": ["id UUID PK", "player1 BIGINT", "player2 BIGINT", "current_turn BIGINT",
                     "board_state JSON", "version INT"]},
        {"name": "moves",
         "columns": ["game_id UUID", "seq INT", "player_id BIGINT", "tiles JSON", "score INT",
                     "PRIMARY KEY (game_id, seq)"]},
    ],
    indexes=["(player_id, game_id) for finding a player's games"],
    hld_desc=(
        "Stateless API server; game state in DB with optimistic version. Move validation server-side. "
        "On valid move: increment version, persist move, push to opponent."
    ),
    hld_components=[
        {"name": "Game API", "role": "Create / move / state endpoints"},
        {"name": "Move Validator", "role": "Dictionary check + adjacency + scoring"},
        {"name": "Game DB", "role": "Game + move records"},
        {"name": "Push Service", "role": "Notify opponent"},
        {"name": "Dictionary Service", "role": "Word validity lookup"},
    ],
    detailed_design={
        "optimistic_lock": "Move includes expected version; server CAS-updates. Conflict → 409.",
        "validation": "Server only. Client pre-checks for UX but server is authoritative.",
        "spectators": "Polling for v1. WebSocket if/when justified.",
    },
    trade_offs=[
        {"option": "Server-authoritative vs trust-client",
         "for_server_authoritative": "Anti-cheat",
         "for_trust_client": "Lower server cost",
         "recommendation": "Server-authoritative — never trust the client for move validity."},
    ],
    tips=[
        "Server validates EVERYTHING. Client checks are UX only.",
        "Version field on game state for optimistic concurrency.",
        "Push for opponent's turn; polling fallback.",
    ],
    thought_process=[
        "1. Async game — state lives in DB, not in-memory session.",
        "2. Server-authoritative move validation.",
        "3. Optimistic locking via version field.",
        "4. Push on opponent's turn.",
        "5. Spectators: read-only fan-out, polling first.",
    ],
    tags=["turn-based", "game-state", "server-authoritative"],
    arch_nodes=[
        {"id": "p1", "label": "Player 1", "type": "client"},
        {"id": "p2", "label": "Player 2", "type": "client"},
        {"id": "api", "label": "Game API", "type": "server"},
        {"id": "val", "label": "Validator", "type": "service"},
        {"id": "db", "label": "Game DB", "type": "database"},
        {"id": "push", "label": "Push", "type": "service"},
    ],
    arch_edges=[
        {"source": "p1", "target": "api"},
        {"source": "api", "target": "val"},
        {"source": "api", "target": "db"},
        {"source": "api", "target": "push"},
        {"source": "push", "target": "p2"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant P1\n  participant API\n  participant DB\n  participant Push\n  participant P2\n"
        "  P1->>API: submit move (version=5)\n"
        "  API->>API: validate\n"
        "  API->>DB: CAS update\n"
        "  API->>Push: notify P2\n"
        "  Push-->>P2: your turn"
    ),
    er_diagram=(
        "erDiagram\n  GAME ||--o{ MOVE : has\n"
        "  GAME { uuid id PK\n bigint player1\n bigint player2\n int version }"
    ),
    thought_flow=(
        "graph TD\n  A[Submit move] --> B[Validate]\n  B --> C{Valid?}\n"
        "  C -->|No| D[400]\n  C -->|Yes| E[CAS persist]\n  E --> F[Notify opponent]"
    ),
    tradeoff_title="Server-authoritative vs Client-trust",
    tradeoff_options=[
        {"label": "Server-authoritative",
         "description": "Server validates and computes everything.",
         "pros": ["Anti-cheat", "Single source of truth"],
         "cons": ["Server CPU per move"]},
        {"label": "Client-trust",
         "description": "Client computes; server records.",
         "pros": ["Lower server cost"],
         "cons": ["Cheaters trivially win", "Bug in client = corrupt game state"]},
    ],
    tradeoff_rec="Server-authoritative — always.",
    senior_topics=[
        _topic("optimistic-concurrency",
               "Optimistic Concurrency for Async Games",
               "Two clients submit moves on same state — version-based CAS prevents lost-update bugs.",
               [
                   ("The bug",
                    "P1 reads version 5, computes move. Network delay. P2 reads version 5, computes move. Both submit; one is lost."),
                   ("CAS",
                    "Each move includes expected version. Server: UPDATE … WHERE version=5; rejects if mismatch. Client retries with fresh state."),
                   ("Idempotency",
                    "Move ID + game ID = idempotency key. Retry with same ID → same outcome."),
               ]),
    ],
)


# ============================================================================
# SD-11 — Note-Taking App (multi-competency)
# ============================================================================
SD_11 = _q(
    "Design Note-Taking / ToDo App",
    "Medium",
    "Phone-based note-taking app. Start simple: store text notes. Progressively layer on structure "
    "(checklists), full-text search, reminders, multi-device sync, and offline-first edits with "
    "conflict resolution.",
    hints=[
        "Start dumb: SQLite local + REST API.",
        "Search: SQLite FTS; server-side full-text search at 10K+ notes.",
        "Reminders: per-note schedule; server-side cron triggers push.",
        "Multi-device: CRDT-friendly note model OR last-write-wins with merge.",
        "Offline-first: optimistic writes locally; sync on connection.",
    ],
    constraints=[
        "Mobile-first",
        "Up to 10K notes per user",
        "Multiple devices (~3 typical)",
        "Offline edits possible",
    ],
    req_func=[
        "CRUD notes",
        "Checklist items inside notes",
        "Full-text search",
        "Reminders / push notifications",
        "Multi-device sync",
        "Offline editing",
    ],
    req_nonfunc=[
        "Eventual consistency across devices",
        "Local-first writes (no internet → still works)",
        "Sync within seconds when online",
    ],
    estimation={
        "users": "10M", "notes_per_user_avg": "100",
        "devices_per_user": "3",
        "sync_events_per_day": "~50M",
    },
    endpoints=[
        {"method": "POST", "path": "/notes", "description": "Create note"},
        {"method": "PATCH", "path": "/notes/{id}", "description": "Update note (with version)"},
        {"method": "GET", "path": "/notes", "description": "List notes (paginated)"},
        {"method": "GET", "path": "/search", "description": "Full-text search", "body": "?q=…"},
        {"method": "POST", "path": "/sync", "description": "Push deltas, get server changes"},
    ],
    tables=[
        {"name": "notes",
         "columns": ["id UUID PK", "user_id BIGINT", "title TEXT", "body TEXT", "version INT",
                     "updated_at BIGINT", "deleted_at BIGINT"]},
        {"name": "reminders",
         "columns": ["id BIGINT PK", "note_id UUID", "fire_at BIGINT", "fired BOOL"]},
    ],
    indexes=["(user_id, updated_at) on notes",
             "(fire_at) on reminders for cron scan",
             "FTS index on (title, body)"],
    hld_desc=(
        "Local-first SQLite cache; sync layer talks to backend. Server: stateless API + Postgres. "
        "Reminders: scheduler scans for fire_at <= now; emits push events."
    ),
    hld_components=[
        {"name": "Mobile App", "role": "Local SQLite + sync layer"},
        {"name": "API Server", "role": "CRUD + sync endpoints"},
        {"name": "Sync Service", "role": "Delta merge"},
        {"name": "FTS (Postgres or ES)", "role": "Search index"},
        {"name": "Reminder Scheduler", "role": "Cron + push"},
        {"name": "Push Service", "role": "APNs / FCM"},
    ],
    detailed_design={
        "offline_first": (
            "Local writes immediately. Sync layer queues changes; flushes when online. Server returns "
            "deltas since client's sync_token."
        ),
        "conflict_resolution": (
            "Last-write-wins on title; for body, surface conflict to user with both versions if "
            "concurrent edits detected."
        ),
        "search": "Postgres pg_trgm + GIN index for v1; Elasticsearch when user count justifies.",
        "reminders": "Per-minute cron polls for fire_at <= now. For >10M users, shard by user_id range.",
    },
    trade_offs=[
        {"option": "LWW vs CRDT for body merge",
         "for_lww": "Simple, predictable",
         "for_crdt": "Lossless concurrent edits",
         "recommendation": "LWW + conflict surface for v1; CRDT if power users emerge."},
    ],
    tips=[
        "Local-first is the only sane design for offline tolerance.",
        "Sync via delta tokens, not full state.",
        "FTS in Postgres before Elasticsearch — saves a system to operate.",
    ],
    thought_process=[
        "1. SQLite locally; REST API; eventual sync.",
        "2. Notes have versions; sync via delta tokens.",
        "3. FTS in Postgres for v1.",
        "4. Reminders: cron scan + push.",
        "5. Multi-device: LWW + conflict surfacing.",
        "6. Offline-first means local writes always work.",
    ],
    tags=["offline-first", "sync", "notes", "fts"],
    arch_nodes=[
        {"id": "app", "label": "Mobile App", "type": "client"},
        {"id": "api", "label": "API", "type": "server"},
        {"id": "db", "label": "Postgres", "type": "database"},
        {"id": "fts", "label": "FTS", "type": "service"},
        {"id": "cron", "label": "Reminder Cron", "type": "service"},
        {"id": "push", "label": "Push", "type": "service"},
    ],
    arch_edges=[
        {"source": "app", "target": "api"},
        {"source": "api", "target": "db"},
        {"source": "api", "target": "fts"},
        {"source": "cron", "target": "db"},
        {"source": "cron", "target": "push"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant A as App\n  participant API\n  participant DB\n"
        "  A->>A: local write\n  A->>API: sync (delta)\n"
        "  API->>DB: persist\n  API-->>A: server changes since token"
    ),
    er_diagram=(
        "erDiagram\n  USER ||--o{ NOTE : has\n  NOTE ||--o{ REMINDER : has\n"
        "  NOTE { uuid id PK\n text title\n text body\n int version }"
    ),
    thought_flow="graph TD\n  A[Write] --> B[Local SQLite]\n  B --> C{Online?}\n  C -->|Yes| D[Sync]\n  C -->|No| E[Queue]",
    tradeoff_title="LWW vs CRDT for note body",
    tradeoff_options=[
        {"label": "Last-Write-Wins",
         "description": "Most-recent timestamped edit wins.",
         "pros": ["Simple", "Predictable"],
         "cons": ["Loses concurrent edits silently"]},
        {"label": "CRDT",
         "description": "Automatic merge of concurrent text edits.",
         "pros": ["No data loss"],
         "cons": ["Complex implementation", "Larger payloads"]},
    ],
    tradeoff_rec="LWW + conflict surfacing for v1; CRDT later if needed.",
    senior_topics=[
        _topic("offline-first-sync",
               "Offline-First Sync via Sync Tokens",
               "Sync token bookkeeping is the core of any sync system.",
               [
                   ("The token",
                    "Opaque per-device. Server returns new token + deltas since old token."),
                   ("Three-way merge",
                    "Server tracks per-record versions. Client provides expected version; server returns server's version on conflict."),
                   ("Bandwidth",
                    "Delta sync only — never full-state."),
               ]),
    ],
)


# ============================================================================
# SD-12 — Parking Lot System
# ============================================================================
SD_12 = _q(
    "Design Parking Lot System (Distributed)",
    "Medium",
    "Automated parking-lot management for 1,000 lots nationwide. Multiple pricing models per lot, "
    "lot-full sensors, nightly usage reports, and an OPS dashboard. Distributed deployment with "
    "regional sharding.",
    hints=[
        "Each lot is a tenant; partition by lot_id.",
        "Pricing strategy is per-lot; persisted as configuration.",
        "Lot-full sign reads a cached count; eventual consistency OK.",
        "Reports aggregate from a daily ETL pipeline; not a live query.",
    ],
    constraints=[
        "1,000 lots", "100 spots/lot avg",
        "100K daily entries across all lots",
        "Lot-full sign refresh ≤ 30s",
    ],
    req_func=[
        "Issue ticket on entry",
        "Charge on exit (per lot's pricing rules)",
        "Lot-full status query",
        "Daily usage report per lot",
        "OPS dashboard for ops/owners",
    ],
    req_nonfunc=[
        "<5s entry/exit ticket processing",
        "Eventually consistent lot-full count (30s)",
        "99.9% uptime per lot",
    ],
    estimation={
        "lots": "1000",
        "entries_per_day": "100K",
        "qps_steady": "~3-5/sec entries; bursts at rush hour",
    },
    endpoints=[
        {"method": "POST", "path": "/lots/{lot_id}/entries", "description": "Issue ticket on entry"},
        {"method": "POST", "path": "/lots/{lot_id}/exits", "description": "Process exit + charge"},
        {"method": "GET", "path": "/lots/{lot_id}/availability", "description": "Free-spot count"},
        {"method": "GET", "path": "/lots/{lot_id}/reports", "description": "Daily usage"},
    ],
    tables=[
        {"name": "lots",
         "columns": ["id BIGINT PK", "name VARCHAR", "spots_total INT", "pricing_strategy_id BIGINT"]},
        {"name": "tickets",
         "columns": ["id BIGINT PK", "lot_id BIGINT", "entered_at BIGINT", "exited_at BIGINT",
                     "amount_paid_cents INT"]},
        {"name": "pricing_strategies",
         "columns": ["id BIGINT PK", "kind VARCHAR", "config JSON"]},
    ],
    indexes=["(lot_id, entered_at) on tickets"],
    hld_desc=(
        "Per-lot stateless workers; central pricing config. Lot-full count materialised in Redis from "
        "ticket events. Daily ETL produces reports overnight."
    ),
    hld_components=[
        {"name": "Lot Edge Service", "role": "Per-lot ticket entry/exit"},
        {"name": "Pricing Service", "role": "Strategy lookup + compute"},
        {"name": "Lot State Cache (Redis)", "role": "Live spot count per lot"},
        {"name": "Sign Service", "role": "Drives the 'lot full' display"},
        {"name": "Reporting Pipeline", "role": "Daily ETL → analytics DB"},
        {"name": "OPS Dashboard", "role": "Owner-facing reports"},
    ],
    detailed_design={
        "pricing": "Strategy pattern: HourlyRate, EarlyBird, EventDay. Each lot has one default + overrides.",
        "lot_full": "Redis counter, decremented on entry, incremented on exit. Sign polls every 30s.",
        "reports": "ETL job nightly: aggregate tickets by hour/day; output to Athena/BigQuery for OPS.",
        "leak_handling": "If car stays past midnight (early-bird violation), apply hourly catch-up rate.",
    },
    trade_offs=[
        {"option": "Per-lot vs central queue",
         "for_per_lot": "Lot can operate offline briefly",
         "for_central": "Simpler ops, central reporting",
         "recommendation": "Per-lot edge service syncing centrally — survives flaky lot internet."},
    ],
    tips=[
        "Per-lot edge — survive flaky on-site internet.",
        "Pricing strategy as data, not code; one config table.",
        "Reports are async; don't run on the live ticketing path.",
    ],
    thought_process=[
        "1. Per-lot tenancy; partition by lot_id.",
        "2. Pricing as data — one config per lot.",
        "3. Lot-full is eventual; sign refreshes every 30s.",
        "4. Reports overnight; never on the hot path.",
        "5. Edge survives flaky internet (local cache + sync).",
    ],
    tags=["multi-tenant", "pricing-strategy", "iot"],
    arch_nodes=[
        {"id": "kiosk", "label": "Lot Kiosk", "type": "client"},
        {"id": "edge", "label": "Edge Service", "type": "server"},
        {"id": "central", "label": "Central API", "type": "server"},
        {"id": "redis", "label": "Lot Cache", "type": "cache"},
        {"id": "db", "label": "Tickets DB", "type": "database"},
        {"id": "etl", "label": "ETL", "type": "service"},
    ],
    arch_edges=[
        {"source": "kiosk", "target": "edge"},
        {"source": "edge", "target": "central"},
        {"source": "central", "target": "redis"},
        {"source": "central", "target": "db"},
        {"source": "db", "target": "etl"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant E as Entry\n  participant Edge\n  participant API\n  participant DB\n"
        "  E->>Edge: request ticket\n  Edge->>API: issue ticket\n  API->>DB: persist\n  API-->>Edge: ticket id"
    ),
    er_diagram=(
        "erDiagram\n  LOT ||--o{ TICKET : has\n  LOT ||--|| PRICING_STRATEGY : uses\n"
        "  TICKET { bigint id\n bigint lot_id\n bigint entered_at\n bigint exited_at }"
    ),
    thought_flow="graph TD\n  A[Car enters] --> B[Edge]\n  B --> C[Issue ticket]\n  C --> D[Update count]\n  E[Car exits] --> F[Pricing lookup]",
    tradeoff_title="Per-lot edge vs Central hub",
    tradeoff_options=[
        {"label": "Per-lot edge service",
         "description": "Each lot runs a local service.",
         "pros": ["Resilient to lot internet outage", "Low latency"],
         "cons": ["Edge ops complexity"]},
        {"label": "Central hub",
         "description": "All lots talk to one regional API.",
         "pros": ["Simpler ops"],
         "cons": ["Internet outage = lot offline"]},
    ],
    tradeoff_rec="Per-lot edge with central sync.",
    senior_topics=[
        _topic("multi-tenant-pricing",
               "Pricing as Data (Strategy Per Lot)",
               "Avoid hard-coding pricing. One config table; new pricing models = one row.",
               [
                   ("Strategy pattern",
                    "Each lot's pricing_strategy_id points to a row with kind + config blob. Code dispatches by kind."),
                   ("Adding a new pricing model",
                    "Implement a strategy class; add the row. No schema change, no deploy per lot."),
                   ("Auditability",
                    "Versioned config — change history per lot lets you replay any historical bill."),
               ]),
    ],
)


# ============================================================================
# SD-13 — Simple Twitter
# ============================================================================
SD_13 = _q(
    "Design Simple Twitter (Tweet + Timeline)",
    "Hard",
    "Two operations: post a tweet, fetch a time-ordered timeline of people I follow. Scale: 100M+ "
    "users, billions of tweets, hot-fan-out for celebrity accounts.",
    hints=[
        "Push (write fan-out) for normal users; pull for celebs. Hybrid is the canonical answer.",
        "Inbox per user; entries are tweet IDs + ts.",
        "Cassandra for inbox (write-heavy, time-series).",
        "Cache hot user timelines.",
    ],
    constraints=[
        "100M+ users", "Avg 200 tweets/day total per user",
        "p99 timeline read < 200ms", "Eventual consistency OK",
    ],
    req_func=[
        "Post a tweet (text + optional media)",
        "Fetch reverse-chronological timeline of followed users",
        "Follow / unfollow",
    ],
    req_nonfunc=[
        "Eventually consistent — tweet shows up within seconds for followers",
        "p99 timeline read < 200ms",
        "Sustain hot account spikes (celeb posts during event)",
    ],
    estimation={
        "users": "100M", "follows_avg": "200", "celebs": "10K",
        "tweets_per_day": "1B",
        "timeline_reads_per_day": "10B",
        "qps_post": "10K/sec", "qps_read": "100K/sec",
    },
    endpoints=[
        {"method": "POST", "path": "/tweets", "description": "Post tweet"},
        {"method": "GET", "path": "/timeline", "description": "Fetch timeline"},
        {"method": "POST", "path": "/follow/{user_id}", "description": "Follow user"},
    ],
    tables=[
        {"name": "users",
         "columns": ["id BIGINT PK", "username VARCHAR", "follower_count BIGINT"]},
        {"name": "tweets",
         "columns": ["id BIGINT PK", "user_id BIGINT", "body TEXT", "created_at BIGINT"]},
        {"name": "follows",
         "columns": ["follower_id BIGINT", "followee_id BIGINT", "PRIMARY KEY (follower_id, followee_id)"]},
        {"name": "user_timeline",
         "columns": ["user_id BIGINT", "ts BIGINT", "tweet_id BIGINT", "PRIMARY KEY (user_id, ts)"]},
    ],
    indexes=["(user_id, ts DESC) on user_timeline (Cassandra clustering)",
             "(user_id, created_at DESC) on tweets"],
    hld_desc=(
        "Hybrid push/pull. Tweet → fan-out to follower inboxes for non-celeb users; celebs stay in own "
        "timeline and readers pull on demand. Inboxes in Cassandra. Cache hot timelines."
    ),
    hld_components=[
        {"name": "Tweet Service", "role": "Post + fan-out trigger"},
        {"name": "Fan-out Worker", "role": "Push to follower inboxes"},
        {"name": "Timeline Service", "role": "Read merged inbox + celeb pulls"},
        {"name": "Cassandra Inbox", "role": "Per-user time-ordered tweet IDs"},
        {"name": "Tweet Store", "role": "Tweet body lookup"},
        {"name": "Cache (Redis)", "role": "Hot timelines"},
    ],
    detailed_design={
        "fanout_threshold": "1K followers. Below: push. Above: skip push, pull at read.",
        "timeline_read": "Read inbox last N entries + pull each celeb-followee's last N → merge by ts → cache 60s.",
        "tweet_store": "Cassandra (partition by user_id). Lookup by tweet_id resolved via user_id + ts (tweet IDs are Snowflake-style with user prefix)."
    },
    trade_offs=[
        {"option": "Push vs Pull vs Hybrid (same as SD-08, larger scale)",
         "for_push": "Fast read, simpler",
         "for_pull": "Cheap write",
         "recommendation": "Hybrid — push for normals, pull for celebs."},
    ],
    tips=[
        "Hybrid is the answer; identify celeb threshold.",
        "Cassandra inbox; Snowflake tweet IDs.",
        "Cache hot user timelines aggressively.",
    ],
    thought_process=[
        "1. Read-heavy (10:1). Caches and inboxes.",
        "2. Hybrid push/pull at celeb threshold.",
        "3. Cassandra for time-ordered inboxes.",
        "4. Snowflake IDs for ordered, sharded tweet IDs.",
        "5. Hot timeline cache (60s TTL).",
    ],
    tags=["social", "fan-out", "timeline", "cassandra"],
    arch_nodes=[
        {"id": "client", "label": "Client", "type": "client"},
        {"id": "lb", "label": "LB", "type": "lb"},
        {"id": "tweet", "label": "Tweet Svc", "type": "server"},
        {"id": "fan", "label": "Fan-out", "type": "server"},
        {"id": "tl", "label": "Timeline Svc", "type": "server"},
        {"id": "cass", "label": "Cassandra", "type": "database"},
        {"id": "cache", "label": "Redis", "type": "cache"},
    ],
    arch_edges=[
        {"source": "client", "target": "lb"},
        {"source": "lb", "target": "tweet"},
        {"source": "tweet", "target": "fan"},
        {"source": "fan", "target": "cass"},
        {"source": "lb", "target": "tl"},
        {"source": "tl", "target": "cache"},
        {"source": "cache", "target": "cass", "label": "miss"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n  participant U as User\n  participant T as Tweet Svc\n"
        "  participant F as Fan-out\n  participant I as Inbox\n  participant V as Viewer\n"
        "  U->>T: post tweet\n  T->>F: emit\n  F->>I: write to followers\n  V->>I: read timeline"
    ),
    er_diagram="erDiagram\n  USER ||--o{ TWEET : posts\n  USER ||--o{ FOLLOW : has\n  USER ||--o{ TIMELINE_ENTRY : sees",
    thought_flow="graph TD\n  A[Post] --> B{Celeb?}\n  B -->|No| C[Push to followers]\n  B -->|Yes| D[Skip push]\n  E[Read] --> F[Inbox + celeb pull]",
    tradeoff_title="Push vs Pull (recap with scale)",
    tradeoff_options=[
        {"label": "Pure push",
         "description": "Fan out every tweet to every follower's inbox.",
         "pros": ["Fast reads"],
         "cons": ["Celeb tweets cause 10M write spikes"]},
        {"label": "Pure pull",
         "description": "Readers query each followee on demand.",
         "pros": ["Cheap writes"],
         "cons": ["Slow reads at the long tail of follow counts"]},
    ],
    tradeoff_rec="Hybrid push/pull at ~1K threshold.",
    senior_topics=[
        _topic("snowflake-ids",
               "Twitter Snowflake IDs",
               "64-bit IDs encoding timestamp + datacenter + worker + sequence. Sortable, sharded, no central coordinator.",
               [
                   ("The encoding",
                    "41 bits timestamp + 10 bits worker + 12 bits sequence. ~280 years of IDs at 4096 IDs/ms/worker."),
                   ("Why not UUID",
                    "UUID isn't sortable; queries by time range are scans. Snowflake is monotonic per worker."),
                   ("Why not auto-increment",
                    "Auto-increment requires a central DB or coordinator. Snowflake decentralizes."),
               ]),
    ],
)


# ============================================================================
# SD-14 — API Rate Limiter
# ============================================================================
SD_14 = _q(
    "Design API Rate Limiter (Distributed)",
    "Hard",
    "Rate limit an API across a cluster. Different limits per endpoint, per user, per API key. Must "
    "scale horizontally and handle traffic bursts. Discuss algorithm choices and centralised vs "
    "distributed counters.",
    hints=[
        "Token bucket and sliding window are the two algorithms to know.",
        "Centralised (Redis) is simpler; per-host is faster but inaccurate at boundaries.",
        "Hybrid: per-host bucket with periodic central reconciliation.",
        "Throttled responses: 429 + Retry-After header.",
    ],
    constraints=[
        "Multiple limit dimensions (user, key, endpoint)",
        "100K+ QPS through the limiter",
        "Limit accuracy ~99% (perfect not required)",
        "Sub-ms decision latency",
    ],
    req_func=[
        "Reject requests over limit with 429",
        "Per-endpoint, per-user, per-API-key limits",
        "Burst tolerance via token bucket",
        "Configurable limits without code change",
    ],
    req_nonfunc=[
        "<1ms decision latency",
        "Eventually consistent counters across hosts",
        "Survive Redis failure (degraded local mode)",
    ],
    estimation={
        "qps": "100K", "users_active": "1M",
        "redis_ops_per_sec": "100K (one INCR per request)",
    },
    endpoints=[
        {"method": "GET", "path": "/api/*", "description": "Limiter is middleware; transparent."},
        {"method": "GET", "path": "/admin/limits", "description": "Configure limits per dimension"},
    ],
    tables=[
        {"name": "limit_rules",
         "columns": ["id BIGINT PK", "dimension VARCHAR", "key VARCHAR", "limit_per_sec INT"]},
    ],
    indexes=["(dimension, key) on limit_rules"],
    hld_desc=(
        "Limiter middleware in front of each API host. Decision: local cache check + Redis INCR. "
        "On exceed: 429 + Retry-After. Config in DB; loaded into memory on each host with refresh."
    ),
    hld_components=[
        {"name": "API Host", "role": "Host running app + limiter middleware"},
        {"name": "Limiter Middleware", "role": "Token-bucket decision per request"},
        {"name": "Redis Cluster", "role": "Centralised counters"},
        {"name": "Config Service", "role": "Limit rules"},
        {"name": "Metrics", "role": "Track limit hits, false positives"},
    ],
    detailed_design={
        "algorithm": "Token bucket: each (dimension, key) has a bucket. Refill at limit_per_sec. Request takes 1 token; reject if 0.",
        "redis_ops": "Lua script: GET tokens, if >0 DECR + return success, else return reject. Atomic.",
        "fallback": "On Redis failure, fall back to per-host limits (lower-fidelity but available).",
        "configuration": "Hot reload: poll config service every 30s; in-memory cache of rules.",
    },
    trade_offs=[
        {"option": "Centralised (Redis) vs Distributed (per-host)",
         "for_centralised": "Accurate, single source of truth",
         "for_distributed": "Sub-ms, no Redis dependency",
         "recommendation": "Centralised primary + distributed fallback."},
        {"option": "Token bucket vs Sliding window",
         "for_token_bucket": "Burst-friendly, simple",
         "for_sliding_window": "Smoother under sustained load",
         "recommendation": "Token bucket — interview standard, easier to explain."},
    ],
    tips=[
        "Atomic INCR via Lua scripts on Redis.",
        "Don't be perfectly accurate — 99% is fine; eventual consistency is OK.",
        "429 + Retry-After header is the contract.",
        "Hierarchical limits — endpoint → user → key, fail at the first.",
    ],
    thought_process=[
        "1. Multiple dimensions: per-endpoint, per-user, per-key.",
        "2. Token bucket — burst-friendly, simple.",
        "3. Centralised counters in Redis with atomic ops.",
        "4. Per-host fallback if Redis is unavailable.",
        "5. 429 + Retry-After response.",
        "6. Config service for hot reload.",
    ],
    tags=["rate-limiting", "redis", "token-bucket"],
    arch_nodes=[
        {"id": "client", "label": "Client", "type": "client"},
        {"id": "host", "label": "API Host", "type": "server"},
        {"id": "limiter", "label": "Limiter", "type": "service"},
        {"id": "redis", "label": "Redis Counter", "type": "cache"},
        {"id": "config", "label": "Config Svc", "type": "server"},
    ],
    arch_edges=[
        {"source": "client", "target": "host"},
        {"source": "host", "target": "limiter"},
        {"source": "limiter", "target": "redis"},
        {"source": "limiter", "target": "config"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n  participant C\n  participant L as Limiter\n  participant R as Redis\n"
        "  C->>L: request\n  L->>R: INCR (Lua)\n  R-->>L: count\n  alt over limit\n  L-->>C: 429\n  else\n  L-->>C: 200\n  end"
    ),
    er_diagram="erDiagram\n  LIMIT_RULE { bigint id PK\n string dimension\n string key\n int limit_per_sec }",
    thought_flow="graph TD\n  A[Request] --> B[Limiter]\n  B --> C[Redis INCR]\n  C --> D{Over?}\n  D -->|Yes| E[429]\n  D -->|No| F[Pass]",
    tradeoff_title="Centralised vs Distributed counters",
    tradeoff_options=[
        {"label": "Centralised (Redis)",
         "description": "Every host queries shared Redis.",
         "pros": ["Accurate", "Single source"],
         "cons": ["Redis is critical-path", "Network hop adds latency"]},
        {"label": "Distributed (per-host)",
         "description": "Each host enforces local quota.",
         "pros": ["Sub-ms", "No external dependency"],
         "cons": ["Inaccurate at host boundaries", "Total quota = limit × hosts"]},
    ],
    tradeoff_rec="Centralised primary + distributed fallback for Redis outages.",
    senior_topics=[
        _topic("token-bucket-vs-sliding",
               "Token Bucket vs Sliding Window",
               "Two competing algorithms. Token bucket is burst-friendly; sliding window smooths.",
               [
                   ("Token bucket",
                    "Bucket of N tokens, refilled R tokens/sec. Each request takes 1. Allows bursts up to N."),
                   ("Sliding window",
                    "Count requests in last second (bucket-aggregated or log-based). No bursts beyond limit."),
                   ("Choosing",
                    "User-facing APIs: token bucket (burst tolerance helps UX). Backend RPC: sliding window (predictable load)."),
               ]),
    ],
)


# ============================================================================
# SD-15 — Product Page URL Service
# ============================================================================
SD_15 = _q(
    "Design Product Page URL Service",
    "Medium",
    "Generate product page URLs for the entire e-commerce catalog (e.g. amazon.com/d/harry-potter/ASIN). "
    "Slug-based URLs, deterministic per product, redirect old URLs to new, A/B-testable. SEO-friendly, "
    "sub-100ms lookups.",
    hints=[
        "Slug derived from product title; deterministic but may need disambiguation.",
        "Cache the slug → ASIN map aggressively.",
        "URL change: old URL must 301 to new permanently.",
        "Localisation: per-locale slug versions.",
    ],
    constraints=[
        "100M+ products in catalog",
        "Sub-100ms slug → product lookup",
        "Slug uniqueness within (locale, slug)",
    ],
    req_func=[
        "Generate slug from product title",
        "Resolve slug → product",
        "Redirect old slugs to current",
        "Per-locale slugs",
    ],
    req_nonfunc=[
        "<100ms lookup p99",
        "Eventually consistent slug updates",
        "SEO-stable: 301 not 302 for moved slugs",
    ],
    estimation={
        "products": "100M", "lookups_per_sec": "1M",
        "storage": "~10GB slug map (compressed)",
    },
    endpoints=[
        {"method": "GET", "path": "/d/{slug}/{asin}", "description": "Product page (redirect or render)"},
        {"method": "POST", "path": "/admin/slugs", "description": "Generate / update slug"},
    ],
    tables=[
        {"name": "slugs",
         "columns": ["slug VARCHAR", "locale CHAR(5)", "asin VARCHAR(16)", "is_current BOOL",
                     "PRIMARY KEY (slug, locale)"]},
        {"name": "products",
         "columns": ["asin VARCHAR(16) PK", "title TEXT", "current_slug VARCHAR"]},
    ],
    indexes=["UNIQUE (slug, locale) on slugs", "(asin, locale) on slugs for redirect lookups"],
    hld_desc=(
        "Edge cache → CDN. Lookup: slug → asin via Redis (warm). Old slugs marked is_current=false; "
        "edge sees that and 301s to current slug."
    ),
    hld_components=[
        {"name": "Edge / CDN", "role": "Cache slug pages aggressively"},
        {"name": "Slug Service", "role": "Resolve slug → ASIN"},
        {"name": "Redis", "role": "Hot slug → ASIN map"},
        {"name": "Slug DB", "role": "Authoritative store"},
        {"name": "Slug Generator", "role": "Title → slug, dedupe via suffix"},
    ],
    detailed_design={
        "slug_gen": "lowercase, dash-separate, strip stopwords. Disambiguate duplicates with -2, -3 suffix or include ASIN suffix.",
        "redirects": "Old slugs in slugs table with is_current=false + asin pointer. Edge serves 301 → /d/{current_slug}/{asin}.",
        "localisation": "Per-locale slug variants. Same ASIN can have multiple slugs (en, de, fr).",
    },
    trade_offs=[
        {"option": "Slug-only vs slug + ASIN",
         "for_slug_only": "Cleaner URLs",
         "for_slug_plus_asin": "Self-disambiguating; slug change doesn't break links",
         "recommendation": "Slug + ASIN suffix — Amazon's pattern; resilient to renames."},
    ],
    tips=[
        "Slug + ASIN — link survives title change.",
        "301 (not 302) for moved slugs — SEO equity preserved.",
        "Per-locale slugs; share ASIN across locales.",
        "Cache aggressively at edge — 99%+ hit ratio target.",
    ],
    thought_process=[
        "1. URL format: /d/{slug}/{asin}. Slug is decorative; ASIN is the real ID.",
        "2. Slug generated from title; disambiguation via suffix or ASIN.",
        "3. Old slugs 301 to current.",
        "4. Per-locale slug variants.",
        "5. Edge cache for hot products; Redis for warm; DB for cold.",
    ],
    tags=["urls", "slugs", "seo", "redirects"],
    arch_nodes=[
        {"id": "browser", "label": "Browser", "type": "client"},
        {"id": "cdn", "label": "CDN", "type": "cache"},
        {"id": "svc", "label": "Slug Svc", "type": "server"},
        {"id": "redis", "label": "Redis", "type": "cache"},
        {"id": "db", "label": "Slug DB", "type": "database"},
    ],
    arch_edges=[
        {"source": "browser", "target": "cdn"},
        {"source": "cdn", "target": "svc", "label": "miss"},
        {"source": "svc", "target": "redis"},
        {"source": "redis", "target": "db", "label": "miss"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n  participant B\n  participant CDN\n  participant S as Slug Svc\n"
        "  B->>CDN: GET /d/old-slug/ASIN\n  CDN->>S: miss\n"
        "  S-->>CDN: 301 → /d/new-slug/ASIN\n  CDN-->>B: 301"
    ),
    er_diagram="erDiagram\n  PRODUCT ||--o{ SLUG : has\n  SLUG { string slug\n string locale\n string asin\n bool is_current }",
    thought_flow="graph TD\n  A[Lookup slug] --> B{Current?}\n  B -->|Yes| C[Render]\n  B -->|No| D[301 to current]",
    tradeoff_title="Slug-only vs slug + ASIN",
    tradeoff_options=[
        {"label": "Slug only",
         "description": "/d/harry-potter",
         "pros": ["Cleanest URL"],
         "cons": ["Renames break old links", "Dedup hard at scale"]},
        {"label": "Slug + ASIN",
         "description": "/d/harry-potter/B0001",
         "pros": ["Self-disambiguating", "Renames don't break"],
         "cons": ["Less clean visual"]},
    ],
    tradeoff_rec="Slug + ASIN — Amazon's pattern; resilient.",
    senior_topics=[
        _topic("301-management",
               "301 Redirect Hygiene at Scale",
               "Each slug change generates a 301. Over time the chain grows; collapse it.",
               [
                   ("301 chains",
                    "If A→B→C, browsers follow chain serially. Crawlers de-prioritise long chains."),
                   ("Compaction",
                    "Daily job: rewrite each historical slug → current slug directly. Drop intermediate hops."),
                   ("Sitemaps",
                    "Only current slugs in sitemap; let old ones decay through redirect."),
               ]),
    ],
)


# ============================================================================
# SD-16 — Amazon eCommerce Backend
# ============================================================================
SD_16 = _q(
    "Design Amazon eCommerce Backend",
    "Hard",
    "Backend for the buy-now flow on a major e-commerce site. Browse → cart → checkout → place order. "
    "Must handle traffic spikes (Prime Day), limited-quantity items, and provide consistent pricing/"
    "inventory across the journey.",
    hints=[
        "Browse is read-heavy; cache + CDN aggressively.",
        "Cart is session state; reasonable to keep in Redis with persistence.",
        "Checkout is a saga: reserve inventory, charge, place order, ship.",
        "Limited-quantity items: optimistic locking on inventory.",
        "Spike handling: pre-warm caches, queue overflow rather than reject.",
    ],
    constraints=[
        "100M+ MAU",
        "Black Friday / Prime Day: 10× steady-state",
        "Sub-second product page render",
        "Strict pricing consistency (no over-discount)",
    ],
    req_func=[
        "Product browse / search / detail",
        "Add to cart, modify cart",
        "Checkout (address, payment, place order)",
        "Order tracking",
    ],
    req_nonfunc=[
        "Sub-second product page p95",
        "Pricing consistent throughout journey",
        "Inventory accurate within seconds",
        "Spike-tolerant (10× Prime Day)",
    ],
    estimation={
        "page_views_per_day": "10B",
        "orders_per_day": "10M",
        "qps_browse": "120K", "qps_orders": "120/sec",
        "peak_qps_orders": "1200/sec (10×)",
    },
    endpoints=[
        {"method": "GET", "path": "/products/{asin}", "description": "Product detail"},
        {"method": "POST", "path": "/cart", "description": "Add to cart"},
        {"method": "POST", "path": "/checkout", "description": "Place order"},
        {"method": "GET", "path": "/orders/{id}", "description": "Order tracking"},
    ],
    tables=[
        {"name": "products",
         "columns": ["asin VARCHAR PK", "title TEXT", "price_cents INT", "inventory INT"]},
        {"name": "carts",
         "columns": ["user_id BIGINT PK", "items JSON", "updated_at BIGINT"]},
        {"name": "orders",
         "columns": ["id UUID PK", "user_id BIGINT", "items JSON", "total_cents BIGINT",
                     "status VARCHAR", "created_at BIGINT"]},
    ],
    indexes=["(user_id, created_at) on orders"],
    hld_desc=(
        "Browse: CDN + Redis cache → Postgres (sharded). Cart: Redis with persistence. Checkout: saga "
        "service orchestrating inventory reserve + payment + order persist + ship."
    ),
    hld_components=[
        {"name": "Browse Service", "role": "Catalog read API"},
        {"name": "Cart Service", "role": "Session-bound cart state"},
        {"name": "Checkout Saga", "role": "Order placement orchestration"},
        {"name": "Inventory Service", "role": "Optimistic-locked stock"},
        {"name": "Payment Service", "role": "(see SD-05)"},
        {"name": "Order Service", "role": "Order persistence + lifecycle"},
        {"name": "Shipping Adapter", "role": "Hand off to logistics"},
    ],
    detailed_design={
        "spike_handling": "Pre-warm caches with predicted-popular SKUs. Queue checkout requests; never drop. Apply a virtual waiting room for checkout if needed.",
        "inventory_lock": "Optimistic CAS on inventory column. On conflict, retry with fresh count.",
        "saga_compensation": "If charge succeeds but ship fails: refund + release inventory + email customer.",
    },
    trade_offs=[
        {"option": "Strong vs eventual inventory consistency",
         "for_strong": "Never oversell",
         "for_eventual": "Faster, simpler",
         "recommendation": "Strong via optimistic CAS — overselling is reputational damage."},
    ],
    tips=[
        "Cache product pages at CDN; invalidate on price/inventory change.",
        "Saga pattern for checkout — local transactions + compensations.",
        "Optimistic CAS on inventory; pessimistic locking is too slow at QPS.",
        "Pre-warm + queue for spikes; never drop a checkout under load.",
    ],
    thought_process=[
        "1. Browse: read-heavy, cache aggressively.",
        "2. Cart: session state in Redis.",
        "3. Checkout: saga (reserve → charge → order → ship).",
        "4. Inventory: optimistic CAS.",
        "5. Spike handling: pre-warm + queue.",
        "6. Compensations on saga failure.",
    ],
    tags=["e-commerce", "saga", "inventory", "spikes"],
    arch_nodes=[
        {"id": "client", "label": "Client", "type": "client"},
        {"id": "cdn", "label": "CDN", "type": "cache"},
        {"id": "browse", "label": "Browse", "type": "server"},
        {"id": "cart", "label": "Cart", "type": "server"},
        {"id": "saga", "label": "Checkout Saga", "type": "server"},
        {"id": "inv", "label": "Inventory", "type": "server"},
        {"id": "pay", "label": "Payment", "type": "service"},
        {"id": "order", "label": "Orders", "type": "server"},
    ],
    arch_edges=[
        {"source": "client", "target": "cdn"},
        {"source": "cdn", "target": "browse", "label": "miss"},
        {"source": "client", "target": "cart"},
        {"source": "client", "target": "saga"},
        {"source": "saga", "target": "inv"},
        {"source": "saga", "target": "pay"},
        {"source": "saga", "target": "order"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n  participant C\n  participant S as Saga\n  participant I as Inv\n"
        "  participant P as Payment\n  participant O as Orders\n"
        "  C->>S: checkout\n  S->>I: reserve inventory\n  I-->>S: ok\n"
        "  S->>P: charge\n  P-->>S: success\n  S->>O: place order\n  O-->>C: 201"
    ),
    er_diagram=(
        "erDiagram\n  USER ||--o{ ORDER : places\n  ORDER ||--o{ ORDER_ITEM : contains\n"
        "  ORDER { uuid id PK\n bigint total_cents\n string status }"
    ),
    thought_flow=(
        "graph TD\n  A[Cart → checkout] --> B[Reserve inventory]\n  B --> C{OK?}\n"
        "  C -->|Yes| D[Charge]\n  D --> E[Place order]\n  E --> F[Ship]\n"
        "  C -->|No| G[Reject - out of stock]"
    ),
    tradeoff_title="Strong vs Eventual Inventory Consistency",
    tradeoff_options=[
        {"label": "Strong (CAS)",
         "description": "Optimistic CAS on inventory column.",
         "pros": ["Never oversell"],
         "cons": ["Conflicts under high contention"]},
        {"label": "Eventual",
         "description": "Async inventory updates with reconciliation.",
         "pros": ["Higher throughput"],
         "cons": ["Risk of overselling; reputational damage"]},
    ],
    tradeoff_rec="Strong CAS — overselling hurts brand more than 1% conflicts hurt UX.",
    senior_topics=[
        _topic("checkout-saga",
               "Checkout as a Saga",
               "Multi-step orchestration with compensations. ACID across services is impossible; sagas are the practical alternative.",
               [
                   ("Steps",
                    "1) Reserve inventory. 2) Charge payment. 3) Persist order. 4) Trigger shipping."),
                   ("Compensations",
                    "If step 3 fails after step 2: refund + release inventory + notify customer. Compensations must be idempotent."),
                   ("Orchestration vs choreography",
                    "Orchestration (one saga service) is easier to debug. Choreography (event-driven) is more resilient but harder to reason about."),
               ]),
    ],
)


# ============================================================================
# SD-17 — In-Stock Count Display
# ============================================================================
SD_17 = _q(
    "Design In-Stock Count Display ('Only 3 left!')",
    "Easy",
    "Show on product page: 'Only N left!' when stock is below threshold (10). UI / API / cache / "
    "synchronisation with inventory backend. The simplicity of the prompt hides the inventory-"
    "consistency challenge.",
    hints=[
        "Inventory count is high-write; display is high-read. Cache aggressively but with TTL.",
        "Stale display is fine for 30-60s; an oversold order is not.",
        "Real inventory check happens at add-to-cart and checkout, not display.",
        "Bucket counts: '10+' for high stock, exact number below threshold.",
    ],
    constraints=[
        "100M product pages/day",
        "Sub-100ms display p95",
        "Consistency at checkout, eventual at display",
    ],
    req_func=[
        "Display 'Only N left!' below threshold",
        "Display 'In Stock' above",
        "Refresh within 60s of inventory change",
    ],
    req_nonfunc=[
        "Eventual consistency at display (60s lag OK)",
        "Strict consistency at checkout (CAS)",
        "Cache hit ratio > 95%",
    ],
    estimation={
        "page_views_per_day": "10B",
        "qps_display": "120K",
        "qps_inventory_writes": "100/sec",
    },
    endpoints=[
        {"method": "GET", "path": "/products/{asin}/availability", "description": "Display string"},
        {"method": "POST", "path": "/inventory/decrement", "description": "Internal: on order placement"},
    ],
    tables=[
        {"name": "inventory",
         "columns": ["asin VARCHAR PK", "count INT", "version BIGINT", "updated_at BIGINT"]},
    ],
    indexes=[],
    hld_desc=(
        "Inventory writes update Postgres + emit event. Cache layer (Redis) listens, updates display "
        "string. CDN edge caches the display string with 30-60s TTL."
    ),
    hld_components=[
        {"name": "Inventory DB", "role": "Authoritative count"},
        {"name": "Display Cache (Redis)", "role": "Display strings keyed by ASIN"},
        {"name": "Display API", "role": "Read cache → fallback to DB"},
        {"name": "Inventory Event Bus", "role": "Updates fan to cache"},
        {"name": "Edge / CDN", "role": "30s TTL on display string"},
    ],
    detailed_design={
        "display_logic": "If count < 10: 'Only {count} left!'. If 10-50: 'In stock'. If 50+: 'In stock'.",
        "cache_invalidation": "Inventory write → event → cache update. CDN TTL ensures eventual freshness.",
        "checkout_consistency": "At add-to-cart and at checkout, CAS against current count. Display can lie; checkout cannot.",
    },
    trade_offs=[
        {"option": "Bucket display vs exact count",
         "for_bucket": "Less specific; tolerates more staleness",
         "for_exact": "Urgency for the user",
         "recommendation": "Exact below 10 (urgency); bucket above (no value-add)."},
    ],
    tips=[
        "Display is best-effort; checkout is strict.",
        "30-60s cache TTL is fine — inventory changes are rare per ASIN.",
        "Don't update display synchronously on every inventory write — bucket events.",
    ],
    thought_process=[
        "1. Read-heavy display + low-write inventory.",
        "2. Cache aggressively at edge + Redis.",
        "3. 30-60s TTL acceptable for display.",
        "4. Checkout consistency via CAS — display can lie temporarily.",
        "5. Bucket display above 10 to reduce noise.",
    ],
    tags=["caching", "inventory", "ui-data"],
    arch_nodes=[
        {"id": "browser", "label": "Browser", "type": "client"},
        {"id": "cdn", "label": "CDN", "type": "cache"},
        {"id": "api", "label": "Display API", "type": "server"},
        {"id": "redis", "label": "Display Cache", "type": "cache"},
        {"id": "db", "label": "Inventory DB", "type": "database"},
        {"id": "events", "label": "Event Bus", "type": "queue"},
    ],
    arch_edges=[
        {"source": "browser", "target": "cdn"},
        {"source": "cdn", "target": "api", "label": "miss"},
        {"source": "api", "target": "redis"},
        {"source": "redis", "target": "db", "label": "miss"},
        {"source": "db", "target": "events"},
        {"source": "events", "target": "redis", "label": "invalidate"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n  participant U\n  participant CDN\n  participant API\n  participant R as Redis\n"
        "  U->>CDN: GET /availability\n  CDN-->>U: cached display"
    ),
    er_diagram="erDiagram\n  INVENTORY { string asin PK\n int count\n bigint version }",
    thought_flow="graph TD\n  A[Inventory write] --> B[Event]\n  B --> C[Update cache]\n  D[User views page] --> E[Read cache]\n  E --> F[Display]",
    tradeoff_title="Exact count vs Bucket display",
    tradeoff_options=[
        {"label": "Exact ('Only 3 left')",
         "description": "Show actual count below threshold.",
         "pros": ["Urgency", "Specific"],
         "cons": ["Risk of staleness embarrassment"]},
        {"label": "Bucket ('Only a few left')",
         "description": "Categorical messages.",
         "pros": ["Tolerates staleness", "Simpler"],
         "cons": ["Less compelling"]},
    ],
    tradeoff_rec="Exact below threshold for urgency; bucket above.",
    senior_topics=[
        _topic("write-through-vs-cache-invalidation",
               "Write-Through vs Cache Invalidation",
               "Inventory updates need to propagate to display. Write-through is consistent but tightly coupled; invalidation is loosely coupled with eventual consistency.",
               [
                   ("Write-through",
                    "Update DB + cache atomically. Consistent but requires distributed transaction or two-phase commit."),
                   ("Invalidation",
                    "Update DB + emit event → cache subscriber updates. Asynchronous; brief window of staleness."),
                   ("Recommendation",
                    "Invalidation for display; write-through is over-engineering for this UX-only data."),
               ]),
    ],
)


# Aggregate all SDQs in order
_BASE_SDQS = [SD_01, SD_02, SD_03, SD_04, SD_05, SD_06, SD_07, SD_08, SD_09,
              SD_10, SD_11, SD_12, SD_13, SD_14, SD_15, SD_16, SD_17]


def _load_more():
    """Pick up extra SDQs from `sd_more/` siblings. Each module there
    exports a `PAYLOAD` dict shaped exactly like a `_q(...)` return value."""
    import importlib
    import pkgutil
    extras = []
    try:
        from . import sd_more as _pkg  # type: ignore
    except Exception:
        return extras
    for mod_info in pkgutil.iter_modules(_pkg.__path__):
        mod = importlib.import_module(f"{_pkg.__name__}.{mod_info.name}")
        payload = getattr(mod, "PAYLOAD", None)
        if isinstance(payload, dict):
            extras.append(payload)
    return extras


ALL_SDQS = _BASE_SDQS + _load_more()
