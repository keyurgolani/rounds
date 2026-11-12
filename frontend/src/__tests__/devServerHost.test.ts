// The Vite dev and preview servers listen on loopback unless VITE_DEV_HOST
// names another address (vite.config.ts). The dev container sets it to
// 0.0.0.0 and publishes the port on the host's 127.0.0.1 only.

import type { UserConfig } from 'vite';
import { afterEach, describe, expect, it, vi } from 'vitest';

// Vite's esbuild can't load under jsdom. defineConfig returns its argument
// and the React plugin has no part in the bind, so both are stand-ins here
// and the config file itself is what runs.
vi.mock('vite', () => ({ defineConfig: (config: UserConfig) => config }));
vi.mock('@vitejs/plugin-react', () => ({ default: () => [] }));

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

// vite.config.ts, evaluated fresh with VITE_DEV_HOST set to `value`;
// undefined leaves it unset.
async function loadConfig(value: string | undefined): Promise<UserConfig> {
  vi.stubEnv('VITE_DEV_HOST', value);
  vi.resetModules();
  return (await import('../../vite.config')).default;
}

describe('the dev server host', () => {
  it('is 127.0.0.1 when VITE_DEV_HOST is unset', async () => {
    const config = await loadConfig(undefined);
    expect(config.server?.host).toBe('127.0.0.1');
    expect(config.preview?.host).toBe('127.0.0.1');
  });

  it.each(['', '   '])('is 127.0.0.1 when VITE_DEV_HOST is blank (%j)', async (value) => {
    const config = await loadConfig(value);
    expect(config.server?.host).toBe('127.0.0.1');
    expect(config.preview?.host).toBe('127.0.0.1');
  });

  it('follows VITE_DEV_HOST when it is set', async () => {
    const config = await loadConfig('0.0.0.0');
    expect(config.server?.host).toBe('0.0.0.0');
    expect(config.preview?.host).toBe('0.0.0.0');
  });
});
