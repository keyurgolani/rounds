"""SD-extra — Design a Distributed Logging System (ELK / Splunk-style).

Agent → buffer → forwarder → broker (Kafka) → indexers → tiered storage
(hot Elasticsearch, warm S3+Parquet, cold Glacier). Full-text + faceted
search, sampling, alerting, retention, multi-tenant access control, and
the cardinality-blowup pitfalls that destroy real production logging
clusters.
"""
from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design a Distributed Logging System",
    "Hard",
    "Design a centralized, multi-tenant logging platform in the spirit of ELK (Elasticsearch + "
    "Logstash + Kibana) or Splunk. Tens of thousands of hosts emit structured JSON log lines; the "
    "system must ingest at multi-GB/sec, durably buffer, parse + enrich, index for full-text and "
    "faceted search, tier across hot / warm / cold storage by age, support time-range and regex "
    "queries, raise threshold and anomaly-based alerts, and enforce per-tenant retention, quotas, "
    "and access control — all while staying within a cost envelope that does not grow linearly with "
    "log volume.",
    hints=[
        "Logs are append-only, immutable, time-stamped — pure write-heavy pipeline; reads are bursty.",
        "Agent → local buffer → forwarder → Kafka is the canonical ingest spine. The buffer is "
        "non-negotiable: agents survive broker outages, brokers survive indexer outages.",
        "Structured JSON with a schema (timestamp, level, service, host, trace_id, span_id, msg, "
        "fields{}) — never unstructured text. trace_id is the join key that makes logs useful.",
        "Cardinality blowup is the #1 production failure mode: a field with millions of unique "
        "values (user_id, request_id, full URL with query string) explodes the inverted index.",
        "Hot / warm / cold tiering is what makes the cost story work: ES for last 7d, S3+Parquet "
        "for last 90d (queryable via Athena/Presto), Glacier beyond. 90% of queries hit hot.",
        "Sampling on high-volume hosts at the agent — head-based for ratio control, tail-based "
        "(keep all errors + sample successes) for signal preservation.",
        "Multi-tenant: per-tenant indices/streams + ACLs at query time; quotas at ingest to keep "
        "one noisy tenant from starving others.",
        "Threshold alerts are easy (rules over rolling windows). Anomaly alerts (sudden rate "
        "change, new error message clusters) need a streaming stats job, not a query loop.",
    ],
    constraints=[
        "Ingest: 5-10 GB/sec sustained, 10× spikes during incidents (everyone logs more)",
        "10K+ hosts/services emitting; each emits 10-1000 lines/sec",
        "Hot retention: 7 days searchable in <5s p95; warm: 90 days in <60s; cold: 1+ year",
        "Multi-tenant: 100+ tenants, isolated indices, per-tenant quotas + ACLs",
        "No log loss after agent acks the application (durable buffer)",
        "Cost: storage cost must scale sub-linearly via compression + tiering",
        "Query mix: time-range filter (always) + free-text or regex + facets (service, level, host)",
    ],
    req_func=[
        "Collect structured JSON logs from every host/service via a sidecar/daemon agent",
        "Durably buffer at the agent (disk queue) so app-side acks survive broker outages",
        "Stream into Kafka with per-tenant + per-service topics for backpressure isolation",
        "Parse, validate, enrich (geo-IP, k8s metadata, env), and route to the right index",
        "Index for full-text search + faceted filters (service, level, host, trace_id, custom tags)",
        "Tiered storage: hot (Elasticsearch SSD), warm (S3 + Parquet, queried via Presto/Athena), "
        "cold (Glacier, restore on demand)",
        "Time-range + regex + free-text query API; trace_id and span_id joins to traces",
        "Threshold alerts (rate of ERROR > N over W) and anomaly alerts (new error cluster, "
        "rate change z-score)",
        "Per-tenant retention policies + access control (which users can see which streams)",
        "Sampling at the agent for high-volume hosts — head-based ratio and tail-based "
        "keep-all-errors",
    ],
    req_nonfunc=[
        "Sustained 5-10 GB/sec ingest with 10× burst tolerance",
        "Durability: zero data loss after the agent has fsynced its disk queue",
        "Hot query p95 < 5s for last 7d; warm p95 < 60s for 7-90d",
        "Multi-tenant isolation: noisy neighbor cannot starve others; quotas enforced at ingest",
        "Cost: $/GB-month declines with age via compression + tier transitions",
        "Operability: tenant onboarding self-serve; index lifecycle policies declarative",
        "Security: per-tenant ACLs, field-level redaction for PII, audit log of queries",
    ],
    estimation={
        "log_lines_per_sec": "10M (avg 1KB/line → 10 GB/sec ingest)",
        "daily_volume": "~860 TB/day raw, ~170 TB/day after compression (~5×)",
        "hot_storage_es": "7 days × 170 TB × replication 2 = ~2.4 PB on SSD",
        "warm_storage_s3": "83 days × 170 TB × Parquet (further 3× from columnar) ≈ ~4.7 PB",
        "cold_storage_glacier": "1 year × 170 TB × Glacier compression ≈ ~30 PB at $1/TB-mo",
        "kafka_throughput": "10 GB/sec × RF=3 → 30 GB/sec replicated across ~50 brokers",
        "query_qps": "~5K queries/sec across all tenants; 90% hit hot tier",
        "tenants": "100+ tenants, 99/1 long tail — top 5 tenants are ~80% of volume",
    },
    endpoints=[
        {"method": "POST", "path": "/v1/ingest/{tenant}",
         "description": "Forwarder pushes a batch of JSON log records (mTLS auth)",
         "body": "{records:[{ts,lvl,svc,host,trace_id,msg,fields{}}], compression:gzip|zstd}"},
        {"method": "POST", "path": "/v1/query/{tenant}",
         "description": "Search with time range, free-text, regex, and facets",
         "body": "{from,to, q, filters{svc,lvl,host}, regex?, limit, cursor?, "
                 "facets:[svc,lvl,host]}"},
        {"method": "GET", "path": "/v1/trace/{trace_id}",
         "description": "Pull all log lines stitched to a single trace across services",
         "body": "{tenants?:[...], from?:ts}"},
        {"method": "POST", "path": "/v1/alerts",
         "description": "Create or update an alert rule (threshold or anomaly)",
         "body": "{tenant, name, kind:threshold|anomaly, query, window_s, "
                 "threshold?, sensitivity?, channels:[...]}"},
        {"method": "GET", "path": "/v1/alerts/{tenant}/firing",
         "description": "List currently firing alerts for a tenant",
         "body": "{}"},
        {"method": "POST", "path": "/v1/policies/{tenant}/retention",
         "description": "Set per-stream retention + tier transition rules",
         "body": "{stream, hot_days, warm_days, cold_days, sampling_rate?}"},
        {"method": "POST", "path": "/v1/restore",
         "description": "Restore a cold (Glacier) range to warm so it becomes queryable",
         "body": "{tenant, stream, from, to, expires_in_h}"},
        {"method": "GET", "path": "/v1/quotas/{tenant}",
         "description": "Current ingest + storage usage vs quota",
         "body": "{}"},
    ],
    tables=[
        {"name": "tenants",
         "columns": ["id VARCHAR(64) PK", "name VARCHAR(255)", "ingest_quota_mb_s INT",
                     "storage_quota_tb INT", "default_retention_days INT", "created_at BIGINT"]},
        {"name": "streams",
         "columns": ["tenant_id VARCHAR(64)", "stream VARCHAR(255)", "kafka_topic VARCHAR(255)",
                     "hot_index_alias VARCHAR(255)", "hot_days INT", "warm_days INT",
                     "cold_days INT", "sampling_rate FLOAT",
                     "PRIMARY KEY (tenant_id, stream)"]},
        {"name": "indices",
         "columns": ["index_name VARCHAR(255) PK", "tenant_id VARCHAR(64)", "stream VARCHAR(255)",
                     "from_ts BIGINT", "to_ts BIGINT", "tier VARCHAR(16)",
                     "doc_count BIGINT", "size_bytes BIGINT", "shard_count INT"]},
        {"name": "alerts",
         "columns": ["id BIGINT PK", "tenant_id VARCHAR(64)", "name VARCHAR(255)",
                     "kind VARCHAR(16)", "query TEXT", "window_s INT",
                     "threshold DOUBLE", "sensitivity DOUBLE",
                     "channels TEXT", "state VARCHAR(16)", "last_eval_at BIGINT"]},
        {"name": "audit_log",
         "columns": ["id BIGINT PK", "ts BIGINT", "tenant_id VARCHAR(64)", "user_id VARCHAR(128)",
                     "action VARCHAR(64)", "query TEXT", "rows_returned INT",
                     "ip VARCHAR(45)"]},
        {"name": "schema_registry",
         "columns": ["tenant_id VARCHAR(64)", "stream VARCHAR(255)", "version INT",
                     "schema_json TEXT", "created_at BIGINT",
                     "PRIMARY KEY (tenant_id, stream, version)"]},
        {"name": "acl_bindings",
         "columns": ["tenant_id VARCHAR(64)", "stream VARCHAR(255)", "principal VARCHAR(255)",
                     "permission VARCHAR(16)",
                     "PRIMARY KEY (tenant_id, stream, principal)"]},
    ],
    indexes=[
        "(tenant_id, stream, from_ts) on indices for query planner tier resolution",
        "(tenant_id, ts DESC) on audit_log for tenant audit dashboards",
        "(state, last_eval_at) on alerts for the alert evaluator's worklist",
        "(tier, to_ts) on indices for ILM (lifecycle) tier-transition jobs",
        "ES inverted index on msg + keyword fields (svc, lvl, host, trace_id)",
    ],
    hld_desc=(
        "Hosts run a lightweight collection agent (Fluent Bit / Vector style) that tails app log "
        "files and structured stdout. The agent applies an on-disk buffer (RocksDB or a simple "
        "ring-file) so producer acks survive broker outages, then ships via mTLS to a regional "
        "forwarder fleet. Forwarders are stateless: they batch, compress (zstd), and produce to "
        "Kafka with per-tenant + per-service topics for backpressure isolation. From Kafka, a "
        "stream-processing tier (Flink / Kafka Streams) parses, validates against the per-stream "
        "schema, enriches (geo-IP, k8s pod metadata, environment), drops or samples, and routes: "
        "(1) full records into Elasticsearch hot indices, (2) the same records as Parquet files "
        "to S3 for the warm tier, (3) running aggregates into a metrics store for the alert "
        "engine. Index Lifecycle Management (ILM) ages indices: hot (NVMe SSD, queryable in "
        "seconds) → warm (S3+Parquet, queried via Presto/Athena) → cold (Glacier, restore on "
        "demand). A query gateway routes queries to the right tier(s) based on time range, "
        "merges results, applies tenant ACLs, and audits. The alert engine subscribes to the "
        "Kafka stream directly for low-latency threshold checks and runs windowed anomaly "
        "detectors (rate change, new-cluster detection via log-template fingerprints)."
    ),
    hld_components=[
        {"name": "Collection Agent", "role": "Sidecar/daemon: tail, parse, sample, disk-buffer, ship"},
        {"name": "Forwarder Fleet", "role": "Stateless mTLS endpoint; batch + compress → Kafka"},
        {"name": "Kafka (Per-tenant Topics)", "role": "Durable buffer between forwarder and indexers"},
        {"name": "Stream Processor", "role": "Flink/Kafka Streams: parse, enrich, validate, route"},
        {"name": "Schema Registry", "role": "Per-tenant + per-stream JSON schema versioning"},
        {"name": "Hot Indexer (Elasticsearch)", "role": "Inverted index for last 7d on SSD"},
        {"name": "Warm Storage (S3 + Parquet)", "role": "Columnar files for 7-90d, queried by Presto"},
        {"name": "Cold Storage (Glacier)", "role": "Cheap archive for 90d-1y+; restore-to-warm on demand"},
        {"name": "Query Gateway", "role": "Routes by time range, merges tier results, applies ACL"},
        {"name": "Alert Engine", "role": "Threshold + anomaly evaluator on the streaming pipeline"},
        {"name": "ILM Controller", "role": "Tier transitions, deletion, restore orchestration"},
        {"name": "Tenant Service", "role": "Quotas, retention policies, ACLs, audit"},
        {"name": "UI / API", "role": "Kibana-style dashboards + programmatic query API"},
    ],
    detailed_design={
        "agent_buffer_forwarder": (
            "Agent runs as a per-host daemon (Fluent Bit, Vector) or sidecar in Kubernetes. "
            "Tails container stdout / log files, parses each line as JSON (rejects malformed → "
            "DLQ), enriches with host + container metadata cached locally. Disk buffer is a "
            "bounded ring (e.g., 1 GB per host) — agent fsyncs every batch. The agent "
            "acknowledges the application only after fsync, so a broker outage never loses data. "
            "Forwarders are stateless: terminate mTLS, validate tenant token, batch records by "
            "tenant + stream, compress with zstd (10×+ on JSON), and produce to Kafka with "
            "ack=all + idempotent producer. Forwarder failure has no local state to recover."
        ),
        "kafka_spine": (
            "Per-tenant + per-stream topics (or partitioned per-tenant if tenant count is huge) "
            "with replication factor 3, ack=all, min.insync.replicas=2. Partition key = "
            "host_id (so per-host order is preserved for log tailing). Retention 24-72h on "
            "Kafka itself — long enough to recover from indexer outages without making Kafka "
            "the system of record. A dead-letter topic per tenant catches schema-validation "
            "failures so they're visible without blocking the main flow."
        ),
        "structured_json_schema": (
            "Required fields: ts (epoch ms), lvl (DEBUG|INFO|WARN|ERROR|FATAL), svc (service "
            "name), host, trace_id, span_id, msg (the human message). Optional fields{} for "
            "free-form key-value enrichment, but with strict cardinality budgets per field. "
            "Schema is registered per (tenant, stream) and versioned — backward-compatible adds "
            "are auto-accepted; breaking changes require explicit migration. trace_id is the "
            "spine that joins logs to distributed traces (OpenTelemetry) — a query for one "
            "trace_id pulls the full request's logs across every service."
        ),
        "hot_warm_cold_tiering": (
            "Hot: Elasticsearch on NVMe SSD, time-bucketed indices (logs-{tenant}-{date}), "
            "force-merge to 1 segment after rollover, 1 primary + 1 replica. Daily index "
            "rotation; 7 daily indices live. Warm: after 7 days, ILM exports the index to S3 "
            "as Parquet (columnar, snappy/zstd compressed, ~3× smaller than ES bytes), "
            "partitioned by date + tenant. Queried via Presto / Athena / Trino with predicate "
            "pushdown — slower than ES (seconds → minutes) but 10× cheaper. Cold: after 90 days "
            "Parquet objects transition to Glacier (or Glacier Deep Archive). Restore-to-warm "
            "is a user-initiated operation that pays a thaw cost and a few hours of latency."
        ),
        "search_indexing": (
            "Elasticsearch inverted index on msg (analyzed, full-text) + keyword fields "
            "(svc, lvl, host, trace_id). Custom analyzer tokenizes on whitespace and "
            "punctuation but preserves dotted identifiers. Numeric fields use BKD trees for "
            "range queries. Faceted search uses doc_values (columnar) to aggregate per facet "
            "without scanning rows. Regex queries are best-effort — rooted patterns are fast, "
            "open-ended .* is rate-limited. Free-text query expands stop-word-aware and ranks "
            "by recency, not relevance (logs are not documents)."
        ),
        "sampling_strategy": (
            "Two modes, configurable per stream. Head-based: agent flips a coin per record at a "
            "ratio (e.g., keep 10% of INFO, 100% of ERROR). Cheapest, but loses correlated "
            "signal. Tail-based: agent buffers a request's records (keyed by trace_id) for a "
            "small window; if any record is ERROR, keep all; otherwise sample at the head "
            "ratio. Tail-based gives full context for failed requests at a fraction of the "
            "cost. High-volume hosts default to 10% head + tail-based ERROR retention; "
            "low-volume hosts ship 100%."
        ),
        "query_engine": (
            "Query gateway parses the request, resolves which tier(s) cover the time range, "
            "and dispatches: hot only (most common, last 7d), hot+warm (split scatter-gather), "
            "warm only, or warm + restore-from-cold (async with status polling). Merges "
            "results, applies tenant ACLs (rows the user can't see are filtered before "
            "return), enforces per-query result caps, and writes an audit row. Pagination is "
            "cursor-based (last seen ts + doc_id) — never offset, which doesn't scale. Long "
            "regex / open-ended scans are run on Presto over warm Parquet, not on hot ES."
        ),
        "alerting": (
            "Threshold alerts: rule like 'count(lvl=ERROR, svc=checkout) over 5m > 50'. "
            "Evaluator subscribes to the Kafka stream, maintains rolling counters per rule in "
            "RocksDB, fires on threshold crossing. Latency: <30s end-to-end. Anomaly alerts: "
            "(1) z-score on rate (current rate vs trailing 7-day baseline at same time-of-day) "
            "and (2) new-cluster detection — log lines are fingerprinted by replacing variable "
            "tokens with placeholders (Drain3 algorithm), and a never-before-seen template "
            "spikes a 'new error type' alert. Both run as Flink jobs over the streaming source."
        ),
        "retention_and_lifecycle": (
            "Per-stream policy: hot_days, warm_days, cold_days. ILM controller runs a daily "
            "job: roll hot indices, export to Parquet on warm, transition warm objects to cold "
            "after warm_days, delete cold after cold_days. Deletion is hard delete from S3 + "
            "Glacier; no soft-delete tombstones (compliance). Tenant-level overrides for "
            "regulated workloads (HIPAA = 6 years, etc.). ILM jobs are idempotent and "
            "checkpointed — re-running a partial day is safe."
        ),
        "cardinality_blowup_pitfalls": (
            "The single biggest production failure mode. A field like full_url with the query "
            "string, or user_id, or request_id put into a high-cardinality keyword field, "
            "explodes the inverted index and OOMs ES. Mitigations: (1) field cardinality "
            "budgets in the schema — fields with >10K distinct values rejected by validation; "
            "(2) URL templating: strip query string and replace path IDs with :id placeholders "
            "before indexing; (3) put high-cardinality fields in fields{} as text-only (full-"
            "text search yes, faceted aggregation no); (4) trace_id is a known-cardinality "
            "exception (one per request) and routed to a dedicated keyword index segment with "
            "BKD-style time partitioning. Ops dashboard on cardinality-per-field is the early "
            "warning."
        ),
        "multi_tenant_access_control": (
            "Each tenant has isolated Kafka topics + ES index pattern (logs-{tenant}-*) + S3 "
            "prefix. Ingest auth: forwarder validates a per-tenant mTLS cert; quotas enforced "
            "at the forwarder by tenant_id (token bucket on bytes/sec). Query auth: tenant + "
            "user identity from OAuth/OIDC; ACL bindings map (user → streams → permission). "
            "Field-level redaction: PII fields (email, ssn, etc.) marked in schema; query path "
            "applies redaction unless the caller has 'pii:read'. Every query writes an audit "
            "row (who, what, when, rows returned). Cross-tenant queries are rejected at the "
            "gateway."
        ),
        "cost_envelope": (
            "Storage cost dominates. Naive ES-only retention of all data for a year would be "
            "~60 PB on SSD = millions of dollars/month. Tiering brings that down by ~50×. "
            "Compute cost: Flink + ES indexers scale linearly with ingest, capped by sampling. "
            "Egress is mostly internal (within VPC) and cheap. A typical operating ratio: "
            "30% Kafka/Flink/ES compute, 50% storage (mostly warm/cold), 20% query compute "
            "(Presto/Athena pay-per-scan)."
        ),
    },
    trade_offs=[
        {"option": "Push (agent → ingest endpoint) vs pull (collector scrapes hosts)",
         "for_push": "Lower per-line latency; agent owns retry + buffering",
         "for_pull": "Centralized control of rate; works for hosts behind NAT",
         "recommendation": "Push for logs (latency-sensitive, durable buffer at edge); "
                           "pull is the metrics pattern (Prometheus), wrong for logs."},
        {"option": "Single all-tenants ES cluster vs per-tenant clusters",
         "for_single": "Cheaper per GB, easier ops, better hot-data utilization",
         "for_per_tenant": "Strong isolation; one tenant's bad query can't take others down",
         "recommendation": "Single cluster with per-tenant index allocation + circuit "
                           "breakers for the long tail; dedicated clusters only for top-3 "
                           "tenants where blast radius justifies the cost."},
        {"option": "Elasticsearch hot tier vs ClickHouse / Loki",
         "for_es": "Mature full-text, faceting, ecosystem, Kibana",
         "for_ch_loki": "10× cheaper at scale (columnar / label-indexed), no inverted index",
         "recommendation": "ES for the freshness + free-text search story; Loki/ClickHouse "
                           "for label-driven workloads where free-text isn't the primary need."},
        {"option": "Index every line vs sample at the agent",
         "for_index_all": "No data loss; full-fidelity for incident postmortems",
         "for_sample": "10× lower cost; tail-based keeps all errors anyway",
         "recommendation": "Sample by default for high-volume / non-error lines; full-fidelity "
                           "for ERROR + audit + compliance streams."},
        {"option": "Hot-only retention (long ES) vs aggressive tiering",
         "for_long_hot": "Every query is fast; no Presto / restore cognitive load",
         "for_tier": "10-50× cheaper; matches the read distribution (90% hits last 7d)",
         "recommendation": "Aggressive tiering — anything >7-14 days lives on S3+Parquet; "
                           "1y+ in Glacier. Cost is the constraint; 99% of queries don't care."},
        {"option": "Synchronous vs asynchronous alert evaluation",
         "for_sync": "Run alerts as queries on the index — simple, reuses query layer",
         "for_async": "Stream evaluator is faster (subseconds) and doesn't load ES",
         "recommendation": "Async stream evaluator for threshold + anomaly; query-based "
                           "fallback only for ad-hoc one-off rules."},
    ],
    tips=[
        "Lead with: agents disk-buffer; the buffer is what makes the app's log call "
        "non-blocking and crash-safe. Most candidates skip this and treat ingest as a "
        "fire-and-forget HTTP POST — wrong.",
        "Cardinality blowup is the fail-mode story. Mention field cardinality budgets, URL "
        "templating, and what happens when a junior dev indexes user_id as a keyword.",
        "Tiered storage with a query gateway that routes by time range is THE cost story. "
        "If you don't say 'hot/warm/cold,' you didn't answer the cost question.",
        "trace_id is the join-key magic — it stitches logs to distributed traces. Senior "
        "candidates always mention it.",
        "Tail-based sampling (keep all if any record is ERROR) is a senior signal vs "
        "naive head sampling.",
        "Multi-tenant: quotas at ingest, ACLs at query, audit log on every read. All three "
        "are needed; don't say 'multi-tenant' and only mean indices.",
        "For anomaly detection, mention log-template fingerprinting (Drain3) — most "
        "candidates only know about static thresholds.",
        "ELK isn't the only answer. Loki + ClickHouse are the modern cost-driven alternatives "
        "and a senior candidate engages with that trade-off.",
    ],
    thought_process=[
        "1. Clarify: GB/sec ingest, multi-tenant, 7d hot + 90d warm + 1y cold, full-text + "
        "faceted search, alerts.",
        "2. Estimate: 10 GB/sec × 86400s = 860 TB/day raw → ~170 TB/day compressed.",
        "3. Pipeline: agent (disk buffer) → forwarder (mTLS, batch, zstd) → Kafka (per-tenant "
        "topics, RF=3) → stream processor (parse, enrich, route) → ES + S3.",
        "4. Schema: structured JSON with required ts/lvl/svc/host/trace_id, plus enrichment.",
        "5. Sampling: head-based ratio + tail-based keep-errors at the agent; high-volume "
        "hosts default to 10%.",
        "6. Tiering: ES hot (7d, NVMe), S3+Parquet warm (90d, Presto/Athena), Glacier cold "
        "(1y+, restore-on-demand).",
        "7. Search: ES inverted index on msg + keywords; regex rate-limited; faceted via "
        "doc_values; trace queries hit a dedicated trace_id index.",
        "8. Alerts: stream evaluator on Kafka for thresholds; Flink anomaly job for rate-"
        "change z-score and new-template detection (Drain3).",
        "9. Multi-tenancy: per-tenant Kafka topics + ES index patterns + ACLs + per-tenant "
        "quotas + audit log on every query.",
        "10. Cardinality: schema-enforced field cardinality budgets; URL templating; "
        "high-cardinality fields go to text-only, not keyword.",
        "11. Cost: tiering brings storage from $X to $X/50; sampling drops compute by 10×; "
        "single ES cluster with per-tenant allocation beats per-tenant clusters.",
    ],
    tags=["logging", "observability", "search", "ingestion", "scale"],
    arch_nodes=[
        {"id": "app", "label": "App + Agent", "type": "client"},
        {"id": "buf", "label": "On-Disk Buffer", "type": "queue"},
        {"id": "fwd", "label": "Forwarder Fleet", "type": "server"},
        {"id": "kafka", "label": "Kafka (per-tenant topics)", "type": "queue"},
        {"id": "flink", "label": "Stream Processor", "type": "service"},
        {"id": "schema", "label": "Schema Registry", "type": "service"},
        {"id": "es", "label": "Elasticsearch (Hot)", "type": "database"},
        {"id": "s3", "label": "S3 Parquet (Warm)", "type": "database"},
        {"id": "glacier", "label": "Glacier (Cold)", "type": "database"},
        {"id": "ilm", "label": "ILM Controller", "type": "service"},
        {"id": "qg", "label": "Query Gateway", "type": "lb"},
        {"id": "presto", "label": "Presto / Athena", "type": "service"},
        {"id": "alert", "label": "Alert Engine", "type": "service"},
        {"id": "tenant", "label": "Tenant + ACL Service", "type": "service"},
        {"id": "ui", "label": "UI / API (Kibana)", "type": "client"},
    ],
    arch_edges=[
        {"source": "app", "target": "buf", "label": "fsync"},
        {"source": "buf", "target": "fwd", "label": "mTLS push"},
        {"source": "fwd", "target": "kafka", "label": "produce ack=all"},
        {"source": "kafka", "target": "flink", "label": "consume"},
        {"source": "flink", "target": "schema", "label": "validate"},
        {"source": "flink", "target": "es", "label": "index hot"},
        {"source": "flink", "target": "s3", "label": "Parquet warm"},
        {"source": "flink", "target": "alert", "label": "stream eval"},
        {"source": "ilm", "target": "es", "label": "rollover"},
        {"source": "ilm", "target": "s3", "label": "tier age-out"},
        {"source": "ilm", "target": "glacier", "label": "transition"},
        {"source": "ui", "target": "qg", "label": "query"},
        {"source": "qg", "target": "tenant", "label": "ACL + audit"},
        {"source": "qg", "target": "es", "label": "hot path"},
        {"source": "qg", "target": "presto", "label": "warm path"},
        {"source": "presto", "target": "s3"},
        {"source": "qg", "target": "glacier", "label": "restore-on-demand"},
        {"source": "alert", "target": "ui", "label": "fire"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant App\n"
        "  participant Agent\n"
        "  participant Fwd as Forwarder\n"
        "  participant K as Kafka\n"
        "  participant Flink\n"
        "  participant ES\n"
        "  participant S3\n"
        "  participant QG as Query GW\n"
        "  participant User\n"
        "  App->>Agent: log line (JSON)\n"
        "  Agent->>Agent: enrich + sample\n"
        "  Agent->>Agent: fsync to disk buffer\n"
        "  Agent-->>App: ack\n"
        "  Agent->>Fwd: batch (zstd, mTLS)\n"
        "  Fwd->>K: produce (ack=all, RF=3)\n"
        "  K-->>Fwd: committed\n"
        "  Flink->>K: consume\n"
        "  Flink->>Flink: parse + validate + enrich\n"
        "  Flink->>ES: bulk index (hot)\n"
        "  Flink->>S3: Parquet append (warm)\n"
        "  User->>QG: search (last 24h)\n"
        "  QG->>QG: ACL + tenant resolve\n"
        "  QG->>ES: hot query\n"
        "  ES-->>QG: hits + facets\n"
        "  QG-->>User: results\n"
        "  QG->>QG: audit log row"
    ),
    er_diagram=(
        "erDiagram\n"
        "  TENANT ||--o{ STREAM : owns\n"
        "  STREAM ||--o{ INDEX : produces\n"
        "  STREAM ||--|| SCHEMA : versioned\n"
        "  TENANT ||--o{ ALERT : configures\n"
        "  TENANT ||--o{ ACL : grants\n"
        "  TENANT ||--o{ AUDIT : logs\n"
        "  TENANT { string id PK\n string name\n int ingest_quota_mb_s\n int retention_days }\n"
        "  STREAM { string tenant_id\n string stream\n string kafka_topic\n int hot_days\n "
        "int warm_days\n int cold_days\n float sampling_rate }\n"
        "  INDEX { string index_name PK\n string tier\n bigint from_ts\n bigint to_ts\n "
        "bigint doc_count\n bigint size_bytes }\n"
        "  ALERT { bigint id PK\n string kind\n string query\n int window_s\n double threshold }\n"
        "  AUDIT { bigint id PK\n bigint ts\n string user_id\n string action\n int rows_returned }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[App emits JSON log] --> B[Agent enrich + sample]\n"
        "  B --> C[fsync local buffer]\n"
        "  C --> D[Forwarder batch + zstd]\n"
        "  D --> E[Kafka per-tenant topic]\n"
        "  E --> F[Stream processor]\n"
        "  F --> G{Schema valid?}\n"
        "  G -->|No| DLQ[DLQ topic]\n"
        "  G -->|Yes| H[Enrich + route]\n"
        "  H --> I[ES hot index]\n"
        "  H --> J[S3 Parquet warm]\n"
        "  H --> K[Stream alert eval]\n"
        "  I -. ILM 7d .-> J\n"
        "  J -. ILM 90d .-> L[Glacier cold]\n"
        "  M[Query] --> N{Time range tier?}\n"
        "  N -->|<=7d| I\n"
        "  N -->|7-90d| O[Presto on S3]\n"
        "  O --> J\n"
        "  N -->|>90d| P[Restore-on-demand]\n"
        "  P --> L"
    ),
    tradeoff_title="Hot-only retention vs hot/warm/cold tiered storage",
    tradeoff_options=[
        {"label": "Hot-only (Elasticsearch for full retention)",
         "description": "Keep every log line in Elasticsearch on SSD for the full retention "
                        "period (e.g., 1 year).",
         "pros": ["Every query has the same fast path — no tier-routing logic",
                 "Operationally simpler — one storage system, one query engine",
                 "No restore-from-cold UX, no Presto cognitive load on users"],
         "cons": ["Storage cost is 10-50× more than tiered (SSD vs S3 vs Glacier)",
                 "Inverted index size dominates RAM — JVM heap pressure scales with retention",
                 "Mostly wasted: 90%+ of queries hit the last 7 days"]},
        {"label": "Tiered hot / warm / cold",
         "description": "ES for last 7d (hot), S3+Parquet queried via Presto/Athena for 7-90d "
                        "(warm), Glacier for 90d-1y+ (cold) with restore-on-demand.",
         "pros": ["Storage cost scales sub-linearly — typical 50× reduction vs hot-only",
                 "Hot tier stays small + fast — query latency for 90% of traffic stays <5s",
                 "Cold-tier compression (Glacier Deep Archive) makes multi-year retention "
                 "affordable for compliance"],
         "cons": ["Query gateway must route by time range and merge results across tiers",
                 "Warm queries are seconds-to-minutes — slower than hot",
                 "Cold restore is hours of latency + thaw fees; user expectation management",
                 "ILM controller must orchestrate transitions reliably and idempotently"]},
    ],
    tradeoff_rec="Tiered. The cost delta is 10-50× and the query distribution overwhelmingly "
                 "favors hot. Treat warm and cold as backstops for incident postmortems and "
                 "compliance, not the everyday path.",
    senior_topics=[
        _topic("agent-buffer-and-back-pressure",
               "Agent Disk Buffer: Why Logging Calls Must Be Non-Blocking and Crash-Safe",
               "The agent's local buffer is the boundary that decouples application liveness "
               "from the log pipeline's liveness. Done right, an app keeps logging through "
               "broker outages without blocking; done wrong, log calls become a synchronous "
               "dependency on a remote cluster.",
               [
                   ("Why the buffer must be on disk",
                    "An in-memory buffer loses data on agent crash or host reboot — and hosts "
                    "do reboot. A disk-backed ring (1-10 GB) survives crashes and broker "
                    "outages of hours. The agent fsyncs each batch and only acks the app "
                    "after the fsync — that's the durability contract the app relies on."),
                   ("Block, don't drop, when the buffer fills",
                    "If the buffer is full and the broker is still down, the agent must block "
                    "subsequent writes (or apply backpressure to the app's logger) — silently "
                    "dropping is a debugging nightmare. Loggers expose this as a bounded queue "
                    "with overflow policy: block, drop-oldest, or drop-newest, with metrics."),
                   ("Forwarder is stateless on purpose",
                    "All state lives at the agent. Forwarders are pure batch-compress-produce. "
                    "If a forwarder dies, the agent's next connection lands on another. No "
                    "drain, no failover protocol — that's the simplification."),
                   ("ack=all + idempotent producer end-to-end",
                    "Forwarder produces with ack=all + idempotent (PID + seq) so retries on "
                    "transient broker failure don't dup. Agent retries until ack from "
                    "forwarder; forwarder retries until ack from Kafka. Each hop is "
                    "at-least-once with dedup, end-to-end exactly-once at the broker."),
                   ("Crash-replay from the buffer",
                    "On agent restart, replay the buffer from the last-acked offset. Per-batch "
                    "checksums catch torn writes. The agent treats the buffer as a tiny "
                    "single-host Kafka."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant App\n  participant Agent\n  participant Disk\n"
                   "  participant Fwd\n  participant K as Kafka\n"
                   "  App->>Agent: log()\n"
                   "  Agent->>Disk: append + fsync\n"
                   "  Disk-->>Agent: ok\n"
                   "  Agent-->>App: returned (non-blocking)\n"
                   "  Note over Agent,Fwd: Async ship loop\n"
                   "  Agent->>Fwd: batch\n"
                   "  Fwd->>K: produce (ack=all)\n"
                   "  K-->>Fwd: committed\n"
                   "  Fwd-->>Agent: ack\n"
                   "  Agent->>Disk: advance read cursor"
               )),
        _topic("structured-json-and-trace-id",
               "Structured JSON Schema and trace_id: The Join Key That Makes Logs Useful",
               "Plain-text logs are useless at scale. Structured JSON with a versioned schema "
               "and a request-scoped trace_id is what lets a logging system actually answer "
               "questions instead of being a haystack search.",
               [
                   ("Required fields",
                    "ts (epoch ms), lvl (enum), svc (service name), host, trace_id, span_id, "
                    "msg. These are non-optional; ingest validation rejects records missing "
                    "any of them. The dead-letter topic catches malformed lines so they're "
                    "visible without blocking the main flow."),
                   ("trace_id propagation via OpenTelemetry",
                    "Each request gets a trace_id at the edge (gateway). It's propagated in "
                    "headers (W3C traceparent) on every downstream call. Each service's logger "
                    "reads the active trace_id from its tracer context and stamps every log "
                    "line. Result: querying for a trace_id pulls the full distributed-request "
                    "log timeline across every service involved."),
                   ("Schema evolution + registry",
                    "Per (tenant, stream) schema is registered with a version. Backward-"
                    "compatible adds (new optional fields) auto-promote. Breaking changes "
                    "(rename, type change) require a new version and a dual-write window. The "
                    "registry is queried at parse time; unknown fields are buffered in fields{}, "
                    "not dropped, so future schemas can promote them."),
                   ("Field-level types and cardinality budgets",
                    "Every field has a type (string, keyword, long, double, ip, geo, bool) and "
                    "a cardinality budget. Keyword fields that exceed the budget at ingest are "
                    "demoted to text-only (full-text searchable, not faceted). The schema is "
                    "where you prevent cardinality blowups, not the indexer."),
                   ("Why timestamps are server-validated",
                    "Hosts have skewed clocks. Agent stamps record ts from local clock, "
                    "forwarder also stamps ingest_ts from server clock. Records arriving with "
                    "ts in the far future are rebucketed to ingest_ts to prevent index bloat "
                    "in nonsensical future buckets — a real production gotcha."),
               ]),
        _topic("hot-warm-cold-tiering-and-ilm",
               "Hot / Warm / Cold Tiering and Index Lifecycle Management",
               "The cost story of any log system at scale is tiering. Inverted indices on SSD "
               "for the freshest data, columnar Parquet on object storage for medium-age, "
               "and archival storage for long retention. ILM is the controller that orchestrates "
               "the transitions.",
               [
                   ("Hot tier: Elasticsearch on SSD",
                    "Daily indices (logs-{tenant}-YYYY-MM-DD) with 1 primary + 1 replica on "
                    "NVMe. Force-merge to 1 segment after rollover for query speed. Query p95 "
                    "in seconds. Holds 7 days of data; that's where 90% of traffic lands."),
                   ("Warm tier: S3 + Parquet + Presto/Athena",
                    "On rollover from hot, the daily index is exported as Parquet partitioned "
                    "by date + tenant + service. Parquet's columnar layout + zstd compression "
                    "is ~3× smaller than ES on-disk bytes. Queried by Presto / Athena / Trino "
                    "with predicate pushdown — query latency seconds-to-minutes, cost per byte "
                    "10× lower than ES."),
                   ("Cold tier: Glacier or Glacier Deep Archive",
                    "After warm_days, Parquet objects transition to Glacier via S3 Lifecycle. "
                    "Cost ~$1/TB-month for Deep Archive. Restore is hours of thaw + a per-GB "
                    "fee. Restore-on-demand is a user-initiated workflow that puts data into "
                    "warm temporarily for query."),
                   ("ILM controller orchestration",
                    "Daily cron or on-time-trigger that: rolls hot indices, runs the export "
                    "job to Parquet, transitions warm objects on age, deletes cold past "
                    "retention. Idempotent: each step is keyed by (index_name, target_tier) "
                    "and skipped if already transitioned. Failures don't stall the pipeline — "
                    "they leave data on the previous tier and retry."),
                   ("Query routing across tiers",
                    "Query gateway resolves time range → tier set: 0-7d hot, 7-90d warm, "
                    ">90d cold. Cross-tier queries scatter-gather and merge-sort by ts. UI "
                    "warns 'this range crosses tiers, expected latency Y'. Cold queries return "
                    "a 202 with a polling URL — the user can come back when the restore "
                    "finishes."),
               ],
               diagram=(
                   "graph LR\n"
                   "  HOT[Elasticsearch\\n7d SSD\\nfast queries] -- ILM 7d --> WARM[S3 Parquet\\n"
                   "90d\\nPresto/Athena]\n"
                   "  WARM -- ILM 90d --> COLD[Glacier\\n1y+\\nrestore-on-demand]\n"
                   "  Q[Query Gateway] --> HOT\n  Q --> WARM\n  Q -. restore .-> COLD"
               )),
        _topic("cardinality-blowup",
               "Cardinality Blowup: The #1 Production Failure Mode",
               "A single misconfigured field can take down an entire Elasticsearch cluster. "
               "Cardinality blowup happens when a field with millions of unique values is "
               "indexed as a faceted keyword — the inverted index explodes, JVM heap "
               "saturates, and queries time out for everyone.",
               [
                   ("How it happens",
                    "A developer adds fields.user_id or fields.request_id to their log line. "
                    "Schema doesn't gate cardinality. The dynamic mapper indexes it as a "
                    "keyword. Each value gets an entry in the inverted index per day. With "
                    "100M unique users in a daily index, the term dictionary OOMs. The whole "
                    "cluster degrades."),
                   ("Field cardinality budgets in the schema",
                    "Every keyword field declares max_cardinality (e.g., svc: 10K, host: "
                    "100K, lvl: 10). Stream processor tracks distinct values via "
                    "HyperLogLog per field per day; when threshold approaches, the field is "
                    "demoted to text-only for the rest of that day, alert fires."),
                   ("URL templating",
                    "URLs are the classic offender — /users/12345/posts/67890?session=abc has "
                    "infinite distinct values. Template at ingest: strip query string, replace "
                    "numeric IDs with :id placeholders → /users/:id/posts/:id. Dramatically "
                    "reduces cardinality while preserving the structural shape for analysis."),
                   ("Use text fields for high-cardinality strings",
                    "Free-text fields (text type) store an inverted index over tokens, not "
                    "values. Querying 'find logs where msg contains user_id 12345' works on "
                    "text fields without blowing up cardinality. Faceted aggregation doesn't, "
                    "and that's the right trade-off."),
                   ("trace_id is the deliberate exception",
                    "trace_id is high-cardinality but its query pattern is trivially "
                    "point-lookup — find all records for one trace_id. Indexed in a "
                    "dedicated keyword field, partitioned by hour — tiny term dictionary "
                    "per partition, fast lookups. A focused exception that proves the rule."),
                   ("Cardinality dashboard as early warning",
                    "Per-field, per-tenant, per-day distinct-value counts with HLL. Alert "
                    "when a field grows >2× day-over-day or approaches its budget. Catches "
                    "the bad change before the cluster goes down."),
               ]),
        _topic("sampling-strategies",
               "Sampling: Head-Based vs Tail-Based and the Cost-Signal Trade-off",
               "At 10 GB/sec ingest, you cannot afford to keep every line. Sampling drops "
               "volume by 5-10× while preserving the parts that matter. The hard part is "
               "deciding what matters; the answer is rarely 'random'.",
               [
                   ("Head-based sampling",
                    "Per-line coin flip at the agent: keep with probability p. Fastest, "
                    "stateless, easy to reason about. Loses correlated context — a sampled "
                    "ERROR's preceding INFOs are mostly gone, so the postmortem is "
                    "harder."),
                   ("Tail-based sampling",
                    "Buffer all records for a trace_id in a small window (a few seconds). At "
                    "the end of the window: if any record is ERROR (or matches a 'keep' "
                    "predicate), keep them all. Otherwise sample at the head ratio. Vastly "
                    "better signal-to-noise — full context for failures at a fraction of "
                    "the cost."),
                   ("Always keep ERROR/FATAL",
                    "Hard rule: ERROR and FATAL are never sampled. Audit-log streams are "
                    "never sampled. Compliance streams are never sampled. Sampling applies "
                    "to INFO/DEBUG firehose where most volume lives."),
                   ("Per-stream and per-host configuration",
                    "Sampling rate is a per-stream policy. High-volume hosts (e.g., "
                    "high-RPS edge servers) default to 10% INFO + tail-based; low-volume "
                    "hosts ship 100%. Override per-tenant for incident response (turn "
                    "sampling off for a service while debugging)."),
                   ("Where the sampling decision lives",
                    "At the agent, before the line ships. Sampling at the indexer is too "
                    "late — you've already paid the network + Kafka + parse cost. Pushing "
                    "the decision to the edge is what makes sampling cheap."),
               ]),
        _topic("alerting-threshold-and-anomaly",
               "Threshold Alerts vs Anomaly Detection on Logs",
               "Alerts on logs come in two flavors: static thresholds (which any junior can "
               "write) and anomaly detection (which is where senior signal lives). Both run "
               "as streaming evaluators, not query-loop polls.",
               [
                   ("Static threshold alerts",
                    "Rule: count(lvl=ERROR, svc=checkout) over 5m > 50. Evaluator subscribes "
                    "to the Kafka stream, maintains a rolling counter per rule keyed by "
                    "(rule_id, tumbling_window). Window closes → check threshold → fire if "
                    "exceeded. Latency end-to-end < 30s. Stateful in RocksDB so windows "
                    "survive restart."),
                   ("Rate-change anomaly detection",
                    "Z-score on current rate vs trailing 7-day baseline at same time-of-day "
                    "and day-of-week. Fires when current is N standard deviations above "
                    "(or below — a sudden DROP in error rate is suspicious too). Handles "
                    "diurnal and weekly seasonality without per-rule tuning."),
                   ("New-cluster detection (Drain3)",
                    "Log lines are fingerprinted by replacing variable tokens with "
                    "placeholders ('NullPointerException at User.java:142' → '<exc> at "
                    "<class>:<line>'). Drain3 maintains a tree of templates; an unseen "
                    "template that fires repeatedly is a 'new error type' alert — typically "
                    "a deploy regression or new failure mode."),
                   ("Where alerts run",
                    "Stream evaluator (Flink job) consumes the same Kafka stream as "
                    "indexers. Alerts fire seconds after the underlying event. Critically, "
                    "alerts do NOT poll Elasticsearch — that path is too slow and would "
                    "amplify ES load during an incident (when alerts spike + queries spike "
                    "simultaneously)."),
                   ("Alert routing and dedup",
                    "Fired alerts go to a router (PagerDuty, Slack, email) per rule's "
                    "channels. Dedup window per rule prevents flapping. Alert state machine: "
                    "OK → PENDING → FIRING → ACKED → OK with hysteresis on recovery."),
               ]),
        _topic("multi-tenant-isolation-and-cost",
               "Multi-Tenant Isolation: Quotas, ACLs, Audit, and the Long-Tail Cost Story",
               "Multi-tenant logging means one cluster, many customers, with strict isolation "
               "semantics — noisy neighbors, cost attribution, access control, audit. The hard "
               "parts are at the edges: ingest quotas and query-path ACLs.",
               [
                   ("Ingest quotas at the forwarder",
                    "Per-tenant token bucket on bytes/sec at the forwarder layer. When a "
                    "tenant exceeds quota: forwarder returns 429 with retry-after; agent "
                    "applies its own backpressure (slow producer instead of dropping). One "
                    "tenant's spike doesn't fill Kafka and starve the others."),
                   ("Storage quotas and accounting",
                    "Per-tenant storage usage tracked by the ILM controller. Approaching "
                    "quota → tenant notified, default action is to shorten retention "
                    "automatically (oldest first) or reject new writes. Cost-center "
                    "attribution from index size + tier × $/GB-month is the basis for "
                    "chargeback."),
                   ("Query-path ACLs",
                    "Tenant identity from OAuth/OIDC token. ACL bindings: (user → streams → "
                    "permission). At query time, the gateway enriches the query with a "
                    "filter on streams the user can see; results are post-filtered too "
                    "(belt-and-suspenders). Field-level redaction for PII fields the user "
                    "lacks 'pii:read' on — replaced with '<redacted>'."),
                   ("Audit log: every query, every read",
                    "Each query produces an audit row: (ts, tenant, user, query, result_count, "
                    "ip). Stored in a separate retained-forever stream that the tenant's "
                    "security admin can query. Compliance + insider-threat detection both "
                    "depend on this. The audit log is itself a tenant stream — eats its own "
                    "dog food."),
                   ("Single cluster vs per-tenant cluster trade-off",
                    "Single cluster is 5-10× cheaper per GB but a bad query from one tenant "
                    "can starve others (circuit breakers help but aren't perfect). Per-"
                    "tenant cluster gives strong isolation but doubles ops cost per tenant. "
                    "Practical answer: single shared cluster for the long tail; dedicated "
                    "for top-3 large tenants where blast radius justifies it."),
               ]),
    ],
)
