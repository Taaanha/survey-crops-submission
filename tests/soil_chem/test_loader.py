import csv

import pytest

import soil_chem as sc
import soilgrids_ph_oc as sg
from soil_fixtures import masked_payload, payload

DATE = "2026-11-13"


@pytest.fixture
def csv_path(tmp_path):
    rows = []
    rows += sg.parse_point(payload(), {"point_id": "feni", "point_type": "district_centroid",
                                       "lat": 23.0, "lon": 91.4}, fetch_date=DATE)
    rows += sg.parse_point(masked_payload(), {"point_id": "cumilla", "point_type": "district_centroid",
                                              "lat": 23.46, "lon": 91.18}, fetch_date=DATE)
    path = tmp_path / "soil.csv"
    sg.write_csv(rows, str(path))
    return str(path)


def test_csv_roundtrip_has_required_columns(csv_path):
    with open(csv_path, newline="", encoding="utf-8") as fh:
        head = next(csv.reader(fh))
    for col in ("dataset", "source_url", "property", "depth", "units", "resolution", "fetch_date"):
        assert col in head


def test_baseline_values_and_provenance(csv_path):
    b = sc.soil_baseline("feni", csv_path)
    assert b["status"] == "assessed"
    assert b["label"] == ("SoilGrids model estimate, 250 m, not a soil test; "
                          "confirm with a local soil test")
    oc = b["organic_carbon"]
    assert oc["status"] == "assessed"
    top = oc["layers"][0]
    assert top["depth"] == "0-5cm"
    assert (top["mean"]["value"], top["mean"]["unit"]) == (12.0, "g/kg")
    assert (top["q05"]["value"], top["q95"]["value"]) == (8.0, 17.0)
    prov = top["mean"]["provenance"]
    assert prov["source_url"].startswith("https://") and prov["retrieved"] == DATE
    assert b["ph"]["layers"][2]["mean"]["value"] == 5.8


def test_masked_point_is_gap_with_reason(csv_path):
    b = sc.soil_baseline("cumilla", csv_path)
    assert b["status"] == "gap" and "null" in b["reason"]


def test_unknown_point_is_gap_not_error(csv_path):
    b = sc.soil_baseline("sylhet", csv_path)
    assert b["status"] == "gap" and "not fetched" in b["reason"]


def test_missing_file_is_gap(tmp_path):
    b = sc.soil_baseline("feni", str(tmp_path / "nope.csv"))
    assert b["status"] == "gap"


def test_status_rows_partial_when_some_points_masked(csv_path):
    rows = sc.status_rows(csv_path)
    assert [r["key"] for r in rows] == ["soilgrids_ph", "soilgrids_soc"]
    for r in rows:
        assert r["status"] == "partial" and "cumilla" in r["reason"] and r["resolution"] == "250 m"
        assert r["districts"] == 1


def test_status_rows_when_file_missing_is_not_assessed(tmp_path):
    rows = sc.status_rows(str(tmp_path / "nope.csv"))
    assert all(r["status"] == "not assessed" for r in rows)


def test_no_forbidden_words():
    import inspect
    src = inspect.getsource(sc)
    assert "predict" not in src.lower() and "forecast" not in src.lower()
