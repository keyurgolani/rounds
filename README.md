# Rounds — Interview Prep Command Center

A personal, multi-user interview prep workspace. Rounds gives you one place to
study system design, work through coding problems with an in-browser runner,
build a reusable library of STAR-format behavioral anecdotes, and track every
job application and interview round you're running.

The production build is a single-page React app backed by Supabase
(Postgres + Auth). A FastAPI backend is kept in the repo as a local
development option.

---

## Features

### System design practice
- Curated question library with difficulty, tags, functional &
  non-functional requirements, estimation, API design, database schema,
  high-level and detailed design.
- Interactive visual learning: Mermaid architecture diagrams, sequence
  diagrams, ER diagrams, zoomable charts, animated tradeoff sliders, and
  "senior topics" panels for staff-level follow-ups.
- Per-question progress, notes, and confidence tracking.

### Coding practice
- Monaco editor with per-question starter code and persistent drafts.
- **Run** panel — executes your code against public test cases in a
  sandboxed Python subprocess with stdout/stderr capture, timeouts, and
  structured pass/fail output.
- **Evaluate** panel — runs the full hidden test suite and reports
  per-case results, wall-clock time, and complexity hints.
- Thought-process walkthroughs, tips, companies, topics, time/space
  complexity metadata.

### Behavioral prep
- Question library grouped by category (leadership, conflict, ambiguity,
  …) with STAR guides, sample responses, tips, common pitfalls, follow-up
  questions, and "what interviewers look for" notes.
- **My Anecdotes** — build a personal library of STAR-format stories
  once, then link each anecdote to the behavioral questions it answers.
  Visual connectors show which stories cover which questions.

### Applications & interviews
- Track each application (company, role, status, applied date, resume
  variant, job description, notes, URL).
- Schedule interview rounds under an application with type, date,
  interviewer, questions asked, notes, and result.
- Dashboard summarises login streak, practice activity, and pipeline
  status at a glance.

### Multi-user by default
- Supabase Auth handles email + OAuth (Google, GitHub) sessions.
- Every user-owned table carries `user_id uuid` and is guarded by a
  single RLS policy: `auth.uid() = user_id`. Shared content tables
  (questions, categories) are read-only to authenticated users.

### Theming
- Dark / light themes with a tweaks panel for live design-token edits.

---

## Stack

| Layer | Tech |
| --- | --- |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Framer Motion |
| Editor | Monaco |
| Diagrams / charts | Mermaid, Recharts, D3 (scale/array) |
| Auth + DB (prod) | Supabase (Postgres + Auth, RLS) |
| Backend (local dev only) | FastAPI, SQLAlchemy, SQLite |
| Testing | Vitest + Testing Library (frontend), pytest (backend) |
| Hosting | Vercel (static bundle) + Supabase |

---

## Repository layout

```
.
├── frontend/          React + Vite SPA (production entry point)
│   ├── src/
│   │   ├── auth/          Supabase-backed auth provider + route guard
│   │   ├── components/    Layout, shell primitives, visual diagrams
│   │   ├── pages/         Dashboard, lists, detail pages, editors
│   │   ├── lib/           Supabase client, slug + draft helpers
│   │   └── theme/         Theme provider + tweaks panel
│   └── public/
├── backend/           FastAPI server (local development mode)
│   ├── routers/           questions, applications
│   ├── runner.py          Sandboxed code-execution primitive
│   ├── seed_data.py       Question + category fixtures
│   └── tests/             pytest suite
├── supabase/          schema.sql — tables, indexes, triggers, RLS
├── docs/              deployment.md, supabase.md
├── docker-compose.yml
├── .env.example       Root env template (docker compose auto-loads .env)
└── vercel.json
```

---

## Quick start

### Option A — Supabase (production-shaped)

```sh
cp frontend/.env.example frontend/.env.local
# fill in VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY

npm --prefix frontend install
npm --prefix frontend run dev
```

Open http://localhost:3000. Auth and data go through Supabase; no backend
process to run.

Before the first run, open your Supabase project's SQL editor and run
`supabase/schema.sql` to create every table, index, trigger, and RLS
policy. See [`docs/supabase.md`](docs/supabase.md) for details.

### Option B — FastAPI + SQLite (local development)

```sh
# backend
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn --app-dir backend main:app --port 3099

# frontend (separate shell)
VITE_API_PROXY_TARGET=http://127.0.0.1:3099 \
  npm --prefix frontend run dev
```

When the Supabase env vars are absent, the frontend falls back to a
single-tenant mock auth provider and talks to `/api/*` on the FastAPI
backend. The SQLite database lives at `backend/data/interview.db` and
seeds itself from `backend/seed_data.py` on first boot.

### Option C — Docker Compose

```sh
cp .env.example .env
# edit ports, DATABASE_URL, and Supabase keys to taste
docker compose up
```

Brings up the FastAPI backend (`${BACKEND_PORT}`, default `3099`) and the
Vite dev server (`${FRONTEND_PORT}`, default `3001`), both with
live-reload mounts. All configuration lives in the root `.env` file that
Docker Compose auto-loads; see [`.env.example`](.env.example) for the
full list.

---

## Tests

```sh
# frontend
npm --prefix frontend test

# backend
pytest backend
```

---

## Deployment

Full walkthrough: [`docs/deployment.md`](docs/deployment.md). In short:

1. Create a Supabase project and run `supabase/schema.sql`.
2. Enable the auth providers you want (Email + Google + GitHub).
3. Import the repo into Vercel. The root `vercel.json` points the build
   at `frontend/dist` and rewrites `/*` to `index.html`.
4. Set `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, and the
   `VITE_OAUTH_*_ENABLED` flags as Vercel env vars.
5. Deploy. Preview → production.

---

## Environment variables

See [`frontend/.env.example`](frontend/.env.example) for the full list.
Only `VITE_*` variables ship to the browser bundle. The Supabase `anon`
key is safe to embed in the client — RLS guards per-user data on the
server side.
