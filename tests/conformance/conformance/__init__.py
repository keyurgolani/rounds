"""Containment conformance corpus framework (ROUNDS-00A-L08).

The framework runs the hostile-fixture corpus against a stack built from
the commit under test and writes a machine-readable receipt per fixture.
This package holds only the reusable parts: the manifest and skip-ledger
loader and validator, the outcome vocabulary and its comparison, canary
handling, artifact redaction, the probe budget, and the receipt
serializer. The fixtures themselves live in ``corpus/`` (one module per
fixture), the pytest plugin in ``conftest.py``, and the self-tests in
``selftest/``.

No part of this package encodes an attack recipe or a request shape that
reproduces a bypass. A fixture states the guarantee it checks and the
contained answer it expects; a regression fails the lane with the fixture
id and redacted artifacts. Fixtures are committed only for guarantees the
branch already enforces; every other inventory row is a ``pending`` row
in the manifest naming the leaf that closes it, with no fixture code
(orchestrator decision D4).
"""

CORPUS_VERSION = "1"
RECEIPT_SCHEMA = "rounds-containment-receipt/v1"
