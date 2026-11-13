"""Hand-made rotation evaluations (same shape as rotation.evaluate_rotation
returns) so every expected score can be worked out by hand."""

PROV = {"dataset": "synthetic test weather", "source_url": "https://example.org/test",
        "retrieved": "2026-10-24", "granule_or_file": "tests/priorities/priority_fixtures.py"}


def m(value, unit):
    return {"value": value, "unit": unit, "provenance": dict(PROV)}


def fake_eval(rot_id, irrigation=100.0, legumes=0, problems=0, flood=None, n=24,
              unknown=(), checked=("heat_flowering", "waterlog")):
    """irrigation None = not modelled; problems None = not assessed;
    flood = years with a waterlogging problem (None = waterlogging not assessed)."""
    hazards = [h for h in checked if not (h == "waterlog" and flood is None)]
    by_hazard = {h: m(0, "years") for h in hazards}
    if flood is not None:
        by_hazard["waterlog"] = m(flood, "years")
    return {"district": "test",
            "rotation": {"id": rot_id, "slots": [{"crop": "aman_rice"}, {"crop": rot_id}]},
            "summary": {"n_years": m(n, "years"),
                        "problem_years": None if problems is None else m(problems, "years"),
                        "problem_years_by_hazard": by_hazard,
                        "problem_line": f"problems in {problems} of {n} years",
                        "irrigation_mm_worst20": None if irrigation is None else m(irrigation, "mm"),
                        "legume_count": m(legumes, "crops"),
                        "legume_unknown_crops": list(unknown),
                        "hazards_checked": hazards},
            "years": []}
