from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design Gmail",
    "Hard",
    "Design a planet-scale email service: SMTP receive + send (MTA), durable mailbox storage, "
    "labels (not folders), Gmail-style conversation threading, full-text search via inverted index, "
    "spam filtering (Bayesian + ML + sender reputation), authentication (DKIM/SPF/DMARC), "
    "attachment storage on object store, IMAP/POP3 for legacy clients, push delivery (XMPP / IDLE), "
    "DSN bounce handling, abuse rate limiting, and multi-tenant Workspace isolation. "
    "Target ~2B mailboxes, ~300B messages delivered per day, p95 spam-decision <100ms, "
    "p95 search <300ms across a years-long mailbox, and 11-nines durability for stored mail. "
    "This is the consumer/business email plane — NOT the transactional email notification system "
    "(SES-style) which is a different problem with different SLOs.",
    hints=[
        "SMTP is unforgiving — receive must accept-and-defer; rejecting at SMTP time leaks abuse signal.",
        "Folders vs labels: Gmail is a label model. A 'message' is one row; folders are views over labels.",
        "Threading is by Message-ID + In-Reply-To + References + normalized Subject — RFC 5322.",
        "Search at scale = inverted index, NOT LIKE on a relational column. Per-user shards.",
        "Spam runs in two stages: cheap rule/reputation gate at SMTP, expensive ML after acceptance.",
        "DKIM/SPF/DMARC failures are reputation signals, not hard rejects (except DMARC p=reject).",
        "Object store attachments by content hash — dedupe across users (saves PB at scale).",
        "IMAP IDLE / Gmail push needs long-lived sessions — same fan-out problem as chat.",
    ],
    constraints=[
        "Standards-bound: must speak SMTP, IMAP, POP3, DKIM, SPF, DMARC, ARC interoperably",
        "Untrusted senders: anyone on the internet can hit port 25 — DDoS + abuse permanent",
        "Mailbox size: free tier 15GB; paid tiers up to 5TB; some accounts >100GB hot",
        "Retention: messages kept until user deletes; trash 30d; spam 30d",
        "Privacy: tenant isolation in Workspace; admin audit; eDiscovery legal hold",
        "Latency: p95 send-to-deliver (intra-domain) <2s; cross-domain bounded by remote MTA",
        "Durability: 11 nines for accepted mail — losing email is unacceptable",
    ],
    req_func=[
        "Receive inbound mail over SMTP (port 25) from arbitrary internet MTAs",
        "Send outbound mail via SMTP submission with MX lookup + queue + retry",
        "Store mail in per-user mailboxes with label-based organization",
        "Thread messages into conversations via References / Subject normalization",
        "Full-text + structured search (from:, to:, has:attachment, label:, before:, after:)",
        "Spam classification: header rules + sender reputation + ML scoring + user feedback loop",
        "DKIM sign outbound; verify inbound DKIM/SPF/DMARC and apply policy",
        "Store attachments on object store; dedupe by content hash; virus scan",
        "Serve IMAP and POP3 to legacy clients; XMPP/IDLE-style push to modern clients",
        "DSN: generate bounces for hard failures; retry-and-defer for transient",
        "Rate limit per-sender, per-IP, per-tenant to throttle abuse and snowshoe spam",
        "Workspace multi-tenancy: per-tenant DKIM keys, retention policies, admin controls",
    ],
    req_nonfunc=[
        "Durability ≥11 nines for accepted messages",
        "Availability 99.99% for read; 99.9% for SMTP receive (graceful 4xx defer is OK)",
        "Scale: ~2B mailboxes; ~300B msgs/day inbound; ~50B/day outbound; ~80% spam pre-accept",
        "Search p95 <300ms across multi-year mailbox",
        "Spam classification p95 <100ms in critical path",
        "Strong tenant isolation; per-tenant encryption keys for paid Workspace tiers",
        "Standards compliant — interoperate with arbitrary RFC 5321/5322/6376/7208/7489 peers",
    ],
    estimation={
        "mailboxes": "~2B (consumer + workspace)",
        "inbound_msgs_per_day": "~300B at the edge; ~60B accepted (80% spam dropped pre-accept)",
        "outbound_msgs_per_day": "~50B",
        "qps_inbound_steady": "~3.5M SMTP conns/sec edge; ~700K accepted msgs/sec",
        "qps_inbound_peak": "~3-5x steady (Monday morning, campaign storms)",
        "avg_msg_size": "~75KB body + ~200KB avg attachment",
        "storage_per_user": "free 15GB cap; avg ~5GB; long tail >100GB",
        "total_hot_storage": "~10 EB across all mailboxes; growth ~5 PB/day",
        "search_index_size": "~30% of body bytes per shard (postings + offsets)",
    },
    endpoints=[
        {"method": "SMTP", "path": "tcp:25 (inbound MX)",
         "description": "RFC 5321 server: HELO/EHLO, STARTTLS, MAIL FROM, RCPT TO, DATA. "
                        "Returns 2xx accepted, 4xx defer, 5xx reject.",
         "body": "envelope + RFC 5322 message"},
        {"method": "SMTP", "path": "tcp:587 (submission)",
         "description": "Authenticated outbound submission from user MUA; AUTH PLAIN/LOGIN over TLS",
         "body": "envelope + RFC 5322 message"},
        {"method": "IMAP", "path": "tcp:993 (TLS)",
         "description": "RFC 9051: SELECT mailbox, FETCH, STORE flags, IDLE for push, SEARCH",
         "body": "IMAP4rev2 protocol"},
        {"method": "POP3", "path": "tcp:995 (TLS)",
         "description": "Legacy: USER, PASS, LIST, RETR, DELE, QUIT",
         "body": "RFC 1939"},
        {"method": "GET", "path": "/v1/messages?q=&pageToken=",
         "description": "Web/API search with Gmail query syntax; returns thread refs",
         "body": "{q, label_ids?, page_token?}"},
        {"method": "GET", "path": "/v1/threads/{thread_id}",
         "description": "Fetch a conversation: ordered messages + per-message labels",
         "body": ""},
        {"method": "POST", "path": "/v1/messages/send",
         "description": "Web compose path: enqueue for outbound; signs DKIM and dispatches",
         "body": "{to, cc, bcc, subject, body_html, attachments[]}"},
        {"method": "POST", "path": "/v1/messages/{id}/labels",
         "description": "Add/remove labels (incl INBOX, STARRED, TRASH, SPAM)",
         "body": "{addLabelIds[], removeLabelIds[]}"},
        {"method": "POST", "path": "/v1/spam/feedback",
         "description": "User Mark-as-Spam / Not-Spam feedback into ML training set",
         "body": "{message_id, label}"},
        {"method": "POST", "path": "/v1/attachments/upload-url",
         "description": "Presigned PUT for large attachment; returns content_hash + ref",
         "body": "{size, mime}"},
        {"method": "GET", "path": "/v1/push/watch",
         "description": "Modern push: long-poll or HTTP/2 server-push of mailbox change events",
         "body": "{watermark}"},
    ],
    tables=[
        {"name": "users",
         "columns": ["user_id BIGINT PK", "primary_address VARCHAR(254) UNIQUE",
                     "tenant_id BIGINT NULL  -- workspace, null for consumer",
                     "quota_bytes BIGINT", "used_bytes BIGINT", "created_at BIGINT"]},
        {"name": "tenants",
         "columns": ["tenant_id BIGINT PK", "domain VARCHAR(253) UNIQUE",
                     "dkim_selector VARCHAR(64)", "dkim_priv_key_kms_ref TEXT",
                     "retention_days INT", "legal_hold BOOL"]},
        {"name": "messages",
         "columns": ["message_id BIGINT PK  -- internal", "rfc_message_id VARCHAR(998)",
                     "user_id BIGINT  -- mailbox owner", "thread_id BIGINT",
                     "from_addr VARCHAR(254)", "subject_norm VARCHAR(998)",
                     "received_at BIGINT", "size_bytes INT",
                     "headers_blob_ref VARCHAR(128)", "body_blob_ref VARCHAR(128)",
                     "spam_score REAL", "auth_results JSONB"]},
        {"name": "message_labels",
         "columns": ["user_id BIGINT", "message_id BIGINT", "label_id BIGINT",
                     "PRIMARY KEY (user_id, message_id, label_id)"]},
        {"name": "labels",
         "columns": ["label_id BIGINT PK", "user_id BIGINT", "name VARCHAR(64)",
                     "is_system BOOL  -- INBOX/SPAM/TRASH/STARRED",
                     "color VARCHAR(16)"]},
        {"name": "threads",
         "columns": ["thread_id BIGINT PK", "user_id BIGINT", "subject_norm VARCHAR(998)",
                     "first_received_at BIGINT", "last_received_at BIGINT",
                     "msg_count INT", "label_set BIGINT[]  -- denormalized for list views"]},
        {"name": "attachments",
         "columns": ["content_hash CHAR(64) PK  -- sha256", "size_bytes BIGINT",
                     "mime VARCHAR(128)", "object_url TEXT", "ref_count BIGINT"]},
        {"name": "message_attachments",
         "columns": ["message_id BIGINT", "content_hash CHAR(64)", "filename VARCHAR(255)",
                     "PRIMARY KEY (message_id, content_hash)"]},
        {"name": "outbound_queue",
         "columns": ["queue_id BIGINT PK", "user_id BIGINT", "envelope_from VARCHAR(254)",
                     "rcpt_to VARCHAR(254)", "next_attempt_at BIGINT", "attempts INT",
                     "raw_blob_ref VARCHAR(128)", "state VARCHAR(16)  -- queued/active/done/dead"]},
        {"name": "sender_reputation",
         "columns": ["sender_key VARCHAR(64) PK  -- ip|domain|dkim_d", "score REAL",
                     "complaints_30d INT", "volume_30d BIGINT", "updated_at BIGINT"]},
    ],
    indexes=[
        "(user_id, received_at DESC) on messages  -- mailbox listing",
        "(user_id, thread_id, received_at) on messages  -- thread expansion",
        "(thread_id) on threads",
        "(user_id, label_id, message_id) on message_labels  -- label view",
        "(rfc_message_id) on messages  -- threading lookup",
        "(state, next_attempt_at) on outbound_queue  -- scheduler",
        "(content_hash) unique on attachments  -- dedupe",
        "GIN/inverted index on messages_text(user_id, tokens)  -- search shard",
    ],
    hld_desc=(
        "An MX cluster terminates inbound SMTP, runs a fast pre-accept gate (RBL, SPF, "
        "rate limits), and either 5xx-rejects spam or accepts to a durable receive queue. "
        "An async pipeline performs DKIM/DMARC verification, virus scan, ML spam scoring, "
        "threading, label assignment, and writes the message to per-user mailbox shards "
        "(metadata in a sharded SQL/Spanner-style store; bodies and attachments in object "
        "storage by content hash). A separate inverted-index service shards search by "
        "user_id and indexes tokens + structured fields. Outbound submission goes through "
        "an Authenticated Submission MTA that DKIM-signs, queues, and dispatches to peer "
        "MTAs over MX with retry + DSN. IMAP/POP3 servers and a Web/API layer read from "
        "the same metadata + blob stores. Push is delivered to modern clients over a "
        "long-lived channel (HTTP/2 server-push or XMPP) and to IMAP via IDLE."
    ),
    hld_components=[
        {"name": "Inbound MX (SMTP receiver)", "role": "Port 25 termination, RBL, rate limit, STARTTLS, accept-or-defer"},
        {"name": "Pre-Accept Filter", "role": "Cheap reputation + SPF + connection-level abuse signals"},
        {"name": "Receive Queue", "role": "Durable Kafka-like log decoupling MTA from processing"},
        {"name": "Mail Processor", "role": "DKIM/DMARC verify, virus scan, ML spam, threading, label apply"},
        {"name": "Mailbox Metadata Store", "role": "Sharded SQL (Spanner/Vitess): users, messages, labels, threads"},
        {"name": "Blob Store", "role": "Object storage for raw RFC 5322 + attachments by content hash"},
        {"name": "Search Indexer", "role": "Inverted index sharded by user_id; tokens + structured fields"},
        {"name": "Submission MTA", "role": "Port 587 auth, DKIM sign, enqueue outbound"},
        {"name": "Outbound Dispatcher", "role": "MX lookup, queue management, retry/backoff, DSN generation"},
        {"name": "IMAP/POP3 Servers", "role": "Stateful protocol heads reading mailbox + blob stores"},
        {"name": "Push Service", "role": "HTTP/2 / XMPP / IMAP IDLE fan-out of mailbox change events"},
        {"name": "Reputation Service", "role": "Per-IP / per-domain / per-DKIM-d rolling scores"},
        {"name": "Spam ML Service", "role": "Online scorer + offline trainer fed by user feedback"},
    ],
    detailed_design={
        "smtp_receive_pipeline": (
            "Port 25 listeners run behind anycast IPs. The MX speaks RFC 5321: HELO/EHLO, "
            "advertises STARTTLS, then MAIL FROM / RCPT TO / DATA. The pre-accept gate runs "
            "INSIDE the SMTP transaction: check sender IP against RBLs (Spamhaus, internal "
            "reputation), enforce per-IP and per-tenant connection rate limits, and verify "
            "SPF for the envelope sender. If the sender is flagrantly bad we 5xx-reject; if "
            "we are overloaded or unsure we 4xx-defer (compliant senders retry; spammers "
            "rarely do — defer is a useful filter). Once we 250-accept after DATA we OWN the "
            "message and must not lose it: write to a durable receive log (Kafka with "
            "replication factor 3) and ack synchronously before closing the SMTP connection."
        ),
        "post_accept_processing": (
            "An async pipeline consumes from the receive log. Steps: (1) virus scan via a "
            "ClamAV-style pool, (2) DKIM verify against the signing domain's published "
            "selector, (3) DMARC alignment check using SPF + DKIM results, (4) ML spam "
            "score using sender reputation, header heuristics, body features, link "
            "reputation, and embedded-image fingerprints, (5) threading lookup, (6) label "
            "assignment (INBOX vs SPAM vs PROMOTIONS vs SOCIAL), (7) write metadata + blob "
            "refs + ACL row to the mailbox store, (8) emit a mailbox change event to the "
            "push service. Failures retry with backoff; permanently un-processable mail "
            "goes to a poison queue for SRE review."
        ),
        "label_model_vs_folders": (
            "A message is ONE row in messages plus zero or more rows in message_labels. "
            "INBOX, STARRED, IMPORTANT, TRASH, SPAM, and user labels are all just labels. "
            "'Move to Trash' is removing INBOX and adding TRASH. IMAP, which is folder-"
            "based, is mapped on top: each label is presented as a folder; the same "
            "message can appear in multiple IMAP folders because the underlying row is "
            "shared. This is the right model — Gmail's UX falls out of it (Archive = "
            "remove INBOX label) and storage stays O(1) per message."
        ),
        "mailbox_sharding": (
            "Shard by user_id using consistent hashing. A user's messages, labels, threads, "
            "and search index all live on the same shard family — every common query is "
            "single-shard. Cross-user operations (eDiscovery, admin search across a "
            "Workspace tenant) fan out via a coordinator. Hot mailboxes (e.g., "
            "support@bigcorp) are detected and pinned to a beefy shard; very large "
            "mailboxes can be split by year-range as a secondary partition key."
        ),
        "threading": (
            "RFC 5322 says: a reply carries In-Reply-To: <msg-id> and References: <chain>. "
            "On insert we look up parent by rfc_message_id; if found, inherit its thread_id. "
            "If References references a chain we don't have, create a new thread but tag "
            "with a fingerprint so a later arriving root can stitch. As a tiebreaker we "
            "match a normalized subject (strip leading 'Re:', 'Fwd:', collapse whitespace) "
            "within a 7-day window from the same correspondents. This handles broken "
            "clients that drop References. Threads are denormalized into the threads table "
            "for fast list view; on each new message we update msg_count, last_received_at, "
            "and a denormalized label_set."
        ),
        "search_inverted_index": (
            "Per-user search shards. On message accept the indexer tokenizes the subject + "
            "body (Unicode-aware, language-detected), normalizes (lowercase, accent-fold), "
            "and writes postings to a per-user inverted index segment (Lucene/Tantivy-"
            "shaped). Structured fields (from, to, has:attachment, label, date) are "
            "indexed as keyword fields. Queries parse Gmail syntax (from:foo subject:bar "
            "has:attachment) into a boolean query, evaluate against the user's shard, and "
            "return ranked thread refs. Index is segmented; segments merge in the "
            "background. Cold mailboxes can move segments to slower storage with a higher "
            "first-query latency budget."
        ),
        "spam_filtering": (
            "Two stages. Stage 1 (pre-accept, in SMTP transaction, <10ms budget): RBL "
            "lookups, SPF result, connection-level abuse, per-IP rate. Drops ~80% of junk "
            "without paying acceptance cost. Stage 2 (post-accept, <100ms p95): full "
            "DKIM/DMARC, sender reputation lookup, ML model scoring (gradient-boosted "
            "trees on header + body + URL + image features, plus per-recipient "
            "personalization for ham/spam priors), and finally Bayesian per-user filter "
            "trained on that user's mark-as-spam feedback. Output is a score; threshold "
            "decides INBOX vs SPAM. User feedback (mark spam / not spam) flows back to "
            "the trainer and updates per-user priors plus the global model nightly."
        ),
        "auth_dkim_spf_dmarc": (
            "DKIM: outbound is signed using a per-tenant private key in KMS; the public "
            "key is published as a TXT at selector._domainkey.<domain>. Inbound DKIM "
            "verification fetches the same record and validates signature over header + "
            "body hash. SPF: TXT lookup of v=spf1 mechanisms; pass/fail/softfail/neutral. "
            "DMARC: ties together DKIM + SPF with alignment to the From: header domain "
            "and a published policy (none/quarantine/reject). On p=reject + DMARC fail "
            "we honor the policy; otherwise these are inputs to the spam score, not hard "
            "drops. ARC headers are added when forwarding so downstream MTAs can see the "
            "original auth chain across hops."
        ),
        "attachment_storage": (
            "Client uploads attachments via a presigned PUT URL to object storage. "
            "Server computes SHA-256 content hash, dedupes against the attachments table, "
            "increments ref_count. The message stores only a content_hash reference. At "
            "scale this saves significant storage — large mailing lists send the same "
            "PDF to many users. Garbage collection: when ref_count → 0 (last referencing "
            "message hard-deleted past trash retention), object is purged. Virus scan "
            "happens once per content hash; the result is cached in attachments.scan_status."
        ),
        "imap_pop3": (
            "IMAP servers are stateful — a SELECT pins a mailbox view. We materialize the "
            "label-as-folder mapping at SELECT time: the server queries (user_id, "
            "label_id) → message_ids and assigns IMAP UIDs that are STABLE per (label, "
            "message). UID stability is a hard IMAP requirement; we store an "
            "(user_id, label_id, message_id) → uid map. IDLE keeps the connection open; "
            "we subscribe to the user's push channel and emit EXISTS / EXPUNGE on "
            "change. POP3 is simpler and stateless across sessions — we map LIST/RETR/"
            "DELE to the user's INBOX label."
        ),
        "outbound_pipeline": (
            "Submission MTA on 587 authenticates the user, validates From: alignment "
            "with the user's allowed identities, applies per-tenant outbound rate limits, "
            "DKIM-signs with the tenant's selector, and enqueues to the outbound queue. "
            "The dispatcher picks up jobs by next_attempt_at, does an MX lookup for the "
            "recipient domain (cache TTL'd), opens an SMTP client connection (ideally "
            "from an IP with good reputation for that destination), STARTTLS, transfers, "
            "and records the result. Transient 4xx retries with exponential backoff up "
            "to ~5 days. Permanent 5xx triggers a DSN bounce email back to the sender. "
            "Outbound IPs are warmed and pooled per destination to maintain reputation."
        ),
        "push_delivery": (
            "Modern clients use a long-lived HTTP/2 stream or XMPP-style channel; the "
            "push service subscribes to the user's mailbox change topic and emits "
            "lightweight events (new_message, label_changed, deleted). Clients then "
            "fetch only the deltas. IMAP IDLE is built on the same subscription, "
            "translated to IMAP wire events. APNS/FCM is used for mobile background "
            "wake just like chat — payload is a non-content hint, the client fetches."
        ),
        "dsn_bounces": (
            "RFC 3464 multipart/report. Hard bounces (5xx, no MX, mailbox-not-found) "
            "produce a DSN immediately. Soft bounces (4xx, greylisting, temporary "
            "deferral) retry with backoff, generating a DSN only on final give-up. "
            "DSNs themselves are normal mail through the inbound pipeline — they "
            "thread back to the original outbound message via the Original-Message-ID "
            "header for UI 'this message bounced' indicators."
        ),
        "abuse_rate_limiting": (
            "Multiple dimensions enforced via token-bucket counters in Redis: per source "
            "IP (inbound), per envelope domain, per DKIM d=, per Workspace tenant "
            "(outbound), per user (compose). Snowshoe spam (spreading across many low-"
            "volume IPs) is caught by aggregating reputation at the d= or content-"
            "fingerprint level rather than IP. Sudden volume spikes from a normally "
            "quiet sender trigger automatic throttling and human review."
        ),
        "workspace_multitenancy": (
            "Workspace tenants get their own DKIM selector and signing key in KMS, their "
            "own retention/legal-hold policies, their own admin console, and audit logs "
            "of admin actions. Storage encryption uses a per-tenant DEK wrapped by a "
            "tenant KEK in KMS — admin can revoke a KEK to crypto-shred. Tenant data is "
            "logically partitioned by tenant_id at every query layer; cross-tenant "
            "queries require explicit operator-level permission."
        ),
    },
    trade_offs=[
        {"option": "Reject vs defer at SMTP edge",
         "for_reject": "Sender sees immediate failure; clean signal",
         "for_defer": "Spammers don't retry; legit senders do — natural filter",
         "recommendation": "Defer (4xx) when uncertain or overloaded; reject (5xx) only on clear policy violation."},
        {"option": "Folders vs labels",
         "for_folders": "Maps cleanly to IMAP; familiar to users",
         "for_labels": "One message, many labels; storage O(1) per message; richer UX",
         "recommendation": "Labels under the hood, folders presented over IMAP."},
        {"option": "Synchronous vs async post-accept processing",
         "for_sync": "Spam decision before storing — never see spam at all",
         "for_async": "SMTP tail latency stays low; processing is durable and retriable",
         "recommendation": "Async — accept fast to durable log, decide labels in the pipeline."},
        {"option": "Per-user vs global search index",
         "for_global": "Cross-user features (Workspace eDiscovery)",
         "for_per_user": "Single-shard query, simple ACL, cache-friendly",
         "recommendation": "Per-user shards; coordinator fan-out for the rare cross-user case."},
        {"option": "Bayesian-only vs ML-only spam",
         "for_bayes": "Cheap, transparent, per-user adaptable",
         "for_ml": "Catches sophisticated phishing, link reputation, image spam",
         "recommendation": "Ensemble: rules + reputation + ML + per-user Bayesian feedback."},
        {"option": "Store attachments inline vs by content hash on object store",
         "for_inline": "Single storage path; simpler ACL",
         "for_object_dedupe": "Massive dedup savings at scale; CDN-friendly download",
         "recommendation": "Object store + content-hash dedupe; ref-counted GC."},
    ],
    tips=[
        "Open with the spam economics: '~80% of inbound is junk; the design is shaped by that.'",
        "Distinguish pre-accept (cheap, in SMTP) from post-accept (expensive, async). Senior signal.",
        "Labels, not folders. If you draw a folder tree on the whiteboard you've lost.",
        "Threading by Message-ID + References, normalized Subject as fallback. Cite RFC 5322.",
        "Mention DKIM/SPF/DMARC by name and what each actually proves — they are NOT redundant.",
        "Per-user search shards + inverted index. LIKE on a SQL column is a junior answer.",
        "Outbound IP reputation and warming is real — don't hand-wave 'just send it'.",
        "Object-store attachments with content-hash dedupe is the storage win that interviewers expect.",
        "Don't confuse with transactional email (SES/notifications) — different SLOs, different shape.",
    ],
    thought_process=[
        "1. Clarify scope: consumer + Workspace email, full SMTP/IMAP/POP3, search, spam, attachments.",
        "2. Estimate: 2B mailboxes, 300B inbound/day, ~80% spam → ~60B accepted, ~5PB/day storage growth.",
        "3. Inbound: SMTP MX with pre-accept gate (RBL/SPF/rate) → durable receive log → async pipeline.",
        "4. Pipeline: virus scan → DKIM/DMARC → ML spam → threading → labels → mailbox + index write.",
        "5. Storage: messages metadata in sharded SQL by user_id; bodies + attachments in object store.",
        "6. Attachments deduped by SHA-256 content hash; ref-counted GC.",
        "7. Threading: Message-ID + In-Reply-To + References + normalized-subject fallback.",
        "8. Labels not folders; INBOX/SPAM/TRASH are just labels; IMAP folders are views.",
        "9. Search: per-user inverted index (Lucene-shaped); structured + full-text fields.",
        "10. Spam: rules + sender reputation + ML + per-user Bayesian feedback loop.",
        "11. Outbound: 587 submission → DKIM sign → MX dispatch with retry + DSN.",
        "12. Push: HTTP/2/XMPP for modern, IMAP IDLE for legacy, APNS/FCM mobile wake.",
        "13. Abuse: token-bucket rate limits per IP/domain/d=/tenant; snowshoe-aware aggregation.",
        "14. Workspace tenancy: per-tenant DKIM, retention, admin, KMS-backed encryption.",
    ],
    tags=["email", "smtp", "imap", "search", "spam", "anti-abuse"],
    arch_nodes=[
        {"id": "internet", "label": "Internet MTAs", "type": "client"},
        {"id": "mx", "label": "Inbound MX (SMTP:25)", "type": "lb"},
        {"id": "preaccept", "label": "Pre-Accept Filter", "type": "service"},
        {"id": "rxlog", "label": "Receive Log", "type": "queue"},
        {"id": "pipeline", "label": "Mail Processor", "type": "server"},
        {"id": "spam", "label": "Spam ML + Reputation", "type": "service"},
        {"id": "meta", "label": "Mailbox Metadata", "type": "database"},
        {"id": "blob", "label": "Blob + Attachment Store", "type": "database"},
        {"id": "index", "label": "Search Index (per-user)", "type": "database"},
        {"id": "submit", "label": "Submission MTA (587)", "type": "server"},
        {"id": "outq", "label": "Outbound Queue", "type": "queue"},
        {"id": "dispatch", "label": "Outbound Dispatcher", "type": "server"},
        {"id": "imap", "label": "IMAP / POP3", "type": "server"},
        {"id": "push", "label": "Push (HTTP2/XMPP/IDLE)", "type": "service"},
        {"id": "client", "label": "User Clients", "type": "client"},
    ],
    arch_edges=[
        {"source": "internet", "target": "mx", "label": "SMTP:25"},
        {"source": "mx", "target": "preaccept"},
        {"source": "preaccept", "target": "rxlog", "label": "accepted"},
        {"source": "rxlog", "target": "pipeline"},
        {"source": "pipeline", "target": "spam", "label": "score"},
        {"source": "pipeline", "target": "meta", "label": "metadata"},
        {"source": "pipeline", "target": "blob", "label": "raw + attachments"},
        {"source": "pipeline", "target": "index", "label": "tokens"},
        {"source": "client", "target": "submit", "label": "SMTP:587"},
        {"source": "submit", "target": "outq", "label": "DKIM-signed"},
        {"source": "outq", "target": "dispatch"},
        {"source": "dispatch", "target": "internet", "label": "MX delivery"},
        {"source": "client", "target": "imap", "label": "IMAP/POP3"},
        {"source": "imap", "target": "meta"},
        {"source": "imap", "target": "blob"},
        {"source": "pipeline", "target": "push", "label": "mailbox event"},
        {"source": "push", "target": "client"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant Sndr as Sender MTA\n"
        "  participant MX as Gmail MX\n"
        "  participant Pre as Pre-Accept\n"
        "  participant Log as Receive Log\n"
        "  participant Proc as Processor\n"
        "  participant ML as Spam/ML\n"
        "  participant Meta as Mailbox\n"
        "  participant Idx as Index\n"
        "  participant Push as Push\n"
        "  participant Rcpt as Recipient\n"
        "  Sndr->>MX: HELO / MAIL FROM / RCPT TO / DATA\n"
        "  MX->>Pre: IP, SPF, RBL, rate\n"
        "  alt clearly bad\n"
        "    Pre-->>MX: reject\n"
        "    MX-->>Sndr: 5xx\n"
        "  else accept\n"
        "    Pre-->>MX: accept\n"
        "    MX->>Log: append (durable)\n"
        "    MX-->>Sndr: 250 OK\n"
        "  end\n"
        "  Log->>Proc: consume\n"
        "  Proc->>ML: score (DKIM/DMARC + features)\n"
        "  Proc->>Meta: write message + thread + labels\n"
        "  Proc->>Idx: index tokens\n"
        "  Proc->>Push: mailbox_changed\n"
        "  Push-->>Rcpt: new_message hint\n"
        "  Rcpt->>Meta: fetch thread\n"
    ),
    er_diagram=(
        "erDiagram\n"
        "  USER ||--o{ MESSAGE : owns\n"
        "  USER ||--o{ LABEL : defines\n"
        "  MESSAGE ||--o{ MESSAGE_LABEL : tagged\n"
        "  LABEL ||--o{ MESSAGE_LABEL : applies\n"
        "  THREAD ||--o{ MESSAGE : groups\n"
        "  MESSAGE ||--o{ MESSAGE_ATTACHMENT : has\n"
        "  ATTACHMENT ||--o{ MESSAGE_ATTACHMENT : referenced\n"
        "  TENANT ||--o{ USER : contains\n"
        "  MESSAGE { bigint message_id\n string rfc_message_id\n bigint thread_id\n real spam_score }\n"
        "  ATTACHMENT { string content_hash\n bigint size_bytes\n bigint ref_count }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Inbound SMTP] --> B{Pre-accept gate}\n"
        "  B -->|bad| R[5xx reject]\n"
        "  B -->|uncertain/overloaded| D[4xx defer]\n"
        "  B -->|ok| L[Receive log durable]\n"
        "  L --> P[Processor]\n"
        "  P --> V[Virus scan]\n"
        "  P --> K[DKIM/SPF/DMARC]\n"
        "  P --> M[ML spam + per-user Bayes]\n"
        "  P --> T[Threading]\n"
        "  T --> S[Mailbox + Labels]\n"
        "  S --> I[Inverted index]\n"
        "  S --> N[Push notify]\n"
        "  N --> C[Client fetches delta]"
    ),
    tradeoff_title="Spam Filtering Architecture",
    tradeoff_options=[
        {"label": "Single-stage post-accept ML",
         "description": "Always accept, then run heavy ML to classify.",
         "pros": ["Single code path", "Best accuracy — full feature set"],
         "cons": ["Pays storage + CPU for known junk", "Bots flood your acceptance pipeline"]},
        {"label": "Two-stage: pre-accept gate + post-accept ML",
         "description": "Cheap rules + reputation in SMTP transaction; full ML after acceptance.",
         "pros": ["Drops ~80% of junk before storage cost", "Async stage can be deeper"],
         "cons": ["Two policies to maintain", "Pre-accept rules can leak signal to attackers"]},
    ],
    tradeoff_rec="Two-stage. Cheap pre-accept gate is required at this scale; post-accept ML carries accuracy.",
    senior_topics=[
        _topic("smtp-receive-pipeline",
               "SMTP Receive: Accept-and-Defer, Not Accept-and-Pray",
               "How a high-scale MX actually behaves on the wire, and why deferral is a tool.",
               [
                   ("The SMTP transaction in slow motion",
                    "Connection → EHLO → STARTTLS → MAIL FROM → RCPT TO → DATA → 250. Every "
                    "step has a response code. We can apply policy at any of them: connection "
                    "drop, RCPT TO refusal, post-DATA reject."),
                   ("Why 4xx defer is powerful",
                    "Spam software is single-shot — if it gets a 4xx it usually moves on to the "
                    "next victim. Legitimate MTAs have a queue and retry for days. So 4xx during "
                    "overload or on borderline reputation is a near-free filter."),
                   ("Once we say 250, we own it",
                    "After accepting we MUST persist before closing the SMTP connection. "
                    "Otherwise we have to bounce, which means generating a DSN — bad for our "
                    "reputation. So the 250 is gated on a successful synchronous append to a "
                    "replicated durable log."),
                   ("Tarpitting and connection-level abuse",
                    "Slow down chatty bad senders by inserting delays in the transaction (RFC "
                    "5321 allows it). Burns the attacker's connection slots. Combined with "
                    "per-IP concurrency caps it shapes the abuse load."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant S as Sender\n"
                   "  participant MX\n"
                   "  participant Log as Receive Log\n"
                   "  S->>MX: HELO + STARTTLS\n"
                   "  S->>MX: MAIL FROM\n"
                   "  MX->>MX: SPF + IP rep\n"
                   "  alt clearly bad\n"
                   "    MX-->>S: 550 reject\n"
                   "  else uncertain\n"
                   "    MX-->>S: 421 try again later\n"
                   "  else ok\n"
                   "    S->>MX: RCPT TO + DATA\n"
                   "    MX->>Log: append (sync)\n"
                   "    MX-->>S: 250 OK\n"
                   "  end"
               )),
        _topic("threading-rfc5322",
               "Conversation Threading: Message-ID, References, Subject Fallback",
               "Gmail-style threads from RFC 5322 headers, with a normalized-subject fallback for broken clients.",
               [
                   ("The headers that matter",
                    "Message-ID: globally unique per message. In-Reply-To: the parent's "
                    "Message-ID. References: full ancestor chain. RFC 5322 says clients SHOULD "
                    "carry References across reply hops; many do not."),
                   ("Threading algorithm",
                    "On insert: if In-Reply-To references a known Message-ID, attach to that "
                    "message's thread. Else if any References entry is known, attach to its "
                    "thread (oldest match wins). Else look up recent (≤7 day) threads in the "
                    "same correspondent set with a normalized subject match. Else start a new "
                    "thread."),
                   ("Subject normalization",
                    "Strip any leading sequence of 'Re:', 'Fwd:', 'AW:', etc. (i18n list), "
                    "collapse whitespace, lowercase. This is the fallback that handles broken "
                    "MUAs and forwarded chains where References was lost."),
                   ("Late-arriving root",
                    "If a deeper child arrives before its root (out-of-order delivery), we "
                    "create a thread with a placeholder. When the root lands and we discover "
                    "its Message-ID is referenced by an existing thread, we stitch them by "
                    "reparenting under the older thread_id."),
               ]),
        _topic("search-inverted-index",
               "Per-User Inverted Index for Mailbox Search",
               "Why search at this scale is a Lucene-shaped problem, sharded by user_id.",
               [
                   ("Why not LIKE on the messages table",
                    "LIKE '%foo%' is a full table scan. With a multi-year mailbox of 100K+ "
                    "messages, p95 spans seconds. Even with a SQL full-text extension, you "
                    "give up Gmail-syntax operators (has:attachment, label:starred, before:)."),
                   ("Inverted index basics",
                    "Tokenize subject + body with Unicode + language-aware analysis (CJK "
                    "needs special tokenization). For each token store a posting list of "
                    "(message_id, positions). Boolean queries intersect/union postings."),
                   ("Sharding by user",
                    "Per-user shards keep query latency predictable. ACL is implicit — the "
                    "shard contains only one user's data. Multi-tenant Workspace eDiscovery "
                    "uses a coordinator that fans out across the tenant's user shards."),
                   ("Structured fields and Gmail syntax",
                    "from:, to:, label:, has:attachment, before:, after:, larger:, "
                    "newer_than: are keyword/range fields. Parser builds a boolean tree "
                    "of (text-tokens) AND (filter-clauses), evaluates against the user's "
                    "shard, ranks by recency and relevance."),
                   ("Index lifecycle",
                    "Segment-based — new segments per batch of indexed messages, periodic "
                    "merges in the background, immutable segments are easy to back up. "
                    "Cold mailboxes can move older segments to cheaper storage with a "
                    "longer first-query SLA."),
               ]),
        _topic("spam-architecture",
               "Spam Filtering: Rules + Reputation + ML + Per-User Bayes",
               "An ensemble where each layer pays for itself in latency and accuracy.",
               [
                   ("Layer 1 — RBL + connection rep (pre-accept, <10ms)",
                    "Spamhaus, Spamcop, internal IP reputation, connection-level abuse "
                    "(too many concurrent, too many RCPT TO from one connection). Rejects "
                    "the easy ~80% before they cost us a single byte of storage."),
                   ("Layer 2 — DKIM/SPF/DMARC (post-accept)",
                    "Authenticate the sender. NOT a spam decision by itself — only DMARC "
                    "p=reject is a hard drop. Otherwise these are features for the ML model "
                    "(domain alignment, signature validity, ARC chain integrity)."),
                   ("Layer 3 — ML scorer (post-accept, <100ms)",
                    "Gradient-boosted trees over hundreds of features: header structure, "
                    "body URL reputation, image fingerprint, attachment type, time-of-day "
                    "vs sender baseline, link domain reputation, redirect chains. Outputs "
                    "a calibrated probability of spam."),
                   ("Layer 4 — Per-user Bayesian filter",
                    "Each user's mark-as-spam / not-spam clicks update per-user token "
                    "priors. The final score blends global ML probability with per-user "
                    "evidence — newsletters one user loves are spam to another."),
                   ("Feedback loop",
                    "User actions write to a feedback topic. Per-user priors update online; "
                    "the global model retrains nightly on the aggregated stream with "
                    "carefully sampled negatives (false-positive cost is high)."),
               ]),
        _topic("dkim-spf-dmarc-arc",
               "DKIM, SPF, DMARC, ARC: What Each Actually Proves",
               "These are NOT redundant. Each protects against a different attack.",
               [
                   ("SPF — the envelope sender",
                    "Domain owner publishes 'these IPs are allowed to send mail with my "
                    "domain in MAIL FROM'. Receiver checks the connecting IP against the "
                    "list. Breaks on forwarding, because the forwarder's IP isn't in the "
                    "original domain's SPF."),
                   ("DKIM — message-content integrity",
                    "Sender signs selected headers + body hash with a private key; public "
                    "key is published in DNS. Receiver verifies. Survives forwarding if "
                    "the forwarder doesn't mangle headers/body. Does NOT bind to envelope."),
                   ("DMARC — alignment + policy",
                    "Ties SPF and DKIM to the From: header domain that the user sees. "
                    "Requires that AT LEAST ONE of {SPF aligned, DKIM aligned} pass. The "
                    "domain owner publishes a policy: none/quarantine/reject and asks for "
                    "aggregate + forensic reports. Fixes spoofing of the visible From."),
                   ("ARC — preserve auth across forwarding",
                    "Mailing lists and forwarders break SPF and sometimes DKIM. ARC adds "
                    "a chain of 'I saw the original auth pass' headers signed by each hop. "
                    "Lets the final receiver trust a forwarder it knows is legitimate."),
                   ("Putting it together",
                    "We sign outbound with DKIM (per-tenant selector + key in KMS), publish "
                    "SPF, publish DMARC with quarantine for our own domains, add ARC when "
                    "we forward, and on inbound we check all four and feed results into "
                    "the ML model — only DMARC p=reject + fail is a hard drop."),
               ]),
        _topic("outbound-mta-and-reputation",
               "Outbound Delivery: MX, Retry, DSN, IP Reputation Warming",
               "Sending at our scale is itself a deliverability problem, not just a TCP problem.",
               [
                   ("Submission to dispatch",
                    "User submits via authenticated SMTP on 587 or the API. We validate the "
                    "From: alignment, apply per-tenant outbound rate limits (cooperative "
                    "tenants, abusive tenants), DKIM-sign, and enqueue."),
                   ("MX lookup and connection pool",
                    "Recipient domain → MX records (cached with TTL). We pool SMTP "
                    "connections per (destination domain, source IP). Connection reuse "
                    "matters for throughput because TLS + EHLO costs dominate at high "
                    "QPS to popular destinations."),
                   ("Retry and DSN",
                    "4xx → exponential backoff up to ~5 days. 5xx → immediate DSN to the "
                    "envelope sender via the inbound pipeline. DSN is RFC 3464 multipart/"
                    "report carrying the original headers and the failure reason."),
                   ("IP reputation and warming",
                    "Outbound IPs have reputation at the receiver (Gmail/Outlook score "
                    "you). New IPs must be 'warmed' — slowly increasing volume so receivers "
                    "build trust. We pool IPs by destination domain and route a tenant's "
                    "outbound through IPs whose reputation matches the tenant's volume "
                    "profile. Bad tenants are isolated to dirty pools to protect the "
                    "shared good IPs."),
                   ("Bounce + complaint handling",
                    "Hard bounces and complaint-feedback-loop reports update sender "
                    "reputation. Repeat hard-bouncers are auto-suppressed. Workspace "
                    "tenants get visibility via aggregate DMARC reports and bounce dashboards."),
               ]),
        _topic("workspace-multitenancy",
               "Workspace Multi-Tenancy and Compliance",
               "Per-tenant DKIM, retention, encryption, audit, eDiscovery, legal hold.",
               [
                   ("Per-tenant DKIM keys",
                    "Each tenant has its own DKIM selector and private key in KMS. Outbound "
                    "signing fetches the key from KMS at send time — cached briefly. Key "
                    "rotation publishes the new selector first, then flips signing, then "
                    "deprecates the old selector."),
                   ("Retention and legal hold",
                    "Per-tenant retention policy (e.g., delete after 7 years). Legal hold "
                    "overrides retention for specific custodians or matters — those messages "
                    "are exempt from purge until the hold lifts. eDiscovery exports run "
                    "via a coordinator over the tenant's user shards."),
                   ("Encryption and crypto-shred",
                    "Storage uses per-tenant DEKs wrapped by a tenant KEK in KMS. Revoking "
                    "the KEK renders all the tenant's data unreadable — 'crypto-shredding' "
                    "is the operationally sound way to honor a delete-everything request."),
                   ("Admin audit",
                    "Every admin action (impersonation, eDiscovery export, retention change) "
                    "is appended to a tamper-evident audit log readable by the tenant's "
                    "compliance team but not modifiable by the admin who performed it."),
               ]),
    ],
)
