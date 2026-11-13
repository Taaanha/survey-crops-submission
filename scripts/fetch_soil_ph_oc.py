"""Fetch SoilGrids pH and organic carbon for the 5 live-district centroids and the 2 demo
fields (centre of each 20 km demo tile), write data/processed/soilgrids_ph_oc_points.csv,
then refresh the two soil rows in docs/w1b_data_status.csv.

No key or login. About 7 calls spaced 13 s apart (service fair use: 5 calls per minute),
so it takes ~2 minutes. Run from the repo root:  python scripts/fetch_soil_ph_oc.py
"""

import json
import os
import sys

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for sub in (("src", "compute"), ("src", "acquire")):
    sys.path.insert(0, os.path.join(ROOT, *sub))

import soilgrids_ph_oc as sg  # noqa: E402
from sat_layers.status import COLUMNS, STATUS_PATH  # noqa: E402
from soil_chem import CSV_PATH, status_rows  # noqa: E402

PROC = os.path.join(ROOT, "data", "processed")


def points():
    meta = pd.read_csv(os.path.join(PROC, "district_metadata.csv"))
    pts = [{"point_id": r.district, "point_type": "district_centroid",
            "lat": round(float(r.latitude), 4), "lon": round(float(r.longitude), 4)}
           for r in meta.itertuples()]
    for name in ("feni", "cumilla"):
        with open(os.path.join(PROC, f"field_profile_manifest_{name}.json"), encoding="utf-8") as fh:
            w, s, e, n = json.load(fh)["grid"]["bbox_lonlat"]
        pts.append({"point_id": f"demo_field_{name}", "point_type": "demo_field_tile_centre",
                    "lat": round((s + n) / 2, 4), "lon": round((w + e) / 2, 4)})
    return pts


def main():
    rows = sg.fetch_rows(points())
    sg.write_csv(rows, CSV_PATH)
    status = pd.read_csv(STATUS_PATH, keep_default_na=False)
    new = pd.DataFrame(status_rows(CSV_PATH), columns=COLUMNS)
    status = pd.concat([status[~status.key.isin(new.key)], new], ignore_index=True)
    status.to_csv(STATUS_PATH, index=False)
    print("wrote", CSV_PATH, len(rows), "rows")
    print(new[["key", "status", "coverage", "reason"]].to_string(index=False))


if __name__ == "__main__":
    main()
