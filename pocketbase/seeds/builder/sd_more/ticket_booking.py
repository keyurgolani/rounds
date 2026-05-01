"""SDQ — Design a Concert Ticket Booking System (Ticketmaster-style).

High-contention seat-level inventory, virtual waiting room at sale open, hold +
TTL checkout, anti-scalper controls, dynamic pricing, presales, secondary market
resale, fraud-resistant rotating barcodes, and real-time sales analytics.
Mirrors `sd_questions.SD_01` shape via the `_q` / `_topic` helpers.
"""
from __future__ import annotations

from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design a Concert Ticket Booking System",
    "Hard",
    "Design a Ticketmaster-style ticket sales platform for live events (concerts, sports, "
    "festivals). The system stores per-venue seating charts down to the individual seat, opens "
    "sales for popular events where millions of fans land in the same second, places users into "
    "a virtual waiting room and admits them in fair batches, lets a fan select specific seats on "
    "an interactive map, holds those seats for a TTL during checkout, charges payment, issues "
    "fraud-resistant tickets with rotating barcodes, supports fan-club presales with codes, "
    "exposes a verified resale (secondary) market, and feeds real-time sales-velocity dashboards "
    "to artists and promoters. Anti-scalper controls (CAPTCHA, account verification, per-account "
    "limits, rate limits) run throughout. The contention surface is the individual seat, not a "
    "category — this is what distinguishes it from a hotel-style room-type-day inventory model.",
    hints=[
        "Inventory is per individual seat (event_id, section, row, seat) — not per price tier. "
        "Two fans clicking the same seat at the same instant is the central concurrency problem.",
        "Sale-open is a bursty thundering-herd event: millions of users hit /buy in the same "
        "second. A virtual waiting room is mandatory; admit in fair shuffled batches, never "
        "first-come-first-served at the front door.",
        "A seat hold is a TTL-bounded reservation (e.g. 7 minutes) — Redis SETNX with EXPIRE is "
        "the natural primitive; the DB row is the system of record but the lock lives in Redis.",
        "Anti-scalper is a layered control surface, not one switch: account verification, "
        "per-account purchase limits, CAPTCHA before sale, behavioural bot detection, "
        "device-fingerprint dedupe, and IP rate limits — each catches a different abuser class.",
        "Tickets must be unforgeable. Static barcodes are screenshot-able; rotating barcodes "
        "(short-lived signed tokens refreshed in the official app) defeat the screenshot-resale "
        "attack.",
        "Resale is a first-party market with verified-ticket transfer — never a re-issue of a "
        "new barcode without invalidating the old one. The original holder loses access the "
        "instant the buyer pays.",
        "Dynamic pricing on top hits is real (platinum / surge tiers); design the price as a "
        "lookup at hold-time, locked into the hold, and re-evaluated only on hold expiry — never "
        "mid-checkout.",
    ],
    constraints=[
        "Single popular on-sale: 1-5M concurrent users contending for 50K-100K seats in a venue.",
        "Seat-level contention: any two users may target the exact same seat at the same instant.",
        "Hold TTL ~7 minutes from selection to payment confirmation; expired holds must release "
        "atomically without leaving phantom inventory.",
        "Barcodes must defeat screenshot resale; physical paper tickets are a small minority and "
        "must be matched against the same source-of-truth.",
        "Scalper / bot pressure is sustained — every layer (queue, CAPTCHA, account, device, IP) "
        "is under active attack and must be tunable per event.",
        "Resale must invalidate the seller's access atomically with crediting the buyer — no "
        "window where both parties could enter the venue.",
        "Real-time sales velocity dashboards for artists / promoters must reflect commits within "
        "a few seconds.",
        "PCI scope for payments; PII (name, ID for high-trust events) for fraud / law enforcement.",
    ],
    req_func=[
        "Render an interactive seat map per event with live availability (held / sold / open).",
        "Place a user into a virtual waiting room when an event opens; admit in fair batches.",
        "Hold one or more specific seats for a TTL; show countdown to user.",
        "Convert a hold into a confirmed purchase via payment; issue tickets.",
        "Enforce per-account purchase limit per event (e.g. 4 tickets / 8 / 12 by event policy).",
        "Support fan-club presale codes (gated availability subset, code-bounded redemptions).",
        "Support dynamic / platinum pricing at hold-time with locked price for the hold window.",
        "Issue rotating-barcode tickets visible only in the verified app; allow PDF for legacy.",
        "Verified resale: list a ticket, accept a buyer, atomically transfer + invalidate seller.",
        "Real-time sales-velocity feed for artist / promoter dashboards.",
        "Cancel / refund per event policy; release seat back to inventory if pre-event.",
    ],
    req_nonfunc=[
        "Zero double-booking — strict invariant that any seat sells to at most one purchaser.",
        "Sale-open burst handling: 1-5M concurrent waiting-room participants, fair admission.",
        "Seat-hold p99 < 300 ms once admitted from the queue.",
        "Checkout (payment + ticket issue) p99 < 2 s.",
        "Barcode rotation: token TTL ≤ 30 s in-app; verifier offline-tolerant for short windows.",
        "99.99% availability during on-sale window; 99.9% steady state.",
        "Fraud / abuse controls tunable per event without code deploy.",
        "Sales-velocity propagation to dashboards p95 < 5 s.",
    ],
    estimation={
        "venues": "~10K venues, ~100K-500K future events at any time",
        "seats_per_venue": "~5K-100K (median ~20K)",
        "popular_onsale_concurrent": "1-5M users hitting /buy at the same minute",
        "tickets_per_year": "~500M tickets sold globally",
        "peak_purchases_per_sec": "~50K-100K during a top tour onsale",
        "search_to_buy_ratio": "~50:1 (browse vs purchase)",
        "barcode_scans_per_event": "~1-2× tickets sold (entry + re-entry)",
        "retention": "Order + ticket events 7 years (financial / dispute); sales-velocity 90 days hot",
    },
    endpoints=[
        {"method": "GET", "path": "/v1/events/{event_id}",
         "description": "Event metadata + seat-map blob URL + on-sale state"},
        {"method": "GET", "path": "/v1/events/{event_id}/availability",
         "description": "Sparse availability deltas for the seat map (open / held / sold)",
         "body": "{since_version}"},
        {"method": "POST", "path": "/v1/queue/enter",
         "description": "Join the virtual waiting room for an event; returns queue token + ETA",
         "body": "{event_id, captcha_token, device_fingerprint, presale_code?}"},
        {"method": "GET", "path": "/v1/queue/status",
         "description": "Poll position / admission state for a queue token"},
        {"method": "POST", "path": "/v1/holds",
         "description": "Hold a list of specific seats (TTL ~7 min) — admitted users only",
         "body": "{event_id, seat_ids[], queue_token, idempotency_key}"},
        {"method": "DELETE", "path": "/v1/holds/{hold_id}",
         "description": "Release a hold early"},
        {"method": "POST", "path": "/v1/orders",
         "description": "Convert a hold into a paid order; charges payment, issues tickets",
         "body": "{hold_id, payment_token, billing, idempotency_key}"},
        {"method": "GET", "path": "/v1/orders/{order_id}",
         "description": "Order detail + tickets + status"},
        {"method": "POST", "path": "/v1/tickets/{ticket_id}/barcode",
         "description": "Mint a short-lived rotating barcode token (in official app only)"},
        {"method": "POST", "path": "/v1/tickets/{ticket_id}/transfer",
         "description": "Transfer a ticket to another user (gift)"},
        {"method": "POST", "path": "/v1/resale/listings",
         "description": "List an owned ticket for resale at a price (within policy caps)",
         "body": "{ticket_id, ask_cents, idempotency_key}"},
        {"method": "POST", "path": "/v1/resale/{listing_id}/buy",
         "description": "Buy a resale listing — atomic transfer + invalidation of seller's access",
         "body": "{payment_token, idempotency_key}"},
        {"method": "POST", "path": "/v1/scan/verify",
         "description": "Venue gate scanner verifies a rotating-barcode token at entry",
         "body": "{token, gate_id}"},
        {"method": "GET", "path": "/v1/analytics/events/{event_id}/velocity",
         "description": "Real-time sales velocity for artist / promoter dashboards"},
    ],
    tables=[
        {"name": "venues",
         "columns": ["venue_id BIGINT PK", "name VARCHAR(255)", "city VARCHAR(128)",
                     "country CHAR(2)", "tz VARCHAR(64)", "seat_map_blob_url VARCHAR(512)"]},
        {"name": "venue_seats",
         "columns": ["venue_id BIGINT", "section VARCHAR(32)", "row VARCHAR(8)",
                     "seat VARCHAR(8)", "seat_id CHAR(26)", "x_pct DECIMAL(6,3)",
                     "y_pct DECIMAL(6,3)", "ada BOOLEAN",
                     "PRIMARY KEY (venue_id, section, row, seat)"]},
        {"name": "events",
         "columns": ["event_id BIGINT PK", "venue_id BIGINT", "artist_id BIGINT",
                     "title VARCHAR(255)", "starts_at BIGINT",
                     "onsale_at BIGINT", "presale_at BIGINT NULL",
                     "purchase_limit_per_account INT",
                     "status ENUM('SCHEDULED','PRESALE','ONSALE','SOLDOUT','PAUSED','POSTPONED','CANCELLED')",
                     "version BIGINT"]},
        {"name": "event_seats",
         "columns": ["event_id BIGINT", "seat_id CHAR(26)",
                     "price_tier VARCHAR(32)", "base_price_cents BIGINT",
                     "dynamic_price_cents BIGINT NULL", "currency CHAR(3)",
                     "state ENUM('OPEN','HELD','SOLD','BLOCKED')",
                     "hold_id CHAR(26) NULL", "owner_user_id BIGINT NULL",
                     "version BIGINT",
                     "PRIMARY KEY (event_id, seat_id)"]},
        {"name": "presale_codes",
         "columns": ["code_id BIGINT PK", "event_id BIGINT", "code VARCHAR(64) UNIQUE",
                     "max_redemptions INT", "redemptions INT", "expires_at BIGINT",
                     "fan_club_id BIGINT NULL"]},
        {"name": "holds",
         "columns": ["hold_id CHAR(26) PK", "event_id BIGINT", "user_id BIGINT",
                     "seat_ids JSON", "price_locked_cents BIGINT", "currency CHAR(3)",
                     "expires_at BIGINT",
                     "state ENUM('ACTIVE','EXPIRED','CONSUMED','RELEASED')",
                     "idempotency_key VARCHAR(64) UNIQUE"]},
        {"name": "orders",
         "columns": ["order_id CHAR(26) PK", "event_id BIGINT", "user_id BIGINT",
                     "hold_id CHAR(26)", "total_cents BIGINT", "currency CHAR(3)",
                     "status ENUM('PENDING','CONFIRMED','REFUNDED','FAILED')",
                     "channel ENUM('PRIMARY','RESALE','TRANSFER')",
                     "created_at BIGINT", "updated_at BIGINT"]},
        {"name": "tickets",
         "columns": ["ticket_id CHAR(26) PK", "order_id CHAR(26)", "event_id BIGINT",
                     "seat_id CHAR(26)", "owner_user_id BIGINT",
                     "state ENUM('VALID','TRANSFERRED','LISTED','SOLD','REVOKED','SCANNED')",
                     "issued_at BIGINT", "version BIGINT"]},
        {"name": "ticket_events",
         "columns": ["event_log_id BIGINT PK", "ticket_id CHAR(26)", "seq INT",
                     "kind VARCHAR(32)", "payload JSON", "actor VARCHAR(64)",
                     "occurred_at BIGINT"]},
        {"name": "barcode_tokens",
         "columns": ["jti CHAR(26) PK", "ticket_id CHAR(26)", "issued_at BIGINT",
                     "expires_at BIGINT", "consumed_at BIGINT NULL",
                     "device_fingerprint VARCHAR(128)"]},
        {"name": "resale_listings",
         "columns": ["listing_id CHAR(26) PK", "ticket_id CHAR(26)", "seller_user_id BIGINT",
                     "ask_cents BIGINT", "currency CHAR(3)",
                     "state ENUM('ACTIVE','SOLD','CANCELLED','EXPIRED')",
                     "policy_cap_cents BIGINT", "created_at BIGINT"]},
        {"name": "queue_tokens",
         "columns": ["queue_token CHAR(26) PK", "event_id BIGINT", "user_id BIGINT",
                     "joined_at BIGINT", "shuffled_position BIGINT",
                     "state ENUM('WAITING','ADMITTED','EXPIRED','REJECTED')",
                     "device_fingerprint VARCHAR(128)", "ip_hash VARCHAR(64)"]},
        {"name": "payments",
         "columns": ["payment_id CHAR(26) PK", "order_id CHAR(26)",
                     "kind ENUM('AUTH','CAPTURE','REFUND','VOID')",
                     "amount_cents BIGINT", "currency CHAR(3)",
                     "provider VARCHAR(32)", "provider_ref VARCHAR(64)",
                     "status ENUM('PENDING','SUCCESS','FAILED')", "occurred_at BIGINT"]},
        {"name": "abuse_signals",
         "columns": ["signal_id BIGINT PK", "user_id BIGINT NULL", "device_fingerprint VARCHAR(128)",
                     "ip_hash VARCHAR(64)", "kind VARCHAR(32)", "score INT",
                     "occurred_at BIGINT"]},
    ],
    indexes=[
        "(event_id, seat_id) on event_seats — primary contention key",
        "(event_id, state) on event_seats — sparse seat-map deltas",
        "(event_id, shuffled_position) on queue_tokens — fair admission scan",
        "(ticket_id, seq) on ticket_events — replay history",
        "(owner_user_id, state) on tickets — wallet view",
        "(jti) on barcode_tokens — gate verification + replay defence",
        "(event_id, user_id) on orders — per-account purchase-limit enforcement",
        "(device_fingerprint), (ip_hash) on abuse_signals — risk lookup",
    ],
    hld_desc=(
        "Four planes layered behind a hardened edge. Edge plane: CDN + WAF + bot-management + "
        "CAPTCHA gating before any backend reaches the application. Queue plane: a virtual "
        "waiting room (own service, own datastore) admits users in fair shuffled batches into "
        "the buying app — this is what protects every other plane during on-sale. Buying plane: "
        "stateless app servers fronting a sharded inventory store keyed on (event_id, seat_id), "
        "with the hold-lock layered as Redis SETNX+TTL and the durable seat row updated by a "
        "version-CAS write; a saga (Hold → AuthorisePayment → IssueTickets) wraps the durable "
        "commit. Ticketing plane: an append-only ticket event log with the ticket row as a "
        "materialised projection, a short-lived rotating barcode minted only by the official app "
        "via a signed JWT-style token, and a verifier service at the venue. A resale market "
        "shares the same ticket-state machine: listing + buy is implemented as transfer + "
        "ownership revoke, atomic at the ticket row. CDC streams off seat and ticket changes "
        "feed both the search-and-availability deltas and the real-time sales-velocity "
        "analytics."
    ),
    hld_components=[
        {"name": "Edge / WAF / Bot Mgmt", "role": "CAPTCHA, IP rate limit, fingerprint, JS challenges"},
        {"name": "Virtual Waiting Room", "role": "Queue entry, fair shuffle, batched admission"},
        {"name": "API Gateway", "role": "Auth, per-account rate limit, route to event shard"},
        {"name": "Catalog / Event Service", "role": "Event metadata, on-sale state, seat-map blobs"},
        {"name": "Inventory Service", "role": "Authoritative per-seat state machine"},
        {"name": "Hold Service (Redis)", "role": "SETNX+TTL lock per seat with auto-expiry"},
        {"name": "Order / Saga Service", "role": "Hold → AuthorisePayment → IssueTickets"},
        {"name": "Pricing Service", "role": "Dynamic / platinum pricing at hold-time"},
        {"name": "Payment Service", "role": "PSP integration; auth/capture/refund"},
        {"name": "Ticket Service", "role": "Ticket event log + state machine + ownership"},
        {"name": "Barcode Service", "role": "Mint short-lived signed rotating tokens in app"},
        {"name": "Gate Verifier", "role": "Validate token at venue; revocation aware"},
        {"name": "Resale Market", "role": "Listings + atomic verified-transfer purchase"},
        {"name": "Anti-Abuse / Risk", "role": "Bot scoring, device dedupe, per-account limits"},
        {"name": "CDC + Streams", "role": "Seat/ticket changes to availability + analytics"},
        {"name": "Analytics Plane", "role": "Real-time sales velocity for artist/promoter"},
    ],
    detailed_design={
        "seat_inventory_model": (
            "Inventory is one row per (event_id, seat_id) — the venue's seat catalog cloned for "
            "the event with price tier and current state (OPEN / HELD / SOLD / BLOCKED). This is "
            "deliberately finer-grained than a hotel's (room_type, date) because customers care "
            "exactly which seat they got — Section 113 Row 4 Seat 12 is not interchangeable with "
            "Section 113 Row 4 Seat 13. The contention surface is therefore much wider but also "
            "far more parallel: only two users colliding on the literal same seat compete; "
            "neighbouring seats sell independently. The seat_id is a stable ULID that survives "
            "across events at the same venue and is the same identifier the gate scanner reads."
        ),
        "virtual_waiting_room": (
            "On-sale opens at a fixed instant; left unprotected, the buying plane melts. The "
            "queue is its own service, separately scalable and stateless on a Redis-backed "
            "sorted set per event. Users hit /queue/enter with CAPTCHA + device fingerprint; "
            "the service records (queue_token, joined_at, shuffled_position). Fairness comes "
            "from shuffling within bands: everyone who arrived in the first 60 s gets a random "
            "shuffled_position so the user with the fastest connection doesn't dominate. The "
            "admission scheduler reads the next N tokens and marks them ADMITTED with a short "
            "TTL window during which they may call /holds. Admit-rate is tuned to keep the "
            "buying plane comfortable (typically thousands per second, never the millions in "
            "the queue). Users see a position estimate that shrinks; abandoned tokens are "
            "expired so they don't permanently shrink the queue's effective capacity."
        ),
        "hold_concurrency": (
            "Once admitted, a user clicks specific seats and we acquire a hold. Two layers: a "
            "short-lived Redis SETNX with a TTL of ~7 minutes per seat_id (key = "
            "event:{id}:seat:{seat_id}, value = hold_id, NX + EX 420), and a durable UPDATE on "
            "event_seats SET state='HELD', hold_id=?, version=version+1 WHERE event_id=? AND "
            "seat_id=? AND state='OPEN' AND version=?. Redis is the front-line lock — it "
            "absorbs the burst and self-heals on TTL — and the DB CAS is the durable invariant. "
            "If Redis succeeds but the DB CAS loses (rare, only under reconciliation), the "
            "Redis lock is released and the user retries. This pairing keeps p99 hold latency "
            "low while preserving the durable single-source-of-truth in Postgres. Distributed "
            "Redlock is not required: a hold is short-lived and idempotent on retry, and the DB "
            "CAS catches any Redis split-brain."
        ),
        "checkout_saga": (
            "Hold → AuthorisePayment → IssueTickets, with compensations ReleaseHold and Refund. "
            "Each step appends a ticket_event with monotonic seq. AuthorisePayment fails or "
            "times out → ReleaseHold (CAS state back to OPEN, delete Redis lock). Auth succeeds "
            "but IssueTickets fails after partial issue → Refund the unissued portion and the "
            "issued ones are kept (they are real tickets the user paid for). Idempotency keys "
            "on every external call mean retries are safe; the saga state is the event log, not "
            "in-memory orchestrator state, so a crash mid-saga is recoverable by scanning "
            "non-terminal sagas."
        ),
        "anti_scalper": (
            "Layered controls, each catching a different abuser class. (1) CAPTCHA + JS "
            "challenges at queue entry filter trivial scripts. (2) Account verification (email "
            "+ phone + optional ID) raises the marginal cost of a fake account. (3) Per-account "
            "purchase-limit per event enforced at hold time and re-checked at order time, with "
            "a unique partial index on (event_id, user_id) summed across confirmed orders. "
            "(4) Device-fingerprint + IP rate limits stop one user driving 1000 accounts from "
            "the same browser. (5) Behavioural risk score (mouse entropy, time-to-click, "
            "purchase velocity history) feeds a soft-drop list — risky tokens go into a slower "
            "queue lane, not a hard reject, to avoid false-positive ops storms. (6) Promoters "
            "configure per-event tightness (e.g. 'tour pre-sale: ID required, limit 4, no "
            "transfer for 72h')."
        ),
        "dynamic_pricing": (
            "For top hits, prices are not flat. The Pricing Service publishes a per-(event, "
            "section, tier) curve (or even per-seat for platinum) updated in near real time as "
            "demand develops. The price the user pays is the value at hold-time, locked into "
            "the hold record. If the hold expires the user picks again and a fresh price "
            "applies. Price is never re-evaluated mid-checkout — that's a textbook UX/legal "
            "trap. This separation also lets analytics replay 'what would revenue have been at "
            "tier curve X' offline."
        ),
        "presales": (
            "Fan-club / Amex / artist presales are a gated subset of seats and a code-bounded "
            "redemption pool. The presale_codes table tracks max_redemptions and current "
            "redemptions; the queue-entry endpoint accepts a presale_code and routes the user "
            "into a separate per-presale queue with its own admission rate. A successful hold "
            "atomically increments the code's redemption counter — exceeding it bounces the "
            "hold. The same seat catalog is shared, with rows tagged with which presale tiers "
            "they're eligible for so that a presale user sees a strictly larger map than the "
            "general public on-sale."
        ),
        "rotating_barcodes": (
            "Static barcodes are a screenshot-resale gift. Real tickets are rotating: the "
            "official app exchanges (ticket_id, device-attested session) for a short-lived "
            "signed token (JWT-style; jti, ticket_id, expires_at ≤ 30 s, signed by the gate "
            "verifier's public key). The app refreshes every few seconds while displayed; a "
            "screenshot is dead in 30 s. The gate scanner verifies signature offline against "
            "the event's signing public key and POSTs a scan record back when online; replay "
            "is defeated because each jti is single-use and recorded server-side. Legacy paper "
            "tickets exist for accessibility / no-smartphone cases and are issued under the "
            "same ticket row but with a flag — they're matched against ticket_id + an ID check "
            "at the gate, not bare scan."
        ),
        "resale_market": (
            "A resale listing is a transition on the ticket row, not a new ticket. POST "
            "/resale/listings flips state LISTED with an ask_cents under a policy cap "
            "(promoter-configured: face-value cap, % cap, or unrestricted). POST "
            "/resale/{listing}/buy runs a saga: AuthorisePayment buyer → in one DB transaction "
            "transfer ticket ownership (owner_user_id := buyer, state := VALID, version+1) and "
            "append events TicketTransferred + ListingSold; CapturePayment; pay seller the net. "
            "The seller's app sees the ticket leave their wallet immediately on commit, and "
            "any rotating barcodes it had cached are invalidated by a token-version bump on "
            "the ticket row. There is no window in which both seller and buyer could enter — "
            "the ownership swap and the token-version bump are the same DB transaction."
        ),
        "scan_and_revocation": (
            "Gate scanners verify the rotating token's signature locally and call "
            "/scan/verify when online with (jti, gate_id). The verifier marks the jti consumed "
            "and atomically transitions the ticket to SCANNED. A revoked or transferred ticket "
            "fails verification because its token-version no longer matches; the verifier "
            "carries a small bloom filter of revoked ticket_ids pre-event for offline cases. "
            "Re-entry is supported via re-issuing a fresh token to the same ticket; the "
            "scanner allows N scans bounded by event policy."
        ),
        "real_time_analytics": (
            "Seat state changes and ticket events stream off a CDC tail (Debezium) into Kafka. "
            "A Flink / ksqlDB job aggregates per-event sold-per-minute, revenue-per-minute, "
            "section heatmaps, presale vs onsale breakdown, and writes to a serving store "
            "(ClickHouse / Pinot). The artist / promoter dashboard reads from there with p95 "
            "< 5 s freshness. The same stream powers ops dashboards: queue depth, admission "
            "rate, hold rate, payment success, abuse-signal rate."
        ),
        "slo_contract": (
            "Hold p99 < 300 ms after admission; checkout p99 < 2 s; double-booking probability "
            "≈ 0 under the Redis+CAS pairing; barcode-token TTL ≤ 30 s; sales-velocity "
            "freshness p95 < 5 s; ticket history reconstructable for 7 years."
        ),
    },
    trade_offs=[
        {"option": "Per-seat vs per-tier inventory model",
         "for_per_seat": "Customers pick exact seat; matches venue UX; parallelisable",
         "for_per_tier": "Far fewer rows, easier to scale headline counts",
         "recommendation": "Per-seat. The contention is naturally distributed across the seat "
         "set; per-tier collapses everyone onto one row."},
        {"option": "DB row lock vs Redis SETNX+TTL for the hold",
         "for_db_lock": "Single source of truth; trivially serialisable",
         "for_redis": "Absorbs the on-sale burst; self-heals via TTL; sub-ms",
         "recommendation": "Both, layered — Redis SETNX as the front-line lock, DB CAS as the "
         "durable invariant. Neither alone survives both burst and crash."},
        {"option": "Open buying directly vs virtual waiting room",
         "for_open": "Simpler; first-come-first-served feels fair",
         "for_queue": "Survives the burst; admits at a rate the buying plane can serve; fair "
         "with shuffled bands",
         "recommendation": "Waiting room. Open-front-door at 5M concurrent is operational "
         "suicide and FCFS punishes anyone with a slower link."},
        {"option": "Static barcode vs rotating barcode",
         "for_static": "Works in any wallet app; simple",
         "for_rotating": "Defeats screenshot resale; per-scan replay-proof",
         "recommendation": "Rotating in the official app for digital tickets; static + ID-check "
         "for the legacy paper minority."},
        {"option": "Allow off-platform resale vs first-party verified resale",
         "for_off": "Lower platform liability; no secondary infra",
         "for_first_party": "Atomic transfer + invalidation; protects buyer from forged tickets",
         "recommendation": "First-party verified resale — it is the only design where the "
         "buyer can't be defrauded with a screenshot."},
        {"option": "2PC vs Saga across hold + payment + ticket issue",
         "for_2pc": "Atomic to caller",
         "for_saga": "Works with external PSPs; recoverable; idempotent",
         "recommendation": "Saga. PSPs don't vote — same reasoning as any booking system."},
    ],
    tips=[
        "Lead with the inventory key: per-seat. Distinguish from hotel (room_type, date) — "
        "interviewer is watching for that comparison.",
        "Name the on-sale burst explicitly and put the waiting room before everything else. "
        "Without it your buying plane never reaches first contact.",
        "Walk the hold concurrency in two layers (Redis SETNX + DB CAS). Picking only one is "
        "the senior trap — burst-only or durability-only is wrong.",
        "Treat anti-scalper as a layered control surface, not one switch. Name the layers.",
        "Rotating barcodes is a senior signal — most candidates draw a static QR.",
        "Resale is a state transition on the same ticket, not a re-issue. Atomicity of "
        "ownership-swap + token-version-bump is the load-bearing detail.",
        "Dynamic pricing is locked at hold-time, never re-evaluated mid-checkout.",
    ],
    thought_process=[
        "1. Clarify scope: seat-map browsing, on-sale burst, hold + checkout, presales, "
        "anti-scalper, rotating barcodes, resale, gate scan, real-time analytics.",
        "2. Estimate: 1-5M concurrent at on-sale, ~50K seats per popular venue, ~50-100K "
        "purchases/sec peak, ~500M tickets/year globally.",
        "3. Lock the inventory model: per (event_id, seat_id), not per tier.",
        "4. Identify the burst: on-sale instant. Gate everything behind a virtual waiting room "
        "with shuffled-band fairness and a tunable admission rate.",
        "5. APIs: queue/enter, queue/status, holds, orders, tickets/barcode, transfer, "
        "resale/listings, resale/buy, scan/verify, analytics velocity.",
        "6. Schema: events, event_seats (CAS row), holds, orders, tickets + ticket_events, "
        "barcode_tokens, resale_listings, queue_tokens, payments, abuse_signals, presale_codes.",
        "7. Hold concurrency: Redis SETNX+TTL as front-line + DB version-CAS as durable; "
        "Redlock not needed — the DB is the truth.",
        "8. Checkout as saga: Hold → Auth → IssueTickets, with ReleaseHold + Refund "
        "compensations; idempotency keys on every external call.",
        "9. Anti-scalper as a layered surface: CAPTCHA + account verify + per-account limit + "
        "device + IP + behavioural score; tunable per event.",
        "10. Rotating-barcode tokens minted only by the official app, ≤30 s TTL, signature "
        "verified offline at the gate; jti single-use server-side.",
        "11. Resale as ticket-row state transition (LISTED → SOLD); buy is atomic transfer + "
        "token-version bump in one DB transaction.",
        "12. CDC + stream processor for real-time sales velocity to dashboards.",
    ],
    tags=["ticketing", "high-contention", "queue", "anti-abuse", "payments", "fraud"],
    arch_nodes=[
        {"id": "client", "label": "Fan App / Web", "type": "client"},
        {"id": "edge", "label": "Edge / WAF / Bot Mgmt", "type": "lb"},
        {"id": "queue", "label": "Virtual Waiting Room", "type": "service"},
        {"id": "lb", "label": "API Gateway", "type": "lb"},
        {"id": "cat", "label": "Catalog / Event", "type": "server"},
        {"id": "inv", "label": "Inventory Service", "type": "server"},
        {"id": "hold", "label": "Hold Service (Redis)", "type": "cache"},
        {"id": "ord", "label": "Order / Saga", "type": "server"},
        {"id": "price", "label": "Pricing Service", "type": "server"},
        {"id": "pay", "label": "Payment Service", "type": "server"},
        {"id": "psp", "label": "PSP (Stripe/Adyen)", "type": "service"},
        {"id": "tic", "label": "Ticket Service", "type": "server"},
        {"id": "bar", "label": "Barcode Service", "type": "server"},
        {"id": "gate", "label": "Gate Verifier", "type": "service"},
        {"id": "resale", "label": "Resale Market", "type": "server"},
        {"id": "risk", "label": "Anti-Abuse / Risk", "type": "service"},
        {"id": "invdb", "label": "Inventory DB", "type": "database"},
        {"id": "ticdb", "label": "Ticket Event Log", "type": "database"},
        {"id": "cdc", "label": "CDC / Streams", "type": "service"},
        {"id": "analytics", "label": "Sales Velocity", "type": "database"},
    ],
    arch_edges=[
        {"source": "client", "target": "edge"},
        {"source": "edge", "target": "queue", "label": "queue/enter"},
        {"source": "edge", "target": "lb"},
        {"source": "queue", "target": "lb", "label": "admit"},
        {"source": "lb", "target": "cat", "label": "browse"},
        {"source": "lb", "target": "ord", "label": "hold/order"},
        {"source": "lb", "target": "tic", "label": "wallet"},
        {"source": "lb", "target": "resale", "label": "list/buy"},
        {"source": "lb", "target": "bar", "label": "barcode mint"},
        {"source": "ord", "target": "hold", "label": "SETNX seat"},
        {"source": "ord", "target": "inv", "label": "CAS seat row"},
        {"source": "ord", "target": "price", "label": "quote"},
        {"source": "ord", "target": "pay", "label": "auth/capture"},
        {"source": "ord", "target": "tic", "label": "issue"},
        {"source": "ord", "target": "risk", "label": "score"},
        {"source": "pay", "target": "psp"},
        {"source": "inv", "target": "invdb"},
        {"source": "tic", "target": "ticdb", "label": "append events"},
        {"source": "bar", "target": "client", "label": "rotating token"},
        {"source": "client", "target": "gate", "label": "scan"},
        {"source": "gate", "target": "tic", "label": "consume jti"},
        {"source": "resale", "target": "tic", "label": "transfer"},
        {"source": "invdb", "target": "cdc", "label": "CDC"},
        {"source": "ticdb", "target": "cdc", "label": "CDC"},
        {"source": "cdc", "target": "analytics", "label": "rollups"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant U as Fan\n"
        "  participant Q as Waiting Room\n"
        "  participant API\n"
        "  participant ORD as Order Saga\n"
        "  participant R as Redis Hold\n"
        "  participant INV as Inventory\n"
        "  participant PAY as Payment\n"
        "  participant TIC as Ticket Svc\n"
        "  U->>Q: POST /queue/enter (captcha, fp)\n"
        "  Q-->>U: queue_token (waiting)\n"
        "  Q->>U: admitted (batch)\n"
        "  U->>API: POST /holds (seat_ids[])\n"
        "  API->>ORD: HoldSeats\n"
        "  ORD->>R: SETNX seat:{id} hold_id EX 420\n"
        "  R-->>ORD: ok\n"
        "  ORD->>INV: CAS state=HELD, version+1\n"
        "  INV-->>ORD: ok\n"
        "  ORD-->>U: hold_id (7 min)\n"
        "  U->>API: POST /orders (hold_id, payment)\n"
        "  API->>ORD: ConfirmOrder\n"
        "  ORD->>PAY: Authorise(amount, idem)\n"
        "  PAY-->>ORD: AUTH_OK\n"
        "  ORD->>INV: CAS state=SOLD\n"
        "  ORD->>TIC: IssueTickets + append events\n"
        "  ORD-->>U: 201 order + tickets\n"
        "  Note over ORD,PAY: Auth fail → ReleaseHold compensation\n"
        "  Note over ORD,TIC: Issue fail post-auth → Refund compensation"
    ),
    er_diagram=(
        "erDiagram\n"
        "  VENUE ||--o{ VENUE_SEAT : has\n"
        "  VENUE ||--o{ EVENT : hosts\n"
        "  EVENT ||--o{ EVENT_SEAT : per-seat\n"
        "  EVENT ||--o{ PRESALE_CODE : gates\n"
        "  EVENT ||--o{ QUEUE_TOKEN : waiting-room\n"
        "  EVENT_SEAT }o--|| VENUE_SEAT : refers\n"
        "  HOLD }o--o{ EVENT_SEAT : locks\n"
        "  ORDER ||--|| HOLD : consumes\n"
        "  ORDER ||--o{ TICKET : issues\n"
        "  ORDER ||--o{ PAYMENT : auth-capture-refund\n"
        "  TICKET ||--o{ TICKET_EVENT : log\n"
        "  TICKET ||--o{ BARCODE_TOKEN : rotating\n"
        "  TICKET ||--o| RESALE_LISTING : listed"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B[Pick inventory key: per seat]\n"
        "  B --> C[Identify burst: on-sale instant]\n"
        "  C --> D[Virtual waiting room + shuffled fairness]\n"
        "  D --> E{Hold concurrency?}\n"
        "  E -->|Redis SETNX+TTL| F[Front-line lock]\n"
        "  E -->|DB version CAS| G[Durable invariant]\n"
        "  F --> H[Checkout saga]\n"
        "  G --> H\n"
        "  H --> I[Hold -> Auth -> IssueTickets]\n"
        "  I --> J{Step fails?}\n"
        "  J -->|payment fail| K[ReleaseHold]\n"
        "  J -->|issue fail post-auth| L[Refund]\n"
        "  H --> M[Rotating barcode tokens]\n"
        "  M --> N[Gate verify + jti consume]\n"
        "  H --> O[Resale = ticket state transition]\n"
        "  H --> P[CDC -> sales velocity]"
    ),
    tradeoff_title="Hold Concurrency: DB Row Lock vs Redis SETNX+TTL",
    tradeoff_options=[
        {"label": "DB pessimistic SELECT … FOR UPDATE per seat",
         "description": "Take a row lock on (event_id, seat_id) before flipping state to HELD.",
         "pros": ["Trivially serialisable",
                 "Single source of truth",
                 "No cache-vs-DB skew to worry about"],
         "cons": ["Lock queue under on-sale burst saturates DB connections",
                 "Long-held locks block neighbouring writers and readers",
                 "Tail latency explodes precisely when traffic peaks"]},
        {"label": "Redis SETNX with TTL only",
         "description": "Take a Redis lock per seat with EX 420; commit purchase asynchronously.",
         "pros": ["Sub-millisecond happy path",
                 "Self-healing via TTL — abandoned holds vanish without sweeper",
                 "Absorbs the on-sale burst easily"],
         "cons": ["Redis split-brain or eviction can lose locks",
                 "Not the durable source of truth — needs a back-write",
                 "Money path on a cache alone is risky"]},
        {"label": "Redis SETNX+TTL front + DB version-CAS durable (chosen)",
         "description": "Acquire Redis lock, then UPDATE event_seats SET state='HELD', "
         "version=version+1 WHERE … AND state='OPEN' AND version=:v. Both must succeed.",
         "pros": ["Burst-safe via Redis; durable via DB CAS",
                 "DB CAS catches any Redis split-brain — the truth wins",
                 "Compensations are simple: release the Redis key, no DB rollback needed if "
                 "CAS lost"],
         "cons": ["Two systems to operate",
                 "Slightly more code on the happy path",
                 "Requires clear ownership of which layer is authoritative"]},
    ],
    tradeoff_rec=(
        "Use Redis SETNX+TTL as the front-line lock with a 7-minute TTL, paired with a DB "
        "version-CAS as the durable invariant. The DB is authoritative — Redis is the burst "
        "absorber. Avoid pure-DB-lock at on-sale (lock queue saturation) and avoid pure-Redis "
        "on the money path (no durable truth)."
    ),
    senior_topics=[
        _topic("seat-level-contention",
               "Per-Seat Inventory and Why It's Not Like Hotel (Room-Type, Date)",
               "Seats are not interchangeable like hotel rooms of a type — the contention "
               "surface is wider but more parallel, and the model has to honour that.",
               [
                   ("The model",
                    "One row per (event_id, seat_id) with state OPEN / HELD / SOLD / BLOCKED, "
                    "price tier, and a version for CAS. The seat_id is a stable ULID from the "
                    "venue's seat catalog and is the same identifier the gate scanner reads."),
                   ("Why not per-tier",
                    "Per-tier collapses everyone targeting Section 113 onto one row, recreating "
                    "the hotel's last-room hot-cell at every tier. Per-seat distributes the "
                    "load: only literal collisions on the same seat compete, and adjacent seats "
                    "sell entirely in parallel. Customers also pick exactly which seat they "
                    "want; a tier-only model can't render the seat map."),
                   ("Comparison to hotel",
                    "Hotels: (property, room_type, date) — finite hot rows, last-room is the "
                    "scarcity story. Concerts: (event, seat) — millions of rows but the user "
                    "wants this exact seat; locality of contention is high, breadth of "
                    "contention is wide. Different concurrency calculus despite both being "
                    "'inventory CAS'."),
                   ("Block holds (parties)",
                    "A party of four wants four contiguous seats; the hold operation takes a "
                    "list of seat_ids and either acquires all locks or releases acquired ones "
                    "and aborts — partial holds are never returned."),
               ],
               diagram=(
                   "graph LR\n"
                   "  E[Event] --> S1[Section 113 Row 4 Seat 11: OPEN]\n"
                   "  E --> S2[Section 113 Row 4 Seat 12: HELD by U1]\n"
                   "  E --> S3[Section 113 Row 4 Seat 13: SOLD]\n"
                   "  E --> S4[Section 113 Row 4 Seat 14: OPEN]"
               )),
        _topic("waiting-room-fairness",
               "Virtual Waiting Room with Shuffled-Band Fairness",
               "How a waiting room admits millions fairly into a buying plane that can only "
               "serve thousands per second, without first-come-first-served punishing slow "
               "connections.",
               [
                   ("The burst",
                    "On-sale opens at a fixed instant. Without protection the buying plane sees "
                    "millions of /buy in the same second; databases, payment providers, and "
                    "session stores all melt. The queue's job is to time-shift the load into "
                    "what downstream can serve."),
                   ("Shuffled-band fairness",
                    "Pure FCFS punishes anyone with higher latency to the front door — bots and "
                    "users on fast university links win every time. We bucket arrivals into "
                    "60-second bands and randomise position within a band. Within a band you're "
                    "equal whether you arrived at second 1 or second 59; bot networks lose "
                    "their latency edge."),
                   ("Admission rate control",
                    "An admission scheduler reads the next N tokens per second and marks them "
                    "ADMITTED with a short window during which they can call /holds. N is "
                    "tuned by the buying plane's headroom — we'd rather hold the queue moving "
                    "than overwhelm payments."),
                   ("Abandonment and ETA",
                    "Tokens not used within their admission window expire. Position estimates "
                    "are computed from current admission rate so users see a shrinking ETA. "
                    "Without abandonment expiry the queue's 'effective length' grows forever "
                    "as users close their tabs."),
                   ("Per-event tunability",
                    "Promoter sets band size, admission rate, presale lane weighting per event. "
                    "Trial runs (small artists) at low rates; mega tours at maximum hardware."),
               ],
               diagram=(
                   "graph LR\n"
                   "  A[Millions of fans] --> B[CAPTCHA + JS challenge]\n"
                   "  B --> C[Queue: shuffled band per minute]\n"
                   "  C --> D[Admission scheduler: N/sec]\n"
                   "  D --> E[Buying plane]\n"
                   "  C --> X[Abandoned tokens expire]"
               )),
        _topic("rotating-barcodes",
               "Rotating Barcode Tokens — Defeating Screenshot Resale",
               "Why static QRs are a fraud gift and how short-lived signed tokens close the "
               "screenshot-resale attack while staying offline-tolerant for the gate.",
               [
                   ("Why static fails",
                    "A static barcode can be screenshotted, posted on classifieds, and "
                    "scanned at the gate by whoever arrives first; the legitimate owner gets "
                    "rejected with no recourse. Even hashed barcodes are cloneable."),
                   ("The token shape",
                    "Short-lived signed tokens (JWT-style) with payload {jti, ticket_id, "
                    "exp ≤ 30 s, token_version}, signed by the event's signing key. The official "
                    "app refreshes every few seconds while displayed; a screenshot is dead in "
                    "30 s."),
                   ("Offline gate verification",
                    "Gate scanners hold the public key for the event and verify the signature "
                    "locally — they do not need to reach the backend during a brief WAN "
                    "outage. They sync scan records when online and consume jti server-side "
                    "to defeat replay."),
                   ("Revocation and transfer",
                    "On transfer / resale, the ticket's token_version bumps; the seller's "
                    "cached tokens fail signature-vs-version check at the gate. Pre-event "
                    "revocations push a small bloom filter to scanners for offline coverage."),
                   ("Legacy paper",
                    "A small share of tickets are physical / printed for accessibility and "
                    "no-smartphone cases. They share the ticket row with a flag and are matched "
                    "at the gate against ticket_id + ID check, not bare scan."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant App\n"
                   "  participant BS as Barcode Svc\n"
                   "  participant Gate\n"
                   "  participant TIC as Ticket Svc\n"
                   "  App->>BS: POST /tickets/{id}/barcode (device attest)\n"
                   "  BS-->>App: signed token (exp=now+30s)\n"
                   "  App-->>App: rotate every 5s while shown\n"
                   "  App->>Gate: present token\n"
                   "  Gate->>Gate: verify signature offline\n"
                   "  Gate->>TIC: consume jti (when online)\n"
                   "  TIC-->>Gate: ok / already-consumed / revoked"
               )),
        _topic("verified-resale",
               "First-Party Verified Resale — Atomic Transfer + Invalidation",
               "Why resale is a state transition on the same ticket row rather than a re-issue, "
               "and how that closes the double-entry attack and the fake-ticket attack at once.",
               [
                   ("The attack we close",
                    "Off-platform resale lets the seller hand a screenshot to the buyer and "
                    "still walk in themselves, or sell a forged ticket entirely. First-party "
                    "verified resale prevents both because the platform is the source of truth "
                    "for who currently owns the ticket."),
                   ("State machine",
                    "VALID → LISTED (seller posts ask) → SOLD (buyer pays) → VALID (under new "
                    "owner). The ticket_id never changes; only owner_user_id and "
                    "token_version do."),
                   ("Atomic transfer",
                    "POST /resale/{listing}/buy runs: AuthorisePayment buyer; in one DB "
                    "transaction set owner_user_id=buyer, token_version+1, append "
                    "TicketTransferred + ListingSold events; CapturePayment; pay seller net of "
                    "platform fee. The seller's wallet loses the ticket the moment the "
                    "transaction commits; their cached barcodes fail at the gate from the next "
                    "rotation."),
                   ("Price caps and policy",
                    "Each event has a resale policy (face-value cap, % cap, or unrestricted). "
                    "The Listing endpoint validates ask_cents against the cap; promoters tune "
                    "this per event."),
                   ("Why not allow off-platform listings",
                    "We can't atomically invalidate a ticket we don't own the transfer of. "
                    "Off-platform resale is fundamentally incompatible with rotating-barcode "
                    "verification — the design hangs together only if the platform is the "
                    "transfer authority."),
               ],
               diagram=(
                   "stateDiagram-v2\n"
                   "  [*] --> VALID\n"
                   "  VALID --> LISTED: seller lists\n"
                   "  LISTED --> VALID: seller cancels\n"
                   "  LISTED --> SOLD: buyer pays (atomic)\n"
                   "  SOLD --> VALID: ownership=buyer, token_version+1\n"
                   "  VALID --> SCANNED: gate verify\n"
                   "  VALID --> REVOKED: refund/fraud\n"
                   "  SCANNED --> [*]\n"
                   "  REVOKED --> [*]"
               )),
        _topic("anti-scalper-layers",
               "Layered Anti-Scalper Controls — Why One Switch Isn't Enough",
               "Each control catches a different abuser class. Together they raise the marginal "
               "cost of buying at scale to the point where most scalpers quit.",
               [
                   ("CAPTCHA + JS challenges",
                    "Filter trivial scripts and headless browsers; cheap, well-understood, low "
                    "false-positive rate. First gate, never the only gate."),
                   ("Account verification",
                    "Email + phone (+ ID for high-trust events) raises the cost of a fake "
                    "account. Combined with per-account purchase limits this caps any single "
                    "identity's haul."),
                   ("Per-account purchase limit",
                    "Enforced at hold time and re-checked at order time, summed across "
                    "confirmed orders for the event. Unique partial index makes the "
                    "enforcement atomic."),
                   ("Device-fingerprint + IP rate limit",
                    "Stops one user driving 1000 accounts from the same browser or NAT. We "
                    "score (fp, ip) tuples and rate-limit aggressively at the queue door."),
                   ("Behavioural risk score",
                    "Mouse entropy, time-to-click, purchase-velocity history. Risky tokens go "
                    "to a slower queue lane (soft drop) rather than a hard reject — false "
                    "positives are an ops storm."),
                   ("Per-event policy",
                    "Promoter dials each layer's tightness per event: 'no transfer for 72 h', "
                    "'ID required at gate', 'limit 4', 'verified fan only'. The platform's "
                    "value is letting the promoter tune anti-abuse without code deploy."),
               ],
               diagram=(
                   "graph LR\n"
                   "  REQ[Request] --> EDGE[CAPTCHA + JS]\n"
                   "  EDGE --> ACC[Account verify]\n"
                   "  ACC --> RATE[Device + IP rate limit]\n"
                   "  RATE --> RISK[Behavioural score]\n"
                   "  RISK -->|low| Q[Normal queue]\n"
                   "  RISK -->|medium| QS[Slow queue lane]\n"
                   "  RISK -->|high| BLOCK[Reject]\n"
                   "  Q --> LIMIT[Per-account limit at hold]\n"
                   "  QS --> LIMIT"
               )),
    ],
)
