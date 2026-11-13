"""W5 follow-up: relative vulnerability zones for the passport fields (Layer 1).

Every function is tested on a hand-built 4x4 grid whose answer is worked out by hand in the comment.
Missing is NaN inside and None in the output, never 0. Zones are labelled as relative rankings."""

import json
import os
import re

import numpy as np
import pytest

from map_layers import passport as pp
from map_layers import zones as Z

nan = np.nan
LAYERS_PRESENT = os.path.exists(os.path.join(pp.LAYERS_DIR, "layers_manifest_cumilla.json"))


# ------------------------------------------------------------------ low-lying (NASADEM)

ELEV = np.array([[1, 2, 3, 4],
                 [5, 6, 7, 8],
                 [9, 10, 11, 12],
                 [13, 14, 15, nan]], dtype=float)


def test_lowest_third_cut_on_a_hand_built_tile():
    # 15 finite values 1..15; the 33.33rd percentile (linear) is at position 14/3 = 4.667 -> 5.667,
    # so the values 1..5 are in the lowest third: 5 of 15 pixels
    c = Z.lowest_third_cut(ELEV)
    assert c["cut_m"] == pytest.approx(1 + 14 / 3)
    assert c["n_pixels"] == 15 and c["n_flagged"] == 5 and c["share_of_tile"] == pytest.approx(5 / 15)


def test_ties_are_reported_not_hidden():
    # 8 pixels at 1 m, 4 at 2 m, 4 at 3 m: the 33.33rd percentile is 1 m, and "<= 1" takes 8 of 16
    tile = np.array([[1] * 4, [1] * 4, [2] * 4, [3] * 4], dtype=float)
    c = Z.lowest_third_cut(tile)
    assert c["cut_m"] == 1.0 and c["share_of_tile"] == 0.5     # more than a third, and the share says so


def test_flat_tile_has_no_lowest_third():
    assert Z.lowest_third_cut(np.full((4, 4), 7.0)) is None
    assert Z.lowest_third_cut(np.full((4, 4), nan)) is None


def test_low_lying_flags_pixels_at_or_below_the_cut_and_keeps_missing_missing():
    low = Z.low_lying(ELEV, 5.667)
    want = np.array([[1, 1, 1, 1],
                     [1, 0, 0, 0],
                     [0, 0, 0, 0],
                     [0, 0, 0, nan]])
    np.testing.assert_array_equal(low, want)           # NaN == NaN is True here; 0 never replaces nan


def test_the_cut_comes_from_the_tile_not_from_the_window():
    # the window is the top-right 2x2 (values 3, 4, 7, 8): relative to the TILE none is in the lowest
    # third except the 3 (and 4); a window-only cut would wrongly flag two of the four
    c = Z.lowest_third_cut(ELEV)
    win = Z.low_lying(ELEV[0:2, 2:4], c["cut_m"])
    np.testing.assert_array_equal(win, [[1, 1], [0, 0]])
    own = Z.lowest_third_cut(ELEV[0:2, 2:4])
    assert own["cut_m"] != c["cut_m"]


# ------------------------------------------------------------------ flood history (T3b)

NE, OK, TFO, NOO, WET, DNC = ("no event", "ok", "too few observations", "no observations",
                              "still wet at series end", "drain not confirmed")
DAYS = np.array([[-1, -1, 3, 5],
                 [-1, -1, -1, 10],
                 [7, -1, -1, -1],
                 [-1, -1, 2, -1]], dtype=float)
STATUS = np.array([[NE, NE, OK, OK],
                   [NE, NE, NE, OK],
                   [OK, TFO, NE, NE],
                   [NE, NE, OK, NOO]], dtype=object)


def test_flood_days_zero_only_where_observed_dry_and_nan_where_unknown():
    d = Z.flood_days(DAYS, STATUS)
    want = np.array([[0, 0, 3, 5],
                     [0, 0, 0, 10],
                     [7, nan, 0, 0],
                     [0, 0, 2, nan]])
    np.testing.assert_array_equal(d, want)             # 'too few' and 'no observations' stay NaN


def test_flood_days_keeps_unconfirmed_drain_days_and_drops_a_missing_value():
    st = np.array([[WET, DNC], [OK, OK]], dtype=object)
    d = Z.flood_days(np.array([[30, 12], [-1, 4]], dtype=float), st)
    np.testing.assert_array_equal(d, [[30, 12], [nan, 4]])     # status ok but value -1: unknown


def test_flood_cut_is_the_upper_third_of_observed_pixels():
    # 14 observed pixels: nine 0 and 2, 3, 5, 7, 10. 66.67th percentile at position 13*2/3 = 8.667
    # -> between 0 (index 8) and 2 (index 9) = 1.333
    c = Z.flood_cut(Z.flood_days(DAYS, STATUS))
    assert c["cut_days"] == pytest.approx(4 / 3) and c["n_observed"] == 14
    assert c["n_flagged"] == 5 and c["share_of_observed"] == pytest.approx(5 / 14)


def test_flood_exposed_needs_at_least_one_day_when_most_of_the_tile_is_dry():
    # 12 dry pixels and 1, 1, 4, 6: the 66.67th percentile is 0, so "at or above the cut" would flag
    # every dry pixel; the rule also needs more than 0 days, so only the four wet pixels are exposed
    g = np.array([[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [1, 1, 4, 6]], dtype=float)
    c = Z.flood_cut(g)
    assert c["cut_days"] == 0.0 and c["n_flagged"] == 4
    ex = Z.flood_exposed(g, c["cut_days"])
    np.testing.assert_array_equal(ex, [[0] * 4, [0] * 4, [0] * 4, [1, 1, 1, 1]])


def test_flood_exposed_keeps_unknown_pixels_unknown():
    d = Z.flood_days(DAYS, STATUS)
    ex = Z.flood_exposed(d, Z.flood_cut(d)["cut_days"])
    want = np.array([[0, 0, 1, 1],
                     [0, 0, 0, 1],
                     [1, nan, 0, 0],
                     [0, 0, 1, nan]])
    np.testing.assert_array_equal(ex, want)


def test_no_observed_pixels_means_no_flood_cut():
    assert Z.flood_cut(np.full((4, 4), nan)) is None


# ------------------------------------------------------------------ overlap and resampling

def test_overlap_is_a_three_valued_and():
    a = np.array([1, 1, 1, 0, 0, nan, nan, 1], dtype=float)
    b = np.array([1, 0, nan, 1, nan, 0, nan, 1], dtype=float)
    # both flagged -> 1; one known-not -> 0 (known even if the other is unknown); a flagged pixel
    # with an unknown partner -> unknown; both unknown -> unknown
    np.testing.assert_array_equal(Z.overlap(a, b), [1, 0, nan, 0, 0, 0, nan, 1])


def test_overlap_of_4x4_zones():
    low = Z.low_lying(ELEV, 5.667)
    d = Z.flood_days(DAYS, STATUS)
    ex = Z.flood_exposed(d, Z.flood_cut(d)["cut_days"])
    ov = Z.overlap(low, ex)
    want = np.array([[0, 0, 1, 1],        # low row 0 = 1 1 1 1 and flood 0 0 1 1
                     [0, 0, 0, 0],
                     [0, 0, 0, 0],
                     [0, 0, 0, nan]])
    np.testing.assert_array_equal(ov, want)


def test_overlap_shapes_must_match():
    with pytest.raises(ValueError):
        Z.overlap(np.zeros((4, 4)), np.zeros((3, 4)))


def test_sample_nearest_reads_other_grid_pixels_and_nan_outside():
    g = np.arange(16, dtype=float).reshape(4, 4)
    rows = np.array([[0, 3], [3, 4]])
    cols = np.array([[0, 3], [-1, 0]])
    np.testing.assert_array_equal(Z.sample_nearest(g, rows, cols), [[0, 15], [nan, nan]])


def test_summary_counts_flagged_known_and_unknown():
    s = Z.summary(np.array([[1, 0], [nan, 1]]))
    assert s == {"n_flagged": 2, "n_known": 3, "n_unknown": 1, "share_of_known": pytest.approx(2 / 3)}
    assert Z.summary(np.full((2, 2), nan))["share_of_known"] is None


def test_to_lists_turns_nan_into_none_and_flags_into_ints():
    assert Z.to_lists(np.array([[1.0, 0.0], [nan, 1.0]])) == [[1, 0], [None, 1]]


# ------------------------------------------------------------------ the passport block

def fake_tile(tmp_path, high_window=False):
    """20 x 20 tile around (23.45, 91.15); elevations 0..399 rising to the east. Row 0 is north."""
    lats, lons = np.linspace(23.46, 23.44, 20), np.linspace(91.14, 91.16, 20)
    e = (np.arange(400).reshape(20, 20) % 20 * 20 + np.arange(20)[:, None]).astype(np.int16)
    e[2, 2] = -32768
    np.savez(tmp_path / "nasadem_30m_t.npz", elev_m=e, lats=lats, lons=lons)
    return lats, lons


def test_block_without_flood_layers_says_not_in_the_repo_and_keeps_the_rest(tmp_path):
    fake_tile(tmp_path)
    field = {"id": "T", "lat": 23.45, "lon": 91.15, "district": "t", "tile": "t"}
    zb = Z.zones_block(field, 2, data_dir=str(tmp_path), layers_dir=str(tmp_path / "none"))
    assert zb["label"] == Z.LABEL
    assert "relative ranking within this tile" in zb["label"] and "not a cited vulnerability class" in zb["label"]
    low = zb["zones"]["low_lying"]
    assert low["status"] == "assessed" and np.array(low["grid"], dtype=object).shape == (5, 5)
    flood = zb["zones"]["flood_exposed"]
    assert flood["status"] == "not assessed" and flood["grid"] is None
    assert flood["reason"] == "not assessed (layer not in the repo)"
    ov = zb["zones"]["low_and_flood_exposed"]
    assert ov["status"] == "not assessed" and ov["grid"] is None and "flood" in ov["reason"]


def test_window_flag_uses_the_cut_of_the_whole_tile(tmp_path):
    lats, lons = fake_tile(tmp_path)
    field = {"id": "T", "lat": 23.45, "lon": 91.15, "district": "t", "tile": "t"}
    zb = Z.zones_block(field, 1, data_dir=str(tmp_path), layers_dir=str(tmp_path / "none"))
    low = zb["zones"]["low_lying"]
    e = np.load(tmp_path / "nasadem_30m_t.npz")["elev_m"].astype(float)
    e[e == -32768] = nan
    row, col = int(np.argmin(abs(lats - 23.45))), int(np.argmin(abs(lons - 91.15)))
    # lats run north -> south here, so row 0 is already the northern edge
    direct = Z.to_lists(Z.low_lying(e[row - 1:row + 2, col - 1:col + 2], Z.lowest_third_cut(e)["cut_m"]))
    assert low["grid"] == direct
    assert low["cut_m"] == pytest.approx(Z.lowest_third_cut(e)["cut_m"])
    assert low["tile_pixels"] == 399                                  # one nodata pixel is not counted


def test_a_missing_elevation_pixel_is_none_not_zero_in_the_block(tmp_path):
    lats, lons = fake_tile(tmp_path)
    field = {"id": "T", "lat": float(lats[2]), "lon": float(lons[2]), "district": "t", "tile": "t"}  # pixel (2, 2)
    zb = Z.zones_block(field, 1, data_dir=str(tmp_path), layers_dir=str(tmp_path / "none"))
    flat = [v for row in zb["zones"]["low_lying"]["grid"] for v in row]
    assert None in flat and all(v in (0, 1, None) for v in flat)


def test_unassessed_zones_keep_their_reasons_and_provenance(tmp_path):
    fake_tile(tmp_path)
    field = {"id": "T", "lat": 23.45, "lon": 91.15, "district": "t", "tile": "t"}
    zb = Z.zones_block(field, 1, data_dir=str(tmp_path), layers_dir=str(tmp_path / "none"))
    for key in ("cold_prone", "erosion", "water_stress"):
        z = zb["zones"][key]
        assert z["status"] == "not assessed" and len(z["reason"]) > 40
        assert z["grid"] is None and not re.search(r"\b0\b", json.dumps(z.get("value", "")))
    for key, z in zb["zones"].items():
        assert z["dataset"] and z["source_url"].startswith("http"), key
        assert z["label"] == Z.LABEL, key


def test_no_prediction_words_anywhere(tmp_path):
    fake_tile(tmp_path)
    field = {"id": "T", "lat": 23.45, "lon": 91.15, "district": "t", "tile": "t"}
    text = json.dumps(Z.zones_block(field, 1, data_dir=str(tmp_path), layers_dir=str(tmp_path / "none")))
    assert not re.search(r"predict|forecast", text, re.I)


def test_field_outside_the_tile_is_a_clear_error(tmp_path):
    fake_tile(tmp_path)
    field = {"id": "T", "lat": 25.0, "lon": 91.15, "district": "t", "tile": "t"}
    with pytest.raises(ValueError):
        Z.zones_block(field, 1, data_dir=str(tmp_path), layers_dir=str(tmp_path / "none"))


# ------------------------------------------------------------------ the real passport

@pytest.fixture(scope="module")
def real():
    return pp.field_passport("CUM-ARF-01", half_width=7)


def test_passport_carries_the_zones_instead_of_the_old_not_assessed_stub(real):
    vz = real["vulnerability_zones"]
    assert vz["label"] == Z.LABEL and set(vz["zones"]) == {
        "low_lying", "flood_exposed", "low_and_flood_exposed", "cold_prone", "erosion", "water_stress"}
    low = vz["zones"]["low_lying"]
    assert low["status"] == "assessed" and low["tile"] == "cumilla"
    assert np.array(low["grid"], dtype=object).shape == (15, 15)
    assert 0.3 <= low["share_of_tile"] <= 0.45        # a third, plus the ties of whole-metre elevations
    assert low["source_url"].startswith("https://appeears")


@pytest.mark.skipif(LAYERS_PRESENT, reason="only meaningful where the T3b layers are absent")
def test_without_opera_layers_flood_and_overlap_are_not_assessed(real):
    z = real["vulnerability_zones"]["zones"]
    assert z["flood_exposed"]["reason"] == "not assessed (layer not in the repo)"
    assert z["low_and_flood_exposed"]["status"] == "not assessed"


@pytest.mark.skipif(not LAYERS_PRESENT, reason="needs data/raw/opera_layers (not in git)")
def test_with_opera_layers_flood_and_overlap_are_on_their_own_grids(real):
    z = real["vulnerability_zones"]["zones"]
    f, ov = z["flood_exposed"], z["low_and_flood_exposed"]
    assert f["status"] == "assessed" and f["pixel_size_m"] == 30
    assert np.array(f["grid"], dtype=object).shape == (15, 15)
    assert np.array(ov["grid"], dtype=object).shape == (15, 15)
    assert ov["status"] == "assessed" and "nearest" in " ".join(ov["caveats"]).lower()
    assert all(v in (0, 1, None) for row in f["grid"] for v in row)
    assert f["cut_days"] >= 0 and "upper bound" in " ".join(f["caveats"]).lower()
