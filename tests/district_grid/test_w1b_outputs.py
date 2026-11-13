"""The W1b NASADEM and GRACE-FO result files in data/processed/ are complete and labelled."""
import os

import numpy as np
import pandas as pd

from district_grid.boundaries import load_districts

P = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
SLUGS = {d["slug"] for d in load_districts()}


def test_nasadem_has_all_64_districts_with_full_coverage():
    n = pd.read_csv(os.path.join(P, "nasadem_district_static.csv"))
    assert set(n.district) == SLUGS and len(n) == 64
    assert not n.isna().any().any()
    assert (n.filter(like="coverage") == 1.0).all().all()
    assert n.elev_mean_m.between(0, 300).all() and n.slope_mean_deg.between(0, 30).all()
    hills = n.set_index("district").slope_mean_deg
    assert hills["bandarban"] > 5 * hills["noakhali"]  # hill district vs delta district


def test_nasadem_cell_grid_matches_the_common_grid():
    from district_grid.grid import imerg_axes
    c = np.load(os.path.join(P, "nasadem_cells_0p1deg.npz"))
    lons, lats = imerg_axes()
    assert np.allclose(c["lons"], lons) and np.allclose(c["lats"], lats)
    assert c["elev_mean_m"].shape == (len(lats), len(lons))


def test_grace_is_regional_and_names_its_cell():
    g = pd.read_csv(os.path.join(P, "grace_district_monthly.csv"))
    assert set(g.district) == SLUGS
    assert g.groupby("district").size().nunique() == 1  # same dates for every district
    assert g.regional.all() and not g.isna().any().any()
    assert g.drop_duplicates("district").groupby(["cell_lon", "cell_lat"]).size().max() >= 2  # cells are shared
    assert g.lwe_thickness_cm.abs().max() < 200  # centimetres, not metres or mm


def test_every_value_column_has_dataset_unit_and_source():
    cols = pd.read_csv(os.path.join(P, "nasadem_grace_columns.csv"))
    assert set(cols.column) == {"elev_mean_m", "slope_mean_deg", "lwe_thickness_cm", "uncertainty_cm"}
    assert cols.source_url.str.startswith("https://").all() and cols.unit.notna().all() and cols.dataset.notna().all()
    assert cols.set_index("column").loc["lwe_thickness_cm", "note"].startswith("REGIONAL")
