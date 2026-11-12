"""``python -m launcher`` (ROUNDS-00A-L05).

Reads its settings, runs the preflight, and then either starts (the slots,
the reaper, and the routes) or refuses: one ``execution.launcher`` line
naming everything missing, and routes that answer 503 ``not_ready``, until a
restart. A refused launcher never creates a worker.

``--check`` runs the preflight only, prints its line, and exits 0 when the
launcher could start or 3 when it would refuse.
"""
from __future__ import annotations

import sys

from launcher import config, events, preflight, server
from launcher.engine import Engine
from launcher.pool import Pool

REFUSED_EXIT = 3


def build(cfg: config.Config) -> tuple[server.State, Pool | None]:
    result = preflight.run(cfg)
    if not result.ok:
        events.refused(result.missing)
        return server.State(cfg.token, image=cfg.image, runtime=cfg.runtime, missing=result.missing), None
    engine = Engine(cfg.socket)
    prestart = cfg.prestart if cfg.prestart is not None else min(config.PRESTART_DEFAULT, result.slots)
    pool = Pool(engine, cfg.image, cfg.runtime, result.profile, result.slots, prestart)
    removed = pool.start()
    events.started(result.slots, pool.prestart, cfg.runtime, removed)
    return server.State(cfg.token, engine=engine, pool=pool, image=cfg.image, runtime=cfg.runtime), pool


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    cfg = config.from_env()
    if "--check" in args:
        result = preflight.run(cfg)
        if result.ok:
            events.emit("checked", slots=result.slots, runtime=cfg.runtime, engine="dedicated")
            return 0
        events.refused(result.missing)
        return REFUSED_EXIT
    import uvicorn

    state, pool = build(cfg)
    try:
        uvicorn.run(server.create_app(state), host=cfg.bind, port=cfg.port, log_level="warning", access_log=False,
                    lifespan="off")
    finally:
        if pool is not None:
            pool.stop()
            events.emit("stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
