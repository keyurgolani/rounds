# Catalog re-authorization (ROUNDS-01-L03)

DR-0003 decision P11. Every issue body and the dependency export render from the owner's rounds-review catalog, and `npm run issues:file` reverts a body the catalog doesn't carry. These are the rounds-review changes, in order, for one owner authorization. Nothing here edits an issue: the owner applies them in rounds-review, and S2 of this leaf is built on the export they produce. This file is governed by DR-0003; the edge table is read by `scripts/program/lib.mjs`, so keep its columns.

## Order

1. **Per-leaf state in the filer.** The filer hard-codes `state: "open"` (rounds-review `scripts/file-issues.mjs:79`) and reopens closed issues (`:755`, `:1038-1039`). It keeps each leaf's state instead, so `issues:file` never reopens a completed leaf. This goes first: running `--apply` before it reopens every closed leaf.
2. **Prerequisites with `reason` and `kind`.** Every prerequisite gets a reason and a kind (`done`, `merged`, or `closure`, decision P13), staged leaves get stage edges, and the catalog adds or drops the edges in the table below. Two rules add edges per leaf rather than one by one: each leaf with the catalog `ai` flag depends on ROUNDS-14 (spec 3094), and each leaf whose rule runs in #170's (`ROUNDS-34-L01`) job depends on the #170 stage that rule needs, since spec 3075-3076 puts #170 in phase 2.
3. **Gate binding by domain, with producer exemptions.** Gates bind to the leaves that consume each artifact in DR-0003's `gateArtifacts`, not by archetype, and a producer isn't blocked by its own artifact (spec 3232-3236). `requiredFor` adds U4 to #43 and #130 to #137, U8 to #133 to #135, and U9 to #93, #94, and #161.
4. **Surface archetypes and one owner each.** #152 (`ROUNDS-31-L07`) is retargeted off #143 (`ROUNDS-30-L02`) to the Preparation plan read model (DR-0002 OD-3), #161 verifies #4's snapshots, #107 (`ROUNDS-22-L02`) owns Career Activity over #112 and #88, #164 is final removal only, and #26 owns the profile completeness explanations of spec 1030 (DR-0003 decision P10).
5. **Verbatim catalog text.** The catalog's `ai`, `migration`, and `tradeoffs` text verbatim, a numbers block (spec 2015-2067), and `consumes:` and `dod:` lines in each body.
6. **Per-leaf program fields.** `milestone`, `phase`, `size`, `stages`, `authorityTransfer`, and `boundedContext` for the 176 filed leaves and six kept proposals, from each refined body's Effort or stage table. S2 is built after this item.
7. **Corrections from #15 and #16.** Import #15's `DR-0001-owner-corrections.md`, #16's `owner-labels.json` and `owner-sentence-corrections.json`, and the #18 and #36 edges below, so `--apply` carries them.
8. **Apply and export.** `issues:file --apply`, then a regenerated export with its receipt. The receipt moves the export's `edgeSet` from `filed` to `reauthorized` (S2).

Each refined body's own catalog change, listed under "Owner input needed" in its Refinement review, rides items 2 to 6 with these. From S2, `scripts/program/reconcile.mjs` reports a body whose edges the export lacks as `DAG_BODY_DRIFT`.

## Spec-change requests

- **SCR-1, ROUNDS-32 tradeoff wording.** The catalog's ROUNDS-32 tradeoff names the cutover without "data-preserving", the wording DR-0001 G11 fails in any new text. It rides item 5: change it in rounds-review `src/data/capabilities.json` to "A data-preserving clean cutover requires deliberate gates and temporary adapters but avoids permanently paying for dual writes and reconciliation." Then `non-goals.json` quotes the new wording, and the DR-0001@2 allowlist entry for its line goes (`VOCAB_CUTOVER_ALLOWLIST_STALE` flags the entry once the line no longer holds the unqualified phrase).

## Edges

`add` puts the edge in the export; `drop` removes a filed edge. A prerequisite is a leaf, a stage, or a capability (all its leaves). `scripts/program/report.mjs` lists these as pending until the receipt.

| Edge | Change | Dependent | Prerequisite | Kind | Reason | Source |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | add | `ROUNDS-15-L04` | `ROUNDS-00A-L04` | done | #80 converts the Legacy Artifact Snapshots #4 creates. | #17 item 2 |
| E2 | add | `ROUNDS-03-L02` | `ROUNDS-14-L01` | done | #25's field dispositions use #72's privacy classes. | #17 item 2 |
| E3 | add | `ROUNDS-03-L02` | `ROUNDS-32-L02` | done | #25's migration runs on #156's framework. | #17 item 2 |
| E4 | add | `ROUNDS-27-L01` | `ROUNDS-31-L08` | done | Universal search reads #153's search projections. | #17 item 2 |
| E5 | add | `ROUNDS-27-L02` | `ROUNDS-09` | done | Command Center capture modes open the Capture Center. | #17 item 2 |
| E6 | add | `ROUNDS-29-L03` | `ROUNDS-26` | done | Preparation plans create native Actions. | #17 item 2 |
| E7 | add | `ROUNDS-34-L07` | `ROUNDS-32-L10` | done | The release runner proves legacy removal. | #17 item 2 |
| E8 | add | `ROUNDS-01-L03/S3` | `ROUNDS-02-L01` | done | S3 ratifies the context order and rollback defaults against the ADR. | #17 stage gates |
| E9 | drop | `ROUNDS-02-L01` | `ROUNDS-01-L03` | done | With E8 it would deadlock; DR-0001 correction 1 moved the gate it stood for to ROUNDS-01 closure. | #17 stage gates, #16 |
| E10 | add | `ROUNDS-01-L03/S4` | `ROUNDS-00A-L01/S5` | merged | `leaf-gate` enforces only behind #1's release guard. | #17 stage gates |
| E11 | add | `ROUNDS-02-L01` | `ROUNDS-01-L01` | done | #18's records follow #15's decision record format. | #16 |
| E12 | add | `ROUNDS-02-L01` | `ROUNDS-01-L02` | done | #18's ERD covers every store in #16's baseline-stores.json. | #16 |
| E13 | add | `ROUNDS-02-L01` | `ROUNDS-00B-L01/S1` | merged | #18's PR 3 repins #9's harness. | #16 |
| E14 | add | `ROUNDS-02-L01` | `ROUNDS-00A-L01/S3` | merged | #18's ERD covers #1's admission stores. | #16 |
| E15 | add | `ROUNDS-06-L01` | `ROUNDS-01-L02` | done | Each registry entry matches its DR-0002 matrix row. | #16 |
| E16 | add | `ROUNDS-00B-L01/S4` | `ROUNDS-00A-L01/S0` | merged | #9's stage 4 consumes #1's stage 0. | #1 |
| E17 | add | `ROUNDS-00B-L01/S4` | `ROUNDS-00A-L01/S2` | merged | #9's stage 4 consumes #1's stage 2. | #1 |
| E18 | add | `ROUNDS-00A-L01/S4` | `ROUNDS-00B-L01/S1` | merged | #1's stage 4 runs in #9's harness skeleton. | #1 |
| E19 | add | `ROUNDS-32-L01/S2` | `ROUNDS-32-L02/S1` | merged | #156's stage 1 fingerprint gates #155's stage 2. | #155 |
| E20 | add | `ROUNDS-32-L02/S1` | `ROUNDS-32-L01/S1` | merged | #156's stage 1 needs only #155's stage 1. | #155 |
| E21 | add | `ROUNDS-00B-L05` | `ROUNDS-00B-L02` | done | #13's suite covers relation and merge authorization. | orchestrator |
| E22 | add | `ROUNDS-02-L02` | `ROUNDS-00B-L02` | done | The gateway checks relation endpoints with #10's predicate. | orchestrator |
| E23 | add | `ROUNDS-04-L03` | `ROUNDS-00B-L02` | done | #29 takes over #10's deleted and redirected endpoint checks. | orchestrator |
| E24 | add | `ROUNDS-06-L02` | `ROUNDS-00B-L02` | done | Relation endpoints pass #10's endpoint predicate. | orchestrator |
| E25 | add | `ROUNDS-08-L04` | `ROUNDS-00B-L02` | done | Entity lookup relies on #10 refusing another account's records. | orchestrator |
| E26 | add | `ROUNDS-28-L08` | `ROUNDS-31-L06/P1` | merged | #137's reader switch waits on #151's track and overview sections. | #137, #151 |
