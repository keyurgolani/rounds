# Deploy — Supabase + Vercel

Rounds is a single-page React + Vite app that reads and writes to Supabase
(Postgres + Auth). Vercel hosts the static bundle. Nothing else needs to
run in production.

---

## One-time setup

### 1. Supabase project

1. Create a project at <https://app.supabase.com>.
2. **SQL Editor → New query →** paste `supabase/schema.sql` → **Run**. This
   creates every table, index, trigger, and RLS policy.
3. **Authentication → Providers**
   - Enable **Email** (password + email link).
   - Enable **Google** and/or **GitHub** if you want OAuth buttons.
     Provide the OAuth client ID + secret from the provider console.
4. **Authentication → URL Configuration → Redirect URLs** — add:
   - `http://localhost:3000`
   - `https://<your-vercel-preview-pattern>.vercel.app`
   - `https://<your-production-domain>`
5. **Project Settings → API** — note the `Project URL` and `anon` key.
6. Seed the shared content tables (one-time). Easiest path: run
   `backend/seed_data.py` pointed at the Supabase Postgres connection
   string, then stop the backend. That populates
   `system_design_questions`, `coding_questions`,
   `behavioral_categories`, `behavioral_questions` without touching any
   per-user table.

### 2. Vercel project

1. **Import Git Repository**, pick this repo.
2. Vercel auto-detects the `vercel.json` at the root. Leave framework as
   "Other" — the config already points at `frontend/dist`.
3. **Environment Variables** — set on **Production** and **Preview**:

   | Key | Value |
   | --- | --- |
   | `VITE_SUPABASE_URL` | `https://<ref>.supabase.co` |
   | `VITE_SUPABASE_ANON_KEY` | `eyJ…` (anon key) |
   | `VITE_OAUTH_GOOGLE_ENABLED` | `true` or `false` |
   | `VITE_OAUTH_GITHUB_ENABLED` | `true` or `false` |

   Enable each `VITE_OAUTH_*_ENABLED` flag only when that provider is
   configured in Supabase; the flags gate whether the buttons render.
4. Deploy. Preview → production.

---

## Local development

Two modes. Pick whichever matches the feature you're working on.

### Mode A — Supabase (recommended for deploy-ready work)

```sh
cp frontend/.env.example frontend/.env.local
# fill in VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY
npm --prefix frontend install
npm --prefix frontend run dev
```

The app uses Supabase for auth + data. No backend process to run.

### Mode B — Legacy FastAPI (local development)

```sh
# backend
uvicorn --app-dir backend main:app --port 3099

# frontend
VITE_API_PROXY_TARGET=http://127.0.0.1:3099 \
  npm --prefix frontend run dev
```

The mock `AuthProvider` activates automatically when the Supabase env vars
are absent. All data goes to `/api/*` and is single-tenant.

---

## What gets deployed where

| Piece | Production home | Notes |
| --- | --- | --- |
| Static bundle (`frontend/dist`) | Vercel | Rewrites `/*` to `/index.html`. |
| Postgres (tables + RLS) | Supabase | Schema in `supabase/schema.sql`. |
| Auth (sessions, OAuth) | Supabase Auth | Providers configured in dashboard. |
| Shared content seeds | Supabase | One-time load via `backend/seed_data.py`. |
| FastAPI backend | **not deployed** | Kept in the repo for local Mode B only. |

---

## Multi-user isolation

All user-owned tables (`anecdotes`, `applications`, `interview_rounds`,
`user_progress`, `user_preferences`, `profiles`) carry a `user_id uuid`
column that references `auth.users(id)`. RLS is on with a single policy:
`auth.uid() = user_id`. The `anon` key embedded in the client cannot read
or write another user's rows.

Shared content tables (`system_design_questions`, `coding_questions`,
`behavioral_questions`, `behavioral_categories`) are read-only to
authenticated users and are written to only by the `service_role` key
(seeding + admin).

---

## OAuth flow notes

1. User clicks the Google/GitHub button on `/login` or `/signup`.
2. `AuthProvider.oauthSignIn` calls
   `supabase.auth.signInWithOAuth({ provider })` with a `redirectTo` of
   `<origin>/dashboard`.
3. Supabase bounces through the provider, then redirects back with a
   session in the URL fragment, which the Supabase SDK consumes
   automatically (see `detectSessionInUrl: true` in `src/lib/supabase.ts`).
4. `onAuthStateChange` fires, the provider hydrates the `User` from the
   session + the `profiles` row, and the app re-renders.

If either provider is not enabled in Supabase, leave its
`VITE_OAUTH_*_ENABLED` flag at `false` — the button will be hidden
entirely, so there's no way to trigger a failed OAuth redirect.
