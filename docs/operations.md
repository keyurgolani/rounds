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

Images are published to both Docker Hub and GHCR. Docker Hub is the default in `docker-compose.prod.yml`; set `ROUNDS_IMAGE_TAG` to pin a release, and the `ROUNDS_*_IMAGE` variables to use GHCR or per-service tags. Run a pinned release in production; see [Upgrades](#upgrades).

The publishing workflow always pushes GHCR images. Docker Hub publishing requires repository secrets named `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`. A push to `main` publishes `edge` and `sha-<short>`. A `vX.Y.Z` tag publishes the release tags and `latest`, once CI has passed on that commit; [image tags](deployment.md#image-tags) has the details.

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

PocketBase health is checked through the proxied API:

```sh
curl -s http://localhost:${HTTP_PORT:-80}/api/health
```

## Logs

```sh
docker compose -f docker-compose.prod.yml logs -f frontend
docker compose -f docker-compose.prod.yml logs -f pocketbase
docker compose -f docker-compose.prod.yml logs -f runner
```

Use PocketBase logs for auth, migrations, hooks, and data-layer issues. Use runner logs for coding execution failures. Use frontend logs for nginx routing and static serving issues.

## Backups

PocketBase stores SQLite data and uploads in the `pb_data` Docker volume. Back it up regularly, with PocketBase stopped. SQLite keeps recent writes in a separate WAL file while it runs, so a copy of a running database can be missing writes or fail to open. The stop lasts as long as the archive takes; the app shows errors until PocketBase is back.

```sh
docker compose -f docker-compose.prod.yml stop pocketbase
docker run --rm \
  -v rounds_pb_data:/data:ro \
  -v "$(pwd)":/backup \
  alpine tar czf /backup/pocketbase-$(date +%F).tar.gz /data
docker compose -f docker-compose.prod.yml start pocketbase
```

The volume is named after the compose project, which defaults to the checkout's directory name, so `rounds_pb_data` assumes a checkout named `rounds`; `docker volume ls` shows yours. Check that each archive isn't empty, and test a restore on another host now and then.

## Restore

1. Stop the stack.
2. Empty the `pb_data` volume and extract the backup archive into it.
3. Start the stack again.
4. Verify login, dashboard data, applications, interviews, todos, and guide pages.

```sh
docker compose -f docker-compose.prod.yml down
docker run --rm \
  -v rounds_pb_data:/data \
  -v "$(pwd)":/backup:ro \
  alpine sh -c 'find /data -mindepth 1 -delete && tar xzf /backup/pocketbase-2026-01-31.tar.gz -C /data --strip-components=1'
docker compose -f docker-compose.prod.yml up -d
```

Use the archive's own date in place of `2026-01-31`. Do not restore over a running PocketBase container.

## Upgrades

PocketBase applies a release's new migrations when it starts, and an older image can't undo them. So pin the release you run, back up first, and upgrade on purpose. `latest` moves to each new stable release, and an install that pulls it can upgrade on any restart. [Image tags](deployment.md#image-tags) lists what each tag follows.

1. Read the release notes and the migrations the release adds.
2. Note the tag you run now; rolling back goes to it.
3. Stop PocketBase and back up `pb_data` as in [Backups](#backups). Keep that archive until the upgrade has run a while.
4. Set `ROUNDS_IMAGE_TAG` in `.env` to the new release, for example `ROUNDS_IMAGE_TAG=1.2.3`.
5. Pull and start, then watch PocketBase's log for migration errors.
6. Run the smoke tests.

```sh
docker compose -f docker-compose.prod.yml stop pocketbase
# back up pb_data as in Backups, then set ROUNDS_IMAGE_TAG in .env
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml logs -f pocketbase
```

On Kubernetes, scale PocketBase to 0 and back up its volume, then set `newTag` for each image in `k8s/kustomization.yaml` and apply.

### Rolling back

An older image doesn't undo a newer release's migrations, so rolling back means restoring the backup from step 3 and running the tag you noted in step 2. Anything written since the upgrade is lost.

1. Stop the stack.
2. Restore the pre-upgrade archive as in [Restore](#restore).
3. Set `ROUNDS_IMAGE_TAG` back to the previous tag.
4. Start the stack and run the smoke tests.

### Cross-owner relation scan

Before upgrading to the release that tightens the account-scope rules, scan a copy of `pb_data` for relations that point at another account's records and hand the report to the relation quarantine work. The scan is read-only and runs on a copy taken with PocketBase stopped, not on the live volume or a backup of the running one. How to take that copy, the exact commands, what the report holds, and how long to keep it are in [docs/security/cross-owner-scan.md](security/cross-owner-scan.md).

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

The frontend's nginx answers 404 for the admin UI (`/_/`) and PocketBase's admin API, so neither is reachable on your domain. Reach the admin UI on the host instead.

With compose, publish PocketBase on the host's loopback for the session with an override file kept outside the repo, for example `admin.override.yml`:

```yaml
services:
  pocketbase:
    ports:
      - "127.0.0.1:8090:8090"
```

```sh
docker compose -f docker-compose.prod.yml -f admin.override.yml up -d pocketbase
ssh -L 8090:127.0.0.1:8090 you@your-server   # from your machine
```

Open `http://127.0.0.1:8090/_/`, and when you're done run `docker compose -f docker-compose.prod.yml up -d pocketbase` to drop the port again. Restart the frontend afterwards too, since its nginx looks PocketBase's address up once at startup.

On k8s, forward the Service:

```sh
kubectl -n rounds port-forward svc/pocketbase 8090:8090
```

Then open `http://127.0.0.1:8090/_/`.

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
