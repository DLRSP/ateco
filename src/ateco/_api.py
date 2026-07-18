"""Public ATECO API — editions, lookup, validate, search, map_code."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Iterable, Literal

from ateco._codes import canonicalize
from ateco._load import (
    editions_meta,
    load_correspondence_2025_2022,
    load_nodes,
    provenance_meta,
)

TableKind = Literal["theoretical", "operational"]


@dataclass(frozen=True)
class Edition:
    key: str
    title: str
    valid_from: date | None
    valid_to: date | None
    aliases: tuple[str, ...]
    node_count: int
    notes_language: str = "it"


@dataclass(frozen=True)
class AtecoNode:
    code: str
    level: str
    title: str
    parent: str | None
    notes: dict[str, str]
    edition: str


@dataclass(frozen=True)
class MapResult:
    source: str
    targets: tuple[str, ...]
    ambiguous: bool
    coverages: tuple[str, ...]
    table: str


def _parse_day(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def editions() -> list[Edition]:
    meta = editions_meta()
    out: list[Edition] = []
    for row in meta["editions"]:
        out.append(
            Edition(
                key=row["key"],
                title=row["title"],
                valid_from=_parse_day(row.get("valid_from")),
                valid_to=_parse_day(row.get("valid_to")),
                aliases=tuple(row.get("aliases") or ()),
                node_count=int(row["node_count"]),
                notes_language=row.get("notes_language", "it"),
            )
        )
    return out


def get_edition(key: str = "2025") -> Edition:
    key_l = key.strip()
    for ed in editions():
        if ed.key == key_l or key_l in ed.aliases:
            return ed
    raise KeyError(f"unknown ATECO edition: {key!r}")


def as_of(when: date | datetime | str) -> Edition:
    """Resolve the edition in force on a calendar day (default rules)."""
    if isinstance(when, datetime):
        day = when.date()
    elif isinstance(when, date):
        day = when
    else:
        day = date.fromisoformat(str(when))
    # Prefer the unique edition whose [from, to] contains day; else latest started.
    candidates: list[Edition] = []
    for ed in editions():
        if ed.valid_from and day < ed.valid_from:
            continue
        if ed.valid_to and day > ed.valid_to:
            continue
        candidates.append(ed)
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        return sorted(candidates, key=lambda e: e.valid_from or date.min)[-1]
    # Before first known — return earliest
    return sorted(editions(), key=lambda e: e.valid_from or date.min)[0]


def _resolve_edition(edition: str | None = None, as_of_day: date | str | None = None) -> str:
    if as_of_day is not None:
        return as_of(as_of_day).key
    if edition is None:
        return editions_meta()["default"]
    return get_edition(edition).key


def lookup(
    code: str,
    *,
    edition: str | None = None,
    as_of: date | str | None = None,
) -> AtecoNode | None:
    ed = _resolve_edition(edition, as_of)
    canon = canonicalize(code)
    node = load_nodes(ed).get(canon)
    if node is None:
        return None
    return AtecoNode(
        code=node["code"],
        level=node["level"],
        title=node["title"],
        parent=node.get("parent"),
        notes=dict(node.get("notes") or {}),
        edition=ed,
    )


def validate(
    code: str,
    *,
    edition: str | None = None,
    as_of: date | str | None = None,
) -> bool:
    return lookup(code, edition=edition, as_of=as_of) is not None


def notes(
    code: str,
    *,
    edition: str | None = None,
    as_of: date | str | None = None,
    lang: str = "it",
) -> dict[str, str]:
    """Return explanatory notes for a code.

    Only Italian notes are shipped in v1. ``lang='en'`` raises until the future
    ``ateco[en]`` data extra is published in this repository.
    """
    if lang.lower() != "it":
        raise LookupError(
            "English notes are not bundled yet; planned as ateco[en] in this repo"
        )
    node = lookup(code, edition=edition, as_of=as_of)
    if node is None:
        raise KeyError(code)
    return dict(node.notes)


def search(
    query: str,
    *,
    edition: str | None = None,
    as_of: date | str | None = None,
    limit: int = 50,
) -> list[AtecoNode]:
    ed = _resolve_edition(edition, as_of)
    q = query.strip().lower()
    if not q:
        return []
    hits: list[AtecoNode] = []
    for node in load_nodes(ed).values():
        blob = f"{node['code']} {node['title']}".lower()
        notes_blob = " ".join((node.get("notes") or {}).values()).lower()
        if q in blob or q in notes_blob:
            hits.append(
                AtecoNode(
                    code=node["code"],
                    level=node["level"],
                    title=node["title"],
                    parent=node.get("parent"),
                    notes=dict(node.get("notes") or {}),
                    edition=ed,
                )
            )
            if len(hits) >= limit:
                break
    return hits


def map_code(
    code: str,
    from_edition: str,
    to_edition: str,
    *,
    table: TableKind = "theoretical",
) -> MapResult:
    """Map a code between editions.

    v1 ships the ISTAT bidirectional theoretical table for 2025↔2022.
    Operational table is reserved for a later data revision.
    """
    if table != "theoretical":
        raise NotImplementedError(
            "operational correspondence table not bundled yet (ISTAT tabella operativa)"
        )
    src = canonicalize(code)
    fr = get_edition(from_edition).key
    to = get_edition(to_edition).key
    pair = {fr, to}
    if pair != {"2022", "2025"}:
        raise NotImplementedError(
            f"no correspondence table for {fr!r} → {to!r} in this release"
        )
    data = load_correspondence_2025_2022()
    targets: list[str] = []
    coverages: list[str] = []
    if fr == "2025" and to == "2022":
        for row in data["mappings"]:
            if row["code_2025"] == src:
                targets.append(row["code_2022"])
                coverages.append(row.get("coverage_2025") or "")
    else:
        for row in data["mappings"]:
            if row["code_2022"] == src:
                targets.append(row["code_2025"])
                coverages.append(row.get("coverage_2022") or "")
    # unique preserve order
    seen: set[str] = set()
    uniq: list[str] = []
    cov_u: list[str] = []
    for t, c in zip(targets, coverages, strict=False):
        if t in seen:
            continue
        seen.add(t)
        uniq.append(t)
        cov_u.append(c)
    return MapResult(
        source=src,
        targets=tuple(uniq),
        ambiguous=len(uniq) != 1,
        coverages=tuple(cov_u),
        table=table,
    )


def provenance() -> dict[str, Any]:
    return dict(provenance_meta())
