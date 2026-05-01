"""Airbnb system design question. Loaded automatically via
`sd_questions._load_more` because this module exposes `PAYLOAD`."""
from __future__ import annotations

from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design Airbnb",
    "Hard",
    "Design Airbnb: a global lodging marketplace where hosts list properties and guests search, book, "
    "and stay. Must support geospatial + filter search with ranking, calendar availability, a "
    "hold-then-confirm booking flow with TTL, dynamic pricing, post-stay reviews, host onboarding and "
    "verification, trust + safety, photo delivery via CDN, and host-guest messaging. Focus on the "
    "search-to-booking hot path and the concurrency story around overlapping date requests.",
    hints=[
        "Two-sided marketplace — model hosts and guests as distinct user kinds with different lifecycles.",
        "Search is geospatial (map bounds) PLUS filters (price, beds, amenities) PLUS ranking — needs an "
        "inverted index, not just a geo index. Elasticsearch with geo_bounding_box + filters wins.",
        "Calendar availability is the bookability source of truth. Day-granularity bitmap or per-night "
        "rows; both work, the choice drives query shape.",
        "Booking is hold-then-confirm with a TTL on the hold so abandoned checkouts don't block inventory.",
        "Concurrency on overlapping dates is the senior signal: pessimistic (row lock per night) vs "
        "optimistic (compare-and-set on availability version). Spell out the tradeoff.",
        "Dynamic pricing is read at search time; computed offline or near-real-time, not synchronously.",
        "Reviews are post-stay only and double-blind — both sides write before either sees the other.",
        "Trust + safety is a cross-cutting concern: ID verification, payments risk, fraud signals.",
    ],
    constraints=[
        "150M+ guests, 4M+ hosts, 7M+ active listings globally",
        "~2M searches/sec peak across regions; ~1M bookings/day",
        "Search p99 < 500ms over geo + filters + ranking",
        "Bookings must never double-book a single night — strong consistency on the calendar",
        "Hold TTL ~10–15 minutes; payment confirmation within that window",
        "Photos served globally — CDN required for sub-100ms first byte",
        "Reviews unlocked only after stay completes",
    ],
    req_func=[
        "Host onboarding: list a property with photos, price, calendar, house rules, verification",
        "Guest search: map-bounds + filters (price, beds, dates, amenities) with ranked results",
        "View listing detail with photos, calendar, reviews, host profile",
        "Book a date range: hold inventory, charge payment, confirm reservation",
        "Cancel / modify booking with policy-aware refund",
        "Post-stay reviews (guest reviews host; host reviews guest) — double-blind",
        "Host calendar management — block dates, set custom prices, sync iCal feeds",
        "Host-guest messaging pre- and post-booking",
        "Dynamic / smart pricing recommendations for hosts",
        "Trust + safety: ID verification, payment fraud screening, abuse reports",
    ],
    req_nonfunc=[
        "Search p99 < 500ms; listing detail p99 < 300ms",
        "Booking: strong consistency — zero double-bookings",
        "99.95% availability for browse + search; 99.99% for the booking write path",
        "Read-heavy: ~99:1 search-to-book ratio. Cache aggressively above the database.",
        "Photos delivered via CDN with regional edge caching",
        "GDPR-aware retention; PCI-compliant payment isolation",
        "Eventual consistency for review aggregates and ranking signals",
    ],
    estimation={
        "active_listings": "7M",
        "active_guests": "150M",
        "searches_per_day": "~150B (~2M/sec peak)",
        "bookings_per_day": "~1M",
        "photos_per_listing": "~30 average → ~200M photos total",
        "media_storage": "~600TB across responsive variants",
        "review_volume": "~1M reviews/day (post-stay)",
        "qps_search": "~2M peak / ~500K steady",
        "qps_booking": "~12 peak (very low; bursty by region)",
    },
    endpoints=[
        {"method": "GET", "path": "/search",
         "description": "Geospatial + filtered listing search",
         "body": "?bbox=lat1,lng1,lat2,lng2&checkin&checkout&guests&price_min&price_max&amenities[]&sort"},
        {"method": "GET", "path": "/listings/{id}",
         "description": "Listing detail (photos, calendar slice, reviews, host)"},
        {"method": "GET", "path": "/listings/{id}/availability",
         "description": "Calendar slice for date range",
         "body": "?from=YYYY-MM-DD&to=YYYY-MM-DD"},
        {"method": "POST", "path": "/bookings/hold",
         "description": "Reserve inventory with TTL; returns hold_id",
         "body": "{listing_id, checkin, checkout, guests}"},
        {"method": "POST", "path": "/bookings/{hold_id}/confirm",
         "description": "Charge payment + finalise booking",
         "body": "{payment_method_id}"},
        {"method": "POST", "path": "/bookings/{id}/cancel",
         "description": "Cancel and apply refund per policy"},
        {"method": "POST", "path": "/listings",
         "description": "Host creates a listing",
         "body": "{title, address, beds, amenities, base_price, photos:[]}"},
        {"method": "POST", "path": "/listings/{id}/photos",
         "description": "Presigned S3 URL for direct photo upload"},
        {"method": "POST", "path": "/reviews",
         "description": "Submit a post-stay review (double-blind)",
         "body": "{booking_id, rating, body}"},
        {"method": "POST", "path": "/threads/{listing_id}/messages",
         "description": "Host-guest messaging — defers to chat design"},
    ],
    tables=[
        {"name": "users",
         "columns": ["id BIGINT PK", "email VARCHAR UNIQUE", "kind VARCHAR(8)",
                     "verified_at BIGINT", "rating FLOAT", "created_at BIGINT"]},
        {"name": "listings",
         "columns": ["id BIGINT PK", "host_id BIGINT", "title VARCHAR", "lat DOUBLE", "lng DOUBLE",
                     "geohash VARCHAR(8)", "city VARCHAR", "country VARCHAR(2)", "beds INT",
                     "max_guests INT", "amenities JSONB", "base_price_cents INT", "currency CHAR(3)",
                     "status VARCHAR", "created_at BIGINT", "rating_avg FLOAT", "review_count INT"]},
        {"name": "calendar",
         "columns": ["listing_id BIGINT", "night DATE", "available BOOL", "price_cents INT",
                     "min_stay INT", "version BIGINT", "PRIMARY KEY (listing_id, night)"]},
        {"name": "bookings",
         "columns": ["id BIGINT PK", "listing_id BIGINT", "guest_id BIGINT", "checkin DATE",
                     "checkout DATE", "total_cents INT", "currency CHAR(3)", "status VARCHAR",
                     "hold_expires_at BIGINT", "created_at BIGINT", "confirmed_at BIGINT"]},
        {"name": "payments",
         "columns": ["id BIGINT PK", "booking_id BIGINT", "amount_cents INT", "status VARCHAR",
                     "provider VARCHAR", "provider_ref VARCHAR", "created_at BIGINT"]},
        {"name": "reviews",
         "columns": ["id BIGINT PK", "booking_id BIGINT", "author_id BIGINT", "subject_id BIGINT",
                     "kind VARCHAR(8)", "rating INT", "body TEXT", "submitted_at BIGINT",
                     "published_at BIGINT"]},
        {"name": "photos",
         "columns": ["id BIGINT PK", "listing_id BIGINT", "url VARCHAR", "ord INT",
                     "width INT", "height INT", "created_at BIGINT"]},
        {"name": "host_verifications",
         "columns": ["host_id BIGINT PK", "id_doc_status VARCHAR", "selfie_status VARCHAR",
                     "payout_account_status VARCHAR", "verified_at BIGINT"]},
        {"name": "messages",
         "columns": ["thread_id BIGINT", "ts BIGINT", "msg_id UUID", "user_id BIGINT", "body TEXT",
                     "PRIMARY KEY (thread_id, ts, msg_id)"]},
    ],
    indexes=[
        "(geohash, status) on listings — coarse pre-filter",
        "(city, status) on listings",
        "(listing_id, night) on calendar — primary key, range scan friendly",
        "(guest_id, created_at DESC) on bookings",
        "(host_id, status) on listings",
        "(booking_id) on reviews — one per side per booking",
        "(listing_id, ord) on photos",
    ],
    hld_desc=(
        "Search served by Elasticsearch over a denormalised listing index (geo_point + filters + "
        "ranking signals). Listing detail fan-reads listing metadata, a calendar slice, and review "
        "aggregates, fronted by Redis. Booking flows through a stateful Booking Service that creates "
        "a hold (TTL) on the calendar, locks per-night rows, then confirms via the Payment Service. "
        "Photos go via presigned S3 + CDN. Reviews are double-blind with a 14-day reveal window. "
        "Host onboarding integrates with an Identity / KYC provider. Messaging is a thin chat surface "
        "that defers to the chat design. Pricing is computed by an offline / near-real-time pipeline "
        "and read at search time."
    ),
    hld_components=[
        {"name": "Mobile / Web Clients", "role": "Search, browse, book, message, review"},
        {"name": "API Gateway", "role": "Auth, rate-limit, region-route"},
        {"name": "Search Service", "role": "Geo + filter + ranked search via Elasticsearch"},
        {"name": "Listing Service", "role": "CRUD on listings; emits index update events"},
        {"name": "Calendar Service", "role": "Per-night availability + price; source of truth for bookability"},
        {"name": "Booking Service", "role": "Hold-confirm flow, concurrency control, cancellation"},
        {"name": "Payment Service", "role": "PCI-isolated charge + payout to host"},
        {"name": "Pricing Service", "role": "Smart-pricing recommendations and per-night override"},
        {"name": "Review Service", "role": "Double-blind post-stay reviews with reveal job"},
        {"name": "Photo Pipeline", "role": "Presigned upload, responsive variants, CDN distribution"},
        {"name": "Identity / KYC", "role": "Host verification, ID + selfie + payout account"},
        {"name": "Trust + Safety", "role": "Fraud signals, abuse reports, account holds"},
        {"name": "Messaging", "role": "Host-guest chat — defers to chat design"},
        {"name": "Search Index (Elasticsearch)", "role": "Denormalised listings with geo_point + amenities"},
        {"name": "Object Store + CDN", "role": "S3 origin, edge cache for photos"},
        {"name": "Event Bus (Kafka)", "role": "Listing changes, booking events, review reveals"},
    ],
    detailed_design={
        "search_with_filters_and_ranking": (
            "Elasticsearch index per region with a denormalised listing document: geo_point, city, "
            "country, beds, max_guests, amenities (keyword set), base_price_cents, rating_avg, "
            "review_count, host_score, instant_book. Query is a bool with geo_bounding_box (the map "
            "viewport) plus term/range filters (dates → availability flag from a precomputed lookup, "
            "price range, amenities). Ranking blends quality (rating_avg + review_count smoothed by "
            "Bayesian average), price-fit to the user, distance-from-bbox-centre, host responsiveness, "
            "and personalisation (recent searches, language). Date filtering is handled by a "
            "precomputed 'available_in_window' boolean on the doc, refreshed every few minutes from "
            "the calendar; the source of truth is still calendar at booking time."
        ),
        "calendar_availability": (
            "Per-night row in calendar(listing_id, night, available, price_cents, version). Range "
            "scan SELECT WHERE listing_id=X AND night BETWEEN checkin AND checkout-1 AND available=true "
            "decides bookability. Hosts edit by upserting row(s); iCal sync ingests external bookings "
            "(VRBO etc.) by writing available=false rows. The calendar is the single source of truth; "
            "the search index is a stale-tolerant projection."
        ),
        "hold_then_confirm_flow": (
            "Step 1 (hold): Booking Service starts a transaction, locks the calendar rows for "
            "[checkin, checkout-1], verifies all available=true and min_stay constraints, then sets "
            "available=false and writes a booking row in status='held' with hold_expires_at = now + "
            "10min. Returns hold_id. Step 2 (confirm): client posts payment_method; Payment Service "
            "charges the card; on success Booking Service flips status to 'confirmed'. On payment "
            "failure or timeout, a sweeper releases the hold by setting available=true and booking "
            "status='abandoned'. The TTL prevents abandoned checkout from permanently blocking dates."
        ),
        "concurrency_pessimistic_vs_optimistic": (
            "Pessimistic (default): SELECT ... FOR UPDATE on the per-night rows inside the hold "
            "transaction. Two concurrent guests serialise; the second sees rows already taken and "
            "fails fast. Strong but holds locks for the duration of the hold transaction (sub-100ms). "
            "Optimistic: read rows + version, attempt UPDATE ... WHERE version=read_version. If the "
            "rowcount mismatches, retry once or fail. Cheaper at low contention; needs explicit retry "
            "ladder. Recommendation: pessimistic for the hold (rare contention, short critical "
            "section), optimistic only if you must scale beyond a single primary; with a partitioned "
            "calendar by listing_id even the pessimistic path scales linearly."
        ),
        "dynamic_pricing": (
            "Smart Pricing recommends per-night prices to hosts using demand signals (search volume, "
            "competitor prices, lead time, day-of-week, events). A nightly batch + streaming top-up "
            "writes recommended prices; hosts opt in to auto-apply or accept manually. At search time "
            "the calendar's price_cents is authoritative — never compute pricing synchronously per "
            "search. Surge / event-driven multipliers get applied by the pricing pipeline, not the "
            "booking path."
        ),
        "post_stay_reviews": (
            "Reviews can only be written after checkout. Both sides have a 14-day window. Reviews "
            "are double-blind: stored with submitted_at but published_at = NULL until either both "
            "sides submit OR the window closes (then any single submitted review is revealed). A "
            "reveal job processes the queue daily. After publish, the listing's rating_avg + "
            "review_count are recomputed and republished to the search index (eventual)."
        ),
        "host_onboarding_and_verification": (
            "New host registers → uploads government ID + selfie → KYC provider (Onfido/Persona) "
            "verifies; payout account (bank or Stripe Connect) is verified separately. Listings can "
            "be drafted before verification but cannot accept bookings until host is verified. "
            "Verification status surfaces on the listing detail (verified-host badge)."
        ),
        "trust_and_safety": (
            "Pre-booking signals: device fingerprint, account age, payment-method risk score, IP "
            "geolocation mismatch with stated travel. Risky bookings route to manual review or "
            "require additional verification. Post-booking abuse reports write into a moderation "
            "queue with SLA. Cross-cutting account holds disable booking + payouts atomically."
        ),
        "photos_via_cdn": (
            "Client requests presigned S3 PUT URL → uploads original. S3 ObjectCreated triggers a "
            "transcoder that generates responsive variants (320/640/960/1280/1920 webp + a thumbnail) "
            "and a low-quality blur placeholder for instant rendering. Variants are served via CDN "
            "(CloudFront/Akamai) keyed by content hash for permanent caching. The listing document "
            "stores hash-based URLs."
        ),
        "host_guest_messaging": (
            "1:1 thread per (listing, guest); host can have many threads. Defers to the dedicated "
            "chat design (WebSocket gateway, Cassandra messages, push for offline). Messages can "
            "pre-date a booking (inquiries) and continue post-booking (logistics). Auto-redaction "
            "of phone numbers / off-platform contact info to keep transactions on-platform."
        ),
        "cancellation_and_refunds": (
            "Cancellation policies (Flexible / Moderate / Strict) determine refund percentage by "
            "lead time. Cancel flow flips booking.status='cancelled', releases calendar rows, and "
            "issues a refund through Payment Service per policy. Host-side cancellations carry "
            "reputation penalty + automatic guest rebooking offer."
        ),
        "slo_contract": (
            "Search p99 < 500ms; listing detail p99 < 300ms; hold p99 < 200ms; confirm p99 < 1.5s "
            "(payment-bound). Zero double-bookings — calendar is strongly consistent. Search "
            "freshness: listing edits visible within ~2 min; calendar edits within ~30s."
        ),
    },
    trade_offs=[
        {"option": "Pessimistic vs optimistic concurrency on overlapping dates",
         "for_pessimistic": "Strong, simple to reason about, fails fast on contention",
         "for_optimistic": "No locks held, scales horizontally with low contention",
         "recommendation": "Pessimistic per-night row locks — hold critical sections are short and contention is rare; correctness first."},
        {"option": "Calendar as bitmap vs per-night rows",
         "for_bitmap": "Very compact, fast range checks",
         "for_rows": "Per-night price + min_stay + version metadata; SQL-friendly",
         "recommendation": "Per-night rows — Airbnb needs per-night pricing and constraints, not just availability."},
        {"option": "Search via Elasticsearch vs Postgres geo + filters",
         "for_es": "Inverted index, geo_bounding_box, ranking, near-instant filters at scale",
         "for_postgres": "One database to operate; PostGIS is competent",
         "recommendation": "Elasticsearch — ranked geo+filter search at 2M QPS isn't a Postgres workload."},
        {"option": "Synchronous vs async dynamic pricing",
         "for_sync": "Always fresh price",
         "for_async": "Bounded latency, decoupled, deterministic",
         "recommendation": "Async (batch + streaming top-up) — price freshness budget is minutes, not milliseconds."},
        {"option": "Reviews: blind vs immediate publish",
         "for_blind": "Honest reviews; neither side retaliates",
         "for_immediate": "Faster social signal",
         "recommendation": "Double-blind with 14-day reveal — Airbnb's actual policy and the right call."},
    ],
    tips=[
        "Lead with the booking concurrency story — it's the senior signal. Pessimistic per-night row locks inside a hold transaction.",
        "Hold-confirm with a TTL. State the TTL (10–15 min) and the sweeper that releases abandoned holds.",
        "Calendar is the single source of truth. The search index is a stale-tolerant projection.",
        "Search is geo + filters + ranking — Elasticsearch, not raw PostGIS or Redis geo.",
        "Photos never go through app servers — presigned S3 + async transcode + CDN.",
        "Reviews are double-blind for a reason; mention the reveal job.",
        "Don't compute dynamic pricing on the booking hot path — async pipeline writes the calendar.",
        "Defer messaging to the chat design and say so explicitly.",
    ],
    thought_process=[
        "1. Clarify scope: search, calendar, booking, reviews, host onboarding, photos, messaging, T+S.",
        "2. Estimate: 7M listings, 150B searches/day (~2M QPS peak), 1M bookings/day. Read-heavy 99:1.",
        "3. APIs: /search (geo+filters), /listings/{id}, /bookings/hold, /bookings/confirm, /reviews.",
        "4. Search: Elasticsearch index with geo_bounding_box + filters + ranking. Date filter from a precomputed available_in_window flag.",
        "5. Calendar: per-night rows with available, price, version. Source of truth for bookability.",
        "6. Booking: hold-then-confirm with TTL. Pessimistic per-night row locks for correctness.",
        "7. Pricing: offline/streaming pipeline writes recommended per-night prices; never compute synchronously.",
        "8. Reviews: double-blind, post-stay, 14-day reveal window.",
        "9. Photos: presigned S3 + async transcode + CDN, content-hashed URLs.",
        "10. Host onboarding: KYC + payout verification gates booking acceptance.",
        "11. Trust + safety: device + payment + behavioural signals; account holds.",
        "12. Messaging: defers to chat design.",
    ],
    tags=["marketplace", "booking", "search", "calendar", "geospatial"],
    arch_nodes=[
        {"id": "client", "label": "Mobile / Web", "type": "client"},
        {"id": "lb", "label": "API Gateway", "type": "lb"},
        {"id": "search", "label": "Search Service", "type": "server"},
        {"id": "es", "label": "Elasticsearch", "type": "database"},
        {"id": "listing", "label": "Listing Service", "type": "server"},
        {"id": "listingdb", "label": "Listing DB", "type": "database"},
        {"id": "cal", "label": "Calendar Service", "type": "server"},
        {"id": "caldb", "label": "Calendar DB", "type": "database"},
        {"id": "book", "label": "Booking Service", "type": "server"},
        {"id": "pay", "label": "Payment Service", "type": "service"},
        {"id": "price", "label": "Pricing Pipeline", "type": "service"},
        {"id": "review", "label": "Review Service", "type": "server"},
        {"id": "kyc", "label": "Identity / KYC", "type": "service"},
        {"id": "ts", "label": "Trust + Safety", "type": "service"},
        {"id": "photo", "label": "Photo Pipeline", "type": "service"},
        {"id": "s3", "label": "S3 (Photos)", "type": "database"},
        {"id": "cdn", "label": "Media CDN", "type": "cache"},
        {"id": "msg", "label": "Messaging", "type": "service"},
        {"id": "kafka", "label": "Kafka", "type": "queue"},
        {"id": "redis", "label": "Redis", "type": "cache"},
    ],
    arch_edges=[
        {"source": "client", "target": "lb"},
        {"source": "lb", "target": "search"},
        {"source": "search", "target": "es", "label": "geo + filters"},
        {"source": "lb", "target": "listing"},
        {"source": "listing", "target": "listingdb"},
        {"source": "listing", "target": "kafka", "label": "listing.changed"},
        {"source": "kafka", "target": "es", "label": "index update"},
        {"source": "lb", "target": "cal"},
        {"source": "cal", "target": "caldb"},
        {"source": "lb", "target": "book"},
        {"source": "book", "target": "caldb", "label": "lock + write"},
        {"source": "book", "target": "pay", "label": "charge"},
        {"source": "book", "target": "kafka", "label": "booking.events"},
        {"source": "kafka", "target": "price"},
        {"source": "price", "target": "caldb", "label": "recommended price"},
        {"source": "lb", "target": "review"},
        {"source": "review", "target": "kafka", "label": "review.published"},
        {"source": "kafka", "target": "es", "label": "rating refresh"},
        {"source": "lb", "target": "kyc"},
        {"source": "lb", "target": "ts"},
        {"source": "client", "target": "s3", "label": "presigned PUT"},
        {"source": "s3", "target": "photo", "label": "ObjectCreated"},
        {"source": "photo", "target": "s3", "label": "variants"},
        {"source": "client", "target": "cdn", "label": "photo GET"},
        {"source": "cdn", "target": "s3", "label": "origin"},
        {"source": "lb", "target": "msg"},
        {"source": "search", "target": "redis", "label": "hot results"},
        {"source": "listing", "target": "redis", "label": "detail cache"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant G as Guest\n"
        "  participant API\n"
        "  participant S as Search\n"
        "  participant L as Listing\n"
        "  participant B as Booking\n"
        "  participant C as Calendar\n"
        "  participant P as Payment\n"
        "  G->>API: GET /search (bbox + filters)\n"
        "  API->>S: query ES\n"
        "  S-->>G: ranked listings\n"
        "  G->>API: GET /listings/{id}\n"
        "  API->>L: detail + photos + reviews\n"
        "  L-->>G: listing page\n"
        "  G->>API: POST /bookings/hold\n"
        "  API->>B: start hold tx\n"
        "  B->>C: SELECT FOR UPDATE nights\n"
        "  C-->>B: rows locked, all available\n"
        "  B->>C: UPDATE available=false\n"
        "  B-->>G: hold_id (TTL=10m)\n"
        "  G->>API: POST /confirm payment\n"
        "  API->>B: confirm\n"
        "  B->>P: charge card\n"
        "  P-->>B: success\n"
        "  B->>C: status=confirmed\n"
        "  B-->>G: booked"
    ),
    er_diagram=(
        "erDiagram\n"
        "  USER ||--o{ LISTING : hosts\n"
        "  USER ||--o{ BOOKING : guest_of\n"
        "  LISTING ||--o{ CALENDAR : has\n"
        "  LISTING ||--o{ PHOTO : has\n"
        "  LISTING ||--o{ BOOKING : booked_as\n"
        "  BOOKING ||--|| PAYMENT : pays\n"
        "  BOOKING ||--o{ REVIEW : produces\n"
        "  LISTING { bigint id PK\n bigint host_id\n double lat\n double lng\n int base_price_cents\n float rating_avg }\n"
        "  CALENDAR { bigint listing_id\n date night\n bool available\n int price_cents\n bigint version }\n"
        "  BOOKING { bigint id PK\n bigint listing_id\n date checkin\n date checkout\n string status\n bigint hold_expires_at }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B[Two-sided marketplace]\n"
        "  B --> C[Search: geo + filters + ranking]\n"
        "  C --> D[Calendar = source of truth]\n"
        "  D --> E{Booking concurrency?}\n"
        "  E -->|Pessimistic| F[Row locks per night]\n"
        "  E -->|Optimistic| G[Version CAS + retry]\n"
        "  F --> H[Hold-then-confirm with TTL]\n"
        "  H --> I[Async payment + sweeper]\n"
        "  I --> J[Reviews: double-blind, post-stay]\n"
        "  J --> K[Photos: presigned + CDN]\n"
        "  K --> L[Trust + safety cross-cutting]"
    ),
    tradeoff_title="Pessimistic vs Optimistic concurrency for overlapping date bookings",
    tradeoff_options=[
        {"label": "Pessimistic locking (SELECT FOR UPDATE per night)",
         "description": "Lock the per-night calendar rows for the date range inside the hold transaction.",
         "pros": ["Strong correctness — zero double-bookings",
                  "Simple to reason about and audit",
                  "Fails fast on contention"],
         "cons": ["Holds locks for the duration of hold critical section",
                  "Hot listings can serialise concurrent attempts",
                  "Requires partitioning calendar by listing_id to scale"]},
        {"label": "Optimistic concurrency (version CAS)",
         "description": "Read calendar rows with version; UPDATE WHERE version=read_version; retry on mismatch.",
         "pros": ["No locks held",
                  "Higher throughput at low contention",
                  "Plays well with multi-region read replicas"],
         "cons": ["Requires explicit retry ladder",
                  "Failed CAS bursts under contention waste work",
                  "Slightly trickier to reason about edge cases (partial range conflict)"]},
        {"label": "Distributed lock (Redis/Zookeeper) per (listing, range)",
         "description": "Acquire a named lock for the listing+range before touching the database.",
         "pros": ["Decouples lock from DB",
                  "Cross-region coordination friendly"],
         "cons": ["Lock service becomes a critical dependency",
                  "Lease + fencing tokens needed for safety",
                  "Two systems to keep consistent"]},
    ],
    tradeoff_rec=(
        "Pessimistic per-night row locks inside the hold transaction. Calendar partitioned by "
        "listing_id keeps contention local; the critical section is sub-100ms. Reach for optimistic "
        "only when scaling past a single primary; reach for distributed locks only when crossing "
        "regions in the booking path."
    ),
    senior_topics=[
        _topic("hold-confirm-ttl",
               "Hold-Then-Confirm with TTL",
               "Booking is two-phase: a short hold reserves the calendar; a confirm step charges "
               "payment and finalises. A TTL on the hold prevents abandoned checkouts from blocking "
               "inventory. The pattern decouples inventory correctness from payment latency.",
               [
                   ("Why two phases",
                    "If you charge payment inline with the calendar update you couple the booking "
                    "transaction's duration to the payment provider's tail latency (seconds to tens "
                    "of seconds). Holding row locks that long destroys throughput and amplifies "
                    "deadlocks on hot listings."),
                   ("Hold transaction",
                    "Atomic: SELECT FOR UPDATE the per-night rows for [checkin, checkout-1], assert "
                    "available=true everywhere, validate min_stay, set available=false, write a "
                    "booking row in status='held' with hold_expires_at = now+10m. Commit. Critical "
                    "section is sub-100ms."),
                   ("Confirm step",
                    "Outside the hold transaction. Payment Service charges; on success flip booking "
                    "to 'confirmed'. On payment failure the client can retry within the TTL. The "
                    "calendar already shows unavailable; if the client never confirms, the sweeper "
                    "releases."),
                   ("Sweeper / TTL release",
                    "A background job scans bookings with status='held' and hold_expires_at < now, "
                    "flips them to 'abandoned', and re-marks the calendar rows available=true. Run "
                    "every 30s; idempotent — safe to retry. An alternative is a per-row TTL job, but "
                    "a single sweeper is operationally simpler and well below capacity at 1M "
                    "bookings/day."),
                   ("UX implications",
                    "Surface a countdown to the guest during checkout. On confirm-after-expiry, fail "
                    "explicitly and let the guest retry from search — never silently re-hold (the "
                    "room may have been booked by someone else)."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant G as Guest\n"
                   "  participant B as Booking Svc\n"
                   "  participant C as Calendar\n"
                   "  participant P as Payment\n"
                   "  participant S as Sweeper\n"
                   "  G->>B: hold(listing, range)\n"
                   "  B->>C: SELECT FOR UPDATE nights\n"
                   "  B->>C: mark unavailable; status=held\n"
                   "  B-->>G: hold_id (TTL=10m)\n"
                   "  alt confirm in time\n"
                   "    G->>B: confirm(payment)\n"
                   "    B->>P: charge\n"
                   "    P-->>B: ok\n"
                   "    B->>C: status=confirmed\n"
                   "  else timeout\n"
                   "    S->>B: scan held + expired\n"
                   "    B->>C: mark available; status=abandoned\n"
                   "  end"
               )),
        _topic("concurrency-pessimistic-optimistic",
               "Pessimistic vs Optimistic on Overlapping Dates",
               "Two concurrent guests trying to book overlapping nights is the canonical correctness "
               "problem. Pessimistic locks serialise; optimistic CAS lets one win and the other "
               "retry. Both are correct; the choice is operational.",
               [
                   ("Pessimistic mechanics",
                    "Inside the hold transaction, SELECT ... FROM calendar WHERE listing_id=X AND "
                    "night IN (...) FOR UPDATE. Postgres / MySQL hold row locks until commit. The "
                    "second concurrent attempt blocks until the first commits, then sees rows "
                    "already unavailable and fails."),
                   ("Optimistic mechanics",
                    "Read each row with its version. UPDATE calendar SET available=false, "
                    "version=version+1 WHERE listing_id=X AND night=N AND version=read_version AND "
                    "available=true. If any row's UPDATE returns 0 rows affected, ROLLBACK and "
                    "either fail or retry once."),
                   ("Why pessimistic wins here",
                    "Contention is rare per-listing (a hot listing might get a few simultaneous "
                    "requests, not thousands). Lock duration is sub-100ms. The simplicity dividend "
                    "is large: one transaction, no retry ladder, easy to audit. Calendar partitioned "
                    "by listing_id means locks never cross shards."),
                   ("When optimistic wins",
                    "If the calendar must scale beyond a single primary (it almost certainly doesn't "
                    "at 7M listings — 1M bookings/day is ~12 QPS peak globally), optimistic is "
                    "friendlier to multi-primary or read-replica routing. Or when extending to a "
                    "geographically distributed write path."),
                   ("Anti-pattern: app-level lock without DB serialisation",
                    "Holding a lock in Redis but not serialising the DB write is unsafe under lock "
                    "expiry + clock skew. Always pair a distributed lock with a DB-level invariant "
                    "(unique constraint or row lock) so the truth is in the database."),
                   ("Idempotency on hold creation",
                    "Client passes a hold_idempotency_key; the booking table has a unique index. A "
                    "retried network request returns the original hold instead of double-locking."),
               ]),
        _topic("search-ranking-filters",
               "Geospatial Search with Filters and Ranking",
               "Airbnb search is bounding-box geo + structured filters + ranking. Elasticsearch "
               "handles all three in one query against a denormalised listing index that's "
               "asynchronously updated from the source databases.",
               [
                   ("Index shape",
                    "One Elasticsearch document per listing: geo_point (lat, lng), city, country, "
                    "beds, max_guests, amenities (keyword set), base_price_cents, rating_avg, "
                    "review_count, host_score, instant_book, available_in_window:bool (precomputed), "
                    "popularity (decayed view + book counts)."),
                   ("Date filter via projection",
                    "Computing per-query date availability against millions of calendar rows is too "
                    "slow. Instead, a streaming job computes for each listing whether it's available "
                    "in [now, now+90d] and refreshes the available_in_window flag every few minutes. "
                    "Source of truth for the booking write is still the calendar table — search is "
                    "an approximation that must be re-validated at hold time."),
                   ("Bounding-box query",
                    "geo_bounding_box on the map viewport rather than a centre+radius — matches the "
                    "user's actual UI. Combined with term filters (amenities) and range filters "
                    "(price). Tile aggregations let the map render counts per cell at low zoom."),
                   ("Ranking signals",
                    "Bayesian-smoothed rating_avg (so a listing with 3 perfect reviews doesn't "
                    "outrank one with 200 great reviews), price-fit to user budget, distance from "
                    "viewport centre, host responsiveness, instant-book preference, personalised "
                    "affinity (recent searches, language, prior bookings). Mix as a weighted sum or "
                    "a learned-to-rank model trained on click + book outcomes."),
                   ("Index freshness",
                    "Listing edits fan out via Kafka to a reindexer; eventual within ~2 minutes. "
                    "Calendar projection refreshes within ~30 seconds. The booking flow re-checks "
                    "calendar atomically at hold time — search staleness can never cause an "
                    "incorrect booking, only a 'no longer available' message."),
               ]),
        _topic("dynamic-pricing",
               "Dynamic / Smart Pricing — Async, Not Synchronous",
               "Smart Pricing recommends per-night prices for hosts based on demand. It runs as a "
               "batch + streaming pipeline; the booking and search paths read pre-written prices.",
               [
                   ("Inputs",
                    "Search volume per geography, competitor prices for similar listings, lead time "
                    "to checkin, day-of-week pattern, local events (concerts, conferences), booking "
                    "history, listing's own conversion rate at price points. Combined into a per-"
                    "listing-per-night recommended price."),
                   ("Pipeline",
                    "Nightly batch produces baseline prices for the next 12 months. Streaming top-up "
                    "(Flink) adjusts the next ~30 days based on real-time demand signals every few "
                    "minutes. Output: an UPDATE to the calendar.price_cents for hosts who opted into "
                    "auto-pricing; a stored recommendation for hosts who manually accept."),
                   ("Why never synchronous",
                    "Computing demand-aware prices on the search hot path would couple search "
                    "latency to a complex feature pipeline. The price freshness budget is minutes, "
                    "not milliseconds, so async is correct and safer."),
                   ("Host control",
                    "Hosts set min/max bounds. Auto-pricing stays inside the bounds. Manual hosts "
                    "see a 'recommended ${price}' nudge in the UI but the calendar's price is what "
                    "they entered."),
                   ("Surge / event multipliers",
                    "Detected events apply a multiplier on the recommended baseline; never on the "
                    "calendar.price_cents directly without going through the same pipeline (avoids "
                    "double-applying multipliers across batch + streaming cycles)."),
               ]),
        _topic("reviews-double-blind",
               "Double-Blind Post-Stay Reviews",
               "Both guest and host write reviews after checkout, neither sees the other's review "
               "until both submit or a 14-day window closes. The mechanism reduces retaliation and "
               "produces more honest reviews.",
               [
                   ("Eligibility",
                    "Reviews can only be written after checkout AND only by the booking parties. A "
                    "review row references booking_id; uniqueness on (booking_id, kind) prevents "
                    "duplicates. Bookings cancelled before checkin produce no review eligibility."),
                   ("Submit + reveal mechanics",
                    "On submit, store row with submitted_at and published_at = NULL. A reveal job "
                    "runs daily: for any booking where both reviews are submitted OR the 14-day "
                    "window has closed, set published_at = now on whichever rows exist. Until then, "
                    "neither side sees the other's review."),
                   ("Aggregate refresh",
                    "On publish, push an event to recompute the listing's rating_avg + review_count. "
                    "These propagate to the search index for ranking. Use Bayesian smoothing in the "
                    "search ranker so listings with few reviews don't dominate."),
                   ("Anti-abuse",
                    "Review content is scanned for retaliatory language, off-platform contact info, "
                    "and policy violations. Flagged reviews route to moderation; the booking is "
                    "still eligible for the other party to publish their review on schedule."),
                   ("Non-completion case",
                    "If a guest cancels mid-stay or there's a refund event, review eligibility may "
                    "be revoked or surfaced with a 'partial stay' note. Encode this as a booking "
                    "status flag the review service reads at submit time."),
               ]),
        _topic("photos-cdn",
               "Photo Pipeline: Presigned Upload + Async Variants + CDN",
               "Listings live or die by photos. The pipeline keeps app servers out of the byte path "
               "and produces responsive variants for fast first paint.",
               [
                   ("Presigned upload",
                    "Client requests a short-lived S3 PUT URL from the listing service. Client "
                    "PUTs the original directly to S3. App server load is constant regardless of "
                    "photo size. Concurrency limited by S3, not the app."),
                   ("Async variants",
                    "S3 ObjectCreated triggers a transcoder (SQS → worker fleet). Variants: "
                    "320/640/960/1280/1920 webp, a 200px thumbnail, and a low-quality blur "
                    "placeholder (BlurHash or LQIP) for instant render. Variants written to S3, "
                    "URLs content-hashed for permanent cacheability."),
                   ("CDN delivery",
                    "CloudFront / Akamai fronts S3. Cache-Control: public, immutable, 1y. Edge "
                    "caches near every major metro. Image delivery p99 < 100ms first byte."),
                   ("Listing readiness",
                    "Listing status='draft' until photos.transcode_done; only then can it appear in "
                    "search. Hosts see a clear 'processing' indicator in the listing dashboard."),
                   ("Retention + cost",
                    "Originals tier to S3 Glacier after 30 days (still recoverable for re-encode). "
                    "Variants stay warm. Removed listings keep originals for 90 days for moderation, "
                    "then deleted to comply with retention policy."),
               ]),
    ],
)
