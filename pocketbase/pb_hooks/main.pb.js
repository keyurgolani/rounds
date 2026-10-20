/// <reference path="../pb_data/types.d.ts" />

onRecordBeforeCreateRequest((e) => {
  // ROUNDS_GATE_SIGNUPS wins when set; ROUNDS_DISABLE_SIGNUPS is its alias.
  const gates = require(`${__hooks}/gates.js`);
  const signups = gates.resolve("SIGNUPS", {
    ROUNDS_GATE_SIGNUPS: $os.getenv("ROUNDS_GATE_SIGNUPS"),
    ROUNDS_DISABLE_SIGNUPS: $os.getenv("ROUNDS_DISABLE_SIGNUPS"),
  });

  if (signups.value === "enabled") return;
  throw new BadRequestError("Signups are disabled on this instance.");
}, "users");
