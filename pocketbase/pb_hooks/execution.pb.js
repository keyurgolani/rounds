/// <reference path="../pb_data/types.d.ts" />

// The execution job store's routes and hooks (ROUNDS-00A-L03 PRs 1 to
// 3). The logic, and every write to execution_*, lives in execution.js.
//
// The runner calls these at pocketbase:8090, and only while
// ROUNDS_GATE_EXECUTION_STORE is on; off, each answers 503. nginx answers
// /api/rounds/execution/ with 404, so a browser never reaches them.
//
//   enqueue, cancel, status,         the caller's bearer, plus the runner
//   review_start, review_finish      key (ROUNDS_ADMISSION_SECRET)
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

// The account's own job, for the runner's job read and its long-poll.
routerAdd(
  "POST",
  "/api/rounds/execution/status",
  (c) => require(`${__hooks}/execution.js`).handleCaller(c, "status"),
  $apis.requireRecordAuth("users"),
);

// A grading result's rubric review (PR 3): marked requested, with its own
// admission charge, before the runner calls a provider, then written into
// the graded row. Once per result.
routerAdd(
  "POST",
  "/api/rounds/execution/review_start",
  (c) => require(`${__hooks}/execution.js`).handleCaller(c, "review_start"),
  $apis.requireRecordAuth("users"),
);

routerAdd(
  "POST",
  "/api/rounds/execution/review_finish",
  (c) => require(`${__hooks}/execution.js`).handleCaller(c, "review_finish"),
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

// Every 5 minutes: scratch jobs that ended more than 7 days ago, and
// those that never ended and were last queued that long ago unless a
// worker still holds them, go with their attempts, envelopes, and
// admission command (execution.js purge).
cronAdd("rounds_execution_purge", "*/5 * * * *", () => {
  require(`${__hooks}/execution.js`).purgeNow();
});

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
// sets it, when complete writes the graded row (PR 3).
onRecordBeforeCreateRequest((e) => {
  require(`${__hooks}/execution.js`).guardEnvelopeCreate(e);
}, "ai_coding_attempts", "take_home_attempts");

onRecordBeforeUpdateRequest((e) => {
  require(`${__hooks}/execution.js`).guardEnvelopeUpdate(e);
}, "ai_coding_attempts", "take_home_attempts");

// No client creates a graded attempt row, moves a row to graded, or
// changes a graded row: only complete writes one (PR 4). The rules refuse
// these too; this checks the record as it would be saved.
onRecordBeforeCreateRequest((e) => {
  require(`${__hooks}/execution.js`).guardGradedCreate(e);
}, "ai_coding_attempts", "take_home_attempts");

onRecordBeforeUpdateRequest((e) => {
  require(`${__hooks}/execution.js`).guardGradedUpdate(e);
}, "ai_coding_attempts", "take_home_attempts");
