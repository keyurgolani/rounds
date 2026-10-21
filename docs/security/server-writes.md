# Server-Write Record

The contract for who may write server-only PocketBase collections. It comes from #1 (`ROUNDS-00A-L01`) and lands in its stage 0, before any containment collection exists. #18 (`ROUNDS-02-L01`) ratifies it or migrates it.

## The Rule

A server-only collection has `null` client create, update, and delete rules. At runtime only the three writer kinds below write it, and none of them uses the PocketBase superuser token.

| Kind | What it is | Registered by |
| --- | --- | --- |
| Caller | A hook route under `$apis.requireRecordAuth("users")`. It writes only the caller's rows, and touches a shared counter only inside its own transaction, never resetting it. | the leaf that adds the route |
| Service | A non-superuser auth collection for work no caller owns, matched in rules by `@request.auth.collectionName`. | its leaf, in the registry below |
| System hook | A PocketBase handler with no caller token: a boot hook (`onAfterBootstrap`, since PocketBase 0.22's JS hooks have no `onBeforeServe`), a `cronAdd` job, or an anonymous hook route. A Service leaf that creates or resets its record at boot registers that hook too. | its leaf, in the registry below |

1. No Service credential goes into the runner's environment before #1's stage 2 ships the minimal child environment. Until then, candidate code can read that environment.
2. A model hook (`onModel*`), or a library called inside another writer's transaction, rides on that write when it writes a server-only row. Its leaf lists it in its registry row.
3. Migrations run inside PocketBase at start with no token. One that writes rows into a server-only collection gets a registry row too, as #10's, #14's, #73's, and #177's do. #156 and #1's stage 5 lint cover migration safety.

## Superuser Token

No writer kind uses the superuser token. Two operator-run steps use superuser credentials, outside the app:

1. #73's `migrate-legacy`, which rewraps legacy provider keys. The operator enters the credentials for that run only. #1's body names this as the only superuser row.
2. #10's quarantine replay, which goes through the admin API so #10's relation hook re-checks each entry. It's a second operator-run row, recorded here so the list is complete.

At `62d4eae` the runner itself uses the superuser token. All of it retires:

| Use at `62d4eae` | Code | Retired by |
| --- | --- | --- |
| Mints and caches the token from `PB_ADMIN_EMAIL` and `PB_ADMIN_PASSWORD`, or development defaults when those are absent | [`backend/app/pb_auth.py:121-162`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/app/pb_auth.py#L121-L162) | #14 S3 |
| Finds a share link by token and reads its resume, or its variant and the parent resume | [`backend/routers/share.py:155-196`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/share.py#L155-L196) | #11 S1 hardens it, #14 S1 removes the route |
| Writes a `resume_share_views` row on every public view | [`backend/routers/share.py:198-216`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/share.py#L198-L216) | #11 S1 |
| Counts each link's views for the owner's list | [`backend/routers/share.py:240-258`](https://github.com/keyurgolani/rounds/blob/62d4eaeaecf601da836afa1981adc0b1ae2db16a/backend/routers/share.py#L240-L258) | #11 S1 |

The harness superuser in #13 and #172 seeds and reads fixtures inside the test stack only. It isn't a deployment writer.

## Admission State

#1's stage 3 adds `admission_commands`, `admission_counters`, and `admission_leases` in `pocketbase/pb_migrations/1700006100_admission.js`, with every client rule `null`. Only the functions in `pocketbase/pb_hooks/admission.js` write them:

1. `admit`, `settle`, and `finish`, which #1 calls from Caller hook routes under `/api/rounds/admission/` in `pb_hooks/admission.pb.js`. nginx answers that prefix with 404 from stage 2, so the runner reaches them with the caller's bearer and `ROUNDS_ADMISSION_SECRET`, and a browser never does. Other leaves call the same functions from their own routes and hooks (#3, #4, #12, #177).
2. `sweep`, which the `rounds_admission_sweep` cron job runs every 5 minutes with no caller token.

Each call is one transaction: `admit` writes the command row, the charge, and the lease, or nothing. PocketBase runs every write transaction on its one SQLite write connection, so both runner replicas share one count.

A Caller route writes only the caller's rows. The account and its tier come from the bearer's auth record, never the body. The write routes also need `ROUNDS_ADMISSION_SECRET`, which PocketBase and the runner share and no candidate process gets (#1 S2's minimal environment and per-slot uid), so a bearer alone admits, settles, and finishes nothing. The runner makes each lease's token and sends only its SHA-256, so `settle` and `finish` act only on a lease that runner holds. A lease settles once, never above what it was admitted for, and nothing moves its window later. The `usage` route reads the caller's own counters for the dependency check with the bearer alone and writes nothing.

`pb_hooks/admission.pb.js` also refuses any client create or update that sets or changes `users.is_demo`, `demo_run_used`, or `demo_evaluate_used`, including an OAuth2 sign-up's `createData`. Superusers, migrations, and server hooks can still set them.

## Legacy Artifact Snapshots

#4's PR 1 adds `legacy_artifact_snapshots` in `pocketbase/pb_migrations/1700008000_legacy_artifact_snapshots.js`. Its owner can list and view a row; create, update, and delete are `null`. Nothing writes it yet. Its one writer is the Caller route in #4's row below, which PR 2 adds behind `legacy_snapshot_create` (default off). That route reads a resume or variant only after checking the caller owns it, and stores the markup the `materializer` service returns for it. The materializer itself writes nothing, holds no credential, and answers only PocketBase. The migration writes no row, and its down step drops the collection only while it's empty.

## Demo Account

#177's stage 1 contains the demo account that `1700000600_demo_user.js` creates on every install. `pb_hooks/demo.pb.js` reads `ROUNDS_GATE_DEMO`, or its alias `ROUNDS_ENABLE_DEMO`, in each handler; the demo is off by default. With it off, the System hook `onAfterBootstrap` gives each demo account a random password and a new token key at every start, so an old password or token stops working, and a demo sign-in gets the wrong-password 400. On or off, a demo caller changes only its `name`, `bio`, `target`, and `avatar`, can't delete its account or change its email, and no demo account owns a `resume_share_links`, `share_capabilities`, `ai_providers`, `ai_credentials`, `ai_provider_models`, or `ai_settings` row. Model hooks on those six refuse the save whoever writes it, so they write nothing themselves. Whether an account is a demo account comes only from #1's tier accessor, `tierOf()` in `pb_hooks/admission.js`, which reads `is_demo` until stage 2 repoints it at `account_system_state`.

`1700006700_demo_contain.js` deletes the demo accounts' share links, their `resume_share_views` with them, and their `ai_settings` and `ai_providers`, forward-only. Manifest `demo-contain-v1` gives each delete its disposition.

## Registry of Planned Writers

Each row restates the leaf's current body. The leaf confirms or corrects its row in the PR that adds the writer. Credentials appear by environment variable name only.

| Leaf | Kind | Principal, route, or hook | Writes | Credential |
| --- | --- | --- | --- | --- |
| #1 S3 | Caller | `admit`, `settle`, and `finish` in `pb_hooks/admission.js`, from the routes in `pb_hooks/admission.pb.js` under `/api/rounds/admission/` | `admission_commands`, `admission_counters`, `admission_leases` | caller's bearer and `ROUNDS_ADMISSION_SECRET` |
| #1 S3 | System hook | the `rounds_admission_sweep` `cronAdd` job in `pb_hooks/admission.pb.js`, which runs `sweep` in `pb_hooks/admission.js` | deletes expired `admission_*` rows; marks `in_flight` commands without a live lease `failed_infrastructure` | none |
| #2 | Migration | `1700006200_definitions_expand.js` at start | `definition_migration_journal`, and `definition_version` (and `definition_case_ids` on coding) on `coding_questions`, `ai_coding_rounds`, `take_home_assignments` | none |
| #3 | Caller | `enqueue` and owner `cancel` in `pb_hooks/execution.pb.js`, under `/api/rounds/execution/` | `execution_jobs`, and the `job_id` on #1's admission row | caller's bearer |
| #3 | Service | `execution_service`, one record (`execution-worker`): `claim`, `heartbeat`, `complete`, `reap` | `execution_jobs`, `execution_attempts`, `execution_envelopes`, and the graded rows in `ai_coding_attempts` and `take_home_attempts`, which `complete` writes with the envelope | `ROUNDS_EXECUTION_SECRET` |
| #3 | System hook | `onBeforeServe` in `pb_hooks/execution.pb.js`, which creates `execution-worker` or resets its password | `execution_service` | `ROUNDS_EXECUTION_SECRET` |
| #4 | Caller | `POST /api/rounds/legacy-snapshots` (PR 2, behind `legacy_snapshot_create`), which the runner calls with the caller's bearer; it gets the markup from the `materializer` service over the internal `materialize` network | `legacy_artifact_snapshots` and its `markup` file, and it completes the `admission_commands` row | caller's bearer |
| #6 | Service | `execution_service` `claim` and `complete` for render jobs | the render output record and its PDF | `ROUNDS_EXECUTION_SECRET` |
| #10 | Migration, then operator | `1700007000_relation_endpoint_authz.js` at start; then an operator's replay with `pocketbase/levers/replay_quarantine.template.js`, a one-off `migrate up` whose every write the relation triggers re-check, or the admin API to mark an entry `dropped` ([operations.md](../operations.md#relation-endpoint-authorization-and-quarantine)) | `relation_quarantine` and `relation_quarantine_reports`; it moves or clears the cross-owner rows in the 22 collections that hold a typed relation. A replay writes the replayed row or field and the entry's `status` | none for the migration or the lever; the admin token to mark an entry `dropped` |
| #11 S2 | Caller | the owner's `POST /api/rounds/share/capabilities/:id/revoke` | `share_capabilities` | caller's bearer |
| #11 S2 | Model hook | `onModelAfterDelete` on `resumes` and `resume_variants`, which revokes; `onModelBeforeDelete` on `users`, which deletes the account's capabilities in the same transaction | `share_capabilities` | rides on the delete |
| #12 | Caller | `POST /api/rounds/share/capabilities` and `POST /api/rounds/share/capabilities/:id/rotate`, each through `pb_hooks/admission.js` | `share_capabilities`, the `share_secret_state` latch, admission rows | caller's bearer |
| #12 | Service | `share_resolvers`, one record: `POST /api/rounds/share/lookup` | `share_throttle` | `ROUNDS_SHARE_RESOLVER_PASSWORD` |
| #14 | Migration | M1 | `legacy_share_migration` | none |
| #22 | Library | `pb_hooks/lib/outbox.js`, which #21's transaction writer calls before commit | `domain_outbox` | rides on #21's write |
| #22 | Service | `dispatcher_service`: routes under `/api/outbox/` | `outbox_cursors`, `outbox_watermarks`, `outbox_parked`, and the relay lease in `platform_leases` | `ROUNDS_DISPATCHER_SECRET` |
| #54 | Caller and Service | `pb_hooks/processing.pb.js`: `enqueue`, `cancel`, and `retry` with the caller's bearer; `checkpoint`, `block`, and `complete` as `execution_service` | `processing_*` | caller's bearer; `ROUNDS_EXECUTION_SECRET` |
| #56 | Service | #54's `complete`, as `execution_service` | `processing_extraction_outputs` | `ROUNDS_EXECUTION_SECRET` |
| #73 | Service | `ai_gateway`, one record, scoped to the bearer's account | `ai_providers`, `ai_credentials`, `ai_provider_models`, Intent records | `ROUNDS_AI_GATEWAY_SECRET` |
| #73 | System hook | `onBeforeServe`, which seeds the `ai_gateway` record | `ai_gateway` | `ROUNDS_AI_GATEWAY_SECRET` |
| #73 | Migration | step 3, which moves the legacy ciphertext and model caches out of `ai_providers` | `ai_credentials_legacy`, `ai_provider_models` | none |
| #76 | Model hook | `onModelBeforeDelete` on each classed collection; retention purges run as #22's `dispatcher_service` | `deletion_journal` | rides on the delete |
| #80 | set by #80 | the backfill and deltas, per account through #19 | `legacy_material_blocks` | never the superuser |
| #91 | Service | the export pool as `execution_service`, through `pb_hooks/account_export.pb.js` | `account_exports` | `ROUNDS_EXECUTION_SECRET` |
| #93 | Service | `share_resolvers`: `POST /api/rounds/share/view` | `share_view_counters` | `ROUNDS_SHARE_RESOLVER_PASSWORD` |
| #130, #133, #134, #135 | Service | `execution_service`, inside #3's `complete`, calling #130's `AttachFeedback` | Feedback on Attempts | `ROUNDS_EXECUTION_SECRET` |
| #161 | set by #161 | written once at the seal, per account through #19 | `legacy_share_history` | never the superuser |
| #177 S1 | Migration | `1700006700_demo_contain.js` at start, under manifest `demo-contain-v1` | deletes the demo accounts' `resume_share_links` with their `resume_share_views`, and their `ai_settings` and `ai_providers` | none |
| #177 S1 | System hook | `onAfterBootstrap` in `pb_hooks/demo.pb.js`: with the demo off, a random password and a new token key for each demo account at every start | demo `users` | none |
| #177 S2 | Migration | stage 2's state migration, one `demo` row per demo account | `account_system_state` | none |
| #177 S3 | System hook | `demo.pb.js`: the boot sweep, the `cronAdd` sweep, and the anonymous `POST /api/rounds/demo/sessions` | demo `users`, `account_system_state`, and the deployment `demo-session-create` bucket in `admission_counters` through `pb_hooks/admission.js` | none |
| #177 S3 | Caller | `POST /api/rounds/demo/sessions/end` | deletes the demo caller's account and files | caller's bearer |

#19's command gateway becomes a Caller hook route if #18 keeps PocketBase, and registers here then.

## Leaves Cited

| Issue | Leaf | Title |
| --- | --- | --- |
| [#1](https://github.com/keyurgolani/rounds/issues/1) | `ROUNDS-00A-L01` | Authenticate, authorize, and quota every execution and render route |
| [#3](https://github.com/keyurgolani/rounds/issues/3) | `ROUNDS-00A-L03` | Introduce the execution-control protocol and durable result envelope |
| [#4](https://github.com/keyurgolani/rounds/issues/4) | `ROUNDS-00A-L04` | Create the Legacy Artifact Snapshot bridge and safe render disable |
| [#6](https://github.com/keyurgolani/rounds/issues/6) | `ROUNDS-00A-L06` | Isolate document rendering in ephemeral no-script workers |
| [#10](https://github.com/keyurgolani/rounds/issues/10) | `ROUNDS-00B-L02` | Authorize every typed relation and merge |
| [#11](https://github.com/keyurgolani/rounds/issues/11) | `ROUNDS-00B-L03` | Create immutable artifact share capabilities |
| [#12](https://github.com/keyurgolani/rounds/issues/12) | `ROUNDS-00B-L04` | Implement one-time share secret delivery, password protection, and rotation |
| [#13](https://github.com/keyurgolani/rounds/issues/13) | `ROUNDS-00B-L05` | Add the complete two-account IDOR and disclosure suite |
| [#14](https://github.com/keyurgolani/rounds/issues/14) | `ROUNDS-00B-L06` | Migrate legacy shares and prove immediate revocation |
| [#18](https://github.com/keyurgolani/rounds/issues/18) | `ROUNDS-02-L01` | Ratify the canonical database and transaction-owner ADR |
| [#19](https://github.com/keyurgolani/rounds/issues/19) | `ROUNDS-02-L02` | Build the account-authorized domain command gateway |
| [#21](https://github.com/keyurgolani/rounds/issues/21) | `ROUNDS-02-L04` | Persist transactional change sets, revisions, and audit entries |
| [#22](https://github.com/keyurgolani/rounds/issues/22) | `ROUNDS-02-L05` | Publish domain events through a transactional outbox |
| [#54](https://github.com/keyurgolani/rounds/issues/54) | `ROUNDS-10-L02` | Define durable Processing Jobs and adapter versioning |
| [#56](https://github.com/keyurgolani/rounds/issues/56) | `ROUNDS-10-L04` | Build the extraction adapter registry and reprocessing flow |
| [#73](https://github.com/keyurgolani/rounds/issues/73) | `ROUNDS-14-L02` | Define Provider Invocation Intent and authorization |
| [#76](https://github.com/keyurgolani/rounds/issues/76) | `ROUNDS-14-L05` | Enforce deletion, purge, backup expiry, and restore suppression |
| [#80](https://github.com/keyurgolani/rounds/issues/80) | `ROUNDS-15-L04` | Migrate legacy materials into editions and revisions |
| [#91](https://github.com/keyurgolani/rounds/issues/91) | `ROUNDS-18-L03` | Create complete versioned account export |
| [#93](https://github.com/keyurgolani/rounds/issues/93) | `ROUNDS-18-L05` | Build revocable public artifact sharing |
| [#130](https://github.com/keyurgolani/rounds/issues/130) | `ROUNDS-28-L01` | Define shared Practice Item, Attempt, Progress, and Feedback contracts |
| [#133](https://github.com/keyurgolani/rounds/issues/133) | `ROUNDS-28-L04` | Migrate Coding practice |
| [#134](https://github.com/keyurgolani/rounds/issues/134) | `ROUNDS-28-L05` | Migrate AI-assisted Coding practice |
| [#135](https://github.com/keyurgolani/rounds/issues/135) | `ROUNDS-28-L06` | Migrate Take-home practice |
| [#156](https://github.com/keyurgolani/rounds/issues/156) | `ROUNDS-32-L02` | Build the migration framework, manifests, and journals |
| [#161](https://github.com/keyurgolani/rounds/issues/161) | `ROUNDS-32-L07` | Migrate materials, renders, submissions, and shares |
| [#172](https://github.com/keyurgolani/rounds/issues/172) | `ROUNDS-34-L03` | Maintain the authorization and privacy verification matrix |
| [#177](https://github.com/keyurgolani/rounds/issues/177) | `ROUNDS-00B-L07` | Contain and own the hosted demo account lifecycle |

## Keeping This Current

A PR that adds a server-only collection, a writer, or a superuser use edits this file in the same PR. Add the row before the collection takes writes, and keep the registry in issue order.
