"""``python -m launcher.canary`` (ROUNDS-00A-L05): one known job through the
launcher, for operators.

Run it from a runner container, which holds ``ROUNDS_LAUNCHER_URL`` and
``ROUNDS_LAUNCHER_TOKEN``. It sends a job whose one part prints a fixed line
and prints one summary line: the outcome, dispatch to first byte, whether a
pre-started worker took it, and the cleanup. Exit status 0 means the worker
ran the job, said what it should, and is confirmed destroyed.
"""
from __future__ import annotations

import json
import secrets
import sys

from execution import launcher_client
from worker import manifest

EXPECTED = b"rounds launcher canary\n"


def main() -> int:
    try:
        client = launcher_client.LauncherClient.from_env()
        archive = manifest.build(
            parts=[{"id": "canary", "argv": ["python3", "-c", "print('rounds launcher canary')"], "wall_ms": 3000,
                    "result": None, "channel": False}],
            src={},
        )
        result = client.submit(job_id="canary-" + secrets.token_hex(8), kind="run", definition=None,
                               deadline_ms=3000, archive=archive)
    except (launcher_client.LauncherUnavailable, launcher_client.LauncherLost) as err:
        print(json.dumps({"canary": "unavailable", "reason": str(err)}))
        return 1
    observation = result.observation
    cleanup = client.cleanup(observation["job_id"]) if observation.get("cleanup") == "pending" else observation["cleanup"]
    ok = (launcher_client.classify(observation) is None and result.parts and result.parts[0].out == EXPECTED
          and cleanup == "confirmed")
    print(json.dumps({
        "canary": "ok" if ok else "failed", "first_byte_ms": observation.get("first_byte_ms"),
        "prestarted": observation.get("prestarted"), "cleanup": cleanup, "kill_reason": observation.get("kill_reason"),
    }))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
