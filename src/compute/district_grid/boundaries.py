"""The 64 Bangladesh districts (geoBoundaries ADM2, CC BY 3.0 IGO) as shapely polygons."""

import json
import os

from shapely.geometry import shape

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
GEOJSON = os.path.join(ROOT, "data", "reference", "bgd_adm2_districts.geojson")

# geoBoundaries spelling -> our lower-case slug (current official spellings). All 64 are listed,
# so an unknown name is an error, never a guess.
SLUGS = {
    "Bagerhat": "bagerhat", "Bandarban": "bandarban", "Barguna": "barguna", "Barisal": "barishal",
    "Bhola": "bhola", "Bogra": "bogura", "Brahamanbaria": "brahmanbaria", "Chandpur": "chandpur",
    "Chittagong": "chattogram", "Chuadanga": "chuadanga", "Comilla": "cumilla",
    "Cox's Bazar": "coxs_bazar", "Dhaka": "dhaka", "Dinajpur": "dinajpur", "Faridpur": "faridpur",
    "Feni": "feni", "Gaibandha": "gaibandha", "Gazipur": "gazipur", "Gopalganj": "gopalganj",
    "Habiganj": "habiganj", "Jamalpur": "jamalpur", "Jessore": "jashore", "Jhalokati": "jhalakathi",
    "Jhenaidah": "jhenaidah", "Joypurhat": "joypurhat", "Khagrachhari": "khagrachari",
    "Khulna": "khulna", "Kishoreganj": "kishoreganj", "Kurigram": "kurigram", "Kushtia": "kushtia",
    "Lakshmipur": "lakshmipur", "Lalmonirhat": "lalmonirhat", "Madaripur": "madaripur",
    "Magura": "magura", "Manikganj": "manikganj", "Maulvibazar": "moulvibazar", "Meherpur": "meherpur",
    "Munshiganj": "munshiganj", "Mymensingh": "mymensingh", "Naogaon": "naogaon", "Narail": "narail",
    "Narayanganj": "narayanganj", "Narsingdi": "narsingdi", "Natore": "natore",
    "Nawabganj": "chapai_nawabganj", "Netrakona": "netrokona", "Nilphamari": "nilphamari",
    "Noakhali": "noakhali", "Pabna": "pabna", "Panchagarh": "panchagarh", "Patuakhali": "patuakhali",
    "Pirojpur": "pirojpur", "Rajbari": "rajbari", "Rajshahi": "rajshahi", "Rangamati": "rangamati",
    "Rangpur": "rangpur", "Satkhira": "satkhira", "Shariatpur": "shariatpur", "Sherpur": "sherpur",
    "Sirajganj": "sirajganj", "Sunamganj": "sunamganj", "Sylhet": "sylhet", "Tangail": "tangail",
    "Thakurgaon": "thakurgaon",
}
LIVE_DISTRICTS = ("cumilla", "feni", "brahmanbaria", "noakhali", "sylhet")


def slug_for(boundary_name):
    return SLUGS[boundary_name]


def load_districts(path=GEOJSON):
    """List of {slug, name, geometry, point}; point = centroid, or a point inside the polygon if
    the centroid falls outside it (used as the POWER query point)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    out = []
    for feat in data["features"]:
        name = feat["properties"]["shapeName"]
        geom = shape(feat["geometry"])
        pt = geom.centroid
        if not geom.contains(pt):
            pt = geom.representative_point()
        out.append({"slug": slug_for(name), "name": name, "geometry": geom, "point": pt})
    return sorted(out, key=lambda d: d["slug"])


def metadata(path=GEOJSON):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["metadata"]
