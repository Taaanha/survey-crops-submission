"""Tests for the W1b helpers: request bodies, the AppEEARS client (fake session), masks, tables."""
import numpy as np
import pandas as pd
import pytest

from w1b import appeears, convert, dem, products, tables


# ---------- products ----------
def test_area_task_body():
    t = products.area_task("smap_test", "smap", "2020-01-01", "2020-12-31", (87.85, 20.45, 92.95, 26.75))
    p = t["params"]
    assert t["task_type"] == "area"
    assert p["dates"] == [{"startDate": "01-01-2020", "endDate": "12-31-2020"}]
    assert {x["product"] for x in p["layers"]} == {"SPL4SMGP.008"}
    assert p["output"]["projection"] == "geographic"
    ring = p["geo"]["features"][0]["geometry"]["coordinates"][0]
    assert ring[0] == ring[-1] and len(ring) == 5


def test_area_task_rejects_bad_input():
    box = (87.85, 20.45, 92.95, 26.75)
    with pytest.raises(ValueError):
        products.area_task("x", "grace", "2020-01-01", "2020-12-31", box)  # not an AppEEARS product
    with pytest.raises(ValueError):
        products.area_task("x", "smap", "2020-02-01", "2020-01-01", box)
    with pytest.raises(ValueError):
        products.area_task("x", "smap", "2010-01-01", "2010-12-31", box)  # before SMAP L4 starts
    with pytest.raises(ValueError):
        products.area_task("x", "smap", "2020-01-01", "2020-12-31", box, layers=["nope"])
    with pytest.raises(ValueError):
        products.bbox_feature_collection((92, 20, 91, 26))


def test_catalogue_is_complete_and_sourced():
    for key, p in products.PRODUCTS.items():
        assert p["source_url"].startswith("https://"), key
        assert p["unit"] and p["native"] and p["start"] and p["tier"] in products.TIERS, key
    assert products.PRODUCTS["gedi"]["caveat"].startswith("mostly measures trees")
    assert products.year_chunks(2001, 2003)[0] == ("2001-01-01", "2001-12-31")
    assert len(products.year_chunks(2001, 2024)) == 24


# ---------- appeears client with a fake session ----------
class Resp:
    def __init__(self, payload=None, chunks=()):
        self.payload, self.chunks = payload, chunks

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload

    def iter_content(self, chunk_size=0):
        return iter(self.chunks)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeSession:
    def __init__(self, statuses):
        self.statuses, self.calls = list(statuses), []

    def post(self, url, **kw):
        self.calls.append(("POST", url, kw))
        return Resp({"token": "tok"} if url.endswith("/login") else {"task_id": "t1"})

    def get(self, url, **kw):
        self.calls.append(("GET", url, kw))
        if "/task/" in url:
            return Resp({"status": self.statuses.pop(0)})
        if url.endswith("/bundle/t1"):
            return Resp({"files": [{"file_id": "f1", "file_name": "a/b/out.nc", "file_size": 3},
                                   {"file_id": "f2", "file_name": "readme.txt"}]})
        return Resp(chunks=[b"ab", b"c"])


def test_client_flow(tmp_path):
    s = FakeSession(["pending", "processing", "done"])
    token = appeears.login(s, "user", "pw")
    assert token == "tok" and s.calls[0][2]["auth"] == ("user", "pw")
    assert appeears.submit(s, token, {"x": 1}) == "t1"
    assert appeears.wait(s, token, "t1", poll_s=1, sleep=lambda n: None) == "done"
    files = appeears.list_files(s, token, "t1")
    assert files == [("f1", "out.nc", 3)]
    dest = appeears.download(s, token, "t1", "f1", str(tmp_path / "d" / "out.nc"))
    assert open(dest, "rb").read() == b"abc" and not (tmp_path / "d" / "out.nc.part").exists()


def test_wait_raises_on_error_and_timeout():
    with pytest.raises(RuntimeError, match="error"):
        appeears.wait(FakeSession(["error"]), "tok", "t1", sleep=lambda n: None)
    with pytest.raises(RuntimeError, match="still"):
        appeears.wait(FakeSession(["pending"] * 5), "tok", "t1", poll_s=10, max_wait_s=20, sleep=lambda n: None)


# ---------- convert ----------
def test_mod13_keeps_only_good_pixels():
    vi = np.array([0.5, 0.6, -0.3, 0.7])
    rel = np.array([0, 1, -1, 0])  # -1 = fill, with the fill value -3000 x 0.0001 = -0.3
    out, share = convert.mod13_clean(vi, rel)
    assert out[0] == 0.5 and np.isnan(out[1]) and np.isnan(out[2]) and out[3] == 0.7
    assert share == pytest.approx(2 / 4)


def test_unscaled_values_are_caught():
    with pytest.raises(ValueError, match="scale factor"):
        convert.mod13_clean(np.array([5000.0, 6000.0, 7000.0]), np.zeros(3))


def test_fmask_bits():
    f = np.array([0, 2, 4, 8, 16, 32, 255, np.nan])  # clear, cloud, adjacent, shadow, snow, water, fill, fill-as-NaN
    assert convert.fmask_clear(f).tolist() == [True, False, False, False, False, True, False, False]


def test_hls_ndvi_by_hand():
    red, nir = np.array([0.1, 0.1, 0.0]), np.array([0.5, 0.5, 0.0])
    fm = np.array([0, 2, 0])
    out = convert.hls_ndvi(red, nir, fm)
    assert out[0] == pytest.approx((0.5 - 0.1) / 0.6)
    assert np.isnan(out[1]) and np.isnan(out[2])  # cloud; zero sum


def test_longitude_and_kelvin():
    assert convert.wrap_longitude([0.25, 90.25, 180.25, 359.75]).tolist() == [0.25, 90.25, -179.75, -0.25]
    assert convert.kelvin_to_celsius(300.15) == pytest.approx(27.0)


# ---------- tables ----------
def test_stack_to_district_table_matches_hand_mean():
    w = np.array([[[0.5, 0.0], [0.5, 0.0]], [[0.0, 1.0], [0.0, 0.0]]])  # two districts
    stack = np.array([[[2.0, 9.0], [4.0, 9.0]], [[np.nan, np.nan], [4.0, np.nan]]])
    t = tables.stack_to_district_table(stack, ["d1", "d2"], ["a", "b"], w, "v")
    a = t[t.district == "a"].reset_index(drop=True)
    b = t[t.district == "b"].reset_index(drop=True)
    assert a.v.tolist() == [3.0, 4.0] and a.coverage.tolist() == [1.0, 0.5]
    assert b.v[0] == 9.0 and np.isnan(b.v[1]) and b.coverage.tolist() == [1.0, 0.0]


def test_grace_nearest_cell_and_regional_flag():
    lons = np.array([88.25, 88.75, 271.25])  # 271.25 = -88.75
    lats = np.array([23.25, 23.75])
    lwe = np.arange(12, dtype=float).reshape(2, 2, 3)
    t = tables.grace_table(lwe, ["m1", "m2"], lons, lats, {"x": (88.7, 23.3), "y": (88.3, 23.7)})
    x = t[t.district == "x"]
    assert x.lwe_thickness_cm.tolist() == [1.0, 7.0] and x.regional.all()
    assert set(zip(t.cell_lon, t.cell_lat)) == {(88.75, 23.25), (88.25, 23.75)}


def test_column_rows_carry_dataset_unit_and_source():
    df = tables.column_rows([("ndvi", "modis", 2001, 2024, "good pixels only")])
    assert df.loc[0, "source_url"].startswith("https://") and df.loc[0, "unit"]


def test_dem_strips_give_mean_elevation_and_slope():
    step = 0.01  # 10 pixels per 0.1 degree cell
    lons = np.round(np.arange(0.005, 0.2, step), 4)
    lats = np.round(np.arange(10.005, 10.2, step), 4)
    lat_axis = lats[::-1]  # raster order, north first
    z = (np.tan(np.radians(4)) * lat_axis * products_m_per_deg())[:, None] * np.ones((1, lons.size))

    def read_strip(a, b):
        m = (lat_axis >= a) & (lat_axis <= b)
        return z[m], lons, lat_axis[m]

    gl, ga = np.array([0.05, 0.15]), np.array([10.05, 10.15])
    elev, slope, count = dem.dem_cell_stats(read_strip, gl, ga, step)
    assert (count == 100).all()
    assert slope == pytest.approx(np.full((2, 2), 4.0), abs=1e-6)
    assert elev[0, 0] == pytest.approx(np.tan(np.radians(4)) * 10.05 * products_m_per_deg(), rel=1e-9)


def products_m_per_deg():
    from district_grid.regrid import M_PER_DEG
    return M_PER_DEG


def test_gedi_cells_ignore_nodata():
    lon = np.array([[0.02, 0.08], [0.12, 0.18]])
    lat = np.full((2, 2), 10.02)
    mean, count = dem.gedi_cell_means(np.array([[10.0, -9999.0], [4.0, 6.0]]), lon, lat,
                                      np.array([0.05, 0.15]), np.array([10.05]), nodata=-9999.0)
    assert mean[0].tolist() == [10.0, 5.0] and count[0].tolist() == [1, 2]


# ---------- helpers added for the notebook ----------
def test_find_variable_and_coord():
    names = ["Geophysical_Data_sm_rootzone", "Geophysical_Data_sm_rootzone_pctl", "Geophysical_Data_sm_surface"]
    assert convert.find_variable(names, "Geophysical_Data_sm_rootzone") == names[0]
    assert convert.find_variable(names, "sm_surface") == names[2]
    with pytest.raises(KeyError, match="several"):
        convert.find_variable(names, "sm_root")
    with pytest.raises(KeyError, match="not found"):
        convert.find_variable(names, "nope")
    assert convert.find_coord(["time", "Latitude", "Longitude"], "lat") == "Latitude"
    assert convert.find_coord(["time", "y", "x"], "lon") == "x"
    with pytest.raises(KeyError):
        convert.find_coord(["time"], "lat")


def test_mask_range_and_et_conversion():
    assert np.isnan(convert.mask_range([-9999.0, 0.3, 0.95], *convert.SMAP_VALID)[[0, 2]]).all()
    assert convert.mask_range([0.3], *convert.SMAP_VALID)[0] == 0.3
    # 100 W/m2 for a day = 8.64 MJ/m2/day = 3.52512 mm/day
    assert convert.wm2_to_mm_per_day(100.0) == pytest.approx(3.52512)


def test_wide_table_and_coverage_summary():
    t = pd.DataFrame({"date": ["d1", "d2", "d1", "d2"], "district": ["a", "a", "b", "b"],
                      "v": [1.0, 2.0, 3.0, np.nan], "coverage": [1.0, 0.5, 1.0, 0.0]})
    w = tables.to_wide(t, "v")
    assert w.loc["d2", "a"] == 2.0 and np.isnan(w.loc["d2", "b"]) and list(w.columns) == ["a", "b"]
    s = tables.coverage_summary(t).set_index("district")
    assert s.loc["a", "min_coverage"] == 0.5 and s.loc["b", "share_of_dates_with_data"] == 0.5


def test_demo_bboxes_come_from_the_manifests():
    import os
    boxes = products.demo_field_bboxes(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "processed"))
    assert set(boxes) == {"feni", "cumilla"}
    w, s, e, n = boxes["feni"]
    assert 91 < w < e < 92 and 22 < s < n < 24


def test_scene_stats_by_hand():
    a = np.array([[[1.0, 3.0], [np.nan, np.nan]], [[np.nan, np.nan], [np.nan, np.nan]]])
    df = tables.scene_stats(a, ["s1", "s2"], "v", tile="feni")
    assert df.v[0] == 2.0 and df.clear_share[0] == 0.5
    assert np.isnan(df.v[1]) and df.clear_share[1] == 0.0 and (df.tile == "feni").all()
    with pytest.raises(ValueError):
        tables.scene_stats(a, ["s1"], "v")
