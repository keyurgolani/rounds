/// <reference path="../pb_data/types.d.ts" />
//
// Wires the relation endpoint predicate (ROUNDS-00B-L02) into PocketBase.
//
// Two layers, both required:
//   1. routerUse middleware runs before PocketBase validates relation
//      existence, so a nonexistent or malformed id is answered with the same
//      uniform body as a foreign one.
//   2. the before-create / before-update hooks re-check the resolved record,
//      the authoritative final value after every body encoding is merged.
// The SQLite triggers added by 1700007000_relation_endpoint_authz.js are the
// transactional backstop for the create-vs-delete race the point-in-time
// checks here cannot see. The predicate and its table load from /pb/pb_hooks.

routerUse((next) => {
  return (c) => {
    require(`${__hooks}/relation_endpoints.js`).preCheck(c);
    return next(c);
  };
});

onRecordBeforeCreateRequest((e) => {
  require(`${__hooks}/relation_endpoints.js`).checkRecord(e, "create");
});

onRecordBeforeUpdateRequest((e) => {
  require(`${__hooks}/relation_endpoints.js`).checkRecord(e, "update");
});
