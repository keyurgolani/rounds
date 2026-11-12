"""The privacy policy's three operator settings (ROUNDS-14-L01).

- ``ROUNDS_LOG_RETENTION_DAYS``: how long logs and traces are kept.
- ``ROUNDS_BACKUP_RETENTION_DAYS``: how long encrypted backups are kept.
- ``ROUNDS_AI_PRIVATE_ENDPOINTS``: the operator-network AI endpoints.

Their bounds and defaults come from the lifecycle rows in ``policy.json``,
so the startup check, the evaluators, and the docs read one number. The
runner calls ``init`` once at startup; a bad value raises
``SettingsError``, which stops the runner with one line naming the
setting and its bounds, or the position of the entry it refuses. The
line never repeats a day count, and shows an entry's network only once
it has parsed as one. Unset or empty takes the
default. Nothing else reads these yet: ROUNDS-34-L05 applies the log
window, ROUNDS-32-L03 the backup window, and ROUNDS-14-L02 reads the
allowlist at dispatch, where a private address needs both it and
``ROUNDS_GATE_PROVIDER_PRIVATE_NETWORK``.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Mapping

from app import gates
from app.privacy import evaluator

LOG_RETENTION = "ROUNDS_LOG_RETENTION_DAYS"
BACKUP_RETENTION = "ROUNDS_BACKUP_RETENTION_DAYS"
PRIVATE_ENDPOINTS = "ROUNDS_AI_PRIVATE_ENDPOINTS"

_log = logging.getLogger(__name__)


class SettingsError(RuntimeError):
    """A privacy setting the runner refuses to start with."""


@dataclass(frozen=True)
class PrivacySettings:
    log_retention_days: int
    backup_retention_days: int
    private_endpoints: tuple[Mapping[str, Any], ...]


def _days(env: Mapping[str, str], name: str) -> int:
    spec = evaluator.operator_setting(name)
    lo, hi, default = spec["min"], spec["max"], spec["default"]
    raw = (env.get(name) or "").strip()
    if not raw:
        return default
    if not re.fullmatch(r"[0-9]{1,6}", raw):
        raise SettingsError(f"{name} must be a whole number of days from {lo} to {hi} (unset takes {default})")
    value = int(raw)
    if not lo <= value <= hi:
        raise SettingsError(f"{name} is outside its bounds; it must be from {lo} to {hi} days (unset takes {default})")
    return value


def load(env: Mapping[str, str] | None = None) -> PrivacySettings:
    """The three settings from ``env`` (the process environment by default)."""
    env = os.environ if env is None else env
    log_days = _days(env, LOG_RETENTION)
    backup_days = _days(env, BACKUP_RETENTION)
    try:
        entries = evaluator.parse_private_endpoints(env.get(PRIVATE_ENDPOINTS) or "")
    except ValueError as err:
        raise SettingsError(str(err)) from None
    return PrivacySettings(log_days, backup_days, tuple(entries))


_settings: PrivacySettings | None = None


def init(env: Mapping[str, str] | None = None) -> PrivacySettings:
    """Read and check the settings once, at startup, and log what was read."""
    global _settings
    _settings = load(env)
    gate_on = gates.value("PROVIDER_PRIVATE_NETWORK") == "enabled"
    if _settings.private_endpoints and not gate_on:
        _log.warning("%s has %d entries, but ROUNDS_GATE_PROVIDER_PRIVATE_NETWORK is off, so every private address stays refused.",
                     PRIVATE_ENDPOINTS, len(_settings.private_endpoints))
    _log.info("privacy settings: %s=%d, %s=%d, %s has %d entries", LOG_RETENTION, _settings.log_retention_days,
              BACKUP_RETENTION, _settings.backup_retention_days, PRIVATE_ENDPOINTS, len(_settings.private_endpoints))
    return _settings


def current() -> PrivacySettings:
    return _settings if _settings is not None else init()
