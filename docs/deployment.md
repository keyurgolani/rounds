# Deployment

Rounds v1.0.0 is designed for self-hosted Docker Compose deployments, with Kubernetes manifests included for advanced setups.

## Docker Compose Production

```sh
cp .env.example .env
docker compose -f docker-compose.prod.yml up -d
```

Production compose runs three containers on a private network:

- `frontend`: nginx serving the Vite build and reverse-proxying backend traffic.
- `pocketbase`: auth, data, migrations, hooks, and SQLite storage.
- `runner`: FastAPI code execution service.

Only `HTTP_PORT` is exposed on the host.

The production compose file pulls published Docker Hub images by default:

- `keyurgolani/rounds-frontend`
- `keyurgolani/rounds-pocketbase`
- `keyurgolani/rounds-runner`

The same images are also published to GHCR:

- `ghcr.io/keyurgolani/rounds-frontend`
- `ghcr.io/keyurgolani/rounds-pocketbase`
- `ghcr.io/keyurgolani/rounds-runner`

Set `ROUNDS_IMAGE_TAG` to pin all services to a tag. Set `ROUNDS_FRONTEND_IMAGE`, `ROUNDS_POCKETBASE_IMAGE`, or `ROUNDS_RUNNER_IMAGE` to use a different registry or per-service tag. Left unset, the tag is `latest`.

Docker Hub publishing requires `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` GitHub repository secrets. GHCR publishing uses `GITHUB_TOKEN`.

## Image Tags

| Tag | What it is | Moves |
| --- | --- | --- |
| `1.2.3`, `v1.2.3` | One release | Never |
| `1.2` | The newest patch release of 1.2 | With each 1.2.x release |
| `latest` | The newest stable release | Only when a higher `vX.Y.Z` tag is pushed |
| `edge` | The newest commit on `main` | With every push to `main` |
| `sha-<short>` | One commit on `main` | Never |

Run a release tag in production, such as `ROUNDS_IMAGE_TAG=1.2.3`, and change it on purpose; [Upgrades](operations.md#upgrades) walks through it, backup and rollback included. `latest` is safe to follow only if you're fine with upgrades, and their migrations, arriving whenever the stack pulls. `edge` isn't for production.

Releases come from `vX.Y.Z` tags on `main`. The workflow checks that CI passed on a push of that exact commit to `main` before it publishes anything, and publishes nothing otherwise. A pre-release tag such as `v1.3.0-rc.1` publishes only `1.3.0-rc.1` and `v1.3.0-rc.1`. Nothing publishes from `next` or any other branch.

## Required Production Settings

Set these in `.env` or your deployment secret manager:

```env
HTTP_PORT=80
CORS_ALLOW_ORIGINS=https://rounds.example.com
PB_ADMIN_EMAIL=admin@example.com
PB_ADMIN_PASSWORD=<strong-password>
```

For invite-only hosted instances:

```env
VITE_DISABLE_SIGNUPS=true
ROUNDS_DISABLE_SIGNUPS=true
```

If OAuth providers are configured in PocketBase, enable frontend buttons at build time:

```env
VITE_OAUTH_GOOGLE_ENABLED=true
VITE_OAUTH_GITHUB_ENABLED=true
```

## First Boot

PocketBase applies migrations automatically:

1. Final schema creation.
2. Consolidated shared data seed.
3. Optional admin bootstrap from `PB_ADMIN_EMAIL` and `PB_ADMIN_PASSWORD`.

The admin UI isn't served on your domain. [PocketBase Admin Access](operations.md#pocketbase-admin-access) shows how to reach it.

## Backups

PocketBase stores SQLite data and uploads in the `pb_data` volume. Back it up with PocketBase stopped, so the archive is a consistent copy:

```sh
docker compose -f docker-compose.prod.yml stop pocketbase
docker run --rm \
  -v rounds_pb_data:/data:ro \
  -v "$(pwd)":/backup \
  alpine tar czf /backup/pocketbase-$(date +%F).tar.gz /data
docker compose -f docker-compose.prod.yml start pocketbase
```

[Backups and Restore](operations.md#backups) in the operations guide have the volume name and the restore commands.

## TLS

The frontend container serves plain HTTP. Put Caddy, Traefik, Cloudflare, nginx, or a managed load balancer in front for TLS.

Example Caddyfile:

```text
rounds.example.com {
  reverse_proxy localhost:80
}
```

## Kubernetes

Kustomize manifests live in `k8s/`. Update image references, signup policy, and ingress host before applying. The `images` list in `k8s/kustomization.yaml` sets every Deployment's image in one place: set `newName` to your registry's image and `newTag` to the release you run. It's the counterpart of `ROUNDS_IMAGE_TAG`, so upgrade and roll back by changing `newTag`.

```sh
kubectl apply -k k8s/
```

PocketBase should remain single-replica with a `Recreate` strategy when using SQLite. Frontend and runner can scale horizontally.

## Verification

```sh
npm --prefix frontend test
npm --prefix frontend run build
python -m pip install -r backend/requirements.txt
python -m pytest backend
```
