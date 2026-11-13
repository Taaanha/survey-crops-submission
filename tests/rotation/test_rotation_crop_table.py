"""data/reference/crops.csv: every filled cell has a source pointer; every blank cell is
flagged in needs_source; filled values agree with the cited reference rows."""

import risk_calendar as rc

from rotation import load_crop_table

CELL_SRC = {"duration_days": "duration_src", "sow_start_mmdd": "window_src",
            "sow_end_mmdd": "window_src", "seedling_age_days": "seedling_src",
            "kc_stages": "kc_src", "gdd_base_c": "gdd_src", "heat_limit_c": "heat_src",
            "cold_limit_c": "cold_src", "flood_tolerance_days": "flood_src",
            "salt_ECt_dSm": "salt_src", "salt_slope_pct": "salt_src",
            "is_legume": "legume_src"}


def test_every_filled_cell_has_a_source_and_every_blank_is_flagged():
    table = load_crop_table()
    assert {"aman_rice", "wheat", "mustard", "lentil", "boro_rice"} <= set(table["crop"])
    for _, row in table.iterrows():
        for cell, src in CELL_SRC.items():
            if row[cell]:
                assert row[src], f"{row['crop']}.{cell} has a value but no source"
            else:
                direct_seeded = cell == "seedling_age_days" and row["crop"] not in (
                    "aman_rice", "boro_rice")    # seedling age only applies to transplanted rice
                assert direct_seeded or cell in row["needs_source"], \
                    f"{row['crop']}.{cell} is blank but not listed in needs_source"


def test_filled_values_match_the_cited_reference_rows():
    ref = rc.load_reference_for_calendar()
    for _, row in load_crop_table().iterrows():
        if row["duration_days"] and row["duration_src"].startswith("crop_calendar.csv:"):
            cited = rc.resolve_range(ref, row["duration_src"].split(":", 1)[1])
            assert cited is not None, row["duration_src"]
            assert cited["low"] <= float(row["duration_days"]) <= cited["high"], row["crop"]
        if row["heat_limit_c"]:
            cited = rc.resolve_range(ref, row["heat_src"].split(":", 1)[1])
            assert cited is not None and float(row["heat_limit_c"]) in (cited["low"], cited["high"])


def test_unsourced_columns_stay_blank():
    table = load_crop_table()
    assert (table["salt_ECt_dSm"] == "").all() and (table["salt_slope_pct"] == "").all()
    assert set(table["is_legume"]) <= {"yes", "no"}   # filled only where legume_src cites a page (fixups, 0.6)
