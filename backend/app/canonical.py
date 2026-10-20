"""RFC 8785 JSON canonicalization and definition checksums (ROUNDS-00A-L02).

A definition's checksum is ``sha256:`` and the hex SHA-256 of its RFC 8785
serialization: object keys sorted by UTF-16 code unit, no whitespace,
strings escaped as ECMAScript's ``JSON.stringify`` escapes them, and
numbers written as ECMAScript's ``Number.prototype.toString`` writes them.

Every value has to survive the trip through an IEEE 754 double, as RFC
8785 requires, so an integer past 2**53, a non-finite float, or a string
that isn't valid Unicode is refused rather than silently changed.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any

CHECKSUM_PREFIX = "sha256:"
MAX_SAFE_INTEGER = 2**53 - 1


class CanonicalError(ValueError):
    """A value RFC 8785 can't represent exactly."""


def _number(value: int | float) -> str:
    if isinstance(value, bool):
        raise CanonicalError("bool is not a number")
    if isinstance(value, int):
        if abs(value) > MAX_SAFE_INTEGER:
            raise CanonicalError(f"integer {value} is outside the IEEE 754 safe range")
        return str(value)
    if not math.isfinite(value):
        raise CanonicalError("non-finite numbers have no JSON form")
    if value == 0:
        return "0"
    # repr() gives the shortest digits that round-trip, as ECMAScript does.
    # Split it into those digits and n, the decimal point's place counted
    # from the first digit, so the value is 0.digits * 10**n.
    mantissa, _, exponent = repr(abs(value)).partition("e")
    whole, _, fraction = mantissa.partition(".")
    if whole.strip("0"):
        n = len(whole.lstrip("0"))
    else:
        n = -(len(fraction) - len(fraction.lstrip("0")))
    n += int(exponent) if exponent else 0
    digits = (whole + fraction).strip("0")
    k = len(digits)
    # ECMAScript Number::toString, steps 6 to 10.
    if k <= n <= 21:
        out = digits + "0" * (n - k)
    elif 0 < n <= 21:
        out = digits[:n] + "." + digits[n:]
    elif -6 < n <= 0:
        out = "0." + "0" * (-n) + digits
    else:
        e = n - 1
        sign = "+" if e >= 0 else "-"
        out = digits[0] + ("." + digits[1:] if k > 1 else "") + "e" + sign + str(abs(e))
    return "-" + out if value < 0 else out


def _string(value: str) -> str:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise CanonicalError("string is not valid Unicode") from None
    # Python's escaping with ensure_ascii off is JSON.stringify's: \" \\
    # \b \f \n \r \t, \u00xx for the other controls, everything else as is.
    return json.dumps(value, ensure_ascii=False)


def _utf16_key(key: str) -> bytes:
    return key.encode("utf-16-be", "surrogatepass")


def _write(value: Any, out: list[str]) -> None:
    if value is None:
        out.append("null")
    elif value is True:
        out.append("true")
    elif value is False:
        out.append("false")
    elif isinstance(value, str):
        out.append(_string(value))
    elif isinstance(value, (int, float)):
        out.append(_number(value))
    elif isinstance(value, (list, tuple)):
        out.append("[")
        for i, item in enumerate(value):
            if i:
                out.append(",")
            _write(item, out)
        out.append("]")
    elif isinstance(value, dict):
        for key in value:
            if not isinstance(key, str):
                raise CanonicalError("object keys must be strings")
        out.append("{")
        for i, key in enumerate(sorted(value, key=_utf16_key)):
            if i:
                out.append(",")
            out.append(_string(key))
            out.append(":")
            _write(value[key], out)
        out.append("}")
    else:
        raise CanonicalError(f"{type(value).__name__} has no JSON form")


def canonical(value: Any) -> bytes:
    """The RFC 8785 serialization of ``value`` as UTF-8 bytes."""
    out: list[str] = []
    _write(value, out)
    return "".join(out).encode("utf-8")


def checksum_bytes(data: bytes) -> str:
    return CHECKSUM_PREFIX + hashlib.sha256(data).hexdigest()


def checksum(value: Any) -> str:
    """``sha256:`` over the RFC 8785 serialization of ``value``."""
    return checksum_bytes(canonical(value))


def is_checksum(value: Any) -> bool:
    return (
        isinstance(value, str)
        and value.startswith(CHECKSUM_PREFIX)
        and len(value) == len(CHECKSUM_PREFIX) + 64
        and all(c in "0123456789abcdef" for c in value[len(CHECKSUM_PREFIX):])
    )
