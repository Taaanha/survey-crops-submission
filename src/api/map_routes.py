"""W5 map endpoints (proposed in docs/contract_change_proposals.md section 11). They only read the
Layer 1 map_layers module and wrap the result in the standard envelope; the web page never computes.

register(app, envelope, ApiError) is called once from app.py."""

import functools

from fastapi import Request
from fastapi.responses import JSONResponse

from map_layers import layers as L
from map_layers import outlines, passport, scenario
from sat_layers.status import NotAssessed

BASE = "/api/v1/map"
SCENARIO_DISTRICTS = ("cumilla", "feni", "brahmanbaria", "noakhali", "sylhet")


def _prov(*entries):
    out, seen = [], set()
    for e in entries:
        url = e.get("source_url") or e.get("url")
        if url and url not in seen:
            seen.add(url)
            out.append({"id": f"m{len(out) + 1}", "dataset": e.get("dataset", ""), "url": url, **e})
    return out


def register(app, envelope, ApiError):
    def respond(endpoint, request, build):
        try:
            data, notices, provenance = build()
            return JSONResponse(envelope(endpoint, request, data, None, notices, provenance=provenance))
        except ApiError as err:
            body = envelope(endpoint, request, None,
                            errors=[{"code": err.code, "en": err.en, "bn": err.bn}], provenance=[])
            return JSONResponse(body, status_code=err.status)
        except Exception as exc:  # noqa: BLE001 - the contract forbids an empty body
            err = ApiError("INTERNAL", f"Internal error: {type(exc).__name__}")
            return JSONResponse(envelope(endpoint, request, None, provenance=[], errors=[
                {"code": err.code, "en": err.en, "bn": err.bn}]), status_code=500)

    @functools.lru_cache(maxsize=1)
    def catalogue():
        return L.catalog()

    @app.get(BASE + "/layers")
    def map_layers():
        def build():
            cat = catalogue()
            data = {"layers": cat, "years": [L.YEARS[0], L.YEARS[-1]], "seasons": list(L.SEASONS),
                    "note": "Layers that are not assessed stay in the list, disabled, with their reason."}
            return data, [], _prov(*cat)
        return respond(BASE + "/layers", {}, build)

    @app.get(BASE + "/outlines")
    def map_outlines():
        def build():
            data = outlines.district_outlines()
            return data, [], _prov(data["provenance"])
        return respond(BASE + "/outlines", {}, build)

    @app.get(BASE + "/values")
    def map_values(layer: str = None, year: str = None, season: str = None):
        request = {"layer": layer, "year": year, "season": season}

        def build():
            if not layer:
                raise ApiError("BAD_PARAMETER", "Missing parameter: layer.", "layer")
            entry = next((e for e in catalogue() if e["key"] == layer), None)
            if entry is None:
                raise ApiError("BAD_PARAMETER", f"Unknown layer {layer!r}.", "layer")
            if not entry["enabled"]:
                raise ApiError("NO_DATA_FOR_PERIOD", f"{layer} is not assessed: {entry['reason']}",
                               entry["reason"])
            y = None
            if not entry["static"]:
                try:
                    y = int(year)
                except (TypeError, ValueError):
                    raise ApiError("BAD_PARAMETER", "year must be a whole year, 2001-2024.", "year") from None
            try:
                data = L.layer_values(layer, year=y, season=season)
            except NotAssessed as err:
                raise ApiError("NO_DATA_FOR_PERIOD", str(err), str(err)) from None
            except ValueError as err:
                raise ApiError("BAD_PARAMETER", str(err), "year or season") from None
            return data, [], _prov(data["provenance"])
        return respond(BASE + "/values", request, build)

    @app.get(BASE + "/scenario")
    def map_scenario(district: str = None, crop: str = None, rain_pct: str = None,
                     temp_add_c: str = None, sowing: str = None):
        request = {"district": district, "crop": crop, "rain_pct": rain_pct, "temp_add_c": temp_add_c,
                   "sowing": sowing}

        def build():
            if not district:
                raise ApiError("BAD_PARAMETER", "Missing parameter: district.", "district")
            if district.lower() not in SCENARIO_DISTRICTS:
                raise ApiError("DISTRICT_NOT_COVERED", "The scenario sliders cover the five live districts.")
            try:
                data = scenario.run_scenario(district.lower(), crop, rain_pct or 0, temp_add_c or 0,
                                             sowing or None)
            except ValueError as err:
                raise ApiError("BAD_PARAMETER", str(err), str(err)) from None
            notices = [{"level": "info", "en": scenario.LABEL,
                        "bn": "অতীতের মৌসুমের উপর \"যদি\" হিসাব, পূর্বাভাস নয়।"}]
            return data, notices, data["provenance"] and _prov(*data["provenance"])
        return respond(BASE + "/scenario", request, build)

    @app.get(BASE + "/passport")
    def map_passport(field: str = None, half_width: str = "7"):
        request = {"field": field, "half_width": half_width}

        def build():
            if not field:
                raise ApiError("BAD_PARAMETER", "Missing parameter: field.", "field")
            try:
                data = passport.field_passport(field, half_width=int(half_width))
            except KeyError as err:
                raise ApiError("BAD_PARAMETER", str(err).strip("'\""), "field") from None
            except ValueError as err:
                raise ApiError("BAD_PARAMETER", str(err), "half_width") from None
            return data, [], _prov(*data["layers"], *data["vulnerability_zones"]["zones"].values())
        return respond(BASE + "/passport", request, build)
