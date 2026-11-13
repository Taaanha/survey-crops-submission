"""T3b: re-cut the Feni river fixture (50 x 50) around a real river pixel, from the raw windows
already on disk. No network. Run from the repo root:  python scripts/recut_fixture.py"""
import json
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "compute"))
from field_profile import OPEN_WATER, NOT_WATER, NO_OBS, encode_hls, encode_s1, merge_water  # noqa: E402

DIR = os.path.join(ROOT, "tests", "fixtures", "field_profile")
NPZ = os.path.join(DIR, "feni_river_50x50.npz")
META = os.path.join(DIR, "feni_river_meta.json")
BASE = os.path.join(ROOT, "data", "raw", "opera_stacks", "feni")
ROW, COL, HALF, N_DATES = 487, 487, 25, 7
ENC = {"DSWx-HLS": ("hls_raw", encode_hls), "DSWx-S1": ("s1_raw", encode_s1)}

manifest = json.load(open(os.path.join(ROOT, "data", "processed",
                                       "field_profile_manifest_feni.json"), encoding="utf-8"))
entries = {e["date"]: e for e in manifest["dates"]}
z = np.load(os.path.join(BASE, "water_class_stack_2024-07-01_2024-11-30.npz"))
dates, water = z["dates"].tolist(), z["water"]
series = water[:, ROW, COL]

candidates = [i for i, d in enumerate(dates)
              if series[i] == OPEN_WATER
              and all(len(entries[d]["granules"][p]) <= 1 for p in ENC)]
print(f"dates where pixel ({ROW},{COL}) is open water with <= 1 granule per product: {len(candidates)}")
if len(candidates) < N_DATES:
    sys.exit("not enough usable dates; paste this output to Claude")
chosen = [candidates[i] for i in np.linspace(0, len(candidates) - 1, N_DATES).round().astype(int)]

r0, c0 = ROW - HALF, COL - HALF
sl = (slice(r0, r0 + 2 * HALF), slice(c0, c0 + 2 * HALF))
old_meta = json.load(open(META, encoding="utf-8"))
out = {"hls_raw": [], "s1_raw": [], "merged": []}
new_entries = []
for i in chosen:
    e = entries[dates[i]]
    parts = []
    for product, (key, enc) in ENC.items():
        ids = e["granules"][product]
        if ids:
            raw = np.load(os.path.join(BASE, "raw_windows", ids[0] + ".npz"))["wtr"][sl]
            parts.append(enc(raw))
        else:
            raw = np.full((2 * HALF, 2 * HALF), 255, dtype=np.uint8)
        out[key].append(raw.astype(np.uint8))
    out["merged"].append(merge_water(*parts))
    new_entries.append({"date": e["date"], "granules": e["granules"], "source_urls": e["source_urls"]})

arrays = {k: np.stack(v) for k, v in out.items()}
np.savez_compressed(NPZ, **arrays)
others = [k for k in old_meta if k not in ("dates", "channel_pixel")]
old_meta["dates"] = new_entries
old_meta["channel_pixel"] = [HALF, HALF]
old_meta["window_origin_row_col"] = [r0, c0]
json.dump(old_meta, open(META, "w", encoding="utf-8"), indent=1)

m = arrays["merged"]
print("chosen dates:", [d["date"] for d in new_entries])
print("channel series:", m[:, HALF, HALF].tolist())
print("share not-water in window:", round(float((m == NOT_WATER).mean()), 3),
      "| no-obs:", round(float((m == NO_OBS).mean()), 3))
print("other keys kept in meta (check they still make sense):", others)
print("file sizes (KB):", round(os.path.getsize(NPZ) / 1024, 1), round(os.path.getsize(META) / 1024, 1))