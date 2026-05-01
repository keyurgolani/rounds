"""SDQ — Design a Distributed Cache (Redis-like).

In-memory key-value cache sharded across many nodes with replication, eviction,
persistence, and stampede protection. Mirrors `sd_questions.SD_01` shape via the
`_q` / `_topic` helpers.
"""
from __future__ import annotations

from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design a Distributed Cache",
    "Hard",
    "Design an in-memory distributed key-value cache (Redis-like) that fronts a slower system of record "
    "(RDBMS, search index, downstream service). Clients SET/GET/DEL by key with sub-millisecond latency, "
    "the dataset is sharded across hundreds of nodes via consistent hashing with vnodes, each shard runs "
    "leader-follower replication, eviction is configurable per namespace (LRU / LFU / TTL with memory "
    "caps), and the cluster tolerates node failure without losing the ability to serve. The system must "
    "stay correct under thundering-herd loads, hot keys, network partitions, and rolling upgrades, and "
    "offers RDB snapshot + AOF persistence as opt-in durability.",
    hints=[
        "Cache is an optimisation, not a system of record — design the miss path first, then the hit path.",
        "Consistent hashing with virtual nodes is the placement primitive; without vnodes you get hot shards.",
        "Replication mode (sync vs async) is the latency-vs-durability dial — pick per namespace, not globally.",
        "Stampede protection (single-flight + early refresh) belongs at the cache client, not the server.",
        "Hot keys break consistent hashing — detect via sampling and replicate the offending keys to N shards.",
        "Persistence (RDB+AOF) is opt-in: most caches accept loss-on-crash because the SoR is authoritative.",
    ],
    constraints=[
        "Sub-millisecond p99 GET latency intra-AZ; p99 < 5 ms cross-AZ.",
        "Working set 10s of TB across the fleet; per-node RAM 64–256 GB; memory is the dominant cost.",
        "Read:write ratio ~ 20:1; bursts of 10× on cache-miss storms after deploys or DB failovers.",
        "Cluster size 100–1000 nodes; rebalancing must avoid O(N) key movement on membership changes.",
        "Most workloads accept loss-on-crash; a minority (sessions, rate-limits) opt into AOF durability.",
        "Hot-key fan-in can hit a single shard at 1M+ QPS — must not collapse the rest of the cluster.",
    ],
    req_func=[
        "GET / SET / DEL / EXPIRE / INCR / MGET / MSET on byte-string keys and values.",
        "Per-key TTL with lazy and active expiration.",
        "Configurable eviction policy per namespace: LRU, LFU, allkeys-random, volatile-only, no-eviction.",
        "Replication: each shard has 1 leader + N followers; reads optionally served from followers.",
        "Cluster membership: add/remove/replace nodes without dropping traffic.",
        "Optional persistence: periodic RDB snapshots and/or append-only AOF; restore on cold start.",
        "Pub/Sub channels and Lua-style atomic scripts for compound operations (stretch).",
    ],
    req_nonfunc=[
        "Latency: p50 < 200 µs, p99 < 1 ms intra-AZ for GET; SET p99 < 2 ms async-replicated.",
        "Throughput: 100k+ ops/sec/node steady, peak 250k on hot reads.",
        "Availability 99.99% per shard; single-node loss must not cause user-visible miss storm.",
        "Durability is opt-in: AOF fsync-every-second loses ≤1 s of writes on crash; RDB loses ≤ snapshot interval.",
        "Rebalance moves O(K/N) keys for a single node change, not O(K).",
        "Backpressure: clients see explicit `OVERLOADED` rather than tail-latency cliff under saturation.",
    ],
    estimation={
        "fleet_nodes": "500 nodes, 128 GB RAM each → ~64 TB working set (~50% headroom)",
        "keys": "~5B keys total, average value 256 B + 80 B overhead",
        "qps_steady": "20M GET/sec, 1M SET/sec aggregate",
        "qps_hotkey_peak": "1M+ QPS to a single key during viral events",
        "vnodes_per_node": "256 — enough to balance to ~1% skew",
        "replication_factor": "RF=3 (1 leader + 2 followers) for HA; RF=2 for cost-tier namespaces",
        "memory_overhead": "~30% per-key overhead (hash table, expiration metadata, freelist)",
    },
    endpoints=[
        {"method": "TCP", "path": "GET <key>",
         "description": "Read value; returns NIL on miss/expired"},
        {"method": "TCP", "path": "SET <key> <value> [EX <ttl>] [NX|XX]",
         "description": "Write with optional TTL and existence guard",
         "body": "binary value"},
        {"method": "TCP", "path": "DEL <key> [<key>...]",
         "description": "Delete one or more keys; returns count removed"},
        {"method": "TCP", "path": "MGET <key>...",
         "description": "Pipelined multi-get scattered across shards by client router"},
        {"method": "TCP", "path": "INCR <key> / EXPIRE <key> <sec>",
         "description": "Atomic counter and TTL refresh"},
        {"method": "HTTP", "path": "GET /admin/cluster/topology",
         "description": "Slot map: vnode → leader/followers; clients refresh on MOVED redirects"},
        {"method": "HTTP", "path": "POST /admin/rebalance",
         "description": "Trigger slot migration to a new node; idempotent and resumable"},
        {"method": "HTTP", "path": "POST /admin/snapshot",
         "description": "Force RDB snapshot on a node (used pre-upgrade)"},
    ],
    tables=[
        {"name": "in_memory_keyspace (per-node, hash table)",
         "columns": ["key BYTES (PK)", "value BYTES", "expire_at_ms BIGINT NULL",
                     "lru_clock UINT24", "lfu_counter UINT8", "encoding ENUM(raw,int,list,zset,hash,stream)"]},
        {"name": "slot_map (cluster metadata, gossiped or in coordinator)",
         "columns": ["slot_id INT (0..16383)", "leader_node_id VARCHAR(64)",
                     "follower_node_ids VARCHAR[]", "epoch BIGINT", "state ENUM(stable,migrating,importing)"]},
        {"name": "nodes (cluster metadata)",
         "columns": ["node_id VARCHAR(64) PK", "addr VARCHAR(64)", "role ENUM(leader,follower,learner)",
                     "vnode_ids INT[]", "last_heartbeat_ms BIGINT", "version VARCHAR(16)"]},
        {"name": "aof_log (per-node append-only file)",
         "columns": ["offset BIGINT", "command BYTES", "args BYTES", "ts_ms BIGINT"]},
        {"name": "rdb_snapshots (per-node disk)",
         "columns": ["snapshot_id VARCHAR(40) PK", "started_at_ms BIGINT", "size_bytes BIGINT",
                     "aof_offset BIGINT", "checksum CHAR(64)"]},
        {"name": "hot_key_registry (sampled, per-node, gossiped to clients)",
         "columns": ["key BYTES PK", "qps DOUBLE", "decided_at_ms BIGINT",
                     "replica_node_ids VARCHAR[]"]},
    ],
    indexes=[
        "Primary keyspace: open-addressed hash table with incremental rehash (Redis dict).",
        "Expiration: secondary hash of TTL'd keys; active sampling job evicts in O(1) batches.",
        "LRU/LFU: 24-bit clock per entry, sampled-N eviction (~N=5) — no global LRU list.",
        "Slot map fanned out via gossip; clients cache (slot → leader) and update on MOVED.",
        "Hot-key registry indexed by key; background sketch (count-min) feeds promotion decisions.",
    ],
    hld_desc=(
        "Sharded in-memory KV with smart clients. The keyspace is split into a fixed number of slots "
        "(e.g. 16384). Each slot maps to a leader node and N followers; placement of slots over physical "
        "nodes is computed via consistent hashing on (slot_id, node_id) with virtual nodes for balance. "
        "Smart clients hold a slot-map and route directly to the leader of the relevant slot — one network "
        "hop per op. Each shard runs leader-follower replication with a per-shard write log; replication "
        "mode (sync/async) is per-namespace. Eviction is local to each node and policy-driven (LRU/LFU/TTL "
        "with allkeys vs volatile scope). Persistence is opt-in via RDB snapshots and/or AOF append-only "
        "logging. Cluster membership and slot ownership propagate via a gossip protocol (or are coordinated "
        "by an external service like ZooKeeper for stronger guarantees). A stampede-protection layer in the "
        "client library does single-flight + probabilistic early refresh; a hot-key sampler in each node "
        "promotes hot keys to read-replicate across multiple shards."
    ),
    hld_components=[
        {"name": "Smart Client Library", "role": "Slot-map cache, MOVED redirects, single-flight, early refresh"},
        {"name": "Cache Node (Shard)", "role": "Hash table, eviction, replication, AOF, RDB"},
        {"name": "Slot / Topology Manager", "role": "Slot ownership, rebalancing plans, epoch numbering"},
        {"name": "Gossip Layer / Coordinator", "role": "Failure detection, membership; ZK option for arbitration"},
        {"name": "Replication Pipeline", "role": "Leader → follower op stream with backlog + full resync"},
        {"name": "Persistence Engine", "role": "RDB fork+copy-on-write snapshots; AOF rewriter"},
        {"name": "Hot-Key Sampler", "role": "Count-min sketch; promotes hot keys to N-replica read fan-out"},
        {"name": "Eviction Engine", "role": "Per-policy sampler (LRU/LFU/TTL); active TTL expiration"},
        {"name": "Admin / Migration Service", "role": "Slot migration MOVING→IMPORTING→STABLE; idempotent"},
        {"name": "Metrics & Tracing", "role": "Per-shard QPS, hit rate, evictions, replication lag"},
    ],
    detailed_design={
        "consistent_hashing_with_vnodes": (
            "Each physical node owns 256 virtual nodes placed on a hash ring (e.g. 64-bit MurmurHash). "
            "Keys are hashed and the lookup walks clockwise to the first vnode → owning physical node. "
            "Why vnodes: with N=10 physical nodes, plain consistent hashing leaves wide gaps and a single "
            "node can own 3× the average slice. 256 vnodes per node smooths the distribution to within "
            "~1% of mean. Adding a node steals roughly 1/N of every existing node's keys (rather than one "
            "node losing all its keys), so cold-cache impact is spread and the rebalance is incremental."
        ),
        "replication": (
            "Each shard is a Raft-like or Redis-style leader-follower group with RF=3. Writes hit the "
            "leader, which appends to its op log and streams to followers. ASYNC is the default — leader "
            "ACKs the client on local write — and is right for caches whose source-of-truth is elsewhere; "
            "max ~1 s of writes lost on leader crash. SYNC (wait for f+1 replicas) is offered for "
            "session-store and rate-limit namespaces where stale reads after failover are unacceptable. "
            "On leader failure, gossip-detected timeouts trigger an election; the new leader's epoch is "
            "incremented so stale clients see MOVED and refresh."
        ),
        "eviction_policies": (
            "Each node has a memory cap (maxmemory). On insert exceeding the cap the eviction engine "
            "samples N (~5) random keys from the candidate set and evicts the worst per-policy: "
            "ALLKEYS-LRU (cheapest, dominant default), ALLKEYS-LFU (better for skewed access — uses an "
            "8-bit log-counter with decay), VOLATILE-LRU/LFU/TTL (only TTL'd keys), NOEVICTION (return "
            "OOM and let the SoR carry the load). Active expiration runs a background sampler over the "
            "TTL hash; lazy expiration also fires on every key access. The combination keeps amortised "
            "expire work O(1) per op."
        ),
        "cache_patterns": (
            "Cache-aside (lazy): app reads cache; on miss reads SoR and writes cache with TTL. Default "
            "for most read-heavy workloads. Write-through: app writes go to cache and SoR synchronously — "
            "consistent but doubles write latency. Write-back / write-behind: app writes only to cache, "
            "queue replicates to SoR async — fast and risky (cache loss = data loss). Write-around: app "
            "writes only to SoR, cache populated lazily on read — good when written data is rarely read "
            "again. Choice is a per-namespace decision; the cache library exposes all four."
        ),
        "stampede_protection": (
            "Three layers, all in the client. (1) Single-flight: when N concurrent requests miss for the "
            "same key, only one fetches the SoR; the rest park on a per-key lock. (2) Probabilistic early "
            "refresh: each GET refreshes early with probability proportional to (now - last_refresh) / TTL "
            "and `beta * compute_time`, so refreshes spread out instead of stampeding at TTL boundary. "
            "(3) Request coalescing on the server: identical in-flight reads collapse to one downstream "
            "call. Combined, a viral key with 1M QPS produces ~1 SoR query per refresh window."
        ),
        "hot_keys": (
            "Each node feeds a count-min sketch over recent ops. Keys exceeding a QPS threshold are "
            "flagged hot and registered globally. Mitigation: replicate the value to N additional nodes "
            "(read-replicas) and have smart clients hash hot keys to (key, replica_idx) where replica_idx "
            "is randomised per request. Writes still go to the canonical leader and fan out; reads scale "
            "linearly with replica count. This breaks the consistent-hashing assumption that one key has "
            "exactly one home — explicitly, only for the small hot tail."
        ),
        "persistence": (
            "RDB snapshots: fork() + copy-on-write so the parent keeps serving while the child writes a "
            "compact binary dump every N minutes or M writes. Restore = load the dump on cold start. "
            "AOF: every write is appended to a log, fsync per-write (slow, durable), per-second (default), "
            "or never (fastest). Periodic AOF rewrite collapses the log into an equivalent shorter form. "
            "Both can coexist: RDB for fast restore, AOF for ≤1 s loss bound. Most cache namespaces run "
            "neither and accept full loss on crash because the SoR is canonical."
        ),
        "failure_model": (
            "Single node crash: followers detect via gossip heartbeat; new leader elected within seconds; "
            "clients see one MOVED and refresh. With persistence disabled the rebooting node starts empty "
            "and re-warms on demand — there is a temporary cold-cache miss spike on its slots. With AOF "
            "enabled the node replays its log and rejoins as follower. Network partition: minority side "
            "loses leadership for its slots and fails reads/writes (CP-leaning) or returns stale follower "
            "reads if the namespace opted into AP. Split-brain prevented by epoch numbering: a stale "
            "leader's writes are rejected by followers on next epoch contact."
        ),
        "topology_coordination": (
            "Two viable architectures. Gossip (Redis Cluster style): every node sees every other via "
            "epidemic exchange; cluster decisions (slot ownership, leader election) reach quorum via "
            "heartbeat votes. Pros: no external dep, scales to thousands of nodes, simple to deploy. "
            "Cons: convergence-time tail under partitions, harder to reason about. ZooKeeper / etcd: "
            "external strongly-consistent coordinator owns slot map and leader leases. Pros: clean "
            "arbitration, easy admin UX. Cons: hard dependency, ZK becomes the failure domain. "
            "Recommendation: gossip for the data plane, optional ZK for cluster admin operations and "
            "rebalance arbitration only — keep the hot path off the coordinator."
        ),
        "rebalancing": (
            "Adding a node assigns it a chunk of slots. Migration runs slot-by-slot in three states: "
            "STABLE → MIGRATING (source still authoritative; trickle-copy keys to dest) → IMPORTING "
            "(dest authoritative; source forwards stragglers) → STABLE. Clients see ASK redirects during "
            "the move and only the per-slot epoch flips on completion. Result: O(K/N) keys move, no "
            "freeze, resumable on failure."
        ),
        "slo_contract": (
            "GET p50 < 200 µs, p99 < 1 ms intra-AZ; SET (async RF=3) p99 < 2 ms; "
            "shard availability 99.99%; rebalance moves ≤ 1/N of keys; AOF-fsync-everysec loses ≤ 1 s "
            "on crash; hot-key replication reduces single-key shard CPU by ≥ N×."
        ),
    },
    trade_offs=[
        {"option": "Sync vs async replication",
         "for_sync": "No data loss on leader crash; safe failover for sessions/rate-limits",
         "for_async": "Sub-ms write latency; right default for caches whose SoR is authoritative",
         "recommendation": "Async by default, sync per-namespace for stateful caches (sessions, rate-limit, idempotency keys)."},
        {"option": "RDB snapshot vs AOF append-only",
         "for_rdb": "Compact, fast restore, near-zero steady cost (fork+CoW)",
         "for_aof": "Bounded loss (≤1 s with fsync-everysec); replay is deterministic",
         "recommendation": "Both — RDB for fast cold-start, AOF for durability bound. Disable both for stateless caches."},
        {"option": "LRU vs LFU eviction",
         "for_lru": "Cheap recency window; great for scan-heavy or working-set traffic",
         "for_lfu": "Better hit rate on skewed (Zipfian) access; rejects one-hit-wonders",
         "recommendation": "LFU for most production caches with skewed access; LRU as safe default for unknown workloads."},
        {"option": "Cache-aside vs write-through vs write-back",
         "for_cache_aside": "Simple; cache only ever holds known-good data; SoR stays authoritative",
         "for_write_through": "Cache and SoR consistent post-write; no read-miss cliff after writes",
         "for_write_back": "Fastest writes; absorbs write spikes; risks data loss on cache failure",
         "recommendation": "Cache-aside as the default; write-through for read-after-write hot paths; write-back only when SoR is rebuildable."},
        {"option": "Gossip cluster vs ZooKeeper-coordinated",
         "for_gossip": "No external dependency; scales to thousands of nodes; no ZK ops burden",
         "for_zk": "Strong arbitration on membership and leadership; simpler admin reasoning",
         "recommendation": "Gossip for data-plane decisions; optionally ZK/etcd for rebalance arbitration only — never on the request path."},
    ],
    tips=[
        "Start with the placement primitive: consistent hashing + vnodes. Without that, the rest is air.",
        "Distinguish replication mode from persistence — interviewers conflate them; senior candidates don't.",
        "Stampede protection is a client-library concern, not a server feature. Naming single-flight earns the senior signal.",
        "Hot keys explicitly break consistent hashing; calling that out and proposing N-replica fan-out is a strong signal.",
        "Most caches run with NO persistence. Volunteering 'we accept loss-on-crash because the SoR is authoritative' shows judgment.",
        "Quote a concrete vnode count (256/node) and replication factor (RF=3) — vague numbers read as hand-waving.",
    ],
    thought_process=[
        "1. Clarify: in-memory KV cache fronting a slower SoR; sub-ms p99; loss tolerance varies per namespace.",
        "2. Estimate: 5B keys × ~336 B → ~1.7 TB hot working set; 500 nodes × 128 GB; 20M GET / 1M SET sec.",
        "3. APIs: GET / SET / DEL / EXPIRE / MGET; admin topology and snapshot.",
        "4. Placement: consistent hashing with 256 vnodes/node — bounded skew + incremental rebalance.",
        "5. Replication: RF=3 leader-follower; async default, sync per opt-in namespace.",
        "6. Eviction: maxmemory + sampled LRU/LFU + TTL active+lazy expiration.",
        "7. Cache patterns: cache-aside default; write-through / write-back / write-around per workload.",
        "8. Stampede: single-flight + probabilistic early refresh + server-side coalescing.",
        "9. Hot keys: count-min sketch detection + N-way replica fan-out.",
        "10. Persistence: opt-in RDB (fork+CoW) and AOF (fsync-everysec); rewrite for compaction.",
        "11. Failure: gossip heartbeats, epoch-numbered leadership, MOVED/ASK redirects on migration.",
        "12. Topology: gossip data plane; ZK/etcd optional for admin arbitration only.",
    ],
    tags=["cache", "distributed", "consistent-hashing", "scaling", "performance"],
    arch_nodes=[
        {"id": "client", "label": "Smart Client", "type": "client"},
        {"id": "lb", "label": "VIP / Direct Routing", "type": "lb"},
        {"id": "leader", "label": "Shard Leader", "type": "server"},
        {"id": "follower", "label": "Shard Followers", "type": "server"},
        {"id": "topo", "label": "Topology / Slot Map", "type": "service"},
        {"id": "gossip", "label": "Gossip Layer", "type": "service"},
        {"id": "zk", "label": "ZK / etcd (optional)", "type": "service"},
        {"id": "aof", "label": "AOF Log", "type": "database"},
        {"id": "rdb", "label": "RDB Snapshots", "type": "database"},
        {"id": "sor", "label": "System of Record", "type": "database"},
        {"id": "hot", "label": "Hot-Key Sampler", "type": "service"},
    ],
    arch_edges=[
        {"source": "client", "target": "topo", "label": "slot map refresh"},
        {"source": "client", "target": "leader", "label": "GET/SET (one hop)"},
        {"source": "leader", "target": "follower", "label": "replicate (async/sync)"},
        {"source": "client", "target": "follower", "label": "replica reads"},
        {"source": "leader", "target": "aof", "label": "append"},
        {"source": "leader", "target": "rdb", "label": "fork + CoW snapshot"},
        {"source": "client", "target": "sor", "label": "miss path / write-through"},
        {"source": "leader", "target": "gossip", "label": "heartbeat"},
        {"source": "follower", "target": "gossip", "label": "heartbeat"},
        {"source": "gossip", "target": "topo", "label": "membership"},
        {"source": "zk", "target": "topo", "label": "rebalance arbitration"},
        {"source": "leader", "target": "hot", "label": "sample QPS"},
        {"source": "hot", "target": "client", "label": "promote N-replica"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant App\n"
        "  participant C as Smart Client\n"
        "  participant L as Shard Leader\n"
        "  participant F as Follower\n"
        "  participant SoR\n"
        "  App->>C: GET key\n"
        "  C->>C: hash(key) → slot → leader\n"
        "  C->>L: GET key\n"
        "  alt hit\n"
        "    L-->>C: value\n"
        "  else miss\n"
        "    L-->>C: NIL\n"
        "    C->>C: single-flight lock(key)\n"
        "    C->>SoR: SELECT row\n"
        "    SoR-->>C: row\n"
        "    C->>L: SET key value EX 300\n"
        "    L->>F: replicate (async)\n"
        "    L-->>C: OK\n"
        "    C-->>App: value\n"
        "  end\n"
        "  Note over L,F: on leader crash → epoch++<br/>follower elected → MOVED to client"
    ),
    er_diagram=(
        "erDiagram\n"
        "  CLUSTER ||--o{ NODE : has\n"
        "  NODE ||--o{ VNODE : owns\n"
        "  VNODE ||--o{ SLOT : maps\n"
        "  SLOT ||--|| SHARD : routes\n"
        "  SHARD ||--|| LEADER : has\n"
        "  SHARD ||--o{ FOLLOWER : has\n"
        "  SHARD ||--o{ KEY : holds\n"
        "  KEY ||--o| TTL : optional\n"
        "  SHARD ||--o| AOF_LOG : appends\n"
        "  SHARD ||--o| RDB_SNAPSHOT : snapshots\n"
        "  KEY ||--o| HOT_REGISTRY : flagged"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B[Cache fronts a SoR]\n"
        "  B --> C[Consistent hashing + vnodes]\n"
        "  C --> D[Leader-follower replication per shard]\n"
        "  D --> E{Loss tolerance?}\n"
        "  E -->|none| F[Sync replicate + AOF fsync]\n"
        "  E -->|bounded| G[Async + AOF everysec]\n"
        "  E -->|full loss ok| H[Async, no persistence]\n"
        "  C --> I[Eviction: LRU / LFU / TTL]\n"
        "  I --> J[Stampede: single-flight + early refresh]\n"
        "  J --> K{Hot key?}\n"
        "  K -->|yes| L[Replicate to N shards]\n"
        "  K -->|no| M[Single home]\n"
        "  D --> N[Gossip membership; epoch-numbered leadership]"
    ),
    tradeoff_title="Replication Mode and Persistence",
    tradeoff_options=[
        {"label": "Async replication, no persistence",
         "description": "Leader ACKs on local write; followers catch up; no disk writes.",
         "pros": ["Sub-ms write latency", "Cheapest steady-state cost",
                 "Right for caches whose SoR is canonical"],
         "cons": ["Loses unreplicated writes on leader crash",
                 "Cold restart re-warms from SoR (miss-storm risk)",
                 "Stale reads from followers during catch-up"]},
        {"label": "Async replication + AOF fsync-everysec",
         "description": "Leader ACKs on local write; AOF fsync once per second; periodic RDB.",
         "pros": ["Bounded ≤1 s loss window", "Fast restart from disk", "Low-overhead durability"],
         "cons": ["Disk I/O cost", "AOF rewrite needs CPU + I/O", "Still loses 1 s on crash"]},
        {"label": "Sync replication (wait f+1) + AOF fsync-always",
         "description": "Quorum-replicated writes; every write fsynced before ACK.",
         "pros": ["Zero loss on single-node failure", "Safe automatic failover",
                 "Right for sessions / rate-limits / idempotency keys"],
         "cons": ["Write latency = slowest replica + fsync", "Throughput drops 3–10×",
                 "Defeats the point of an in-memory cache for most workloads"]},
    ],
    tradeoff_rec=(
        "Async + no persistence as the default — caches are an optimisation and the SoR is the truth. "
        "Async + AOF-everysec for caches that are expensive to rebuild (large derived datasets). "
        "Sync + fsync-always only for the small set of namespaces where the cache IS the system of record "
        "(session store, rate-limit counters, idempotency keys); for those, accept the latency cost."
    ),
    senior_topics=[
        _topic("consistent-hashing-vnodes",
               "Consistent Hashing with Virtual Nodes",
               "Why a hash ring with vnodes is the placement primitive for distributed caches, and how it "
               "bounds rebalance cost, smooths skew, and survives node churn without freezing the cluster.",
               [
                   ("The naive approach fails",
                    "Mod-N hashing: key → hash(key) % N. Add or remove a node and (N-1)/N of all keys "
                    "remap to a different home. The cache effectively cold-starts on every membership "
                    "change — unacceptable at any real scale."),
                   ("The hash ring",
                    "Place each node at hash(node_id) on a 64-bit ring. A key lands on the first node "
                    "clockwise from hash(key). Adding a node only steals keys whose hash falls in the new "
                    "node's arc — roughly 1/(N+1) of the keyspace. Removing a node hands its arc to the "
                    "successor."),
                   ("Why plain rings are unbalanced",
                    "With 10 nodes the arc lengths are wildly uneven; the unluckiest node can own 3× the "
                    "average slice. Worse, the entire stolen arc on add comes from a single neighbour — "
                    "concentrated cold-cache impact."),
                   ("Virtual nodes fix the skew",
                    "Place 256 vnodes per physical node, each at hash(node_id, vnode_idx). Now 10 "
                    "physical nodes own 2,560 small arcs, distribution is within ~1% of mean, and a new "
                    "node steals tiny slices from every existing node — load and cold-cache impact "
                    "spread."),
                   ("Operational notes",
                    "Vnode count is a knob: too few = skew, too many = bigger slot map and gossip "
                    "traffic. 128–256 per physical node is the industry sweet spot. Heterogeneous nodes "
                    "(different RAM sizes) get proportional vnode counts."),
               ],
               diagram=(
                   "graph LR\n"
                   "  K[key] --> H[hash → ring position]\n"
                   "  H --> R[ring with 256 vnodes per node]\n"
                   "  R --> N1[Node A vnodes]\n"
                   "  R --> N2[Node B vnodes]\n"
                   "  R --> N3[Node C vnodes]\n"
                   "  Add[+Node D] --> S[steals 1/N from each]\n"
                   "  S --> N1\n"
                   "  S --> N2\n"
                   "  S --> N3"
               )),
        _topic("cache-stampede",
               "Cache Stampede: Single-Flight, Early Refresh, Coalescing",
               "When a hot key expires and 1M concurrent requests miss simultaneously, naive systems hammer "
               "the SoR until it falls over. Three composable layers prevent it.",
               [
                   ("The failure mode",
                    "Key with TTL=300s and 100k QPS expires. Every request misses, every request queries "
                    "the SoR, the SoR's connection pool saturates, latency spikes, the cache rewrite "
                    "queues behind a slow SoR, and the entire site stalls. This is a 'thundering herd' or "
                    "'dogpile'."),
                   ("Single-flight",
                    "On miss, the client takes a per-key lock (in-process or via a lightweight cache-side "
                    "lock with short TTL). Only the lock-holder queries the SoR; everyone else parks "
                    "until the result is published, then reads it from cache. Reduces SoR fan-in from N "
                    "to 1 per miss event."),
                   ("Probabilistic early refresh",
                    "Don't wait for TTL=0. On every GET, refresh with probability "
                    "p = -compute_time × beta × ln(rand). Hot keys refresh smoothly across the TTL "
                    "window instead of stampeding at expiry. Beta tuned so expected refresh count "
                    "matches steady-state load."),
                   ("Server-side request coalescing",
                    "Independent of the client: when N concurrent in-flight reads target the same SoR "
                    "row, the data layer collapses them to one underlying query and broadcasts the "
                    "result. Belt-and-braces; protects you from clients that don't single-flight."),
                   ("When to skip",
                    "Low-QPS keys don't need it; the overhead of locking exceeds the SoR savings. Apply "
                    "selectively per namespace or above a sampled-QPS threshold."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant R1\n  participant R2\n  participant R3\n  participant Cache\n  participant SoR\n"
                   "  R1->>Cache: GET k (miss)\n"
                   "  R2->>Cache: GET k (miss)\n"
                   "  R3->>Cache: GET k (miss)\n"
                   "  R1->>Cache: SETNX lock:k\n"
                   "  Cache-->>R1: acquired\n"
                   "  R2->>Cache: SETNX lock:k\n"
                   "  Cache-->>R2: lost; wait\n"
                   "  R1->>SoR: SELECT k\n"
                   "  SoR-->>R1: value\n"
                   "  R1->>Cache: SET k value EX 300\n"
                   "  R1->>Cache: DEL lock:k\n"
                   "  R2->>Cache: GET k\n"
                   "  Cache-->>R2: value\n"
                   "  R3->>Cache: GET k\n"
                   "  Cache-->>R3: value"
               )),
        _topic("hot-keys",
               "Hot-Key Detection and N-Replica Fan-Out",
               "Consistent hashing assumes one home per key. A viral key violates that assumption and "
               "melts a single shard. The fix is to relax 'one home' for the hot tail explicitly.",
               [
                   ("How hot keys are born",
                    "Celebrity follow-graph entries, trending product pages, breaking-news article IDs, "
                    "global rate-limit counters. Real distributions are Zipfian; the top 0.001% of keys "
                    "can hold 10–30% of all traffic."),
                   ("Detection: count-min sketch",
                    "Each node maintains a small (KB-sized) count-min sketch over recent ops. Keys "
                    "exceeding a QPS threshold (e.g. 10× the per-node mean) are reported to a cluster "
                    "registry. Sketches are probabilistic but bounded-error, and use constant memory "
                    "regardless of cardinality."),
                   ("Mitigation: replicate hot keys",
                    "For each hot key, place a read-only copy on N additional nodes (N=3–10). Smart "
                    "clients, on seeing a key in the hot registry, hash to (key, random replica_idx) and "
                    "spread reads across the N replicas. Writes still funnel through the canonical leader "
                    "and fan out, so write throughput on a single hot key is unchanged — but read load is "
                    "divided by N."),
                   ("Cost and edge cases",
                    "Read replicas drift (eventual consistency); for counter-style hot keys (rate-limits) "
                    "this is wrong — instead shard the counter into N independent counters and sum on "
                    "read. Promotion/demotion needs hysteresis or it flaps. Registry must propagate to "
                    "clients in seconds via gossip or push, or the mitigation lags the spike."),
                   ("Don't forget the L1",
                    "A small in-process cache (e.g. 1k-entry LRU per app pod) absorbs a huge fraction of "
                    "hot-key traffic before it ever reaches the cache fleet. Treat it as the first layer "
                    "of a multi-tier cache: L1 in-process → L2 distributed → L3 SoR."),
               ],
               diagram=(
                   "graph LR\n"
                   "  K[hot key] --> S[count-min sketch]\n"
                   "  S --> R[hot registry]\n"
                   "  R --> C1[Client A]\n"
                   "  R --> C2[Client B]\n"
                   "  W[writer] --> L[canonical leader]\n"
                   "  L --> N1[replica 1]\n"
                   "  L --> N2[replica 2]\n"
                   "  L --> N3[replica 3]\n"
                   "  C1 -. random .-> N1\n"
                   "  C1 -. random .-> N2\n"
                   "  C2 -. random .-> N3"
               )),
        _topic("persistence-rdb-aof",
               "Persistence: RDB Snapshots vs AOF Append-Only File",
               "Two complementary durability strategies. Most caches use neither; the ones that do "
               "almost always combine both, because each covers the other's weakness.",
               [
                   ("RDB snapshots",
                    "Periodic point-in-time dump of the entire keyspace to a compact binary file. "
                    "Implemented via fork() + copy-on-write: the child process serialises the keyspace "
                    "while the parent keeps serving; only modified pages get duplicated, so steady-state "
                    "memory overhead is ~10% of the working set. Restore = read the file. Compact (5–10× "
                    "smaller than AOF), fast restore, near-zero impact on the request path."),
                   ("RDB weakness",
                    "You lose every write since the last snapshot. Snapshot every 5 minutes → up to 5 "
                    "minutes of data gone on crash. Tuning the interval down trades durability for fork "
                    "frequency (and CoW memory overhead)."),
                   ("AOF append-only file",
                    "Every write command is appended to a log. Three fsync modes: ALWAYS (every write "
                    "fsynced — durable, slow), EVERYSEC (background fsync once per second — bounded ≤1s "
                    "loss, default), NO (let the OS decide — fast, unbounded loss on crash)."),
                   ("AOF weakness",
                    "Log grows without bound. Mitigated by AOF rewrite: a background process rebuilds an "
                    "equivalent compact log from the current keyspace, then atomically swaps it in. "
                    "Replay on restart is also slow on a big log."),
                   ("Combine for best-of-both",
                    "RDB for fast restart and disaster-recovery off-site copies; AOF for the bounded "
                    "loss window. On restart, load the last RDB then replay AOF entries since the "
                    "snapshot. Total restart time stays seconds-to-minutes; loss bound stays ≤1 s."),
                   ("When to disable both",
                    "Pure caches whose SoR is authoritative: turn everything off. Restart is empty, "
                    "warm-up takes seconds-to-minutes from real traffic, the SoR carries the cold-cache "
                    "spike. Persistence costs CPU, disk, and IOPS that are wasted if the data is "
                    "rebuildable on demand."),
               ],
               diagram=(
                   "graph TD\n"
                   "  W[write] --> L[in-memory keyspace]\n"
                   "  L --> A[AOF append]\n"
                   "  A -->|fsync everysec| D[disk]\n"
                   "  L -. fork+CoW .-> S[RDB child]\n"
                   "  S --> D\n"
                   "  R[restart] --> RDB[load RDB]\n"
                   "  RDB --> RA[replay AOF since snapshot]\n"
                   "  RA --> L"
               )),
        _topic("topology-coordination",
               "Cluster Topology: Gossip vs ZooKeeper-Coordinated",
               "How nodes agree on who owns which slot, who is leader, and who is alive. Two "
               "architectures with very different operational profiles.",
               [
                   ("Gossip protocol (Redis Cluster, Cassandra)",
                    "Every node periodically picks K random peers and exchanges (membership, slot map, "
                    "epoch numbers, heartbeats). Failure detection is local: a node is suspected after "
                    "missing heartbeats from a quorum of peers. Slot ownership and leader election "
                    "converge via epoch-numbered messages — higher-epoch state wins. No external "
                    "dependency; scales smoothly to thousands of nodes."),
                   ("ZooKeeper / etcd-coordinated (Kafka, HBase, classic Bookkeeper)",
                    "An external strongly-consistent coordinator owns the slot map and per-shard leader "
                    "leases. Nodes register, take leases, and watch for changes. Leadership and slot "
                    "ownership are arbitrated by the coordinator's consensus layer. Operationally cleaner "
                    "for admins; ZK becomes the failure domain and the cluster is bounded by ZK's write "
                    "throughput."),
                   ("Tradeoffs",
                    "Gossip: no external dep, weaker consistency on cluster decisions, slower convergence "
                    "under pathological partitions, easier deploy. Coordinator: strong arbitration, "
                    "simpler reasoning, hard dep on ZK availability and ops, ZK write throughput bottleneck "
                    "for very large clusters."),
                   ("Recommendation: hybrid",
                    "Use gossip for the data-plane decisions (heartbeats, slot map, leader election) — "
                    "fast and self-contained. Optionally use ZK/etcd for cluster admin operations only: "
                    "rebalance arbitration, configuration store, version pinning. Critically, keep ZK "
                    "OFF the request path; if ZK is unavailable, the cluster keeps serving."),
                   ("Split-brain prevention",
                    "Both architectures rely on epoch / fencing tokens: a leader's writes carry an epoch, "
                    "and followers reject lower-epoch writes. After a partition heals, the stale leader "
                    "discovers it has been superseded on first contact and steps down. Without epochs, "
                    "two leaders writing concurrent versions of the same slot is the worst class of "
                    "bug."),
               ],
               diagram=(
                   "graph TD\n"
                   "  subgraph Gossip\n"
                   "    G1[node] --- G2[node]\n"
                   "    G2 --- G3[node]\n"
                   "    G3 --- G1\n"
                   "    G1 --- G4[node]\n"
                   "  end\n"
                   "  subgraph ZK\n"
                   "    Z[ZooKeeper / etcd] --> N1[node]\n"
                   "    Z --> N2[node]\n"
                   "    Z --> N3[node]\n"
                   "  end"
               )),
    ],
)
