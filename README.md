# ateco

Italian **ATECO** economic activity classification (ISTAT) as a pure-Python data library.

[![CI](https://github.com/DLRSP/ateco/actions/workflows/ci.yaml/badge.svg)](https://github.com/DLRSP/ateco/actions/workflows/ci.yaml)

## Features

- Editions **2007**, **2022** (ATECO 2007 aggiornamento 2022), **2025** (default)
- Canonical codes are **dotted** (`55.20.42`); compact input (`552042`) accepted
- Lazy-loaded package data via `importlib.resources` (offline, reproducible)
- Bidirectional **2025↔2022** correspondence (`map_code`)
- Explanatory notes in **Italian**; English notes planned as future `ateco[en]` in **this same repo**

## Install

```shell
pip install ateco
# future: pip install ateco[en]  # English notes (not shipped yet)
```

## Quick start

```python
import ateco

node = ateco.lookup("01.11.00")          # default edition 2025
assert ateco.validate("552042")         # compact → dotted
ed = ateco.as_of("2023-01-15")          # → 2022
mapped = ateco.map_code("01.11", "2025", "2022")
```

## Data provenance

Classification data from **ISTAT** (open data; attribute ISTAT). Package code is MIT.
Sources and checksums: `ateco.provenance()`. Maintainers rebuild datasets with `tools/build_data.py` from official ISTAT publications.

## Versioning

- Package `__version__` ≠ classification edition key
- ISTAT data refreshes → package patch/minor + towncrier `data:` fragment
- API breaks → major

## License

MIT (code) · ISTAT attribution for classification content
