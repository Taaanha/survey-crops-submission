"""T3b step 7: build the real field-profile layers from the class stacks already on disk, report
the HAND-masked effect on the flood peak date, print the DAE context table, and show one example
pixel through field_profile(). No network. Run from the repo root:
    python scripts/build_layers.py feni cumilla"""
import _proj  # noqa: F401  PROJ guard: keep first (before rasterio / pyproj)
import json
import os
import sys
import time

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "compute"))
from field_profile import (NO_OBS, OPEN_WATER, STATUS, encode_hls, encode_s1,  # noqa: E402
                           field_profile, load_rules, merge_water, write_layers)

START, END = "2024-07-01", "2024-11-30"
BASE = os.path.join(ROOT, "data", "raw", "opera_stacks")
OUT = os.path.join(ROOT, "data", "raw", "opera_layers")
# DAE district figures (share of farmland affected, Aug 2024), as quoted by UNB 2024:
# https://unb.com.bd/category/Bangladesh/no-shortage-of-fertilizers-in-the-country-agriculture-adviser/142861
DAE = {"feni": 80, "cumilla": 36}


def open_share(layer):
    obs = layer != NO_OBS
    return float((layer == OPEN_WATER).sum() / obs.sum()) if obs.any() else 0.0, float(obs.mean())


def merge_date(entry, raw_dir, hand_masked_as):
    parts = []
    for product, enc in (("DSWx-HLS", encode_hls), ("DSWx-S1", encode_s1)):
        enc_list = []
        for gid in entry["granules"][product]:
            raw = np.load(os.path.join(raw_dir, gid + ".npz"))["wtr"]
            enc_list.append(enc(raw, hand_masked_as=hand_masked_as) if product == "DSWx-S1"
                            else enc(raw))
        if enc_list:
            parts.append(merge_water(*enc_list))
    return merge_water(*parts)


def build(district, rules):
    t0 = time.time()
    manifest = json.load(open(os.path.join(ROOT, "data", "processed",
                                           f"field_profile_manifest_{district}.json"), encoding="utf-8"))
    z = np.load(os.path.join(BASE, district, f"water_class_stack_{START}_{END}.npz"))
    dates, stack = z["dates"].tolist(), z["water"]
    by_date = {e["date"]: e for e in manifest["dates"]}
    entries = [by_date[d] for d in dates]
    path = write_layers(district, manifest["grid"], dates, stack, entries, OUT, rules=rules)
    print(f"\n=== {district}: layers written in {time.time() - t0:.0f} s -> {path}")
    for name in sorted(os.listdir(OUT)):
        if name.startswith(district):
            print(f"   {name}  {os.path.getsize(os.path.join(OUT, name)) / 1e6:.1f} MB")

    # --- peak date and the HAND-masked effect
    min_obs = rules["peak_min_observed_share"]
    best = None
    for i, d in enumerate(dates):
        share, obs = open_share(stack[i])
        if obs >= min_obs and (best is None or share > best[1]):
            best = (i, share, obs)
    i, share, obs = best
    d = dates[i]
    raw_dir = os.path.join(BASE, district, "raw_windows")
    hand = np.zeros(stack[i].shape, dtype=bool)
    for gid in by_date[d]["granules"]["DSWx-S1"]:
        hand |= np.load(os.path.join(raw_dir, gid + ".npz"))["wtr"] == 250
    alt_share, alt_obs = open_share(merge_date(by_date[d], raw_dir, "no_observation"))
    print(f"   peak date {d}: observed {100 * obs:.0f}% of the box, open water = {100 * share:.1f}% of observed pixels")
    print(f"   HAND-masked pixels that day: {100 * hand.mean():.1f}% of the box")
    print(f"   if HAND-masked were 'no observation': open water = {100 * alt_share:.1f}% of observed "
          f"(observed {100 * alt_obs:.0f}% of the box)")
    print(f"   CONTEXT: DAE says {DAE.get(district, '?')}% of the district's farmland was affected. "
          f"Not comparable: 20 km box vs whole district; observed pixels only; 'affected' is not 'under open water'.")

    # --- status shares
    import rasterio
    with rasterio.open(os.path.join(OUT, f"{district}_open_water.tif")) as ds:
        names = list(ds.descriptions)
        data = {n: ds.read(k + 1) for k, n in enumerate(names)}
        tr = ds.transform
    st = data["status"]
    print("   open-water status of all pixels:")
    for k, label in enumerate(STATUS):
        n = int((st == k).sum())
        if n:
            print(f"     {label:26s} {100 * n / st.size:6.2f}%")
    ok = np.argwhere((st == 0) & (data["n_events"] == 1) & (data["inundation_days_min"] > 0))
    if len(ok):
        r, c = ok[len(ok) // 2]
        from rasterio.warp import transform as wt
        x, y = tr * (c + 0.5, r + 0.5)
        lon, lat = wt(ds.crs, "EPSG:4326", [x], [y])
        res = field_profile(lat[0], lon[0], district=district, layers_dir=OUT)
        ow = res["metrics"]["open_water"]
        print(f"   example pixel row {r}, col {c} ({lat[0]:.4f}, {lon[0]:.4f}):")
        print(f"     first wet {ow['first_wet_date']}, last wet {ow['last_wet_date']}, drain window "
              f"{ow['drain_window']}, inundation {ow['inundation_days_min']}-{ow['inundation_days_max']} days, status {ow['status']}")
        print(f"     any-water: events {res['metrics']['any_water']['n_events']}, status "
              f"{res['metrics']['any_water']['status']}")
        print(f"     granules (last wet / first dry): "
              f"{res['provenance']['granule_ids']['open_water']['last_wet'][:1]} / "
              f"{res['provenance']['granule_ids']['open_water']['first_dry'][:1]}")


if __name__ == "__main__":
    rules = load_rules()
    for dist in sys.argv[1:] or ["feni", "cumilla"]:
        build(dist, rules)