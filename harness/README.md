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
the demo on, checks the execution job store on PocketBase and both replicas
through a secret rotation with both execution keys off, then each key on in
turn, recreates PocketBase with signups disabled, the demo at its default, and
no worker secret (the named `pb_data` volume keeps the run's accounts and
rows), runs the signup-hook probe and the demo-off checks, recreates
PocketBase with the worker secret, brings the runner and nginx frontend up and
runs the deployment verifier through them, checks that only PocketBase reaches the snapshot materializer
and that it has no route out, stops PocketBase for the degraded probe, runs
the verifier's checks and the cross-owner scan on the run's `pb_data`, prints
the verdict (pass / expected-fail / fail counts), runs the admission
migration, execution migration, JSON limits, demo containment migration,
relation quarantine, snapshot store, older share links' migration, and attempt
grade rules checks, and tears the stack down, removing the images and the volumes it made.
Its exit code is non-zero on any failed or missing result.

## Admission state across two replicas

`ROUNDS-00A-L01` stage 3 keeps idempotency and quota state in PocketBase, so
every runner replica sees one count. The admission phase starts `runner` and
`runner-b`, two replicas of the runner image built from this commit, on the
one PocketBase, with `ROUNDS_GATE_ENFORCE_IDEMPOTENCY` and
`ROUNDS_GATE_ENFORCE_QUOTA` at `enforce` and a test `ROUNDS_ADMISSION_SECRET`
shared by PocketBase, both runners, and the probe. Since `ROUNDS-00A-L03` PR 4
it runs, as the later phases do unless they say otherwise, with definitions
enforced, both execution keys on, the job store on, and the worker secret, so
each code run is a job; it waits until both replicas answer ready.
[`probes/admission_check.py`](probes/admission_check.py) checks that:

- a run's duplicate on the other replica answers the same job, and a reused
  or missing `Idempotency-Key` is refused;
- runs on both replicas land in one hourly count, an evaluate settles on the
  cases it runs, each account's tier comes from its record, and every job the
  phase makes ends before it does;
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
  `/app`, from its own 0700 scratch, each read from a run's job; a running
  job doesn't hold up either replica's `/health`; the renderer health check
  answers only its status; and
  a render the renderer can't finish is the typed 503 without its text.

Next the launcher restarts both replicas and nginx with
`ROUNDS_GATE_RUN=disabled` (`emergency-disable`), while signups are still on
so the phase can make its account: `/api/run` answers 503 `route_disabled`
through nginx and at each replica, for no bearer, an unknown bearer, and a
signed-in account, and charges nothing, while the other routes still refuse
an anonymous caller 401, `/api/evaluate` still answers with a job that ends,
and each replica's saved gates line shows `RUN` disabled. It clears the gate
and restarts both again (`emergency-enable`): every route refuses an
anonymous caller 401 again, and runs are jobs again through nginx and at each
replica, each of which ends. A saved gates line keeps the execution keys'
start lines after it, so a key that acts as off fails the gates check with
what it needs. Later the
deploy phase adds the verifier's `--admission` checks through the real nginx
and the runner's startup gates line. The verdict requires a passing receipt
for every check id in `verify_deployment.ADMISSION_CHECKS` and
`admission_deploy.CHECKS`.

## Execution job store

`ROUNDS-00A-L03` PR 1 keeps execution jobs in PocketBase. After the gate
cycle, the launcher restarts PocketBase with `ROUNDS_GATE_EXECUTION_STORE=on`
and a test `ROUNDS_EXECUTION_SECRET`, and
[`probes/execution_check.py`](probes/execution_check.py) checks on the real
store that:

- only the secret logs in as `execution-worker`; a `users` token and an
  anonymous caller are refused on the service routes; and no client reads or
  writes the job collections or links an attempt row to an envelope;
- enqueue needs the account's admitted command and the runner key, answers a
  duplicate with its job and a different request as a mismatch, and records
  the job on the command, and another account's cancel gets the unknown-id
  404;
- two sessions racing for one job make one attempt, a superseded token's
  write is counted and never applied, and an envelope outside v1 is refused
  whole;
- after a real 31 s wait, reap puts a lease lost before its run started back
  in the queue and ends one lost after it started `worker-lost`, and a
  same-key retry runs attempt two;
- an account's filters on its envelopes name no field of a job or an
  attempt, and one account's backlog of queued jobs holds no other account's
  job back.

The store and the secret are on from phase 1 since PR 4, and from this
phase to `execution-scratch` both execution keys are off. Then both replicas
start (`execution-runners`): each is ready, and each claims jobs and ends
every one once, `canceled` before it starts, since neither key is on.
PocketBase restarts with another secret and neither replica stays ready
(`execution-unready`); the replicas restart with it, both are ready again,
and only the new secret logs in (`execution-ready-again`).

PR 2's scratch jobs (`execution-scratch`, [`probes/scratch_check.py`](probes/scratch_check.py))
restart both replicas and nginx with `ROUNDS_GATE_EXECUTION_SCRATCH=on`, the
grading key off, and `ROUNDS_GATE_EXECUTION_DEFINITIONS=enforce`, and check
through nginx that each
replica's gates line holds the three values; a run answers 202 with its job,
which ends with its envelope; a duplicate answers the same job and charges
nothing more, and the same key for other work is a mismatch; another
account's read and cancel of a job get the unknown id's 404 and leave it as
it was, which the case table's two `runner:execution-jobs` rows take as
evidence; a cancel stops a running test run; and a run that reaches its time
limit names it, keeps its charge, and shows no output. Then a long project
run starts on `runner` alone (`execution-scratch-start`), the launcher kills
that replica and starts both again, and once both answer ready (a replica
that refuses the connection while it starts reads as not ready yet, until
a deadline) the job ends `worker-lost` once its lease runs out, and a
same-key retry through nginx runs it to the end
(`execution-scratch-retry`). The signup restart runs PocketBase with no worker
secret, and the last one no longer logs in (`execution-disabled`); PocketBase
gets it back before the runner and nginx start for the deploy phase. The deploy
phase's verifier checks that nginx answers `/api/rounds/execution/` and the
worker's login and records with 404, those in other cases too.

After the scan,
[`probes/admission_migration_check.py`](probes/admission_migration_check.py)
copies the pinned PocketBase binary out of its image and, with no network,
applies `1700006100_admission.js` to a `pb_data` built from every migration
before `1700006000` (the `62d4eae` set), checks that it adds only the three
server-only collections, reverses it with `pocketbase migrate down 1` as an
operator would, checks that the data is back as it was, and applies it again.
[`probes/execution_migration_check.py`](probes/execution_migration_check.py)
does the same for `1700007100_execution_jobs.js` on a `pb_data` built from
every migration before it: the four collections with no client writes, the
`envelope` and `job` links, and the 8 MiB `files` limit, and nothing else,
with envelopes that link into no service-only collection and a down step
that keeps a store holding a job and, on an empty one, puts back the
`files` limit it found, also on a `pb_data` where PocketBase's reset ran
first and `files` held 2 MiB.
[`probes/grade_rules_migration_check.py`](probes/grade_rules_migration_check.py)
is the dry run of `1700008700_attempt_grade_rules.js` (`ROUNDS-00A-L03` PR 4)
on a `pb_data` built from every other migration, with in-progress rows and
both kinds of graded row planted for two accounts. It takes each attempt
collection's census from the manifest
(`pocketbase/migration-manifests/attempt-grade-rules-v1.json`) before and after
the migration and prints them as one reconciliation line, counts and
checksums only, which must match; the rules must be the policy's and the
`_params` record the rules they replaced, with nothing else changed. On a
second copy, where the lock lever froze `take_home_attempts` before the
upgrade, that collection keeps its lock, the other takes the new rules, and
the record holds what was found. On the first copy, served with no hooks so only the rules decide, every client write to a
graded row, or one that would grade a row or give it an envelope, is refused,
and in-progress rows still save. `migrate down 1` keeps the rules and the
record, and applying it again changes neither. Last, a copy without the
migration, whose rules still take an owner's graded write (they must hash to
the manifest's record of the rules it replaces), is served with the
execution hooks alone: their record checks refuse every client write that
would grade a row, change a graded row, or set an envelope, in each request
form, and open rows still save.
[`probes/json_limits_check.py`](probes/json_limits_check.py) holds every JSON
field's maxSize to the limit its migrations declare (D10). PocketBase's own
`1702134272_set_default_json_max_size` resets them all to 2,000,000 bytes and
sorts after the repository's migrations, and `1702134273_json_limits.js` sets
them back. The check takes the declared limits from a `pb_data` where
PocketBase's migrations ran first, then checks that a fresh `pb_data` and one
upgraded from every migration before `1700007100_execution_jobs.js` hold them,
that the registry changes nothing else but its record and saves and
records nothing where they already hold, and that `pocketbase migrate down 1`
puts back the size each field held before it, removes the record, and a
second `migrate up` restores them.

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
works with the demo on and fails with it off, and to try its code run.

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
  through PocketBase or the runner, while a standard account still can;
- the deployment verifier's demo check (`--demo`) passes through nginx: the
  seeded demo account's code run answers 503 `demo_execution_disabled`.

The runners run with `ROUNDS_GATE_DEMO_EXECUTION` at its default, off, in
every phase, as a release ships it.

The signup restart turns the demo off, and `demo-off` checks that both demo
accounts' sign-ins get the answer a wrong password gets, as does a demo
password a superuser sets after the restart, so the sign-in refusal holds on
its own. A token from before the restart is refused, and so is a live token the
boot lock never rotated, once a superuser makes its account a demo account: on
refresh and on any other request. The demo routes answer as unknown routes do,
and a standard account still signs in.

After the admission migration check,
[`probes/demo_contain_migration_check.py`](probes/demo_contain_migration_check.py)
applies `1700006700_demo_contain.js` with the pinned binary in upgrade order, to
a `pb_data` built from every migration before it whose legacy fixture has rows
in every account-scoped collection for the seeded demo account, a second demo
account, and a standard account, plus a demo provider the standard account's
AI settings point at. It checks that the migration deletes only the demo
accounts' share links, the views on them, their AI settings, and their AI
providers, keeps that one provider's row with its stored key cleared, that
every other row is as it was, column by column, and that `migrate down 1`
changes no row and applying it again changes nothing more. Then it serves a
fresh `pb_data` with every migration and the hooks, the demo at its default:
the first start logs `demo_lock` `not_ready`, the published password gets the
wrong-password answer, and the next start locks the demo account.

## Legacy Artifact Snapshots

`ROUNDS-00A-L04` PR 2 runs after the execution store phases, while signups are
still on. PocketBase, both runners, and nginx restart with
`ROUNDS_GATE_LEGACY_SNAPSHOT_CREATE=enabled` and the materializer up, and
[`probes/legacy_snapshot_check.py`](probes/legacy_snapshot_check.py) checks
through nginx (`snapshot-create`) that:

- each `tests/conformance/rd_02/` input, stored as an account's own resume, gets
  its declared outcome; an ineligible one writes nothing, and a created
  snapshot's markup hashes to its checksum and leaves out what the input
  declares;
- a replayed key returns the first answer, the same inputs under a new key are
  `reused`, and a variant with its parent's markup gets its own snapshot;
- a stale `expected_updated` is a conflict that writes nothing, another
  account's source answers exactly like a missing one, and nobody but the owner
  reads a snapshot or its file;
- a variant naming another account's resume, and the demo account, get no
  snapshot;
- every snapshot reconciles with its checksum, owner, and source rows.

run.sh then runs the operator's scan in the PocketBase container and signs and
verifies the report on the runner.

PR 3 adds server PDF on snapshot ids. The real PDF renderer, built from this
commit, runs behind the `renderer` profile only during these phases, so every
other phase's runner has no renderer to reach. Through nginx
(`snapshot-render`):

- the owner gets a PDF of each of its snapshots;
- another account's snapshot, named with its checksum, answers exactly like a
  missing one, and so does a snapshot whose source was deleted;
- a checksum the snapshot doesn't hold, the request shape from before
  snapshots, and an anonymous caller are refused;
- a completed render's key doesn't render again, and another account's key on
  its own request is its own command.

The isolation check writes the receipts for the case table's
`isolation.render.snapshot.uniform-not-found` row. run.sh then saves both
replicas' decision lines for the render route into the run's state, and
`snapshot-render-audit` checks that each refused render ended at its refusal
before a slot ran and that the replicas answered exactly as many renders as
the owner made. With the renderer stopped, a render is the typed 503 with the
renderer's fixed sentence and none of its text.

With the materializer stopped, creation answers 503 `materializer_unavailable`
and writes nothing, and a snapshot that exists still renders; back up, the
same key makes one snapshot. With the gate off, creation answers 503
`route_disabled`, and every snapshot still reads back and renders, owner only;
a rescan gives the same report, which `snapshot-scan` compares with the signed
one. With the gate on again, every snapshot's source gives `reused` with the
same checksum, no resume, variant, or version row changed through any of it,
and deleting an account deletes its snapshots.

Last, the Recovery check (`snapshot-recovery`): with PocketBase stopped, run.sh
archives `pb_data` as Backups in `docs/operations.md` does, `storage/`
included, empties the volume, and restores the archive. Every snapshot then
renders for its owner with the checksum it had, and another account gets the
404. The scan secret is a per-run test value. Between phases the probe keeps
only emails, ids, and correlation ids, under `harness/.state/`, along with the
decision lines and the backup archive, none of which go up with the receipts.

## Share Capabilities

`ROUNDS-00B-L03` stage 2 runs right after the snapshot phases, while signups
are still on. Both runners and nginx restart, and
[`probes/share_capability_check.py`](probes/share_capability_check.py)
(`share-capabilities`) checks that:

- an owner's list through nginx and the runner holds only their own
  capabilities, with only the owner fields; a revoke answers the same the
  second time, and another account's capability answers exactly like a
  missing one and doesn't change;
- deleting a resume or a variant that has been shared succeeds with an active
  capability, which ends revoked as `source_deleted`, and with only a revoked
  one, which stays as it was; a resume delete that reaches a shared variant
  revokes that variant's capability, and every snapshot stays;
- PocketBase refuses to delete a snapshot a capability names, and refuses the
  superuser's changes to a capability's snapshot, account, checksum, or
  expiry, or the reopening of a revoked one;
- deleting an account with active and revoked capabilities succeeds and leaves
  none of its capabilities or snapshots.

The superuser seeds the snapshots and capabilities, through the model hooks
and owner triggers every writer meets. The main phase's families cover the
collection's null rules, and the deploy phase checks that nginx answers the
hook routes itself and that the resolver gives the uniform not-found while its
gate is closed.

## Share Secrets

`ROUNDS-00B-L04` runs next, still with signups and the demo on. PocketBase and
both runners restart with snapshot creation and share capability resolution
on, the materializer up, and nginx, and
[`probes/share_secrets_check.py`](probes/share_secrets_check.py) checks, in
three phases:

- `share-secrets`: a new link's secret comes back once, and the same key
  answers `already-issued` without it, as it is and after the source changes;
  Rotate recovers a lost link, a repeated rotate key answers `already-issued`,
  and ten rotations at one version across both replicas make one new secret
  while the old one stops on both; a revoked or expired link can't be
  rotated, and a demo account's create is ineligible; a wrong, missing, or
  impossible password answers exactly as an unknown link does; password
  tries and resolves per client are limited, 1,000 random well-formed links
  from one client meet the limit, and a throttled client gets the same 429
  for a live link as for an unknown one; a client's own `X-Real-IP` doesn't
  reach the runner through nginx, and nginx's backstop answers a burst.
- `share-secrets-down`: with PocketBase stopped, a live link gets the unknown
  answer.
- `share-secrets-scan`: no issued secret (raw, URL-encoded, or base64) or
  password (raw, or its SHA-1, SHA-256, or MD5) is in any service's log or in
  pb_data, and no log line for a share resolve or the share page has the
  probe's address. The launcher puts the logs and a pb_data tarball in the
  state folder, never the receipts, and removes them after the scan.

The direct calls to a replica name test clients in `X-Real-IP`, which the
runners trust from the compose network as they do from nginx, so they keep the
probe's own count for the calls through nginx. Secrets and passwords stay in
the state folder; receipts carry check ids and counts only.

## Older share links

`ROUNDS-00B-L06` stage 1 turns off every share link made before it, for good,
and gives each owner "Get a new link". Two parts of the run check it.

Phase 3o runs after the share secrets phases, still before signups close.
[`probes/legacy_share_check.py`](probes/legacy_share_check.py) makes a pb_data
shaped like `62d4eae` offline, in a volume of its own, with older links for
two accounts, their views, and one link on another account's resume; then
PocketBase starts on it and runs every later migration before its first
request. Both runners reach PocketBase through the recorder
([`probes/recorder.py`](probes/recorder.py)), with nginx, snapshot creation,
and the materializer on, and the job store off, so the recorder sees no
worker's calls, and the probe checks, in three phases:

- `legacy-shares-fixture`: the pb_data, with the pinned binary and no network.
- `legacy-shares`: every older link's value, and as many random ones, gets
  one answer per path and caller (the older read path through nginx and at
  each replica, the resolver, the `/r/<value>` page, and PocketBase's own
  API, anonymously, as the owner, and as another account); the owner's list
  and Get a new link, its replay and second press,
  and the refusals; revoke, then resolve at once on both replicas; deleting
  the resume revokes its variant's new link; every way a capability fails to
  resolve has one shape; the quarantined link shows to nobody; and the
  recorder shows public share requests reaching PocketBase only as the share
  resolver's own login and identity.
- `legacy-shares-scan`: no fixture value is in any service's log or in that
  pb_data. The scan passes over the every-value check's own tagged requests.

PocketBase then goes back to the main volume. The recorder publishes no port,
and its log stays on its own volume, never the receipts.

Phase 15, after the verdict, is offline:
[`probes/legacy_share_migration_check.py`](probes/legacy_share_migration_check.py)
runs the migration with the pinned binary on a fixture with every outcome a
database can hold once #10 has run, and 10,000 more links: a dry run on a copy
with `pocketbase legacy-share-receipt`, forward, killed at its first batch and
run again, reversed with `migrate down 1` after a new link, and forward again,
with the same journal checksum each time. A native run outside a container
names the seeds folder in `PB_SEEDS_DIR`.

## Two-account isolation suite

`ROUNDS-00B-L05` grows this harness into the suite every later isolation
check lands in, rather than adding a second one. Rows that are one family on
one collection stay in `probe_families` and each collection's `probes`. Every
other row is in the policy's `cases` table: runner routes, realtime,
service logs, the share surfaces, and surfaces that have no server yet. A
row records its surface, actor, request variant, expected outcome, positive
control, owner leaf, status, and lane.

- `pass`: the guarantee holds on this revision. `evidence` names the checks
  that prove it: the row's own id, an existing family or deployment check
  it maps to instead of repeating it (`<collection>:<check id>` to count
  one collection's receipts only), or `phase:<name>` for a phase whose
  exit code is the evidence (the launcher fails the run when it fails).
- `pending`: the leaf that closes it is named, and no probe is committed
  until that leaf lands it with the fix and flips the row.
- `slot`: the surface has no server yet. Its owner leaf fills the row when
  it builds the surface.
- `quarantined`: a row that flipped without a code change. It names an
  owner, the targets it covers (`<target>:<check id>`, for checks of its
  own), and an expiry within 14 days. It still runs, and a failure on a
  covered target is reported as expected-fail. A failure anywhere else
  fails the run, and so does a pass on every covered target, until the row
  is flipped back.

`policy.load` refuses a table it can't decide on: no table, an unknown key,
a quarantine that covers a family, a deployment check, or a phase, a check
that is evidence for both a `pass` and a `quarantined` row, or a `pending`
or `slot` id that a check already uses. The verdict fails on any
unregistered failure, a `pending` or `slot` row with an implementation or a
receipt, a quarantined row that passes, a quarantine that starts in the
future or ends more than 14 days out, any row past its `expires` date, and a
run that collected no receipts. Nothing is retried. A flake is quarantined
with an owner and an expiry, never deleted.

To add a row: write it in `cases` with its positive control, and land its
probe in the same pull request (or name existing checks as `evidence`). A
row for a guarantee that isn't enforced yet is `pending` with its closing
leaf, and carries no probe.

The suite's helpers:

- [`probes/recorder.py`](probes/recorder.py) is a recording proxy the runner
  can be pointed at instead of PocketBase. For every call it logs the
  method, the path without its query, the auth class (`superuser`, `user`,
  `service`, `none`, `malformed`, read from the token's payload only), the
  status, the length, and keyed pseudonyms of the owners in the response.
  It never logs a header, token, query, or body. It binds 127.0.0.1 unless
  `RECORDER_HOST` says otherwise. In the harness it runs on the stack's
  private network and publishes no port. Its log stays outside the uploaded
  receipts folder (it refuses to start with a log path inside it), and the
  phase that runs it deletes the log when it ends.
- [`probes/compare.py`](probes/compare.py) decides whether two answers are
  indistinguishable: status, headers, the raw body, and length, and the upstream
  call sequence with the probed ids templated. Only the `Date` header,
  correlation ids, and quoted request ids are set aside. Differences are
  reported by name, never by value.
- [`probes/logscan.py`](probes/logscan.py) counts issued session tokens,
  harness passwords, and registered literals in text logs and in a SQLite
  log database opened read-only. It reports counts and sources only.

## Receipts

Each probe appends one JSON line to `harness/.receipts/<project>/receipts.jsonl`
(generated, git-ignored). A receipt records the run id, commit, verified
PocketBase binary digest and architecture, migration list, the policy and
migration-list checksums, probe id, collection, operation, actor, expected
and observed status, pass/fail, and request time. Receipts carry no record
contents and no secrets. The writer redacts every string, keys included,
and then the serialized line, before it writes anything: each account's
password and session token, the superuser's token, and the harness admin
password (registered in every phase) become case-local labels, and anything
shaped like a session token or an account factory password becomes a fixed
label, registered or not.

## PocketBase image

`pocketbase/Dockerfile` verifies the pinned release zip against its published
SHA-256 before unpacking, keyed on the build's target architecture, so a
tampered or truncated download fails the build. Production and CI build
`linux/amd64`; the arm64 digest only exists so this harness can build and run
the same pinned version natively on an arm64 developer machine.
