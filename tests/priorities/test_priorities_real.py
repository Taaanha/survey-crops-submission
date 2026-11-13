"""T2 on real Cumilla data: the rotation module exposes the flood-related counts
and rank_rotations ranks the real candidates."""

import pytest

from priorities import rank_rotations
from rotation import candidate_rotations, evaluate_rotation, load_context


@pytest.fixture(scope="module")
def ctx():
    return load_context("cumilla")


def test_rotation_summary_exposes_problem_years_per_hazard(ctx):
    mustard = [r for r in candidate_rotations("cumilla", ctx) if r["id"].endswith(">mustard")][0]
    s = evaluate_rotation("cumilla", mustard, context=ctx)["summary"]
    by = s["problem_years_by_hazard"]
    assert set(by) == set(s["hazards_checked"])
    assert by["waterlog"]["unit"] == "years" and by["waterlog"]["provenance"]["dataset"]
    full = evaluate_rotation("cumilla", mustard, context=ctx)
    hits = [y["slots"][-1]["hazards_hit"] for y in full["years"] if y["feasible"]]
    for hazard, count in by.items():                      # equals a hand count over the years
        assert count["value"] == sum(hazard in h for h in hits)
    assert s["problem_years"]["value"] == sum(bool(h) for h in hits)


def test_rank_rotations_on_real_data(ctx):
    weights = {"save_water": 0.5, "lowest_risk": 0.5}
    result = rank_rotations("cumilla", weights, context=ctx)
    assert result["ranked"], result
    assert [r["rank"] for r in result["ranked"]] == list(range(1, len(result["ranked"]) + 1))
    for row in result["ranked"]:
        assert abs(sum(c["contribution"] for c in row["components"].values()) - row["score"]) < 1e-9
        assert row["components"]["save_water"]["raw"]["provenance"]["source_url"]
    assert rank_rotations("cumilla", weights, context=ctx) == result
