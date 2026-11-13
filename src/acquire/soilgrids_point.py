"""
src/acquire/soilgrids_point.py

Topsoil (0-30 cm) at one field point from ISRIC SoilGrids 2.0 (250 m, a
model estimate from soil surveys + satellite data, not a lab test), for
GET /api/v1/soil.

One REST call returns sand / silt / clay / pH(H2O) / organic carbon at the
three topsoil depths (0-5, 5-15, 15-30 cm). They are thickness-weighted into
one 0-30 cm value, and sand/silt/clay are classified into a USDA texture
class. Answers are cached on disk (soil does not change from day to day).

SoilGrids masks some cells (towns, rivers, water): the API then returns null.
That is reported as "no value" (None), never guessed.

Why a background fetch (measured 13 Nov 2026): rest.isric.org is a beta service
with no uptime promise. The same query answered in 0.3 s, hung for 60 s with no
answer, returned 502 after 22 s, and returned 503 at once. A 10 s wait on the
request therefore often gave up while the answer was still coming. Now the call
runs in a worker thread with a long timeout and retries; the request waits only
WAIT_S seconds for it. If it is late, the request is answered with the district
soil (and a notice that says so) and the worker still finishes and saves the
answer, so the next request gets it from the cache.

Order for one point: cache (memory, then disk) -> saved fixture
(demo_fixtures/soilgrids_points.json, exact point only) -> live. A point is
never filled from a neighbour.
"""

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from datetime import date

import requests

from fetch_soilgrids import usda_texture

URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
PROPERTIES = ("sand", "silt", "clay", "phh2o", "soc")
DEPTHS = {"0-5cm": 5, "5-15cm": 10, "15-30cm": 15}   # label -> layer thickness (cm)
CONNECT_TIMEOUT_S = 10    # to reach the server
READ_TIMEOUT_S = 60       # to wait for the answer, in the background worker
WAIT_S = 8                # how long one request waits for the worker
ATTEMPTS = 3              # tries per fetch (5xx, timeout, connection error only)
RETRY_DELAY_S = 5
FAIL_COOLDOWN_S = 60      # after a failure, do not call ISRIC again for this point
STALE_DAYS = 90           # an older cache entry is still used, and refreshed behind it

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CACHE_DIR = os.path.join(ROOT, "data", "processed", "soilgrids_cache")
FIXTURE_PATH = os.path.join(ROOT, "demo_fixtures", "soilgrids_points.json")


class SoilGridsError(Exception):
    """SoilGrids did not give a usable answer. `kind` says why, so the notice is true:
    "timeout" (no answer in time), "busy" (a fetch is still running in the background),
    "http" (the service answered with an error status), "bad_answer" (not usable JSON),
    "network" (could not connect)."""

    def __init__(self, message, kind="http"):
        super().__init__(message)
        self.kind = kind


def cache_path(lat, lon, cache_dir=None):
    return os.path.join(cache_dir or CACHE_DIR, f"{lat:.3f}_{lon:.3f}.json")


def parse_response(payload):
    """SoilGrids JSON -> {"sand","silt","clay" (%), "ph", "organic_carbon_g_kg",
    "texture"}, each 0-30 cm thickness-weighted. None for a property or the
    whole point when SoilGrids has no value there."""
    try:
        layers = payload["properties"]["layers"]
        raw = {}
        for layer in layers:
            d_factor = layer["unit_measure"]["d_factor"]
            total, thickness = 0.0, 0
            for depth in layer["depths"]:
                value = depth["values"]["mean"]
                if value is None:
                    total = None
                    break
                total += (value / d_factor) * DEPTHS[depth["label"]]
                thickness += DEPTHS[depth["label"]]
            raw[layer["name"]] = None if total is None else total / thickness
    except (KeyError, TypeError, ZeroDivisionError) as err:
        raise SoilGridsError(f"unexpected SoilGrids response ({type(err).__name__})") from err
    out = {"sand": raw.get("sand"), "silt": raw.get("silt"), "clay": raw.get("clay"),
           "ph": raw.get("phh2o"),
           # SoilGrids soc is dg/kg (d_factor 10 -> g/kg); organic carbon, not organic matter
           "organic_carbon_g_kg": raw.get("soc"), "texture": None}
    if out["sand"] is None and out["ph"] is None and out["organic_carbon_g_kg"] is None:
        return None
    if None not in (out["sand"], out["silt"], out["clay"]):
        scale = 100.0 / (out["sand"] + out["silt"] + out["clay"])   # fractions sum to 99-101
        for p in ("sand", "silt", "clay"):
            out[p] *= scale
        out["texture"] = usda_texture(out["sand"], out["silt"], out["clay"])
    return out


def fetch_point(lat, lon, get=None):
    """One SoilGrids call -> parse_response(). Raises SoilGridsError (with a kind)."""
    params = [("lon", lon), ("lat", lat), ("value", "mean")]
    params += [("property", p) for p in PROPERTIES] + [("depth", d) for d in DEPTHS]
    try:
        response = (get or requests.get)(URL, params=params,
                                         timeout=(CONNECT_TIMEOUT_S, READ_TIMEOUT_S))
    except requests.Timeout as err:
        raise SoilGridsError(type(err).__name__, "timeout") from err
    except requests.RequestException as err:
        raise SoilGridsError(type(err).__name__, "network") from err
    if response.status_code != 200:
        raise SoilGridsError(f"HTTP {response.status_code}", "http")
    try:
        payload = response.json()
    except ValueError as err:
        raise SoilGridsError("answer was not JSON", "bad_answer") from err
    return parse_response(payload)


def _retryable(err):
    """5xx, timeouts and connection errors are retried; 429 (rate limit), other 4xx and
    bad answers are not (a quick retry only makes a rate limit worse)."""
    if err.kind in ("timeout", "network"):
        return True
    return err.kind == "http" and str(err).startswith("HTTP 5")


def fetch_with_retry(lat, lon, get=None):
    """fetch_point() up to ATTEMPTS times for retryable errors, RETRY_DELAY_S apart."""
    for attempt in range(1, ATTEMPTS + 1):
        try:
            return fetch_point(lat, lon, get)
        except SoilGridsError as err:
            if attempt == ATTEMPTS or not _retryable(err):
                raise
            time.sleep(RETRY_DELAY_S)


# ---------------- cache, fixture, background worker ----------------

_lock = threading.Lock()
_pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix="soilgrids")
_memory = {}      # path -> {"soil", "retrieved"}   (works even on a read-only disk)
_inflight = {}    # path -> Future
_failed = {}      # path -> (time.monotonic(), error kind)


def reset_state():
    """Forget memory cache, running fetches and failures (tests)."""
    with _lock:
        _memory.clear(), _inflight.clear(), _failed.clear()


def join_background(timeout=10):
    """Wait for running fetches (tests)."""
    with _lock:
        futures = list(_inflight.values())
    for f in futures:
        try:
            f.result(timeout=timeout)
        except Exception:   # noqa: BLE001 - failures are recorded in _failed
            pass


def _read_disk(path):
    try:
        with open(path, encoding="utf-8") as f:
            rec = json.load(f)
        return {"soil": rec["soil"], "retrieved": rec.get("retrieved")}
    except (OSError, ValueError, KeyError):
        return None


def _is_stale(rec):
    try:
        age = date.today() - date.fromisoformat(rec["retrieved"])
        return age.days > STALE_DAYS
    except (TypeError, ValueError, KeyError):
        return False    # an old file with no date is kept (soil does not change daily)


def fixture_at(lat, lon, fixture_path=None):
    """Saved SoilGrids answer for exactly this point (same 3-decimal key as the cache), or
    None. -> {"soil": dict|None, "retrieved": "YYYY-MM-DD", "estimate": None | info}.
    A masked point with a neighbour-median `estimate` returns that estimate's soil and
    `estimate` = {"ring_km", "n_cells", "spread"} so the route can say it is not the
    point's own value. Only this exact point is looked up."""
    try:
        with open(fixture_path or FIXTURE_PATH, encoding="utf-8") as f:
            points = json.load(f)["points"]
    except (OSError, ValueError, KeyError):
        return None
    for pt in points:
        if (f"{pt['lat']:.3f}", f"{pt['lon']:.3f}") == (f"{lat:.3f}", f"{lon:.3f}"):
            if pt.get("status") not in ("assessed", "masked") or not pt.get("retrieved"):
                return None
            est = pt.get("estimate")
            if pt["status"] == "masked" and est and est.get("soil"):
                soil = dict(est["soil"])
                info = {"ring_km": est["ring_km"], "n_cells": est["n_cells"],
                        "spread": soil.pop("spread", {})}
                soil.pop("n_cells", None)
                return {"soil": soil, "retrieved": est["retrieved"], "estimate": info}
            return {"soil": pt["soil"] if pt["status"] == "assessed" else None,
                    "retrieved": pt["retrieved"], "estimate": None}
    return None


def _job(path, lat, lon, get):
    try:
        soil = fetch_with_retry(lat, lon, get)
    except SoilGridsError as err:
        with _lock:
            _failed[path] = (time.monotonic(), err.kind)
        raise
    rec = {"soil": soil, "retrieved": date.today().isoformat()}
    with _lock:
        _memory[path] = rec
        _failed.pop(path, None)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"lat": lat, "lon": lon, **rec}, f)
    except OSError:
        pass   # a read-only disk only loses the disk copy
    return soil


def _start(path, lat, lon, get):
    """One worker per point at a time. Returns its Future, or raises SoilGridsError when the
    point failed less than FAIL_COOLDOWN_S ago (ISRIC is not called again so soon)."""
    with _lock:
        running = _inflight.get(path)
        if running is not None and not running.done():
            return running
        failed = _failed.get(path)
        if failed and time.monotonic() - failed[0] < FAIL_COOLDOWN_S:
            raise SoilGridsError("failed a moment ago", failed[1])
        future = _pool.submit(_job, path, lat, lon, get)
        _inflight[path] = future
        return future


def _refresh_quietly(path, lat, lon, get):
    try:
        _start(path, lat, lon, get)
    except SoilGridsError:
        pass


def soil_at(lat, lon, cache_dir=None, get=None, with_meta=False):
    """-> (soil dict or None, source_mode "live"|"cache"|"fixture"); with_meta=True adds a
    third item {"retrieved": date or None}. None = SoilGrids has no value at this point.
    Raises SoilGridsError (see .kind) if there is no answer within WAIT_S and nothing is
    cached or saved; the fetch then keeps running and fills the cache for the next request."""
    path = cache_path(lat, lon, cache_dir)

    def done(soil, mode, retrieved=None, estimate=None):
        meta = {"retrieved": retrieved, "estimate": estimate}
        return (soil, mode, meta) if with_meta else (soil, mode)

    with _lock:
        rec = _memory.get(path)
    rec = rec or _read_disk(path)
    if rec is not None:
        if _is_stale(rec):
            _refresh_quietly(path, lat, lon, get)
        return done(rec["soil"], "cache", rec.get("retrieved"))
    saved = fixture_at(lat, lon)
    if saved is not None:
        if saved["soil"] is not None and saved["estimate"] is None:   # masked / estimated: no refresh
            _refresh_quietly(path, lat, lon, get)
        return done(saved["soil"], "fixture", saved["retrieved"], saved["estimate"])
    future = _start(path, lat, lon, get)
    try:
        soil = future.result(timeout=WAIT_S)
    except FutureTimeout as err:
        raise SoilGridsError(f"no answer in {WAIT_S} s; still fetching", "busy") from err
    return done(soil, "live", date.today().isoformat())
