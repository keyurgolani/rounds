// OAuth provider gating.
//
// A provider button only renders when its enabling env var is truthy.
// In production (Supabase), setting `VITE_OAUTH_GOOGLE_ENABLED=true` also
// implies the Supabase project has the matching provider configured in
// Authentication → Providers. In local dev without Supabase, the buttons
// trigger the mock `oauthSignIn` in AuthProvider.
//
// Recognized truthy values: "true", "1", "yes" (case-insensitive).

function isTruthy(v: string | undefined): boolean {
  if (!v) return false;
  const n = v.trim().toLowerCase();
  return n === 'true' || n === '1' || n === 'yes';
}

const env = import.meta.env as Record<string, string | undefined>;

const google = isTruthy(env.VITE_OAUTH_GOOGLE_ENABLED);
const github = isTruthy(env.VITE_OAUTH_GITHUB_ENABLED);

export const oauthConfig = {
  google,
  github,
  anyEnabled: google || github,
};
