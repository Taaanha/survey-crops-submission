"""
scripts/build_boundaries.py

Turns the raw geoBoundaries ADM2 file for Bangladesh (data/raw/boundaries/, gitignored) into the
small committed file data/reference/bgd_adm2_districts.geojson (64 districts, coordinates rounded
to 4 decimals, with licence and source in a top-level "metadata" block).

Run from the repo root:  python scripts/build_boundaries.py
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "compute"))
from district_grid.boundaries import slug_for  # noqa: E402

RAW = os.path.join(ROOT, "data", "raw", "boundaries", "gb_bgd_adm2_simplified.geojson")
OUT = os.path.join(ROOT, "data", "reference", "bgd_adm2_districts.geojson")


def rnd(c):
    return [rnd(x) for x in c] if isinstance(c[0], list) else [round(c[0], 4), round(c[1], 4)]


def main():
    raw = json.load(open(RAW, encoding="utf-8"))
    feats = []
    for f in raw["features"]:
        name = f["properties"]["shapeName"]
        g = f["geometry"]
        feats.append({"type": "Feature",
                      "properties": {"shapeName": name, "slug": slug_for(name),
                                     "shapeID": f["properties"]["shapeID"]},
                      "geometry": {"type": g["type"], "coordinates": rnd(g["coordinates"])}})
    feats.sort(key=lambda x: x["properties"]["slug"])
    out = {"type": "FeatureCollection",
           "metadata": {
               "dataset": "geoBoundaries gbOpen BGD ADM2 (simplified geometry)",
               "license": "Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO)",
               "attribution": "geoBoundaries (William & Mary geoLab); original source Bangladesh Bureau of "
                              "Statistics (BBS) via OCHA ROAP, boundary year 2020",
               "source_url": "https://www.geoboundaries.org/api/current/gbOpen/BGD/ADM2/",
               "file_url": "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/BGD/ADM2/"
                           "geoBoundaries-BGD-ADM2_simplified.geojson",
               "license_source": "https://data.humdata.org/dataset/administrative-boundaries-of-bangladesh-as-of-2015",
               "retrieved": "2026-11-10", "units": 64},
           "features": feats}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, separators=(",", ":"))
    print(len(feats), "districts,", os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
