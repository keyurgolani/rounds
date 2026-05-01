from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design WhatsApp / Messenger",
    "Hard",
    "Design a globally distributed mobile-first chat platform supporting 1:1 and group messaging "
    "(up to ~1000 members), real-time delivery, online/last-seen presence, typing indicators, "
    "media (photos, videos, voice notes), and end-to-end encryption by default. Target ~2B monthly "
    "active users producing ~100B messages/day with strict mobile constraints: flaky cellular links, "
    "battery and bandwidth budgets, and hours-long offline windows. The hard problems are durable "
    "low-latency delivery over long-lived connections, key management for E2EE at group scale, "
    "and multi-device sync without ever exposing plaintext to the server.",
    hints=[
        "Mobile-first: persistent connection cost (battery/radio) is a real constraint — coalesce.",
        "E2EE means the server is a dumb relay for ciphertext. Search/spam/abuse work differently.",
        "Group fan-out at 1000 members must NOT be O(N) AES re-encryptions per message — sender keys.",
        "Push notifications (APNS/FCM) wake the app for offline delivery; payload is encrypted blob.",
        "Last-seen / presence is a privacy + scale problem; soft-state in Redis, not the message store.",
        "Multi-device sync: the senior signal is 'each device is its own E2EE identity', not 'share keys'.",
    ],
    constraints=[
        "Mobile clients: cellular, intermittent, battery-budgeted",
        "End-to-end encrypted by default — server never sees plaintext",
        "Groups up to ~1000 members; 1:1 dominant by volume",
        "p50 delivery <500ms when both peers online; p99 <2s",
        "Offline window up to 30 days — messages must persist until delivered",
        "Multi-device: phone + up to 4 linked devices (web/desktop/tablet)",
    ],
    req_func=[
        "Send/receive 1:1 messages with delivered + read receipts",
        "Group chat send/receive with per-member receipts",
        "Online presence and last-seen (privacy-respecting)",
        "Typing indicators (ephemeral, best-effort)",
        "Media upload (photo, video, voice) with encrypted blobs on a CDN",
        "Push notification to wake app for offline delivery",
        "Multi-device link/unlink; companion devices receive history",
        "End-to-end encryption for 1:1 and groups by default",
        "Message history sync on new device (encrypted backup or device-to-device transfer)",
        "Block, mute, leave-group; delete-for-everyone within a window",
    ],
    req_nonfunc=[
        "p50 in-app delivery <500ms; p99 <2s when both online",
        "Availability 99.99% globally; regional failover",
        "Scale: ~2B MAU, ~100B msgs/day, ~10M concurrent sockets/region",
        "Confidentiality: server cannot read plaintext (E2EE)",
        "Durability: undelivered messages retained ≥30 days, zero loss",
        "Bandwidth/battery efficient: heartbeat tuned, payloads compressed",
    ],
    estimation={
        "mau": "~2B",
        "concurrent_sockets": "~500M peak globally; ~10M per region",
        "messages_per_day": "~100B (avg ~50/user/day)",
        "qps_steady": "~1.2M msgs/sec; peak ~3M msgs/sec",
        "media_per_day": "~7B objects, avg 200KB → ~1.4PB/day to CDN",
        "storage_inbox": "~100B msgs × 200B avg envelope ≈ 20TB/day; TTL 30d ≈ 600TB hot",
    },
    endpoints=[
        {"method": "WS", "path": "/ws (TLS, persistent)",
         "description": "Long-lived bidirectional channel; frames: SEND, ACK, RECEIPT, PRESENCE, TYPING, PING",
         "body": "{type, msg_id, conv_id, ciphertext, sender_device_id, ts}"},
        {"method": "POST", "path": "/v1/messages",
         "description": "HTTP fallback when WS unavailable; idempotent via client msg_id",
         "body": "{conv_id, recipients:[{user_id, device_id, ciphertext}], media_ref?}"},
        {"method": "GET", "path": "/v1/messages?since={token}",
         "description": "Pull undelivered envelopes for this device since sync token"},
        {"method": "POST", "path": "/v1/keys/prekeys",
         "description": "Upload identity key + signed prekey + one-time prekeys (X3DH bundle)"},
        {"method": "GET", "path": "/v1/keys/{user_id}/{device_id}",
         "description": "Fetch peer prekey bundle to start a Signal session"},
        {"method": "POST", "path": "/v1/media/upload-url",
         "description": "Get presigned PUT URL for encrypted media blob; returns media_ref + decryption hint"},
        {"method": "POST", "path": "/v1/groups/{gid}/members",
         "description": "Add/remove member; triggers sender-key rotation client-side"},
        {"method": "POST", "path": "/v1/devices/link",
         "description": "Link a companion device via QR-code-bound ephemeral key exchange"},
        {"method": "POST", "path": "/v1/presence",
         "description": "Heartbeat/away signal; soft-state in Redis"},
        {"method": "POST", "path": "/v1/push/register",
         "description": "Register APNS/FCM token bound to (user_id, device_id)"},
    ],
    tables=[
        {"name": "users",
         "columns": ["user_id BIGINT PK", "phone_e164 VARCHAR(20) UNIQUE",
                     "display_name VARCHAR(64)", "created_at BIGINT"]},
        {"name": "devices",
         "columns": ["device_id VARCHAR(64) PK", "user_id BIGINT", "platform VARCHAR(16)",
                     "push_token TEXT", "identity_pub BYTEA", "last_seen_at BIGINT",
                     "linked_at BIGINT"]},
        {"name": "prekeys",
         "columns": ["device_id VARCHAR(64)", "key_id INT", "prekey_pub BYTEA",
                     "is_signed BOOL", "consumed_at BIGINT", "PRIMARY KEY (device_id, key_id)"]},
        {"name": "conversations",
         "columns": ["conv_id BIGINT PK", "kind VARCHAR(8)  -- 'dm' or 'group'",
                     "group_meta JSONB", "created_at BIGINT"]},
        {"name": "conversation_members",
         "columns": ["conv_id BIGINT", "user_id BIGINT", "role VARCHAR(16)",
                     "joined_at BIGINT", "PRIMARY KEY (conv_id, user_id)"]},
        {"name": "inbox",
         "columns": ["device_id VARCHAR(64)", "seq BIGINT", "envelope BYTEA  -- ciphertext",
                     "received_at BIGINT", "PRIMARY KEY (device_id, seq)"]},
        {"name": "media_refs",
         "columns": ["media_id VARCHAR(64) PK", "owner_user_id BIGINT", "cdn_url TEXT",
                     "size_bytes BIGINT", "encryption_hint BYTEA", "expires_at BIGINT"]},
    ],
    indexes=[
        "(device_id, seq DESC) on inbox  -- pull undelivered",
        "(user_id) on devices  -- fan-out target lookup",
        "(device_id, consumed_at) on prekeys  -- pick unused prekey",
        "(conv_id) on conversation_members  -- group membership",
    ],
    hld_desc=(
        "Edge POPs terminate TLS and hold persistent WebSockets; an Edge Gateway maps "
        "(user_id, device_id) → owning Connection Server in the home region. The Message Router "
        "writes a per-device inbox row (ciphertext envelope) and pushes via the live socket if "
        "online, else queues an APNS/FCM wake. Identity/Key Service serves Signal X3DH prekey "
        "bundles. Media is uploaded encrypted to object storage fronted by a CDN — message "
        "service only carries the media_ref + symmetric key (encrypted to recipients). Presence "
        "and typing live in Redis as soft-state with TTL."
    ),
    hld_components=[
        {"name": "Edge POP / WS Termination", "role": "TLS, persistent socket, PING/PONG, region pin"},
        {"name": "Connection Manager", "role": "Routes (user, device) → owning shard; maintains presence table"},
        {"name": "Message Router", "role": "Fan-out per recipient device; writes inbox; triggers push"},
        {"name": "Inbox Store", "role": "Per-device durable queue of ciphertext envelopes (Cassandra/Bigtable)"},
        {"name": "Key Service", "role": "X3DH prekey bundles, identity keys, sender-key distribution helpers"},
        {"name": "Media Service + CDN", "role": "Presigned uploads of encrypted blobs; geo CDN egress"},
        {"name": "Push Gateway", "role": "APNS/FCM wake-ups for offline devices"},
        {"name": "Presence Service", "role": "Redis soft-state: online, typing, last-seen with privacy filter"},
    ],
    detailed_design={
        "transport_websocket_vs_persistent_tcp": (
            "Use TLS WebSocket on 443: NAT-friendly, proxy-tolerant, sub-second handshake with "
            "TLS 1.3 + 0-RTT resumption. Client maintains one socket; PING tuned to ~5min on Wi-Fi, "
            "longer on cellular to spare radio. On disconnect, client falls back to HTTPS pull "
            "(/v1/messages?since=) with exponential backoff. Raw TCP is rejected — middleboxes drop it."
        ),
        "e2ee_signal_protocol": (
            "Each device has a long-lived identity key + signed prekey + a pool of one-time prekeys "
            "uploaded to the Key Service. New session uses X3DH (4-DH key agreement) to derive a "
            "shared secret; subsequent messages use the Double Ratchet for forward secrecy and "
            "post-compromise security (each message advances the chain). Server stores only "
            "ciphertext envelopes — it never holds session state or plaintext."
        ),
        "group_fanout_sender_keys": (
            "Naive per-recipient pairwise encryption is O(N) and breaks at 1000 members. Instead, "
            "each sender maintains a 'sender key' (symmetric chain key) per group; the sender key "
            "is delivered to each member ONCE via their pairwise Signal session. Subsequent group "
            "messages are encrypted once with the sender key and broadcast — server fan-out is "
            "O(N) network writes but O(1) crypto. Membership change → rotate sender key."
        ),
        "inbox_model": (
            "Per-device inbox (NOT per-conversation log) is the source of truth for delivery. "
            "When user A sends to group G with members [B,C,D] each having 2 devices, router writes "
            "6 inbox rows. Device pulls by monotonically increasing seq and ACKs; row deleted on ACK "
            "(or after 30d TTL). This is necessary for E2EE: each device has its own session "
            "and ciphertext."
        ),
        "presence_and_last_seen": (
            "Redis hash: presence:{user_id} → {device_id: last_heartbeat_ts}. Aggregated 'online' "
            "iff any device heartbeat within 60s. Last-seen is a privacy setting (everyone / "
            "contacts / nobody) enforced at read time. Typing is a fire-and-forget WS frame to "
            "online recipients only — never persisted."
        ),
        "media_pipeline": (
            "Client generates a random symmetric key K, AES-GCM encrypts the blob, uploads "
            "ciphertext to CDN-fronted object store via presigned URL, then sends the chat "
            "message containing only {media_ref, K_encrypted_to_each_recipient_session}. The "
            "media service has no access to K and cannot decrypt. CDN egress handles the heavy "
            "bandwidth; chat path stays lightweight."
        ),
        "push_notifications": (
            "On inbox write where target device offline, enqueue APNS/FCM wake. Payload is "
            "minimal ('You have a message') OR an encrypted notification extension that the "
            "device decrypts locally to render sender + preview. Server NEVER sends plaintext "
            "preview through APNS — would leak to Apple/Google."
        ),
        "multi_device_sync": (
            "Each linked device is its own cryptographic identity with its own prekeys — the "
            "phone does NOT share its private keys with web/desktop. New device pairs via "
            "QR-code-bound key exchange; the primary device transfers historical message "
            "ciphertext (or an encrypted snapshot) directly. Going forward, every send fan-outs "
            "to all of the recipient's devices AND all of the sender's other devices (self-echo)."
        ),
    },
    trade_offs=[
        {"option": "WebSocket over TLS vs persistent raw TCP/MQTT",
         "for_websocket": "443 traverses every middlebox; HTTP/2/3 multiplexing; standard auth",
         "for_mqtt_tcp": "Smaller frames, lower battery in theory",
         "recommendation": "WebSocket. Real-world cellular wins; battery delta is marginal with tuned PING."},
        {"option": "Per-conversation log vs per-device inbox",
         "for_log": "Simpler search, single source of truth, group-friendly",
         "for_inbox": "Each device pulls own ciphertext; matches E2EE session model exactly",
         "recommendation": "Per-device inbox. E2EE forces it; logs only viable for un-encrypted systems."},
        {"option": "Pairwise group encryption vs sender keys",
         "for_pairwise": "Simplest; reuses 1:1 Signal session unchanged",
         "for_sender_keys": "O(1) crypto per send regardless of group size",
         "recommendation": "Sender keys for groups >~10. Distribute the sender key over pairwise sessions."},
        {"option": "Encrypted backup vs device-to-device history transfer",
         "for_backup": "Survives device loss; uses iCloud/Google Drive",
         "for_p2p": "Never trusts third-party cloud; user controls keys",
         "recommendation": "Optional encrypted backup with user-held passphrase + P2P transfer at link."},
        {"option": "Read receipts always-on vs user-toggleable",
         "for_on": "Clear UX, fewer settings",
         "for_toggle": "Privacy; users want plausible deniability",
         "recommendation": "User-toggle, mutual: if you disable, you don't see others' either."},
    ],
    tips=[
        "Open with: 'mobile-first, E2EE by default, server is a ciphertext relay.' Sets the right frame.",
        "Distinguish 1:1 (Double Ratchet) from groups (Sender Keys). Most candidates conflate.",
        "Inbox-per-device is the senior signal — it falls out of E2EE, not the other way around.",
        "Multi-device = each device is its own identity. Do NOT propose sharing private keys.",
        "Mention APNS/FCM payload privacy: server cannot put plaintext in push.",
        "Don't overspend on Signal internals — name X3DH + Double Ratchet, then move on.",
        "Capacity-estimate sockets, not just messages: 10M concurrent sockets per region is the harder number.",
    ],
    thought_process=[
        "1. Clarify: 1:1 + groups, E2EE default, mobile-first, presence, multi-device.",
        "2. Estimate: 2B MAU → 100B msgs/day → ~1-3M msg/s, 10M concurrent sockets/region.",
        "3. Transport: WS over TLS:443 (middlebox-friendly) + HTTP pull fallback + APNS/FCM wake.",
        "4. E2EE: Signal — X3DH session setup, Double Ratchet for forward secrecy.",
        "5. Storage: per-device inbox of ciphertext envelopes (Cassandra), TTL 30d.",
        "6. Groups: sender keys to avoid O(N) crypto; rotate on membership change.",
        "7. Media: encrypt client-side, upload to CDN, send only media_ref + per-recipient-encrypted key.",
        "8. Presence/typing: Redis soft-state, TTL'd, privacy-filtered at read.",
        "9. Multi-device: each device its own identity; companion linking via QR.",
        "10. Failure modes: socket churn, prekey exhaustion, group-key rotation storms.",
    ],
    tags=["chat", "messaging", "e2ee", "mobile", "real-time"],
    arch_nodes=[
        {"id": "phone", "label": "Mobile App", "type": "client"},
        {"id": "edge", "label": "Edge POP / WS", "type": "lb"},
        {"id": "conn", "label": "Connection Mgr", "type": "server"},
        {"id": "router", "label": "Message Router", "type": "server"},
        {"id": "inbox", "label": "Inbox Store", "type": "database"},
        {"id": "keys", "label": "Key Service (X3DH)", "type": "service"},
        {"id": "media", "label": "Media + CDN", "type": "cache"},
        {"id": "push", "label": "APNS / FCM", "type": "service"},
        {"id": "presence", "label": "Presence (Redis)", "type": "cache"},
    ],
    arch_edges=[
        {"source": "phone", "target": "edge", "label": "WSS:443"},
        {"source": "edge", "target": "conn"},
        {"source": "conn", "target": "router"},
        {"source": "router", "target": "inbox", "label": "envelope per device"},
        {"source": "router", "target": "push", "label": "wake offline"},
        {"source": "phone", "target": "keys", "label": "prekey bundle"},
        {"source": "phone", "target": "media", "label": "encrypted blob"},
        {"source": "conn", "target": "presence", "label": "heartbeat"},
        {"source": "push", "target": "phone"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant A as Alice (phone)\n"
        "  participant E as Edge WS\n"
        "  participant R as Router\n"
        "  participant I as Inbox\n"
        "  participant P as APNS/FCM\n"
        "  participant B as Bob (phone)\n"
        "  A->>E: SEND {conv, ciphertext}\n"
        "  E->>R: route by recipient device\n"
        "  R->>I: append envelope (Bob.dev1)\n"
        "  alt Bob online\n"
        "    R->>B: deliver via WS\n"
        "    B-->>R: ACK\n"
        "  else Bob offline\n"
        "    R->>P: wake notification\n"
        "    P-->>B: push\n"
        "    B->>E: GET /messages?since=\n"
        "    E-->>B: envelopes\n"
        "  end\n"
        "  B-->>A: RECEIPT delivered\n"
    ),
    er_diagram=(
        "erDiagram\n"
        "  USER ||--o{ DEVICE : owns\n"
        "  DEVICE ||--o{ PREKEY : publishes\n"
        "  DEVICE ||--o{ INBOX : receives\n"
        "  CONVERSATION ||--o{ MEMBER : has\n"
        "  USER ||--o{ MEMBER : participates\n"
        "  DEVICE { string device_id\n bigint user_id\n bytea identity_pub\n string push_token }\n"
        "  INBOX { string device_id\n bigint seq\n bytea envelope }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B[E2EE default]\n"
        "  B --> C{Transport}\n"
        "  C --> D[WSS:443 + HTTP fallback]\n"
        "  B --> E[Per-device inbox of ciphertext]\n"
        "  E --> F{Group?}\n"
        "  F -->|Yes| G[Sender keys, rotate on membership]\n"
        "  F -->|No| H[Double Ratchet pairwise]\n"
        "  E --> I[Offline -> APNS/FCM wake]\n"
        "  B --> J[Multi-device = independent identities]"
    ),
    tradeoff_title="Group Encryption Strategy",
    tradeoff_options=[
        {"label": "Pairwise per-recipient encryption",
         "description": "Encrypt the message N times, once per recipient session.",
         "pros": ["Reuses 1:1 Signal session as-is", "Simplest membership churn"],
         "cons": ["O(N) crypto per send — breaks at 1000 members", "Battery + CPU heavy on sender"]},
        {"label": "Sender keys (symmetric chain per sender per group)",
         "description": "One symmetric key, distributed once over pairwise sessions; messages encrypted once.",
         "pros": ["O(1) crypto per send", "Scales to 1000+ groups"],
         "cons": ["Must rotate sender key on every membership change", "More moving parts"]},
    ],
    tradeoff_rec="Sender keys for groups >~10; pairwise for 1:1. Distribute sender key over pairwise Double Ratchet.",
    senior_topics=[
        _topic("signal-x3dh-double-ratchet",
               "Signal: X3DH + Double Ratchet (just enough)",
               "End-to-end encryption with forward secrecy and post-compromise security. "
               "X3DH bootstraps the session asynchronously; Double Ratchet advances per message.",
               [
                   ("X3DH session setup",
                    "Sender fetches recipient's {identity_key, signed_prekey, one_time_prekey} "
                    "bundle from server. Performs 3 or 4 Diffie-Hellman operations and combines "
                    "them via HKDF into an initial shared secret. Works while recipient is offline."),
                   ("Double Ratchet",
                    "Each message advances a symmetric chain key (KDF ratchet) AND, on every "
                    "round-trip, performs a new DH (DH ratchet). Result: forward secrecy "
                    "(past messages safe if current key leaks) + post-compromise security "
                    "(future messages safe after a leak heals)."),
                   ("Server's role",
                    "Server holds prekey bundles and ciphertext envelopes only. It cannot read, "
                    "modify undetectably, or replay messages without breaking the MAC."),
                   ("Why not just TLS?",
                    "TLS protects client↔server. We need client↔client, with the server explicitly "
                    "untrusted for content. Different threat model."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant A as Alice\n  participant S as Server\n  participant B as Bob\n"
                   "  B->>S: upload prekey bundle\n"
                   "  A->>S: fetch Bob's bundle\n"
                   "  A->>A: X3DH -> shared secret\n"
                   "  A->>S: ciphertext (DR msg 1)\n"
                   "  S->>B: deliver\n"
                   "  B->>B: derive same secret, decrypt\n"
                   "  Note over A,B: Subsequent msgs ratchet"
               )),
        _topic("group-sender-keys",
               "Sender Keys for Group E2EE Fan-out",
               "How to encrypt a message ONCE for a group of 1000 without leaking forward secrecy.",
               [
                   ("The naive approach fails",
                    "Pairwise-encrypt to each member: O(N) AES + O(N) network. At 1000 members and "
                    "thousands of sends/sec/server, CPU and bandwidth blow up."),
                   ("Sender key construction",
                    "Each sender, per group, derives a symmetric chain key. Sends are AES-GCM "
                    "with that key; the key advances via KDF per message (forward secrecy within "
                    "the chain)."),
                   ("Distributing the sender key",
                    "Wrap the current sender-key state inside each pairwise Double Ratchet session "
                    "and ship once per recipient. After that, plaintext fan-out is a single "
                    "ciphertext blast to N recipients."),
                   ("Membership churn",
                    "Add: existing senders distribute current state to new member. Remove: every "
                    "sender rotates their sender key and re-distributes — otherwise the removed "
                    "member could still derive future keys."),
               ]),
        _topic("inbox-vs-log",
               "Per-Device Inbox vs Per-Conversation Log",
               "Why E2EE forces an inbox model and what you give up.",
               [
                   ("E2EE precludes a shared log",
                    "A per-conversation log assumes the server can append once and let everyone "
                    "read. With E2EE, every recipient device has its own ciphertext (different "
                    "session keys). There is no single canonical encrypted blob."),
                   ("Inbox semantics",
                    "Per-device queue indexed by (device_id, monotonic seq). Client pulls forward, "
                    "ACKs, server deletes. TTL fallback (~30d) for never-acked messages."),
                   ("Cost",
                    "Write amplification: a 1000-member group send = up to 4000 inbox writes "
                    "(4 devices/user). Mitigation: idempotent writes, batch within shard, "
                    "compress envelopes."),
                   ("Why this is OK",
                    "Reads dominate writes in chat, and most reads are 'pull my last K' on a "
                    "single device — the inbox is the perfect index for that."),
               ]),
        _topic("multi-device-identity",
               "Multi-Device: Each Device Is Its Own Identity",
               "Avoid the temptation to 'share keys across devices' — it breaks the security model.",
               [
                   ("Wrong: share private keys",
                    "Tempting because history sync is trivial. But every linked device is a "
                    "compromise vector for ALL devices. Forward secrecy collapses."),
                   ("Right: one identity per device",
                    "Each device has its own identity key, prekeys, and Signal sessions. Senders "
                    "fan-out to all of a user's devices. Self-echo: my own other devices receive "
                    "my outgoing messages too."),
                   ("Linking flow",
                    "Primary phone shows a QR code containing an ephemeral public key + "
                    "signature. New device scans, derives a shared secret, registers its own "
                    "identity, and the primary transfers historical ciphertext (re-encrypted to "
                    "the new device's session)."),
                   ("Implication for groups",
                    "Group fan-out is over devices, not users — sender keys are distributed to "
                    "every device of every member."),
               ]),
        _topic("presence-privacy-scale",
               "Presence and Last-Seen at Scale (with Privacy)",
               "Soft-state in Redis with privacy filter at read time.",
               [
                   ("Soft-state design",
                    "Redis hash presence:{user_id} → {device_id: last_heartbeat_ts}. WS layer "
                    "writes heartbeats every ~30s. Online iff any device heartbeat in last 60s."),
                   ("Privacy filter",
                    "Per-user setting: everyone / contacts / nobody. Enforced at read: query "
                    "presence + check viewer's relationship before returning. The store does "
                    "not contain the privacy logic."),
                   ("Last-seen vs online",
                    "Last-seen is the max heartbeat ts; computed from the same hash. No separate "
                    "table — saves write amplification."),
                   ("Typing indicators",
                    "Pure WS frame, never persisted, sent to online recipients only. If you'd "
                    "design persistence for typing, you've over-engineered."),
               ]),
    ],
)
