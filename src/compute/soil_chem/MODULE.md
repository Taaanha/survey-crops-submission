# soil_chem (soil pH and organic carbon, Layer 1)

Code: src/compute/soil_chem/loader.py, src/acquire/soilgrids_ph_oc.py

Fetch with `python scripts/fetch_soil_ph_oc.py` (acquire layer, network; the loader never calls out).

Reads `data/processed/soilgrids_ph_oc_points.csv` (ISRIC SoilGrids 2.0, 250 m, CC BY 4.0, no key or login; fair use 5 calls/minute) and returns pH and organic carbon at three layers (0-5, 5-15, 15-30 cm) with the mean and the service's Q0.05 / Q0.5 / Q0.95, each as a `measured` number with provenance.

- Always labelled: "SoilGrids model estimate, 250 m, not a soil test; confirm with a local soil test".
- Units are read from the service's own metadata (`d_factor`: pH x10, organic carbon dg/kg), never assumed; an unknown `mapped_units` string is refused.
- Organic carbon is NOT organic matter: no conversion factor is applied (none is sourced).
- Layers are reported one by one. Quantiles of separate layers are not combined into a 0-30 cm range.
- A masked cell (service returns null) or a failed call is a gap row with its reason. Nothing is interpolated or taken from a neighbouring cell.
- `status_rows()` gives the two rows in `docs/w1b_data_status.csv` (also appended by `sat_layers.intake.build_status`).

Used by `strategies.core.attach_soil` (W4 organic-matter indicator). Tests: `tests/soil_chem/` (26), `tests/strategies/test_soil_wiring.py`.
