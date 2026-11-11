"""Hostile fixtures for the containment corpus (one module per fixture).

Each module here corresponds to a ``contained`` row in
``manifest.json`` and exposes a single ``run(ctx)`` function returning a
:class:`~corpus._base.Result`. A module is committed only for a guarantee
the branch already enforces; a guarantee still open on this branch is a
``pending`` row in the manifest with no module (orchestrator decision
D4). A fixture states the guarantee it checks and the contained answer it
expects; it carries no attack recipe or bypass-revealing request shape.
"""
