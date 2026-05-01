#!/usr/bin/env bash
# Dev-only helper: rebuild seed JSON, rebuild the PocketBase image, and
# re-trigger the idempotent seed migrations on the running stack so newly
# added questions appear without wiping pb_data. Safe to run repeatedly.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")"/../.. && pwd)"
cd "$REPO_ROOT"

echo "==> Building seed JSON (more_coding.json + more_content.json)"
python3 -m pocketbase.seeds.builder.build
python3 -m pocketbase.seeds.builder.build_more_content

echo "==> Rebuilding PocketBase docker image"
docker compose build pocketbase

echo "==> Clearing seed-migration records so they re-run on container start"
docker exec interview-pocketbase-1 sh -c "
  command -v sqlite3 >/dev/null 2>&1 || apk add --no-cache sqlite >/dev/null
  sqlite3 /pb/pb_data/data.db \"DELETE FROM _migrations WHERE file IN ('1700000200_seed_more_coding.js', '1700000700_seed_more_content.js');\"
"

echo "==> Recreating PocketBase container"
docker compose up -d --force-recreate pocketbase

echo "==> Done — new questions should be visible in the running app."
