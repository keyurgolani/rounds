"""The runner's render-request/v1 model accepts exactly what the committed
schema accepts (ROUNDS-00A-L02, ROUNDS-00A-L04 PR 3). The runner image
carries no contracts/, so ``legacy_snapshots.RenderRequestV1`` mirrors
contracts/definitions/render-request.v1.schema.json and this keeps the two
in step: the same fields, the same required set, and one verdict for every
body below."""
from __future__ import annotations

import copy
import json

import pytest
from pydantic import ValidationError

from app import contract_schema, legacy_snapshots

VALID = {
    "snapshot_id": "snapaaaaaaaaaa1",
    "expected_checksum": "sha256:" + "c" * 64,
    "format": "pdf",
    "page_size": "A4",
    "margin_mm": 0,
    "locale": "en",
    "idempotency_id": "0190f000-0000-7000-8000-00000000000a",
}
MISSING = object()

# (field, value): MISSING leaves the field out.
CASES = [
    (None, None),
    ("margin_mm", 30),
    ("margin_mm", 12.5),
    ("margin_mm", 0.0),
    ("margin_mm", -1),
    ("margin_mm", 30.5),
    ("margin_mm", "0"),
    ("margin_mm", True),
    ("margin_mm", None),
    ("snapshot_id", "SNAPAAAAAAAAAA1"),
    ("snapshot_id", "snapaaaaaaaaaa"),
    ("snapshot_id", "snapaaaaaaaaaa12"),
    ("snapshot_id", 123456789012345),
    ("expected_checksum", "sha256:" + "C" * 64),
    ("expected_checksum", "sha256:" + "c" * 63),
    ("expected_checksum", "md5:" + "c" * 32),
    ("format", "png"),
    ("format", "PDF"),
    ("page_size", "Letter"),
    ("locale", "fr"),
    ("idempotency_id", "0190f000-0000-4000-8000-00000000000a"),
    ("idempotency_id", "0190F000-0000-7000-8000-00000000000A"),
    ("idempotency_id", "0190f000-0000-7000-c000-00000000000a"),
    ("html", "<p>x</p>"),
    ("markup", "<p>x</p>"),
    ("template_id", "modern"),
    ("design", {}),
    ("snapshot_id", MISSING),
    ("expected_checksum", MISSING),
    ("format", MISSING),
    ("page_size", MISSING),
    ("margin_mm", MISSING),
    ("locale", MISSING),
    ("idempotency_id", MISSING),
]


def schema() -> contract_schema.Validator:
    return contract_schema.load("definitions/render-request.v1.schema.json")


def changed(field, value) -> dict:
    out = copy.deepcopy(VALID)
    if field is None:
        return out
    if value is MISSING:
        out.pop(field)
    else:
        out[field] = value
    return out


def model_accepts(payload: dict) -> bool:
    try:
        legacy_snapshots.RenderRequestV1.model_validate(payload)
    except ValidationError:
        return False
    return True


@pytest.mark.parametrize("field,value", CASES, ids=[f"{f}={v!r}"[:60] for f, v in CASES])
def test_the_model_and_the_schema_give_one_verdict(field, value):
    payload = changed(field, value)
    # The way the route reads a body: parsed JSON.
    payload = json.loads(json.dumps(payload))
    assert model_accepts(payload) == (schema().errors(payload) == [])


def test_the_model_has_the_schemas_fields_all_required():
    doc = json.loads((contract_schema.CONTRACTS_DIR / "definitions" / "render-request.v1.schema.json").read_text())
    fields = legacy_snapshots.RenderRequestV1.model_fields
    assert set(fields) == set(doc["properties"]) == set(doc["required"])
    assert all(f.is_required() for f in fields.values())
    assert doc["additionalProperties"] is False
