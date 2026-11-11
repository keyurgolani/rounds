"""Deployment wiring for the execution job store (ROUNDS-00A-L03 PR 1).

Both compose files and the k8s manifests hand ``ROUNDS_EXECUTION_SECRET`` to
PocketBase and the runner only, with no default, and the runner's readiness
probe is ``/ready`` while liveness stays ``/health``. The candidate process
side is covered in ``test_execution_executor.py``.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SECRET = "ROUNDS_EXECUTION_SECRET"
RUNNER_SECRETS = "rounds-runner-secrets"


def _env_lines(service: dict) -> list[str]:
    env = service.get("environment", [])
    if isinstance(env, dict):
        return [f"{key}={value}" for key, value in env.items()]
    return list(env)


def _deployment_container(manifest: str) -> dict:
    docs = [d for d in yaml.safe_load_all((ROOT / "k8s" / manifest).read_text()) if d]
    (deployment,) = [d for d in docs if d["kind"] == "Deployment"]
    (container,) = deployment["spec"]["template"]["spec"]["containers"]
    return container


@pytest.mark.parametrize("compose_file", ["docker-compose.yml", "docker-compose.prod.yml"])
def test_compose_hands_the_worker_secret_to_pocketbase_and_the_runner_with_no_default(compose_file):
    services = yaml.safe_load((ROOT / compose_file).read_text())["services"]
    assert {"pocketbase", "runner"} <= set(services)
    for name, service in services.items():
        assert "env_file" not in service, (compose_file, name)
        lines = [line for line in _env_lines(service) if line.split("=", 1)[0] == SECRET]
        want = [f"{SECRET}=${{{SECRET}:-}}"] if name in ("pocketbase", "runner") else []
        assert lines == want, (compose_file, name)


def test_k8s_runner_loads_the_runner_secret_and_is_ready_on_ready():
    container = _deployment_container("runner.yaml")
    assert {"secretRef": {"name": RUNNER_SECRETS}} in container["envFrom"]
    assert all(entry["name"] != SECRET for entry in container.get("env", []))
    assert container["readinessProbe"]["httpGet"] == {"path": "/ready", "port": 8000}
    assert container["livenessProbe"]["httpGet"] == {"path": "/health", "port": 8000}


def test_k8s_pocketbase_takes_only_the_worker_key_of_the_runner_secret():
    container = _deployment_container("pocketbase.yaml")
    (entry,) = [e for e in container["env"] if e["name"] == SECRET]
    assert entry == {
        "name": SECRET,
        "valueFrom": {"secretKeyRef": {"name": RUNNER_SECRETS, "key": SECRET, "optional": True}},
    }
    refs = [src.get("secretRef", {}).get("name") for src in container.get("envFrom", [])]
    assert RUNNER_SECRETS not in refs


def test_the_frontend_never_gets_the_worker_secret():
    container = _deployment_container("frontend.yaml")
    assert all(entry["name"] != SECRET for entry in container.get("env", []))
    refs = [src.get("secretRef", {}).get("name") for src in container.get("envFrom", [])]
    assert RUNNER_SECRETS not in refs
