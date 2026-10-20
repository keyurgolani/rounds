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
6. Take user-visible names from `frontend/src/vocabulary/labels.ts` (`label('extracted-claim')`), not string literals. See [vocabulary.md](vocabulary.md).

## Product Vocabulary And Conformance

Product and domain names live in `contracts/vocabulary/terms.json`, and [vocabulary.md](vocabulary.md) explains how to use and change them. Baseline names that differ are listed in `contracts/vocabulary/adapters.json` with the leaf that retires them. Decision records live in `docs/decisions/`.

The conformance rules in `scripts/conformance/rules/` check all of this with Node 22 and no install step:

```sh
node --test scripts/conformance          # rule tests
node scripts/conformance/run.mjs         # every rule; exits 1 on any finding
node scripts/conformance/run.mjs --write # regenerate labels.ts, vocabulary.md, and the owner corrections file
```

The vocabulary rule compares `terms.json` with `--base` (default `origin/main`; CI passes the branch a pull request targets, such as `origin/next`); pass `--base none` when that ref isn't fetched. An unknown `--rule` exits 2. A new name in a navigation label, Command Center entry, page header, route, collection, or stored value needs a term label or an adapter entry; the finding says which.

## Adding Guide Content

Guide UI is shared across tracks. Prefer this flow:

1. Add or update seeded guide data in PocketBase migrations/seeds.
2. Keep shared guide data shape aligned with `frontend/src/pages/guides/guideTypes.ts`.
3. Add reusable presentation to `GuideShared.tsx` only when multiple tracks benefit.
4. Add track-specific visual decisions in the relevant track experience component.

Guide pages should contain synthesized internal prep knowledge, not external resource-link catalogs.

## Adding Coding Questions

Coding question seed data is authored through the builder pipeline rather than by editing generated JSON directly.

1. Add a question module under `pocketbase/seeds/builder/questions/`.
2. Define the canonical PocketBase payload, including `entry`, `test_cases`, starter code, hints, thought process, tips, and conservative metadata.
3. Add a Python reference implementation and register it with `register(...)` from `pocketbase/seeds/builder/registry.py`.
4. Run `python -m pocketbase.seeds.builder.build` from the repository root.
5. Commit both the authored module and the regenerated `pocketbase/seeds/more_coding.json`.

The builder imports every question module, validates references against the same backend matchers used at runtime, smoke-runs node-aware Python solutions for linked-list, tree, and graph entries, and rewrites the consolidated seed file consumed by `1700000100_seed_data.js`.

Use the `entry` contract in `pocketbase/seeds/builder/registry.py` for runner-backed problems. Function problems use `kind: "function"`; data-structure problems can use `linked_list`, `tree`, or `graph` so Python and JavaScript submissions receive real node objects while tests stay in readable shorthand forms.

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

For any change, from the repository root:

```sh
node --test scripts/conformance
node scripts/conformance/run.mjs
```

For backend runner work:

```sh
python3.12 -m venv /tmp/rounds-backend-venv
/tmp/rounds-backend-venv/bin/python -m pip install -r backend/requirements.txt
/tmp/rounds-backend-venv/bin/python -m pytest backend
```

Current frontend builds can emit a Vite chunk-size warning because diagram/editor-related bundles are large. Treat warnings separately from failures.
