"""GET /api/v1/warnings?district=  weather-outlook warnings (proposal: docs/contract_change_proposals.md section 15).

Open-Meteo daily numbers (non-NASA partner data, live -> cache -> fixture) are compared, in
src/compute/weather_warnings, ONLY with thresholds that have a source row in data/reference/.
Nothing is computed or invented here. No warnings is an honest empty list.
register(app, envelope, error_response, ApiError, check_district, point_of) is called once from app.py."""

import datetime as dt
import hashlib

import open_meteo
import weather_warnings as ww

OM_ID = "om"
BD_TZ = dt.timezone(dt.timedelta(hours=6))


def _th_id(th):
    return "th_" + hashlib.sha1(f'{th["file"]}|{th["item"]}'.encode()).hexdigest()[:8]


def _measure(value, unit, src, decimals=1):
    return {"value": round(value, decimals), "unit": unit, "src": src}


def build_data(district, days, thresholds, found):
    """The `data` block and its provenance entries (om + one entry per threshold row used)."""
    warnings, used = [], {}
    for w in found:
        th = w["threshold"]
        used[_th_id(th)] = th
        for c in w["crops"]:
            used[_th_id(c)] = c
        warnings.append({
            "type": w["type"], "date": w["date"],
            "forecast": _measure(w["expected"]["value"], w["expected"]["unit"], [OM_ID]),
            "threshold": _measure(th["value"], th["unit"], [_th_id(th)]),
            "crops": [{"crop": c["crop"], "stage": {"en": c["stage_en"], "bn": c["stage_bn"]},
                       "threshold": _measure(c["value"], c["unit"], [_th_id(c)])} for c in w["crops"]],
            "action": w["action"]})
    dates = [d["date"] for d in days]
    data = {"district": district, "valid_from": dates[0] if dates else None,
            "valid_to": dates[-1] if dates else None, "warnings": warnings}
    prov = [{"id": tid, "dataset": t["source_title"], "url": t["source_url"], "agency": "",
             "period": str(t["year"]), "resolution": "", "retrieved": None,
             "granule_or_file": f'data/reference/{t["file"]}, item {t["item"]}',
             "note": f'Threshold row {t["item"]}' + (f', page {t["page"]}' if t["page"] else "")}
            for tid, t in sorted(used.items())]
    return data, prov


def om_provenance(district, lat, lon, days, retrieved):
    return {"id": OM_ID, "dataset": "Open-Meteo Forecast API: daily precipitation_sum, "
                                    "temperature_2m_max, temperature_2m_min",
            "url": "https://open-meteo.com/", "agency": "Open-Meteo (non-NASA partner data)",
            "period": f'{days[0]["date"]}/{days[-1]["date"]}' if days else "", "resolution": "~11 km grid",
            "retrieved": retrieved,
            "granule_or_file": f"{open_meteo.URL}?latitude={round(lat, 4)}&longitude={round(lon, 4)}"
                               f"&daily={open_meteo.DAILY}&timezone=Asia/Dhaka&forecast_days=7",
            "note": "Free for non-commercial use, attribution required: " + open_meteo.CREDIT}


def notices_for(mode, days, retrieved, skipped, found):
    out = [{"level": "info",
            "en": "Weather data is from Open-Meteo, not NASA. " + open_meteo.CREDIT + ".",
            "bn": "আবহাওয়ার তথ্য Open-Meteo থেকে, NASA নয়। Weather data by Open-Meteo.com (CC BY 4.0)।"},
           {"level": "info",
            "en": "This is a weather outlook for the area around your field, not a measurement at your field. "
                  "Warning limits come from published sources; the stage a crop is at is not checked.",
            "bn": "এটি আপনার জমির আশেপাশের এলাকার আবহাওয়ার আভাস, আপনার জমির মাপা তথ্য নয়। সতর্কতার সীমা "
                  "প্রকাশিত উৎস থেকে নেওয়া; ফসল কোন পর্যায়ে আছে তা যাচাই করা হয়নি।"}]
    if mode != "live":
        span = f'{days[0]["date"]} to {days[-1]["date"]}' if days else "unknown dates"
        out.insert(0, {"level": "caution",
                       "en": f"The live weather service could not be reached. This is a saved copy "
                             f"({mode}, fetched {retrieved or 'on an unknown date'}) covering {span}, "
                             "not today's outlook.",
                       "bn": f"সরাসরি আবহাওয়া সেবা পাওয়া যায়নি। এটি সংরক্ষিত কপি ({mode}, তারিখ "
                             f"{retrieved or 'অজানা'}), আজকের আভাস নয়।"})
    if skipped:
        out.append({"level": "info",
                    "en": f"{len(skipped)} possible warning types are not used because their limit has no "
                          "verified source yet.",
                    "bn": f"{len(skipped)}টি সম্ভাব্য সতর্কতার সীমার যাচাইকৃত উৎস এখনও নেই, তাই ব্যবহার করা হয়নি।"})
    if not found:
        out.append({"level": "info",
                    "en": "No warning limit is exceeded in these days.",
                    "bn": "এই দিনগুলোতে কোনো সতর্কতার সীমা অতিক্রম হয়নি।"})
    return out


def register(app, envelope, error_response, ApiError, check_district, point_of):
    from fastapi.responses import JSONResponse

    @app.get("/api/v1/warnings")
    def warnings(district: str = None):
        endpoint, request = "/api/v1/warnings", {"district": district}
        try:
            did = check_district(district)
            lat, lon = point_of(did)
            today = dt.datetime.now(BD_TZ).date().isoformat()
            try:
                days, mode, retrieved = open_meteo.fetch_outlook(did, lat, lon, today)
            except RuntimeError as err:
                raise ApiError("NO_DATA_FOR_PERIOD",
                               "The weather outlook is not available (no live, saved or demo copy).",
                               "Open-Meteo") from err
            thresholds, skipped = ww.load_thresholds()
            found = ww.evaluate_days(days, thresholds)
            data, prov = build_data(did, days, thresholds, found)
            body = envelope(endpoint, request, data, None, notices_for(mode, days, retrieved, skipped, found),
                            provenance=[om_provenance(did, lat, lon, days, retrieved)] + prov,
                            source_mode=mode)
            return JSONResponse(body)
        except ApiError as err:
            return error_response(endpoint, request, err)
        except Exception as exc:  # noqa: BLE001 - the contract forbids an empty body
            return error_response(endpoint, request, ApiError("INTERNAL", f"Internal error: {type(exc).__name__}"))
