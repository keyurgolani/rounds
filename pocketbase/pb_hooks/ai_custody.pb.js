/// <reference path="../pb_data/types.d.ts" />

// AI provider custody routes (ROUNDS-14-L02 stage A). The logic, and every
// write to ai_credentials and ai_provider_models and every create or update
// of ai_providers, lives in ai_custody.js.
//
// Only the runner calls these, with the caller's bearer and
// ROUNDS_ADMISSION_SECRET; nginx and the Vite proxy answer /api/rounds/ai/
// with 404, so a browser never reaches them. PocketBase runs each handler
// on its own, so each names its action itself.

routerAdd(
  "POST",
  "/api/rounds/ai/providers/list",
  (c) => require(`${__hooks}/ai_custody.js`).handle(c, "list"),
  $apis.requireRecordAuth("users"),
);

routerAdd(
  "POST",
  "/api/rounds/ai/providers/create",
  (c) => require(`${__hooks}/ai_custody.js`).handle(c, "create"),
  $apis.requireRecordAuth("users"),
);

routerAdd(
  "POST",
  "/api/rounds/ai/providers/update",
  (c) => require(`${__hooks}/ai_custody.js`).handle(c, "update"),
  $apis.requireRecordAuth("users"),
);

routerAdd(
  "POST",
  "/api/rounds/ai/providers/models",
  (c) => require(`${__hooks}/ai_custody.js`).handle(c, "models"),
  $apis.requireRecordAuth("users"),
);

routerAdd(
  "POST",
  "/api/rounds/ai/credentials/read",
  (c) => require(`${__hooks}/ai_custody.js`).handle(c, "read"),
  $apis.requireRecordAuth("users"),
);

routerAdd(
  "POST",
  "/api/rounds/ai/credentials/convert",
  (c) => require(`${__hooks}/ai_custody.js`).handle(c, "convert"),
  $apis.requireRecordAuth("users"),
);
