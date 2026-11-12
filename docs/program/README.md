# Transformation Program

The order in which the transformation lands, what each leaf must produce before others may build on it, and how each bounded context moves to its new authority. Owned by [#17](https://github.com/keyurgolani/rounds/issues/17) (`ROUNDS-01-L03`) and decided in [DR-0003](../decisions/DR-0003-transformation-program.json). Spec lines refer to the approved rounds-review spec, `docs/superpowers/specs/2026-10-18-rounds-review-board-design.md`.

## Files

| File | What it holds |
| --- | --- |
| [`cutover-policy.md`](cutover-policy.md) | The data-preserving clean cutover rules, the owner of each of the 16 migration stages, the draft context order, and the rollback defaults |
| [`rollback-template.schema.json`](rollback-template.schema.json) | The rollback template each authority transfer fills once per context; [`fixtures/rollback-synthetic.json`](fixtures/rollback-synthetic.json) is a synthetic example |
| [`non-goals.json`](non-goals.json) | Product non-goals, every catalog tradeoff verbatim, and the reference leaf issue (gate U11) |
| [`definition-of-done.json`](definition-of-done.json) | DOD-1 to DOD-7, what done means for every implementation leaf |
| [`journeys.json`](journeys.json) | Each primary journey step mapped to one leaf, milestone, and gate, and the first-run trace |
| [`reauthorization.md`](reauthorization.md) | The rounds-review catalog changes, in order, for one owner authorization, and the edges they add or drop |
| [`program-record.schema.json`](program-record.schema.json) | The format of DR-0003's gate strings, gate artifacts, and closure condition |
| [`issue-export.json`](issue-export.json) | Each filed issue's number, title, and "Exact prerequisite leaf issues" section, as GitHub held it on `exportedOn`, with a SHA-256 over them |
| [`leaf-program.json`](leaf-program.json) | The DAG's other input: base phase and milestone rules, the stage lists the issue bodies name, `satisfiedBy`, and edge corrections, each with its reason |
| [`leaf-dag.json`](leaf-dag.json) | Generated: one node per leaf with its phase, milestone, stages, and filed prerequisites; the five folded ids under `dropped` |
| [`leaf-gate.json`](leaf-gate.json) | The leaf gate's mode, `report` or `enforce` |

Each JSON file has a schema next to it. DR-0003 pins the SHA-256 of every file here except this README and the fixture, so a change takes a new DR-0003 revision: edit the file, raise the revision, name the prior one in `supersedes` with a `supersessionReason`, and re-pin. A ratified revision is never edited.

## Gate artifacts

Every gate string a leaf can wait on (C0 to C7 for containment, U0 to U11 for everything else) is split into artifacts in DR-0003's `gateArtifacts`, each with exactly one producer: a leaf or stage, or, for an artifact each authority-matrix row needs, the matrix field naming that row's producer (`command_owner.leaf` or `transfer.mapping`). A row whose producer has landed lists where the artifact lives. A producer isn't blocked by its own artifact (spec 3232-3236), and `requiredFor` names the consumers that need an artifact whatever their archetype.

ROUNDS-01 closes once #15, #16, this leaf's S4, and every U0 to U11 producer have merged. Closure gates no leaf.

## The leaf DAG

`scripts/program/dag.mjs` builds `leaf-dag.json` from `issue-export.json` and `leaf-program.json`, offline, so CI never reads GitHub. It parses each section's references (`#N`, leaf ids, ranges like `#19 to #22` and `` `ROUNDS-02-L02` to `L05` ``, and the `` `-L03` `` shorthand) and their stage qualifiers (`#1's stage 3`, `#91 Stage 1`, `` `ROUNDS-01-L03/S2` ``). A line that starts with a stage ("Stage 2 adds", "S1:", "1b needs") scopes its edges to that stage of the dependent (`forStages`), and "Stage 1 needs only #45" keeps the leaf's other edges off that stage. It skips what isn't this leaf's prerequisite: downstream lists, dropped, transitive, soft, rollout-only and section gates, closure edges, and sentences about other leaves. Every edge keeps the body's words as its `reason` and the export line as its `source`.

Stage ids are the per-PR labels (`S<n>`, `S<letter>`, `P<n>`, and the step numbers of #2, #3, and #4). Where a body has a stage section, `leaf-program.json` lists the stages (`stagesComplete: true`); otherwise the DAG lists the stages other sections reference (`stagesComplete: false`). An edge on a whole staged leaf waits on every stage, or on the stages its `satisfiedBy` names (#17's dependents need S2; #178's need its stages through 2d). Phase follows spec 3072-3091 and milestone spec 3098-3147, by capability rule, then a prerequisite is pulled into the phase and milestone of the earliest leaf that needs it.

To refresh after the bodies change:

```sh
gh issue list --repo keyurgolani/rounds --state all --limit 300 --json number,title,body > issues.json
node scripts/program/export.mjs --from issues.json --write
node scripts/conformance/run.mjs --write
```

Then re-pin both files in a new DR-0003 revision.

## Checks

The `program` rule (`scripts/conformance/rules/program.mjs`) runs in the `conformance` job and in `node scripts/conformance/run.mjs`. It runs `scripts/program/lib.mjs`'s checks: each file against its schema, the 20 gates bound, one producer per artifact and no artifact twice, every leaf reference resolved, artifact paths present, 16 stages with one owner each, the context order, every journey step mapped, the edge table, and the rollback fixture (its defaults, its context in its transfer node's list, and its decision owner), and the registers against their sources (DOD-1 to DOD-7, and the spec's non-goals and journey steps and the catalog's tradeoffs, pinned as `SOURCE_SETS` digests). It adds the DAG's checks: the export's checksum and the DAG's record of both inputs (`PROGRAM_EXPORT_STALE`), node ids against `contracts/vocabulary/leaf-ids.json` (`PROGRAM_DAG_UNKNOWN`, `PROGRAM_DAG_DUPLICATE`, `PROGRAM_DAG_DROPPED`, `PROGRAM_DAG_MISSING`), an edge without a reason (`PROGRAM_EDGE_REASON`), an unknown prerequisite or stage, cycles over the stage nodes (`PROGRAM_DAG_CYCLE`), and decision-record references (`PROGRAM_DR_UNRESOLVED`: the DAG, `leaf-program.json`, and `leaf-gate.json` cite the current DR-0003 revision, and every `DR-nnnn@r` here resolves and isn't superseded by a breaking revision). It regenerates the DAG in memory, so a hand edit fails as `CONFORMANCE_DRIFT`.

## Leaf gate

`scripts/program/leaf-gate.mjs` runs as the last step of the `conformance` job on every pull request, with `contents: read` and no `pull_request_target`, `workflow_dispatch`, or status write. It takes the PR title from the step's environment (never interpolated into the script, and never printed), reads its `[LEAF-ID]` or `[LEAF-ID/<stage>]` label, and checks that leaf's prerequisites (for a stage, the edges that bind it) against the base branch's commit messages. A prerequisite counts once it's merged into the base: its stage PR's squash subject, its `[LEAF-ID]` PR, `Closes #N` in its finishing PR's squash message, or every stage its `satisfiedBy` names (or every listed stage, when the list is complete). Each one missing is reported under `LEAF_GATE_BLOCKED` with its reason.

It fails closed: a missing or unlabeled title (`LEAF_GATE_UNLABELED`), an unknown or folded leaf or a stage the DAG doesn't list (`LEAF_GATE_UNKNOWN`), and an unreadable DAG or base history (`LEAF_GATE_UNREADABLE`) are blocked verdicts, and an unreadable `leaf-gate.json` fails the step. In `report` mode it prints the verdict and a warning annotation and passes; in `enforce` it fails the job. The verdict is computed on a push, so a retitled PR needs a new push or a re-run. Locally: `PR_TITLE='... [ROUNDS-02-L01]' node scripts/program/leaf-gate.mjs --base origin/next`.

## Report

`node scripts/program/report.mjs` prints ROUNDS-01 closure, the pending re-authorization edges, and drift. It reads the titles of PRs merged into `next`, closed issues, and the commit messages on `next` through `gh` (read-only), or from a saved file with `--state <file>`; `--json` prints the same as JSON. A stage counts as merged when its `[LEAF-ID/<stage>]` PR merged, and a leaf when its `[LEAF-ID]` PR merged, when the squash message of its finishing PR on `next` says `Closes #N`, or when its issue closed as completed. A leaf is done only once its issue closed as completed (a stage once its PR merged), so a `done` edge waits for that, while `merged` and `closure` edges wait for the merge.

## Stages of this leaf

1. **S1**: DR-0003, the policy files, `scripts/program/lib.mjs`, and `scripts/program/report.mjs`.
2. **S2** (DR-0003 revision 2): the issue export, `leaf-program.json`, `leaf-dag.json`, `leaf-gate.json` and their schemas, `scripts/program/dag.mjs`, `export.mjs`, and `leaf-gate.mjs`, and the `program` rule, with the gate in report mode. Built from the filed bodies, without waiting for re-authorization item 6.
3. **S3**, after #18: the context order and rollback defaults, ratified against the ADR.
4. **S4**, after the owner's `main` and `next` rulesets require `conformance`: `leaf-gate.json` set to `enforce`.

Deferred from S2 to the backlog: revision 1's `leaf-gate-dispatch.yml` and `leaf-gate.yml` pair and its posted status; the open-PR limit (`LEAF_GATE_WIP`), `program:override`, and protected paths; `scripts/program/reconcile.mjs` and body drift; edge kinds (`done`, `merged`, `closure`), `proposedPrerequisites` and the `edgeSet` switch; and each node's `gates`, `consumes`, `dod`, `size`, `archetype`, and `boundedContext`. Until then every edge waits for a merge into the base, closure edges a body names are left out, and leaves whose bodies have no stage section keep derived stage lists.
