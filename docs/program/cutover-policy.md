# Data-preserving clean cutover policy

DR-0003 decisions P2 to P5 (ROUNDS-01-L03). Spec lines refer to rounds-review `docs/superpowers/specs/2026-10-18-rounds-review-board-design.md` (spec 2637-2716). This file is governed by DR-0003: a change takes a new DR-0003 revision. The two tables below are read by `scripts/program/lib.mjs`, so keep their columns.

## Rules

1. The program moves one bounded context at a time (spec 2641-2647). Temporary expand and contract schemas, compatibility adapters, shadow reads, and comparisons are allowed. Each converted concept has one writable authority at every revision ([DR-0002](../decisions/DR-0002-authority-matrix.json) M2), a retirement criterion (its matrix row's `transfer.retirement`), and a time-bounded compatibility window (`transfer.window`). Adapters read, shadow, or compare; they never write.
2. No migration is approved before #155 (`ROUNDS-32-L01`) covers every store in its disposition manifest, with counts, checksums, unresolved cases, and validation evidence (spec 2649-2673).
3. An `authorityTransfer` node is the PR that ships a run plan, after its mapping leaves, with one transfer per context it lists. #163's run stages 0 to 6 are transfers inside its P1 node, not nodes. Transfers run after merge, under #156's (`ROUNDS-32-L02`) one-context-at-a-time rollout; `leaf-gate` (S2) limits only open PRs.
4. Freezes never overlap, and a context sits in exactly one transfer node's list.
5. Each transfer fills [`rollback-template.schema.json`](rollback-template.schema.json) once per context it lists, as `docs/program/transfers/<leaf>-<context>.json` in its own PR (from S2).
6. A database snapshot alone is not a rollback once new writes exist (spec 2699). A rollback replays or compensates post-switch changes and never discards them, and startup refuses an incompatible schema or pack version (spec 2715-2716).
7. #164 (`ROUNDS-32-L10`) is final removal only: it runs stage 16 and removes the legacy paths after every context's receipt. It switches no authority of its own.

## Migration stages

Each stage of spec 2677-2695 has one owner leaf: the leaf whose mechanism or receipt the stage runs on. `Runs` says whether the stage happens once for the program, in every transfer for each context it lists, or between transfers. `With` lists the other leaves the stage works with.

| Stage | Spec | Step | Owner | Runs | With |
| --- | --- | --- | --- | --- | --- |
| 1 | 2677 | Contain the execution and sharing P0s before migration work. | `ROUNDS-00A-L08` | once | `ROUNDS-00B-L05` |
| 2 | 2678 | Ratify database/transaction and authorization ADRs. | `ROUNDS-02-L01` | once | `ROUNDS-34-L03`, `ROUNDS-00B-L01` |
| 3 | 2679 | Inventory the complete disposition manifest and operational baseline. | `ROUNDS-32-L01` | once | none |
| 4 | 2680 | Produce immutable backups, key/secret handling plan, and checksums. | `ROUNDS-32-L03` | once | `ROUNDS-14-L02` |
| 5 | 2681 | Introduce migration/change-journal infrastructure and schema-version gates. | `ROUNDS-32-L02` | once | none |
| 6 | 2682 | Dry-run one bounded context and generate stable identifier maps. | `ROUNDS-32-L02` | per transfer | each row's mapping leaf |
| 7 | 2683-2684 | Report duplicates, ambiguous matches, invalid records, lossy fields, and browser-local data requiring reconciliation. | `ROUNDS-32-L02` | per transfer | `ROUNDS-32-L04` |
| 8 | 2685 | Resolve or explicitly defer blocking items. | `ROUNDS-32-L02` | per transfer | `ROUNDS-31-L09` |
| 9 | 2686 | Backfill target records and compare shadow reads. | `ROUNDS-32-L02` | per transfer | each context's read models |
| 10 | 2687-2688 | Validate authorization, referential integrity, domain invariants, artifact rendering, and primary journeys. | `ROUNDS-32-L02` | per transfer | `ROUNDS-34-L03`, `ROUNDS-34-L04` |
| 11 | 2689 | Freeze only the bounded context's writes and apply its final delta. | `ROUNDS-32-L02` | per transfer | none |
| 12 | 2690 | Switch its command/read paths behind a version gate. | `ROUNDS-32-L02` | per transfer | none |
| 13 | 2691 | Observe acceptance criteria and projection health. | `ROUNDS-34-L05` | per transfer | `ROUNDS-31-L01`, `ROUNDS-31-L09` |
| 14 | 2692 | Retire its legacy write path. | `ROUNDS-32-L02` | per transfer | `ROUNDS-32-L10` |
| 15 | 2693 | Repeat for the next bounded context. | `ROUNDS-01-L03` | between transfers | `ROUNDS-32-L02` |
| 16 | 2694-2695 | Rehearse full backup restore and reverse/forward recovery before final legacy-schema removal. | `ROUNDS-32-L10` | once | `ROUNDS-32-L03` |

How each owner runs its stage:

- Stage 1: #8's release gate needs #1 to #7, and #13's suite needs #9 to #12, so together they close ROUNDS-00A and ROUNDS-00B. The `share` transfer below is containment's own (#14) and needs #13, not #8.
- Stage 2: #18's database and transaction ADR and ERD; #172's authorization matrix, with #9's account-scope rows.
- Stage 3: #155's registry, scans, absence proofs, and owner sign-off. Cutover stays blocked for unowned durable state.
- Stage 4: #157's stage A backup, restore, and parity, with #73's keyring for provider keys. A fresh backup and a rehearsal receipt come before each transfer.
- Stage 5: #156's manifests, fingerprint, change journal, freeze, and version marker.
- Stages 6 to 12: #156's dry run, report, unresolved records, shadow backfill, checks, freeze, and switch, run by the transfer node with each matrix row's mapping leaf (DR-0002 `transfer.mapping`). A deferred blocking item needs an owner-approval record (spec 2685), and #154 (`ROUNDS-31-L09`) counts the deferrals. #158 (`ROUNDS-32-L04`) reconciles browser-local data. Validation uses #172's matrix and the primary journeys in [`journeys.json`](journeys.json) through #173.
- Stage 13: #174's alerts and operational targets, #146's projector health, and #154's Data Health, until the transfer's rollback deadline.
- Stage 14: #156's `close-rules` step applies each row's retirement; #164's stage B removes the code after the receipt and 14 days without an accepted write to a retired store.
- Stage 15: the context order below. The next transfer starts only after the previous one is switched and observed.
- Stage 16: #164 runs it on a deployment copy with #157's rehearsal, before any schema is removed.

## Context order (draft)

S3 ratifies this order against #18's ADR (decision P3). Milestones are spec 3104-3147. A transfer node's contexts run in the order listed.

| Order | Milestone | Context | Transfer node | Runs |
| --- | --- | --- | --- | --- |
| 1 | 0 | `share` | `ROUNDS-00B-L06/S1` | #14: legacy share links revoked and reissued as capabilities |
| 2 | 1 | `account` | `ROUNDS-32-L05` | #159's Account transfer: #25, #178, #158, #73 |
| 3 | 1 | `directory` | `ROUNDS-32-L05` | #159's Directory transfer: #30 |
| 4 | 1 | `career-profile` | `ROUNDS-32-L05` | #159's Career Profile transfer: #35, #38 |
| 5 | 2 | `pipeline` | `ROUNDS-32-L06/S1` | #98's applications split |
| 6 | 2 | `campaign` | `ROUNDS-32-L06/S2` | #121's campaign lens |
| 7 | 2 | `people-pursuit-notes` | `ROUNDS-32-L06/S3` | #114 stage 1 |
| 8 | 2 | `actions` | `ROUNDS-32-L08/S1` | #125 via #162 |
| 9 | 3 | `materials` | `ROUNDS-32-L07` | #161's materials run: #80, #85, #84 |
| 10 | 4 | `interview` | `ROUNDS-32-L06/S4` | #110's interview rounds |
| 11 | 4 | `people-round-notes` | `ROUNDS-32-L06/S5` | #114 stage 2 |
| 12 | 4 | `offer` | `ROUNDS-32-L06/S6` | #115 with #118's decisions |
| 13 | 5 | `practice-0` | `ROUNDS-32-L09/P1` | content, #43 stage A |
| 14 | 5 | `practice-1` | `ROUNDS-32-L09/P1` | Coding, #133 |
| 15 | 5 | `practice-2` | `ROUNDS-32-L09/P1` | System Design, #132 |
| 16 | 5 | `practice-3` | `ROUNDS-32-L09/P1` | Behavioral, #136 |
| 17 | 5 | `practice-4` | `ROUNDS-32-L09/P1` | AI-assisted Coding, #134 |
| 18 | 5 | `practice-5` | `ROUNDS-32-L09/P1` | Take-home, #135 |
| 19 | 5 | `practice-6` | `ROUNDS-32-L09/P1` | shared status and timers, #137 |

After the last transfer, #164 (`ROUNDS-32-L10`, Milestone 7) runs stage 16 and removes the legacy paths.

### Open for S3

1. Ratify the order against #18's ADR; its store and transaction boundaries may merge or split contexts.
2. Share rows: DR-0002@1 names #161 as their transfer leaf and #14 as their mapping leaf. This draft gives #14/S1 the `share` context in Milestone 0 (legacy links revoked and reissued as capabilities over Legacy Artifact Snapshots), and #161 retargets those capabilities to Artifact Revisions inside `materials`. S3 decides which node holds the share rows' transfer and supersedes DR-0002 if a row's transfer leaf changes.
3. #43's round types land in Milestone 5, and #160's S4 and S5 wait on them unless #43 ships them early (#110, #160). S3 moves `interview` and `people-round-notes` to Milestone 5 or pulls #43's round types forward.
4. The rollback defaults below, against #18's benchmark.

## Rollback

Every transfer fills the template once per context: the 11 fields of spec 2703-2713 (rollback deadline, allowed downtime, recovery point objective, recovery time objective, forward and reverse compatibility, final write-freeze boundary, replay or reverse-delta journal, treatment of public shares, exports, emails, and other external effects, partial-deploy detection, read-model downgrade or rebuild, and decision owner), plus `upgradeSource` (the tag, commit, and image digests a rollback returns to) and `backupConsistency`. [`fixtures/rollback-synthetic.json`](fixtures/rollback-synthetic.json) fills it with synthetic values.

Defaults (draft, decision P5; S3 ratifies them against #18's benchmark):

| Default | Value | Spec |
| --- | --- | --- |
| Final write freeze | at most 15 minutes | 2062 |
| Recovery point | zero accepted writes lost | 2063 |
| Recovery time | at most 30 minutes at the scale floor (spec 2020-2028) | 2064-2065 |
| Restore | rehearsed, not inferred from a successful backup | 2066-2067 |

A transfer may tighten a default. Loosening one needs a `deviations` entry naming the owner's approval.
