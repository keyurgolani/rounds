// Conformance rule for the privacy policy (ROUNDS-14-L01, DR-0005).
//
// check:    contracts/privacy/ against its schema; the matrix and lifecycle
//           rules; one class or visibility per field, no looser than its
//           ROUNDS-01-L02 floor; coverage of every live collection field,
//           the named JSON paths, every browser storage key family, and
//           every stored definition property; the purpose registry and the
//           provider-call scan; the violation register and its detectors;
//           version pins; the decision record; loosening against the base
//           branch; and synthetic fixtures only. With --review it also checks
//           the spec tables word for word.
// generate: the copies in backend/app/privacy/ and frontend/src/privacy/,
//           docs/privacy-retention.md, and the settings section of
//           docs/configuration.md.

import fs from 'node:fs';
import path from 'node:path';
import { createContext, finding } from '../lib/context.mjs';
import { analyze } from '../lib/privacy/checks.mjs';
import { CONFIG_DOC_PATH, DOC_PATH, POLICY_PATH, copies } from '../lib/privacy/files.mjs';
import { renderConfigSection, renderPrivacyDoc, pendingEnforcement, spliceConfig } from '../lib/privacy/render.mjs';

export const id = 'privacy';
export const owningLeaf = 'ROUNDS-14-L01';
export const description = 'Privacy classes, sink policy, and numeric retention: schema, coverage, floors, purposes, the register, pins, the record, and loosening';

const memo = new WeakMap();

function run(ctx) {
  if (memo.has(ctx)) return memo.get(ctx);
  const result = analyze(ctx);
  // Without its markers the settings section would silently stop regenerating.
  if (!ctx.exists(CONFIG_DOC_PATH) || spliceConfig(ctx.read(CONFIG_DOC_PATH), '') === null) {
    result.findings.push(finding('PRIVACY_DOC_MARKERS', CONFIG_DOC_PATH, 1, 'needs its privacy-settings:begin and privacy-settings:end markers, so --write keeps the settings table'));
  }
  if (ctx.reviewRoot) result.findings.push(...checkSpec(ctx, result.A.P));
  memo.set(ctx, result);
  return result;
}

// --review: the policy's tables equal the spec's lines.
function checkSpec(ctx, P) {
  const policy = P.policy;
  if (!policy) return [];
  const specPath = path.join(ctx.reviewRoot, policy.spec.path);
  let lines;
  try {
    lines = fs.readFileSync(specPath, 'utf8').replace(/\r\n/g, '\n').split('\n');
  } catch {
    return [finding('PRIVACY_SPEC_MISMATCH', POLICY_PATH, 1, `can't read the spec at ${specPath}`)];
  }
  const cell = (cells) => `| ${cells.join(' | ')} |`;
  const want = [cell(policy.matrix.columns), ...policy.matrix.rows.map((r) => cell(r.cells))];
  const got = lines.slice(policy.spec.matrixLines[0] - 1, policy.spec.matrixLines[1]).filter((l) => !/^\|\s*---/.test(l));
  const out = [];
  if (want.join('\n') !== got.join('\n')) out.push(finding('PRIVACY_SPEC_MISMATCH', POLICY_PATH, 1, `the matrix differs from spec lines ${policy.spec.matrixLines.join('-')}`));
  const wantL = [cell(policy.lifecycle.columns), ...policy.lifecycle.rows.map((r) => cell(r.cells))];
  const gotL = lines.slice(policy.spec.lifecycleLines[0] - 1, policy.spec.lifecycleLines[1]).filter((l) => !/^\|\s*---/.test(l));
  if (wantL.join('\n') !== gotL.join('\n')) out.push(finding('PRIVACY_SPEC_MISMATCH', POLICY_PATH, 1, `the lifecycle table differs from spec lines ${policy.spec.lifecycleLines.join('-')}`));
  const deletion = lines.slice(policy.spec.deletionLines[0] - 1, policy.spec.deletionLines[1]).join(' ').replace(/\s+/g, ' ').trim();
  if (deletion !== policy.accountDeletion.text) out.push(finding('PRIVACY_SPEC_MISMATCH', POLICY_PATH, 1, `the account deletion text differs from spec lines ${policy.spec.deletionLines.join('-')}`));
  return out;
}

export function settingsRows(policy) {
  const rows = new Map([...policy.lifecycle.rows, ...policy.lifecycle.decided].map((r) => [r.id, r]));
  return policy.operatorSettings.map((s) => {
    if (s.kind === 'days') {
      const spec = rows.get(s.row).retention;
      return { name: s.name, allowed: `${spec.range[0]} to ${spec.range[1]} days`, default: `${spec.default}`, meaning: s.meaning };
    }
    return { name: s.name, allowed: 'comma-separated entries', default: 'empty', meaning: s.meaning };
  });
}

export function check(repoRoot, ctx = createContext(repoRoot)) {
  return run(ctx).findings;
}

export function generate(repoRoot, ctx = createContext(repoRoot)) {
  const { A } = run(ctx);
  const P = A.P;
  const out = [...copies(ctx)];
  if (P.policy) {
    out.push({ path: DOC_PATH, content: renderPrivacyDoc(P, { fieldCount: P.fieldMap?.entries?.length }) });
    if (ctx.exists(CONFIG_DOC_PATH)) {
      const text = ctx.read(CONFIG_DOC_PATH);
      const spliced = spliceConfig(text, renderConfigSection(P, settingsRows(P.policy)));
      if (spliced !== null) out.push({ path: CONFIG_DOC_PATH, content: spliced });
    }
  }
  return out;
}

export function summary(repoRoot, ctx = createContext(repoRoot)) {
  const { A, findings } = run(ctx);
  const P = A.P;
  if (!P.policy) return ['policy unreadable'];
  const lines = [];
  lines.push(`versions: ${P.policy.versions.map((v) => `${v.id}@${v.current}`).join(', ')}; decision record ${P.policy.decisionRecord}${A.record ? ` (${A.record.record.status})` : ' missing'}`);
  const purposes = P.purposes?.purposes || [];
  const byStatus = ['legacy', 'current', 'retired'].map((s) => `${purposes.filter((p) => p.status === s).length} ${s}`).join(', ');
  lines.push(`purposes: ${purposes.length} (${byStatus}); provider call references scanned: ${(A.callRefs || []).filter((r) => r.kind === 'helper').length}`);
  const schema = A.schema;
  lines.push(`field map: ${P.fieldMap?.entries?.length ?? 0} ids; live schema ${schema ? `${schema.collections.length} collections, ${schema.collections.reduce((n, c) => n + c.fields.length, 0)} fields from ${schema.files.length} migrations` : 'unread'}; ${A.storage ? A.storage.families.size : 0} storage key families; ${(A.definitions?.used || []).reduce((n, d) => n + d.properties.length, 0)} definition properties`);
  const unclassified = findings.filter((f) => f.code === 'FIELD_UNCLASSIFIED').length;
  lines.push(`unclassified: ${unclassified} (must be 0)`);
  const open = (P.violations?.entries || []).filter((v) => v.status === 'open');
  const byOwner = new Map();
  for (const v of open) byOwner.set(v.owner, [...(byOwner.get(v.owner) || []), v.id]);
  lines.push(`register: ${open.length} open (${[...byOwner].map(([o, ids]) => `${o} ${ids.join('+')}`).join(', ')}), ${(P.violations?.entries || []).length - open.length} closed`);
  const pending = pendingEnforcement(P.policy);
  lines.push(`enforcement pending: ${pending.length} rows and blocks without a test that reads the policy value`);
  return lines;
}
