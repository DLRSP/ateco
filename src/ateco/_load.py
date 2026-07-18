"""Lazy loaders for vendored ISTAT datasets via importlib.resources."""

from __future__ import annotations

import json
import threading
from functools import lru_cache
from importlib import resources
from typing import Any


_lock = threading.Lock()
_edition_nodes: dict[str, dict[str, dict[str, Any]]] = {}
_edition_list: dict[str, Any] | None = None
_corr_2025_2022: dict[str, Any] | None = None
_provenance: dict[str, Any] | None = None


def _read_json(package: str, *parts: str) -> Any:
    root = resources.files(package)
    node = root.joinpath(*parts)
    with node.open("r", encoding="utf-8") as f:
        return json.load(f)


def editions_meta() -> dict[str, Any]:
    global _edition_list
    if _edition_list is None:
        with _lock:
            if _edition_list is None:
                _edition_list = _read_json("ateco", "data", "editions.json")
    return _edition_list


def provenance_meta() -> dict[str, Any]:
    global _provenance
    if _provenance is None:
        with _lock:
            if _provenance is None:
                _provenance = _read_json("ateco", "data", "provenance.json")
    return _provenance


def load_nodes(edition: str) -> dict[str, dict[str, Any]]:
    """Return code → node map for an edition (lazy, cached)."""
    if edition not in _edition_nodes:
        with _lock:
            if edition not in _edition_nodes:
                payload = _read_json("ateco", "data", edition, "nodes.json")
                _edition_nodes[edition] = {n["code"]: n for n in payload["nodes"]}
    return _edition_nodes[edition]


def load_correspondence_2025_2022() -> dict[str, Any]:
    global _corr_2025_2022
    if _corr_2025_2022 is None:
        with _lock:
            if _corr_2025_2022 is None:
                _corr_2025_2022 = _read_json(
                    "ateco", "data", "correspondence", "2025_2022.json"
                )
    return _corr_2025_2022


@lru_cache(maxsize=1)
def cold_import_guard() -> bool:
    """True if package imported without loading edition trees."""
    return "2025" not in _edition_nodes
