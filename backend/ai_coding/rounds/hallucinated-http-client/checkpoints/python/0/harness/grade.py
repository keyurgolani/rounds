"""Grades checkpoint 0 of hallucinated-http-client in Python: the
candidate's fetch_user against the real users service in ``users_api``,
through ``probe.py`` in a child process."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import users_api  # noqa: E402

if __name__ == "__main__":
    users_api.check([sys.executable, "-I", os.path.join(HERE, "probe.py")])
