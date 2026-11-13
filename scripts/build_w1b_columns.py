"""
scripts/build_w1b_columns.py

Writes data/processed/nasadem_grace_columns.csv: dataset, unit and source URL for every value
column of the W1b NASADEM and GRACE-FO files (acceptance rule of plan section W1). Reads only the
product catalogue in src/acquire/w1b/products.py. Run from the repo root:
    python scripts/build_w1b_columns.py
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "compute"))
sys.path.insert(0, os.path.join(ROOT, "src", "acquire"))
from w1b.tables import column_rows  # noqa: E402

SPEC = [
    ("elev_mean_m", "nasadem", 2000, 2000,
     "mean of the 30 m pixels per 0.1 degree cell, then area-weighted over the district; single 2000 acquisition; "
     "coastal cells may include sea pixels"),
    ("slope_mean_deg", "nasadem", 2000, 2000,
     "slope from the 30 m DEM (central differences), then the same averaging; sphere approximation for metres per degree"),
    ("lwe_thickness_cm", "grace", 2002, 2026,
     "REGIONAL, about 300 km effective: nearest 0.5 degree mascon cell to the district point, cell recorded per row; "
     "up to 3 districts share one cell; 261 irregular dates with gaps (longest 370 days, 2017-06 to 2018-06)"),
    ("uncertainty_cm", "grace", 2002, 2026, "JPL mascon uncertainty for the same cell and date"),
]

if __name__ == "__main__":
    out = os.path.join(ROOT, "data", "processed", "nasadem_grace_columns.csv")
    column_rows(SPEC).to_csv(out, index=False)
    print("wrote", out)
