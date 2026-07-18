#!/usr/bin/env python3
"""Build normalized ATECO JSON datasets from ISTAT XML/XLSX (maintainer only).

Usage (from repo root, with cache present)::

    py -3.12 tools/build_data.py

Does not run at import time. Outputs under ``src/ateco/data/``.
"""
from __future__ import annotations

import hashlib
import json
import re
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "tools" / "istat_cache"
OUT = ROOT / "src" / "ateco" / "data"

LEVEL_TAGS = (
    ("sezione", "section"),
    ("divisione", "division"),
    ("gruppo", "group"),
    ("classe", "class"),
    ("categoria", "category"),
    ("sottocategoria", "subcategory"),
)

SOURCES = {
    "2007": {
        "title": "ATECO 2007",
        "xml": CACHE / "extracted" / "2007.xml",
        "url": "https://www.istat.it/wp-content/uploads/2022/03/ateco-2007.zip",
        "valid_from": "2008-01-01",
        "valid_to": "2021-12-31",
    },
    "2022": {
        "title": "ATECO 2007 aggiornamento 2022",
        "xml": CACHE / "extracted" / "2022.xml",
        "url": "https://www.istat.it/wp-content/uploads/1970/03/ateco-2007-Aggiornamento-2022.zip",
        "valid_from": "2022-01-01",
        "valid_to": "2024-12-31",
        "aliases": ["2007-2022", "ateco-2007-aggiornamento-2022"],
    },
    "2025": {
        "title": "ATECO 2025",
        "xml": CACHE / "extracted" / "2025.xml",
        "url": "https://www.istat.it/wp-content/uploads/2025/02/Struttura-e-note-esplicative-ATECO-2025-italiano.zip",
        "valid_from": "2025-01-01",
        "valid_to": None,
    },
}

CORRESPONDENCE_XLSX = CACHE / "raccordo_2025_2022.xlsx"
CORRESPONDENCE_URL = (
    "https://www.istat.it/wp-content/uploads/2025/02/"
    "Corrispondenza-bidirezionale-2025-vs-2022-IT.xlsx"
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def local(tag: str) -> str:
    return tag.split("}")[-1].lower()


def text_of(el: ET.Element | None) -> str:
    if el is None:
        return ""
    return "".join(el.itertext()).strip()


def child(el: ET.Element, name: str) -> ET.Element | None:
    for c in el:
        if local(c.tag) == name:
            return c
    return None


def parse_notes(desc_el: ET.Element | None) -> dict[str, str]:
    """Normalize ISTAT notes to IT-only structured dict."""
    if desc_el is None:
        return {}
    # 2025 nested tags
    structured: dict[str, str] = {}
    known = {
        "centrale": "centrale",
        "inclusione": "inclusione",
        "inclusioneaggiuntiva": "inclusione_aggiuntiva",
        "esclusione": "esclusione",
        "implementationrule": "implementation_rule",
    }
    for c in list(desc_el):
        key = known.get(local(c.tag))
        if key:
            val = text_of(c)
            if val:
                structured[key] = val
    if structured:
        return structured
    # Legacy flat description text
    plain = text_of(desc_el)
    return {"text": plain} if plain else {}


def compose_code(level: str, relative: str, parents: dict[str, str]) -> str:
    """Build canonical dotted ATECO code from relative XML segments."""
    rel = relative.strip()
    if level == "section":
        return rel.upper()
    if level == "division":
        return rel.zfill(2)
    division = parents["division"]
    if level == "group":
        return f"{division}.{rel}"
    group = parents["group"]  # already dotted e.g. 01.1
    if level == "class":
        return f"{group}{rel}"
    class_code = parents["class"]
    if level == "category":
        return f"{class_code}.{rel}"
    # subcategory
    category = parents["category"]
    return f"{category}{rel}"


def walk_tree(root: ET.Element) -> list[dict]:
    nodes: list[dict] = []

    def visit(el: ET.Element, parents: dict[str, str], parent_code: str | None) -> None:
        tag = local(el.tag)
        level = dict(LEVEL_TAGS).get(tag)
        if level is None:
            for c in el:
                visit(c, parents, parent_code)
            return

        code_el = child(el, "codice")
        title_el = child(el, "titolo")
        desc_el = child(el, "descrizione")
        relative = text_of(code_el)
        title = text_of(title_el)
        full = compose_code(level, relative, parents)
        notes = parse_notes(desc_el)
        nodes.append(
            {
                "code": full,
                "level": level,
                "title": title,
                "parent": parent_code,
                "notes": notes,
            }
        )
        child_parents = dict(parents)
        child_parents[level] = full
        for c in el:
            ctag = local(c.tag)
            if ctag in dict(LEVEL_TAGS):
                visit(c, child_parents, full)
            elif ctag not in ("codice", "titolo", "descrizione"):
                visit(c, child_parents, full)

    # Root may be Ateco / ateco
    for c in root:
        visit(c, {}, None)
    return nodes


def build_edition(edition: str) -> dict:
    meta = SOURCES[edition]
    xml_path: Path = meta["xml"]
    if not xml_path.exists():
        raise FileNotFoundError(xml_path)
    # ISTAT XML may declare encoding that mismatches actual bytes; recover.
    raw = xml_path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    text = re.sub(r"encoding\s*=\s*['\"][^'\"]+['\"]", 'encoding="utf-8"', text, count=1)
    root = ET.fromstring(text.encode("utf-8"))
    nodes = walk_tree(root)
    by_code = {n["code"]: n for n in nodes}
    if len(by_code) != len(nodes):
        # keep first; log duplicates lightly
        pass
    return {
        "edition": edition,
        "title": meta["title"],
        "valid_from": meta["valid_from"],
        "valid_to": meta["valid_to"],
        "source_url": meta["url"],
        "source_sha256": sha256_file(xml_path),
        "node_count": len(nodes),
        "nodes": nodes,
    }


def read_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    out: list[str] = []
    for si in root.findall("m:si", ns):
        texts = [
            t.text or ""
            for t in si.iter(
                "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"
            )
        ]
        out.append("".join(texts))
    return out


def build_correspondence() -> dict:
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(CORRESPONDENCE_XLSX) as zf:
        strings = read_shared_strings(zf)
        sheet = ET.fromstring(zf.read("xl/worksheets/sheet2.xml"))
        rows = sheet.findall("m:sheetData/m:row", ns)
        mappings: list[dict] = []
        header: list[str] | None = None
        for row in rows:
            vals: list[str] = []
            for c in row.findall("m:c", ns):
                t = c.get("t")
                v = c.find("m:v", ns)
                if v is None:
                    vals.append("")
                    continue
                raw = v.text or ""
                if t == "s":
                    raw = strings[int(raw)]
                vals.append(raw)
            if not any(vals):
                continue
            if header is None:
                header = vals
                continue
            # Pad
            while len(vals) < len(header):
                vals.append("")
            rec = dict(zip(header, vals, strict=False))
            code_2025 = (rec.get("CODICE_ATECO_2025") or "").strip()
            code_2022 = (rec.get("CODICE_ATECO_2022") or "").strip()
            if not code_2025 or not code_2022:
                continue
            mappings.append(
                {
                    "code_2025": code_2025,
                    "code_2022": code_2022,
                    "coverage_2025": (rec.get("COPERTURA_ATECO_2025") or "").strip(),
                    "coverage_2022": (rec.get("COPERTURA_ATECO_2022") or "").strip(),
                    "hierarchy": (rec.get("GERARCHIA") or "").strip(),
                    "n_corr_2025": (rec.get("NUMERO_CORR_ATECO_2025") or "").strip(),
                    "n_corr_2022": (rec.get("NUMERO_CORR_ATECO_2022") or "").strip(),
                }
            )
    return {
        "table": "theoretical",
        "from_edition": "2025",
        "to_edition": "2022",
        "source_url": CORRESPONDENCE_URL,
        "source_sha256": sha256_file(CORRESPONDENCE_XLSX),
        "row_count": len(mappings),
        "mappings": mappings,
    }


def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    editions_meta = []
    provenance_sources = []

    for edition in ("2007", "2022", "2025"):
        print(f"building {edition}…")
        data = build_edition(edition)
        ed_dir = OUT / edition
        write_json(ed_dir / "nodes.json", {"nodes": data["nodes"]})
        editions_meta.append(
            {
                "key": edition,
                "title": data["title"],
                "valid_from": data["valid_from"],
                "valid_to": data["valid_to"],
                "aliases": SOURCES[edition].get("aliases", []),
                "node_count": data["node_count"],
                "notes_language": "it",
                "default": edition == "2025",
            }
        )
        provenance_sources.append(
            {
                "edition": edition,
                "url": data["source_url"],
                "sha256": data["source_sha256"],
                "node_count": data["node_count"],
            }
        )
        print(f"  nodes={data['node_count']}")

    print("building correspondence 2025-2022...")
    corr = build_correspondence()
    write_json(OUT / "correspondence" / "2025_2022.json", corr)
    provenance_sources.append(
        {
            "kind": "correspondence",
            "url": corr["source_url"],
            "sha256": corr["source_sha256"],
            "row_count": corr["row_count"],
        }
    )
    print(f"  rows={corr['row_count']}")

    write_json(
        OUT / "editions.json",
        {
            "default": "2025",
            "notes_language": "it",
            "notes_en": "deferred — future ateco[en] extra in same repo",
            "editions": editions_meta,
        },
    )
    write_json(
        OUT / "provenance.json",
        {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "ingest_date": date.today().isoformat(),
            "license_note": (
                "Classification data (c) ISTAT; redistribution under ISTAT open-data "
                "terms (CC-BY 4.0) with attribution. Package code MIT (DLRSP)."
            ),
            "attribution": "Istituto Nazionale di Statistica (ISTAT) — Classificazione ATECO",
            "docs": "https://www.istat.it/classificazione/documenti-ateco/",
            "sources": provenance_sources,
        },
    )
    print("done ->", OUT)


if __name__ == "__main__":
    main()
