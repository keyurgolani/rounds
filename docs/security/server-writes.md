# Server-Write Record

The contract for who may write server-only PocketBase collections. It comes from #1 (`ROUNDS-00A-L01`) and lands in its stage 0, before any containment collection exists. #18 (`ROUNDS-02-L01`) ratifies it or migrates it.

## The Rule

A server-only collection has `null` client create, update, and delete rules. At runtime only the three writer kinds below write it, and none of them uses the PocketBase superuser token.

| Kind | What it is | Registered by |
| --- | --- | --- |
| Caller | A hook route under `$apis.requireRecordAuth("users")`. It writes only the caller's rows, and touches a shared counter only inside its own transaction, never resetting it. | the leaf that adds the route |
| Service | A non-superuser auth collection for work no caller owns, matched in rules by `@request.auth.collectionName`. | its leaf, in the registry below |
| System hook | A PocketBase handler with no caller token: a boot hook (`onBeforeServe`), a `cronAdd` job, or an anonymous hook route. A Service leaf that creates or resets its record at boot registers that hook too. | its leaf, in the registry below |

1. No Service credential goes into the runner's environment before #1's stage 2 ships the minimal child environment. Until then, candidate code can read that environment.
2. A model hook (`onModel*`) that writes a server-only row rides on the write that fired it. Its leaf lists it in its registry row.
3. Migrations run inside PocketBase at start with no token. One that writes rows into a server-only collection gets a registry row too, as #10's and #14's do. #156 and #1's stage 5 lint cover migration safety.

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

#1's stage 3 adds `admission_commands`, `admission_counters`, and `admission_leases` in `pocketbase/pb_migrations/1700006100_admission.js`. Only the functions in `pb_hooks/admission.js` write them. #1 calls them from Caller hook routes under `/api/rounds/admission/`, which nginx answers with 404 from stage 2, and other leaves call the same functions from their own routes and hooks (#3, #4, #12, #177). One transaction writes the command row, the charge, and the lease, or nothing. SQLite serializes PocketBase writes, so both runner replicas share one count.

## Registry of Planned Writers

Each row restates the leaf's current body. The leaf confirms or corrects its row in the PR that adds the writer. Credentials appear by environment variable name only.

| Leaf | Kind | Principal, route, or hook | Writes | Credential |
| --- | --- | --- | --- | --- |
| #1 S3 | Caller | `pb_hooks/admission.js`, under `/api/rounds/admission/` | `admission_commands`, `admission_counters`, `admission_leases` | caller's bearer |
| #3 | Caller | `enqueue` and owner `cancel` in `pb_hooks/execution.pb.js`, under `/api/rounds/execution/` | `execution_jobs`, and the `job_id` on #1's admission row | caller's bearer |
| #3 | Service | `execution_service`, one record (`execution-worker`): `claim`, `heartbeat`, `complete`, `reap` | `execution_jobs`, `execution_attempts`, `execution_envelopes` | `ROUNDS_EXECUTION_SECRET` |
| #3 | System hook | `onBeforeServe` in `pb_hooks/execution.pb.js`, which creates `execution-worker` or resets its password | `execution_service` | `ROUNDS_EXECUTION_SECRET` |
| #4 | Caller | `POST /api/rounds/legacy-snapshots`, which the runner calls with the caller's bearer | `legacy_artifact_snapshots`, and it completes the `admission_commands` row | caller's bearer |
| #6 | Service | `execution_service` `claim` and `complete` for render jobs | the render output record and its PDF | `ROUNDS_EXECUTION_SECRET` |
| #10 | Migration, then operator | the quarantine migration at start; replay through the admin API | `relation_quarantine`, `relation_quarantine_reports` | none for the migration; superuser for replay |
| #11 S2 | Caller | the owner's `POST /api/rounds/share/capabilities/:id/revoke`, plus an `onModelAfterDelete` hook on `resumes` and `resume_variants` that revokes on delete | `share_capabilities` | caller's bearer |
| #12 | Caller | `POST /api/rounds/share/capabilities` and `POST /api/rounds/share/capabilities/:id/rotate`, each through `pb_hooks/admission.js` | `share_capabilities`, the `share_secret_state` latch, admission rows | caller's bearer |
| #12 | Service | `share_resolvers`, one record: `POST /api/rounds/share/lookup` | `share_throttle` | `ROUNDS_SHARE_RESOLVER_PASSWORD` |
| #14 | Migration | M1 | `legacy_share_migration` | none |
| #22 | Service | `dispatcher_service`: routes under `/api/outbox/` | `outbox_cursors`, `outbox_watermarks`, `outbox_parked`, and the relay lease in `platform_leases` | `ROUNDS_DISPATCHER_SECRET` |
| #54 | Caller and Service | `pb_hooks/processing.pb.js`: `enqueue`, `cancel`, and `retry` with the caller's bearer; `checkpoint`, `block`, and `complete` as `execution_service` | `processing_*` | caller's bearer; `ROUNDS_EXECUTION_SECRET` |
| #56 | Service | #54's `complete`, as `execution_service` | `processing_extraction_outputs` | `ROUNDS_EXECUTION_SECRET` |
| #73 | Service | `ai_gateway`, one record, scoped to the bearer's account | `ai_providers`, `ai_credentials`, `ai_provider_models`, Intent records | `ROUNDS_AI_GATEWAY_SECRET` |
| #73 | System hook | `onBeforeServe`, which seeds the `ai_gateway` record | `ai_gateway` | `ROUNDS_AI_GATEWAY_SECRET` |
| #76 | Model hook | `onModelBeforeDelete` on each classed collection; retention purges run as #22's `dispatcher_service` | `deletion_journal` | rides on the delete |
| #80 | set by #80 | the backfill and deltas, per account through #19 | `legacy_material_blocks` | never the superuser |
| #91 | Service | the export pool as `execution_service`, through `pb_hooks/account_export.pb.js` | `account_exports` | `ROUNDS_EXECUTION_SECRET` |
| #93 | Service | `share_resolvers`: `POST /api/rounds/share/view` | `share_view_counters` | `ROUNDS_SHARE_RESOLVER_PASSWORD` |
| #130, #133, #134, #135 | Service | `execution_service`, inside #3's `complete`, calling #130's `AttachFeedback` | Feedback on Attempts | `ROUNDS_EXECUTION_SECRET` |
| #161 | set by #161 | written once at the seal, per account through #19 | `legacy_share_history` | never the superuser |
| #177 | System hook | `demo.pb.js`: `onBeforeServe`, the `cronAdd` sweep, and the anonymous `POST /api/rounds/demo/sessions` | demo `users`, `account_system_state`, and the deployment `demo-session-create` bucket in `admission_counters` through `pb_hooks/admission.js` | none |
| #177 | Caller | `POST /api/rounds/demo/sessions/end` | deletes the demo caller's account and files | caller's bearer |

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
