"""Self-test: artifact redaction removes a planted canary before upload
(issue #8, Required tests Unit: a planted canary is gone before upload)."""
from __future__ import annotations

from conformance.redaction import clean, redact


def test_planted_canary_is_gone_after_redaction():
    canary = "canary-ai_key_secret-run42-abcdef0123456789"
    artifact = f"stdout: AI_KEY_SECRET={canary} and more"
    safe = redact(artifact, [canary])
    assert canary not in safe
    assert "<redacted:canary>" in safe
    assert clean(safe, [canary])


def test_environment_secret_is_removed():
    env = {"SOME_SECRET": "super-secret-value-9999", "PATH": "/usr/bin"}
    artifact = "leaked super-secret-value-9999 here, PATH /usr/bin stays"
    safe = redact(artifact, [], env)
    assert "super-secret-value-9999" not in safe
    assert "/usr/bin" in safe  # PATH is structural, not a secret


def test_short_env_values_are_not_mangled():
    env = {"TIER": "demo"}
    artifact = "the demo tier output"
    safe = redact(artifact, [], env)
    assert safe == artifact


def test_bearer_token_is_redacted():
    artifact = "Authorization: Bearer abcdef0123456789TOKEN"
    safe = redact(artifact, [])
    assert "abcdef0123456789TOKEN" not in safe
    assert "<redacted:bearer>" in safe


def test_clean_is_false_when_a_canary_survives():
    assert not clean("holds canary-x-123456 still", ["canary-x-123456"])
