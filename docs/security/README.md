# Security Docs

Contracts and inventories for the Epic 0 containment work. Each file names the leaf that owns it, and a leaf that changes what a file describes edits it in the same PR.

| File | What it holds | Owner |
| --- | --- | --- |
| [`inventory.md`](inventory.md) | Every execution and render entry point at `62d4eae`, with its auth, inputs, what it starts, where its data goes, its threat category, and the leaf and stage that closes each gap | [#1](https://github.com/keyurgolani/rounds/issues/1) (`ROUNDS-00A-L01`), stage 0 |
| [`server-writes.md`](server-writes.md) | Who may write server-only PocketBase collections, the superuser rule, and the registry of planned writers | [#1](https://github.com/keyurgolani/rounds/issues/1), stage 0 |
| [`account-scope.v1.json`](account-scope.v1.json) | The account-scope policy and one row per user-owned collection, which the inventory reads for its PocketBase rows | [#9](https://github.com/keyurgolani/rounds/issues/9) (`ROUNDS-00B-L01`), stage 1 |
| [`cross-owner-scan.md`](cross-owner-scan.md) | The read-only cross-owner relation scan: what it guarantees, how an operator runs it on a `pb_data` copy, and its report format | [#9](https://github.com/keyurgolani/rounds/issues/9), stage 2 |
| `execution-runbook.md` | Flipping and confirming each gate, each error code, alerts, dependency checks, and repair | [#1](https://github.com/keyurgolani/rounds/issues/1); not added yet |
