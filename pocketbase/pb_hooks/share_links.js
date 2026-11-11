/// <reference path="../pb_data/types.d.ts" />
//
// Share link create check (ROUNDS-00B-L03 stage 1).
//
// A new resume_share_links row must:
//   * point at exactly one target, `resume` or `variant`;
//   * be owned by the caller (`user` is the signed-in account; the create
//     rule says the same, and this re-checks it on the resolved record);
//   * carry a token of exactly 22 characters from [A-Za-z0-9_-], the format
//     the runner mints (backend/routers/share.py).
// That the target belongs to the same account is the relation endpoint
// predicate's job (relation_endpoints.js, ROUNDS-00B-L02), which answers a
// foreign target exactly like a missing one. Every denial here answers with
// that same body, "Failed to create record.", so no shape of request tells a
// foreign target from a missing one or a malformed token from either.
//
// screen() is pure, so the Node unit test require()s it without PocketBase.
// No token, id, or owner is ever logged.

const TOKEN_RE = /^[A-Za-z0-9_-]{22}$/;

// The first reason the row may not be created, or null. fields holds the
// resolved record's user, resume, variant, and token strings; caller is the
// signed-in account id, "" for none, and admin is true for a superuser.
function screen(fields, caller, admin) {
  const resume = typeof fields.resume === "string" ? fields.resume : "";
  const variant = typeof fields.variant === "string" ? fields.variant : "";
  const token = typeof fields.token === "string" ? fields.token : "";
  const user = typeof fields.user === "string" ? fields.user : "";
  if ((resume === "") === (variant === "")) return "target";
  if (!admin && (caller === "" || user !== caller)) return "owner";
  if (!TOKEN_RE.test(token)) return "token";
  return null;
}

function checkCreate(e) {
  const info = $apis.requestInfo(e.httpContext);
  const admin = !!info.admin;
  const caller = info.authRecord ? info.authRecord.id : "";
  const r = e.record;
  const reason = screen(
    {
      user: r.getString("user"),
      resume: r.getString("resume"),
      variant: r.getString("variant"),
      token: r.getString("token"),
    },
    caller,
    admin,
  );
  if (reason === null) return;
  console.log(
    JSON.stringify({
      v: "obs/v1",
      event: "share_link_denied",
      service: "pocketbase",
      reason: reason,
      actor: admin ? "admin" : caller ? "user" : "anonymous",
    }),
  );
  throw new BadRequestError("Failed to create record.");
}

module.exports = { TOKEN_RE: TOKEN_RE, screen: screen, checkCreate: checkCreate };
