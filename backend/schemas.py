"""Pydantic schemas for the code runner. Data-model schemas moved to
PocketBase (pocketbase/pb_migrations/) when the data layer migrated.

Request models follow admission/v1: they refuse unknown fields, and a
caller never supplies the entry, test cases, or expected values. Those
load on the server (routers/runner.py)."""
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app import limits
from app.limits import StrictModel


class Entry(BaseModel):
    """Per-problem entry declaration, as stored on the question. Per-kind
    fields validated by the driver — pydantic only enforces the union of
    kinds here."""
    model_config = ConfigDict(extra="allow")

    kind: Literal[
        "function",
        "class_ops",
        "in_place_mutation",
        "custom",
        "linked_list",
        "tree",
        "graph",
    ]


class CodeRunRequest(StrictModel):
    question_slug: str = Field(pattern=limits.SLUG_PATTERN)
    language: str = Field(default="python", pattern=limits.LANGUAGE_PATTERN)
    code: str
    input: Dict[str, Any]

    @field_validator("code")
    @classmethod
    def _code_size(cls, v: str) -> str:
        return limits.check_text(v, limits.SNIPPET_CODE_BYTES, "code")

    @field_validator("input")
    @classmethod
    def _input_size(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        return limits.check_json(v, limits.RUN_INPUT_BYTES, "input")


class CodeRunResult(BaseModel):
    stdout: str
    stderr: str
    return_value: Any = None
    error: Optional[str] = None
    duration_ms: int
    truncated: bool = False


class EvaluateFilter(StrictModel):
    tags: Optional[List[str]] = Field(default=None, max_length=limits.EVALUATE_MAX_CASES)
    indices: Optional[List[int]] = Field(default=None, max_length=limits.EVALUATE_MAX_CASES)

    @field_validator("tags")
    @classmethod
    def _tag_lengths(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None and any(len(tag) > 64 for tag in v):
            raise limits.over_limit("tags")
        return v


class CodeEvaluateRequest(StrictModel):
    question_slug: str = Field(pattern=limits.SLUG_PATTERN)
    language: str = Field(default="python", pattern=limits.LANGUAGE_PATTERN)
    code: str
    filter: Optional[EvaluateFilter] = None

    @field_validator("code")
    @classmethod
    def _code_size(cls, v: str) -> str:
        return limits.check_text(v, limits.SNIPPET_CODE_BYTES, "code")


class EvaluateCaseResult(BaseModel):
    index: int
    passed: bool
    description: str = ""
    tags: List[str] = []
    output: Any = None
    expected: Any = None
    error: Optional[str] = None
    duration_ms: int = 0


class CodeEvaluateResult(BaseModel):
    passed: int
    failed: int
    results: List[EvaluateCaseResult]
