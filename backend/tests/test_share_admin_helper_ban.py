"""No share capability module reaches PocketBase as the superuser
(ROUNDS-00B-L03 stage 2).

The runner reads and changes a capability only with the owner's bearer,
and from #12 with the resolver's own service identity. This parses every
share module under app/ and routers/ and fails on any import, name,
attribute, or string that would reach a superuser helper or credential.
routers/share.py is stage 1's router, which #14 replaces; it isn't one of
these modules.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
STAGE_ONE_ROUTER = BACKEND / "routers" / "share.py"
BANNED_NAMES = frozenset({"admin_token", "pb_admin_get", "pb_admin_post"})
BANNED_TEXT = ("PB_ADMIN_", "/api/admins", "_superusers")


def _modules() -> list[Path]:
    found = sorted({*BACKEND.glob("app/share*.py"), *BACKEND.glob("routers/share*.py")})
    return [path for path in found if path != STAGE_ONE_ROUTER]


def offences(source: str) -> list[str]:
    """Every way ``source`` names a superuser helper or credential."""
    out: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            out += [f"import {alias.name}" for alias in node.names
                    if alias.name.rsplit(".", 1)[-1] in BANNED_NAMES]
        elif isinstance(node, ast.Name) and node.id in BANNED_NAMES:
            out.append(f"name {node.id}")
        elif isinstance(node, ast.Attribute) and node.attr in BANNED_NAMES:
            out.append(f"attribute {node.attr}")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in BANNED_NAMES or any(text in node.value for text in BANNED_TEXT):
                out.append(f"string {node.value[:40]!r}")
    return out


def test_the_check_covers_the_capability_modules():
    names = {path.relative_to(BACKEND).as_posix() for path in _modules()}
    assert {"app/share_capabilities.py", "routers/share_capabilities.py"} <= names


@pytest.mark.parametrize("path", _modules(), ids=lambda p: p.relative_to(BACKEND).as_posix())
def test_no_share_capability_module_reaches_a_superuser_helper(path):
    assert offences(path.read_text()) == []


@pytest.mark.parametrize("snippet", [
    "from app.pb_auth import admin_token",
    "from app.pb_auth import pb_admin_get as read",
    "from app import pb_auth\npb_auth.pb_admin_post('/x', {})",
    "import app.pb_auth as p\np.admin_token()",
    "helper = getattr(__import__('app.pb_auth'), 'pb_admin_get')",
    "import os\nos.environ['PB_ADMIN_PASSWORD']",
    "url = '/api/admins/auth-with-password'",
    "url = '/api/collections/_superusers/auth-with-password'",
])
def test_the_check_catches_each_way_in(snippet):
    assert offences(snippet)


def test_the_owners_own_bearer_helpers_pass():
    assert offences("from app.pb_auth import pb_get, pb_post, POCKETBASE_URL\nfrom app import admission") == []
