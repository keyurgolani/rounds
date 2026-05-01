"""Stack Overflow system design question. Loaded automatically via
`sd_questions._load_more` because this module exposes `PAYLOAD`."""
from __future__ import annotations

from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design Stack Overflow",
    "Medium",
    "Design Stack Overflow: a programming Q&A platform where users post questions, answer others, and "
    "comment on both. Content is voted up/down, the asker can mark one answer as accepted, and users "
    "earn reputation for upvotes/accepts that gates privileges (e.g. comment, vote, edit, close). "
    "Questions are organised by tags and made discoverable via tag pages and full-text search "
    "(Elasticsearch). Markdown content is editable with full revision history. Badges fire as "
    "asynchronous events when users hit milestones. Moderation queues handle flags, low-quality posts, "
    "and close/reopen votes; anti-spam runs at write time. The workload is overwhelmingly read-heavy "
    "(~99:1 reads:writes) thanks to Google traffic landing on question pages — every layer must be "
    "cache-friendly, with a sitemap pipeline feeding search engines.",
    hints=[
        "Read:write is ~99:1 — design every hot path to be cache-served (CDN edge + Redis), not DB-served.",
        "Voting must be idempotent per (user, post): re-pressing same direction is a no-op; flipping is one delta.",
        "Reputation is derived from vote events — store the events, materialise rep async; never trust a counter as the source of truth.",
        "Privileges are reputation thresholds (e.g. comment ≥ 50, vote-up ≥ 15, close ≥ 3000) — gate at write time, cache the user's flags.",
        "Edit history keeps every revision (markdown) — the post body is the most recent revision; older ones are immutable.",
        "Badges are event-driven: a Badge Service consumes vote/post/answer events from Kafka and awards on rule match; idempotent per (user, badge).",
        "Search is Elasticsearch over question title + body + tags + answers; ranking blends BM25 with score and recency.",
        "Sitemap generation is a batch job emitting daily compressed XML segments to S3+CDN — Google needs them current within ~24h.",
    ],
    constraints=[
        "~100M monthly users, ~10M DAU (mostly anonymous Google traffic)",
        "~25M questions, ~35M answers, ~75M comments — corpus grows ~10K Q + 15K A per day",
        "~99:1 read:write (anonymous viewers vastly outnumber authors)",
        "Question page p99 < 300ms (cache-served); search p99 < 500ms",
        "Vote / comment write p99 < 250ms",
        "Eventually-consistent reputation (seconds-to-minutes staleness OK)",
        "Markdown content; every edit kept forever for revision history",
    ],
    req_func=[
        "Ask a question with title, body (markdown), and 1–5 tags",
        "Post answers to a question; one answer can be marked accepted by the asker",
        "Comment on questions and answers",
        "Cast up/down vote on questions, answers, and (only up) comments — idempotent toggle",
        "Edit a question/answer with full revision history; show diff between revisions",
        "Earn reputation from upvotes (+10 question / +10 answer), accepted answer (+15), accept-bonus (+2 to asker), downvotes (-2 to author / -1 to voter)",
        "Privileges unlock at reputation thresholds (comment, vote, edit-others, close, etc.)",
        "Browse by tag and view tag pages with feeds (newest, active, votes)",
        "Full-text search across questions, answers, tags",
        "Award badges (bronze/silver/gold) for milestones (first answer, 10-upvoted answer, etc.)",
        "Flag posts; moderation queues for review (low-quality, spam, close/reopen votes)",
        "Generate sitemaps so search engines can crawl new questions",
    ],
    req_nonfunc=[
        "Read-heavy: question page p99 < 300ms via CDN+Redis cache; search p99 < 500ms",
        "Vote/comment write p99 < 250ms",
        "Eventually-consistent reputation and badges (staleness < 60s acceptable)",
        "99.95% read availability; 99.9% write availability",
        "Durable: zero post / revision / vote loss",
        "Anti-spam latency budget: synchronous filter < 50ms; async ML out-of-band",
        "Sitemap freshness: new questions appear in sitemap within 24h",
    ],
    estimation={
        "dau": "10M",
        "anonymous_visits_per_day": "~150M (Google landing)",
        "questions_per_day": "~10K",
        "answers_per_day": "~15K",
        "comments_per_day": "~80K",
        "votes_per_day": "~3M",
        "qps_question_read": "~30K/sec steady; 100K/sec peak (cache-served)",
        "qps_search": "~5K/sec steady",
        "qps_write": "~1K/sec aggregate (vote+comment+edit)",
        "storage_per_year": "~200GB text + revisions; multi-TB with indexes and sitemaps",
    },
    endpoints=[
        {"method": "POST", "path": "/questions",
         "description": "Ask a question",
         "body": "{title, body_md, tags:[1..5]}"},
        {"method": "GET", "path": "/questions/{id}",
         "description": "Question with answers + comments (cached)"},
        {"method": "POST", "path": "/questions/{id}/answers",
         "description": "Post an answer",
         "body": "{body_md}"},
        {"method": "POST", "path": "/posts/{id}/comments",
         "description": "Comment on question or answer (markdown subset)",
         "body": "{body_md}"},
        {"method": "POST", "path": "/posts/{id}/vote",
         "description": "Idempotent up/down/none vote",
         "body": "{dir: 1|-1|0}"},
        {"method": "POST", "path": "/questions/{qid}/answers/{aid}/accept",
         "description": "Asker marks an answer accepted (replaces any prior accept)"},
        {"method": "PUT", "path": "/posts/{id}",
         "description": "Edit a post; creates a new revision",
         "body": "{title?, body_md?, tags?, comment}"},
        {"method": "GET", "path": "/posts/{id}/revisions",
         "description": "Revision history with diffs"},
        {"method": "GET", "path": "/tags/{tag}",
         "description": "Tag page",
         "body": "?sort=newest|active|votes&cursor=opaque"},
        {"method": "GET", "path": "/search",
         "description": "Full-text search",
         "body": "?q=...&tag=...&sort=relevance|newest|votes"},
        {"method": "POST", "path": "/posts/{id}/flag",
         "description": "Flag a post for moderation",
         "body": "{reason}"},
        {"method": "POST", "path": "/mod/queue/{kind}/action",
         "description": "Moderator action on queue item",
         "body": "{item_id, action: approve|reject|close|reopen}"},
        {"method": "GET", "path": "/users/{id}/badges",
         "description": "User's earned badges"},
        {"method": "GET", "path": "/sitemap-{n}.xml.gz",
         "description": "Sitemap segment (S3+CDN)"},
    ],
    tables=[
        {"name": "users",
         "columns": ["id BIGINT PK", "handle VARCHAR(40) UNIQUE", "email VARCHAR(120)",
                     "reputation INT", "trust_score FLOAT", "is_moderator BOOL",
                     "is_suspended BOOL", "created_at BIGINT"]},
        {"name": "posts",
         "columns": ["id BIGINT PK", "kind VARCHAR(8)",  # 'question' | 'answer'
                     "parent_id BIGINT NULL",  # answer.question
                     "user_id BIGINT", "title VARCHAR(300) NULL",
                     "body_md TEXT", "body_html TEXT",  # rendered cache
                     "score INT", "ups INT", "downs INT", "answer_count INT",
                     "view_count BIGINT", "accepted_answer_id BIGINT NULL",
                     "is_closed BOOL", "is_deleted BOOL",
                     "created_at BIGINT", "last_activity_at BIGINT"]},
        {"name": "post_revisions",
         "columns": ["id BIGINT PK", "post_id BIGINT", "user_id BIGINT", "rev_number INT",
                     "title VARCHAR(300) NULL", "body_md TEXT", "tags_snapshot TEXT",
                     "edit_comment VARCHAR(255)", "created_at BIGINT"]},
        {"name": "comments",
         "columns": ["id BIGINT PK", "post_id BIGINT", "user_id BIGINT",
                     "body_md TEXT", "score INT", "is_deleted BOOL", "created_at BIGINT"]},
        {"name": "tags",
         "columns": ["id BIGINT PK", "name VARCHAR(40) UNIQUE", "description TEXT",
                     "question_count INT", "created_at BIGINT"]},
        {"name": "post_tags",
         "columns": ["post_id BIGINT", "tag_id BIGINT", "PRIMARY KEY (post_id, tag_id)"]},
        {"name": "votes",
         "columns": ["user_id BIGINT", "target_kind VARCHAR(8)", "target_id BIGINT",
                     "dir SMALLINT", "rep_event_id BIGINT", "updated_at BIGINT",
                     "PRIMARY KEY (user_id, target_kind, target_id)"]},
        {"name": "vote_counters_shard",
         "columns": ["target_id BIGINT", "shard SMALLINT", "ups INT", "downs INT",
                     "PRIMARY KEY (target_id, shard)"]},
        {"name": "reputation_events",
         "columns": ["id BIGINT PK", "user_id BIGINT", "kind VARCHAR(24)",
                     "delta INT", "source_kind VARCHAR(8)", "source_id BIGINT",
                     "created_at BIGINT"]},
        {"name": "badges",
         "columns": ["id BIGINT PK", "name VARCHAR(40) UNIQUE",
                     "tier VARCHAR(8)",  # bronze | silver | gold
                     "description TEXT", "rule_id VARCHAR(40)"]},
        {"name": "user_badges",
         "columns": ["user_id BIGINT", "badge_id BIGINT", "awarded_at BIGINT",
                     "source_kind VARCHAR(8)", "source_id BIGINT",
                     "PRIMARY KEY (user_id, badge_id, source_id)"]},
        {"name": "flags",
         "columns": ["id BIGINT PK", "post_id BIGINT", "user_id BIGINT",
                     "reason VARCHAR(40)", "status VARCHAR(16)",  # open|approved|rejected
                     "created_at BIGINT"]},
        {"name": "mod_actions",
         "columns": ["id BIGINT PK", "moderator_id BIGINT", "target_kind VARCHAR(8)",
                     "target_id BIGINT", "action VARCHAR(24)", "reason TEXT",
                     "created_at BIGINT"]},
        {"name": "close_votes",
         "columns": ["post_id BIGINT", "user_id BIGINT", "reason VARCHAR(40)",
                     "created_at BIGINT", "PRIMARY KEY (post_id, user_id)"]},
    ],
    indexes=[
        "(kind, created_at DESC) on posts — newest questions feed",
        "(kind, last_activity_at DESC) on posts — active feed",
        "(kind, score DESC) on posts — top votes",
        "(parent_id, score DESC) on posts — answers under a question, by score",
        "(post_id, rev_number) on post_revisions — revision walk",
        "(post_id, created_at) on comments",
        "(tag_id, post_id) on post_tags — tag → posts",
        "(target_kind, target_id) on votes — count rebuild and audit",
        "(user_id, created_at DESC) on reputation_events — user rep timeline",
        "(post_id, status) on flags — open flags per post",
    ],
    hld_desc=(
        "API gateway fans into Question, Answer, Comment, Vote, Reputation, Badge, Search, Tag, "
        "Moderation, and Sitemap services. Posts live in sharded Postgres (sharded by question id; "
        "answers + comments + revisions co-locate with their question for thread-locality). Markdown "
        "is rendered to HTML on write and cached as body_html; the rendered question page (header + "
        "answers + top comments) is stored in Redis and at the CDN edge with long TTLs and "
        "tag-based invalidation on edits/votes. Voting writes go through an idempotent Vote Service "
        "that updates per-user vote rows and sharded counters and emits a vote event to Kafka. The "
        "Reputation Service consumes vote/accept events and applies deltas to users.reputation as "
        "append-only reputation_events (rebuildable). The Badge Service is a separate Kafka consumer "
        "with rule plug-ins; awards are idempotent per (user, badge, source). Search runs on "
        "Elasticsearch indexed via Kafka CDC; ranking blends BM25 with score and recency. A nightly "
        "(or hourly) Sitemap Job reads the question stream and writes compressed segmented XML to "
        "S3 + CDN. Anti-spam runs at the edge (rate limits, account-trust gates) and async (ML "
        "classifier on content + behaviour features)."
    ),
    hld_components=[
        {"name": "Web / Mobile / Anonymous Crawlers", "role": "Render question pages, post, vote"},
        {"name": "CDN", "role": "Edge-cache rendered question pages and tag pages"},
        {"name": "API Gateway", "role": "Auth, rate-limit, route"},
        {"name": "Question Service", "role": "Ask/read questions; emit events"},
        {"name": "Answer Service", "role": "Post answers; accept marker"},
        {"name": "Comment Service", "role": "Comments under question/answer"},
        {"name": "Vote Service", "role": "Idempotent up/down with sharded counters"},
        {"name": "Reputation Service", "role": "Consume vote/accept events; append rep_events"},
        {"name": "Privilege Resolver", "role": "Compute privilege flags from reputation"},
        {"name": "Badge Service", "role": "Event-driven badge awards via rule plug-ins"},
        {"name": "Search (Elasticsearch)", "role": "Full-text over title/body/tags/answers"},
        {"name": "Tag Service", "role": "Tag pages, tag counts"},
        {"name": "Moderation Service", "role": "Flags, queues, close/reopen votes, mod actions"},
        {"name": "Anti-Spam", "role": "Edge rate limits + async ML"},
        {"name": "Markdown Renderer", "role": "Render body_md → body_html on write"},
        {"name": "Revision Service", "role": "Append-only post_revisions; diffs"},
        {"name": "Sitemap Job", "role": "Batch generate compressed XML segments → S3+CDN"},
        {"name": "Kafka", "role": "Event bus: vote, post, accept, edit"},
        {"name": "Sharded Postgres", "role": "Posts, comments, votes, revisions"},
        {"name": "Redis", "role": "Rendered page cache + rate-limit buckets + privilege cache"},
    ],
    detailed_design={
        "qa_hierarchy": (
            "All long-form content lives in a single posts table with kind ∈ {question, answer}. "
            "Answers point at their question via parent_id; comments live in their own table keyed "
            "by post_id (so a comment can target either a question or an answer uniformly). The "
            "asker's accepted_answer_id on the question row points at the chosen answer; only the "
            "asker (or a moderator) can flip it. answer_count and last_activity_at on the question "
            "row are denormalised counters maintained on insert/edit. Sharding by question id keeps "
            "the entire thread (question + its answers + their comments + revisions) on one shard, "
            "so the question page reads from a single shard."
        ),
        "voting_idempotent": (
            "POST /posts/{id}/vote with dir ∈ {-1, 0, 1}. Vote Service does an upsert into votes "
            "keyed by (user_id, target_kind, target_id) and computes the delta vs the previous "
            "direction inside the same transaction. Re-pressing the same direction is a no-op "
            "(delta=0). The delta increments / decrements one row of vote_counters_shard at "
            "shard=hash(user_id) % N to spread contention. The same transaction emits a vote event "
            "to Kafka so the Reputation Service can apply rep deltas. Counters are eventually "
            "materialised to posts.ups/downs/score by the aggregator. The votes table is the "
            "authoritative source — counters and rep can be rebuilt from it."
        ),
        "reputation_system": (
            "Reputation is computed from append-only reputation_events. Rules: question/answer "
            "upvote +10; question downvote -2 (voter -1); answer downvote -2 (voter -1); accepted "
            "answer +15 to author, +2 to asker; accept revoke reverses both. The Reputation Service "
            "consumes vote / accept events from Kafka, writes a reputation_events row keyed by "
            "(source_kind, source_id, kind) for idempotency, and updates users.reputation via "
            "atomic UPDATE rep = rep + delta. The events table is the ledger; users.reputation is "
            "a materialised total. On any inconsistency, replay events to rebuild. Rep changes are "
            "visible within seconds — eventual consistency is fine and matches user expectation."
        ),
        "privileges": (
            "Privileges are reputation thresholds: ask/answer (1), comment everywhere (50), vote-up "
            "(15), vote-down (125), edit-others-suggested (1000), close/reopen votes (3000), "
            "trusted-user (20000). The Privilege Resolver reads the user's reputation and produces "
            "a small flags struct cached in Redis per user (TTL ~60s, invalidated on rep change). "
            "Write paths gate on these flags — e.g. POST /comments rejects if !flags.can_comment. "
            "Cheap edge check; correctness re-verified server-side because privileges are also "
            "checked at the service layer."
        ),
        "tagging_search": (
            "Tags are a small dimension table (~60K tags). Each post has 1–5 tags via post_tags. "
            "Tag pages read via the (tag_id, post_id) index joined to posts ordered by sort. "
            "Full-text search lives in Elasticsearch indexed off Kafka (post.created / post.edited "
            "/ post.voted events). The ES doc per question contains title, body_md, answer bodies, "
            "tags, score, accepted flag, and timestamps. Ranking function: BM25 on text, plus a "
            "log-scaled score boost (log(1+score)*α) and a recency decay term — surfaces canonical "
            "high-rep answers ahead of fresh-but-empty pages."
        ),
        "edit_history": (
            "Every edit creates a new post_revisions row with rev_number = previous + 1 inside the "
            "same transaction that updates posts.body_md / title / tags. The posts row is always the "
            "current revision; older revisions are immutable. Diffs are computed at read time "
            "(server-side line-level diff, cached). Only privileged users can edit others' posts; "
            "edit suggestions from low-rep users land in the Suggested Edit queue for review."
        ),
        "accepted_answer": (
            "Question rows have nullable accepted_answer_id. Only the question author (or a mod) "
            "can set/change it. Toggling emits an accept event with old/new answer ids; Reputation "
            "Service applies +15 to new answer's author and -15 to old (if any) plus +2 / -2 on "
            "the asker. The acceptance flag boosts the answer's display order independently of "
            "score (accepted answer pinned at top by default; toggleable to score-sort)."
        ),
        "badges_event_driven": (
            "A Badge Service is a Kafka consumer over post / answer / vote / accept events. Each "
            "badge is a rule plug-in that takes the user_id and event context and decides if a "
            "badge should be awarded. Examples: 'Teacher' (first answer with score ≥ 1) on the "
            "first vote-up event for a user's answer; 'Nice Answer' on score crossing 10; "
            "'Self-Learner' on accepting your own answer with score ≥ 3. Awards are idempotent "
            "via PRIMARY KEY (user_id, badge_id, source_id) on user_badges — a duplicate event is "
            "a no-op. Rule plug-ins are registered declaratively; new badges ship as data, not "
            "code redeploys."
        ),
        "moderation_queues": (
            "Flags, low-quality posts (heuristic + ML), and close/reopen votes feed into per-queue "
            "tables. Mod queue UI pulls open items prioritised by flag count + age. Mod actions "
            "(close, reopen, delete, undelete, edit) write a mod_actions audit row. Close/reopen "
            "is community-driven: 5 close-vote rows from privileged users (rep ≥ 3000) on the "
            "same post auto-close it; 3 reopen votes reverse. Suspensions are time-bounded user "
            "flags checked at write time."
        ),
        "anti_spam": (
            "Layered: (1) edge — token-bucket rate limits in Redis (ask: 1/min/user, answer: "
            "5/min, comment: 10/min, vote: 30/min). (2) account-trust — new accounts (rep < 10) "
            "have stricter rate limits and writes get auto-flagged for review. (3) synchronous "
            "content filter: regex blocklists + URL blocklists run < 50ms. (4) async ML on Kafka "
            "events: classifier reads {writer age, link density, vote velocity, content embedding} "
            "and emits {clean | review | shadow} verdicts; high-confidence shadowed posts are "
            "filtered from listings while still visible to author."
        ),
        "sitemap_generation": (
            "Sitemap Job runs hourly. It queries posts where kind='question' AND created_at >= "
            "last_run, generates URLs, and appends them into segmented sitemaps (50K URLs each "
            "per Google's limit). Output is gzipped XML written to S3, fronted by CDN. A sitemap "
            "index file lists all segments. Updated questions emit URLs into a 'recent' segment "
            "to ensure freshness. Total sitemap size for 25M questions = ~500 segments. The CDN "
            "long-TTL caches stable old segments; only the recent segment changes hourly."
        ),
        "read_heavy_caching": (
            "Layered cache: (1) CDN edge: rendered question page HTML keyed by question_id, TTL "
            "~5–15min, surrogate-key invalidated on edit/accept/score-cross-threshold events. "
            "(2) Redis: rendered fragment cache for the question body, top answers, and top "
            "comments — assembled at the API layer when the CDN misses. (3) Postgres: read replicas "
            "behind a connection pooler; the question-page query reads from one shard with "
            "the (question_id) primary key + (parent_id, score DESC) for answers. View counts are "
            "buffered in Redis and flushed to Postgres in batches every minute. The bulk of "
            "anonymous Google traffic should never reach Postgres."
        ),
        "sharding_strategy": (
            "Sharded by question id (truncated hash → shard). Answers, comments, revisions on a "
            "question all share its shard, so the question-page read is single-shard. Users, tags, "
            "badges, reputation_events live in separate global stores (small, low-write). Votes "
            "are sharded by (user_id) on the votes table (per-user lookup) and by target_id on "
            "vote_counters_shard. Search and sitemap pipelines read CDC streams off all shards "
            "into Kafka and fan-out to Elasticsearch / sitemap workers. Cross-shard reads are rare "
            "(user activity feed) and use read-time scatter-gather with bounded fan-in."
        ),
        "slo_contract": (
            "Question page p99 < 300ms (CDN/Redis hit; ~95% of anonymous traffic). Search p99 < "
            "500ms. Vote write p99 < 250ms (counters write only; rep applied async). Reputation "
            "and badge visibility within ~60s of triggering event. Sitemap freshness within 24h "
            "(hourly job, daily SEO surface). Edit visibility immediate to the editor; cache "
            "invalidation for everyone within 60s."
        ),
    },
    trade_offs=[
        {"option": "Strong vs eventual reputation consistency",
         "for_strong": "User sees rep change instantly on vote; trivial mental model",
         "for_eventual": "Decouples vote write latency from rep recomputation; survives reputation-rule changes via ledger replay",
         "recommendation": "Eventual via reputation_events ledger — vote SLO (250ms) is the hot path; users tolerate seconds of rep delay; replay capability is invaluable."},
        {"option": "Single posts table (questions + answers) vs separate tables",
         "for_single": "Comments and votes target a uniform 'post'; simpler schema",
         "for_separate": "Type-specific columns avoid nullable noise (title only on question)",
         "recommendation": "Single posts table with kind discriminator — uniform vote / comment / revision pipelines outweigh a few nullable columns."},
        {"option": "Render markdown on write vs on read",
         "for_write": "Read path is pure HTML; cheap to cache; no per-request render cost",
         "for_read": "Always-fresh rendering; markdown engine upgrades take effect immediately",
         "recommendation": "Render on write (cached body_html) — read amplification is 1000:1; bulk re-render on engine upgrade is a one-time job."},
        {"option": "Pre-compute privileges vs gate at every write",
         "for_precompute": "Sub-millisecond gate; cached flags struct",
         "for_per_write": "Always reflects the latest reputation",
         "recommendation": "Pre-compute and cache 60s — staleness is harmless; deny still re-checks server-side; brings privilege checks under the SLO budget."},
        {"option": "Fan-out vs read-time merge for tag pages",
         "for_fanout": "Pre-sorted tag feeds, fastest reads",
         "for_merge": "Tag set per post is small (1–5); writes don't thrash a list",
         "recommendation": "Pre-sorted (Redis sorted set per (tag, sort)) — only 5 ZADDs per post; reads dominate writes."},
    ],
    tips=[
        "Lead with read:write ratio — 99:1 dictates every architectural choice (CDN, render-on-write, eventual rep).",
        "Reputation as an event ledger (reputation_events) is the senior signal; users.reputation is a materialised total.",
        "Privileges are reputation thresholds, not roles — keep the threshold table data-driven.",
        "Idempotent voting: prev/new diff inside the upsert; do NOT propose UPDATE post SET ups=ups+1.",
        "Markdown rendered on write to body_html — reads are pure HTML and cache naturally.",
        "Edit history is append-only post_revisions; the posts row is always the current revision.",
        "Badges are event-driven via Kafka with rule plug-ins; awards idempotent on (user, badge, source).",
        "Single posts table with kind discriminator beats Question + Answer split — uniform comment/vote pipelines.",
        "Sharding is by question id so the question page is single-shard.",
    ],
    thought_process=[
        "1. Clarify scope: Q&A hierarchy, voting+rep, privileges, tags, full-text search, edit history, badges, moderation, anti-spam, sitemap.",
        "2. Estimate: 99:1 read:write; 100K/sec peak question reads; ~3M votes/day; 25M+ questions corpus.",
        "3. APIs: ask/answer/comment, vote (idempotent toggle), accept, edit (revision), tag/search, flag, mod actions.",
        "4. Schema: single posts table (kind=question|answer) sharded by question id; post_revisions append-only; votes per-user keyed table + sharded counters.",
        "5. Reputation: ledger of reputation_events consumed off Kafka; users.reputation materialised; rebuildable.",
        "6. Privileges: threshold-based flags struct cached per user (60s).",
        "7. Tags: post_tags join + Redis ZSET per (tag, sort).",
        "8. Search: Elasticsearch indexed via CDC; BM25 + score + recency rank.",
        "9. Edit history: post_revisions with rev_number; render markdown on write to body_html.",
        "10. Badges: Kafka consumer with rule plug-ins; idempotent (user, badge, source).",
        "11. Moderation: flag table + queues; community close/reopen votes (5/3 thresholds); mod_actions audit.",
        "12. Anti-spam: edge rate limits + account-trust + content filter + async ML.",
        "13. Sitemap: hourly job → segmented gzipped XML to S3+CDN.",
        "14. Caching: CDN edge for question pages; Redis fragment cache; Postgres only on miss.",
        "15. SLO: question p99<300ms, search p99<500ms, vote p99<250ms, rep < 60s eventual.",
    ],
    tags=["q-and-a", "voting", "reputation", "search", "moderation", "read-heavy"],
    arch_nodes=[
        {"id": "client", "label": "Web / Crawlers", "type": "client"},
        {"id": "cdn", "label": "CDN", "type": "cache"},
        {"id": "lb", "label": "API Gateway", "type": "lb"},
        {"id": "qsvc", "label": "Question Svc", "type": "server"},
        {"id": "asvc", "label": "Answer Svc", "type": "server"},
        {"id": "csvc", "label": "Comment Svc", "type": "server"},
        {"id": "vsvc", "label": "Vote Svc", "type": "server"},
        {"id": "rep", "label": "Reputation Svc", "type": "service"},
        {"id": "priv", "label": "Privilege Resolver", "type": "service"},
        {"id": "badge", "label": "Badge Svc", "type": "service"},
        {"id": "tag", "label": "Tag Svc", "type": "server"},
        {"id": "search", "label": "Elasticsearch", "type": "database"},
        {"id": "render", "label": "Markdown Renderer", "type": "service"},
        {"id": "rev", "label": "Revision Svc", "type": "server"},
        {"id": "mod", "label": "Moderation Svc", "type": "server"},
        {"id": "spam", "label": "Anti-Spam / ML", "type": "service"},
        {"id": "site", "label": "Sitemap Job", "type": "service"},
        {"id": "kafka", "label": "Kafka", "type": "queue"},
        {"id": "db", "label": "Sharded Postgres", "type": "database"},
        {"id": "shards", "label": "Counter Shards", "type": "database"},
        {"id": "redis", "label": "Redis (cache+RL)", "type": "cache"},
        {"id": "s3", "label": "S3 Sitemaps", "type": "database"},
    ],
    arch_edges=[
        {"source": "client", "target": "cdn"},
        {"source": "cdn", "target": "lb", "label": "miss"},
        {"source": "lb", "target": "spam", "label": "rate-limit / trust"},
        {"source": "spam", "target": "redis"},
        {"source": "lb", "target": "qsvc"},
        {"source": "lb", "target": "asvc"},
        {"source": "lb", "target": "csvc"},
        {"source": "lb", "target": "vsvc"},
        {"source": "lb", "target": "tag"},
        {"source": "lb", "target": "mod"},
        {"source": "qsvc", "target": "render"},
        {"source": "asvc", "target": "render"},
        {"source": "render", "target": "db", "label": "body_html"},
        {"source": "qsvc", "target": "rev", "label": "create revision"},
        {"source": "rev", "target": "db"},
        {"source": "vsvc", "target": "shards", "label": "shard increment"},
        {"source": "vsvc", "target": "db", "label": "user vote row"},
        {"source": "vsvc", "target": "kafka", "label": "vote event"},
        {"source": "qsvc", "target": "kafka", "label": "post events"},
        {"source": "asvc", "target": "kafka", "label": "answer / accept"},
        {"source": "kafka", "target": "rep"},
        {"source": "rep", "target": "db", "label": "rep_events + users.rep"},
        {"source": "kafka", "target": "badge"},
        {"source": "badge", "target": "db", "label": "user_badges"},
        {"source": "kafka", "target": "search", "label": "CDC index"},
        {"source": "kafka", "target": "site", "label": "new question stream"},
        {"source": "site", "target": "s3", "label": "sitemap-N.xml.gz"},
        {"source": "s3", "target": "cdn", "label": "serve"},
        {"source": "lb", "target": "priv"},
        {"source": "priv", "target": "redis", "label": "flags cache"},
        {"source": "qsvc", "target": "redis", "label": "fragment cache"},
        {"source": "redis", "target": "db", "label": "miss"},
        {"source": "tag", "target": "redis", "label": "tag ZSET"},
        {"source": "kafka", "target": "spam", "label": "async ML"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant U as User\n"
        "  participant API\n"
        "  participant V as Vote Svc\n"
        "  participant SH as Counter Shards\n"
        "  participant K as Kafka\n"
        "  participant R as Reputation Svc\n"
        "  participant B as Badge Svc\n"
        "  participant DB as Postgres\n"
        "  U->>API: POST /posts/42/vote {dir:1}\n"
        "  API->>V: idempotent vote\n"
        "  V->>V: upsert votes(prev=0,new=1) -> delta=+1 up\n"
        "  V->>SH: INCR shard[hash(user)]\n"
        "  V->>K: emit vote.up event\n"
        "  V-->>U: 200\n"
        "  K->>R: vote.up consumed\n"
        "  R->>DB: append rep_event(+10)\n"
        "  R->>DB: UPDATE users.reputation\n"
        "  K->>B: vote.up consumed\n"
        "  B->>B: rule: score crosses 10?\n"
        "  B->>DB: insert user_badges (idempotent)"
    ),
    er_diagram=(
        "erDiagram\n"
        "  USER ||--o{ POST : authors\n"
        "  USER ||--o{ COMMENT : authors\n"
        "  USER ||--o{ VOTE : casts\n"
        "  USER ||--o{ REPUTATION_EVENT : earns\n"
        "  USER ||--o{ USER_BADGE : has\n"
        "  POST ||--o{ POST : answers\n"
        "  POST ||--o{ COMMENT : has\n"
        "  POST ||--o{ POST_REVISION : versioned_by\n"
        "  POST ||--o{ POST_TAG : tagged\n"
        "  TAG ||--o{ POST_TAG : on\n"
        "  POST ||--o{ VOTE : receives\n"
        "  POST ||--o{ FLAG : flagged\n"
        "  POST { bigint id PK\n string kind\n bigint parent_id\n bigint user_id\n string title\n text body_md\n int score\n bigint accepted_answer_id }\n"
        "  POST_REVISION { bigint id PK\n bigint post_id\n int rev_number\n text body_md\n bigint created_at }\n"
        "  VOTE { bigint user_id\n string target_kind\n bigint target_id\n smallint dir }\n"
        "  REPUTATION_EVENT { bigint id PK\n bigint user_id\n string kind\n int delta\n bigint source_id }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B[99:1 read:write — cache-first]\n"
        "  B --> C[CDN edge for question pages]\n"
        "  C --> D[Render markdown on write to body_html]\n"
        "  D --> E{Voting?}\n"
        "  E -->|Naive UPDATE| F[Row contention on viral question]\n"
        "  E -->|Sharded counters| G[Race-free; emit Kafka event]\n"
        "  G --> H[Reputation Svc: append rep_events]\n"
        "  H --> I[Privilege flags cached 60s]\n"
        "  G --> J[Badge Svc: rule plug-ins, idempotent]\n"
        "  D --> K[Edit -> append post_revisions]\n"
        "  B --> L[Search: Elasticsearch via CDC]\n"
        "  B --> M[Sitemap: hourly batch -> S3+CDN]\n"
        "  B --> N[Moderation queues + community close votes]"
    ),
    tradeoff_title="Reputation: derived ledger vs authoritative counter",
    tradeoff_options=[
        {"label": "Authoritative counter (UPDATE users SET rep = rep + delta)",
         "description": "Each vote synchronously updates the user's reputation column.",
         "pros": ["Always-current rep; trivial UX", "One write"],
         "cons": ["Adds DB write to vote critical path",
                 "No audit trail for rep changes",
                 "Rule changes (e.g. new bonuses) cannot be retro-applied",
                 "Rebuilding rep on bug requires custom script"]},
        {"label": "Append-only reputation_events ledger (materialised total)",
         "description": "Vote events emit rep events; ledger is canonical, users.reputation is derived.",
         "pros": ["Full audit trail per user",
                  "Replay rebuilds rep from scratch — survives bugs and rule changes",
                  "Decouples vote write latency from rep computation (async)",
                  "Idempotent via (source_kind, source_id, kind) unique key"],
         "cons": ["Eventual consistency (~seconds delay)",
                 "Two-stage system (events table + materialised total) to maintain"]},
        {"label": "Pure derived (compute rep on read)",
         "description": "No materialised total — sum reputation_events on profile load.",
         "pros": ["Single source of truth", "Zero materialisation drift"],
         "cons": ["Profile load slow as user history grows",
                 "Privilege checks on every write require the same sum — too expensive",
                 "Caching restores complexity removed"]},
    ],
    tradeoff_rec="Append-only ledger + materialised total. Ledger is the audit and rebuild story; the column on users is the read-fast cache. Eventual consistency (seconds) matches user expectation.",
    senior_topics=[
        _topic("voting-and-reputation",
               "Idempotent Voting + Event-Sourced Reputation",
               "The vote write is the most-touched mutation on the platform. It must be idempotent, "
               "race-free under contention, and the source of reputation deltas — without ballooning "
               "the write critical path.",
               [
                   ("Idempotent vote algebra",
                    "Vote rows are keyed by (user_id, target_kind, target_id) with dir ∈ {-1, 0, 1}. "
                    "On POST, the service reads the prior dir, computes the delta (+1 up, -1 up + 1 "
                    "down, etc.), and upserts the new dir in one transaction. Re-pressing the same "
                    "direction yields delta=0 — a no-op write. Toggling between up and down is one "
                    "transaction with a two-component delta."),
                   ("Sharded counters",
                    "vote_counters_shard(target_id, shard, ups, downs). shard = hash(user_id) % N "
                    "(N=32). Per-user-stable shard: re-pressing votes on the same row remains "
                    "idempotent. Spreads viral-question contention across 32 rows."),
                   ("Aggregator → posts.score",
                    "An aggregator periodically (every ~1s for hot, slower for cold) sums shards "
                    "and writes the canonical posts.ups/downs/score column. Read paths read the "
                    "materialised column — counters are seconds-stale by design."),
                   ("Reputation as derived events",
                    "The vote upsert emits a Kafka event {user_id_target, dir_old, dir_new, "
                    "post_kind, post_id}. Reputation Service consumes and writes a "
                    "reputation_events row for each affected user (author of post, possibly voter "
                    "if rule applies). Idempotency via PRIMARY KEY (user_id, source_kind, source_id, "
                    "kind) — duplicate consumption is a no-op."),
                   ("Materialised users.reputation",
                    "A simple UPDATE users SET reputation = reputation + delta WHERE id = ? after "
                    "the rep event is written. Users see rep updates within seconds of voting; "
                    "the ledger remains canonical."),
                   ("Replay / repair",
                    "Bug shipped that mis-credited rep? Drop users.reputation, re-aggregate from "
                    "reputation_events with corrected rules, write back. The events ledger is "
                    "immutable; correction is a sweep, not a forensic disaster."),
                   ("Why not Redis-only counters",
                    "Redis INCR is fast but durability across failover is fragile and there's no "
                    "audit. Postgres-resident shards + ledger satisfy SLO and durability."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant U as User\n"
                   "  participant V as Vote Svc\n"
                   "  participant DB as Postgres\n"
                   "  participant SH as Shard table\n"
                   "  participant K as Kafka\n"
                   "  participant R as Reputation Svc\n"
                   "  U->>V: POST /vote dir=1\n"
                   "  V->>DB: SELECT prior dir\n"
                   "  V->>DB: UPSERT votes (prev=0,new=1)\n"
                   "  V->>SH: INCR shard\n"
                   "  V->>K: emit vote event\n"
                   "  V-->>U: 200\n"
                   "  K->>R: consume\n"
                   "  R->>DB: INSERT rep_event(+10) idempotent\n"
                   "  R->>DB: UPDATE users.reputation"
               )),
        _topic("privileges-thresholds",
               "Privileges as Reputation Thresholds",
               "Stack Overflow models permissions as numeric thresholds rather than roles. The "
               "design choice keeps the system data-driven (rules are configuration, not code) and "
               "the user mental model self-evident: earn rep, unlock capabilities.",
               [
                   ("Threshold table",
                    "privileges(name, min_reputation): comment=50, vote_up=15, vote_down=125, "
                    "create_chat_room=20, edit_others_suggested=2000, close=3000, "
                    "edit_directly=2000, trusted_user=20000. Easily queried; new privileges added "
                    "as data."),
                   ("Resolver flags",
                    "Privilege Resolver reads a user's reputation, joins against the threshold "
                    "table, and produces a flags struct: {can_comment: true, can_vote_up: true, "
                    "can_vote_down: false, can_close: false, ...}. Cached in Redis per user with "
                    "60s TTL; invalidated on rep events crossing thresholds."),
                   ("Gate at write time",
                    "Every write API checks the relevant flag first (cheap Redis read). On miss, "
                    "compute and cache. Server-side at the service layer re-checks against the "
                    "threshold table — defense in depth."),
                   ("Why not RBAC roles",
                    "Roles are coarse and require admin assignment. Threshold gates scale to all "
                    "users, are intrinsic to participation, and naturally produce a graded "
                    "permission structure (more rep = more trust)."),
                   ("Cross-threshold events",
                    "When a rep event causes the user's rep to cross a threshold, an event is "
                    "published — used to invalidate the cached flags struct and to fire 'privilege "
                    "earned' notifications. Crossing back down (e.g. heavy downvotes) revokes."),
                   ("Mod override",
                    "Moderators have all privileges via the is_moderator flag — a separate boolean "
                    "short-circuits the threshold check. Suspensions set is_suspended which negates "
                    "all write privileges regardless of rep."),
               ],
               diagram=(
                   "graph TD\n"
                   "  V[Vote arrives] --> R[Rep delta applied]\n"
                   "  R --> C{Crossed threshold?}\n"
                   "  C -->|Yes| INV[Invalidate flags cache]\n"
                   "  C -->|No| OK[Keep cache]\n"
                   "  W[Write request] --> F{Flags cache hit?}\n"
                   "  F -->|Hit| G[Gate at edge]\n"
                   "  F -->|Miss| RC[Resolve from rep + thresholds]\n"
                   "  RC --> S[Cache 60s]"
               )),
        _topic("cache-heavy-architecture",
               "Cache-Heavy Architecture for 99:1 Read:Write",
               "Most traffic is anonymous viewers landing from Google. The architecture is shaped "
               "so that the median request never reaches Postgres — the database services writes "
               "and the long tail of cache misses, not the firehose.",
               [
                   ("Layer 1: CDN edge",
                    "Rendered question page HTML cached at the CDN keyed by question_id. TTL "
                    "5–15 min. Surrogate keys (question:42, user:7) tag responses; edits/votes/"
                    "accepts emit purges via the CDN's tag-purge API. ~95% of anonymous Google "
                    "traffic terminates here."),
                   ("Layer 2: Redis fragment cache",
                    "On CDN miss, the API renders the page from cached fragments: {question_body, "
                    "answers_block, comments_block, sidebar_tags}. Each fragment is independently "
                    "cached and invalidated on the relevant write. Composition is sub-10ms."),
                   ("Layer 3: Postgres read replicas",
                    "On Redis miss, a read replica services the query. Question-page query is one "
                    "shard (single question + its answers + comments + revisions). Connection "
                    "pooler (PgBouncer) absorbs spikes."),
                   ("Render on write",
                    "Markdown → HTML happens on POST/PUT and the result is stored in posts.body_html. "
                    "Reads never re-render. On engine upgrade, a one-shot job re-renders all rows."),
                   ("View counter buffering",
                    "Naive UPDATE posts SET view_count = view_count + 1 on every page view would "
                    "destroy the database. Views increment a Redis hash; a flusher writes batches "
                    "(every minute) to Postgres. View count is approximate by design."),
                   ("Cache invalidation surfaces",
                    "Edits, accepts, score-crossing-threshold, and tag changes invalidate. Vote "
                    "events do NOT invalidate the rendered page — score is a small fragment, "
                    "updated lazily; the page is correct enough for SEO and casual viewers."),
                   ("Anonymous vs logged-in",
                    "Anonymous get the cached page. Logged-in users have personalised bits (your "
                    "vote arrows, your bookmark state) that defeat full-page CDN caching — "
                    "personalisation is fetched as a separate small JSON and merged client-side, "
                    "preserving CDN cacheability of the main HTML."),
               ],
               diagram=(
                   "graph LR\n"
                   "  C[Anonymous viewer] --> CDN\n"
                   "  CDN -->|95% hit| C\n"
                   "  CDN -->|miss| API\n"
                   "  API --> R[Redis fragments]\n"
                   "  R -->|hit| API\n"
                   "  R -->|miss| PG[Postgres replica]\n"
                   "  PG --> R\n"
                   "  W[Editor saves edit] --> APIw[API write]\n"
                   "  APIw --> PGm[Postgres primary]\n"
                   "  APIw --> INV[Purge surrogate-keys]\n"
                   "  INV --> CDN\n"
                   "  INV --> R"
               )),
        _topic("badges-event-driven",
               "Event-Driven Badge Service with Rule Plug-ins",
               "Badges are gamification atoms — hundreds exist (e.g. Teacher, Nice Answer, Famous "
               "Question, Stellar Question). Coupling each rule to its trigger code would explode "
               "complexity. A consumer over the platform's event stream with declarative rules "
               "scales cleanly.",
               [
                   ("Event topics",
                    "Producers (Vote Svc, Answer Svc, Question Svc) emit events to Kafka topics: "
                    "vote.up, vote.down, answer.created, answer.accepted, question.score_crossed, "
                    "answer.score_crossed. Topic schema is a stable contract; payload contains "
                    "user_id (and post id) plus context."),
                   ("Rule plug-in shape",
                    "Each rule is a function (event_context) -> Optional[(user_id, badge_id, "
                    "source_id)]. Rule registry: declarative YAML maps event topic → rule list. "
                    "Adding a badge ships as data + a small rule (sometimes pure SQL: 'first answer "
                    "with score ≥ 1' = SELECT 1 WHERE NOT EXISTS prior award AND new score)."),
                   ("Idempotent awards",
                    "user_badges PRIMARY KEY (user_id, badge_id, source_id). Re-consumed events "
                    "produce the same insert key — duplicate is a no-op. source_id is the post or "
                    "vote that triggered the badge so per-source uniqueness is enforced."),
                   ("Daily/lifetime distinction",
                    "Some badges are one-time (Teacher) — uniqueness on (user_id, badge_id) with "
                    "source_id=0. Others repeat per-source (Nice Answer per answer) — full key. "
                    "The schema accommodates both via the source_id sentinel."),
                   ("Backfill on rule change",
                    "Adding a new badge with retroactive eligibility: a one-shot job replays the "
                    "relevant slice of historical events (e.g. last year's vote.up) through the "
                    "new rule. Ledger replayability makes badge launches operationally cheap."),
                   ("Notification fan-out",
                    "Badge insert emits a notification event so the UI can show 'New Badge!' on "
                    "next page load. Notification delivery is best-effort; the badge is real "
                    "regardless."),
                   ("Why not synchronous in vote path",
                    "Putting badge logic on the vote critical path (250ms SLO) is fragile — a "
                    "slow rule blocks the vote. Async over Kafka decouples; bad rule slows badges "
                    "but never voting."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant V as Vote Svc\n"
                   "  participant K as Kafka\n"
                   "  participant B as Badge Svc\n"
                   "  participant DB as Postgres\n"
                   "  V->>K: vote.up {answer=42, author=7}\n"
                   "  K->>B: consume\n"
                   "  B->>DB: SELECT score FROM posts WHERE id=42\n"
                   "  B->>B: rule 'Nice Answer' (score>=10)?\n"
                   "  B->>DB: INSERT user_badges (7, NiceAnswer, 42)\n"
                   "  Note over DB: PK conflict on replay = no-op\n"
                   "  B->>K: emit notification.badge"
               )),
        _topic("search-elasticsearch",
               "Full-Text Search on Elasticsearch",
               "Search is the second-largest read surface after the question page. Postgres "
               "full-text isn't sufficient at corpus scale (25M+ questions, multi-field, ranking "
               "needs). Elasticsearch is the canonical answer.",
               [
                   ("Indexing pipeline",
                    "post.created / post.edited / post.tagged events flow off Kafka into an "
                    "indexer that upserts ES documents. The doc per question contains title, "
                    "body_md, all answer bodies (concatenated as a child field), tags, score, "
                    "accepted flag, view_count, created_at, last_activity_at."),
                   ("Ranking function",
                    "function_score: BM25 baseline on text fields (title boost ~5×, body 1×, "
                    "answer_body 0.5×) + log(1 + score) × α (vote weighting) + recency decay "
                    "(gauss on last_activity_at). The accepted flag adds a small constant. Tags "
                    "match adds a hard filter when query specifies a tag."),
                   ("Tag search vs free text",
                    "[python] in the query is parsed as a tag filter. Free-text combines with the "
                    "tag filter (AND). Pure tag browse hits the tag page (Postgres + Redis) "
                    "instead of ES — ES is for relevance ranking, not flat lists."),
                   ("Sharding the index",
                    "ES sharded by question id; replicas for read availability. Index size grows "
                    "linearly; rollover by year keeps shards small for query latency."),
                   ("Suggest / autocomplete",
                    "completion suggester on title surfaces 'Did you mean...' and search-as-you-type. "
                    "Common-term and stop-word handling tuned per language."),
                   ("Reindex strategy",
                    "Schema changes use blue/green: build a new index, flip an alias atomically. "
                    "The Kafka log allows reindexing from an offset cheaply."),
                   ("Why blend score+recency, not pure BM25",
                    "Stack Overflow's value is canonical answers, not freshest. A 2014 question "
                    "with 5K upvotes about Python generators should outrank a 2024 stub with the "
                    "same query terms. Score boost recovers that. But recency still matters for "
                    "evolving topics — the gauss decay keeps fresh content alive."),
               ],
               diagram=(
                   "graph LR\n"
                   "  E[post events] --> K[Kafka]\n"
                   "  K --> IDX[Indexer]\n"
                   "  IDX --> ES[Elasticsearch]\n"
                   "  C[Client] --> API\n"
                   "  API --> ES\n"
                   "  ES --> API\n"
                   "  API --> C\n"
                   "  ES -. blue/green reindex .-> ES2[ES new index]"
               )),
        _topic("moderation-queues-flags",
               "Moderation: Flag Queues, Community Close Votes, and Mod Actions",
               "With 25K new posts per day, mod throughput depends on community-driven workflows "
               "and prioritisation. The platform supports flagging, low-quality detection, and "
               "voting-based closes/reopens — moderators are the escalation tier.",
               [
                   ("Flag types",
                    "Flag reasons: spam, offensive, low-quality, duplicate, off-topic, needs-edit. "
                    "flags(post_id, user_id, reason, status, created_at). Per-user-per-post unique "
                    "to prevent flag stuffing. Trust-weighted: low-rep flags need 3 to act; "
                    "high-rep (≥1000) acts on 1."),
                   ("Mod queue prioritisation",
                    "Queue items sorted by (open_flag_count DESC, age ASC). Backlog dashboard "
                    "exposes per-queue p50/p95 dwell time. Auto-escalate aged items."),
                   ("Community close votes",
                    "Users with ≥3000 rep can cast close votes with a reason. close_votes(post_id, "
                    "user_id, reason). 5 close-votes auto-close the post (is_closed = true). "
                    "Reopen needs 3 reopen votes. Question stays visible but new answers blocked."),
                   ("Low-quality posts",
                    "A heuristic + ML classifier scores submissions on length, formatting, code "
                    "block presence, similarity to known dupes. Below threshold → auto-flag for "
                    "review queue; egregious (e.g. one-line 'thanks') auto-deleted with appeal."),
                   ("Mod actions audit",
                    "Every mod action (close, reopen, delete, undelete, edit, ban) writes a "
                    "mod_actions row. Immutable; reversals are new rows. Public mod log is the "
                    "transparency surface."),
                   ("Suspensions",
                    "users.is_suspended is a boolean with an expires_at. Write APIs reject for "
                    "suspended users. Reputation history is preserved; the user simply can't "
                    "participate."),
                   ("Why community-driven",
                    "Centralised moderation doesn't scale to 25M questions. The reputation gate "
                    "+ vote thresholds harness the community as a graduated moderation force, "
                    "with paid moderators as escalation."),
               ]),
        _topic("anti-spam-and-sitemaps",
               "Anti-Spam Defence + Sitemap Pipeline",
               "Two operational concerns that don't share a thesis but both shape the production "
               "shape of the system: keeping bad actors out and getting good content discoverable.",
               [
                   ("Anti-spam: edge rate limits",
                    "Token-bucket per (user_id, action) and per IP in Redis. Ask: 1/min, answer: "
                    "5/min, comment: 10/min, vote: 30/min. Bursts allowed via bucket capacity; "
                    "sustained abuse drains the bucket and rejects."),
                   ("Anti-spam: account-trust gate",
                    "Brand-new accounts (rep < 10) get half rate limits and writes auto-flagged "
                    "for review. CAPTCHA on signup; phone-number reputation; email-domain "
                    "blocklist for known disposable providers."),
                   ("Anti-spam: content filter",
                    "Synchronous regex + URL blocklist runs at write time (<50ms). Catches the "
                    "obvious link-spam wave and known crypto/casino domains. False positives "
                    "land in moderator queue."),
                   ("Anti-spam: async ML",
                    "Kafka events feed a classifier with features {writer age, link density, "
                    "vote velocity, content embedding, IP reputation}. Verdicts: clean | review "
                    "| shadow. Shadow = post visible to author, hidden from listings. Review-queue "
                    "dwell time bounded; auto-approve after 24h with no flag."),
                   ("Sitemap: why it matters",
                    "Stack Overflow's value depends on Google indexing fresh questions. A new "
                    "question must be in a sitemap and crawlable within 24h or it dies in obscurity."),
                   ("Sitemap: pipeline",
                    "Hourly job reads question stream off Kafka (or a queryable created_at >= "
                    "last_run on Postgres for catch-up). Generates URLs, segments into 50K-URL "
                    "files (Google's per-sitemap cap), gzips, writes to S3. CDN serves. A sitemap "
                    "index file lists all segments with lastmod timestamps."),
                   ("Sitemap: freshness",
                    "Recent segment is overwritten every hour. Old segments rarely change "
                    "(historical questions). Edits update the question's lastmod in its segment "
                    "via a lighter delta job. Total sitemap size at 25M questions = ~500 segments."),
                   ("Sitemap: SEO discipline",
                    "Robots.txt allows crawling; canonical URLs prevent duplicate-content "
                    "penalties; structured data (Schema.org Q&A) on rendered pages improves "
                    "rich-snippet eligibility."),
               ],
               diagram=(
                   "graph TD\n"
                   "  W[Question created] --> K[Kafka]\n"
                   "  K --> S[Sitemap Job]\n"
                   "  S --> Seg[Segment N gzipped XML]\n"
                   "  Seg --> S3[S3]\n"
                   "  S3 --> CDN\n"
                   "  G[Googlebot] --> CDN\n"
                   "  CDN --> G"
               )),
    ],
)
