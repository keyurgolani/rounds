"""The privacy operator settings and the runner's startup check (ROUNDS-14-L01)."""
from __future__ import annotations

import logging
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from app import gates
from app.privacy import evaluator, settings

ENV = (settings.LOG_RETENTION, settings.BACKUP_RETENTION, settings.PRIVATE_ENDPOINTS)
ROOT = Path(__file__).resolve().parents[2]


def test_unset_and_empty_take_the_defaults():
    for env in ({}, {name: "" for name in ENV}, {name: "  " for name in ENV}):
        got = settings.load(env)
        assert (got.log_retention_days, got.backup_retention_days, got.private_endpoints) == (14, 30, ())


def test_bounds_come_from_the_policy_rows():
    rows = {r["id"]: r for r in evaluator.POLICY["lifecycle"]["rows"]}
    assert evaluator.operator_setting(settings.LOG_RETENTION) == {
        "name": settings.LOG_RETENTION, "min": rows["logs-traces"]["retention"]["range"][0],
        "max": rows["logs-traces"]["retention"]["range"][1], "default": rows["logs-traces"]["retention"]["default"], "row": "logs-traces"}
    assert evaluator.operator_setting(settings.BACKUP_RETENTION)["max"] == 90


@pytest.mark.parametrize("value", ["1", "14", "30"])
def test_log_retention_inside_its_bounds(value):
    assert settings.load({settings.LOG_RETENTION: value}).log_retention_days == int(value)


@pytest.mark.parametrize("value", ["0", "31", "45"])
def test_log_retention_outside_its_bounds_names_them_not_the_value(value):
    with pytest.raises(settings.SettingsError) as raised:
        settings.load({settings.LOG_RETENTION: value})
    assert str(raised.value) == f"{settings.LOG_RETENTION} is outside its bounds; it must be from 1 to 30 days (unset takes 14)"


@pytest.mark.parametrize("value", ["fourteen", "14.5", "-3", "1e2"])
def test_log_retention_not_a_whole_number(value):
    with pytest.raises(settings.SettingsError, match=r"must be a whole number of days from 1 to 30"):
        settings.load({settings.LOG_RETENTION: value})


@pytest.mark.parametrize("value,ok", [("7", True), ("90", True), ("6", False), ("91", False)])
def test_backup_retention_bounds(value, ok):
    if ok:
        assert settings.load({settings.BACKUP_RETENTION: value}).backup_retention_days == int(value)
    else:
        with pytest.raises(settings.SettingsError) as raised:
            settings.load({settings.BACKUP_RETENTION: value})
        assert str(raised.value) == f"{settings.BACKUP_RETENTION} is outside its bounds; it must be from 7 to 90 days (unset takes 30)"


@pytest.mark.parametrize("entry", ["localhost:8000", "pocketbase:8090", "pdf-renderer:4000", "169.254.169.254:80"])
def test_never_destinations_are_refused_as_entries_by_position(entry):
    with pytest.raises(settings.SettingsError) as raised:
        settings.load({settings.PRIVATE_ENDPOINTS: f"10.0.0.5:11434,{entry}"})
    assert str(raised.value).startswith(f"{settings.PRIVATE_ENDPOINTS} entry 2 ")
    assert entry not in str(raised.value)


@pytest.mark.parametrize("value", [
    "https://user:example@10.0.0.1:443",
    "10.0.0.5:11434,user:example@10.0.0.1:443",
    "Bearer EXAMPLEexampleEXAMPLE:443",
    "[fd12::1%eth0]:8000",
])
def test_a_refused_entry_never_appears_in_the_message(value):
    with pytest.raises(settings.SettingsError) as raised:
        settings.load({settings.PRIVATE_ENDPOINTS: value})
    for item in value.split(","):
        assert item.strip() not in str(raised.value)
    for piece in ("user", "example", "EXAMPLE", "eth0"):
        assert piece not in str(raised.value)


def test_entries_are_parsed():
    got = settings.load({settings.PRIVATE_ENDPOINTS: "10.0.0.5:11434, 192.168.1.0/24:8000"})
    assert [(str(e["network"]), e["port"]) for e in got.private_endpoints] == [("10.0.0.5/32", 11434), ("192.168.1.0/24", 8000)]


def test_entries_with_the_gate_off_start_and_say_so(monkeypatch, caplog):
    monkeypatch.setattr(gates, "_snapshot", gates.load({}, gates.RUNNER))
    with caplog.at_level(logging.WARNING, logger="app.privacy.settings"):
        got = settings.init({settings.PRIVATE_ENDPOINTS: "10.0.0.5:11434"})
    assert len(got.private_endpoints) == 1
    assert "ROUNDS_GATE_PROVIDER_PRIVATE_NETWORK is off" in caplog.text


@pytest.mark.parametrize("name,value,message", [
    (settings.LOG_RETENTION, "45", "ROUNDS_LOG_RETENTION_DAYS is outside its bounds; it must be from 1 to 30 days"),
    (settings.BACKUP_RETENTION, "120", "ROUNDS_BACKUP_RETENTION_DAYS is outside its bounds; it must be from 7 to 90 days"),
    (settings.PRIVATE_ENDPOINTS, "pocketbase:8090", "ROUNDS_AI_PRIVATE_ENDPOINTS entry 1 names a host"),
    (settings.PRIVATE_ENDPOINTS, "https://user:example@10.0.0.1:443", "ROUNDS_AI_PRIVATE_ENDPOINTS entry 1 isn't ip:port"),
])
def test_the_runner_refuses_to_start_on_a_bad_value(monkeypatch, caplog, name, value, message):
    from main import app

    for other in ENV:
        monkeypatch.delenv(other, raising=False)
    monkeypatch.setenv(name, value)
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(settings.SettingsError) as raised:
            with TestClient(app):
                pass
    assert message in str(raised.value)
    assert value not in str(raised.value)
    assert value not in caplog.text


@pytest.mark.parametrize("compose_file", ["docker-compose.yml", "docker-compose.prod.yml"])
def test_compose_passes_each_setting_to_the_runner_empty_by_default(compose_file):
    compose = yaml.safe_load((ROOT / compose_file).read_text(encoding="utf-8"))
    env = compose["services"]["runner"]["environment"]
    for name in ENV:
        assert f"{name}=${{{name}:-}}" in env, (compose_file, name)


def test_the_k8s_runner_leaves_each_setting_to_its_secret():
    """A value under env would hide the one in rounds-runner-secrets, which
    the runner reads through envFrom."""
    docs = [d for d in yaml.safe_load_all((ROOT / "k8s" / "runner.yaml").read_text(encoding="utf-8")) if d]
    (deployment,) = [d for d in docs if d["kind"] == "Deployment"]
    (container,) = deployment["spec"]["template"]["spec"]["containers"]
    assert not {e["name"] for e in container["env"]} & set(ENV)
    assert {"secretRef": {"name": "rounds-runner-secrets"}} in container["envFrom"]


def test_the_example_env_lists_each_setting_empty():
    lines = (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    for name in ENV:
        assert f"{name}=" in lines, name


def test_the_runner_starts_with_valid_values(monkeypatch):
    from main import app

    monkeypatch.setenv(settings.LOG_RETENTION, "7")
    monkeypatch.setenv(settings.BACKUP_RETENTION, "60")
    monkeypatch.setenv(settings.PRIVATE_ENDPOINTS, "")
    with TestClient(app) as c:
        assert c.get("/health").json() == {"status": "ok"}
    assert settings.current().log_retention_days == 7
