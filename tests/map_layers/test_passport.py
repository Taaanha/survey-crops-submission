"""W5 Field Passport (Layer 1): demo fields only, every layer at its real pixel size, layers that
are not in the repo are 'not assessed' with the reason, never zeros."""

import json
import os
import re

import numpy as np
import pytest

from map_layers import passport as pp


def test_two_demo_fields_with_a_stated_location_source():
    fields = pp.demo_fields()
    assert {f["id"] for f in fields} == {"CUM-ARF-01", "CUM-BRRI-02"}
    for f in fields:
        assert f["district"] == "cumilla" and f["location_source"]


def test_unknown_field_is_an_error():
    with pytest.raises(KeyError):
        pp.field_passport("NOPE-01")


@pytest.fixture(scope="module")
def passport():
    return pp.field_passport("CUM-ARF-01", half_width=7)


def test_elevation_window_is_the_real_30m_grid(passport):
    layer = {x["key"]: x for x in passport["layers"]}["nasadem_elevation_30m"]
    assert layer["status"] == "assessed" and layer["pixel_size_m"] == 30
    g = np.array(layer["grid"], dtype=float)
    assert g.shape == (15, 15)
    z = np.load("data/processed/nasadem_30m_cumilla.npz")
    lat_i = int(np.argmin(abs(z["lats"] - passport["field"]["lat"])))
    lon_i = int(np.argmin(abs(z["lons"] - passport["field"]["lon"])))
    assert g[7, 7] == float(z["elev_m"][lat_i, lon_i])
    assert g[0, 0] == float(z["elev_m"][lat_i - 7, lon_i - 7])        # north-west corner first
    assert layer["source_url"].startswith("https://appeears")
    assert layer["extent_m"] == 15 * 30


def test_slope_window_is_derived_and_called_relative(passport):
    layer = {x["key"]: x for x in passport["layers"]}["nasadem_slope_30m"]
    assert layer["status"] == "assessed" and layer["pixel_size_m"] == 30
    assert any("relative" in c.lower() for c in layer["caveats"])
    assert any("derived" in c.lower() for c in layer["caveats"])
    g = np.array(layer["grid"], dtype=float)
    assert g.shape == (15, 15) and np.nanmin(g) >= 0 and np.nanmax(g) < 90


def test_nodata_pixels_are_none_never_zero(tmp_path):
    tile = tmp_path / "nasadem_30m_t.npz"
    e = np.full((9, 9), 12, dtype=np.int16)
    e[4, 4] = -32768
    np.savez(tile, elev_m=e, lats=np.linspace(23.5, 23.4, 9), lons=np.linspace(91.1, 91.2, 9))
    out = pp.elevation_window("t", 23.45, 91.15, half_width=1, data_dir=str(tmp_path))
    assert out["grid"][1][1] is None and out["grid"][0][0] == 12


def test_layers_not_in_the_repo_are_not_assessed_with_a_reason(passport):
    layers = {x["key"]: x for x in passport["layers"]}
    for key in ("hls_ndvi_30m", "ecostress_et_70m", "smap_9km", "modis_ndvi_250m"):
        x = layers[key]
        assert x["status"] == "not assessed" and x["reason"] and x["grid"] is None
        assert x["pixel_size_m"] in (30, 70, 9000, 250)


def test_flood_history_layer_is_assessed_only_if_t3b_layers_exist(tmp_path):
    empty = pp.field_passport("CUM-ARF-01", half_width=2, layers_dir=str(tmp_path))
    x = {y["key"]: y for y in empty["layers"]}["opera_inundation_days_30m"]
    assert x["status"] == "not assessed" and "T3b" in x["reason"] and x["grid"] is None


@pytest.mark.skipif(not os.path.exists("data/raw/opera_layers/cumilla_open_water.tif"),
                    reason="T3b layers are not in git; this machine does not have them")
def test_flood_history_window_when_the_layers_exist():
    p = pp.field_passport("CUM-ARF-01", half_width=3)
    x = {y["key"]: y for y in p["layers"]}["opera_inundation_days_30m"]
    assert x["status"] == "assessed" and x["pixel_size_m"] == 30
    g = np.array(x["grid"], dtype=object)
    assert g.shape == (7, 7)
    assert all(v is None or v >= 0 for row in x["grid"] for v in row)
    assert "open water" in x["label"].lower()
    assert len(x["status_grid"]) == 7 and len(x["status_grid"][0]) == 7
    for row, srow in zip(x["grid"], x["status_grid"]):
        for v, st in zip(row, srow):
            assert v is not None or st != "ok", "a cell without a value must say why"


def test_each_layer_states_provenance_and_the_text_is_clean(passport):
    for x in passport["layers"]:
        assert x["dataset"] and x["source_url"].startswith("http"), x["key"]
    vz = passport["vulnerability_zones"]
    assert "not a cited vulnerability class" in vz["label"]
    for key in ("cold_prone", "erosion", "water_stress"):
        assert vz["zones"][key]["status"] == "not assessed" and vz["zones"][key]["reason"]
    text = json.dumps(passport).lower()
    assert not re.search(r"predict|forecast", text)
    assert "not nasa data" in passport["field"]["record_note"].lower()
