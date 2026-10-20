"""Compiled server-owned definitions (ROUNDS-00A-L02): the compiler
``backend/definitions/build.py``, its committed output, and the runner's
startup check and resolver in ``app.definitions``."""
from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from app import canonical, definitions
from app.errors import CODES, TypedError
from definitions import build
from matchers import match

ROOT = Path(__file__).resolve().parents[2]
DEFINITIONS = ROOT / "backend" / "definitions"
MANIFEST = json.loads((DEFINITIONS / "manifest.json").read_text(encoding="utf-8"))
ENTRIES = MANIFEST["entries"]


def stored(entry: dict) -> dict:
    return json.loads((DEFINITIONS / entry["path"]).read_bytes())


def events(out: str, name: str) -> list[dict]:
    lines = [json.loads(line) for line in out.splitlines() if line.startswith("{")]
    return [line for line in lines if line.get("event") == name]


# ---- the committed output --------------------------------------------------------


def test_the_committed_definitions_are_what_the_sources_compile_to():
    res = subprocess.run(
        [sys.executable, str(DEFINITIONS / "build.py"), "--check"], capture_output=True, text=True, timeout=300
    )
    assert res.returncode == 0, res.stderr
    assert "471 versions, all current" in res.stdout


def test_compiling_twice_gives_the_same_bytes():
    first = build.compile_all(build.load_manifest())
    second = build.compile_all(build.load_manifest())
    assert build.manifest_text(first) == build.manifest_text(second)
    assert first.files == second.files


def test_every_stored_file_is_its_checksums_rfc_8785_bytes():
    for entry in ENTRIES:
        if entry["path"] is None:
            continue
        data = (DEFINITIONS / entry["path"]).read_bytes()
        assert canonical.checksum_bytes(data) == entry["checksum"]
        assert canonical.canonical(json.loads(data)) == data


def test_the_store_holds_each_seeded_definition_once():
    kinds: dict[tuple, int] = {}
    for e in ENTRIES:
        key = (e["kind"], e["track"], e["lifecycle"])
        kinds[key] = kinds.get(key, 0) + 1
    assert len(ENTRIES) == 471
    assert kinds == {
        ("test-definition", "coding", "active"): 450,
        ("harness-revision", "coding", "active"): 11,
        ("harness-revision", "ai-coding", "active"): 2,
        ("harness-revision", "ai-coding", "retired"): 5,
        ("harness-revision", "take-home", "retired"): 3,
    }
    identities = [(e["kind"], e["track"], e["slug"], e["variant"], e["content_version"]) for e in ENTRIES]
    assert len(identities) == len(set(identities))


def test_eleven_questions_share_fifteen_validator_predicates_across_45_cases():
    revisions = [e for e in ENTRIES if e["kind"] == "harness-revision" and e["track"] == "coding"]
    predicates = {v["predicate"] for e in revisions for v in stored(e)["validators"]}
    assert (len(revisions), len(predicates)) == (11, 15)
    for e in revisions:
        assert e["variant"] is None and e["path"].endswith("/validators.v1.json")
    cases = [
        c
        for e in ENTRIES
        if e["kind"] == "test-definition" and e["variant"] == "python"
        for c in stored(e)["cases"]
        if "validator_id" in c["expected"]
    ]
    assert len(cases) == 45


def test_both_variants_pin_their_questions_validator_revision():
    by_slug = {e["slug"]: e for e in ENTRIES if e["kind"] == "harness-revision" and e["track"] == "coding"}
    for e in ENTRIES:
        if e["kind"] != "test-definition":
            continue
        doc = stored(e)
        ref = by_slug.get(e["slug"])
        if ref is None:
            assert doc["validators"] is None
            assert not any("validator_id" in c["expected"] for c in doc["cases"])
        else:
            assert doc["validators"] == {"slug": e["slug"], "content_version": 1, "checksum": ref["checksum"]}
            ids = {v["validator_id"] for v in stored(ref)["validators"]}
            assert {c["expected"]["validator_id"] for c in doc["cases"] if "validator_id" in c["expected"]} <= ids


def test_the_five_sourceless_ai_coding_samples_and_three_take_homes_are_retired():
    retired = {(e["track"], e["slug"]): e for e in ENTRIES if e["lifecycle"] == "retired"}
    assert set(retired) == {("ai-coding", s) for s in build.SOURCELESS_AI_CODING} | {
        ("take-home", s) for s in build.RETIRED_TAKE_HOME
    }
    for slug, variant in build.SOURCELESS_AI_CODING.items():
        entry = retired[("ai-coding", slug)]
        assert (entry["variant"], entry["path"], entry["checksum"]) == (variant, None, None)
    for slug in build.RETIRED_TAKE_HOME:
        assert stored(retired[("take-home", slug)])["result_protocol"] == "legacy-stdout"


# ---- what the compiler ports from the seeds --------------------------------------


def seed_rows() -> list[dict]:
    return build.coding_questions()


def test_the_seed_migrations_entry_inference_is_ported_for_182_questions():
    inferred = 0
    for row in seed_rows():
        slug = build.slugify(row.get("slug") or row.get("title") or "")
        doc = stored(next(e for e in ENTRIES if e["kind"] == "test-definition" and e["slug"] == slug))
        if row.get("entry"):
            assert doc["entry"] == row["entry"]
        else:
            inferred += 1
            starter = row["starter_code"]["python"]
            name = re.search(r"def\s+(\w+)\s*\(", starter).group(1)
            assert doc["entry"]["kind"] == "function" and doc["entry"]["name"] == name
    assert inferred == 182


def _legacy(expected: dict, predicates: dict[str, str]):
    """A compiled expected value in the shape matchers.match reads."""
    if "literal" in expected:
        return expected["literal"]
    if "validator_id" in expected:
        return {"$match": "validator", "code": predicates[expected["validator_id"]]}
    kind = expected["matcher"]
    out = {"$match": kind}
    out.update({k: v for k, v in expected.items() if k != "matcher"})
    return out


def _seed_view(expected):
    if not (isinstance(expected, dict) and isinstance(expected.get("$match"), str)):
        return expected
    keep = ("$match", "value", "values", "abs_tol", "rel_tol", "code")
    return {k: v for k, v in expected.items() if k in keep and v is not None}


def test_compiled_cases_grade_as_the_seeded_ones_do():
    """Each compiled case reads back as its seed case, so the legacy path
    and test_question_validation.py see the same tests; a predicate that
    only compares to a literal became that literal and matches the same."""
    folded = 0
    revisions = {e["slug"]: stored(e) for e in ENTRIES if e["kind"] == "harness-revision" and e["track"] == "coding"}
    for row in seed_rows():
        slug = build.slugify(row.get("slug") or row.get("title") or "")
        predicates = {v["validator_id"]: v["predicate"] for v in revisions.get(slug, {}).get("validators", [])}
        seeded = [tc for tc in row.get("test_cases") or [] if isinstance(tc, dict)]
        for variant in ("python", "javascript"):
            entry = next(e for e in ENTRIES if e["kind"] == "test-definition" and e["slug"] == slug
                         and e["variant"] == variant)
            cases = stored(entry)["cases"]
            assert [c["case_id"] for c in cases] == [f"c{i:03d}" for i in range(len(seeded))]
            for case, tc in zip(cases, seeded):
                assert case["input"] == tc.get("input", {})
                assert case["tags"] == list(tc.get("tags") or [])
                assert case["time_class"] == ("large" if "large" in case["tags"] else "standard")
                legacy = _legacy(case["expected"], predicates)
                seed = tc.get("expected")
                if _seed_view(seed) == _seed_view(legacy):
                    continue
                # The literal fold: same verdict on the literal and off it.
                assert seed["$match"] == "validator" and "literal" in case["expected"]
                value = case["expected"]["literal"]
                assert value == ast.literal_eval(seed["code"].split("out ==", 1)[1].strip())
                assert match(seed, value, tc.get("input")) == match(value, value, tc.get("input")) == (True, None)
                assert match(seed, ["not", value], tc.get("input"))[0] is False
                folded += 1
    # Amazon Lottery's out == ['a'], in both variants.
    assert folded == 2


def test_hallucinated_http_client_compiles_its_drivers_per_variant():
    active = {e["variant"]: stored(e) for e in ENTRIES
              if e["track"] == "ai-coding" and e["lifecycle"] == "active"}
    assert set(active) == {"python", "typescript"}
    for variant, doc in active.items():
        assert doc["slug"] == "hallucinated-http-client"
        assert doc["runtime_profile"] == ("python-pytest" if variant == "python" else "node-tsx")
        harness = {f["path"]: f["contents"] for f in doc["files"]}
        assert harness["harness/rounds_harness.py"] == build.HARNESS_RUNTIME.read_text(encoding="utf-8")
        # The grade checks the real server; the visible test stays a candidate file.
        assert "hidden_tests" not in json.dumps(doc)
        assert all(p.startswith("tests/") or "/" not in p for p in doc["candidate_paths"])


# ---- versioning, on copies of the sources ----------------------------------------


QUESTION = {
    "title": "Add Two",
    "slug": "add-two",
    "starter_code": {"python": "def add(a, b):\n    pass\n"},
    "test_cases": [{"input": {"a": 1, "b": 2}, "expected": 3, "tags": ["basic"]}],
}


@pytest.fixture
def sources(tmp_path):
    seeds = tmp_path / "seeds"
    seeds.mkdir()
    rounds = tmp_path / "rounds"
    shutil.copytree(build.AI_CODING_ROUNDS / "hallucinated-http-client", rounds / "hallucinated-http-client")
    out = tmp_path / "definitions"
    out.mkdir()

    def write_questions(*questions):
        (seeds / "content.json").write_text(json.dumps({"coding_questions": list(questions)}), encoding="utf-8")

    def compile_once():
        old = build.load_manifest(out / "manifest.json")
        plan = build.compile_all(old, seeds=seeds, rounds=rounds, assignments=tmp_path / "no-take-homes",
                                 definitions=out)
        build.write(plan, out)
        return {(e["track"], e["slug"], e["kind"], e["variant"], e["content_version"]): e for e in plan.entries}

    write_questions(QUESTION)
    return {"seeds": seeds, "rounds": rounds, "out": out, "write_questions": write_questions,
            "compile": compile_once}


def coding(entries: dict, slug: str = "add-two") -> dict:
    return {(k[3], k[4]): e["lifecycle"] for k, e in entries.items() if k[1] == slug and k[2] == "test-definition"}


def test_a_first_compile_adds_version_1_of_each_variant(sources):
    entries = sources["compile"]()
    assert coding(entries) == {("python", 1): "active", ("javascript", 1): "active"}
    assert build.differences(build.compile_all(build.load_manifest(sources["out"] / "manifest.json"),
                                               seeds=sources["seeds"], rounds=sources["rounds"],
                                               assignments=sources["out"] / "none",
                                               definitions=sources["out"]), sources["out"]) == []


def test_unchanged_sources_keep_their_versions(sources):
    first = sources["compile"]()
    second = sources["compile"]()
    assert first == second


def test_a_changed_source_adds_the_next_version_and_supersedes_the_active_one(sources):
    sources["compile"]()
    v1 = (sources["out"] / "store/coding/add-two/python.v1.json").read_bytes()
    changed = json.loads(json.dumps(QUESTION))
    changed["test_cases"].append({"input": {"a": 2, "b": 2}, "expected": 4})
    sources["write_questions"](changed)
    entries = sources["compile"]()
    assert coding(entries) == {
        ("python", 1): "superseded", ("javascript", 1): "superseded",
        ("python", 2): "active", ("javascript", 2): "active",
    }
    # Shipped bytes never change.
    assert (sources["out"] / "store/coding/add-two/python.v1.json").read_bytes() == v1


def test_a_change_to_one_variant_moves_every_variant_to_the_next_version(sources):
    sources["compile"]()
    grade = sources["rounds"] / "hallucinated-http-client/checkpoints/python/0/harness/grade.py"
    grade.write_text(grade.read_text(encoding="utf-8") + "\n# edited\n", encoding="utf-8")
    entries = sources["compile"]()
    versions = {(k[3], k[4]): e["lifecycle"] for k, e in entries.items() if k[1] == "hallucinated-http-client"}
    assert versions == {
        ("python", 1): "superseded", ("typescript", 1): "superseded",
        ("python", 2): "active", ("typescript", 2): "active",
    }


def test_only_a_manifest_edit_retires_a_version(sources):
    sources["compile"]()
    # A question dropped from the seeds keeps its versions as they were.
    sources["write_questions"]()
    assert set(coding(sources["compile"]()).values()) == {"active"}
    manifest_path = sources["out"] / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["entries"]:
        if entry["slug"] == "add-two":
            entry["lifecycle"] = "retired"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    sources["write_questions"](QUESTION)
    assert set(coding(sources["compile"]()).values()) == {"retired"}


def test_a_changed_shipped_file_stops_the_compile(sources):
    sources["compile"]()
    path = sources["out"] / "store/coding/add-two/python.v1.json"
    path.write_bytes(path.read_bytes().replace(b'"expected"', b'"expected" '))
    changed = json.loads(json.dumps(QUESTION))
    changed["test_cases"][0]["expected"] = 4
    sources["write_questions"](changed)
    with pytest.raises(build.CompileError, match="doesn't match its checksum"):
        sources["compile"]()


@pytest.mark.parametrize(
    "edit, message",
    [
        (lambda q: q.update(starter_code={"python": "x = 1\n"}), "has no entry"),
        (lambda q: q["test_cases"][0].update(expected={"$match": "regex", "value": "."}), "unknown matcher"),
        (lambda q: q.update(entry={"kind": "custom", "code": "print(1)"}), "add-two"),
    ],
    ids=["no-entry", "unknown-matcher", "custom-entry"],
)
def test_a_question_the_contract_cant_express_stops_the_compile(sources, edit, message):
    question = json.loads(json.dumps(QUESTION))
    edit(question)
    sources["write_questions"](question)
    with pytest.raises(build.CompileError, match=message):
        sources["compile"]()


def test_a_slug_listed_twice_stops_the_compile(sources):
    sources["write_questions"](QUESTION, QUESTION)
    with pytest.raises(build.CompileError, match="appears twice"):
        sources["compile"]()


def test_a_shell_test_command_stops_the_compile(sources):
    manifest_path = sources["rounds"] / "hallucinated-http-client/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["variants"]["python"]["checkpoints"][0]["test_command"] = "bash -c 'pytest -q'"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(build.CompileError, match="doesn't start with one of"):
        sources["compile"]()


def test_a_sourceless_sample_with_sources_again_stops_the_compile(sources):
    shutil.copytree(sources["rounds"] / "hallucinated-http-client", sources["rounds"] / "word-count-py")
    with pytest.raises(build.CompileError, match="has sources again"):
        sources["compile"]()


def test_only_the_removed_take_home_assignments_compile_and_only_as_retired(tmp_path):
    root = tmp_path / "assignments"
    shutil.copytree(build.TAKE_HOME_ASSIGNMENTS / "kv-store-py", root / "kv-store-py")
    compiled = build.take_home_sources(root)
    assert [(s.key.slug, s.lifecycle) for s in compiled] == [("kv-store-py", "retired")]
    manifest = json.loads((root / "kv-store-py/manifest.json").read_text(encoding="utf-8"))
    manifest["slug"] = "new-assignment"
    shutil.copytree(root / "kv-store-py", root / "new-assignment")
    (root / "new-assignment/manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(build.CompileError, match="fd 3 driver"):
        build.take_home_sources(root)


# ---- the runner's store ----------------------------------------------------------


def test_the_runner_verifies_every_shipped_version_at_startup(capsys):
    store = definitions.init()
    assert store.loaded and not store.mismatched
    assert len(store.entries) == 471
    (loaded,) = events(capsys.readouterr().out, "definitions.loaded")
    assert (loaded["entries"], loaded["mismatched"]) == (471, 0)


def test_the_app_checks_definitions_when_it_starts(capsys):
    from fastapi.testclient import TestClient

    from main import app

    with TestClient(app):
        pass
    assert events(capsys.readouterr().out, "definitions.loaded")


def _doc(slug: str, variant: str, version: int) -> dict:
    return {
        "schema": "test-definition/v1", "track": "coding", "slug": slug, "variant": variant,
        "content_version": version, "entry": {"kind": "function", "name": "f", "params": []},
        "cases": [{"case_id": "c000", "tags": [], "visibility": "visible", "time_class": "standard",
                   "input": {}, "expected": {"literal": version}}],
        "validators": None,
    }


@pytest.fixture
def store(tmp_path):
    """A small store: two-sum python v1 superseded by v2, javascript v1
    active, both AI-coding variants, and a payload-free retired sample."""
    docs = [
        (_doc("two-sum", "python", 1), "superseded"),
        (_doc("two-sum", "python", 2), "active"),
        (_doc("two-sum", "javascript", 1), "active"),
    ]
    for variant in ("python", "typescript"):
        path = DEFINITIONS / f"store/ai-coding/hallucinated-http-client/{variant}.v1.json"
        docs.append((json.loads(path.read_bytes()), "active"))
    entries = []
    for doc, lifecycle in docs:
        kind = "test-definition" if doc["schema"] == "test-definition/v1" else "harness-revision"
        path = f"store/{doc['track']}/{doc['slug']}/{doc['variant']}.v{doc['content_version']}.json"
        data = canonical.canonical(doc)
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_bytes(data)
        entries.append({"kind": kind, "track": doc["track"], "slug": doc["slug"], "variant": doc["variant"],
                        "content_version": doc["content_version"], "lifecycle": lifecycle, "path": path,
                        "checksum": canonical.checksum_bytes(data)})
    entries.append({"kind": "harness-revision", "track": "ai-coding", "slug": "word-count-py", "variant": "python",
                    "content_version": 1, "lifecycle": "retired", "path": None, "checksum": None})
    (tmp_path / "manifest.json").write_text(json.dumps({"schema": "definitions-manifest/v1", "entries": entries}))
    return tmp_path


def _code(fn) -> TypedError:
    with pytest.raises(TypedError) as caught:
        fn()
    return caught.value


def test_an_active_version_resolves_with_its_receipt(store, capsys):
    resolved = definitions.Store(store).load().resolve("coding", "two-sum", "python", 2, route="/api/evaluate")
    assert resolved.document["cases"][0]["expected"] == {"literal": 2}
    receipt = resolved.receipt()
    assert receipt == {"track": "coding", "slug": "two-sum", "variant": "python", "content_version": 2,
                       "checksum": receipt["checksum"]}
    assert canonical.is_checksum(receipt["checksum"])
    (line,) = events(capsys.readouterr().out, "definition.resolved")
    assert (line["definition"], line["route"]) == ("coding/two-sum/python@2", "/api/evaluate")


@pytest.mark.parametrize(
    "request_",
    [("coding", "no-such-question", "python", 1), ("coding", "two-sum", "ruby", 1),
     ("coding", "two-sum", "python", 99), ("ai-coding", "two-sum", "python", 1), ("pack", "two-sum", "python", 1)],
    ids=["slug", "variant", "version", "track", "unknown-track"],
)
def test_anything_unknown_is_the_same_definition_not_found(store, request_):
    err = _code(lambda: definitions.Store(store).load().resolve(*request_))
    assert (err.code, CODES[err.code], err.detail) == ("definition_not_found", 404, TypedError("definition_not_found").detail)


def test_a_superseded_version_names_the_active_one(store, capsys):
    err = _code(lambda: definitions.Store(store).load().resolve("coding", "two-sum", "python", 1, route="/api/run"))
    assert (err.code, CODES[err.code]) == ("definition_superseded", 409)
    assert "version 2" in err.detail
    (line,) = events(capsys.readouterr().out, "definition.rejected")
    assert (line["definition"], line["code"], line["route"]) == ("coding/two-sum/python@1", "definition_superseded", "/api/run")


def test_a_retired_version_is_gone(store):
    err = _code(lambda: definitions.Store(store).load().resolve("ai-coding", "word-count-py", "python", 1))
    assert (err.code, CODES[err.code]) == ("definition_retired", 410)


def test_an_unsupported_runtime_names_the_variants_this_runner_has(store, monkeypatch):
    monkeypatch.setattr(definitions, "RUNTIME_PROFILES", frozenset({"python-pytest", "validator-python"}))
    loaded = definitions.Store(store).load()
    err = _code(lambda: loaded.resolve("ai-coding", "hallucinated-http-client", "typescript", 1))
    assert (err.code, CODES[err.code]) == ("runtime_unsupported", 422)
    assert err.detail == "This language isn't supported here. Try python."
    assert loaded.resolve("ai-coding", "hallucinated-http-client", "python", 1).identity.variant == "python"


def test_an_unsupported_coding_variant_names_only_supported_ones(store, monkeypatch):
    monkeypatch.setattr(definitions, "CODING_VARIANTS", frozenset({"python"}))
    loaded = definitions.Store(store).load()
    err = _code(lambda: loaded.resolve("coding", "two-sum", "javascript", 1))
    assert (err.code, err.detail) == ("runtime_unsupported", "This language isn't supported here. Try python.")
    monkeypatch.setattr(definitions, "CODING_VARIANTS", frozenset())
    err = _code(lambda: loaded.resolve("coding", "two-sum", "javascript", 1))
    assert err.detail == TypedError("runtime_unsupported").detail


def test_a_file_changed_before_startup_fails_closed_and_alerts(store, capsys):
    path = store / "store/coding/two-sum/python.v2.json"
    path.write_bytes(path.read_bytes().replace(b'"literal":2', b'"literal":3'))
    loaded = definitions.Store(store).load()
    out = capsys.readouterr().out
    (summary,) = events(out, "definitions.loaded")
    assert summary["mismatched"] == 1
    assert any(e.get("definition") == "coding/two-sum/python@2" for e in events(out, "definition.rejected"))
    err = _code(lambda: loaded.resolve("coding", "two-sum", "python", 2))
    assert (err.code, CODES[err.code]) == ("definition_integrity_mismatch", 503)
    assert loaded.resolve("coding", "two-sum", "javascript", 1)


def test_a_file_changed_or_removed_after_startup_fails_closed(store):
    loaded = definitions.Store(store).load()
    (store / "store/coding/two-sum/javascript.v1.json").unlink()
    err = _code(lambda: loaded.resolve("coding", "two-sum", "javascript", 1))
    assert err.code == "definition_integrity_mismatch"
    # It stays failed until a restart reads a repaired image.
    assert _code(lambda: loaded.resolve("coding", "two-sum", "javascript", 1)).code == "definition_integrity_mismatch"


def _entry_with(**fields) -> dict:
    good = {"kind": "test-definition", "track": "coding", "slug": "two-sum", "variant": "python",
            "content_version": 1, "lifecycle": "active", "path": "store/coding/two-sum/python.v1.json",
            "checksum": "sha256:" + "0" * 64}
    return {"schema": "definitions-manifest/v1", "entries": [{**good, **fields}]}


@pytest.mark.parametrize(
    "manifest",
    [None, "not json", {"schema": "something-else/v1", "entries": []},
     {"schema": "definitions-manifest/v1", "entries": [{"kind": "test-definition"}]},
     {"schema": "definitions-manifest/v1"},
     {"schema": "definitions-manifest/v1", "entries": 7},
     {"schema": "definitions-manifest/v1", "entries": {"two-sum": {}}},
     {"schema": "definitions-manifest/v1", "entries": "two-sum"},
     _entry_with(track=["coding"]),
     _entry_with(kind={"test-definition": 1}),
     _entry_with(variant=["python"]),
     _entry_with(lifecycle=["active"]),
     _entry_with(path=["store/x.json"]),
     _entry_with(checksum=7),
     '{"schema": "definitions-manifest/v1", "entries": ' + "[" * 100_000 + "]" * 100_000 + "}"],
    ids=["missing", "not-json", "wrong-schema", "bad-entry", "no-entries", "entries-a-number", "entries-an-object",
         "entries-a-string", "track-a-list", "kind-an-object", "variant-a-list", "lifecycle-a-list", "path-a-list",
         "checksum-a-number", "deep-nesting"],
)
def test_an_unusable_manifest_leaves_nothing_to_resolve(tmp_path, capsys, manifest):
    if manifest is not None:
        (tmp_path / "manifest.json").write_text(manifest if isinstance(manifest, str) else json.dumps(manifest))
    loaded = definitions.Store(tmp_path).load()
    assert not loaded.loaded and not loaded.entries
    assert events(capsys.readouterr().out, "definition.rejected")[0]["code"] == "definition_integrity_mismatch"
    assert _code(lambda: loaded.resolve("coding", "two-sum", "python", 1)).code == "definition_not_found"


def test_a_malformed_manifest_never_stops_the_runner_starting(tmp_path, monkeypatch):
    # init() is what startup calls: it answers an empty store, and the
    # store a request asks for afterwards is that one, not an exception.
    (tmp_path / "manifest.json").write_text(json.dumps(_entry_with(track=["coding"])))
    monkeypatch.setattr(definitions, "_store", None)
    loaded = definitions.init(tmp_path)
    assert loaded.entries == {} and definitions.store() is loaded
    monkeypatch.setattr(definitions, "_store", None)


def test_a_manifest_listing_a_version_twice_is_unusable(store):
    manifest = json.loads((store / "manifest.json").read_text())
    manifest["entries"].append(dict(manifest["entries"][0]))
    (store / "manifest.json").write_text(json.dumps(manifest))
    assert not definitions.Store(store).load().entries


def test_validators_load_only_at_the_checksum_the_definition_pins():
    two_sum = definitions.Store().load()
    ref = next(e for e in ENTRIES if e["kind"] == "harness-revision" and e["track"] == "coding")
    doc = two_sum.validators(ref["slug"], 1, ref["checksum"])
    assert doc["kind"] == "coding-validators"
    err = _code(lambda: two_sum.validators(ref["slug"], 1, "sha256:" + "0" * 64))
    assert err.code == "definition_integrity_mismatch"


def test_the_definition_log_lines_carry_identity_and_never_content(store, capsys):
    loaded = definitions.Store(store).load()
    loaded.resolve("coding", "two-sum", "python", 2)
    with pytest.raises(TypedError):
        loaded.resolve("coding", "two-sum", "python", 1)
    for line in [json.loads(x) for x in capsys.readouterr().out.splitlines() if x.startswith("{")]:
        assert set(line) <= {"v", "event", "definition", "route", "code", "service", "entries", "mismatched"}
        assert "dropped" not in line
