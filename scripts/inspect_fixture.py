"""Read-only: show the raw and encoded codes at the river fixture's best pixels."""
import json
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "compute"))
from field_profile import NO_OBS, OPEN_WATER, PARTIAL_WATER  # noqa: E402

DIR = os.path.join(ROOT, "tests", "fixtures", "field_profile")
meta = json.load(open(os.path.join(DIR, "feni_river_meta.json"), encoding="utf-8"))
a = np.load(os.path.join(DIR, "feni_river_50x50.npz"))
m = a["merged"]

print("dates:")
for i, d in enumerate(meta["dates"]):
    print(f"  {i}  {d['date']}  HLS={len(d['granules']['DSWx-HLS'])} S1={len(d['granules']['DSWx-S1'])}")

print("channel_pixel in meta:", meta["channel_pixel"])
water_any = np.isin(m, [OPEN_WATER, PARTIAL_WATER]).sum(axis=0)
obs = (m != NO_OBS).sum(axis=0)
order = np.argsort(-(water_any * 100 + obs), axis=None)[:3]
for flat in order:
    y, x = np.unravel_index(flat, water_any.shape)
    print(f"\npixel ({y},{x}): any-water on {water_any[y, x]} of {obs[y, x]} observed dates")
    print("  merged:", m[:, y, x].tolist())
    print("  hls_raw:", a["hls_raw"][:, y, x].tolist())
    print("  s1_raw :", a["s1_raw"][:, y, x].tolist())

print("\nshare of window pixels per merged code (all dates):")
for code in (2, 1, 0, 255):
    print(f"  {code}: {100 * (m == code).mean():.1f}%")