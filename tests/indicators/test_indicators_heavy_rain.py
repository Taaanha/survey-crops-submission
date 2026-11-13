"""Heavy-rain days from a cited reference row, next to ETCCDI R20mm; counted by hand."""

import numpy as np
import pandas as pd
import pytest

from indicators.build import build_district_table
from indicators.core import r20mm_days
from indicators.heavy_rain import CELL_MEAN_LABEL, heavy_rain_days, load_heavy_rain_threshold

HEADER = "item,value,unit,source_title,source_url,page,year,notes\n"
BMD_ROW = ('bmd_heavy_rain_min,44,mm per 24 h,"News report of the BMD scale",https://example.org/bmd,,,'
           '"BMD heavy rainfall = 44 to 88 mm in 24 h"\n')
STRICT_ROW = ('climate.rain.heavy_day_mm,50,mm per day,"A BMD document",https://example.org/doc,7,2020,"note"\n')


def write_ref(tmp_path, body):
    (tmp_path / "r03_heavy_rain.csv").write_text(HEADER + body, encoding="utf-8")
    return str(tmp_path)


def test_heavy_rain_days_counts_at_or_above_the_limit():
    rain = [43.9, 44.0, 44.1, 88.0, 0.0]
    assert heavy_rain_days(rain, 44.0) == 3   # 44.0, 44.1, 88.0 (44 is the first heavy value)
    assert r20mm_days(rain) == 4              # 43.9 also passes 20 mm: the two limits give different counts


def test_threshold_comes_from_the_cited_row_with_its_source(tmp_path):
    t = load_heavy_rain_threshold(write_ref(tmp_path, BMD_ROW))
    assert t["value"] == 44.0 and t["item"] == "bmd_heavy_rain_min"
    assert t["source_title"] == "News report of the BMD scale"
    assert t["source_url"] == "https://example.org/bmd"
    assert t["page"] == ""                    # the row has no page: shown as missing, not invented
    assert t["via"].startswith("raw row")     # the loader rejects this item name (no dots)


def test_a_properly_named_row_is_preferred_and_read_by_the_strict_loader(tmp_path):
    t = load_heavy_rain_threshold(write_ref(tmp_path, BMD_ROW + STRICT_ROW))
    assert t["value"] == 50.0 and t["item"] == "climate.rain.heavy_day_mm" and t["page"] == "7"
    assert t["via"] == "strict loader"


def test_no_cited_row_means_none(tmp_path):
    assert load_heavy_rain_threshold(write_ref(tmp_path, "")) is None
    no_url = 'bmd_heavy_rain_min,44,mm per 24 h,"A report",not-a-link,,,"n"\n'
    assert load_heavy_rain_threshold(write_ref(tmp_path, no_url)) is None
    assert load_heavy_rain_threshold(str(tmp_path / "missing_dir")) is None


def weather():
    idx = pd.date_range("2006-01-01", "2007-02-28", freq="D")
    w = pd.DataFrame({"rainfall_mm": 0.0, "temp_max_c": 30.0, "temp_min_c": 15.0}, index=idx)
    w.loc["2006-07-11", "rainfall_mm"] = 44.0    # counts (>= 44)
    w.loc["2006-07-21", "rainfall_mm"] = 43.9    # does not count for BMD heavy, does for R20mm
    w.loc["2006-08-05", "rainfall_mm"] = 60.0    # counts
    return w


HEAVY = {"item": "bmd_heavy_rain_min", "value": 44.0, "unit": "mm per 24 h", "source_title": "T",
         "source_url": "https://example.org/bmd", "page": "", "via": "raw row"}


def pick(t, ind, season="kharif2"):
    r = t[(t.indicator == ind) & (t.season == season)]
    assert len(r) == 1
    return r.iloc[0]


def test_build_row_has_label_threshold_and_both_indices_side_by_side():
    w = weather()
    t = build_district_table("testville", w, pd.Series(4.0, index=w.index), None, [], [2006], heavy_rain=HEAVY)
    h, r = pick(t, "heavy_rain_days_bmd"), pick(t, "extreme_rain_days_r20mm")
    assert h.value == 2 and h.threshold == 44.0 and h.status == "ok" and h.unit == "days"
    assert CELL_MEAN_LABEL in h.dataset and "may undercount point extremes" in h.dataset
    assert "bmd_heavy_rain_min" in h.threshold_source and "https://example.org/bmd" in h.threshold_source
    assert r.value == 3 and r.threshold == 20.0     # 44.0, 43.9, 60.0 all reach 20 mm


def test_no_threshold_is_not_assessed_never_zero():
    w = weather()
    t = build_district_table("testville", w, pd.Series(4.0, index=w.index), None, [], [2006], heavy_rain=None)
    h = pick(t, "heavy_rain_days_bmd")
    assert np.isnan(h.value) and h.status.startswith("not assessed") and "heavy-rain" in h.status


def test_incomplete_window_is_nan_not_zero():
    w = weather().drop(pd.Timestamp("2006-08-20"))
    t = build_district_table("testville", w, pd.Series(4.0, index=w.index), None, [], [2006], heavy_rain=HEAVY)
    h = pick(t, "heavy_rain_days_bmd")
    assert np.isnan(h.value) and h.status.startswith("incomplete")
