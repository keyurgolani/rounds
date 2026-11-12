"""Hostile fixtures for the containment corpus (one module per fixture).

Each module here is named for its fixture's id (``ex_01_*.py`` is EX-01's)
and carries that fixture's detail as ``SPEC``, a literal that
``conformance/manifest.py`` reads and checks: the routes, the sub-cases,
the expected outcome per target, the languages, the named negative
control, setup, teardown, and the ``destructive`` and
``environment_sensitive`` flags. It exposes a single ``run(ctx)``
function returning a :class:`~corpus._base.Result`. A module is committed
only for a guarantee the branch already enforces; a fixture's probe lands
with the fix that makes it pass (orchestrator decision D4). A fixture
states the guarantee it checks and the contained answer it expects; it
carries no attack recipe or bypass-revealing request shape.
"""
