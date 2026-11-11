"""The frontend's client address behind a proxy (ROUNDS-00B-L04,
frontend/docker-entrypoint.d/20-real-ip.sh).

Unset, nginx counts each client by its peer address and writes no real_ip
settings. Set, each entry becomes one trusted hop for X-Forwarded-For. An
entry that isn't an address or a CIDR stops the container and writes
nothing, so a typo never trusts the wrong hop.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "frontend" / "docker-entrypoint.d" / "20-real-ip.sh"
DOCKERFILE = ROOT / "frontend" / "Dockerfile"


def _run(tmp_path: Path, value: str | None) -> tuple[subprocess.CompletedProcess, Path]:
    sh = shutil.which("sh")
    assert sh
    target = tmp_path / "00-real-ip.conf"
    env = {"PATH": os.environ.get("PATH", ""), "ROUNDS_REAL_IP_CONF_PATH": str(target)}
    if value is not None:
        env["ROUNDS_FRONTEND_REAL_IP_FROM"] = value
    return subprocess.run([sh, str(SCRIPT)], env=env, capture_output=True, text=True, timeout=30), target


@pytest.mark.parametrize("value", [None, "", " , "])
def test_unset_writes_no_real_ip_settings(tmp_path, value):
    (tmp_path / "00-real-ip.conf").write_text("set_real_ip_from 0.0.0.0/0;\n")
    res, target = _run(tmp_path, value)
    assert res.returncode == 0, res.stderr
    assert not target.exists()


def test_each_entry_becomes_one_trusted_hop(tmp_path):
    res, target = _run(tmp_path, "10.42.0.0/16, 10.43.0.0/16,fd00::/8")
    assert res.returncode == 0, res.stderr
    lines = [ln for ln in target.read_text().splitlines() if not ln.startswith("#")]
    assert lines == [
        "set_real_ip_from 10.42.0.0/16;",
        "set_real_ip_from 10.43.0.0/16;",
        "set_real_ip_from fd00::/8;",
        "real_ip_header X-Forwarded-For;",
        "real_ip_recursive on;",
    ]


@pytest.mark.parametrize("value", ["10.0.0.0/8;0.0.0.0/0", "10.0.0.0/8 include /etc/passwd", "all", "10.0.0.0//8",
                                   "/8", "10.0.0.0/"])
def test_an_entry_that_is_not_an_address_stops_the_container_and_writes_nothing(tmp_path, value):
    res, target = _run(tmp_path, value)
    assert res.returncode != 0
    assert not target.exists()
    # The message names the setting, never its value.
    assert value not in res.stderr and "ROUNDS_FRONTEND_REAL_IP_FROM" in res.stderr


def test_the_image_runs_the_script():
    text = DOCKERFILE.read_text()
    assert "COPY docker-entrypoint.d/20-real-ip.sh /docker-entrypoint.d/20-real-ip.sh" in text
    assert "/docker-entrypoint.d/20-real-ip.sh" in text.split("RUN chmod +x", 1)[1].splitlines()[0]
