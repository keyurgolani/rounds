/// <reference path="../pb_data/types.d.ts" />

// The share resolver's service login (ROUNDS-00B-L04). The logic is in
// share_secrets.js.

// On every start, and before every share-resolver login: share-resolver
// has ROUNDS_SHARE_RESOLVER_PASSWORD as its password, or, with no usable
// secret, can't log in at all. PocketBase 0.22's JS hooks have no
// onBeforeServe, and onAfterBootstrap runs before migrations, so the login
// hook covers the first start after the migration.
onAfterBootstrap((e) => {
  try {
    require(`${__hooks}/share_secrets.js`).bootstrapResolver();
  } catch (err) {
    console.error("share-resolver bootstrap failed: " + err);
  }
});

// The login answers only under the collection's exact name.
onRecordBeforeAuthWithPasswordRequest((e) => {
  require(`${__hooks}/share_secrets.js`).syncResolverForLogin(e);
}, "share_resolvers");

// The lookup: share-resolver only. nginx and the Vite proxy answer
// /api/rounds/share with 404, so only the runner reaches these routes.
routerAdd(
  "POST",
  "/api/rounds/share/lookup",
  (c) => require(`${__hooks}/share_secrets.js`).handleLookup(c),
  $apis.requireRecordAuth("share_resolvers"),
);

// CreateShare and RotateShareBearer: the owner's bearer and the runner key.
routerAdd(
  "POST",
  "/api/rounds/share/commands",
  (c) => require(`${__hooks}/share_secrets.js`).handleBegin(c),
  $apis.requireRecordAuth("users"),
);

routerAdd(
  "POST",
  "/api/rounds/share/capabilities",
  (c) => require(`${__hooks}/share_secrets.js`).handleCreate(c),
  $apis.requireRecordAuth("users"),
);

routerAdd(
  "POST",
  "/api/rounds/share/capabilities/:id/rotate",
  (c) => require(`${__hooks}/share_secrets.js`).handleRotate(c),
  $apis.requireRecordAuth("users"),
);

// The share-resolver record gets 403 on every route but its own.
routerUse((next) => {
  return (c) => {
    require(`${__hooks}/share_secrets.js`).guardResolverRequest(c);
    return next(c);
  };
});
