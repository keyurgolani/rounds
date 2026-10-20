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

- `/api/run`, `/api/evaluate`, and the other runner groups go to the FastAPI runner.
- Other `/api/*` paths go to PocketBase.
- PocketBase's admin UI (`/_/*`), its admin APIs, collection metadata, and the admission hook routes answer 404. Open the admin UI on PocketBase's own port, `http://localhost:8090/_/`.

This keeps browser code portable between local dev, Docker Compose, and production.

## Working With Data

Most app code should use `frontend/src/api/client.ts` instead of importing PocketBase directly. The shim preserves the app's historical `api.get/post/put/del` contract and adapts PocketBase relation fields into page-friendly fields.

Use the PocketBase SDK directly only in infrastructure-level code such as auth, low-level client setup, or a new adapter inside `api/client.ts`.

## Migrations

PocketBase applies each `.js` and `.ts` file at the top of `pocketbase/pb_migrations/` once, when it starts, and records it by name. A migration that has shipped never runs again, so every schema or data change gets a new migration. Don't edit, rename, or delete one that exists.

Pull requests into `main` and `next` run `scripts/lint_migrations.py`. It fails when a change:

1. edits, renames, or deletes an existing migration;
2. adds a migration whose up step drops a collection or a field, rewrites or deletes existing rows, or loads code with `require()`;
3. adds, edits, or deletes any other file in that directory.

A down step may do all of that. The lint reads the whole file except the down step, helpers included. It matches destructive and row-writing calls by method name, whatever the object is called, plus SQL in a file that runs `newQuery()`, so it catches mistakes rather than every possible rewrite. Run it before you push:

```sh
python3 scripts/lint_migrations.py --base origin/next --head HEAD
```

A destructive change that's intended needs review and an entry in `scripts/migration-lint-allowlist.json`. The lint prints one to start from, with the file's SHA-256 filled in:

```json
{
  "path": "pocketbase/pb_migrations/1700009000_example.js",
  "rules": ["drops-field", "rewrites-rows"],
  "sha256": "<printed by the lint>",
  "issue": "#14",
  "manifest": "legacy-shares-v1",
  "reason": "Drops the plaintext token fields after the cutover.",
  "reviewed_by": "keyurgolani"
}
```

The entry covers only that file, those rules, and that exact content, so any later edit fails the lint until it's reviewed again. `manifest` is optional. CI annotates each finding the entry covers.

The lint can't prove the review happened. It runs from the pull request's own checkout, so the same pull request can add a destructive migration and its own entry, and `reviewed_by` is free text. `.github/CODEOWNERS` assigns the migrations, the allowlist, the lint, the release gate, and the workflows to the owner, but nothing enforces that review or the lint yet: `main` and `next` have no branch protection or ruleset today, so a failing `migrations` check and a missing code-owner approval don't block a merge. Both stay advisory until the owner enables a ruleset on `main` and `next` that requires code-owner review and the `migrations` check.

[#156](https://github.com/keyurgolani/rounds/issues/156)'s migration framework and [#157](https://github.com/keyurgolani/rounds/issues/157)'s restore rehearsal replace this lint.

## Adding Pages

1. Add the route component under `frontend/src/pages/`.
2. Register the route in `frontend/src/App.tsx`.
3. Add navigation in `frontend/src/components/Layout.tsx` when the page should be globally reachable.
4. Fetch data through `api/client.ts` unless there is a strong reason not to.
5. Add tests under the nearest `__tests__/` directory when behavior is non-trivial.
6. Take user-visible names from `frontend/src/vocabulary/labels.ts` (`label('extracted-claim')`), not string literals. See [vocabulary.md](vocabulary.md).

## Product Vocabulary And Conformance

Product and domain names live in `contracts/vocabulary/terms.json`, and [vocabulary.md](vocabulary.md) explains how to use and change them. Baseline names that differ are listed in `contracts/vocabulary/adapters.json` with the leaf that retires them. Decision records live in `docs/decisions/`.

Who may write each durable concept lives in `contracts/authority/matrix.json` (DR-0002), and [authority.md](authority.md) explains how to read, cite, and change it. Before writing a collection or browser storage key, find its row there and write only through that row's command owner.

The conformance rules in `scripts/conformance/rules/` check all of this with Node 22 and no install step:

```sh
node --test scripts/conformance          # rule tests
node scripts/conformance/run.mjs         # every rule; exits 1 on any finding
node scripts/conformance/run.mjs --write # regenerate labels.ts, vocabulary.md, authority.md, baseline-stores.json, and the owner corrections file
node scripts/conformance/run.mjs --review ../rounds-review  # also check spec rows, services, the ledger pin, and owner labels
```

The vocabulary and authority rules compare `terms.json` and `matrix.json` with `--base` (default `origin/main`; CI passes the branch a pull request targets, such as `origin/next`); pass `--base none` when that ref isn't fetched. An unknown `--rule` exits 2. A new name in a navigation label, Command Center entry, page header, route, collection, or stored value needs a term label or an adapter entry; the finding says which.

The authority rule reads the audited revision (`62d4eae`) through git, so it needs full history (`fetch-depth: 0` in CI). A changed matrix row takes the new matrix revision and declares its `compatibility`; a change to a row's command owner, target authority, privacy floor or visibility, scope, or package is `breaking`. `baseline-stores.json` is generated from the audited revision; only each store's `rows` and `note` are written by hand, and `--write` keeps them.

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
