# Architecture

Rounds is a self-hostable interview prep workspace. The app is split into four runtime services: a React frontend, PocketBase for auth and data, a FastAPI runner for code execution and the AI / PDF / share endpoints, and a Node + Puppeteer sidecar that produces high-fidelity PDFs.

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
  | /api/run, /api/evaluate, /api/pdf, /api/ai, /api/share
  v
FastAPI runner ----------+
  |                      |
  | internal HTTP        |
  v                      |
PDF renderer (Node +     |
Puppeteer sidecar)       |
                         |
Frontend container       |
  |                      |
  | /api/*, /_/*         |
  v                      |
PocketBase  <------------+ admin token (share endpoint)
  |-- auth
  |-- SQLite data
  |-- migrations
  |-- hooks
  |-- seeded shared content
```

In development, Vite mirrors the production proxy behavior. Exact runner paths (`/api/run`, `/api/evaluate`, `/api/pdf`, `/api/ai`, `/api/share`) go to FastAPI, while the rest of `/api/*` and `/_/*` go to PocketBase. In production, nginx in the frontend container owns that same routing. The PDF renderer is internal-only — it has no host port mapping and is reached through the runner.

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

## Resume Studio

The Resume Studio lives under `frontend/src/features/resume/` and is hosted by `frontend/src/pages/ResumeStudio.tsx`.

Layout:

- `studio/StudioShell.tsx`: three-column shell — section nav, active editor or tool tab, and the live A4 preview. Each column scrolls independently so editing one pane never moves another.
- `studio/PreviewPane.tsx` and `studio/PaginatedFrame.tsx`: live preview with on-screen page-break markers that mirror the printed pagination. The shaded preview surround is height-constrained to its column, so the resume scrolls inside the surround rather than pushing it past the fold.
- `studio/PreviewDialog.tsx`: full-screen inspect-mode modal with a zoom toolbar (−, 100%, +, Fit), keyboard shortcuts (`+`, `−`, `0`, `F`, `Esc`), and Ctrl/Cmd-wheel zoom. The page is wrapped in a CSS-transform scaler so the scroll container reports correct overflow at any zoom level.
- `studio/editors/`: per-section editors (personal info, experience, education, skills, projects, publications, profiles) with `@dnd-kit` drag-and-drop reordering.
- `studio/tabs/`: tool tabs (Templates, Tailor, ATS, History, Export). The Export tab replaces a former modal — it lives on the same surface as the live preview so the user can pick a format without losing sight of the page being exported.
- `templates/`: built-in templates (Classic, Modern, Executive, SWE LaTeX) and the registry the gallery and renderer share.
- `share/`: public share-link UI and client.
- `bullets/`: cross-resume bullet library context and drawer.
- `ai/` and `studio/EnhancementContext.tsx`: AI client and per-bullet enhancement state for the Improve affordance.
- `import/`: `.docx` (mammoth) and PDF (pdfjs) → JSON Resume conversion.
- `export/`: format-specific exporters — server PDF, browser print, DOCX, standalone HTML, Markdown, plain text, JSON Resume.

The studio's active tab is mirrored to the URL via the `?tab=` query parameter so reloads, links, and the back button stay accurate.

## Backend Runner

The backend in `backend/` owns code execution plus the runner-adjacent endpoints PocketBase isn't suited for: server-rendered PDFs, AI provider proxying, and the public read-only share endpoint. Auth and data still live in PocketBase.

Endpoints:

- `POST /api/run`: execute one input case.
- `POST /api/evaluate`: execute a selected set of test cases and compare results.
- `POST /api/pdf/render`: forward to the headless-Chromium sidecar and stream the resulting PDF back.
- `POST /api/ai/*`: server-side AI provider calls. The runner reads each user's stored credentials from PocketBase, decrypts them with `AI_KEY_SECRET`, and proxies the request — keys never reach the browser.
- `GET /api/share/<token>`: public read-only resume fetch backed by a cached PocketBase admin token so the endpoint can bypass per-user owner rules.
- `GET /health`: container health check path outside the `/api` namespace.

Runner schemas live in `backend/schemas.py`. Execution drivers live under `backend/drivers/` and matching logic lives in `backend/matchers.py`. Cross-cutting helpers (key encryption, admin-token cache, ATS keyword analysis) live in `backend/app/`.

## PDF Renderer

`backend/pdf_renderer/` is a Node + Puppeteer service packaged as a separate container. It accepts an HTML payload and returns a fixed-margin A4 PDF. The runner is the only client; the sidecar has no host port mapping in either the dev or prod compose stack, and the runner reaches it at `PDF_RENDERER_URL` (default `http://pdf-renderer:4000`).

Splitting it from the runner keeps the Python image free of a Chromium dependency and lets the renderer be replaced or scaled independently.

## PocketBase

PocketBase files live in `pocketbase/`.

Migrations:

- `1700000000_init_collections.js`: final schema.
- `1700000100_seed_data.js`: shared questions, categories, coding question sets, and guide cheat sheets.
- `1700000500_bootstrap_admin.js`: optional first admin bootstrap from environment variables.
- `1700000600_demo_user.js`: hosted demo user and usage limiter fields.
- `1700000700_resume_studio.js`: `resumes`, `resume_versions`, and `bullet_library` collections.
- `1700000800_ai_providers.js`: per-user `ai_providers` collection storing encrypted provider credentials.
- `1700000900_share_links_resume_rel.js`: extends `share_links` with a relation to resumes for public read-only views.

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
