/// <reference path="../pb_data/types.d.ts" />

onRecordBeforeCreateRequest((e) => {
  const value = $os.getenv("ROUNDS_DISABLE_SIGNUPS");
  const disabled = value && ["true", "1", "yes"].includes(value.trim().toLowerCase());

  if (!disabled) return;
  throw new BadRequestError("Signups are disabled on this instance.");
}, "users");
