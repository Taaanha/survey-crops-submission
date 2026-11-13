"""Hand-made rotation evaluations (same shape as rotation.evaluate_rotation returns)
so every expected W4 indicator can be worked out by hand.

The hand counts used by the tests:
- aman sown 2001-06-15, harvest 2001-10-28 (135 days in the field);
  wheat sown 2001-11-15, harvest 2002-02-23 (100 days in the field).
  In-field days = 135 + 100 = 235, so bare days = 365 - 235 = 130.
- year 2002 uses the same dates one year later (365 - 235 = 130 again).
"""

PROV = {"dataset": "synthetic test weather", "source_url": "https://example.org/test",
        "retrieved": "2026-11-12", "granule_or_file": "tests/strategies/strategy_fixtures.py"}


def m(value, unit):
    return {"value": value, "unit": unit, "provenance": dict(PROV)}


def slot(crop, sow, harvest):
    return {"crop": crop, "sowing_date": sow, "harvest_date": harvest}


def year_row(year, slots, feasible=True, problem=False):
    return {"year": year, "feasible": feasible, "infeasible_reason": None if feasible else "late",
            "problem_year": None if not feasible else problem, "slots": slots}


def two_clean_years(problems=(False, False)):
    """Two feasible years, 130 bare days each (hand count in the module docstring)."""
    return [
        year_row(2001, [slot("aman_rice", "2001-06-15", "2001-10-28"),
                        slot("wheat", "2001-11-15", "2002-02-23")], problem=problems[0]),
        year_row(2002, [slot("aman_rice", "2002-06-15", "2002-10-28"),
                        slot("wheat", "2002-11-15", "2003-02-23")], problem=problems[1]),
    ]


def fake_eval(rot_id="aman_rice@06-15>wheat", rabi="wheat", years=None, n=None,
              problems=0, irrigation=100.0, legumes=0, unknown=(),
              checked=("heat_flowering", "waterlog")):
    years = two_clean_years() if years is None else years
    n = len(years) if n is None else n
    return {"district": "test",
            "rotation": {"id": rot_id,
                         "slots": [{"crop": "aman_rice"}, {"crop": rabi}]},
            "summary": {"n_years": m(n, "years"),
                        "feasible_years": m(sum(1 for y in years if y["feasible"]), "years"),
                        "problem_years": None if problems is None else m(problems, "years"),
                        "problem_years_by_hazard": {h: m(0, "years") for h in checked},
                        "problem_line": f"problems in {problems} of {n} years",
                        "irrigation_mm_worst20": None if irrigation is None else m(irrigation, "mm"),
                        "irrigation_mm_median": None if irrigation is None else m(irrigation, "mm"),
                        "legume_count": m(legumes, "crops"),
                        "legume_unknown_crops": list(unknown),
                        "hazards_checked": list(checked),
                        "hazards_missing": []},
            "years": years}
