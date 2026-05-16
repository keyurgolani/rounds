import { describe, it, expect, beforeEach } from 'vitest';
import {
  compute, DEFAULT_INPUTS, readStored, writeStored,
} from '../system-design/pages/capacityMath';

const STORAGE_KEY = 'rounds:guide:capacity-math';

describe('capacityMath.compute', () => {
  it('derives avg QPS from DAU and actions/day', () => {
    const { avgQps } = compute({ dau: 86_400, actionsPerDay: 1, avgPayloadBytes: 1, peakMultiplier: 1 });
    expect(avgQps).toBeCloseTo(1, 5);
  });

  it('applies peak multiplier to peak QPS', () => {
    const out = compute({ dau: 86_400, actionsPerDay: 1, avgPayloadBytes: 1, peakMultiplier: 7 });
    expect(out.peakQps).toBeCloseTo(7, 5);
  });

  it('computes raw storage as dailyOps × avg payload', () => {
    const out = compute({ dau: 1_000, actionsPerDay: 10, avgPayloadBytes: 100, peakMultiplier: 1 });
    expect(out.rawStoragePerDayBytes).toBe(1_000_000);
  });

  it('computes bandwidth as avg QPS × payload', () => {
    const out = compute({ dau: 86_400, actionsPerDay: 1, avgPayloadBytes: 500, peakMultiplier: 1 });
    expect(out.bandwidthBytesPerSecond).toBeCloseTo(500, 5);
  });

  it('returns 0 for zero inputs without dividing by zero', () => {
    const out = compute({ dau: 0, actionsPerDay: 5, avgPayloadBytes: 100, peakMultiplier: 5 });
    expect(out.avgQps).toBe(0);
    expect(out.rawStoragePerDayBytes).toBe(0);
  });
});

describe('capacityMath persistence', () => {
  beforeEach(() => window.localStorage.removeItem(STORAGE_KEY));

  it('round-trips inputs through localStorage', () => {
    const sample = { dau: 1, actionsPerDay: 2, avgPayloadBytes: 3, peakMultiplier: 4 };
    writeStored(sample);
    expect(readStored()).toEqual(sample);
  });

  it('returns null when nothing is stored', () => {
    expect(readStored()).toBeNull();
  });

  it('returns null when the stored payload is malformed', () => {
    window.localStorage.setItem(STORAGE_KEY, '{"dau":"oops"}');
    expect(readStored()).toBeNull();
  });

  it('exposes DEFAULT_INPUTS', () => {
    expect(DEFAULT_INPUTS).toMatchObject({
      dau: 10_000_000,
      actionsPerDay: 5,
      avgPayloadBytes: 2_048,
      peakMultiplier: 5,
    });
  });
});
