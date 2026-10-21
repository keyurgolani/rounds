"""The runner and PocketBase decide the tier alike (ROUNDS-00B-L07 stage 1).

Every demo check in PocketBase asks tierOf() in
pocketbase/pb_hooks/admission.js, and the runner's admission asks
tier_of() in app/admission.py. Both read is_demo until stage 2 repoints
them at account_system_state, and this keeps them in step."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from app import admission

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / "pocketbase" / "pb_hooks"

# The shapes an auth record's is_demo takes: PocketBase's bool field, and
# a record that has none.
RECORDS = [{"is_demo": True}, {"is_demo": False}, {}]

SCRIPT = r"""
const path = require("path");
const [hooksDir, raw] = process.argv.slice(1);
globalThis.BadRequestError = class BadRequestError extends Error {};
globalThis.UnauthorizedError = class UnauthorizedError extends Error {};
const admission = require(path.join(hooksDir, "admission.js"));
// A stored bool reads back through getBool.
const record = (fields) => ({ getBool: (name) => fields[name] === true });
process.stdout.write(JSON.stringify(JSON.parse(raw).map((fields) => admission.tierOf(record(fields)))));
"""


@pytest.fixture(scope="module")
def pocketbase_tiers() -> list[str]:
    node = shutil.which("node")
    assert node, "node is required for the PocketBase hook checks; CI installs it"
    res = subprocess.run([node, "-e", SCRIPT, str(HOOKS), json.dumps(RECORDS)], capture_output=True, text=True,
                         timeout=60, check=True)
    return json.loads(res.stdout)


def test_the_runner_and_pocketbase_decide_the_tier_alike(pocketbase_tiers):
    assert pocketbase_tiers == [admission.tier_of(record) for record in RECORDS] == ["demo", "standard", "standard"]


def test_every_demo_check_in_pocketbase_asks_the_one_accessor():
    source = (HOOKS / "demo.js").read_text()
    assert "require(`${__hooks}/admission.js`).tierOf(record)" in source
    # Nothing in the demo hooks reads is_demo past the accessor, except the
    # boot query that finds the candidates it then asks about.
    assert 'getBool("is_demo")' not in source
    assert re.findall(r'"[^"\n]*is_demo[^"\n]*"', source) == ['"is_demo = true"']
