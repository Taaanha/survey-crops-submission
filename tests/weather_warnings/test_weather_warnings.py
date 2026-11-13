"""Weather warnings: normal day, heavy-rain day, unsourced threshold skipped, no warnings is an empty list."""

import csv
import os

import pytest

from weather_warnings import evaluate_days, load_thresholds

HEADER = ["item", "value", "unit", "source_title", "source_url", "page", "year", "notes"]


def write(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for r in rows:
            w.writerow(r)


def row(item, value, url="https://example.org/paper", notes="ok"):
    return [item, value, "x", "A paper", url, "1", "2020", notes]


@pytest.fixture
def refdir(tmp_path):
    write(tmp_path / "r03_heavy_rain.csv", [row("bmd_heavy_rain_min", "44"),
                                            row("bmd_very_heavy_rain_above", "88")])
    write(tmp_path / "crop_thresholds.csv", [row("mustard.heat.flowering_tmax_high", "29"),
                                             row("wheat.heat.anthesis_tmax", "31")])
    write(tmp_path / "r04_cold_injury.csv", [row("mustard.cold.bamis_warning_tmin", "below 10")])
    return str(tmp_path)


def day(date, rain=0.0, tmax=25.0, tmin=15.0):
    return {"date": date, "rain_mm": rain, "tmax_c": tmax, "tmin_c": tmin}


def test_normal_day_gives_an_honest_empty_list(refdir):
    th, _ = load_thresholds(refdir)
    assert evaluate_days([day("2026-11-14", 3.2, 28.0, 18.0)], th) == []


def test_heavy_rain_day_warns_with_the_sourced_threshold(refdir):
    th, _ = load_thresholds(refdir)
    out = evaluate_days([day("2026-11-15", rain=51.0)], th)
    assert len(out) == 1
    w = out[0]
    assert w["type"] == "heavy_rain" and w["date"] == "2026-11-15"
    assert w["expected"] == {"value": 51.0, "unit": "mm/24h"}
    assert w["threshold"]["value"] == 44 and w["threshold"]["source_url"] == "https://example.org/paper"
    assert w["action"]["en"] and w["action"]["bn"]


def test_very_heavy_rain_leads_with_the_higher_level(refdir):
    th, _ = load_thresholds(refdir)
    assert evaluate_days([day("d", rain=95.0)], th)[0]["threshold"]["value"] == 88


def test_hot_day_lists_every_crop_exceeded_and_leads_with_the_highest(refdir):
    th, _ = load_thresholds(refdir)
    w = evaluate_days([day("d", tmax=32.0)], th)[0]
    assert w["type"] == "heat" and w["threshold"]["value"] == 31
    assert [c["crop"] for c in w["crops"]] == ["mustard", "wheat"]
    assert "mustard (flowering), wheat (flowering)" in w["action"]["en"]


def test_cold_night_uses_less_than(refdir):
    th, _ = load_thresholds(refdir)
    assert evaluate_days([day("d", tmin=10.0)], th) == []        # equal to the limit is not below it
    assert evaluate_days([day("d", tmin=9.4)], th)[0]["type"] == "cold"


def test_missing_numbers_are_not_assessed_not_zero(refdir):
    th, _ = load_thresholds(refdir)
    assert evaluate_days([{"date": "d", "rain_mm": None, "tmax_c": None, "tmin_c": None}], th) == []


@pytest.mark.parametrize("value,url,notes,reason", [
    ("35", "https://example.org/x", "TEMPORARY PLACEHOLDER VALUE", "placeholder"),
    ("below 15", "https://example.org/x", "SUSPECT: conflicts with another row", "suspect"),
    ("12", "https://n/a - fabricated", "ok", "http source link"),
    ("10-16 days", "https://example.org/x", "ok", "single number"),
])
def test_unsourced_threshold_is_skipped_and_reported(tmp_path, value, url, notes, reason):
    write(tmp_path / "crop_thresholds.csv", [row("mustard.heat.flowering_tmax_high", value, url, notes)])
    th, skipped = load_thresholds(str(tmp_path))
    assert not [t for t in th if t["item"] == "mustard.heat.flowering_tmax_high"]
    assert any(s["item"] == "mustard.heat.flowering_tmax_high" and reason in s["reason"] for s in skipped)
    # a 40 degree day must NOT warn on a threshold that has no usable source
    assert evaluate_days([day("d", tmax=40.0)], th) == []


def test_missing_reference_file_skips_instead_of_crashing(tmp_path):
    th, skipped = load_thresholds(str(tmp_path))
    assert th == [] and skipped


def test_real_reference_files_give_sourced_thresholds_and_skip_the_placeholders():
    th, skipped = load_thresholds()
    assert {"heavy_rain", "heat", "cold"} <= {t["type"] for t in th}
    assert all(t["source_url"].startswith("http") for t in th)
    skipped_items = {s["item"] for s in skipped}
    assert "aman_rice.cold.flowering_tmin" in skipped_items      # fabricated placeholder
    assert "wheat.cold.bamis_warning_tmin" in skipped_items      # marked SUSPECT
    assert [t["value"] for t in th if t["item"] == "bmd_heavy_rain_min"] == [44.0]
