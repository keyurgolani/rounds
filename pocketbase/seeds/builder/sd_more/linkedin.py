"""LinkedIn system design question. Loaded automatically via
`sd_questions._load_more` because this module exposes `PAYLOAD`."""
from __future__ import annotations

from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design LinkedIn",
    "Hard",
    "Design LinkedIn: a professional network with bidirectional (mutual-consent) connections, a 1st/2nd/"
    "3rd-degree connection graph, ranked home feed, People You May Know recommendations, multi-entity "
    "search (people, jobs, companies), 1:1 + group messaging, notifications, job postings with search "
    "and applications, endorsements/skills, and premium subscription. Distinguish from generic social "
    "networks: connections require mutual consent (handshake workflow), and the graph itself is the "
    "primary product surface — degree-of-separation gates visibility, search ranking, and PYMK.",
    hints=[
        "Connections are bidirectional with mutual consent — not a unilateral follow. Model the request "
        "workflow (pending/accepted/declined/withdrawn) as a first-class state machine.",
        "Degree-of-separation (1st/2nd/3rd+) is THE primary access-control and ranking dimension. It "
        "appears on every profile view, every search result, every PYMK card.",
        "2nd-degree intersection (mutual connections) is a hot read on the critical path. Pre-compute "
        "and cache; never compute online for non-trivial users.",
        "PYMK is graph traversal (2-hop friend-of-friend candidate generation) + ML re-ranking on "
        "features like mutual count, company/school overlap, co-view, profile-edit recency.",
        "Feed is fan-out-on-write for the long tail + read-time pull for hyper-connected influencers — "
        "same hybrid pattern as Instagram/Twitter, applied to a connection graph rather than a follow graph.",
        "Search spans heterogeneous entities (people, jobs, companies, posts). Elasticsearch with per-"
        "entity indexes and a federated query layer; ranking is degree-aware for people search.",
        "Jobs is a separate vertical with its own search, recommender, and application workflow — but "
        "shares the connection graph for 'who do I know at this company' insights.",
    ],
    constraints=[
        "1B+ registered members, ~300M MAU, ~150M DAU",
        "Average ~500 connections/member; power users have the 30K connection cap",
        "10B+ connection edges in the graph; ~1B job-related edges (applied/saved/viewed)",
        "Feed open p99 < 1s; profile open p99 < 500ms; search p99 < 300ms",
        "PYMK refresh: candidates within 24h of new connection signal; ranking on read",
        "Jobs corpus: ~30M active postings; search must reflect new postings within minutes",
        "Global multi-region; messages and notifications near-real-time across regions",
        "Connection requests are mutual-consent — a connection edge appears only after acceptance",
    ],
    req_func=[
        "Send / accept / decline / withdraw connection requests (bidirectional mutual consent)",
        "View profile with degree-of-separation badge and mutual-connection count",
        "Compute 1st / 2nd / 3rd-degree relationship between any two members",
        "People You May Know — ranked candidate list refreshed daily",
        "Ranked home feed of posts/articles/reshares from connections and followed entities",
        "Multi-entity search (people, jobs, companies, posts, groups) with autocomplete",
        "Job postings: company posts a job; member searches/applies; recruiter sees applicants",
        "1:1 + group messaging (defers to the dedicated chat design)",
        "Notifications: bell icon for connection requests, post engagement, job recommendations",
        "Endorsements + skills on profile; premium subscription tier with InMail and analytics",
    ],
    req_nonfunc=[
        "Read-skewed; profile + feed reads dominate by 100:1 over writes",
        "Eventual consistency on feed inclusion (post visible within seconds), strong on connection state",
        "99.95% read availability; write availability can degrade gracefully",
        "Degree-of-separation calculation < 50ms p99 — appears on every profile/search hit",
        "Search index freshness: jobs < 5 min; profile edits < 1 hour acceptable",
        "Spam + fraud-resistant: connection requests, job postings, and messages all gated",
        "Premium features (InMail, who-viewed-your-profile) are entitlement-checked at every call",
    ],
    estimation={
        "members": "1B registered, 300M MAU, 150M DAU",
        "avg_connections": "~500 (mode); power users hit 30K cap",
        "connection_edges": "~10B (each accepted handshake = 2 directed rows or 1 undirected + index)",
        "connection_requests_per_day": "~50M sent, ~20M accepted",
        "feed_opens_per_day": "~1.5B",
        "qps_feed_read": "~20K/sec steady, ~120K/sec peak (US business hours)",
        "qps_search": "~30K/sec steady",
        "active_job_postings": "~30M; ~10M new applications/day",
        "messages_per_day": "~500M (handed off to chat tier)",
        "pymk_candidates_per_user": "Top 50 surfaced; 500–2000 generated",
        "graph_storage": "~10B edges × ~50B = ~500GB hot graph state, with replicas + indexes ~5TB",
    },
    endpoints=[
        {"method": "POST", "path": "/connections/request",
         "description": "Send a connection request to another member",
         "body": "{to_member_id, note?, source?}"},
        {"method": "POST", "path": "/connections/{request_id}/accept",
         "description": "Accept a pending connection request — creates the bidirectional edge"},
        {"method": "POST", "path": "/connections/{request_id}/decline",
         "description": "Decline (soft reject) — request transitions to declined state"},
        {"method": "DELETE", "path": "/connections/{request_id}",
         "description": "Withdraw an outgoing pending request, or remove an existing connection"},
        {"method": "GET", "path": "/connections/degree/{other_id}",
         "description": "Return 1/2/3/3+ degree of separation and mutual-connection count"},
        {"method": "GET", "path": "/pymk",
         "description": "People You May Know — ranked candidate list",
         "body": "?limit=20&cursor=opaque"},
        {"method": "GET", "path": "/feed",
         "description": "Ranked home feed",
         "body": "?cursor=opaque&limit=20"},
        {"method": "POST", "path": "/posts",
         "description": "Create a post (text/article/share)",
         "body": "{kind, body, media?, mentions?}"},
        {"method": "GET", "path": "/search",
         "description": "Federated search across entities",
         "body": "?q=<query>&kind=people|jobs|companies|posts&filters={...}"},
        {"method": "POST", "path": "/jobs",
         "description": "Recruiter posts a job",
         "body": "{company_id, title, description, location, skills, comp_range}"},
        {"method": "POST", "path": "/jobs/{job_id}/apply",
         "description": "Member applies to a job",
         "body": "{resume_id, cover_note?}"},
        {"method": "GET", "path": "/jobs/recommendations",
         "description": "Ranked job recommendations for the member"},
        {"method": "POST", "path": "/profile/{member_id}/endorsements",
         "description": "Endorse a skill on a 1st-degree connection's profile",
         "body": "{skill}"},
        {"method": "GET", "path": "/notifications",
         "description": "Bell-icon feed (connection requests, engagement, jobs)"},
        {"method": "POST", "path": "/premium/subscribe",
         "description": "Subscribe to premium tier",
         "body": "{plan, payment_method_id}"},
    ],
    tables=[
        {"name": "members",
         "columns": ["id BIGINT PK", "handle VARCHAR(64) UNIQUE", "name VARCHAR",
                     "headline VARCHAR(220)", "current_company_id BIGINT", "location VARCHAR",
                     "is_premium BOOL", "connection_count INT", "created_at BIGINT"]},
        {"name": "connections",
         "columns": ["member_a BIGINT", "member_b BIGINT", "created_at BIGINT",
                     "PRIMARY KEY (member_a, member_b)",
                     "// stored undirected: always member_a < member_b; reverse index for adjacency lookup"]},
        {"name": "connection_requests",
         "columns": ["id BIGINT PK", "from_id BIGINT", "to_id BIGINT", "state VARCHAR(16)",
                     "note TEXT", "source VARCHAR(32)", "created_at BIGINT", "updated_at BIGINT",
                     "// state in {pending, accepted, declined, withdrawn, expired}"]},
        {"name": "adjacency_index",
         "columns": ["member_id BIGINT", "neighbor_id BIGINT", "created_at BIGINT",
                     "PRIMARY KEY (member_id, neighbor_id)",
                     "// directed view of connections — two rows per edge for cheap neighbour lookup"]},
        {"name": "posts",
         "columns": ["id BIGINT PK", "author_id BIGINT", "kind VARCHAR(16)", "body TEXT",
                     "media_id VARCHAR(64)", "created_at BIGINT", "engagement_count INT"]},
        {"name": "user_feed",
         "columns": ["member_id BIGINT", "post_id BIGINT", "score FLOAT", "inserted_at BIGINT",
                     "PRIMARY KEY (member_id, inserted_at, post_id)"]},
        {"name": "pymk_candidates",
         "columns": ["member_id BIGINT", "candidate_id BIGINT", "mutual_count INT",
                     "features JSONB", "score FLOAT", "generated_at BIGINT",
                     "PRIMARY KEY (member_id, candidate_id)"]},
        {"name": "companies",
         "columns": ["id BIGINT PK", "name VARCHAR", "domain VARCHAR", "size_bucket VARCHAR(16)",
                     "industry VARCHAR", "verified BOOL"]},
        {"name": "jobs",
         "columns": ["id BIGINT PK", "company_id BIGINT", "title VARCHAR", "description TEXT",
                     "location VARCHAR", "skills JSONB", "comp_min INT", "comp_max INT",
                     "posted_at BIGINT", "expires_at BIGINT", "state VARCHAR(16)"]},
        {"name": "job_applications",
         "columns": ["id BIGINT PK", "job_id BIGINT", "member_id BIGINT", "resume_id VARCHAR",
                     "cover_note TEXT", "state VARCHAR(16)", "applied_at BIGINT"]},
        {"name": "skills",
         "columns": ["id BIGINT PK", "name VARCHAR UNIQUE", "canonical_id BIGINT"]},
        {"name": "member_skills",
         "columns": ["member_id BIGINT", "skill_id BIGINT", "endorsement_count INT",
                     "PRIMARY KEY (member_id, skill_id)"]},
        {"name": "endorsements",
         "columns": ["endorser_id BIGINT", "endorsee_id BIGINT", "skill_id BIGINT",
                     "created_at BIGINT", "PRIMARY KEY (endorser_id, endorsee_id, skill_id)"]},
        {"name": "subscriptions",
         "columns": ["member_id BIGINT PK", "plan VARCHAR(16)", "status VARCHAR(16)",
                     "renews_at BIGINT", "stripe_customer_id VARCHAR"]},
        {"name": "notifications",
         "columns": ["id BIGINT PK", "member_id BIGINT", "kind VARCHAR(32)",
                     "actor_id BIGINT", "object_id BIGINT", "created_at BIGINT", "read BOOL"]},
    ],
    indexes=[
        "(member_a, member_b) on connections — undirected canonical edge",
        "(member_id, neighbor_id) on adjacency_index — neighbour scan for graph traversal",
        "(to_id, state, created_at DESC) on connection_requests — incoming-requests inbox",
        "(from_id, state) on connection_requests — outgoing-requests view",
        "(member_id, inserted_at DESC) on user_feed — feed read",
        "(member_id, score DESC) on pymk_candidates — PYMK serve",
        "GIN(skills) on jobs — match by skill",
        "(company_id, state) on jobs — company recruiter view",
        "(job_id, applied_at DESC) on job_applications — applicant pipeline",
        "(endorsee_id, skill_id) on endorsements — skill endorsements aggregate",
        "(member_id, created_at DESC, read) on notifications",
    ],
    hld_desc=(
        "Graph-centric architecture. The Connection Graph Service (a sharded property graph backed by "
        "Espresso/distributed KV with adjacency-list partitioning, similar in shape to LinkedIn's "
        "production stack — Neo4j is the open-source mental model) is the platform's core dependency: "
        "every profile view, every search ranking, every PYMK call queries it for degree-of-separation "
        "and mutual-connection intersections. Connection lifecycle runs through a state-machine service "
        "(Connection Service) that owns the request workflow and emits domain events on accept/decline. "
        "Feed is a hybrid fan-out (push for normal connections, pull-merge for 30K-cap influencers and "
        "followed companies). PYMK runs as a daily Spark/Flink job: 2-hop traversal for candidate "
        "generation, then a feature-rich ML re-ranker. Search is per-entity Elasticsearch indexes behind "
        "a federated query gateway, with degree-of-separation injected as a ranking signal. Jobs is a "
        "first-class vertical with its own ES index, recommender, and application workflow. Messaging "
        "and presence defer to the dedicated chat design. Premium entitlements live in a Subscription "
        "service consulted at gateway and feature-edge."
    ),
    hld_components=[
        {"name": "Web / Mobile Clients", "role": "Render feed, profile, search, jobs, messaging"},
        {"name": "API Gateway", "role": "Auth, rate-limit, premium entitlement, region-route"},
        {"name": "Connection Service", "role": "Request state machine; mutual-consent workflow"},
        {"name": "Connection Graph Service", "role": "Sharded property graph: adjacency, degree, intersection"},
        {"name": "Profile Service", "role": "Member profile read/write; cached aggressively"},
        {"name": "Feed Service", "role": "Hybrid fan-out reader; ranked merge"},
        {"name": "Fan-out Worker", "role": "Push posts into connection feeds (long tail)"},
        {"name": "PYMK Service", "role": "Serve daily-generated candidates; feature lookup at ranking"},
        {"name": "PYMK Pipeline (Spark/Flink)", "role": "2-hop candidate generation + ML re-ranker"},
        {"name": "Search Federation", "role": "Multi-entity ES query orchestrator with degree-aware ranking"},
        {"name": "People Search Index (ES)", "role": "Members + skills + headline; degree-aware re-rank"},
        {"name": "Jobs Service", "role": "Posting CRUD, application workflow, recommender"},
        {"name": "Jobs Search Index (ES)", "role": "Active jobs corpus; freshness < 5 min"},
        {"name": "Companies Service", "role": "Company pages, verified domains, recruiter accounts"},
        {"name": "Endorsements Service", "role": "Skill endorsements (1st-degree only)"},
        {"name": "Notification Service", "role": "Bell-icon inbox + push (APNs/FCM/email)"},
        {"name": "Subscription Service", "role": "Premium plan, billing, entitlement check"},
        {"name": "Messaging Tier", "role": "Defers to chat design — WebSocket gateway + Cassandra"},
        {"name": "Kafka", "role": "Domain events: connection.accepted, post.created, job.posted"},
        {"name": "Redis", "role": "Hot caches: profile, adjacency, degree, mutual-count"},
        {"name": "Object Store + CDN", "role": "Profile photos, post media, resume PDFs"},
    ],
    detailed_design={
        "connection_workflow": (
            "Connection requests are a state machine, not a flag. States: pending → "
            "{accepted, declined, withdrawn, expired (after 6 months)}. Sender writes a "
            "connection_requests row (state=pending) and a notification fires to the recipient. On "
            "accept, the Connection Service writes the canonical undirected edge to connections "
            "(member_a < member_b), two rows to adjacency_index (a→b and b→a), increments both "
            "members' connection_count, and emits connection.accepted to Kafka. Downstream consumers: "
            "Feed (start fan-out from the new connection), PYMK (refresh candidate features), "
            "Notification (bell), Search (re-score affinity). The undirected canonical row prevents "
            "duplicate edges; the directed adjacency_index gives O(1) neighbour scan for traversal."
        ),
        "connection_graph_storage": (
            "Production-shape: a sharded property-graph service over a distributed KV (Espresso-style "
            "per-shard B-tree with replication) keyed by member_id, value = sorted neighbour list. "
            "Mental model: Neo4j (or Dgraph, JanusGraph) for development clarity; production uses "
            "horizontally sharded KV because Neo4j's single-master write path doesn't scale to 50M "
            "request acceptances/day. 1-hop adjacency reads are O(1) per shard; 2-hop intersection "
            "is a parallel fan-out across the connections of the requesting user. The shard key is "
            "member_id, so neighbour reads are co-located."
        ),
        "degree_of_separation": (
            "Hot-path query on every profile view and search result. Approach: (1) check 1st-degree "
            "via direct adjacency lookup — single shard read, < 5ms cached. (2) For 2nd-degree, "
            "intersect my adjacency set with theirs; bloom-filter pre-check then exact intersect. "
            "(3) For 3rd-degree, intersect my 2-hop neighbourhood with theirs. To bound cost we "
            "materialise per-member 2-hop neighbour sets (capped at ~10M, sketched with HyperLogLog "
            "for very-large) and store as compressed bitmaps in Redis. Above 3rd we render '3rd+'. "
            "Mutual-connection count is computed via the same intersection and cached."
        ),
        "pymk_pipeline": (
            "Daily batch (Spark) reads the full graph and runs 2-hop candidate generation per "
            "active member: for each 1st-degree connection X, take X's 1st-degree connections "
            "(minus self and existing 1st-degree) → candidate set with mutual_count. Cap at 2000 "
            "per member. Feature vector per candidate: mutual_count, company overlap, school "
            "overlap, location overlap, co-view-with-other-friends signal, profile-edit recency, "
            "co-applied-jobs, prior-rejected flag. Gradient-boosted ranker scores candidates; top "
            "50 written to pymk_candidates with TTL. Online refresh: connection.accepted events "
            "trigger incremental candidate updates (the new friend's 1st-degree connections become "
            "candidates with mutual_count=1+). Dismissed candidates write a negative-feedback row "
            "and are suppressed for 90 days."
        ),
        "feed_generation": (
            "Hybrid fan-out, same shape as Instagram but over the connection graph: when a normal "
            "member (≤ ~50K connections) posts, the Fan-out Worker enumerates their 1st-degree "
            "connections from adjacency_index and pushes (post_id, base_score, ts) into each "
            "follower's user_feed. Influencers (verified, follower_count > 100K) and Company Pages "
            "skip fan-out — Feed Service reads the user's pushed feed AND pulls recent posts from "
            "followed influencers/companies on read, then re-ranks with affinity, recency, and "
            "professional-relevance signals. Cap fan-out at the 30K connection limit (a hard "
            "platform constraint that prevents unbounded write storms)."
        ),
        "search": (
            "Per-entity Elasticsearch indexes (people, jobs, companies, posts, groups). A Search "
            "Federation Gateway parses the query, fans out to the relevant indexes, and merges. "
            "People search injects degree-of-separation as a re-ranking signal: 1st-degree results "
            "rank above 2nd, 2nd above 3rd+, then by classical relevance (BM25 + popularity + "
            "personalised affinity). Autocomplete uses edge-ngram analyzers. Profile-edit pipeline "
            "indexes changes via near-real-time bulk updates with ~1h freshness target. Jobs index "
            "is refreshed within 5 min — recruiters expect their posting to be searchable immediately."
        ),
        "jobs_subsystem": (
            "Jobs is its own vertical with the same architectural shape as the main app but a "
            "narrower domain. Posting flow: recruiter creates job → Jobs Service persists → emits "
            "job.posted event → Jobs Search Index ingests → Recommender pipeline batches feature "
            "computation. Application flow: member applies → job_applications row → recruiter sees "
            "via ATS-style applicant pipeline. Critical cross-cut: 'who do I know at this company' "
            "card on every job page is a Connection Graph query: intersect my 1st-degree set with "
            "members whose current_company_id == job.company_id. Pre-cached per (member, company) "
            "pair on first lookup."
        ),
        "endorsements_skills": (
            "Skills are canonicalised — 'JavaScript', 'Javascript', 'JS' all map to the same "
            "skill_id via a curated synonym table maintained by an ML normalisation pipeline. "
            "Endorsements: 1st-degree-only constraint enforced in the API (cheap adjacency lookup). "
            "endorsement_count on member_skills is a denormalised counter updated on insert. "
            "Suggested-endorsements feature uses the skill graph and connection graph: for each "
            "1st-degree connection, score skills by (theirs ∩ co-endorsed-by-our-mutuals)."
        ),
        "notifications": (
            "Per-member inbox table written by Notification Service. Sources: connection requests/"
            "accepts, post engagement (likes/comments/reshares), profile views (premium), job "
            "matches, birthdays/work-anniversaries, mentions. High-volume types are aggregated "
            "('5 people viewed your profile this week'). Push delivery via APNs/FCM and email "
            "digests for inactive members."
        ),
        "premium_subscription": (
            "Subscription Service holds plan, status, billing identity (Stripe). Entitlement is a "
            "tiny in-memory map (member_id → plan) replicated to every gateway and feature edge — "
            "InMail credits, who-viewed-your-profile, advanced search filters, salary insights, "
            "Learning. Cancellations transition to status=canceled with active-until-date; "
            "entitlement check honours the grace window."
        ),
        "messaging": (
            "1:1 + group messaging defers to the dedicated chat design — WebSocket gateway, "
            "Cassandra-backed thread/messages tables, presence service. Mentioned here only "
            "because the bell-icon notification fan-out and InMail (premium-gated message to "
            "non-connections) live alongside it."
        ),
        "spam_and_abuse": (
            "Connection requests are rate-limited per sender and globally; mass-invite patterns "
            "trigger ML-based restrictions. Job postings are domain-verified (company-claimed "
            "domain → verified=true) and scored for ghost-job heuristics. Profile creation goes "
            "through a fraud pipeline that joins email-domain, signup-IP, name-graph features."
        ),
    },
    trade_offs=[
        {"option": "Graph DB (Neo4j) vs sharded SQL/KV property graph",
         "for_neo4j": "Native multi-hop traversal; expressive Cypher; single-source-of-truth model",
         "for_sharded_kv": "Horizontally scalable writes; predictable per-shard latency; fits commodity infra",
         "recommendation": "Sharded KV in production (Espresso-style adjacency-list per member); use the "
                           "graph-DB mental model for design clarity. Neo4j's single-master writer caps "
                           "throughput well below 50M accepts/day."},
        {"option": "Online vs offline PYMK candidate generation",
         "for_online": "Always fresh; reflects last-second connection signals",
         "for_offline": "Affordable 2-hop traversal at full-graph scale; richer features",
         "recommendation": "Daily offline batch + incremental updates on connection.accepted. Top-50 "
                           "served from precomputed table — online ranking only blends real-time signals."},
        {"option": "Push vs pull vs hybrid feed fan-out",
         "for_push": "Sub-second feed open; pre-rankable",
         "for_pull": "Cheap writes; always fresh",
         "recommendation": "Hybrid — push for normal connections, pull for influencers and Company "
                           "Pages. Same as Instagram/Twitter, applied to a 30K-cap connection graph."},
        {"option": "Dedicated job search index vs unified people+job ES",
         "for_dedicated": "Independent freshness SLO (5 min for jobs); narrower mapping; recruiter-tuned ranking",
         "for_unified": "Single query path; cross-entity recall",
         "recommendation": "Dedicated indexes + a federation layer — jobs and people have different "
                           "ranking signals and freshness requirements."},
        {"option": "Materialise mutual-connection counts vs compute on demand",
         "for_materialise": "Sub-10ms reads; no cost amplification under viral profile views",
         "for_demand": "No staleness; no cache invalidation",
         "recommendation": "Materialise (with TTL invalidation on connection.accepted) — the count "
                           "appears on every search result and profile preview."},
    ],
    tips=[
        "Lead with the connection state machine. Mutual consent is THE thing that distinguishes "
        "LinkedIn from Twitter/Instagram — candidates who say 'follow' lose the senior signal.",
        "Spell out 1st/2nd/3rd-degree as a hot-path query and how you bound its cost. Bitmap "
        "intersections + HyperLogLog sketch for huge networks is the senior answer.",
        "Production graph isn't Neo4j — it's a sharded KV property graph (Espresso-style). Mention "
        "Neo4j only as the mental model. Single-master graph DBs don't survive write scale.",
        "PYMK is graph traversal + ML re-ranking, not a SQL query. Two-hop candidate generation, "
        "then a feature-rich gradient-boosted ranker.",
        "Feed is the same hybrid fan-out as Instagram — don't redesign it from scratch; explicitly "
        "name the pattern and adapt it to mutual connections + the 30K cap.",
        "Search is multi-entity. Inject degree-of-separation as a re-rank signal in people search; "
        "say so out loud.",
        "Jobs is a vertical, not a feature — own search, recommender, application workflow. The "
        "cross-cut is 'who do I know here' from the connection graph.",
        "Defer messaging to the chat design — interview honesty beats hand-waving the WebSocket tier.",
    ],
    thought_process=[
        "1. Clarify scope: connections (mutual consent), profile, feed, PYMK, search, jobs, "
        "endorsements, notifications, premium, messaging (defer to chat).",
        "2. Estimate: 1B members, 300M MAU, ~10B edges, 50M requests/day, 1.5B feed opens/day. "
        "Read-skewed by 100:1.",
        "3. APIs: connection workflow (request/accept/decline/withdraw), degree query, PYMK, feed, "
        "search, jobs, profile, notifications.",
        "4. Connection state machine: pending → accepted/declined/withdrawn/expired. Acceptance "
        "writes canonical edge + adjacency index + emits domain event.",
        "5. Graph storage: sharded KV property graph (production); Neo4j as mental model. Adjacency "
        "list per member, sharded by member_id.",
        "6. Degree of separation: 1st via direct adjacency, 2nd/3rd via bitmap intersection of 2-hop "
        "neighbour sets, 3rd+ render. Cache aggressively.",
        "7. PYMK: daily Spark batch for 2-hop candidate gen + ML ranker; incremental updates on "
        "new connections.",
        "8. Feed: hybrid fan-out — push for normal members, pull for influencers/Company Pages.",
        "9. Search: per-entity ES (people, jobs, companies, posts) behind federation gateway; "
        "people ranking is degree-aware.",
        "10. Jobs: own vertical with index + recommender + application workflow; 'who do I know "
        "here' cross-cut hits the connection graph.",
        "11. Endorsements: 1st-degree-only constraint, canonicalised skills, denormalised counts.",
        "12. Premium: subscription service + entitlement map at gateway; messaging defers to chat.",
        "13. SLOs: feed open p99 < 1s, profile p99 < 500ms, search p99 < 300ms, degree query p99 < 50ms.",
    ],
    tags=["social", "graph", "connections", "feed", "search", "jobs", "recommendations", "scale"],
    arch_nodes=[
        {"id": "client", "label": "Web / Mobile", "type": "client"},
        {"id": "lb", "label": "API Gateway", "type": "lb"},
        {"id": "conn", "label": "Connection Service", "type": "server"},
        {"id": "graph", "label": "Connection Graph (sharded KV)", "type": "database"},
        {"id": "profile", "label": "Profile Service", "type": "server"},
        {"id": "feed", "label": "Feed Service", "type": "server"},
        {"id": "fanout", "label": "Fan-out Worker", "type": "service"},
        {"id": "userfeed", "label": "user_feed (Redis+C*)", "type": "cache"},
        {"id": "post", "label": "Post Service", "type": "server"},
        {"id": "pymk", "label": "PYMK Service", "type": "server"},
        {"id": "pymk_pipe", "label": "PYMK Pipeline (Spark/Flink)", "type": "service"},
        {"id": "search", "label": "Search Federation", "type": "server"},
        {"id": "es_people", "label": "People ES Index", "type": "database"},
        {"id": "es_jobs", "label": "Jobs ES Index", "type": "database"},
        {"id": "jobs", "label": "Jobs Service", "type": "server"},
        {"id": "company", "label": "Companies Service", "type": "server"},
        {"id": "endorse", "label": "Endorsements Service", "type": "server"},
        {"id": "notif", "label": "Notification Service", "type": "service"},
        {"id": "sub", "label": "Subscription Service", "type": "server"},
        {"id": "msg", "label": "Messaging Tier", "type": "service"},
        {"id": "kafka", "label": "Kafka", "type": "queue"},
        {"id": "redis", "label": "Redis (degree/mutuals)", "type": "cache"},
        {"id": "cdn", "label": "Media CDN", "type": "cache"},
    ],
    arch_edges=[
        {"source": "client", "target": "lb"},
        {"source": "lb", "target": "conn"},
        {"source": "conn", "target": "graph", "label": "edge write"},
        {"source": "conn", "target": "kafka", "label": "connection.accepted"},
        {"source": "lb", "target": "profile"},
        {"source": "profile", "target": "graph", "label": "degree query"},
        {"source": "profile", "target": "redis", "label": "mutual count"},
        {"source": "lb", "target": "feed"},
        {"source": "feed", "target": "userfeed", "label": "read pushed"},
        {"source": "feed", "target": "post", "label": "pull influencers"},
        {"source": "lb", "target": "post"},
        {"source": "post", "target": "kafka", "label": "post.created"},
        {"source": "kafka", "target": "fanout"},
        {"source": "fanout", "target": "graph", "label": "list connections"},
        {"source": "fanout", "target": "userfeed", "label": "push"},
        {"source": "lb", "target": "pymk"},
        {"source": "pymk_pipe", "target": "graph", "label": "2-hop traversal"},
        {"source": "pymk_pipe", "target": "pymk", "label": "candidate table"},
        {"source": "kafka", "target": "pymk_pipe", "label": "incremental"},
        {"source": "lb", "target": "search"},
        {"source": "search", "target": "es_people"},
        {"source": "search", "target": "es_jobs"},
        {"source": "search", "target": "graph", "label": "degree re-rank"},
        {"source": "lb", "target": "jobs"},
        {"source": "jobs", "target": "es_jobs", "label": "index"},
        {"source": "jobs", "target": "graph", "label": "who do I know here"},
        {"source": "lb", "target": "company"},
        {"source": "lb", "target": "endorse"},
        {"source": "endorse", "target": "graph", "label": "1st-degree check"},
        {"source": "kafka", "target": "notif"},
        {"source": "lb", "target": "sub"},
        {"source": "lb", "target": "msg"},
        {"source": "client", "target": "cdn", "label": "media"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant A as Member A\n"
        "  participant API\n"
        "  participant CS as Conn Service\n"
        "  participant G as Graph\n"
        "  participant K as Kafka\n"
        "  participant N as Notif\n"
        "  participant B as Member B\n"
        "  A->>API: POST /connections/request (to=B)\n"
        "  API->>CS: create request (state=pending)\n"
        "  CS->>K: connection.requested\n"
        "  K->>N: notify B\n"
        "  N-->>B: bell + push\n"
        "  B->>API: POST /connections/{id}/accept\n"
        "  API->>CS: transition pending->accepted\n"
        "  CS->>G: write edge + adjacency (A,B)\n"
        "  CS->>K: connection.accepted\n"
        "  K->>N: notify A\n"
        "  K->>N: PYMK incremental refresh\n"
        "  K->>N: feed fan-out enabled"
    ),
    er_diagram=(
        "erDiagram\n"
        "  MEMBER ||--o{ CONNECTION_REQUEST : sends\n"
        "  MEMBER ||--o{ CONNECTION : has\n"
        "  MEMBER ||--o{ POST : authors\n"
        "  MEMBER ||--o{ MEMBER_SKILL : claims\n"
        "  MEMBER ||--o{ JOB_APPLICATION : submits\n"
        "  COMPANY ||--o{ JOB : posts\n"
        "  JOB ||--o{ JOB_APPLICATION : receives\n"
        "  MEMBER_SKILL ||--o{ ENDORSEMENT : earns\n"
        "  MEMBER ||--o{ SUBSCRIPTION : holds\n"
        "  MEMBER { bigint id PK\n string handle\n string headline\n int connection_count\n bool is_premium }\n"
        "  CONNECTION { bigint member_a\n bigint member_b\n bigint created_at }\n"
        "  CONNECTION_REQUEST { bigint id PK\n bigint from_id\n bigint to_id\n string state }\n"
        "  JOB { bigint id PK\n bigint company_id\n string title\n bigint posted_at }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B[Bidirectional, mutual-consent — NOT a follow]\n"
        "  B --> C[Connection state machine]\n"
        "  C --> D[Sharded property graph (Espresso-style)]\n"
        "  D --> E[1st/2nd/3rd-degree on every read]\n"
        "  E --> F[Bitmap intersection + HLL sketch]\n"
        "  F --> G{Recommendations}\n"
        "  G --> H[PYMK: 2-hop offline + ML re-rank]\n"
        "  G --> I[Job recs: separate vertical]\n"
        "  H --> J[Feed: hybrid fan-out]\n"
        "  J --> K[Search: per-entity ES + degree-aware]\n"
        "  K --> L[Endorsements 1st-degree-only]\n"
        "  L --> M[Premium entitlement at gateway]\n"
        "  M --> N[Messaging defers to chat design]"
    ),
    tradeoff_title="Graph DB (Neo4j) vs Sharded KV Property Graph",
    tradeoff_options=[
        {"label": "Native graph DB (Neo4j / JanusGraph / Dgraph)",
         "description": "Purpose-built engine; expressive multi-hop traversal in one query.",
         "pros": ["Cypher / Gremlin expressiveness",
                  "Cheap multi-hop traversal in-engine",
                  "Single source of truth for the graph"],
         "cons": ["Single-master write path caps throughput",
                  "Operational maturity at multi-billion-edge scale is lower",
                  "Mixing graph + non-graph workloads is awkward"]},
        {"label": "Sharded KV property graph (Espresso-style)",
         "description": "Adjacency list per member stored in a distributed KV; reads partitioned by member_id.",
         "pros": ["Horizontally scalable writes — fits 50M accepts/day",
                  "Predictable per-shard latency with replication",
                  "Reuses existing infra primitives (KV + cache + ES)"],
         "cons": ["Multi-hop traversal is application code, not engine",
                  "Bitmap intersection + sketches needed for degree-of-separation",
                  "Schema evolution requires app-side discipline"]},
        {"label": "Hybrid (graph DB for offline analytics, KV for hot path)",
         "description": "Hot serving from sharded KV; nightly export into a graph DB for analytics + PYMK pipeline.",
         "pros": ["Best of both: cheap reads + powerful analytics queries",
                  "Decouples online tier from analytics scale"],
         "cons": ["Two systems to keep in sync",
                  "Pipeline latency on the analytics side"]},
    ],
    tradeoff_rec="Sharded KV property graph for the online tier (production-grade write scale + predictable "
                 "reads), with optional offline graph-DB or Spark GraphX for batch PYMK and graph analytics. "
                 "Native graph DBs don't survive LinkedIn's write throughput on a single master.",
    senior_topics=[
        _topic("connection-state-machine",
               "The Connection Workflow as a State Machine",
               "Mutual-consent is what differentiates LinkedIn from follow-graph platforms. The "
               "request lifecycle has explicit states with explicit transitions, and many downstream "
               "behaviours hang off the accepted transition.",
               [
                   ("States and transitions",
                    "pending → accepted | declined | withdrawn | expired (after 6 months idle). "
                    "Only pending → accepted creates an edge. Declined is a soft state — no edge "
                    "is created and the sender is not notified (anti-harassment). Withdrawn is "
                    "sender-initiated cancellation. Expired runs as a sweeper job."),
                   ("Acceptance side effects",
                    "Atomic write (or saga) of: canonical undirected edge, two adjacency_index "
                    "rows, increment connection_count on both members, mark request accepted, emit "
                    "connection.accepted Kafka event. Downstream consumers: Feed (start fan-out), "
                    "PYMK (refresh candidates), Notification (bell), Search (re-score affinity)."),
                   ("Idempotency and races",
                    "Two members may try to connect simultaneously — the API canonicalises the pair "
                    "(min/max member_id) so the second request collapses into the first or is "
                    "auto-accepted. Acceptance is idempotent on (request_id, accepted)."),
                   ("Anti-spam gates",
                    "Rate-limit per sender (~100/day baseline; higher for verified). ML signal on "
                    "mass-invite patterns drops the limit. 'I don't know this person' on accept "
                    "feeds a negative-signal pipeline that throttles bad senders."),
                   ("Why a state machine and not a flag",
                    "Flag-based ('is_connected') loses the request workflow — no inbox, no decline "
                    "without notification, no 'who I sent invites to'. The state machine is the "
                    "first-class product surface, not internal plumbing."),
               ],
               diagram=(
                   "stateDiagram-v2\n"
                   "  [*] --> pending : send\n"
                   "  pending --> accepted : recipient accepts\n"
                   "  pending --> declined : recipient declines\n"
                   "  pending --> withdrawn : sender withdraws\n"
                   "  pending --> expired : 6mo idle\n"
                   "  accepted --> [*] : edge written\n"
                   "  declined --> [*]\n"
                   "  withdrawn --> [*]\n"
                   "  expired --> [*]"
               )),
        _topic("graph-storage",
               "Why Production Isn't Neo4j — Sharded KV Property Graph at Scale",
               "Native graph DBs are a great mental model but fail at LinkedIn's write throughput. "
               "Production uses a sharded KV property graph (Espresso-style at LinkedIn, similar in "
               "shape at Facebook with TAO and at Twitter with FlockDB).",
               [
                   ("Why Neo4j hits a wall",
                    "Neo4j's write path goes through a single leader. 50M new connection accepts/"
                    "day at peak ~5K writes/sec is uncomfortable for a single-leader engine, before "
                    "you add post creation, profile updates, endorsements, etc. Read replicas help "
                    "reads but writes don't scale horizontally."),
                   ("Sharded adjacency list",
                    "Member_id is the shard key. Each shard stores members[id] = {profile, "
                    "neighbours: sorted [neighbour_id]}. Adding an edge is a (member_a-shard, "
                    "member_b-shard) pair of writes — two-phase commit or saga depending on "
                    "consistency budget."),
                   ("Co-location for hot reads",
                    "Profile read + degree query for the same viewer hits one shard for the "
                    "viewer's neighbours; the target member's shard answers the existence query. "
                    "Two-shard fan-out, both cacheable."),
                   ("Multi-hop is application code",
                    "2-hop intersection isn't a Cypher one-liner; it's app code that reads my "
                    "neighbour list (one shard), my target's neighbour list (one shard), intersects "
                    "(in-process or via bitmap on Redis). Trade engine sugar for write scalability."),
                   ("Graph DB still earns its keep — offline",
                    "Spark GraphX, GraphFrames, or a periodic Neo4j export power PYMK candidate "
                    "generation, community detection, fraud-ring detection. The hot path stays on "
                    "the KV; analytics use the graph engine."),
               ],
               diagram=(
                   "graph TD\n"
                   "  S1[Shard 1<br/>members 0-N/3]\n"
                   "  S2[Shard 2<br/>members N/3-2N/3]\n"
                   "  S3[Shard 3<br/>members 2N/3-N]\n"
                   "  R[Replica per shard]\n"
                   "  C[Coordinator]\n"
                   "  C --> S1\n"
                   "  C --> S2\n"
                   "  C --> S3\n"
                   "  S1 -.replicates.-> R\n"
                   "  S2 -.replicates.-> R\n"
                   "  S3 -.replicates.-> R"
               )),
        _topic("degree-of-separation",
               "1st/2nd/3rd-Degree on the Hot Path",
               "Degree-of-separation is computed on every profile preview, every search result hover, "
               "every PYMK card. It must be < 50ms p99. Naive 2-hop traversal on a 30K-degree node is "
               "infeasible — bitmap intersection + sketches make it tractable.",
               [
                   ("1st-degree: direct lookup",
                    "Single shard read against viewer's adjacency list, bloom-filter pre-check on "
                    "neighbour set. Sub-5ms cached."),
                   ("2nd-degree: set intersection",
                    "viewer's neighbours ∩ target's neighbours. Maintained as compressed bitmaps "
                    "(Roaring bitmaps over member_id) in Redis for active users. Intersection of "
                    "two bitmaps is microseconds; cardinality gives the mutual-count badge."),
                   ("3rd-degree: 2-hop neighbourhood",
                    "Materialise per-member 2-hop neighbour set (capped). For pairs where exact "
                    "set is too large (super-connectors), use HyperLogLog sketches and approximate. "
                    "The product UX is fine with ~95% accurate '3rd vs 3rd+' rendering."),
                   ("Cache invalidation",
                    "connection.accepted invalidates the bitmap cache for both endpoints AND their "
                    "1-hop neighbours (whose 2-hop sets just changed). Eventual consistency is OK "
                    "— a brief ~minute staleness on degree-of-separation is invisible in product."),
                   ("Why not BFS at request time",
                    "A super-connector's 1-hop set is 30K. 2-hop is millions. BFS at request time "
                    "is impossible inside a 50ms budget. Pre-computation is the only path."),
               ],
               diagram=(
                   "graph LR\n"
                   "  V[Viewer] --> N1[Neighbours<br/>bitmap]\n"
                   "  T[Target] --> N2[Neighbours<br/>bitmap]\n"
                   "  N1 --> I[Intersect]\n"
                   "  N2 --> I\n"
                   "  I --> D{Cardinality > 0?}\n"
                   "  D -->|Yes| R1[2nd-degree + mutual count]\n"
                   "  D -->|No| H[Try 2-hop sets]\n"
                   "  H --> D2{Intersect ≠ 0?}\n"
                   "  D2 -->|Yes| R2[3rd-degree]\n"
                   "  D2 -->|No| R3[3rd+]"
               )),
        _topic("pymk",
               "People You May Know — Graph Traversal + ML",
               "PYMK is the canonical interview-trap recommendation problem: candidate generation "
               "via graph traversal, then ML re-ranking on rich features. Not a SQL query, not a "
               "single algorithm.",
               [
                   ("Candidate generation: 2-hop friend-of-friend",
                    "For each active member, take their 1st-degree connections; for each of those, "
                    "take 1st-degree connections (friends-of-friends); subtract self and existing "
                    "1st-degree; aggregate mutual_count. Cap candidate set at 2000/member. Spark "
                    "GraphX or a custom Pregel-style job runs nightly over the full graph."),
                   ("Feature engineering",
                    "Per (viewer, candidate): mutual_count, company overlap (current + past), "
                    "school overlap, location overlap, co-view-by-mutual-friends, prior-rejected "
                    "flag (suppress 90 days), industry overlap, profile-edit recency, endorsement "
                    "co-occurrence, similarity-of-skills."),
                   ("Re-ranker",
                    "Gradient-boosted decision tree (XGBoost/LightGBM) trained on accept/dismiss "
                    "labels. Top-50 written to pymk_candidates with daily refresh. Online layer "
                    "may apply real-time deltas — e.g., a just-accepted connection's 1st-degree "
                    "list becomes immediate candidates with mutual_count = 1+."),
                   ("Cold start",
                    "New members lack a 2-hop neighbourhood. Bootstrap from email/contact-import, "
                    "school + company + location signals, and an exploration tier that surfaces "
                    "popular accounts with non-zero affinity."),
                   ("Negative feedback loop",
                    "Dismiss action writes a suppression row used both by the ranker (negative "
                    "signal) and the serving layer (filter for 90 days). Without this, the same "
                    "candidates resurface and erode trust."),
                   ("Why not online traversal",
                    "Computing fresh 2-hop candidates for every active user on demand is "
                    "intractable — full 2-hop expansion of a high-degree node is millions of edges. "
                    "Offline batch + incremental updates is the only viable shape."),
               ],
               diagram=(
                   "graph TD\n"
                   "  G[Connection Graph] --> S[Spark batch nightly]\n"
                   "  S --> C[2-hop candidate gen<br/>per member, cap 2000]\n"
                   "  C --> F[Feature lookup<br/>company/school/location]\n"
                   "  F --> M[ML re-ranker<br/>GBDT]\n"
                   "  M --> T[pymk_candidates<br/>top-50 per member]\n"
                   "  K[Kafka connection.accepted] --> I[Incremental updates]\n"
                   "  I --> T\n"
                   "  T --> A[API serve]"
               )),
        _topic("search-federation",
               "Multi-Entity Search with Degree-Aware Ranking",
               "LinkedIn search spans people, jobs, companies, posts, and groups. Each entity has "
               "different ranking signals, freshness needs, and access control. A federation gateway "
               "fans out to per-entity Elasticsearch indexes and merges with degree-of-separation "
               "as a first-class re-ranking signal for people search.",
               [
                   ("Per-entity indexes",
                    "Separate ES clusters / indexes for people, jobs, companies, posts. Each has "
                    "its own analyzers, mappings, and refresh cadence (jobs < 5 min, profiles ~1h, "
                    "companies ~1d). Independent scaling avoids hot-spotting."),
                   ("Federation gateway",
                    "Parses the query, classifies intent (jobs vs people vs company), fans out to "
                    "the right indexes in parallel, deduplicates, merges with cross-entity "
                    "ranking. Single response shape to the client."),
                   ("Degree-aware people ranking",
                    "ES returns BM25 + popularity. The federation layer joins with the Connection "
                    "Graph (degree-of-separation per result) and re-ranks: 1st > 2nd > 3rd > 3rd+, "
                    "tie-break by relevance + affinity. Done in a streaming top-K pipeline so we "
                    "don't hydrate degree for every match — only the top ~200 candidates."),
                   ("Autocomplete",
                    "edge-ngram analyzer on member.handle, name, headline, company.name. "
                    "Personalised by recent searches and degree (your 1st-degree connections "
                    "dominate completions for ambiguous prefixes)."),
                   ("Filters and facets",
                    "Faceting on industry, location, company, school, current_role. Premium users "
                    "get expanded filters (years-of-experience ranges, function categorisation). "
                    "Filter parsing happens at the gateway; ES performs the constrained query."),
                   ("Why not unified index",
                    "People and jobs have orthogonal ranking signals (degree-aware vs skill-match), "
                    "different freshness SLOs (1h vs 5min), and different access controls. A unified "
                    "index forces the lowest common denominator on all dimensions."),
               ]),
        _topic("jobs-vertical",
               "Jobs as a First-Class Vertical with a Connection-Graph Cross-Cut",
               "Jobs is its own subsystem with posting, search, recommendation, and application "
               "workflows — but the connection graph is the thing that makes LinkedIn's job product "
               "special: 'who do I know at this company' on every job page.",
               [
                   ("Posting flow",
                    "Recruiter creates a job → Jobs Service persists row → emits job.posted → ES "
                    "ingests for searchability < 5 min → Recommender pipeline batches feature "
                    "computation. Domain-verified company posts (verified=true) rank higher; "
                    "ghost-job heuristics down-rank stale postings."),
                   ("Application workflow",
                    "Member applies (job_applications row, state=submitted) → ATS-style applicant "
                    "pipeline (recruiter views, shortlists, advances). State transitions: submitted "
                    "→ in_review → interview → offer → accepted/rejected. Each is a notification "
                    "to the applicant."),
                   ("Job recommendations",
                    "Per-member ranked feed: features include skills overlap (member_skills ∩ "
                    "job.skills), location, seniority match, company affinity (followed companies), "
                    "and connection-network signal ('5 of your connections work here'). Re-ranked "
                    "daily with a separate ML model from PYMK."),
                   ("'Who do I know here' cross-cut",
                    "On every job page, intersect the viewer's 1st-degree connections with members "
                    "whose current_company_id == job.company_id. Result is the network-insight card "
                    "('5 connections work at Acme, 2 in similar roles'). Cached per (member, "
                    "company) pair on first lookup; invalidated on job-change events."),
                   ("Search vs recommendation split",
                    "Search is recall-first (member typed 'frontend engineer NYC'); recommendation "
                    "is precision-first (top 10 we surface unprompted). Different ranking models, "
                    "shared corpus."),
               ]),
        _topic("feed-fanout",
               "Hybrid Feed Fan-out on a Connection Graph",
               "Feed generation is the same hybrid push/pull pattern as Instagram or Twitter, with "
               "two LinkedIn-specific twists: connections are bounded at 30K (a hard cap), and "
               "Company Pages + 'follow' relationships add a one-way follow channel alongside the "
               "mutual connection graph.",
               [
                   ("Push for the long tail",
                    "When a normal member posts, fan-out worker enumerates their 1st-degree "
                    "connections (capped at 30K) and pushes (post_id, base_score, ts) into each "
                    "user_feed shard. Average member has ~500 connections — comfortable write fan-out."),
                   ("Pull for influencers + Company Pages",
                    "Verified influencers and Company Pages can have millions of followers. Pure "
                    "push would create write storms. Their posts skip fan-out; Feed Service pulls "
                    "their recent posts on read and merges with the user's pushed feed."),
                   ("30K cap protects the system",
                    "The platform-imposed 30K connection limit is also a write-fan-out ceiling. "
                    "Without it the worst-case fan-out would be the celeb-pull problem from social "
                    "platforms. With it, push remains tractable for every non-influencer."),
                   ("Re-ranking on read",
                    "The pre-computed score is just a recency baseline. On read, Feed Service "
                    "joins with the engagement counter, viewer affinity, and post type (article > "
                    "share > job > like-only ranks differently). Top-K on the merged list is the "
                    "served feed."),
                   ("Eventual consistency",
                    "A new post may take seconds to appear in a follower's feed (fan-out worker "
                    "lag). Acceptable UX for a professional network — the immediate-publish surface "
                    "is the author's own profile timeline, served from the canonical post store."),
               ]),
        _topic("endorsements-skills",
               "Endorsements + Skill Canonicalisation",
               "Skills + endorsements are a small surface but a good interview probe: "
               "canonicalisation is non-trivial, the 1st-degree-only constraint is a graph query "
               "on the hot path, and the suggested-endorsements feature is a multi-graph join.",
               [
                   ("Skill canonicalisation",
                    "'JavaScript', 'Javascript', 'JS' all map to a single skill_id. A curated "
                    "synonym table (member-suggested + ML-clustered) backs the normalisation. New "
                    "skills go through a moderation/clustering pipeline; member-typed values are "
                    "matched fuzzy-then-canonical-ID at write time."),
                   ("1st-degree-only constraint",
                    "API enforces that endorser and endorsee are 1st-degree connected via Connection "
                    "Graph adjacency lookup. Cheap (sub-5ms cached) but mandatory — protects against "
                    "inflated endorsement counts."),
                   ("Counter denormalisation",
                    "endorsement_count on member_skills is updated at write time. The endorsements "
                    "table is the source of truth; the counter is the read-fast denorm. Periodic "
                    "reconciliation job catches drift."),
                   ("Suggested endorsements",
                    "On profile view, suggest skills to endorse: for each 1st-degree connection, "
                    "score their skills by (skills they're already endorsed for) × (skills my "
                    "mutual friends endorsed them for). Encourages the engagement loop without "
                    "noise from random suggestions."),
                   ("Why this is a senior probe",
                    "Naive design: 'just store endorsements'. Senior design names canonicalisation, "
                    "the graph constraint, the denorm strategy, and the suggestion feature. "
                    "Demonstrates seeing the whole loop, not just the table."),
               ]),
    ],
)
