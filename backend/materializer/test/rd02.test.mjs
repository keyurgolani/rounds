// RD-02 sub-cases for the materializer (ROUNDS-00A-L04), from
// tests/conformance/rd_02/, which #8 (ROUNDS-00A-L08) adopts. Each file
// declares one hostile input and the outcome it must get: ineligible with a
// reason, or a snapshot whose markup carries none of the listed text and
// passes the output checks.

import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import { describe, it } from 'node:test';

import { checkMarkup, materialize } from '../dist/materialize.mjs';

const DIR = new URL('../../../tests/conformance/rd_02/', import.meta.url);
const files = readdirSync(DIR).filter((name) => name.endsWith('.json')).sort();
const REASONS = ['design_out_of_domain', 'data_malformed', 'data_too_large', 'markup_unsafe'];

describe('RD-02 sub-cases', () => {
  it('ships one file per sub-case', () => {
    assert.ok(files.length >= 15, `${files.length} files`);
  });

  for (const file of files) {
    const subcase = JSON.parse(readFileSync(new URL(file, DIR), 'utf8'));
    it(`${subcase.id}: ${subcase.title}`, () => {
      assert.deepEqual(Object.keys(subcase).sort(), ['closing_leaf', 'expected', 'fixture', 'id', 'input', 'target', 'title']);
      assert.equal(subcase.fixture, 'RD-02');
      assert.equal(file, `${subcase.id.replace(/^RD-02\./, '')}.json`);
      assert.equal(subcase.closing_leaf, 'ROUNDS-00A-L04');
      assert.equal(subcase.target, 'legacy-snapshot-materializer');
      assert.deepEqual(Object.keys(subcase.input).sort(), ['data', 'design', 'template_id']);

      const result = materialize(structuredClone(subcase.input));
      assert.deepEqual(materialize(structuredClone(subcase.input)), result, 'the same input gets the same answer');
      const { expected } = subcase;
      if (expected.status === 'ineligible') {
        assert.ok(REASONS.includes(expected.reason), expected.reason);
        assert.equal(result.status, 'ineligible');
        assert.equal(result.reason, expected.reason);
        return;
      }
      assert.equal(expected.status, 'ok');
      assert.equal(result.status, 'ok', result.reason);
      assert.equal(result.template_id, expected.template_id);
      assert.equal(result.template_fallback, expected.template_fallback);
      assert.deepEqual(checkMarkup(result.markup), { ok: true });
      const lower = result.markup.toLowerCase();
      for (const text of expected.markup_excludes) {
        assert.ok(!lower.includes(text.toLowerCase()), `markup holds ${text}`);
      }
      for (const key of expected.data_excludes ?? []) {
        assert.ok(!JSON.stringify(result.data).includes(key), `data holds ${key}`);
      }
    });
  }
});
