"""SD-YouTube — Design YouTube (large-scale video upload, transcoding,
streaming, CDN). Mirrors the schema/shape of SD_01 in sd_questions.py."""
from __future__ import annotations

from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design YouTube",
    "Hard",
    "Design a planet-scale video platform supporting upload, transcoding, adaptive streaming, "
    "and global CDN distribution. The system must accept multi-GB uploads from creators, transcode "
    "into an adaptive bitrate (ABR) ladder, store masters durably, push popular content to edge POPs, "
    "and serve billions of viewers per day with sub-second start time. Cover view-count aggregation, "
    "comments/likes, live streaming (LL-HLS), recommendations, and ML-driven content moderation.",
    hints=[
        "Read-heavy by 1000:1 — design viewing path before upload path.",
        "Long-tail content distribution: 90% of watches hit 10% of catalog → tiered storage.",
        "Don't transcode on the upload edge — decouple via queue. Bursty traffic crushes ingest.",
        "ABR ladder + manifest is the unit of streaming, not raw mp4.",
        "View counts are eventual — Kafka → batch aggregator. Strong consistency = thundering herd.",
        "Live streaming and VOD share storage but have separate ingest/edge paths.",
    ],
    constraints=[
        "Uploads up to 256 GB / 12 hours per file",
        "2B+ MAU, 1B+ hours watched/day",
        "500 hours of video uploaded per minute",
        "Global audience — sub-second start, < 1% rebuffer ratio",
        "11 nines durability for masters; transcoded renditions are reproducible",
        "Cost-sensitive: cold archive for tail content",
    ],
    req_func=[
        "Upload video (chunked, resumable) with metadata",
        "Transcode to ABR ladder (240p–4K) and package HLS+DASH",
        "Stream adaptive video to web, mobile, TV with low start time",
        "Search, browse, recommend videos",
        "Comments, likes/dislikes, subscriptions",
        "Live streaming with LL-HLS (sub-3s glass-to-glass)",
        "Content moderation (ML + human review) before/after publish",
        "View count, watch time, engagement metrics",
    ],
    req_nonfunc=[
        "Upload p99 success > 99.9% (resumable across network drops)",
        "Playback start time p95 < 1s globally",
        "Rebuffer ratio < 1% on broadband, < 3% on mobile",
        "Durability 11 nines for masters; renditions reproducible from masters",
        "Read:write ratio ~1000:1 — optimize viewing path",
        "Eventual consistency acceptable for view counts/likes (seconds–minutes)",
        "Cost: tier hot/warm/cold storage; reclaim renditions for cold tail",
    ],
    estimation={
        "mau": "2B",
        "uploads_per_min": "500 hours of video/min → ~30K min/min = 0.5× realtime",
        "storage_per_video_master": "~1 GB avg master (10 min @ 1080p)",
        "storage_per_video_renditions": "~3-5× master across ABR ladder",
        "daily_uploads_storage": "~1 PB/day raw + 4 PB/day renditions",
        "watch_qps_peak": "~5M concurrent streams; ~50M manifest req/s peak",
        "cdn_egress": "200+ Tbps peak global egress",
        "transcode_cpu": "~10× realtime CPU per rendition × ladder size → massive batch fleet",
    },
    endpoints=[
        {"method": "POST", "path": "/upload/init",
         "description": "Initiate resumable upload; returns upload_id + signed URL",
         "body": "{title, description, size_bytes, mime, visibility}"},
        {"method": "PUT", "path": "/upload/{upload_id}/chunk",
         "description": "Upload chunk; supports Content-Range for resume",
         "body": "binary chunk; headers: Content-Range, X-Chunk-Hash"},
        {"method": "POST", "path": "/upload/{upload_id}/complete",
         "description": "Finalize upload; enqueue for transcoding"},
        {"method": "GET", "path": "/videos/{video_id}",
         "description": "Fetch video metadata + signed manifest URLs"},
        {"method": "GET", "path": "/manifest/{video_id}.m3u8",
         "description": "HLS master manifest (CDN-served)"},
        {"method": "GET", "path": "/segment/{rendition}/{seg}.ts",
         "description": "HLS segment (CDN-served, long TTL)"},
        {"method": "POST", "path": "/videos/{video_id}/view",
         "description": "Record a view event (fire-and-forget to Kafka)"},
        {"method": "POST", "path": "/videos/{video_id}/comments",
         "description": "Post a comment"},
        {"method": "POST", "path": "/live/{stream_key}/ingest",
         "description": "RTMP/SRT live ingest endpoint"},
        {"method": "GET", "path": "/live/{channel}.m3u8",
         "description": "LL-HLS manifest for live channel"},
    ],
    tables=[
        {"name": "videos",
         "columns": ["video_id VARCHAR(16) PK", "owner_id BIGINT", "title VARCHAR(255)",
                     "description TEXT", "duration_sec INT", "visibility VARCHAR(16)",
                     "status VARCHAR(16)", "created_at BIGINT", "published_at BIGINT",
                     "master_s3_key VARCHAR(255)", "manifest_url VARCHAR(255)"]},
        {"name": "renditions",
         "columns": ["video_id VARCHAR(16)", "rendition VARCHAR(16)", "codec VARCHAR(16)",
                     "bitrate_kbps INT", "width INT", "height INT", "s3_key VARCHAR(255)",
                     "PRIMARY KEY (video_id, rendition)"]},
        {"name": "view_events",
         "columns": ["event_id BIGINT PK", "video_id VARCHAR(16)", "user_id BIGINT",
                     "ts BIGINT", "watch_sec INT", "device VARCHAR(32)", "geo VARCHAR(8)"]},
        {"name": "view_counts",
         "columns": ["video_id VARCHAR(16) PK", "count BIGINT", "updated_at BIGINT"]},
        {"name": "comments",
         "columns": ["comment_id BIGINT PK", "video_id VARCHAR(16)", "user_id BIGINT",
                     "parent_id BIGINT", "body TEXT", "ts BIGINT"]},
        {"name": "likes",
         "columns": ["video_id VARCHAR(16)", "user_id BIGINT", "kind VARCHAR(8)",
                     "ts BIGINT", "PRIMARY KEY (video_id, user_id)"]},
        {"name": "moderation",
         "columns": ["video_id VARCHAR(16) PK", "ml_score FLOAT", "ml_labels JSON",
                     "decision VARCHAR(16)", "reviewer_id BIGINT", "decided_at BIGINT"]},
    ],
    indexes=[
        "(owner_id, published_at DESC) on videos — channel page",
        "(visibility, published_at DESC) on videos — recent feed",
        "FULLTEXT(title, description) on videos — search",
        "(video_id, ts DESC) on comments — top-of-thread",
        "(video_id) on view_events — partition by video for aggregation",
        "(rendition) on renditions — manifest assembly",
    ],
    hld_desc=(
        "Two decoupled planes. Upload plane: resumable chunked upload → object store → transcode "
        "queue → ABR fleet → packager → manifest writer. View plane: edge CDN with origin-shield "
        "tiers → object store for masters/renditions → metadata service for video info. Asynchronous "
        "data-plane: Kafka collects view/like/comment events; batch + stream aggregators update "
        "counters. Live plane: RTMP/SRT ingest → realtime transcoder → LL-HLS packager → CDN."
    ),
    hld_components=[
        {"name": "Upload Edge", "role": "Chunked resumable upload to nearest region"},
        {"name": "Object Store", "role": "S3-class store for masters + renditions"},
        {"name": "Transcode Orchestrator", "role": "Schedules ABR jobs on GPU/CPU fleet"},
        {"name": "Packager", "role": "Produces HLS/DASH manifests + segment maps"},
        {"name": "Metadata Service", "role": "Video CRUD, search, recommendation reads"},
        {"name": "CDN (Edge POPs)", "role": "Serves manifests + segments from edge"},
        {"name": "Origin Shield", "role": "Mid-tier cache to protect origin storage"},
        {"name": "View Aggregator", "role": "Kafka-fed batch+stream counter updates"},
        {"name": "Comments Service", "role": "Sharded comment store, eventual consistency"},
        {"name": "Live Ingest", "role": "RTMP/SRT → realtime transcoder → LL-HLS"},
        {"name": "Moderation Pipeline", "role": "ML scan + human review queue"},
        {"name": "Recommendation Service", "role": "Candidate gen + ranking; embedding store"},
    ],
    detailed_design={
        "upload_pipeline": (
            "Resumable chunked upload (5–25 MB chunks) using signed URLs to nearest regional bucket. "
            "Client computes per-chunk hash; server verifies on PUT. Composite multi-part complete "
            "stitches chunks; emits 'upload.complete' to Kafka. Validation step: header sniff + ffprobe "
            "for codec/duration/integrity; ClamAV-style malware scan on the raw container. Reject early "
            "if codec/container disallowed."
        ),
        "transcoding_ladder": (
            "ABR ladder: 240p (300 kbps), 360p (700 kbps), 480p (1.2 Mbps), 720p (2.5 Mbps), "
            "1080p (5 Mbps), 1440p (9 Mbps), 4K (16 Mbps). Codec selection: H.264 universal fallback, "
            "H.265/HEVC for premium devices, AV1 for top tier (savings 30% bandwidth). Transcode is "
            "embarrassingly parallel — split master into GOP-aligned chunks, fan out to fleet, reduce. "
            "Each rendition packaged into HLS (.ts/CMAF) and DASH segments (~6s segments; 2s for live). "
            "Manifest writer emits master + variant playlists and stores in object store."
        ),
        "storage_tiering": (
            "Master: 11-nines durable object store (cross-region replication); kept forever for the "
            "tail. Renditions: warm tier with regional caching for active catalog. Hot CDN tier for "
            "trending (last 7 days, top creators) — pre-warmed. Cold archive (Glacier-class) for "
            "videos with < 1 view/month; renditions deleted (regenerable from master). Lifecycle "
            "policies move data automatically based on access frequency."
        ),
        "cdn_strategy": (
            "Three-tier edge: client → nearest POP (200+ globally) → regional origin shield (10–20) "
            "→ object store. Geo-routing via anycast + DNS GSLB. Origin shield collapses requests to "
            "protect storage during cache miss storms. Long TTL (1 year) on segments — they're "
            "immutable; manifest TTL ~5min for catalog updates. Tokenized URLs for paid/private content."
        ),
        "metadata_db": (
            "Metadata sharded by video_id (consistent hash). Hot path read-through cache (Memcached/"
            "Redis). Search: Elasticsearch index updated via CDC from primary store. "
            "Recommendation pipeline: offline candidate generation (matrix factorization, two-tower "
            "embedding) + online ranking (gradient-boosted trees / DNN) — served via low-latency "
            "model server with feature store."
        ),
        "view_count_aggregation": (
            "Each play emits a view event to Kafka (fire-and-forget from client SDK). Two pipelines: "
            "(1) Stream aggregator (Flink) windows 1-minute counts and increments a Redis HLL for "
            "approximate near-real-time counts shown on UI. (2) Batch aggregator (Spark) hourly "
            "deduplicates by (video, user, hour) and writes authoritative counts to view_counts. "
            "Anti-fraud filters bots before increment."
        ),
        "comments_likes": (
            "Comments sharded by video_id; threaded via parent_id. Eventual consistency — write to "
            "primary, async fan-out to read replicas + cache invalidation via pub/sub. Likes are "
            "idempotent UPSERTs; aggregate count maintained via stream aggregator like view counts. "
            "Spam/toxicity ML scan inline; flagged for review."
        ),
        "live_streaming": (
            "RTMP or SRT ingest; transcoder produces LL-HLS (low-latency HLS) with chunked transfer "
            "encoding and CMAF segments (~1s chunks, ~3s glass-to-glass). DVR window kept in hot "
            "object store. Live → VOD: post-stream pipeline re-packages full recording and triggers "
            "standard transcode for higher renditions if needed."
        ),
        "content_moderation": (
            "Pre-publish ML pipeline: thumbnail/frame sampling + audio classifier + OCR for text in "
            "video. Models flag categories (violence, nudity, copyright). High-confidence violations "
            "auto-block; ambiguous routed to human review queue with priority by creator reach. "
            "Copyright: Content-ID style audio/video fingerprint match against rights-holder DB."
        ),
        "slo_contract": (
            "Upload success p99 > 99.9%. Transcode SLA: 720p ready < 5 min for sub-30-min videos. "
            "Playback start p95 < 1s. Rebuffer < 1%. View count freshness: < 60s for stream est., "
            "< 1h for authoritative."
        ),
    },
    trade_offs=[
        {"option": "Synchronous vs asynchronous transcoding",
         "for_sync": "Simpler; video ready immediately for owner",
         "for_async": "Decouples bursty uploads; cheaper batch fleets",
         "recommendation": "Async with progressive availability — 360p first, higher tiers stream in."},
        {"option": "Transcode all renditions vs lazy / JIT",
         "for_all": "Predictable latency; simple manifests",
         "for_jit": "Cheaper for tail content; only popular tiers materialised",
         "recommendation": "Transcode core tiers (360p/720p) eagerly; high tiers (4K/AV1) JIT or for popular only."},
        {"option": "View count: strong vs eventual consistency",
         "for_strong": "Exact counts visible immediately",
         "for_eventual": "Massively cheaper; ~minute lag is fine",
         "recommendation": "Eventual via Kafka + Flink. Show approximate near-real-time."},
        {"option": "HLS vs DASH",
         "for_hls": "Apple-native; ubiquitous on iOS/tvOS",
         "for_dash": "Open standard; richer codec support",
         "recommendation": "Both — share CMAF segments, dual manifests."},
        {"option": "Codec: H.264 vs H.265 vs AV1",
         "for_h264": "Universal hardware decode; royalty murky but ubiquitous",
         "for_h265": "30-50% bitrate savings; royalty/licensing risk",
         "for_av1": "30-50% better than H.264; royalty-free; encode cost still high",
         "recommendation": "H.264 always; AV1 for top creators / 1080p+ on supported clients."},
    ],
    tips=[
        "Lead with read:write ratio (1000:1) — drives CDN-first design.",
        "Don't transcode on the upload edge — decouple via queue. Bursty traffic kills sync designs.",
        "ABR ladder + HLS/DASH manifest is the unit of streaming. Naming each tier earns senior signal.",
        "View counts are eventual — never propose a SQL increment on every play.",
        "Mention origin shield — it's the missing tier most candidates skip and shows multi-tier CDN thinking.",
        "Tier storage: hot CDN, warm regional, cold archive. Renditions for cold content are deleted (regenerable).",
        "For live: LL-HLS with CMAF chunks, sub-3s glass-to-glass. Don't propose RTMP-only.",
    ],
    thought_process=[
        "1. Clarify: VOD + live? Global? Read:write ratio? Latency target?",
        "2. Estimate: 500 hr/min uploads → 1 PB/day; 2B MAU; 200+ Tbps egress.",
        "3. Upload plane: chunked resumable → object store → transcode queue.",
        "4. Transcode: ABR ladder, GOP-parallel, package HLS/DASH (CMAF).",
        "5. Storage tiering: master (forever), renditions (regenerable), CDN hot tier, cold archive.",
        "6. View plane: edge POPs → origin shield → object store; long-TTL segments.",
        "7. Metadata: sharded SQL + ES for search; cache hot reads.",
        "8. View counts: Kafka → Flink (near-real-time) + Spark (authoritative).",
        "9. Comments/likes: separate service, eventual consistency.",
        "10. Live: RTMP/SRT ingest → LL-HLS packager.",
        "11. Moderation: ML pre-scan + human review queue + Content-ID for copyright.",
    ],
    tags=["video", "streaming", "cdn", "transcoding", "large-scale"],
    arch_nodes=[
        {"id": "client", "label": "Web / Mobile / TV", "type": "client"},
        {"id": "upload_edge", "label": "Upload Edge", "type": "lb"},
        {"id": "obj_store", "label": "Object Store (Masters)", "type": "database"},
        {"id": "queue", "label": "Transcode Queue", "type": "service"},
        {"id": "transcode", "label": "Transcode Fleet (GPU/CPU)", "type": "server"},
        {"id": "packager", "label": "HLS/DASH Packager", "type": "server"},
        {"id": "rendition_store", "label": "Rendition Store", "type": "database"},
        {"id": "cdn", "label": "CDN Edge POPs", "type": "cache"},
        {"id": "shield", "label": "Origin Shield", "type": "cache"},
        {"id": "meta", "label": "Metadata Service", "type": "server"},
        {"id": "meta_db", "label": "Metadata DB", "type": "database"},
        {"id": "search", "label": "Search (ES)", "type": "database"},
        {"id": "kafka", "label": "Kafka (events)", "type": "service"},
        {"id": "flink", "label": "Stream Aggregator", "type": "server"},
        {"id": "spark", "label": "Batch Aggregator", "type": "server"},
        {"id": "live_ingest", "label": "Live Ingest (RTMP/SRT)", "type": "server"},
        {"id": "moderation", "label": "Moderation ML", "type": "service"},
        {"id": "rec", "label": "Recommendation", "type": "service"},
    ],
    arch_edges=[
        {"source": "client", "target": "upload_edge", "label": "chunked upload"},
        {"source": "upload_edge", "target": "obj_store", "label": "master"},
        {"source": "upload_edge", "target": "queue", "label": "enqueue"},
        {"source": "queue", "target": "transcode"},
        {"source": "transcode", "target": "packager"},
        {"source": "packager", "target": "rendition_store"},
        {"source": "packager", "target": "meta", "label": "manifest URL"},
        {"source": "client", "target": "cdn", "label": "watch"},
        {"source": "cdn", "target": "shield", "label": "miss"},
        {"source": "shield", "target": "rendition_store", "label": "miss"},
        {"source": "client", "target": "meta", "label": "video metadata"},
        {"source": "meta", "target": "meta_db"},
        {"source": "meta", "target": "search"},
        {"source": "client", "target": "kafka", "label": "view/like/comment events"},
        {"source": "kafka", "target": "flink", "label": "stream"},
        {"source": "kafka", "target": "spark", "label": "batch"},
        {"source": "flink", "target": "meta_db", "label": "near-RT counts"},
        {"source": "spark", "target": "meta_db", "label": "authoritative"},
        {"source": "client", "target": "live_ingest", "label": "RTMP/SRT"},
        {"source": "live_ingest", "target": "transcode"},
        {"source": "transcode", "target": "moderation"},
        {"source": "moderation", "target": "meta", "label": "decision"},
        {"source": "meta", "target": "rec"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant C as Creator\n"
        "  participant UE as Upload Edge\n"
        "  participant S3 as Object Store\n"
        "  participant Q as Transcode Queue\n"
        "  participant T as Transcoder\n"
        "  participant P as Packager\n"
        "  participant CDN\n"
        "  participant V as Viewer\n"
        "  C->>UE: POST /upload/init\n"
        "  UE-->>C: upload_id, signed URL\n"
        "  loop chunks\n"
        "    C->>UE: PUT /chunk\n"
        "    UE->>S3: write chunk\n"
        "  end\n"
        "  C->>UE: POST /complete\n"
        "  UE->>Q: enqueue(video_id)\n"
        "  Q->>T: claim job\n"
        "  T->>S3: read master\n"
        "  T->>T: ABR ladder\n"
        "  T->>P: renditions\n"
        "  P->>S3: HLS/DASH segments + manifest\n"
        "  V->>CDN: GET manifest.m3u8\n"
        "  CDN-->>V: manifest\n"
        "  V->>CDN: GET segment_*.ts\n"
        "  CDN-->>V: bytes\n"
    ),
    er_diagram=(
        "erDiagram\n"
        "  USER ||--o{ VIDEO : uploads\n"
        "  VIDEO ||--o{ RENDITION : has\n"
        "  VIDEO ||--o{ VIEW_EVENT : receives\n"
        "  VIDEO ||--o{ COMMENT : has\n"
        "  VIDEO ||--o{ LIKE : receives\n"
        "  VIDEO ||--|| MODERATION : gated_by\n"
        "  VIDEO { string video_id\n bigint owner_id\n string title\n int duration_sec\n string status }\n"
        "  RENDITION { string video_id\n string rendition\n string codec\n int bitrate_kbps }\n"
        "  VIEW_EVENT { bigint event_id\n string video_id\n bigint user_id\n bigint ts }\n"
        "  COMMENT { bigint comment_id\n string video_id\n bigint user_id\n bigint parent_id }\n"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B{Read:write ratio}\n"
        "  B -->|1000:1| C[CDN-first design]\n"
        "  C --> D[Decouple upload from transcode via queue]\n"
        "  D --> E[ABR ladder + HLS/DASH]\n"
        "  E --> F[Tier storage: hot/warm/cold]\n"
        "  F --> G[Eventual counts via Kafka + Flink]\n"
        "  G --> H[Live = LL-HLS branch]\n"
        "  H --> I[Moderation: ML + human review]\n"
    ),
    tradeoff_title="Eager full-ladder transcode vs Just-in-Time renditions",
    tradeoff_options=[
        {"label": "Eager: transcode entire ABR ladder on upload",
         "description": "Every video gets every rendition immediately upon upload completion.",
         "pros": ["Predictable playback latency", "Simple manifest logic",
                  "No first-watch warm-up"],
         "cons": ["Wastes compute + storage on tail (90% never re-watched)",
                  "Expensive top tiers (4K/AV1) generated for videos no one watches",
                  "Slow time-to-publish for long videos"]},
        {"label": "JIT: transcode on first request per rendition",
         "description": "Generate higher renditions only when a viewer requests them.",
         "pros": ["Cheap for tail content", "Top tiers materialized only for popular videos",
                  "Faster initial publish (just 360p)"],
         "cons": ["First-viewer latency spike", "Complex orchestration",
                  "Cache stampede risk when videos go viral"]},
        {"label": "Hybrid (recommended)",
         "description": "Eager core tiers (360p/720p); JIT or popularity-triggered for higher (1080p+/AV1).",
         "pros": ["Fast publish + cheap tail + on-demand top tiers",
                  "Storage reclaim for cold content"],
         "cons": ["More moving parts; needs popularity signal feedback loop"]},
    ],
    tradeoff_rec=(
        "Hybrid. Eager 360p+720p H.264 for universal playback; JIT or popularity-triggered for "
        "1080p+, HEVC, AV1. Reclaim higher-tier renditions for content that's cold for 30+ days."
    ),
    senior_topics=[
        _topic("abr-and-cmaf",
               "ABR Ladder, HLS/DASH, and CMAF Convergence",
               "Adaptive bitrate streaming requires segmented media + manifest. CMAF unifies HLS "
               "and DASH on a single segment format, halving storage and CDN cost.",
               [
                   ("Why ABR",
                    "Network bandwidth varies; player measures throughput and switches between "
                    "renditions. Ladder bitrates are spaced ~1.5–2× apart so switches are stable."),
                   ("HLS vs DASH",
                    "HLS = .m3u8 manifest + .ts (or fMP4) segments; native on Apple. DASH = .mpd + "
                    "ISO-BMFF segments; open standard. Both are protocols on top of segmented media."),
                   ("CMAF as the unifier",
                    "CMAF = ISO-BMFF chunked media. Same segment files served by both HLS (with "
                    "fMP4) and DASH manifests. Single set of segments → one storage, one cache key."),
                   ("Low-latency variants",
                    "LL-HLS uses partial segments (CMAF chunks) + HTTP/2 push to drop latency from "
                    "~30s (classic HLS) to ~3s. LL-DASH uses chunked transfer encoding."),
                   ("Manifest writer responsibilities",
                    "Generates master + variant playlists, lists segment URLs, declares codec "
                    "(avc1, hvc1, av01), bandwidth, resolution. Updates on live as new chunks land."),
               ],
               diagram=(
                   "graph LR\n"
                   "  M[Master Video] --> T[Transcode]\n"
                   "  T --> R1[CMAF 240p]\n"
                   "  T --> R2[CMAF 720p]\n"
                   "  T --> R3[CMAF 4K AV1]\n"
                   "  R1 & R2 & R3 --> H[HLS Manifest]\n"
                   "  R1 & R2 & R3 --> D[DASH Manifest]\n"
                   "  H & D --> CDN\n"
                   "  CDN --> Player\n"
               )),
        _topic("cdn-tiers",
               "Multi-Tier CDN: Edge, Origin Shield, Origin",
               "A flat edge cache against an origin storage layer is fragile under cache miss storms. "
               "Origin shield is the senior pattern that protects storage and reduces fan-in.",
               [
                   ("Why a flat CDN fails at scale",
                    "200+ POPs each missing simultaneously on a viral video issue 200 parallel "
                    "requests to origin storage — storage thrashes, segment latency spikes."),
                   ("Origin shield as request collapser",
                    "Mid-tier of 10–20 regional caches. POPs miss to their assigned shield POP; "
                    "shield collapses concurrent requests, fetches once from origin, then fans out."),
                   ("Geo-routing",
                    "Anycast IP + DNS GSLB pin user to nearest healthy POP based on RTT + load. "
                    "Cross-region failover within seconds when a POP is degraded."),
                   ("TTL strategy",
                    "Segments are content-addressed and immutable → 1-year TTL. Manifests are "
                    "short TTL (30s–5min) to reflect catalog changes for live or new uploads."),
                   ("Pre-warm for predictable spikes",
                    "Major creators' premiere videos are pushed into edge cache before the publish "
                    "time. New trending detection triggers reactive pre-warm to top POPs."),
               ],
               diagram=(
                   "graph TD\n"
                   "  V[Viewer] --> E[Edge POP]\n"
                   "  E -->|miss| S[Origin Shield]\n"
                   "  S -->|miss| O[Object Store Origin]\n"
                   "  O --> S\n"
                   "  S --> E\n"
                   "  E --> V\n"
               )),
        _topic("view-counts-eventual",
               "View Count Aggregation: Lambda Architecture",
               "Strong-consistency view counts are intractable at billions of plays/day. The "
               "industry pattern is lambda: stream layer for fast approximate, batch layer for "
               "authoritative.",
               [
                   ("Why not SQL UPDATE on every play",
                    "Hot rows (viral video) become single-row contention bottlenecks. Sharding by "
                    "video helps but a top video can still saturate a shard."),
                   ("Stream layer (Flink + Redis HLL)",
                    "Plays land in Kafka. Flink job windows by minute, increments per-video "
                    "HyperLogLog in Redis for unique-viewer estimate. UI shows estimate within ~60s."),
                   ("Batch layer (Spark)",
                    "Hourly job dedupes by (video, user, hour) bucket from Kafka archive in S3, "
                    "writes authoritative count to view_counts table. Used for monetization."),
                   ("Anti-fraud filter",
                    "Bot detection inline in Flink: heuristics (UA, IP rate, watch_sec=0) plus "
                    "ML scoring. Flagged events excluded from increments."),
                   ("Reconciliation",
                    "Batch layer is source of truth; stream estimate clamped if it drifts more "
                    "than X% on the next batch run."),
               ],
               diagram=(
                   "graph LR\n"
                   "  P[Player] --> K[Kafka view events]\n"
                   "  K --> F[Flink stream]\n"
                   "  F --> R[Redis HLL near-RT]\n"
                   "  K --> S3[S3 events archive]\n"
                   "  S3 --> SP[Spark batch]\n"
                   "  SP --> DB[view_counts authoritative]\n"
                   "  R & DB --> UI[Watch page]\n"
               )),
        _topic("live-ll-hls",
               "Live Streaming with LL-HLS / CMAF",
               "Live needs sub-3s glass-to-glass without abandoning HTTP-based delivery. LL-HLS "
               "with CMAF chunked transfer is the modern answer.",
               [
                   ("Ingest protocols",
                    "RTMP (legacy, ubiquitous in OBS) or SRT (loss recovery, lower latency). "
                    "WebRTC for sub-second contributor cases."),
                   ("Realtime transcode",
                    "Ingest → ABR ladder transcoded with hardware encoders (NVENC) for realtime "
                    "performance. Lower ladder for live (e.g., skip 4K) to keep encode budget."),
                   ("LL-HLS partial segments",
                    "Each segment broken into ~250ms parts. Player pulls part-by-part using "
                    "HTTP/2 push or blocking playlist reload. Manifest updates with each part."),
                   ("CDN considerations",
                    "Edge must support chunked transfer encoding and not buffer full segments. "
                    "Manifest TTL effectively zero — use HTTP/2 server push or websocket signaling."),
                   ("Live-to-VOD",
                    "Post-stream, full recording packaged as standard VOD; higher renditions "
                    "transcoded offline. DVR window kept hot during live."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant Cr as Creator (OBS)\n"
                   "  participant In as RTMP Ingest\n"
                   "  participant T as Realtime Transcoder\n"
                   "  participant Pk as LL-HLS Packager\n"
                   "  participant CDN\n"
                   "  participant V as Viewer\n"
                   "  Cr->>In: RTMP/SRT stream\n"
                   "  In->>T: raw\n"
                   "  T->>Pk: ABR renditions\n"
                   "  Pk->>CDN: CMAF parts (250ms)\n"
                   "  V->>CDN: GET part_N\n"
                   "  CDN-->>V: chunked\n"
               )),
        _topic("moderation-pipeline",
               "Content Moderation: ML Pre-Scan + Human Review",
               "At 500 hours/min, manual review of every upload is impossible. Tiered ML + human-in-"
               "the-loop with Content-ID for copyright is the operational pattern.",
               [
                   ("ML pre-publish scan",
                    "Sample frames + audio classifier + OCR. Models score categories: violence, "
                    "nudity, hate, copyright likelihood. High-confidence violations auto-block."),
                   ("Human review queue",
                    "Ambiguous cases queued; priority-ranked by creator reach and predicted "
                    "watch-time. Review tooling timestamps offending segments for fast adjudication."),
                   ("Content-ID for copyright",
                    "Audio + video fingerprint of upload matched against rights-holder DB. Match "
                    "triggers configured policy: block, monetize-for-owner, or track."),
                   ("Post-publish signals",
                    "User reports, comment toxicity ML, watch-pattern anomalies feed re-review. "
                    "Strikes accumulate per channel."),
                   ("Latency vs accuracy",
                    "Pre-publish ML must run < ~minute to keep publish UX fast; if review needed, "
                    "video published in 'pending' state; only monetization gated."),
               ]),
        _topic("storage-tiering-cost",
               "Storage Tiering for Long-Tail Catalog",
               "90% of watches hit 10% of the catalog. Tier storage by access frequency to reclaim "
               "cost while preserving the long tail.",
               [
                   ("Hot CDN tier",
                    "Trending + last-7-day uploads + top creators pre-warmed. Bytes priced highest "
                    "but offset by aggressive cache hit rate (>95%)."),
                   ("Warm regional tier",
                    "Active catalog (watched in last 90 days). Standard object storage in 2-3 "
                    "regions. Renditions fully materialized."),
                   ("Cold archive tier",
                    "Glacier-class. Master only — renditions deleted (regenerable from master). "
                    "First view after move triggers async re-transcode + warm-up; user sees a "
                    "couple-minute 'preparing video' state on the rare cold play."),
                   ("Lifecycle automation",
                    "Daily job: read access counters, move objects between tiers based on policy "
                    "(no plays in 30 days → warm; 90 days → cold; rare new creator: pin)."),
                   ("Cost vs UX",
                    "Cold-tier latency hit affects only the very long tail; trade is justified by "
                    "the 100×+ storage cost saving on rarely-watched content."),
               ]),
    ],
)
