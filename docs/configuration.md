# Configuration

Rounds is configured through environment variables. The root `.env.example` is the source of truth for Docker Compose deployments.

## Files

- `.env.example`: template for Docker Compose and production settings.
- `.env`: local machine or deployment-specific values. Do not commit real secrets.
- `frontend/.env.example`: frontend-only template, when present.
- `docker-compose.yml`: local development stack.
- `docker-compose.prod.yml`: single-box production stack.

## Host Ports

These variables control host-side ports.

| Variable | Default | Used by | Purpose |
| --- | --- | --- | --- |
| `POCKETBASE_PORT` | `8090` | dev compose | Exposes PocketBase locally. |
| `RUNNER_PORT` | `3099` | dev compose | Exposes FastAPI runner locally. |
| `FRONTEND_PORT` | `3001` | dev compose | Exposes Vite dev server locally. |
| `HTTP_PORT` | `80` | prod compose | Exposes the nginx-fronted frontend. |

Production compose exposes only `HTTP_PORT`. PocketBase and runner stay on the private Docker network.

## Production Images

`docker-compose.prod.yml` pulls published Docker Hub images by default. Equivalent GHCR images are available for users who prefer GitHub Packages.

| Variable | Default | Purpose |
| --- | --- | --- |
| `ROUNDS_IMAGE_TAG` | `latest` | Tag applied to all default service images. |
| `ROUNDS_FRONTEND_IMAGE` | `keyurgolani/rounds-frontend:${ROUNDS_IMAGE_TAG}` | Full frontend image override. |
| `ROUNDS_POCKETBASE_IMAGE` | `keyurgolani/rounds-pocketbase:${ROUNDS_IMAGE_TAG}` | Full PocketBase image override. |
| `ROUNDS_RUNNER_IMAGE` | `keyurgolani/rounds-runner:${ROUNDS_IMAGE_TAG}` | Full runner image override. |

GHCR example:

```env
ROUNDS_FRONTEND_IMAGE=ghcr.io/keyurgolani/rounds-frontend:latest
ROUNDS_POCKETBASE_IMAGE=ghcr.io/keyurgolani/rounds-pocketbase:latest
ROUNDS_RUNNER_IMAGE=ghcr.io/keyurgolani/rounds-runner:latest
```

## Runner

| Variable | Default | Purpose |
| --- | --- | --- |
| `CORS_ALLOW_ORIGINS` | `*` in dev | Comma-separated allowed frontend origins for FastAPI CORS. |
| `PDF_RENDERER_URL` | `http://pdf-renderer:4000` | Internal URL the runner forwards `/api/pdf/render` requests to. The sidecar is not exposed to the host. |
| `POCKETBASE_URL` | `http://pocketbase:8090` | Internal URL the runner uses for the public-share endpoint and AI provider credential lookups. |
| `AI_KEY_SECRET` | dev placeholder | Symmetric secret used to encrypt user-supplied AI provider API keys at rest. **Set a strong value in production**; rotating it invalidates every stored key. |
| `PB_ADMIN_EMAIL`, `PB_ADMIN_PASSWORD` | see PocketBase admin bootstrap | Used by the runner's share endpoint to obtain a cached admin token so public-share reads can bypass per-user owner rules. |

Use `*` only for local development. In production, set `CORS_ALLOW_ORIGINS` to your deployed origin, such as `https://rounds.example.com`.

## Frontend Build And Proxy

| Variable | Default | Purpose |
| --- | --- | --- |
| `VITE_POCKETBASE_URL` | blank in compose runtime | Explicit browser-facing PocketBase URL. Blank means same-origin. |
| `VITE_API_PROXY_TARGET` | `http://runner:8000` | Vite dev proxy target for runner endpoints. |
| `VITE_POCKETBASE_PROXY_TARGET` | `http://pocketbase:8090` | Vite dev proxy target for PocketBase endpoints. |
| `VITE_DEV_ALLOWED_HOSTS` | `localhost` | Comma-separated allowed hosts for Vite dev server. |

In production, the frontend should usually use same-origin PocketBase access. Leave `VITE_POCKETBASE_URL` blank unless you intentionally host PocketBase on a separate browser-visible origin.

## OAuth Buttons

| Variable | Default | Purpose |
| --- | --- | --- |
| `VITE_OAUTH_GOOGLE_ENABLED` | `false` | Shows the Google auth button on login/signup. |
| `VITE_OAUTH_GITHUB_ENABLED` | `false` | Shows the GitHub auth button on login/signup. |

These flags only control whether buttons render. The corresponding providers must also be configured in the PocketBase admin UI.

## Signup Policy

| Variable | Default | Layer | Purpose |
| --- | --- | --- | --- |
| `VITE_DISABLE_SIGNUPS` | `false` | frontend | Hides signup entry points and blocks the frontend signup flow. |
| `ROUNDS_DISABLE_SIGNUPS` | `false` | PocketBase hook | Blocks direct user creation requests. |

Set both to `true` for invite-only hosted instances:

```env
VITE_DISABLE_SIGNUPS=true
ROUNDS_DISABLE_SIGNUPS=true
```

Use both flags because frontend hiding is not a security boundary. The PocketBase hook is the server-side enforcement point.

## PocketBase Admin Bootstrap

| Variable | Default | Purpose |
| --- | --- | --- |
| `PB_ADMIN_EMAIL` | blank in prod, dev placeholder in dev compose | Optional initial PocketBase admin email. |
| `PB_ADMIN_PASSWORD` | blank in prod, dev placeholder in dev compose | Optional initial PocketBase admin password. |

On fresh setup, migration `1700000500_bootstrap_admin.js` creates the first admin when both values are set. In production, set strong credentials or create the admin manually with the PocketBase CLI.

## Recommended Production Values

```env
HTTP_PORT=80
CORS_ALLOW_ORIGINS=https://rounds.example.com
PB_ADMIN_EMAIL=admin@example.com
PB_ADMIN_PASSWORD=<strong-password>
AI_KEY_SECRET=<long-random-secret>
VITE_POCKETBASE_URL=
VITE_DISABLE_SIGNUPS=true
ROUNDS_DISABLE_SIGNUPS=true
VITE_OAUTH_GOOGLE_ENABLED=false
VITE_OAUTH_GITHUB_ENABLED=false
```

If TLS is terminated by a reverse proxy on the same host, `HTTP_PORT=80` is sufficient behind that proxy.

## Configuration Timing

The published frontend image generates `/runtime-config.js` at container startup so these frontend options remain configurable without rebuilding:

- `VITE_DISABLE_SIGNUPS`
- `VITE_OAUTH_GOOGLE_ENABLED`
- `VITE_OAUTH_GITHUB_ENABLED`

If you build the frontend outside the provided Docker image, make sure your deployment preserves the same runtime config behavior or sets the matching Vite build-time variables.
