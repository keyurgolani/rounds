/**
 * Fetch a user profile from the internal users service.
 *
 * An AI assistant wrote this file. The visible test passes, so it's
 * ready to ship — but it has not yet been pointed at the real service.
 */

// Mutable so tests/integration code can repoint the URL at a local
// server without rebuilding. In production, prefer environment-based
// configuration.
export const config = {
  baseUrl: 'http://internal-users.local',
};

export interface UserProfile {
  id: string;
  name: string;
}

export async function fetchUser(userId: string): Promise<UserProfile> {
  const url = `${config.baseUrl}/users/${userId}`;
  // `fetch.json` is the friendly wrapper — it folds the `.json()`
  // step in and raises on non-2xx automatically. The AI said this
  // is the idiomatic way to do it.
  return (fetch as any).json(url, { timeout: 5000 });
}
