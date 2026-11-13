"""
src/acquire/power_points.py

NASA POWER daily point data (AG community) for any latitude/longitude, with CropShift's column
names (same as src/acquire/fetch_power.py). Used for the 64 district query points. POWER is a
regional reanalysis/satellite product (about 0.5 degree), so nearby districts can share a cell;
POWER rain is NOT used for recommendations (IMERG is), see CLAUDE.md.
"""

import numpy as np
import pandas as pd
import requests

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
COLUMNS = {
    "PRECTOTCORR": "rainfall_mm",
    "T2M": "temp_mean_c",
    "T2M_MAX": "temp_max_c",
    "T2M_MIN": "temp_min_c",
    "RH2M": "rh_pct",
    "WS2M": "wind_speed_ms",
    "ALLSKY_SFC_SW_DWN": "solar_rad_mj_m2",  # MJ/m2/day under the AG community
}
SOURCE_URL = "https://power.larc.nasa.gov/docs/services/api/temporal/daily/"


def request_params(lat, lon, start, end):
    return {"parameters": ",".join(COLUMNS), "community": "AG", "longitude": lon, "latitude": lat,
            "start": start, "end": end, "format": "JSON"}


def parse_power(data):
    """POWER JSON -> (DataFrame indexed by date with project column names, elevation in m).
    -999 becomes NaN; a missing parameter raises KeyError."""
    table = pd.DataFrame({k: data["properties"]["parameter"][k] for k in COLUMNS})
    table.index = pd.to_datetime(table.index, format="%Y%m%d")
    table.index.name = "date"
    df = table.rename(columns=COLUMNS)[list(COLUMNS.values())].replace(-999, np.nan)
    return df, data["geometry"]["coordinates"][2]


def fetch_point(lat, lon, start="20010101", end="20260831", timeout=180):
    """Live POWER request. Returns (DataFrame, elevation_m, (lon, lat) POWER echoes back; this is the query point, not the native cell)."""
    r = requests.get(URL, params=request_params(lat, lon, start, end), timeout=timeout)
    r.raise_for_status()
    data = r.json()
    df, elev = parse_power(data)
    coords = data["geometry"]["coordinates"]
    return df, elev, (coords[0], coords[1])
