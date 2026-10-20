"""The candidate's side of checkpoint 0's grade: point client.py at the
driver's server, call fetch_user, and print the result as one JSON line.
It runs as a child of grade.py, with the candidate's project root as its
working directory and no result channel."""
import json
import os
import sys

sys.path.insert(0, os.getcwd())

import client  # noqa: E402

client.INTERNAL_BASE_URL = sys.argv[1]
result = client.fetch_user(sys.argv[2])
sys.stdout.write("\n" + json.dumps(result) + "\n")
