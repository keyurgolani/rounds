"""Artifact redaction for the containment corpus.

The repository is public, so any artifact the corpus keeps for a failed
fixture is scrubbed before it is written or uploaded: the run's canary
values and the job's own environment values are removed, because a
redaction miss on a public repo publishes whatever leaked (#8 body,
Privacy and security implications). Redaction runs on every retained
artifact, and the self-test plants a canary and asserts it is gone before
upload.

What is removed:
- every present canary value (exact match);
- every value in the job's environment that is long enough to be a secret
  (short, common values like ``PATH`` segments or ``C.UTF-8`` are not
  treated as secrets, so normal output is not mangled);
- bearer tokens in ``Authorization`` headers echoed into an artifact.

Each removal leaves a fixed ``<redacted:REASON>`` marker so the artifact
still reads sensibly. Redaction never widens: it only replaces, so an
already-clean artifact is unchanged apart from any real secret it held.
"""
from __future__ import annotations

import os
import re
from typing import Iterable, Mapping

# A value shorter than this from the environment is not treated as a
# secret. Canary values are always redacted regardless of length.
_MIN_ENV_SECRET_LEN = 12

# Environment variables whose values are structural, not secret, so
# redacting them would corrupt ordinary output.
_ENV_NEVER_REDACT = {
    "PATH", "HOME", "PWD", "LANG", "LC_ALL", "TMPDIR", "USER", "LOGNAME",
    "SHELL", "TERM", "HOSTNAME", "PYTHONPATH", "PYTHONDONTWRITEBYTECODE",
}

_BEARER = re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]{8,}", re.IGNORECASE)


def _env_secrets(env: Mapping[str, str]) -> list[str]:
    out: list[str] = []
    for key, value in env.items():
        if key in _ENV_NEVER_REDACT:
            continue
        if value and len(value) >= _MIN_ENV_SECRET_LEN:
            out.append(value)
    # Longest first, so a value that contains another is replaced whole.
    return sorted(set(out), key=len, reverse=True)


def redact(text: str, canary_values: Iterable[str], env: Mapping[str, str] | None = None) -> str:
    """Return ``text`` with every canary value, environment secret, and
    bearer token removed."""
    if env is None:
        env = os.environ
    out = text
    for value in sorted({v for v in canary_values if v}, key=len, reverse=True):
        out = out.replace(value, "<redacted:canary>")
    for value in _env_secrets(env):
        out = out.replace(value, "<redacted:env>")
    out = _BEARER.sub(r"\1<redacted:bearer>", out)
    return out


def clean(text: str, canary_values: Iterable[str]) -> bool:
    """Whether ``text`` holds no canary value verbatim. Used by the
    self-test and as a last-chance guard: ``clean(redact(a, c), c)`` must
    hold before an artifact is written."""
    return all(v not in text for v in canary_values if v)
