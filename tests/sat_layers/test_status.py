"""The status table reader, and the real status table against the real files."""
import pandas as pd
import pytest

from sat_layers import intake
from sat_layers.status import COLUMNS, NotAssessed, load_status, require_assessed, status_of


def table(tmp_path, rows):
    p = tmp_path / "status.csv"
    pd.DataFrame(rows, columns=COLUMNS).to_csv(p, index=False)
    return str(p)


ROW = ["k", "d", "c", 1, "assessed", "r", "https://x", "u", "res"]


def test_reader_returns_status_and_reason(tmp_path):
    p = table(tmp_path, [ROW[:4] + ["not assessed", "job did not finish"] + ROW[6:]])
    assert status_of("k", p) == ("not assessed", "job did not finish")


def test_unknown_key_and_bad_status_are_errors(tmp_path):
    with pytest.raises(KeyError):
        status_of("missing", table(tmp_path, [ROW]))
    with pytest.raises(ValueError, match="unknown status"):
        load_status(table(tmp_path, [ROW[:4] + ["done"] + ROW[5:]]))


def test_require_assessed(tmp_path):
    p = table(tmp_path, [["a"] + ROW[1:4] + ["assessed"] + ROW[5:], ["p"] + ROW[1:4] + ["partial"] + ROW[5:],
                         ["n"] + ROW[1:4] + ["not assessed"] + ROW[5:]])
    assert require_assessed("a", path=p) == "assessed"
    assert require_assessed("p", path=p) == "partial"
    with pytest.raises(NotAssessed):
        require_assessed("p", allow_partial=False, path=p)
    with pytest.raises(NotAssessed, match="not assessed"):
        require_assessed("n", path=p)


# ---------- the real table ----------
def test_real_status_table_matches_the_files():
    shipped = load_status()
    built = intake.build_status(intake.run_checks())
    pd.testing.assert_frame_equal(shipped.reset_index(drop=True), built.reset_index(drop=True), check_dtype=False)


def test_real_status_values_you_asked_for():
    assert status_of("smap_64")[0] == "not assessed" and "did not finish" in status_of("smap_64")[1]
    assert "five live districts use the existing point files" in status_of("smap_64")[1]
    assert status_of("ecostress_et")[0] == "not assessed" and "units unresolved" in status_of("ecostress_et")[1]
    assert status_of("nasadem_elevation")[0] == "assessed"
    assert "relative ranking" in status_of("nasadem_slope")[1]
    assert "never district groundwater" in status_of("grace_fo")[1]
    with pytest.raises(NotAssessed):
        require_assessed("ecostress_et")
    df = load_status()
    assert (df.reason.str.len() > 0).all() and df.source_url.str.startswith("https://").all()


def test_real_modis_join_and_years():
    from sat_layers import loaders as L
    m = L.load_modis()
    assert len(m.data) == 14784 and m.data.district.nunique() == 64  # 10 files x 1536 rows, minus 9 x 64 overlap copies
    assert L.modis_years_present(m.data) == list(range(2015, 2025))
    table, status = L.ndvi_anomaly(m.data, "feni")
    assert status == "partial (10 years of 24 present)" and table.n_other.max() == 9


def test_real_grace_and_hls_counts():
    from sat_layers import loaders as L
    g = L.load_grace().data
    assert L.grace_cells(g) == (48, 3) and len(L.grace_gaps(g)) == 20
    c = L.hls_clear_counts(L.load_hls().data).set_index(["tile", "sensor"])
    assert c.loc[("feni", "hls_l30"), "usable"] == 15 and c.loc[("cumilla", "hls_l30"), "usable"] == 27
