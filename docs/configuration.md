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
| `POCKETBASE_PORT` | `8090` | dev compose | Exposes PocketBase on `127.0.0.1`. |
| `RUNNER_PORT` | `3099` | dev compose | Exposes FastAPI runner on `127.0.0.1`. |
| `FRONTEND_PORT` | `3001` | dev compose | Exposes Vite dev server on `127.0.0.1`. |
| `HTTP_PORT` | `80` | prod compose | Exposes the nginx-fronted frontend. |

Dev compose publishes its three ports on `127.0.0.1` only, since its admin login is a development placeholder; reach them from another machine through an SSH tunnel (`ssh -L 3001:127.0.0.1:3001 host`). Production compose exposes only `HTTP_PORT`. PocketBase and runner stay on the private Docker network.

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
| `ROUNDS_ADMISSION_SECRET` | blank; dev compose sets a placeholder | The key the runner sends with every write to the admission store. Set the same value, at least 32 printable characters, on PocketBase and every runner replica. Without it the runner can't reach the store, so admission records `quota_unavailable` in observe mode and answers it in enforce mode. Candidate processes never get it. |
| `ROUNDS_EXECUTION_SECRET` | blank, with no default in either compose file | The password the runner logs in to the execution job store with, as `execution-worker`. Set the same value, 32 to 72 printable characters with no spaces, on PocketBase and every runner replica before `ROUNDS_GATE_EXECUTION_STORE` is `on`. Without it nothing can log in as `execution-worker`, the runner starts no worker, and `/ready` stays ready. Candidate processes never get it. |
| `ROUNDS_SHARE_RESOLVER_PASSWORD` | blank, with no default in either compose file | The password the runner logs in with as `share-resolver` to resolve share links. Set the same value, 32 to 72 printable characters with no spaces, on PocketBase and every runner replica before you set `ROUNDS_GATE_SHARE_CAPABILITY_RESOLUTION=enabled`. Without it nothing can log in as `share-resolver`, and every share link answers the uniform not-found. Candidate processes never get it. |
| `ROUNDS_TRUSTED_PROXY_CIDRS` | blank (loopback and the RFC 1918 ranges) | The addresses nginx reaches the runner from, whose `X-Real-IP` the share resolver's throttle counts a client by, as comma-separated CIDRs; any other peer counts as the client. The default covers nginx in the compose files and on k8s. A proxy in front of nginx is `ROUNDS_FRONTEND_REAL_IP_FROM`'s, not this one's. `none` trusts no proxy. A value that can't be read trusts none and logs one error. |

Use `*` only for local development. In production, set `CORS_ALLOW_ORIGINS` to your deployed origin, such as `https://rounds.example.com`.

## Frontend Build And Proxy

| Variable | Default | Purpose |
| --- | --- | --- |
| `VITE_POCKETBASE_URL` | blank in compose runtime | Explicit browser-facing PocketBase URL. Blank means same-origin. |
| `VITE_API_PROXY_TARGET` | `http://runner:8000` | Vite dev proxy target for runner endpoints. |
| `VITE_POCKETBASE_PROXY_TARGET` | `http://pocketbase:8090` | Vite dev proxy target for PocketBase endpoints. |
| `VITE_DEV_ALLOWED_HOSTS` | `localhost` | Comma-separated allowed hosts for Vite dev server. |

In production, the frontend should usually use same-origin PocketBase access. Leave `VITE_POCKETBASE_URL` blank unless you intentionally host PocketBase on a separate browser-visible origin.

The Vite dev proxy (`frontend/devProxy.ts`) answers 404 for the paths production nginx never proxies: PocketBase's admin UI and admin APIs, collection metadata, the admission and execution hook routes, and the execution service record's routes. Like nginx, it matches them on the decoded path, and the collection paths in any case. In dev, open the admin UI on PocketBase's own port.

## OAuth Buttons

| Variable | Default | Purpose |
| --- | --- | --- |
| `VITE_OAUTH_GOOGLE_ENABLED` | `false` | Shows the Google auth button on login/signup. |
| `VITE_OAUTH_GITHUB_ENABLED` | `false` | Shows the GitHub auth button on login/signup. |

These flags only control whether buttons render. The corresponding providers must also be configured in the PocketBase admin UI.

## Public Shares

| Variable | Default | Layer | Purpose |
| --- | --- | --- | --- |
| `ROUNDS_GATE_PUBLIC_SHARES` | blank (`enabled`) | runner | `disabled` answers every public share request, `POST /api/share/resolve`, with the uniform not-found, before any lookup. |
| `ROUNDS_DISABLE_PUBLIC_SHARES` | `false` | runner | Alias read while the gate is blank. Any value other than empty, `false`, `0`, `no`, or `off` does the same as `disabled`. |
| `ROUNDS_GATE_SHARE_CAPABILITY_RESOLUTION` | blank (`disabled`) | runner, frontend | `enabled` lets `POST /api/share/resolve` look a Share Capability up, makes `POST /api/share` CreateShare, and turns rotation on. Disabled, the default, the resolver answers the uniform not-found, `POST /api/share` answers 503 `route_disabled`, so no share link resolves and nobody can make one, and the share dialog says sharing is turned off. Set it for the runner and the frontend together. |
| `ROUNDS_FRONTEND_REAL_IP_FROM` | blank | frontend | Behind anything in front of the frontend, a front proxy, a tunnel, or the k8s ingress controller, compose included: the addresses it connects from, as comma-separated CIDRs. nginx then takes each client's address from `X-Forwarded-For`, which that proxy must send. Blank, nginx counts each client by its peer address, which is right only where nginx's own port is the public one; behind a proxy, every client then shares one count. An entry that isn't an address or a CIDR stops the container. |

Restart the runner after changing any of the first three, and the frontend after the last two. See [Public shares](operations.md#public-shares).

## Signup Policy

| Variable | Default | Layer | Purpose |
| --- | --- | --- | --- |
| `ROUNDS_GATE_SIGNUPS` | blank (`enabled`) | PocketBase hook and frontend | `disabled` blocks user creation in PocketBase and hides signup entry points in the frontend. |
| `VITE_DISABLE_SIGNUPS` | `false` | frontend | Alias read while the gate is blank. Hides signup entry points and blocks the frontend signup flow. |
| `ROUNDS_DISABLE_SIGNUPS` | `false` | PocketBase hook | Alias read while the gate is blank. Blocks direct user creation requests. |

For an invite-only hosted instance, set the gate once:

```env
ROUNDS_GATE_SIGNUPS=disabled
```

Setting both older flags to `true` still works. Frontend hiding is not a security boundary; the PocketBase hook is the server-side enforcement point. A set gate wins over the aliases, so `ROUNDS_GATE_SIGNUPS=enabled` reopens signups even when an alias is `true`.

## Demo Account

| Variable | Default | Layer | Purpose |
| --- | --- | --- | --- |
| `ROUNDS_GATE_DEMO` | blank (`disabled`) | PocketBase hooks | `enabled` turns the demo account on. |
| `ROUNDS_ENABLE_DEMO` | `false` | PocketBase hooks | Alias read while the gate is blank. `true` turns the demo account on. |
| `ROUNDS_GATE_DEMO_EXECUTION` | blank (`disabled`) | runner | `enabled` gives the demo account its code runs. Disabled, a demo account's run, evaluate, run-project, grade, take-home run, and take-home submit answer 503 `demo_execution_disabled`. |

Every install creates the demo account (`1700000600_demo_user.js`), and it stays off unless the operator turns it on, as the hosted demo does:

```env
ROUNDS_ENABLE_DEMO=true
```

Off, PocketBase refuses a demo account's sign-in with the answer a wrong password gets, and at each start gives every demo account a new random password and token key, so a session from before the restart ends, and any request a demo account's token authenticates gets 401. On or off, a demo account can change only its own name, bio, target, and avatar, can't delete itself or change its email, and can't own a share link, an AI provider, or AI settings: those writes get 403 `demo_not_permitted`, from a client or a server hook. Restart PocketBase after changing either variable.

With the demo on, its code runs stay off until the operator opens them with `ROUNDS_GATE_DEMO_EXECUTION=enabled` on every runner replica, followed by a restart. Until then a demo account's code run answers 503 `demo_execution_disabled` before anything is charged or runs, and the coding, AI-coding, and take-home pages say code runs are off in the demo and keep the draft. Other accounts, and the demo's other pages, aren't affected.

## Gates

Gates are `ROUNDS_GATE_<NAME>` switches with written defaults. Compose reads them from the root `.env`, and k8s reads them from the `rounds-gates` ConfigMap in `k8s/gates.yaml`. Three readers share the names: the runner (`backend/app/gates.py`), PocketBase (`pocketbase/pb_hooks/gates.js`), and the frontend through `runtime-config.js`, which publishes only the gates the SPA reads.

| Gate | Values | Default | Read by | Enforced |
| --- | --- | --- | --- | --- |
| `ROUNDS_GATE_SIGNUPS` | `enabled`, `disabled` | `enabled` | PocketBase, frontend | yes |
| `ROUNDS_GATE_DEMO` | `enabled`, `disabled` | `disabled` | PocketBase | yes; disabled, no demo account signs in ([Demo Account](#demo-account)) |
| `ROUNDS_GATE_DEMO_EXECUTION` | `enabled`, `disabled` | `disabled` | runner | yes; disabled, a demo account's request to the six code-run routes answers 503 `demo_execution_disabled` before anything is charged or runs, and other accounts are unchanged ([Demo Account](#demo-account)) |
| `ROUNDS_GATE_RUN` | `enabled`, `disabled` | `enabled` | runner | yes; disabled, `/api/run` answers 503 `route_disabled` |
| `ROUNDS_GATE_EVALUATE` | `enabled`, `disabled` | `enabled` | runner | yes; `/api/evaluate` |
| `ROUNDS_GATE_AI_CODING_RUN_PROJECT` | `enabled`, `disabled` | `enabled` | runner | yes; `/api/ai-coding/run-project` |
| `ROUNDS_GATE_AI_CODING_GRADE` | `enabled`, `disabled` | `enabled` | runner | yes; `/api/ai-coding/grade` |
| `ROUNDS_GATE_TAKE_HOME_RUN` | `enabled`, `disabled` | `enabled` | runner | yes; `/api/take-home/run` |
| `ROUNDS_GATE_TAKE_HOME_SUBMIT` | `enabled`, `disabled` | `enabled` | runner | yes; `/api/take-home/submit` |
| `ROUNDS_GATE_PDF_RENDER` | `enabled`, `disabled` | `enabled` | runner | yes; `/api/pdf/render`, every snapshot's render, existing ones included, and PDF export offers Print instead |
| `ROUNDS_GATE_PDF_HEALTH` | `enabled`, `disabled` | `enabled` | runner | yes; `/api/pdf/health` |
| `ROUNDS_GATE_ATS_RULE` | `enabled`, `disabled` | `enabled` | runner | yes; `/api/ai/ats-rule` |
| `ROUNDS_GATE_PAPER_FETCH` | `enabled`, `disabled` | `disabled` | runner | yes; the `paper_url` fetch in `/api/ai/improve` |
| `ROUNDS_GATE_PROVIDER_PRIVATE_NETWORK` | `enabled`, `disabled` | `disabled` | runner | yes; AI provider base URLs on private addresses (RFC 1918, RFC 6598, IPv6 ULA) |
| `ROUNDS_GATE_ENFORCE_IDEMPOTENCY` | `off`, `observe`, `enforce` | `observe` | runner | `enforce` only; `Idempotency-Key` checks and replays on the admitted routes |
| `ROUNDS_GATE_ENFORCE_QUOTA` | `off`, `observe`, `enforce` | `observe` | runner | `enforce` only; account, deployment, and demo quotas on the admitted routes |
| `ROUNDS_GATE_EXECUTION_DEFINITIONS` | `legacy`, `enforce`, `disabled` | `legacy` | runner, frontend | `legacy` loads run, evaluate, grade, run-project, and take-home from PocketBase as before; `enforce` takes only requests that name a compiled definition, which the app then sends, and runs only that definition; `disabled` answers 503 `definitions_disabled` on those six routes and keeps every draft. An unknown value closes to `disabled`. Restart the runner and the frontend together when it changes. |
| `ROUNDS_GATE_EXECUTION_STORE` | `off`, `on` | `off` | runner, PocketBase | yes; `on` serves the execution job store's routes in PocketBase and runs each runner replica's worker and reaper, and `off` answers those routes 503 `store_off` and starts no worker. An unknown value closes to `off`. Set `ROUNDS_EXECUTION_SECRET` first, and restart PocketBase and every runner replica when it changes. Run, evaluate, run-project, and take-home run go through it while `ROUNDS_GATE_EXECUTION_SCRATCH` is `on`, and grade and take-home submit while `ROUNDS_GATE_EXECUTION_GRADING` is `on`. |
| `ROUNDS_GATE_EXECUTION_SCRATCH` | `legacy`, `on`, `off` | `legacy` | runner | `legacy` runs run, evaluate, run-project, and take-home run in their request as before; `on` makes each a durable job on the execution job store, answered 202 with the job, which the page follows on `/api/execution/jobs/{id}` until it ends; `off` answers those four routes 503 `execution_disabled` before the account check and keeps every draft. `on` needs `ROUNDS_GATE_EXECUTION_STORE=on` and `ROUNDS_GATE_EXECUTION_DEFINITIONS=enforce`: without either it acts as `off`, never as `legacy`, and the runner's start logs `execution.scratch` with the setting it needs. An unknown value closes to `off`. Restart every runner replica when it changes ([Execution Job Store](operations.md#execution-job-store)). |
| `ROUNDS_GATE_EXECUTION_GRADING` | `legacy`, `on`, `off` | `legacy` | runner | `legacy` grades an AI-coding submission and a take-home submission in their request as before; `on` makes each a durable job on the execution job store, answered 202 with the job, whose graded row the server writes with its authoritative result, and serves the two review routes, which ask the account's AI provider for that result's rubric review once; `off` answers grade, take-home submit, and the review routes 503 `execution_disabled` before the account check and keeps every draft. The review routes answer only at `on`. `on` needs `ROUNDS_GATE_EXECUTION_STORE=on` and `ROUNDS_GATE_EXECUTION_DEFINITIONS=enforce`: without either it acts as `off`, never as `legacy`, and the runner's start logs `execution.grading` with the setting it needs. An unknown value closes to `off`. Restart every runner replica when it changes ([Grading Jobs](operations.md#grading-jobs)). |
| `ROUNDS_GATE_PUBLIC_SHARES` | `enabled`, `disabled` | `enabled` | runner | yes; disabled, every public share request answers the uniform not-found ([Public Shares](#public-shares)) |
| `ROUNDS_GATE_SHARE_CAPABILITY_RESOLUTION` | `enabled`, `disabled` | `disabled` | runner, frontend | yes; disabled, `POST /api/share/resolve` answers the uniform not-found before any lookup, and `POST /api/share` and rotation answer 503 `route_disabled`, so no share link resolves and nobody can make one. Opening it is the owner's step: do the others in [Public shares](operations.md#public-shares) first, and restart the runner and the frontend together when it changes |

Each route gate is that route's off switch. Set it to `disabled` and restart the runner, and the route answers 503 `route_disabled` before it reads the request; nothing else changes. [The execution runbook](security/execution-runbook.md) covers flipping and confirming each gate and what each error code means.

The two enforcement gates decide admission steps 6 and 7. `off` skips its step: with `ENFORCE_QUOTA` at `off` nothing is counted, charged, or limited, and idempotency still records each command while its own gate is on. `observe`, the default for now, checks every request, records in its `decision` line what enforcing would have answered (`would_deny`), and denies nothing. `enforce` denies: a missing key is 400 `idempotency_key_required`, a completed command's retry gets its stored response, a reused key is 409, a still-running one is 409 with `Retry-After`, an over-limit request is 429 with `Retry-After`, and an unreachable admission store, or a runner without `ROUNDS_ADMISSION_SECRET`, is 503 `quota_unavailable`. Set `ROUNDS_ADMISSION_SECRET` before enforcing; the next `v*` release sets both gates to `enforce`, and [the runbook](security/execution-runbook.md#idempotency-and-quotas) has the limits and how to read the observe lines first.

Two outbound switches start off. `PAPER_FETCH` lets `/api/ai/improve` fetch a publication's `paper_url`. `PROVIDER_PRIVATE_NETWORK` lets an AI provider base URL point at a private address, for a model server on your LAN. Enabled, every account's provider URL can reach this deployment's private network, its own services included, so enable it only when you trust every account. Loopback, link-local, and cloud metadata addresses and service names such as `pocketbase` or `*.svc` stay refused either way, with 403 `destination_denied`.

The runner looks a provider host up once per call, checks every address it gets, and connects only to one of those addresses. When an address refuses the connection or takes more than 3 seconds to connect, the runner tries the next one, all within the call's connect timeout. Provider calls don't follow redirects. The paper fetch gets the same check for the URL and for each of up to 5 redirects, and it refuses private addresses whatever `PROVIDER_PRIVATE_NETWORK` says; a refused paper URL is skipped like any other failed fetch. Provider calls and the paper fetch ignore `HTTP_PROXY` and `HTTPS_PROXY`.

Each reader resolves a gate the same way:

1. A set gate with an allowed value wins. Values are trimmed and case-insensitive.
2. A set gate with any other value takes its most restrictive value (`disabled` or `enforce`), and the reader logs an error that names the gate but not the value.
3. A blank gate falls back to the reader's alias when the alias is `true`, `1`, or `yes`. `SIGNUPS` and `DEMO` have aliases: PocketBase reads `ROUNDS_DISABLE_SIGNUPS` and `ROUNDS_ENABLE_DEMO`, and the frontend reads `VITE_DISABLE_SIGNUPS`. The runner's `ROUNDS_DISABLE_PUBLIC_SHARES`, the alias of `PUBLIC_SHARES`, fails closed instead: any value but empty, `false`, `0`, `no`, or `off` applies it.
4. Otherwise the default applies.

A process reads its gates once at startup, so a change needs a restart. The runner reads the two share gates on each request as well, and they need a restart all the same. The runner and PocketBase each log one JSON line with every gate they read, its value, and where the value came from (`default`, `env`, `alias`, or `invalid`). The frontend container passes the SPA only the gates it reads, today `ROUNDS_GATE_SIGNUPS` and `ROUNDS_GATE_EXECUTION_DEFINITIONS`, and logs each value it passes. Runner and PocketBase gates never reach the browser. Gate values aren't secret, so never put a secret in one.

<!-- privacy-settings:begin (generated by node scripts/conformance/run.mjs --write from contracts/privacy/policy.json) -->
## Privacy And Retention Settings

The runner reads these once at startup and refuses to start on a bad value, naming the setting and its bounds, or the position of the entry it refuses. The message never repeats a day count, and shows an entry's network only once it has parsed as one. Unset or empty takes the default. On Kubernetes, set them in the `rounds-runner-secrets` Secret: the runner's manifest leaves them out of `env`, where a value would hide the Secret's. The bounds come from `contracts/privacy/policy.json`; see [privacy and retention](privacy-retention.md).

| Variable | Allowed | Default | What it sets |
| --- | --- | --- | --- |
| `ROUNDS_LOG_RETENTION_DAYS` | 1 to 30 days | 14 | How long operational logs and traces are kept. |
| `ROUNDS_BACKUP_RETENTION_DAYS` | 7 to 90 days | 30 | How long encrypted backups are kept; the operator publishes the value. |
| `ROUNDS_AI_PRIVATE_ENDPOINTS` | comma-separated entries | empty | The operator-network AI endpoints: comma-separated ip:port, [ipv6]:port, cidr:port, or [ipv6-cidr]:port entries inside the private networks. |

`ROUNDS_AI_PRIVATE_ENDPOINTS` lists the AI endpoints on your own network. Each entry is `ip:port`, `[ipv6]:port`, `cidr:port`, or `[ipv6-cidr]:port`, inside 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 100.64.0.0/10, fc00::/7. An entry that names a host, or names or covers loopback, link-local, a metadata address, or a service name such as `pocketbase`, stops the runner. A private destination passes only when ROUNDS_GATE_PROVIDER_PRIVATE_NETWORK is enabled and the resolved address and port match a ROUNDS_AI_PRIVATE_ENDPOINTS entry. With the gate off, every private address is refused whatever the list says; with the gate on, an empty list refuses every private address.

Today the runner only validates these. The values take effect when their enforcing leaves land: `ROUNDS_LOG_RETENTION_DAYS` by ROUNDS-34-L05, `ROUNDS_BACKUP_RETENTION_DAYS` by ROUNDS-32-L03, `ROUNDS_AI_PRIVATE_ENDPOINTS` by ROUNDS-14-L02. Until then the private-network gate alone decides which private addresses a provider may use, as before.

<!-- privacy-settings:end -->

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
ROUNDS_ADMISSION_SECRET=<another-long-random-secret>
ROUNDS_EXECUTION_SECRET=<a-third-long-random-secret>
ROUNDS_SHARE_RESOLVER_PASSWORD=<a-fourth-long-random-secret>
VITE_POCKETBASE_URL=
ROUNDS_GATE_SIGNUPS=disabled
VITE_OAUTH_GOOGLE_ENABLED=false
VITE_OAUTH_GITHUB_ENABLED=false
```

If TLS is terminated by a reverse proxy on the same host, `HTTP_PORT=80` is sufficient behind that proxy.

## Configuration Timing

The published frontend image generates `/runtime-config.js` at container startup so these frontend options remain configurable without rebuilding:

- `VITE_DISABLE_SIGNUPS`
- `VITE_OAUTH_GOOGLE_ENABLED`
- `VITE_OAUTH_GITHUB_ENABLED`
- the gates the SPA reads, today `ROUNDS_GATE_SIGNUPS`, `ROUNDS_GATE_EXECUTION_DEFINITIONS`, and `ROUNDS_GATE_SHARE_CAPABILITY_RESOLUTION`

If you build the frontend outside the provided Docker image, make sure your deployment preserves the same runtime config behavior or sets the matching Vite build-time variables.
