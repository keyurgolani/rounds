"""SD-Calendar — Design Google Calendar (scheduling, recurring events,
RSVPs, reminders). Mirrors the schema/shape of SD_01 in sd_questions.py."""
from __future__ import annotations

from builder.sd_questions import _q, _topic


PAYLOAD = _q(
    "Design Google Calendar",
    "Medium",
    "Design a planet-scale calendaring platform supporting personal scheduling, multi-attendee meetings, "
    "recurring events with arbitrary RFC 5545 recurrence rules, RSVPs, reminders/notifications, free/busy "
    "lookups across many users, calendar sharing with fine-grained ACLs, time-zone-aware display, and "
    "interoperability with external clients via ICS/CalDAV. The system must serve 1B+ users, store decades "
    "of historical and future events, expand recurring series efficiently for range queries, deliver "
    "reminders on time even at peak fan-out, and reconcile concurrent edits across web, mobile, and email "
    "clients. Cover the event data model, recurrence semantics (RRULE/RDATE/EXDATE), exception overrides, "
    "time-zone storage strategy (UTC + display TZ + DST handling), conflict detection, reminder dispatch, "
    "free/busy queries, sharing/ACLs, ICS import/export, and CalDAV synchronization.",
    hints=[
        "Store events in UTC + carry the originating IANA TZ — DST transitions and floating-time events "
        "are the failure mode candidates miss.",
        "Recurrence is RFC 5545 RRULE; expansion at query time vs precomputation is the central tradeoff.",
        "An event series is a single row with RRULE; exceptions (edited single occurrence) are separate "
        "override rows keyed by RECURRENCE-ID.",
        "Reminders are a fan-out scheduling problem — a delay queue keyed by trigger time, sharded.",
        "Free/busy is per-user — shard by user_id; a meeting query with N attendees is N parallel reads.",
        "RSVPs are per-attendee state on the event; conflict-free since each attendee owns their slot.",
        "CalDAV/ICS are interop surfaces — speak them at the edge, keep the internal model native.",
    ],
    constraints=[
        "1B+ users, 10B+ events stored, decades of past + future range",
        "Reminder delivery within +/- 30s of scheduled trigger at p99",
        "Event read p95 < 100ms; range query (week view) p95 < 200ms",
        "Recurring series can extend indefinitely — must not materialise unbounded rows",
        "Free/busy across up to 50 attendees in a single scheduling query",
        "Time zones: 400+ IANA zones; DST transitions correct across boundaries",
        "Concurrent edits across devices reconciled without losing RSVPs",
        "ICS/CalDAV interoperability with Outlook, Apple, Thunderbird",
        "Sharing ACLs: free/busy-only, see-all, edit, delegate — enforced server-side",
    ],
    req_func=[
        "Create / read / update / delete one-off events",
        "Recurring events via RFC 5545 RRULE (daily, weekly, monthly-by-day, yearly, etc.)",
        "Edit-this / edit-this-and-future / edit-all semantics for recurring series",
        "Invite attendees; track RSVP state (accepted, declined, tentative, needs-action)",
        "Reminders: in-app push, email, SMS at configurable lead times before start",
        "Free/busy lookup for one or more users over a time range",
        "Suggest meeting times that work for all required attendees",
        "Calendar sharing with ACLs (free/busy-only, read, write, delegate)",
        "Multiple calendars per user (personal, work, holidays, subscribed)",
        "Time-zone-aware display — store UTC + originating TZ; render in viewer TZ",
        "ICS import and export per calendar; subscribe to remote ICS URL",
        "CalDAV sync endpoint for external clients (Apple Calendar, Thunderbird)",
        "Conflict detection — surface overlapping events on the user's calendars",
    ],
    req_nonfunc=[
        "Reminder timing accuracy: 99% within +/- 30s; 99.9% within +/- 2min",
        "99.99% availability for read; 99.95% for write",
        "Range query latency p95 < 200ms even with recurring expansion",
        "Free/busy fan-out for 50 attendees p95 < 500ms",
        "Eventual consistency on sharing-graph propagation; per-event strong consistency",
        "DST and TZ-rule updates (IANA tzdata) hot-reloadable without restart",
        "Storage efficient — no unbounded materialisation of recurring series",
        "GDPR / SOC2 / data-residency aware (region-pinned calendars)",
    ],
    estimation={
        "users": "1B registered, ~300M DAU",
        "events_per_user": "avg ~500 future-or-recent; long tail to 100K (corp shared rooms)",
        "total_events_stored": "~10B rows; logical occurrences expanded ~10–100T",
        "writes_qps_steady": "~50K events/sec (creates+edits+RSVPs)",
        "writes_qps_peak": "~250K/sec (Monday 9am US)",
        "reads_qps": "~500K range queries/sec; ~200K free/busy queries/sec",
        "reminders_per_day": "~5B reminder dispatches/day (≈58K/sec avg, 500K/sec peak)",
        "storage_per_event": "~2 KB (metadata + RRULE + attendees JSON)",
        "total_storage": "~25 TB primary + indexes + replicas → ~150 TB",
    },
    endpoints=[
        {"method": "POST", "path": "/calendars/{cal_id}/events",
         "description": "Create an event (one-off or recurring with RRULE)",
         "body": "{title, start_utc, end_utc, tz, rrule?, attendees:[], reminders:[]}"},
        {"method": "GET", "path": "/calendars/{cal_id}/events",
         "description": "Range query — returns expanded occurrences in [from, to]",
         "body": "?from=ISO&to=ISO&tz=America/New_York"},
        {"method": "PATCH", "path": "/calendars/{cal_id}/events/{event_id}",
         "description": "Edit event; ?scope=this|this_and_future|all for recurring series",
         "body": "{fields...}"},
        {"method": "DELETE", "path": "/calendars/{cal_id}/events/{event_id}",
         "description": "Delete event; ?scope=this|this_and_future|all"},
        {"method": "POST", "path": "/events/{event_id}/rsvp",
         "description": "Set RSVP state for the calling user",
         "body": "{state: 'accepted'|'declined'|'tentative', comment?}"},
        {"method": "POST", "path": "/freebusy",
         "description": "Free/busy across multiple users for a range",
         "body": "{users:[user_id], from, to, tz}"},
        {"method": "POST", "path": "/scheduling/suggest",
         "description": "Suggest meeting slots that work for all required attendees",
         "body": "{required:[user_id], optional:[user_id], duration_min, range, working_hours}"},
        {"method": "POST", "path": "/calendars/{cal_id}/share",
         "description": "Grant ACL on a calendar",
         "body": "{grantee_user_id, role: 'freebusy'|'reader'|'writer'|'delegate'}"},
        {"method": "POST", "path": "/calendars/{cal_id}/import.ics",
         "description": "Import an ICS file"},
        {"method": "GET", "path": "/calendars/{cal_id}/export.ics",
         "description": "Export calendar as RFC 5545 ICS"},
        {"method": "ANY", "path": "/caldav/{user}/{cal}/",
         "description": "CalDAV (RFC 4791) PROPFIND/REPORT/PUT/DELETE for external client sync"},
    ],
    tables=[
        {"name": "calendars",
         "columns": ["calendar_id BIGINT PK", "owner_user_id BIGINT", "title VARCHAR(255)",
                     "default_tz VARCHAR(64)", "color VARCHAR(16)", "kind VARCHAR(16)",
                     "created_at BIGINT"]},
        {"name": "events",
         "columns": ["event_id BIGINT PK", "calendar_id BIGINT", "organizer_user_id BIGINT",
                     "title VARCHAR(255)", "description TEXT", "location VARCHAR(255)",
                     "start_utc BIGINT", "end_utc BIGINT", "tz VARCHAR(64)",
                     "all_day BOOL", "rrule VARCHAR(512)", "rdate TEXT", "exdate TEXT",
                     "series_id BIGINT NULL", "recurrence_id BIGINT NULL",
                     "status VARCHAR(16)", "visibility VARCHAR(16)",
                     "version BIGINT", "etag VARCHAR(64)",
                     "created_at BIGINT", "updated_at BIGINT"]},
        {"name": "event_attendees",
         "columns": ["event_id BIGINT", "user_id BIGINT", "email VARCHAR(255)",
                     "role VARCHAR(16)", "rsvp_state VARCHAR(16)",
                     "responded_at BIGINT", "comment TEXT",
                     "PRIMARY KEY (event_id, user_id)"]},
        {"name": "reminders",
         "columns": ["reminder_id BIGINT PK", "event_id BIGINT", "user_id BIGINT",
                     "occurrence_start_utc BIGINT", "trigger_at_utc BIGINT",
                     "channel VARCHAR(16)", "lead_min INT",
                     "status VARCHAR(16)", "delivered_at BIGINT"]},
        {"name": "calendar_acls",
         "columns": ["calendar_id BIGINT", "grantee_user_id BIGINT", "role VARCHAR(16)",
                     "granted_at BIGINT",
                     "PRIMARY KEY (calendar_id, grantee_user_id)"]},
        {"name": "user_freebusy_index",
         "columns": ["user_id BIGINT", "bucket_start_utc BIGINT",
                     "bucket_end_utc BIGINT", "event_id BIGINT",
                     "busy BOOL"]},
        {"name": "subscriptions",
         "columns": ["subscription_id BIGINT PK", "calendar_id BIGINT",
                     "ics_url VARCHAR(1024)", "etag VARCHAR(64)",
                     "last_synced_at BIGINT"]},
        {"name": "caldav_sync_tokens",
         "columns": ["user_id BIGINT", "calendar_id BIGINT", "client_id VARCHAR(64)",
                     "sync_token VARCHAR(128)",
                     "PRIMARY KEY (user_id, calendar_id, client_id)"]},
    ],
    indexes=[
        "(calendar_id, start_utc) on events — range scan for week/month view",
        "(series_id, recurrence_id) on events — locate exception overrides for a series",
        "(organizer_user_id, start_utc) on events — events I organise",
        "(user_id, occurrence_start_utc) on event_attendees join — invitations to a user",
        "(trigger_at_utc) on reminders — sharded delay queue scan",
        "(user_id, bucket_start_utc) on user_freebusy_index — free/busy fan-out",
        "(grantee_user_id) on calendar_acls — calendars shared with me",
        "(calendar_id, updated_at) on events — CalDAV sync delta queries",
    ],
    hld_desc=(
        "Core stack splits into Calendar Service (CRUD on events with recurrence), Free/Busy Service "
        "(low-latency time-overlap queries), Scheduling Service (slot suggestion), Reminder Service "
        "(scheduled fan-out), Sharing Service (ACL + invitation graph), and Sync Edge (CalDAV/ICS "
        "interop). All write traffic terminates at the Calendar Service which writes the event row "
        "with its RRULE and emits a change event. The free/busy index is updated synchronously for "
        "near events (next 90 days) and lazily for far-future. Reminders are computed at create/edit "
        "time and enqueued into a delay queue (e.g., Kafka with time-bucketed topics, or a sharded "
        "DynamoDB time-series with a workers fleet polling the next bucket). Range queries hit the "
        "Calendar Service which fetches matching base events + their exception overrides + expands "
        "RRULEs in-memory, returning concrete occurrences. Free/busy queries hit a per-user busy "
        "index (precomputed, sharded by user_id) so 50-attendee fan-out is 50 parallel point lookups. "
        "Sharding strategy: events sharded by calendar_id; free/busy index sharded by user_id; "
        "reminders sharded by trigger time bucket. CalDAV gateway translates CalDAV verbs to "
        "internal API; ICS import/export is a server-side parser/serializer."
    ),
    hld_components=[
        {"name": "API Gateway", "role": "Auth, rate-limit, route, multi-tenant"},
        {"name": "Calendar Service", "role": "Event CRUD, RRULE expansion, exception override resolution"},
        {"name": "Free/Busy Service", "role": "Per-user busy index lookups; fan-out for scheduling"},
        {"name": "Scheduling Service", "role": "Find common free slots across required attendees"},
        {"name": "Reminder Service", "role": "Compute trigger times; enqueue and dispatch via push/email/SMS"},
        {"name": "Reminder Dispatcher", "role": "Polls delay queue; calls notification channels"},
        {"name": "Sharing Service", "role": "ACL evaluation; invitation graph propagation"},
        {"name": "CalDAV Gateway", "role": "RFC 4791 PROPFIND/REPORT/PUT mapped to internal API"},
        {"name": "ICS Service", "role": "RFC 5545 import/export; remote-URL subscription poller"},
        {"name": "Event Store (sharded by calendar_id)", "role": "Primary event rows with RRULE"},
        {"name": "Free/Busy Store (sharded by user_id)", "role": "Per-user time-bucketed busy index"},
        {"name": "Reminder Queue", "role": "Time-bucketed delay queue, sharded by trigger time"},
        {"name": "TZ Database", "role": "IANA tzdata; hot-reloadable for DST rule updates"},
        {"name": "Notification Channels", "role": "Push (FCM/APNs), email, SMS providers"},
        {"name": "Search Index", "role": "Full-text + facet on title/location/attendees"},
    ],
    detailed_design={
        "event_model": (
            "Each event is a single row carrying its UTC start/end, originating IANA TZ, and an "
            "optional RRULE plus RDATE/EXDATE auxiliary date sets. Recurring events are NOT "
            "expanded into rows. Edits to a single occurrence create an exception override row "
            "with series_id pointing to the parent and recurrence_id = the original occurrence's "
            "UTC start. Edits to 'this and future' truncate the parent's RRULE with UNTIL and "
            "create a new series starting from the split point. Edit-all updates the parent. "
            "Each row carries a version + etag for CalDAV/optimistic-concurrency sync."
        ),
        "recurrence_expansion": (
            "Read path: when a client requests a range [from, to], the service finds (a) all "
            "non-recurring events whose start_utc overlaps the range, and (b) all recurring base "
            "events whose RRULE could possibly produce an occurrence in the range — pruned by "
            "indexed start_utc and (RRULE-derived) latest-possible-end. For each candidate base, "
            "expand the RRULE in-memory using a deterministic library, intersect with [from, to], "
            "subtract EXDATEs, then JOIN against exception override rows to replace overridden "
            "occurrences with their edited versions. Result is a flat list of concrete occurrences. "
            "Expansion at query time avoids unbounded materialisation; cost is O(occurrences in "
            "range) per series, which is small for typical week/month views. For very long-range "
            "queries (year view), cap expansion at a configurable horizon (e.g., 1000 occurrences "
            "per series) and request narrower ranges from the client."
        ),
        "expansion_tradeoff": (
            "Two extremes. (1) Precompute every occurrence as a row — O(infinity) for daily 'until "
            "forever' RRULEs; index bloat; edits cascade across thousands of rows. (2) Pure on-the-"
            "fly expansion — every range query re-walks the RRULE; CPU-bound on hot calendars. The "
            "production answer is hybrid: store base + RRULE; precompute a free/busy summary "
            "(coarse busy bitmap) for the next 90 days into the per-user index; expand the rich "
            "occurrence detail at query time. The free/busy index is the only precomputed "
            "materialisation, sized to a finite horizon."
        ),
        "time_zones": (
            "Always store start_utc as the absolute instant; carry the originating IANA TZ ID "
            "alongside. Display in the viewer's TZ via tzdata conversion. DST transitions handled "
            "at expansion time: a daily 9am New York event has its UTC instant shift by an hour "
            "across DST boundaries, but the local 9am invariant holds — recurrence libraries that "
            "compute next-occurrence in local TZ then convert get this right; libraries that step "
            "in UTC get it wrong. Floating events (no TZ — common in birthdays / all-day) stored "
            "with all_day=true and a date (no UTC instant). Time-zone changes (governments updating "
            "DST rules) require hot-reloading tzdata; recurring events whose computed UTC moves are "
            "re-indexed lazily."
        ),
        "rsvp_handling": (
            "RSVP state is per-attendee on event_attendees. Each attendee owns their slot — no "
            "conflict resolution needed across attendees. Organizer sees the rolled-up summary "
            "(accepted/declined/tentative/needs-action). Updates emit a notification to the "
            "organizer and (optionally) other attendees. RSVP on a recurring series defaults to "
            "all occurrences but can be set per-occurrence by creating an exception with an "
            "attendee-specific override."
        ),
        "reminders": (
            "On event create/edit, the Reminder Service computes trigger times = "
            "occurrence_start_utc - lead_minutes for each (attendee, channel, lead_minutes) tuple "
            "and writes them to a sharded delay queue. The queue is bucketed by minute-of-day; "
            "each bucket is a sorted set keyed by trigger_at_utc. A dispatcher fleet wakes up each "
            "minute, claims due reminders (lease + ack pattern to handle worker failure), and "
            "fans out to push/email/SMS. For recurring events, only a rolling window (e.g., next "
            "30 days) of reminder rows is materialised; a maintenance job advances the window "
            "daily. Edits remove and re-enqueue affected reminder rows. Exactly-once semantics are "
            "approximate — at-least-once delivery with a per-(reminder_id) dedupe at the channel."
        ),
        "free_busy_lookup": (
            "Per-user time-bucketed busy index, sharded by user_id. Each event create/edit writes "
            "(user_id, bucket_start, bucket_end, event_id, busy=true) rows for the next-90-day "
            "horizon (recurring expanded into the index too, capped). A free/busy query for N "
            "attendees over [from, to] is N parallel point reads to the user shards, each returning "
            "the busy intervals; service merges to a unified availability stream. Far-future "
            "queries (beyond the 90-day horizon) trigger lazy expansion + caching for that user's "
            "shard. The busy bitmap can be coarsened (15-minute buckets) to compress; precise "
            "intervals only when needed."
        ),
        "scheduling_suggestion": (
            "'Find a meeting time' query: gather free/busy for required + optional attendees over "
            "the candidate range; intersect required attendees' free intervals to derive must-be-"
            "free slots; rank by (a) maximising optional attendees free, (b) staying within all "
            "attendees' working hours and TZ, (c) avoiding back-to-back stacking for any single "
            "attendee. Return top-K slots. Caching: per-attendee free/busy can be cached for "
            "seconds with versioned invalidation on event edit."
        ),
        "sharing_acls": (
            "calendar_acls table holds (calendar_id, grantee, role). Roles in increasing power: "
            "freebusy (sees only busy/free, no titles), reader (sees full event), writer (can "
            "edit), delegate (can edit + send-as on behalf of owner). ACL evaluation is per-"
            "request; cached per-user with a small TTL (5–30s). Public calendars (e.g., holidays) "
            "are special-cased as world-readable for free/busy. Invitation creates a temporary "
            "ACL grant on the organizer's calendar for the attendee to read just that one event."
        ),
        "ics_caldav": (
            "ICS (RFC 5545) is a textual serialization. Import: parse VCALENDAR > VEVENT blocks; "
            "translate DTSTART/DTEND/RRULE/EXDATE/ATTENDEE into our event row. Subscribed remote "
            "ICS URLs are polled hourly; ETag/Last-Modified used for efficient delta. Export "
            "renders the event row back into VCALENDAR text. CalDAV (RFC 4791) layers WebDAV "
            "verbs (PROPFIND, REPORT, PUT, DELETE) over HTTP for sync. Our CalDAV Gateway maps "
            "CalDAV requests to internal API; sync_token + WebDAV-Sync extension enable delta "
            "fetch. Apple Calendar and Thunderbird drive the CalDAV interop test matrix."
        ),
        "concurrency_etag": (
            "Each event row carries a version (monotonic) and etag (hash of payload). Updates "
            "require If-Match etag header; mismatch returns 412 Precondition Failed. Mobile/web "
            "clients merge or surface conflict. CalDAV sync uses WebDAV ETag the same way. RSVPs "
            "are partition-safe (each attendee writes their own row) so RSVP updates don't "
            "contend with event-body edits."
        ),
        "sharding": (
            "events sharded by calendar_id (hash) — keeps a single user's calendar local to one "
            "shard for fast range scans. event_attendees indexed for the inverse — 'invitations "
            "to user X'. user_freebusy_index sharded by user_id — fan-out for scheduling. "
            "reminders sharded by trigger-time bucket — dispatcher fleet processes buckets in "
            "parallel. Per-user shard hot spots (executive assistants managing 1000+ events) "
            "handled with secondary indexes + cross-shard query gather."
        ),
        "slo_contract": (
            "Event read p95 < 100ms, p99 < 300ms. Range query (week view) p95 < 200ms. Free/busy "
            "for 50 attendees p95 < 500ms. Reminder delivery: p99 within +/-30s of trigger. "
            "Write durability: replicated; lost write rate < 1e-9. CalDAV sync delta correctness: "
            "100% (lost edits = data loss). Availability: 99.99% read, 99.95% write."
        ),
    },
    trade_offs=[
        {"option": "Recurring expansion: precompute vs query-time",
         "for_precompute": "O(1) range queries; uniform indexing",
         "for_query_time": "Bounded storage; cheap edits; no horizon limit",
         "recommendation": "Query-time expansion + precomputed free/busy summary for next 90 days."},
        {"option": "Time zones: store local + TZ vs UTC + TZ",
         "for_local": "Floating events trivially correct; DST 'invariant local time' obvious",
         "for_utc": "All ordering/range arithmetic uses absolute instants; no ambiguity",
         "recommendation": "UTC + originating TZ. Floating/all-day stored as date-only with all_day flag."},
        {"option": "Reminder queue: time-bucketed log vs DB poll",
         "for_log": "Linear scan of due bucket; high throughput",
         "for_poll": "Simpler ops; reuse existing DB",
         "recommendation": "Bucketed log (Kafka or sharded Dynamo TTL-style); poll-based pattern caps throughput."},
        {"option": "RSVP storage: separate table vs JSON-on-event",
         "for_separate": "Per-attendee writes don't contend; cheap inverse index",
         "for_json": "Single read fetches everything; one row update",
         "recommendation": "Separate table — write contention and inverse index ('events I was invited to') matter."},
        {"option": "Free/busy: per-user index vs join-at-query",
         "for_index": "Fast 50-attendee fan-out; bounded latency",
         "for_join": "No precomputation; simpler model",
         "recommendation": "Per-user index. 50-way join across event shards is too slow at p95 budget."},
        {"option": "CalDAV: edge translation vs native protocol",
         "for_edge": "Internal API stays clean; CalDAV is one of N gateways",
         "for_native": "No translation cost; direct mapping",
         "recommendation": "Edge gateway. CalDAV is a legacy interop surface; don't pollute internal model."},
    ],
    tips=[
        "Lead with the event model: UTC + TZ + RRULE, with exception overrides as separate rows. That's the senior signal.",
        "Recurring expansion at query time is the modern answer — precompute only the free/busy summary.",
        "RFC 5545 by name (RRULE, RDATE, EXDATE, RECURRENCE-ID) — tells the interviewer you've read the spec.",
        "Time zones: store UTC + IANA TZ. DST transitions break local-only storage. Tzdata must be hot-reloadable.",
        "Free/busy is sharded by user_id; events are sharded by calendar_id. Different access patterns = different shard keys.",
        "Reminders are a delay queue problem — time-bucketed log + dispatcher pool. Cite Kafka or sharded Dynamo.",
        "RSVP per-attendee row avoids write contention with event-body edits.",
        "CalDAV / ICS are interop edges, not core. Translate at the gateway.",
        "ETag/version-based optimistic concurrency for CalDAV and mobile sync.",
        "Don't materialise infinite recurring series — that's the trap. Always expand on read with bounded horizon.",
    ],
    thought_process=[
        "1. Clarify: scale, time-zone correctness, recurring depth, reminder accuracy.",
        "2. Estimate: 1B users × ~500 events; ~250K writes/sec peak; 5B reminders/day.",
        "3. Event model: UTC + IANA TZ; one row per series with RRULE; exceptions as overrides.",
        "4. Recurrence: expand at query time; precompute only the per-user free/busy summary.",
        "5. Reminders: trigger times computed on edit; enqueued to time-bucketed delay queue.",
        "6. Free/busy: per-user index sharded by user_id; 50-attendee fan-out is 50 parallel reads.",
        "7. Scheduling suggestion: intersect free intervals; rank by working-hours + optional attendees.",
        "8. RSVP: per-attendee row, eliminates contention with event edits.",
        "9. Sharing: ACL table; freebusy/reader/writer/delegate roles; cached per-request.",
        "10. CalDAV/ICS: edge gateway; internal API stays calendar-native.",
        "11. Sharding: calendar_id for events, user_id for free/busy, trigger-bucket for reminders.",
        "12. Concurrency: etag + If-Match; RSVPs partition-safe.",
    ],
    tags=["calendar", "scheduling", "recurrence", "rfc5545", "caldav", "time-zones"],
    arch_nodes=[
        {"id": "client", "label": "Client (Web/Mobile)", "type": "client"},
        {"id": "ext_client", "label": "External (Apple/Outlook)", "type": "client"},
        {"id": "lb", "label": "API Gateway", "type": "lb"},
        {"id": "calendar_svc", "label": "Calendar Service", "type": "server"},
        {"id": "fb_svc", "label": "Free/Busy Service", "type": "server"},
        {"id": "sched_svc", "label": "Scheduling Service", "type": "server"},
        {"id": "reminder_svc", "label": "Reminder Service", "type": "server"},
        {"id": "dispatcher", "label": "Reminder Dispatcher", "type": "service"},
        {"id": "sharing_svc", "label": "Sharing Service", "type": "server"},
        {"id": "caldav", "label": "CalDAV Gateway", "type": "server"},
        {"id": "ics_svc", "label": "ICS Import/Export", "type": "service"},
        {"id": "event_db", "label": "Event Store (shard: calendar_id)", "type": "database"},
        {"id": "fb_db", "label": "Free/Busy Index (shard: user_id)", "type": "database"},
        {"id": "rem_q", "label": "Reminder Queue (time-bucketed)", "type": "database"},
        {"id": "tzdb", "label": "TZ Database (IANA)", "type": "database"},
        {"id": "push", "label": "Push / Email / SMS", "type": "service"},
    ],
    arch_edges=[
        {"source": "client", "target": "lb"},
        {"source": "ext_client", "target": "caldav", "label": "CalDAV"},
        {"source": "lb", "target": "calendar_svc"},
        {"source": "lb", "target": "fb_svc"},
        {"source": "lb", "target": "sched_svc"},
        {"source": "lb", "target": "sharing_svc"},
        {"source": "caldav", "target": "calendar_svc", "label": "internal API"},
        {"source": "ics_svc", "target": "calendar_svc"},
        {"source": "calendar_svc", "target": "event_db", "label": "events + RRULE"},
        {"source": "calendar_svc", "target": "tzdb", "label": "TZ resolution"},
        {"source": "calendar_svc", "target": "fb_db", "label": "update busy index"},
        {"source": "calendar_svc", "target": "reminder_svc", "label": "compute reminders"},
        {"source": "fb_svc", "target": "fb_db", "label": "fan-out reads"},
        {"source": "sched_svc", "target": "fb_svc", "label": "free/busy lookups"},
        {"source": "reminder_svc", "target": "rem_q", "label": "enqueue"},
        {"source": "dispatcher", "target": "rem_q", "label": "claim due"},
        {"source": "dispatcher", "target": "push", "label": "deliver"},
        {"source": "sharing_svc", "target": "event_db", "label": "ACL check"},
    ],
    sequence_diagram=(
        "sequenceDiagram\n"
        "  participant U as User\n"
        "  participant API\n"
        "  participant CAL as Calendar Svc\n"
        "  participant DB as Event Store\n"
        "  participant FB as Free/Busy Idx\n"
        "  participant REM as Reminder Svc\n"
        "  participant Q as Reminder Queue\n"
        "  participant DSP as Dispatcher\n"
        "  participant N as Notification\n"
        "  U->>API: POST /events {RRULE, attendees, reminders}\n"
        "  API->>CAL: create event\n"
        "  CAL->>DB: insert event row (RRULE)\n"
        "  CAL->>FB: write busy intervals (next 90d)\n"
        "  CAL->>REM: compute trigger_at for each occurrence × attendee × channel\n"
        "  REM->>Q: enqueue reminder rows (sharded by trigger bucket)\n"
        "  CAL-->>API: 201 event_id, etag\n"
        "  API-->>U: event created\n"
        "  Note over DSP,Q: each minute\n"
        "  DSP->>Q: claim due bucket\n"
        "  DSP->>N: push / email / SMS\n"
        "  N-->>U: reminder\n"
    ),
    er_diagram=(
        "erDiagram\n"
        "  USER ||--o{ CALENDAR : owns\n"
        "  CALENDAR ||--o{ EVENT : contains\n"
        "  EVENT ||--o{ EVENT_ATTENDEE : has\n"
        "  EVENT ||--o{ REMINDER : triggers\n"
        "  EVENT ||--o| EVENT : exception_of\n"
        "  CALENDAR ||--o{ CALENDAR_ACL : shared_via\n"
        "  USER ||--o{ EVENT_ATTENDEE : invited_as\n"
        "  USER ||--o{ USER_FREEBUSY_INDEX : busy_in\n"
        "  CALENDAR { bigint calendar_id\n bigint owner_user_id\n string default_tz }\n"
        "  EVENT { bigint event_id\n bigint calendar_id\n bigint start_utc\n string tz\n string rrule\n bigint series_id\n bigint recurrence_id }\n"
        "  EVENT_ATTENDEE { bigint event_id\n bigint user_id\n string rsvp_state }\n"
        "  REMINDER { bigint reminder_id\n bigint event_id\n bigint trigger_at_utc\n string channel }\n"
        "  CALENDAR_ACL { bigint calendar_id\n bigint grantee_user_id\n string role }\n"
    ),
    thought_flow=(
        "graph TD\n"
        "  A[Read prompt] --> B{Recurring?}\n"
        "  B -->|Yes| C[RRULE on base row]\n"
        "  B -->|No| D[Single row UTC + TZ]\n"
        "  C --> E{Expansion strategy}\n"
        "  E -->|Precompute| F[Bloat + edit cascade]\n"
        "  E -->|Query-time| G[Bounded storage]\n"
        "  G --> H[Precompute free/busy for 90d]\n"
        "  H --> I{Reminder timing}\n"
        "  I --> J[Time-bucketed delay queue]\n"
        "  J --> K[Dispatcher fleet]\n"
        "  H --> L{Free/busy fan-out}\n"
        "  L --> M[Shard by user_id; parallel reads]\n"
    ),
    tradeoff_title="Recurring Expansion: Precompute vs Query-Time",
    tradeoff_options=[
        {"label": "Precompute every occurrence",
         "description": "Materialise each occurrence as a separate row at create time.",
         "pros": ["O(1) range queries — uniform indexing",
                  "Cheap exception override (just edit one row)",
                  "Simple reminder scheduling — one-to-one with rows"],
         "cons": ["Unbounded storage for daily-forever rules",
                  "Edit-all cascades across thousands of rows",
                  "Tzdata changes require re-materialising affected series",
                  "Free/busy index bloat"]},
        {"label": "Pure query-time expansion",
         "description": "Store base + RRULE only; expand on every read.",
         "pros": ["Bounded storage independent of horizon",
                  "Edit-all is one row update",
                  "Tzdata changes pick up automatically on next read"],
         "cons": ["Every range query re-walks RRULE — CPU cost",
                  "Free/busy fan-out across attendees is expensive",
                  "Long-range queries (year view) can be slow"]},
        {"label": "Hybrid: query-time + free/busy summary (recommended)",
         "description": "Store base + RRULE; precompute coarse busy bitmap for next ~90 days into per-user index; expand rich detail at query time.",
         "pros": ["Bounded storage (only the 90-day busy summary is materialised)",
                  "Fast free/busy fan-out for scheduling (precomputed)",
                  "Detail expansion on read keeps cost proportional to rendered range",
                  "Tzdata changes correct beyond the 90-day window automatically"],
         "cons": ["Two storage models to keep consistent (event row + free/busy index)",
                  "90-day rolling window requires a maintenance job",
                  "Edits must update both stores transactionally (or compensating)"]},
    ],
    tradeoff_rec=(
        "Hybrid: store base events with RRULE; expand occurrence detail at query time; precompute "
        "only the per-user free/busy summary for the rolling 90-day window. Avoids unbounded "
        "materialisation while keeping scheduling fan-out fast. The maintenance job advances the "
        "window daily and is the only place re-materialisation happens."
    ),
    senior_topics=[
        _topic("rrule-rfc5545",
               "RFC 5545 RRULE Semantics",
               "Recurrence is an iCalendar standard with rich grammar — DAILY/WEEKLY/MONTHLY/YEARLY "
               "frequencies, INTERVAL, BYDAY/BYMONTHDAY/BYSETPOS modifiers, COUNT/UNTIL termination. "
               "Knowing the spec by name distinguishes senior from junior answers.",
               [
                   ("Core grammar",
                    "FREQ + INTERVAL + (COUNT | UNTIL) + BY-clauses. Example: FREQ=WEEKLY;BYDAY=MO,WE,FR; "
                    "INTERVAL=1 (every Mon/Wed/Fri). Combine with RDATE (additional dates) and EXDATE "
                    "(excluded dates) on the same event."),
                   ("Edge cases",
                    "MONTHLY BYMONTHDAY=31 must skip months with fewer days (Feb, Apr). YEARLY "
                    "BYYEARDAY=366 occurs only in leap years. BYSETPOS picks 'last Friday of month'. "
                    "DST-shifted local times must compute next-occurrence in local TZ then convert."),
                   ("Exception overrides (RECURRENCE-ID)",
                    "Editing a single occurrence creates a separate VEVENT with same UID + a "
                    "RECURRENCE-ID matching the original occurrence's start. Reader joins and "
                    "substitutes the override during expansion."),
                   ("UNTIL vs COUNT",
                    "UNTIL is a DTSTART-aligned end instant in UTC. COUNT is the total occurrence "
                    "limit. Edit-this-and-future is implemented by truncating the parent's RRULE "
                    "with UNTIL = the split point and creating a new series from there."),
                   ("Library choice",
                    "Use battle-tested libraries (rrule.js, python-dateutil, ical4j); never roll "
                    "your own. The grammar has subtle rules even seasoned engineers get wrong."),
               ],
               diagram=(
                   "graph TD\n"
                   "  A[VEVENT base] --> B[RRULE: FREQ=WEEKLY;BYDAY=MO,WE,FR]\n"
                   "  A --> C[RDATE: +specific extras]\n"
                   "  A --> D[EXDATE: -specific exclusions]\n"
                   "  A --> E[VEVENT exception RECURRENCE-ID=t1]\n"
                   "  E --> F[Replaces occurrence at t1]\n"
                   "  B --> G[Expand in [from,to] - EXDATE + RDATE]\n"
                   "  G --> H[Substitute exceptions]\n"
                   "  H --> I[Concrete occurrences]\n"
               )),
        _topic("time-zones-dst",
               "Time-Zone Correctness and DST Handling",
               "Time zones are the most common source of calendar bugs. The correct model is UTC + "
               "originating IANA TZ; derive local time at render. Floating events and DST transitions "
               "are the edge cases that catch naive designs.",
               [
                   ("UTC + IANA TZ",
                    "Store start_utc as the absolute instant; carry the originating IANA TZ ID "
                    "(America/New_York, not 'EST'). Display in viewer's TZ via tzdata conversion. "
                    "This handles DST transitions correctly because tzdata encodes the offset rules."),
                   ("DST and recurring events",
                    "A daily 9am New York event computes next-occurrence in local time then converts "
                    "to UTC — its UTC instant shifts by an hour twice a year. Recurrence libraries "
                    "that step in UTC produce 8am or 10am events on the wrong side of DST."),
                   ("Floating / all-day events",
                    "Birthdays, holidays, multi-day vacations have no TZ — they happen 'on that "
                    "date' wherever you are. Store with all_day=true and a date-only field; never "
                    "convert to UTC instant."),
                   ("Tzdata updates",
                    "Governments change DST rules (e.g., Turkey, Brazil, US Senate proposals). "
                    "tzdata releases ~4×/year. System must hot-reload tzdata; recurring events "
                    "whose computed UTC moves are re-indexed lazily on next read."),
                   ("Cross-TZ meetings",
                    "An organizer in Tokyo invites attendees in NYC and London. Each renders the "
                    "event in their own TZ. Free/busy queries always normalize to UTC for "
                    "intersection."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant Org as Organizer (Tokyo)\n"
                   "  participant API\n"
                   "  participant DB\n"
                   "  participant View as Attendee (NYC)\n"
                   "  Org->>API: create 'Daily standup 9am Tokyo'\n"
                   "  API->>DB: store start_utc=00:00Z, tz=Asia/Tokyo, rrule=FREQ=DAILY\n"
                   "  Note over DB: DST in Tokyo: none. NYC: yes.\n"
                   "  View->>API: GET week range\n"
                   "  API->>API: expand RRULE in Asia/Tokyo, convert to UTC\n"
                   "  API->>API: render in America/New_York → 8pm or 7pm depending on DST\n"
                   "  API-->>View: occurrences with local times\n"
               )),
        _topic("reminder-delay-queue",
               "Reminder Service: Time-Bucketed Delay Queue",
               "Delivering 5B reminders/day at +/-30s accuracy is a scheduled fan-out problem. The "
               "core primitive is a sharded delay queue keyed by trigger time, processed by a "
               "dispatcher fleet.",
               [
                   ("Bucketing",
                    "Partition the timeline into minute-sized buckets. Each reminder writes to the "
                    "bucket containing its trigger_at_utc. Dispatchers wake each minute and process "
                    "the bucket whose timestamp == now (or now-1, with replay tolerance)."),
                   ("Storage choices",
                    "(a) Kafka with one topic per minute or hash-based bucketing — high throughput, "
                    "natural sharding. (b) Sharded Dynamo with TTL-driven expiration → CDC stream "
                    "→ dispatcher. (c) Redis sorted sets per shard, ZRANGEBYSCORE for due rows. "
                    "Tradeoffs: Kafka scales best; Redis is simplest; Dynamo TTL has built-in "
                    "deletion."),
                   ("Lease and ack",
                    "Each dispatcher claims a batch of due reminders by writing a lease (worker_id "
                    "+ expires_at). On successful delivery, ack and delete. On lease expiry without "
                    "ack, reminder becomes claimable again — at-least-once delivery. Channel-side "
                    "dedupe (reminder_id) provides approximate exactly-once."),
                   ("Edits and cancels",
                    "Event edit recomputes trigger times and writes new reminder rows; old rows "
                    "are tombstoned (status=cancelled) so dispatcher skips them. For Kafka-backed "
                    "queue, dispatcher consults a 'cancelled set' before delivery."),
                   ("Recurring window",
                    "Materialise reminders only for the next ~30 days of recurring occurrences; a "
                    "maintenance job rolls the window forward daily. Avoids unbounded reminder "
                    "rows for FREQ=DAILY;UNTIL=2099 events."),
                   ("Failure modes",
                    "Channel down → retry with backoff, fall back to alternate channel. Dispatcher "
                    "fleet down → buckets accumulate, replay on recovery (delivery latency spikes "
                    "but no loss). Clock skew on dispatchers → use distributed clock or central "
                    "broker timestamp."),
               ],
               diagram=(
                   "graph LR\n"
                   "  E[Event Create/Edit] --> R[Reminder Service]\n"
                   "  R -- compute trigger_at --> Q[Time-Bucketed Queue]\n"
                   "  subgraph Q\n"
                   "    B1[Bucket 09:00]\n"
                   "    B2[Bucket 09:01]\n"
                   "    B3[Bucket 09:02]\n"
                   "  end\n"
                   "  D[Dispatcher Pool] -- claim due bucket --> Q\n"
                   "  D -- lease + deliver --> N[Push/Email/SMS]\n"
                   "  N -- ack --> D\n"
                   "  D -- delete --> Q\n"
               )),
        _topic("freebusy-fanout",
               "Free/Busy Lookup: Per-User Index with Fan-Out",
               "Scheduling a meeting with 50 attendees requires fast availability lookup across 50 "
               "users. The data layout choice — events sharded by calendar vs free/busy indexed "
               "per user — determines fan-out cost.",
               [
                   ("Why join-at-query is too slow",
                    "Events are sharded by calendar_id. To answer 'is user X busy at T?', a join "
                    "would scan multiple calendar shards X owns or is invited to. 50 attendees × "
                    "average 3 calendars each = 150 shard reads per query, multiplied by the time "
                    "range. Latency budget exhausted."),
                   ("Per-user busy index",
                    "Maintain a per-user table sharded by user_id storing busy intervals from all "
                    "calendars that user owns or has accepted invites to. One row per attended event "
                    "× occurrence × time-bucket. Free/busy point query is now an indexed range "
                    "scan on a single shard."),
                   ("Maintenance",
                    "On event create / edit / RSVP-accept, write the affected attendees' busy "
                    "intervals (next 90 days for recurring) into the index. On delete / decline, "
                    "remove. Maintenance job rolls the 90-day window forward daily and re-expands "
                    "recurring events into the new window."),
                   ("Coarsening",
                    "For free/busy-only ACL grants, return only busy/free (no event details) — "
                    "the index already stores just busy intervals, naturally privacy-preserving. "
                    "Bucket size 15min is enough for most scheduling; finer granularity stored as "
                    "exact timestamps for precise rendering."),
                   ("Fan-out at query time",
                    "Scheduling Service issues N parallel reads (one per attendee shard), each "
                    "returning busy intervals over [from, to]. Service merges and intersects "
                    "free intervals; ranks by working hours and optional-attendee coverage."),
               ],
               diagram=(
                   "graph TD\n"
                   "  E[Event create/edit] --> CAL[Calendar Service]\n"
                   "  CAL -- update --> EV[(Event Store shard: cal_id)]\n"
                   "  CAL -- propagate to attendees --> FB[(Free/Busy Index shard: user_id)]\n"
                   "  Q[Scheduling Query: 50 attendees] --> SCHED[Scheduling Service]\n"
                   "  SCHED -- N parallel point reads --> FB\n"
                   "  FB --> SCHED\n"
                   "  SCHED -- intersect free intervals --> R[Top-K slot suggestions]\n"
               )),
        _topic("caldav-ics",
               "CalDAV and ICS Interop",
               "External clients (Apple Calendar, Outlook, Thunderbird) speak CalDAV (RFC 4791) and "
               "consume/produce ICS (RFC 5545). The pragmatic design exposes a CalDAV gateway at "
               "the edge while keeping the internal API native — translation, not rewriting.",
               [
                   ("ICS (RFC 5545)",
                    "Textual VCALENDAR > VEVENT > properties (DTSTART, DTEND, RRULE, ATTENDEE, "
                    "ORGANIZER, etc.). Self-contained file format used for email invites (text/"
                    "calendar attachment) and one-shot import/export. Parser + serializer at the "
                    "service edge."),
                   ("CalDAV (RFC 4791)",
                    "WebDAV (RFC 4918) extension for calendars. PROPFIND lists collections, REPORT "
                    "queries events in a range, PUT creates/updates an event resource (body is "
                    "ICS), DELETE removes it. ETag for optimistic concurrency. Sync via "
                    "WebDAV-Sync (RFC 6578) sync_token returns deltas since last sync."),
                   ("Authentication",
                    "Basic / OAuth2 over HTTPS. App-specific passwords for clients that don't "
                    "support OAuth (legacy CalDAV)."),
                   ("Gateway architecture",
                    "CalDAV Gateway accepts WebDAV verbs, parses ICS bodies, calls internal "
                    "Calendar Service API. Internal events have native fields; gateway "
                    "round-trips ICS on the way in and out. Internal model never sees CalDAV — "
                    "keeps it composable with web/mobile UIs that use a JSON API."),
                   ("Subscribed remote ICS",
                    "Read-only feeds (sports schedules, holidays). Poller fetches the remote URL "
                    "hourly; ETag/Last-Modified for delta efficiency; parsed events stored as a "
                    "read-only calendar."),
                   ("Quirks",
                    "Apple Calendar caches aggressively — broken ETags cause sync loops. Outlook "
                    "uses extended properties (X-MICROSOFT-*) — ignore unknown X- properties on "
                    "import. Thunderbird sends CalDAV without sync_token — fall back to full "
                    "REPORT."),
               ],
               diagram=(
                   "sequenceDiagram\n"
                   "  participant AC as Apple Calendar\n"
                   "  participant CD as CalDAV Gateway\n"
                   "  participant CAL as Calendar Service\n"
                   "  participant DB as Event Store\n"
                   "  AC->>CD: PROPFIND /caldav/user/cal/\n"
                   "  CD-->>AC: collection metadata + sync_token\n"
                   "  AC->>CD: REPORT (calendar-query, range)\n"
                   "  CD->>CAL: range query\n"
                   "  CAL->>DB: fetch + expand RRULE\n"
                   "  CAL-->>CD: event list\n"
                   "  CD-->>AC: multistatus + ICS bodies\n"
                   "  AC->>CD: PUT event.ics (new event)\n"
                   "  CD->>CD: parse ICS\n"
                   "  CD->>CAL: create event\n"
                   "  CAL-->>CD: 201 etag\n"
                   "  CD-->>AC: 201 ETag\n"
               )),
        _topic("sharding-strategy",
               "Sharding: Different Keys for Different Access Patterns",
               "A single shard key cannot serve both 'show me my calendar' (calendar-centric) and "
               "'is user X busy?' (user-centric). Calendar uses two sharded stores with different "
               "keys plus inverse indexes.",
               [
                   ("Events sharded by calendar_id",
                    "Range queries scan one calendar's events efficiently — 'show my week' is a "
                    "single-shard scan. Index on (calendar_id, start_utc). Hot calendars (huge "
                    "shared rooms) handled with secondary partitioning by year."),
                   ("Free/busy indexed by user_id",
                    "Scheduling fan-out is N parallel point reads to user shards. Each event "
                    "create/edit propagates busy intervals to all attendee user_id shards (async, "
                    "with retries)."),
                   ("Reminders sharded by trigger time bucket",
                    "Dispatcher fleet scales horizontally with bucket count. No per-user hotspot."),
                   ("ACL sharded by calendar_id",
                    "Co-located with events for fast 'who has access to this calendar' check. "
                    "Inverse index (grantee_user_id → calendars) sharded separately for "
                    "'calendars shared with me' query."),
                   ("Cross-shard transactions",
                    "Event create touches event shard + free/busy shards + reminder queue. "
                    "Pattern: write event row first (source of truth), then async propagate to "
                    "free/busy + reminders with retries; reconciliation job catches stragglers. "
                    "Eventual consistency on free/busy and reminders is acceptable; user-facing "
                    "event read is strongly consistent on the event row."),
                   ("Hot-shard mitigations",
                    "Executive assistants managing 1000s of events on shared calendars create "
                    "hotspots. Mitigate with secondary partitioning (calendar_id, year), per-shard "
                    "rate limiting, and read replicas."),
               ],
               diagram=(
                   "graph TD\n"
                   "  C[Client] --> CAL[Calendar Service]\n"
                   "  CAL -->|shard by calendar_id| E1[(Event Shard A)]\n"
                   "  CAL -->|shard by calendar_id| E2[(Event Shard B)]\n"
                   "  CAL -->|propagate per attendee| F1[(Free/Busy Shard user 1)]\n"
                   "  CAL -->|propagate per attendee| F2[(Free/Busy Shard user 2)]\n"
                   "  CAL -->|by trigger bucket| Q1[(Reminder Bucket 09:00)]\n"
                   "  CAL -->|by trigger bucket| Q2[(Reminder Bucket 09:01)]\n"
                   "  S[Scheduling Service] -->|N parallel reads| F1\n"
                   "  S --> F2\n"
               )),
    ],
)
