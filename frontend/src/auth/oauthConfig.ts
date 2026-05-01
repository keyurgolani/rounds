// OAuth provider gating.
//
// A provider button only renders when its enabling env var is truthy.
// In production, setting `VITE_OAUTH_GOOGLE_ENABLED=true` also implies the
// PocketBase instance has the matching provider configured in Settings → Auth
// providers. These flags only control whether buttons render in the SPA.
//
// Recognized truthy values: "true", "1", "yes" (case-insensitive).

function isTruthy(v: string | undefined): boolean {
  if (!v) return false;
  const n = v.trim().toLowerCase();
  return n === 'true' || n === '1' || n === 'yes';
}

const env = import.meta.env as Record<string, string | undefined>;
const runtime = typeof window !== 'undefined'
  ? (window as unknown as { __ROUNDS_CONFIG__?: Record<string, string | undefined> }).__ROUNDS_CONFIG__
  : undefined;

const google = isTruthy(runtime?.VITE_OAUTH_GOOGLE_ENABLED ?? env.VITE_OAUTH_GOOGLE_ENABLED);
const github = isTruthy(runtime?.VITE_OAUTH_GITHUB_ENABLED ?? env.VITE_OAUTH_GITHUB_ENABLED);

export const oauthConfig = {
  google,
  github,
  anyEnabled: google || github,
};
