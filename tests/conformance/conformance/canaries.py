"""Per-run canaries for the containment corpus.

A canary is a secret-shaped value the corpus plants in a place a
contained worker must never expose (the runner's environment, the
provider-key secret, the admission secret). Each run generates fresh
values, so a receipt or an artifact can be scanned for them and a leak is
unambiguous. The values are obvious test placeholders with a per-run
random suffix; they are never real secrets.

Some canaries name a value that a later leaf introduces and this branch
does not set yet (#3's ``ROUNDS_EXECUTION_SECRET``, #5's launcher token).
Those are carried as ``absent``: the corpus still records the name so the
receipt shows the full set, but there is nothing to plant or scan for
until the leaf lands. The launcher injects the present values into the
stack as the runner's environment; the absent ones are simply not set.

The canary set has a stable id (``canary-set/v1``) that the receipt
records, plus the per-run values, so a reviewer can tell which names were
live for a given run.
"""
from __future__ import annotations

import json
import os
import secrets
from dataclasses import dataclass, field
from typing import Iterable

CANARY_SET_ID = "canary-set/v1"

# name -> environment variable the launcher sets to the canary value, and
# whether the value exists on this branch. ``landed_by`` names the leaf
# that introduces an absent one.
CANARY_NAMES = {
    "AI_KEY_SECRET": {"env": "AI_KEY_SECRET", "landed": True, "landed_by": None},
    "PB_ADMIN_EMAIL": {"env": "PB_ADMIN_EMAIL", "landed": True, "landed_by": None},
    "PB_ADMIN_PASSWORD": {"env": "PB_ADMIN_PASSWORD", "landed": True, "landed_by": None},
    "ROUNDS_ADMISSION_SECRET": {"env": "ROUNDS_ADMISSION_SECRET", "landed": True, "landed_by": None},
    # Introduced by later leaves; absent until they land.
    "ROUNDS_EXECUTION_SECRET": {"env": "ROUNDS_EXECUTION_SECRET", "landed": False, "landed_by": "ROUNDS-00A-L03"},
    "ROUNDS_LAUNCHER_TOKEN": {"env": "ROUNDS_LAUNCHER_TOKEN", "landed": False, "landed_by": "ROUNDS-00A-L05"},
}


@dataclass(frozen=True)
class Canary:
    name: str
    value: str | None  # None when absent on this branch
    landed: bool
    landed_by: str | None

    @property
    def present(self) -> bool:
        return self.landed and bool(self.value)


@dataclass
class CanarySet:
    set_id: str = CANARY_SET_ID
    canaries: list[Canary] = field(default_factory=list)

    @classmethod
    def generate(cls, run_id: str) -> "CanarySet":
        """A fresh set for one run. Present canaries get a random value;
        absent ones get ``None``."""
        out: list[Canary] = []
        for name, meta in CANARY_NAMES.items():
            value = None
            if meta["landed"]:
                value = f"canary-{name.lower()}-{run_id}-{secrets.token_hex(8)}"
            out.append(Canary(name, value, meta["landed"], meta["landed_by"]))
        return cls(canaries=out)

    @classmethod
    def from_env(cls) -> "CanarySet":
        """The set the launcher planted, read back from the environment the
        corpus container was given. A present canary whose variable is unset
        is treated as absent for this run."""
        out: list[Canary] = []
        for name, meta in CANARY_NAMES.items():
            value = os.environ.get(meta["env"]) if meta["landed"] else None
            out.append(Canary(name, value or None, meta["landed"] and bool(value), meta["landed_by"]))
        return cls(canaries=out)

    def present_values(self) -> dict[str, str]:
        return {c.name: c.value for c in self.canaries if c.present}

    def env(self) -> dict[str, str]:
        """The environment a launcher sets to plant the present canaries."""
        env: dict[str, str] = {}
        for c in self.canaries:
            if c.present:
                env[CANARY_NAMES[c.name]["env"]] = c.value  # type: ignore[index]
        return env

    def hits(self, text: str) -> dict[str, bool]:
        """Which present canaries appear in ``text``. Absent canaries map
        to ``False`` so the receipt carries the full set."""
        return {c.name: (c.present and c.value in text) for c in self.canaries}

    def any_hit(self, text: str) -> bool:
        return any(self.hits(text).values())

    def summary(self) -> dict[str, object]:
        return {
            "set_id": self.set_id,
            "names": {
                c.name: ("present" if c.present else "absent")
                + (f" (landed_by {c.landed_by})" if not c.landed else "")
                for c in self.canaries
            },
        }


def scan(values: Iterable[str], text: str) -> list[str]:
    """Which of ``values`` appear verbatim in ``text``."""
    return [v for v in values if v and v in text]
