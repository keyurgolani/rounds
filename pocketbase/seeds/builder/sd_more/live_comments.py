from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design Live Comments / Stadium-Style Reactions",
    "Hard",
    "Design the real-time chat and reactions experience that sits next to a livestream — the "
    "Twitch chat next to a top-tier streamer, the YouTube Live chat under a major event, the "
    "TikTok Live comments column, the Facebook/Instagram Live reactions ticker. The product "
    "looks deceptively simple: a scrolling list of short messages and floating heart/clap "
    "reactions next to a video. The systems problem is brutal: a single popular stream can "
    "have 1M+ concurrent viewers, message rate spikes from 100 to 50K msgs/sec in seconds when "
    "something dramatic happens on-screen, every viewer expects every message it can render to "
    "show up within ~2 seconds, and the entire fan-out runs at stadium scale across dozens of "
    "regions. Beyond the raw delivery, the product has heavy moderation needs: spam/abuse "
    "detection inline (NOT post-hoc — toxic messages must die before fan-out), slow mode and "
    "emote-only mode triggered by mods or auto-mod, sub-only chat tied to subscription state, "
    "pinned messages and announcements that override the scroll, hosts/raids/timeouts/bans, "
    "VIP and moderator badges, channel-point redemptions and bits/cheers as message metadata, "
    "and a recording + replay path so VOD viewers see chat synchronized with playback. The "
    "stadium-reactions side adds a different shape: heart/clap/laugh reactions are extremely "
    "high-cardinality, low-information events (one user might tap heart 30 times in 5 seconds) "
    "where individual delivery does not matter — only the aggregate visual density matters. "
    "Treat them like analytics, not chat.",
    hints=[
        "Two distinct workloads share the page: chat (every message matters, ordering matters) "
        "and reactions (only aggregate matters; individual taps are lossy). Don't mix them.",
        "WebSocket is the right transport for chat. Long-poll is a graceful fallback for clients "
        "behind weird proxies, not the primary path.",
        "Shard chat by channel_id, NOT by user_id. The hot-spot is one channel with 1M viewers, "
        "not one user across many channels. Pin a hot channel to a dedicated cluster.",
        "Backpressure: under spike, drop OLD messages, not new ones. Viewers want recency over "
        "completeness. A 5-second-old message no one read is worthless.",
        "Spam/abuse detection runs INLINE before fan-out. A toxic message that reaches 1M people "
        "for 2 seconds before retraction is unrecoverable PR damage. Latency budget for moderation "
        "is ~50ms.",
        "Reactions are aggregated server-side: per-channel counter buckets at 100ms or 1s "
        "resolution. Clients receive aggregate frames, not individual taps.",
        "Fan-out tree, not flat fan-out. One ingest server cannot push to 1M sockets. Use a "
        "two-level (or three-level) tree: ingest → regional dispatchers → edge socket holders.",
        "End-to-end latency target <2s viewer-to-viewer. Most of that is fan-out tree + WebSocket "
        "frame, not the database write.",
    ],
    constraints=[
        "1M+ concurrent viewers per top-tier livestream; 100K+ concurrent live channels globally",
        "Chat rate: bursty 100-50K msgs/sec on a hot channel; long-tail channels run at 1-100/sec",
        "Reaction rate: 100K+ taps/sec on a single hot channel during a spike",
        "End-to-end p99 viewer-to-viewer latency < 2s for chat",
        "Inline moderation latency budget < 50ms (added to send path)",
        "Message size cap (~500 chars text; emotes resolved server-side)",
        "VOD replay must reconstruct chat synchronized to video playhead within ~1s accuracy",
        "Cost: a long-tail channel with 5 viewers must be near-free per message",
    ],
    req_func=[
        "Real-time text chat next to live video, scoped per channel/stream",
        "Floating reactions (heart, clap, laugh) aggregated by type, delivered as density frames",
        "Slow mode: minimum N seconds between messages per user",
        "Emote-only mode: reject non-emote messages",
        "Sub-only mode: only subscribers may post",
        "Moderator actions: timeout, ban, delete message, clear chat, lock channel",
        "Pinned message / channel announcement at top of chat",
        "Inline spam, abuse, and rate-limit detection (auto-mod) before fan-out",
        "Badges: subscriber, moderator, VIP, broadcaster, channel-point holders",
        "Channel-point redemptions, bits/cheers, and host/raid notifications surface in chat",
        "Recording: persist chat events with playhead offsets for VOD replay",
        "Replay: reconstruct chat scrolled to a given video timestamp",
        "Mobile + web client support; WebSocket primary, long-poll fallback",
    ],
    req_nonfunc=[
        "End-to-end chat latency p99 < 2s viewer-to-viewer at 1M-viewer scale",
        "Inline auto-mod adds < 50ms p99 to send path",
        "Reaction aggregation frame cadence 100ms-1s; never individual deliveries to clients",
        "Backpressure under spike: drop oldest queued, never new; never block the producer",
        "Availability: chat is best-effort relative to video — video must NEVER block on chat",
        "Cost-efficient long tail: idle channels with <10 viewers cost ~zero per message",
        "Replay durability: chat for a stream is recoverable for VOD retention period (90 days+)",
        "Compliance: per-region data residency for moderation audit logs",
    ],
    estimation={
        "concurrent_streams": "~100K live globally",
        "concurrent_viewers_top_stream": "~1M",
        "concurrent_viewers_global": "~50M",
        "chat_msg_rate_top_stream_peak": "~50K msgs/sec",
        "chat_msg_rate_global_avg": "~500K msgs/sec",
        "reaction_rate_top_stream_peak": "~200K taps/sec",
        "fan_out_amplification_top": "1 msg in × 1M sockets out = 1B frames/sec at peak channel",
        "messages_per_day": "~50B chat messages",
        "reactions_per_day": "~5T taps (aggregated to ~5B frames after bucketing)",
        "storage_chat_per_day": "~50B × ~200 bytes = ~10TB/day raw, ~3TB compressed",
    },
    endpoints=[
        {"method": "GET", "path": "/v1/channels/{ch}/connect",
         "description": "Bootstrap WebSocket: returns regional ws_url + initial recent-messages snapshot + channel state (slow mode, emote-only, sub-only)"},
        {"method": "POST", "path": "/v1/channels/{ch}/messages",
         "description": "Send a chat message; server-assigned ts and seq",
         "body": "{client_msg_id, text, parent_msg_id?}"},
        {"method": "POST", "path": "/v1/channels/{ch}/reactions",
         "description": "Send a reaction tap (heart, clap, laugh, etc.). High-frequency, idempotent-best-effort.",
         "body": "{reaction_type, count?}"},
        {"method": "POST", "path": "/v1/channels/{ch}/mode",
         "description": "Mod/broadcaster sets slow mode, emote-only, sub-only, or clears them",
         "body": "{slow_mode_seconds?, emote_only?, sub_only?, followers_only_minutes?}"},
        {"method": "POST", "path": "/v1/channels/{ch}/moderation",
         "description": "Mod actions: timeout, ban, unban, delete message, clear chat",
         "body": "{action, target_user_id?, target_msg_id?, duration_seconds?, reason?}"},
        {"method": "POST", "path": "/v1/channels/{ch}/pin",
         "description": "Pin a message as channel announcement",
         "body": "{msg_id, expires_at?}"},
        {"method": "GET", "path": "/v1/vod/{vod_id}/chat",
         "description": "Replay chat for a VOD; returns events near a given playhead",
         "body": "{playhead_seconds, window_seconds, limit, cursor}"},
    ],
    tables=[
        {"name": "channels",
         "columns": ["id BIGINT PK", "broadcaster_user_id BIGINT", "title TEXT",
                     "is_live BOOL", "started_at BIGINT", "current_stream_id BIGINT"]},
        {"name": "streams",
         "columns": ["id BIGINT PK", "channel_id BIGINT", "started_at BIGINT",
                     "ended_at BIGINT", "vod_id BIGINT NULL"]},
        {"name": "chat_messages",
         "columns": ["stream_id BIGINT", "seq BIGINT", "ts BIGINT",
                     "user_id BIGINT", "text TEXT", "badges_json JSONB",
                     "emotes_json JSONB", "deleted_at BIGINT NULL",
                     "PRIMARY KEY (stream_id, seq)"]},
        {"name": "reaction_buckets",
         "columns": ["stream_id BIGINT", "bucket_ts BIGINT",
                     "reaction_type VARCHAR(16)", "count BIGINT",
                     "PRIMARY KEY (stream_id, bucket_ts, reaction_type)"]},
        {"name": "channel_modes",
         "columns": ["channel_id BIGINT PK", "slow_mode_seconds INT",
                     "emote_only BOOL", "sub_only BOOL",
                     "followers_only_minutes INT", "updated_at BIGINT"]},
        {"name": "moderation_actions",
         "columns": ["id BIGINT PK", "channel_id BIGINT", "actor_user_id BIGINT",
                     "target_user_id BIGINT NULL", "target_msg_id BIGINT NULL",
                     "action VARCHAR(16)", "duration_seconds INT NULL",
                     "reason TEXT", "created_at BIGINT"]},
        {"name": "user_channel_state",
         "columns": ["user_id BIGINT", "channel_id BIGINT",
                     "is_subscriber BOOL", "is_moderator BOOL", "is_vip BOOL",
                     "banned_until BIGINT NULL", "follow_started_at BIGINT NULL",
                     "PRIMARY KEY (user_id, channel_id)"]},
        {"name": "pinned_messages",
         "columns": ["channel_id BIGINT PK", "msg_id BIGINT",
                     "pinned_by BIGINT", "expires_at BIGINT NULL"]},
    ],
    indexes=[
        "(stream_id, seq) on chat_messages — VOD replay scan",
        "(stream_id, ts) on chat_messages — playhead-anchored seek",
        "(stream_id, bucket_ts) on reaction_buckets — replay aggregation",
        "(channel_id, created_at DESC) on moderation_actions",
        "(user_id, channel_id) on user_channel_state — sub/mod/VIP lookup on send",
        "Hot channels pinned to dedicated Redis Streams keyed by channel_id",
    ],
    hld_desc=(
        "The architecture splits the page into two pipelines that share nothing on the hot path. "
        "Chat: clients open a WebSocket to a regional Edge socket holder. Sends go through an "
        "Ingest service that does auth, rate-limit, channel-mode check, inline auto-mod (toxicity, "
        "spam, regex banlist, link filter) within a 50ms budget, then assigns a per-stream seq + "
        "ts and writes the message into a per-channel Redis Stream (or Kafka partition keyed by "
        "channel_id). A two- or three-level Fan-out Tree consumes the stream: a Coordinator per "
        "hot channel, regional Dispatchers (one per region), and Edge socket holders that own "
        "the actual TCP sockets and push the frame. Cold (long-tail) channels skip the tree and "
        "use direct fan-out from a small worker pool. Reactions: clients send to a separate "
        "Reaction Aggregator that bucketizes by (channel, reaction_type) into 100ms-1s windows, "
        "writes counters, and publishes density frames into the same fan-out tree. Persistence: "
        "an async writer drains chat to a partitioned chat-archive store (Cassandra/ScyllaDB or "
        "Postgres-sharded) keyed by (stream_id, seq) for VOD replay, and a downsampling job rolls "
        "reaction buckets to coarser resolution for retention. Moderation: mod actions go through "
        "the same Ingest path, replicate to the channel-state cache used by every Edge for "
        "client-side enforcement (e.g. greying out a banned user's avatar), and emit retraction "
        "frames into the fan-out tree to scrub deleted messages from in-memory client buffers."
    ),
    hld_components=[
        {"name": "Edge Socket Holder", "role": "TLS, WebSocket, holds 1M+ sockets per region; pushes frames"},
        {"name": "Ingest Service", "role": "Auth, rate-limit, channel-mode check, seq/ts assignment"},
        {"name": "Auto-Mod Pipeline", "role": "Inline toxicity, spam, regex banlist, link filter (<50ms)"},
        {"name": "Channel Stream (Redis/Kafka)", "role": "Per-channel ordered log of messages and mod events"},
        {"name": "Fan-out Coordinator", "role": "Per-hot-channel orchestrator; assigns dispatchers per region"},
        {"name": "Regional Dispatcher", "role": "Mid-tier of fan-out tree; one per region per hot channel"},
        {"name": "Reaction Aggregator", "role": "Bucketizes taps by (channel, type, time window); emits density frames"},
        {"name": "Channel State Cache", "role": "Slow-mode, emote-only, sub-only, ban list, pinned msg — read by every Edge"},
        {"name": "Chat Archive Writer", "role": "Drains stream to durable store with playhead offsets for VOD"},
        {"name": "VOD Replay Service", "role": "Reads archive; serves chat windows synchronized to playhead"},
        {"name": "Moderation Audit Log", "role": "Append-only record of every mod action for compliance"},
        {"name": "Mode Control Service", "role": "Slow/emote-only/sub-only/follower-only state + propagation"},
    ],
    detailed_design={
        "transport_and_socket_holder": (
            "WebSocket is primary. Each region runs a fleet of Edge socket holders sized for "
            "100K-500K sockets per process (epoll/kqueue with careful memory budget — ~10KB per "
            "idle socket). Long-poll is a fallback for clients behind hostile middleboxes; the "
            "Edge presents both as a single subscription abstraction. Connect: client hits a "
            "regional load balancer with channel_id hint, gets routed to an Edge that's already "
            "subscribed to that channel's fan-out (consistent hashing on channel_id within "
            "region). On connect the Edge sends an initial snapshot: last ~50 messages, current "
            "channel mode (slow/emote-only/sub-only), pinned message, and the user's own mod "
            "state. After that, it streams frames as they arrive."
        ),
        "send_path_and_inline_automod": (
            "POST /messages → API gateway → Ingest. Ingest does (1) auth and per-user rate "
            "limit (token bucket in Redis, e.g. 100 msgs/30s), (2) channel-mode enforcement "
            "(slow_mode_seconds since this user's last message; sub_only requires subscriber "
            "flag; emote_only parses message and rejects if non-emote chars present; "
            "followers_only requires follow_started_at older than threshold), (3) inline "
            "Auto-Mod: parallel calls to a regex banlist, link filter, and a small toxicity "
            "model with a 30ms timeout — anything over budget is allowed-with-flag, never "
            "blocked. (4) Assign per-stream monotonic seq + server ts. (5) Write into the "
            "channel's Redis Stream. (6) Return 200 to the sender with seq. Total p99 budget: "
            "<150ms including round trips."
        ),
        "fanout_tree": (
            "A flat fan-out from one ingest server to 1M sockets does not work — kernel and "
            "NIC limits make it pathological. The tree: (1) Channel Stream is the root — one "
            "Redis Stream or Kafka partition per channel. (2) The Fan-out Coordinator for a "
            "hot channel subscribes to the stream once and assigns Regional Dispatchers (one "
            "per region with viewers). (3) Each Regional Dispatcher subscribes to the "
            "Coordinator and re-publishes to the Edge socket holders in its region that have "
            "viewers on this channel. (4) Each Edge holds a per-channel viewer list (sockets) "
            "and writes the frame to each. The branching factor at each level is tuned so that "
            "no node pushes to more than ~10K consumers; for 1M viewers split across 8 regions "
            "with 100K sockets per Edge, the tree is depth 3. Cold channels (<1K viewers) skip "
            "the tree and use a single dispatcher pool."
        ),
        "backpressure_and_drop_policy": (
            "Under spike, the bottleneck is the Edge → socket fan-out. Each Edge has per-socket "
            "send buffers (~16KB). When a buffer is full, we DROP from the FRONT — the oldest "
            "queued frame — and continue. Viewers want recent messages; a stale message is "
            "useless. Reactions density frames carry their own drop tolerance: dropping one "
            "frame just slightly understates density for 100ms — invisible to viewers. We "
            "expose a per-Edge metric drops/sec and auto-scale on it. Clients receive an "
            "occasional 'gap' marker when their read-side buffer overflows, prompting a soft "
            "snapshot refresh."
        ),
        "reactions_aggregation": (
            "Reactions are NOT chat. A user mashing the heart button at 30 taps/sec generates "
            "noise that nobody needs delivered individually. Pipeline: client sends batched "
            "POSTs (e.g. {type:'heart', count: 12} every 200ms). Reaction Aggregator buckets "
            "by (channel_id, reaction_type, floor(ts/100ms)) into a sharded in-memory counter "
            "(per-channel keyed sharding). Every 100ms-1s the aggregator emits one density "
            "frame per channel per active reaction type into the fan-out tree, which delivers "
            "it as a numeric counter ('167 hearts in last 100ms'). The client renders this as "
            "floating animations whose density is proportional to the count. Persistence "
            "writes coarser buckets (1s and 1m rollups) for VOD replay; raw 100ms buckets "
            "expire after 60s."
        ),
        "channel_modes_and_enforcement": (
            "Slow mode, emote-only, sub-only, followers-only are channel-level state cached at "
            "every Edge in a Channel State Cache (Redis with local LRU on each Edge for ~1ms "
            "reads). Mods/broadcaster set modes via Mode Control Service, which writes Postgres "
            "+ Redis and emits a 'mode-changed' frame into the channel stream so all Edges "
            "refresh and clients update UI ('Slow mode: 30s'). Enforcement on send is at Ingest "
            "(reject with structured error). Enforcement on display: Edges also use channel "
            "state to decide whether a message should show (e.g. emote-only mode active mid-"
            "burst — reject after the fact, retract via a delete frame)."
        ),
        "moderation_actions": (
            "Timeout/ban/delete-message/clear-chat go through the same Ingest path with a mod-"
            "action endpoint. Effects: (a) ban writes to user_channel_state.banned_until and "
            "the Channel State Cache; subsequent sends from that user are rejected at Ingest "
            "before auto-mod. (b) Delete-message emits a retraction frame in the fan-out tree; "
            "Edges and clients scrub the seq from local buffers and the archive marks it "
            "deleted_at NOT NULL with original text retained for audit. (c) Clear-chat sends "
            "a single bulk-clear frame; clients reset their visible buffer. All mod actions "
            "are appended to moderation_actions for compliance and to the Moderation Audit "
            "Log (immutable, exportable for legal)."
        ),
        "subscriber_and_badges": (
            "Subscriber/VIP/Mod state is derived from the subscription/membership service and "
            "cached in user_channel_state per (user, channel). Badges_json is computed at send "
            "time and stored on the message so the visual is stable even if the user later "
            "loses sub status. Channel-point redemptions and bits/cheers are events emitted "
            "by their own services that ride the channel stream as 'system' messages with "
            "type=cheer/redemption — same fan-out path, different render in the client."
        ),
        "pinned_messages": (
            "Pin is a per-channel single-slot pointer (msg_id) with optional expires_at. Edges "
            "include the pinned message in the connect snapshot AND maintain it in their per-"
            "channel state so it survives reconnects. Pin/unpin emits a frame so existing "
            "viewers update their UI."
        ),
        "vod_replay": (
            "While the stream is live, the Chat Archive Writer drains the channel stream to a "
            "partitioned chat archive (Cassandra/ScyllaDB keyed by (stream_id, seq)) and stamps "
            "each row with a playhead_offset_ms relative to stream start. When the broadcaster "
            "ends the stream, the channel record links a vod_id; the chat archive is now "
            "queryable as VOD chat. Replay query: GET /vod/{id}/chat?playhead=120s&window=10s "
            "returns the chat events whose playhead_offset_ms falls in the window. Reactions "
            "use the 1s rolled-up buckets for replay (raw 100ms is too granular and short-"
            "lived). The replay path is read-only and served from a separate read-replica "
            "fleet so it can't impact live."
        ),
        "long_tail_efficiency": (
            "100K live channels but most have <100 viewers. Spinning up a Coordinator + "
            "Dispatcher tree per channel is wasteful. Cold-channel mode: a small Worker pool "
            "subscribes to a multiplexed Cold Channel Stream (one Kafka topic with hashed "
            "partition by channel_id) and pushes directly to the Edges that have any viewers "
            "for those channels. A channel auto-promotes to its own dedicated stream when "
            "viewer count crosses a threshold (e.g. 5K) and demotes back when it drops."
        ),
        "regional_isolation_and_failover": (
            "Each region runs a full Edge fleet + Regional Dispatcher pool. The Channel Stream "
            "is geo-replicated for hot channels to a primary + 2 standby regions; if the "
            "primary fails, the Coordinator fails over and Dispatchers re-subscribe. Worst-"
            "case viewer impact: a 5-10s gap with a 'reconnecting' indicator. Video and chat "
            "are independent — chat outage never blocks the video player."
        ),
        "slo_contract": (
            "Send→fan-out p99 <2s viewer-to-viewer at 1M scale. Auto-mod p99 <50ms added. "
            "Mod action propagation <1s globally. Reaction frame cadence 100ms-1s; density "
            "drift bounded to <5% in steady state. VOD replay window query p99 <300ms. Chat "
            "availability 99.9% per region; video availability is independent and unaffected "
            "by chat outages."
        ),
    },
    trade_offs=[
        {"option": "Flat fan-out vs Fan-out tree",
         "for_flat": "Simple; fewer hops; works fine to ~10K viewers",
         "for_tree": "Required at 100K+ viewers; bounded branching factor; survives single-node failure",
         "recommendation": "Tree for hot channels (>5K viewers); flat for the long tail. Auto-promote on threshold."},
        {"option": "Drop oldest vs Drop newest under backpressure",
         "for_oldest": "Viewers see freshest messages; stale msgs are useless",
         "for_newest": "Preserves order; never reorders",
         "recommendation": "Drop oldest — recency >> completeness for live chat. Mod actions are an exception (must deliver)."},
        {"option": "Individual reaction events vs Aggregated density frames",
         "for_individual": "Pixel-perfect rendering; per-user attribution",
         "for_aggregate": "1000× less bandwidth; matches what users actually perceive",
         "recommendation": "Aggregate — reactions are a vibe meter, not chat. Individual events scale O(viewers × tap rate)."},
        {"option": "Inline auto-mod vs Async post-hoc moderation",
         "for_inline": "Toxic messages never reach viewers",
         "for_async": "Lower send latency; cheaper",
         "recommendation": "Inline with strict timeout. Toxic msg reaching 1M viewers for 2s is unrecoverable."},
        {"option": "WebSocket vs Server-Sent Events vs Long-poll",
         "for_websocket": "Bidirectional, low overhead, native browser support",
         "for_sse": "Simpler, server→client only, auto-reconnect built in",
         "recommendation": "WebSocket primary (need bidirectional for sends + acks); long-poll as fallback for hostile networks."},
        {"option": "Per-channel dedicated stream vs Shared multiplexed stream",
         "for_dedicated": "Isolation; hot channel can't starve others",
         "for_shared": "Cheap for the long tail of small channels",
         "recommendation": "Hybrid — dedicated for hot channels (>5K viewers), shared multiplexed for the long tail."},
    ],
    tips=[
        "Open with the dichotomy: chat (every message matters, ordered) vs reactions (only aggregate matters). They share NO hot-path infra.",
        "1M viewers is the headline number. Lead with the fan-out tree — flat fan-out is an instant fail signal.",
        "Drop OLD messages under backpressure, not new ones. State this explicitly — it's the senior signal.",
        "Inline auto-mod with a hard <50ms timeout. A toxic message reaching viewers is the worst possible outcome.",
        "Reactions as analytics: bucket-aggregate server-side, deliver density frames at 100ms-1s. NEVER deliver individual taps.",
        "Hot channels get dedicated stream + tree; long tail goes through a shared multiplexed pool. Auto-promote on viewer threshold.",
        "VOD replay is a separate read path against a partitioned archive keyed by (stream_id, seq). Never query the live store.",
        "Chat is best-effort relative to video. The video player must NEVER block on chat — outage isolation is a product requirement.",
        "Mod actions ride the SAME stream as chat so retractions arrive in order. Don't build a parallel mod path that races messages.",
    ],
    thought_process=[
        "1. Clarify scale: 1M concurrent on one channel; 50K msgs/sec on chat spike; 200K reactions/sec.",
        "2. Identify the two distinct workloads: chat (ordered, every-msg) vs reactions (aggregate density).",
        "3. Transport: WebSocket with long-poll fallback. Shard by channel_id.",
        "4. Send path: auth → rate-limit → channel-mode check → inline auto-mod (<50ms) → seq/ts → channel stream.",
        "5. Fan-out tree: stream → Coordinator → Regional Dispatcher → Edge socket holder. Bounded branching factor at each level.",
        "6. Backpressure: drop OLD frames when buffers fill. Recency > completeness.",
        "7. Reactions: bucket server-side, emit density frames at 100ms-1s. Treat as analytics.",
        "8. Modes (slow/emote-only/sub-only) cached at every Edge; enforced at Ingest on send.",
        "9. Mod actions through same path → retraction frames in fan-out tree → clients scrub buffers.",
        "10. Hot vs cold: dedicated tree for >5K viewer channels; multiplexed pool for long tail. Auto-promote.",
        "11. VOD replay: archive keyed by (stream_id, seq) with playhead offsets; separate read fleet.",
        "12. Failure isolation: chat outage never blocks video. Cross-region failover for hot channel streams.",
    ],
    tags=["livestream", "chat", "real-time", "fan-out", "moderation", "high-cardinality"],
    arch_nodes=[
        {"id": "client", "label": "Web/Mobile Viewer Client", "type": "client"},
        {"id": "lb", "label": "Regional LB / WS Gateway", "type": "lb"},
        {"id": "edge", "label": "Edge Socket Holder", "type": "service"},
        {"id": "ingest", "label": "Ingest Service", "type": "server"},
        {"id": "automod", "label": "Auto-Mod Pipeline", "type": "service"},
        {"id": "stream", "label": "Channel Stream (Redis/Kafka)", "type": "queue"},
        {"id": "coord", "label": "Fan-out Coordinator", "type": "service"},
        {"id": "disp", "label": "Regional Dispatcher", "type": "service"},
        {"id": "react", "label": "Reaction Aggregator", "type": "service"},
        {"id": "modes", "label": "Channel State Cache", "type": "cache"},
        {"id": "mod", "label": "Mode Control / Moderation", "type": "server"},
        {"id": "archive", "label": "Chat Archive (Cassandra)", "type": "database"},
        {"id": "writer", "label": "Archive Writer", "type": "service"},
        {"id": "vod", "label": "VOD Replay Service", "type": "service"},
        {"id": "audit", "label": "Moderation Audit Log", "type": "database"},
    ],
    arch_edges=[
        {"source": "client", "target": "lb"},
        {"source": "lb", "target": "edge", "label": "WSS"},
        {"source": "lb", "target": "ingest", "label": "REST send"},
        {"source": "ingest", "target": "automod", "label": "<50ms check"},
        {"source": "ingest", "target": "modes", "label": "mode/ban check"},
        {"source": "ingest", "target": "stream", "label": "append seq/ts"},
        {"source": "stream", "target": "coord", "label": "consume"},
        {"source": "coord", "target": "disp", "label": "per-region"},
        {"source": "disp", "target": "edge", "label": "frame"},
        {"source": "edge", "target": "client", "label": "ws push"},
        {"source": "client", "target": "react", "label": "tap batches"},
        {"source": "react", "target": "stream", "label": "density frames"},
        {"source": "mod", "target": "stream", "label": "mod-action"},
        {"source": "mod", "target": "modes", "label": "update"},
        {"source": "mod", "target": "audit", "label": "audit row"},
        {"source": "stream", "target": "writer", "label": "drain"},
        {"source": "writer", "target": "archive"},
        {"source": "vod", "target": "archive", "label": "playhead query"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant V as Viewer (sender)\n"
        "  participant LB as Regional LB\n"
        "  participant I as Ingest\n"
        "  participant AM as Auto-Mod\n"
        "  participant S as Channel Stream\n"
        "  participant C as Coordinator\n"
        "  participant D as Regional Dispatcher\n"
        "  participant E as Edge\n"
        "  participant V2 as Viewer (receiver, 1 of 1M)\n"
        "  V->>LB: POST /messages (text='LFG!!')\n"
        "  LB->>I: send (channel, user, text)\n"
        "  I->>I: rate-limit, mode check, ban check\n"
        "  I->>AM: inline check (30ms timeout)\n"
        "  AM-->>I: clean\n"
        "  I->>S: append (seq, ts, msg)\n"
        "  I-->>V: 200 {seq}\n"
        "  S->>C: new frame\n"
        "  C->>D: fan-out per region\n"
        "  D->>E: push frame\n"
        "  E->>V2: ws frame (msg)\n"
        "  Note over E,V2: < 2s viewer-to-viewer p99"
    ),
    er_diagram=(
        "erDiagram\n"
        "  CHANNEL ||--o{ STREAM : runs\n"
        "  STREAM ||--o{ CHAT_MESSAGE : contains\n"
        "  STREAM ||--o{ REACTION_BUCKET : aggregates\n"
        "  CHANNEL ||--|| CHANNEL_MODES : configured_by\n"
        "  CHANNEL ||--o{ MODERATION_ACTION : has\n"
        "  USER ||--o{ USER_CHANNEL_STATE : in\n"
        "  CHANNEL ||--o{ USER_CHANNEL_STATE : has\n"
        "  CHANNEL ||--|| PINNED_MESSAGE : pins\n"
        "  CHAT_MESSAGE { bigint stream_id\n bigint seq\n bigint ts\n bigint user_id\n text text\n bigint deleted_at }\n"
        "  REACTION_BUCKET { bigint stream_id\n bigint bucket_ts\n string reaction_type\n bigint count }\n"
        "  CHANNEL_MODES { bigint channel_id\n int slow_mode_seconds\n bool emote_only\n bool sub_only }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B{Two workloads?}\n"
        "  B -->|Chat| C[Ordered, every-msg]\n"
        "  B -->|Reactions| D[Aggregate density only]\n"
        "  C --> E[Inline auto-mod <50ms]\n"
        "  E --> F[Channel stream + seq/ts]\n"
        "  F --> G{Viewer count?}\n"
        "  G -->|>5K| H[Fan-out tree per channel]\n"
        "  G -->|<5K| I[Multiplexed cold pool]\n"
        "  H --> J[Coord -> Dispatcher -> Edge]\n"
        "  J --> K[WS push to client]\n"
        "  K --> L{Backpressure?}\n"
        "  L -->|Yes| M[Drop OLDEST frame]\n"
        "  D --> N[Bucket 100ms-1s]\n"
        "  N --> O[Density frame -> tree]\n"
        "  F --> P[Archive writer -> VOD replay]\n"
        "  C --> Q[Mod actions -> same stream -> retractions]"
    ),
    tradeoff_title="Fan-out Tree vs Flat Fan-out for 1M Viewers",
    tradeoff_options=[
        {"label": "Flat fan-out from a single ingest server",
         "description": "One process subscribes to the message stream and pushes to every viewer socket directly.",
         "pros": [
             "Trivial to reason about; one hop only",
             "Lowest absolute latency when within capacity",
             "Works fine up to ~10K viewers per channel",
         ],
         "cons": [
             "Hits NIC/CPU/file-descriptor limits at 100K+ sockets per process",
             "Single point of failure — that one server going down kills the channel",
             "Cannot survive multi-region traffic without cross-region pushes (slow + expensive)",
             "Tail latency degrades catastrophically as fan-out approaches process limits",
         ]},
        {"label": "Multi-level fan-out tree (Coordinator -> Regional Dispatcher -> Edge)",
         "description": "Each level has bounded branching factor (~10K consumers max). Tree depth ~3 for 1M viewers across 8 regions.",
         "pros": [
             "Scales linearly — add nodes at any level to grow capacity",
             "Per-region locality — viewers in EU never wait for a US push",
             "Single-node failure affects only its subtree, with re-subscription <1s",
             "Backpressure is local — each level applies its own drop policy",
         ],
         "cons": [
             "More moving parts; failure modes between levels need careful handling",
             "Adds 1-2 hops of latency vs flat (typically <100ms total — fine for the 2s SLO)",
             "Auto-promotion logic for hot channels adds complexity",
             "Needs a Coordinator-election story per channel",
         ]},
    ],
    tradeoff_rec=(
        "Tree for any channel above ~5K viewers; flat (or shared multiplexed pool) for the long "
        "tail. The constant flat-vs-tree question is really 'when do you cross over' — the answer "
        "is 'before you actually need to,' because crossing over under load is harder than "
        "running tree-mode wastefully on a borderline channel. Auto-promote based on observed "
        "viewer count over a 30s window; demote with hysteresis to avoid flapping."
    ),
    senior_topics=[
        _topic("two-workloads-chat-vs-reactions",
               "Why Chat and Reactions Are Two Different Systems",
               "The single most common error is to treat reactions like fast chat. They aren't.",
               [
                   ("Different consistency models",
                    "Chat is ordered, every-message-matters, retractable. Losing a message is a "
                    "user-visible bug. Reactions are unordered, only-aggregate-matters, lossy. "
                    "Losing 5% of taps doesn't affect the visual at all — the floating heart "
                    "density is approximately correct."),
                   ("Different rate shapes",
                    "Chat: 50K msgs/sec peak on a hot channel. Reactions: 200K+ taps/sec. "
                    "Delivering reactions individually would be 4× the chat fan-out for zero "
                    "additional information."),
                   ("Different APIs and storage",
                    "Chat uses POST per message with seq/ts assignment, ordered persistence "
                    "in (stream_id, seq). Reactions use batched POSTs ('20 hearts in last "
                    "200ms') and bucket counters in (stream_id, bucket_ts, type)."),
                   ("Different replay model",
                    "Chat replay must reproduce the exact message stream. Reaction replay only "
                    "needs to reproduce the density curve over time — coarse 1s buckets are "
                    "fine; nobody notices."),
               ]),
        _topic("fanout-tree-construction",
               "Constructing a Fan-out Tree at Stadium Scale",
               "How to push one message to 1M sockets in <2s without melting any single node.",
               [
                   ("Bounded branching factor",
                    "Set a hard ceiling (~10K consumers per node). For 1M viewers across 8 "
                    "regions: root stream -> 1 Coordinator -> 8 Regional Dispatchers -> ~12 "
                    "Edges per region (each holding ~10K sockets) -> 100K sockets at the leaves. "
                    "Tree depth 3."),
                   ("Per-region locality",
                    "Regional Dispatchers subscribe to the Coordinator over private backbone. "
                    "Edge socket holders are in the same region as their viewers. A frame "
                    "traverses cross-region exactly once (Coordinator -> Dispatcher), then stays "
                    "regional."),
                   ("Subscribe vs poll",
                    "Each level uses a long-lived subscription (gRPC stream or Redis Stream "
                    "consumer). No polling. New viewers register with their Edge; the Edge "
                    "doesn't open a new upstream subscription per viewer — it has one upstream "
                    "subscription per channel and adds the viewer to its local subscriber list."),
                   ("Failure handling",
                    "Each consumer holds the last-seen seq. On reconnect after a node failure, "
                    "it resumes from seq+1. The stream retains messages for ~60s of replay "
                    "headroom. Worst case: viewer sees a 1-2s stutter, never a permanent gap."),
                   ("Coordinator election",
                    "Per hot channel, exactly one Coordinator is active (etcd/Zookeeper lease). "
                    "On lease expiry, a standby takes over within ~1s and re-subscribes. "
                    "Dispatchers then re-subscribe to the new Coordinator's address."),
               ],
               diagram=(
                   "graph TD\n"
                   "  S[Channel Stream] --> C[Coordinator]\n"
                   "  C --> D1[Dispatcher US-East]\n"
                   "  C --> D2[Dispatcher EU-West]\n"
                   "  C --> D3[Dispatcher AP-South]\n"
                   "  D1 --> E11[Edge 1 ~100K sockets]\n"
                   "  D1 --> E12[Edge 2 ~100K sockets]\n"
                   "  D1 --> E13[Edge N ...]\n"
                   "  D2 --> E21[Edge ...]\n"
                   "  E11 --> V1[1M viewers total]\n"
                   "  E12 --> V1\n"
                   "  E21 --> V1"
               )),
        _topic("backpressure-drop-old",
               "Backpressure: Drop Oldest, Not Newest",
               "Why live chat backpressure flips the usual queue intuition.",
               [
                   ("The intuitive (wrong) instinct",
                    "Most queueing systems drop the newest arrival when full — preserves the "
                    "work already accepted. For LIVE chat, this is exactly backwards: a 5-"
                    "second-old message is worthless to a viewer; the new one is what they want."),
                   ("Mechanism",
                    "Each socket has a fixed-size send buffer (e.g. 16KB). When write-ready, "
                    "the Edge pops the FRONT of the buffer (oldest) if the buffer was full at "
                    "any point in the last frame. New frames go to the back. Order within "
                    "delivered frames is preserved; only stale frames are sacrificed."),
                   ("What about ordering invariants?",
                    "Chat is causal — within one user's messages, order matters; across users, "
                    "rough ordering is fine. We never reorder within a single seq stream we "
                    "actually deliver; we only drop a contiguous prefix when behind. Clients "
                    "may receive a 'gap' marker indicating dropped seqs."),
                   ("Mod actions are an exception",
                    "Bans, deletes, and clear-chat must NOT be dropped — they fix the visible "
                    "state. The Edge classifies frames; mod-action frames have priority and "
                    "skip the drop policy. Worst case they cause a brief socket-write block, "
                    "which is acceptable for the rare action."),
                   ("Per-Edge metric and autoscaling",
                    "Drops/sec per Edge is a first-class SLI. Sustained drops indicate "
                    "undersized fleet — autoscale on it. Spiky drops during a 50K msg/sec "
                    "burst are expected and tolerable."),
               ]),
        _topic("inline-automod",
               "Inline Auto-Mod with a Hard Latency Budget",
               "Catching toxic content before fan-out without blowing the send-path SLO.",
               [
                   ("The constraint",
                    "Toxicity check must run before the message enters the channel stream. If "
                    "it ran async, a slur would reach 1M viewers for ~2s before retraction — "
                    "operationally and reputationally unrecoverable."),
                   ("Pipeline",
                    "Three checks run in parallel: (1) regex banlist (channel-specific + "
                    "global, ~1ms), (2) link/domain filter against an allowlist (~5ms), "
                    "(3) small toxicity classifier model (distilled BERT-class, ~20ms). "
                    "Hard 30ms timeout on the whole batch; whatever returned in time is "
                    "evaluated, the rest is allowed-with-flag."),
                   ("Decisions",
                    "Three actions: ALLOW (publish), HOLD (publish only to the sender — "
                    "shadowban-style), REJECT (return error to sender). Mods receive a "
                    "separate 'flagged for review' frame for HOLD and ambiguous ALLOW."),
                   ("Channel-specific tuning",
                    "Each channel can configure strictness: e.g. /r/ProgrammerHumor allows "
                    "'kill it with fire' but a kids' streamer's auto-mod blocks 'kill'. "
                    "Banlists and threshold settings are per-channel; the model is shared."),
                   ("Audit and appeal",
                    "Every auto-mod decision is logged with the message text, decision, "
                    "model scores. Senders can see the reason ('your message was held — "
                    "links not allowed in this channel'). Mods can review HOLD'd messages "
                    "in a queue and approve/reject."),
               ]),
        _topic("reactions-as-analytics",
               "Reactions as Analytics, Not Chat",
               "Server-side aggregation that delivers density frames at fixed cadence.",
               [
                   ("The math",
                    "On a hot channel: 1M viewers × 0.5 taps/sec/active-viewer = 500K taps/sec. "
                    "Delivering each individually = 500K events × 1M viewers = 500B frames/sec. "
                    "Aggregated to 1s buckets per reaction type: 1M viewers × 5 types × 1 "
                    "frame/sec = 5M frames/sec. 100,000× cheaper."),
                   ("Aggregator pipeline",
                    "Sharded in-memory counters keyed by (channel_id, type, floor(ts/100ms)). "
                    "On each tick (100ms or 1s, configurable per channel based on activity), "
                    "the aggregator emits one density frame per (channel, type) into the same "
                    "fan-out tree as chat. Counters reset after emit."),
                   ("Client rendering",
                    "Density frame says '167 hearts in last 100ms'. Client renders ~167 "
                    "floating hearts at random positions; viewers perceive 'lots of hearts'. "
                    "If the next frame is 5, only ~5 new hearts spawn. The aggregate density "
                    "matches the global feeling."),
                   ("Long-tail efficiency",
                    "On a small channel with 50 viewers tapping occasionally, the aggregator "
                    "can drop to 1s cadence or skip emit when count==0. No fixed cost for "
                    "idle channels."),
                   ("Replay and persistence",
                    "Persist 1s and 1m rollups to the archive. Raw 100ms buckets expire after "
                    "60s. VOD replay uses 1s buckets — viewers can't perceive 100ms granularity "
                    "on a recorded video anyway."),
               ]),
        _topic("hot-vs-cold-channels",
               "Hot Channels vs the Long Tail: Hybrid Topology",
               "Most channels are tiny. Most concurrent viewers are on a few channels. Optimize for both.",
               [
                   ("The bimodal load",
                    "100K live channels but 80% of concurrent viewers are on the top 1% of "
                    "channels. A naive per-channel architecture wastes resources on the tail; "
                    "a naive shared architecture starves the head."),
                   ("Hot path",
                    "Channels above ~5K viewers get a dedicated Channel Stream, dedicated "
                    "Coordinator, and a fan-out tree with regional dispatchers. Resources "
                    "scale with viewer count via Edge auto-scaling."),
                   ("Cold path",
                    "Channels below threshold share a Multiplexed Cold Stream — one Kafka "
                    "topic with hashed partitions by channel_id. A small Worker pool consumes "
                    "and pushes directly to the Edges that have any viewers for those channels. "
                    "Per-message overhead is amortized across thousands of small channels."),
                   ("Auto-promotion and demotion",
                    "Promote a channel from cold to hot when its 30s viewer-count window "
                    "crosses 5K. Promotion: spin up a dedicated Coordinator, migrate the "
                    "channel's stream from the multiplexed pool to a dedicated stream, redirect "
                    "Edges to subscribe to the new stream. Brief 200ms cutover where in-flight "
                    "messages are double-delivered (de-duped client-side by seq). Demote with "
                    "hysteresis (e.g. drop only if <2K viewers for 5 minutes) to avoid flapping."),
                   ("Cost outcome",
                    "A channel with 5 viewers costs ~$0.0001/hour for chat. A channel with "
                    "1M viewers costs ~$50/hour. Both are economically viable on a single "
                    "platform."),
               ]),
        _topic("mod-actions-on-the-same-stream",
               "Mod Actions Ride the Chat Stream",
               "Why deletes, bans, and clear-chat go through the same pipeline as messages.",
               [
                   ("The race condition you avoid",
                    "If mod actions go through a parallel path, a delete-msg can race the "
                    "original message and arrive at viewers BEFORE the message itself — "
                    "viewers see no delete, then see the offending message persist. By "
                    "appending mod actions to the same channel stream, ordering is "
                    "guaranteed end-to-end."),
                   ("Frame types",
                    "The stream carries a tagged union: msg, reaction-density, mod-delete, "
                    "mod-ban, mod-clear, mode-change, pin, system. Edges and clients dispatch "
                    "on the type. Each frame has a seq from the same monotonic stream."),
                   ("Client behavior",
                    "On mod-delete{seq=X}, the client looks up X in its visible buffer and "
                    "removes (or replaces with '<deleted>'). On mod-ban{user_id=U}, the client "
                    "greys all messages from U currently visible and refuses to render "
                    "subsequent ones. On mod-clear, the client wipes its visible chat buffer."),
                   ("Server-side cleanup",
                    "Auto-Mod and the archive writer also see the mod-delete and update "
                    "their stores: archive sets deleted_at=ts, audit log records "
                    "(actor, action, target, original_text). Original text is retained for "
                    "compliance; only the user-visible representation is hidden."),
               ]),
        _topic("vod-replay-architecture",
               "VOD Chat Replay Synchronized to Playhead",
               "How recorded-video viewers see the chat that was happening when each moment was live.",
               [
                   ("Persistence shape",
                    "Chat Archive Writer drains the channel stream while live, writing to a "
                    "partitioned table keyed by (stream_id, seq). Each row has playhead_offset_ms "
                    "= ts_msg - stream_started_at. This makes 'give me chat near playhead 120s' "
                    "an indexed range query."),
                   ("Storage choice",
                    "Cassandra/ScyllaDB or partitioned Postgres. Wide-row per stream: partition "
                    "key stream_id, clustering on seq. Hot streams (currently live) sit in a "
                    "write-heavy tier; old streams roll to a read-optimized tier."),
                   ("Replay query path",
                    "GET /vod/{id}/chat?playhead=120000ms&window=10000ms&limit=200. Service "
                    "binary-searches by playhead_offset_ms or scans seq range; returns events. "
                    "Reactions queried separately with the 1s bucket index."),
                   ("Read isolation",
                    "VOD replay traffic is served from a separate read-replica fleet. Live "
                    "chat is never impacted by replay load. Caching layer (Redis with TTL) "
                    "in front of the most-replayed VODs."),
                   ("Synchronization",
                    "The video player emits playhead updates every ~1s. The chat replay "
                    "client maintains a sliding window of events around the playhead, "
                    "scrolling at the same rate as the video. Seek (jump in playhead) "
                    "triggers a fresh window query."),
               ]),
        _topic("availability-isolation-from-video",
               "Chat Outage Must Never Block Video",
               "The product invariant that constrains the architecture more than any latency SLO.",
               [
                   ("Why it matters",
                    "Viewers are watching the video FIRST. If chat is broken but video plays, "
                    "users tolerate it. If video is broken because chat broke, users leave. "
                    "Chat can be best-effort; video cannot."),
                   ("Architectural enforcement",
                    "Chat services run on entirely separate infrastructure from video CDN/"
                    "transcoding/origin. No shared dependencies on the hot path. Even auth "
                    "tokens for chat are issued by a chat-only token service so an auth "
                    "outage doesn't ripple."),
                   ("Player behavior",
                    "Video player initializes chat lazily, with timeout. If the chat WS "
                    "fails to connect within ~3s, the player shows a 'chat unavailable' "
                    "indicator and continues video. Chat reconnects in the background."),
                   ("Graceful degradation modes",
                    "Read-only chat (drop send capability), no-reactions (when reaction "
                    "aggregator is down), polling fallback (when WS infrastructure is "
                    "stressed). Each mode is a documented degraded state, not an outage."),
                   ("Disaster scenarios",
                    "Whole-region chat outage: regional failover for hot channel streams; "
                    "viewers reconnect to alternate region within ~30s. Worst case: 1-2 "
                    "minute chat blackout while clients reconnect. Video unaffected."),
               ]),
    ],
)
