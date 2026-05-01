/// <reference path="../pb_data/types.d.ts" />

function envTruthy(name) {
  const value = $os.getenv(name);
  if (!value) return false;
  const normalized = value.trim().toLowerCase();
  return normalized === "true" || normalized === "1" || normalized === "yes";
}

onRecordBeforeCreateRequest((e) => {
  if (!envTruthy("ROUNDS_DISABLE_SIGNUPS")) return;
  throw new BadRequestError("Signups are disabled on this instance.");
}, "users");
