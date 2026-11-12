/// <reference path="../pb_data/types.d.ts" />

// No client creates or changes a profile file (ROUNDS-00B-L07).
// profile_files.pb.js registers these handlers. PocketBase runs each one in
// its own context, so each requires this file.
//
// A client's users create or update is refused when its request names a
// profile file field in any form: the field, its + or - modifier, or an
// upload under its name, whatever the value, empty or null included.
// It's refused too when the record would save a different file there,
// whatever form the request took. An OAuth2 sign-up's createData skips the
// create request hook, so its keys are checked here as well. A superuser
// isn't held to it, and a file already stored stays as it is.

// The users fields that hold a file: PocketBase's default users collection
// has one, and no screen sets it.
const FILE_FIELDS = ["avatar"];
// admission.js's answer to an account field no client sets, so a request
// that also touches a demo flag gets one answer whichever users hook
// PocketBase runs first (test_profile_files_hooks.py holds them equal).
const LOCKED = "These account fields can't be changed.";

function isSuperuser(httpContext) {
  return Boolean(httpContext && $apis.requestInfo(httpContext).admin);
}

// A request key's field, without a + or - modifier.
function fieldOf(key) {
  return String(key).replace(/^\+|[+-]$/g, "");
}

function namesFile(keys) {
  return keys.some((key) => FILE_FIELDS.indexOf(fieldOf(key)) >= 0);
}

// Every key in a users request's data, and every upload's. The record
// check covers any form the data doesn't show.
function requestKeys(e) {
  const data = $apis.requestInfo(e.httpContext).data || {};
  return Object.keys(data).concat(Object.keys(e.uploadedFiles || {}));
}

function filesOf(record, field) {
  return record ? JSON.stringify(record.getStringSlice(field)) : "[]";
}

function guardCreate(e) {
  if (isSuperuser(e.httpContext)) return;
  if (namesFile(requestKeys(e)) || FILE_FIELDS.some((field) => filesOf(e.record, field) !== "[]")) {
    throw new BadRequestError(LOCKED);
  }
}

function guardUpdate(e) {
  if (isSuperuser(e.httpContext)) return;
  const original = e.record.originalCopy();
  if (namesFile(requestKeys(e)) || FILE_FIELDS.some((field) => filesOf(e.record, field) !== filesOf(original, field))) {
    throw new BadRequestError(LOCKED);
  }
}

function guardOAuth2(e) {
  if (!e.isNewRecord || isSuperuser(e.httpContext)) return;
  const data = $apis.requestInfo(e.httpContext).data || {};
  const createData = data.createData;
  if (createData && typeof createData === "object" && namesFile(Object.keys(createData))) {
    throw new BadRequestError(LOCKED);
  }
}

module.exports = {
  FILE_FIELDS,
  LOCKED,
  fieldOf,
  guardCreate,
  guardUpdate,
  guardOAuth2,
};
