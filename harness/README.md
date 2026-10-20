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

- a signed-in account's list never returns another account's rows, including
  under a filter naming another account's record or account id;
- an anonymous list returns none of an account's rows;
- a signed-in account cannot read, update, or delete another account's record
  by id, and the record comes out exactly as it was;
- an anonymous caller cannot read, update, or delete an account's record by id;
- reading, updating, or deleting another account's record answers with the
  same status and the same JSON body as the same request on a record that does
  not exist;
- an anonymous create of a complete, valid row is rejected by the create rule
  (not by field validation), and no row is left;
- a signed-in account's create of a row owned by another account is rejected
  by the create rule, and no row is left under that owner; replaying it is
  rejected every time, and naming an owner that does not exist is rejected
  with the same status;
- an update that moves a row to another account is rejected, and the row keeps
  its owner;
- an account's own update still succeeds, both leaving `user` out and resending
  its own id;
- `resume_share_views` refuses a client create or update, and the superuser
  view-tracking insert still succeeds;
- a JSON field larger than its `maxSize` is rejected, on every collection that
  has one;
- signup is rejected when the instance disables signups;
- with PocketBase unreachable, a runner write through nginx fails closed with
  503 `auth_unavailable` before the route runs;
- the live collection rules read back equal the rule table exactly (including
  the `users` manage rule).

It also runs the operator's deployment verifier,
[`verify_deployment.py`](verify_deployment.py), through the stack's real nginx
frontend and at PocketBase's own port: the routes nginx answers itself never
reach PocketBase or the runner, the routes it leaves open still work, a body
over the 1 MiB cap gets the typed 413, no shipped default login or password
opens an admin account, the live rules and the run's `pb_data` match the table,
and an admin exists. Each check needs a passing receipt, as the policy's
`deployment_checks` lists. The policy's `open_exceptions` name what stays open
at this revision (timing and error shapes, for `ROUNDS-00B-L05`).

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

With PocketBase stopped, the harness runs the read-only cross-owner relation
scan
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

The launcher builds the pocketbase, probe, runner, and frontend images, brings
PocketBase up, runs the main probe phase, recreates PocketBase with signups
disabled (the named `pb_data` volume keeps the run's accounts and rows), runs
the signup-hook probe, brings the runner and nginx frontend up and runs the
deployment verifier through them, stops PocketBase for the degraded probe,
runs the verifier's checks and the cross-owner scan on the run's `pb_data`,
prints the verdict (pass / expected-fail / fail counts), and tears the stack
down, removing the images it built. Its exit code is non-zero on any failed or
missing result.

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
