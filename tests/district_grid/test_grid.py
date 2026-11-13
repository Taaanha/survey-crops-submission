"""District averages on the common 0.1 degree grid: hand calculations on small fixture grids."""

import numpy as np
import pytest
from shapely.geometry import box

from district_grid.grid import cell_weights, district_mean, imerg_axes

# 3 x 3 grid, cell centres 0.05, 0.15, 0.25 (lon) and 0.05, 0.15, 0.25 (lat)
LONS = np.array([0.05, 0.15, 0.25])
LATS = np.array([0.05, 0.15, 0.25])


def test_imerg_axes_are_the_ges_disc_cell_centres():
    lons, lats = imerg_axes()
    assert lons[0] == pytest.approx(87.85) and lons[-1] == pytest.approx(92.95)
    assert lats[0] == pytest.approx(20.45) and lats[-1] == pytest.approx(26.75)
    assert len(lons) == 52 and len(lats) == 64
    assert np.allclose(np.diff(lons), 0.1) and np.allclose(np.diff(lats), 0.1)


def test_weights_are_area_fractions():
    # polygon covers the whole cell (0..0.1, 0..0.1) and the left half of cell (0.1..0.2, 0..0.1)
    w = cell_weights(box(0.0, 0.0, 0.15, 0.1), LONS, LATS)
    assert w.shape == (3, 3)                       # [lat, lon]
    assert w[0, 0] == pytest.approx(1.0)
    assert w[0, 1] == pytest.approx(0.5)
    assert w.sum() == pytest.approx(1.5)


def test_district_mean_matches_hand_calculation():
    field = np.array([[10.0, 20.0, 99.0],
                      [99.0, 99.0, 99.0],
                      [99.0, 99.0, 99.0]])          # [lat, lon]
    w = cell_weights(box(0.0, 0.0, 0.15, 0.1), LONS, LATS)
    mean, coverage = district_mean(field, w)
    assert mean == pytest.approx((10 * 1.0 + 20 * 0.5) / 1.5)   # = 13.333...
    assert coverage == pytest.approx(1.0)


def test_missing_cells_are_left_out_and_coverage_says_so():
    field = np.array([[10.0, np.nan, 5.0],
                      [5.0, 5.0, 5.0],
                      [5.0, 5.0, 5.0]])
    w = cell_weights(box(0.0, 0.0, 0.15, 0.1), LONS, LATS)
    mean, coverage = district_mean(field, w)
    assert mean == pytest.approx(10.0)
    assert coverage == pytest.approx(1.0 / 1.5)     # 1.0 of 1.5 weight observed


def test_all_missing_gives_nan_not_zero():
    mean, coverage = district_mean(np.full((3, 3), np.nan), cell_weights(box(0, 0, 0.1, 0.1), LONS, LATS))
    assert np.isnan(mean) and coverage == 0.0


def test_time_stack_means_each_day_separately():
    stack = np.stack([np.full((3, 3), 2.0), np.full((3, 3), 4.0)])   # [time, lat, lon]
    w = cell_weights(box(0.0, 0.0, 0.3, 0.3), LONS, LATS)
    mean, coverage = district_mean(stack, w)
    assert mean.tolist() == pytest.approx([2.0, 4.0])
    assert coverage.tolist() == pytest.approx([1.0, 1.0])


def test_polygon_outside_grid_has_zero_weight():
    assert cell_weights(box(5, 5, 6, 6), LONS, LATS).sum() == 0.0
