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
the probe families that apply to it.

This stage runs the probe families whose guarantees the current rules already
enforce, once per collection:

- a signed-in account's list never returns another account's rows;
- an anonymous list returns none of an account's rows;
- a signed-in account cannot read another account's record by id;
- an anonymous caller cannot read an account's record by id;
- a signed-in account cannot delete another account's record (and the record
  survives);
- signup is rejected when the instance disables signups;
- the live collection rules read back equal the rule table.

Families whose fix has not landed yet (rejecting a create whose owner is not
the caller, and rejecting an ownership reassignment on update) are listed in
the policy as `pending` with the leaf and stage that closes them. They carry
no probe here by design: their probes land in the pull request that tightens
the rules, which is where the before/after is demonstrated. The run fails if a
pending family ever gains an implementation or produces a receipt, so the
policy row and its probe flip together.

## Running it

```sh
# Local (Finch):
harness/run.sh

# CI (Docker on ubuntu):
COMPOSE_BIN="docker compose" harness/run.sh
```

The launcher builds the pocketbase and probe images, brings PocketBase up,
runs the main probe phase, recreates PocketBase with signups disabled, runs
the signup-hook probe, prints the verdict (pass / expected-fail / fail
counts), and tears the stack down. Its exit code is non-zero on any failed or
missing result. Host ports bind to `127.0.0.1` and are for debugging only; the
probes reach services by their compose network names.

The account factory generates fresh credentials for every run and never uses
the demo account password.

## Receipts

Each probe appends one JSON line to `harness/.receipts/receipts.jsonl`
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
