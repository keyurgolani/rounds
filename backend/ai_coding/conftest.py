"""Exclude `rounds/` from pytest collection.

The files under `backend/ai_coding/rounds/<slug>/checkpoints/<idx>/tests/`
are content seeded into a candidate's workspace at runtime by
``project_runner.py``. They import modules from the candidate's tree
(not from this repo) and would fail to collect as standard pytest
tests. Excluding the whole `rounds/` subtree keeps the backend suite
clean while still letting `build_seed.py` walk the directory.
"""
collect_ignore_glob = ["rounds/*"]
