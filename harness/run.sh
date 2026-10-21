#!/usr/bin/env bash
# Account-scope two-account harness launcher.
#
# Sequences the phases against one compose stack and always tears it down:
#   1. bring PocketBase up with signups enabled
#   2. main phase   - create two accounts, seed fixtures, run enforced probes,
#                     read the live rules back against the policy table
#   3. admission    - two runner replicas built from this commit on the one
#                     PocketBase, enforcing idempotency and quotas; check that
#                     they replay, count, and limit as one
#                     (harness/probes/admission_check.py)
#  3b. admission deploy - on each replica, the admitted routes' anonymous
#                     refusals and typed envelope, the runner's byte caps
#                     before the account, field and key checks before any
#                     lookup, and stage 2's closures in the built image
#                     (harness/probes/admission_deploy.py)
#  3c. emergency disable - both runner replicas and nginx restarted with
#                     ROUNDS_GATE_RUN=disabled: 503 route_disabled for every
#                     caller on each, nothing charged, other routes still admit
#  3d. re-enable    - the gate cleared and both replicas restarted: runs
#                     admitted on each
#  3e. execution store - PocketBase restarted with ROUNDS_GATE_EXECUTION_STORE
#                     on and a worker secret: the job store's routes, rules,
#                     fencing, and reaper on the real store
#                     (harness/probes/execution_check.py)
#  3f. execution workers - both replicas up with the store on: ready, and
#                     each job claimed and ended once
#  3g. execution readiness - PocketBase restarted with another secret: both
#                     replicas go unready; restarted with it, ready again
#   4. recreate PocketBase with signups disabled; the named pb_data volume
#      keeps the accounts and rows from phase 2 across the restart
#   5. hook phase   - signup-disabled probe
#   6. bring the runner and the nginx frontend up (after the last PocketBase
#      recreate, since nginx looks PocketBase's address up once at start)
#   7. deploy       - the deployment verifier (harness/verify_deployment.py)
#                     through the real nginx config and at PocketBase's port,
#                     with its admission and gate checks and the runner's
#                     saved startup gates line
#  7b. materializer reach - PocketBase reaches the snapshot materializer over
#                     the internal materialize network; the runner and nginx
#                     reach it by neither name nor address, and it has no
#                     route out (ROUNDS-00A-L04)
#   8. stop PocketBase; degraded - a runner write through nginx fails closed
#   9. deploy-db    - the verifier's checks on the run's pb_data (read-only)
#  10. scan         - the cross-owner relation scan against the run's pb_data
#                     (read-only) and a fixture copy (harness/probes/scan_check.py)
#  11. verdict      - require every enforced result, rule read-back, and
#                     deployment check to pass, and no pending family to leak
#  12. admission migration - apply and reverse the admission migration with
#                     the pinned binary on a 62d4eae-shaped pb_data, with no
#                     network (harness/probes/admission_migration_check.py)
#  12b. execution migration - the same for the execution job store's
#                     migration, on a pb_data with every earlier migration
#                     (harness/probes/execution_migration_check.py)
#  13. relation quarantine - with the pinned binary and no network: dry-run
#                     and apply the relation quarantine on a legacy pb_data
#                     holding cross-owner rows, then delete through the API on
#                     a served copy (harness/probes/relation_quarantine_check.py)
#  14. snapshot store - with the pinned binary and no network: apply the
#                     Legacy Artifact Snapshot store, show its down step keeps
#                     a non-empty store and drops an empty one, and reapply
#                     (harness/probes/snapshot_store_check.py)
#
# The stack is built and brought up with compose; the probe container runs
# directly on the compose network so the flow is identical under Finch
# (nerdctl) and Docker and needs no TTY. The stack publishes no host ports;
# everything talks over the compose network. Image tags, network, volume, the
# compose env file, and the receipts directory all derive from the compose
# project name, so two runs with different COMPOSE_PROJECT values share
# nothing and do not collide on this machine. Teardown removes the images this
# run built.
#
# Local (Finch, default):      harness/run.sh
# CI (Docker on ubuntu):       COMPOSE_BIN="docker compose" harness/run.sh
# Isolated concurrent run:     COMPOSE_PROJECT=rounds-9s1-b harness/run.sh
set -euo pipefail

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HARNESS_DIR}/.." && pwd)"
COMPOSE_BIN="${COMPOSE_BIN:-finch compose}"
# Container CLI for the one-off probe runs: first word of COMPOSE_BIN unless
# overridden (finch / docker).
CONTAINER_BIN="${CONTAINER_BIN:-${COMPOSE_BIN%% *}}"
PROJECT="${COMPOSE_PROJECT:-rounds-9s1}"
COMPOSE_FILE="${HARNESS_DIR}/compose.yml"
NETWORK="${PROJECT}_default"
# Per-project state so concurrent runs do not share an env file or receipts.
ENV_FILE="${HARNESS_DIR}/.env.${PROJECT}"
RECEIPTS_DIR="${HARNESS_DIR}/.receipts/${PROJECT}"
# Image tags, network, and volume all derive from the project name.
export IMAGE_PREFIX="${PROJECT}"
PROBE_IMAGE="${IMAGE_PREFIX}-probes:test"
BUILT_IMAGES="${IMAGE_PREFIX}-pocketbase:test ${IMAGE_PREFIX}-probes:test ${IMAGE_PREFIX}-runner:test ${IMAGE_PREFIX}-frontend:test ${IMAGE_PREFIX}-materializer:test"
# The pinned PocketBase binary, copied out of its image for the migration check.
PBBIN_VOLUME="${PROJECT}_pbbin"
RUNNER_URLS="http://runner:8000,http://runner-b:8000"

PB_ADMIN_EMAIL_V="${PB_ADMIN_EMAIL:-ops@harness.test}"
PB_ADMIN_PASSWORD_V="${PB_ADMIN_PASSWORD:-harness-admin-pw-123}"
# The runner key PocketBase, both runners, and the admission probe share; a
# test placeholder, as in compose.yml.
ADMISSION_SECRET_V="${ROUNDS_ADMISSION_SECRET:-harness-admission-key-not-a-secret-0123}"
# The execution-worker secrets the job store phases use and rotate between;
# test placeholders too.
EXECUTION_SECRET_V="${ROUNDS_EXECUTION_SECRET:-harness-execution-key-not-a-secret-0123}"
EXECUTION_ROTATED_V="harness-execution-key-rotated-not-a-secret-4567"

# The verified PocketBase binary digest comes from the Dockerfile's ARGs, the
# one source of truth, rather than a copy kept in sync here. Prod/CI build
# amd64; a native arm64 developer build records the arm64 digest.
DOCKERFILE="${ROOT}/pocketbase/Dockerfile"
PB_SHA256_AMD64="$(sed -n 's/^ARG PB_SHA256=\(.*\)$/\1/p' "${DOCKERFILE}")"
PB_SHA256_ARM64="$(sed -n 's/^ARG PB_SHA256_ARM64=\(.*\)$/\1/p' "${DOCKERFILE}")"
case "$(uname -m)" in
  arm64|aarch64) PB_BINARY_ARCH="arm64"; PB_BINARY_SHA256="${PB_SHA256_ARM64}" ;;
  *)             PB_BINARY_ARCH="amd64"; PB_BINARY_SHA256="${PB_SHA256_AMD64}" ;;
esac
# Fail loudly if the Dockerfile layout changed and the digest did not parse.
if ! printf '%s' "${PB_BINARY_SHA256}" | grep -qE '^[0-9a-f]{64}$'; then
  echo "run.sh: could not read a 64-hex PocketBase ${PB_BINARY_ARCH} digest from ${DOCKERFILE}" >&2
  exit 1
fi

RUN_ID="${RUN_ID:-$(date +%s)-$$}"
GIT_COMMIT="${GIT_COMMIT:-$(git -C "${ROOT}" rev-parse --short HEAD 2>/dev/null || echo unknown)}"

# --env-file must be an absolute path and must come after -p/-f (nerdctl rejects
# it before them); both finch and docker compose accept it here. --profile
# materializer enables the materializer, which every compose file keeps behind
# that profile so a plain deploy `up` starts without it; the flag is used
# rather than COMPOSE_PROFILES because nerdctl honours the flag but not the
# environment variable, and both finch and docker compose accept the flag.
compose() { ${COMPOSE_BIN} -p "${PROJECT}" -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" --profile materializer "$@"; }

cleanup() {
  echo "--- tearing down harness stack ---"
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  ${CONTAINER_BIN} volume rm "${PBBIN_VOLUME}" >/dev/null 2>&1 || true
  ${CONTAINER_BIN} rmi ${BUILT_IMAGES} >/dev/null 2>&1 || true
  rm -f "${ENV_FILE}"
}
trap cleanup EXIT

# The runners enforce idempotency and quotas for the admission phase. The
# optional second argument sets ROUNDS_GATE_RUN for the emergency phases;
# the third, fourth, and fifth set ROUNDS_GATE_EXECUTION_STORE and the
# worker secret PocketBase and the runners get, for the execution phases.
set_signups() {
  printf 'IMAGE_PREFIX=%s\nROUNDS_DISABLE_SIGNUPS=%s\nROUNDS_GATE_ENFORCE_IDEMPOTENCY=enforce\nROUNDS_GATE_ENFORCE_QUOTA=enforce\nROUNDS_ADMISSION_SECRET=%s\nROUNDS_GATE_RUN=%s\nROUNDS_GATE_EXECUTION_STORE=%s\nPB_EXECUTION_SECRET=%s\nRUNNER_EXECUTION_SECRET=%s\n' \
    "${IMAGE_PREFIX}" "$1" "${ADMISSION_SECRET_V}" "${2:-}" "${3:-}" "${4:-}" "${5:-}" > "${ENV_FILE}"
}

# A runner replica's startup gates line (only gate names and values,
# nothing secret), saved for the probe phase that checks it:
# gates-PHASE.log for runner, gates-PHASE-SERVICE.log for another replica.
capture_gates() {
  local phase="$1" service="${2:-runner}" line="" out
  out="${RECEIPTS_DIR}/gates-${phase}.log"
  [ "${service}" = "runner" ] || out="${RECEIPTS_DIR}/gates-${phase}-${service}.log"
  for _ in $(seq 1 60); do
    line="$(compose logs --no-color "${service}" 2>/dev/null | grep '"event":"gates"' | tail -n 1 || true)"
    [ -n "${line}" ] && break
    sleep 1
  done
  printf '%s\n' "${line}" > "${out}"
}

# Restart both runner replicas and nginx with the env file as it is now:
# removed and created again, so the new gate value applies and nginx looks
# the new runner up, while PocketBase keeps running.
restart_runners() {
  compose stop runner runner-b frontend >/dev/null 2>&1 || true
  compose rm -f runner runner-b frontend >/dev/null 2>&1 || true
  compose up -d runner runner-b frontend
}

# Phase 7b (ROUNDS-00A-L04). The materializer joins only the internal
# materialize network, which PocketBase also joins: PocketBase reaches it,
# the runner and nginx find it by neither name nor address, and it has no
# default route and can't reach the app network. One PASS or FAIL line each.
check_materializer_reach() {
  local fails=0 up=1 address="" runner_address=""
  verdict() {
    if [ "$2" -eq 0 ]; then echo "PASS $1"; else echo "FAIL $1"; fails=$((fails + 1)); fi
  }
  # Exit 0 only when the command fails, for the checks that must be refused.
  refused() { if "$@" >/dev/null 2>&1; then return 1; fi; return 0; }

  for _ in $(seq 1 30); do
    if compose exec -T pocketbase wget -q -T 3 -O /dev/null http://materializer:4100/health >/dev/null 2>&1; then
      up=0
      break
    fi
    sleep 1
  done
  verdict materializer.reach.pocketbase-by-name "${up}"

  address="$(compose exec -T materializer node -e \
    "process.stdout.write(Object.values(require('os').networkInterfaces()).flat().filter((i) => i.family === 'IPv4' && !i.internal).map((i) => i.address).join(' '))" \
    2>/dev/null || true)"
  runner_address="$(compose exec -T runner python3 -c \
    "import socket; print(socket.gethostbyname(socket.gethostname()), end='')" 2>/dev/null || true)"
  # The address checks below mean something only with both addresses known
  # and the materializer on exactly one network.
  verdict materializer.reach.addresses-known \
    "$([ -n "${address}" ] && [ "${address}" = "${address%% *}" ] && [ -n "${runner_address}" ] && echo 0 || echo 1)"

  refused compose exec -T runner python3 -c "import socket; socket.getaddrinfo('materializer', 4100)"
  verdict materializer.reach.runner-by-name-refused $?
  refused compose exec -T runner python3 -c \
    "import socket, sys; socket.create_connection((sys.argv[1], 4100), timeout=3)" "${address:-0.0.0.0}"
  verdict materializer.reach.runner-by-address-refused $?
  refused compose exec -T frontend wget -q -T 3 -O /dev/null http://materializer:4100/health
  verdict materializer.reach.frontend-by-name-refused $?
  refused compose exec -T frontend wget -q -T 3 -O /dev/null "http://${address:-0.0.0.0}:4100/health"
  verdict materializer.reach.frontend-by-address-refused $?

  # No default route: /proc/net/route lists none with destination 00000000.
  # nerdctl compose, which Finch runs, ignores `internal: true` and says so,
  # so only Docker, which CI runs, can show it.
  if [ "${CONTAINER_BIN}" = "docker" ]; then
    refused compose exec -T materializer node -e \
      "const routes = require('fs').readFileSync('/proc/net/route', 'utf8').split('\n').slice(1); process.exit(routes.some((r) => r.split(/\s+/)[1] === '00000000') ? 0 : 1)"
    verdict materializer.egress.no-default-route $?
  else
    echo "SKIP materializer.egress.no-default-route: ${COMPOSE_BIN} ignores internal networks; CI checks it under Docker"
  fi
  refused compose exec -T materializer node -e \
    "const s = require('net').connect({ host: process.argv[1], port: 8000, timeout: 3000 }); s.on('connect', () => process.exit(0)); s.on('error', () => process.exit(1)); s.on('timeout', () => process.exit(1));" \
    "${runner_address:-0.0.0.0}"
  verdict materializer.egress.runner-refused $?

  echo "materializer reach: ${fails} failed"
  [ "${fails}" -eq 0 ]
}

probe() {
  local phase="$1"
  ${CONTAINER_BIN} run --rm --network "${NETWORK}" \
    -e POCKETBASE_URL="http://pocketbase:8090" \
    -e FRONTEND_URL="http://frontend" \
    -e RUNNER_URL="http://runner:8000" \
    -e PB_ADMIN_EMAIL="${PB_ADMIN_EMAIL_V}" \
    -e PB_ADMIN_PASSWORD="${PB_ADMIN_PASSWORD_V}" \
    -e POLICY_PATH="/policy/account-scope.v1.json" \
    -e RECEIPTS_PATH="/out/receipts.jsonl" \
    -e PB_MIGRATIONS_DIR="/pb_migrations" \
    -e RUN_ID="${RUN_ID}" \
    -e GIT_COMMIT="${GIT_COMMIT}" \
    -e PB_BINARY_SHA256="${PB_BINARY_SHA256}" \
    -e PB_BINARY_ARCH="${PB_BINARY_ARCH}" \
    -e RUNNER_URLS="${RUNNER_URLS}" \
    -e ROUNDS_ADMISSION_SECRET="${ADMISSION_SECRET_V}" \
    -e ROUNDS_EXECUTION_SECRET="${EXECUTION_SECRET_V}" \
    -e ROUNDS_EXECUTION_SECRET_ROTATED="${EXECUTION_ROTATED_V}" \
    -v "${ROOT}/docs/security:/policy:ro" \
    -v "${ROOT}/pocketbase/pb_migrations:/pb_migrations:ro" \
    -v "${RECEIPTS_DIR}:/out" \
    "${PROBE_IMAGE}" "${phase}"
}

# Fresh receipts for this run.
rm -rf "${RECEIPTS_DIR}"
mkdir -p "${RECEIPTS_DIR}"

# With PocketBase stopped: the run's pb_data mounted read-only, no network.
offline() {
  local phase="$1"; shift
  ${CONTAINER_BIN} run --rm --network none \
    -e POLICY_PATH="/policy/account-scope.v1.json" \
    -e RECEIPTS_PATH="/out/receipts.jsonl" \
    -e PB_MIGRATIONS_DIR="/pb_migrations" \
    -e RUN_ID="${RUN_ID}" \
    -e GIT_COMMIT="${GIT_COMMIT}" \
    -e PB_BINARY_SHA256="${PB_BINARY_SHA256}" \
    -e PB_BINARY_ARCH="${PB_BINARY_ARCH}" \
    "$@" \
    -v "${PROJECT}_pb_data:/pb_data:ro" \
    -v "${ROOT}/docs/security:/policy:ro" \
    -v "${ROOT}/pocketbase/pb_migrations:/pb_migrations:ro" \
    -v "${RECEIPTS_DIR}:/out" \
    "${PROBE_IMAGE}" "${phase}"
}

echo "--- building pocketbase, probes, runner, frontend, and materializer images ---"
set_signups false
compose build pocketbase probes runner frontend materializer

echo "--- phase 1: PocketBase up (signups enabled) ---"
compose up -d pocketbase

echo "--- phase 2: main (accounts, fixtures, enforced probes, rule read-back) ---"
probe main

echo "--- phase 3: admission (two runner replicas on one PocketBase) ---"
compose up -d runner runner-b
set +e
probe admission
admission_rc=$?
set -e

echo "--- phase 3b: admission deploy (policy, order, caps, and stage 2 closures on both replicas) ---"
probe admission-deploy
compose stop runner runner-b

# The emergency phases run while signups are still on, so they can make
# their accounts; nginx starts with the runner each time and is removed
# again before PocketBase is recreated, since it looks addresses up once.
echo "--- phase 3c: emergency disable (ROUNDS_GATE_RUN=disabled, both replicas restarted) ---"
set_signups false disabled
restart_runners
capture_gates emergency-disable
capture_gates emergency-disable runner-b
probe emergency-disable

echo "--- phase 3d: re-enable (gate cleared, both replicas restarted) ---"
set_signups false
restart_runners
capture_gates emergency-enable
capture_gates emergency-enable runner-b
probe emergency-enable
# TODO(ROUNDS-00A-L02): before step 3 makes legacy act as disabled, a
# phase here restarts the runners and nginx with
# ROUNDS_GATE_EXECUTION_DEFINITIONS=enforce and runs the six routes on
# definition requests through nginx: both AI-coding variants and a
# test-only take-home definition. Step 2's route tests run in process.
compose stop runner runner-b frontend
compose rm -f runner runner-b frontend >/dev/null 2>&1 || true

echo "--- phase 3e: execution store (PocketBase with the store on and a worker secret) ---"
set_signups false "" on "${EXECUTION_SECRET_V}" "${EXECUTION_SECRET_V}"
compose up -d --force-recreate pocketbase
set +e
probe execution-store
execution_rc=$?
set -e

echo "--- phase 3f: execution workers (both replicas with the store on) ---"
compose up -d runner runner-b
set +e
probe execution-runners
rc_step=$?
[ "${rc_step}" -eq 0 ] || execution_rc=1

echo "--- phase 3g: execution readiness (PocketBase rotated to another secret, then the replicas) ---"
set_signups false "" on "${EXECUTION_ROTATED_V}" "${EXECUTION_SECRET_V}"
# Only PocketBase restarts; the replicas keep the old secret.
compose up -d --force-recreate pocketbase
probe execution-unready
rc_step=$?
[ "${rc_step}" -eq 0 ] || execution_rc=1
set_signups false "" on "${EXECUTION_ROTATED_V}" "${EXECUTION_ROTATED_V}"
compose stop runner runner-b >/dev/null 2>&1
compose rm -f runner runner-b >/dev/null 2>&1
compose up -d runner runner-b
probe execution-ready-again
rc_step=$?
[ "${rc_step}" -eq 0 ] || execution_rc=1
set -e
compose stop runner runner-b
compose rm -f runner runner-b >/dev/null 2>&1 || true

echo "--- phase 4: recreate PocketBase (signups disabled) ---"
set_signups true
compose up -d --force-recreate pocketbase

echo "--- phase 5: hook (signup-disabled probe) ---"
probe hook
# PocketBase came back with no worker secret, so no old one logs in.
set +e
probe execution-disabled
rc_step=$?
[ "${rc_step}" -eq 0 ] || execution_rc=1
set -e

echo "--- phase 6: runner and nginx frontend up ---"
compose up -d runner frontend
capture_gates deploy

echo "--- phase 7: deploy (verifier through the real nginx config) ---"
probe deploy

echo "--- phase 7b: materializer reach (only PocketBase reaches it; it reaches nothing) ---"
compose up -d materializer
set +e
check_materializer_reach
reach_rc=$?
set -e
compose stop materializer

echo "--- phase 8: degraded (PocketBase stopped; a runner write fails closed) ---"
compose stop pocketbase
probe degraded
compose stop runner frontend

echo "--- phase 9: deploy-db (verifier on the run's pb_data, read-only) ---"
offline deploy-db

echo "--- phase 10: cross-owner scan (PocketBase stopped, pb_data read-only) ---"
set +e
offline scan \
  -e SCAN_PB_DATA="/pb_data" \
  -e SCAN_TOOL="/tools/scan_cross_owner.py" \
  -v "${ROOT}/pocketbase/tools:/tools:ro"
scan_rc=$?
set -e

echo "--- phase 11: verdict ---"
set +e
offline verdict
rc=$?
set -e

if [ -f "${RECEIPTS_DIR}/receipts.jsonl" ]; then
  echo "--- receipts at ${RECEIPTS_DIR#"${ROOT}/"}/receipts.jsonl ($(wc -l < "${RECEIPTS_DIR}/receipts.jsonl") lines) ---"
fi

echo "--- phase 12: admission migration applied and reversed on a 62d4eae-shaped pb_data ---"
${CONTAINER_BIN} volume create "${PBBIN_VOLUME}" >/dev/null
${CONTAINER_BIN} run --rm -v "${PBBIN_VOLUME}:/out" "${IMAGE_PREFIX}-pocketbase:test" cp /pb/pocketbase /out/pocketbase
set +e
${CONTAINER_BIN} run --rm --network none \
  -e PB_BIN="/pbbin/pocketbase" \
  -e PB_MIGRATIONS_DIR="/pb_migrations" \
  -v "${PBBIN_VOLUME}:/pbbin:ro" \
  -v "${ROOT}/pocketbase/pb_migrations:/pb_migrations:ro" \
  -v "${ROOT}/pocketbase/seeds:/pb_seeds:ro" \
  "${PROBE_IMAGE}" admission-migration
migration_rc=$?

echo "--- phase 12b: execution migration applied and reversed ---"
${CONTAINER_BIN} run --rm --network none \
  -e PB_BIN="/pbbin/pocketbase" \
  -e PB_MIGRATIONS_DIR="/pb_migrations" \
  -v "${PBBIN_VOLUME}:/pbbin:ro" \
  -v "${ROOT}/pocketbase/pb_migrations:/pb_migrations:ro" \
  -v "${ROOT}/pocketbase/seeds:/pb_seeds:ro" \
  "${PROBE_IMAGE}" execution-migration
[ $? -eq 0 ] || migration_rc=1
set -e

echo "--- phase 13: relation quarantine on a legacy pb_data, then deletes on a served copy ---"
set +e
${CONTAINER_BIN} run --rm --network none \
  -e PB_BIN="/pbbin/pocketbase" \
  -e PB_MIGRATIONS_DIR="/pb_migrations" \
  -e PB_HOOKS_DIR="/pb_hooks" \
  -e PB_LEVERS_DIR="/pb_levers" \
  -v "${PBBIN_VOLUME}:/pbbin:ro" \
  -v "${ROOT}/pocketbase/pb_migrations:/pb_migrations:ro" \
  -v "${ROOT}/pocketbase/pb_hooks:/pb_hooks:ro" \
  -v "${ROOT}/pocketbase/levers:/pb_levers:ro" \
  -v "${ROOT}/pocketbase/seeds:/pb_seeds:ro" \
  "${PROBE_IMAGE}" relation-quarantine
quarantine_rc=$?
set -e

echo "--- phase 14: snapshot store applied, kept while it holds a snapshot, and reversed ---"
set +e
${CONTAINER_BIN} run --rm --network none \
  -e PB_BIN="/pbbin/pocketbase" \
  -e PB_MIGRATIONS_DIR="/pb_migrations" \
  -v "${PBBIN_VOLUME}:/pbbin:ro" \
  -v "${ROOT}/pocketbase/pb_migrations:/pb_migrations:ro" \
  -v "${ROOT}/pocketbase/seeds:/pb_seeds:ro" \
  "${PROBE_IMAGE}" snapshot-store
snapshot_rc=$?
set -e

if [ "${rc}" -ne 0 ] || [ "${scan_rc}" -ne 0 ] || [ "${admission_rc}" -ne 0 ] || [ "${migration_rc}" -ne 0 ] \
   || [ "${execution_rc}" -ne 0 ] || [ "${quarantine_rc}" -ne 0 ] || [ "${reach_rc}" -ne 0 ] \
   || [ "${snapshot_rc}" -ne 0 ]; then
  exit 1
fi
exit 0
