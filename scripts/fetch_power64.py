"""
scripts/fetch_power64.py

NASA POWER daily data (AG community, 2001-01-01 to 2026-08-31) at the query point of each of the
64 districts (polygon centroid, or a point inside the polygon if the centroid is outside).

    data/raw/power64/power_<slug>_daily.csv   daily table (gitignored, rebuildable)
    data/processed/power64_points.csv         one row per district: query point, the coordinates
                                              POWER echoes back, elevation, first/last date

Resumable (existing CSVs are kept; delete one to refetch). Free; no account needed.
Run from the repo root:  python scripts/fetch_power64.py
"""
import os
import sys
import time

import _proj  # noqa: F401  PROJ guard: keep first
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "compute"))
sys.path.insert(0, os.path.join(ROOT, "src", "acquire"))
import power_points as pp  # noqa: E402
from district_grid.boundaries import load_districts  # noqa: E402

RAW = os.path.join(ROOT, "data", "raw", "power64")
POINTS = os.path.join(ROOT, "data", "processed", "power64_points.csv")


def main():
    os.makedirs(RAW, exist_ok=True)
    rows = []
    for d in load_districts():
        slug, lat, lon = d["slug"], round(d["point"].y, 4), round(d["point"].x, 4)
        path = os.path.join(RAW, f"power_{slug}_daily.csv")
        if os.path.exists(path):
            df = pd.read_csv(path, index_col="date", parse_dates=True)
            meta = {"elevation_m": None, "echo_lon": None, "echo_lat": None}
            prev = pd.read_csv(POINTS, index_col="district") if os.path.exists(POINTS) else None
            if prev is not None and slug in prev.index:
                meta = prev.loc[slug, ["elevation_m", "echo_lon", "echo_lat"]].to_dict()
        else:
            for attempt in range(4):
                try:
                    df, elev, cell = pp.fetch_point(lat, lon)
                    break
                except Exception as err:
                    print(f"  {slug}: {type(err).__name__}, retry {attempt + 1}", flush=True)
                    time.sleep(5 * (attempt + 1))
            else:
                raise RuntimeError(f"POWER failed 4 times for {slug}")
            df.to_csv(path)
            meta = {"elevation_m": elev, "echo_lon": cell[0], "echo_lat": cell[1]}
            time.sleep(1)
        rows.append({"district": slug, "query_lat": lat, "query_lon": lon, **meta,
                     "first_date": str(df.index.min().date()), "last_date": str(df.index.max().date()),
                     "days": len(df), "source_url": pp.SOURCE_URL, "dataset": "NASA POWER daily AG (point)",
                     "retrieved": time.strftime("%Y-%m-%d")})
        print(f"{slug}: {len(df)} days", flush=True)
    pd.DataFrame(rows).set_index("district").to_csv(POINTS)
    print("wrote", POINTS)


if __name__ == "__main__":
    main()
