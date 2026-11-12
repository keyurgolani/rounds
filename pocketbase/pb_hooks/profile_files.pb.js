/// <reference path="../pb_data/types.d.ts" />

// No client creates or changes a profile file (ROUNDS-00B-L07); the logic
// is in profile_files.js. A superuser isn't held to it.

onRecordBeforeCreateRequest((e) => {
  require(`${__hooks}/profile_files.js`).guardCreate(e);
}, "users");

onRecordBeforeUpdateRequest((e) => {
  require(`${__hooks}/profile_files.js`).guardUpdate(e);
}, "users");

// An OAuth2 sign-up's createData skips the create request hook.
onRecordBeforeAuthWithOAuth2Request((e) => {
  require(`${__hooks}/profile_files.js`).guardOAuth2(e);
}, "users");
