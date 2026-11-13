"""Regridding onto the 0.1 degree grid: every expected number is worked out by hand."""
import numpy as np
import pytest

from district_grid.regrid import (M_PER_DEG, bin_mean_scattered, bin_mean_to_grid, nearest_cell,
                                  slope_degrees)

GL = np.array([0.05, 0.15])  # two 0.1 degree cells in each direction
GA = np.array([10.05, 10.15])


def test_bin_mean_is_mean_of_pixels_inside_each_cell():
    # 4 x 4 native pixels of 0.05 degrees: centres 0.025, 0.075, 0.125, 0.175
    lons = lats = np.array([0.025, 0.075, 0.125, 0.175])
    lats = lats + 10.0
    v = np.arange(16, dtype=float).reshape(4, 4)
    mean, count = bin_mean_to_grid(v, lons, lats, GL, GA)
    assert mean[0, 0] == pytest.approx((0 + 1 + 4 + 5) / 4)
    assert mean[0, 1] == pytest.approx((2 + 3 + 6 + 7) / 4)
    assert mean[1, 0] == pytest.approx((8 + 9 + 12 + 13) / 4)
    assert mean[1, 1] == pytest.approx((10 + 11 + 14 + 15) / 4)
    assert (count == 4).all()


def test_nan_pixels_are_ignored_and_empty_cells_are_nan():
    lons = lats = np.array([0.025, 0.075, 0.125, 0.175])
    lats = lats + 10.0
    v = np.ones((4, 4))
    v[0:2, 0:2] = np.nan  # the whole lower-left cell
    v[2, 2] = np.nan      # one of four pixels in the upper-right cell
    v[3, 3] = 5.0
    mean, count = bin_mean_to_grid(v, lons, lats, GL, GA)
    assert np.isnan(mean[0, 0]) and count[0, 0] == 0
    assert mean[1, 1] == pytest.approx((1 + 1 + 5) / 3) and count[1, 1] == 3


def test_pixels_outside_the_grid_are_dropped_and_descending_lats_work():
    lons = np.array([0.05, 0.15, 5.0])
    lats = np.array([10.15, 10.05])  # north to south, as most rasters are
    v = np.array([[1.0, 2.0, 99.0], [3.0, 4.0, 99.0]])
    mean, _ = bin_mean_to_grid(v, lons, lats, GL, GA)
    assert mean.tolist() == [[3.0, 4.0], [1.0, 2.0]]


def test_time_axis_is_kept():
    lons = lats = np.array([0.05, 0.15])
    mean, count = bin_mean_to_grid(np.stack([np.ones((2, 2)), 2 * np.ones((2, 2))]), lons, lats + 10, GL, GA)
    assert mean.shape == (2, 2, 2) and mean[0, 0, 0] == 1 and mean[1, 1, 1] == 2


def test_shape_mismatch_raises():
    with pytest.raises(ValueError):
        bin_mean_to_grid(np.ones((2, 3)), [0.05, 0.15], [10.05, 10.15], GL, GA)


def test_scattered_matches_hand_mean():
    lon = np.array([0.02, 0.08, 0.12, 0.18])
    lat = np.array([10.02, 10.08, 10.12, 10.18])
    v = np.array([1.0, 3.0, 10.0, np.nan])
    mean, count = bin_mean_scattered(v, lon, lat, GL, GA)
    assert mean[0, 0] == pytest.approx(2.0) and count[0, 0] == 2
    assert mean[1, 1] == pytest.approx(10.0) and count[1, 1] == 1
    assert np.isnan(mean[0, 1])


def test_nearest_cell_picks_closest_and_keeps_time():
    lons = np.array([88.25, 88.75, 89.25])
    lats = np.array([23.25, 23.75])
    field = np.arange(12, dtype=float).reshape(2, 2, 3)  # [time, lat, lon]
    val, cl, ca = nearest_cell(field, lons, lats, 88.7, 23.3)
    assert (cl, ca) == (88.75, 23.25)
    assert val.tolist() == [1.0, 7.0]


def test_slope_of_planes_is_exact():
    lats = np.linspace(23.0, 23.1, 21)[::-1]  # descending, as a raster
    step = 0.1 / 20
    lon_n = 21
    # north-south plane rising 5 degrees: z = tan(5 deg) * northing
    z_ns = (np.tan(np.radians(5)) * lats * M_PER_DEG)[:, None] * np.ones((1, lon_n))
    assert slope_degrees(z_ns, lats, step) == pytest.approx(5.0, abs=1e-6)
    # east-west plane rising 3 degrees: z = tan(3 deg) * easting, easting shrinks with cos(lat)
    easting = (np.arange(lon_n) * step * M_PER_DEG)[None, :] * np.cos(np.radians(lats))[:, None]
    assert slope_degrees(np.tan(np.radians(3)) * easting, lats, step) == pytest.approx(3.0, abs=1e-6)
    assert slope_degrees(np.full((21, 21), 7.0), lats, step) == pytest.approx(0.0)
