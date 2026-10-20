# Security Docs

Contracts and inventories for the Epic 0 containment work. Each file names the leaf that owns it, and a leaf that changes what a file describes edits it in the same PR.

| File | What it holds | Owner |
| --- | --- | --- |
| [`inventory.md`](inventory.md) | Every execution and render entry point at `62d4eae`, with its auth, inputs, what it starts, where its data goes, its threat category, and the leaf and stage that closes each gap | [#1](https://github.com/keyurgolani/rounds/issues/1) (`ROUNDS-00A-L01`), stage 0 |
| [`server-writes.md`](server-writes.md) | Who may write server-only PocketBase collections, the superuser rule, and the registry of planned writers | [#1](https://github.com/keyurgolani/rounds/issues/1), stage 0 |
| [`account-scope.v1.json`](account-scope.v1.json) | The account-scope policy and one row per user-owned collection, which the inventory reads for its PocketBase rows; stage 3 carries the enforced create and update rules that [`1700006000_account_scope_rules.js`](../../pocketbase/pb_migrations/1700006000_account_scope_rules.js) applies | [#9](https://github.com/keyurgolani/rounds/issues/9) (`ROUNDS-00B-L01`), stages 1 to 3 |
| [`cross-owner-scan.md`](cross-owner-scan.md) | The read-only cross-owner relation scan: what it guarantees, how an operator runs it on a `pb_data` copy, and its report format | [#9](https://github.com/keyurgolani/rounds/issues/9), stage 2 |
| [`../../harness/verify_deployment.py`](../../harness/verify_deployment.py) | The read-only deployment verifier: nginx's denials and open routes, default credentials, live rules against the table, and an admin in a `pb_data` copy; how to run it is in [`docs/operations.md`](../operations.md#deployment-verification) | [#9](https://github.com/keyurgolani/rounds/issues/9), stage 4 |
| [`../../pocketbase/levers/`](../../pocketbase/levers/) | Emergency lever templates: freeze one collection's writes (superuser only) and the forward fix that restores its rules; the "Account-scope rules" runbook in [`docs/operations.md`](../operations.md) says when to use them | [#9](https://github.com/keyurgolani/rounds/issues/9), stage 3 |
| [`execution-runbook.md`](execution-runbook.md) | Flipping and confirming each gate, each error code, the request limits, idempotency and quotas, alerts, dependency checks, and repair | [#1](https://github.com/keyurgolani/rounds/issues/1), stages 2 and 3 |
