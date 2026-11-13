"""The geoBoundaries ADM2 file committed in data/reference/ and the slug map."""

import os

import pytest

from district_grid.boundaries import LIVE_DISTRICTS, load_districts, slug_for

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FILE = os.path.join(ROOT, "data", "reference", "bgd_adm2_districts.geojson")


def test_file_is_small_and_has_64_districts():
    assert os.path.getsize(FILE) < 2_000_000
    d = load_districts()
    assert len(d) == 64
    assert len({x["slug"] for x in d}) == 64


def test_live_districts_resolve_to_their_polygons():
    slugs = {x["slug"] for x in load_districts()}
    assert set(LIVE_DISTRICTS) <= slugs
    assert slug_for("Comilla") == "cumilla" and slug_for("Brahamanbaria") == "brahmanbaria"


def test_unknown_boundary_name_is_an_error_not_a_guess():
    with pytest.raises(KeyError):
        slug_for("Atlantis")


def test_all_polygons_valid_inside_bangladesh_and_centroid_inside_polygon():
    for x in load_districts():
        assert x["geometry"].is_valid and x["geometry"].area > 0
        w, s, e, n = x["geometry"].bounds
        assert 87.9 <= w and e <= 92.8 and 20.5 <= s and n <= 26.7, x["slug"]
        assert x["geometry"].contains(x["point"]), x["slug"]


def test_every_district_has_a_licence_and_source_in_the_file():
    import json
    meta = json.load(open(FILE, encoding="utf-8"))["metadata"]
    assert "CC BY 3.0 IGO" in meta["license"] and meta["source_url"].startswith("https://")
