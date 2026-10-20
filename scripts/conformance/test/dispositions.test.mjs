import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { parseFeatureDisposition, parseItemDisposition } from '../lib/vocabulary/dispositions.mjs';
import { FIXTURES, REPO_ROOT, readJson } from './helpers.mjs';

const { dispositions } = readJson(REPO_ROOT, 'contracts/vocabulary/terms.json');

describe('dispositions (DR-0001 G10)', () => {
  it('parses all 34 spec ledger dispositions into Preserve or Transform plus a qualifier', () => {
    const rows = readJson(FIXTURES, 'ledger-dispositions.json').rows;
    assert.equal(rows.length, 34);
    const parsed = rows.map((r) => ({ id: r.id, ...parseFeatureDisposition(r.disposition, dispositions) }));
    for (const p of parsed) {
      assert.equal(p.ok, true, p.id);
      assert.ok(['Preserve', 'Transform'].includes(p.value), p.id);
      assert.equal(p.requiresOwnerApproval, false, p.id);
    }
    const byId = Object.fromEntries(parsed.map((p) => [p.id, p]));
    assert.deepEqual([byId['CUR-01'].value, byId['CUR-01'].qualifier], ['Preserve', 'and harden']);
    assert.deepEqual([byId['CUR-18'].value, byId['CUR-18'].qualifier], ['Transform', 'without loss']);
    assert.deepEqual([byId['CUR-25'].value, byId['CUR-25'].qualifier], ['Preserve', 'only after containment and make reproducible']);
    assert.deepEqual([byId['INT-01'].value, byId['INT-01'].qualifier], ['Transform', null]);
    assert.equal(parsed.filter((p) => p.value === 'Preserve').length, 12);
    assert.equal(parsed.filter((p) => p.value === 'Transform').length, 22);
  });

  it('requires owner approval to retire, and rejects anything else', () => {
    const retire = parseFeatureDisposition('Retire with migration statement', dispositions);
    assert.deepEqual([retire.ok, retire.value, retire.requiresOwnerApproval], [true, 'Retire', true]);
    assert.equal(parseFeatureDisposition('Keep', dispositions).ok, false);
    assert.equal(parseFeatureDisposition('Preserved', dispositions).ok, false);
  });

  it('maps item dispositions and the catalog words for #155', () => {
    for (const v of ['migrate', 'archive', 'rebuild', 'reconcile', 'drop']) assert.equal(parseItemDisposition(v, dispositions).value, v);
    assert.equal(parseItemDisposition('drop', dispositions).requiresOwnerApproval, true);
    const bridge = parseItemDisposition('bridge', dispositions);
    assert.deepEqual([bridge.value, bridge.via], ['migrate', 'bridge']);
    assert.match(bridge.condition, /time-bounded adapter/);
    assert.equal(parseItemDisposition('quarantine', dispositions).value, 'archive');
    const retire = parseItemDisposition('retire', dispositions);
    assert.deepEqual([retire.value, retire.requiresOwnerApproval], ['drop', true]);
    assert.equal(parseItemDisposition('translate', dispositions).ok, false);
  });
});
