"""Load and validate the corpus manifest, each fixture's spec, and the
skip ledger.

The manifest lists every fixture by id and family, and nothing else. A
fixture's detail lives in its module under ``corpus/``, as the module's
``SPEC``: the routes it must exercise, its sub-cases, the expected
outcome per target, its languages, the named negative control, setup,
teardown, and the ``destructive`` and ``environment_sensitive`` flags.
The validator reads each ``SPEC`` as a literal, without importing the
module, and fails if a row is missing, carries more than its id and
family, or names the wrong family; if a module names no row; or if a
spec is malformed (#8 acceptance criteria). A fixture without a module
isn't run, and the receipt records it as ``not-run``.

The skip ledger carries an owner and an expiry for every skip. An
expired skip fails the lane, and a skip for an unknown fixture fails it
too (#8 acceptance criteria). At stage 1 the ledger is empty; the
structure and its rules ship so a later skip lands with its disposition.
"""
from __future__ import annotations

import ast
import datetime as _dt
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any

from .outcomes import EXPECTATIONS, Outcome

MANIFEST_SCHEMA = "containment-corpus-manifest/v2"
SKIP_LEDGER_SCHEMA = "containment-corpus-skip-ledger/v1"

TARGETS = ("ci", "compose", "k8s")
KNOWN_LANGUAGES = ("python", "javascript", "typescript")
# A fixture's family is its id's prefix.
FAMILIES = {"EX": "execution", "FG": "grading", "RD": "render"}

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

# What the manifest may hold: framework settings at the top, and an id and
# a family per row. Anything else about a fixture belongs in its module.
MANIFEST_KEYS = frozenset({"schema", "corpus_version", "audited_revision", "targets", "defaults", "fixtures"})
DEFAULT_KEYS = frozenset({"schemas", "contract_revisions", "environment", "retained_evidence"})
ROW_KEYS = frozenset({"id", "family"})
# What a module's SPEC holds. ``reason`` belongs only to a spec with no
# sub-cases, which reports one outcome for the whole fixture.
SPEC_KEYS = frozenset({
    "routes", "subcases", "expected", "languages", "control", "setup", "teardown", "destructive",
    "environment_sensitive",
})

_ID = re.compile(r"^(EX|FG|RD)-[0-9]{2}$")
_SUBCASE_ID = re.compile(r"^(EX|FG|RD)-[0-9]{2}\.[a-z0-9-]+$")
# A fixture module is named for its id: ex_01_anonymous.py is EX-01's.
_MODULE = re.compile(r"^(ex|fg|rd)_([0-9]{2})(?:_[a-z0-9_]+)?$")

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MANIFEST = os.path.join(_HERE, "manifest.json")
DEFAULT_SKIP_LEDGER = os.path.join(_HERE, "skip_ledger.json")
CORPUS_DIR = os.path.join(_HERE, "corpus")


class ManifestError(ValueError):
    """A malformed manifest, fixture spec, or skip ledger. Fails the lane."""


@dataclass
class Fixture:
    id: str
    family: str
    # The rest comes from the module's SPEC; a fixture without a module
    # has none of it and isn't run.
    module: str | None = None
    routes: list[str] = field(default_factory=list)
    subcases: list[str] = field(default_factory=list)
    expected: dict[str, str] = field(default_factory=dict)
    languages: list[str] = field(default_factory=list)
    control: str = ""
    setup: str = ""
    teardown: str = ""
    destructive: bool = False
    environment_sensitive: bool = False
    reason: str = ""

    @property
    def runnable(self) -> bool:
        return self.module is not None

    def expectation(self, target: str) -> str:
        default = Outcome.CONTAINED.value if self.subcases else Outcome.NOT_APPLICABLE.value
        return self.expected.get(target, default)


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

    def runnable(self) -> list[Fixture]:
        return [f for f in self.fixtures if f.runnable]

    def not_run(self) -> list[Fixture]:
        return [f for f in self.fixtures if not f.runnable]


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ManifestError(msg)


def _rows(raw: Any) -> list[tuple[str, str]]:
    """(id, family) per row. A row is its id and family and nothing else."""
    _require(isinstance(raw, list) and raw, "fixtures must be a non-empty list")
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for row in raw:
        _require(isinstance(row, dict), "each fixture row is an object")
        fid = row.get("id")
        _require(isinstance(fid, str) and bool(_ID.match(fid)), "every fixture row needs an id like EX-01")
        extra = sorted(set(row) - ROW_KEYS)
        _require(not extra, f"{fid}: a row carries only its id and family, not {extra}")
        _require(fid not in seen, f"duplicate fixture id {fid}")
        seen.add(fid)
        family = FAMILIES[fid[:2]]
        _require(row.get("family") == family, f"{fid}: family must be {family}")
        out.append((fid, family))
    return out


def _modules(corpus_dir: str) -> dict[str, str]:
    """Fixture id -> module name, for every fixture module in ``corpus_dir``."""
    out: dict[str, str] = {}
    for name in sorted(os.listdir(corpus_dir)):
        stem, ext = os.path.splitext(name)
        if ext != ".py" or stem.startswith("_"):
            continue
        match = _MODULE.match(stem)
        _require(match is not None, f"{name} names no fixture: a fixture module is named for its id, as ex_01_*.py")
        fid = f"{match.group(1).upper()}-{match.group(2)}"
        _require(fid not in out, f"{fid} has two modules: {out.get(fid)}.py and {name}")
        out[fid] = stem
    return out


def _read_spec(path: str, where: str) -> Any:
    """The module's ``SPEC``, read as a literal; the module isn't imported."""
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=path)
    values = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "SPEC" for t in node.targets):
            values.append(node.value)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "SPEC":
            values.append(node.value)
    _require(len(values) == 1 and values[0] is not None, f"{where}: the module sets SPEC once, at module level")
    try:
        return ast.literal_eval(values[0])
    except (ValueError, TypeError, SyntaxError) as err:
        raise ManifestError(f"{where}: SPEC must be a literal") from err


def _fixture(fid: str, family: str, module: str, spec: Any) -> Fixture:
    where = f"{fid} ({module}.py)"
    _require(isinstance(spec, dict), f"{where}: SPEC must be a dict")
    missing = sorted(SPEC_KEYS - set(spec))
    unknown = sorted(set(spec) - SPEC_KEYS - {"reason"})
    _require(not missing, f"{where}: SPEC is missing {missing}")
    _require(not unknown, f"{where}: SPEC has unknown keys {unknown}")

    routes = spec["routes"]
    _require(isinstance(routes, list) and bool(routes) and all(isinstance(r, str) and r for r in routes),
             f"{where}: routes must be a non-empty list")
    subcases = spec["subcases"]
    _require(isinstance(subcases, list), f"{where}: subcases must be a list")
    for sid in subcases:
        _require(isinstance(sid, str) and bool(_SUBCASE_ID.match(sid)) and sid.startswith(fid + "."),
                 f"{where}: sub-case ids start with {fid}.")
    _require(len(subcases) == len(set(subcases)), f"{where}: duplicate sub-case id")
    expected = spec["expected"]
    _require(isinstance(expected, dict) and set(expected) == set(TARGETS),
             f"{where}: expected must cover targets {TARGETS}")
    for target, value in expected.items():
        _require(value in EXPECTATIONS, f"{where}: bad expected {value} for {target}")
    languages = spec["languages"]
    _require(isinstance(languages, list) and all(l in KNOWN_LANGUAGES for l in languages),
             f"{where}: unknown language in {languages}")
    for key in ("control", "setup", "teardown"):
        _require(isinstance(spec[key], str) and bool(spec[key]), f"{where}: {key} is required")
    for key in ("destructive", "environment_sensitive"):
        _require(isinstance(spec[key], bool), f"{where}: {key} must be a bool")

    if subcases:
        _require("reason" not in spec, f"{where}: only a spec with no sub-cases gives a reason")
    else:
        # No sub-case: the fixture reports one outcome for the whole row, a
        # surface this branch doesn't have yet, so it expects not-applicable.
        _require(all(v == Outcome.NOT_APPLICABLE.value for v in expected.values()),
                 f"{where}: a spec with no sub-cases expects not-applicable on every target")
        _require(isinstance(spec.get("reason"), str) and bool(spec.get("reason")),
                 f"{where}: a spec with no sub-cases needs a reason")

    return Fixture(
        id=fid,
        family=family,
        module=module,
        routes=list(routes),
        subcases=list(subcases),
        expected=dict(expected),
        languages=list(languages),
        control=spec["control"],
        setup=spec["setup"],
        teardown=spec["teardown"],
        destructive=spec["destructive"],
        environment_sensitive=spec["environment_sensitive"],
        reason=spec.get("reason", ""),
    )


def load_manifest(
    path: str = DEFAULT_MANIFEST,
    *,
    corpus_dir: str = CORPUS_DIR,
    required_ids: tuple[str, ...] | None = None,
) -> Manifest:
    with open(path) as fh:
        raw = json.load(fh)
    _require(isinstance(raw, dict), "the manifest is an object")
    _require(raw.get("schema") == MANIFEST_SCHEMA, f"manifest schema must be {MANIFEST_SCHEMA}")
    unknown = sorted(set(raw) - MANIFEST_KEYS)
    _require(not unknown, f"manifest has unknown keys: {unknown}")
    _require(isinstance(raw.get("corpus_version"), str), "corpus_version must be a string")
    defaults = raw.get("defaults") or {}
    _require(isinstance(defaults, dict), "defaults must be an object")
    unknown = sorted(set(defaults) - DEFAULT_KEYS)
    _require(not unknown, f"defaults hold framework settings only, not {unknown}")

    rows = _rows(raw.get("fixtures"))
    seen = {fid for fid, _ in rows}
    required = set(required_ids if required_ids is not None else REQUIRED_IDS)
    missing = required - seen
    extra = seen - required
    _require(not missing, f"manifest is missing fixture rows: {sorted(missing)}")
    _require(not extra, f"manifest has unknown fixture rows: {sorted(extra)}")

    modules = _modules(corpus_dir)
    orphans = sorted(f"{modules[fid]}.py" for fid in set(modules) - seen)
    _require(not orphans, f"fixture modules without a manifest row: {orphans}")

    fixtures: list[Fixture] = []
    for fid, family in rows:
        module = modules.get(fid)
        if module is None:
            fixtures.append(Fixture(id=fid, family=family))
            continue
        where = f"{fid} ({module}.py)"
        spec = _read_spec(os.path.join(corpus_dir, module + ".py"), where)
        fixtures.append(_fixture(fid, family, module, spec))

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
