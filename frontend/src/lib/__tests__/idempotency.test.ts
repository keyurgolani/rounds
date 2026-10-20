import { describe, expect, it } from 'vitest';
import { UUID_V7_PATTERN, mintIdempotencyKey } from '../idempotency';

describe('mintIdempotencyKey', () => {
  it('mints RFC 9562 UUIDv7 keys', () => {
    for (let i = 0; i < 50; i++) {
      expect(mintIdempotencyKey()).toMatch(UUID_V7_PATTERN);
    }
  });

  it('puts the millisecond time in the first 48 bits', () => {
    const now = Date.parse('2026-10-20T12:00:00.123Z');
    const key = mintIdempotencyKey(now);
    const ms = parseInt(key.replace(/-/g, '').slice(0, 12), 16);
    expect(ms).toBe(now);
  });

  it('sorts by creation time', () => {
    const earlier = mintIdempotencyKey(1_700_000_000_000);
    const later = mintIdempotencyKey(1_700_000_000_001);
    expect(earlier < later).toBe(true);
  });

  it('sets the version and variant bits over any random bytes', () => {
    const allOnes = (n: number) => new Uint8Array(n).fill(0xff);
    const allZeros = (n: number) => new Uint8Array(n);
    expect(mintIdempotencyKey(0, allOnes)).toBe('00000000-0000-7fff-bfff-ffffffffffff');
    expect(mintIdempotencyKey(0, allZeros)).toBe('00000000-0000-7000-8000-000000000000');
  });

  it('mints a different key every time', () => {
    const keys = new Set(Array.from({ length: 200 }, () => mintIdempotencyKey(1_700_000_000_000)));
    expect(keys.size).toBe(200);
  });
});
