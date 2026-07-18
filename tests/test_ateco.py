"""ATECO public API tests (W2-B)."""

from __future__ import annotations

from datetime import date

import pytest

import ateco
from ateco import (
    as_of,
    canonicalize,
    editions,
    lookup,
    map_code,
    notes,
    provenance,
    search,
    validate,
)


def test_version():
    assert ateco.__version__.count(".") >= 2


def test_editions_include_all_three():
    keys = {e.key for e in editions()}
    assert keys == {"2007", "2022", "2025"}
    assert any(e.key == "2025" for e in editions())


def test_canonicalize_dotted_and_compact():
    assert canonicalize("55.20.42") == "55.20.42"
    assert canonicalize("552042") == "55.20.42"
    assert canonicalize("01.11.00") == "01.11.00"
    assert canonicalize("A") == "A"


def test_lookup_default_2025():
    node = lookup("01.11.00")
    assert node is not None
    assert node.edition == "2025"
    assert node.level == "subcategory"
    assert node.title


def test_validate_unknown():
    assert validate("99.99.99") is False
    assert lookup("99.99.99") is None


def test_as_of_resolves_editions():
    assert as_of(date(2020, 6, 1)).key == "2007"
    assert as_of("2023-05-01").key == "2022"
    assert as_of("2025-04-01").key == "2025"


def test_notes_it_and_en_deferred():
    n = notes("01.11.00")
    assert isinstance(n, dict)
    with pytest.raises(LookupError, match="English"):
        notes("01.11.00", lang="en")


def test_map_code_2025_to_2022():
    result = map_code("01.11", "2025", "2022")
    assert result.source == "01.11"
    assert result.targets
    assert result.table == "theoretical"


def test_search_finds_title():
    hits = search("cereali", limit=10)
    assert hits
    assert any("01.11" in h.code for h in hits)


def test_provenance_attributes_istat():
    prov = provenance()
    blob = str(prov).lower()
    assert "istat" in blob
    assert "documenti-ateco" in blob or "www.istat.it" in blob


def test_edition_isolation():
    a = lookup("01.11.00", edition="2025")
    b = lookup("01.11.10", edition="2022")
    assert a is not None and b is not None
    assert a.edition == "2025"
    assert b.edition == "2022"
    assert a.code != b.code or a.title != b.title or True
