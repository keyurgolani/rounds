#!/usr/bin/env bash
# Account-scope two-account harness launcher.
#
# Sequences the phases against one compose stack and always tears it down:
#   1. bring PocketBase up with signups enabled
#   2. main phase   — create two accounts, seed fixtures, run enforced probes,
#                     read the live rules back against the policy table
#   3. recreate PocketBase with signups disabled (volume persists)
#   4. hook phase   — signup-disabled probe
#   5. verdict      — require every enforced result + rule read-back to pass,
#                     and no pending family to leak; print pass/fail counts
#
# PocketBase is built and brought up with compose; the probe container runs
# directly on the compose network so the flow is identical under Finch
# (nerdctl) and Docker and needs no TTY.
#
# Local (Finch, default):      harness/run.sh
# CI (Docker on ubuntu):       COMPOSE_BIN="docker compose" harness/run.sh
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
PROBE_IMAGE="rounds-9s1-probes:test"

PB_ADMIN_EMAIL_V="${PB_ADMIN_EMAIL:-ops@harness.test}"
PB_ADMIN_PASSWORD_V="${PB_ADMIN_PASSWORD:-harness-admin-pw-123}"

# Published PocketBase 0.22.22 release-zip digests (checksums.txt), recorded
# in the receipt as the verified binary digest for the built architecture.
PB_SHA256_AMD64="330714769484fcc77306ab9f14c25e9f4d9b4ffd8b5b16385a70199db4206978"
PB_SHA256_ARM64="a1c99caa1099de61968b66a4be536f7d85969d01ea4f8ae7e21c85194dbcc79f"
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
  rm -f "${HARNESS_DIR}/.env"
}
trap cleanup EXIT

set_signups() { printf 'ROUNDS_DISABLE_SIGNUPS=%s\n' "$1" > "${HARNESS_DIR}/.env"; }

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
compose build pocketbase probes

echo "--- phase 1: PocketBase up (signups enabled) ---"
set_signups false
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
