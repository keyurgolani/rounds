"""Gate registry (ROUNDS-00A-L01): written defaults, resolution, the
startup log, and the three readers staying in step."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from app import gates

ROOT = Path(__file__).resolve().parents[2]
PB_MODULE = ROOT / "pocketbase" / "pb_hooks" / "gates.js"
SPA_REGISTRY = ROOT / "frontend" / "src" / "lib" / "gateRegistry.json"

RUNNER_GATES = [g for g in gates.REGISTRY if gates.RUNNER in g.readers]


@pytest.fixture(autouse=True)
def _restore_snapshot(monkeypatch):
    monkeypatch.setattr(gates, "_snapshot", None)


def _gates_lines(out: str) -> list[dict]:
    lines = [json.loads(line) for line in out.splitlines() if line.startswith("{")]
    return [line for line in lines if line.get("event") == "gates"]


# ---- registry shape ------------------------------------------------------


def test_every_gate_has_a_prefixed_name_and_a_valid_default_and_closed_value():
    names = [g.name for g in gates.REGISTRY]
    assert len(names) == len(set(names))
    for gate in gates.REGISTRY:
        assert gate.env == "ROUNDS_GATE_" + gate.name
        assert gate.default in gate.values
        assert gate.closed in gate.values
        assert gate.readers
        for alias in gate.aliases:
            assert alias.value in gate.values
            assert alias.reader in gate.readers


def test_the_registry_covers_each_admitted_route_and_the_switches():
    routes = {g.route for g in gates.REGISTRY if g.route}
    assert routes == {
        "/api/run",
        "/api/evaluate",
        "/api/ai-coding/run-project",
        "/api/ai-coding/grade",
        "/api/take-home/run",
        "/api/take-home/submit",
        "/api/pdf/render",
        "/api/pdf/health",
        "/api/ai/ats-rule",
    }
    assert {
        "PAPER_FETCH",
        "PROVIDER_PRIVATE_NETWORK",
        "ENFORCE_IDEMPOTENCY",
        "ENFORCE_QUOTA",
        "SIGNUPS",
    } <= set(gates.BY_NAME)


def test_written_defaults_keep_routes_on_and_outbound_reach_off():
    # Route gates keep each route serving and enforcement starts off.
    # The paper fetch and private provider addresses start disabled
    # (#1 stage 2).
    resolved = gates.load({}, gates.RUNNER)
    assert [n for n in resolved] == [g.name for g in RUNNER_GATES]
    for name, r in resolved.items():
        assert r.source == "default"
        if name.startswith("ENFORCE_"):
            expected = "off"
        elif name in ("PAPER_FETCH", "PROVIDER_PRIVATE_NETWORK"):
            expected = "disabled"
        else:
            expected = "enabled"
        assert r.value == expected, name
    assert gates.load({}, gates.POCKETBASE)["SIGNUPS"] == gates.Resolved("enabled", "default")
    assert gates.load({}, gates.FRONTEND)["SIGNUPS"] == gates.Resolved("enabled", "default")


# ---- resolution ----------------------------------------------------------


@pytest.mark.parametrize("raw", ["disabled", " Disabled ", "DISABLED"])
def test_an_allowed_value_wins_trimmed_and_case_insensitive(raw):
    resolved = gates.load({"ROUNDS_GATE_RUN": raw})
    assert resolved["RUN"] == gates.Resolved("disabled", "env")


@pytest.mark.parametrize("raw", ["true", "on", "en abled", "enabled!", "0"])
def test_any_other_value_takes_the_most_restrictive_value(raw):
    assert gates.load({"ROUNDS_GATE_PDF_RENDER": raw})["PDF_RENDER"] == gates.Resolved("disabled", "invalid")
    assert gates.load({"ROUNDS_GATE_ENFORCE_QUOTA": raw})["ENFORCE_QUOTA"] == gates.Resolved("enforce", "invalid")


@pytest.mark.parametrize("raw", ["", "   "])
def test_an_empty_gate_counts_as_unset(raw):
    assert gates.load({"ROUNDS_GATE_RUN": raw})["RUN"] == gates.Resolved("enabled", "default")


@pytest.mark.parametrize("truthy", ["true", "TRUE", "1", "yes", " yes "])
def test_each_signup_alias_applies_only_to_its_own_reader(truthy):
    pb_alias = {"ROUNDS_DISABLE_SIGNUPS": truthy}
    assert gates.load(pb_alias, gates.POCKETBASE)["SIGNUPS"] == gates.Resolved("disabled", "alias")
    assert gates.load(pb_alias, gates.FRONTEND)["SIGNUPS"] == gates.Resolved("enabled", "default")

    spa_alias = {"VITE_DISABLE_SIGNUPS": truthy}
    assert gates.load(spa_alias, gates.FRONTEND)["SIGNUPS"] == gates.Resolved("disabled", "alias")
    assert gates.load(spa_alias, gates.POCKETBASE)["SIGNUPS"] == gates.Resolved("enabled", "default")


@pytest.mark.parametrize("falsy", ["false", "0", "no", "", "disabled"])
def test_a_signup_alias_that_isnt_truthy_changes_nothing(falsy):
    env = {"ROUNDS_DISABLE_SIGNUPS": falsy, "VITE_DISABLE_SIGNUPS": falsy}
    assert gates.load(env, gates.POCKETBASE)["SIGNUPS"].value == "enabled"
    assert gates.load(env, gates.FRONTEND)["SIGNUPS"].value == "enabled"


def test_a_set_signup_gate_wins_over_its_aliases():
    env = {
        "ROUNDS_GATE_SIGNUPS": "enabled",
        "ROUNDS_DISABLE_SIGNUPS": "true",
        "VITE_DISABLE_SIGNUPS": "true",
    }
    assert gates.load(env, gates.POCKETBASE)["SIGNUPS"] == gates.Resolved("enabled", "env")
    assert gates.load(env, gates.FRONTEND)["SIGNUPS"] == gates.Resolved("enabled", "env")


def test_the_runner_never_reads_the_signup_gate():
    assert "SIGNUPS" not in gates.load({"ROUNDS_GATE_SIGNUPS": "disabled"}, gates.RUNNER)


# ---- startup log ---------------------------------------------------------


def test_startup_logs_every_runner_gate_once(capsys):
    gates.init({"ROUNDS_GATE_PDF_RENDER": "disabled"})
    (line,) = _gates_lines(capsys.readouterr().out)
    assert line["v"] == "obs/v1"
    assert line["service"] == "runner"
    assert sorted(line["gates"]) == sorted(g.name for g in RUNNER_GATES)
    assert line["gates"]["PDF_RENDER"] == {"value": "disabled", "source": "env"}
    assert line["gates"]["RUN"] == {"value": "enabled", "source": "default"}
    assert "dropped" not in line


def test_an_invalid_value_is_logged_without_the_raw_value(capsys, caplog):
    raw = "Placeholder-Not-A-Gate-Value"
    with caplog.at_level("ERROR"):
        gates.init({"ROUNDS_GATE_RUN": raw})
    (line,) = _gates_lines(capsys.readouterr().out)
    assert line["gates"]["RUN"] == {"value": "disabled", "source": "invalid"}
    messages = [r.getMessage() for r in caplog.records]
    assert any("ROUNDS_GATE_RUN" in m and "invalid" in m for m in messages)
    assert all(raw.lower() not in m.lower() for m in messages)
    assert raw.lower() not in json.dumps(line).lower()


def test_values_are_read_once_and_served_from_the_snapshot(capsys):
    gates.init({"ROUNDS_GATE_ATS_RULE": "disabled"})
    capsys.readouterr()
    assert gates.value("ATS_RULE") == "disabled"
    assert gates.route_enabled("ATS_RULE") is False
    assert gates.route_enabled("RUN") is True
    assert _gates_lines(capsys.readouterr().out) == []


def test_the_runner_logs_its_gates_when_it_starts(capsys, monkeypatch):
    from fastapi.testclient import TestClient

    from main import app

    monkeypatch.setenv("ROUNDS_GATE_PDF_HEALTH", "disabled")
    with TestClient(app):
        pass
    lines = _gates_lines(capsys.readouterr().out)
    assert lines and lines[-1]["gates"]["PDF_HEALTH"] == {"value": "disabled", "source": "env"}


# ---- the three readers stay in step --------------------------------------


def _expected_for(reader: str) -> dict:
    return {
        g.name: {
            "values": list(g.values),
            "default": g.default,
            "closed": g.closed,
            "aliases": [{"env": a.env, "value": a.value} for a in g.aliases if a.reader == reader],
        }
        for g in gates.REGISTRY
        if reader in g.readers
    }


def _node(script: str, *args: str) -> object:
    node = shutil.which("node")
    assert node, "node is required for the PocketBase gate checks; CI installs it"
    res = subprocess.run(
        [node, "-e", script, *args], capture_output=True, text=True, timeout=60, check=True
    )
    return json.loads(res.stdout)


def test_the_pocketbase_module_carries_the_pocketbase_gates():
    data = _node(
        "const g = require(process.argv[1]);"
        "console.log(JSON.stringify({prefix: g.PREFIX, truthy: g.TRUTHY, gates: g.GATES, keys: g.envKeys()}));",
        str(PB_MODULE),
    )
    assert data["prefix"] == gates.PREFIX
    assert data["truthy"] == list(gates.TRUTHY)
    assert data["gates"] == _expected_for(gates.POCKETBASE)
    assert data["keys"] == ["ROUNDS_GATE_SIGNUPS", "ROUNDS_DISABLE_SIGNUPS"]


ENV_CASES = [
    {},
    {"ROUNDS_GATE_SIGNUPS": "disabled"},
    {"ROUNDS_GATE_SIGNUPS": " ENABLED "},
    {"ROUNDS_GATE_SIGNUPS": "true"},
    {"ROUNDS_GATE_SIGNUPS": ""},
    {"ROUNDS_DISABLE_SIGNUPS": "true"},
    {"ROUNDS_DISABLE_SIGNUPS": "YES"},
    {"ROUNDS_DISABLE_SIGNUPS": "false"},
    {"ROUNDS_GATE_SIGNUPS": "enabled", "ROUNDS_DISABLE_SIGNUPS": "true"},
    {"VITE_DISABLE_SIGNUPS": "true"},
]


def test_pocketbase_resolves_every_case_like_the_runner_registry():
    results = _node(
        "const g = require(process.argv[1]);"
        "const cases = JSON.parse(process.argv[2]);"
        "console.log(JSON.stringify(cases.map((env) => g.snapshot(env))));",
        str(PB_MODULE),
        json.dumps(ENV_CASES),
    )
    for env, got in zip(ENV_CASES, results, strict=True):
        want = {n: {"value": r.value, "source": r.source} for n, r in gates.load(env, gates.POCKETBASE).items()}
        assert got == want, env


def test_the_spa_registry_carries_the_frontend_gates():
    data = json.loads(SPA_REGISTRY.read_text())
    assert data["prefix"] == gates.PREFIX
    assert data["truthy"] == list(gates.TRUTHY)
    assert data["gates"] == _expected_for(gates.FRONTEND)


def test_runtime_config_publishes_only_the_frontend_gates():
    script = (ROOT / "frontend" / "docker-entrypoint.d" / "10-runtime-config.sh").read_text()
    (line,) = [ln for ln in script.splitlines() if ln.startswith("SPA_GATES=")]
    published = set(line.split("=", 1)[1].strip('"').split())
    assert published == {g.name for g in gates.REGISTRY if gates.FRONTEND in g.readers}


# ---- deployment plumbing passes every gate through -----------------------


def _service_env(compose: dict, service: str) -> list[str]:
    return compose["services"][service].get("environment", [])


@pytest.mark.parametrize("compose_file", ["docker-compose.yml", "docker-compose.prod.yml"])
def test_compose_passes_each_reader_its_gates(compose_file):
    compose = yaml.safe_load((ROOT / compose_file).read_text())
    for service, reader in (("runner", gates.RUNNER), ("pocketbase", gates.POCKETBASE), ("frontend", gates.FRONTEND)):
        env = _service_env(compose, service)
        for gate in gates.REGISTRY:
            line = f"{gate.env}=${{{gate.env}:-}}"
            if reader in gate.readers:
                assert line in env, (compose_file, service, gate.env)


def test_the_k8s_configmap_lists_every_gate_empty_and_every_reader_loads_it():
    configmap = yaml.safe_load((ROOT / "k8s" / "gates.yaml").read_text())
    assert configmap["metadata"]["name"] == "rounds-gates"
    assert configmap["data"] == {g.env: "" for g in gates.REGISTRY}
    kustomization = yaml.safe_load((ROOT / "k8s" / "kustomization.yaml").read_text())
    assert "gates.yaml" in kustomization["resources"]
    for manifest in ("runner.yaml", "pocketbase.yaml", "frontend.yaml"):
        docs = [d for d in yaml.safe_load_all((ROOT / "k8s" / manifest).read_text()) if d]
        (deployment,) = [d for d in docs if d["kind"] == "Deployment"]
        (container,) = deployment["spec"]["template"]["spec"]["containers"]
        refs = [src.get("configMapRef") for src in container.get("envFrom", [])]
        assert {"name": "rounds-gates", "optional": True} in refs, manifest
