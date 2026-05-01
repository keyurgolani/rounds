"""News Feed (Facebook-style) system design question. Loaded automatically
via `sd_questions._load_more` because this module exposes `PAYLOAD`."""
from __future__ import annotations

from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design News Feed (Facebook-style)",
    "Hard",
    "Design a Facebook-style News Feed: a personalised, ranked stream of posts, photos, videos, and "
    "shares from a user's friends, followed pages, and groups. The feed must rank by relevance "
    "(time decay x engagement x affinity), update in near real-time as friends post, paginate "
    "smoothly under heavy insert load, and gracefully handle the power-law of social graphs where "
    "celebrity creators dwarf normal users. Focus on the feed-generation hot path, ranking pipeline, "
    "and the hybrid push/pull strategy that keeps both writes and reads tractable at billions-of-users "
    "scale.",
    hints=[
        "Feed generation is the central decision: pull (compute on read), push (fan-out on write), or hybrid.",
        "Hybrid is the only answer at this scale: push for normal users, pull for celebrities a viewer follows.",
        "Ranking is not just recency — it is time-decay x engagement velocity x viewer-author affinity (ML model).",
        "Activity timeline (raw chronological) and ranked feed are different products with different stores.",
        "Per-user feed cache lives in Redis sorted sets keyed by score; durable copy in Cassandra/sharded SQL.",
        "Posts DB sharded by author user_id; feed-cache sharded by viewer user_id — two different shard keys.",
        "Async pipeline: post.created -> Kafka -> fan-out workers -> per-follower feed cache updates.",
        "Cursor-based pagination beats offset — handles new inserts during scroll without dupes/skips.",
        "Real-time pushes via WebSocket or long-poll; cold-start users get a recommended seed feed.",
    ],
    constraints=[
        "3B+ monthly users, ~2B DAU",
        "~5B feed opens per day; 10B+ scroll page-fetches",
        "Power-law graph: top creators have 100M+ followers; median user has ~300 friends",
        "Feed open p99 < 800ms; pagination p99 < 300ms",
        "Eventual consistency on feed inclusion (seconds-of-staleness acceptable)",
        "Global multi-region; writes regional, reads edge-cached where possible",
        "Mixed media — text, images, videos, shares, link previews",
    ],
    req_func=[
        "Create a post (text + optional media) and publish to friends/followers",
        "Render personalised, ranked home feed on open",
        "Paginate the feed without duplicates or gaps as new posts arrive",
        "React, comment, share — feeding back into ranking signals",
        "Real-time top-of-feed updates when a friend posts (push to active sessions)",
        "Activity timeline view (chronological, unranked) for a single profile",
        "Cold start for new users: recommended seed posts from popular pages and friend suggestions",
    ],
    req_nonfunc=[
        "Feed open p99 < 800ms; subsequent page p99 < 300ms",
        "99.95% availability for read paths",
        "Read-heavy: ~100x more reads than writes — caching is the primary scale lever",
        "Eventual consistency: a new post may take seconds to surface in followers' feeds",
        "Durable post storage — zero post loss",
        "Bandwidth-efficient: media via CDN, paginated payloads, delta updates on long-lived sessions",
        "Personalised: ranking model must run within the feed-open budget",
    ],
    estimation={
        "dau": "2B",
        "feed_opens_per_day": "~5B",
        "page_fetches_per_day": "~10B (multiple scrolls per open)",
        "posts_per_day": "~500M (text + media)",
        "qps_feed_read": "~120K/sec global steady; ~1M/sec peak",
        "qps_post_create": "~6K/sec steady",
        "fanout_writes_per_sec": "~6K posts/sec * 300 avg followers ~= 1.8M writes/sec into feed caches",
        "feed_cache_size": "~1KB metadata x ~500 entries x 2B users ~= 1PB hot tier (sharded Redis)",
        "post_storage": "~500M posts/day x 2KB metadata + media in object store ~= 1TB/day metadata",
    },
    endpoints=[
        {"method": "POST", "path": "/posts",
         "description": "Create a post; returns post_id; fan-out triggered async",
         "body": "{kind: text|photo|video|share, body, media_ids:[], audience: friends|public|custom}"},
        {"method": "GET", "path": "/feed",
         "description": "Ranked home feed for the authenticated user; cursor pagination",
         "body": "?cursor=opaque&limit=20"},
        {"method": "GET", "path": "/timeline/{user_id}",
         "description": "Chronological activity timeline for a profile (no ranking)",
         "body": "?cursor=opaque&limit=20"},
        {"method": "POST", "path": "/posts/{post_id}/react",
         "description": "Add/change reaction; emits engagement event for ranking",
         "body": "{kind: like|love|haha|wow|sad|angry}"},
        {"method": "POST", "path": "/posts/{post_id}/comments",
         "description": "Add a comment; engagement signal feeds ranker",
         "body": "{body}"},
        {"method": "POST", "path": "/posts/{post_id}/share",
         "description": "Share a post into your own feed",
         "body": "{commentary?}"},
        {"method": "GET", "path": "/feed/realtime",
         "description": "WebSocket / long-poll endpoint for top-of-feed pushes"},
        {"method": "GET", "path": "/feed/coldstart",
         "description": "Recommended seed posts for a new user with no graph signal"},
    ],
    tables=[
        {"name": "users",
         "columns": ["id BIGINT PK", "handle VARCHAR(32) UNIQUE", "name VARCHAR",
                     "follower_count BIGINT", "is_celebrity BOOL", "created_at BIGINT",
                     "last_active_at BIGINT"]},
        {"name": "posts",
         "columns": ["id BIGINT PK", "author_id BIGINT", "kind VARCHAR(8)",
                     "body TEXT", "media_ids JSONB", "audience VARCHAR(16)",
                     "created_at BIGINT", "engagement_score FLOAT",
                     "like_count INT", "comment_count INT", "share_count INT"]},
        {"name": "follows",
         "columns": ["follower_id BIGINT", "followee_id BIGINT", "affinity FLOAT",
                     "created_at BIGINT", "PRIMARY KEY (follower_id, followee_id)"]},
        {"name": "user_feed",
         "columns": ["viewer_id BIGINT", "post_id BIGINT", "score FLOAT",
                     "inserted_at BIGINT", "PRIMARY KEY (viewer_id, score, post_id)"]},
        {"name": "reactions",
         "columns": ["post_id BIGINT", "user_id BIGINT", "kind VARCHAR(8)",
                     "created_at BIGINT", "PRIMARY KEY (post_id, user_id)"]},
        {"name": "comments",
         "columns": ["id BIGINT PK", "post_id BIGINT", "user_id BIGINT",
                     "body TEXT", "created_at BIGINT"]},
        {"name": "celeb_timeline",
         "columns": ["author_id BIGINT", "post_id BIGINT", "created_at BIGINT",
                     "PRIMARY KEY (author_id, created_at, post_id)"]},
    ],
    indexes=[
        "(follower_id) on follows — list followees on feed open",
        "(followee_id) on follows — reverse index for fan-out worker",
        "(author_id, created_at DESC) on posts — pull-mode timeline scan",
        "(viewer_id, score DESC) on user_feed — ranked feed read",
        "(viewer_id, inserted_at DESC) on user_feed — chronological fallback",
        "(author_id, created_at DESC) on celeb_timeline — read-time merge",
        "(post_id) on reactions/comments — engagement aggregation",
    ],
    hld_desc=(
        "Hybrid feed-generation pipeline. Most posts are pushed (fan-out on write) into per-follower "
        "user_feed entries — kept in Redis sorted sets (hot tier) backed by Cassandra (durable). "
        "Celebrity posts skip fan-out and live in a celeb_timeline; the Feed Service merges pushed "
        "feed + recent celeb posts at read time, runs the ranker, and returns a paginated cursor. "
        "Posts are produced via Post Service, persisted to a sharded Posts DB (sharded by author_id), "
        "and emit a post.created event onto Kafka. Fan-out Workers consume Kafka, enumerate non-celeb "
        "follower lists, and write into user_feed shards. Engagement events (reactions, comments, "
        "shares) flow through Kafka into the Ranking Service, which updates per-post engagement "
        "scores and per-edge affinity. A WebSocket gateway pushes top-of-feed deltas to active "
        "sessions. Cold-start users hit a Recommendation Service that returns a seeded feed of "
        "popular content."
    ),
    hld_components=[
        {"name": "Mobile / Web Clients", "role": "Render feed, scroll, react, post"},
        {"name": "API Gateway", "role": "Auth, rate-limit, region-route"},
        {"name": "Post Service", "role": "Persist posts; emit post.created event"},
        {"name": "Posts DB", "role": "Sharded by author_id; canonical post storage"},
        {"name": "Kafka", "role": "post.created + engagement event bus"},
        {"name": "Fan-out Worker", "role": "Push post into followers' user_feed (skip celebrities)"},
        {"name": "Feed Service", "role": "Read pushed feed + merge celeb posts; rank; paginate"},
        {"name": "user_feed Cache (Redis sorted sets + Cassandra)",
         "role": "Per-viewer feed materialisation, sharded by viewer_id"},
        {"name": "celeb_timeline", "role": "Per-celebrity recent posts for read-time merge"},
        {"name": "Ranking Service", "role": "Score posts: time decay x engagement x affinity (ML model)"},
        {"name": "Affinity Store", "role": "Per (viewer, author) interaction history feature store"},
        {"name": "Engagement Aggregator", "role": "Stream-process reactions/comments to update post scores"},
        {"name": "Real-time Gateway", "role": "WebSocket / long-poll fan-out of top-of-feed deltas"},
        {"name": "Recommendation Service", "role": "Cold-start seed feed for new users"},
        {"name": "Media CDN + Object Store", "role": "Photos and videos served at the edge"},
    ],
    detailed_design={
        "feed_generation_hybrid": (
            "Push (fan-out on write) for the long tail: when a non-celebrity user posts, the Fan-out "
            "Worker enumerates followers and inserts (post_id, score, inserted_at) into each follower's "
            "user_feed. Pull (compute on read) for celebrities: posts by users with is_celebrity=true "
            "or follower_count > ~1M skip fan-out. On feed open the Feed Service does: "
            "(1) read top-N pushed entries from user_feed for the viewer; "
            "(2) read recent posts from celeb_timeline for each celeb the viewer follows (bounded — "
            "users follow tens of celebs at most); "
            "(3) merge candidate set; "
            "(4) run ranker; "
            "(5) return ranked page + cursor. The hybrid avoids the celeb write apocalypse (100M "
            "writes per post) and the average-user pull blow-up (300 timeline scans per open)."
        ),
        "ranking_pipeline": (
            "Ranking score = f(time_decay, engagement_velocity, viewer_author_affinity, "
            "content_type_preference, predicted_dwell). "
            "Time decay: exp(-age_hours / half_life), half_life ~= 6h for friends, 2h for celebs. "
            "Engagement velocity: likes_per_min and comments_per_min in the last hour, normalised. "
            "Affinity: per-edge feature stored from past interactions (DMs, profile views, prior "
            "reactions). High affinity boosts a friend's post even if engagement is modest. "
            "Content-type preference: per-viewer learnt preference for video vs photo vs text. "
            "An ML model (gradient-boosted trees + small DNN) scores the merged candidate set "
            "(~few hundred items) within ~50ms. Heavier offline ranking refreshes pushed-feed "
            "scores in the background."
        ),
        "storage_layers": (
            "Posts DB sharded by author_id — keeps an author's posts colocated for timeline scans. "
            "user_feed sharded by viewer_id — keeps a viewer's feed colocated for feed open. "
            "Hot tier per viewer in Redis (sorted set keyed by score): top ~500 entries with TTL. "
            "Durable tier in Cassandra with the same schema for cache rebuild + cold-tier reads. "
            "celeb_timeline kept as a separate Cassandra table sharded by author_id with descending "
            "created_at clustering — read-time merge pulls the last K minutes from each celeb the "
            "viewer follows."
        ),
        "activity_timeline_vs_feed": (
            "Two distinct products: "
            "Activity timeline (chronological) is just GET posts WHERE author_id = X ORDER BY "
            "created_at DESC — served straight off the Posts DB or a per-author Cassandra timeline. "
            "Ranked feed is the user_feed cache + celeb merge + ML ranker described above. "
            "Conflating them forces every timeline read to pay ranking cost or every feed read to "
            "skip personalisation. Keeping them separate lets each store be optimised independently."
        ),
        "celebrity_threshold": (
            "Mark users with follower_count > ~1M as is_celebrity=true; their posts skip the fan-out "
            "path. Threshold tuning: too low and the read-time merge cost grows; too high and the "
            "fan-out worker drowns. Boundary cases: a user crosses threshold mid-life — stop fanning "
            "out new posts, let old pushed entries age out naturally; a user drops below threshold — "
            "resume fan-out for new posts but do NOT back-fill pushed copies for their historical "
            "content (the read-time merge handles that gap until aged out)."
        ),
        "inactive_user_problem": (
            "Pure push wastes storage on inactive followers — a celeb's post fans out to 100M caches "
            "but ~70% of those users won't open the app today. Mitigations: "
            "(1) skip fan-out for users with last_active_at older than ~30d — they pull from celeb "
            "timeline on next return; "
            "(2) age-out user_feed entries aggressively (TTL 7d) so dormant caches don't bloat Redis; "
            "(3) priority queue fan-out — active followers first, dormant ones lazily."
        ),
        "async_via_kafka": (
            "Post Service writes the post row, then emits post.created onto Kafka with "
            "{post_id, author_id, audience, created_at}. Fan-out Worker consumers partitioned by "
            "author_id consume the topic, look up the author's followers (skipping fan-out for "
            "celebrities), and bulk-write user_feed entries via batched Cassandra writes + Redis "
            "ZADD. Idempotent on (viewer_id, post_id) so retries are safe. Engagement events "
            "(post.reacted, post.commented) flow on a separate topic into the Engagement Aggregator "
            "and Affinity Store."
        ),
        "pagination_cursor": (
            "Cursor-based, not offset. Cursor encodes (last_score, last_post_id) opaquely. "
            "Server query: WHERE (score, post_id) < (last_score, last_post_id) ORDER BY score DESC "
            "LIMIT N. This is stable under insertions: new posts pushed into the feed during scroll "
            "appear at the top on next refresh, never as duplicates or skips on subsequent pages. "
            "Offset-based would shift pages every time a new entry was inserted — a notorious "
            "duplicate/skip bug at this scale."
        ),
        "real_time_updates": (
            "Active sessions hold a WebSocket to the Real-time Gateway. When the Fan-out Worker "
            "writes into a viewer's user_feed AND that viewer is online, it emits a feed.delta "
            "message with the new top-of-feed post_id; the client renders a 'New posts' banner or "
            "auto-prepends. Long-poll fallback for clients that can't hold a WebSocket. Push "
            "delivery is best-effort; clients always reconcile against /feed on next open."
        ),
        "cold_start": (
            "New user has no follow graph and no engagement history — the personalised path returns "
            "an empty merged set. Recommendation Service supplies a seeded feed: globally popular "
            "posts of the last 24h, posts from suggested-friends and pages the onboarding flow "
            "captured (interests, location, contacts uploaded), and viral content trending in the "
            "user's region. As the user follows accounts and engages, the personalised feed phases "
            "in — typically within hours of activity."
        ),
        "slo_contract": (
            "Feed open p99 < 800ms; subsequent page p99 < 300ms. Inclusion freshness: 95% of new "
            "posts appear in active followers' feeds within 5 seconds, 99% within 30 seconds. "
            "Real-time push delivery: best-effort 90% within 60 seconds, no guaranteed delivery — "
            "clients reconcile on reopen."
        ),
    },
    trade_offs=[
        {"option": "Pull vs push vs hybrid feed",
         "for_pull": "Cheap on write; trivial for celebrities; always fresh",
         "for_push": "Sub-second feed open; pre-rankable; great p99",
         "recommendation": "Hybrid — push for the long tail, pull-merge for celebrities. "
                            "Industry-validated at Facebook, Twitter, Instagram scale."},
        {"option": "Ranked feed vs chronological",
         "for_chronological": "Predictable, no surprise ordering, simple infra",
         "for_ranked": "Dramatically higher engagement and time-on-app — the business case",
         "recommendation": "Ranked is non-negotiable at Facebook scale; expose chronological as "
                            "an opt-in 'Most Recent' toggle."},
        {"option": "Offset vs cursor pagination",
         "for_offset": "Simple, easy to jump to page N",
         "for_cursor": "Stable under insertions, no dupes/skips, cheap to compute",
         "recommendation": "Cursor — feeds are insert-heavy and offset paging produces "
                            "user-visible bugs."},
        {"option": "Materialised user_feed vs computed-on-read",
         "for_materialised": "Sub-100ms reads; pre-ranked; smooth scrolling",
         "for_computed": "No staleness window; no pre-fan-out cost",
         "recommendation": "Materialised with celeb-pull-merge — the staleness window is acceptable "
                            "UX and read latency is the conversion driver."},
        {"option": "Inline vs async fan-out",
         "for_inline": "Post is immediately in followers' feeds",
         "for_async": "Decouples post-create from compute; survives spikes; idempotent retries",
         "recommendation": "Async via Kafka — post-create p99 stays bounded; fan-out can spike "
                            "without affecting the write path."},
    ],
    tips=[
        "Lead with hybrid fan-out and the celebrity threshold — the senior signal.",
        "Spell out the math: 100M followers x 1 post = 100M writes. Push-everything does not work.",
        "Distinguish ranked feed from activity timeline — different stores, different products.",
        "Ranking is time decay x engagement x affinity, scored by a model — not just 'recent first'.",
        "Cursor-based pagination — interviewers probe this; offset is wrong at feed scale.",
        "Real-time updates are best-effort over WebSocket; clients reconcile on /feed open.",
        "Cold start is a separate code path with a Recommendation Service — say so explicitly.",
        "Posts DB sharded by author_id; user_feed sharded by viewer_id — call out the split.",
    ],
    thought_process=[
        "1. Clarify scope: ranked home feed, post creation, real-time updates, pagination, cold start.",
        "2. Estimate: 2B DAU, 5B feed opens/day, 6K posts/sec -> ~120K read QPS, ~1.8M fan-out "
        "writes/sec at average 300 followers per user.",
        "3. APIs: POST /posts, GET /feed (cursor), GET /timeline (chrono), reactions, comments, "
        "WebSocket /feed/realtime, GET /feed/coldstart.",
        "4. Feed strategy: hybrid — push for normal users (sub-second reads), pull-merge for "
        "celebrities (avoid 100M-write fan-out per post). Threshold ~1M followers.",
        "5. Storage: Posts DB sharded by author_id; user_feed Redis sorted sets + Cassandra "
        "sharded by viewer_id; celeb_timeline as separate Cassandra table.",
        "6. Ranking: time decay x engagement velocity x viewer-author affinity x content-type "
        "preference, scored by ML model on the merged candidate set within ~50ms.",
        "7. Async pipeline: post.created -> Kafka -> Fan-out Worker -> per-follower user_feed "
        "writes; engagement events on a separate topic feed the ranker.",
        "8. Pagination: cursor on (score, post_id) — stable under insertions.",
        "9. Real-time: WebSocket gateway pushes feed.delta to active sessions; long-poll fallback.",
        "10. Cold start: Recommendation Service returns popular + region-trending + suggested-friend "
        "posts until graph signal accumulates.",
        "11. SLOs: feed open p99 < 800ms; inclusion freshness 95% within 5s; ranking budget ~50ms.",
    ],
    tags=["feed", "social", "ranking", "fan-out", "scale"],
    arch_nodes=[
        {"id": "client", "label": "Mobile / Web", "type": "client"},
        {"id": "lb", "label": "API Gateway", "type": "lb"},
        {"id": "post", "label": "Post Service", "type": "server"},
        {"id": "postdb", "label": "Posts DB (shard by author)", "type": "database"},
        {"id": "kafka", "label": "Kafka", "type": "queue"},
        {"id": "fanout", "label": "Fan-out Worker", "type": "service"},
        {"id": "userfeed", "label": "user_feed (Redis+C*)", "type": "cache"},
        {"id": "celeb", "label": "celeb_timeline", "type": "database"},
        {"id": "feed", "label": "Feed Service", "type": "server"},
        {"id": "rank", "label": "Ranking Service", "type": "service"},
        {"id": "affinity", "label": "Affinity Store", "type": "database"},
        {"id": "engage", "label": "Engagement Aggregator", "type": "service"},
        {"id": "rt", "label": "Real-time Gateway (WS)", "type": "service"},
        {"id": "rec", "label": "Recommendation Service", "type": "service"},
        {"id": "cdn", "label": "Media CDN", "type": "cache"},
        {"id": "follow", "label": "Follow Service", "type": "server"},
        {"id": "graph", "label": "Follow DB", "type": "database"},
    ],
    arch_edges=[
        {"source": "client", "target": "lb"},
        {"source": "lb", "target": "post"},
        {"source": "post", "target": "postdb", "label": "persist"},
        {"source": "post", "target": "kafka", "label": "post.created"},
        {"source": "kafka", "target": "fanout"},
        {"source": "fanout", "target": "graph", "label": "list followers"},
        {"source": "fanout", "target": "userfeed", "label": "push (non-celeb)"},
        {"source": "post", "target": "celeb", "label": "celeb path"},
        {"source": "lb", "target": "feed"},
        {"source": "feed", "target": "userfeed", "label": "read pushed"},
        {"source": "feed", "target": "celeb", "label": "celeb pull-merge"},
        {"source": "feed", "target": "rank", "label": "score candidates"},
        {"source": "rank", "target": "affinity", "label": "features"},
        {"source": "kafka", "target": "engage", "label": "engagement events"},
        {"source": "engage", "target": "postdb", "label": "update scores"},
        {"source": "engage", "target": "affinity", "label": "update edges"},
        {"source": "fanout", "target": "rt", "label": "feed.delta"},
        {"source": "rt", "target": "client", "label": "WebSocket push"},
        {"source": "lb", "target": "rec", "label": "cold start"},
        {"source": "lb", "target": "follow"},
        {"source": "follow", "target": "graph"},
        {"source": "client", "target": "cdn", "label": "media GET"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant U as User\n"
        "  participant API\n"
        "  participant P as Post Svc\n"
        "  participant K as Kafka\n"
        "  participant F as Fan-out\n"
        "  participant UF as user_feed\n"
        "  participant V as Viewer\n"
        "  participant FS as Feed Svc\n"
        "  participant CT as celeb_timeline\n"
        "  participant R as Ranker\n"
        "  participant RT as Real-time GW\n"
        "  U->>API: POST /posts\n"
        "  API->>P: persist\n"
        "  P->>K: post.created\n"
        "  K->>F: consume\n"
        "  F->>F: author celeb? skip : fan-out\n"
        "  F->>UF: ZADD per follower\n"
        "  F->>RT: feed.delta\n"
        "  RT-->>V: WS push\n"
        "  V->>API: GET /feed?cursor=...\n"
        "  API->>FS: feed open\n"
        "  FS->>UF: read pushed top-N\n"
        "  FS->>CT: pull recent celeb posts\n"
        "  FS->>R: rank merged set\n"
        "  R-->>FS: scored list\n"
        "  FS-->>V: page + next_cursor"
    ),
    er_diagram=(
        "erDiagram\n"
        "  USER ||--o{ POST : authors\n"
        "  USER ||--o{ FOLLOW : follows\n"
        "  USER ||--o{ USER_FEED : sees\n"
        "  POST ||--o{ REACTION : has\n"
        "  POST ||--o{ COMMENT : has\n"
        "  POST { bigint id PK\n bigint author_id\n string kind\n text body\n bigint created_at\n float engagement_score }\n"
        "  FOLLOW { bigint follower_id\n bigint followee_id\n float affinity }\n"
        "  USER_FEED { bigint viewer_id\n bigint post_id\n float score\n bigint inserted_at }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B[Read-skewed, billions of users]\n"
        "  B --> C{Feed strategy?}\n"
        "  C -->|Pull| D[Cheap writes, slow reads]\n"
        "  C -->|Push| E[Cheap reads, celeb write apocalypse]\n"
        "  C -->|Hybrid| F[Push normal + pull celebs]\n"
        "  F --> G[Ranking: time x engagement x affinity]\n"
        "  G --> H[Async via Kafka fan-out]\n"
        "  H --> I[Cursor pagination]\n"
        "  I --> J[Real-time via WebSocket]\n"
        "  J --> K[Cold start via recommender]"
    ),
    tradeoff_title="Push vs Pull vs Hybrid feed generation",
    tradeoff_options=[
        {"label": "Push (fan-out on write)",
         "description": "Materialise the post into every follower's feed at write time.",
         "pros": ["Sub-100ms feed reads", "Pre-rankable feed", "Simple read path",
                  "Predictable read latency"],
         "cons": ["Catastrophic for celebrities (100M+ writes per post)",
                  "Wasted writes for inactive followers",
                  "Hot fan-out workers on viral posts"]},
        {"label": "Pull (compute on read)",
         "description": "On feed open, query each followee's recent posts and merge in the ranker.",
         "pros": ["Cheap writes — single insert",
                  "Always fresh, no staleness window",
                  "No celeb fan-out problem"],
         "cons": ["Slow p99 reads — 300+ timeline scans per open at average follow count",
                  "Hot followee partitions get hammered",
                  "Re-ranks the same set on every open"]},
        {"label": "Hybrid",
         "description": "Push for normal users; pull-merge celebrity posts at read time.",
         "pros": ["Bounded write cost — celeb posts skip fan-out",
                  "Sub-second reads for the hot path",
                  "Scales gracefully under power-law follow graph",
                  "Independent tuning of push and pull paths"],
         "cons": ["Two code paths to maintain and reason about",
                  "Celebrity threshold is a tuning knob",
                  "Cross-region replication complexity for both stores"]},
    ],
    tradeoff_rec="Hybrid — push for the long tail, pull-merge for ~1M+ follower celebrities. "
                  "Industry-validated at Facebook, Twitter, and Instagram scale.",
    senior_topics=[
        _topic("hybrid-fanout",
               "Hybrid Fan-out: Why Pure Push Breaks at Celebrity Scale",
               "A power-law follow graph means a tiny number of accounts have astronomical "
               "follower counts. Pure push fan-out turns one of their posts into 100M+ writes — "
               "unworkable. The hybrid model side-steps this by pulling only for that thin tail.",
               [
                   ("The fan-out math",
                    "Average user has ~300 followers — push is fine, ~300 writes per post. "
                    "A celebrity with 100M followers produces 100M user_feed writes per post. "
                    "At 10 posts/day from the top 1000 creators that is ~1T writes/day on its "
                    "own — bigger than the entire main workload."),
                   ("Celebrity threshold",
                    "Mark users with follower_count > ~1M as is_celebrity=true. Their posts skip "
                    "fan-out entirely. The Feed Service does a read-time merge of pushed feed + "
                    "recent posts from celebs the viewer follows."),
                   ("Read-time merge cost",
                    "An average viewer follows tens of celebs at most. That is a bounded fan-in "
                    "lookup over celeb_timeline (recent K minutes per celeb), well within the "
                    "feed-open latency budget if celeb timelines are cached in Redis."),
                   ("Boundary cases",
                    "User crosses celeb threshold mid-life: stop fanning out new posts; let old "
                    "pushed entries age out via TTL. Drops below threshold: resume fan-out for new "
                    "posts but do NOT back-fill historical pushed copies — would re-do too much work."),
                   ("Why not just pull always",
                    "Median user follows ~300 accounts. Pure pull means 300 timeline scans per "
                    "feed open at 120K QPS — the read amplification annihilates the database."),
               ],
               diagram=(
                   "graph TD\n"
                   "  P[New post] --> Q{Author celeb?}\n"
                   "  Q -->|No| F[Fan-out worker]\n"
                   "  F --> UF[user_feed of each follower]\n"
                   "  Q -->|Yes| C[celeb_timeline]\n"
                   "  R[Feed open] --> M[Merge + rank]\n"
                   "  M --> UF\n"
                   "  M --> C"
               )),
        _topic("ranking-pipeline",
               "Ranking: Time Decay x Engagement x Affinity",
               "The feed is not chronological — it is scored. Three dominant signals plus content-"
               "type preference, blended by an ML model that runs over the merged candidate set "
               "within the feed-open latency budget.",
               [
                   ("Time decay",
                    "score *= exp(-age_hours / half_life). Half-life ~6h for friend posts, ~2h for "
                    "celeb posts (their posts age out faster because viewers expect freshness from "
                    "creators). Exponential decay beats linear because it preserves ordering at the "
                    "boundary while rapidly demoting day-old content."),
                   ("Engagement velocity",
                    "likes_per_minute and comments_per_minute over the last hour, normalised by "
                    "author baseline (so a small creator's surge is not drowned by a celeb's "
                    "constant volume). Updated near-real-time by the Engagement Aggregator stream "
                    "job."),
                   ("Viewer-author affinity",
                    "Per-edge feature stored in the Affinity Store: prior reactions, comments, "
                    "profile views, DMs, time-on-post. High affinity boosts a friend's modest post "
                    "above a stranger's viral one. The dominant personalisation signal."),
                   ("Content-type preference",
                    "Per-viewer learnt preference for video vs photo vs text vs share. A user who "
                    "watches 80% videos sees video-heavy ranking. Updated daily by an offline "
                    "training job."),
                   ("Model serving",
                    "Gradient-boosted trees + small DNN (Wide-and-Deep) scores the merged ~few-"
                    "hundred-item candidate set within ~50ms. Heavy offline ranking refreshes "
                    "user_feed scores in the background so subsequent pages are pre-ranked."),
                   ("Edge cases",
                    "Brand-new post has no engagement yet — bootstrap with author baseline. Stale "
                    "post somehow surfaces — time decay clamps the score floor."),
               ]),
        _topic("storage-split",
               "Two Shard Keys: author_id for Posts, viewer_id for Feed",
               "Posts and feeds have opposite access patterns. Sharding both by the same key "
               "would make one of them slow. Maintaining two stores with two shard keys is the "
               "classic write-amplification-for-read-locality trade.",
               [
                   ("Posts DB sharded by author_id",
                    "Authors' posts colocated for /timeline reads, profile views, and the celeb "
                    "pull-merge. A single-shard query lists an author's recent posts."),
                   ("user_feed sharded by viewer_id",
                    "Viewer's pushed feed colocated for /feed reads. Single-shard query returns "
                    "top-K scored entries. Redis sorted set per viewer in the hot tier; Cassandra "
                    "with the same shard key as the durable layer."),
                   ("Cost of the split",
                    "Each post is written once to Posts DB (1 write) and N times to user_feed "
                    "(N = follower count, skipping celebs). Feed reads are a single shard; "
                    "timeline reads are a single shard — both win on the read path."),
                   ("Why not just one store",
                    "Sharding posts by viewer would require duplicating the post body N times — "
                    "huge storage waste. Sharding feed by author would require fan-in on read "
                    "across hundreds of shards — slow. The two-shard split is unavoidable."),
                   ("celeb_timeline as third store",
                    "Sharded by author_id, kept hot in Redis for the top creators. Read-time "
                    "merge during feed open hits this for the celebs the viewer follows."),
               ]),
        _topic("inactive-user-waste",
               "The Inactive-User Problem in Push Fan-out",
               "Fan-out treats every follower equally, but ~70% of followers are inactive on any "
               "given day. Pushing into their caches wastes storage and write bandwidth. The fix "
               "blends activity-aware fan-out with aggressive TTLs.",
               [
                   ("The waste",
                    "A celeb just-below-threshold (say 900K followers) posts and the fan-out "
                    "worker writes 900K user_feed entries — but only ~270K of those users will "
                    "open the app in the next 24h. The other ~630K writes are storage that may "
                    "never be read."),
                   ("Activity-aware fan-out",
                    "Skip fan-out for users with last_active_at older than ~30d. They pull from "
                    "celeb_timeline + author timeline lazily on next return. Reduces pushed "
                    "writes by ~40-60% in practice."),
                   ("Aggressive TTL on user_feed",
                    "Pushed entries TTL ~7d. Dormant viewers' caches naturally evict; on return "
                    "the cache is rebuilt from Cassandra durable tier or recomputed lazily."),
                   ("Priority-queue fan-out",
                    "Fan-out worker writes active followers first (low partition order), dormant "
                    "ones lazily. Active users see the post within seconds; dormant users see it "
                    "minutes later when the worker drains the tail — they would not have noticed."),
                   ("Cost reduction",
                    "Combined: ~50% reduction in fan-out write volume and ~40% reduction in "
                    "user_feed storage for the same SLO on the active path."),
               ]),
        _topic("cursor-pagination",
               "Cursor-Based Pagination for Insert-Heavy Feeds",
               "Offset pagination produces user-visible duplicates and skips on insert-heavy "
               "feeds. Cursor pagination is stable under insertions because it does not depend "
               "on absolute positions — it depends on the score of the last seen item.",
               [
                   ("Why offset breaks",
                    "GET /feed?offset=20&limit=20 returns items 20-39. If 5 new posts arrive at "
                    "the top before the next page-fetch, the next call (offset=40) would return "
                    "items 35-54 in the new ordering — duplicating items 35-39 the user already "
                    "saw. Or the reverse on deletion. Notorious bug at feed scale."),
                   ("Cursor encodes (score, post_id)",
                    "First page returns next_cursor = base64({last_score, last_post_id}). Next "
                    "call: GET /feed?cursor=..., server queries WHERE (score, post_id) < (last_"
                    "score, last_post_id) ORDER BY score DESC, post_id DESC LIMIT N. Stable under "
                    "any number of new inserts at the top."),
                   ("Snapshot semantics",
                    "Optionally embed a snapshot_at timestamp in the cursor — only return posts "
                    "with inserted_at <= snapshot_at, so the user gets a frozen view across the "
                    "whole scroll session. Trade-off: misses fresh posts until /feed open.")
               ,
                   ("Top-of-feed refresh",
                    "Pull-to-refresh issues a fresh /feed call without a cursor (or with cursor "
                    "snapshot_at = now). New posts appear at the top; the user has not seen them, "
                    "so no dupes."),
                   ("Why not opaque token only",
                    "Encode the (score, post_id) so the server is stateless. Stateful cursors "
                    "(server-stored pagination state) add a coordination dependency and break "
                    "horizontal scale."),
               ]),
        _topic("realtime-and-coldstart",
               "Real-time Top-of-Feed Updates and the Cold-Start Path",
               "Two distinct corners of the feed product: pushing deltas to active sessions, and "
               "bootstrapping a feed for users with no graph signal. Both are best-effort and run "
               "as separate services.",
               [
                   ("WebSocket gateway",
                    "Active client opens a WebSocket to the Real-time Gateway. When the Fan-out "
                    "Worker pushes a post into a viewer's user_feed AND the gateway sees that "
                    "viewer is connected, it emits feed.delta {post_id, score}. The client renders "
                    "a 'New posts' banner or auto-prepends. Best-effort delivery — the client "
                    "always reconciles via /feed on app foreground."),
                   ("Long-poll fallback",
                    "Clients that cannot hold a WebSocket (corporate proxies, low-tier mobile) "
                    "fall back to long-poll: GET /feed/realtime?since=cursor blocks for up to "
                    "30s server-side, returns deltas or empty. Higher latency, higher overhead, "
                    "but reachable everywhere."),
                   ("Cold-start recommendation",
                    "New user has no follow graph and no engagement history — the personalised "
                    "merged set is empty. Recommendation Service supplies a seed feed: globally "
                    "popular last-24h posts, posts from suggested-friends and pages captured at "
                    "onboarding (interests, location, contacts upload), and viral content trending "
                    "in the user's region."),
                   ("Phasing in personalisation",
                    "Each engagement event flows through Kafka into the Affinity Store. As the "
                    "viewer follows accounts and reacts to posts, the personalised feed phases "
                    "in — typically within hours of activity. The recommended seed is mixed-in "
                    "for ~7d to keep the feed populated while graph signal accumulates."),
                   ("Edge cases",
                    "Returning user with stale signal: treat as warm-start, blend recommended "
                    "into the personalised feed at low weight. Inactive 90d+ user: re-seed via "
                    "cold-start path until they re-engage."),
               ]),
    ],
)
