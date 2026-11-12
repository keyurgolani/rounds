"""The admission and gate checks in harness/verify_deployment.py
(ROUNDS-00A-L01 stage 4).

Each check runs against a local fake that answers like the deployed
admission chain, then like a deployment that drifted, so every check is
shown to pass on the real shape and fail on the wrong one. The route table,
caps, and gate values are held in step with the runner and nginx, and the
runner's own startup line and denials are fed through the checks in
process. No test reaches a real host.
"""
from __future__ import annotations

import contextlib
import functools
import json
import re
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness"))

import verify_deployment as vd  # noqa: E402

CID = "0123456789abcdef0123456789abcdef"
# ingress-nginx's own answer to a declared length over its proxy-body-size:
# a plain page, no envelope, no correlation id.
PROXY_413 = (
    413,
    b"<html>\r\n<head><title>413 Request Entity Too Large</title></head>\r\n<body>\r\n"
    b"<center><h1>413 Request Entity Too Large</h1></center>\r\n<hr><center>nginx</center>\r\n"
    b"</body>\r\n</html>\r\n",
    {"Content-Type": "text/html"},
)


def envelope(code: str, detail: str = "A fixed sentence.") -> dict:
    return {"detail": detail, "code": code, "correlation_id": CID}


def runner_definition_routes() -> set[str]:
    """The routes ROUNDS_GATE_EXECUTION_DEFINITIONS=disabled stops, from the
    runner's own table."""
    from app import admission

    return {path for (_m, path), route in admission.ROUTES.items()
            if route.operation in admission.DEFINITION_OPERATIONS}


def runner_scratch_routes() -> set[str]:
    """The routes ROUNDS_GATE_EXECUTION_SCRATCH off stops, from the
    runner's own table (ROUNDS-00A-L03 PR 2)."""
    from app import admission
    from execution import keys

    return {path for (_m, path), route in admission.ROUTES.items() if route.operation in keys.SCRATCH_OPERATIONS}


def runner_grading_routes() -> set[str]:
    """The routes ROUNDS_GATE_EXECUTION_GRADING off stops, from the
    runner's own table (ROUNDS-00A-L03 PR 3)."""
    from app import admission
    from execution import keys

    return {path for (_m, path), route in admission.ROUTES.items() if route.operation in keys.GRADING_OPERATIONS}


def ingress_body_cap() -> int:
    """proxy-body-size on the repository's Kubernetes ingress."""
    text = (ROOT / "k8s" / "ingress.yaml").read_text()
    size = re.search(r'proxy-body-size:\s*"(\d+)([km])"', text)
    return int(size.group(1)) * {"k": 1024, "m": 1024 * 1024}[size.group(2)]


class Admission:
    """What the fake answers. Defaults to a deployment whose every admitted
    route is enabled and whose caps match the table."""

    def __init__(self) -> None:
        self.disabled: set[str] = set()
        # ROUNDS_GATE_EXECUTION_DEFINITIONS=disabled.
        self.definitions_off = False
        # ROUNDS_GATE_EXECUTION_SCRATCH off, or on without what it needs.
        self.scratch_off = False
        # ROUNDS_GATE_EXECUTION_GRADING off (ROUNDS-00A-L03 PR 3).
        self.grading_off = False
        self.overrides: dict[str, tuple[int, object, dict]] = {}
        self.caps = {path: edge for _m, path, _g, _r, edge in vd.ADMITTED_ROUTES}
        self.buffering = False
        self.cap_answer = (413, envelope("payload_too_large"), {"X-Correlation-Id": CID})
        # A proxy in front that refuses a declared length over this with
        # its own page, before the frontend sees the request.
        self.proxy_cap: int | None = None

    def answer(self, path: str, bearer: str) -> tuple[int, object, dict]:
        if path in self.overrides:
            return self.overrides[path]
        # The runner's order: the route's gate, then the definitions stop,
        # then the account.
        if path in self.disabled:
            return 503, envelope("route_disabled"), {"X-Correlation-Id": CID}
        if self.definitions_off and path in runner_definition_routes():
            return 503, envelope("definitions_disabled"), {"X-Correlation-Id": CID}
        if self.scratch_off and path in runner_scratch_routes():
            return 503, envelope("execution_disabled"), {"X-Correlation-Id": CID}
        if self.grading_off and path in runner_grading_routes():
            return 503, envelope("execution_disabled"), {"X-Correlation-Id": CID}
        return 401, envelope("unauthenticated"), {"X-Correlation-Id": CID}


@contextlib.contextmanager
def fake(dep: Admission):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, status, payload, headers):
            raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            self.send_response(status)
            headers = {"Content-Type": "application/json", **headers}
            for name, value in headers.items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _handle(self):
            length = int(self.headers.get("Content-Length") or 0)
            if dep.proxy_cap is not None and length > dep.proxy_cap:
                self._send(*PROXY_413)
                self.close_connection = True
                return
            # A review route's path fills its {job} segment.
            path = vd.template_of(self.path)
            cap = dep.caps.get(path)
            if cap is not None and length > cap:
                if dep.buffering:
                    time.sleep(3)
                    self.close_connection = True
                    return
                # Decided on the header alone, like nginx and the runner.
                self._send(*dep.cap_answer)
                self.close_connection = True
                return
            if length:
                self.rfile.read(length)
            self._send(*dep.answer(path, self.headers.get("Authorization", "")))

        do_GET = do_POST = _handle

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown()
        srv.server_close()


def failed(results):
    return [f"{r.check_id} {r.target}: {r.detail}" for r in results if not r.passed]


# ---- the table stays in step with the runner and nginx --------------------------


def test_the_admitted_route_table_matches_the_runner():
    from app import admission

    runner = {(m, p): (route.gate, route.max_body) for (m, p), route in admission.ROUTES.items()}
    table = {(m, p): (gate, cap) for m, p, gate, cap, _edge in vd.ADMITTED_ROUTES}
    assert table == runner


def _nginx_caps() -> dict[str, int]:
    text = (ROOT / "frontend" / "nginx.conf").read_text()
    units = {"k": 1024, "m": 1024 * 1024}

    def cap_in(block: str) -> int:
        size = re.search(r"client_max_body_size\s+(\d+)([km])", block)
        return int(size.group(1)) * units[size.group(2)]

    exact = {m.group(1): cap_in(m.group(2)) for m in re.finditer(r"location = (/api/[a-z/-]+) \{(.*?)\}", text, re.S)}
    group = re.search(r"location ~ \^/api/\(([^)]*)\)\(/\|\$\) \{(.*?)\}", text, re.S)
    prefixes = group.group(1).split("|")
    caps = {}
    for _m, path, _g, _r, _e in vd.ADMITTED_ROUTES:
        if path in exact:
            caps[path] = exact[path]
        elif path.split("/")[2] in prefixes:
            caps[path] = cap_in(group.group(2))
    return caps


def test_the_edge_caps_match_nginx():
    assert _nginx_caps() == {path: edge for _m, path, _g, _r, edge in vd.ADMITTED_ROUTES}


def test_the_gate_values_match_the_registry():
    from app import gates

    by_name = {g.name: g for g in gates.REGISTRY}
    for _m, _p, gate, _r, _e in vd.ADMITTED_ROUTES:
        assert gates.RUNNER in by_name[gate].readers
        assert tuple(by_name[gate].values) == vd.ROUTE_GATE_VALUES
    for name, values in vd.ENFORCEMENT_GATES.items():
        assert tuple(by_name[name].values) == values


# ---- anonymous refusals and the error shape -------------------------------------


def test_a_deployment_that_admits_correctly_passes():
    with fake(Admission()) as url:
        results = vd.check_admitted_routes(url)
    assert failed(results) == []
    assert len(results) == 2 * len(vd.ADMITTED_ROUTES)


def test_a_route_the_operator_turned_off_passes_when_named():
    dep = Admission()
    dep.disabled.add("/api/run")
    with fake(dep) as url:
        results = vd.check_admitted_routes(url, disabled=["/api/run"])
    assert failed(results) == []
    denied = {r.target: r.expected_status for r in results if r.check_id == "deployment.admission.anonymous.denied"}
    assert denied["/api/run"] == 503 and denied["/api/evaluate"] == 401


def test_the_routes_that_ship_off_are_the_registrys():
    from app import admission, gates

    defaults = {g.name: g.default for g in gates.REGISTRY}
    shipped_off = {path for (_m, path), route in admission.ROUTES.items() if defaults[route.gate] == "disabled"}
    assert shipped_off == vd.SHIPS_OFF


@pytest.mark.parametrize("answer, passes", [
    ((503, envelope("route_disabled"), {"X-Correlation-Id": CID}), True),
    ((401, envelope("unauthenticated"), {"X-Correlation-Id": CID}), True),
    ((503, envelope("definitions_disabled"), {"X-Correlation-Id": CID}), False),
    ((503, envelope("materializer_unavailable"), {"X-Correlation-Id": CID}), False),
    ((201, {"status": "created"}, {}), False),
], ids=["shipped-off", "turned-on", "other-stop", "other-503", "ran-it"])
def test_a_route_that_ships_off_passes_off_or_on_until_it_is_named(answer, passes):
    (path,) = vd.SHIPS_OFF
    dep = Admission()
    dep.overrides[path] = answer
    with fake(dep) as url:
        results = vd.check_admitted_routes(url)
    bad = [r for r in results if not r.passed and r.check_id == "deployment.admission.anonymous.denied"]
    assert [r.target for r in bad] == ([] if passes else [path])


def test_a_route_that_ships_off_and_is_named_off_has_to_be_off():
    (path,) = vd.SHIPS_OFF
    with fake(Admission()) as url:
        results = vd.check_admitted_routes(url, disabled=[path])
    bad = [r for r in results if not r.passed]
    assert [(r.check_id, r.target) for r in bad] == [("deployment.admission.anonymous.denied", path)]


def test_a_route_left_off_fails_until_it_is_named():
    dep = Admission()
    dep.disabled.add("/api/run")
    with fake(dep) as url:
        results = vd.check_admitted_routes(url)
    bad = [r for r in results if not r.passed]
    assert [(r.check_id, r.target) for r in bad] == [("deployment.admission.anonymous.denied", "/api/run")]
    assert "--expect-disabled /api/run" in bad[0].detail


def test_a_route_named_off_that_still_admits_fails():
    with fake(Admission()) as url:
        results = vd.check_admitted_routes(url, disabled=["/api/run"])
    bad = [r for r in results if not r.passed]
    assert [(r.check_id, r.target) for r in bad] == [("deployment.admission.anonymous.denied", "/api/run")]
    assert "status=401" in bad[0].detail


@pytest.mark.parametrize(
    "answer, check",
    [
        ((200, {"stdout": "", "stderr": ""}, {}), "deployment.admission.anonymous.denied"),
        ((401, {"detail": "Sign in to continue."}, {"X-Correlation-Id": CID}), "deployment.admission.error-shape.safe"),
        ((401, envelope("unauthenticated"), {}), "deployment.admission.error-shape.safe"),
        ((401, {**envelope("unauthenticated"), "trace": "x"}, {"X-Correlation-Id": CID}),
         "deployment.admission.error-shape.safe"),
        ((401, {**envelope("unauthenticated"), "correlation_id": "abc"}, {"X-Correlation-Id": "abc"}),
         "deployment.admission.error-shape.safe"),
        ((500, b"<html>Internal Server Error</html>", {}), "deployment.admission.anonymous.denied"),
    ],
    ids=["ran-it", "no-code", "no-header", "extra-key", "short-id", "html-500"],
)
def test_a_route_that_answers_wrong_fails(answer, check):
    dep = Admission()
    dep.overrides["/api/ai-coding/grade"] = answer
    with fake(dep) as url:
        results = vd.check_admitted_routes(url)
    bad = [r for r in results if not r.passed]
    assert {(r.check_id, r.target) for r in bad} >= {(check, "/api/ai-coding/grade")}
    assert all(r.target == "/api/ai-coding/grade" for r in bad)


# ---- body caps -----------------------------------------------------------------


def test_every_post_route_refuses_a_declared_oversize_body():
    with fake(Admission()) as url:
        results = vd.check_admission_body_caps(url)
    assert failed(results) == []
    assert len(results) == sum(1 for r in vd.ADMITTED_ROUTES if r[0] == "POST")


def test_the_runner_caps_are_checked_straight_at_a_replica():
    dep = Admission()
    dep.caps = {path: runner for _m, path, _g, runner, _e in vd.ADMITTED_ROUTES}
    with fake(dep) as url:
        results = vd.check_admission_body_caps(url, at_runner=True)
    assert failed(results) == []
    # Declared one byte over the runner's own cap, not nginx's.
    assert {r.target for r in results} >= {"/api/pdf/render (2097153 bytes declared)",
                                          "/api/ai/ats-rule (1048577 bytes declared)"}


def test_a_cap_answered_by_the_wrong_hop_fails():
    dep = Admission()
    dep.cap_answer = (400, {"code": 400, "message": "Failed to parse.", "data": {}}, {})
    with fake(dep) as url:
        results = vd.check_admission_body_caps(url)
    assert results and all(not r.passed and not r.inconclusive for r in results)


def test_a_buffering_proxy_makes_the_cap_check_inconclusive():
    dep = Admission()
    dep.buffering = True
    with fake(dep) as url:
        results = vd.check_admission_body_caps(url, timeout=1.0)
    assert results and all(r.inconclusive for r in results)


def test_a_capped_proxy_in_front_makes_the_caps_over_its_own_inconclusive():
    # A proxy that refuses a declared length over its own cap with its own
    # page hides the frontend's cap for those routes; the rest still reach
    # nginx, which refuses them typed.
    dep = Admission()
    dep.proxy_cap = ingress_body_cap()
    with fake(dep) as url:
        results = vd.check_admission_body_caps(url)
    assert [r.target for r in results if not r.passed and not r.inconclusive] == []
    over = {path for method, path, _g, _r, edge in vd.ADMITTED_ROUTES if method == "POST" and edge + 1 > dep.proxy_cap}
    hidden = [r for r in results if r.inconclusive]
    # Seven 6 MiB routes, and the two review routes from ROUNDS-00A-L03 PR 3.
    assert {r.target.split(" ")[0] for r in hidden} == over and len(over) == 9
    assert all(r.detail.startswith("inconclusive (capped proxy in front)") for r in hidden)
    assert {r.target.split(" ")[0] for r in results if r.passed} == {"/api/run", "/api/evaluate"}


def test_admission_passes_behind_the_kubernetes_ingress(monkeypatch, capsys):
    # The repository's ingress: request buffering on, and its own 413 page
    # over proxy-body-size. Every cap is inconclusive, none fails, and the
    # run exits 0. The proxy checks have their own tests.
    dep = Admission()
    dep.proxy_cap = ingress_body_cap()
    dep.buffering = True
    monkeypatch.setattr(vd, "check_proxy", lambda _url: [])
    monkeypatch.setattr(vd, "check_admission_body_caps",
                        functools.partial(vd.check_admission_body_caps, timeout=1.0))
    with fake(dep) as url:
        assert vd.main(["--url", url, "--admission"], env={}) == 0
    out = capsys.readouterr().out
    posts = sum(1 for r in vd.ADMITTED_ROUTES if r[0] == "POST")
    assert out.count("INCONCLUSIVE deployment.admission.body-cap.rejected") == posts
    assert f"0 failed, {posts} inconclusive" in out


@pytest.mark.parametrize(
    "answer",
    [
        (413, {"code": 413, "message": "Request entity too large.", "data": {}}, {}),
        (413, {"detail": "Request body too large"}, {}),
        (413, envelope("payload_too_large"), {}),
        (413, envelope("invalid_request"), {"X-Correlation-Id": CID}),
    ],
    ids=["pocketbase", "untyped-runner", "no-header", "wrong-code"],
)
def test_a_413_in_this_stacks_shapes_but_wrong_still_fails(answer):
    dep = Admission()
    dep.cap_answer = answer
    with fake(dep) as url:
        results = vd.check_admission_body_caps(url)
    assert results and all(not r.passed and not r.inconclusive for r in results)


# ---- an emergency disable ------------------------------------------------------


def test_a_disabled_route_answers_route_disabled_for_every_caller():
    dep = Admission()
    dep.disabled.add("/api/run")
    with fake(dep) as url:
        (result,) = vd.check_disabled_routes(url, ["/api/run"])
    assert result.passed, result.detail


def test_a_route_still_on_fails_the_disabled_check():
    with fake(Admission()) as url:
        (result,) = vd.check_disabled_routes(url, ["/api/run"])
    assert not result.passed and "status=401" in result.detail


def test_only_an_admitted_route_can_be_expected_off():
    with pytest.raises(vd.ConfigError):
        vd.check_disabled_routes("http://127.0.0.1:9", ["/api/share/by-token/x"])


def test_the_definitions_stop_passes_when_each_route_is_named_with_it():
    dep = Admission()
    dep.definitions_off = True
    named = [f"{path}=definitions_disabled" for path in sorted(runner_definition_routes())]
    with fake(dep) as url:
        results = vd.check_admitted_routes(url, disabled=named) + vd.check_disabled_routes(url, named)
    assert failed(results) == []
    denied = {r.target: r.expected_status for r in results if r.check_id == "deployment.admission.anonymous.denied"}
    assert {path for path, status in denied.items() if status == 503} == runner_definition_routes()


def test_the_definitions_stop_fails_until_it_is_named_with_its_code():
    dep = Admission()
    dep.definitions_off = True
    with fake(dep) as url:
        unnamed = vd.check_admitted_routes(url)
        (as_route_gate,) = vd.check_disabled_routes(url, ["/api/run"])
    bad = [r for r in unnamed if not r.passed]
    assert {r.target for r in bad} == runner_definition_routes()
    assert {r.check_id for r in bad} == {"deployment.admission.anonymous.denied"}
    run = next(r for r in bad if r.target == "/api/run")
    assert "--expect-disabled /api/run=definitions_disabled" in run.detail
    assert not as_route_gate.passed and "code='definitions_disabled'" in as_route_gate.detail


def test_a_route_gate_named_as_the_definitions_stop_fails():
    dep = Admission()
    dep.disabled.add("/api/run")
    with fake(dep) as url:
        results = vd.check_admitted_routes(url, disabled=["/api/run=definitions_disabled"])
        (result,) = vd.check_disabled_routes(url, ["/api/run=definitions_disabled"])
    bad = [r for r in results if not r.passed]
    assert [r.target for r in bad] == ["/api/run"] and "give --expect-disabled /api/run if" in bad[0].detail
    assert not result.passed and "code='route_disabled'" in result.detail


def test_the_scratch_stop_passes_when_each_scratch_route_is_named_with_it():
    dep = Admission()
    dep.scratch_off = True
    named = [f"{path}=execution_disabled" for path in sorted(runner_scratch_routes())]
    with fake(dep) as url:
        results = vd.check_admitted_routes(url, disabled=named) + vd.check_disabled_routes(url, named)
        unnamed = vd.check_admitted_routes(url)
    assert failed(results) == []
    bad = [r for r in unnamed if not r.passed]
    assert {r.target for r in bad} == runner_scratch_routes()
    run = next(r for r in bad if r.target == "/api/run")
    assert "--expect-disabled /api/run=execution_disabled" in run.detail
    assert "ROUNDS_GATE_EXECUTION_SCRATCH" in run.detail


def test_expected_stops_parse_to_a_code_per_route():
    assert vd.parse_expected_disabled(["/api/run"]) == {"/api/run": "route_disabled"}
    assert vd.parse_expected_disabled(["/api/run=Definitions_Disabled", "/api/pdf/render=route_disabled"]) == {
        "/api/run": "definitions_disabled", "/api/pdf/render": "route_disabled"}


@pytest.mark.parametrize(
    "items",
    # From ROUNDS-00A-L03 PR 3 grade is stopped by the grading key, so the
    # route neither key stops is the PDF render.
    [["/api/pdf/render=definitions_disabled"], ["/api/pdf/render=execution_disabled"],
     ["/api/run=unauthenticated"], ["/api/run="], ["/api/run", "/api/run=definitions_disabled"],
     ["/api/not-admitted=route_disabled"]],
    ids=["not-a-definition-route", "not-a-job-route", "not-a-stop", "empty-code", "two-codes", "not-admitted"],
)
def test_an_expected_stop_that_cant_happen_is_a_usage_error(items):
    with pytest.raises(vd.ConfigError):
        vd.parse_expected_disabled(items)


# ---- the gates line -----------------------------------------------------------


def gates_line(**overrides) -> str:
    table = {gate: {"value": "enabled", "source": "default"} for _m, _p, gate, _r, _e in vd.ADMITTED_ROUTES}
    table.update({"ENFORCE_IDEMPOTENCY": {"value": "observe", "source": "default"},
                  "ENFORCE_QUOTA": {"value": "observe", "source": "default"},
                  "PAPER_FETCH": {"value": "disabled", "source": "default"}})
    for name, entry in overrides.items():
        if entry is None:
            table.pop(name, None)
        else:
            table[name] = entry
    line = {"event": "gates", "gates": table, "service": "runner", "v": "obs/v1"}
    return "runner-1  | INFO:     Started server process [1]\n" \
           f"runner-1  | {json.dumps(line, separators=(',', ':'), sort_keys=True)}\n"


def test_a_clean_gates_line_passes():
    assert failed(vd.check_gates_log(gates_line())) == []


def test_the_last_gates_line_wins():
    text = gates_line(RUN={"value": "disabled", "source": "env"}) + gates_line()
    (logged, valid, expected) = vd.check_gates_log(text, {"RUN": "enabled"})
    assert logged.passed and valid.passed and expected.passed


@pytest.mark.parametrize(
    "overrides, check",
    [
        ({"RUN": None}, "deployment.gates.logged"),
        ({"ENFORCE_QUOTA": None}, "deployment.gates.logged"),
        ({"RUN": {"value": "disabled", "source": "invalid"}}, "deployment.gates.valid"),
        ({"ENFORCE_QUOTA": {"value": "sometimes", "source": "env"}}, "deployment.gates.valid"),
        ({"PDF_RENDER": {"value": "off", "source": "env"}}, "deployment.gates.valid"),
    ],
    ids=["route-gate-missing", "enforcement-gate-missing", "fell-back", "unknown-enforcement", "unknown-route-value"],
)
def test_a_wrong_gates_line_fails(overrides, check):
    results = {r.check_id: r for r in vd.check_gates_log(gates_line(**overrides))}
    assert not results[check].passed


@pytest.mark.parametrize(
    "overrides, needs",
    [
        ({"EXECUTION_STORE": {"value": "off", "source": "default"}}, "EXECUTION_STORE=on"),
        ({"EXECUTION_DEFINITIONS": {"value": "legacy", "source": "default"}}, "EXECUTION_DEFINITIONS=enforce"),
        ({"EXECUTION_STORE": None}, "EXECUTION_STORE=on"),
    ],
    ids=["store-off", "definitions-legacy", "store-not-logged"],
)
def test_scratch_on_without_what_it_needs_is_reported_as_acting_off(overrides, needs):
    on = {"EXECUTION_SCRATCH": {"value": "on", "source": "env"}, "EXECUTION_STORE": {"value": "on", "source": "env"},
          "EXECUTION_DEFINITIONS": {"value": "enforce", "source": "env"}}
    text = gates_line(**{**on, **overrides})
    results = {r.check_id: r for r in vd.check_gates_log(text, {"EXECUTION_SCRATCH": "on"})}
    for check in ("deployment.gates.valid", "deployment.gates.expected"):
        assert not results[check].passed
        assert "acts as if it were off" in results[check].detail and needs in results[check].detail
    assert results["deployment.gates.logged"].passed
    clean = {r.check_id: r for r in vd.check_gates_log(gates_line(**on), {"EXECUTION_SCRATCH": "on"})}
    assert all(r.passed for r in clean.values()), [r.detail for r in clean.values()]


@pytest.mark.parametrize("name, value", [("EXECUTION_SCRATCH", "yes"), ("EXECUTION_STORE", "enabled"),
                                         ("EXECUTION_DEFINITIONS", "on")])
def test_an_execution_key_outside_its_values_fails_the_valid_check(name, value):
    results = {r.check_id: r for r in vd.check_gates_log(gates_line(**{name: {"value": value, "source": "env"}}))}
    assert not results["deployment.gates.valid"].passed and name in results["deployment.gates.valid"].detail


def test_the_runners_own_scratch_line_passes_only_with_what_it_needs(capsys, monkeypatch):
    from app import gates

    for env, ok in (({"ROUNDS_GATE_EXECUTION_SCRATCH": "on", "ROUNDS_GATE_EXECUTION_STORE": "on",
                      "ROUNDS_GATE_EXECUTION_DEFINITIONS": "enforce"}, True),
                    ({"ROUNDS_GATE_EXECUTION_SCRATCH": "on", "ROUNDS_GATE_EXECUTION_STORE": "on"}, False)):
        monkeypatch.setattr(gates, "_snapshot", None)
        gates.init(env)
        results = vd.check_gates_log(capsys.readouterr().out, {"EXECUTION_SCRATCH": "on"})
        assert all(r.passed for r in results) is ok, [r.detail for r in results]
    monkeypatch.setattr(gates, "_snapshot", None)


def test_an_unexpected_value_fails_the_expected_check():
    results = {r.check_id: r for r in vd.check_gates_log(gates_line(), {"RUN": "disabled"})}
    assert results["deployment.gates.logged"].passed and not results["deployment.gates.expected"].passed
    assert "expected 'disabled'" in results["deployment.gates.expected"].detail


def test_a_log_without_a_gates_line_fails_both():
    results = {r.check_id: r for r in vd.check_gates_log("runner-1  | started\n", {"RUN": "enabled"})}
    assert not results["deployment.gates.logged"].passed
    assert not results["deployment.gates.valid"].passed
    assert not results["deployment.gates.expected"].passed


def test_the_runners_own_startup_line_passes(capsys, monkeypatch):
    from app import gates

    monkeypatch.setattr(gates, "_snapshot", None)
    gates.init({"ROUNDS_GATE_RUN": "disabled"})
    out = capsys.readouterr().out
    results = {r.check_id: r for r in vd.check_gates_log(out, {"RUN": "disabled"})}
    assert all(r.passed for r in results.values()), [r.detail for r in results.values()]
    monkeypatch.setattr(gates, "_snapshot", None)


def test_the_runbooks_definitions_stop_confirmation_passes(tmp_path, capsys, monkeypatch):
    # docs/security/execution-runbook.md, Compiled Definitions: the six
    # routes named with definitions_disabled, and the gate in the log.
    from app import gates

    monkeypatch.setattr(gates, "_snapshot", None)
    gates.init({"ROUNDS_GATE_EXECUTION_DEFINITIONS": "disabled"})
    log = tmp_path / "runner.log"
    log.write_text(capsys.readouterr().out)
    monkeypatch.setattr(gates, "_snapshot", None)
    dep = Admission()
    dep.definitions_off = True
    monkeypatch.setattr(vd, "check_proxy", lambda _url: [])
    named = [arg for path in sorted(vd.DEFINITION_ROUTES) for arg in ("--expect-disabled", f"{path}=definitions_disabled")]
    with fake(dep) as url:
        code = vd.main(["--url", url, "--admission", *named, "--gates-log", str(log),
                        "--expect-gate", "EXECUTION_DEFINITIONS=disabled"], env={})
    assert code == 0, capsys.readouterr().out


def test_expected_gates_take_either_spelling():
    assert vd.parse_expected_gates(["RUN=disabled", "ROUNDS_GATE_ENFORCE_QUOTA=Enforce"]) == {
        "RUN": "disabled", "ENFORCE_QUOTA": "enforce"}
    with pytest.raises(vd.ConfigError):
        vd.parse_expected_gates(["RUN"])


# ---- the runner's own denials pass the shape check ----------------------------


def _every_route_on(monkeypatch):
    from app import gates

    env = {f"{gates.PREFIX}{gate}": "enabled" for _m, _p, gate, _r, _e in vd.ADMITTED_ROUTES}
    # The review routes serve only while grading runs as jobs, which needs
    # the store on and definitions enforced (ROUNDS-00A-L03 PR 3).
    env.update({"ROUNDS_GATE_EXECUTION_GRADING": "on", "ROUNDS_GATE_EXECUTION_STORE": "on",
                "ROUNDS_GATE_EXECUTION_DEFINITIONS": "enforce"})
    monkeypatch.setattr(gates, "_snapshot", gates.load(env, gates.RUNNER))


@pytest.mark.parametrize("shipped", [True, False], ids=["as-shipped", "every-route-on"])
def test_the_runners_anonymous_denials_are_the_safe_shape(client, monkeypatch, shipped):
    from app import gates

    if shipped:
        monkeypatch.setattr(gates, "_snapshot", gates.load({}, gates.RUNNER))
    else:
        _every_route_on(monkeypatch)
    for method, path, _g, _r, _e in vd.ADMITTED_ROUTES:
        res = client.request(method, vd.concrete(path), json={} if method == "POST" else None)
        headers = {k.lower(): v for k, v in res.headers.items()}
        assert vd.envelope_problem(res.status_code, res.content, headers) == "", path
        # A route whose gate ships off answers its stop before the account,
        # and so does a review route while grading isn't on.
        want = "unauthenticated"
        if shipped and path in vd.SHIPS_OFF:
            want = "route_disabled"
        elif shipped and path in vd.SERVED_WHILE_GRADING:
            want = "execution_disabled"
        assert res.json()["code"] == want, path


def test_the_runners_field_refusals_repeat_none_of_the_request(client, signed_in, monkeypatch):
    # What the harness's no-echo check expects of each replica, here for
    # every POST route with its gate on: a field the route doesn't take is
    # the typed 422, and nothing sent comes back.
    _every_route_on(monkeypatch)
    marker = "s4echo0123456789ab"
    for method, path, _g, _r, _e in vd.ADMITTED_ROUTES:
        if method != "POST":
            continue
        res = client.post(vd.concrete(path), json={marker: marker, "code": f"# {marker}"}, headers=signed_in)
        headers = {k.lower(): v for k, v in res.headers.items()}
        assert res.status_code == 422 and res.json()["code"] == "invalid_request", path
        assert vd.envelope_problem(res.status_code, res.content, headers) == "", path
        assert marker not in res.text, path


def _in_process(client):
    """The verifier's request function, answered by the runner in process."""

    def req(method, url, *, body=None, token="", timeout=10.0):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        res = client.request(method, urllib.parse.urlsplit(url).path, json=body, headers=headers)
        return vd.Response(res.status_code, res.content, {k.lower(): v for k, v in res.headers.items()}, 0)

    return req


def test_the_stop_codes_and_definition_routes_match_the_runner():
    from app import errors, gates
    from execution import keys

    assert vd.DEFINITION_ROUTES == runner_definition_routes()
    assert vd.SCRATCH_ROUTES == runner_scratch_routes()
    assert vd.GRADING_ROUTES == runner_grading_routes()
    assert vd.SERVED_WHILE_GRADING == {p for (_m, p), r in admission_routes().items() if r.operation == "review"}
    assert set(vd.STOPPED_BY) == set(vd.STOP_CODES)
    assert all(errors.CODES[code] == 503 for code in vd.STOP_CODES)
    assert vd.SCRATCH_NEEDS == keys.SCRATCH_NEEDS and vd.GRADING_NEEDS == keys.GRADING_NEEDS
    for name, values in vd.EXECUTION_GATES.items():
        assert tuple(gates.BY_NAME[name].values) == values


def admission_routes():
    from app import admission

    return admission.ROUTES


def test_a_review_routes_request_fills_its_job_id_and_names_its_template():
    for path in vd.SERVED_WHILE_GRADING:
        sent = vd.concrete(path)
        assert "{" not in sent and vd.template_of(sent) == path
        assert vd.template_of(sent + "/x") == sent + "/x"
    assert vd.template_of("/api/run") == "/api/run"


def test_the_runners_grading_stop_is_the_one_the_verifier_expects(client, monkeypatch):
    from app import gates

    for env in ({"ROUNDS_GATE_EXECUTION_GRADING": "off"}, {"ROUNDS_GATE_EXECUTION_GRADING": "on"}):
        monkeypatch.setattr(gates, "_snapshot", gates.load(env, gates.RUNNER))
        req = _in_process(client)
        named = [f"{path}=execution_disabled" for path in sorted(vd.GRADING_ROUTES)]
        results = vd.check_admitted_routes("http://runner", req, disabled=named)
        results += vd.check_disabled_routes("http://runner", named, req)
        assert failed(results) == []


def test_a_review_route_passes_off_or_on_until_it_is_named():
    dep = Admission()
    dep.grading_off = True
    with fake(dep) as url:
        results = vd.check_admitted_routes(url)
    bad = [r.target for r in results if not r.passed]
    # Grade and submit are left off unnamed; the review routes may be off.
    assert len(bad) == 2 and set(bad) == {"/api/take-home/submit", "/api/ai-coding/grade"}
    with fake(dep) as url:
        named = [f"{p}=execution_disabled" for p in sorted(vd.GRADING_ROUTES)]
        assert failed(vd.check_admitted_routes(url, disabled=named) + vd.check_disabled_routes(url, named)) == []


@pytest.mark.parametrize("missing", ["EXECUTION_STORE", "EXECUTION_DEFINITIONS"])
def test_a_gates_log_with_grading_on_without_what_it_needs_fails_and_says_why(missing):
    table = {gate: {"value": "enabled", "source": "default"} for _m, _p, gate, _r, _e in vd.ADMITTED_ROUTES}
    table.update({name: {"value": "observe", "source": "default"} for name in vd.ENFORCEMENT_GATES})
    table.update({"EXECUTION_STORE": {"value": "on", "source": "env"},
                  "EXECUTION_DEFINITIONS": {"value": "enforce", "source": "env"},
                  "EXECUTION_GRADING": {"value": "on", "source": "env"}})
    table[missing] = {"value": {"EXECUTION_STORE": "off", "EXECUTION_DEFINITIONS": "legacy"}[missing],
                      "source": "default"}
    log = json.dumps({"v": "obs/v1", "event": "gates", "service": "runner", "gates": table})
    results = vd.check_gates_log(log, {"EXECUTION_GRADING": "on"})
    bad = {r.check_id: r.detail for r in results if not r.passed}
    want = "EXECUTION_STORE=on" if missing == "EXECUTION_STORE" else "EXECUTION_DEFINITIONS=enforce"
    assert set(bad) == {"deployment.gates.valid", "deployment.gates.expected"}
    assert all("EXECUTION_GRADING is on" in why and want in why for why in bad.values())


def test_the_runners_scratch_stop_is_the_one_the_verifier_expects(client, monkeypatch):
    from app import gates

    for env in ({"ROUNDS_GATE_EXECUTION_SCRATCH": "off"}, {"ROUNDS_GATE_EXECUTION_SCRATCH": "on"}):
        monkeypatch.setattr(gates, "_snapshot", gates.load(env, gates.RUNNER))
        req = _in_process(client)
        named = [f"{path}=execution_disabled" for path in sorted(vd.SCRATCH_ROUTES)]
        results = vd.check_admitted_routes("http://runner", req, disabled=named)
        results += vd.check_disabled_routes("http://runner", named, req)
        assert failed(results) == []


def test_the_runners_definitions_stop_is_the_one_the_verifier_expects(client, monkeypatch):
    from app import gates

    monkeypatch.setattr(gates, "_snapshot", gates.load({"ROUNDS_GATE_EXECUTION_DEFINITIONS": "disabled"}, gates.RUNNER))
    req = _in_process(client)
    named = [f"{path}=definitions_disabled" for path in sorted(vd.DEFINITION_ROUTES)]
    results = vd.check_admitted_routes("http://runner", req, disabled=named)
    results += vd.check_disabled_routes("http://runner", named, req)
    assert failed(results) == []
    unnamed = vd.check_admitted_routes("http://runner", req)
    assert {r.target for r in unnamed if not r.passed} == vd.DEFINITION_ROUTES


def test_the_runners_byte_cap_comes_before_the_account(client):
    res = client.post("/api/run", content=b"x" * (512 * 1024 + 1), headers={"Content-Type": "application/json"})
    headers = {k.lower(): v for k, v in res.headers.items()}
    assert res.status_code == 413 and res.json()["code"] == "payload_too_large"
    assert vd.envelope_problem(res.status_code, res.content, headers) == ""


# ---- the command line ----------------------------------------------------------


@pytest.mark.parametrize(
    "argv",
    [["--admission"], ["--expect-disabled", "/api/run"], ["--url", "http://127.0.0.1:9", "--expect-gate", "RUN=x"],
     ["--url", "http://127.0.0.1:9", "--expect-disabled", "/api/not-admitted"],
     ["--url", "http://127.0.0.1:9", "--expect-disabled", "/api/pdf/render=definitions_disabled"]],
    ids=["admission-needs-url", "disabled-needs-url", "expect-needs-log", "not-admitted", "no-such-stop"],
)
def test_misuse_is_a_usage_error(argv):
    assert vd.main(argv, env={}) == 2


def test_the_gates_log_alone_runs_and_fails_on_a_mismatch(tmp_path, capsys):
    log = tmp_path / "runner.log"
    log.write_text(gates_line())
    assert vd.main(["--gates-log", str(log)], env={}) == 0
    assert vd.main(["--gates-log", str(log), "--expect-gate", "RUN=disabled"], env={}) == 1
    out = capsys.readouterr().out
    assert "FAIL deployment.gates.expected" in out


def test_every_admission_check_id_is_registered():
    with fake(Admission()) as url:
        seen = {r.check_id for r in vd.check_admitted_routes(url) + vd.check_admission_body_caps(url)}
    dep = Admission()
    dep.disabled.add("/api/run")
    with fake(dep) as url:
        seen |= {r.check_id for r in vd.check_disabled_routes(url, ["/api/run"])}
    seen |= {r.check_id for r in vd.check_gates_log(gates_line(), {"RUN": "enabled"})}
    assert seen == set(vd.ADMISSION_CHECKS)


# ---- the demo account's code runs (ROUNDS-00B-L07) ------------------------------

DEMO_TOKEN = "demo-session-token-placeholder"
DEMO_REFUSED = (503, envelope("demo_execution_disabled", "Code runs are off in the demo."), {"X-Correlation-Id": CID})


def _demo_deployment(run, sign_in=200):
    """The verifier's request function for the two answers --demo reads:
    the demo account's sign-in, then its code run. ``run`` is (status,
    body, headers); ``sign_in`` is the sign-in's status. Records each
    request as (method, path, bearer)."""
    seen: list[tuple[str, str, str]] = []

    def req(method, url, *, body=None, token="", timeout=10.0):
        path = urllib.parse.urlsplit(url).path
        seen.append((method, path, token))
        if path == vd.USER_SIGN_IN:
            if sign_in == 200:
                doc = {"token": DEMO_TOKEN, "record": {"id": "demo00000000001"}}
            else:
                doc = {"code": sign_in, "message": "Failed to authenticate.", "data": {}}
            return vd.Response(sign_in, json.dumps(doc).encode(), {}, 0)
        status, doc, headers = run
        raw = doc if isinstance(doc, bytes) else json.dumps(doc).encode()
        return vd.Response(status, raw, {k.lower(): v for k, v in headers.items()}, 0, "" if status else "URLError")

    return req, seen


def test_the_demo_check_passes_only_on_the_typed_refusal_after_one_demo_sign_in():
    req, seen = _demo_deployment(DEMO_REFUSED)
    result = vd.check_demo_code_runs("http://deploy.test/", req)
    assert result.passed and result.detail == "" and result.check_id in vd.DEMO_CHECKS
    assert (result.expected_status, result.observed_status, result.target) == (503, 503, vd.DEMO_CODE_RUN)
    assert seen == [("POST", vd.USER_SIGN_IN, ""), ("POST", vd.DEMO_CODE_RUN, DEMO_TOKEN)]


def test_the_demo_check_fails_where_the_demos_code_runs_are_open():
    req, _seen = _demo_deployment((422, envelope("invalid_request"), {"X-Correlation-Id": CID}))
    result = vd.check_demo_code_runs("http://deploy.test", req)
    assert not result.passed and result.observed_status == 422
    assert "ROUNDS_GATE_DEMO_EXECUTION is enabled" in result.detail


@pytest.mark.parametrize(
    "answer, says",
    [
        ((503, envelope("route_disabled"), {"X-Correlation-Id": CID}), "its gate is off"),
        ((503, envelope("execution_disabled"), {"X-Correlation-Id": CID}), "ROUNDS_GATE_EXECUTION_SCRATCH"),
        ((503, envelope("worker_unavailable"), {"X-Correlation-Id": CID}), "code='worker_unavailable'"),
        ((503, envelope("demo_execution_disabled"), {}), "X-Correlation-Id header doesn't match"),
        ((503, {"detail": "Service Unavailable"}, {}), "keys differ"),
        ((503, b"<html>bad gateway</html>", {}), "answered_by=proxy"),
        ((*DEMO_REFUSED[:2], {"X-Correlation-Id": CID, "Retry-After": "300"}), "retry-after"),
        ((*DEMO_REFUSED[:2], {"X-Correlation-Id": CID, "Idempotent-Replayed": "true"}), "idempotent-replayed"),
        ((200, {"stdout": "", "stderr": "", "error": None}, {}), "status=200"),
        ((0, b"", {}), "no response"),
    ],
    ids=["route-off", "scratch-off", "busy", "no-correlation-header", "untyped", "proxy-page", "counted",
         "replayed", "ran", "unreachable"],
)
def test_any_other_answer_to_the_demos_code_run_fails_and_says_what_came_back(answer, says):
    req, _seen = _demo_deployment(answer)
    result = vd.check_demo_code_runs("http://deploy.test", req)
    assert not result.passed and not result.inconclusive
    assert says in result.detail


@pytest.mark.parametrize("status", [400, 401, 0], ids=["refused", "runner-shaped", "unreachable"])
def test_a_demo_sign_in_the_deployment_refuses_fails_and_sends_no_code_run(status):
    req, seen = _demo_deployment(DEMO_REFUSED, sign_in=status)
    result = vd.check_demo_code_runs("http://deploy.test", req)
    assert not result.passed and result.observed_status == status
    assert "didn't sign in" in result.detail
    assert [path for _m, path, _t in seen] == [vd.USER_SIGN_IN]


def test_the_demo_check_reports_no_login_or_token():
    for answer in (DEMO_REFUSED, (422, envelope("invalid_request"), {"X-Correlation-Id": CID})):
        req, _seen = _demo_deployment(answer)
        result = vd.check_demo_code_runs("http://deploy.test", req)
        for value in (*vd.DEMO_LOGIN, DEMO_TOKEN):
            assert value not in result.detail


def test_the_demo_refusal_and_its_route_are_the_runners_and_the_login_is_the_shipped_one():
    from app import admission, errors

    assert errors.CODES[vd.DEMO_REFUSAL] == 503
    assert admission.ROUTES[("POST", vd.DEMO_CODE_RUN)].operation in admission.DEFINITION_OPERATIONS
    assert ("the demo account", *vd.DEMO_LOGIN) in vd.DEFAULT_ADMIN_LOGINS
    seeded = (ROOT / "pocketbase" / "pb_migrations" / "1700000600_demo_user.js").read_text()
    assert f'DEMO_EMAIL = "{vd.DEMO_LOGIN[0]}"' in seeded and f'DEMO_PASSWORD = "{vd.DEMO_LOGIN[1]}"' in seeded


def _demo_in_process(client, monkeypatch):
    """The verifier's request function with the sign-in answered the way
    PocketBase answers the demo account's, and the code run answered by the
    runner in process, which takes the issued token as that demo account."""
    from app import admission
    from app.errors import TypedError

    async def authenticate(token):
        if token != DEMO_TOKEN:
            raise TypedError("unauthenticated")
        return {"id": "demo00000000001", "token": token, "record": {"id": "demo00000000001", "is_demo": True}}

    monkeypatch.setattr(admission, "authenticate", authenticate)
    runner = _in_process(client)

    def req(method, url, *, body=None, token="", timeout=10.0):
        if urllib.parse.urlsplit(url).path == vd.USER_SIGN_IN:
            return vd.Response(200, json.dumps({"token": DEMO_TOKEN, "record": {}}).encode(), {}, 0)
        return runner(method, url, body=body, token=token, timeout=timeout)

    return req


@pytest.fixture
def runs(monkeypatch):
    """Every code run the runner starts, recorded and refused."""
    from routers import runner as coding

    started: list[str] = []

    def run_one(*_args, **_kwargs):
        started.append("run_one")
        raise AssertionError("a code run started")

    monkeypatch.setattr(coding, "run_one", run_one)
    return started


def test_the_runners_demo_refusal_passes_the_demo_check_and_charges_nothing(client, monkeypatch, admission_store,
                                                                              runs):
    from app import gates

    monkeypatch.setattr(gates, "_snapshot", gates.load({}, gates.RUNNER))
    result = vd.check_demo_code_runs("http://runner", _demo_in_process(client, monkeypatch))
    assert result.passed, result.detail
    assert admission_store.calls == [] and runs == []


def test_where_the_demos_code_runs_are_open_the_check_fails_and_nothing_runs_or_is_charged(
    client, monkeypatch, admission_store, runs
):
    from app import gates

    env = {"ROUNDS_GATE_DEMO_EXECUTION": "enabled", "ROUNDS_GATE_ENFORCE_IDEMPOTENCY": "enforce",
           "ROUNDS_GATE_ENFORCE_QUOTA": "enforce"}
    monkeypatch.setattr(gates, "_snapshot", gates.load(env, gates.RUNNER))
    result = vd.check_demo_code_runs("http://runner", _demo_in_process(client, monkeypatch))
    assert not result.passed and result.observed_status == 422
    assert admission_store.calls == [] and runs == []


def test_the_command_line_runs_the_demo_check_only_with_demo(monkeypatch, capsys):
    dep = Admission()
    dep.overrides[vd.USER_SIGN_IN] = (200, {"token": DEMO_TOKEN, "record": {}}, {})
    dep.overrides[vd.DEMO_CODE_RUN] = DEMO_REFUSED
    monkeypatch.setattr(vd, "check_proxy", lambda _url: [])
    with fake(dep) as url:
        assert vd.main(["--url", url], env={}) == 0
        assert "deployment.demo" not in capsys.readouterr().out
        assert vd.main(["--url", url, "--demo"], env={}) == 0
        passed = capsys.readouterr().out
        dep.overrides[vd.DEMO_CODE_RUN] = (422, envelope("invalid_request"), {"X-Correlation-Id": CID})
        assert vd.main(["--url", url, "--demo"], env={}) == 1
        failed_out = capsys.readouterr().out
    assert "PASS deployment.demo.code-run.refused" in passed
    assert "FAIL deployment.demo.code-run.refused" in failed_out and "ROUNDS_GATE_DEMO_EXECUTION" in failed_out
    for value in (*vd.DEMO_LOGIN, DEMO_TOKEN):
        assert value not in passed and value not in failed_out


def test_the_demo_check_needs_the_url():
    assert vd.main(["--demo"], env={}) == 2
    assert vd.main(["--gates-log", "/nonexistent", "--demo"], env={}) == 2


def test_every_demo_check_id_is_registered():
    req, _seen = _demo_deployment(DEMO_REFUSED)
    assert {vd.check_demo_code_runs("http://deploy.test", req).check_id} == set(vd.DEMO_CHECKS)
    assert not set(vd.DEMO_CHECKS) & (set(vd.ADMISSION_CHECKS) | set(vd.CHECKS))
