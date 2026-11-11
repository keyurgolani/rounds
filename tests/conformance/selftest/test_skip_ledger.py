"""Self-test: the skip ledger enforces an owner, an expiry, and known
fixtures, and fails on an expired entry (issue #8, Required tests Unit)."""
from __future__ import annotations

import datetime as _dt
import json

import pytest

from conformance import manifest as m


def test_real_ledger_loads_and_is_empty_at_stage_1():
    man = m.load_manifest()
    skips = m.load_skip_ledger(manifest=man)
    assert skips == []


def _write(tmp_path, skips):
    data = {"schema": m.SKIP_LEDGER_SCHEMA, "skips": skips}
    path = tmp_path / "skip_ledger.json"
    path.write_text(json.dumps(data))
    return str(path)


def test_future_skip_with_owner_and_expiry_loads(tmp_path):
    man = m.load_manifest()
    path = _write(tmp_path, [{
        "id": man.fixtures[0].id, "target": "ci", "owner": "team",
        "expiry": "2099-01-01", "reason": "flaky on shared runners",
    }])
    skips = m.load_skip_ledger(path, manifest=man)
    assert len(skips) == 1 and skips[0].owner == "team"


def test_expired_skip_fails(tmp_path):
    man = m.load_manifest()
    path = _write(tmp_path, [{
        "id": man.fixtures[0].id, "target": "ci", "owner": "team",
        "expiry": "2000-01-01", "reason": "stale",
    }])
    with pytest.raises(m.ManifestError):
        m.load_skip_ledger(path, manifest=man, today=_dt.date(2026, 1, 1))


def test_skip_without_owner_fails(tmp_path):
    man = m.load_manifest()
    path = _write(tmp_path, [{
        "id": man.fixtures[0].id, "target": "ci", "owner": "",
        "expiry": "2099-01-01", "reason": "x",
    }])
    with pytest.raises(m.ManifestError):
        m.load_skip_ledger(path, manifest=man)


def test_skip_for_unknown_fixture_fails(tmp_path):
    man = m.load_manifest()
    path = _write(tmp_path, [{
        "id": "ZZ-99", "target": "ci", "owner": "team",
        "expiry": "2099-01-01", "reason": "x",
    }])
    with pytest.raises(m.ManifestError):
        m.load_skip_ledger(path, manifest=man)
