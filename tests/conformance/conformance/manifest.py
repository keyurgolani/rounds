"""Load and validate the corpus manifest and the skip ledger.

The manifest pins, per fixture, its id, spec reference, routes,
languages, status, the leaf that closes it, the expected outcome per
target, the named negative control, the ``destructive`` and
``environment_sensitive`` flags, setup, teardown, and a reason where one
is required (#8 acceptance criteria). It covers every row of the issue's
fixture table; the validator fails if a row is missing, a contained row
has no module, a pending row carries a module, or a not-applicable row
has no reason.

The skip ledger carries an owner and an expiry for every skip. An
expired skip fails the lane, and a skip for an unknown fixture fails it
too (#8 acceptance criteria). At stage 1 the ledger is empty; the
structure and its rules ship so a later skip lands with its disposition.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from dataclasses import dataclass, field
from typing import Any

MANIFEST_SCHEMA = "containment-corpus-manifest/v1"
SKIP_LEDGER_SCHEMA = "containment-corpus-skip-ledger/v1"

TARGETS = ("ci", "compose", "k8s")
STATUSES = ("contained", "pending", "not-applicable")
KNOWN_LANGUAGES = ("python", "javascript", "typescript")

# Every row of the issue's fixture table. The validator requires the
# manifest to carry exactly this set, so the corpus cannot silently drop
# or rename a fixture.
REQUIRED_IDS = (
    "EX-01", "EX-02", "EX-03", "EX-04", "EX-05", "EX-06", "EX-07", "EX-08",
    "EX-09", "EX-10", "EX-11", "EX-12", "EX-13", "EX-14", "EX-15", "EX-16",
    "EX-17", "EX-18",
    "FG-01", "FG-02", "FG-03", "FG-04", "FG-05", "FG-06",
    "RD-01", "RD-02", "RD-03", "RD-04", "RD-05", "RD-06", "RD-07", "RD-08",
    "RD-09",
)

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MANIFEST = os.path.join(_HERE, "manifest.json")
DEFAULT_SKIP_LEDGER = os.path.join(_HERE, "skip_ledger.json")
CORPUS_DIR = os.path.join(_HERE, "corpus")


class ManifestError(ValueError):
    """A malformed manifest or skip ledger. Fails the lane."""


@dataclass
class Fixture:
    id: str
    attack: str
    spec_ref: str
    status: str
    closing_leaf: str
    routes: list[str]
    languages: list[str]
    control: str
    destructive: bool
    environment_sensitive: bool
    setup: str
    teardown: str
    module: str | None = None
    expected: dict[str, str] = field(default_factory=dict)
    reason: str = ""
    guarantee: str = ""

    @property
    def runnable(self) -> bool:
        return self.status in ("contained", "not-applicable") and self.module is not None

    def expectation(self, target: str) -> str:
        return self.expected.get(target, self.status)


@dataclass
class Manifest:
    corpus_version: str
    audited_revision: str
    defaults: dict[str, Any]
    fixtures: list[Fixture]

    def by_id(self, fixture_id: str) -> Fixture:
        for f in self.fixtures:
            if f.id == fixture_id:
                return f
        raise KeyError(fixture_id)

    def contained(self) -> list[Fixture]:
        return [f for f in self.fixtures if f.status == "contained"]

    def runnable(self) -> list[Fixture]:
        return [f for f in self.fixtures if f.runnable]

    def pending(self) -> list[Fixture]:
        return [f for f in self.fixtures if f.status == "pending"]


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ManifestError(msg)


def _merge_defaults(row: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    merged = dict(row)
    for key in ("languages", "control", "destructive", "environment_sensitive"):
        if key not in merged and key in defaults:
            merged[key] = defaults[key]
    return merged


def load_manifest(
    path: str = DEFAULT_MANIFEST,
    *,
    corpus_dir: str = CORPUS_DIR,
    required_ids: tuple[str, ...] | None = None,
) -> Manifest:
    with open(path) as fh:
        raw = json.load(fh)
    _require(raw.get("schema") == MANIFEST_SCHEMA, f"manifest schema must be {MANIFEST_SCHEMA}")
    _require(isinstance(raw.get("corpus_version"), str), "corpus_version must be a string")
    defaults = raw.get("defaults") or {}
    rows = raw.get("fixtures")
    _require(isinstance(rows, list) and rows, "fixtures must be a non-empty list")

    fixtures: list[Fixture] = []
    seen: set[str] = set()
    for row in rows:
        merged = _merge_defaults(row, defaults)
        fid = merged.get("id")
        _require(isinstance(fid, str) and fid, "every fixture needs an id")
        _require(fid not in seen, f"duplicate fixture id {fid}")
        seen.add(fid)
        status = merged.get("status")
        _require(status in STATUSES, f"{fid}: status must be one of {STATUSES}")
        for key in ("attack", "spec_ref", "closing_leaf", "setup", "teardown"):
            _require(isinstance(merged.get(key), str) and merged.get(key), f"{fid}: {key} is required")
        routes = merged.get("routes")
        _require(isinstance(routes, list) and routes, f"{fid}: routes must be a non-empty list")
        languages = merged.get("languages") or []
        _require(all(l in KNOWN_LANGUAGES for l in languages), f"{fid}: unknown language in {languages}")
        _require(isinstance(merged.get("destructive"), bool), f"{fid}: destructive must be a bool")
        _require(isinstance(merged.get("environment_sensitive"), bool), f"{fid}: environment_sensitive must be a bool")
        _require(isinstance(merged.get("control"), str) and merged.get("control"), f"{fid}: control is required")

        module = merged.get("module")
        expected = merged.get("expected") or {}
        if status == "contained":
            _require(isinstance(module, str) and module, f"{fid}: a contained fixture needs a module")
            mod_path = os.path.join(corpus_dir, module + ".py")
            _require(os.path.exists(mod_path), f"{fid}: module {module}.py is missing from {corpus_dir}")
            _require(set(expected) == set(TARGETS), f"{fid}: expected must cover targets {TARGETS}")
            for target, value in expected.items():
                _require(value in ("contained", "not-applicable"), f"{fid}: bad expected {value} for {target}")
        elif status == "pending":
            _require(not module, f"{fid}: a pending fixture must not carry a module (decision D4)")
            _require(not expected, f"{fid}: a pending fixture has no expected outcomes")
        else:  # not-applicable
            _require(not module or isinstance(module, str), f"{fid}: bad module")
            _require(isinstance(merged.get("reason"), str) and merged.get("reason"), f"{fid}: not-applicable needs a reason")

        fixtures.append(
            Fixture(
                id=fid,
                attack=merged["attack"],
                spec_ref=merged["spec_ref"],
                status=status,
                closing_leaf=merged["closing_leaf"],
                routes=list(routes),
                languages=list(languages),
                control=merged["control"],
                destructive=bool(merged["destructive"]),
                environment_sensitive=bool(merged["environment_sensitive"]),
                setup=merged["setup"],
                teardown=merged["teardown"],
                module=module,
                expected=dict(expected),
                reason=merged.get("reason", ""),
                guarantee=merged.get("guarantee", ""),
            )
        )

    required = set(required_ids if required_ids is not None else REQUIRED_IDS)
    missing = required - seen
    extra = seen - required
    _require(not missing, f"manifest is missing fixture rows: {sorted(missing)}")
    _require(not extra, f"manifest has unknown fixture rows: {sorted(extra)}")

    return Manifest(
        corpus_version=raw["corpus_version"],
        audited_revision=raw.get("audited_revision", ""),
        defaults=defaults,
        fixtures=fixtures,
    )


@dataclass
class Skip:
    id: str
    target: str
    owner: str
    expiry: _dt.date
    reason: str


def load_skip_ledger(
    path: str = DEFAULT_SKIP_LEDGER,
    *,
    manifest: Manifest | None = None,
    today: _dt.date | None = None,
) -> list[Skip]:
    """Load the skip ledger and enforce it. An entry without an owner or a
    parseable expiry, an expired entry, or an entry for a fixture the
    manifest does not carry fails the lane."""
    today = today or _dt.date.today()
    with open(path) as fh:
        raw = json.load(fh)
    _require(raw.get("schema") == SKIP_LEDGER_SCHEMA, f"skip ledger schema must be {SKIP_LEDGER_SCHEMA}")
    entries = raw.get("skips")
    _require(isinstance(entries, list), "skips must be a list")
    known = {f.id for f in manifest.fixtures} if manifest else None
    out: list[Skip] = []
    for entry in entries:
        for key in ("id", "target", "owner", "expiry", "reason"):
            _require(isinstance(entry.get(key), str) and entry.get(key), f"skip entry needs {key}")
        try:
            expiry = _dt.date.fromisoformat(entry["expiry"])
        except ValueError as err:
            raise ManifestError(f"skip {entry['id']}: bad expiry {entry['expiry']!r}") from err
        _require(expiry >= today, f"skip {entry['id']} expired on {expiry.isoformat()}")
        _require(entry["target"] in TARGETS, f"skip {entry['id']}: unknown target {entry['target']}")
        if known is not None:
            _require(entry["id"] in known, f"skip {entry['id']}: not a fixture in the manifest")
        out.append(Skip(entry["id"], entry["target"], entry["owner"], expiry, entry["reason"]))
    return out
