// The frontend image's entrypoint script (ROUNDS-00A-L01) writes
// runtime-config.js from the container environment. Gates pass through
// as lowercase words only, so nothing else reaches the page.

import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { runInNewContext } from 'node:vm';
import { afterEach, describe, expect, it } from 'vitest';

const SCRIPT = resolve(__dirname, '../../../docker-entrypoint.d/10-runtime-config.sh');

const dirs: string[] = [];

afterEach(() => {
  for (const dir of dirs.splice(0)) rmSync(dir, { recursive: true, force: true });
});

function render(env: Record<string, string>) {
  const dir = mkdtempSync(join(tmpdir(), 'rounds-runtime-config-'));
  dirs.push(dir);
  const target = join(dir, 'runtime-config.js');
  const log = execFileSync('sh', [SCRIPT], {
    env: { PATH: process.env.PATH ?? '/usr/bin:/bin', ROUNDS_RUNTIME_CONFIG_PATH: target, ...env },
    encoding: 'utf8',
  });
  const source = readFileSync(target, 'utf8');
  const sandbox: { window: { __ROUNDS_CONFIG__?: Record<string, string> } } = { window: {} };
  runInNewContext(source, sandbox);
  return { config: sandbox.window.__ROUNDS_CONFIG__!, log, source };
}

describe('10-runtime-config.sh', () => {
  it('writes only the existing flags when no gate is set', () => {
    const { config, log } = render({});
    expect(config).toEqual({
      VITE_DISABLE_SIGNUPS: 'false',
      VITE_OAUTH_GOOGLE_ENABLED: 'false',
      VITE_OAUTH_GITHUB_ENABLED: 'false',
    });
    expect(log).toContain('no ROUNDS_GATE_* set');
  });

  it('keeps the existing flags working', () => {
    const { config } = render({ VITE_DISABLE_SIGNUPS: 'TRUE', VITE_OAUTH_GITHUB_ENABLED: 'yes' });
    expect(config.VITE_DISABLE_SIGNUPS).toBe('true');
    expect(config.VITE_OAUTH_GITHUB_ENABLED).toBe('true');
    expect(config.VITE_OAUTH_GOOGLE_ENABLED).toBe('false');
  });

  it('passes each set gate through as a trimmed lowercase word and logs it', () => {
    const { config, log } = render({ ROUNDS_GATE_SIGNUPS: ' Disabled ', ROUNDS_GATE_ENFORCE_QUOTA: 'observe' });
    expect(config.ROUNDS_GATE_SIGNUPS).toBe('disabled');
    expect(config.ROUNDS_GATE_ENFORCE_QUOTA).toBe('observe');
    expect(log).toContain('runtime-config: ROUNDS_GATE_SIGNUPS=disabled');
    expect(log).toContain('runtime-config: ROUNDS_GATE_ENFORCE_QUOTA=observe');
  });

  it('leaves out empty gates and names that are not gate names', () => {
    const { config } = render({ ROUNDS_GATE_RUN: '', ROUNDS_GATE_lower: 'enabled', NOT_A_GATE: 'enabled' });
    expect(Object.keys(config).filter((k) => k !== 'VITE_DISABLE_SIGNUPS' && !k.startsWith('VITE_OAUTH'))).toEqual([]);
  });

  it.each([
    'en abled',
    'enabled!',
    '"; window.pwned = 1; "',
    '</script><script>',
    'enabled\\',
    'é',
  ])('sends a value that is not a lowercase word as "invalid": %s', (raw) => {
    const { config, source } = render({ ROUNDS_GATE_SIGNUPS: raw });
    expect(config.ROUNDS_GATE_SIGNUPS).toBe('invalid');
    expect(source).not.toContain('pwned');
    expect(source).not.toContain('<');
  });
});
