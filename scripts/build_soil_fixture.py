"""
scripts/build_soil_fixture.py

Writes demo_fixtures/soilgrids_points.json: the SoilGrids topsoil answer (0-30 cm, same
shape the /api/v1/soil route uses) for the demo points (5 district centres; the 2 demo-field
tile centres share a 3-decimal key with their district), so the Farm page still shows pH and
organic carbon when SoilGrids is down or slow.

A point SoilGrids answers with null is stored as "masked" and gets a labelled `estimate`: the
median of the real SoilGrids cells in a ring around it (src/acquire/soilgrids_neighbours.py;
never presented as the point's own value). A failed call is "no cell", never a guess. A point
that could not be fetched is left OUT (the file only holds real answers).

Fast and safe to stop: WORKERS calls at a time, a PAUSE_S pause before each call, the file is
saved after every point (run it again and it resumes), a hard TIME_LIMIT_S budget, progress
printed as it goes. A HTTP 429 (rate limit) stops the run. Run from the repo root:

    python scripts/build_soil_fixture.py [--refresh] [--limit 300]
"""

import argparse
import json
import os
import sys
import threading
import time
from datetime import date

import pandas as pd
import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "acquire"))

import soilgrids_neighbours as nb  # noqa: E402
import soilgrids_point as sg  # noqa: E402

POINTS_CSV = os.path.join(ROOT, "data", "processed", "soilgrids_ph_oc_points.csv")
OUT = sg.FIXTURE_PATH
WORKERS = 4            # calls at a time
PAUSE_S = 1.5          # pause before every call, per worker
TIME_LIMIT_S = 300     # hard budget for the whole run
CALL_TIMEOUT = (8, 20)  # connect, read: a hung call must not eat the budget


class Stop(Exception):
    """Time budget used up, or ISRIC asked us to slow down (429)."""


def key(lat, lon):
    return f"{lat:.3f}_{lon:.3f}"


def wanted_points():
    """Demo points of the W4b fetch, one entry per 3-decimal key."""
    df = pd.read_csv(POINTS_CSV, usecols=["point_id", "lat", "lon"]).drop_duplicates()
    out = {}
    for row in df.itertuples():
        out.setdefault(key(row.lat, row.lon), {"lat": float(row.lat), "lon": float(row.lon),
                                               "labels": []})["labels"].append(row.point_id)
    return list(out.values())


def make_caller(deadline, state):
    """fetch(lat, lon) -> soil dict | None; raises Stop or SoilGridsError."""
    def get(url, params, timeout):
        return requests.get(url, params=params, timeout=CALL_TIMEOUT)

    def call(lat, lon):
        if state["stop"] or time.monotonic() > deadline:
            raise Stop("time limit")
        time.sleep(PAUSE_S)
        try:
            return sg.fetch_point(lat, lon, get)
        except sg.SoilGridsError as err:
            if str(err) == "HTTP 429":
                state["stop"] = "rate limited (HTTP 429)"
                raise Stop(state["stop"]) from err
            raise
    return call


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="fetch every point again")
    ap.add_argument("--limit", type=float, default=TIME_LIMIT_S, help="time budget, seconds")
    args = ap.parse_args()
    deadline, state = time.monotonic() + args.limit, {"stop": None}
    call = make_caller(deadline, state)
    try:
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, ValueError):
        old = {}
    have = {key(p["lat"], p["lon"]): p for p in old.get("points", [])}
    doc = {"dataset": "ISRIC SoilGrids 2.0 (CC BY 4.0; Poggio et al. 2021, doi:10.5194/soil-7-217-2021)",
           "source_url": "https://docs.isric.org/globaldata/soilgrids/index.html",
           "query_url": sg.URL, "resolution": "250 m",
           "depth": "0-30 cm, thickness-weighted from 0-5, 5-15, 15-30 cm (mean)",
           "note": "A model estimate, not a soil test. Only real answers are stored; "
                   "status 'masked' = SoilGrids returned null for that cell; an `estimate` is "
                   "the median of real cells around it, not that point's own value.",
           "points": []}
    lock = threading.Lock()

    def save():
        with lock:
            doc["points"] = list(have.values())
            os.makedirs(os.path.dirname(OUT), exist_ok=True)
            with open(OUT, "w", encoding="utf-8") as f:
                json.dump(doc, f, indent=1, ensure_ascii=False)

    points = wanted_points()
    missing = []
    t0 = time.monotonic()
    print(f"{len(points)} demo points, {WORKERS} calls at a time, {PAUSE_S} s pause, "
          f"limit {args.limit:.0f} s", flush=True)
    for i, pt in enumerate(points, 1):
        k = key(pt["lat"], pt["lon"])
        tag = f"[{i}/{len(points)}] {k}"
        rec = have.get(k)
        try:
            if rec is None or args.refresh:
                try:
                    soil = call(pt["lat"], pt["lon"])
                except sg.SoilGridsError as err:
                    print(f"{tag} {pt['labels']}: FAILED ({err}); not stored", flush=True)
                    missing.append(k)
                    continue
                rec = {"lat": pt["lat"], "lon": pt["lon"], "label": " + ".join(pt["labels"]),
                       "status": "masked" if soil is None else "assessed",
                       "retrieved": date.today().isoformat(), "soil": soil}
                have[k] = rec
                save()
                print(f"{tag} {rec['label']}: {rec['status']}", flush=True)
            else:
                print(f"{tag} {rec['label']}: kept ({rec['status']})", flush=True)
            if rec["status"] == "masked" and "estimate" not in rec:
                est = nb.estimate_from_neighbours(pt["lat"], pt["lon"], call, workers=WORKERS)
                if state["stop"] or time.monotonic() > deadline:
                    raise Stop(state["stop"] or "time limit")
                if est is None:
                    print("       no ring had %d+ cells with values (or calls failed): not "
                          "estimated; district soil is used" % nb.MIN_CELLS, flush=True)
                    missing.append(k)
                    continue
                rec["estimate"] = {"method": "median of SoilGrids cells around the point",
                                   "retrieved": date.today().isoformat(), "soil": est["soil"],
                                   "ring_km": est["ring_km"], "n_cells": est["soil"]["n_cells"],
                                   "n_asked": est["n_asked"], "n_failed": est["n_failed"],
                                   "cells": est["cells"]}
                save()
                print(f"       estimate: median of {est['soil']['n_cells']} cells within "
                      f"{est['ring_km']} km ({est['n_failed']} calls failed)", flush=True)
        except Stop as stop:
            print(f"STOPPED: {stop}. Saved so far; run again to resume.", flush=True)
            missing.extend(key(p["lat"], p["lon"]) for p in points[i - 1:])
            break
    save()
    done = [k for k in (key(p["lat"], p["lon"]) for p in points)
            if k in have and (have[k]["status"] == "assessed" or "estimate" in have[k])]
    print(f"{time.monotonic() - t0:.0f} s. With a value: {len(done)}/{len(points)}. "
          f"Missing or not estimated: {sorted(set(missing)) or 'none'}", flush=True)


if __name__ == "__main__":
    main()
