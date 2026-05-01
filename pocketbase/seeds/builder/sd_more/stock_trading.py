"""SD-extra — Design a Stock Trading System (matching engine + market data feed).

Participants connect via FIX gateways → pre-trade risk → single-threaded
matching engine per symbol (deterministic price-time priority order book) →
append-only trade log → market data multicast (UDP) feed handlers + drop-copy
to clearing/regulator. Position management, kill switches, circuit breakers,
and T+1/T+2 settlement round out the picture. Hot path is microseconds;
audit and settlement are eventual.
"""
from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design a Stock Trading System",
    "Hard",
    "Design an exchange-grade stock trading system — the matching engine, order book, market data feed, "
    "participant gateways, pre-trade risk layer, and the surrounding settlement / audit / control plane. "
    "Buyers and sellers submit orders (limit, market, stop, IOC, FOK) through FIX gateways; a deterministic, "
    "single-threaded matching engine per symbol maintains a price-time-priority order book and produces a "
    "stream of trades. Trades are written to an append-only log, multicast to participants and market-data "
    "subscribers via UDP for ultra-low latency, dropped to clearing for T+1 / T+2 settlement, and persisted "
    "for regulatory audit. The hot path is measured in microseconds; the control plane (risk limits, kill "
    "switches, circuit breakers, position management) must be able to halt trading instantly without "
    "corrupting the book.",
    hints=[
        "The matching engine is single-threaded per symbol — determinism beats parallelism. Sequence "
        "ordering is the contract; if you parallelize matching for one symbol you destroy fairness and "
        "lose replay-ability.",
        "Order book is two price-level priority queues (bids descending, asks ascending). At each price "
        "level, FIFO of resting orders. Lookup by order_id via a hash → node pointer for O(1) cancel.",
        "Latency budget: receive → decode FIX → risk → match → emit market data ≤ 10–50 microseconds in HFT "
        "venues. Everything in the hot path is in-memory, lock-free, and pre-allocated.",
        "Market data is UDP multicast with sequence numbers + a TCP gap-fill / snapshot recovery channel. "
        "TCP unicast to every subscriber does not scale to thousands of consumers at millions of msgs/sec.",
        "Pre-trade risk is mandatory and synchronous — fat-finger checks, max order size, max notional, "
        "credit limit, self-cross prevention, restricted-symbol checks. SEC Rule 15c3-5 makes this a legal "
        "requirement, not a 'nice to have'.",
        "Append-only trade log (sequenced) is the source of truth. Everything downstream — market data, "
        "drop-copy, settlement, audit — is a projection. Replay rebuilds state.",
        "Kill switch must be reachable from a control plane channel that is independent of the order entry "
        "channel; if FIX is jammed by a runaway algo you still need to stop it.",
    ],
    constraints=[
        "Matching latency p99 ≤ 50 microseconds; p99.9 ≤ 200 microseconds",
        "Market data fan-out to 1000s of subscribers at millions of msgs/sec peak",
        "Deterministic ordering: identical input sequence → identical trade output (replayable)",
        "Pre-trade risk is mandatory on every order (regulatory)",
        "Append-only audit log retained 7 years (SEC), trade log retained for life of venue",
        "Settlement T+1 (US equities, post-2024) or T+2; clearing house is external",
        "Trading hours bounded (e.g., 09:30–16:00 ET) but pre-/post-market and 24h crypto variants",
    ],
    req_func=[
        "Accept new orders (limit, market, stop, stop-limit) with TIF (DAY, IOC, FOK, GTC)",
        "Cancel and amend orders by client_order_id",
        "Match orders using price-time priority; emit fills",
        "Publish market data: trades (last), top-of-book (L1), full depth (L2), order-by-order (L3)",
        "Publish drop-copy stream of all fills to clearing and to the originating participant",
        "Pre-trade risk checks: max order size, max notional, credit, self-cross, restricted symbols",
        "Position and PnL tracking per participant in real time",
        "Kill switch: halt a participant or the entire venue without losing book state",
        "Circuit breakers: per-symbol (LULD bands) and market-wide (Level 1/2/3 halts)",
        "Append-only audit log of every order, modify, cancel, fill (regulatory)",
        "End-of-day clearing extract for T+1 / T+2 settlement",
    ],
    req_nonfunc=[
        "Hot-path latency: matching p99 ≤ 50µs, gateway-to-gateway ≤ 200µs",
        "Throughput: ≥ 1M orders/sec peak across the venue, ≥ 100K matches/sec per hot symbol",
        "Determinism: replay of the input log produces identical trade output",
        "Availability: 99.99% during trading hours; planned maintenance only outside hours",
        "Durability: zero acknowledged-order loss (fsync to replicated log before ACK on critical paths)",
        "Auditability: every event reconstructable for 7+ years",
        "Fairness: price-time priority not violated under any circumstance",
    ],
    estimation={
        "symbols": "~8K US equities + ~3K ETFs",
        "active_participants": "~500 firms × multiple sessions",
        "orders_per_day": "~20–50B messages on a busy US equity day (NMS)",
        "trades_per_day": "~50–100M",
        "peak_order_rate": "1M+ msgs/sec across venue; 100K+ on hot single symbol around open/close",
        "market_data_fanout": "~1000 direct subscribers × millions of msgs/sec",
        "hot_path_memory": "Order book per symbol fits in L2/L3 cache (~100s of KB)",
        "audit_log_volume": "~10–50 TB/day raw, compressed",
    },
    endpoints=[
        {"method": "FIX", "path": "NewOrderSingle (35=D)",
         "description": "Submit a new order via FIX 4.4/5.0 over TCP",
         "body": "{ClOrdID, Symbol, Side, OrdType, Price, OrderQty, TimeInForce, Account}"},
        {"method": "FIX", "path": "OrderCancelRequest (35=F)",
         "description": "Cancel a working order",
         "body": "{OrigClOrdID, ClOrdID, Symbol, Side}"},
        {"method": "FIX", "path": "OrderCancelReplaceRequest (35=G)",
         "description": "Amend price/qty (loses time priority)",
         "body": "{OrigClOrdID, ClOrdID, Price, OrderQty}"},
        {"method": "FIX", "path": "ExecutionReport (35=8)",
         "description": "Server → client: ACK / fill / cancel / reject"},
        {"method": "MULTICAST", "path": "MD-Feed (ITCH-style)",
         "description": "UDP multicast: AddOrder, ExecuteOrder, CancelOrder, Trade, with seq numbers"},
        {"method": "TCP", "path": "MD-Recovery / Snapshot",
         "description": "Gap-fill on detected sequence loss; periodic full snapshot"},
        {"method": "POST", "path": "/admin/halt",
         "description": "Control-plane: halt symbol or participant (out-of-band from FIX)",
         "body": "{symbol|participant_id, reason}"},
        {"method": "POST", "path": "/admin/kill_switch",
         "description": "Hard-stop a participant; cancels all open orders",
         "body": "{participant_id}"},
    ],
    tables=[
        {"name": "orders",
         "columns": ["order_id BIGINT PK", "client_order_id VARCHAR(64)", "participant_id BIGINT",
                     "symbol VARCHAR(12)", "side CHAR(1)", "ord_type VARCHAR(8)", "price BIGINT",
                     "qty INT", "leaves_qty INT", "tif VARCHAR(8)", "status VARCHAR(16)",
                     "received_ns BIGINT", "sequence BIGINT"]},
        {"name": "trades",
         "columns": ["trade_id BIGINT PK", "symbol VARCHAR(12)", "buy_order_id BIGINT",
                     "sell_order_id BIGINT", "price BIGINT", "qty INT", "executed_ns BIGINT",
                     "sequence BIGINT", "venue_session_id BIGINT"]},
        {"name": "audit_log",
         "columns": ["sequence BIGINT PK", "kind VARCHAR(16)", "payload BLOB", "ts_ns BIGINT"]},
        {"name": "positions",
         "columns": ["participant_id BIGINT", "symbol VARCHAR(12)", "net_qty BIGINT",
                     "avg_price BIGINT", "realized_pnl BIGINT", "updated_ns BIGINT",
                     "PRIMARY KEY (participant_id, symbol)"]},
        {"name": "risk_limits",
         "columns": ["participant_id BIGINT PK", "max_order_qty INT", "max_notional BIGINT",
                     "credit_limit BIGINT", "restricted_symbols TEXT", "kill_switch BOOL"]},
        {"name": "settlements",
         "columns": ["settle_id BIGINT PK", "participant_id BIGINT", "symbol VARCHAR(12)",
                     "net_qty BIGINT", "net_cash BIGINT", "trade_date DATE", "settle_date DATE",
                     "status VARCHAR(16)"]},
    ],
    indexes=[
        "(symbol, sequence) on trades",
        "(participant_id, symbol) on orders WHERE status='WORKING'",
        "(sequence) on audit_log (clustered, append-only)",
        "(trade_date, participant_id) on settlements",
    ],
    hld_desc=(
        "Participants connect via FIX gateways at the colocation edge. Each order passes synchronous "
        "pre-trade risk, is sequenced into a per-symbol input ring buffer, and dispatched to that "
        "symbol's single-threaded matching engine. The engine maintains an in-memory order book "
        "(price-level priority queues + order_id hash for cancels), produces fills, appends to a "
        "sequenced log, and publishes market-data deltas onto a UDP multicast feed. A drop-copy stream "
        "feeds clearing and the originating participant. End-of-day a settlement extract goes to the "
        "central counterparty (DTCC/NSCC). A control plane — independent of the order channel — owns "
        "halts, kill switches, and LULD/market-wide circuit breakers."
    ),
    hld_components=[
        {"name": "FIX Gateway", "role": "TCP/TLS termination, FIX decode, session sequencing"},
        {"name": "Pre-Trade Risk", "role": "Synchronous limits: size, notional, credit, self-cross, restricted"},
        {"name": "Sequencer", "role": "Assigns global monotonic sequence number; serializes per-symbol input"},
        {"name": "Matching Engine (per symbol)", "role": "Single-threaded order book + price-time priority match"},
        {"name": "Order Book", "role": "Bid/ask price-level FIFO queues + order_id → node hash"},
        {"name": "Trade Log", "role": "Append-only, replicated, fsync'd; source of truth"},
        {"name": "Market Data Publisher", "role": "Encode to ITCH-like format, UDP multicast, gap recovery"},
        {"name": "Drop-Copy Service", "role": "Per-participant fill stream + clearing feed"},
        {"name": "Position Service", "role": "Real-time net position and PnL per participant"},
        {"name": "Control Plane", "role": "Halts, kill switches, LULD bands, market-wide breakers"},
        {"name": "Settlement Extract", "role": "EOD netting, T+1/T+2 file to clearing house"},
        {"name": "Audit / Surveillance", "role": "Long-term retention, regulator queries, manipulation detection"},
    ],
    detailed_design={
        "order_book_structure": (
            "Two sorted price-level structures (bids descending, asks ascending). Common implementations: "
            "intrusive doubly-linked list of orders per price level, with a sorted map (or array if price "
            "ticks are dense, e.g., $0.01 over a small range) of price → level. Plus a hash map "
            "order_id → order_node for O(1) cancel/amend lookup. All nodes pre-allocated from an arena to "
            "avoid malloc on the hot path."
        ),
        "matching_algorithm": (
            "On NewOrder: walk the opposite side from the best price. While crossable price AND remaining "
            "qty > 0: pop oldest order at level (FIFO), produce fill at the resting order's price, "
            "decrement both. If incoming order has remaining qty AND is a limit, insert into own side at "
            "its price level (tail of FIFO). IOC: cancel residual. FOK: pre-check fillable qty before "
            "committing. Market: cross until filled or book exhausted (bounded by collar)."
        ),
        "single_threaded_determinism": (
            "Per-symbol matching is single-threaded. Concurrency is across symbols (different threads / "
            "cores). Determinism comes from: (1) deterministic input sequence number; (2) no wall-clock "
            "in matching logic; (3) pre-allocated memory (no GC / allocator non-determinism); (4) replay "
            "from the sequenced log produces identical trades. This is what makes recovery and "
            "regulatory replay possible."
        ),
        "latency_budget": (
            "Wire-in to wire-out target ≤ 10–50µs in HFT venues. Breakdown: NIC (kernel-bypass via DPDK or "
            "Solarflare ef_vi) ~1µs, FIX decode ~1µs, risk ~1µs, match ~5–20µs, encode + UDP send ~1–2µs. "
            "All in-process, all in-cache. Cross-process IPC adds microseconds and is avoided on the hot "
            "path; risk is co-located in the gateway or in the same process as matching."
        ),
        "market_data_feed": (
            "ITCH-style binary protocol over UDP multicast. Messages: AddOrder, ExecuteOrder, "
            "OrderCancel, OrderReplace, Trade, SystemEvent. Each message carries a monotonic sequence "
            "number. Subscribers detect gaps and request retransmission via a separate TCP recovery "
            "channel; periodic snapshot multicast lets late joiners synchronize. Two redundant feeds "
            "(A/B) on different network paths to survive packet loss."
        ),
        "fix_gateway": (
            "FIX 4.4 / 5.0SP2 over TCP/TLS. Session layer handles seq nums, heartbeats, ResendRequest, "
            "GapFill. Application layer maps NewOrderSingle / Cancel / Cancel-Replace / ExecutionReport. "
            "Gateway is the rate-limit and authentication boundary; out-of-bound orders are rejected "
            "before risk."
        ),
        "pre_trade_risk": (
            "Synchronous, in-process, microsecond-budget checks: max order size, max notional, max "
            "messages/sec (throttle), credit / buying-power, self-cross (don't match a participant's bid "
            "against its own ask), restricted-symbol list, fat-finger price collar (e.g., reject if > "
            "X% from last). SEC Rule 15c3-5 mandates this; broker-dealers cannot disable it."
        ),
        "kill_switch_and_halts": (
            "Control plane API (separate auth, separate network) can: (a) halt a single symbol — engine "
            "stops matching, market data emits HALT message, gateways reject new orders for that symbol; "
            "(b) halt a participant — cancel all working orders, reject new; (c) halt the venue — same "
            "but global. LULD: per-symbol price bands; if NBBO exits the band, 5-minute pause. "
            "Market-wide: S&P 500 down 7%/13%/20% triggers Level 1/2/3 halts."
        ),
        "trade_log_and_replay": (
            "Sequenced append-only log, written before ACK on durability-critical paths (cancel-on-disconnect "
            "and similar). Replicated to a hot standby via shared-memory or low-latency fabric. On failover, "
            "standby replays from last checkpoint to recover identical book state. The log is the system of "
            "record; everything else (positions, market data, drop-copy) is a deterministic projection."
        ),
        "settlement": (
            "EOD process nets trades per (participant, symbol) → net qty + net cash. Extract sent to "
            "clearing house (NSCC/DTCC for US equities). T+1 settlement (post-May 2024) means settle "
            "next business day; clearing house becomes central counterparty (CCP) and guarantees "
            "delivery vs. payment. Failures (DK, fail-to-deliver) reconciled out-of-band."
        ),
        "audit_and_surveillance": (
            "Every order, modify, cancel, fill, and admin action goes to an immutable audit log "
            "(WORM storage: S3 Object Lock or equivalent). 7-year retention (SEC). Surveillance "
            "downstream: spoofing / layering / wash-trade detection on the trade stream; CAT (Consolidated "
            "Audit Trail) reporting daily."
        ),
        "position_management": (
            "Per (participant, symbol): net_qty, avg_price, realized PnL. Updated synchronously from the "
            "trade stream. Enforces position limits and feeds margin / credit recompute that loops back "
            "into pre-trade risk."
        ),
    },
    trade_offs=[
        {"option": "Single-threaded vs multi-threaded matching",
         "for_single": "Deterministic, replayable, fair, simple",
         "for_multi": "Higher peak throughput on one symbol",
         "recommendation": "Single-threaded per symbol; parallelism across symbols. Determinism is non-negotiable."},
        {"option": "TCP unicast vs UDP multicast for market data",
         "for_tcp": "Reliable, no gap handling needed",
         "for_udp": "One-to-many at line rate, ms cheaper, scales to 1000s of subscribers",
         "recommendation": "UDP multicast + TCP recovery. Standard at every major exchange."},
        {"option": "Co-located risk vs out-of-process risk service",
         "for_colocated": "Microsecond-fast, no IPC",
         "for_out_of_process": "Independently scalable, easier to update rules",
         "recommendation": "Co-located on the hot path; out-of-process service for limit *configuration* only."},
        {"option": "FIX vs binary native protocol for order entry",
         "for_fix": "Industry standard, every OMS/EMS speaks it",
         "for_binary": "Lower latency, fewer bytes on wire",
         "recommendation": "Both — FIX for general access, binary (e.g., OUCH) for HFT participants."},
    ],
    tips=[
        "Lead with 'single-threaded matching engine per symbol — determinism, not parallelism.' That one "
        "sentence signals you understand how real exchanges work.",
        "Mention SEC Rule 15c3-5 when discussing pre-trade risk. It's regulatory, not optional.",
        "UDP multicast for market data is the right answer; TCP unicast to thousands of subs does not "
        "scale. Be ready to discuss A/B redundant feeds and TCP gap recovery.",
        "The append-only sequenced trade log IS the system. Market data, positions, drop-copy, settlement "
        "are projections. Mention replay-from-log for failover.",
        "Distinguish hot path (microseconds, in-process, in-cache) from control plane (seconds, "
        "out-of-band) — kill switches live in the control plane.",
        "Don't forget LULD bands and market-wide circuit breakers. Senior interviewers will ask.",
        "T+1 settlement (US equities, post-May 2024) is a recency signal; older material says T+2.",
    ],
    thought_process=[
        "1. Clarify: equities exchange, microsecond hot path, regulated venue.",
        "2. Estimate: 20–50B messages/day, 1M+ orders/sec peak, 100K+/sec on hot symbols.",
        "3. Hot path: FIX gateway → pre-trade risk → sequencer → per-symbol single-threaded matching.",
        "4. Order book: price-level FIFO queues + order_id hash for O(1) cancel.",
        "5. Output: append-only sequenced trade log = source of truth.",
        "6. Market data: UDP multicast (ITCH-style) with seq numbers + TCP gap-fill + periodic snapshot.",
        "7. Drop-copy + position + PnL projected from the trade log.",
        "8. Control plane (out-of-band): halts, kill switch, LULD, market-wide breakers.",
        "9. EOD: net into settlement extract → CCP → T+1 settle.",
        "10. Audit: WORM log, 7-year retention, CAT reporting, surveillance pipeline.",
    ],
    tags=["fintech", "matching-engine", "low-latency", "market-data", "exchange"],
    arch_nodes=[
        {"id": "trader", "label": "Trader / Algo", "type": "client"},
        {"id": "fix", "label": "FIX Gateway", "type": "lb"},
        {"id": "risk", "label": "Pre-Trade Risk", "type": "service"},
        {"id": "seq", "label": "Sequencer", "type": "service"},
        {"id": "engine", "label": "Matching Engine", "type": "server"},
        {"id": "book", "label": "Order Book", "type": "cache"},
        {"id": "log", "label": "Trade Log", "type": "database"},
        {"id": "md", "label": "Market Data Pub", "type": "service"},
        {"id": "mcast", "label": "UDP Multicast", "type": "queue"},
        {"id": "drop", "label": "Drop-Copy", "type": "service"},
        {"id": "pos", "label": "Position / PnL", "type": "service"},
        {"id": "ctl", "label": "Control Plane", "type": "service"},
        {"id": "clear", "label": "Clearing / CCP", "type": "service"},
        {"id": "audit", "label": "Audit / WORM", "type": "database"},
    ],
    arch_edges=[
        {"source": "trader", "target": "fix", "label": "FIX/TCP"},
        {"source": "fix", "target": "risk"},
        {"source": "risk", "target": "seq"},
        {"source": "seq", "target": "engine"},
        {"source": "engine", "target": "book", "label": "match"},
        {"source": "engine", "target": "log", "label": "append"},
        {"source": "log", "target": "md"},
        {"source": "md", "target": "mcast"},
        {"source": "mcast", "target": "trader", "label": "MD"},
        {"source": "log", "target": "drop"},
        {"source": "drop", "target": "trader", "label": "fills"},
        {"source": "log", "target": "pos"},
        {"source": "pos", "target": "risk", "label": "credit/limits"},
        {"source": "ctl", "target": "engine", "label": "halt"},
        {"source": "ctl", "target": "fix", "label": "kill switch"},
        {"source": "log", "target": "clear", "label": "EOD net"},
        {"source": "log", "target": "audit", "label": "WORM"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant T as Trader\n"
        "  participant G as FIX Gateway\n"
        "  participant R as Risk\n"
        "  participant E as Match Engine\n"
        "  participant L as Trade Log\n"
        "  participant M as MD Multicast\n"
        "  T->>G: NewOrderSingle (D)\n"
        "  G->>R: check limits\n"
        "  R-->>G: ok\n"
        "  G->>E: sequenced order\n"
        "  E->>E: match vs book\n"
        "  E->>L: append fill (seq=N)\n"
        "  E-->>G: ExecutionReport\n"
        "  G-->>T: 35=8 fill\n"
        "  L->>M: publish trade\n"
        "  M-->>T: MD delta (UDP)"
    ),
    er_diagram=(
        "erDiagram\n"
        "  PARTICIPANT ||--o{ ORDER : submits\n"
        "  ORDER ||--o{ TRADE : fills\n"
        "  PARTICIPANT ||--o{ POSITION : holds\n"
        "  PARTICIPANT ||--|| RISK_LIMITS : governed_by\n"
        "  TRADE ||--o{ SETTLEMENT : nets_into\n"
        "  ORDER { bigint order_id PK\n string symbol\n char side\n bigint price\n int qty\n string status }\n"
        "  TRADE { bigint trade_id PK\n string symbol\n bigint price\n int qty\n bigint executed_ns }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Order in] --> B[FIX decode]\n"
        "  B --> C{Pre-trade risk}\n"
        "  C -->|reject| X[35=8 reject]\n"
        "  C -->|ok| D[Sequencer]\n"
        "  D --> E[Single-thread match]\n"
        "  E --> F[Append trade log]\n"
        "  F --> G[Drop-copy + Position]\n"
        "  F --> H[UDP multicast MD]\n"
        "  F --> I[EOD settlement]\n"
        "  J[Control plane] -->|halt/kill| E\n"
        "  J -->|kill switch| B"
    ),
    tradeoff_title="Single-threaded matching vs parallel matching",
    tradeoff_options=[
        {"label": "Single-threaded per symbol",
         "description": "One thread owns the order book; serialized input via sequencer.",
         "pros": [
             "Deterministic — replay produces identical trades",
             "Strict price-time priority preserved",
             "No locks, no contention on the hot path",
             "Simple recovery: replay log → identical state",
         ],
         "cons": [
             "Per-symbol throughput capped by one core's speed",
             "Requires careful symbol-to-thread sharding to balance load",
         ]},
        {"label": "Parallel / multi-threaded matching",
         "description": "Multiple threads cooperate on the same book under locks or lock-free structures.",
         "pros": [
             "Theoretically higher single-symbol throughput",
             "Can use more cores for one hot symbol",
         ],
         "cons": [
             "Non-deterministic — replay can diverge",
             "Lock contention destroys microsecond latency",
             "Fairness (price-time priority) becomes hard / impossible to prove",
             "Regulatory replay is broken",
         ]},
    ],
    tradeoff_rec=(
        "Single-threaded per symbol, every time. Scale by sharding symbols across cores/processes. "
        "Determinism, fairness, and replay-ability matter more than raw single-symbol throughput, "
        "and a modern core matches >100K orders/sec on a hot symbol — well above real demand."
    ),
    senior_topics=[
        _topic("price-time-priority",
               "Price-Time Priority Order Book",
               "Price-time priority is the fairness contract: best price wins; among equal prices, "
               "first to arrive wins. The data structure has to deliver this in O(log P) for inserts and "
               "O(1) for cancels by id, where P is number of price levels.",
               [
                   ("Two sides, sorted opposite ways",
                    "Bids: highest price at the top (max-heap or sorted map descending). "
                    "Asks: lowest price at the top (min-heap or sorted map ascending). "
                    "Best bid + best ask → top-of-book (NBBO contribution)."),
                   ("Price-level FIFO",
                    "At each price level, orders form a FIFO queue. New order at that price goes to the "
                    "tail. Match consumes from the head. Time priority = arrival order."),
                   ("Cancel and amend",
                    "Cancel by client_order_id needs O(1) — implement an id → node hash so you can splice "
                    "the node out of its FIFO without scanning. Amend = cancel + new (loses time priority "
                    "unless qty-only decrement, which keeps it)."),
                   ("Implementation choice",
                    "If tick grid is dense (e.g., $0.01 in a $1–$1000 range), an array of price levels is "
                    "fastest. For wide grids, a sorted map (red-black tree, B-tree, or skiplist). Orders "
                    "in each level are an intrusive doubly-linked list of pre-allocated nodes."),
               ],
               diagram=(
                   "graph LR\n"
                   "  subgraph Bids[Bids - desc]\n"
                   "    B1[100.05 -> O1->O2->O3]\n"
                   "    B2[100.04 -> O4->O5]\n"
                   "  end\n"
                   "  subgraph Asks[Asks - asc]\n"
                   "    A1[100.06 -> O6->O7]\n"
                   "    A2[100.07 -> O8]\n"
                   "  end\n"
                   "  Hash[order_id hash] --> O1\n"
                   "  Hash --> O7"
               )),
        _topic("market-data-multicast",
               "UDP Multicast Market Data + Gap Recovery",
               "Direct exchange feeds (NASDAQ ITCH, NYSE Pillar, CME MDP 3.0) are UDP multicast for one "
               "reason: one packet on the wire reaches every subscriber simultaneously, at line rate. "
               "TCP unicast cannot keep up at millions of msgs/sec to thousands of subs.",
               [
                   ("Sequence numbers are the contract",
                    "Every multicast message carries a monotonically increasing sequence number. "
                    "Subscribers detect a gap the moment seq jumps."),
                   ("A/B redundant feeds",
                    "Two independent multicast feeds carrying identical data on different network paths. "
                    "Subscribers consume both, dedupe by sequence, and survive single-path packet loss."),
                   ("TCP gap-fill / retransmission",
                    "Separate TCP service answers requests like 'send me 1000 messages from seq=N'. "
                    "Used only on detected loss, not the hot path."),
                   ("Snapshot service",
                    "Periodically (or on demand) the publisher emits a full book snapshot with the seq "
                    "number it represents. Late joiners and recovery clients use this as the synch "
                    "point: apply snapshot, then replay deltas from the next seq forward."),
                   ("Conflated vs full feed",
                    "L1 (top-of-book) and trades = small, every consumer wants. L2 / L3 (depth, "
                    "order-by-order) = large, subscribed by professionals only. Often separate "
                    "multicast groups so retail clients don't drown."),
               ],
               diagram=(
                   "graph LR\n"
                   "  Pub[Publisher] -- A feed --> NetA[Net A]\n"
                   "  Pub -- B feed --> NetB[Net B]\n"
                   "  NetA --> Sub[Subscriber]\n"
                   "  NetB --> Sub\n"
                   "  Sub -- gap? --> Recov[TCP Recovery]\n"
                   "  Recov --> Sub\n"
                   "  Snap[Snapshot Pub] --> Sub"
               )),
        _topic("pre-trade-risk-15c3-5",
               "Pre-Trade Risk and SEC Rule 15c3-5",
               "Every order on a regulated US equities venue passes synchronous pre-trade risk before it "
               "reaches the matching engine. SEC Rule 15c3-5 (the 'Market Access Rule') requires "
               "broker-dealers to enforce financial and regulatory limits programmatically — naked "
               "sponsored access is illegal.",
               [
                   ("Financial limits",
                    "Max order size (shares), max order notional ($), max daily notional, credit / "
                    "buying-power. Block any order that would breach."),
                   ("Regulatory checks",
                    "Restricted / hard-to-borrow list, locate requirement for shorts, ISO order tagging, "
                    "wash-trade self-cross prevention."),
                   ("Sanity / fat-finger collars",
                    "Reject orders priced more than X% from last trade or NBBO. Catches a misplaced "
                    "decimal point before it reaches the book."),
                   ("Throttles",
                    "Max messages/sec per session — protects gateway and engine from a runaway algo and "
                    "is the first line of defense before the kill switch."),
                   ("Where it lives",
                    "Co-located with — or in the same process as — the gateway. IPC to a remote risk "
                    "service costs microseconds you cannot spend on the hot path. Configuration "
                    "(limits) updates from a slow control plane; enforcement is in-line."),
               ]),
        _topic("kill-switch-and-circuit-breakers",
               "Kill Switches, LULD, and Market-Wide Circuit Breakers",
               "Three layers of stop: per-participant kill switch, per-symbol LULD bands, and "
               "market-wide circuit breakers. They live in the control plane — independent of the order "
               "channel — so a runaway algo can be stopped even if FIX is jammed.",
               [
                   ("Participant kill switch",
                    "Operator-triggered. Cancel all working orders for the participant; reject new orders. "
                    "Reaches the engine via a control-plane channel (separate auth, separate network) "
                    "so it works even if the participant's order channel is saturated."),
                   ("LULD (Limit Up-Limit Down)",
                    "Per-symbol price bands (e.g., ±5% / ±10% depending on tier). If NBBO exits the band "
                    "for 15 seconds, 5-minute pause. Prevents single-stock flash crashes."),
                   ("Market-wide circuit breakers",
                    "S&P 500 down 7% (Level 1) → 15-min halt; 13% (Level 2) → 15-min halt; 20% (Level 3) "
                    "→ trading closed for the day. Coordinated across all US equity venues."),
                   ("State preserved across halt",
                    "Critical: the order book is NOT discarded on halt. Working orders remain; engine "
                    "stops accepting new and stops matching. On resume, an opening auction reprices."),
                   ("Knight Capital, 2012",
                    "$440M loss in 45 minutes from a runaway algo. Exact case where a fast, reachable "
                    "kill switch would have capped the damage. Required reading for the topic."),
               ]),
        _topic("settlement-t1",
               "T+1 Settlement and the Central Counterparty",
               "Trading produces obligations; settlement transfers the cash and shares. As of May 2024, "
               "US equities settle T+1 (next business day). The clearing house steps in as central "
               "counterparty (CCP), guaranteeing delivery vs. payment.",
               [
                   ("Trade date vs settle date",
                    "Trade executes today; settlement (cash/stock change hands) occurs T+1. "
                    "The CCP novates: each side's counterparty becomes the CCP, not the other firm."),
                   ("Netting reduces flow",
                    "EOD multilateral netting: across all of a participant's trades in a symbol, only "
                    "the net qty and net cash settles. Cuts settlement obligations by 90%+."),
                   ("Margin and risk at the CCP",
                    "CCP collects initial margin + variation margin from each participant to cover the "
                    "risk of default between trade and settle. Default fund mutualizes residual risk."),
                   ("Why it shortened",
                    "T+2 → T+1 reduces counterparty risk (one fewer day of exposure) and frees up "
                    "margin capital. Comes with operational pressure: post-trade processing, FX funding "
                    "for cross-border, corporate actions all compress to one day."),
                   ("Fail to deliver",
                    "If a seller can't deliver shares by T+1, it's a fail. CCP buy-in process forces "
                    "resolution. Frequent fails on a name → SEC Reg SHO threshold list."),
               ]),
        _topic("audit-and-cat",
               "Audit Trail, WORM Storage, and CAT Reporting",
               "Every order, modify, cancel, fill, and admin action is durably recorded for regulatory "
               "review. The Consolidated Audit Trail (CAT) requires daily reporting of full lifecycle "
               "events across all US equity venues — billions of records per day.",
               [
                   ("WORM storage",
                    "SEC Rule 17a-4 requires write-once-read-many storage for trade records. Realised as "
                    "S3 Object Lock (Compliance mode), tape, or specialized WORM appliances. 7-year "
                    "retention is the floor; venues often keep longer."),
                   ("CAT lifecycle reporting",
                    "Daily file containing every event: order received, routed, modified, cancelled, "
                    "executed, allocated. Linked across venues via order IDs. Used by SEC for "
                    "cross-market manipulation investigations."),
                   ("Surveillance pipeline",
                    "Stream the trade + order events into a surveillance system that detects spoofing "
                    "(place + cancel), layering (fake depth), wash trades (self-cross), marking the "
                    "close, and front-running. Alerts go to the venue's compliance team."),
                   ("Replay for investigations",
                    "When a regulator asks 'what happened on day X at time Y for symbol Z', the answer "
                    "comes from replaying the sequenced log. Reproduces the exact book state at that "
                    "instant. The append-only log being the source of truth makes this tractable."),
               ]),
    ],
)
