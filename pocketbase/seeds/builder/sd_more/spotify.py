"""SD-Spotify — Design Spotify (music streaming + recommendations).
Mirrors the schema/shape of SD_01 in sd_questions.py."""
from __future__ import annotations

from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design Spotify",
    "Hard",
    "Design a global music streaming platform supporting on-demand audio playback, library/playlist "
    "management, search, and personalised recommendations. The system must store master audio durably, "
    "transcode into multiple bitrates and codecs (Ogg Vorbis for desktop, AAC for iOS/web), distribute "
    "via CDN with HTTP range requests for instant seek, enforce DRM (Widevine/FairPlay) on premium "
    "tracks, and serve hundreds of millions of users with sub-200ms time-to-first-audio. Cover "
    "playlists/library, search, recommendations (collaborative filtering + content-based + ML), the "
    "Discover Weekly batch pipeline, listening-history ingestion via Kafka, offline caching for premium "
    "users, royalty/play-count tracking for rights-holder payouts, and social features (friends, "
    "sharing, collaborative playlists).",
    hints=[
        "Music files are small, finite, and immutable — unlike video, the catalog is closed-form (~100M tracks) and changes slowly.",
        "Read-heavy by 10000:1 — design the playback path first, the upload/ingest path is back-office.",
        "HTTP range requests over static files >> HLS for on-demand audio. HLS only for live/podcast simulcast.",
        "Recommendations are NOT a single model — collaborative filtering + content-based audio analysis + session-based ML.",
        "Discover Weekly is a weekly batch — offline pipeline, not real-time. Don't conflate with Daily Mix.",
        "Royalty tracking is the financial source of truth — every play must be attributable; eventual consistency OK but no loss.",
        "Offline cache for premium uses encrypted local storage tied to device + license refresh on reconnect.",
    ],
    constraints=[
        "100M+ tracks in catalog; ~60K new tracks/day from ingest partners",
        "500M+ MAU, ~200M premium subscribers",
        "Time-to-first-audio p95 < 200ms on broadband, < 500ms on mobile",
        "Audio masters: lossless 24-bit/96kHz FLAC; renditions: Ogg Vorbis 96/160/320kbps, AAC 128/256kbps for iOS",
        "11 nines durability for masters; royalty/play data zero-loss",
        "Offline cache size: up to 10K tracks per premium device",
        "Cost-sensitive — most catalog is long-tail, very low play frequency",
    ],
    req_func=[
        "Stream a track on demand with instant start and seek",
        "Search tracks/artists/albums/playlists with typeahead",
        "Manage user library: liked songs, followed artists, saved albums",
        "Create, edit, share, and collaborate on playlists",
        "Personalised recommendations: home page, Daily Mix, Discover Weekly, Release Radar",
        "Play-count and listening-history tracking for users + royalty payouts",
        "Offline download for premium users (encrypted, license-bound)",
        "DRM-protected playback for premium-only tracks",
        "Social: follow friends, see friend activity, share track/playlist",
        "Podcast support (live + on-demand episodes)",
    ],
    req_nonfunc=[
        "Playback start p95 < 200ms; seek p95 < 100ms",
        "Stream success rate > 99.95%; rebuffer ratio < 0.5%",
        "11 nines durability for masters; renditions reproducible from masters",
        "Read:write ratio ~10000:1 — optimise CDN + cache for playback",
        "Eventual consistency for play counts and friend activity (seconds–minutes)",
        "Strong consistency for billing/subscription state",
        "Royalty pipeline: zero play loss tolerated; auditable end-to-end",
        "Offline DRM: license expiry honoured; revocation propagates within 24h",
    ],
    estimation={
        "mau": "500M (premium ~200M)",
        "catalog_size": "100M tracks; avg 4 min @ 320 kbps Ogg ≈ 9.6 MB/track → ~1 PB renditions per codec",
        "masters_storage": "100M × ~50 MB FLAC ≈ 5 PB; cross-region replicated",
        "plays_per_day": "~5B plays/day → ~60K plays/sec steady, ~200K/sec peak",
        "search_qps": "~100K/sec peak with typeahead amplification",
        "cdn_egress": "~50–80 Tbps peak audio egress (small per-stream but huge concurrency)",
        "kafka_events_day": "~5B play events + ~50B fine-grained UI events (skip, seek, like)",
        "discover_weekly_batch": "200M premium users × ~30 candidate tracks scored = 6B candidate scorings/week",
    },
    endpoints=[
        {"method": "GET", "path": "/tracks/{track_id}",
         "description": "Fetch track metadata + signed CDN URLs per rendition"},
        {"method": "GET", "path": "/audio/{track_id}/{rendition}",
         "description": "CDN-served audio file; supports HTTP Range for seek",
         "body": "headers: Range: bytes=0-65535"},
        {"method": "POST", "path": "/license/widevine",
         "description": "Acquire Widevine license for DRM-protected track",
         "body": "{track_id, device_id, challenge}"},
        {"method": "GET", "path": "/search",
         "description": "Search across tracks/artists/albums/playlists",
         "body": "?q=...&type=track,artist&limit=20"},
        {"method": "POST", "path": "/me/playlists",
         "description": "Create playlist",
         "body": "{name, public, collaborative}"},
        {"method": "PUT", "path": "/me/playlists/{pid}/tracks",
         "description": "Add tracks to playlist (idempotent positions)"},
        {"method": "GET", "path": "/me/home",
         "description": "Personalised home page (Daily Mix, Discover Weekly, recommendations)"},
        {"method": "POST", "path": "/me/plays",
         "description": "Report play event (fire-and-forget to Kafka)",
         "body": "{track_id, started_at, played_ms, context, device}"},
        {"method": "POST", "path": "/me/offline/{track_id}",
         "description": "Download track for offline (premium); returns encrypted file + license"},
        {"method": "GET", "path": "/me/friends/activity",
         "description": "Recent listening activity from followed friends"},
    ],
    tables=[
        {"name": "tracks",
         "columns": ["track_id VARCHAR(22) PK", "title VARCHAR(255)", "artist_id BIGINT",
                     "album_id BIGINT", "duration_ms INT", "isrc VARCHAR(15)", "explicit BOOL",
                     "rights_holder_id BIGINT", "drm_protected BOOL", "released_at BIGINT"]},
        {"name": "renditions",
         "columns": ["track_id VARCHAR(22)", "codec VARCHAR(8)", "bitrate_kbps INT",
                     "size_bytes BIGINT", "cdn_key VARCHAR(255)",
                     "PRIMARY KEY (track_id, codec, bitrate_kbps)"]},
        {"name": "audio_features",
         "columns": ["track_id VARCHAR(22) PK", "tempo_bpm FLOAT", "key INT", "energy FLOAT",
                     "danceability FLOAT", "valence FLOAT", "acousticness FLOAT",
                     "embedding VECTOR(128)"]},
        {"name": "playlists",
         "columns": ["playlist_id VARCHAR(22) PK", "owner_id BIGINT", "name VARCHAR(100)",
                     "public BOOL", "collaborative BOOL", "created_at BIGINT", "updated_at BIGINT"]},
        {"name": "playlist_tracks",
         "columns": ["playlist_id VARCHAR(22)", "position INT", "track_id VARCHAR(22)",
                     "added_by BIGINT", "added_at BIGINT", "PRIMARY KEY (playlist_id, position)"]},
        {"name": "user_library",
         "columns": ["user_id BIGINT", "kind VARCHAR(8)", "ref_id VARCHAR(22)",
                     "added_at BIGINT", "PRIMARY KEY (user_id, kind, ref_id)"]},
        {"name": "play_events",
         "columns": ["event_id BIGINT PK", "user_id BIGINT", "track_id VARCHAR(22)",
                     "ts BIGINT", "played_ms INT", "context VARCHAR(64)", "device VARCHAR(32)",
                     "country VARCHAR(2)"]},
        {"name": "play_counts",
         "columns": ["track_id VARCHAR(22) PK", "count BIGINT", "monthly_listeners BIGINT",
                     "updated_at BIGINT"]},
        {"name": "royalties",
         "columns": ["royalty_id BIGINT PK", "rights_holder_id BIGINT", "track_id VARCHAR(22)",
                     "period_start BIGINT", "period_end BIGINT", "qualified_plays BIGINT",
                     "amount_cents BIGINT", "status VARCHAR(16)"]},
        {"name": "follows",
         "columns": ["follower_id BIGINT", "followee_id BIGINT", "ts BIGINT",
                     "PRIMARY KEY (follower_id, followee_id)"]},
        {"name": "drm_licenses",
         "columns": ["license_id VARCHAR(64) PK", "user_id BIGINT", "track_id VARCHAR(22)",
                     "device_id VARCHAR(64)", "issued_at BIGINT", "expires_at BIGINT",
                     "scope VARCHAR(16)"]},
    ],
    indexes=[
        "(artist_id, released_at DESC) on tracks — artist discography",
        "(album_id) on tracks — album page",
        "FULLTEXT(title) on tracks — search",
        "(playlist_id, position) on playlist_tracks — playlist render",
        "(user_id, added_at DESC) on user_library — recently saved",
        "(user_id, ts DESC) on play_events — listening history",
        "(track_id, ts) on play_events — partition by track for aggregation",
        "(rights_holder_id, period_start) on royalties — payout reports",
        "(follower_id) on follows — friend feed",
    ],
    hld_desc=(
        "Three decoupled planes. Ingest plane: label/artist uploads → master store → transcode fleet "
        "produces Ogg Vorbis + AAC ladder → CDN-pushed renditions; metadata + audio-feature extraction "
        "feeds search and recommendation. Playback plane: catalog + playlist services back a thin "
        "metadata API; audio bytes served by global CDN as static range-requestable files; DRM-protected "
        "tracks gated by license server (Widevine/FairPlay). Data plane: every play/skip/seek event "
        "lands in Kafka; stream aggregator drives near-real-time counters and home-page candidates; "
        "batch (Spark) drives Discover Weekly weekly, royalty settlement monthly, and offline "
        "candidate-generation models for recommendations."
    ),
    hld_components=[
        {"name": "Ingest Service", "role": "Validate label uploads; ISRC/UPC dedup; trigger transcode"},
        {"name": "Master Store", "role": "11-nines durable lossless FLAC originals"},
        {"name": "Transcode Fleet", "role": "Produce Ogg Vorbis (96/160/320) + AAC (128/256) renditions"},
        {"name": "Audio Analyzer", "role": "Extract tempo/key/energy + neural embedding for content-based reco"},
        {"name": "Catalog Service", "role": "Track/album/artist metadata CRUD + read-through cache"},
        {"name": "Search Service", "role": "Elasticsearch-backed track/artist/album/playlist search + typeahead"},
        {"name": "Playlist Service", "role": "Playlist CRUD, collaborative edits with CRDT/OT"},
        {"name": "Library Service", "role": "User saved tracks/albums/artists; offline-tolerant client sync"},
        {"name": "License Server", "role": "Widevine/FairPlay DRM license issuance + revocation"},
        {"name": "CDN", "role": "Global edge for static audio range requests + manifests"},
        {"name": "Origin Shield", "role": "Mid-tier cache; collapses regional miss storms to origin"},
        {"name": "Kafka Backbone", "role": "Listening events, royalty events, social events"},
        {"name": "Stream Aggregator (Flink)", "role": "Near-real-time play counts, monthly listeners, home candidates"},
        {"name": "Batch Pipeline (Spark)", "role": "Discover Weekly, Release Radar, royalty settlement"},
        {"name": "Recommendation Service", "role": "Candidate gen (CF + content-based) + online ranking"},
        {"name": "Royalty Engine", "role": "Per-stream payout calc against rights-holder contracts"},
        {"name": "Social Service", "role": "Follow graph, friend activity feed, sharing"},
    ],
    detailed_design={
        "audio_storage_and_codecs": (
            "Masters are 24-bit/96kHz FLAC, stored once in 11-nines object storage with cross-region "
            "replication. From each master, the transcode fleet produces an immutable rendition set: "
            "Ogg Vorbis at 96 kbps (Free tier mobile), 160 kbps (Free desktop), 320 kbps (Premium); "
            "AAC at 128 kbps and 256 kbps for iOS/web where Vorbis lacks hardware decode. Each "
            "rendition is content-addressed (sha256 of bytes) so de-dup across re-ingests is automatic "
            "and CDN cache keys are stable forever. Renditions are cheap and regenerable — for cold "
            "long-tail tracks we keep only Vorbis 160 in warm tier; the rest regenerate on demand."
        ),
        "playback_protocol": (
            "On-demand audio is a single static file per (track, rendition). The client opens the "
            "stream with HTTP Range requests (e.g., bytes=0-262143 first), gets a fast 200ms first-"
            "buffer, and continues with sequential ranges. Seek is a fresh range request to the "
            "computed byte offset (size × seek_fraction) — instant, no manifest. We deliberately "
            "skip HLS/DASH for VOD audio because (a) audio is small enough that ABR switching gains "
            "little, (b) range requests over a single file have far simpler CDN cache semantics, "
            "(c) seek latency is much lower without manifest reload. HLS is reserved for live radio "
            "and podcast simulcast where adaptive bitrate over time matters."
        ),
        "drm_widevine": (
            "Premium-only or label-mandated tracks are encrypted at rest using AES-128 CTR per-track "
            "content key. The client bootstraps playback by sending a Widevine challenge (or FairPlay "
            "SPC on iOS) to the License Server, which validates subscription state, device "
            "attestation, and per-track entitlement, then returns a license bound to (user, device) "
            "with TTL. License Server issues short-TTL streaming licenses for online play and "
            "longer-TTL persistent licenses for offline downloads. Revocation: subscription cancel "
            "flips an entitlement bit; clients refresh license on next online tick (within 24h cap). "
            "Free-tier non-DRM tracks ship plaintext; the cost of CDM negotiation isn't paid where "
            "the rights holder doesn't require it."
        ),
        "playlists_and_library": (
            "Playlists are sharded by playlist_id. The track list is stored as a (playlist_id, "
            "position, track_id) row set; reorder/insert is a small range update, not a rewrite. "
            "Collaborative playlists use server-mediated operational transform on insert/delete/move "
            "ops so two simultaneous editors converge. User library (liked tracks, saved albums) is "
            "a per-user table with offline-tolerant sync: client tracks a sync_token; on reconnect, "
            "POST deltas + GET server changes since token. Playlists are eventually consistent — "
            "reads can hit a cache lagging seconds; writes are read-your-write via session affinity."
        ),
        "search": (
            "Elasticsearch cluster sharded by entity type. Indexes pulled via CDC from catalog and "
            "playlist primaries. Typeahead uses edge-ngram analyzer + completion suggester for "
            "artist/track names; re-ranks by global popularity (play count) and per-user affinity "
            "(personalisation overlay). Multi-language: per-locale analyzer chain. Latency budget: "
            "p95 < 50 ms server-side; client coalesces keystrokes."
        ),
        "recommendations": (
            "Three-pillar candidate generation. (1) Collaborative filtering: weekly matrix-factorisation "
            "on the (user, track, listen_count) matrix → user/item embeddings; nearest-neighbour "
            "lookups produce 'because you listened to X' rails. (2) Content-based: audio analyser "
            "outputs a 128-d neural embedding per track (CNN on mel-spectrograms); ANN index serves "
            "track-similarity even for cold-start tracks with zero plays. (3) Session/sequence model: "
            "transformer trained on listening sessions predicts next-best-track for queue extension "
            "and Daily Mix radio. Candidates from all three pillars feed an online ranker (gradient-"
            "boosted trees / DNN) that scores ~500 candidates against per-request features (time-of-"
            "day, device, recent skips) at p95 < 80 ms via a feature store + low-latency model server."
        ),
        "discover_weekly_pipeline": (
            "Weekly batch on Spark over the last-90-days listening matrix. Step 1: refresh user/track "
            "embeddings via ALS matrix factorisation. Step 2: for each premium user, generate ~500 "
            "candidate tracks (CF nearest neighbours filtered out by 'already heard last 90d'). "
            "Step 3: re-rank candidates with a personalisation model trained on prior-week skip/save "
            "labels. Step 4: choose top 30 with diversity constraints (artist/genre quotas) → write "
            "to a per-user playlist row. Drop happens Monday 00:00 in user's local timezone — "
            "playlist writer staggers by timezone to spread CDN warm-up."
        ),
        "listening_history_via_kafka": (
            "Client SDK emits a play event when a track passes the 30-second royalty threshold "
            "(qualified play) plus skip/seek/like/queue events. Events go through edge collectors "
            "to Kafka topics partitioned by user_id (preserves per-user order). Two consumers: "
            "(a) Flink stream — increments per-track play_counts (HLL for monthly_listeners), updates "
            "per-user recent-listening for home-page personalisation; writes to Cassandra/Redis. "
            "(b) Spark batch — daily archive in S3, source for Discover Weekly + royalty settlement. "
            "Anti-fraud: bot detection inline in Flink filters bot streams before counting toward "
            "royalty or charts."
        ),
        "offline_caching_premium": (
            "Premium users can pin tracks/playlists for offline. Client requests offline download → "
            "License Server issues a persistent Widevine license (TTL 30d) bound to device → CDN "
            "ships the encrypted file. Local store keeps (track_id, file_path, license_blob, "
            "license_expires_at). Playback verifies license validity locally; on reconnect, client "
            "refreshes license proactively if within 7d of expiry. Subscription cancel revokes by "
            "refusing license refresh; next online tick disables offline playback. Cap: 10K tracks "
            "per device × 5 devices/account."
        ),
        "royalty_play_count_tracking": (
            "A play counts for royalty if played_ms > 30000 (industry standard). Royalty pipeline: "
            "Spark daily job aggregates qualified_plays per (track, country, period). Royalty "
            "engine joins against rights_holder contracts (per-stream rate by territory, mechanical "
            "vs publishing splits) and computes payout per rights-holder per period. Output is a "
            "monthly settlement file; auditors can replay from Kafka archive any time. Zero loss is "
            "non-negotiable: Kafka has 30-day retention + S3 archive forever; consumer offsets are "
            "committed only after batch write success."
        ),
        "social_friends_sharing": (
            "Follow graph stored in a Cassandra table (follower → followee) with denormalised "
            "(followee → followers) for fan-out. Friend Activity uses fan-out-on-write for users with "
            "< 10K followers (most users) — write a row to each follower's activity feed when the "
            "user plays a public track. For high-fanout celebrities, switch to fan-out-on-read: feed "
            "service queries followee feeds and merges. Sharing a track/playlist creates a short-link "
            "with an OG image; click attribution lands in Kafka."
        ),
        "slo_contract": (
            "Time-to-first-audio p95 < 200 ms; rebuffer < 0.5%. Search p95 < 100 ms end-to-end. "
            "Recommendation home page p95 < 300 ms. Royalty settlement: monthly with auditable "
            "lineage. Offline license refresh within 24h of subscription change."
        ),
    },
    trade_offs=[
        {"option": "HTTP Range over static files vs HLS/DASH for on-demand audio",
         "for_range": "Lower latency, simpler CDN, instant seek, no manifest overhead",
         "for_hls": "Adaptive bitrate over poor networks; native player support for live",
         "recommendation": "Range requests for VOD audio; HLS for live radio and podcasts."},
        {"option": "Codec: Ogg Vorbis vs AAC",
         "for_vorbis": "Royalty-free, slightly better quality at low bitrates, Spotify's historic codec",
         "for_aac": "Hardware decode on iOS/web, ubiquitous, slightly higher compute on encode",
         "recommendation": "Both — Vorbis for Android/desktop, AAC for iOS/web; pay the dual-rendition cost."},
        {"option": "Recommendation: pure CF vs hybrid CF + content-based + sequence",
         "for_cf": "High quality on hot users/tracks; conceptually simple",
         "for_hybrid": "Solves cold-start; richer signal blend; better diversity",
         "recommendation": "Hybrid — CF carries the warm catalog; content embeddings cover cold-start and new releases."},
        {"option": "Discover Weekly: real-time vs weekly batch",
         "for_realtime": "Always fresh; reactive to recent listening shifts",
         "for_batch": "Cheaper, simpler, ritual matters (Monday drop is product anchor)",
         "recommendation": "Weekly batch — Discover Weekly is a product ritual, not a real-time feature; Daily Mix covers freshness."},
        {"option": "Friend activity: fan-out on write vs fan-out on read",
         "for_write": "Fast feed reads",
         "for_read": "No celebrity-fanout amplification",
         "recommendation": "Hybrid by follower count threshold — write for the long tail, read for the head."},
        {"option": "Offline: streaming-only vs encrypted local cache",
         "for_streaming": "Always-fresh license, simpler client",
         "for_offline": "Required for premium product promise; mandatory subway/airplane UX",
         "recommendation": "Encrypted offline with persistent Widevine license; refresh proactively."},
    ],
    tips=[
        "Lead with read:write ratio (10000:1) — the playback path dominates everything.",
        "Distinguish on-demand audio (range requests) from live audio (HLS). Most candidates default to HLS unnecessarily.",
        "Name both codecs (Ogg Vorbis + AAC) and explain WHY (royalty + iOS hardware decode).",
        "Recommendations are a portfolio, not one model — CF + content-based + session. Naming all three earns senior signal.",
        "Royalty pipeline is its own thing — interviewers love when candidates remember Spotify is fundamentally a payout machine.",
        "Discover Weekly = batch (Monday drop ritual). Daily Mix = quasi-real-time. Don't conflate.",
        "DRM = Widevine (Android/web) + FairPlay (iOS). Mention both; the dual-CDM cost is real.",
        "Offline cache must include license expiry + revocation story, not just bytes.",
        "Kafka is the spine — play events drive counts, recommendations, royalties. Event schema is load-bearing.",
    ],
    thought_process=[
        "1. Clarify: on-demand only? Live/podcasts? Free + premium? Global? Recommendations scope?",
        "2. Estimate: 500M MAU, 100M tracks, 5B plays/day → playback path dominates.",
        "3. Catalog ingest: label upload → master FLAC → transcode to Ogg Vorbis + AAC ladder.",
        "4. Playback path: thin metadata API + CDN-served static audio with HTTP Range requests.",
        "5. DRM gate: Widevine/FairPlay license server checks subscription + device, issues bound license.",
        "6. Search: Elasticsearch with edge-ngram + popularity re-rank.",
        "7. Recommendations portfolio: CF (matrix factorisation) + content-based (audio embedding) + session model.",
        "8. Discover Weekly: weekly Spark batch; staggered Monday drop by user timezone.",
        "9. Listening history: Kafka → Flink (near-RT counts) + Spark (batch for royalties + Discover).",
        "10. Royalty engine: qualified_plays × per-territory rate against rights-holder contracts.",
        "11. Offline cache: encrypted local file + persistent Widevine license + proactive refresh.",
        "12. Social: hybrid fan-out by follower count; sharing via short-link + Kafka attribution.",
    ],
    tags=["audio", "streaming", "recommendations", "cdn", "metadata"],
    arch_nodes=[
        {"id": "client", "label": "Mobile / Web / Desktop", "type": "client"},
        {"id": "lb", "label": "API Gateway", "type": "lb"},
        {"id": "catalog", "label": "Catalog Service", "type": "server"},
        {"id": "playlist", "label": "Playlist Service", "type": "server"},
        {"id": "library", "label": "Library Service", "type": "server"},
        {"id": "search", "label": "Search (ES)", "type": "database"},
        {"id": "license", "label": "DRM License Server", "type": "service"},
        {"id": "cdn", "label": "CDN (Edge POPs)", "type": "cache"},
        {"id": "shield", "label": "Origin Shield", "type": "cache"},
        {"id": "rendition_store", "label": "Rendition Store", "type": "database"},
        {"id": "master_store", "label": "Master Store (FLAC)", "type": "database"},
        {"id": "transcode", "label": "Transcode Fleet", "type": "server"},
        {"id": "analyzer", "label": "Audio Analyzer", "type": "server"},
        {"id": "meta_db", "label": "Metadata DB", "type": "database"},
        {"id": "kafka", "label": "Kafka", "type": "queue"},
        {"id": "flink", "label": "Stream Aggregator", "type": "server"},
        {"id": "spark", "label": "Batch Pipeline", "type": "server"},
        {"id": "rec", "label": "Recommendation Service", "type": "service"},
        {"id": "royalty", "label": "Royalty Engine", "type": "service"},
        {"id": "social", "label": "Social Service", "type": "service"},
    ],
    arch_edges=[
        {"source": "client", "target": "lb"},
        {"source": "lb", "target": "catalog", "label": "metadata"},
        {"source": "lb", "target": "playlist"},
        {"source": "lb", "target": "library"},
        {"source": "lb", "target": "search"},
        {"source": "lb", "target": "license", "label": "DRM challenge"},
        {"source": "client", "target": "cdn", "label": "Range GET audio"},
        {"source": "cdn", "target": "shield", "label": "miss"},
        {"source": "shield", "target": "rendition_store", "label": "miss"},
        {"source": "transcode", "target": "rendition_store"},
        {"source": "master_store", "target": "transcode"},
        {"source": "transcode", "target": "analyzer"},
        {"source": "analyzer", "target": "meta_db", "label": "audio features"},
        {"source": "catalog", "target": "meta_db"},
        {"source": "client", "target": "kafka", "label": "play/skip/seek events"},
        {"source": "kafka", "target": "flink"},
        {"source": "kafka", "target": "spark"},
        {"source": "flink", "target": "meta_db", "label": "near-RT counts"},
        {"source": "spark", "target": "rec", "label": "Discover Weekly"},
        {"source": "spark", "target": "royalty", "label": "qualified plays"},
        {"source": "rec", "target": "client", "label": "home / Daily Mix"},
        {"source": "social", "target": "kafka"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant U as User App\n"
        "  participant API\n"
        "  participant Cat as Catalog\n"
        "  participant Lic as License Server\n"
        "  participant CDN\n"
        "  participant K as Kafka\n"
        "  U->>API: GET /tracks/{id}\n"
        "  API->>Cat: metadata\n"
        "  Cat-->>API: track + signed CDN URL\n"
        "  API-->>U: metadata + URL\n"
        "  U->>Lic: Widevine challenge\n"
        "  Lic->>Lic: verify entitlement\n"
        "  Lic-->>U: license (key)\n"
        "  U->>CDN: GET audio (Range: 0-262143)\n"
        "  CDN-->>U: bytes (encrypted)\n"
        "  U->>U: decrypt + play (TTFA ~150ms)\n"
        "  loop seek / continue\n"
        "    U->>CDN: Range bytes=N-M\n"
        "    CDN-->>U: bytes\n"
        "  end\n"
        "  U->>K: play_event (after 30s)\n"
    ),
    er_diagram=(
        "erDiagram\n"
        "  ARTIST ||--o{ ALBUM : releases\n"
        "  ALBUM ||--o{ TRACK : contains\n"
        "  TRACK ||--o{ RENDITION : has\n"
        "  TRACK ||--|| AUDIO_FEATURES : analyzed\n"
        "  USER ||--o{ PLAYLIST : owns\n"
        "  PLAYLIST ||--o{ PLAYLIST_TRACK : has\n"
        "  PLAYLIST_TRACK }o--|| TRACK : refs\n"
        "  USER ||--o{ USER_LIBRARY : saves\n"
        "  USER ||--o{ PLAY_EVENT : produces\n"
        "  TRACK ||--o{ PLAY_EVENT : receives\n"
        "  RIGHTS_HOLDER ||--o{ ROYALTY : earns\n"
        "  USER ||--o{ DRM_LICENSE : holds\n"
        "  TRACK { string track_id\n string title\n bigint artist_id\n int duration_ms\n bool drm_protected }\n"
        "  RENDITION { string track_id\n string codec\n int bitrate_kbps\n string cdn_key }\n"
        "  PLAY_EVENT { bigint event_id\n bigint user_id\n string track_id\n bigint ts\n int played_ms }\n"
        "  ROYALTY { bigint royalty_id\n bigint rights_holder_id\n bigint qualified_plays\n bigint amount_cents }\n"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B{Read:write ratio}\n"
        "  B -->|10000:1| C[Playback path first]\n"
        "  C --> D[CDN + HTTP Range over static files]\n"
        "  D --> E[Codecs: Vorbis + AAC]\n"
        "  E --> F[DRM: Widevine + FairPlay]\n"
        "  F --> G[Search: ES + popularity rerank]\n"
        "  G --> H[Recommendations: CF + content + session]\n"
        "  H --> I[Discover Weekly: weekly Spark batch]\n"
        "  I --> J[Listening history: Kafka -> Flink + Spark]\n"
        "  J --> K[Royalty engine: qualified plays x rate]\n"
        "  K --> L[Offline: encrypted file + persistent license]\n"
        "  L --> M[Social: hybrid fan-out]\n"
    ),
    tradeoff_title="HTTP Range Requests vs HLS/DASH for On-Demand Audio",
    tradeoff_options=[
        {"label": "HTTP Range over static files (recommended)",
         "description": "One file per (track, rendition); client uses Range headers for first buffer and seek.",
         "pros": ["Lowest TTFA (no manifest round-trip)",
                  "Instant seek by byte offset",
                  "Trivial CDN cache key (URL path) with infinite TTL",
                  "No manifest churn or signing complexity"],
         "cons": ["No mid-stream bitrate switching (mitigated: client picks rendition up front)",
                  "Less suited to live or very long-form variable-bandwidth content"]},
        {"label": "HLS / DASH for on-demand audio",
         "description": "Segment each rendition; client downloads manifest then segments adaptively.",
         "pros": ["Adaptive bitrate over flaky networks",
                  "Standard tooling pipeline shared with video"],
         "cons": ["Extra manifest fetch increases TTFA",
                  "Seek requires segment boundary alignment",
                  "Manifest signing + short TTL adds CDN/origin complexity",
                  "Audio files are small enough that ABR rarely pays off"]},
        {"label": "Hybrid: range for VOD audio, HLS for live",
         "description": "Use range requests on the catalog; reserve HLS for live radio and live podcasts.",
         "pros": ["Best of both worlds",
                  "Right tool per workload"],
         "cons": ["Two playback code paths to maintain on the client"]},
    ],
    tradeoff_rec=(
        "HTTP Range over static files for the entire on-demand catalog; HLS only for live radio "
        "and live podcast simulcast. The TTFA + seek-latency win on the dominant playback path is "
        "decisive at Spotify scale; ABR for ~10 MB files isn't worth the manifest cost."
    ),
    senior_topics=[
        _topic("audio-codecs-and-renditions",
               "Audio Codecs: Ogg Vorbis vs AAC and Why Spotify Carries Both",
               "Spotify must serve every device class with sensible bitrate ladders while keeping "
               "royalty exposure low. The codec mix is a deliberate trade between licensing, "
               "decoder availability, and quality.",
               [
                   ("Why Ogg Vorbis historically",
                    "Royalty-free, no patent licensing fees, slightly better quality than MP3 at "
                    "low bitrates. Spotify's desktop and Android clients use Vorbis at 96 / 160 / "
                    "320 kbps."),
                   ("Why AAC for iOS and web",
                    "iOS and Safari have hardware AAC decoders but no native Vorbis. Software-"
                    "decoding Vorbis on iPhone wastes battery and adds CPU load. AAC at 128 / 256 "
                    "kbps is the iOS Premium ceiling."),
                   ("Storage cost of dual renditions",
                    "Each track ships ~5 renditions (Vorbis × 3 + AAC × 2) ≈ 25–40 MB additional "
                    "warm storage per track. Across 100M tracks that is ~3 PB of regenerable data "
                    "— offset by deleting cold long-tail renditions and regenerating on demand."),
                   ("Tier-by-popularity",
                    "Hot top-1% tracks: all renditions kept warm in CDN. Mid tier: only mid-bitrate "
                    "Vorbis + AAC kept warm; high-bitrate JIT-transcoded on first request. Cold "
                    "tail: only Vorbis 160 kept warm; everything else regenerated from master."),
                   ("Loudness normalisation",
                    "Each rendition stores ReplayGain-style loudness metadata so the client can "
                    "level-match across the catalog without re-encoding."),
               ],
               diagram=(
                   "graph LR\n"
                   "  M[FLAC Master] --> T[Transcode]\n"
                   "  T --> V96[Vorbis 96]\n"
                   "  T --> V160[Vorbis 160]\n"
                   "  T --> V320[Vorbis 320 Premium]\n"
                   "  T --> A128[AAC 128]\n"
                   "  T --> A256[AAC 256 Premium]\n"
                   "  V96 & V160 & V320 & A128 & A256 --> CDN\n"
               )),
        _topic("playback-range-requests",
               "HTTP Range Requests: Why Spotify Skips HLS for VOD Audio",
               "On-demand audio is the canonical workload where range requests beat segmented "
               "streaming. Understanding the trade is a senior signal in any audio-platform design.",
               [
                   ("First-buffer math",
                    "320 kbps Vorbis = 40 KB/s. A 64 KB initial range gives ~1.5s of audio — "
                    "enough to start playback while the next ranges fly in. Total TTFA is one "
                    "round trip + first-byte time ≈ 100–200 ms on a healthy CDN."),
                   ("Seek behaviour",
                    "Client knows duration_ms and file size; seek_byte = file_size × seek_fraction "
                    "(approximate; Vorbis page boundaries make it exact within a few ms). Fresh "
                    "Range header pulls the new bytes; player reattaches decoder state."),
                   ("Why HLS hurts here",
                    "HLS needs a manifest GET first (extra RTT), then segment GETs. Each seek may "
                    "require a manifest re-evaluation if it expired. Audio segment durations "
                    "(typically 6–10s) limit seek granularity. None of this pays off because audio "
                    "files are small enough that mid-stream bitrate switching is rarely needed."),
                   ("CDN cache simplicity",
                    "One URL per (track, rendition) — perfect for long-TTL immutable caching. "
                    "CDN config: 1-year TTL, content-addressed paths, no signing on free-tier "
                    "tracks. DRM tracks are encrypted at rest so they remain safely cacheable."),
                   ("Where HLS still belongs",
                    "Live radio, live podcasts, and live concerts use LL-HLS with CMAF chunks — "
                    "those are streaming workloads where time-shifting and ABR over time matter."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant Player\n"
                   "  participant CDN\n"
                   "  Player->>CDN: GET audio Range: 0-65535\n"
                   "  CDN-->>Player: bytes (200 OK -> 206 Partial)\n"
                   "  Player->>Player: start playback @ 150ms\n"
                   "  loop sequential\n"
                   "    Player->>CDN: Range: N-M\n"
                   "    CDN-->>Player: bytes\n"
                   "  end\n"
                   "  Note over Player: seek\n"
                   "  Player->>CDN: Range: seekByte-...\n"
                   "  CDN-->>Player: bytes\n"
               )),
        _topic("recommendations-portfolio",
               "Recommendations Portfolio: CF + Content-Based + Session",
               "No single model produces Spotify-quality recommendations. The interview-grade "
               "answer names all three pillars and explains where each shines.",
               [
                   ("Collaborative filtering (matrix factorisation)",
                    "Weekly ALS or implicit-feedback MF on (user, track, listen_count) → user "
                    "embeddings + item embeddings. Strong on hot users + hot tracks; the workhorse "
                    "for Discover Weekly and 'fans also like'."),
                   ("Content-based audio embedding",
                    "CNN over mel-spectrograms produces a 128-d embedding per track at ingest. "
                    "Solves cold-start: a brand-new release with zero plays is still placeable in "
                    "the embedding space and similar to known tracks."),
                   ("Session/sequence model",
                    "Transformer trained on listening sessions predicts next-best-track. Drives "
                    "queue auto-extend (radio mode) and Daily Mix freshness."),
                   ("Online ranker",
                    "Candidates from all three pillars (~500) are passed to a gradient-boosted-tree "
                    "or DNN ranker that scores against per-request features (time-of-day, device, "
                    "recent skips, locale) using a feature store. p95 < 80 ms."),
                   ("Diversity and fairness constraints",
                    "Final selection enforces artist quotas, genre spread, new-vs-familiar mix, "
                    "and emerging-artist exposure floors — hard constraints applied after ranking."),
                   ("Feedback loop",
                    "Skip-within-30s, save-to-library, repeat-play within 7 days are the labels "
                    "that retrain the ranker. Negative signals (skip) carry more weight per event "
                    "than positive (save) because skip is denser."),
               ],
               diagram=(
                   "graph TD\n"
                   "  CF[Collab Filtering MF] --> CG[Candidate Pool]\n"
                   "  CB[Content Embedding] --> CG\n"
                   "  SQ[Session Transformer] --> CG\n"
                   "  CG --> R[Online Ranker]\n"
                   "  R --> D[Diversity Filter]\n"
                   "  D --> UI[Home / Daily Mix / Discover]\n"
                   "  UI --> L[Skip / Save / Replay]\n"
                   "  L --> CF & CB & SQ\n"
               )),
        _topic("discover-weekly-batch",
               "Discover Weekly: A Weekly Spark Batch Pipeline",
               "Discover Weekly is the canonical 'product is a batch job' feature. The Monday "
               "drop ritual matters more than freshness — the architecture matches.",
               [
                   ("Why batch, not real-time",
                    "Discover Weekly is a 30-track personalised playlist updated weekly. Real-time "
                    "would (a) waste compute scoring the full long tail per request, (b) lose the "
                    "Monday-morning product ritual, and (c) require keeping all candidate models "
                    "hot. Batch lets us run heavier models offline."),
                   ("Pipeline stages",
                    "Step 1 (Sun 18:00 UTC): refresh user/track embeddings via ALS over last-90d "
                    "listening matrix. Step 2: per premium user, generate ~500 candidates from CF "
                    "neighbours + content-based 'similar to recently saved'. Step 3: rerank with a "
                    "personalisation model trained on prior-week labels. Step 4: top 30 with "
                    "artist/genre diversity quotas; serialised to per-user playlist row."),
                   ("Staggered drop by timezone",
                    "Playlist swap happens Monday 00:00 in user's local time. Writer schedules "
                    "spread the global swap across 24 hours, smoothing CDN warm-up + DB write "
                    "load. UTC+13 sees their Monday hours before US East Coast."),
                   ("Fallback for new users",
                    "Users with < 30 days history get a content-based bootstrap: top tracks from "
                    "their declared favourite genres + onboarding picks. Switches to full CF "
                    "personalisation after 30+ days listening signal."),
                   ("Validation before drop",
                    "Quality gate: avg novelty score, artist quota check, no duplicate tracks "
                    "across users above threshold, model drift checks. If gate fails, ship "
                    "previous week's playlist (with banner) instead of a regression."),
               ],
               diagram=(
                   "graph LR\n"
                   "  H[Listening History 90d] --> ALS[Spark ALS]\n"
                   "  ALS --> Emb[User+Track Embeddings]\n"
                   "  Emb --> CG[Per-User Candidates ~500]\n"
                   "  CG --> RR[Reranker]\n"
                   "  RR --> Div[Diversity Filter -> 30]\n"
                   "  Div --> PW[Playlist Writer]\n"
                   "  PW --> TZ[Timezone-Staggered Swap]\n"
                   "  TZ --> Client\n"
               )),
        _topic("listening-history-kafka",
               "Listening History via Kafka: One Stream, Many Consumers",
               "Every play and skip is a fact that must reach play counts, royalties, and "
               "recommendations without coupling those consumers. Kafka is the spine.",
               [
                   ("Event schema",
                    "play_event { user_id, track_id, ts, played_ms, context (album/playlist/radio), "
                    "device, country, session_id }. Skip / seek / like as separate event types. "
                    "Schema-Registry-validated Avro for forward/backward compatibility."),
                   ("Partitioning by user_id",
                    "Preserves per-user order so session models see a consistent stream. ~256 "
                    "partitions per topic; replication factor 3."),
                   ("Stream consumer (Flink)",
                    "Increments per-track play counts and HLL for monthly_listeners. Updates "
                    "per-user recently-played for home page. Produces fraud-filtered events to a "
                    "downstream royalty-eligible topic."),
                   ("Batch consumer (Spark)",
                    "Daily archive in S3 from Kafka; source for Discover Weekly + royalty "
                    "settlement + analytics. Spark is the authoritative aggregator; Flink output "
                    "is reconciled against batch nightly."),
                   ("Zero-loss guarantees",
                    "Kafka retention 30d; S3 archive forever. Consumer offsets committed only "
                    "after batch write success. Royalty consumer is the strictest — at-least-once "
                    "delivery + idempotent dedup keys (event_id) at the sink."),
                   ("Anti-fraud filter inline",
                    "Rule + ML scoring filters obvious bots (UA anomalies, IP velocity, played_ms "
                    "= duration_ms exactly, 1000 plays/hour from a single account). Filtered "
                    "events are still archived for audit but excluded from royalty + chart."),
               ],
               diagram=(
                   "graph LR\n"
                   "  Client --> EC[Edge Collector]\n"
                   "  EC --> K[Kafka play_events]\n"
                   "  K --> F[Flink near-RT]\n"
                   "  K --> SA[S3 Archive]\n"
                   "  SA --> SP[Spark Batch]\n"
                   "  F --> Counts[(play_counts)]\n"
                   "  SP --> R[Royalty Engine]\n"
                   "  SP --> DW[Discover Weekly]\n"
                   "  F --> Rec[Recommendation Features]\n"
               )),
        _topic("offline-drm-widevine",
               "Offline Caching with Widevine: Encrypted Files + Persistent Licenses",
               "Premium offline is non-negotiable product UX. The architecture must keep audio "
               "playable on a plane while still honouring subscription state and revocation.",
               [
                   ("Encrypted at rest",
                    "Premium / label-mandated tracks are AES-128 CTR encrypted with a per-track "
                    "content key. Encrypted bytes are the same on CDN and on disk — no separate "
                    "offline pipeline."),
                   ("Persistent license issuance",
                    "On offline-pin, License Server issues a Widevine persistent license with TTL "
                    "(typically 30 days), bound to (user_id, device_id). License blob stored "
                    "alongside the file; the device CDM uses it to decrypt without re-contacting "
                    "the server."),
                   ("Proactive license refresh",
                    "Within 7 days of expiry, client refreshes whenever it has connectivity. "
                    "Refresh re-validates subscription state at the License Server. If "
                    "subscription cancelled, refresh denied; on next license expiry, playback "
                    "stops with a 'reconnect to keep listening' UX."),
                   ("Revocation latency cap",
                    "Subscription cancel sets an entitlement bit immediately. Devices online "
                    "within 24 hours see refresh denied; we accept up-to-license-TTL playback in "
                    "the worst case for users who go offline immediately after cancel."),
                   ("FairPlay equivalence on iOS",
                    "iOS uses FairPlay Streaming (FPS) instead of Widevine. License flow is "
                    "structurally identical (SPC → CKC) but the License Server issues FPS "
                    "licenses. Both CDMs honour persistent license + revocation semantics."),
                   ("Cache eviction",
                    "Client enforces 10K tracks per device cap; LRU eviction by last-played time. "
                    "User-pinned playlists override LRU. Eviction frees encrypted file + license."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant App\n"
                   "  participant Lic as License Server\n"
                   "  participant CDN\n"
                   "  App->>Lic: persistent license challenge\n"
                   "  Lic->>Lic: verify Premium + device\n"
                   "  Lic-->>App: persistent license (30d)\n"
                   "  App->>CDN: GET encrypted audio\n"
                   "  CDN-->>App: bytes (encrypted at rest)\n"
                   "  Note over App: offline playback OK\n"
                   "  App->>Lic: refresh (within 7d of expiry)\n"
                   "  alt Subscription active\n"
                   "    Lic-->>App: new license\n"
                   "  else Cancelled\n"
                   "    Lic-->>App: 403; offline disabled at expiry\n"
                   "  end\n"
               )),
        _topic("royalty-pipeline",
               "Royalty Pipeline: Per-Stream Payouts and Audit",
               "Spotify is fundamentally a payout machine. The royalty pipeline is its own "
               "first-class system — separate from analytics — because rights-holders audit it.",
               [
                   ("Qualified play definition",
                    "Industry standard: a stream counts for royalty if played_ms > 30,000. The "
                    "30s threshold is enforced in the client SDK before it emits the play event "
                    "to Kafka, then re-validated server-side."),
                   ("Daily aggregation",
                    "Spark daily job groups (track_id, country, period) → qualified_plays. "
                    "Country matters because per-stream rates vary by territory and rights "
                    "agreement."),
                   ("Rate calculation",
                    "Rights-holder contracts encode per-stream rate by territory + mechanical "
                    "vs publishing splits + minimum guarantees. Royalty engine joins aggregated "
                    "plays with contracts and outputs payout per (rights_holder, period)."),
                   ("Auditability",
                    "Every input fact (Kafka event) is archived in S3 forever. Auditors can "
                    "replay aggregation from raw events at any time and reconcile with output "
                    "settlement. Discrepancies trigger investigation."),
                   ("Idempotency",
                    "Every event has an event_id; sinks dedupe on it. Re-running a day's batch "
                    "(after fixes) produces the same output. Settlement files are versioned and "
                    "released only after sign-off."),
                   ("Error handling",
                    "Late-arriving events (offline play synced days later) are folded into a "
                    "next-period adjustment, not silently dropped. Bot-flagged events are "
                    "excluded but kept in the archive with a reason code."),
               ],
               diagram=(
                   "graph LR\n"
                   "  K[Kafka play_events] --> S3[S3 Archive forever]\n"
                   "  S3 --> SP[Spark Daily]\n"
                   "  SP --> Q[(qualified plays per track-country-day)]\n"
                   "  Q --> RE[Royalty Engine]\n"
                   "  RH[Rights-Holder Contracts] --> RE\n"
                   "  RE --> PO[Monthly Payout File]\n"
                   "  PO --> Audit\n"
               )),
    ],
)
