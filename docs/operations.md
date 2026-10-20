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
3. Check that `ROUNDS_IMAGE_TAG` in `.env` is the release that wrote the archive. PocketBase migrates whatever data it starts on, so a newer image would upgrade the restored data again.
4. Start the stack again.
5. Verify login, dashboard data, applications, interviews, todos, and guide pages.

```sh
docker compose -f docker-compose.prod.yml down
docker run --rm \
  -v rounds_pb_data:/data \
  -v "$(pwd)":/backup:ro \
  alpine sh -c 'find /data -mindepth 1 -delete && tar xzf /backup/pocketbase-2026-01-31.tar.gz -C /data --strip-components=1'
```

Use the archive's own date in place of `2026-01-31`. Nothing has started yet; once the tag is right, start the stack:

```sh
docker compose -f docker-compose.prod.yml up -d
```

Do not restore over a running PocketBase container.

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

An older image doesn't undo a newer release's migrations, so rolling back means restoring the backup from step 3 and running the tag you noted in step 2. Anything written since the upgrade is lost. Set the tag before anything starts, so the newer image never runs on the restored data.

1. Stop the stack.
2. Set `ROUNDS_IMAGE_TAG` in `.env` back to the previous tag.
3. Restore the pre-upgrade archive into `pb_data`.
4. Start the stack and run the smoke tests.

```sh
docker compose -f docker-compose.prod.yml down
# set ROUNDS_IMAGE_TAG in .env back to the previous tag
docker run --rm \
  -v rounds_pb_data:/data \
  -v "$(pwd)":/backup:ro \
  alpine sh -c 'find /data -mindepth 1 -delete && tar xzf /backup/pocketbase-2026-01-31.tar.gz -C /data --strip-components=1'
docker compose -f docker-compose.prod.yml up -d
```

### Cross-owner relation scan

Before upgrading to the release that tightens the account-scope rules, scan a copy of `pb_data` for relations that point at another account's records and hand the report to the relation quarantine work. The scan is read-only and runs on a copy taken with PocketBase stopped, not on the live volume or a backup of the running one. How to take that copy, the exact commands, what the report holds, and how long to keep it are in [docs/security/cross-owner-scan.md](security/cross-owner-scan.md).

### Relation endpoint authorization and quarantine

`1700007000_relation_endpoint_authz.js` authorizes every typed relation: a write may point a relation only at a target the same account owns, and it adds a transactional SQLite backstop for all 34 relation fields. The same migration quarantines any existing cross-owner (or missing-target) references before the backstop starts rejecting them, so a deployment that already holds such rows upgrades cleanly. A reference on an optional field is cleared; a row whose required relation points at another account (or a missing record) is moved into `relation_quarantine` and deleted, cascading or null-repairing its dependents exactly as a normal delete would. One pseudonymized report row, in the cross-owner scan's shape, is written to `relation_quarantine_reports`. `migrate down` keeps every trigger: a predicate that proves too tight is repaired with a forward-fix migration, never by reverting.

Dry-run it on a copy of each deployment first, so you see exactly what the apply will quarantine before you run it for real:

```sh
mkdir -p ~/rounds-scan/reports
docker run --rm --network none \
  -e ROUNDS_RELATION_QUARANTINE=dry-run \
  -e ROUNDS_RELATION_QUARANTINE_REPORT=/reports/quarantine-$(date +%F).json \
  -v ~/rounds-scan/pb_data:/pb/pb_data \
  -v ~/rounds-scan/reports:/reports \
  keyurgolani/rounds-pocketbase:${ROUNDS_IMAGE_TAG} \
  /pb/pocketbase migrate up --dir=/pb/pb_data --migrationsDir=/pb/pb_migrations
```

`~/rounds-scan/pb_data` is the stopped-PocketBase copy the cross-owner scan already uses; set `ROUNDS_IMAGE_TAG` to the release you are about to deploy so the copy runs the same migrations. The container's report path is `/reports/...`, which resolves outside `/pb/pb_data`. This runs the migration (the dry run writes the report and throws) without serving, and `--network none` keeps it offline.

- The report path must be set and must resolve outside `pb_data`; the migration refuses a path containing `pb_data` and refuses an unset path. Create its directory first (the migration writes the file, not the directory), and the file is written mode `0600`.
- The dry run writes the report, logs `relation_quarantine_dry_run`, then throws, so PocketBase rolls the transaction back and exits without serving. That non-zero exit is expected: judge the run by the report and the `relation_quarantine_dry_run` log line, not by the exit code. Nothing in the copy changes.
- The report's `summary` carries `owned_collections`, `relations_checked`, `rows_scanned`, `references_checked`, `cross_owner`, and `missing_target`; `findings` lists each quarantined reference with per-report account pseudonyms (`acct-01`, ...), never account ids. Keep the report and the scanned copy no longer than its `expires_at` (14 days), same as the cross-owner scan.

Deploying the real migration (no dry-run env vars) applies both changes in one transaction. An apply that quarantines anything logs `relation_quarantine_applied` with the report `checksum` and writes the one report row into `relation_quarantine_reports`; compare that checksum against the dry run you took on the copy. They match only if the live data did not change between taking the copy and the apply; a different checksum means rows that cross accounts were added or removed in that window, so re-read the applied report rather than assuming the dry run still describes it. Do not pin a pre-L02 image to avoid the migration, and do not roll back to one to undo it: the backstop and the quarantine are forward-only. The relation triggers live in `data.db`, so they keep rejecting cross-owner writes even under an older image that predates this release; what an older image loses is the relation hook and its uniform denial, so the triggers' own abort error becomes the only guard. Repair a predicate that proves too tight with a forward-fix migration, never by reverting.

After a quarantine, an operator can replay a `relation_quarantine` row through the admin API so the relation hook re-checks it (for example after the owning account is corrected). That replay is the one superuser-run step for this collection; it is recorded in [server-writes.md](security/server-writes.md).

**Alert.** Each denial logs one `relation_denied` line carrying `collection`, `field`, `operation`, and `actor` only (no ids or values). A low background rate is normal. Alert on a sustained rise in `relation_denied` per `collection`/`field` after a deploy, or on the first `relation_denied` for a `field` that never denied before: either points at a client that started sending a cross-owner or stale id, or at a predicate that is now too tight for a legitimate write.

**Dependency check.** The uniform denial depends on the relation hook being loaded: confirm `relation_endpoints.pb.js` and its sibling `relation_endpoints.v1.json` table load from `/pb/pb_hooks` at boot (a hook load error prints to the PocketBase log), then send one foreign-id create per relation family and confirm it is denied with the documented status (create `400`, update `404`, a foreign id and a nonexistent id indistinguishable). If the hook is missing, the in-database triggers still abort every cross-owner write, but the denial stops being uniform: the raw `relation endpoint denied` abort surfaces instead of the typed response.

**Repair.** A predicate that proves too tight is repaired with a new forward-fix migration, never by editing `1700007000` or rolling back. While that migration is being prepared, the immediate lever for any one collection that is wrongly accepting or rejecting a write is to set that collection's create/update rule to `null` (superuser-only) through the admin API, which stops all non-superuser writes to it until the fix ships; it never widens a rule. Record any such change in [server-writes.md](security/server-writes.md).

### Account-scope rules

`1700006000_account_scope_rules.js` sets server-derived ownership on every user-owned collection: a create must name the signed-in account (`@request.data.user = @request.auth.id`) and an update cannot reassign `user`. `resume_share_views` becomes superuser-only, so only the share viewer's admin-token insert writes it. List, view, and delete rules are unchanged, and so are the `users` rules. The policy table is [`docs/security/account-scope.v1.json`](security/account-scope.v1.json).

Deploying the release that carries it:

1. Take a fresh `pb_data` backup with PocketBase stopped.
2. Run the cross-owner relation scan (above) on a copy to see what cross-owner references exist, then dry-run the [relation endpoint authorization and quarantine](#relation-endpoint-authorization-and-quarantine) migration on the same copy; its apply clears and quarantines those references as part of the upgrade.
3. Note the accepted and denied create and update requests per collection and status in the PocketBase request logs over the retained window (5 days by default). Read them in the admin UI's Logs view, reached as in "PocketBase Admin Access" below.
4. Deploy. The migration applies on start. If one of its collections is missing, it fails whole: PocketBase logs `Failed to apply migration 1700006000_account_scope_rules.js`, changes no rule, and exits without serving, and under `restart: unless-stopped` it keeps restarting. Go back to the previous image tag while you find out why the collection is missing.
5. Compare the same counts daily for 7 days. Create or update denials rising on a collection is the alert.
6. Run [deployment verification](#deployment-verification) and clear every `FAIL`.

If a rule turns out too tight and a legitimate flow starts getting denied, fix it forward with a new migration that corrects that collection's rule. If a rule is too loose and a probe or the scan finds a foreign write, lock that collection with `pocketbase/levers/lock_collection.template.js` until the fix ships; it sets create and update to `null` so only the superuser can write. Lift the lock with the corrected rule, or with `pocketbase/levers/restore_collection.template.js` when the rules themselves were right.

After the release, review each account's `ai_providers.base_url` and any `encrypted_key`/`key_iv` pair shared across accounts. Users are not forced to re-confirm their providers.

There is no rollback. Account isolation is forward-only: `migrate down` keeps the rules, and a bad rule is repaired with a forward fix or the lever above, never by reverting. Don't use [Rolling back](#rolling-back) to undo these rules either: restoring the pre-upgrade archive brings the old rules back with the old data. `harness/migration_check.sh` exercises the migration, the fail-whole behavior, and both levers.

### Deployment verification

`harness/verify_deployment.py` checks a deployment you operate. It only reads: every request is a read, a login that should fail, or a request nginx refuses on its headers alone. It prints no email, password, or token, and it never uses `http_proxy` or any other environment proxy. It needs Python 3.9 or newer and nothing else; run it from a checkout of this repository.

- `--url`: through the public URL, the routes nginx must answer itself (`/_/`, `/api/admins`, `/api/settings`, `/api/backups`, `/api/logs`, collection schema routes, `/api/rounds/admission/`) never reach PocketBase or the runner; `/api/execute` is gone; record, auth, OAuth redirect, realtime, file, and health routes still reach PocketBase; and a body over the 1 MiB cap gets the typed 413.
- `--pb-url`: at PocketBase's own port, the development default admin login and the demo account's login fail as an admin. This URL carries your admin password and token, so it must be `https` or a loopback address such as `http://127.0.0.1:8090`; `--allow-insecure` lifts that for a private network you trust.
- `--admin-email`, with the password in `PB_ADMIN_PASSWORD`: the live rules match the rule table, and no admin account accepts a shipped default password. These are reads with your admin login.
- `--db`: on a `pb_data` copy taken with PocketBase stopped (the cross-owner scan's copy), the rules match the rule table and at least one admin exists, so PocketBase's first-admin setup is closed.
- `--admission`, with `--url`: each of the nine admitted runner routes refuses a caller with no bearer before it reads the body, with 401 `unauthenticated`, in the typed `{"detail", "code", "correlation_id"}` envelope whose id the `X-Correlation-Id` header repeats, and a body declared over the route's cap gets the typed 413. A route you turned off answers 503 instead: `route_disabled` when its own gate is off, or `definitions_disabled` for the six execution routes while `ROUNDS_GATE_EXECUTION_DEFINITIONS` is `disabled`. Name it with `--expect-disabled`, or the check fails. It sends no bearer and, for the caps, only headers, so nothing is charged or run.
- `--gates-log FILE`: a runner log saved from its start (`docker compose -f docker-compose.prod.yml logs --no-color runner > runner.log`) has the gates line, which lists every admitted route's gate and both enforcement gates with valid values, and no gate fell back from a value it doesn't know. Add `--expect-gate NAME=VALUE` (repeatable), such as `--expect-gate ENFORCE_QUOTA=enforce`, to check a value you set.
- `--expect-disabled PATH[=CODE]`, with `--url`: after you turned that route off, it answers 503 `CODE` with no bearer and with a made-up one. `CODE` is `route_disabled` (the default) for the route's own gate, or `definitions_disabled` for each of the six execution routes after you set `ROUNDS_GATE_EXECUTION_DEFINITIONS=disabled`, such as `--expect-disabled /api/run=definitions_disabled`. The [execution runbook](security/execution-runbook.md#turning-a-gate-off) has the whole disable and re-enable cycle.

The rule table is `docs/security/account-scope.v1.json` in the checkout you run from; `--policy` names another copy, and is only accepted with `--admin-email` or `--db`, which supply the rules to compare.

First check that PocketBase answers inside its container, then reach its port as in [PocketBase Admin Access](#pocketbase-admin-access) and run the checks:

```sh
docker compose -f docker-compose.prod.yml exec pocketbase wget -qO- http://127.0.0.1:8090/api/health
read -rs PB_ADMIN_PASSWORD && export PB_ADMIN_PASSWORD   # your admin's password, kept out of shell history
python3 harness/verify_deployment.py \
  --url https://your-domain \
  --pb-url http://127.0.0.1:8090 \
  --admin-email you@example.com
python3 harness/verify_deployment.py --db ~/rounds-scan/pb_data/data.db
docker compose -f docker-compose.prod.yml logs --no-color runner > runner.log
python3 harness/verify_deployment.py --url https://your-domain --admission --gates-log runner.log
```

It prints one line per check and exits `0` when nothing failed, `1` on any failure, and `2` on a usage or configuration error (after printing the results it already had).

1. `FAIL` on a denied or open route: the public URL isn't served through this repository's `frontend/nginx.conf`.
2. `INCONCLUSIVE` on the 413 check: a proxy in front of the frontend waits for the whole body, or refuses a declared size over its own cap with its own 413 page, so the frontend's own cap can't be seen from the public URL. The Kubernetes ingress in `k8s/ingress.yaml` does both: ingress-nginx buffers request bodies by default, and it answers its own 413 for a size declared over its 6 MiB `proxy-body-size`, as the AI-coding, take-home, PDF, and ATS cap checks are. Check the frontend directly through a port-forward instead: `kubectl -n rounds port-forward svc/frontend 8080:80`, then `--url http://127.0.0.1:8080`. Nothing sits in front of the frontend there, so an `INCONCLUSIVE` through the port-forward means the frontend isn't serving this repository's `frontend/nginx.conf`.
3. `FAIL` on a credential check: an admin still uses a default; change that admin's password in the admin UI.
4. `FAIL` on the admin check: PocketBase's first-admin setup is open; create an admin as above.
5. `FAIL` on an admission check: a route answered something other than the typed refusal, so it isn't behind this release's runner, or a proxy rewrote its answer. A route that is still off fails until you name it with `--expect-disabled` and the code it answers; the failure names both. `INCONCLUSIVE` on an admission cap has the same cause and fix as item 2.
6. `FAIL` on a gates check: the log has no gates line (save it from the runner's start), a gate is missing (the runner predates this release), or a value fell back from a typo; fix the value in `.env` or the `rounds-gates` ConfigMap and restart.

Quotas and idempotency across replicas, a candidate's environment and uid, and the full disable and re-enable cycle need accounts and restarts, so they run only in the harness, not against your deployment.

The harness runs the same checks through its own nginx frontend on every CI run, where nginx is the first hop and an inconclusive check fails the run.

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
