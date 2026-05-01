import PocketBase from 'pocketbase';

// Base URL resolution:
//   1. `VITE_POCKETBASE_URL` wins (explicit override — needed in local
//      dev when the Vite dev server and PB are on different ports).
//   2. Same-origin in production. The frontend's nginx config reverse-
//      proxies /api/* and /_/* to the PocketBase container, so PB SDK
//      calls travel along the same origin as the page.
const explicitUrl = import.meta.env.VITE_POCKETBASE_URL as string | undefined;
const baseUrl = explicitUrl && explicitUrl.trim()
  ? explicitUrl.trim()
  : window.location.origin;

export const pb = new PocketBase(baseUrl);

// PB's default auto-cancellation keys requests by endpoint, so a
// component that re-fires the same fetch on a dependency change aborts
// the first in-flight request and the caller sees a spurious
// "autocancelled" error. The app manages its own lifecycles
// (useEffect cleanup, campaign switching, etc.), so opt out globally.
pb.autoCancellation(false);

// PocketBase is always enabled. The flag is kept so callers can make one
// structural decision without depending directly on SDK details.
export const pocketbaseEnabled = true;
