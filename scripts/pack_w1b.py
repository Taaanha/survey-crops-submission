"""
scripts/pack_w1b.py

Bundles the few files the Colab notebook needs (the repo is private, so Colab cannot clone it) into
data/raw/w1b_pack.zip (about 0.7 MB, gitignored). Upload that zip to Google Drive or when the
notebook asks for it. Contains: district_grid code (grid, boundaries, regrid), the W1b helpers,
the 64-district boundary file, the two demo-tile manifests and the five old SMAP point files
(used only for a cross-check). No secrets.

Run from the repo root:  python scripts/pack_w1b.py
"""
import glob
import os
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "data", "raw", "w1b_pack.zip")

PATTERNS = [
    "src/compute/district_grid/__init__.py", "src/compute/district_grid/grid.py",
    "src/compute/district_grid/boundaries.py", "src/compute/district_grid/regrid.py",
    "src/acquire/w1b/__init__.py", "src/acquire/w1b/products.py", "src/acquire/w1b/appeears.py",
    "src/acquire/w1b/convert.py", "src/acquire/w1b/tables.py", "src/acquire/w1b/dem.py",
    "data/reference/bgd_adm2_districts.geojson",
    "data/processed/field_profile_manifest_feni.json", "data/processed/field_profile_manifest_cumilla.json",
    "data/processed/smap_*_2015_2026.csv",
]


def main():
    files = sorted({p for pat in PATTERNS for p in glob.glob(os.path.join(ROOT, pat))})
    missing = [pat for pat in PATTERNS if not glob.glob(os.path.join(ROOT, pat))]
    if missing:
        raise SystemExit(f"missing: {missing}")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, os.path.relpath(p, ROOT).replace(os.sep, "/"))
    print(f"wrote {OUT}: {len(files)} files, {os.path.getsize(OUT) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
