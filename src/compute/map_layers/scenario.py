"""Scenario sliders for the map (W5, Layer 1): the same past seasons, re-run with a different
rain amount and a warmer climate.

The BACKEND does this; the web page only shows the result. At rain 0 % and warming 0 C the answer
is exactly the plain Layer 1 FAO-56 water balance (`water_balance.crop_season`) over 2001-2024.
It is a "what-if on past seasons", never a forecast of a coming season. No AI, no network."""

import functools
import math
import re
from datetime import datetime

import numpy as np
import pandas as pd

import risk_calendar as rc
from indicators.thresholds import load_thresholds
from reference import load_reference
from water_balance import crop_season, load_crop_params, load_soil_params, weather_table
from weather import RAIN_CITATIONS, load_weather

LABEL = "what-if on past seasons, not a forecast"
RAIN_RANGE = (-30.0, 30.0)     # percent, asked for by the plan (W5)
TEMP_RANGE = (0.0, 2.0)        # degrees C added to the daily Tmax, Tmin and Tmean
YEARS = tuple(range(2001, 2025))
CROPS = tuple(c for c, m in rc.WATER_MODEL.items() if m == "fao56")
KC_PATH = rc.KC_TABLE_PATH
POWER_SOURCE = {"dataset": "NASA POWER daily, AG community (temperature, humidity, wind, solar)",
                "source_url": "https://power.larc.nasa.gov/docs/services/api/temporal/daily/"}
ASSUMPTIONS = [
    "Rain: every day's rain amount is multiplied by the slider (+30 % = 1.3 times); the days it rains "
    "on do not change. Temperature: the slider is added to every day's highest, lowest and mean "
    "temperature.",
    "Relative humidity, wind and sunshine stay as observed, so the warmer-day evaporation uses the "
    "same relative humidity (a simplification: in a warmer climate the air could also hold more "
    "water vapour).",
    "Evaporation (FAO-56 Penman-Monteith), the soil bucket and the sowing date are the same as in "
    "the plain water balance; only the weather changes.",
    "Heat counts are days above a cited limit anywhere in the crop's season; each limit applies to "
    "one growth stage (shown), so the count is an upper bound for that stage.",
]


def _number(name, value, low, high):
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number") from None
    if not math.isfinite(v) or not low <= v <= high:
        raise ValueError(f"{name} must be between {low:g} and {high:g}")
    return v


def apply_scenario(raw, rain_pct, temp_add_c):
    """Copy of a POWER+IMERG weather table with rain x (1 + rain_pct/100) and all three
    temperatures + temp_add_c. Humidity, wind and solar are unchanged."""
    rain = _number("rain_pct", rain_pct, *RAIN_RANGE)
    temp = _number("temp_add_c", temp_add_c, *TEMP_RANGE)
    out = raw.copy()
    out["rainfall_mm"] = raw["rainfall_mm"].astype(float) * (1 + rain / 100)
    for col in ("temp_mean_c", "temp_max_c", "temp_min_c"):
        out[col] = raw[col].astype(float) + temp
    return out


def heat_days_in_season(season, limits):
    """{item: days} above each limit (strictly) in one season's daily temperatures."""
    out = {}
    for lim in limits:
        col = "temp_max_c" if lim["variable"] == "tmax" else "temp_min_c"
        out[lim["item"]] = rc.count_days(season[col].to_numpy(), lim["value"], ">")
    return out


def heat_limits(crop):
    """The cited heat and hot-night limits of a crop (W2's thresholds, same source rows)."""
    return [t for t in load_thresholds()
            if t["crop"] == crop and t["kind"] in ("heat_days", "night_heat_days")]


def default_sowing(crop):
    """The start of the cited sowing window as 'MM-DD' (rows of data/reference/crop_calendar.csv)."""
    window = rc.build_crop_spec(load_reference(), crop)["window"]
    if window is None:
        raise ValueError(f"no cited sowing window for {crop}; give sowing='MM-DD'")
    month, day = window["start"]
    return f"{month:02d}-{day:02d}"


def _check_sowing(sowing):
    if not isinstance(sowing, str) or not re.fullmatch(r"\d{2}-\d{2}", sowing):
        raise ValueError("sowing must be 'MM-DD'")
    try:
        datetime.strptime("2001-" + sowing, "%Y-%m-%d")
    except ValueError:
        raise ValueError("sowing is not a real date") from None
    return sowing


def _with_et0(weather, latitude, elevation):
    water = weather_table(weather, latitude, elevation)
    return weather[["temp_mean_c", "temp_max_c", "temp_min_c"]].join(water)


def run_on_weather(raw, latitude, elevation, crop, sowing, rain_pct, temp_add_c,
                   kc_table, crop_params, soil, limits, years=YEARS):
    """The season results for one weather table (raw = load_weather output). Pure: no file reads."""
    w = _with_et0(apply_scenario(raw, rain_pct, temp_add_c), latitude, elevation)
    month, day = (int(x) for x in sowing.split("-"))
    rows = []
    for year in years:
        try:
            res = crop_season(crop, pd.Timestamp(year=year, month=month, day=day), w, kc_table,
                              crop_params, soil)
        except ValueError as err:
            if "does not cover" in str(err):
                continue
            raise
        heat = heat_days_in_season(w.loc[res["daily"].index], limits)
        rows.append({"year": year, "irrigation_mm": res["net_irrigation_mm"],
                     "water_stress_days": res["water_stress_days"], "rain_mm": res["rain_mm"],
                     "etc_mm": res["etc_mm"], "heat": heat})
    if not rows:
        raise ValueError("the weather covers none of the requested seasons")
    irr = [r["irrigation_mm"] for r in rows]
    heat_summary = []
    for lim in limits:
        counts = [r["heat"][lim["item"]] for r in rows]
        heat_summary.append({
            "item": lim["item"], "stage": lim["stage"], "limit": lim["value"], "unit": lim["unit"],
            "variable": lim["variable"], "mean_days": round(float(np.mean(counts)), 2),
            "years_with_any": int(sum(c > 0 for c in counts)), "n_years": len(counts),
            "source_title": lim["source_title"], "source_url": lim["source_url"]})
    return {
        "n_years": len(rows), "years": [r["year"] for r in rows],
        "irrigation_mm_mean": round(float(np.mean(irr)), 1),
        "irrigation_mm_worst20": round(float(rc.worst_mean(irr)), 1),
        "water_stress_days_mean": round(float(np.mean([r["water_stress_days"] for r in rows])), 1),
        "rain_mm_mean": round(float(np.mean([r["rain_mm"] for r in rows])), 1),
        "etc_mm_mean": round(float(np.mean([r["etc_mm"] for r in rows])), 1),
        "heat": heat_summary,
        "per_year": [{"year": r["year"], "irrigation_mm": r["irrigation_mm"],
                      "water_stress_days": r["water_stress_days"], "rain_mm": r["rain_mm"]}
                     for r in rows],
    }


@functools.lru_cache(maxsize=8)
def _raw(district):
    return load_weather(district)


@functools.lru_cache(maxsize=1)
def _static():
    kc = pd.read_csv(KC_PATH)
    meta = pd.read_csv(rc.DISTRICT_METADATA_PATH).set_index("district")
    return kc, load_crop_params(), load_soil_params(), meta


@functools.lru_cache(maxsize=64)
def _run(district, crop, sowing, rain_pct, temp_add_c):
    kc, params, soils, meta = _static()
    m = meta.loc[district]
    return run_on_weather(_raw(district), float(m["latitude"]), float(m["elevation_m"]), crop, sowing,
                          rain_pct, temp_add_c, kc, params, soils[district], heat_limits(crop))


def run_scenario(district, crop, rain_pct, temp_add_c, sowing=None):
    """The baseline (0 %, +0 C) and the chosen what-if for one district and crop, with the
    difference between them. Raises ValueError for anything not supported or out of range."""
    _, _, soils, meta = _static()
    if district not in soils or district not in meta.index:
        raise ValueError(f"no water-balance inputs for district {district!r}; known: {sorted(soils)}")
    if crop not in CROPS:
        raise ValueError(f"crop must be one of {list(CROPS)}")
    sowing = _check_sowing(sowing) if sowing else default_sowing(crop)
    rain = _number("rain_pct", rain_pct, *RAIN_RANGE)
    temp = _number("temp_add_c", temp_add_c, *TEMP_RANGE)
    base = _run(district, crop, sowing, 0.0, 0.0)
    scen = base if (rain == 0 and temp == 0) else _run(district, crop, sowing, rain, temp)
    delta = {k: round(scen[k] - base[k], 1) for k in
             ("irrigation_mm_mean", "irrigation_mm_worst20", "water_stress_days_mean", "rain_mm_mean",
              "etc_mm_mean")}
    delta["heat_mean_days"] = {h["item"]: round(h["mean_days"] - b["mean_days"], 2)
                               for h, b in zip(scen["heat"], base["heat"])}
    provenance = [
        {"dataset": RAIN_CITATIONS["imerg"]["dataset"], "source_url": RAIN_CITATIONS["imerg"]["url"]},
        dict(POWER_SOURCE),
        {"dataset": "FAO-56 Table 22 root depth and depletion fraction (data/reference/crop_params.csv); "
                    "Kc values from data/processed/kc_table.csv (its public page is still an open "
                    "question in PROJECT_STATE)",
         "source_url": "https://www.fao.org/4/x0490e/x0490e0e.htm"},
    ] + [{"dataset": h["source_title"], "source_url": h["source_url"]} for h in base["heat"]]
    seen, unique = set(), []
    for p in provenance:
        if p["source_url"] not in seen:
            seen.add(p["source_url"])
            unique.append(p)
    return {"label": LABEL, "inputs": {"district": district, "crop": crop, "sowing_mmdd": sowing,
                                       "rain_pct": rain, "temp_add_c": temp},
            "ranges": {"rain_pct": list(RAIN_RANGE), "temp_add_c": list(TEMP_RANGE)},
            "baseline": base, "scenario": scen, "delta": delta, "assumptions": ASSUMPTIONS,
            "provenance": unique}
