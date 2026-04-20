// Supabase client — lazily constructed only when both env vars are present.
//
// In local/dev without Supabase you get `null` and the app falls back to:
//   • FastAPI at `/api/*` for data
//   • The in-browser mock `AuthProvider` for sessions
//
// In production both vars are set (Vercel project env → Preview + Production):
//   VITE_SUPABASE_URL=https://<ref>.supabase.co
//   VITE_SUPABASE_ANON_KEY=eyJ...
//
// The anon key is safe to embed in the client bundle. Row-level security on
// Postgres enforces per-user isolation.

import { createClient, type SupabaseClient } from '@supabase/supabase-js';

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

let client: SupabaseClient | null = null;

if (url && anonKey) {
  client = createClient(url, anonKey, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    },
  });
}

export const supabase = client;
export const supabaseEnabled = Boolean(client);
