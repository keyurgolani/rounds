"""SDQ — Design a Distributed Unique ID Generator (Snowflake-style).

64-bit, time-ordered, decentralised IDs at ~4M/sec/machine without a central
coordinator. Mirrors `sd_questions.SD_01` shape via the `_q` / `_topic`
helpers.
"""
from __future__ import annotations

from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design a Distributed Unique ID Generator",
    "Medium",
    "Design a service that issues 64-bit unique IDs across many hosts without a central allocator. "
    "IDs must be globally unique, roughly time-ordered (k-sortable so range scans by time work), and "
    "produced at very high throughput on each host (~millions/sec) with sub-millisecond latency. The "
    "design must survive clock skew, NTP jumps, worker-ID collisions, and process restarts without "
    "reissuing a previously emitted ID. The reference layout is Twitter Snowflake: 1 sign bit + 41 "
    "ms-timestamp bits + 10 worker bits + 12 sequence bits.",
    hints=[
        "Lead with the 64-bit Snowflake layout: sign(1) + timestamp(41ms) + worker(10) + sequence(12).",
        "Time-ordered ('k-sortable') is the key requirement — that is why UUID v4 is wrong here.",
        "Clock skew is the bug factory: NTP backwards jumps, VM pauses, leap seconds.",
        "Worker IDs must be unique cluster-wide. Static config works small; ZooKeeper/etcd scales.",
        "Sequence overflow within the same ms = busy-wait until the next ms. Don't reuse across ms.",
        "Always read the host clock from a monotonic source for ordering; wall clock only for the epoch base.",
    ],
    constraints=[
        "ID must fit in 64 bits (signed long) so it round-trips through every language and DB.",
        "Throughput target: ~4M IDs/sec/machine (4096 per ms × 1000 ms).",
        "Latency target: p99 < 1 ms in-process; no network call on hot path.",
        "Cluster size: up to 1024 workers (10-bit worker field). Beyond that, repartition the bits.",
        "No duplicate IDs ever — even on clock rollback, restart, or worker-ID collision.",
        "Time-ordered enough that a binary sort by ID approximately sorts by creation time.",
    ],
    req_func=[
        "Issue a unique 64-bit integer per call, in-process, no network round-trip.",
        "IDs are monotonically increasing per worker and roughly globally time-ordered.",
        "Survive process restart without re-emitting an ID (persist last-seen timestamp or wait one ms).",
        "Detect clock-rollback and refuse to issue until the clock catches up.",
        "Allocate worker IDs uniquely on startup (config, ZooKeeper, etcd, or DB row).",
        "Expose a single getId() / nextId() call; expose a /id HTTP endpoint when used as a service.",
    ],
    req_nonfunc=[
        "Throughput: 4M IDs/sec per machine; tens of millions/sec cluster-wide.",
        "Availability: 99.99% — a single ZooKeeper outage must not stop ID generation on running workers.",
        "Correctness over availability on clock rollback: pause issuing rather than emit a duplicate.",
        "K-sortable: a bytewise sort of IDs is approximately a sort by creation time.",
        "Compact: 8 bytes is half the size of a UUID and fits in BIGINT columns and primary-key indexes cheaply.",
        "Operable: per-worker /metrics for sequence-overflows-per-sec, clock-rollbacks, ms-waits.",
    ],
    estimation={
        "id_size": "8 bytes (BIGINT)",
        "throughput_per_worker": "~4M IDs/sec (4096 / ms)",
        "epoch_lifetime": "41 bits ms = ~69 years from custom epoch",
        "max_workers": "1024 (10 bits)",
        "cluster_throughput": "1024 × 4M = ~4B IDs/sec at saturation",
        "memory_per_worker": "negligible (a few longs); no DB on hot path",
        "expected_clock_drift": "single-digit ms with chrony/NTP; 100s of ms on rollback",
    },
    endpoints=[
        {"method": "GET", "path": "/id",
         "description": "Issue one ID. Used when ID generation is exposed as a service.",
         "body": "n/a — returns {id: 7235123456789012345}"},
        {"method": "POST", "path": "/id/batch",
         "description": "Issue N IDs in one call (N up to e.g. 1000) for high-throughput callers.",
         "body": "{count: 100}"},
        {"method": "GET", "path": "/admin/worker-id",
         "description": "Diagnostic: show the worker ID assigned to this process and its lease state."},
    ],
    tables=[
        {"name": "worker_registry",
         "columns": ["worker_id INT PK", "host VARCHAR(128)", "leased_at BIGINT",
                     "expires_at BIGINT", "last_heartbeat BIGINT"]},
        {"name": "id_audit (optional)",
         "columns": ["worker_id INT", "epoch_ms BIGINT", "max_seq INT",
                     "PRIMARY KEY (worker_id, epoch_ms)"]},
    ],
    indexes=["UNIQUE(worker_id) on worker_registry",
             "(expires_at) on worker_registry for lease-reaper"],
    hld_desc=(
        "An in-process library is the primary deployment: every app links libsnowflake and emits IDs "
        "with no network hop. A thin HTTP service wraps the library for callers that cannot link it "
        "(non-JVM, edge functions). Worker IDs are leased from ZooKeeper/etcd at startup. Each worker "
        "keeps last_ts and seq in memory and rejects requests if the monotonic clock goes backwards."
    ),
    hld_components=[
        {"name": "ID Library", "role": "In-process generator: timestamp | worker | sequence."},
        {"name": "ID Service", "role": "Optional HTTP/gRPC wrapper for non-linkable callers."},
        {"name": "Worker-ID Registry", "role": "ZooKeeper or etcd lease that uniquely assigns 0..1023."},
        {"name": "NTP / chrony", "role": "Keeps wall clock within a few ms; gates ID emission on rollback."},
        {"name": "Monotonic Clock", "role": "Ordering source on the hot path; never goes backwards."},
        {"name": "Metrics Sink", "role": "Exposes seq-overflows/sec, clock-waits/sec, rollback events."},
    ],
    detailed_design={
        "bit_layout": (
            "[sign 1][timestamp 41][worker 10][sequence 12]. Sign bit always 0 so IDs stay positive in "
            "signed-long languages (Java long, JS BigInt). Timestamp is ms since a custom epoch (e.g. "
            "2020-01-01) — 41 bits buys ~69 years. Worker = datacenter*32 + machine, or just machine for "
            "single-region. Sequence resets to 0 every new ms."
        ),
        "hot_path": (
            "1) read monotonic ms; 2) if same ms as last_ts: seq=(seq+1)&0xFFF; if seq wraps to 0, "
            "busy-wait until next ms; 3) if newer ms: seq=0, last_ts=now; 4) if now < last_ts: clock "
            "rollback — block until now ≥ last_ts (or fail fast if drift > threshold); 5) compose ID."
        ),
        "clock_skew_handling": (
            "Run chrony with slew (not step) so the clock never jumps backwards in normal operation. On "
            "abnormal backward step (NTP, leap second, VM resume), generator detects now < last_ts and "
            "BLOCKS issuing until the clock catches up. If drift > a few seconds, fail fast and let the "
            "process exit — duplicates are never acceptable."
        ),
        "worker_id_assignment": (
            "Three options: (a) static — burn worker_id into config/env; simplest, but operationally "
            "fragile. (b) ZooKeeper ephemeral sequential node under /snowflake/workers — auto-releases on "
            "process death. (c) etcd/DB lease with TTL + heartbeat. Recommendation: ZooKeeper or etcd "
            "with TTL leases; static config only for sub-32-worker clusters."
        ),
        "sequence_overflow": (
            "If seq wraps within the same ms (>4096 IDs in 1 ms), spin in a tight loop reading the "
            "monotonic clock until ms increments. At ~4M IDs/sec this is rare; if you hit it sustained, "
            "either repartition bits (more sequence, fewer worker bits) or shard across more workers."
        ),
        "restart_safety": (
            "On startup, read last_ts from local persistent file (fsynced once per ms is too expensive — "
            "fsync once per second and on graceful shutdown). On crash, sleep until "
            "now > last_persisted_ts + 1 second before issuing — guarantees no overlap with pre-crash IDs."
        ),
        "alternatives": (
            "UUIDv4: random 128-bit; not sortable, blows up B-tree caches. UUIDv7/ULID: 128-bit, sortable, "
            "good if 8 bytes is not required. DB auto-increment: sortable but a single point of bottleneck. "
            "Flickr ticket-server: two MySQLs with offset increments — OK ops story, central. Snowflake wins "
            "when you need 64 bits AND k-sortable AND decentralised."
        ),
        "slo_contract": (
            "Per-worker p99 < 1ms in-process; HTTP service p99 < 5ms LAN. Zero duplicates. Up to 1 second "
            "of stalled emission tolerated on clock rollback before alerting; >5 seconds = page operator."
        ),
    },
    trade_offs=[
        {"option": "Snowflake (64-bit) vs ULID/UUIDv7 (128-bit)",
         "for_snowflake": "Half the bytes; fits BIGINT primary keys; cheaper indexes.",
         "for_ulid": "No worker-ID assignment to manage; bigger seq space; lexicographic sort.",
         "recommendation": "Snowflake when storage/index size dominates; ULID when worker-ID ops is the bigger pain."},
        {"option": "In-process library vs central ID service",
         "for_library": "No network hop; per-host throughput in millions/sec.",
         "for_service": "Single binary to upgrade; non-JVM clients.",
         "recommendation": "Library for hot paths; service as a fallback for edge/non-linkable callers."},
        {"option": "Static worker IDs vs ZooKeeper leases",
         "for_static": "No external dependency; survives ZK outage.",
         "for_zk": "Auto-recovery on machine death; no human config drift.",
         "recommendation": "ZooKeeper/etcd ephemeral nodes once cluster > ~32 workers."},
        {"option": "Block on clock rollback vs fail-fast",
         "for_block": "Availability — issuance resumes when clock catches up.",
         "for_fail": "Loud — operator notices drift immediately.",
         "recommendation": "Block for small drift (<1s); fail fast for large drift to surface real bugs."},
    ],
    tips=[
        "Draw the 64-bit layout on the whiteboard first — it anchors everything.",
        "Say 'k-sortable, not strictly sortable.' Clocks differ; perfect global order is unavailable without a coordinator.",
        "Always state how clock rollback is handled — it is the question behind the question.",
        "Mention monotonic vs wall clock distinction. Junior candidates use System.currentTimeMillis() blindly.",
        "Compare to UUIDv4 (random/large), UUIDv7/ULID (128-bit, sortable), DB auto-inc (single point) — shows breadth.",
        "Worker-ID collision is a duplicate-ID factory; mention ZooKeeper/etcd lease.",
    ],
    thought_process=[
        "1. Clarify: 64-bit, sortable, decentralized, ~4M/sec/host, no duplicates ever.",
        "2. Bit layout: 1 + 41 + 10 + 12 = 64. Timestamp dominates (sortability), seq absorbs intra-ms bursts.",
        "3. Hot path: monotonic clock → same ms? bump seq, wrap → wait next ms; new ms? reset seq.",
        "4. Worker-ID: ZooKeeper ephemeral node (auto-release on death), fallback to static config.",
        "5. Clock rollback: detect now < last_ts → block (small) or fail (large). Persist last_ts.",
        "6. Throughput: 4096 / ms × 1000 = 4M IDs/sec/worker. Plenty of headroom for most apps.",
        "7. Alternatives: UUIDv4 (no sort), UUIDv7/ULID (128b sort), DB auto-inc (central) — Snowflake wins on size+sort+decentralised.",
        "8. Failure modes: clock backwards, worker-ID collision, sequence overflow — answer each.",
    ],
    tags=["id", "distributed", "snowflake", "scaling", "backend"],
    arch_nodes=[
        {"id": "app", "label": "App Process", "type": "client"},
        {"id": "lib", "label": "Snowflake Lib", "type": "service"},
        {"id": "svc", "label": "ID Service (opt)", "type": "server"},
        {"id": "zk", "label": "ZooKeeper / etcd", "type": "service"},
        {"id": "ntp", "label": "NTP / chrony", "type": "service"},
        {"id": "metrics", "label": "Metrics", "type": "service"},
    ],
    arch_edges=[
        {"source": "app", "target": "lib", "label": "nextId()"},
        {"source": "lib", "target": "zk", "label": "lease worker_id (startup)"},
        {"source": "lib", "target": "ntp", "label": "clock sync"},
        {"source": "lib", "target": "metrics", "label": "seq-overflows, rollbacks"},
        {"source": "app", "target": "svc", "label": "GET /id (fallback)"},
        {"source": "svc", "target": "lib"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant App\n"
        "  participant Lib as Snowflake Lib\n"
        "  participant Clock as Monotonic Clock\n"
        "  App->>Lib: nextId()\n"
        "  Lib->>Clock: now_ms()\n"
        "  Clock-->>Lib: 1714300000123\n"
        "  alt now == last_ts\n"
        "    Lib->>Lib: seq = (seq+1) & 0xFFF\n"
        "    alt seq wrapped\n"
        "      Lib->>Clock: spin until ms+1\n"
        "    end\n"
        "  else now > last_ts\n"
        "    Lib->>Lib: seq = 0; last_ts = now\n"
        "  else now < last_ts\n"
        "    Lib->>Lib: clock rollback! block\n"
        "  end\n"
        "  Lib-->>App: (ts<<22) | (worker<<12) | seq"
    ),
    er_diagram=(
        "erDiagram\n"
        "  WORKER_REGISTRY ||--o{ ID_AUDIT : emits\n"
        "  WORKER_REGISTRY { int worker_id\n string host\n bigint leased_at\n bigint expires_at }\n"
        "  ID_AUDIT { int worker_id\n bigint epoch_ms\n int max_seq }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Need 64-bit unique ID] --> B{Sortable?}\n"
        "  B -->|Yes| C[Snowflake-style: ts|worker|seq]\n"
        "  B -->|No, fine to be random| D[UUIDv4]\n"
        "  C --> E{Worker-ID source?}\n"
        "  E -->|<32 workers| F[Static config]\n"
        "  E -->|larger| G[ZooKeeper/etcd lease]\n"
        "  C --> H{Clock backwards?}\n"
        "  H -->|small drift| I[Block until caught up]\n"
        "  H -->|large drift| J[Fail fast, alert]"
    ),
    tradeoff_title="Snowflake (64-bit) vs UUIDv7 / ULID (128-bit)",
    tradeoff_options=[
        {"label": "Snowflake 64-bit",
         "description": "1 + 41 + 10 + 12 layout, in-process generator, leased worker IDs.",
         "pros": ["Half the bytes — cheaper indexes",
                  "Fits native BIGINT in every DB and language",
                  "Decentralised, ~4M/sec/host"],
         "cons": ["Worker-ID assignment is operational overhead",
                  "Clock-skew handling required",
                  "Only 1024 workers without re-cutting bits"]},
        {"label": "UUIDv7 / ULID 128-bit",
         "description": "Time-ordered 128-bit ID; no worker-ID coordination required.",
         "pros": ["No worker-ID infrastructure",
                  "More entropy bits — no sequence-overflow concern",
                  "Standardised"],
         "cons": ["2× storage and index size vs BIGINT",
                  "String form is 26+ chars; clients sometimes mis-handle",
                  "Less compact in URLs"]},
    ],
    tradeoff_rec="Snowflake when index size and BIGINT-compat matter; UUIDv7/ULID when worker-ID ops is unwelcome.",
    senior_topics=[
        _topic("clock-skew",
               "Clock Skew, Monotonic Clocks, and Rollback",
               "The single biggest correctness risk in Snowflake. NTP can step backwards; VMs can pause; "
               "leap seconds happen. The hot path must use a monotonic source and refuse to issue if the "
               "clock goes backwards.",
               [
                   ("Wall clock vs monotonic",
                    "Wall clock (System.currentTimeMillis, gettimeofday) can jump backwards on NTP step, "
                    "VM resume, or operator action. Monotonic clock (clock_gettime(CLOCK_MONOTONIC), "
                    "System.nanoTime) only ever moves forward. Use wall clock once at startup to compute "
                    "the epoch base, then drive the hot path off the monotonic source delta."),
                   ("NTP slew vs step",
                    "Configure chrony with `makestep 0.1 3` and `maxslewrate` so corrections smear over "
                    "seconds rather than jump. A jump backwards is what creates duplicate IDs."),
                   ("Detection in the generator",
                    "If now_ms < last_ts_ms, you have rollback. Strategy: if delta < 1s, block until "
                    "now_ms >= last_ts_ms; if delta > 5s, throw and let the supervisor restart — duplicates "
                    "are unacceptable, availability isn't worth a silent corruption."),
                   ("Leap seconds",
                    "Leap-second smear at OS level (Google-style 24h smear) avoids a 1-second backwards "
                    "step. Without smear, the generator sees rollback and blocks."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant Lib\n  participant OS\n"
                   "  Lib->>OS: clock_gettime(MONOTONIC)\n"
                   "  OS-->>Lib: 1000\n"
                   "  Lib->>OS: clock_gettime(MONOTONIC)\n"
                   "  OS-->>Lib: 999 (rollback?)\n"
                   "  Note over Lib: monotonic guarantees this never happens;\n"
                   "  Note over Lib: wall-clock rollback handled separately"
               )),
        _topic("worker-id-collision",
               "Worker-ID Collision and ZooKeeper Leases",
               "Two workers with the same worker_id will emit duplicate IDs within the same ms whenever "
               "their sequence counters align. This is silent and catastrophic.",
               [
                   ("Static-config failure mode",
                    "Operator copy-pastes a config; two pods come up with worker_id=7. Within minutes, "
                    "matching IDs appear in the DB. Detection is via UNIQUE constraint violations or via "
                    "audit logs comparing (worker_id, ts) tuples."),
                   ("ZooKeeper ephemeral sequential",
                    "/snowflake/workers/_ ephemeral sequential nodes auto-release on session loss. New "
                    "process picks the lowest free worker_id. No config drift."),
                   ("etcd lease alternative",
                    "etcd lease with TTL + keepalive. Worker_id is the value; key is the host. On crash "
                    "the lease expires after TTL and the slot frees up."),
                   ("Detection in production",
                    "Per-(worker_id, host) heartbeat in a registry table. Alert on duplicate worker_id "
                    "from distinct hosts. Run a generator-side self-test that hashes own ID stream and "
                    "trips a circuit on duplicates."),
               ]),
        _topic("alternatives-comparison",
               "UUIDv4, UUIDv7/ULID, DB Auto-Increment, Flickr Ticket Server",
               "Snowflake is one design point. Knowing the others — and when to pick them — is the senior signal.",
               [
                   ("UUIDv4",
                    "128-bit random. No coordination, no sortability. Index inserts scatter across the "
                    "B-tree, killing cache locality. Use only when you actively want unguessable IDs."),
                   ("UUIDv7 / ULID",
                    "128-bit, time-prefixed, sortable. No worker-ID assignment needed (random low bits "
                    "absorb collisions probabilistically). Pick when you don't want ZooKeeper/etcd in the "
                    "story and 16 bytes is acceptable."),
                   ("DB auto-increment",
                    "Sortable, dense, simple. But every insert serializes through one DB instance. Works "
                    "for low-throughput single-region apps; falls over at scale or across shards."),
                   ("Flickr ticket-server",
                    "Two MySQLs with offsets (1,3,5,...) and (2,4,6,...). Cheap HA over auto-increment "
                    "but still central. Useful intermediate step."),
                   ("When Snowflake wins",
                    "You need: 64 bits (BIGINT compat), k-sortable, decentralised, 4M/sec/host. If any of "
                    "those drops out, simpler choices exist."),
               ]),
    ],
)
