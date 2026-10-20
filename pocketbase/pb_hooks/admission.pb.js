/// <reference path="../pb_data/types.d.ts" />

// Admission state routes and hooks (ROUNDS-00A-L01 stage 3). The logic,
// and every write to admission_*, lives in admission.js.
//
// The runner calls these with the caller's bearer: admit (steps 6 and 7),
// settle (evaluate's and grade's exact charge), finish (the end of an
// admitted request), and usage (the dependency check). The first three
// also need ROUNDS_ADMISSION_SECRET, which only the runner holds. nginx
// answers /api/rounds/admission/ with 404, so a browser never reaches them.

routerAdd(
  "POST",
  "/api/rounds/admission/admit",
  (c) => require(`${__hooks}/admission.js`).handle(c, "admit"),
  $apis.requireRecordAuth("users"),
);

routerAdd(
  "POST",
  "/api/rounds/admission/settle",
  (c) => require(`${__hooks}/admission.js`).handle(c, "settle"),
  $apis.requireRecordAuth("users"),
);

routerAdd(
  "POST",
  "/api/rounds/admission/finish",
  (c) => require(`${__hooks}/admission.js`).handle(c, "finish"),
  $apis.requireRecordAuth("users"),
);

routerAdd(
  "GET",
  "/api/rounds/admission/usage",
  (c) => require(`${__hooks}/admission.js`).handle(c, "usage"),
  $apis.requireRecordAuth("users"),
);

// Every 5 minutes: forget commands past their 24 hours, mark in-flight
// commands whose lease is gone failed_infrastructure, and drop expired
// leases and day-old counters.
cronAdd("rounds_admission_sweep", "*/5 * * * *", () => {
  require(`${__hooks}/admission.js`).sweepNow();
});

// No client sets or changes is_demo or the demo flags; a superuser,
// a migration, or a server hook can.
onRecordBeforeCreateRequest((e) => {
  require(`${__hooks}/admission.js`).guardDemoCreate(e);
}, "users");

onRecordBeforeUpdateRequest((e) => {
  require(`${__hooks}/admission.js`).guardDemoUpdate(e);
}, "users");

onRecordBeforeAuthWithOAuth2Request((e) => {
  require(`${__hooks}/admission.js`).guardDemoOAuth2(e);
}, "users");
