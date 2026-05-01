# Development

This guide covers local setup, common commands, verification, and implementation conventions for Rounds.

## Prerequisites

- Docker and Docker Compose for the full local stack.
- Node.js compatible with the frontend toolchain.
- Python 3.12 for backend verification. Python 3.14 is not recommended with the pinned backend dependencies.

## Start The Full Stack

```sh
cp .env.example .env
docker compose up -d
```

Services:

- Frontend: `http://localhost:3001`
- PocketBase: `http://localhost:8090`
- PocketBase admin UI: `http://localhost:8090/_/`
- Runner: `http://localhost:3099`

Dev compose creates a PocketBase admin from `PB_ADMIN_EMAIL` and `PB_ADMIN_PASSWORD`. If those are not set, compose uses dev-only placeholder defaults.

## Frontend Commands

Run these from `frontend/`:

```sh
npm install
npm run dev
npm run typecheck
npm test
npm run build
```

Useful scripts:

- `npm run dev`: start Vite.
- `npm run typecheck`: run TypeScript with `--noEmit`.
- `npm test`: run Vitest once.
- `npm run test:watch`: run Vitest in watch mode.
- `npm run build`: run TypeScript and build the production bundle.
- `npm run check`: run tests and build.

The frontend test suite uses Vitest, Testing Library, and jsdom.

## Backend Commands

Use Python 3.12 when creating a local environment:

```sh
python3.12 -m venv /tmp/rounds-backend-venv
/tmp/rounds-backend-venv/bin/python -m pip install -r backend/requirements.txt
/tmp/rounds-backend-venv/bin/python -m pytest backend
```

To run the backend directly:

```sh
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Routing And Proxies

The app is written against same-origin URLs. Vite development and production nginx use the same split:

- `/api/run` and `/api/evaluate` go to the FastAPI runner.
- Other `/api/*` paths go to PocketBase.
- `/_/*` goes to PocketBase admin UI.

This keeps browser code portable between local dev, Docker Compose, and production.

## Working With Data

Most app code should use `frontend/src/api/client.ts` instead of importing PocketBase directly. The shim preserves the app's historical `api.get/post/put/del` contract and adapts PocketBase relation fields into page-friendly fields.

Use the PocketBase SDK directly only in infrastructure-level code such as auth, low-level client setup, or a new adapter inside `api/client.ts`.

## Adding Pages

1. Add the route component under `frontend/src/pages/`.
2. Register the route in `frontend/src/App.tsx`.
3. Add navigation in `frontend/src/components/Layout.tsx` when the page should be globally reachable.
4. Fetch data through `api/client.ts` unless there is a strong reason not to.
5. Add tests under the nearest `__tests__/` directory when behavior is non-trivial.

## Adding Guide Content

Guide UI is shared across tracks. Prefer this flow:

1. Add or update seeded guide data in PocketBase migrations/seeds.
2. Keep shared guide data shape aligned with `frontend/src/pages/guides/guideTypes.ts`.
3. Add reusable presentation to `GuideShared.tsx` only when multiple tracks benefit.
4. Add track-specific visual decisions in the relevant track experience component.

Guide pages should contain synthesized internal prep knowledge, not external resource-link catalogs.

## Adding Command Center Widgets

1. Create a view in `frontend/src/command-center/views/`.
2. Add it to `frontend/src/command-center/registry.tsx` with an id, label, description, icon, and component.
3. Use `onComplete` after successful mutations so the modal closes consistently.
4. Dispatch a relevant `rounds:*changed` event when nearby UI should refresh.

Existing widget ids include `add-todo`, `add-application`, `schedule-interview`, `campaigns`, and `theme`.

## Styling Conventions

- Prefer existing CSS variables from `frontend/src/styles/globals.css`.
- Keep shell-level controls in `components/shell/` when reusable.
- Respect the selected navigation style: sidebar and topbar both live in `Layout.tsx`.
- Use established card, pill, typography, and visual token patterns before creating new ones.

## Verification Before Completion

For frontend work:

```sh
cd frontend
npm run typecheck
npm test
npm run build
```

For backend runner work:

```sh
python3.12 -m venv /tmp/rounds-backend-venv
/tmp/rounds-backend-venv/bin/python -m pip install -r backend/requirements.txt
/tmp/rounds-backend-venv/bin/python -m pytest backend
```

Current frontend builds can emit a Vite chunk-size warning because diagram/editor-related bundles are large. Treat warnings separately from failures.
