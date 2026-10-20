#!/usr/bin/env bash
# Account-scope two-account harness launcher.
#
# Sequences the phases against one compose stack and always tears it down:
#   1. bring PocketBase up with signups enabled
#   2. main phase   - create two accounts, seed fixtures, run enforced probes,
#                     read the live rules back against the policy table
#   3. recreate PocketBase with signups disabled; the named pb_data volume
#      keeps the accounts and rows from phase 2 across the restart
#   4. hook phase   - signup-disabled probe
#   5. bring the runner and the nginx frontend up (after the last PocketBase
#      recreate, since nginx looks PocketBase's address up once at start)
#   6. deploy       - the deployment verifier (harness/verify_deployment.py)
#                     through the real nginx config and at PocketBase's port
#   7. stop PocketBase; degraded - a runner write through nginx fails closed
#   8. deploy-db    - the verifier's checks on the run's pb_data (read-only)
#   9. scan         - the cross-owner relation scan against the run's pb_data
#                     (read-only) and a fixture copy (harness/probes/scan_check.py)
#  10. verdict      - require every enforced result, rule read-back, and
#                     deployment check to pass, and no pending family to leak
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

PB_ADMIN_EMAIL_V="${PB_ADMIN_EMAIL:-ops@harness.test}"
PB_ADMIN_PASSWORD_V="${PB_ADMIN_PASSWORD:-harness-admin-pw-123}"

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
  ${CONTAINER_BIN} rmi ${BUILT_IMAGES} >/dev/null 2>&1 || true
  rm -f "${ENV_FILE}"
}
trap cleanup EXIT

set_signups() { printf 'IMAGE_PREFIX=%s\nROUNDS_DISABLE_SIGNUPS=%s\n' "${IMAGE_PREFIX}" "$1" > "${ENV_FILE}"; }

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

echo "--- phase 3: recreate PocketBase (signups disabled) ---"
set_signups true
compose up -d --force-recreate pocketbase

echo "--- phase 4: hook (signup-disabled probe) ---"
probe hook

echo "--- phase 5: runner and nginx frontend up ---"
compose up -d runner frontend

echo "--- phase 6: deploy (verifier through the real nginx config) ---"
probe deploy

echo "--- phase 7: degraded (PocketBase stopped; a runner write fails closed) ---"
compose stop pocketbase
probe degraded
compose stop runner frontend

echo "--- phase 8: deploy-db (verifier on the run's pb_data, read-only) ---"
offline deploy-db

echo "--- phase 9: cross-owner scan (PocketBase stopped, pb_data read-only) ---"
set +e
offline scan \
  -e SCAN_PB_DATA="/pb_data" \
  -e SCAN_TOOL="/tools/scan_cross_owner.py" \
  -v "${ROOT}/pocketbase/tools:/tools:ro"
scan_rc=$?
set -e

echo "--- phase 10: verdict ---"
set +e
offline verdict
rc=$?
set -e

if [ -f "${RECEIPTS_DIR}/receipts.jsonl" ]; then
  echo "--- receipts at ${RECEIPTS_DIR#"${ROOT}/"}/receipts.jsonl ($(wc -l < "${RECEIPTS_DIR}/receipts.jsonl") lines) ---"
fi

if [ "${rc}" -ne 0 ] || [ "${scan_rc}" -ne 0 ]; then
  exit 1
fi
exit 0
