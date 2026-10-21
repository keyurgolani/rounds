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
| `conformance/` | The framework: manifest and ledger loader, the outcome vocabulary, canaries, artifact redaction, the probe budget, and the receipt serializer. |
| `corpus/` | One module per `contained` fixture. A `pending` row has no module. |
| `selftest/` | The framework's own unit tests; no stack needed. |
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

Fault profiles (the negative controls) live only in
`tests/conformance/faults/`, tagged `ci-fault-*`, and are never committed
or pushed. Each names the fixtures it must make fail.

The corpus keeps no committed receipt that shows a sub-case exploitable,
and pulls no `sha-62d4eae` image.

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
   route ships disabled.
4. Rerun green.

## Receipts

Each run writes one `rounds-containment-receipt/v1` file (git-ignored,
uploaded as a CI artifact): the commit, corpus version, target, image
references, the contract versions, and the canary-set id, plus one entry
per fixture with its outcome, expectation, verdict, artifact checksums,
and a canary-hit boolean per canary. A field a later leaf introduces reads
`absent`. Receipts state `contained` or `pending` only.

## Canaries

Each run plants fresh, secret-shaped placeholders (never real secrets) as
the runner's environment: the provider-key secret, the admin credentials,
and the admission secret. A fixture scans output for them, and every
retained artifact is redacted before it is written, because the repository
is public. The canaries a later leaf introduces (`ROUNDS_EXECUTION_SECRET`,
the launcher token) are carried as `absent` until that leaf lands.
