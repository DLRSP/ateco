"""ATECO code normalization — canonical form is dotted."""

from __future__ import annotations

import re

_COMPACT_RE = re.compile(r"^[A-Za-z]\d*$|^\d{2,6}$")


def compact_to_dotted(code: str) -> str:
    """Convert compact forms like ``011100`` / ``552042`` to dotted when possible.

    Section letters stay as single letter. Numeric compact codes of length 2–6
    become ``DD``, ``DD.G``, ``DD.GG``, ``DD.GG.C``, ``DD.GG.CS``.
    """
    raw = code.strip()
    if not raw:
        return raw
    if "." in raw or (len(raw) == 1 and raw.isalpha()):
        return raw.upper() if raw.isalpha() else raw
    if raw.isalpha() and len(raw) == 1:
        return raw.upper()
    digits = raw
    if len(digits) == 2:
        return digits
    if len(digits) == 3:
        return f"{digits[:2]}.{digits[2]}"
    if len(digits) == 4:
        return f"{digits[:2]}.{digits[2:]}"
    if len(digits) == 5:
        return f"{digits[:2]}.{digits[2:4]}.{digits[4]}"
    if len(digits) == 6:
        return f"{digits[:2]}.{digits[2:4]}.{digits[4:]}"
    return raw


def canonicalize(code: str) -> str:
    """Return canonical **dotted** ATECO code (uppercase section letters)."""
    s = code.strip()
    if not s:
        raise ValueError("empty ATECO code")
    if "." not in s and not (len(s) == 1 and s.isalpha()):
        s = compact_to_dotted(s)
    # Uppercase leading section letter if present alone
    if len(s) == 1 and s.isalpha():
        return s.upper()
    return s


def normalize(code: str) -> str:
    """Alias of :func:`canonicalize` — accepts dotted or compact input."""
    return canonicalize(code)
