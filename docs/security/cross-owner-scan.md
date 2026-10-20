# Cross-owner relation scan

`pocketbase/tools/scan_cross_owner.py` is a read-only operator tool. It lists
every row in a PocketBase `pb_data` database whose relation field points at a
record owned by a different account. Run it on a copy of each deployment's
`pb_data` before upgrading to the release that ships the account-scope rule
migration (`ROUNDS-00B-L01` stage 3), and hand the report to the relation
quarantine work (`ROUNDS-00B-L02`, #10).

## What it guarantees

- It copies `data.db` and its write-ahead log (`data.db-wal`, when present)
  into a private temporary directory with plain file reads, retrying if they
  change while they are copied, then copies that with the SQLite online-backup
  API into a scan copy it opens read-only. It never opens the source with
  SQLite and never creates or changes anything in the source directory, so a
  read-only mount works. It deletes every copy when it finishes.
- It makes no network request. It never uses the PocketBase superuser or REST
  API.
- The report holds only collection names, field names, record ids, target ids,
  per-report owner pseudonyms (`acct-01`, `acct-02`, ...), and counts. It never
  holds field values or account ids: a target id that is itself an account (a
  relation into `users`) is replaced with that account's pseudonym.
- It refuses to write the report inside the database's directory (compared by
  directory identity, so a symlink or a differently cased path can't get
  around it), never overwrites an existing report, and creates the report
  readable only by the operator (mode `0600`). It checks the database, the
  report and work locations, and the policy before it creates anything.
- It needs Python 3.9 or newer and nothing outside the standard library.

The report is operator-only. Delete it, and the `pb_data` copy you scanned,
within 14 days (the report's `expires_at`).

## Run it on a deployment

1. Take a backup of the `pb_data` volume as described in
   [Backups](../operations.md#backups). For a consistent copy, stop PocketBase
   first and start it again afterwards:

   ```sh
   docker compose -f docker-compose.prod.yml stop pocketbase
   docker run --rm \
     -v rounds_pb_data:/data \
     -v "$(pwd)":/backup \
     alpine tar czf /backup/pocketbase-$(date +%F).tar.gz /data
   docker compose -f docker-compose.prod.yml start pocketbase
   ```

2. Unpack the backup outside the live volume:

   ```sh
   mkdir -p ~/rounds-scan/pb_data ~/rounds-scan/reports
   chmod 700 ~/rounds-scan
   tar xzf pocketbase-$(date +%F).tar.gz -C ~/rounds-scan/pb_data --strip-components=1
   ```

3. From a checkout of this repository, run the scan against the copy:

   ```sh
   python3 pocketbase/tools/scan_cross_owner.py \
     --db ~/rounds-scan/pb_data/data.db \
     --out ~/rounds-scan/reports/cross-owner-$(date +%F).json
   ```

   Without Python on the host, run the same command in a throwaway container
   with no network, as your own user so the `0600` report stays readable to
   you:

   ```sh
   docker run --rm --network none --user "$(id -u):$(id -g)" \
     -v ~/rounds-scan/pb_data:/pb_data:ro \
     -v ~/rounds-scan/reports:/reports \
     -v "$(pwd)/pocketbase/tools":/tools:ro \
     -v "$(pwd)/docs/security":/policy:ro \
     python:3.12-slim python /tools/scan_cross_owner.py \
       --db /pb_data/data.db \
       --policy /policy/account-scope.v1.json \
       --out /reports/cross-owner-$(date +%F).json
   ```

4. Hand the report to #10. Then delete the unpacked copy, the backup archive
   if you made it only for the scan, and the report within 14 days:

   ```sh
   rm -rf ~/rounds-scan
   ```

On Kubernetes, take the copy the way you take backups (for example a volume
snapshot, or a helper pod that mounts the PocketBase PVC while `pocketbase` is
scaled to 0) and run step 3 against it.

The tool exits `0` when the scan finds nothing, `1` when the report lists
findings, `2` on a usage or runtime error (no report is written), and `3` when
the scan finished but the policy check failed, so the scan may be incomplete
(see `policy_check` in the report).

## What it checks

An account-owned collection is one whose owner field is a relation to the
`users` auth collection. The owner field comes from the collection's
`owner_field` in the policy, or is `user` for a collection the policy does not
list. For every account-owned collection, the scan checks each relation field
whose target is also account-owned (or is `users`), row by row in a fixed
order: collection, field, record id. A finding is either:

- `cross_owner`: the relation points at a record whose owner differs from the
  row's owner.
- `missing_target`: the relation points at an id that no longer exists.

Relations into shared content (question banks, guides, AI-coding rounds,
take-home assignments) have no owner and are listed under
`shared_content_relations` without being checked.

When a policy file is available (the repository's
`docs/security/account-scope.v1.json` by default, or `--policy`), the report's
`policy_check` compares the database with the policy. It fails (`ok` is false,
exit code `3`) when the scan checked a relation the policy's
`relation_exceptions` does not list (`unlisted_in_policy`, the policy is
stale), or when a collection the policy lists exists without its owner field
(`owner_field_missing`; the scan would otherwise treat it as shared content and
skip it). Policy entries this database does not have at all, which an older
release can legitimately lack (`listed_but_absent`, `collections_absent`), are
reported without failing the check. A policy with an unknown `version` stops
the scan before anything is copied. `--no-policy` skips the comparison.

## What it does not cover

- Ids kept inside text or JSON fields: `applications.resume_variant`, the
  `links` graphs on `resumes`, `resume_variants`, and `resume_versions`, and
  `todos.mentions`. The report lists the ones present under `not_covered`; #10
  routes them to the mention, resume-link, and application migrations.
- Rows whose owner field was set to another account with no foreign relation.
  They look like that account's own rows.

## Report format

```json
{
  "kind": "rounds.cross-owner-scan",
  "version": "v1",
  "generated_at": "2026-10-20T08:00:00Z",
  "expires_at": "2026-11-03T08:00:00Z",
  "retention_days": 14,
  "checksum": "sha256:...",
  "migrations": {"applied": 25, "last": "1700005100_drop_resume_bullets.js"},
  "summary": {
    "owned_collections": 30,
    "relations_checked": 34,
    "rows_scanned": 0,
    "references_checked": 0,
    "cross_owner": 0,
    "missing_target": 0
  },
  "relations": [
    {"collection": "todos", "field": "campaign", "target_collection": "campaigns",
     "rows": 0, "references": 0, "cross_owner": 0, "missing_target": 0}
  ],
  "shared_content_relations": [
    {"collection": "ai_coding_drafts", "field": "round", "target_collection": "ai_coding_rounds"}
  ],
  "not_covered": [
    {"collection": "todos", "field": "mentions", "reason": "JSON mention tokens"}
  ],
  "policy_check": {"policy_version": "v1", "ok": true, "unlisted_in_policy": [],
                   "owner_field_missing": [], "listed_but_absent": [], "collections_absent": []},
  "findings": [
    {"kind": "cross_owner", "collection": "...", "field": "...", "record_id": "...",
     "target_collection": "...", "target_id": "...", "owner": "acct-01", "target_owner": "acct-02"}
  ]
}
```

`findings` is sorted by collection, field, record id, and target id. Owner
pseudonyms are assigned in that order and mean nothing outside one report; a
target id that is an account uses the same pseudonym as that account.
`checksum` is the SHA-256 of the canonical JSON of `version`, `relations`, and
`findings`, so two scans of the same data have the same checksum.
