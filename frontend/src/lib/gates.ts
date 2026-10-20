// Gates the SPA reads (ROUNDS-00A-L01).
//
// Values come from `window.__ROUNDS_CONFIG__`, which the frontend
// image's runtime-config.js fills from the container environment at
// start, then from build-time `import.meta.env`. The registry carries
// the gates backend/app/gates.py marks for the frontend reader;
// backend/tests/test_gates.py keeps them in step.
//
// ROUNDS_GATE_<NAME> set to an allowed value wins. Any other value takes
// the gate's most restrictive value. Unset or empty, a truthy alias
// applies, then the written default.

import registry from './gateRegistry.json';

type GateSpec = {
  values: string[];
  default: string;
  closed: string;
  aliases: { env: string; value: string }[];
};

export type GateName = keyof typeof registry.gates;
export type GateSource = 'env' | 'alias' | 'default' | 'invalid';
export type ResolvedGate = { value: string; source: GateSource };
export type GateEnv = Record<string, string | undefined>;

const GATES = registry.gates as Record<GateName, GateSpec>;

function read(env: GateEnv, key: string): string {
  const raw = env[key];
  return typeof raw === 'string' ? raw.trim().toLowerCase() : '';
}

export function resolveGate(name: GateName, env: GateEnv): ResolvedGate {
  const gate = GATES[name];
  const raw = read(env, registry.prefix + name);
  if (raw !== '') {
    return gate.values.includes(raw)
      ? { value: raw, source: 'env' }
      : { value: gate.closed, source: 'invalid' };
  }
  for (const alias of gate.aliases) {
    if (registry.truthy.includes(read(env, alias.env))) {
      return { value: alias.value, source: 'alias' };
    }
  }
  return { value: gate.default, source: 'default' };
}

/** Runtime config first, then build-time env, key by key. */
export function readGateEnv(): GateEnv {
  const build = import.meta.env as GateEnv;
  const runtime =
    typeof window !== 'undefined'
      ? (window as unknown as { __ROUNDS_CONFIG__?: GateEnv }).__ROUNDS_CONFIG__
      : undefined;
  const keys = new Set<string>();
  for (const [name, gate] of Object.entries(GATES)) {
    keys.add(registry.prefix + name);
    for (const alias of gate.aliases) keys.add(alias.env);
  }
  const env: GateEnv = {};
  for (const key of keys) env[key] = runtime?.[key] ?? build[key];
  return env;
}

export function gateValue(name: GateName, env: GateEnv = readGateEnv()): string {
  return resolveGate(name, env).value;
}
