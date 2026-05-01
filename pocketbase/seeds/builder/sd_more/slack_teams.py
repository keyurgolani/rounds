from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design Slack / Microsoft Teams",
    "Hard",
    "Design a workplace messaging platform supporting multi-tenant workspaces (Slack) or orgs/tenants "
    "(Teams), persistent channels (public, private, shared), 1:1 and group DMs, threaded replies, "
    "rich reactions/emoji, file uploads, presence (active/away/dnd), full-text search across an "
    "entire workspace's history, push notifications, and a thriving integration ecosystem (bots, "
    "slash commands, incoming/outgoing webhooks, Apps with OAuth scopes). Target: ~20M concurrent "
    "users, ~100K active workspaces of varying size (3 to 500K members), millions of channels, and "
    "tens of billions of historical messages searchable in <500ms. Unlike WhatsApp, the server is "
    "trusted — messages are stored server-side (encrypted at rest, not E2EE), enabling search, "
    "compliance/eDiscovery, retention policies, and rich integrations. The hard problems are the "
    "channel timeline + thread model under heavy fan-out, presence at workspace scale, indexing "
    "for low-latency cross-channel search with permission filtering, and a multi-workspace user "
    "identity that lets one human be a guest in many orgs without leaking data across them.",
    hints=[
        "Server-side storage, NOT E2EE — that's the dividing line vs WhatsApp; everything else flows from it.",
        "The unit of read is a channel timeline. Per-channel append-only message log + cursor pagination.",
        "Threads are not a separate log — they're (parent_ts, thread_ts) child rows hanging off a parent.",
        "Presence is soft-state in Redis; never put heartbeats in the message DB.",
        "Search = Elasticsearch with a permission filter (channel ACL) applied at query time, not index time.",
        "Multi-workspace identity: one human, many memberships. Channel/message keys must include workspace_id.",
        "Fan-out for read state is per (user, channel) cursor, not per-message receipts — channels can have 50K members.",
        "Mentions trigger notifications; non-mention messages do not — that's the cheap signal that scales.",
    ],
    constraints=[
        "Multi-tenant: workspaces are strict isolation boundaries — never leak across",
        "Workspaces from 3 to 500K members; channels from 2 to 100K members",
        "20M concurrent WebSocket connections globally; ~100K workspaces active",
        "Tens of billions of historical messages, retained per workspace policy",
        "p50 message send→deliver <300ms; p99 <1s within a workspace",
        "Search latency p99 <500ms across an entire workspace's history",
        "Compliance: eDiscovery export, legal hold, configurable retention (1 day to forever)",
        "Integrations: 10K+ third-party apps, rate-limited per app per workspace",
    ],
    req_func=[
        "Workspaces with channels (public, private, shared across workspaces)",
        "1:1 and group direct messages",
        "Threaded replies on any message; reactions and custom emoji",
        "Server-side message store with edit/delete history and tombstones",
        "Per-channel cursor pagination (load older / load newer)",
        "Presence: active / away / do-not-disturb with per-user privacy",
        "Push notifications (APNS/FCM) for mentions, DMs, and keyword alerts",
        "Full-text search across all channels the user can read",
        "File uploads (any type, up to ~1GB) with previews and access control",
        "Integrations: bots, slash commands, incoming/outgoing webhooks, OAuth apps",
        "Org-wide directory with multi-workspace user identity (one human, many memberships)",
        "@mentions (user, group, here, channel, subteam) → notifications",
        "Per-(user, channel) read state — last_read cursor + unread/badge counts",
        "Admin: retention policies, eDiscovery export, legal hold, member provisioning (SCIM/SSO)",
    ],
    req_nonfunc=[
        "Multi-tenant isolation — strong, enforced at every layer",
        "Send→deliver p50 <300ms; p99 <1s when both peers online in same region",
        "Search p99 <500ms over a full workspace's index, with ACL filter",
        "Availability 99.99% per region; 99.95% for cross-region federated DMs",
        "Durability: zero message loss after server ACK; replicated WAL + S3 archive",
        "Scale: 20M concurrent sockets, ~10B messages/day across the fleet",
        "Compliance: encryption at rest, audit log of admin actions, retention enforcement",
        "Cost: hot data on SSD/Postgres, warm on Elasticsearch, cold on S3+Parquet",
    ],
    estimation={
        "workspaces": "~100K active",
        "concurrent_sockets": "~20M",
        "messages_per_day": "~10B",
        "messages_per_user_per_day": "~50 read, ~5 sent",
        "channels_per_workspace": "median 100, p99 ~10K",
        "members_per_channel": "median 8, p99 50K (#general in giant orgs)",
        "search_qps": "~50K/sec global",
        "presence_writes": "20M sockets × 1 heartbeat / 30s ≈ 670K/sec",
        "storage_hot": "~1KB/msg × 10B/day = ~10TB/day raw; ~3TB/day after compression",
        "files_per_day": "~50M; avg 500KB; 25TB/day to object storage",
    },
    endpoints=[
        {"method": "POST", "path": "/v1/workspaces/{ws}/channels/{ch}/messages",
         "description": "Send a message (or threaded reply if thread_ts provided)",
         "body": "{client_msg_id, text, blocks?, thread_ts?, attachments?}"},
        {"method": "GET", "path": "/v1/workspaces/{ws}/channels/{ch}/messages",
         "description": "Cursor-paginated channel history (oldest_ts, newest_ts, limit, inclusive)"},
        {"method": "GET", "path": "/v1/workspaces/{ws}/channels/{ch}/threads/{parent_ts}",
         "description": "Fetch all replies for a thread parent"},
        {"method": "POST", "path": "/v1/workspaces/{ws}/channels/{ch}/read",
         "description": "Update per-(user, channel) last_read cursor",
         "body": "{last_read_ts}"},
        {"method": "POST", "path": "/v1/workspaces/{ws}/messages/{ts}/reactions",
         "description": "Add or remove a reaction (emoji name, add|remove)"},
        {"method": "POST", "path": "/v1/files.upload",
         "description": "Multipart upload; returns file_id used to attach in messages"},
        {"method": "GET", "path": "/v1/search",
         "description": "Full-text search across channels the user can read",
         "body": "{q, workspace_id, channel?, from?, to?, sort, cursor}"},
        {"method": "GET", "path": "/v1/presence/{user}",
         "description": "Read presence (filtered by privacy)"},
        {"method": "GET", "path": "/v1/rtm.connect",
         "description": "Bootstrap WebSocket: returns ws_url + initial state snapshot"},
        {"method": "POST", "path": "/v1/hooks/incoming/{token}",
         "description": "Incoming webhook from a third-party app — posts as the integration"},
    ],
    tables=[
        {"name": "workspaces",
         "columns": ["id BIGINT PK", "domain VARCHAR(64) UNIQUE", "name VARCHAR",
                     "plan VARCHAR(16)", "retention_days INT", "created_at BIGINT"]},
        {"name": "users",
         "columns": ["id BIGINT PK", "email VARCHAR UNIQUE", "name VARCHAR",
                     "global_avatar_url TEXT", "created_at BIGINT"]},
        {"name": "memberships",
         "columns": ["user_id BIGINT", "workspace_id BIGINT", "role VARCHAR(16)",
                     "display_name VARCHAR", "is_guest BOOL", "joined_at BIGINT",
                     "PRIMARY KEY (user_id, workspace_id)"]},
        {"name": "channels",
         "columns": ["id BIGINT PK", "workspace_id BIGINT", "name VARCHAR(80)",
                     "type VARCHAR(8)", "is_archived BOOL", "creator_id BIGINT",
                     "created_at BIGINT"]},
        {"name": "channel_members",
         "columns": ["channel_id BIGINT", "user_id BIGINT", "joined_at BIGINT",
                     "PRIMARY KEY (channel_id, user_id)"]},
        {"name": "messages",
         "columns": ["workspace_id BIGINT", "channel_id BIGINT", "ts BIGINT",
                     "thread_ts BIGINT NULL", "user_id BIGINT", "text TEXT",
                     "blocks_json JSONB", "edited_at BIGINT NULL", "deleted_at BIGINT NULL",
                     "PRIMARY KEY (workspace_id, channel_id, ts)"]},
        {"name": "reactions",
         "columns": ["workspace_id BIGINT", "channel_id BIGINT", "ts BIGINT",
                     "emoji VARCHAR(64)", "user_id BIGINT", "created_at BIGINT",
                     "PRIMARY KEY (workspace_id, channel_id, ts, emoji, user_id)"]},
        {"name": "read_state",
         "columns": ["user_id BIGINT", "channel_id BIGINT", "last_read_ts BIGINT",
                     "mention_count INT", "PRIMARY KEY (user_id, channel_id)"]},
        {"name": "files",
         "columns": ["id BIGINT PK", "workspace_id BIGINT", "uploader_id BIGINT",
                     "name VARCHAR", "mime VARCHAR(64)", "size_bytes BIGINT",
                     "storage_url TEXT", "acl_channel_ids BIGINT[]", "created_at BIGINT"]},
        {"name": "apps",
         "columns": ["id BIGINT PK", "name VARCHAR", "scopes TEXT[]", "owner_workspace_id BIGINT"]},
        {"name": "app_installs",
         "columns": ["app_id BIGINT", "workspace_id BIGINT", "bot_user_id BIGINT",
                     "scopes TEXT[]", "PRIMARY KEY (app_id, workspace_id)"]},
    ],
    indexes=[
        "(workspace_id, channel_id, ts DESC) on messages — channel timeline scan",
        "(workspace_id, channel_id, thread_ts, ts) on messages — thread replies",
        "(user_id, workspace_id) on memberships",
        "(channel_id, user_id) on channel_members",
        "(user_id, channel_id) on read_state",
        "Elasticsearch index per workspace, sharded; doc fields: text, channel_id, user_id, ts",
    ],
    hld_desc=(
        "Edge gateways terminate WebSocket and route by workspace_id (sharded). The Channel Service "
        "owns the per-channel append-only message log in Postgres/Vitess (sharded by workspace), "
        "publishes to Kafka for fan-out and indexing. The Connection/Fan-out Service maps "
        "(workspace, channel) to all subscribed sockets and pushes new messages. Presence is "
        "soft-state in Redis with per-region pub/sub. Search is Elasticsearch with a per-workspace "
        "index, ACL filter applied at query time. Files go directly to S3 via signed URLs; the file "
        "record stores ACL. Push notifications via APNS/FCM, triggered only by mentions/DMs/keyword "
        "alerts to keep volume sane. Bots/webhooks run through the same channel API as humans."
    ),
    hld_components=[
        {"name": "Edge Gateway / WS Tier", "role": "TLS, WebSocket, auth, route by workspace shard"},
        {"name": "Connection Manager", "role": "Per-region socket registry; (channel → sockets) fan-out"},
        {"name": "Channel Service", "role": "Append message, paginate timeline, validate ACL"},
        {"name": "Thread Service", "role": "Logically same store; encapsulates thread reads + reply counts"},
        {"name": "Reaction Service", "role": "Idempotent add/remove with per-emoji counters"},
        {"name": "Read State Service", "role": "Per-(user, channel) cursor + mention counters"},
        {"name": "Presence Service", "role": "Heartbeats in Redis; subscriber set per user; privacy filter"},
        {"name": "Search Service", "role": "Elasticsearch indexer + query gateway with ACL filter"},
        {"name": "Notification Service", "role": "Mention extraction, push to APNS/FCM, email digests"},
        {"name": "File Service", "role": "S3 signed URLs, AV scan, preview generation, ACL bound to channels"},
        {"name": "Integration Platform", "role": "Bot tokens, slash commands, webhooks, Events API"},
        {"name": "Identity / Directory", "role": "User, workspace, membership; SCIM, SSO, multi-workspace"},
        {"name": "Compliance / eDiscovery", "role": "Retention, legal hold, export pipeline"},
        {"name": "Kafka Bus", "role": "message-events, mention-events, search-index, audit"},
    ],
    detailed_design={
        "channel_timeline": (
            "Messages are an append-only log keyed (workspace_id, channel_id, ts). ts is a "
            "client-visible monotonic timestamp generated by the Channel Service per channel "
            "(microsecond resolution, never reused even on edit). Read paths are cursor-based: "
            "GET /messages?before=ts&limit=50 binary-searches the index. The store is Postgres "
            "(sharded by workspace_id via Vitess/Citus) for hot data, with periodic compaction to "
            "S3 + Parquet for cold tiers older than the workspace's retention window. We deliberately "
            "do NOT use a per-user inbox model (that's WhatsApp's E2EE constraint) — the channel "
            "log IS the source of truth, and clients pull from it."
        ),
        "threads": (
            "A thread is just messages with thread_ts = the parent's ts. The parent row carries "
            "reply_count and reply_users_count denormalized for the channel timeline UI. Thread "
            "reads are a single index-range scan on (workspace, channel, thread_ts, ts). New "
            "replies fan out twice: to subscribers viewing the channel (with a reply-count bump) "
            "and to subscribers actively viewing that thread (full message)."
        ),
        "fan_out_and_delivery": (
            "On send: write to Postgres → emit to Kafka → Connection Manager looks up sockets "
            "subscribed to (workspace, channel) → push frame. Subscribers are computed lazily as "
            "users join channels client-side (not pre-computed for huge channels). For #general at "
            "100K members, we don't push to every socket — only to currently-connected sockets "
            "actually viewing or recently-active in that channel. Others discover the message on "
            "next channel open, via cursor delta."
        ),
        "presence": (
            "Redis hash presence:{workspace_id}:{user_id} → {device_id: last_heartbeat_ts}. "
            "Heartbeat from each socket every 30s. Online iff any heartbeat <60s old; away if "
            "60-300s; offline beyond. DND is an explicit user setting, not a timeout. Presence "
            "subscriptions are batched per user (one query returns presence for all members of a "
            "user's open channels). Privacy: visible to (workspace members | direct contacts | "
            "nobody) per user setting, enforced at read."
        ),
        "search": (
            "Elasticsearch per-workspace index (large workspaces sharded across multiple ES "
            "shards). Indexer consumes message-events Kafka topic; deletes/edits emit tombstone "
            "or update doc. Query path: JWT carries user_id; service computes the set of channel "
            "IDs the user can read (memberships + public channels in this workspace) and adds it "
            "as a terms filter. ACL filter at query time, not index time, so re-adding a user to "
            "a channel doesn't require re-indexing. For very large workspaces (>50K channels), "
            "we cache the readable-channel-set in Redis per user with short TTL."
        ),
        "read_state_and_unreads": (
            "Per-(user, channel) row with last_read_ts and mention_count. On message send, the "
            "channel service does not write to every member's read_state — that's O(N). Instead, "
            "unreads are computed lazily: client UI queries 'for each of my channels, count msgs "
            "where ts > last_read_ts'. We keep mention_count incrementally maintained because "
            "mentions are sparse (only the @-targeted users) and the badge UX is hot."
        ),
        "notifications": (
            "Notification Service consumes the message-events topic, parses mentions/keywords, "
            "and emits push events for matching users. Only mentions, DMs, threads-you're-in, and "
            "keyword alerts trigger pushes — not every channel message. Honors DND and per-channel "
            "muting. APNS/FCM payload includes channel + sender + a snippet (server-rendered, "
            "since we have plaintext)."
        ),
        "files": (
            "Direct-to-S3 multipart upload via signed URL. After upload, client calls files.complete "
            "with the file_id and a list of channels to share into. The file record stores "
            "acl_channel_ids; downloads issue a fresh signed URL only after re-checking the "
            "viewer's membership in any of those channels. AV scan + preview generation run async; "
            "until complete, the message shows 'processing'."
        ),
        "integrations": (
            "Apps register with scopes (channels:read, chat:write, files:read, etc.). Workspace "
            "admin installs an app → OAuth grant → app receives a workspace-scoped bot token. "
            "Bots post messages through the same /messages endpoint with bearer = bot token. "
            "Slash commands and interactive messages POST a signed payload to the app's URL. "
            "Outgoing webhooks (Events API): Notification Service POSTs subscribed events to the "
            "app's HTTPS endpoint with HMAC signature. Per-app rate limits: ~1 msg/sec/channel, "
            "with burst budget."
        ),
        "multi_workspace_identity": (
            "Global users table holds the human (email, password hash, MFA). memberships joins to "
            "workspaces with a per-workspace display_name + role + is_guest. All keys at the "
            "channel/message/file layer carry workspace_id; cross-workspace queries are forbidden "
            "at the data layer. Shared channels (channel spans two workspaces) are modeled as a "
            "channel with two workspace_ids in a federation table; messages still write to one "
            "primary and replicate."
        ),
        "compliance_retention": (
            "Per-workspace retention policy (e.g. 90 days for Free, configurable for Enterprise). "
            "A daily job tombstones messages past retention; tombstones become hard deletes after "
            "an additional grace period. Legal hold flag suspends deletion for a (workspace, "
            "user|channel) scope. eDiscovery export streams matching messages to a customer-"
            "controlled S3 bucket as JSON + linked files."
        ),
        "slo_contract": (
            "Send→deliver p50 <300ms / p99 <1s within a region. Search p99 <500ms. WS connect "
            "p99 <2s including initial-snapshot. Presence updates eventually consistent <30s. "
            "Push notification delivery best-effort, SLO 95% in <60s. Zero message loss after "
            "server ACK; bounded message reordering only within the same channel within 1ms."
        ),
    },
    trade_offs=[
        {"option": "Per-channel log vs per-user inbox",
         "for_per_channel": "One source of truth, search-friendly, integrations easy, lower writes",
         "for_per_user": "Trivial offline delivery, simple cursors, required by E2EE",
         "recommendation": "Per-channel log — Slack/Teams are server-trusted, search and integrations win."},
        {"option": "Push every message vs lazy fan-out",
         "for_push_all": "Lowest perceived latency, simple client",
         "for_lazy": "Scales to 100K-member channels; sockets only push for currently-viewed channels",
         "recommendation": "Lazy with active-view boost — push to currently-viewing sockets; rest pull on open."},
        {"option": "ACL at index time vs query time",
         "for_index_time": "Fast queries, no ACL join",
         "for_query_time": "Membership changes don't trigger reindex; correct semantics",
         "recommendation": "Query time — channel membership churn is constant; reindex cost is prohibitive."},
        {"option": "Presence in DB vs Redis",
         "for_db": "Single store",
         "for_redis": "670K writes/sec is trivial in Redis, disastrous in Postgres",
         "recommendation": "Redis — soft state, never durable. Lose it on restart, recover on next heartbeat."},
        {"option": "Read receipts per recipient vs per-(user, channel) cursor",
         "for_per_recipient": "Granular 'seen by Alice' UI",
         "for_cursor": "O(1) state per channel-member, scales to huge channels",
         "recommendation": "Cursor — Slack does NOT do per-message read receipts; it's intentional."},
    ],
    tips=[
        "Open with the dividing line: server-trusted, server-side store. Everything follows.",
        "Channel log is the source of truth, NOT a per-user inbox. Don't import WhatsApp's model.",
        "Threads are a (parent_ts, thread_ts) shape on the same log — not a separate store.",
        "Lazy fan-out for 100K-member channels — only push to currently-viewing sockets.",
        "ACL filter at search query time, not index time — channel membership changes constantly.",
        "Presence in Redis as soft state. Heartbeats in Postgres is an instant fail signal.",
        "Multi-workspace identity: workspace_id MUST be on every channel/message/file key.",
        "Per-channel cursor for read state, NOT per-message receipts. That's how 50K-member channels work.",
        "Notifications only on mentions/DMs/threads — never every message.",
    ],
    thought_process=[
        "1. Clarify trust model: server-trusted (NOT E2EE). Unlocks search, retention, integrations.",
        "2. Multi-tenancy: workspace_id on every key; isolation enforced at the data layer.",
        "3. Read shape: channel timeline. → per-channel append-only log + cursor pagination.",
        "4. Threads: same log with thread_ts pointing at parent; denormalize reply_count on parent.",
        "5. Fan-out: WS push for currently-viewing sockets; pull on open for everyone else.",
        "6. Presence: Redis heartbeats, privacy filter at read.",
        "7. Search: Elasticsearch per-workspace; ACL filter at query time via channel-member set.",
        "8. Read state: per-(user, channel) cursor, lazy unread count, eager mention count.",
        "9. Notifications: only mentions/DMs/keywords → APNS/FCM.",
        "10. Files: direct-to-S3 with ACL bound to channels.",
        "11. Integrations: workspace-scoped bot tokens; same /messages API; rate-limited.",
        "12. Multi-workspace user: global users + per-workspace memberships with display_name/role.",
        "13. Compliance: retention job, legal hold, eDiscovery export.",
    ],
    tags=["chat", "workplace", "channels", "threads", "real-time"],
    arch_nodes=[
        {"id": "client", "label": "Web/Desktop/Mobile Clients", "type": "client"},
        {"id": "edge", "label": "Edge Gateway (TLS, WS)", "type": "lb"},
        {"id": "conn", "label": "Connection Manager", "type": "service"},
        {"id": "channel", "label": "Channel Service", "type": "server"},
        {"id": "thread", "label": "Thread Service", "type": "server"},
        {"id": "react", "label": "Reaction Service", "type": "server"},
        {"id": "read", "label": "Read State Service", "type": "server"},
        {"id": "presence", "label": "Presence (Redis)", "type": "cache"},
        {"id": "search", "label": "Search (Elasticsearch)", "type": "database"},
        {"id": "notif", "label": "Notification Service", "type": "service"},
        {"id": "files", "label": "File Service + S3", "type": "service"},
        {"id": "integ", "label": "Integration Platform", "type": "service"},
        {"id": "id", "label": "Identity / Directory", "type": "service"},
        {"id": "msgdb", "label": "Postgres / Vitess (sharded by workspace)", "type": "database"},
        {"id": "kafka", "label": "Kafka Bus", "type": "queue"},
        {"id": "push", "label": "APNS / FCM", "type": "service"},
    ],
    arch_edges=[
        {"source": "client", "target": "edge"},
        {"source": "edge", "target": "conn", "label": "WSS"},
        {"source": "edge", "target": "channel", "label": "REST"},
        {"source": "channel", "target": "msgdb", "label": "append/query"},
        {"source": "channel", "target": "kafka", "label": "message-events"},
        {"source": "thread", "target": "msgdb"},
        {"source": "react", "target": "msgdb"},
        {"source": "read", "target": "msgdb"},
        {"source": "kafka", "target": "conn", "label": "fan-out"},
        {"source": "conn", "target": "client", "label": "ws push"},
        {"source": "kafka", "target": "search", "label": "index"},
        {"source": "kafka", "target": "notif", "label": "mentions"},
        {"source": "notif", "target": "push"},
        {"source": "client", "target": "presence", "label": "heartbeat"},
        {"source": "client", "target": "files", "label": "upload/download"},
        {"source": "integ", "target": "channel", "label": "bot posts"},
        {"source": "integ", "target": "notif", "label": "events api"},
        {"source": "id", "target": "channel", "label": "membership/ACL"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant A as Alice (client)\n"
        "  participant E as Edge/WS\n"
        "  participant C as Channel Svc\n"
        "  participant DB as Postgres\n"
        "  participant K as Kafka\n"
        "  participant CM as Conn Mgr\n"
        "  participant S as Search\n"
        "  participant N as Notify\n"
        "  participant B as Bob (online)\n"
        "  A->>E: POST /messages (text='hi @bob', client_msg_id)\n"
        "  E->>C: send (workspace, channel, user)\n"
        "  C->>C: ACL check\n"
        "  C->>DB: INSERT (ws, ch, ts, ...)\n"
        "  C->>K: emit message-event\n"
        "  C-->>A: 200 {ts}\n"
        "  K->>CM: fan-out\n"
        "  CM->>B: ws push (channel msg)\n"
        "  K->>S: index doc\n"
        "  K->>N: parse mentions -> @bob\n"
        "  N->>B: APNS push if backgrounded"
    ),
    er_diagram=(
        "erDiagram\n"
        "  WORKSPACE ||--o{ CHANNEL : contains\n"
        "  WORKSPACE ||--o{ MEMBERSHIP : has\n"
        "  USER ||--o{ MEMBERSHIP : joins\n"
        "  CHANNEL ||--o{ CHANNEL_MEMBER : has\n"
        "  CHANNEL ||--o{ MESSAGE : holds\n"
        "  MESSAGE ||--o{ REACTION : tagged\n"
        "  MESSAGE ||--o{ MESSAGE : thread_replies\n"
        "  USER ||--o{ READ_STATE : tracks\n"
        "  CHANNEL ||--o{ READ_STATE : per_user\n"
        "  WORKSPACE ||--o{ APP_INSTALL : installs\n"
        "  MESSAGE { bigint workspace_id\n bigint channel_id\n bigint ts\n bigint thread_ts\n bigint user_id\n text text }\n"
        "  READ_STATE { bigint user_id\n bigint channel_id\n bigint last_read_ts\n int mention_count }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B{E2EE?}\n"
        "  B -->|No, server-trusted| C[Server-side store]\n"
        "  C --> D[Per-channel append log]\n"
        "  D --> E{Threads?}\n"
        "  E --> F[thread_ts on same log]\n"
        "  D --> G{Channel size?}\n"
        "  G -->|Huge| H[Lazy fan-out to viewers]\n"
        "  G -->|Small| I[Push to all sockets]\n"
        "  C --> J[Search: ES + ACL at query time]\n"
        "  C --> K[Presence: Redis soft state]\n"
        "  C --> L[Read state: per-channel cursor]\n"
        "  C --> M[Notify: mentions only -> APNS/FCM]\n"
        "  C --> N[Multi-workspace: ws_id on every key]"
    ),
    tradeoff_title="Channel Log vs Per-User Inbox",
    tradeoff_options=[
        {"label": "Per-channel append-only log (Slack/Teams)",
         "description": "One canonical message stored once per channel; clients pull by cursor.",
         "pros": [
             "Single source of truth — search, retention, eDiscovery trivial",
             "Write amplification = 1 per message regardless of channel size",
             "Integrations and bots naturally read/write the same log",
             "Cursor pagination is the perfect index for channel UX",
         ],
         "cons": [
             "Requires server to be trusted with plaintext (no E2EE)",
             "Offline delivery needs cursor + lazy pull, not auto-push",
             "Fan-out to 100K-member channels needs lazy push strategy",
         ]},
        {"label": "Per-user/per-device inbox (WhatsApp/Signal)",
         "description": "Each recipient gets their own ciphertext envelope queued.",
         "pros": [
             "Required for E2EE — server can't read content",
             "Offline delivery is natural — pop from queue on connect",
             "Per-recipient receipts are easy",
         ],
         "cons": [
             "Write amplification O(N) per send — explodes at channel size 1000+",
             "No server-side search; compliance/eDiscovery need client-side cooperation",
             "Bots/webhooks awkward — every integration is another 'device' to fan out to",
         ]},
    ],
    tradeoff_rec=(
        "Per-channel log for Slack/Teams. The server is trusted by design (enterprise contracts "
        "require eDiscovery, retention, integrations) — once you accept that, the inbox model "
        "becomes pure overhead. Pick the inbox model only when E2EE is a product requirement."
    ),
    senior_topics=[
        _topic("channel-log-vs-inbox",
               "Why a Channel Log, Not a Per-User Inbox",
               "The data-model decision that separates server-trusted chat from E2EE chat.",
               [
                   ("The thinking trap",
                    "Engineers who designed WhatsApp/Signal first reach for a per-device inbox. "
                    "It's the right answer when the server can't read the message. It is the "
                    "wrong answer when the server CAN read — you've taken on O(N) write "
                    "amplification for nothing."),
                   ("What the channel log buys you",
                    "Search becomes a server problem (Elasticsearch reads the log). Retention is "
                    "a single DELETE pass per workspace. Integrations are first-class — a bot is "
                    "just an authenticated client posting to the same /messages endpoint. "
                    "Compliance/eDiscovery export is one query."),
                   ("What you give up",
                    "Confidentiality from the operator. You compensate with encryption at rest, "
                    "strong access control, audit logs, and contractual commitments — which is "
                    "exactly what Slack/Teams sell to enterprises."),
                   ("Hybrid is rarely worth it",
                    "Some products try to bolt E2EE channels on top of a server-trusted core. "
                    "You lose search and bots in those channels and confuse the UX. Pick one."),
               ]),
        _topic("threads-on-the-log",
               "Threads: A Pointer, Not a Separate Store",
               "How to model threads, reply counts, and thread subscriptions cheaply.",
               [
                   ("Schema",
                    "thread_ts is a nullable column on the messages table pointing at the "
                    "parent's ts. NULL = top-level channel message. Reading a thread is a "
                    "single index range scan on (workspace, channel, thread_ts, ts)."),
                   ("Denormalize for the channel UI",
                    "The channel timeline shows 'N replies, last reply 3m ago' on the parent. "
                    "Maintain reply_count and last_reply_ts on the parent row, updated "
                    "atomically with each reply insert (or via a Kafka consumer)."),
                   ("Subscription model",
                    "Users 'subscribe' to threads they participate in; subscriptions are a "
                    "separate small table. New replies fan out to the channel viewers (counter "
                    "bump) AND to thread subscribers (full message)."),
                   ("Anti-pattern",
                    "Don't model threads as a separate 'thread channel' that mirrors a sub-log. "
                    "It double-writes, doubles the search index, and complicates ACL."),
               ],
               diagram=(
                   "graph TD\n"
                   "  M1[parent msg ts=1700] --> R1[reply ts=1701, thread_ts=1700]\n"
                   "  M1 --> R2[reply ts=1715, thread_ts=1700]\n"
                   "  M1 --> R3[reply ts=1740, thread_ts=1700]\n"
                   "  M1 -.-> M1c[parent.reply_count=3]\n"
                   "  M1 -.-> M1l[parent.last_reply_ts=1740]"
               )),
        _topic("search-acl-at-query-time",
               "Cross-Workspace Search with ACL at Query Time",
               "Why permission filtering belongs in the query, not the index.",
               [
                   ("The naive approach: per-user index",
                    "Build a separate index per user containing only the channels they can read. "
                    "Bankrupt at scale: a 50K-member workspace = 50K nearly-identical indexes, "
                    "and channel membership changes (add user → reindex everything they can now read)."),
                   ("The right approach: workspace index + filter",
                    "One Elasticsearch index per workspace (sharded for big ones). At query time, "
                    "the search service computes the user's readable channel set "
                    "(memberships ∪ public channels) and adds it as a terms filter. "
                    "Membership churn doesn't touch the index."),
                   ("Caching the readable set",
                    "For users in workspaces with tens of thousands of channels, computing the "
                    "readable set on every query is expensive. Cache it in Redis with a short "
                    "TTL (~60s) and invalidate on membership change events."),
                   ("Edge cases",
                    "Private channels: filter must include them only when the user is a member. "
                    "Archived channels: searchable by default if the user was a member at archive. "
                    "Ex-members: typically lose access to history — filter excludes them."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant U as User\n"
                   "  participant API as Search API\n"
                   "  participant R as Redis\n"
                   "  participant ES as Elasticsearch\n"
                   "  U->>API: q='budget' workspace=acme\n"
                   "  API->>R: get readable_channels(user, ws)\n"
                   "  R-->>API: [c1,c2,c5,c9,...]\n"
                   "  API->>ES: query(q) AND channel_id IN [...]\n"
                   "  ES-->>API: top hits\n"
                   "  API-->>U: results"
               )),
        _topic("presence-at-scale",
               "Presence at Workspace Scale (Active / Away / DND)",
               "Soft-state in Redis, with batched reads and privacy filtering.",
               [
                   ("Heartbeats",
                    "Each WebSocket sends a heartbeat every ~30s to its Connection Manager, which "
                    "writes presence:{workspace_id}:{user_id} → {device_id: ts} into Redis with "
                    "an expiry. Online iff any device heartbeat is <60s old."),
                   ("Subscriptions",
                    "When Alice opens a channel, her client wants presence for the visible members. "
                    "Don't make N round-trips: batch into one MGET. For larger lists, the client "
                    "subscribes to a 'presence-changed' pub/sub topic per workspace and only refetches "
                    "for users whose state actually changed."),
                   ("Privacy",
                    "User setting: visible to {everyone | contacts | nobody}. Enforced at read by "
                    "joining the membership table. The Redis store does NOT carry privacy logic — "
                    "keeping it dumb is what lets it stay fast."),
                   ("DND vs away",
                    "DND is an explicit user state with a schedule (e.g. 9pm-8am). It overrides "
                    "automatic away inference and suppresses notifications. Critically: DND lives "
                    "in the user_settings table (durable), NOT in Redis."),
               ]),
        _topic("read-state-and-unreads",
               "Read State and Unreads Without Per-Recipient Receipts",
               "How to do badge counts and 'where did I leave off' for 50K-member channels.",
               [
                   ("Per-channel cursor, not per-message",
                    "read_state(user_id, channel_id) → last_read_ts. One row per (user, channel) "
                    "you have ever joined. Updates only when YOU read; not when others send. "
                    "O(channels per user) state, NOT O(messages × members)."),
                   ("Lazy unread count",
                    "Don't increment a counter on every send to every member — that's O(N) per "
                    "message. Instead, the client computes 'unread count' for each open channel "
                    "as a range query: SELECT count(*) FROM messages WHERE channel = X AND ts > "
                    "last_read_ts. Cache the result in the client; refresh on focus."),
                   ("Mention count is eager (and worth it)",
                    "Mentions are sparse — only a handful of users per message. Maintain "
                    "mention_count in read_state by emitting a per-mentioned-user event from the "
                    "Notification Service. This makes the badge UX cheap and instant."),
                   ("Why not per-message receipts",
                    "Per-recipient 'seen' UI in a 50K-member #general would require 50K writes per "
                    "message read — a write storm with no UX value at that scale. Slack/Teams "
                    "deliberately do not show 'seen by' for channels for this reason."),
               ]),
        _topic("multi-workspace-identity",
               "Multi-Workspace User Identity",
               "One human, many memberships — without leaking data across workspaces.",
               [
                   ("Schema",
                    "Global users table holds the human (email, password, MFA, devices). "
                    "memberships(user_id, workspace_id, role, display_name, is_guest, joined_at) "
                    "is the per-workspace identity. Display name and avatar can differ per "
                    "workspace; the email cannot (it's the join key)."),
                   ("Isolation rule",
                    "Every channel/message/file/reaction key includes workspace_id. The data layer "
                    "rejects cross-workspace joins. ACL checks always scope by both user and "
                    "workspace. This is what makes guest access in Workspace B safe even if the "
                    "user is admin in Workspace A."),
                   ("Shared channels",
                    "When two workspaces share a channel (Slack Connect / Teams shared channels), "
                    "the channel record carries TWO workspace_ids and a federation table tracks "
                    "the partnership. Messages still write once (to a primary workspace) and the "
                    "other workspace's members are granted read via a shared-channel-membership "
                    "rule. ACL gets more complex; the workspace_id-on-every-key invariant still holds."),
                   ("Auth", "SSO/SAML configured per workspace; SCIM provisioning per workspace. A user "
                            "may have password+MFA on the global user record AND SAML at one "
                            "particular workspace — the login flow picks the strictest applicable."),
               ]),
        _topic("integrations-bots-webhooks",
               "Integration Platform: Bots, Webhooks, Slash Commands",
               "Why everything funnels through the same /messages API and what changes.",
               [
                   ("Apps and scopes",
                    "An app declares scopes (channels:read, chat:write, files:read, ...). A "
                    "workspace admin installs the app via OAuth, granting those scopes. The app "
                    "receives a workspace-scoped bot token and a bot user identity that appears "
                    "in member lists like a human."),
                   ("Bots post like users",
                    "Bot writes via POST /messages with bearer = bot token. Same code path as "
                    "humans; same ACL checks. This is why your bot's posts are searchable, "
                    "exportable, and threadable for free."),
                   ("Slash commands and interactivity",
                    "User types /deploy in a channel → API gateway POSTs a signed payload "
                    "(team_id, channel_id, user_id, text) to the app's HTTPS endpoint. App "
                    "responds with a message or opens a modal. HMAC over the body using the "
                    "app's signing secret prevents spoofing."),
                   ("Events API (outgoing webhooks)",
                    "Apps subscribe to events (message.channels, reaction_added, …). Notification "
                    "Service POSTs matching events to the app's URL with HMAC. Retries with "
                    "exponential backoff; circuit-breaks misbehaving apps; per-app rate limits "
                    "enforce ~1 msg/sec/channel + burst budget."),
                   ("Why this design scales",
                    "The integration layer is just authenticated clients of the same API. We don't "
                    "build a parallel write path for bots — that's how a single API surface ends "
                    "up powering 10K third-party apps without per-app code."),
               ]),
        _topic("compliance-retention-ediscovery",
               "Retention, Legal Hold, and eDiscovery",
               "Server-trust unlocks compliance — and you have to actually deliver it.",
               [
                   ("Retention policy",
                    "Per-workspace setting: retain messages for N days (or forever). A daily "
                    "Spark/Flink job runs per workspace, tombstoning rows past the cutoff. "
                    "Tombstones (deleted_at not NULL, text NULLed) become hard deletes after a "
                    "grace period (e.g. 30d) so accidental misconfig is recoverable."),
                   ("Legal hold",
                    "When legal hold is set on a (workspace, user|channel) scope, retention jobs "
                    "skip those rows even if past the cutoff. The hold is metadata; deletion "
                    "queries respect it."),
                   ("eDiscovery export",
                    "Admin queries via web UI: by user, channel, date range, keyword. Service "
                    "pushes matching messages + linked files to a customer-controlled S3 bucket "
                    "as JSON. Includes edit/delete history (since tombstones preserve metadata) "
                    "and DM contents the admin is authorized to view."),
                   ("Audit log",
                    "Every admin action (export, retention change, member removal, scope grant) "
                    "writes an audit-log row with actor, action, target, timestamp. Audit log is "
                    "append-only and can itself be exported."),
               ]),
    ],
)
