/// <reference path="../pb_data/types.d.ts" />
//
// Wires the share link create check (ROUNDS-00B-L03 stage 1) into PocketBase.
// It runs on every create request, the runner's and a direct REST call alike;
// the relation endpoint hooks (relation_endpoints.pb.js) check the target's
// owner on the same request. 1700008100_share_link_owner_rules.js makes the
// update rule null, so no request changes a link after this.

onRecordBeforeCreateRequest((e) => {
  require(`${__hooks}/share_links.js`).checkCreate(e);
}, "resume_share_links");
