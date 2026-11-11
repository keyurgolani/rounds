"""Public share requests leave no access-log line (ROUNDS-00B-L04).

uvicorn writes one ``uvicorn.access`` line per request: the peer's address
and the request line. ``install()`` puts a filter on that logger that drops
the line for the public share routes (the share page paths, the older
public share read, and the resolver), in any letter case and however the
path is spelled. The runner's own ``share.resolve`` line (``app.obs``) still
records each resolve's outcome; every other request keeps its access line.
"""
from __future__ import annotations

import logging
import posixpath
import re
import urllib.parse

LOGGER = "uvicorn.access"

# Lowercased, percent-decoded, normalized paths.
_PUBLIC_SHARE = re.compile(r"/r(?:/.*)?|/api/share/by-token(?:/.*)?|/api/share/resolve", re.S)
# The request line inside a formatted access message.
_REQUEST_LINE = re.compile(r'"[A-Za-z]+ (\S+) HTTP/[0-9.]+"')


def is_public_share_path(path: str) -> bool:
    """Whether a request path, with or without its query, is a public
    share route's."""
    raw = path.split("?", 1)[0].split("#", 1)[0]
    try:
        decoded = urllib.parse.unquote(raw, errors="strict")
    except UnicodeDecodeError:
        decoded = urllib.parse.unquote(raw, errors="replace")
    normalized = posixpath.normpath("/" + re.sub(r"/{2,}", "/", decoded.replace("\\", "/")).lstrip("/"))
    return _PUBLIC_SHARE.fullmatch(normalized.lower()) is not None


def _paths(record: logging.LogRecord) -> list[str]:
    """Every path the record names: uvicorn's path argument, and the path in
    its formatted request line, whichever it has."""
    out = []
    args = record.args
    if isinstance(args, tuple) and len(args) >= 3 and isinstance(args[2], str):
        out.append(args[2])
    try:
        message = record.getMessage()
    except Exception:  # noqa: BLE001 - a malformed record keeps only its arguments
        message = str(record.msg)
    out.extend(_REQUEST_LINE.findall(message))
    return out


class PublicShareFilter(logging.Filter):
    """Drops the access line of a public share request."""

    def filter(self, record: logging.LogRecord) -> bool:
        return not any(is_public_share_path(path) for path in _paths(record))


def install(logger: logging.Logger | None = None) -> PublicShareFilter:
    """Adds the filter to uvicorn's access logger, once."""
    target = logger if logger is not None else logging.getLogger(LOGGER)
    for existing in target.filters:
        if isinstance(existing, PublicShareFilter):
            return existing
    added = PublicShareFilter()
    target.addFilter(added)
    return added
