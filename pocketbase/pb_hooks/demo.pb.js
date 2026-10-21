/// <reference path="../pb_data/types.d.ts" />

// The demo account's containment (ROUNDS-00B-L07 stage 1); the logic is in
// demo.js. Every handler that depends on the demo gate reads it itself:
// ROUNDS_GATE_DEMO wins when set, and ROUNDS_ENABLE_DEMO is its alias.

// 1. At every start with the demo off, each demo account gets a random
// password and a new token key. One log line with the counts.
onAfterBootstrap((e) => {
  const out = require(`${__hooks}/demo.js`).lockAll($app.dao(), {
    ROUNDS_GATE_DEMO: $os.getenv("ROUNDS_GATE_DEMO"),
    ROUNDS_ENABLE_DEMO: $os.getenv("ROUNDS_ENABLE_DEMO"),
  });
  console.log(JSON.stringify(Object.assign({ v: "obs/v1", event: "demo_lock", service: "pocketbase" }, out)));
});

// 2. With the demo off, no demo account signs in.
onRecordBeforeAuthWithPasswordRequest((e) => {
  require(`${__hooks}/demo.js`).guardSignIn(e, {
    ROUNDS_GATE_DEMO: $os.getenv("ROUNDS_GATE_DEMO"),
    ROUNDS_ENABLE_DEMO: $os.getenv("ROUNDS_ENABLE_DEMO"),
  });
}, "users");

onRecordBeforeAuthWithOAuth2Request((e) => {
  require(`${__hooks}/demo.js`).guardSignIn(e, {
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
// model, or settings row, through the API or any other writer. The tags
// are demo.js's CONTAINED.
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
