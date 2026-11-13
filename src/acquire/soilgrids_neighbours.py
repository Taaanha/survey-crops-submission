"""
src/acquire/soilgrids_neighbours.py

For a point whose own SoilGrids cell is masked (null: town, river, water), an estimate
from the real SoilGrids cells around it: the MEDIAN of each property over the cells that
have values, in the nearest ring that has at least MIN_CELLS of them.

This is a labelled estimate, never the point's own value. It is built offline by
scripts/build_soil_fixture.py (not on a live request) and stored with its method, the
number of cells, the radius and the min-max spread of the cells.

Ring step: 0.009 degrees of latitude is about 1.0 km (SoilGrids cells are 250 m); rings
at 1 km and 2 km, 8 directions each. The ring distances are our choice.
"""

import math
import statistics
from concurrent.futures import ThreadPoolExecutor

from fetch_soilgrids import usda_texture

STEP_DEG = 0.009
RINGS = (1, 2)            # multiples of STEP_DEG
MIN_CELLS = 3             # fewer valid cells than this: not assessed
DIRECTIONS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
PROPS = ("sand", "silt", "clay", "ph", "organic_carbon_g_kg")


def ring_points(lat, lon, ring):
    """8 points around (lat, lon) at ring * STEP_DEG in latitude (about ring km);
    longitude is scaled by cos(lat) so the distance is the same in every direction."""
    d = ring * STEP_DEG
    out = []
    for dy, dx in DIRECTIONS:
        scale = math.sqrt(2) / 2 if dy and dx else 1.0
        out.append((round(lat + dy * d * scale, 5),
                    round(lon + dx * d * scale / math.cos(math.radians(lat)), 5)))
    return out


def median_estimate(cells):
    """cells: list of soil dicts (parse_response output, None = masked). -> soil dict of
    medians plus spread, or None if fewer than MIN_CELLS cells have any value."""
    valid = [c for c in cells if c is not None]
    if len(valid) < MIN_CELLS:
        return None
    out, spread = {}, {}
    for p in PROPS:
        vals = [c[p] for c in valid if c.get(p) is not None]
        if len(vals) >= MIN_CELLS:
            out[p], spread[p] = statistics.median(vals), [min(vals), max(vals)]
        else:
            out[p] = None
    if None not in (out["sand"], out["silt"], out["clay"]):
        scale = 100.0 / (out["sand"] + out["silt"] + out["clay"])
        for p in ("sand", "silt", "clay"):
            out[p] *= scale
        out["texture"] = usda_texture(out["sand"], out["silt"], out["clay"])
    else:
        out["texture"] = None
    if all(out[p] is None for p in PROPS):
        return None
    out["n_cells"], out["spread"] = len(valid), spread
    return out


def estimate_from_neighbours(lat, lon, fetch, workers=1):
    """fetch(lat, lon) -> soil dict | None (raises on a failed call). Tries each ring in
    turn, `workers` calls at a time. -> {"soil", "ring_km", "cells": [[lat, lon], ...], "n_asked", "n_failed"} or None.
    A failed call counts as no cell (never retried here, never guessed)."""
    for ring in RINGS:
        asked = ring_points(lat, lon, ring)
        cells, ok, failed = [], [], 0

        def ask(pt):
            try:
                return True, fetch(*pt)
            except Exception:   # noqa: BLE001 - a failed call is simply not a cell
                return False, None

        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            answers = list(pool.map(ask, asked))
        for (plat, plon), (called, soil) in zip(asked, answers):
            if not called:
                failed += 1
                continue
            cells.append(soil)
            if soil is not None:
                ok.append([plat, plon])
        est = median_estimate(cells)
        if est is not None:
            return {"soil": est, "ring_km": ring, "cells": ok, "n_asked": len(asked),
                    "n_failed": failed}
    return None
