#!/usr/bin/env bash
# Behavioural checks for the account-scope rule migration (ROUNDS-00B-L01/S3).
#
# Runs one-off `pocketbase migrate up` containers against throwaway pb_data and
# reads the collection rules straight out of the resulting data.db to prove
# three things the static test (pocketbase/tests/test_account_scope_migration.py)
# can only assert structurally:
#   A. migrate up produces exactly the policy's rules (create/update tightened,
#      resume_share_views null, users unchanged);
#   B. a missing collection fails the whole migration and changes no other rule;
#   C. the emergency lever locks a collection and the forward fix restores it.
#
# PocketBase 0.22's `migrate down` confirmation needs a real terminal, so the
# forward-only guarantee (down keeps the rules) is covered by the static test,
# not here.
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
  rm -rf "${WORK}"
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

read_rule() { # data.db collection create|update  -> rule text, <<NULL>>, or <<ABSENT>>
  python3 - "$1" "$2" "$3" <<'PYEOF'
import sqlite3, sys
db, name, which = sys.argv[1:4]
col = "createRule" if which == "create" else "updateRule"
conn = sqlite3.connect("file:" + db + "?mode=ro", uri=True)
try:
    try:
        row = conn.execute("SELECT %s FROM _collections WHERE name=?" % col, (name,)).fetchone()
    except sqlite3.OperationalError:
        # No _collections table at all: the whole batch rolled back.
        row = None
finally:
    conn.close()
print("<<ABSENT>>" if row is None else ("<<NULL>>" if row[0] is None else row[0]))
PYEOF
}

migrate_up() { # migrations_dir pb_data_dir   (exit code is PocketBase's)
  ${CONTAINER_BIN} run --rm \
    -v "$1:/mig:ro" -v "$2:/pb/pb_data" \
    "${PB_IMAGE}" /pb/pocketbase migrate up --dir=/pb/pb_data --migrationsDir=/mig
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
check "C.lever.create.null" "$(read_rule "${cdb}" campaigns create)" "<<NULL>>"
check "C.lever.update.null" "$(read_rule "${cdb}" campaigns update)" "<<NULL>>"
# A later-timestamped forward fix, applied on the same pb_data, restores the rules.
sed 's/__COLLECTION__/campaigns/' "${ROOT}/pocketbase/levers/restore_collection.template.js" > "${C}/mig/1900000000_restore_campaigns.js"
migrate_up "${C}/mig" "${C}/pb_data" >/dev/null
check "C.restore.create.tightened" "$(read_rule "${cdb}" campaigns create)" "${TIGHT_CREATE}"
check "C.restore.update.tightened" "$(read_rule "${cdb}" campaigns update)" "${TIGHT_UPDATE}"

echo "=== migration_check: $([ ${fail} -eq 0 ] && echo OK || echo FAILED) ==="
exit ${fail}
