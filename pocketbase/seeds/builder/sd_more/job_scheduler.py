"""SD-extra — Design a Distributed Job Scheduler (cron-as-a-service).

Cron + one-time + delayed jobs, partitioned schedule store, dispatcher poll →
worker queue, at-least-once + idempotence, leader-elected scheduler, per-job
timezone, exponential backoff with jitter, dead-letter queue, missed-run
catch-up, pluggable compute backends (Lambda / k8s / HTTP), and cancellation
semantics.
"""
from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design a Distributed Job Scheduler",
    "Hard",
    "Design a multi-tenant cron-as-a-service that lets users schedule recurring (cron-expression), "
    "one-time (run at T), and delayed (run after Δ) jobs, then dispatches each scheduled run to a "
    "compute backend (HTTP webhook, AWS Lambda, Kubernetes Job, or internal worker pool). The "
    "system must scale to tens of millions of jobs, fire on-time within seconds, never silently "
    "drop a run, recover missed runs after outages, retry transient failures with exponential "
    "backoff and jitter, route permanently-failed runs to a dead-letter queue, support per-job "
    "timezones with correct DST handling, and offer at-least-once delivery with idempotency keys "
    "for safe retries. A leader-elected scheduler tier owns the time-to-fire decision, while a "
    "horizontally-scaled dispatcher tier hands runs off to a durable queue (Kafka or SQS) consumed "
    "by stateless workers. Cancellation, pause/resume, and audit history are first-class.",
    hints=[
        "Two clocks: schedule clock (when to fire) and execution clock (the actual run lifecycle).",
        "Jobs table partitioned/sharded by next_run_at — index-friendly polling, not full scans.",
        "Dispatcher polls 'due' jobs in a tight time bucket, enqueues to broker, then advances next_run_at.",
        "Leader election (etcd/ZK/Raft) ensures one scheduler per shard — duplicate fires are the failure mode.",
        "At-least-once delivery + idempotency key per (job_id, scheduled_for) — workers dedup, never the broker.",
        "Cron is timezone-sensitive. Always store the tz; recompute next_run_at in UTC at schedule time.",
        "Backoff = base × 2^attempt × (1 + rand(0,jitter)) — jitter prevents thundering herds.",
        "Missed runs: on outage recovery, sweep next_run_at < now and either catch-up, skip, or coalesce — policy-driven.",
        "Cancellation has two phases: stop future fires (DB flag) AND best-effort kill in-flight runs.",
        "Compute backends are pluggable adapters; the scheduler's contract is 'fire-and-track', not 'execute'.",
    ],
    constraints=[
        "Scale: 50M+ active scheduled jobs, 100K+ dispatches/sec at peak, multi-tenant",
        "Timeliness: p99 fire latency < 5s after scheduled instant under steady state",
        "Durability: zero scheduled runs silently lost; every fire is recorded in run history",
        "Recovery: after 30-min control-plane outage, fully drain backlog within 10 minutes",
        "Per-job timezone with DST correctness; cron expressions follow standard 5/6-field syntax",
        "Tenant isolation: noisy-neighbor protection via per-tenant rate limits and queue lanes",
        "Retry budget bounded: configurable max_attempts and total_timeout per job",
    ],
    req_func=[
        "Create / update / delete a job: cron expression OR one-time timestamp OR delay-from-now",
        "Per-job timezone, payload, target backend (HTTP/Lambda/k8s/internal), retry policy",
        "Fire each scheduled run on time and dispatch to the configured compute backend",
        "Track run lifecycle: SCHEDULED → DISPATCHED → RUNNING → SUCCEEDED / FAILED / DEAD_LETTERED",
        "At-least-once delivery with per-run idempotency key for worker-side dedup",
        "Exponential backoff with jitter on failure; route to DLQ after max_attempts",
        "Pause / resume / cancel a job; cancel best-effort terminates in-flight runs",
        "Missed-run catch-up policy: catch-up-all, catch-up-once, or skip after outage",
        "Run history: query past runs, view payload, exit code, logs reference, latency",
        "Multi-tenant API with auth, per-tenant quotas, and per-tenant audit log",
    ],
    req_nonfunc=[
        "Horizontally scalable scheduler + dispatcher; sharded by job_id (or hash bucket)",
        "Leader-elected scheduler per shard for at-most-once dispatch decision",
        "Fire-time accuracy: p99 < 5s drift; p999 < 30s including failover windows",
        "Durable: jobs and runs persisted before any external side effect; queue is durable",
        "Highly available: tolerate AZ failure, broker partition, single-node scheduler crash",
        "Observable: metrics on backlog, fire-latency histogram, retry rate, DLQ rate per tenant",
        "Tenant fairness: weighted-fair queueing prevents one tenant starving the cluster",
    ],
    estimation={
        "active_jobs": "50M scheduled jobs, ~30% recurring with sub-hourly cadence",
        "dispatches_per_sec": "Steady ~30K/sec; peak top-of-minute / top-of-hour ~100K/sec",
        "row_size": "~500 bytes/job + ~200 bytes/run record",
        "schedule_store_size": "50M × 500B ≈ 25GB hot table; +runs partitioned by day",
        "runs_per_day": "~3B run records/day; retain 30d hot, archive to S3",
        "shards": "256 hash buckets; ~200K jobs/shard, dispatcher polls each shard at 1Hz",
        "queue_throughput": "100K msg/sec peak; RF=3 replicated broker (Kafka or SQS-equivalent)",
        "leader_election": "256 shard leaders × 1 backup each; etcd lease 10s, renew 3s",
    },
    endpoints=[
        {"method": "POST", "path": "/v1/jobs",
         "description": "Create a scheduled job (cron / one-time / delay) with target + retry policy",
         "body": "{name, schedule:{kind:cron|once|delay, cron?, run_at?, delay_ms?, tz}, "
                 "target:{kind:http|lambda|k8s|internal, ...}, payload, retry:{max_attempts, "
                 "base_ms, jitter, total_timeout_ms}, catchup:catch-up-all|once|skip}"},
        {"method": "PATCH", "path": "/v1/jobs/{id}",
         "description": "Update schedule, payload, or retry policy; recomputes next_run_at",
         "body": "{...partial fields...}"},
        {"method": "DELETE", "path": "/v1/jobs/{id}",
         "description": "Soft-delete a job; future fires suppressed; in-flight runs unaffected",
         "body": "{}"},
        {"method": "POST", "path": "/v1/jobs/{id}/pause",
         "description": "Pause future fires without deleting the job",
         "body": "{}"},
        {"method": "POST", "path": "/v1/jobs/{id}/resume",
         "description": "Resume; recompute next_run_at from now per catchup policy",
         "body": "{}"},
        {"method": "POST", "path": "/v1/jobs/{id}/cancel-run/{run_id}",
         "description": "Best-effort cancellation of a specific in-flight run",
         "body": "{reason}"},
        {"method": "POST", "path": "/v1/jobs/{id}/trigger",
         "description": "Manually fire a job out-of-band (one-shot, idempotency key required)",
         "body": "{idempotency_key, override_payload?}"},
        {"method": "GET", "path": "/v1/jobs/{id}/runs",
         "description": "Paginated run history with filter by status, time range",
         "body": "{}"},
        {"method": "GET", "path": "/v1/runs/{run_id}",
         "description": "Detailed run record: status, attempts, last_error, dispatch + completion ts",
         "body": "{}"},
        {"method": "POST", "path": "/v1/runs/{run_id}/ack",
         "description": "Worker reports terminal status (SUCCESS / FAIL) for a dispatched run",
         "body": "{status, exit_code, output_ref, error?}"},
    ],
    tables=[
        {"name": "jobs",
         "columns": ["id UUID PK", "tenant_id UUID", "name VARCHAR(255)", "kind VARCHAR(16)",
                     "cron_expr VARCHAR(64)", "tz VARCHAR(64)", "run_at BIGINT", "delay_ms BIGINT",
                     "next_run_at BIGINT", "shard SMALLINT", "status VARCHAR(16)",
                     "target_kind VARCHAR(16)", "target_config JSON", "payload JSON",
                     "retry_policy JSON", "catchup_policy VARCHAR(16)",
                     "created_at BIGINT", "updated_at BIGINT", "version BIGINT"]},
        {"name": "runs",
         "columns": ["id UUID PK", "job_id UUID", "tenant_id UUID", "scheduled_for BIGINT",
                     "idempotency_key VARCHAR(128)", "attempt INT", "status VARCHAR(16)",
                     "dispatched_at BIGINT", "started_at BIGINT", "completed_at BIGINT",
                     "exit_code INT", "error TEXT", "output_ref TEXT",
                     "PRIMARY KEY (id)"]},
        {"name": "leader_leases",
         "columns": ["shard SMALLINT PK", "leader_id VARCHAR(64)", "lease_until BIGINT",
                     "term BIGINT"]},
        {"name": "dlq",
         "columns": ["run_id UUID PK", "job_id UUID", "tenant_id UUID", "reason TEXT",
                     "last_error TEXT", "attempts INT", "moved_at BIGINT"]},
        {"name": "audit_log",
         "columns": ["id BIGINT PK", "tenant_id UUID", "actor VARCHAR(128)", "action VARCHAR(64)",
                     "subject_id UUID", "details JSON", "at BIGINT"]},
    ],
    indexes=[
        "(shard, next_run_at) on jobs — primary dispatcher poll index",
        "(tenant_id, status) on jobs — tenant dashboards / list",
        "(job_id, scheduled_for) on runs UNIQUE — idempotent fire dedup",
        "(tenant_id, completed_at DESC) on runs — recent run history",
        "(status, dispatched_at) on runs — stuck-run sweeper",
        "(tenant_id, moved_at DESC) on dlq — DLQ inbox per tenant",
    ],
    hld_desc=(
        "Three planes. Control plane: API + jobs DB (Postgres or sharded MySQL) holds job "
        "definitions and the authoritative next_run_at. Schedule plane: a fleet of scheduler "
        "processes, each elected leader for a subset of 256 hash shards, polls (shard, "
        "next_run_at <= now) every second, claims due rows transactionally, writes a run "
        "record with an idempotency key (job_id, scheduled_for), advances next_run_at to the "
        "next cron tick, and enqueues a dispatch message onto a durable broker (Kafka or SQS). "
        "Dispatch plane: stateless dispatcher workers consume the broker, call the configured "
        "compute adapter (HTTP webhook, Lambda invoke, k8s Job apply, internal worker pool), "
        "and on completion ack the run via a callback or sidecar. Failures retry with "
        "exponential backoff + jitter up to max_attempts; permanent failures land in a DLQ "
        "topic and a dlq table for tenant inspection. Leader election uses etcd / Consul / "
        "ZK leases per shard; loss of a leader is detected within one lease (10s) and a backup "
        "scheduler takes over. Cancellation flips a job flag (stops future fires) and emits a "
        "cancel-run message that the adapter forwards to the compute backend (best-effort kill)."
    ),
    hld_components=[
        {"name": "API Gateway", "role": "Auth, rate-limit, tenant isolation, route to control plane"},
        {"name": "Control Service", "role": "CRUD on jobs; computes initial next_run_at + tz handling"},
        {"name": "Jobs DB (sharded)", "role": "Authoritative jobs + runs; partitioned by shard"},
        {"name": "Scheduler (per-shard leader)", "role": "Polls due jobs, claims, writes run, advances next_run_at"},
        {"name": "Leader Election (etcd / ZK)", "role": "Per-shard lease; one active scheduler per shard"},
        {"name": "Cron Engine", "role": "Parses cron expr + tz, computes next fire instant in UTC"},
        {"name": "Durable Broker (Kafka / SQS)", "role": "Dispatch queue between scheduler and workers"},
        {"name": "Dispatcher Worker", "role": "Consumes broker, invokes compute adapter, tracks run"},
        {"name": "Compute Adapters", "role": "HTTP, Lambda, k8s Job, internal pool — pluggable"},
        {"name": "Retry / Backoff Service", "role": "Failed runs requeued with exp backoff + jitter"},
        {"name": "DLQ", "role": "Permanently-failed runs surfaced for tenant action"},
        {"name": "Catch-up Sweeper", "role": "After outage, sweeps next_run_at < now per catchup policy"},
        {"name": "Stuck-Run Reaper", "role": "Times out runs DISPATCHED but never acked"},
        {"name": "Audit Log", "role": "All control-plane mutations + dispatch decisions"},
    ],
    detailed_design={
        "schedule_storage_and_polling": (
            "jobs table is hash-sharded by job_id into 256 buckets. The hot column is "
            "next_run_at; the primary index is (shard, next_run_at). Each scheduler leader owns "
            "one shard and runs a 1Hz loop: SELECT id, next_run_at FROM jobs WHERE shard=? AND "
            "next_run_at <= now() AND status='ACTIVE' ORDER BY next_run_at LIMIT 1000 FOR UPDATE "
            "SKIP LOCKED. Per row: insert a runs record with idempotency_key=(job_id, "
            "scheduled_for) UNIQUE, recompute next_run_at via cron+tz, UPDATE the job, COMMIT, "
            "then publish to the broker. SKIP LOCKED + UNIQUE constraint together make the fire "
            "idempotent under retries and overlapping leader windows."
        ),
        "leader_election_per_shard": (
            "Each shard has an etcd lease key /scheduler/lease/{shard}. Schedulers compete on "
            "startup; the holder renews every 3s on a 10s lease. On lease loss the scheduler "
            "self-fences (drops in-flight DB transactions) within one renewal window. A backup "
            "scheduler in another AZ acquires the lease and resumes polling. Exactly-one-active "
            "per shard at any instant prevents duplicate writes to the runs table; the UNIQUE "
            "(job_id, scheduled_for) is the second line of defense if leases overlap by jitter."
        ),
        "cron_and_timezone": (
            "Stored as (cron_expr, tz IANA name). next_run_at is computed in UTC at create/update "
            "time and after each fire. The cron engine localizes 'now' to the tz, finds the next "
            "matching local instant, then converts back to UTC. DST: at 'spring forward' a 02:30 "
            "daily job is shifted to the equivalent skipped-or-following instant per policy "
            "(skip / fold). At 'fall back' the duplicated wall-clock hour fires once, not twice — "
            "the engine tracks the last fired UTC instant to avoid the duplicate. Fixed cadences "
            "(every 5m) are tz-independent and use simple addition."
        ),
        "dispatch_and_at_least_once": (
            "Once a run row is committed with idempotency_key, the scheduler publishes "
            "{run_id, job_id, scheduled_for, attempt, target, payload} to the broker. Dispatcher "
            "workers consume in groups; on receipt they invoke the configured adapter. The "
            "broker guarantees at-least-once delivery — duplicates are possible. Workers dedup "
            "by checking runs.status before invoking the target: if already RUNNING/SUCCEEDED, "
            "the message is acked and skipped. The compute backend itself is expected to honor "
            "an Idempotency-Key header for HTTP / a client token for Lambda — the scheduler "
            "passes idempotency_key through so the user's handler can dedup as well."
        ),
        "retry_backoff_jitter_dlq": (
            "Per-job retry policy: {max_attempts, base_ms, factor=2, max_backoff_ms, jitter=0.5, "
            "total_timeout_ms}. On failure ack: backoff = min(base × factor^attempt, max_backoff) "
            "× (1 + rand(0, jitter)). The dispatcher schedules a delayed re-enqueue (broker "
            "DelaySeconds, or a delay topic with a per-shard timer wheel for sub-second). When "
            "attempts == max_attempts or wall-clock exceeds total_timeout_ms, the run transitions "
            "to DEAD_LETTERED and is published to the DLQ topic + dlq table; tenants can list, "
            "inspect, and replay from DLQ. Jitter is critical: many jobs fire on top-of-minute "
            "and would synchronize their retries without it."
        ),
        "missed_run_catchup": (
            "On scheduler restart or after a control-plane outage, queryable jobs may have "
            "next_run_at far in the past. catchup_policy options: (1) catch-up-all — emit one "
            "run per missed cron tick up to a cap; (2) catch-up-once — emit a single run for "
            "the most recent missed tick; (3) skip — advance next_run_at to the next future "
            "tick and emit nothing. Per-job choice; default is catch-up-once. The catch-up "
            "sweeper runs on shard-leader takeover and is rate-limited per tenant to prevent a "
            "thundering herd after long outages."
        ),
        "compute_backends": (
            "Pluggable adapter interface: invoke(run_id, idempotency_key, payload, deadline) -> "
            "(ack_token, async). Implementations: (1) HTTP webhook — POST with Idempotency-Key "
            "header, expects 2xx; on 5xx retry, on 4xx (non-429) DLQ immediately; (2) AWS "
            "Lambda — Invoke with ClientContext including idempotency_key, async event source; "
            "(3) Kubernetes Job — apply a Job manifest with name=run_id (k8s name uniqueness "
            "gives idempotency), watch for completion; (4) Internal worker pool — push onto a "
            "lower-tier queue consumed by tenant-owned workers. Each adapter has its own "
            "completion path: HTTP synchronous return, Lambda destination/EventBridge, k8s "
            "watch, internal ack callback."
        ),
        "cancellation_semantics": (
            "Two-phase. Phase 1 (always succeeds): UPDATE jobs SET status='CANCELLED' — future "
            "fires suppressed. Already-published runs in the broker are filtered by dispatcher "
            "before invocation (re-read job status, skip if cancelled). Phase 2 (best-effort): "
            "for in-flight runs, the API issues an adapter-specific kill: HTTP — fire a DELETE "
            "to a configured cancel_url if the user provided one; Lambda — no native kill, mark "
            "run as 'cancel requested' and let the handler poll; k8s — kubectl delete job "
            "<run_id>; internal — interrupt the worker thread/process. Runs reaching SUCCEEDED "
            "concurrently with cancel are not rolled back — cancellation is at-most-best-effort, "
            "the user's handler is the source of truth on whether work happened."
        ),
        "stuck_run_reaper": (
            "A run can sit DISPATCHED forever if the worker crashes between invoke and ack. A "
            "reaper job runs every 30s and finds runs WHERE status='DISPATCHED' AND "
            "dispatched_at < now() - dispatch_timeout. It transitions them to FAILED and "
            "either retries (per retry policy) or DLQs. dispatch_timeout is per-target — HTTP "
            "default 30s, Lambda backend-bounded, k8s up to job activeDeadlineSeconds. The "
            "reaper is the safety net that keeps the run state machine live under any failure."
        ),
        "tenant_isolation_and_quotas": (
            "Per-tenant rate limits at the API (creates/updates/sec) and at the dispatcher "
            "(dispatches/sec). The broker uses per-tenant queue lanes (one Kafka topic prefix "
            "per tenant for big tenants; a hash-bucketed shared topic for the long tail). "
            "Weighted-fair queueing in the dispatcher — round-robin across tenants, with each "
            "tenant capped at its quota. A noisy tenant can saturate its own lane but cannot "
            "starve others. Quota exhaustion errors are loud (429) at the API; in-broker we "
            "delay rather than drop."
        ),
        "consistency_and_durability": (
            "Strong consistency at the row level for jobs and runs (Postgres / sharded MySQL "
            "with single-shard transactions). Cross-shard operations are avoided — a job lives "
            "in exactly one shard chosen at creation. The broker is the only async, at-least-"
            "once boundary. The contract: a run record committed in the DB is the source of "
            "truth that the run was 'fired'; broker delivery is opportunistic with the reaper "
            "as backstop. No external side effect (HTTP call, Lambda invoke) happens before "
            "the run row is durable."
        ),
        "observability": (
            "Key metrics: scheduler poll latency, fire-latency histogram (now - scheduled_for), "
            "broker publish errors, dispatch attempt rate, retry rate per tenant, DLQ rate, "
            "stuck-run count, leader-election flap rate, per-tenant quota usage. Per-job traces: "
            "scheduled_for → dispatched_at → started_at → completed_at, with tenant_id and "
            "target_kind labels. Alerts on backlog growth (next_run_at < now - 60s row count) "
            "and DLQ spike."
        ),
    },
    trade_offs=[
        {"option": "Polling jobs DB vs in-memory timer wheel",
         "for_db": "Durable, shard-scaled, simple to reason about, recovers cleanly after crash",
         "for_wheel": "Microsecond fire accuracy, no DB load, good for huge fan-out of short delays",
         "recommendation": "DB poll at 1Hz for cron + long delays; per-shard in-memory timer wheel "
                           "as an optional accelerator for sub-second delays. Polling is the "
                           "correct default — durability beats accuracy for cron workloads."},
        {"option": "Broker: Kafka vs SQS / SNS for dispatch",
         "for_kafka": "High throughput, retention enables replay, ordered per partition",
         "for_sqs": "Managed, infinite retention with DLQ built-in, no ops burden, native delay queues",
         "recommendation": "SQS-style for SaaS / managed deployments — DLQ + delay-queue + "
                           "managed ops are a perfect fit. Kafka for self-hosted high-throughput "
                           "or when stream-processing the dispatch log is valuable."},
        {"option": "Leader-elected scheduler vs leaderless with optimistic claim",
         "for_leader": "Single decision-maker per shard, simpler reasoning, fewer wasted DB ops",
         "for_leaderless": "No election dependency, any node can claim with FOR UPDATE SKIP LOCKED",
         "recommendation": "Leader-elected by default — election cost is paid once per 10s. "
                           "Leaderless with SKIP LOCKED is a correct fallback if etcd/ZK is "
                           "unavailable; UNIQUE (job_id, scheduled_for) prevents double-fire."},
        {"option": "Catch-up: replay all missed vs skip after outage",
         "for_replay": "Faithful to user's intent — every cron tick fires",
         "for_skip": "Avoids thundering herd; users care about future runs, not historical",
         "recommendation": "Per-job policy with catch-up-once as default. Replay-all only for "
                           "audit / billing jobs that must hit every tick; skip for monitoring "
                           "pings; catch-up-once is the sane middle."},
        {"option": "Per-job timer rows vs cron expression evaluated at fire time",
         "for_rows": "Pre-materialize the next N runs into a rows table — easy poll",
         "for_eval": "Single row per job, recompute next_run_at on each fire",
         "recommendation": "Single row + recompute. Pre-materializing wastes storage on jobs "
                           "with frequent cadences (every-second × forever) and complicates "
                           "schedule edits. Recompute is O(1) with a good cron library."},
    ],
    tips=[
        "Lead with the two-clocks framing: schedule clock (when) vs execution clock (how it ran).",
        "Shard the jobs table by hash(job_id) and index by (shard, next_run_at) — this is the "
        "single most important decision for throughput.",
        "Idempotency key = (job_id, scheduled_for). UNIQUE constraint + SKIP LOCKED is the "
        "double-belt-and-suspenders against duplicate fires.",
        "Always say 'at-least-once + idempotent worker' — exactly-once is a red flag for senior interviews.",
        "Backoff with jitter — call out thundering-herd at top-of-minute as the failure mode.",
        "Per-job timezone is a bug magnet. Mention DST handling explicitly — interviewers love this.",
        "Cancellation is two-phase: stop future fires (cheap) + best-effort kill (hard). Don't "
        "promise hard cancel.",
        "Compute backends are pluggable adapters — scheduler's job is fire-and-track, not execute.",
        "Reaper for stuck runs is the unsung hero. Don't forget the cleanup loop.",
    ],
    thought_process=[
        "1. Clarify scope: cron + one-time + delay; pluggable backends; multi-tenant.",
        "2. Estimate: 50M jobs, 100K dispatches/sec peak, 256 shards by hash(job_id).",
        "3. APIs: CRUD jobs, pause/resume/cancel, run history, manual trigger.",
        "4. Schema: jobs (next_run_at indexed), runs (idempotency unique), dlq, leader_leases.",
        "5. Schedule plane: leader-elected scheduler per shard, 1Hz poll, FOR UPDATE SKIP LOCKED.",
        "6. Cron + tz: store IANA name; recompute next_run_at in UTC; handle DST explicitly.",
        "7. Dispatch plane: durable broker (Kafka/SQS); workers idempotent via run status check.",
        "8. Failure: exp backoff + jitter; bounded retries; DLQ for permanent failure.",
        "9. Recovery: missed-run catchup policy (all / once / skip), rate-limited.",
        "10. Cancellation: phase 1 DB flag, phase 2 adapter kill (best-effort).",
        "11. Reaper for stuck DISPATCHED runs; observability on fire-latency + backlog.",
        "12. Tenant isolation: lanes + weighted-fair dispatch; per-tenant quotas.",
    ],
    tags=["scheduler", "cron", "distributed", "queue", "backend"],
    arch_nodes=[
        {"id": "client", "label": "Tenant Client", "type": "client"},
        {"id": "api", "label": "API Gateway", "type": "lb"},
        {"id": "ctrl", "label": "Control Service", "type": "server"},
        {"id": "db", "label": "Jobs DB (sharded)", "type": "database"},
        {"id": "elect", "label": "Leader Election\\n(etcd / ZK)", "type": "service"},
        {"id": "sched", "label": "Scheduler (per shard)", "type": "server"},
        {"id": "cron", "label": "Cron + TZ Engine", "type": "service"},
        {"id": "broker", "label": "Durable Broker\\n(Kafka / SQS)", "type": "queue"},
        {"id": "disp", "label": "Dispatcher Workers", "type": "server"},
        {"id": "ad_http", "label": "HTTP Adapter", "type": "service"},
        {"id": "ad_lambda", "label": "Lambda Adapter", "type": "service"},
        {"id": "ad_k8s", "label": "k8s Job Adapter", "type": "service"},
        {"id": "ad_int", "label": "Internal Pool", "type": "service"},
        {"id": "retry", "label": "Retry / Backoff", "type": "service"},
        {"id": "dlq", "label": "DLQ", "type": "queue"},
        {"id": "reap", "label": "Stuck-Run Reaper", "type": "service"},
        {"id": "audit", "label": "Audit Log", "type": "database"},
    ],
    arch_edges=[
        {"source": "client", "target": "api"},
        {"source": "api", "target": "ctrl", "label": "CRUD"},
        {"source": "ctrl", "target": "db", "label": "persist job"},
        {"source": "ctrl", "target": "cron", "label": "compute next_run_at"},
        {"source": "ctrl", "target": "audit"},
        {"source": "elect", "target": "sched", "label": "lease"},
        {"source": "sched", "target": "db", "label": "poll due / claim"},
        {"source": "sched", "target": "cron", "label": "advance next"},
        {"source": "sched", "target": "broker", "label": "publish run"},
        {"source": "broker", "target": "disp"},
        {"source": "disp", "target": "ad_http"},
        {"source": "disp", "target": "ad_lambda"},
        {"source": "disp", "target": "ad_k8s"},
        {"source": "disp", "target": "ad_int"},
        {"source": "disp", "target": "db", "label": "ack run"},
        {"source": "disp", "target": "retry", "label": "on failure"},
        {"source": "retry", "target": "broker", "label": "delayed re-enqueue"},
        {"source": "retry", "target": "dlq", "label": "max attempts"},
        {"source": "reap", "target": "db", "label": "sweep stuck"},
        {"source": "reap", "target": "broker", "label": "requeue"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant U as Tenant\n"
        "  participant API\n"
        "  participant DB as Jobs DB\n"
        "  participant S as Scheduler (leader)\n"
        "  participant B as Broker\n"
        "  participant W as Dispatcher\n"
        "  participant T as Target (HTTP/Lambda/k8s)\n"
        "  U->>API: POST /jobs (cron, tz, target)\n"
        "  API->>DB: insert job, compute next_run_at\n"
        "  API-->>U: 201 created\n"
        "  loop every 1s per shard\n"
        "    S->>DB: SELECT due FOR UPDATE SKIP LOCKED\n"
        "    DB-->>S: due jobs\n"
        "    S->>DB: insert runs (idempotency_key UNIQUE)\n"
        "    S->>DB: advance next_run_at\n"
        "    S->>B: publish dispatch msg\n"
        "  end\n"
        "  B->>W: deliver msg (at-least-once)\n"
        "  W->>DB: read run status (dedup check)\n"
        "  W->>T: invoke (Idempotency-Key)\n"
        "  T-->>W: 2xx / failure\n"
        "  W->>DB: update run status\n"
        "  alt failure within retry budget\n"
        "    W->>B: delayed requeue (exp backoff + jitter)\n"
        "  else max attempts hit\n"
        "    W->>DB: status=DEAD_LETTERED\n"
        "    W->>B: publish to DLQ topic\n"
        "  end"
    ),
    er_diagram=(
        "erDiagram\n"
        "  TENANT ||--o{ JOB : owns\n"
        "  JOB ||--o{ RUN : produces\n"
        "  RUN ||--o| DLQ : terminal-fail\n"
        "  JOB ||--o{ AUDIT : changes\n"
        "  SHARD ||--o{ JOB : groups\n"
        "  SHARD ||--|| LEASE : elects\n"
        "  JOB { uuid id PK\n uuid tenant_id\n string kind\n string cron_expr\n string tz\n bigint next_run_at\n int shard\n string status }\n"
        "  RUN { uuid id PK\n uuid job_id\n bigint scheduled_for\n string idempotency_key\n int attempt\n string status }\n"
        "  LEASE { int shard PK\n string leader_id\n bigint lease_until }\n"
        "  DLQ { uuid run_id PK\n uuid job_id\n text reason }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Create job] --> B{Schedule kind?}\n"
        "  B -->|cron + tz| C[Compute next_run_at in UTC]\n"
        "  B -->|once at T| D[next_run_at = T]\n"
        "  B -->|delay Δ| E[next_run_at = now + Δ]\n"
        "  C --> F[Persist in shard]\n"
        "  D --> F\n"
        "  E --> F\n"
        "  F --> G[Scheduler leader polls shard]\n"
        "  G --> H{Due?}\n"
        "  H -->|No| G\n"
        "  H -->|Yes| I[Claim FOR UPDATE SKIP LOCKED]\n"
        "  I --> J[Insert run UNIQUE idempotency_key]\n"
        "  J --> K[Advance next_run_at]\n"
        "  K --> L[Publish to broker]\n"
        "  L --> M[Dispatcher consumes]\n"
        "  M --> N[Adapter invokes target]\n"
        "  N --> O{Success?}\n"
        "  O -->|Yes| P[runs.status=SUCCEEDED]\n"
        "  O -->|No| Q{Attempts < max?}\n"
        "  Q -->|Yes| R[Backoff + jitter, requeue]\n"
        "  Q -->|No| S[DLQ]\n"
        "  R --> M"
    ),
    tradeoff_title="Catch-up policy after outage: replay-all vs catch-up-once vs skip",
    tradeoff_options=[
        {"label": "Replay all missed runs",
         "description": "Emit one run per missed cron tick (capped) once the scheduler recovers.",
         "pros": ["Faithful to the cron contract — every tick fires",
                 "Required for billing / audit / metering jobs that must hit every interval",
                 "Predictable from the user's mental model: 'cron always runs'"],
         "cons": ["Thundering herd of backlogged runs after long outages",
                 "Most jobs (alerts, monitoring pings) genuinely don't want N stale invocations",
                 "Risk of cascading load on downstream targets"]},
        {"label": "Catch-up once",
         "description": "Emit a single run for the most recent missed tick, then resume normally.",
         "pros": ["Avoids the herd; downstream sees one extra run, not N",
                 "Matches user intent for 99% of monitoring / sync jobs",
                 "Bounded recovery cost regardless of outage length"],
         "cons": ["Loses fidelity for jobs that genuinely need every tick",
                 "Some runs are silently skipped — observability must surface this"]},
        {"label": "Skip — advance to next future tick",
         "description": "Discard all missed runs; next_run_at jumps to the next future cron tick.",
         "pros": ["Zero backlog cost; cleanest recovery",
                 "Right choice for liveness-style pings where 'old' is worthless"],
         "cons": ["Silent data loss for any job that needed the missed runs",
                 "Surprising to users not aware of the policy"]},
    ],
    tradeoff_rec=(
        "Per-job policy with catch-up-once as the system default. Replay-all only for jobs the "
        "user has explicitly tagged as billing/audit/metering. Skip is the right default for "
        "monitoring pings. All three modes need observability — surface the count of skipped or "
        "replayed runs in the post-outage tenant report so users aren't surprised."
    ),
    senior_topics=[
        _topic("partitioned-jobs-table",
               "Partitioned Jobs Table and the (shard, next_run_at) Index",
               "The single most important schema decision. Cron-as-a-service is dominated by one "
               "query: 'what is due now in my shard?' — and the table layout must make that "
               "query an index range scan, not a full table scan.",
               [
                   ("Why hash-shard by job_id",
                    "Hash sharding distributes load uniformly across scheduler leaders and DB "
                    "shards regardless of tenant skew. Range sharding (by tenant_id or "
                    "next_run_at) creates hot shards: one big tenant or a top-of-minute fire "
                    "concentration overwhelms one node. Hash by job_id keeps every shard ~equal."),
                   ("Composite index (shard, next_run_at)",
                    "The poll query is WHERE shard=? AND next_run_at <= now() ORDER BY "
                    "next_run_at LIMIT N. With (shard, next_run_at) the index seek is O(log n) "
                    "to the shard's earliest due row, then sequential — the optimal physical "
                    "layout. Without it the planner falls back to filter+sort, which is fatal "
                    "at 50M rows."),
                   ("FOR UPDATE SKIP LOCKED",
                    "Postgres' SKIP LOCKED lets the scheduler claim due rows without blocking "
                    "on rows another transaction is processing. Combined with the leader lease, "
                    "it's the safety net: if leases overlap by jitter, two schedulers won't "
                    "block each other but also won't double-claim. The UNIQUE (job_id, "
                    "scheduled_for) on runs is the third guard."),
                   ("Avoid a table-wide ORDER BY",
                    "Polling without the shard predicate scans every shard's data. Always poll "
                    "per-shard. The scheduler instance for shard 17 only ever WHERE shard=17 — "
                    "this is what makes 256-way parallelism actually work."),
                   ("Vacuum and bloat",
                    "next_run_at is updated on every fire — the row churns. Postgres HOT updates "
                    "help, but heavy churn requires aggressive autovacuum tuning per-table. "
                    "Alternative: use a separate 'schedule_state' table with one tiny row per "
                    "job to avoid bloating the main jobs table."),
               ],
               diagram=(
                   "graph LR\n"
                   "  J[jobs table] --> S0[shard=0]\n"
                   "  J --> S1[shard=1]\n"
                   "  J --> SN[shard=255]\n"
                   "  S0 -. (shard,next_run_at) idx .-> Q0[poll <= now]\n"
                   "  S1 -. (shard,next_run_at) idx .-> Q1[poll <= now]\n"
                   "  SN -. (shard,next_run_at) idx .-> QN[poll <= now]\n"
                   "  L0[Leader 0] --> S0\n"
                   "  L1[Leader 1] --> S1\n"
                   "  LN[Leader N] --> SN"
               )),
        _topic("at-least-once-and-idempotency",
               "At-Least-Once Delivery and the (job_id, scheduled_for) Idempotency Key",
               "Distributed cron will fire some runs twice. The design's job is to make the "
               "second fire harmless, not to prevent it.",
               [
                   ("Why exactly-once is a lie",
                    "A scheduler crash between 'insert run row' and 'publish to broker' must "
                    "result in either the run being retried after recovery (at-least-once) or "
                    "lost (at-most-once). There is no third option without a 2PC against the "
                    "broker, and 2PC against Kafka/SQS is not a real-world primitive."),
                   ("The idempotency key",
                    "(job_id, scheduled_for) uniquely identifies a logical fire. UNIQUE on the "
                    "runs table prevents two run rows for the same fire. The dispatcher passes "
                    "this key to the compute target as Idempotency-Key (HTTP) / ClientContext "
                    "(Lambda) / job name (k8s) so the user's handler can dedup as well."),
                   ("Worker-side dedup",
                    "Before invoking the target, the worker re-reads the run row. If status is "
                    "already RUNNING/SUCCEEDED (because a previous delivery beat it), the "
                    "worker acks the broker message and skips. This makes broker redelivery a "
                    "no-op for already-completed runs."),
                   ("Compose with target idempotency",
                    "Even with worker dedup, the target may receive a second invocation if the "
                    "first started before the worker crashed. Pushing Idempotency-Key into the "
                    "target's contract is the only correct end-to-end story. For HTTP, that "
                    "means the customer's handler must dedup on the header — document it."),
                   ("Why never use exactly-once language",
                    "In a system-design interview, 'exactly-once' is a senior red flag. Senior "
                    "engineers say 'at-least-once with idempotent receivers' and explain why. "
                    "The scheduler delivers at-least-once; the worker dedups; the target is "
                    "idempotent on the key. End to end this is the only sound model."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant S as Scheduler\n"
                   "  participant DB\n"
                   "  participant B as Broker\n"
                   "  participant W as Worker\n"
                   "  participant T as Target\n"
                   "  S->>DB: INSERT run (uniq job_id+sched_for)\n"
                   "  S->>B: publish run msg\n"
                   "  Note over S,B: scheduler crashes here on retry\n"
                   "  B-->>W: deliver msg #1\n"
                   "  W->>DB: read run.status\n"
                   "  W->>T: invoke (Idem-Key)\n"
                   "  B-->>W: deliver msg #1 again (at-least-once)\n"
                   "  W->>DB: status=RUNNING — skip\n"
                   "  W-->>B: ack"
               )),
        _topic("leader-election-per-shard",
               "Leader Election Per Shard (etcd / ZK Leases)",
               "Each shard has exactly one active scheduler at any instant — that's the "
               "guarantee leader election provides. Without it, two schedulers polling the "
               "same shard produce duplicate fires (the UNIQUE on runs catches them, but only "
               "after wasted work).",
               [
                   ("Lease, not lock",
                    "Use a TTL'd lease (etcd lease, ZK ephemeral node, Consul session) rather "
                    "than an indefinite lock. A lease with renewal automatically releases on "
                    "scheduler death — no fence-on-stuck-process problem. Typical: 10s lease, "
                    "renew every 3s; 7s safety margin for renewal jitter."),
                   ("Self-fencing on lease loss",
                    "The scheduler must check its lease ownership before each DB transaction "
                    "and abort if the lease is gone. Otherwise after a GC pause it could write "
                    "with a stale view while a new leader has taken over. etcd's revision "
                    "number is a fencing token — include it in the DB write predicate."),
                   ("Per-shard, not cluster-wide",
                    "256 shards = 256 independent leaders. Cluster-wide single leader is a "
                    "single point of failure and doesn't scale. Per-shard leadership scales "
                    "with shard count and has a smaller blast radius — one shard's leader "
                    "death affects ~0.4% of jobs."),
                   ("Fast failover",
                    "Lease expiry detection is bounded by lease TTL; new leader election is "
                    "another lease renewal. Total failover ~10-20s in the worst case. During "
                    "that window the affected shard's poll loop is paused — fire-latency p99 "
                    "absorbs the gap. Mitigated by a hot standby per shard that holds a "
                    "lower-priority lease, ready to take over."),
                   ("Leaderless fallback",
                    "If etcd is down, schedulers can fall back to leaderless mode: any node "
                    "polls any shard with FOR UPDATE SKIP LOCKED. Throughput drops (more "
                    "wasted DB ops), but correctness holds — the UNIQUE constraint on runs "
                    "still prevents double-fires. Worth implementing as a safety mode."),
               ],
               diagram=(
                   "graph TD\n"
                   "  E[etcd / ZK quorum] --> L0[/scheduler/lease/0/]\n"
                   "  E --> L1[/scheduler/lease/1/]\n"
                   "  E --> LN[/scheduler/lease/255/]\n"
                   "  L0 --> S0[Scheduler A: shard 0 leader]\n"
                   "  L0 -. backup .-> S0b[Scheduler B: shard 0 standby]\n"
                   "  L1 --> S1[Scheduler C: shard 1 leader]\n"
                   "  LN --> SN[Scheduler Z: shard 255 leader]"
               )),
        _topic("cron-and-timezone-correctness",
               "Cron Expressions, IANA Timezones, and DST Pitfalls",
               "Per-job timezone is one of the single biggest correctness pitfalls. DST "
               "transitions, leap seconds, and timezone DB updates all silently break naive "
               "implementations.",
               [
                   ("Always store IANA tz, never offset",
                    "Store 'America/New_York', not '-05:00'. Offsets don't capture DST. The "
                    "tz database (tzdata) is updated periodically — your server's tzdata must "
                    "be kept current, or DST shifts in countries that change their rules will "
                    "fire jobs at the wrong wall clock time."),
                   ("Compute next_run_at in UTC",
                    "Algorithm: localize 'now' to the job's tz, ask cron parser for the next "
                    "matching local instant, convert that instant back to UTC, store it. The "
                    "DB only ever sees UTC — comparisons are unambiguous, indexes are "
                    "monotonic, and the tz logic is isolated to the cron engine."),
                   ("Spring forward (skipped hour)",
                    "At 02:00 local time, clock jumps to 03:00 — there is no 02:30 that day. "
                    "A '30 2 * * *' job has no fire instant. Policy: skip the missing day, or "
                    "fold to 03:00. The Quartz convention is to fire at 03:00. Document "
                    "explicitly — silent behavior here is a recurring bug source."),
                   ("Fall back (duplicated hour)",
                    "At 02:00 local time, clock rewinds to 01:00 — wall clock 01:30 happens "
                    "twice. A '30 1 * * *' job must fire once, not twice. The cron engine "
                    "tracks the last fired UTC instant; the second occurrence has a UTC "
                    "instant > last fired, but the engine recognizes the wall-clock match was "
                    "already satisfied by the first occurrence and skips."),
                   ("Cron expression dialects",
                    "Standard 5-field (min hr dom mon dow) vs Quartz 6-field (with seconds) vs "
                    "AWS extended (with year). Pick one and document it. Year-based wildcards, "
                    "L (last day), W (weekday), # (nth-of-month) are all dialect-specific. "
                    "Use a battle-tested cron parser library; do not roll your own."),
               ],
               diagram=(
                   "graph TD\n"
                   "  J[Job: 30 2 * * * tz=America/New_York] --> P[Cron Parser]\n"
                   "  P --> N[localize now to NY]\n"
                   "  N --> M{DST transition?}\n"
                   "  M -->|spring fwd| F[Fold 02:30 -> 03:00]\n"
                   "  M -->|fall back| D[Skip duplicate 01:30]\n"
                   "  M -->|none| R[Next instant = today 02:30 NY]\n"
                   "  F --> U[Convert to UTC]\n"
                   "  D --> U\n"
                   "  R --> U\n"
                   "  U --> S[Store next_run_at]"
               )),
        _topic("backoff-jitter-and-dlq",
               "Exponential Backoff with Jitter and the Dead-Letter Queue",
               "Retries without jitter cause synchronized retry storms. The DLQ is the "
               "operational surface that lets users see and act on permanent failures.",
               [
                   ("Why jitter is mandatory",
                    "1000 jobs share a downstream dependency. Dependency goes down for 30s; "
                    "all 1000 fail at the same instant. Without jitter they all retry at base, "
                    "again at 2×base, again at 4×base — a synchronized hammer. Jitter de-"
                    "correlates: each retry is at base × 2^attempt × (1 + rand(0, jitter)) "
                    "which spreads them across the interval."),
                   ("Backoff with cap",
                    "min(base × 2^attempt, max_backoff) caps the wait so that a misconfigured "
                    "max_attempts of 30 doesn't wait days between retries. Typical: base=1s, "
                    "factor=2, max_backoff=300s (5 min), jitter=0.5, max_attempts=10. Total "
                    "retry budget: ~30 minutes wall clock."),
                   ("Total timeout vs attempt count",
                    "max_attempts alone leaves total time variable. Add total_timeout_ms — if "
                    "wall clock from first dispatch exceeds it, give up regardless of attempts "
                    "remaining. Guards against pathological backoff sequences and ensures a "
                    "predictable upper bound on retry-related load."),
                   ("DLQ as a tenant inbox",
                    "Dead-lettered runs land in two places: a dlq topic for stream processing, "
                    "and a dlq table for tenant UI. Tenants list their DLQ, inspect run "
                    "details (last_error, attempts, payload), and can replay (re-publish to "
                    "broker with attempt=0) or discard. DLQ retention is tenant-configurable; "
                    "default 14 days."),
                   ("Permanent vs transient errors",
                    "Not all failures should retry. HTTP 4xx (except 408/429) is permanent — "
                    "go straight to DLQ, don't waste retries. HTTP 5xx, 408, 429, network "
                    "timeouts, and Lambda throttles are transient — retry. The adapter "
                    "encodes this taxonomy; the retry/backoff service consults it before "
                    "re-enqueuing."),
               ],
               diagram=(
                   "graph LR\n"
                   "  F[Fail] --> C{Permanent?}\n"
                   "  C -->|4xx non-429| D[DLQ]\n"
                   "  C -->|5xx / timeout| A{attempt < max?}\n"
                   "  A -->|No| D\n"
                   "  A -->|Yes| B[wait base*2^a*(1+jitter)]\n"
                   "  B --> R[requeue to broker]\n"
                   "  D --> I[(dlq table)]\n"
                   "  D --> T[(dlq topic)]"
               )),
        _topic("missed-run-catchup",
               "Missed-Run Catch-Up After Outages",
               "When the scheduler is down for an hour, what happens to the cron jobs that "
               "should have fired? The answer is policy, not mechanism, and the policy must "
               "be visible per-job.",
               [
                   ("The three policies",
                    "catch-up-all: emit one run per missed tick, capped at a max (e.g., 100 "
                    "missed runs per job). catch-up-once: emit a single run for the most "
                    "recent missed tick. skip: advance next_run_at to the next future tick "
                    "with no make-up runs. Default catch-up-once strikes the right balance."),
                   ("Why catch-up-all needs a cap",
                    "A job with 'every minute' cadence and a 24-hour outage has 1440 missed "
                    "runs. Replaying all 1440 simultaneously hammers the target. Cap at N (say "
                    "60) and emit oldest-first; document that runs beyond the cap are skipped "
                    "with an outage marker on the job for tenant visibility."),
                   ("Sweep on leader takeover",
                    "When a scheduler acquires a shard's lease, before entering the steady-"
                    "state poll loop, it runs a catch-up sweep: SELECT WHERE next_run_at < "
                    "now() ORDER BY next_run_at. For each row, apply the per-job catchup "
                    "policy. The sweep is rate-limited (e.g., 1000 rows/sec/tenant) to "
                    "prevent the post-outage thundering herd."),
                   ("Observability of skipped runs",
                    "skip and the catch-up-all-cap silently drop runs. This is correct "
                    "behavior, but 'silent' is poison. Emit an audit-log event per skipped/"
                    "capped run; surface a 'last outage caused N skipped runs' metric in the "
                    "tenant dashboard. Users tolerate skipping; they don't tolerate not being "
                    "told."),
                   ("Coalescing semantics",
                    "An advanced variant of catch-up-once: 'coalesce all missed runs into a "
                    "single run with a coalesce_count payload field.' Useful when the user's "
                    "handler can do bulk work (e.g., 'process N reports' becomes 'process all "
                    "outstanding reports'). Optional, opt-in per job."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant S as Scheduler\n"
                   "  participant DB\n"
                   "  Note over S,DB: Outage 12:00-13:00\n"
                   "  S->>DB: acquire lease shard 17\n"
                   "  S->>DB: SELECT next_run_at < now()\n"
                   "  DB-->>S: 240 missed jobs\n"
                   "  loop per job\n"
                   "    S->>S: read catchup_policy\n"
                   "    alt all (capped 60)\n"
                   "      S->>DB: insert up to 60 runs\n"
                   "    else once\n"
                   "      S->>DB: insert 1 run for latest tick\n"
                   "    else skip\n"
                   "      S->>DB: advance to next future tick\n"
                   "    end\n"
                   "  end\n"
                   "  S->>S: enter steady-state poll"
               )),
        _topic("compute-backends-pluggable-adapters",
               "Compute Backends as Pluggable Adapters",
               "The scheduler's contract is fire-and-track. Where the work runs — HTTP "
               "webhook, Lambda, k8s Job, internal pool — is the user's choice. Adapters "
               "isolate per-backend semantics behind a uniform interface.",
               [
                   ("Adapter interface",
                    "invoke(run_id, idempotency_key, payload, deadline) returns "
                    "(ack_token, async). For sync adapters (HTTP), the call returns when the "
                    "target returns. For async adapters (Lambda async, k8s Job), invoke "
                    "returns immediately with an ack_token; completion is signaled via a "
                    "callback (Lambda destination → SNS → dispatcher), watch (k8s API), or "
                    "polling (last-resort)."),
                   ("HTTP webhook specifics",
                    "POST with Idempotency-Key header, Content-Type, signed body (HMAC) for "
                    "tenant verification. 2xx = success; 4xx (except 408/429) = permanent "
                    "failure (DLQ); 5xx/408/429/network = transient (retry). Configurable "
                    "timeout per job (default 30s). HTTPS required; mTLS for high-security "
                    "tenants."),
                   ("AWS Lambda specifics",
                    "InvocationType=Event for fire-and-forget with async dest, or "
                    "RequestResponse for sync. ClientContext carries idempotency_key. Lambda "
                    "concurrency limits per function — exceeding triggers throttle (429 "
                    "equivalent), retry. Async destinations route success/failure to SQS "
                    "topics that the dispatcher consumes for run completion."),
                   ("Kubernetes Job specifics",
                    "Apply a Job manifest with metadata.name=run_id — k8s rejects duplicate "
                    "names, giving free idempotency. activeDeadlineSeconds bounds runtime. "
                    "Watch the Job for completion via the k8s API or a controller pod. "
                    "Cleanup: ttlSecondsAfterFinished auto-deletes finished jobs to avoid "
                    "API server bloat."),
                   ("Internal worker pool",
                    "Lower-tier durable queue (e.g., Redis Streams or another Kafka topic) "
                    "consumed by tenant-owned worker processes. Useful for jobs that need "
                    "access to internal infrastructure not reachable by webhook. Same "
                    "idempotency_key contract; tenant SDK provides a runner library that "
                    "handles dedup."),
                   ("Adding a new backend",
                    "Implement Adapter (invoke + completion path), register in the dispatcher's "
                    "adapter registry, define the target_config schema. The control service "
                    "validates target_config on job create. The scheduler core remains "
                    "unchanged — adapters are the only per-backend code."),
               ],
               diagram=(
                   "graph TD\n"
                   "  D[Dispatcher Worker] --> A[Adapter Registry]\n"
                   "  A --> H[HTTP Adapter]\n"
                   "  A --> L[Lambda Adapter]\n"
                   "  A --> K[k8s Job Adapter]\n"
                   "  A --> I[Internal Pool Adapter]\n"
                   "  H --> HT[(target webhook)]\n"
                   "  L --> LT[(AWS Lambda)]\n"
                   "  K --> KT[(k8s API)]\n"
                   "  I --> IT[(internal queue)]\n"
                   "  HT -. 2xx/5xx/timeout .-> D\n"
                   "  LT -. async dest -> SNS .-> D\n"
                   "  KT -. watch .-> D\n"
                   "  IT -. ack .-> D"
               )),
        _topic("cancellation-semantics",
               "Cancellation: Two-Phase, Best-Effort",
               "Cancellation is one of the most-asked-about features and one of the most-"
               "lied-about. It is fundamentally not a hard guarantee; the design must be "
               "explicit about what it does and does not promise.",
               [
                   ("Phase 1: stop future fires",
                    "UPDATE jobs SET status='CANCELLED'. The next scheduler poll skips this "
                    "row. Already-published runs in the broker are filtered by the dispatcher "
                    "(re-read jobs.status before invoke). Phase 1 is fast, durable, and "
                    "guaranteed — within one poll cycle no new runs will fire."),
                   ("Phase 2: kill in-flight runs",
                    "For runs already RUNNING, attempt an adapter-specific kill. HTTP: send "
                    "DELETE to a tenant-configured cancel_url (if provided); the user's "
                    "handler must support it. Lambda: no native kill — write 'cancel' to a "
                    "shared store (e.g., DynamoDB) that the handler polls. k8s: kubectl "
                    "delete job/<run_id>. Internal: send interrupt to the worker process."),
                   ("Best-effort means best-effort",
                    "If the run completes successfully between cancel-request and kill-"
                    "delivery, it is not rolled back. If the user's handler ignores the "
                    "cancel signal, the run continues. Document this loudly: cancel stops "
                    "future fires guaranteed; in-flight termination is best-effort."),
                   ("Idempotent cancel",
                    "Cancel API is idempotent — calling cancel twice is harmless. The run "
                    "transitions through CANCEL_REQUESTED → CANCELLED on confirmation, or "
                    "stays CANCEL_REQUESTED until the next status update. Tenants can poll "
                    "/runs/{id} to observe the final state."),
                   ("Pause vs cancel vs delete",
                    "Three distinct operations: pause (status=PAUSED, future fires "
                    "suppressed, resumable); cancel (one-shot kill on a specific run, job "
                    "schedule continues); delete (status=DELETED, soft-delete, no future "
                    "fires, history retained). Don't conflate — the API exposes all three "
                    "explicitly."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant U as User\n"
                   "  participant API\n"
                   "  participant DB\n"
                   "  participant W as Worker\n"
                   "  participant T as Target\n"
                   "  U->>API: POST /jobs/{id}/cancel-run/{run_id}\n"
                   "  API->>DB: UPDATE run SET status=CANCEL_REQUESTED\n"
                   "  API-->>U: 202 accepted (best-effort)\n"
                   "  par phase 2\n"
                   "    API->>W: emit cancel msg\n"
                   "    W->>T: adapter-kill (DELETE / k8s del / interrupt)\n"
                   "    T-->>W: killed | already done\n"
                   "    W->>DB: UPDATE run SET status=CANCELLED|SUCCEEDED\n"
                   "  end"
               )),
    ],
)
