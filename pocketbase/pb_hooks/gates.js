/// <reference path="../pb_data/types.d.ts" />

// Gate registry for PocketBase (ROUNDS-00A-L01).
//
// Carries the gates backend/app/gates.py marks for the pocketbase
// reader; backend/tests/test_gates.py keeps the two in step. PocketBase
// runs every handler in its own context, so a handler requires this file
// itself and passes in the variables it read with $os.getenv:
//
//   const gates = require(`${__hooks}/gates.js`);
//
// ROUNDS_GATE_<NAME> set to an allowed value wins. Any other value
// takes the gate's most restrictive value. Unset or empty, a truthy
// alias applies, then the written default.

const PREFIX = "ROUNDS_GATE_";
const TRUTHY = ["true", "1", "yes"];

const GATES = {
  // The execution job store (ROUNDS-00A-L03): on serves the hook routes
  // under /api/rounds/execution/ (execution.pb.js).
  EXECUTION_STORE: {
    values: ["off", "on"],
    default: "off",
    closed: "off",
    aliases: [],
  },
  SIGNUPS: {
    values: ["enabled", "disabled"],
    default: "enabled",
    closed: "disabled",
    aliases: [{ env: "ROUNDS_DISABLE_SIGNUPS", value: "disabled" }],
  },
};

function read(env, key) {
  const raw = env && env[key];
  return typeof raw === "string" ? raw.trim().toLowerCase() : "";
}

function resolve(name, env) {
  const gate = GATES[name];
  if (!gate) {
    throw new Error("unknown gate " + name);
  }
  const raw = read(env, PREFIX + name);
  if (raw !== "") {
    if (gate.values.indexOf(raw) >= 0) {
      return { value: raw, source: "env" };
    }
    return { value: gate.closed, source: "invalid" };
  }
  for (let i = 0; i < gate.aliases.length; i++) {
    const alias = gate.aliases[i];
    if (TRUTHY.indexOf(read(env, alias.env)) >= 0) {
      return { value: alias.value, source: "alias" };
    }
  }
  return { value: gate.default, source: "default" };
}

// Every variable a snapshot reads, so a handler can collect them first.
function envKeys() {
  const keys = [];
  Object.keys(GATES).forEach((name) => {
    keys.push(PREFIX + name);
    GATES[name].aliases.forEach((alias) => keys.push(alias.env));
  });
  return keys;
}

function snapshot(env) {
  const out = {};
  Object.keys(GATES).forEach((name) => {
    out[name] = resolve(name, env);
  });
  return out;
}

module.exports = { PREFIX, TRUTHY, GATES, resolve, envKeys, snapshot };
