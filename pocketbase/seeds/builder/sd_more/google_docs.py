"""SDQ — Design Google Docs (Real-Time Collaborative Editor).

Real-time collaborative rich-text editor. Operational Transform with a central
server (Google's actual approach) compared to CRDTs (Yjs/Automerge), with deep
treatment of the document model, conflict transformation, offline reconciliation,
presence, comments/suggestions, version history, sharing/ACLs, undo semantics,
and snapshotting/log compaction. Mirrors `sd_questions.SD_01` shape via the
`_q` / `_topic` helpers.
"""
from __future__ import annotations

from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design Google Docs (Collaborative Editor)",
    "Hard",
    "Design a web-based real-time collaborative rich-text editor. Many users open the same document, "
    "edit concurrently, and see each other's keystrokes within ~100 ms. The system preserves user intent "
    "under concurrent edits, supports offline editing with reconciliation on reconnect, renders presence "
    "(live cursors and selections), threaded comments and suggestions, full version history with named "
    "checkpoints, sharing via ACLs and link tokens, sane undo semantics in a multi-author session, and "
    "scales to documents with hundreds of concurrent editors and a corpus of billions of documents.",
    hints=[
        "Core split: rich-text document model + concurrency control engine + transport.",
        "OT (Operational Transform) vs CRDT is THE design fork — Google Docs uses OT with a central server.",
        "Operations carry a revision number; the server linearises and transforms incoming ops against the gap.",
        "Offline: client buffers ops; on reconnect server transforms them onto the new head.",
        "Presence (cursors/selections) is ephemeral state, NOT in the op log — different transport.",
        "Undo in collab is per-user — must skip over other users' ops, transforming as needed.",
        "Snapshot + log compaction keeps op history bounded; full history reconstructible from snapshot+ops.",
    ],
    constraints=[
        "Edit-to-remote-render p95 < 100 ms within a region; < 250 ms cross-region.",
        "Hundreds of concurrent editors per document; pathological cases up to ~1000.",
        "Offline edits replay correctly even after hours offline; never silently lose user keystrokes.",
        "Documents up to ~50 MB serialised rich text; embedded images are blobs out-of-band.",
        "Billions of documents; read:write ≈ 50:1; long-tailed access pattern.",
        "Strong session correctness: every client converges to the same final document state.",
    ],
    req_func=[
        "Create, open, edit, and persist rich-text documents (formatting, lists, tables, links, images).",
        "Concurrent multi-user editing with intent-preserving conflict resolution.",
        "Live presence: cursors, selections, name labels, typing indicators.",
        "Offline editing with deterministic reconciliation on reconnect.",
        "Threaded inline comments anchored to text spans; suggestions / track-changes mode.",
        "Version history: timestamped snapshots, named versions, restore prior version.",
        "Sharing: per-principal ACLs (viewer/commenter/editor/owner) and link tokens with role.",
        "Per-user undo/redo that respects collaborative ops from other authors.",
    ],
    req_nonfunc=[
        "Convergence: all clients of a document reach identical final state (CC, IP, TP2 properties).",
        "Sub-100 ms intra-region keystroke echo; sub-second cross-region.",
        "Durability: zero acknowledged-op loss; RPO ≈ 0 for committed ops.",
        "Scale: 1B+ documents, 100M+ DAU, 10M+ concurrent editing sessions.",
        "Availability ≥ 99.99%; soft-degrade to read-only on backend partition.",
        "Bandwidth efficient — character-level ops, not full-document diffs.",
    ],
    estimation={
        "documents": "1B stored, ~10M opened per hour",
        "concurrent_sessions": "~10M concurrent edit sessions globally",
        "ops_per_session": "~2 ops/sec/user during active editing",
        "ops_qps_steady": "~2-5M ops/sec aggregate",
        "ops_qps_peak": "~20M ops/sec (workday handoffs across regions)",
        "avg_doc_size": "~50 KB serialised; tail to ~50 MB",
        "op_size": "~80-200 bytes per op (insert/delete/format)",
        "snapshot_cadence": "every ~1000 ops or 5 minutes idle, whichever first",
    },
    endpoints=[
        {"method": "POST", "path": "/v1/docs",
         "description": "Create a new document; returns doc_id and initial revision",
         "body": "{title, parent_folder_id, kind:'doc'}"},
        {"method": "GET", "path": "/v1/docs/{doc_id}",
         "description": "Load document head: latest snapshot + ops since snapshot + ACL summary"},
        {"method": "WSS", "path": "/v1/docs/{doc_id}/session",
         "description": "Persistent session: client sends ops with rev, receives transformed ops + acks; presence on side channel",
         "body": "{op, base_rev, client_id, op_seq}"},
        {"method": "POST", "path": "/v1/docs/{doc_id}/ops",
         "description": "REST fallback: submit a batch of ops with base_rev (used when WSS blocked)",
         "body": "{ops:[...], base_rev}"},
        {"method": "GET", "path": "/v1/docs/{doc_id}/history",
         "description": "List versions / named checkpoints with timestamps and authors"},
        {"method": "POST", "path": "/v1/docs/{doc_id}/restore",
         "description": "Restore a prior version as new head (creates a forward op set, not a rewind)",
         "body": "{version_id}"},
        {"method": "POST", "path": "/v1/docs/{doc_id}/comments",
         "description": "Create a comment thread anchored to an op-relative range",
         "body": "{anchor:{start_op, end_op, offset_start, offset_end}, body}"},
        {"method": "POST", "path": "/v1/docs/{doc_id}/suggestions/{sid}/accept",
         "description": "Accept a suggestion: materialise its ops into the main op log"},
        {"method": "POST", "path": "/v1/share",
         "description": "Grant ACL or mint a share link with role",
         "body": "{doc_id, principal|link, role}"},
    ],
    tables=[
        {"name": "documents",
         "columns": ["doc_id BIGINT PK", "owner_user_id BIGINT", "title VARCHAR(512)",
                     "parent_folder_id BIGINT NULL", "current_rev BIGINT", "head_snapshot_id BIGINT",
                     "created_at BIGINT", "updated_at BIGINT", "deleted_at BIGINT NULL"]},
        {"name": "doc_ops",
         "columns": ["doc_id BIGINT", "rev BIGINT", "author_user_id BIGINT",
                     "client_id VARCHAR(64)", "op_seq INT", "op_kind VARCHAR(16)",
                     "op_payload BLOB", "ts BIGINT",
                     "PRIMARY KEY (doc_id, rev)"]},
        {"name": "doc_snapshots",
         "columns": ["snapshot_id BIGINT PK", "doc_id BIGINT", "rev BIGINT",
                     "blob_ref VARCHAR(128)", "size BIGINT", "ts BIGINT"]},
        {"name": "doc_versions",
         "columns": ["version_id BIGINT PK", "doc_id BIGINT", "rev BIGINT",
                     "name VARCHAR(255) NULL", "kind ENUM('auto','named','restored')",
                     "author_user_id BIGINT", "ts BIGINT"]},
        {"name": "comments",
         "columns": ["comment_id BIGINT PK", "doc_id BIGINT", "thread_id BIGINT",
                     "anchor_payload BLOB", "author_user_id BIGINT",
                     "body TEXT", "resolved BOOLEAN", "ts BIGINT"]},
        {"name": "suggestions",
         "columns": ["suggestion_id BIGINT PK", "doc_id BIGINT", "ops BLOB",
                     "author_user_id BIGINT", "state ENUM('open','accepted','rejected')",
                     "ts BIGINT"]},
        {"name": "acls",
         "columns": ["acl_id BIGINT PK", "doc_id BIGINT", "principal_id BIGINT",
                     "role ENUM('viewer','commenter','editor','owner')",
                     "inherited BOOLEAN"]},
        {"name": "share_links",
         "columns": ["token CHAR(32) PK", "doc_id BIGINT", "role VARCHAR(16)",
                     "expires_at BIGINT NULL", "revoked BOOLEAN"]},
        {"name": "presence",
         "columns": ["session_id VARCHAR(64) PK", "doc_id BIGINT", "user_id BIGINT",
                     "cursor_anchor BLOB", "selection_anchor BLOB",
                     "color INT", "last_heartbeat_ts BIGINT"]},
    ],
    indexes=[
        "(doc_id, rev) on doc_ops — append + range scan since rev",
        "(doc_id, rev DESC) on doc_snapshots — find latest snapshot ≤ rev",
        "(doc_id, ts DESC) on doc_versions — history listing",
        "(doc_id, thread_id, ts) on comments — render thread chronology",
        "(doc_id, state) on suggestions — open suggestion list",
        "(doc_id, principal_id) on acls — permission resolution",
        "(token) on share_links — link redemption",
        "(doc_id, last_heartbeat_ts) on presence — live editor list (TTL pruned)",
    ],
    hld_desc=(
        "Three-tier architecture. Edge: WebSocket-terminating gateway with sticky routing per "
        "doc_id. Core: a stateful Document Server owns the in-memory authoritative state for each "
        "open document — a single goroutine/actor per doc serialises all ops, transforms incoming "
        "ops against the gap (Operational Transform), assigns a strictly monotonic revision number, "
        "broadcasts the transformed op to peers, and append-writes to the durable op log. Storage: "
        "op log in a partitioned, replicated commit log (Spanner / Bigtable-class), periodic "
        "snapshots in object storage. Auxiliary services handle presence (ephemeral pub/sub), "
        "comments and suggestions (regular CRUD with op-anchored ranges), version history "
        "(snapshot + named version pointers), ACLs and share links (Drive-shared permission "
        "service), and a search/indexer pipeline that consumes the op log asynchronously."
    ),
    hld_components=[
        {"name": "Web/Mobile Client", "role": "Local document model + OT engine; render, undo stack, presence"},
        {"name": "Edge / WS Gateway", "role": "TLS, auth, sticky route to the doc's owning server"},
        {"name": "Document Server", "role": "Authoritative in-memory state; per-doc actor; OT transform + linearise"},
        {"name": "Op Log Store", "role": "Append-only durable log of all ops, partitioned by doc_id"},
        {"name": "Snapshot Store", "role": "Periodic full-doc blobs in object storage"},
        {"name": "Version History Service", "role": "Named versions, restore, per-doc timeline"},
        {"name": "Presence Service", "role": "Ephemeral pub/sub for cursors/selections; Redis-class"},
        {"name": "Comments / Suggestions Service", "role": "Anchored threads + reviewer suggestions"},
        {"name": "Permission Service", "role": "ACL + share-link resolution; integrates with Drive"},
        {"name": "Indexer / Search", "role": "Async stream over op log; full-text + metadata index"},
        {"name": "GC / Compaction Worker", "role": "Snapshot cadence, op-log compaction, trash purge"},
    ],
    detailed_design={
        "document_model": (
            "Rich text modeled as an ordered sequence of character spans with attribute maps "
            "(bold, italic, link, color, list-level, paragraph style). Embedded objects (images, "
            "tables, equations) are nodes with stable ids and out-of-band blob refs. The atomic "
            "ops are: INSERT(pos, text, attrs), DELETE(pos, len), FORMAT(range, attr_delta), "
            "INSERT_OBJECT(pos, object_ref). Each op carries author_user_id, client_id, op_seq, "
            "and base_rev. The model is a single linear address space; tables/lists are spans "
            "with structural attributes — keeping ops one-dimensional makes OT tractable."
        ),
        "ot_pipeline": (
            "Client maintains a local revision number `rev_local`. When typing, it applies the op "
            "locally (optimistic) and sends {op, base_rev=rev_local}. Server holds authoritative "
            "rev. If incoming op.base_rev == server.rev: accept, assign rev+1, broadcast. If "
            "base_rev < server.rev: server transforms op against every op in the gap "
            "(server.ops[base_rev+1 .. server.rev]) using the operation-transformation function "
            "T(op_a, op_b) — e.g., insert at pos=10 transformed against a prior insert(pos=5, "
            "len=3) becomes insert(pos=13). Result is appended at server.rev+1. Server returns an "
            "ACK with the assigned rev plus all gap ops; client transforms its outstanding "
            "buffered ops the symmetric way and rebases its local view."
        ),
        "ot_vs_crdt": (
            "Google chose OT with a central server in 2010 because: (1) OT keeps payloads tiny — "
            "ops are intent (insert at pos 7), not large vector clocks or position identifiers "
            "growing over time; (2) the central server linearises trivially (no peer-to-peer "
            "merge needed); (3) rich-text intents like format-range and structural attrs map "
            "naturally to OT ops. CRDTs (Yjs, Automerge) trade payload size and position-id "
            "growth for true peer-to-peer convergence with no server-side transform; great for "
            "decentralised or P2P, less ideal when you already have a central authoritative "
            "service. Modern picks lean CRDT for new systems because the math is simpler and "
            "implementations have caught up — but Docs is OT, deeply."
        ),
        "convergence_properties": (
            "Correctness checks: CC (causality preservation — never apply child op before parent), "
            "CP1 / TP1 (transformed ops produce identical state regardless of order), TP2 "
            "(diamond property: T(T(a,b), T(c,b)) == T(T(a,c), T(b,c))). Central-server OT only "
            "needs CP1/TP1 because the server linearises; peer-to-peer OT (Jupiter) needs TP2 "
            "and is famously hard. Google's central-server design sidesteps TP2 — a major reason "
            "the architecture stays simple."
        ),
        "offline_reconciliation": (
            "Offline client keeps applying ops to local state and pushing them onto an outbox "
            "queue, each tagged with its base_rev (frozen at time of disconnect). On reconnect: "
            "client pulls server.ops since its base_rev (the gap). For each outbox op, transform "
            "it against the cumulative gap (and against earlier transformed-outbox ops). Send the "
            "transformed batch; server applies in order. The client's local view is rebased: "
            "discard the optimistic state, re-derive from snapshot + server gap + transformed "
            "outbox. UX: never reject a user keystroke, but if the doc was deleted or ACL revoked "
            "while offline, surface a clear 'this version was orphaned' export-only mode."
        ),
        "presence": (
            "Cursors and selections are NOT in the op log — they are ephemeral and high-frequency. "
            "Presence flows over a separate pub/sub channel (Redis Pub/Sub or equivalent) keyed "
            "by doc_id. Each client publishes {session_id, user_id, cursor_anchor, "
            "selection_anchor, color} on change with a heartbeat TTL of ~10 s. Cursor anchors are "
            "expressed in op-relative terms (target_op_id, offset) so concurrent edits naturally "
            "shift the cursor — when an op transforms, the presence transformer updates anchors "
            "the same way. On session drop (heartbeat miss), the cursor is reaped and disappears "
            "from peers' UIs."
        ),
        "comments_suggestions": (
            "Comments anchor to op-relative ranges {start_op_id, end_op_id, offset_start, "
            "offset_end}. When an editor op shifts the underlying text, the comment-range "
            "transformer adjusts anchors using the same OT logic; if the anchor's op is deleted, "
            "the comment becomes 'orphaned' but stays visible against the most-recent surviving "
            "context (don't silently drop). Suggestions are a parallel op-set on a side branch — "
            "stored as a pending ops list with author and rationale. Accepting a suggestion means "
            "transforming its ops onto the current head and appending them as a normal commit; "
            "rejecting just discards the side-branch entry."
        ),
        "version_history": (
            "Auto-versions are created at quiescent points (idle for ~5 min) or every ~1000 ops. "
            "Named versions are user-triggered checkpoints. Each version row stores doc_id and "
            "the rev pointer; the underlying snapshot may be the auto-snapshot at or near that "
            "rev plus the ops needed to advance to exactly that rev. Restore does NOT rewind — it "
            "creates a forward op-set that re-derives the older content as a new commit, "
            "preserving the linear log (rewind would break OT for any concurrently connected "
            "editor). Diff between versions = render(snapshot_a + ops) vs render(snapshot_b + "
            "ops) with a structural diff highlighter."
        ),
        "sharing_acls": (
            "Permissions tier is the same as Drive's: ACL rows attach to doc_id with "
            "viewer/commenter/editor/owner roles, inherited from parent folders, with "
            "materialised inherited rows for O(1) checks. Share links are HMAC-signed tokens "
            "carrying doc_id + role + expiry, with a revocation flag. The permission check runs "
            "at session-establish AND on every op-write — revocation mid-session forcibly closes "
            "the WSS channel within seconds. Commenter role is enforced at op level: the server "
            "rejects INSERT/DELETE/FORMAT but accepts comment-thread ops."
        ),
        "undo_in_collab": (
            "Per-user undo is the senior signal. Naive 'undo the last op in the global log' "
            "would let user A undo user B's keystroke. Correct semantics: each client maintains a "
            "user-scoped undo stack of its own ops; undo emits the inverse op (e.g., DELETE for "
            "a prior INSERT) but transformed against all intervening ops from other users. If "
            "the targeted op was already overwritten by a peer's op, the undo gracefully "
            "no-ops. Redo is symmetric on the redo stack. Selection state is captured per-undo-"
            "frame so the cursor restores intuitively. Implementation: undo stack stores the "
            "INVERSE op + the rev at which the original was committed, so the transform path is "
            "deterministic."
        ),
        "snapshot_compaction": (
            "Op log grows linearly with edits — billions of ops would dominate cost and replay "
            "time. Compaction strategy: (1) every ~1000 ops or every 5 min idle, the Document "
            "Server emits a snapshot — full materialised doc state at rev R, written to object "
            "storage with snapshot_id; (2) version-history pointers reference snapshots by id; "
            "(3) op log retains all ops indefinitely for legal-hold and version-history "
            "rebuilding, BUT load path is `latest_snapshot + ops_after(snapshot.rev)`, so "
            "open-doc cost is bounded; (4) hot snapshot cached at the Document Server and at "
            "the edge for warm restarts."
        ),
        "transport_consistency": (
            "Primary transport is WebSocket with sticky routing: the gateway hashes doc_id to "
            "the owning Document Server. On server failover, the new owner replays from "
            "latest_snapshot + ops, then accepts new sessions; clients reconnect and resume from "
            "their last-acked rev. REST fallback for environments that block WSS — clients long-"
            "poll /ops with their base_rev. Idempotency: every op carries a (client_id, op_seq) "
            "tuple; the server dedupes on this pair so retries during disconnect are safe."
        ),
        "slo_contract": (
            "Op echo p95 < 100 ms intra-region, < 250 ms cross-region; durability of acked ops = "
            "0 loss (Spanner-class storage); session-establish p99 < 500 ms; share-revoke "
            "globally effective ≤ 5 s; convergence: 100% of clients reach identical state on a "
            "given rev."
        ),
    },
    trade_offs=[
        {"option": "Operational Transform vs CRDT",
         "for_ot": "Tiny ops, central linearisation, well-suited to rich text intents",
         "for_crdt": "True peer-to-peer convergence, simpler math, no transform server",
         "recommendation": "Central-server OT for a Docs-class product (Google's actual choice). CRDT for offline-first, multi-master, or P2P. New systems often pick CRDT now because the implementations matured."},
        {"option": "Central authoritative server vs peer-to-peer mesh",
         "for_central": "Single linearisation point, simpler conflict math, easy snapshots",
         "for_p2p": "No server bottleneck, works on LAN/disconnected",
         "recommendation": "Central — Docs scale comes from horizontal sharding by doc_id, not P2P."},
        {"option": "WebSocket vs long-poll",
         "for_websocket": "Sub-100 ms echo, low overhead per op",
         "for_long_poll": "Works through any proxy/firewall, simple recovery",
         "recommendation": "WebSocket primary, long-poll fallback for restricted networks."},
        {"option": "Per-user undo vs global undo",
         "for_per_user": "Matches user mental model; no surprise reverts of others' work",
         "for_global": "Trivial implementation",
         "recommendation": "Per-user with op-transform on the inverse. Global undo is the junior trap."},
        {"option": "Snapshot cadence: aggressive vs lazy",
         "for_aggressive": "Fast cold-open, small replay tail",
         "for_lazy": "Lower storage cost, fewer writes",
         "recommendation": "Aggressive on active docs (every 1000 ops), lazy on cold (only on access). Hybrid wins."},
    ],
    tips=[
        "Lead with the OT-vs-CRDT fork and pick OT for a Google-Docs-style central design. State the reason.",
        "Be specific about T(op_a, op_b) — say 'insert(10) transformed past insert(5,len=3) becomes insert(13)'. That sentence earns the senior signal.",
        "Keep presence OFF the op log — it's ephemeral pub/sub. Conflating the two is a junior trap.",
        "Per-user undo with inverse-op transformation is the question that separates seniors from staff.",
        "Restore-by-forward-op, not rewind, is correct because rewind breaks live editors. State this explicitly.",
        "Snapshot + log compaction bounds open-doc latency — quote 'open = latest snapshot + tail ops'.",
        "Idempotency via (client_id, op_seq) makes retries safe across disconnects — name it.",
    ],
    thought_process=[
        "1. Clarify scope: rich-text editor, multi-user concurrent, offline-tolerant, presence, comments, versions, sharing.",
        "2. Estimate: 10M concurrent sessions × 2 ops/sec ≈ 20M ops/sec peak; bound payloads at ~100 B/op.",
        "3. Concurrency model: pick OT (central server, Google's actual choice) over CRDT; explain trade-off.",
        "4. Document model: linear sequence of spans with attrs; ops INSERT/DELETE/FORMAT/INSERT_OBJECT.",
        "5. Protocol: WSS with op {op, base_rev, client_id, op_seq}; server transforms gap and assigns monotonic rev.",
        "6. Storage: per-doc actor in memory; durable append-only op log + periodic snapshots.",
        "7. Offline: outbox of ops with frozen base_rev; reconcile by transforming against the gap on reconnect.",
        "8. Presence on a separate pub/sub channel; cursor anchors are op-relative and transform with edits.",
        "9. Comments anchor to op ranges; suggestions are side-branch op-sets accepted by transforming + appending.",
        "10. Version history: snapshot + named pointers; restore is forward-op, never rewind.",
        "11. Sharing: ACL + share-link; permission check at session-open and at every op write.",
        "12. Undo: per-user inverse-op with OT against intervening peer ops.",
        "13. Compaction: snapshot every ~1000 ops; load path = snapshot + tail ops to bound open latency.",
        "14. SLOs: < 100 ms echo, zero acked-op loss, convergence on every rev.",
    ],
    tags=["collaboration", "crdt", "ot", "real-time", "editor"],
    arch_nodes=[
        {"id": "client", "label": "Web/Mobile Client", "type": "client"},
        {"id": "edge", "label": "WS Gateway", "type": "lb"},
        {"id": "doc", "label": "Document Server", "type": "server"},
        {"id": "oplog", "label": "Op Log Store", "type": "database"},
        {"id": "snap", "label": "Snapshot Store", "type": "database"},
        {"id": "presence", "label": "Presence Pub/Sub", "type": "cache"},
        {"id": "comments", "label": "Comments/Suggest Svc", "type": "service"},
        {"id": "versions", "label": "Version History Svc", "type": "service"},
        {"id": "perms", "label": "Permission Svc", "type": "service"},
        {"id": "indexer", "label": "Search Indexer", "type": "service"},
        {"id": "gc", "label": "GC / Compaction", "type": "service"},
    ],
    arch_edges=[
        {"source": "client", "target": "edge", "label": "WSS"},
        {"source": "edge", "target": "doc", "label": "sticky by doc_id"},
        {"source": "doc", "target": "oplog", "label": "append op @ rev"},
        {"source": "doc", "target": "snap", "label": "snapshot every ~1000 ops"},
        {"source": "doc", "target": "presence", "label": "publish cursor"},
        {"source": "presence", "target": "client", "label": "fan-out cursors"},
        {"source": "client", "target": "comments", "label": "thread CRUD"},
        {"source": "client", "target": "versions", "label": "history list/restore"},
        {"source": "edge", "target": "perms", "label": "ACL check"},
        {"source": "doc", "target": "perms", "label": "per-op authorise"},
        {"source": "oplog", "target": "indexer", "label": "stream"},
        {"source": "gc", "target": "oplog", "label": "compact"},
        {"source": "gc", "target": "snap", "label": "tier cold"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant A as Client A\n"
        "  participant G as WS Gateway\n"
        "  participant D as Doc Server\n"
        "  participant L as Op Log\n"
        "  participant B as Client B\n"
        "  A->>G: open doc_id (auth, ACL)\n"
        "  G->>D: route, attach session\n"
        "  D-->>A: snapshot @ rev=42 + tail ops\n"
        "  B->>D: insert(pos=10, 'x') base_rev=42\n"
        "  D->>D: rev 42==head, accept as rev=43\n"
        "  D->>L: append rev=43\n"
        "  D-->>B: ack rev=43\n"
        "  D-->>A: op rev=43 insert(pos=10,'x')\n"
        "  A->>D: insert(pos=10,'y') base_rev=42\n"
        "  D->>D: gap=[rev43]; transform: pos=10 → pos=11\n"
        "  D->>L: append rev=44 insert(pos=11,'y')\n"
        "  D-->>A: ack rev=44 (transformed)\n"
        "  D-->>B: op rev=44 insert(pos=11,'y')"
    ),
    er_diagram=(
        "erDiagram\n"
        "  USER ||--o{ DOCUMENT : owns\n"
        "  DOCUMENT ||--o{ DOC_OP : log\n"
        "  DOCUMENT ||--o{ DOC_SNAPSHOT : snapshots\n"
        "  DOCUMENT ||--o{ DOC_VERSION : versions\n"
        "  DOCUMENT ||--o{ COMMENT : annotates\n"
        "  DOCUMENT ||--o{ SUGGESTION : reviews\n"
        "  DOCUMENT ||--o{ ACL : grants\n"
        "  DOCUMENT ||--o{ SHARE_LINK : exposes\n"
        "  DOCUMENT ||--o{ PRESENCE : has\n"
        "  DOC_OP }o--|| USER : authored-by"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B[OT vs CRDT?]\n"
        "  B -->|central server| C[OT pipeline]\n"
        "  C --> D[Op = insert/delete/format + base_rev]\n"
        "  D --> E[Server transforms gap, assigns monotonic rev]\n"
        "  E --> F[Broadcast + append to log]\n"
        "  F --> G{Offline?}\n"
        "  G -->|yes| H[Outbox; reconcile on reconnect]\n"
        "  G -->|no| I[Optimistic local apply]\n"
        "  E --> J[Presence pub/sub off-log]\n"
        "  E --> K[Comments anchored to op ranges]\n"
        "  E --> L[Snapshot every ~1000 ops]\n"
        "  L --> M[Open doc = snapshot + tail ops]\n"
        "  E --> N[Per-user undo via inverse-op transform]"
    ),
    tradeoff_title="Concurrency Model: OT vs CRDT",
    tradeoff_options=[
        {"label": "Operational Transform (central server)",
         "description": "Clients send intent ops with base_rev; central server transforms against the gap and linearises.",
         "pros": ["Tiny ops (~80-200 B)", "Natural fit for rich-text intent (insert at pos, format range)",
                 "Central linearisation avoids TP2 — simpler math", "Battle-tested in Google Docs"],
         "cons": ["Requires authoritative server in the path", "Transform functions are tricky for structural ops",
                 "Implementer must own the OT library — few good open-source options"]},
        {"label": "CRDT (Yjs / Automerge)",
         "description": "Each op carries position identifiers that are globally unique and ordered; merges commute.",
         "pros": ["True peer-to-peer convergence with no server transform", "Simpler theoretical model",
                 "Excellent for offline-first and decentralised", "Mature OSS libraries (Yjs, Automerge)"],
         "cons": ["Position identifiers grow over time → bloat", "Larger payloads than OT",
                 "Garbage collection of tombstones is non-trivial", "Less natural for rich-text formatting attrs"]},
        {"label": "Per-character locking / pessimistic",
         "description": "Acquire a lock on a span before editing.",
         "pros": ["Trivial mental model", "No conflict math"],
         "cons": ["Latency-fatal for typing UX", "Doesn't scale beyond a few users",
                 "Lock contention on hot paragraphs"]},
    ],
    tradeoff_rec=(
        "Operational Transform with a central authoritative server — Google's actual choice. Pick CRDT (Yjs) "
        "instead if the requirement is offline-first multi-master with no central authority, or for new "
        "systems where the math simplification outweighs the payload cost. Pessimistic locking is "
        "non-viable for an interactive editor."
    ),
    senior_topics=[
        _topic("ot-transform-function",
               "The Operation-Transformation Function in Practice",
               "How T(op_a, op_b) actually works for the three core rich-text op kinds, why the central-server "
               "model only needs CP1/TP1, and the pitfalls when structural attributes enter the picture.",
               [
                   ("Insert vs Insert",
                    "T(insert(pos=10, 'x'), insert(pos=5, 'abc')) = insert(pos=13, 'x'). The earlier insert "
                    "shifts the later by len(other.text). Tie-break on equal pos by client_id ordering so "
                    "both sides converge."),
                   ("Insert vs Delete",
                    "T(insert(pos=10, 'x'), delete(pos=5, len=3)) = insert(pos=7, 'x'). If delete spans the "
                    "insert pos, the insert lands at the start of the deleted range — never inside a deleted "
                    "span, since that span no longer exists."),
                   ("Delete vs Delete",
                    "Overlapping deletes: shrink the later delete to remove only the still-present subrange. "
                    "If fully covered → no-op. This is the case where naive implementations lose characters."),
                   ("Format vs Edit",
                    "Formatting carries a range; transforming against a delete clamps the range; against an "
                    "insert with attribute_inheritance, the new chars adopt the surrounding format. Decide "
                    "the inheritance rule once and document it."),
                   ("Why TP2 isn't needed centrally",
                    "TP2 (diamond convergence under three-way concurrent merges) is required for "
                    "peer-to-peer OT. The central server linearises ops into a single sequence, so we only "
                    "need TP1 (transform-correctness against a known prefix). This is why Google's design "
                    "stays tractable."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant A\n  participant S\n  participant B\n"
                   "  Note over A,B: both at rev=10\n"
                   "  A->>S: insert(pos=5,'x') base_rev=10\n"
                   "  S->>S: accept as rev=11\n"
                   "  S-->>A: ack rev=11\n"
                   "  S-->>B: rev=11 insert(pos=5,'x')\n"
                   "  B->>S: insert(pos=8,'y') base_rev=10\n"
                   "  S->>S: T past rev=11 → insert(pos=9,'y')\n"
                   "  S-->>B: ack rev=12 (pos=9)\n"
                   "  S-->>A: rev=12 insert(pos=9,'y')"
               )),
        _topic("offline-reconciliation",
               "Offline Editing and Reconnect Reconciliation",
               "How a client that has been offline for hours reconciles its outbox of optimistic ops against "
               "the server's authoritative log without losing keystrokes or violating convergence.",
               [
                   ("Outbox shape",
                    "On disconnect, freeze base_rev = last-acked server rev. Each subsequent local op enters "
                    "the outbox tagged with that base_rev (NOT the moving local rev), with (client_id, "
                    "op_seq) for idempotency. Optimistic UI continues from the last acked state."),
                   ("Reconnect handshake",
                    "Client opens session with last_acked_rev. Server responds with snapshot + ops since "
                    "that rev (the 'gap'). Client applies the gap to a clean copy of the doc state, then "
                    "transforms each outbox op against the cumulative gap (and earlier transformed outbox "
                    "ops) before sending."),
                   ("Idempotent retries",
                    "Server dedupes incoming ops by (client_id, op_seq). If the connection drops mid-batch, "
                    "the client safely re-sends; server skips ops it has already committed and ACKs the "
                    "expected rev range."),
                   ("UX edge cases",
                    "If the doc was deleted while offline → degrade to read-only export. If the user lost "
                    "edit permission → keep local copy as a 'detached' draft and offer 'request access'. "
                    "Never silently discard offline keystrokes — that's the worst failure mode."),
                   ("Bounded outbox",
                    "Cap outbox size (e.g., 10 MB or 100k ops); past that, fold older outbox ops into a "
                    "client-local snapshot and submit as a forward-op-set. Prevents unbounded memory on "
                    "weeks-long offline sessions."),
               ],
               diagram=(
                   "graph LR\n"
                   "  L[local edits offline] --> O[outbox base_rev=R]\n"
                   "  O --> R[reconnect]\n"
                   "  R --> P[pull gap ops since R]\n"
                   "  P --> T[transform outbox vs gap]\n"
                   "  T --> S[send transformed batch]\n"
                   "  S --> A[server acks new revs]\n"
                   "  A --> V[client rebases local view]"
               )),
        _topic("undo-in-collab",
               "Per-User Undo Stack Semantics in a Collaborative Session",
               "Why naive 'undo last op' is wrong in multi-author editing, and how the inverse-op + "
               "transform pattern produces an undo that matches user expectations even when peers have "
               "edited around the targeted op.",
               [
                   ("Why global undo is wrong",
                    "A naive global undo lets user A undo user B's keystroke. Users expect 'undo MY last "
                    "action' — the stack must be partitioned per user."),
                   ("Inverse op + transform",
                    "When user A applies INSERT(pos=10, 'x') at rev=20, push onto A's undo stack: "
                    "{inverse: DELETE(pos=10, len=1), original_rev: 20}. On undo, transform the inverse "
                    "against all ops at rev>20 from any author, producing a current-rev DELETE that lands "
                    "in the right place — even if peers have inserted/deleted around it."),
                   ("Already-overwritten target",
                    "If a peer has already deleted the inserted character, the transformed inverse becomes "
                    "a no-op delete of length zero — the undo gracefully does nothing. Surface a subtle "
                    "'undo had no effect' indicator if desired; never raise an error."),
                   ("Selection restoration",
                    "Each undo frame stores the cursor/selection at the time of the original op, "
                    "transformed forward to current rev. Restoring selection on undo makes the UX feel "
                    "native; without it, undo feels broken even when correct."),
                   ("Redo symmetry",
                    "Redo stack mirrors undo with the original op (not the inverse). Same transform "
                    "discipline. Editing-while-undone should clear the redo stack — standard convention."),
               ]),
        _topic("snapshot-and-compaction",
               "Snapshot Cadence, Log Compaction, and Bounded Open-Doc Latency",
               "Operational discipline that keeps an append-only op log from blowing up open latency or "
               "storage cost, while preserving the auditability and version-history affordances users expect.",
               [
                   ("Why pure append-only doesn't scale",
                    "A document edited 10M times over years has 10M ops. Loading from rev=0 is unacceptable "
                    "(seconds-to-minutes of replay). Without compaction, open latency is unbounded."),
                   ("Snapshot cadence",
                    "Document Server emits a full materialised snapshot every ~1000 ops or after ~5 min "
                    "idle, whichever first. Snapshot is written async to object storage; snapshot_id and "
                    "rev are stored in doc_snapshots for lookup."),
                   ("Open path",
                    "Client open-doc fetches `latest_snapshot ≤ current_rev` plus the tail ops "
                    "(snapshot.rev, current_rev]. Bounded at ~1000 ops + one snapshot blob — sub-second "
                    "open even on multi-million-op documents."),
                   ("Op log retention",
                    "Keep all ops indefinitely for legal-hold and version-history reconstruction; older "
                    "ops can move to colder, cheaper storage tiers. Compaction never deletes ops — it "
                    "introduces snapshots that make replay cheap."),
                   ("Snapshot tiering",
                    "Hot snapshots cached in the Document Server's memory and at the edge for warm "
                    "restarts; cold snapshots live in object storage with lazy fetch. Version-history "
                    "navigation references snapshot_id directly so 'restore to last week' is O(snapshot)."),
                   ("Failure recovery",
                    "On Document Server crash, the new owner replays from latest snapshot + tail ops; "
                    "since ops are committed to the durable log before broadcast, no acked op is lost."),
               ],
               diagram=(
                   "graph LR\n"
                   "  OPS[op log: 0..N] --> S1[snapshot @ 1000]\n"
                   "  OPS --> S2[snapshot @ 2000]\n"
                   "  OPS --> SN[snapshot @ N - tail]\n"
                   "  OPEN[open doc] --> SN\n"
                   "  SN --> TAIL[+ ops since SN.rev]\n"
                   "  TAIL --> READY[ready in <1s]"
               )),
    ],
)
