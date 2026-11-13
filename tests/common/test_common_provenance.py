"""common.Provenance / measured: a number cannot be built without a source."""

import pytest

from common import Provenance, measured

GOOD = dict(dataset="NASA GPM IMERG V07 Final Run",
            source_url="https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary",
            retrieved="2026-10-24", granule_or_file="data/processed/imerg_cumilla_daily.csv")


def test_measured_carries_value_unit_and_provenance():
    out = measured(12.5, "mm", Provenance(**GOOD, note="daily sum"))
    assert out["value"] == 12.5 and out["unit"] == "mm"
    assert out["provenance"] == {**GOOD, "note": "daily sum"}


@pytest.mark.parametrize("missing", ["dataset", "source_url", "retrieved", "granule_or_file"])
def test_missing_or_blank_source_field_is_rejected(missing):
    with pytest.raises(ValueError):
        Provenance(**{**GOOD, missing: "  "})


def test_measured_rejects_a_plain_dict_as_provenance():
    with pytest.raises(TypeError):
        measured(1, "mm", GOOD)


def test_provenance_is_immutable():
    p = Provenance(**GOOD)
    with pytest.raises(Exception):
        p.dataset = "other"
