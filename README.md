# Rounds — Interview Prep Command Center

Rounds is a self-hostable interview prep workspace for system design, coding, behavioral prep, and job-search tracking.

Current release: **v1.0.0**

## Features

- System design practice with question lists, API-backed cheat-sheet guides, diagrams, trade-off panels, and senior follow-up topics.
- Coding practice with Monaco editor, local drafts, custom runs, full-suite evaluation, and structured problem metadata.
- Behavioral prep with competency-tagged questions, STAR story guidance, personal anecdotes, and question-to-story linking.
- Application tracking with companies, roles, statuses, rounds, offers, campaign context, and todos.
- Command center, theme controls, streak tracking, and dashboard widgets for day-to-day prep.

## Stack

| Layer | Tech |
| --- | --- |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Auth + data | PocketBase + SQLite |
| Code runner | FastAPI + Python/Node subprocess drivers |
| Deployment | Docker Compose or Kubernetes manifests |
| Tests | Vitest + Testing Library, pytest on Python 3.12 |

## Repository Layout

```text
.
├── frontend/              React + Vite SPA, production nginx config
├── backend/               FastAPI code runner
├── pocketbase/            PocketBase image, migrations, hooks, seeds
├── docs/                  Deployment notes
├── k8s/                   Kustomize manifests
├── docker-compose.yml     Local development stack
└── docker-compose.prod.yml Single-box production stack
```

## Local Development

```sh
cp .env.example .env
docker compose up -d
```

Services:

- Frontend: `http://localhost:3001`
- PocketBase: `http://localhost:8090`, admin UI at `http://localhost:8090/_/`
- Runner: `http://localhost:3099`

Dev compose bootstraps a PocketBase admin from `PB_ADMIN_EMAIL` and `PB_ADMIN_PASSWORD` when set. The `.env.example` defaults are for local development only.

## Production Compose

```sh
cp .env.example .env
# edit .env for your domain, admin credentials, CORS, OAuth, and signup policy
docker compose -f docker-compose.prod.yml up -d
```

Only the frontend port is exposed. nginx routes runner endpoints to FastAPI and all other `/api/*` plus `/_/*` traffic to PocketBase.

Production compose pulls published images from Docker Hub by default:

- `keyurgolani/rounds-frontend`
- `keyurgolani/rounds-pocketbase`
- `keyurgolani/rounds-runner`

Equivalent images are also published to GHCR as `ghcr.io/keyurgolani/rounds-frontend`, `ghcr.io/keyurgolani/rounds-pocketbase`, and `ghcr.io/keyurgolani/rounds-runner`.

PocketBase data lives in the `pb_data` Docker volume. Back it up regularly.

## Signup Policy

Hosted instances can disable public signups:

```env
VITE_DISABLE_SIGNUPS=true
ROUNDS_DISABLE_SIGNUPS=true
```

`VITE_DISABLE_SIGNUPS` hides signup UI in the frontend. `ROUNDS_DISABLE_SIGNUPS` blocks direct PocketBase user creation through a server-side hook.

## Migrations and Seed Data

Fresh deployments run three migrations:

1. `1700000000_init_collections.js` creates the final schema.
2. `1700000100_seed_data.js` loads all shared questions, categories, and guide cheat sheets.
3. `1700000500_bootstrap_admin.js` optionally creates the first PocketBase admin from environment variables.

## Verification

```sh
npm --prefix frontend test
npm --prefix frontend run build
python3.12 -m venv /tmp/rounds-backend-venv
/tmp/rounds-backend-venv/bin/python -m pip install -r backend/requirements.txt
/tmp/rounds-backend-venv/bin/python -m pytest backend
```

## Environment Variables

See `.env.example` and `frontend/.env.example` for the complete list.

| Variable | Purpose |
| --- | --- |
| `HTTP_PORT` | Production frontend host port |
| `POCKETBASE_PORT` | Dev PocketBase host port |
| `RUNNER_PORT` | Dev runner host port |
| `FRONTEND_PORT` | Dev frontend host port |
| `CORS_ALLOW_ORIGINS` | Runner CORS origins |
| `PB_ADMIN_EMAIL`, `PB_ADMIN_PASSWORD` | Optional PocketBase admin bootstrap |
| `VITE_POCKETBASE_URL` | Browser PocketBase base URL; blank means same-origin |
| `VITE_API_PROXY_TARGET` | Vite dev runner proxy target |
| `VITE_POCKETBASE_PROXY_TARGET` | Vite dev PocketBase proxy target |
| `VITE_DEV_ALLOWED_HOSTS` | Comma-separated Vite dev allowed hosts |
| `VITE_OAUTH_GOOGLE_ENABLED`, `VITE_OAUTH_GITHUB_ENABLED` | Render OAuth buttons |
| `VITE_DISABLE_SIGNUPS`, `ROUNDS_DISABLE_SIGNUPS` | Disable signup UI and server-side user creation |

## License

MIT. See `LICENSE`.
