"""SDQ — Design a Distributed Lock Service (Chubby/ZooKeeper-style).

A coordination service that issues mutually-exclusive, lease-bound locks across a
fleet of clients, plus the surrounding primitives (sessions, watches, fencing
tokens, ephemeral nodes) that make the locks safe to use as the foundation for
leader election, configuration, and queueing. Mirrors `sd_questions.SD_01`
shape via the `_q` / `_topic` helpers.
"""
from __future__ import annotations

from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design a Distributed Lock Service",
    "Hard",
    "Design a Chubby/ZooKeeper-style distributed lock service that lets thousands of clients coordinate "
    "mutual exclusion, leader election, configuration distribution, and lightweight queueing across a "
    "datacentre. The service exposes named locks with lease-bound ownership, hierarchical znode-style "
    "metadata, watch/notification on changes, and monotonically-increasing fencing tokens that allow "
    "downstream resources to safely reject zombie lock-holders. The cluster itself is a small "
    "(3- or 5-node) replicated state machine running Paxos/Raft, optimised for read-heavy coordination "
    "traffic with strong consistency, session-based client liveness, and graceful behaviour under "
    "partitions. The design must address the Redlock controversy — why a quorum-of-Redis approach is "
    "not safe without fencing — and articulate the lease/clock-skew assumptions on which any "
    "lock-with-TTL scheme depends.",
    hints=[
        "A lock without a fencing token is unsafe — a paused client may wake and overwrite a successor's work.",
        "Leases bound liveness, not safety; only monotonic tokens enforced at the resource provide safety.",
        "ZooKeeper-style ephemeral sequential nodes elegantly solve the herd problem for lock waiters.",
        "Use Paxos/Raft for the coordination layer itself — gossip is too weak for arbitration.",
        "Session ≠ TCP connection. A session survives reconnects; only the session timeout kills the lock.",
        "Read this design as 'a tiny CP database whose API is shaped for coordination' — not a queue, not a cache.",
        "Redlock is famous but flawed; senior signal is naming why (clock assumption + GC pause + no fencing).",
    ],
    constraints=[
        "Cluster of 3 or 5 voting nodes; latency matters but throughput is bounded by consensus, not hardware.",
        "Tens of thousands of concurrent clients per cluster; many holding long-lived sessions but few writes/sec.",
        "Read-heavy workload (config reads, watch fan-out) — typically 100:1 reads to writes.",
        "Lease durations 10s–60s; session timeouts 30s–120s; clock skew bounded by NTP (~ tens of ms).",
        "Write throughput intentionally modest: 1k–10k writes/sec aggregate per cluster (consensus-bound).",
        "p99 read latency < 10 ms intra-DC; p99 write latency dominated by quorum round-trip (~ 5–20 ms).",
        "Operators expect this service to outlive every other system and never lose committed state.",
    ],
    req_func=[
        "Create / delete named locks (znodes) in a hierarchical namespace.",
        "Acquire / release a lock with a TTL/lease; lock acquisition returns a monotonic fencing token.",
        "Try-acquire (non-blocking) and acquire-with-wait (blocking, herd-safe).",
        "Renew (heartbeat) a held lock to extend the lease before expiry.",
        "Sessions: clients establish a session, heartbeat to keep it alive; ephemeral state is tied to it.",
        "Ephemeral nodes: znodes/locks that auto-delete when the owning session expires.",
        "Sequential znodes: server appends a monotonic suffix on creation (basis for queue and herd-free locks).",
        "Watches: one-shot or persistent notifications when a znode's data, children, or existence change.",
        "Read znode data + children with optional 'sync' for strict linearisable reads.",
        "ACL / authentication on every operation (Kerberos, mTLS, or SASL).",
    ],
    req_nonfunc=[
        "Linearisable writes; consistent prefix reads with optional strict-linearisable read (sync barrier).",
        "Tolerate f node failures with 2f+1 cluster (3-node tolerates 1, 5-node tolerates 2).",
        "Availability 99.99% across rolling upgrades and single-node losses.",
        "Bounded session timeout: client clearly knows when it has lost its lock (no silent zombie holders).",
        "Watches: at-most-once delivery with monotonic ordering; lost watches replaced by full re-read.",
        "Write durability: every committed log entry fsynced on quorum before ACK.",
        "No silent split-brain: epoch / fencing tokens enforce single-writer semantics at the resource layer.",
    ],
    estimation={
        "cluster_size": "5 voting nodes (tolerate 2 failures) — typical large-deployment shape",
        "clients": "10k–100k concurrent sessions per cluster",
        "active_locks": "100k–1M znodes; 1k–10k of them currently held",
        "writes_per_sec": "1k–10k aggregate (acquire/release/renew/data writes)",
        "reads_per_sec": "100k+ (config reads, list children, watch fan-out)",
        "session_timeout": "30 s default, 10 s minimum, 5 min maximum",
        "lease_duration": "10–60 s typical; extended via session heartbeat",
        "log_retention": "Hours of write log + periodic snapshot; log truncated post-snapshot",
        "consensus_round_trip": "p50 ~ 2 ms intra-AZ; p99 ~ 10–20 ms cross-AZ",
    },
    endpoints=[
        {"method": "RPC", "path": "Session.Open(timeout, auth)",
         "description": "Establish session; returns session_id, leader hint, and granted timeout"},
        {"method": "RPC", "path": "Session.Heartbeat(session_id)",
         "description": "Renew session liveness; called every (timeout/3) by client library"},
        {"method": "RPC", "path": "Lock.Acquire(path, mode, session_id, blocking)",
         "description": "Acquire EXCLUSIVE or SHARED lock; returns {token: int64, version, lease_until}"},
        {"method": "RPC", "path": "Lock.Release(path, session_id)",
         "description": "Release lock; returns version of the resulting deletion"},
        {"method": "RPC", "path": "Znode.Create(path, data, flags, session_id)",
         "description": "Create node; flags = {EPHEMERAL, SEQUENTIAL, PERSISTENT}; SEQUENTIAL appends a monotonic suffix"},
        {"method": "RPC", "path": "Znode.Get(path, watch?)",
         "description": "Read data + stat; optional watch fires on next change"},
        {"method": "RPC", "path": "Znode.GetChildren(path, watch?)",
         "description": "List children; basis for ephemeral-sequential lock queue"},
        {"method": "RPC", "path": "Znode.Set(path, data, expected_version)",
         "description": "Conditional write; CAS on stat.version (optimistic concurrency)"},
        {"method": "RPC", "path": "Znode.Delete(path, expected_version)",
         "description": "Conditional delete on version"},
        {"method": "RPC", "path": "Sync(path)",
         "description": "Force this server to catch up to leader before next read — strict linearisability"},
        {"method": "RPC", "path": "Lease.Grant(ttl) / Lease.Keepalive(lease_id) / Lease.Revoke(lease_id)",
         "description": "etcd-style explicit lease objects — locks attach to a lease that can be revoked"},
    ],
    tables=[
        {"name": "log (replicated Raft/Paxos write-ahead log)",
         "columns": ["log_index BIGINT PK", "term BIGINT", "command BYTES",
                     "checksum BYTES", "committed BOOL", "ts_ms BIGINT"]},
        {"name": "snapshots (periodic state-machine snapshots)",
         "columns": ["snapshot_id VARCHAR(40) PK", "last_included_index BIGINT",
                     "last_included_term BIGINT", "size_bytes BIGINT", "checksum CHAR(64)"]},
        {"name": "znodes (in-memory state machine)",
         "columns": ["path VARCHAR(512) PK", "data BYTES", "version INT", "cversion INT",
                     "aversion INT", "ephemeral_owner_session VARCHAR(64) NULL",
                     "creation_id BIGINT (zxid)", "modification_id BIGINT (zxid)"]},
        {"name": "locks (logical view over znodes)",
         "columns": ["path VARCHAR(512) PK", "holder_session VARCHAR(64)", "fencing_token BIGINT",
                     "mode ENUM(EXCLUSIVE,SHARED)", "lease_until_ms BIGINT", "acquired_at_ms BIGINT"]},
        {"name": "sessions",
         "columns": ["session_id VARCHAR(64) PK", "client_addr VARCHAR(64)", "timeout_ms INT",
                     "last_heartbeat_ms BIGINT", "owned_ephemerals INT[]", "auth_principal VARCHAR(128)"]},
        {"name": "watches (in-memory per-server)",
         "columns": ["path VARCHAR(512)", "session_id VARCHAR(64)", "kind ENUM(DATA,CHILDREN,EXISTS)",
                     "kind_persistent BOOL", "registered_zxid BIGINT"]},
        {"name": "fencing_counter (monotonic per-lock)",
         "columns": ["path VARCHAR(512) PK", "next_token BIGINT"]},
    ],
    indexes=[
        "Primary znode tree: in-memory hash map keyed by path; secondary tree for prefix scans (children).",
        "Sessions indexed by session_id and by ephemeral-owner so session expiry can sweep all owned znodes.",
        "Watches indexed by (path, kind) for O(1) fan-out on znode change events.",
        "Log indexed by log_index; truncated past last_included_index of latest snapshot.",
        "fencing_counter is part of the replicated state machine; updated atomically inside the Acquire command.",
    ],
    hld_desc=(
        "A small, replicated state machine. 3 or 5 voting nodes run Raft (or Multi-Paxos / Zab), with one "
        "elected leader who serialises all writes. Clients connect to any node; reads can be served locally "
        "for performance, but a `sync` barrier is required before a read if strict linearisability is "
        "needed. Writes are forwarded to the leader, appended to the replicated log, fsynced and acked by a "
        "quorum, and only then applied to the in-memory state machine (the znode tree). Snapshots and log "
        "truncation keep recovery time bounded. Clients hold long-lived sessions, heartbeating periodically; "
        "the cluster reaps any session that misses its timeout, and that reap deletes every ephemeral znode "
        "owned by the session — which is how locks are released on client failure. Each lock acquisition "
        "returns a monotonically-increasing fencing token; downstream resources (databases, blob stores) "
        "compare tokens on writes and reject any operation tagged with a stale token, so a paused or "
        "GC-stalled client cannot corrupt state after its lease has expired and a successor has taken "
        "over. Watches piggy-back on each connection: the leader (or local replica, for committed state) "
        "fans out change notifications to subscribed sessions."
    ),
    hld_components=[
        {"name": "Client Library / SDK", "role": "Session, heartbeat, watches, lock recipe (ephemeral-sequential)"},
        {"name": "Connection Front End", "role": "TCP/TLS termination, session affinity, RPC framing"},
        {"name": "Consensus Module (Raft/Paxos)", "role": "Leader election, log replication, fsync quorum"},
        {"name": "State Machine (znode tree)", "role": "Apply committed log entries; strong-read snapshot"},
        {"name": "Session Manager", "role": "Track sessions, heartbeats, expire on timeout, sweep ephemerals"},
        {"name": "Watch Manager", "role": "Per-path watch lists; fire on apply; deliver in-order"},
        {"name": "Fencing Token Allocator", "role": "Monotonic per-lock counter inside the state machine"},
        {"name": "Snapshot / Log Truncation", "role": "Periodic snapshot, GC of old log entries"},
        {"name": "Failure Detector", "role": "Heartbeat between peers; trigger leader election"},
        {"name": "Admin / Reconfig", "role": "Joint-consensus member changes; rolling upgrades"},
    ],
    detailed_design={
        "consensus_choice": (
            "The coordination layer must be CP, not AP — a partition that returned 'still your lock' to two "
            "clients on opposite sides would defeat the entire point of the service. Raft is the modern "
            "default (clear paper, well-understood, easy to operate). Multi-Paxos works but is harder to "
            "implement correctly. Zab (ZooKeeper's protocol) is essentially Raft-like with FIFO client "
            "ordering. Pick Raft for new designs. The cluster is intentionally small (3 or 5 voters); "
            "more voters slow every write because every commit waits for a quorum, and the read path "
            "saturates well before the write path. Witness/learner nodes can scale read capacity without "
            "increasing the quorum size."
        ),
        "leader_election": (
            "Raft randomised-timeout election: each follower starts a per-term timer (150–300 ms with "
            "jitter); the first to time out becomes a candidate, requests votes, and on receiving a "
            "majority becomes leader for that term. Term numbers are monotonic across the cluster — they "
            "are themselves the cluster-level fencing token: any RPC tagged with a stale term is rejected, "
            "preventing two leaders from committing concurrently. Leadership lease (a leader-stickiness "
            "optimisation) lets the leader serve linearisable reads without a round-trip, by holding a "
            "time-bounded promise from followers; it depends on bounded clock drift, so NTP discipline is "
            "operationally required."
        ),
        "mutual_exclusion": (
            "A lock at path /locks/foo is just a znode with EXCLUSIVE semantics: at most one session may "
            "hold it. Acquire serialises through the leader's log, so the linearisability of the lock is "
            "the linearisability of consensus — there is no race. The held lock is encoded as an EPHEMERAL "
            "child under the lock path, owned by the holding session; release is either explicit (delete) "
            "or implicit (session expires, ephemeral is reaped). Crucially, mutual exclusion in the "
            "coordination service is not the same as mutual exclusion at the protected resource — that "
            "requires fencing tokens (below)."
        ),
        "lease_semantics_with_ttl": (
            "A held lock is bounded in real time by the session timeout: if the holder stops heartbeating, "
            "the cluster reaps the session (and thus the lock) after `session_timeout`. This bounds "
            "liveness — the system makes progress even if a client dies — but it does NOT bound safety: "
            "the holder may be alive, GC-paused, or network-partitioned for longer than the timeout, in "
            "which case the cluster declares it dead and hands the lock to a successor while the original "
            "holder still believes it owns the lock. Without an additional mechanism (fencing tokens), "
            "the original holder's next write to the protected resource will corrupt successor state. "
            "Therefore: leases bound liveness, never safety. Always pair with fencing."
        ),
        "fencing_tokens_critical_safety": (
            "Each successful Acquire returns a fencing_token: a strictly monotonically-increasing int64 "
            "that the lock service guarantees never to repeat or move backward, ever. The lock holder is "
            "expected to attach this token to every write it makes against the resource the lock is "
            "protecting. The resource (a database row, a blob store, a coordinator API) records the "
            "highest token it has ever seen and rejects any write whose token is ≤ stored. Why this is "
            "essential: if process A acquires the lock with token=42, GC-pauses for 90s, the cluster "
            "expires its session at 60s and grants the lock to B with token=43, and B writes the resource "
            "with token=43, then A wakes up and tries to write with token=42 — the resource sees 42 < 43 "
            "and rejects A's write. Without tokens, A's write silently overwrites B's. This is THE safety "
            "property; everything else is plumbing. Source: Martin Kleppmann, 'How to do distributed "
            "locking' (2016)."
        ),
        "redlock_controversy": (
            "Redlock (Antirez, 2016) proposes acquiring a lock by talking to N independent Redis instances "
            "and considering the lock held if a quorum responds OK within a time window. Martin Kleppmann's "
            "critique (2016) argues this is unsafe because (1) it depends on bounded clock drift across "
            "the Redis nodes — if any node's clock jumps forward (NTP correction, VM migration, leap "
            "second), it may wrongly believe a lease has expired and grant the lock to a second client; "
            "(2) it depends on bounded GC pauses in clients — same failure mode as any TTL lock, with no "
            "fencing token to make safety independent of timing; (3) the algorithm has no notion of a "
            "monotonic token at all, so a delayed message from a previous owner is indistinguishable from "
            "a current owner's message at the protected resource. Antirez's rebuttal accepts that fencing "
            "tokens are necessary for resources that need them, but argues many use-cases (efficiency "
            "locks, where double-execution is wasteful but not incorrect) are fine without. The senior "
            "framing: Redlock is a fine efficiency lock; it is not a correctness lock; do not use it where "
            "double-execution corrupts state, and prefer ZK/etcd/Chubby (consensus-based) when you need "
            "real safety."
        ),
        "zookeeper_ephemeral_pattern": (
            "The canonical ZooKeeper recipe for a lock at /lock/foo: (1) the client creates an EPHEMERAL "
            "SEQUENTIAL child, e.g. /lock/foo/lock-0000000007, owned by its session; (2) it lists children "
            "of /lock/foo and finds the lowest-numbered child; (3) if its own child is the lowest, it "
            "holds the lock; otherwise it sets a watch on the immediately-lower-numbered child (only that "
            "one — not on the parent), and waits. When that child is deleted (its holder released or its "
            "session died), the watch fires and the client re-evaluates. This solves the herd problem "
            "(only one waiter is woken per release, not all of them), and it composes with sessions: if "
            "the lock-holder dies, its ephemeral disappears and the next waiter is woken automatically. "
            "Read-write locks are the same recipe with two prefixes (read- / write-) and slightly "
            "different ordering rules. This pattern is so good it has been ported almost verbatim to "
            "every consensus-backed coordination service since."
        ),
        "etcd_lease_revisions": (
            "etcd takes a slightly different shape: rather than ephemerals, it has explicit Lease objects "
            "with a TTL. A Put can be tagged with a lease, and when the lease expires (or is revoked), all "
            "keys attached to it are deleted atomically. Locks are built as Put-if-not-exists on a key "
            "tagged with the client's lease. etcd assigns every cluster mutation a monotonic global "
            "revision (mod_revision); the revision of the lock-holder's Put becomes the natural fencing "
            "token. Watches are revision-aware: clients can watch from a specific revision and never miss "
            "an event between a Get and a Watch. The two designs (znode ephemerals vs explicit leases) "
            "are isomorphic — same primitives wearing different clothes — but etcd's revision exposes "
            "the fencing token explicitly, whereas in ZK the holder reads stat.czxid as its token."
        ),
        "lock_as_building_block": (
            "Once you have a fencing-safe distributed lock + ephemeral nodes + watches, an enormous amount "
            "of distributed-systems machinery falls out for free. (1) Leader election: every candidate "
            "creates an ephemeral-sequential under /election/role; the lowest-numbered child is leader; "
            "watch the predecessor to handle leader failover. (2) Service discovery: services register "
            "ephemeral znodes under /services/<name>; clients GetChildren+watch to learn membership. "
            "(3) Distributed configuration: write config under /config/<key>; clients watch and reload on "
            "change. (4) Distributed queues: producers create sequential children, consumers acquire the "
            "lowest one (with care — true work-queue semantics need additional ack/retry). (5) Barriers "
            "and latches: synchronize N participants via znode counts. The lock service is the kernel; "
            "everything else is library code on top of it."
        ),
        "client_failure_handling": (
            "Failure modes the client library must handle. (1) Lock holder dies: session expires, "
            "ephemeral is reaped, successor's watch fires — fully automatic, ~ session_timeout latency. "
            "(2) Lock holder GC-pauses past its lease: cluster grants the lock to a successor; original "
            "holder must NOT continue writing — the client library must re-check session validity before "
            "every protected operation, and the resource layer must enforce fencing as the safety "
            "backstop. (3) Lock holder partitioned from cluster but still running: same as GC pause; the "
            "library detects session loss on reconnect and surfaces a SessionExpiredException; the "
            "application MUST treat this as 'I have lost the lock, even if I think I haven't' and stop. "
            "(4) Lock holder is the cluster leader (etcd lease auto-renew failure, Raft term change): "
            "library exposes a session-state callback so the application can pause work proactively."
        ),
        "session_reconnection": (
            "A session is decoupled from any single TCP connection. The client library maintains a "
            "session_id and the timeout granted at Session.Open; if the underlying connection drops, the "
            "library reconnects to any cluster member and presents the session_id. As long as the cluster "
            "has not yet expired the session (the reconnection happens within `session_timeout`), the "
            "session — and all ephemeral nodes / locks — remain valid. If reconnection takes too long, "
            "the cluster expires the session, ephemerals are reaped, and the next client RPC fails with "
            "SessionExpired. There is a subtle pitfall: the client must compute a 'negotiated' timeout "
            "that's slightly less than the cluster's, so it gives up locally before the cluster gives up "
            "on it — otherwise the client may believe it still holds locks that the cluster has already "
            "released. The standard recipe is: heartbeat every timeout/3, declare local-loss at "
            "timeout × 2/3, treat any reconnect failure past that as a hard SessionExpired."
        ),
        "watch_notification_api": (
            "Watches are one-shot or persistent server-side triggers attached to a path. ZooKeeper's "
            "classic API is one-shot: watch fires once and is rearmed by the client on next read. etcd "
            "and modern ZK support persistent / recursive watches that survive event delivery. Important "
            "guarantees: (a) ordering — watches fire in the same order as the underlying commits, so a "
            "client's view of a path is always a consistent prefix; (b) at-most-once delivery — if the "
            "client is disconnected when the event fires, the watch is lost (in the one-shot model), and "
            "the client MUST re-read the znode on reconnect to resync; (c) watches are local to a server, "
            "but committed state is global — so a watch fires only after the leader has committed the "
            "change and that server has applied it. The herd-free lock recipe relies on watch ordering: "
            "watching the immediate predecessor ensures exactly one waiter is woken per release. etcd's "
            "revision-keyed watches improve on this by letting a reconnecting client say 'replay events "
            "from revision R' so no events are missed."
        ),
        "split_brain_prevention": (
            "Three layers. (1) Within the coordination cluster: Raft term numbers are themselves epoch "
            "fences — a stale leader's AppendEntries are rejected by followers carrying a higher term. "
            "(2) Between cluster and clients: session epoch carried in every RPC; a session reincarnated "
            "after expiry has a fresh epoch, and the cluster rejects late RPCs from the dead epoch. "
            "(3) Between client and the protected resource: monotonic fencing tokens. The three together "
            "make split-brain at the resource impossible even in the presence of arbitrary GC pauses, "
            "network partitions, and clock drift, provided fencing is actually enforced at the resource "
            "(which is the application author's responsibility — the lock service can hand out tokens but "
            "cannot make the database check them)."
        ),
        "scalability_limits": (
            "This system is intentionally NOT scale-out. Every write goes through one leader and waits "
            "for a quorum fsync; the write throughput is bounded by single-leader CPU and quorum "
            "round-trip, typically 1k–10k writes/sec on commodity hardware. Reads can scale linearly via "
            "follower reads (with optional sync barrier for linearisability). When a workload outgrows "
            "the cluster, the answer is sharding — multiple independent coordination clusters, each "
            "serving a subtree of the namespace — not making one cluster bigger. Big clusters (9, 11 "
            "voters) are slower and less available than small ones, because every commit waits for a "
            "majority and the probability of a majority being healthy decreases with cluster size."
        ),
        "slo_contract": (
            "Read p50 < 2 ms, p99 < 10 ms intra-DC (follower reads, no sync). "
            "Strong read p99 < 20 ms (sync barrier). "
            "Write p99 < 20 ms (quorum fsync). "
            "Lock acquire (uncontended) p99 < 25 ms. "
            "Session expiry detection: bounded by session_timeout (typically 30 s). "
            "Availability 99.99% on a 5-node cluster across rolling upgrades. "
            "Zero committed data loss; every committed log entry is fsynced on a quorum."
        ),
    },
    trade_offs=[
        {"option": "Lock TTL only vs Lock TTL + fencing tokens",
         "for_ttl_only": "Simpler API; works fine for efficiency locks (double-execution wasteful but safe)",
         "for_fencing": "Real safety — survives GC pauses, partitions, clock drift",
         "recommendation": "Always issue fencing tokens. Apps that don't need them can ignore them; apps that do need them have no alternative."},
        {"option": "Consensus-based (Chubby/ZK/etcd) vs Redlock-style quorum",
         "for_consensus": "True linearisability, monotonic tokens, formally analysed",
         "for_redlock": "Reuses existing Redis; lower ops complexity for small teams",
         "recommendation": "Consensus for correctness locks; Redlock acceptable only for efficiency locks where double-execution is tolerable."},
        {"option": "Ephemeral-sequential watch (ZK style) vs Lease + key (etcd style)",
         "for_zk": "Composable recipe; no explicit lease object to manage; herd-free by construction",
         "for_etcd": "Explicit lease lifecycle; clearer mental model; revision == fencing token natively",
         "recommendation": "Functionally equivalent. Pick by ecosystem fit; both solve the same problem with the same guarantees."},
        {"option": "Local follower reads vs leader-only reads",
         "for_follower": "Scales reads linearly with cluster size; lower latency",
         "for_leader": "Always linearisable without a sync barrier; simpler reasoning",
         "recommendation": "Follower reads with explicit sync(path) for the (rare) cases needing strict linearisability — best of both."},
        {"option": "Short session timeout vs long session timeout",
         "for_short": "Fast lock recovery on client death; less zombie-holder window",
         "for_long": "Survives transient network blips and GC pauses without losing locks",
         "recommendation": "30 s default. Tune up for clients with long GCs (JVMs); tune down for fast-failover workloads. Always pair with fencing — timeout choice is liveness, not safety."},
        {"option": "3-node cluster vs 5-node cluster",
         "for_3": "Faster writes (smaller quorum), simpler ops, lower cost",
         "for_5": "Tolerates 2 simultaneous failures (rolling-upgrade-safe), better availability",
         "recommendation": "5-node for production. 3-node for dev/test or strictly cost-bounded deployments. Avoid 7+ — diminishing returns and worse write latency."},
    ],
    tips=[
        "Lead with 'leases bound liveness, fencing tokens bound safety' — interviewers wait for this distinction.",
        "Naming the Kleppmann/Antirez Redlock debate explicitly is a senior signal; don't just say 'Redlock is bad'.",
        "ZK ephemeral-sequential is the canonical lock recipe; if you draw it, draw the predecessor-watch (not parent-watch).",
        "Don't forget the resource side: the lock service issues tokens; the database/blob-store enforces them. Both halves required.",
        "Distinguish session_timeout (liveness boundary) from lease_duration (held-lock boundary) — they're separate knobs.",
        "Volunteer the scalability ceiling: this is a tiny CP system, sharded namespaces are the scale-out path, not bigger clusters.",
        "When the interviewer says 'just use Redis SETNX', describe the GC-pause failure and the missing fencing token — this is THE classic question.",
    ],
    thought_process=[
        "1. Clarify: coordination service for mutual exclusion, leader election, config; CP not AP.",
        "2. Estimate: 5-node cluster, 100k clients, 1k–10k writes/sec, 100k reads/sec, 30s session TTL.",
        "3. APIs: Session, Acquire/Release, Znode CRUD, Watch, Lease — shaped like ZK or etcd.",
        "4. Consensus: Raft (modern default); 5 voters; leader serialises writes.",
        "5. State machine: in-memory hierarchical znode tree; ephemeral nodes tied to sessions.",
        "6. Sessions: heartbeat-driven; ephemerals reaped on expiry; reconnect transparent if within TTL.",
        "7. Lock recipe: ephemeral-sequential + watch immediate predecessor → herd-free.",
        "8. Fencing tokens: monotonic per-lock counter; resource layer compares and rejects stale.",
        "9. Redlock: name the controversy — clock + GC + no fencing → unsafe for correctness locks.",
        "10. Watches: in-order, at-most-once; revision-keyed in etcd; clients re-read on reconnect.",
        "11. Building blocks on top: leader election, service discovery, config, queues, barriers.",
        "12. Scale-out: sharded namespaces, not bigger clusters. Reads scale; writes don't.",
    ],
    tags=["distributed-locks", "coordination", "consensus", "raft", "zookeeper", "etcd",
          "fencing-tokens", "leader-election", "linearisability"],
    arch_nodes=[
        {"id": "client", "label": "Client + SDK", "type": "client"},
        {"id": "lb", "label": "Front-end Routing", "type": "lb"},
        {"id": "leader", "label": "Raft Leader", "type": "server"},
        {"id": "follower1", "label": "Follower 1", "type": "server"},
        {"id": "follower2", "label": "Follower 2", "type": "server"},
        {"id": "log", "label": "Replicated Log (fsync)", "type": "database"},
        {"id": "snap", "label": "Snapshots", "type": "database"},
        {"id": "sm", "label": "State Machine (znodes)", "type": "service"},
        {"id": "sess", "label": "Session Manager", "type": "service"},
        {"id": "watch", "label": "Watch Manager", "type": "service"},
        {"id": "fence", "label": "Fencing Token Allocator", "type": "service"},
        {"id": "resource", "label": "Protected Resource (DB / Blob)", "type": "database"},
    ],
    arch_edges=[
        {"source": "client", "target": "lb", "label": "RPC"},
        {"source": "lb", "target": "leader", "label": "writes"},
        {"source": "lb", "target": "follower1", "label": "reads (+ sync)"},
        {"source": "lb", "target": "follower2", "label": "reads (+ sync)"},
        {"source": "leader", "target": "log", "label": "append + fsync"},
        {"source": "leader", "target": "follower1", "label": "AppendEntries (quorum)"},
        {"source": "leader", "target": "follower2", "label": "AppendEntries (quorum)"},
        {"source": "log", "target": "sm", "label": "apply on commit"},
        {"source": "sm", "target": "snap", "label": "periodic snapshot"},
        {"source": "sm", "target": "sess", "label": "ephemeral lifecycle"},
        {"source": "sm", "target": "watch", "label": "fire on apply"},
        {"source": "sm", "target": "fence", "label": "monotonic alloc"},
        {"source": "watch", "target": "client", "label": "notifications"},
        {"source": "client", "target": "resource", "label": "write(token)"},
        {"source": "resource", "target": "fence", "label": "compare & reject stale"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant A as Client A\n"
        "  participant B as Client B\n"
        "  participant L as Raft Leader\n"
        "  participant Q as Quorum\n"
        "  participant R as Resource\n"
        "  A->>L: Session.Open(timeout=30s)\n"
        "  L->>Q: replicate session\n"
        "  Q-->>L: ack\n"
        "  L-->>A: session_id=S1\n"
        "  A->>L: Lock.Acquire(/locks/foo, S1)\n"
        "  L->>L: assign fencing_token=42\n"
        "  L->>Q: replicate (create ephemeral, token=42)\n"
        "  Q-->>L: ack\n"
        "  L-->>A: held, token=42\n"
        "  Note over A: GC pause 90s\n"
        "  L->>L: session S1 expired (no heartbeat)\n"
        "  L->>L: reap ephemeral; release lock\n"
        "  B->>L: Lock.Acquire(/locks/foo, S2)\n"
        "  L->>L: assign fencing_token=43\n"
        "  L->>Q: replicate\n"
        "  L-->>B: held, token=43\n"
        "  B->>R: write(token=43)\n"
        "  R->>R: store max_token=43\n"
        "  R-->>B: ok\n"
        "  Note over A: A wakes up\n"
        "  A->>R: write(token=42)\n"
        "  R->>R: 42 < 43 → reject\n"
        "  R-->>A: FENCED — session lost"
    ),
    er_diagram=(
        "erDiagram\n"
        "  CLUSTER ||--|{ NODE : has\n"
        "  NODE ||--|| LOG : owns\n"
        "  NODE ||--|| SNAPSHOT : keeps\n"
        "  CLUSTER ||--|| STATE_MACHINE : applies\n"
        "  STATE_MACHINE ||--o{ ZNODE : holds\n"
        "  ZNODE ||--o| EPHEMERAL_OWNER : tied_to\n"
        "  SESSION ||--o{ EPHEMERAL_OWNER : owns\n"
        "  SESSION ||--o{ WATCH : registers\n"
        "  ZNODE ||--o| WATCH : fires\n"
        "  LOCK ||--|| ZNODE : implemented_as\n"
        "  LOCK ||--|| FENCING_TOKEN : issues\n"
        "  RESOURCE ||--|| FENCING_TOKEN : compares"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B[Coordination service: CP not AP]\n"
        "  B --> C[Consensus: Raft, 5 voters]\n"
        "  C --> D[State machine: znode tree]\n"
        "  D --> E[Sessions + ephemerals]\n"
        "  E --> F[Lock = ephemeral-sequential]\n"
        "  F --> G{Safety needed?}\n"
        "  G -->|yes| H[Issue fencing tokens]\n"
        "  G -->|efficiency only| I[TTL alone may suffice]\n"
        "  H --> J[Resource enforces token]\n"
        "  F --> K[Watch predecessor → herd-free]\n"
        "  E --> L[Session reconnect within TTL]\n"
        "  C --> M[Term# = cluster epoch fence]\n"
        "  H --> N[Lock + fencing → leader election, config, queues]"
    ),
    tradeoff_title="Lock Safety: TTL Alone vs TTL + Fencing Tokens vs Consensus + Fencing",
    tradeoff_options=[
        {"label": "Pure TTL lock (Redis SETNX EX)",
         "description": "Acquire = SETNX with TTL. Renew with EXPIRE. Release with DEL. No token.",
         "pros": ["Trivial to implement", "No new infrastructure",
                 "Fine for efficiency locks (deduplicate cron, dedupe work)"],
         "cons": ["Unsafe under GC pause / VM stall / partition",
                 "No fencing — late writes from prior holder corrupt state",
                 "Single-Redis = single point of failure; Redis replication is async (lossy)",
                 "Clock drift breaks the lease assumption"]},
        {"label": "Quorum-of-Redis (Redlock)",
         "description": "Acquire from N independent Redis with TTL; held if quorum acks within window.",
         "pros": ["No single Redis SPOF", "Reuses existing infra",
                 "Better than single-Redis for efficiency locks"],
         "cons": ["Still depends on bounded clock drift across all N",
                 "Still no fencing token — Kleppmann's main critique",
                 "Quorum failure modes are subtle (clock jump → second grant)",
                 "Not a correctness lock; do not use where double-execution corrupts"]},
        {"label": "Consensus + fencing (Chubby / ZooKeeper / etcd)",
         "description": "Replicated state machine via Raft/Paxos; lock is an ephemeral znode; "
                        "every Acquire returns a strictly monotonic fencing token.",
         "pros": ["Linearisable lock state across the cluster",
                 "Survives GC pause, partition, clock drift safely",
                 "Monotonic token at the resource layer is the safety backstop",
                 "Composes into leader election, config, service discovery"],
         "cons": ["Higher operational overhead (consensus cluster to run)",
                 "Write throughput bounded by quorum fsync (~ 1k–10k/sec)",
                 "Resource side must actually enforce the token (app author's responsibility)",
                 "Cluster availability bounded by quorum health"]},
    ],
    tradeoff_rec=(
        "Default to consensus + fencing tokens for any lock that protects state where double-execution "
        "would be incorrect. Use pure TTL locks (or Redlock) only for efficiency locks where double "
        "execution is wasteful but safe. The senior framing: 'leases bound liveness; only fencing tokens "
        "bound safety' — choose your locking primitive on whether the resource you're protecting cares "
        "about safety or only efficiency, and make sure the resource layer actually checks the token. "
        "ZooKeeper-style ephemeral-sequential is the canonical recipe; etcd's lease + revision is "
        "isomorphic; Chubby's lease + sequencer was the original. All three are correct; pick by "
        "ecosystem fit."
    ),
    senior_topics=[
        _topic("fencing-tokens",
               "Fencing Tokens: The Only Safe Way to Use a Distributed Lock",
               "A monotonically-increasing token is the missing piece that makes lock-with-TTL safe under "
               "arbitrary client failure. Without it, any TTL-based lock is unsafe; with it, even a "
               "pathologically delayed client cannot corrupt successor state.",
               [
                   ("The unsafe scenario",
                    "Client A acquires lock with TTL=30s. A's process GC-pauses for 60s. The lock service, "
                    "seeing no heartbeat, releases the lock and grants it to client B. B does its work and "
                    "commits to the database. A wakes up, still believing it holds the lock, and writes "
                    "to the database — overwriting B's work. The lock service did everything correctly; "
                    "the failure is at the resource boundary, where the database had no way to tell A's "
                    "stale write from a current one."),
                   ("The fix",
                    "On every successful Acquire, the lock service returns a strictly monotonically "
                    "increasing int64 — the fencing token. The token is replicated through consensus, so "
                    "it is globally unique and globally ordered. The lock holder attaches this token to "
                    "every write against the resource. The resource records the highest token it has ever "
                    "accepted and rejects any write with token ≤ stored. In the scenario above, B would "
                    "have written with token=43 and stored max_token=43; A's late write with token=42 is "
                    "rejected (42 < 43). Safety is restored, independent of how long A was paused."),
                   ("Why this is THE safety property",
                    "Every other mechanism in the lock service (leases, sessions, heartbeats, ephemerals) "
                    "is about liveness — bounding how long a dead client's lock takes to be reclaimed. "
                    "Only the fencing token is about safety — preventing two clients from both believing "
                    "they hold the lock from corrupting state. They are orthogonal properties. You need "
                    "both: liveness so the system makes progress when clients fail; safety so failure "
                    "cannot cause corruption."),
                   ("Where the token comes from",
                    "ZooKeeper: stat.czxid (zxid of the create) is naturally monotonic per session, but "
                    "for a per-lock token you typically use a separate counter znode incremented in the "
                    "Acquire transaction. etcd: mod_revision of the lock-holder's Put is the token "
                    "directly — etcd revisions are globally monotonic by construction. Chubby: explicit "
                    "'sequencer' returned from Acquire — Chubby was the system that named the pattern."),
                   ("Application responsibility",
                    "The lock service can mint tokens; it cannot enforce them. The application must (a) "
                    "pass the token through to every protected operation; (b) the resource must compare "
                    "and reject. Common idioms: a token column in the protected row with a `WHERE "
                    "token <= ?` reject; a conditional Put in a key-value store with a token-prefixed "
                    "version; an HMAC over the token in API calls. If the resource layer doesn't check, "
                    "the lock is back to TTL-only safety guarantees."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant A\n  participant L as Lock Service\n  participant DB\n  participant B\n"
                   "  A->>L: Acquire\n"
                   "  L-->>A: token=42\n"
                   "  Note over A: GC pause 60s\n"
                   "  L->>L: A's session expires\n"
                   "  B->>L: Acquire\n"
                   "  L-->>B: token=43\n"
                   "  B->>DB: write(token=43)\n"
                   "  DB->>DB: store max_token=43\n"
                   "  DB-->>B: ok\n"
                   "  Note over A: A wakes up\n"
                   "  A->>DB: write(token=42)\n"
                   "  DB->>DB: 42 < 43 — reject\n"
                   "  DB-->>A: FENCED"
               ),
               sources=["Martin Kleppmann, 'How to do distributed locking' (2016)",
                       "Mike Burrows, 'The Chubby lock service for loosely-coupled distributed systems' (OSDI 2006)"]),
        _topic("redlock-controversy",
               "The Redlock Controversy: Kleppmann vs Antirez",
               "A 2016 debate about whether Redlock — a quorum-of-Redis distributed lock algorithm — is "
               "safe. Understanding both sides is the senior signal because it crystallises what 'safe' "
               "actually means for a distributed lock.",
               [
                   ("What Redlock proposes",
                    "To acquire a lock, the client sends SET NX EX with the same lock_id and TTL to N "
                    "(typically 5) independent Redis instances. The lock is considered held if a quorum "
                    "(3 of 5) ack within a configurable time budget AND the elapsed real time is less "
                    "than the TTL minus a safety margin. To release, the client deletes the key on every "
                    "instance. The intent is to remove the single-Redis SPOF while preserving Redis' "
                    "speed."),
                   ("Kleppmann's safety critique",
                    "(1) Redlock depends on bounded clock drift across the N Redis instances. If any "
                    "instance's clock jumps forward (NTP correction, leap second, VM live-migration), it "
                    "may believe a lease has expired earlier than it should and grant the lock to a "
                    "second client while the first still believes it holds it. (2) Redlock has no notion "
                    "of a fencing token — even ignoring clocks, a GC-paused or partitioned client wakes "
                    "and writes with no way for the resource to distinguish stale from current. (3) These "
                    "are not 'edge cases'; they are the reasons we use distributed locks in the first "
                    "place. A lock that doesn't survive these scenarios isn't a safety lock."),
                   ("Antirez's response",
                    "Concedes that fencing tokens are required for resources that need them, but argues "
                    "many production use-cases are 'efficiency locks' — where double-execution is "
                    "wasteful but not incorrect (e.g. preventing two cron-runs of an idempotent batch). "
                    "For those, Redlock is fine. He also argues the clock-drift assumption is operationally "
                    "manageable in practice with disciplined NTP. The implicit pushback: insisting on "
                    "consensus + fencing for every coordination problem is over-engineering when the "
                    "underlying work is idempotent."),
                   ("Who is right",
                    "Both, partially. Kleppmann is right that Redlock cannot provide correctness "
                    "guarantees against arbitrary delay; Antirez is right that not every lock needs to. "
                    "The mature framing: classify your lock as efficiency vs correctness. If "
                    "double-execution is wasteful but produces a correct outcome (idempotent work, "
                    "deduplicating notifications, coordinating cache rebuilds), Redlock is acceptable. "
                    "If double-execution corrupts state (transferring money, advancing a workflow, "
                    "leasing a unique resource), use a consensus-based lock service AND fencing tokens. "
                    "Naming the distinction explicitly is the senior signal."),
                   ("What this means in interviews",
                    "When asked 'design a distributed lock', the wrong answer is 'just use Redis SETNX'. "
                    "The right answer cites the controversy, distinguishes efficiency locks from "
                    "correctness locks, and reaches for ZooKeeper / etcd / Chubby + fencing tokens for "
                    "the latter. Bonus points for noting that even with consensus, the resource layer "
                    "must check the token — the lock service alone is not enough."),
               ],
               diagram=(
                   "graph TD\n"
                   "  Q[Question: is Redlock safe?] --> E{Efficiency or correctness lock?}\n"
                   "  E -->|Efficiency| OK[Redlock acceptable; double-exec is wasteful but safe]\n"
                   "  E -->|Correctness| F{Fencing tokens?}\n"
                   "  F -->|No tokens| BAD[Unsafe: clock drift / GC pause → corrupt state]\n"
                   "  F -->|Tokens enforced at resource| SAFE[Use consensus + fencing — ZK/etcd/Chubby]\n"
                   "  OK --> N[Document the assumption: idempotent work]\n"
                   "  SAFE --> R[Resource must check token]"
               ),
               sources=["Martin Kleppmann, 'How to do distributed locking' (2016)",
                       "Salvatore Sanfilippo, 'Is Redlock safe?' (2016 response)",
                       "https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html"]),
        _topic("zk-ephemeral-sequential",
               "ZooKeeper Ephemeral-Sequential Lock Recipe",
               "The canonical herd-free distributed lock pattern, used (often unmodified) by Curator, "
               "Helix, Kafka controllers, HBase, and dozens of other systems. Worth understanding deeply: "
               "the pattern's elegance is in what it doesn't do.",
               [
                   ("The recipe, step by step",
                    "(1) Client wishing to acquire /locks/foo creates a child znode at "
                    "/locks/foo/lock- with flags EPHEMERAL+SEQUENTIAL. The server appends a monotonic "
                    "10-digit suffix, e.g. /locks/foo/lock-0000000007. Because EPHEMERAL, this znode is "
                    "tied to the client's session — when the session expires (client crash, partition "
                    "past timeout), the znode is deleted automatically. (2) Client lists children of "
                    "/locks/foo and finds them sorted by suffix. (3) If the client's own child is the "
                    "lowest, it holds the lock and proceeds. (4) Otherwise, it sets a watch on the "
                    "immediately-preceding child only — NOT the parent. (5) When that watch fires, the "
                    "client re-lists, re-evaluates, and either holds the lock or watches the new "
                    "predecessor."),
                   ("Why predecessor-watch (not parent-watch)",
                    "If every waiter watched the parent, a single release would wake all N waiters "
                    "simultaneously — the herd problem — and N-1 of them would immediately re-list and "
                    "go back to sleep. With predecessor-watch, only the next-in-line waiter is woken on "
                    "release. O(1) wakeups per release instead of O(N). For 10k waiters, this is the "
                    "difference between a clean handover and a coordination storm."),
                   ("Why ephemeral",
                    "If the lock holder dies (crash, partition, GC past timeout), its session expires, "
                    "the ephemeral znode is reaped, and the next waiter's watch fires — fully automatic "
                    "lock release on client failure. Without ephemerals, you'd need a separate liveness "
                    "mechanism on top of the lock; with them, liveness is built into the storage model."),
                   ("Why sequential",
                    "The monotonic suffix is the queue position. Waiters know exactly who is ahead of "
                    "them, can reason about expected wait time, and can reliably watch only their "
                    "predecessor. Without sequential numbering, you'd need a separate notion of order "
                    "(timestamp, transaction ID) and the predecessor lookup becomes ambiguous."),
                   ("Read-write variant",
                    "For shared/exclusive locks, use two prefixes — /locks/foo/read- and "
                    "/locks/foo/write-. A read-lock waiter's predecessor is the lowest write-lock with a "
                    "smaller suffix; a write-lock waiter's predecessor is whichever (read or write) has "
                    "the highest suffix smaller than its own. Slightly more bookkeeping, same elegance."),
                   ("Producing the fencing token",
                    "The natural fencing token here is the SEQUENTIAL suffix itself — it's globally "
                    "monotonic per parent path because it is assigned by the leader inside the same "
                    "consensus log entry that creates the znode. Pass that suffix through to the "
                    "protected resource as the token. Some implementations also use stat.czxid (the "
                    "global zxid of the create) as a stronger globally-monotonic token across all paths."),
               ],
               diagram=(
                   "graph TD\n"
                   "  Acquire[client creates lock-NNNNNNNNNN] --> List[GetChildren]\n"
                   "  List --> Cmp{my suffix lowest?}\n"
                   "  Cmp -->|yes| Hold[hold lock]\n"
                   "  Cmp -->|no| Watch[set watch on predecessor]\n"
                   "  Watch --> Wait[block]\n"
                   "  Wait --> Fired[predecessor deleted]\n"
                   "  Fired --> List\n"
                   "  Hold --> Done[do work; delete own znode to release]\n"
                   "  CrashOrPartition --> SessionExpire --> EphemeralReaped --> Fired"
               ),
               sources=["ZooKeeper Recipes: Locks (Apache Curator documentation)",
                       "Junqueira & Reed, 'ZooKeeper: Distributed Process Coordination' (2013)"]),
        _topic("etcd-leases-revisions",
               "etcd: Explicit Leases and Revision-as-Token",
               "etcd's coordination model differs from ZooKeeper's in surface syntax but is the same "
               "underneath. Two distinctive choices — explicit Lease objects and globally monotonic "
               "revisions — make the fencing-token story especially clean.",
               [
                   ("Lease as a first-class object",
                    "etcd has explicit Lease(ttl) objects with their own ID. A client granted a lease "
                    "keepalives it (heartbeats every ttl/3 by convention). Any Put can be tagged with a "
                    "lease ID, and when the lease expires (or is revoked), all keys tagged with that "
                    "lease are deleted atomically by the cluster. This subsumes ZK's ephemeral-node "
                    "pattern: instead of 'ephemeral nodes tied to my session', you have 'keys tied to "
                    "my explicit lease, which is itself heart-beated'. The semantics are identical; the "
                    "lifecycle is more explicit."),
                   ("Revision as global fencing token",
                    "Every cluster mutation in etcd is assigned a globally monotonic 64-bit revision. "
                    "The mod_revision returned in the response of the Put that grabbed a lock is "
                    "naturally a fencing token: it cannot decrease, and a successor's lock-Put will have "
                    "a strictly higher mod_revision. Pass that revision through to the protected "
                    "resource as the token. No separate counter znode, no extra transaction — the "
                    "fencing token is a free byproduct of the consistency model."),
                   ("Lock recipe (clientv3 concurrency package)",
                    "The standard recipe: (1) Grant a lease with TTL (e.g. 10s); (2) Put the lock key "
                    "with `IfNotExists` and tag with the lease ID; (3) on success, the response's "
                    "mod_revision is the fencing token; on conflict, watch the existing key and retry "
                    "when it disappears. Release = explicit Delete or simply let the lease expire. The "
                    "client library wraps all of this; applications see a Lock()/Unlock() API."),
                   ("Watches with revision",
                    "etcd watches are revision-keyed: the client passes 'watch starting from revision R'. "
                    "On reconnect after a partition, the client passes the last observed revision and "
                    "etcd replays missed events. This eliminates the ZK rough edge of having to re-read "
                    "after a connection blip — etcd's watches are deterministic across disconnects "
                    "(provided the events haven't been compacted away by the cluster's history GC)."),
                   ("Comparison to ZK",
                    "Same primitives in different clothes. Ephemeral znodes ↔ leased keys; SEQUENTIAL "
                    "↔ mod_revision; one-shot watches ↔ revision-keyed watches. ZK's model is more "
                    "uniform (everything is a znode); etcd's is more explicit (leases as objects). "
                    "Choose by ecosystem fit. If you're in Kubernetes, etcd is already there. If you're "
                    "in the Hadoop/Kafka world, ZK is already there. The lock service quality is "
                    "comparable."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant C as Client\n"
                   "  participant E as etcd\n"
                   "  participant R as Resource\n"
                   "  C->>E: Lease.Grant(ttl=10s) → leaseID=L1\n"
                   "  C->>E: Put(/lock/foo, leaseID=L1, IfNotExists)\n"
                   "  E-->>C: ok, mod_revision=42\n"
                   "  loop every 3s\n"
                   "    C->>E: Lease.KeepAlive(L1)\n"
                   "  end\n"
                   "  C->>R: write(token=42)\n"
                   "  R->>R: store max_token=42\n"
                   "  Note over C: client crashes, no keepalive\n"
                   "  E->>E: lease L1 expires; key deleted\n"
                   "  C2->>E: Put(/lock/foo, leaseID=L2, IfNotExists)\n"
                   "  E-->>C2: ok, mod_revision=43"
               ),
               sources=["etcd documentation: Concurrency",
                       "etcd clientv3 concurrency package",
                       "Howard et al., 'etcd: A reliable key-value store' (2014)"]),
        _topic("session-watch-semantics",
               "Sessions, Reconnection, and Watch Semantics",
               "The often-overlooked machinery that makes a lock service usable in practice: how "
               "sessions outlive TCP connections, how watches preserve ordering, and how clients "
               "detect lock loss promptly enough to stop work safely.",
               [
                   ("Session vs connection",
                    "A session is a logical entity owned by the cluster, with a session_id, a timeout, "
                    "and a set of owned ephemeral nodes / leases. A TCP connection is the physical "
                    "channel. They are decoupled: when the connection drops, the session continues to "
                    "exist for `session_timeout` more seconds. The client library reconnects to any "
                    "cluster member, presents its session_id, and resumes — no locks lost, no "
                    "ephemerals reaped. Only when the client cannot reconnect within session_timeout "
                    "does the cluster expire the session and reap its state."),
                   ("Negotiated timeout",
                    "When the client opens a session with timeout=30s, the cluster grants a timeout "
                    "(possibly capped lower or higher per server config). The client must then pessimise "
                    "this number — declaring local-loss at, say, granted_timeout × 2/3 — so the client "
                    "always gives up on its locks BEFORE the cluster does. If the timing is reversed, the "
                    "client may believe it still holds locks for a brief window after the cluster has "
                    "released them — a safety hole that fencing tokens close, but that's unsightly. "
                    "Standard pattern: heartbeat every timeout/3, declare local-loss at timeout × 2/3."),
                   ("Watch ordering guarantees",
                    "Watches fire in the same order as the underlying state-machine commits. A client "
                    "that sees its data-watch on /a fire before its data-watch on /b is guaranteed that "
                    "/a was modified before /b in the global commit order. This is what makes "
                    "ephemeral-sequential herd-free: the predecessor's deletion is observed before the "
                    "client's own re-evaluation, so handover is always correct."),
                   ("At-most-once delivery",
                    "If the client is disconnected at the moment a watch should fire, the watch is lost "
                    "(in ZK's classic one-shot model). The contract is: on reconnect, the client MUST "
                    "re-read the watched paths to resync. Failing to re-read is a frequent bug — the "
                    "application thinks 'no event happened' when really it missed one. Persistent and "
                    "recursive watches (modern ZK, etcd) ease this, but the discipline of 'reconnect = "
                    "resync' is still the right mental model."),
                   ("Session loss is application-visible",
                    "When the cluster expires a session, the client library raises SessionExpired on the "
                    "next operation. The application MUST treat this as 'every lock and ephemeral I "
                    "owned is gone'. In practice this means: on SessionExpired, stop all in-progress "
                    "work that depended on a held lock; do not write to any protected resource without "
                    "first re-acquiring; treat the application's logical state as undefined until "
                    "re-bootstrapped. This is uncomfortable for application authors but it is the "
                    "honest contract — and fencing tokens are what make it tolerable, because even a "
                    "buggy app that fails to stop won't actually corrupt anything."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant App\n  participant Lib as Client Lib\n  participant N1 as Node 1\n  participant N2 as Node 2\n"
                   "  App->>Lib: Open session(timeout=30s)\n"
                   "  Lib->>N1: connect; Session.Open\n"
                   "  N1-->>Lib: session_id=S1, granted=30s\n"
                   "  loop every 10s\n"
                   "    Lib->>N1: heartbeat\n"
                   "  end\n"
                   "  Note over N1: N1 partitioned\n"
                   "  Lib->>N2: reconnect; present S1\n"
                   "  N2-->>Lib: session OK (within 30s)\n"
                   "  Note over Lib: continues; no locks lost\n"
                   "  Note over N2: 30s pass with no heartbeat possible\n"
                   "  N2->>N2: expire S1; reap ephemerals\n"
                   "  Lib->>N2: heartbeat\n"
                   "  N2-->>Lib: SessionExpired\n"
                   "  Lib-->>App: SessionExpiredException — STOP"
               ),
               sources=["ZooKeeper Programmer's Guide: Sessions and Watches",
                       "etcd documentation: Watch and Lease semantics"]),
        _topic("lock-as-building-block",
               "The Lock Service as a Building Block: Election, Discovery, Config, Queues",
               "Once you have ephemeral znodes, sequential numbering, watches, and fencing tokens, an "
               "enormous amount of distributed-systems infrastructure becomes a few hundred lines of "
               "library code. This is why every consequential distributed system depends on a "
               "coordination service.",
               [
                   ("Leader election",
                    "Identical to the lock recipe with a different framing: every candidate creates an "
                    "ephemeral-sequential under /election/<role>. The lowest-numbered child IS the "
                    "leader. Each non-leader watches its predecessor. On predecessor's deletion (death "
                    "or release), the watch fires; the new lowest re-evaluates and may become leader. "
                    "Leader-fencing-token = stat.czxid of the winning znode, attached to all writes the "
                    "leader makes. Used by: Kafka controllers, HBase masters, Storm Nimbus, "
                    "Druid coordinators, ClickHouse, Redshift coordinators."),
                   ("Service discovery",
                    "Each service instance creates an ephemeral znode under /services/<name>/<instance>. "
                    "Clients GetChildren+watch /services/<name> to learn the live membership. When an "
                    "instance crashes, its session expires and the ephemeral disappears — clients are "
                    "notified, no separate health-check needed. This is essentially what Curator's "
                    "ServiceDiscovery does, and what Kubernetes does atop etcd for its Endpoints "
                    "objects."),
                   ("Distributed configuration",
                    "Configuration data lives at well-known paths (/config/feature-flags, /config/db). "
                    "Clients GetData+watch on the path. On change, the watch fires and the client "
                    "reloads. Compared to polling, latency is sub-second and load is bounded by change "
                    "frequency, not client count. Compared to a static deploy, change rollout is "
                    "instantaneous and reversible. This is the original Chubby use-case at Google."),
                   ("Distributed queues",
                    "Producers create SEQUENTIAL znodes under /queue/. Consumers GetChildren and "
                    "process the lowest. Naive version is fine for simple FIFO; production-grade "
                    "queues need ack/retry/dead-letter, which adds significant complexity (one reason "
                    "Kafka exists despite being built on ZK — it's a much better queue at high "
                    "throughput). The pattern is: use ZK for low-throughput coordination queues "
                    "(orchestration, leader hand-off), not high-throughput data pipelines."),
                   ("Barriers and latches",
                    "Phase coordination across N participants. A double-barrier (everyone joins, then "
                    "everyone leaves) is a known recipe: each participant creates an ephemeral child of "
                    "a barrier znode and waits until count = N; then the leader creates a 'ready' marker "
                    "and everyone proceeds; departure is the inverse. Used by MapReduce-style frameworks "
                    "to coordinate phase transitions."),
                   ("The general pattern",
                    "Ephemeral znodes give you 'liveness-tracked membership for free'. Sequential gives "
                    "you 'global FIFO ordering for free'. Watches give you 'event-driven coordination "
                    "for free'. Fencing tokens give you 'safe handover under arbitrary delay for free'. "
                    "These four primitives compose into virtually every coordination pattern any "
                    "production distributed system needs. Hence the Chubby paper's claim: a coordination "
                    "service should be the foundation of a distributed-systems toolkit."),
               ],
               diagram=(
                   "graph TD\n"
                   "  ZK[Coordination Service] --> E[Ephemeral znodes]\n"
                   "  ZK --> S[Sequential numbering]\n"
                   "  ZK --> W[Watches]\n"
                   "  ZK --> F[Fencing tokens]\n"
                   "  E --> M[Membership / liveness]\n"
                   "  S --> O[Global ordering]\n"
                   "  W --> N[Event-driven coordination]\n"
                   "  F --> Sa[Safe handover]\n"
                   "  M --> Disc[Service discovery]\n"
                   "  M --> El[Leader election]\n"
                   "  O --> Q[FIFO queues]\n"
                   "  N --> Cfg[Live config reload]\n"
                   "  Sa --> Lk[Correctness locks]\n"
                   "  M --> B[Barriers/latches]"
               ),
               sources=["Mike Burrows, 'The Chubby lock service for loosely-coupled distributed systems' (OSDI 2006)",
                       "Apache ZooKeeper Recipes (locks, election, queues, barriers)",
                       "Apache Curator Framework documentation"]),
    ],
)
