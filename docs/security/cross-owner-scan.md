# Cross-owner relation scan

`pocketbase/tools/scan_cross_owner.py` is a read-only operator tool. It lists
every row in a PocketBase `pb_data` database whose relation field points at a
record owned by a different account. Run it on a copy of each deployment's
`pb_data` before upgrading to the release that ships the account-scope rule
migration (`ROUNDS-00B-L01` stage 3), and hand the report to the relation
quarantine work (`ROUNDS-00B-L02`, #10).

## What it guarantees

- It copies `data.db` with the SQLite online-backup API into a private
  temporary directory, opens the copy read-only, and deletes the copy when it
  finishes. The source database is opened read-only and is never written.
- It makes no network request. It never uses the PocketBase superuser or REST
  API.
- The report holds only collection names, field names, record ids, target ids,
  per-report owner pseudonyms (`acct-01`, `acct-02`, ...), and counts. It never
  holds field values or account ids.
- It refuses to write the report inside the database's directory, never
  overwrites an existing report, and creates the report readable only by the
  operator (mode `0600`).
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
   with no network:

   ```sh
   docker run --rm --network none \
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
findings, and `2` on a usage or runtime error, in which case no report is
written.

## What it checks

An account-owned collection is one with a `user` relation to the `users` auth
collection. For every account-owned collection, the scan checks each relation
field whose target is also account-owned (or is `users`), row by row in a fixed
order: collection, field, record id. A finding is either:

- `cross_owner`: the relation points at a record whose owner differs from the
  row's owner.
- `missing_target`: the relation points at an id that no longer exists.

Relations into shared content (question banks, guides, AI-coding rounds,
take-home assignments) have no owner and are listed under
`shared_content_relations` without being checked.

When a policy file is available (the repository's
`docs/security/account-scope.v1.json` by default, or `--policy`), the report's
`policy_check` compares the database's relation fields with the policy's
`relation_exceptions`: relations the scan checked that the policy does not
list, and listed fields the database does not have. A policy with an unknown
`version` stops the scan before anything is copied. `--no-policy` skips the
comparison.

## What it does not cover

- Ids kept inside text or JSON fields: `applications.resume_variant`, the
  `links` graphs on `resumes`, `resume_variants`, and `resume_versions`, and
  `todos.mentions`. The report lists the ones present under `not_covered`; #10
  routes them to the mention, resume-link, and application migrations.
- Rows whose `user` was set to another account with no foreign relation. They
  look like that account's own rows.

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
    "relations_checked": 33,
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
  "policy_check": {"policy_version": "v1", "unlisted_in_policy": [], "listed_but_absent": []},
  "findings": [
    {"kind": "cross_owner", "collection": "...", "field": "...", "record_id": "...",
     "target_collection": "...", "target_id": "...", "owner": "acct-01", "target_owner": "acct-02"}
  ]
}
```

`findings` is sorted by collection, field, record id, and target id. Owner
pseudonyms are assigned in that order and mean nothing outside one report.
`checksum` is the SHA-256 of the canonical JSON of `version`, `relations`, and
`findings`, so two scans of the same data have the same checksum.
