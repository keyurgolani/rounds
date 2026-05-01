"""Instagram system design question. Loaded automatically via
`sd_questions._load_more` because this module exposes `PAYLOAD`."""
from __future__ import annotations

from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design Instagram",
    "Hard",
    "Design Instagram: a photo + short-video (Reels) social platform with a follow graph, ranked home "
    "feed, hashtag/user search, stories with TTL, likes/comments, DMs, and notifications. Must scale to "
    "billions of users globally with sub-second feed open and tight media delivery latency. Focus on the "
    "feed-generation hot path; DM is a secondary surface that defers to the chat design.",
    hints=[
        "Feed generation is the core decision: pull (compute on read), push (fan-out on write), or hybrid.",
        "Hybrid wins at Instagram scale: push for normal users, pull for celebrities (avoid 100M-row fan-out).",
        "Photos and reels are blob workloads — never put bytes in the relational DB. CDN + object store.",
        "Follow graph is read-heavy and skewed (power-law). Shard by follower_id; cache hot fan-in lists.",
        "Hashtag and user search needs Elasticsearch — autocomplete + ranked relevance is not a SQL query.",
        "Stories have TTL (24h) — separate hot store with expiry, don't pollute the main media corpus.",
    ],
    constraints=[
        "2B+ monthly users, ~500M DAU",
        "100M+ photos and reels uploaded per day",
        "Power-law follow graph: top accounts have 100M+ followers",
        "Feed open p99 < 1s; first-frame reel start p99 < 500ms",
        "Stories expire after 24 hours",
        "Global — multi-region with edge media delivery",
    ],
    req_func=[
        "Upload photo or short video; transcode into multiple variants",
        "Follow / unfollow users; bidirectional follow graph queries",
        "Ranked home feed mixing photos and reels from followed accounts",
        "Likes, comments, mentions, saves",
        "Stories with 24h TTL",
        "Hashtag and user search with autocomplete",
        "Notifications: bell icon (likes/follows/mentions/comments)",
        "DMs (1:1 + group) — defers to the dedicated chat design",
    ],
    req_nonfunc=[
        "Feed open p99 < 1s; reel start p99 < 500ms",
        "99.95% availability for read paths; uploads can be eventual",
        "Heavily read-skewed — caching is the primary scale lever",
        "Eventual consistency for feed inclusion (a post may take seconds to appear in followers' feeds)",
        "Durable storage for media — zero photo loss",
        "Bandwidth-efficient — adaptive bitrate for reels, responsive variants for photos",
    ],
    estimation={
        "dau": "500M",
        "uploads_per_day": "100M photos + 50M reels",
        "feed_opens_per_day": "~5B",
        "qps_feed_read": "~60K/sec global steady; 500K/sec peak",
        "qps_upload": "~1.7K/sec photos, ~600/sec reels",
        "media_storage_per_day": "~50TB photos + ~150TB reels (multi-variant)",
        "follow_edges": "~200B edges (avg 400 follows/user)",
    },
    endpoints=[
        {"method": "POST", "path": "/media/upload",
         "description": "Initiate upload — returns presigned S3 URL",
         "body": "{kind: photo|reel, mime, size_bytes}"},
        {"method": "POST", "path": "/posts",
         "description": "Create post after media upload completes",
         "body": "{media_id, caption, hashtags:[], mentions:[], location?}"},
        {"method": "GET", "path": "/feed",
         "description": "Ranked home feed for authenticated user",
         "body": "?cursor=opaque&limit=20"},
        {"method": "POST", "path": "/follow/{user_id}",
         "description": "Follow a user (creates edge)"},
        {"method": "DELETE", "path": "/follow/{user_id}",
         "description": "Unfollow"},
        {"method": "GET", "path": "/search",
         "description": "Search users + hashtags (autocomplete)",
         "body": "?q=<prefix>&kind=user|hashtag"},
        {"method": "POST", "path": "/stories",
         "description": "Post a 24h story",
         "body": "{media_id}"},
        {"method": "GET", "path": "/notifications",
         "description": "Bell-icon feed of recent activity"},
    ],
    tables=[
        {"name": "users",
         "columns": ["id BIGINT PK", "handle VARCHAR(32) UNIQUE", "name VARCHAR",
                     "follower_count BIGINT", "is_celebrity BOOL", "created_at BIGINT"]},
        {"name": "posts",
         "columns": ["id BIGINT PK", "user_id BIGINT", "kind VARCHAR(8)",
                     "media_id VARCHAR(64)", "caption TEXT", "hashtags JSONB",
                     "created_at BIGINT", "like_count INT", "comment_count INT"]},
        {"name": "follows",
         "columns": ["follower_id BIGINT", "followee_id BIGINT", "created_at BIGINT",
                     "PRIMARY KEY (follower_id, followee_id)"]},
        {"name": "user_feed",
         "columns": ["user_id BIGINT", "post_id BIGINT", "score FLOAT",
                     "inserted_at BIGINT", "PRIMARY KEY (user_id, inserted_at, post_id)"]},
        {"name": "stories",
         "columns": ["id BIGINT PK", "user_id BIGINT", "media_id VARCHAR(64)",
                     "expires_at BIGINT"]},
        {"name": "likes",
         "columns": ["post_id BIGINT", "user_id BIGINT", "created_at BIGINT",
                     "PRIMARY KEY (post_id, user_id)"]},
        {"name": "notifications",
         "columns": ["id BIGINT PK", "user_id BIGINT", "kind VARCHAR(16)",
                     "actor_id BIGINT", "object_id BIGINT", "created_at BIGINT", "read BOOL"]},
    ],
    indexes=[
        "(follower_id) on follows — list followees",
        "(followee_id) on follows — list followers (sharded)",
        "(user_id, created_at DESC) on posts",
        "(user_id, inserted_at DESC) on user_feed — feed read",
        "(expires_at) on stories — TTL sweeper",
        "(user_id, created_at DESC, read) on notifications",
    ],
    hld_desc=(
        "Hybrid feed: most posts fan-out on write into per-user materialised feeds (Redis sorted sets + "
        "Cassandra). Celebrity posts are NOT fanned out — read-time merge pulls celeb timelines on feed "
        "open. Media uploaded via presigned S3 URLs; transcoding pipeline produces photo variants and "
        "reel ABR ladders, served via CDN. Search is Elasticsearch over users + hashtags. Stories have a "
        "TTL store with sweeper. Notifications are a fan-out service writing into per-user inbox."
    ),
    hld_components=[
        {"name": "Mobile / Web Clients", "role": "Render feed, capture media, autocomplete search"},
        {"name": "API Gateway", "role": "Auth, rate-limit, region-route"},
        {"name": "Upload Service", "role": "Issue presigned S3 URLs; record media metadata"},
        {"name": "Transcoding Pipeline", "role": "Photo variants + reel ABR ladders; emit ready event"},
        {"name": "Post Service", "role": "Persist post, emit fan-out event"},
        {"name": "Fan-out Worker", "role": "Push post into followers' user_feed (skip celebrities)"},
        {"name": "Feed Service", "role": "Read user_feed + merge celeb timelines, rank, paginate"},
        {"name": "Follow Service", "role": "Follow graph CRUD; cache hot followee lists"},
        {"name": "Search (Elasticsearch)", "role": "User + hashtag autocomplete and ranked search"},
        {"name": "Story Service", "role": "TTL-bounded story store with sweeper"},
        {"name": "Notification Service", "role": "Fan-out activity into per-user inbox"},
        {"name": "Media CDN", "role": "Edge-cache photos and reel segments"},
        {"name": "Object Store (S3)", "role": "Durable origin for all media variants"},
    ],
    detailed_design={
        "feed_generation_hybrid": (
            "Push (fan-out on write) for the long tail: when a normal user posts, a worker enumerates "
            "followers and inserts (post_id, score, ts) into each follower's user_feed shard. Pull "
            "(read-time merge) for celebrities: posts by users with is_celebrity=true skip fan-out; on "
            "feed open the Feed Service reads the user's pushed feed AND fetches recent posts from the "
            "set of celebrities the user follows, then merges + ranks. Threshold for celebrity is "
            "follower_count > ~1M — fan-out cost would be 100M+ writes per post otherwise."
        ),
        "ranking": (
            "Inputs: recency, affinity (interaction history with author), engagement velocity (likes/min), "
            "media-type preference, predicted dwell. Lightweight ranker at read time over the merged "
            "candidate set (~few hundred items). Heavy ranking can run async to refresh user_feed scores."
        ),
        "media_pipeline": (
            "Client requests presigned S3 URL → uploads directly to S3 (offload from app servers). On "
            "S3 ObjectCreated event a transcoder reads the object: photos → 320/640/1080/1440 webp + "
            "thumbnail; reels → HLS/DASH ABR ladder (240p/480p/720p/1080p) + thumbnail + first-frame "
            "poster. Variants written to S3, surfaced via CDN. Post becomes visible only after "
            "transcode completes (processing → ready state)."
        ),
        "follow_graph": (
            "follows table sharded by follower_id (cheap to list a user's followees on feed open). "
            "Reverse index sharded by followee_id for the fan-out worker. Hot followee lists cached "
            "in Redis; hot follower lists for celebrities are NOT cached — celebs use the pull path."
        ),
        "hashtag_indexing": (
            "On post create, hashtags extracted and indexed into Elasticsearch with the post_id. A "
            "hashtag page query is a sorted ES search by recency × engagement. Trending hashtags from "
            "a streaming aggregation (Flink) over the last 1h posts."
        ),
        "stories_ttl": (
            "Stories live in a dedicated table with expires_at = created_at + 24h. A sweeper deletes "
            "expired rows; viewed records also expire. Story media in S3 has lifecycle rule for cold "
            "tier after 24h (kept for archive feature) but removed from CDN."
        ),
        "reels_pipeline": (
            "Same shape as YouTube but smaller files (≤90s, ~10–30MB). Vertical 9:16 only. ABR HLS so "
            "first-frame is fast — request lowest rendition first, upgrade as bandwidth allows. "
            "Pre-fetch next 1–2 reels in the scroller to mask startup."
        ),
        "search": (
            "Elasticsearch index over users (handle, name, bio) and hashtags. Autocomplete via "
            "edge-ngram analyzer. Ranking blends popularity (follower_count, post engagement), "
            "personalised affinity (do I follow this person? do my friends?), and prefix match score."
        ),
        "notifications": (
            "On like/comment/follow/mention, Notification Service writes a row into the recipient's "
            "inbox and emits a push (APNs/FCM). Inbox is paginated by recency; high-volume creators "
            "get per-post aggregation ('123 people liked your photo')."
        ),
        "dm": (
            "1:1 + group messaging defers to the dedicated chat design — WebSocket gateway, Cassandra "
            "thread/messages tables, presence service. Mentioned here only because the bell icon and "
            "DM unread counts share a fan-out shape."
        ),
    },
    trade_offs=[
        {"option": "Pull vs push vs hybrid feed",
         "for_pull": "Cheap on write; trivial for celebrities; no stale fan-out",
         "for_push": "Cheap on read; pre-ranked; great p99 feed open",
         "recommendation": "Hybrid — push for the long tail, pull for celebrities. Best p99 without write apocalypse."},
        {"option": "Inline vs async transcoding",
         "for_inline": "Post is immediately viewable",
         "for_async": "Decouples upload from compute; survives spikes",
         "recommendation": "Async — show 'processing' state; tolerate seconds before public visibility."},
        {"option": "Follow graph in SQL vs graph DB",
         "for_sql": "Simple, sharded, well-understood; sufficient for 1-hop queries",
         "for_graph_db": "Multi-hop traversals (friends-of-friends) cheaper",
         "recommendation": "SQL sharded by follower_id — Instagram's hot queries are 1-hop. Reach for graph DB only for recommendation features."},
        {"option": "Per-user feed materialised vs computed",
         "for_materialised": "Sub-100ms reads; pre-ranked",
         "for_computed": "Always fresh; no staleness window",
         "recommendation": "Materialised with celeb pull-merge — staleness window is acceptable UX."},
    ],
    tips=[
        "Lead with hybrid fan-out and the celebrity threshold — the senior signal.",
        "Never fan-out a celebrity post. Spell out the math: 100M writes per post is unworkable.",
        "Media never touches the app servers — presigned S3 + async transcode + CDN.",
        "Stories are a separate hot store with TTL — don't conflate with posts.",
        "Search is Elasticsearch, not SQL LIKE. Autocomplete needs edge-ngram.",
        "Defer DM to the chat design and say so — interview honesty beats hand-waving.",
    ],
    thought_process=[
        "1. Clarify scope: feed (photo+reel), follow, search, stories, notifications. DM defers to chat design.",
        "2. Estimate: 500M DAU, 5B feed opens/day → ~60K QPS steady, 500K peak. Read-skewed.",
        "3. APIs: /media/upload (presigned), /posts, /feed, /follow, /search, /stories.",
        "4. Feed: hybrid fan-out — push for normal, pull for celebs. Threshold ~1M followers.",
        "5. Media: presigned upload, async transcode, CDN. Photo variants + reel ABR ladder.",
        "6. Follow graph: SQL sharded by follower_id; reverse index by followee_id for fan-out.",
        "7. Search: Elasticsearch with edge-ngram autocomplete + popularity ranking.",
        "8. Stories: TTL store, sweeper; CDN + lifecycle to cold after 24h.",
        "9. Notifications: per-user inbox + push; aggregate for high-volume creators.",
        "10. SLO: feed open p99 < 1s; reel first-frame < 500ms; eventual consistency on inclusion.",
    ],
    tags=["feed", "social", "photo", "video", "timeline", "fan-out", "search", "scale"],
    arch_nodes=[
        {"id": "client", "label": "Mobile / Web", "type": "client"},
        {"id": "lb", "label": "API Gateway", "type": "lb"},
        {"id": "upload", "label": "Upload Service", "type": "server"},
        {"id": "s3", "label": "S3 (Media)", "type": "database"},
        {"id": "trans", "label": "Transcoder", "type": "service"},
        {"id": "post", "label": "Post Service", "type": "server"},
        {"id": "fanout", "label": "Fan-out Worker", "type": "service"},
        {"id": "feed", "label": "Feed Service", "type": "server"},
        {"id": "userfeed", "label": "user_feed (Redis+C*)", "type": "cache"},
        {"id": "follow", "label": "Follow Service", "type": "server"},
        {"id": "graph", "label": "Follow DB", "type": "database"},
        {"id": "search", "label": "Elasticsearch", "type": "database"},
        {"id": "story", "label": "Story Service", "type": "server"},
        {"id": "notif", "label": "Notification Service", "type": "service"},
        {"id": "cdn", "label": "Media CDN", "type": "cache"},
        {"id": "kafka", "label": "Kafka", "type": "queue"},
    ],
    arch_edges=[
        {"source": "client", "target": "lb"},
        {"source": "lb", "target": "upload"},
        {"source": "upload", "target": "s3", "label": "presigned PUT"},
        {"source": "s3", "target": "trans", "label": "ObjectCreated"},
        {"source": "trans", "target": "s3", "label": "variants"},
        {"source": "trans", "target": "post", "label": "ready event"},
        {"source": "lb", "target": "post"},
        {"source": "post", "target": "kafka", "label": "post.created"},
        {"source": "kafka", "target": "fanout"},
        {"source": "fanout", "target": "userfeed", "label": "push (non-celeb)"},
        {"source": "lb", "target": "feed"},
        {"source": "feed", "target": "userfeed", "label": "read"},
        {"source": "feed", "target": "post", "label": "celeb pull"},
        {"source": "feed", "target": "cdn", "label": "media URLs"},
        {"source": "lb", "target": "follow"},
        {"source": "follow", "target": "graph"},
        {"source": "fanout", "target": "graph", "label": "list followers"},
        {"source": "lb", "target": "search"},
        {"source": "post", "target": "search", "label": "index hashtags"},
        {"source": "lb", "target": "story"},
        {"source": "kafka", "target": "notif"},
        {"source": "client", "target": "cdn", "label": "media GET"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant U as User\n"
        "  participant API\n"
        "  participant S3\n"
        "  participant T as Transcoder\n"
        "  participant P as Post\n"
        "  participant F as Fan-out\n"
        "  participant UF as user_feed\n"
        "  participant V as Viewer\n"
        "  U->>API: POST /media/upload\n"
        "  API-->>U: presigned URL\n"
        "  U->>S3: PUT bytes\n"
        "  S3->>T: ObjectCreated\n"
        "  T->>S3: write variants\n"
        "  T->>P: ready event\n"
        "  U->>API: POST /posts\n"
        "  API->>P: persist\n"
        "  P->>F: post.created\n"
        "  F->>UF: push to non-celeb followers\n"
        "  V->>API: GET /feed\n"
        "  API->>UF: read pushed feed\n"
        "  API->>P: pull celeb posts\n"
        "  API-->>V: ranked merge"
    ),
    er_diagram=(
        "erDiagram\n"
        "  USER ||--o{ POST : authors\n"
        "  USER ||--o{ FOLLOW : follows\n"
        "  USER ||--o{ STORY : posts\n"
        "  POST ||--o{ LIKE : has\n"
        "  POST ||--o{ COMMENT : has\n"
        "  USER ||--o{ NOTIFICATION : receives\n"
        "  POST { bigint id PK\n string kind\n string media_id\n text caption\n bigint created_at }\n"
        "  FOLLOW { bigint follower_id\n bigint followee_id }\n"
        "  STORY { bigint id PK\n bigint user_id\n bigint expires_at }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B[Read-skewed, billions of users]\n"
        "  B --> C{Feed strategy?}\n"
        "  C -->|Push| D[Cheap reads, write apocalypse for celebs]\n"
        "  C -->|Pull| E[Cheap writes, slow reads]\n"
        "  C -->|Hybrid| F[Push normal + pull celebs]\n"
        "  F --> G[Media: presigned + async transcode]\n"
        "  G --> H[Search: Elasticsearch autocomplete]\n"
        "  H --> I[Stories: TTL store]\n"
        "  I --> J[Notifications: per-user inbox]"
    ),
    tradeoff_title="Push vs Pull vs Hybrid feed generation",
    tradeoff_options=[
        {"label": "Push (fan-out on write)",
         "description": "Materialise post into every follower's feed at write time.",
         "pros": ["Sub-100ms feed reads", "Pre-rankable", "Simple read path"],
         "cons": ["Catastrophic for celebrities (100M writes per post)", "Wasted writes for inactive followers"]},
        {"label": "Pull (compute on read)",
         "description": "On feed open, query recent posts from each followee and merge.",
         "pros": ["Cheap writes", "Always fresh", "No celeb fan-out"],
         "cons": ["Slow p99 reads", "Re-ranks on every open", "Hot followee partitions get hammered"]},
        {"label": "Hybrid",
         "description": "Push for normal users; pull-merge for celebrities at read time.",
         "pros": ["Bounded write cost", "Sub-second reads", "Scales to power-law graph"],
         "cons": ["Two code paths to maintain", "Celeb threshold tuning"]},
    ],
    tradeoff_rec="Hybrid — push for the long tail, pull for the ~1M-follower-plus celebrities. Industry-validated pattern.",
    senior_topics=[
        _topic("hybrid-fanout",
               "Hybrid Fan-out: Why Pure Push Breaks at Celebrity Scale",
               "A power-law follow graph means a tiny number of accounts have astronomical follower "
               "counts. Pure push fan-out turns one of their posts into 100M+ writes — unworkable. "
               "The hybrid model side-steps this by pulling at read time only for that thin tail.",
               [
                   ("The fan-out math",
                    "Average user has ~400 followers — push is fine. A celebrity with 100M followers "
                    "produces 100M user_feed writes per post. At 10 posts/day from the top 1000 "
                    "creators that's ~1T writes/day on its own — bigger than the entire main workload."),
                   ("Celebrity threshold",
                    "Mark users with follower_count > ~1M as is_celebrity=true. Their posts skip "
                    "fan-out entirely. The Feed Service does a read-time merge of pushed feed + "
                    "recent posts from celebs the user follows."),
                   ("Read-time merge cost",
                    "An average user follows tens of celebs at most. That's a bounded fan-in lookup, "
                    "well within feed-open latency budget if celeb timelines are cached."),
                   ("Edge cases",
                    "User crosses the celeb threshold mid-life: stop fanning out new posts; let old "
                    "pushed entries age out naturally. Going below threshold: resume fan-out but don't "
                    "back-fill — would re-do too much work."),
                   ("Why not just pull always",
                    "Median user follows 400 accounts. Pure pull means 400 timeline scans per feed "
                    "open at 60K QPS — the read amplification kills the database."),
               ],
               diagram=(
                   "graph TD\n"
                   "  P[New post] --> Q{Author celeb?}\n"
                   "  Q -->|No| F[Fan-out worker]\n"
                   "  F --> UF[user_feed of each follower]\n"
                   "  Q -->|Yes| C[Celeb timeline]\n"
                   "  R[Feed open] --> M[Merge]\n"
                   "  M --> UF\n"
                   "  M --> C"
               )),
        _topic("media-pipeline",
               "Photo + Reel Transcoding Pipeline",
               "Media never touches app servers. Presigned uploads + event-driven async transcoding "
               "produce the variants needed for responsive web, mobile, and ABR streaming.",
               [
                   ("Presigned upload",
                    "App returns a short-lived S3 PUT URL. Client uploads bytes directly. App load "
                    "is constant regardless of file size; no proxying through compute."),
                   ("Photo variants",
                    "Original → 320/640/1080/1440 webp + 200px thumbnail. Client requests the "
                    "appropriate size based on viewport. ~5× CDN bandwidth reduction vs always-full."),
                   ("Reel ABR ladder",
                    "240p/480p/720p/1080p HLS or DASH segments. Client starts at lowest rendition "
                    "for sub-500ms first-frame, ramps up as bandwidth permits. Vertical 9:16 only."),
                   ("Transcode orchestration",
                    "S3 ObjectCreated → SQS → fleet of GPU/CPU workers. Failure isolated per job; "
                    "retry with backoff. Post visibility gated on transcode-ready event."),
                   ("Cost optimisation",
                    "Reels not viewed in first 7 days drop from CDN edge. Old originals move to "
                    "Glacier-tier; only variants stay warm. ~80% storage cost reduction long-tail."),
               ]),
        _topic("follow-graph-sharding",
               "Sharding the Follow Graph for Bidirectional Reads",
               "Two access patterns: list a user's followees (feed open) and list a user's followers "
               "(fan-out). They want different shard keys, so we maintain two indexes.",
               [
                   ("Forward index",
                    "follows sharded by follower_id. Listing my followees on feed open is a single-"
                    "shard query. Hot in cache for active users."),
                   ("Reverse index",
                    "follower_of sharded by followee_id. The fan-out worker queries this when a "
                    "non-celeb user posts. Two writes per follow (one each index) — cost worth paying."),
                   ("Why not a graph DB",
                    "Instagram's hot queries are 1-hop. SQL sharding handles billions of edges with "
                    "predictable latency. Graph DBs shine on multi-hop (friend-of-friend) — keep "
                    "those for recommendation/discovery, not the hot path."),
                   ("Skew handling",
                    "Celebrities have huge follower lists. We never enumerate them at write time "
                    "(they're celeb-pulled at read), so the skew never hits a hot fan-out worker."),
               ]),
        _topic("hashtag-search",
               "Hashtag Indexing and Autocomplete Search",
               "Search is Elasticsearch — not SQL LIKE, not Redis. Autocomplete + ranked relevance "
               "+ hashtag pages are all the same engine.",
               [
                   ("Indexing on post create",
                    "Post Service extracts hashtags from caption; bulk-indexes (hashtag, post_id, "
                    "engagement, ts) into ES. Updates on like/comment via near-real-time pipeline."),
                   ("Autocomplete",
                    "edge-ngram analyzer on user.handle and user.name. Query 'kyl' matches 'kylie', "
                    "'kyle', etc. Ranking blends follower_count + personal affinity (do I follow them?)."),
                   ("Hashtag pages",
                    "GET /tag/{tag} = ES query sorted by recency × engagement. Top-of-page = "
                    "most-recent + viral; scroll = recency."),
                   ("Trending",
                    "Streaming aggregation (Flink) over the last 1h post stream. Counts per hashtag "
                    "with z-score against the prior 24h baseline. Top-K maintained in Redis sorted set."),
                   ("Why not SQL",
                    "LIKE 'prefix%' on a billion rows + relevance ranking is infeasible. ES inverted "
                    "index + scoring is built for this exact shape."),
               ]),
        _topic("stories-ttl",
               "Stories with 24h TTL — Why a Separate Store",
               "Stories have fundamentally different lifecycle than posts: ephemeral, view-tracked, "
               "media archived after expiry. Conflating them with posts makes both worse.",
               [
                   ("Schema",
                    "stories(id, user_id, media_id, expires_at). Index on expires_at for the sweeper. "
                    "Per-user 'my friends' stories list is a Redis sorted set keyed by ts."),
                   ("Sweeper",
                    "Background job deletes rows where expires_at < now. Media in S3 has a lifecycle "
                    "rule for cold-tier transition (kept for archive but not CDN-cached)."),
                   ("View tracking",
                    "Per (story, viewer) row written on first view; expires alongside the story. "
                    "Powers the 'who saw this' UX."),
                   ("Why separate from posts",
                    "Putting expires_at on posts table forces every read to filter; index bloat for "
                    "a feature 5% of posts use. Separation isolates the hot, ephemeral read pattern."),
               ]),
    ],
)
