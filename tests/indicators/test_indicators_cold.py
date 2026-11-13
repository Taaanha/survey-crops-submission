"""Tmin-only cold limits from r04_cold_injury.csv: what is kept, what is rejected and why."""

import pandas as pd
import pytest

from indicators.cold_limits import is_tmin_row, load_cold_limits, parse_limit, select_cold_limits


@pytest.mark.parametrize("value,expected", [
    ("10", 10.0), ("-2.5", -2.5), ("below 10", 10.0), ("Below 10 ", 10.0),
    ("below 15 (SUSPECT)", None), ("below 10 (SUSPECT template)", None), ("12 to 13", None),
    ("-3.5 to -2.0", None), ("below 10 (first stage); max above 32 (later stages)", None), ("", None), ("GAP", None),
])
def test_parse_limit_accepts_only_a_plain_number_or_below_n(value, expected):
    assert parse_limit(value) == expected


@pytest.mark.parametrize("item,unit,expected", [
    ("boro_rice.cold.bamis_warning_tmin", "deg C Tmin", True),
    ("wheat.cold.ecocrop_tmin", "deg C", True),
    ("mustard.cold.frost_seed_kill_tmin", "deg C Tmin", True),
    ("boro_rice.cold.anthesis_critical_tmean", "deg C daily mean", False),   # daily mean
    ("wheat.cold.root_growth_tlmin", "deg C", False),                        # Tlmin = lethal minimum, type not Tmin
    ("boro_rice.cold.reduction_division_sterility_below", "deg C", False),   # temperature type not stated
    ("aman_rice.cold.pi_booting_temp_days", "days", False),                  # a duration
    ("boro_rice.cold.reproductive_duration_days_tmin", "days", False),       # *_days is skipped even if it says tmin
    ("boro_rice.cold.critical_night_temp", "deg C night", False),            # night temperature, not a Tmin tag
])
def test_is_tmin_row(item, unit, expected):
    assert is_tmin_row(item, unit) is expected


def raw(rows):
    cols = ["item", "value", "unit", "source_title", "source_url", "page", "year", "notes"]
    return pd.DataFrame(rows, columns=cols, dtype=str).fillna("")


def row(item, value, unit="deg C Tmin", url="https://example.org/x", title="Source", page="1"):
    return [item, value, unit, title, url, page, "2019", "n"]


def test_select_counts_by_hand():
    table = raw([
        row("boro_rice.cold.bamis_warning_tmin", "below 10"),                    # kept
        row("boro_rice.cold.bamis_warning_tmin", "below 10", page="2"),          # same item+value: dropped (duplicate)
        row("wheat.cold.ecocrop_tmin", "5", unit="deg C"),                       # kept
        row("boro_rice.cold.anthesis_critical_tmean", "22", unit="deg C daily mean"),   # tmean: skipped
        row("aman_rice.cold.pi_booting_temp_days", "3", unit="days"),            # *_days: skipped
        row("wheat.cold.bamis_warning_tmin", "below 15 (SUSPECT)"),              # not a plain limit
        row("maize.cold.bamis_warning_tmin", "below 10", url=""),                # no source link
        row("potato.cold.bamis_warning_tmin", "below 10", title="PLACEHOLDER x"),  # placeholder
    ])
    limits, rejected = select_cold_limits(table)
    assert [(g["item"], g["value"]) for g in limits] == [("boro_rice.cold.bamis_warning_tmin", 10.0),
                                                          ("wheat.cold.ecocrop_tmin", 5.0)]
    assert all(g["kind"] == "cold_nights" and g["variable"] == "tmin" and g["op"] == "<" for g in limits)
    reasons = {r["item"]: r["reason"] for r in rejected}
    assert reasons["wheat.cold.bamis_warning_tmin"].startswith("value")
    assert reasons["maize.cold.bamis_warning_tmin"].startswith("source_url")
    assert reasons["potato.cold.bamis_warning_tmin"].startswith("placeholder")
    assert reasons["boro_rice.cold.anthesis_critical_tmean"].startswith("not a Tmin")
    assert reasons["aman_rice.cold.pi_booting_temp_days"].startswith("not a Tmin")
    assert len(rejected) == 5        # suspect, no link, placeholder, tmean, days; the duplicate is dropped quietly


def test_real_file_gives_only_cited_tmin_rows():
    limits, rejected = load_cold_limits()
    items = {g["item"] for g in limits}
    assert items == {"boro_rice.cold.bamis_warning_tmin", "mustard.cold.bamis_warning_tmin",
                     "potato.cold.bamis_warning_tmin", "wheat.cold.ecocrop_tmin"}
    for g in limits:
        assert g["source_url"].startswith("http") and g["source_title"]
    names = {r["item"] for r in rejected}
    assert "wheat.cold.bamis_warning_tmin" in names        # SUSPECT in the file: not used
    assert "aman_rice.cold.bamis_warning_tmin" in names    # no source link: not used
    assert not any("tmean" in i for i in items)
