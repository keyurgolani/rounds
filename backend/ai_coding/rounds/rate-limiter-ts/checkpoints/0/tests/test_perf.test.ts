import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { RateLimiter } from '../../rateLimiter.ts';

// Correctness — passes against the naive starter.
test('basic allow / deny', () => {
  const rl = new RateLimiter(2, 1000);
  assert.equal(rl.allow(0), true);
  assert.equal(rl.allow(100), true);
  assert.equal(rl.allow(200), false);   // limit hit
  assert.equal(rl.allow(1100), true);   // earliest expired
});

test('rejected requests are not recorded', () => {
  const rl = new RateLimiter(1, 1000);
  assert.equal(rl.allow(0), true);
  assert.equal(rl.allow(100), false);   // rejected
  assert.equal(rl.allow(100), false);   // still rejected
  assert.equal(rl.allow(1001), true);   // first hit aged out
});

// Performance — fails against the naive O(n²) implementation. With a
// generous limit and wide window every hit accumulates in history;
// the naive .filter() rebuilds the full array on every call. The
// optimized solution does this in well under 500ms on commodity
// hardware (we measured ~3ms locally; the naive takes 10+ seconds).
test('handles 50k allow() calls under 500ms', () => {
  const rl = new RateLimiter(1_000_000, 10_000_000);
  const N = 50_000;
  const start = performance.now();
  for (let i = 0; i < N; i++) {
    rl.allow(i);
  }
  const elapsed = performance.now() - start;
  assert.ok(elapsed < 500, `expected < 500ms, took ${elapsed.toFixed(1)}ms`);
});
