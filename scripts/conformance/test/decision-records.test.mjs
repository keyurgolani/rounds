import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { after, describe, it } from 'node:test';
import { createContext } from '../lib/context.mjs';
import * as records from '../rules/decision-records.mjs';
import { REPO_ROOT, cleanup, codes, ctxFor, editJson, fixture, readJson, writeJson } from './helpers.mjs';

const DR = 'docs/decisions/DR-0001-product-vocabulary.json';
const SCHEMA = 'docs/decisions/decision-record.schema.json';
const DR2 = 'docs/decisions/DR-0002-authority-matrix.json';

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
    assert.equal(dr.revision, 2);
    assert.equal(dr.supersedes, 'DR-0001@1');
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
    only(run(editDr((r) => { r.revision = 2; r.supersedes = null; delete r.supersessionReason; })), 'DR_SUPERSEDES_INVALID');
    only(run(editDr((r) => { r.revision = 2; r.supersedes = 'DR-0001@1'; delete r.supersessionReason; })), 'DR_SUPERSEDES_INVALID');
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
    only(run(editDr((r) => { r.id = 'DR-0007'; r.supersedes = 'DR-0007@1'; })), 'DR_RECORD_INVALID');
    const dir = fixture((d) => fs.copyFileSync(path.join(d, DR), path.join(d, 'docs/decisions/DR-0001-copy.json')));
    only(run(dir), 'DR_DUPLICATE_ID');
  });

  it('checks affected packages against contracts/authority/packages.json by id or service', () => {
    assert.deepEqual(run(fixture()), []);
    assert.deepEqual(run(editDr((r) => { r.affectedPackages = ['account', 'Career Profile Service', 'read-model']; })), []);
    const unknown = run(editDr((r) => { r.affectedPackages.push('Billing Service'); }));
    only(unknown, 'DR_UNKNOWN_PACKAGE');
    assert.match(unknown[0].message, /"Billing Service" is neither a package id nor a service/);
  });

  // packages.json is governed by DR-0002, so these fixtures make DR-0002 a draft.
  const withPackages = (write) => fixture((d) => {
    editJson(d, DR2, (r) => { r.status = 'draft'; r.approvalRef = null; delete r.ratifiedOn; });
    write(d);
  });

  it('reports an unreadable packages.json once instead of failing every package', () => {
    const findings = run(withPackages((d) => fs.writeFileSync(path.join(d, 'contracts/authority/packages.json'), '{ not json')));
    only(findings, 'DR_UNKNOWN_PACKAGE');
    assert.equal(findings.length, 1);
    assert.match(findings[0].message, /packages\.json is not valid JSON: .*; affected packages are unchecked$/);
  });

  it('skips the package check before packages.json exists', () => {
    const dir = withPackages((d) => {
      fs.rmSync(path.join(d, 'contracts/authority/packages.json'));
      editJson(d, DR, (r) => { r.affectedPackages = ['Not A Package Yet']; });
    });
    assert.deepEqual(run(dir), []);
    const known = withPackages((d) => writeJson(d, 'contracts/authority/packages.json', { packages: [{ id: 'not-a-package-yet', service: 'Not A Package Yet' }] }));
    only(run(known), 'DR_UNKNOWN_PACKAGE');
  });
});

describe('decision records: DR-0002', () => {
  const editDr2 = (fn) => fixture((d) => editJson(d, DR2, fn));

  it('records one owner, the authority boundary, alternatives, consequences, packages, versioning, supersession, and OD-1 to OD-5', () => {
    const dr = readJson(REPO_ROOT, DR2);
    assert.equal(dr.owner, 'Product Architecture');
    assert.equal(dr.authorityBoundary, 'contracts/authority/matrix.json');
    assert.equal(dr.affectedPackages.length, 18);
    assert.ok(dr.affectedPackages.includes('Provider Gateway'));
    assert.deepEqual(dr.prerequisites, ['ROUNDS-01-L01']);
    assert.match(dr.versioning, /DR-0002@<revision>:<row-id>/);
    assert.ok(dr.supersession.length > 0);
    assert.deepEqual(dr.decisions.filter((d) => /^OD-\d$/.test(d.id)).map((d) => d.id), ['OD-1', 'OD-2', 'OD-3', 'OD-4', 'OD-5']);
    for (const d of dr.decisions) {
      assert.ok(d.alternatives.length >= 1, d.id);
      for (const k of ['consequences', 'migrationImpact', 'rollbackImpact']) assert.ok(d[k].length > 0, `${d.id} ${k}`);
    }
  });

  it('fails DR-0002 without an owner, boundary, alternative, consequence, or supersession rule', () => {
    only(run(editDr2((r) => { delete r.owner; })), 'DR_RECORD_INCOMPLETE');
    only(run(editDr2((r) => { delete r.authorityBoundary; })), 'DR_RECORD_INCOMPLETE');
    only(run(editDr2((r) => { r.decisions[0].alternatives = []; })), 'DR_RECORD_INCOMPLETE');
    only(run(editDr2((r) => { delete r.decisions[1].consequences; })), 'DR_RECORD_INCOMPLETE');
    only(run(editDr2((r) => { delete r.supersession; })), 'DR_RECORD_INCOMPLETE');
  });
});
