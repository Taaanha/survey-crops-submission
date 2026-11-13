"""T3b: COG layers, the public field_profile() API, JRC label, "not covered", HF source.

Uses a tiny 8 x 8 grid cut from the Feni grid so nothing here needs the network or big files."""

import json
import os

import numpy as np
import pytest
import rasterio
from rasterio.warp import transform

from field_profile import field_profile, district_grid, write_layers
from field_profile.profile import AREA_NOTE

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FIXTURE_DIR = os.path.join(ROOT, "tests", "fixtures", "field_profile")
RULES = dict(min_obs_per_event=2, max_drain_window_days=12, dry_obs_to_separate_events=2,
             hand_masked_as="not_water")
DATES = ["2024-08-21", "2024-08-27", "2024-09-02", "2024-09-08", "2024-09-14", "2024-09-20",
         "2024-09-26", "2024-10-02"]
JRC_INFO = {"dataset": "JRC Global Surface Water occurrence v1.5 (1984-2024)",
            "source_url": "https://global-surface-water.appspot.com/download",
            "licence": "Copernicus Programme, free of charge without restriction of use",
            "retrieved": "2026-10-24"}


def tiny_grid():
    g = dict(district_grid("feni"))
    g.update(width=8, height=8)
    return g


def centre_lonlat(grid, row, col):
    a, _, c, _, e, f = grid["transform"]
    x, y = c + (col + 0.5) * a, f + (row + 0.5) * e
    lon, lat = transform(grid["crs"], "EPSG:4326", [x], [y])
    return lat[0], lon[0]


def entries():
    return [{"date": d, "granules": {"DSWx-HLS": [], "DSWx-S1": [f"S1_GRANULE_{d}"]},
             "source_urls": [f"https://example.org/{d}_B01_WTR.tif"]} for d in DATES]


@pytest.fixture()
def layers(tmp_path):
    g = tiny_grid()
    stack = np.zeros((len(DATES), 8, 8), dtype=np.uint8)
    stack[2:5, 3, 4] = 2             # open-water flood d2..d4, dry again after
    stack[2:5, 3, 5] = 1             # inundated vegetation only (flooded paddy)
    stack[:, 0, 0] = 255             # never observed
    jrc = np.zeros((8, 8), dtype=np.uint8)
    jrc[3, 4] = 97
    jrc[7, 7] = 255
    write_layers("feni", g, DATES, stack, entries(), str(tmp_path), rules=RULES, jrc=jrc,
                 jrc_info=JRC_INFO, built="2026-10-24")
    return str(tmp_path), g


def test_layers_are_cogs_with_manifest(layers):
    out, g = layers
    files = sorted(os.listdir(out))
    assert "layers_manifest_feni.json" in files
    m = json.load(open(os.path.join(out, "layers_manifest_feni.json"), encoding="utf-8"))
    assert m["district"] == "feni" and m["grid"]["width"] == 8
    assert m["rules"]["max_drain_window_days"] == 12
    assert os.path.getsize(os.path.join(out, "layers_manifest_feni.json")) < 1_000_000
    for name in m["files"].values():
        with rasterio.open(os.path.join(out, name)) as ds:
            assert ds.width == 8 and ds.height == 8
            assert ds.crs.to_string() == g["crs"]
    with rasterio.open(os.path.join(out, m["files"]["open_water"])) as ds:
        assert "n_events" in ds.descriptions and "drain_date" in ds.descriptions
        assert ds.profile.get("tiled") or ds.driver == "GTiff"


def test_open_water_flood_pixel(layers):
    out, g = layers
    lat, lon = centre_lonlat(g, 3, 4)
    r = field_profile(lat, lon, district="feni", layers_dir=out)
    assert r["covered"] is True and r["district"] == "feni"
    ow = r["metrics"]["open_water"]
    assert ow["n_events"] == 1 and ow["status"] == "ok"
    assert ow["first_wet_date"] == DATES[2] and ow["last_wet_date"] == DATES[4]
    assert ow["drain_date"] == DATES[5] and ow["drain_window"] == [DATES[4], DATES[5]]
    assert ow["gap_days"] == 6
    assert ow["inundation_days_min"] == 12 and ow["inundation_days_max"] == 24
    # top-level copies are the open-water (main) numbers
    assert r["drain_window"] == ow["drain_window"] and r["gap_days"] == 6 and r["status"] == "ok"
    # provenance: granule IDs of the last-wet and first-dry observations
    prov = r["provenance"]
    assert prov["granule_ids"]["open_water"]["last_wet"] == [f"S1_GRANULE_{DATES[4]}"]
    assert prov["granule_ids"]["open_water"]["first_dry"] == [f"S1_GRANULE_{DATES[5]}"]
    assert prov["retrieved"] and prov["datasets"]
    assert "20 km window" in r["area_note"] and r["area_note"] == AREA_NOTE
    assert "open water" in ow["label"].lower() and "context" in r["metrics"]["any_water"]["label"].lower()


def test_jrc_is_labelled_non_nasa(layers):
    out, g = layers
    r = field_profile(*centre_lonlat(g, 3, 4), district="feni", layers_dir=out)
    j = r["jrc_occurrence"]
    assert j["value_pct"] == 97 and "non-NASA" in j["label"]
    assert j["source_url"].startswith("http") and j["dataset"].startswith("JRC")
    # no-data pixel is None, not 0
    r = field_profile(*centre_lonlat(g, 7, 7), district="feni", layers_dir=out)
    assert r["jrc_occurrence"]["value_pct"] is None


def test_paddy_only_pixel_has_no_open_water_flood(layers):
    out, g = layers
    r = field_profile(*centre_lonlat(g, 3, 5), district="feni", layers_dir=out)
    assert r["metrics"]["open_water"]["n_events"] == 0
    assert r["metrics"]["open_water"]["drain_date"] is None
    assert r["metrics"]["any_water"]["n_events"] == 1
    assert r["metrics"]["any_water"]["drain_date"] == DATES[5]


def test_unobserved_pixel_is_not_zero(layers):
    out, g = layers
    r = field_profile(*centre_lonlat(g, 0, 0), district="feni", layers_dir=out)
    assert r["covered"] is True
    ow = r["metrics"]["open_water"]
    assert ow["status"] == "no observations" and ow["n_events"] is None


def test_never_wet_pixel_reports_zero_events(layers):
    out, g = layers
    r = field_profile(*centre_lonlat(g, 6, 2), district="feni", layers_dir=out)
    assert r["metrics"]["open_water"]["n_events"] == 0
    assert r["metrics"]["open_water"]["status"] == "no event"


def test_outside_box_is_not_covered(layers):
    out, g = layers
    r = field_profile(24.8949, 91.8687, layers_dir=out)               # Sylhet
    assert r["covered"] is False and r["status"] == "not covered"
    assert "metrics" not in r and "n_events" not in r
    assert r["area_note"] == AREA_NOTE
    # inside the real 20 km box but outside the tiny test grid
    r = field_profile(23.0159, 91.3976, district="feni", layers_dir=out)
    assert r["covered"] is False


def test_district_found_from_point_when_not_given(layers):
    out, g = layers
    r = field_profile(*centre_lonlat(g, 3, 4), layers_dir=out)
    assert r["covered"] is True and r["district"] == "feni"


def test_source_hf_uses_downloaded_layers(layers, monkeypatch):
    out, g = layers
    calls = []

    def fake_download(district, dest, repo=None):
        calls.append(district)
        return out
    monkeypatch.setattr("field_profile.hf.download_layers", fake_download)
    r = field_profile(*centre_lonlat(g, 3, 4), district="feni", source="hf",
                      cache_dir=os.path.join(out, "cache"))
    assert calls == ["feni"] and r["covered"] is True


def test_bad_source_raises():
    with pytest.raises(ValueError):
        field_profile(23.0, 91.4, source="ftp")


def test_real_fixture_channel_pixel_through_profile_stack():
    from field_profile import profile_stack
    meta = json.load(open(os.path.join(FIXTURE_DIR, "feni_river_meta.json"), encoding="utf-8"))
    arrays = np.load(os.path.join(FIXTURE_DIR, "feni_river_50x50.npz"))
    dates = [d["date"] for d in meta["dates"]]
    out = profile_stack(dates, arrays["merged"], "open_water", RULES)
    cy, cx = meta["channel_pixel"]
    assert out["n_events"][cy, cx] == 1                  # a river is open water, not many events
    assert out["n_observed"][cy, cx] >= 3
