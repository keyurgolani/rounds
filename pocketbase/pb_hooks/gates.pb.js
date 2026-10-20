/// <reference path="../pb_data/types.d.ts" />

// Startup log of every gate PocketBase reads (ROUNDS-00A-L01). Gates
// are read per request, but values only change with a restart, so one
// line at boot shows what this process will use.
onAfterBootstrap((e) => {
  const gates = require(`${__hooks}/gates.js`);
  const env = {};
  gates.envKeys().forEach((key) => {
    env[key] = $os.getenv(key);
  });
  const resolved = gates.snapshot(env);
  console.log(
    JSON.stringify({ v: "obs/v1", event: "gates", service: "pocketbase", gates: resolved }),
  );
  Object.keys(resolved).forEach((name) => {
    if (resolved[name].source === "invalid") {
      console.error(
        gates.PREFIX + name + " has an invalid value; using " + resolved[name].value + " until it is fixed.",
      );
    }
  });
});
