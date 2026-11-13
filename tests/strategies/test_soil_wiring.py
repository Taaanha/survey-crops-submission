"""The W4 organic-matter indicator carries the SoilGrids baseline, labelled, with gaps named."""

from strategies import cards, core

LABEL = "SoilGrids model estimate, 250 m, not a soil test; confirm with a local soil test"
SOIL = {"status": "assessed", "label": LABEL, "point_id": "feni",
        "organic_carbon": {"status": "assessed", "layers": []},
        "ph": {"status": "assessed", "layers": []}}


def test_residue_gap_plus_soil_is_assessed_with_both_parts():
    om = core.attach_soil({"status": "gap", "reason": "no cited residue row"}, SOIL)
    assert om["status"] == "assessed" and om["soil_baseline"] is SOIL
    assert om["by_crop"] == {} and "no cited residue row" in om["residue_note"]


def test_residue_assessed_keeps_by_crop():
    base = {"status": "assessed", "by_crop": {"wheat": {"status": "assessed"}}}
    om = core.attach_soil(base, SOIL)
    assert om["by_crop"] == base["by_crop"] and om["soil_baseline"] is SOIL


def test_both_gaps_stay_gap_with_both_reasons():
    om = core.attach_soil({"status": "gap", "reason": "no residue"},
                          {"status": "gap", "reason": "SoilGrids returned null"})
    assert om["status"] == "gap"
    assert "no residue" in om["reason"] and "SoilGrids returned null" in om["reason"]


def test_soil_gap_with_residue_rows_notes_the_gap():
    base = {"status": "assessed", "by_crop": {"wheat": {"status": "assessed"}}}
    om = core.attach_soil(base, {"status": "gap", "reason": "SoilGrids returned null"})
    assert om["status"] == "assessed" and "SoilGrids returned null" in om["soil_note"]


def test_card_benefits_line_uses_the_exact_label():
    soil = {**SOIL, "organic_carbon": {"status": "assessed", "layers": [{
        "depth": "0-5cm",
        "mean": {"value": 12.0, "unit": "g/kg"},
        "q05": {"value": 8.0, "unit": "g/kg"}, "q95": {"value": 17.0, "unit": "g/kg"}}]}}
    ind = {"organic_matter": core.attach_soil({"status": "gap", "reason": "x"}, soil)}
    text = " ".join(cards._benefits({}, ind))
    assert LABEL in text and "12.0 g/kg" in text and "8.0" in text and "17.0" in text
    assert "predict" not in text.lower() and "forecast" not in text.lower()


def test_card_names_soil_gap_under_information_gaps():
    ind = {"organic_matter": core.attach_soil(
        {"status": "assessed", "by_crop": {"wheat": {"status": "assessed"}}},
        {"status": "gap", "reason": "SoilGrids returned null at this point"})}
    assert any("SoilGrids returned null" in line for line in cards._gaps(ind))
