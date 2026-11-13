"""W4 acceptance on real data (Cumilla): the baseline is always shown, three or
more strategies appear, unsourced values appear only as gaps, excluded crops
are listed with reasons, and no user-facing text says predict or forecast."""

import json

import pytest

from strategies import build_strategies

BASELINE_ID = "aman_rice@06-15>boro_rice"


@pytest.fixture(scope="module")
def result():
    return build_strategies("cumilla", current=BASELINE_ID)


def test_baseline_is_always_shown_first(result):
    assert result["baseline"]["id"] == BASELINE_ID
    assert result["baseline"]["role"] == "baseline"
    assert result["baseline"]["card"]


def test_three_or_more_strategies(result):
    assert 1 + len(result["alternatives"]) >= 3
    for s in result["alternatives"]:
        assert s["role"] == "alternative"
        assert list(s["card"]) == ["why_suggested", "evidence", "benefits",
                                   "information_gaps", "risks_to_check_locally"]


def test_every_indicator_is_assessed_or_a_gap_never_a_bare_zero(result):
    for s in [result["baseline"], *result["alternatives"]]:
        for name, ind in s["indicators"].items():
            assert ind["status"] in ("assessed", "gap"), (s["id"], name)
            if ind["status"] == "gap":
                assert ind["reason"], (s["id"], name)


def test_assessed_numbers_carry_dataset_and_source_url(result):
    def walk(node):
        if isinstance(node, dict):
            if set(node) >= {"value", "unit", "provenance"}:
                prov = node["provenance"]
                assert prov.get("dataset"), node
                assert str(prov.get("source_url", "")).startswith("http") or \
                    prov.get("source_url"), node
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(result)


def test_crops_not_offered_are_listed_with_reasons(result):
    names = {row["crop"] for row in result["crops_not_offered"]}
    # khesari, maize and sesame have reference rows but no usable crops.csv row
    assert {"khesari", "maize", "sesame"} <= names
    for row in result["crops_not_offered"]:
        assert row["reason"]


def test_priority_matrix_covers_all_strategies(result):
    ids = {result["baseline"]["id"], *(s["id"] for s in result["alternatives"])}
    assert set(result["priority_matrix"]["cells"]) == ids


def test_no_predict_or_forecast_anywhere(result):
    text = json.dumps(result).lower()
    assert "predict" not in text
    assert "forecast" not in text


def test_bare_days_and_erosion_are_labelled_honestly(result):
    for s in [result["baseline"], *result["alternatives"]]:
        bare = s["indicators"]["bare_field_days"]
        if bare["status"] == "assessed":
            assert "not satellite-observed" in bare["note"]
        ero = s["indicators"]["erosion_exposure"]
        if ero["status"] == "assessed":
            assert "relative" in ero["index"]["unit"]


def test_unknown_current_rotation_is_a_clear_error():
    with pytest.raises(ValueError, match="current"):
        build_strategies("cumilla", current="aman_rice@06-15>dragonfruit")
