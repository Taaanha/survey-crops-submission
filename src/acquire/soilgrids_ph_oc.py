"""
src/acquire/soilgrids_ph_oc.py

Soil pH (phh2o) and organic carbon (soc) at point locations from ISRIC SoilGrids 2.0
(250 m model estimate, NOT a soil test), for three topsoil layers (0-5, 5-15, 15-30 cm):
the mean plus the service's own quantiles Q0.05, Q0.5, Q0.95.

Licence: CC BY 4.0 (https://docs.isric.org/globaldata/soilgrids/index.html). The REST
API needs no key or login. Fair use is 5 calls per minute, so calls are spaced by
PAUSE_S seconds. Cite: Poggio et al. 2021, SOIL 7, 217-240,
https://doi.org/10.5194/soil-7-217-2021.

Units are NEVER assumed: every layer in the response carries unit_measure.d_factor
(SoilGrids stores pH x10 and organic carbon in dg/kg) and the value is raw / d_factor.
If the mapped_units string is not one we know, the point is refused.

Output is a long table, one row per (point, property, depth, statistic). A masked cell
(the service answers 200 with null) or a failed call becomes a gap row with the reason,
never a number. Nothing is interpolated or taken from a neighbouring cell.
"""

import csv
import datetime as dt
import time

import requests

URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
DOCS_URL = "https://docs.isric.org/globaldata/soilgrids/index.html"
DATASET = "ISRIC SoilGrids 2.0 (CC BY 4.0; Poggio et al. 2021, doi:10.5194/soil-7-217-2021)"
RESOLUTION = "250 m"
PROPERTIES = ("phh2o", "soc")
DEPTHS = ("0-5cm", "5-15cm", "15-30cm")
STATISTICS = ("mean", "Q0.05", "Q0.5", "Q0.95")
# property -> (mapped units we have verified from the service metadata, output unit)
KNOWN_UNITS = {"phh2o": ("pH*10", "pH"), "soc": ("dg/kg", "g/kg")}
PAUSE_S = 13            # fair use: 5 calls per minute
TIMEOUT_S = 60          # the service sometimes needs ~10 s per call
COLUMNS = ["point_id", "point_type", "lat", "lon", "property", "depth", "statistic",
           "raw_value", "d_factor", "value", "units", "mapped_units", "dataset",
           "source_url", "resolution", "fetch_date", "status", "reason", "query"]


class SoilGridsError(Exception):
    """The service answer cannot be read with the units we have verified."""


def _query(point):
    return f"{URL}?lon={point['lon']}&lat={point['lat']}"


def _row(point, prop, depth, stat, fetch_date, **kw):
    base = {"point_id": point["point_id"], "point_type": point["point_type"],
            "lat": point["lat"], "lon": point["lon"], "property": prop, "depth": depth,
            "statistic": stat, "raw_value": "", "d_factor": "", "value": "",
            "units": KNOWN_UNITS[prop][1], "mapped_units": "", "dataset": DATASET,
            "source_url": DOCS_URL, "resolution": RESOLUTION, "fetch_date": fetch_date,
            "status": "gap", "reason": "", "query": _query(point)}
    base.update(kw)
    return base


def gap_rows(point, reason, fetch_date):
    return [_row(point, p, d, s, fetch_date, reason=reason)
            for p in PROPERTIES for d in DEPTHS for s in STATISTICS]


def parse_point(payload, point, fetch_date):
    """SoilGrids JSON -> 24 rows (2 properties x 3 depths x 4 statistics)."""
    try:
        layers = {layer["name"]: layer for layer in payload["properties"]["layers"]}
    except (KeyError, TypeError) as err:
        raise SoilGridsError(f"unexpected response shape ({type(err).__name__})") from err
    rows = []
    for prop in PROPERTIES:
        layer = layers.get(prop)
        if layer is None:
            rows += [_row(point, prop, d, s, fetch_date, reason=f"{prop} not in the response")
                     for d in DEPTHS for s in STATISTICS]
            continue
        um = layer["unit_measure"]
        if um.get("mapped_units") != KNOWN_UNITS[prop][0]:
            raise SoilGridsError(f"{prop}: mapped_units {um.get('mapped_units')!r} is not the "
                                 f"verified {KNOWN_UNITS[prop][0]!r}; not converting")
        d_factor = um["d_factor"]
        by_depth = {d["label"]: d["values"] for d in layer["depths"]}
        for depth in DEPTHS:
            values = by_depth.get(depth, {})
            for stat in STATISTICS:
                raw = values.get(stat)
                if raw is None:
                    rows.append(_row(point, prop, depth, stat, fetch_date, d_factor=d_factor,
                                     mapped_units=um["mapped_units"],
                                     reason="SoilGrids returned null (masked cell or no data)"))
                else:
                    rows.append(_row(point, prop, depth, stat, fetch_date, raw_value=raw,
                                     d_factor=d_factor, value=round(raw / d_factor, 4),
                                     mapped_units=um["mapped_units"], status="assessed"))
    return rows


def fetch_payload(point, get=None):
    params = [("lon", point["lon"]), ("lat", point["lat"])]
    params += [("property", p) for p in PROPERTIES] + [("depth", d) for d in DEPTHS]
    params += [("value", s) for s in STATISTICS]
    try:
        response = (get or requests.get)(URL, params=params, timeout=TIMEOUT_S)
    except requests.RequestException as err:
        raise SoilGridsError(type(err).__name__) from err
    if response.status_code != 200:
        raise SoilGridsError(f"HTTP {response.status_code}")
    try:
        return response.json()
    except ValueError as err:
        raise SoilGridsError("answer was not JSON") from err


def fetch_rows(points, get=None, sleep=time.sleep, fetch_date=None):
    """One call per point, PAUSE_S apart. A failed point becomes gap rows."""
    fetch_date = fetch_date or dt.date.today().isoformat()
    rows = []
    for i, point in enumerate(points):
        if i:
            sleep(PAUSE_S)
        for attempt in (1, 2):          # a failed call is retried once; a masked cell is not
            try:
                rows += parse_point(fetch_payload(point, get), point, fetch_date)
                break
            except SoilGridsError as err:
                if attempt == 2:
                    rows += gap_rows(point, f"fetch failed twice: {err}", fetch_date)
                else:
                    sleep(PAUSE_S)
    return rows


def write_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
