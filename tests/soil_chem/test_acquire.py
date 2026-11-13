"""SoilGrids pH / organic-carbon fetch: unit conversion is read from the service's own
metadata (d_factor), masked cells become gaps, nothing is guessed."""

import pytest

import soilgrids_ph_oc as sg
from soil_fixtures import masked_payload, payload

PT = {"point_id": "demo", "point_type": "district_centroid", "lat": 23.0, "lon": 91.0}


def rows_of(p, **kw):
    return sg.parse_point(p, PT, fetch_date="2026-11-13", **kw)


def pick(rows, prop, depth, stat):
    hit = [r for r in rows if (r["property"], r["depth"], r["statistic"]) == (prop, depth, stat)]
    assert len(hit) == 1
    return hit[0]


def test_row_count_is_2_properties_x_3_depths_x_4_statistics():
    assert len(rows_of(payload())) == 24


def test_ph_converted_with_d_factor_from_metadata():
    r = pick(rows_of(payload()), "phh2o", "0-5cm", "mean")
    assert (r["raw_value"], r["d_factor"], r["value"], r["units"]) == (55, 10, 5.5, "pH")
    assert r["mapped_units"] == "pH*10"


def test_quantiles_converted_too():
    rows = rows_of(payload())
    assert pick(rows, "phh2o", "0-5cm", "Q0.05")["value"] == 4.5
    assert pick(rows, "phh2o", "0-5cm", "Q0.95")["value"] == 6.8


def test_soc_dg_per_kg_to_g_per_kg():
    r = pick(rows_of(payload()), "soc", "5-15cm", "mean")
    assert (r["raw_value"], r["value"], r["units"], r["mapped_units"]) == (100, 10.0, "g/kg", "dg/kg")


def test_factor_is_not_hard_coded():
    """If the service ever changed d_factor to 100, the output must follow it."""
    r = pick(rows_of(payload(ph_factor=100)), "phh2o", "0-5cm", "mean")
    assert r["value"] == 0.55 and r["d_factor"] == 100


def test_unexpected_mapped_units_is_refused():
    p = payload()
    p["properties"]["layers"][0]["unit_measure"]["mapped_units"] = "pH*100"
    with pytest.raises(sg.SoilGridsError):
        rows_of(p)


def test_masked_cell_is_a_gap_with_reason_never_a_value():
    rows = rows_of(masked_payload())
    assert len(rows) == 24
    assert all(r["status"] == "gap" and r["value"] == "" and r["raw_value"] == "" for r in rows)
    assert all("null" in r["reason"] for r in rows)


def test_missing_property_in_response_is_a_gap():
    p = payload()
    p["properties"]["layers"] = p["properties"]["layers"][:1]   # no soc at all
    rows = rows_of(p)
    soc = [r for r in rows if r["property"] == "soc"]
    assert len(soc) == 12 and all(r["status"] == "gap" for r in soc)


def test_every_row_carries_dataset_url_resolution_and_date():
    for r in rows_of(payload()):
        assert r["dataset"].startswith("ISRIC SoilGrids 2.0")
        assert r["source_url"].startswith("https://")
        assert r["resolution"] == "250 m"
        assert r["fetch_date"] == "2026-11-13"


def test_http_error_gives_gap_rows_not_exception_in_build():
    def bad_get(url, params=None, timeout=None):
        class R:
            status_code = 503
        return R()
    rows = sg.fetch_rows([PT], get=bad_get, sleep=lambda s: None, fetch_date="2026-11-13")
    assert len(rows) == 24 and all(r["status"] == "gap" and "HTTP 503" in r["reason"] for r in rows)


def test_rate_limit_sleeps_between_calls_not_before_first():
    calls, naps = [], []

    class R:
        status_code = 200

        def json(self):
            return payload()

    def get(url, params=None, timeout=None):
        calls.append(params)
        return R()
    pts = [dict(PT, point_id=f"p{i}") for i in range(3)]
    sg.fetch_rows(pts, get=get, sleep=naps.append, fetch_date="2026-11-13")
    assert len(calls) == 3 and naps == [sg.PAUSE_S, sg.PAUSE_S]
    assert sg.PAUSE_S >= 12       # service fair use: 5 calls per minute
    assert ("value", "Q0.05") in calls[0] and ("value", "mean") in calls[0]


def test_failed_call_is_retried_once_masked_cell_is_not():
    attempts = []

    class Ok:
        status_code = 200

        def json(self):
            return payload()

    class Boom:
        status_code = 503

    def flaky(url, params=None, timeout=None):
        attempts.append(1)
        return Boom() if len(attempts) == 1 else Ok()
    rows = sg.fetch_rows([PT], get=flaky, sleep=lambda s: None, fetch_date="2026-11-13")
    assert len(attempts) == 2 and all(r["status"] == "assessed" for r in rows)

    attempts.clear()

    class Masked:
        status_code = 200

        def json(self):
            return masked_payload()
    sg.fetch_rows([PT], get=lambda *a, **k: (attempts.append(1), Masked())[1],
                  sleep=lambda s: None, fetch_date="2026-11-13")
    assert len(attempts) == 1
