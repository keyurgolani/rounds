// SPA gate reader (ROUNDS-00A-L01). backend/tests/test_gates.py checks
// that gateRegistry.json matches the runner's registry; this checks the
// resolution rules and where the values come from.

import { afterEach, describe, expect, it, vi } from 'vitest';
import registry from '../gateRegistry.json';
import { gateValue, readGateEnv, resolveGate } from '../gates';

type ConfigWindow = { __ROUNDS_CONFIG__?: Record<string, string | undefined> };

afterEach(() => {
  delete (window as unknown as ConfigWindow).__ROUNDS_CONFIG__;
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe('resolveGate', () => {
  it('defaults keep signups open', () => {
    expect(resolveGate('SIGNUPS', {})).toEqual({ value: 'enabled', source: 'default' });
  });

  it.each(['disabled', ' Disabled ', 'DISABLED'])('an allowed value wins: %s', (raw) => {
    expect(resolveGate('SIGNUPS', { ROUNDS_GATE_SIGNUPS: raw })).toEqual({ value: 'disabled', source: 'env' });
  });

  it.each(['true', 'invalid', 'on', 'en abled'])('any other value closes the gate: %s', (raw) => {
    expect(resolveGate('SIGNUPS', { ROUNDS_GATE_SIGNUPS: raw })).toEqual({ value: 'disabled', source: 'invalid' });
  });

  it('an empty gate counts as unset', () => {
    expect(resolveGate('SIGNUPS', { ROUNDS_GATE_SIGNUPS: '' })).toEqual({ value: 'enabled', source: 'default' });
  });

  it.each(['true', 'TRUE', '1', 'yes'])('the VITE alias applies while the gate is unset: %s', (truthy) => {
    expect(resolveGate('SIGNUPS', { VITE_DISABLE_SIGNUPS: truthy })).toEqual({ value: 'disabled', source: 'alias' });
  });

  it.each(['false', '0', 'no', ''])('a falsy alias changes nothing: %s', (falsy) => {
    expect(resolveGate('SIGNUPS', { VITE_DISABLE_SIGNUPS: falsy }).value).toBe('enabled');
  });

  it('the SPA ignores the PocketBase alias', () => {
    expect(resolveGate('SIGNUPS', { ROUNDS_DISABLE_SIGNUPS: 'true' }).value).toBe('enabled');
  });

  it('a set gate wins over its alias', () => {
    expect(resolveGate('SIGNUPS', { ROUNDS_GATE_SIGNUPS: 'enabled', VITE_DISABLE_SIGNUPS: 'true' })).toEqual({
      value: 'enabled',
      source: 'env',
    });
  });

  it('the registry the SPA ships has only gates it reads', () => {
    expect(Object.keys(registry.gates)).toEqual(['SIGNUPS']);
    expect(registry.prefix).toBe('ROUNDS_GATE_');
  });
});

describe('readGateEnv', () => {
  it('prefers runtime-config.js and falls back to the build, key by key', () => {
    vi.stubEnv('VITE_DISABLE_SIGNUPS', 'true');
    vi.stubEnv('ROUNDS_GATE_SIGNUPS', 'enabled');
    (window as unknown as ConfigWindow).__ROUNDS_CONFIG__ = { ROUNDS_GATE_SIGNUPS: 'disabled' };
    const env = readGateEnv();
    expect(env.ROUNDS_GATE_SIGNUPS).toBe('disabled');
    expect(env.VITE_DISABLE_SIGNUPS).toBe('true');
    expect(gateValue('SIGNUPS', env)).toBe('disabled');
  });

  it('reads only the keys the registry names', () => {
    (window as unknown as ConfigWindow).__ROUNDS_CONFIG__ = { ROUNDS_GATE_SIGNUPS: 'disabled', OTHER: 'x' };
    expect(Object.keys(readGateEnv()).sort()).toEqual(['ROUNDS_GATE_SIGNUPS', 'VITE_DISABLE_SIGNUPS']);
  });
});

describe('signupConfig', () => {
  async function load() {
    vi.resetModules();
    return (await import('../../auth/signupConfig')).signupConfig;
  }

  it('keeps signups on by default', async () => {
    vi.stubEnv('VITE_DISABLE_SIGNUPS', 'false');
    expect((await load()).disabled).toBe(false);
  });

  it('still honors VITE_DISABLE_SIGNUPS from the build or runtime config', async () => {
    vi.stubEnv('VITE_DISABLE_SIGNUPS', 'true');
    expect((await load()).disabled).toBe(true);
    vi.stubEnv('VITE_DISABLE_SIGNUPS', 'false');
    (window as unknown as ConfigWindow).__ROUNDS_CONFIG__ = { VITE_DISABLE_SIGNUPS: 'true' };
    expect((await load()).disabled).toBe(true);
  });

  it('follows ROUNDS_GATE_SIGNUPS from runtime-config.js over the alias', async () => {
    (window as unknown as ConfigWindow).__ROUNDS_CONFIG__ = {
      VITE_DISABLE_SIGNUPS: 'true',
      ROUNDS_GATE_SIGNUPS: 'enabled',
    };
    expect((await load()).disabled).toBe(false);
    (window as unknown as ConfigWindow).__ROUNDS_CONFIG__ = { ROUNDS_GATE_SIGNUPS: 'disabled' };
    expect((await load()).disabled).toBe(true);
  });
});
