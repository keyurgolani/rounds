"""Request field limits for admitted routes (admission/v1, step 5).

Request models call these from field validators. An over-limit value
raises a ``limit_exceeded`` error, which ``app.errors`` answers with 413
``limit_exceeded``; any other invalid value answers 422
``invalid_request``. The spec ceilings are 256 KiB of snippet code and
200 files or 5 MiB per project; the rest are proposed values the owner
ratifies.
"""
from __future__ import annotations

import json
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict
from pydantic_core import PydanticCustomError

from app.errors import LIMIT_ERROR_TYPE

KIB = 1024
MIB = 1024 * KIB

SNIPPET_CODE_BYTES = 256 * KIB
RUN_INPUT_BYTES = 64 * KIB
EVALUATE_MAX_CASES = 32
PROJECT_MAX_FILES = 200
PROJECT_MAX_BYTES = 5 * MIB
PROJECT_PATH_CHARS = 255
MAX_CHECKPOINT_INDEX = 999
AI_CHATS_BYTES = 512 * KIB
NOTES_BYTES = 64 * KIB
JOB_DESCRIPTION_BYTES = 64 * KIB
# /api/ai/enhance-projects: the batch cap of #72 and #73 until #179.
ENHANCE_MAX_PROJECTS = 25
SLUG_PATTERN = r"^[a-z0-9-]{1,128}$"
LANGUAGE_PATTERN = r"^[a-z0-9+#-]{1,32}$"
# A PocketBase record id, or empty for none.
OPTIONAL_RECORD_ID_PATTERN = r"^(?:[a-z0-9]{15})?$"


class StrictModel(BaseModel):
    """admission/v1 request models refuse fields they don't define."""

    model_config = ConfigDict(extra="forbid")


def over_limit(what: str) -> PydanticCustomError:
    return PydanticCustomError(LIMIT_ERROR_TYPE, "{what} is over its limit", {"what": what})


def utf8_size(value: str) -> int:
    return len(value.encode("utf-8", errors="surrogatepass"))


def json_size(value: Any) -> int:
    return len(json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8", errors="surrogatepass"))


def check_text(value: str, limit: int, what: str) -> str:
    if utf8_size(value) > limit:
        raise over_limit(what)
    return value


def check_json(value: Any, limit: int, what: str) -> Any:
    if json_size(value) > limit:
        raise over_limit(what)
    return value


def check_files(files: Mapping[str, str]) -> Mapping[str, str]:
    """A project's file map: at most 200 files and 5 MiB, relative paths
    that stay inside the project."""
    if len(files) > PROJECT_MAX_FILES:
        raise over_limit("files")
    total = 0
    for path, contents in files.items():
        if (
            not path
            or len(path) > PROJECT_PATH_CHARS
            or path.startswith("/")
            or "\\" in path
            or "\x00" in path
            or any(part in ("", ".", "..") for part in path.split("/"))
        ):
            raise PydanticCustomError("unsafe_path", "file paths must stay inside the project")
        total += utf8_size(path) + utf8_size(contents)
        if total > PROJECT_MAX_BYTES:
            raise over_limit("files")
    return files
