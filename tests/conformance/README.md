# Containment conformance corpus

Adversarial execution and rendering conformance suites (`ROUNDS-00A-L08`).
The corpus runs hostile fixtures against a stack built from the commit
under test and writes a machine-readable receipt per fixture, so a
containment regression fails CI with the fixture id and redacted
artifacts, and no image ships unless its exact build passed the corpus.

This is stage 1: the framework, the fixtures for guarantees the branch
already enforces, the bait network, and a non-required `containment-corpus`
CI job. Later stages add the required gate and promote-by-digest.

## Layout

| Path | What it is |
| --- | --- |
| `manifest.json` | One row per fixture in the issue's table: id, routes, languages, status, the leaf that closes it, the expected outcome per target, the named control, the `destructive` and `environment_sensitive` flags, setup, teardown. |
| `manifest.schema.json` | The manifest shape. `conformance/manifest.py` is the authoritative validator. |
| `skip_ledger.json` | Skips, each with an owner, an expiry, and a reason. An expired skip, or one for an unknown fixture, fails the lane. Empty at stage 1. |
| `conformance/` | The framework: manifest and ledger loader, the outcome vocabulary, canaries, artifact redaction, the probe budget and deadline, the counting clients, the per-fixture rules (`execute.py`), the receipt serializer, and the corpus stack's take-home definition (`overlay.py`). |
| `corpus/` | One module per `contained` fixture, plus the well-formed request bodies they share (`_requests.py`), each naming an active definition. A `pending` row has no module. |
| `selftest/` | The framework's own unit tests and every fixture's negative control; no stack needed. |
| `conftest.py`, `test_corpus.py` | The pytest plugin and the live run. |
| `compose.yml` | Overlay on `harness/compose.yml`: the enforced runner, the bait network, and the `corpus` driver. |
| `bait/` | The decoys on the bait network. |

## What is committed, and what is not

A fixture module is committed only for a guarantee the branch already
enforces (anonymous execution denied, oversized input refused,
caller-supplied tests or validators refused, the demo flag immutable,
cross-account result reads denied, no runner secret in the candidate
environment, the render proxy echoing no sidecar text). Every other row
in `manifest.json` is a `pending` row that names the leaf which closes it
and carries no fixture code: a runnable probe for a gap still open on
`next` would publish working exploit code before the fix (orchestrator
decision D4). The probe for a pending row lands in the pull request that
closes the gap, and that pull request proves its negative control locally.
A fixture can also list sub-cases that are still open (EX-02's quota
sub-cases, for one); those are `pending` sub-cases with their closing
leaf, and the receipt records them as pending.

Each committed fixture has a negative control in
`selftest/test_negative_controls.py`: the fixture runs through the same
rules the live run applies, against a fake target where its guarantee
holds (it must report `contained`) and against one where that guarantee
is switched off (it must report `detected`). The fakes model answers
only; they run nothing. The manifest's `control` field names each one.

The corpus keeps no committed receipt that shows a sub-case exploitable,
and pulls no `sha-62d4eae` image.

## What the live run checks

`conformance/execute.py` applies these to every fixture:

- every contained sub-case the manifest lists needs an outcome, and the
  fixture's outcome is its worst one; a `not-applicable` row reports one
  outcome for the whole row and passes only as `not-applicable`;
- a canary anywhere in what the fixture saw fails it, and a canary that
  has landed but wasn't planted for the run fails the whole run;
- every route the manifest lists for a fixture must be one it exercised,
  and the receipt records the routes it did exercise;
- every request goes through the counting clients, so the budget sees all
  of them; a fixture past its request or wall-second cap, or past its
  deadline, fails;
- a fixture that raises is `inconclusive`, and a failed teardown fails it;
  an account is tracked before the request that creates it, so one whose
  signup landed before its sign-in failed is removed too;
- whatever a fixture hands back is read as text, so a result in the wrong
  shape fails with its receipt entry, and any problem turns a met outcome
  `inconclusive`;
- the verdict is the strict comparison with the manifest's expectation,
  and a failure reports the fixture's own note and its redacted evidence;
- every manifest row gets a receipt entry (ran, quarantined, or pending),
  and the last case fails the run if one is missing. That case doesn't
  count as a fixture: a run in which no fixture passed or failed fails the
  lane, every fixture quarantined included.

A fixture keeps only what it needs as evidence. EX-07's program prints
the candidate's environment, so it keeps that output's SHA-256 and the
names of any variable outside the minimal environment, never a value.

## Running it

Needs a container runtime and `harness/compose.yml` (#9's harness). Local
runs use Finch; CI uses Docker.

```sh
# The whole corpus, local (Finch):
tests/conformance/run.sh

# CI (Docker on ubuntu):
COMPOSE_BIN="docker compose" tests/conformance/run.sh

# One fixture and its context, by id:
tests/conformance/run.sh -k EX-07

# Or directly against an already-built stack:
docker compose -f harness/compose.yml -f tests/conformance/compose.yml \
  run --rm corpus -k EX-07

# The framework's own unit tests (no stack):
python -m pytest tests/conformance/selftest
```

The launcher builds PocketBase, the runner, the corpus driver, and the
bait image from the commit, generates the run's canaries, brings up
PocketBase and the runner, runs the corpus, writes
`.receipts/containment-receipt.json`, and tears the stack down.

No take-home definition is active on this branch, so a take-home body
would stop at the definition step. The launcher writes one only the
corpus stack has (`python3 tests/conformance/conformance/overlay.py --out
DIR`, into `CORPUS_DEFINITIONS`): the real manifest plus one entry for the
active AI-coding HTTP-client revision keyed as a take-home, which
`compose.yml` mounts read-only into the runner's definitions directory. A
direct `docker compose ... run` needs that directory written first, at
`tests/conformance/.definitions` by default.

## When a fixture detects a regression

The run fails with the fixture id and its redacted evidence. To respond:

1. Check the runtime: Docker or Finch is up, and `harness/compose.yml`
   builds. A missing runtime, zero fixtures collected, or everything
   skipped fails the lane by design.
2. Reproduce the one fixture: `tests/conformance/run.sh -k <ID>`.
3. Fix the regression in the runner, worker, or renderer, or, if it cannot
   be fixed at once, quarantine the fixture with an owner and an expiry in
   `skip_ledger.json` and disable its route by default through #1's gate
   registry. A quarantined containment fixture blocks promotion unless its
   route ships disabled. EX-01 records a route its gate turned off as
   contained by the gate, so turning a route off doesn't turn EX-01 red.
4. Rerun green.

## Receipts

Each run writes one `rounds-containment-receipt/v1` file (git-ignored,
uploaded as a CI artifact): the commit, corpus version, target, image
references, the contract versions, the canary-set id, and the run's total
probe spend, plus one entry for every manifest row. A fixture that ran
records its outcome, expectation, verdict, each sub-case's status (and
outcome when contained), the routes it exercised, its redacted evidence
and checksums, a canary-hit boolean per canary, its spend, the reason for
its verdict, and its note. A quarantined fixture records the skip
ledger's owner and expiry; a pending row records its closing leaf. A field
a later leaf introduces reads `absent`. A passing run's receipt states
`contained`, `not-applicable`, `pending`, or `quarantined` only.

## Canaries

Each run plants fresh, secret-shaped placeholders (never real secrets) as
the runner's environment: the provider-key secret, the admin credentials,
and the admission secret. A fixture scans output for them, and every
retained artifact is redacted before it is written, because the repository
is public. The canaries a later leaf introduces (`ROUNDS_EXECUTION_SECRET`,
the launcher token) are carried as `absent` until that leaf lands.
