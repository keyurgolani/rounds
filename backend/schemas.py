"""Pydantic schemas for the code runner. Data-model schemas moved to
PocketBase (pocketbase/pb_migrations/) when the data layer migrated."""
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict


class Entry(BaseModel):
    """Per-problem entry declaration. Per-kind fields validated by the
    driver — pydantic only enforces the union of kinds here."""
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


class CodeRunRequest(BaseModel):
    code: str
    language: str = "python"
    entry: Entry
    input: Dict[str, Any]


class CodeRunResult(BaseModel):
    stdout: str
    stderr: str
    return_value: Any = None
    error: Optional[str] = None
    duration_ms: int
    truncated: bool = False


class EvaluateFilter(BaseModel):
    tags: Optional[List[str]] = None
    indices: Optional[List[int]] = None


class CodeEvaluateRequest(BaseModel):
    code: str
    language: str = "python"
    entry: Entry
    test_cases: List[Dict[str, Any]]
    filter: Optional[EvaluateFilter] = None


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
