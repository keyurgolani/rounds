#!/usr/bin/env bash
# Containment conformance corpus launcher (ROUNDS-00A-L08, stage 1).
#
# Builds the stack from the commit under test (harness/compose.yml plus
# tests/conformance/compose.yml), generates the run's canaries and the
# corpus's take-home definition (conformance/overlay.py), brings up
# PocketBase and the runner, runs the corpus driver against them, writes a
# receipt, and tears everything down. No 62d4eae image is pulled.
#
#   tests/conformance/run.sh                 # local, Finch
#   COMPOSE_BIN="docker compose" tests/conformance/run.sh   # CI, Docker
#   tests/conformance/run.sh -k EX-07        # one fixture and its context
#
# Any arguments are passed through to pytest in the corpus container.
set -euo pipefail

CORPUS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# tests/conformance is two levels below the repository root.
ROOT="$(cd "${CORPUS_DIR}/../.." && pwd)"
COMPOSE_BIN="${COMPOSE_BIN:-finch compose}"
CONTAINER_BIN="${CONTAINER_BIN:-${COMPOSE_BIN%% *}}"
PROJECT="${COMPOSE_PROJECT:-rounds-l08corpus}"
HARNESS_FILE="${ROOT}/harness/compose.yml"
OVERLAY_FILE="${CORPUS_DIR}/compose.yml"
# Per-project state kept inside the repo (the Finch VM shares only $HOME),
# git-ignored. Different COMPOSE_PROJECT values share nothing.
ENV_FILE="${CORPUS_DIR}/.env.${PROJECT}"
RECEIPTS_DIR="${CORPUS_DIR}/.receipts"
# The take-home definition only the corpus stack has (conformance/overlay.py).
DEFINITIONS_DIR="${CORPUS_DIR}/.definitions-${PROJECT}"
export IMAGE_PREFIX="${PROJECT}"
BUILT_IMAGES="${IMAGE_PREFIX}-pocketbase:test ${IMAGE_PREFIX}-runner:test ${IMAGE_PREFIX}-corpus:test ${IMAGE_PREFIX}-bait:test"

RUN_ID="${RUN_ID:-$(date +%s)-$$}"
GIT_COMMIT="${GIT_COMMIT:-$(git -C "${ROOT}" rev-parse --short HEAD 2>/dev/null || echo unknown)}"
CORPUS_TARGET="${CORPUS_TARGET:-ci}"

# A fresh secret-shaped canary per name. Obvious test placeholders, never a
# real secret.
rand() { openssl rand -hex 6 2>/dev/null || printf '%s%s' "${RANDOM}" "${RANDOM}"; }
CANARY_AI_KEY="canary-aikey-${RUN_ID}-$(rand)"
CANARY_ADMIN_PW="canary-pbpw-${RUN_ID}-$(rand)"
CANARY_ADMIN_EMAIL="pbadmin-${RUN_ID}-$(rand)@canary.invalid"
CANARY_ADMISSION="canary-adm-${RUN_ID}-$(rand)"
BAIT_CANARY="canary-bait-${RUN_ID}-$(rand)"

compose() { ${COMPOSE_BIN} -p "${PROJECT}" -f "${HARNESS_FILE}" -f "${OVERLAY_FILE}" --env-file "${ENV_FILE}" "$@"; }

cleanup() {
  echo "--- tearing down corpus stack ---"
  compose down -v --remove-orphans >/dev/null 2>&1 || true
  ${CONTAINER_BIN} rmi ${BUILT_IMAGES} >/dev/null 2>&1 || true
  rm -f "${ENV_FILE}"
  rm -rf "${DEFINITIONS_DIR}"
}
trap cleanup EXIT

mkdir -p "${RECEIPTS_DIR}"
rm -f "${RECEIPTS_DIR}/containment-receipt.json"
rm -rf "${DEFINITIONS_DIR}"
python3 "${CORPUS_DIR}/conformance/overlay.py" --out "${DEFINITIONS_DIR}"

# The env file both compose files read. The runner picks up the canaries as
# its environment (so a leak surfaces), and the corpus reads the same values
# to scan for them. Signups stay enabled so the corpus can make accounts.
cat > "${ENV_FILE}" <<EOF
IMAGE_PREFIX=${IMAGE_PREFIX}
RUN_ID=${RUN_ID}
GIT_COMMIT=${GIT_COMMIT}
CORPUS_TARGET=${CORPUS_TARGET}
ROUNDS_DISABLE_SIGNUPS=false
ROUNDS_GATE_EXECUTION_DEFINITIONS=enforce
ROUNDS_GATE_ENFORCE_IDEMPOTENCY=off
ROUNDS_GATE_ENFORCE_QUOTA=off
AI_KEY_SECRET=${CANARY_AI_KEY}
PB_ADMIN_EMAIL=${CANARY_ADMIN_EMAIL}
PB_ADMIN_PASSWORD=${CANARY_ADMIN_PW}
ROUNDS_ADMISSION_SECRET=${CANARY_ADMISSION}
BAIT_CANARY=${BAIT_CANARY}
CORPUS_DEFINITIONS=${DEFINITIONS_DIR}
EOF

echo "--- building pocketbase, runner, corpus, and bait images ---"
compose build pocketbase runner corpus bait-metadata

echo "--- bringing up PocketBase, the runner, and the bait decoys ---"
# The bait decoys bring up the internal bait network and idle on it (the
# fixtures that exercise them are pending rows); PocketBase and the runner
# are what the stage-1 fixtures drive.
compose up -d pocketbase runner bait-metadata bait-rfc1918 bait-dns

echo "--- running the containment corpus ---"
# Run the driver as a one-off container on the app network, like #9's
# probe runner, rather than `compose run`: nerdctl's `compose run` forces a
# pseudo-TTY and has no --no-TTY, so it fails with no console (CI, a
# background shell). A bare `run --rm` allocates no TTY on either runtime.
set +e
${CONTAINER_BIN} run --rm --network "${PROJECT}_default" \
  -e CORPUS_RUN=1 \
  -e POCKETBASE_URL="http://pocketbase:8090" \
  -e RUNNER_URL="http://runner:8000" \
  -e PB_ADMIN_EMAIL="${CANARY_ADMIN_EMAIL}" \
  -e PB_ADMIN_PASSWORD="${CANARY_ADMIN_PW}" \
  -e AI_KEY_SECRET="${CANARY_AI_KEY}" \
  -e ROUNDS_ADMISSION_SECRET="${CANARY_ADMISSION}" \
  -e RUN_ID="${RUN_ID}" \
  -e GIT_COMMIT="${GIT_COMMIT}" \
  -e CORPUS_TARGET="${CORPUS_TARGET}" \
  -e RECEIPTS_PATH="/out/containment-receipt.json" \
  -v "${RECEIPTS_DIR}:/out" \
  "${IMAGE_PREFIX}-corpus:test" "$@"
rc=$?
set -e

if [ -f "${RECEIPTS_DIR}/containment-receipt.json" ]; then
  echo "--- receipt at ${RECEIPTS_DIR#"${ROOT}/"}/containment-receipt.json ---"
fi

exit "${rc}"
