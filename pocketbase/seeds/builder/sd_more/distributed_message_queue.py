"""SD-extra — Design a Distributed Message Queue / Pub-Sub System (Kafka-style).

Topics, partitions, append-only logs, replication (ISR), consumer groups,
delivery semantics, retention, controller / KRaft, and backpressure.
"""
from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design a Distributed Message Queue (Kafka-style)",
    "Hard",
    "Design a distributed, durable, high-throughput pub-sub / message-queue system in the spirit of "
    "Apache Kafka. Producers publish messages to topics; topics are split into ordered partitions; "
    "messages are appended to a per-partition replicated log on disk; consumers read in groups with "
    "automatic partition assignment and offset tracking. The system must scale to millions of "
    "messages/sec, replicate for durability, support at-least-once and exactly-once delivery, and "
    "handle consumer rebalances and broker failures without losing data.",
    hints=[
        "Partition is the unit of order AND parallelism — order is per-partition, never per-topic.",
        "Append-only log on disk per partition — sequential writes, page cache, zero-copy reads.",
        "Replication: leader + ISR (in-sync replicas); ack=all means commit requires all ISR.",
        "Consumer groups: one partition is consumed by exactly one consumer in a group at a time.",
        "Offsets are stored as messages in an internal __consumer_offsets compacted topic.",
        "Exactly-once = idempotent producer (PID + seq) + transactions across partitions.",
        "Controller (ZooKeeper or KRaft) owns broker metadata, leader election, and ISR changes.",
        "Backpressure: bound producer buffer, return errors when full; do not silently drop.",
    ],
    constraints=[
        "Throughput: 1M+ messages/sec sustained per cluster, scaling horizontally with brokers",
        "Durability: zero message loss after producer ack=all returns",
        "Latency: p99 produce ack < 50ms, end-to-end consume < 200ms within a region",
        "Replication factor 3 standard; tolerate 1 broker failure with no data loss, 2 with degraded",
        "Retention: configurable per topic — time (days/weeks) or size; log compaction for keyed topics",
        "Ordering: strict per-partition; cross-partition ordering not guaranteed",
    ],
    req_func=[
        "Producers publish messages to a topic with optional key (for partitioning)",
        "Topics are split into N partitions; each partition is an ordered append-only log",
        "Messages are replicated across R brokers; leader + followers; ISR set",
        "Consumers join a consumer group; coordinator assigns partitions to consumers",
        "Consumers commit offsets; resume after restart from last committed offset",
        "Support at-most-once, at-least-once, and exactly-once delivery semantics",
        "Retention by time and by size; log compaction for keyed topics (latest-value-per-key)",
        "Cluster controller owns broker metadata, partition leadership, and ISR membership",
    ],
    req_nonfunc=[
        "High throughput: sequential disk I/O + zero-copy sendfile + batching",
        "Durability: replicated log with quorum acks (ack=all + min.insync.replicas)",
        "Availability: leader failover within seconds; consumer rebalance bounded",
        "Horizontal scalability: add brokers, partitions move; producers/consumers auto-discover",
        "Backpressure-friendly: bounded producer buffers, slow-consumer protection",
        "Operability: per-topic retention, replication, partition count tunable",
    ],
    estimation={
        "messages_per_sec": "1M peak, ~500KB/sec per partition × 2K partitions",
        "avg_message_bytes": "~1KB → 1GB/sec ingress, 3GB/sec replicated (RF=3)",
        "per_broker_throughput": "~100K msg/sec sustained (NIC + disk)",
        "brokers_per_cluster": "~30-100 for 1M msg/sec with RF=3",
        "retention_storage": "1GB/sec × 7 days × 3 (RF) ≈ 1.8PB cluster",
        "consumer_groups": "10K+ groups, ~50K consumer instances total",
        "metadata_qps": "~1K/sec to controller (rebalances + ISR shrinks)",
    },
    endpoints=[
        {"method": "POST", "path": "/topics",
         "description": "Create a topic with partition count, replication factor, retention",
         "body": "{name, partitions, replication_factor, retention_ms, compaction:bool}"},
        {"method": "POST", "path": "/produce/{topic}",
         "description": "Produce a batch of records to a topic (key-hashed partitioning)",
         "body": "{records:[{key, value, headers}], acks:0|1|all, idempotent:bool, txn_id?}"},
        {"method": "GET", "path": "/fetch/{topic}/{partition}",
         "description": "Fetch records from a partition starting at offset, up to max bytes",
         "body": "{offset, max_bytes, max_wait_ms, isolation:read_committed|read_uncommitted}"},
        {"method": "POST", "path": "/groups/{group}/join",
         "description": "Join a consumer group; coordinator assigns partitions",
         "body": "{member_id, subscribed_topics, assignment_strategy}"},
        {"method": "POST", "path": "/groups/{group}/commit",
         "description": "Commit consumed offsets for partitions owned by this member",
         "body": "{offsets:{topic_partition: offset}}"},
        {"method": "GET", "path": "/metadata",
         "description": "Cluster metadata: brokers, topics, partition leaders, ISR",
         "body": "{}"},
        {"method": "POST", "path": "/txn/{txn_id}/commit",
         "description": "Commit a producer transaction across multiple partitions",
         "body": "{partitions:[{topic, partition, last_offset}]}"},
    ],
    tables=[
        {"name": "topics",
         "columns": ["name VARCHAR(255) PK", "partitions INT", "replication_factor INT",
                     "retention_ms BIGINT", "compaction BOOL", "created_at BIGINT"]},
        {"name": "partitions",
         "columns": ["topic VARCHAR(255)", "partition INT", "leader_broker_id INT",
                     "isr_set TEXT", "log_start_offset BIGINT", "log_end_offset BIGINT",
                     "PRIMARY KEY (topic, partition)"]},
        {"name": "brokers",
         "columns": ["id INT PK", "host VARCHAR(253)", "port INT", "rack VARCHAR(64)",
                     "epoch BIGINT", "status VARCHAR(16)"]},
        {"name": "consumer_groups",
         "columns": ["group_id VARCHAR(255) PK", "coordinator_broker_id INT",
                     "generation INT", "protocol VARCHAR(64)", "state VARCHAR(32)"]},
        {"name": "consumer_offsets",
         "columns": ["group_id VARCHAR(255)", "topic VARCHAR(255)", "partition INT",
                     "offset BIGINT", "metadata TEXT", "committed_at BIGINT",
                     "PRIMARY KEY (group_id, topic, partition)"]},
        {"name": "producer_state",
         "columns": ["producer_id BIGINT", "topic VARCHAR(255)", "partition INT",
                     "epoch INT", "last_seq INT", "last_offset BIGINT",
                     "PRIMARY KEY (producer_id, topic, partition)"]},
    ],
    indexes=[
        "(topic, partition) on partitions for fast leader lookup",
        "(group_id, topic, partition) on consumer_offsets for commit/fetch",
        "(producer_id, topic, partition) on producer_state for idempotent dedup",
        "(leader_broker_id) on partitions for failover queries",
    ],
    hld_desc=(
        "A cluster of brokers; each broker owns a slice of partitions. Topics are logically split "
        "into N partitions; each partition is an append-only log on disk replicated to R brokers "
        "(1 leader + R-1 followers). Producers send batched, compressed records to the leader; "
        "leader appends to local log, followers fetch and replicate. Once all in-sync replicas (ISR) "
        "have the message, it's committed and visible to consumers. Consumers join consumer groups; "
        "the group coordinator (a broker) runs the rebalance protocol to assign partitions. Offsets "
        "are committed back as messages in the internal __consumer_offsets compacted topic. The "
        "controller (a single elected broker, backed by ZooKeeper or KRaft Raft quorum) owns "
        "cluster metadata: broker membership, partition leadership, ISR changes, and topic creation. "
        "Retention is enforced per partition by time or size; compacted topics retain the latest "
        "value per key. Exactly-once delivery is built on idempotent producers (PID + seq) and "
        "two-phase transactions across partitions."
    ),
    hld_components=[
        {"name": "Producer Client", "role": "Batch, compress, partition, retry; idempotent + txn"},
        {"name": "Broker", "role": "Hosts partition replicas; serves produce + fetch"},
        {"name": "Partition Log", "role": "Append-only segment files on disk per partition"},
        {"name": "Replication Fetcher", "role": "Follower pulls from leader to stay in ISR"},
        {"name": "Group Coordinator", "role": "One per consumer group; runs rebalance protocol"},
        {"name": "Controller", "role": "Cluster-wide metadata + leader election + ISR"},
        {"name": "Metadata Quorum (KRaft / ZooKeeper)", "role": "Persisted, replicated metadata log"},
        {"name": "__consumer_offsets Topic", "role": "Compacted internal topic for offset commits"},
        {"name": "Transaction Coordinator", "role": "2PC across partitions for exactly-once"},
        {"name": "Log Cleaner", "role": "Compacts keyed topics; trims by retention policy"},
        {"name": "Consumer Client", "role": "Joins group, fetches, processes, commits offsets"},
    ],
    detailed_design={
        "partition_log": (
            "Each partition is an ordered, immutable, append-only log split into segment files "
            "(default 1GB). The active segment is appended to; older segments are sealed. Each "
            "segment has a sparse offset index and a timestamp index for O(log n) lookup. Writes "
            "are sequential — disks (especially HDDs and SSDs) hit peak throughput on sequential "
            "I/O. Reads are served via the OS page cache and zero-copy sendfile() from disk to "
            "socket, bypassing user space."
        ),
        "replication_isr": (
            "Each partition has 1 leader and R-1 followers (replication factor R, default 3). "
            "Producers write only to the leader. Followers issue Fetch requests to the leader "
            "and replicate. The ISR (in-sync replicas) is the subset of replicas that have caught "
            "up within replica.lag.time.max.ms. Commit watermark = high-watermark = min ISR offset. "
            "Messages above the high-watermark are not visible to consumers. ack=0: no wait; "
            "ack=1: leader-only ack; ack=all: wait for all ISR. min.insync.replicas guards "
            "against shrinking ISR to 1 silently — produce errors out instead."
        ),
        "leader_election": (
            "Controller watches broker liveness via the metadata quorum heartbeat. When a leader "
            "fails, controller picks a new leader from the surviving ISR (preferring the head of "
            "the ISR list to minimize data loss). Unclean leader election (picking from out-of-ISR) "
            "is opt-in and risks data loss. New leader's epoch is bumped; followers truncate to "
            "the new leader's log end and resume replication."
        ),
        "producer_batching": (
            "Producer batches records per partition in a buffer (linger.ms, batch.size). Compresses "
            "the batch (snappy / lz4 / zstd) before sending. Partitioning: sticky-partition for "
            "null keys (round-robin per batch), murmur2(key) % partitions for keyed records, or a "
            "custom partitioner. Retries on transient errors with backoff. Idempotent mode: each "
            "producer assigned a Producer ID (PID); each record carries (PID, partition, sequence) "
            "so the broker dedups retries deterministically."
        ),
        "consumer_groups_rebalance": (
            "Consumers identify by group_id. The group coordinator (a broker chosen by hash of "
            "group_id) tracks members. Rebalance protocol: members JoinGroup, coordinator picks a "
            "leader member, leader runs the assignment strategy (range, round-robin, or sticky), "
            "members SyncGroup to receive their assignment. Heartbeats keep membership alive; "
            "session timeout triggers rebalance. Incremental cooperative rebalance (KIP-429) "
            "avoids stop-the-world by revoking only the moving partitions."
        ),
        "offsets_and_commits": (
            "Each consumer commits the next-to-read offset per (topic, partition) it owns. "
            "Commits are written as messages to __consumer_offsets, a compacted internal topic "
            "partitioned by group_id (default 50 partitions). Compaction retains the latest "
            "offset per (group, topic, partition) key. On consumer restart, the coordinator looks "
            "up the latest committed offset and resumes from there."
        ),
        "delivery_semantics": (
            "At-most-once: ack=0 or commit before processing — fast but data loss on failure. "
            "At-least-once (default): ack=all + commit after processing — duplicates possible on "
            "retry. Exactly-once: idempotent producer (dedup by PID+seq within a partition) PLUS "
            "transactional producer (2PC across partitions). Consumer reads with "
            "isolation.level=read_committed to skip aborted-txn records. End-to-end EOS for "
            "stream processing requires Kafka-Streams-style transactional read-process-write."
        ),
        "transactions": (
            "Producer registers transactional.id → fences any older epoch with same txn_id. "
            "Begin txn → produce to N partitions → addPartitionsToTxn (informs txn coordinator) → "
            "commitTxn. Coordinator writes PREPARE → COMMIT markers to a __transaction_state log. "
            "Each affected partition gets a control record (commit/abort marker). Consumers in "
            "read_committed mode skip records before a commit marker."
        ),
        "retention_and_compaction": (
            "Time-based: segments older than retention.ms are deleted. Size-based: oldest segment "
            "is deleted when partition exceeds retention.bytes. Log compaction (per-key topics): "
            "background log cleaner periodically rewrites a partition keeping only the latest "
            "value per key — useful for changelog topics and __consumer_offsets. Tombstones "
            "(null value) signal deletion; retained briefly then purged."
        ),
        "controller_and_kraft": (
            "Pre-KRaft: ZooKeeper hosts /brokers, /controller, /partitions metadata; one broker "
            "elected controller via ephemeral node. Post-KRaft (Kafka Raft): metadata stored as "
            "an event log replicated by a Raft quorum of controller nodes (3 or 5). Brokers "
            "subscribe to metadata changes via a Fetch from the active controller. KRaft removes "
            "ZK, simplifies ops, and scales to millions of partitions per cluster."
        ),
        "backpressure": (
            "Producer side: bounded send buffer (buffer.memory). When full, send() blocks up to "
            "max.block.ms, then throws. Block-then-error is correct — silently dropping is wrong. "
            "Broker side: per-client quotas (produce/fetch bytes per sec) throttle abusive clients "
            "by delaying responses, not closing connections. Slow follower: drops out of ISR, "
            "stops blocking commits but still replicates lazily — producer keeps progressing."
        ),
        "zero_copy_sendfile": (
            "On fetch, broker calls sendfile(disk_fd, socket_fd) — kernel transfers bytes directly "
            "from page cache to NIC, no copy into user space, no JVM heap pressure. Combined with "
            "page cache hits for hot data, this is the throughput unlock that lets one broker "
            "serve hundreds of MB/sec from a single core."
        ),
        "exactly_once_in_practice": (
            "Reality check: end-to-end exactly-once across an external sink requires either an "
            "idempotent sink (dedup by message id) or a 2PC into the sink. Within Kafka boundaries "
            "(read-process-write), Kafka transactions give true EOS. Across sinks, prefer "
            "idempotent consumer logic + at-least-once for simplicity."
        ),
    },
    trade_offs=[
        {"option": "ack=1 (leader only) vs ack=all (full ISR)",
         "for_ack1": "Lower produce latency, higher throughput",
         "for_ackall": "No data loss on leader failure; correct durability story",
         "recommendation": "ack=all + min.insync.replicas=2 for durable workloads; ack=1 for "
                           "metrics/logs where a tiny loss window is acceptable."},
        {"option": "ZooKeeper vs KRaft for cluster metadata",
         "for_zk": "Mature, battle-tested, separate operational domain",
         "for_kraft": "One system to operate, scales to millions of partitions, faster failover",
         "recommendation": "KRaft for new clusters — Kafka 3.x+ default; ZK is being deprecated."},
        {"option": "Partition count: many vs few",
         "for_many": "More parallelism for consumers; finer load distribution",
         "for_few": "Less metadata overhead, faster rebalance, fewer open files per broker",
         "recommendation": "Size partitions to the slowest consumer's required parallelism; "
                           "rule of thumb: target_throughput / per_consumer_throughput."},
        {"option": "At-least-once + idempotent consumer vs exactly-once with transactions",
         "for_alo": "Simpler producer + broker; consumer dedups on a business key",
         "for_eos": "True read-process-write semantics; atomic across partitions",
         "recommendation": "ALO + idempotent sink for most pipelines; EOS only when the sink "
                           "cannot dedup and atomicity across partitions is required."},
        {"option": "Compacted vs time-retention topics",
         "for_compaction": "Latest-value-per-key (changelog, materialized view inputs)",
         "for_time": "Append-only event stream with bounded history",
         "recommendation": "Match the topic to its semantic — compaction for state, time for events."},
    ],
    tips=[
        "Lead with: partition is the unit of order AND parallelism. Most candidates skip this.",
        "Sequential append + page cache + zero-copy sendfile = the throughput story. Don't skip it.",
        "ISR + ack=all + min.insync.replicas is the durability triplet — quote all three.",
        "Consumer group rebalance is a stop-the-world event by default — mention cooperative rebalance.",
        "Offsets stored in a compacted Kafka topic, not a separate database. That's the trick.",
        "Exactly-once = idempotent producer (PID + seq) + transactions across partitions.",
        "Mention KRaft over ZooKeeper — 2026-era answer; old answer is ZK.",
        "Backpressure: block-then-error on producer; quotas and ISR shrink on broker side.",
    ],
    thought_process=[
        "1. Clarify: pub-sub or queue? Both — durable log with consumer groups gives both.",
        "2. Estimate: 1M msg/sec × 1KB → 1GB/sec ingress; RF=3 → 3GB/sec replicated.",
        "3. APIs: produce, fetch, group join/commit, metadata, transactions.",
        "4. Topic → N partitions → append-only log per partition; sequential disk wins.",
        "5. Replication: leader + ISR followers; ack=all + min.insync.replicas for durability.",
        "6. Producer: batch, compress, partition by key-hash; idempotent for retry-safety.",
        "7. Consumer groups: coordinator runs rebalance; offsets in __consumer_offsets.",
        "8. Delivery: ALO default, EOS via idempotent producer + transactions.",
        "9. Retention: time + size; compaction for keyed (changelog) topics.",
        "10. Controller: KRaft Raft quorum (or ZK); leader election on broker failure.",
        "11. Backpressure: bounded buffers + quotas; never silently drop.",
    ],
    tags=["queue", "pub-sub", "kafka", "streaming", "async"],
    arch_nodes=[
        {"id": "prod", "label": "Producer", "type": "client"},
        {"id": "cons", "label": "Consumer", "type": "client"},
        {"id": "lb", "label": "Bootstrap / Discovery", "type": "lb"},
        {"id": "b1", "label": "Broker 1 (Leader P0)", "type": "server"},
        {"id": "b2", "label": "Broker 2 (Follower P0)", "type": "server"},
        {"id": "b3", "label": "Broker 3 (Follower P0)", "type": "server"},
        {"id": "log", "label": "Partition Log (disk)", "type": "database"},
        {"id": "ctrl", "label": "Controller", "type": "service"},
        {"id": "kraft", "label": "KRaft Quorum", "type": "database"},
        {"id": "coord", "label": "Group Coordinator", "type": "service"},
        {"id": "offsets", "label": "__consumer_offsets", "type": "queue"},
        {"id": "txn", "label": "Txn Coordinator", "type": "service"},
        {"id": "cleaner", "label": "Log Cleaner", "type": "service"},
    ],
    arch_edges=[
        {"source": "prod", "target": "lb", "label": "discover leaders"},
        {"source": "lb", "target": "b1"},
        {"source": "prod", "target": "b1", "label": "produce"},
        {"source": "b1", "target": "log", "label": "append"},
        {"source": "b2", "target": "b1", "label": "fetch (replicate)"},
        {"source": "b3", "target": "b1", "label": "fetch (replicate)"},
        {"source": "ctrl", "target": "kraft", "label": "metadata log"},
        {"source": "ctrl", "target": "b1", "label": "leader/ISR"},
        {"source": "ctrl", "target": "b2"},
        {"source": "ctrl", "target": "b3"},
        {"source": "cons", "target": "coord", "label": "join group"},
        {"source": "coord", "target": "cons", "label": "assignment"},
        {"source": "cons", "target": "b1", "label": "fetch"},
        {"source": "cons", "target": "offsets", "label": "commit"},
        {"source": "prod", "target": "txn", "label": "begin/commit"},
        {"source": "txn", "target": "b1", "label": "control records"},
        {"source": "cleaner", "target": "log", "label": "compact"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant P as Producer\n"
        "  participant L as Leader Broker\n"
        "  participant F1 as Follower 1\n"
        "  participant F2 as Follower 2\n"
        "  participant C as Consumer\n"
        "  participant Co as Coordinator\n"
        "  P->>L: produce batch (acks=all, PID, seq)\n"
        "  L->>L: append to log (offset N)\n"
        "  F1->>L: fetch from N\n"
        "  L-->>F1: records\n"
        "  F2->>L: fetch from N\n"
        "  L-->>F2: records\n"
        "  L->>L: high-watermark advances\n"
        "  L-->>P: ack (offset N)\n"
        "  C->>Co: join group\n"
        "  Co-->>C: assigned partitions\n"
        "  C->>L: fetch from offset\n"
        "  L-->>C: records (zero-copy)\n"
        "  C->>C: process\n"
        "  C->>Co: commit offset"
    ),
    er_diagram=(
        "erDiagram\n"
        "  TOPIC ||--o{ PARTITION : has\n"
        "  PARTITION ||--o{ REPLICA : on\n"
        "  BROKER ||--o{ REPLICA : hosts\n"
        "  CONSUMER_GROUP ||--o{ OFFSET : commits\n"
        "  PARTITION ||--o{ OFFSET : tracks\n"
        "  TOPIC { string name PK\n int partitions\n int rf\n bool compaction }\n"
        "  PARTITION { string topic\n int partition\n int leader\n string isr }\n"
        "  OFFSET { string group\n string topic\n int partition\n bigint offset }\n"
        "  BROKER { int id PK\n string host\n int port\n string status }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Produce record] --> B{Has key?}\n"
        "  B -->|Yes| C[hash key, pick partition]\n"
        "  B -->|No| D[Sticky / round-robin]\n"
        "  C --> E[Leader appends to log]\n"
        "  D --> E\n"
        "  E --> F[Followers fetch + replicate]\n"
        "  F --> G{All ISR caught up?}\n"
        "  G -->|Yes| H[High-watermark advances]\n"
        "  G -->|No| I[Wait or shrink ISR]\n"
        "  H --> J[Ack producer]\n"
        "  J --> K[Consumer fetches]\n"
        "  K --> L[Process + commit offset]\n"
        "  L --> M[__consumer_offsets compacted topic]"
    ),
    tradeoff_title="Delivery semantics: at-least-once vs exactly-once",
    tradeoff_options=[
        {"label": "At-least-once (ALO) + idempotent consumer",
         "description": "Producer ack=all + retries; consumer dedups by business key.",
         "pros": ["Simple producer + broker model",
                 "No transactional overhead on the hot path",
                 "Sink-agnostic — works with any external system that can dedup"],
         "cons": ["Consumer must implement dedup correctly",
                 "Reasoning about side effects requires care",
                 "Not atomic across multiple output partitions"]},
        {"label": "Exactly-once (EOS) with Kafka transactions",
         "description": "Idempotent producer (PID + seq) + 2PC across partitions; consumer "
                        "reads with isolation.level=read_committed.",
         "pros": ["Atomic read-process-write within Kafka",
                 "No application-level dedup needed for Kafka-only pipelines",
                 "Aborted transactions are skipped by consumers transparently"],
         "cons": ["Higher throughput cost (~10-20%) due to control records and txn coordinator",
                 "Doesn't extend to external sinks without an idempotent or 2PC interface",
                 "More moving parts: transaction coordinator, transactional.id fencing"]},
    ],
    tradeoff_rec="ALO + idempotent consumer for most pipelines; EOS only when the workload is "
                 "Kafka-internal read-process-write or the downstream sink genuinely cannot dedup.",
    senior_topics=[
        _topic("partition-as-unit-of-order",
               "Partition: The Unit of Order and Parallelism",
               "Partitioning is the most consequential design decision. Order is per-partition; "
               "parallelism is bounded by partition count. Pick the partition key to align with "
               "what must be ordered together.",
               [
                   ("Per-partition order, not per-topic",
                    "All records for the same key land on the same partition (murmur2(key) % N) "
                    "and are strictly ordered. Across partitions, no global order is guaranteed. "
                    "If you need per-user order, partition by user_id; if per-account, by account_id."),
                   ("Parallelism ceiling",
                    "Within a consumer group, one partition is consumed by exactly one member. So "
                    "max parallelism = partition count. Under-partitioning bottlenecks consumers; "
                    "over-partitioning wastes metadata and makes rebalances slow."),
                   ("Partition key skew",
                    "Hot keys (one user with 100× the volume) create hot partitions. Mitigations: "
                    "salt the key (user_id + bucket) when order across the salted set is OK, or "
                    "isolate hot tenants on dedicated topics."),
                   ("Sizing partitions",
                    "Rule of thumb: target_throughput / per_consumer_throughput, plus headroom "
                    "for future growth. Default 6-12 for small topics; high-throughput topics "
                    "go to 100s. Adding partitions later breaks key→partition mapping for "
                    "in-flight data — plan up front."),
                   ("Cross-partition order",
                    "If you need global order, use 1 partition (and accept the throughput cap). "
                    "Otherwise embed a global sequencer upstream or use timestamps + tolerate "
                    "out-of-order downstream."),
               ],
               diagram=(
                   "graph LR\n"
                   "  T[Topic: orders] --> P0[Partition 0]\n"
                   "  T --> P1[Partition 1]\n"
                   "  T --> P2[Partition 2]\n"
                   "  P0 --> C1[Consumer A]\n"
                   "  P1 --> C2[Consumer B]\n"
                   "  P2 --> C2\n"
                   "  K1[Key=user_42] -. murmur2 .-> P1\n"
                   "  K2[Key=user_77] -. murmur2 .-> P0"
               )),
        _topic("isr-replication-and-acks",
               "ISR, ack=all, and min.insync.replicas — The Durability Triplet",
               "Durability in Kafka is a function of three settings working together. Misunderstand "
               "any one and silent data loss is possible.",
               [
                   ("In-Sync Replica set",
                    "ISR = leader + followers caught up within replica.lag.time.max.ms (default "
                    "30s). A slow follower is removed from ISR; a recovering follower rejoins once "
                    "caught up. ISR is owned by the controller and persisted in the metadata log."),
                   ("ack=0 / 1 / all semantics",
                    "ack=0: producer fires and forgets — fastest, no durability. ack=1: leader "
                    "writes and acks — fast, but data lost if leader fails before replication. "
                    "ack=all: leader waits for all ISR to fetch — durable, but bounded latency."),
                   ("min.insync.replicas",
                    "Without this, ack=all is meaningless: if ISR shrinks to 1 (leader alone), "
                    "ack=all degrades to ack=1 silently. Setting min.insync.replicas=2 errors "
                    "produces with NotEnoughReplicas when ISR < 2 — a loud failure beats silent "
                    "data loss. Standard config: RF=3 + min.insync.replicas=2 + ack=all."),
                   ("Unclean leader election",
                    "If all ISR die and only out-of-ISR replicas remain, the controller can pick "
                    "one as new leader (unclean.leader.election.enable=true) — risks data loss. "
                    "Default false: prefer unavailability over silent loss. Flip on only for "
                    "throwaway data."),
                   ("Why followers fetch, not leader pushes",
                    "Pull-based replication scales better — followers control their own pace, "
                    "leader doesn't track per-follower buffers. Plus: same fetch path consumers "
                    "use, so one code path serves both."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant P as Producer\n"
                   "  participant L as Leader\n"
                   "  participant F1 as Follower\n"
                   "  participant F2 as Follower\n"
                   "  P->>L: produce (ack=all)\n"
                   "  L->>L: append offset N\n"
                   "  F1->>L: fetch\n"
                   "  L-->>F1: records up to N\n"
                   "  F2->>L: fetch\n"
                   "  L-->>F2: records up to N\n"
                   "  L->>L: ISR all at N → HW=N\n"
                   "  L-->>P: ack offset N"
               )),
        _topic("consumer-group-rebalance",
               "Consumer Group Rebalance Protocol",
               "Rebalance is when membership changes (join, leave, crash, partition added) trigger "
               "redistribution. Done naively, every consumer stops processing. Done well, only the "
               "moving partitions pause.",
               [
                   ("Group coordinator",
                    "One broker per group, chosen by abs(hash(group_id)) % num_offset_partitions, "
                    "co-located with the leader of that __consumer_offsets partition. The "
                    "coordinator tracks members, runs the rebalance, and commits offsets."),
                   ("JoinGroup / SyncGroup",
                    "All members send JoinGroup with their subscriptions. Coordinator picks one "
                    "member as leader, responds with the member list. Leader runs the assignment "
                    "strategy locally and sends back via SyncGroup. Coordinator forwards each "
                    "member's slice. This keeps the coordinator stateless about strategy logic."),
                   ("Assignment strategies",
                    "Range: contiguous partition ranges per consumer (good for joins). RoundRobin: "
                    "interleaved. Sticky: minimizes movement on rebalance. Cooperative-Sticky "
                    "(KIP-429): incremental — only revoke moving partitions, don't stop the world."),
                   ("Heartbeats and session timeout",
                    "Consumer sends Heartbeat every heartbeat.interval.ms. If session.timeout.ms "
                    "passes without a heartbeat, coordinator triggers rebalance. max.poll.interval.ms "
                    "guards against slow processing — long pauses kick the consumer out."),
                   ("Static membership (KIP-345)",
                    "Set group.instance.id; coordinator treats short disconnects as the same "
                    "member returning, skipping rebalance. Critical for stateful consumers (Kafka "
                    "Streams, large local stores) where rebalance triggers expensive state restore."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant C1 as Consumer 1\n"
                   "  participant C2 as Consumer 2\n"
                   "  participant Co as Coordinator\n"
                   "  C1->>Co: JoinGroup\n"
                   "  C2->>Co: JoinGroup\n"
                   "  Co-->>C1: leader, members=[C1,C2]\n"
                   "  Co-->>C2: follower\n"
                   "  C1->>C1: compute assignment\n"
                   "  C1->>Co: SyncGroup (assignment)\n"
                   "  Co-->>C1: P0, P1\n"
                   "  Co-->>C2: P2, P3"
               )),
        _topic("exactly-once-and-transactions",
               "Idempotent Producers + Transactions = Exactly-Once",
               "Exactly-once is the joint property of two mechanisms: idempotent producer dedups "
               "retries within a single partition; transactions provide atomicity across multiple "
               "partitions. Together they give true read-process-write EOS within Kafka.",
               [
                   ("Idempotent producer (PID + seq)",
                    "On enable.idempotence=true, the broker assigns a Producer ID. Each record "
                    "carries (PID, partition, sequence). Broker dedups by checking the sequence "
                    "is exactly last_seq + 1 — duplicates from retries are dropped, gaps trigger "
                    "an error. State persisted in producer_state per partition."),
                   ("Transactional producer",
                    "transactional.id is set by the application. initTransactions() registers it "
                    "with a transaction coordinator and bumps producer epoch — older epoch zombies "
                    "are fenced. beginTransaction → produce to N partitions → addPartitionsToTxn "
                    "→ commitTransaction. Coordinator writes PREPARE then COMMIT to its log."),
                   ("Control records on partitions",
                    "On commit, the coordinator writes a commit-marker control record to each "
                    "involved partition. On abort, an abort-marker. Consumers in read_committed "
                    "mode buffer records until they see a marker, then either deliver (commit) or "
                    "skip (abort) the txn's records."),
                   ("Read-process-write loop",
                    "Kafka Streams pattern: consume from input topic, process, produce to output "
                    "topic, then commit consumer offset — all in one transaction. sendOffsetsToTxn "
                    "writes the offset commit to __consumer_offsets atomically with the output "
                    "produce. Either everything happened or nothing did."),
                   ("Limits of EOS",
                    "EOS is exactly-once within Kafka. To extend across an external sink (DB, "
                    "search index), the sink must be idempotent (dedup by message id) or support "
                    "2PC (rare). Most production pipelines use ALO + idempotent sink — simpler "
                    "and just as correct in practice."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant P as Producer\n"
                   "  participant TC as Txn Coord\n"
                   "  participant T1 as Topic A P0\n"
                   "  participant T2 as Topic B P3\n"
                   "  P->>TC: initTransactions\n"
                   "  TC-->>P: PID, epoch\n"
                   "  P->>TC: beginTxn\n"
                   "  P->>T1: produce (in-txn)\n"
                   "  P->>T2: produce (in-txn)\n"
                   "  P->>TC: addPartitions\n"
                   "  P->>TC: commitTxn\n"
                   "  TC->>T1: commit marker\n"
                   "  TC->>T2: commit marker\n"
                   "  TC-->>P: ok"
               )),
        _topic("retention-and-log-compaction",
               "Retention Policies and Log Compaction",
               "Two retention modes coexist. Time/size retention bounds an event-stream topic; "
               "compaction retains only the latest value per key, turning a topic into a "
               "changelog suitable for materialized state.",
               [
                   ("Time- and size-based retention",
                    "Default cleanup.policy=delete. Segments older than retention.ms (default 7 "
                    "days) or pushing the partition above retention.bytes are deleted whole. "
                    "Cheap — just unlink the file. Tunable per topic; news streams may run hours, "
                    "audit logs years."),
                   ("Log compaction semantics",
                    "cleanup.policy=compact retains the latest value per key forever (or until "
                    "tombstoned). Background log cleaner thread reads segments, builds an offset "
                    "map (key → latest offset), then rewrites segments dropping superseded "
                    "values. Active segment is never compacted — only sealed segments."),
                   ("Tombstones for deletes",
                    "Producing a record with a null value marks the key for deletion. Tombstones "
                    "are retained for delete.retention.ms (default 24h) so consumers can observe "
                    "the deletion, then the cleaner purges them."),
                   ("Use cases",
                    "Compacted topics power changelog/state-store recovery (Kafka Streams), "
                    "configuration broadcasts (latest config per service), and __consumer_offsets "
                    "itself (latest offset per group/topic/partition)."),
                   ("Compact-and-delete hybrid",
                    "cleanup.policy=compact,delete combines both: latest-value-per-key retained, "
                    "but old records also age out by time. Useful for changelogs of ephemeral "
                    "state where forever-retention is overkill."),
               ],
               diagram=(
                   "graph LR\n"
                   "  S0[Segment 0\\nk1=v1, k2=v2, k1=v3] --> X[Cleaner]\n"
                   "  S1[Segment 1\\nk2=v4, k3=v5] --> X\n"
                   "  X --> Y[Compacted]\n"
                   "  Y --> R[k1=v3, k2=v4, k3=v5]"
               )),
        _topic("controller-zk-vs-kraft",
               "Controller, ZooKeeper, and the KRaft Migration",
               "The controller is the cluster's single source of truth for topic metadata, "
               "broker membership, partition leadership, and ISR. Pre-3.x it lived in ZooKeeper; "
               "post-3.x it lives in a Raft-replicated metadata log (KRaft).",
               [
                   ("Controller responsibilities",
                    "Owns the cluster metadata: which topics exist, partition leaders, ISR sets, "
                    "broker liveness. On broker failure, picks new leaders for affected partitions "
                    "from the surviving ISR. On topic creation, assigns partitions to brokers."),
                   ("ZooKeeper era (legacy)",
                    "ZK ensemble (3-5 nodes) hosts znodes: /brokers/ids, /controller, /topics, "
                    "/partitions. One broker is elected controller via ephemeral /controller znode. "
                    "Metadata is read from ZK on broker startup and watched for changes. "
                    "Limitations: ZK scaling cap (~200K partitions), separate operational domain."),
                   ("KRaft (Kafka Raft)",
                    "KIP-500: replace ZK with an internal Raft quorum of 3 or 5 controller "
                    "processes. The metadata log is a Kafka topic itself, replicated by Raft. "
                    "Brokers subscribe by Fetching from the active controller. One system to run, "
                    "scales to millions of partitions, controller failover in seconds."),
                   ("Migration considerations",
                    "Kafka 3.x supports both ZK and KRaft. New clusters: KRaft-only. Existing ZK "
                    "clusters: rolling migration via the migration tool. Kafka 4.x removes ZK. "
                    "The controller quorum nodes can be co-located with brokers (combined mode) "
                    "or separate (recommended for production)."),
                   ("Why a Raft log for metadata",
                    "Metadata is small but consistency-critical. A replicated log gives you "
                    "linearizable history, durable across failures, with a clear leader. "
                    "Brokers tail the log incrementally — no full reload on reconnect."),
               ],
               diagram=(
                   "graph TD\n"
                   "  CQ[Controller Quorum\\n3-5 nodes\\nKRaft Raft] --> ML[Metadata Log]\n"
                   "  ML --> B1[Broker 1]\n"
                   "  ML --> B2[Broker 2]\n"
                   "  ML --> B3[Broker 3]\n"
                   "  B1 -. heartbeat .-> CQ\n"
                   "  B2 -. heartbeat .-> CQ\n"
                   "  B3 -. heartbeat .-> CQ"
               )),
        _topic("backpressure-and-quotas",
               "Backpressure: Producer Buffers, Broker Quotas, ISR Shrink",
               "A high-throughput log gets pushed by producers and pulled by consumers; both "
               "sides need backpressure mechanisms or the slowest link silently melts.",
               [
                   ("Producer-side bounded buffer",
                    "buffer.memory caps the in-flight + unsent record buffer. When full, send() "
                    "blocks up to max.block.ms then throws BufferExhaustedException. Block-then-"
                    "error is the correct shape — silently dropping or unbounded buffering hides "
                    "real problems. Application catches and applies its own backpressure."),
                   ("Broker-side client quotas",
                    "Per-client (or per-user) produce/fetch byte/sec quotas. Exceeding the quota "
                    "doesn't drop or close — broker delays the response by enough milliseconds "
                    "to bring the client into compliance. Loud but non-destructive throttling."),
                   ("Slow-follower ISR shrink",
                    "If a follower can't keep up, it falls out of ISR. Producer with ack=all is "
                    "no longer blocked on it — commits proceed with remaining ISR. Slow follower "
                    "isn't a global outage; it's a local degradation. min.insync.replicas guards "
                    "against shrinking too far."),
                   ("Slow-consumer protection",
                    "A slow consumer just sits at an old offset. Kafka doesn't push — consumer "
                    "fetches at its own pace. Risk: retention may delete data the consumer hasn't "
                    "read. Monitor consumer lag (LEO − committed offset) and alert when it grows. "
                    "Stretching retention is a band-aid; fixing the consumer is the real answer."),
                   ("End-to-end shape",
                    "Backpressure flows: slow consumer → growing lag → ops alert → consumer scaled "
                    "or fixed. Slow follower → ISR shrink → producer keeps going. Slow producer → "
                    "buffer fills → app gets BufferExhausted → app sheds load. Each link is loud "
                    "and observable; nothing is silently dropped."),
               ]),
    ],
)
