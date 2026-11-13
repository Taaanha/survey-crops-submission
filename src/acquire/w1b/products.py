"""W1b catalogue: which NASA product, which layers, which route, and the source link for each.

Product IDs, layer names, fill values, scale factors and start dates were read from the public
AppEEARS product API (https://appeears.earthdatacloud.nasa.gov/api/product) and the NASA CMR
catalogue on 2026-11-10. The builders below only make request bodies; nothing here touches the
network, and no password is ever stored."""

import datetime as dt
import json
import os

APPEEARS_API = "https://appeears.earthdatacloud.nasa.gov/api"
DEMO_START, DEMO_END = "2024-01-01", "2024-12-31"  # our choice: one full year around the OPERA window
TIERS = ("standard", "field_detail")

# key -> facts. `layers` are AppEEARS layer names (None when the route is not AppEEARS).
PRODUCTS = {
    "smap": dict(
        tier="standard", route="appeears", product="SPL4SMGP.008",
        layers=["Geophysical_Data_sm_rootzone", "Geophysical_Data_sm_surface"],
        native="9 km", start="2015-03-31", unit="m3/m3", doi="10.5067/T5RUATAQREF8",
        source_url="https://nsidc.org/data/spl4smgp/versions/8"),
    "modis": dict(
        tier="standard", route="appeears", product="MOD13Q1.061",
        layers=["_250m_16_days_NDVI", "_250m_16_days_EVI", "_250m_16_days_pixel_reliability"],
        native="250 m", start="2000-02-18", unit="index (scale factor 0.0001)",
        doi="10.5067/MODIS/MOD13Q1.061",
        source_url="https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod13q1-061"),
    "nasadem": dict(
        tier="standard", route="appeears", product="NASADEM_NC.001", layers=["NASADEM_HGT"],
        native="30 m", start="2000-02-11", unit="m", doi="10.5067/MEaSUREs/NASADEM/NASADEM_NC.001",
        source_url="https://appeears.earthdatacloud.nasa.gov/api/product/NASADEM_NC.001"),
    "grace": dict(
        tier="standard", route="podaac", product="TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4",
        layers=None, native="0.5 degree mascon grid (about 300 km effective)", start="2002-04-04",
        unit="cm equivalent water thickness (anomaly from the time mean)", doi=None,
        source_url="https://podaac.jpl.nasa.gov/dataset/TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4",
        cmr_concept="C3195527175-POCLOUD"),
    "hls_l30": dict(
        tier="field_detail", route="appeears", product="HLSL30.020",
        layers=["B04", "B05", "Fmask"], native="30 m", start="2013-04-11", unit="reflectance (x0.0001)",
        doi="10.5067/HLS/HLSL30.002",
        source_url="https://appeears.earthdatacloud.nasa.gov/api/product/HLSL30.020"),
    "hls_s30": dict(
        tier="field_detail", route="appeears", product="HLSS30.020",
        layers=["B04", "B8A", "Fmask"], native="30 m", start="2015-11-28", unit="reflectance (x0.0001)",
        doi="10.5067/HLS/HLSS30.002",
        source_url="https://appeears.earthdatacloud.nasa.gov/api/product/HLSS30.020"),
    "eco_et": dict(
        tier="field_detail", route="appeears", product="ECO_L3T_JET.002",
        layers=["ETdaily", "cloud"], native="70 m", start="2018-07-10", unit="W/m2",
        doi="10.5067/ECOSTRESS/ECO_L3T_JET.002",
        source_url="https://appeears.earthdatacloud.nasa.gov/api/product/ECO_L3T_JET.002"),
    "eco_lst": dict(
        tier="field_detail", route="appeears", product="ECO_L2T_LSTE.002",
        layers=["LST", "cloud"], native="70 m", start="2018-07-09", unit="K",
        doi="10.5067/ECOSTRESS/ECO_L2T_LSTE.002",
        source_url="https://appeears.earthdatacloud.nasa.gov/api/product/ECO_L2T_LSTE.002"),
    "gedi": dict(
        tier="field_detail", route="earthdata_direct", product="GEDI_L4B_Gridded_Biomass_V2_1",
        layers=None, native="1 km", start="2019-04-18", unit="Mg/ha aboveground biomass density (confirm from the file's own metadata)",
        doi="10.3334/ORNLDAAC/2299", source_url="https://doi.org/10.3334/ORNLDAAC/2299",
        cmr_concept="C2792577683-ORNL_CLOUD",
        caveat="mostly measures trees, not field crops; context only"),
}

# Valid ranges from the AppEEARS layer records, used to catch "scale factor not applied".
VALID_RANGE = {"ndvi": (-0.2, 1.0), "evi": (-0.2, 1.0), "reflectance": (0.0, 1.0)}


def demo_field_bboxes(processed_dir):
    """{'feni': (west, south, east, north), 'cumilla': ...}: the two 20 km demo tiles built in T3,
    read from their manifests (data/processed/field_profile_manifest_<district>.json)."""
    out = {}
    for name in ("feni", "cumilla"):
        with open(os.path.join(processed_dir, f"field_profile_manifest_{name}.json"), encoding="utf-8") as fh:
            out[name] = tuple(json.load(fh)["grid"]["bbox_lonlat"])
    return out


def appeears_date(iso):
    """'2024-07-01' -> '07-01-2024' (the format AppEEARS wants)."""
    return dt.date.fromisoformat(iso).strftime("%m-%d-%Y")


def year_chunks(first_year, last_year):
    """[(start, end)] ISO date pairs, one per calendar year; keeps big 250 m requests small."""
    return [(f"{y}-01-01", f"{y}-12-31") for y in range(first_year, last_year + 1)]


def bbox_feature_collection(bbox, name="area"):
    """GeoJSON FeatureCollection with one rectangle from (west, south, east, north) degrees."""
    w, s, e, n = bbox
    if not (w < e and s < n):
        raise ValueError("bbox must be (west, south, east, north) with west < east and south < north")
    ring = [[w, s], [e, s], [e, n], [w, n], [w, s]]
    return {"type": "FeatureCollection", "features": [{
        "type": "Feature", "properties": {"id": name},
        "geometry": {"type": "Polygon", "coordinates": [ring]}}]}


def area_task(name, key, start, end, bbox, layers=None, fmt="netcdf4"):
    """AppEEARS 'area' task body for catalogue entry `key` over a rectangle.

    Output is reprojected to plain latitude/longitude ('geographic') so pixel centres are lon/lat.
    Raises if the product has no AppEEARS route or the start is before the product's first date."""
    p = PRODUCTS[key]
    if p["route"] != "appeears":
        raise ValueError(f"{key} is read through {p['route']}, not AppEEARS")
    if dt.date.fromisoformat(start) > dt.date.fromisoformat(end):
        raise ValueError("start is after end")
    use = layers or p["layers"]
    unknown = [lay for lay in use if lay not in p["layers"]]
    if unknown:
        raise ValueError(f"layers not in the catalogue for {key}: {unknown}")
    if dt.date.fromisoformat(end) < dt.date.fromisoformat(p["start"]):
        raise ValueError(f"{key} has no data before {p['start']}")
    return {
        "task_type": "area", "task_name": name,
        "params": {
            "dates": [{"startDate": appeears_date(start), "endDate": appeears_date(end)}],
            "layers": [{"product": p["product"], "layer": lay} for lay in use],
            "geo": bbox_feature_collection(bbox, name),
            "output": {"format": {"type": fmt}, "projection": "geographic"},
        },
    }
