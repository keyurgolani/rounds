"""The definition contracts (ROUNDS-00A-L02): RFC 8785 checksums, the
schema checker, the five schemas and the manifest's, their fixtures, and
the committed Python and TypeScript bindings."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from app import canonical, contract_schema

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "contracts" / "definitions"
STORE = ROOT / "backend" / "definitions"
FRONTEND = ROOT / "frontend" / "src"
CHECKSUM = "sha256:" + "a" * 64


def schema(name: str) -> contract_schema.Validator:
    return contract_schema.load(f"definitions/{name}.v1.schema.json")


def stored(path: str) -> dict:
    return json.loads((STORE / path).read_bytes())


# ---- RFC 8785 --------------------------------------------------------------------


def test_the_rfc_8785_example_canonicalizes_to_its_published_bytes():
    # RFC 8785 section 3.2.2's input, parsed as JSON.parse would.
    value = {
        "numbers": [333333333.33333329, 1e30, 4.50, 2e-3, 0.000000000000000000000000001],
        "string": "\u20ac$\u000f\nA'B\"\\\\\"/",
        "literals": [None, True, False],
    }
    assert canonical.canonical(value) == (
        '{"literals":[null,true,false],"numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27],'
        '"string":"€$\\u000f\\nA\'B\\"\\\\\\\\\\"/"}'
    ).encode("utf-8")


def test_keys_sort_by_utf16_code_units():
    # RFC 8785 section 3.2.3: the emoji's surrogates sort before U+FB33,
    # though its code point is higher.
    keys = ["\u20ac", "\r", "\ufb33", "1", "\U0001f600", "\u0080", "\u00f6"]
    out = canonical.canonical({k: i for i, k in enumerate(keys)})
    order = json.loads(out, object_pairs_hook=lambda pairs: [k for k, _ in pairs])
    assert order == ["\r", "1", "\u0080", "\u00f6", "\u20ac", "\U0001f600", "\ufb33"]


@pytest.mark.parametrize(
    "number, text",
    [
        (0, "0"), (-0.0, "0"), (1e21, "1e+21"), (1e20, "100000000000000000000"), (1e-7, "1e-7"),
        (0.000001, "0.000001"), (4.5, "4.5"), (-1.5, "-1.5"), (0.30000000000000004, "0.30000000000000004"),
        (9007199254740991, "9007199254740991"), (5e-324, "5e-324"), (1.7976931348623157e308, "1.7976931348623157e+308"),
    ],
)
def test_numbers_are_written_as_ecmascript_writes_them(number, text):
    assert canonical.canonical(number) == text.encode()


@pytest.mark.parametrize("value", [2**53 + 1, -(2**53 + 1), float("nan"), float("inf"), "\ud800", {1: "x"}, b"bytes", {1, 2}])
def test_values_rfc_8785_cant_represent_exactly_are_refused(value):
    with pytest.raises(canonical.CanonicalError):
        canonical.canonical(value)


def test_a_checksum_is_sha256_over_the_canonical_bytes():
    value = {"b": [1, 2.5], "a": "x"}
    assert canonical.checksum(value) == canonical.checksum_bytes(b'{"a":"x","b":[1,2.5]}')
    assert canonical.is_checksum(canonical.checksum(value))
    assert not canonical.is_checksum("sha256:" + "A" * 64) and not canonical.is_checksum("md5:" + "a" * 32)


# ---- the schema checker ----------------------------------------------------------


def test_the_checker_refuses_keywords_it_does_not_implement():
    with pytest.raises(contract_schema.SchemaError):
        contract_schema.Validator({"type": "object", "if": {"type": "object"}})
    with pytest.raises(contract_schema.SchemaError):
        contract_schema.Validator({"$ref": "https://example.test/remote.json"}).errors({})


def test_a_pattern_dollar_matches_only_at_the_end_as_in_ecmascript():
    checker = contract_schema.Validator({"type": "string", "pattern": "^[a-z]+$"})
    assert checker.is_valid("abc") and not checker.is_valid("abc\n")


def test_one_of_needs_exactly_one_branch():
    checker = contract_schema.Validator({"oneOf": [{"type": "integer"}, {"type": "number"}]})
    assert checker.is_valid(1.5) and not checker.is_valid(1)


@pytest.mark.parametrize(
    "name",
    ["test-definition", "harness-revision", "artifact-renderer", "render-request", "resource-profile", "manifest"],
)
def test_every_schema_uses_only_supported_keywords_and_is_versioned(name):
    doc = json.loads((SCHEMAS / f"{name}.v1.schema.json").read_text())
    assert doc["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert doc["$id"] == f"urn:rounds:contracts:definitions:{name}:v1"
    contract_schema.Validator(doc)


# ---- fixtures: every compiled file, and what each schema refuses -----------------


def test_every_stored_definition_matches_its_schema():
    manifest = json.loads((STORE / "manifest.json").read_text())
    assert schema("manifest").errors(manifest) == []
    for entry in manifest["entries"]:
        if entry["path"] is None:
            continue
        doc = stored(entry["path"])
        assert schema(entry["kind"]).errors(doc) == [], entry["path"]


def _coding() -> dict:
    return stored("store/coding/two-sum/python.v1.json")


def _ai_coding() -> dict:
    return stored("store/ai-coding/hallucinated-http-client/python.v1.json")


def _broken(doc: dict, path: tuple, value) -> dict:
    doc = json.loads(json.dumps(doc))
    node = doc
    for key in path[:-1]:
        node = node[key]
    if value is KeyError:
        del node[path[-1]]
    else:
        node[path[-1]] = value
    return doc


@pytest.mark.parametrize(
    "path, value",
    [
        (("command",), "pytest"),
        (("entry",), {"kind": "custom", "code": "x"}),
        (("entry", "name"), "two sum"),
        (("cases", 0, "case_id"), "case-1"),
        (("cases", 0, "time_class"), "huge"),
        (("cases", 0, "expected"), {"validator_id": "lambda inp, out: True"}),
        (("cases", 0, "expected"), {"$match": "validator", "code": "lambda inp, out: True"}),
        (("variant",), "ruby"),
        (("content_version",), 0),
    ],
)
def test_a_test_definition_refuses_what_a_caller_could_use_to_change_grading(path, value):
    assert schema("test-definition").errors(_broken(_coding(), path, value))


@pytest.mark.parametrize(
    "path, value",
    [
        (("checkpoints", 0, "grade", "argv"), ["bash", "-c", "pytest"]),
        (("checkpoints", 0, "grade", "argv"), ["sh", "harness/grade.sh"]),
        (("checkpoints", 0, "results"), []),
        (("checkpoints", 0, "min_executed"), 0),
        (("files", 0, "path"), "../escape.py"),
        (("files", 0, "path"), "/etc/passwd"),
        (("network",), "internet"),
        (("result_protocol",), "stdout"),
        (("ai_policy",), "always"),
    ],
)
def test_a_harness_revision_refuses_shells_escapes_and_self_scored_results(path, value):
    assert schema("harness-revision").errors(_broken(_ai_coding(), path, value))


RENDERER = {
    "schema": "artifact-renderer/v1",
    "template_id": "modern",
    "template_bundle_checksum": CHECKSUM,
    "renderer_version": "24.20.0",
    "font_package_version": "1.0.0",
    "overrides": {
        "spacing": {"margin": 14},
        "typography": {"body": {"size": 10.5, "family": "inter"}, "heading": {"family": "playfair-display"}},
        "colors": {"primary": "#1A2B3C"},
        "bulletStyle": "disc",
    },
}


def test_an_artifact_renderer_contract_accepts_the_allowlisted_grammar():
    assert schema("artifact-renderer").errors(RENDERER) == []
    assert schema("artifact-renderer").errors({**RENDERER, "overrides": {}}) == []


@pytest.mark.parametrize(
    "path, value",
    [
        (("template_id",), "unknown-template"),
        (("overrides", "spacing", "margin"), 31),
        (("overrides", "typography", "body", "size"), 13),
        (("overrides", "colors", "primary"), "red"),
        (("overrides", "bulletStyle"), "skull"),
        (("overrides", "typography", "body", "family"), "Comic Sans MS"),
        (("overrides", "css"), "body { display: none }"),
        (("overrides", "page_size"), "Letter"),
        (("html",), "<p>hi</p>"),
    ],
)
def test_an_artifact_renderer_contract_refuses_unknown_templates_and_out_of_grammar_values(path, value):
    assert schema("artifact-renderer").errors(_broken(RENDERER, path, value))


def test_the_renderer_contract_lists_the_registry_templates_and_bullet_styles():
    registry = (FRONTEND / "features" / "resume" / "templates" / "registry.ts").read_text()
    sidebar = (FRONTEND / "features" / "resume" / "studio" / "DesignSidebar.tsx").read_text()
    doc = json.loads((SCHEMAS / "artifact-renderer.v1.schema.json").read_text())
    templates = re.findall(r"^\s{4}id: '([a-z0-9-]+)',", registry, re.M)
    assert len(templates) == 19
    assert doc["properties"]["template_id"]["enum"] == templates
    bullets = re.findall(r"\{ key: '([a-z-]+)', label:", sidebar)
    assert doc["properties"]["overrides"]["properties"]["bulletStyle"]["enum"] == bullets


RENDER_REQUEST = {
    "snapshot_id": "a" * 15,
    "expected_checksum": CHECKSUM,
    "format": "pdf",
    "page_size": "A4",
    "margin_mm": 0,
    "locale": "en",
    "idempotency_id": "0190f000-0000-7000-8000-000000000001",
}


def test_a_render_request_names_a_snapshot_and_its_checksum():
    assert schema("render-request").errors(RENDER_REQUEST) == []


@pytest.mark.parametrize(
    "path, value",
    [
        (("format",), "png"),
        (("page_size",), "Letter"),
        (("margin_mm",), 31),
        (("locale",), "fr"),
        (("expected_checksum",), "sha1:abc"),
        (("idempotency_id",), "0190f000-0000-4000-8000-000000000001"),
        (("html",), "<html></html>"),
        (("template_id",), "modern"),
        (("snapshot_id",), KeyError),
    ],
)
def test_a_render_request_refuses_markup_other_pages_and_unknown_fields(path, value):
    assert schema("render-request").errors(_broken(RENDER_REQUEST, path, value))


def _profile() -> dict:
    return json.loads((STORE / "profiles" / "execution-default.v1.json").read_text())


def test_the_resource_profile_sits_at_the_spec_ceilings_with_a_256_kib_stdin_cap():
    profile = _profile()
    assert schema("resource-profile").errors(profile) == []
    assert profile["stdin_bytes"] == 256 * 1024 >= 200_010
    assert profile["job_classes"] == {"interactive": {"wall_s_max": 10}, "project": {"wall_s_max": 120}}


@pytest.mark.parametrize(
    "path, value",
    [
        (("memory_bytes",), 512 * 1024 * 1024 + 1),
        (("processes",), 65),
        (("snippet_bytes",), 256 * 1024 + 1),
        (("job_classes", "interactive", "wall_s_max"), 11),
        (("job_classes", "project", "wall_s_max"), 121),
        (("network",), "none"),
    ],
)
def test_no_resource_profile_goes_past_the_spec_ceilings(path, value):
    assert schema("resource-profile").errors(_broken(_profile(), path, value))


def test_a_retired_entry_without_a_file_must_say_it_is_retired():
    entry = {"kind": "harness-revision", "track": "ai-coding", "slug": "word-count-py", "variant": "python",
             "content_version": 1, "lifecycle": "active", "path": None, "checksum": None}
    assert schema("manifest").errors({"schema": "definitions-manifest/v1", "entries": [entry]})
    assert not schema("manifest").errors(
        {"schema": "definitions-manifest/v1", "entries": [{**entry, "lifecycle": "retired"}]}
    )


# ---- bindings -------------------------------------------------------------------


def test_the_committed_bindings_match_the_schemas():
    script = ROOT / "scripts" / "definitions_bindings.py"
    res = subprocess.run([sys.executable, str(script), "--check"], capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, res.stderr


def test_the_python_bindings_import_and_name_every_root_type():
    from app.contracts.definitions import (
        artifact_renderer, harness_revision, manifest, render_request, resource_profile, test_definition,
    )

    assert {"TestDefinitionV1", "HarnessRevisionV1", "ArtifactRendererV1", "RenderRequestV1",
            "ResourceProfileV1", "DefinitionsManifestV1"} <= (
        set(test_definition.__all__) | set(harness_revision.__all__) | set(artifact_renderer.__all__)
        | set(render_request.__all__) | set(resource_profile.__all__) | set(manifest.__all__)
    )
