"""SDQ — Design Dropbox / Google Drive.

File-sync service across devices with sharing, versioning, and conflict
resolution. Mirrors `sd_questions.SD_01` shape via the `_q` / `_topic` helpers.
"""
from __future__ import annotations

from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design Dropbox / Google Drive",
    "Hard",
    "Design a cloud file-sync service that keeps a user's files consistent across desktops, "
    "phones, tablets, and the web. Users edit files locally (offline OK), share folders/files with "
    "ACLs or public links, and expect new edits to propagate to other devices within seconds. The "
    "system stores blobs durably, deduplicates at block level, supports 30-day version history and "
    "trash, resolves concurrent edits, and gracefully degrades on flaky networks.",
    hints=[
        "Separate the metadata plane (file tree, perms, versions) from the blob plane (content).",
        "Block-level chunking + content-addressable storage gives dedupe + delta-sync for free.",
        "Sync client = local FS watcher + indexer + uploader + downloader + reconciler.",
        "Conflict story is the senior signal: last-write-wins is wrong for collaboration.",
        "Sharing/ACLs need permission inheritance and link-token revocation, not just row flags.",
    ],
    constraints=[
        "Files up to 50 GB; 90% are <10 MB, but the long tail dominates bandwidth.",
        "Clients can be offline for hours-to-weeks; reconciliation must be cheap on reconnect.",
        "Cross-region propagation: edits on a US laptop visible on EU phone within seconds.",
        "Blob storage is the dominant cost — dedupe and tiering are non-optional.",
        "Hard delete must purge all replicas within 30 days for compliance.",
    ],
    req_func=[
        "Upload, download, rename, move, delete files and folders.",
        "Two-way sync across all of a user's devices with offline support.",
        "Share a file/folder with another user (ACL) or via public link with permissions.",
        "Versioning: 30-day history, restore prior version, recover from trash.",
        "Conflict resolution when two devices edit the same file while offline.",
        "Selective sync: choose which folders sync to which device.",
    ],
    req_nonfunc=[
        "Durability 11 nines for blob storage; metadata RPO ≤ 5s.",
        "Sync latency p95 < 5s online; p95 < 60s after extended offline.",
        "Bandwidth efficient — only changed blocks travel on edit.",
        "Scale: 700M users, 100B files, ~1 EB total stored.",
        "Read-heavy: read:write ≈ 10:1 on metadata; blob reads >> writes.",
    ],
    estimation={
        "active_users": "700M",
        "files_per_user": "~150 (median), tail to millions",
        "block_size": "4 MB content-addressed chunks",
        "writes_per_day": "~5B file-events (create/edit/delete)",
        "qps_steady": "60K metadata writes/sec, 600K metadata reads/sec",
        "blob_storage": "~1 EB raw → ~400 PB after dedupe + erasure coding",
        "egress": "~50 GB/s aggregate; biased to working hours per region",
    },
    endpoints=[
        {"method": "POST", "path": "/v1/files/{path}/upload-init",
         "description": "Begin upload — server returns block list to skip (already-have hashes)",
         "body": "{size, mtime, blocks:[{hash, size}]}"},
        {"method": "PUT", "path": "/v1/blocks/{hash}",
         "description": "Upload one 4MB block (idempotent on hash)",
         "body": "binary"},
        {"method": "POST", "path": "/v1/files/{path}/commit",
         "description": "Commit upload: server materialises new file version from block list",
         "body": "{block_hashes:[...], parent_version, client_mtime}"},
        {"method": "GET", "path": "/v1/files/{path}",
         "description": "Get file metadata + signed block URLs"},
        {"method": "GET", "path": "/v1/delta",
         "description": "Long-poll: return all metadata changes since cursor",
         "body": "{cursor}"},
        {"method": "POST", "path": "/v1/share",
         "description": "Grant ACL or mint link token",
         "body": "{path, principal|link, role}"},
        {"method": "POST", "path": "/v1/versions/{file_id}/restore",
         "description": "Restore a prior version as the current head"},
    ],
    tables=[
        {"name": "namespaces",
         "columns": ["ns_id BIGINT PK", "owner_user_id BIGINT", "kind ENUM('user','team','shared')",
                     "quota_bytes BIGINT"]},
        {"name": "files",
         "columns": ["file_id BIGINT PK", "ns_id BIGINT", "parent_id BIGINT",
                     "name VARCHAR(255)", "kind ENUM('file','folder')",
                     "head_version_id BIGINT", "deleted_at BIGINT NULL",
                     "INDEX (ns_id, parent_id, name)"]},
        {"name": "file_versions",
         "columns": ["version_id BIGINT PK", "file_id BIGINT", "size BIGINT",
                     "block_list_id BIGINT", "client_mtime BIGINT", "server_ctime BIGINT",
                     "author_device_id VARCHAR(64)", "parent_version_id BIGINT NULL"]},
        {"name": "block_lists",
         "columns": ["block_list_id BIGINT PK", "block_hashes BLOB"]},
        {"name": "blocks",
         "columns": ["hash CHAR(64) PK", "size INT", "storage_class VARCHAR(16)",
                     "refcount BIGINT", "first_seen_at BIGINT"]},
        {"name": "acls",
         "columns": ["acl_id BIGINT PK", "file_id BIGINT", "principal_id BIGINT",
                     "role ENUM('viewer','commenter','editor','owner')",
                     "inherited BOOLEAN"]},
        {"name": "share_links",
         "columns": ["token CHAR(32) PK", "file_id BIGINT", "role VARCHAR(16)",
                     "expires_at BIGINT NULL", "password_hash VARCHAR(64) NULL",
                     "revoked BOOLEAN"]},
        {"name": "device_cursors",
         "columns": ["user_id BIGINT", "device_id VARCHAR(64)", "cursor BIGINT",
                     "PRIMARY KEY (user_id, device_id)"]},
    ],
    indexes=[
        "(ns_id, parent_id, name) on files — directory listing",
        "(file_id, version_id DESC) on file_versions — history scan",
        "(hash) on blocks — content-addressable lookup",
        "(file_id) on acls — permission resolution",
        "(token) on share_links — link redemption",
    ],
    hld_desc=(
        "Two-plane architecture. Metadata plane: sharded RDBMS (file tree, ACLs, versions) fronted by a "
        "stateless API tier with a per-user sequence log that drives the long-poll Notify service. Blob "
        "plane: content-addressable object store (4 MB chunks keyed by SHA-256), erasure-coded across "
        "AZs, with cold tier for blocks unread for 90 days. Sync client (desktop/mobile) watches local FS, "
        "indexes block hashes, uploads only missing blocks, then commits a new version pointer. A "
        "notification service pushes 'namespace changed, pull delta' to the user's other devices."
    ),
    hld_components=[
        {"name": "Sync Client", "role": "FS watch, hashing, upload/download, local DB, conflict UI"},
        {"name": "API Gateway", "role": "Auth, throttle, route by namespace shard"},
        {"name": "Metadata Service", "role": "File tree, versions, ACLs — sharded by ns_id"},
        {"name": "Block Service", "role": "Content-addressable blob upload/download, refcounts"},
        {"name": "Object Store", "role": "Erasure-coded durable storage with hot/cold tiering"},
        {"name": "Notify Service", "role": "Long-poll fan-out of namespace deltas to devices"},
        {"name": "Indexer / Search", "role": "Async pipeline: extract text, build search index"},
        {"name": "GC / Trash Worker", "role": "30-day retention sweep; refcount-zero block reaping"},
        {"name": "Edge CDN", "role": "Cache hot block reads for public links and large teams"},
    ],
    detailed_design={
        "block_chunking": (
            "Files split into 4 MB blocks. For text/code we use a content-defined rolling-hash "
            "boundary (Rabin-Karp) so a 1-byte insert in a 1 GB file re-uploads ~one block, not the whole "
            "tail. Each block keyed by SHA-256 of contents — same block from any user/file dedupes. "
            "Upload-init sends the block-hash list; server returns 'already-have' so client only uploads "
            "missing blocks. This is the delta-sync mechanism."
        ),
        "metadata_plane": (
            "Sharded by ns_id (user or team). A monotonic per-namespace `seq` increments on every "
            "metadata change. Devices store the last-seen `seq` as their cursor. /v1/delta long-polls and "
            "returns all changes since the cursor, including renames/moves modeled as metadata-only (zero "
            "block traffic). Read replicas serve listing; writes go to the leader of the ns_id shard."
        ),
        "conflict_resolution": (
            "Each commit names a `parent_version_id`. If the server's current head differs, the commit is "
            "rejected and the client materialises both: the original keeps its name, the loser is "
            "renamed `foo (deviceA's conflicted copy 2026-04-28).txt`. Branch-with-rename — never "
            "silently discard. For Google-Docs-style live collaboration the same files are layered with an "
            "OT/CRDT editor service; the file-sync layer just stores periodic snapshots."
        ),
        "sharing_acls": (
            "ACL rows attach to file_id; effective permission = walk ancestors + direct grants, with the "
            "highest role winning. Inherited rows materialised on grant for O(1) check (denormalised, "
            "rebuilt on move). Public links are signed tokens with optional password + expiry; revocation "
            "is a flag flip + token-cache invalidate. Org-level admin overrides bolt on as a separate "
            "policy layer."
        ),
        "versioning_trash": (
            "Every commit creates an immutable `file_versions` row pointing to a `block_list`. Restore is "
            "a metadata-only flip of `head_version_id`. Soft-delete sets `deleted_at`; trash sweeper "
            "purges metadata after 30 days, decrements block refcounts, and a separate GC reclaims "
            "refcount-zero blocks asynchronously (lagging by hours so a fast un-delete is cheap)."
        ),
        "notifications": (
            "Devices hold a long-poll on /v1/delta with their cursor. The Notify service fans out "
            "'cursor advanced' hints over a connection pool keyed by (user_id, device_id), with "
            "WebSocket fallback on unstable networks. If the long-poll connection drops, the next "
            "/v1/delta call still picks up missed changes — push is an optimisation, never a "
            "correctness requirement."
        ),
        "selective_offline": (
            "Selective-sync is per-device metadata: ignore-paths set client-side, server-enforced for "
            "team-policy folders. Offline access pins local block copies; on edit, the client commits to "
            "an outbox queue and replays on reconnect through the same upload-init/commit path."
        ),
        "encryption": (
            "TLS 1.3 in transit. At rest: server-side AES-256 on every block (per-customer KMS-wrapped "
            "DEK). Optional zero-knowledge / E2EE tier encrypts blocks client-side; the price is no "
            "server-side dedupe across users and no thumbnail / search."
        ),
        "slo_contract": (
            "Metadata write p99 < 200 ms; sync visible cross-device p95 < 5 s online; durability "
            "11 nines; trash purge ≤ 30 days; share-revoke globally effective ≤ 60 s."
        ),
    },
    trade_offs=[
        {"option": "Fixed-size vs content-defined chunking",
         "for_fixed": "Simple hashing, predictable block table",
         "for_content_defined": "Robust to inserts; far better delta-sync on text/code",
         "recommendation": "Content-defined for text/code, fixed 4 MB for media — the boundary is set by file type."},
        {"option": "Last-write-wins vs branch-with-rename for conflicts",
         "for_lww": "Simpler client; fewer files in tree",
         "for_branch": "Never silently lose a user's edit",
         "recommendation": "Branch-with-rename — silent data loss is the worst failure mode."},
        {"option": "Push (WebSocket) vs long-poll for sync notifications",
         "for_push": "Lower idle latency, fewer connections",
         "for_long_poll": "Works through every NAT/proxy, dead-simple recovery",
         "recommendation": "Long-poll as the floor (correctness), WebSocket as an optimisation."},
        {"option": "Strong vs eventual consistency on metadata",
         "for_strong": "Listing always shows latest; no surprise stale reads",
         "for_eventual": "Cheap read replicas, lower write latency",
         "recommendation": "Strong on the writer's region; eventual cross-region with cursor-driven catchup."},
    ],
    tips=[
        "Lead with the two-plane split — metadata plane vs blob plane. Most candidates conflate them.",
        "Content-addressable blocks earn dedupe + delta-sync from a single design choice.",
        "Branch-with-rename for conflicts is the senior answer; LWW is the junior trap.",
        "ACL permission resolution must include inheritance + link tokens, not just row checks.",
        "Quote the long-poll cursor mechanism — it's the correctness floor under any push system.",
    ],
    thought_process=[
        "1. Clarify: 2-way sync, sharing, versions, conflicts, scale.",
        "2. Estimate: 700M users × 150 files × 5B daily events → split metadata vs blob plane.",
        "3. APIs: upload-init / PUT block / commit / delta / share / restore.",
        "4. Schema: namespaces, files, file_versions, blocks (content-addressable), acls, share_links.",
        "5. Block-level chunking (rolling hash) → dedupe + delta-sync.",
        "6. Conflict story: parent_version + branch-with-rename, never LWW.",
        "7. Sharing: inherited ACLs + signed link tokens, revocation propagated via cache invalidate.",
        "8. Versioning + 30-day trash + async block GC.",
        "9. Notifications via long-poll cursor (correctness) + WebSocket (latency).",
        "10. Offline outbox + selective sync; encryption at rest + in transit; E2EE tier as opt-in.",
    ],
    tags=["file-sync", "storage", "blob", "metadata", "collaboration"],
    arch_nodes=[
        {"id": "client", "label": "Sync Client", "type": "client"},
        {"id": "lb", "label": "API Gateway", "type": "lb"},
        {"id": "meta", "label": "Metadata Service", "type": "server"},
        {"id": "block", "label": "Block Service", "type": "server"},
        {"id": "metadb", "label": "Metadata DB", "type": "database"},
        {"id": "obj", "label": "Object Store", "type": "database"},
        {"id": "notify", "label": "Notify Service", "type": "service"},
        {"id": "gc", "label": "GC / Trash Worker", "type": "service"},
        {"id": "cdn", "label": "Edge CDN", "type": "cache"},
    ],
    arch_edges=[
        {"source": "client", "target": "lb"},
        {"source": "lb", "target": "meta", "label": "tree/ACL/version"},
        {"source": "lb", "target": "block", "label": "block I/O"},
        {"source": "meta", "target": "metadb"},
        {"source": "block", "target": "obj"},
        {"source": "meta", "target": "notify", "label": "seq advance"},
        {"source": "notify", "target": "client", "label": "long-poll/WS"},
        {"source": "client", "target": "cdn", "label": "block read"},
        {"source": "cdn", "target": "obj", "label": "miss"},
        {"source": "gc", "target": "obj", "label": "reap refcount=0"},
        {"source": "gc", "target": "metadb", "label": "trash sweep"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant C1 as Client A\n"
        "  participant API\n"
        "  participant META as Metadata\n"
        "  participant BLK as Block Svc\n"
        "  participant N as Notify\n"
        "  participant C2 as Client B\n"
        "  C1->>API: upload-init(blocks=[h1,h2,h3])\n"
        "  API->>BLK: have?(h1,h2,h3)\n"
        "  BLK-->>API: missing=[h2]\n"
        "  API-->>C1: PUT h2\n"
        "  C1->>BLK: PUT block h2\n"
        "  C1->>API: commit(parent_version=v7)\n"
        "  API->>META: write v8 (parent=v7)\n"
        "  META->>N: seq++\n"
        "  N-->>C2: cursor advanced\n"
        "  C2->>API: GET /v1/delta\n"
        "  API-->>C2: {file changed -> v8, blocks=[h1,h2,h3]}\n"
        "  C2->>BLK: GET h2 (have h1,h3)\n"
        "  BLK-->>C2: block h2"
    ),
    er_diagram=(
        "erDiagram\n"
        "  USER ||--o{ NAMESPACE : owns\n"
        "  NAMESPACE ||--o{ FILE : contains\n"
        "  FILE ||--o{ FILE_VERSION : has\n"
        "  FILE_VERSION }o--|| BLOCK_LIST : refs\n"
        "  BLOCK_LIST }o--o{ BLOCK : composed-of\n"
        "  FILE ||--o{ ACL : grants\n"
        "  FILE ||--o{ SHARE_LINK : exposes\n"
        "  USER ||--o{ DEVICE_CURSOR : tracks"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B[Split metadata vs blob plane]\n"
        "  B --> C[Content-addressable blocks]\n"
        "  C --> D[Delta sync via have/missing]\n"
        "  D --> E[Per-namespace seq + long-poll cursor]\n"
        "  E --> F{Conflict?}\n"
        "  F -->|same parent| G[Fast-forward]\n"
        "  F -->|diverged| H[Branch-with-rename]\n"
        "  E --> I[ACL + share-link layer]\n"
        "  I --> J[Versioning + 30-day trash + async GC]"
    ),
    tradeoff_title="Conflict Resolution Strategy",
    tradeoff_options=[
        {"label": "Last-write-wins (LWW)",
         "description": "Server keeps the most recent commit by timestamp; older edit is overwritten.",
         "pros": ["Trivial to implement", "Tree stays clean", "Cheap on metadata"],
         "cons": ["Silently discards offline edits", "Clock-skew dependent",
                 "Worst failure mode (data loss) is invisible to user"]},
        {"label": "Branch-with-rename",
         "description": "Loser commit becomes a parallel file `name (device's conflicted copy date).ext`.",
         "pros": ["Zero silent data loss", "User decides which to keep",
                 "Dropbox/Drive industry-standard behaviour"],
         "cons": ["Tree clutter", "Slightly more metadata", "User must manually reconcile"]},
        {"label": "OT / CRDT live merge",
         "description": "Operational transform or CRDT character-level merge (Google Docs model).",
         "pros": ["True concurrent editing", "No conflicted-copy files"],
         "cons": ["Only works for known structured formats", "Heavy editor-service dependency",
                 "Wrong layer for arbitrary binaries"]},
    ],
    tradeoff_rec=(
        "Branch-with-rename as the default for arbitrary files; layer OT/CRDT on top for first-class "
        "doc/sheet/slide types. LWW only for opaque metadata fields no human ever inspects."
    ),
    senior_topics=[
        _topic("rolling-hash-chunking",
               "Content-Defined Chunking with Rolling Hashes",
               "Why a Rabin-Karp boundary makes 1-byte inserts cost one block instead of the whole tail "
               "of the file, and the dedupe gains it brings across users.",
               [
                   ("Why fixed-size fails on inserts",
                    "Insert 1 byte at the start of a 1 GB file with fixed 4 MB blocks: every block hash "
                    "shifts by 1 byte → 250 new hashes → re-upload the entire file. Useless on logs, "
                    "code, prose."),
                   ("Rabin-Karp boundary",
                    "Slide a 48-byte window; cut a block when the rolling hash matches a fixed bit "
                    "pattern. Boundaries are content-determined, so a local edit only invalidates the "
                    "blocks containing the change."),
                   ("Cross-user dedupe",
                    "Same Linux ISO uploaded by 100K users → stored once. Block table refcount drives "
                    "GC. Even per-user, large folders share boilerplate (fonts, libraries, npm caches)."),
                   ("When to skip",
                    "Encrypted-client-side files have random ciphertext — no dedupe, fixed-size is fine. "
                    "Already-compressed media (mp4, zip) sees minor wins; default to fixed 4 MB there."),
               ],
               diagram=(
                   "graph LR\n"
                   "  F[file bytes] --> R[rolling hash window]\n"
                   "  R --> B1[block1 hash]\n"
                   "  R --> B2[block2 hash]\n"
                   "  R --> B3[block3 hash]\n"
                   "  B1 --> S[block store keyed by hash]\n"
                   "  B2 --> S\n"
                   "  B3 --> S"
               )),
        _topic("permission-inheritance",
               "ACLs, Inheritance, and Link-Token Revocation",
               "How effective permissions are computed across nested folders, and what happens the "
               "instant an admin revokes a public link.",
               [
                   ("Effective permission",
                    "Walk from the file up the parent chain collecting ACL rows; combine with direct "
                    "grants. Highest role wins. Cache the resolved set per (user_id, file_id) for hot "
                    "paths and invalidate on any ancestor ACL change."),
                   ("Materialised inherited rows",
                    "On grant, write inherited rows for every descendant so checks are O(1). Re-derive "
                    "on move/rename. Trade write amplification for read latency — almost always the "
                    "right call for sharing-heavy workloads."),
                   ("Link tokens",
                    "Public links are HMAC-signed tokens carrying file_id, role, and expiry. Stored "
                    "row tracks revocation flag; CDN tier honours a short token cache, so revoke "
                    "= flip flag + invalidate cache by tag → globally effective in seconds."),
                   ("Org policy overlay",
                    "Enterprise admins can force-deny external sharing; that policy evaluates AFTER "
                    "ACLs and can override any allow. Keep policy in its own layer so it is auditable "
                    "independently."),
               ]),
        _topic("trash-and-block-gc",
               "Trash, Versioning, and Refcount-Zero Block Reaping",
               "How a soft-delete and version-restore UX is built on top of immutable versions and an "
               "async block GC, with the compliance hard-delete path layered on.",
               [
                   ("Immutable versions",
                    "Every commit creates a new version row pointing at a block list. Restore = swap "
                    "head pointer; no blocks move. History scan = file_id range query."),
                   ("Soft delete",
                    "Set `deleted_at`; file disappears from listings but versions and blocks stay. "
                    "Un-delete is a metadata flip. Quota counts deleted bytes for 30 days."),
                   ("Async block GC",
                    "Sweeper decrements refcounts when versions expire; a separate reaper deletes "
                    "blocks at refcount 0 with hours of lag, so an immediate un-delete never races a "
                    "physical purge."),
                   ("Compliance hard-delete",
                    "Right-to-erasure must purge across all replicas and tiers within 30 days. "
                    "Tracked as a separate workflow with explicit completion receipts; do NOT bolt it "
                    "onto best-effort GC."),
               ]),
    ],
)
