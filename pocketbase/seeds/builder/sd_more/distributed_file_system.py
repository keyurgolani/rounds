"""SDQ — Design a Distributed File System (HDFS / GFS-style).

Petabyte-scale append-mostly distributed file system with a metadata namenode,
many block-serving datanodes, replicated immutable blocks, rack-aware placement,
write pipelines, and HA via quorum journal. Mirrors `sd_questions.SD_01` shape
via the `_q` / `_topic` helpers.
"""
from __future__ import annotations

from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design a Distributed File System",
    "Hard",
    "Design a petabyte-scale distributed file system in the GFS / HDFS family: a single logical namespace "
    "of POSIX-like paths whose file contents are split into large fixed-size blocks (64 MB or 128 MB), "
    "each block replicated across several datanodes for durability, and whose metadata (directory tree, "
    "file→block mapping, block→datanode locations) is owned by a namenode. Clients ask the namenode where "
    "a block lives, then stream bytes directly to/from datanodes — the namenode never sits on the data "
    "path. The system is optimised for very large files written once and read many times by batch jobs "
    "(MapReduce, Spark, Trino) — not for many small files, not for random writes, not for low-latency "
    "transactional workloads. The design must survive disk corruption, datanode crashes, and namenode "
    "failover, while serving sustained sequential read throughput in the GB/s per file range.",
    hints=[
        "Separate metadata path from data path — namenode for directory ops, datanodes for byte streams.",
        "Block size is huge (64–128 MB) on purpose: it shrinks the namenode metadata footprint by ~1000×.",
        "Replication factor = 3 with rack awareness is the durability sweet spot, not RAID.",
        "Writes are append-only via a chained replication pipeline; random writes are not in scope.",
        "Namenode keeps the full namespace in RAM — that's why small files are toxic.",
        "HA is namenode-active / namenode-standby on a Quorum Journal Manager, NOT a shared NFS.",
        "Distinguish from object stores (S3, key→blob, no hierarchy) and block stores (EBS, single-attach).",
    ],
    constraints=[
        "Total capacity 10s of PB across thousands of commodity datanodes; disks fail weekly.",
        "Files are typically 100 MB to 100 GB; tens of millions of files (not billions).",
        "Workload: large sequential reads + appending writes; almost no random writes.",
        "Sustained read throughput per client > 100 MB/s; cluster aggregate > 100 GB/s.",
        "Single namenode RAM footprint must hold the namespace — ~150 bytes per file/block in memory.",
        "Cross-rack bandwidth is scarce (oversubscribed core); placement must be rack-aware.",
        "POSIX-like semantics for directory ops; NOT full POSIX — no random writes, no hard links, no fcntl locks.",
    ],
    req_func=[
        "Hierarchical namespace: create / read / delete / rename / list / chmod / chown on paths.",
        "File contents split into fixed-size blocks; one block per file may be smaller (the tail).",
        "Each block replicated R times (default R=3) across datanodes; client picks read replica by locality.",
        "Append-only writes via a write pipeline; close-once semantics; truncate at file end allowed.",
        "Read API: open(path), read(offset, len) → byte stream; seek allowed within an open file.",
        "Block-level checksums (CRC32C per 512 B chunk) to detect bit rot; auto-repair from replica.",
        "Re-replication on datanode loss to restore R; balancer to even out per-node disk fill.",
        "Snapshots of a directory subtree (copy-on-write metadata; blocks shared).",
        "Permissions and authentication (POSIX ugo+rwx; Kerberos for identity in a hardened deployment).",
    ],
    req_nonfunc=[
        "Durability: 11 nines per object (3-replica × independent failure domains).",
        "Availability: namenode HA failover < 60 s; datanode loss invisible to readers (other replicas).",
        "Throughput: per-client sequential read > 100 MB/s; cluster aggregate scales with datanode count.",
        "Latency: metadata ops p99 < 50 ms; first-byte read < 200 ms.",
        "Scale: 100k+ files per directory listable; 100M+ files cluster-wide; 100k+ blocks per datanode.",
        "Operability: rolling upgrades; decommission a node without data loss; balance after add.",
        "Cost: commodity disks; no shared SAN; no RAID at the disk layer (replication does the job).",
    ],
    estimation={
        "cluster_capacity": "20 PB raw / ~6.7 PB usable at R=3",
        "datanodes": "1000 nodes × 12 × 4 TB JBOD = ~48 PB raw (room to grow)",
        "block_size": "128 MB default; configurable per-file (64 MB / 256 MB observed)",
        "blocks_per_file_avg": "~10 (typical 1 GB file); large files have hundreds",
        "files": "~50M files; ~150M blocks pre-replication; ~450M block replicas",
        "namenode_ram": "~150 B/file + ~150 B/block ≈ (50M+150M) × 150 B ≈ 30 GB heap",
        "qps_metadata": "~10k metadata ops/sec steady; ~50k peak (job-launch storms)",
        "throughput_aggregate": "100+ GB/s read; 30+ GB/s write (writes pay 3× for replication)",
        "replication_factor_default": "R=3 (1 same-rack + 2 different-rack)",
        "checksum_chunk": "CRC32C every 512 B → ~0.8% storage overhead",
    },
    endpoints=[
        {"method": "RPC", "path": "namenode.create(path, perm, replication, blocksize)",
         "description": "Allocate a file in namespace; returns lease + first-block placement"},
        {"method": "RPC", "path": "namenode.addBlock(path, prevBlock)",
         "description": "Allocate next block; returns ordered datanode pipeline"},
        {"method": "RPC", "path": "namenode.getBlockLocations(path, offset, len)",
         "description": "Returns list of (block_id, generation_stamp, [datanodes sorted by locality])"},
        {"method": "RPC", "path": "namenode.complete(path, lastBlock)",
         "description": "Finalises file; releases write lease"},
        {"method": "RPC", "path": "namenode.rename(src, dst) / delete / mkdirs / setPermission",
         "description": "Pure metadata ops on the namespace tree"},
        {"method": "RPC", "path": "namenode.snapshot(path)",
         "description": "Copy-on-write metadata snapshot of a directory"},
        {"method": "TCP", "path": "datanode.readBlock(block_id, gen_stamp, offset, len)",
         "description": "Streams bytes with per-chunk CRC32C; client validates on the fly"},
        {"method": "TCP", "path": "datanode.writeBlockPipeline(block_id, [dn2, dn3], data)",
         "description": "Chained replication: dn1 → dn2 → dn3; ACKs flow back the chain"},
        {"method": "RPC", "path": "datanode → namenode.blockReport / heartbeat",
         "description": "Periodic full block report (hours) + heartbeats (3 s) carry liveness + commands"},
        {"method": "HTTP", "path": "GET /webhdfs/v1/<path>?op=OPEN",
         "description": "REST gateway for non-Java clients; redirects to a datanode for the byte stream"},
    ],
    tables=[
        {"name": "inodes (in namenode RAM, persisted via FsImage + edits)",
         "columns": ["inode_id BIGINT PK", "parent_id BIGINT", "name VARCHAR(255)", "type ENUM(file,dir,symlink)",
                     "owner VARCHAR(64)", "group VARCHAR(64)", "perm SMALLINT (ugo+rwx)",
                     "mtime BIGINT", "atime BIGINT", "replication SMALLINT", "block_size INT"]},
        {"name": "file_blocks (file → ordered list of blocks, in namenode RAM)",
         "columns": ["inode_id BIGINT", "block_index INT", "block_id BIGINT", "generation_stamp BIGINT",
                     "num_bytes BIGINT", "PRIMARY KEY (inode_id, block_index)"]},
        {"name": "block_locations (block → datanodes, in namenode RAM, NOT persisted)",
         "columns": ["block_id BIGINT", "datanode_id VARCHAR(64)", "state ENUM(finalized,rbw,rwr,rur)",
                     "PRIMARY KEY (block_id, datanode_id)"]},
        {"name": "datanodes (cluster registry, in namenode RAM)",
         "columns": ["datanode_id VARCHAR(64) PK", "hostname VARCHAR(128)", "rack VARCHAR(64)",
                     "capacity_bytes BIGINT", "used_bytes BIGINT", "remaining_bytes BIGINT",
                     "last_heartbeat_ms BIGINT", "state ENUM(live,decommissioning,dead)",
                     "xceiver_count INT"]},
        {"name": "fsimage (on-disk snapshot of inodes + file_blocks)",
         "columns": ["fsimage_txid BIGINT PK", "path VARCHAR", "size_bytes BIGINT",
                     "checksum CHAR(64)", "created_at_ms BIGINT"]},
        {"name": "edits_log (write-ahead log of namespace ops; mirrored to journal nodes)",
         "columns": ["txid BIGINT PK", "op_code SMALLINT", "args BYTES", "ts_ms BIGINT"]},
        {"name": "journal_nodes (Quorum Journal Manager — replicates edits log)",
         "columns": ["journal_id VARCHAR(64) PK", "addr VARCHAR(64)",
                     "last_promised_epoch BIGINT", "last_accepted_txid BIGINT"]},
        {"name": "leases (active write lease per file)",
         "columns": ["holder VARCHAR(128) PK", "path VARCHAR", "last_renewed_ms BIGINT", "soft_limit_ms BIGINT",
                     "hard_limit_ms BIGINT"]},
        {"name": "snapshots (per-directory CoW metadata)",
         "columns": ["snapshot_id BIGINT PK", "path VARCHAR", "created_at_ms BIGINT",
                     "diff_blob BYTES (delta vs current namespace)"]},
        {"name": "datanode local block storage (per-disk on each datanode)",
         "columns": ["block_id BIGINT", "generation_stamp BIGINT", "len_bytes BIGINT",
                     "data_file PATH (.../blk_<id>)", "meta_file PATH (.../blk_<id>_<genstamp>.meta — CRC + version)"]},
    ],
    indexes=[
        "Namespace tree: inode_id → children (in-RAM hash map per directory inode).",
        "Path lookup: walk components from / using per-directory hashmap (O(depth)).",
        "block_id → list<datanode> (in-RAM map; rebuilt from block reports on namenode startup).",
        "Per-datanode block list (in-RAM; for re-replication and balancer planning).",
        "Rack tree: rack → datanodes (in-RAM; consulted on placement and read locality).",
        "Edits log: append-only file, sealed on segment rotation; indexed by (start_txid, end_txid).",
        "FsImage: single binary file replaced atomically by checkpoint; superseded by next FsImage + edits suffix.",
    ],
    hld_desc=(
        "Master-worker architecture. The namenode is the single logical owner of all metadata: directory "
        "tree, file→block mapping, and (in RAM only) block→datanode locations. The entire namespace fits "
        "in namenode RAM by design. Persistence of metadata is two artefacts: a periodic FsImage binary "
        "snapshot, and an edits log that records every namespace mutation. The edits log is replicated "
        "synchronously to a quorum of Journal Nodes (3 or 5) — this is what makes namenode HA actually "
        "safe. Datanodes serve byte streams; they hold blocks as opaque files on local disks (JBOD, no "
        "RAID). Clients ask the namenode for block locations once, then stream directly from the datanode "
        "of their choice — the namenode never sees the data. Writes form a chained pipeline: client → "
        "dn1 → dn2 → dn3, with ACKs flowing back. Reads are locality-aware: same-node > same-rack > "
        "remote rack. Datanodes heartbeat every 3 s and send full block reports every few hours; the "
        "namenode uses these to detect failure, compute under-replicated blocks, and schedule "
        "re-replication. A Standby Namenode tails the journal and is hot-promotable on active failure."
    ),
    hld_components=[
        {"name": "Active Namenode", "role": "Owns namespace; serves metadata RPCs; allocates blocks; schedules replication"},
        {"name": "Standby Namenode", "role": "Tails edits via JournalNodes; hot-failover; checkpoints FsImage"},
        {"name": "JournalNode Quorum (3 or 5)", "role": "Replicated edits log via Paxos-flavoured QJM"},
        {"name": "ZooKeeper / ZKFC", "role": "Active election + fencing of the loser to prevent split-brain"},
        {"name": "Datanode", "role": "Stores block files + .meta CRC files; serves read/write streams; heartbeat"},
        {"name": "Client Library (DFSClient)", "role": "Path resolution, lease renewal, pipeline I/O, checksum verify"},
        {"name": "Block Pool / Block Manager", "role": "Inside namenode; tracks block→DN map and replication state"},
        {"name": "Block Placement Policy", "role": "Rack-aware: 1 local + 1 same-rack + 1 different-rack"},
        {"name": "Replication Monitor", "role": "Scans for under/over-replicated blocks; queues replication work"},
        {"name": "Balancer", "role": "Off-line tool; moves blocks between DNs to even disk fill"},
        {"name": "WebHDFS / HTTPFS Gateway", "role": "REST front-end for non-Java clients; redirects to datanodes"},
        {"name": "Kerberos KDC", "role": "Identity for users + service principals; SASL on RPCs; delegation tokens"},
    ],
    detailed_design={
        "block_size_choice": (
            "Default 128 MB (64 MB in original GFS, raised over time). Why huge: (a) metadata footprint — "
            "a 1 TB file at 4 KB blocks is 256M block records; at 128 MB blocks it is 8000 records, three "
            "orders of magnitude less in namenode RAM; (b) sequential throughput — large blocks amortise "
            "seek cost and let the disk run at sustained sequential rate (100+ MB/s/disk); (c) network — "
            "the namenode is consulted once per block, so a 10 GB read is ~80 RPCs instead of millions. "
            "The cost is wasted space on the tail block of small files (small file problem), and "
            "coarse-grained parallelism for tiny reads. The fix is workload alignment: this FS is for "
            "large sequential analytics, not for many small files."
        ),
        "namenode_in_ram_metadata": (
            "The active namenode holds the entire namespace in heap: inodes, file→block list, and "
            "block→datanode locations. Rule of thumb: ~150 bytes per file or block. A 100M-file cluster "
            "needs ~30 GB heap, which is comfortable on a beefy master. Block→DN locations are NOT "
            "persisted to disk — they are reconstructed at startup from datanode block reports, which "
            "every datanode sends within minutes of joining the cluster. Persistence is two artefacts on "
            "disk: FsImage (a compact binary snapshot of inodes + file→block mapping) and edits log "
            "(append-only WAL of every namespace mutation). On startup the namenode loads the latest "
            "FsImage, replays edits since that FsImage's transaction id, then waits for a configurable "
            "fraction of expected datanodes to send block reports before leaving safe mode."
        ),
        "fsimage_and_edits_checkpoint": (
            "Every namespace mutation appends one record to the edits log. Without checkpoints the edits "
            "log grows unbounded and startup replay takes forever. The Standby Namenode (or, in older "
            "deployments, a SecondaryNameNode) periodically performs a checkpoint: pull the current "
            "FsImage + new edits, merge them into a new FsImage, ship it back to the Active. This caps "
            "startup replay to the recent edits suffix. Checkpoint trigger: every N transactions (default "
            "1M) or every M seconds (default 1 hour), whichever comes first. The FsImage write itself is "
            "atomic (write to .tmp + rename) and the old FsImage is kept until the new one is verified."
        ),
        "namenode_ha_quorum_journal": (
            "Two namenode processes run simultaneously: one Active, one Standby. They share the edits log "
            "via a Quorum Journal Manager: 3 or 5 lightweight JournalNode processes form a Paxos-style "
            "quorum, and the Active writes every edit to a majority before ACK. The Standby tails the "
            "JournalNodes, applying edits to its in-RAM namespace as they land, and receives heartbeat + "
            "block reports from datanodes too — so on failover it has the full state and is hot-promotable. "
            "The earlier shared-NFS HA is obsolete: NFS introduces a single point of failure that defeats "
            "the purpose. Failover is driven by ZKFC (ZooKeeper Failover Controller), a sidecar on each "
            "namenode that takes a ZK ephemeral lock; loss of the lock by the Active triggers Standby "
            "promotion. STONITH-style fencing of the loser (SSH-based kill or power-fence) prevents "
            "split-brain on flaky networks. End-to-end failover < 60 s, often 5–15 s."
        ),
        "rack_awareness_and_placement": (
            "A datacentre is structured as racks; intra-rack bandwidth (top-of-rack switch) is cheap, "
            "cross-rack bandwidth (core/spine) is scarce and oversubscribed. The placement policy for "
            "R=3: replica 1 on the writer's local node (or any node in writer's rack if writer isn't a "
            "DN); replica 2 on a different rack from replica 1; replica 3 on the same rack as replica 2 "
            "but a different node. Why: 2-of-3 replicas in one rack means a rack failure (TOR switch, "
            "rack power) only loses one replica — durability holds. 1-of-3 in the writer's rack means "
            "writes don't pay full cross-rack bandwidth; subsequent reads have a same-rack replica. "
            "Operators teach the cluster the rack topology via a script (resolve hostname → rack id). "
            "For R>3, additional replicas spread across racks evenly."
        ),
        "write_pipeline": (
            "Client opens file, requests addBlock from namenode, gets back an ordered list of datanodes "
            "[dn1, dn2, dn3] for the new block. Client opens TCP to dn1; dn1 opens TCP to dn2; dn2 to "
            "dn3. Client streams bytes in 64 KB packets to dn1, which buffers and forwards to dn2, which "
            "forwards to dn3. ACKs flow back the chain in reverse: dn3 → dn2 → dn1 → client. Per-packet "
            "ACK lets the client see write progress and surface errors fast. Pipeline failures (dn2 dies "
            "mid-write) are recovered by the client: the namenode is asked for a replacement datanode, a "
            "new generation stamp is allocated for the block (so stale partial replicas can be detected "
            "and garbage-collected), and the pipeline restarts at the surviving prefix. The block is "
            "finalised and committed only after the writer calls close() and the namenode confirms enough "
            "replicas exist."
        ),
        "read_path_locality": (
            "Client calls getBlockLocations(path, offset, len) once per range; namenode returns each block "
            "with its replicas sorted by network distance from the client (same node → same rack → "
            "different rack → different DC). Client opens a TCP connection to the closest live replica "
            "and streams bytes, validating CRC32C per 512 B chunk on the fly. If a chunk fails CRC, the "
            "client closes that DN, reports the corrupt replica to the namenode (which queues it for "
            "deletion + re-replication), and retries from the next closest replica. Reads can be "
            "parallelised across blocks; large analytics frameworks (Spark, MapReduce) co-locate compute "
            "with HDFS replicas via the namenode's locality hints — a job task is scheduled on a node "
            "that holds the block, achieving ~95% local-read rates in practice."
        ),
        "checksums_and_corruption": (
            "Every 512 B of data has a 4-byte CRC32C stored in a sibling .meta file alongside the block "
            "(blk_<id>.meta). Writers compute and store CRCs; readers re-verify on every read. A "
            "background ScanBlocks job on each datanode periodically reads every block and checks CRCs to "
            "catch silent bit rot before a reader hits it. Corrupt replicas are reported to the namenode, "
            "which removes them from the block→DN map and triggers re-replication from a healthy replica. "
            "Storage overhead is ~0.8% (4 B per 512 B). This is end-to-end-ish: corruption between RAM "
            "and disk on a single DN is detected; corruption upstream of the writer is not (which is why "
            "production clients also wrap their own application-level checksums for paranoid pipelines)."
        ),
        "datanode_heartbeat_block_report": (
            "Each datanode sends a heartbeat to the namenode every 3 s (configurable). The heartbeat "
            "carries (capacity, used, remaining, xceiver count, failed volumes); the response carries "
            "commands (replicate this block to dn_x, delete this block, recover this lease, shutdown). "
            "Missing 10 heartbeats (~30 s) marks the DN stale; missing the dead-interval (~10 minutes) "
            "marks it dead and triggers re-replication of all its blocks. Less frequently — every 6 hours "
            "by default — each DN sends a full block report listing every block it holds; this is how the "
            "namenode rebuilds the block→DN map at startup and how drift is corrected steady-state. "
            "Incremental block reports (block added / removed) flow inline with heartbeats so that the "
            "namenode's view is fresh."
        ),
        "node_failure_and_re_replication": (
            "Datanode loss: namenode notices missed heartbeats, marks blocks formerly on the dead DN as "
            "under-replicated, and the Replication Monitor enqueues replication work — pick a healthy "
            "source replica + a healthy target DN that satisfies the rack-aware policy, then issue a "
            "replicate command to the source on its next heartbeat. Throttled (per-DN concurrency cap, "
            "cluster-wide bandwidth cap) so re-replication doesn't crater user workloads. With R=3, the "
            "system tolerates 2 simultaneous replica losses per block before user-visible unavailability. "
            "Disk failure on a DN: only the affected disk's blocks are demoted; the DN keeps serving "
            "from healthy disks. Whole-rack loss: rack-aware policy ensures 1+ replica survives off-rack "
            "for every block; cluster auto-heals as DNs recover."
        ),
        "small_file_problem": (
            "Each file occupies ~150 B in namenode RAM regardless of size, and each block adds another "
            "~150 B. A million 1 KB files cost ~300 MB of namenode heap and provide ~1 GB of data — "
            "1000× worse density than a single 1 GB file. Beyond 100M files the namenode heap pressure "
            "starts to dominate operability (long GCs, slow startup). Mitigations: (1) HAR archives — "
            "concatenate many small files into a tar-like archive and index it; one HAR file = one inode "
            "+ a few blocks; (2) SequenceFile / Avro / Parquet container formats — many records in one "
            "large file with internal indexing; (3) HDFS Federation — multiple namenodes each owning a "
            "namespace subtree, sharing the same datanode pool; (4) push small-file workloads to an "
            "object store (S3) or KV store, where billions of small objects are first-class. The "
            "underlying lesson: this FS amortises a fixed metadata cost per object — design workloads "
            "to keep object count modest and object size large."
        ),
        "append_vs_random_writes": (
            "Original GFS allowed only create + append + delete — no random writes, no truncation. HDFS "
            "added append (initially controversial; eventually stable) and truncate-to-length, but "
            "in-place random writes are still NOT supported. The reason is fundamental: a block has R "
            "replicas streaming through a pipeline, and random in-place updates would require coordinating "
            "writes across replicas with strong consistency — losing the simplicity that makes the "
            "system fast. Append works because only one writer holds the lease at a time, the block "
            "currently being written has a single tail being extended, and the generation stamp lets "
            "us detect stale replicas after pipeline recovery. Workloads that need random writes belong "
            "on a block store (EBS) or a transactional store (a database, an LSM key-value store) — not "
            "here."
        ),
        "snapshots": (
            "Per-directory copy-on-write metadata snapshots. snapshot(/foo) creates a snapshot id; from "
            "that point, modifications to inodes under /foo create diff records rather than mutating the "
            "snapshotted inode in place. Block content is shared — a block referenced by both snapshot "
            "and live state is reference-counted, deleted only when both references drop. Restore = walk "
            "the diff records to reconstruct the historical inode state. Cheap (no data copy), bounded "
            "(diffs are O(changed inodes) per snapshot), and safe for backup workflows. Limitations: "
            "snapshots don't protect against namenode corruption or admin error at the FsImage level — "
            "they live inside the same namespace."
        ),
        "security": (
            "Two-tier security model. (1) Authentication: Kerberos for principals (users + services) — "
            "every RPC carries a SASL-wrapped ticket; cross-cluster trust via realm configuration. "
            "Delegation tokens for long-running jobs (a job acquires a token at submit, uses it for hours "
            "without re-authing). (2) Authorisation: POSIX ugo+rwx on every inode (owner, group, mode); "
            "ACLs (extended setfacl-style entries) for fine-grained access; HDFS-level encryption zones "
            "(per-directory transparent encryption with a KMS-managed master key per zone, per-file DEKs "
            "wrapped by the master). At-rest encryption is per-file; at-rest data-corruption integrity is "
            "the CRC layer. In-flight encryption uses SASL QOP=privacy or RPC-over-TLS. Audit logs of "
            "every namespace op + every read are emitted from the namenode for compliance."
        ),
        "vs_object_store_vs_block_store": (
            "Object store (S3, GCS, Azure Blob): flat key→object namespace (no real directories — keys "
            "with '/' are a UI convention); single-PUT or multipart uploads; eventually consistent (now "
            "strongly consistent in modern S3); no append in the GFS sense; HTTPS-only; perfect for "
            "billions of small to large immutable objects with high durability and low operational "
            "overhead. Trade-off: per-request latency 10–100× higher than a colocated DFS; no compute "
            "locality. Block store (EBS, GCP Persistent Disk): single-host attached virtual disk; full "
            "POSIX random reads/writes; not a shared FS at all. Distributed FS (HDFS / GFS / Lustre / "
            "CephFS): hierarchical namespace, large blocks, replication, compute-data locality, append-"
            "only — chosen for analytics platforms and HPC. Modern stacks often use S3 as the durable "
            "store with a query engine (Spark on S3, Trino on S3, Iceberg/Delta tables) — trading "
            "locality for operational simplicity. The decision tree: many small mutable files → block "
            "store; massive immutable objects, low ops cost → object store; sequential analytics with "
            "compute locality and rich namespace ops → distributed FS like HDFS."
        ),
        "slo_contract": (
            "Metadata RPC p99 < 50 ms; first-byte read p99 < 200 ms; sustained per-client read > "
            "100 MB/s; namenode HA failover < 60 s; cluster tolerates 2 simultaneous DN losses per block "
            "without read unavailability at R=3; silent-corruption MTBD ≥ weeks via background scanner; "
            "edits durability: every committed namespace op is on a JournalNode majority before client ACK."
        ),
    },
    trade_offs=[
        {"option": "Single namenode vs federation vs sharded metadata",
         "for_single": "Simple, strong consistency on the namespace, easy to reason about",
         "for_federation": "Horizontal scale of namespace; shared DN pool; isolation between namespaces",
         "for_sharded": "Removes the metadata ceiling; needed at >500M files",
         "recommendation": "Single namenode + HA standby up to ~100M files; HDFS Federation past that; full sharded metadata only at extreme scale (Colossus / Tectonic territory)."},
        {"option": "Replication R=3 vs erasure coding (e.g. RS(6,3))",
         "for_replication": "Simple, fast recovery, locality-friendly, write-once read-many sweet spot",
         "for_erasure_coding": "Storage overhead 1.5× instead of 3×; reconstruction cost on read",
         "recommendation": "Replication for hot data; erasure coding for cold tiered data — modern HDFS supports both, pick per-policy."},
        {"option": "Block size 64 MB vs 128 MB vs 256 MB",
         "for_64mb": "Finer parallelism for smaller files; less wasted tail",
         "for_128mb": "Modern default; good balance of parallelism and metadata footprint",
         "for_256mb": "Lowest metadata footprint; best for very large sequential reads",
         "recommendation": "128 MB default; bump to 256 MB for log-archive or video workloads; never go below 64 MB."},
        {"option": "Namenode HA via shared NFS vs Quorum Journal Manager",
         "for_nfs": "Simple to set up; familiar admin model",
         "for_qjm": "No external SPOF; quorum-replicated edits log; supports rolling upgrade",
         "recommendation": "QJM, always — shared NFS reintroduces the SPOF that HA was supposed to remove."},
        {"option": "DFS vs object store vs block store",
         "for_dfs": "Hierarchical namespace, compute-data locality, append, large sequential analytics",
         "for_object": "Billions of immutable objects, low ops cost, durable, low-locality",
         "for_block": "Single-host POSIX random R/W, not shared",
         "recommendation": "Use the object store unless you need locality + append + a hierarchical namespace; use the block store only for single-host workloads."},
        {"option": "Sync replication of edits via QJM vs async to a hot standby",
         "for_sync_qjm": "Zero metadata loss on namenode crash; supported failover in seconds",
         "for_async": "Lower steady-state RPC latency",
         "recommendation": "Sync to QJM majority — namespace is the most precious metadata in the system; you cannot lose a metadata op."},
    ],
    tips=[
        "Lead with the master/worker split and the 'metadata path is separate from data path' invariant — that's the architectural spine.",
        "Quote concrete numbers: 128 MB blocks, R=3, ~150 B per file/block in namenode RAM. Vague numbers read as hand-waving.",
        "Naming the rack-aware placement policy (1 local + 1 same-rack + 1 different-rack) is a senior signal.",
        "When asked about HA, immediately say 'Quorum Journal Manager + ZKFC' and mention fencing — shared-NFS HA is an anti-pattern.",
        "Distinguish DFS from object store and block store unprompted; senior interviewers want to see you place the system in the wider storage taxonomy.",
        "Treat the small-file problem as a known limitation with named mitigations (HAR, federation, container formats), not an oversight.",
        "Append + close-once + immutable blocks is a feature, not a limitation — it's what makes the design tractable.",
        "Never put the namenode on the data path. Every byte goes datanode↔client. The namenode handles only metadata.",
    ],
    thought_process=[
        "1. Clarify: petabyte-scale, sequential analytics, write-once read-many, large files. NOT a transactional store.",
        "2. Estimate: 50M files × ~10 blocks × 3 replicas × 128 MB ≈ 20 PB raw; namenode heap ≈ 30 GB.",
        "3. Architecture: master namenode for metadata, many datanodes for blocks, client streams direct to datanodes.",
        "4. Block size: 128 MB — collapses metadata footprint and amortises seeks over sequential I/O.",
        "5. Replication: R=3 with rack-aware placement (1 local + 2 cross-rack) for durability without RAID.",
        "6. Write path: client → namenode (allocate + pipeline) → chained replication dn1→dn2→dn3 → close.",
        "7. Read path: getBlockLocations once per range; client streams from closest replica; CRC verify per chunk.",
        "8. Metadata persistence: in-RAM namespace + FsImage snapshot + edits WAL + checkpoint via standby.",
        "9. HA: Active + Standby + 3-or-5 JournalNodes (QJM) + ZKFC for election + fencing for split-brain.",
        "10. Failure: heartbeats (3 s) + block reports (hours) drive re-replication; CRC scrub catches bit rot.",
        "11. Small-file problem: ~150 B per object in heap; mitigate via HAR / federation / container formats.",
        "12. Append-only — random writes are out of scope; that's what block stores or transactional stores are for.",
        "13. Snapshots: per-directory copy-on-write metadata; blocks shared via reference counting.",
        "14. Security: Kerberos auth, POSIX + ACLs, encryption zones via KMS, in-flight SASL/TLS.",
        "15. Position vs alternatives: object store for low-locality cheap durability; block store for single-host POSIX.",
    ],
    tags=["distributed-file-system", "hdfs", "gfs", "storage", "replication", "rack-aware", "namenode-ha", "big-data"],
    arch_nodes=[
        {"id": "client", "label": "DFS Client", "type": "client"},
        {"id": "nn_active", "label": "Active Namenode", "type": "server"},
        {"id": "nn_standby", "label": "Standby Namenode", "type": "server"},
        {"id": "qjm", "label": "JournalNode Quorum (3 or 5)", "type": "service"},
        {"id": "zk", "label": "ZooKeeper / ZKFC", "type": "service"},
        {"id": "dn_rack_a", "label": "Datanodes (Rack A)", "type": "server"},
        {"id": "dn_rack_b", "label": "Datanodes (Rack B)", "type": "server"},
        {"id": "fsimage", "label": "FsImage + edits", "type": "database"},
        {"id": "kms", "label": "Kerberos KDC + KMS", "type": "service"},
        {"id": "webhdfs", "label": "WebHDFS Gateway", "type": "lb"},
    ],
    arch_edges=[
        {"source": "client", "target": "nn_active", "label": "metadata RPC"},
        {"source": "client", "target": "dn_rack_a", "label": "read/write bytes"},
        {"source": "client", "target": "dn_rack_b", "label": "read/write bytes"},
        {"source": "dn_rack_a", "target": "dn_rack_b", "label": "pipeline replicate"},
        {"source": "dn_rack_a", "target": "nn_active", "label": "heartbeat + block report"},
        {"source": "dn_rack_b", "target": "nn_active", "label": "heartbeat + block report"},
        {"source": "nn_active", "target": "qjm", "label": "edits log (sync majority)"},
        {"source": "qjm", "target": "nn_standby", "label": "tail edits"},
        {"source": "nn_active", "target": "fsimage", "label": "checkpoint"},
        {"source": "nn_standby", "target": "fsimage", "label": "checkpoint write"},
        {"source": "zk", "target": "nn_active", "label": "election lock"},
        {"source": "zk", "target": "nn_standby", "label": "watch + promote"},
        {"source": "client", "target": "kms", "label": "Kerberos auth"},
        {"source": "webhdfs", "target": "client", "label": "REST → redirect"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant C as Client\n"
        "  participant NN as Active Namenode\n"
        "  participant J as JournalNodes\n"
        "  participant D1 as Datanode 1 (rack A)\n"
        "  participant D2 as Datanode 2 (rack B)\n"
        "  participant D3 as Datanode 3 (rack B)\n"
        "  Note over C,NN: WRITE — append a block\n"
        "  C->>NN: addBlock(/foo/bar)\n"
        "  NN->>NN: allocate block_id, gen_stamp\n"
        "  NN->>NN: pick rack-aware [D1,D2,D3]\n"
        "  NN->>J: edits.append(addBlock) — sync majority\n"
        "  J-->>NN: ack\n"
        "  NN-->>C: block_id, [D1,D2,D3]\n"
        "  C->>D1: write packets\n"
        "  D1->>D2: forward\n"
        "  D2->>D3: forward\n"
        "  D3-->>D2: ack\n"
        "  D2-->>D1: ack\n"
        "  D1-->>C: ack\n"
        "  C->>NN: complete()\n"
        "  NN->>J: edits.append(complete)\n"
        "  Note over C,D3: READ — locality-aware\n"
        "  C->>NN: getBlockLocations(/foo/bar)\n"
        "  NN-->>C: [D2 (same rack), D1, D3]\n"
        "  C->>D2: readBlock\n"
        "  D2-->>C: bytes + CRC32C per 512B\n"
        "  C->>C: verify CRC\n"
        "  Note over NN,D1: FAILURE — D1 dies\n"
        "  D1-xNN: missed heartbeats\n"
        "  NN->>NN: mark D1 dead; under-replicate\n"
        "  NN->>D2: replicate block to D_new (next heartbeat)"
    ),
    er_diagram=(
        "erDiagram\n"
        "  CLUSTER ||--|| NAMENODE_HA : has\n"
        "  NAMENODE_HA ||--|| ACTIVE_NN : runs\n"
        "  NAMENODE_HA ||--|| STANDBY_NN : runs\n"
        "  NAMENODE_HA ||--o{ JOURNAL_NODE : edits_quorum\n"
        "  CLUSTER ||--o{ RACK : has\n"
        "  RACK ||--o{ DATANODE : contains\n"
        "  DATANODE ||--o{ BLOCK_REPLICA : stores\n"
        "  INODE ||--o{ FILE_BLOCK : contains\n"
        "  FILE_BLOCK ||--o{ BLOCK_REPLICA : has_3_of\n"
        "  INODE ||--o| LEASE : write_locked_by\n"
        "  INODE ||--o{ SNAPSHOT_DIFF : versioned_via\n"
        "  BLOCK_REPLICA ||--|| CHECKSUM_META : has\n"
        "  INODE { bigint inode_id PK\n string name\n short perm\n int replication\n int block_size }\n"
        "  FILE_BLOCK { bigint block_id\n bigint generation_stamp\n bigint num_bytes }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B[Master/worker: namenode + datanodes]\n"
        "  B --> C[Block size 128 MB — large, sequential]\n"
        "  C --> D[Replication R=3 + rack-aware placement]\n"
        "  D --> E[Write: chained pipeline dn1->dn2->dn3]\n"
        "  D --> F[Read: locality-aware, CRC verify]\n"
        "  B --> G[Namespace in RAM + FsImage + edits log]\n"
        "  G --> H[HA: Active/Standby + Quorum JournalNodes + ZKFC]\n"
        "  D --> I[Heartbeat + block report drive re-replication]\n"
        "  I --> J[Background CRC scrub for bit rot]\n"
        "  C --> K{Many small files?}\n"
        "  K -->|yes| L[Namenode RAM pressure → HAR / federation]\n"
        "  K -->|no| M[Sweet spot]\n"
        "  B --> N[Append-only — no random writes]\n"
        "  B --> O[Vs object store / vs block store positioning]"
    ),
    tradeoff_title="Distributed FS vs Object Store vs Block Store",
    tradeoff_options=[
        {"label": "Distributed File System (HDFS / GFS / CephFS)",
         "description": "Hierarchical namespace, large fixed blocks, replication, compute-data locality, append-only.",
         "pros": ["Compute-data locality (95% local reads in analytics jobs)",
                 "Hierarchical namespace with directory ops",
                 "Sustained sequential throughput at GB/s per file",
                 "Append + atomic close semantics for streaming writers"],
         "cons": ["Namenode is a metadata bottleneck (single namespace ceiling ~100M files)",
                 "Small-file toxicity (~150 B per object in heap)",
                 "No random writes; not POSIX-complete",
                 "Significant operational burden (rack topology, balancer, HA)"]},
        {"label": "Object Store (S3, GCS, Azure Blob)",
         "description": "Flat key→object map with REST API; durability via background erasure coding; managed service.",
         "pros": ["Effectively unlimited capacity and object count (billions)",
                 "11 nines durability with operator-managed redundancy",
                 "Zero ops overhead for the consumer; pay-per-use",
                 "Strongly consistent reads (modern S3)"],
         "cons": ["No hierarchical namespace (keys with '/' are a convention, not directories)",
                 "Per-request latency 10–100× a colocated DFS",
                 "No compute locality — every read is a network call",
                 "No native append; multipart upload + immutable objects only"]},
        {"label": "Block Store (EBS, GCP Persistent Disk)",
         "description": "Virtual disk attached to a single host; full POSIX random R/W via the OS file system on top.",
         "pros": ["Full POSIX semantics including random writes and fcntl locks",
                 "Predictable single-host performance and IOPS",
                 "Drop-in for legacy applications expecting a local disk"],
         "cons": ["Not a shared file system — single-attach per volume (mostly)",
                 "Capacity bounded by single volume size limits",
                 "Replication is invisible to the user; no app-level redundancy",
                 "No compute fan-out — one host owns the disk"]},
    ],
    tradeoff_rec=(
        "Use a distributed FS like HDFS when you need (a) compute-data locality for analytics, (b) a real "
        "hierarchical namespace, and (c) sustained GB/s sequential throughput per file — i.e. classic "
        "MapReduce / Spark / Trino on-prem. Use an object store when you have many objects, durability "
        "and operability matter more than locality, and your compute layer can absorb the higher per-"
        "request latency (modern cloud-native data lakes lean here). Use a block store only for "
        "single-host POSIX workloads that genuinely need random writes and locks (databases, single-"
        "node app servers). The decision is rarely 'all of one' — production stacks routinely mix: "
        "block store for the database, object store for archival and shared access, and a DFS (or DFS-"
        "like layer over the object store) for the analytics estate."
    ),
    senior_topics=[
        _topic("namenode-ha-qjm",
               "Namenode High Availability via Quorum Journal Manager",
               "How HDFS makes the namenode — the single owner of all metadata — survive process crashes, "
               "host failures, and rolling upgrades without losing a single namespace edit, and without "
               "introducing an external single point of failure.",
               [
                   ("The original SPOF",
                    "First-generation HDFS had one namenode; if it died, the cluster was offline until "
                    "an operator restarted it and reloaded FsImage + replayed edits — minutes to hours of "
                    "outage. The SecondaryNameNode helped checkpoint but was not a hot standby; it could "
                    "not take over."),
                   ("Shared-NFS HA (legacy, deprecated)",
                    "Active and Standby namenodes shared the edits log on an NFS server. The Standby "
                    "tailed it; on Active failure ZKFC promoted the Standby. The fatal flaw: the NFS "
                    "server itself was now the SPOF — and NFS gives no quorum guarantee, so a flaky "
                    "network could let both namenodes write."),
                   ("Quorum Journal Manager",
                    "Run an odd number (3 or 5) of lightweight JournalNode processes. The Active "
                    "namenode writes every namespace edit to a majority of JournalNodes synchronously "
                    "before ACKing the client RPC — this is a Paxos-style write quorum on the edits log. "
                    "The Standby tails the JournalNodes and applies edits to its own in-RAM namespace as "
                    "they land. Tolerates loss of any (N-1)/2 JournalNodes (1 of 3, 2 of 5) without edit "
                    "loss or unavailability."),
                   ("ZKFC and election",
                    "Each namenode runs a ZooKeeper Failover Controller sidecar. ZKFC tries to acquire a "
                    "ZK ephemeral lock; the holder is Active, the other is Standby. If the Active's "
                    "ZKFC loses the lock (process crash, network drop, GC pause exceeding ZK session "
                    "timeout), the Standby's ZKFC sees the watch fire and takes the lock — this is the "
                    "promotion trigger."),
                   ("Fencing — the silent prerequisite",
                    "Promotion is unsafe if the previous Active is alive and still writing to "
                    "JournalNodes (split-brain). Before promoting, the new Active fences the loser: SSH "
                    "+ kill, IPMI power-fence, or — at the JournalNode layer itself — epoch numbers. The "
                    "JournalNodes refuse writes from any namenode whose epoch is lower than the highest "
                    "they have promised, so a partitioned old Active simply cannot commit edits when it "
                    "rejoins. Epoch-based fencing is the senior answer."),
                   ("Failover budget",
                    "End-to-end failover from Active death to Standby serving traffic: typically 5–60 s. "
                    "The Standby already has the in-RAM namespace (because it was tailing edits) and "
                    "already has datanode block reports (because all DNs heartbeat to BOTH namenodes). "
                    "What it pays on promotion is the time to confirm fencing, exit safe-mode-equivalent "
                    "checks, and accept the Active role from ZK."),
                   ("Datanode dual-reporting",
                    "Every datanode heartbeats and block-reports to BOTH namenodes — Active and Standby. "
                    "This is critical: if only the Active received block reports, the Standby on "
                    "promotion would have no idea where blocks live and would refuse to serve until it "
                    "rebuilt the map (~minutes). Dual-reporting cuts failover from minutes to seconds."),
                   ("What this does NOT solve",
                    "Logical data corruption (an admin runs rm -rf on the wrong subtree) — both Active "
                    "and Standby happily replicate the delete to JournalNodes. This is what snapshots, "
                    "trash, and off-cluster backups are for. HA is for process and host failures, not "
                    "for human error or namespace logical corruption."),
               ],
               diagram=(
                   "graph TD\n"
                   "  C[Client] --> NN_A[Active Namenode]\n"
                   "  C -. failover .-> NN_S[Standby Namenode]\n"
                   "  NN_A -->|edits sync majority| J1[JN1]\n"
                   "  NN_A --> J2[JN2]\n"
                   "  NN_A --> J3[JN3]\n"
                   "  J1 --> NN_S\n"
                   "  J2 --> NN_S\n"
                   "  J3 --> NN_S\n"
                   "  ZK[ZooKeeper] --> ZKFC_A[ZKFC sidecar]\n"
                   "  ZK --> ZKFC_S[ZKFC sidecar]\n"
                   "  ZKFC_A --> NN_A\n"
                   "  ZKFC_S --> NN_S\n"
                   "  DN[Datanodes] -->|heartbeat + block report to BOTH| NN_A\n"
                   "  DN --> NN_S"
               )),
        _topic("rack-aware-placement",
               "Rack-Aware Block Placement Policy",
               "Why HDFS spends real engineering effort to know the physical rack topology, and how the "
               "default 1-local-plus-2-cross-rack policy survives realistic correlated failures while "
               "respecting scarce cross-rack bandwidth.",
               [
                   ("Failure domains in a real datacentre",
                   "Disks fail every few hours per fleet; nodes fail weekly; whole racks fail monthly "
                   "(top-of-rack switch reboot, power phase loss, cable yank). Replication that ignores "
                   "topology lets a single rack failure take down all R replicas of some block, costing "
                   "you durability you thought you had. Topology-aware placement converts independent "
                   "datacentre failures into independent replica failures."),
                   ("The default policy for R=3",
                   "Replica 1: writer's local node (or random node in writer's rack if writer isn't a "
                   "DN). Replica 2: a different rack from replica 1. Replica 3: same rack as replica 2 "
                   "but different node. Why not all three on different racks? Cross-rack bandwidth is "
                   "expensive — 2-of-3 on one rack means writes only pay one cross-rack hop, and reads "
                   "have a same-rack replica."),
                   ("Why this survives a rack outage",
                   "Rack outage takes out either replica 1 (writer's rack) — leaving 2 on the other "
                   "rack — or replicas 2+3 (the cross-rack pair) — leaving 1 on the writer's rack. "
                   "Either way ≥1 replica survives, so reads keep working and re-replication restores R."),
                   ("Why this saves cross-rack bandwidth",
                   "Pure 'all racks different' would cost the writer 3 cross-rack hops per block; "
                   "1-local + 2-cross saves 1 hop on the write path. At sustained 10 GB/s ingest, that "
                   "is real money in core-router budget."),
                   ("Higher replication and special cases",
                   "R=4+: spread the additional replicas evenly across racks. R=2: 1 local + 1 cross-"
                   "rack (less safe — single rack failure can lose both). HDFS exposes pluggable "
                   "BlockPlacementPolicy for orgs with multi-DC topologies (one replica in each region "
                   "for DR)."),
                   ("Operationally — how the namenode learns the topology",
                   "Operator configures a topology resolution script (or pluggable resolver class) that "
                   "maps hostname → rack id. The namenode invokes it at DN registration. Mistakes here "
                   "(every node mapped to /default-rack) silently disable rack awareness — you get "
                   "placement that looks correct but isn't. Sanity-check via fsck and the namenode UI."),
                   ("Reads are locality-sorted by the same topology",
                   "On getBlockLocations, the namenode sorts replicas by network distance from the "
                   "client: same-node (cost 0) > same-rack (cost 2) > different-rack same-DC (cost 4) "
                   "> different-DC. Job schedulers (YARN, Spark) then place tasks on nodes that hold "
                   "the input block, achieving the famous 'compute moves to data' property."),
               ],
               diagram=(
                   "graph TD\n"
                   "  W[Writer] -->|replica 1| L[Local node — Rack A]\n"
                   "  W -->|replica 2| R2[Node X — Rack B]\n"
                   "  W -->|replica 3| R3[Node Y — Rack B]\n"
                   "  subgraph Rack A\n"
                   "    L\n"
                   "    A1[other DNs]\n"
                   "  end\n"
                   "  subgraph Rack B\n"
                   "    R2\n"
                   "    R3\n"
                   "    B1[other DNs]\n"
                   "  end\n"
                   "  RackOutA[Rack A outage] -.-> L\n"
                   "  RackOutA -.-> SurvivorsB[2 replicas in Rack B survive]\n"
                   "  RackOutB[Rack B outage] -.-> R2\n"
                   "  RackOutB -.-> R3\n"
                   "  RackOutB -.-> SurvivorA[1 replica in Rack A survives]"
               )),
        _topic("write-pipeline-and-recovery",
               "The Write Pipeline and Pipeline Recovery",
               "How HDFS streams a block to R datanodes via chained replication, why per-packet ACKs are "
               "the unit of durability, and how the system recovers cleanly when a datanode in the chain "
               "fails mid-write.",
               [
                   ("Why chained, not fan-out",
                   "Two ways to replicate a block to 3 DNs: fan-out (writer streams to all 3 in "
                   "parallel) or chained (writer → dn1 → dn2 → dn3). Chained wins because (a) the "
                   "writer's NIC bandwidth is paid only once — at fan-out 3× — and (b) the topology "
                   "policy puts dn1 same-rack as the writer and dn2/dn3 cross-rack, so the cross-rack "
                   "hop is paid by the chain, not by the writer's edge link."),
                   ("Packet structure",
                   "The data stream is split into 64 KB packets (configurable). Each packet contains "
                   "data + per-512-B CRC32C chunks + a sequence number. The writer pushes packets into "
                   "an in-flight window and waits for ACKs to slide it; backpressure is built in."),
                   ("ACKs flow back the chain",
                   "dn3 receives packet, persists to OS buffer + CRC verify, ACKs to dn2. dn2 ACKs to "
                   "dn1 only after its own persist. dn1 ACKs to client. Client now knows packet is on "
                   "all 3 DNs (modulo their fsync policy). The block is finalised on close, which is "
                   "when the namenode is told 'this block is done; here is its final length and "
                   "generation stamp'."),
                   ("Mid-pipeline failure",
                   "If dn2 dies mid-block, dn1 sees the TCP error and bubbles it back to the client. "
                   "Client requests pipeline recovery from the namenode: a new generation stamp is "
                   "allocated for the block (so any stale partial replica with the old gen stamp is "
                   "garbage), the namenode picks a replacement DN (rack-aware again), and the writer "
                   "resumes streaming from the last ACKed packet. The chain may shrink temporarily "
                   "(stream to 2 DNs while a replacement is found); HDFS has policies for "
                   "min-replication-during-write."),
                   ("Generation stamp — the unsung hero",
                   "Every block has a generation stamp incremented on each pipeline recovery. After "
                   "recovery, a partial replica from the previous attempt has an older stamp; on its "
                   "next block report the namenode notices the mismatch and orders deletion. Without "
                   "gen stamps, the cluster could not tell a stale partial replica from a healthy one."),
                   ("Lease and close-once semantics",
                   "Only one writer per file at a time, enforced by a soft + hard lease on the "
                   "namenode. If the writer dies without close(), the namenode reclaims the lease "
                   "after the hard limit (~1 hour by default) and either closes the file at the last "
                   "complete block or truncates the partial tail. close() is idempotent; clients "
                   "retry safely."),
                   ("What this design refuses to do",
                   "No mid-block random writes — supporting them would require multi-replica strong "
                   "consistency and undo the simplicity that lets the pipeline run at line rate. "
                   "Append-only is the architectural choice that makes everything else fast."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant C as Client\n"
                   "  participant D1 as DN1 (rack A)\n"
                   "  participant D2 as DN2 (rack B)\n"
                   "  participant D3 as DN3 (rack B)\n"
                   "  C->>D1: pkt(seq=1)\n"
                   "  D1->>D2: pkt(seq=1)\n"
                   "  D2->>D3: pkt(seq=1)\n"
                   "  D3-->>D2: ack(1)\n"
                   "  D2-->>D1: ack(1)\n"
                   "  D1-->>C: ack(1)\n"
                   "  Note over D2: D2 dies\n"
                   "  D1-xD2: pkt(seq=N)\n"
                   "  D1-->>C: pipeline error\n"
                   "  C->>NN: recover (newGenStamp, replacement)\n"
                   "  NN-->>C: [D1, D2_new, D3] gs=g+1\n"
                   "  C->>D1: pkt(seq=N) gs=g+1\n"
                   "  D1->>D2_new: pkt(seq=N) gs=g+1\n"
                   "  D2_new->>D3: pkt(seq=N) gs=g+1"
               )),
        _topic("checksums-and-corruption-detection",
               "Block Checksums and Bit-Rot Detection",
               "Cheap, layered defence against silent data corruption — disks lie, RAM bit-flips, network "
               "interfaces drop bits — and the system detects it on every read plus a background scrub.",
               [
                   ("The threat: silent corruption",
                   "A petabyte cluster has hundreds of millions of disk sectors. Even at quoted "
                   "manufacturer URE rates (1 in 10^14 bits), random bit flips happen weekly. Without "
                   "checksums these slide silently into reader output — a job processes corrupt input, "
                   "produces wrong results, ships them to dashboards. Detection has to be the system's "
                   "job, not the user's."),
                   ("Per-chunk CRC32C",
                   "Every 512 bytes of block data has a 4-byte CRC32C stored in a sibling .meta file "
                   "(blk_<id>_<gen>.meta). Storage overhead is 4 / 512 = 0.78%. CRC32C is a hardware-"
                   "accelerated polynomial checksum that catches any single-bit error and almost all "
                   "multi-bit errors within a chunk."),
                   ("Computed on write, verified on read",
                   "The writer computes CRCs as bytes flow through the client library; CRCs are sent "
                   "with the packet down the pipeline; each DN persists CRCs alongside data. On read, "
                   "the DN sends both data and CRCs; the client re-verifies per chunk before delivering "
                   "bytes to the application. Mismatch triggers a retry from the next replica + a "
                   "report to the namenode."),
                   ("Background scanner",
                   "Each datanode has a BlockScanner thread that walks its blocks on a configured "
                   "period (default ~3 weeks) and reads-and-CRCs every block. This catches latent "
                   "corruption before any user reads it. Throttled (a few MB/s per DN) so it doesn't "
                   "compete with foreground I/O."),
                   ("End-to-end is a stretch goal",
                   "Strictly, this checksum is between the writer's library and the reader's library "
                   "of the same FS — corruption in the application before the writer sees it is not "
                   "caught. Truly end-to-end means the application carries its own checksum / "
                   "signature over the bytes it cares about. Most production big-data formats "
                   "(Parquet, ORC, Avro) include their own page/row CRCs as belt-and-braces."),
                   ("Self-healing on detection",
                   "Reader's bad-replica report → namenode marks that replica corrupt → block becomes "
                   "under-replicated → Replication Monitor schedules a replicate-from-good-replica → "
                   "corrupt replica is deleted. From the user's perspective: one read failed, the next "
                   "succeeded, and durability silently restored itself."),
               ],
               diagram=(
                   "graph TD\n"
                   "  W[Writer] -->|data + CRC32C/512B| L[client lib computes CRC]\n"
                   "  L --> P[pipeline → DN1, DN2, DN3]\n"
                   "  P --> M[blk_<id> + blk_<id>.meta]\n"
                   "  R[Reader] --> DN[Datanode]\n"
                   "  DN --> Send[stream data + CRC]\n"
                   "  Send --> V[client verifies per 512B]\n"
                   "  V -->|mismatch| Bad[report bad replica]\n"
                   "  Bad --> NN[Namenode]\n"
                   "  NN --> RR[re-replicate from good]\n"
                   "  Scan[Background BlockScanner] -. periodic .-> M\n"
                   "  Scan -->|silent corruption found| Bad"
               )),
        _topic("small-file-problem",
               "The Small-File Problem and Its Mitigations",
               "Why a file system optimised for petabytes-of-large-files chokes on millions-of-tiny-files, "
               "and the named industry-standard mitigations — none of which fix the underlying tension; "
               "they reshape the workload around it.",
               [
                   ("The cost model",
                   "Namenode RAM is dominated by inodes (~150 B each) and block records (~150 B each). "
                   "A million 1 KB files = 1 million inodes + 1 million blocks (one block each, sub-"
                   "block-size) ≈ 300 MB of namenode heap, holding 1 GB of actual data. Compare to one "
                   "1 GB file: 1 inode + ~8 blocks ≈ 1.5 KB of heap. The metadata-to-data ratio is "
                   "~200,000× worse for the small-file case."),
                   ("Operational symptoms",
                   "Above 100M files: namenode startup takes 10s of minutes (FsImage load is "
                   "proportional to inode count); GC pauses on the namenode JVM grow into seconds; "
                   "metadata RPC latency tail blows up; failover takes longer (Standby's safe-mode wait "
                   "scales). Cluster operators learn to fear file-count growth more than data-volume "
                   "growth."),
                   ("Mitigation 1 — HAR archives",
                   "Hadoop Archives concatenate many small files into a tar-like archive with an index. "
                   "The result is one inode + a few blocks for thousands of original files. Read-only — "
                   "good for cold log dumps, archived training data, anything write-once. Tools "
                   "transparently expose paths inside the HAR via the har:// URI."),
                   ("Mitigation 2 — container formats",
                   "SequenceFile, Avro, Parquet, ORC pack many records into one large file with internal "
                   "indexing and column statistics. This is the dominant approach in modern data lakes: "
                   "the analytics engine reads pages or row groups, not 'files'. Combined benefit: large "
                   "files for the FS + columnar compression + predicate pushdown."),
                   ("Mitigation 3 — HDFS Federation",
                   "Multiple namenodes, each owning a disjoint subtree of the namespace, sharing a "
                   "single pool of datanodes. Horizontal scale of metadata, plus failure isolation "
                   "(namenode crash affects only its subtree). Doesn't fix small-file density per "
                   "namenode but multiplies the file-count budget by the number of namenodes."),
                   ("Mitigation 4 — push it elsewhere",
                   "If the workload is genuinely many small mutable files (user uploads, thumbnail "
                   "image cache), it doesn't belong in HDFS. Object stores (S3, GCS) are first-class "
                   "for billions of small immutable objects; KV stores (DynamoDB, Cassandra, RocksDB) "
                   "for small mutable records. Architectural move: change the storage tier, not the FS."),
                   ("The senior framing",
                   "The small-file problem is not a bug; it is the price of a single-namespace metadata "
                   "design that puts everything in RAM to keep the metadata path fast. Acknowledge the "
                   "tension, name the mitigations, recommend a concrete one for the workload at hand. "
                   "Vague hand-waving on this question is a reliable junior signal."),
               ],
               diagram=(
                   "graph TD\n"
                   "  P[Many small files] --> NN[Namenode RAM bloats]\n"
                   "  NN --> Slow[Slow startup, long GCs]\n"
                   "  P --> M1[Mitigate: HAR archive]\n"
                   "  P --> M2[Mitigate: Parquet / ORC / SequenceFile]\n"
                   "  P --> M3[Mitigate: HDFS Federation — multi-NN]\n"
                   "  P --> M4[Mitigate: object store / KV store]\n"
                   "  M1 --> OK[Few inodes, many records]\n"
                   "  M2 --> OK\n"
                   "  M3 --> Scaled[Multiplied file-count budget]\n"
                   "  M4 --> RightTier[Workload on right storage tier]"
               )),
        _topic("dfs-vs-object-vs-block",
               "Distributed FS vs Object Store vs Block Store",
               "Three families of distributed storage with very different namespace, consistency, and "
               "performance contracts. Senior interviewers want to see you place HDFS in the wider "
               "taxonomy, not just describe it in isolation.",
               [
                   ("Distributed File System (this design)",
                   "Hierarchical namespace; large fixed blocks; replication for durability; compute-data "
                   "locality; append-only writes; close-once immutable blocks. Hot path is sustained "
                   "sequential GB/s per file. Examples: HDFS, GFS, Lustre, CephFS, Tectonic, Colossus."),
                   ("Object Store",
                   "Flat key→object map; HTTPS REST API (GET / PUT / DELETE / multipart); durability via "
                   "operator-managed erasure coding; effectively unlimited scale; no compute locality; "
                   "per-request latency in tens of ms. Eventually consistent historically, strongly "
                   "consistent in modern S3. Examples: Amazon S3, GCS, Azure Blob, Ceph RGW, MinIO."),
                   ("Block Store",
                   "Single virtual disk attached to one host; full POSIX random read/write via the host "
                   "OS file system; replicated invisibly underneath; not a shared FS — single-attach "
                   "(mostly). Examples: AWS EBS, GCP Persistent Disk, Azure Managed Disk."),
                   ("Namespace",
                   "DFS: real hierarchical tree, atomic rename, directory ACLs. Object store: flat keys; "
                   "'/' is a UI convention; no atomic rename of large objects (it's a copy). Block "
                   "store: whatever FS the host OS lays on top — usually ext4 / xfs."),
                   ("Mutability",
                   "DFS: append + close-once + delete; no random writes. Object store: immutable "
                   "objects, replace whole object via PUT (or multipart for big ones); no append. Block "
                   "store: full random read/write, mmap, fcntl locks — full POSIX."),
                   ("Locality",
                   "DFS: explicit; the namenode tells the scheduler where bytes live; jobs run where the "
                   "data is. Object store: none; every read is a network call to the storage service. "
                   "Block store: locality is one host."),
                   ("When you'd pick each",
                   "DFS: on-prem analytics estate where compute and storage co-locate, sustained "
                   "throughput matters, append + hierarchical namespace are required. Object store: "
                   "cloud-native data lakes, archival, billions of small to huge immutable objects, "
                   "operability over locality. Block store: legacy single-host POSIX workloads — "
                   "databases, app servers, anything that fcntl-locks. Modern stacks routinely mix all "
                   "three."),
                   ("The cloud trend",
                   "Spark / Trino / Iceberg / Delta on S3 — analytics workloads moved from HDFS to "
                   "S3-backed lakes. The trade is: lose locality, gain durability + zero ops + infinite "
                   "scale. The performance gap shrinks because EC2 instances inside the same region "
                   "have fast network to S3, and columnar formats minimise per-request overhead. HDFS "
                   "is now a less-common choice for new builds, but its design lessons (large blocks, "
                   "append-only, separate metadata path) are foundational and reappear in newer systems "
                   "(Tectonic, JuiceFS) under modernised packaging."),
               ],
               diagram=(
                   "graph LR\n"
                   "  subgraph DFS[Distributed FS — HDFS / GFS]\n"
                   "    NS[Hierarchical namespace]\n"
                   "    L[Compute locality]\n"
                   "    A[Append-only big blocks]\n"
                   "  end\n"
                   "  subgraph OBJ[Object Store — S3 / GCS]\n"
                   "    K[Flat key->object]\n"
                   "    Sc[Effectively unlimited scale]\n"
                   "    NoL[No locality, REST per req]\n"
                   "  end\n"
                   "  subgraph BLK[Block Store — EBS / PD]\n"
                   "    SH[Single host attach]\n"
                   "    PX[Full POSIX R/W]\n"
                   "  end\n"
                   "  Use1[Analytics + locality] --> DFS\n"
                   "  Use2[Data lake / archive / billions of objects] --> OBJ\n"
                   "  Use3[Single-host POSIX / databases] --> BLK"
               )),
    ],
)
