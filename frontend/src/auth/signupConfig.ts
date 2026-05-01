// Signup gating for hosted instances.
//
// `VITE_DISABLE_SIGNUPS=true` hides the signup flow in the SPA. PocketBase
// also enforces `ROUNDS_DISABLE_SIGNUPS=true` through a server-side hook, so
// hosted instances should set both variables.

function isTruthy(v: string | undefined): boolean {
  if (!v) return false;
  const n = v.trim().toLowerCase();
  return n === 'true' || n === '1' || n === 'yes';
}

const env = import.meta.env as Record<string, string | undefined>;
const runtime = typeof window !== 'undefined'
  ? (window as unknown as { __ROUNDS_CONFIG__?: Record<string, string | undefined> }).__ROUNDS_CONFIG__
  : undefined;

export const signupConfig = {
  disabled: isTruthy(runtime?.VITE_DISABLE_SIGNUPS ?? env.VITE_DISABLE_SIGNUPS),
};
