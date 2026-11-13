"""One-off: set the 'value' column of data/reference/opera_classes.csv to the T3b states
(2 open water, 1 partial/vegetation water, 0 not water, 255 no observation), computed with
the real encoders so the table and the code cannot disagree. Run from the repo root."""
import csv
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "compute"))
from field_profile import encode_hls, encode_s1  # noqa: E402

PATH = os.path.join(ROOT, "data", "reference", "opera_classes.csv")
ENCODERS = (("dswx_hls.wtr.", encode_hls), ("dswx_s1.wtr.", encode_s1))

with open(PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    fields = reader.fieldnames
    rows = list(reader)

changed = 0
for row in rows:
    for prefix, enc in ENCODERS:
        if row["item"].startswith(prefix):
            code = int(row["item"][len(prefix):])
            new = str(int(enc(np.array([code], dtype=np.uint8))[0]))
            if row["value"] != new:
                print(f"{row['item']}: {row['value']} -> {new}")
                row["value"] = new
                changed += 1

with open(PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
print(f"done, {changed} value(s) changed")