import type { SystemDesignContent } from '../guideTypes';

// ─────────────────────────────────────────────────────────────────────────────
// Long literals declared FIRST to avoid temporal dead zone when referenced
// inside the systemDesignContent export below.
// ─────────────────────────────────────────────────────────────────────────────

const ROUND_TIMELINE: SystemDesignContent['dashboard']['timeline'] = [
  {
    id: 'requirements',
    minutes: '0–5',
    label: 'Requirements',
    checklist: ['functional list', 'non-functional list', 'scale numbers', 'non-goals'],
  },
  {
    id: 'api-data',
    minutes: '5–10',
    label: 'API + Data model',
    checklist: ['endpoints', 'entities', 'primary keys', 'idempotency keys where retried'],
  },
  {
    id: 'architecture',
    minutes: '10–20',
    label: 'High-level architecture',
    checklist: ['write path with verbs', 'read path with verbs', 'components that earned a seat'],
  },
  {
    id: 'deep-dive',
    minutes: '20–32',
    label: 'Deep dive',
    checklist: ['pick one bottleneck', 'justify with scale math', 'name the trade-off'],
  },
  {
    id: 'failure-modes',
    minutes: '32–40',
    label: 'Failure modes',
    checklist: ['pick the failure that hurts the user', 'mitigation', 'metric', 'recovery'],
  },
  {
    id: 'close',
    minutes: '40–45',
    label: 'Close',
    checklist: ['requirement met', 'biggest unresolved trade-off', 'what you would do next'],
  },
];

const BUILDING_BLOCKS: SystemDesignContent['buildingBlocks'] = {
  components: [
    { id: 'cache-aside',      eyebrow: 'Cache',    trigger: 'simple read-heavy cache',           move: 'app checks cache, loads DB on miss, writes cache; TTL + invalidation', watch: 'stampede on miss' },
    { id: 'write-through',    eyebrow: 'Cache',    trigger: 'must read what was just written',   move: 'write cache and DB together (sync) for safer reads',                  watch: 'higher write latency' },
    { id: 'write-behind',     eyebrow: 'Cache',    trigger: 'write throughput dominates',        move: 'write cache/queue first, DB later (async)',                           watch: 'data-loss risk on crash' },
    { id: 'queue-idempotent', eyebrow: 'Queue',    trigger: 'retries possible',                  move: 'idempotency key per job; dedupe table or unique constraint',          watch: 'window too small leaks duplicates' },
    { id: 'queue-dlq',        eyebrow: 'Queue',    trigger: 'poison messages exist',             move: 'DLQ after N attempts; alert on size',                                 watch: 'silent DLQ growth' },
    { id: 'cdn',              eyebrow: 'CDN',      trigger: 'global static or media reads',      move: 'object storage behind CDN; cache headers + purge path',               watch: 'private content via CDN, purge lag' },
    { id: 'stream',           eyebrow: 'Stream',   trigger: 'multi-consumer ordered log',        move: 'partition key + retention + consumer groups',                         watch: 'hot partitions; ordering only within partition' },
    { id: 'coordinator',      eyebrow: 'Coord.',   trigger: 'leader election or exclusive work', move: 'lease with expiry + fencing token',                                   watch: 'stale leader after lease drift' },
    { id: 'api-gateway',      eyebrow: 'Gateway',  trigger: 'auth, rate limit, routing',         move: 'gateway only — no business logic',                                    watch: 'gateway becomes a monolith' },
  ],
  storage: [
    { kind: 'Relational',  useWhen: 'transactions, joins, constraints, money',             primaryKeyShape: 'surrogate or composite business key', tradeOffNamed: 'vertical scale; sharding is manual' },
    { kind: 'Key–Value',   useWhen: 'get/put by key — sessions, counters, flags',          primaryKeyShape: 'opaque key',                          tradeOffNamed: 'no joins; range scans usually expensive' },
    { kind: 'Document',    useWhen: 'flexible nested objects — profiles, catalogs',        primaryKeyShape: 'doc id; partition on a tenant key',   tradeOffNamed: 'cross-doc transactions limited' },
    { kind: 'Wide-Column', useWhen: 'huge writes, time-series, predictable partition key', primaryKeyShape: 'partition + clustering key',          tradeOffNamed: 'queries pre-planned; ad-hoc is hard' },
    { kind: 'Object',      useWhen: 'blobs, images, video, logs, backups',                 primaryKeyShape: 'bucket + path',                       tradeOffNamed: 'eventual consistency on list ops' },
    { kind: 'Search',      useWhen: 'inverted index, ranking, filter, typo/prefix',        primaryKeyShape: 'doc id; not source of truth',         tradeOffNamed: 'indexing lag; reindex cost' },
    { kind: 'Graph',       useWhen: 'depth-N relationship traversal',                      primaryKeyShape: 'node id + edge type',                 tradeOffNamed: 'less mature ops tooling' },
  ],
  keysIndexesNotes: [
    'Primary key matches the most common direct lookup (userId, postId, orderId).',
    'Composite index: equality fields first, then range / sort field.',
    'Feed table: partition by userId, sort by createdAt desc.',
    'Chat: partition by conversationId, sort by messageSequence or createdAt.',
    'Time-series: partition by entityId + time bucket to avoid unbounded partitions.',
    'Unique constraint: username, email, shortCode, idempotencyKey per user/order.',
  ],
  shardingNotes: [
    'Shard by userId when user-owned data dominates and cross-user queries are rare.',
    'Shard by objectId for uniform object lookup; add secondary indexes for owner queries.',
    'Avoid hot partitions: celebrity user, global counter, trending hashtag, current time bucket.',
    'Consistent hashing when nodes churn; directory service when placement needs control.',
    'Strong consistency: single leader / quorum — cost is latency and failover complexity.',
    'Eventual consistency: async events, reconciliation jobs, versioning, user-visible stale tolerance.',
    'Conflict resolution: last-write-wins, version vector, server timestamp, domain-specific merge.',
  ],
};

const RELIABILITY: SystemDesignContent['reliability'] = {
  failureMenu: [
    { failure: 'Duplicate write',    mitigation: 'idempotency key + unique constraint + dedupe table' },
    { failure: 'Partial failure',    mitigation: 'transactional boundary or saga with compensating action' },
    { failure: 'Queue backlog',      mitigation: 'autoscale workers, shed noncritical work, priority queues, backpressure' },
    { failure: 'Cache outage',       mitigation: 'bypass to DB under rate limit; warm critical keys; degrade features' },
    { failure: 'DB primary failure', mitigation: 'replica promotion + read-only mode + RPO/RTO statement' },
    { failure: 'Hot key',            mitigation: 'split key, add local cache, request coalescing, async fanout' },
    { failure: 'Thundering herd',    mitigation: 'jittered TTL, token bucket, single-flight lock, circuit breaker' },
    { failure: 'Data corruption',    mitigation: 'checksums, audit log, backups, restore drills, dual-write verification' },
  ],
  patterns: [
    { id: 'retry',                pattern: 'Retry',                handles: 'transient failure',      risk: 'duplicate side effects without idempotency' },
    { id: 'timeout',              pattern: 'Timeout',              handles: 'resource exhaustion',    risk: 'false failure if too aggressive' },
    { id: 'circuit-breaker',      pattern: 'Circuit breaker',      handles: 'downstream outage',      risk: 'degraded UX while open' },
    { id: 'bulkhead',             pattern: 'Bulkhead',             handles: 'failure containment',    risk: 'underutilized capacity' },
    { id: 'rate-limit',           pattern: 'Rate limit',           handles: 'overload + abuse',       risk: 'blocking legitimate spikes' },
    { id: 'graceful-degradation', pattern: 'Graceful degradation', handles: 'partial outage',         risk: 'silent feature loss' },
    { id: 'outbox',               pattern: 'Outbox',               handles: 'dual-write atomicity',   risk: 'extra publish latency' },
    { id: 'saga',                 pattern: 'Saga',                 handles: 'multi-service workflow', risk: 'compensation correctness' },
  ],
  seniorFraming: [
    'State SLO target and current attainment, not just availability adjectives.',
    'Name the error budget the choice consumes.',
    'Name blast radius (which users, which features, which region).',
    'Reference the runbook a responder would open.',
    'Show observability: dashboard, alerts, SLI definitions.',
    'State RPO/RTO so the recovery story has numbers.',
  ],
};

export const systemDesignContent: SystemDesignContent = {
  dashboard: {
    title: 'System Design Interview Field Guide',
    description:
      'Study the pressure-first thinking, the 45-minute round flow, capacity math, the components that earn their seat, and the failure modes that prove senior judgment.',
    boardLayoutCaption: 'The whiteboard layout an interviewer expects to see',
    timeline: ROUND_TIMELINE,
    pressureMenu: [
      'Users', 'Top actions', 'QPS', 'Latency',
      'Availability', 'Consistency', 'Retention', 'Regions',
    ],
    seniorPhrases: [
      'I will keep v1 simple and add this component only when scale math requires it.',
      'The cache helps p95 reads, but I need an invalidation or TTL story.',
      'This is eventually consistent; the user-visible stale window is acceptable because…',
      'The biggest unresolved trade-off is latency vs consistency.',
    ],
  },

  mentalModel: {
    thesis: 'Requirements create pressure. Pressure creates architecture.',
    forceComponentLinks: [
      { force: 'users',       component: 'cache' },
      { force: 'scale',       component: 'sharding' },
      { force: 'scale',       component: 'queue' },
      { force: 'latency',     component: 'cache' },
      { force: 'latency',     component: 'cdn' },
      { force: 'consistency', component: 'consensus' },
      { force: 'reliability', component: 'replication' },
      { force: 'reliability', component: 'multi-region' },
      { force: 'retention',   component: 'cold-storage' },
    ],
    earnItsSeatQuestions: [
      'Why does it exist?',
      'What state does it own?',
      'How does it scale?',
      'How does it fail?',
    ],
    pathBeforeInfraNote:
      'Draw one write path and one read path with verbs on the arrows BEFORE adding any infrastructure box.',
  },

  cheatsheet: {
    preflight: [
      'requirements', 'scale numbers', 'API', 'data model', 'write path',
      'read path', 'component reasons', 'failure story', 'trade-off close',
    ],
    decisionDeck: [
      {
        id: 'cache',
        eyebrow: 'Cache',
        trigger: 'read pressure or expensive recompute',
        move: 'cache-aside by default; state TTL, invalidation path, stampede control, and behavior when cache is down',
        watch: 'stale reads, hot keys, stampede, derived keys hard to invalidate',
      },
      {
        id: 'queue',
        eyebrow: 'Queue',
        trigger: 'slow or bursty side effects behind the write path',
        move: 'accept write, persist intent, publish job; idempotent worker with retry budget, DLQ, lag metric',
        watch: 'duplicate side effects, poison messages, unbounded backlog, user-visible freshness',
      },
      {
        id: 'storage-choice',
        eyebrow: 'Storage',
        trigger: 'a new entity has appeared on the board',
        move: 'name entity, primary key, secondary indexes, shard key, retention, and the query each index serves',
        watch: 'cross-shard joins, hot partitions, write amplification, unclear source of truth',
      },
      {
        id: 'cdn',
        eyebrow: 'CDN',
        trigger: 'global static or media reads',
        move: 'put media in object storage behind a CDN; name cache headers, purge path, and access control',
        watch: 'private content via CDN, cache poisoning, purge lag',
      },
      {
        id: 'search-index',
        eyebrow: 'Search',
        trigger: 'text, ranking, or filter queries against any entity',
        move: 'async index pipeline (CDC or stream); name freshness delay and reindex strategy',
        watch: 'using search as source of truth, stale results during reindex, permission filtering',
      },
      {
        id: 'stream',
        eyebrow: 'Stream',
        trigger: 'durable ordered event log with replay or multiple consumers',
        move: 'partition key + retention; name consumer group, lag metric, and replay strategy',
        watch: 'hot partitions, ordering across partitions, schema evolution',
      },
      {
        id: 'replication',
        eyebrow: 'Replication',
        trigger: 'availability + read scaling',
        move: 'primary + N replicas; name read-after-write strategy and failover RPO/RTO',
        watch: 'reads from stale replicas, split-brain on failover, lag spikes',
      },
      {
        id: 'idempotency',
        eyebrow: 'Idempotency',
        trigger: 'anywhere a request can be retried',
        move: 'idempotency key per logical operation; dedupe on the server before side effect',
        watch: 'idempotency window too short, key collisions across clients',
      },
    ],
    traps: [
      'component before requirement', 'cache without invalidation', 'queue without idempotency',
      'sharding without key', 'no pagination', 'no backpressure',
      'no hot-key answer', 'no observability',
    ],
  },

  roundFlow: {
    phases: ROUND_TIMELINE,
    usefulPhrases: [
      'I will keep v1 simple and add this component only when the scale math requires it.',
      'The key correctness risk here is duplicate writes, so I want an idempotency key.',
      'This cache improves p95 reads, but I need an invalidation or TTL story.',
      'This is eventually consistent; the user-visible stale window is acceptable because…',
      'If this becomes a hot-key problem, I would split by [key] or add request coalescing.',
      'The biggest unresolved trade-off is [latency vs consistency/cost/complexity].',
    ],
  },

  capacityMath: {
    formulas: [
      { label: 'Daily ops',         formula: 'DAU × actions/user/day' },
      { label: 'Avg QPS',           formula: 'daily ops / 86,400' },
      { label: 'Peak QPS',          formula: 'avg QPS × peak multiplier (typically 3–10×)' },
      { label: 'Raw storage/day',   formula: 'writes/day × avg object size' },
      { label: 'Storage footprint', formula: 'raw storage × replication × retention days' },
      { label: 'Bandwidth/sec',     formula: 'read QPS × avg response size' },
      { label: 'Cache memory',      formula: 'hot keys × avg cached value size × overhead (1.2–2)' },
    ],
    interpretations: [
      { threshold: '> 10k QPS',    implication: 'consider read replicas or a caching layer' },
      { threshold: '> 100 GB/day', implication: 'name a shard key and retention policy' },
      { threshold: '> 1 MB/s',     implication: 'consider CDN or object storage' },
      { threshold: '> 1M DAU',     implication: 'plan for hot partitions and regional placement' },
    ],
    sloRows: [
      { target: '99.9% (three nines)',  minutesPerMonth: '43.8 min/month', designChoice: 'single-region multi-AZ + health checks' },
      { target: '99.99% (four nines)',  minutesPerMonth: '4.38 min/month', designChoice: 'multi-AZ + fast failover + graceful degradation' },
      { target: '99.999% (five nines)', minutesPerMonth: '26 sec/month',   designChoice: 'multi-region active-active + consensus + chaos drills' },
    ],
  },

  buildingBlocks: BUILDING_BLOCKS,
  reliability: RELIABILITY,
};
