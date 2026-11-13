"""
src/acquire/open_meteo.py

Free Open-Meteo weather outlook (next 7 days) for one district point. Open-Meteo is non-NASA partner
data: free for non-commercial use, attribution required (CC BY 4.0, https://open-meteo.com/). No API key.

Online-first through safe_fetch.fetch_json: live -> per-point per-day cache (cache/) -> fixture
(demo_fixtures/openmeteo_<district>.json). Only the backend calls this; web/ never does.
"""

import datetime as dt
import json
import os

import safe_fetch

URL = "https://api.open-meteo.com/v1/forecast"
DAILY = "precipitation_sum,temperature_2m_max,temperature_2m_min"
CREDIT = "Weather data by Open-Meteo.com (CC BY 4.0), https://open-meteo.com/"


def request_params(lat, lon):
    return {"latitude": round(lat, 4), "longitude": round(lon, 4), "daily": DAILY,
            "timezone": "Asia/Dhaka", "forecast_days": 7}


def parse_daily(payload):
    """[{"date", "rain_mm", "tmax_c", "tmin_c"}] from an Open-Meteo answer. A missing value stays None."""
    daily = payload["daily"]
    out = []
    for i, date in enumerate(daily["time"]):
        def pick(key):
            values = daily.get(key) or []
            return values[i] if i < len(values) and values[i] is not None else None
        out.append({"date": date, "rain_mm": pick("precipitation_sum"),
                    "tmax_c": pick("temperature_2m_max"), "tmin_c": pick("temperature_2m_min")})
    return out


def fetch_outlook(district, lat, lon, today=None):
    """Returns (days, source_mode, retrieved). source_mode is "live", "cache" or "fixture";
    retrieved is the date the numbers were fetched (None if a fixture does not say).
    Raises RuntimeError only if live, cache and fixture are all missing."""
    today = today or dt.date.today().isoformat()
    key = f"openmeteo_{district}_{today}"
    try:
        payload, mode = safe_fetch.fetch_json(URL, request_params(lat, lon), key, ttl_hours=12)
    except RuntimeError:
        fixture = os.path.join(safe_fetch.FIXTURE_DIR, f"openmeteo_{district}.json")
        if not os.path.exists(fixture):
            raise
        with open(fixture, encoding="utf-8") as f:
            payload, mode = json.load(f), "fixture"
    if mode == "live":
        retrieved = today
    elif mode == "cache" and os.path.exists(safe_fetch._cache_path(key)):
        retrieved = dt.date.fromtimestamp(os.path.getmtime(safe_fetch._cache_path(key))).isoformat()
    else:
        retrieved = payload.get("retrieved_on")
    return parse_daily(payload), mode, retrieved
