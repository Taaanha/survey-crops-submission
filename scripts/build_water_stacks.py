"""Builds the OPERA water stacks (T3a) and the coverage numbers. Raw windows and stacks go to
data/raw/opera_stacks/ (gitignored); the small manifest goes to data/processed/.

Run from the repo root:
    python scripts/build_water_stacks.py feni cumilla
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "compute"))
from field_profile import build_water_stack  # noqa: E402

START, END = "2024-07-01", "2024-11-30"
OUT = os.path.join(ROOT, "data", "raw", "opera_stacks")

if __name__ == "__main__":
    for district in sys.argv[1:] or ["feni", "cumilla"]:
        print(district, build_water_stack(district, START, END, OUT), flush=True)
