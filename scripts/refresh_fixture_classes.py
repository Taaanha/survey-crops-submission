"""One-off (T3b): recompute the 'merged' layer of the Feni river fixture with the class-aware
encoders (2 open water, 1 partial/vegetation water, 0 not water, 255 no observation) from the
raw codes stored in the same file. Re-picks the channel pixel from the data if the old one is not
open water on >= 90% of its observed dates. No network. Run from the repo root."""
import json
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "compute"))
from field_profile import OPEN_WATER, NO_OBS, encode_hls, encode_s1, merge_water  # noqa: E402

DIR = os.path.join(ROOT, "tests", "fixtures", "field_profile")
NPZ = os.path.join(DIR, "feni_river_50x50.npz")
META = os.path.join(DIR, "feni_river_meta.json")

with open(META, encoding="utf-8") as f:
    meta = json.load(f)
data = {k: v for k, v in np.load(NPZ).items()}

merged = []
for i, d in enumerate(meta["dates"]):
    parts = []
    for key, product, enc in (("hls", "DSWx-HLS", encode_hls), ("s1", "DSWx-S1", encode_s1)):
        if d["granules"][product]:
            parts.append(enc(data[f"{key}_raw"][i]))
    merged.append(merge_water(*parts))
data["merged"] = np.stack(merged)

observed = data["merged"] != NO_OBS
n_obs = observed.sum(axis=0)
n_open = (data["merged"] == OPEN_WATER).sum(axis=0)
frac = np.where(n_obs > 0, n_open / np.maximum(n_obs, 1), 0.0)


def describe(y, x):
    return f"pixel ({y},{x}): open water on {n_open[y, x]} of {n_obs[y, x]} observed dates"


cy, cx = meta["channel_pixel"]
print("old channel", describe(cy, cx))
if n_obs[cy, cx] >= 3 and frac[cy, cx] >= 0.9:
    print("old channel pixel is fine, keeping it")
else:
    ok = n_obs >= 3
    score = np.where(ok, frac * 1000 + n_obs, -1)
    cy, cx = [int(v) for v in np.unravel_index(np.argmax(score), score.shape)]
    meta["channel_pixel"] = [cy, cx]
    print("new channel", describe(cy, cx))

np.savez_compressed(NPZ, **data)
with open(META, "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=1)
print("fixture rewritten")