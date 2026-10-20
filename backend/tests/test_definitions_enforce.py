"""The six execution routes at ROUNDS_GATE_EXECUTION_DEFINITIONS=enforce
(ROUNDS-00A-L02 step 2).

Every request names one compiled definition, and what runs, how it
scores, and what comes back are the definition's. Coding and AI-coding run
the committed store; take-home runs a test-only definition, since every
seeded assignment is retired. The forgery fixtures go through the routes:
a candidate can't report its own result, change the score, or read a
hidden file back out of a response or an attempt row.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from app import canonical, definitions, execution, gates
from routers import ai_coding, runner, take_home

BACKEND = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((BACKEND / "definitions" / "manifest.json").read_text())
HARNESS_LIB = (BACKEND / "definitions" / "harness" / "rounds_harness.py").read_text()

PYTHON_TWO_SUM = (
    "def two_sum(nums, target):\n"
    "    seen = {}\n"
    "    for i, num in enumerate(nums):\n"
    "        if target - num in seen:\n"
    "            return [seen[target - num], i]\n"
    "        seen[num] = i\n"
)
PYTHON_SEARCH = (
    "def search(nums, target):\n"
    "    lo, hi = 0, len(nums)\n"
    "    while lo < hi:\n"
    "        mid = (lo + hi) // 2\n"
    "        if nums[mid] == target:\n"
    "            return mid\n"
    "        if nums[mid] < target:\n"
    "            lo = mid + 1\n"
    "        else:\n"
    "            hi = mid\n"
    "    return -1\n"
)
JS_SEARCH = (
    "function search(nums, target) {\n"
    "  let lo = 0, hi = nums.length;\n"
    "  while (lo < hi) {\n"
    "    const mid = (lo + hi) >> 1;\n"
    "    if (nums[mid] === target) return mid;\n"
    "    if (nums[mid] < target) lo = mid + 1; else hi = mid;\n"
    "  }\n"
    "  return -1;\n"
    "}\n"
)


def ref(track: str, slug: str, variant: str, version: int = 1) -> dict:
    return {"track": track, "slug": slug, "variant": variant, "version": version}


def active_entry(receipt: dict) -> dict:
    """The manifest entry a response's receipt names; it must be active."""
    (entry,) = [
        e for e in MANIFEST["entries"]
        if (e["track"], e["slug"], e["variant"], e["content_version"])
        == (receipt["track"], receipt["slug"], receipt["variant"], receipt["content_version"])
    ]
    assert entry["lifecycle"] == "active" and entry["checksum"] == receipt["checksum"]
    return entry


def typed(res, status: int, code: str) -> dict:
    assert res.status_code == status, res.text
    body = res.json()
    assert set(body) == {"detail", "code", "correlation_id"} and body["code"] == code, body
    return body


@pytest.fixture
def gate(monkeypatch):
    def set_value(value: str) -> None:
        monkeypatch.setattr(gates, "_snapshot", gates.load({"ROUNDS_GATE_EXECUTION_DEFINITIONS": value}, gates.RUNNER))

    return set_value


@pytest.fixture
def enforce(gate):
    gate("enforce")


@pytest.fixture
def committed_store(monkeypatch):
    """The committed definitions, loaded fresh for the test."""
    monkeypatch.setattr(definitions, "_store", definitions.Store().load())


@pytest.fixture
def tripwires(monkeypatch):
    """Everything that runs code, each recorded and refused."""
    hits: list[str] = []

    def trip(name):
        def guarded(*_args, **_kwargs):
            hits.append(name)
            raise AssertionError(f"{name} ran")

        return guarded

    monkeypatch.setattr(runner, "run_one", trip("run_one"))
    monkeypatch.setattr(execution, "run_step", trip("run_step"))
    monkeypatch.setattr(execution, "grade", trip("grade"))
    monkeypatch.setattr(ai_coding, "run_project", trip("run_project"))
    monkeypatch.setattr(take_home, "run_assignment", trip("run_assignment"))
    return hits


@pytest.fixture
def no_review(monkeypatch):
    """No provider in tests: the rubric review is skipped."""

    async def unavailable(_user):
        raise RuntimeError("no provider in tests")

    monkeypatch.setattr(ai_coding, "_active_text_config", unavailable)
    monkeypatch.setattr(take_home, "_active_text_config", unavailable)


# ---- the gate ---------------------------------------------------------------------


def test_enforce_is_a_value_the_runner_and_the_spa_both_read():
    gate = gates.BY_NAME["EXECUTION_DEFINITIONS"]
    assert gate.values == ("legacy", "enforce", "disabled") and gate.default == "legacy"
    assert {gates.RUNNER, gates.FRONTEND} <= gate.readers
    resolved = gates.load({"ROUNDS_GATE_EXECUTION_DEFINITIONS": "enforce"}, gates.RUNNER)
    assert resolved["EXECUTION_DEFINITIONS"] == gates.Resolved("enforce", "env")


@pytest.mark.parametrize("raw", ["enforced", "on", "legacy-ish"])
def test_a_value_it_doesnt_know_still_closes_the_routes(raw):
    resolved = gates.load({"ROUNDS_GATE_EXECUTION_DEFINITIONS": raw}, gates.RUNNER)
    assert resolved["EXECUTION_DEFINITIONS"] == gates.Resolved("disabled", "invalid")


ROUTE_BODIES = {
    "/api/run": {"definition": ref("coding", "two-sum", "python"), "code": PYTHON_TWO_SUM, "input": {"nums": [1, 2], "target": 3}},
    "/api/evaluate": {"definition": ref("coding", "two-sum", "python"), "code": PYTHON_TWO_SUM},
    "/api/ai-coding/run-project": {"definition": ref("ai-coding", "hallucinated-http-client", "python"), "checkpoint": 0, "files": {}},
    "/api/ai-coding/grade": {"definition": ref("ai-coding", "hallucinated-http-client", "python"), "files": {}},
    "/api/take-home/run": {"definition": ref("take-home", "kv-store-py", "python"), "files": {}},
    "/api/take-home/submit": {"definition": ref("take-home", "kv-store-py", "python"), "files": {}},
}


@pytest.mark.parametrize("path", sorted(ROUTE_BODIES))
def test_disabled_turns_every_execution_route_off_before_anything(client, signed_in, gate, tripwires, pocketbase,
                                                                  admission_store, path):
    gate("disabled")
    typed(client.post(path, json=ROUTE_BODIES[path], headers=signed_in), 503, "definitions_disabled")
    assert tripwires == [] and pocketbase.calls == [] and admission_store.calls == []


# ---- older request shapes ----------------------------------------------------------

LEGACY_BODIES = [
    ("/api/run", {"question_slug": "two-sum", "language": "python", "code": "x", "input": {}}, "language"),
    ("/api/evaluate", {"question_slug": "two-sum", "code": "x", "filter": {"tags": ["basic"]}}, "filter"),
    ("/api/evaluate", {"entry": {"kind": "function", "name": "f"}, "test_cases": [], "code": "x"}, "entry"),
    ("/api/ai-coding/run-project", {"round_slug": "r", "checkpoint_index": 0, "files": {}}, "checkpoint_index"),
    ("/api/ai-coding/run-project", {"files": {}, "test_command": "pytest", "timeout_s": 30}, "test_command"),
    ("/api/ai-coding/grade", {"round_slug": "r", "files": {}}, "round_slug"),
    ("/api/take-home/run", {"assignment_slug": "a", "files": {}}, "assignment_slug"),
    ("/api/take-home/submit", {"assignment_slug": "a", "files": {}, "harness_files": []}, "assignment_slug"),
]


@pytest.mark.parametrize("path, body, field", LEGACY_BODIES)
def test_an_older_request_shape_is_rejected_by_name_before_anything(client, signed_in, enforce, tripwires,
                                                                     pocketbase, admission_store, capsys, path,
                                                                     body, field):
    out = typed(client.post(path, json=body, headers=signed_in), 422, "legacy_request_rejected")
    assert field in out["detail"] and "Reload" in out["detail"]
    assert tripwires == [] and pocketbase.calls == [] and admission_store.calls == []
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith("{")]
    (rejected,) = [x for x in lines if x.get("event") == "definition.rejected"]
    assert rejected["code"] == "legacy_request_rejected" and rejected["field"] == field


@pytest.mark.parametrize("field", ["test_command", "validators", "hidden_files", "env", "network", "limits", "image"])
def test_a_forbidden_input_next_to_a_definition_is_still_rejected(client, signed_in, enforce, tripwires, field):
    body = {**ROUTE_BODIES["/api/run"], field: "anything"}
    out = typed(client.post("/api/run", json=body, headers=signed_in), 422, "legacy_request_rejected")
    assert field in out["detail"] and tripwires == []


@pytest.mark.parametrize("path", sorted(ROUTE_BODIES))
def test_every_definition_request_refuses_an_unknown_field_before_any_lookup(client, signed_in, enforce, tripwires,
                                                                            pocketbase, capsys, path):
    body = {**ROUTE_BODIES[path], "colour": "blue"}
    typed(client.post(path, json=body, headers=signed_in), 422, "invalid_request")
    assert tripwires == [] and pocketbase.calls == []
    assert '"event":"definition.resolved"' not in capsys.readouterr().out


def test_an_input_over_its_limit_is_refused_before_anything_runs(client, signed_in, enforce, tripwires):
    body = {**ROUTE_BODIES["/api/run"], "code": "x" * (300 * 1024)}
    typed(client.post("/api/run", json=body, headers=signed_in), 413, "limit_exceeded")
    assert tripwires == []


def test_any_other_unknown_field_is_invalid(client, signed_in, enforce, tripwires):
    body = {**ROUTE_BODIES["/api/run"], "colour": "blue"}
    typed(client.post("/api/run", json=body, headers=signed_in), 422, "invalid_request")
    nested = {**ROUTE_BODIES["/api/run"], "definition": {**ref("coding", "two-sum", "python"), "checksum": "x"}}
    typed(client.post("/api/run", json=nested, headers=signed_in), 422, "invalid_request")
    assert tripwires == []


def test_a_definition_request_at_legacy_is_invalid(client, signed_in, tripwires):
    # legacy takes stage 2's shapes only, so a newer tab's request is refused.
    typed(client.post("/api/run", json=ROUTE_BODIES["/api/run"], headers=signed_in), 422, "invalid_request")
    assert tripwires == []


# ---- coding --------------------------------------------------------------------------


def test_a_run_comes_from_the_definition_and_names_it(client, signed_in, enforce, committed_store, pocketbase):
    res = client.post("/api/run", json=ROUTE_BODIES["/api/run"], headers=signed_in)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["return_value"] == [0, 1] and body["error"] is None
    active_entry(body["definition"])
    # Nothing came from PocketBase.
    assert pocketbase.calls == []


def test_an_evaluate_runs_every_case_and_its_validators_out_of_process(client, signed_in, enforce, committed_store,
                                                                       pocketbase):
    res = client.post("/api/evaluate", json=ROUTE_BODIES["/api/evaluate"], headers=signed_in)
    assert res.status_code == 200, res.text
    body = res.json()
    document = definitions.store().resolve("coding", "two-sum", "python", 1).document
    assert body["failed"] == 0 and body["passed"] == len(document["cases"])
    assert [r["case_id"] for r in body["results"]] == [c["case_id"] for c in document["cases"]]
    assert all(r["expected"] == {"$match": "validator"} for r in body["results"])
    active_entry(body["definition"])
    assert pocketbase.calls == []


def test_an_evaluate_takes_case_ids_and_tags(client, signed_in, enforce, committed_store):
    base = {"definition": ref("coding", "binary-search", "python"), "code": PYTHON_SEARCH}
    by_id = client.post("/api/evaluate", json={**base, "case_ids": ["c001", "c000"]}, headers=signed_in).json()
    assert [r["case_id"] for r in by_id["results"]] == ["c000", "c001"] and by_id["failed"] == 0
    document = definitions.store().resolve("coding", "binary-search", "python", 1).document
    tagged = {c["case_id"] for c in document["cases"] if "basic" in c["tags"]}
    by_tag = client.post("/api/evaluate", json={**base, "tags": ["basic"]}, headers=signed_in).json()
    assert {r["case_id"] for r in by_tag["results"]} == tagged
    assert by_tag["results"][0]["expected"] == document["cases"][0]["expected"]["literal"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_the_javascript_variant_runs_its_own_definition(client, signed_in, enforce, committed_store):
    body = {"definition": ref("coding", "binary-search", "javascript"), "code": JS_SEARCH}
    res = client.post("/api/evaluate", json=body, headers=signed_in)
    assert res.status_code == 200, res.text
    assert res.json()["failed"] == 0 and res.json()["definition"]["variant"] == "javascript"


def test_a_case_the_version_doesnt_have_is_case_unknown(client, signed_in, enforce, committed_store, tripwires):
    body = {**ROUTE_BODIES["/api/evaluate"], "case_ids": ["c000", "c999"]}
    typed(client.post("/api/evaluate", json=body, headers=signed_in), 422, "case_unknown")
    assert tripwires == []


@pytest.mark.parametrize(
    "definition",
    [ref("coding", "no-such-question", "python"), ref("coding", "two-sum", "java"), ref("coding", "two-sum", "python", 7),
     ref("ai-coding", "two-sum", "python")],
    ids=["slug", "variant", "version", "other-track"],
)
def test_anything_unknown_is_the_same_definition_not_found(client, signed_in, enforce, committed_store, tripwires,
                                                           definition):
    body = {**ROUTE_BODIES["/api/run"], "definition": definition}
    out = typed(client.post("/api/run", json=body, headers=signed_in), 404, "definition_not_found")
    assert out["detail"] == "This practice item isn't available."
    assert tripwires == []


# ---- the version states, on a store made for the test ---------------------------------


def _store(tmp_path: Path, entries: list[tuple[dict, dict, str]]) -> definitions.Store:
    """A definitions store holding ``(manifest entry, document, lifecycle)``."""
    manifest = {"schema": "definitions-manifest/v1", "entries": []}
    for entry, document, lifecycle in entries:
        data = canonical.canonical(document)
        path = f"store/{entry['track']}/{entry['slug']}/{entry['variant']}.v{entry['content_version']}.json"
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_bytes(data)
        manifest["entries"].append({**entry, "lifecycle": lifecycle, "path": path,
                                    "checksum": canonical.checksum_bytes(data)})
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    return definitions.Store(tmp_path).load()


def _coding(version: int) -> tuple[dict, dict]:
    document = json.loads((BACKEND / "definitions" / "store" / "coding" / "binary-search" / "python.v1.json").read_text())
    document["content_version"] = version
    entry = {"kind": "test-definition", "track": "coding", "slug": "binary-search", "variant": "python",
             "content_version": version}
    return entry, document


def test_a_superseded_version_names_the_active_one(client, signed_in, enforce, tmp_path, monkeypatch, tripwires):
    (e1, d1), (e2, d2) = _coding(1), _coding(2)
    monkeypatch.setattr(definitions, "_store", _store(tmp_path, [(e1, d1, "superseded"), (e2, d2, "active")]))
    body = {"definition": ref("coding", "binary-search", "python", 1), "code": PYTHON_SEARCH, "input": {}}
    out = typed(client.post("/api/run", json=body, headers=signed_in), 409, "definition_superseded")
    assert "version 2" in out["detail"] and tripwires == []


def test_a_retired_version_runs_nothing(client, signed_in, enforce, committed_store, tripwires, pocketbase):
    # Every seeded take-home assignment is retired.
    for path in ("/api/take-home/run", "/api/take-home/submit"):
        typed(client.post(path, json=ROUTE_BODIES[path], headers=signed_in), 410, "definition_retired")
    assert tripwires == [] and pocketbase.calls == []


def test_a_changed_file_fails_closed(client, signed_in, enforce, tmp_path, monkeypatch, tripwires):
    entry, document = _coding(1)
    store = _store(tmp_path, [(entry, document, "active")])
    (tmp_path / "store" / "coding" / "binary-search" / "python.v1.json").write_text("{}")
    monkeypatch.setattr(definitions, "_store", store)
    body = {"definition": ref("coding", "binary-search", "python"), "code": PYTHON_SEARCH, "input": {}}
    typed(client.post("/api/run", json=body, headers=signed_in), 503, "definition_integrity_mismatch")
    assert tripwires == []


def test_an_unsupported_runtime_names_the_variants_this_runner_has(client, signed_in, enforce, committed_store,
                                                                   monkeypatch, tripwires):
    monkeypatch.setattr(definitions, "CODING_VARIANTS", frozenset({"python"}))
    body = {**ROUTE_BODIES["/api/run"], "definition": ref("coding", "two-sum", "javascript")}
    out = typed(client.post("/api/run", json=body, headers=signed_in), 422, "runtime_unsupported")
    assert "python" in out["detail"] and tripwires == []


# ---- paths a submission can't carry ---------------------------------------------------


@pytest.mark.parametrize(
    "path, problem",
    [
        ("harness/users_api.py", "harness"), ("harness/anything.txt", "harness"),
        ("conftest.py", "config"), ("tests/conftest.py", "config"), ("Conftest.py", "config"),
        ("pytest.ini", "config"), ("pyproject.toml", "config"), ("setup.cfg", "config"), ("tox.ini", "config"),
        ("package.json", "config"), (".npmrc", "config"), ("tsconfig.json", "config"),
        ("node_modules/x/index.js", "config"), ("__pycache__/client.cpython-312.pyc", "config"),
        ("sitecustomize.py", "startup"), ("usercustomize.py", "startup"), ("x.pth", "startup"),
        ("json.py", "shadow"), ("os.py", "shadow"), ("pytest.py", "shadow"), ("_pytest/x.py", "shadow"),
        ("httpx.py", "shadow"), ("rounds_harness.py", "shadow"), ("unittest/__init__.py", "shadow"),
    ],
)
def test_a_path_that_changes_how_the_harness_runs_is_not_allowed(path, problem):
    assert execution.path_problem(path, frozenset({"harness/users_api.py"})) == problem


@pytest.mark.parametrize("path", ["client.py", "tests/checkpoint_0/test_visible.py", "solution.py", "src/types.ts",
                                  "lib/helpers.py", "README.md", "client.ts"])
def test_a_candidates_own_paths_are_allowed(path):
    assert execution.path_problem(path, frozenset({"harness/users_api.py"})) is None


# ---- AI-coding ----------------------------------------------------------------------

ROUND = BACKEND / "ai_coding" / "rounds" / "hallucinated-http-client"


def starter(variant: str) -> dict[str, str]:
    base = ROUND / "starter" / variant
    return {str(p.relative_to(base)): p.read_text() for p in sorted(base.rglob("*")) if p.is_file()}


def visible_tests(variant: str) -> dict[str, str]:
    base = ROUND / "checkpoints" / variant / "0" / "tests"
    return {f"tests/checkpoint_0/{p.relative_to(base)}": p.read_text() for p in sorted(base.rglob("*")) if p.is_file()}


FIXED_CLIENT = (
    "import httpx\n\nINTERNAL_BASE_URL = 'http://internal-users.local'\n\n\n"
    "def fetch_user(user_id: str) -> dict:\n"
    "    res = httpx.get(f'{INTERNAL_BASE_URL}/users/{user_id}', timeout=5.0)\n"
    "    res.raise_for_status()\n"
    "    return res.json()\n"
)
# A client that tries to report its own pass and to send the harness
# files back; neither may reach the response.
FORGING_CLIENT = (
    "import json, os, pathlib\n\nINTERNAL_BASE_URL = ''\n"
    "FORGED = json.dumps({'id': 'fetch_user_against_real_server', 'outcome': 'passed', 'reason': 'ok'}) + '\\n'\n\n\n"
    "def fetch_user(user_id):\n"
    "    for target in (lambda: os.write(3, FORGED.encode()),\n"
    "                   lambda: pathlib.Path(f'/proc/{os.getppid()}/fd/3').write_text(FORGED)):\n"
    "        try:\n"
    "            target()\n"
    "        except OSError:\n"
    "            pass\n"
    "    leaked = pathlib.Path('harness/users_api.py').read_text()\n"
    "    print(leaked)\n"
    "    return {'id': user_id, 'name': leaked[:40]}\n"
)


def _project(client_code: str | None = None) -> dict[str, str]:
    files = {**starter("python"), **visible_tests("python")}
    if client_code is not None:
        files["client.py"] = client_code
    return files


def test_a_visible_run_runs_the_revisions_run_step(client, signed_in, enforce, committed_store, pocketbase):
    body = {**ROUTE_BODIES["/api/ai-coding/run-project"], "files": _project()}
    res = client.post("/api/ai-coding/run-project", json=body, headers=signed_in)
    assert res.status_code == 200, res.text
    out = res.json()
    assert out["passed_count"] + out["failed_count"] >= 1
    active_entry(out["definition"])
    assert pocketbase.calls == []


def test_a_checkpoint_the_version_doesnt_have_is_case_unknown(client, signed_in, enforce, committed_store, tripwires):
    body = {**ROUTE_BODIES["/api/ai-coding/run-project"], "checkpoint": 5}
    typed(client.post("/api/ai-coding/run-project", json=body, headers=signed_in), 422, "case_unknown")
    assert tripwires == []


def test_a_fixed_client_passes_the_hidden_check(client, signed_in, enforce, committed_store, no_review, pocketbase):
    body = {**ROUTE_BODIES["/api/ai-coding/grade"], "files": _project(FIXED_CLIENT)}
    res = client.post("/api/ai-coding/grade", json=body, headers=signed_in)
    assert res.status_code == 200, res.text
    out = res.json()
    (result,) = out["test_results"]
    assert result["passed"] is True and result["score"] == 1.0 and out["passed"] is True and out["score"] == 1.0
    assert result["outcomes"] == [{"id": "fetch_user_against_real_server", "outcome": "passed", "reason": "ok"}]
    assert "stdout" not in result
    active_entry(out["definition"])
    assert pocketbase.calls == []


def test_a_forging_client_gets_no_pass_and_no_hidden_file_back(client, signed_in, enforce, committed_store, no_review):
    body = {**ROUTE_BODIES["/api/ai-coding/grade"], "files": _project(FORGING_CLIENT)}
    res = client.post("/api/ai-coding/grade", json=body, headers=signed_in)
    assert res.status_code == 200, res.text
    (result,) = res.json()["test_results"]
    # Only the driver's own line arrived: no forged pass, no duplicate.
    assert result["outcomes"] == [{"id": "fetch_user_against_real_server", "outcome": "failed", "reason": "assertion"}]
    assert result["passed"] is False and result["score"] == 0.0
    assert "users service" not in res.text and "ThreadingHTTPServer" not in res.text


def test_an_edited_visible_test_doesnt_change_the_grade(client, signed_in, enforce, committed_store, no_review):
    files = _project()
    files["tests/checkpoint_0/test_visible.py"] = "def test_everything():\n    assert True\n"
    res = client.post("/api/ai-coding/grade", json={**ROUTE_BODIES["/api/ai-coding/grade"], "files": files},
                      headers=signed_in)
    assert res.status_code == 200 and res.json()["test_results"][0]["passed"] is False


FIXED_TS_CLIENT = (
    "export const config = { baseUrl: 'http://internal-users.local' };\n"
    "export interface UserProfile { id: string; name: string; }\n"
    "export async function fetchUser(userId: string): Promise<UserProfile> {\n"
    "  const res = await fetch(`${config.baseUrl}/users/${userId}`);\n"
    "  if (!res.ok) throw new Error(`HTTP ${res.status}`);\n"
    "  return (await res.json()) as UserProfile;\n"
    "}\n"
)
TS_REF = ref("ai-coding", "hallucinated-http-client", "typescript")


@pytest.mark.skipif(shutil.which("tsx") is None, reason="tsx not on PATH")
def test_the_typescript_variant_runs_and_grades_through_its_python_driver(client, signed_in, enforce,
                                                                          committed_store, no_review):
    project = {**starter("typescript"), **visible_tests("typescript")}
    run = client.post("/api/ai-coding/run-project", json={"definition": TS_REF, "checkpoint": 0, "files": project},
                      headers=signed_in)
    assert run.status_code == 200, run.text
    assert run.json()["passed_count"] + run.json()["failed_count"] >= 1
    grades = {}
    for name, files in (("starter", project), ("fixed", {**project, "client.ts": FIXED_TS_CLIENT})):
        res = client.post("/api/ai-coding/grade", json={"definition": TS_REF, "files": files}, headers=signed_in)
        assert res.status_code == 200, res.text
        (result,) = res.json()["test_results"]
        grades[name] = (result["passed"], result["outcomes"][0]["outcome"])
    assert grades == {"starter": (False, "failed"), "fixed": (True, "passed")}


@pytest.mark.parametrize("extra", ["conftest.py", "tests/conftest.py", "json.py", "sitecustomize.py",
                                   "harness/users_api.py", "node_modules/x/index.js"])
def test_a_file_that_changes_how_the_grade_runs_is_refused(client, signed_in, enforce, committed_store, tripwires,
                                                           extra):
    files = {**_project(FIXED_CLIENT), extra: "x = 1\n"}
    out = typed(client.post("/api/ai-coding/grade", json={**ROUTE_BODIES["/api/ai-coding/grade"], "files": files},
                            headers=signed_in), 422, "path_not_allowed")
    # One of the fixed sentences, never the path the request sent.
    assert out["detail"] in execution.PATH_DETAILS.values()
    assert tripwires == []


# ---- take-home, on a test-only definition ---------------------------------------------

TAKE_HOME_GRADE = '''"""Grades add-numbers: the candidate's add() in a child, twice. Like
every driver, it loads what it runs before the first child."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import rounds_harness  # noqa: E402

CASES = (("adds_small", 2, 3), ("adds_large", 10**12, 7))
with open(os.path.join(HERE, "probe.py"), encoding="utf-8") as handle:
    PROBE = handle.read()


def main():
    rounds_harness.protect()
    channel = rounds_harness.Channel()
    for rid, a, b in CASES:
        child = rounds_harness.run_child(
            [sys.executable, "-I", "-c", PROBE, str(a), str(b)], cwd=os.getcwd(), timeout_s=20
        )
        if child.timed_out:
            channel.report(rid, "failed", "timeout")
        elif child.returncode != 0:
            channel.report(rid, "failed", "exception")
        else:
            answer = rounds_harness.last_json_line(child.stdout)
            if answer is None:
                channel.report(rid, "failed", "no-result")
            elif answer == {"sum": a + b}:
                channel.report(rid, "passed", "ok")
            else:
                channel.report(rid, "failed", "assertion")


main()
'''
TAKE_HOME_PROBE = '''import json
import os
import sys

sys.path.insert(0, os.getcwd())

import solution  # noqa: E402

sys.stdout.write("\\n" + json.dumps({"sum": solution.add(int(sys.argv[1]), int(sys.argv[2]))}) + "\\n")
'''
HIDDEN_MARKER = "hidden-case-notes-7c1e2b"


def _take_home_document() -> dict:
    return {
        "schema": "harness-revision/v1", "kind": "take-home", "track": "take-home", "slug": "add-numbers-py",
        "variant": "python", "content_version": 1,
        "files": [
            {"path": "harness/grade.py", "contents": TAKE_HOME_GRADE},
            {"path": "harness/probe.py", "contents": TAKE_HOME_PROBE},
            {"path": "harness/notes.txt", "contents": HIDDEN_MARKER},
            {"path": "harness/rounds_harness.py", "contents": HARNESS_LIB},
        ],
        "candidate_paths": ["solution.py"],
        "checkpoints": [{
            "index": 0, "label": "Adds numbers", "ai_allowed": False, "run": None,
            "grade": {"argv": ["python3", "-I", "harness/grade.py"], "job_class": "project", "wall_s": 60},
            "results": [{"id": "adds_small", "weight": 0.5}, {"id": "adds_large", "weight": 0.5}],
            "min_executed": 2,
        }],
        "rubric": {"items": []}, "ai_policy": "off", "runtime_profile": "python-pytest", "network": "none",
        "result_protocol": "fd3",
    }


@pytest.fixture
def take_home_store(tmp_path, monkeypatch):
    entry = {"kind": "harness-revision", "track": "take-home", "slug": "add-numbers-py", "variant": "python",
             "content_version": 1}
    monkeypatch.setattr(definitions, "_store", _store(tmp_path, [(entry, _take_home_document(), "active")]))


@pytest.fixture
def attempts(monkeypatch, pocketbase):
    """The take-home assignment's row, and every attempt submit saves."""
    pocketbase.add("take_home_assignments", slug="add-numbers-py", title="Add numbers")
    saved: list[dict] = []

    async def pb_post(_token, path, body):
        saved.append({"path": path, "body": body})
        return {"id": "a" * 15}

    monkeypatch.setattr(take_home, "pb_post", pb_post)
    return saved


TAKE_HOME_REF = ref("take-home", "add-numbers-py", "python")
HONEST = "def add(a, b):\n    return a + b\n"


def _take_home(client, signed_in, path: str, solution: str, **extra_files: str):
    files = {"solution.py": solution, **{k.replace("__", "/"): v for k, v in extra_files.items()}}
    return client.post(path, json={"definition": TAKE_HOME_REF, "files": files}, headers=signed_in)


def test_an_honest_take_home_passes_on_the_servers_score(client, signed_in, enforce, take_home_store, attempts,
                                                        no_review):
    run = _take_home(client, signed_in, "/api/take-home/run", HONEST)
    assert run.status_code == 200, run.text
    body = run.json()
    assert (body["passed"], body["score"]) == (True, 1.0)
    assert [c["id"] for c in body["criteria"]] == ["adds_small", "adds_large"] and body["stdout"] == ""
    submit = _take_home(client, signed_in, "/api/take-home/submit", HONEST)
    assert submit.status_code == 200, submit.text
    (row,) = attempts
    assert row["body"]["harness_output"]["passed"] is True and row["body"]["harness_output"]["stdout"] == ""
    assert submit.json()["definition"]["slug"] == "add-numbers-py"


def _outcomes(res) -> list[tuple[str, str, str]]:
    assert res.status_code == 200, res.text
    return [(o["id"], o["outcome"], o["reason"]) for o in res.json()["outcomes"]]


FORGERIES = {
    # The grader is killed before it reports: nothing passes.
    "reports-nothing": (
        "import os, signal\nos.kill(os.getppid(), signal.SIGKILL)\ndef add(a, b):\n    return a + b\n",
        [("adds_small", "not-run", "no-result"), ("adds_large", "not-run", "no-result")],
    ),
    # A passing line printed at exit is just output.
    "atexit-marker": (
        "import atexit, json\n"
        "atexit.register(lambda: print(json.dumps({'criteria': [], 'score': 1.0})))\n"
        "atexit.register(lambda: print(json.dumps({'sum': 0})))\n"
        "def add(a, b):\n    return 0\n",
        [("adds_small", "failed", "assertion"), ("adds_large", "failed", "assertion")],
    ),
    # A score it prints is ignored; the server weighs the one real pass.
    "out-of-range-score": (
        "import json\nprint(json.dumps({'criteria': [], 'score': 7}))\n"
        "def add(a, b):\n    return a + b if a < 100 else -1\n",
        [("adds_small", "passed", "ok"), ("adds_large", "failed", "assertion")],
    ),
    # Writing the grader's fd 3, directly or through /proc, never lands.
    "writes-fd-3": (
        "import json, os, pathlib\n"
        "line = ''.join(json.dumps({'id': i, 'outcome': 'passed', 'reason': 'ok'}) + '\\n' "
        "for i in ('adds_small', 'adds_large'))\n"
        "for target in (lambda: os.write(3, line.encode()),\n"
        "               lambda: pathlib.Path(f'/proc/{os.getppid()}/fd/3').write_text(line)):\n"
        "    try:\n        target()\n    except OSError:\n        pass\n"
        "def add(a, b):\n    return 0\n",
        [("adds_small", "failed", "assertion"), ("adds_large", "failed", "assertion")],
    ),
}


@pytest.mark.parametrize("name", sorted(FORGERIES))
def test_a_forged_take_home_result_fails_closed(client, signed_in, enforce, take_home_store, name):
    solution, expected = FORGERIES[name]
    res = _take_home(client, signed_in, "/api/take-home/run", solution)
    assert _outcomes(res) == expected
    assert res.json()["passed"] is False and 0.0 <= res.json()["score"] <= 1.0


def test_the_out_of_range_score_is_the_servers_weighting(client, signed_in, enforce, take_home_store):
    res = _take_home(client, signed_in, "/api/take-home/run", FORGERIES["out-of-range-score"][0])
    assert res.json()["score"] == 0.5


def test_an_edited_visible_test_doesnt_change_the_take_home_grade(client, signed_in, enforce, take_home_store):
    res = _take_home(client, signed_in, "/api/take-home/run", "def add(a, b):\n    return 0\n",
                     tests__test_solution_py="def test_passes():\n    assert True\n")
    assert res.json()["passed"] is False


@pytest.mark.parametrize("extra", ["conftest.py", "json.py", "harness/grade.py", "sitecustomize.py"])
def test_a_take_home_file_that_changes_the_grader_is_refused(client, signed_in, enforce, take_home_store, tripwires,
                                                             attempts, extra):
    res = client.post("/api/take-home/submit", json={"definition": TAKE_HOME_REF,
                                                     "files": {"solution.py": HONEST, extra: "x = 1\n"}},
                      headers=signed_in)
    typed(res, 422, "path_not_allowed")
    assert tripwires == [] and attempts == []


def test_a_take_home_that_prints_hidden_files_gets_none_back(client, signed_in, enforce, take_home_store, attempts,
                                                            no_review):
    leaking = (
        "import pathlib\n"
        "def add(a, b):\n"
        "    print(pathlib.Path('harness/notes.txt').read_text())\n"
        "    print(pathlib.Path('harness/grade.py').read_text())\n"
        "    return a + b\n"
    )
    run = _take_home(client, signed_in, "/api/take-home/run", leaking)
    submit = _take_home(client, signed_in, "/api/take-home/submit", leaking)
    for res in (run, submit):
        assert res.status_code == 200, res.text
        assert HIDDEN_MARKER not in res.text and "rounds_harness" not in res.text
    (row,) = attempts
    assert HIDDEN_MARKER not in json.dumps(row["body"]["harness_output"])
