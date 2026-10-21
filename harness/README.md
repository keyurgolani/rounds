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
none remain. `ROUNDS-00B-L02` adds the enforced typed-relation endpoint
families: a write may point a relation only at a target the same account owns,
and a foreign target reads the same as a nonexistent one, so both are denied
alike.

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
schema, and that a relation pointed at another account's record in a fixture
copy (a direct SQLite write to the copy, never through the API) is reported.
The same direct cross-owner write is first confirmed to be aborted by the
`ROUNDS-00B-L02` relation-endpoint triggers (the transactional backstop), which
are then dropped on the throwaway copy only so the pre-migration row can be
planted for the scan to detect. It also checks that reports carry no account
ids, are private, have a stable checksum, and are refused inside `pb_data`.

## Running it

```sh
# Local (Finch):
harness/run.sh

# CI (Docker on ubuntu):
COMPOSE_BIN="docker compose" harness/run.sh

# A second, isolated run alongside the first:
COMPOSE_PROJECT=rounds-9s1-b harness/run.sh
```

The launcher builds the pocketbase, probe, runner, frontend, and materializer
images, brings PocketBase up, runs the main probe phase, runs the admission
check and the admission-deploy phase against two runner replicas, restarts the
runner with `/api/run` turned off and then on again, runs the demo checks with
the demo on, recreates PocketBase with signups disabled and the demo at its
default (the named `pb_data` volume keeps the run's accounts and rows), runs
the signup-hook probe and the demo-off checks, brings the runner and nginx
frontend up and
runs the deployment verifier through them, checks that only PocketBase reaches
the snapshot materializer and that it has no route out, stops PocketBase for
the degraded probe, runs the verifier's checks and the cross-owner scan on the
run's `pb_data`, prints the verdict (pass / expected-fail / fail counts), runs
the admission migration, demo containment migration, relation quarantine, and
snapshot store checks, and
tears the stack down, removing the images and the volume it made.
Its exit code is non-zero on any failed or missing result.

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

## Admission and gates as deployed

`ROUNDS-00A-L01` stage 4 builds on the admission phase rather than repeating
it. With both replicas still up, the `admission-deploy` phase
([`probes/admission_deploy.py`](probes/admission_deploy.py)) checks on each
replica that:

- every admitted route refuses an anonymous caller in the typed
  `{"detail", "code", "correlation_id"}` envelope, and a body declared over
  the runner's own cap gets the typed 413 before any account is asked for;
- a field a route doesn't take is refused 422 before the idempotency key is
  asked for, and a missing key is refused 400 before anything is looked up;
- that 422 is the typed envelope and repeats none of what was sent;
- the replica admits through the admission store in `admission/v1`, and of
  the account's requests so far only the one it admitted counts;
- stage 2's closures hold in the built image: a candidate process sees only
  the minimal environment and runs as a candidate uid that can't write
  `/app`, from its own 0700 scratch; a running execution doesn't hold up the
  replica's `/health`; the renderer health check answers only its status; and
  a render the renderer can't finish is the typed 503 without its text.

Next the launcher restarts both replicas and nginx with
`ROUNDS_GATE_RUN=disabled` (`emergency-disable`), while signups are still on
so the phase can make its account: `/api/run` answers 503 `route_disabled`
through nginx and at each replica, for no bearer, an unknown bearer, and a
signed-in account, and charges nothing, while the other routes still refuse
an anonymous caller 401, `/api/evaluate` still admits, and each replica's
saved gates line shows `RUN` disabled. It clears the gate and restarts both
again (`emergency-enable`): every route refuses an anonymous caller 401
again, and runs are admitted through nginx and at each replica. Later the
deploy phase adds the verifier's `--admission` checks through the real nginx
and the runner's startup gates line. The verdict requires a passing receipt
for every check id in `verify_deployment.ADMISSION_CHECKS` and
`admission_deploy.CHECKS`.

After the scan,
[`probes/admission_migration_check.py`](probes/admission_migration_check.py)
copies the pinned PocketBase binary out of its image and, with no network,
applies `1700006100_admission.js` to a `pb_data` built from every migration
before `1700006000` (the `62d4eae` set), checks that it adds only the three
server-only collections, reverses it with `pocketbase migrate down 1` as an
operator would, checks that the data is back as it was, and applies it again.

Last, [`probes/relation_quarantine_check.py`](probes/relation_quarantine_check.py)
runs the same pinned binary, with no network, against the relation
quarantine in `1700007000_relation_endpoint_authz.js`. It builds a `pb_data`
from every earlier migration, plants a legacy fixture of cross-owner and
missing-target rows with direct SQL, and checks that:

- the dry run changes nothing, exits 0 as PocketBase 0.22 does even after a
  failed migration, and reports the outcomes and checksum the apply then has;
- the apply moves each row whose required or cascading relation crosses
  accounts with its cascade dependents (two offers chained through
  `previous_offer` included), clears a row's offending optional fields in one
  update, clears a reference to a moved row, and moves a row whose clear
  would collide with a unique index, journalling every move and clear with
  the original row, pseudonyms, and status;
- same-owner rows and total row counts stay as they were, each journal
  entry's payload is the row's every raw column value exactly, the logs carry
  counts and the checksum but no ids, and a second run adds nothing;
- on copies of the applied data, the admin API marks entries `dropped` and
  `replayed` without touching their payload, and the replay lever
  (`pocketbase/levers/replay_quarantine.template.js`) writes same-owner
  entries back exactly, `created` and `updated` included, and refuses one
  whose target still belongs to another account;
- a view, an added relation, and a toggled cascade with nothing to quarantine
  change nothing; a toggled cascade on a field with something to quarantine,
  or an added relation pointing at a row about to move, stops the migration;
  and a failure as early as creating the triggers still writes the dry run's
  report and the apply's failure log line.

It then serves a fresh copy on loopback with the hooks and checks, through
the API, that deleting a provider set as both text and vision provider,
deleting an application with two chained offers, and a superuser deleting an
account holding both shapes all succeed without touching another account.

No service publishes a host port; the probes reach services over the compose
network. Image tags, network, volume, the compose env file, and the receipts
directory all derive from the compose project name, so runs with different
`COMPOSE_PROJECT` values do not collide.

The account factory generates fresh credentials for every run and never uses
the demo account password. Only the demo phases sign in with it, to check it
works with the demo on and fails with it off.

## Demo account

`ROUNDS-00B-L07` stage 1 keeps the demo account off unless PocketBase runs with
`ROUNDS_ENABLE_DEMO=true`. PocketBase runs with it on from phase 1, as a hosted
demo does, and [`probes/demo_check.py`](probes/demo_check.py) checks with the
runner up (`demo-on`) that:

- the seeded demo account signs in, and so does a demo account a superuser
  makes;
- a demo caller changes its profile but not its password, email, username, or
  verification, and can't delete itself or ask for an email change;
- a demo caller can't create a share link, an AI provider, or AI settings,
  through PocketBase or the runner, while a standard account still can.

The signup restart turns the demo off, and `demo-off` checks that both demo
accounts' sign-ins get the answer a wrong password gets, that a token from
before the restart is refused, and that a standard account still signs in.

After the admission migration check,
[`probes/demo_contain_migration_check.py`](probes/demo_contain_migration_check.py)
applies `1700006700_demo_contain.js` with the pinned binary to a `pb_data` whose
legacy fixture has rows in every account-scoped collection for the seeded demo
account, a second demo account, and a standard account. It checks that the
migration deletes only the demo accounts' share links, the views on them, their
AI providers, and their AI settings, that every other row is as it was, column
by column, and that `migrate down 1` changes no row and applying it again
deletes nothing more.

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
