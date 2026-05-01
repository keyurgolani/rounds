"""SD-Zoom/Meet — Design Zoom / Google Meet (real-time video calls,
screensharing, recording). Mirrors the schema/shape of SD_01 in
sd_questions.py."""
from __future__ import annotations

from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design Zoom / Google Meet",
    "Hard",
    "Design a planet-scale real-time video conferencing platform supporting hundreds of participants per "
    "meeting with sub-200ms glass-to-glass latency, screensharing, cloud recording, and end-to-end "
    "encryption. The system must traverse arbitrary NATs, adapt to lossy and bandwidth-limited networks, "
    "scale from 1:1 calls to 1000-person webinars, and produce server-side recordings without compromising "
    "E2EE for non-recorded calls. Cover signaling (SDP/ICE), media topology (P2P mesh vs SFU vs MCU), "
    "STUN/TURN traversal, simulcast/SVC for adaptive bitrate, jitter buffer, FEC/NACK packet loss recovery, "
    "bandwidth estimation (GCC/transport-cc), breakout rooms, and per-meeting key distribution.",
    hints=[
        "Real-time (<200ms) means UDP/RTP, not TCP/HTTP. WebRTC is the standard stack.",
        "Topology choice (P2P / SFU / MCU) is the central design decision — argue from participant count and CPU.",
        "Signaling (SDP+ICE) is decoupled from media — separate control plane from data plane.",
        "TURN traffic is expensive (relays full media) — design to minimize fallback rate.",
        "Simulcast/SVC lets the SFU forward different layers per receiver without re-encoding.",
        "Recording is server-side mixing on a 'recorder participant' — preserves E2EE for non-recorded calls.",
        "Jitter buffer trades latency for smoothness — adaptive based on network variance.",
        "End-to-end encryption uses per-meeting symmetric key; SFU forwards opaque encrypted RTP.",
    ],
    constraints=[
        "Glass-to-glass latency p95 < 200ms within region; < 400ms cross-region",
        "Up to 1000 participants per meeting (webinar mode); 100 active video tiles",
        "Audio drop tolerance < 0.5%; video freeze < 1% of session time",
        "Bandwidth: 100 kbps–4 Mbps per participant adaptive; degrade to audio-only on bad networks",
        "NAT traversal must succeed > 99% (P2P or TURN-relayed)",
        "E2EE optional but available — server cannot decrypt media when enabled",
        "Recording durability 11 nines; retrievable for compliance retention windows",
        "Global: 200+ edge media POPs; meeting region pinned to majority participants",
    ],
    req_func=[
        "Create / join / leave meetings with auth + per-meeting room codes",
        "Bidirectional audio + video for all participants",
        "Screensharing as a distinct media track (separate stream from camera)",
        "Active speaker detection + dominant-speaker switching",
        "Server-side cloud recording (audio + video + screenshare + transcript)",
        "Breakout rooms — sub-meetings spawned from a parent meeting",
        "Chat (in-meeting messaging), reactions, raise-hand",
        "Live captions / transcription via streaming ASR",
        "End-to-end encryption mode (no server access to media)",
        "Webinar mode — 1000+ viewers, only hosts/panelists publish",
    ],
    req_nonfunc=[
        "Glass-to-glass p95 < 200ms; jitter buffer adaptive 30–200ms",
        "Audio is sacred — drop video before audio under congestion",
        "99.99% availability for signaling; 99.95% for media plane",
        "Bandwidth-adaptive — simulcast / SVC layers, ABR on receiver",
        "Packet loss tolerance up to 10% via FEC + NACK + RED",
        "NAT traversal success > 99% (UDP hole-punch + TURN fallback)",
        "Recording isolation — recorded meetings excluded from E2EE mode",
        "GDPR / SOC2 / HIPAA configurations per tenant",
    ],
    estimation={
        "concurrent_meetings_peak": "~1M concurrent meetings globally",
        "concurrent_participants_peak": "~10M concurrent active streams",
        "avg_meeting_size": "~5 participants; long tail to 1000",
        "bitrate_per_participant": "~1.5 Mbps (camera) + 1 Mbps (screenshare); adaptive",
        "media_egress": "~15 Tbps aggregate at peak (mostly intra-region, SFU-relayed)",
        "signaling_qps": "~100K join/leave/SDP-renegotiation/sec",
        "turn_relay_share": "~10–15% of calls fully or partially relayed",
        "recording_storage": "~600 MB/hour per meeting recorded; ~5 PB/day at 5% record rate",
        "transcribe_cpu": "1× realtime ASR per recorded participant; GPU fleet",
    },
    endpoints=[
        {"method": "POST", "path": "/meetings",
         "description": "Create a meeting; returns meeting_id, join_token, region",
         "body": "{host_user_id, scheduled_start, e2ee_enabled, max_participants}"},
        {"method": "POST", "path": "/meetings/{meeting_id}/join",
         "description": "Request to join; returns SFU endpoint, ICE servers, meeting_key (E2EE)",
         "body": "{user_id, join_token, device_caps}"},
        {"method": "POST", "path": "/signaling/{meeting_id}/sdp",
         "description": "WebSocket: SDP offer/answer + ICE candidate exchange with SFU",
         "body": "{type:'offer'|'answer'|'candidate', sdp|candidate}"},
        {"method": "GET", "path": "/turn/credentials",
         "description": "Short-lived TURN credentials (HMAC-signed username/password)"},
        {"method": "POST", "path": "/meetings/{meeting_id}/recording/start",
         "description": "Host triggers cloud recording (joins recorder bot to meeting)"},
        {"method": "POST", "path": "/meetings/{meeting_id}/recording/stop",
         "description": "Stop recording; finalize and enqueue post-processing"},
        {"method": "POST", "path": "/meetings/{meeting_id}/breakout",
         "description": "Create breakout sub-meetings",
         "body": "{rooms:[{name, participants:[user_id]}]}"},
        {"method": "GET", "path": "/recordings/{recording_id}",
         "description": "Fetch recording metadata + signed playback URL"},
        {"method": "POST", "path": "/meetings/{meeting_id}/screenshare",
         "description": "Start screenshare (publishes additional video track)"},
    ],
    tables=[
        {"name": "meetings",
         "columns": ["meeting_id VARCHAR(16) PK", "host_user_id BIGINT", "title VARCHAR(255)",
                     "scheduled_start BIGINT", "started_at BIGINT", "ended_at BIGINT",
                     "region VARCHAR(16)", "sfu_cluster_id VARCHAR(32)", "e2ee_enabled BOOL",
                     "max_participants INT", "status VARCHAR(16)"]},
        {"name": "participants",
         "columns": ["meeting_id VARCHAR(16)", "user_id BIGINT", "role VARCHAR(16)",
                     "joined_at BIGINT", "left_at BIGINT", "device VARCHAR(32)",
                     "ice_outcome VARCHAR(16)",
                     "PRIMARY KEY (meeting_id, user_id)"]},
        {"name": "meeting_keys",
         "columns": ["meeting_id VARCHAR(16) PK", "wrapped_key BLOB", "key_epoch INT",
                     "rotated_at BIGINT"]},
        {"name": "recordings",
         "columns": ["recording_id VARCHAR(16) PK", "meeting_id VARCHAR(16)", "started_at BIGINT",
                     "ended_at BIGINT", "duration_sec INT", "s3_key_audio VARCHAR(255)",
                     "s3_key_video VARCHAR(255)", "transcript_s3_key VARCHAR(255)",
                     "status VARCHAR(16)"]},
        {"name": "chat_messages",
         "columns": ["msg_id BIGINT PK", "meeting_id VARCHAR(16)", "user_id BIGINT",
                     "ts BIGINT", "body TEXT", "kind VARCHAR(16)"]},
        {"name": "breakout_rooms",
         "columns": ["breakout_id VARCHAR(16) PK", "parent_meeting_id VARCHAR(16)",
                     "name VARCHAR(64)", "created_at BIGINT", "closed_at BIGINT"]},
        {"name": "ice_stats",
         "columns": ["session_id BIGINT PK", "meeting_id VARCHAR(16)", "user_id BIGINT",
                     "candidate_type VARCHAR(16)", "rtt_ms INT", "packet_loss FLOAT",
                     "ts BIGINT"]},
    ],
    indexes=[
        "(host_user_id, scheduled_start DESC) on meetings — host calendar",
        "(meeting_id) on participants — roster lookups",
        "(meeting_id, ts ASC) on chat_messages — replay order",
        "(parent_meeting_id) on breakout_rooms — children of a parent meeting",
        "(meeting_id) on recordings — recording history per meeting",
        "(ts) on ice_stats — time-series partitioning for QoE analytics",
    ],
    hld_desc=(
        "Three decoupled planes. Signaling plane: WebSocket-based control servers handle SDP "
        "offer/answer, ICE candidate exchange, room state, and roster updates. Media plane: a fleet "
        "of regional SFUs (Selective Forwarding Units) terminates RTP from each participant and "
        "selectively forwards simulcast/SVC layers to other participants — no transcoding for the "
        "common path. NAT traversal plane: globally distributed STUN servers issue server-reflexive "
        "candidates; TURN servers relay UDP/TCP for the ~10% of clients behind symmetric NATs. "
        "Side services: a recorder service (a synthetic SFU participant that subscribes to all "
        "tracks, mixes server-side, and stores HLS-packaged output to object storage). Streaming "
        "ASR service for live captions. Per-meeting key distribution service for E2EE mode. "
        "Coordinator picks meeting region by participant geography and pins all SFU shards to one "
        "regional cluster."
    ),
    hld_components=[
        {"name": "Signaling Server", "role": "WebSocket SDP/ICE exchange, roster, room state"},
        {"name": "STUN Server", "role": "Issues server-reflexive candidates for NAT discovery"},
        {"name": "TURN Server", "role": "Relays media for clients behind symmetric NAT"},
        {"name": "SFU (Selective Forwarding Unit)", "role": "Receives RTP from N publishers; forwards selected layers to N-1 subscribers"},
        {"name": "MCU (optional)", "role": "Server-side mix/transcode for legacy SIP / dial-in clients"},
        {"name": "Recorder Service", "role": "Joins meeting as synthetic participant; mixes + writes HLS to S3"},
        {"name": "Transcription Service", "role": "Streaming ASR + speaker diarization for captions"},
        {"name": "Meeting Coordinator", "role": "Allocates SFU cluster by region; load-balances participants"},
        {"name": "Key Distribution Service", "role": "Issues per-meeting symmetric key for E2EE mode"},
        {"name": "Bandwidth Estimator (in SFU)", "role": "GCC / transport-cc; tells encoder target bitrate"},
        {"name": "Object Store", "role": "Recordings, transcripts, manifests"},
        {"name": "Edge Media POPs", "role": "Anycast TURN + SFU front-doors for low-latency entry"},
    ],
    detailed_design={
        "media_topology_choice": (
            "Three options. (1) P2P mesh: each participant sends its stream to every other; "
            "O(N^2) uplink — viable only for 2–4 participants. (2) MCU: server decodes all streams, "
            "mixes into one composite, re-encodes per receiver — heavy CPU, single output bitrate, "
            "loses participant flexibility. (3) SFU: server terminates RTP, selectively forwards "
            "simulcast/SVC layers without decoding — O(N) uplink per participant + linear server "
            "egress. SFU is the modern default. Use MCU only for SIP gateway / phone dial-in where "
            "the endpoint can't handle multiple streams."
        ),
        "signaling_protocol": (
            "WebSocket-based. On join, client establishes WS to signaling server; server returns SFU "
            "endpoint + ICE server list. Client creates RTCPeerConnection → generates SDP offer "
            "(media descriptions, codecs, simulcast layers) → sends to SFU via signaling → SFU "
            "answers. ICE candidates trickle as discovered (host, srflx, relay). Renegotiation "
            "(participant joins, screenshare starts) sends incremental SDP offers. Signaling never "
            "carries media — separate concern."
        ),
        "nat_traversal": (
            "ICE workflow: gather host candidates (local IPs), srflx candidates (via STUN — public "
            "IP/port observed by STUN server), and relay candidates (TURN-allocated public address). "
            "ICE pairs candidates from both sides, runs connectivity checks (STUN binding requests), "
            "promotes the highest-priority working pair. ~85% complete on host/srflx, ~15% require "
            "TURN. TURN runs UDP-preferred, TCP fallback for restrictive corporate firewalls, "
            "TURN-over-TLS-443 last resort. TURN credentials are short-lived HMAC tokens."
        ),
        "simulcast_svc": (
            "Each publisher sends 2–3 simulcast layers (e.g., 1080p / 720p / 180p) on different SSRCs "
            "with independent bitrates. SFU decides per-receiver which layer to forward based on "
            "receiver bandwidth, viewport size (active speaker tile vs thumbnail), and CPU. Switching "
            "between layers is essentially free — no re-encode. SVC (scalable video coding, e.g., "
            "VP9-SVC, AV1-SVC) ships temporal+spatial layers in one stream; SFU drops layers per "
            "subscriber. SVC saves uplink versus simulcast at the cost of codec complexity."
        ),
        "bandwidth_estimation": (
            "Two-sided. Sender uses GCC (Google Congestion Control) or transport-cc: receiver tags "
            "each RTP packet with arrival time, sends RTCP feedback; sender computes delay-gradient "
            "and packet-loss to estimate available bandwidth and adjusts encoder target bitrate "
            "(typically every 100–500ms). SFU also runs estimator per egress pipe to receiver and "
            "drops simulcast layers if downstream is congested — never blocks audio."
        ),
        "packet_loss_recovery": (
            "Three mechanisms layered. (1) NACK: receiver requests retransmission of lost packets — "
            "cheap, works for short bursts, adds RTT of latency. (2) FEC: sender adds redundant "
            "packets (RED for audio, ULPFEC/FlexFEC for video) — recovers small losses without "
            "retransmit, adds bandwidth overhead. (3) PLI / FIR: receiver requests a keyframe when "
            "decoder state is unrecoverable. Audio uses Opus in-band FEC + RED duplication; video "
            "uses NACK + FEC + temporal scalability (drop B-frames first under loss). Jitter buffer "
            "smooths arrival variance — adaptive 30–200ms target based on observed jitter."
        ),
        "screenshare_pipeline": (
            "Screenshare published as an additional video track on the same RTCPeerConnection (new "
            "m-line). Encoder optimized for screen content: VP9/AV1 with 'screen' tuning (low motion, "
            "high text fidelity), variable frame rate (down to 1 fps for static slides, 30 fps for "
            "video). Higher resolution (1080p–4K) but lower bitrate than camera. SFU forwards as a "
            "distinct stream so receivers can render it in a separate UI region. Audio sharing "
            "(system audio) is a separate audio track on the same connection."
        ),
        "active_speaker_detection": (
            "Each publisher's RTP audio carries the audio-level header extension (RFC 6464). SFU "
            "tracks per-participant rolling audio level; the highest-level participant for the "
            "trailing window (~500ms with hysteresis) is the dominant speaker. SFU broadcasts "
            "active-speaker change to all participants as a control message; UI promotes that "
            "tile. SFU may also up-rate that publisher's simulcast layer choice for receivers."
        ),
        "recording": (
            "A 'recorder participant' (headless bot) joins the meeting like any other client and "
            "subscribes to all tracks. It receives the per-meeting symmetric key (only if E2EE is "
            "off OR if host explicitly enables recording, in which case E2EE is downgraded for that "
            "meeting). Recorder mixes audio (sum-and-AGC) and composes video (active-speaker focus "
            "or grid layout) into HLS segments + master playlist; writes to object storage. "
            "Post-processing pipeline: trim leading/trailing silence, generate thumbnail grid, "
            "produce searchable transcript via streaming ASR with diarization, and store final "
            "package (audio+video+chat+transcript+attendance). E2EE meetings cannot be cloud-"
            "recorded — local-only recording on host's device."
        ),
        "breakout_rooms": (
            "Breakout = spawning N child meetings from a parent. Coordinator allocates SFU shards "
            "for each breakout (often the same SFU cluster for affinity). Participants are migrated "
            "by signaling: parent SFU connection torn down, new join token issued for breakout SFU, "
            "client renegotiates SDP. Host can broadcast a message to all breakouts (signaling fan-"
            "out) and pull participants back to parent on close."
        ),
        "e2ee_mode": (
            "Per-meeting symmetric key generated at meeting creation, distributed to participants "
            "via key distribution service over authenticated WebSocket. Each frame is encrypted by "
            "the publisher with this key (frame-level AES-GCM via Insertable Streams API in WebRTC) "
            "before SFU sees it; SFU forwards opaque ciphertext. Receivers decrypt locally. SFU "
            "never holds plaintext. Key rotation on participant leave (rolling epoch) prevents "
            "ex-participant decryption. Tradeoff: server-side recording, transcription, and "
            "background-blur features are unavailable in E2EE mode (server can't see frames)."
        ),
        "webinar_mode": (
            "1000+ viewers but only ~10 panelists publish. SFU acts as 1-to-many fanout for "
            "publishers; for viewers > capacity of a single SFU egress, deploy a tree of relay SFUs "
            "(each ingest from origin SFU, fan out further). For very large (>10K) audiences, fall "
            "back to LL-HLS streaming via CDN — 3–5s latency but unbounded scale. Q&A flows over a "
            "separate signaling channel; raise-hand promotes a viewer to panelist by reissuing a "
            "publishing token."
        ),
        "slo_contract": (
            "Glass-to-glass p95 < 200ms intra-region; < 400ms cross-region. Audio drop p99 < 0.5%. "
            "Video freeze < 1% session time. Join time p95 < 3s (signaling + ICE complete). "
            "TURN-relay rate < 15%. Recording finalization p95 < 5min after meeting end."
        ),
    },
    trade_offs=[
        {"option": "P2P mesh vs SFU vs MCU",
         "for_p2p": "Zero server media cost; lowest latency 1:1",
         "for_sfu": "O(N) uplink, no transcoding, scales to ~50–100 active",
         "for_mcu": "Single composited output; works for legacy/SIP endpoints",
         "recommendation": "SFU as default; P2P for 1:1; MCU as gateway for SIP/phone."},
        {"option": "Simulcast vs SVC",
         "for_simulcast": "Codec-agnostic (works on H.264); broad client support",
         "for_svc": "Lower uplink (one stream with layers); single encoder pass",
         "recommendation": "Simulcast (H.264/VP8) baseline; SVC (VP9/AV1) for clients that support it."},
        {"option": "WebRTC vs custom UDP protocol",
         "for_webrtc": "Standard, browser-native, mature traversal/codec stack",
         "for_custom": "Full control over congestion / transport optimisations",
         "recommendation": "WebRTC. Building custom UDP loses 5+ years of NAT/codec work."},
        {"option": "FEC vs NACK for packet loss",
         "for_fec": "No retransmit RTT; works on broadcast paths",
         "for_nack": "Bandwidth-efficient when loss is rare",
         "recommendation": "Both — FEC for audio (latency-critical), NACK + temporal scalability for video."},
        {"option": "Server-side recording vs client-side",
         "for_server": "Reliable, includes all participants, transcribable",
         "for_client": "Compatible with E2EE; off-server cost",
         "recommendation": "Server-side default; client-only when E2EE is enabled."},
        {"option": "E2EE always on vs opt-in",
         "for_always": "Strongest privacy guarantee",
         "for_optin": "Allows server-side recording, transcription, breakout migration",
         "recommendation": "Opt-in per meeting. Disable cloud features when on."},
    ],
    tips=[
        "Lead with topology choice (SFU) and justify from N×N uplink math — that's the senior signal.",
        "WebRTC stack: signaling (SDP/ICE) is separate from media (RTP/SRTP). Don't conflate.",
        "STUN discovers public IP; TURN relays media. ~10–15% of calls need TURN — design for it.",
        "Simulcast vs SVC is a real interview hook — name VP9-SVC / AV1-SVC + transport-cc.",
        "Audio is sacred: drop video layers or freeze before sacrificing audio. Cite Opus in-band FEC + RED.",
        "Active-speaker detection runs on RFC 6464 audio-level header extension — SFU never decodes.",
        "Recording = 'recorder bot as synthetic participant' — preserves architecture symmetry.",
        "E2EE uses Insertable Streams API + per-meeting key. Tradeoff: no server-side recording/captions.",
        "Don't forget jitter buffer — adaptive 30–200ms based on observed network variance.",
        "Webinar at 10K+ viewers fans out via tree of relay SFUs or falls back to LL-HLS.",
    ],
    thought_process=[
        "1. Clarify: max participants? E2EE? Recording? Latency target?",
        "2. Estimate: 1M concurrent meetings × 5 avg = 5–10M streams; ~15 Tbps egress.",
        "3. Topology: P2P doesn't scale → SFU. Justify with N×N uplink math.",
        "4. Signaling plane: WebSocket SDP/ICE; control plane separate from media.",
        "5. NAT traversal: STUN for srflx, TURN for 10–15% behind symmetric NAT.",
        "6. ABR: simulcast or SVC; SFU forwards selected layers per receiver.",
        "7. Bandwidth estimation: GCC/transport-cc; sender adapts encoder.",
        "8. Loss recovery: NACK + FEC + jitter buffer. Audio gets RED + Opus FEC.",
        "9. Screenshare: separate track, screen-tuned codec, lower fps.",
        "10. Recording: synthetic participant joins as recorder; mixes server-side.",
        "11. E2EE: per-meeting key + Insertable Streams; SFU forwards ciphertext.",
        "12. Webinar: tree of relay SFUs or LL-HLS for >10K viewers.",
    ],
    tags=["video", "webrtc", "real-time", "sfu", "streaming"],
    arch_nodes=[
        {"id": "client_a", "label": "Participant A", "type": "client"},
        {"id": "client_b", "label": "Participant B", "type": "client"},
        {"id": "client_n", "label": "Participant N", "type": "client"},
        {"id": "signaling", "label": "Signaling Server", "type": "server"},
        {"id": "stun", "label": "STUN Server", "type": "service"},
        {"id": "turn", "label": "TURN Relay", "type": "service"},
        {"id": "sfu", "label": "SFU (Regional)", "type": "server"},
        {"id": "coord", "label": "Meeting Coordinator", "type": "server"},
        {"id": "kds", "label": "Key Distribution", "type": "service"},
        {"id": "recorder", "label": "Recorder Bot", "type": "service"},
        {"id": "asr", "label": "Streaming ASR", "type": "service"},
        {"id": "obj_store", "label": "Object Store (Recordings)", "type": "database"},
        {"id": "meta_db", "label": "Meeting Metadata DB", "type": "database"},
        {"id": "edge", "label": "Edge POPs (Anycast)", "type": "lb"},
    ],
    arch_edges=[
        {"source": "client_a", "target": "signaling", "label": "SDP/ICE (WS)"},
        {"source": "client_b", "target": "signaling", "label": "SDP/ICE (WS)"},
        {"source": "client_n", "target": "signaling", "label": "SDP/ICE (WS)"},
        {"source": "signaling", "target": "coord", "label": "allocate SFU"},
        {"source": "coord", "target": "sfu"},
        {"source": "client_a", "target": "stun", "label": "srflx discovery"},
        {"source": "client_a", "target": "turn", "label": "relay (fallback)"},
        {"source": "client_a", "target": "sfu", "label": "RTP publish"},
        {"source": "sfu", "target": "client_b", "label": "RTP forward (selected layer)"},
        {"source": "sfu", "target": "client_n", "label": "RTP forward"},
        {"source": "client_a", "target": "edge", "label": "anycast entry"},
        {"source": "edge", "target": "sfu"},
        {"source": "signaling", "target": "kds", "label": "fetch meeting key (E2EE)"},
        {"source": "kds", "target": "client_a", "label": "wrapped key"},
        {"source": "recorder", "target": "sfu", "label": "subscribes as participant"},
        {"source": "recorder", "target": "obj_store", "label": "HLS segments"},
        {"source": "recorder", "target": "asr", "label": "audio stream"},
        {"source": "asr", "target": "obj_store", "label": "transcript"},
        {"source": "signaling", "target": "meta_db"},
        {"source": "coord", "target": "meta_db"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant A as Participant A\n"
        "  participant SIG as Signaling\n"
        "  participant CO as Coordinator\n"
        "  participant ST as STUN\n"
        "  participant TR as TURN\n"
        "  participant SFU\n"
        "  participant B as Participant B\n"
        "  A->>SIG: WS connect + join(meeting_id)\n"
        "  SIG->>CO: allocate SFU(region)\n"
        "  CO-->>SIG: sfu_endpoint, ice_servers\n"
        "  SIG-->>A: sfu_endpoint, ice_servers, meeting_key\n"
        "  A->>ST: STUN binding (gather srflx)\n"
        "  ST-->>A: server-reflexive candidate\n"
        "  A->>TR: TURN allocate (relay candidate)\n"
        "  TR-->>A: relay address\n"
        "  A->>SIG: SDP offer + ICE candidates\n"
        "  SIG->>SFU: forward offer\n"
        "  SFU-->>SIG: SDP answer\n"
        "  SIG-->>A: answer + remote ICE\n"
        "  Note over A,SFU: ICE connectivity checks\n"
        "  A->>SFU: RTP (simulcast L0/L1/L2)\n"
        "  SFU->>B: RTP (forwarded layer based on BWE)\n"
        "  B->>SFU: RTCP transport-cc feedback\n"
        "  SFU->>A: REMB / NACK / PLI as needed\n"
    ),
    er_diagram=(
        "erDiagram\n"
        "  USER ||--o{ MEETING : hosts\n"
        "  MEETING ||--o{ PARTICIPANT : has\n"
        "  MEETING ||--o| MEETING_KEY : encrypted_with\n"
        "  MEETING ||--o{ RECORDING : produces\n"
        "  MEETING ||--o{ CHAT_MESSAGE : has\n"
        "  MEETING ||--o{ BREAKOUT_ROOM : spawns\n"
        "  PARTICIPANT ||--o{ ICE_STATS : reports\n"
        "  MEETING { string meeting_id\n bigint host_user_id\n string region\n bool e2ee_enabled\n string status }\n"
        "  PARTICIPANT { string meeting_id\n bigint user_id\n string role\n bigint joined_at }\n"
        "  RECORDING { string recording_id\n string meeting_id\n int duration_sec\n string s3_key_video }\n"
        "  MEETING_KEY { string meeting_id\n blob wrapped_key\n int key_epoch }\n"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B{Latency target}\n"
        "  B -->|<200ms| C[UDP/RTP via WebRTC]\n"
        "  C --> D{Topology}\n"
        "  D -->|Mesh O(N^2)| E[Reject for N>4]\n"
        "  D -->|MCU| F[Heavy CPU; only for SIP]\n"
        "  D -->|SFU| G[Default choice]\n"
        "  G --> H[Signaling: SDP/ICE over WS]\n"
        "  H --> I[STUN+TURN for NAT]\n"
        "  I --> J[Simulcast/SVC + GCC BWE]\n"
        "  J --> K[FEC+NACK+jitter buffer]\n"
        "  K --> L{Recording?}\n"
        "  L -->|Yes| M[Recorder bot joins]\n"
        "  L -->|E2EE| N[Local-only recording]\n"
    ),
    tradeoff_title="P2P Mesh vs SFU vs MCU",
    tradeoff_options=[
        {"label": "P2P Mesh",
         "description": "Each participant sends its stream directly to every other participant.",
         "pros": ["Zero server media cost", "Lowest possible latency for 1:1",
                  "Native E2EE — no server in the path"],
         "cons": ["O(N^2) uplink — kills CPU/bandwidth at N>4",
                  "No server-side recording or transcription",
                  "NAT traversal must succeed for every pair"]},
        {"label": "MCU (Multipoint Control Unit)",
         "description": "Server decodes all incoming streams, mixes into a composite, re-encodes once per receiver.",
         "pros": ["Single output stream per receiver — works on any client",
                  "Required for SIP / phone gateway",
                  "Easy to record (already have the mix)"],
         "cons": ["Heavy CPU per meeting — decode N + encode N",
                  "Single layout / bitrate forced on all receivers",
                  "High per-meeting cost — limits scale"]},
        {"label": "SFU (Selective Forwarding Unit) — recommended",
         "description": "Server terminates RTP, selectively forwards simulcast/SVC layers without decoding.",
         "pros": ["O(N) uplink per participant + linear server egress",
                  "Per-receiver layer choice — adaptive bitrate without re-encoding",
                  "Supports 50–100 active participants per meeting",
                  "Composable with recorder bot for cloud recording"],
         "cons": ["Server sees encrypted RTP frames (unless E2EE with Insertable Streams)",
                  "Receiver-side composition required (clients render multiple tracks)",
                  "Bandwidth scales with N at the SFU egress"]},
    ],
    tradeoff_rec=(
        "SFU as default for 3+ participants. P2P mesh shortcut for 1:1 calls. MCU only as a "
        "gateway for SIP/phone dial-in clients that can't handle multiple incoming streams. "
        "Layer relay-SFU trees on top of base SFUs for webinars > a few hundred viewers."
    ),
    senior_topics=[
        _topic("webrtc-stack",
               "WebRTC: Signaling + Media + Traversal Decoupled",
               "WebRTC is not a protocol but a stack. Knowing the layer boundaries — signaling vs "
               "ICE vs RTP vs SRTP — separates senior candidates from juniors who say 'use WebRTC'.",
               [
                   ("Signaling is BYO",
                    "WebRTC defines no signaling protocol — apps choose WebSocket, SIP, or custom. "
                    "Carries SDP offer/answer + ICE candidates between peers. Decoupled from media."),
                   ("SDP — session description",
                    "Text describing media (codecs, resolutions, simulcast layers, RTP extensions, "
                    "DTLS fingerprints). Each side offers; the other answers with intersection."),
                   ("ICE — connectivity establishment",
                    "Gathers candidates (host, srflx via STUN, relay via TURN). Pairs candidates "
                    "from both peers, runs STUN binding requests over each pair, picks the "
                    "highest-priority working pair."),
                   ("DTLS-SRTP — media encryption",
                    "DTLS handshake over the chosen ICE pair establishes keys; SRTP encrypts each "
                    "RTP packet. Server-mediated SFU still uses SRTP between client and SFU — "
                    "decryption happens at SFU unless E2EE Insertable Streams is layered on top."),
                   ("RTCP — feedback loop",
                    "Receiver reports loss/jitter; sender adapts. NACK, PLI, FIR, REMB, and "
                    "transport-cc feedback all ride on RTCP. SFU acts as feedback router."),
               ],
               diagram=(
                   "graph LR\n"
                   "  C1[Client A] -- Signaling --> SIG[WS Server]\n"
                   "  SIG -- Signaling --> C2[Client B]\n"
                   "  C1 -- ICE check --> C2\n"
                   "  C1 -- DTLS-SRTP --> C2\n"
                   "  C1 -- RTP/RTCP --> C2\n"
               )),
        _topic("sfu-vs-mcu",
               "SFU vs MCU: The Topology Decision",
               "The single most consequential design choice in video conferencing. Drives CPU, "
               "bandwidth, codec flexibility, and recording strategy.",
               [
                   ("MCU economics",
                    "Server runs full decode of N streams + encode of N output streams per meeting. "
                    "CPU scales O(N) per meeting and is a hard ceiling — typically caps at ~16 "
                    "active video participants per server core."),
                   ("SFU economics",
                    "Server receives N RTP streams and forwards selected layers; no encode/decode. "
                    "CPU is dominated by packet shuffling — one server can handle thousands of "
                    "concurrent participants spread across many meetings."),
                   ("Per-receiver flexibility",
                    "MCU dictates layout and bitrate to all viewers. SFU forwards independent "
                    "tracks; client renders its own layout (active speaker focus, grid, picture-"
                    "in-picture). Receiver bandwidth chooses simulcast layer."),
                   ("When MCU still wins",
                    "SIP/H.323 endpoints, PSTN dial-in (one mixed audio stream), legacy hardware "
                    "video conferencing rooms. Modern web/mobile use SFU exclusively."),
                   ("Hybrid: cascading SFUs",
                    "For very large meetings or geo-distributed participants, deploy a tree of "
                    "SFUs. One ingest SFU per region; cross-region SFU-to-SFU relay edges connect "
                    "them. Avoids forcing every participant to a single regional SFU."),
               ],
               diagram=(
                   "graph TD\n"
                   "  subgraph MCU\n"
                   "    P1[A] --> M[Mix]\n"
                   "    P2[B] --> M\n"
                   "    P3[C] --> M\n"
                   "    M --> O1[Composite to A]\n"
                   "    M --> O2[Composite to B]\n"
                   "    M --> O3[Composite to C]\n"
                   "  end\n"
                   "  subgraph SFU\n"
                   "    Q1[A] --> S[SFU]\n"
                   "    Q2[B] --> S\n"
                   "    Q3[C] --> S\n"
                   "    S --> R1[B+C tracks to A]\n"
                   "    S --> R2[A+C tracks to B]\n"
                   "    S --> R3[A+B tracks to C]\n"
                   "  end\n"
               )),
        _topic("nat-traversal",
               "STUN, TURN, and ICE for NAT Traversal",
               "Roughly 15% of clients sit behind symmetric NATs or restrictive firewalls; without "
               "a deliberate strategy, calls fail. ICE is the orchestration layer.",
               [
                   ("Candidate types",
                    "Host = local interface IP. Server-reflexive (srflx) = public IP/port observed "
                    "by a STUN server. Peer-reflexive (prflx) = address discovered during checks. "
                    "Relay = TURN-allocated public address."),
                   ("STUN role",
                    "Lightweight binding request to STUN server returns the public IP/port the "
                    "server saw. Free, stateless, cheap to host. Solves cone-NAT scenarios."),
                   ("TURN role",
                    "Stateful relay allocating a public address that forwards packets bidirection-"
                    "ally. Required for symmetric NAT (port mapping is destination-specific) and "
                    "restrictive firewalls. Expensive — every byte of media traverses."),
                   ("ICE pairing + checks",
                    "Each side gathers all candidates and shares via signaling. ICE forms pairs, "
                    "prioritises (host > srflx > relay), runs STUN binding on each pair, promotes "
                    "highest-priority succeeding pair as nominated."),
                   ("TURN protocols",
                    "TURN/UDP preferred for performance. TURN/TCP and TURN/TLS-443 fallbacks for "
                    "egress-restrictive networks (corporate, hotel WiFi). Short-lived HMAC-signed "
                    "credentials prevent abuse."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant C as Client\n"
                   "  participant ST as STUN\n"
                   "  participant TR as TURN\n"
                   "  participant SFU\n"
                   "  C->>ST: Binding Request\n"
                   "  ST-->>C: srflx (public IP:port)\n"
                   "  C->>TR: Allocate\n"
                   "  TR-->>C: relay (public IP:port)\n"
                   "  C->>SFU: ICE checks (host, srflx, relay)\n"
                   "  SFU-->>C: nominate working pair\n"
                   "  C->>SFU: SRTP over chosen path\n"
               )),
        _topic("simulcast-svc-bwe",
               "Simulcast, SVC, and Bandwidth Estimation",
               "Adaptive bitrate without server transcoding. The SFU's superpower is forwarding "
               "different encoded layers to different receivers based on each receiver's network.",
               [
                   ("Simulcast",
                    "Publisher encodes the same video at 2–3 resolutions/bitrates simultaneously, "
                    "each on its own SSRC. Costs more uplink/CPU at sender; SFU picks layer per "
                    "receiver. Codec-agnostic — works on H.264 baseline."),
                   ("SVC (scalable video coding)",
                    "Single encoded stream contains hierarchical layers (temporal: drop B-frames; "
                    "spatial: drop high-res layers). SFU drops layers per subscriber. Saves uplink "
                    "vs simulcast. Requires VP9, AV1, or H.264-SVC."),
                   ("Sender-side BWE — GCC",
                    "Google Congestion Control: receiver timestamps RTP arrivals, sends transport-"
                    "cc feedback; sender computes delay-gradient + loss to estimate bandwidth, "
                    "adjusts encoder target every 100–500ms."),
                   ("SFU-side egress estimation",
                    "Each subscriber's downlink is estimated independently (transport-cc per "
                    "subscription). SFU drops to lower simulcast/SVC layer when downstream "
                    "congests — never blocks audio."),
                   ("Audio priority",
                    "Audio is uncompressible past ~30 kbps Opus. Under congestion, drop video "
                    "layers first; freeze video before sacrificing audio. Mark audio packets "
                    "with DSCP EF for QoS-aware networks."),
               ],
               diagram=(
                   "graph LR\n"
                   "  Pub[Publisher] -- L0 1080p --> SFU\n"
                   "  Pub -- L1 720p --> SFU\n"
                   "  Pub -- L2 180p --> SFU\n"
                   "  SFU -- L0 to A (gigabit) --> A[Subscriber A]\n"
                   "  SFU -- L1 to B (wifi) --> B[Subscriber B]\n"
                   "  SFU -- L2 to C (4G) --> C[Subscriber C]\n"
                   "  B -- transport-cc --> SFU\n"
                   "  SFU -- REMB/PLI --> Pub\n"
               )),
        _topic("packet-loss-jitter",
               "FEC, NACK, and Jitter Buffers",
               "Networks lose and reorder packets. Real-time media tolerates ~10% loss with "
               "layered recovery; the right mix balances latency, bandwidth, and quality.",
               [
                   ("Jitter buffer",
                    "Smooths arrival variance. Adaptive size (30–200ms) targets observed jitter "
                    "P99 with hysteresis. Larger = smoother; smaller = lower latency. Audio buffer "
                    "tighter than video."),
                   ("NACK (Negative ACK)",
                    "Receiver requests retransmit of specific lost RTP sequence numbers. Cheap on "
                    "bandwidth; adds RTT of latency. Disabled when RTT > ~150ms (retransmit "
                    "arrives too late)."),
                   ("FEC (Forward Error Correction)",
                    "Sender adds redundant packets carrying XOR or Reed-Solomon parity. Recovers "
                    "small loss bursts without retransmit. Costs ~10–30% bandwidth overhead. "
                    "RED for audio (simple duplication); ULPFEC/FlexFEC for video."),
                   ("Opus in-band FEC + RED",
                    "Opus encodes a low-bitrate redundant copy of the previous frame inside the "
                    "next frame; RED layer adds an additional duplicate. Audio survives 10%+ loss "
                    "with imperceptible artifacts."),
                   ("Keyframe requests (PLI/FIR)",
                    "When video decoder state is unrecoverable (inter-frame chain broken), "
                    "receiver sends PLI; sender produces a keyframe. Keyframes are large — avoid "
                    "thrashing under sustained loss; back off temporal layers first."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant S as Sender\n"
                   "  participant N as Network\n"
                   "  participant R as Receiver\n"
                   "  S->>N: RTP seq=1..10 + FEC parity\n"
                   "  N->>R: 1,2,4,5,6,7,8,9,10 (lost 3)\n"
                   "  R->>R: FEC recovers seq=3\n"
                   "  Note over R: jitter buffer reorders\n"
                   "  R->>S: NACK seq=99 (later loss)\n"
                   "  S->>R: retransmit seq=99\n"
               )),
        _topic("e2ee-meetings",
               "End-to-End Encryption with Per-Meeting Keys",
               "SFU sees every RTP packet — by default, the operator can decrypt media. E2EE "
               "removes that capability using frame-level encryption with keys the SFU never sees.",
               [
                   ("Why SRTP isn't E2EE",
                    "SRTP encrypts hop-by-hop: client to SFU. SFU decrypts to inspect headers and "
                    "re-encrypts to next hop. Operator-side compromise reveals media."),
                   ("Insertable Streams API",
                    "WebRTC API exposing each frame as a buffer pre-SRTP on send and post-SRTP on "
                    "receive. App layers AES-GCM with a key the SFU doesn't have; SFU forwards "
                    "opaque ciphertext frames."),
                   ("Per-meeting key distribution",
                    "Key Distribution Service generates a symmetric meeting key on creation. "
                    "Wrapped per-participant under their device public key (KEM-style); delivered "
                    "via authenticated signaling. Rotated on participant leave (epoch increment)."),
                   ("Tradeoffs",
                    "Server-side recording, live transcription, background-blur, virtual "
                    "background, and noise suppression all run on plaintext frames — unavailable "
                    "in E2EE. Recording becomes local-only on each participant's device."),
                   ("Verification",
                    "Display per-meeting safety code (hash of meeting key + participant fingerprints) "
                    "for out-of-band comparison. Detects MITM key substitution by the operator."),
               ],
               diagram=(
                   "graph LR\n"
                   "  KDS[Key Distribution] -- wrapped key --> A[Participant A]\n"
                   "  KDS -- wrapped key --> B[Participant B]\n"
                   "  A -- AES-GCM(frame, K) --> SFU\n"
                   "  SFU -- opaque ciphertext --> B\n"
                   "  B -- AES-GCM-decrypt(K) --> B\n"
                   "  Note[SFU never sees K]\n"
               )),
        _topic("recording-and-asr",
               "Server-Side Recording and Live Transcription",
               "Recording is implemented as a 'recorder participant' — a headless bot that joins "
               "the meeting like any other client. Architectural symmetry keeps the SFU simple.",
               [
                   ("Recorder bot model",
                    "Headless WebRTC client subscribes to all tracks via the SFU. Receives audio "
                    "and video like any participant; uses meeting key (only available when E2EE "
                    "is off or recording is opt-in)."),
                   ("Audio mixing",
                    "Sum-and-AGC across all participant audio tracks; ducking for very loud "
                    "speakers. Diarization tags each speaker for the transcript."),
                   ("Video composition",
                    "Two modes: active-speaker focus (one large tile, others small) or grid "
                    "(equal tiles). Composer pulls active-speaker events from SFU control plane "
                    "to switch focus tile. Output encoded as HLS segments."),
                   ("Streaming ASR",
                    "Audio stream forwarded to streaming ASR service (chunked transfer). Returns "
                    "incremental transcripts with word timestamps. Live captions overlaid on UI; "
                    "final transcript stored alongside recording."),
                   ("Post-processing",
                    "Trim silence, generate thumbnail strip, finalize HLS manifest, package "
                    "metadata (attendees, chat log, timestamps), write to durable object store. "
                    "Notify host with playback URL via email/notification."),
               ],
               diagram=(
                   "graph TD\n"
                   "  SFU -- audio+video tracks --> R[Recorder Bot]\n"
                   "  R -- audio --> ASR[Streaming ASR]\n"
                   "  ASR -- captions --> UI[Meeting UI]\n"
                   "  R -- mixed audio --> ENC[HLS Encoder]\n"
                   "  R -- composed video --> ENC\n"
                   "  ENC --> S3[Object Store]\n"
                   "  ASR -- transcript --> S3\n"
               )),
    ],
)
