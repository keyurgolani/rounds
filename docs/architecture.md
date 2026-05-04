# Architecture

Rounds is a self-hostable interview prep workspace. The app is split into three runtime services: a React frontend, PocketBase for auth and data, and a FastAPI code runner for executing coding practice submissions.

## System Overview

```text
Browser
  |
  | same-origin HTTP
  v
Frontend container
  |-- static React/Vite app
  |-- nginx or Vite proxy
  |
  | /api/run, /api/evaluate
  v
FastAPI runner

Frontend container
  |
  | /api/*, /_/*
  v
PocketBase
  |-- auth
  |-- SQLite data
  |-- migrations
  |-- hooks
  |-- seeded shared content
```

In development, Vite mirrors the production proxy behavior. Exact runner paths go to FastAPI, while the rest of `/api/*` and `/_/*` go to PocketBase. In production, nginx in the frontend container owns that same routing.

## Frontend

The frontend is a React 18 + TypeScript + Vite single-page app in `frontend/`.

Important directories:

- `frontend/src/App.tsx`: route tree for authenticated and public pages.
- `frontend/src/components/Layout.tsx`: authenticated shell, sidebar/topbar navigation, campaign pill, user menu, and command center mounting.
- `frontend/src/components/shell/`: shared shell controls such as headers, selects, date pickers, and visual glyphs.
- `frontend/src/pages/`: route-level pages for dashboard, guides, questions, applications, interviews, todos, campaigns, settings, and auth.
- `frontend/src/pages/guides/`: shared guide loader/types/components plus track-specific guide experiences.
- `frontend/src/command-center/`: command center provider, modal, registry, and widget views.
- `frontend/src/api/client.ts`: compatibility API shim over PocketBase plus runner passthrough.
- `frontend/src/lib/pocketbase.ts`: PocketBase SDK configuration.
- `frontend/src/auth/`: auth context, route guard, and signup policy.
- `frontend/src/campaign/`: campaign context and campaign-scoped workspace state.
- `frontend/src/theme/`: theme/nav style preferences.

The app uses React Router for navigation. Authenticated routes sit under `RequireAuth`, `CampaignProvider`, and `Layout`.

## Data Access

PocketBase is the authoritative auth and data store. Most frontend code still calls `api.get`, `api.post`, `api.put`, and `api.del` with legacy `/api/...` paths. `frontend/src/api/client.ts` keeps those call sites stable by translating paths to PocketBase collection operations and adapting PocketBase records into the flat shapes expected by the pages.

The shim also passes code-runner calls through to FastAPI:

- `/api/run`
- `/api/evaluate`

Everything else under `/api/*` is handled by PocketBase.

## Auth

PocketBase manages users and auth tokens. `AuthProvider` maps PocketBase auth records into the app `User` shape, refreshes auth state on mount, and clears invalid tokens.

The frontend also enforces a 30-minute idle timeout. Activity is written to localStorage so multiple tabs share one session clock.

Public signup can be disabled in two places:

- `VITE_DISABLE_SIGNUPS=true` hides frontend signup UI.
- `ROUNDS_DISABLE_SIGNUPS=true` blocks direct PocketBase user creation in `pocketbase/pb_hooks/main.pb.js`.

## Campaigns

Campaigns are the workspace boundary for job-search and prep progress. `CampaignProvider` loads the user's campaigns, creates a default campaign on first use, persists the active campaign in localStorage and PocketBase preferences, and scopes progress/draft operations to the active campaign.

The dashboard, todos, applications, and command center widgets use DOM events such as `rounds:applications-changed`, `rounds:interviews-changed`, `rounds:campaigns-changed`, and `rounds:todos-changed` to refresh nearby UI after lightweight mutations.

## Guides

Guide pages use a shared route/controller and track-specific experiences:

- `GuidePage.tsx`: route loader, track detection, data fetch, and scroll reset.
- `guideTypes.ts`: shared guide data contracts and track config.
- `GuideShared.tsx`: reusable guide layout and rendering components.
- `SystemDesignGuideExperience.tsx`, `CodingGuideExperience.tsx`, `BehavioralGuideExperience.tsx`: track-specific presentation.

Guide content comes from seeded PocketBase records rather than external link catalogs.

## Command Center

The command center is mounted once in `Layout` through `CommandCenterProvider` and `CommandCenter`. Widgets are registered in `frontend/src/command-center/registry.tsx`.

Current widgets:

- Add todo
- Add application
- Schedule interview
- Campaigns
- Theme

Pages can open the hub or a specific widget with `useCommandCenter().open()` and `useCommandCenter().openView(id)`.

## Backend Runner

The backend in `backend/` is intentionally narrow. It only owns code execution endpoints now that auth and data live in PocketBase.

Endpoints:

- `POST /api/run`: execute one input case.
- `POST /api/evaluate`: execute a selected set of test cases and compare results.
- `GET /health`: container health check path outside the `/api` namespace.

Runner schemas live in `backend/schemas.py`. Execution drivers live under `backend/drivers/` and matching logic lives in `backend/matchers.py`.

## PocketBase

PocketBase files live in `pocketbase/`.

Migrations:

- `1700000000_init_collections.js`: final schema.
- `1700000100_seed_data.js`: shared questions, categories, coding question sets, and guide cheat sheets.
- `1700000500_bootstrap_admin.js`: optional first admin bootstrap from environment variables.
- `1700000600_demo_user.js`: hosted demo user and usage limiter fields.

Hooks:

- `main.pb.js`: server-side signup disablement.

PocketBase stores SQLite data and uploads in the `pb_data` Docker volume.

## Navigation

The app supports sidebar and topbar navigation styles. The sidebar shows grouped practice nav plus tracking links. The topbar shows the main categories as first-class nav items:

- Today
- System Design
- Coding
- Behavioral
- Applications
- Interview
- Todo

System Design, Coding, and Behavioral open dropdowns for Guide and Problem List.

## Deployment Shape

Local development uses `docker-compose.yml` with exposed ports for each service. Production uses `docker-compose.prod.yml`, where only the frontend/nginx port is exposed and backend traffic stays private.

Kubernetes manifests live in `k8s/` for advanced deployments. PocketBase should stay single-replica when using SQLite.
