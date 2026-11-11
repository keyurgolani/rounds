"""Snapshot creation and server PDF never reach PocketBase as the superuser
(ROUNDS-00A-L04). The runner's snapshot module and the PDF router read,
create, and render with the caller's bearer, and PocketBase's own rules
decide what that bearer sees. This parses both and fails on any import,
name, attribute, or string that would reach a superuser helper or
credential, with the same check the share capability modules pass."""
from __future__ import annotations

import pytest

from tests.test_share_admin_helper_ban import BACKEND, offences

MODULES = ("app/legacy_snapshots.py", "routers/pdf.py")


@pytest.mark.parametrize("path", MODULES)
def test_no_snapshot_or_render_module_reaches_a_superuser_helper(path):
    assert offences((BACKEND / path).read_text()) == []


def test_the_check_reads_the_modules_the_render_path_uses():
    from app import legacy_snapshots
    from routers import pdf

    assert pdf.legacy_snapshots is legacy_snapshots
    assert {"markup_for_render", "read_markup", "create"} <= set(dir(legacy_snapshots))
