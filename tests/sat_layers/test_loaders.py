"""Loaders for the W1b layers, on small fixtures with hand-worked expected values."""
import numpy as np
import pandas as pd
import pytest

from sat_layers import loaders as L
from sat_layers.provenance import PROVENANCE, REQUIRED_FIELDS, provenance


def write_modis(path, rows):
    pd.DataFrame(rows, columns=["date", "district", "ndvi", "coverage", "evi", "coverage_evi"]).to_csv(path, index=False)


# ---------- MODIS ----------
def test_modis_year_files_overlap_is_removed_not_chosen(tmp_path):
    # the 2019 file starts with the last composite of 2018 (2018-12-19), exactly as the real files do
    write_modis(tmp_path / "modis_district_2018.csv.gz", [
        ["2018-11-03", "a", 0.5, 1.0, 0.3, 1.0], ["2018-12-19", "a", 0.6, 1.0, 0.4, 1.0], ["2018-12-19", "b", np.nan, 0.0, np.nan, 0.0]])
    write_modis(tmp_path / "modis_district_2019.csv.gz", [
        ["2018-12-19", "a", 0.6, 1.0, 0.4, 1.0], ["2018-12-19", "b", np.nan, 0.0, np.nan, 0.0], ["2019-01-01", "a", 0.7, 1.0, 0.5, 1.0]])
    layer = L.load_modis(str(tmp_path))
    assert len(layer.data) == 4  # 6 raw rows, 2 duplicates
    assert layer.data.duplicated(["date", "district"]).sum() == 0
    b = layer.data[(layer.data.district == "b")].iloc[0]
    assert np.isnan(b.ndvi) and b.coverage == 0.0  # missing stays NaN, never 0
    assert set(layer.provenance) >= set(REQUIRED_FIELDS) | {"coverage_years"}


def test_modis_disagreeing_overlap_raises(tmp_path):
    write_modis(tmp_path / "modis_district_2018.csv.gz", [["2018-12-19", "a", 0.6, 1.0, 0.4, 1.0]])
    write_modis(tmp_path / "modis_district_2019.csv.gz", [["2018-12-19", "a", 0.61, 1.0, 0.4, 1.0]])
    with pytest.raises(ValueError, match="disagree"):
        L.load_modis(str(tmp_path))


def composites(years, n=20, value=lambda y, k: 0.4 + 0.01 * (y - 2001)):
    rows = [[(pd.Timestamp(y, 1, 1) + pd.Timedelta(days=16 * k)).strftime("%Y-%m-%d"), "a", value(y, k), 1.0, 0.3, 1.0]
            for y in years for k in range(n)]
    return pd.DataFrame(rows, columns=["date", "district", "ndvi", "coverage", "evi", "coverage_evi"])


def test_years_present_ignores_the_single_carry_over_composite():
    df = pd.concat([composites([2020]), composites([2019], n=1)])
    assert L.modis_years_present(df) == [2020]


def test_anomaly_by_hand_with_seven_years():
    # ndvi of year y = 0.40 + 0.01*(y-2001). 2001 vs 2002..2007: mean 0.435, sample sd 0.018708
    df = composites(range(2001, 2008))
    table, status = L.ndvi_anomaly(df, "a")
    assert status == "partial (7 years of 24 present)"
    row = table[(table.year == 2001) & (table.doy == 1)].iloc[0]
    assert row.n_other == 6 and row.z == pytest.approx((0.40 - 0.435) / np.sqrt(0.00035), abs=1e-9)
    assert table.z.notna().all()


def test_anomaly_not_assessed_with_fewer_than_six_years():
    table, status = L.ndvi_anomaly(composites(range(2001, 2006)), "a")  # 5 years
    assert status.startswith("not assessed (needs >=5 other years")
    assert table.z.isna().all()  # NaN, not 0


# ---------- HLS ----------
def test_hls_clear_counts_by_hand():
    df = pd.DataFrame({"date": ["d1", "d2", "d3", "d4"], "tile": ["feni"] * 4, "sensor": ["hls_l30"] * 3 + ["hls_s30"],
                       "tile_mean_ndvi": [0.5, np.nan, 0.6, 0.7], "clear_share": [0.5, 0.0, 0.49, 0.9]})
    c = L.hls_clear_counts(df).set_index("sensor")
    assert c.loc["hls_l30"].tolist() == ["feni", 3, 2, 1]  # 3 scenes, 2 with pixels, 1 with clear_share >= 0.5
    assert c.loc["hls_s30", "usable"] == 1


# ---------- ECOSTRESS ----------
def test_ecostress_is_refused_unless_opted_in(tmp_path):
    pd.DataFrame({"date": ["2024-01-01T09:00"], "tile": ["feni"], "product": ["eco_et"], "et_mm_day": [0.1],
                  "clear_share": [1.0]}).to_csv(tmp_path / "ecostress_tile_series.csv", index=False)
    with pytest.raises(L.LayerUnverified) as err:
        L.load_ecostress(str(tmp_path))
    msg = str(err.value)
    assert "units are unresolved" in msg
    assert "ECO_L3T_JET" in msg and "User Guide" in msg and "ATBD" in msg  # what would resolve it
    assert "mm/day" not in msg.replace("look like mm/day", "")  # the message must not pick a unit
    layer = L.load_ecostress(str(tmp_path), allow_unverified=True)
    assert "UNRESOLVED" in layer.provenance["units"] and any("UNRESOLVED" in n for n in layer.notes)


# ---------- NASADEM ----------
def test_nasadem_tile_summary_counts_negative_pixels(tmp_path):
    np.savez(tmp_path / "nasadem_30m_x.npz", elev_m=np.array([[-5, -32768], [0, 3]], dtype="int16"))
    s = L.nasadem_tile_summary("x", str(tmp_path))
    assert (s["n_pixels"], s["min_m"], s["max_m"], s["n_below_0m"]) == (3, -5.0, 3.0, 1)
    assert s["share_below_0m"] == pytest.approx(1 / 3)


def test_nasadem_loader_carries_slope_caveat(tmp_path):
    pd.DataFrame({"district": ["a"], "elev_mean_m": [3.0], "coverage_elev_mean_m": [1.0], "slope_mean_deg": [2.0],
                  "coverage_slope_mean_deg": [1.0]}).to_csv(tmp_path / "nasadem_district_static.csv", index=False)
    layer = L.load_nasadem(str(tmp_path))
    assert any("relative ranking" in n for n in layer.notes)


# ---------- GRACE-FO ----------
def grace_df(regional=True):
    return pd.DataFrame({"date": ["2020-01-01", "2020-01-31", "2020-04-01", "2020-05-01"] * 2,
                         "district": ["a"] * 4 + ["b"] * 4, "lwe_thickness_cm": np.arange(8.0), "cell_lon": [90.25] * 8,
                         "cell_lat": [23.25] * 8, "regional": [regional] * 8, "uncertainty_cm": np.ones(8)})


def test_grace_gaps_and_cells_by_hand():
    df = grace_df()
    assert L.grace_gaps(df) == [("2020-01-31", "2020-04-01", 61)]  # 31->Apr 1 2020 = 61 days; others are 30 days
    assert L.grace_cells(df) == (1, 2)  # one cell shared by two districts


def test_grace_must_be_regional(tmp_path):
    grace_df(regional=False).to_csv(tmp_path / "grace_district_monthly.csv", index=False)
    with pytest.raises(ValueError, match="regional"):
        L.load_grace(str(tmp_path))


# ---------- provenance ----------
def test_every_layer_has_dataset_url_resolution_units():
    for key, p in PROVENANCE.items():
        assert all(p.get(f) for f in REQUIRED_FIELDS), key
        assert p["source_url"].startswith("https://"), key
    assert provenance("modis", "2015")["coverage_years"] == "2015"
    with pytest.raises(KeyError):
        provenance("nope", "x")


def test_provenance_urls_match_the_download_catalogue():
    from w1b.products import PRODUCTS
    for ours, theirs in [("nasadem", "nasadem"), ("grace", "grace"), ("modis", "modis"), ("hls", "hls_l30"), ("smap_live", "smap")]:
        assert PROVENANCE[ours]["source_url"] == PRODUCTS[theirs]["source_url"], ours
