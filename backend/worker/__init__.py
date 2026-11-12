"""The code worker (ROUNDS-00A-L05): what runs inside a rounds-worker
container, and the protocol it shares with the launcher.

``init.py`` is the container's PID 1. ``frames``, ``manifest``, and
``seccomp`` use only the standard library, because the worker image carries
no app code and the launcher imports the same modules to read what a worker
says.
"""
