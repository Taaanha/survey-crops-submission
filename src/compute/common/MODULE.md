# common (shared contracts)
Layer: 1 compute
Code: src/compute/common/provenance.py
Purpose (2–3 sentences): The one shared contract every new feature module may import. A `Provenance` names the dataset, the page it can be checked on, the day it was retrieved and the exact granule or file; `measured()` returns a number with its unit and that provenance. Nothing else lives here.
Public API (exact signatures + one-line description each):
- `measured(value, unit, provenance)` : returns {"value", "unit", "provenance"}; raises TypeError if provenance is not a Provenance.
- Class `Provenance` with fields dataset, source_url, retrieved, granule_or_file and note (default empty) : frozen dataclass; the first four fields must be non-blank (ValueError otherwise); `to_dict()` returns a plain dict.
Inputs (data files / other modules) and their provenance: none.
Outputs (shape + units + provenance fields): {"value", "unit", "provenance": {dataset, source_url, retrieved, granule_or_file, note}}.
Reference tables used (data/reference/*.csv rows): none.
Tests (file names + what each proves): tests/common/test_common_provenance.py (a number cannot be built without a source; immutability).
Known limitations / honest caveats: not used by any old code yet. `guard()` reads the key `url`, while this contract uses `source_url`; T17 must align them. The API still uses {value, unit, src}.
CHAT KIT: src/compute/common/MODULE.md, src/compute/common/provenance.py, tests/common/test_common_provenance.py
Last changed: 2026-10-24 by session A (partition)
