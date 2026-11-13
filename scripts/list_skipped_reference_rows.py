"""
scripts/list_skipped_reference_rows.py

Prints every row the strict reference loader (src/compute/reference.py) skips in data/reference/*.csv,
and the GAP rows of crop_params.csv that the water balance reports as "not assessed". The files belong
to the research teammate and are not edited here: this list is what to fix at the source.

Run from the repo root:  python scripts/list_skipped_reference_rows.py [--all]
(default: counts per file and per reason, plus the GAP rows; --all: every skipped row)
"""
import os
import sys

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "compute"))
from reference import load_reference  # noqa: E402
from water_balance import load_crop_params_report  # noqa: E402

ref = load_reference()
sk = ref.skipped
print(f"{len(ref.kept)} rows kept, {len(sk)} skipped, by reason: {ref.skipped_counts()}")
print(sk.groupby(["file", "reason"]).size().rename("rows").to_string())
if "--all" in sys.argv:
    pd.set_option("display.width", 250, "display.max_colwidth", 70, "display.max_rows", 1000)
    print(sk[["file", "line", "item", "value", "reason"]].to_string(index=False))
_, gaps = load_crop_params_report()
print(f"\ncrop_params.csv GAP rows ({len(gaps)}), reported as 'not assessed':")
for g in gaps:
    print(f"  {g['item']}: {g['status']} ({g['reason'][:90]})")
