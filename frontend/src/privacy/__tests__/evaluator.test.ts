// The privacy evaluator against the shared vectors (ROUNDS-14-L01).
// backend/tests/test_privacy_evaluator.py runs the same vector files, so
// both evaluators answer every case the same way. The vectors and policy
// files are the copies scripts/conformance/run.mjs --write keeps beside the
// evaluator.

import { describe, expect, it } from 'vitest';
import {
  MAX_CODE_POINTS, POLICY, PURPOSES, SECRET_PATTERNS, VERSIONS, classifyDestination, descendants, detectSecret, evaluateEgress,
  evaluateRetention, evaluateSink, formatNetwork, parsePrivateEndpoints,
  type Consent, type Endpoint, type Json, type Registry,
} from '../evaluator';

interface Args {
  field_id: string; sink: string; context?: Record<string, unknown>;
  purpose: string; field_ids: string[]; endpoint?: Endpoint; location?: string; consent?: Consent;
  row_id: string; value?: Json; anchor: string;
  host: string; port: number; addresses: string[]; settings?: Record<string, unknown>;
  pieces: (string | string[])[];
}
interface Vector { id: string; call: string; args: Args; registryPatch?: Record<string, object>; expect: Record<string, unknown> | null }
interface Suite { suite: string; cases: Vector[] }

const suites = Object.values(import.meta.glob<Suite>('../vectors/*.json', { eager: true, import: 'default' }))
  .sort((a, b) => (a.suite < b.suite ? -1 : 1));

function registry(patch: Record<string, object>): Registry {
  const reg = JSON.parse(JSON.stringify(PURPOSES)) as Registry;
  for (const p of reg.purposes) Object.assign(p, JSON.parse(JSON.stringify(patch[p.id] ?? {})));
  return reg;
}

const text = (pieces: (string | string[])[]) => pieces.map((p) => (Array.isArray(p) ? p.join('') : p)).join('');

function call(v: Vector): unknown {
  const a = v.args;
  switch (v.call) {
    case 'evaluate_sink':
      return evaluateSink(a.field_id, a.sink, a.context);
    case 'evaluate_egress':
      return evaluateEgress(a.purpose, a.field_ids, a.endpoint, a.location, a.consent, a.context,
        v.registryPatch ? registry(v.registryPatch) : undefined);
    case 'evaluate_retention':
      return evaluateRetention(a.row_id, a.value, a.anchor, a.context);
    case 'classify_destination':
      return classifyDestination(a.host, a.port, a.addresses, a.settings);
    case 'detect_secret':
      return detectSecret(text(a.pieces));
    case 'parse_private_endpoints':
      try {
        return { entries: parsePrivateEndpoints(a.value as string).map((e) => ({ network: formatNetwork(e.network), port: e.port })) };
      } catch (err) {
        return { error: (err as Error).message };
      }
    default:
      throw new Error(`unknown call ${v.call}`);
  }
}

describe.each(suites.map((s) => [s.suite, s] as const))('%s vectors', (_suite, suite) => {
  it.each(suite.cases.map((c) => [c.id, c] as const))('%s', (_id, v) => {
    const got = call(v) as Record<string, unknown> | null;
    const want = v.expect;
    if (want === null || got === null) {
      expect(got).toEqual(want);
      return;
    }
    if ('error' in want) {
      expect(got).toHaveProperty('error');
      expect(String(got.error)).toContain(String(want.error));
      return;
    }
    for (const [key, value] of Object.entries(want)) expect(got[key], key).toEqual(value);
  });
});

describe('privacy evaluator', () => {
  it('has a matrix vector for every class and sink', () => {
    const matrix = suites.find((s) => s.suite === 'matrix') as Suite;
    const ids = new Set(matrix.cases.map((c) => c.id));
    for (const cell of POLICY.matrix.cells) expect(ids.has(cell.id), cell.id).toBe(true);
    expect(POLICY.matrix.cells).toHaveLength(40);
  });

  it.each(SECRET_PATTERNS.fixtures.map((s) => [s.pattern, s] as const))('flags the %s fixture by offsets only', (_p, sample) => {
    const secret = sample.parts.join('');
    const got = detectSecret(sample.before + secret + sample.after);
    expect(got?.code).toBe('secret-detected');
    const start = Array.from(sample.before).length;
    expect(got?.findings).toContainEqual({ pattern: sample.pattern, start, end: start + Array.from(secret).length });
    expect(JSON.stringify(got)).not.toContain(secret);
  });

  it.each(SECRET_PATTERNS.nearMisses.map((s) => [s.pattern, s] as const))('passes the %s near miss', (_p, sample) => {
    const got = detectSecret(sample.before + sample.parts.join('') + sample.after);
    expect((got?.findings ?? []).filter((f) => f.pattern === sample.pattern)).toEqual([]);
  });

  it('has a fixture and a near miss for every pattern', () => {
    const ids = new Set(SECRET_PATTERNS.patterns.map((p) => p.id));
    expect(new Set(SECRET_PATTERNS.fixtures.map((s) => s.pattern))).toEqual(ids);
    expect(new Set(SECRET_PATTERNS.nearMisses.map((s) => s.pattern))).toEqual(ids);
  });

  it('names every policy version', () => {
    expect(VERSIONS).toEqual({ privacy: 'privacy@1', retention: 'retention@1', redaction: 'redaction@1', consent: 'consent@1' });
  });

  it('never repeats a refused entry in its message', () => {
    const settings = suites.find((s) => s.suite === 'settings') as Suite;
    for (const v of settings.cases.filter((c) => c.expect && 'error' in c.expect)) {
      const value = v.args.value as string;
      let message = '';
      try {
        parsePrivateEndpoints(value);
      } catch (err) {
        message = (err as Error).message;
      }
      expect(message, v.id).not.toBe('');
      for (const item of value.split(',').map((x) => x.trim()).filter(Boolean)) expect(message, v.id).not.toContain(item);
    }
  });

  it('keeps map order and the caller\'s column for the entries below an id', () => {
    const got = descendants('pb:resume_variants.data#/personalInfo');
    expect(got[0].startsWith('pb:resume_variants.data#/personalInfo/')).toBe(true);
    expect(got).toContain('pb:resume_variants.data#/personalInfo/email');
    expect(descendants('pb:ai_coding_rounds.checkpoints').slice(0, 2)).toEqual([
      'pb:ai_coding_rounds.checkpoints#/*/*/hidden_files', 'pb:ai_coding_rounds.checkpoints#/*/*/test_command']);
    expect(descendants('storage:pocketbase_auth')).toEqual([]);
    expect(descendants('pb:offers.id')).toEqual([]);
  });
});

describe('detectSecret at its limits', () => {
  const CAP = MAX_CODE_POINTS;
  const fill = (unit: string, n = CAP) => unit.repeat(Math.ceil(n / unit.length) + 1).slice(0, n);
  // Texts that made the earlier JWT and PEM patterns quadratic, and the other
  // runs a pattern could backtrack over, each at the cap.
  const adversarial: [string, () => string][] = [
    ['jwt-heads', () => fill('eyJ')],
    ['jwt-long-runs', () => fill(` eyJ${'A'.repeat(8200)}`)],
    ['pem-headers', () => fill('-----BEGIN ')],
    ['pem-words', () => `-----BEGIN ${fill('A ', CAP - 11)}`],
    ['bearer-spaces', () => `Bearer${fill(' ', CAP - 6)}`],
    ['short-keys', () => fill('sk-AAAAAAAAAAAAAAAAAAA ')],
  ];
  const groq = SECRET_PATTERNS.fixtures.find((s) => s.pattern === 'groq-key') as { parts: string[] };
  const secret = groq.parts.join('');

  it.each(adversarial)('stays linear on %s', (_name, make) => {
    const text = make();
    expect(text).toHaveLength(CAP);
    const started = performance.now();
    detectSecret(text);
    expect(performance.now() - started).toBeLessThan(2000);
  });

  it('reads up to the cap and refuses past it', () => {
    expect(detectSecret(' '.repeat(CAP - secret.length) + secret)).toEqual({
      code: 'secret-detected', findings: [{ pattern: 'groq-key', start: CAP - secret.length, end: CAP }],
    });
    expect(detectSecret(' '.repeat(CAP) + secret)).toEqual({ code: 'text-too-long', findings: [] });
    expect(detectSecret('🔑'.repeat(CAP - secret.length) + secret)?.code).toBe('secret-detected');
    expect(detectSecret('🔑'.repeat(CAP) + secret)).toEqual({ code: 'text-too-long', findings: [] });
  });

  it('counts many offsets in code points in one pass', () => {
    const unit = `🔑 ${secret} `;
    const text = unit.repeat(20_000);
    const started = performance.now();
    const got = detectSecret(text);
    expect(performance.now() - started).toBeLessThan(2000);
    const width = Array.from(unit).length;
    expect(got?.findings).toHaveLength(20_000);
    expect(got?.findings[19_999]).toEqual({ pattern: 'groq-key', start: 19_999 * width + 2, end: 19_999 * width + 2 + secret.length });
  });

  it.each([[42], [['text']], [{ text: 'a' }]])('refuses %j, which isn\'t text', (value) => {
    expect(detectSecret(value as unknown as string)).toEqual({ code: 'input-invalid', findings: [] });
  });

  it('passes no text', () => {
    expect(detectSecret(null)).toBeNull();
    expect(detectSecret('')).toBeNull();
  });
});
