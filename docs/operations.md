# Operations

This guide covers deployment, health checks, backups, upgrades, and common operational tasks for Rounds.

## Production Deployment

Single-box production deploys use Docker Compose:

```sh
cp .env.example .env
# edit .env for your domain, admin credentials, CORS, OAuth, and signup policy
docker compose -f docker-compose.prod.yml up -d
```

Production compose starts three services:

- `frontend`: nginx serving the Vite build and reverse-proxying backend traffic.
- `pocketbase`: auth, app data, migrations, hooks, SQLite, uploads.
- `runner`: FastAPI code runner.

Only the frontend port is exposed on the host.

Images are published to both Docker Hub and GHCR. Docker Hub is the default in `docker-compose.prod.yml`; set the `ROUNDS_*_IMAGE` variables to use GHCR or pinned per-service tags.

The publishing workflow always pushes GHCR images. Docker Hub publishing requires repository secrets named `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`.

## Health Checks

Check running containers:

```sh
docker compose -f docker-compose.prod.yml ps
```

Check the frontend from the host:

```sh
curl -I http://localhost:${HTTP_PORT:-80}
```

Check the runner from inside the compose network:

```sh
docker compose -f docker-compose.prod.yml exec runner python - <<'PY'
import urllib.request
print(urllib.request.urlopen('http://localhost:8000/health').read().decode())
PY
```

PocketBase health is usually checked through the proxied API or admin UI:

```sh
curl -I http://localhost:${HTTP_PORT:-80}/_/
```

## Logs

```sh
docker compose -f docker-compose.prod.yml logs -f frontend
docker compose -f docker-compose.prod.yml logs -f pocketbase
docker compose -f docker-compose.prod.yml logs -f runner
```

Use PocketBase logs for auth, migrations, hooks, and data-layer issues. Use runner logs for coding execution failures. Use frontend logs for nginx routing and static serving issues.

## Backups

PocketBase stores SQLite data and uploads in the `pb_data` Docker volume. Back it up regularly.

```sh
docker run --rm \
  -v rounds_pb_data:/data \
  -v "$(pwd)":/backup \
  alpine tar czf /backup/pocketbase-$(date +%F).tar.gz /data
```

Validate that backup files are non-empty and periodically test restore on a non-production host.

## Restore

1. Stop the stack.
2. Extract the backup archive into the `pb_data` volume.
3. Start the stack again.
4. Verify login, dashboard data, applications, interviews, todos, and guide pages.

Example outline:

```sh
docker compose -f docker-compose.prod.yml down
# restore archive contents into the pb_data volume
docker compose -f docker-compose.prod.yml up -d
```

Do not restore over a running PocketBase container.

## Upgrades

1. Read release notes or changed migrations before deploying.
2. Take a fresh `pb_data` backup.
3. Pull the desired image tag and restart production compose.
4. Watch PocketBase logs for migration errors.
5. Run smoke tests.

```sh
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml logs -f pocketbase
```

## Smoke Test Checklist

After deploy or restore, verify:

- Login works.
- Signup policy matches the intended instance policy.
- Dashboard loads without API errors.
- Guide pages load for System Design, Coding, and Behavioral.
- Question lists and detail pages load.
- Code runner can run and evaluate a sample coding problem.
- Application creation works.
- Interview scheduling works.
- Todo creation works.
- Campaign switching works.
- Command center opens with `Cmd/Ctrl+K` and can create records.

## TLS

The frontend container serves plain HTTP. Terminate TLS with a reverse proxy or managed load balancer.

Example Caddyfile:

```text
rounds.example.com {
  reverse_proxy localhost:80
}
```

When TLS is terminated externally, set `CORS_ALLOW_ORIGINS` to the public HTTPS origin.

## Signup Lockdown

For hosted or invite-only instances, set both flags:

```env
VITE_DISABLE_SIGNUPS=true
ROUNDS_DISABLE_SIGNUPS=true
```

The published frontend image applies these flags at container startup through `/runtime-config.js`, so no local image rebuild is required.

## PocketBase Admin Access

The admin UI is available at:

```text
https://<your-domain>/_/
```

If `PB_ADMIN_EMAIL` and `PB_ADMIN_PASSWORD` were not set on first boot, create an admin manually:

```sh
docker compose -f docker-compose.prod.yml exec pocketbase /pb/pocketbase admin create admin@example.com <password>
```

## Kubernetes Notes

Kustomize manifests live in `k8s/`.

PocketBase should stay single-replica with SQLite storage. Use a `Recreate` deployment strategy to avoid multiple writers. Frontend and runner can scale horizontally.

Before applying manifests, update:

- image references
- ingress host
- signup policy
- CORS origins
- persistent volume settings

## Common Issues

### Signup UI is hidden but users can still be created

Set `ROUNDS_DISABLE_SIGNUPS=true`. `VITE_DISABLE_SIGNUPS` only affects frontend rendering.

### OAuth buttons show but sign-in fails

The Vite flags only render buttons. Configure the matching OAuth provider in PocketBase admin settings.

### Code runner fails from the browser

Check that `/api/run` and `/api/evaluate` are routed to the runner. In development, inspect `frontend/vite.config.ts`. In production, inspect the frontend nginx config and runner logs.

### PocketBase data disappears after restart

Confirm the `pb_data` Docker volume exists and is mounted into the PocketBase container. Do not run production without persistent storage.

### Frontend config changes do not appear

Restart the frontend container so `/runtime-config.js` is regenerated from the latest environment variables. If you are using a custom frontend image that does not include the runtime config entrypoint, rebuild it with the desired `VITE_*` values.
