"""Server-owned definitions in the runner (ROUNDS-00A-L02).

``init()`` runs at startup: it reads ``backend/definitions/manifest.json``
(``/app/definitions`` in the image, mode 0400) and checks every stored
version's bytes against its checksum. A manifest that's missing, isn't
JSON, or isn't the manifest's shape in any way leaves the store empty, and
a file that's missing or doesn't match makes that version answer 503
``definition_integrity_mismatch``; each logs a ``definition.rejected``
line. Startup goes on either way, so legacy routes keep serving while an
operator repairs the image.

``resolve()`` turns a request's ``{track, slug, variant, version}`` into
one ``active``, checksum-verified definition, rereading its file each
time, or a typed failure:

- an unknown slug, variant, or version: 404 ``definition_not_found``,
  the same for each, so nothing tells them apart;
- a superseded version: 409 ``definition_superseded``, naming the active
  version;
- a retired version: 410 ``definition_retired``;
- a definition whose runtime this runner doesn't have: 422
  ``runtime_unsupported``, naming the variants it does have;
- a file that's gone or changed: 503 ``definition_integrity_mismatch``.

Each outcome logs ``definition.resolved`` or ``definition.rejected``
through the observability kit, with the identity, route, and code.

TODO(ROUNDS-00A-L02): step 2 resolves every request at
``ROUNDS_GATE_EXECUTION_DEFINITIONS=enforce``; until then only startup
verification and the tests call this module.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app import obs
from app.errors import TypedError

DEFINITIONS_DIR = Path(__file__).resolve().parents[1] / "definitions"
MANIFEST_NAME = "manifest.json"
TRACK_KIND = {"coding": "test-definition", "ai-coding": "harness-revision", "take-home": "harness-revision"}
LIFECYCLES = ("active", "superseded", "retired")
# Runtimes this runner can run, by runtime profile and by coding variant.
RUNTIME_PROFILES = frozenset({"python-pytest", "node-tsx", "validator-python"})
CODING_VARIANTS = frozenset({"python", "javascript"})

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Identity:
    track: str
    slug: str
    variant: str | None
    content_version: int

    def label(self) -> str:
        return f"{self.track}/{self.slug}/{self.variant or 'shared'}@{self.content_version}"


@dataclass(frozen=True)
class Entry:
    kind: str
    identity: Identity
    lifecycle: str
    path: str | None
    checksum: str | None


@dataclass(frozen=True)
class Resolved:
    identity: Identity
    checksum: str
    document: dict[str, Any]

    def receipt(self) -> dict[str, Any]:
        """What a response carries for #3 to store."""
        i = self.identity
        return {"track": i.track, "slug": i.slug, "variant": i.variant,
                "content_version": i.content_version, "checksum": self.checksum}


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _runtime_of(document: Any) -> str | None:
    """What a version needs to run: a coding variant, or a harness
    revision's runtime profile."""
    if not isinstance(document, dict):
        return None
    if document.get("schema") == "test-definition/v1":
        return f"coding:{document.get('variant')}"
    profile = document.get("runtime_profile")
    return profile if isinstance(profile, str) else None


def _supported(runtime: str | None) -> bool:
    if runtime is None:
        return False
    if runtime.startswith("coding:"):
        return runtime[len("coding:"):] in CODING_VARIANTS
    return runtime in RUNTIME_PROFILES


def _parse_entry(raw: Any) -> Entry:
    """One manifest entry, or ValueError for anything that isn't one.
    Every field's type is checked before it's compared or hashed, so a
    wrong shape is a ValueError, never a TypeError."""
    if not isinstance(raw, dict):
        raise ValueError("entry is not an object")
    kind, track, slug = raw.get("kind"), raw.get("track"), raw.get("slug")
    variant, version, lifecycle = raw.get("variant"), raw.get("content_version"), raw.get("lifecycle")
    path, checksum = raw.get("path"), raw.get("checksum")
    if not isinstance(kind, str) or not isinstance(track, str) or not isinstance(lifecycle, str):
        raise ValueError("kind, track, and lifecycle must be strings")
    if kind not in ("test-definition", "harness-revision") or track not in TRACK_KIND:
        raise ValueError("unknown kind or track")
    if not isinstance(slug, str) or not slug or not (variant is None or isinstance(variant, str)):
        raise ValueError("bad slug or variant")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1 or lifecycle not in LIFECYCLES:
        raise ValueError("bad version or lifecycle")
    if not (path is None or isinstance(path, str)) or not (checksum is None or isinstance(checksum, str)):
        raise ValueError("path and checksum must be strings")
    if (path is None) != (checksum is None) or (path is None and lifecycle != "retired"):
        raise ValueError("only a retired version may have no file")
    if path is not None and (not path.startswith("store/") or ".." in path.split("/")):
        raise ValueError("bad path")
    return Entry(kind, Identity(track, slug, variant, version), lifecycle, path, checksum)


class Store:
    """The manifest and the integrity of each stored version."""

    def __init__(self, root: Path = DEFINITIONS_DIR) -> None:
        self.root = root
        self.entries: dict[tuple[str, Identity], Entry] = {}
        self.mismatched: set[tuple[str, Identity]] = set()
        # Each verified version's runtime: a coding variant or a harness
        # revision's runtime_profile.
        self.runtimes: dict[tuple[str, Identity], str | None] = {}
        self.loaded = False

    def load(self) -> "Store":
        self.entries.clear()
        self.mismatched.clear()
        self.runtimes.clear()
        self.loaded = False
        try:
            manifest = json.loads((self.root / MANIFEST_NAME).read_bytes())
            if not isinstance(manifest, dict) or manifest.get("schema") != "definitions-manifest/v1":
                raise ValueError("not a definitions-manifest/v1")
            entries = manifest.get("entries")
            if not isinstance(entries, list):
                raise ValueError("entries is not a list")
            for raw in entries:
                entry = _parse_entry(raw)
                key = (entry.kind, entry.identity)
                if key in self.entries:
                    raise ValueError(f"{entry.identity.label()} is listed twice")
                self.entries[key] = entry
        except (OSError, ValueError, TypeError, RecursionError) as err:
            # Anything that keeps the manifest from parsing leaves no
            # definitions; it never stops the runner from starting.
            self.entries.clear()
            _log.error("definitions: manifest unusable: %s", type(err).__name__)
            obs.emit("definition.rejected", code="definition_integrity_mismatch", service="runner")
            return self
        for key, entry in self.entries.items():
            if entry.path is None:
                continue
            data = self._read(entry)
            try:
                document = json.loads(data) if data is not None else None
            except (ValueError, RecursionError):
                document = None
            if document is None:
                self.mismatched.add(key)
                obs.emit("definition.rejected", definition=entry.identity.label(),
                         code="definition_integrity_mismatch", service="runner")
                continue
            self.runtimes[key] = _runtime_of(document)
        self.loaded = True
        obs.emit("definitions.loaded", entries=len(self.entries), mismatched=len(self.mismatched), service="runner")
        return self

    def _read(self, entry: Entry) -> bytes | None:
        """The version's bytes when they match its checksum."""
        assert entry.path is not None
        try:
            data = (self.root / entry.path).read_bytes()
        except OSError:
            return None
        return data if _sha256(data) == entry.checksum else None

    def versions(self, kind: str, track: str, slug: str, variant: str | None) -> list[Entry]:
        return sorted(
            (e for (k, i), e in self.entries.items()
             if k == kind and i.track == track and i.slug == slug and i.variant == variant),
            key=lambda e: e.identity.content_version,
        )

    def resolve(self, track: str, slug: str, variant: str | None, version: int,
                route: str | None = None) -> Resolved:
        """The active definition for a request, or its typed failure."""
        kind = TRACK_KIND.get(track)
        identity = Identity(track, slug, variant, version)
        entry = self.entries.get((kind, identity)) if kind else None
        if entry is None:
            raise self._reject(identity, route, TypedError("definition_not_found"))
        if entry.lifecycle == "superseded":
            active = [e for e in self.versions(kind, track, slug, variant) if e.lifecycle == "active"]
            detail = (
                f"This version was replaced. Use version {active[-1].identity.content_version}."
                if active else None
            )
            raise self._reject(identity, route, TypedError("definition_superseded", detail))
        if entry.lifecycle == "retired":
            raise self._reject(identity, route, TypedError("definition_retired"))
        data = None if (kind, identity) in self.mismatched else self._read(entry)
        if data is None:
            self.mismatched.add((kind, identity))
            raise self._reject(identity, route, TypedError("definition_integrity_mismatch"))
        document = json.loads(data)
        if not _supported(_runtime_of(document)):
            others = sorted({
                i.variant for (k, i), e in self.entries.items()
                if k == kind and i.track == track and i.slug == slug and e.lifecycle == "active"
                and i.variant is not None and i.variant != variant
                and (k, i) not in self.mismatched and _supported(self.runtimes.get((k, i)))
            })
            detail = f"This language isn't supported here. Try {', '.join(others)}." if others else None
            raise self._reject(identity, route, TypedError("runtime_unsupported", detail))
        assert entry.checksum is not None
        obs.emit("definition.resolved", definition=identity.label(), route=route, service="runner")
        return Resolved(identity, entry.checksum, document)

    def validators(self, slug: str, version: int, checksum: str) -> dict[str, Any]:
        """A coding question's validator revision, pinned by the test
        definition that names it."""
        identity = Identity("coding", slug, None, version)
        entry = self.entries.get(("harness-revision", identity))
        data = None if entry is None or entry.checksum != checksum else self._read(entry)
        if data is None:
            raise self._reject(identity, None, TypedError("definition_integrity_mismatch"))
        return json.loads(data)

    @staticmethod
    def _reject(identity: Identity, route: str | None, err: TypedError) -> TypedError:
        obs.emit("definition.rejected", definition=identity.label(), route=route, code=err.code, service="runner")
        return err


_store: Store | None = None
_lock = threading.Lock()


def init(root: Path = DEFINITIONS_DIR) -> Store:
    """Loads and verifies the store once per process."""
    global _store
    with _lock:
        _store = Store(root).load()
        return _store


def store() -> Store:
    """The verified store, loaded on first use when startup didn't."""
    global _store
    with _lock:
        if _store is None:
            _store = Store().load()
        return _store
