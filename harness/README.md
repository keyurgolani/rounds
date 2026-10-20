# Account-scope security harness

A two-account harness that proves Rounds' server-derived account-scope
invariant against a PocketBase, runner, and nginx frontend stack built from
the current commit, shaped like `docker-compose.prod.yml`.

It is the harness that `ROUNDS-00B-L01` establishes and that later security
leaves (`ROUNDS-00A-L01`, `ROUNDS-00B-L05`, `ROUNDS-02-L01`,
`ROUNDS-34-L01`) run in.

## What it verifies

The rule table lives in [`docs/security/account-scope.v1.json`](../docs/security/account-scope.v1.json):
one row per account-scoped collection (the 30 user-owned collections plus
`users`), each with its migration, current and target rules, exceptions, and
the probe families that apply to it. Expected statuses come from the policy's
`deny_contract`.

The harness runs every probe family whose guarantee the current rules already
enforce, once per collection it applies to:

- a signed-in account's list never returns another account's rows;
- an anonymous list returns none of an account's rows;
- a signed-in account cannot read, update, or delete another account's record
  by id, and the record survives;
- an anonymous caller cannot read, update, or delete an account's record by id;
- an anonymous create of a complete, valid row is rejected by the create rule
  (not by field validation);
- a signed-in account's create of a row owned by another account is rejected
  by the create rule, and no row is left under that owner;
- an update that moves a row to another account is rejected, and the row keeps
  its owner;
- an account's own update still succeeds, both leaving `user` out and resending
  its own id;
- `resume_share_views` refuses a client create or update, and the superuser
  view-tracking insert still succeeds;
- a JSON field larger than its `maxSize` is rejected, on every collection that
  has one;
- signup is rejected when the instance disables signups;
- the live collection rules read back equal the rule table exactly (including
  the `users` manage rule).

A guarantee whose fix has not landed yet is listed in the policy as `pending`
with the leaf and stage that closes it, and carries no probe here: its probes
land in the pull request that fixes it. The run fails if a pending family ever
gains an implementation or produces a receipt, so the policy row and its probe
flip together. Stage 3 of `ROUNDS-00B-L01` closed the last pending families, so
none remain.

`harness/migration_check.sh` checks the rule migration itself in one-off
`pocketbase migrate up` containers: the migration produces the rule table's
rules, a missing collection fails it whole, and the write-lock lever in
[`pocketbase/levers/`](../pocketbase/levers/) locks a collection until a forward
fix restores it.

After the verdict, the harness stops PocketBase and runs the read-only
cross-owner relation scan
([`pocketbase/tools/scan_cross_owner.py`](../pocketbase/tools/scan_cross_owner.py),
[docs](../docs/security/cross-owner-scan.md)) against the run's `pb_data`
volume, mounted read-only in a container with no network. It checks that the
clean data has no findings, that the policy's relation table matches the live
schema, that a relation pointed at another account's record in a fixture copy
(a direct SQLite write to the copy, never through the API) is reported, and
that reports carry no account ids, are private, have a stable checksum, and are
refused inside `pb_data`.

## Running it

```sh
# Local (Finch):
harness/run.sh

# CI (Docker on ubuntu):
COMPOSE_BIN="docker compose" harness/run.sh

# A second, isolated run alongside the first:
COMPOSE_PROJECT=rounds-9s1-b harness/run.sh
```

The launcher builds the pocketbase, runner, and probe images, brings
PocketBase up, runs the main probe phase, runs the admission check against two
runner replicas, recreates PocketBase with signups disabled (the named
`pb_data` volume keeps the run's accounts and rows), runs the signup-hook
probe, prints the verdict (pass / expected-fail / fail counts), runs the
cross-owner scan check and the admission migration check, and tears the stack
down, removing the images and the volume it made. Its exit code is non-zero on
any failed or missing result.

## Admission state across two replicas

`ROUNDS-00A-L01` stage 3 keeps idempotency and quota state in PocketBase, so
every runner replica sees one count. The admission phase starts `runner` and
`runner-b`, two replicas of the runner image built from this commit, on the
one PocketBase, with `ROUNDS_GATE_ENFORCE_IDEMPOTENCY` and
`ROUNDS_GATE_ENFORCE_QUOTA` at `enforce` and a test `ROUNDS_ADMISSION_SECRET`
shared by PocketBase, both runners, and the probe, and
[`probes/admission_check.py`](probes/admission_check.py) checks that:

- a run completed on one replica replays on the other, and a reused or
  missing `Idempotency-Key` is refused;
- runs on both replicas land in one hourly count, and an account's in-flight
  limit and the shared demo tier's hold across them;
- a run denied at step 8 stays retryable, with no live lease, on either
  replica;
- no client sets or clears `is_demo`, the `admission_*` collections are
  superuser-only, the admission routes need a bearer, and the write routes
  need the runner key as well;
- on the real store, a lease settles once, never above what it was admitted
  for, with its window only ever brought closer; a lease the runner never
  heard about ends with the token the runner made; a duplicate of a running
  command hears when to try again; and quota `off` counts nothing.

After the scan,
[`probes/admission_migration_check.py`](probes/admission_migration_check.py)
copies the pinned PocketBase binary out of its image and, with no network,
applies `1700006100_admission.js` to a `pb_data` built from every migration
before `1700006000` (the `62d4eae` set), checks that it adds only the three
server-only collections, reverses it with `pocketbase migrate down 1` as an
operator would, checks that the data is back as it was, and applies it again.

No service publishes a host port; the probes reach services over the compose
network. Image tags, network, volume, the compose env file, and the receipts
directory all derive from the compose project name, so runs with different
`COMPOSE_PROJECT` values do not collide.

The account factory generates fresh credentials for every run and never uses
the demo account password.

## Receipts

Each probe appends one JSON line to `harness/.receipts/<project>/receipts.jsonl`
(generated, git-ignored). A receipt records the run id, commit, verified
PocketBase binary digest and architecture, migration list, probe id,
collection, operation, actor, expected and observed status, pass/fail, and
request time. Receipts carry no record contents and no secrets.

## PocketBase image

`pocketbase/Dockerfile` verifies the pinned release zip against its published
SHA-256 before unpacking, keyed on the build's target architecture, so a
tampered or truncated download fails the build. Production and CI build
`linux/amd64`; the arm64 digest only exists so this harness can build and run
the same pinned version natively on an arm64 developer machine.
