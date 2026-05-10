import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { RateLimiter } from '../../rateLimiter.ts';

test('boundary: hit exactly at now-window edge expires', () => {
  const rl = new RateLimiter(1, 1000);
  assert.equal(rl.allow(0), true);
  // now=1000 means now-window=0; the original hit at t=0 is at the
  // boundary. Per the spec ("previous windowMs"), it should have aged
  // out by t=1000 (strictly greater-than).
  assert.equal(rl.allow(1000), true);
});

test('many distinct hits within window', () => {
  const rl = new RateLimiter(100, 1000);
  for (let i = 0; i < 100; i++) {
    assert.equal(rl.allow(i), true);
  }
  assert.equal(rl.allow(150), false);   // 101st within 150ms — denied
});

test('zero limit denies everything', () => {
  const rl = new RateLimiter(0, 1000);
  assert.equal(rl.allow(0), false);
  assert.equal(rl.allow(500), false);
  assert.equal(rl.allow(2000), false);
});
