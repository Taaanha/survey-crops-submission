"""T3b: build the class-aware water stacks (2 open water, 1 partial/vegetation water, 0 not water,
255 no observation) from the raw windows already on disk, check them against the T3a stacks, and
list candidate river pixels. No network. Output stays in data/raw/ (gitignored).
Run from the repo root:  python scripts/build_class_stacks.py feni cumilla"""
import json
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "compute"))
from field_profile import (NO_OBS, OPEN_WATER, PARTIAL_WATER, encode_hls, encode_s1,  # noqa: E402
                           merge_water)

START, END = "2024-07-01", "2024-11-30"
BASE = os.path.join(ROOT, "data", "raw", "opera_stacks")
ENC = {"DSWx-HLS": encode_hls, "DSWx-S1": encode_s1}


def build(district):
    with open(os.path.join(ROOT, "data", "processed",
                           f"field_profile_manifest_{district}.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    raw_dir = os.path.join(BASE, district, "raw_windows")
    dates, layers, missing = [], [], 0
    for entry in manifest["dates"]:
        parts = []
        for product, ids in entry["granules"].items():
            encoded = []
            for gid in ids:
                path = os.path.join(raw_dir, gid + ".npz")
                if not os.path.exists(path):
                    missing += 1
                    continue
                encoded.append(ENC[product](np.load(path)["wtr"]))
            if encoded:
                parts.append(merge_water(*encoded))
        if parts:
            dates.append(entry["date"])
            layers.append(merge_water(*parts))
    stack = np.stack(layers)
    out = os.path.join(BASE, district, f"water_class_stack_{START}_{END}.npz")
    np.savez_compressed(out, dates=np.array(dates), water=stack)
    print(f"\n{district}: wrote {out}  shape {stack.shape}  missing raw windows: {missing}")

    any_water = np.isin(stack, [OPEN_WATER, PARTIAL_WATER])
    try:
        old = np.load(os.path.join(BASE, district, f"water_stack_{START}_{END}.npz"))
        print("  check vs T3a stack: dates equal =", old["dates"].tolist() == dates,
              "| any-water equal =", bool(((old["water"] == 1) == any_water).all()),
              "| no-obs equal =", bool(((old["water"] == 255) == (stack == NO_OBS)).all()))
    except Exception as err:  # the old T3a file can be damaged; the new stack does not depend on it
        print("  old T3a stack unreadable, check skipped:", type(err).__name__)
    back = np.load(out)["water"]
    print("  new stack reads back fine:", back.shape, "any open water:", bool((back == OPEN_WATER).any()))
    obs = (stack != NO_OBS).sum(axis=0)
    n_open = (stack == OPEN_WATER).sum(axis=0)
    frac = np.where(obs > 0, n_open / np.maximum(obs, 1), 0.0)
    good = (obs >= 8) & (frac >= 0.9)
    print(f"  pixels observed on >= 8 dates and open water on >= 90% of them: {int(good.sum())}"
          f" of {good.size}")
    if good.any():
        score = np.where(good, obs, -1)
        for flat in np.argsort(-score, axis=None)[:5]:
            y, x = np.unravel_index(flat, score.shape)
            print(f"   pixel row {y}, col {x}: open water on {n_open[y, x]} of {obs[y, x]} dates")
        y, x = np.unravel_index(np.argmax(score), score.shape)
        print("   series at the best pixel:", stack[:, y, x].tolist())


if __name__ == "__main__":
    for d in sys.argv[1:] or ["feni", "cumilla"]:
        build(d)
        