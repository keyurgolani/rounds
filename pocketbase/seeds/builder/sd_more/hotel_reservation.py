"""SDQ — Design a Hotel Reservation System (chain like Marriott).

Inventory, search, booking, payments, loyalty, and channel manager for a global
hotel chain. Mirrors `sd_questions.SD_01` shape via the `_q` / `_topic` helpers.
"""
from __future__ import annotations

from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design a Hotel Reservation System",
    "Hard",
    "Design the reservation backbone for a global hotel chain (think Marriott / Hilton). The "
    "system powers search across thousands of properties, books rooms by date range, manages "
    "rate plans (BAR / AAA / member / corporate), enforces cancellation policies, awards "
    "loyalty points, and syncs inventory and prices to OTA channels (Expedia, Booking.com, "
    "Agoda). It must handle thousands of concurrent shoppers contending for the last room of a "
    "type, recover gracefully when a payment provider fails mid-booking, and reconstruct any "
    "reservation's full history for audit / dispute resolution.",
    hints=[
        "Inventory is keyed by (property, room_type, date) — NOT per physical room. Per-room "
        "assignment is a check-in concern, not a booking concern.",
        "The contention hotspot is the single (property, room_type, date) row when only 1 unit "
        "is left — concurrency strategy lives or dies there.",
        "Treat reservation lifecycle as an append-only event log; the `reservations` row is a "
        "materialised projection. This is what enables audits, replays, and saga compensation.",
        "Booking is a multi-step distributed transaction (hold inventory → charge card → "
        "confirm) — payment failure must release the held inventory deterministically. Saga, "
        "not 2PC.",
        "Channel manager is bidirectional: pull bookings from OTAs, push availability and "
        "rates to OTAs. Idempotency keys on every cross-system message.",
        "Search is a different system from booking — denormalised availability index, refreshed "
        "from the booking system, never the source of truth.",
    ],
    constraints=[
        "Thousands of properties, ~100-1000 room-types per property, 730-day booking horizon.",
        "Concurrent shoppers can hammer the same (property, room_type, date) slot — last-room "
        "contention is the central concurrency problem.",
        "OTA channels (Expedia, Booking.com) push reservations asynchronously and expect "
        "availability updates within seconds; double-booking across channels is unacceptable.",
        "Payment authorisation is external and may fail, time out, or succeed silently — "
        "every booking must be reconcilable.",
        "Cancellation policies vary per rate plan (refundable / non-refundable / partial) and "
        "must be enforced atomically with refund issuance.",
        "Audit / compliance: any reservation's full state history must be reconstructable "
        "for years (PCI, financial dispute, fraud).",
    ],
    req_func=[
        "Search properties by location/dates/guests with available rooms and prices.",
        "Hold and book a (room_type, date-range) at a chosen rate plan.",
        "Cancel or modify a reservation honouring the rate plan's cancellation policy.",
        "Group bookings: hold N rooms across multiple room-types under one reservation.",
        "Apply rate plans: BAR (best-available), AAA, member, corporate negotiated, promo codes.",
        "Award and redeem loyalty points; tier-based perks (free night, upgrade).",
        "Channel manager: ingest reservations from and broadcast inventory/rates to OTAs.",
        "Reconstruct full history of any reservation for audit and dispute handling.",
    ],
    req_nonfunc=[
        "No double-booking — strict invariant on (property, room_type, date) sold ≤ capacity.",
        "Booking write p99 < 500 ms; search p99 < 300 ms.",
        "Availability propagation to OTAs p95 < 5 s after a booking commits.",
        "99.99% availability for booking; 99.9% for search; reservation data durability 11 nines.",
        "Scale: 10K bookings/sec peak, 200K searches/sec peak, billions of inventory cells.",
        "Payment / inventory state recoverable after any single-component failure (saga).",
    ],
    estimation={
        "properties": "~8K hotels, ~2M total rooms",
        "room_types_per_property": "10-100 (median ~25)",
        "booking_horizon": "730 days → ~18B (property, room_type, date) cells",
        "bookings_per_day": "~5M global, peak 10K/sec around major events",
        "searches_per_day": "~2B; ~100:1 search:book ratio",
        "ota_share": "~40% of bookings arrive via OTAs; channel push fan-out 5-10× internal",
        "loyalty_members": "~200M; ~1B annual point transactions",
        "retention": "Reservation event log: 7 years for financial / regulatory audit",
    },
    endpoints=[
        {"method": "GET", "path": "/v1/search",
         "description": "Search available properties + room-types for dates",
         "body": "{location, check_in, check_out, guests, rate_plan_filter?}"},
        {"method": "GET", "path": "/v1/properties/{property_id}/availability",
         "description": "Per-room-type availability + price grid for a date range"},
        {"method": "POST", "path": "/v1/holds",
         "description": "Soft-hold inventory for ~10 min during checkout (returns hold_id)",
         "body": "{property_id, room_type_id, check_in, check_out, qty, idempotency_key}"},
        {"method": "POST", "path": "/v1/reservations",
         "description": "Confirm booking — converts hold + payment authorisation into reservation",
         "body": "{hold_id, guest, payment_token, rate_plan, loyalty_id?, idempotency_key}"},
        {"method": "GET", "path": "/v1/reservations/{id}",
         "description": "Fetch reservation with current status + materialised history"},
        {"method": "POST", "path": "/v1/reservations/{id}/cancel",
         "description": "Cancel respecting cancellation policy; issues refund if eligible"},
        {"method": "POST", "path": "/v1/reservations/{id}/modify",
         "description": "Change dates / room-type — re-prices and re-holds inventory atomically"},
        {"method": "POST", "path": "/v1/channel/inbound",
         "description": "OTA → us: receive booking pushed by Expedia / Booking.com",
         "body": "{channel, channel_ref, ...mapped reservation fields, idempotency_key}"},
        {"method": "POST", "path": "/v1/channel/outbound/availability",
         "description": "Internal: broadcast availability/rate change to all subscribed channels"},
        {"method": "GET", "path": "/v1/loyalty/{member_id}",
         "description": "Loyalty balance, tier, and recent point transactions"},
    ],
    tables=[
        {"name": "properties",
         "columns": ["property_id BIGINT PK", "brand VARCHAR(64)", "name VARCHAR(255)",
                     "geo_lat DECIMAL(9,6)", "geo_lng DECIMAL(9,6)",
                     "city VARCHAR(128)", "country CHAR(2)", "tz VARCHAR(64)"]},
        {"name": "room_types",
         "columns": ["room_type_id BIGINT PK", "property_id BIGINT", "code VARCHAR(32)",
                     "name VARCHAR(128)", "capacity_per_unit INT", "total_units INT"]},
        {"name": "inventory",
         "columns": ["property_id BIGINT", "room_type_id BIGINT", "stay_date DATE",
                     "total_units INT", "sold_units INT", "held_units INT",
                     "version BIGINT",
                     "PRIMARY KEY (property_id, room_type_id, stay_date)"]},
        {"name": "rate_plans",
         "columns": ["rate_plan_id BIGINT PK", "property_id BIGINT", "code VARCHAR(32)",
                     "name VARCHAR(128)", "kind ENUM('BAR','AAA','MEMBER','CORPORATE','PROMO')",
                     "cancellation_policy_id BIGINT", "advance_purchase_days INT",
                     "active BOOLEAN"]},
        {"name": "rates",
         "columns": ["property_id BIGINT", "room_type_id BIGINT", "rate_plan_id BIGINT",
                     "stay_date DATE", "amount_cents BIGINT", "currency CHAR(3)",
                     "PRIMARY KEY (property_id, room_type_id, rate_plan_id, stay_date)"]},
        {"name": "cancellation_policies",
         "columns": ["policy_id BIGINT PK", "name VARCHAR(64)",
                     "kind ENUM('REFUNDABLE','NON_REFUNDABLE','PARTIAL')",
                     "free_until_hours_before INT NULL", "penalty_pct INT NULL"]},
        {"name": "holds",
         "columns": ["hold_id CHAR(26) PK", "property_id BIGINT", "room_type_id BIGINT",
                     "check_in DATE", "check_out DATE", "qty INT",
                     "expires_at BIGINT", "state ENUM('ACTIVE','EXPIRED','CONSUMED')",
                     "idempotency_key VARCHAR(64) UNIQUE"]},
        {"name": "reservations",
         "columns": ["reservation_id CHAR(26) PK", "property_id BIGINT", "room_type_id BIGINT",
                     "check_in DATE", "check_out DATE", "qty INT",
                     "rate_plan_id BIGINT", "guest_id BIGINT", "loyalty_id BIGINT NULL",
                     "channel ENUM('DIRECT','EXPEDIA','BOOKING','AGODA') ",
                     "channel_ref VARCHAR(64) NULL",
                     "total_cents BIGINT", "currency CHAR(3)",
                     "status ENUM('PENDING','CONFIRMED','CANCELLED','NO_SHOW','CHECKED_IN','CHECKED_OUT')",
                     "version BIGINT", "created_at BIGINT", "updated_at BIGINT"]},
        {"name": "reservation_events",
         "columns": ["event_id BIGINT PK", "reservation_id CHAR(26)", "seq INT",
                     "kind VARCHAR(32)", "payload JSON", "actor VARCHAR(64)",
                     "occurred_at BIGINT"]},
        {"name": "payments",
         "columns": ["payment_id CHAR(26) PK", "reservation_id CHAR(26)",
                     "kind ENUM('AUTH','CAPTURE','REFUND','VOID')",
                     "amount_cents BIGINT", "currency CHAR(3)",
                     "provider VARCHAR(32)", "provider_ref VARCHAR(64)",
                     "status ENUM('PENDING','SUCCESS','FAILED')", "occurred_at BIGINT"]},
        {"name": "loyalty_accounts",
         "columns": ["loyalty_id BIGINT PK", "guest_id BIGINT", "tier VARCHAR(16)",
                     "points_balance BIGINT", "lifetime_points BIGINT"]},
        {"name": "loyalty_ledger",
         "columns": ["txn_id BIGINT PK", "loyalty_id BIGINT", "reservation_id CHAR(26) NULL",
                     "kind ENUM('EARN','REDEEM','ADJUST','EXPIRE')",
                     "points BIGINT", "occurred_at BIGINT"]},
        {"name": "channel_outbox",
         "columns": ["msg_id BIGINT PK", "channel VARCHAR(16)", "kind VARCHAR(32)",
                     "payload JSON", "state ENUM('PENDING','SENT','FAILED')",
                     "attempts INT", "next_attempt_at BIGINT"]},
    ],
    indexes=[
        "(property_id, room_type_id, stay_date) on inventory — primary contention key",
        "(property_id, geo_lat, geo_lng) on properties — geo search",
        "(reservation_id, seq) on reservation_events — replay history",
        "(loyalty_id, occurred_at DESC) on loyalty_ledger — statement view",
        "(state, next_attempt_at) on channel_outbox — outbox poller",
        "(channel, channel_ref) on reservations — OTA dedupe",
    ],
    hld_desc=(
        "Three-plane architecture. Inventory plane: sharded RDBMS keyed by "
        "(property_id, room_type_id, stay_date) with row-level concurrency control — the single "
        "source of truth for who owns which night. Reservation plane: append-only event log "
        "(`reservation_events`) projected into the materialised `reservations` table; this is "
        "what gives clean audits and saga compensation. Search plane: denormalised availability "
        "index (Elasticsearch / OpenSearch) hydrated by a CDC stream off inventory — fast, "
        "approximate, and rebuildable. The booking flow is a saga: HoldInventory → "
        "AuthorisePayment → ConfirmReservation, each step idempotent and each with a "
        "compensating action. A channel manager service consumes the reservation event stream "
        "to push availability/rates outbound, and a separate inbound adapter ingests OTA "
        "bookings through the same hold/confirm path."
    ),
    hld_components=[
        {"name": "API Gateway", "role": "Auth, rate-limit, route by property shard"},
        {"name": "Search Service", "role": "Geo + date + filters over availability index"},
        {"name": "Inventory Service", "role": "Authoritative (prop, room_type, date) state"},
        {"name": "Reservation Service", "role": "Saga orchestrator + event log writer"},
        {"name": "Pricing / Rates Service", "role": "Rate plans, BAR, member, promo, loyalty discounts"},
        {"name": "Payment Service", "role": "External PSP integration; auth/capture/refund"},
        {"name": "Loyalty Service", "role": "Points ledger, tier evaluation, redemption"},
        {"name": "Channel Manager", "role": "Bidirectional OTA sync (Expedia/Booking/Agoda)"},
        {"name": "Outbox / CDC", "role": "At-least-once delivery to channels and search index"},
        {"name": "Audit / Replay", "role": "Reconstruct reservation state from event log"},
    ],
    detailed_design={
        "inventory_model": (
            "Inventory is per (property_id, room_type_id, stay_date) — NOT per physical room. A "
            "single row stores total_units, sold_units, held_units, version. Per-room assignment "
            "(which 312 vs 415) is decided at check-in by the property management system; "
            "booking only commits to a type. This collapses the contention surface from millions "
            "of physical rooms to ~thousands of (type, date) cells per property and matches how "
            "the industry actually thinks about availability. A multi-night stay is a write to "
            "every date row in [check_in, check_out)."
        ),
        "concurrency_control": (
            "Three options on the hot row. (1) Pessimistic SELECT … FOR UPDATE — correct, "
            "trivially serialisable, but the row becomes a serialisation bottleneck on the last "
            "unit. (2) Optimistic CAS on `version` — UPDATE … SET sold_units=sold_units+1, "
            "version=version+1 WHERE … AND version=:v AND total-sold-held≥qty; retries on "
            "conflict. (3) Distributed lock (Redis Redlock) — extra moving piece. We use "
            "optimistic CAS as the default with bounded retries (3-5) and fall back to "
            "FOR UPDATE only on rate-limited contention. The `held_units` field carries the "
            "soft-hold during checkout; it expires automatically and a sweeper restores capacity."
        ),
        "booking_saga": (
            "Booking is HoldInventory → AuthorisePayment → ConfirmReservation. Each step "
            "appends an event. If AuthorisePayment fails or times out, a compensation event "
            "ReleaseHold runs, which CASes held_units back down. If ConfirmReservation fails "
            "after a successful auth, a compensation Refund runs against the same provider_ref. "
            "Idempotency keys on every external call mean retries are safe. The saga state is "
            "the event log — not RAM in any service — so a crashed orchestrator resumes by "
            "scanning unfinished sagas. 2PC across PSP + DB is rejected: PSPs do not vote."
        ),
        "rate_plans_pricing": (
            "Rate plans are templates: BAR (best-available, public), AAA (10-15% off, gated by "
            "membership), member (loyalty-tier discounts), corporate (negotiated nightly cap), "
            "promo (code-gated, capacity-bounded). The `rates` table stores per-(room_type, "
            "rate_plan, date) prices, populated by a yield-management pipeline. At booking time "
            "the Pricing Service evaluates eligibility (auth claims, member tier, promo code "
            "remaining, advance-purchase window) and returns the cheapest valid rate. Total "
            "price = sum over stay dates; taxes/fees layered last."
        ),
        "cancellation_policies": (
            "Each rate_plan points at a cancellation_policy. REFUNDABLE: free until N hours "
            "before check-in; after that one-night penalty. NON_REFUNDABLE: full charge at "
            "booking, no refund. PARTIAL: percentage refund based on lead time. Cancellation is "
            "atomic: append CancelRequested, release inventory (CAS), compute refund amount per "
            "policy, issue Refund payment with idempotency key, append Cancelled. Failure "
            "between release and refund is recovered by the outbox poller scanning unfinished "
            "cancellations — never lose money to a partial cancel."
        ),
        "loyalty": (
            "Points awarded on stay completion (CHECKED_OUT event) — not at booking, because "
            "of cancellations. Redemption at booking decrements points via a ledger entry; if "
            "the booking saga fails, the compensation appends a reverse ledger entry — the "
            "balance is always derivable as ledger sum, never a single mutable counter. Tier "
            "evaluation is a daily batch over the last 12 months of EARN entries; tier perks "
            "(upgrade, late checkout) are applied as non-revenue rate plans at check-in."
        ),
        "channel_manager": (
            "Outbound: every reservation_events change publishes to a channel topic; per-channel "
            "adapters translate to Expedia/Booking/Agoda APIs and update remote availability + "
            "rates. The outbox table guarantees at-least-once delivery; idempotency keys handle "
            "redelivery. Inbound: each channel has a webhook adapter that maps the OTA payload "
            "to our HoldInventory + ConfirmReservation calls — same saga, different entry "
            "point. The (channel, channel_ref) unique index dedupes redelivered webhooks. "
            "Per-channel rate-limit and circuit-breaker keep one bad OTA from cascading."
        ),
        "search_plane": (
            "Search is NOT served from the inventory DB. A CDC stream (Debezium / equivalent) "
            "tails the inventory + rates tables into Kafka, and a sink writes denormalised "
            "documents into Elasticsearch keyed by (property_id, date_range_bucket) with "
            "min/max prices, room-type counts, geo, amenities. Search returns candidates; the "
            "actual hold uses authoritative inventory. A tiny stale window is acceptable — "
            "users always see real availability at hold time. Rebuildable from scratch by "
            "replaying CDC, which is the operational escape hatch."
        ),
        "event_log_audit": (
            "`reservation_events` is append-only with a per-reservation `seq`. The "
            "`reservations` row is a materialised projection updated in the same transaction "
            "as the event write (so the projection never lags durably). Replaying events from "
            "seq=1 reconstructs the row at any point in time — used for audits, fraud "
            "investigations, and point-in-time disputes. Retention is 7 years per financial "
            "compliance; old events tier to cold storage but stay queryable."
        ),
        "group_bookings": (
            "Group booking is N reservations under a parent group_id, each with its own "
            "(room_type, dates) tuple but a single rate plan and payment. The orchestrator "
            "holds inventory for every leg first; if any leg fails to hold, all legs release. "
            "Payment is one auth for the total, captured per-leg at check-in. Cancellation can "
            "be per-leg or whole-group; policy applies per leg."
        ),
        "slo_contract": (
            "Booking write p99 < 500 ms; search p99 < 300 ms; availability propagation to "
            "OTAs p95 < 5 s; double-booking probability ≈ 0 (CAS invariant); reservation "
            "durability 11 nines; full reservation history reconstructable for 7 years."
        ),
    },
    trade_offs=[
        {"option": "Per-room vs (room-type, date) inventory model",
         "for_per_room": "Exact assignment at booking; matches physical room",
         "for_room_type_date": "Far less contention; matches industry mental model",
         "recommendation": "(room-type, date). Room assignment is a check-in concern."},
        {"option": "Pessimistic locking vs optimistic CAS for last-room contention",
         "for_pessimistic": "Trivially serialisable; predictable",
         "for_optimistic": "No row-lock queue; scales horizontally; fast happy path",
         "recommendation": "Optimistic CAS with bounded retries; pessimistic only as a "
         "fallback under sustained contention."},
        {"option": "2PC vs Saga across booking + payment",
         "for_2pc": "Atomic from caller's view",
         "for_saga": "Works with external PSPs, recoverable, idempotent",
         "recommendation": "Saga. PSPs don't vote — 2PC is not even an option in practice."},
        {"option": "Mutable reservation row vs append-only event log",
         "for_mutable": "Simpler reads",
         "for_event_log": "Audit, replay, saga recovery, regulatory",
         "recommendation": "Both — event log as truth, materialised row as projection."},
        {"option": "Synchronous vs async OTA push",
         "for_sync": "Strong consistency to channel",
         "for_async": "Decouples booking latency from OTA latency",
         "recommendation": "Async via outbox; tolerate ~seconds of staleness, never block a "
         "booking on OTA availability."},
    ],
    tips=[
        "Lead with the inventory key: (property, room_type, date). Every interviewer is "
        "watching for this — per-physical-room is the junior trap.",
        "Name the contention point explicitly: the last-unit row. Then walk the three "
        "concurrency options (pessimistic / optimistic / distributed lock) and pick.",
        "Booking is a saga, not a transaction. Articulate the compensations.",
        "Append-only event log with materialised projection is the senior signal — buys "
        "audit, replay, and saga recovery in one move.",
        "Search plane is denormalised and rebuildable from CDC; never serve search from "
        "the booking DB.",
        "Channel manager is bidirectional with idempotency keys — call this out; many "
        "candidates only design the outbound half.",
    ],
    thought_process=[
        "1. Clarify scope: search, book, cancel, modify, group, OTA, loyalty, audit.",
        "2. Estimate: 8K properties × ~25 room-types × 730 days → ~150M inventory cells; 5M "
        "bookings/day with 10K/sec peaks; 100:1 search:book.",
        "3. Lock the inventory model: (property, room_type, date), not per physical room.",
        "4. APIs: search, hold, confirm, cancel, modify, channel inbound/outbound, loyalty.",
        "5. Schema: properties, room_types, inventory (CAS row), rate_plans/rates, holds, "
        "reservations + reservation_events, payments, loyalty_ledger, channel_outbox.",
        "6. Concurrency on the hot row: optimistic CAS with bounded retries; pessimistic "
        "fallback; soft holds via held_units + expiry.",
        "7. Booking as saga: HoldInventory → AuthorisePayment → ConfirmReservation, with "
        "ReleaseHold and Refund as compensations; idempotency keys on every external call.",
        "8. Rate plans + cancellation policies + loyalty as separate, composable layers.",
        "9. Channel manager via outbox + per-channel adapter; inbound webhooks reuse the "
        "same hold/confirm saga; (channel, channel_ref) dedupe.",
        "10. Search plane denormalised in OpenSearch via CDC; authoritative recheck at hold.",
        "11. Event log as source of truth; row as projection; retention 7 years.",
    ],
    tags=["reservation", "booking", "inventory", "concurrency", "payments"],
    arch_nodes=[
        {"id": "client", "label": "Client / OTA", "type": "client"},
        {"id": "lb", "label": "API Gateway", "type": "lb"},
        {"id": "search", "label": "Search Service", "type": "server"},
        {"id": "inv", "label": "Inventory Service", "type": "server"},
        {"id": "res", "label": "Reservation Service (saga)", "type": "server"},
        {"id": "price", "label": "Pricing / Rates", "type": "server"},
        {"id": "pay", "label": "Payment Service", "type": "server"},
        {"id": "loy", "label": "Loyalty Service", "type": "server"},
        {"id": "chan", "label": "Channel Manager", "type": "service"},
        {"id": "psp", "label": "PSP (Stripe/Adyen)", "type": "service"},
        {"id": "ota", "label": "Expedia / Booking / Agoda", "type": "service"},
        {"id": "invdb", "label": "Inventory DB", "type": "database"},
        {"id": "evdb", "label": "Reservation Event Log", "type": "database"},
        {"id": "es", "label": "Search Index", "type": "database"},
        {"id": "obox", "label": "Outbox / CDC", "type": "service"},
    ],
    arch_edges=[
        {"source": "client", "target": "lb"},
        {"source": "lb", "target": "search", "label": "search"},
        {"source": "lb", "target": "res", "label": "hold/confirm"},
        {"source": "search", "target": "es"},
        {"source": "res", "target": "inv", "label": "CAS hold/sell"},
        {"source": "res", "target": "price", "label": "quote"},
        {"source": "res", "target": "pay", "label": "auth/capture"},
        {"source": "res", "target": "loy", "label": "earn/redeem"},
        {"source": "inv", "target": "invdb"},
        {"source": "res", "target": "evdb", "label": "append events"},
        {"source": "pay", "target": "psp"},
        {"source": "evdb", "target": "obox", "label": "CDC"},
        {"source": "invdb", "target": "obox", "label": "CDC"},
        {"source": "obox", "target": "es", "label": "index"},
        {"source": "obox", "target": "chan", "label": "publish"},
        {"source": "chan", "target": "ota", "label": "push avail/rates"},
        {"source": "ota", "target": "lb", "label": "inbound webhook"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant U as Shopper\n"
        "  participant API\n"
        "  participant RES as Reservation\n"
        "  participant INV as Inventory\n"
        "  participant PAY as Payment\n"
        "  participant PSP as PSP\n"
        "  participant CH as Channel Mgr\n"
        "  U->>API: POST /holds (room_type, dates, qty)\n"
        "  API->>RES: HoldInventory\n"
        "  RES->>INV: CAS held_units+=qty\n"
        "  INV-->>RES: ok (version+1)\n"
        "  RES-->>U: hold_id (10 min ttl)\n"
        "  U->>API: POST /reservations (hold_id, payment_token)\n"
        "  API->>RES: ConfirmReservation (saga)\n"
        "  RES->>PAY: AuthorisePayment\n"
        "  PAY->>PSP: auth(amount, idem_key)\n"
        "  PSP-->>PAY: AUTH_OK provider_ref\n"
        "  PAY-->>RES: ok\n"
        "  RES->>INV: CAS held_units-=qty, sold_units+=qty\n"
        "  RES->>RES: append Confirmed event + materialise row\n"
        "  RES-->>U: 201 reservation_id\n"
        "  RES->>CH: publish availability change\n"
        "  CH->>OTA: push new availability\n"
        "  Note over RES,PAY: On payment fail → ReleaseHold compensation\n"
        "  Note over RES,PAY: On confirm fail post-auth → Refund compensation"
    ),
    er_diagram=(
        "erDiagram\n"
        "  PROPERTY ||--o{ ROOM_TYPE : has\n"
        "  ROOM_TYPE ||--o{ INVENTORY : per-date\n"
        "  PROPERTY ||--o{ RATE_PLAN : offers\n"
        "  RATE_PLAN ||--o{ RATE : nightly-price\n"
        "  RATE_PLAN }o--|| CANCELLATION_POLICY : uses\n"
        "  RESERVATION ||--o{ RESERVATION_EVENT : log\n"
        "  RESERVATION ||--o{ PAYMENT : auth-capture-refund\n"
        "  RESERVATION }o--|| ROOM_TYPE : books\n"
        "  RESERVATION }o--o| LOYALTY_ACCOUNT : earns\n"
        "  LOYALTY_ACCOUNT ||--o{ LOYALTY_LEDGER : ledger\n"
        "  RESERVATION }o--o| CHANNEL_OUTBOX : publishes"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B[Pick inventory key: room_type x date]\n"
        "  B --> C[Identify hot row: last-unit contention]\n"
        "  C --> D{Concurrency?}\n"
        "  D -->|optimistic CAS| E[Bounded retries on version]\n"
        "  D -->|pessimistic| F[Row lock fallback]\n"
        "  E --> G[Booking saga]\n"
        "  G --> H[Hold -> Auth -> Confirm]\n"
        "  H --> I{Step fails?}\n"
        "  I -->|payment fail| J[ReleaseHold compensation]\n"
        "  I -->|confirm fail post-auth| K[Refund compensation]\n"
        "  G --> L[Append event + materialise row]\n"
        "  L --> M[Outbox to channels + search index]\n"
        "  M --> N[OTAs see updated availability]"
    ),
    tradeoff_title="Concurrency on the Last-Unit Row",
    tradeoff_options=[
        {"label": "Pessimistic SELECT … FOR UPDATE",
         "description": "Take a row lock on (property, room_type, date) before checking and "
         "decrementing capacity.",
         "pros": ["Trivially serialisable", "Easy to reason about",
                 "No retry loop in app code"],
         "cons": ["Lock queue under contention becomes the bottleneck",
                 "Long-held locks block readers and writers alike",
                 "DB connection pressure during peak"]},
        {"label": "Optimistic CAS on version",
         "description": "Read version + capacity, then UPDATE … WHERE version=:v AND "
         "total-sold-held>=qty; retry on conflict.",
         "pros": ["No lock queue — happy-path is one round-trip",
                 "Scales horizontally with stateless app",
                 "Natural fit for an event-sourced model"],
         "cons": ["Requires bounded retry policy",
                 "Pathological hot rows still see contention storms",
                 "App must handle conflict explicitly"]},
        {"label": "Distributed lock (Redis Redlock)",
         "description": "Take a named lock per (property, room_type, date) before mutating the DB.",
         "pros": ["Decouples concurrency from the DB engine",
                 "Easy to share with non-DB resources"],
         "cons": ["Extra critical dependency; lock-loss edge cases",
                 "Adds latency to every booking",
                 "Redlock correctness is debated — real risk for money paths"]},
    ],
    tradeoff_rec=(
        "Optimistic CAS as the default with a 3-5 retry budget; pessimistic FOR UPDATE as the "
        "automatic fallback once a row's retry rate crosses a threshold (sticky single-cell "
        "contention). Avoid distributed locks on the money path."
    ),
    senior_topics=[
        _topic("inventory-as-room-type-day",
               "Inventory as (Property, Room-Type, Date) — Not Per Physical Room",
               "Why the entire industry models availability per room-type per night, and what "
               "this buys at booking time, in concurrency, and in operations.",
               [
                   ("The model",
                    "One inventory row per (property_id, room_type_id, stay_date) with "
                    "total_units, sold_units, held_units, version. A multi-night stay touches "
                    "every date row in [check_in, check_out)."),
                   ("Why not per physical room",
                    "Per-room booking pretends the customer cares which 312 vs 415 they get — "
                    "they don't, and assigning physical rooms at booking inflates the "
                    "contention surface from thousands of cells to millions, and tightly "
                    "couples the booking system to housekeeping, maintenance, and "
                    "out-of-order rooms."),
                   ("Room assignment at check-in",
                    "The property management system assigns the actual room number at "
                    "check-in, factoring in housekeeping status, accessibility needs, and "
                    "VIP upgrades. The reservation only commits to a type."),
                   ("Operational benefits",
                    "Closing a single room for repair never invalidates a reservation — "
                    "total_units drops by one and the next overbooked night gets walked or "
                    "upgraded. This separation is what lets large chains absorb minor outages "
                    "without bookings cascading."),
               ],
               diagram=(
                   "graph LR\n"
                   "  P[Property] --> RT[Room Type Deluxe King]\n"
                   "  RT --> I1[Date 2026-05-01: 100 units, sold 87, held 4]\n"
                   "  RT --> I2[Date 2026-05-02: 100 units, sold 92, held 1]\n"
                   "  RT --> I3[Date 2026-05-03: 100 units, sold 100, held 0]\n"
                   "  I3 --> X[SOLD OUT — booking blocked]"
               )),
        _topic("booking-saga-payment-recovery",
               "Booking Saga and Payment-Failure Recovery",
               "How a multi-step distributed booking stays correct when payment authorisation "
               "fails, times out, or succeeds silently — and why 2PC is not an option.",
               [
                   ("Why not 2PC",
                    "External PSPs (Stripe, Adyen, Worldpay) do not participate in a two-phase "
                    "commit — they have their own ledger, their own asynchronous webhooks, "
                    "and their own retry semantics. There is no PSP that exposes a 'prepare' "
                    "phase to your DB. Saga is the only realistic primitive."),
                   ("Saga shape",
                    "Three forward steps: HoldInventory, AuthorisePayment, ConfirmReservation. "
                    "Two compensating actions: ReleaseHold (for fail before auth or auth fail) "
                    "and Refund (for fail after auth). The state of the saga is the event log "
                    "— there is no in-memory state to lose."),
                   ("Idempotency",
                    "Every external call carries an idempotency_key derived from "
                    "(reservation_id, step). Replaying after a crash is safe; the PSP returns "
                    "the original auth, the inventory CAS no-ops because version moved, and "
                    "the event log refuses duplicate seq numbers."),
                   ("Silent success",
                    "PSP times out; we don't know if charge happened. The reconciler scans "
                    "PENDING auths nightly, queries the PSP by idempotency_key, and either "
                    "completes the saga or issues a refund. Never assume failure on timeout — "
                    "always reconcile."),
                   ("Held inventory expiry",
                    "If the saga abandons (process killed, never resumed), held_units expires "
                    "via TTL sweep. Capacity returns; user sees room available again. The "
                    "system self-heals."),
               ],
               diagram=(
                   "stateDiagram-v2\n"
                   "  [*] --> Holding\n"
                   "  Holding --> Authorising: HoldInventory ok\n"
                   "  Holding --> Failed: hold conflict\n"
                   "  Authorising --> Confirming: auth ok\n"
                   "  Authorising --> Released: auth fail / timeout\n"
                   "  Confirming --> Confirmed: commit + event\n"
                   "  Confirming --> Refunding: confirm fail post-auth\n"
                   "  Refunding --> Failed: refund ok\n"
                   "  Released --> Failed\n"
                   "  Confirmed --> [*]\n"
                   "  Failed --> [*]"
               )),
        _topic("channel-manager-bidirectional",
               "Channel Manager — Bidirectional OTA Sync Without Double-Booking",
               "How availability and rates flow outbound to Expedia/Booking/Agoda and how "
               "their bookings flow inbound, with idempotency and rate-limit protection.",
               [
                   ("Outbound via outbox + CDC",
                    "Inventory and rate changes are tailed by CDC into a per-channel topic. "
                    "Per-channel adapters translate to the OTA's protocol (Expedia EQC, "
                    "Booking.com OpenAPI, Agoda YCS) and PUT availability/rate updates. "
                    "Outbox table guarantees at-least-once; idempotency keys make the OTA "
                    "side safely re-deliverable."),
                   ("Inbound webhooks",
                    "Each channel posts new bookings to /v1/channel/inbound. The adapter maps "
                    "channel fields to our HoldInventory + ConfirmReservation calls — same "
                    "saga, different entry point. Unique index on (channel, channel_ref) "
                    "dedupes redelivered webhooks."),
                   ("Avoiding double-booking",
                    "The authoritative invariant is the inventory CAS. Even if two channels "
                    "race for the last room, only one CAS wins; the loser sees a hold conflict "
                    "and the OTA gets a rejection that it surfaces to its customer. Ours is "
                    "the only system that decides; OTAs cache, but cache always loses to the "
                    "source of truth."),
                   ("Rate limits and circuit breakers",
                    "Each OTA has tight ingress rate limits. Per-channel token bucket + "
                    "circuit breaker prevents one slow / failing OTA from saturating the "
                    "outbox or the booking path. Failed sends retry with jitter and degrade "
                    "to a daily reconciliation job that diffs OTA availability vs ours."),
                   ("Reconciliation",
                    "Nightly reconciler pulls each OTA's view of availability + bookings and "
                    "diffs against ours. Mismatches surface as alerts to ops and as targeted "
                    "PUTs to the OTA. This is the long-tail safety net under best-effort "
                    "near-real-time pushes."),
               ],
               diagram=(
                   "graph LR\n"
                   "  INV[Inventory DB] -- CDC --> OUT[Outbox Topic]\n"
                   "  EV[Reservation Events] -- CDC --> OUT\n"
                   "  OUT --> AE[Expedia Adapter]\n"
                   "  OUT --> AB[Booking Adapter]\n"
                   "  OUT --> AA[Agoda Adapter]\n"
                   "  AE --> EXP[Expedia]\n"
                   "  AB --> BKG[Booking.com]\n"
                   "  AA --> AGO[Agoda]\n"
                   "  EXP -- webhook --> WH[/v1/channel/inbound]\n"
                   "  BKG -- webhook --> WH\n"
                   "  AGO -- webhook --> WH\n"
                   "  WH --> SAGA[Hold + Confirm Saga]\n"
                   "  SAGA --> INV"
               )),
        _topic("reservation-event-log",
               "Append-Only Event Log + Materialised Reservation Row",
               "Why the reservation lifecycle is stored as an event log with the row as a "
               "projection, and what this buys for audits, sagas, and disputes.",
               [
                   ("Event shape",
                    "Each event has (reservation_id, seq, kind, payload, actor, occurred_at). "
                    "Kinds: HoldRequested, HoldGranted, AuthRequested, AuthGranted, "
                    "AuthFailed, Confirmed, Modified, CancelRequested, Cancelled, NoShow, "
                    "CheckedIn, CheckedOut, Refunded. Append-only with monotonic seq."),
                   ("Materialised projection",
                    "The `reservations` row is updated in the same transaction as the event "
                    "append. The projection is therefore never durably behind the events; on "
                    "rebuild we replay from seq=1 and reproduce the row deterministically."),
                   ("Audit and disputes",
                    "A chargeback dispute six months later asks 'what did the customer see at "
                    "booking?' — replay events, reconstruct shown rate, applied policy, "
                    "captured timing. Without the log this is reconstructive guesswork."),
                   ("Saga recovery",
                    "On orchestrator crash mid-saga, the new instance scans recent reservations "
                    "with no terminal event and resumes from the last event. Idempotency keys "
                    "make in-flight steps replay-safe. The log is the saga state — no separate "
                    "saga store needed."),
                   ("Retention and tiering",
                    "7 years of events per financial / regulatory compliance. Older than 90 "
                    "days tiers to cold object storage; queryable with higher latency. "
                    "Projections stay warm; raw events stay cold but reachable."),
               ]),
    ],
)
