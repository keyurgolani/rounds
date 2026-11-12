// Renders docs/decisions/DR-0004-canonical-database.md from the record, the
// ERD, and the benchmark receipt (ROUNDS-02-L01). Generated: edit the JSON,
// then run node scripts/conformance/run.mjs --write.

import { renderMermaid } from './erd.mjs';

const cell = (v) => String(v ?? '').replace(/\|/g, '\\|').replace(/\n/g, ' ');
const table = (head, rows) => [`| ${head.join(' | ')} |`, `| ${head.map(() => '---').join(' | ')} |`, ...rows.map((r) => `| ${r.map(cell).join(' | ')} |`)].join('\n');
const list = (items) => items.map((x) => `- ${x}`).join('\n');
const num = (v, unit) => (v === null || v === undefined ? 'n/a' : `${typeof v === 'number' ? Math.round(v * 100) / 100 : v} ${unit}`.trim());

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

function benchmarkSection(receipt) {
  if (!receipt) return 'No receipt yet.';
  const p = receipt.profile || {};
  const hw = p.hardware || {};
  const k8s = p.k8sLimits || {};
  const out = [
    `Synthetic data only. Receipt \`contracts/database/benchmark.json\`, ${receipt.generatedAt}, result **${receipt.result}**.`,
    '',
    table(['Profile', 'Value'], [
      ['Hardware', `${hw.cpu}, ${hw.cores} cores, ${Math.round((hw.memoryBytes || 0) / 1024 ** 3)} GiB, ${hw.os}, ${hw.storage}`],
      ['PocketBase', `${p.pocketbase?.version} (binary sha256 \`${String(p.pocketbase?.binarySha256).slice(0, 12)}...\`; Dockerfile pin at the run ${p.pocketbase?.dockerfilePin?.PB_VERSION})`],
      ['k8s limits', `${k8s.cpuLimit} CPU, ${k8s.memoryLimit} memory, ${k8s.replicas} replica, ${k8s.strategy}, ${k8s.pvc} PVC`],
      ['Emulation', p.emulation?.note],
      ['Machine', p.sharedMachine],
      ['Seed', `the scale floor per account (spec 2020-2028), fraction ${receipt.seedPlan?.fraction}, at ${Object.keys(receipt.scales || {}).join(' and ')} accounts`],
      ['Bytes', `${Math.round((receipt.seedPlan?.bytesSampleMeasured || 0) / 1024 ** 3)} GiB measured at 1 account; 10 GB per account extrapolated`],
    ]),
    '',
    table(['Target', 'Limit', 'Value', 'Basis', 'Result', 'Detail', 'Consequence'],
      (receipt.targets || []).map((t) => [`${t.target} (${t.spec})`, `${t.limit} ${t.unit}`, num(t.value, t.unit), t.basis, t.result, t.detail, t.consequence || ''])),
    '',
  ];
  const rows = [];
  for (const [n, s] of Object.entries(receipt.scales || {})) {
    rows.push([`${n} account(s)`, num(s.steady?.queueMs?.p99, 'ms'), num(s.steady?.holdMs?.p50, 'ms'), num(s.steady?.holdMs?.p99, 'ms'),
      num(s.steady?.relayLagMs?.p95, 'ms'), num(s.steady?.readYourWritesMs?.p99, 'ms'), num(s.steady?.writeAmplification, 'rows'),
      num(Math.max(...Object.values(s.sweep || {}).map((x) => x.perSecond || 0)), '/s'), num(s.freeze?.seconds, 's'),
      num((s.samplers?.walMaxBytes || 0) / 1024 ** 2, 'MiB'), num((s.samplers?.rssMaxBytes || 0) / 1024 ** 2, 'MiB')]);
  }
  out.push(table(['Scale', 'Lock queue p99', 'Lock hold p50', 'Lock hold p99', 'Relay lag p95', 'Read-your-writes p99', 'Rows per command', 'Peak commands', 'Freeze', 'WAL max', 'RSS max'], rows));
  return out.join('\n');
}

export function renderAdr(record, erd, receipt) {
  const pb = record.pocketbase || {};
  const out = [
    `# ${record.id}: ${record.title}`,
    '',
    `<!-- Generated from ${'docs/decisions/DR-0004-canonical-database.json'}, contracts/database/erd.json, and contracts/database/benchmark.json by node scripts/conformance/run.mjs --write. Edit those, not this file. -->`,
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
    benchmarkSection(receipt),
    '',
    '## PocketBase version',
    '',
    `Pinned **${pb.pin}**. Decision: **${pb.decision}**. ${pb.summary || ''}`,
    '',
    table(['Break site', 'Where', 'Count', 'Upstream', 'Note'], (pb.breakSites || []).map((b) => [b.id, b.site, b.count ?? '', b.upstream, b.note || ''])),
    '',
    `**Strategy.** ${pb.strategy}`,
    '',
    `**Freeze window.** ${pb.freezeWindow}`,
    '',
    `**Rollback boundary.** ${pb.rollbackBoundary}`,
    '',
    '**Triggers for the major-line port**',
    '',
    list(pb.triggers || []),
    '',
    ...(pb.benchmark ? [`**Benchmarked version.** ${pb.benchmark}`, ''] : []),
    '## ERD',
    '',
    `Every collection at snapshot \`${String(erd.snapshot.revision).slice(0, 7)}\` (PocketBase ${erd.snapshot.pocketbaseVersion}), the system tables, and the platform tables and stores this record places. Delete behavior is PocketBase's own, measured: ${Object.entries(erd.semantics.measured).map(([k, v]) => `${k} ${v}`).join(', ')}.`,
    '',
    table(['Store', 'Kind', 'Location', 'Canonical', 'Backup'], erd.stores.map((s) => [s.id, s.kind, s.location, s.canonical ? 'yes' : 'no', s.backup])),
    '',
  ];
  for (const g of erd.groups) {
    const members = erd.entities.filter((e) => e.group === g.id);
    if (!members.length) continue;
    out.push(`### ${g.title}`, '', renderMermaid(erd, g.id), '');
    out.push(table(['Entity', 'Status', 'Scope', 'Partition', 'Indexed', 'Writers', 'On account delete'], members.map((e) => [
      e.id, e.status + (e.owningLeaf ? ` (${e.owningLeaf})` : ''), e.scope, e.partition ? `${e.partition.field} (${e.partition.kind}, ${e.partition.onAccountDelete})` : 'none',
      e.indexes ? `${e.indexes.length}${e.partitionIndexed ? ', partition first' : ''}` : '', e.writers, e.purge])), '');
  }
  out.push('### Relations', '', table(['Relation', 'To', 'Cardinality', 'Required', 'On delete', 'Merge', 'Authorized by'],
    erd.relations.map((r) => [r.id + (r.status === 'live' ? '' : ` (${r.status})`), r.to, r.cardinality, r.required ? 'yes' : 'no', r.onDelete, r.merge, r.authorization])), '');
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
  out.push('## Versioning and supersession', '', record.versioning, '', record.supersession, '', `Consumers: ${record.consumers.join(', ')}.`, '');
  return `${out.join('\n').replace(/\n{3,}/g, '\n\n').trim()}\n`;
}
