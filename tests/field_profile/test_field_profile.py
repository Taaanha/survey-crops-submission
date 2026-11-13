"""T3a/T3b acceptance tests: class encoding, merge, grid, manifest, offline fixture.

Encoding (T3b): 2 = open water, 1 = inundated vegetation / partial water, 0 = not water,
255 = no observation. Class tables come from
data/reference/opera_classes.csv (OPERA DSWx-HLS spec D-107395 Rev B and DSWx-S1
spec D-108761 Rev A, Table 4-1 in both)."""

import csv
import json
import os

import numpy as np
import pytest

from field_profile import (NO_OBS, NOT_WATER, OPEN_WATER, PARTIAL_WATER, district_grid,
                           encode_hls, encode_s1, merge_water, validate_manifest)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CLASSES_CSV = os.path.join(ROOT, "data", "reference", "opera_classes.csv")
FIXTURE_DIR = os.path.join(ROOT, "tests", "fixtures", "field_profile")


def class_table():
    with open(CLASSES_CSV, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# ---------- encoding ----------

def test_constants():
    assert (OPEN_WATER, PARTIAL_WATER, NOT_WATER, NO_OBS) == (2, 1, 0, 255)


def test_encode_hls_matches_cited_table():
    # HLS WTR: 0 not water, 1 open water, 2 partial surface water, 252 snow/ice,
    # 253 cloud/shadow, 254 ocean masked, 255 fill.
    raw = np.array([[0, 1, 2], [252, 253, 254], [255, 0, 1]], dtype=np.uint8)
    out = encode_hls(raw)
    assert out.dtype == np.uint8
    assert out.tolist() == [[0, 2, 1], [255, 255, 255], [255, 0, 2]]


def test_encode_s1_matches_cited_table():
    # S1 WTR: 0 not water, 1 open water, 3 inundated vegetation, 250 HAND masked,
    # 251 layover/shadow masked, 255 fill.
    raw = np.array([[0, 1, 3], [250, 251, 255]], dtype=np.uint8)
    out = encode_s1(raw)
    assert out.tolist() == [[0, 2, 1], [0, 255, 255]]  # HAND-masked 250 -> rule default: not water
    out = encode_s1(raw, hand_masked_as="no_observation")
    assert out.tolist() == [[0, 2, 1], [255, 255, 255]]
    with pytest.raises(ValueError):
        encode_s1(raw, hand_masked_as="water")


def test_unknown_class_code_raises():
    with pytest.raises(ValueError):
        encode_hls(np.array([7], dtype=np.uint8))
    with pytest.raises(ValueError):
        encode_s1(np.array([2], dtype=np.uint8))  # code 2 does not exist in DSWx-S1


def test_class_csv_agrees_with_encoders():
    # the CSV 'value' column is the state used by the default rules (HAND-masked 250 -> 0)
    rows = class_table()
    assert rows, "opera_classes.csv is empty"
    for prefix, encode in (("dswx_hls.wtr.", encode_hls), ("dswx_s1.wtr.", encode_s1)):
        mine = [r for r in rows if r["item"].startswith(prefix)]
        assert mine
        for r in mine:
            assert r["source_url"].startswith("http")
            code = int(r["item"][len(prefix):])
            got = int(encode(np.array([code], dtype=np.uint8))[0])
            assert got == int(r["value"]), r["item"]


# ---------- HLS + S1 merge ----------

def test_merge_water_wins():
    hls = np.array([0, 2, 0, 255, 255, 2, 1, 1], dtype=np.uint8)
    s1 = np.array([2, 0, 0, 1, 0, 255, 2, 0], dtype=np.uint8)
    # open water beats partial/vegetation, which beats not water, which beats no observation
    assert merge_water(hls, s1).tolist() == [2, 2, 0, 1, 0, 2, 2, 1]


def test_merge_missing_only_if_all_missing():
    a = np.array([255, 255, 0], dtype=np.uint8)
    b = np.array([255, 0, 255], dtype=np.uint8)
    assert merge_water(a, b).tolist() == [255, 0, 0]


def test_merge_many_and_single():
    a = np.array([255, 0, 0], dtype=np.uint8)
    b = np.array([255, 255, 2], dtype=np.uint8)
    c = np.array([255, 255, 0], dtype=np.uint8)
    assert merge_water(a, b, c).tolist() == [255, 0, 2]
    assert merge_water(a).tolist() == a.tolist()


def test_merge_rejects_shape_mismatch_and_empty():
    with pytest.raises(ValueError):
        merge_water(np.zeros((2, 2), np.uint8), np.zeros((3, 3), np.uint8))
    with pytest.raises(ValueError):
        merge_water()


# ---------- grid ----------

def test_district_grid_equals_fetch_dswx_grid():
    """The copy in field_profile must never drift from scripts/fetch_dswx.py (T3b fix c)."""
    import importlib.util
    import sys
    scripts = os.path.join(ROOT, "scripts")
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location("fetch_dswx_for_test",
                                                      os.path.join(scripts, "fetch_dswx.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(scripts)
    from field_profile.core import DISTRICT_POINTS
    for name in ("feni", "cumilla"):
        lat, lon = mod.DISTRICTS[name]["lat"], mod.DISTRICTS[name]["lon"]
        assert DISTRICT_POINTS[name] == (lat, lon)
        crs, aff, n = mod.area_grid(lat, lon)
        g = district_grid(name)
        assert g["crs"] == f"EPSG:{crs.to_epsg()}"
        assert list(g["transform"]) == [aff.a, aff.b, aff.c, aff.d, aff.e, aff.f]
        assert g["width"] == g["height"] == n
        assert np.allclose(g["bbox_lonlat"], mod.grid_bbox_lonlat((crs, aff, n)))

def test_district_grid_is_30m_and_snapped():
    for name in ("feni", "cumilla"):
        g = district_grid(name)
        assert g["res"] == 30.0 and g["width"] == g["height"] == 667
        assert g["crs"] == "EPSG:32646"
        left, top = g["transform"][2], g["transform"][5]
        assert left % 30 == 0 and top % 30 == 0
        w, s, e, n = g["bbox_lonlat"]
        assert 90.5 < w < e < 92 and 22 < s < n < 24


def test_district_grid_unknown_district():
    with pytest.raises(KeyError):
        district_grid("atlantis")


# ---------- manifest ----------

def good_manifest():
    return {
        "district": "feni",
        "grid": district_grid("feni"),
        "classes_reference": "data/reference/opera_classes.csv",
        "dates": [
            {"date": "2024-08-21",
             "granules": {"DSWx-S1": ["OPERA_L3_DSWx-S1_T46QCL_20240821T120455Z_x"], "DSWx-HLS": []},
             "source_urls": ["https://example.org/a_B01_WTR.tif"]},
        ],
    }


def test_manifest_valid():
    assert validate_manifest(good_manifest()) == []


def test_manifest_flags_date_without_granule_or_url():
    m = good_manifest()
    m["dates"][0]["granules"] = {"DSWx-S1": [], "DSWx-HLS": []}
    assert any("granule" in p for p in validate_manifest(m))
    m = good_manifest()
    m["dates"][0]["source_urls"] = []
    assert any("source" in p for p in validate_manifest(m))


def test_manifest_flags_duplicate_dates_and_missing_keys():
    m = good_manifest()
    m["dates"].append(dict(m["dates"][0]))
    assert any("duplicate" in p for p in validate_manifest(m))
    assert validate_manifest({"district": "feni"})


# ---------- real fixture (offline) ----------

def load_fixture():
    meta = json.load(open(os.path.join(FIXTURE_DIR, "feni_river_meta.json"), encoding="utf-8"))
    arrays = np.load(os.path.join(FIXTURE_DIR, "feni_river_50x50.npz"))
    return meta, arrays


def test_fixture_is_small():
    for name in os.listdir(FIXTURE_DIR):
        assert os.path.getsize(os.path.join(FIXTURE_DIR, name)) < 200_000
    meta, arrays = load_fixture()
    assert arrays["merged"].shape[1:] == (50, 50)
    assert arrays["merged"].shape[0] == len(meta["dates"]) >= 3


def test_fixture_manifest_part_is_valid():
    meta, _ = load_fixture()
    assert validate_manifest({"district": "feni", "grid": meta["grid"],
                              "classes_reference": "data/reference/opera_classes.csv",
                              "dates": meta["dates"]}) == []


def test_fixture_raw_codes_are_documented_and_reproduce_merged():
    meta, arrays = load_fixture()
    documented = {"DSWx-HLS": {0, 1, 2, 252, 253, 254, 255}, "DSWx-S1": {0, 1, 3, 250, 251, 255}}
    for i, d in enumerate(meta["dates"]):
        parts = []
        for key, product, enc in (("hls", "DSWx-HLS", encode_hls), ("s1", "DSWx-S1", encode_s1)):
            raw = arrays[f"{key}_raw"][i]
            assert set(np.unique(raw).tolist()) <= documented[product]
            if d["granules"][product]:
                parts.append(enc(raw))
        assert parts, d["date"]
        assert np.array_equal(merge_water(*parts), arrays["merged"][i]), d["date"]


def test_fixture_river_channel_is_open_water_on_nearly_all_observed_dates():
    meta, arrays = load_fixture()
    cy, cx = meta["channel_pixel"]
    col = arrays["merged"][:, cy, cx]
    observed = col != NO_OBS
    assert observed.sum() >= 3
    assert (col[observed] == OPEN_WATER).mean() >= 0.9
    # the window also contains land, so it is not a uniform block
    assert (arrays["merged"] == NOT_WATER).any()
