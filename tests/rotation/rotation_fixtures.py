"""Synthetic fixtures for the rotation tests: a crop table, hand-made crop
specs and a 3-year daily weather table, so every expected number can be
counted by hand without any real data."""

import pandas as pd

from common import Provenance

from rotation import RotationContext

TEST_PROV = Provenance(dataset="synthetic test weather", source_url="https://example.org/test",
                       retrieved="2026-10-24", granule_or_file="tests/rotation/conftest.py")


def crop_row(crop, phase, duration, start, end, variety="v", seedling="", legume=""):
    return {"crop": crop, "variety_class": variety, "phase": phase, "duration_days": duration,
            "sow_start_mmdd": start, "sow_end_mmdd": end, "seedling_age_days": seedling,
            "is_legume": legume, "duration_src": "", "window_src": "", "legume_src": ""}


def temp_spec(crop, start, end, flowering=50, maturity=100, limit=31.0):
    """A crop with fixed (cited-days) stages and one heat hazard at flowering."""
    return {"crop": crop, "window": {"start": start, "end": end, "method": "cited",
                                     "citations": []},
            "base_temp": None, "stage_days": {"flowering": {"value": flowering},
                                              "maturity": {"value": maturity}},
            "hazards": [{"hazard": "heat_flowering", "kind": "temp", "variable": "temp_max_c",
                         "op": ">", "item": "x", "stage": "flowering",
                         "threshold": {"low": limit, "high": limit, "value": limit}}],
            "missing": [], "water_model": "fao56", "stage_method": "cited_days"}


def synthetic_weather(hot_days_by_year):
    """Daily weather 2000-08-01 .. 2006-12-31 (cool and dry). hot_days_by_year:
    {year: [dates]} get temp_max_c = 36."""
    days = pd.date_range("2000-08-01", "2006-12-31", freq="D")
    w = pd.DataFrame({"temp_mean_c": 20.0, "temp_max_c": 25.0, "temp_min_c": 12.0,
                      "rainfall_mm": 0.0}, index=days)
    for dates in hot_days_by_year.values():
        w.loc[pd.to_datetime(dates), "temp_max_c"] = 36.0
    return w


def make_context(crops, specs, weather, turnaround=7):
    return RotationContext(crop_table=pd.DataFrame(crops), specs=specs, weather=weather,
                           water=None, turnaround_days=turnaround, weather_provenance=TEST_PROV)
