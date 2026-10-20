import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { after, describe, it } from 'node:test';
import { createContext } from '../lib/context.mjs';
import * as records from '../rules/decision-records.mjs';
import { REPO_ROOT, cleanup, codes, ctxFor, editJson, fixture, readJson, writeJson } from './helpers.mjs';

const DR = 'docs/decisions/DR-0001-product-vocabulary.json';
const SCHEMA = 'docs/decisions/decision-record.schema.json';

after(cleanup);

const run = (dir) => records.check(dir, ctxFor(dir));
const only = (findings, code) => assert.deepEqual(codes(findings), [code], JSON.stringify(findings, null, 2));
const editDr = (fn) => fixture((dir) => editJson(dir, DR, fn));

describe('decision records: repository', () => {
  it('passes DR-0001 as committed', () => {
    assert.deepEqual(records.check(REPO_ROOT, createContext(REPO_ROOT, { base: 'none' })), []);
  });

  it('records one owner, the authority boundary, packages, versioning, supersession, and security consequences', () => {
    const dr = readJson(REPO_ROOT, DR);
    assert.equal(dr.owner, 'Product Architecture');
    assert.equal(dr.authorityBoundary, 'contracts/vocabulary/terms.json');
    assert.equal(dr.affectedPackages.length, 17);
    assert.ok(dr.versioning.includes('vocabulary@<n> is DR-0001@<n>'));
    assert.ok(dr.supersession.length > 0);
    assert.deepEqual(Object.keys(dr.securityConsequences).sort(), ['account', 'privacy', 'publicBoundary', 'secret']);
    assert.equal(dr.status, 'ratified');
    assert.equal(dr.revision, 1);
    assert.ok(Number.isInteger(dr.approvalRef.pr));
    assert.deepEqual(dr.prerequisites, []);
  });

  it('gives each gap decision alternatives, consequences, migration impact, and rollback impact', () => {
    const dr = readJson(REPO_ROOT, DR);
    const gaps = dr.decisions.filter((d) => /^G\d+$/.test(d.id)).map((d) => d.id);
    assert.deepEqual(gaps, ['G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8', 'G9', 'G10', 'G11', 'G12']);
    for (const d of dr.decisions) {
      assert.ok(d.alternatives.length >= 1, d.id);
      for (const k of ['consequences', 'migrationImpact', 'rollbackImpact']) assert.ok(d[k].length > 0, `${d.id} ${k}`);
    }
  });
});

describe('decision records: architecture', () => {
  it('fails DR_RECORD_INCOMPLETE without an owner', () => {
    only(run(editDr((r) => { delete r.owner; })), 'DR_RECORD_INCOMPLETE');
  });

  it('fails DR_RECORD_INCOMPLETE without any other required field', () => {
    const schema = readJson(REPO_ROOT, SCHEMA);
    for (const field of schema.required) {
      const findings = run(editDr((r) => { delete r[field]; }));
      assert.ok(codes(findings).includes('DR_RECORD_INCOMPLETE'), `${field}: ${JSON.stringify(codes(findings))}`);
    }
  });

  it('fails a ratified record without an approver or approval reference', () => {
    only(run(editDr((r) => { r.approver = ''; })), 'DR_RECORD_INCOMPLETE');
    only(run(editDr((r) => { r.approvalRef = null; })), 'DR_RECORD_INCOMPLETE');
    assert.deepEqual(run(editDr((r) => { r.status = 'draft'; r.approver = ''; r.approvalRef = null; })), []);
  });

  it('fails a decision without alternatives or a consequence', () => {
    only(run(editDr((r) => { r.decisions[0].alternatives = []; })), 'DR_RECORD_INCOMPLETE');
    only(run(editDr((r) => { delete r.decisions[3].rollbackImpact; })), 'DR_RECORD_INCOMPLETE');
    only(run(editDr((r) => { delete r.securityConsequences.publicBoundary; })), 'DR_RECORD_INCOMPLETE');
  });

  it('fails VOCAB_UNRESOLVED_REF on an unknown or rejected leaf', () => {
    only(run(editDr((r) => { r.consumers.push('ROUNDS-99-L99'); })), 'VOCAB_UNRESOLVED_REF');
    const rejected = run(editDr((r) => { r.consumers.push('ROUNDS-26-L05'); }));
    only(rejected, 'VOCAB_UNRESOLVED_REF');
    assert.match(rejected[0].message, /rejected/);
    only(run(editDr((r) => { r.prerequisites = ['ROUNDS-04-L05']; })), 'VOCAB_UNRESOLVED_REF');
    assert.deepEqual(run(editDr((r) => { r.prerequisites = ['ROUNDS-00A-L01/S0']; })), []);
  });

  it('fails when the governed file changes after approval', () => {
    const dir = fixture((d) => editJson(d, 'contracts/vocabulary/terms.json', (t) => { t.description = `${t.description} Edited.`; }));
    only(run(dir), 'DR_APPROVAL_STALE');
  });

  it('checks supersession', () => {
    only(run(editDr((r) => { r.revision = 2; })), 'DR_SUPERSEDES_INVALID');
    only(run(editDr((r) => { r.revision = 2; r.supersedes = 'DR-0001@1'; })), 'DR_SUPERSEDES_INVALID');
    assert.deepEqual(run(editDr((r) => { r.revision = 2; r.supersedes = 'DR-0001@1'; r.supersessionReason = 'Owner changed G6.'; })), []);
    only(run(editDr((r) => { r.revision = 2; r.supersedes = 'DR-0001@3'; r.supersessionReason = 'x'; })), 'DR_SUPERSEDES_INVALID');
  });

  it('reserves DR-0002 and DR-0003 for ROUNDS-01-L02 and ROUNDS-01-L03', () => {
    const dir = fixture((d) => {
      const dr = readJson(d, DR);
      writeJson(d, 'docs/decisions/DR-0002-authority-matrix.json', { ...dr, id: 'DR-0002', leaf: 'ROUNDS-02-L01', approvalRef: null, status: 'draft', approver: '' });
    });
    only(run(dir), 'DR_NUMBER_RESERVED');
  });

  it('rejects a file name that disagrees with the id, and duplicate ids', () => {
    only(run(editDr((r) => { r.id = 'DR-0007'; })), 'DR_RECORD_INVALID');
    const dir = fixture((d) => fs.copyFileSync(path.join(d, DR), path.join(d, 'docs/decisions/DR-0001-copy.json')));
    only(run(dir), 'DR_DUPLICATE_ID');
  });

  it('checks affected packages once contracts/authority/packages.json exists', () => {
    const dr = readJson(REPO_ROOT, DR);
    const known = fixture((d) => writeJson(d, 'contracts/authority/packages.json', { packages: dr.affectedPackages.map((name) => ({ id: name.toLowerCase().replace(/[^a-z]+/g, '-'), service: name })) }));
    assert.deepEqual(run(known), []);
    const missing = fixture((d) => writeJson(d, 'contracts/authority/packages.json', { packages: dr.affectedPackages.slice(1).map((name) => ({ service: name })) }));
    only(run(missing), 'DR_UNKNOWN_PACKAGE');
  });
});
