"""W5 map layers (Layer 1): the catalogue (disabled layers stay visible with the reason), the
per-district values for a year, and the boundary file with its licence."""

import json
import re

import numpy as np
import pandas as pd
import pytest

from map_layers import layers as L
from map_layers import outlines
from sat_layers.status import NotAssessed, load_status

LIVE = {"cumilla", "feni", "brahmanbaria", "noakhali", "sylhet"}
DATA = "data/processed/"


@pytest.fixture(scope="module")
def cat():
    return {c["key"]: c for c in L.catalog()}


# ---------------- catalogue ----------------

def test_every_status_table_layer_is_in_the_catalogue(cat):
    for key in load_status().key:
        assert key in cat, f"{key} must be listed (never hidden)"


def test_not_assessed_layers_are_disabled_with_their_reason(cat):
    status = load_status().set_index("key")
    for key in ("smap_64", "ecostress_et", "ecostress_lst", "gedi_agbd"):
        c = cat[key]
        assert status.loc[key, "status"] == "not assessed"
        assert c["enabled"] is False and c["status"] == "not assessed"
        assert c["reason"] == status.loc[key, "reason"] and c["reason"]
        assert c["available_years"] == []


def test_enabled_layers_have_a_source_and_a_scope(cat):
    for c in cat.values():
        assert c["dataset"] and c["source_url"].startswith("http"), c["key"]
        assert c["scope"] in ("64 districts", "5 live districts", "demo fields", "none yet")
        assert isinstance(c["caveats"], list)


def test_the_requested_layers_exist_and_carry_their_labels(cat):
    assert cat["nasadem_elevation"]["enabled"] and cat["nasadem_elevation"]["static"] is True
    assert any("relative" in x.lower() for x in cat["nasadem_slope"]["caveats"])
    g = cat["grace_fo"]
    assert any("regional" in x.lower() and "300 km" in x for x in g["caveats"])
    assert any("share" in x.lower() for x in g["caveats"])
    assert cat["modis_ndvi"]["available_years"] == list(range(2015, 2025))
    assert cat["w2:extreme_rain_days_r20mm"]["scope"] == "5 live districts"


def test_timeline_is_greyed_where_a_dataset_has_no_data(cat):
    smap = cat["w2:smap_rootzone_z"]["available_years"]
    assert smap and min(smap) >= 2015 and 2014 not in smap
    assert cat["grace_fo"]["available_years"][0] == 2002 and 2001 not in cat["grace_fo"]["available_years"]
    assert cat["w2:extreme_rain_days_r20mm"]["available_years"] == list(range(2001, 2025))


# ---------------- values ----------------

def test_nasadem_values_match_the_file_for_64_districts():
    out = L.layer_values("nasadem_elevation")
    rows = {r["district"]: r for r in out["rows"]}
    ref = pd.read_csv(DATA + "nasadem_district_static.csv").set_index("district")
    assert len(rows) == 64
    for d in ("cumilla", "bandarban", "bhola"):
        assert rows[d]["value"] == pytest.approx(ref.loc[d, "elev_mean_m"])
    assert out["unit"] == "m"


def test_slope_is_labelled_relative():
    out = L.layer_values("nasadem_slope")
    assert any("relative" in c.lower() for c in out["caveats"])
    assert out["unit"] == "degrees"


def test_grace_year_value_is_the_mean_of_that_years_dates_and_a_gap_year_is_none():
    g = pd.read_csv(DATA + "grace_district_monthly.csv")
    g = g[g.district == "cumilla"]
    year = 2010
    expect = g[g.date.str[:4] == str(year)].lwe_thickness_cm.mean()
    out = L.layer_values("grace_fo", year=year)
    row = {r["district"]: r for r in out["rows"]}["cumilla"]
    assert row["value"] == pytest.approx(expect)
    assert row["n"] == int((g.date.str[:4] == str(year)).sum())
    empty = [y for y in range(2002, 2025) if y not in set(pd.to_datetime(g.date).dt.year)]
    for y in empty:
        out = L.layer_values("grace_fo", year=y)
        assert all(r["value"] is None for r in out["rows"]), "a year with no observations is None, not 0"


def test_modis_only_has_values_in_years_present():
    ok = L.layer_values("modis_ndvi", year=2020)
    assert sum(r["value"] is not None for r in ok["rows"]) > 50
    assert all(-0.2 <= r["value"] <= 1 for r in ok["rows"] if r["value"] is not None)
    assert all(r["value"] is None for r in L.layer_values("modis_ndvi", year=2005)["rows"])


def test_w2_values_equal_the_indicator_table_and_other_districts_are_not_assessed():
    t = pd.read_csv(DATA + "indicators_districts_2001_2024.csv")
    expect = t[(t.indicator == "extreme_rain_days_r20mm") & (t.season_year == 2007)
               & (t.season == "kharif2") & (t.district == "feni")].value.iloc[0]
    out = L.layer_values("w2:extreme_rain_days_r20mm", year=2007, season="kharif2")
    rows = {r["district"]: r for r in out["rows"]}
    assert rows["feni"]["value"] == pytest.approx(expect)
    assert len(rows) == 64
    for d, r in rows.items():
        if d not in LIVE:
            assert r["value"] is None and "not assessed" in r["note"].lower()


def test_every_value_response_carries_dataset_and_source_url():
    for key, kw in [("nasadem_elevation", {}), ("grace_fo", {"year": 2010}), ("modis_ndvi", {"year": 2020}),
                    ("w2:cdd", {"year": 2010, "season": "rabi"})]:
        out = L.layer_values(key, **kw)
        assert out["provenance"]["dataset"] and out["provenance"]["source_url"].startswith("http"), key
        assert out["label"] and out["unit"]


def test_a_disabled_or_unknown_layer_raises():
    with pytest.raises(NotAssessed):
        L.layer_values("ecostress_et")
    with pytest.raises(NotAssessed):
        L.layer_values("smap_64")
    with pytest.raises(KeyError):
        L.layer_values("no_such_layer")


def test_year_outside_a_layers_range_gives_no_values_not_zero():
    out = L.layer_values("w2:smap_rootzone_z", year=2005, season="rabi")
    assert all(r["value"] is None for r in out["rows"])
    assert out["status_note"]


def test_no_predict_or_forecast_in_map_text(cat):
    text = json.dumps(cat).lower()
    assert not re.search(r"predict|forecast", text)


# ---------------- boundaries ----------------

def test_outlines_are_64_with_licence_and_source():
    out = outlines.district_outlines()
    assert len(out["features"]) == 64
    live = {f["properties"]["slug"] for f in out["features"] if f["properties"]["live"]}
    assert live == LIVE
    p = out["provenance"]
    assert p["licence"].startswith("Creative Commons Attribution 3.0") or "CC BY 3.0 IGO" in p["licence"]
    assert p["source_url"].startswith("https://www.geoboundaries.org/")
    assert "simplified" in p["note"].lower()
    assert "Runfola" in p["citation"]
