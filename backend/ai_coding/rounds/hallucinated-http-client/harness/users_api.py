"""The real users service both languages' checkpoint 0 grades against.

``check`` serves GET /users/<id> on 127.0.0.1 with a name made up for this
run, runs the candidate's side of the check as a child with the server's
URL and a user id, and reports one result on fd 3. A client that still
calls the hallucinated method fails, and only one that really called the
server can know the name.
"""
import json
import os
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import rounds_harness

RESULT_ID = "fetch_user_against_real_server"
USER_ID = "u-42"
CHILD_TIMEOUT_S = 30


def check(child_argv):
    """Runs ``child_argv + [base_url, user_id]`` and reports the result."""
    rounds_harness.protect()
    channel = rounds_harness.Channel()
    name = "Real-" + secrets.token_hex(8)
    requested = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requested.append(self.path)
            if self.path.startswith("/users/"):
                body = json.dumps({"id": self.path[len("/users/"):], "name": name}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        child = rounds_harness.run_child(
            child_argv + [base_url, USER_ID], cwd=os.getcwd(), timeout_s=CHILD_TIMEOUT_S
        )
    finally:
        server.shutdown()
        server.server_close()

    if child.timed_out:
        channel.report(RESULT_ID, "failed", "timeout")
    elif child.returncode != 0:
        channel.report(RESULT_ID, "failed", "exception")
    else:
        answer = rounds_harness.last_json_line(child.stdout)
        if answer is None:
            channel.report(RESULT_ID, "failed", "no-result")
        elif answer == {"id": USER_ID, "name": name} and f"/users/{USER_ID}" in requested:
            channel.report(RESULT_ID, "passed", "ok")
        else:
            channel.report(RESULT_ID, "failed", "assertion")
