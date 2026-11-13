"""W5 scenario sliders (Layer 1): rain -30..+30 %, temperature +0..2 C, the FAO-56 balance and the
heat counts re-run on the changed past seasons. The slider at (0, 0) must equal the plain Layer 1
numbers; the what-if label is fixed; ranges are enforced."""

import json
import re

import numpy as np
import pandas as pd
import pytest

from map_layers import scenario as sc
import risk_calendar as rc
from water_balance import crop_season_all_years, load_crop_params, load_soil_params


def raw_frame(days=4):
    idx = pd.date_range("2001-01-01", periods=days, freq="D")
    return pd.DataFrame({"rainfall_mm": [0.0, 10.0, 20.0, 50.0][:days],
                         "temp_mean_c": [20.0] * days, "temp_max_c": [30.0, 34.0, 36.0, 40.0][:days],
                         "temp_min_c": [10.0] * days, "rh_pct": [70.0] * days,
                         "wind_speed_ms": [2.0] * days, "solar_rad_mj_m2": [15.0] * days}, index=idx)


# ---------------- the weather change ----------------

def test_rain_is_scaled_exactly_and_temperature_shifted_exactly():
    out = sc.apply_scenario(raw_frame(), rain_pct=30, temp_add_c=2)
    assert out["rainfall_mm"].tolist() == pytest.approx([0.0, 13.0, 26.0, 65.0])
    assert out["temp_max_c"].tolist() == pytest.approx([32.0, 36.0, 38.0, 42.0])
    assert out["temp_min_c"].tolist() == pytest.approx([12.0] * 4)
    assert out["temp_mean_c"].tolist() == pytest.approx([22.0] * 4)


def test_other_columns_and_the_input_are_untouched():
    raw = raw_frame()
    before = raw.copy()
    out = sc.apply_scenario(raw, rain_pct=-30, temp_add_c=1)
    pd.testing.assert_frame_equal(raw, before)
    for col in ("rh_pct", "wind_speed_ms", "solar_rad_mj_m2"):
        assert out[col].tolist() == raw[col].tolist()
    assert out["rainfall_mm"].tolist() == pytest.approx([0.0, 7.0, 14.0, 35.0])


@pytest.mark.parametrize("rain,temp", [(-31, 0), (31, 0), (0, -0.1), (0, 2.1), (float("nan"), 0), ("a", 0)])
def test_out_of_range_sliders_are_rejected(rain, temp):
    with pytest.raises(ValueError):
        sc.apply_scenario(raw_frame(), rain, temp)


def test_ends_of_the_ranges_are_allowed():
    sc.apply_scenario(raw_frame(), -30, 0)
    sc.apply_scenario(raw_frame(), 30, 2)


# ---------------- heat counts (hand-counted) ----------------

def test_heat_counts_by_hand():
    season = pd.DataFrame({"temp_max_c": [30.0, 35.4, 35.5, 40.0], "temp_min_c": [28.0, 29.0, 20.0, 31.0]})
    limits = [{"item": "wheat.heat.anthesis_tmax", "kind": "heat_days", "variable": "tmax", "op": ">",
               "value": 35.4, "unit": "C", "stage": "anthesis", "source_url": "u", "source_title": "t"},
              {"item": "potato.heat.tuber_tmin_night_high", "kind": "night_heat_days", "variable": "tmin",
               "op": ">", "value": 28.0, "unit": "C", "stage": "tuber", "source_url": "u", "source_title": "t"}]
    got = sc.heat_days_in_season(season, limits)
    assert got == {"wheat.heat.anthesis_tmax": 2, "potato.heat.tuber_tmin_night_high": 2}  # strict ">": 28.0 is not above 28.0


# ---------------- the slider equals Layer 1 ----------------

@pytest.fixture(scope="module")
def base():
    return sc.run_scenario("cumilla", "wheat", rain_pct=0, temp_add_c=0)


def test_zero_slider_equals_the_plain_layer1_balance(base):
    w = rc.prepare_weather("cumilla")
    kc = pd.read_csv("data/processed/kc_table.csv")
    direct = crop_season_all_years("wheat", base["inputs"]["sowing_mmdd"], w, kc, load_crop_params(),
                                   load_soil_params()["cumilla"], years=range(2001, 2025))
    s = base["scenario"]
    assert s["n_years"] == len(direct) == 24
    assert s["irrigation_mm_mean"] == pytest.approx(direct["net_irrigation_mm"].mean(), abs=0.06)
    assert s["water_stress_days_mean"] == pytest.approx(direct["water_stress_days"].mean(), abs=0.06)
    assert s["rain_mm_mean"] == pytest.approx(direct["rain_mm"].mean(), abs=0.06)
    assert base["delta"]["irrigation_mm_mean"] == 0
    assert base["scenario"] == base["baseline"]


def test_more_rain_needs_less_irrigation_and_warmer_needs_more(base):
    wet = sc.run_scenario("cumilla", "wheat", rain_pct=30, temp_add_c=0)["scenario"]
    dry = sc.run_scenario("cumilla", "wheat", rain_pct=-30, temp_add_c=0)["scenario"]
    warm = sc.run_scenario("cumilla", "wheat", rain_pct=0, temp_add_c=2)["scenario"]
    b = base["baseline"]
    assert wet["irrigation_mm_mean"] <= b["irrigation_mm_mean"] <= dry["irrigation_mm_mean"]
    assert warm["irrigation_mm_mean"] >= b["irrigation_mm_mean"]
    assert wet["rain_mm_mean"] == pytest.approx(1.3 * b["rain_mm_mean"], rel=0.01)


def test_heat_days_never_fall_with_warming(base):
    warm = sc.run_scenario("cumilla", "wheat", rain_pct=0, temp_add_c=2)
    assert warm["scenario"]["heat"], "wheat has cited heat limits"
    for hot, cool in zip(warm["scenario"]["heat"], warm["baseline"]["heat"]):
        assert hot["item"] == cool["item"]
        assert hot["mean_days"] >= cool["mean_days"]
        assert hot["source_url"].startswith("http")


def test_baseline_is_the_same_whatever_the_slider(base):
    other = sc.run_scenario("cumilla", "wheat", rain_pct=-30, temp_add_c=2)
    assert other["baseline"] == base["baseline"]
    assert other["delta"]["irrigation_mm_mean"] == pytest.approx(
        other["scenario"]["irrigation_mm_mean"] - base["baseline"]["irrigation_mm_mean"], abs=0.11)


def test_label_provenance_and_wording(base):
    assert base["label"] == "what-if on past seasons, not a forecast"
    assert base["provenance"] and all(p["dataset"] and p["source_url"].startswith("http")
                                      for p in base["provenance"])
    text = json.dumps({k: v for k, v in base.items() if k != "label"}).lower()
    assert not re.search(r"predict|forecast", text)
    assert any("relative humidity" in a.lower() or "humidity" in a.lower() for a in base["assumptions"])


def test_unknown_crop_district_and_missing_window_are_errors():
    with pytest.raises(ValueError):
        sc.run_scenario("cumilla", "banana", 0, 0)
    with pytest.raises(ValueError):
        sc.run_scenario("not_a_district", "wheat", 0, 0)
    with pytest.raises(ValueError):
        sc.run_scenario("cumilla", "wheat", 0, 0, sowing="13-40")
