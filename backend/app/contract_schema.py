"""A JSON Schema checker for the contracts in ``contracts/`` (ROUNDS-00A-L02).

It covers the 2020-12 keywords those schemas use and refuses any other
keyword, so a schema can't lean on a check that silently does nothing:

    $ref (local, ``#/$defs/...``), $defs, type, enum, const, pattern,
    minLength, maxLength, minimum, maximum, prefixItems, items, minItems,
    maxItems, uniqueItems, properties, required, additionalProperties,
    propertyNames, maxProperties, oneOf, anyOf, allOf

``$schema``, ``$id``, ``title``, ``description``, ``$comment``, and
``examples`` are annotations. A ``pattern`` follows ECMAScript: unanchored
unless it says otherwise, and a trailing ``$`` matches only at the end of
the string, never before a final newline as Python's does.

TODO(ROUNDS-34-L08): #182's shared contracts package takes this over.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

ANNOTATIONS = frozenset({"$schema", "$id", "title", "description", "$comment", "examples"})
KEYWORDS = frozenset({
    "$ref", "$defs", "type", "enum", "const", "pattern", "minLength", "maxLength",
    "minimum", "maximum", "prefixItems", "items", "minItems", "maxItems", "uniqueItems", "properties",
    "required", "additionalProperties", "propertyNames", "maxProperties", "oneOf",
    "anyOf", "allOf",
}) | ANNOTATIONS

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "contracts"


class SchemaError(ValueError):
    """The schema itself uses something this checker doesn't support."""


def _type_ok(name: str, value: Any) -> bool:
    if name == "null":
        return value is None
    if name == "boolean":
        return isinstance(value, bool)
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "string":
        return isinstance(value, str)
    if name == "array":
        return isinstance(value, list)
    if name == "object":
        return isinstance(value, dict)
    raise SchemaError(f"unknown type {name!r}")


@lru_cache(maxsize=512)
def _regex(pattern: str) -> re.Pattern[str]:
    # ECMAScript's $ is the end of input; Python's also matches before a
    # final newline, so a trailing $ becomes \Z.
    if pattern.endswith("$") and not pattern.endswith("\\$"):
        pattern = pattern[:-1] + r"\Z"
    return re.compile(pattern)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class Validator:
    def __init__(self, schema: dict[str, Any]) -> None:
        self.schema = schema
        self._check_keywords(schema, "#")

    def _check_keywords(self, node: Any, where: str) -> None:
        if isinstance(node, bool):
            return
        if not isinstance(node, dict):
            raise SchemaError(f"{where}: a schema is an object or a boolean")
        unknown = set(node) - KEYWORDS
        if unknown:
            raise SchemaError(f"{where}: unsupported keyword(s) {sorted(unknown)}")
        for key in ("properties", "$defs"):
            for name, sub in (node.get(key) or {}).items():
                self._check_keywords(sub, f"{where}/{key}/{name}")
        for key in ("items", "additionalProperties", "propertyNames"):
            if key in node and not isinstance(node[key], bool):
                self._check_keywords(node[key], f"{where}/{key}")
        for key in ("prefixItems", "oneOf", "anyOf", "allOf"):
            for i, sub in enumerate(node.get(key) or []):
                self._check_keywords(sub, f"{where}/{key}/{i}")

    def _resolve(self, ref: str) -> Any:
        if not ref.startswith("#/"):
            raise SchemaError(f"only local references are supported, not {ref!r}")
        node: Any = self.schema
        for part in ref[2:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            if not isinstance(node, dict) or part not in node:
                raise SchemaError(f"unresolved reference {ref!r}")
            node = node[part]
        return node

    def errors(self, instance: Any) -> list[str]:
        out: list[str] = []
        self._validate(self.schema, instance, "", out)
        return out

    def is_valid(self, instance: Any) -> bool:
        return not self.errors(instance)

    def _validate(self, schema: Any, value: Any, path: str, out: list[str]) -> None:
        where = path or "/"
        if schema is True:
            return
        if schema is False:
            out.append(f"{where}: not allowed")
            return
        if "$ref" in schema:
            self._validate(self._resolve(schema["$ref"]), value, path, out)
        if "type" in schema:
            names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
            if not any(_type_ok(name, value) for name in names):
                out.append(f"{where}: expected {' or '.join(names)}")
                return
        if "const" in schema and _canonical_json(value) != _canonical_json(schema["const"]):
            out.append(f"{where}: expected {schema['const']!r}")
        if "enum" in schema and _canonical_json(value) not in {_canonical_json(v) for v in schema["enum"]}:
            out.append(f"{where}: not one of the allowed values")
        if isinstance(value, str):
            if "minLength" in schema and len(value) < schema["minLength"]:
                out.append(f"{where}: shorter than {schema['minLength']}")
            if "maxLength" in schema and len(value) > schema["maxLength"]:
                out.append(f"{where}: longer than {schema['maxLength']}")
            if "pattern" in schema and not _regex(schema["pattern"]).search(value):
                out.append(f"{where}: doesn't match {schema['pattern']}")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in schema and value < schema["minimum"]:
                out.append(f"{where}: below {schema['minimum']}")
            if "maximum" in schema and value > schema["maximum"]:
                out.append(f"{where}: above {schema['maximum']}")
        if isinstance(value, list):
            if "minItems" in schema and len(value) < schema["minItems"]:
                out.append(f"{where}: fewer than {schema['minItems']} items")
            if "maxItems" in schema and len(value) > schema["maxItems"]:
                out.append(f"{where}: more than {schema['maxItems']} items")
            if schema.get("uniqueItems") and len({_canonical_json(v) for v in value}) != len(value):
                out.append(f"{where}: items aren't unique")
            prefix = schema.get("prefixItems", [])
            for i, sub in enumerate(prefix[: len(value)]):
                self._validate(sub, value[i], f"{path}/{i}", out)
            if "items" in schema:
                for i, item in enumerate(value[len(prefix):], start=len(prefix)):
                    self._validate(schema["items"], item, f"{path}/{i}", out)
        if isinstance(value, dict):
            if "maxProperties" in schema and len(value) > schema["maxProperties"]:
                out.append(f"{where}: more than {schema['maxProperties']} properties")
            for name in schema.get("required", []):
                if name not in value:
                    out.append(f"{where}: missing {name!r}")
            properties = schema.get("properties", {})
            for name, item in value.items():
                child = f"{path}/{name}"
                if "propertyNames" in schema:
                    self._validate(schema["propertyNames"], name, child, out)
                if name in properties:
                    self._validate(properties[name], item, child, out)
                elif "additionalProperties" in schema:
                    self._validate(schema["additionalProperties"], item, child, out)
        for sub in schema.get("allOf", []):
            self._validate(sub, value, path, out)
        if "anyOf" in schema:
            if not any(not self._branch(sub, value, path) for sub in schema["anyOf"]):
                out.append(f"{where}: matches none of anyOf")
        if "oneOf" in schema:
            matched = sum(1 for sub in schema["oneOf"] if not self._branch(sub, value, path))
            if matched != 1:
                out.append(f"{where}: matches {matched} of oneOf, not exactly one")

    def _branch(self, schema: Any, value: Any, path: str) -> list[str]:
        out: list[str] = []
        self._validate(schema, value, path, out)
        return out


@lru_cache(maxsize=32)
def load(relative: str) -> Validator:
    """The validator for ``contracts/<relative>``."""
    path = CONTRACTS_DIR / relative
    return Validator(json.loads(path.read_text(encoding="utf-8")))
