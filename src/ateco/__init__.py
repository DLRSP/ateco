"""Italian ATECO classification (ISTAT) — pure-Python data package.

Default edition is **2025**. Notes are Italian; English notes are a future
``ateco[en]`` evolution in this same repository.
"""

from __future__ import annotations

from ateco._api import (
    as_of,
    editions,
    get_edition,
    lookup,
    map_code,
    notes,
    provenance,
    search,
    validate,
)
from ateco._codes import canonicalize, compact_to_dotted, normalize

__version__ = "0.1.0"
__version_info__ = tuple(
    int(i) if i.isdigit() else i for i in __version__.split(".")
)
__license__ = "MIT"
__title__ = "ateco"
__author__ = "DLRSP"
__copyright__ = "Copyright 2010-present DLRSP"

VERSION = __version_info__

__all__ = [
    "__version__",
    "as_of",
    "canonicalize",
    "compact_to_dotted",
    "editions",
    "get_edition",
    "lookup",
    "map_code",
    "normalize",
    "notes",
    "provenance",
    "search",
    "validate",
]
