"""SDQ — Design an Online Code Editor / Sandbox (Replit-style with execution).

A browser-based IDE that lets a user open a workspace, edit a multi-file project,
run arbitrary code in a sandboxed runtime, stream a live terminal, install
packages, and collaborate with others in real time. Covers the editor frontend
(Monaco/CodeMirror), per-workspace storage and persistent volumes, sandboxed
execution (Docker/Firecracker microVMs, gVisor, eBPF/seccomp), language runtime
provisioning, terminal/PTY streaming over WebSocket, real-time collaborative
editing (CRDT/OT — see Google Docs), package install (npm/pip), persistent vs
ephemeral state, container lifecycle (idle eviction + snapshot/restore),
networking with egress controls, abuse detection (crypto-mining, network
scanning), and CPU-second metering for billing. Mirrors `sd_questions.SD_01`
shape via the `_q` / `_topic` helpers.
"""
from __future__ import annotations

from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design an Online Code Editor / Sandbox",
    "Hard",
    "Design a Replit-style online IDE: a browser front-end where a user opens a workspace, edits "
    "a multi-file project, runs arbitrary code in a per-workspace sandbox, sees real-time program "
    "output and a live shell, installs packages from npm/pip, and optionally collaborates with "
    "others on the same files in real time. The system must isolate untrusted code from the host "
    "and from other tenants, persist a per-user file tree across sessions, lazily provision and "
    "evict containers to control cost, stream PTY output over WebSocket with low latency, meter "
    "CPU-seconds and egress for billing, and detect abuse (crypto mining, port scans, fork bombs). "
    "Scale is millions of workspaces, hundreds of thousands concurrent runs, polyglot runtimes.",
    hints=[
        "The hard core is sandboxed multi-tenant code execution. Editor + filesystem are well-trodden.",
        "Workspace = persistent volume (file tree) + an ephemeral runner (container/microVM) attached on demand.",
        "Container per workspace — never share an interpreter across tenants. Pick microVM (Firecracker) or gVisor for the kernel-isolation story.",
        "Idle eviction + snapshot/restore is the cost lever — don't keep idle runners hot.",
        "Terminal is a PTY in the runner streamed over WebSocket; framing is binary, ~16 KB chunks.",
        "Collab editing is the same OT/CRDT problem as Google Docs — point at that design and don't re-derive.",
        "Network egress is the abuse vector: per-workspace egress firewall + outbound DNS allowlist + bandwidth metering.",
        "Billing on CPU-seconds and egress bytes; meter inside the runtime, not at the orchestrator.",
    ],
    constraints=[
        "Cold-start a new runner in < 2 s p95 (microVM snapshot restore < 500 ms).",
        "Terminal echo p95 < 120 ms intra-region; PTY chunk delivery sub-200 ms cross-region.",
        "Hard-isolate every workspace from the host kernel and from every other tenant's processes/network/filesystem.",
        "Per-workspace defaults: 0.5 vCPU burst, 512 MB RAM, 1 GB persistent disk, 50 Mbps egress cap.",
        "Idle workspace evicted after ~60 s of no terminal/edit activity; snapshot preserves /tmp + RAM.",
        "Scale: 50M workspaces total, ~5M monthly active, ~200k concurrent runners at peak.",
        "Polyglot: at least Python, Node, Go, Rust, Java, C/C++ runtimes ready out of the box.",
        "No persistent code execution outside billed CPU-seconds — never let evicted workloads keep mining.",
    ],
    req_func=[
        "Create, open, edit, save a multi-file workspace (file tree + monorepo-style structure).",
        "Run arbitrary user code in a sandbox; stream stdout/stderr to the browser in real time.",
        "Live terminal (PTY) attached to the runner, with shell history and resize.",
        "Install packages from public registries (npm, pip, cargo, apt within an allowlist).",
        "Persistent file storage across sessions; ephemeral /tmp and process state can be lost.",
        "Real-time collaborative editing with cursors and selections (multi-user).",
        "Idle eviction + snapshot/restore of paused workspaces.",
        "Per-workspace networking: outbound by default, inbound only via tunnelled HTTPS preview URL.",
        "CPU-seconds and egress metering; per-tenant quotas with friendly limit-reached UX.",
        "Abuse detection: crypto-miner heuristics, outbound port scans, fork bombs, runaway disk fill.",
    ],
    req_nonfunc=[
        "Strong isolation: kernel-level sandbox (microVM or gVisor), seccomp, network namespaces, cgroup limits.",
        "Cold-start p95 < 2 s; warm reattach p95 < 300 ms.",
        "Terminal latency p95 < 120 ms intra-region.",
        "Workspace storage durability — zero loss of saved files; RPO < 5 s for autosave.",
        "Tenant-isolated noisy-neighbour: per-workspace cgroup CPU/RAM/IO caps enforced.",
        "Billable accuracy: CPU-second metering accurate to ±2%, egress accurate to byte.",
        "Multi-region with regional data residency for workspace volumes.",
        "Availability ≥ 99.95% for editor + autosave; runners may degrade to 'queued' under load.",
    ],
    estimation={
        "workspaces_total": "50M",
        "monthly_active": "5M",
        "concurrent_runners_peak": "~200k",
        "avg_workspace_size": "~120 MB on disk; tail to 1 GB cap",
        "avg_run_duration": "~3 min interactive, ~30 min for long-runners",
        "cpu_seconds_per_day": "~10B aggregate billed CPU-seconds",
        "egress_per_day": "~200 TB outbound from runners",
        "pty_throughput": "~50 KB/s per active terminal; bursty",
        "ops_per_collab_session": "~2 ops/sec/user (same as Google Docs)",
    },
    endpoints=[
        {"method": "POST", "path": "/v1/workspaces",
         "description": "Create a new workspace with a runtime template (python, node, etc.)",
         "body": "{name, template, visibility:'private|public', region}"},
        {"method": "GET", "path": "/v1/workspaces/{ws_id}",
         "description": "Fetch metadata + file tree + last-known runner state"},
        {"method": "POST", "path": "/v1/workspaces/{ws_id}/files",
         "description": "Create or update a file in the persistent volume",
         "body": "{path, content_b64, mode}"},
        {"method": "WSS", "path": "/v1/workspaces/{ws_id}/edit",
         "description": "Persistent collab edit channel; OT/CRDT ops with cursors (delegates to Docs-class engine)",
         "body": "{op, base_rev, client_id, op_seq}"},
        {"method": "POST", "path": "/v1/workspaces/{ws_id}/run",
         "description": "Boot or reattach the runner and execute the configured run command",
         "body": "{command, env, timeout_seconds}"},
        {"method": "WSS", "path": "/v1/workspaces/{ws_id}/pty",
         "description": "Bidirectional terminal: client sends keystrokes + resize; server streams PTY output",
         "body": "{kind:'data|resize|signal', payload}"},
        {"method": "POST", "path": "/v1/workspaces/{ws_id}/install",
         "description": "Run the package manager inside the runner (npm/pip/cargo) with a wrapped command",
         "body": "{manager, packages:[...]}"},
        {"method": "POST", "path": "/v1/workspaces/{ws_id}/snapshot",
         "description": "Snapshot the runner (memory + disk delta) for fast restore",
         "body": "{}"},
        {"method": "POST", "path": "/v1/workspaces/{ws_id}/stop",
         "description": "Cooperative stop + snapshot; idempotent"},
        {"method": "GET", "path": "/v1/workspaces/{ws_id}/preview",
         "description": "Returns the public HTTPS tunnel URL bound to a port inside the runner"},
        {"method": "POST", "path": "/v1/workspaces/{ws_id}/share",
         "description": "Invite a collaborator with role (viewer/editor/owner)",
         "body": "{principal, role}"},
        {"method": "GET", "path": "/v1/usage/{tenant_id}",
         "description": "Billed CPU-seconds, egress bytes, storage GB, current period"},
    ],
    tables=[
        {"name": "workspaces",
         "columns": ["ws_id BIGINT PK", "owner_user_id BIGINT", "name VARCHAR(255)",
                     "template VARCHAR(64)", "region VARCHAR(16)", "visibility VARCHAR(16)",
                     "volume_id VARCHAR(64)", "current_rev BIGINT",
                     "created_at BIGINT", "updated_at BIGINT", "deleted_at BIGINT NULL"]},
        {"name": "workspace_volumes",
         "columns": ["volume_id VARCHAR(64) PK", "ws_id BIGINT", "backend VARCHAR(16)",
                     "size_bytes BIGINT", "used_bytes BIGINT", "snapshot_blob_ref VARCHAR(128) NULL"]},
        {"name": "files",
         "columns": ["ws_id BIGINT", "path VARCHAR(1024)", "blob_ref VARCHAR(128)",
                     "size_bytes BIGINT", "mode INT", "updated_at BIGINT",
                     "PRIMARY KEY (ws_id, path)"]},
        {"name": "runners",
         "columns": ["runner_id VARCHAR(64) PK", "ws_id BIGINT", "host_id VARCHAR(64)",
                     "status VARCHAR(16)", "image_ref VARCHAR(128)",
                     "cpu_quota_micro INT", "mem_quota_bytes BIGINT",
                     "started_at BIGINT", "evicted_at BIGINT NULL"]},
        {"name": "runner_snapshots",
         "columns": ["snapshot_id VARCHAR(64) PK", "ws_id BIGINT", "runner_id VARCHAR(64)",
                     "memory_blob_ref VARCHAR(128)", "disk_delta_ref VARCHAR(128)",
                     "size_bytes BIGINT", "created_at BIGINT"]},
        {"name": "collab_ops",
         "columns": ["ws_id BIGINT", "rev BIGINT", "author_user_id BIGINT",
                     "client_id VARCHAR(64)", "op_seq INT", "file_path VARCHAR(1024)",
                     "op_kind VARCHAR(16)", "op_payload BLOB", "ts BIGINT",
                     "PRIMARY KEY (ws_id, rev)"]},
        {"name": "acls",
         "columns": ["acl_id BIGINT PK", "ws_id BIGINT", "principal_id BIGINT",
                     "role VARCHAR(16)"]},
        {"name": "usage_events",
         "columns": ["event_id BIGINT PK", "tenant_id BIGINT", "ws_id BIGINT",
                     "kind VARCHAR(16)", "value_micro BIGINT", "ts BIGINT"]},
        {"name": "abuse_signals",
         "columns": ["signal_id BIGINT PK", "ws_id BIGINT", "kind VARCHAR(32)",
                     "score FLOAT", "evidence BLOB", "ts BIGINT", "action VARCHAR(16)"]},
    ],
    indexes=[
        "(owner_user_id, updated_at DESC) on workspaces — recent workspace list",
        "(ws_id, path) on files — directory listing + file open",
        "(ws_id, status) on runners — find live runner for a workspace",
        "(ws_id, created_at DESC) on runner_snapshots — pick latest snapshot for restore",
        "(ws_id, rev) on collab_ops — append + range scan since rev (OT pipeline)",
        "(tenant_id, ts) on usage_events — billing aggregation",
        "(ws_id, ts) on abuse_signals — incident review",
        "(host_id, status) on runners — host-level scheduling",
    ],
    hld_desc=(
        "Three planes. Control plane: HTTPS API + Edit/PTY WebSocket gateway, workspace metadata "
        "in a relational store, file tree backed by per-workspace persistent volumes (block "
        "storage or distributed FS) and small-file blobs in object storage, collab edits routed "
        "to a Document-Server-class actor per workspace using OT (delegated to the Google Docs "
        "engine). Data plane: a fleet of bare-metal hosts each running many Firecracker microVMs "
        "(or gVisor sandboxes); each workspace runner is one VM with the workspace volume "
        "mounted, a PTY bound to a WebSocket, cgroup CPU/RAM/IO caps, a network namespace with "
        "egress firewall, seccomp + eBPF policy, and a side metering daemon emitting "
        "CPU-seconds + egress bytes. Lifecycle plane: scheduler places runners on hosts by free "
        "capacity and locality to the volume, an idle-watcher snapshots+evicts after ~60 s "
        "inactivity, snapshot/restore uses Firecracker memory snapshots + copy-on-write disk "
        "deltas. Abuse plane: per-runner eBPF probes feed an anomaly classifier (syscall mix, "
        "egress patterns, CPU profile) that throttles or kills runners and raises tickets."
    ),
    hld_components=[
        {"name": "Browser IDE", "role": "Monaco/CodeMirror editor, file tree, terminal, preview pane"},
        {"name": "Edge Gateway", "role": "TLS, auth, sticky route by ws_id; terminates Edit + PTY WSS"},
        {"name": "Workspace API", "role": "CRUD on workspaces/files/ACLs; orchestration entrypoint"},
        {"name": "File Service", "role": "File tree CRUD; block-store volume + object-store blob refs"},
        {"name": "Document Server", "role": "Per-workspace OT actor for collab edits (Docs-class)"},
        {"name": "Run Orchestrator", "role": "Schedule runner placement, snapshot/restore, eviction"},
        {"name": "Runner Host", "role": "Bare-metal host running many Firecracker microVMs / gVisor sandboxes"},
        {"name": "Runner VM", "role": "User code + PTY + metering agent + egress NAT"},
        {"name": "PTY Broker", "role": "Multiplex PTY streams to/from WebSocket clients with backpressure"},
        {"name": "Snapshot Store", "role": "Memory snapshots + COW disk deltas in object storage"},
        {"name": "Egress Firewall", "role": "Per-workspace network namespace + DNS allowlist + bw cap"},
        {"name": "Metering Pipeline", "role": "Stream CPU-seconds + egress bytes → billing"},
        {"name": "Abuse Detector", "role": "eBPF + classifier; mining/scan/fork-bomb signals → throttle/kill"},
        {"name": "Permission Service", "role": "ACLs, share links, role-based op authorisation"},
    ],
    detailed_design={
        "editor_frontend": (
            "Monaco (VS Code's editor) for desktop, CodeMirror 6 for mobile/embeds — both expose "
            "the same Document model so the OT bindings are shared. Editor is hydrated from a "
            "compact file-tree manifest plus lazy fetch of opened blobs (range-fetch large files). "
            "Save is autosave-on-pause (debounced ~500 ms) which produces ops on the collab "
            "channel; explicit save is just a no-op flush. Local LSP-lite diagnostics run client-"
            "side; richer language servers run inside the runner and are tunnelled over the same "
            "WSS. Editor never touches the runner directly — all run/PTY traffic goes through the "
            "edge gateway with sticky routing."
        ),
        "workspace_storage": (
            "Each workspace owns a logical persistent volume (~1 GB cap default). The volume "
            "holds the file tree as a real filesystem (ext4) so user shell commands work. Volumes "
            "live on networked block storage (e.g., EBS-class) attached to the runner host on "
            "boot; small workspaces can use a copy-on-write overlay over a base template image "
            "instead of a dedicated volume to slash provisioning time. File metadata (path, size, "
            "mtime, owner) is also indexed in a relational store so the UI can render a file tree "
            "without booting a runner. Large blobs and snapshots live in object storage. Autosave "
            "writes go to the volume AND emit ops to the collab log so opening the file from "
            "another browser sees the same state without booting a runner."
        ),
        "sandboxed_execution": (
            "Three layered isolation tiers. Tier 1 (kernel): every runner is its own Firecracker "
            "microVM with a stripped guest kernel — full kernel isolation from the host and from "
            "every other tenant. Tier 2 (syscall): inside the guest, a seccomp-bpf profile blocks "
            "dangerous syscalls (kexec, ptrace cross-process, mount of arbitrary fs) and an eBPF "
            "LSM policy enforces per-process limits. Tier 3 (resources): cgroup v2 caps CPU "
            "(0.5 vCPU burstable), memory (512 MB), pids, IO bandwidth, and disk fill. gVisor is "
            "the alternative when microVM cold-start is too expensive — gVisor's user-space "
            "kernel intercepts syscalls and blocks the most dangerous ones, with ~10× faster "
            "cold-start at the cost of weaker isolation. Production picks Firecracker for default "
            "and gVisor for low-tier free runners or short bursts."
        ),
        "language_runtimes": (
            "Each language template is a base rootfs image: Python 3.x, Node LTS, Go, Rust, JDK, "
            "GCC, plus common libs. Templates are layered with overlayfs so workspaces share the "
            "base read-only layer; per-workspace writes go to a thin upper layer. Booting a "
            "runner takes the template image + workspace volume + last-known snapshot (if any) "
            "and resumes. Package install (npm, pip, cargo) runs as a normal command inside the "
            "runner — no special pathway — but the runner's egress namespace allowlists the "
            "registry domains so installs are observable and rate-limitable. Lockfile-based "
            "installs are cached at the host level (npm cache, pip wheels) keyed by lockfile "
            "hash for second-time speedup."
        ),
        "terminal_pty_streaming": (
            "Each runner exposes a PTY (Unix /dev/ptmx) bound to a WebSocket inside the guest, "
            "tunnelled out through the host's PTY broker. Frames are binary {kind:'data|resize|"
            "signal', payload} with a small length prefix; chunk size ~16 KB to balance latency "
            "and overhead. Backpressure: the broker pauses reads from the PTY when the client's "
            "send buffer exceeds 256 KB, so a `cat huge.bin` doesn't OOM the gateway. Terminal "
            "input flows the other way — keystrokes are sent immediately (no batching) for echo "
            "feel. Resize messages reflow the PTY (TIOCSWINSZ). Disconnect tolerates short "
            "drops via session resume keyed by (ws_id, terminal_id, last_seq) — the broker "
            "buffers 1-2 s of recent output for replay."
        ),
        "collaborative_editing": (
            "The editor talks to a per-workspace Document Server (the same actor pattern Google "
            "Docs uses). Each file is a sub-document with its own rev counter; ops are INSERT, "
            "DELETE, FORMAT, with base_rev, client_id, op_seq. Server linearises with "
            "Operational Transform — see the Google Docs design for the transform semantics, "
            "convergence properties, offline reconciliation, and per-user undo. Cursors and "
            "selections flow on a separate ephemeral pub/sub channel keyed by (ws_id, file_path). "
            "We deliberately reuse the Docs engine rather than re-derive — code editing is the "
            "same OT problem on plain text + structural awareness from the language server."
        ),
        "package_install": (
            "Package install is a wrapped command (`/usr/local/bin/install-helper npm install …`) "
            "that runs npm/pip/cargo with deterministic flags, captures the resolved lockfile, "
            "and writes a per-host content-addressed cache so the next install of the same "
            "lockfile is near-instant. Egress for installs goes through the per-workspace "
            "namespace's NAT, observed by the egress firewall — registries are allowlisted, "
            "post-install scripts are blocked from contacting non-registry hosts. Quota: install "
            "CPU and bandwidth count against the workspace's metered budget, so a runaway "
            "`npm install` doesn't bypass billing."
        ),
        "persistent_vs_ephemeral": (
            "Persistent: files on the workspace volume, environment files (.env, lockfiles), "
            "ACL/metadata. Ephemeral: process state, /tmp, listening sockets, in-memory app "
            "state — these are wiped on eviction unless we snapshot. Snapshot semantics live "
            "between the two: the user can opt into 'pause-and-resume' which captures memory + "
            "tmpfs as well, so a long-running dev server resumes mid-flight. Stateless workloads "
            "(e.g., scripts, compile-then-run) skip snapshots entirely — eviction is just "
            "process kill + volume detach."
        ),
        "container_lifecycle": (
            "States: COLD (no runner), WARM (snapshot in object storage), LIVE (runner booted, "
            "PTY attached), IDLE (live but no recent activity), STOPPING (snapshotting), "
            "EVICTED (snapshot complete, runner gone). Idle-watcher transitions LIVE→IDLE after "
            "~30 s without PTY/edit traffic, IDLE→STOPPING after another ~30 s, takes a "
            "Firecracker memory snapshot + COW disk delta, writes both to object storage, and "
            "frees the host slot. Restore reverses: copy snapshot to host SSD, mmap memory, "
            "resume guest from saved state — sub-500 ms p95 with warm hosts. Hard timeout: "
            "evict any LIVE runner after 6 h of continuous use to keep host fragmentation in "
            "check (paid plans get 24 h)."
        ),
        "networking_and_egress": (
            "Each runner gets its own network namespace + veth pair to a per-host bridge with "
            "an egress NAT. Egress firewall enforces: outbound-only by default (no inbound "
            "except the PTY/edit tunnel and the public preview tunnel), DNS-allowlist mode for "
            "free tier (npm, pypi, github, etc.), full-egress mode for paid plans, bandwidth "
            "cap (50 Mbps default) shaped via tc, byte counter exported to billing. Inbound "
            "preview: the gateway holds a TLS-terminating tunnel from the runner that maps "
            "https://<ws-id>.preview.example to a configurable port inside — no inbound port "
            "is opened on the runner network, the runner pushes a tunnel client outbound. "
            "DNS spoofing/exfil over DNS is mitigated by the per-runner resolver only "
            "answering allowlisted names plus rate limits."
        ),
        "abuse_detection": (
            "Per-runner eBPF probes export: syscall histograms, CPU usage profile (user vs "
            "kernel, %nice), egress connection counts and unique destinations, top-talker "
            "dst:port pairs, /proc/loadavg and unusual fork rates, file write rate. A "
            "classifier scores three families. Crypto mining: sustained 95%+ CPU + low "
            "syscall variance + egress to known mining pools (signature list) → throttle to "
            "0.05 vCPU and surface to user; second strike → kill + 24 h ban. Network "
            "scanning: > N unique destination IPs / minute or fan-out to common scan ports "
            "(22/3389/445) → block egress. Fork bombs: fork rate > threshold + pid-namespace "
            "near limit → cgroup pids.max enforces hard cap, runner killed. Disk-fill: write "
            "rate > X with low read-back → cgroup io.max throttle. Every signal is logged to "
            "abuse_signals with evidence for review."
        ),
        "billing_metering": (
            "CPU-seconds: a metering daemon inside the guest reads cgroup cpu.stat at 1 Hz and "
            "writes deltas (user_us, system_us) to the metering pipeline; aggregated by tenant "
            "into hourly buckets. Egress bytes: read from the per-namespace bridge counters at "
            "1 Hz. Storage GB-hours: sampled hourly from the volume's used_bytes. Idle runners "
            "do NOT consume CPU-seconds — that's the whole reason we evict; storage is still "
            "billed. The metering pipeline is at-least-once → idempotent dedup at the billing "
            "aggregator using (runner_id, sequence). End-of-month rollup produces an invoice "
            "with line items per workspace. Free tier has hard caps (e.g., 50 CPU-h/mo) "
            "enforced at the orchestrator: when a tenant's month-to-date crosses the limit, "
            "new run requests return 402 with a friendly upgrade flow."
        ),
        "slo_contract": (
            "Cold start (no warm snapshot) p95 < 2 s; warm restore p95 < 500 ms; PTY echo p95 "
            "< 120 ms intra-region; autosave RPO < 5 s; snapshot durability ≥ 11 nines (object "
            "storage); abuse-action latency from signal to throttle < 5 s; metering accuracy "
            "± 2% on CPU-seconds, ± 0.1% on egress bytes; collaborative edit convergence "
            "(delegated to the Docs engine) at 100% on every committed rev."
        ),
    },
    trade_offs=[
        {"option": "Firecracker microVM vs gVisor sandbox vs plain Docker",
         "for_microvm": "Strongest isolation (separate guest kernel), purpose-built for multi-tenant code execution (AWS Lambda, Replit), fast snapshot/restore",
         "for_gvisor": "User-space kernel, ~10× faster cold-start than microVM, fewer host kernel CVEs in scope, simpler ops",
         "recommendation": "Firecracker as default for paid runners; gVisor for free-tier short bursts. Plain Docker is not multi-tenant safe — kernel is shared and a kernel CVE is a tenant escape."},
        {"option": "OT vs CRDT for collaborative editing",
         "for_ot": "Tiny ops, central linearisation, well-understood for Docs-class systems",
         "for_crdt": "Peer-to-peer convergence, simpler offline story, mature OSS (Yjs)",
         "recommendation": "Reuse the Google Docs OT engine — code editing is the same problem on plain text. Picking CRDT here would split the implementation for no win."},
        {"option": "Snapshot+restore vs always-on runners",
         "for_snapshot": "Massive cost savings (only billed when active), free-tier viable",
         "for_always_on": "Sub-100 ms reattach, no warm-up jank",
         "recommendation": "Snapshot + restore by default; offer 'pinned' runners on paid plans for users who need always-on (long-running servers, ngrok-style demos)."},
        {"option": "Block-storage volumes vs overlay over base image",
         "for_volume": "Real filesystem, native shell semantics, easy snapshot",
         "for_overlay": "Near-zero provisioning time, perfect for ephemeral workspaces",
         "recommendation": "Hybrid — overlay for fresh templated workspaces; promote to a dedicated volume when usage > threshold or user enables persistence."},
        {"option": "Egress allowlist vs full-egress",
         "for_allowlist": "Strong abuse mitigation, predictable billing, blocks data exfil",
         "for_full_egress": "Better DX — users can curl anywhere",
         "recommendation": "Allowlist on free tier (npm/pypi/github + a curated list); full egress on paid with bandwidth caps + abuse classifier."},
        {"option": "Run metering in the guest vs at the orchestrator",
         "for_guest": "Accurate per-process attribution, sees real cgroup numbers",
         "for_orch": "Simpler — less guest agent surface",
         "recommendation": "Guest metering for CPU-seconds (cgroup truth); orchestrator/host metering for egress bytes (NAT counters). Cross-check against host-side cgroup stats for billing audit."},
    ],
    tips=[
        "Lead with the isolation story: 'every workspace is its own Firecracker microVM'. That single sentence tells the interviewer you know the problem.",
        "Don't re-derive collab editing — say 'reuse the Google Docs OT design, code editing is the same problem on plain text' and move on.",
        "Snapshot + restore is the cost lever. Quote 'cold start < 2 s, warm restore < 500 ms' and explain the eviction policy.",
        "Per-workspace network namespace + egress firewall is the abuse story. Mention DNS allowlist for free tier.",
        "Meter CPU-seconds in the guest (cgroup cpu.stat) and egress at the host bridge — that split is the senior signal.",
        "PTY backpressure (pause reads when client buffer > N) prevents `cat huge.bin` from OOMing the gateway. Name it.",
        "Crypto-mining detection is a heuristic stack (CPU profile + syscall mix + egress signatures), not a single rule. Walk the signal chain.",
        "Restate that plain Docker is NOT multi-tenant safe — shared kernel = one CVE away from tenant escape. Always pick microVM or gVisor.",
    ],
    thought_process=[
        "1. Clarify scope: editor + persistent files + sandboxed runner + terminal + collab + billing.",
        "2. Identify the hard core: multi-tenant code execution. Editor and file tree are mostly conventional.",
        "3. Estimate: 5M MAU, ~200k concurrent runners, ~10B CPU-seconds/day, ~200 TB egress/day.",
        "4. Pick isolation: Firecracker microVM by default, gVisor as low-tier alt, NEVER plain Docker for multi-tenant.",
        "5. Workspace storage: per-workspace volume + small-blob object storage; metadata in SQL for tree rendering.",
        "6. Lifecycle: snapshot + restore for cost; cold-start < 2 s; idle-evict at ~60 s.",
        "7. Terminal: PTY in guest, WSS to gateway, binary frames with backpressure.",
        "8. Collab: reuse Google Docs OT engine, point at that design — don't re-derive.",
        "9. Networking: per-workspace netns + egress firewall + DNS allowlist + bandwidth shaping.",
        "10. Abuse: eBPF probes + classifier for crypto-mining, port scans, fork bombs, disk-fill.",
        "11. Billing: meter CPU-seconds inside the guest (cgroup), egress at the host bridge; idempotent pipeline.",
        "12. SLOs: cold-start < 2 s, PTY echo < 120 ms, autosave RPO < 5 s, abuse-throttle < 5 s.",
    ],
    tags=["sandbox", "multi-tenant", "microvm", "firecracker", "collab", "ide", "metering"],
    arch_nodes=[
        {"id": "client", "label": "Browser IDE", "type": "client"},
        {"id": "edge", "label": "Edge / WS Gateway", "type": "lb"},
        {"id": "api", "label": "Workspace API", "type": "server"},
        {"id": "files", "label": "File Service", "type": "service"},
        {"id": "doc", "label": "Document Server (OT)", "type": "server"},
        {"id": "orch", "label": "Run Orchestrator", "type": "server"},
        {"id": "host", "label": "Runner Host", "type": "server"},
        {"id": "vm", "label": "Runner microVM", "type": "service"},
        {"id": "pty", "label": "PTY Broker", "type": "service"},
        {"id": "vol", "label": "Workspace Volume", "type": "database"},
        {"id": "snap", "label": "Snapshot Store", "type": "database"},
        {"id": "fw", "label": "Egress Firewall", "type": "service"},
        {"id": "meter", "label": "Metering Pipeline", "type": "queue"},
        {"id": "abuse", "label": "Abuse Detector", "type": "service"},
        {"id": "perms", "label": "Permission Svc", "type": "service"},
    ],
    arch_edges=[
        {"source": "client", "target": "edge", "label": "WSS edit + PTY"},
        {"source": "edge", "target": "api", "label": "REST"},
        {"source": "edge", "target": "doc", "label": "sticky by ws_id"},
        {"source": "edge", "target": "pty", "label": "PTY frames"},
        {"source": "api", "target": "files"},
        {"source": "api", "target": "orch", "label": "run/stop/snapshot"},
        {"source": "orch", "target": "host", "label": "schedule runner"},
        {"source": "host", "target": "vm", "label": "Firecracker boot"},
        {"source": "vm", "target": "vol", "label": "mount"},
        {"source": "vm", "target": "fw", "label": "egress via netns"},
        {"source": "vm", "target": "meter", "label": "cpu-seconds + egress"},
        {"source": "vm", "target": "abuse", "label": "eBPF probes"},
        {"source": "orch", "target": "snap", "label": "save / restore"},
        {"source": "pty", "target": "vm", "label": "PTY socket"},
        {"source": "doc", "target": "files", "label": "autosave"},
        {"source": "edge", "target": "perms", "label": "ACL check"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant U as Browser IDE\n"
        "  participant G as Gateway\n"
        "  participant O as Orchestrator\n"
        "  participant H as Runner Host\n"
        "  participant V as microVM\n"
        "  participant M as Metering\n"
        "  U->>G: POST /run (ws_id)\n"
        "  G->>O: schedule(ws_id)\n"
        "  O->>H: pick host w/ free slot\n"
        "  H->>V: restore snapshot (mem + disk delta)\n"
        "  V-->>H: ready (PTY socket)\n"
        "  H-->>G: runner attached\n"
        "  G-->>U: WSS /pty open\n"
        "  U->>V: keystrokes\n"
        "  V-->>U: PTY chunks (16 KB)\n"
        "  V->>M: cgroup cpu.stat delta @ 1 Hz\n"
        "  Note over O,V: idle 60 s\n"
        "  O->>V: graceful stop\n"
        "  V->>H: snapshot mem + disk delta\n"
        "  H->>O: snapshot stored\n"
        "  O->>H: free slot"
    ),
    er_diagram=(
        "erDiagram\n"
        "  USER ||--o{ WORKSPACE : owns\n"
        "  WORKSPACE ||--|| WORKSPACE_VOLUME : has\n"
        "  WORKSPACE ||--o{ FILE : contains\n"
        "  WORKSPACE ||--o{ RUNNER : runs\n"
        "  RUNNER ||--o{ RUNNER_SNAPSHOT : saves\n"
        "  WORKSPACE ||--o{ COLLAB_OP : edits\n"
        "  WORKSPACE ||--o{ ACL : grants\n"
        "  TENANT ||--o{ USAGE_EVENT : meters\n"
        "  WORKSPACE ||--o{ ABUSE_SIGNAL : flags"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B[Hard core: sandboxed multi-tenant exec]\n"
        "  B --> C{Isolation tier}\n"
        "  C -->|paid| D[Firecracker microVM]\n"
        "  C -->|free| E[gVisor]\n"
        "  D --> F[cgroup + seccomp + netns]\n"
        "  E --> F\n"
        "  F --> G[PTY over WSS]\n"
        "  F --> H[Per-workspace volume + snapshot]\n"
        "  H --> I[Idle evict + restore]\n"
        "  F --> J[Egress firewall + DNS allowlist]\n"
        "  F --> K[eBPF abuse probes]\n"
        "  K --> L[Classifier: mining / scan / fork-bomb]\n"
        "  F --> M[Meter cpu-seconds + egress]\n"
        "  N[Editor] --> O[OT Document Server]\n"
        "  O --> P[Reuse Google Docs design]"
    ),
    tradeoff_title="Sandbox Isolation: Firecracker microVM vs gVisor vs plain Docker",
    tradeoff_options=[
        {"label": "Firecracker microVM",
         "description": "Each workspace runs in its own KVM-backed microVM with a stripped guest kernel.",
         "pros": ["Strongest isolation — separate guest kernel", "Purpose-built for serverless multi-tenant (AWS Lambda)",
                 "Fast memory snapshot + COW disk for restore", "Tight resource accounting via cgroups"],
         "cons": ["Cold-start ~125-500 ms vs ~50 ms for containers", "Requires bare-metal or nested-virt hosts",
                 "Operationally heavier than containers", "Per-VM memory overhead ~5-10 MB"]},
        {"label": "gVisor (user-space kernel)",
         "description": "Container running under a user-space kernel (Sentry) that intercepts syscalls.",
         "pros": ["~10× faster cold-start than microVM", "Strong syscall-level isolation without a separate kernel",
                 "Mature (powers Google Cloud Run, App Engine)", "Lower per-tenant memory overhead"],
         "cons": ["Some syscalls fall through to the host kernel — weaker than microVM",
                 "Performance penalty on syscall-heavy workloads (~10-30%)",
                 "Complex bug surface in Sentry itself", "Some kernel features unsupported"]},
        {"label": "Plain Docker / OCI containers",
         "description": "Standard container with cgroup limits and a seccomp profile.",
         "pros": ["Trivial cold-start", "Mature tooling", "Lowest overhead"],
         "cons": ["Shared host kernel — single CVE = tenant escape", "Seccomp + AppArmor are not enough for untrusted code",
                 "Industry consensus: do not run untrusted multi-tenant code in plain containers"]},
    ],
    tradeoff_rec=(
        "Firecracker microVM as the production default for paid runners (matches Replit/Lambda), with "
        "gVisor as the fallback for free-tier short bursts where the cold-start budget matters more "
        "than the marginal isolation gain. Plain Docker is non-viable — it's the answer that gets you "
        "fired the first time someone runs a kernel exploit."
    ),
    senior_topics=[
        _topic("microvm-snapshot-restore",
               "Firecracker Memory Snapshots and Sub-Second Restore",
               "How a stopped runner becomes a sub-500 ms 'resume' instead of a multi-second cold-start, what "
               "actually goes into the snapshot, and the COW disk pattern that keeps storage costs bounded.",
               [
                   ("What's in a memory snapshot",
                    "Firecracker captures: full guest RAM (mmap'd file), CPU register state, virtual device "
                    "state (vCPU, virtio queues), and the kernel command-line. Snapshot size ≈ in-use RAM "
                    "(zero pages dropped) — typically 50-300 MB for a Node/Python workspace."),
                   ("COW disk delta",
                    "Workspace disk is layered: read-only base image (Python, Node, etc.) + per-workspace "
                    "upper layer. Snapshot stores only the upper layer's blocks that changed since base — "
                    "a few MB for most short sessions. Restore mounts the base + upper, no copy needed."),
                   ("Restore path",
                    "On reattach, host fetches snapshot blob (often <300 MB), mmap's it as guest RAM, "
                    "restores vCPU + device state, resumes execution. p95 < 500 ms with warm hosts; "
                    "tail dominated by S3 fetch latency, mitigated by host-local snapshot cache."),
                   ("Cold-cache behaviour",
                    "First page touch faults from the snapshot file — initial seconds of execution are "
                    "slightly slower as pages are demand-paged in. Userfaultfd lets us start the guest "
                    "before the entire snapshot is on disk; the rest streams in async."),
                   ("Snapshot churn and GC",
                    "Each eviction writes a new snapshot; we keep only the latest per workspace. Older "
                    "snapshots are GC'd nightly. Free-tier may use a shorter snapshot retention (1 h) "
                    "to control object-storage cost."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant O as Orchestrator\n"
                   "  participant H as Host\n"
                   "  participant S as Snapshot Store\n"
                   "  participant V as microVM\n"
                   "  O->>H: restore(ws_id)\n"
                   "  H->>S: fetch snapshot blob\n"
                   "  S-->>H: mem + disk delta\n"
                   "  H->>V: mmap RAM, restore vCPU+devs\n"
                   "  V-->>H: resume\n"
                   "  H-->>O: ready (~400ms)"
               )),
        _topic("egress-firewall-dns-allowlist",
               "Per-Workspace Network Namespace, Egress Firewall, and DNS Allowlist",
               "How outbound networking is fully controlled per-workspace without crippling DX, why DNS "
               "exfiltration is a real threat, and the pattern that lets free-tier users still `npm install`.",
               [
                   ("Network namespace per runner",
                    "Each runner has its own netns + veth pair to a per-host bridge. The bridge does NAT "
                    "to the internet via the host's public IP. The guest sees only its loopback + veth — "
                    "no access to the host network or to peer runners."),
                   ("Egress firewall and bandwidth shaping",
                    "iptables/nftables on the bridge enforces: outbound-only by default; DNS-allowlist "
                    "mode for free tier (only registry domains resolve); full egress for paid plans. "
                    "Bandwidth is shaped via tc (HTB qdisc) at the bridge, with byte counters exported "
                    "to the metering pipeline."),
                   ("DNS allowlist for free tier",
                    "Per-runner resolver (dnsmasq) only answers a curated list (npm, pypi, github, "
                    "common CDN domains). Anything else NXDOMAIN. This blocks both 'curl arbitrary "
                    "endpoint' and most data-exfil patterns."),
                   ("DNS exfiltration mitigation",
                    "Even with allowlist, attackers can encode data into DNS queries to allowlisted "
                    "domains. Mitigations: rate-limit DNS queries per runner (e.g., 100/min), disallow "
                    "long subdomain queries (>63 chars), and log all queries for offline analysis."),
                   ("Inbound preview tunnel",
                    "No inbound port is opened on the runner. To expose a dev server, the runner pushes "
                    "an outbound tunnel client (like ngrok) to the gateway, which maps "
                    "https://<ws-id>.preview.example to a chosen guest port. The gateway is the only "
                    "internet-facing surface; the runner stays behind NAT."),
               ],
               diagram=(
                   "graph LR\n"
                   "  V[Runner VM netns] -->|veth| BR[host bridge + NAT]\n"
                   "  BR --> FW[nftables egress]\n"
                   "  FW -->|allow| REG[npm/pypi/github]\n"
                   "  FW -->|allow paid| ANY[full egress]\n"
                   "  FW -->|deny free| BLOCK[(NXDOMAIN)]\n"
                   "  V -.->|outbound tunnel| TUN[Gateway preview]\n"
                   "  TUN --> NET[(Internet HTTPS)]"
               )),
        _topic("abuse-detection-mining-scanning",
               "Detecting Crypto Mining, Network Scanning, and Fork Bombs in a Multi-Tenant Sandbox",
               "What signals reliably distinguish abusive workloads from legitimate compute, and the tiered "
               "response (throttle → kill → ban) that keeps false positives from torching dev UX.",
               [
                   ("Why this matters",
                    "Free-tier sandboxes are abuse magnets — crypto mining is the canonical case, but "
                    "outbound port scanning and stress-test fork bombs also show up. Without detection, "
                    "free-tier economics break and the platform's IP reputation tanks."),
                   ("Crypto mining signals",
                    "Sustained > 95% CPU + low syscall variance + egress to known mining-pool domains "
                    "(stratum+tcp://...) + characteristic instruction mix (ASIC-friendly hashing). "
                    "Single-signal classifiers fail; need a weighted ensemble. False-positive risk: "
                    "legitimate Rust/C++ compile or simulation. Tier action accordingly."),
                   ("Network scanning signals",
                    "> N (e.g., 50) unique destination IPs / minute, especially fan-out to common "
                    "scan ports (22/3389/445/5432). Block egress immediately on threshold cross — "
                    "scanning is unambiguous abuse. Surface a clear error to the user."),
                   ("Fork bomb signals",
                    "Fork rate > threshold + pid-namespace usage approaching limit + low per-process "
                    "CPU. cgroup pids.max enforces a hard cap (256 default), so the fork bomb hits a "
                    "wall instead of consuming the host. Detector pattern-matches on fork rate to kill "
                    "the runner immediately rather than waiting for the cap."),
                   ("Tiered response",
                    "Tier 1 (low confidence): throttle to 0.05 vCPU + UI banner 'we noticed unusual "
                    "activity'. Tier 2 (medium): kill the runner, retain volume + snapshot. Tier 3 "
                    "(high or repeat): ban the tenant pending review. False-positive recovery is "
                    "click-through human appeal — never silently ban."),
                   ("eBPF as the probe",
                    "eBPF programs attached at syscall entry, sched events, and net_dev_xmit emit "
                    "aggregated counters to a per-host classifier daemon. No syscall overhead per "
                    "process, near-zero false-positive on the data path itself."),
               ],
               diagram=(
                   "graph LR\n"
                   "  EBPF[eBPF probes] --> COL[per-host collector]\n"
                   "  COL --> CLF[classifier]\n"
                   "  CLF -->|mining sig| T1[throttle vCPU]\n"
                   "  CLF -->|scan sig| T2[block egress]\n"
                   "  CLF -->|fork bomb| T3[kill runner]\n"
                   "  T1 --> UI[user banner]\n"
                   "  T3 --> BAN[tenant review queue]"
               )),
        _topic("cpu-second-metering-billing",
               "CPU-Second Metering, Egress Accounting, and the Idempotent Billing Pipeline",
               "How CPU usage is measured accurately enough to bill in cents, why egress is accounted at "
               "the host bridge instead of in-guest, and how the pipeline survives crashes without "
               "double-billing.",
               [
                   ("Where to measure CPU",
                    "Inside the guest, the metering daemon reads cgroup cpu.stat (user_us, system_us) "
                    "at 1 Hz and emits deltas. cgroup numbers are the kernel's own accounting — billing "
                    "auditable. Doing it at the orchestrator misses bursts and is always behind."),
                   ("Where to measure egress",
                    "Per-workspace network namespace bridge counters (RX/TX bytes) at the host. "
                    "Doing this in-guest lets a malicious workload undercount itself by tampering "
                    "with the agent. Host-side bridge counters are the kernel's truth and live "
                    "outside the tenant's reach."),
                   ("At-least-once + idempotent",
                    "Metering events flow through Kafka with (runner_id, sequence) keys. The billing "
                    "aggregator dedupes on this pair and stores aggregated buckets per (tenant, hour, "
                    "kind). Crash recovery: replay from last-committed offset; duplicates are a "
                    "no-op in the aggregator. Never use at-most-once for billing."),
                   ("Sub-second accounting precision",
                    "1 Hz sampling is sufficient for ± 2% accuracy at minute granularity (the billing "
                    "unit). For sub-second jobs (CI runs, function-style invokes) we measure the "
                    "wall-clock from runner-attach to detach as a coarse upper bound and prefer the "
                    "cgroup number when available."),
                   ("Quotas and back-pressure",
                    "When tenant month-to-date crosses a hard limit, new run requests are rejected "
                    "at the orchestrator with 402 Payment Required + upgrade CTA; live runners are "
                    "given a grace window then evicted. This prevents 'free' code from running "
                    "indefinitely after the tenant is delinquent."),
                   ("Audit and disputes",
                    "Per-runner per-second usage events are retained for 90 days raw + indefinitely "
                    "as hourly rollups. Disputes drill into raw events; reconciliation between "
                    "guest cgroup numbers and host CPU-time stat is run nightly with alerts on "
                    "drift > 5%."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant V as Runner VM\n"
                   "  participant H as Host bridge\n"
                   "  participant K as Kafka\n"
                   "  participant A as Billing Aggregator\n"
                   "  participant DB as Billing Store\n"
                   "  loop 1 Hz\n"
                   "    V->>K: cpu_us delta (runner_id, seq)\n"
                   "    H->>K: egress bytes delta (runner_id, seq)\n"
                   "  end\n"
                   "  K->>A: stream events\n"
                   "  A->>A: dedupe by (runner_id, seq)\n"
                   "  A->>DB: hourly rollup per tenant\n"
                   "  DB-->>A: ack"
               )),
    ],
)
