/// <reference path="../pb_data/types.d.ts" />

// Share capabilities (ROUNDS-00B-L03 stage 2): the owner's routes and the
// model hooks. The logic, and every write to share_capabilities, lives in
// share_capabilities.js.
//
// Only the runner calls the routes, with the owner's bearer; nginx and the
// Vite proxy answer /api/rounds/share with 404, so a browser never reaches
// them.

routerAdd(
  "GET",
  "/api/rounds/share/capabilities",
  (c) => require(`${__hooks}/share_capabilities.js`).handleList(c),
  $apis.requireRecordAuth("users"),
);

routerAdd(
  "POST",
  "/api/rounds/share/capabilities/:id/revoke",
  (c) => require(`${__hooks}/share_capabilities.js`).handleRevoke(c),
  $apis.requireRecordAuth("users"),
);

// What any writer, a superuser included, may store and change.
onModelBeforeCreate((e) => {
  require(`${__hooks}/share_capabilities.js`).guardCreate(e);
}, "share_capabilities");

onModelBeforeUpdate((e) => {
  require(`${__hooks}/share_capabilities.js`).guardUpdate(e);
}, "share_capabilities");

// A deleted resume or variant revokes the capabilities over its snapshots,
// the resume-to-variant cascade included, and keeps the snapshots.
onModelAfterDelete((e) => {
  require(`${__hooks}/share_capabilities.js`).onSourceDeleted(e, "resume");
}, "resumes");

onModelAfterDelete((e) => {
  require(`${__hooks}/share_capabilities.js`).onSourceDeleted(e, "variant");
}, "resume_variants");

// An account delete removes its capabilities first, in the same
// transaction, so its cascade into the snapshots can finish.
onModelBeforeDelete((e) => {
  require(`${__hooks}/share_capabilities.js`).onAccountDelete(e);
}, "users");
