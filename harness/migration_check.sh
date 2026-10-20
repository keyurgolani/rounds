#!/usr/bin/env bash
# Behavioural checks for the account-scope rule migration (ROUNDS-00B-L01/S3).
#
# Runs one-off `pocketbase migrate up` containers against throwaway pb_data and
# reads the collection rules straight out of the resulting data.db:
#   A. migrate up produces exactly the policy's rules (create/update tightened,
#      resume_share_views null, users unchanged);
#   B. a missing collection fails the whole migration and changes no other rule;
#   C. the emergency lever locks a collection and the forward fix restores it;
#   D. rollback keeps the rules.
#
# C and D write JSON-line receipts (harness/probes/receipts.py schema) so the
# contract's recovery and rollback cells are receipt-backed; the migration-check
# CI job uploads them. PocketBase 0.22's `migrate down` confirmation needs a real
# terminal, so D does not drive it: it shows migrate up sets the rule and the
# migration's down callback writes no rule, the same property the static test
# (pocketbase/tests/test_account_scope_migration.py) asserts.
#
# Local (Finch, reuse a prebuilt image):
#   PB_IMAGE=rounds-s3-pb:test harness/migration_check.sh
# CI (Docker, build from this commit):
#   CONTAINER_BIN=docker harness/migration_check.sh
set -euo pipefail

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HARNESS_DIR}/.." && pwd)"
CONTAINER_BIN="${CONTAINER_BIN:-finch}"
PB_IMAGE="${PB_IMAGE:-}"
WORK="${HARNESS_DIR}/.migcheck/$$-$(date +%s)"
BUILT_IMAGE=""

cleanup() {
  # The containers write pb_data as root on a Linux host; the scratch
  # directories are this user's, so the files can still be removed. Never let
  # cleanup change the check's exit code.
  rm -rf "${WORK}" 2>/dev/null || true
  rmdir "${HARNESS_DIR}/.migcheck" 2>/dev/null || true
  [ -n "${BUILT_IMAGE}" ] && ${CONTAINER_BIN} rmi "${BUILT_IMAGE}" >/dev/null 2>&1 || true
}
trap cleanup EXIT
mkdir -p "${WORK}"

if [ -z "${PB_IMAGE}" ]; then
  BUILT_IMAGE="rounds-migcheck-$$:test"
  PB_IMAGE="${BUILT_IMAGE}"
  echo "--- building pocketbase image ${PB_IMAGE} ---"
  ${CONTAINER_BIN} build -t "${PB_IMAGE}" "${ROOT}/pocketbase" >/dev/null
fi

fail=0
check() { if [ "$2" = "$3" ]; then echo "PASS $1"; else echo "FAIL $1: got [$2] want [$3]"; fail=1; fi; }
check_contains() { case "$2" in *"$3"*) echo "PASS $1";; *) echo "FAIL $1: [$2] missing [$3]"; fail=1;; esac; }

# Receipts for the recovery (lever, forward fix) and rollback checks, in the
# same JSON-line schema as the two-account harness (harness/probes/receipts.py),
# so the account-scope contract's recovery and rollback cells are receipt-backed
# too. The migration-check CI job uploads them.
RECEIPTS_PATH="${RECEIPTS_PATH:-${HARNESS_DIR}/.receipts/migration-check/receipts.jsonl}"
RUN_ID="${RUN_ID:-$(date +%s)-$$}"
GIT_COMMIT="${GIT_COMMIT:-$(git -C "${ROOT}" rev-parse --short HEAD 2>/dev/null || echo unknown)}"
rm -f "${RECEIPTS_PATH}"
mkdir -p "$(dirname "${RECEIPTS_PATH}")"

emit_receipt() { # probe_id operation passed(0|1) detail
  RCPT_PROBE="$1" RCPT_OP="$2" RCPT_PASSED="$3" RCPT_DETAIL="$4" \
  RCPT_PATH="${RECEIPTS_PATH}" RCPT_RUN="${RUN_ID}" RCPT_COMMIT="${GIT_COMMIT}" \
  PROBES_DIR="${HARNESS_DIR}/probes" \
  python3 - <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["PROBES_DIR"])
from receipts import Receipt, ReceiptWriter
passed = os.environ["RCPT_PASSED"] == "1"
writer = ReceiptWriter(os.environ["RCPT_PATH"], {
    "run_id": os.environ["RCPT_RUN"],
    "commit": os.environ["RCPT_COMMIT"],
    "phase": "migration-check",
    "migrations": ["1700006000_account_scope_rules.js"],
})
writer.write(Receipt(
    probe_id=os.environ["RCPT_PROBE"],
    collection="campaigns",
    operation=os.environ["RCPT_OP"],
    actor="operator",
    expected_status=200,
    observed_status=200 if passed else 500,
    passed=passed,
    request_time_ms=0,
    detail=os.environ["RCPT_DETAIL"],
))
PYEOF
}

# Was every check since the given baseline a pass? (reads the running `fail`.)
passed_since() { [ "${fail}" -eq "$1" ] && echo 1 || echo 0; }

read_rule() { # data.db collection create|update  -> rule text, <<NULL>>, <<ABSENT>>, or <<ERROR: ...>>
  python3 "${HARNESS_DIR}/probes/read_collection_rule.py" "$1" "$2" "$3"
}

migrate_up() { # migrations_dir pb_data_dir   (exit code is PocketBase's)
  ${CONTAINER_BIN} run --rm \
    -v "$1:/mig:ro" -v "$2:/pb/pb_data" \
    "${PB_IMAGE}" /pb/pocketbase migrate up --dir=/pb/pb_data --migrationsDir=/mig
}

down_reverts_nothing() { # migration.js  -> OK when its down callback writes no rule
  python3 - "$1" <<'PYEOF'
import re, sys
src = open(sys.argv[1]).read()
m = re.search(r"\(_db\)\s*=>\s*\{([^}]*)\}", src)  # the down callback
body = m.group(1) if m else None
print("OK" if (body is not None and "saveCollection" not in body and "Rule" not in body) else "BAD")
PYEOF
}

TIGHT_CREATE='@request.auth.id != "" && @request.data.user = @request.auth.id'
TIGHT_UPDATE='user = @request.auth.id && (@request.data.user:isset = false || @request.data.user = @request.auth.id)'

echo "=== A: migrate up applies the policy rules ==="
A="${WORK}/a"; mkdir -p "${A}/pb_data"
migrate_up "${ROOT}/pocketbase/pb_migrations" "${A}/pb_data" >/dev/null
adb="${A}/pb_data/data.db"
check "A.campaigns.create.tightened"      "$(read_rule "${adb}" campaigns create)"           "${TIGHT_CREATE}"
check "A.campaigns.update.tightened"      "$(read_rule "${adb}" campaigns update)"           "${TIGHT_UPDATE}"
check "A.resume_share_views.create.null"  "$(read_rule "${adb}" resume_share_views create)"  "<<NULL>>"
check "A.resume_share_views.update.null"  "$(read_rule "${adb}" resume_share_views update)"  "<<NULL>>"
check "A.users.update.unchanged"          "$(read_rule "${adb}" users update)"               "id = @request.auth.id"

echo "=== B: a missing collection fails the migration whole ==="
B="${WORK}/b"; mkdir -p "${B}/mig" "${B}/pb_data"
cp "${ROOT}"/pocketbase/pb_migrations/*.js "${B}/mig/"
# Test-only drop of one owned leaf collection, sorted just before the stage-3
# migration. Destructive, so it is generated here and never committed.
cat > "${B}/mig/1700005999_test_drop_leaf.js" <<'JS'
migrate((db) => {
  const dao = new Dao(db);
  dao.deleteCollection(dao.findCollectionByNameOrId("exp_anecdote_bullets"));
}, (_db) => {});
JS
# PocketBase applies all pending migrations in one transaction and, on 0.22,
# logs the failure but still exits 0, so assert on the log and the rolled-back
# db rather than the exit code.
migrate_up "${B}/mig" "${B}/pb_data" > "${B}/out.log" 2>&1 || true
blog="$(cat "${B}/out.log")"
check_contains "B.error.failed-to-apply"          "${blog}" "Failed to apply migration 1700006000"
check_contains "B.error.names-missing-collection" "${blog}" "exp_anecdote_bullets is missing; no rule was changed"
# One transaction: the throw rolls the whole batch back, so no collection (and
# so no tightened rule) persists. campaigns is absent, not loose and not tight.
check "B.rolled-back.changes-nothing" "$(read_rule "${B}/pb_data/data.db" campaigns create)" "<<ABSENT>>"

echo "=== C: lever locks a collection, forward fix restores it ==="
C="${WORK}/c"; mkdir -p "${C}/mig" "${C}/pb_data"
cp "${ROOT}"/pocketbase/pb_migrations/*.js "${C}/mig/"
sed 's/__COLLECTION__/campaigns/' "${ROOT}/pocketbase/levers/lock_collection.template.js" > "${C}/mig/1700006010_lock_campaigns.js"
migrate_up "${C}/mig" "${C}/pb_data" >/dev/null
cdb="${C}/pb_data/data.db"
base=${fail}
check "C.lever.create.null" "$(read_rule "${cdb}" campaigns create)" "<<NULL>>"
check "C.lever.update.null" "$(read_rule "${cdb}" campaigns update)" "<<NULL>>"
emit_receipt "account-scope.lever.lock.applied" "lever" "$(passed_since ${base})" \
  "the write-lock lever set campaigns create and update to null (superuser only)"
# A later-timestamped forward fix, applied on the same pb_data, restores the rules.
sed 's/__COLLECTION__/campaigns/' "${ROOT}/pocketbase/levers/restore_collection.template.js" > "${C}/mig/1900000000_restore_campaigns.js"
migrate_up "${C}/mig" "${C}/pb_data" >/dev/null
base=${fail}
check "C.restore.create.tightened" "$(read_rule "${cdb}" campaigns create)" "${TIGHT_CREATE}"
check "C.restore.update.tightened" "$(read_rule "${cdb}" campaigns update)" "${TIGHT_UPDATE}"
emit_receipt "account-scope.lever.forward-fix.restored" "forward-fix" "$(passed_since ${base})" \
  "the forward fix restored campaigns create and update to the account-scope rules"

echo "=== D: rollback keeps the rules ==="
# PocketBase 0.22's migrate down confirm needs an interactive terminal, so this
# does not drive it. It shows that migrate up sets the tightened rule and that
# the migration's down callback writes no rule, so a migrate down runs a no-op
# and the rule stays. The static test asserts the same down property
# (pocketbase/tests/test_account_scope_migration.py).
D="${WORK}/d"; mkdir -p "${D}/pb_data"
migrate_up "${ROOT}/pocketbase/pb_migrations" "${D}/pb_data" >/dev/null
base=${fail}
check "D.up.tightened"         "$(read_rule "${D}/pb_data/data.db" campaigns create)" "${TIGHT_CREATE}"
check "D.down.reverts-nothing" "$(down_reverts_nothing "${ROOT}/pocketbase/pb_migrations/1700006000_account_scope_rules.js")" "OK"
emit_receipt "account-scope.migration.rollback.keeps-rules" "rollback" "$(passed_since ${base})" \
  "migrate up set the tightened create rule and the migration down writes no rule, so migrate down keeps it (migrate down not driven: 0.22 confirm needs a terminal)"

echo "--- receipts at ${RECEIPTS_PATH#"${ROOT}/"} ($(wc -l < "${RECEIPTS_PATH}" | tr -d ' ') lines) ---"
echo "=== migration_check: $([ ${fail} -eq 0 ] && echo OK || echo FAILED) ==="
exit ${fail}
