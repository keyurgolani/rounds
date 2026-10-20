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

Each JSON file has a schema next to it. DR-0003 pins the SHA-256 of every file here except this README and the fixture, so a change takes a new DR-0003 revision: edit the file, raise the revision, name the prior one in `supersedes` with a `supersessionReason`, and re-pin. A ratified revision is never edited.

## Gate artifacts

Every gate string a leaf can wait on (C0 to C7 for containment, U0 to U11 for everything else) is split into artifacts in DR-0003's `gateArtifacts`, each with exactly one producer: a leaf or stage, or, for an artifact each authority-matrix row needs, the matrix field naming that row's producer (`command_owner.leaf` or `transfer.mapping`). A row whose producer has landed lists where the artifact lives. A producer isn't blocked by its own artifact (spec 3232-3236), and `requiredFor` names the consumers that need an artifact whatever their archetype.

ROUNDS-01 closes once #15, #16, this leaf's S4, and every U0 to U11 producer have merged. Closure gates no leaf.

## Checks and report

`node --test scripts/conformance` runs `scripts/program/lib.mjs`'s checks on these files: each file against its schema, the 20 gates bound, one producer per artifact, every leaf reference resolved, artifact paths present, 16 stages with one owner each, the context order, every journey step mapped, the edge table, and the rollback fixture and defaults. Findings are `PROGRAM_*` codes.

`node scripts/program/report.mjs` prints ROUNDS-01 closure, the pending re-authorization edges, and drift. It reads merged PR titles, closed issues, and the commit messages on `next` through `gh` (read-only), or from a saved file with `--state <file>`; `--json` prints the same as JSON. A stage counts as merged when its `[LEAF-ID/<stage>]` PR merged, and a leaf when its `[LEAF-ID]` PR merged, when the squash message of its finishing PR on `next` says `Closes #N`, or when its issue closed as completed.

## Stages of this leaf

1. **S1** (this): DR-0003, the files above, `scripts/program/lib.mjs`, and `scripts/program/report.mjs`.
2. **S2**, after re-authorization item 6: `leaf-dag.json` and its schema, `scripts/conformance/rules/program.mjs`, `scripts/program/reconcile.mjs`, and `leaf-gate` in report mode. The `leaf-gate` workflows ship disabled behind `vars.LEAF_GATE_ENABLED == 'true'`; the owner turns them on with the `main` ruleset.
3. **S3**, after #18: the context order and rollback defaults, ratified against the ADR.
4. **S4**: `leaf-gate.json` set to `enforce`.
