"""Provenance of the W1b satellite layers: dataset, source URL, resolution, units.

Every value a loader returns carries one of these dicts, so any number shown later can cite its
dataset and link. URLs were opened or read from the NASA catalogues on 10-11 Nov 2026 (the same
links as src/acquire/w1b/products.py; a test keeps the two in step). `coverage_years` is added by
the loader from the data actually present, never typed here."""

PROVENANCE = {
    "nasadem": {
        "dataset": "NASADEM_NC.001 (NASA JPL), 30 m, read through NASA AppEEARS",
        "source_url": "https://appeears.earthdatacloud.nasa.gov/api/product/NASADEM_NC.001",
        "resolution": "30 m pixels, averaged onto the 0.1 degree grid, then over the district polygon",
        "units": "elevation in m; slope in degrees",
    },
    "grace": {
        "dataset": "JPL GRACE and GRACE-FO mascons, CRI filtered, RL06.3 Mv04 (TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4), PO.DAAC",
        "source_url": "https://podaac.jpl.nasa.gov/dataset/TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4",
        "resolution": "0.5 degree mascon grid, about 300 km effective; nearest cell to the district point (REGIONAL)",
        "units": "cm equivalent water thickness, anomaly from the time mean (unit inferred from the product, not read from the file)",
    },
    "modis": {
        "dataset": "MODIS Terra MOD13Q1.061 NDVI and EVI, 16-day, read through NASA AppEEARS",
        "source_url": "https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod13q1-061",
        "resolution": "250 m pixels, averaged onto the 0.1 degree grid, then over the district polygon",
        "units": "NDVI and EVI index values (no unit)",
    },
    "hls": {
        "dataset": "Harmonized Landsat Sentinel-2 HLSL30.020 and HLSS30.020, read through NASA AppEEARS",
        "source_url": "https://appeears.earthdatacloud.nasa.gov/api/product/HLSL30.020",
        "resolution": "30 m; mean of the clear pixels over the whole 20 km demo tile (not a single field)",
        "units": "NDVI (no unit); clear_share = fraction of tile pixels used",
    },
    "ecostress": {
        "dataset": "ECOSTRESS ECO_L3T_JET.002 ETdaily, read through NASA AppEEARS",
        "source_url": "https://www.earthdata.nasa.gov/data/catalog/lpcloud-eco-l3t-jet-002",
        "resolution": "70 m; mean over the 20 km demo tile, irregular passes",
        "units": "UNRESOLVED: the file tags W/m2 (also on the 0/1 cloud layer); raw values look like mm/day, not W/m2",
    },
    "smap_live": {
        "dataset": "NASA SMAP L4 SPL4SMGP v8 root-zone soil moisture, point pixel at each live district",
        "source_url": "https://nsidc.org/data/spl4smgp/versions/8",
        "resolution": "9 km pixel at the district point",
        "units": "m3/m3",
    },
}

REQUIRED_FIELDS = ("dataset", "source_url", "resolution", "units")


def provenance(key, coverage_years):
    """Copy of the provenance for `key` with the coverage years found in the data added."""
    if key not in PROVENANCE:
        raise KeyError(f"no provenance for {key!r}; known: {sorted(PROVENANCE)}")
    return {**PROVENANCE[key], "coverage_years": coverage_years}
