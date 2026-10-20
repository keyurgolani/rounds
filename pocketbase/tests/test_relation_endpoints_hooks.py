"""Relation endpoint predicate unit vectors (ROUNDS-00B-L02).

The decision logic in pb_hooks/relation_endpoints.js (idsOf, screen) is pure:
it never touches a PocketBase global, so it is require()d straight into Node
and exercised here the same way test_gates_hooks.py drives the gate hooks.

idsOf turns one raw request value into the list of ids PocketBase would read,
or null when the value cannot be an id list at all (a malformed value, which
must be denied rather than read as empty). screen walks the relation rows and
returns the first offending field, denying on a malformed value, a missing
owner, or any id whose target is owned by someone else.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1] / "pb_hooks"

HARNESS = r"""
const path = require("path");
const [hooksDir, mode, argJson] = process.argv.slice(1);
const mod = require(path.join(hooksDir, "relation_endpoints.js"));
const arg = JSON.parse(argJson);
let result;
if (mode === "idsOf") {
  result = mod.idsOf(arg.value);
} else if (mode === "screen") {
  const owners = arg.owners || {};
  const raws = arg.raws || {};
  const rawFor = (field) => (Object.prototype.hasOwnProperty.call(raws, field) ? raws[field] : []);
  const lookup = (target, id) => {
    const key = target + "\u0000" + id;
    return Object.prototype.hasOwnProperty.call(owners, key) ? owners[key] : null;
  };
  result = mod.screen(arg.rows, arg.owner, rawFor, lookup);
} else {
  throw new Error("unknown mode " + mode);
}
process.stdout.write(JSON.stringify({ result: result }));
"""


def _run(mode: str, arg: dict):
    node = shutil.which("node")
    assert node, "node is required for the relation endpoint checks; CI installs it"
    res = subprocess.run(
        [node, "-e", HARNESS, str(HOOKS), mode, json.dumps(arg)],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    return json.loads(res.stdout)["result"]


# --- idsOf ----------------------------------------------------------------
# Each case is (raw value, expected). null (Python None) means "deny": the
# value is not a valid id list.
@pytest.mark.parametrize(
    "value,expected",
    [
        (None, []),                       # unset
        ("", []),                         # cleared
        ("rec0000000000001", ["rec0000000000001"]),   # a single id
        ("[]", []),                       # empty multi-relation
        (["a", "b"], ["a", "b"]),         # a multi-relation array
        (["a", None, ""], ["a"]),         # null/empty entries drop out
        ('["a","b"]', ["a", "b"]),        # a JSON-encoded array string
        ('["a",""]', ["a"]),              # empty entry drops out of JSON array
        ('["a",1]', None),                # a non-string element: malformed
        ("a[b", None),                    # looks like an array, will not parse
        (["a", 1], None),                 # a non-string element in an array
        ([{}], None),                     # an object element
        ({}, None),                       # an object value
        (5, None),                        # a number
        (True, None),                     # a boolean
    ],
)
def test_idsOf_maps_each_raw_value(value, expected):
    assert _run("idsOf", {"value": value}) == expected


# --- screen ---------------------------------------------------------------
ROWS = [
    {"field": "campaign", "target": "campaigns"},
    {"field": "application", "target": "applications"},
]


def test_screen_passes_when_every_relation_matches_the_owner():
    owners = {"campaigns\u0000c1": "u1", "applications\u0000a1": "u1"}
    raws = {"campaign": ["c1"], "application": ["a1"]}
    assert _run("screen", {"rows": ROWS, "owner": "u1", "raws": raws, "owners": owners}) is None


def test_screen_denies_a_foreign_target():
    owners = {"campaigns\u0000c1": "u2", "applications\u0000a1": "u1"}
    raws = {"campaign": ["c1"], "application": ["a1"]}
    assert _run("screen", {"rows": ROWS, "owner": "u1", "raws": raws, "owners": owners}) == "campaign"


def test_screen_denies_a_missing_target_like_a_foreign_one():
    # c1 is not in the owner map: lookup returns null, which never equals the
    # owner, so the field is denied exactly as a foreign target would be.
    owners = {"applications\u0000a1": "u1"}
    raws = {"campaign": ["c1"], "application": ["a1"]}
    assert _run("screen", {"rows": ROWS, "owner": "u1", "raws": raws, "owners": owners}) == "campaign"


def test_screen_denies_every_relation_when_the_owner_is_missing():
    owners = {"campaigns\u0000c1": "", "applications\u0000a1": ""}
    raws = {"campaign": ["c1"], "application": ["a1"]}
    assert _run("screen", {"rows": ROWS, "owner": "", "raws": raws, "owners": owners}) == "campaign"


def test_screen_denies_a_malformed_value_without_a_lookup():
    # A value that cannot be an id list is denied on its own, before any owner
    # comparison, so a crafted body cannot slip past as empty.
    owners = {"applications\u0000a1": "u1"}
    raws = {"campaign": ['["a",1]'], "application": ["a1"]}
    assert _run("screen", {"rows": ROWS, "owner": "u1", "raws": raws, "owners": owners}) == "campaign"


def test_screen_checks_every_raw_encoding_of_a_field():
    # The plain value is clean but a second encoding carries a foreign id; both
    # are screened, so the field is still denied.
    owners = {"campaigns\u0000c1": "u1", "campaigns\u0000c2": "u2", "applications\u0000a1": "u1"}
    raws = {"campaign": ["c1", "c2"], "application": ["a1"]}
    assert _run("screen", {"rows": ROWS, "owner": "u1", "raws": raws, "owners": owners}) == "campaign"


def test_the_predicate_module_is_not_auto_loaded_as_a_hook_file():
    # PocketBase loads only *.pb.js files; the shared predicate stays a plain
    # require target for both the hook wrapper and this unit test.
    assert (HOOKS / "relation_endpoints.js").exists()
    assert not (HOOKS / "relation_endpoints.js").name.endswith(".pb.js")
    wrapper = (HOOKS / "relation_endpoints.pb.js").read_text()
    assert "require(`${__hooks}/relation_endpoints.js`)" in wrapper
