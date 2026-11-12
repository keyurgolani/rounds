"""The privacy operator settings and the runner's startup check (ROUNDS-14-L01)."""
from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from app import gates
from app.privacy import evaluator, settings

ENV = (settings.LOG_RETENTION, settings.BACKUP_RETENTION, settings.PRIVATE_ENDPOINTS)


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
def test_log_retention_outside_its_bounds_names_them(value):
    with pytest.raises(settings.SettingsError, match=rf"{settings.LOG_RETENTION} is {value} days; it must be from 1 to 30"):
        settings.load({settings.LOG_RETENTION: value})


@pytest.mark.parametrize("value", ["fourteen", "14.5", "-3", "1e2"])
def test_log_retention_not_a_whole_number(value):
    with pytest.raises(settings.SettingsError, match=r"must be a whole number of days from 1 to 30"):
        settings.load({settings.LOG_RETENTION: value})


@pytest.mark.parametrize("value,ok", [("7", True), ("90", True), ("6", False), ("91", False)])
def test_backup_retention_bounds(value, ok):
    if ok:
        assert settings.load({settings.BACKUP_RETENTION: value}).backup_retention_days == int(value)
    else:
        with pytest.raises(settings.SettingsError, match=rf"{settings.BACKUP_RETENTION} is {value} days; it must be from 7 to 90"):
            settings.load({settings.BACKUP_RETENTION: value})


@pytest.mark.parametrize("entry", ["localhost:8000", "pocketbase:8090", "pdf-renderer:4000", "169.254.169.254:80"])
def test_never_destinations_are_refused_as_entries(entry):
    with pytest.raises(settings.SettingsError, match=entry.replace(".", r"\.")):
        settings.load({settings.PRIVATE_ENDPOINTS: f"10.0.0.5:11434,{entry}"})


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
    (settings.LOG_RETENTION, "45", "ROUNDS_LOG_RETENTION_DAYS is 45 days; it must be from 1 to 30"),
    (settings.BACKUP_RETENTION, "120", "ROUNDS_BACKUP_RETENTION_DAYS is 120 days; it must be from 7 to 90"),
    (settings.PRIVATE_ENDPOINTS, "pocketbase:8090", "'pocketbase:8090' names a host"),
])
def test_the_runner_refuses_to_start_on_a_bad_value(monkeypatch, name, value, message):
    from main import app

    for other in ENV:
        monkeypatch.delenv(other, raising=False)
    monkeypatch.setenv(name, value)
    with pytest.raises(settings.SettingsError) as raised:
        with TestClient(app):
            pass
    assert message in str(raised.value)


def test_the_runner_starts_with_valid_values(monkeypatch):
    from main import app

    monkeypatch.setenv(settings.LOG_RETENTION, "7")
    monkeypatch.setenv(settings.BACKUP_RETENTION, "60")
    monkeypatch.setenv(settings.PRIVATE_ENDPOINTS, "")
    with TestClient(app) as c:
        assert c.get("/health").json() == {"status": "ok"}
    assert settings.current().log_retention_days == 7
