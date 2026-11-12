"""Where the compose files publish ports on the host.

Production publishes only the frontend's nginx port, on the host address
HTTP_BIND names. Unset or blank, the address is empty, and Compose reads the
entry exactly as it read the bare "80:80" entry before HTTP_BIND, which
Docker publishes on every IPv4 and IPv6 address. 127.0.0.1 or [::1], the
spellings the docs give, publish it on loopback only, and a value that isn't
an IP address stops Compose. Dev compose publishes each of its ports on
127.0.0.1.

The tests that run real Compose run only in GitHub Actions, whose backend
job has the docker CLI, and skip everywhere else. They only render the
files and start nothing.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PROD = ROOT / "docker-compose.prod.yml"
# The frontend's entry before HTTP_BIND. Unset, the new entry must render
# exactly as this one does.
BARE_ENTRY = '"${HTTP_PORT:-80}:80"'
# Compose's ${VAR:-default}: VAR when it's set and not blank, else default.
DEFAULTED = re.compile(r"\$\{(\w+):-([^}]*)\}")

# GitHub Actions sets GITHUB_ACTIONS on every step. Keyed on that rather
# than on finding docker, so a machine that has the CLI never runs it here,
# and CI fails these instead of skipping them if its docker CLI goes away.
in_ci = pytest.mark.skipif(os.environ.get("GITHUB_ACTIONS") != "true", reason="real Compose runs only in CI's backend job")


def _services(path: Path) -> dict:
    return yaml.safe_load(path.read_text())["services"]


def _interpolate(value: str, env: dict[str, str]) -> str:
    rendered = DEFAULTED.sub(lambda m: env.get(m.group(1)) or m.group(2), value)
    assert "$" not in rendered, f"a form this test can't render: {value}"
    return rendered


def _compose_config(compose_file: Path, env: dict[str, str], tmp_path: Path) -> subprocess.CompletedProcess:
    # An empty env file, so a local .env can't change the result, and no
    # inherited HTTP_BIND, HTTP_PORT, or COMPOSE_ setting either.
    env_file = tmp_path / "empty.env"
    env_file.write_text("")
    inherited = {k: v for k, v in os.environ.items() if k not in ("HTTP_BIND", "HTTP_PORT") and not k.startswith("COMPOSE_")}
    return subprocess.run(
        ["docker", "compose", "--env-file", str(env_file), "-p", "ports_check", "-f", str(compose_file), "config", "--format", "json"],
        env={**inherited, **env},
        capture_output=True,
        text=True,
        timeout=120,
    )


def _frontend_port(compose_file: Path, env: dict[str, str], tmp_path: Path) -> dict:
    proc = _compose_config(compose_file, env, tmp_path)
    assert proc.returncode == 0, proc.stderr
    (port,) = json.loads(proc.stdout)["services"]["frontend"]["ports"]
    return port


def _bare_compose(tmp_path: Path) -> Path:
    path = tmp_path / "bare.yml"
    path.write_text(f"services:\n  frontend:\n    image: nginx\n    ports:\n      - {BARE_ENTRY}\n")
    return path


@pytest.mark.parametrize(
    ("env", "rendered"),
    [
        ({}, ":80:80"),
        ({"HTTP_BIND": ""}, ":80:80"),
        ({"HTTP_BIND": "127.0.0.1"}, "127.0.0.1:80:80"),
        ({"HTTP_BIND": "[::1]"}, "[::1]:80:80"),
        ({"HTTP_PORT": "8080"}, ":8080:80"),
    ],
    ids=["unset", "blank", "ipv4_loopback", "ipv6_loopback", "other_port"],
)
def test_the_frontend_port_renders_on_the_address_http_bind_names(env, rendered):
    # An empty address before the host port is no address; the real Compose
    # tests below check that it reads that way.
    (entry,) = _services(PROD)["frontend"]["ports"]
    assert _interpolate(entry, env) == rendered


@in_ci
@pytest.mark.parametrize("env", [{}, {"HTTP_BIND": ""}, {"HTTP_PORT": "8080"}], ids=["unset", "blank", "other_port"])
def test_compose_publishes_the_default_exactly_as_the_bare_entry_did(tmp_path, env):
    port = _frontend_port(PROD, env, tmp_path)
    assert port == _frontend_port(_bare_compose(tmp_path), env, tmp_path)
    assert not port.get("host_ip")
    assert str(port["published"]) == env.get("HTTP_PORT", "80") and port["target"] == 80


@in_ci
@pytest.mark.parametrize(
    ("env", "host_ip"),
    [
        ({"HTTP_BIND": "127.0.0.1"}, "127.0.0.1"),
        # The docs give the bracketed spelling; both are checked.
        ({"HTTP_BIND": "[::1]"}, "::1"),
        ({"HTTP_BIND": "::1"}, "::1"),
        ({"HTTP_BIND": "127.0.0.1", "HTTP_PORT": "8080"}, "127.0.0.1"),
    ],
    ids=["ipv4_loopback", "ipv6_loopback_bracketed", "ipv6_loopback_bare", "ipv4_loopback_other_port"],
)
def test_compose_publishes_on_the_address_http_bind_names(tmp_path, env, host_ip):
    # The bare entry's port, on that address only.
    want = {**_frontend_port(_bare_compose(tmp_path), env, tmp_path), "host_ip": host_ip}
    assert _frontend_port(PROD, env, tmp_path) == want


@in_ci
def test_compose_refuses_an_http_bind_that_is_not_an_ip_address(tmp_path):
    # A hostname, so Compose stops rather than publish the port anywhere.
    proc = _compose_config(PROD, {"HTTP_BIND": "localhost"}, tmp_path)
    assert proc.returncode != 0, proc.stdout
    assert not proc.stdout.strip()


def test_dev_compose_publishes_every_port_on_loopback_only():
    services = _services(ROOT / "docker-compose.yml")
    ports = [(name, port) for name, svc in services.items() for port in svc.get("ports", [])]
    assert ports, "dev compose publishes no ports"
    for name, port in ports:
        # A literal address, so no variable can widen it.
        assert isinstance(port, str) and port.startswith("127.0.0.1:"), (name, port)
