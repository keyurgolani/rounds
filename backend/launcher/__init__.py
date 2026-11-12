"""The code launcher (ROUNDS-00A-L05): the runner image's second entrypoint,
``python -m launcher``, and the only process that can start code workers.

It holds no app secret. Only the runner reaches it, over the internal
``exec`` network and with ``ROUNDS_LAUNCHER_TOKEN``. It talks to one
rootless engine, the worker daemon in ``DOCKER_HOST``, and builds every
worker from constants and #2's resource profile, never from a request.

- ``config``: its settings, read once at start.
- ``engine``: a small client of the engine's API over its unix socket.
- ``preflight``: what the engine and the settings must be before any
  worker starts.
- ``profile``: isolation profile v1, the one container spec every worker
  gets.
- ``jobspec``: job spec v1, checked before any worker exists.
- ``run``: one job in one worker, read through frame protocol v1.
- ``pool``: the slots, pre-started workers, cleanup, quarantine, and the
  reaper.
- ``server``: the HTTP routes the runner calls.
- ``events``: its ``execution.launcher`` lines.
- ``canary``: one known job, for operators.
"""
