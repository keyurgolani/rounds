"""SD-GoogleMaps — Design Google Maps (map tiles + directions/routing + traffic).
Mirrors the schema/shape of SD_01 in sd_questions.py. Auto-discovered by
`sd_questions._load_more` because this module exposes `PAYLOAD`."""
from __future__ import annotations

from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design Google Maps",
    "Hard",
    "Design a planet-scale mapping platform that delivers four headline products: (1) interactive "
    "map rendering via pre-generated tiles at 20+ zoom levels, served globally from a CDN with sub-"
    "100ms latency; (2) geocoding (address -> lat/lng) and reverse geocoding (lat/lng -> address); "
    "(3) directions / routing on a continent-scale road graph with hundreds of millions of edges, "
    "supporting Dijkstra / A* and Contraction Hierarchies for millisecond response on cross-country "
    "queries; (4) real-time traffic — ingest probe pings from hundreds of millions of phones, fuse "
    "them into per-edge speed estimates, recompute ETAs, and reroute around congestion. Cover the "
    "tile pyramid (raster vs vector tiles, precompute vs render-on-demand), the tile cache + CDN "
    "story, the offline-map download path, geocoding indexes, the routing graph build pipeline, "
    "turn-by-turn instruction generation, alternative routes, indoor maps, Street View image "
    "storage and panorama indexing, and the POI database used by both search and the rendered map.",
    hints=[
        "Map tiles are precomputed at every zoom level (z, x, y) and cached aggressively — render-"
        "on-demand at request time would never hit latency budgets.",
        "Vector tiles ship the geometry + style metadata (kilobytes) and let the client style and "
        "rotate; raster tiles ship a pre-rendered PNG (tens of KB) and the server controls the "
        "look. Production maps now ship vector tiles to support smooth zoom and theming.",
        "Naive Dijkstra over a continent-scale graph (~200M edges) is seconds-per-query — "
        "Contraction Hierarchies precompute shortcuts so cross-country routes return in a few "
        "milliseconds.",
        "A* with a great-circle (haversine) heuristic prunes Dijkstra by ~10x and is the baseline "
        "for short / medium routes.",
        "Real-time traffic comes from anonymized probe pings — every Android / Google Maps device "
        "emits speed + position; pings are matched onto the road graph and aggregated per edge.",
        "ETA = sum of (edge_length / current_speed) along the chosen route + intersection delay; "
        "current_speed is a blend of historical (time-of-day, day-of-week) and live probe data.",
        "Tiles are immutable per (style_version, z, x, y, data_epoch) — that is what makes CDN "
        "caching trivially correct.",
        "Geocoding is fundamentally a search problem (address parser + ranked match), not a "
        "geometry problem.",
        "Street View is a panorama image store keyed by (lat, lng, heading) plus a connectivity "
        "graph telling the client which neighbour panoramas are reachable.",
    ],
    constraints=[
        "1B+ MAU; 100M+ concurrent active sessions at peak",
        "Map tile read p99 < 100ms (CDN-served)",
        "Routing p99 < 500ms for cross-country queries",
        "Probe ingest peak ~5-10M pings/sec globally",
        "Street View: tens of billions of panoramas, petabyte-scale image storage",
        "Road graph: ~200M edges (worldwide drivable), updated weekly from map-edits",
        "Offline maps: a single country pack must fit in ~1-3 GB on phone",
        "Tile pyramid: zoom 0 (whole world) -> zoom 22 (building level), 4^z tiles per level",
    ],
    req_func=[
        "Render an interactive map at any (lat, lng, zoom) — return tiles for the visible viewport",
        "Geocode an address string to (lat, lng) and reverse-geocode (lat, lng) to address + POI",
        "Compute a driving / walking / transit / cycling route between two or more waypoints",
        "Generate turn-by-turn instructions for the chosen route",
        "Provide alternative routes (typically 2-3) ranked by ETA, distance, simplicity",
        "Ingest live probe pings and surface per-edge speed estimates",
        "Recompute ETA and proactively reroute when traffic ahead degrades",
        "Search POIs by name / category, anchored at a viewport or radius",
        "Render Street View panoramas with smooth navigation between adjacent panoramas",
        "Render indoor maps for malls / airports / stations with floor selector",
        "Allow users to download a region for offline use (tiles + routing graph + POIs)",
    ],
    req_nonfunc=[
        "Tile read p99 < 100ms via CDN; cache hit ratio > 95%",
        "Routing p99 < 500ms for cross-country, < 100ms for short urban",
        "Probe ingest p99 < 200ms write; lossy is acceptable (next ping in seconds)",
        "Traffic freshness < 60s end-to-end",
        "Map data eventual consistency: edits via the map-editor pipeline propagate within hours",
        "Petabyte-scale durable storage for tiles, panoramas, road graph snapshots",
        "Globally distributed: multi-region with regional tile caches and routing replicas",
        "Privacy: probe pings anonymized; no raw user trajectory persisted long-term",
    ],
    estimation={
        "mau": "1B",
        "concurrent_peak": "~100M sessions",
        "tiles_per_session": "~30 tiles per pan/zoom; ~300/min for an active driver",
        "tile_qps_steady": "~5-10M tile reads/sec globally (mostly CDN)",
        "tile_qps_origin": "~50-200K tile reads/sec to origin (after CDN absorbs ~99%)",
        "tile_storage": "~50PB raw tiles across all zoom levels and styles (vector + raster)",
        "road_graph_edges": "~200M drivable edges worldwide",
        "routing_qps": "~100K routes/sec steady; 500K peak",
        "probe_pings_qps": "~5-10M pings/sec peak (rush hour, multiple metros)",
        "street_view_panoramas": "~tens of billions; petabytes of imagery",
        "geocode_qps": "~50-100K/sec",
    },
    endpoints=[
        {"method": "GET", "path": "/tiles/{style}/{z}/{x}/{y}.{fmt}",
         "description": "Fetch a map tile (vector .pbf or raster .png) at zoom z, column x, row y; "
                        "served via CDN; long-cache with style_version in path"},
        {"method": "GET", "path": "/geocode",
         "description": "Address string -> ranked list of (lat,lng, formatted_address)",
         "body": "?q=&country=&viewport_bias="},
        {"method": "GET", "path": "/reverse-geocode",
         "description": "(lat,lng) -> nearest address + POI",
         "body": "?lat=&lng="},
        {"method": "GET", "path": "/route",
         "description": "Compute route(s) between waypoints with traffic-aware ETA",
         "body": "?from=&to=&via=&mode=driving&alternatives=true&avoid=tolls,highways"},
        {"method": "POST", "path": "/probe/ping",
         "description": "Anonymized probe ping from a device",
         "body": "{anon_id, lat, lng, speed_mps, heading, accuracy_m, ts}"},
        {"method": "GET", "path": "/streetview/panorama",
         "description": "Fetch panorama metadata + image tiles near (lat,lng)",
         "body": "?lat=&lng=&heading="},
        {"method": "GET", "path": "/places/search",
         "description": "POI search anchored at viewport or radius",
         "body": "?q=&lat=&lng=&radius_m=&category="},
        {"method": "GET", "path": "/offline/region",
         "description": "Download a packaged offline region (tiles + sub-graph + POIs)",
         "body": "?bbox=&include=routing,tiles,places"},
    ],
    tables=[
        {"name": "tiles_meta",
         "columns": ["style VARCHAR(32)", "z TINYINT", "x INT", "y INT",
                     "data_epoch BIGINT", "blob_url TEXT", "etag VARCHAR(64)",
                     "size_bytes INT",
                     "PRIMARY KEY (style, z, x, y, data_epoch)"]},
        {"name": "road_edges",
         "columns": ["edge_id BIGINT PK", "from_node BIGINT", "to_node BIGINT",
                     "length_m INT", "free_flow_speed_mps FLOAT",
                     "road_class TINYINT", "oneway BOOL", "geometry GEOMETRY",
                     "country_code CHAR(2)", "graph_version BIGINT"]},
        {"name": "road_nodes",
         "columns": ["node_id BIGINT PK", "lat DOUBLE", "lng DOUBLE",
                     "intersection_kind TINYINT", "elevation_m FLOAT"]},
        {"name": "ch_shortcuts",
         "columns": ["shortcut_id BIGINT PK", "from_node BIGINT", "to_node BIGINT",
                     "weight FLOAT", "via_node BIGINT", "level INT",
                     "graph_version BIGINT"]},
        {"name": "edge_speeds_live",
         "columns": ["edge_id BIGINT PK", "current_speed_mps FLOAT",
                     "sample_count INT", "last_updated BIGINT"]},
        {"name": "edge_speeds_historical",
         "columns": ["edge_id BIGINT", "dow TINYINT", "hour TINYINT",
                     "p50_speed_mps FLOAT", "p90_speed_mps FLOAT",
                     "PRIMARY KEY (edge_id, dow, hour)"]},
        {"name": "geocode_index",
         "columns": ["doc_id BIGINT PK", "formatted_address TEXT",
                     "lat DOUBLE", "lng DOUBLE",
                     "country CHAR(2)", "admin1 VARCHAR(64)", "admin2 VARCHAR(64)",
                     "locality VARCHAR(128)", "postal VARCHAR(16)", "tokens TEXT"]},
        {"name": "places",
         "columns": ["place_id VARCHAR(64) PK", "name TEXT", "category VARCHAR(64)",
                     "lat DOUBLE", "lng DOUBLE", "s2_cell_id BIGINT",
                     "rating FLOAT", "review_count INT", "metadata JSON"]},
        {"name": "panoramas",
         "columns": ["pano_id VARCHAR(64) PK", "lat DOUBLE", "lng DOUBLE",
                     "captured_at DATE", "heading FLOAT", "tile_blob_root TEXT",
                     "neighbours JSON"]},
        {"name": "probe_pings_raw",
         "columns": ["ping_id BIGINT PK", "anon_id BINARY(16)", "lat DOUBLE",
                     "lng DOUBLE", "speed_mps FLOAT", "heading FLOAT",
                     "accuracy_m INT", "ts BIGINT"]},
    ],
    indexes=[
        "(style, z, x, y, data_epoch) on tiles_meta — primary tile lookup",
        "(from_node) and (to_node) on road_edges — graph traversal",
        "(country_code, road_class) on road_edges — region build / pruning",
        "(s2_cell_id) on places — geospatial place lookup",
        "(lat, lng) spatial / S2 index on panoramas — Street View nearest",
        "Inverted token index on geocode_index — address search",
        "(edge_id) on edge_speeds_live — fast per-edge lookup during routing",
    ],
    hld_desc=(
        "Four loosely coupled subsystems share a single canonical Map Data store: "
        "(1) Tile Service generates immutable vector + raster tiles in a batch pipeline keyed by "
        "(style, z, x, y, data_epoch); they live in object storage, fronted by a tiered CDN with "
        "near-100% hit rate. (2) Routing Service holds a sharded routing graph in RAM with "
        "Contraction Hierarchies precomputed weekly; queries do A* / bidirectional CH and pull "
        "live edge speeds from a separate hot store. (3) Traffic Pipeline ingests probe pings "
        "via a stateless ingestor -> Kafka -> map-matcher -> stream aggregator that updates "
        "edge_speeds_live and emits incident events. (4) Geocoder + Places + Street View ride a "
        "search-style stack: Elasticsearch-class inverted index for addresses and POIs, S2-cell "
        "index for spatial nearest, and an image blob store + panorama graph for Street View."
    ),
    hld_components=[
        {"name": "API Gateway", "role": "Auth, rate-limit, route to subsystem"},
        {"name": "Tile CDN", "role": "Globally distributed; absorbs >95% of tile reads"},
        {"name": "Tile Origin", "role": "Serves cache-miss tiles from object storage"},
        {"name": "Tile Build Pipeline", "role": "Batch render vector + raster tiles per data_epoch"},
        {"name": "Routing Service", "role": "A* / bidirectional CH on in-RAM graph; per-region shards"},
        {"name": "Routing Graph Builder", "role": "Weekly job: build CH shortcuts from road edges"},
        {"name": "Live Edge Speed Store", "role": "Per-edge current speed; consulted at query time"},
        {"name": "Probe Ingest", "role": "Stateless HTTP/UDP ingest, drop on overflow"},
        {"name": "Map Matcher", "role": "Snap raw GPS pings onto road graph edges"},
        {"name": "Traffic Aggregator", "role": "Stream processor; per-edge speed roll-ups"},
        {"name": "Geocoder Service", "role": "Address parse + ranked search"},
        {"name": "Places Service", "role": "POI search anchored at viewport / radius"},
        {"name": "Street View Service", "role": "Panorama metadata + neighbour graph"},
        {"name": "Image Blob Store", "role": "Petabyte object store for panoramas + tiles"},
        {"name": "Map Data Store", "role": "Canonical road graph + POIs + addresses (RDB + S3)"},
    ],
    detailed_design={
        "tile_pyramid": (
            "World is recursively divided into a quadtree. Zoom 0 = 1 tile covering the whole "
            "world; zoom z has 4^z tiles addressed by (x, y). Standard scheme is the Web Mercator "
            "/ Slippy Map convention used everywhere from OSM to Google. Each tile is rendered at "
            "256x256 (raster) or as a Mapbox Vector Tile .pbf containing layers (roads, water, "
            "buildings, labels). A tile is uniquely identified by (style, z, x, y, data_epoch) — "
            "the data_epoch in the path makes every (re)build a fresh URL, so the CDN can cache "
            "for years. Style upgrades bump style_version, also part of the path."
        ),
        "vector_vs_raster": (
            "Vector tiles ship geometry + attributes (typically 5-50 KB) and the client renders "
            "them with WebGL using a style sheet. This makes smooth zoom (intermediate scaling), "
            "rotation, theming (dark mode, satellite labels), and runtime style edits possible "
            "without re-fetching. Raster tiles are pre-rendered PNGs (10-100 KB) that are simpler "
            "to serve and easier on low-end devices but bloat storage (one set per style) and "
            "lose interactivity. Production Google Maps uses vector tiles for the base map and "
            "raster tiles for satellite/aerial imagery (where vector makes no sense)."
        ),
        "tile_cache_and_cdn": (
            "Tiles are immutable per data_epoch and style_version, so they are perfect CDN "
            "candidates. Three tiers: (a) browser HTTP cache (max-age=1y, immutable); (b) edge "
            "POP CDN with regional fill from origin; (c) origin reads from object storage. "
            "Cache key includes the entire path so style/data revs do not need explicit "
            "invalidation. Hot tiles (city centres, country centroids, navigation along major "
            "highways) are pre-warmed at edge. We also pre-render only the tiles people actually "
            "ask for at deep zoom levels (>17) — the long tail of zoom-22 tiles in the Sahara is "
            "rendered on-demand and cached opportunistically."
        ),
        "tile_build_pipeline": (
            "Map data edits flow into a canonical store. A batch pipeline (think MapReduce / "
            "Beam) reads the map data, simplifies geometry per zoom (Douglas-Peucker), assigns "
            "labels with collision-aware placement, and emits vector tiles. Output is partitioned "
            "by (style, z, x, y) and uploaded to object storage. A new data_epoch is published "
            "atomically by flipping a manifest pointer; clients pick up the new epoch on next "
            "session start. Incremental builds re-render only tiles whose underlying geometry "
            "or labels changed."
        ),
        "geocoding": (
            "Geocoding is search, not geometry. A parser breaks the input into components "
            "(number, street, locality, admin1, country, postal). The index is an Elasticsearch-"
            "class inverted index over normalized address tokens with per-component weighting. "
            "Ranking blends textual match score, viewport bias (closer to the user wins), prior "
            "popularity, and disambiguation against ambiguous names ('Springfield'). Reverse "
            "geocoding does an S2-cell nearest-neighbour lookup over the address index plus a "
            "snap to the nearest road / building. Geocoding is fronted by an aggressive query "
            "cache because most distinct queries repeat."
        ),
        "routing_graph": (
            "Road edges and nodes are loaded into a directed weighted graph held in RAM, "
            "sharded by metro / region. Each edge stores (from, to, length, road_class, "
            "free-flow speed, oneway, allowed-modes). The graph is rebuilt weekly from the "
            "canonical map data; a graph_version label keeps queries consistent. For "
            "transit / walking / cycling we maintain mode-specific overlays."
        ),
        "routing_algorithms": (
            "Three tiers: (1) Dijkstra is the textbook baseline — correct but slow (seconds on a "
            "continent). (2) A* with a haversine heuristic prunes ~10x and is the default for "
            "short / medium routes. (3) Contraction Hierarchies (CH) precompute shortcut edges "
            "so a bidirectional Dijkstra on the contracted graph returns cross-country routes in "
            "a few milliseconds. Customizable CH (CCH) allows per-query weight changes (e.g., "
            "live traffic) without rebuilding the hierarchy. Production routers use CH + A* + "
            "ALT (landmark heuristics) in combination depending on query length and freshness "
            "requirements."
        ),
        "turn_by_turn": (
            "After the path is found, instruction generation walks the edge sequence and emits "
            "maneuver objects (continue, turn-left, take-exit, merge) keyed off intersection "
            "kind, edge angle change, and signage attributes attached to nodes. Voice prompts "
            "are templated per locale ('In 200 meters, turn left onto Elm Street'). Lane "
            "guidance is derived from per-edge lane attributes. Re-route is triggered when the "
            "device drifts off the path or when downstream traffic worsens the ETA past a "
            "threshold."
        ),
        "alternative_routes": (
            "Alternatives are generated by penalty-based re-runs: after the primary route is "
            "found, edges along it are penalized and the search re-run; results are kept only "
            "if they are sufficiently dissimilar (Jaccard on edge set < 0.7) and within X% of "
            "the optimum. Plateau-based and Pareto-frontier methods (ETA vs simplicity vs "
            "tolls) also exist. We typically return 2-3 alternatives ranked by user-visible "
            "trade-offs."
        ),
        "real_time_traffic": (
            "Probe pings are anonymized and dropped from devices via a stateless UDP/HTTP "
            "ingestor that buffers to Kafka. A map-matcher snaps each ping to the most likely "
            "edge using a Hidden Markov Model that considers prior edge, ping speed, and road "
            "geometry. A stream aggregator (Flink / Dataflow) maintains per-edge windowed "
            "median speed (1m, 5m, 15m). edge_speeds_live is updated every few seconds. "
            "Routing fuses live + historical: weight w * live_speed + (1-w) * historical_speed, "
            "with w decaying as the route extends past the visible-traffic horizon (~30 min)."
        ),
        "eta_estimation": (
            "Per-edge time = length / blended_speed + intersection_delay (signal vs stop vs "
            "yield). Total ETA = sum of per-edge times + a calibration term learned from "
            "ground-truth completed trips. Confidence intervals come from probe ping variance. "
            "ETAs are recomputed every ~30s during navigation; if downstream traffic degrades "
            "past a threshold, the device proactively offers a reroute."
        ),
        "indoor_maps": (
            "Indoor maps are a separate vector tile layer keyed by (building_id, floor). "
            "Triggered when the user is inside a known venue; switches the rendered tile set "
            "and exposes a floor selector. Indoor routing uses the same routing service over a "
            "separate sub-graph (corridors, escalators, elevators)."
        ),
        "street_view": (
            "Each panorama is stored as a multi-resolution image pyramid (think the same tile "
            "trick) in object storage; metadata lives in a panoramas table indexed by S2 cell. "
            "A neighbour graph stores 'from this pano, you can step forward / left / right to "
            "this pano-id.' Client requests nearest panorama by (lat,lng), gets metadata + the "
            "set of low-res tiles to render the cube map, and lazily fetches high-res tiles for "
            "the heading the user is looking at. Privacy blurring (faces, plates) runs in the "
            "ingest pipeline."
        ),
        "poi_database": (
            "POIs (places) live in a sharded store; each POI has a stable place_id, geometry, "
            "category, attributes, and review aggregates. Indexed by S2 cell for spatial "
            "search and by an inverted index for name/keyword search. Search results blend "
            "spatial proximity, query relevance, popularity, and personalization."
        ),
        "offline_maps": (
            "User selects a bbox / region; a packager job assembles a self-contained pack: "
            "vector tiles for the bbox at zooms 6-16, the routing sub-graph + CH shortcuts "
            "scoped to the bbox, and the POI subset. Pack is signed and downloaded to the "
            "device. Routing on-device uses the same CH algorithm with a smaller graph; "
            "traffic is unavailable offline so historical speeds are used."
        ),
        "sharding_strategy": (
            "Tiles: object storage natively sharded by key — no extra logic. Routing graph: "
            "sharded by metro / country with overlap in border regions; cross-shard queries "
            "use a thin coordinator. Probe pings: hash by anon_id at ingest, then re-shard "
            "by edge_id at the aggregator. Geocode + Places: shard by S2 cell. Street View: "
            "shard panoramas by S2 cell (image blobs are the bulk and live in object storage)."
        ),
        "slo_contract": (
            "Tile read p99<100ms (CDN), <500ms origin. Route p99<500ms cross-country, <100ms "
            "urban. Probe ingest p99<200ms. Traffic freshness p99<60s. Geocode p99<200ms."
        ),
    },
    trade_offs=[
        {"option": "Vector tiles vs Raster tiles",
         "for_vector": "Smooth zoom, runtime theming, smaller per-tile, single render path",
         "for_raster": "Simpler client, works on low-end GPUs, cheap to serve",
         "recommendation": "Vector for base map; raster for satellite/aerial; hybrid in production."},
        {"option": "Render tiles on-demand vs precompute pyramid",
         "for_on_demand": "No storage cost for cold tiles, instant style changes",
         "for_precompute": "p99<100ms via CDN, no render compute on hot path",
         "recommendation": "Precompute up to zoom 17 for populated areas; on-demand + cache for the long tail."},
        {"option": "Dijkstra vs A* vs Contraction Hierarchies",
         "for_dijkstra": "Simple, no preprocessing, optimal",
         "for_astar": "10x faster than Dijkstra for point-to-point, no preprocessing",
         "for_ch": "Cross-country in a few ms, but rebuilds when the graph changes",
         "recommendation": "CH (or CCH) for primary routing + A* for short queries / when graph dirty."},
        {"option": "Live traffic only vs Live + Historical blend",
         "for_live": "Reflects current state",
         "for_blend": "Robust when probe density is sparse; smoothes spurious dips",
         "recommendation": "Blend with weight that decays past the visible-traffic horizon."},
        {"option": "Per-anon-id sharding vs Per-edge sharding for probe pipeline",
         "for_anon": "Trivial at ingest, rate limit per device",
         "for_edge": "Aggregations are single-shard",
         "recommendation": "Anon at ingest -> re-shard to edge at the aggregator."},
        {"option": "Eager invalidation vs Epoch-in-URL for tile cache",
         "for_eager": "Always fresh",
         "for_epoch": "CDN-friendly; immutable URLs",
         "recommendation": "Epoch-in-URL — immutable tiles are the whole reason CDNs work here."},
    ],
    tips=[
        "Lead with the four subsystems: tiles, geocoding, routing, traffic. Drawing them as "
        "loosely coupled is the senior signal.",
        "Say 'tiles are immutable per (style, z, x, y, data_epoch)' early — it makes every "
        "caching question downstream trivial.",
        "Name the algorithms: Dijkstra / A* / Contraction Hierarchies / CCH / ALT. Interviewers "
        "want to know you know the landscape.",
        "Always pair CH with 'rebuilt weekly' or 'CCH for live weight updates' — naive CH cannot "
        "absorb live traffic.",
        "Map matching is an HMM over candidate edges, not a nearest-edge snap.",
        "Probe ingest is fire-and-forget at p99<200ms — losses are fine, the next ping is in "
        "seconds.",
        "Vector vs raster trade-off should be presented as 'both, for different layers.'",
        "Street View is a tile pyramid in disguise plus a panorama neighbour graph.",
        "ETA = blend of historical + live, not pure live.",
    ],
    thought_process=[
        "1. Clarify scope: tiles + geocoding + routing + traffic + Street View + POI search + offline.",
        "2. Estimate: 1B MAU, 5-10M tile QPS, 100K route QPS, 5-10M probe pings/sec, ~200M road edges.",
        "3. Tiles: precompute the pyramid in vector + raster, immutable URL, CDN absorbs >95%.",
        "4. Vector for base map (smooth zoom, theming) + raster for satellite imagery.",
        "5. Routing graph in RAM, sharded by region; rebuild CH weekly.",
        "6. Routing query: bidirectional CH + A* fallback; consult live edge speeds.",
        "7. Traffic: probe ingest -> Kafka -> HMM map-match -> Flink per-edge windowed median.",
        "8. ETA = blend of live + historical; reroute when downstream worsens past threshold.",
        "9. Geocoding = inverted-index search + viewport bias + S2 nearest for reverse.",
        "10. Street View = panorama metadata + image pyramid + neighbour graph.",
        "11. Indoor = separate tile layer + sub-graph for indoor routing.",
        "12. Offline = bbox-scoped pack of tiles + sub-graph + POIs, signed and downloaded.",
    ],
    tags=["maps", "tiles", "routing", "graph", "traffic", "cdn", "geospatial"],
    arch_nodes=[
        {"id": "client", "label": "Client (App / Web)", "type": "client"},
        {"id": "lb", "label": "API Gateway", "type": "lb"},
        {"id": "cdn", "label": "Tile CDN", "type": "cache"},
        {"id": "tile_origin", "label": "Tile Origin", "type": "server"},
        {"id": "tile_build", "label": "Tile Build Pipeline", "type": "service"},
        {"id": "blob", "label": "Object Storage (tiles + panoramas)", "type": "database"},
        {"id": "route", "label": "Routing Service (CH + A*)", "type": "server"},
        {"id": "graph_build", "label": "Routing Graph Builder", "type": "service"},
        {"id": "live_speed", "label": "Live Edge Speed Store", "type": "cache"},
        {"id": "probe_in", "label": "Probe Ingest", "type": "server"},
        {"id": "kafka", "label": "Kafka", "type": "queue"},
        {"id": "matcher", "label": "Map Matcher (HMM)", "type": "service"},
        {"id": "agg", "label": "Traffic Aggregator (Flink)", "type": "service"},
        {"id": "geo", "label": "Geocoder", "type": "server"},
        {"id": "places", "label": "Places Service", "type": "server"},
        {"id": "sv", "label": "Street View Service", "type": "server"},
        {"id": "mapdata", "label": "Map Data Store", "type": "database"},
    ],
    arch_edges=[
        {"source": "client", "target": "lb"},
        {"source": "client", "target": "cdn", "label": "tile fetch"},
        {"source": "cdn", "target": "tile_origin", "label": "miss"},
        {"source": "tile_origin", "target": "blob", "label": "read"},
        {"source": "tile_build", "target": "blob", "label": "write"},
        {"source": "tile_build", "target": "mapdata", "label": "read"},
        {"source": "lb", "target": "route", "label": "/route"},
        {"source": "lb", "target": "geo", "label": "/geocode"},
        {"source": "lb", "target": "places", "label": "/places"},
        {"source": "lb", "target": "sv", "label": "/streetview"},
        {"source": "lb", "target": "probe_in", "label": "/probe/ping"},
        {"source": "route", "target": "live_speed", "label": "edge speeds"},
        {"source": "route", "target": "graph_build", "label": "graph snapshot"},
        {"source": "graph_build", "target": "mapdata", "label": "edges + nodes"},
        {"source": "probe_in", "target": "kafka"},
        {"source": "kafka", "target": "matcher"},
        {"source": "matcher", "target": "agg", "label": "edge events"},
        {"source": "agg", "target": "live_speed", "label": "current speed"},
        {"source": "geo", "target": "mapdata"},
        {"source": "places", "target": "mapdata"},
        {"source": "sv", "target": "blob", "label": "panorama tiles"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant U as App\n"
        "  participant API\n"
        "  participant CDN\n"
        "  participant R as Routing\n"
        "  participant LS as Live Speeds\n"
        "  participant P as Probe Ingest\n"
        "  participant K as Kafka\n"
        "  participant F as Flink Aggregator\n"
        "  U->>CDN: GET /tiles/v9/14/2620/6334.pbf\n"
        "  CDN-->>U: tile (cached)\n"
        "  U->>API: GET /route?from=A&to=B\n"
        "  API->>R: route request\n"
        "  R->>LS: fetch live edge speeds\n"
        "  R->>R: bidirectional CH + A*\n"
        "  R-->>U: route + ETA + alternatives\n"
        "  U->>P: POST /probe/ping (every 5s)\n"
        "  P->>K: enqueue\n"
        "  K->>F: consume + map-match (HMM)\n"
        "  F->>LS: update edge speed\n"
        "  Note over R,LS: next /route picks up new traffic"
    ),
    er_diagram=(
        "erDiagram\n"
        "  ROAD_NODE ||--o{ ROAD_EDGE : connects\n"
        "  ROAD_EDGE ||--o{ EDGE_SPEED_LIVE : has\n"
        "  ROAD_EDGE ||--o{ EDGE_SPEED_HIST : has\n"
        "  ROAD_EDGE ||--o{ CH_SHORTCUT : contracts\n"
        "  PLACE ||--o{ REVIEW : has\n"
        "  PANORAMA ||--o{ PANORAMA : neighbours\n"
        "  ROAD_EDGE { bigint edge_id\n bigint from_node\n bigint to_node\n int length_m\n float free_flow_speed }\n"
        "  PLACE { string place_id\n string name\n string category\n bigint s2_cell }\n"
        "  PANORAMA { string pano_id\n double lat\n double lng\n string tile_blob_root }"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B[Four subsystems: tiles, routing, traffic, search]\n"
        "  B --> C[Tiles: precompute pyramid + CDN]\n"
        "  C --> D[Vector base + raster satellite]\n"
        "  B --> E[Routing: in-RAM graph, CH precomputed]\n"
        "  E --> F[Bidirectional CH + A* fallback]\n"
        "  F --> G[Consult live edge speeds]\n"
        "  B --> H[Traffic: probe ingest -> Kafka -> HMM match -> Flink]\n"
        "  H --> I[edge_speeds_live updated every few s]\n"
        "  B --> J[Geocode = search + viewport bias]\n"
        "  B --> K[Street View = panorama pyramid + neighbour graph]"
    ),
    tradeoff_title="Routing algorithm: Dijkstra vs A* vs Contraction Hierarchies vs CCH",
    tradeoff_options=[
        {"label": "Dijkstra",
         "description": "Textbook shortest-path on the live weighted graph.",
         "pros": ["Trivial to implement", "No preprocessing", "Always optimal",
                  "Tolerates arbitrary weight changes"],
         "cons": ["Seconds per query on continent-scale graphs",
                  "Scales linearly with edge count"]},
        {"label": "A* with haversine heuristic",
         "description": "Best-first Dijkstra guided by great-circle distance to target.",
         "pros": ["~10x faster than Dijkstra for point-to-point",
                  "No preprocessing", "Handles dynamic weights"],
         "cons": ["Still too slow for cross-country in real time",
                  "Heuristic must be admissible — degrades for transit / time-dependent graphs"]},
        {"label": "Contraction Hierarchies (CH)",
         "description": "Precompute shortcut edges by contracting nodes in importance order; "
                        "query is bidirectional Dijkstra on the contracted graph.",
         "pros": ["Cross-country routes in a few ms",
                  "Memory-efficient",
                  "Industry standard at planet scale"],
         "cons": ["Preprocessing takes hours and assumes static weights",
                  "Live traffic changes cannot directly mutate the hierarchy"]},
        {"label": "Customizable CH (CCH)",
         "description": "CH variant that separates topology from weights; weight changes "
                        "(e.g., live traffic) refresh in seconds without re-contracting.",
         "pros": ["Same query speed as CH", "Live traffic-friendly",
                  "Used in production by mapping vendors"],
         "cons": ["More complex preprocessing", "Extra memory for the separator hierarchy"]},
    ],
    tradeoff_rec=(
        "CCH for primary routing (planet-scale + live traffic) + A* fallback for short queries "
        "or when the graph snapshot is in flux. Plain Dijkstra is reserved for "
        "small / specialised sub-graphs (indoor, walking inside a campus)."
    ),
    senior_topics=[
        _topic("tile-pyramid",
               "The Tile Pyramid: Web Mercator, Quadtree Addressing, and Why Precompute",
               "The map is a quadtree where each zoom level has 4x the tiles of the previous. "
               "Tiles are immutable per data_epoch, which is why CDNs cache them at near-100% "
               "hit rate.",
               [
                   ("Web Mercator + Slippy Map",
                    "Lat/lng is projected to Web Mercator; the world is then a unit square. At "
                    "zoom z, that square is split into 2^z by 2^z tiles addressed by (x, y). "
                    "This is the same scheme used by Google, Apple, OSM, Mapbox — the universal "
                    "tile language."),
                   ("Why precompute",
                    "At 100M concurrent sessions and ~30 tiles per pan, render-on-demand would "
                    "burn render farms continuously. Precomputed tiles in object storage cost a "
                    "few dollars per terabyte-month and serve at CDN latency."),
                   ("Cache key = full path",
                    "Tile URL includes style_version, z, x, y, and data_epoch. A new build mints "
                    "new URLs; the old ones can age out naturally. No 'cache invalidation' "
                    "problem."),
                   ("Long-tail strategy",
                    "Zoom 17+ in unpopulated regions are rendered on-demand and cached "
                    "opportunistically — full precompute would waste petabytes."),
                   ("Storage budget",
                    "~50 PB across all styles and zoom levels is typical; raster doubles this "
                    "per supported style."),
               ],
               diagram=(
                   "graph TD\n"
                   "  Z0[Zoom 0: 1 tile] --> Z1[Zoom 1: 4 tiles]\n"
                   "  Z1 --> Z2[Zoom 2: 16 tiles]\n"
                   "  Z2 --> Zk[... Zoom z: 4^z tiles]\n"
                   "  Zk --> S[Object Storage]\n"
                   "  S --> CDN\n"
                   "  CDN --> Client"
               )),
        _topic("contraction-hierarchies",
               "Contraction Hierarchies for Continent-Scale Routing",
               "Plain Dijkstra is too slow on a 200M-edge graph. CH precomputes shortcut edges "
               "by contracting nodes in order of importance; queries become bidirectional "
               "Dijkstra on the much smaller contracted graph and finish in milliseconds.",
               [
                   ("Why Dijkstra fails at scale",
                    "Dijkstra explores edges proportional to graph size. A coast-to-coast US "
                    "query touches tens of millions of edges; even with A* the constant factor "
                    "is too high for a sub-100ms p99."),
                   ("Node contraction",
                    "Nodes are contracted in increasing importance order (degree, betweenness, "
                    "edge difference). Contracting a node v means: for every pair (u, w) of "
                    "neighbours where the shortest path u->v->w is unique, add a shortcut edge "
                    "u->w with weight = sum."),
                   ("Bidirectional query",
                    "Forward search from source only follows edges that go up the hierarchy; "
                    "backward search from target does the same in reverse. They meet in the "
                    "middle. Result is provably equal to true shortest path on the original "
                    "graph."),
                   ("Live traffic problem",
                    "If edge weights change (live traffic), the precomputed shortcuts may no "
                    "longer be optimal. Solutions: (a) CCH separates topology from weights — "
                    "weight changes refresh the metric in seconds; (b) blend live traffic in "
                    "as a query-time penalty bounded by an upper-envelope assumption; (c) only "
                    "use CH for the long-haul portion of the route, switch to A* for the "
                    "remaining urban miles where live traffic dominates."),
                   ("Production pattern",
                    "CCH built weekly; live edge speeds folded in via metric refresh every few "
                    "minutes. Query path: bidirectional CCH for the long middle of the route + "
                    "A* over the urban first/last mile."),
               ],
               diagram=(
                   "graph TD\n"
                   "  A[Original graph: 200M edges] --> B[Order nodes by importance]\n"
                   "  B --> C[Contract: insert shortcuts]\n"
                   "  C --> D[CH graph + shortcuts]\n"
                   "  D --> E[Query: bidirectional Dijkstra]\n"
                   "  E --> F[Path in a few ms]\n"
                   "  W[Live edge speeds] --> M[CCH metric refresh]\n"
                   "  M --> E"
               )),
        _topic("traffic-pipeline",
               "Real-Time Traffic: Probe Ingest -> Map-Match -> Per-Edge Speed",
               "Live traffic is built from anonymised probe pings emitted by hundreds of "
               "millions of devices. Pings are snapped to road edges via a Hidden Markov Model "
               "and aggregated into per-edge windowed median speed.",
               [
                   ("Probe ingest",
                    "Stateless ingestor accepts UDP/HTTPS pings ({anon_id, lat, lng, speed, "
                    "heading, accuracy, ts}). At 5-10M pings/sec peak, drops on overflow are "
                    "fine — the next ping is in seconds. Anonymisation strips identifiers; "
                    "trajectories are not retained long-term."),
                   ("Map matching is HMM, not nearest snap",
                    "Naive 'snap to nearest edge' fails at parallel roads (highway + service "
                    "road) and intersections. HMM treats the true edge as a hidden state; "
                    "emission probability is GPS error model; transition probability favours "
                    "edges reachable from the previous edge along the ping cadence. Viterbi "
                    "decode produces the most likely edge sequence."),
                   ("Streaming aggregation",
                    "Flink / Dataflow keeps a tumbling-or-sliding window per edge_id; output is "
                    "(edge_id, p50_speed, p10_speed, count) every few seconds. Outputs land in "
                    "edge_speeds_live (in-memory KV)."),
                   ("Live + historical blend",
                    "ETA uses w * live + (1-w) * historical, with w = 1 inside a horizon (~30 "
                    "min ahead) and decaying past it because we cannot see traffic that far "
                    "out. Sparse-probe edges fall back to historical."),
                   ("Incident detection",
                    "A sudden drop below 30% of the historical p50 with sustained low sample "
                    "speed triggers an incident event — surfaced as a slowdown / accident on "
                    "the map and used to recompute ETAs aggressively."),
                   ("Privacy",
                    "Pings are aggregated; raw user trajectories are not persisted past short "
                    "buffers. Aggregates are k-anonymous — no edge update is published unless "
                    "supported by enough independent devices."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant D as Device\n"
                   "  participant I as Probe Ingest\n"
                   "  participant K as Kafka\n"
                   "  participant M as HMM Map-Matcher\n"
                   "  participant F as Flink\n"
                   "  participant L as Live Speeds\n"
                   "  participant R as Routing\n"
                   "  D->>I: ping (lat,lng,v,t)\n"
                   "  I->>K: enqueue\n"
                   "  K->>M: consume\n"
                   "  M->>M: Viterbi over candidate edges\n"
                   "  M->>F: (edge_id, speed, ts)\n"
                   "  F->>L: update windowed median\n"
                   "  R->>L: read at query time"
               )),
        _topic("street-view",
               "Street View: Panorama Pyramid + Neighbour Graph",
               "Street View is conceptually a tile pyramid wrapped on a sphere, plus a graph "
               "telling you which panorama you can step into next.",
               [
                   ("Panorama as image pyramid",
                    "Each panorama is a cube-mapped or equirectangular image stored as a multi-"
                    "resolution pyramid. The client renders the cube map, swapping in higher "
                    "resolution tiles as the user looks closer."),
                   ("Spatial index",
                    "Panoramas are indexed by S2 cell; nearest-panorama queries take the user's "
                    "(lat,lng) and return the closest panorama plus its metadata."),
                   ("Neighbour graph",
                    "Each panorama stores edges to adjacent panoramas {forward, back, side "
                    "streets}. Stepping forward in the UI is a graph traversal, not a "
                    "geographic search."),
                   ("Image storage",
                    "Petabyte-scale object storage with hot tier for popular panoramas (city "
                    "centres) and cold tier for rural / historical."),
                   ("Privacy pipeline",
                    "Faces and license plates are blurred at ingest using a CV pipeline; "
                    "takedown requests re-process individual panoramas asynchronously."),
                   ("Time travel",
                    "Multiple panoramas can exist at the same (lat,lng) captured at different "
                    "dates; the UI exposes a date selector. Default surface is most recent."),
               ]),
        _topic("vector-vs-raster",
               "Vector Tiles vs Raster Tiles: Why Production Maps Use Both",
               "Vector tiles ship geometry + attributes and let the client render with WebGL; "
               "raster tiles ship pre-rendered PNGs. Each has a job.",
               [
                   ("Vector tile structure",
                    "Mapbox Vector Tile (MVT) is a protobuf with layers (roads, water, "
                    "buildings, labels) and per-feature attributes. The client applies a style "
                    "sheet at render time."),
                   ("Why vector wins for the base map",
                    "Smooth zoom (intermediate scales), runtime theming (dark mode), language "
                    "switching, rotation, and 3D extrusion all become trivial because the "
                    "client owns the rendering."),
                   ("Why raster wins for satellite",
                    "There is no geometry for satellite imagery — it IS the bitmap. Raster is "
                    "the natural fit. Same goes for terrain hillshade and historical aerial."),
                   ("Storage trade-off",
                    "Vector tiles are smaller per-tile (5-50 KB) but require a richer client. "
                    "Raster tiles are larger (10-100 KB) and one set per style — supporting "
                    "10 styles balloons storage 10x for raster, ~1x for vector."),
                   ("Hybrid in production",
                    "Google Maps and Apple Maps both ship vector base tiles + raster satellite "
                    "tiles. The client composites layers."),
               ]),
        _topic("offline-maps",
               "Offline Map Packs: Tiles + Sub-Graph + POIs",
               "Offline mode requires a self-contained pack the device can render and route on "
               "without network. Pack composition is the design problem.",
               [
                   ("Bbox selection",
                    "User picks a region on the map. Backend computes a tight bbox plus a small "
                    "buffer for cross-border routing."),
                   ("Tile subset",
                    "Vector tiles for the bbox at zooms 6-16 (lower zooms cover the whole world "
                    "and are part of the global download anyway). Higher zooms only on demand."),
                   ("Routing sub-graph",
                    "Road edges + nodes inside the bbox plus border edges to allow routing that "
                    "exits and returns. CH shortcuts re-extracted for the sub-graph so on-"
                    "device routing is still fast."),
                   ("POI subset",
                    "Top-N POIs by popularity inside the bbox, with offline-friendly minimal "
                    "metadata."),
                   ("Pack format",
                    "Single signed binary file (~1-3 GB per country pack) with index header. "
                    "Updated quarterly; expiry drives a re-download nudge."),
                   ("Offline limitations",
                    "No live traffic; ETAs use historical speeds. No Street View. Reverse "
                    "geocoding limited to packed POIs / addresses."),
               ]),
    ],
)
