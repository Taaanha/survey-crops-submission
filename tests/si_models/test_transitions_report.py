"""Problem 1 (NDVI transitions) and the report helpers, on hand-worked fixtures."""

import numpy as np
import pandas as pd
import pytest

from si_models import report, transitions as tr


def test_threshold_crossings_interpolates_and_skips_nan():
    dates = pd.date_range("2020-01-01", periods=5, freq="16D")
    out = tr.threshold_crossings(dates, [0.2, 0.6, np.nan, 0.6, 0.2], 0.4)
    assert [w for _, w in out] == ["up", "down"]
    assert out[0][0] == pd.Timestamp("2020-01-09")          # halfway between 1 Jan and 17 Jan
    # the down crossing lies between the 4th and 5th composite, halfway
    assert out[1][0] == dates[3] + pd.Timedelta(days=8)
    assert tr.threshold_crossings(dates, [0.5, 0.6, 0.7, 0.6, 0.5], 0.1) == []   # never reaches 0.1


def test_smooth_keeps_a_straight_line_and_counts_filled():
    line = np.linspace(0.2, 0.8, 9)
    sm, n = tr.smooth(line)
    assert n == 0 and np.allclose(sm, line)                 # order-2 filter reproduces a line exactly
    gap = line.copy()
    gap[4] = np.nan
    sm, n = tr.smooth(gap)
    assert n == 1 and np.allclose(sm, line)
    short, n = tr.smooth([0.1, np.nan, 0.3])
    assert n == 1 and np.allclose(short, [0.1, 0.2, 0.3])   # too short to filter: only filled


def test_change_point_date_is_the_midpoint_of_the_step():
    dates = pd.date_range("2020-01-01", periods=8, freq="16D")
    step = [0.3, 0.3, 0.3, 0.3, 0.7, 0.7, 0.7, 0.7]
    date, p = tr.change_point_date(dates, step, "up")
    assert date == dates[3] + pd.Timedelta(days=8) and 0 < p <= 1
    assert tr.change_point_date(dates, step, "down")[0] is None      # level rises, so no browning date
    assert tr.change_point_date(dates[:3], step[:3], "up")[0] is None  # fewer than 4 composites


def test_days_outside_hand_worked():
    s, e = pd.Timestamp("2020-01-10"), pd.Timestamp("2020-01-30")
    assert tr.days_outside(pd.Timestamp("2020-01-20"), s, e) == 0
    assert tr.days_outside(pd.Timestamp("2020-02-10"), s, e) == 11
    assert tr.days_outside(pd.Timestamp("2020-01-05"), s, e) == -5


def test_window_dates_cross_the_year_end():
    start, end = tr.window_dates(((12, 5, -1), (1, 30, 0)), 2020)
    assert (start, end) == (pd.Timestamp("2019-12-05"), pd.Timestamp("2020-01-30"))


@pytest.mark.parametrize("url,ok", [
    ("https://apps.barc.gov.bd/cropcalendar/index.php", True),
    ("https://journal.safebd.org/index.php/jafe/article/download/3", True),
    ("https://adhunikDhanerChash.pdf (BRRI official handbook)", False),
    ("https://brridhan28.pdf / brridhan29.pdf", False),
    ("https://n/a - fabricated for prototype", False),
    ("", False),
])
def test_is_public_url(url, ok):
    assert tr.is_public_url(url) is ok


def _kept(rows):
    cols = ["item", "month", "day", "low", "high", "source_url"]
    return pd.DataFrame(rows, columns=cols)


def test_reference_windows_hand_worked():
    u = "https://example.org/calendar"
    kept = _kept([
        ("boro_rice.sow.seedbed_start", 10, 31, np.nan, np.nan, u), ("boro_rice.sow.seedbed_start", 11, 15, np.nan, np.nan, u),
        ("boro_rice.sow.window_end", 1, 30, np.nan, np.nan, u), ("boro_rice.stage.seedling_age", np.nan, np.nan, 35, 45, u),
        ("aman_rice.sow.window_start", 6, 15, np.nan, np.nan, u), ("aman_rice.sow.window_end", 7, 30, np.nan, np.nan, u),
        ("aman_rice.stage.seedling_age", np.nan, np.nan, 25, 30, u),
        ("boro_rice.sow.seedbed_start", 10, 1, np.nan, np.nan, "https://brridhan28.pdf"),   # placeholder: ignored
    ])
    w = tr.reference_windows(kept)
    assert w["boro_greenup"]["start"] == (12, 5, -1) and w["boro_greenup"]["end"] == (1, 30, 0)   # 31 Oct + 35 d
    assert w["aman_greenup"]["start"] == (7, 10, 0) and w["aman_greenup"]["end"] == (8, 29, 0)    # 15 Jun + 25 d, 30 Jul + 30 d
    assert all("example.org" in s for s in w["boro_greenup"]["sources"])
    assert w["boro_browning"]["status"] == "not assessed" and w["aman_browning"]["status"] == "not assessed"


def test_reference_windows_without_cited_rows_are_not_assessed():
    w = tr.reference_windows(_kept([("boro_rice.sow.seedbed_start", 11, 15, np.nan, np.nan, "https://brridhan28.pdf")]))
    assert w["boro_greenup"]["status"] == "not assessed" and w["aman_greenup"]["status"] == "not assessed"


def _modis():
    dates = pd.date_range("2019-12-03", periods=23, freq="16D")       # to Nov 2020
    ndvi = np.where((dates >= "2020-02-01") & (dates <= "2020-04-20"), 0.7, 0.4).astype(float)
    return pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "district": "a", "ndvi": ndvi})


def test_detect_and_errors_on_a_step_series():
    w = {"boro_greenup": {"start": (12, 5, -1), "end": (1, 30, 0)},
         "boro_browning": {"status": "not assessed", "reason": "x"}}
    d = tr.add_errors(tr.detect(_modis(), "a", [2020], threshold=0.1), w).set_index("transition")
    assert d.date_a.isna().all()                                       # NDVI never reaches 0.1: no Method A date
    g = d.loc["boro_greenup"]
    assert pd.Timestamp("2020-01-20") <= g.date_b <= pd.Timestamp("2020-02-21")   # rise is at the start of Feb
    assert g.err_b == tr.days_outside(g.date_b, pd.Timestamp("2019-12-05"), pd.Timestamp("2020-01-30"))
    assert np.isnan(g.err_a) and np.isnan(d.loc["boro_browning", "err_b"])        # no window: NaN, never 0
    assert d.loc["boro_browning", "date_b"] is not None


def test_load_events_uses_only_cited_rows(tmp_path):
    p = tmp_path / "events.csv"
    p.write_text(
        "item,value,unit,source_title,source_url,page,year,notes\n"
        "event.flood.cumilla,2024,kharif2 season year,A report,https://example.org/r,,2024,read\n"
        "event.flood.feni,GAP,kharif2 season year,,,,,not read\n"
        "event.cold.sylhet,2018,rabi season year,,,,,no source\n"
        "event.flood.noakhali,2024,winter season year,A report,https://example.org/r,,2024,bad season\n",
        encoding="utf-8")
    used, unused = report.load_events(str(p))
    assert used.to_dict("records") == [{"district": "cumilla", "season_year": 2024, "season": "kharif2", "event": "flood",
                                        "source_title": "A report", "source_url": "https://example.org/r"}]
    assert [u["item"] for u in unused] == ["event.flood.feni", "event.cold.sylhet", "event.flood.noakhali"]


def test_real_events_file_every_used_event_has_a_source():
    used, unused = report.load_events()
    assert len(used) >= 1 and used.source_url.str.startswith("http").all() and (used.source_title != "").all()
    assert all(u["reason"] for u in unused)


def test_load_ndvi_threshold(tmp_path):
    p = tmp_path / "ndvi.csv"
    p.write_text("item,value,unit,source_title,source_url,page,year,notes\n"
                 "ndvi_bare_soil_upper_limit_nasa,0.1,NDVI,T,https://example.org,,2000,n\n"
                 "bangladesh_bare_field_ndvi_threshold,GAP,NDVI,,,,,gap\n", encoding="utf-8")
    assert report.load_ndvi_threshold(str(p))["value"] == 0.1
    assert report.load_ndvi_threshold(str(p), "bangladesh_bare_field_ndvi_threshold") is None   # GAP is not a number
    assert report.load_ndvi_threshold(str(p), "missing_item") is None


def test_fmt_and_model_card_wording():
    assert report.fmt({"value": 0.5, "lo": 0.25, "hi": 0.75, "n": 8}) == "0.50 (95% interval 0.25 to 0.75, n = 8)"
    assert report.fmt({"value": float("nan"), "lo": float("nan"), "hi": float("nan"), "n": 0}) == "not assessed (n = 0)"
    assert "no interval, n = 1" in report.fmt({"value": 1.0, "lo": float("nan"), "hi": float("nan"), "n": 1})
    card = report.model_card("m", "p", "method", [("D", "https://example.org")], "n = 3", [("hit rate", "x")],
                             ["a limit"], "no: reason", 1)
    assert "needs local validation" in card.lower() and "https://example.org" in card and "seed 1" in card
    low = card.lower()
    assert "predict" not in low and "forecast" not in low
