// Renders DR-0004's two documents (ROUNDS-02-L01). Generated: edit the JSON,
// then run node scripts/conformance/run.mjs --write.
//
// docs/decisions/DR-0004-canonical-database.md, the ADR, renders the record,
// the ERD's written part, and the benchmark receipt, so its SHA-256 changes
// only when one of them does. docs/decisions/DR-0004-erd.md renders the
// generated ERD, which every migration change regenerates.

import { DECISIONS_PATH, ERD_DOC_PATH, ERD_PATH, SNAPSHOT_PATH, isPlanned, renderMermaid } from './erd.mjs';
import { RECEIPT_PATH } from './benchmark.mjs';

const cell = (v) => String(v ?? '').replace(/\|/g, '\\|').replace(/\n/g, ' ');
const table = (head, rows) => [`| ${head.join(' | ')} |`, `| ${head.map(() => '---').join(' | ')} |`, ...rows.map((r) => `| ${r.map(cell).join(' | ')} |`)].join('\n');
const list = (items) => items.map((x) => `- ${x}`).join('\n');
const num = (v, unit) => (v === null || v === undefined ? 'n/a' : `${typeof v === 'number' ? Math.round(v * 100) / 100 : v} ${unit}`.trim());
const loads = (l) => (Array.isArray(l) ? l.map((x) => Math.round(x * 10) / 10).join(', ') : 'n/a');
const indexText = (i) => `${i.unique ? 'unique ' : ''}(${i.columns.join(', ')})${i.partial ? ', partial' : ''}`;
const partitionText = (p) => (p ? `${p.field} (${p.kind}, ${p.onAccountDelete})` : 'none');

function decisionSection(d) {
  const out = [`### ${d.id}. ${d.title}`, '', d.decision, ''];
  out.push(table(['Concern', 'Store', 'Owning process', 'Owning leaf', 'Status'], [[d.concern, d.store, d.process, d.owningLeaf, d.status]]), '');
  out.push('**Alternatives**', '', list(d.alternatives.map((a) => `${a.option}: ${a.reason}`)), '');
  out.push('**Failure modes**', '', list(d.failureModes), '');
  out.push('**Limits**', '', list(d.limits), '');
  out.push(`**Consequences.** ${d.consequences}`, '');
  out.push(`**Migration.** ${d.migrationImpact}`, '');
  out.push(`**Rollback.** ${d.rollbackImpact}`, '');
  if (d.dedupe) out.push(`**Dedupe.** ${d.dedupe}`, '');
  out.push(`Sources: ${d.sources.join('; ')}.`, '');
  return out.join('\n');
}

function bytesRow(receipt) {
  const measured = receipt.seedPlan?.bytesSampleMeasured;
  const ex = (receipt.extrapolations || []).filter((e) => e.target === 'restore_rto');
  const sample = measured ? `${Math.round((measured / 1024 ** 3) * 100) / 100} GiB measured at 1 account` : 'none measured';
  if (!ex.length) return `${sample}; nothing extrapolated`;
  return `${sample}; ${ex.map((e) => `${Math.round(e.targetBytes / 1000 ** 3)} GB extrapolated at the measured ${Math.round(e.throughputBytesPerSecond / 1000 ** 2)} MB/s`).join(', ')} (${ex[0].formula})`;
}

function benchmarkSection(receipt, record) {
  if (!receipt) return 'No receipt yet.';
  const p = receipt.profile || {};
  const hw = p.hardware || {};
  const k8s = p.k8sLimits || {};
  const out = [
    `Synthetic data only. Receipt \`${RECEIPT_PATH}\` (revision ${receipt.revision}), ${receipt.generatedAt}, result **${receipt.result}**.`,
    '',
    table(['Profile', 'Value'], [
      ['Hardware', `${hw.cpu}, ${hw.cores} cores, ${Math.round((hw.memoryBytes || 0) / 1024 ** 3)} GiB, ${hw.os}, ${hw.storage}`],
      ['PocketBase', `${p.pocketbase?.version} (binary sha256 \`${String(p.pocketbase?.binarySha256).slice(0, 12)}...\`; Dockerfile pin at the run ${p.pocketbase?.dockerfilePin?.PB_VERSION})`],
      ['k8s limits', `${k8s.cpuLimit} CPU, ${k8s.memoryLimit} memory, ${k8s.replicas} replica, ${k8s.strategy}, ${k8s.pvc} PVC`],
      ['Emulation', p.emulation?.note],
      ['Machine', p.sharedMachine],
      ['Load average', `${loads(p.loadAverageAtStart)} at the start and ${loads(p.loadAverageAtEnd)} at the end (1, 5, and 15 minutes)`],
      ['Seed', `the scale floor per account (spec 2020-2028), fraction ${receipt.seedPlan?.fraction}, at ${Object.keys(receipt.scales || {}).join(' and ')} accounts${record?.benchmark?.seedReading ? `; ${record.benchmark.seedReading}` : ''}`],
      ['Bytes', bytesRow(receipt)],
    ]),
    '',
    table(['Target', 'Limit', 'Value', 'Basis', 'Result', 'Detail', 'Consequence'],
      (receipt.targets || []).map((t) => [`${t.target} (${t.spec})`, `${t.limit} ${t.unit}`, num(t.value, t.unit), t.basis, t.result, t.detail, t.consequence || ''])),
    '',
  ];
  const rows = [];
  for (const [n, s] of Object.entries(receipt.scales || {})) {
    const cp = s.steady?.checkpoint;
    rows.push([`${n} account(s)`, num(s.steady?.queueMs?.p99, 'ms'), num(s.steady?.holdMs?.p50, 'ms'), num(s.steady?.holdMs?.p99, 'ms'),
      num(s.steady?.relayLagMs?.p95, 'ms'), num(s.steady?.readYourWritesMs?.p99, 'ms'), num(s.steady?.writeAmplification, 'rows'),
      num(Object.keys(s.sweep || {}).length ? Math.max(...Object.values(s.sweep).map((x) => x.perSecond || 0)) : null, '/s'), num(s.freeze?.seconds, 's'),
      cp?.ms !== undefined ? `${num(cp.ms, 'ms')}; commands in flight took up to ${num(cp.clientMsDuring?.max, 'ms')}` : 'n/a',
      num((s.samplers?.walMaxBytes || 0) / 1024 ** 2, 'MiB'), num((s.samplers?.rssMaxBytes || 0) / 1024 ** 2, 'MiB')]);
  }
  out.push(table(['Scale', 'Lock queue p99', 'Lock hold p50', 'Lock hold p99', 'Relay lag p95', 'Read-your-writes p99', 'Rows per command', 'Peak commands', 'Freeze',
    'Checkpoint under load', 'WAL max', 'RSS max'], rows), '');
  const defaults = Object.entries(receipt.rollbackDefaults || {}).filter(([, d]) => d && typeof d === 'object');
  if (defaults.length) {
    out.push(`**Rollback defaults (${receipt.rollbackDefaults.source}).** Each rests on a target and carries its basis, so an extrapolated pass reads as one.`, '');
    out.push(table(['Default', 'Met', 'Basis', 'Target', 'Detail'], defaults.map(([k, d]) => [k, d.met ? 'yes' : 'no', d.basis, d.target || 'none',
      [d.detail, d.owner ? `owner ${d.owner}` : ''].filter(Boolean).join('; ')])));
  }
  return out.join('\n');
}

// The ERD's written part: what DR-0004 ratifies.
function writtenErd(decisions) {
  const sem = decisions.semantics || {};
  const values = [
    ...Object.entries(sem.onDelete || {}).map(([k, v]) => ['On delete', k, v]),
    ...Object.entries(sem.onAccountDelete || {}).map(([k, v]) => ['On account delete', k, v]),
    ...Object.entries(sem.merge || {}).map(([k, v]) => ['Merge', k, v]),
  ];
  const out = [
    `The ERD's written fields are this record's, in \`${DECISIONS_PATH}\`, and are rendered here. \`${ERD_PATH}\` joins them to PocketBase's own schema, \`${SNAPSHOT_PATH}\` from a native \`migrate up\`, and \`${ERD_DOC_PATH}\` draws the result. A PR that adds or changes a migration regenerates the snapshot and both files (DB_ERD_STALE until it does), and needs a revision of this record only when it changes a written field.`,
    '',
    table(['Field', 'Value', 'Meaning'], values),
    '',
    table(['Store', 'Kind', 'Location', 'Canonical', 'Backup'], decisions.stores.map((s) => [s.id, s.kind, s.location, s.canonical ? 'yes' : 'no', s.backup])),
    '',
  ];
  const planned = decisions.entities.filter(isPlanned);
  out.push('### Planned and held tables', '', table(['Table', 'Status', 'Owning leaf', 'Scope', 'Partition', 'Indexes', 'Writers', 'Purge'], planned.map((e) => [
    e.id, e.status, e.owningLeaf, e.scope, partitionText(e.partition), (e.indexes || []).map(indexText).join('; '), e.writers, e.purge])), '');
  const noted = planned.filter((e) => e.note);
  if (noted.length) out.push(list(noted.map((e) => `**${e.id}.** ${e.note}`)), '');
  out.push('### Written fields of the live tables', '', 'The snapshot gives each live table its partition relation, indexes, and rules; these fields are written.', '');
  for (const g of decisions.groups) {
    const members = decisions.entities.filter((e) => !isPlanned(e) && e.group === g.id);
    if (!members.length) continue;
    out.push(`#### ${g.title}`, '', table(['Table', 'Scope', 'Rows', 'Writers', 'Purge'], members.map((e) => [
      e.id + (e.partition ? ` (partition ${partitionText(e.partition)})` : ''), e.scope, (e.rows || []).join(', '), e.writers, e.purge])), '');
    const notes = members.filter((e) => e.note);
    if (notes.length) out.push(list(notes.map((e) => `**${e.id}.** ${e.note}`)), '');
  }
  const byMerge = new Map();
  for (const r of decisions.relations) byMerge.set(r.merge, [...(byMerge.get(r.merge) || []), r.id]);
  out.push('### Merge behavior', '', table(['Merge', 'Relations'], [...byMerge.entries()].map(([m, ids]) => [m, ids.join(', ')])), '');
  const byNote = new Map();
  for (const r of decisions.relations.filter((x) => x.note)) byNote.set(r.note, [...(byNote.get(r.note) || []), r.id]);
  if (byNote.size) out.push(list([...byNote.entries()].map(([note, ids]) => `${ids.join(', ')}: ${note}`)), '');
  return out.join('\n');
}

export function renderAdr(record, decisions, receipt) {
  const pb = record.pocketbase || {};
  const out = [
    `# ${record.id}: ${record.title}`,
    '',
    `<!-- Generated from docs/decisions/DR-0004-canonical-database.json, ${DECISIONS_PATH}, and ${RECEIPT_PATH} by node scripts/conformance/run.mjs --write. Edit those, not this file. -->`,
    '',
    table(['Record', 'Status', 'Owner', 'Approver', 'Approval', 'Leaf'], [[`${record.id}@${record.revision}`, record.status, record.owner, record.approver || 'pending review',
      record.approvalRef ? `PR #${record.approvalRef.pr}` : 'not ratified: not citable', record.leaf]]),
    '',
    record.context,
    '',
    '## The ten decisions',
    '',
    table(['Decision', 'Concern', 'Store', 'Owning process', 'Owning leaf'], record.decisions.map((d) => [`${d.id}. ${d.title}`, d.concern, d.store, d.process, d.owningLeaf])),
    '',
    ...record.decisions.map(decisionSection),
    '## Alternatives A to D',
    '',
    table(['Alternative', 'Runner write path', 'Image build', 'Bindings', 'nginx change', 'Verdict'], record.alternativesEvaluated.map((a) => [`${a.id}. ${a.name}`, a.runnerWritePath, a.imageBuild, a.bindings, a.nginxChange, `${a.verdict}: ${a.reason}`])),
    '',
    '## Rejected options',
    '',
    table(['Option', 'Why', 'Source'], record.rejected.map((r) => [r.option, r.reason, r.source])),
    '',
    '## Benchmark',
    '',
    benchmarkSection(receipt, record),
    '',
    '## PocketBase version',
    '',
    `Line **${pb.line}**, pinned ${pb.pinAtRatification} at ratification. Decision: **${pb.decision}**. ${pb.summary || ''}`,
    '',
    `The counts below are at \`${String(pb.countedAt).slice(0, 7)}\`.`,
    '',
    table(['Break site', 'Where', 'Count', 'Upstream', 'Note'], (pb.breakSites || []).map((b) => [b.id, b.site, b.count ?? '', b.upstream, b.note || ''])),
    '',
    `**Strategy.** ${pb.strategy}`,
    '',
    `**Freeze window.** ${pb.freezeWindow}`,
    '',
    `**Rollback boundary.** ${pb.rollbackBoundary}`,
    '',
    '**Triggers for the port to another line**',
    '',
    list(pb.triggers || []),
    '',
    ...(pb.benchmark ? [`**Benchmarked version.** ${pb.benchmark}`, ''] : []),
    ...(pb.snapshot ? [`**Schema snapshot.** ${pb.snapshot}`, ''] : []),
    '## ERD',
    '',
    writtenErd(decisions),
  ];
  out.push('## Identifier rules', '', list(record.identifiers.map((x) => `**${x.id}.** ${x.rule} (${x.owner})`)), '');
  out.push('## Invariants', '', table(['Invariant', 'Where at 62d4eae', 'Row', 'Mechanism', 'Owner'], record.invariants.map((i) => [i.detail, i.site, i.row, [].concat(i.mechanism).join(' + '), i.owningLeaf])), '');
  out.push('## Containment stores', '', table(['Store', 'Leaf', 'Disposition', 'Detail'], record.containment.map((c) => [c.store, c.leaf, c.disposition + (c.owningLeaf ? `, ${c.owningLeaf}` : ''), c.detail])), '');
  out.push('## Storage plan', '', table(['Store', 'Location', 'Growth at the floor', 'Rows per command', 'Compaction', 'Lock budget', 'Sizing'],
    record.storagePlan.map((s) => [s.store, s.location, s.growthAtFloor, s.writeAmplification, s.compaction, s.lockBudget, s.sizing])), '');
  out.push('## Credentials', '', table(['Credential', 'Holder', 'Disposition', 'Leaf'], record.credentials.map((c) => [c.credential, c.holder, c.disposition, c.leaf])), '');
  out.push('## Changed authorities', '', table(['Authority', 'Disposition', 'After', 'Rollback'], record.changes.map((c) => [c.authority, c.disposition, c.dependsOn.join(', '), c.rollback])), '');
  out.push('## Export gate', '', table(['Item', 'Producer'], record.exportGate.map((g) => [g.item, [].concat(g.producer).join(', ')])), '', record.foundationExemption, '');
  out.push('## AI, exposure, and security', '', `**AI.** ${record.catalogRule}`, '', `**Exposure.** ${record.exposure}`, '');
  out.push(table(['Consequence', 'Statement'], Object.entries(record.securityConsequences).map(([k, v]) => [k, v])), '');
  out.push('## Baseline facts', '', table(['Fact', 'At 62d4eae', 'On next'], record.baselineFacts.map((b) => [b.id, b.citation, b.now])), '');
  if ((record.deferred || []).length) out.push('## Deferred', '', list(record.deferred.map((d) => `**${d.item}.** ${d.detail}`)), '');
  out.push('## Versioning and supersession', '', record.versioning, '', record.supersession, '', `Consumers: ${record.consumers.join(', ')}.`, '');
  return `${out.join('\n').replace(/\n{3,}/g, '\n\n').trim()}\n`;
}

// The generated ERD: the written part joined to the live schema.
export function renderErdDoc(erd) {
  const live = erd.entities.filter((e) => e.status === 'live');
  const out = [
    '# DR-0004 ERD, generated',
    '',
    `<!-- Generated from ${ERD_PATH} by node scripts/conformance/run.mjs --write. Edit ${DECISIONS_PATH} for the written fields, and regenerate ${SNAPSHOT_PATH} with harness/bench/schema_dump.py for the rest. -->`,
    '',
    `Every collection at snapshot \`${String(erd.snapshot.revision).slice(0, 7)}\` (PocketBase ${erd.snapshot.pocketbaseVersion}), ${live.filter((e) => e.kind === 'collection').length} in all, the ${live.filter((e) => e.kind === 'system-table').length} system tables, the ${erd.entities.length - live.length} planned or held tables DR-0004 places, and ${erd.relations.length} relations. The written fields (group, scope, rows, writers, purge, a text partition, merge, notes, and the planned tables) are DR-0004's and change only with a revision of it; the rest comes from the snapshot, and the PR that changes a migration regenerates this file. Delete behavior is PocketBase's own, measured on the snapshot's native run: ${Object.entries(erd.semantics.measured).map(([k, v]) => `${k} ${v}`).join(', ')}.`,
    '',
    table(['Store', 'Kind', 'Location', 'Canonical', 'Backup'], erd.stores.map((s) => [s.id, s.kind, s.location, s.canonical ? 'yes' : 'no', s.backup])),
    '',
  ];
  for (const g of erd.groups) {
    const members = erd.entities.filter((e) => e.group === g.id);
    if (!members.length) continue;
    out.push(`## ${g.title}`, '', renderMermaid(erd, g.id), '');
    out.push(table(['Entity', 'Status', 'Scope', 'Partition', 'Indexed', 'Writers', 'On account delete'], members.map((e) => [
      e.id, e.status + (e.owningLeaf ? ` (${e.owningLeaf})` : ''), e.scope, partitionText(e.partition),
      e.partition?.kind === 'self' ? 'primary key' : e.indexes ? `${e.indexes.length}${e.partitionIndexed ? ', partition first' : ''}` : '', e.writers, e.purge])), '');
  }
  out.push('## Relations', '', table(['Relation', 'To', 'Cardinality', 'Required', 'On delete', 'Merge', 'Authorized by'],
    erd.relations.map((r) => [r.id + (r.status === 'live' ? '' : ` (${r.status})`), r.to, r.cardinality, r.required ? 'yes' : 'no', r.onDelete, r.merge, r.authorization])), '');
  return `${out.join('\n').replace(/\n{3,}/g, '\n\n').trim()}\n`;
}
