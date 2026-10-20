export type CapacityInputs = {
  dau: number;
  actionsPerDay: number;
  avgPayloadBytes: number;
  peakMultiplier: number;
};

export type CapacityOutputs = {
  avgQps: number;
  peakQps: number;
  rawStoragePerDayBytes: number;
  bandwidthBytesPerSecond: number;
};

export const DEFAULT_INPUTS: CapacityInputs = {
  dau: 10_000_000,
  actionsPerDay: 5,
  avgPayloadBytes: 2_048,
  peakMultiplier: 5,
};

export function compute(inputs: CapacityInputs): CapacityOutputs {
  const dailyOps = inputs.dau * inputs.actionsPerDay;
  const avgQps = dailyOps / 86_400;
  const peakQps = avgQps * inputs.peakMultiplier;
  const rawStoragePerDayBytes = dailyOps * inputs.avgPayloadBytes;
  const bandwidthBytesPerSecond = avgQps * inputs.avgPayloadBytes;
  return { avgQps, peakQps, rawStoragePerDayBytes, bandwidthBytesPerSecond };
}

const KIB = 1024;
const MIB = 1024 * KIB;
const GIB = 1024 * MIB;

export function formatBytes(bytes: number): string {
  if (bytes >= GIB) return `${(bytes / GIB).toFixed(1)} GB`;
  if (bytes >= MIB) return `${(bytes / MIB).toFixed(1)} MB`;
  if (bytes >= KIB) return `${(bytes / KIB).toFixed(1)} KB`;
  return `${Math.round(bytes)} B`;
}

export function formatPerSecond(bytesPerSecond: number): string {
  return `${formatBytes(bytesPerSecond)}/s`;
}

export function formatRate(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)} M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)} k`;
  return value.toFixed(1);
}

const STORAGE_KEY = 'rounds:guide:capacity-math';

export function readStored(): CapacityInputs | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<CapacityInputs>;
    if (
      typeof parsed.dau === 'number' &&
      typeof parsed.actionsPerDay === 'number' &&
      typeof parsed.avgPayloadBytes === 'number' &&
      typeof parsed.peakMultiplier === 'number'
    ) {
      return parsed as CapacityInputs;
    }
  } catch {
    return null;
  }
  return null;
}

export function writeStored(inputs: CapacityInputs) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(inputs));
}
