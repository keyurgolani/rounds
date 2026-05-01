"""Food Delivery (Uber Eats / DoorDash) system design question.
Loaded automatically via `sd_questions._load_more` because this module
exposes `PAYLOAD`."""
from __future__ import annotations

from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design Food Delivery (Uber Eats / DoorDash)",
    "Hard",
    "Design a three-sided food-delivery marketplace connecting customers, restaurants, and couriers. "
    "Customers browse a localised restaurant catalog, place orders against live menus, and watch a "
    "courier carry the food to their door in real time. Restaurants accept orders, prep food, and "
    "hand off to couriers. Couriers receive dispatches, accept or reject within seconds, and stream "
    "their location during pickup and drop-off. The system must compute fares with surge pricing, "
    "predict ETAs, run payments, and notify all three parties through every state transition. "
    "Focus on the order lifecycle and the dispatch hot path; defer broad analytics, fraud, and "
    "loyalty programs.",
    hints=[
        "Three-sided marketplace — customer, restaurant, courier — each with a different SLO and a different failure mode.",
        "Order lifecycle is a state machine: created → confirmed → prepping → ready → picked-up → en-route → delivered. Persist the FSM, never derive it.",
        "Dispatch is geohash/H3 candidate query + scoring + reject-retry within ~30s — bound the search and the offer timer.",
        "Restaurant menu is a separate read-heavy service with its own caching shape; menu edits invalidate item lists, not whole carts.",
        "Real-time courier location: gRPC bidi or MQTT for the courier app; WebSocket fan-out to customer app. Don't reuse one transport for all hops.",
        "ETA is an ML model (prep time + travel time + handoff overhead) — never a static constant.",
        "Surge / busy-pricing is decoupled from dispatch — periodic batch reads supply/demand grid.",
        "Payment authorises at order placement, captures at delivery — two-phase, async from the user-visible flow.",
    ],
    constraints=[
        "100M+ customers, ~5M restaurants, ~3M couriers globally; ~500K couriers concurrently online",
        "30M+ orders/day at peak; lunch and dinner spikes 5–8× off-peak",
        "Order placement → courier matched p99 < 30s",
        "Courier location update every 3–5s during active delivery",
        "Customer ETA accuracy MAE target < 3 minutes",
        "Payment authorisation pre-confirm; capture on delivery",
        "Courier offer-to-accept timer ≤ 15s; reject-retry chain ≤ 3 hops",
        "Restaurants must be able to edit menu pricing and 86 items in seconds",
    ],
    req_func=[
        "Customer: search and browse restaurants by location, cuisine, rating, delivery time",
        "Customer: view restaurant menu with live availability and prices, build cart, place order",
        "Customer: track order status and live courier location end-to-end",
        "Restaurant: receive order, accept/reject, set prep time, mark ready, hand off to courier",
        "Restaurant: edit menu, prices, photos; toggle items 86'd in real time; pause new orders",
        "Courier: go online/offline, receive offers, accept/reject, navigate to pickup and drop-off, mark events",
        "Courier: stream live location during active delivery",
        "Dispatch: match orders to courier with geohash candidate + score + reject-retry chain",
        "Pricing: compute fare = food + delivery fee + service fee + tip + surge multiplier",
        "ETA: predict prep time + travel time + handoff for customer-facing countdown",
        "Notifications: push to all three parties on every state transition",
        "Payment: authorise at order placement; capture on delivery; refund on cancel",
    ],
    req_nonfunc=[
        "Order placement → courier matched p99 < 30s",
        "Live tracking position lag p99 < 5s",
        "99.95% availability for the order placement and dispatch path",
        "Menu read p99 < 100ms (edge-cached); menu write propagates in < 5s",
        "Geographic data partitioning — request from SF hits SF shard",
        "Eventual consistency on analytics, ratings, payouts; strong consistency on order state and payment",
        "Courier app battery-friendly (adaptive ping interval)",
        "Idempotent order placement and payment — never double-charge or double-deliver on retry",
    ],
    estimation={
        "customers": "100M (~30M MAU)",
        "restaurants": "5M (~2M active in any week)",
        "couriers": "3M registered, ~500K concurrently online at peak",
        "orders_per_day": "30M peak; ~6× lunch/dinner spike vs off-peak",
        "qps_order_create": "~700/sec steady; ~5K/sec at meal peak",
        "qps_menu_read": "~50K/sec steady; ~300K/sec at peak (edge-cached)",
        "location_pings": "500K couriers × 12 pings/min = 6M/min during active deliveries",
        "active_deliveries_concurrent": "~300K at peak",
        "payment_volume": "~$300M/day GMV",
        "storage_per_order": "~5KB structured + ~0.5MB historical telemetry",
    },
    endpoints=[
        {"method": "GET", "path": "/restaurants",
         "description": "Localised restaurant search/feed by lat/lng, cuisine, filters",
         "body": "?lat&lng&cuisine&open_now&max_eta&cursor"},
        {"method": "GET", "path": "/restaurants/{id}/menu",
         "description": "Live menu with availability + prices",
         "body": "?lat&lng (for delivery feasibility + price zone)"},
        {"method": "POST", "path": "/orders",
         "description": "Place order; authorises payment and triggers dispatch",
         "body": "{restaurant_id, items:[{id, qty, mods}], dropoff, tip_cents, idempotency_key}"},
        {"method": "GET", "path": "/orders/{id}",
         "description": "Current order state + courier position (WebSocket upgrade for live)"},
        {"method": "POST", "path": "/orders/{id}/cancel",
         "description": "Customer-initiated cancel (subject to state)"},
        {"method": "POST", "path": "/restaurants/{id}/orders/{order_id}/accept",
         "description": "Restaurant accepts and sets prep time"},
        {"method": "POST", "path": "/restaurants/{id}/menu",
         "description": "Edit menu items / 86 items / pause orders"},
        {"method": "POST", "path": "/couriers/online",
         "description": "Courier goes online; opens dispatch eligibility"},
        {"method": "POST", "path": "/couriers/location",
         "description": "Courier location ping (gRPC bidi stream preferred)",
         "body": "{lat, lng, heading, speed, battery, accuracy}"},
        {"method": "POST", "path": "/dispatch/offers/{offer_id}/respond",
         "description": "Courier accepts or rejects an offer",
         "body": "{accept: bool}"},
        {"method": "POST", "path": "/couriers/events",
         "description": "Courier marks pickup/arrival/delivered events",
         "body": "{order_id, event, ts, lat, lng}"},
        {"method": "GET", "path": "/eta",
         "description": "Predict ETA for a restaurant + drop-off",
         "body": "?restaurant_id&dropoff_lat&dropoff_lng"},
        {"method": "POST", "path": "/payments/capture",
         "description": "Internal: capture authorised payment on delivery (idempotent)"},
    ],
    tables=[
        {"name": "customers",
         "columns": ["id BIGINT PK", "phone VARCHAR", "email VARCHAR",
                     "default_address JSONB", "rating FLOAT", "created_at BIGINT"]},
        {"name": "restaurants",
         "columns": ["id BIGINT PK", "name VARCHAR", "lat DOUBLE", "lng DOUBLE",
                     "geohash VARCHAR(8)", "cuisine VARCHAR", "rating FLOAT",
                     "open_hours JSONB", "is_paused BOOL", "prep_time_p50 INT"]},
        {"name": "menu_items",
         "columns": ["id BIGINT PK", "restaurant_id BIGINT", "name VARCHAR", "description TEXT",
                     "price_cents INT", "photo_url VARCHAR", "is_available BOOL",
                     "modifiers JSONB", "version BIGINT"]},
        {"name": "couriers",
         "columns": ["id BIGINT PK", "name VARCHAR", "vehicle VARCHAR(8)", "rating FLOAT",
                     "acceptance_rate FLOAT", "is_online BOOL", "is_on_delivery BOOL"]},
        {"name": "courier_locations",
         "columns": ["courier_id BIGINT PK", "lat DOUBLE", "lng DOUBLE",
                     "geohash VARCHAR(8)", "heading INT", "updated_at BIGINT"]},
        {"name": "orders",
         "columns": ["id BIGINT PK", "customer_id BIGINT", "restaurant_id BIGINT",
                     "courier_id BIGINT", "status VARCHAR(16)", "subtotal_cents INT",
                     "delivery_fee_cents INT", "service_fee_cents INT", "tip_cents INT",
                     "surge_multiplier FLOAT", "total_cents INT",
                     "dropoff_lat DOUBLE", "dropoff_lng DOUBLE",
                     "placed_at BIGINT", "ready_at BIGINT", "delivered_at BIGINT",
                     "idempotency_key VARCHAR(64) UNIQUE"]},
        {"name": "order_items",
         "columns": ["order_id BIGINT", "menu_item_id BIGINT", "qty INT",
                     "unit_price_cents INT", "modifiers JSONB",
                     "PRIMARY KEY (order_id, menu_item_id)"]},
        {"name": "dispatch_offers",
         "columns": ["id BIGINT PK", "order_id BIGINT", "courier_id BIGINT",
                     "offered_at BIGINT", "expires_at BIGINT", "score FLOAT",
                     "outcome VARCHAR(8)"]},
        {"name": "order_events",
         "columns": ["id BIGINT PK", "order_id BIGINT", "event VARCHAR(16)",
                     "actor VARCHAR(8)", "lat DOUBLE", "lng DOUBLE", "ts BIGINT"]},
        {"name": "payments",
         "columns": ["id BIGINT PK", "order_id BIGINT UNIQUE", "amount_cents INT",
                     "auth_ref VARCHAR", "capture_ref VARCHAR",
                     "status VARCHAR(12)", "updated_at BIGINT"]},
    ],
    indexes=[
        "(geohash, is_paused) on restaurants — radius search",
        "(restaurant_id, is_available) on menu_items — menu read",
        "(geohash, is_online, is_on_delivery) on courier_locations — dispatch candidate query",
        "(customer_id, placed_at DESC) on orders — order history",
        "(restaurant_id, placed_at DESC, status) on orders — restaurant tablet view",
        "(courier_id, placed_at DESC) on orders — courier earnings",
        "(order_id, ts) on order_events — audit timeline",
        "UNIQUE (idempotency_key) on orders — replay safety",
    ],
    hld_desc=(
        "Geo-sharded marketplace. Customer App, Restaurant Tablet, and Courier App all hit a regional "
        "API Gateway. Order Service owns the order FSM and is the source of truth for order state. "
        "Menu Service is a read-heavy catalog with edge cache + invalidation. Dispatch Service runs "
        "the candidate-query + score + offer-retry loop, reading driver positions from an in-memory "
        "H3 index fed by a Location Ingestor. Couriers stream locations via gRPC bidi (or MQTT for "
        "constrained networks); customers receive position updates via WebSocket. Pricing Service "
        "computes fees plus a per-cell surge multiplier (batch every ~30s). ETA Service serves an ML "
        "model combining restaurant prep estimate + travel time + handoff overhead. Payments are "
        "two-phase (auth on placement, capture on delivery) and run async via Kafka. Notifications "
        "are fan-out to APNs/FCM and to the restaurant tablet via long-poll."
    ),
    hld_components=[
        {"name": "Customer App", "role": "Browse, order, track; WebSocket for live position"},
        {"name": "Restaurant Tablet App", "role": "Receive orders, accept, mark ready, edit menu"},
        {"name": "Courier App", "role": "Online toggle, accept offers, gRPC location stream, mark events"},
        {"name": "API Gateway", "role": "Auth, region-route, rate-limit, transport upgrade"},
        {"name": "Order Service", "role": "Owns order FSM; idempotent placement; emits state events"},
        {"name": "Menu Service", "role": "Restaurant catalog reads + writes; cache invalidation"},
        {"name": "Search Service", "role": "Localised restaurant feed; Elasticsearch + filters"},
        {"name": "Dispatch Service", "role": "Candidate query, scoring, offer/retry loop"},
        {"name": "Location Ingestor", "role": "gRPC/MQTT termination; updates H3 index"},
        {"name": "H3 Geo-Index", "role": "In-memory per-region courier positions and state"},
        {"name": "Pricing Service", "role": "Fees + surge multiplier from supply/demand grid"},
        {"name": "ETA Service", "role": "ML model: prep + travel + handoff prediction"},
        {"name": "Payment Service", "role": "Two-phase auth/capture via Stripe/Adyen; async pipeline"},
        {"name": "Notification Service", "role": "APNs/FCM fan-out + restaurant tablet push"},
        {"name": "Kafka", "role": "order.* events, payment.*, courier.events backbone"},
        {"name": "Object Store + CDN", "role": "Menu photos, restaurant images, courier ID photos"},
    ],
    detailed_design={
        "order_lifecycle_fsm": (
            "Order is a finite-state machine persisted in the orders table and enforced by Order "
            "Service: created → payment_authorised → confirmed_by_restaurant → prepping → ready → "
            "courier_assigned → picked_up → en_route → delivered (terminal). Off-paths: "
            "cancelled_by_customer, cancelled_by_restaurant, refunded. Each transition writes an "
            "order_events row with actor + ts + lat/lng and emits a Kafka order.state_changed event. "
            "Transitions are guarded — only legal predecessors permitted; invalid transitions "
            "return 409. State is the source of truth; UI never derives state from telemetry."
        ),
        "dispatch_matching": (
            "On confirmed_by_restaurant, Dispatch Service queries the H3 index for online couriers "
            "within ~3–5 km of the restaurant, filtered by vehicle class and on-delivery flag. "
            "Candidates scored by: ETA-to-pickup (40%), historical acceptance rate (20%), courier "
            "rating (10%), batched-delivery feasibility (20%), idle time fairness (10%). Top "
            "candidate gets a 15s offer; on reject or timeout the next candidate is offered. After "
            "3 rejects the search radius widens and surge multiplier increases. Offer state lives "
            "in dispatch_offers with expires_at — a reaper handles stuck offers."
        ),
        "courier_location_stream": (
            "Courier App opens a gRPC bidirectional stream to Location Ingestor; falls back to "
            "MQTT-over-TLS on cellular-constrained networks. Pings every 4s while on delivery, "
            "every 30s while just online (battery save). Ingestor writes to courier_locations "
            "(KV) and updates the in-memory H3 index. Customer App receives the courier's position "
            "via a WebSocket from Order Service, which subscribes to the relevant courier feed "
            "from a Pub/Sub topic — never directly to the courier app."
        ),
        "menu_service": (
            "Menu reads dominate (>50× writes). Catalog stored in DynamoDB/Cassandra by "
            "(restaurant_id, item_id) with a per-restaurant version vector. Restaurant edits bump "
            "the version and publish a menu.changed event; edge cache (CDN + regional Redis) "
            "invalidates by restaurant_id key on receipt. 86'ing an item is a single PATCH that "
            "propagates in <5s. Carts hold (item_id, version_at_add); placement re-validates the "
            "current version and surfaces price/availability changes for confirmation."
        ),
        "eta_model": (
            "ETA = restaurant prep + courier travel-to-pickup + dwell at pickup + travel-to-dropoff "
            "+ dwell at dropoff. Prep time is a per-restaurant gradient-boosted model on "
            "(time-of-day, current order backlog, item count, item type history). Travel from a "
            "routing engine (OSRM/Valhalla) with a learned correction term for traffic and "
            "courier vehicle class. Dwell times are quantile estimates per restaurant + dropoff "
            "type. Model served at p99<50ms; refreshed every minute as state changes."
        ),
        "surge_pricing": (
            "Pricing Service runs a per-H3-cell batch every 30s computing demand (orders/min) vs "
            "supply (online couriers / on-delivery couriers). Multiplier = clipped(demand / "
            "available_supply, [1.0, 2.5]) with EMA smoothing to prevent flapping. Match path "
            "reads multiplier from a small KV; surge does NOT slow dispatch. Customers see a "
            "small busy-fee disclosure rather than the raw multiplier."
        ),
        "payment_two_phase": (
            "Order placement triggers an async authorisation hold via Payment Service through "
            "Stripe/Adyen. Order moves to payment_authorised on success, rejects on decline. "
            "Capture happens on the delivered transition, also async via Kafka. Auth-without-"
            "capture released after 7 days by reaper. Refunds on cancel are best-effort idempotent "
            "with a reconciliation job. Payment is never on the critical request path beyond the "
            "auth hold; the order flow tolerates a few seconds of payment latency."
        ),
        "search_and_filter": (
            "Restaurant feed is an Elasticsearch index with geo-distance filter + cuisine/rating/"
            "price filters + ETA estimate. Indexed nightly + near-real-time updates for "
            "is_paused, hours, rating. Personalisation overlays from a recommendation service "
            "(prior orders, cuisine affinity). Result count typically 50–100; ranking inputs "
            "include distance, ETA, rating, popularity, and personal affinity."
        ),
        "notifications": (
            "Notification Service consumes order.state_changed and dispatch.* events. Pushes via "
            "APNs/FCM for customer + courier; restaurants get a tablet push (long-poll fallback). "
            "Templates are localised; quiet hours respected per recipient. High-priority events "
            "(order accepted, courier arrived, delivered) bypass batching; low-priority (rating "
            "request, receipt) batches."
        ),
        "idempotency_and_failure": (
            "Order placement uses an idempotency_key column with UNIQUE constraint — replays "
            "return the original order_id. Payment auth uses the same key as the Stripe/Adyen "
            "idempotency key. Dispatch offers are deduplicated by (order_id, courier_id) so a "
            "retried offer doesn't duplicate. Courier event marking is idempotent on "
            "(order_id, event)."
        ),
        "geo_sharding": (
            "Region (city/metro) is the unit of sharding for order data, dispatch state, and the "
            "H3 index. Cross-region traffic is rare (delivery doesn't cross regions). Customer "
            "and restaurant records are globally read-replicated; orders pinned to the originating "
            "region. Failover plan: a region's read traffic can serve from a neighbour region with "
            "stale-by-seconds tolerance; writes block until primary recovers."
        ),
        "slo_contract": (
            "Order place→matched p99 < 30s; live position lag p99 < 5s; menu read p99 < 100ms; "
            "ETA MAE < 3 min; payment auth p99 < 3s; notification p99 < 10s; availability 99.95% "
            "for the order/dispatch path."
        ),
    },
    trade_offs=[
        {"option": "Push (offer one courier at a time) vs broadcast dispatch",
         "for_push": "Bounded courier inbox; fair; predictable acceptance signal",
         "for_broadcast": "Lower time-to-first-accept",
         "recommendation": "Push with a 15s timer + reject-retry chain. Broadcast turns into a race that hurts fairness and triggers ghost-accept thrash."},
        {"option": "gRPC bidi vs MQTT vs WebSocket for courier location",
         "for_grpc": "Strong typing, HTTP/2 multiplexing, simpler server backpressure",
         "for_mqtt": "Battery and cellular friendly; QoS levels; reconnection semantics",
         "recommendation": "gRPC primary; MQTT fallback for constrained networks. WebSocket is fine for customer app, not for courier ingest."},
        {"option": "Synchronous vs asynchronous payment",
         "for_sync": "Simpler reasoning",
         "for_async": "Decouples checkout latency from payment provider variability",
         "recommendation": "Async two-phase — auth at placement, capture at delivery. Never block the order/dispatch hot path on capture."},
        {"option": "Static ETA vs ML ETA",
         "for_static": "Trivial to implement",
         "for_ml": "Materially better MAE; adapts to time-of-day and restaurant",
         "recommendation": "ML — prep variance alone is enough to justify it. Static ETA leads to chronic optimism on lunch peaks."},
        {"option": "Batch vs single-order dispatch",
         "for_single": "Simpler ranking; lower customer wait variance",
         "for_batch": "Lower per-delivery cost; less courier idle time",
         "recommendation": "Hybrid — single-order default; batch only when both deliveries are within tight time/distance windows and customer-disclosed."},
    ],
    tips=[
        "Lead with the three-sided marketplace framing — different SLOs and failure modes per side.",
        "Order is a state machine. Persist it. Don't derive state from courier telemetry.",
        "Dispatch is bounded: cap candidates, cap offer timer, cap retry depth — every layer.",
        "Menu is a separate service with its own caching shape; don't conflate with order data.",
        "ETA is ML, not a static constant — interview signal.",
        "Two-phase payment (auth+capture) is the correct shape; never charge synchronously on tap.",
        "Idempotency keys on order placement and payment are non-negotiable for retry safety.",
        "Geo-shard everything that's hot — cross-region traffic should be rare on the dispatch path.",
    ],
    thought_process=[
        "1. Clarify scope: customer ordering, restaurant ops, courier dispatch, payments, ETA, notifications.",
        "2. Estimate: 30M orders/day, 5K QPS at meal peaks, 500K concurrent couriers, 6M location pings/min.",
        "3. APIs: /restaurants, /menu, /orders, /dispatch/offers, /couriers/location, /eta.",
        "4. Order is an FSM: created → confirmed → prepping → ready → picked-up → en-route → delivered.",
        "5. Dispatch: H3 candidate query → scored shortlist → push offer → 15s timer → retry.",
        "6. Courier location: gRPC bidi (MQTT fallback) → Location Ingestor → H3 index + Pub/Sub.",
        "7. Customer live tracking: WebSocket from Order Service, fed by courier Pub/Sub topic.",
        "8. Menu: read-heavy catalog with edge cache + invalidation on edit; per-restaurant version.",
        "9. Pricing: surge multiplier per-cell, batch every 30s; decoupled from dispatch.",
        "10. ETA: ML model (prep + travel + dwell); served at p99<50ms.",
        "11. Payment: async two-phase — auth on placement, capture on delivery, idempotent.",
        "12. Notifications: Kafka-driven fan-out to APNs/FCM and tablet long-poll.",
        "13. Geo-shard by metro; idempotent placement; SLO p99 < 30s order-to-matched.",
    ],
    tags=["marketplace", "logistics", "matching", "real-time", "geospatial"],
    arch_nodes=[
        {"id": "cust", "label": "Customer App", "type": "client"},
        {"id": "rest", "label": "Restaurant Tablet", "type": "client"},
        {"id": "cour", "label": "Courier App", "type": "client"},
        {"id": "lb", "label": "API Gateway", "type": "lb"},
        {"id": "order", "label": "Order Service", "type": "server"},
        {"id": "menu", "label": "Menu Service", "type": "server"},
        {"id": "search", "label": "Search (ES)", "type": "database"},
        {"id": "disp", "label": "Dispatch Service", "type": "server"},
        {"id": "loc", "label": "Location Ingestor", "type": "server"},
        {"id": "h3", "label": "H3 Geo-Index", "type": "cache"},
        {"id": "price", "label": "Pricing Service", "type": "server"},
        {"id": "eta", "label": "ETA Service (ML)", "type": "service"},
        {"id": "pay", "label": "Payment Service", "type": "service"},
        {"id": "notif", "label": "Notification Service", "type": "service"},
        {"id": "kafka", "label": "Kafka", "type": "queue"},
        {"id": "orderdb", "label": "Order DB", "type": "database"},
        {"id": "menudb", "label": "Menu DB", "type": "database"},
        {"id": "cdn", "label": "Media CDN", "type": "cache"},
    ],
    arch_edges=[
        {"source": "cust", "target": "lb"},
        {"source": "rest", "target": "lb"},
        {"source": "cour", "target": "lb"},
        {"source": "lb", "target": "order"},
        {"source": "lb", "target": "menu"},
        {"source": "lb", "target": "search"},
        {"source": "order", "target": "orderdb"},
        {"source": "menu", "target": "menudb"},
        {"source": "menu", "target": "cdn", "label": "photos"},
        {"source": "order", "target": "kafka", "label": "order.*"},
        {"source": "kafka", "target": "disp"},
        {"source": "disp", "target": "h3", "label": "candidates"},
        {"source": "cour", "target": "loc", "label": "gRPC bidi / MQTT"},
        {"source": "loc", "target": "h3", "label": "upsert"},
        {"source": "loc", "target": "kafka", "label": "courier.location"},
        {"source": "kafka", "target": "order", "label": "subscribe"},
        {"source": "order", "target": "cust", "label": "WebSocket"},
        {"source": "disp", "target": "cour", "label": "offer push"},
        {"source": "order", "target": "price", "label": "fee calc"},
        {"source": "order", "target": "eta", "label": "predict"},
        {"source": "kafka", "target": "pay"},
        {"source": "kafka", "target": "notif"},
        {"source": "notif", "target": "cust", "label": "APNs/FCM"},
        {"source": "notif", "target": "rest", "label": "tablet push"},
        {"source": "notif", "target": "cour", "label": "APNs/FCM"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant C as Customer\n"
        "  participant API\n"
        "  participant O as Order Svc\n"
        "  participant P as Payment\n"
        "  participant R as Restaurant\n"
        "  participant D as Dispatch\n"
        "  participant H as H3 Index\n"
        "  participant K as Courier\n"
        "  participant N as Notify\n"
        "  C->>API: POST /orders (cart, idem_key)\n"
        "  API->>O: create order\n"
        "  O->>P: authorise (async)\n"
        "  P-->>O: auth_ok\n"
        "  O->>R: tablet push: new order\n"
        "  R-->>O: accept + prep_time\n"
        "  O->>D: dispatch.requested\n"
        "  D->>H: candidates near pickup\n"
        "  H-->>D: [k1, k2, k3]\n"
        "  D->>K: offer (15s timer) k1\n"
        "  K-->>D: accept\n"
        "  D-->>O: courier_assigned\n"
        "  O-->>C: WebSocket: matched\n"
        "  K->>O: stream location\n"
        "  O-->>C: live position\n"
        "  K->>O: picked_up\n"
        "  K->>O: delivered\n"
        "  O->>P: capture\n"
        "  O->>N: notify all parties"
    ),
    er_diagram=(
        "erDiagram\n"
        "  CUSTOMER ||--o{ ORDER : places\n"
        "  RESTAURANT ||--o{ ORDER : fulfills\n"
        "  COURIER ||--o{ ORDER : delivers\n"
        "  RESTAURANT ||--o{ MENU_ITEM : owns\n"
        "  ORDER ||--o{ ORDER_ITEM : contains\n"
        "  ORDER ||--o{ ORDER_EVENT : logs\n"
        "  ORDER ||--|| PAYMENT : settles\n"
        "  ORDER ||--o{ DISPATCH_OFFER : receives\n"
        "  ORDER { bigint id PK\n string status\n int total_cents\n bigint placed_at\n string idempotency_key }\n"
        "  MENU_ITEM { bigint id PK\n bigint restaurant_id\n int price_cents\n bool is_available\n bigint version }\n"
        "  DISPATCH_OFFER { bigint id PK\n bigint order_id\n bigint courier_id\n bigint expires_at\n string outcome }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B[3-sided marketplace]\n"
        "  B --> C[Order FSM is the spine]\n"
        "  C --> D{Dispatch?}\n"
        "  D -->|Push offer| E[H3 candidate + score + 15s timer]\n"
        "  E --> F[Reject-retry chain ≤3]\n"
        "  F --> G[Live tracking: gRPC ingest + WS fan-out]\n"
        "  G --> H[ETA = ML prep + travel + dwell]\n"
        "  H --> I[Surge: per-cell batch, decoupled]\n"
        "  I --> J[Payment 2-phase: auth + capture]\n"
        "  J --> K[Notify all 3 parties on every transition]"
    ),
    tradeoff_title="Push offer vs broadcast dispatch",
    tradeoff_options=[
        {"label": "Push (one offer at a time)",
         "description": "Score candidates, offer to the top one with a short timer; on reject/timeout, offer the next.",
         "pros": ["Bounded courier inbox", "Fair acceptance signal", "Predictable per-courier load",
                  "Easy to reason about reject-retry semantics"],
         "cons": ["Time-to-accept dominated by reject chain length", "Needs aggressive timer tuning",
                  "Bad-actor couriers can stall by timing out"]},
        {"label": "Broadcast (offer to many simultaneously)",
         "description": "Send the offer to N candidates at once; first to accept wins.",
         "pros": ["Fast time-to-first-accept", "Resilient to slow couriers"],
         "cons": ["Race conditions and ghost accepts", "Multiple couriers driving toward pickup wastes labour",
                  "Erodes courier trust ('I lost the offer again')", "Harder fairness story"]},
        {"label": "Hybrid (escalating push)",
         "description": "Single push for the first 1–2 hops; broadcast widens after repeated reject/timeout.",
         "pros": ["Fairness by default", "Latency safety net under shortage"],
         "cons": ["Two code paths", "Threshold tuning per market"]},
    ],
    tradeoff_rec="Hybrid: single-push default with a 15s timer and ≤3 retries; escalate to a small broadcast only when the chain stalls or supply is thin. Industry-validated by Uber/DoorDash/Grubhub.",
    senior_topics=[
        _topic("order-fsm",
               "Order Lifecycle as a Persisted State Machine",
               "An order is not a row that gets columns mutated — it is a finite-state machine "
               "whose every transition is explicit, audited, and idempotent. This is what makes "
               "the marketplace recoverable from partial failure without double-charges or "
               "double-deliveries.",
               [
                   ("States and transitions",
                    "created → payment_authorised → confirmed_by_restaurant → prepping → ready → "
                    "courier_assigned → picked_up → en_route → delivered. Off-paths: "
                    "cancelled_by_customer, cancelled_by_restaurant, refunded, lost. Each "
                    "transition has a guard predicate (legal predecessor + actor + invariants)."),
                   ("Persisted vs derived",
                    "Order Service writes the new state in a single transaction with an "
                    "order_events log row and an outbox row for Kafka. Telemetry never overrides "
                    "state. A courier dropping off-network for two minutes does not 'undo' a "
                    "delivery; only an explicit event does."),
                   ("Idempotency",
                    "Every state-changing API takes an idempotency key. Replays are deduplicated "
                    "at the FSM layer (transition-already-applied → return the prior result). "
                    "Payment auth and capture share the same idempotency key as the order."),
                   ("Why this is the senior signal",
                    "Junior designs treat status as a free-form string. The hard problems "
                    "(double-capture, lost-update on cancel, ghost-accept) all stem from missing "
                    "FSM discipline. Naming the FSM up front is what separates the senior answer."),
               ],
               diagram=(
                   "stateDiagram-v2\n"
                   "  [*] --> created\n"
                   "  created --> payment_authorised\n"
                   "  payment_authorised --> confirmed_by_restaurant\n"
                   "  confirmed_by_restaurant --> prepping\n"
                   "  prepping --> ready\n"
                   "  ready --> courier_assigned\n"
                   "  courier_assigned --> picked_up\n"
                   "  picked_up --> en_route\n"
                   "  en_route --> delivered\n"
                   "  payment_authorised --> cancelled_by_customer\n"
                   "  confirmed_by_restaurant --> cancelled_by_restaurant\n"
                   "  delivered --> [*]"
               )),
        _topic("dispatch-matching",
               "Dispatch: Candidate Query, Scoring, Reject-Retry Chain",
               "Matching an order to a courier is a bounded search with a hard SLO — every "
               "decision (candidates, ranking, offer timer, retry depth) is a knob the design "
               "must spell out, not a heuristic to wave at.",
               [
                   ("H3 candidate query",
                    "Read the H3 index for online couriers within ~3–5 km of pickup, filtered by "
                    "vehicle class and on-delivery flag. Bound the candidate count (~20–30) — "
                    "never scan the city."),
                   ("Scoring features",
                    "ETA-to-pickup (distance ÷ realistic speed, 40%), historical acceptance rate "
                    "(20%), courier rating (10%), batched-delivery feasibility (20%), idle time "
                    "fairness (10%). Train weights via offline simulation; treat them as a "
                    "model, not constants."),
                   ("Offer + reject-retry",
                    "Push the offer to the top candidate with a 15s timer. On reject or timeout, "
                    "remove from the candidate set and offer the next. Cap chain length at 3 "
                    "before widening radius and bumping the surge multiplier."),
                   ("Anti-thrash and fairness",
                    "Repeated rejections degrade the courier's acceptance score (slowly). "
                    "Couriers who time out (didn't even respond) are temporarily de-prioritised. "
                    "Fairness term keeps idle couriers eligible — without it the top-scored "
                    "couriers monopolise."),
                   ("Failure modes",
                    "All candidates reject → widen radius, surge up, retry. Order older than 5 "
                    "minutes unmatched → escalate to ops queue. Courier accepts then goes "
                    "offline → retract offer, reopen dispatch with the next candidate, log "
                    "courier reliability event."),
               ],
               diagram=(
                   "graph TD\n"
                   "  O[order ready for dispatch] --> Q[H3 query candidates]\n"
                   "  Q --> S[score and rank]\n"
                   "  S --> P[push offer to top]\n"
                   "  P --> W{response in 15s?}\n"
                   "  W -->|accept| A[assign courier]\n"
                   "  W -->|reject/timeout| N{retries < 3?}\n"
                   "  N -->|yes| S\n"
                   "  N -->|no| E[widen radius + surge up]\n"
                   "  E --> Q"
               )),
        _topic("courier-location-stream",
               "Real-Time Courier Location: gRPC, MQTT, WebSocket",
               "Three transports, each chosen for the leg it serves — not one transport "
               "everywhere. The customer's live-tracking pin is two hops removed from the "
               "courier's GPS.",
               [
                   ("Courier-to-server (ingest)",
                    "gRPC bidirectional stream over HTTP/2 is the primary path: typed messages, "
                    "multiplexed, server-side backpressure. MQTT-over-TLS is the fallback for "
                    "constrained cellular networks (lower overhead, QoS levels, durable "
                    "reconnects). Pings every 4s during active delivery, 30s while idle online "
                    "(battery save)."),
                   ("Server-side fan-out",
                    "Location Ingestor terminates the stream, writes to courier_locations KV, "
                    "updates the in-memory H3 index, and publishes to a Pub/Sub topic keyed by "
                    "order_id (or courier_id during dispatch). Order Service subscribes to that "
                    "topic for the active order."),
                   ("Server-to-customer (delivery)",
                    "Customer App opens a WebSocket (HTTP/2 or HTTP/3 fallback) to Order Service. "
                    "Order Service pushes a smoothed, snapped-to-roads position at ~1Hz — never "
                    "raw GPS. Snapping uses the routing engine's polyline."),
                   ("Why not one transport everywhere",
                    "WebSocket is browser-friendly but lacks gRPC's typing and MQTT's QoS. MQTT "
                    "is mobile-friendly but a poor fit for browser customer apps. Pick per leg."),
                   ("Battery and network",
                    "Adaptive ping rate based on speed and battery; pause stream when stationary "
                    "for >60s with a heartbeat. Background-friendly on iOS/Android (significant-"
                    "location-change API as fallback when app is backgrounded)."),
               ]),
        _topic("eta-ml",
               "ETA Prediction: ML, Not a Constant",
               "ETA is a customer-facing promise. Static heuristics ('30 min average') are "
               "chronically wrong on lunch peaks and embarrassing on slow restaurants. ML "
               "decomposition is what makes the number defensible.",
               [
                   ("Decomposition",
                    "ETA = E[prep] + E[travel-to-pickup] + E[dwell at pickup] + E[travel-to-"
                    "dropoff] + E[dwell at dropoff]. Each component a separate model — easier to "
                    "train, debug, and replace."),
                   ("Prep time model",
                    "Per-restaurant gradient-boosted tree on (time-of-day, current order "
                    "backlog, item count, item category mix, recent prep observed). Updated "
                    "daily; restaurant-side metrics streamed in real time."),
                   ("Travel model",
                    "Routing engine (OSRM/Valhalla) gives a deterministic baseline. A learned "
                    "correction term adjusts for live traffic, weather, vehicle class (bike vs "
                    "car), and historical road-segment performance."),
                   ("Quantile vs point",
                    "Customers respond better to a slightly pessimistic estimate than a "
                    "chronic-late one. Serve the p70 quantile, not the mean. MAE is the metric, "
                    "but UX latency-truth-asymmetry shapes what we serve."),
                   ("Update cadence",
                    "Recompute on every state transition (accepted, ready, picked_up). The "
                    "customer countdown only moves later, never earlier (one-way ratchet) to "
                    "avoid jitter."),
                   ("Failure mode",
                    "When backlog explodes, models extrapolate badly. Fall back to a clipped "
                    "high quantile and a 'busy right now' UX rather than a number we don't trust."),
               ]),
        _topic("surge-pricing",
               "Surge / Busy-Pricing: Decoupled From Dispatch",
               "Computing a multiplier inside the dispatch hot path slows every match. Pricing "
               "is a slow, per-cell aggregation read at constant cost — that's the architectural "
               "win.",
               [
                   ("Per-cell aggregation",
                    "Every 30s, a Flink/Spark job aggregates per-H3-cell demand (orders/min) and "
                    "supply (online couriers minus on-delivery). Multiplier = clipped(demand / "
                    "available_supply, [1.0, 2.5])."),
                   ("Smoothing",
                    "EMA (alpha ~0.3) over the last few windows prevents flapping that would "
                    "show jittery prices to customers."),
                   ("Read path",
                    "Match path looks up the multiplier in a small KV at O(1). No supply/demand "
                    "scan happens during dispatch."),
                   ("Customer UX",
                    "Most platforms hide the raw multiplier behind a 'busy fee' disclosure to "
                    "preserve trust. Internal dashboards expose the multiplier for ops."),
                   ("Demand shaping",
                    "Surge increases courier earnings → pulls more couriers online in that cell "
                    "→ multiplier subsides. The control loop assumes courier responsiveness; "
                    "monitor for stalls (no supply response after 10 minutes) and intervene."),
               ]),
        _topic("menu-service",
               "Restaurant Menu Service: Read-Heavy With Edge Invalidation",
               "Menu reads dominate the catalog workload. The hard part isn't reading fast — "
               "it's making restaurant edits propagate within seconds without invalidating "
               "every cart in the city.",
               [
                   ("Storage shape",
                    "Cassandra/DynamoDB by (restaurant_id, item_id). Each restaurant has a "
                    "version vector that bumps on any item edit."),
                   ("Edge cache + invalidation",
                    "Per-restaurant menu blob cached at CDN and regional Redis. On edit, Menu "
                    "Service publishes menu.changed{restaurant_id, version}; a fan-out invalidator "
                    "purges by key. Steady-state hit rate >95%."),
                   ("86'ing items",
                    "Toggling is_available is a single PATCH with version bump; propagates in "
                    "<5s. Carts holding the item show a visual 'unavailable' state on next read."),
                   ("Cart re-validation at placement",
                    "Cart stores (item_id, version_at_add). Placement re-fetches current menu "
                    "version and surfaces price/availability deltas for explicit user "
                    "confirmation — never silently changes the total."),
                   ("Why a separate service",
                    "Conflating menu with order data forces every menu read through the "
                    "transactional store. The read shape (huge, idempotent, edge-cacheable) is "
                    "fundamentally different from order writes (small, transactional, geo-shard-"
                    "ed)."),
               ]),
        _topic("payment-two-phase",
               "Two-Phase Payment: Auth at Placement, Capture at Delivery",
               "Synchronous charge-on-tap couples the user-visible flow to a third-party "
               "provider's tail latency. The two-phase model decouples them and gives the "
               "marketplace a clean cancel/refund story.",
               [
                   ("Authorisation",
                    "On order placement, Payment Service requests an authorisation hold via "
                    "Stripe/Adyen with the order's idempotency key. Order moves to "
                    "payment_authorised on success; order rejected on hard decline. The hold "
                    "prevents the customer from spending the same funds elsewhere but does not "
                    "yet move money."),
                   ("Capture",
                    "On the delivered transition, Payment Service captures the held amount, "
                    "again idempotently. Capture happens async via Kafka — never on the "
                    "request path."),
                   ("Cancel and refund",
                    "Cancel before pickup voids the auth (no money moved). Cancel after "
                    "pickup or delivery issues a refund, also idempotent. A reconciliation "
                    "job sweeps held-without-capture older than 7 days."),
                   ("Tip handling",
                    "Tip is part of the placement auth amount; final capture amount is the "
                    "actual delivered total (tip can increase post-delivery, requiring a "
                    "second auth+capture)."),
                   ("PCI scope",
                    "App never sees card numbers. Tokenised via the provider's SDK; tokens "
                    "stored on the customer record. Reduces PCI scope to the Payment Service "
                    "boundary."),
                   ("Why never synchronous",
                    "Provider tail latency (p99>5s sometimes) would dominate user-perceived "
                    "checkout latency. Decoupling lets the order/dispatch flow proceed at "
                    "system pace."),
               ]),
        _topic("geo-sharding-marketplace",
               "Geo-Sharding the Three-Sided Marketplace",
               "Region (city/metro) is the natural shard key — deliveries don't cross regions, "
               "and each region's data fits comfortably on a shard. Cross-region traffic is the "
               "exception, not the rule.",
               [
                   ("What is sharded by region",
                    "Orders, dispatch state, courier locations, pricing grid, ETA model context. "
                    "Each region runs its own dispatch loop and H3 index."),
                   ("What is global",
                    "Customer accounts, restaurant master records, menu catalog (read-replicated), "
                    "payment tokenisation, identity. Reads are local; writes propagate via async "
                    "replication."),
                   ("Cross-region edge cases",
                    "Customer travelling to another city: their orders are placed in the "
                    "destination region. Restaurant chain spanning regions: each location is "
                    "its own restaurant_id pinned to its region."),
                   ("Failover",
                    "A region's read traffic can serve from a neighbour region's read replica "
                    "with stale-by-seconds tolerance. Writes block until the primary recovers — "
                    "we never accept divergent dispatch state."),
                   ("Why not function-shard",
                    "Sharding by service (orders here, payments there) couples regions and "
                    "creates cross-region traffic on every order. Geo-sharding keeps the hot "
                    "path local."),
               ]),
    ],
)
