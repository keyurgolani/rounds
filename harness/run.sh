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
#   4. recreate PocketBase with signups disabled; the named pb_data volume
#      keeps the accounts and rows from phase 2 across the restart
#   5. hook phase   - signup-disabled probe
#   6. bring the runner and the nginx frontend up (after the last PocketBase
#      recreate, since nginx looks PocketBase's address up once at start)
#   7. deploy       - the deployment verifier (harness/verify_deployment.py)
#                     through the real nginx config and at PocketBase's port,
#                     with its admission and gate checks and the runner's
#                     saved startup gates line
#   8. stop PocketBase; degraded - a runner write through nginx fails closed
#   9. deploy-db    - the verifier's checks on the run's pb_data (read-only)
#  10. scan         - the cross-owner relation scan against the run's pb_data
#                     (read-only) and a fixture copy (harness/probes/scan_check.py)
#  11. verdict      - require every enforced result, rule read-back, and
#                     deployment check to pass, and no pending family to leak
#  12. admission migration - apply and reverse the admission migration with
#                     the pinned binary on a 62d4eae-shaped pb_data, with no
#                     network (harness/probes/admission_migration_check.py)
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
BUILT_IMAGES="${IMAGE_PREFIX}-pocketbase:test ${IMAGE_PREFIX}-probes:test ${IMAGE_PREFIX}-runner:test ${IMAGE_PREFIX}-frontend:test"
# The pinned PocketBase binary, copied out of its image for the migration check.
PBBIN_VOLUME="${PROJECT}_pbbin"
RUNNER_URLS="http://runner:8000,http://runner-b:8000"

PB_ADMIN_EMAIL_V="${PB_ADMIN_EMAIL:-ops@harness.test}"
PB_ADMIN_PASSWORD_V="${PB_ADMIN_PASSWORD:-harness-admin-pw-123}"
# The runner key PocketBase, both runners, and the admission probe share; a
# test placeholder, as in compose.yml.
ADMISSION_SECRET_V="${ROUNDS_ADMISSION_SECRET:-harness-admission-key-not-a-secret-0123}"

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
# it before them); both finch and docker compose accept it here.
compose() { ${COMPOSE_BIN} -p "${PROJECT}" -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" "$@"; }

cleanup() {
  echo "--- tearing down harness stack ---"
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  ${CONTAINER_BIN} volume rm "${PBBIN_VOLUME}" >/dev/null 2>&1 || true
  ${CONTAINER_BIN} rmi ${BUILT_IMAGES} >/dev/null 2>&1 || true
  rm -f "${ENV_FILE}"
}
trap cleanup EXIT

# The runners enforce idempotency and quotas for the admission phase. The
# optional second argument sets ROUNDS_GATE_RUN for the emergency phases.
set_signups() {
  printf 'IMAGE_PREFIX=%s\nROUNDS_DISABLE_SIGNUPS=%s\nROUNDS_GATE_ENFORCE_IDEMPOTENCY=enforce\nROUNDS_GATE_ENFORCE_QUOTA=enforce\nROUNDS_ADMISSION_SECRET=%s\nROUNDS_GATE_RUN=%s\n' \
    "${IMAGE_PREFIX}" "$1" "${ADMISSION_SECRET_V}" "${2:-}" > "${ENV_FILE}"
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

echo "--- building pocketbase, probes, runner, and frontend images ---"
set_signups false
compose build pocketbase probes runner frontend

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
compose stop runner runner-b frontend
compose rm -f runner runner-b frontend >/dev/null 2>&1 || true

echo "--- phase 4: recreate PocketBase (signups disabled) ---"
set_signups true
compose up -d --force-recreate pocketbase

echo "--- phase 5: hook (signup-disabled probe) ---"
probe hook

echo "--- phase 6: runner and nginx frontend up ---"
compose up -d runner frontend
capture_gates deploy

echo "--- phase 7: deploy (verifier through the real nginx config) ---"
probe deploy

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
set -e

if [ "${rc}" -ne 0 ] || [ "${scan_rc}" -ne 0 ] || [ "${admission_rc}" -ne 0 ] || [ "${migration_rc}" -ne 0 ]; then
  exit 1
fi
exit 0
