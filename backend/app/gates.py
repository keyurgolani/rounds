"""Gate registry (ROUNDS-00A-L01).

Each gate is an environment variable ``ROUNDS_GATE_<NAME>`` with a
written default that keeps current behavior. Compose reads the values
from the root ``.env``; k8s reads them from the ``rounds-gates``
ConfigMap. A process reads its gates once at startup, so a flip needs
a restart, and the startup log lists every value it read.

Three readers share these keys: the runner (this module), PocketBase
(``pocketbase/pb_hooks/gates.js``), and the SPA through
``runtime-config.js`` (``frontend/src/lib/gateRegistry.json``).
``backend/tests/test_gates.py`` keeps the three in step.

Resolution, the same in all three readers:

1. ``ROUNDS_GATE_<NAME>`` set to an allowed value wins.
2. Set to anything else, the gate takes its most restrictive value
   (``closed``) and the reader logs an error without the raw value.
3. Unset or empty, the reader's own alias applies when it is truthy
   (``true``, ``1``, or ``yes``). The signup pair are aliases of
   ``SIGNUPS``: PocketBase reads ``ROUNDS_DISABLE_SIGNUPS`` and the
   SPA reads ``VITE_DISABLE_SIGNUPS``, as each does today.
   ``ROUNDS_ENABLE_DEMO`` is PocketBase's alias of ``DEMO``.
   ``ROUNDS_DISABLE_PUBLIC_SHARES`` is the runner's alias of
   ``PUBLIC_SHARES`` and fails closed: any value but an off word
   (``false``, ``0``, ``no``, ``off``, or empty) applies it.
4. Otherwise the written default applies.

Admission (``app/admission.py``) enforces the route gates and
``EXECUTION_DEFINITIONS`` and runs steps 6 and 7 as
``ENFORCE_IDEMPOTENCY`` and ``ENFORCE_QUOTA`` say, the AI router reads
``PAPER_FETCH`` and ``PROVIDER_PRIVATE_NETWORK``, PocketBase and the
SPA read ``SIGNUPS``, and PocketBase reads ``DEMO``. ``EXECUTION_STORE``
turns on the execution job store (ROUNDS-00A-L03): PocketBase serves its
hook routes and each runner replica runs its executor and reaper.
``EXECUTION_SCRATCH`` moves run, evaluate, run-project, and take-home run
onto it, and ``EXECUTION_GRADING`` moves grade, take-home submit, and their
reviews; ``execution/keys.py`` gives both effective values. The share routes
read ``PUBLIC_SHARES`` and ``SHARE_CAPABILITY_RESOLUTION``
on each request (ROUNDS-00B-L03); the startup log still lists both.

The two enforcement gates start at ``observe``: admission records what
it would deny and denies nothing. The next ``v*`` release sets them to
``enforce``.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Mapping

from app import obs

PREFIX = "ROUNDS_GATE_"
TRUTHY = ("true", "1", "yes")
# The values that leave a fail-closed alias off; any other applies it.
OFF_WORDS = ("", "false", "0", "no", "off")

RUNNER = "runner"
POCKETBASE = "pocketbase"
FRONTEND = "frontend"

ROUTE_VALUES = ("enabled", "disabled")
ENFORCEMENT_VALUES = ("off", "observe", "enforce")
# ROUNDS-00A-L02: legacy loads what runs from PocketBase as #1 stage 2
# does, enforce takes only definition requests, and disabled turns the
# six execution routes off.
DEFINITION_VALUES = ("legacy", "enforce", "disabled")
# ROUNDS-00A-L03: off until an operator turns the job store on.
STORE_VALUES = ("off", "on")
# ROUNDS-00A-L03 PR 2: legacy runs the four scratch routes in their
# request as before, on runs them as jobs, and off turns them off. PR 3's
# grading key takes the same three.
SCRATCH_VALUES = ("legacy", "on", "off")

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Alias:
    """A legacy variable one reader still honors when the gate is unset.

    An alias applies when it holds a truthy word. A fail-closed alias, an
    emergency switch, applies when it holds anything but an off word
    (OFF_WORDS), so a mistyped value still turns the thing off.
    """

    env: str
    value: str
    reader: str
    fail_closed: bool = False


@dataclass(frozen=True)
class Gate:
    name: str
    values: tuple[str, ...]
    default: str
    closed: str
    readers: frozenset[str]
    description: str
    route: str | None = None
    aliases: tuple[Alias, ...] = field(default=())

    @property
    def env(self) -> str:
        return PREFIX + self.name


@dataclass(frozen=True)
class Resolved:
    value: str
    source: str  # default, env, alias, or invalid


def _route_gate(name: str, route: str) -> Gate:
    return Gate(
        name=name,
        values=ROUTE_VALUES,
        default="enabled",
        closed="disabled",
        readers=frozenset({RUNNER}),
        description=f"Serves {route}; disabled answers 503 route_disabled.",
        route=route,
    )


REGISTRY: tuple[Gate, ...] = (
    _route_gate("RUN", "/api/run"),
    _route_gate("EVALUATE", "/api/evaluate"),
    _route_gate("AI_CODING_RUN_PROJECT", "/api/ai-coding/run-project"),
    _route_gate("AI_CODING_GRADE", "/api/ai-coding/grade"),
    _route_gate("TAKE_HOME_RUN", "/api/take-home/run"),
    _route_gate("TAKE_HOME_SUBMIT", "/api/take-home/submit"),
    _route_gate("PDF_RENDER", "/api/pdf/render"),
    _route_gate("PDF_HEALTH", "/api/pdf/health"),
    _route_gate("ATS_RULE", "/api/ai/ats-rule"),
    Gate(
        name="PAPER_FETCH",
        values=ROUTE_VALUES,
        default="disabled",
        closed="disabled",
        readers=frozenset({RUNNER}),
        description="Lets /api/ai/improve fetch a publication's paper_url.",
    ),
    Gate(
        name="PROVIDER_PRIVATE_NETWORK",
        values=ROUTE_VALUES,
        default="disabled",
        closed="disabled",
        readers=frozenset({RUNNER}),
        description=(
            "Lets an AI provider base URL reach a private address (RFC 1918, "
            "RFC 6598, or IPv6 ULA), for a model server on the operator's LAN."
        ),
    ),
    Gate(
        name="ENFORCE_IDEMPOTENCY",
        values=ENFORCEMENT_VALUES,
        default="observe",
        closed="enforce",
        readers=frozenset({RUNNER}),
        description="Idempotency-Key checks on admitted routes.",
    ),
    Gate(
        name="ENFORCE_QUOTA",
        values=ENFORCEMENT_VALUES,
        default="observe",
        closed="enforce",
        readers=frozenset({RUNNER}),
        description="Account, deployment, and demo quotas on admitted routes.",
    ),
    Gate(
        name="EXECUTION_DEFINITIONS",
        values=DEFINITION_VALUES,
        default="legacy",
        closed="disabled",
        # The SPA reads it too, so its request shapes match the runner's.
        readers=frozenset({RUNNER, FRONTEND}),
        description=(
            "Where the six execution routes get what they run: legacy loads it from "
            "PocketBase as stage 2 does; enforce runs only the compiled server-owned "
            "definitions and refuses older request shapes; disabled answers 503 "
            "definitions_disabled."
        ),
    ),
    Gate(
        name="EXECUTION_STORE",
        values=STORE_VALUES,
        default="off",
        closed="off",
        readers=frozenset({RUNNER, POCKETBASE}),
        description=(
            "The execution job store: on, PocketBase serves the hook routes under "
            "/api/rounds/execution/ and each runner replica runs its executor and reaper."
        ),
    ),
    Gate(
        name="EXECUTION_SCRATCH",
        values=SCRATCH_VALUES,
        default="legacy",
        closed="off",
        readers=frozenset({RUNNER}),
        description=(
            "Run, evaluate, run-project, and take-home run: legacy runs each in its request as before; on runs "
            "each as a durable job, and acts as off unless EXECUTION_STORE is on and EXECUTION_DEFINITIONS is "
            "enforce; off answers 503 execution_disabled and keeps every draft."
        ),
    ),
    Gate(
        name="EXECUTION_GRADING",
        values=SCRATCH_VALUES,
        default="legacy",
        closed="off",
        readers=frozenset({RUNNER}),
        description=(
            "Grade, take-home submit, and their review routes: legacy grades each in its request as before; on "
            "grades each as a durable job whose graded row the server writes, reviewed once per result, and acts "
            "as off unless EXECUTION_STORE is on and EXECUTION_DEFINITIONS is enforce; off answers 503 "
            "execution_disabled and keeps every draft."
        ),
    ),
    Gate(
        # ROUNDS-00A-L04: Legacy Artifact Snapshot creation. Off by default;
        # the runner route and the PocketBase hook both check it, and both
        # answer 503 route_disabled while it is off. Turn it on only after
        # the signed scan (docs/operations.md#legacy-artifact-snapshots).
        name="LEGACY_SNAPSHOT_CREATE",
        values=ROUTE_VALUES,
        default="disabled",
        closed="disabled",
        readers=frozenset({RUNNER, POCKETBASE}),
        description=(
            "Lets an account create Legacy Artifact Snapshots of its own resumes "
            "and variants (/api/pdf/snapshots); disabled answers 503 route_disabled."
        ),
        route="/api/pdf/snapshots",
    ),
    Gate(
        # ROUNDS-00B-L03: the emergency switch for every public share read,
        # the share link read and the capability resolver. Both read it on
        # each request. Its alias fails closed: any value but an off word
        # turns public reads off.
        name="PUBLIC_SHARES",
        values=ROUTE_VALUES,
        default="enabled",
        closed="disabled",
        readers=frozenset({RUNNER}),
        description=(
            "Public share reads, the share link read and the capability resolver; disabled answers each with "
            "the uniform not-found before any lookup."
        ),
        aliases=(Alias(env="ROUNDS_DISABLE_PUBLIC_SHARES", value="disabled", reader=RUNNER, fail_closed=True),),
    ),
    Gate(
        # ROUNDS-00B-L03 stage 2 and ROUNDS-00B-L04: capability resolution,
        # CreateShare, and rotation. Read on each request, like the switch
        # above, and by the SPA, so the share dialog matches the runner.
        # Closed by default: until the owner opens it, no share link
        # resolves and none is made (ROUNDS-00B-L06), so a deploy changes
        # nothing about who can read a link.
        name="SHARE_CAPABILITY_RESOLUTION",
        values=ROUTE_VALUES,
        default="disabled",
        closed="disabled",
        readers=frozenset({RUNNER, FRONTEND}),
        description=(
            "Lets POST /api/share/resolve look a share capability up, and makes POST /api/share CreateShare with "
            "rotation on; disabled answers the uniform not-found before any lookup and makes no link."
        ),
    ),
    Gate(
        name="SIGNUPS",
        values=ROUTE_VALUES,
        default="enabled",
        closed="disabled",
        readers=frozenset({POCKETBASE, FRONTEND}),
        description="New account signups.",
        aliases=(
            Alias(env="ROUNDS_DISABLE_SIGNUPS", value="disabled", reader=POCKETBASE),
            Alias(env="VITE_DISABLE_SIGNUPS", value="disabled", reader=FRONTEND),
        ),
    ),
    # ROUNDS-00B-L07: the demo is off unless an operator opts in.
    Gate(
        name="DEMO",
        values=ROUTE_VALUES,
        default="disabled",
        closed="disabled",
        readers=frozenset({POCKETBASE}),
        description=(
            "The demo account (users.is_demo). Disabled, PocketBase refuses its sign-in and gives it a "
            "random password and a new token key at every start."
        ),
        aliases=(Alias(env="ROUNDS_ENABLE_DEMO", value="enabled", reader=POCKETBASE),),
    ),
)

BY_NAME: dict[str, Gate] = {g.name: g for g in REGISTRY}


def resolve(gate: Gate, environ: Mapping[str, str], reader: str) -> Resolved:
    raw = (environ.get(gate.env) or "").strip().lower()
    if raw:
        if raw in gate.values:
            return Resolved(raw, "env")
        return Resolved(gate.closed, "invalid")
    for alias in gate.aliases:
        if alias.reader != reader:
            continue
        word = (environ.get(alias.env) or "").strip().lower()
        if (word not in OFF_WORDS) if alias.fail_closed else (word in TRUTHY):
            return Resolved(alias.value, "alias")
    return Resolved(gate.default, "default")


def load(environ: Mapping[str, str] | None = None, reader: str = RUNNER) -> dict[str, Resolved]:
    """Resolve every gate ``reader`` reads, in registry order."""
    env = os.environ if environ is None else environ
    return {g.name: resolve(g, env, reader) for g in REGISTRY if reader in g.readers}


_snapshot: dict[str, Resolved] | None = None


def init(environ: Mapping[str, str] | None = None) -> dict[str, Resolved]:
    """Read the runner's gates and log every value. Runs at startup."""
    global _snapshot
    _snapshot = load(environ, RUNNER)
    for name, resolved in _snapshot.items():
        if resolved.source == "invalid":
            _log.error(
                "%s%s has an invalid value; using %r until it is fixed.",
                PREFIX,
                name,
                resolved.value,
            )
    obs.emit(
        "gates",
        service=RUNNER,
        gates={n: {"value": r.value, "source": r.source} for n, r in _snapshot.items()},
    )
    return _snapshot


def snapshot() -> Mapping[str, Resolved]:
    return _snapshot if _snapshot is not None else init()


def value(name: str) -> str:
    return snapshot()[name].value


def route_enabled(name: str) -> bool:
    return value(name) == "enabled"
