/// <reference path="../pb_data/types.d.ts" />

// Legacy Artifact Snapshot creation route and scan (ROUNDS-00A-L04, PR 2).
// The logic, and every write to legacy_artifact_snapshots, lives in
// legacy_snapshots.js.
//
// Only the runner calls the route, with the caller's bearer and
// ROUNDS_ADMISSION_SECRET; nginx and the Vite proxy answer
// /api/rounds/legacy-snapshots with 404, so a browser never reaches it.
// While ROUNDS_GATE_LEGACY_SNAPSHOT_CREATE is off (its default) it answers
// 503 route_disabled and calls nothing.

routerAdd(
  "POST",
  "/api/rounds/legacy-snapshots",
  (c) => require(`${__hooks}/legacy_snapshots.js`).handle(c),
  $apis.requireRecordAuth("users"),
);

// pocketbase legacy-snapshot-scan --out PATH [--commit SHA]: the dry run an
// operator signs (python -m app.legacy_receipt sign) before turning the gate
// on. legacy_snapshots.js reads its arguments; PocketBase reads its own
// flags (--dir and the rest) before this runs.
$app.rootCmd.addCommand(
  new Command({
    use: "legacy-snapshot-scan",
    short: "Dry-run Legacy Artifact Snapshot creation over every resume and variant and write a report",
    disableFlagParsing: true,
    run: (cmd, args) => require(`${__hooks}/legacy_snapshots.js`).scanCommand(args),
  }),
);
