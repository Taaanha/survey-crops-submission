"""Checks on the committed data/processed/soilgrids_ph_oc_points.csv (hand-checked facts)."""

import os

import pandas as pd
import pytest

import soil_chem as sc

pytestmark = pytest.mark.skipif(not os.path.exists(sc.CSV_PATH), reason="file not fetched")
POINTS = {"cumilla", "noakhali", "feni", "brahmanbaria", "sylhet",
          "demo_field_feni", "demo_field_cumilla"}


@pytest.fixture(scope="module")
def df():
    return pd.read_csv(sc.CSV_PATH, keep_default_na=False)


def test_seven_points_each_with_24_rows(df):
    assert set(df.point_id) == POINTS
    assert (df.groupby("point_id").size() == 24).all()


def test_every_row_has_dataset_url_resolution_date(df):
    for col in ("dataset", "source_url", "resolution", "fetch_date", "units"):
        assert (df[col] != "").all(), col
    assert set(df.resolution) == {"250 m"}


def test_gap_rows_have_reason_and_no_value_assessed_rows_have_value(df):
    gap, ok = df[df.status == "gap"], df[df.status == "assessed"]
    assert (gap.value == "").all() and (gap.reason != "").all()
    assert (ok.value != "").all() and (ok.reason == "").all()


def test_conversion_matches_the_stored_d_factor_and_is_physical(df):
    ok = df[df.status == "assessed"].copy()
    ok["v"], ok["raw"], ok["f"] = ok.value.astype(float), ok.raw_value.astype(float), ok.d_factor.astype(float)
    assert ((ok.raw / ok.f - ok.v).abs() < 1e-3).all()
    assert set(ok[ok.property == "phh2o"].f) == {10.0}
    ph = ok[ok.property == "phh2o"].v
    assert ph.between(3.0, 10.0).all()          # a raw x10 value left unconverted would be 30-100
    soc = ok[ok.property == "soc"].v
    assert soc.between(0.5, 600).all()


def test_quantiles_are_ordered_where_present(df):
    ok = df[df.status == "assessed"].copy()
    ok["v"] = ok.value.astype(float)
    wide = ok.pivot_table(index=["point_id", "property", "depth"], columns="statistic", values="v")
    assert (wide["Q0.05"] <= wide["Q0.5"]).all() and (wide["Q0.5"] <= wide["Q0.95"]).all()


def test_soil_baseline_reads_it_back():
    b = sc.soil_baseline("brahmanbaria")
    assert b["status"] == "assessed" and b["label"] == sc.LABEL
    assert sc.soil_baseline("feni")["status"] == "gap"
