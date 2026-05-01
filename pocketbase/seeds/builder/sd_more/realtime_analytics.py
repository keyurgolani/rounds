"""SD-extra — Design a Real-time Analytics System (clickstream + dashboards).

HTTP collectors → Kafka ingestion → stream processing (Flink / Spark
Streaming) with windowed aggregations and watermarks → OLAP store
(Druid / ClickHouse / Pinot) for low-latency dashboards. Lambda vs
Kappa architecture, exactly-once semantics, late events, sessionization,
funnels, and HyperLogLog / Theta sketches for cardinality at scale.
"""
from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design a Real-time Analytics System",
    "Hard",
    "Design an end-to-end real-time analytics platform that ingests web/mobile clickstream events "
    "(pageviews, clicks, custom events) at millions of events per second, processes them as a stream "
    "with windowed aggregations and sessionization, and serves sub-second interactive dashboards over "
    "an OLAP store. Users explore time series, funnels, retention cohorts, and percentile latencies "
    "with arbitrary slice-and-dice across high-cardinality dimensions. The system must reconcile "
    "late-arriving mobile events, deliver exactly-once aggregates, and stay within a cost envelope "
    "that does not grow linearly with event volume — which means heavy use of pre-aggregation, "
    "approximate algorithms (HyperLogLog, Theta sketches, t-digest), and tiered storage.",
    hints=[
        "Two distinct workloads: high-throughput append-only ingest (write path) and "
        "low-latency interactive queries over arbitrary slices (read path). Optimize both — they "
        "have nothing in common except the data.",
        "HTTP collector → Kafka is the canonical ingest spine. Collector is a thin, stateless edge "
        "service whose only job is auth + sanity-check + push to Kafka. Never put business logic on "
        "the hot ingest path.",
        "Event schema is the contract: timestamp (event-time), user/anonymous_id, session_id, "
        "event_name, properties{}. Schema registry (Avro/Protobuf) prevents producer drift from "
        "breaking downstream consumers.",
        "Stream processor is Flink or Spark Structured Streaming. Flink wins for true event-time "
        "semantics, low-latency, and watermarks. Spark Streaming wins when you already run Spark "
        "for batch and want one engine.",
        "OLAP store: Druid / ClickHouse / Apache Pinot. All three give sub-second slice-and-dice; "
        "they differ on ingestion model (real-time vs batch), update support, and operational "
        "complexity. Druid + Pinot favor real-time; ClickHouse favors raw flexibility.",
        "Lambda vs Kappa: Lambda runs streaming + batch in parallel and merges; Kappa runs only "
        "streaming and replays from Kafka for backfills. Kappa wins when your stream engine is "
        "expressive enough; Lambda is the safer choice when batch logic is materially different.",
        "Late events are real (mobile app went offline, packet retried 6 hours later). Watermarks "
        "bound how late is too late; allowed-lateness controls how long windows stay open.",
        "Exactly-once = idempotent producer + checkpointed stream operator + idempotent OLAP "
        "writes. Skip any link and you get duplicate counts on replay.",
        "Cardinality kills naive aggregation. count distinct over user_id at billion-event scale "
        "needs HyperLogLog or Theta sketches — sublinear memory, mergeable, ~1% error.",
        "Pre-aggregate by (time-bucket × dimension-cube) on ingest; serve dashboards from cubes, "
        "not raw events. Fall back to raw only when a query asks for a dimension not in any cube.",
    ],
    constraints=[
        "Ingest: 5M events/sec peak, ~1KB/event → 5GB/sec ingress, 15GB/sec replicated (RF=3)",
        "End-to-end freshness: dashboards reflect events within 30s p95, 60s p99",
        "Query latency: p95 < 1s for time-series, < 3s for funnels and cohort retention",
        "Late events: tolerate up to 24h late for mobile/offline clients; correctness preserved",
        "Retention: 90 days raw events queryable; 2 years pre-aggregated cubes; 7 years archive",
        "Exactly-once aggregate semantics across collector → Kafka → Flink → OLAP",
        "Multi-tenant: per-tenant rate limits, schema isolation, cost attribution",
        "Cost: storage and compute scale sublinearly with event volume — pre-agg + approx required",
    ],
    req_func=[
        "HTTP collector accepts events from web/mobile SDKs (POST /track), validates, enriches, "
        "and publishes to Kafka with at-least-once semantics",
        "Schema registry validates events against an Avro/Protobuf contract per event_name",
        "Stream processor runs windowed aggregations (tumbling, sliding, session) keyed by tenant "
        "× event_name × dimension cube, emitting pre-aggregated rollups every minute",
        "Sessionization: derive session_id from gaps > 30min; emit session-level metrics on close",
        "Backfill: re-process historical Kafka data through the same operator graph (Kappa-style)",
        "OLAP store ingests both real-time rollups and batch backfills; serves slice-and-dice "
        "queries with sub-second latency",
        "Dashboard API: time-series, top-N, funnels, retention cohorts, percentiles (p50/p95/p99)",
        "Approximate count distinct (HyperLogLog) and quantiles (t-digest) for high-cardinality "
        "dimensions and rank statistics",
        "Late-event handling: allowed-lateness window keeps aggregates open for up to N hours, "
        "then emits final + side-output of late events",
    ],
    req_nonfunc=[
        "Throughput: 5M events/sec sustained, 10M peak with horizontal scaling of brokers and "
        "stream operators",
        "End-to-end latency: 30s p95 from collector ingest to dashboard visibility",
        "Query latency: p95 < 1s on pre-aggregated cubes, < 3s on raw fallback paths",
        "Durability: zero event loss after collector 200; checkpointed exactly-once for aggregates",
        "Availability: collector 99.99%; query path 99.95%; degraded mode (stale by minutes) > "
        "hard failure",
        "Correctness with late events: results converge to ground-truth within allowed-lateness",
        "Cost efficiency: sublinear storage growth via pre-agg + sketches + tiered storage "
        "(hot OLAP, warm Parquet on S3, cold Glacier)",
        "Multi-tenant isolation: per-tenant quotas, dedicated topics or partitions for noisy "
        "neighbors, per-tenant cost attribution",
        "Operability: replay any 24h window through the stream graph in under 4h for backfills "
        "or bug fixes",
    ],
    estimation={
        "events_per_sec": "5M peak, 2M steady",
        "avg_event_bytes": "~1KB JSON / ~300B Avro → 5GB/sec ingress raw, 1.5GB/sec encoded",
        "events_per_day": "~150B events/day",
        "kafka_storage": "1.5GB/sec × 86400 × 7d × 3 (RF) ≈ 2.7PB hot Kafka tier",
        "raw_event_storage_90d": "~13PB raw on Parquet/S3 (encoded + compressed)",
        "rollup_cardinality": "~10M distinct (tenant × dim-cube × minute) rows/day in OLAP",
        "olap_storage_2yr": "~50TB rollups (columnar + dictionary + bitmap-indexed)",
        "stream_parallelism": "~500 Flink task slots; 2K Kafka partitions for ingest topics",
        "dashboard_qps": "~5K queries/sec across all tenants; 80% hit pre-agg cubes",
        "p95_query_pre_agg": "<1s; raw scan fallback 1-5s for arbitrary dimensions",
    },
    endpoints=[
        {"method": "POST", "path": "/track",
         "description": "Collector ingest: client SDK posts a batch of events",
         "body": "{events:[{event:str, user_id:str, anon_id:str, ts:long, props:{}}], "
                 "context:{ua, ip, sdk_ver}}"},
        {"method": "POST", "path": "/identify",
         "description": "Bind anonymous_id to user_id; emits an alias event",
         "body": "{anon_id, user_id, traits:{}}"},
        {"method": "GET", "path": "/query/timeseries",
         "description": "Dashboard time-series query over pre-agg cubes",
         "body": "{tenant, event, dims:{country:US}, metric:count, granularity:1m, "
                 "range:[t0,t1]}"},
        {"method": "GET", "path": "/query/funnel",
         "description": "Funnel: ordered sequence of events within a time window per user",
         "body": "{tenant, steps:[viewed_pdp, added_to_cart, checked_out], window_hours:24, "
                 "range:[t0,t1]}"},
        {"method": "GET", "path": "/query/retention",
         "description": "Retention cohort: % of users from cohort C active in week N",
         "body": "{tenant, cohort_event:signup, return_event:any, weeks:8, range:[t0,t1]}"},
        {"method": "GET", "path": "/query/distinct",
         "description": "Approximate count distinct via HyperLogLog merge",
         "body": "{tenant, event, dims:{}, dimension:user_id, range:[t0,t1]}"},
        {"method": "POST", "path": "/schemas/{event_name}",
         "description": "Register or evolve the schema for an event_name",
         "body": "{schema_avro, compatibility:backward}"},
        {"method": "POST", "path": "/backfill",
         "description": "Trigger a Kappa-style replay of a Kafka offset range through the "
                        "current operator graph",
         "body": "{topic, partition_range, start_offset, end_offset, sink_table}"},
    ],
    tables=[
        {"name": "events_raw_parquet",
         "columns": ["event_id UUID PK", "tenant_id BIGINT", "event VARCHAR(64)",
                     "user_id VARCHAR(64)", "anon_id VARCHAR(64)", "session_id VARCHAR(64)",
                     "event_ts BIGINT", "ingest_ts BIGINT", "props JSON",
                     "country VARCHAR(2)", "device VARCHAR(32)", "sdk_version VARCHAR(16)"]},
        {"name": "rollup_minute",
         "columns": ["tenant_id BIGINT", "event VARCHAR(64)", "minute_bucket BIGINT",
                     "country VARCHAR(2)", "device VARCHAR(32)",
                     "count BIGINT", "uniques_hll VARBINARY",
                     "latency_tdigest VARBINARY",
                     "PRIMARY KEY (tenant_id, event, minute_bucket, country, device)"]},
        {"name": "rollup_hour",
         "columns": ["tenant_id BIGINT", "event VARCHAR(64)", "hour_bucket BIGINT",
                     "country VARCHAR(2)", "device VARCHAR(32)",
                     "count BIGINT", "uniques_hll VARBINARY",
                     "latency_tdigest VARBINARY",
                     "PRIMARY KEY (tenant_id, event, hour_bucket, country, device)"]},
        {"name": "sessions",
         "columns": ["session_id VARCHAR(64) PK", "tenant_id BIGINT", "user_id VARCHAR(64)",
                     "started_at BIGINT", "ended_at BIGINT", "event_count INT",
                     "first_event VARCHAR(64)", "last_event VARCHAR(64)",
                     "duration_ms BIGINT", "props JSON"]},
        {"name": "schema_registry",
         "columns": ["event_name VARCHAR(64)", "version INT", "schema_avro TEXT",
                     "compatibility VARCHAR(16)", "created_at BIGINT",
                     "PRIMARY KEY (event_name, version)"]},
        {"name": "tenants",
         "columns": ["tenant_id BIGINT PK", "name VARCHAR(255)", "qps_quota INT",
                     "retention_days INT", "plan VARCHAR(32)", "created_at BIGINT"]},
    ],
    indexes=[
        "(tenant_id, event, minute_bucket) on rollup_minute — primary dashboard lookup",
        "(tenant_id, user_id, event_ts) on events_raw_parquet — funnel & retention scans",
        "(tenant_id, session_id) on events_raw_parquet — session reconstruction",
        "Bitmap indexes on country/device/event in OLAP store — slice-and-dice",
        "Bloom filters on user_id per Parquet rowgroup — efficient point lookups in cold tier",
    ],
    hld_desc=(
        "A four-stage pipeline: (1) edge HTTP collectors validate, enrich, and push events to "
        "Kafka topics partitioned by tenant + event_name; (2) a Flink job consumes Kafka with "
        "exactly-once checkpointed state, runs windowed aggregations keyed by dimension cubes, "
        "performs sessionization, and emits per-minute rollups to an OLAP store while also "
        "writing raw enriched events to S3/Parquet; (3) the OLAP store (Druid / ClickHouse / "
        "Pinot) ingests rollups in real time and exposes a SQL endpoint for dashboards; (4) a "
        "dashboard service answers time-series, funnel, retention, and percentile queries by "
        "first hitting pre-agg cubes and falling back to raw scan only when a query needs a "
        "dimension not in any cube. A schema registry (Avro/Protobuf) enforces the event "
        "contract between producers and consumers. Lambda is avoided in favor of a Kappa-style "
        "design where backfills replay Kafka through the same operator graph; the only "
        "concession to Lambda is a nightly batch job that recomputes rollups from S3/Parquet "
        "as a correctness sentinel."
    ),
    hld_components=[
        {"name": "Web/Mobile SDK", "role": "Buffer events client-side, batch, retry, send"},
        {"name": "HTTP Collector", "role": "Stateless edge: auth, sanity-check, enqueue to Kafka"},
        {"name": "Kafka (ingest)", "role": "Durable buffer: per-tenant + per-event partitioned topics"},
        {"name": "Schema Registry", "role": "Avro/Protobuf contracts; producer/consumer compatibility"},
        {"name": "Stream Processor (Flink)", "role": "Windowed agg, sessionization, watermarks, EOS"},
        {"name": "Late-Event Side Output", "role": "Drops dropped-late events into a side topic for audit"},
        {"name": "OLAP Store (Druid/ClickHouse/Pinot)", "role": "Sub-second slice-and-dice over rollups"},
        {"name": "Cold Lake (S3 + Parquet)", "role": "Raw enriched events for backfills & ad-hoc"},
        {"name": "Batch Reconciler (Spark)", "role": "Nightly recompute from raw → sentinel for stream output"},
        {"name": "Dashboard API", "role": "Query planner: pre-agg first, raw fallback, sketch merges"},
        {"name": "Sketch Library (HLL/Theta/t-digest)", "role": "Approximate, mergeable distincts/quantiles"},
        {"name": "Backfill Runner", "role": "Kappa replay of historical Kafka offsets through Flink"},
        {"name": "Tenant Quota Service", "role": "Per-tenant rate limit, cost attribution, isolation"},
    ],
    detailed_design={
        "collector_ingest": (
            "Collector is a thin, stateless Go/Rust service behind a global anycast load balancer. "
            "It accepts batched events over HTTP/2 with a project_id auth token, validates the "
            "event against the schema registry's latest version (rejects on incompatible changes), "
            "enriches with server-derived fields (server_ts, ip, geo, user_agent parsed), and "
            "publishes to a Kafka topic partitioned by murmur2(tenant_id ∥ event_name) % N. The "
            "collector returns 200 only after Kafka acks=all + min.insync.replicas=2, so a "
            "successful POST means the event is durable. No business logic, no joins, no enrichment "
            "from external systems on the hot path — keep p99 collector latency < 50ms. Backpressure "
            "(Kafka producer buffer full) returns 429 with Retry-After; SDK queues client-side."
        ),
        "schema_registry_evolution": (
            "Each event_name has an Avro/Protobuf schema with backward-compatibility rules. New "
            "fields must be optional with defaults. Removing a field requires a deprecation cycle. "
            "Producers (SDKs) embed the schema id in each event; consumers (Flink, OLAP loaders) "
            "fetch the schema by id and decode. This decouples producer and consumer release "
            "cadence. Without a registry, one bad SDK release silently corrupts dashboards for "
            "weeks before someone notices the funnel chart broke."
        ),
        "kafka_ingest_topology": (
            "Three classes of topics: (1) events_raw partitioned by (tenant, event) at ~2K "
            "partitions; (2) sessions (compacted, keyed by session_id) for sessionization state "
            "broadcast; (3) late_events side-output for events past allowed-lateness. Retention "
            "= 7 days hot (replay window); cold tier offload via Kafka tiered storage or a "
            "Connect → S3 sink. Compression = zstd, batched 64KB. ack=all + min.insync.replicas=2 "
            "+ idempotent producer for the durability triplet. Per-tenant quota enforced by "
            "Kafka client quotas — noisy neighbors get throttled, not dropped."
        ),
        "stream_processing_flink": (
            "Flink job consumes events_raw, keys by (tenant, event, dimension-cube), and runs "
            "tumbling 1-minute windows for cube rollups + session windows (gap=30min) for "
            "sessionization. State backend: RocksDB on local SSD with incremental checkpoints "
            "to S3 every 30s. Exactly-once: Flink's two-phase-commit sink coordinator coordinates "
            "Kafka source offsets + sink commits — on recovery, replay from the last successful "
            "checkpoint and the sink dedups via transaction marker. Parallelism ≈ Kafka "
            "partition count; operators chain to keep network shuffles minimal."
        ),
        "windowing_and_watermarks": (
            "Event-time windowing keyed off the SDK-stamped event_ts (not server ingest_ts) — "
            "otherwise mobile-app retries get bucketed as if they happened now, distorting the "
            "time series. Watermark = max event_ts seen − allowed-skew (e.g., 30s). Window "
            "fires when watermark passes window-end. allowed-lateness = up to 24h: window state "
            "is retained, late events update aggregates and emit a retraction + new value to the "
            "OLAP store; OLAP must support upsert (Druid: late-arriving compaction, Pinot: "
            "upsert tables, ClickHouse: ReplacingMergeTree). Past allowed-lateness, events go to "
            "the side-output topic, are still saved to raw lake, and never silently dropped."
        ),
        "sessionization": (
            "Session = sequence of events from the same user with no gap > 30min. Implemented as "
            "a Flink session window keyed by user_id with eventTimeSessionWindows(Time.minutes(30)). "
            "On session close (gap exceeded or job timeout), emit a session record: started_at, "
            "ended_at, event_count, first/last event, duration_ms. Sessions feed both the OLAP "
            "store (sessions table) and a sessions Kafka topic for downstream consumers (e.g., "
            "marketing attribution). Trickiest part: late events that fall inside an already-"
            "closed session — handled via the same allowed-lateness mechanism."
        ),
        "olap_store_choice": (
            "Druid: best for high-throughput real-time ingest + segment-based time partitioning + "
            "time-series queries. Pinot: similar shape, native upsert, strong on user-facing "
            "dashboards. ClickHouse: maximum query flexibility, excellent compression, weaker "
            "real-time semantics (best with batch micro-ingests). Pick by team familiarity; all "
            "three deliver sub-second slice-and-dice when fed pre-aggregated rollups. Schema in "
            "OLAP: time bucket as primary partition key; tenant + event as secondary partition; "
            "dimensions as bitmap-indexed columns; metrics as columnar values."
        ),
        "pre_aggregation_cubes": (
            "Build a small set of dimension cubes per event family covering 80% of dashboard "
            "queries: e.g., (tenant × event × minute × country × device) and (tenant × event × "
            "hour × campaign × landing_page). Each cube row stores count, sum, HLL of user_id, "
            "t-digest of latency. Storage cost is N(rows) ≈ product of cardinalities × time "
            "buckets. Choose cube dimensions by tracing actual dashboard queries — don't "
            "speculatively cube every dimension or storage explodes. Queries first hit cubes; "
            "if the requested dimension is not in any cube, fall back to raw event scan (slow "
            "but correct)."
        ),
        "exactly_once_end_to_end": (
            "Three handoffs to make idempotent: (1) collector → Kafka via idempotent producer "
            "(PID + seq dedup); (2) Kafka → Flink via Flink's exactly-once source (offset "
            "checkpointed atomically with state); (3) Flink → OLAP via two-phase-commit sink "
            "(transactional write to OLAP, committed only when Flink checkpoint succeeds). "
            "Skip any link and replays produce duplicate counts. Downstream sinks like Pinot "
            "upsert tables or Druid replace-by-timestamp also help — they tolerate duplicate "
            "writes by virtue of being idempotent on (tenant, event, time-bucket, dim-key)."
        ),
        "lambda_vs_kappa": (
            "Lambda runs streaming + batch in parallel: stream gives fresh-but-approximate, batch "
            "gives stale-but-correct, dashboards merge. Two codepaths, two bugs to keep in sync. "
            "Kappa runs only streaming: backfills replay Kafka through the same operator graph. "
            "Single codepath; correctness depends on Kafka retention being long enough for "
            "replay (7-30 days hot tier + tiered cold). We choose Kappa as the default with "
            "one nightly Spark recompute over the raw S3 lake as a sentinel — if stream and "
            "batch disagree by > tolerance, page the on-call. Best of both: one codepath day-to-"
            "day, defense-in-depth correctness check overnight."
        ),
        "approximate_aggregations": (
            "Exact count distinct over user_id at 150B events/day is infeasible — would require "
            "billions of rows of user_ids per (tenant × dim-cube × minute). HyperLogLog: "
            "sublinear memory (~12KB / sketch for ~1% error), mergeable across time windows and "
            "dimension slices. Theta sketches: HLL alternative that supports set intersection "
            "(useful for funnel uniques). t-digest: streaming quantile sketch, ~10KB, 0.5% "
            "error on extreme percentiles. Quantile-quantile (KLL) sketch is a newer choice "
            "with better merge properties. Store sketches as VARBINARY in OLAP rollup rows; "
            "merge at query time across the requested time range and dimensions."
        ),
        "queries_funnels_retention": (
            "Time-series: SUM/COUNT over rollup_minute filtered by (tenant, event, dims) within "
            "[t0, t1] — sub-second on cubes. Funnels: a funnel of N steps within a window W is "
            "a sequenced match; implemented either by a Flink job that emits funnel-progression "
            "events to a separate cube, or by a SQL window query over raw events with PARTITION "
            "BY user_id ORDER BY event_ts and a step-detection match_recognize. Retention: "
            "cohort users from event C in week 0; check active in week N; HLL of user_ids per "
            "(cohort_week, return_week) cube row, retention = HLL(cohort ∩ active) / HLL(cohort). "
            "Theta sketches make the intersection efficient."
        ),
        "late_events_handling": (
            "Three layers of defense: (1) watermark = max(event_ts) − 30s — bounds 'normal' "
            "lateness; (2) allowed-lateness = 24h — windows stay in state, late events update "
            "and emit retractions; (3) side-output for events past 24h — never silently dropped, "
            "saved to raw lake and counted in a 'dropped_late' metric. Trade-off: longer "
            "allowed-lateness = more state in Flink + more upserts to OLAP. Tune per workload. "
            "Mobile-heavy clickstream: 24h reasonable. Server logs: 1h plenty. Calibrate from "
            "actual lateness percentiles — don't guess."
        ),
        "tiered_storage_cost": (
            "Hot: Kafka 7 days for replay, OLAP 90 days of rollups (~50TB). Warm: raw events "
            "as Parquet on S3 with Hive-style partitioning by (tenant, day) for 90 days "
            "queryable via Athena/Trino — covers ad-hoc that pre-agg can't. Cold: Glacier "
            "for 7y compliance retention. Cost shape: hot OLAP ~$0.10/GB-month, warm S3 "
            "~$0.023, Glacier ~$0.004 — three orders of magnitude. Without tiering, raw "
            "retention dominates the bill at scale."
        ),
        "multi_tenant_isolation": (
            "Per-tenant rate limit at collector (token bucket, 1K events/sec default, configurable "
            "by plan). Noisy-neighbor protection: top-N tenants get dedicated Kafka partitions "
            "or even dedicated topics; small tenants share. Flink job uses keyed state — one "
            "tenant's hot keys don't affect another's. OLAP partitioned by tenant_id as primary "
            "key so a slow query on one tenant doesn't lock segments belonging to others. Cost "
            "attribution: track bytes ingested + bytes scanned per tenant; bill back monthly."
        ),
    },
    trade_offs=[
        {"option": "Lambda (stream + batch parallel) vs Kappa (stream only, replay for backfills)",
         "for_lambda": "Batch path catches bugs in stream code; mature and well-understood",
         "for_kappa": "Single codepath, no batch/stream divergence to maintain",
         "recommendation": "Kappa as the default; one nightly Spark recompute over raw lake as a "
                           "correctness sentinel. Best of both — one daily codepath, defense-in-"
                           "depth check overnight."},
        {"option": "Flink vs Spark Structured Streaming",
         "for_flink": "True event-time semantics, low-latency, robust watermarks, EOS first-class",
         "for_spark": "Reuse existing Spark infra, Python/SQL friendly, micro-batch good enough "
                      "for 30s freshness",
         "recommendation": "Flink for sub-second / sessionization-heavy workloads; Spark "
                           "Structured Streaming when batch is already Spark and freshness "
                           "tolerance is minutes."},
        {"option": "Druid vs ClickHouse vs Pinot for OLAP serving",
         "for_druid": "Battle-tested real-time ingest, time-partitioned segments, mature",
         "for_clickhouse": "Maximum query flexibility, excellent compression, SQL-friendly",
         "for_pinot": "Native upsert tables (great for late events), strong user-facing latency",
         "recommendation": "Druid or Pinot for real-time-heavy / late-event correctness; "
                           "ClickHouse when ad-hoc query flexibility outweighs streaming "
                           "polish. Team familiarity is the tiebreaker."},
        {"option": "Exact count distinct vs HyperLogLog / Theta sketches",
         "for_exact": "Correct to the event; auditable; no error bars on dashboards",
         "for_sketches": "Sublinear memory, mergeable across slices, scales to billions of events",
         "recommendation": "Sketches for ~1% error tolerable workloads (~99% of analytics); "
                           "exact only for compliance/billing where the event count is the "
                           "deliverable."},
        {"option": "Pre-aggregated cubes vs query-time aggregation over raw",
         "for_cubes": "Sub-second dashboards; cheap repeated queries",
         "for_raw": "Arbitrary slice flexibility; no cube-design lock-in",
         "recommendation": "Cubes for the 80% of common dashboard slices; raw scan as a fallback "
                           "for the long tail. Don't try to cube everything — storage explodes."},
        {"option": "Allowed-lateness 1h vs 24h",
         "for_1h": "Smaller Flink state, fewer OLAP upserts",
         "for_24h": "Correct for offline mobile clients, app-resume scenarios",
         "recommendation": "Tune per workload from observed lateness p99. Mobile-heavy "
                           "clickstream: 24h. Server logs: 1h. Calibrate, don't guess."},
    ],
    tips=[
        "Lead with the two-workload framing: high-throughput append-only ingest vs interactive "
        "low-latency query. They share the data and nothing else — design each independently.",
        "Event-time vs ingest-time is the senior signal. If you bucket by ingest-time, late "
        "mobile retries get attributed to 'now' and your time-series is wrong.",
        "Schema registry is non-negotiable. Without it, one bad SDK release silently corrupts "
        "weeks of dashboards. Mention Avro/Protobuf + backward-compatibility rules.",
        "Watermarks + allowed-lateness + side-output = the late-event triple. Many candidates "
        "remember watermarks but skip the rest, leaving silent dropped events on the table.",
        "Exactly-once is the joint property of three handoffs (collector→Kafka→Flink→OLAP). "
        "Skip any one and replays double-count. Idempotent sink + transactional checkpoint is "
        "the senior answer.",
        "Pre-aggregation cubes are how dashboards stay sub-second. Trace actual queries to size "
        "cubes — don't speculatively cube everything.",
        "HyperLogLog and Theta sketches are the answer to 'count distinct over a billion events.' "
        "Mention mergeability — that's why sketches beat exact for slice-and-dice.",
        "Lambda vs Kappa: pick Kappa as the default; mention the nightly Spark sentinel as "
        "defense in depth. That's the 2026 answer; pure Lambda is dated.",
        "OLAP store is Druid / ClickHouse / Pinot. Know the differentiators (real-time ingest, "
        "upserts, query flexibility) — don't just say 'OLAP DB.'",
        "Tiered storage (hot OLAP / warm Parquet / cold Glacier) is what makes the cost story "
        "work. Without it, raw retention dominates the bill at scale.",
    ],
    thought_process=[
        "1. Clarify: what's an event? Anything client-emitted with timestamp + user + properties.",
        "2. Two workloads: (a) durable, high-throughput ingest; (b) low-latency interactive query.",
        "3. Estimate: 5M events/sec × 1KB ≈ 5GB/sec → Kafka with 2K partitions, RF=3.",
        "4. Collector: stateless edge, validate via schema registry, push to Kafka with EOS.",
        "5. Stream processor: Flink on event-time, keyed by tenant + event + dim-cube, tumbling "
        "+ session windows, RocksDB state with checkpoints.",
        "6. Watermarks bound normal lateness; allowed-lateness keeps windows open up to 24h; "
        "past that, side-output to a late-events topic.",
        "7. Sessionization via session windows keyed by user_id with 30-min gap.",
        "8. Pre-aggregation: emit (tenant × event × minute × dim-cube) rollups with HLL + "
        "t-digest sketches as values.",
        "9. OLAP store (Druid/Pinot/ClickHouse) ingests rollups in real time + nightly batch "
        "recompute from raw S3 as correctness sentinel.",
        "10. Dashboards: query planner hits pre-agg cubes first; raw fallback for arbitrary "
        "dimensions; sketch merges for distincts and quantiles.",
        "11. Backfills via Kappa replay through the same Flink graph; bug fixes don't require "
        "a separate batch codepath.",
        "12. Multi-tenant: per-tenant quotas at collector, dedicated partitions for noisy "
        "neighbors, OLAP partitioned by tenant_id.",
        "13. Tiered storage: hot OLAP 90d, warm Parquet on S3 90d, cold Glacier 7y.",
        "14. Exactly-once across the chain: idempotent producer + Flink 2PC sink + idempotent "
        "OLAP upserts.",
    ],
    tags=["analytics", "streaming", "kafka", "flink", "olap", "druid", "clickhouse", "pinot",
          "hll", "lambda-architecture", "kappa-architecture"],
    arch_nodes=[
        {"id": "sdk", "label": "Web/Mobile SDK", "type": "client"},
        {"id": "lb", "label": "Anycast LB", "type": "lb"},
        {"id": "coll", "label": "HTTP Collector", "type": "server"},
        {"id": "reg", "label": "Schema Registry", "type": "service"},
        {"id": "kafka", "label": "Kafka (events_raw)", "type": "queue"},
        {"id": "kafka_late", "label": "Kafka (late_events)", "type": "queue"},
        {"id": "flink", "label": "Flink (windowed agg + sessions)", "type": "service"},
        {"id": "rocks", "label": "RocksDB state + S3 checkpoints", "type": "database"},
        {"id": "olap", "label": "OLAP Store (Druid/Pinot/CH)", "type": "database"},
        {"id": "lake", "label": "Raw Parquet on S3", "type": "database"},
        {"id": "spark", "label": "Spark (nightly sentinel)", "type": "service"},
        {"id": "dash_api", "label": "Dashboard API", "type": "server"},
        {"id": "cube", "label": "Pre-agg Cubes", "type": "cache"},
        {"id": "dash", "label": "Dashboards (UI)", "type": "client"},
        {"id": "backfill", "label": "Backfill Runner (Kappa)", "type": "service"},
    ],
    arch_edges=[
        {"source": "sdk", "target": "lb", "label": "POST /track"},
        {"source": "lb", "target": "coll"},
        {"source": "coll", "target": "reg", "label": "validate"},
        {"source": "coll", "target": "kafka", "label": "produce (idempotent, ack=all)"},
        {"source": "kafka", "target": "flink", "label": "consume (EOS source)"},
        {"source": "flink", "target": "rocks", "label": "checkpoint"},
        {"source": "flink", "target": "olap", "label": "rollups (2PC sink)"},
        {"source": "flink", "target": "lake", "label": "raw enriched"},
        {"source": "flink", "target": "kafka_late", "label": "late side-output"},
        {"source": "lake", "target": "spark", "label": "nightly recompute"},
        {"source": "spark", "target": "olap", "label": "sentinel reconcile"},
        {"source": "dash", "target": "dash_api"},
        {"source": "dash_api", "target": "cube", "label": "pre-agg first"},
        {"source": "dash_api", "target": "olap", "label": "fallback raw scan"},
        {"source": "backfill", "target": "kafka", "label": "replay offsets"},
        {"source": "backfill", "target": "flink"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant SDK as Web/Mobile SDK\n"
        "  participant C as Collector\n"
        "  participant SR as Schema Registry\n"
        "  participant K as Kafka\n"
        "  participant F as Flink\n"
        "  participant O as OLAP Store\n"
        "  participant D as Dashboard\n"
        "  SDK->>C: POST /track (batch, schema_id)\n"
        "  C->>SR: validate schema\n"
        "  SR-->>C: ok\n"
        "  C->>K: produce (idempotent, ack=all)\n"
        "  K-->>C: committed\n"
        "  C-->>SDK: 200\n"
        "  F->>K: consume (checkpointed offsets)\n"
        "  F->>F: window agg + sessionize (event-time)\n"
        "  F->>F: emit rollups (2PC pre-commit)\n"
        "  F->>O: write rollups (txn)\n"
        "  F->>F: checkpoint succeeds\n"
        "  F->>O: 2PC commit\n"
        "  D->>O: query timeseries (pre-agg cube)\n"
        "  O-->>D: rows < 1s\n"
        "  Note over F,O: late event arrives within 24h\n"
        "  F->>O: upsert rollup row (retraction + new)"
    ),
    er_diagram=(
        "erDiagram\n"
        "  TENANT ||--o{ EVENT_RAW : owns\n"
        "  EVENT_RAW ||--o{ ROLLUP_MINUTE : aggregates\n"
        "  ROLLUP_MINUTE ||--o{ ROLLUP_HOUR : rolls_up\n"
        "  USER ||--o{ EVENT_RAW : performs\n"
        "  USER ||--o{ SESSION : has\n"
        "  SESSION ||--o{ EVENT_RAW : contains\n"
        "  SCHEMA_REGISTRY ||--o{ EVENT_RAW : validates\n"
        "  TENANT { bigint tenant_id PK\n string name\n int qps_quota\n int retention_days }\n"
        "  EVENT_RAW { uuid event_id PK\n bigint tenant_id\n string event\n string user_id\n bigint event_ts\n json props }\n"
        "  ROLLUP_MINUTE { bigint tenant_id\n string event\n bigint minute_bucket\n string country\n bigint count\n bytes uniques_hll }\n"
        "  SESSION { string session_id PK\n string user_id\n bigint started_at\n bigint ended_at }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Event arrives at SDK] --> B[Buffer + batch client-side]\n"
        "  B --> C[POST /track to collector]\n"
        "  C --> D{Schema valid?}\n"
        "  D -->|No| E[Reject, log producer error]\n"
        "  D -->|Yes| F[Enrich: server_ts, geo, ua]\n"
        "  F --> G[Produce to Kafka idempotent ack=all]\n"
        "  G --> H[Flink consume EOS source]\n"
        "  H --> I[Key by tenant+event+dim-cube]\n"
        "  I --> J{Within watermark?}\n"
        "  J -->|Yes| K[Tumbling 1m window agg]\n"
        "  J -->|No, < 24h late| L[Update window, emit retract+new]\n"
        "  J -->|No, > 24h late| M[Side-output to late_events]\n"
        "  K --> N[Sessionize by user_id, 30m gap]\n"
        "  L --> N\n"
        "  N --> O[2PC sink to OLAP + raw to S3]\n"
        "  O --> P[OLAP serves dashboards via cubes]\n"
        "  P --> Q{Dim in any cube?}\n"
        "  Q -->|Yes| R[Sub-second pre-agg query]\n"
        "  Q -->|No| S[Raw scan fallback 1-5s]"
    ),
    tradeoff_title="Lambda Architecture vs Kappa Architecture",
    tradeoff_options=[
        {"label": "Lambda (stream + batch in parallel)",
         "description": "Two parallel pipelines: a streaming layer for fresh-but-approximate "
                        "real-time results, and a batch layer for stale-but-correct historicals. "
                        "Dashboards merge the two — recent windows from streaming, older windows "
                        "from batch.",
         "pros": ["Battle-tested pattern with mature tooling on each side",
                 "Batch path independently catches bugs in the stream code",
                 "Different optimization targets per path are natural",
                 "Easier to start with batch and add streaming incrementally"],
         "cons": ["Two codepaths to maintain — same logic written twice in different engines",
                 "Reconciliation between layers is a permanent ops burden",
                 "Risk of subtle drift between stream and batch results that nobody notices",
                 "Storage cost: raw kept for batch + intermediate state for stream"]},
        {"label": "Kappa (stream-only, replay for backfills)",
         "description": "Single streaming pipeline. Backfills and bug fixes are handled by "
                        "replaying historical Kafka offsets through the same operator graph. "
                        "Requires Kafka retention long enough for the replay window "
                        "(7-30d hot + tiered cold).",
         "pros": ["One codepath — no stream/batch divergence to maintain",
                 "Backfills exercise the same logic that runs in production",
                 "Operationally simpler: one engine, one job graph, one set of metrics",
                 "Fits naturally with EOS streaming engines (Flink, Kafka Streams)"],
         "cons": ["Requires Kafka tiered storage or aggressive retention for long replays",
                 "Stream engine must be expressive enough for all batch logic",
                 "Replay cost can be high — running 30 days through Flink takes hours/days",
                 "Some heavy joins or graph computations are awkward in pure streaming"]},
    ],
    tradeoff_rec="Kappa as the daily codepath; one nightly Spark recompute over the raw S3 lake "
                 "as a correctness sentinel that pages on disagreement beyond tolerance. Single "
                 "codepath day-to-day, defense-in-depth check overnight — captures the "
                 "operational simplicity of Kappa with the catch-all safety of Lambda's batch "
                 "layer.",
    senior_topics=[
        _topic("event-time-vs-ingest-time-watermarks",
               "Event-Time, Ingest-Time, and Watermarks",
               "Real-time analytics over clickstream is a study in time. Mobile retries arrive "
               "minutes-to-hours after the event happened; bucketing by ingest-time silently "
               "distorts every dashboard. Event-time + watermarks is the answer.",
               [
                   ("Why event-time wins",
                    "An event happens on the user's phone at 09:00:00. The phone is offline; "
                    "the SDK retries; the event reaches the collector at 11:42:00. Bucket by "
                    "ingest-time: 'pageviews at 11:42' is wrong. Bucket by event-time: 'pageviews "
                    "at 09:00' is right. Every analytics query is implicitly an event-time "
                    "question."),
                   ("Watermarks bound normal lateness",
                    "A watermark W(t) at processing time t says 'no more events with event_ts < W '. "
                    "Computed as max(event_ts) − allowed_skew, it lets the engine close windows "
                    "and emit results without waiting forever. Tune allowed_skew from observed "
                    "p99 lateness — too tight drops events; too loose adds end-to-end latency."),
                   ("Allowed-lateness keeps windows open",
                    "Past the watermark, but within allowed-lateness, the window state stays in "
                    "memory. Late events update aggregates and emit retractions + new values "
                    "downstream. Storage cost: Flink state grows with allowed-lateness × event "
                    "rate per key. Past allowed-lateness, send to side-output, never silently "
                    "drop."),
                   ("Side-output for very-late events",
                    "Events past allowed-lateness route to a late_events Kafka topic and a "
                    "dropped_late metric. The raw lake still ingests them so they're queryable "
                    "for forensics. The metric drives the question 'is allowed-lateness too "
                    "tight?' — calibrate from real lateness percentiles."),
                   ("Watermarks across operators",
                    "Each operator emits a watermark = min(input watermarks). A keyed window "
                    "fires only after its watermark passes window-end. In multi-source jobs "
                    "(joins), one slow source holds back every watermark — design for it: "
                    "bound the slow source or accept the lag."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant SDK\n  participant K as Kafka\n  participant F as Flink\n  participant O as OLAP\n"
                   "  Note over SDK: event_ts = 09:00\n"
                   "  SDK->>K: enqueue at 11:42 (offline retry)\n"
                   "  K->>F: consume\n"
                   "  F->>F: max(event_ts)=11:42; W=11:41:30\n"
                   "  F->>F: late by 2h41m — within 24h\n"
                   "  F->>F: update 09:00 window, emit retract+new\n"
                   "  F->>O: upsert rollup at minute=09:00\n"
                   "  Note over O: dashboard pageviews at 09:00 corrects upward"
               )),
        _topic("hyperloglog-and-theta-sketches",
               "HyperLogLog, Theta Sketches, and Mergeable Approximate Aggregates",
               "Exact count distinct over billions of events is infeasible; HLL and Theta sketches "
               "give sublinear memory, mergeability across slices, and ~1% error — making them "
               "the only realistic answer for high-cardinality dashboards.",
               [
                   ("Why exact distinct fails at scale",
                    "Counting distinct user_ids per (tenant × dim-cube × minute) at 5M events/sec "
                    "across 1M users would require billions of user_id rows in OLAP rollups. "
                    "Storage and merge cost both explode. Sketches turn this into a constant-"
                    "memory problem per slice."),
                   ("HyperLogLog mechanics",
                    "Hash each user_id to 64 bits. Use first p bits as a register index (2^p "
                    "registers, e.g., p=12 → 4096), and count leading zeros in the rest. The "
                    "max leading-zero count per register estimates log2(distinct count). "
                    "Standard error ~1.04/sqrt(2^p); with p=12, ~1.6% — fine for dashboards. "
                    "Memory: ~12KB per sketch."),
                   ("Mergeability is the killer feature",
                    "HLL sketches merge by element-wise max of registers. So merging across "
                    "time windows (minute → hour → day) and across dimension slices (sum HLLs "
                    "over countries to get global) is O(register count). Without mergeability, "
                    "you'd have to re-scan raw events per query."),
                   ("Theta sketches for set operations",
                    "Theta sketches generalize HLL to support union, intersection, and "
                    "difference of sets — useful for funnels (users who did A AND B), "
                    "retention (cohort ∩ active), and deduplication across overlapping sources. "
                    "HLL only natively supports union; Theta is HLL's more flexible cousin."),
                   ("Where exact still matters",
                    "Compliance, billing, audit logs — anything where the count is the deliverable "
                    "and a 1% error is unacceptable. For these, run a separate exact pipeline "
                    "(Spark batch over raw lake) and accept the latency. Don't try to make HLL "
                    "exact — it's not."),
                   ("Storage shape in OLAP",
                    "Sketches are stored as VARBINARY (or sketch-native types in Pinot/Druid). "
                    "Rollup row: (tenant, event, minute, country, count, hll_user_id, "
                    "tdigest_latency). Dashboard query: SELECT MERGE_HLL(hll_user_id) FROM "
                    "rollup_minute WHERE tenant=X AND ts BETWEEN ... — sub-second."),
               ],
               diagram=(
                   "graph LR\n"
                   "  E[Events] --> H[hash user_id]\n"
                   "  H --> R[Update HLL register p bits → leading-zero max]\n"
                   "  R --> S1[HLL minute-1]\n"
                   "  R --> S2[HLL minute-2]\n"
                   "  R --> S3[HLL minute-3]\n"
                   "  S1 -. element-wise max .-> SH[HLL hour]\n"
                   "  S2 -. element-wise max .-> SH\n"
                   "  S3 -. element-wise max .-> SH\n"
                   "  SH --> Q[Query: distinct ≈ 2^max_lz × constant]"
               )),
        _topic("end-to-end-exactly-once",
               "End-to-End Exactly-Once Across Collector → Kafka → Flink → OLAP",
               "Exactly-once is not a property of any one component; it's the joint property of "
               "every handoff in the pipeline. Skip any link and replays double-count.",
               [
                   ("Three handoffs, three idempotency stories",
                    "(1) Collector → Kafka: idempotent producer (PID + sequence) dedups retries "
                    "within a single producer session; transactional producer extends to multi-"
                    "partition atomicity. (2) Kafka → Flink: Flink's source connector "
                    "checkpoints offsets atomically with operator state; on recovery, restart "
                    "from the last checkpoint, not from where Kafka thinks the consumer was. "
                    "(3) Flink → OLAP: 2PC sink — Flink pre-commits OLAP writes during the "
                    "checkpoint barrier and commits when the checkpoint completes. On failure, "
                    "the pre-committed transaction is aborted."),
                   ("Idempotent sinks as the safety net",
                    "Even with 2PC, idempotent OLAP writes are belt-and-suspenders. Druid's "
                    "replace-by-timestamp, Pinot's upsert tables, and ClickHouse's "
                    "ReplacingMergeTree all dedup on a key. So a duplicate write from a "
                    "marginally-buggy sink is absorbed, not double-counted. Always design "
                    "rollup keys (tenant × event × time-bucket × dim-cube) to be deterministic "
                    "so idempotent upsert is meaningful."),
                   ("Checkpoint cadence trade-off",
                    "Flink checkpoints every 30s — that's the maximum data-loss window on "
                    "recovery. Shorter checkpoints = lower recovery RPO but more S3 writes "
                    "and more 2PC coordinator work. Longer = cheaper but slower failover. "
                    "Tune from RPO target."),
                   ("Where EOS breaks: external sinks without idempotency",
                    "If the sink is a non-idempotent system (raw HTTP webhook, an audit log "
                    "that rejects duplicates with an error), 2PC won't save you. Either wrap "
                    "the sink in an idempotent shim (write to Kafka, separate consumer pushes "
                    "with dedup) or accept at-least-once + downstream dedup."),
                   ("Replay testing",
                    "Routinely kill the Flink job mid-checkpoint and verify no duplicate "
                    "rollup rows appear. This is the only real test of EOS — production "
                    "is too rare and quiet to surface bugs. Inject failures during "
                    "integration tests."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant C as Collector\n  participant K as Kafka\n  participant F as Flink\n  participant O as OLAP\n"
                   "  C->>K: produce (PID, seq, ack=all)\n"
                   "  K-->>C: ok (idempotent dedup on retry)\n"
                   "  F->>K: consume (offset N)\n"
                   "  F->>F: process + checkpoint barrier\n"
                   "  F->>O: pre-commit txn (stage rollup write)\n"
                   "  F->>F: checkpoint complete\n"
                   "  F->>O: commit txn\n"
                   "  Note over F,O: on crash, abort uncommitted txn; replay from checkpoint"
               )),
        _topic("sessionization-and-funnels",
               "Sessionization, Funnels, and Retention at Stream Scale",
               "Sessions and funnels are the queries that justify the entire analytics stack. "
               "Implemented well, they fall out of session windows + sketches; implemented "
               "poorly, they require full raw-event scans every dashboard load.",
               [
                   ("Session windows",
                    "Flink's eventTimeSessionWindows(Time.minutes(30)) keys by user_id and "
                    "groups events into sessions where consecutive events are < 30 min apart. "
                    "Session closes when the watermark passes the last event + 30 min. On "
                    "close, emit a session record with started_at, ended_at, event_count, "
                    "first/last event, duration_ms. Sessions feed both the OLAP table and a "
                    "downstream sessions Kafka topic for attribution consumers."),
                   ("Funnels via match_recognize or stream pattern",
                    "A funnel asks: of users who did event_A in [t0, t1], how many then did "
                    "event_B within W hours, then event_C? Two implementation patterns: "
                    "(1) Flink's CEP / pattern API — emit funnel-progression events to a "
                    "dedicated cube; (2) SQL match_recognize over raw events at query time — "
                    "flexible but slower. Pre-built funnel cubes are the fastest read path; "
                    "match_recognize is the catchall when the funnel definition changes per "
                    "query."),
                   ("Retention cohorts via sketches",
                    "Cohort = users who did the cohort event in week 0. Retention week N = "
                    "% of cohort active in week N. Implementation: rollup row per (cohort_week, "
                    "return_week) with HLL of user_ids per cell. Retention = "
                    "cardinality(cohort_hll ∩ return_hll) / cardinality(cohort_hll). Theta "
                    "sketches make the intersection efficient. Storage: O(cohorts × weeks) "
                    "sketches, ~12KB each — tractable even at scale."),
                   ("Why pre-aggregating funnels is worth it",
                    "A 5-step funnel over 30 days at 100K daily-active users involves "
                    "millions of session reconstructions per query. Caching funnel results "
                    "in a dedicated cube (per-day per-funnel-id) turns dashboard load from "
                    "10s+ into < 500ms. Cost: a Flink job emitting funnel progressions per "
                    "user; storage proportional to (active funnels × users × time)."),
                   ("Late events and funnel correctness",
                    "A late event arriving 6h after a session window closed can change funnel "
                    "step completion. With allowed-lateness, the session window stays open, "
                    "the funnel cube is upserted, and dashboards eventually correct. Without "
                    "it, funnels show stale data. This is the single biggest argument for "
                    "long allowed-lateness on mobile-heavy clickstream."),
               ],
               diagram=(
                   "graph TD\n"
                   "  E[Events keyed by user_id] --> SW[Session Window 30m gap]\n"
                   "  SW --> S[Session Record: started_at, duration, events]\n"
                   "  S --> SesT[Sessions OLAP table]\n"
                   "  SW --> CEP[CEP Pattern: A → B → C within W]\n"
                   "  CEP --> FC[Funnel Cube per funnel_id × day]\n"
                   "  FC --> DASH[Dashboard]\n"
                   "  SW --> RC[Retention HLL per cohort_week × return_week]\n"
                   "  RC --> DASH"
               )),
        _topic("pre-aggregation-cubes-and-query-planning",
               "Pre-Aggregation Cubes, OLAP Schema, and the Query Planner",
               "Pre-aggregation is what turns 'sub-second dashboard over a billion events' from "
               "a fantasy into a Tuesday. The trick is choosing cube dimensions from real "
               "queries, not speculative coverage.",
               [
                   ("Cube dimension selection",
                    "Trace actual dashboard queries from logs for two weeks. Bucket by "
                    "(filter dimensions, group-by dimensions). The top 5-10 dimension "
                    "combinations cover 80% of queries. Build cubes for those. The long tail "
                    "falls back to raw scan — slower but correct. Don't try to cube every "
                    "dimension — storage = ∏(cardinalities) × time-buckets, which explodes "
                    "fast."),
                   ("Time-bucket hierarchy",
                    "Build minute, hour, day rollups. Queries over a 7-day range hit hour "
                    "rollups; over a 90-day range hit day rollups. Each higher level is "
                    "computed by merging the lower level (sum counts, max-merge HLL "
                    "registers). This compresses query cost: a 90-day query reads ~90 day-"
                    "rows, not 90 × 24 × 60 minute-rows."),
                   ("OLAP partitioning",
                    "Primary partition: time (day or hour). Secondary partition: tenant_id. "
                    "Within partition: bitmap indexes on common filter dimensions (event, "
                    "country, device, campaign). Columnar storage with dictionary encoding "
                    "for low-cardinality columns. Pre-agg row: (tenant, event, time-bucket, "
                    "country, device, count, sum_metric, hll_user_id, tdigest_latency)."),
                   ("Query planner: cube-first, raw-fallback",
                    "On query arrival: parse filters and group-bys; check if every requested "
                    "dimension is covered by a cube; if yes, hit the cube (sub-second); if "
                    "no, plan a raw scan with predicate pushdown to the columnar lake "
                    "(seconds). Bonus: when raw fallback is hit often for a particular "
                    "dimension combo, that's a signal to add a new cube."),
                   ("Sketch-aware aggregation",
                    "Counts and sums merge with SUM(); HLLs merge with a custom MERGE_HLL "
                    "function (element-wise max of registers); t-digests merge with their "
                    "merge operator. The query planner must understand which functions are "
                    "scalar SUM-like and which are sketch-merge — Druid, Pinot, ClickHouse "
                    "all expose sketch UDFs natively."),
                   ("Cube backfill and rebuild",
                    "When a new cube is added, backfill from the raw lake via Spark, then "
                    "switch the query planner to use it. When a cube logic changes (e.g., "
                    "new sketch type), Kappa-replay through Flink to regenerate. Cubes are "
                    "derived data — recoverable from raw + code."),
               ],
               diagram=(
                   "graph TD\n"
                   "  Q[Dashboard query] --> P[Query Planner]\n"
                   "  P --> CK{All dims in cube?}\n"
                   "  CK -->|Yes| C1[rollup_minute / rollup_hour / rollup_day]\n"
                   "  CK -->|No| R1[Raw Parquet scan via Trino/Athena]\n"
                   "  C1 --> M[Merge: SUM, MERGE_HLL, MERGE_TDIGEST]\n"
                   "  R1 --> M\n"
                   "  M --> D[Dashboard <1s for cubes, 1-5s for raw]"
               )),
        _topic("multi-tenant-isolation-and-cost",
               "Multi-Tenant Isolation, Quotas, and Cost Attribution",
               "An analytics platform serves many tenants on shared infrastructure. Without "
               "explicit isolation, one noisy tenant brings down everyone's dashboards.",
               [
                   ("Per-tenant rate limiting at collector",
                    "Token bucket per tenant_id, sized by plan tier (e.g., 1K/sec free, "
                    "100K/sec enterprise). Excess returns 429 with Retry-After; SDK queues "
                    "client-side. Avoids one tenant's traffic spike from filling the Kafka "
                    "buffer and starving everyone else."),
                   ("Dedicated topics or partitions for top tenants",
                    "Top 1% of tenants by volume get dedicated Kafka topics or large partition "
                    "ranges. Small tenants share. Routes the noisy-neighbor problem from "
                    "Kafka layer to topic layer where it can be operated independently."),
                   ("Keyed state isolation in Flink",
                    "Flink's keyed state partitions by (tenant_id, event, dim-cube). One "
                    "tenant's hot key (e.g., a viral event from one tenant) creates a hot "
                    "Flink slot, but doesn't share state with other tenants. Skew "
                    "monitoring: track per-key throughput and rebalance partitions for "
                    "outliers."),
                   ("OLAP partitioning by tenant",
                    "Primary partition by tenant_id ensures one tenant's slow query scans "
                    "only its own segments. Per-tenant resource pools (Druid: tier-aware "
                    "broker; ClickHouse: SET max_threads per profile) prevent one tenant "
                    "from monopolizing CPU/IO."),
                   ("Cost attribution",
                    "Track per-tenant: bytes ingested (Kafka), state size (Flink RocksDB), "
                    "rollup rows (OLAP), bytes scanned (raw fallback). Multiply by unit "
                    "costs to bill back. Without attribution, the cheapest tenants subsidize "
                    "the heaviest — and you can't price the platform."),
                   ("Per-tenant retention and schema isolation",
                    "Free tier: 7-day rollup retention, no raw access. Enterprise: 2-year "
                    "rollups, raw lake access via Athena. Schema registry enforces per-"
                    "tenant namespacing — tenant A's 'pageview' schema is independent of "
                    "tenant B's. Cross-tenant queries are not allowed."),
               ],
               diagram=(
                   "graph TD\n"
                   "  T1[Tenant 1: 5M/s] --> Q1[Quota: 100K/s]\n"
                   "  T2[Tenant 2: 100/s] --> Q2[Quota: 1K/s]\n"
                   "  Q1 --> KT1[Kafka: dedicated topic events_t1]\n"
                   "  Q2 --> KT2[Kafka: shared topic events_shared]\n"
                   "  KT1 --> F1[Flink slot tenant=1]\n"
                   "  KT2 --> F2[Flink slot tenant=2]\n"
                   "  F1 --> O[(OLAP partition by tenant)]\n"
                   "  F2 --> O\n"
                   "  O --> CA[Cost attribution: bytes×rate per tenant]"
               )),
        _topic("backfills-replay-and-correctness-sentinels",
               "Backfills via Kappa Replay and Nightly Correctness Sentinels",
               "Bug fixes, schema changes, and new dimensions all require reprocessing "
               "history. Kappa-style replay through the same operator graph keeps one "
               "codepath; a nightly batch sentinel keeps it honest.",
               [
                   ("Why backfills are inevitable",
                    "Every analytics platform encounters: 'we computed retention wrong for "
                    "the last 30 days' or 'we want a new dimension in the cube going back "
                    "90 days' or 'a producer was emitting bad data — fix it from week 12.' "
                    "Without a clean backfill story, every fix is a one-off Spark job in "
                    "a notebook somewhere."),
                   ("Kappa replay mechanics",
                    "Backfill = replay Kafka offset range [O_start, O_end] through the "
                    "current Flink graph. Run a separate Flink job (not the production one) "
                    "with consumer group = 'backfill-2026-04-01'. Reads from Kafka tiered "
                    "storage if O_start is past the hot retention. Sink writes to a "
                    "side-table or upserts the canonical rollup table — depending on "
                    "whether the backfill replaces or supplements the existing data."),
                   ("Kafka tiered storage as backfill substrate",
                    "Hot Kafka: 7 days local SSD. Tiered: 90+ days on S3, transparent to "
                    "consumers. Replays from tiered storage are slower (S3 read latency) "
                    "but operationally identical to hot replay — same offsets, same "
                    "deserialization, same operator graph."),
                   ("Nightly batch sentinel",
                    "Spark job runs over the raw Parquet lake every night, recomputes "
                    "rollups for the prior day from scratch, and diffs against the streaming "
                    "rollups in OLAP. Disagreement beyond tolerance (e.g., > 0.5%) pages the "
                    "on-call. Catches: silent stream bugs, late-event handling regressions, "
                    "schema drift, sketch corruption. The single best correctness check in "
                    "the system."),
                   ("Backfill idempotency",
                    "Backfill writes the same (tenant, event, time-bucket, dim-cube) keys "
                    "as production. Idempotent OLAP upsert (replace-by-key) absorbs the "
                    "rewrite without duplicates. If you skipped idempotent design upstream, "
                    "every backfill is a delete-then-rewrite ops nightmare."),
                   ("Schema evolution during backfill",
                    "If backfill adds a new dimension to a rollup, the cube's primary key "
                    "changes. Two strategies: (a) write to a v2 table, dual-read in the "
                    "query planner during a cutover window, drop v1 once backfill is done; "
                    "(b) add the column with a default for old rows, accept the lossy past. "
                    "(a) is correct; (b) is fast. Pick by stakes."),
               ],
               diagram=(
                   "graph TD\n"
                   "  RR[Replay request: offsets O0..O1] --> BF[Backfill Flink job]\n"
                   "  BF --> KT[Kafka tiered storage]\n"
                   "  KT --> BF\n"
                   "  BF --> O[(OLAP idempotent upsert)]\n"
                   "  RAW[Raw Parquet lake] --> SP[Spark sentinel nightly]\n"
                   "  SP --> RC[Recomputed rollups]\n"
                   "  RC -. diff .-> O\n"
                   "  RC -- > tolerance --> AL[Alert on-call]"
               )),
    ],
)
