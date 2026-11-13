"""District outlines for the map (W5, Layer 1): the geoBoundaries ADM2 file already in the repo.

Licence and source were verified on 10 Nov 2026 (data/reference/r13_boundary_licence.csv) and again
on 12 Nov 2026 against the geoBoundaries API: Creative Commons Attribution 3.0 IGO, original source
BBS / OCHA ROAP, boundary year 2020. The shapes are the simplified geometry. No AI, no network."""

import functools
import json
import os

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
GEOJSON = os.path.join(ROOT, "data", "reference", "bgd_adm2_districts.geojson")
# the five live districts = the rows of district_metadata.csv (kept free of shapely, which the
# deployed API does not install)
LIVE_DISTRICTS = tuple(pd.read_csv(os.path.join(ROOT, "data", "processed", "district_metadata.csv")).district)

CITATION = ("Runfola, D. et al. (2020) geoBoundaries: A global database of political administrative "
            "boundaries. PLOS ONE 15(4): e0231866. https://doi.org/10.1371/journal.pone.0231866")
LICENCE_TEXT_URL = "https://creativecommons.org/licenses/by/3.0/igo/"


def _slugs(path=GEOJSON):
    with open(path, encoding="utf-8") as f:
        return sorted(ft["properties"]["slug"] for ft in json.load(f)["features"])


SLUG_LIST = _slugs()


@functools.lru_cache(maxsize=1)
def district_outlines(path=GEOJSON):
    """GeoJSON FeatureCollection of the 64 districts (properties: slug, name, live) and the
    provenance block (dataset, source URL, licence, attribution, citation)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    meta = data["metadata"]
    features = [{"type": "Feature", "geometry": f["geometry"],
                 "properties": {"slug": f["properties"]["slug"], "name": f["properties"]["shapeName"],
                                "live": f["properties"]["slug"] in LIVE_DISTRICTS}}
                for f in data["features"]]
    return {"type": "FeatureCollection", "features": features,
            "provenance": {"dataset": meta["dataset"], "source_url": meta["source_url"],
                           "licence": meta["license"], "licence_text_url": LICENCE_TEXT_URL,
                           "attribution": meta["attribution"], "citation": CITATION,
                           "retrieved": meta["retrieved"],
                           "note": "Simplified geometry, boundary year 2020; we did not edit the shapes."}}
