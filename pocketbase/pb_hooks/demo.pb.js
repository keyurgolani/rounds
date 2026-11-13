/// <reference path="../pb_data/types.d.ts" />

// The demo account's containment (ROUNDS-00B-L07 stage 1); the logic is in
// demo.js. Every handler that depends on the demo gate reads it itself:
// ROUNDS_GATE_DEMO wins when set, and ROUNDS_ENABLE_DEMO is its alias.

// 1. At every start with the demo off, each demo account gets a random
// password and a new token key. One log line with the counts, at error
// level when the lock couldn't finish.
onAfterBootstrap((e) => {
  const demo = require(`${__hooks}/demo.js`);
  const out = demo.lockAll($app.dao(), {
    ROUNDS_GATE_DEMO: $os.getenv("ROUNDS_GATE_DEMO"),
    ROUNDS_ENABLE_DEMO: $os.getenv("ROUNDS_ENABLE_DEMO"),
  });
  const line = JSON.stringify(Object.assign({ v: "obs/v1", event: "demo_lock", service: "pocketbase" }, out));
  if (demo.lockFailed(out)) console.error(line);
  else console.log(line);
});

// 2. With the demo off, no demo account signs in or holds a working
// session: any request its token authenticates gets 401.
routerUse((next) => {
  return (c) => {
    require(`${__hooks}/demo.js`).guardSession(c, {
      ROUNDS_GATE_DEMO: $os.getenv("ROUNDS_GATE_DEMO"),
      ROUNDS_ENABLE_DEMO: $os.getenv("ROUNDS_ENABLE_DEMO"),
    });
    return next(c);
  };
});

onRecordBeforeAuthWithPasswordRequest((e) => {
  require(`${__hooks}/demo.js`).guardSignIn(e, {
    ROUNDS_GATE_DEMO: $os.getenv("ROUNDS_GATE_DEMO"),
    ROUNDS_ENABLE_DEMO: $os.getenv("ROUNDS_ENABLE_DEMO"),
  });
}, "users");

// The demo account signs in with its password only, on or off.
onRecordBeforeAuthWithOAuth2Request((e) => {
  require(`${__hooks}/demo.js`).guardPasswordOnly(e, {
    ROUNDS_GATE_DEMO: $os.getenv("ROUNDS_GATE_DEMO"),
    ROUNDS_ENABLE_DEMO: $os.getenv("ROUNDS_ENABLE_DEMO"),
  });
}, "users");

// 3. A demo caller changes only its profile, and can't delete its account
// or change its email.
onRecordBeforeUpdateRequest((e) => {
  require(`${__hooks}/demo.js`).guardAccountUpdate(e);
}, "users");

onRecordBeforeDeleteRequest((e) => {
  require(`${__hooks}/demo.js`).guardAccountDelete(e);
}, "users");

onRecordBeforeRequestEmailChangeRequest((e) => {
  require(`${__hooks}/demo.js`).guardEmailChange(e);
}, "users");

// 4. No demo account owns a share link or an AI provider, credential,
// model, or settings row, through the API or any save through the app's
// Dao. The tags are demo.js's CONTAINED.
onRecordBeforeCreateRequest((e) => {
  require(`${__hooks}/demo.js`).guardContainedRequest(e);
}, "resume_share_links", "share_capabilities", "ai_providers", "ai_credentials", "ai_provider_models", "ai_settings");

onRecordBeforeUpdateRequest((e) => {
  require(`${__hooks}/demo.js`).guardContainedRequest(e);
}, "resume_share_links", "share_capabilities", "ai_providers", "ai_credentials", "ai_provider_models", "ai_settings");

onModelBeforeCreate((e) => {
  require(`${__hooks}/demo.js`).guardContainedModel(e);
}, "resume_share_links", "share_capabilities", "ai_providers", "ai_credentials", "ai_provider_models", "ai_settings");

onModelBeforeUpdate((e) => {
  require(`${__hooks}/demo.js`).guardContainedModel(e);
}, "resume_share_links", "share_capabilities", "ai_providers", "ai_credentials", "ai_provider_models", "ai_settings");

// 5. The demo's sign-out clears what the demo account holds, and puts its
// seeded profile back. With the demo off it answers as a route that
// doesn't exist, so it carries no auth middleware of its own.
routerAdd("POST", "/api/rounds/demo/sessions/end", (c) => {
  return require(`${__hooks}/demo.js`).handleEnd(c, {
    ROUNDS_GATE_DEMO: $os.getenv("ROUNDS_GATE_DEMO"),
    ROUNDS_ENABLE_DEMO: $os.getenv("ROUNDS_ENABLE_DEMO"),
  });
});

// 6. Every 5 minutes with the demo on: the same reset for a demo account
// none of whose rows the reset can clear changed in 2 hours, or whose
// oldest such row is a day old.
cronAdd("rounds_demo_reset", "*/5 * * * *", () => {
  require(`${__hooks}/demo.js`).sweepNow({
    ROUNDS_GATE_DEMO: $os.getenv("ROUNDS_GATE_DEMO"),
    ROUNDS_ENABLE_DEMO: $os.getenv("ROUNDS_ENABLE_DEMO"),
  });
});
