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

Set `ROUNDS_IMAGE_TAG` to pin all services to a tag. Set `ROUNDS_FRONTEND_IMAGE`, `ROUNDS_POCKETBASE_IMAGE`, or `ROUNDS_RUNNER_IMAGE` to use a different registry or per-service tag.

Docker Hub publishing requires `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` GitHub repository secrets. GHCR publishing uses `GITHUB_TOKEN`.

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

Admin UI is available at `https://<your-domain>/_/`.

## Backups

PocketBase stores SQLite data and uploads in the `pb_data` volume.

```sh
docker run --rm \
  -v rounds_pb_data:/data \
  -v "$(pwd)":/backup \
  alpine tar czf /backup/pocketbase-$(date +%F).tar.gz /data
```

To restore, stop the stack, extract the archive into the volume, and start the stack again.

## TLS

The frontend container serves plain HTTP. Put Caddy, Traefik, Cloudflare, nginx, or a managed load balancer in front for TLS.

Example Caddyfile:

```text
rounds.example.com {
  reverse_proxy localhost:80
}
```

## Kubernetes

Kustomize manifests live in `k8s/`. Update image references, signup policy, and ingress host before applying:

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
