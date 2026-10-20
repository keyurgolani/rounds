"""Grades checkpoint 0 of hallucinated-http-client in TypeScript: the
candidate's fetchUser against the real users service in ``users_api``,
through ``probe.ts`` as a tsx child. Node can't drop its own dumpable flag,
so this Python driver holds the result channel."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import users_api  # noqa: E402

if __name__ == "__main__":
    users_api.check(["tsx", os.path.join(HERE, "probe.ts")])
