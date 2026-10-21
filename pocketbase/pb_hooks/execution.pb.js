/// <reference path="../pb_data/types.d.ts" />

// The execution job store's routes and hooks (ROUNDS-00A-L03 PR 1). The
// logic, and every write to execution_*, lives in execution.js.
//
// The runner calls these at pocketbase:8090, and only while
// ROUNDS_GATE_EXECUTION_STORE is on; off, each answers 503. nginx answers
// /api/rounds/execution/ with 404, so a browser never reaches them.
//
//   enqueue, cancel                  the caller's bearer, plus the runner
//                                    key (ROUNDS_ADMISSION_SECRET)
//   claim, heartbeat, complete, reap the execution_service record
//                                    (ROUNDS_EXECUTION_SECRET)

routerAdd(
  "POST",
  "/api/rounds/execution/enqueue",
  (c) => require(`${__hooks}/execution.js`).handleCaller(c, "enqueue"),
  $apis.requireRecordAuth("users"),
);

routerAdd(
  "POST",
  "/api/rounds/execution/cancel",
  (c) => require(`${__hooks}/execution.js`).handleCaller(c, "cancel"),
  $apis.requireRecordAuth("users"),
);

routerAdd(
  "POST",
  "/api/rounds/execution/claim",
  (c) => require(`${__hooks}/execution.js`).handleService(c, "claim"),
  $apis.requireRecordAuth("execution_service"),
);

routerAdd(
  "POST",
  "/api/rounds/execution/heartbeat",
  (c) => require(`${__hooks}/execution.js`).handleService(c, "heartbeat"),
  $apis.requireRecordAuth("execution_service"),
);

routerAdd(
  "POST",
  "/api/rounds/execution/complete",
  (c) => require(`${__hooks}/execution.js`).handleService(c, "complete"),
  $apis.requireRecordAuth("execution_service"),
);

routerAdd(
  "POST",
  "/api/rounds/execution/reap",
  (c) => require(`${__hooks}/execution.js`).handleService(c, "reap"),
  $apis.requireRecordAuth("execution_service"),
);

// On every start, and before every execution-worker login:
// execution-worker has ROUNDS_EXECUTION_SECRET as its password, or, with
// no usable secret, can't log in at all. PocketBase 0.22's JS hooks have
// no onBeforeServe, and onAfterBootstrap runs before migrations, so the
// login hook covers the first start after the migration.
onAfterBootstrap((e) => {
  try {
    require(`${__hooks}/execution.js`).bootstrapWorker();
  } catch (err) {
    console.error("execution-worker bootstrap failed: " + err);
  }
});

onRecordBeforeAuthWithPasswordRequest((e) => {
  require(`${__hooks}/execution.js`).syncWorkerForLogin(e);
}, "execution_service");

// No client sets or changes an attempt row's envelope. Only the server
// sets it, when it writes the graded row (PR 3).
onRecordBeforeCreateRequest((e) => {
  require(`${__hooks}/execution.js`).guardEnvelopeCreate(e);
}, "ai_coding_attempts", "take_home_attempts");

onRecordBeforeUpdateRequest((e) => {
  require(`${__hooks}/execution.js`).guardEnvelopeUpdate(e);
}, "ai_coding_attempts", "take_home_attempts");
