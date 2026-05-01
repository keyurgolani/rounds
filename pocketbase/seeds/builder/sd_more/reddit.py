"""Reddit system design question. Loaded automatically via
`sd_questions._load_more` because this module exposes `PAYLOAD`."""
from __future__ import annotations

from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design Reddit",
    "Hard",
    "Design Reddit: a community-driven link/text-aggregation platform organised into subreddits. Users "
    "subscribe to subreddits, submit posts (links, text, media), cast up/down votes, comment in deeply "
    "nested threads, and consume per-subreddit feeds plus a personalised home feed. The system must "
    "handle billions of votes a day with race-free counters under eventual consistency, rank posts via "
    "Reddit's actual scoring formulas (hot, top, new, controversial), serve threaded comments with "
    "thousands of replies efficiently, and police the platform with moderation tools and anti-spam.",
    hints=[
        "Voting is the highest-QPS write path. Idempotent per (user, post): toggling re-press is a no-op or flip.",
        "Counters under contention need sharded counters or async aggregation — never naive UPDATE post SET score = score + 1.",
        "Reddit's hot ranking uses a logarithmic vote weight + time decay (Wilson-derived). Memorise the formula.",
        "Comment threads are deep — store materialised path or use recursive CTE; never N+1 by parent_id.",
        "Subreddit feeds shard by subreddit_id; home feed merges top-K from each subscribed subreddit.",
        "Anti-spam runs at write time (rate limits, shadowban) and async (bot-detection ML).",
    ],
    constraints=[
        "500M+ monthly users, ~100M DAU",
        "1M+ active subreddits with extreme size skew (r/funny vs niche subs)",
        "~10B votes/day, ~50M posts+comments/day",
        "Power-law subreddit traffic: top 100 subs = ~50% of reads",
        "Feed open p99 < 800ms; vote write p99 < 200ms",
        "Highly read-skewed (~100:1 read/write on listings)",
    ],
    req_func=[
        "Subscribe / unsubscribe to subreddits",
        "Create posts (link, text, image, video) inside a subreddit",
        "Cast up/down vote on posts and comments — idempotent toggle",
        "Ranked subreddit feeds: hot, top (1h/day/week/month/year/all), new, controversial",
        "Personalised home feed merging subscribed subreddits",
        "Nested comment threads with deep reply chains",
        "Moderation: remove posts/comments, ban users, configure automod rules",
        "Anti-spam: rate limit, shadowban, bot-detection signals",
    ],
    req_nonfunc=[
        "Vote write p99 < 200ms; feed read p99 < 800ms",
        "Eventual consistency on vote counts (seconds of staleness OK)",
        "99.95% read availability; 99.9% write availability",
        "Race-free counters under massive concurrency (a viral post = 10K votes/min)",
        "Durable: zero post / comment loss",
        "Read-heavy caching: hot subreddit listings + post detail are CDN/edge cacheable",
    ],
    estimation={
        "dau": "100M",
        "subs_active": "1M",
        "posts_per_day": "5M",
        "comments_per_day": "45M",
        "votes_per_day": "10B",
        "qps_vote_steady": "~115K/sec; viral spike: 10×",
        "qps_feed_read": "~200K/sec global steady; 1M/sec peak",
        "storage_per_year": "~50TB posts/comments + multi-PB media",
    },
    endpoints=[
        {"method": "POST", "path": "/subreddits/{name}/subscribe",
         "description": "Subscribe to a subreddit"},
        {"method": "DELETE", "path": "/subreddits/{name}/subscribe",
         "description": "Unsubscribe"},
        {"method": "POST", "path": "/subreddits/{name}/posts",
         "description": "Submit a post",
         "body": "{kind: link|text|image|video, title, url?, body?, media_id?}"},
        {"method": "GET", "path": "/subreddits/{name}",
         "description": "Subreddit feed",
         "body": "?sort=hot|top|new|controversial&t=hour|day|week|all&cursor=opaque"},
        {"method": "GET", "path": "/home",
         "description": "Personalised home feed (subscribed subreddits merged)",
         "body": "?cursor=opaque"},
        {"method": "POST", "path": "/posts/{id}/vote",
         "description": "Idempotent up/down/none vote",
         "body": "{dir: 1|-1|0}"},
        {"method": "POST", "path": "/posts/{id}/comments",
         "description": "Reply to post or comment",
         "body": "{parent_id?, body}"},
        {"method": "GET", "path": "/posts/{id}/comments",
         "description": "Threaded comments",
         "body": "?sort=best|top|new|controversial&depth=10"},
        {"method": "POST", "path": "/posts/{id}/comments/{cid}/vote",
         "description": "Idempotent comment vote",
         "body": "{dir: 1|-1|0}"},
        {"method": "POST", "path": "/mod/{sub}/remove",
         "description": "Moderator removes post/comment",
         "body": "{target_id, reason}"},
        {"method": "POST", "path": "/mod/{sub}/ban",
         "description": "Ban user from subreddit",
         "body": "{user_id, duration_days, reason}"},
    ],
    tables=[
        {"name": "users",
         "columns": ["id BIGINT PK", "handle VARCHAR(32) UNIQUE", "karma_post INT",
                     "karma_comment INT", "is_shadowbanned BOOL", "trust_score FLOAT",
                     "created_at BIGINT"]},
        {"name": "subreddits",
         "columns": ["id BIGINT PK", "name VARCHAR(32) UNIQUE", "description TEXT",
                     "subscriber_count BIGINT", "created_at BIGINT"]},
        {"name": "subscriptions",
         "columns": ["user_id BIGINT", "subreddit_id BIGINT", "created_at BIGINT",
                     "PRIMARY KEY (user_id, subreddit_id)"]},
        {"name": "posts",
         "columns": ["id BIGINT PK", "subreddit_id BIGINT", "user_id BIGINT", "kind VARCHAR(8)",
                     "title VARCHAR(300)", "url TEXT", "body TEXT", "media_id VARCHAR(64)",
                     "ups INT", "downs INT", "score INT", "hot_score DOUBLE",
                     "controversy_score DOUBLE", "comment_count INT",
                     "removed BOOL", "created_at BIGINT"]},
        {"name": "comments",
         "columns": ["id BIGINT PK", "post_id BIGINT", "parent_id BIGINT NULL", "user_id BIGINT",
                     "body TEXT", "path VARCHAR(255)", "depth INT",
                     "ups INT", "downs INT", "score INT", "best_score DOUBLE",
                     "removed BOOL", "created_at BIGINT"]},
        {"name": "votes",
         "columns": ["user_id BIGINT", "target_kind VARCHAR(8)", "target_id BIGINT",
                     "dir SMALLINT", "updated_at BIGINT",
                     "PRIMARY KEY (user_id, target_kind, target_id)"]},
        {"name": "vote_counters_shard",
         "columns": ["target_id BIGINT", "shard SMALLINT", "ups INT", "downs INT",
                     "PRIMARY KEY (target_id, shard)"]},
        {"name": "mod_actions",
         "columns": ["id BIGINT PK", "subreddit_id BIGINT", "moderator_id BIGINT",
                     "target_kind VARCHAR(8)", "target_id BIGINT", "action VARCHAR(16)",
                     "reason TEXT", "created_at BIGINT"]},
        {"name": "subreddit_bans",
         "columns": ["subreddit_id BIGINT", "user_id BIGINT", "expires_at BIGINT NULL",
                     "reason TEXT", "PRIMARY KEY (subreddit_id, user_id)"]},
    ],
    indexes=[
        "(subreddit_id, hot_score DESC) on posts — hot feed",
        "(subreddit_id, score DESC, created_at DESC) on posts — top feed",
        "(subreddit_id, created_at DESC) on posts — new feed",
        "(subreddit_id, controversy_score DESC) on posts — controversial feed",
        "(post_id, path) on comments — threaded fetch by materialised path",
        "(user_id) on subscriptions — list my subreddits",
        "(target_kind, target_id) on votes — count rebuild and audits",
        "(subreddit_id, created_at DESC) on mod_actions",
    ],
    hld_desc=(
        "API gateway fans into Subreddit, Post, Vote, Comment, Feed, and Moderation services. Posts and "
        "comments live in a sharded relational store (Postgres/Vitess) sharded by subreddit_id. Vote "
        "writes go through an idempotent Vote Service that writes to a per-user vote table and increments "
        "sharded counters; an aggregator periodically materialises ups/downs/score and recomputes "
        "hot/best/controversy scores. Per-subreddit feeds are pre-sorted (Redis sorted sets per sort/window) "
        "and read-through cached. The home feed is a read-time top-K merge across the user's subscribed "
        "subreddit feeds. Media uploads use presigned S3 + async processing + CDN. Anti-spam runs at the "
        "edge (rate limits, shadowban check) and asynchronously via a bot-detection pipeline."
    ),
    hld_components=[
        {"name": "Mobile / Web Clients", "role": "Render feeds, post, vote, comment"},
        {"name": "API Gateway", "role": "Auth, rate-limit, region-route"},
        {"name": "Subreddit Service", "role": "Subreddit CRUD, subscriptions"},
        {"name": "Post Service", "role": "Submit/read posts; emit events"},
        {"name": "Vote Service", "role": "Idempotent up/down; sharded counters"},
        {"name": "Counter Aggregator", "role": "Roll up shards; recompute scores"},
        {"name": "Comment Service", "role": "Threaded comments; materialised path"},
        {"name": "Feed Service", "role": "Subreddit pre-sorted feeds; home merge"},
        {"name": "Ranking Job", "role": "Recompute hot/best/controversy on vote bursts"},
        {"name": "Moderation Service", "role": "Removals, bans, automod"},
        {"name": "Anti-Spam / Bot Detection", "role": "Edge rules + async ML"},
        {"name": "Media Pipeline", "role": "Presigned S3 upload + transcode + CDN"},
        {"name": "Search (Elasticsearch)", "role": "Post + subreddit + user search"},
        {"name": "Notification Service", "role": "Reply / mention / mod inbox"},
    ],
    detailed_design={
        "voting_idempotent": (
            "POST /posts/{id}/vote with dir ∈ {-1, 0, 1}. Vote Service does an upsert into votes keyed "
            "by (user_id, target_kind, target_id). The delta vs the previous direction is computed in "
            "the same transaction: prev=0,new=1 → +1 up; prev=1,new=-1 → -1 up, +1 down; prev=1,new=0 "
            "→ -1 up. The delta is applied to vote_counters_shard at shard = hash(user_id) % N to "
            "spread contention. Re-pressing the same direction is a no-op. The user's authoritative "
            "vote row is the source of truth — counters can be rebuilt by a sweep over votes."
        ),
        "race_free_counters": (
            "Naive UPDATE posts SET ups = ups + 1 on a viral post serialises 10K writes/min on a single "
            "row. Solution: shard the counter into N rows per post (vote_counters_shard, N=32). Each "
            "vote increments one shard. A Counter Aggregator reads all shards every few seconds (or "
            "on score-recompute trigger), sums them, and writes the canonical posts.ups/downs/score. "
            "Trade: ups/downs are read from the materialised columns and are seconds-stale by design — "
            "the eventual-consistency contract."
        ),
        "ranking_formulas": (
            "Hot (Reddit's actual): hot = log10(max(|ups-downs|,1)) * sign(ups-downs) + (created_at - "
            "epoch) / 45000. Time term dominates initially; vote term dominates as votes accumulate. "
            "Best (for comments, Wilson lower bound at 95%): WLB(ups, downs) gives confidence-adjusted "
            "score that doesn't punish new high-quality comments. Controversy: ((ups+downs)) ^ "
            "min(ups,downs)/max(ups,downs) — high when total is high AND ratio is near 50/50. Top: "
            "raw score within a time window (1h/day/week/month/year/all). New: created_at DESC. "
            "Scores are recomputed on vote bursts and cached in pre-sorted Redis sorted sets per "
            "(subreddit_id, sort, window)."
        ),
        "subreddit_feeds": (
            "Each (subreddit_id, sort, window) maps to a Redis ZSET with member=post_id, score=ranked "
            "score. Subreddit feed reads do ZREVRANGEBYSCORE with cursor pagination. Cold-store backing: "
            "posts table sharded by subreddit_id with the matching index. The ZSET is the read-through "
            "hot cache; cache miss → materialise from Postgres + warm. ZSETs trim to top ~10K entries "
            "per (subreddit, sort) — pages beyond fall through to DB."
        ),
        "home_feed_merge": (
            "Reddit's home feed is NOT fan-out on write — subscribing/unsubscribing makes that thrash. "
            "Instead: on home open, Feed Service reads the user's subscriptions (cached), fetches top-K "
            "(K~50) from each subscribed subreddit's hot ZSET in parallel, then runs a merge-sort with "
            "personalisation reweighting (recently-visited subs boosted, blocked subs zeroed, NSFW "
            "filter). Bounded by subscription count (median ~50, capped); fan-in is fast. Result cached "
            "for 60–120s per user."
        ),
        "comment_threads": (
            "Materialised-path approach: comments.path = parent.path + '/' + zero-padded comment_id "
            "(e.g. '00012/00045/00091'). Fetching a thread is a single index range scan on (post_id, "
            "path) — depth and ordering fall out for free. Depth is bounded for rendering (default 10); "
            "deeper subthreads collapse behind 'continue this thread'. Sort within sibling group by "
            "best_score (Wilson lower bound). Counter sharding identical to post votes."
        ),
        "media_pipeline": (
            "POST /media/upload returns a presigned S3 PUT URL. Client uploads bytes directly. S3 "
            "ObjectCreated → SQS → transcoder fleet: images get responsive variants + thumbnails; "
            "videos get HLS ABR ladders. Post becomes 'ready' on transcode-complete event. Served "
            "via CDN with long TTL; original kept for archive."
        ),
        "moderation": (
            "Each subreddit has moderators (role rows). Mod actions write a mod_actions audit row and "
            "set posts.removed / comments.removed (soft delete; the row stays for audit, the listing "
            "filters them). Bans live in subreddit_bans with optional expires_at. Automod runs as a "
            "synchronous filter at write time: regex/keyword rules per subreddit can auto-remove or "
            "shadow-remove submissions before they hit the feed."
        ),
        "anti_spam": (
            "Layered: (1) edge — IP + account rate limits via token bucket in Redis (vote: 1/sec/user, "
            "post: 5/min/user, comment: 10/min/user). (2) shadowban — flagged users continue to see "
            "their own writes but writes are filtered from all listings; effective vs naive abuse. "
            "(3) async bot detection — feature pipeline (vote velocity, age, IP entropy, write/read "
            "ratio) into a classifier; high-confidence accounts get shadowbanned; borderline get "
            "rate-throttled. (4) account-trust score gates new-account voting weight: brand-new "
            "accounts cast votes worth less in counters until trust accrues."
        ),
        "slo_contract": (
            "Vote write p99 < 200ms (counters write only; aggregation async). Subreddit hot feed read "
            "p99 < 300ms (Redis ZSET hit). Home feed p99 < 800ms (parallel fan-in over ~50 subs). "
            "Comment thread fetch p99 < 400ms for posts with <10K comments. Eventual consistency on "
            "vote totals: visible within ~5s. Media upload-to-visible: <30s p99."
        ),
    },
    trade_offs=[
        {"option": "Single-row counter vs sharded counters",
         "for_single": "Simple; ups/downs immediately consistent",
         "for_sharded": "Race-free under viral contention; bounded write latency",
         "recommendation": "Sharded — naive single-row update collapses on viral posts; eventual consistency on counters is acceptable UX."},
        {"option": "Fan-out home feed vs read-time merge",
         "for_fanout": "Sub-100ms read, pre-ranked",
         "for_merge": "No churn on subscribe/unsubscribe; bounded fan-in by sub count",
         "recommendation": "Read-time merge — Reddit's subscribe rate would make fan-out maintenance ruinous; subscriptions are bounded so merge stays fast."},
        {"option": "Recursive CTE vs materialised path for comments",
         "for_cte": "No path maintenance; tree shape is implicit",
         "for_path": "Single index range scan per thread fetch; trivial sort/depth",
         "recommendation": "Materialised path — read pattern (whole thread) dominates; CTEs blow up on deep trees."},
        {"option": "Inline vs async ranking score updates",
         "for_inline": "Always-fresh hot ranking",
         "for_async": "Decouples vote latency from score recompute; tolerates bursts",
         "recommendation": "Async with backpressure — votes are O(10B/day); recompute is amortised over batched score updates per post."},
    ],
    tips=[
        "Lead with sharded counters for vote contention — the viral-post math is a clear senior signal.",
        "Quote Reddit's actual hot formula (log10 + time/45000) — interview gold.",
        "Materialised path for comments beats recursive CTE at scale — be specific about why.",
        "Home feed is read-time merge, not fan-out. State the reasoning: subscriptions thrash, fan-in is bounded.",
        "Idempotency on vote: prev/new diff inside the upsert transaction, not a naive increment.",
        "Anti-spam is layered (edge rate limits + shadowban + async ML). Don't conflate.",
    ],
    thought_process=[
        "1. Clarify scope: subreddits, posts, votes, ranking, threaded comments, home feed, mod, anti-spam.",
        "2. Estimate: 10B votes/day → ~115K QPS steady, 1M+ peak on viral posts. Read-skewed 100:1.",
        "3. APIs: subscribe, post, vote (idempotent), comment, feed read, mod actions.",
        "4. Voting: per-user vote row + sharded counters; aggregator materialises.",
        "5. Ranking: Reddit hot/best/controversy formulas in pre-sorted Redis ZSETs per (sub, sort, window).",
        "6. Comments: materialised path; fetch by index range scan; sort by Wilson lower bound.",
        "7. Subreddit feed: ZSET-backed, sharded by subreddit_id.",
        "8. Home feed: read-time top-K merge across subscriptions, cached 60–120s per user.",
        "9. Media: presigned S3 + async transcode + CDN.",
        "10. Moderation: soft-delete with audit; automod regex at write time; bans table.",
        "11. Anti-spam: edge rate limits + shadowban + async bot detection + trust-weighted vote impact.",
        "12. SLO: vote p99<200ms, home p99<800ms, eventual on counters within ~5s.",
    ],
    tags=["social", "feed", "ranking", "comments", "voting"],
    arch_nodes=[
        {"id": "client", "label": "Mobile / Web", "type": "client"},
        {"id": "lb", "label": "API Gateway", "type": "lb"},
        {"id": "sub", "label": "Subreddit Svc", "type": "server"},
        {"id": "post", "label": "Post Svc", "type": "server"},
        {"id": "vote", "label": "Vote Svc", "type": "server"},
        {"id": "agg", "label": "Counter Aggregator", "type": "service"},
        {"id": "comment", "label": "Comment Svc", "type": "server"},
        {"id": "feed", "label": "Feed Svc", "type": "server"},
        {"id": "rank", "label": "Ranking Job", "type": "service"},
        {"id": "mod", "label": "Moderation Svc", "type": "server"},
        {"id": "spam", "label": "Anti-Spam / Bot ML", "type": "service"},
        {"id": "db", "label": "Sharded Postgres", "type": "database"},
        {"id": "shards", "label": "Counter Shards", "type": "database"},
        {"id": "zset", "label": "Feed ZSETs (Redis)", "type": "cache"},
        {"id": "rl", "label": "Rate Limit (Redis)", "type": "cache"},
        {"id": "s3", "label": "S3 Media", "type": "database"},
        {"id": "trans", "label": "Transcoder", "type": "service"},
        {"id": "cdn", "label": "CDN", "type": "cache"},
        {"id": "search", "label": "Elasticsearch", "type": "database"},
        {"id": "kafka", "label": "Kafka", "type": "queue"},
    ],
    arch_edges=[
        {"source": "client", "target": "lb"},
        {"source": "lb", "target": "spam", "label": "rate-limit / shadowban"},
        {"source": "spam", "target": "rl"},
        {"source": "lb", "target": "sub"},
        {"source": "lb", "target": "post"},
        {"source": "post", "target": "db"},
        {"source": "post", "target": "kafka", "label": "post.created"},
        {"source": "lb", "target": "vote"},
        {"source": "vote", "target": "shards", "label": "shard increment"},
        {"source": "vote", "target": "db", "label": "user vote row"},
        {"source": "shards", "target": "agg"},
        {"source": "agg", "target": "db", "label": "materialise ups/downs/score"},
        {"source": "agg", "target": "rank", "label": "trigger recompute"},
        {"source": "rank", "target": "zset", "label": "update sorted set"},
        {"source": "lb", "target": "feed"},
        {"source": "feed", "target": "zset", "label": "subreddit feed"},
        {"source": "feed", "target": "sub", "label": "user subs"},
        {"source": "lb", "target": "comment"},
        {"source": "comment", "target": "db", "label": "path-indexed"},
        {"source": "lb", "target": "mod"},
        {"source": "mod", "target": "db"},
        {"source": "post", "target": "s3", "label": "presigned"},
        {"source": "s3", "target": "trans", "label": "ObjectCreated"},
        {"source": "trans", "target": "cdn"},
        {"source": "client", "target": "cdn", "label": "media GET"},
        {"source": "post", "target": "search", "label": "index"},
        {"source": "kafka", "target": "spam", "label": "bot detection"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant U as User\n"
        "  participant API\n"
        "  participant V as Vote Svc\n"
        "  participant SH as Counter Shards\n"
        "  participant A as Aggregator\n"
        "  participant R as Ranking Job\n"
        "  participant Z as Feed ZSET\n"
        "  participant F as Feed Svc\n"
        "  participant V2 as Viewer\n"
        "  U->>API: POST /posts/{id}/vote {dir:1}\n"
        "  API->>V: idempotent vote\n"
        "  V->>V: upsert votes(prev=0,new=1) -> delta=+1 up\n"
        "  V->>SH: INCR shard[hash(user)]\n"
        "  V-->>U: 200\n"
        "  A->>SH: read all shards\n"
        "  A->>R: score recompute\n"
        "  R->>Z: ZADD post hot_score\n"
        "  V2->>API: GET /subreddits/aww?sort=hot\n"
        "  API->>F: feed\n"
        "  F->>Z: ZREVRANGE\n"
        "  F-->>V2: ranked posts"
    ),
    er_diagram=(
        "erDiagram\n"
        "  USER ||--o{ SUBSCRIPTION : has\n"
        "  SUBREDDIT ||--o{ SUBSCRIPTION : has\n"
        "  SUBREDDIT ||--o{ POST : contains\n"
        "  USER ||--o{ POST : authors\n"
        "  POST ||--o{ COMMENT : has\n"
        "  COMMENT ||--o{ COMMENT : replies\n"
        "  USER ||--o{ VOTE : casts\n"
        "  POST ||--o{ VOTE : receives\n"
        "  SUBREDDIT ||--o{ MOD_ACTION : audited\n"
        "  POST { bigint id PK\n bigint subreddit_id\n bigint user_id\n int score\n double hot_score\n bigint created_at }\n"
        "  COMMENT { bigint id PK\n bigint post_id\n bigint parent_id\n string path\n int depth\n int score }\n"
        "  VOTE { bigint user_id\n string target_kind\n bigint target_id\n smallint dir }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B[Read-skewed, 10B votes/day]\n"
        "  B --> C{Counter strategy?}\n"
        "  C -->|Single row| D[Viral post collapses one row]\n"
        "  C -->|Sharded| E[Race-free under contention]\n"
        "  E --> F[Aggregator materialises ups/downs/score]\n"
        "  F --> G[Ranking job: hot/best/controversy]\n"
        "  G --> H[Per-subreddit ZSET feeds]\n"
        "  H --> I{Home feed?}\n"
        "  I -->|Fan-out| J[Thrashes on subscribe]\n"
        "  I -->|Read-merge| K[Top-K from each sub, cached 60s]\n"
        "  K --> L[Comments: materialised path]\n"
        "  L --> M[Anti-spam layered: edge + shadowban + ML]"
    ),
    tradeoff_title="Counter strategy under viral-post contention",
    tradeoff_options=[
        {"label": "Single-row UPDATE",
         "description": "UPDATE posts SET ups = ups + 1 on every vote.",
         "pros": ["Trivially consistent ups/downs", "One write, one row"],
         "cons": ["Row-lock contention serialises 10K votes/min on a viral post",
                 "Tail latency explodes; vote p99 misses SLO",
                 "DB hot-spot risk"]},
        {"label": "Sharded counters + async aggregator",
         "description": "Each vote increments one of N shards; aggregator sums periodically.",
         "pros": ["Race-free at any QPS", "Bounded write latency",
                  "Authoritative votes table can rebuild counters"],
         "cons": ["Counters are seconds-stale (eventual)",
                 "Aggregator + recompute scheduling complexity"]},
        {"label": "In-memory atomic (Redis INCR)",
         "description": "All counters live in Redis; persist to DB asynchronously.",
         "pros": ["Lowest possible write latency", "No DB row contention"],
         "cons": ["Durability risk on Redis loss",
                 "Two-system consistency to manage",
                 "Counter rebuild on disaster is expensive"]},
    ],
    tradeoff_rec="Sharded counters + async aggregator. Authoritative source remains the votes table; sharding eliminates row-lock contention; counters as materialised columns are fine to be seconds-stale.",
    senior_topics=[
        _topic("hot-ranking-formula",
               "Reddit's Hot Ranking — Logarithmic Votes + Linear Time",
               "Reddit's hot algorithm uses a log-scale vote weight added to a linear time term. The "
               "log dampens vote dominance so a 5-year-old post with 100K upvotes doesn't permanently "
               "outrank a today-post with 1K upvotes. Time wins early; votes win later.",
               [
                   ("The actual formula",
                    "hot(ups, downs, t) = log10(max(|ups - downs|, 1)) * sign(ups - downs) + "
                    "(t - 1134028003) / 45000. The 45000 constant is ~12.5 hours: every 12.5 hours "
                    "of age is worth one log10-unit of net votes."),
                   ("Why log on votes",
                    "Linear vote weight means a post with 1M upvotes outranks anything for years. "
                    "Log compresses: 10× more votes = +1 score, so freshness can compete with virality."),
                   ("Why linear on time",
                    "Time is the natural rank-decay axis. Linear with the log makes the cross-over "
                    "point predictable — exactly when 12.5 hours of age equals one order of magnitude "
                    "of net votes."),
                   ("Recompute strategy",
                    "Hot score depends on time, so it would change every second. Reddit recomputes "
                    "on vote arrival: each vote triggers a score update for that post (debounced). "
                    "ZSET in Redis holds top-K per (subreddit, hot)."),
                   ("Variant: best for comments (Wilson)",
                    "For comments, hot's log-with-time biases new comments. Best uses the Wilson "
                    "lower bound at 95%: a confidence interval on the true upvote rate. New high-quality "
                    "comments rise even with few votes; one early downvote doesn't crush them."),
                   ("Variant: controversial",
                    "controversy = (ups + downs) ^ (min(ups,downs)/max(ups,downs)). High when total "
                    "is large AND ratio is near 1.0. Surfaces hot-button content that gets equal "
                    "love and hate."),
               ],
               diagram=(
                   "graph TD\n"
                   "  V[Vote arrives] --> S[Update sharded counters]\n"
                   "  S --> A[Aggregator sums shards]\n"
                   "  A --> H[Recompute hot = log10 + t/45000]\n"
                   "  A --> B[Recompute best = Wilson LB]\n"
                   "  A --> C[Recompute controversy]\n"
                   "  H --> Z[ZADD subreddit:hot post]\n"
                   "  B --> Z2[ZADD post:best comment]\n"
                   "  C --> Z3[ZADD subreddit:controversial post]"
               )),
        _topic("sharded-counters",
               "Sharded Counters for Race-Free Voting",
               "A viral post draws 10K+ votes/min. Naive UPDATE serialises on the row lock; tail "
               "latency collapses. Sharded counters spread the writes across N rows; an aggregator "
               "materialises the sum into the canonical column.",
               [
                   ("The contention math",
                    "10K votes/min on one post = 167 writes/sec on one row. Postgres row-lock holds "
                    "for ~1ms; that's 167ms of contention per second — vote p99 already misses the "
                    "200ms SLO. Worse posts are 100K/min."),
                   ("Sharding scheme",
                    "vote_counters_shard(target_id, shard, ups, downs). Shard = hash(user_id) % N "
                    "with N=32 — a per-user-stable shard so re-pressing a vote is idempotent on the "
                    "same row. Writes spread to 32 rows: 5 writes/sec/row, no contention."),
                   ("Aggregation",
                    "Counter Aggregator runs on a schedule (every ~1s for hot posts, slower for cold) "
                    "or triggered by per-post write counters crossing a threshold. SUM(ups), SUM(downs) "
                    "across shards → write back to posts.ups/downs/score in a single UPDATE."),
                   ("Idempotency",
                    "Authoritative source is the votes table (PK on user_id+target). On vote change "
                    "the Vote Service computes prev→new delta inside the same upsert transaction "
                    "and applies that delta to its user-deterministic shard. Re-pressing same direction "
                    "yields delta=0 — no shard write."),
                   ("Disaster rebuild",
                    "If shard data is lost: a sweep over votes by target_id rebuilds shards "
                    "deterministically. Authoritative votes table makes this safe."),
                   ("Why not Redis only",
                    "Redis INCR is fast but not durable across failover without complex setup. "
                    "Postgres-resident shards + async aggregation hits the SLO and keeps durability."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant U1\n  participant U2\n  participant V as Vote Svc\n"
                   "  participant S0 as shard 0\n  participant S5 as shard 5\n  participant A as Aggregator\n"
                   "  U1->>V: vote dir=1\n"
                   "  V->>S0: INCR ups (hash(U1)%32==0)\n"
                   "  U2->>V: vote dir=1\n"
                   "  V->>S5: INCR ups (hash(U2)%32==5)\n"
                   "  A->>S0: SUM\n  A->>S5: SUM\n"
                   "  A->>A: recompute hot/best\n"
                   "  A->>A: write posts.ups/downs/score"
               )),
        _topic("comment-tree-storage",
               "Materialised Path for Threaded Comments",
               "Comments form deep trees (10+ levels common). Naive parent_id traversal is N+1. "
               "Materialised path encodes ancestry into a single sortable string so a thread fetch "
               "is one indexed range scan.",
               [
                   ("The schema",
                    "comments(id, post_id, parent_id, path, depth, ups, downs, body, ...). path is "
                    "'/'-separated zero-padded ancestor IDs: '00012/00045/00091'. depth is len(path "
                    "split). On insert, child.path = parent.path + '/' + zfill(child.id)."),
                   ("Thread fetch query",
                    "SELECT * FROM comments WHERE post_id = ? ORDER BY path. The (post_id, path) "
                    "index produces the entire tree in pre-order traversal. One round trip; render "
                    "the tree by walking depth changes."),
                   ("Sorting siblings",
                    "Within a parent, sort by best_score (Wilson lower bound) — done at render time "
                    "by grouping siblings by parent path prefix and sorting each group. Alternative: "
                    "include best_score in the order key for free DB-side sorting at the cost of "
                    "tree-shape sortability."),
                   ("Deep-thread collapse",
                    "Default depth limit is 10 in the API. Deeper subtrees render as 'continue this "
                    "thread' link → fetches the subtree by WHERE path LIKE '00012/00045/%'."),
                   ("Why not recursive CTE",
                    "Recursive CTEs touch each row in the tree per query and don't scale on hot "
                    "posts with 10K+ comments. The materialised-path index reduces it to O(log N) "
                    "seek + sequential scan of the tree's slice."),
                   ("Why not nested sets",
                    "Nested sets have cheap reads but expensive insert (recomputing left/right "
                    "bounds on N rows per insert). Comments are insert-heavy near hot posts; "
                    "materialised path's per-insert cost is one parent fetch."),
                   ("ID width caveat",
                    "Path width caps thread depth times zero-padded ID length. With 5-digit IDs "
                    "and 255-char path that's ~40 levels — beyond UI; safe."),
               ],
               diagram=(
                   "graph TD\n"
                   "  R[post_id=42] --> C1[id=12 path=00012]\n"
                   "  C1 --> C2[id=45 path=00012/00045]\n"
                   "  C2 --> C3[id=91 path=00012/00045/00091]\n"
                   "  C1 --> C4[id=77 path=00012/00077]\n"
                   "  Q[SELECT WHERE post_id=42 ORDER BY path] --> O[returns 00012, 00012/00045, 00012/00045/00091, 00012/00077]"
               )),
        _topic("home-feed-merge",
               "Home Feed via Read-Time Top-K Merge",
               "Reddit's home is the merge of subscribed-subreddit hot feeds. Fan-out on write "
               "would thrash on subscribe/unsubscribe; merge-on-read is bounded by the user's "
               "subscription count and stays fast.",
               [
                   ("Why not fan-out",
                    "Subscribing a user to a popular subreddit would copy thousands of posts into "
                    "their materialised home feed. Unsubscribing requires removing them. Average "
                    "subscribe rate × subscriber count makes the write cost intolerable."),
                   ("Read-time merge",
                    "On home open: fetch user's subscriptions (cached). For each subreddit fetch "
                    "top-K (K=50) from the hot ZSET in parallel. Merge into a single ranked list "
                    "with personalisation (recency/affinity reweight; block list filter; NSFW filter)."),
                   ("Bounded fan-in",
                    "Median subscriptions ~50; cap at ~250 active subscriptions for power users. "
                    "Parallel ZRANGE fan-out completes in ~10–30ms; merge is in-memory."),
                   ("Personalisation",
                    "Each candidate post score in the merge is reweighted by user-specific factors: "
                    "recently-visited subs get a small boost, dwell-history feeds the ranker, "
                    "blocked subs filter out, repeated authors deduplicated."),
                   ("Caching",
                    "Result cached per-user with 60–120s TTL. Vote/post events do not invalidate; "
                    "users tolerate slightly stale ordering. Pull-to-refresh forces recompute."),
                   ("Why this works at Reddit's scale",
                    "Read amplification (50 ZRANGEs per home open) is fine — ZSETs are O(log N + K) "
                    "and Redis is in-memory. The pattern scales horizontally by Redis sharding on "
                    "subreddit_id."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant U as User\n  participant F as Feed Svc\n"
                   "  participant S as Sub Svc\n  participant Z1 as ZSET sub A\n"
                   "  participant Z2 as ZSET sub B\n  participant Z3 as ZSET sub C\n"
                   "  U->>F: GET /home\n"
                   "  F->>S: list subs (cached)\n"
                   "  par fan-in\n"
                   "    F->>Z1: ZREVRANGE 0 50\n"
                   "  and\n"
                   "    F->>Z2: ZREVRANGE 0 50\n"
                   "  and\n"
                   "    F->>Z3: ZREVRANGE 0 50\n"
                   "  end\n"
                   "  F->>F: merge + personalise\n"
                   "  F-->>U: ranked home"
               )),
        _topic("anti-spam-layered",
               "Layered Anti-Spam: Edge + Shadowban + Async ML",
               "No single defence stops bots — each layer trades off latency, false-positive cost, "
               "and detection power. Together they keep the platform usable.",
               [
                   ("Edge rate limits",
                    "Token-bucket per user + per IP in Redis. Vote: 1/sec; post: 5/min; comment: "
                    "10/min. Bursts allowed via bucket capacity. Cheap, sub-millisecond, kills the "
                    "obvious abuse."),
                   ("Shadowban",
                    "Flagged users continue to see their own posts/comments/votes succeed locally, "
                    "but writes are filtered out of all listing queries (post/comment/feed). "
                    "Devastatingly effective vs naive bots that don't check engagement."),
                   ("Async bot detection",
                    "Feature pipeline reads write events from Kafka: vote velocity, account age, "
                    "IP / device entropy, write/read ratio, content embedding similarity to known "
                    "spam. Classifier emits {shadowban | rate-throttle | trusted}; high-confidence "
                    "shadowbans applied automatically; borderline reviewed by ops."),
                   ("Trust-weighted vote impact",
                    "User trust score (0..1) acts as a multiplier on vote count contribution: a "
                    "5-minute-old account voting 100 times in a minute contributes near-zero to the "
                    "actual ups/downs. Trust grows with age, karma, and clean record. Sybil attacks "
                    "that flood new accounts gain no ranking purchase."),
                   ("Account-level controls",
                    "CAPTCHA on signup; phone-number rate limit per number; email-domain reputation; "
                    "vote-manipulation detection (highly correlated voting groups across posts) "
                    "triggers temporary holds."),
                   ("Why not just async ML",
                    "ML has minutes of latency. Edge limits + shadowban catch obvious abuse instantly. "
                    "ML catches the sophisticated tail."),
               ]),
        _topic("moderation-tools",
               "Moderation: Removals, Bans, and Automod at Scale",
               "Each subreddit is a small republic. Mod actions must be auditable, fast, and "
               "support automation since hot subreddits get thousands of new submissions/hour.",
               [
                   ("Soft removals",
                    "Mod 'remove' sets posts.removed=true / comments.removed=true and writes a "
                    "mod_actions audit row. Listing queries filter removed=false. Author still "
                    "sees their own removed content (UX choice; prevents endless re-submission). "
                    "Hard delete reserved for ToS-violating content with separate audit."),
                   ("Bans",
                    "subreddit_bans(subreddit_id, user_id, expires_at, reason) checked at write time "
                    "by the Post/Comment Service. Cached per-user per-sub for fast write checks; "
                    "TTL = ban duration."),
                   ("Automod",
                    "Per-subreddit YAML rules: regex on title/body, link-domain blocklists, account-age "
                    "thresholds, karma minimums. Runs synchronously on submission and can remove, "
                    "shadow-remove (visible only to author), or report. Compiled rule sets cached "
                    "per subreddit."),
                   ("Mod queue",
                    "Reports + automod-flagged content land in /mod/{sub}/queue, sorted by report "
                    "count + time. Mods action from a dedicated UI; bulk actions supported."),
                   ("Audit and reversal",
                    "All mod_actions are immutable; reversals are new rows. Subreddit log is the "
                    "ground truth — supports appeal flows and admin oversight."),
                   ("Cross-subreddit signals",
                    "Site-wide admins use mod_actions stream + bot-detection signals to escalate "
                    "from per-sub bans to platform-level account actions for serial offenders."),
               ]),
    ],
)
