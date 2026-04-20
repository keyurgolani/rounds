# Supabase setup

Everything needed to stand up the Rounds backend on Supabase.

## Files (in `/supabase`)

- `schema.sql` — tables, indexes, triggers, RLS policies. Idempotent.

## First-time setup

1. Create a Supabase project at <https://app.supabase.com>.
2. Open SQL Editor → paste `schema.sql` → Run.
3. Authentication → Providers → enable Email; enable Google and/or GitHub
   with the credentials you'd like to support. Whichever you enable here,
   set the matching `VITE_OAUTH_*_ENABLED=true` in the frontend .env so the
   buttons render on the login / signup pages.
4. Authentication → URL Configuration → add your Vercel preview + production
   URLs to the redirect allow-list.
5. Project Settings → API → copy the `Project URL` and `anon` key into the
   frontend `.env` (see `frontend/.env.example`).

## Seeding content

The content tables (`system_design_questions`, `coding_questions`,
`behavioral_*`) are shared and are normally seeded once. The simplest path:
run the FastAPI backend once pointed at the Supabase Postgres connection
string. The `seed_if_empty` startup handler in `backend/main.py` will
populate the content tables from `backend/seed_data.py`.

## Row-level security

RLS is on for every user-scoped table. The default policy is
`auth.uid() = user_id` — a user can only read and write rows that belong to
them. Shared content tables are readable by any authenticated user and are
written to only via the `service_role` key (seeding only).

## Triggers

- `trg_auth_user_created` — when Supabase Auth creates a new user, we insert
  a matching row in `profiles` and `user_preferences`.
- `trg_*_updated` — bumps `updated_at` on every update.
