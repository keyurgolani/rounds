#!/usr/bin/env bash
# Account-scope two-account harness launcher.
#
# Sequences the phases against one compose stack and always tears it down:
#   1. bring PocketBase up with signups enabled
#   2. main phase   — create two accounts, seed fixtures, run enforced probes,
#                     read the live rules back against the policy table
#   3. recreate PocketBase with signups disabled; the named pb_data volume
#      keeps the accounts and rows from phase 2 across the restart
#   4. hook phase   — signup-disabled probe
#   5. verdict      — require every enforced result + rule read-back to pass,
#                     and no pending family to leak; print pass/fail counts
#
# PocketBase is built and brought up with compose; the probe container runs
# directly on the compose network so the flow is identical under Finch
# (nerdctl) and Docker and needs no TTY.
#
# Everything (image tags, network, volume) derives from the compose project
# name, so two runs with different COMPOSE_PROJECT values do not collide on
# this shared machine. Teardown removes the images this run built.
#
# Local (Finch, default):      harness/run.sh
# CI (Docker on ubuntu):       COMPOSE_BIN="docker compose" harness/run.sh
# Isolated concurrent run:     COMPOSE_PROJECT=rounds-9s1-b PB_HOST_PORT=8490 harness/run.sh
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

RUN_ID="${RUN_ID:-$(date +%s)-$$}"
GIT_COMMIT="${GIT_COMMIT:-$(git -C "${ROOT}" rev-parse --short HEAD 2>/dev/null || echo unknown)}"

compose() { ${COMPOSE_BIN} -p "${PROJECT}" -f "${COMPOSE_FILE}" "$@"; }

cleanup() {
  echo "--- tearing down harness stack ---"
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  ${CONTAINER_BIN} rmi ${BUILT_IMAGES} >/dev/null 2>&1 || true
  rm -f "${HARNESS_DIR}/.env"
}
trap cleanup EXIT

set_signups() { printf 'IMAGE_PREFIX=%s\nROUNDS_DISABLE_SIGNUPS=%s\n' "${IMAGE_PREFIX}" "$1" > "${HARNESS_DIR}/.env"; }

probe() {
  local phase="$1"
  ${CONTAINER_BIN} run --rm --network "${NETWORK}" \
    -e POCKETBASE_URL="http://pocketbase:8090" \
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
    -v "${HARNESS_DIR}/.receipts:/out" \
    "${PROBE_IMAGE}" "${phase}"
}

# Fresh receipts for this run.
rm -rf "${HARNESS_DIR}/.receipts"
mkdir -p "${HARNESS_DIR}/.receipts"

echo "--- building pocketbase + probes images ---"
set_signups false
compose build pocketbase probes

echo "--- phase 1: PocketBase up (signups enabled) ---"
compose up -d pocketbase

echo "--- phase 2: main (accounts, fixtures, enforced probes, rule read-back) ---"
probe main

echo "--- phase 3: recreate PocketBase (signups disabled) ---"
set_signups true
compose up -d --force-recreate pocketbase

echo "--- phase 4: hook (signup-disabled probe) ---"
probe hook

echo "--- phase 5: verdict ---"
set +e
probe verdict
rc=$?
set -e

if [ -f "${HARNESS_DIR}/.receipts/receipts.jsonl" ]; then
  echo "--- receipts at harness/.receipts/receipts.jsonl ($(wc -l < "${HARNESS_DIR}/.receipts/receipts.jsonl") lines) ---"
fi

exit "${rc}"
