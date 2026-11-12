/// <reference path="../pb_data/types.d.ts" />
//
// Wires the older share links' guard (ROUNDS-00B-L06 stage 1) into
// PocketBase: every save of a resume_share_links row through the app's Dao,
// a hook's or the admin UI's alike, changes nothing but replaced_by, once.
// 1700008500_legacy_share_migration.js makes every client write rule null.

onModelBeforeUpdate((e) => {
  require(`${__hooks}/share_links.js`).checkUpdate(e);
}, "resume_share_links");
